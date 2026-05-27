---
phase: 114-automatic-merge-trigger
reviewed: 2026-05-26T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - quirk/dashboard/api/routes/sensor.py
  - tests/test_auto_merge_trigger.py
  - config.yaml
findings:
  critical: 1
  warning: 3
  info: 1
  total: 5
status: issues_found
---

# Phase 114: Code Review Report

**Reviewed:** 2026-05-26
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the Phase 114 auto-merge trigger implementation: `run_auto_merge` background task,
`_eval_trigger_condition` and `_load_auto_merge_config` helpers, IntegrationDelivery audit
rows, and the acceptance test suite.

Failure isolation is structurally sound — `run_auto_merge` opens its own session via
`get_session(db_path)`, so any merge exception cannot roll back or corrupt the push
transaction. The `safe_str` / `error_summary` contract is correctly applied on all audit
paths. The `get_session` context manager rolls back on exception and closes the session in
`finally`, so there are no session leaks.

One critical bug was found in the revoked-sensor exclusion logic used for the
`all-sensors-in` trigger condition. Three warnings follow: a hardcoded `config.yaml` path
inside `_ingest_envelope`, a potential `TypeError` in the `cadence-window` branch if
`merged_at` is ever stored as an aware datetime, and an ambiguous transactional contract in
the `_audit` helper. One info-level concern rounds out the findings.

---

## Critical Issues

### CR-01: Revoked-sensor exclusion uses wrong subquery semantics — sensors with mixed token sets are misclassified

**File:** `quirk/dashboard/api/routes/sensor.py:164-171`

**Issue:** The `all-sensors-in` trigger condition builds `revoked_sensor_ids` as all
`SensorToken.sensor_id` values where `revoked_at IS NOT NULL`, then excludes any `Sensor`
whose `sensor_id` appears in that subquery.

This logic conflates "sensor has at least one revoked token" with "sensor has no active
token." Two incorrect cases result:

**Case 1 — Re-keyed sensor (BLOCKER):** A sensor that was re-keyed — its old token was
revoked and a new active token issued — appears in `revoked_sensor_ids` because the old
`SensorToken` row has `revoked_at IS NOT NULL`. It is excluded from `active_sensors` even
though it has a valid active token and continues to push successfully. The `all-sensors-in`
condition then fires without that sensor's data being required, causing merges that
silently omit a live sensor. This is the most realistic operational scenario
(Phase 113 introduced per-sensor revocation).

**Case 2 — Un-tokenized sensor (ghost):** A `Sensor` row with no `SensorToken` rows at all
is NOT in `revoked_sensor_ids`, so it is included in `active_sensors`. Its
`last_push_at` is always `None`, so the guard at line 175 prevents triggering indefinitely.
Any enrollment half-ghost silently blocks all auto-merges until manually removed.

The correct logic is: a sensor is "active" if it has at least one `SensorToken` row where
`revoked_at IS NULL`.

```python
# Fix: include only sensors that have at least one active (non-revoked) token
active_token_sensor_ids = (
    db.query(SensorToken.sensor_id)
    .filter(SensorToken.revoked_at.is_(None))
)
active_sensors = (
    db.query(Sensor)
    .filter(Sensor.sensor_id.in_(active_token_sensor_ids))
    .all()
)
```

This also eliminates Case 2: a sensor with no token rows produces no entry in
`active_token_sensor_ids` and is correctly excluded.

**Why the acceptance test does not catch this:** `test_revoked_sensor_excluded` seeds
`sensor-b` with only a single revoked token. The buggy subquery and the corrected subquery
behave identically for that scenario. The failing scenario — a sensor with both a revoked
token and an active token — is not exercised by any test.

---

## Warnings

### WR-01: `_ingest_envelope` called with hardcoded `"config.yaml"` instead of env-var-derived path

**File:** `quirk/dashboard/api/routes/sensor.py:481`

**Issue:** The `_ingest_envelope` call passes `config_path="config.yaml"` as a literal
string. Twelve lines later (line 535) the route correctly derives the config path from
`QUIRK_CONFIG_PATH`. Any deployment that sets `QUIRK_CONFIG_PATH` to a non-default location
will have `_ingest_envelope` silently reading the wrong (or absent) config file, while
`_eval_trigger_condition` and `run_auto_merge` correctly use the env-var path.

This is particularly visible in the acceptance test suite: tests call
`monkeypatch.setenv("QUIRK_CONFIG_PATH", config_path)` expecting all config reads to go to
the temp file, but `_ingest_envelope` ignores the env var and falls back to
`./config.yaml` in the process working directory.

```python
# Before (line 479-485):
        _ingest_envelope(
            envelope_dict,
            config_path="config.yaml",
            skip_replay_window=False,
            qpush_sig=qpush_sig,
            db=db,
        )

# After — resolve once at the start of sensor_push and reuse:
        # Resolve config_path once (used for ingest, trigger eval, and background task):
        config_path = os.environ.get("QUIRK_CONFIG_PATH", "./config.yaml")
        ...
        _ingest_envelope(
            envelope_dict,
            config_path=config_path,
            skip_replay_window=False,
            qpush_sig=qpush_sig,
            db=db,
        )
```

### WR-02: `cadence-window` elapsed calculation raises `TypeError` if `merged_at` is aware

**File:** `quirk/dashboard/api/routes/sensor.py:193-195`

**Issue:** Line 194 computes `now - latest_merge.merged_at` where `now` is explicitly made
naive (`.replace(tzinfo=None)`). The comment says "always naive UTC" and this is currently
safe because `merge_scan` also strips tzinfo before writing `merged_at`. However, there is
no enforcement: if any code path — a future migration, a seeded test row, or a SQLite
driver configuration that returns aware datetimes — writes an aware `merged_at`, the
subtraction raises `TypeError: can't subtract offset-naive and offset-aware datetimes` at
runtime inside `run_auto_merge`'s try block. The outer `except Exception` in
`run_auto_merge` does write an audit row in that case, so data is not lost, but the
auto-merge is silently skipped with only a WARNING log.

The same naive-vs-aware risk applies on line 181 (`latest_push > latest_merge.merged_at`)
in the `all-sensors-in` branch.

```python
# Fix: normalize merged_at on read, mirroring the _sensor_status pattern (line 111-112):
merged_at = latest_merge.merged_at
if getattr(merged_at, "tzinfo", None) is not None:
    merged_at = merged_at.replace(tzinfo=None)
elapsed = (now - merged_at).total_seconds() / 60
return elapsed >= window_minutes
```

Apply the same guard to the `latest_push > latest_merge.merged_at` comparison on line 181.

### WR-03: `_audit` helper has ambiguous transactional contract — always commits internally

**File:** `quirk/dashboard/api/routes/sensor.py:315-340`

**Issue:** `_audit` always calls `db.commit()` internally (line 338). On the error paths
(lines 489-501) it is called after `db.rollback()`, which is correct — the rollback clears
the failed transaction, and `_audit` opens a new transaction, adds a row, and commits it.

However, the function is also reachable from contexts where a caller might not realize it
commits. The docstring says "Commit is OUTSIDE the ingest try-block" (an instruction about
call-site placement) but does not state that `_audit` itself always issues `db.commit()`.
A future maintainer who calls `_audit` mid-transaction to log a partial event would
unknowingly commit unfinished work.

Additionally, the success path bypasses `_audit` entirely (the `ok` row is added via
`db.add(ok_row)` directly and committed by the caller), which is inconsistent — two
patterns exist for the same class of write.

**Fix:** Add an explicit docstring note: "This function always calls db.commit(). Callers
MUST have called db.rollback() first (or be in a clean session state) before calling
_audit." Consider adding a boolean `commit: bool = True` parameter so the success path can
reuse `_audit` without the implicit commit behavior.

---

## Info

### IN-01: Test comment inaccurate about payload dedup in `test_double_fire_harmless`

**File:** `tests/test_auto_merge_trigger.py:387-389`

**Issue:** The comment says "same payload_id would be rejected (409). Use a fresh envelope."
But `_do_push` always calls `_build_envelope` which generates a new `uuid4()` payload_id
each invocation, so there is no 409 risk and the comment is misleading. The actual
mechanism being tested is the D-05 idempotent re-check inside `run_auto_merge`.

**Fix:** Replace the comment with: "Send a second push with a fresh payload_id (uuid4 ensures
no 409). The D-05 re-check in run_auto_merge should suppress a redundant MergeRun because
last_push_at will be <= merged_at from the first merge."

---

_Reviewed: 2026-05-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
