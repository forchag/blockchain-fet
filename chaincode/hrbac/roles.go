package main

// Role identifies an HRBAC actor role.
type Role string

const (
	Admin       Role = "Admin"
	Gateway     Role = "Gateway"
	Farmer      Role = "Farmer"
	Agronomist  Role = "Agronomist"
	Certifier   Role = "Certifier"
	SupplyChain Role = "SupplyChain"
	Sensor      Role = "Sensor"
)

// Permission identifies an action allowed by an effective role.
type Permission string

const (
	ReadOwn        Permission = "ReadOwn"
	ReadZone       Permission = "ReadZone"
	ReadAll        Permission = "ReadAll"
	WriteSensor    Permission = "WriteSensor"
	ControlZone    Permission = "ControlZone"
	ControlAll     Permission = "ControlAll"
	ReadAudit      Permission = "ReadAudit"
	ManageRoles    Permission = "ManageRoles"
	IssueCrossZone Permission = "IssueCrossZone"
	AdminAll       Permission = "AdminAll"
)

var rolePermissions = map[Role][]Permission{
	SupplyChain: {ReadOwn},
	Certifier:   {ReadZone, ReadAudit},
	Agronomist:  {ControlZone, IssueCrossZone},
	Farmer:      {WriteSensor},
	Sensor:      {WriteSensor},
	Gateway:     {ReadZone, ControlZone},
	Admin:       {ReadAll, ControlAll, ManageRoles, AdminAll},
}

var roleAncestors = map[Role][]Role{
	SupplyChain: {SupplyChain},
	Certifier:   {Certifier, SupplyChain},
	Agronomist:  {Agronomist, Certifier, SupplyChain},
	Farmer:      {Farmer, Agronomist, Certifier, SupplyChain},
	Sensor:      {Sensor},
	Gateway:     {Gateway, Sensor},
	Admin:       {Admin, Farmer, Agronomist, Certifier, SupplyChain, Gateway, Sensor},
}

var validRoles = map[Role]struct{}{
	Admin: {}, Gateway: {}, Farmer: {}, Agronomist: {}, Certifier: {}, SupplyChain: {}, Sensor: {},
}

// GetEffectivePermissions returns permissions inherited by r in deterministic order.
func GetEffectivePermissions(r Role) []Permission {
	ancestors, ok := roleAncestors[r]
	if !ok {
		return nil
	}

	seen := make(map[Permission]struct{})
	permissions := make([]Permission, 0)
	for _, role := range ancestors {
		for _, permission := range rolePermissions[role] {
			if _, exists := seen[permission]; exists {
				continue
			}
			seen[permission] = struct{}{}
			permissions = append(permissions, permission)
		}
	}
	return permissions
}

// IsRoleValid reports whether r is one of the supported HRBAC roles.
func IsRoleValid(r Role) bool {
	_, ok := validRoles[r]
	return ok
}
