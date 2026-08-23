# V10_CHANGELOG.md

V10 is a from-scratch reanalysis of the manuscript against a real raw-data
package supplied separately from any manuscript draft. V9.2 (preserved
unchanged at `paper_iot/V9.2/V9.2-single-column.pdf`) is the comparison
baseline. This changelog lists every changed numerical result, every
withdrawn or newly supported claim, and every remaining unresolved
limitation. See `analysis/CLAIM_DATA_MAP.csv` for the full 50-claim table
and `analysis/DATA_DISCREPANCIES.md` for the narrative explanation of each
material difference.

## Scope of work

- Branch: `claude/paper-v10-real-data-update-0g8kkl` (the session's assigned
  development branch; the task's own suggested name
  `paper/v10-real-data-update` was superseded by this explicit branch
  assignment).
- No V9.2 file was modified, renamed, or deleted. V9.2 exists in this
  repository for the first time as of this change (it was supplied as a PDF
  upload alongside the analyst data, not previously committed); it is
  stored verbatim at `paper_iot/V9.2/V9.2-single-column.pdf` (SHA-256
  `4a6842698b855e358c1386462aa4c4743b0979ff77516efd1e9e0469a80645cb`,
  unchanged from the supplied file).
- No unrelated repository directory (`data/`, `gateway/`, `esp32/`,
  `chaincode/`, `contracts/`, `network/`, `results/`, `tests/`, `tla/`,
  `dashboard/`, `frontend/`, `backend/`, `docs/`, `scripts/`) was
  reorganized, deleted, or modified. All V10 output lives under
  `paper_iot/V10/`.

## Changed numerical results (V9.2 → V10 verified)

See the table in `analysis/DATA_DISCREPANCIES.md` Section 4 for the full
list with explanations. Summary:

| # | Result | V9.2 | V10 |
|---|---|---|---|
| 1 | Security-oracle confirmed/discrepant | 2,149/517 (80.6%/19.4%) | 852/1,814 (32.0%/68.0%) — oracle file absent, V10 uses a disclosed replacement |
| 2 | 4-vs-32-peer span 90% CI | [-9.77, 0.22] ms | [4.03, 4.60] ms |
| 3 | Throughput model R² | 0.206 | 0.317 |
| 4 | Throughput % difference (mean/SD/range) | 9.6% / 1.6 / 7.9-12.4% | 9.4% / 1.18 / 6.9-10.7% |
| 5 | Quantization max/RMS error | 0.37% / 0.21% | 0.366% / 0.215% (bit-truncating quantiser, method now documented) |
| 6 | Revocation delayed count/pct | 59 / 29.5% | 57 / 28.5% |
| 7 | Revocation trace span | 58 days | 55 days |
| 8 | Released rows/traces | 377,414 / 10 | 370,118 / 12 CSV traces + provenance logs + ledger sample |
| 9 | Grant-rate range (CheckAccess cells) | "uniformly 91-93%" | 90.6-93.1% (35 cells; 36th cell is the automated sensor-write channel at 100%, reported separately) |
| 10 | Throughput condition-effect magnitude | 6.03 TPS | 5.65 TPS |
| 11 | Throughput interaction magnitude | 0.007 TPS/client | 0.002 TPS/client |
| 12 | HRBAC decline from peak to 100 clients | 15.3% | 14.1% |
| 13 | 4-vs-32 total-latency diff / CI | 393.0 ms [374.5, 411.4] | 391.0 ms [388.3, 393.8] (tighter interval; real per-run variance is smaller) |

## Withdrawn claims

- **Revocation stage-duration statistics** (CRL publication mean 60.4 s;
  gossip propagation mean 4.21 min). No duration field exists in the real
  revocation-stage trace. Reported only as stage counts and delayed
  proportion in V10.
- **Corrected-implementation existence.** V9.2 implies (via tagged releases,
  regression tests, and a "confirmed with a throwaway copy" claim) that a
  working corrected chaincode/firmware/gateway exists. It does not exist in
  this repository. V10 withdraws every claim that treats the correction as
  built, tested, or measured, and restates each as "specified and
  arithmetically checked" only.
- **`policy-requirements.json`-based oracle results as previously stated.**
  The specific 2,149/517 split cannot be reproduced because the file is
  absent; V10 reports its own disclosed, differently-constructed oracle's
  results instead, clearly labelled as such.

## Newly supported claims

- **Counterbalancing design independently confirmed from the run manifest.**
  V9.2 asserted a two-complementary-Latin-square design; V10 is the first
  version to actually reconstruct and verify this from `run_id` and
  `start_timestamp` fields in the real run manifest
  (`03_peer_scaling.py::counterbalancing_check`), rather than stating it as
  given.
- **Signature-message mismatch and fail-open behaviour confirmed by direct
  source inspection.** V10 quotes the exact code (`gateway/gateway.py`
  `verify_signature`/`_signature_payload`; `esp32/main/signing.c`) rather
  than describing the defect only in prose, and confirms the struct-vs-ASCII
  mismatch and the `if reading.signature is None: return True` fail-open
  line directly.
- **CRT bound-violation finding shown robust to an undocumented calibration
  gap.** V10 discovers and states that no ADC-to-percent calibration
  constant exists anywhere in the repository, then shows the 100%
  bound-exceedance finding holds under both possible calibration polarities.
- **Repository-wide absence of the corrected implementation and analysis
  pipeline**, documented for the first time in `DATA_DISCREPANCIES.md` and
  `MISSING_DATA.md`.

## Affected manuscript sections

Abstract; Introduction (contribution list); Section 4.5 (new); Sections
6.1-6.9 (all values now macro-driven); Section 7 (Discussion, corrected
framing throughout); Table 1, 3, 4, 5 (values and framing updated); Figures
3 and 4 (regenerated from real data); Data Availability statement (repo-tag
and corrected-package language corrected); Ethics section (unchanged in
substance, factual wording preserved per the source ethics documentation).

## Changed figures

- Figure 3 (throughput vs. concurrency): regenerated from
  `raw/experiments/throughput_runs.csv`; "saturation" label replaced with
  "observed peak" language in the caption per the task's wording
  requirement.
- Figure 4 (peer-count latency): regenerated from
  `raw/experiments/peer_scaling_transactions.csv`; now shows all 32
  individual run-level points colour-coded by counterbalancing block, plus
  group means and 95% CIs, and a separate P95 panel.

## Changed tables

- Table 1 (policy-table): "Corrected" column reworded to state the fix is
  specified, not implemented.
- Table 3 (latency accounting): values regenerated from real run-level
  means.
- Table 4 (validity classification): "corrected-code performance" language
  updated to note no corrected code exists in this repository.
- Table 5 (limitations): L6 reworded to state the absence of a corrected
  implementation as the limitation, not merely its unevaluated performance.

## Remaining unresolved limitations (unchanged from V9.2, verified still open)

L1 (timer boundaries), L2 (peer multiplicity / external validity), L3
(throughput campaign order / saturation), L4 (authorization-corpus
coverage), L5 (revocation observability). L6 is **strengthened**: not only
is corrected-version performance unevaluated, but no corrected artifact
exists at all in this repository.

## Build and reproducibility

- `paper_iot/V10/analysis/scripts/run_all.sh` regenerates every JSON output,
  the LaTeX macro file, and both figures from the raw-data package.
- The manuscript (`paper_iot/V10/manuscript/main.tex`) and supplement
  (`paper_iot/V10/supplement/supplementary_material.tex`) both compile
  cleanly with `pdflatex` + `bibtex` (elsarticle, single-column preprint
  class). A double-column build was attempted and abandoned: the
  `longtable` environment used for Table 5 (limitations) is incompatible
  with `elsarticle`'s `twocolumn` option (a hard LaTeX limitation, not a
  content issue); producing a two-column variant would require redesigning
  that table, which was out of scope for this pass.
