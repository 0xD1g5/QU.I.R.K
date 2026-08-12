# Phase 149 Test Suite Triage Ledger (SUITE-01)

This ledger tracks the disposition of every currently-failing test in QU.I.R.K.'s full
suite, one cluster at a time. Each of Plans 02-10 in Phase 149 owns one or more clusters
below, investigates every failing test in scope, and appends a row to that cluster's
table recording how the failure was resolved (fixed, quarantined, deleted, or
environment-fixed). This file is the single source of truth for the triage effort — no
test is dropped silently; every disposition is either a code fix, a documented
quarantine entry in `tests/skip_registry.py`, or an explicit deletion with rationale.

Built against: `pytest -q -m ""` → 113 failed, 3078 passed, 22 skipped, 125 warnings — 2026-08-11

## Status Legend

- **fixed** — the underlying code or test defect was corrected; the test now passes
  legitimately.
- **quarantined-skip** — the test is marked `pytest.skip()` / `@pytest.mark.skipif` with
  a `pre_existing_triage_149`-category entry in `tests/skip_registry.py`, pending a
  follow-up fix outside this phase's scope.
- **quarantined-xfail** — the test is marked `@pytest.mark.xfail` with a
  `pre_existing_triage_149`-category entry in `tests/skip_registry.py`, expected to fail
  until a follow-up fix lands.
- **deleted** — the test (or the marker) was removed because it tests behavior/a module
  that no longer exists, confirmed via grep/read (mirrors D-05 from Phase 41).
- **environment-fix-applied** — the test failure was caused by a dev-environment gap
  (missing optional extra, stale local state, etc.) that was fixed at the environment
  level rather than in test or production code.

## Cluster 1: SSRF/DNS-blocked sandbox

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|
| `test_notify_email.py::test_starttls_path_timeout_and_recipients` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ValueError: SSRF blocked (dns_failure)`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:75) |
| `test_notify_email.py::test_ssl_path_timeout_passed` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ValueError: SSRF blocked (dns_failure)`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:76) |
| `test_notify_email.py::test_no_login_when_smtp_user_none` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ValueError: SSRF blocked (dns_failure)`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:77) |
| `test_notify_webhook.py::test_no_hmac_when_key_env_not_set` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ValueError: SSRF blocked (dns_failure)`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:78) |
| `test_notify_webhook.py::test_hmac_header_present_when_key_set` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ValueError: SSRF blocked (dns_failure)`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:79) |
| `test_notify_webhook.py::test_hmac_absent_when_key_env_empty` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ValueError: SSRF blocked (dns_failure)`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:80) |
| `test_notify_webhook.py::test_body_omits_topology_keys` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ValueError: SSRF blocked (dns_failure)`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:81) |
| `test_notify_webhook.py::test_non_2xx_raises_runtime_error` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ValueError: SSRF blocked (dns_failure)`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:82) |
| `test_ticketing_servicenow.py::test_create_incident` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ValueError: SSRF blocked (dns_failure)`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:83) |
| `test_ticketing_servicenow.py::test_dedup_then_work_notes` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ValueError: SSRF blocked (dns_failure)`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:84) |
| `test_ticketing_servicenow.py::test_correlation_id_is_fingerprint` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ValueError: SSRF blocked (dns_failure)`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:85) |
| `test_ticketing_servicenow.py::test_credentials_not_in_logs` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ValueError: SSRF blocked (dns_failure)`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:86) |
| `test_ticketing_servicenow.py::test_create_issue_missing_sys_id_raises_runtime_error` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ValueError: SSRF blocked (dns_failure)`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:87) |
| `test_ticketing_servicenow.py::test_create_issue_non_json_response_raises_runtime_error` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ValueError: SSRF blocked (dns_failure)`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:88) |
| `test_sensor_cmd.py::test_push_posts_to_correct_url` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ERROR: console URL blocked by SSRF allowlist — dns_failure` (assert 1 == 0); expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:89) |
| `test_sensor_cmd.py::test_push_retry_on_5xx` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ERROR: console URL blocked by SSRF allowlist — dns_failure` (AssertionError: 5xx retry never reached); expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:90) |
| `test_sensor_cmd.py::test_push_no_retry_on_4xx` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ERROR: console URL blocked by SSRF allowlist — dns_failure`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:91) |
| `test_sensor_cmd.py::test_push_connect_error_retries` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ERROR: console URL blocked by SSRF allowlist — dns_failure`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:92) |
| `test_sensor_cmd.py::test_push_409_treated_as_success` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ERROR: console URL blocked by SSRF allowlist — dns_failure` (assert 1 == 0); expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:93) |
| `test_sensor_cmd.py::test_spool_on_connect_failure` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ERROR: console URL blocked by SSRF allowlist — dns_failure`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:94) |
| `test_sensor_cmd.py::test_spool_flush_delivers_and_unlinks` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ERROR: console URL blocked by SSRF allowlist — dns_failure`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:95) |
| `test_sensor_cmd.py::test_spool_409_unlinks_file` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ERROR: console URL blocked by SSRF allowlist — dns_failure` (assert 1 == 0); expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:96) |
| `test_sensor_cmd.py::test_spool_filename_is_uuid_pattern` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `ERROR: console URL blocked by SSRF allowlist — dns_failure`; expected to pass on a DNS-enabled runner; re-verify in Phase 150 | yes (tests/skip_registry.py:97) |

## Cluster 2: Playwright cross-test pollution

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|

## Cluster 3: Version staleness (environment)

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|

## Cluster 4: Version staleness (stale assertions)

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|

## Cluster 5: sensor_id shape / AUDIT-08 regression

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|

## Cluster 6: pip dry-run extras-install flakiness

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|

## Cluster 7: Optional GCP extras missing

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|

## Cluster 8: Meta-gate self-failure (D-04)

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|
| `test_skip_registry.py::test_no_unregistered_skips` | fixed | D-04 drift repaired | 30 unregistered skip markers registered/updated in `tests/skip_registry.py`; AST walker extended to detect `skip`/`skipif`/`xfail` decorators (Plan 01, Tasks 1-2) | No — resolved via direct registry repair, no quarantine needed |

## Cluster 9: Remaining individually-distinct failures

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|

---

*Phase: 149-test-suite-triage*
*Plan: 01*
*Updated: 2026-08-11*
