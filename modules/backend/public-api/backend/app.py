"""The app module, containing the app factory function."""
import logging
import sys
import json
from time import strftime

from flask import Flask, request
from flask_cors import CORS

from backend import commands
from backend.exceptions import BaseQuailException
from backend import views


def create_app(config_object="backend.settings.prod"):
    """Create application factory, as explained here: http://flask.pocoo.org/docs/patterns/appfactories/.

    :param config_object: The configuration object to use.
    """
    app = Flask(__name__.split(".")[0])
    app.config.from_object(config_object)

    register_routes(app)
    register_errorhandlers(app)
    register_hooks(app)
    register_extensions(app)
    register_shellcontext(app)
    register_commands(app)
    configure_logger(app)

    return app


def register_hooks(app):
    """Register Flask hooks."""

    @app.before_request
    def before_request_func():
        timestamp = strftime("[%Y-%b-%d %H:%M]")
        app.logger.info(
            "Before request: %s %s %s %s %s %s",
            timestamp,
            request.remote_addr,
            request.method,
            request.scheme,
            request.full_path,
            request.headers.items(),
        )

    @app.after_request
    def after_request_func(response):
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


def register_extensions(app):
    """Register Flask extensions."""
    # CORS(app, resources={r"/*": {"origins": "*"}})
    CORS(app)
    return None


def register_errorhandlers(app):
    """Register error handlers."""

    def render_error(error):
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, "code", 500)
        return {}, error_code

    for errcode in [401, 404, 500]:
        app.register_error_handler(errcode, render_error)

    def translate_exception(error_code, message, exception):
        """Traps known exceptions and translates them to error responses."""
        return {"error": message}, error_code

    app.register_error_handler(BaseQuailException, lambda e: translate_exception(e.status_code, e.message, e))

    return None


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
    # Add rules for serving the react SPA
    app.add_url_rule("/healthcheck", "healthcheck", view_func=views.get_healthcheck)
    app.add_url_rule("/param", "params:list", view_func=views.get_params)
    app.add_url_rule("/instance", "instance:list_get", view_func=views.get_instances, methods=["get"])
    app.add_url_rule("/instance", "instance:list_post", view_func=views.post_instances, methods=["post"])
    app.add_url_rule(
        "/instance/<stackset_id>/start",
        "instance:detail_post_start",
        view_func=views.post_instance_start,
        methods=["post"],
    )
    app.add_url_rule(
        "/instance/<stackset_id>/stop",
        "instance:detail_post_stop",
        view_func=views.post_instance_stop,
        methods=["post"],
    )
    app.add_url_rule(
        "/instance/<stackset_id>/extend",
        "instance:detail_post_extend",
        view_func=views.post_instance_extend,
        methods=["post"],
    )
    app.add_url_rule(
        "/instance/<stackset_id>", "instance:detail_patch", view_func=views.patch_instance, methods=["patch"]
    )
    app.add_url_rule(
        "/instance/<stackset_id>", "instance:detail_delete", view_func=views.delete_instances, methods=["delete"]
    )
