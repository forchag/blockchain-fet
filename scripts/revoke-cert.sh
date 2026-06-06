set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${ROOT_DIR}/logs/bootstrap.log"
CA_NAME="${CA_NAME:-ca-farm}"
TLS_CERTFILES="${TLS_CERTFILES:-${ROOT_DIR}/network/organizations/fabric-ca/farm/ca-cert.pem}"
FABRIC_CA_CLIENT_HOME="${FABRIC_CA_CLIENT_HOME:-${ROOT_DIR}/network/crypto-config/peerOrganizations/farm.tn}"
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
  [[ $# -ge 1 ]] || fatal "usage: bash scripts/revoke-cert.sh <enrollmentID> [reason]"
  need fabric-ca-client
  local id="$1" reason="${2:-cessationofoperation}"
  export FABRIC_CA_CLIENT_HOME
  log "Revoking certificate(s) for ${id} with reason ${reason}"
  fabric-ca-client revoke --caname "${CA_NAME}" -e "${id}" -r "${reason}" --gencrl --tls.certfiles "${TLS_CERTFILES}"
  if command -v peer >/dev/null 2>&1; then
    set_admin_peer
    local nonce="revoke-${id}-$(date -u '+%s')"
    peer chaincode invoke -C "${CHANNEL_NAME}" -n "${CHAINCODE_NAME}" \
      -o "${ORDERER_ADDRESS}" --ordererTLSHostnameOverride orderer0.farm.tn --tls --cafile "${ORDERER_TLS_CA}" \
      -c "{\"Args\":[\"RevokeRole\",\"${id}\",\"${nonce}\"]}" >/dev/null || log "Role revocation invoke failed; CA revocation succeeded"
  fi
  "${ROOT_DIR}/scripts/generate-crl.sh"
  log "Revocation workflow complete for ${id}"
}

main "$@"
