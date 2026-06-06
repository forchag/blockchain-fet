#!/usr/bin/env python3
"""Compare live benchmark output against paper-reported benchmark values."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
PAPER_SUMMARY = ROOT / "data" / "benchmarks" / "paper_benchmark_summary.json"
RESULTS_DIR = ROOT / "results"
THROUGHPUT_CSV = RESULTS_DIR / "throughput.csv"
LATENCY_CSV = RESULTS_DIR / "latency.csv"
SECURITY_CSV = RESULTS_DIR / "security.csv"
REPORT = RESULTS_DIR / "live_vs_paper_report.md"
NO_LIVE_MESSAGE = "No live benchmark result file found. Run the benchmark suite first."


@dataclass(frozen=True)
class CheckResult:
    metric: str
    paper_value: str
    live_value: str
    acceptable_range: str
    status: str
    comment: str

    @property
    def failed(self) -> bool:
        return self.status == "FAIL"


@dataclass(frozen=True)
class LiveMetric:
    value: float | None
    comment: str


def load_paper_summary() -> dict:
    with PAPER_SUMMARY.open() as fh:
        return json.load(fh)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip().replace("%", "")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def rows_matching(rows: Iterable[dict[str, str]], **criteria: object) -> list[dict[str, str]]:
    matches = []
    for row in rows:
        ok = True
        for key, expected in criteria.items():
            actual = row.get(key)
            if actual is None or str(actual).strip().lower() != str(expected).strip().lower():
                ok = False
                break
        if ok:
            matches.append(row)
    return matches


def throughput_at_50_clients(path: Path) -> LiveMetric:
    rows = read_csv_rows(path)
    summary = rows_matching(rows, concurrency=50, repeat="summary")
    if summary:
        value = parse_float(summary[-1].get("mean_tps"))
        if value is not None:
            return LiveMetric(value, "50-client summary mean_tps from results/throughput.csv")

    samples = [parse_float(row.get("tps")) for row in rows_matching(rows, concurrency=50)]
    values = [value for value in samples if value is not None]
    if values:
        return LiveMetric(sum(values) / len(values), "average of 50-client TPS samples from results/throughput.csv")

    return LiveMetric(None, "no 50-client HRBAC TPS value found in results/throughput.csv")


def sensor_write_p95_latency(path: Path) -> LiveMetric:
    rows = rows_matching(read_csv_rows(path), operation="sensor_write")
    values = [(row.get("concurrency", "unknown"), parse_float(row.get("p95_ms"))) for row in rows]
    values = [(concurrency, value) for concurrency, value in values if value is not None]
    if not values:
        return LiveMetric(None, "no sensor_write p95_ms value found in results/latency.csv")

    concurrency, value = max(values, key=lambda item: item[1])
    return LiveMetric(value, f"maximum sensor_write p95_ms from results/latency.csv (concurrency {concurrency})")


def security_block_rate(path: Path) -> LiveMetric:
    rows = read_csv_rows(path)
    field_candidates = ("block_rate_percent", "block_rate", "blocked_percent", "blocked_rate_percent")
    for row in rows:
        for field in field_candidates:
            value = parse_float(row.get(field))
            if value is not None:
                if field == "block_rate" and value <= 1:
                    value *= 100
                return LiveMetric(value, f"{field} from results/security.csv")

    blocked_total = 0.0
    attempts_total = 0.0
    found_counts = False
    for row in rows:
        blocked = parse_float(row.get("blocked") or row.get("blocked_attempts"))
        attempts = parse_float(row.get("attempts") or row.get("total_attempts"))
        if blocked is not None and attempts is not None:
            blocked_total += blocked
            attempts_total += attempts
            found_counts = True
    if found_counts and attempts_total > 0:
        return LiveMetric((blocked_total / attempts_total) * 100, "computed from blocked and attempts counts in results/security.csv")

    return LiveMetric(None, "no security block-rate value found in results/security.csv")


def check_metric(
    *,
    metric: str,
    paper_value: object,
    live: LiveMetric | None,
    acceptable_range: str,
    predicate: Callable[[float], bool],
    missing_comment: str,
) -> CheckResult:
    if live is None:
        return CheckResult(metric, str(paper_value), "missing", acceptable_range, "MISSING", missing_comment)
    if live.value is None:
        return CheckResult(metric, str(paper_value), "unavailable", acceptable_range, "MISSING", live.comment)
    status = "PASS" if predicate(live.value) else "FAIL"
    return CheckResult(metric, str(paper_value), format_number(live.value), acceptable_range, status, live.comment)


def format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def markdown_table(checks: list[CheckResult], missing_files: list[Path]) -> str:
    lines = [
        "# Live vs paper benchmark report",
        "",
        "| metric | paper_value | live_value | acceptable_range | status | comment |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    for check in checks:
        lines.append(
            f"| {check.metric} | {check.paper_value} | {check.live_value} | {check.acceptable_range} | {check.status} | {check.comment} |"
        )
    if missing_files:
        lines.extend(["", "## Missing live benchmark files", ""])
        for path in missing_files:
            lines.append(f"- `{path.relative_to(ROOT)}`")
    lines.append("")
    return "\n".join(lines)


def build_report(strict: bool) -> int:
    paper = load_paper_summary()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    live_paths = [THROUGHPUT_CSV, LATENCY_CSV, SECURITY_CSV]
    present = [path for path in live_paths if path.exists()]
    missing = [path for path in live_paths if not path.exists()]
    if not present:
        REPORT.write_text(NO_LIVE_MESSAGE + "\n")
        return 1 if strict else 0

    throughput = throughput_at_50_clients(THROUGHPUT_CSV) if THROUGHPUT_CSV.exists() else None
    latency = sensor_write_p95_latency(LATENCY_CSV) if LATENCY_CSV.exists() else None
    security = security_block_rate(SECURITY_CSV) if SECURITY_CSV.exists() else None

    expected_min = paper["throughput"].get("expected_hrbac_tps_min", 55)
    expected_max = paper["throughput"].get("expected_hrbac_tps_max", 70)
    latency_max = paper["latency"].get("expected_sensor_write_p95_max_ms", 2000)
    security_rate = paper["security"].get("block_rate_percent", 100)

    checks = [
        check_metric(
            metric="hrbac_tps_50_clients",
            paper_value=paper["throughput"]["hrbac_tps"],
            live=throughput,
            acceptable_range=f"{expected_min}-{expected_max} TPS",
            predicate=lambda value: float(expected_min) <= value <= float(expected_max),
            missing_comment="results/throughput.csv is missing",
        ),
        check_metric(
            metric="sensor_write_p95_latency_ms",
            paper_value=paper["latency"].get("p95_latency_4_peers_ms", paper["latency"].get("sensor_write_total_latency_ms")),
            live=latency,
            acceptable_range=f"< {latency_max} ms",
            predicate=lambda value: value < float(latency_max),
            missing_comment="results/latency.csv is missing",
        ),
        check_metric(
            metric="security_block_rate_percent",
            paper_value=security_rate,
            live=security,
            acceptable_range="100%",
            predicate=lambda value: value == 100.0,
            missing_comment="results/security.csv is missing",
        ),
    ]
    REPORT.write_text(markdown_table(checks, missing))

    if strict and (missing or any(check.status != "PASS" for check in checks)):
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="fail if live files are missing or checks are outside expected ranges")
    args = parser.parse_args()
    try:
        return build_report(args.strict)
    except Exception as exc:  # keep CLI diagnostics concise for malformed benchmark files
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
