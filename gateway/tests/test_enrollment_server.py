from enrollment_server import create_app


def test_enrollment_server_zone_rejection(monkeypatch):
    monkeypatch.setenv("GATEWAY_ZONE", "North")
    client = create_app().test_client()
    response = client.post("/enroll", json={"sensor_id": "s1", "zone": "South"})
    assert response.status_code == 403


def test_health_endpoint(monkeypatch):
    monkeypatch.setenv("GATEWAY_ZONE", "North")
    client = create_app().test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "zone": "North"}


def test_enroll_success(monkeypatch):
    monkeypatch.setenv("GATEWAY_ZONE", "North")
    client = create_app().test_client()
    response = client.post("/enroll", json={"sensor_id": "s1", "zone": "North"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["gateway_public_key"]
    assert body["ca_cert"]
    assert body["sensor_certificate"]
