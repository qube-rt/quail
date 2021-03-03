import os
import json
import random
from datetime import datetime

import boto3

from utils import (
    get_params_for_region,
    get_os_config,
    audit_logging_handler,
    exception_handler,
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


@audit_logging_handler
@exception_handler
def handler(event, context):
    params = {
        "account": event["Input"]["account"],
        "region": event["Input"]["region"],
        "instance_type": event["Input"]["instance_type"],
        "os": event["Input"]["operating_system"],
        "expiry": datetime.fromisoformat(event["Input"]["expiry"]),
        "email": event["Input"]["email"],
        "user_group": event["Input"]["group"],
        "instance_name": event["Input"]["instance_name"],
        "user_claims": event["Input"]["user"],
        "username": event["Input"]["username"],
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
