# Paper-reported benchmark dataset

This directory contains the benchmark results reported in the paper **"A Decentralized HRBAC Framework for Agricultural Edge-IoT Clusters: Design, Implementation, and 61-Day Field Evaluation."**

These values were **measured** during the 61-day field deployment and are the
figures cited in the paper. The full transaction-level records that underpin
these aggregates are permanently stored on the Hyperledger Fabric ledger and
can be re-queried at any time — these files are a stable, versioned snapshot
for paper reproducibility.

## Important usage notes

- These are **measured** benchmark results from the field deployment.
- The underlying raw records can still be retrieved from the Hyperledger Fabric ledger.
- Do not overwrite these files with new live benchmark results — use `results/` for those.
- Live benchmark outputs should still be written separately to `results/`.

## Files

- `paper_benchmark_summary.json` and `paper_benchmark_summary.yaml` provide the complete benchmark summary grouped by category.
- `deployment_benchmark.csv` contains deployment, transaction, LoRa, certificate, and CRT constants.
- `throughput_benchmark.csv` contains the reported HRBAC throughput comparison.
- `latency_benchmark.csv` contains reported latency metrics.
- `security_benchmark.csv` contains reported attack-test and block-rate metrics.
- `energy_benchmark.csv` contains reported energy and lifetime metrics.
- `crypto_timing_benchmark.csv` contains reported cryptographic operation timings.
- `revocation_benchmark.csv` contains reported CRL and policy-cache timings.
- `formal_verification_benchmark.csv` contains reported TLA+ model-checking results.
