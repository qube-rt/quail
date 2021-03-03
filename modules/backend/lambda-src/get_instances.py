import logging
import os

from utils import (
    get_claims,
    get_owned_stacksets,
    get_instance_details,
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
    email, group, _, is_superuser = get_claims(claims=claims)

    # read in data from environment
    state_table = os.environ["dynamodb_state_table_name"]
    permissions_table = os.environ["dynamodb_permissions_table_name"]

    # Get config from dynamodb
    stacksets = get_owned_stacksets(table_name=state_table, email=email, is_superuser=is_superuser)
    permissions = get_permissions_for_group(table_name=permissions_table, group_name=group)
    max_extension_count = permissions["max_extension_count"]
    instances = get_instance_details(
        stacksets=stacksets,
        max_extension_count=max_extension_count,
        is_superuser=is_superuser,
    )

    return instances
