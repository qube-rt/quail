from flask import Blueprint

from backend.public_api import views


def create_blueprint():
    blueprint = Blueprint("public_api", __name__)
    register_routes(blueprint)

    return blueprint


def register_routes(blueprint):
    # Add rules for serving the API
    blueprint.add_url_rule("/param", "params:list", view_func=views.get_params)
    blueprint.add_url_rule("/instance", "instance:list_get", view_func=views.get_instances, methods=["get"])
    blueprint.add_url_rule(
        "/instance",
        "instance:list_post",
        view_func=views.post_instances,
        methods=["post"],
    )
    blueprint.add_url_rule(
        "/instance/<stackset_id>/start",
        "instance:detail_post_start",
        view_func=views.post_instance_start,
        methods=["post"],
    )
    blueprint.add_url_rule(
        "/instance/<stackset_id>/stop",
        "instance:detail_post_stop",
        view_func=views.post_instance_stop,
        methods=["post"],
    )
    blueprint.add_url_rule(
        "/instance/<stackset_id>/extend",
        "instance:detail_post_extend",
        view_func=views.post_instance_extend,
        methods=["post"],
    )
    blueprint.add_url_rule(
        "/instance/<stackset_id>",
        "instance:detail_patch",
        view_func=views.patch_instance,
        methods=["patch"],
    )
    blueprint.add_url_rule(
        "/instance/<stackset_id>",
        "instance:detail_delete",
        view_func=views.delete_instances,
        methods=["delete"],
    )
