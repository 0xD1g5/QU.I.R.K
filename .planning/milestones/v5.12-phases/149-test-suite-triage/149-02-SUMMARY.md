---
phase: 149-test-suite-triage
plan: 02
subsystem: test-infra
tags: [triage-ledger, skip-registry, xfail, ssrf-sandbox]
requires:
  - skip_registry_gate_green
  - pre_existing_triage_149_category
  - test-triage-149_ledger_skeleton
provides:
  - cluster_1_ssrf_dns_sandbox_quarantined
affects:
  - tests/test_notify_email.py
  - tests/test_notify_webhook.py
  - tests/test_ticketing_servicenow.py
  - tests/test_sensor_cmd.py
  - tests/skip_registry.py
  - docs/test-triage-149.md
tech-stack:
  added: []
  patterns:
    - "xfail(strict=False) + pre_existing_triage_149 registry entry + ledger row, per Plan 01's established convention"
key-files:
  created: []
  modified:
    - tests/test_notify_email.py
    - tests/test_notify_webhook.py
    - tests/test_ticketing_servicenow.py
    - tests/test_sensor_cmd.py
    - tests/skip_registry.py
    - docs/test-triage-149.md
decisions:
  - "All 23 Cluster 1 tests dispositioned quarantined-xfail (never quarantined-skip) since every failure still exercises real code up to the SSRF DNS-resolution boundary and is expected to pass on a DNS-enabled runner (per D-03/RESEARCH.md row 1)"
metrics:
  duration: 20min
  completed: 2026-08-12
---

# Phase 149 Plan 02: Cluster 1 (SSRF/DNS-blocked sandbox) Quarantine Summary

Quarantined all 23 Cluster-1 test failures — `ValueError: SSRF blocked (dns_failure)` /
its downstream `assert 1 == 0` symptoms in `_cmd_push` — across
`test_notify_email.py`, `test_notify_webhook.py`, `test_ticketing_servicenow.py`, and
`test_sensor_cmd.py`, with `xfail(strict=False)` markers, matching
`pre_existing_triage_149` registry entries, and 23 ledger rows citing evidence.

## What Was Built

### Task 1: `test_notify_email.py` + `test_notify_webhook.py` (8 tests)

Reproduced the 8 failures live first (`ValueError: SSRF blocked (dns_failure)` from
`validate_external_url`, since this sandbox has no outbound DNS resolution). Added
`@pytest.mark.xfail(reason="TRIAGE-149: ...", strict=False)` above each of
`test_starttls_path_timeout_and_recipients`, `test_ssl_path_timeout_passed`,
`test_no_login_when_smtp_user_none` (email) and `test_no_hmac_when_key_env_not_set`,
`test_hmac_header_present_when_key_set`, `test_hmac_absent_when_key_env_empty`,
`test_body_omits_topology_keys`, `test_non_2xx_raises_runtime_error` (webhook). Added 8
matching `ALLOWED_SKIPS` tuples under a new `# Phase 149 D-02/D-03` banner in
`tests/skip_registry.py`, category `pre_existing_triage_149`. Result: 8 xfailed, 0
failed.

### Task 2: `test_ticketing_servicenow.py` + `test_sensor_cmd.py` (15 tests)

Reproduced the 15 failures live (6 `ValueError: SSRF blocked (dns_failure)` in
ServiceNow's `instance_url` validation, 9 `_cmd_push`/`_cmd_export_results` failures
downstream of the same SSRF-blocked console URL, surfacing as `assert 1 == 0` /
`AssertionError` once the retry/spool logic never got network access to exercise).
Applied the identical xfail pattern to `test_create_incident`,
`test_dedup_then_work_notes`, `test_correlation_id_is_fingerprint`,
`test_credentials_not_in_logs`, `test_create_issue_missing_sys_id_raises_runtime_error`,
`test_create_issue_non_json_response_raises_runtime_error` (servicenow) and
`test_push_posts_to_correct_url`, `test_push_retry_on_5xx`, `test_push_no_retry_on_4xx`,
`test_push_connect_error_retries`, `test_push_409_treated_as_success`,
`test_spool_on_connect_failure`, `test_spool_flush_delivers_and_unlinks`,
`test_spool_409_unlinks_file`, `test_spool_filename_is_uuid_pattern` (sensor_cmd). Added
15 matching `ALLOWED_SKIPS` entries under the same banner. Result: 15 xfailed, 0 failed.

Note: after adding each `xfail` decorator, the function's line number in the file shifts
by 4 lines relative to the pre-decorator layout; registry `line_number` values use the
actual post-edit decorator line (confirmed via `grep -n "@pytest.mark.xfail"`), not the
pre-edit function-def line, so every entry sits within the meta-gate's ±2-line tolerance.

### Task 3: Cluster 1 ledger rows + meta-gate verification

Added 23 rows under `## Cluster 1: SSRF/DNS-blocked sandbox` in
`docs/test-triage-149.md`, each with `Disposition = quarantined-xfail`,
`Sub-reason = environment-dependent (SSRF DNS-blocked sandbox)`, the exact failure
evidence (`ValueError: SSRF blocked (dns_failure)` for the direct-validation tests,
`ERROR: console URL blocked by SSRF allowlist — dns_failure` plus the downstream
assertion symptom for the `_cmd_push`-path tests), a note that the test is expected to
pass on a DNS-enabled runner and should be re-verified in Phase 150, and the exact
`tests/skip_registry.py:<line>` citation. Ran
`pytest tests/test_skip_registry.py -q -m ""` — 1 passed, confirming the meta-gate
stayed green after the 23 new decorators.

## Deviations from Plan

None — plan executed exactly as written. One self-caught arithmetic slip during Task 3
(an initial registry line-number carry-over from the pre-edit file state) was corrected
in the same task before commit, not a post-hoc fix.

## Verification

- `pytest tests/test_notify_email.py tests/test_notify_webhook.py tests/test_ticketing_servicenow.py tests/test_sensor_cmd.py -q -m ""` → 39 passed, 23 xfailed
- `pytest tests/test_skip_registry.py -q -m ""` → 1 passed
- `docs/test-triage-149.md` Cluster 1 table has 23 rows (confirmed via `grep -c`, accounting for 1 unrelated legend-line match)

## Self-Check

- `tests/test_notify_email.py` modified: FOUND
- `tests/test_notify_webhook.py` modified: FOUND
- `tests/test_ticketing_servicenow.py` modified: FOUND
- `tests/test_sensor_cmd.py` modified: FOUND
- `tests/skip_registry.py` modified: FOUND
- `docs/test-triage-149.md` modified: FOUND
- Commit `bff8215` (Task 1): FOUND
- Commit `02cec26` (Task 2): FOUND
- Commit `36c1db5` (Task 3): FOUND
- `pytest tests/test_skip_registry.py -q -m ""` exits 0: CONFIRMED (1 passed)
- Full Cluster 1 scope: CONFIRMED (39 passed, 23 xfailed, 0 failed)

## Self-Check: PASSED
