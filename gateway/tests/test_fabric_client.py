from fabric_client import FabricClient


def test_fabric_client_mocked_transaction_calls():
    calls = []

    def invoker(name, payload):
        calls.append((name, payload))
        return {"decision": "GRANT", "nonce": payload["nonce"]}

    client = FabricClient(invoker=invoker, jitter=0, sleeper=lambda _seconds: None)
    response = client.check_access("sensor-1", "North")
    assert response["decision"] == "GRANT"
    assert calls[0][0] == "CheckAccess"
    assert calls[0][1]["device_id"] == "sensor-1"
    assert calls[0][1]["nonce"]

    client.submit_sensor_reading({"device_id": "sensor-1", "reading_id": "r1", "value": 7})
    client.revoke_certificate("cert-1", "keyCompromise")
    assert [call[0] for call in calls] == ["CheckAccess", "SubmitSensorReading", "RevokeCertificate"]
    assert len({call[1]["nonce"] for call in calls}) == 3


def test_fixed_nonce_invocation():
    calls = []
    client = FabricClient(invoker=lambda name, payload: calls.append((name, payload)) or payload)
    response = client.invoke_with_nonce("CheckAccess", {"device_id": "sensor-1"}, "fixed")
    assert response["nonce"] == "fixed"
    with client.fixed_nonce("context-fixed"):
        client.check_access("sensor-1", "North")
    assert calls[-1][1]["nonce"] == "context-fixed"
