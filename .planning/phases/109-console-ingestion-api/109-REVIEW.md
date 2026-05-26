---
phase: 109-console-ingestion-api
reviewed: 2026-05-25T14:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - quirk/dashboard/api/routes/sensor.py
  - quirk/cli/console_cmd.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: clean
iteration: 3
---

# Phase 109: Code Review Report (Re-review — Iteration 3, Final)

**Reviewed:** 2026-05-25T14:00:00Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** clean
**Scope:** Final confirmation re-review of WR-01a fix (power-of-two `_ZSTD_MAX_WINDOW`); full
regression check of all previously-resolved findings (CR-01, CR-02, WR-02, WR-03, WR-04,
IN-01, IN-02).

## Summary

The WR-01a fix is correctly applied in both files. `_ZSTD_MAX_WINDOW = 32 * 1024 * 1024`
(2^25, a valid zstd window-log exponent) is declared as a separate named constant in both
`sensor.py` (line 58) and `console_cmd.py` (line 55), with inline comments explaining the
power-of-two requirement and the rounding behaviour that motivated the separation. Both
decompressor constructions pass `max_window_size=_ZSTD_MAX_WINDOW` (not the 20 MB application
cap), and the authoritative 20 MB application limit is still enforced by the post-read length
check (`read(_MAX_DECOMPRESS_BYTES + 1)` + `len(raw) > _MAX_DECOMPRESS_BYTES`) in both paths.
A legitimate payload under 20 MB decompresses successfully; a payload that decompresses to more
than 20 MB is rejected cleanly before the result is used. No new Critical or Warning issues
were found.

All eight previously-resolved findings remain resolved with no regressions.

---

## Fix Verification

### WR-01a: `_ZSTD_MAX_WINDOW = 32 MB` (power of two) — RESOLVED

**sensor.py**
- Line 54: `_MAX_DECOMPRESS_BYTES = 20 * 1024 * 1024` — 20 MB application cap unchanged.
- Line 55–58: `_ZSTD_MAX_WINDOW = 32 * 1024 * 1024` — explicit power-of-two constant (2^25)
  with comment documenting the zstd window-log rounding rationale.
- Line 167: `zstandard.ZstdDecompressor(max_window_size=_ZSTD_MAX_WINDOW)` — uses the
  power-of-two constant; C-layer cap is exact at 32 MB.
- Line 168: `dctx.stream_reader(body).read(_MAX_DECOMPRESS_BYTES + 1)` — Python read capped
  at 20 MB + 1 bytes.
- Lines 169–174: `if len(raw) > _MAX_DECOMPRESS_BYTES:` — post-read rejection; payloads
  over 20 MB are rejected with HTTP 413 before the buffer is used. Confirmed.

**console_cmd.py**
- Line 49: `_MAX_DECOMPRESS_BYTES = 20 * 1024 * 1024` — unchanged.
- Lines 50–55: `_ZSTD_MAX_WINDOW = 32 * 1024 * 1024` — same power-of-two constant with
  matching comment.
- Line 275: `zstandard.ZstdDecompressor(max_window_size=_ZSTD_MAX_WINDOW)` — correct.
- Line 276: `dctx.stream_reader(data).read(_MAX_DECOMPRESS_BYTES + 1)` — correct.
- Lines 277–282: `if len(raw) > _MAX_DECOMPRESS_BYTES:` — correct post-read rejection;
  oversized payload exits with error message + `sys.exit(1)`. Confirmed.

### CR-01: db.rollback() before _audit() — NO REGRESSION

`sensor.py` lines 252, 258, 263: all three `except` branches (`DuplicatePayloadError`,
`UnknownSensorError`, bare `Exception`) call `db.rollback()` before delegating to `_audit()`.
Session is in a clean state for every audit write. Confirmed.

### CR-02: UnknownSensorError caught explicitly — NO REGRESSION

`sensor.py` line 37: `UnknownSensorError` imported at module scope. Lines 255–260: explicit
`except UnknownSensorError` block calls `db.rollback()`, writes `"unknown_sensor_id"` audit
row, raises `HTTPException(404)`. FK-race path cannot produce a 500. Confirmed.

### WR-02: "ok" audit row atomic with ingest commit — NO REGRESSION

`sensor.py` lines 272–290: `IntegrationDelivery(status="ok")` row added via `db.add(ok_row)`
before the single `db.commit()`. The flushed ingest rows and the ok audit row commit in one
transaction. The "final commit failed" path rolls back and writes a "failed" audit row.
Confirmed atomic.

### WR-03: scan_id clamped to 64 chars — NO REGRESSION

`sensor.py` line 194: `scan_id = (envelope.pushed_at or scan_id)[:64]`. Untrusted `pushed_at`
cannot overflow `IntegrationDelivery.scan_id String(64)`. Confirmed.

### WR-04: sys.exit(0) removed — NO REGRESSION

`console_cmd.py` lines 206–207 and 323–325: both success paths return normally. No
`sys.exit(0)` call anywhere in the file. Error paths retain `sys.exit(1)`. Confirmed.

### IN-01: import json at module scope — NO REGRESSION

`sensor.py` line 28: `import json` at module scope. Confirmed.

### IN-02: Field(default_factory=list) — NO REGRESSION

`sensor.py` line 83: `findings: list = Field(default_factory=list)`. `Field` imported from
pydantic at line 34. Confirmed.

---

_All reviewed files meet quality standards. No Critical or Warning issues remain._

---

_Reviewed: 2026-05-25T14:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 3 (final — WR-01a power-of-two fix confirmed clean)_
