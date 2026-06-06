package main

import (
	"fmt"
	"strings"
)

// CrossZoneToken authorizes temporary access from a source zone to target zones.
type CrossZoneToken struct {
	TokenID     string   `json:"tokenId"`
	SubjectID   string   `json:"subjectId"`
	SourceZone  string   `json:"sourceZone"`
	TargetZones []string `json:"targetZones"`
	IssuedBy    string   `json:"issuedBy"`
	IssuedAt    int64    `json:"issuedAt"`
	ExpiresAt   int64    `json:"expiresAt"`
	Nonce       string   `json:"nonce"`
}

func cztKey(tokenID string) string {
	return cztKeyPrefix + tokenID
}

func parseZones(values ...string) map[string]struct{} {
	zones := make(map[string]struct{})
	for _, value := range values {
		for _, part := range strings.Split(value, ",") {
			zone := strings.TrimSpace(part)
			if zone == "" {
				continue
			}
			zones[zone] = struct{}{}
		}
	}
	return zones
}

func validateZoneAccess(assignment RoleAssignment, requestedZone string) error {
	requestedZone = strings.TrimSpace(requestedZone)
	if requestedZone == "" {
		return fmt.Errorf("zone is required")
	}

	zones := parseZones(assignment.Zones...)
	if _, ok := zones["*"]; ok {
		return nil
	}
	if _, ok := zones[requestedZone]; ok {
		return nil
	}
	return fmt.Errorf("zone access denied for %q", requestedZone)
}

var validZones = map[string]struct{}{
	"North": {},
	"South": {},
	"East":  {},
	"West":  {},
}

// IsZoneValid reports whether zone is one of the four supported HRBAC zones.
func IsZoneValid(zone string) bool {
	_, ok := validZones[strings.TrimSpace(zone)]
	return ok
}
