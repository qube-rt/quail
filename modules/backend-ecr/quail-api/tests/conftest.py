"""Defines fixtures available to all tests."""
import os
import logging
import json

import pytest
from flask.testing import FlaskClient

from backend.app import create_public_app, create_private_app

from flask.testing import FlaskClient


class AuthenticatedClient(FlaskClient):
    def __init__(self, *args, **kwargs):
        self.claims = kwargs.pop("claims")
        super().__init__(*args, **kwargs)

    def open(self, *args, **kwargs):
        headers = kwargs.setdefault("headers", {})
        headers.setdefault("X-Amzn-Request-Context", self.claims)
        return super().open(*args, **kwargs)


@pytest.fixture(scope="session")
def private_app():
    """Create application for the tests."""
    _app = create_private_app("backend.settings.test")
    _app.logger.setLevel(logging.CRITICAL)
    ctx = _app.test_request_context()
    ctx.push()

    yield _app

    ctx.pop()


@pytest.fixture()
def public_app(permission_table_name):
    """Create application for the tests."""
    os.environ["DYNAMODB_PERMISSIONS_TABLE_NAME"] = permission_table_name

    _app = create_public_app("backend.settings.test")
    _app.logger.setLevel(logging.DEBUG)
    ctx = _app.test_request_context()
    ctx.push()

    yield _app

    ctx.pop()


@pytest.fixture()
def public_client(public_app):
    """Create application for the tests."""
    # return public_app.test_client()
    public_app.test_client_class = AuthenticatedClient
    claims = json.dumps({
        "authorizer": {
            "jwt": {
                "claims": {
                    "email": "john@doe.test",
                    # "groups": "quail-developers,admins,private",
                    "groups": "private",
                    "name": "John Doe"
                }
            }
        }
    })

    with public_app.test_client(claims=claims) as client:
        yield client


@pytest.fixture
def client_anonymous(public_app):
    public_app.test_client_class = FlaskClient
    yield public_app.test_client()


import os
import json
from datetime import datetime, timedelta

import boto3
import pytest
from moto import mock_dynamodb, mock_cloudformation, mock_sts, mock_s3

permission_data = {
    "public": {
        "instance-types": ["t3.nano", "t3.micro", "t3.small"],
        "operating-systems": [
            {
                "name": "AWS Linux 2",
                "connection-protocol": "ssh",
                "instance-profile-name": "fake_profile_name",
                "template-filename": "cfn-templates/aws_linux.yaml",
                "user-data-file": "user-data/linux.sh",
                "region-map": {
                    "eu-west-1": {"security-group": "fake_security_group", "ami": "ami-0bb3fad3c0286ebd5"},
                    "us-east-1": {"security-group": "fake_security_group", "ami": "ami-09te47d2ba12ee1ff75"},
                },
            },
            {
                "name": "Ubuntu 20.04",
                "connection-protocol": "ssh",
                "instance-profile-name": "fake_profile_name",
                "template-filename": "cfn-templates/ubuntu_2004.yaml",
                "user-data-file": "user-data/linux.sh",
                "region-map": {"eu-west-1": {"security-group": "fake_security_group", "ami": "ami-0aef57767f5404a3c"}},
            },
            {
                "name": "Windows Server 2019",
                "connection-protocol": "rdp",
                "instance-profile-name": "fake_profile_name",
                "template-filename": "cfn-templates/windows_server_2019.yaml",
                "user-data-file": "user-data/windows.ps1",
                "region-map": {
                    "eu-west-1": {"security-group": "fake_security_group", "ami": "ami-0a262e3ac12949132"},
                    "us-east-1": {"security-group": "fake_security_group", "ami": "ami-0eb7fbcc77e5e6ec6"},
                },
            },
        ],
        "max-instance-count": "5",
        "max-days-to-expiry": "7",
        "max-extension-count": "3",
    },
    "private": {
        "instance-types": ["t3.micro", "t3.small"],
        "operating-systems": [
            {
                "name": "AWS Linux 2",
                "instance-profile-name": "fake_profile_name",
                "connection-protocol": "ssh",
                "template-filename": "cfn-templates/aws_linux.yaml",
                "user-data-file": "user-data/linux.sh",
                "region-map": {"eu-west-1": {"security-group": "fake_security_group", "ami": "ami-0bb3fad3c0286ebd5"}},
            },
            {
                "name": "Windows Server 2019",
                "instance-profile-name": "fake_profile_name",
                "connection-protocol": "rdp",
                "template-filename": "cfn-templates/windows_server_2019.yaml",
                "user-data-file": "user-data/windows.ps1",
                "region-map": {"eu-west-1": {"security-group": "fake_security_group", "ami": "ami-0a262e3ac12949132"}},
            },
            {
                "name": "Ubuntu 20.04",
                "instance-profile-name": "fake_profile_name",
                "connection-protocol": "ssh",
                "template-filename": "cfn-templates/ubuntu_2004.yaml",
                "user-data-file": "user-data/linux.sh",
                "region-map": {"eu-west-1": {"security-group": "fake_security_group", "ami": "ami-0aef57767f5404a3c"}},
            },
        ],
        "max-instance-count": "5",
        "max-days-to-expiry": "3",
        "max-extension-count": "3",
    },
}


regional_data = {
    "eu-west-1": {
        "ssh-key-name": "eu-west-1 key",
        "vpc-id": "eu-west-1 VPC",
        "subnet-id": ["eu-west-1 subnet"],
    },
    "us-east-1": {
        "ssh-key-name": "us-east-1 key",
        "vpc-id": "us-east-1 VPC",
        "subnet-id": ["us-east-1 subnet"],
    },
}


state_data = [
    {
        "stackset_id": "0001",
        "username": "alice",
        "email": "alice@example.com",
        "extension_count": "0",
        "expiry": datetime.now() + timedelta(days=1),
    },
    {
        "stackset_id": "0002",
        "username": "alice",
        "email": "alice@example.com",
        "extension_count": "3",
        "expiry": datetime.now() + timedelta(days=3),
    },
    {
        "stackset_id": "0003",
        "username": "bob",
        "email": "bob@example.com",
        "extension_count": "0",
        "expiry": datetime.now() + timedelta(days=1),
    },
]

dummy_cfn_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 2",
    "Resources": {},
}
dummy_cfn_template_json = json.dumps(dummy_cfn_template)


@pytest.fixture(autouse=True)
def aws_credentials():
    """
    Mocked AWS Credentials for moto. This means that AWS calls will fail
    even if they haven't been mocked correctly.
    """
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def account_id():
    account_id = "123456789"
    os.environ["MOTO_ACCOUNT_ID"] = account_id
    with mock_sts():
        yield account_id


@pytest.fixture
def permission_table_name():
    return "permissions_table"


@pytest.fixture
def permission_table(dynamodb, permission_table_name):
    dynamodb.create_table(
        AttributeDefinitions=[
            {
                "AttributeName": "group",
                "AttributeType": "S",
            },
        ],
        KeySchema=[
            {
                "AttributeName": "group",
                "KeyType": "HASH",
            },
        ],
        BillingMode="PAY_PER_REQUEST",
        TableName=permission_table_name,
    )

    for group, values in permission_data.items():
        dynamodb.put_item(
            TableName=permission_table_name,
            Item={
                "group": {"S": group},
                "instanceTypes": {"SS": values["instance-types"]},
                "operatingSystems": {"S": json.dumps(values["operating-systems"])},
                "maxInstanceCount": {"N": values["max-instance-count"]},
                "maxExtensionCount": {"N": values["max-extension-count"]},
                "maxDaysToExpiry": {"N": values["max-days-to-expiry"]},
            },
        )

    yield dynamodb


# @pytest.fixture
# def regional_table_name():
#     return "regional_table"


# @pytest.fixture
# def regional_table(dynamodb, regional_table_name):
#     dynamodb.create_table(
#         AttributeDefinitions=[
#             {
#                 "AttributeName": "region",
#                 "AttributeType": "S",
#             },
#         ],
#         KeySchema=[
#             {
#                 "AttributeName": "region",
#                 "KeyType": "HASH",
#             },
#         ],
#         BillingMode="PAY_PER_REQUEST",
#         TableName=regional_table_name,
#     )

#     for region, values in regional_data.items():
#         dynamodb.put_item(
#             TableName=regional_table_name,
#             Item={
#                 "region": {"S": region},
#                 "sshKeyName": {"S": values["ssh-key-name"]},
#                 "vpcId": {"S": values["vpc-id"]},
#                 "subnetId": {"SS": values["subnet-id"]},
#             },
#         )

#     yield dynamodb


# @pytest.fixture
# def state_table_name():
#     return "state_table"


# @pytest.fixture
# def state_table_empty(dynamodb, state_table_name):
#     dynamodb.create_table(
#         AttributeDefinitions=[
#             {
#                 "AttributeName": "stacksetID",
#                 "AttributeType": "S",
#             },
#         ],
#         KeySchema=[
#             {
#                 "AttributeName": "stacksetID",
#                 "KeyType": "HASH",
#             },
#         ],
#         BillingMode="PAY_PER_REQUEST",
#         TableName=state_table_name,
#     )
#     yield dynamodb


# @pytest.fixture
# def state_table(state_table_empty, state_table_name):
#     for entry in state_data:
#         state_table_empty.put_item(
#             TableName=state_table_name,
#             Item={
#                 "stacksetID": {"S": entry["stackset_id"]},
#                 "username": {"S": entry["username"]},
#                 "email": {"S": entry["email"]},
#                 "extensionCount": {"N": entry["extension_count"]},
#                 "expiry": {"S": entry["expiry"].isoformat()},
#             },
#         )

#     yield state_table_empty


@pytest.fixture
def dynamodb(account_id):
    with mock_dynamodb():
        mock_client = boto3.client("dynamodb")
        yield mock_client


# @pytest.fixture
# def cloudformation():
#     with mock_cloudformation():
#         mock_client = boto3.client("cloudformation")
#         yield mock_client


# @pytest.fixture
# def s3():
#     with mock_s3():
#         mock_client = boto3.client("s3")
#         yield mock_client


# @pytest.fixture
# def template_bucket(s3):
#     bucket_name = "cfn-data-bucket"
#     s3.bucket_name = bucket_name
#     s3.create_bucket(Bucket=bucket_name)
#     s3.put_object(Bucket=bucket_name, Body=dummy_cfn_template_json, Key="cfn-templates/aws_linux.yaml")
#     s3.put_object(Bucket=bucket_name, Body=dummy_cfn_template_json, Key="cfn-templates/ubuntu_2004.yaml")
#     s3.put_object(Bucket=bucket_name, Body=dummy_cfn_template_json, Key="cfn-templates/windows_server_2019.yaml")

#     s3.put_object(Bucket=bucket_name, Body=dummy_cfn_template_json, Key="user-data/linux.sh")
#     s3.put_object(Bucket=bucket_name, Body=dummy_cfn_template_json, Key="user-data/windows.ps1")

#     return s3
