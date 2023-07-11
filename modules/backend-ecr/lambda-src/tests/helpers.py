from datetime import datetime, timedelta


class StackSetNotFound(Exception):
    pass


def add_stackset_to_state(dynamodb_client, table_name, stackset_id, username, email, extension_count=0, expiry=None):
    if not expiry:
        expiry = datetime.now() + timedelta(days=1)

    dynamodb_client.put_item(
        TableName=table_name,
        Item={
            "stacksetID": {"S": stackset_id},
            "username": {"S": username},
            "email": {"S": email},
            "extensionCount": {"N": str(extension_count)},
            "expiry": {"S": expiry.isoformat()},
        },
    )


def get_deleted_stackset(cloudformation, stackset_id):
    list_stacksets_response = cloudformation.list_stack_sets()
    for stackset in list_stacksets_response["Summaries"]:
        if stackset["StackSetId"] == stackset_id:
            return stackset

    raise StackSetNotFound()
