import json
from operator import itemgetter
from datetime import timedelta, datetime

from flask import current_app, request
from marshmallow import ValidationError

from backend.exceptions import (
    UnauthorizedForInstanceError,
    InvalidArgumentsError,
    InstanceUpdateError,
)
from backend.serializers import group_serializer, instance_post_serializer, instance_patch_serializer


def get_params():
    groups = itemgetter("groups")(current_app.aws.get_claims(request=request))

    # Get config from dynamodb
    permissions = current_app.aws.get_permissions_for_all_groups(groups=groups)

    return permissions


def get_instances():
    email, groups, is_superuser = itemgetter("email", "groups", "is_superuser")(
        current_app.aws.get_claims(request=request)
    )

    # Get config from dynamodb
    stacksets = current_app.aws.get_owned_stacksets(email=email, is_superuser=is_superuser)
    permissions = current_app.aws.get_permissions_for_all_groups(groups=groups)

    instances = current_app.aws.get_instance_details(
        stacksets=stacksets,
        max_extension_per_group=permissions,
        is_superuser=is_superuser,
    )

    return {"instances": instances}


def post_instances():
    # Get auth params
    email, groups, username, is_superuser, claims = itemgetter("email", "groups", "username", "is_superuser", "claims")(
        current_app.aws.get_claims(request=request)
    )

    # Get body params
    payload = request.json

    # Get user group
    try:
        group_data = group_serializer(groups=groups).load(payload)
    except ValidationError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": e.messages}),
            "headers": {"Content-Type": "application/json"},
        }
    current_group = group_data["group"]

    # Get user permissions for the selected group
    permissions = current_app.aws.get_permissions_for_one_group(group_name=current_group)
    permitted_accounts = list(permissions["region_map"].keys())

    # Validate the user provided params, raises a ValidationException if user has no permissions
    serializer = instance_post_serializer(
        accounts=permitted_accounts,
        region_map=permissions["region_map"],
        instance_types=permissions["instance_types"],
        max_days_to_expiry=permissions["max_days_to_expiry"],
        initiator_username=username,
        initator_email=email,
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
    stack_email = data.pop("email")
    stack_username = data.pop("username")

    if not is_superuser:
        stacksets = current_app.aws.get_owned_stacksets(email=stack_email)
        if len(stacksets) >= permissions["max_instance_count"]:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"message": f"Instance limit exceeded. You already own {len(stacksets)} instances."}
                ),
                "headers": {"Content-Type": "application/json"},
            }

    # Provision stackset
    sfn_execution_arn = current_app.aws.provision_stackset(
        email=stack_email,
        group=current_group,
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
    email, is_superuser = itemgetter("email", "is_superuser")(current_app.aws.get_claims(request=request))

    # get details of the specified stackset
    stackset_data = current_app.aws.get_stackset_state_data(stackset_id=stackset_id)
    if not stackset_data or (stackset_data["email"] != email and not is_superuser):
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "You're not authorized to modify this instance."}),
            "headers": {"Content-Type": "application/json"},
        }

    instances = current_app.aws.get_instance_details(stacksets=[stackset_data])

    target_instance = instances[0]
    current_app.aws.start_instance(
        stackset_id=stackset_id,
        account_id=target_instance["account_id"],
        region_name=target_instance["region"],
        instance_id=target_instance["instance_id"],
    )

    return {}, 204


def post_instance_stop(stackset_id):
    email, is_superuser = itemgetter("email", "is_superuser")(current_app.aws.get_claims(request=request))

    # get details of the specified stackset
    stackset_data = current_app.aws.get_stackset_state_data(stackset_id=stackset_id)
    if not stackset_data or (stackset_data["email"] != email and not is_superuser):
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "You're not authorized to modify this instance."}),
            "headers": {"Content-Type": "application/json"},
        }

    instances = current_app.aws.get_instance_details(stacksets=[stackset_data])

    target_instance = instances[0]
    current_app.aws.stop_instance(
        stackset_id=stackset_id,
        account_id=target_instance["account_id"],
        region_name=target_instance["region"],
        instance_id=target_instance["instance_id"],
    )

    return {}, 204


def patch_instance(stackset_id):
    email, is_superuser = itemgetter("email", "is_superuser")(current_app.aws.get_claims(request=request))

    # Get body params
    payload = request.json

    # get details of the specified stackset
    stackset_data = current_app.aws.get_stackset_state_data(stackset_id=stackset_id)
    if not stackset_data or (stackset_data["email"] != email and not is_superuser):
        raise UnauthorizedForInstanceError()

    # Get params the user has permissions for and sanitize input
    permissions = current_app.aws.get_permissions_for_one_group(group_name=stackset_data["group"])
    serializer = instance_patch_serializer(
        instance_types=permissions["instance_types"],
    )

    try:
        data = serializer.load(payload)
    except ValidationError as e:
        raise InvalidArgumentsError(message=str(e))

    instance_type = data["instance_type"]
    current_app.aws.update_stackset(stackset_id=stackset_id, InstanceType=instance_type)

    return {}, 204


def post_instance_extend(stackset_id):
    email, is_superuser = itemgetter("email", "is_superuser")(current_app.aws.get_claims(request=request))

    # get details of the specified stackset
    stackset_data = current_app.aws.get_stackset_state_data(stackset_id=stackset_id)
    if not stackset_data or (stackset_data["email"] != email and not is_superuser):
        raise UnauthorizedForInstanceError()

    # get user group permissions
    permissions = current_app.aws.get_permissions_for_one_group(group_name=stackset_data["group"])
    max_extension_count = permissions["max_extension_count"]

    # check user hasn't exceeded the max number of extensions
    if not is_superuser and stackset_data["extension_count"] >= max_extension_count:
        raise InstanceUpdateError(
            f"You cannot extend instance lifetime more than {stackset_data['extension_count']} times."
        )

    new_expiry = datetime.fromisoformat(stackset_data["expiry"]) + timedelta(days=1)
    new_extension_count = stackset_data["extension_count"] + 1

    current_app.aws.update_instance_expiry(
        stackset_id=stackset_id, expiry=new_expiry, extension_count=new_extension_count
    )

    return {
        "stackset_id": stackset_id,
        "can_extend": is_superuser or new_extension_count < max_extension_count,
        "expiry": new_expiry.isoformat(),
    }


def delete_instances(stackset_id):
    email, is_superuser = itemgetter("email", "is_superuser")(current_app.aws.get_claims(request=request))

    # Check if the requester owns the stackset
    stackset_data = current_app.aws.get_stackset_state_data(stackset_id=stackset_id)
    if not stackset_data or (stackset_data["email"] != email and not is_superuser):
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "You're not authorized to modify this instance."}),
            "headers": {"Content-Type": "application/json"},
        }

    current_app.aws.update_stackset_state_entry(
        stackset_id=stackset_id,
        data=[
            {"field_name": "stackStatus", "value": "deleting"},
            {"field_name": "instanceStatus", "value": "shutting-down"},
        ],
    )

    # Deprovision stackset
    owner_email = stackset_data["email"]
    response = current_app.aws.initiate_stackset_deprovisioning(
        stackset_id=stackset_id,
        owner_email=owner_email,
    )
    current_app.logger.info(f"SFN cleanup execution response: {response}")

    return {}, 204
