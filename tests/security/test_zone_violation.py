from __future__ import annotations

import uuid

from tests.security.conftest import blocked, extract_peer_payload
from tests.security.role_model import Permission, Role


def test_zone_violation_is_denied_100_percent(fabric, attempt_nonce):
    denied = 0
    for index in range(1_000):
        result = fabric.invoke("CheckAccess", "farmer-1", Permission.WRITE_SENSOR.value, "South", "", role=Role.FARMER)
        if blocked(result):
            denied += 1
    assert denied == 1_000


def test_cross_zone_token_allows_only_authorized_target_zone(fabric, expiry_iso):
    token_result = fabric.invoke("IssueCrossZoneToken", "farmer-1", "South", expiry_iso, role=Role.AGRONOMIST, nonce=f"czt-{uuid.uuid4()}")
    assert token_result.ok, token_result.combined_output
    token = extract_peer_payload(token_result)

    south = fabric.invoke("CheckAccess", "farmer-1", Permission.CONTROL_ZONE.value, "South", token, role=Role.FARMER)
    assert south.ok and not blocked(south), south.combined_output

    east = fabric.invoke("CheckAccess", "farmer-1", Permission.CONTROL_ZONE.value, "East", token, role=Role.FARMER)
    assert blocked(east), east.combined_output


def test_revoked_cross_zone_token_is_denied(fabric, expiry_iso):
    token_result = fabric.invoke("IssueCrossZoneToken", "farmer-1", "South", expiry_iso, role=Role.AGRONOMIST, nonce=f"czt-revoke-{uuid.uuid4()}")
    assert token_result.ok, token_result.combined_output
    token = extract_peer_payload(token_result)
    revoke = fabric.invoke("RevokeCrossZoneToken", token, role=Role.AGRONOMIST, nonce=f"czt-revoke-2-{uuid.uuid4()}")
    assert revoke.ok, revoke.combined_output
    check = fabric.invoke("CheckAccess", "farmer-1", Permission.CONTROL_ZONE.value, "South", token, role=Role.FARMER)
    assert blocked(check), check.combined_output
