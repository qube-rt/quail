import click
import boto3
from botocore.config import Config

SYNCHRONIZED_STATUS = "CURRENT"
INCOMPLETE_DETAILED_STATUS = {"PENDING", "RUNNING"}


retry_config = Config(retries={"mode": "adaptive", "max_attempts": 7})


def serialize_state_table_row(item):
    def nullable_get(item, key):
        return item[key]["S"] if key in item else None

    return {
        "stackset_id": item["stacksetID"]["S"],
        "expiry": item["expiry"]["S"],
        "extension_count": int(item["extensionCount"]["N"]),
        "username": item["username"]["S"],
        "email": item["email"]["S"],
        "group": item["group"]["S"],
        "account": nullable_get(item, "account"),
        "instance_name": nullable_get(item, "instanceName"),
        "instance_status": nullable_get(item, "instanceStatus"),
        "instance_type": nullable_get(item, "instanceType"),
        "operating_system": nullable_get(item, "operatingSystem"),
        "private_ip": nullable_get(item, "privateIp"),
        "region": nullable_get(item, "region"),
        "connection_protocol": nullable_get(item, "connectionProtocol"),
        "instance_id": nullable_get(item, "instanceId"),
    }


@click.command()
@click.option(
    "--state-table",
    help="State table name",
    required=True,
)
@click.option("--number", "-n", help="Number of stacks to migrate", default=10, type=int)
@click.option(
    "--dry-run",
    is_flag=True,
    show_default=True,
    default=False,
    help="Dry run",
)
def cleanup(state_table, number, dry_run):
    """Cleanup stale stacksets and dynamodb data"""
    dynamodb_client = boto3.client("dynamodb")
    stackset_whitelist = []  # noqa
    stackset_blacklist = []  # noqa

    # Fetch stackset state from dynamodb
    stackset_state_raw = dynamodb_client.scan(
        TableName=state_table,
    )
    print(f"{stackset_state_raw=}")
    stackset_state = [serialize_state_table_row(item) for item in stackset_state_raw["Items"]]

    filtered_stackset_state = [
        entry
        for entry in stackset_state
        if (
            (len(stackset_whitelist) == 0 or entry["stackset_id"] in stackset_whitelist)
            and (len(stackset_blacklist) == 0 or entry["stackset_id"] not in stackset_blacklist)
        )
    ]
    print(f"Stacksets prepared for update: {filtered_stackset_state=}")

    # Limit the number of stacksets to work on to the number provided
    limited_stacksets = filtered_stackset_state[:number]

    # Fetch stackset details
    cf_client = boto3.client("cloudformation", config=retry_config)
    for target_stackset in limited_stacksets:
        stackset_id = target_stackset["stackset_id"]
        stack_instances = cf_client.list_stack_instances(StackSetName=stackset_id)

        if len(stack_instances["Summaries"]) != 0:
            raise Exception(f"Wrong number of stack instances for stackset: {stackset_id}")

        print("################################################")
        print(f"Removing stackset {target_stackset['stackset_id']}")

        if dry_run:
            continue

        cf_client.delete_stack_set(StackSetName=target_stackset["stackset_id"])

        # Remove the StackSet record from the state table
        dynamodb_client = boto3.client("dynamodb")
        dynamodb_client.delete_item(
            TableName=state_table,
            Key={"stacksetID": {"S": target_stackset["stackset_id"]}},
        )

    exit(0)


if __name__ == "__main__":
    cleanup()
