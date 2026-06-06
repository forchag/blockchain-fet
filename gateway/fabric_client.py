"""Small Hyperledger Fabric gateway client wrapper used by the Python gateway."""

from __future__ import annotations

import random
import time
import uuid
from contextlib import contextmanager
from typing import Any, Callable, Iterator


class FabricClient:
    """Invoke HRBAC chaincode transactions with nonce and retry handling.

    The class accepts an optional ``invoker`` callable so tests and deployments can
    plug in either mocks or a real Fabric SDK adapter without changing gateway
    code. The callable receives ``(transaction_name, payload_dict)``.
    """

    def __init__(
        self,
        invoker: Callable[[str, dict[str, Any]], Any] | None = None,
        *,
        initial_backoff: float = 1.0,
        backoff_multiplier: float = 2.0,
        max_backoff: float = 60.0,
        jitter: float = 0.1,
        max_attempts: int = 3,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.invoker = invoker or self._not_configured_invoker
        self.initial_backoff = initial_backoff
        self.backoff_multiplier = backoff_multiplier
        self.max_backoff = max_backoff
        self.jitter = jitter
        self.max_attempts = max_attempts
        self._sleeper = sleeper
        self._fixed_nonce: str | None = None

    @staticmethod
    def _not_configured_invoker(transaction_name: str, payload: dict[str, Any]) -> Any:
        raise RuntimeError("Fabric invoker is not configured")

    def _new_nonce(self) -> str:
        return self._fixed_nonce or str(uuid.uuid4())

    @contextmanager
    def fixed_nonce(self, nonce: str) -> Iterator[None]:
        """Temporarily force a nonce, useful for replay-protection tests."""
        previous = self._fixed_nonce
        self._fixed_nonce = nonce
        try:
            yield
        finally:
            self._fixed_nonce = previous

    def invoke_with_nonce(self, transaction_name: str, payload: dict[str, Any], nonce: str) -> Any:
        """Invoke a transaction with a caller-provided nonce for replay tests."""
        payload_with_nonce = dict(payload)
        payload_with_nonce["nonce"] = nonce
        return self._invoke(transaction_name, payload_with_nonce, add_nonce=False)

    def _invoke(self, transaction_name: str, payload: dict[str, Any], *, add_nonce: bool = True) -> Any:
        request_payload = dict(payload)
        if add_nonce:
            request_payload["nonce"] = self._new_nonce()

        delay = self.initial_backoff
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self.invoker(transaction_name, request_payload)
            except Exception as exc:  # pragma: no cover - exact failures are adapter-specific
                last_error = exc
                if attempt >= self.max_attempts:
                    break
                jitter_delta = random.uniform(-self.jitter, self.jitter) if self.jitter else 0.0
                sleep_for = max(0.0, min(self.max_backoff, delay + jitter_delta))
                self._sleeper(sleep_for)
                delay = min(self.max_backoff, delay * self.backoff_multiplier)
        assert last_error is not None
        raise last_error

    def check_access(self, device_id: str, zone: str, action: str = "submit_reading") -> Any:
        return self._invoke("CheckAccess", {"device_id": device_id, "zone": zone, "action": action})

    def submit_sensor_reading(self, reading: Any) -> Any:
        if hasattr(reading, "to_payload"):
            payload = reading.to_payload()
        elif hasattr(reading, "__dict__"):
            payload = dict(reading.__dict__)
        else:
            payload = dict(reading)
        return self._invoke("SubmitSensorReading", payload)

    def revoke_certificate(self, certificate_id: str, reason: str = "cessationOfOperation") -> Any:
        return self._invoke("RevokeCertificate", {"certificate_id": certificate_id, "reason": reason})
