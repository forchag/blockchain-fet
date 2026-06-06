set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${ROOT_DIR}/logs/bootstrap.log"
CHANNEL_NAME="${CHANNEL_NAME:-farmchannel}"
CA_NAME="${CA_NAME:-ca-farm}"
CA_URL="${CA_URL:-https://admin:adminpw@localhost:7054}"
TLS_CERTFILES="${TLS_CERTFILES:-${ROOT_DIR}/network/organizations/fabric-ca/farm/ca-cert.pem}"
FABRIC_CA_CLIENT_HOME="${FABRIC_CA_CLIENT_HOME:-${ROOT_DIR}/network/crypto-config/peerOrganizations/farm.tn}"
ORDERER_CA="${ROOT_DIR}/network/crypto-config/ordererOrganizations/farm.tn/orderers/orderer0.farm.tn/tls/ca.crt"
ORDERER_ADDRESS="localhost:7050"

mkdir -p "$(dirname "${LOG_FILE}")"
log() { printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "${LOG_FILE}" >&2; }
fatal() { log "ERROR: $*"; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fatal "required command not found: $1"; }

docker_compose() {
  if docker compose version >/dev/null 2>&1; then docker compose "$@"; elif command -v docker-compose >/dev/null 2>&1; then docker-compose "$@"; else fatal "docker compose or docker-compose is required"; fi
}

wait_for_file() {
  local file="$1" timeout="${2:-60}" elapsed=0
  until [[ -f "${file}" ]]; do
    (( elapsed >= timeout )) && fatal "timed out waiting for ${file}"
    sleep 1; elapsed=$((elapsed + 1))
  done
}

register_identity() {
  local name="$1" secret="$2" type="$3" attrs="${4:-}"
  export FABRIC_CA_CLIENT_HOME
  if fabric-ca-client identity list --caname "${CA_NAME}" --tls.certfiles "${TLS_CERTFILES}" 2>/dev/null | grep -q "Name: ${name},"; then
    log "Identity ${name} already registered"
    return 0
  fi
  local args=(register --caname "${CA_NAME}" --id.name "${name}" --id.secret "${secret}" --id.type "${type}" --tls.certfiles "${TLS_CERTFILES}")
  [[ -n "${attrs}" ]] && args+=(--id.attrs "${attrs}")
  fabric-ca-client "${args[@]}"
}

enroll_msp() {
  local name="$1" secret="$2" msp_dir="$3" csr_hosts="$4" type_label="$5"
  if [[ -f "${msp_dir}/signcerts/cert.pem" ]]; then
    log "${name} MSP already enrolled"
    return 0
  fi
  fabric-ca-client enroll -u "https://${name}:${secret}@localhost:7054" --caname "${CA_NAME}" -M "${msp_dir}" \
    --csr.hosts "${csr_hosts}" --csr.names "O=FarmMSP,OU=${type_label}" --tls.certfiles "${TLS_CERTFILES}"
}

enroll_tls() {
  local name="$1" secret="$2" tls_dir="$3" hosts="$4"
  if [[ -f "${tls_dir}/server.crt" ]]; then
    log "${name} TLS material already enrolled"
    return 0
  fi
  mkdir -p "${tls_dir}"
  fabric-ca-client enroll -u "https://${name}:${secret}@localhost:7054" --caname "${CA_NAME}" -M "${tls_dir}" \
    --enrollment.profile tls --csr.hosts "${hosts}" --tls.certfiles "${TLS_CERTFILES}"
  cp "${tls_dir}/signcerts/"* "${tls_dir}/server.crt"
  cp "${tls_dir}/keystore/"* "${tls_dir}/server.key"
  cp "${tls_dir}/tlscacerts/"* "${tls_dir}/ca.crt"
}

prepare_org_msps() {
  local peer_org="${ROOT_DIR}/network/crypto-config/peerOrganizations/farm.tn"
  local orderer_org="${ROOT_DIR}/network/crypto-config/ordererOrganizations/farm.tn"
  mkdir -p "${peer_org}/msp" "${orderer_org}/msp"
  cp "${peer_org}/users/Admin@farm.tn/msp/config.yaml" "${peer_org}/msp/config.yaml"
  cp "${peer_org}/users/Admin@farm.tn/msp/config.yaml" "${orderer_org}/msp/config.yaml"
}

start_ca() {
  need docker
  log "Starting Fabric CA"
  docker_compose -f "${ROOT_DIR}/network/docker-compose-ca.yaml" up -d
  wait_for_file "${TLS_CERTFILES}" 90
}

register_and_enroll_nodes() {
  need fabric-ca-client
  export FABRIC_CA_CLIENT_HOME
  local peer_org="${ROOT_DIR}/network/crypto-config/peerOrganizations/farm.tn"
  local orderer_org="${ROOT_DIR}/network/crypto-config/ordererOrganizations/farm.tn"
  mkdir -p "${peer_org}" "${orderer_org}"
  "${ROOT_DIR}/scripts/enroll-admin.sh"
  for zone in north south east west; do
    local peer="peer0.${zone}.farm.tn"
    register_identity "${peer}" "${peer}pw" peer "role=Peer:ecert,zone=${zone}:ecert"
    enroll_msp "${peer}" "${peer}pw" "${peer_org}/peers/${peer}/msp" "${peer},localhost" Peer
    enroll_tls "${peer}" "${peer}pw" "${peer_org}/peers/${peer}/tls" "${peer},localhost"
  done
  for idx in 0 1 2; do
    local orderer="orderer${idx}.farm.tn"
    register_identity "${orderer}" "${orderer}pw" orderer "role=Orderer:ecert"
    enroll_msp "${orderer}" "${orderer}pw" "${orderer_org}/orderers/${orderer}/msp" "${orderer},localhost" Orderer
    enroll_tls "${orderer}" "${orderer}pw" "${orderer_org}/orderers/${orderer}/tls" "${orderer},localhost"
  done
  prepare_org_msps
}

generate_genesis() {
  need configtxgen
  mkdir -p "${ROOT_DIR}/network/system-genesis-block" "${ROOT_DIR}/network/channel-artifacts"
  export FABRIC_CFG_PATH="${ROOT_DIR}/network"
  if [[ ! -f "${ROOT_DIR}/network/system-genesis-block/genesis.block" ]]; then
    log "Generating Raft genesis block"
    configtxgen -profile FarmGenesis -channelID system-channel -outputBlock "${ROOT_DIR}/network/system-genesis-block/genesis.block"
  fi
  if [[ ! -f "${ROOT_DIR}/network/channel-artifacts/${CHANNEL_NAME}.tx" ]]; then
    log "Generating ${CHANNEL_NAME} channel transaction"
    configtxgen -profile FarmChannel -outputCreateChannelTx "${ROOT_DIR}/network/channel-artifacts/${CHANNEL_NAME}.tx" -channelID "${CHANNEL_NAME}"
  fi
}

start_orderers() { log "Starting orderers"; docker_compose -f "${ROOT_DIR}/network/docker-compose-orderer.yaml" up -d; }
start_peers() { log "Starting peers and CouchDB"; docker_compose -f "${ROOT_DIR}/network/docker-compose-peers.yaml" up -d; }

set_peer_env() {
  local zone="$1" port="$2" host="peer0.${zone}.farm.tn"
  export CORE_PEER_LOCALMSPID=FarmMSP CORE_PEER_ADDRESS="localhost:${port}" CORE_PEER_TLS_ENABLED=true
  export CORE_PEER_MSPCONFIGPATH="${ROOT_DIR}/network/crypto-config/peerOrganizations/farm.tn/users/Admin@farm.tn/msp"
  export CORE_PEER_TLS_ROOTCERT_FILE="${ROOT_DIR}/network/crypto-config/peerOrganizations/farm.tn/peers/${host}/tls/ca.crt"
}

create_and_join_channel() {
  need peer
  set_peer_env north 7051
  if [[ ! -f "${ROOT_DIR}/network/channel-artifacts/${CHANNEL_NAME}.block" ]]; then
    log "Creating ${CHANNEL_NAME}"
    peer channel create -o "${ORDERER_ADDRESS}" -c "${CHANNEL_NAME}" -f "${ROOT_DIR}/network/channel-artifacts/${CHANNEL_NAME}.tx" \
      --outputBlock "${ROOT_DIR}/network/channel-artifacts/${CHANNEL_NAME}.block" --tls --cafile "${ORDERER_CA}" --ordererTLSHostnameOverride orderer0.farm.tn
  else
    log "Channel block already exists for ${CHANNEL_NAME}"
  fi
  local zones=(north south east west) ports=(7051 8051 9051 10051)
  for i in "${!zones[@]}"; do
    set_peer_env "${zones[$i]}" "${ports[$i]}"
    if peer channel getinfo -c "${CHANNEL_NAME}" >/dev/null 2>&1; then
      log "peer0.${zones[$i]}.farm.tn already joined ${CHANNEL_NAME}"
    else
      log "Joining peer0.${zones[$i]}.farm.tn to ${CHANNEL_NAME}"
      peer channel join -b "${ROOT_DIR}/network/channel-artifacts/${CHANNEL_NAME}.block"
    fi
  done
}

main() {
  start_ca
  register_and_enroll_nodes
  generate_genesis
  start_orderers
  start_peers
  create_and_join_channel
  "${ROOT_DIR}/scripts/deploy-chaincode.sh"
  log "Bootstrap complete"
}

main "$@"
