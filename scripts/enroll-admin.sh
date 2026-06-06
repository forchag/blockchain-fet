set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${ROOT_DIR}/logs/bootstrap.log"
CA_URL="${CA_URL:-https://admin:adminpw@localhost:7054}"
CA_NAME="${CA_NAME:-ca-farm}"
FABRIC_CA_CLIENT_HOME="${FABRIC_CA_CLIENT_HOME:-${ROOT_DIR}/network/crypto-config/peerOrganizations/farm.tn}"
TLS_CERTFILES="${TLS_CERTFILES:-${ROOT_DIR}/network/organizations/fabric-ca/farm/ca-cert.pem}"
ADMIN_MSP="${ADMIN_MSP:-${FABRIC_CA_CLIENT_HOME}/users/Admin@farm.tn/msp}"

mkdir -p "$(dirname "${LOG_FILE}")"
log() { printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "${LOG_FILE}" >&2; }
fatal() { log "ERROR: $*"; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fatal "required command not found: $1"; }

write_node_ous() {
  local msp_dir="$1" cacert="$2"
  mkdir -p "${msp_dir}"
  cat > "${msp_dir}/config.yaml" <<EOF2
NodeOUs:
  Enable: true
  ClientOUIdentifier:
    Certificate: cacerts/localhost-7054-ca-farm.pem
    OrganizationalUnitIdentifier: client
  PeerOUIdentifier:
    Certificate: cacerts/localhost-7054-ca-farm.pem
    OrganizationalUnitIdentifier: peer
  AdminOUIdentifier:
    Certificate: cacerts/localhost-7054-ca-farm.pem
    OrganizationalUnitIdentifier: admin
  OrdererOUIdentifier:
    Certificate: cacerts/localhost-7054-ca-farm.pem
    OrganizationalUnitIdentifier: orderer
EOF2
  if [[ -f "${cacert}" ]]; then
    mkdir -p "${msp_dir}/tlscacerts"
    cp "${cacert}" "${msp_dir}/tlscacerts/ca.crt"
  fi
}

main() {
  need fabric-ca-client
  export FABRIC_CA_CLIENT_HOME
  mkdir -p "${FABRIC_CA_CLIENT_HOME}"
  if [[ -f "${ADMIN_MSP}/signcerts/cert.pem" ]]; then
    log "Admin MSP already enrolled at ${ADMIN_MSP}"
  else
    log "Enrolling FarmMSP admin"
    fabric-ca-client enroll -u "${CA_URL}" --caname "${CA_NAME}" -M "${ADMIN_MSP}" --tls.certfiles "${TLS_CERTFILES}"
  fi
  write_node_ous "${ADMIN_MSP}" "${TLS_CERTFILES}"
  mkdir -p "${FABRIC_CA_CLIENT_HOME}/msp"
  cp "${ADMIN_MSP}/config.yaml" "${FABRIC_CA_CLIENT_HOME}/msp/config.yaml"
  log "Admin enrollment complete"
}

main "$@"
