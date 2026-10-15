---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §2/§3.6 consequence ceilings)
priority: high
area: quirk/dashboard/api/routes/trends.py, quirk/intelligence/trends.py, quirk/dashboard/api/routes/merge.py, quirk/merge/scan.py
status: pending
resolves_phase: 228
---

# Trend timeline and multi-sensor merge scores ignore the CRITICAL/HIGH consequence ceilings

The trend, timeline and merge scores are computed from `build_evidence_summary(endpoints)` with no findings, so
under scoring v3 the consequence ceilings (which now move the number, not only the band) never bind there:

- `quirk/dashboard/api/routes/trends.py:211-212` `evidence = build_evidence_summary(eps)` / `compute_readiness_score(evidence)` (timeline).
- `quirk/intelligence/trends.py:217-218` same, for `/api/trends`.
- `quirk/dashboard/api/routes/merge.py:96-97` and `:124-125` `build_evidence_summary(..., findings=None)` (per-segment and overall).
- `quirk/merge/scan.py:246-247` `build_evidence_summary(union, findings=None)`.

The "D-07 (184.4): intentionally findings-less" comments justify this by saying no band is read; that premise was
safe when CRITICAL only capped the band, but v3 caps the score itself. Probe `gc3-r3-f1-*` (one expired certificate):
headline score 32 on the Executive page, trend score 78 for the same scan.

When fixed, update docs/report-interpretation.md §2 (ceiling paragraph) and §3.6 "Not every dashboard score applies the finding ceilings".

## Feasibility & Effort

- **Verdict: CONFIRMED, effort M.** The four call sites above pass no findings (re-verified 2026-10-13).
- Fix: derive findings per session the way `list_scans` does (`quirk/dashboard/api/routes/scan.py:1554` `_derive_findings(eps)`,
  `:1568-1571` evidence with findings then `compute_readiness_score`).
- Cost: the timeline is O(sessions) and finding derivation runs per session; check timeline latency on a large DB.
- Unknown: whether the merge union should derive findings per sensor or over the union.
