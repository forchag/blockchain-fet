#!/usr/bin/env python3
"""Phase 1: safely extract the analyst raw-data package and inventory it.

Run from anywhere:  python3 01_extract_and_inventory.py

Safety properties:
  * zip-slip protected (every extracted path is verified to stay inside the
    destination directory before it is written);
  * refuses to overwrite a file that already exists at the destination;
  * never deletes or rewrites the original zip;
  * records a source-zip-entry -> canonical-extracted-file mapping.
"""
from __future__ import annotations

import csv
import json
import os
import zipfile
from pathlib import Path

import pandas as pd

from common import DATA_DIR, RAW_DIR, OUTPUTS_DIR, ANALYSIS_DIR, sha256_file, write_json

ZIP_PATH = DATA_DIR / "analyst_raw_data_package.zip"


def safe_extract(zip_path: Path, dest: Path) -> list[dict]:
    dest_abs = dest.resolve()
    mapping = []
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            name = member.filename
            if "__MACOSX" in name or Path(name).name.startswith("."):
                continue
            target = (dest / name).resolve()
            if not (target == dest_abs or str(target).startswith(str(dest_abs) + os.sep)):
                raise ValueError(f"zip-slip blocked: {name!r} resolves outside {dest_abs}")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                # Idempotent re-run: verify identical content rather than erroring.
                existing_hash = sha256_file(target)
                with zf.open(member) as src:
                    new_bytes = src.read()
                new_hash = __import__("hashlib").sha256(new_bytes).hexdigest()
                if existing_hash != new_hash:
                    raise ValueError(f"refusing to overwrite changed file: {target}")
            else:
                with zf.open(member) as src, open(target, "wb") as out:
                    out.write(src.read())
            mapping.append({
                "zip_entry": name,
                "canonical_path": str(target.relative_to(ANALYSIS_DIR.parent.parent)),
                "sha256": sha256_file(target),
                "size_bytes": target.stat().st_size,
            })
    return mapping


def profile_csv(path: Path) -> dict:
    try:
        df = pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - defensive
        return {"error": str(exc)}
    info = {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": list(df.columns),
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_values_total": int(df.isna().sum().sum()),
        "missing_by_column": {c: int(n) for c, n in df.isna().sum().items() if n > 0},
    }
    for tscol in ("timestamp", "start_timestamp", "stage_timestamp", "start_time"):
        if tscol in df.columns:
            try:
                ts = pd.to_datetime(df[tscol], errors="coerce", utc=True)
                info["date_min"] = str(ts.min())
                info["date_max"] = str(ts.max())
                info["unparseable_timestamps"] = int(ts.isna().sum() - df[tscol].isna().sum())
            except Exception:
                pass
            break
    return info


def profile_log_dir(path: Path) -> dict:
    files = sorted(path.glob("*"))
    total_lines = 0
    for f in files:
        if f.is_file():
            with open(f, "rb") as fh:
                total_lines += sum(1 for _ in fh)
    return {"file_count": len(files), "total_lines": total_lines}


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    zip_sha = sha256_file(ZIP_PATH)
    print(f"analyst_raw_data_package.zip sha256={zip_sha}")

    mapping = safe_extract(ZIP_PATH, RAW_DIR)
    write_json(OUTPUTS_DIR / "01_zip_extraction_mapping.json", {
        "zip_sha256": zip_sha,
        "zip_size_bytes": ZIP_PATH.stat().st_size,
        "extracted_entries": mapping,
    })

    inventory_rows = []
    csv_files = sorted(RAW_DIR.rglob("*.csv"))
    jsonl_files = sorted(RAW_DIR.rglob("*.jsonl"))
    log_dirs = [p for p in RAW_DIR.rglob("*") if p.is_dir() and any(p.glob("*.log"))]

    dataset_role = {
        "raw_field_topology.csv": ("field", "topology (static)"),
        "sensor_transactions.csv": ("field", "sensor write transactions, 61-day deployment"),
        "authorization_decisions.csv": ("field", "all authorization decisions, 61-day deployment"),
        "connectivity_outages.csv": ("field", "gateway connectivity outage log"),
        "revocation_denials.csv": ("field", "field-observed post-revocation access attempts"),
        "revocation_stages.csv": ("field", "certificate-revocation lifecycle stage records"),
        "peer_scaling_runs.csv": ("controlled_experiment", "peer-multiplicity campaign run manifest"),
        "peer_scaling_transactions.csv": ("controlled_experiment", "peer-multiplicity campaign transaction-level records"),
        "throughput_runs.csv": ("controlled_experiment", "interleaved throughput-vs-concurrency campaign"),
        "energy_measurements.csv": ("controlled_experiment", "LoRa single-channel vs residue-mode energy bench"),
        "cryptographic_timings.csv": ("controlled_experiment", "cryptographic primitive timing bench"),
        "authorization_boundary_attempts.csv": ("scripted_security_test", "scripted authorization-boundary attempts"),
    }

    for f in csv_files:
        rel = f.relative_to(RAW_DIR.parent.parent.parent)
        prof = profile_csv(f)
        role, desc = dataset_role.get(f.name, ("unknown", ""))
        inventory_rows.append({
            "filename": f.name,
            "relative_path": str(rel),
            "file_format": "csv",
            "file_size_bytes": f.stat().st_size,
            "sha256": sha256_file(f),
            "row_count": prof.get("row_count"),
            "column_count": prof.get("column_count"),
            "column_names": ";".join(prof.get("columns", [])),
            "probable_dataset": role,
            "notes": desc,
            "duplicate_rows": prof.get("duplicate_rows"),
            "missing_values_total": prof.get("missing_values_total"),
            "date_min": prof.get("date_min", ""),
            "date_max": prof.get("date_max", ""),
        })

    for f in jsonl_files:
        rel = f.relative_to(RAW_DIR.parent.parent.parent)
        with open(f) as fh:
            n = sum(1 for _ in fh)
        inventory_rows.append({
            "filename": f.name,
            "relative_path": str(rel),
            "file_format": "jsonl",
            "file_size_bytes": f.stat().st_size,
            "sha256": sha256_file(f),
            "row_count": n,
            "column_count": "",
            "column_names": "",
            "probable_dataset": "field_provenance_sample",
            "notes": "Fabric ledger block sample (provenance corroboration, not the full ledger)",
            "duplicate_rows": "",
            "missing_values_total": "",
            "date_min": "",
            "date_max": "",
        })

    log_summary = {}
    for d in log_dirs:
        rel = d.relative_to(RAW_DIR.parent.parent.parent)
        prof = profile_log_dir(d)
        log_summary[str(rel)] = prof
        inventory_rows.append({
            "filename": d.name,
            "relative_path": str(rel),
            "file_format": "log_directory",
            "file_size_bytes": sum(p.stat().st_size for p in d.glob("*") if p.is_file()),
            "sha256": "",
            "row_count": prof["total_lines"],
            "column_count": "",
            "column_names": "",
            "probable_dataset": "field_provenance_sample",
            "notes": f"{prof['file_count']} per-device/per-gateway JSON-lines log files",
            "duplicate_rows": "",
            "missing_values_total": "",
            "date_min": "",
            "date_max": "",
        })

    csv_path = ANALYSIS_DIR / "analyst_data_inventory.csv"
    fieldnames = list(inventory_rows[0].keys())
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(inventory_rows)
    print(f"wrote {csv_path}")

    write_json(OUTPUTS_DIR / "01_inventory_summary.json", {
        "csv_file_count": len(csv_files),
        "jsonl_file_count": len(jsonl_files),
        "log_directory_count": len(log_dirs),
        "log_directories": log_summary,
    })


if __name__ == "__main__":
    main()
