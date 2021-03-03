import json
import os
import logging

import boto3

from utils import (
    get_claims,
    get_instance_details,
    get_stackset_state_data,
    audit_logging_handler,
    exception_handler,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@audit_logging_handler
@exception_handler
def handler(event, context):
    claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
    email, _, _, is_superuser = get_claims(claims=claims)

    # read in data from request path
    stackset_id = event["pathParameters"]["id"]

    # read in data from environment
    state_table = os.environ["dynamodb_state_table_name"]

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

    return {}
