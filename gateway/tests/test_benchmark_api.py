from enrollment_server import create_app


def _client(monkeypatch):
    monkeypatch.setenv("GATEWAY_ZONE", "North")
    return create_app().test_client()


def test_paper_benchmark_endpoint_returns_full_dataset(monkeypatch):
    response = _client(monkeypatch).get("/api/benchmarks/paper")

    assert response.status_code == 200
    body = response.get_json()
    assert "throughput" in body
    assert "security" in body


def test_paper_benchmark_throughput_category(monkeypatch):
    response = _client(monkeypatch).get("/api/benchmarks/paper/throughput")

    assert response.status_code == 200
    assert response.get_json()["hrbac_tps"] == 63


def test_paper_benchmark_security_category(monkeypatch):
    response = _client(monkeypatch).get("/api/benchmarks/paper/security")

    assert response.status_code == 200
    assert response.get_json()["block_rate_percent"] == 100


def test_paper_benchmark_unknown_category(monkeypatch):
    response = _client(monkeypatch).get("/api/benchmarks/paper/unknown")

    assert response.status_code == 404
    assert response.get_json() == {"error": "unknown benchmark category"}
