import json
from operator import itemgetter
from datetime import timedelta

import boto3
from flask import current_app, request
from marshmallow import ValidationError

from backend.aws_utils import (
    get_permissions_for_group,
    get_claims,
    get_owned_stacksets,
    get_instance_details,
    get_account_id,
    provision_stackset,
    get_stackset_state_data,
    UnauthorizedForInstanceError,
    InvalidArgumentsError,
    update_stackset,
    InstanceUpdateError,
    initiate_stackset_deprovisioning,
)
from backend.serializers import instance_post_serializer, instance_patch_serializer


def get_params():
    group = itemgetter("group")(get_claims(request=request))

    # read in data from config
    permissions_table = current_app.config["DYNAMODB_PERMISSIONS_TABLE_NAME"]

    # Get config from dynamodb
    permissions = get_permissions_for_group(table_name=permissions_table, group_name=group)

    # Restructure the permissions
    del permissions["operating_systems"]

    return permissions


def get_instances():
    email, group, is_superuser = itemgetter("email", "group", "is_superuser")(get_claims(request=request))

    # read in data from environment
    state_table = current_app.config["DYNAMODB_STATE_TABLE_NAME"]
    permissions_table = current_app.config["DYNAMODB_PERMISSIONS_TABLE_NAME"]

    # Get config from dynamodb
    stacksets = get_owned_stacksets(table_name=state_table, email=email, is_superuser=is_superuser)
    permissions = get_permissions_for_group(table_name=permissions_table, group_name=group)
    max_extension_count = permissions["max_extension_count"]
    instances = get_instance_details(
        stacksets=stacksets,
        max_extension_count=max_extension_count,
        is_superuser=is_superuser,
    )

    return {"instances": instances}


def post_instances():
    # Get auth params
    email, group, username, is_superuser, claims = itemgetter("email", "group", "username", "is_superuser", "claims")(
        get_claims(request=request)
    )

    # Get body params
    payload = request.json

    # Read env data
    state_table = current_app.config["DYNAMODB_STATE_TABLE_NAME"]
    permissions_table = current_app.config["DYNAMODB_PERMISSIONS_TABLE_NAME"]
    provision_sfn_arn = current_app.config["PROVISION_SFN_ARN"]

    # Get params the user has permissions for
    permissions = get_permissions_for_group(table_name=permissions_table, group_name=group)

    # Validate the user provided params, raises a ValidationException if user has no permissions
    current_account_id = get_account_id()
    serializer = instance_post_serializer(
        current_account_id=current_account_id,
        regions=permissions["region_map"].keys(),
        instance_types=permissions["instance_types"],
        operating_systems=permissions["region_map"].get(payload.get("region"), []),
        max_days_to_expiry=permissions["max_days_to_expiry"],
        is_superuser=is_superuser,
    )
    try:
        data = serializer.load(payload)
    except ValidationError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": e.messages}),
            "headers": {"Content-Type": "application/json"},
        }

    # Check if instance count is within limits if the user isn't a superuser
    if is_superuser:
        stack_email = data.pop("email")
        stack_username = data.pop("username")
    else:
        stack_email = email
        stack_username = username

        stacksets = get_owned_stacksets(table_name=state_table, email=stack_email)
        if len(stacksets) >= permissions["max_instance_count"]:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"message": f"Instance limit exceeded. You already own {len(stacksets)} instances."}
                ),
                "headers": {"Content-Type": "application/json"},
            }

    # Provision stackset
    sfn_execution_arn = provision_stackset(
        provision_sfn_arn=provision_sfn_arn,
        email=stack_email,
        group=group,
        username=stack_username,
        user=claims,
        **data,
    )

    return {
        "sfn_execution_arn": sfn_execution_arn,
        "email": stack_email,
        "username": stack_username,
    }


def post_instance_start(stackset_id):
    email, is_superuser = itemgetter("email", "is_superuser")(get_claims(request=request))

    # read in data from environment
    state_table = current_app.config["DYNAMODB_STATE_TABLE_NAME"]

    # get details of the specified stackset
    stackset_data = get_stackset_state_data(stackset_id=stackset_id, table_name=state_table)
    if not stackset_data or (stackset_data["email"] != email and not is_superuser):
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "You're not authorized to modify this instance."}),
            "headers": {"Content-Type": "application/json"},
        }

    instances = get_instance_details(stacksets=[stackset_data])

    client = boto3.client("ec2", region_name=instances[0]["region"])
    client.start_instances(InstanceIds=[instances[0]["instance_id"]])

    return {}, 204


def post_instance_stop(stackset_id):
    email, is_superuser = itemgetter("email", "is_superuser")(get_claims(request=request))

    # read in data from environment
    state_table = current_app.config["DYNAMODB_STATE_TABLE_NAME"]

    # get details of the specified stackset
    stackset_data = get_stackset_state_data(stackset_id=stackset_id, table_name=state_table)
    if not stackset_data or (stackset_data["email"] != email and not is_superuser):
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "You're not authorized to modify this instance."}),
            "headers": {"Content-Type": "application/json"},
        }

    instances = get_instance_details(stacksets=[stackset_data])

    client = boto3.client("ec2", region_name=instances[0]["region"])
    client.stop_instances(InstanceIds=[instances[0]["instance_id"]])

    return {}, 204


def patch_instance(stackset_id):
    email, group, is_superuser = itemgetter("email", "group", "is_superuser")(get_claims(request=request))

    # Get body params
    payload = request.json

    # read in data from environment
    state_table = current_app.config["DYNAMODB_STATE_TABLE_NAME"]
    permissions_table = current_app.config["DYNAMODB_PERMISSIONS_TABLE_NAME"]

    # get details of the specified stackset
    stackset_data = get_stackset_state_data(stackset_id=stackset_id, table_name=state_table)
    if not stackset_data or (stackset_data["email"] != email and not is_superuser):
        raise UnauthorizedForInstanceError()

    # Get params the user has permissions for and sanitize input
    permissions = get_permissions_for_group(table_name=permissions_table, group_name=group)
    serializer = instance_patch_serializer(
        instance_types=permissions["instance_types"],
    )

    try:
        data = serializer.load(payload)
    except ValidationError as e:
        raise InvalidArgumentsError(message=str(e))

    instance_type = data["instance_type"]
    update_stackset(stackset_id=stackset_id, InstanceType=instance_type)

    return {}, 204


def post_instance_extend(stackset_id):
    email, group, is_superuser = itemgetter("email", "group", "is_superuser")(get_claims(request=request))

    # read in data from environment
    state_table = current_app.config["DYNAMODB_STATE_TABLE_NAME"]
    permissions_table = current_app.config["DYNAMODB_PERMISSIONS_TABLE_NAME"]

    # get details of the specified stackset
    stackset_data = get_stackset_state_data(stackset_id=stackset_id, table_name=state_table)
    if not stackset_data or (stackset_data["email"] != email and not is_superuser):
        raise UnauthorizedForInstanceError()

    # get user group permissions
    permissions = get_permissions_for_group(table_name=permissions_table, group_name=group)
    max_extension_count = permissions["max_extension_count"]

    # check user hasn't exceeded the max number of extensions
    if not is_superuser and stackset_data["extension_count"] >= max_extension_count:
        raise InstanceUpdateError(
            f"You cannot extend instance lifetime more than {stackset_data['extension_count']} times."
        )

    new_expiry = stackset_data["expiry"] + timedelta(days=1)
    new_extension_count = stackset_data["extension_count"] + 1

    client = boto3.client("dynamodb")
    client.update_item(
        TableName=state_table,
        Key={"stacksetID": {"S": stackset_id}},
        UpdateExpression="SET extensionCount = :extensionCount, expiry = :expiry",
        ExpressionAttributeValues={
            ":extensionCount": {"N": str(new_extension_count)},
            ":expiry": {"S": new_expiry.isoformat()},
        },
    )

    return {
        "stackset_id": stackset_id,
        "can_extend": is_superuser or new_extension_count < max_extension_count,
        "expiry": new_expiry.isoformat(),
    }


def delete_instances(stackset_id):
    email, is_superuser = itemgetter("email", "is_superuser")(get_claims(request=request))

    # Read env data
    state_table = current_app.config["DYNAMODB_STATE_TABLE_NAME"]
    cleanup_sfn_arn = current_app.config["CLEANUP_SFN_ARN"]

    # Check if the requester owns the stackset
    stackset_data = get_stackset_state_data(stackset_id=stackset_id, table_name=state_table)
    if not stackset_data or (stackset_data["email"] != email and not is_superuser):
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "You're not authorized to modify this instance."}),
            "headers": {"Content-Type": "application/json"},
        }

    # Deprovision stackset
    owner_email = stackset_data["email"]
    response = initiate_stackset_deprovisioning(
        stackset_id=stackset_id,
        cleanup_sfn_arn=cleanup_sfn_arn,
        owner_email=owner_email,
    )
    current_app.logger.info(f"SFN cleanup execution response: {response}")

    return {}, 204
