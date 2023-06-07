from http import HTTPStatus


def test_healthckeck(client_anonymous):
    url = "/healthcheck"

    response = client_anonymous.get(url)

    assert response.status_code == HTTPStatus.NO_CONTENT
