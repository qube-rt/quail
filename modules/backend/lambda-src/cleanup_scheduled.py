import json
import logging
import os
from datetime import datetime, timedelta, timezone

import boto3

from email_utils import send_email
from utils import (
    exception_handler,
    audit_logging_handler,
    initiate_stackset_deprovisioning,
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
    cleanup_notice_notification_hours = json.loads(os.environ["cleanup_notice_notification_hours"])
    cleanup_sfn_arn = os.environ["cleanup_sfn_arn"]

    dynamodb_client = boto3.client("dynamodb")
    results = dynamodb_client.scan(
        TableName=state_table,
    )
    logger.info(results)

    # Make provisions for paging of the results
    now = datetime.now(timezone.utc)
    for entry in results["Items"]:
        stackset_id = entry["stacksetID"]["S"]
        owner_email = entry["email"]["S"]
        expiry = datetime.fromisoformat(entry["expiry"]["S"])

        if expiry <= now:
            # If instance is expired, kick off cleanup
            logger.info(f"Stackset {stackset_id} is due for cleanup, passing it to the cleanup state machine")
            response = initiate_stackset_deprovisioning(
                stackset_id=stackset_id,
                cleanup_sfn_arn=cleanup_sfn_arn,
                owner_email=owner_email,
            )
            logger.info(f"SFN cleanup execution response: {response}")
            continue

        for notice in cleanup_notice_notification_hours:
            window_start = now + timedelta(hours=notice)
            window_end = now + timedelta(hours=notice - 1)

            logger.info(f"{window_start} {now} {window_end}")
            if window_start < now < window_end:
                logger.info(f"Sending advance termination notice for Stackset {stackset_id}")

                # send notifications
                for instance_data in fetch_stackset_instances(stackset_id=stackset_id):
                    template_data = {
                        "instance_name": instance_data["instanceName"],
                        "region": instance_data["region"],
                        "os": instance_data["operatingSystemName"],
                        "instance_type": instance_data["instanceType"],
                        "ip": instance_data["private_ip"],
                        "expiry": expiry.strftime("%-I %p %d %B"),
                    }

                    response = send_email(
                        send_email="Your compute instance will be deprovisioned soon",
                        template_name="cleanup_notice",
                        template_data=template_data,
                        source_email=f"Instance Cleanup ({project_name}) <{notification_email}>",
                        to_email=owner_email,
                    )
                    logger.info(f"Sending notice email: {response}")
