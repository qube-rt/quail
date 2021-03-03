import boto3

from utils import (
    StackSetExecutionInProgressException,
    STACKSET_OPERATION_INCOMPLETE_STATUSES,
    SYNCHRONIZED_STATUS,
    SUCCESS_DETAILED_STATUS,
    exception_handler,
)


@exception_handler
def handler(event, context):
    stack_name = event["stackset_id"]
    # Whether no operations should cause the function to error. It should be true when creating an instance
    # but false when waiting for delete operations to complete.
    error_if_no_operations = event["error_if_no_operations"]

    client = boto3.client("cloudformation")

    stack_operations = client.list_stack_set_operations(StackSetName=stack_name)
    if error_if_no_operations and not stack_operations["Summaries"]:
        # Fail if the stack operations are still not available
        raise StackSetExecutionInProgressException()

    for operation in stack_operations["Summaries"]:
        # The stackset operation hasn't completed
        if operation["Status"] in STACKSET_OPERATION_INCOMPLETE_STATUSES:
            raise StackSetExecutionInProgressException()

    stack_instances = client.list_stack_instances(StackSetName=stack_name)
    for instance in stack_instances["Summaries"]:
        # Stack instances are in progress of being updated
        if (
            instance["Status"] != SYNCHRONIZED_STATUS
            or instance["StackInstanceStatus"]["DetailedStatus"] != SUCCESS_DETAILED_STATUS
        ):
            raise StackSetExecutionInProgressException()
