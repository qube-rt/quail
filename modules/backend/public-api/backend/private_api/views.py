import os
import json
import random
from datetime import datetime

import boto3
from flask import request

from backend.aws_utils import (
    get_params_for_region,
    get_os_config,
    audit_logging_handler,
    StackSetExecutionInProgressException,
    STACKSET_OPERATION_INCOMPLETE_STATUSES,
    SYNCHRONIZED_STATUS,
    SUCCESS_DETAILED_STATUS,
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
    project_name = os.environ["project_name"]
    regional_metadata_table = os.environ["dynamodb_regional_metadata_table_name"]
    state_table = os.environ["dynamodb_state_table_name"]
    permissions_table = os.environ["dynamodb_permissions_table_name"]
    cfn_data_bucket = os.environ["cfn_data_bucket"]
    tag_config = json.loads(os.environ["tag_config"])

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
        StackSetName=f"{project_name}-stackset-{context.aws_request_id}",
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
    payload = request.json

    stack_name = payload["stackset_id"]
    # Whether no operations should cause the function to error. It should be true when creating an instance
    # but false when waiting for delete operations to complete.
    error_if_no_operations = payload["error_if_no_operations"]

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
