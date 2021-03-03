import os
import logging
from datetime import timedelta

import boto3

from utils import (
    get_claims,
    get_permissions_for_group,
    get_stackset_state_data,
    exception_handler,
    UnauthorizedForInstanceError,
    InstanceUpdateError,
    audit_logging_handler,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@audit_logging_handler
@exception_handler
def handler(event, context):
    claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
    email, group, _, is_superuser = get_claims(claims=claims)

    # read in data from request path
    stackset_id = event["pathParameters"]["id"]

    # read in data from environment
    state_table = os.environ["dynamodb_state_table_name"]
    permissions_table = os.environ["dynamodb_permissions_table_name"]

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
