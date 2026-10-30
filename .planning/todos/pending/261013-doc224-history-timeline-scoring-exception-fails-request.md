---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §3.6 em-dash rule)
priority: low
area: quirk/dashboard/api/routes/scan.py (list_scans), quirk/dashboard/api/routes/trends.py (get_trends_timeline)
status: pending
resolves_phase: null
owner: "999.134"
---

# A scoring exception fails the whole scan-history or trend-timeline request instead of showing an em-dash

`merge.py:96-107` wraps per-segment scoring in try/except and records `None` (rendered `—`). `list_scans`
(`quirk/dashboard/api/routes/scan.py:1446`, scoring at `:1571`) and `get_trends_timeline`
(`quirk/dashboard/api/routes/trends.py:186`, scoring at `:212`) have no such handler, so one session whose scoring
raises turns the whole response into a 500 rather than one `—` point.

When fixed, update docs/report-interpretation.md §3.6 (Phase 199 em-dash paragraph).

## Feasibility & Effort

- **Verdict: CONFIRMED, effort S.** Handler present at `merge.py:99-107`; absent around `scan.py:1571` and `trends.py:212`.
- Fix: same try/except-and-None pattern plus a logged warning; add tests that monkeypatch `compute_readiness_score` to raise.
