---
phase: 114-automatic-merge-trigger
reviewed: 2026-05-26T00:00:00Z
depth: standard
iteration: 2
files_reviewed: 2
files_reviewed_list:
  - quirk/dashboard/api/routes/sensor.py
  - tests/test_auto_merge_trigger.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 114: Code Review Report (Iteration 2 — Re-Review)

**Reviewed:** 2026-05-26
**Depth:** standard
**Iteration:** 2 (re-review after CR-01, WR-01, WR-02, WR-03, IN-01 fixes applied)
**Files Reviewed:** 2
**Status:** issues_found (0 critical, 1 warning, 2 info)

---

## Prior Finding Verdicts

### CR-01 — RESOLVED

`_eval_trigger_condition` (lines 169–177) now uses an inclusion subquery:

```python
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

A sensor is active only if it has at least one `SensorToken` row where `revoked_at IS NULL`.
Re-keyed sensors (revoked old token + active new token) produce at least one row in the
subquery and are correctly included. Zero-token sensors produce no row in the subquery and
are correctly excluded.

Regression tests directly exercise both cases:

- `test_mixed_token_sensor_is_required_for_all_in` (line 307): seeds sensor-b with one
  revoked token and one active token. Asserts no merge fires until sensor-b pushes using the
  active token. Then asserts the merge fires after sensor-b pushes. Assertions are concrete.
- `test_zero_token_sensor_not_counted_as_active` (line 359): seeds sensor-ghost with zero
  tokens. Asserts the merge fires after sensor-a pushes alone, confirming the ghost sensor
  does not block the trigger. Assertion is concrete.

**CR-01: RESOLVED.**

### WR-01 — RESOLVED

`ingest_config_path` is resolved from `QUIRK_CONFIG_PATH` env var at line 501 and passed as
`config_path` to `_ingest_envelope` (line 505). `_load_auto_merge_config` resolves its
effective path via `config_path or os.environ.get("QUIRK_CONFIG_PATH", "./config.yaml")`
(line 136). All three call sites in the route handler read from the same env variable.

**WR-01: RESOLVED.**

### WR-02 — RESOLVED

Both branches of `_eval_trigger_condition` normalize `merged_at` before comparison:

- `all-sensors-in` branch: lines 187–189 strip `tzinfo` if aware before `latest_push > merged_at`.
- `cadence-window` branch: lines 206–208 strip `tzinfo` if aware before the elapsed calculation.

Pattern mirrors `_sensor_status` lines 111–112.

**WR-02: RESOLVED.**

### WR-03 — RESOLVED

The `_audit` docstring (lines 330–361) now explicitly documents the transactional contract:
always commits internally; error-path callers must call `db.rollback()` first; success-path
callers add the row directly and commit outside the helper.

**WR-03: RESOLVED.**

### IN-01 (prior) — RESOLVED

Test comment in `test_double_fire_harmless` was updated per the fix review record.

---

## Narrative Findings (AI reviewer — fresh scan)

### Warnings

#### WR-01: Vacuous `sensor_count >= 0` assertion provides no merge-correctness coverage

**File:** `tests/test_auto_merge_trigger.py:242`

**Issue:** The assertion `assert mr.sensor_count >= 0` is vacuously true for any non-negative
integer including zero. `sensor_count` is an integer column; it cannot be negative in normal
operation, so this assertion can never fail. The test confirms a `MergeRun` row exists
(correct) but does not verify that the merge actually processed the two seeded sensors
(sensor-a and sensor-b), leaving open the possibility that `merge_scan` wrote a zero-sensor
run undetected.

**Fix:** Replace with a meaningful lower bound:
```python
assert mr.sensor_count >= 2, (
    f"Expected MergeRun to cover both seeded sensors, got sensor_count={mr.sensor_count}"
)
```
If `merge_scan`'s counting logic does not match `2` exactly (e.g., counts by distinct hosts
rather than enrolled sensors), `>= 1` is the minimum meaningful bound, but the two-sensor
test setup makes `>= 2` correct.

---

### Info

#### IN-01: Misleading inline comment on success-path audit row

**File:** `quirk/dashboard/api/routes/sensor.py:531`

**Issue:** The inline comment reads:

```
# _audit() calls db.add(); the final db.commit() below persists everything.
```

This is factually wrong. On the success path `_audit()` is never called. The code directly
calls `db.add(ok_row)` (line 542) and `db.commit()` (line 546). The comment appears to be a
copy/paste artefact from an earlier design. A future maintainer reading this comment would
incorrectly believe `_audit` has already been called.

**Fix:**
```python
# Write the ok audit row directly (bypassing _audit so ingest data and the
# audit row commit atomically — see _audit docstring for the two-pattern rationale).
```

#### IN-02: `QUIRK_CONFIG_PATH` resolved twice in the same request handler

**File:** `quirk/dashboard/api/routes/sensor.py:501,559`

**Issue:** The comment at line 499–500 states the intent is to "resolve config_path once
here." However `os.environ.get("QUIRK_CONFIG_PATH", "./config.yaml")` is called a second
time at line 559 as the local variable `config_path`, which is then passed to
`_eval_trigger_condition` and `run_auto_merge`. In production both reads return the same
value, so there is no behavioral defect. The issue is that the stated design intent
("resolve once") is violated, and a future mutation of the env var between the two reads
(hypothetical, but valid under `os.environ` mutation in tests) would produce inconsistent
config paths.

**Fix:** Reuse `ingest_config_path` for all three downstream call sites:
```python
ingest_config_path = os.environ.get("QUIRK_CONFIG_PATH", "./config.yaml")
# ... _ingest_envelope call (unchanged) ...
if _eval_trigger_condition(db, ingest_config_path):
    background_tasks.add_task(run_auto_merge, db_path, ingest_config_path)
```

---

## Summary

All five prior findings (CR-01, WR-01, WR-02, WR-03, IN-01) are confirmed resolved. The
inclusion-subquery fix for CR-01 is mechanically correct and both regression tests carry
concrete, non-vacuous assertions — with one exception noted in WR-01 above.

The fresh scan produced no new critical or security issues. The monkeypatch target in
`test_merge_failure_isolated` (line 416) correctly patches `quirk.merge.scan.merge_scan`
before the deferred `from quirk.merge.scan import merge_scan` executes inside
`run_auto_merge`, so the mock is effective. The `cadence_window_minutes=0` edge case in
`test_cadence_window_triggers` is valid: `cfg.get("cadence_window_minutes")` returns integer
`0`, the `is None` guard at line 198 correctly passes through, and `elapsed >= 0` always
fires.

**Verdict: no blockers. WR-01 (vacuous assertion) is recommended before merge. Two info
items are housekeeping only.**

---

_Reviewed: 2026-05-26_
_Reviewer: Claude (gsd-code-reviewer) — iteration 2_
_Depth: standard_
