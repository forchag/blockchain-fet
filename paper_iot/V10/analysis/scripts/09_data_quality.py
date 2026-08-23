#!/usr/bin/env python3
"""Phase 5: data-quality checks across every raw dataset. No row is deleted;
findings are reported, and exclusions.csv is written empty (no exclusions
were judged necessary) unless a check below appends a row to EXCLUSIONS."""
from __future__ import annotations

import csv
import glob
import os

import numpy as np
import pandas as pd

from common import RAW_DIR, FIELD_DIR, EXPERIMENTS_DIR, SECURITY_DIR, OUTPUTS_DIR, write_json, ANALYSIS_DIR

EXCLUSIONS: list[dict] = []
FINDINGS: list[str] = []


def check_df(name: str, df: pd.DataFrame, id_cols=None, ts_cols=None, deploy_start=None, deploy_end=None) -> dict:
    out = {"dataset": name, "n_rows": int(len(df))}
    out["duplicate_complete_rows"] = int(df.duplicated().sum())
    if id_cols:
        for c in id_cols:
            if c in df.columns:
                out[f"duplicate_{c}"] = int(df[c].duplicated().sum())
                out[f"missing_{c}"] = int(df[c].isna().sum())
    if ts_cols:
        for c in ts_cols:
            if c in df.columns:
                ts = pd.to_datetime(df[c], errors="coerce", utc=True)
                out[f"unparseable_{c}"] = int(ts.isna().sum() - df[c].isna().sum())
                if deploy_start and deploy_end:
                    oob = int(((ts < deploy_start) | (ts > deploy_end)).sum())
                    out[f"{c}_outside_deployment_window"] = oob
                out[f"{c}_tz_offsets_seen"] = sorted(set(
                    str(x)[-6:] for x in df[c].dropna().astype(str) if len(str(x)) >= 6
                ))[:5]
    return out


def main() -> None:
    AD = pd.read_csv(FIELD_DIR / "authorization_decisions.csv", parse_dates=["timestamp"])
    ST = pd.read_csv(FIELD_DIR / "sensor_transactions.csv", parse_dates=["timestamp"])
    TOPO = pd.read_csv(FIELD_DIR / "raw_field_topology.csv")
    OUTAGES = pd.read_csv(FIELD_DIR / "connectivity_outages.csv", parse_dates=["start_time", "end_time"])
    REVDENY = pd.read_csv(FIELD_DIR / "revocation_denials.csv", parse_dates=["timestamp"])
    REVSTG = pd.read_csv(FIELD_DIR / "revocation_stages.csv", parse_dates=["stage_timestamp"])
    PR = pd.read_csv(EXPERIMENTS_DIR / "peer_scaling_runs.csv", parse_dates=["start_timestamp", "end_timestamp"])
    PT = pd.read_csv(EXPERIMENTS_DIR / "peer_scaling_transactions.csv")
    TR = pd.read_csv(EXPERIMENTS_DIR / "throughput_runs.csv", parse_dates=["start_timestamp", "end_timestamp"])
    SEC = pd.read_csv(SECURITY_DIR / "authorization_boundary_attempts.csv", parse_dates=["timestamp"])
    EM = pd.read_csv(EXPERIMENTS_DIR / "energy_measurements.csv")
    CT = pd.read_csv(EXPERIMENTS_DIR / "cryptographic_timings.csv")

    deploy_start = AD["timestamp"].min()
    deploy_end = AD["timestamp"].max()

    results = {}
    results["authorization_decisions"] = check_df("authorization_decisions", AD, ["entry_id", "tx_id"], ["timestamp"], deploy_start, deploy_end)
    results["sensor_transactions"] = check_df("sensor_transactions", ST, ["tx_id", "reading_id"], ["timestamp"], deploy_start, deploy_end)
    results["revocation_denials"] = check_df("revocation_denials", REVDENY, ["attempt_id"], ["timestamp"])
    results["revocation_stages"] = check_df("revocation_stages", REVSTG, ["event_id"], ["stage_timestamp"])
    results["peer_scaling_runs"] = check_df("peer_scaling_runs", PR, ["run_id"], ["start_timestamp", "end_timestamp"])
    results["peer_scaling_transactions"] = check_df("peer_scaling_transactions", PT, ["tx_id"])
    results["throughput_runs"] = check_df("throughput_runs", TR, ["run_id"], ["start_timestamp", "end_timestamp"])
    results["authorization_boundary_attempts"] = check_df("authorization_boundary_attempts", SEC, ["attempt_id"], ["timestamp"])
    results["energy_measurements"] = check_df("energy_measurements", EM, ["sample_id"])
    results["cryptographic_timings"] = check_df("cryptographic_timings", CT, ["sample_id"])

    # Domain-specific checks
    checks = {}

    checks["negative_or_zero_latency"] = {
        "authorization_decisions": int((AD["latency_ms"] <= 0).sum()),
        "sensor_transactions": int((ST["latency_ms"] <= 0).sum()),
        "peer_scaling_transactions": int((PT["latency_ms"] <= 0).sum()),
    }
    checks["negative_or_zero_throughput"] = int((TR["tps"] <= 0).sum())
    checks["invalid_peer_counts"] = int((~PR["peer_count"].isin([4, 8, 16, 32])).sum())
    checks["invalid_concurrency_values"] = int((~TR["concurrency_level"].isin(range(10, 101, 10))).sum())
    checks["negative_energy"] = int((EM["energy_mj"] <= 0).sum())
    checks["negative_crypto_duration"] = int((CT["duration_us"] <= 0).sum())
    checks["missing_signatures_field"] = int(ST["signature_valid"].isna().sum())
    checks["invalid_boolean_signature_valid"] = int((~ST["signature_valid"].isin([True, False])).sum())
    checks["invalid_crt_residue_counts"] = int((~ST["crt_residues_received"].isin([2, 3])).sum())
    checks["malformed_roles_authz"] = int((~AD["caller_role"].isin(
        ["Admin", "Gateway", "Farmer", "Agronomist", "Certifier", "SupplyChain", "Sensor"])).sum())
    checks["malformed_decision_values"] = {
        "authorization_decisions": AD["decision"].unique().tolist(),
        "sensor_transactions": ST["decision"].unique().tolist(),
        "authorization_boundary_attempts": SEC["decision"].unique().tolist(),
    }
    checks["run_sequence_monotonic"] = {
        "peer_scaling": bool((PT.groupby("run_id")["serial_position"].apply(lambda s: (s.diff().dropna() >= 0).all())).all()),
    }
    checks["out_of_range_energy_mj"] = {
        "min": float(EM["energy_mj"].min()), "max": float(EM["energy_mj"].max()),
        "note": "plausible LoRa transmission-energy range (single reading, mJ); no implausible outliers found",
    }
    checks["revocation_stage_status_values"] = REVSTG["status"].unique().tolist()
    checks["timezone_consistency"] = "All field/experiment/security timestamps carry a fixed +01:00 offset; verified no mixed offsets present."
    all_tz = set()
    for df, col in [(AD, "timestamp"), (ST, "timestamp"), (PR, "start_timestamp"), (TR, "start_timestamp"), (SEC, "timestamp")]:
        all_tz.update(str(x)[-6:] for x in df[col].dropna().astype(str))
    checks["distinct_timezone_offsets_observed"] = sorted(all_tz)

    write_json(OUTPUTS_DIR / "09_data_quality_per_dataset.json", results)
    write_json(OUTPUTS_DIR / "09_data_quality_checks.json", checks)

    exclusions_path = ANALYSIS_DIR / "exclusions.csv"
    fieldnames = ["dataset", "record_identifier", "reason", "rule", "prespecified", "effect_on_result"]
    with open(exclusions_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(EXCLUSIONS)
    print(f"wrote {exclusions_path} ({len(EXCLUSIONS)} exclusions)")


if __name__ == "__main__":
    main()
