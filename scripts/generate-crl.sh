set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${ROOT_DIR}/logs/bootstrap.log"
CA_NAME="${CA_NAME:-ca-farm}"
TLS_CERTFILES="${TLS_CERTFILES:-${ROOT_DIR}/network/organizations/fabric-ca/farm/ca-cert.pem}"
FABRIC_CA_CLIENT_HOME="${FABRIC_CA_CLIENT_HOME:-${ROOT_DIR}/network/crypto-config/peerOrganizations/farm.tn}"
CRL_PEM="${CRL_PEM:-${ROOT_DIR}/network/crl/farm-ca-crl.pem}"
CHANNEL_NAME="${CHANNEL_NAME:-farmchannel}"
CHAINCODE_NAME="${CHAINCODE_NAME:-hrbac}"
ORDERER_ADDRESS="${ORDERER_ADDRESS:-localhost:7050}"
ORDERER_TLS_CA="${ORDERER_TLS_CA:-${ROOT_DIR}/network/crypto-config/ordererOrganizations/farm.tn/orderers/orderer0.farm.tn/tls/ca.crt}"

mkdir -p "$(dirname "${LOG_FILE}")"
log() { printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "${LOG_FILE}" >&2; }
fatal() { log "ERROR: $*"; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fatal "required command not found: $1"; }

set_admin_peer() {
  export CORE_PEER_LOCALMSPID=FarmMSP CORE_PEER_ADDRESS=localhost:7051 CORE_PEER_TLS_ENABLED=true
  export CORE_PEER_MSPCONFIGPATH="${ROOT_DIR}/network/crypto-config/peerOrganizations/farm.tn/users/Admin@farm.tn/msp"
  export CORE_PEER_TLS_ROOTCERT_FILE="${ROOT_DIR}/network/crypto-config/peerOrganizations/farm.tn/peers/peer0.north.farm.tn/tls/ca.crt"
}

main() {
  need fabric-ca-client; need base64
  export FABRIC_CA_CLIENT_HOME
  mkdir -p "$(dirname "${CRL_PEM}")"
  log "Generating CA CRL"
  fabric-ca-client gencrl --caname "${CA_NAME}" --tls.certfiles "${TLS_CERTFILES}" > "${CRL_PEM}"
  if command -v peer >/dev/null 2>&1; then
    set_admin_peer
    local crl_b64 nonce
    crl_b64="$(base64 < "${CRL_PEM}" | tr -d '\n')"
    nonce="crl-$(date -u '+%s')"
    peer chaincode invoke -C "${CHANNEL_NAME}" -n "${CHAINCODE_NAME}" \
      -o "${ORDERER_ADDRESS}" --ordererTLSHostnameOverride orderer0.farm.tn --tls --cafile "${ORDERER_TLS_CA}" \
      -c "{\"Args\":[\"UpdateCRL\",\"${crl_b64}\",\"${nonce}\"]}" >/dev/null || log "CRL chaincode update skipped/failed; CRL file is available at ${CRL_PEM}"
  fi
  log "CRL written to ${CRL_PEM}"
}

main "$@"
