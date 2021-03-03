import json
import os
import logging

from marshmallow import Schema, fields, EXCLUDE, ValidationError
from marshmallow.validate import OneOf


from utils import (
    get_claims,
    get_stackset_state_data,
    exception_handler,
    UnauthorizedForInstanceError,
    InvalidArgumentsError,
    get_permissions_for_group,
    update_stackset,
    audit_logging_handler,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_request_serializer(instance_types):
    return Schema.from_dict(
        dict(
            instance_type=fields.Str(required=True, data_key="instanceType", validate=OneOf(instance_types)),
        )
    )(unknown=EXCLUDE)


@audit_logging_handler
@exception_handler
def handler(event, context):
    claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
    email, group, _, is_superuser = get_claims(claims=claims)

    # read in data from request path
    stackset_id = event["pathParameters"]["id"]

    # Get body params
    payload = json.loads(event["body"])

    # read in data from environment
    state_table = os.environ["dynamodb_state_table_name"]
    permissions_table = os.environ["dynamodb_permissions_table_name"]

    # get details of the specified stackset
    stackset_data = get_stackset_state_data(stackset_id=stackset_id, table_name=state_table)
    if not stackset_data or (stackset_data["email"] != email and not is_superuser):
        raise UnauthorizedForInstanceError()

    # Get params the user has permissions for and sanitize input
    permissions = get_permissions_for_group(table_name=permissions_table, group_name=group)
    serializer = get_request_serializer(
        instance_types=permissions["instance_types"],
    )

    try:
        data = serializer.load(payload)
    except ValidationError as e:
        raise InvalidArgumentsError(message=str(e))

    instance_type = data["instance_type"]
    update_stackset(stackset_id=stackset_id, InstanceType=instance_type)

    return {}
