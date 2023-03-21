import json
import logging
import os
from datetime import datetime, timedelta, timezone

from marshmallow import Schema, fields, EXCLUDE, ValidationError
from marshmallow.validate import OneOf, Range, Length

from utils import (
    get_permissions_for_group,
    provision_stackset,
    get_claims,
    get_account_id,
    get_owned_stacksets,
    audit_logging_handler,
    exception_handler,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_request_serializer(
    current_account_id,
    regions,
    instance_types,
    operating_systems,
    max_days_to_expiry,
    is_superuser,
):
    extra_fields = dict()
    if is_superuser:
        extra_fields = dict(
            email=fields.Email(required=True),
            username=fields.Str(required=True),
        )

    min_date = datetime.now(timezone.utc) + timedelta(hours=2)
    max_date = datetime.now(timezone.utc) + timedelta(days=max_days_to_expiry)
    return Schema.from_dict(
        dict(
            account=fields.Constant(constant=current_account_id),
            region=fields.Str(required=True, validate=OneOf(regions)),
            instance_type=fields.Str(required=True, data_key="instanceType", validate=OneOf(instance_types)),
            operating_system=fields.Str(
                required=True,
                data_key="operatingSystem",
                validate=OneOf(operating_systems),
            ),
            instance_name=fields.Str(required=True, data_key="instanceName", validate=Length(max=255)),
            expiry=fields.AwareDateTime(
                required=True,
                validate=Range(
                    min=min_date,
                    max=max_date,
                    error=(
                        f"Must be between {min_date.strftime('%Y-%m-%d %H:%M')} "
                        f"and {max_date.strftime('%Y-%m-%d %H:%M')}."
                    ),
                ),
            ),
            **extra_fields,
        )
    )(unknown=EXCLUDE)


@audit_logging_handler
@exception_handler
def handler(event, context):
    # Get auth params
    claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
    email, group, username, is_superuser = get_claims(claims=claims)

    # Get body params
    payload = json.loads(event["body"])

    # Read env data
    provision_sfn_arn = os.environ["provision_sfn_arn"]
    permissions_table = os.environ["dynamodb_permissions_table_name"]
    state_table = os.environ["dynamodb_state_table_name"]

    # Get params the user has permissions for
    permissions = get_permissions_for_group(table_name=permissions_table, group_name=group)

    # Validate the user provided params, raises a ValidationException if user has no permissions
    current_account_id = get_account_id()
    serializer = get_request_serializer(
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
