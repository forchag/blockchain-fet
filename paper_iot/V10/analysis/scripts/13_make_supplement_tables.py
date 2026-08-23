#!/usr/bin/env python3
"""Generate LaTeX table bodies for the V10 supplementary material directly
from the analysis outputs / raw data, so the supplement's numbers are
reproducible the same way the main text's are."""
from __future__ import annotations

import pandas as pd

from common import EXPERIMENTS_DIR, TABLES_DIR, load_json, OUTPUTS_DIR

import importlib.util
spec = importlib.util.spec_from_file_location("sec_oracle", "06_security_oracle.py")
sec_oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sec_oracle)


def esc(s):
    return str(s).replace("_", "\\_").replace("%", "\\%")


def s2_permission_matrix():
    perms = ["ReadOwn", "ReadZone", "ReadAll", "WriteSensor", "ControlZone",
             "ControlAll", "ReadAudit", "ManageRoles", "IssueCrossZone", "AdminAll"]
    roles = ["Admin", "Gateway", "Farmer", "Agronomist", "Certifier", "SupplyChain", "Sensor"]
    lines = [r"\begin{tabular}{l" + "c" * len(perms) + "}", r"\toprule",
             "Role & " + " & ".join(f"\\rotatebox{{60}}{{{p}}}" for p in perms) + r" \\", r"\midrule"]
    for r in roles:
        eff = sec_oracle.effective_permissions(r, sec_oracle.ROLE_PERMISSIONS_DEPLOYED, sec_oracle.ROLE_ANCESTORS_DEPLOYED)
        row = [r] + [("Yes" if p in eff or "AdminAll" in eff else "") for p in perms]
        lines.append(" & ".join(row) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TABLES_DIR / "s2_permission_matrix.tex").write_text("\n".join(lines))


def s5_latency_by_cell():
    d = load_json(OUTPUTS_DIR / "02_latency_by_class.json")
    cells = d["grant_rate_by_cell_pct"]
    lines = [r"\begin{longtable}{llr}", r"\caption{Grant rate by role-operation cell (all cells in the trace).}\label{tab:s5}\\",
             r"\toprule", r"Role & Operation & Grant rate (\%) \\", r"\midrule", r"\endfirsthead",
             r"\toprule", r"Role & Operation & Grant rate (\%) \\", r"\midrule", r"\endhead",
             r"\bottomrule", r"\endfoot"]
    for k, v in sorted(cells.items()):
        role, op = k.split("|")
        lines.append(f"{esc(role)} & {esc(op)} & {v:.2f} \\\\")
    lines.append(r"\end{longtable}")
    (TABLES_DIR / "s5_latency_by_cell.tex").write_text("\n".join(lines))


def s6_throughput_per_level():
    d = load_json(OUTPUTS_DIR / "04_throughput_per_level.json")
    peaks = load_json(OUTPUTS_DIR / "04_throughput_peaks.json")
    means = peaks["mean_tps_by_level_and_condition"]
    lines = [r"\begin{tabular}{rrrrr}", r"\toprule",
             r"Concurrency & Baseline TPS & HRBAC TPS & \% lower & Holm-adj.\ $p$ \\", r"\midrule"]
    for lvl in sorted(d["pct_diff_by_level"].keys(), key=int):
        base = means["baseline"][str(lvl)]
        hr = means["hrbac"][str(lvl)]
        pct = d["pct_diff_by_level"][lvl]
        padj = d["holm_bonferroni"]["holm_adjusted_p_by_level"][lvl]
        padj_s = "$<$0.001" if padj < 0.001 else f"{padj:.4f}"
        lines.append(f"{lvl} & {base:.1f} & {hr:.1f} & {pct:.1f} & {padj_s} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TABLES_DIR / "s6_throughput_per_level.tex").write_text("\n".join(lines))


def s7_s8_peer_runs():
    df = pd.read_csv(OUTPUTS_DIR / "03_peer_scaling_run_table.csv")
    df = df.sort_values("serial_position")
    lines = [r"\begin{longtable}{rrrrrrr}",
             r"\caption{All 32 peer-scaling run-level observations.}\label{tab:s7}\\",
             r"\toprule",
             r"Serial pos. & Run ID & Peers & Block (rep.) & Total lat.\ (ms) & Span (ms) & P95 (ms) \\",
             r"\midrule", r"\endfirsthead",
             r"\toprule",
             r"Serial pos. & Run ID & Peers & Block (rep.) & Total lat.\ (ms) & Span (ms) & P95 (ms) \\",
             r"\midrule", r"\endhead", r"\bottomrule", r"\endfoot"]
    for _, r in df.iterrows():
        lines.append(
            f"{int(r.serial_position)} & {esc(r.run_id)} & {int(r.peer_count)} & {int(r.repetition)} & "
            f"{r.total_latency_mean:.1f} & {r.span_mean:.1f} & {r.total_latency_p95:.1f} \\\\"
        )
    lines.append(r"\end{longtable}")
    (TABLES_DIR / "s7_peer_runs.tex").write_text("\n".join(lines))

    # S8: counterbalancing schedule (peer count x position-in-cycle x cycle)
    ct = df.groupby(["peer_count", "position_in_cycle", "cycle"]).size().reset_index(name="n")
    lines2 = [r"\begin{tabular}{rrrr}", r"\toprule",
              r"Peer count & Position in cycle & Cycle & Runs \\", r"\midrule"]
    for _, r in ct.sort_values(["cycle", "position_in_cycle", "peer_count"]).iterrows():
        lines2.append(f"{int(r.peer_count)} & {int(r.position_in_cycle)} & {int(r.cycle)} & {int(r.n)} \\\\")
    lines2 += [r"\bottomrule", r"\end{tabular}"]
    (TABLES_DIR / "s8_counterbalancing.tex").write_text("\n".join(lines2))


def s10_crt_bounds():
    d = load_json(OUTPUTS_DIR / "05_crt_quantization.json")
    b = d["deployed_pairwise_bounds"]
    cb = d["corrected_domain"]["pairwise_bounds"]
    lines = [r"\begin{tabular}{lrr}", r"\toprule", r"Missing residue pair & Deployed bound & Corrected bound \\", r"\midrule",
             f"$\\{{97,101\\}}$ (missing mod 103) & {b['a*b']:,} & {cb['a*b']:,} \\\\",
             f"$\\{{97,103\\}}$ (missing mod 101) & {b['a*c']:,} & {cb['a*c']:,} \\\\",
             f"$\\{{101,103\\}}$ (missing mod 97) & {b['b*c']:,} & {cb['b*c']:,} \\\\",
             r"\bottomrule", r"\end{tabular}"]
    (TABLES_DIR / "s10_crt_bounds.tex").write_text("\n".join(lines))


def s11_denial_mechanism_breakdown():
    sec = pd.read_csv(sec_oracle.SECURITY_DIR / "authorization_boundary_attempts.csv")
    ct = pd.crosstab(sec["scenario"], sec["deny_reason"])
    lines = [r"\begin{tabular}{l" + "r" * len(ct.columns) + "}", r"\toprule",
             "Scenario & " + " & ".join(esc(c) for c in ct.columns) + r" \\", r"\midrule"]
    for idx, row in ct.iterrows():
        lines.append(esc(idx) + " & " + " & ".join(str(v) for v in row.values) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TABLES_DIR / "s11_denial_breakdown.tex").write_text("\n".join(lines))


if __name__ == "__main__":
    s2_permission_matrix()
    s5_latency_by_cell()
    s6_throughput_per_level()
    s7_s8_peer_runs()
    s10_crt_bounds()
    s11_denial_mechanism_breakdown()
    print("wrote supplement table bodies to", TABLES_DIR)
