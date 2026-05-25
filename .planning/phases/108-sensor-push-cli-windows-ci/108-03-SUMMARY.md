---
phase: 108-sensor-push-cli-windows-ci
plan: "03"
subsystem: sensor-cli
tags: [sensor-04, air-gap, sneakernet, export-results, import-results, byte-identity, zstd]
dependency_graph:
  requires:
    - quirk.cli.sensor_cmd._build_envelope (108-02 canonical serializer)
    - quirk.cli.sensor_cmd._build_compressed_payload (108-02 canonical compressor)
    - quirk.cli.console_cmd stub (108-02 SENSOR-04 shell)
    - zstandard>=0.22.0 (108-01 dep)
  provides:
    - quirk.cli.sensor_cmd._cmd_export_results (byte-identical .qpush export)
    - quirk.cli.console_cmd._cmd_import_results (air-gap ingest stub, Phase 109 seam)
    - quirk.cli.console_cmd._ingest_envelope (Phase 109 DB-write stub)
  affects:
    - quirk/cli/sensor_cmd.py (export-results implementation)
    - quirk/cli/console_cmd.py (import-results full implementation)
    - tests/test_sensor_cmd.py (export tests added)
    - tests/test_console_cmd.py (new file)
tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN per task (test(108-03) commit before feat(108-03))
    - Byte-identity invariant enforced by regression test (export body == push body)
    - zstandard.ZstdDecompressor().decompress() + try/except for T-108-09 clean error handling
    - skip_replay_window=True air-gap carve-out per D-15
    - Single _ingest_envelope seam for Phase 109 to replace
key_files:
  created:
    - tests/test_console_cmd.py
  modified:
    - quirk/cli/sensor_cmd.py
    - quirk/cli/console_cmd.py
    - tests/test_sensor_cmd.py
decisions:
  - "_cmd_export_results stores ONLY the compressed payload bytes in .qpush — no wrapper envelope. The HMAC signature travels in the push header for HTTPS; for air-gap, Phase 109 will add HMAC verification on import using the stored hmac_key in sensor.yaml"
  - "_ingest_envelope is a Phase 108 stub that validates + prints summary; Phase 109 replaces its body with sensor_pushes dedup + CryptoEndpoint write without touching the CLI"
  - "skip_replay_window=True is passed on the air-gap path per D-15: clock-window check skipped because file transit time is unbounded for sneakernet; payload_id dedup intent preserved for Phase 109"
  - "run_scan.py console dispatch block was already wired in Plan 02 — no change needed in Plan 03"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-25"
  tasks_completed: 2
  files_changed: 4
---

# Phase 108 Plan 03: Air-Gap Sneakernet (export-results / import-results) Summary

**One-liner:** Air-gap export/import path — `quirk sensor export-results` writes a byte-identical .qpush file using the Plan 02 canonical serializers; `quirk console import-results` decompresses, validates, and routes through a single Phase 109 ingest stub with the ±15-min replay window skipped per D-15.

## What Was Built

### Task 1 — quirk sensor export-results (SENSOR-04)

Replaced the Plan 02 stub in `_cmd_export_results` with the full implementation:

- Reads `sensor.yaml` (same as push)
- Runs local scan via `_run_local_scan` to a temp dir (same as push)
- Reads `CryptoEndpoint` rows from the scan DB (same as push)
- Calls `_build_envelope(sensor_cfg, endpoints)` — the **canonical Plan 02 serializer** — no fork
- Calls `_build_compressed_payload(envelope)` — the **canonical Plan 02 compressor** — no fork
- Writes the resulting bytes to `{output}/{sensor_id}-{payload_id}.qpush`
- No httpx, no `validate_external_url`, no network I/O
- `sys.exit(0)` on success

**Byte-identity invariant:** The `.qpush` body is the compressed payload bytes — identical to what push sends as the HTTP request body — because export and push call the exact same `_build_envelope` + `_build_compressed_payload` helpers. The regression test `test_export_body_byte_identical_to_push_body` monkeypatches `payload_id` and `pushed_at` to fixed values and asserts `export_bytes == expected_push_body`. This invariant is what lets Phase 109 have one ingest implementation and Phase 110 one merge.

Test coverage added to `tests/test_sensor_cmd.py`:
- `test_export_writes_qpush_file`: file created with correct naming
- `test_export_filename_contains_payload_id`: `{sensor_id}-{payload_id}.qpush` format
- `test_export_body_byte_identical_to_push_body`: byte-identity regression test
- `test_export_decompresses_to_canonical_envelope_keys`: round-trip decompress validates key set
- `test_export_no_network_call`: httpx.Client raises if called (fail-on-network guard)

### Task 2 — quirk console import-results (SENSOR-04)

Replaced the Plan 02 stub in `quirk/cli/console_cmd.py` with the full Phase 108 implementation:

**`_cmd_import_results(args)`:**
- Reads the `.qpush` file bytes
- `zstandard.ZstdDecompressor().decompress()` wrapped in `try/except` — clean `SystemExit(1)` on non-zstd input (T-108-09)
- `json.loads` wrapped in `try/except` — clean error on invalid JSON
- Validates required envelope keys (`payload_id`, `schema_version`, `sensor_version`, `sensor_id`, `segment`, `findings`) — `SystemExit(1)` with a clear stderr message on missing keys
- Calls `_ingest_envelope(envelope, config_path, skip_replay_window=True)` — the single Phase 109 seam
- `sys.exit(0)` on success

**`_ingest_envelope(envelope, config_path, skip_replay_window=False)` (Phase 108 stub):**
- Validates and prints a summary: sensor_id, segment, payload_id, finding count, schema_version, sensor_version
- Documents the Phase 109 body replacement: sensor_pushes dedup + CryptoEndpoint write
- `skip_replay_window=True` is the air-gap carve-out per D-15: ±15-min clock window skipped; payload_id dedup preserved for Phase 109

**run_scan.py:** The `console` dispatch block was already wired in Plan 02 — no change required.

New file `tests/test_console_cmd.py`:
- `test_import_results_success_exit_zero`: valid .qpush exits 0
- `test_import_results_prints_summary`: output contains sensor_id, segment, payload_id, finding count
- `test_import_results_finding_count_nonzero`: correct count for 2-finding envelope
- `test_import_results_corrupt_file_exits_nonzero`: non-zstd → clean error, no traceback
- `test_import_results_missing_key_exits_nonzero`: missing `segment` → validation exit
- `test_import_results_missing_payload_id_exits_nonzero`: missing dedup key rejected
- `test_import_results_calls_ingest_with_skip_replay`: `skip_replay_window=True` verified
- `test_import_results_single_ingest_entry`: exactly one `_ingest_envelope` call
- `test_run_scan_console_dispatch`: run_scan.py console block wiring verified statically

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

- `quirk/cli/console_cmd.py::_ingest_envelope` — prints summary only; full DB ingest (sensor_pushes dedup + CryptoEndpoint write + received_at stamp) is Phase 109. This is intentional per the plan spec: "the actual DB write (sensor_pushes dedup + CryptoEndpoint persist) is a Phase 109 stub — validate + summarize only." The plan's goal (air-gap file roundtrip + single ingest seam) is fully achieved.

## Threat Flags

No new trust boundaries beyond those in the plan's threat model.

| Threat ID | Mitigation Implemented |
|-----------|----------------------|
| T-108-09 Tampering (malformed .qpush) | decompress + key-validation in try/except → clean SystemExit(1); `_REQUIRED_ENVELOPE_KEYS` whitelist enforced before any ingest call |
| T-108-10 Repudiation (replayed .qpush) | skip_replay_window=True omits ±15-min clock check; payload_id dedup documented for Phase 109 enforcement |
| T-108-11 Tampering (.qpush diverges from push body) | byte-equality regression test `test_export_body_byte_identical_to_push_body` enforces the invariant |

## Self-Check: PASSED

Files created/exist:
- quirk/cli/sensor_cmd.py: FOUND
- quirk/cli/console_cmd.py: FOUND
- tests/test_sensor_cmd.py: FOUND
- tests/test_console_cmd.py: FOUND

Commits exist:
- f19e691 test(108-03): add failing export-results tests RED (SENSOR-04)
- 92685cd feat(108-03): implement quirk sensor export-results — byte-identical .qpush (SENSOR-04)
- 2702d0e test(108-03): add failing console import-results tests RED (SENSOR-04)
- 7c5c676 feat(108-03): implement quirk console import-results air-gap ingest stub (SENSOR-04)
