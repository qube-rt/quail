from http import HTTPStatus


def test_healthckeck(client):
    url = "/api/healthcheck/"

    response = client.get(url)

    assert response.status_code == HTTPStatus.NO_CONTENT
