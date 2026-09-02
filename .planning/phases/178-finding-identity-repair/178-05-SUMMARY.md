---
phase: 178-finding-identity-repair
plan: 05
subsystem: intelligence-trends
tags: [trends, intelligence, api, ident-02, non-vacuity]

# Dependency graph
requires: ["178-02"]
provides:
  - "quirk/intelligence/trends.py::compute_trend_report — (host, port, protocol) match key, severity_transitions, new_total/resolved_total (IDENT-02 fix)"
  - "quirk/dashboard/api/schemas.py::TrendReportResponse — severity_transitions, new_total, resolved_total wire fields"
affects: [178-06, 178-07, 179, 180, 181]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Severity carried alongside the match key as a dict (host,port,protocol) -> severity instead of embedded in the key tuple, so a key change can be detected (severity_transitions) without corrupting endpoint identity."
    - "Reworded RED-era test docstrings/module docstring immediately upon flipping GREEN, per RETROSPECTIVE.md Top Lesson 24 — no 'RED today'/'xfail' narration left behind describing a bug that no longer exists."

key-files:
  created: []
  modified:
    - quirk/intelligence/trends.py
    - quirk/dashboard/api/routes/trends.py
    - quirk/dashboard/api/schemas.py
    - tests/test_trends_non_vacuity.py
    - tests/test_intelligence_trends.py
    - tests/test_dashboard_trends.py

key-decisions:
  - "_count_by_bucket's signature changed from (keys) to (keys, sev_map) since severity is no longer embedded in the key tuple. Its one external caller — quirk/dashboard/api/routes/trends.py's /api/trends/timeline endpoint — was updated in the same commit as Task 1 (not deferred to Task 2) because leaving it unfixed would have been a blocking regression (Rule 3), not an in-scope Task 2 change."
  - "Removed all literal 'xfail' substring occurrences (not just the markers) from tests/test_trends_non_vacuity.py's prose, including individual test docstrings that said 'RED today by AttributeError' — those sentences described a bug that no longer exists after this plan lands, and the plan's own acceptance grep (`grep -c 'xfail'` -> 0) required it."
  - "test_uat_31_trends_two_sessions_flat_wire_format was extended (not left alone) to include the three new wire-format keys in its required_keys presence check, even though the test only asserts presence-not-exhaustiveness (so it would have passed either way) — matches the plan's Task 2 acceptance intent that the wire-format test reflect the new contract."

requirements-completed: []  # IDENT-02 spans plans 02/05/07 — NOT closed by this plan. Do not mark complete.

# Metrics
duration: 35min
completed: 2026-09-02
---

# Phase 178 Plan 05: Trend Non-Vacuity Fix Summary

**Dropped `severity` from `compute_trend_report`'s match key (now `(host, port, protocol)`), removed the `severity is not None` filter that emptied every real-scan delta by construction, and added `severity_transitions`/`new_total`/`resolved_total` so D-03's partial-remediation signal survives the key change as an explicit transition record instead of a double-count — threaded through to the `/api/trends` wire format with zero frontend churn.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-09-02
- **Tasks:** 2 completed
- **Files modified:** 6 (2 production trend files, 1 API schema file, 3 test files)

## Live-DB measurement (closes RESEARCH.md Assumption A1 with a number)

```
$ .venv/bin/python -c "import sqlite3;c=sqlite3.connect('output/quirk.db');print('rows',c.execute('select count(*) from crypto_endpoints').fetchone(),'protocol_null',c.execute('select count(*) from crypto_endpoints where protocol is null').fetchone(),'severity_nonnull',c.execute('select count(*) from crypto_endpoints where severity is not null').fetchone())"
rows (30,) protocol_null (0,) severity_nonnull (0,)
```

Confirms Plan 178-02's measurement: `crypto_endpoints` has 30 rows, 0 non-NULL `severity`,
**0 NULL `protocol`** (fully populated). Dropping `severity` from the match key and keying on
`(host, port, protocol)` genuinely revives `compute_trend_report` on live data — `protocol` is
not itself NULL-prone, so the fix does not simply move the vacuity to a second empty column.

## Accomplishments

### Task 1 — Re-key the delta, add severity transitions and severity-agnostic totals

- `quirk/intelligence/trends.py`: match key for the finding delta is now `(host, port,
  protocol)`. `current_sev`/`previous_sev` dicts (`key -> Optional[str] severity`) replace the
  bare 4-tuple sets; `current_keys`/`previous_keys` are `set(current_sev)`/`set(previous_sev)`.
  The `ep.severity is not None` filter is gone from both sides.
- `SeverityTransitionItem` dataclass added (`host, port, protocol, previous_severity,
  current_severity`). Computed from `current_keys & previous_keys` where the two sessions'
  severities differ, sorted by `(host, port)` for deterministic output. This is D-03's original
  intent — a HIGH→MEDIUM change at an unchanged endpoint must be visible — now served without
  corrupting the endpoint identity key.
- `TrendReport` gained `severity_transitions: List[SeverityTransitionItem]`, `new_total: int`,
  `resolved_total: int` (all with defaults, both construction sites — D-06 early return and the
  final return — updated explicitly, both set to `0` in the D-06 path).
- `_count_by_bucket(keys)` became `_count_by_bucket(keys, sev_map)` — bucket lookup now goes
  through the severity map instead of unpacking a 4-tuple. **Both call sites inside trends.py**
  updated (`new_counts`/`resolved_counts`), **plus the one external caller**
  (`quirk/dashboard/api/routes/trends.py`'s `/api/trends/timeline` endpoint, which built its own
  4-tuple keys) — updated to build a matching 3-tuple key list + `sev_map` so the signature
  change did not silently break that endpoint. This external-caller fix was not explicitly
  named in the plan's Task 1 file list but is a direct, mechanical consequence of the signature
  change named in the interfaces section (Rule 3 — blocking fix).
- `_sample_findings`'s membership filter changed from the 4-tuple to the 3-tuple; sort/cap
  logic (D-08) untouched.
- Docstring rewritten: states the new key, explicitly retires the old "severity included
  intentionally" sentence, and explains how D-03's intent moved to `severity_transitions`.
  D-04/D-05/D-06/D-08/D-12/D-13 are each re-stated as unchanged.
- Removed the four `xfail(strict=True)` markers in `tests/test_trends_non_vacuity.py`. Also
  reworded every "RED today"/"xfail" narration sentence in that file's module docstring and
  individual test docstrings — per RETROSPECTIVE.md Top Lesson 24, a comment describing a bug
  that no longer exists must not survive the fix that closed it.
- Updated `tests/test_intelligence_trends.py::test_severity_change_surfaces` to assert the new
  transition-based behavior (`resolved_high == 0`, `new_medium == 0`, exactly one matching
  `severity_transitions` entry) instead of the old double-count, with an added docstring
  sentence explaining the D-03 signal's new home.

### Task 2 — Thread the new fields through the API response

- `quirk/dashboard/api/schemas.py`: added `SeverityTransitionResponse` (mirrors
  `SeverityTransitionItem`'s five fields) and `severity_transitions: List[SeverityTransitionResponse]
  = Field(default_factory=list)`, `new_total: int = 0`, `resolved_total: int = 0` on
  `TrendReportResponse`.
- `quirk/dashboard/api/routes/trends.py::_to_response` now maps all three new fields. Verified
  the 0-session early return (`TrendReportResponse()`) still constructs successfully with the
  new defaults.
- `tests/test_dashboard_trends.py`'s `test_uat_31_trends_two_sessions_flat_wire_format` extended
  to require the three new top-level wire keys in its presence check.
- Zero `src/dashboard/` files touched — confirmed via `git diff --name-only | grep -c
  '^src/dashboard/'` → `0`. Frontend surfacing of `severity_transitions`/`new_total`/
  `resolved_total` is Phase 181's scope.

## Invariant confirmation (D-04/D-05/D-06/D-08/D-12/D-13)

| Decision | How confirmed |
|----------|----------------|
| D-04 (scan_error rows excluded from finding delta keys; current-session errored hosts excluded from both sides) | `current_error_hosts` computation and its use in `previous_sev`'s filter unchanged in shape; `tests/test_intelligence_trends.py::test_scan_error_excluded_from_delta` still passes. |
| D-05 (scan-error counts computed independently; INFO/None severity excluded from bucket counts) | `cur_err`/`prev_err` computation block untouched; `_bucket_for_severity` / `_SEVERITY_BUCKET` untouched; `test_scan_error_counts_surfaced` and the new `test_severity_bucket_counts_still_work_when_severity_is_populated` guard both pass. |
| D-06 (null-delta single-session response when `previous_ts is None`) | Early-return block unchanged except two new fields explicitly set to `0`; existing single-session tests in `tests/test_intelligence_trends.py` and `tests/test_dashboard_trends.py` still pass. |
| D-08 (sample arrays capped at 5, sorted severity desc then host/port asc) | `_sample_findings`'s sort key and `[:5]` cap untouched — only its membership filter's tuple shape changed. |
| D-12 (pure function, no `datetime.now()` inside) | No new call to any clock function was added; `current_ts`/`previous_ts` remain caller-supplied. |
| D-13 (NULL `scanned_at` rows excluded from session fetches) | `_fetch_session_endpoints` untouched by this plan. |

## Task Commits

1. **Task 1: Re-key the delta, add severity transitions and severity-agnostic totals** —
   `ac851e7e` (feat). Includes the blocking `_count_by_bucket` external-caller fix in
   `quirk/dashboard/api/routes/trends.py` (Rule 3) since it is a direct, mechanical consequence
   of the signature change and leaving it unfixed would have broken `/api/trends/timeline`.
2. **Task 2: Thread the new fields through the API response** — `840dba9d` (feat).

## Files Created/Modified

- `quirk/intelligence/trends.py` — match key re-keyed to `(host, port, protocol)`,
  `SeverityTransitionItem` added, `TrendReport.severity_transitions`/`new_total`/`resolved_total`
  added, docstring rewritten.
- `quirk/dashboard/api/routes/trends.py` — `_to_response` maps the three new fields;
  `/api/trends/timeline`'s `_count_by_bucket` call site updated for the new signature.
- `quirk/dashboard/api/schemas.py` — `SeverityTransitionResponse` model added,
  `TrendReportResponse` gained the three new fields with backward-compatible defaults.
- `tests/test_trends_non_vacuity.py` — 4 `xfail(strict=True)` markers removed; stale RED/xfail
  prose reworded throughout.
- `tests/test_intelligence_trends.py` — `test_severity_change_surfaces` updated to assert the
  new transition-based behavior.
- `tests/test_dashboard_trends.py` — wire-format test's `required_keys` extended.

## Verification Evidence (verbatim)

```
$ .venv/bin/pytest tests/test_trends_non_vacuity.py tests/test_intelligence_trends.py tests/test_dashboard_trends.py -q
........................                                                 [100%]
24 passed in 0.73s

$ .venv/bin/pytest tests/test_trends_non_vacuity.py -q
.....                                                                    [100%]
5 passed in 0.18s

$ grep -c '(ep.host, ep.port, ep.protocol, ep.severity)' quirk/intelligence/trends.py
0
$ grep -c 'ep.severity is not None' quirk/intelligence/trends.py
0
$ grep -c 'xfail' tests/test_trends_non_vacuity.py
0
$ grep -c 'severity_transitions' quirk/intelligence/trends.py
5
$ grep -c 'severity_transitions' quirk/dashboard/api/schemas.py
1
$ grep -c 'severity_transitions' quirk/dashboard/api/routes/trends.py
2
$ .venv/bin/python -c "from quirk.dashboard.api.schemas import TrendReportResponse as R; r=R(); print(r.new_total, r.resolved_total, r.severity_transitions)"
0 0 []
$ git diff --name-only | grep -c '^src/dashboard/'
0
```

Notify/dispatcher regression check (reads `TrendReport` attributes, not positional construction —
confirmed by grep before editing; no production file in `quirk/notify/` touched):

```
$ .venv/bin/pytest tests/test_notify_dispatcher.py tests/test_notify_dispatcher_isolation.py tests/test_notify_payload_whitelist.py -q
........................................                                 [100%]
40 passed in 0.37s
```

`tests/test_notify_payload.py` does not exist in this repo — no such file to run (acceptance
criteria's documented fallback).

Baseline check — `DEFER-172-01` unchanged, no new/different failure:

```
$ .venv/bin/pytest tests/test_skip_registry.py -q
FAILED tests/test_skip_registry.py::test_no_unregistered_skips - Failed: Unre...
1 failed in 0.42s
```

`python -m compileall` on all touched files: OK (no syntax errors).

## Decisions Made

- `_count_by_bucket`'s external caller (`/api/trends/timeline`) was fixed in Task 1's commit
  rather than deferred, since the plan's own Task 1 interfaces section calls out `_count_by_bucket`
  as one of the four sites that must move in lockstep, and this route file is the one place
  outside `trends.py` that calls it directly.
- Removed every literal `xfail` substring (not just the pytest markers) from
  `tests/test_trends_non_vacuity.py`, including in individual test docstrings ("RED today by
  AttributeError..."), to satisfy both the plan's grep-based acceptance criterion and
  RETROSPECTIVE.md Top Lesson 24 (stale comments outlive the bug they describe).

## Deviations from Plan

**1. [Rule 3 - Blocking fix] Updated `/api/trends/timeline`'s `_count_by_bucket` call site**
- **Found during:** Task 1
- **Issue:** Changing `_count_by_bucket`'s signature from `(keys)` to `(keys, sev_map)` (required
  by the plan's design) breaks its one external caller in
  `quirk/dashboard/api/routes/trends.py`'s `/api/trends/timeline` endpoint, which still built
  4-tuple keys and called `_count_by_bucket(keys)` with one argument.
- **Fix:** Changed the call site to build a 3-tuple `keys` list plus a matching `sev_map` dict,
  then call `_count_by_bucket(keys, sev_map)`.
- **Files modified:** `quirk/dashboard/api/routes/trends.py`
- **Commit:** `ac851e7e`

No other deviations — plan executed as written.

## Issues Encountered

None. All 5 tests in `tests/test_trends_non_vacuity.py` came out GREEN on first run after the
fix (4 previously-xfailed guards + 1 always-green regression guard); the one pre-existing
`test_severity_change_surfaces` failure (expected, since it asserted the old double-count
behavior) was updated per the plan's explicit instruction, not treated as a regression.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

IDENT-02 is intentionally NOT marked complete in REQUIREMENTS.md — it spans Plans 02/05/07 and
only closes once all land. Plan 178-07's ADVISORY-01 guard (verifying `compute_trend_report`
does not feed new/resolved/transition state back into `compute_readiness_score`) can now run
against the finished implementation.

---
*Phase: 178-finding-identity-repair*
*Completed: 2026-09-02*

## Self-Check: PASSED

- FOUND: .planning/phases/178-finding-identity-repair/178-05-SUMMARY.md
- FOUND commit: ac851e7e
- FOUND commit: 840dba9d
