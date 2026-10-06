def test_health_returns_ok_with_db_connected(client):
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "connected"}


def test_unversioned_health_alias(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "connected"}


def test_request_id_header_is_generated(client):
    response = client.get("/v1/health")
    assert response.headers.get("X-Request-ID")


def test_request_id_header_is_echoed(client):
    response = client.get("/v1/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"
