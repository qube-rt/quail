from uuid import uuid4
import json
import random
from datetime import datetime

import boto3
from flask import request, current_app

from backend.aws_utils import (
    get_params_for_region,
    get_os_config,
    STACKSET_OPERATION_INCOMPLETE_STATUSES,
    SYNCHRONIZED_STATUS,
    SUCCESS_DETAILED_STATUS,
    send_sns_message,
    fetch_stackset_instances,
    initiate_stackset_deprovisioning,
)
from backend.email_utils import send_email
from backend.exceptions import (
    StackSetExecutionInProgressException,
)


def get_tags(user, tag_config):
    tags = []

    for tag in tag_config:
        if tag["tag-value"].startswith("$"):
            # Skip leading dollar sign
            attribute_key = tag["tag-value"][1:]
            tag["tag-value"] = user[attribute_key]

        tags.append(tag)

    return tags


def post_provision():
    # Get body params
    payload = request.json

    params = {
        "account": payload["account"],
        "region": payload["region"],
        "instance_type": payload["instance_type"],
        "os": payload["operating_system"],
        "expiry": datetime.fromisoformat(payload["expiry"]),
        "email": payload["email"],
        "user_group": payload["group"],
        "instance_name": payload["instance_name"],
        "user_claims": payload["user"],
        "username": payload["username"],
    }

    # read in data from environment
    project_name = current_app.config["PROJECT_NAME"]
    regional_metadata_table = current_app.config["DYNAMODB_REGIONAL_METADATA_TABLE_NAME"]
    state_table = current_app.config["DYNAMODB_STATE_TABLE_NAME"]
    permissions_table = current_app.config["DYNAMODB_PERMISSIONS_TABLE_NAME"]
    cfn_data_bucket = current_app.config["CFN_DATA_BUCKET"]
    tag_config = json.loads(current_app.config["TAG_CONFIG"])

    # The number of tags is hardcoded in the terraform template
    assert len(tag_config) == 2

    # Get the remaining params from permissions
    os_config = get_os_config(
        table_name=permissions_table,
        group_name=params["user_group"],
        os_name=params["os"],
    )

    # Evaluate tags
    tags = get_tags(user=params["user_claims"], tag_config=tag_config)

    # Create the stackset
    template_url = f"https://s3.amazonaws.com/{cfn_data_bucket}/{os_config['template-filename']}"

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
                "ParameterValue": params["os"],
            },
            {
                "ParameterKey": "InstanceType",
                "ParameterValue": params["instance_type"],
            },
            {
                "ParameterKey": "InstanceExpiry",
                "ParameterValue": params["expiry"].isoformat(),
            },
            {
                "ParameterKey": "ConnectionProtocol",
                "ParameterValue": os_config["connection-protocol"],
            },
            {
                "ParameterKey": "UserDataBucket",
                "ParameterValue": cfn_data_bucket,
            },
            {
                "ParameterKey": "UserDataFile",
                "ParameterValue": os_config["user-data-file"],
            },
            {
                "ParameterKey": "InstanceProfileName",
                "ParameterValue": os_config["instance-profile-name"],
            },
            {
                "ParameterKey": "AMI",
                "ParameterValue": os_config["region-map"][params["region"]]["ami"],
            },
            {
                "ParameterKey": "SecurityGroupId",
                "ParameterValue": os_config["region-map"][params["region"]]["security-group"],
            },
            # Tags
            {
                "ParameterKey": "InstanceName",
                "ParameterValue": params["instance_name"],
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
        # AdministrationRoleARN='string',
        # ExecutionRoleName='string',
        PermissionModel="SELF_MANAGED",
    )
    stackset_id = response["StackSetId"]

    region = params["region"]
    region_params = get_params_for_region(table_name=regional_metadata_table, region=region)

    client.create_stack_instances(
        StackSetName=stackset_id,
        Accounts=[params["account"]],
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
        TableName=state_table,
        Item={
            "stacksetID": {"S": stackset_id},
            "username": {"S": params["username"]},
            "email": {"S": params["email"]},
            "extensionCount": {"N": "0"},
            "expiry": {"S": params["expiry"].isoformat()},
        },
    )

    return {"stackset_id": stackset_id, "stackset_email": params["email"]}


def get_wait():
    stack_name = request.args.get("stackset_id")
    # Whether no operations should cause the function to error. It should be true when creating an instance
    # but false when waiting for delete operations to complete.
    error_if_no_operations = request.args.get("error_if_no_operations")

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

    return {}, 204


def post_notify_success():
    # read in data from environment
    project_name = current_app.config["PROJECT_NAME"]
    notification_email = current_app.config["NOTIFICATION_EMAIL"]
    state_table = current_app.config["DYNAMODB_STATE_TABLE_NAME"]

    # read in data passed to the lambda call
    payload = request.json
    stackset_id = payload["stackset_id"]
    stackset_email = payload["stackset_email"]

    # Get config from dynamodb
    dynamodb_client = boto3.client("dynamodb")
    state_data = dynamodb_client.get_item(TableName=state_table, Key={"stacksetID": {"S": stackset_id}})["Item"]

    for instance_data in fetch_stackset_instances(stackset_id=stackset_id):
        template_data = {
            "region": instance_data["region"],
            "os": instance_data["operatingSystemName"],
            "instance_type": instance_data["instanceType"],
            "instance_name": instance_data["instanceName"],
            "ip": instance_data["private_ip"],
            "expiry": datetime.fromisoformat(state_data["expiry"]["S"]).strftime("%-I %p %d %B"),
        }

        send_email(
            subject="Compute instance provisioned successfully",
            template_name="provision_success",
            template_data=template_data,
            source_email=f"Instance Provisioning ({project_name}) <{notification_email}>",
            to_email=stackset_email,
        )

    return {}, 204


def post_notify_failure():
    # read in data from environment
    project_name = current_app.config["PROJECT_NAME"]
    notification_email = current_app.config["NOTIFICATION_EMAIL"]
    admin_email = current_app.config["ADMIN_EMAIL"]
    sns_error_topic_arn = current_app.config["SNS_ERROR_TOPIC_ARN"]
    cleanup_sfn_arn = current_app.config["CLEANUP_SFN_ARN"]

    # read in data passed to the lambda call
    payload = request.json
    stackset_id = payload["stackset_id"]
    stackset_email = payload["stackset_email"]

    # send SNS failure notification
    send_sns_message(topic_arn=sns_error_topic_arn, stackset_id=stackset_id)

    for instance_data in fetch_stackset_instances(stackset_id=stackset_id, acceptable_statuses=None):
        template_data = {
            "region": instance_data["region"],
            "os": instance_data["operatingSystemName"],
            "instance_type": instance_data["instanceType"],
            "instance_name": instance_data["instanceName"],
        }

        response = send_email(
            subject="Error provisioning compute instances",
            template_name="provision_failure",
            template_data=template_data,
            source_email=f"Instance Provisioning ({project_name}) <{notification_email}>",
            to_email=stackset_email,
            cc_email=admin_email,
        )
        current_app.logger.info(response)

        current_app.logger.info(f"Stackset {stackset_id} is due for cleanup, passing it to the cleanup state machine")
        initiate_stackset_deprovisioning(
            stackset_id=stackset_id,
            cleanup_sfn_arn=cleanup_sfn_arn,
            owner_email=stackset_email,
        )
        current_app.logger.info(f"SFN cleanup execution response: {response}")

    return {}, 204


def post_cleanup_start():
    # read in data from environment
    project_name = current_app.config["PROJECT_NAME"]
    notification_email = current_app.config["NOTIFICATION_EMAIL"]

    # read in data passed to the lambda call
    payload = request.json
    stackset_id = payload["stackset_id"]
    owner_email = payload["stackset_email"]

    # Make provisions for paging of the results
    cfn_client = boto3.client("cloudformation")

    for instance_data in fetch_stackset_instances(stackset_id=stackset_id):
        response = cfn_client.delete_stack_instances(
            StackSetName=stackset_id,
            Accounts=[instance_data["account_id"]],
            Regions=[instance_data["region"]],
            RetainStacks=False,
        )

        current_app.logger.info(response)

        template_data = {
            "region": instance_data["region"],
            "os": instance_data["operatingSystemName"],
            "instance_type": instance_data["instanceType"],
            "instance_name": instance_data["instanceName"],
        }
        response = send_email(
            subject="Your compute instance has been deprovisioned",
            template_name="cleanup_complete",
            template_data=template_data,
            source_email=f"Instance Cleanup ({project_name}) <{notification_email}>",
            to_email=owner_email,
        )

        current_app.logger.info(response)

    return {
        "stackset_id": stackset_id,
    }


def post_cleanup_complete():
    # read in data from environment
    state_table = current_app.config["DYNAMODB_STATE_TABLE_NAME"]

    # read in data passed to the lambda call
    payload = request.json
    stackset_id = payload["stackset_id"]

    # Delete StackSet
    cfn_client = boto3.client("cloudformation")
    response = cfn_client.delete_stack_set(StackSetName=stackset_id)
    current_app.logger.info(response)

    # Remove the StackSet record from the state table
    dynamodb_client = boto3.client("dynamodb")
    response = dynamodb_client.delete_item(
        TableName=state_table,
        Key={"stacksetID": {"S": stackset_id}},
    )
    current_app.logger.info(response)

    return response
