---
phase: 108-sensor-push-cli-windows-ci
verified: 2026-05-25T22:15:19Z
status: human_needed
score: 7/7 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run quirk sensor enroll against a real or stubbed HTTPS console; check sensor.yaml written, token printed once, not stored"
    expected: "sensor.yaml written atomically at platformdirs config path; enrollment token visible on stdout with 'shown once' warning; token absent from sensor.yaml content"
    why_human: "Enrollment flow requires a live or stub HTTPS endpoint; filesystem + stdout inspection in a real terminal confirms the one-time token UX"
  - test: "Run quirk sensor push with a real scan config; observe spool behavior by blocking the console endpoint"
    expected: "push triggers local run_scan subprocess, payload POSTed with HMAC signature; blocking the console produces a .json.zst spool file; next push delivers the spool FIFO"
    why_human: "End-to-end push requires a running HTTPS console or proxy; spool retry behavior is time-sensitive and subprocess-dependent"
  - test: "Confirm Windows CI job actually runs on a windows-latest GitHub Actions runner and blocks PR merge on failure"
    expected: "windows-sensor-smoke job appears in Actions checks; status is red when test fails, green when passing; no 'skipped' or 'continue-on-error' bypass"
    why_human: "Hard-gate enforcement can only be verified by actually failing the workflow on GitHub — local static tests confirm the YAML is correct but cannot verify GitHub's branch-protection respects the job"
---

# Phase 108: Sensor Push CLI + Windows CI Verification Report

**Phase Goal:** A consultant can enroll a sensor and push results from any OS, with Windows correctness validated on a real Windows runner before merging.
**Verified:** 2026-05-25T22:15:19Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `_NoRedirectHandler` is importable from `quirk.util.no_redirect`; webhook.py and servicenow.py no longer define it locally | VERIFIED | `quirk/util/no_redirect.py` exists; `grep -c "class _NoRedirectHandler"` returns 0 in both importers; both files contain `from quirk.util.no_redirect import _NoRedirectHandler`; `test_no_redirect_extraction.py` passes |
| 2 | `quirk sensor enroll` writes `sensor.yaml` atomically with all required fields; one-time enrollment token printed but NOT stored | VERIFIED | `sensor_cfg` dict at L192–200 contains `console_url, sensor_id, segment, engagement, sensor_version, hmac_key, console_api_token`; `raw_token` is printed at L206 but absent from `sensor_cfg`; atomic write via `_write_sensor_config`; 26 test_sensor_cmd.py tests pass (all 26 PASSED) |
| 3 | `quirk sensor push` uses `verify=True` hardcoded, `follow_redirects=False`; `verify=False` grep gate test exists and passes | VERIFIED | `httpx.Client(verify=True, follow_redirects=False)` at L490–491; no override parameter; `test_sensor_no_verify_false.py` passes with comment-stripped tokenize scan over `sensor_cmd.py` and `console_cmd.py` |
| 4 | tenacity retry: 5xx triggers retry; 4xx does NOT retry; bounded spool dir, FIFO retry, delete on 200/409 | VERIFIED | `_do_push` raises via `resp.raise_for_status()` only when `status_code >= 500` (L324–325); `_is_retryable` is isinstance-gated on `httpx.ConnectError` and `httpx.TimeoutException` + `httpx.HTTPStatusError`; spool at L366–430 uses `_SPOOL_MAX_FILES=100`, `_SPOOL_MAX_BYTES=500MB`; FIFO via `sorted(..., key=lambda p: p.stat().st_mtime)`; unlinks on 200/409 at L419–420; spool tests PASSED |
| 5 | `quirk sensor export-results` produces byte-identical payload to `quirk sensor push` body; `quirk console import-results` routes through `_ingest_envelope` stub skipping ±15-min window, keeping `payload_id` dedup intent | VERIFIED | `test_export_body_byte_identical_to_push_body` PASSED; `_build_compressed_payload` shared by both paths; `_cmd_import_results` calls `_ingest_envelope(envelope, config_path, skip_replay_window=True)` at L113–114; dedup enforcement deferred to Phase 109 as designed (explicitly noted in code comments and confirmed by Phase 109 roadmap) |
| 6 | `scheduler_cmd.py` POSIX-isms fixed: output dir anchored to `cfg.output.directory`; SIGTERM guarded by `sys.platform != "win32"` | VERIFIED | `Path(cfg.output.directory)` at L145; `if sys.platform != "win32":` at L283 governs `signal.signal(signal.SIGTERM, ...)` at L284; `test_scheduler_posix_fixes.py` passes with comment-stripped static assertions |
| 7 | `windows-latest` CI job in `.github/workflows/python-ci.yml` with ZERO `continue-on-error`; smoke tests assert no-backslash payload + clean shutdown; static hard-gate test passes | VERIFIED | `.github/workflows/python-ci.yml` has `runs-on: windows-latest`; `grep -c "continue-on-error" python-ci.yml` returns 0; `test_sensor_windows_smoke.py` has `TestNoBackslashInPayload` + `TestCleanShutdownOnKeyboardInterrupt` classes; `test_windows_ci_hardgate.py` passes asserting no `continue-on-error: true` |

**Score:** 7/7 truths verified

---

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | `payload_id` uniqueness dedup enforcement in `_ingest_envelope` (currently a stub) | Phase 109 | Phase 109 roadmap: "payload-ID dedup, clock-skew window"; `console_cmd.py` comment: "DB ingest (sensor_pushes dedup + CryptoEndpoint write) is Phase 109" |

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/util/no_redirect.py` | Single-source `_NoRedirectHandler` SSRF redirect guard | VERIFIED | Exists; `class _NoRedirectHandler(urllib.request.HTTPRedirectHandler)` at L12 |
| `tests/test_no_redirect_extraction.py` | STAB-02 import + no-duplicate-definition guard | VERIFIED | Exists; tests pass |
| `tests/test_scheduler_posix_fixes.py` | SENSOR-05 POSIX-ism regression tests | VERIFIED | Exists; tests pass |
| `quirk/cli/sensor_cmd.py` | `run_sensor()`, `_build_envelope`, `_build_compressed_payload`, enroll/push/export subcommands, spool manager | VERIFIED | Exists; all functions present; 26 tests pass |
| `tests/test_sensor_cmd.py` | SENSOR-01/02/03/04 unit coverage | VERIFIED | Exists; 26 tests all PASSED |
| `tests/test_sensor_no_verify_false.py` | SENSOR-02 TLS-verify grep gate | VERIFIED | Exists; parametrized over sensor_cmd.py and console_cmd.py; passes |
| `quirk/cli/console_cmd.py` | `run_console()`, `import-results` subcommand, `_ingest_envelope` stub | VERIFIED | Exists; 9 test_console_cmd.py tests pass |
| `tests/test_console_cmd.py` | SENSOR-04 import-results coverage | VERIFIED | Exists; 9 tests PASSED |
| `.github/workflows/python-ci.yml` | `windows-latest` hard-gate sensor smoke job | VERIFIED | Exists; `windows-sensor-smoke` job; 0 `continue-on-error` |
| `tests/test_sensor_windows_smoke.py` | SENSOR-06 backslash + clean-shutdown assertions | VERIFIED | Exists; `TestNoBackslashInPayload` and `TestCleanShutdownOnKeyboardInterrupt` classes; tests pass |
| `tests/test_windows_ci_hardgate.py` | Static guard that CI job is windows-latest with no continue-on-error | VERIFIED | Exists; passes |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/notify/channels/webhook.py` | `quirk/util/no_redirect.py` | `from quirk.util.no_redirect import _NoRedirectHandler` | WIRED | Import at L24 verified; no local class definition remains |
| `quirk/ticketing/servicenow.py` | `quirk/util/no_redirect.py` | `from quirk.util.no_redirect import _NoRedirectHandler` | WIRED | Import at L28 verified; no local class definition remains |
| `run_scan.py` | `quirk/cli/sensor_cmd.py` | `from quirk.cli.sensor_cmd import run_sensor` in `argv[1] == "sensor"` dispatch | WIRED | L509–511 in run_scan.py; test `test_run_scan_sensor_dispatch` passes |
| `run_scan.py` | `quirk/cli/console_cmd.py` | `from quirk.cli.console_cmd import run_console` in `argv[1] == "console"` dispatch | WIRED | L515–517 in run_scan.py; test `test_run_scan_console_dispatch` passes |
| `quirk/cli/sensor_cmd.py` | `quirk/util/url_allowlist.py` | `validate_external_url(console_url)` before any connection | WIRED | `validate_external_url` called in `_cmd_enroll` (L162) and `_cmd_push` (L449) |
| `quirk/cli/sensor_cmd.py export-results` | `_build_compressed_payload` | Export reuses identical envelope + compression helpers as push | WIRED | Same `_build_envelope`/`_build_compressed_payload` functions called in both paths; byte-equality test passes |
| `.github/workflows/python-ci.yml` | `tests/test_sensor_windows_smoke.py` | pytest invocation in windows-sensor-smoke job | WIRED | `pytest tests/test_sensor_windows_smoke.py tests/test_sensor_no_verify_false.py -v` in CI step |

---

### Data-Flow Trace (Level 4)

Not applicable — phase delivers CLI commands and test infrastructure, not dashboard/data rendering components.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 60 phase tests pass | `pytest tests/test_sensor_cmd.py tests/test_console_cmd.py tests/test_sensor_no_verify_false.py tests/test_sensor_windows_smoke.py tests/test_windows_ci_hardgate.py tests/test_no_redirect_extraction.py tests/test_scheduler_posix_fixes.py -q` | 60 passed, 26 warnings in 0.83s | PASS |
| Compile check | `python -m compileall quirk run_scan.py -q` | No errors, exit 0 | PASS |
| byte-identical export/push invariant | `pytest tests/test_sensor_cmd.py::test_export_body_byte_identical_to_push_body -v` | 1 passed | PASS |
| verify=False grep gate | `pytest tests/test_sensor_no_verify_false.py -v` | 2 passed | PASS |
| CI hard-gate static check | `pytest tests/test_windows_ci_hardgate.py -v` | 4 passed | PASS |
| no-backslash payload + clean shutdown smoke | `pytest tests/test_sensor_windows_smoke.py -v` | 9 passed | PASS |

---

### Probe Execution

No `scripts/*/tests/probe-*.sh` probes declared or found for this phase.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| STAB-02 | 108-01 | `_NoRedirectHandler` extracted to single module | SATISFIED | `quirk/util/no_redirect.py` exists; both importers use it; tests pass |
| SENSOR-05 | 108-01 | Scheduler POSIX-ism fixes + `platformdirs` | SATISFIED | `cfg.output.directory` anchor + `sys.platform != "win32"` SIGTERM guard in `scheduler_cmd.py`; `platformdirs>=4.3.0` in `pyproject.toml` core deps |
| SENSOR-01 | 108-02 | `quirk sensor enroll` writes bound `sensor.yaml` + prints one-time token | SATISFIED | Code, wiring, and 26 unit tests verified. REQUIREMENTS.md tracker row still shows `Pending` — tracker staleness only; code delivers the requirement |
| SENSOR-02 | 108-02 | `quirk sensor push` over HTTPS with `verify=True` + tenacity retry | SATISFIED | `httpx.Client(verify=True)` hardcoded; `stop_after_attempt(5)` with 5xx/network retry, 4xx no-retry; grep gate passes. Tracker shows `Pending` — staleness only |
| SENSOR-03 | 108-02 | Bounded spool dir, FIFO retry, delete on 200/409 | SATISFIED | `_spool_dir`, `_evict_if_full` (100 files / 500MB), `_flush_spool` with mtime-sorted FIFO; unlink on 200/409. Tracker shows `Pending` — staleness only |
| SENSOR-04 | 108-03 | Byte-identical `.qpush` export + `console import-results` ingest stub | SATISFIED | Byte-equality test passes; `_ingest_envelope(skip_replay_window=True)` wired; payload_id dedup deferred to Phase 109 as designed |
| SENSOR-06 | 108-04 | `windows-latest` CI hard gate | SATISFIED | CI YAML exists with `windows-latest`, 0 `continue-on-error`; smoke + hardgate tests pass |

**REQUIREMENTS.md staleness WARNING:** SENSOR-01, SENSOR-02, SENSOR-03 are marked `- [ ]` (unchecked) and `Pending` in the coverage table. The code fully implements all three. This is a tracker update miss, not a code gap.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `quirk/cli/sensor_cmd.py` | 271 | `datetime.utcnow()` deprecated (DeprecationWarning from Python 3.12+) | Info | Cosmetic; does not affect behavior in Python 3.11 target; 26 warnings emitted during test run. No fix required for Phase 108. |

No `TBD`, `FIXME`, or `XXX` debt markers found in phase-modified files. No stubs blocking goal achievement.

---

### Human Verification Required

#### 1. Live Sensor Enroll + sensor.yaml Inspection

**Test:** Run `quirk sensor enroll https://console.example.com --segment dmz --config /tmp/test-sensor.yaml` (console URL may be unreachable; an SSRF-guard rejection is expected for non-routable addresses — use a reachable HTTPS endpoint or mock). Then `cat /tmp/test-sensor.yaml` and confirm the raw enrollment token printed to stdout is absent from the file.
**Expected:** `sensor.yaml` contains `console_url`, `sensor_id` (UUID), `segment`, `engagement`, `sensor_version`, `hmac_key` (64 hex chars), `console_api_token`; the one-time token printed to stdout does not appear anywhere in the YAML content.
**Why human:** The "shown once" UX contract requires visual confirmation of terminal output and file content in a real session.

#### 2. Spool Round-Trip Verification

**Test:** With the console endpoint unreachable (e.g., blocked port), run `quirk sensor push`. Then restore connectivity and run `quirk sensor push` again. Check `platformdirs.user_data_dir("quirk")/spool/` between runs.
**Expected:** First push leaves one `*.json.zst` spool file; second push delivers it (FIFO) and the spool directory is empty afterward.
**Why human:** Subprocess scan + real network stack required; time-sensitive FIFO ordering not reproducible with pure mock tests.

#### 3. GitHub Actions Windows Hard Gate

**Test:** Open a PR that intentionally fails `tests/test_sensor_windows_smoke.py` (e.g., temporarily revert the `chr(92)` assert). Confirm the `windows-sensor-smoke` check appears as a required check that blocks merging.
**Expected:** GitHub Actions shows the `windows-sensor-smoke` job as failed and red; the PR cannot be merged until the job passes.
**Why human:** Branch protection rules and required status checks are a GitHub configuration concern that cannot be verified by reading the YAML file alone.

---

### Gaps Summary

No code gaps. All 7 must-have truths are VERIFIED. The only issues found are:

1. **REQUIREMENTS.md tracker staleness (WARNING):** SENSOR-01, SENSOR-02, SENSOR-03 rows remain `- [ ]` / `Pending`. The implementation is complete. The tracker should be updated to `[x]` / `Complete` to match actual state.

2. **`datetime.utcnow()` deprecation (INFO):** Used at `sensor_cmd.py:271`; emits 26 DeprecationWarnings during test run. Not a blocker for Python 3.11 target. Suggested cleanup in a future debt phase.

Automated checks passed. Three human verification items remain — two UX/runtime behaviors and one GitHub branch-protection confirmation.

---

_Verified: 2026-05-25T22:15:19Z_
_Verifier: Claude (gsd-verifier)_
