"""Application configuration.

Most configuration is set via environment variables.

For local development, use a .env file to set
environment variables.
"""
from environs import Env

env = Env()
env.read_env()

ENV = env.str("FLASK_ENV", default="production")
DEBUG = ENV == "development"
SECRET_KEY = env.str("SECRET_KEY")
SEND_FILE_MAX_AGE_DEFAULT = env.int("SEND_FILE_MAX_AGE_DEFAULT", default=3600)
CACHE_TYPE = "simple"  # Can be "memcached", d"redis", etc.

# JWT settings
JWT_ISSUER = env.str("JWT_ISSUER", default="quail")

PROJECT_NAME = env.str("PROJECT_NAME")  # noqa: F405
NOTIFICATION_EMAIL = env.str("NOTIFICATION_EMAIL")  # noqa: F405
ADMIN_EMAIL = env.str("ADMIN_EMAIL")  # noqa: F405
ADMIN_GROUP_NAME = env.str("ADMIN_GROUP_NAME")  # noqa: F405

# AWS config
DYNAMODB_PERMISSIONS_TABLE_NAME = env.str("DYNAMODB_PERMISSIONS_TABLE_NAME")
DYNAMODB_STATE_TABLE_NAME = env.str("DYNAMODB_STATE_TABLE_NAME")
DYNAMODB_REGIONAL_METADATA_TABLE_NAME = env.str("DYNAMODB_REGIONAL_METADATA_TABLE_NAME")  # noqa: F405

PROVISION_SFN_ARN = env.str("PROVISION_SFN_ARN")  # noqa: F405
CLEANUP_SFN_ARN = env.str("CLEANUP_SFN_ARN")
CFN_DATA_BUCKET = env.str("CFN_DATA_BUCKET")  # noqa: F405

SNS_ERROR_TOPIC_ARN = env.str("SNS_ERROR_TOPIC_ARN")  # noqa: F405
CROSS_ACCOUNT_ROLE_NAME = env.str("CROSS_ACCOUNT_ROLE_NAME")

CLEANUP_NOTICE_NOTIFICATION_HOURS = env.str("CLEANUP_NOTICE_NOTIFICATION_HOURS")  # noqa: F405
TAG_CONFIG = env.str("TAG_CONFIG")  # noqa: F405
