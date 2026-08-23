# V10_PREMORTEM.md

Seven-reviewer acceptance check, run before finalizing V10. Each reviewer's
likely decision, remaining concerns, and the exact V10 response are given
below. This is a self-critique exercise, not a claim of guaranteed
acceptance.

---

## R01 — Editor and journal scope

**Likely decision:** Accept for review (minor revision likely at review stage).

**Remaining major concerns:**
- None blocking. The paper's evidence separation (field vs. controlled vs.
  scripted vs. audit) is unusually explicit for this journal's typical
  submissions, which is a strength for *Internet of Things*'s scope.

**Remaining minor concerns:**
- The title and framing emphasize "postmortem," which is somewhat unusual
  framing for this journal; the abstract and introduction should make clear
  in the first 100 words that this is a measurement + audit study, not a
  narrative retrospective. (Addressed: abstract opens with the measurement
  claim, not the postmortem framing.)
- Novelty vs. Idrissi & Palmieri (2024) and Abang et al. (2024) should be
  stated crisply.

**V10 response:** Related Work Section 2.2 explicitly differentiates from
both; Introduction states RQ1-RQ3 up front. No reanalysis needed; wording
only.

**Requires:** wording (resolved).

---

## R02 — Experimental systems reviewer

**Likely decision:** Minor revision.

**Remaining major concerns:**
- Is the peer-multiplicity counterbalancing design actually verified from
  the run manifest, or merely asserted? **Resolved:** `03_peer_scaling.py`
  reconstructs the two-complementary-Latin-square design from `run_id` and
  `start_timestamp` and reports the result in `03_design_check.json`
  (`each_config_occupies_each_position_exactly_twice: true`).
- Is "run" genuinely the right experimental unit, or could ledger/CouchDB
  state carry over between runs, inflating apparent stability? **Not fully
  resolved** — the released manifest does not record pre-run system state
  (Limitation L2), so state-carryover cannot be ruled out. V10 states this
  directly rather than assuming independence.
- Logical vs. physical peers: is this conflated anywhere in the text?
  Checked: every mention of the peer-multiplicity experiment in the main
  text qualifies "logical" and states the four-fixed-host constraint.

**Remaining minor concerns:**
- Throughput campaign's single-session design limits generality; addressed
  explicitly in L3 and the Discussion's "peers buy latency, not capacity"
  framing.

**V10 response:** Section 5.2 (Methodology) and Section 6.4 both state the
counterbalancing verification method and its result; Limitation L2 remains
open and is not overstated as resolved.

**Requires:** reanalysis (done — counterbalancing verification); wording for the remaining state-carryover caveat.

---

## R03 — Statistical reviewer

**Likely decision:** Minor revision, possibly major if the reviewer weighs the security-oracle mapping change heavily.

**Remaining major concerns:**
- The security-oracle confirmed/discrepant split (32.0%/68.0%) is entirely
  dependent on a mapping V10 constructs itself, not an independent released
  artifact. A statistically careful reviewer will ask whether this
  statistic should be reported with a caveat this strong, or omitted.
  **V10 response:** the statistic is retained but heavily caveated in
  Section 6.6 and flagged again in Table 5 (L4) and the Discussion; an
  alternative would be to drop the confirmed/discrepant split entirely and
  report only the scored-attempt total (2,666), which is mapping-independent.
  We judge retaining it with strong caveats is more informative than
  omitting it, but flag this as a defensible point of disagreement a
  reviewer might raise.
- Does the block-design model (peer count + block + serial position) versus
  the joint regression (log2(peers) + centred sequence) give consistent
  conclusions? **Resolved:** both are reported side by side in
  `03_peer_scaling_results.json`; both find peer count significant and
  order/block not significant.
- Are p-values reported correctly (no p=0.000)? **Resolved:** macros use
  "$<$0.001" formatting wherever the true p-value is below that threshold.

**Remaining minor concerns:**
- TOST margin selection is explicitly labelled exploratory/post-hoc, per
  the task's requirement; confirmed present in Sections 5.4 and 6.1.2.
- Multiple-comparisons correction (Holm-Bonferroni) for the ten throughput
  levels is applied and reported (10/10 remain significant).

**V10 response:** As above; the security-oracle caveat is the one place we
recommend the handling editor/reviewers weigh in, since reasonable people
could disagree about whether to report or withhold a mapping-dependent
statistic.

**Requires:** wording (done) plus an editorial judgment call flagged for reviewers.

---

## R04 — Hyperledger Fabric reviewer

**Likely decision:** Minor revision.

**Remaining major concerns:**
- Physical vs. logical peer distinction: verified consistent throughout
  (single `host_id` for all 32 peer-scaling runs, stated explicitly in
  Methodology, Results and Discussion).
- Saturation language: checked every instance of "peak"/"saturation" in the
  manuscript; "observed peak" is used throughout, "saturation" only appears
  when explicitly attributed to Thakkar et al. (2018) as a candidate
  explanation, never asserted as established for this deployment.
- Endorsement/ordering/validation attribution: the manuscript explicitly
  states it cannot decompose the "remaining latency" into these Fabric
  stages (L1), consistent with the single end-to-end timer available.

**Remaining minor concerns:**
- A Fabric-literate reviewer may ask why endorsement policy details
  (zone-local peers only) aren't varied as an independent factor; this is
  out of scope and stated as such (future work implied by L1/L2).

**V10 response:** No changes needed beyond what is already in the
manuscript; this reviewer's concerns are pre-addressed by the existing
Limitations table.

**Requires:** none (pre-addressed).

---

## R05 — Security reviewer

**Likely decision:** Minor-to-major revision, depending on how strictly the reviewer weighs the missing positive-test corpus and the disclosed (not released) oracle.

**Remaining major concerns:**
- No permitted-request (positive) test corpus exists; false-denial rate
  cannot be estimated. **Not resolved** (L4, honestly stated, not
  glossed over).
- The independent oracle is built by V10 itself, not an artifact
  independent of the authors. **Explicitly disclosed** in Section 6.6 and
  Table 1's footnote; not presented as an independent third-party
  validation.
- Mutation testing, corrected positive/negative tests: **do not exist**
  in this repository (Section 4.5); V10 does not claim they were run.

**Remaining minor concerns:**
- "All attacks were correctly refused" language: checked, not used;
  V10 uses "All 8,000 scripted requests were refused through 6 recorded
  denial mechanisms," matching the task's required phrasing.

**V10 response:** Security claims are already appropriately bounded. A
security reviewer may still request an independently-authored oracle file
as a condition of publication; V10 cannot manufacture that without new data
collection, which is outside this task's scope (flagged in the final report
to the user as a possible necessary follow-up).

**Requires:** new data (the positive-test corpus and an independently-authored oracle are the two items that would need genuinely new data collection, not reanalysis).

---

## R06 — Embedded/cryptography reviewer

**Likely decision:** Minor revision.

**Remaining major concerns:**
- CRT bound recomputation: verified against the actual compiled constants
  in `esp32/main/crt_encode.h`/`.c` (moduli 97/101/103, `CRT_MAX_VALUE`),
  not re-derived from prose. Confirmed exact match.
- Quantization error claim: **initially a concern** — V9.2's 0.37%/0.21%
  figures had no stated derivation method. **Resolved** in V10 by
  identifying that a bit-truncating quantiser (the natural embedded
  implementation) reproduces these figures almost exactly, and stating the
  method explicitly (`05_crt_quantization.py::quantization_error`).
- Calibration gap for `soil_moisture`: **flagged as a real limitation**,
  not hidden; the 100%-bound-exceedance finding is shown robust to it, but
  the exact numerical min/max packed values are explicitly calibration-
  dependent.
- Signature construction: verified directly against `signing.c` and
  `gateway.py`; the nonstandard prehash and the ASCII/binary message
  mismatch are both confirmed from source, not merely asserted.

**Remaining minor concerns:**
- "Legacy-compatible corrected verification" language checked: used
  correctly, no claim of a standards-based Ed25519/Ed25519ph migration.

**V10 response:** All concerns addressed by direct source verification
rather than reliance on the prior draft's prose.

**Requires:** reanalysis (done).

---

## R07 — Reproducibility/ethics reviewer

**Likely decision:** Minor revision, contingent on the commit-SHA placeholder being resolved before camera-ready.

**Remaining major concerns:**
- Data Availability statement currently contains a `[ARTIFACT_COMMIT_SHA]`
  placeholder, per explicit task instruction not to invent a commit SHA.
  **This must be filled in before submission**, once the final commit is
  made and, if authorized, pushed.
- No Zenodo DOI: consistent with the task's explicit instruction not to
  invent one; provisional wording used.
- Ethics wording: uses the task-supplied preferred wording (FET-CE-2025-014)
  verbatim, since this refers to real ethics-approval documentation the
  authors hold; V10 could not independently re-verify this reference number
  against a primary ethics-office record (outside this session's access),
  and states it as given rather than independently confirmed.
- PII scan: performed directly on the raw-data package (`DATA_QUALITY_REPORT.md`
  cross-check); no names, emails, phone numbers or coordinates found. The
  ethics-section wording was adjusted from the task's suggested text to
  remove an unverifiable claim ("coordinate columns... unreliable") since no
  coordinate column exists in this release at all — the real data provide a
  stronger privacy posture than the suggested wording assumed.

**Remaining minor concerns:**
- CRediT statement retained from the presumed real authorship of the prior
  draft; not independently verifiable by this analysis.

**V10 response:** All resolvable items resolved; the commit-SHA placeholder
is an intentional, task-mandated gap requiring a human action (commit and,
if authorized, push) before the placeholder can be filled.

**Requires:** wording (done) + a follow-up action (insert real commit SHA once available; this is explicitly outside what a reanalysis session should do unilaterally, per the task's instruction not to invent a SHA).

---

## Summary

| Reviewer | Likely decision | Blocking items requiring new data | Items resolved by wording | Items resolved by reanalysis |
|---|---|---|---|---|
| R01 Editor | Accept | none | title/abstract framing | — |
| R02 Systems | Minor | none (L2 state-carryover honestly open) | — | counterbalancing verification |
| R03 Statistics | Minor/Major | none | p-value formatting | block model, oracle mapping caveat |
| R04 Fabric | Minor | none | — | (pre-addressed) |
| R05 Security | Minor/Major | positive-test corpus, independent oracle | denial-refusal wording | — |
| R06 Crypto | Minor | none | — | quantization method, CRT/signature verification |
| R07 Reproducibility | Minor | commit SHA (post-hoc, mechanical) | ethics wording | PII scan |

**Overall:** V10 is scientifically defensible for submission with the
caveats above disclosed rather than hidden. The two items that would
require genuinely new data collection (a positive authorization-test
corpus and an independently-authored policy oracle) are real, disclosed
gaps, not fabricable from the existing package. No reviewer concern
identified above was resolved by adjusting wording alone where reanalysis
was actually required, and no reanalysis was invented to make a number look
more favorable than what the real data support.
