import logging
import os

from email_utils import send_email
from utils import (
    send_sns_message,
    exception_handler,
    audit_logging_handler,
    fetch_stackset_instances,
    initiate_stackset_deprovisioning,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@audit_logging_handler
@exception_handler
def handler(event, context):
    # read in data from environment
    project_name = os.environ["project_name"]
    notification_email = os.environ["notification_email"]
    admin_email = os.environ["admin_email"]
    sns_error_topic_arn = os.environ["sns_error_topic_arn"]
    cleanup_sfn_arn = os.environ["cleanup_sfn_arn"]

    # read in data passed to the lambda call
    stackset_id = event["stackset_id"]
    stackset_email = event["stackset_email"]

    # send SNS failure notification
    send_sns_message(topic_arn=sns_error_topic_arn, stackset_id=stackset_id)

    for instance_data in fetch_stackset_instances(stackset_id=stackset_id, acceptable_statuses=None):
        template_data = {
            "region": instance_data["region"],
            "os": instance_data["operatingSystemName"],
            "instance_type": instance_data["instanceType"],
            "instance_name": instance_data["instanceName"],
        }

        response = send_email(
            subject="Error provisioning compute instances",
            template_name="provision_failure",
            template_data=template_data,
            source_email=f"Instance Provisioning ({project_name}) <{notification_email}>",
            to_email=stackset_email,
            cc_email=admin_email,
        )
        logger.info(response)

        logger.info(f"Stackset {stackset_id} is due for cleanup, passing it to the cleanup state machine")
        initiate_stackset_deprovisioning(
            stackset_id=stackset_id,
            cleanup_sfn_arn=cleanup_sfn_arn,
            owner_email=stackset_email,
        )
        logger.info(f"SFN cleanup execution response: {response}")
