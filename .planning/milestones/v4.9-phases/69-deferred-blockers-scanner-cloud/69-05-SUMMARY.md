---
phase: 69
plan: 05
subsystem: engine/cache
tags: [block-05, cr-06, cache, api-contract, bugfix]
requires: []
provides:
  - "load_cache treats ttl_hours <= 0 as cache-disabled (returns None)"
  - "Test coverage for all four TTL paths"
  - "UAT-SERIES.md API-contract note for future callers"
affects:
  - quirk/engine/cache.py
  - tests/test_cache.py
  - docs/UAT-SERIES.md
tech-stack:
  added: []
  patterns:
    - "TDD: RED-first failing test before fix"
    - "Internal API contract note (no CLI surface)"
key-files:
  created:
    - tests/test_cache.py
  modified:
    - quirk/engine/cache.py
    - docs/UAT-SERIES.md
decisions:
  - "D-10: ttl_hours <= 0 means cache disabled (was: cache forever). Inverted CR-06."
metrics:
  duration_minutes: ~5
  completed: 2026-05-14
  tasks_completed: 2
  files_changed: 3
---

# Phase 69 Plan 05: BLOCK-05 / CR-06 — load_cache ttl_hours Semantics Fix Summary

Inverted the `ttl_hours <= 0` branch in `quirk/engine/cache.py::load_cache` so zero or
negative TTL now means "cache disabled" (returns `None`) instead of the previous (inverted)
"cache forever" behavior. Added `tests/test_cache.py` with four parametric paths and
documented the API contract change in `docs/UAT-SERIES.md`.

## What Was Built

### Task 1 — Invert `ttl_hours <= 0` branch + RED-first tests

Followed TDD cycle:

**RED:** Created `tests/test_cache.py` with four tests. Ran pytest → first test failed
as expected (`load_cache(..., ttl_hours=0)` returned the cached dict instead of `None`).
- Commit: `e6d2dd7` — `test(69-05): add failing tests for load_cache ttl_hours<=0 contract`

**GREEN:** Changed the single production line in `quirk/engine/cache.py:60` from
`return obj` to `return None` inside the `if ttl_hours <= 0:` branch (with an explanatory
comment citing D-10 / BLOCK-05). All four tests now pass. `python -m compileall` clean.
- Commit: `9c0c1bf` — `fix(69-05): invert ttl_hours<=0 branch in load_cache (BLOCK-05)`

Tests cover:
- `test_ttl_zero_returns_none_on_fresh_file` — ttl=0 disables cache on fresh file
- `test_ttl_negative_returns_none_on_fresh_file` — ttl=-1 also disables cache
- `test_ttl_positive_returns_obj_when_fresh` — ttl>0 within window returns cached obj
- `test_ttl_positive_returns_none_when_stale` — ttl>0 past window returns None (monkeypatched `_now`)

### Task 2 — Document load_cache API contract change

Added an "Internal API Contract Note — Phase 69 / BLOCK-05 (2026-05-14)" subsection
right after `UAT-3-08: Cache Mode` in `docs/UAT-SERIES.md`. Prepended the Phase 69 /
BLOCK-05 entry to the `**Last Updated:**` changelog string. Minimal diff, purely additive.
- Commit: `de9262c` — `docs(69-05): document load_cache(ttl_hours=0) API contract change`

## Integration Check

Per the plan's instruction, ran `grep -rn 'load_cache' quirk/ tests/` after the fix:
- Only match in production code: the definition itself at `quirk/engine/cache.py:50`.
- No callers in `quirk/run_scan.py` or anywhere else in `quirk/`.
- No `--cache-ttl-hours` CLI flag exists.

**Finding:** Zero production callers affected by this fix. The change preempts misuse by
future callers (D-10 rationale). No further code changes required across the codebase.

## Verification

```
pytest tests/test_cache.py -x -q   →  4 passed in 0.01s
python -m compileall quirk/engine/cache.py  →  exit 0
grep -n 'return None' quirk/engine/cache.py  →  line 63 inside ttl<=0 branch
grep -n 'BLOCK-05' docs/UAT-SERIES.md       →  matches (header + note section)
grep -n 'load_cache' docs/UAT-SERIES.md     →  matches (note section)
**Last Updated:** 2026-05-14                →  present at line 4
```

## Deviations from Plan

None — plan executed exactly as written. The one-line fix matched D-10 precisely;
no auto-fix rules triggered; no architectural deviations.

## Commits

| Step  | Hash      | Message                                                       |
| ----- | --------- | ------------------------------------------------------------- |
| RED   | `e6d2dd7` | test(69-05): add failing tests for load_cache ttl_hours<=0 contract |
| GREEN | `9c0c1bf` | fix(69-05): invert ttl_hours<=0 branch in load_cache (BLOCK-05) |
| DOCS  | `de9262c` | docs(69-05): document load_cache(ttl_hours=0) API contract change |

## Known Stubs

None.

## Self-Check: PASSED

- [x] `quirk/engine/cache.py` modified (verified — `return None` at line 63 inside `if ttl_hours <= 0:`)
- [x] `tests/test_cache.py` created (verified — 4 tests, all pass)
- [x] `docs/UAT-SERIES.md` updated (verified — BLOCK-05 + load_cache + ttl_hours=0 markers present)
- [x] Commits exist: `e6d2dd7`, `9c0c1bf`, `de9262c` (verified via `git log --oneline -5`)
- [x] `pytest tests/test_cache.py -x -q` → 4 passed
- [x] `python -m compileall quirk/engine/cache.py` → exit 0
- [x] Integration check confirms zero production callers
