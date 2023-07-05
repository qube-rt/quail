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

# AWS config
DYNAMODB_PERMISSIONS_TABLE_NAME = env.str("DYNAMODB_PERMISSIONS_TABLE_NAME")
DYNAMODB_STATE_TABLE_NAME = env.str("DYNAMODB_STATE_TABLE_NAME")
CLEANUP_SFN_ARN = env.str("CLEANUP_SFN_ARN")
CROSS_ACCOUNT_ROLE_NAME = env.str("CROSS_ACCOUNT_ROLE_NAME")
