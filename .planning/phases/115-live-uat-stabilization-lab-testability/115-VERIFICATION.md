---
phase: 115-live-uat-stabilization-lab-testability
verified: 2026-05-27T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
gaps: []
---

# Phase 115: Live-UAT Stabilization + Lab Testability Verification Report

**Phase Goal:** The four defects surfaced by the distributed E2E are root-caused and eliminated so the lab is re-runnable without teardown, and the Phase 111 per-segment filter is exercisable end-to-end against a real weak-crypto target in the distributed lab.
**Verified:** 2026-05-27T00:00:00Z
**Status:** passed (gap closed 2026-05-27)
**Re-verification:** Yes — STAB-03 gap closed; 28/28 tests pass

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Re-running console enroll for an already-provisioned sensor_id exits 0, prints no token, creates no duplicate row | VERIFIED | console_cmd.py L175-199: pre-check queries Sensor.filter(sensor_id) BEFORE secrets.token_urlsafe(32) at L199; returns normally (WR-04); "INFO: sensor already enrolled" to stderr; IntegrityError backstop retained at L236; test_enroll_idempotent_console passes |
| 2 | Re-running sensor enroll with the same sensor_id leaves sensor.yaml hmac_key unchanged and exits 0 | VERIFIED | sensor_cmd.py L248-264: pre-check reads sensor.yaml BEFORE hmac_key = secrets.token_bytes(32).hex() at L271; sys.exit(0) on match; test_enroll_idempotent_sensor_yaml passes |
| 3 | Merged console output contains zero endpoints with scanned_at=None or port=0 | VERIFIED | _read_scan_endpoints L471-472 applies filter `(scan_error_category != "missing_extra") | scan_error_category.is_(None)` — IS NULL clause present. Same function called at both push (L626) and export-results (L762). test_stab04_phantom_rows.py 2 tests pass |
| 4 | cmvp_cache.json loads via importlib.resources and is declared as wheel package-data — no 'CMVP cache unavailable' warning on merge | VERIFIED | pyproject.toml L132: `"compliance/*.json"` in package-data list. cmvp.py L29: `from importlib.resources import files as _ir_files`; L94-101: override hook for monkeypatched tests, production path uses `_ir_files("quirk.compliance").joinpath("cmvp_cache.json")`. 38 cmvp tests pass. |
| 5 | Scheduler subprocess cmd passes neither --target nor --output to run_scan; scheduled scans exit 0 | VERIFIED | --target and --output absent (static test passes). STAB-03 gap closed: `_materialize_scan_config` generates a scan config embedding `schedule.target` so config-less schedules run via `--config <generated>`. 28 tests pass: test_dispatch_lifecycle, test_startup_recovery, test_dispatch_failure_marks_failed, test_scheduler_dispatch_raises_scan_record_unaffected + 4 new targeted tests. |
| 6 | A weak-TLS target (tls-weak-b) exists on segment-b at 10.20.0.20, reachable only by sensor-b | VERIFIED | docker-compose.distributed.yml: tls-weak-b service exists, image=nginx:1.28.0, ipv4_address=10.20.0.20 on segment-b, volumes=nginx/legacy/nginx.conf+certs, expose=443, no host-port binding, no crypto.internal alias. sensor-b mounts sensor-config-b.yaml (not shared sensor-config.yaml). sensor-config-b.yaml contains 10.20.0.20 in include_ips. No sensor-a route to segment-b. |

**Score:** 6/6 truths verified (5/5 PLAN must-haves verified — STAB-03 gap closed 2026-05-27)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/cli/console_cmd.py` | Idempotent enroll pre-check before token minting | VERIFIED | pre-check at L175-199, token_urlsafe at L199 — correct order. "already enrolled" string present |
| `quirk/cli/sensor_cmd.py` | Idempotent sensor enroll + advisory-row filter in _read_scan_endpoints | VERIFIED | pre-check at L248-264, hmac_key at L271 — correct order. filter at L471-472 with IS NULL clause |
| `tests/test_stab04_phantom_rows.py` | Phantom-row regression tests | VERIFIED | File exists; 2 tests pass: test_read_scan_endpoints_excludes_advisory + test_no_phantom_rows_in_merged_output |
| `pyproject.toml` | compliance/*.json package-data declaration | VERIFIED | L132: `"compliance/*.json"` present in [tool.setuptools.package-data] quirk list |
| `quirk/compliance/cmvp.py` | importlib.resources read path for cmvp_cache.json | VERIFIED | L29 import + L94-101 load path with override hook for test isolation |
| `quirk/cli/scheduler_cmd.py` | run_scan cmd list without --target/--output + schedule.target preservation | VERIFIED | --target/--output absent. `_materialize_scan_config` generates `scan-config.generated.yaml` with schedule.target injected; passed as `--config` to run_scan. Fail-fast only when target empty AND no scan_config. 28 tests pass. |
| `tests/test_scheduler_posix_fixes.py` | STAB-03 static regression guard | VERIFIED | test_scheduler_cmd_drops_target_and_output added; 3 tests pass. NOTE: static test does not exercise runtime fail-fast path |
| `quantum-chaos-enterprise-lab/docker-compose.distributed.yml` | tls-weak-b service on segment-b | VERIFIED | Service present, nginx:1.28.0, 10.20.0.20/segment-b, legacy nginx.conf reused |
| `quantum-chaos-enterprise-lab/sensor-config-b.yaml` | sensor-b target list including the weak-TLS IP | VERIFIED | File exists; 10.20.0.20 in include_ips |
| `quantum-chaos-enterprise-lab/expected_results_distributed.md` | weak-TLS oracle rows + per-segment filter validation | VERIFIED | tls-weak-b Services table row at L53; LAB-01 Per-Segment Weak-TLS Filter Validation section at L164+ |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `sensor_cmd._read_scan_endpoints` | push envelope | SQLAlchemy filter excluding scan_error_category=missing_extra (with IS NULL clause) | VERIFIED | L471-472: `(CryptoEndpoint.scan_error_category != "missing_extra") | CryptoEndpoint.scan_error_category.is_(None)` — IS NULL clause present |
| `console_cmd._cmd_enroll` | Sensor table | pre-check query by sensor_id before secrets.token_urlsafe | VERIFIED | L189: `_pre_db.query(Sensor).filter(Sensor.sensor_id == sensor_id).first()` precedes L199: `secrets.token_urlsafe(32)` |
| `cmvp._load_cache` | quirk.compliance/cmvp_cache.json | importlib.resources.files().joinpath().read_text() | VERIFIED | L99-101: `_ir_files("quirk.compliance").joinpath("cmvp_cache.json").read_text(encoding="utf-8")` |
| `scheduler_cmd subprocess` | run_scan --config | cmd list with --config + --profile only | VERIFIED (partial) | L165: cmd = [sys.executable, "-m", "run_scan", "--config", scan_config_path] — --target and --output absent. BUT fail-fast guard crashes (see gap) |
| `sensor-b (segment-b)` | tls-weak-b (10.20.0.20:443) | sensor-config-b.yaml include_ips + segment-b network membership | VERIFIED | docker-compose mounts sensor-config-b.yaml to sensor-b; 10.20.0.20 in include_ips; tls-weak-b on segment-b only |
| `docker-compose.distributed.yml` | nginx/legacy/nginx.conf | volume mount reusing the tls-legacy pattern | VERIFIED | tls-weak-b.volumes: ['./nginx/legacy/nginx.conf:/etc/nginx/nginx.conf:ro', './certs:/etc/nginx/certs:ro'] |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Enroll idempotency tests pass | `python -m pytest tests/test_console_cmd.py -k enroll -q` | 1 passed | PASS |
| Sensor enroll idempotency tests pass | `python -m pytest tests/test_sensor_cmd.py -k enroll -q` | 11 passed | PASS |
| STAB-04 phantom-row tests pass | `python -m pytest tests/test_stab04_phantom_rows.py -q` | 2 passed | PASS |
| STAB-03 static regression guard passes | `python -m pytest tests/test_scheduler_posix_fixes.py -q` | 3 passed | PASS |
| CMVP tests pass | `python -m pytest tests/ -k cmvp -q` | 38 passed | PASS |
| Full scheduler + notify suite | `python -m pytest tests/test_scheduler_cmd.py tests/test_notify_dispatcher.py tests/test_scheduler_posix_fixes.py -q` | 28 passed | PASS |
| scheduler_cmd dispatch lifecycle | `python -m pytest tests/test_scheduler_cmd.py::test_dispatch_lifecycle -q` | 1 passed | PASS |
| scheduler_cmd startup recovery | `python -m pytest tests/test_scheduler_cmd.py::test_startup_recovery -q` | 1 passed | PASS |
| scheduler_cmd dispatch failure | `python -m pytest tests/test_scheduler_cmd.py::test_dispatch_failure_marks_failed -q` | 1 passed | PASS |
| notify dispatcher scan record | `python -m pytest tests/test_notify_dispatcher.py::test_scheduler_dispatch_raises_scan_record_unaffected -q` | 1 passed | PASS |
| Docker compose YAML valid | `python3 -c "import yaml; yaml.safe_load(open('quantum-chaos-enterprise-lab/docker-compose.distributed.yml'))"` | parsed OK | PASS |
| lab.sh bash syntax | `bash -n quantum-chaos-enterprise-lab/lab.sh` | exit 0 | PASS |
| distributed-e2e.sh bash syntax | `bash -n quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh` | exit 0 | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| STAB-01 | 115-01 | `quirk console enroll` is idempotent — re-running succeeds without duplicate rows | SATISFIED | Pre-check in both console_cmd._cmd_enroll (before token_urlsafe) and sensor_cmd._cmd_enroll (before hmac_key gen); tests pass |
| STAB-02 | 115-02 | cmvp_cache.json ships inside the installed package (declared as package data) | SATISFIED | pyproject.toml L132 compliance/*.json; cmvp.py importlib.resources load path; 38 tests pass |
| STAB-03 | 115-02 | `quirk scheduler` no longer passes unsupported --output/--target arguments; schedule.target preserved via generated config | SATISFIED | --target/--output absent. `_materialize_scan_config` generates valid scan config embedding schedule.target. Fail-fast only for empty-target + no-config case. 28 tests pass (gap closed 2026-05-27). |
| STAB-04 | 115-01 | Phantom scanned_at=None/port-0 rows eliminated from merged output | SATISFIED | filter at _read_scan_endpoints covers both push (L626) and export-results (L762); IS NULL clause present; 2 regression tests pass |
| LAB-01 | 115-03 | Distributed lab includes weak-crypto target in non-default segment; no-drift rule satisfied | SATISFIED | tls-weak-b on segment-b; sensor-config-b.yaml; expected_results_distributed.md; README; distributed-e2e.sh Test 7; lab.sh syntax clean |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `quirk/cli/scheduler_cmd.py` | — | `logger.error(...)` referencing undefined `logger` | RESOLVED | Fixed 2026-05-27: replaced with `_materialize_scan_config` approach + inline `import logging as _logging` pattern. NameError eliminated. 28 tests pass. |

---

### Human Verification Required

None required — all failures are mechanically verifiable.

---

### Gaps Summary

**0 gaps — all truths verified (gap closed 2026-05-27).**

The STAB-03 gap was resolved by implementing `schedule.target` preservation: rather than a simple fail-fast when `scan_config_path is None`, `_dispatch_schedule` now calls `_materialize_scan_config` to generate a valid `scan-config.generated.yaml` that embeds the schedule's target IP/CIDR/hostname. Config-less schedules now run correctly. The NameError on `logger` was eliminated by using the existing inline logging pattern. 28 tests pass.

---

---

## Gap Closure — 2026-05-27

**Gap:** STAB-03 verification failure — `_dispatch_schedule` crashed with `NameError` on any call where `scan_config_path is None`.

**Root cause (original):** The fail-fast guard added in Phase 115 called `logger.error(...)` but `logger` was never defined at module scope. Python raises `NameError` at runtime after `db.commit()` succeeds, leaving the function unable to return cleanly.

**Fix applied:** Replaced the fail-fast guard with a full `schedule.target`-preservation implementation:

1. Added `_classify_target(target)` — uses the stdlib `ipaddress` module to classify a bare target string as `include_ips` (IPv4/IPv6), `cidrs` (CIDR notation), or `fqdns` (hostname). No regex guessing.

2. Added `_materialize_scan_config(schedule, scan_config_path, output_dir) -> str` — builds a scan config YAML that always includes `schedule.target`. If `scan_config_path` is provided, loads it via `yaml.safe_load` and merges the target into the appropriate sub-key (append, never clobber). Otherwise starts from a minimal inert skeleton (`_MINIMAL_SCAN_CONFIG`). Sets `output.directory` to `str(output_dir)` for SENSOR-05 anchoring. Writes `output_dir/scan-config.generated.yaml` and returns its path.

3. Revised `_dispatch_schedule` fail-fast condition: now only marks failed (no Popen) when **both** `scan_config_path is None` AND `schedule.target` is empty/falsy. Schedules with a non-empty target always produce a generated config and proceed to Popen. The inline `import logging as _logging` pattern (already used elsewhere in the file) is used for the error log.

**Tests updated/added:**
- `test_dispatch_lifecycle` — now asserts cmd contains `--config` + generated path, no `--target`/`--output`, and that `scan-config.generated.yaml` embeds `127.0.0.1` under `targets.include_ips`.
- `test_scheduler_preserves_schedule_target` — focused unit test for `_materialize_scan_config` asserting target placement and `output.directory` anchoring.
- `test_classify_target_ip/cidr/hostname` — unit tests for `_classify_target`.
- `test_dispatch_empty_target_marks_failed` — asserts the narrowed fail-fast (empty target + no config → failed, no Popen).
- All pre-existing tests updated with `QUIRK_OUTPUT_DIR` env override so output trees land under `tmp_path`.

**Verification:** `python -m compileall quirk/cli/scheduler_cmd.py` → OK. `python -m pytest tests/test_scheduler_cmd.py tests/test_notify_dispatcher.py tests/test_scheduler_posix_fixes.py -q` → 28 passed.

_Gap closed: 2026-05-27_
_Verifier: Claude (gap-closure executor)_

---

_Verified: 2026-05-27T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
