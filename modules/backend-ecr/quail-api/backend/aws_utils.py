from uuid import uuid4
import json
import logging
from collections import defaultdict
from datetime import datetime
import random

import boto3

from backend.exceptions import PermissionsMissing, StackSetExecutionInProgressException

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# StackSet operations incomplete statuses
# All listed under https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_StackSetOperationSummary.html
STACKSET_OPERATION_INCOMPLETE_STATUSES = {"QUEUED", "RUNNING", "STOPPING"}
# Stack Instance Statuses
# All listed under https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_StackInstanceSummary.html
SYNCHRONIZED_STATUS = "CURRENT"
# Stack Instance Detailed Statuses
# All listed under https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_StackInstanceComprehensiveStatus.html  # noqa
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


class AwsUtils:
    def __init__(
        self,
        permissions_table_name,
        regional_data_table_name,
        state_table_name,
        cross_account_role_name,
        admin_group_name,
        provision_sfn_arn,
        error_topic_arn,
        cleanup_sfn_arn,
        cfn_data_bucket,
        execution_role_name,
        admin_role_arn,
    ):
        self.permissions_table_name = permissions_table_name
        self.regional_data_table_name = regional_data_table_name
        self.state_table_name = state_table_name

        self.cleanup_sfn_arn = cleanup_sfn_arn
        self.provision_sfn_arn = provision_sfn_arn

        self.admin_group_name = admin_group_name
        self.error_topic_arn = error_topic_arn
        self.cross_account_role_name = cross_account_role_name
        self.cfn_data_bucket = cfn_data_bucket
        self.execution_role_name = execution_role_name
        self.admin_role_arn = admin_role_arn

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

    def get_permissions_for_groups(self, groups):
        client = boto3.client("dynamodb")

        result = {
            "instance_types": [],
            "operating_systems": [],
            "max_days_to_expiry": 0,
            "max_instance_count": 0,
            "max_extension_count": 0,
        }

        for group_name in groups:
            fetched = client.get_item(TableName=self.permissions_table_name, Key={"group": {"S": group_name}})

            if "Item" not in fetched:
                logger.info(f"The group '{group_name}' does not have any permissions associated with it.")
                continue

            item = fetched["Item"]

            result = {
                "instance_types": list(set([*result["instance_types"], *item["instanceTypes"]["SS"]])),
                "operating_systems": [
                    *result["operating_systems"],
                    *json.loads(item["operatingSystems"]["S"]),
                ],
                # Even though DynamoDB treats Number type as numeric internally, but accepts and returns them
                # as strings hence the need to cast the values explicitly
                # https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.NamingRulesDataTypes.html#HowItWorks.DataTypes
                "max_days_to_expiry": max([result["max_days_to_expiry"], int(item["maxDaysToExpiry"]["N"])]),
                "max_instance_count": max([result["max_instance_count"], int(item["maxInstanceCount"]["N"])]),
                "max_extension_count": max([result["max_extension_count"], int(item["maxExtensionCount"]["N"])]),
            }

        region_map = defaultdict(lambda: defaultdict(list))
        for os_item in result["operating_systems"]:
            for account_id in os_item["region-map"].keys():
                account_map = os_item["region-map"][account_id]
                for region_name in account_map.keys():
                    region_map[account_id][region_name] += [os_item["name"]]

        result["region_map"] = region_map

        return result

    def get_os_config(self, groups, os_name):
        client = boto3.client("dynamodb")

        result = []
        for group_name in groups:
            fetched = client.get_item(TableName=self.permissions_table_name, Key={"group": {"S": group_name}})

            if "Item" not in fetched:
                logger.info(f"The group '{group_name}' does not have any permissions associated with it.")
                continue

            os_configs = json.loads(fetched["Item"]["operatingSystems"]["S"])
            target_configs = [config for config in os_configs if config["name"] == os_name]
            result = [*result, *target_configs]

        if not result:
            raise PermissionsMissing(message=f"Could not find the permission for '{os_name}' in groups: {groups}.")

        if len(result) > 1:
            logger.info(f"Multiple permissions for '{os_name}' in groups: {groups}.")

        return result[0]

    def get_params_for_region(self, account_id, region):
        client = boto3.client("dynamodb")
        regional_data = client.get_item(
            TableName=self.regional_data_table_name,
            Key={"accountId": {"S": account_id}, "region": {"S": region}},
        )

        if "Item" not in regional_data:
            raise PermissionsMissing(
                message=f"The region '{region}' does not have any configuration associated with it."
            )

        result = {
            "vpc_id": regional_data["Item"]["vpcId"]["S"],
            "ssh_key_name": regional_data["Item"]["sshKeyName"]["S"],
            "subnet_id": regional_data["Item"]["subnetId"]["SS"],
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
        groups,
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
                    "groups": groups,
                }
            ),
        )
        return response["executionArn"]

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
        return {
            "stackset_id": item["stacksetID"]["S"],
            "expiry": item["expiry"]["S"],
            "extension_count": int(item["extensionCount"]["N"]),
            "username": item["username"]["S"],
            "email": item["email"]["S"],
        }

    def get_all_stack_sets(self):
        dynamodb_client = boto3.client("dynamodb")
        results = dynamodb_client.scan(
            TableName=self.state_table_name,
        )

        return [self.serialize_state_table_row(item) for item in results["Items"]]

    def get_one_stack_set(self, stackset_id):
        dynamodb_client = boto3.client("dynamodb")
        state_data = dynamodb_client.get_item(TableName=self.state_table_name, Key={"stacksetID": {"S": stackset_id}})[
            "Item"
        ]
        return self.serialize_state_table_row(state_data)

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

    def assume_remote_role(self, account_id):
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

            remote_account_boto3 = self.assume_remote_role(account_id=account_id)
            stack_client = remote_account_boto3.client("cloudformation", region_name=region)
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

            if (
                instance["Status"] == SYNCHRONIZED_STATUS
                and instance["StackInstanceStatus"]["DetailedStatus"] not in INCOMPLETE_DETAILED_STATUS
            ):
                current_outputs = current_stack["Outputs"]
                output_dict = {x["OutputKey"]: x["OutputValue"] for x in current_outputs}

                current_result = {
                    **current_result,
                    "private_ip": output_dict["PrivateIp"],
                    "instance_id": output_dict["InstanceID"],
                }

            yield current_result

    def get_instance_details(self, stacksets, max_extension_count=None, is_superuser=False):
        results = []

        for stackset in stacksets:
            stackset_id = stackset["stackset_id"]
            expiry = stackset["expiry"]
            stack_username = stackset["username"]
            stack_email = stackset["email"]
            extension_count = stackset["extension_count"]

            for instance_data in self.fetch_stackset_instances(stackset_id=stackset_id):
                instance_data["expiry"] = expiry
                instance_data["username"] = stack_username
                instance_data["email"] = stack_email

                if is_superuser:
                    instance_data["can_extend"] = True
                elif max_extension_count is not None:
                    instance_data["can_extend"] = extension_count < max_extension_count

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

        # Describe instances per region to get their current state
        state_dict = {}
        for (account_id, region), instance_ids in region_to_instances.items():
            remote_account_boto3 = self.assume_remote_role(account_id=account_id)
            ec2_client = remote_account_boto3.client("ec2", region_name=region)
            described_instances = ec2_client.describe_instances(InstanceIds=instance_ids)

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

        result = {
            "stackset_id": item["Item"]["stacksetID"]["S"],
            "username": item["Item"]["username"]["S"],
            "email": item["Item"]["email"]["S"],
            "extension_count": int(item["Item"]["extensionCount"]["N"]),
            "expiry": datetime.fromisoformat(item["Item"]["expiry"]["S"]),
        }
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

    def update_stackset(self, stackset_id, **kwargs):
        client = boto3.client("cloudformation")

        # Get current parameters and override the ones provided
        current_stackset = client.describe_stack_set(StackSetName=stackset_id)["StackSet"]
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

        # Update stack set
        client.update_stack_set(
            StackSetName=stackset_id,
            UsePreviousTemplate=True,
            Parameters=params,
            Capabilities=current_capabilities,
            AdministrationRoleARN=self.admin_role_arn,
            ExecutionRoleName=self.execution_role_name,
        )

    def stop_instance(self, account_id, region_name, instance_id):
        remote_boto3 = self.assume_remote_role(account_id=account_id)
        client = remote_boto3.client("ec2", region_name=region_name)
        client.stop_instances(InstanceIds=[instance_id])

    def start_instance(self, account_id, region_name, instance_id):
        remote_boto3 = self.assume_remote_role(account_id=account_id)
        client = remote_boto3.client("ec2", region_name=region_name)
        client.start_instances(InstanceIds=[instance_id])

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
        groups,
        instance_name,
        username,
    ):
        # Get the remaining params from permissions
        os_config = self.get_os_config(
            groups=groups,
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

        region_params = self.get_params_for_region(account_id=account, region=region)

        client.create_stack_instances(
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
                    "ParameterValue": random.choice(region_params["subnet_id"]),
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
                "extensionCount": {"N": "0"},
                "expiry": {"S": expiry.isoformat()},
            },
        )

        return stackset_id

    def check_stackset_complete(self, stack_name, error_if_no_operations):
        client = boto3.client("cloudformation")

        stack_operations = client.list_stack_set_operations(StackSetName=stack_name)
        if error_if_no_operations and not stack_operations["Summaries"]:
            # Fail if the stack operations are still not available
            raise StackSetExecutionInProgressException()

        for operation in stack_operations["Summaries"]:
            # The stackset operation hasn't completed
            if operation["Status"] in STACKSET_OPERATION_INCOMPLETE_STATUSES:
                raise StackSetExecutionInProgressException()

        stack_instances = client.list_stack_instances(StackSetName=stack_name)
        for instance in stack_instances["Summaries"]:
            # Stack instances are in progress of being updated
            if (
                instance["Status"] != SYNCHRONIZED_STATUS
                or instance["StackInstanceStatus"]["DetailedStatus"] != SUCCESS_DETAILED_STATUS
            ):
                raise StackSetExecutionInProgressException()

    def delete_stack_instance(self, stackset_id, account_id, region):
        cfn_client = boto3.client("cloudformation")

        response = cfn_client.delete_stack_instances(
            StackSetName=stackset_id,
            Accounts=[account_id],
            Regions=[region],
            RetainStacks=False,
        )

        return response

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
