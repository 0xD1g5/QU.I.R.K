---
phase: 114-automatic-merge-trigger
fixed_at: 2026-05-26T00:00:00Z
review_path: .planning/phases/114-automatic-merge-trigger/114-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 114: Code Review Fix Report

**Fixed at:** 2026-05-26
**Source review:** .planning/phases/114-automatic-merge-trigger/114-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (CR-01, WR-01, WR-02, WR-03, IN-01)
- Fixed: 5
- Skipped: 0

---

## Fixed Issues

### CR-01: Revoked-sensor exclusion uses wrong subquery semantics

**Files modified:** `quirk/dashboard/api/routes/sensor.py`, `tests/test_auto_merge_trigger.py`
**Commit:** a4a7fd1 (sensor.py), 67df13e (tests)
**Applied fix:** Replaced the exclusion subquery (`~Sensor.sensor_id.in_(revoked_sensor_ids)`)
with an inclusion subquery (`Sensor.sensor_id.in_(active_token_sensor_ids)`) that matches
sensors having at least one `SensorToken` where `revoked_at IS NULL`.

This correctly handles the re-key scenario (old revoked token + new active token coexist):
the old logic excluded such sensors because their revoked token appeared in the exclusion
set; the new logic requires a positive match on an active token.

Zero-token ghost sensors are also excluded by construction — they produce no row in
`active_token_sensor_ids`.

**Regression tests added** in `tests/test_auto_merge_trigger.py`:
- `test_mixed_token_sensor_is_required_for_all_in`: seeds a sensor with both a revoked and
  an active token plus a normal sensor; asserts auto-merge does NOT fire until the
  mixed-token sensor pushes, then asserts it fires after.
- `test_zero_token_sensor_not_counted_as_active`: seeds a ghost sensor with zero tokens;
  asserts auto-merge fires for the sole active-token sensor without being blocked.

**Note:** Logic correctness verified by test suite (9/9 pass including 2 new regression
tests). Requires human verification that the inclusion subquery semantics match D-04 intent.

---

### WR-01: `_ingest_envelope` called with hardcoded `"config.yaml"`

**Files modified:** `quirk/dashboard/api/routes/sensor.py`
**Commit:** a4a7fd1
**Applied fix:** Resolved `QUIRK_CONFIG_PATH` env var via
`os.environ.get("QUIRK_CONFIG_PATH", "./config.yaml")` into `ingest_config_path` at the
start of the ingest block and passed it to `_ingest_envelope`. This keeps all three config
consumers in `sensor_push` (ingest, trigger eval, background task) reading the same file.

---

### WR-02: `cadence-window` elapsed calculation raises `TypeError` if `merged_at` is aware

**Files modified:** `quirk/dashboard/api/routes/sensor.py`
**Commit:** a4a7fd1
**Applied fix:** Applied the `_sensor_status` tzinfo-normalization pattern
(`if getattr(merged_at, "tzinfo", None) is not None: merged_at = merged_at.replace(tzinfo=None)`)
to both comparison sites:
1. The `latest_push > merged_at` comparison in the `all-sensors-in` branch.
2. The `(now - merged_at_cw).total_seconds()` elapsed calculation in the `cadence-window` branch.

---

### WR-03: `_audit` helper has ambiguous transactional contract

**Files modified:** `quirk/dashboard/api/routes/sensor.py`
**Commit:** a4a7fd1
**Applied fix:** Replaced the single-line docstring with an explicit docstring that states:
(1) this function always calls `db.commit()` internally; (2) callers on error paths MUST
call `db.rollback()` first; (3) the success path intentionally bypasses `_audit` to commit
ingest data and the ok row atomically — two patterns exist by design. Behavior unchanged.

---

### IN-01: Test comment inaccurate in `test_double_fire_harmless`

**Files modified:** `tests/test_auto_merge_trigger.py`
**Commit:** 67df13e
**Applied fix:** Replaced the comment "Second push: same payload_id would be rejected (409).
Use a fresh envelope." with the accurate description: "Send a second push with a fresh
payload_id (uuid4 ensures no 409). The D-05 re-check in run_auto_merge should suppress a
redundant MergeRun because last_push_at will be <= merged_at from the first merge."

---

## Test Results

```
tests/test_auto_merge_trigger.py — 9 passed (7 original + 2 new CR-01 regression)
Broader sensor suite (sensor_ingest / sensor_merge / sensor_push / sensor_registry) — 40 passed
python -m compileall quirk/dashboard/api/routes/sensor.py — PASS
```

All tests pass. No regressions introduced.

---

_Fixed: 2026-05-26_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
