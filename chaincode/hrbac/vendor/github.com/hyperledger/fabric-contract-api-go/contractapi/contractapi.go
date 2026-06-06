package contractapi

import "github.com/hyperledger/fabric-chaincode-go/shim"

type Contract struct{}

type TransactionContextInterface interface {
	GetStub() shim.ChaincodeStubInterface
}

type Chaincode struct{}

func NewChaincode(_ ...interface{}) (*Chaincode, error) { return &Chaincode{}, nil }
func (c *Chaincode) Start() error                       { return nil }
