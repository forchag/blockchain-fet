from __future__ import annotations

import uuid

from tests.security.conftest import blocked
from tests.security.role_model import Role


def test_fixed_nonce_replay_is_blocked(fabric):
    nonce = f"fixed-replay-{uuid.uuid4()}"
    first = fabric.invoke("WriteSensorData", "sensor-replay", '{"moisture":42}', "North", role=Role.SENSOR, nonce=nonce)
    assert first.ok, first.combined_output

    replay = fabric.invoke("WriteSensorData", "sensor-replay", '{"moisture":43}', "North", role=Role.SENSOR, nonce=nonce)
    assert blocked(replay), replay.combined_output


def test_replay_block_rate_with_fixed_nonce(fabric):
    nonce = f"fixed-check-{uuid.uuid4()}"
    first = fabric.invoke("AssignRole", "replay-farmer", Role.FARMER.value, "North", "2099-01-01T00:00:00Z", role=Role.ADMIN, nonce=nonce)
    assert first.ok, first.combined_output

    blocked_count = 0
    for _ in range(1_000):
        result = fabric.invoke("AssignRole", "replay-farmer", Role.FARMER.value, "North", "2099-01-01T00:00:00Z", role=Role.ADMIN, nonce=nonce)
        if blocked(result):
            blocked_count += 1
    assert blocked_count == 1_000
