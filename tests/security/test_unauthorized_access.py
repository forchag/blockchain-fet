from __future__ import annotations

import pytest

from tests.security.conftest import blocked
from tests.security.role_model import Permission, Role

ATTEMPTS_PER_SCENARIO = 1_000

UNAUTHORIZED_SCENARIOS = [
    pytest.param(Role.SENSOR, "AssignRole", ("intruder-admin", Role.ADMIN.value, "North"), "sensor cannot assign admin", id="sensor_assign_admin"),
    pytest.param(Role.FARMER, "RevokeRole", ("sensor-1",), "farmer cannot revoke roles", id="farmer_revoke_role"),
    pytest.param(Role.SUPPLY_CHAIN, "GetAuditLog", (), "supply-chain cannot read audit", id="supply_chain_audit"),
    pytest.param(Role.CERTIFIER, "PruneNonces", ("1",), "certifier cannot prune nonces", id="certifier_prune_nonces"),
    pytest.param(Role.SENSOR, "IssueCrossZoneToken", ("sensor-1", "South"), "sensor cannot issue CZT", id="sensor_issue_czt"),
    pytest.param(Role.SUPPLY_CHAIN, "RevokeCrossZoneToken", ("missing-token",), "supply-chain cannot revoke CZT", id="supply_chain_revoke_czt"),
    pytest.param(Role.SENSOR, "CheckAccess", ("sensor-1", Permission.ADMIN_ALL.value, "North", ""), "sensor lacks AdminAll", id="sensor_admin_all"),
    pytest.param(Role.GATEWAY, "CheckAccess", ("gateway-1", Permission.MANAGE_ROLES.value, "North", ""), "gateway lacks ManageRoles", id="gateway_manage_roles"),
]


@pytest.mark.parametrize("role,function,args,reason", UNAUTHORIZED_SCENARIOS)
def test_unauthorized_access_scenarios_block_100_percent(fabric, expiry_iso, attempt_nonce, role, function, args, reason):
    blocked_count = 0
    for index in range(ATTEMPTS_PER_SCENARIO):
        expanded_args = tuple(expiry_iso if arg == "<expiry>" else arg for arg in args)
        if function in {"AssignRole", "IssueCrossZoneToken"}:
            expanded_args = (*expanded_args, expiry_iso) if function == "IssueCrossZoneToken" and len(expanded_args) == 2 else expanded_args
        result = fabric.invoke(function, *expanded_args, role=role, nonce=attempt_nonce(f"unauth-{function}-{index}") if function not in {"CheckAccess", "GetAuditLog"} else None)
        if blocked(result):
            blocked_count += 1
    assert blocked_count == ATTEMPTS_PER_SCENARIO, f"{reason}: blocked {blocked_count}/{ATTEMPTS_PER_SCENARIO} attempts"
