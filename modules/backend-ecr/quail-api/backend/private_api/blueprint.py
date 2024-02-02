from flask import Blueprint

from backend.private_api import views


def create_blueprint():
    blueprint = Blueprint("private_api", __name__)
    register_routes(blueprint)

    return blueprint


def register_routes(blueprint):
    # Add rules for serving the API
    blueprint.add_url_rule("/provision", "provision", view_func=views.post_provision, methods=["post"])
    blueprint.add_url_rule("/wait", "wait", view_func=views.get_wait)
    blueprint.add_url_rule(
        "/waitForUpdateCompletion",
        "wait-for-update-completion",
        view_func=views.get_wait_for_update_completion,
    )
    blueprint.add_url_rule(
        "/updateComplete",
        "update-complete",
        view_func=views.post_update_complete,
        methods=["post"],
    )
    blueprint.add_url_rule(
        "/updateFailure",
        "update-failure",
        view_func=views.post_update_failure,
        methods=["post"],
    )
    blueprint.add_url_rule(
        "/notifySuccess",
        "notify-success",
        view_func=views.post_notify_success,
        methods=["post"],
    )
    blueprint.add_url_rule(
        "/notifyFailure",
        "notify-failure",
        view_func=views.post_notify_failure,
        methods=["post"],
    )
    blueprint.add_url_rule(
        "/cleanupStart",
        "cleanup-start",
        view_func=views.post_cleanup_start,
        methods=["post"],
    )
    blueprint.add_url_rule(
        "/cleanupComplete",
        "cleanup-complete",
        view_func=views.post_cleanup_complete,
        methods=["post"],
    )
    blueprint.add_url_rule(
        "/cleanupSchedule",
        "cleanup-schedule",
        view_func=views.post_cleanup_schedule,
        methods=["post"],
    )
    # Temporary endpoint
    # TODO: Clean up
    blueprint.add_url_rule(
        "/migrateData",
        "migrate-data",
        view_func=views.post_migrate_data,
        methods=["post"],
    )
