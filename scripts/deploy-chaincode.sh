set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${ROOT_DIR}/logs/bootstrap.log"
CHANNEL_NAME="${CHANNEL_NAME:-farmchannel}"
CHAINCODE_NAME="${CHAINCODE_NAME:-hrbac}"
CHAINCODE_LABEL="${CHAINCODE_LABEL:-hrbac_1.0}"
CHAINCODE_VERSION="${CHAINCODE_VERSION:-1.0}"
CHAINCODE_SEQUENCE="${CHAINCODE_SEQUENCE:-1}"
CHAINCODE_PATH="${CHAINCODE_PATH:-${ROOT_DIR}/chaincode/hrbac}"
ORDERER_ADDRESS="${ORDERER_ADDRESS:-localhost:7050}"
ORDERER_TLS_CA="${ORDERER_TLS_CA:-${ROOT_DIR}/network/crypto-config/ordererOrganizations/farm.tn/orderers/orderer0.farm.tn/tls/ca.crt}"
PACKAGE_FILE="${PACKAGE_FILE:-${ROOT_DIR}/network/${CHAINCODE_LABEL}.tar.gz}"
ENDORSEMENT_POLICY="${ENDORSEMENT_POLICY:-OR('FarmMSP.member')}"

mkdir -p "$(dirname "${LOG_FILE}")"
log() { printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "${LOG_FILE}" >&2; }
fatal() { log "ERROR: $*"; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fatal "required command not found: $1"; }

PEER_NAMES=(north south east west)
PEER_PORTS=(7051 8051 9051 10051)

set_peer_env() {
  local zone="$1" port="$2" host="peer0.${zone}.farm.tn"
  export CORE_PEER_LOCALMSPID=FarmMSP
  export CORE_PEER_ADDRESS="localhost:${port}"
  export CORE_PEER_TLS_ENABLED=true
  export CORE_PEER_TLS_ROOTCERT_FILE="${ROOT_DIR}/network/crypto-config/peerOrganizations/farm.tn/peers/${host}/tls/ca.crt"
  export CORE_PEER_MSPCONFIGPATH="${ROOT_DIR}/network/crypto-config/peerOrganizations/farm.tn/users/Admin@farm.tn/msp"
}

package_id() {
  peer lifecycle chaincode queryinstalled | awk -v label="${CHAINCODE_LABEL}" '$0 ~ "Package ID:" && $0 ~ label {gsub(",", "", $3); print $3; exit}'
}

main() {
  need peer
  [[ -d "${CHAINCODE_PATH}" ]] || fatal "chaincode path does not exist: ${CHAINCODE_PATH}"
  [[ -f "${ORDERER_TLS_CA}" ]] || fatal "orderer TLS CA not found: ${ORDERER_TLS_CA}"

  set_peer_env "${PEER_NAMES[0]}" "${PEER_PORTS[0]}"
  if [[ ! -f "${PACKAGE_FILE}" ]]; then
    log "Packaging ${CHAINCODE_NAME} as ${PACKAGE_FILE}"
    peer lifecycle chaincode package "${PACKAGE_FILE}" --path "${CHAINCODE_PATH}" --lang golang --label "${CHAINCODE_LABEL}"
  else
    log "Using existing chaincode package ${PACKAGE_FILE}"
  fi

  for i in "${!PEER_NAMES[@]}"; do
    set_peer_env "${PEER_NAMES[$i]}" "${PEER_PORTS[$i]}"
    if package_id >/dev/null; then
      log "${CHAINCODE_LABEL} already installed on peer0.${PEER_NAMES[$i]}.farm.tn"
    else
      log "Installing ${CHAINCODE_LABEL} on peer0.${PEER_NAMES[$i]}.farm.tn"
      peer lifecycle chaincode install "${PACKAGE_FILE}"
    fi
  done

  set_peer_env "${PEER_NAMES[0]}" "${PEER_PORTS[0]}"
  local cc_package_id
  cc_package_id="$(package_id)"
  [[ -n "${cc_package_id}" ]] || fatal "unable to discover package id for ${CHAINCODE_LABEL}"

  if peer lifecycle chaincode queryapproved --channelID "${CHANNEL_NAME}" --name "${CHAINCODE_NAME}" --sequence "${CHAINCODE_SEQUENCE}" --output json >/dev/null 2>&1; then
    log "${CHAINCODE_NAME} sequence ${CHAINCODE_SEQUENCE} already approved"
  else
    log "Approving ${CHAINCODE_NAME} for FarmMSP"
    peer lifecycle chaincode approveformyorg \
      -o "${ORDERER_ADDRESS}" --ordererTLSHostnameOverride orderer0.farm.tn --tls --cafile "${ORDERER_TLS_CA}" \
      --channelID "${CHANNEL_NAME}" --name "${CHAINCODE_NAME}" --version "${CHAINCODE_VERSION}" \
      --package-id "${cc_package_id}" --sequence "${CHAINCODE_SEQUENCE}" --signature-policy "${ENDORSEMENT_POLICY}"
  fi

  if peer lifecycle chaincode querycommitted --channelID "${CHANNEL_NAME}" --name "${CHAINCODE_NAME}" >/dev/null 2>&1; then
    log "${CHAINCODE_NAME} already committed on ${CHANNEL_NAME}"
  else
    log "Committing ${CHAINCODE_NAME} on ${CHANNEL_NAME}"
    peer lifecycle chaincode commit \
      -o "${ORDERER_ADDRESS}" --ordererTLSHostnameOverride orderer0.farm.tn --tls --cafile "${ORDERER_TLS_CA}" \
      --channelID "${CHANNEL_NAME}" --name "${CHAINCODE_NAME}" --version "${CHAINCODE_VERSION}" \
      --sequence "${CHAINCODE_SEQUENCE}" --signature-policy "${ENDORSEMENT_POLICY}" \
      --peerAddresses localhost:7051 --tlsRootCertFiles "${ROOT_DIR}/network/crypto-config/peerOrganizations/farm.tn/peers/peer0.north.farm.tn/tls/ca.crt" \
      --peerAddresses localhost:8051 --tlsRootCertFiles "${ROOT_DIR}/network/crypto-config/peerOrganizations/farm.tn/peers/peer0.south.farm.tn/tls/ca.crt"
  fi
  peer lifecycle chaincode querycommitted --channelID "${CHANNEL_NAME}" --name "${CHAINCODE_NAME}"
  log "Chaincode deployment complete"
}

main "$@"
