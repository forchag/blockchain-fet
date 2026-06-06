package main

import (
	"crypto/sha256"
	"crypto/x509"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"math/big"
	"strings"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
	_ "github.com/hyperledger/fabric-protos-go/peer"
)

const (
	roleKeyPrefix   = "role:"
	cztKeyPrefix    = "czt:"
	auditKeyPrefix  = "audit:"
	nonceKeyPrefix  = "nonce:"
	sensorKeyPrefix = "sensor:"

	auditIndexKey = "audit:index"
	nonceIndexKey = "nonce:index"
)

// SmartContract is the foundation contract for HRBAC chaincode.
type SmartContract struct {
	contractapi.Contract
}

type creatorProvider interface {
	GetCreator() ([]byte, error)
}

type attributeProvider interface {
	GetAttributeValue(string) (string, bool, error)
}

type deleteStateProvider interface {
	DelState(string) error
}

type callerIdentity struct {
	ID        string
	Role      Role
	Zone      string
	SerialHex string
}

func (s *SmartContract) AssignRole(ctx contractapi.TransactionContextInterface, subjectID string, roleName string, zonesCSV string, expiresAtISO string, nonce string) error {
	caller, err := getCallerIdentity(ctx)
	if err != nil {
		return err
	}
	if err := validateNonce(ctx, caller.ID, nonce); err != nil {
		return err
	}
	if caller.Role != Admin {
		return fmt.Errorf("unauthorized: admin role required to assign roles")
	}
	subjectID = strings.TrimSpace(subjectID)
	if subjectID == "" {
		return fmt.Errorf("subject id is required")
	}
	role := Role(strings.TrimSpace(roleName))
	if !IsRoleValid(role) {
		return fmt.Errorf("invalid role %q", roleName)
	}
	zones, err := normalizeZonesForRole(role, zonesCSV)
	if err != nil {
		return err
	}
	expiresAt, err := parseFutureExpiry(ctx, expiresAtISO, false)
	if err != nil {
		return err
	}
	now, err := txTime(ctx)
	if err != nil {
		return err
	}
	assignment := RoleAssignment{SubjectID: subjectID, Role: role, Zones: zones, IssuedBy: caller.ID, IssuedAt: now.Unix(), ExpiresAt: expiresAt}
	payload, err := json.Marshal(assignment)
	if err != nil {
		return fmt.Errorf("failed to marshal role assignment: %w", err)
	}
	if err := ctx.GetStub().PutState(roleKey(subjectID), payload); err != nil {
		return fmt.Errorf("failed to write role assignment: %w", err)
	}
	_, err = writeAuditEntry(ctx, AuditEntry{ActorID: caller.ID, Action: "AssignRole", Resource: subjectID, Decision: "GRANT", Reason: fmt.Sprintf("assigned %s", role)})
	return err
}

func (s *SmartContract) RevokeRole(ctx contractapi.TransactionContextInterface, subjectID string, nonce string) error {
	caller, err := getCallerIdentity(ctx)
	if err != nil {
		return err
	}
	if err := validateNonce(ctx, caller.ID, nonce); err != nil {
		return err
	}
	if caller.Role != Admin {
		return fmt.Errorf("unauthorized: admin role required to revoke roles")
	}
	subjectID = strings.TrimSpace(subjectID)
	if subjectID == "" {
		return fmt.Errorf("subject id is required")
	}
	if err := deleteState(ctx, roleKey(subjectID)); err != nil {
		return fmt.Errorf("failed to revoke role assignment: %w", err)
	}
	_, err = writeAuditEntry(ctx, AuditEntry{ActorID: caller.ID, Action: "RevokeRole", Resource: subjectID, Decision: "GRANT", Reason: "role revoked"})
	return err
}

func (s *SmartContract) RenewRole(ctx contractapi.TransactionContextInterface, subjectID string, expiresAtISO string, nonce string) error {
	caller, err := getCallerIdentity(ctx)
	if err != nil {
		return err
	}
	if err := validateNonce(ctx, caller.ID, nonce); err != nil {
		return err
	}
	if caller.Role != Admin {
		return fmt.Errorf("unauthorized: admin role required to renew roles")
	}
	assignment, err := getRoleAssignment(ctx, subjectID)
	if err != nil {
		return err
	}
	expiresAt, err := parseFutureExpiry(ctx, expiresAtISO, true)
	if err != nil {
		return err
	}
	assignment.ExpiresAt = expiresAt
	payload, err := json.Marshal(assignment)
	if err != nil {
		return fmt.Errorf("failed to marshal role assignment: %w", err)
	}
	if err := ctx.GetStub().PutState(roleKey(subjectID), payload); err != nil {
		return fmt.Errorf("failed to write role assignment: %w", err)
	}
	_, err = writeAuditEntry(ctx, AuditEntry{ActorID: caller.ID, Action: "RenewRole", Resource: subjectID, Decision: "GRANT", Reason: "role renewed"})
	return err
}

func (s *SmartContract) CheckAccess(ctx contractapi.TransactionContextInterface, userID string, permissionName string, requestedZone string, tokenID string) (bool, error) {
	caller, err := getCallerIdentity(ctx)
	if err != nil {
		return false, err
	}
	userID = strings.TrimSpace(userID)
	permission := Permission(strings.TrimSpace(permissionName))
	resource := strings.TrimSpace(requestedZone)

	deny := func(reason string) (bool, error) {
		_, auditErr := writeAuditEntry(ctx, AuditEntry{ActorID: caller.ID, Action: "CheckAccess", Resource: resource, Decision: "DENY", Reason: reason})
		if auditErr != nil {
			return false, auditErr
		}
		return false, nil
	}

	if caller.SerialHex != "" {
		revoked, err := ctx.GetStub().GetState("crl:" + caller.SerialHex)
		if err != nil {
			return false, fmt.Errorf("failed to read certificate revocation state: %w", err)
		}
		if revoked != nil {
			return deny("certificate revoked")
		}
	}

	assignment, err := getRoleAssignment(ctx, userID)
	if err != nil {
		return deny(err.Error())
	}
	if err := checkRoleExpiration(ctx, assignment); err != nil {
		_ = deleteState(ctx, roleKey(userID))
		return deny("role expired and auto-revoked")
	}
	if !hasPermission(assignment.Role, permission) {
		return deny(fmt.Sprintf("permission %s denied", permission))
	}
	if needsZoneCheck(permission) {
		if err := validateZoneAccess(assignment, requestedZone); err != nil {
			if tokenID == "" {
				return deny(err.Error())
			}
			ok, reason, err := s.validCrossZoneToken(ctx, tokenID, userID, requestedZone)
			if err != nil {
				return false, err
			}
			if !ok {
				return deny(reason)
			}
		}
	}
	_, err = writeAuditEntry(ctx, AuditEntry{ActorID: caller.ID, Action: "CheckAccess", Resource: resource, Decision: "GRANT", Reason: string(permission)})
	if err != nil {
		return false, err
	}
	return true, nil
}

func (s *SmartContract) IssueCrossZoneToken(ctx contractapi.TransactionContextInterface, userID string, targetZonesCSV string, expiresAtISO string, nonce string) (string, error) {
	caller, err := getCallerIdentity(ctx)
	if err != nil {
		return "", err
	}
	if err := validateNonce(ctx, caller.ID, nonce); err != nil {
		return "", err
	}
	if caller.Role != Admin && !hasPermission(caller.Role, IssueCrossZone) {
		return "", fmt.Errorf("unauthorized: IssueCrossZone permission required")
	}
	assignment, err := getRoleAssignment(ctx, userID)
	if err != nil {
		return "", err
	}
	targets, err := normalizeZones(targetZonesCSV, true)
	if err != nil {
		return "", err
	}
	expiresAt, err := parseFutureExpiry(ctx, expiresAtISO, true)
	if err != nil {
		return "", err
	}
	now, err := txTime(ctx)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256([]byte(userID + now.String() + nonce))
	tokenID := hex.EncodeToString(sum[:])
	token := CrossZoneToken{TokenID: tokenID, SubjectID: userID, SourceZone: firstZone(assignment.Zones), TargetZones: targets, IssuedBy: caller.ID, IssuedAt: now.Unix(), ExpiresAt: expiresAt, Nonce: nonce}
	payload, err := json.Marshal(token)
	if err != nil {
		return "", fmt.Errorf("failed to marshal cross-zone token: %w", err)
	}
	if err := ctx.GetStub().PutState(cztKey(tokenID), payload); err != nil {
		return "", fmt.Errorf("failed to write cross-zone token: %w", err)
	}
	_, err = writeAuditEntry(ctx, AuditEntry{ActorID: caller.ID, Action: "IssueCrossZoneToken", Resource: userID, Decision: "GRANT", Reason: tokenID})
	if err != nil {
		return "", err
	}
	return tokenID, nil
}

func (s *SmartContract) RevokeCrossZoneToken(ctx contractapi.TransactionContextInterface, tokenID string, nonce string) error {
	caller, err := getCallerIdentity(ctx)
	if err != nil {
		return err
	}
	if err := validateNonce(ctx, caller.ID, nonce); err != nil {
		return err
	}
	if caller.Role != Admin && !hasPermission(caller.Role, IssueCrossZone) {
		return fmt.Errorf("unauthorized: IssueCrossZone permission required")
	}
	tokenID = strings.TrimSpace(tokenID)
	if tokenID == "" {
		return fmt.Errorf("token id is required")
	}
	if err := deleteState(ctx, cztKey(tokenID)); err != nil {
		return fmt.Errorf("failed to revoke cross-zone token: %w", err)
	}
	_, err = writeAuditEntry(ctx, AuditEntry{ActorID: caller.ID, Action: "RevokeCrossZoneToken", Resource: tokenID, Decision: "GRANT", Reason: "token revoked"})
	return err
}

func (s *SmartContract) GetAuditLog(ctx contractapi.TransactionContextInterface) ([]AuditEntry, error) {
	caller, err := getCallerIdentity(ctx)
	if err != nil {
		return nil, err
	}
	if caller.Role != Admin && !hasPermission(caller.Role, ReadAudit) {
		return nil, fmt.Errorf("unauthorized: ReadAudit permission required")
	}
	keys, err := getStringIndex(ctx, auditIndexKey)
	if err != nil {
		return nil, err
	}
	if len(keys) > 1000 {
		keys = keys[len(keys)-1000:]
	}
	entries := make([]AuditEntry, 0, len(keys))
	for _, key := range keys {
		payload, err := ctx.GetStub().GetState(key)
		if err != nil {
			return nil, fmt.Errorf("failed to read audit entry %s: %w", key, err)
		}
		if payload == nil {
			continue
		}
		var entry AuditEntry
		if err := json.Unmarshal(payload, &entry); err != nil {
			return nil, fmt.Errorf("failed to unmarshal audit entry %s: %w", key, err)
		}
		entries = append(entries, entry)
	}
	return entries, nil
}

func (s *SmartContract) PruneNonces(ctx contractapi.TransactionContextInterface, beforeUnix int64, nonce string) (int, error) {
	caller, err := getCallerIdentity(ctx)
	if err != nil {
		return 0, err
	}
	if err := validateNonce(ctx, caller.ID, nonce); err != nil {
		return 0, err
	}
	if caller.Role != Admin {
		return 0, fmt.Errorf("unauthorized: admin role required to prune nonces")
	}
	keys, err := getStringIndex(ctx, nonceIndexKey)
	if err != nil {
		return 0, err
	}
	kept := make([]string, 0, len(keys))
	pruned := 0
	for _, key := range keys {
		payload, err := ctx.GetStub().GetState(key)
		if err != nil {
			return pruned, fmt.Errorf("failed to read nonce %s: %w", key, err)
		}
		if payload == nil {
			continue
		}
		var record Nonce
		if err := json.Unmarshal(payload, &record); err != nil {
			return pruned, fmt.Errorf("failed to unmarshal nonce %s: %w", key, err)
		}
		if record.Timestamp < beforeUnix && key != nonceKey(caller.ID, nonce) {
			if err := deleteState(ctx, key); err != nil {
				return pruned, fmt.Errorf("failed to delete nonce %s: %w", key, err)
			}
			pruned++
			continue
		}
		kept = append(kept, key)
	}
	if err := putStringIndex(ctx, nonceIndexKey, kept); err != nil {
		return pruned, err
	}
	_, err = writeAuditEntry(ctx, AuditEntry{ActorID: caller.ID, Action: "PruneNonces", Resource: nonceIndexKey, Decision: "GRANT", Reason: fmt.Sprintf("pruned %d", pruned)})
	return pruned, err
}

func (s *SmartContract) WriteSensorData(ctx contractapi.TransactionContextInterface, deviceID string, readingJSON string, zone string, nonce string) error {
	caller, err := getCallerIdentity(ctx)
	if err != nil {
		return err
	}
	if err := validateNonce(ctx, caller.ID, nonce); err != nil {
		return err
	}
	ok, err := s.CheckAccess(ctx, caller.ID, string(WriteSensor), zone, "")
	if err != nil {
		return err
	}
	if !ok {
		return fmt.Errorf("access denied: WriteSensor permission required")
	}
	deviceID = strings.TrimSpace(deviceID)
	if deviceID == "" {
		return fmt.Errorf("device id is required")
	}
	var js json.RawMessage
	if err := json.Unmarshal([]byte(readingJSON), &js); err != nil {
		return fmt.Errorf("sensor reading must be valid JSON: %w", err)
	}
	now, err := txTime(ctx)
	if err != nil {
		return err
	}
	key := fmt.Sprintf("%s%s:%d", sensorKeyPrefix, deviceID, now.UnixNano())
	if err := ctx.GetStub().PutState(key, []byte(readingJSON)); err != nil {
		return fmt.Errorf("failed to write sensor data: %w", err)
	}
	return nil
}

func getCallerIdentity(ctx contractapi.TransactionContextInterface) (callerIdentity, error) {
	stub := ctx.GetStub()
	caller := callerIdentity{}
	if attrs, ok := stub.(attributeProvider); ok {
		if value, found, err := attrs.GetAttributeValue("hf.EnrollmentID"); err != nil {
			return caller, fmt.Errorf("failed to read caller id attribute: %w", err)
		} else if found {
			caller.ID = strings.TrimSpace(value)
		}
		if value, found, err := attrs.GetAttributeValue("role"); err != nil {
			return caller, fmt.Errorf("failed to read caller role attribute: %w", err)
		} else if found {
			caller.Role = Role(strings.TrimSpace(value))
		}
		if value, found, err := attrs.GetAttributeValue("zone"); err != nil {
			return caller, fmt.Errorf("failed to read caller zone attribute: %w", err)
		} else if found {
			caller.Zone = strings.TrimSpace(value)
		}
	}
	if provider, ok := stub.(creatorProvider); ok {
		creator, err := provider.GetCreator()
		if err != nil {
			return caller, fmt.Errorf("failed to read caller certificate: %w", err)
		}
		cert, err := parseCertificate(creator)
		if err != nil {
			return caller, err
		}
		if caller.ID == "" {
			caller.ID = cert.Subject.CommonName
		}
		if caller.Role == "" {
			caller.Role = roleFromCertificate(cert)
		}
		if caller.Zone == "" {
			caller.Zone = zoneFromCertificate(cert)
		}
		caller.SerialHex = serialHex(cert.SerialNumber)
	}
	if caller.ID == "" {
		return caller, fmt.Errorf("caller id is required")
	}
	if caller.Role != "" && !IsRoleValid(caller.Role) {
		return caller, fmt.Errorf("invalid caller role %q", caller.Role)
	}
	return caller, nil
}

func parseCertificate(creator []byte) (*x509.Certificate, error) {
	if start := strings.Index(string(creator), "-----BEGIN CERTIFICATE-----"); start >= 0 {
		creator = creator[start:]
	}
	rest := creator
	for {
		block, remaining := pem.Decode(rest)
		if block == nil {
			break
		}
		if block.Type == "CERTIFICATE" {
			cert, err := x509.ParseCertificate(block.Bytes)
			if err != nil {
				return nil, fmt.Errorf("failed to parse caller certificate: %w", err)
			}
			return cert, nil
		}
		rest = remaining
	}
	cert, err := x509.ParseCertificate(creator)
	if err == nil {
		return cert, nil
	}
	return nil, fmt.Errorf("failed to find X.509 caller certificate")
}

func roleFromCertificate(cert *x509.Certificate) Role {
	attrs := certAttributeMap(cert)
	if role := attrs["role"]; role != "" {
		return Role(role)
	}
	for _, ou := range cert.Subject.OrganizationalUnit {
		if IsRoleValid(Role(ou)) {
			return Role(ou)
		}
	}
	return ""
}

func zoneFromCertificate(cert *x509.Certificate) string {
	attrs := certAttributeMap(cert)
	if zone := attrs["zone"]; zone != "" {
		return zone
	}
	if len(cert.Subject.Locality) > 0 {
		return cert.Subject.Locality[0]
	}
	return ""
}

func certAttributeMap(cert *x509.Certificate) map[string]string {
	attrs := make(map[string]string)
	for _, ext := range cert.Extensions {
		raw := strings.TrimSpace(string(ext.Value))
		if raw == "" {
			continue
		}
		var wrapper struct {
			Attrs map[string]string `json:"attrs"`
		}
		if json.Unmarshal([]byte(raw), &wrapper) == nil {
			for k, v := range wrapper.Attrs {
				attrs[k] = v
			}
		}
		var direct map[string]string
		if json.Unmarshal([]byte(raw), &direct) == nil {
			for k, v := range direct {
				attrs[k] = v
			}
		}
		for _, part := range strings.FieldsFunc(raw, func(r rune) bool { return r == ';' || r == ',' || r == '\n' }) {
			kv := strings.SplitN(part, "=", 2)
			if len(kv) == 2 {
				attrs[strings.TrimSpace(kv[0])] = strings.TrimSpace(kv[1])
			}
		}
	}
	return attrs
}

func serialHex(serial *big.Int) string {
	if serial == nil {
		return ""
	}
	if serial.Sign() == 0 {
		return "0"
	}
	return strings.ToLower(serial.Text(16))
}

func normalizeZonesForRole(role Role, zonesCSV string) ([]string, error) {
	zones, err := normalizeZones(zonesCSV, role == Gateway || role == Sensor)
	if err != nil {
		return nil, err
	}
	if (role == Gateway || role == Sensor) && len(zones) == 0 {
		return nil, fmt.Errorf("zone is required for %s role", role)
	}
	return zones, nil
}

func normalizeZones(zonesCSV string, required bool) ([]string, error) {
	seen := make(map[string]struct{})
	zones := make([]string, 0)
	for zone := range parseZones(zonesCSV) {
		if zone == "*" {
			zones = append(zones, zone)
			continue
		}
		if !IsZoneValid(zone) {
			return nil, fmt.Errorf("invalid zone %q", zone)
		}
		if _, ok := seen[zone]; !ok {
			seen[zone] = struct{}{}
			zones = append(zones, zone)
		}
	}
	if required && len(zones) == 0 {
		return nil, fmt.Errorf("zone is required")
	}
	return zones, nil
}

func parseFutureExpiry(ctx contractapi.TransactionContextInterface, expiresAtISO string, required bool) (int64, error) {
	expiresAtISO = strings.TrimSpace(expiresAtISO)
	if expiresAtISO == "" {
		if required {
			return 0, fmt.Errorf("expiresAtISO is required")
		}
		return 0, nil
	}
	expiresAt, err := time.Parse(time.RFC3339, expiresAtISO)
	if err != nil {
		return 0, fmt.Errorf("expiresAtISO must be RFC3339: %w", err)
	}
	now, err := txTime(ctx)
	if err != nil {
		return 0, err
	}
	if !expiresAt.After(now) {
		return 0, fmt.Errorf("expiry in the past")
	}
	return expiresAt.UTC().Unix(), nil
}

func txTime(ctx contractapi.TransactionContextInterface) (time.Time, error) {
	ts, err := ctx.GetStub().GetTxTimestamp()
	if err != nil {
		return time.Time{}, fmt.Errorf("failed to read transaction timestamp: %w", err)
	}
	return time.Unix(ts.Seconds, int64(ts.Nanos)).UTC(), nil
}

func getRoleAssignment(ctx contractapi.TransactionContextInterface, subjectID string) (RoleAssignment, error) {
	subjectID = strings.TrimSpace(subjectID)
	if subjectID == "" {
		return RoleAssignment{}, fmt.Errorf("subject id is required")
	}
	payload, err := ctx.GetStub().GetState(roleKey(subjectID))
	if err != nil {
		return RoleAssignment{}, fmt.Errorf("failed to read role assignment: %w", err)
	}
	if payload == nil {
		return RoleAssignment{}, fmt.Errorf("role assignment not found for %s", subjectID)
	}
	var assignment RoleAssignment
	if err := json.Unmarshal(payload, &assignment); err != nil {
		return RoleAssignment{}, fmt.Errorf("failed to unmarshal role assignment: %w", err)
	}
	return assignment, nil
}

func hasPermission(role Role, permission Permission) bool {
	if permission == "" {
		return false
	}
	for _, p := range GetEffectivePermissions(role) {
		if p == permission || p == AdminAll {
			return true
		}
	}
	return false
}

func needsZoneCheck(permission Permission) bool {
	return permission == ReadZone || permission == WriteSensor || permission == ControlZone
}

func (s *SmartContract) validCrossZoneToken(ctx contractapi.TransactionContextInterface, tokenID, userID, requestedZone string) (bool, string, error) {
	payload, err := ctx.GetStub().GetState(cztKey(strings.TrimSpace(tokenID)))
	if err != nil {
		return false, "", fmt.Errorf("failed to read cross-zone token: %w", err)
	}
	if payload == nil {
		return false, "cross-zone token not found or revoked", nil
	}
	var token CrossZoneToken
	if err := json.Unmarshal(payload, &token); err != nil {
		return false, "", fmt.Errorf("failed to unmarshal cross-zone token: %w", err)
	}
	if token.SubjectID != userID {
		return false, "cross-zone token subject mismatch", nil
	}
	now, err := txTime(ctx)
	if err != nil {
		return false, "", err
	}
	if token.ExpiresAt <= now.Unix() {
		return false, "cross-zone token expired", nil
	}
	zones := parseZones(token.TargetZones...)
	if _, ok := zones[requestedZone]; !ok {
		return false, "cross-zone token does not cover requested zone", nil
	}
	return true, "", nil
}

func firstZone(zones []string) string {
	if len(zones) == 0 {
		return ""
	}
	return zones[0]
}

func deleteState(ctx contractapi.TransactionContextInterface, key string) error {
	if deleter, ok := ctx.GetStub().(deleteStateProvider); ok {
		return deleter.DelState(key)
	}
	return ctx.GetStub().PutState(key, nil)
}

func getStringIndex(ctx contractapi.TransactionContextInterface, key string) ([]string, error) {
	payload, err := ctx.GetStub().GetState(key)
	if err != nil {
		return nil, fmt.Errorf("failed to read index %s: %w", key, err)
	}
	if payload == nil {
		return nil, nil
	}
	var values []string
	if err := json.Unmarshal(payload, &values); err != nil {
		return nil, fmt.Errorf("failed to unmarshal index %s: %w", key, err)
	}
	return values, nil
}

func putStringIndex(ctx contractapi.TransactionContextInterface, key string, values []string) error {
	payload, err := json.Marshal(values)
	if err != nil {
		return fmt.Errorf("failed to marshal index %s: %w", key, err)
	}
	if err := ctx.GetStub().PutState(key, payload); err != nil {
		return fmt.Errorf("failed to write index %s: %w", key, err)
	}
	return nil
}
