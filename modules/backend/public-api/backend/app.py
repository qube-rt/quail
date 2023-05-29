"""The app module, containing the app factory function."""
import logging
import sys
from time import strftime

from flask import Flask, request
from flask_cors import CORS

from backend import commands
from backend.exceptions import BaseQuailException
from backend import views

def create_base_app(config_object="backend.settings.prod"):
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

    return app


def create_public_app():
    app = create_base_app()
    configure_cors(app)

    from backend.public_api.blueprint import create_blueprint
    public_blueprint = create_blueprint()
    app.register_blueprint(public_blueprint)

    return app


def create_private_app():
    app = create_base_app()
    from backend.private_api.blueprint import create_blueprint
    private_blueprint = create_blueprint()
    app.register_blueprint(private_blueprint)

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
            list(request.headers.items()),
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


def configure_cors(app):
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
    # Add rules for serving the API
    app.add_url_rule("/healthcheck", "healthcheck", view_func=views.get_healthcheck)
