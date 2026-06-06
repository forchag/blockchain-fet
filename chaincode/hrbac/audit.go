package main

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// AuditEntry records a deterministic authorization or administration event.
type AuditEntry struct {
	TxID      string `json:"txId"`
	ActorID   string `json:"actorId"`
	Action    string `json:"action"`
	Resource  string `json:"resource"`
	Decision  string `json:"decision"`
	Reason    string `json:"reason,omitempty"`
	Timestamp int64  `json:"timestamp"`
}

func auditKey(txID string) string {
	return auditKeyPrefix + txID
}

func auditKeyWithSequence(txID string, sequence int) string {
	if sequence == 0 {
		return auditKey(txID)
	}
	return fmt.Sprintf("%s%s:%d", auditKeyPrefix, txID, sequence)
}

func writeAuditEntry(ctx contractapi.TransactionContextInterface, entry AuditEntry) (string, error) {
	stub := ctx.GetStub()
	txTimestamp, err := stub.GetTxTimestamp()
	if err != nil {
		return "", fmt.Errorf("failed to read transaction timestamp: %w", err)
	}

	entry.TxID = stub.GetTxID()
	entry.Timestamp = time.Unix(txTimestamp.Seconds, int64(txTimestamp.Nanos)).UTC().Unix()

	payload, err := json.Marshal(entry)
	if err != nil {
		return "", fmt.Errorf("failed to marshal audit entry: %w", err)
	}

	keys, err := getStringIndex(ctx, auditIndexKey)
	if err != nil {
		return "", err
	}

	key := auditKeyWithSequence(entry.TxID, 0)
	for sequence := 0; ; sequence++ {
		key = auditKeyWithSequence(entry.TxID, sequence)
		existing, err := stub.GetState(key)
		if err != nil {
			return "", fmt.Errorf("failed to check audit entry key: %w", err)
		}
		if existing == nil {
			break
		}
	}
	if err := stub.PutState(key, payload); err != nil {
		return "", fmt.Errorf("failed to write audit entry: %w", err)
	}
	keys = append(keys, key)
	if err := putStringIndex(ctx, auditIndexKey, keys); err != nil {
		return "", err
	}
	return key, nil
}
