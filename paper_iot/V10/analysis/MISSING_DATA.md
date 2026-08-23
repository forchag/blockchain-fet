# MISSING_DATA.md

Fields, files or measurements that V9.2 referenced or implied but that are
**not present** in the analyst's real-data package or the repository, with
the consequence for V10.

| Missing item | Referenced where | Consequence in V10 |
|---|---|---|
| `analysis/derive_results.py` (V9.2's claimed analysis pipeline) | V9.2 Sec. 5.6 | Not present in this repository. V10 builds a new pipeline (`paper_iot/V10/analysis/scripts/`) from scratch against the real data. |
| `chaincode/policy-requirements.json` (independent role/operation oracle) | V9.2 Sec. 6.6, 6.9.1 | Not present. V10 discloses and constructs its own oracle (`06_security_oracle.py`), explicitly flagged as a V10 construction, not a released artifact. |
| `chaincode/hrbac-corrected/`, corrected firmware, corrected gateway verifier | V9.2 Sec. 4.2, 6.9.1-6.9.3 | Not present anywhere in the repository (confirmed by `find`/`grep` across the full tree). V10 reports the corrections as specified and arithmetically checked, not implemented or measured (Sec. 4.5 of the manuscript). |
| `v09-deployed-historical` / `v09-corrected` git tags | V9.2 Data Availability | Repository history contains a single commit at the time of this analysis; no such tags exist. V10's Data Availability statement reports this directly. |
| ADC-to-percent calibration constant for `soil_moisture` | Implied by V9.2 Sec. 6.9.2's packed-value reconstruction | Not present in firmware, gateway, or backend code. V10 states the gap and reports the CRT bound-violation finding under both polarity assumptions (Sec. 6.9.2 of the manuscript; `05_crt_quantization.py`). |
| Per-stage start/end timestamps for revocation lifecycle stages | Implied by V9.2's CRL-publication (60.4 s) and gossip (4.21 min) duration statistics | Only a single `stage_timestamp` per stage row exists. V10 withdraws the specific duration statistics (Supplement S9) and reports only stage counts and delayed-proportion, which do not require a duration field. |
| Episode/correlation identifier linking revocation stages | V9.2 Sec. 6.9.4 (identifies the gap but implies `event_id` could be it) | `event_id` maps 1:1 to `cert_user_id` in this trace but cannot disambiguate repeated revocations of the same subject; V10 confirms this explicitly rather than assuming `event_id` solves the gap. |
| Pre-run host CPU/memory/disk/CouchDB-document-count telemetry for the peer-scaling campaign | V9.2 Sec. 5.2 (states this is absent) | Confirmed absent in the real package too; V10 repeats this limitation (L2) rather than assuming later data filled it in. |
| Positive (permitted) authorization test corpus | V9.2 Sec. 6.6 (L4) | The scripted security corpus (8,000 rows) contains only denied requests. Confirmed still true in the real package; L4 in Table 5 is unchanged. |
| Zone/resource-ownership attributes on the 517 (deployed-oracle) discrepant boundary-attempt records | V9.2 Sec. 6.6 | Confirmed absent; V10 reports the discrepancy without resolving it, as V9.2 did. |

No manuscript claim in V10 relies on an item listed above being present; where
V9.2 implied such an item existed, V10 states plainly that it does not and
adjusts the claim accordingly (see `DATA_DISCREPANCIES.md` and
`V10_CHANGELOG.md`).
