import logging
import os
from datetime import datetime

import boto3

from email_utils import send_email
from utils import (
    audit_logging_handler,
    exception_handler,
    fetch_stackset_instances,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@audit_logging_handler
@exception_handler
def handler(event, context):
    # read in data from environment
    project_name = os.environ["project_name"]
    notification_email = os.environ["notification_email"]
    state_table = os.environ["dynamodb_state_table_name"]

    # read in data passed to the lambda call
    stackset_id = event["stackset_id"]
    stackset_email = event["stackset_email"]

    # Get config from dynamodb
    dynamodb_client = boto3.client("dynamodb")
    state_data = dynamodb_client.get_item(TableName=state_table, Key={"stacksetID": {"S": stackset_id}})["Item"]

    for instance_data in fetch_stackset_instances(stackset_id=stackset_id):
        template_data = {
            "region": instance_data["region"],
            "os": instance_data["operatingSystemName"],
            "instance_type": instance_data["instanceType"],
            "instance_name": instance_data["instanceName"],
            "ip": instance_data["private_ip"],
            "expiry": datetime.fromisoformat(state_data["expiry"]["S"]).strftime("%-I %p %d %B"),
        }

        send_email(
            template_name="provision_success",
            template_data=template_data,
            source_email=f"Instance Provisioning ({project_name}) <{notification_email}>",
            to_email=stackset_email,
        )
