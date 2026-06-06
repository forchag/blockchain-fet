#!/usr/bin/env python3
"""Latency benchmark for the live HRBAC Fabric network."""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.performance.bench_throughput import LEVELS, PeerConfig, invoke
from tests.performance.workload_generator import OperationType, WorkloadGenerator, validate_distribution

DURATION_SECONDS = 60
RESULTS = ROOT / "results" / "latency.csv"
SENSOR_WRITE_P95_LIMIT_MS = 2_000.0


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((p / 100) * (len(ordered) - 1)))))
    return ordered[index]


def run_latency(level: int, duration: int, seed: int) -> dict[OperationType, list[float]]:
    config = PeerConfig()
    generator = WorkloadGenerator(seed=seed)
    stop = threading.Event()
    lock = threading.Lock()
    samples = {kind: [] for kind in OperationType}

    def worker() -> None:
        while not stop.is_set():
            operation = generator.next_operation()
            start = time.perf_counter()
            try:
                ok = invoke(config, operation)
            except Exception:
                ok = False
            elapsed_ms = (time.perf_counter() - start) * 1000
            if ok:
                with lock:
                    samples[operation.kind].append(elapsed_ms)

    with ThreadPoolExecutor(max_workers=level) as executor:
        futures = [executor.submit(worker) for _ in range(level)]
        time.sleep(duration)
        stop.set()
        for future in futures:
            future.result()
    return samples


def dry_run(output: Path) -> None:
    observed = validate_distribution(lambda: WorkloadGenerator(seed=84))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["mode", "sensor_write_ratio", "query_ratio", "admin_ratio", "levels", "duration_seconds", "sensor_write_p95_limit_ms"])
        writer.writeheader()
        writer.writerow({"mode": "dry-run", "sensor_write_ratio": f"{observed[OperationType.SENSOR_WRITE]:.4f}", "query_ratio": f"{observed[OperationType.QUERY]:.4f}", "admin_ratio": f"{observed[OperationType.ADMIN]:.4f}", "levels": " ".join(map(str, LEVELS)), "duration_seconds": DURATION_SECONDS, "sensor_write_p95_limit_ms": SENSOR_WRITE_P95_LIMIT_MS})
    print(f"dry-run ok: wrote latency configuration validation to {output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="validate workload/configuration without invoking Fabric")
    parser.add_argument("--output", type=Path, default=RESULTS)
    parser.add_argument("--duration", type=int, default=DURATION_SECONDS)
    args = parser.parse_args()
    if args.dry_run:
        dry_run(args.output)
        return 0
    if shutil.which("peer") is None:
        print("peer CLI is required for live benchmarks", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    sensor_p95_failures = []
    for level in LEVELS:
        samples = run_latency(level, args.duration, seed=9000 + level)
        for kind, values in samples.items():
            row = {
                "concurrency": level,
                "operation": kind.value,
                "samples": len(values),
                "mean_ms": f"{mean(values):.4f}" if values else "0.0000",
                "p50_ms": f"{percentile(values, 50):.4f}",
                "p90_ms": f"{percentile(values, 90):.4f}",
                "p95_ms": f"{percentile(values, 95):.4f}",
                "p99_ms": f"{percentile(values, 99):.4f}",
            }
            rows.append(row)
            if kind is OperationType.SENSOR_WRITE and percentile(values, 95) >= SENSOR_WRITE_P95_LIMIT_MS:
                sensor_p95_failures.append((level, percentile(values, 95)))
    with args.output.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.output}")
    if sensor_p95_failures:
        for level, p95 in sensor_p95_failures:
            print(f"sensor_write P95 at concurrency {level} was {p95:.2f}ms, expected < {SENSOR_WRITE_P95_LIMIT_MS:.0f}ms", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
