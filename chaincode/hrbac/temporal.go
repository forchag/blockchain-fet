package main

import (
	"fmt"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// RoleAssignment grants a role to a subject, optionally scoped to zones and time.
type RoleAssignment struct {
	SubjectID string   `json:"subjectId"`
	Role      Role     `json:"role"`
	Zones     []string `json:"zones,omitempty"`
	IssuedBy  string   `json:"issuedBy"`
	IssuedAt  int64    `json:"issuedAt"`
	ExpiresAt int64    `json:"expiresAt,omitempty"`
}

func roleKey(subjectID string) string {
	return roleKeyPrefix + subjectID
}

func checkRoleExpiration(ctx contractapi.TransactionContextInterface, assignment RoleAssignment) error {
	if assignment.ExpiresAt == 0 {
		return nil
	}
	txTimestamp, err := ctx.GetStub().GetTxTimestamp()
	if err != nil {
		return fmt.Errorf("failed to read transaction timestamp: %w", err)
	}
	now := time.Unix(txTimestamp.Seconds, int64(txTimestamp.Nanos)).UTC().Unix()
	if now > assignment.ExpiresAt {
		return fmt.Errorf("role assignment expired at %d", assignment.ExpiresAt)
	}
	return nil
}
