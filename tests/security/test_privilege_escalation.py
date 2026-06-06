from __future__ import annotations

import pytest

from tests.security.conftest import blocked
from tests.security.role_model import Permission, Role, denied_permission_matrix, privilege_escalation_cases


@pytest.mark.parametrize("role,permission", denied_permission_matrix(), ids=lambda item: getattr(item, "value", str(item)))
def test_privilege_escalation_permission_matrix_denies_unowned_permissions(fabric, role: Role, permission: Permission):
    result = fabric.invoke("CheckAccess", f"{role.value.lower()}-1", permission.value, "North", "", role=role)
    assert blocked(result), f"{role.value} unexpectedly received {permission.value}: {result.combined_output}"


@pytest.mark.parametrize("case", privilege_escalation_cases("2099-01-01T00:00:00Z"), ids=lambda case: f"{case.actor_role.value}-{case.transaction}")
def test_privilege_escalation_state_changes_are_rejected(fabric, attempt_nonce, case):
    result = fabric.invoke(case.transaction, *case.args, role=case.actor_role, nonce=attempt_nonce(f"priv-{case.transaction}"))
    assert blocked(result), f"{case.reason} was not blocked: {result.combined_output}"
