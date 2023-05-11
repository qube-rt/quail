"""Defines fixtures available to all tests."""
import logging

import pytest
from flask.testing import FlaskClient

from backend.app import create_app


@pytest.fixture(scope="session")
def app():
    """Create application for the tests."""
    _app = create_app("backend.settings.test")
    _app.logger.setLevel(logging.CRITICAL)
    ctx = _app.test_request_context()
    ctx.push()

    yield _app

    ctx.pop()


@pytest.fixture
def client_anonymous(app):
    app.test_client_class = FlaskClient
    yield app.test_client()
