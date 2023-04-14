import logging
import os

import boto3

from email_utils import send_email
from utils import (
    exception_handler,
    audit_logging_handler,
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

    # read in data passed to the lambda call
    stackset_id = event["stackset_id"]
    owner_email = event["stackset_email"]

    # Make provisions for paging of the results
    cfn_client = boto3.client("cloudformation")

    for instance_data in fetch_stackset_instances(stackset_id=stackset_id):
        response = cfn_client.delete_stack_instances(
            StackSetName=stackset_id,
            Accounts=[instance_data["account_id"]],
            Regions=[instance_data["region"]],
            RetainStacks=False,
        )

        logger.info(response)

        template_data = {
            "region": instance_data["region"],
            "os": instance_data["operatingSystemName"],
            "instance_type": instance_data["instanceType"],
            "instance_name": instance_data["instanceName"],
        }
        response = send_email(
            subject="Your compute instance has been deprovisioned",
            template_name="cleanup_complete",
            template_data=template_data,
            source_email=f"Instance Cleanup ({project_name}) <{notification_email}>",
            to_email=owner_email,
        )

        logger.info(response)

    return {
        "stackset_id": stackset_id,
    }
