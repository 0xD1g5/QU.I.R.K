---
phase: 109-console-ingestion-api
plan: "01"
subsystem: cli
tags: [console, enroll, provisioning, sensor, bearer-token, sha256]
dependency_graph:
  requires: [108-03]
  provides: [CONSOLE-01-provisioning]
  affects: [quirk/cli/console_cmd.py]
tech_stack:
  added: []
  patterns:
    - "secrets.token_urlsafe(32) + hashlib.sha256 hash-only storage (mirror of token_cmd.py)"
    - "sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)"
    - "IntegrityError rollback + fixed error string + sys.exit(1) (LEAK-02 / T-109-03)"
key_files:
  created: []
  modified:
    - quirk/cli/console_cmd.py
decisions:
  - "109-01-D-01: DB path for enroll resolved via _default_db_path() (QUIRK_DB_PATH / canonical) — no YAML parse dependency on enroll path (RESEARCH Open Question 1)"
  - "109-01-D-02: Generated sensor_id printed to stderr, raw bearer token printed to stdout — consistent with one-time-display convention"
metrics:
  duration: "~12 min"
  completed: "2026-05-25"
  tasks_completed: 2
  files_modified: 1
---

# Phase 109 Plan 01: Console Enroll Provisioning Summary

**One-liner:** `quirk console enroll` provisions a sensors row + SHA-256-hashed sensor_tokens row and prints a one-time bearer token (raw token never stored — CONSOLE-01 provisioning seam for Phase 109 push endpoint).

## What Was Built

### Task 1: `enroll` sub-parser + dispatch in `run_console`

Added the `enroll` argparse sub-parser to `run_console` in `quirk/cli/console_cmd.py`. Arguments: `--sensor-id` (optional, generates UUID4 if omitted), `--segment` (required), `--engagement` (optional), `--config` (default `config.yaml`, parity with import-results). Extended the dispatch block with `elif args.action == "enroll": _cmd_enroll(args)`. Added `import uuid` at module top.

**Commit:** `9aee4a0`

### Task 2: `_cmd_enroll` — write sensors + sensor_tokens rows, mint token

Implemented `_cmd_enroll(args)`:

- Resolves `sensor_id = args.sensor_id or str(uuid.uuid4())`. If generated, prints to stderr.
- Mints `raw_token = secrets.token_urlsafe(32)`; derives `token_hash = hashlib.sha256(raw_token.encode()).hexdigest()`.
- Creates engine via `init_db(_default_db_path())` and a `sessionmaker` session.
- Writes `Sensor(...)` row (expected_cadence_minutes=1440 default), `db.flush()`, then `SensorToken(sensor_id, token_hash, created_at)`, then `db.commit()`.
- On `IntegrityError`: `db.rollback()`, prints `"ERROR: sensor_id already enrolled"` to stderr, `sys.exit(1)`. Raw exception never printed (LEAK-02 / T-109-03).
- On success: prints raw token once to stdout with one-time-display note; prints sensor_id to stderr.

**Commit:** `0749c95`

## Inline Smoke Verification

Executed against a temp SQLite DB — replacing the empty pytest collection warning per plan-checker note:

```
exit code: 0
stdout: 'Bearer token (copy to sensor.yaml — shown once, never stored):\nc-2pu3JlaavfLOb-LSDA_D-5EUopMymU9Mn1VozyeFA\n'
PASS: sensors row OK
  sensor_id=smoke-sensor-01  segment=dmz  cadence=1440
PASS: sensor_tokens row OK
  token_hash=0e03050ae6419daaffdd751ae6dd45949de9b0b93e0f6edd0e5df1ba649d8d3c
PASS: SHA-256 hash verified (hash matches raw token)

PASS: duplicate enroll exits 1 cleanly
  stderr: 'ERROR: sensor_id already enrolled\n'
  sensors rows: 1  sensor_tokens rows: 1
PASS: no partial writes (row counts correct)
PASS: no raw exception text in stderr

PASS: omitted --sensor-id generates UUID4: ae173ac1-9a38-4421-9378-bba6a4370bfe
PASS: row written with generated sensor_id
```

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. `_cmd_enroll` is CLI-only local DB provisioning. All T-109-0x mitigations applied:

- T-109-01: raw token printed once to stdout, SHA-256 hash only in DB.
- T-109-02: IntegrityError → rollback → fixed error + sys.exit(1); no partial rows.
- T-109-03: raw exception never printed; fixed message only.

## Known Stubs

None — all acceptance criteria met; sensors + sensor_tokens rows written, bearer token minted and displayed once.

## Self-Check: PASSED

- `quirk/cli/console_cmd.py` modified and exists: FOUND
- Commit `9aee4a0` (Task 1 sub-parser): FOUND
- Commit `0749c95` (Task 2 _cmd_enroll): FOUND
- `python -m compileall quirk run_scan.py`: CLEAN
- Smoke test (sensors row + token_hash + exit 0): PASSED
- Duplicate test (exit 1, fixed message, no partial writes): PASSED
- Generated UUID test (omit --sensor-id): PASSED
- No `str(exc)` / `repr(exc)` in _cmd_enroll: CLEAN
