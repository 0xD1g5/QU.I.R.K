---
phase: 115-live-uat-stabilization-lab-testability
reviewed: 2026-05-27T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - quirk/cli/scheduler_cmd.py
  - quirk/cli/sensor_cmd.py
  - quirk/cli/console_cmd.py
  - quirk/compliance/cmvp.py
  - pyproject.toml
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 115: Code Review Report

**Reviewed:** 2026-05-27T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 115 delivers four STAB stabilization fixes plus a weak-TLS lab target. The core
correctness goals (STAB-01 idempotency pre-check, STAB-03 fail-fast condition, STAB-04
NULL advisory-row filter, STAB-02 importlib.resources cache loading) are all implemented
as specified and the security-relevant invariants (token churn prevention, no --target/
--output shell-arg widening, YAML safe_dump, IS NULL clause) are present and correct.

One blocker was found: the scheduler's long-running loop has no exception guard around
`_compute_next_run`, meaning a single enabled schedule with a corrupt or malformed
`cron_expr` in the database will crash the entire scheduler process. All other scheduled
scans stop running until the process is restarted. The remaining findings are warnings
and informational items.

---

## Critical Issues

### CR-01: Malformed `cron_expr` in any schedule crashes the entire scheduler loop

**File:** `quirk/cli/scheduler_cmd.py:369`

**Issue:** `_check_and_dispatch_due` calls `_compute_next_run(s)` at line 369 for every
enabled schedule without any exception handling. `_compute_next_run` calls
`croniter(schedule.cron_expr, base).get_next(datetime)` at line 73. If `cron_expr` in
the database is malformed (e.g. truncated by a bug, or manually edited to an invalid
expression), `croniter` raises `CroniterBadCronError` (a subclass of `ValueError`).
This uncaught exception propagates through `_check_and_dispatch_due`, out of the
`with get_session(db_path) as db:` block in the main loop at line 432, and terminates
the `while not _stop_flag` loop via unhandled exception. The scheduler process exits and
all scheduled scans for all segments stop until an operator manually restarts the process.
One bad row in the `scheduled_scans` table is sufficient to take down the entire
scheduler.

`_dispatch_schedule` wraps only the `subprocess.Popen` block (line 305-309) in
`try/except Exception`, not the pre-dispatch logic. The main loop in `run_scheduler`
(lines 430-438) also has no outer try/except. The `--once` path (line 426) is equally
unprotected.

**Fix:**

```python
# In _check_and_dispatch_due, wrap the per-schedule computation defensively:
for s in schedules:
    try:
        next_run = _compute_next_run(s)
    except Exception:
        import logging as _log
        _log.getLogger(__name__).error(
            "Schedule %r has invalid cron_expr %r — skipping this iteration",
            s.name, s.cron_expr,
        )
        continue
    if next_run <= now:
        _dispatch_schedule(s, db, config_path, scan_config_path=scan_config_path)
        dispatched += 1
```

---

## Warnings

### WR-01: `_SAFE_NAME_RE` regex recompiled on every `_dispatch_schedule` call

**File:** `quirk/cli/scheduler_cmd.py:272`

**Issue:** `re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")` is assigned to a local variable
`_SAFE_NAME_RE` inside `_dispatch_schedule`. Python's `re` module does cache compiled
patterns internally, but the canonical practice for a pattern used in a hot loop is to
compile it once at module scope. The scheduler's dispatch loop calls
`_dispatch_schedule` for every due schedule on every 60-second iteration; under load
this creates unnecessary repeated compile-cache lookups and naming confusion (the
leading underscore suggests module-level scope, not a local).

**Fix:** Move the constant to module scope alongside the other module-level constants:

```python
# After _STALE_THRESHOLD at line 80:
_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")
```

Remove the local definition at line 272.

---

### WR-02: Silent exception suppression hides subprocess spawn failures in `_dispatch_schedule`

**File:** `quirk/cli/scheduler_cmd.py:309`

**Issue:** The `except Exception:` block at line 309 catches all exceptions from
`subprocess.Popen(cmd, ...)` and `proc.communicate()` without logging anything.
Failures such as `FileNotFoundError` (Python interpreter missing), `PermissionError`,
or `OSError` are silently swallowed: the run row is marked `failed`, but no diagnostic
is written anywhere. An operator investigating why all scheduled scans are failing will
find only `status=failed` rows with no error detail. This is distinct from the
notification/SIEM exception blocks below (which do log), and is the only exception
block in the file with no logging.

**Fix:** Add a logger warning inside the bare except:

```python
except Exception as _exc:
    run.status = "failed"
    import logging as _logging
    from quirk.util.safe_exc import safe_str as _safe_str
    _logging.getLogger(__name__).error(
        "Subprocess launch failed for schedule %r: %s",
        schedule.name, _safe_str(_exc),
    )
```

---

### WR-03: `_flush_spool` catches bare `Exception`, permanently trapping corrupt spool files

**File:** `quirk/cli/sensor_cmd.py:551`

**Issue:** `_flush_spool` at line 551 catches `(httpx.ConnectError, httpx.TimeoutException, Exception)`.
The first two types are redundant (they are subclasses of `Exception`). More critically,
`bare Exception` swallows *all* errors including permanent 4xx responses from `_do_push`
(which return `resp` without raising), corrupt/invalid `.json.zst` spool files that
fail decompression at `body = f.read_bytes()`, and `RetryError` from tenacity after
five exhausted retries (which is a subclass of `Exception`). When `_do_push` raises
`RetryError` (all 5 retries exhausted on 5xx), the spool file is left on disk and
will be retried endlessly on every future `push` invocation, never being evicted.
This can also mask the fact that the console is persistently rejecting pushes.

**Fix:** Narrow the catch to transient network errors only, and explicitly handle
permanent rejections:

```python
import httpx
from tenacity import RetryError

try:
    resp = _do_push(client, push_url, headers, body)
    if resp.status_code in (200, 409):
        f.unlink(missing_ok=True)
    # 4xx permanent error: leave file but log; do not retry forever
    else:
        import logging as _log
        _log.getLogger(__name__).warning(
            "Spool re-push permanently rejected HTTP %d — leaving %s",
            resp.status_code, f.name,
        )
except (httpx.ConnectError, httpx.TimeoutException, RetryError):
    pass  # Transient — leave file for next attempt
except Exception as exc:
    import logging as _log
    _log.getLogger(__name__).warning("Spool re-push error for %s: %s", f.name, exc)
```

---

### WR-04: `pyproject.toml` version string not bumped for v5.5 delivery

**File:** `pyproject.toml:7`

**Issue:** `version = "5.4.0"` is the declared package version, but Phase 115 is part
of the v5.5 milestone (Phases 113–116). The `quirk.__version__` attribute is derived
from installed package metadata (`importlib.metadata.version`), so any installed wheel
built from this `pyproject.toml` will report `5.4.0`. This cascades into
`sensor_cfg["sensor_version"]` written by `quirk sensor enroll` (sensor_cmd.py line 282)
and into the `sensor_version` field in push envelopes and the sensor registry dashboard.
Sensors enrolled during v5.5 will appear to be running v5.4.0, making version-based
triage impossible. It also prevents CI from detecting version drift between the code and
the declared package.

**Fix:** Bump to the correct v5.5 semver:

```toml
version = "5.5.0"
```

---

## Info

### IN-01: `coverage_for_algorithm` performs two dead intermediate sorts before the final partition

**File:** `quirk/compliance/cmvp.py:312-325`

**Issue:** Lines 312–325 perform two `matches.sort()` calls that are entirely superseded
by the manual partition and re-sort at lines 327–331. The first sort (lines 312–319)
uses a composite key including `-len(module_version)` as a "descending proxy" — this
is neither correct nor used: the comment acknowledges needing "a second pass". The
second sort (lines 322–325) does not sort descending despite `reverse=False` and is
immediately discarded by the partition. The final result is correct (FIPS 140-3 first,
then version descending within each tier), but the two preceding sorts are wasted CPU
and misleading to readers.

**Fix:** Remove the two dead intermediate sorts. Lines 312–325 can be deleted entirely;
the partition + sort at lines 327–331 is self-sufficient and correct.

---

### IN-02: `cmvp_curated.csv` absent from `[tool.setuptools.package-data]`

**File:** `pyproject.toml:128-133`

**Issue:** `quirk/compliance/cmvp_curated.csv` is referenced by `_CURATED_CSV_PATH` in
`cmvp.py` (line 52) and consumed by `_read_curated_cert_numbers()` / `refresh_cache()`.
The `package-data` stanza includes `compliance/*.json` but not `compliance/*.csv`. In a
wheel install, the CSV will be absent from `site-packages/quirk/compliance/` and
`_read_curated_cert_numbers()` will silently return `[]`, making `refresh_cache()` write
an empty module list.

Per the module docstring (line 86), `refresh_cache` is "a developer-only tool intended
for source-checkout use (Pitfall 2)", so this is not a production runtime defect —
developers running `refresh_cache` from a wheel install will get a silent empty result
rather than an error. If the developer intent is confirmed (CSV is source-only), add a
comment to `_read_curated_cert_numbers` explaining this. If the CSV should be bundled,
add it to package-data:

```toml
"compliance/*.json",
"compliance/*.csv",
```

---

### IN-03: `_load_cache` monkeypatch override falls through to the real package resource when patched path does not yet exist

**File:** `quirk/compliance/cmvp.py:94-102`

**Issue:** The monkeypatch override hook at lines 94–95 checks
`_CACHE_PATH != _default_path and _CACHE_PATH.exists()`. If a test replaces `_CACHE_PATH`
with a path to a file that has not yet been written (e.g. a `tmp_path` fixture target
before the test writes it), the condition is `True != True` (path differs) but `.exists()`
is `False`, so the condition is `False` and the code falls through to
`importlib.resources` which loads the real production cache. The test silently reads the
real cache instead of the intended fixture, producing false-positive test results. This
is a test-isolation hazard, not a production bug.

**Fix:** Change the condition to check only that the path has been patched, and raise
clearly if the patched path does not exist:

```python
if _CACHE_PATH != _default_path:
    if not _CACHE_PATH.exists():
        raise FileNotFoundError(f"Monkeypatched _CACHE_PATH does not exist: {_CACHE_PATH}")
    _text = _CACHE_PATH.read_text(encoding="utf-8")
else:
    _text = (
        _ir_files("quirk.compliance")
        .joinpath("cmvp_cache.json")
        .read_text(encoding="utf-8")
    )
```

---

_Reviewed: 2026-05-27T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
