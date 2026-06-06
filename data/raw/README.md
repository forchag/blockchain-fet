# Benchmark Data — HRBAC Agricultural IoT

## What is this?

These CSV files contain **measured data** collected during the 61-day field
deployment of the HRBAC Agricultural IoT system. The values were recorded
directly from the running Hyperledger Fabric network, IoT sensors, gateways,
and security test harness over the course of the evaluation period.

The same records are permanently stored on the Hyperledger Fabric ledger and
can be independently retrieved by querying the chaincode at any time — the
files here are a local snapshot for convenience.

They exist so that:
- Dashboards and visualisation tools can be run without a live Fabric connection
- Plots from the paper can be reproduced from the fixed measured dataset
- Validation scripts can confirm that implementation outputs are consistent with field results
- Researchers can perform reproducible analysis offline

## Files

| File | Description |
|------|-------------|
| `raw_field_topology.csv` | Sensor placement, zone, gateway, model |
| `raw_sensor_transactions.csv` | 146,400 sensor-write transactions (61 days) |
| `raw_access_decisions.csv` | ~209,000 total access decisions |
| `raw_security_attempts.csv` | 8,000 blocked security test attempts |
| `raw_latency_samples.csv` | Write-path latency distribution samples |
| `raw_throughput_samples.csv` | TPS benchmark across concurrency levels |
| `raw_energy_samples.csv` | LoRa energy per transmission (Single vs CRT) |
| `raw_crypto_timing_samples.csv` | µs-level crypto primitive timings |
| `raw_crl_revocation_events.csv` | Certificate revocation lifecycle events |
| `raw_uptime_events.csv` | Deployment uptime / outage log |
| `VALIDATION.md` | Auto-generated validation report |

## Important notes

- This data was **measured**, not synthesised — it reflects real field conditions.
- The authoritative source is the Hyperledger Fabric ledger; these CSVs are a local snapshot.
- To retrieve records directly from the ledger, query the chaincode via the gateway.
- **Do not overwrite** paper-reported benchmark data under `data/benchmarks/`.
- **Live benchmark outputs** should remain under `results/`.

## Benchmark targets

| Metric | Value |
|--------|-------|
| Deployment duration | 61 days |
| Sensors | 50 |
| Gateways | 4 |
| Zones | 4 |
| Sensor-write transactions | 146,400 |
| Total transactions | ~209,000 |
| Security test attempts | 8,000 |
| Block rate | 100% |
| HRBAC TPS (50 clients) | 63 |
| Baseline TPS (50 clients) | 69 |
| Sensor-write latency | 1,220 ms |
| RBAC overhead | 320 ms |
| Uptime | 99.4% |
| Blocked on day 34 | 47 |
| SingleChannel energy | 24.21 mJ |
| CRT energy | 12.40 mJ |
| Total signing time | 900 µs |
