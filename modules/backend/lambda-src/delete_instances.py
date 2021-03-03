import json
import logging
import os

from utils import (
    get_claims,
    get_stackset_state_data,
    initiate_stackset_deprovisioning,
    exception_handler,
    audit_logging_handler,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@audit_logging_handler
@exception_handler
def handler(event, context):
    # Get auth params
    claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
    email, _, _, is_superuser = get_claims(claims=claims)

    # Get route params
    stackset_id = event["pathParameters"]["id"]

    # Read env data
    state_table = os.environ["dynamodb_state_table_name"]
    cleanup_sfn_arn = os.environ["cleanup_sfn_arn"]

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
    logger.info(f"SFN cleanup execution response: {response}")

    return {}
