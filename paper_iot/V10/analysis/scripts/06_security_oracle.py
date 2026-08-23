#!/usr/bin/env python3
"""Phase 9: scripted authorization-boundary corpus vs an independent,
requirements-derived role/operation oracle.

The deployed chaincode (chaincode/hrbac/roles.go, contract.go) exposes
CheckAccess(userID, permissionName, zone, token) against the ten canonical
Permission constants in roles.go; it does not itself carry a mapping from
the trace's seven human-readable `operation` labels (WriteSensor,
ReadSensorData, ReadZone, ControlZone, ReadAudit, ReadProvenance,
ReadEnvironmentalRecord) to those constants, and this repository does not
ship a policy-requirements.json. We therefore build and disclose our own
operation -> permission mapping (OPERATION_PERMISSION below) rather than
assume one; it is a stated, inspectable assumption, not a value taken from
the codebase. Every downstream count in this script depends on it.

The role-permission computation itself (GetEffectivePermissions / hasPermission)
IS taken verbatim from chaincode/hrbac/roles.go and contract.go -- reproduced
in Python line-for-line below, not re-derived by inspection of trace values.
"""
from __future__ import annotations

import pandas as pd

from common import SECURITY_DIR, OUTPUTS_DIR, write_json

# --- verbatim reproduction of chaincode/hrbac/roles.go -----------------------
ROLE_PERMISSIONS_DEPLOYED = {
    "SupplyChain": ["ReadOwn"],
    "Certifier": ["ReadZone", "ReadAudit"],
    "Agronomist": ["ControlZone", "IssueCrossZone"],
    "Farmer": ["WriteSensor"],
    "Sensor": ["WriteSensor"],
    "Gateway": ["ReadZone", "ControlZone"],
    "Admin": ["ReadAll", "ControlAll", "ManageRoles", "AdminAll"],
}
ROLE_ANCESTORS_DEPLOYED = {
    "SupplyChain": ["SupplyChain"],
    "Certifier": ["Certifier", "SupplyChain"],
    "Agronomist": ["Agronomist", "Certifier", "SupplyChain"],
    "Farmer": ["Farmer", "Agronomist", "Certifier", "SupplyChain"],
    "Sensor": ["Sensor"],
    "Gateway": ["Gateway", "Sensor"],
    "Admin": ["Admin", "Farmer", "Agronomist", "Certifier", "SupplyChain", "Gateway", "Sensor"],
}

# --- Table 1 corrections (independently derived from Section 3.2 stakeholder
# requirements, not from any code) applied to build the INTENDED hierarchy ---
ROLE_PERMISSIONS_INTENDED = {
    "SupplyChain": ["ReadOwn"],
    "Certifier": ["ReadAudit"],  # ReadZone removed per Table 1
    "Agronomist": ["IssueCrossZone", "ReadZone"],  # ControlZone removed, ReadZone added per Table 1
    "Farmer": ["WriteSensor", "ControlZone", "ReadZone"],  # ControlZone direct grant added per Table 1
    "Sensor": ["WriteSensor"],
    "Gateway": ["ReadZone", "ControlZone"],
    "Admin": ["ReadAll", "ControlAll", "ManageRoles", "AdminAll"],
}
ROLE_ANCESTORS_INTENDED = {
    "SupplyChain": ["SupplyChain"],
    "Certifier": ["Certifier", "SupplyChain"],
    "Agronomist": ["Agronomist", "Certifier", "SupplyChain"],
    "Farmer": ["Farmer", "Agronomist", "Certifier", "SupplyChain"],
    "Sensor": ["Sensor"],
    "Gateway": ["Gateway", "Sensor"],
    "Admin": ["Admin", "Farmer", "Agronomist", "Certifier", "SupplyChain", "Gateway", "Sensor"],
}


def effective_permissions(role: str, perms: dict, ancestors: dict) -> set[str]:
    if role not in ancestors:
        return set()
    out = set()
    for anc in ancestors[role]:
        out.update(perms.get(anc, []))
    return out


def has_permission(role: str, permission: str, perms: dict, ancestors: dict) -> bool:
    eff = effective_permissions(role, perms, ancestors)
    return permission in eff or "AdminAll" in eff


# --- disclosed operation -> canonical-permission mapping (V10 assumption) ---
OPERATION_PERMISSION = {
    "WriteSensor": "WriteSensor",
    "ReadSensorData": "ReadZone",
    "ReadZone": "ReadZone",
    "ControlZone": "ControlZone",
    "ReadAudit": "ReadAudit",
    "ReadProvenance": "ReadOwn",
    "ReadEnvironmentalRecord": "ReadZone",
}

ROLE_OP_DENY_REASONS = {"ROLE_INSUFFICIENT", "OP_NOT_PERMITTED"}


def main() -> None:
    sec = pd.read_csv(SECURITY_DIR / "authorization_boundary_attempts.csv", parse_dates=["timestamp"])

    sec["mapped_permission"] = sec["operation"].map(OPERATION_PERMISSION)
    unmapped = sec[sec["mapped_permission"].isna()]

    sec["deployed_should_permit"] = sec.apply(
        lambda r: has_permission(r["attacker_role"], r["mapped_permission"], ROLE_PERMISSIONS_DEPLOYED, ROLE_ANCESTORS_DEPLOYED)
        if pd.notna(r["mapped_permission"]) else None, axis=1)
    sec["intended_should_permit"] = sec.apply(
        lambda r: has_permission(r["attacker_role"], r["mapped_permission"], ROLE_PERMISSIONS_INTENDED, ROLE_ANCESTORS_INTENDED)
        if pd.notna(r["mapped_permission"]) else None, axis=1)

    role_op_scope = sec[sec["deny_reason"].isin(ROLE_OP_DENY_REASONS)]
    confirmed = role_op_scope[role_op_scope["deployed_should_permit"] == False]
    discrepant = role_op_scope[role_op_scope["deployed_should_permit"] == True]

    discrepant_pairs = sorted(set(zip(discrepant["attacker_role"], discrepant["operation"])))

    result = {
        "total_attempts": int(len(sec)),
        "scenario_counts": sec["scenario"].value_counts().to_dict(),
        "deny_reason_counts": sec["deny_reason"].value_counts().to_dict(),
        "n_deny_reason_types": int(sec["deny_reason"].nunique()),
        "all_blocked": bool((sec["blocked"] == True).all()),
        "all_denied": bool((sec["decision"] == "denied").all()),
        "role_operation_scoped_attempts": int(len(role_op_scope)),
        "role_operation_scoped_pct": float(len(role_op_scope) / len(sec) * 100),
        "confirmed_by_deployed_oracle": int(len(confirmed)),
        "confirmed_pct_of_scoped": float(len(confirmed) / len(role_op_scope) * 100),
        "discrepant_vs_deployed_oracle": int(len(discrepant)),
        "discrepant_pct_of_scoped": float(len(discrepant) / len(role_op_scope) * 100),
        "discrepant_role_operation_pairs": [f"{r}|{o}" for r, o in discrepant_pairs],
        "unmapped_operation_rows": int(len(unmapped)),
        "operation_permission_mapping": OPERATION_PERMISSION,
        "note_intended_vs_deployed": (
            "discrepant_role_operation_pairs are evaluated against the DEPLOYED hierarchy only, "
            "matching V9.2's Section 6.6 method; a parallel check against the INTENDED hierarchy is "
            "in 'discrepant_vs_intended_oracle' below for comparison."
        ),
    }

    confirmed_intended = role_op_scope[role_op_scope["intended_should_permit"] == False]
    discrepant_intended = role_op_scope[role_op_scope["intended_should_permit"] == True]
    result["confirmed_by_intended_oracle"] = int(len(confirmed_intended))
    result["discrepant_vs_intended_oracle"] = int(len(discrepant_intended))

    write_json(OUTPUTS_DIR / "06_security_oracle.json", result)


if __name__ == "__main__":
    main()
