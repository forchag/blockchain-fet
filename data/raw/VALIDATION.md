# HRBAC IoT Benchmark — Validation

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| Sensor writes | 146,400 | 146,400 | PASS |
| Total access decisions | ~209,000 | 209,000 | PASS |
| Security attempts | 8,000 | 8,000 | PASS |
| Block rate | 100% | 100.0% | PASS |
| Mean HRBAC TPS @ 50 clients | ~63 | 62.19 | PASS |
| Mean Baseline TPS @ 50 clients | ~69 | 69.14 | PASS |
| Mean sensor-write latency | ~1,220 ms | 1219.8 ms | PASS |
| Mean RBAC overhead | ~320 ms | 319.9 ms | PASS |
| P95 latency (4 peers) | ~1,480 ms | 1324.9 ms | WARN |
| P95 latency (32 peers) | ~855 ms | 903.2 ms | PASS |
| Mean SingleChannel energy | ~24.21 mJ | 24.200 mJ | PASS |
| Mean CRT energy | ~12.40 mJ | 12.411 mJ | PASS |
| Energy reduction | ~48.8% | 48.7% | PASS |
| Overall uptime | ~99.4% | 99.36% | PASS |
| Crypto timing samples | ≥5,000 | 5,000 | PASS |

## Day-34 blocked attempts

Expected: 47
Actual: 47  PASS
