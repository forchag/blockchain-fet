package shim

type Timestamp struct {
	Seconds int64
	Nanos   int32
}

type ChaincodeStubInterface interface {
	GetState(string) ([]byte, error)
	PutState(string, []byte) error
	GetTxTimestamp() (*Timestamp, error)
	GetTxID() string
}
