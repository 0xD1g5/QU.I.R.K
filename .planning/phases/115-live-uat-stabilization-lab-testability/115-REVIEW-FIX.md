---
phase: 115-live-uat-stabilization-lab-testability
fixed_at: 2026-05-27T00:00:00Z
review_path: .planning/phases/115-live-uat-stabilization-lab-testability/115-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 115: Code Review Fix Report

**Fixed at:** 2026-05-27T00:00:00Z
**Source review:** .planning/phases/115-live-uat-stabilization-lab-testability/115-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (CR-01, WR-01, WR-02, WR-03, IN-03)
- Fixed: 5
- Skipped: 0
- Deferred (out of scope): WR-04 (version bump 5.4.0→5.5.0 — held for milestone close)

## Fixed Issues

### WR-01: `_SAFE_NAME_RE` regex recompiled on every `_dispatch_schedule` call

**Files modified:** `quirk/cli/scheduler_cmd.py`
**Commit:** 6040275
**Applied fix:** Added `_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")` at module
scope after `_STALE_THRESHOLD`. Removed the local definition inside `_dispatch_schedule`
and updated the adjacent comment to remove the stale "WR-02" label.

---

### WR-02: Silent exception suppression hides subprocess spawn failures

**Files modified:** `quirk/cli/scheduler_cmd.py`
**Commit:** e2e05f6
**Applied fix:** Changed `except Exception:` to `except Exception as _exc:` and added
`logger.error` with `safe_str(_exc)` before marking the run failed, so
`FileNotFoundError`, `PermissionError`, and `OSError` from `Popen` are diagnosable.

---

### CR-01: Malformed `cron_expr` in any schedule crashes the entire scheduler loop

**Files modified:** `quirk/cli/scheduler_cmd.py`, `tests/test_scheduler_cmd.py`
**Commits:** f2fa6ef (code fix), edddf73 (regression test)
**Applied fix:** Wrapped `_compute_next_run(s)` in `try/except Exception` inside the
per-schedule loop in `_check_and_dispatch_due`. On exception, logs
`schedule.name + cron_expr + safe_str(exc)` at ERROR level and `continue`s so all
other valid schedules are still dispatched. Added regression test
`test_malformed_cron_expr_does_not_crash_loop` that seeds one bad + one good schedule
and asserts only the good one produces a run row.

---

### WR-03: `_flush_spool` catches bare `Exception`, permanently trapping corrupt spool files

**Files modified:** `quirk/cli/sensor_cmd.py`
**Commit:** 842601b
**Applied fix:** Replaced the single `except (httpx.ConnectError, httpx.TimeoutException, Exception): pass`
with three clauses: (1) `except (httpx.ConnectError, httpx.TimeoutException): pass` for
transient retries; (2) explicit `else` branch on non-200/409 status logging a WARNING and
leaving the file without endless retry; (3) `except Exception` that checks for `RetryError`
(tenacity exhausted) and logs a WARNING, and logs other unexpected errors via `safe_str`.
Happy path (200/409 → `unlink(missing_ok=True)`) is unchanged.

---

### IN-03: `_load_cache` monkeypatch falls through to real package resource

**Files modified:** `quirk/compliance/cmvp.py`
**Commit:** 0e61d3b
**Applied fix:** Changed `if _CACHE_PATH != _default_path and _CACHE_PATH.exists():` to
`if _CACHE_PATH != _default_path:` with an explicit inner check that raises
`FileNotFoundError` when the patched path does not exist. This prevents tests that
monkeypatch `_CACHE_PATH` to a not-yet-written `tmp_path` target from silently falling
through to `importlib.resources` and reading the real production cache.

---

## Deferred (out of scope)

### WR-04: `pyproject.toml` version string not bumped for v5.5 delivery

**File:** `pyproject.toml:7`
**Reason:** Intentionally deferred to milestone close per fix objective. Bumping version
mid-milestone breaks version-string UAT assertions. Will be applied at the v5.5
milestone-close step alongside the standard version-bump checklist.

---

## Test Results

`python -m compileall quirk/cli/scheduler_cmd.py quirk/cli/sensor_cmd.py quirk/compliance/cmvp.py` — all compiled cleanly.

`python -m pytest tests/test_scheduler_cmd.py tests/test_scheduler_posix_fixes.py tests/test_notify_dispatcher.py tests/ -k "cmvp or sensor_cmd or scheduler or enroll" -q`
— **90 passed, 2590 deselected, 4 warnings** (4 pre-existing mark warnings, unrelated to these fixes).

---

_Fixed: 2026-05-27T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
