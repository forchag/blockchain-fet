#!/usr/bin/env python3
"""Phase 3/4: build CLAIM_DATA_MAP.csv, verified_dataset_counts.json and
dataset_count_validation.csv by comparing V9.2's reported values (transcribed
once into v92_reported_values.json, used only for comparison) against the
values this pipeline computed from the analyst's real data."""
from __future__ import annotations

import csv
import json

from common import ANALYSIS_DIR, OUTPUTS_DIR, merge_outputs, write_json, load_json

V92 = load_json(ANALYSIS_DIR / "v92_reported_values.json")
OUT = merge_outputs()


def g(*path):
    """Dig into the merged outputs dict by dotted path; returns None if missing."""
    cur = OUT
    for p in path:
        if cur is None:
            return None
        cur = cur.get(p) if isinstance(cur, dict) else None
    return cur


# Each row: claim_id, section, claim text, dataset, script, v10 value getter (lambda), v9.2 key
ROWS = [
    ("C01", "5.1/Table2", "61-day deployment", "authorization_decisions.csv", "02_field_deployment.py",
     lambda: g("02_deployment_summary", "deployment_span_days"), "deployment_days"),
    ("C02", "5.1/Table2", "50 sensors", "raw_field_topology.csv", "02_field_deployment.py",
     lambda: g("02_deployment_summary", "sensors"), "sensors"),
    ("C03", "5.1/Table2", "4 gateways", "raw_field_topology.csv", "02_field_deployment.py",
     lambda: g("02_deployment_summary", "gateways"), "gateways"),
    ("C04", "5.1/Table2", "4 zones", "raw_field_topology.csv", "02_field_deployment.py",
     lambda: g("02_deployment_summary", "zones"), "zones"),
    ("C05", "1/5.1", "209,000 authorization decisions", "authorization_decisions.csv", "02_field_deployment.py",
     lambda: g("02_deployment_summary", "authorization_decisions"), "authorization_decisions"),
    ("C06", "5.1", "146,400 sensor readings", "sensor_transactions.csv", "02_field_deployment.py",
     lambda: g("02_deployment_summary", "sensor_readings"), "sensor_readings"),
    ("C07", "5.1", "4,860 (2.33%) ordinary denials", "authorization_decisions.csv", "02_field_deployment.py",
     lambda: g("02_deployment_summary", "ordinary_denials"), "ordinary_denials"),
    ("C08", "6.8", "decision-path uptime 99.36%", "connectivity_outages.csv", "02_field_deployment.py",
     lambda: g("02_availability", "decision_path_uptime_pct"), "decision_path_uptime_pct"),
    ("C09", "6.8", "gateway-hour uptime 99.84%", "connectivity_outages.csv", "02_field_deployment.py",
     lambda: g("02_availability", "gateway_hour_uptime_pct"), "gateway_hour_uptime_pct"),
    ("C10", "6.8", "3 outages, 9.3 h total", "connectivity_outages.csv", "02_field_deployment.py",
     lambda: g("02_availability", "outage_total_hours"), "connectivity_outage_total_hours"),
    ("C11", "6.2", "CheckAccess mean 280 ms (SD 40)", "authorization_decisions.csv", "02_field_deployment.py",
     lambda: g("02_latency_by_class", "checkaccess_nonwrite", "mean_ms"), "checkaccess_mean_ms"),
    ("C12", "6.2", "sensor write mean 1220 ms (SD 60)", "sensor_transactions.csv", "02_field_deployment.py",
     lambda: g("02_latency_by_class", "sensor_write", "mean_ms"), "sensor_write_mean_ms"),
    ("C13", "6.2", "sensor write P95 1319 / P99 1359 ms", "sensor_transactions.csv", "02_field_deployment.py",
     lambda: g("02_latency_by_class", "sensor_write", "p95_ms"), "sensor_write_p95_ms"),
    ("C14", "6.2", "grant rate uniformly 91-93% across 35 cells", "authorization_decisions.csv", "02_field_deployment.py",
     lambda: g("02_latency_by_class", "grant_rate_min_pct"), "grant_rate_low_pct"),
    ("C15", "5.2/6.4", "32 peer-scaling runs, 8 per configuration", "peer_scaling_runs.csv", "03_peer_scaling.py",
     lambda: g("03_design_check", "n_runs"), "peer_scaling_runs_total"),
    ("C16", "5.2", "130 transactions per run", "peer_scaling_transactions.csv", "03_peer_scaling.py",
     lambda: g("03_design_check", "tx_per_run"), "peer_scaling_tx_per_run"),
    ("C17", "6.1.2", "two complementary 4x4 Latin-square cycles, each config each position exactly twice",
     "peer_scaling_runs.csv + peer_scaling_transactions.csv", "03_peer_scaling.py",
     lambda: g("03_design_check", "each_config_occupies_each_position_exactly_twice"), None),
    ("C18", "6.1/Table3", "total latency 4 peers 1204.8 ms", "peer_scaling_transactions.csv", "03_peer_scaling.py",
     lambda: g("03_peer_scaling_results", "total_latency", "group_stats", "4", "mean"), "total_latency_4peer_ms"),
    ("C19", "6.1/Table3", "total latency 32 peers 811.8 ms", "peer_scaling_transactions.csv", "03_peer_scaling.py",
     lambda: g("03_peer_scaling_results", "total_latency", "group_stats", "32", "mean"), "total_latency_32peer_ms"),
    ("C20", "6.4", "4 vs 32 peer total-latency diff 393.0 ms [374.5, 411.4]",
     "peer_scaling_transactions.csv", "03_peer_scaling.py",
     lambda: g("03_peer_scaling_results", "total_latency", "pairwise_4v32", "mean_diff_4_minus_32"),
     "total_latency_4v32_diff_ms"),
    ("C21", "6.1/Table3", "recorded span ~320ms, ~stable across peer counts", "peer_scaling_transactions.csv", "03_peer_scaling.py",
     lambda: g("03_peer_scaling_results", "recorded_span", "group_stats", "4", "mean"), "recorded_span_4peer_ms"),
    ("C22", "6.1.2", "span extreme diff 4.78 ms, 90% CI [-9.77, 0.22], within +-10ms margin",
     "peer_scaling_transactions.csv", "03_peer_scaling.py",
     lambda: g("03_peer_scaling_results", "recorded_span", "pairwise_4v32", "mean_diff_4_minus_32"),
     "span_extreme_diff_ms"),
    ("C23", "6.1.2", "span share 26.6% at 4 peers, 39.0% at 32 peers", "peer_scaling_transactions.csv", "03_peer_scaling.py",
     lambda: g("03_peer_scaling_results", "recorded_span_share_pct_by_peer_count", "32"), "recorded_span_share_pct_32peer"),
    ("C24", "6.4", "log-linear -127.1 ms/doubling, R2=0.893", "peer_scaling_transactions.csv", "03_peer_scaling.py",
     lambda: g("03_peer_scaling_results", "total_latency", "log_linear_fit", "slope_per_doubling"),
     "log_linear_slope_ms_per_doubling"),
    ("C25", "5.4", "sequence effect p=0.76(span)/0.48(total latency); peer-count p<0.001",
     "peer_scaling_transactions.csv", "03_peer_scaling.py",
     lambda: g("03_peer_scaling_results", "total_latency", "order_effect_model", "serial_c_p"),
     "sequence_effect_p_total_latency"),
    ("C26", "5.2/6.3", "100 throughput runs (10 levels x 2 conditions x 5)", "throughput_runs.csv", "04_throughput.py",
     lambda: g("04_throughput_design_check", "n_runs"), "throughput_runs_total"),
    ("C27", "6.3", "campaign_seq vs concurrency r=0.995 (single session, fixed ascending order)",
     "throughput_runs.csv", "04_throughput.py",
     lambda: g("04_throughput_design_check", "campaign_seq_vs_concurrency_correlation"), None),
    ("C28", "6.3", "condition diff 6.03 TPS [3.20, 8.87], p<0.001 (magnitude; HRBAC is the lower path)",
     "throughput_runs.csv", "04_throughput.py",
     lambda: abs(g("04_throughput_primary_model", "condition_coef_tps")), "throughput_condition_diff_tps"),
    ("C29", "6.3", "interaction magnitude 0.007 TPS/client [-0.091,0.104], p=0.89", "throughput_runs.csv", "04_throughput.py",
     lambda: abs(g("04_throughput_primary_model", "interaction_coef_tps_per_client")), "throughput_interaction_tps_per_client"),
    ("C30", "6.3", "position effect not detected p=0.92; model R2=0.206", "throughput_runs.csv", "04_throughput.py",
     lambda: g("04_throughput_primary_model", "position_p"), "throughput_position_p"),
    ("C31", "6.3", "mean 9.6% lower throughput (SD 1.6, range 7.9-12.4%)", "throughput_runs.csv", "04_throughput.py",
     lambda: g("04_throughput_per_level", "pct_diff_mean"), "throughput_pct_diff_mean"),
    ("C32", "6.3", "10/10 concurrency comparisons significant after Holm-Bonferroni",
     "throughput_runs.csv", "04_throughput.py",
     lambda: g("04_throughput_per_level", "holm_bonferroni", "n_significant_after_adjustment"), None),
    ("C33", "6.3", "shared observed peak 70.4 (baseline) / 63.5 (hrbac) TPS at 40 clients",
     "throughput_runs.csv", "04_throughput.py",
     lambda: g("04_throughput_peaks", "baseline_peak_tps"), "throughput_peak_baseline_tps"),
    ("C34", "6.3", "HRBAC declines 15.3% from peak to 100 clients", "throughput_runs.csv", "04_throughput.py",
     lambda: g("04_throughput_peaks", "hrbac_decline_pct_peak_to_100"), "throughput_decline_hrbac_pct_to_100"),
    ("C35", "6.9.2", "8,000 authorization-boundary attempts, 8 scenarios x 1000", "authorization_boundary_attempts.csv",
     "06_security_oracle.py", lambda: g("06_security_oracle", "total_attempts"), "security_attempts_total"),
    ("C36", "6.6", "6 recorded denial mechanisms", "authorization_boundary_attempts.csv", "06_security_oracle.py",
     lambda: g("06_security_oracle", "n_deny_reason_types"), "security_denial_mechanisms"),
    ("C37", "6.6", "2,666 attempts scored by role/operation oracle", "authorization_boundary_attempts.csv",
     "06_security_oracle.py", lambda: g("06_security_oracle", "role_operation_scoped_attempts"), "oracle_scored_attempts"),
    ("C38", "6.6", "2,149 confirmed (80.6%), 517 discrepant (19.4%)", "authorization_boundary_attempts.csv",
     "06_security_oracle.py", lambda: g("06_security_oracle", "confirmed_by_deployed_oracle"), "oracle_confirmed"),
    ("C39", "6.9.2", "131,795 two-residue reconstructions (90.0%), all mathematically incorrect",
     "sensor_transactions.csv", "05_crt_quantization.py",
     lambda: g("05_crt_quantization", "two_residue_reconstruction_count"), "crt_two_residue_count"),
    ("C40", "6.9.2", "100.0% of 146,400 readings exceed smallest recovery bound (9,797)", "sensor_transactions.csv",
     "05_crt_quantization.py", lambda: g("05_crt_quantization", "reconstruction_direct_polarity", "pct_exceed_min_bound"),
     "crt_exceed_pct"),
    ("C41", "6.9.2", "corrected legal-domain max 51,455, bound 64,262", "esp32/main/crt_encode.h (source code)",
     "05_crt_quantization.py", lambda: g("05_crt_quantization", "corrected_domain", "legal_domain_max"),
     "crt_corrected_legal_max"),
    ("C42", "6.9.2", "quantization max error 0.37% (RMS 0.21%)", "derived from esp32/main/main.c encoding",
     "05_crt_quantization.py", lambda: g("05_crt_quantization", "quantization_error", "truncating_quantiser", "max_error_pct_full_scale"),
     "quantization_max_error_pct"),
    ("C43", "6.9.3", "signature-validity field 100.0%", "sensor_transactions.csv", "02_field_deployment.py",
     lambda: g("02_crt_field_summary", "signature_valid_pct"), "signature_validity_pct"),
    ("C44", "6.5", "200 revocation stage records over 58 days", "revocation_stages.csv", "07_revocation.py",
     lambda: g("07_revocation_results", "n_stage_records"), "revocation_stage_records"),
    ("C45", "6.5", "59 of 200 (29.5%) stages delayed", "revocation_stages.csv", "07_revocation.py",
     lambda: g("07_revocation_results", "delayed_count"), "delayed_stage_count"),
    ("C46", "6.9.4", "132 subjects, 0 with all 4 stages, 87 appear once", "revocation_stages.csv", "07_revocation.py",
     lambda: g("07_revocation_results", "n_subjects"), "revocation_subjects"),
    ("C47", "6.5", "973 field revocation denials, 16.0/day", "revocation_denials.csv", "07_revocation.py",
     lambda: g("07_revocation_results", "field_revocation_denials", "count"), "field_revocation_denials"),
    ("C48", "6.7", "energy reduction 48.7% [48.6,48.8]; 24.20 -> 12.41 mJ", "energy_measurements.csv", "08_energy_crypto.py",
     lambda: g("08_energy_results", "reduction_pct"), "energy_reduction_pct"),
    ("C49", "6.7", "signing pipeline ~900 us", "cryptographic_timings.csv", "08_energy_crypto.py",
     lambda: g("08_crypto_timing_results", "sign_pipeline_us_sha256_plus_sign"), "signing_pipeline_us"),
    ("C50", "5.6", "377,414 rows across 10 traces", "all raw/*.csv", "01_extract_and_inventory.py",
     lambda: _total_csv_rows(), "released_rows_total"),
]


def _total_csv_rows() -> int:
    import csv as _csv
    total = 0
    with open(ANALYSIS_DIR / "analyst_data_inventory.csv", newline="") as f:
        for row in _csv.DictReader(f):
            if row["file_format"] == "csv" and row["row_count"]:
                total += int(row["row_count"])
    return total


def pct_diff(v10, v92):
    if v10 is None or v92 is None:
        return None
    try:
        v10 = float(v10)
        v92 = float(v92)
    except (TypeError, ValueError):
        return None
    if v92 == 0:
        return None
    return (v10 - v92) / abs(v92) * 100


def classify(v10, v92, pct):
    if v10 is None:
        return "missing_in_v10"
    if v92 is None:
        return "no_v92_comparator"
    if isinstance(v10, bool):
        return "confirmed_by_manifest" if v10 else "not_confirmed_by_manifest"
    if pct is None:
        return "not_comparable"
    if abs(pct) < 0.5:
        return "reproduced_exact"
    if abs(pct) < 5:
        return "reproduced_within_rounding"
    return "differs_materially"


def main() -> None:
    rows_out = []
    for claim_id, section, claim, dataset, script, getter, v92_key in ROWS:
        try:
            v10_val = getter()
        except Exception as exc:
            v10_val = None
        v92_val = V92.get(v92_key) if v92_key else None
        pct = pct_diff(v10_val, v92_val) if not isinstance(v10_val, bool) else None
        status = classify(v10_val, v92_val, pct)
        action = {
            "reproduced_exact": "retain (matches within rounding)",
            "reproduced_within_rounding": "update to verified V10 value (small, explainable difference)",
            "differs_materially": "replace with verified V10 value; document in changelog",
            "confirmed_by_manifest": "retain; design claim verified against real run manifest",
            "not_comparable": "report V10 value; no direct V9.2 numeric comparator",
            "no_v92_comparator": "report V10 value; no direct V9.2 numeric comparator",
            "missing_in_v10": "investigate: analysis pipeline did not produce a value",
        }[status]
        rows_out.append({
            "claim_id": claim_id, "V9.2_section": section, "V9.2_claim": claim,
            "required_dataset": dataset, "available_dataset": dataset if v10_val is not None else "MISSING",
            "raw_or_summary": "raw", "analysis_script": script,
            "reproduced_value": v10_val, "V9.2_value": v92_val,
            "difference_pct": round(pct, 3) if pct is not None else "",
            "V10_action": action, "status": status,
        })

    csv_path = ANALYSIS_DIR / "CLAIM_DATA_MAP.csv"
    fieldnames = list(rows_out[0].keys())
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_out)
    print(f"wrote {csv_path} ({len(rows_out)} claims)")

    # verified_dataset_counts.json / dataset_count_validation.csv (Phase 4)
    expected_vs_real = [
        ("61-day deployment", 61, g("02_deployment_summary", "deployment_span_days")),
        ("209,000 authorization decisions", 209000, g("02_deployment_summary", "authorization_decisions")),
        ("146,400 sensor readings", 146400, g("02_deployment_summary", "sensor_readings")),
        ("32 peer-multiplicity runs", 32, g("03_design_check", "n_runs")),
        ("8 runs per peer configuration", 8, g("03_design_check", "runs_per_peer_count", "4")),
        ("100 throughput runs (10x2x5)", 100, g("04_throughput_design_check", "n_runs")),
        ("8,000 authorization-boundary attempts", 8000, g("06_security_oracle", "total_attempts")),
        ("200 revocation-stage records", 200, g("07_revocation_results", "n_stage_records")),
        ("973 field revocation denials", 973, g("07_revocation_results", "field_revocation_denials", "count")),
        ("3 gateway outages", 3, g("02_availability", "outage_count")),
    ]
    verified = {}
    validation_rows = []
    for label, expected, real in expected_vs_real:
        match = (expected == real)
        verified[label] = {"expected": expected, "verified_real": real, "match": match}
        validation_rows.append({
            "claim": label, "v92_value": expected, "real_data_value": real,
            "difference": (real - expected) if isinstance(real, (int, float)) else "",
            "likely_explanation": "exact match" if match else "see DATA_DISCREPANCIES.md",
            "manuscript_correction_required": not match,
        })
    write_json(ANALYSIS_DIR / "verified_dataset_counts.json", verified)
    with open(ANALYSIS_DIR / "dataset_count_validation.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(validation_rows[0].keys()))
        w.writeheader()
        w.writerows(validation_rows)
    print("wrote verified_dataset_counts.json and dataset_count_validation.csv")


if __name__ == "__main__":
    main()
