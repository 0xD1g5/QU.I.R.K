---
phase: 108-sensor-push-cli-windows-ci
plan: "02"
subsystem: sensor-cli
tags: [sensor-01, sensor-02, sensor-03, ssrf, tls-enforcement, store-and-forward, wire-contract]
dependency_graph:
  requires:
    - quirk.util.no_redirect._NoRedirectHandler (108-01 STAB-02)
    - platformdirs>=4.3.0 (108-01 dep)
    - tenacity>=8.2.0 (108-01 dep)
    - zstandard>=0.22.0 (108-01 dep)
  provides:
    - quirk.cli.sensor_cmd.run_sensor (CLI entrypoint)
    - quirk.cli.sensor_cmd._build_envelope (canonical wire serializer — Plan 03 MUST reuse)
    - quirk.cli.sensor_cmd._build_compressed_payload (canonical compressor — Plan 03 MUST reuse)
    - quirk.cli.console_cmd.run_console (stub for Phase 109)
    - run_scan.py sensor + console dispatch blocks
  affects:
    - run_scan.py (two new dispatch blocks: sensor, console)
tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN per task (test(108-02) commit before feat(108-02))
    - Atomic YAML write via tempfile + os.replace (token_cmd idiom)
    - tenacity @retry with _is_retryable (ConnectError | TimeoutException | HTTPStatusError)
    - httpx.Client verify=True follow_redirects=False hardcoded — no override parameter
    - File-per-payload bounded spool (100 files / 500 MB, oldest-eviction FIFO)
    - tokenize-based verify=False grep gate (test_phase57_invariants.py pattern)
key_files:
  created:
    - quirk/cli/sensor_cmd.py
    - quirk/cli/console_cmd.py
    - tests/test_sensor_cmd.py
    - tests/test_sensor_no_verify_false.py
  modified:
    - run_scan.py
decisions:
  - "_is_retryable includes httpx.HTTPStatusError so 5xx responses trigger tenacity retry (ConnectError/TimeoutException for network failures, HTTPStatusError only when status>=500 per _do_push gate)"
  - "_spool_payload calls os.makedirs on the spool dir to handle monkeypatched dirs that don't exist yet (test isolation requirement)"
  - "console_cmd.py stub docstring avoids the literal 'verify=False' string to pass the grep gate cleanly"
  - "_run_local_scan docstring avoids the literal 'run_scan.main()' string to pass the subprocess-only grep gate cleanly"
metrics:
  duration: "~40 minutes"
  completed: "2026-05-25"
  tasks_completed: 3
  files_changed: 5
---

# Phase 108 Plan 02: Sensor Push CLI (enroll/push/spool) Summary

**One-liner:** Sensor agent CLI — atomic sensor.yaml enrollment with one-time token, HMAC-signed zstd-compressed wire envelope over httpx verify=True HTTPS with tenacity retry (5xx/network retries, 4xx no-retry), and bounded self-evicting store-and-forward spool.

## What Was Built

### Task 1 — quirk sensor enroll (SENSOR-01)

Created `quirk/cli/sensor_cmd.py` with the `run_sensor(argv)` entrypoint following the `token_cmd.py` subparser shape. The `enroll` subcommand:

- Calls `validate_external_url(console_url)` before any I/O (T-108-04 SSRF guard)
- Mints `sensor_id = uuid.uuid4()`, `hmac_key = secrets.token_bytes(32).hex()`, and a one-time `raw_token = secrets.token_urlsafe(32)`
- Writes `sensor.yaml` atomically via `_write_sensor_config` (tempfile + os.replace idiom from `token_cmd.py`) containing: `console_url`, `sensor_id`, `segment`, `engagement`, `sensor_version`, `hmac_key`, `console_api_token`
- Creates the config directory with `os.makedirs(exist_ok=True)` for fresh-system support
- Prints the raw enrollment token once to stdout with a "shown once" warning to stderr
- **Never writes the raw enrollment token to sensor.yaml** (T-108-05)

Also created `quirk/cli/console_cmd.py` stub with `run_console(argv)` and `import-results` subparser shape for Phase 109 wiring.

Added `sensor` and `console` dispatch blocks to `run_scan.py` (lazy import, after the `ticket` block, before `errors`).

### Task 2 — quirk sensor push (SENSOR-02)

Added `push` subcommand and canonical wire-envelope helpers to `sensor_cmd.py`:

**`_build_envelope(sensor_cfg, endpoints)`:** Returns `{payload_id, pushed_at, schema_version, sensor_version, sensor_id, segment, findings}`. `received_at` is intentionally absent (console stamps it on ingest, Phase 109). This is the **canonical serializer** — Plan 03 `export-results` MUST reuse this function byte-for-byte.

**`_build_compressed_payload(envelope)`:** JSON-encodes the envelope and compresses with `zstandard.ZstdCompressor(level=3)`. Also canonical for Plan 03.

**`_sign(body, key)`:** Returns `"hmac-sha256=" + hmac.new(key, body, sha256).hexdigest()`.

**`_do_push`:** tenacity-decorated POST function. Retries on `httpx.ConnectError`, `httpx.TimeoutException`, and `httpx.HTTPStatusError` (the last only fires when `status >= 500`). 4xx responses return normally without retry. The `httpx.Client` is constructed with `verify=True, follow_redirects=False` hardcoded — no override parameter.

**`_cmd_push`:** Reads sensor.yaml, validates URL (SSRF guard), runs local scan via `_run_local_scan` (subprocess list-form, no `shell=True`), reads `CryptoEndpoint` rows from the scan DB, builds + signs + pushes the envelope. 200 and 409 are both treated as delivered success. On terminal connection failure, calls `_spool_payload`.

Created `tests/test_sensor_no_verify_false.py` — parametrized tokenize-based grep gate over `sensor_cmd.py` and `console_cmd.py` asserting `verify=False` is absent from comment-stripped source (T-108-03).

### Task 3 — Store-and-forward spool (SENSOR-03)

Added spool helpers to `sensor_cmd.py`:

**`_spool_dir()`:** Returns `platformdirs.user_data_dir("quirk") / "spool"` with `os.makedirs(exist_ok=True)`.

**`_evict_if_full(spool_dir)`:** Sorts `*.json.zst` by mtime; evicts oldest while `len >= _SPOOL_MAX_FILES (100)` or `total_bytes > _SPOOL_MAX_BYTES (500 MB)`. Prints a stderr warning per eviction.

**`_spool_payload(payload_id, body)`:** Calls `_evict_if_full` then writes `{payload_id}.json.zst`. Filename is UUID-only (T-108-08: no operator-controlled path components).

**`_flush_spool(client, push_url, headers_fn)`:** Called at the start of every `_cmd_push`; iterates spooled files oldest-first, re-pushes via `_do_push`, unlinks on 200 or 409, leaves on connection failure. v5.4 is single-process — no file lock required (RESEARCH Pitfall 7).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_is_retryable` must include `httpx.HTTPStatusError` to retry 5xx**
- **Found during:** Task 2 — test_push_retry_on_5xx failed because the initial `_is_retryable` only checked `ConnectError` and `TimeoutException`; `raise_for_status()` for 5xx raises `HTTPStatusError` which was not caught
- **Fix:** Added `httpx.HTTPStatusError` to the `isinstance` check in `_is_retryable`. The 4xx no-retry invariant is preserved because `_do_push` only calls `raise_for_status()` when `status >= 500`
- **Files modified:** `quirk/cli/sensor_cmd.py`

**2. [Rule 1 - Bug] `_spool_payload` must call `os.makedirs` on the returned spool dir**
- **Found during:** Task 3 — test_spool_on_connect_failure raised `FileNotFoundError` when spool dir was monkeypatched to a non-existent tmp path
- **Fix:** Added `os.makedirs(d, exist_ok=True)` inside `_spool_payload` (after calling `_spool_dir()`) so the dir is created whether or not it's the real platformdirs path
- **Files modified:** `quirk/cli/sensor_cmd.py`

**3. [Rule 1 - Bug] Docstrings in `console_cmd.py` and `sensor_cmd.py` triggered grep gate false-positives**
- **Found during:** Task 2 verify=False test — `console_cmd.py` docstring contained "verify=False" literally; `sensor_cmd.py` had "run_scan.main()" in a comment
- **Fix:** Rewrote the relevant docstring sentences to avoid the literal forbidden strings while preserving the semantic meaning
- **Files modified:** `quirk/cli/console_cmd.py`, `quirk/cli/sensor_cmd.py`

**4. [Rule 1 - Bug] monkeypatch must target `quirk.cli.sensor_cmd.validate_external_url` (not `quirk.util.url_allowlist.validate_external_url`)**
- **Found during:** Task 1 — `test_enroll_ssrf_guard_exits_nonzero` passed incorrect mock (module-level binding already captured at import time)
- **Fix:** Updated all test monkeypatches to patch the attribute on the sensor_cmd module object directly
- **Files modified:** `tests/test_sensor_cmd.py`

## Known Stubs

- `quirk/cli/console_cmd.py::_cmd_import_results` — exits 1 with "not yet implemented"; full air-gap import ingest wired in Phase 109
- `quirk/cli/sensor_cmd.py::_cmd_export_results` — exits 1 with "not yet implemented"; Plan 03 implements using `_build_envelope` + `_build_compressed_payload` byte-identically

## Threat Flags

No new trust boundaries beyond those in the plan's threat model. All six T-108-0X mitigations are implemented:

| Threat | Mitigation implemented |
|--------|----------------------|
| T-108-03 TLS downgrade | `httpx.Client(verify=True)` hardcoded + grep gate test |
| T-108-04 SSRF redirect | `validate_external_url` in enroll + push; `follow_redirects=False` |
| T-108-05 Token leak | Raw token printed once, never written to sensor.yaml |
| T-108-06 Payload replay | `payload_id = uuid4()` per push; console dedup → 409 (Phase 109) |
| T-108-07 Spool DoS | `_evict_if_full` caps at 100 files / 500 MB with oldest-eviction |
| T-108-08 Path traversal in spool | Filename is `{uuid4}.json.zst` only |

## Self-Check: PASSED

Files created/exist:
- quirk/cli/sensor_cmd.py: FOUND
- quirk/cli/console_cmd.py: FOUND
- tests/test_sensor_cmd.py: FOUND
- tests/test_sensor_no_verify_false.py: FOUND

Commits exist:
- 82615fc test(108-02): add failing tests for sensor enroll/push/spool RED
- 8ac6388 test(108-02): add verify=False grep gate RED
- 821cb20 feat(108-02): implement quirk sensor enroll/push/spool + console stub
