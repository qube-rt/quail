from datetime import datetime, timedelta
import pytest

from utils import (
    get_permissions_for_all_groups,
    PermissionsMissing,
    get_os_config,
    get_params_for_region,
    get_stackset_state_data,
    update_stackset,
    get_owned_stacksets,
    CrossAccountStackSetException,
    get_instance_details,
)
from .conftest import dummy_cfn_template_json


def test_get_permissions_for_all_groups_no_data(permission_table, permission_table_name):
    with pytest.raises(PermissionsMissing):
        get_permissions_for_all_groups(table_name=permission_table_name, group_name="nonexistent")


def test_get_permissions_for_all_groups_success(permission_table, permission_table_name):
    permissions = get_permissions_for_all_groups(table_name=permission_table_name, group_name="private")

    assert "instance_types" in permissions
    assert "operating_systems" in permissions
    assert "max_days_to_expiry" in permissions
    assert "max_instance_count" in permissions
    assert "max_extension_count" in permissions


def test_get_os_config_no_group_data(permission_table, permission_table_name):
    with pytest.raises(PermissionsMissing):
        get_os_config(table_name=permission_table_name, group_name="nonexistent", os_name="nonexistent")


def test_get_os_config_no_os_data(permission_table, permission_table_name):
    with pytest.raises(PermissionsMissing):
        get_os_config(table_name=permission_table_name, group_name="private", os_name="nonexistent")


def test_get_os_config_success(permission_table, permission_table_name):
    config = get_os_config(table_name=permission_table_name, group_name="private", os_name="AWS Linux 2")

    assert "name" in config
    assert "instance-profile-name" in config
    assert "connection-protocol" in config
    assert "template-filename" in config
    assert "user-data-file" in config
    assert "region-map" in config


def test_get_params_for_region_no_data(regional_table, regional_table_name):
    with pytest.raises(PermissionsMissing):
        get_params_for_region(table_name=regional_table_name, region="nonexistent")


def test_get_params_for_region_success(regional_table, regional_table_name):
    region = get_params_for_region(table_name=regional_table_name, region="eu-west-1")

    assert "vpc_id" in region
    assert "ssh_key_name" in region
    assert "subnet_id" in region


def test_get_owned_stacksets_supseruser_success(state_table, state_table_name):
    stacksets = get_owned_stacksets(table_name=state_table_name, email="alice@example.com")

    # Should fetch only stacksets belonging to user
    assert len(stacksets) == 2
    assert "stackset_id" in stacksets[0]
    assert "expiry" in stacksets[0]
    assert "extension_count" in stacksets[0]
    assert "username" in stacksets[0]
    assert "email" in stacksets[0]


def test_get_owned_stacksets_non_supseruser_success(state_table, state_table_name):
    stacksets = get_owned_stacksets(table_name=state_table_name, email="charlie@example.com", is_superuser=True)

    # Should fetch all stacksets
    assert len(stacksets) == 3


def test_get_instance_details_non_supseruser_across_accounts_error(account_id, cloudformation):
    response = cloudformation.create_stack_set(
        StackSetName="fake-name",
        TemplateBody=dummy_cfn_template_json,
        PermissionModel="SELF_MANAGED",
        Parameters=[
            {
                "ParameterKey": "AMI",
                "ParameterValue": "ami",
            },
            {
                "ParameterKey": "SecurityGroupId",
                "ParameterValue": "security-group",
            },
        ],
    )
    stackset_id = response["StackSetId"]

    cloudformation.create_stack_instances(
        StackSetName=stackset_id,
        Accounts=["fake_account"],
        Regions=["us-east-1"],
    )

    params = {
        "stackset_id": stackset_id,
        "expiry": datetime.now() + timedelta(days=1),
        "username": "alice",
        "email": "alice@example.com",
        "extension_count": 0,
    }

    with pytest.raises(CrossAccountStackSetException):
        get_instance_details(stacksets=[params])


@pytest.mark.xfail(reason="Cloudformation StackSet instance mocking in moto lacks depth to simulate this test")
def test_get_instance_details_non_supseruser_success():
    assert False


@pytest.mark.xfail(reason="Cloudformation StackSet instance mocking in moto lacks depth to simulate this test")
def test_get_instance_details_supseruser_success():
    assert False


def test_get_stackset_state_data_no_data(state_table, state_table_name):
    results = get_stackset_state_data(stackset_id="nonexistent", table_name=state_table_name)

    assert results == {}


def test_get_stackset_state_data_success(state_table, state_table_name):
    results = get_stackset_state_data(stackset_id="0001", table_name=state_table_name)

    assert "stackset_id" in results
    assert "username" in results
    assert "email" in results
    assert "extension_count" in results
    assert "expiry" in results


def test_update_stackset_success(cloudformation):
    response = cloudformation.create_stack_set(
        StackSetName="fake-name",
        TemplateBody="fake_body",
        PermissionModel="SELF_MANAGED",
        Parameters=[
            {
                "ParameterKey": "AMI",
                "ParameterValue": "ami",
            },
            {
                "ParameterKey": "SecurityGroupId",
                "ParameterValue": "security-group",
            },
        ],
    )
    stackset_id = response["StackSetId"]

    update_stackset(stackset_id=stackset_id, AMI="new_ami")

    stackset = cloudformation.describe_stack_set(StackSetName=stackset_id)
    parameters = stackset["StackSet"]["Parameters"]
    ami = [item["ParameterValue"] for item in parameters if item["ParameterKey"] == "AMI"][0]
    assert ami == "new_ami"
