"""Defines fixtures available to all tests."""
import logging

import pytest
from flask.testing import FlaskClient

from backend.app import create_public_app, create_private_app


@pytest.fixture(scope="session")
def private_app():
    """Create application for the tests."""
    _app = create_private_app("backend.settings.test")
    _app.logger.setLevel(logging.CRITICAL)
    ctx = _app.test_request_context()
    ctx.push()

    yield _app

    ctx.pop()


@pytest.fixture(scope="session")
def public_app():
    """Create application for the tests."""
    _app = create_public_app("backend.settings.test")
    _app.logger.setLevel(logging.CRITICAL)
    ctx = _app.test_request_context()
    ctx.push()

    yield _app

    ctx.pop()


@pytest.fixture
def client_anonymous(public_app):
    public_app.test_client_class = FlaskClient
    yield public_app.test_client()
