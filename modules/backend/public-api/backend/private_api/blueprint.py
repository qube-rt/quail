from flask import Blueprint

from backend.private_api import views


def create_blueprint():
    # TODO - make the root of the api come from settings
    # blueprint = Blueprint("private_api", __name__, url_prefix="/prod")
    blueprint = Blueprint("private_api", __name__)
    register_routes(blueprint)

    return blueprint


def register_routes(blueprint):
    # Add rules for serving the API
    # blueprint.add_url_rule("/provision", "provision", view_func=views.post_provision)
    # blueprint.add_url_rule("/wait", "wait", view_func=views.wait)
    blueprint.add_url_rule("/provision", "provision", view_func=lambda: ({"path": "provision"}, 200))
    blueprint.add_url_rule("/", "root", view_func=lambda: ({"path": "root"}, 200))
    blueprint.add_url_rule("/prod/provision", "prodprovision", view_func=lambda: ({"path": "prodprovision"}, 200))