---
phase: 109-console-ingestion-api
fixed_at: 2026-05-25T00:00:00Z
review_path: .planning/phases/109-console-ingestion-api/109-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 109: Code Review Fix Report

**Fixed at:** 2026-05-25
**Source review:** `.planning/phases/109-console-ingestion-api/109-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 8
- Fixed: 8
- Skipped: 0

## Fixed Issues

### CR-01: `_audit()` called on a rolled-back session

**Files modified:** `quirk/dashboard/api/routes/sensor.py`
**Commit:** 3003a04
**Applied fix:** Added explicit `db.rollback()` calls in the `DuplicatePayloadError` and bare `except Exception` blocks in `sensor_push()` before delegating to `_audit()`. This ensures the SQLAlchemy session is in a clean implicit-transaction state for the audit write, regardless of whether `_ingest_envelope` internally called `rollback()` during the FK/UNIQUE error handling.

---

### CR-02: `UnknownSensorError` not caught — falls to generic 500

**Files modified:** `quirk/dashboard/api/routes/sensor.py`
**Commit:** 3003a04
**Applied fix:** Added an explicit `except UnknownSensorError:` block in the ingest try/except chain that calls `db.rollback()`, writes a `"unknown_sensor_id"` audit row, and raises `HTTPException(status_code=404)`. Imported `UnknownSensorError` from `quirk.cli.console_cmd` at module scope alongside the existing `DuplicatePayloadError` import.

---

### WR-01: Decompression bomb guard allocates full buffer before checking

**Files modified:** `quirk/dashboard/api/routes/sensor.py`, `quirk/cli/console_cmd.py`
**Commit:** 3003a04
**Applied fix:** Changed `zstandard.ZstdDecompressor()` to `zstandard.ZstdDecompressor(max_window_size=_MAX_DECOMPRESS_BYTES)` in both the HTTPS route (`sensor.py`) and the air-gap import path (`console_cmd.py`). The `max_window_size` parameter causes the C-layer decompressor to reject frames whose decompressed window exceeds the limit before Python allocates the full buffer. The post-read `len(raw) > _MAX_DECOMPRESS_BYTES` check is retained as a secondary Python-level defence.

---

### WR-02: Success-path `_audit("ok")` not atomic with the ingest commit

**Files modified:** `quirk/dashboard/api/routes/sensor.py`
**Commit:** 3003a04
**Applied fix:** Replaced the post-commit `_audit(db, scan_id, "ok", None)` call (which ran in a second separate transaction) with an inline `db.add(ok_row)` before the single final `db.commit()`. The "ok" `IntegrationDelivery` row is now flushed and committed atomically with the ingest data (`SensorPush`, `CryptoEndpoint`, `last_push_at` update) in one transaction. The commit failure path adds a rollback before the failure audit write.

---

### WR-03: `scan_id` set from untrusted `envelope.pushed_at` without length clamp

**Files modified:** `quirk/dashboard/api/routes/sensor.py`
**Commit:** 3003a04
**Applied fix:** Changed `scan_id = envelope.pushed_at or scan_id` to `scan_id = (envelope.pushed_at or scan_id)[:64]`. This enforces the `IntegrationDelivery.scan_id String(64)` schema constraint at the application layer before any audit write, preventing an attacker from injecting arbitrarily long strings into audit records.

---

### WR-04: Gratuitous `sys.exit(0)` in `_cmd_enroll` and `_cmd_import_results`

**Files modified:** `quirk/cli/console_cmd.py`, `tests/test_console_cmd.py`, `tests/test_console_enroll.py`
**Commits:** 3003a04, 69db594
**Applied fix:** Removed `sys.exit(0)` from the success path of `_cmd_enroll` (was line 200) and `_cmd_import_results` (was line 319). Both functions now return normally; `run_console` returns after dispatch. `sys.exit(1)` on all error paths is preserved unchanged.

All success-path test assertions updated: nine test functions in `test_console_cmd.py` and `test_console_enroll.py` that previously used `pytest.raises(SystemExit)` with `code == 0` assertions were updated to call the functions directly (no SystemExit expected). Error-path tests that assert `code != 0` are unchanged. All 80 tests pass.

---

### IN-01: `import json` inside the route handler body

**Files modified:** `quirk/dashboard/api/routes/sensor.py`
**Commit:** 3003a04
**Applied fix:** Moved `import json` from inside the `try` block of `sensor_push()` to module scope at the top of `sensor.py`, alongside the other stdlib imports. Satisfies PEP 8 and the CLAUDE.md project standard.

---

### IN-02: `findings: list = []` mutable default in Pydantic model

**Files modified:** `quirk/dashboard/api/routes/sensor.py`
**Commit:** 3003a04
**Applied fix:** Changed `findings: list = []` to `findings: list = Field(default_factory=list)` in `PushEnvelope`. Added `Field` to the `from pydantic import` line. Idiomatic Pydantic v2 form; eliminates the shared-mutable-default anti-pattern.

---

## Verification

```
python -m compileall quirk run_scan.py -q   → OK (no output)
pytest tests/test_console_cmd.py tests/test_console_enroll.py \
       tests/test_sensor_ingest.py tests/test_sensor_cmd.py \
       tests/test_api_auth.py tests/scanner/test_phase57_invariants.py -q
→ 80 passed, 27 warnings in 1.94s
```

All warnings are pre-existing `datetime.utcnow()` deprecation notices in test helpers — not introduced by these fixes.

---

_Fixed: 2026-05-25_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
