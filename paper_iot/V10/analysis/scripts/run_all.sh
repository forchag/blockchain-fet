#!/usr/bin/env bash
# Regenerates every V10 numerical result, table input and figure from the
# analyst's raw-data package. Run from anywhere; paths are resolved relative
# to this script.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

for script in 01_extract_and_inventory.py 02_field_deployment.py 03_peer_scaling.py \
              04_throughput.py 05_crt_quantization.py 06_security_oracle.py \
              07_revocation.py 08_energy_crypto.py 09_data_quality.py \
              10_build_claim_map.py 11_build_macros.py 12_make_figures.py; do
  echo "==> $script"
  python3 "$script"
done
echo "==> V10 analysis pipeline complete."
