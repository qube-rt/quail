import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from attrdict import AttrDict

from cleanup_complete import handler as cleanup_complete
from delete_instances import handler as delete_instances
from get_params import handler as get_params
from patch_instance import handler as patch_instance
from post_instances import handler as post_instances
from post_instance_extend import handler as post_instance_extend
from provision import handler as provision
from tests.helpers import add_stackset_to_state


def test_cleanup_complete_success(state_table, state_table_name, cloudformation):
    os.environ["dynamodb_state_table_name"] = state_table_name

    response = cloudformation.create_stack_set(
        StackSetName="fake_name",
        TemplateBody="fake_body",
        PermissionModel="SELF_MANAGED",
    )
    stackset_id = response["StackSetId"]
    add_stackset_to_state(
        dynamodb_client=state_table,
        table_name=state_table_name,
        stackset_id=stackset_id,
        username="alice",
        email="alice@example.com",
    )
    event = {"stackset_id": stackset_id}

    cleanup_complete(event, context=None)

    stackset = cloudformation.describe_stack_set(StackSetName=stackset_id)
    # StackSet has been removed
    assert stackset["StackSet"]["Status"] == "DELETED"

    stackset_state = state_table.get_item(TableName=state_table_name, Key={"stacksetID": {"S": stackset_id}})
    # State entry has been removed from the DB
    assert "Item" not in stackset_state


@pytest.mark.xfail(reason="Cloudformation StackSet instance mocking in moto lacks depth to simulate this test")
def test_cleanup_instances_success():
    assert False


@pytest.mark.xfail(reason="Cloudformation StackSet instance mocking in moto lacks depth to simulate this test")
def test_cleanup_scheduled_success():
    assert False


@patch("delete_instances.initiate_stackset_deprovisioning")
def test_delete_instances_success_non_superuser(initiate_stackset_deprovisioning_mock, state_table, state_table_name):
    cleanup_sfn_arn = "cleanup_sfn_arn"
    os.environ["dynamodb_state_table_name"] = state_table_name
    os.environ["cleanup_sfn_arn"] = cleanup_sfn_arn

    stackset_id = "0001"
    owner_email = "alice@example.com"
    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": owner_email,
                        "profile": "developer",
                        "nickname": "alice",
                        "custom:is_superuser": "0",
                    }
                }
            }
        },
        "pathParameters": {
            "id": stackset_id,
        },
    }

    delete_instances(event, context=None)

    initiate_stackset_deprovisioning_mock.assert_called_with(
        stackset_id=stackset_id,
        cleanup_sfn_arn=cleanup_sfn_arn,
        owner_email=owner_email,
    )


@patch("delete_instances.initiate_stackset_deprovisioning")
def test_delete_instances_success_superuser(initiate_stackset_deprovisioning_mock, state_table, state_table_name):
    cleanup_sfn_arn = "cleanup_sfn_arn"
    os.environ["dynamodb_state_table_name"] = state_table_name
    os.environ["cleanup_sfn_arn"] = cleanup_sfn_arn

    stackset_id = "0001"
    owner_email = "alice@example.com"
    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": "charlie@example.com",
                        "profile": "developer",
                        "nickname": "alice",
                        "custom:is_superuser": "1",
                    }
                }
            }
        },
        "pathParameters": {
            "id": stackset_id,
        },
    }

    delete_instances(event, context=None)

    initiate_stackset_deprovisioning_mock.assert_called_with(
        stackset_id=stackset_id,
        cleanup_sfn_arn=cleanup_sfn_arn,
        owner_email=owner_email,
    )


def test_delete_instances_failue_non_owner(state_table, state_table_name):
    cleanup_sfn_arn = "cleanup_sfn_arn"
    os.environ["dynamodb_state_table_name"] = state_table_name
    os.environ["cleanup_sfn_arn"] = cleanup_sfn_arn

    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": "alice@example.com",
                        "profile": "developer",
                        "nickname": "alice",
                        "custom:is_superuser": "0",
                    }
                }
            }
        },
        "pathParameters": {"id": "0003"},
    }

    response = delete_instances(event, context=None)

    # The specified stackset doesn't exist or the user doesn't have permissions for it
    assert response["statusCode"] == 400


@pytest.mark.xfail(reason="Cloudformation StackSet instance mocking in moto lacks depth to simulate this test")
def test_get_instances_success():
    assert False


def test_get_params_success(permission_table, permission_table_name):
    os.environ["dynamodb_permissions_table_name"] = permission_table_name
    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": "alice@example.com",
                        "profile": "private",
                        "nickname": "alice",
                        "custom:is_superuser": "0",
                    }
                }
            }
        },
    }

    response = get_params(event, context=None)

    assert "instance_types" in response
    assert "operating_systems" not in response
    assert "max_days_to_expiry" in response
    assert "max_instance_count" in response
    assert "max_extension_count" in response


@pytest.mark.xfail(reason="Cloudformation StackSet instance mocking in moto lacks depth to simulate this test")
def test_notify_failure_success():
    assert False


@pytest.mark.xfail(reason="Cloudformation StackSet instance mocking in moto lacks depth to simulate this test")
def test_notify_success_success():
    assert False


def test_patch_instance_failure_for_non_owner(
    permission_table, permission_table_name, state_table_empty, state_table_name
):
    os.environ["dynamodb_permissions_table_name"] = permission_table_name
    os.environ["dynamodb_state_table_name"] = state_table_name

    stackset_id = "fake_id"
    add_stackset_to_state(
        dynamodb_client=state_table_empty,
        table_name=state_table_name,
        stackset_id=stackset_id,
        username="alice",
        email="alice@example.com",
    )

    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": "charlie@example.com",
                        "profile": "developer",
                        "nickname": "charlie",
                        "custom:is_superuser": "0",
                    }
                }
            }
        },
        "pathParameters": {
            "id": stackset_id,
        },
        "body": "{}",
    }

    response = patch_instance(event, context=None)

    # Non owner won't be able to extend the instance
    assert response["statusCode"] == 400
    assert "not authorized" in response["body"]


def test_patch_instance_failure_for_unauthorized_param(
    permission_table, permission_table_name, state_table_empty, state_table_name
):
    os.environ["dynamodb_permissions_table_name"] = permission_table_name
    os.environ["dynamodb_state_table_name"] = state_table_name

    stackset_id = "fake_id"
    add_stackset_to_state(
        dynamodb_client=state_table_empty,
        table_name=state_table_name,
        stackset_id=stackset_id,
        username="alice",
        email="alice@example.com",
    )

    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": "alice@example.com",
                        "profile": "private",
                        "nickname": "alice",
                        "custom:is_superuser": "0",
                    }
                }
            }
        },
        "pathParameters": {
            "id": stackset_id,
        },
        "body": json.dumps({"instanceType": "invalid"}),
    }

    response = patch_instance(event, context=None)

    assert response["statusCode"] == 400
    assert "instanceType" in response["body"]


def test_patch_instance_success_for_owner(
    permission_table, permission_table_name, state_table_empty, state_table_name, cloudformation
):
    os.environ["dynamodb_permissions_table_name"] = permission_table_name
    os.environ["dynamodb_state_table_name"] = state_table_name

    initial_instance_type = "fake"
    final_instance_type = "t3.micro"
    response = cloudformation.create_stack_set(
        StackSetName="fake_name",
        TemplateBody="fake_body",
        PermissionModel="SELF_MANAGED",
        Parameters=[
            {
                "ParameterKey": "InstanceType",
                "ParameterValue": initial_instance_type,
            },
        ],
    )
    stackset_id = response["StackSetId"]
    add_stackset_to_state(
        dynamodb_client=state_table_empty,
        table_name=state_table_name,
        stackset_id=stackset_id,
        username="alice",
        email="alice@example.com",
    )

    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": "alice@example.com",
                        "profile": "private",
                        "nickname": "alice",
                        "custom:is_superuser": "0",
                    }
                }
            }
        },
        "pathParameters": {
            "id": stackset_id,
        },
        "body": json.dumps({"instanceType": final_instance_type}),
    }

    response = patch_instance(event, context=None)

    assert response == {}
    stackset = cloudformation.describe_stack_set(StackSetName=stackset_id)
    params = stackset["StackSet"]["Parameters"]
    actual_instance_type = [item["ParameterValue"] for item in params if item["ParameterKey"] == "InstanceType"][0]
    assert actual_instance_type == final_instance_type


def test_patch_instance_success_for_superuser(
    permission_table, permission_table_name, state_table_empty, state_table_name, cloudformation
):
    os.environ["dynamodb_permissions_table_name"] = permission_table_name
    os.environ["dynamodb_state_table_name"] = state_table_name

    initial_instance_type = "fake"
    final_instance_type = "t3.micro"
    response = cloudformation.create_stack_set(
        StackSetName="fake_name",
        TemplateBody="fake_body",
        PermissionModel="SELF_MANAGED",
        Parameters=[
            {
                "ParameterKey": "InstanceType",
                "ParameterValue": initial_instance_type,
            },
        ],
    )
    stackset_id = response["StackSetId"]
    add_stackset_to_state(
        dynamodb_client=state_table_empty,
        table_name=state_table_name,
        stackset_id=stackset_id,
        username="alice",
        email="alice@example.com",
    )

    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        # Request made by non-owner who is a superuser
                        "email": "charlie@example.com",
                        "profile": "private",
                        "nickname": "charlie",
                        "custom:is_superuser": "1",
                    }
                }
            }
        },
        "pathParameters": {
            "id": stackset_id,
        },
        "body": json.dumps({"instanceType": final_instance_type}),
    }

    response = patch_instance(event, context=None)

    assert response == {}
    stackset = cloudformation.describe_stack_set(StackSetName=stackset_id)
    params = stackset["StackSet"]["Parameters"]
    actual_instance_type = [item["ParameterValue"] for item in params if item["ParameterKey"] == "InstanceType"][0]
    assert actual_instance_type == final_instance_type


def test_post_instance_extend_failure_for_non_owner(
    permission_table, permission_table_name, state_table_empty, state_table_name
):
    os.environ["dynamodb_permissions_table_name"] = permission_table_name
    os.environ["dynamodb_state_table_name"] = state_table_name

    stackset_id = "fake_id"
    add_stackset_to_state(
        dynamodb_client=state_table_empty,
        table_name=state_table_name,
        stackset_id=stackset_id,
        username="alice",
        email="alice@example.com",
    )

    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": "charlie@example.com",
                        "profile": "developer",
                        "nickname": "charlie",
                        "custom:is_superuser": "0",
                    }
                }
            }
        },
        "pathParameters": {
            "id": stackset_id,
        },
    }

    response = post_instance_extend(event, context=None)

    # Non owner won't be able to extend the instance
    assert response["statusCode"] == 400
    assert "not authorized" in response["body"]


def test_post_instance_extend_failure_for_owner_exceeding_extension_limit(
    permission_table, permission_table_name, state_table_empty, state_table_name
):
    os.environ["dynamodb_permissions_table_name"] = permission_table_name
    os.environ["dynamodb_state_table_name"] = state_table_name

    stackset_id = "fake_id"
    add_stackset_to_state(
        dynamodb_client=state_table_empty,
        table_name=state_table_name,
        stackset_id=stackset_id,
        username="alice",
        email="alice@example.com",
        extension_count=20,
    )

    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": "alice@example.com",
                        "profile": "private",
                        "nickname": "alice",
                        "custom:is_superuser": "0",
                    }
                }
            }
        },
        "pathParameters": {
            "id": stackset_id,
        },
    }

    response = post_instance_extend(event, context=None)

    # Non owner won't be able to extend the instance
    assert response["statusCode"] == 400
    assert "cannot extend" in response["body"]


def test_post_instance_extend_success_non_superuser(
    permission_table, permission_table_name, state_table_empty, state_table_name
):
    os.environ["dynamodb_permissions_table_name"] = permission_table_name
    os.environ["dynamodb_state_table_name"] = state_table_name

    stackset_id = "fake_id"
    initial_expiry = datetime.now()
    initial_extension_count = 1
    add_stackset_to_state(
        dynamodb_client=state_table_empty,
        table_name=state_table_name,
        stackset_id=stackset_id,
        username="alice",
        email="alice@example.com",
        extension_count=initial_extension_count,
        expiry=initial_expiry,
    )

    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": "alice@example.com",
                        "profile": "private",
                        "nickname": "alice",
                        "custom:is_superuser": "0",
                    }
                }
            }
        },
        "pathParameters": {
            "id": stackset_id,
        },
    }

    response = post_instance_extend(event, context=None)

    # Expiry time of the stackset extended
    assert response["stackset_id"] == stackset_id
    assert response["can_extend"]
    assert datetime.fromisoformat(response["expiry"]) > initial_expiry

    # Extended expiry time saved in dynamodb
    query = state_table_empty.get_item(TableName=state_table_name, Key={"stacksetID": {"S": stackset_id}})
    assert datetime.fromisoformat(query["Item"]["expiry"]["S"]) > initial_expiry
    assert int(query["Item"]["extensionCount"]["N"]) > initial_extension_count


def test_post_instance_extend_success_for_superuser_exceeding_extension_limit(
    permission_table, permission_table_name, state_table_empty, state_table_name
):
    os.environ["dynamodb_permissions_table_name"] = permission_table_name
    os.environ["dynamodb_state_table_name"] = state_table_name

    stackset_id = "fake_id"
    initial_expiry = datetime.now()
    initial_extension_count = 1
    add_stackset_to_state(
        dynamodb_client=state_table_empty,
        table_name=state_table_name,
        stackset_id=stackset_id,
        username="alice",
        email="alice@example.com",
        extension_count=initial_extension_count,
        expiry=initial_expiry,
    )

    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        # Request from non-owner of the stackset
                        "email": "charlie@example.com",
                        "profile": "private",
                        "nickname": "charlie",
                        "custom:is_superuser": "1",
                    }
                }
            }
        },
        "pathParameters": {
            "id": stackset_id,
        },
    }

    response = post_instance_extend(event, context=None)

    # Expiry time of the stackset extended
    assert response["stackset_id"] == stackset_id
    assert response["can_extend"]
    assert datetime.fromisoformat(response["expiry"]) > initial_expiry

    # Extended expiry time saved in dynamodb
    query = state_table_empty.get_item(TableName=state_table_name, Key={"stacksetID": {"S": stackset_id}})
    assert datetime.fromisoformat(query["Item"]["expiry"]["S"]) > initial_expiry
    assert int(query["Item"]["extensionCount"]["N"]) > initial_extension_count


@pytest.mark.xfail(reason="Cloudformation StackSet instance mocking in moto lacks depth to simulate this test")
def test_post_instance_start_success():
    assert False


@pytest.mark.xfail(reason="Cloudformation StackSet instance mocking in moto lacks depth to simulate this test")
def test_post_instance_stop_success():
    assert False


def test_post_instances_failure_missing_parameters_non_superuser(
    permission_table, permission_table_name, state_table_empty, state_table_name, account_id
):
    provision_sfn_arn = "fake_provision_sfn_arn"
    os.environ["dynamodb_permissions_table_name"] = permission_table_name
    os.environ["dynamodb_state_table_name"] = state_table_name
    os.environ["provision_sfn_arn"] = provision_sfn_arn

    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": "charlie@example.com",
                        "profile": "private",
                        "nickname": "charlie",
                        "custom:is_superuser": "0",
                    }
                }
            }
        },
        "body": "{}",
    }

    response = post_instances(event, context=None)

    assert response["statusCode"] == 400
    message = json.loads(response["body"])["message"]
    assert "instanceName" in message
    assert "region" in message
    assert "operatingSystem" in message
    assert "expiry" in message
    assert "instanceType" in message


def test_post_instances_failure_missing_parameters_for_superuser(
    permission_table, permission_table_name, state_table_empty, state_table_name, account_id
):
    provision_sfn_arn = "fake_provision_sfn_arn"
    os.environ["dynamodb_permissions_table_name"] = permission_table_name
    os.environ["dynamodb_state_table_name"] = state_table_name
    os.environ["provision_sfn_arn"] = provision_sfn_arn

    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": "charlie@example.com",
                        "profile": "private",
                        "nickname": "charlie",
                        "custom:is_superuser": "1",
                    }
                }
            }
        },
        "body": "{}",
    }

    response = post_instances(event, context=None)

    assert response["statusCode"] == 400
    message = json.loads(response["body"])["message"]
    assert "instanceName" in message
    assert "region" in message
    assert "operatingSystem" in message
    assert "expiry" in message
    assert "instanceType" in message
    # Additional fields required for superusers
    assert "email" in message
    assert "username" in message


def test_post_instances_failure_invalid_parameters(
    permission_table, permission_table_name, state_table_empty, state_table_name, account_id
):
    provision_sfn_arn = "fake_provision_sfn_arn"
    os.environ["dynamodb_permissions_table_name"] = permission_table_name
    os.environ["dynamodb_state_table_name"] = state_table_name
    os.environ["provision_sfn_arn"] = provision_sfn_arn

    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": "charlie@example.com",
                        "profile": "private",
                        "nickname": "charlie",
                        "custom:is_superuser": "0",
                    }
                }
            }
        },
        "body": json.dumps(
            {
                "instanceName": "invalid",
                "instanceType": "invalid",
                "region": "invalid",
                "operatingSystem": "invalid",
                "expiry": (datetime.now(tz=timezone.utc) + timedelta(days=24)).isoformat(),
            }
        ),
    }

    response = post_instances(event, context=None)

    assert response["statusCode"] == 400
    message = json.loads(response["body"])["message"]
    assert "region" in message
    assert "operatingSystem" in message
    assert "expiry" in message
    assert "instanceType" in message


def test_post_instances_failure_exceed_instance_limit(
    permission_table, permission_table_name, state_table_empty, state_table_name, account_id
):
    provision_sfn_arn = "fake_provision_sfn_arn"
    os.environ["dynamodb_permissions_table_name"] = permission_table_name
    os.environ["dynamodb_state_table_name"] = state_table_name
    os.environ["provision_sfn_arn"] = provision_sfn_arn

    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": "alice@example.com",
                        "profile": "private",
                        "nickname": "alice",
                        "custom:is_superuser": "0",
                    }
                }
            }
        },
        "body": json.dumps(
            {
                "instanceName": "The Best Instance",
                "instanceType": "t3.micro",
                "region": "eu-west-1",
                "operatingSystem": "AWS Linux 2",
                "expiry": (datetime.now(tz=timezone.utc) + timedelta(days=1)).isoformat(),
            }
        ),
    }
    # Add instances to state data to mimic user exceeding their instance allowance
    for i in range(10):
        add_stackset_to_state(
            dynamodb_client=state_table_empty,
            table_name=state_table_name,
            stackset_id=f"fake_stackset_id_{i}",
            username="alice",
            email="alice@example.com",
        )

    response = post_instances(event, context=None)

    assert response["statusCode"] == 400
    assert "limit exceeded" in response["body"]


@patch("post_instances.provision_stackset")
def test_post_instances_success(
    mock_provision_stackset, permission_table, permission_table_name, state_table_empty, state_table_name, account_id
):
    provision_sfn_arn = "fake_provision_sfn_arn"
    os.environ["dynamodb_permissions_table_name"] = permission_table_name
    os.environ["dynamodb_state_table_name"] = state_table_name
    os.environ["provision_sfn_arn"] = provision_sfn_arn

    requester_email = "alice@example.com"
    requester_username = "alice"
    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": requester_email,
                        "profile": "private",
                        "nickname": requester_username,
                        "custom:is_superuser": "0",
                    }
                }
            }
        },
        "body": json.dumps(
            {
                "instanceName": "The Best Instance",
                "instanceType": "t3.micro",
                "region": "eu-west-1",
                "operatingSystem": "AWS Linux 2",
                "expiry": (datetime.now(tz=timezone.utc) + timedelta(days=1)).isoformat(),
            }
        ),
    }

    response = post_instances(event, context=None)

    assert "sfn_execution_arn" in response
    assert response["email"] == requester_email
    assert response["username"] == requester_username
    mock_provision_stackset.assert_called_once()


@patch("post_instances.provision_stackset")
def test_post_instances_success_superuser_on_behalf_of_other_user(
    mock_provision_stackset, permission_table, permission_table_name, state_table_empty, state_table_name, account_id
):
    provision_sfn_arn = "fake_provision_sfn_arn"
    os.environ["dynamodb_permissions_table_name"] = permission_table_name
    os.environ["dynamodb_state_table_name"] = state_table_name
    os.environ["provision_sfn_arn"] = provision_sfn_arn

    requester_email = "alice@example.com"
    requester_username = "alice"
    instance_email = "charlie@example.com"
    instance_username = "charlie"
    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "email": requester_email,
                        "profile": "private",
                        "nickname": requester_username,
                        "custom:is_superuser": "1",
                    }
                }
            }
        },
        "body": json.dumps(
            {
                "instanceName": "The Best Instance",
                "instanceType": "t3.micro",
                "region": "eu-west-1",
                "operatingSystem": "AWS Linux 2",
                "expiry": (datetime.now(tz=timezone.utc) + timedelta(days=1)).isoformat(),
                "email": instance_email,
                "username": instance_username,
            }
        ),
    }

    response = post_instances(event, context=None)

    assert "sfn_execution_arn" in response
    assert response["email"] == instance_email
    assert response["username"] == instance_username
    mock_provision_stackset.assert_called_once()


def test_provision_success(
    template_bucket,
    permission_table,
    permission_table_name,
    state_table_empty,
    state_table_name,
    regional_table,
    regional_table_name,
    cloudformation,
):
    os.environ["project_name"] = "test_quail"
    os.environ["dynamodb_regional_metadata_table_name"] = regional_table_name
    os.environ["dynamodb_permissions_table_name"] = permission_table_name
    os.environ["dynamodb_state_table_name"] = state_table_name
    os.environ["cfn_data_bucket"] = template_bucket.bucket_name
    os.environ["tag_config"] = json.dumps(
        [{"tag-name": "variable-tag", "tag-value": "$email"}, {"tag-name": "fixed-tag", "tag-value": "fixed-vale"}]
    )

    event = {
        "requestContext": {"authorizer": {"jwt": {}}},
        "Input": {
            "account": "fake_account",
            "region": "eu-west-1",
            "instance_name": "The Best Instance",
            "instance_type": "t3.micro",
            "operating_system": "AWS Linux 2",
            "expiry": (datetime.now(tz=timezone.utc) + timedelta(days=1)).isoformat(),
            "email": "alice@example.com",
            "group": "private",
            "username": "alice",
            "user": {
                "email": "alice@example.com",
                "profile": "private",
                "nickname": "alice",
                "custom:is_superuser": "0",
            },
        },
    }

    response = provision(event, context=AttrDict({"aws_request_id": "123456"}))

    # Verify provisioning results
    assert "stackset_id" in response
    stackset_id = response["stackset_id"]

    stackset = cloudformation.describe_stack_set(StackSetName=stackset_id)
    assert stackset["StackSet"]["Status"] == "ACTIVE"

    stack_instances = cloudformation.list_stack_instances(StackSetName=stackset_id)["Summaries"]
    assert len(stack_instances) == 1
    assert stack_instances[0]["Region"] == "eu-west-1"
    assert stack_instances[0]["Account"] == "fake_account"
