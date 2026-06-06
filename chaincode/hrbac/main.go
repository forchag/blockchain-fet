package main

import (
	"fmt"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

func main() {
	chaincode, err := contractapi.NewChaincode(&SmartContract{})
	if err != nil {
		panic(fmt.Errorf("failed to create HRBAC chaincode: %w", err))
	}

	if err := chaincode.Start(); err != nil {
		panic(fmt.Errorf("failed to start HRBAC chaincode: %w", err))
	}
}
