#!/usr/bin/env python3
"""Phase 12: revocation lifecycle-stage reanalysis (field trace)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import FIELD_DIR, OUTPUTS_DIR, write_json

RS = pd.read_csv(FIELD_DIR / "revocation_stages.csv", parse_dates=["stage_timestamp"])
RD = pd.read_csv(FIELD_DIR / "revocation_denials.csv", parse_dates=["timestamp"])


def duration_stats(series: pd.Series) -> dict:
    return {
        "n": int(series.count()), "mean": float(series.mean()), "sd": float(series.std(ddof=1)),
        "p95": float(series.quantile(0.95)), "max": float(series.max()), "min": float(series.min()),
    }


def main() -> None:
    span_days = (RS["stage_timestamp"].max() - RS["stage_timestamp"].min()).days + 1
    stage_counts = RS["stage_name"].value_counts().to_dict()
    status_counts = RS["status"].value_counts().to_dict()
    delayed = RS[RS["status"] == "delayed"]
    delayed_by_stage = RS.groupby("stage_name")["status"].apply(lambda s: (s == "delayed").mean() * 100).to_dict()

    subjects = RS.groupby("cert_user_id")["stage_name"].apply(lambda s: set(s)).reset_index()
    all_stages = set(RS["stage_name"].unique())
    subjects["n_distinct_stages"] = subjects["stage_name"].apply(len)
    n_subjects = int(RS["cert_user_id"].nunique())
    n_all_stages = int((subjects["n_distinct_stages"] == len(all_stages)).sum())
    n_appear_once = int((RS.groupby("cert_user_id").size() == 1).sum())

    result = {
        "n_stage_records": int(len(RS)),
        "trace_span_days": int(span_days),
        "stage_name_counts": stage_counts,
        "status_counts": status_counts,
        "delayed_count": int(len(delayed)),
        "delayed_pct": float(len(delayed) / len(RS) * 100),
        "delayed_pct_by_stage": delayed_by_stage,
        "n_distinct_stage_types": len(all_stages),
        "n_subjects": n_subjects,
        "n_subjects_with_all_stage_types": n_all_stages,
        "n_subjects_appearing_once": n_appear_once,
        "episode_reconstructable": False,
        "episode_reconstruction_note": (
            "No episode/correlation identifier links stages of the same revocation event; "
            "stage records for the same cert_user_id cannot be safely paired into single "
            "episodes because a subject may be revoked more than once over 61 days. End-to-end "
            "exposure and causal attribution against connectivity outages cannot be computed "
            "from this trace, consistent with V9.2's L5 (revocation observability)."
        ),
        "field_revocation_denials": {
            "count": int(len(RD)),
            "per_day": float(len(RD) / ((RD["timestamp"].max() - RD["timestamp"].min()).days + 1)),
            "deny_reason_counts": RD["deny_reason"].value_counts().to_dict(),
            "denominator_of_all_post_revocation_attempts_available": False,
            "success_rate_estimable": False,
        },
    }
    write_json(OUTPUTS_DIR / "07_revocation_results.json", result)


if __name__ == "__main__":
    main()
