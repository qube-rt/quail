import logging
import os

from utils import (
    get_claims,
    get_permissions_for_group,
    exception_handler,
    audit_logging_handler,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@audit_logging_handler
@exception_handler
def handler(event, context):
    claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
    _, group, *rest = get_claims(claims=claims)

    # read in data from environment
    permissions_table = os.environ["dynamodb_permissions_table_name"]

    # Get config from dynamodb
    permissions = get_permissions_for_group(table_name=permissions_table, group_name=group)

    # Restructure the permissions
    del permissions["operating_systems"]

    return permissions
