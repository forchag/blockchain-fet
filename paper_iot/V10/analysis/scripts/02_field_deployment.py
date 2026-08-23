#!/usr/bin/env python3
"""Phase 3/4/13: field-deployment counts, latency-by-class, energy/availability
inputs drawn directly from the 61-day field trace (raw/field/*.csv).

This script only touches field observations: authorization_decisions.csv,
sensor_transactions.csv, raw_field_topology.csv, connectivity_outages.csv,
revocation_denials.csv. Controlled-experiment and scripted-test data are
analyzed in separate scripts (03, 04, 06, 07, 08) and must never be blended
with these field counts.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import FIELD_DIR, OUTPUTS_DIR, write_json

AD = pd.read_csv(FIELD_DIR / "authorization_decisions.csv", parse_dates=["timestamp"])
ST = pd.read_csv(FIELD_DIR / "sensor_transactions.csv", parse_dates=["timestamp"])
TOPO = pd.read_csv(FIELD_DIR / "raw_field_topology.csv")
OUT = pd.read_csv(FIELD_DIR / "connectivity_outages.csv", parse_dates=["start_time", "end_time"])
REVDENY = pd.read_csv(FIELD_DIR / "revocation_denials.csv", parse_dates=["timestamp"])


def deployment_summary() -> dict:
    span_days = (AD["timestamp"].max() - AD["timestamp"].min()).days + 1
    zones = sorted(TOPO["zone"].unique().tolist())
    gateways = sorted(TOPO["gateway_id"].unique().tolist())
    return {
        "authorization_decisions": int(len(AD)),
        "sensor_readings": int(len(ST)),
        "sensors": int(TOPO["sensor_id"].nunique()),
        "gateways": int(TOPO["gateway_id"].nunique()),
        "zones": len(zones),
        "zone_names": zones,
        "gateway_names": gateways,
        "deployment_start": str(AD["timestamp"].min()),
        "deployment_end": str(AD["timestamp"].max()),
        "deployment_span_days": int(span_days),
        "sensor_writes_per_day_mean": float(len(ST) / span_days),
        "decision_count_by_decision": AD["decision"].value_counts().to_dict(),
        "ordinary_denials": int((AD["decision"] == "denied").sum()),
        "ordinary_denial_rate_pct": float((AD["decision"] == "denied").mean() * 100),
        "decision_by_caller_role": AD["caller_role"].value_counts().to_dict(),
        "decision_by_operation": AD["operation"].value_counts().to_dict(),
        "sensors_per_zone": TOPO.groupby("zone")["sensor_id"].nunique().to_dict(),
    }


def latency_by_class() -> dict:
    checkaccess = AD[AD["operation"] != "WriteSensor"]
    write = ST  # every sensor write is a WriteSensor authorization decision
    def stats(s: pd.Series) -> dict:
        return {
            "n": int(s.count()),
            "mean_ms": float(s.mean()),
            "sd_ms": float(s.std(ddof=1)),
            "p95_ms": float(s.quantile(0.95)),
            "p99_ms": float(s.quantile(0.99)),
        }
    role_op = AD.groupby(["caller_role", "operation"])["decision"].apply(
        lambda s: (s == "allowed").mean() * 100
    )
    grant_rates = role_op.to_dict()
    grant_rate_values = list(role_op.values)
    return {
        "checkaccess_nonwrite": stats(checkaccess["latency_ms"]),
        "sensor_write": stats(write["latency_ms"]),
        "gap_ms": float(write["latency_ms"].mean() - checkaccess["latency_ms"].mean()),
        "role_operation_cells": int(len(role_op)),
        "grant_rate_min_pct": float(min(grant_rate_values)) if grant_rate_values else None,
        "grant_rate_max_pct": float(max(grant_rate_values)) if grant_rate_values else None,
        "grant_rate_by_cell_pct": {f"{k[0]}|{k[1]}": float(v) for k, v in role_op.items()},
    }


def availability() -> dict:
    start = AD["timestamp"].min()
    end = AD["timestamp"].max()
    total_hours = (end - start).total_seconds() / 3600.0
    outage_hours = OUT["duration_hours"].sum()
    n_gateways = TOPO["gateway_id"].nunique()
    decision_path_uptime = 1 - (outage_hours / total_hours)
    gateway_hours_total = total_hours * n_gateways
    gateway_hour_uptime = 1 - (outage_hours / gateway_hours_total)
    writes_by_day = ST.set_index("timestamp").resample("1D").size()
    return {
        "total_deployment_hours": float(total_hours),
        "outage_count": int(len(OUT)),
        "outage_durations_hours": OUT["duration_hours"].tolist(),
        "outage_total_hours": float(outage_hours),
        "outage_min_hours": float(OUT["duration_hours"].min()),
        "outage_max_hours": float(OUT["duration_hours"].max()),
        "outage_types": OUT["event_type"].tolist(),
        "outage_affected_components": OUT["affected_component"].tolist(),
        "decision_path_uptime_pct": float(decision_path_uptime * 100),
        "gateway_hour_uptime_pct": float(gateway_hour_uptime * 100),
        "sensor_writes_per_day_min": int(writes_by_day.min()),
        "sensor_writes_per_day_max": int(writes_by_day.max()),
        "sensor_writes_per_day_constant": bool(writes_by_day.min() == writes_by_day.max()),
        "days_observed": int(len(writes_by_day)),
    }


def field_revocation_denials() -> dict:
    span_days = (REVDENY["timestamp"].max() - REVDENY["timestamp"].min()).days + 1
    return {
        "field_revocation_denial_count": int(len(REVDENY)),
        "per_day_mean": float(len(REVDENY) / span_days),
        "deny_reason_counts": REVDENY["deny_reason"].value_counts().to_dict(),
        "span_days": int(span_days),
        "unique_callers": int(REVDENY["caller_id"].nunique()),
    }


def crt_field_summary() -> dict:
    """Descriptive counts of the crt_residues_received and signature_valid
    columns as recorded in the field trace; the bound analysis itself is in
    05_crt_quantization.py."""
    return {
        "crt_residues_received_counts": {str(k): int(v) for k, v in ST["crt_residues_received"].value_counts().items()},
        "signature_valid_counts": {str(k): int(v) for k, v in ST["signature_valid"].value_counts().items()},
        "signature_valid_pct": float((ST["signature_valid"] == True).mean() * 100),
        "soil_moisture_min": float(ST["soil_moisture"].min()),
        "soil_moisture_max": float(ST["soil_moisture"].max()),
        "temp_c_min": float(ST["temp_c"].min()),
        "temp_c_max": float(ST["temp_c"].max()),
    }


def main() -> None:
    write_json(OUTPUTS_DIR / "02_deployment_summary.json", deployment_summary())
    write_json(OUTPUTS_DIR / "02_latency_by_class.json", latency_by_class())
    write_json(OUTPUTS_DIR / "02_availability.json", availability())
    write_json(OUTPUTS_DIR / "02_field_revocation_denials.json", field_revocation_denials())
    write_json(OUTPUTS_DIR / "02_crt_field_summary.json", crt_field_summary())


if __name__ == "__main__":
    main()
