#!/usr/bin/env python3
"""Phase 22: regenerate Figures 3 and 4 from the verified real data."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import EXPERIMENTS_DIR, FIGURES_DIR

plt.rcParams.update({"font.size": 9, "figure.dpi": 200})


def figure3_throughput():
    df = pd.read_csv(EXPERIMENTS_DIR / "throughput_runs.csv")
    stats = df.groupby(["concurrency_level", "condition"])["tps"].agg(["mean", "std"]).reset_index()
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for cond, marker, color in [("baseline", "o", "#1b6ca8"), ("hrbac", "s", "#c0392b")]:
        s = stats[stats.condition == cond].sort_values("concurrency_level")
        ax.errorbar(s.concurrency_level, s["mean"], yerr=s["std"], marker=marker,
                    label="Fabric without access control" if cond == "baseline" else "HRBAC",
                    color=color, capsize=3, linewidth=1.4)
    ax.set_xlabel("Offered concurrency (clients)")
    ax.set_ylabel("Throughput (TPS)")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "figure3_throughput.pdf")
    fig.savefig(FIGURES_DIR / "figure3_throughput.png")
    plt.close(fig)


def figure4_peer_latency():
    tx = pd.read_csv(EXPERIMENTS_DIR / "peer_scaling_transactions.csv")
    runs = pd.read_csv(EXPERIMENTS_DIR / "peer_scaling_runs.csv", parse_dates=["start_timestamp"])
    agg = tx.groupby("run_id").agg(
        peer_count=("peer_count", "first"),
        mean_latency=("latency_ms", "mean"),
        p95_latency=("latency_ms", lambda s: np.percentile(s, 95)),
    ).reset_index().merge(runs[["run_id", "start_timestamp"]], on="run_id").sort_values("start_timestamp")
    agg["repetition"] = agg["run_id"].str.extract(r"-R(\d+)$").astype(int)
    agg["block"] = agg["repetition"]

    fig, axes = plt.subplots(2, 1, figsize=(5.2, 6.0), sharex=True)
    rng = np.random.default_rng(1)
    cmap = plt.get_cmap("tab10")

    for ax, col, ylabel in [(axes[0], "mean_latency", "Mean write latency (ms)"),
                             (axes[1], "p95_latency", "P95 (ms)")]:
        for pc in sorted(agg.peer_count.unique()):
            sub = agg[agg.peer_count == pc]
            jitter = rng.uniform(-0.15, 0.15, size=len(sub))
            xs = np.log2(pc) + jitter
            ax.scatter(xs, sub[col], c=[cmap(b % 10) for b in sub["block"]], s=22, alpha=0.85, zorder=3)
            mean = sub[col].mean()
            sd = sub[col].std(ddof=1)
            se = sd / np.sqrt(len(sub))
            from scipy import stats as sstats
            tcrit = sstats.t.ppf(0.975, df=len(sub) - 1)
            ax.errorbar([np.log2(pc)], [mean], yerr=[tcrit * se], fmt="D", color="black",
                        markersize=7, capsize=4, zorder=4)
        ax.set_ylabel(ylabel)
        ax.set_xticks([2, 3, 4, 5])
        ax.set_xticklabels([4, 8, 16, 32])
        ax.spines[["top", "right"]].set_visible(False)
    axes[1].set_xlabel("Configured logical peers")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "figure4_peer_latency.pdf")
    fig.savefig(FIGURES_DIR / "figure4_peer_latency.png")
    plt.close(fig)


if __name__ == "__main__":
    figure3_throughput()
    figure4_peer_latency()
    print("wrote figure3_throughput.{pdf,png} and figure4_peer_latency.{pdf,png}")
