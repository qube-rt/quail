"""The app module, containing the app factory function."""
import logging
import sys
from time import strftime

import boto3
from flask import Flask, request
from flask_cors import CORS

from backend import commands, views
from backend.aws_utils import AwsUtils
from backend.exceptions import BaseQuailException


def create_base_app(config_object):
    """Create application factory, as explained here: http://flask.pocoo.org/docs/patterns/appfactories/.

    :param config_object: The configuration object to use.
    """
    app = Flask(__name__.split(".")[0], static_folder=None)
    app.config.from_object(config_object)

    register_errorhandlers(app)
    register_hooks(app)
    register_shellcontext(app)
    register_commands(app)
    register_routes(app)
    configure_logger(app)
    configure_aws_utils(app)

    return app


def create_public_app(config_object="backend.settings.prod"):
    app = create_base_app(config_object=config_object)
    configure_cors(app)

    from backend.public_api.blueprint import create_blueprint

    public_blueprint = create_blueprint()
    app.register_blueprint(public_blueprint)

    return app


def create_private_app(config_object="backend.settings.prod"):
    app = create_base_app(config_object=config_object)
    from backend.private_api.blueprint import create_blueprint

    private_blueprint = create_blueprint()
    app.register_blueprint(private_blueprint)

    return app


def register_hooks(app):
    """Register Flask hooks."""

    @app.before_request
    def before_request_logger():
        timestamp = strftime("[%Y-%b-%d %H:%M]")
        app.logger.info(
            "Before request: %s %s %s %s %s %s",
            timestamp,
            request.remote_addr,
            request.method,
            request.scheme,
            request.full_path,
            list(request.headers.items()),
        )

    @app.after_request
    def after_request_logger(response):
        timestamp = strftime("[%Y-%b-%d %H:%M]")
        app.logger.info(
            "After request: %s %s %s %s %s %s",
            timestamp,
            request.remote_addr,
            request.method,
            request.scheme,
            request.full_path,
            response.status,
        )
        return response

    @app.after_request
    def step_function_notifier(response):
        # If the API is invoked by step functions and the request succeeds
        # send a success signal
        task_token = request.headers.get("TaskToken")
        if task_token and 200 <= response.status_code < 300:
            sfn_client = boto3.client("stepfunctions")
            sfn_client.send_task_success(taskToken=task_token, output=response.get_data(as_text=True))

        return response


def configure_cors(app):
    """Register Flask extensions."""
    CORS(app)


def register_errorhandlers(app):
    """Register error handlers."""

    # For exceptions, if invoked by a Step Function with a task token,
    # send a failure signal
    def send_step_function_error(error):
        task_token = request.headers.get("TaskToken")
        if task_token:
            app.logger.info(
                "send_step_function_error.task_token %s %s",
                error.__class__.__name__,
                error.message if hasattr(error, "message") else "Internal Server Error",
            )
            sfn_client = boto3.client("stepfunctions")
            sfn_client.send_task_failure(
                taskToken=task_token,
                error=error.__class__.__name__,
                cause=error.message if hasattr(error, "message") else "Internal Server Error",
            )

    def render_error(error):
        app.logger.error("render_error handler: %s", error, exc_info=True)
        send_step_function_error(error)
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, "code", 500)
        return {}, error_code

    for errcode in [401, 404, 500]:
        app.register_error_handler(errcode, render_error)

    def translate_exception(error_code, message, exception):
        """Traps known exceptions and translates them to error responses."""
        send_step_function_error(exception)
        return {"error": message}, error_code

    app.register_error_handler(BaseQuailException, lambda e: translate_exception(e.status_code, e.message, e))

    # Register a catch-all Exception trap that will notify step functions of the failure
    app.register_error_handler(Exception, render_error)


def register_shellcontext(app):
    """Register shell context objects."""

    def shell_context():
        """Shell context objects."""
        return {}

    app.shell_context_processor(shell_context)


def register_commands(app):
    """Register Click commands."""
    app.cli.add_command(commands.test)


def configure_logger(app):
    """Configure loggers."""
    handler = logging.StreamHandler(sys.stdout)
    if not app.logger.handlers:
        app.logger.addHandler(handler)


def register_routes(app):
    # Add rules for serving the API
    app.add_url_rule("/healthcheck", "healthcheck", view_func=views.get_healthcheck)


def configure_aws_utils(app):
    app.aws = AwsUtils(
        permissions_table_name=app.config["DYNAMODB_PERMISSIONS_TABLE_NAME"],
        regional_data_table_name=app.config["DYNAMODB_REGIONAL_METADATA_TABLE_NAME"],
        state_table_name=app.config["DYNAMODB_STATE_TABLE_NAME"],
        cross_account_role_name=app.config["CROSS_ACCOUNT_ROLE_NAME"],
        admin_group_name=app.config["ADMIN_GROUP_NAME"],
        provision_sfn_arn=app.config["PROVISION_SFN_ARN"],
        cleanup_sfn_arn=app.config["CLEANUP_SFN_ARN"],
        error_topic_arn=app.config["SNS_ERROR_TOPIC_ARN"],
        cfn_data_bucket=app.config["CFN_DATA_BUCKET"],
        execution_role_name=app.config["STACK_SET_EXECUTION_ROLE_NAME"],
        admin_role_arn=app.config["STACK_SET_ADMIN_ROLE_ARN"],
        logger=app.logger,
    )
