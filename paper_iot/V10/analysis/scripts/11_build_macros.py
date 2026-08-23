#!/usr/bin/env python3
"""Build manuscript/macros.tex: every numerical result quoted in the V10
manuscript is a \\newcommand defined here from the analysis outputs. The
manuscript sources never contain a hand-typed statistical result -- they
\\input this file and reference the macros."""
from __future__ import annotations

from common import V10_DIR, merge_outputs

OUT = merge_outputs()


def g(*path, default="?"):
    cur = OUT
    for p in path:
        if cur is None:
            return default
        cur = cur.get(p) if isinstance(cur, dict) else None
    return cur if cur is not None else default


def fmt(x, nd=1):
    if isinstance(x, str):
        return x
    try:
        return f"{x:,.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


def fmt_int(x):
    try:
        return f"{int(round(x)):,}"
    except (TypeError, ValueError):
        return str(x)


def fmt_pct(x, nd=1):
    return fmt(x, nd)


MACROS = []


def m(name, value):
    MACROS.append(f"\\newcommand{{\\{name}}}{{{value}}}")


# --- Field deployment ---
m("DeploymentDays", fmt_int(g("02_deployment_summary", "deployment_span_days")))
m("Sensors", fmt_int(g("02_deployment_summary", "sensors")))
m("Gateways", fmt_int(g("02_deployment_summary", "gateways")))
m("Zones", fmt_int(g("02_deployment_summary", "zones")))
m("AuthDecisions", fmt_int(g("02_deployment_summary", "authorization_decisions")))
m("SensorReadings", fmt_int(g("02_deployment_summary", "sensor_readings")))
m("OrdinaryDenials", fmt_int(g("02_deployment_summary", "ordinary_denials")))
m("OrdinaryDenialPct", fmt_pct(g("02_deployment_summary", "ordinary_denial_rate_pct"), 2))
m("DecisionPathUptime", fmt_pct(g("02_availability", "decision_path_uptime_pct"), 2))
m("GatewayHourUptime", fmt_pct(g("02_availability", "gateway_hour_uptime_pct"), 2))
m("OutageCount", fmt_int(g("02_availability", "outage_count")))
m("OutageTotalHours", fmt(g("02_availability", "outage_total_hours"), 1))
m("OutageMinHours", fmt(g("02_availability", "outage_min_hours"), 1))
m("OutageMaxHours", fmt(g("02_availability", "outage_max_hours"), 1))

m("CheckAccessMeanMs", fmt(g("02_latency_by_class", "checkaccess_nonwrite", "mean_ms"), 0))
m("CheckAccessSdMs", fmt(g("02_latency_by_class", "checkaccess_nonwrite", "sd_ms"), 0))
m("SensorWriteMeanMs", fmt(g("02_latency_by_class", "sensor_write", "mean_ms"), 0))
m("SensorWriteSdMs", fmt(g("02_latency_by_class", "sensor_write", "sd_ms"), 0))
m("SensorWritePNinetyFiveMs", fmt(g("02_latency_by_class", "sensor_write", "p95_ms"), 0))
m("SensorWritePNinetyNineMs", fmt(g("02_latency_by_class", "sensor_write", "p99_ms"), 0))
m("LatencyGapMs", fmt(g("02_latency_by_class", "gap_ms"), 0))
m("RoleOpCells", fmt_int(g("02_latency_by_class", "role_operation_cells")))
m("GrantRateMin", fmt_pct(g("02_latency_by_class", "grant_rate_min_pct"), 1))
m("GrantRateMax", fmt_pct(g("02_latency_by_class", "grant_rate_max_pct"), 1))

m("FieldRevocationDenials", fmt_int(g("07_revocation_results", "field_revocation_denials", "count")))
m("FieldRevocationPerDay", fmt(g("07_revocation_results", "field_revocation_denials", "per_day"), 1))

# --- Peer scaling ---
pk = "03_peer_scaling_results"
m("PeerRunsTotal", fmt_int(g("03_design_check", "n_runs")))
m("PeerRunsPerConfig", fmt_int(g("03_design_check", "runs_per_peer_count", "4")))
m("PeerTxPerRun", fmt_int(g("03_design_check", "tx_per_run")))
PEER_WORD = {4: "PeerFour", 8: "PeerEight", 16: "PeerSixteen", 32: "PeerThirtyTwo"}
for pc in [4, 8, 16, 32]:
    s = str(pc)
    w = PEER_WORD[pc]
    m(f"TotalLatency{w}", fmt(g(pk, "total_latency", "group_stats", s, "mean"), 1))
    m(f"SpanLatency{w}", fmt(g(pk, "recorded_span", "group_stats", s, "mean"), 1))
    m(f"RemainingLatency{w}", fmt(g(pk, "remaining_latency", "group_stats", s, "mean"), 1))
    m(f"PNinetyFiveLatency{w}", fmt(g(pk, "p95_latency", "group_stats", s, "mean"), 1))
    m(f"SpanShare{w}", fmt_pct(g(pk, "recorded_span_share_pct_by_peer_count", s), 1))

m("TotalLatencyDiffFourVThirtyTwo", fmt(g(pk, "total_latency", "pairwise_4v32", "mean_diff_4_minus_32"), 1))
m("TotalLatencyDiffFourVThirtyTwoCILow", fmt(g(pk, "total_latency", "pairwise_4v32", "ci95_low"), 1))
m("TotalLatencyDiffFourVThirtyTwoCIHigh", fmt(g(pk, "total_latency", "pairwise_4v32", "ci95_high"), 1))
m("RemainingLatencyDiffFourVThirtyTwo", fmt(g(pk, "remaining_latency", "pairwise_4v32", "mean_diff_4_minus_32"), 1))
m("SpanDiffFourVThirtyTwo", fmt(g(pk, "recorded_span", "pairwise_4v32", "mean_diff_4_minus_32"), 2))
m("SpanDiffFourVThirtyTwoCINinetyLow", fmt(g(pk, "recorded_span", "pairwise_4v32", "ci90_low"), 2))
m("SpanDiffFourVThirtyTwoCINinetyHigh", fmt(g(pk, "recorded_span", "pairwise_4v32", "ci90_high"), 2))
m("SpanDiffFourVThirtyTwoWelchT", fmt(g(pk, "recorded_span", "pairwise_4v32", "paired_t"), 2))
_span_p = g(pk, "recorded_span", "pairwise_4v32", "paired_p")
m("SpanDiffFourVThirtyTwoP", "$<$0.001" if isinstance(_span_p, float) and _span_p < 0.001 else fmt(_span_p, 4))
_tost_p = g(pk, "recorded_span", "pairwise_4v32", "tost_p")
m("SpanTostP", "$<$0.001" if isinstance(_tost_p, float) and _tost_p < 0.001 else fmt(_tost_p, 4))
m("PNinetyFiveDiffFourVThirtyTwo", fmt(g(pk, "p95_latency", "pairwise_4v32", "mean_diff_4_minus_32"), 1))

m("LogLinearSlope", fmt(g(pk, "total_latency", "log_linear_fit", "slope_per_doubling"), 1))
m("LogLinearRSquared", fmt(g(pk, "total_latency", "log_linear_fit", "r2"), 3))
m("LogLinearP", fmt(g(pk, "total_latency", "log_linear_fit", "p"), 3))
m("SpanTrendSlope", fmt(g(pk, "recorded_span", "log_linear_fit", "slope_per_doubling"), 2))
m("SpanTrendP", fmt(g(pk, "recorded_span", "log_linear_fit", "p"), 3))
m("SpanTrendRSquared", fmt(g(pk, "recorded_span", "log_linear_fit", "r2"), 3))

m("SeqEffectPSpanNFour", fmt(g(pk, "recorded_span", "order_effect_model", "serial_c_p"), 3))
m("SeqEffectPTotalNThirtyTwo", fmt(g(pk, "total_latency", "order_effect_model", "serial_c_p"), 3))
m("PeerEffectPTotalLatency", "$<$0.001" if g(pk, "total_latency", "block_design_model", "peer_count_p") not in ("?", None) and g(pk, "total_latency", "block_design_model", "peer_count_p") < 0.001 else fmt(g(pk, "total_latency", "block_design_model", "peer_count_p"), 4))
m("BlockEffectPTotalLatency", fmt(g(pk, "total_latency", "block_design_model", "block_p"), 3))
m("SpanLogTwoPeersJointP", fmt(g(pk, "recorded_span", "order_effect_model", "log2_peers_p"), 4))

# --- Throughput ---
tk_prim = "04_throughput_primary_model"
m("ThroughputRunsTotal", fmt_int(g("04_throughput_design_check", "n_runs")))
m("ThroughputConditionDiff", fmt(abs(float(g(tk_prim, "condition_coef_tps"))), 2))
m("ThroughputConditionCILow", fmt(abs(float(g(tk_prim, "condition_ci_high"))), 2))
m("ThroughputConditionCIHigh", fmt(abs(float(g(tk_prim, "condition_ci_low"))), 2))
m("ThroughputConditionP", "$<$0.001" if g(tk_prim, "condition_p") not in ("?", None) and g(tk_prim, "condition_p") < 0.001 else fmt(g(tk_prim, "condition_p"), 4))
m("ThroughputInteractionCoef", fmt(g(tk_prim, "interaction_coef_tps_per_client"), 4))
m("ThroughputInteractionP", fmt(g(tk_prim, "interaction_p"), 2))
m("ThroughputPositionP", fmt(g(tk_prim, "position_p"), 2))
m("ThroughputModelRSquared", fmt(g(tk_prim, "r2"), 3))
m("ThroughputPctDiffMean", fmt_pct(g("04_throughput_per_level", "pct_diff_mean"), 1))
m("ThroughputPctDiffSd", fmt(g("04_throughput_per_level", "pct_diff_sd"), 1))
m("ThroughputPctDiffMin", fmt_pct(g("04_throughput_per_level", "pct_diff_min"), 1))
m("ThroughputPctDiffMax", fmt_pct(g("04_throughput_per_level", "pct_diff_max"), 1))
m("ThroughputSigAfterHolm", fmt_int(g("04_throughput_per_level", "holm_bonferroni", "n_significant_after_adjustment")))
m("ThroughputBaselinePeak", fmt(g("04_throughput_peaks", "baseline_peak_tps"), 1))
m("ThroughputHrbacPeak", fmt(g("04_throughput_peaks", "hrbac_peak_tps"), 1))
m("ThroughputPeakLevel", fmt_int(g("04_throughput_peaks", "baseline_peak_level")))
m("ThroughputHrbacDeclinePct", fmt_pct(g("04_throughput_peaks", "hrbac_decline_pct_peak_to_100"), 1))
m("ThroughputCampaignSeqCorr", fmt(g("04_throughput_design_check", "campaign_seq_vs_concurrency_correlation"), 3))

# --- Security / oracle ---
m("SecurityAttemptsTotal", fmt_int(g("06_security_oracle", "total_attempts")))
m("SecurityDenialMechanisms", fmt_int(g("06_security_oracle", "n_deny_reason_types")))
m("OracleScoredAttempts", fmt_int(g("06_security_oracle", "role_operation_scoped_attempts")))
m("OracleConfirmed", fmt_int(g("06_security_oracle", "confirmed_by_deployed_oracle")))
m("OracleConfirmedPct", fmt_pct(g("06_security_oracle", "confirmed_pct_of_scoped"), 1))
m("OracleDiscrepant", fmt_int(g("06_security_oracle", "discrepant_vs_deployed_oracle")))
m("OracleDiscrepantPct", fmt_pct(g("06_security_oracle", "discrepant_pct_of_scoped"), 1))

# --- CRT / quantization ---
m("CrtModuli", "97, 101, 103")
m("CrtMinBound", fmt_int(g("05_crt_quantization", "deployed_pairwise_bounds", "min")))
m("CrtExceedPct", fmt_pct(g("05_crt_quantization", "reconstruction_direct_polarity", "pct_exceed_min_bound"), 4))
m("CrtTwoResidueCount", fmt_int(g("05_crt_quantization", "two_residue_reconstruction_count")))
m("CrtTwoResiduePct", fmt_pct(g("05_crt_quantization", "two_residue_reconstruction_pct"), 1))
m("CrtCorrectedModuli", "253, 254, 255")
m("CrtCorrectedBound", fmt_int(g("05_crt_quantization", "corrected_domain", "pairwise_bounds", "min")))
m("CrtCorrectedLegalMax", fmt_int(g("05_crt_quantization", "corrected_domain", "legal_domain_max")))
m("QuantMaxErrorPct", fmt_pct(g("05_crt_quantization", "quantization_error", "truncating_quantiser", "max_error_pct_full_scale"), 2))
m("QuantRmsErrorPct", fmt_pct(g("05_crt_quantization", "quantization_error", "truncating_quantiser", "rms_error_pct_full_scale"), 2))
m("SignatureValidPct", fmt_pct(g("02_crt_field_summary", "signature_valid_pct"), 1))

# --- Revocation ---
m("RevocationStageRecords", fmt_int(g("07_revocation_results", "n_stage_records")))
m("RevocationTraceSpanDays", fmt_int(g("07_revocation_results", "trace_span_days")))
m("RevocationDelayedCount", fmt_int(g("07_revocation_results", "delayed_count")))
m("RevocationDelayedPct", fmt_pct(g("07_revocation_results", "delayed_pct"), 1))
m("RevocationSubjects", fmt_int(g("07_revocation_results", "n_subjects")))
m("RevocationSubjectsAllStages", fmt_int(g("07_revocation_results", "n_subjects_with_all_stage_types")))
m("RevocationSubjectsOnce", fmt_int(g("07_revocation_results", "n_subjects_appearing_once")))

# --- Energy / crypto ---
m("EnergySingleChannelMj", fmt(g("08_energy_results", "single_channel", "mean_mj"), 2))
m("EnergyCrtMj", fmt(g("08_energy_results", "crt", "mean_mj"), 2))
m("EnergyReductionPct", fmt_pct(g("08_energy_results", "reduction_pct"), 1))
m("EnergyReductionCILow", fmt_pct(g("08_energy_results", "reduction_ci95_low"), 1))
m("EnergyReductionCIHigh", fmt_pct(g("08_energy_results", "reduction_ci95_high"), 1))
m("ShaTwoFiveSixMeanUs", fmt(g("08_crypto_timing_results", "by_operation", "sha256", "mean_us"), 1))
m("SignMeanUs", fmt(g("08_crypto_timing_results", "by_operation", "ed25519_sign", "mean_us"), 1))
m("VerifyMeanUs", fmt(g("08_crypto_timing_results", "by_operation", "ed25519_verify", "mean_us"), 1))
m("SignPipelineUs", fmt(g("08_crypto_timing_results", "sign_pipeline_us_sha256_plus_sign"), 0))

# --- Dataset totals ---
import csv as _csv
from common import ANALYSIS_DIR
total_rows = 0
n_csv = 0
with open(ANALYSIS_DIR / "analyst_data_inventory.csv", newline="") as f:
    for row in _csv.DictReader(f):
        if row["file_format"] == "csv" and row["row_count"]:
            total_rows += int(row["row_count"])
            n_csv += 1
m("ReleasedRowsTotal", fmt_int(total_rows))
m("ReleasedTracesCount", fmt_int(n_csv))

out_path = V10_DIR / "manuscript" / "macros.tex"
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w") as f:
    f.write("% AUTO-GENERATED by analysis/scripts/11_build_macros.py -- DO NOT EDIT BY HAND.\n")
    f.write("% Every value here is computed from paper_iot/V10/analysis/data/raw by the\n")
    f.write("% numbered scripts in analysis/scripts/. Re-run analysis/scripts/run_all.sh\n")
    f.write("% to regenerate.\n")
    f.write("\n".join(MACROS) + "\n")
print(f"wrote {out_path} ({len(MACROS)} macros)")
