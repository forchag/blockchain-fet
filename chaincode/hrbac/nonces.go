package main

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// Nonce records one consumed unique value for replay protection.
type Nonce struct {
	SubjectID string `json:"subjectId"`
	Value     string `json:"value"`
	TxID      string `json:"txId"`
	Timestamp int64  `json:"timestamp"`
}

func nonceKey(subjectID, nonce string) string {
	return nonceKeyPrefix + subjectID + ":" + nonce
}

func validateNonce(ctx contractapi.TransactionContextInterface, subjectID, nonce string) error {
	if subjectID == "" {
		return fmt.Errorf("subject id is required")
	}
	if nonce == "" {
		return fmt.Errorf("nonce is required")
	}

	stub := ctx.GetStub()
	key := nonceKey(subjectID, nonce)
	existing, err := stub.GetState(key)
	if err != nil {
		return fmt.Errorf("failed to read nonce: %w", err)
	}
	if existing != nil {
		return fmt.Errorf("replay detected for nonce %q", nonce)
	}

	txTimestamp, err := stub.GetTxTimestamp()
	if err != nil {
		return fmt.Errorf("failed to read transaction timestamp: %w", err)
	}

	record := Nonce{
		SubjectID: subjectID,
		Value:     nonce,
		TxID:      stub.GetTxID(),
		Timestamp: time.Unix(txTimestamp.Seconds, int64(txTimestamp.Nanos)).UTC().Unix(),
	}
	payload, err := json.Marshal(record)
	if err != nil {
		return fmt.Errorf("failed to marshal nonce: %w", err)
	}
	if err := stub.PutState(key, payload); err != nil {
		return fmt.Errorf("failed to write nonce: %w", err)
	}
	keys, err := getStringIndex(ctx, nonceIndexKey)
	if err != nil {
		return err
	}
	keys = append(keys, key)
	if err := putStringIndex(ctx, nonceIndexKey, keys); err != nil {
		return err
	}
	return nil
}
