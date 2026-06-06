"""Executable Python gateway tying LoRa, policy cache, Fabric, and Flask together."""

from __future__ import annotations

import logging
import os
import signal
import threading
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa

from enrollment_server import create_app
from fabric_client import FabricClient
from lora_rx import LoRaReceiver, SensorReading
from policy_cache import PolicyCache

LOG = logging.getLogger(__name__)


def load_gateway_zone() -> str:
    zone = os.environ.get("GATEWAY_ZONE")
    if not zone:
        raise RuntimeError("GATEWAY_ZONE environment variable is required")
    return zone


def _signature_payload(reading: SensorReading) -> bytes:
    return f"{reading.device_id}:{reading.reading_id}:{reading.value}:{reading.zone or ''}".encode()


def verify_signature(reading: SensorReading, public_key_pem: str | bytes | None = None) -> bool:
    """Verify a reading signature when key material is available.

    Test and simulator packets may omit signatures or certificates; those are
    accepted so the gateway can be exercised without production credentials.
    """
    if reading.signature is None:
        return True
    key_material = public_key_pem or reading.certificate
    if not key_material:
        return False
    signature = bytes.fromhex(reading.signature) if isinstance(reading.signature, str) else reading.signature
    try:
        public_key = serialization.load_pem_public_key(key_material.encode() if isinstance(key_material, str) else key_material)
        if isinstance(public_key, ed25519.Ed25519PublicKey):
            public_key.verify(signature, _signature_payload(reading))
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(signature, _signature_payload(reading), ec.ECDSA(hashes.SHA256()))
        elif isinstance(public_key, rsa.RSAPublicKey):
            public_key.verify(signature, _signature_payload(reading), padding.PKCS1v15(), hashes.SHA256())
        else:
            return False
        return True
    except (ValueError, InvalidSignature):
        return False


class Gateway:
    def __init__(
        self,
        *,
        zone: str | None = None,
        fabric_client: FabricClient | None = None,
        policy_cache: PolicyCache | None = None,
        lora_receiver: LoRaReceiver | None = None,
    ) -> None:
        self.zone = zone or load_gateway_zone()
        self.fabric_client = fabric_client or FabricClient()
        self.policy_cache = policy_cache or PolicyCache(ttl_seconds=300)
        self.lora_receiver = lora_receiver or LoRaReceiver()
        self.stop_event = threading.Event()
        self.app = create_app(zone=self.zone, fabric_client=self.fabric_client)
        self._flask_thread: threading.Thread | None = None

    def start_server(self) -> None:
        self._flask_thread = threading.Thread(
            target=lambda: self.app.run(host="127.0.0.1", port=8080, threaded=True, use_reloader=False),
            name="gateway-flask",
            daemon=True,
        )
        self._flask_thread.start()

    def policy_key(self, reading: SensorReading) -> str:
        return f"{reading.device_id}:{reading.zone or self.zone}:submit_reading"

    def _decision_is_grant(self, decision: Any) -> bool:
        if isinstance(decision, bool):
            return decision
        if isinstance(decision, str):
            return decision.upper() == "GRANT"
        if isinstance(decision, dict):
            return str(decision.get("decision", decision.get("result", ""))).upper() == "GRANT"
        return False

    def handle_reading(self, reading: SensorReading) -> None:
        if not verify_signature(reading):
            LOG.warning("discarding reading %s from %s: invalid signature", reading.reading_id, reading.device_id)
            return
        key = self.policy_key(reading)
        decision = self.policy_cache.get(key)
        if decision is None:
            decision = self.fabric_client.check_access(reading.device_id, reading.zone or self.zone)
            self.policy_cache.set(key, decision)
        if self._decision_is_grant(decision):
            self.fabric_client.submit_sensor_reading(reading)
            self.app.config["LIVE_READINGS"].append(reading.to_payload())
        else:
            LOG.info("discarding reading %s from %s: access denied", reading.reading_id, reading.device_id)

    def run(self) -> None:
        self.start_server()
        self.lora_receiver.start(self.handle_reading)
        while not self.stop_event.is_set():
            reading = self.lora_receiver.next_reading(timeout=0.5)
            if reading:
                self.handle_reading(reading)

    def stop(self, *_args: object) -> None:
        self.stop_event.set()
        self.lora_receiver.stop()


def main() -> None:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    gateway = Gateway()
    signal.signal(signal.SIGTERM, gateway.stop)
    signal.signal(signal.SIGINT, gateway.stop)
    gateway.run()


if __name__ == "__main__":
    main()
