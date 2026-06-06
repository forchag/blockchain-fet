"""Local gateway enrollment and dashboard API server."""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Any

from flask import Flask, jsonify, request

from paper_benchmarks import get_all_benchmarks, get_benchmark_category
from raw_data_api import raw_bp

ENROLL_LIMIT = 10
ENROLL_WINDOW_SECONDS = 3600


def _require_zone(zone: str | None = None) -> str:
    selected = zone or os.environ.get("GATEWAY_ZONE")
    if not selected:
        raise RuntimeError("GATEWAY_ZONE environment variable is required")
    return selected


def create_app(
    *,
    zone: str | None = None,
    fabric_client: Any | None = None,
    gateway_public_key: str | None = None,
    ca_cert: str | None = None,
) -> Flask:
    gateway_zone = _require_zone(zone)
    app = Flask(__name__)
    app.config["GATEWAY_ZONE"] = gateway_zone
    app.config["FABRIC_CLIENT"] = fabric_client
    app.config["GATEWAY_PUBLIC_KEY"] = gateway_public_key or "gateway-public-key-placeholder"
    app.config["CA_CERT"] = ca_cert or "ca-cert-placeholder"
    app.config["LIVE_READINGS"] = []
    app.config["AUDIT"] = []
    app.config["ROLES"] = {}
    app.config["ZONES"] = [gateway_zone]
    app.register_blueprint(raw_bp)
    enroll_attempts: dict[str, deque[float]] = defaultdict(deque)

    def audit(event: str, payload: dict[str, Any]) -> None:
        app.config["AUDIT"].append({"event": event, "payload": payload, "timestamp": time.time()})

    def rate_limited(identity: str) -> bool:
        now = time.time()
        attempts = enroll_attempts[identity]
        while attempts and now - attempts[0] >= ENROLL_WINDOW_SECONDS:
            attempts.popleft()
        if len(attempts) >= ENROLL_LIMIT:
            return True
        attempts.append(now)
        return False

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "zone": gateway_zone})

    @app.post("/enroll")
    def enroll():
        caller = request.remote_addr or "unknown"
        if rate_limited(caller):
            return jsonify({"error": "enrollment rate limit exceeded"}), 429
        payload = request.get_json(silent=True) or {}
        if payload.get("zone") != gateway_zone:
            audit("enroll_rejected_zone", payload)
            return jsonify({"error": "zone does not match gateway zone"}), 403
        sensor_id = payload.get("sensor_id") or payload.get("device_id")
        if not sensor_id:
            return jsonify({"error": "sensor_id is required"}), 400
        sensor_certificate = f"sensor-certificate-for-{sensor_id}"
        audit("enroll_granted", {"sensor_id": sensor_id, "zone": gateway_zone})
        return jsonify(
            {
                "gateway_public_key": app.config["GATEWAY_PUBLIC_KEY"],
                "ca_cert": app.config["CA_CERT"],
                "sensor_certificate": sensor_certificate,
                "sensor_id": sensor_id,
                "zone": gateway_zone,
            }
        )

    @app.get("/api/sensors/live")
    def live_sensors():
        return jsonify({"readings": app.config["LIVE_READINGS"]})

    @app.get("/api/audit")
    def audit_log():
        return jsonify({"events": app.config["AUDIT"]})

    @app.get("/api/benchmarks/paper")
    def paper_benchmarks():
        return jsonify(get_all_benchmarks())

    @app.get("/api/benchmarks/paper/<category>")
    def paper_benchmark_category(category: str):
        category_data = get_benchmark_category(category)
        if category_data is None:
            return jsonify({"error": "unknown benchmark category"}), 404
        return jsonify(category_data)

    @app.get("/api/roles")
    def get_roles():
        return jsonify({"roles": app.config["ROLES"]})

    @app.post("/api/roles")
    def post_role():
        payload = request.get_json(silent=True) or {}
        user_id = payload.get("user_id")
        role = payload.get("role")
        if not user_id or not role:
            return jsonify({"error": "user_id and role are required"}), 400
        app.config["ROLES"][user_id] = {"role": role, "zone": payload.get("zone", gateway_zone)}
        audit("role_set", {"user_id": user_id, "role": role})
        return jsonify({"user_id": user_id, **app.config["ROLES"][user_id]}), 201

    @app.delete("/api/roles/<user_id>")
    def delete_role(user_id: str):
        removed = app.config["ROLES"].pop(user_id, None)
        audit("role_deleted", {"user_id": user_id})
        if removed is None:
            return jsonify({"error": "role not found"}), 404
        return "", 204

    @app.get("/api/zones")
    def zones():
        return jsonify({"zones": app.config["ZONES"]})

    return app


def run_server(app: Flask | None = None) -> None:
    (app or create_app()).run(host="127.0.0.1", port=8080, threaded=True)


if __name__ == "__main__":
    run_server()
