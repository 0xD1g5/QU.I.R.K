---
phase: 75-api-cli-core-warnings
plan: 02
subsystem: dashboard-api
tags: [api, qramm, scan, validation, audit-closure, apcl-02]
requires:
  - quirk/dashboard/api/routes/scan.py
  - quirk/dashboard/api/routes/qramm.py
provides:
  - microsecond-safe scan_id time-window slice (D-04)
  - parsed-datetime list_scans grouping (D-05)
  - server-side multiplier validation before DB access (D-06)
  - clamp-before-round _compute_multiplier (D-07)
affects:
  - GET /api/scan/latest?scan_id=
  - GET /api/scans
  - POST /api/qramm/sessions/{id}/score
tech-stack:
  added: []
  patterns:
    - "datetime.fromisoformat + replace(microsecond=0) for parsed-datetime grouping"
    - "isinstance + bool subclass guard for numeric input validation"
key-files:
  created:
    - tests/test_api_scan_window.py
  modified:
    - quirk/dashboard/api/routes/scan.py
    - quirk/dashboard/api/routes/qramm.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions:
  - "RESEARCH C-2 + user override governs over CONTEXT D-06: multiplier range stays [0.8, 1.5]. NOT widened to [0.0, 4.0]."
  - "D-04 window implemented as [target_ts.replace(microsecond=0), target_ts.replace(microsecond=999_999)] — inclusive both sides, second-bounded."
  - "D-05 grouping moved from SQL strftime GROUP BY to Python-side dict keyed on parsed-datetime; sorted desc on the parsed key."
  - "D-06 detail string concatenates format_error('DASHBOARD-010') with the literal 'multiplier must be numeric in [0.8, 1.5]' phrase to satisfy both Phase 60 contract (QRK-DASHBOARD-010 token) and plan acceptance criteria."
  - "D-07 one-line order swap: round(clamp) -> clamp then round."
metrics:
  duration: 5m
  completed: 2026-05-15
---

# Phase 75 Plan 02: APCL-02 (API Correctness — WR-04/05/06/09) Summary

**One-liner:** Microsecond-safe scan_id window + parsed-datetime list_scans grouping + pre-DB multiplier validation + clamp-then-round _compute_multiplier; four audit rows closed via RED→GREEN TDD.

## What Was Built

### D-04 (WR-04) — `get_latest_scan` microsecond-precision window

`routes/scan.py:927-947` — replaced the `target_ts < scanned_at < target_ts + timedelta(seconds=1)` exclusive comparison with an inclusive `[window_start, window_end]` slice where `window_start = target_ts.replace(microsecond=0)` and `window_end = target_ts.replace(microsecond=999_999)`. SQLite stores `scanned_at` with microsecond resolution; this lets any of the 1,000,000 microsecond offsets within a second match an operator-supplied ISO timestamp at the same second.

### D-05 (WR-05) — `list_scans` parsed-datetime grouping

`routes/scan.py:795-820` — replaced `func.strftime("%Y-%m-%d %H:%M:%S", ...)` SQL grouping with Python-side dict grouping on parsed `datetime` keys (microsecond truncated via `replace(microsecond=0)`). Output sorted descending on the parsed key. Mirrors the `trends.py:41-60` precedent.

### D-06 (WR-06) — Server-side multiplier validation before DB access

`routes/qramm.py:351-369` — lifted the multiplier guard to function entry (already preceded `_get_session_or_404`, now strengthened with an `isinstance(multiplier, (int, float))` check plus an explicit `isinstance(multiplier, bool)` rejection — `bool` is a subclass of `int` in Python and would otherwise sneak through). Range stays `[0.8, 1.5]` per RESEARCH C-2 + user override. The 400 detail string contains both `[QRK-DASHBOARD-010] ...` (preserves Phase 60 SCORE-02 contract `test_qramm_multiplier.py`) and the literal `multiplier must be numeric in [0.8, 1.5]` phrase (plan acceptance criterion). DB session spy test (`test_score_session_out_of_range_does_not_hit_db`) asserts `db.query.call_count == 0` and `db.get.call_count == 0` when 400 is returned.

### D-07 (WR-09) — `_compute_multiplier` clamp-then-round

`routes/qramm.py:179-194` — swapped `max(0.8, min(1.5, round(value, 2)))` for `round(max(0.8, min(1.5, value)), 2)`. Parametrized tests verify boundary inputs (raw value 0.795 → 0.8, 1.505 → 1.5, 1.504 → 1.5) all stay within the declared band.

### Audit ledger flips

`AUDIT-TASKS.md` lines 189-194: WR-04, WR-05, WR-06, WR-09 flipped `| — | [ ] open |` → `| Phase 75 | [x] closed |`.

## Commits

| Commit | Type | Message |
|--------|------|---------|
| `fb9c69c` | test | RED: 9 test functions / 15 parametrized cases in tests/test_api_scan_window.py |
| `dacb578` | feat | GREEN: D-04..D-07 implementation in scan.py + qramm.py |
| `a49b87c` | docs | Audit ledger flips for WR-04/WR-05/WR-06/WR-09 |

## RESEARCH C-2 adjudication (CRITICAL)

CONTEXT D-06 reads "range [0.0, 4.0] with detail 'multiplier must be numeric in [0.0, 4.0]'". RESEARCH C-2 contradicts this: the canonical Phase 54 spec is `[0.8, 1.5]` (Pydantic `Field` constraint at `routes/qramm.py:94-100` + `_compute_multiplier` clamp at lines 179-185). The user prompt re-confirmed: "C-2 CRITICAL: multiplier range stays [0.8, 1.5] per Phase 54; fix is server-validate-before-DB, NOT range widening." This SUMMARY locks the decision: range is `[0.8, 1.5]`; D-06 detail uses the `[0.8, 1.5]` literal phrase. CONTEXT D-06 is superseded by RESEARCH C-2 + user override per `feedback_planner_context_precedence.md` memory.

## Verification

- `python -m compileall quirk/dashboard/api/routes/scan.py quirk/dashboard/api/routes/qramm.py` — clean
- `pytest tests/test_api_scan_window.py` — 15/15 pass
- `pytest tests/test_api_scan_window.py tests/test_qramm_multiplier.py tests/test_dashboard_scan_history.py tests/test_qramm_evidence_bridge.py` — 42 pass, 2 pre-existing failures (out of scope, see Deferred Issues)
- `grep -cE "api-cli-core/WR-(04|05|06|09).*Phase 75.*\[x\] closed" .planning/audit-2026-05-08/AUDIT-TASKS.md` == 4

## Deviations from Plan

**None within scope.** The plan, RESEARCH C-2, and user prompt were unambiguous after the C-2 adjudication. No Rule 1/2/3 auto-fixes were needed; no Rule 4 architectural decisions surfaced.

Implementation notes (not deviations):
- Plan suggested removing the existing post-DB multiplier check; the existing check was already pre-DB (lines 347-355 precede `_get_session_or_404`). Strengthened in place rather than relocated — minimal-diff aligned with the plan's "minimal diff preferred" guidance.
- Added an explicit `isinstance(multiplier, bool)` rejection on top of `isinstance(multiplier, (int, float))` because `bool` is a subclass of `int` in Python and would otherwise satisfy a naive numeric check (defense-in-depth, not a deviation).
- D-04 window computed as `replace(microsecond=999_999)` upper bound (not `+ timedelta(seconds=1)` exclusive) — matches the plan's "inclusive both sides `[start, end]`" specification literally, and avoids subtle off-by-one across the second boundary.

## Deferred Issues (pre-existing, out of scope)

Logged in `.planning/phases/75-api-cli-core-warnings/deferred-items.md`:

- `tests/test_dashboard_scan_history.py::test_compare_self` — asserts pre-Phase-68 detail format
- `tests/test_qramm_evidence_bridge.py::test_unconfirmed_excluded_from_score` — expects 200 from empty-answers /score (route correctly returns 422)
- `tests/test_broker_scanner_rabbitmq.py::test_enrich_rabbitmq_mgmt_success` — KeyError, unrelated subsystem

All three confirmed pre-existing via `git stash` baseline check before 75-02 changes.

## Known Stubs

None.

## Threat Flags

None — implementation hardens existing trust boundaries (T-75-05..T-75-08 in plan threat model) without introducing new surface.

## TDD Gate Compliance

- RED commit `fb9c69c` precedes GREEN commit `dacb578` ✓
- Initial RED run: 3 explicit failures tied to D-04 (microsecond inclusion) and D-06 (literal detail) ✓
- Final GREEN run: 15/15 pass ✓
- Note: D-05 and D-06 "before DB" tests passed at RED because the existing strftime grouping and existing pre-DB guard *partially* satisfied them. Tests are retained as regression guards.

## Self-Check: PASSED

- `tests/test_api_scan_window.py` — FOUND
- `quirk/dashboard/api/routes/scan.py` window edit at line 932 — FOUND (`window_end`, `replace(microsecond=999_999)`)
- `quirk/dashboard/api/routes/scan.py` D-05 grouping — FOUND (`groups: dict[datetime, int]`, `sorted(groups.keys(), reverse=True)`)
- `quirk/dashboard/api/routes/qramm.py` D-06 detail — FOUND (literal "multiplier must be numeric in [0.8, 1.5]")
- `quirk/dashboard/api/routes/qramm.py` D-07 clamp-then-round — FOUND (`max(0.8, min(1.5, value))` then `round(clamped, 2)`)
- Commits `fb9c69c`, `dacb578`, `a49b87c` — FOUND in `git log`
- AUDIT-TASKS.md WR-04/05/06/09 — 4 rows show `Phase 75 | [x] closed`
