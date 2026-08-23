# VARIABLE_MAPPING.md

Maps every analyst raw-data field used in the V10 manuscript to its meaning,
units, and (where relevant) the source-code construct it corresponds to.
Fields not listed here were inspected but not used in any manuscript claim.

## `raw/field/authorization_decisions.csv`

| Field | Meaning | Units / values |
|---|---|---|
| `timestamp` | Decision time, `+01:00` offset | ISO-8601 |
| `entry_id` | Audit-entry identifier | string |
| `tx_id` | Fabric transaction id; populated for `WriteSensor`, mostly blank for other operations (see `DATA_QUALITY_REPORT.md`) | hex string or blank |
| `caller_id` | Pseudonymous caller identifier (`usr-*`, `sns-*`) | string |
| `caller_role` | One of the seven HRBAC roles in `chaincode/hrbac/roles.go` | enum |
| `operation` | Requested operation (`WriteSensor`, `ReadZone`, `ReadAudit`, `ReadSensorData`, `ReadProvenance`, `ReadEnvironmentalRecord`, `ControlZone`) | enum |
| `resource` | Requested resource label | string |
| `zone` | Farm zone (`North`/`South`/`East`/`West`) | enum |
| `decision` | `allowed` / `denied` | enum |
| `deny_reason` | Populated only when `decision=denied` | enum, e.g. `REVOKED_CREDENTIAL` |
| `latency_ms` | End-to-end decision latency at the gateway | milliseconds |

## `raw/field/sensor_transactions.csv`

| Field | Meaning | Units |
|---|---|---|
| `soil_moisture` | Engineering-unit soil moisture | percent (0-100) |
| `temp_c` | Engineering-unit temperature | degrees Celsius |
| `rbac_overhead_ms` | Chaincode-logged authorization-associated span; corresponds to the `rbac_overhead_ms` field written by `CheckAccess` inside `WriteSensorData` | milliseconds |
| `signature_valid` | Gateway-recorded signature-check outcome. **Caveat:** shown in Sec. 6.9.3 / `05_crt_quantization.py`-adjacent audit to be produced by a verifier that checks the wrong bytes and fails open, so `True` does not mean the sensor signature was actually checked and passed. | boolean |
| `crt_residues_received` | Number of the three CRT residue packets received (2 or 3) | integer |
| `energy_mj` | Per-transmission LoRa energy, residue mode | millijoules |

**Calibration gap:** `soil_moisture` (percent) has no documented inverse mapping
to the firmware's `soil_moisture_raw` (12-bit ADC count, 0-4095) anywhere in
this repository (`esp32/main/sensor.c` transmits the raw ADC value; no
gateway/backend code converts it to a percentage). `05_crt_quantization.py`
states and tests this gap explicitly rather than assuming a calibration
constant.

## `raw/experiments/peer_scaling_runs.csv` / `peer_scaling_transactions.csv`

| Field | Meaning |
|---|---|
| `run_id` | `PEER-<peer_count>-R<repetition>`; repetition number is the counterbalancing block |
| `block_id` | A per-run identifier in the transaction file (confirmed one-to-one with `run_id`, **not** a Latin-square block — see `DATA_DISCREPANCIES.md`) |
| `serial_position` | Transaction order within one run (0-129); NOT the campaign-wide run order, which is derived from `start_timestamp` instead |
| `rbac_overhead_ms` | Same field as in the field trace, in the controlled-campaign context |

## `raw/experiments/throughput_runs.csv`

| Field | Meaning |
|---|---|
| `concurrency_level` | Offered client concurrency (10-100, step 10) |
| `condition` | `baseline` (no access control) or `hrbac` |
| `tps` | Committed transactions per second over the run window |

## `raw/security/authorization_boundary_attempts.csv`

| Field | Meaning |
|---|---|
| `scenario` | Collection-time label (8 scenarios x 1000); not used to interpret results directly (Sec. 6.6) |
| `attacker_role` / `operation` | Used to build the disclosed operation-to-permission oracle in `06_security_oracle.py` |
| `deny_reason` | One of 6 mechanisms; `ROLE_INSUFFICIENT` / `OP_NOT_PERMITTED` are the two scored against the role/operation oracle |

## `raw/field/revocation_stages.csv`

| Field | Meaning |
|---|---|
| `event_id` | Confirmed 1:1 with `cert_user_id` in this trace (132 distinct values each) |
| `stage_name` | One of `publish`, `gossip`, `propagation_complete`, `cache_invalidation` |
| `status` | `completed` / `delayed` |

No duration field exists; see `DATA_DISCREPANCIES.md` for the consequence
(withdrawal of stage-duration statistics from V9.2).
