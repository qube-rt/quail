import click
import boto3

SYNCHRONIZED_STATUS = "CURRENT"
INCOMPLETE_DETAILED_STATUS = {"PENDING", "RUNNING"}


@click.command()
@click.option("--count", default=1, help="Number of greetings.")
@click.option("--name", prompt="Your name", help="The person to greet.")
def hello(count, name):
    """Simple program that greets NAME for a total of COUNT times."""
    for x in range(count):
        click.echo(f"Hello {name}!")


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


def get_instance_details(stackset):
    cf_client = boto3.client("cloudformation")

    stackset_id = stackset["stackset_id"]

    stack_instances = cf_client.list_stack_instances(StackSetName=stackset_id)
    if len(stack_instances["Summaries"]) != 1:
        raise Exception(f"Wrong number of stack instances for stackset: {stackset_id}")

    instance = stack_instances["Summaries"][0]
    print(f"{instance=}")

    account_id = instance["Account"]
    region = instance["Region"]
    stack_id = instance.get("StackId")

    remote_cf_client = boto3.client("cloudformation", region_name=region)
    described_stacks = remote_cf_client.describe_stacks(StackName=stack_id)
    current_stack = described_stacks["Stacks"][0]
    param_dict = {x["ParameterKey"]: x["ParameterValue"] for x in current_stack["Parameters"]}

    instance_data = {
        "stackset_id": stackset_id,
        "account_id": account_id,
        "region": region,
        "expiry": stackset["expiry"],
        "username": stackset["username"],
        "email": stackset["email"],
        "group": stackset["group"],
        "operatingSystemName": param_dict.get("OperatingSystemName"),
        "instanceType": param_dict["InstanceType"],
        "instanceName": param_dict["InstanceName"],
        "connectionProtocol": param_dict["ConnectionProtocol"],
        "private_ip": None,
    }

    if (
        instance["Status"] == SYNCHRONIZED_STATUS
        and instance["StackInstanceStatus"]["DetailedStatus"] not in INCOMPLETE_DETAILED_STATUS
    ):
        output_dict = {x["OutputKey"]: x["OutputValue"] for x in current_stack["Outputs"]}

        instance_data = {
            **instance_data,
            "private_ip": output_dict["PrivateIp"],
            "instance_id": output_dict["InstanceID"],
        }

        ec2_client = boto3.client("ec2", region_name=region)
        described_instances = ec2_client.describe_instances(InstanceIds=[instance_data["instance_id"]])

        ec2_instance = described_instances["Reservations"][0]["Instances"][0]
        ec2_instance_status = ec2_instance["State"]["Name"]
        instance_data["state"] = ec2_instance_status

        return instance_data
    else:
        raise f"Could not get instance data for stackset {stackset_id}"


@click.command()
@click.option(
    "--state-table",
    help="State table name",
    required=True,
)
@click.option("--number", "-n", help="Number of stacks to migrate", default=10, type=int)
@click.option(
    "--migrate-state-error",
    is_flag=True,
    show_default=True,
    default=False,
    help="Migrate stacks where instance state is 'error' as opposed to missing",
)
@click.option(
    "--dry-run",
    is_flag=True,
    show_default=True,
    default=False,
    help="Dry run",
)
def migrate(state_table, number, migrate_state_error, dry_run):
    """Migrate the dynamodb data to the new schema."""

    dynamodb_client = boto3.client("dynamodb")
    stackset_whitelist = []  # noqa
    stackset_blacklist = []  # noqa

    # Fetch stackset state from dynamodb
    stackset_state_raw = dynamodb_client.scan(
        TableName=state_table,
    )
    print(f"{stackset_state_raw=}")
    stackset_state = [serialize_state_table_row(item) for item in stackset_state_raw["Items"]]

    def filter_stacksets(entry, migrate_state_error):
        instance_status = entry.get("instance_status")
        if migrate_state_error:
            return instance_status == "error"
        else:
            return instance_status is None or instance_status == ""

    filtered_stackset_state = [entry for entry in stackset_state if filter_stacksets(entry, migrate_state_error)]
    print(f"{filtered_stackset_state=}")

    filtered_stackset_state = [
        entry
        for entry in filtered_stackset_state
        if (
            (len(stackset_whitelist) == 0 or entry["stackset_id"] in stackset_whitelist)
            and (len(stackset_blacklist) == 0 or entry["stackset_id"] not in stackset_blacklist)
        )
    ]
    print(f"Stacksets prepared for update: {filtered_stackset_state=}")

    # Limit the number of stacksets to work on to the number provided
    limited_stacksets = filtered_stackset_state[:number]

    # Fetch stackset details
    for target_stackset in limited_stacksets:
        stackset_details = get_instance_details(target_stackset)
        print("################################################")
        print(f"{stackset_details=}")

        if dry_run:
            continue

        dynamodb_client.update_item(
            TableName=state_table,
            Key={"stacksetID": {"S": stackset_details["stackset_id"]}},
            UpdateExpression=(
                "SET account = :account,"
                "#region = :region,"
                "instanceName = :instanceName,"
                "instanceType = :instanceType,"
                "operatingSystem = :operatingSystem,"
                "connectionProtocol = :connectionProtocol,"
                "privateIp = :privateIp,"
                "instanceId = :instanceId,"
                "instanceStatus = :instanceStatus"
            ),
            ExpressionAttributeValues={
                ":account": {"S": stackset_details["account_id"]},
                ":region": {"S": stackset_details["region"]},
                ":instanceName": {"S": stackset_details["instanceName"]},
                ":instanceType": {"S": stackset_details["instanceType"]},
                ":operatingSystem": {"S": stackset_details["operatingSystemName"]},
                ":connectionProtocol": {"S": stackset_details["connectionProtocol"]},
                ":privateIp": {"S": stackset_details["private_ip"]},
                ":instanceId": {"S": stackset_details["instance_id"]},
                ":instanceStatus": {"S": stackset_details["state"]},
            },
            ExpressionAttributeNames={
                "#region": "region",
            },
        )

    exit(0)


if __name__ == "__main__":
    migrate()
