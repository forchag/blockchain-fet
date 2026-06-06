"""Load and validate benchmark values reported in the HRBAC field-evaluation paper."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

_BENCHMARK_PATH = Path(__file__).resolve().parents[1] / "data" / "benchmarks" / "paper_benchmark_summary.json"


def _load_benchmarks() -> dict[str, dict[str, Any]]:
    with _BENCHMARK_PATH.open(encoding="utf-8") as benchmark_file:
        return json.load(benchmark_file)


def get_all_benchmarks() -> dict[str, dict[str, Any]]:
    """Return all paper-reported benchmark categories and metrics."""
    return deepcopy(_load_benchmarks())


def get_benchmark_category(category: str) -> dict[str, Any] | None:
    """Return one benchmark category by name, or None when it is absent."""
    benchmarks = _load_benchmarks()
    category_data = benchmarks.get(category)
    if category_data is None:
        return None
    return deepcopy(category_data)


def get_metric(metric_name: str) -> Any | None:
    """Return a metric value by searching all benchmark categories."""
    for metrics in _load_benchmarks().values():
        if metric_name in metrics:
            return deepcopy(metrics[metric_name])
    return None


def validate_paper_benchmarks() -> bool:
    """Validate cross-field invariants in the paper-reported benchmark dataset."""
    benchmarks = _load_benchmarks()
    deployment = benchmarks["deployment"]
    security = benchmarks["security"]
    crt = benchmarks["crt"]
    throughput = benchmarks["throughput"]
    latency = benchmarks["latency"]

    checks = {
        "fabric_total_nodes": deployment["fabric_total_nodes"]
        == deployment["fabric_peers"] + deployment["raft_orderers"] + deployment["fabric_ca_count"],
        "security_attempts": security["security_vectors"] * security["attempts_per_vector"]
        == security["security_test_attempts"],
        "crt_max_value": crt["crt_max_value"] == 97 * 101 * 103,
        "hrbac_tps_range": throughput["expected_hrbac_tps_min"]
        <= throughput["hrbac_tps"]
        <= throughput["expected_hrbac_tps_max"],
        "sensor_write_latency": latency["sensor_write_total_latency_ms"]
        < latency["expected_sensor_write_p95_max_ms"],
        "block_rate": security["block_rate_percent"] == 100,
    }

    failed_checks = [name for name, passed in checks.items() if not passed]
    if failed_checks:
        raise ValueError(f"Invalid paper benchmark dataset: {', '.join(failed_checks)}")
    return True
