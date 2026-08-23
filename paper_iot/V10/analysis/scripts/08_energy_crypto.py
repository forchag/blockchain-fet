#!/usr/bin/env python3
"""Phase 13: energy and cryptographic-timing bench reanalysis (controlled,
single-device measurements -- not the 61-day field trace)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from common import EXPERIMENTS_DIR, OUTPUTS_DIR, write_json

EM = pd.read_csv(EXPERIMENTS_DIR / "energy_measurements.csv")
CT = pd.read_csv(EXPERIMENTS_DIR / "cryptographic_timings.csv")


def energy_analysis() -> dict:
    sc = EM[EM["mode"] == "single_channel"]["energy_mj"]
    crt = EM[EM["mode"] == "crt"]["energy_mj"]
    diff_pct = (1 - crt.mean() / sc.mean()) * 100
    # bootstrap CI on the percent reduction
    rng = np.random.default_rng(20251002)
    boots = []
    for _ in range(10000):
        s = rng.choice(sc.values, size=len(sc), replace=True)
        c = rng.choice(crt.values, size=len(crt), replace=True)
        boots.append((1 - c.mean() / s.mean()) * 100)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    t_stat, p_val = stats.ttest_ind(sc, crt, equal_var=False)
    return {
        "single_channel": {"n": int(len(sc)), "mean_mj": float(sc.mean()), "sd_mj": float(sc.std(ddof=1))},
        "crt": {"n": int(len(crt)), "mean_mj": float(crt.mean()), "sd_mj": float(crt.std(ddof=1))},
        "reduction_pct": float(diff_pct),
        "reduction_ci95_low": float(lo), "reduction_ci95_high": float(hi),
        "welch_t": float(t_stat), "welch_p": float(p_val),
        "payload_bytes_range": [int(EM["payload_bytes"].min()), int(EM["payload_bytes"].max())],
        "airtime_ms_by_mode": EM.groupby("mode")["airtime_ms"].mean().to_dict(),
        "measurement_note": "Single-node INA219-style bench measurement; not generalized across all 50 devices.",
    }


def crypto_timing_analysis() -> dict:
    out = {}
    for op, grp in CT.groupby("operation"):
        out[op] = {
            "n": int(len(grp)), "mean_us": float(grp["duration_us"].mean()),
            "sd_us": float(grp["duration_us"].std(ddof=1)),
            "median_us": float(grp["duration_us"].median()),
        }
    total_pipeline = CT.groupby("sample_id")["duration_us"].sum() if "sample_id" in CT.columns else None
    sha_mean = out.get("sha256", {}).get("mean_us", 0)
    sign_mean = out.get("ed25519_sign", {}).get("mean_us", 0)
    verify_mean = out.get("ed25519_verify", {}).get("mean_us", 0)
    return {
        "by_operation": out,
        "sign_pipeline_us_sha256_plus_sign": float(sha_mean + sign_mean),
        "verify_us": float(verify_mean),
        "n_samples_total": int(len(CT)),
    }


def main() -> None:
    write_json(OUTPUTS_DIR / "08_energy_results.json", energy_analysis())
    write_json(OUTPUTS_DIR / "08_crypto_timing_results.json", crypto_timing_analysis())


if __name__ == "__main__":
    main()
