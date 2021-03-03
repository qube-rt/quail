import logging
import os

import boto3

from utils import exception_handler, audit_logging_handler

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@audit_logging_handler
@exception_handler
def handler(event, context):
    # read in data from environment
    state_table = os.environ["dynamodb_state_table_name"]

    # read in data passed to the lambda call
    stackset_id = event["stackset_id"]

    # Delete StackSet
    cfn_client = boto3.client("cloudformation")
    response = cfn_client.delete_stack_set(StackSetName=stackset_id)
    logger.info(response)

    # Remove the StackSet record from the state table
    dynamodb_client = boto3.client("dynamodb")
    response = dynamodb_client.delete_item(
        TableName=state_table,
        Key={"stacksetID": {"S": stackset_id}},
    )
    logger.info(response)
