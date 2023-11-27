import json
from datetime import datetime, timedelta, timezone

from flask import request, current_app

from backend.email_utils import send_email, format_expiry


def get_tags(environment, tag_config):
    tags = []

    for tag in tag_config:
        if tag["tag-value"].startswith("$"):
            # Skip leading dollar sign
            attribute_key = tag["tag-value"][1:]
            tag["tag-value"] = environment[attribute_key]

        tags.append(tag)

    return tags


def post_provision():
    # Get body params
    payload = request.json

    # read in data from environment
    project_name = current_app.config["PROJECT_NAME"]
    tag_config = json.loads(current_app.config["TAG_CONFIG"])

    # The number of tags is hardcoded in the terraform template
    assert len(tag_config) == 2

    # Evaluate tags
    user_claims = payload["user"]
    tags = get_tags(environment={**user_claims, "group": payload["group"]}, tag_config=tag_config)

    stackset_id = current_app.aws.create_stack_set(
        project_name=project_name,
        tags=tags,
        account=payload["account"],
        region=payload["region"],
        instance_type=payload["instance_type"],
        operating_system=payload["operating_system"],
        expiry=datetime.fromisoformat(payload["expiry"]),
        email=payload["email"],
        group=payload["group"],
        instance_name=payload["instance_name"],
        username=payload["username"],
    )

    return {"stackset_id": stackset_id, "stackset_email": payload["email"]}


def get_wait():
    stack_name = request.args.get("stackset_id")
    # Whether no operations should cause the function to error. It should be true when creating an instance
    # but false when waiting for delete operations to complete.
    error_if_no_operations = request.args.get("error_if_no_operations")

    current_app.aws.check_stackset_complete(stack_name=stack_name, error_if_no_operations=error_if_no_operations)

    return {}, 204


def post_notify_success():
    # read in data from environment
    project_name = current_app.config["PROJECT_NAME"]
    notification_email = current_app.config["NOTIFICATION_EMAIL"]

    # read in data passed to the lambda call
    payload = request.json
    stackset_id = payload["stackset_id"]
    stackset_email = payload["stackset_email"]

    # Get config from dynamodb
    stack_set = current_app.aws.get_one_stack_set(stackset_id=stackset_id)
    current_app.logger.info("state data: %s", stack_set)

    for instance_data in current_app.aws.fetch_stackset_instances(stackset_id=stackset_id):
        template_data = {
            "account": instance_data["account_id"],
            "region": instance_data["region"],
            "os": instance_data["operatingSystemName"],
            "instance_type": instance_data["instanceType"],
            "instance_name": instance_data["instanceName"],
            "ip": instance_data["private_ip"],
            "expiry": format_expiry(datetime.fromisoformat(stack_set["expiry"])),
        }
        current_app.logger.info("template data: %s", template_data)

        response = send_email(
            subject="Compute instance provisioned successfully",
            template_name="provision_success",
            template_data=template_data,
            source_email=f"Instance Provisioning ({project_name}) <{notification_email}>",
            to_email=stackset_email,
        )
        current_app.logger.info("send mail response : %s", response)

    return {}, 204


def post_notify_failure():
    # read in data from environment
    project_name = current_app.config["PROJECT_NAME"]
    notification_email = current_app.config["NOTIFICATION_EMAIL"]
    admin_email = current_app.config["ADMIN_EMAIL"]

    # read in data passed to the lambda call
    payload = request.json
    stackset_id = payload["stackset_id"]
    stackset_email = payload["stackset_email"]

    # send SNS failure notification
    current_app.aws.send_error_sns_message(stackset_id=stackset_id)

    for instance_data in current_app.aws.fetch_stackset_instances(stackset_id=stackset_id, acceptable_statuses=None):
        template_data = {
            "account": instance_data["account_id"],
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
        current_app.logger.info(response)

        current_app.logger.info(f"Stackset {stackset_id} is due for cleanup, passing it to the cleanup state machine")
        current_app.aws.initiate_stackset_deprovisioning(
            stackset_id=stackset_id,
            owner_email=stackset_email,
        )
        current_app.logger.info(f"SFN cleanup execution response: {response}")

    return {}, 204


def post_cleanup_start():
    # read in data from environment
    project_name = current_app.config["PROJECT_NAME"]
    notification_email = current_app.config["NOTIFICATION_EMAIL"]

    # read in data passed to the lambda call
    payload = request.json
    stackset_id = payload["stackset_id"]
    owner_email = payload["stackset_email"]

    # Make provisions for paging of the results
    instances = current_app.aws.fetch_stackset_instances(stackset_id=stackset_id)
    current_app.logger.info("instances: %s", instances)
    for instance_data in instances:
        response = current_app.aws.delete_stack_instance(
            stackset_id=stackset_id, account_id=instance_data["account_id"], region=instance_data["region"]
        )

        current_app.logger.info("delete stack instance response: %s", response)

        template_data = {
            "account": instance_data["account_id"],
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

        current_app.logger.info("send mail response: %s", response)

    return {
        "stackset_id": stackset_id,
    }


def post_cleanup_complete():
    # read in data passed to the lambda call
    payload = request.json
    stackset_id = payload["stackset_id"]

    # Delete StackSet
    response = current_app.aws.delete_stack_set(stackset_id=stackset_id)
    current_app.logger.info(response)

    return response


def post_cleanup_schedule():
    # read in data from environment
    project_name = current_app.config["PROJECT_NAME"]
    notification_email = current_app.config["NOTIFICATION_EMAIL"]
    cleanup_notice_notification_hours = json.loads(current_app.config["CLEANUP_NOTICE_NOTIFICATION_HOURS"])

    stack_sets = current_app.aws.get_all_stack_sets()
    current_app.logger.debug("Current state data: %s", stack_sets)

    # Make provisions for paging of the results
    now = datetime.now(timezone.utc)
    for entry in stack_sets:
        stackset_id = entry["stackset_id"]
        owner_email = entry["email"]
        expiry = datetime.fromisoformat(entry["expiry"])

        if expiry <= now:
            # If instance is expired, kick off cleanup
            current_app.logger.info(
                f"Stackset {stackset_id} is due for cleanup, passing it to the cleanup state machine"
            )
            response = current_app.aws.initiate_stackset_deprovisioning(
                stackset_id=stackset_id,
                owner_email=owner_email,
            )
            current_app.logger.info(f"SFN cleanup execution response: {response}")
            continue

        for notice in cleanup_notice_notification_hours:
            window_start = expiry - timedelta(hours=notice + 1)
            window_end = expiry - timedelta(hours=notice)

            # current_app.logger.info(f"{window_start} {now} {window_end}")
            if window_start < now < window_end:
                current_app.logger.info(f"Sending advance termination notice for Stackset {stackset_id}")

                # send notifications
                for instance_data in current_app.aws.fetch_stackset_instances(stackset_id=stackset_id):
                    template_data = {
                        "account": instance_data["account_id"],
                        "instance_name": instance_data["instanceName"],
                        "region": instance_data["region"],
                        "os": instance_data["operatingSystemName"],
                        "instance_type": instance_data["instanceType"],
                        "ip": instance_data["private_ip"],
                        "expiry": format_expiry(expiry),
                    }

                    response = send_email(
                        subject="Your compute instance will be deprovisioned soon",
                        template_name="cleanup_notice",
                        template_data=template_data,
                        source_email=f"Instance Cleanup ({project_name}) <{notification_email}>",
                        to_email=owner_email,
                    )
                    current_app.logger.info(f"Sending notice email: {response}")

    return {}, 204
