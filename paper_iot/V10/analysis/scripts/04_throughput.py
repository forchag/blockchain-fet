#!/usr/bin/env python3
"""Phase 7: reanalysis of the interleaved throughput-vs-concurrency experiment.

Experimental unit: the live run (n=100; 10 concurrency levels x 2 conditions x
5 runs). The campaign used ONE experimental session with the ten concurrency
levels tested in one fixed ascending order; only the two conditions were
interleaved within each concurrency cell. That structure -- not a design
choice of this analysis -- is why campaign-wide sequence cannot serve as an
independent order covariate (it is almost collinear with concurrency) and why
within-cell position is used instead.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

from common import EXPERIMENTS_DIR, OUTPUTS_DIR, write_json

RUNS = pd.read_csv(EXPERIMENTS_DIR / "throughput_runs.csv", parse_dates=["start_timestamp", "end_timestamp"])
RUNS = RUNS.sort_values("start_timestamp").reset_index(drop=True)
RUNS["campaign_seq"] = np.arange(1, len(RUNS) + 1)
RUNS["cell_position"] = RUNS.groupby(["concurrency_level"]).cumcount() + 1  # 1..10 within a concurrency cell
RUNS["concurrency_c"] = RUNS["concurrency_level"] - RUNS["concurrency_level"].mean()
RUNS["position_c"] = RUNS["cell_position"] - RUNS["cell_position"].mean()
RUNS["condition_hrbac"] = (RUNS["condition"] == "hrbac").astype(int)


def design_check() -> dict:
    corr = np.corrcoef(RUNS["campaign_seq"], RUNS["concurrency_level"])[0, 1]
    return {
        "n_runs": int(len(RUNS)),
        "n_concurrency_levels": int(RUNS["concurrency_level"].nunique()),
        "concurrency_levels": sorted(RUNS["concurrency_level"].unique().tolist()),
        "runs_per_condition_per_level": RUNS.groupby(["concurrency_level", "condition"]).size().unstack().to_dict(),
        "n_sessions": int(RUNS["session_id"].nunique()),
        "session_ids": RUNS["session_id"].unique().tolist(),
        "concurrency_order": "single fixed ascending sequence (one session)",
        "conditions_interleaved_within_cell": True,
        "campaign_seq_vs_concurrency_correlation": float(corr),
        "campaign_seq_usable_as_independent_order_covariate": bool(abs(corr) < 0.9),
    }


def primary_model() -> dict:
    model = smf.ols(
        "tps ~ condition_hrbac * concurrency_c + position_c", data=RUNS
    ).fit()
    return {
        "n": int(model.nobs),
        "r2": float(model.rsquared),
        "condition_coef_tps": float(model.params["condition_hrbac"]),
        "condition_ci_low": float(model.conf_int().loc["condition_hrbac", 0]),
        "condition_ci_high": float(model.conf_int().loc["condition_hrbac", 1]),
        "condition_p": float(model.pvalues["condition_hrbac"]),
        "interaction_coef_tps_per_client": float(model.params["condition_hrbac:concurrency_c"]),
        "interaction_ci_low": float(model.conf_int().loc["condition_hrbac:concurrency_c", 0]),
        "interaction_ci_high": float(model.conf_int().loc["condition_hrbac:concurrency_c", 1]),
        "interaction_p": float(model.pvalues["condition_hrbac:concurrency_c"]),
        "position_coef": float(model.params["position_c"]),
        "position_p": float(model.pvalues["position_c"]),
        "residual_shapiro_p": float(stats.shapiro(model.resid).pvalue),
    }


def per_level_percent_diff() -> dict:
    levels = sorted(RUNS["concurrency_level"].unique())
    pct = {}
    raw_pairs = []
    for lvl in levels:
        base = RUNS[(RUNS.concurrency_level == lvl) & (RUNS.condition == "baseline")]["tps"]
        hr = RUNS[(RUNS.concurrency_level == lvl) & (RUNS.condition == "hrbac")]["tps"]
        d = (1 - hr.mean() / base.mean()) * 100
        pct[int(lvl)] = float(d)
        raw_pairs.append(d)
    holm = holm_bonferroni_from_ttests(levels)
    return {
        "pct_diff_by_level": pct,
        "pct_diff_mean": float(np.mean(raw_pairs)),
        "pct_diff_sd": float(np.std(raw_pairs, ddof=1)),
        "pct_diff_min": float(np.min(raw_pairs)),
        "pct_diff_max": float(np.max(raw_pairs)),
        "holm_bonferroni": holm,
    }


def holm_bonferroni_from_ttests(levels) -> dict:
    pvals = []
    for lvl in levels:
        base = RUNS[(RUNS.concurrency_level == lvl) & (RUNS.condition == "baseline")]["tps"]
        hr = RUNS[(RUNS.concurrency_level == lvl) & (RUNS.condition == "hrbac")]["tps"]
        _, p = stats.ttest_ind(base, hr, equal_var=False)
        pvals.append(p)
    order = np.argsort(pvals)
    m = len(pvals)
    adj = [None] * m
    running_max = 0.0
    for rank, idx in enumerate(order):
        adj_p = (m - rank) * pvals[idx]
        running_max = max(running_max, adj_p)
        adj[idx] = min(running_max, 1.0)
    n_sig = sum(1 for a in adj if a < 0.05)
    return {
        "raw_p_by_level": {int(lvl): float(p) for lvl, p in zip(levels, pvals)},
        "holm_adjusted_p_by_level": {int(lvl): float(a) for lvl, a in zip(levels, adj)},
        "n_significant_after_adjustment": int(n_sig),
        "n_levels": int(m),
    }


def observed_peaks() -> dict:
    means = RUNS.groupby(["concurrency_level", "condition"])["tps"].mean().unstack()
    peak_base_level = means["baseline"].idxmax()
    peak_hr_level = means["hrbac"].idxmax()
    at_100 = means.loc[100]
    return {
        "mean_tps_by_level_and_condition": means.to_dict(),
        "baseline_peak_tps": float(means["baseline"].max()),
        "baseline_peak_level": int(peak_base_level),
        "hrbac_peak_tps": float(means["hrbac"].max()),
        "hrbac_peak_level": int(peak_hr_level),
        "same_tested_peak_level": bool(peak_base_level == peak_hr_level),
        "hrbac_decline_pct_peak_to_100": float((1 - at_100["hrbac"] / means["hrbac"].max()) * 100),
        "baseline_decline_pct_peak_to_100": float((1 - at_100["baseline"] / means["baseline"].max()) * 100),
    }


def main() -> None:
    write_json(OUTPUTS_DIR / "04_throughput_design_check.json", design_check())
    write_json(OUTPUTS_DIR / "04_throughput_primary_model.json", primary_model())
    write_json(OUTPUTS_DIR / "04_throughput_per_level.json", per_level_percent_diff())
    write_json(OUTPUTS_DIR / "04_throughput_peaks.json", observed_peaks())
    RUNS.to_csv(OUTPUTS_DIR / "04_throughput_run_table.csv", index=False)


if __name__ == "__main__":
    main()
