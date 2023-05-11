import functools
import json
import logging
from collections import defaultdict
from datetime import datetime

import boto3

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


class APIException(Exception):
    status_code = 500
    message = "Server error"

    def __init__(self, message=None, status_code=None):
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code


class PermissionsMissing(APIException):
    status_code = 400


class UnauthorizedForInstanceError(APIException):
    status_code = 400
    message = "You're not authorized to modify this instance."


class InstanceUpdateError(APIException):
    status_code = 400
    message = "Instance update has failed."


class InvalidArgumentsError(APIException):
    status_code = 400


class StackSetCreationException(Exception):
    pass


class CrossAccountStackSetException(Exception):
    pass


class StackSetExecutionInProgressException(Exception):
    # NB: This should not inherit from APIException as the exception is used to signal
    # retries in the step function state machine
    pass


def exception_handler(handler):
    """
    Wrapper for handling exceptions raised by the applications and converting them to error messages.
    """

    @functools.wraps(handler)
    def inner(*args, **kwargs):
        try:
            return handler(*args, **kwargs)
        except APIException as e:
            return {
                "statusCode": e.status_code,
                "body": json.dumps({"message": e.message}),
                "headers": {"Content-Type": "application/json"},
            }

    return inner


def audit_logging_handler(handler):
    """
    Wrapper for logging calls parameters and results.
    """

    @functools.wraps(handler)
    def inner(*args, **kwargs):
        # Ignoring the Lambda context for logging purposes
        try:
            result = handler(*args, **kwargs)
            logger.info({"event": args[0], "response": result, "type": "SUCCESS", "audit": 1})
            return result
        except Exception as e:  # noqa: B902
            logger.info({"event": args[0], "response": str(e), "type": "ERROR", "audit": 1})
            raise

    return inner


def get_account_id():
    return boto3.client("sts").get_caller_identity().get("Account")


def get_claims(request):
    context = json.loads(request.headers["X-Amzn-Request-Context"])
    claims = context["authorizer"]["jwt"]["claims"]

    if "email" not in claims or not claims["email"]:
        raise ValueError("The JWT is missing the 'email' claim value.")

    if "profile" not in claims or not claims["profile"]:
        raise ValueError("The JWT is missing the 'profile' claim value.")

    if "nickname" not in claims or not claims["nickname"]:
        raise ValueError("The JWT is missing the 'nickname' claim value.")

    is_superuser = claims.get("custom:is_superuser", False) == "1"

    return {
        "email": claims["email"],
        "group": claims["profile"],
        "username": claims["nickname"],
        "is_superuser": is_superuser,
        "claims": claims,
    }


def get_permissions_for_group(table_name, group_name):
    client = boto3.client("dynamodb")
    result = client.get_item(TableName=table_name, Key={"group": {"S": group_name}})

    if "Item" not in result:
        raise PermissionsMissing(message=f"The group '{group_name}' does not have any permissions associated with it.")

    item = result["Item"]
    result = {
        "instance_types": item["instanceTypes"]["SS"],
        "operating_systems": json.loads(item["operatingSystems"]["S"]),
        # Even though DynamoDB treats Number type as numeric internally, but accepts and returns them as strings,
        # hence the need to cast it explicitly
        # https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.NamingRulesDataTypes.html#HowItWorks.DataTypes
        "max_days_to_expiry": int(item["maxDaysToExpiry"]["N"]),
        "max_instance_count": int(item["maxInstanceCount"]["N"]),
        "max_extension_count": int(item["maxExtensionCount"]["N"]),
    }

    region_map = defaultdict(list)
    for item in result["operating_systems"]:
        for region_name in item["region-map"].keys():
            region_map[region_name] += [item["name"]]

    result["region_map"] = region_map

    return result


def get_os_config(table_name, group_name, os_name):
    client = boto3.client("dynamodb")
    result = client.get_item(TableName=table_name, Key={"group": {"S": group_name}})

    if "Item" not in result:
        raise PermissionsMissing(message=f"The group '{group_name}' does not have any permissions associated with it.")

    os_configs = json.loads(result["Item"]["operatingSystems"]["S"])
    target_configs = [config for config in os_configs if config["name"] == os_name]
    if not target_configs:
        raise PermissionsMissing(message=f"The group '{group_name}' does not have any permissions associated with it.")

    return target_configs[0]


def get_params_for_region(table_name, region):
    client = boto3.client("dynamodb")
    regional_data = client.get_item(TableName=table_name, Key={"region": {"S": region}})

    if "Item" not in regional_data:
        raise PermissionsMissing(message=f"The region '{region}' does not have any configuration associated with it.")

    result = {
        "vpc_id": regional_data["Item"]["vpcId"]["S"],
        "ssh_key_name": regional_data["Item"]["sshKeyName"]["S"],
        "subnet_id": regional_data["Item"]["subnetId"]["SS"],
    }

    return result


def provision_stackset(
    provision_sfn_arn,
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
        stateMachineArn=provision_sfn_arn,
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


def send_sns_message(topic_arn, stackset_id):
    sns_client = boto3.client("sns")
    sns_client.publish(
        TopicArn=topic_arn,
        Message=json.dumps(
            {
                "message": f"Error provisioning the stackset {stackset_id}",
            }
        ),
    )


def get_owned_stacksets(table_name, email, is_superuser=False):
    client = boto3.client("dynamodb")

    # For superusers, return all created instances
    # For other users, filter the results by email
    filter_kwargs = dict(
        FilterExpression="email = :val",
        ExpressionAttributeValues={":val": {"S": email}},
    )
    if is_superuser:
        filter_kwargs = {}

    result = client.scan(TableName=table_name, **filter_kwargs)

    stacksets = []
    for item in result["Items"]:
        stacksets.append(
            {
                "stackset_id": item["stacksetID"]["S"],
                "expiry": item["expiry"]["S"],
                "extension_count": int(item["extensionCount"]["N"]),
                "username": item["username"]["S"],
                "email": item["email"]["S"],
            }
        )

    return stacksets


def fetch_stackset_instances(stackset_id, acceptable_statuses=INSTANCES_STACK_STATUSES):
    current_account_id = get_account_id()

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

        if account_id != current_account_id:
            raise CrossAccountStackSetException("Cross-account instances currently not supported")

        stack_client = boto3.client("cloudformation", region_name=region)
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


def get_instance_details(stacksets, max_extension_count=None, is_superuser=False):
    results = []

    for stackset in stacksets:
        stackset_id = stackset["stackset_id"]
        expiry = stackset["expiry"]
        stack_username = stackset["username"]
        stack_email = stackset["email"]
        extension_count = stackset["extension_count"]

        for instance_data in fetch_stackset_instances(stackset_id=stackset_id):
            instance_data["expiry"] = expiry
            instance_data["username"] = stack_username
            instance_data["email"] = stack_email

            if is_superuser:
                instance_data["can_extend"] = True
            elif max_extension_count is not None:
                instance_data["can_extend"] = extension_count < max_extension_count

            results.append(instance_data)

    results = annotate_with_instance_state(instances=results)
    return results


def annotate_with_instance_state(instances):
    """Get the status of each instance"""
    # Get the region of each instance
    region_to_instances = defaultdict(list)
    for item in instances:
        if "instance_id" in item:
            region_to_instances[item["region"]].append(item["instance_id"])

    # Describe instances per region to get their current state
    state_dict = {}
    for region, instance_ids in region_to_instances.items():
        ec2_client = boto3.client("ec2", region_name=region)
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


def get_stackset_state_data(stackset_id, table_name):
    client = boto3.client("dynamodb")
    item = client.get_item(TableName=table_name, Key={"stacksetID": {"S": stackset_id}})

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


def initiate_stackset_deprovisioning(stackset_id, cleanup_sfn_arn, owner_email):
    sfn_client = boto3.client("stepfunctions")
    response = sfn_client.start_execution(
        stateMachineArn=cleanup_sfn_arn,
        input=json.dumps(
            {
                "stackset_id": stackset_id,
                "stackset_email": owner_email,
            }
        ),
    )
    return response


def update_stackset(stackset_id, **kwargs):
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
    )
