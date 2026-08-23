"""Shared paths and helpers for the V10 analysis pipeline.

Every number reported in the V10 manuscript is produced by running the
scripts in this directory against the analyst's real raw-data package.
Nothing here reads or writes any value from the V9.2 manuscript text; V9.2
values used for comparison are stored separately in
``analysis/v92_reported_values.json`` (hand-transcribed from the released
V9.2 PDF, used only as a comparison target, never as an input to a
computation).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

# paper_iot/V10/analysis
ANALYSIS_DIR = Path(__file__).resolve().parents[1]
V10_DIR = ANALYSIS_DIR.parent
REPO_ROOT = V10_DIR.parent.parent

DATA_DIR = ANALYSIS_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
OUTPUTS_DIR = ANALYSIS_DIR / "outputs"
FIGURES_DIR = V10_DIR / "figures"
TABLES_DIR = V10_DIR / "tables"

FIELD_DIR = RAW_DIR / "raw" / "field"
EXPERIMENTS_DIR = RAW_DIR / "raw" / "experiments"
SECURITY_DIR = RAW_DIR / "raw" / "security"
PROVENANCE_DIR = RAW_DIR / "raw" / "provenance"

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
TABLES_DIR.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, sort_keys=True, default=str)
    print(f"wrote {path.relative_to(REPO_ROOT)}")


def load_json(path: Path):
    with open(path) as f:
        return json.load(f)


def merge_outputs() -> dict:
    """Combine every outputs/*.json file into one dict keyed by file stem."""
    merged = {}
    for p in sorted(OUTPUTS_DIR.glob("*.json")):
        merged[p.stem] = load_json(p)
    return merged
