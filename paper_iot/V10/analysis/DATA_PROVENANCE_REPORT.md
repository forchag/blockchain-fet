# DATA_PROVENANCE_REPORT.md

Classification of every dataset used or considered for V10, per the
categories: `verified_real_field`, `verified_real_controlled`,
`scripted_test`, `processed_from_verified_real`, `simulated`,
`provenance_uncertain`, `missing`.

"Verified" here means: internally consistent across independent capture
streams (field CSVs cross-checked against per-device/per-gateway JSON-lines
logs and a Fabric-ledger block sample down to matching transaction ids),
free of the synthetic-data red flags checked for below, and structurally
consistent with the actual deployed source code (CRT moduli, role hierarchy,
signature construction). This is the strongest verification available from
data-analysis alone; it is not a substitute for chain-of-custody
documentation from the original field collection, which was outside the
scope of this analysis.

## Datasets classified `verified_real_field`

- `raw/field/authorization_decisions.csv` (209,000 rows)
- `raw/field/sensor_transactions.csv` (146,400 rows)
- `raw/field/raw_field_topology.csv` (50 rows)
- `raw/field/connectivity_outages.csv` (3 rows)
- `raw/field/revocation_denials.csv` (973 rows)
- `raw/field/revocation_stages.csv` (200 rows)
- `raw/provenance/device_logs/*.log` (50 files, 146,400 lines total) — cross-checked: `reading_id`, `timestamp`, `soil_moisture`, `temp_c`, `latency_ms` and `rbac_overhead_ms` values match `sensor_transactions.csv` row-for-row for the sampled device (`esp32-001`); device logs do not carry a `tx_id` field.
- `raw/provenance/gateway_logs/*.log` (4 files) — cross-checked: `tx_id` and timestamps match `sensor_transactions.csv` / `authorization_decisions.csv` for the sampled gateway (`gw-north`).
- `raw/provenance/fabric_ledger/ledger_sample.jsonl` (100 blocks) — a sample, not the full ledger; block contents cross-check against `sensor_transactions.csv` timestamps and tx ids for the sampled window.

Basis: realistic non-round values, hex transaction identifiers (not
sequential placeholders), internal cross-stream consistency (device logs,
gateway logs and the ledger sample independently reproduce the same
transaction ids and timestamps as the aggregate CSVs), and exact
reproduction of several counts V9.2 reported as field totals (209,000;
146,400; 973; 200; 3 outages) from raw row counts rather than from any
target value in the analysis code.

## Datasets classified `verified_real_controlled`

- `raw/experiments/peer_scaling_runs.csv` (32 rows) and `peer_scaling_transactions.csv` (4,160 rows)
- `raw/experiments/throughput_runs.csv` (100 rows)
- `raw/experiments/energy_measurements.csv` (300 rows)
- `raw/experiments/cryptographic_timings.csv` (900 rows)

Basis: run manifests carry real execution timestamps that reconstruct an
internally consistent counterbalancing design (two complementary 4x4
Latin-square cycles for the peer-scaling campaign, confirmed by
`analysis/scripts/03_peer_scaling.py`; a single fixed-ascending-order session
for the throughput campaign, confirmed by `04_throughput.py`); per-run
transaction counts are exactly constant (130/run for peer-scaling); values
show realistic sample-to-sample variability rather than round numbers.

## Datasets classified `scripted_test`

- `raw/security/authorization_boundary_attempts.csv` (8,000 rows)

Basis: explicitly a scripted campaign per its own structure (8 scenarios of
exactly 1,000 attempts each); classified as scripted testing per the task's
requirement to distinguish scripted security tests from field attacks, not
as a lesser-quality dataset.

## Datasets classified `provenance_uncertain` (pre-existing repository data, NOT used for V10)

- `data/raw/*.csv` (10 files; already present in the repository before this analysis)
- `data/benchmarks/paper_benchmark_summary.json`, `paper_benchmark_summary.yaml`, and the associated `*_benchmark.csv` files
- `data/raw/VALIDATION.md`

Basis for `provenance_uncertain` classification:

1. `data/raw/VALIDATION.md` checks its own numbers against a manuscript's
   reported values ("Expected" column) rather than against an independent
   ground truth -- the direction of validation is inverted from what
   reproducible research requires.
2. Row-level content differs structurally from the analyst package despite
   identical row counts: `decision` values are `GRANT`/binary-literal rather
   than `allowed`/`denied`; `tx_id` values are sequential placeholders
   (`SW-00000001`) rather than realistic hex identifiers; `latency_ms`
   values include suspiciously round entries (e.g. exactly `1220.0`).
3. `data/benchmarks/paper_benchmark_summary.json`'s own header attributes it
   to a differently titled paper ("A Decentralized HRBAC Framework for
   Agricultural Edge-IoT Clusters...") and its reported values (e.g. HRBAC
   TPS 63, RBAC overhead 8.7%) do not match either V9.2's or V10's verified
   figures.
4. No script in this repository (`gateway/paper_benchmarks.py`,
   `data/comp.py`) generates these files from raw measurements; they are
   loaded as fixed targets.

**Disposition:** these files are left untouched in place (this study does
not reorganize or delete unrelated repository content) and are not used as
input to any V10 script or claim. `DATA_DISCREPANCIES.md` records the
comparison in more detail.

## Datasets classified `missing`

See `MISSING_DATA.md` for the full list (analysis pipeline, policy oracle,
corrected implementation, calibration constant, revocation episode key,
positive-request corpus).

## No datasets classified `simulated`

No dataset in the analyst package shows hallmarks of simulation presented as
measurement (fixed-seed resampling used only for bootstrap confidence
intervals, never for generating "new" observations; no script in
`analysis/scripts/` calls a random-number generator to produce a value used
as a reported measurement rather than a resampling statistic).
