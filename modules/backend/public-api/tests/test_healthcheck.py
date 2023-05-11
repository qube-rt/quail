from http import HTTPStatus


def test_healthckeck(client):
    url = "/healthcheck"

    response = client.get(url)

    assert response.status_code == HTTPStatus.NO_CONTENT
