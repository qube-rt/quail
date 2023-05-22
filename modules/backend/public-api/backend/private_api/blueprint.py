from flask import Blueprint

from backend.private_api import views


def create_blueprint():
    blueprint = Blueprint("private_api", __name__, url_prefix="/private-api")
    register_routes(blueprint)

    return blueprint


def register_routes(blueprint):
    # Add rules for serving the API
    blueprint.add_url_rule("/provision", "provision", view_func=views.post_provision)
