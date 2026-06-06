"""HRBAC role and permission model used by live security tests."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    ADMIN = "Admin"
    GATEWAY = "Gateway"
    FARMER = "Farmer"
    AGRONOMIST = "Agronomist"
    CERTIFIER = "Certifier"
    SUPPLY_CHAIN = "SupplyChain"
    SENSOR = "Sensor"


class Permission(StrEnum):
    READ_OWN = "ReadOwn"
    READ_ZONE = "ReadZone"
    READ_ALL = "ReadAll"
    WRITE_SENSOR = "WriteSensor"
    CONTROL_ZONE = "ControlZone"
    CONTROL_ALL = "ControlAll"
    READ_AUDIT = "ReadAudit"
    MANAGE_ROLES = "ManageRoles"
    ISSUE_CROSS_ZONE = "IssueCrossZone"
    ADMIN_ALL = "AdminAll"


DIRECT_PERMISSIONS: dict[Role, tuple[Permission, ...]] = {
    Role.SUPPLY_CHAIN: (Permission.READ_OWN,),
    Role.CERTIFIER: (Permission.READ_ZONE, Permission.READ_AUDIT),
    Role.AGRONOMIST: (Permission.CONTROL_ZONE, Permission.ISSUE_CROSS_ZONE),
    Role.FARMER: (Permission.WRITE_SENSOR,),
    Role.SENSOR: (Permission.WRITE_SENSOR,),
    Role.GATEWAY: (Permission.READ_ZONE, Permission.CONTROL_ZONE),
    Role.ADMIN: (Permission.READ_ALL, Permission.CONTROL_ALL, Permission.MANAGE_ROLES, Permission.ADMIN_ALL),
}

ROLE_ANCESTORS: dict[Role, tuple[Role, ...]] = {
    Role.SUPPLY_CHAIN: (Role.SUPPLY_CHAIN,),
    Role.CERTIFIER: (Role.CERTIFIER, Role.SUPPLY_CHAIN),
    Role.AGRONOMIST: (Role.AGRONOMIST, Role.CERTIFIER, Role.SUPPLY_CHAIN),
    Role.FARMER: (Role.FARMER, Role.AGRONOMIST, Role.CERTIFIER, Role.SUPPLY_CHAIN),
    Role.SENSOR: (Role.SENSOR,),
    Role.GATEWAY: (Role.GATEWAY, Role.SENSOR),
    Role.ADMIN: (Role.ADMIN, Role.FARMER, Role.AGRONOMIST, Role.CERTIFIER, Role.SUPPLY_CHAIN, Role.GATEWAY, Role.SENSOR),
}

ROLE_ZONES: dict[Role, str] = {
    Role.ADMIN: "North,South,East,West",
    Role.GATEWAY: "North",
    Role.FARMER: "North",
    Role.AGRONOMIST: "North",
    Role.CERTIFIER: "North",
    Role.SUPPLY_CHAIN: "North",
    Role.SENSOR: "North",
}

ZONE_SCOPED_PERMISSIONS = {Permission.WRITE_SENSOR, Permission.CONTROL_ZONE, Permission.READ_ZONE}


@dataclass(frozen=True)
class EscalationCase:
    actor_role: Role
    transaction: str
    args: tuple[str, ...]
    reason: str


def effective_permissions(role: Role) -> set[Permission]:
    permissions: list[Permission] = []
    seen: set[Permission] = set()
    for ancestor in ROLE_ANCESTORS[role]:
        for permission in DIRECT_PERMISSIONS[ancestor]:
            if permission not in seen:
                seen.add(permission)
                permissions.append(permission)
    return set(permissions)


def is_allowed(role: Role, permission: Permission) -> bool:
    return permission in effective_permissions(role)


def denied_permission_matrix() -> list[tuple[Role, Permission]]:
    return [
        (role, permission)
        for role in Role
        for permission in Permission
        if permission not in effective_permissions(role)
    ]


def privilege_escalation_cases(expiry_iso: str) -> list[EscalationCase]:
    return [
        EscalationCase(role, "AssignRole", (f"escalate-{role.value.lower()}", Role.ADMIN.value, "North", expiry_iso), "non-admin role assignment")
        for role in Role
        if role is not Role.ADMIN
    ] + [
        EscalationCase(Role.SENSOR, "IssueCrossZoneToken", ("sensor-1", "South", expiry_iso), "sensor token issuance"),
        EscalationCase(Role.SUPPLY_CHAIN, "RevokeCrossZoneToken", ("missing-token",), "supply-chain token revocation"),
        EscalationCase(Role.FARMER, "PruneNonces", ("1",), "farmer nonce pruning"),
        EscalationCase(Role.CERTIFIER, "RevokeRole", ("sensor-1",), "certifier role revocation"),
    ]
