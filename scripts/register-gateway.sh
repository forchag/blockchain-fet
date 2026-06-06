set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${ROOT_DIR}/logs/bootstrap.log"
ZONE_OID="${ZONE_OID:-1.3.6.1.4.1.55555.1.1}"
CA_NAME="${CA_NAME:-ca-farm}"
CA_HOST="${CA_HOST:-localhost}"
CA_PORT="${CA_PORT:-7054}"
CA_SCHEME="${CA_SCHEME:-https}"
CA_ADMIN_URL="${CA_ADMIN_URL:-${CA_SCHEME}://admin:adminpw@${CA_HOST}:${CA_PORT}}"
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
validate_zone() { case "$1" in North|South|East|West) ;; *) fatal "invalid zone '$1'; expected North, South, East, or West";; esac; }
json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"; }

set_admin_peer() {
  export CORE_PEER_LOCALMSPID=FarmMSP CORE_PEER_ADDRESS=localhost:7051 CORE_PEER_TLS_ENABLED=true
  export CORE_PEER_MSPCONFIGPATH="${ROOT_DIR}/network/crypto-config/peerOrganizations/farm.tn/users/Admin@farm.tn/msp"
  export CORE_PEER_TLS_ROOTCERT_FILE="${ROOT_DIR}/network/crypto-config/peerOrganizations/farm.tn/peers/peer0.north.farm.tn/tls/ca.crt"
}

generate_csr() {
  local id="$1" zone="$2" dir="$3" key="$4" csr="$5" cfg="${dir}/csr.conf"
  openssl genpkey -algorithm ED25519 -out "${key}"
  cat > "${cfg}" <<EOF2
[ req ]
prompt = no
distinguished_name = dn
req_extensions = ext
[ dn ]
CN = ${id}
O = FarmMSP
OU = Gateway
[ ext ]
${ZONE_OID} = ASN1:UTF8String:${zone}
EOF2
  openssl req -new -key "${key}" -out "${csr}" -config "${cfg}"
}

assign_role() {
  local id="$1" zone="$2" expires nonce
  need peer
  expires="$(date -u -d '+365 days' '+%Y-%m-%dT%H:%M:%SZ')"
  nonce="gateway-${id}-$(date -u '+%s')"
  set_admin_peer
  peer chaincode invoke -C "${CHANNEL_NAME}" -n "${CHAINCODE_NAME}" \
    -o "${ORDERER_ADDRESS}" --ordererTLSHostnameOverride orderer0.farm.tn --tls --cafile "${ORDERER_TLS_CA}" \
    -c "{\"Args\":[\"AssignRole\",\"${id}\",\"Gateway\",\"${zone}\",\"${expires}\",\"${nonce}\"]}" >/dev/null
}

main() {
  [[ $# -ge 2 ]] || fatal "usage: bash scripts/register-gateway.sh <GatewayID> <North|South|East|West> [secret]"
  need fabric-ca-client; need openssl; need python3
  local id="$1" zone="$2" secret="${3:-${1}pw}" gateway_dir key csr cert summary
  validate_zone "${zone}"
  gateway_dir="${ROOT_DIR}/network/identities/gateways/${id}"
  key="${gateway_dir}/ed25519_sk.pem"; csr="${gateway_dir}/${id}.csr"; cert="${gateway_dir}/msp/signcerts/cert.pem"
  mkdir -p "${gateway_dir}"
  export FABRIC_CA_CLIENT_HOME
  if fabric-ca-client identity list --caname "${CA_NAME}" --tls.certfiles "${TLS_CERTFILES}" 2>/dev/null | grep -q "Name: ${id},"; then
    log "Gateway ${id} already registered"
  else
    fabric-ca-client register --caname "${CA_NAME}" --id.name "${id}" --id.secret "${secret}" --id.type client \
      --id.attrs "role=Gateway:ecert,zone=${zone}:ecert,hf.Registrar.Roles=client:ecert,hf.Registrar.Attributes=role,zone:ecert" --tls.certfiles "${TLS_CERTFILES}"
  fi
  printf '%s\n' "${zone}" > "${gateway_dir}/zone"
  [[ -f "${csr}" && -f "${key}" ]] || generate_csr "${id}" "${zone}" "${gateway_dir}" "${key}" "${csr}"
  if [[ ! -f "${cert}" ]]; then
    fabric-ca-client enroll -u "${CA_SCHEME}://${id}:${secret}@${CA_HOST}:${CA_PORT}" --caname "${CA_NAME}" -M "${gateway_dir}/msp" \
      --csr.cn "${id}" --csr.names "O=FarmMSP,OU=Gateway" --enrollment.attrs "role,zone" --tls.certfiles "${TLS_CERTFILES}"
  fi
  assign_role "${id}" "${zone}"
  summary="{\"id\":$(json_escape "${id}"),\"zone\":$(json_escape "${zone}"),\"csr\":$(json_escape "${csr}"),\"certificate\":$(json_escape "${cert}"),\"privateKey\":$(json_escape "${key}")}" 
  printf '%s\n' "${summary}"
  log "Gateway ${id} registered and enrolled"
}

main "$@"
