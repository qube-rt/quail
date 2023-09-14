from http import HTTPStatus


def test_get_params_success(public_client, permission_table, permission_table_name):
    response = public_client.get("/param")

    assert "instance_types" in response.json
    assert "operating_systems" not in response.json
    assert "max_days_to_expiry" in response.json
    assert "max_instance_count" in response.json
    assert "max_extension_count" in response.json
