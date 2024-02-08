from uuid import uuid4
from enum import Enum
import json
import random
from collections import defaultdict

import boto3
from cachetools import cached, TTLCache

from backend.exceptions import (
    InvalidArgumentsError,
    PermissionsMissing,
    StackSetExecutionInProgressException,
    StackSetUpdateInProgressException,
    InvalidApplicationState,
)

# StackSet operations incomplete statuses
# All listed under https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_StackSetOperationSummary.html
STACKSET_UPDATING_STATUS = "RUNNING"
STACKSET_OPERATION_INCOMPLETE_STATUSES = {"QUEUED", "RUNNING", "STOPPING"}
# Stack Instance Statuses
# All listed under https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_StackInstanceSummary.html
SYNCHRONIZED_STATUS = "CURRENT"
FAILED_STATUS = "FAILED"
# Stack Instance Detailed Statuses
# All listed under https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_StackInstanceComprehensiveStatus.html  # noqa
STACK_INSTANCE_PENDING_STATUS = "PENDING"
INCOMPLETE_DETAILED_STATUS = {"PENDING", "RUNNING"}
# Stack Instance Detailed Statuses
# All listed under https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_StackInstanceComprehensiveStatus.html  # noqa
SUCCESS_DETAILED_STATUS = "SUCCEEDED"
# Acceptable stack statuses. Only instances with stack status among these two should be reported on to users.
# List values listed under https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_ListStacks.html
INSTANCES_STACK_STATUSES = {
    "CREATE_IN_PROGRESS",
    "CREATE_COMPLETE",
    "UPDATE_IN_PROGRESS",
    "UPDATE_COMPLETE",
}

EC2_INSTANCE_PENDING_STATE = "pending"
EC2_INSTANCE_FINAL_STATES = {"running", "stopped"}


class UpdateLevel(Enum):
    STACKSET_LEVEL = "stack_set"
    INSTANCE_LEVEL = "instance"


class AwsUtils:
    def __init__(
        self,
        permissions_table_name,
        regional_data_table_name,
        state_table_name,
        cross_account_role_name,
        admin_group_name,
        provision_sfn_arn,
        update_sfn_arn,
        error_topic_arn,
        cleanup_sfn_arn,
        cfn_data_bucket,
        execution_role_name,
        admin_role_arn,
        logger,
    ):
        self.permissions_table_name = permissions_table_name
        self.regional_data_table_name = regional_data_table_name
        self.state_table_name = state_table_name

        self.cleanup_sfn_arn = cleanup_sfn_arn
        self.provision_sfn_arn = provision_sfn_arn
        self.update_sfn_arn = update_sfn_arn

        self.admin_group_name = admin_group_name
        self.error_topic_arn = error_topic_arn
        self.cross_account_role_name = cross_account_role_name
        self.cfn_data_bucket = cfn_data_bucket
        self.execution_role_name = execution_role_name
        self.admin_role_arn = admin_role_arn

        self.logger = logger

    def get_claims_list(self, value):
        # Accepts a string representation of a list, returns a python list
        return value[1:-1].split(" ")

    def get_claims(self, request):
        context = json.loads(request.headers["X-Amzn-Request-Context"])
        claims = context["authorizer"]["jwt"]["claims"]

        if "email" not in claims or not claims["email"]:
            raise ValueError("The JWT is missing the 'email' claim value.")

        if "groups" not in claims or not claims["groups"]:
            raise ValueError("The JWT is missing the 'groups' claim value.")

        if "name" not in claims or not claims["name"]:
            raise ValueError("The JWT is missing the 'name' claim value.")

        groups = self.get_claims_list(claims["groups"])
        is_superuser = self.admin_group_name in groups

        return {
            "email": claims["email"],
            "groups": groups,
            "username": claims["name"],
            "is_superuser": is_superuser,
            "claims": claims,
        }

    def get_permissions_for_all_groups(self, groups):
        result = {}

        for group_name in groups:
            permissions = self.get_permissions_for_one_group(group_name=group_name)
            if not permissions:
                continue

            # Filter out the InstanceTypes the users have permissions for
            # through what's available in the configured AZs
            for account_id, account_map in permissions["region_map"].items():
                for region_id in account_map.keys():
                    region_permissions = self.get_params_for_region(account_id=account_id, region=region_id)

                    all_instance_types = set(
                        [item for az_list in region_permissions["azs_to_instance_types"].values() for item in az_list]
                    )
                    available_instance_types = set(permissions["instance_types"]).intersection(all_instance_types)

                    permissions["region_map"][account_id][region_id]["instance_types"] = list(available_instance_types)

            result[group_name] = permissions

        return result

    def get_permissions_for_one_group(self, group_name):
        client = boto3.client("dynamodb")

        result = {}

        fetched = client.get_item(TableName=self.permissions_table_name, Key={"group": {"S": group_name}})

        if "Item" not in fetched:
            self.logger.info(f"The group '{group_name}' does not have any permissions associated with it.")
            return result

        item = fetched["Item"]

        operating_systems = json.loads(item["operatingSystems"]["S"])
        region_map = defaultdict(lambda: defaultdict(dict))
        for os_item in operating_systems:
            for account_id in os_item["region-map"].keys():
                account_map = os_item["region-map"][account_id]
                for region_name in account_map.keys():
                    current_oses = region_map[account_id][region_name].get("os_types", [])
                    region_map[account_id][region_name]["os_types"] = [*current_oses, os_item["name"]]

        return {
            "instance_types": item["instanceTypes"]["SS"],
            "region_map": region_map,
            # Even though DynamoDB treats Number type as numeric internally, but accepts and returns them
            # as strings hence the need to cast the values explicitly
            # https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.NamingRulesDataTypes.html#HowItWorks.DataTypes
            "max_days_to_expiry": int(item["maxDaysToExpiry"]["N"]),
            "max_instance_count": int(item["maxInstanceCount"]["N"]),
            "max_extension_count": int(item["maxExtensionCount"]["N"]),
        }

    def get_os_config(self, group_name, os_name):
        client = boto3.client("dynamodb")

        fetched = client.get_item(TableName=self.permissions_table_name, Key={"group": {"S": group_name}})

        if "Item" not in fetched:
            raise PermissionsMissing(
                message=f"The group '{group_name}' does not have any permissions associated with it."
            )

        os_configs = json.loads(fetched["Item"]["operatingSystems"]["S"])
        result = [config for config in os_configs if config["name"] == os_name]

        if not result:
            raise PermissionsMissing(message=f"Could not find the permission for '{os_name}' for group: {group_name}.")

        return result[0]

    @cached(cache=TTLCache(maxsize=1024, ttl=600))
    def get_params_for_region(self, account_id, region):
        dynamodb_client = boto3.client("dynamodb")
        regional_data = dynamodb_client.get_item(
            TableName=self.regional_data_table_name,
            Key={"accountId": {"S": account_id}, "region": {"S": region}},
        )

        if "Item" not in regional_data:
            raise PermissionsMissing(
                message=f"The region '{region}' does not have any configuration associated with it."
            )

        subnet_ids = regional_data["Item"]["subnetId"]["SS"]

        # Check which subnet the instance_type is available in
        ec2_client = self.get_remote_client(account_id=account_id, region=region, service="ec2")
        subnets = ec2_client.describe_subnets(SubnetIds=subnet_ids)
        az_to_subnet_map = {}
        for item in subnets["Subnets"]:
            current_az = item["AvailabilityZone"]
            az_to_subnet_map[current_az] = [
                *az_to_subnet_map.get(current_az, []),
                item["SubnetId"],
            ]

        availability_zones = list(az_to_subnet_map.keys())
        potential_instance_types = ec2_client.describe_instance_type_offerings(
            LocationType="availability-zone",
            Filters=[{"Name": "location", "Values": availability_zones}],
        )
        azs_to_instance_types = defaultdict(list)
        for item in potential_instance_types["InstanceTypeOfferings"]:
            azs_to_instance_types[item["Location"]].append(item["InstanceType"])

        result = {
            "vpc_id": regional_data["Item"]["vpcId"]["S"],
            "ssh_key_name": regional_data["Item"]["sshKeyName"]["S"],
            "az_to_subnet_map": az_to_subnet_map,
            "azs_to_instance_types": azs_to_instance_types,
        }

        return result

    def get_provisioning_params_for_region(self, account_id, region, instance_type):
        regional_data = self.get_params_for_region(account_id=account_id, region=region)

        valid_azs = [
            az_name
            for az_name, instance_types in regional_data["azs_to_instance_types"].items()
            if instance_type in instance_types
        ]

        if len(valid_azs) == 0:
            raise InvalidArgumentsError(
                message=f"The instance type '{instance_type}' is not available in the region '{region}'."
            )

        selected_az = random.choice(valid_azs)
        result = {
            "vpc_id": regional_data["vpc_id"],
            "ssh_key_name": regional_data["ssh_key_name"],
            "subnet_id": random.choice(regional_data["az_to_subnet_map"][selected_az]),
            "availability_zone": selected_az,
        }

        return result

    def provision_stackset(
        self,
        account,
        region,
        instance_type,
        operating_system,
        expiry,
        instance_name,
        user,
        username,
        email,
        group,
    ):
        sfn_client = boto3.client("stepfunctions")
        response = sfn_client.start_execution(
            stateMachineArn=self.provision_sfn_arn,
            input=json.dumps(
                {
                    "account": account,
                    "region": region,
                    "instance_type": instance_type,
                    "operating_system": operating_system,
                    "expiry": expiry.isoformat(),
                    "instance_name": instance_name,
                    "user": user,
                    "username": username,
                    "email": email,
                    "group": group,
                }
            ),
        )
        return response["executionArn"]

    def monitor_update(self, stackset_id, update_level, operation_id=""):
        # Kick off the SFN that will monitor the running SS and update its
        # state entry when update completes.

        sfn_client = boto3.client("stepfunctions")
        sfn_client.start_execution(
            stateMachineArn=self.update_sfn_arn,
            input=json.dumps(
                {
                    "stackset_id": stackset_id,
                    "update_level": update_level.value,
                    "operation_id": operation_id,
                }
            ),
        )

    def send_error_sns_message(self, stackset_id):
        sns_client = boto3.client("sns")
        sns_client.publish(
            TopicArn=self.error_topic_arn,
            Message=json.dumps(
                {
                    "message": f"Error provisioning the stackset {stackset_id}",
                }
            ),
        )

    def serialize_state_table_row(self, item):
        def nullable_get(item, key):
            return item[key]["S"] if key in item else None

        return {
            "stackset_id": item["stacksetID"]["S"],
            "expiry": item["expiry"]["S"],
            "extension_count": int(item["extensionCount"]["N"]),
            "username": item["username"]["S"],
            "email": item["email"]["S"],
            "group": item["group"]["S"],
            "account": nullable_get(item, "account"),
            "instance_name": nullable_get(item, "instanceName"),
            "instance_status": nullable_get(item, "instanceStatus"),
            "instance_type": nullable_get(item, "instanceType"),
            "operating_system": nullable_get(item, "operatingSystem"),
            "private_ip": nullable_get(item, "privateIp"),
            "region": nullable_get(item, "region"),
            "connection_protocol": nullable_get(item, "connectionProtocol"),
            "instance_id": nullable_get(item, "instanceId"),
            "availability_zone": nullable_get(item, "availabilityZone"),
        }

    def get_all_stacksets(self):
        dynamodb_client = boto3.client("dynamodb")
        results = dynamodb_client.scan(
            TableName=self.state_table_name,
        )

        return [self.serialize_state_table_row(item) for item in results["Items"]]

    def get_user_stacksets(self, email, permissions, is_superuser):
        dynamodb_client = boto3.client("dynamodb")
        results = dynamodb_client.scan(
            TableName=self.state_table_name,
        )

        results = [self.serialize_state_table_row(item) for item in results["Items"]]
        filtered_results = [entry for entry in results if is_superuser or entry["email"] == email]

        # annotate stacksets with permission details
        for instance_data in filtered_results:
            group = instance_data["group"]
            account = instance_data["account"]
            region = instance_data["region"]
            extension_count = instance_data["extension_count"]

            max_extension_count = permissions.get(group, {}).get("max_extension_count", None)
            if is_superuser:
                instance_data["can_extend"] = True
            elif max_extension_count is not None:
                instance_data["can_extend"] = extension_count < max_extension_count

            # Prepare the instance types that the current instance can be updated to
            group_instance_types = permissions[instance_data["group"]]["instance_types"]
            instance_az = instance_data["availability_zone"]

            if instance_az:
                region_params = self.get_params_for_region(account_id=account, region=region)
                all_instance_types = region_params["azs_to_instance_types"][instance_az]

                available_instance_types = list(set(group_instance_types).intersection(set(all_instance_types)))
            else:
                available_instance_types = group_instance_types

            instance_data["available_instance_types"] = available_instance_types

        return filtered_results

    def get_one_stack_set(self, stackset_id):
        dynamodb_client = boto3.client("dynamodb")
        state_data = dynamodb_client.get_item(TableName=self.state_table_name, Key={"stacksetID": {"S": stackset_id}})[
            "Item"
        ]
        return self.serialize_state_table_row(state_data)

    def update_stackset_state_entry(self, stackset_id, data):
        # Data: list of dicts with "field_name" and "value"
        dynamodb_client = boto3.client("dynamodb")

        # from https://stackoverflow.com/a/62030403
        update_expression_list = ["set "]
        update_values = dict()

        for entry in data:
            field_name = entry["field_name"]
            value = entry["value"]
            update_expression_list.append(f" {field_name} = :{field_name},")
            update_values[f":{field_name}"] = {"S": value}

        # Remove the trailing comma
        update_expression = "".join(update_expression_list)[:-1]

        updated_entry = dynamodb_client.update_item(
            TableName=self.state_table_name,
            Key={"stacksetID": {"S": stackset_id}},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=update_values,
            ReturnValues="ALL_NEW",
        )

        return self.serialize_state_table_row(updated_entry["Attributes"])

    def get_owned_stacksets(self, email, is_superuser=False):
        client = boto3.client("dynamodb")

        # For superusers, return all created instances
        # For other users, filter the results by email
        filter_kwargs = dict(
            FilterExpression="email = :val",
            ExpressionAttributeValues={":val": {"S": email}},
        )
        if is_superuser:
            filter_kwargs = {}

        results = client.scan(TableName=self.state_table_name, **filter_kwargs)

        return [self.serialize_state_table_row(item) for item in results["Items"]]

    def create_remote_role_session(self, account_id):
        sts_client = boto3.client("sts")
        response = sts_client.assume_role(
            RoleArn=f"arn:aws:iam::{account_id}:role/{self.cross_account_role_name}",
            RoleSessionName=f"{account_id}-{self.cross_account_role_name}",
        )
        remote_account_boto3 = boto3.Session(
            aws_access_key_id=response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
            aws_session_token=response["Credentials"]["SessionToken"],
        )
        return remote_account_boto3

    def get_remote_client(self, account_id, region, service):
        remote_session = self.create_remote_role_session(account_id)
        remote_client = remote_session.client(service, region_name=region)

        return remote_client

    def parse_stack_outputs(self, original_outputs):
        # Stack outputs are a list of dicts, convert to a mapping dict
        return {x["OutputKey"]: x["OutputValue"] for x in original_outputs}

    def fetch_stackset_instances(self, stackset_id, acceptable_statuses=INSTANCES_STACK_STATUSES):
        client = boto3.client("cloudformation")

        stack_instances = client.list_stack_instances(StackSetName=stackset_id)

        for instance in stack_instances["Summaries"]:
            account_id = instance["Account"]
            region = instance["Region"]
            stack_id = instance.get("StackId")

            if not stack_id:
                # Could be a stackset that has failed to provision, could be a timing issue
                # if this is called between creating the stackset and the stack instance being created
                continue

            stack_client = self.get_remote_client(account_id=account_id, region=region, service="cloudformation")
            described_stacks = stack_client.describe_stacks(StackName=stack_id)

            current_stack = described_stacks["Stacks"][0]

            stack_status = current_stack["StackStatus"]
            if acceptable_statuses and stack_status not in acceptable_statuses:
                continue

            # Convert the stack's params and outputs lists to dicts for easier access
            param_dict = {x["ParameterKey"]: x["ParameterValue"] for x in current_stack["Parameters"]}

            current_result = {
                "stackset_id": stackset_id,
                "account_id": account_id,
                "region": region,
                "operatingSystemName": param_dict.get("OperatingSystemName"),
                "instanceType": param_dict["InstanceType"],
                "instanceName": param_dict["InstanceName"],
                "connectionProtocol": param_dict["ConnectionProtocol"],
                "private_ip": None,
            }

            self.logger.info(f"fetch_stackset_instances {instance=}")
            if (
                instance["Status"] == SYNCHRONIZED_STATUS
                and instance["StackInstanceStatus"]["DetailedStatus"] not in INCOMPLETE_DETAILED_STATUS
            ):
                output_dict = self.parse_stack_outputs(current_stack["Outputs"])

                current_result = {
                    **current_result,
                    "private_ip": output_dict["PrivateIp"],
                    "instance_id": output_dict["InstanceID"],
                }

            yield current_result

    def get_instance_details(self, stacksets):
        results = []

        for stackset in stacksets:
            stackset_id = stackset["stackset_id"]
            expiry = stackset["expiry"]
            stack_username = stackset["username"]
            stack_email = stackset["email"]
            group = stackset["group"]

            for instance_data in self.fetch_stackset_instances(stackset_id=stackset_id):
                instance_data["expiry"] = expiry
                instance_data["username"] = stack_username
                instance_data["email"] = stack_email
                instance_data["group"] = group

                results.append(instance_data)

        results = self.annotate_with_instance_state(instances=results)

        return results

    def annotate_with_instance_state(self, instances):
        """Get the status of each instance"""
        # Get the region of each instance
        region_to_instances = defaultdict(list)
        for item in instances:
            if "instance_id" in item:
                region_to_instances[(item["account_id"], item["region"])].append(item["instance_id"])

        self.logger.info(f"annotate_with_instance_state: {region_to_instances=}")
        self.logger.info(f"annotate_with_instance_state: {instances=}")
        # Describe instances per region to get their current state
        state_dict = {}
        for (account_id, region), instance_ids in region_to_instances.items():
            ec2_client = self.get_remote_client(account_id=account_id, region=region, service="ec2")
            described_instances = ec2_client.describe_instances(InstanceIds=instance_ids)

            self.logger.info(f"annotate_with_instance_state: {described_instances=}")
            for instance in described_instances.get("Reservations", []):
                if len(instance["Instances"]) > 1:
                    raise ValueError(f"More than one instance running: {instance}")
                instance_id = instance["Instances"][0]["InstanceId"]
                state = instance["Instances"][0]["State"]["Name"]

                state_dict[instance_id] = state

        # Annotate the instances with their state
        for item in instances:
            if item.get("instance_id") and item["instance_id"] in state_dict:
                item["state"] = state_dict[item["instance_id"]]

        return instances

    def get_stackset_state_data(self, stackset_id):
        client = boto3.client("dynamodb")
        item = client.get_item(TableName=self.state_table_name, Key={"stacksetID": {"S": stackset_id}})

        if "Item" not in item:
            return {}

        result = self.serialize_state_table_row(item["Item"])
        return result

    def initiate_stackset_deprovisioning(self, stackset_id, owner_email):
        sfn_client = boto3.client("stepfunctions")
        response = sfn_client.start_execution(
            stateMachineArn=self.cleanup_sfn_arn,
            input=json.dumps(
                {
                    "stackset_id": stackset_id,
                    "stackset_email": owner_email,
                }
            ),
        )
        return response

    def mark_stackset_as_updating(self, stackset_id):
        return self.update_stackset_state_entry(
            stackset_id=stackset_id,
            data=[
                {"field_name": "instanceStatus", "value": EC2_INSTANCE_PENDING_STATE},
            ],
        )

    def update_stackset(self, stackset_id, **kwargs):
        cf_client = boto3.client("cloudformation")
        self.logger.info(f"{stackset_id=}, {kwargs=}")

        # Get current parameters and override the ones provided
        current_stackset = cf_client.describe_stack_set(StackSetName=stackset_id)["StackSet"]
        current_params = current_stackset["Parameters"]
        current_capabilities = current_stackset["Capabilities"]
        params = [
            *[
                {"ParameterKey": param["ParameterKey"], "UsePreviousValue": True}
                for param in current_params
                if param["ParameterKey"] not in kwargs.keys()
            ],
            *[{"ParameterKey": key, "ParameterValue": value} for key, value in kwargs.items()],
        ]

        self.mark_stackset_as_updating(stackset_id=stackset_id)

        # Update stack set
        operation = cf_client.update_stack_set(
            StackSetName=stackset_id,
            UsePreviousTemplate=True,
            Parameters=params,
            Capabilities=current_capabilities,
            AdministrationRoleARN=self.admin_role_arn,
            ExecutionRoleName=self.execution_role_name,
        )

        self.monitor_update(
            stackset_id=stackset_id,
            update_level=UpdateLevel.STACKSET_LEVEL,
            operation_id=operation["OperationId"],
        )

    def stop_instance(self, stackset_id, account_id, region_name, instance_id):
        self.mark_stackset_as_updating(stackset_id=stackset_id)

        client = self.get_remote_client(account_id=account_id, region=region_name, service="ec2")
        client.stop_instances(InstanceIds=[instance_id])

        self.monitor_update(stackset_id=stackset_id, update_level=UpdateLevel.INSTANCE_LEVEL)

    def start_instance(self, stackset_id, account_id, region_name, instance_id):
        self.mark_stackset_as_updating(stackset_id=stackset_id)

        client = self.get_remote_client(account_id=account_id, region=region_name, service="ec2")
        client.start_instances(InstanceIds=[instance_id])

        self.monitor_update(stackset_id=stackset_id, update_level=UpdateLevel.INSTANCE_LEVEL)

    def update_instance_expiry(self, stackset_id, expiry, extension_count):
        client = boto3.client("dynamodb")
        client.update_item(
            TableName=self.state_table_name,
            Key={"stacksetID": {"S": stackset_id}},
            UpdateExpression="SET extensionCount = :extensionCount, expiry = :expiry",
            ExpressionAttributeValues={
                ":extensionCount": {"N": str(extension_count)},
                ":expiry": {"S": expiry.isoformat()},
            },
        )

    def create_stack_set(
        self,
        project_name,
        tags,
        account,
        region,
        instance_type,
        operating_system,
        expiry,
        email,
        group,
        instance_name,
        username,
    ):
        # Get the remaining params from permissions
        os_config = self.get_os_config(
            group_name=group,
            os_name=operating_system,
        )

        # Create the stackset
        template_url = f"https://s3.amazonaws.com/{self.cfn_data_bucket}/{os_config['template-filename']}"

        client = boto3.client("cloudformation")
        response = client.create_stack_set(
            StackSetName=f"{project_name}-stackset-{str(uuid4())}",
            Description=f"Provisioning compute instances using {project_name}",
            TemplateURL=template_url,
            Parameters=[
                {
                    "ParameterKey": "ProjectName",
                    "ParameterValue": project_name,
                },
                {
                    "ParameterKey": "OperatingSystemName",
                    "ParameterValue": operating_system,
                },
                {
                    "ParameterKey": "InstanceType",
                    "ParameterValue": instance_type,
                },
                {
                    "ParameterKey": "InstanceExpiry",
                    "ParameterValue": expiry.isoformat(),
                },
                {
                    "ParameterKey": "ConnectionProtocol",
                    "ParameterValue": os_config["connection-protocol"],
                },
                {
                    "ParameterKey": "UserDataBucket",
                    "ParameterValue": self.cfn_data_bucket,
                },
                {
                    "ParameterKey": "UserDataFile",
                    "ParameterValue": os_config["user-data-file"],
                },
                {
                    "ParameterKey": "AMI",
                    "ParameterValue": os_config["region-map"][account][region]["ami"],
                },
                {
                    "ParameterKey": "SecurityGroupId",
                    "ParameterValue": os_config["region-map"][account][region]["security-group"],
                },
                {
                    "ParameterKey": "InstanceProfileName",
                    "ParameterValue": os_config["region-map"][account][region]["instance-profile-name"],
                },
                # Tags
                {
                    "ParameterKey": "InstanceName",
                    "ParameterValue": instance_name,
                },
                {
                    "ParameterKey": "TagNameOne",
                    "ParameterValue": tags[0]["tag-name"],
                },
                {
                    "ParameterKey": "TagValueOne",
                    "ParameterValue": tags[0]["tag-value"],
                },
                {
                    "ParameterKey": "TagNameTwo",
                    "ParameterValue": tags[1]["tag-name"],
                },
                {
                    "ParameterKey": "TagValueTwo",
                    "ParameterValue": tags[1]["tag-value"],
                },
                # Provide empty string as the temporary values of the parameters,
                # to be overridden using config values fetched
                {
                    "ParameterKey": "VPCID",
                    "ParameterValue": "",
                },
                {
                    "ParameterKey": "SubnetId",
                    "ParameterValue": "",
                },
                {
                    "ParameterKey": "SSHKeyName",
                    "ParameterValue": "",
                },
            ],
            AdministrationRoleARN=self.admin_role_arn,
            ExecutionRoleName=self.execution_role_name,
            PermissionModel="SELF_MANAGED",
        )
        stackset_id = response["StackSetId"]

        region_params = self.get_provisioning_params_for_region(
            account_id=account, region=region, instance_type=instance_type
        )

        create_operation = client.create_stack_instances(
            StackSetName=stackset_id,
            Accounts=[account],
            Regions=[region],
            ParameterOverrides=[
                {
                    "ParameterKey": "VPCID",
                    "ParameterValue": region_params["vpc_id"],
                },
                {
                    "ParameterKey": "SubnetId",
                    "ParameterValue": region_params["subnet_id"],
                },
                {
                    "ParameterKey": "SSHKeyName",
                    "ParameterValue": region_params["ssh_key_name"],
                },
            ],
        )

        # Save stackset state to dynamodb
        dynamodb_client = boto3.client("dynamodb")
        dynamodb_client.put_item(
            TableName=self.state_table_name,
            Item={
                "stacksetID": {"S": stackset_id},
                "username": {"S": username},
                "email": {"S": email},
                "group": {"S": group},
                "extensionCount": {"N": "0"},
                "expiry": {"S": expiry.isoformat()},
                "account": {"S": account},
                "region": {"S": region},
                "instanceType": {"S": instance_type},
                "operatingSystem": {"S": operating_system},
                "privateIp": {"S": ""},
                "instanceStatus": {"S": ""},
                "instanceName": {"S": instance_name},
                "connectionProtocol": {"S": os_config["connection-protocol"]},
                "availabilityZone": {"S": region_params["availability_zone"]},
            },
        )

        return stackset_id, create_operation["OperationId"]

    def check_stackset_complete(self, stackset_id, operation_id):
        cf_client = boto3.client("cloudformation")

        stack_operation = cf_client.describe_stack_set_operation(StackSetName=stackset_id, OperationId=operation_id)
        self.logger.info(f"check_stackset_update_complete: {stack_operation=}")

        if stack_operation["StackSetOperation"]["Status"] in STACKSET_OPERATION_INCOMPLETE_STATUSES:
            raise StackSetExecutionInProgressException("StackSet operation still in progress")

        stack_instances = cf_client.list_stack_instances(StackSetName=stackset_id)
        for instance in stack_instances["Summaries"]:
            # Stack instances are in progress of being updated
            if (
                instance["Status"] != SYNCHRONIZED_STATUS
                or instance["StackInstanceStatus"]["DetailedStatus"] != SUCCESS_DETAILED_STATUS
            ):
                raise StackSetExecutionInProgressException()

    def check_stackset_update_complete(self, stackset_id, update_level, operation_id):
        # Update level can be: stackset (updating params) or instance (updating instance state)
        self.logger.info(f"check_stackset_update_complete: {stackset_id=} {update_level=} {operation_id=}")
        cf_client = boto3.client("cloudformation")

        if operation_id:
            stack_operation = cf_client.describe_stack_set_operation(StackSetName=stackset_id, OperationId=operation_id)
            self.logger.info(f"check_stackset_update_complete: {stack_operation=}")

            if stack_operation["StackSetOperation"]["Status"] in STACKSET_OPERATION_INCOMPLETE_STATUSES:
                raise StackSetUpdateInProgressException("StackSet operation still in progress")

        stack_instances = cf_client.list_stack_instances(StackSetName=stackset_id)
        self.logger.info(f"check_stackset_update_complete: {stack_instances=}")
        if len(stack_instances["Summaries"]) != 1:
            raise InvalidApplicationState(message="Unexpected number of stack instances")

        stack_instances = stack_instances["Summaries"][0]
        # Stack instances are in progress of being updated
        if (
            stack_instances["Status"] != SYNCHRONIZED_STATUS
            or stack_instances["StackInstanceStatus"]["DetailedStatus"] != SUCCESS_DETAILED_STATUS
        ):
            raise StackSetUpdateInProgressException("Stack Instances is being updated")

        # Check the state of the running ec2 instances
        account_id = stack_instances["Account"]
        region = stack_instances["Region"]
        stack_id = stack_instances["StackId"]

        stack_client = self.get_remote_client(account_id=account_id, region=region, service="cloudformation")
        described_stacks = stack_client.describe_stacks(StackName=stack_id)
        self.logger.info(f"check_stackset_update_complete: {described_stacks=}")

        current_stack = described_stacks["Stacks"][0]
        output_dict = self.parse_stack_outputs(current_stack["Outputs"])
        instance_id = output_dict["InstanceID"]

        ec2_client = self.get_remote_client(account_id=account_id, region=region, service="ec2")
        described_instances = ec2_client.describe_instances(InstanceIds=[instance_id])

        if (
            len(described_instances.get("Reservations", [])) != 1
            or len(described_instances["Reservations"][0]["Instances"]) != 1
        ):
            self.logger.info(f"{described_instances=}")
            raise InvalidApplicationState(message="Unexpected number of ec2 instances")

        ec2_instance = described_instances["Reservations"][0]["Instances"][0]
        state = ec2_instance["State"]["Name"]

        if state not in EC2_INSTANCE_FINAL_STATES:
            raise StackSetUpdateInProgressException("EC2 instance is still being updated.")

    def delete_stack_instance(self, stackset_id, account_id, region):
        cfn_client = boto3.client("cloudformation")

        response = cfn_client.delete_stack_instances(
            StackSetName=stackset_id,
            Accounts=[account_id],
            Regions=[region],
            RetainStacks=False,
        )

        return response["OperationId"]

    def delete_stack_set(self, stackset_id):
        cfn_client = boto3.client("cloudformation")
        cfn_client.delete_stack_set(StackSetName=stackset_id)

        # Remove the StackSet record from the state table
        dynamodb_client = boto3.client("dynamodb")
        response = dynamodb_client.delete_item(
            TableName=self.state_table_name,
            Key={"stacksetID": {"S": stackset_id}},
        )

        return response
