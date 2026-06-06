"""Raw benchmark data API endpoints — reads CSV files from data/raw/."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from flask import Blueprint, jsonify, request

RAW_DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
_NOT_FOUND_MSG = (
    "Benchmark data not found. "
    "The measured CSV files should be present under data/raw/; "
    "alternatively, query the Hyperledger Fabric ledger directly via the gateway."
)

raw_bp = Blueprint("raw", __name__, url_prefix="/api/raw")


def _csv_path(name: str) -> Path:
    return RAW_DATA_DIR / name


def _read_csv(name: str) -> list[dict] | None:
    path = _csv_path(name)
    if not path.exists():
        return None
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _not_found():
    return jsonify({"error": _NOT_FOUND_MSG}), 404


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


@raw_bp.get("/summary")
def raw_summary():
    txns = _read_csv("raw_sensor_transactions.csv")
    security = _read_csv("raw_security_attempts.csv")
    throughput = _read_csv("raw_throughput_samples.csv")
    latency = _read_csv("raw_latency_samples.csv")
    energy = _read_csv("raw_energy_samples.csv")
    uptime = _read_csv("raw_uptime_events.csv")

    if any(d is None for d in [txns, security, throughput, latency, energy]):
        return _not_found()

    hrbac_50 = [
        float(r["tps"]) for r in throughput
        if r["benchmark_type"] == "HRBAC" and r["concurrent_clients"] == "50"
    ]
    baseline_50 = [
        float(r["tps"]) for r in throughput
        if r["benchmark_type"] == "Baseline" and r["concurrent_clients"] == "50"
    ]
    write_latencies = [
        float(r["latency_ms"]) for r in latency if r.get("operation") == "WriteSensor"
    ]
    rbac_overheads = [
        float(r["rbac_overhead_ms"]) for r in latency
        if r.get("operation") == "WriteSensor" and r.get("rbac_overhead_ms")
    ]
    sc_energy = [float(r["energy_mj"]) for r in energy if r["mode"] == "SingleChannel"]
    crt_energy = [float(r["energy_mj"]) for r in energy if r["mode"] == "CRT"]
    mean_sc = _mean(sc_energy) or 0.0
    mean_crt = _mean(crt_energy) or 0.0
    energy_reduction = round((mean_sc - mean_crt) / mean_sc * 100, 1) if mean_sc else 0

    uptime_pct = None
    if uptime:
        total_deployment = sum(
            float(r["duration_hours"]) for r in uptime
            if r.get("event_type") == "DEPLOYMENT"
        )
        total_outage = sum(
            float(r["duration_hours"]) for r in uptime
            if "OUTAGE" in r.get("event_type", "")
        )
        if total_deployment:
            uptime_pct = round(
                (total_deployment - total_outage) / total_deployment * 100, 1
            )

    mean_hrbac = _mean(hrbac_50)
    mean_baseline = _mean(baseline_50)
    mean_latency = _mean(write_latencies)
    mean_overhead = _mean(rbac_overheads)

    return jsonify({
        "sensor_transaction_count": len(txns),
        "security_attempt_count": len(security),
        "mean_hrbac_tps_50_clients": round(mean_hrbac, 2) if mean_hrbac is not None else None,
        "mean_baseline_tps_50_clients": round(mean_baseline, 2) if mean_baseline is not None else None,
        "mean_sensor_write_latency_ms": round(mean_latency, 1) if mean_latency is not None else None,
        "mean_rbac_overhead_ms": round(mean_overhead, 1) if mean_overhead is not None else None,
        "energy_reduction_percent": energy_reduction,
        "uptime_percent": uptime_pct,
    })


@raw_bp.get("/throughput")
def raw_throughput():
    rows = _read_csv("raw_throughput_samples.csv")
    if rows is None:
        return _not_found()
    data = [
        {
            "concurrent_clients": int(r["concurrent_clients"]),
            "benchmark_type": r["benchmark_type"],
            "tps": float(r["tps"]),
        }
        for r in rows
    ]
    return jsonify({"rows": data, "count": len(data)})


@raw_bp.get("/latency")
def raw_latency():
    rows = _read_csv("raw_latency_samples.csv")
    if rows is None:
        return _not_found()
    data = [
        {
            "operation": r["operation"],
            "latency_ms": float(r["latency_ms"]),
            "rbac_overhead_ms": float(r["rbac_overhead_ms"]) if r.get("rbac_overhead_ms") else None,
            "peer_count": int(r["peer_count"]) if r.get("peer_count") else None,
            "concurrent_clients": int(r["concurrent_clients"]) if r.get("concurrent_clients") else None,
        }
        for r in rows
    ]
    return jsonify({"rows": data, "count": len(data)})


@raw_bp.get("/energy")
def raw_energy():
    rows = _read_csv("raw_energy_samples.csv")
    if rows is None:
        return _not_found()
    data = [
        {
            "sample_id": r["sample_id"],
            "mode": r["mode"],
            "energy_mj": float(r["energy_mj"]),
            "payload_bytes": int(r["payload_bytes"]) if r.get("payload_bytes") else None,
            "airtime_ms": float(r["airtime_ms"]) if r.get("airtime_ms") else None,
        }
        for r in rows
    ]
    return jsonify({"rows": data, "count": len(data)})


@raw_bp.get("/security")
def raw_security():
    rows = _read_csv("raw_security_attempts.csv")
    if rows is None:
        return _not_found()

    scenario_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        scenario_counts[r["scenario"]] += 1

    scenarios = [
        {"scenario": scenario, "blocked_attempts": count}
        for scenario, count in sorted(scenario_counts.items())
    ]
    return jsonify({"scenarios": scenarios, "total_attempts": len(rows)})


@raw_bp.get("/sensor-transactions")
def raw_sensor_transactions():
    path = _csv_path("raw_sensor_transactions.csv")
    if not path.exists():
        return _not_found()

    limit = min(int(request.args.get("limit", 100)), 1000)
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader):
            if i >= limit:
                break
            rows.append({
                "timestamp": r["timestamp"],
                "tx_id": r["tx_id"],
                "sensor_id": r["sensor_id"],
                "zone": r["zone"],
                "operation": r["operation"],
                "decision": r["decision"],
                "latency_ms": float(r["latency_ms"]),
                "energy_mj": float(r["energy_mj"]),
            })
    return jsonify({"rows": rows, "count": len(rows), "limit": limit})
