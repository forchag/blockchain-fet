set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${ROOT_DIR}/logs/bootstrap.log"
ZONE_OID="${ZONE_OID:-1.3.6.1.4.1.55555.1.1}"
CA_NAME="${CA_NAME:-ca-farm}"
CA_HOST="${CA_HOST:-localhost}"
CA_PORT="${CA_PORT:-7054}"
CA_SCHEME="${CA_SCHEME:-https}"
TLS_CERTFILES="${TLS_CERTFILES:-${ROOT_DIR}/network/organizations/fabric-ca/farm/ca-cert.pem}"
CHANNEL_NAME="${CHANNEL_NAME:-farmchannel}"
CHAINCODE_NAME="${CHAINCODE_NAME:-hrbac}"
ORDERER_ADDRESS="${ORDERER_ADDRESS:-localhost:7050}"
ORDERER_TLS_CA="${ORDERER_TLS_CA:-${ROOT_DIR}/network/crypto-config/ordererOrganizations/farm.tn/orderers/orderer0.farm.tn/tls/ca.crt}"

mkdir -p "$(dirname "${LOG_FILE}")"
log() { printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "${LOG_FILE}" >&2; }
fatal() { log "ERROR: $*"; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fatal "required command not found: $1"; }
validate_zone() { case "$1" in North|South|East|West) ;; *) fatal "invalid zone '$1'; expected North, South, East, or West";; esac; }

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
OU = Sensor
[ ext ]
${ZONE_OID} = ASN1:UTF8String:${zone}
EOF2
  openssl req -new -key "${key}" -out "${csr}" -config "${cfg}"
}

assign_role() {
  local id="$1" zone="$2" expires nonce
  need peer
  expires="$(date -u -d '+365 days' '+%Y-%m-%dT%H:%M:%SZ')"
  nonce="sensor-${id}-$(date -u '+%s')"
  set_admin_peer
  peer chaincode invoke -C "${CHANNEL_NAME}" -n "${CHAINCODE_NAME}" \
    -o "${ORDERER_ADDRESS}" --ordererTLSHostnameOverride orderer0.farm.tn --tls --cafile "${ORDERER_TLS_CA}" \
    -c "{\"Args\":[\"AssignRole\",\"${id}\",\"Sensor\",\"${zone}\",\"${expires}\",\"${nonce}\"]}" >/dev/null
}

main() {
  [[ $# -ge 4 ]] || fatal "usage: bash scripts/enroll-sensor.sh <SensorID> <North|South|East|West> <GatewayID> <GatewaySecret> [sensorSecret]"
  need fabric-ca-client; need openssl; need python3
  local id="$1" zone="$2" gateway_id="$3" gateway_secret="$4" secret="${5:-${1}pw}"
  local gateway_dir="${ROOT_DIR}/network/identities/gateways/${gateway_id}" sensor_dir key csr cert flash gateway_zone
  validate_zone "${zone}"
  [[ -f "${gateway_dir}/zone" ]] || fatal "gateway zone metadata not found; register gateway first: ${gateway_dir}/zone"
  gateway_zone="$(cat "${gateway_dir}/zone")"
  [[ "${gateway_zone}" == "${zone}" ]] || fatal "sensor zone ${zone} does not match gateway ${gateway_id} zone ${gateway_zone}"
  export FABRIC_CA_CLIENT_HOME="${gateway_dir}"
  if fabric-ca-client identity list --caname "${CA_NAME}" --tls.certfiles "${TLS_CERTFILES}" 2>/dev/null | grep -q "Name: ${id},"; then
    log "Sensor ${id} already registered"
  else
    fabric-ca-client register --caname "${CA_NAME}" --id.name "${id}" --id.secret "${secret}" --id.type client \
      --id.attrs "role=Sensor:ecert,zone=${zone}:ecert" --tls.certfiles "${TLS_CERTFILES}"
  fi
  sensor_dir="${ROOT_DIR}/network/identities/sensors/${id}"
  key="${sensor_dir}/ed25519_sk.pem"; csr="${sensor_dir}/${id}.csr"; cert="${sensor_dir}/msp/signcerts/cert.pem"; flash="${sensor_dir}/${id}.flash.bin"
  mkdir -p "${sensor_dir}"
  [[ -f "${csr}" && -f "${key}" ]] || generate_csr "${id}" "${zone}" "${sensor_dir}" "${key}" "${csr}"
  if [[ ! -f "${cert}" ]]; then
    fabric-ca-client enroll -u "${CA_SCHEME}://${id}:${secret}@${CA_HOST}:${CA_PORT}" --caname "${CA_NAME}" -M "${sensor_dir}/msp" \
      --csr.cn "${id}" --csr.names "O=FarmMSP,OU=Sensor" --enrollment.attrs "role,zone" --tls.certfiles "${TLS_CERTFILES}"
  fi
  python3 "${ROOT_DIR}/scripts/make_flash_package.py" --cert "${cert}" --key "${key}" --zone "${zone}" --out "${flash}"
  assign_role "${id}" "${zone}"
  printf '{"id":"%s","zone":"%s","gateway":"%s","certificate":"%s","privateKey":"%s","flashPackage":"%s"}\n' "${id}" "${zone}" "${gateway_id}" "${cert}" "${key}" "${flash}"
  log "Sensor ${id} enrolled and packaged"
}

main "$@"
