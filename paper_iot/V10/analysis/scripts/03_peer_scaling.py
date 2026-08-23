#!/usr/bin/env python3
"""Phase 6: reanalysis of the logical peer-multiplicity experiment.

Experimental unit: the live run (n=32; 8 per peer count). Individual
transactions within a run are NOT treated as independent replicates.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

from common import EXPERIMENTS_DIR, OUTPUTS_DIR, write_json

RUNS = pd.read_csv(EXPERIMENTS_DIR / "peer_scaling_runs.csv", parse_dates=["start_timestamp", "end_timestamp"])
TX = pd.read_csv(EXPERIMENTS_DIR / "peer_scaling_transactions.csv")

N_BOOT = 10000
RNG = np.random.default_rng(20251001)  # fixed seed, resampling only (never generates new observations)


def build_run_table() -> pd.DataFrame:
    agg = TX.groupby("run_id").agg(
        peer_count=("peer_count", "first"),
        host_id=("host_id", "first"),
        session_id=("session_id", "first"),
        n_tx=("tx_id", "count"),
        total_latency_mean=("latency_ms", "mean"),
        total_latency_p95=("latency_ms", lambda s: np.percentile(s, 95)),
        span_mean=("rbac_overhead_ms", "mean"),
    ).reset_index()
    agg["remaining_mean"] = agg["total_latency_mean"] - agg["span_mean"]
    agg["remaining_p95"] = agg["total_latency_p95"] - agg["span_mean"]
    agg = agg.merge(RUNS[["run_id", "start_timestamp"]], on="run_id")
    agg = agg.sort_values("start_timestamp").reset_index(drop=True)
    agg["serial_position"] = np.arange(1, len(agg) + 1)
    agg["repetition"] = agg["run_id"].str.extract(r"-R(\d+)$").astype(int)
    agg["cycle"] = np.where(agg["repetition"] <= 4, 1, 2)
    agg["position_in_cycle"] = ((agg["repetition"] - 1) % 4) + 1
    agg["log2_peers"] = np.log2(agg["peer_count"])
    agg["serial_c"] = agg["serial_position"] - agg["serial_position"].mean()
    return agg


def counterbalancing_check(run_tbl: pd.DataFrame) -> dict:
    ct = pd.crosstab(run_tbl["peer_count"], run_tbl["position_in_cycle"])
    latin_square_holds = bool((ct.values == 2).all())
    return {
        "n_runs": int(len(run_tbl)),
        "n_peer_counts": int(run_tbl["peer_count"].nunique()),
        "runs_per_peer_count": run_tbl.groupby("peer_count").size().to_dict(),
        "n_repetitions": int(run_tbl["repetition"].nunique()),
        "cycles_detected": int(run_tbl["cycle"].nunique()),
        "peer_count_by_position_in_cycle_crosstab": {
            str(k): {str(kk): int(vv) for kk, vv in v.items()} for k, v in ct.to_dict(orient="index").items()
        },
        "each_config_occupies_each_position_exactly_twice": latin_square_holds,
        "host_ids_used": sorted(run_tbl["host_id"].unique().tolist()),
        "session_ids_used": sorted(run_tbl["session_id"].unique().tolist()),
        "single_physical_host": bool(run_tbl["host_id"].nunique() == 1),
        "tx_per_run": int(TX.groupby("run_id").size().iloc[0]),
        "tx_per_run_constant": bool(TX.groupby("run_id").size().nunique() == 1),
    }


def group_stats(run_tbl: pd.DataFrame, col: str) -> dict:
    out = {}
    for pc, grp in run_tbl.groupby("peer_count"):
        vals = grp[col].values
        n = len(vals)
        mean = float(np.mean(vals))
        sd = float(np.std(vals, ddof=1))
        se = sd / np.sqrt(n)
        tcrit = stats.t.ppf(0.975, df=n - 1)
        out[int(pc)] = {
            "n": int(n), "mean": mean, "sd": sd,
            "median": float(np.median(vals)),
            "ci95_low": mean - tcrit * se, "ci95_high": mean + tcrit * se,
        }
    return out


def bootstrap_group_p95_ci(run_tbl: pd.DataFrame, col: str) -> dict:
    """Resample whole runs (the experimental unit), not individual
    transactions, for each peer-count group's P95-of-run-means CI."""
    out = {}
    for pc, grp in run_tbl.groupby("peer_count"):
        vals = grp[col].values
        boots = RNG.choice(vals, size=(N_BOOT, len(vals)), replace=True).mean(axis=1)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        out[int(pc)] = {"mean": float(vals.mean()), "ci95_low": float(lo), "ci95_high": float(hi)}
    return out


def log_linear_fit(run_tbl: pd.DataFrame, col: str) -> dict:
    means = run_tbl.groupby("peer_count")[col].mean()
    x = np.log2(means.index.values.astype(float))
    y = means.values
    slope, intercept, r, p, se = stats.linregress(x, y)
    return {
        "slope_per_doubling": float(slope), "intercept": float(intercept),
        "r2": float(r ** 2), "p": float(p), "n_configs": int(len(means)),
    }


def pairwise_extreme(run_tbl: pd.DataFrame, col: str, margin_ms: float = 10.0) -> dict:
    lo = run_tbl[run_tbl["peer_count"] == 4].sort_values("repetition")
    hi = run_tbl[run_tbl["peer_count"] == 32].sort_values("repetition")
    merged = lo.merge(hi, on="repetition", suffixes=("_4", "_32"))
    diffs = merged[f"{col}_4"].values - merged[f"{col}_32"].values
    n = len(diffs)
    mean_d = float(diffs.mean())
    sd_d = float(diffs.std(ddof=1))
    se_d = sd_d / np.sqrt(n)
    t90 = stats.t.ppf(0.95, df=n - 1)
    t95 = stats.t.ppf(0.975, df=n - 1)
    # paired t-test (superiority)
    t_stat, p_val = stats.ttest_rel(merged[f"{col}_4"], merged[f"{col}_32"])
    cohens_d = mean_d / sd_d if sd_d > 0 else float("nan")
    # exploratory TOST for equivalence within +/- margin (applies to the recorded span only)
    t_low = (mean_d - (-margin_ms)) / se_d
    t_high = (mean_d - margin_ms) / se_d
    p_tost_low = 1 - stats.t.cdf(t_low, df=n - 1)
    p_tost_high = stats.t.cdf(t_high, df=n - 1)
    p_tost = max(p_tost_low, p_tost_high)
    return {
        "n_pairs": int(n),
        "block_level_differences": {int(r): float(d) for r, d in zip(merged["repetition"], diffs)},
        "mean_diff_4_minus_32": mean_d,
        "sd_diff": sd_d,
        "ci95_low": mean_d - t95 * se_d, "ci95_high": mean_d + t95 * se_d,
        "ci90_low": mean_d - t90 * se_d, "ci90_high": mean_d + t90 * se_d,
        "paired_t": float(t_stat), "paired_p": float(p_val), "cohens_d": float(cohens_d),
        "tost_margin_ms": margin_ms,
        "tost_p": float(p_tost),
        "tost_equivalent_at_alpha_05": bool(p_tost < 0.05),
    }


def order_effect_model(run_tbl: pd.DataFrame, col: str) -> dict:
    """Joint regression on log2(peer count) and centred run sequence,
    replicating the design V9.2 describes, run against the real run table."""
    df = run_tbl.copy()
    model = smf.ols(f"{col} ~ log2_peers + serial_c", data=df).fit()
    return {
        "n": int(model.nobs),
        "r2": float(model.rsquared),
        "log2_peers_coef": float(model.params["log2_peers"]),
        "log2_peers_p": float(model.pvalues["log2_peers"]),
        "serial_c_coef": float(model.params["serial_c"]),
        "serial_c_p": float(model.pvalues["serial_c"]),
        "intercept": float(model.params["Intercept"]),
    }


def block_design_model(run_tbl: pd.DataFrame, col: str) -> dict:
    """Primary block-design model: outcome ~ C(peer_count) + C(block) + serial_position,
    block = repetition number (1..8), the true counterbalancing block confirmed
    by the run manifest (see counterbalancing_check)."""
    df = run_tbl.copy()
    df = df.rename(columns={"repetition": "block"})
    model = smf.ols(f"{col} ~ C(peer_count) + C(block) + serial_position", data=df).fit()
    from statsmodels.stats.anova import anova_lm
    aov = anova_lm(model, typ=2)
    return {
        "n": int(model.nobs),
        "r2": float(model.rsquared),
        "r2_adj": float(model.rsquared_adj),
        "peer_count_F": float(aov.loc["C(peer_count)", "F"]),
        "peer_count_p": float(aov.loc["C(peer_count)", "PR(>F)"]),
        "block_F": float(aov.loc["C(block)", "F"]),
        "block_p": float(aov.loc["C(block)", "PR(>F)"]),
        "serial_position_F": float(aov.loc["serial_position", "F"]),
        "serial_position_p": float(aov.loc["serial_position", "PR(>F)"]),
        "residual_shapiro_p": float(stats.shapiro(model.resid).pvalue),
    }


def sensitivity_without_extremes(run_tbl: pd.DataFrame, col: str) -> dict:
    """Sensitivity analysis: drop the single fastest and slowest run overall
    and recompute the 4-vs-32 group means, to check robustness."""
    trimmed = run_tbl[(run_tbl[col] != run_tbl[col].min()) & (run_tbl[col] != run_tbl[col].max())]
    return group_stats(trimmed, col)


def main() -> None:
    run_tbl = build_run_table()
    run_tbl.to_csv(OUTPUTS_DIR / "03_peer_scaling_run_table.csv", index=False)

    design = counterbalancing_check(run_tbl)
    write_json(OUTPUTS_DIR / "03_design_check.json", design)

    result = {"design": design}
    for label, col in [
        ("total_latency", "total_latency_mean"),
        ("recorded_span", "span_mean"),
        ("remaining_latency", "remaining_mean"),
        ("p95_latency", "total_latency_p95"),
    ]:
        result[label] = {
            "group_stats": group_stats(run_tbl, col),
            "bootstrap_ci": bootstrap_group_p95_ci(run_tbl, col),
            "log_linear_fit": log_linear_fit(run_tbl, col),
            "pairwise_4v32": pairwise_extreme(run_tbl, col),
            "order_effect_model": order_effect_model(run_tbl, col),
            "block_design_model": block_design_model(run_tbl, col),
        }
    result["sensitivity_trim_extremes_total_latency"] = sensitivity_without_extremes(run_tbl, "total_latency_mean")

    # Recorded-span share of write path, by peer count
    span_share = {}
    for pc, grp in run_tbl.groupby("peer_count"):
        span_share[int(pc)] = float((grp["span_mean"] / grp["total_latency_mean"]).mean() * 100)
    result["recorded_span_share_pct_by_peer_count"] = span_share

    write_json(OUTPUTS_DIR / "03_peer_scaling_results.json", result)


if __name__ == "__main__":
    main()
