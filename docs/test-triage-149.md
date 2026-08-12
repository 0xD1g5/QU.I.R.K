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
| `test_reports_writer.py::test_json_export_preserves_description` | quarantined-skip | flaky (test-isolation / shared Playwright singleton) | `AttributeError: PlaywrightContextManager` only in full-suite runs; confirmed passing standalone (`pytest tests/test_reports_writer.py tests/test_writer.py -q -m ""` — 7 passed) | yes (tests/skip_registry.py:100) |
| `test_reports_writer.py::test_json_export_preserves_deprecation_phrase` | quarantined-skip | flaky (test-isolation / shared Playwright singleton) | `AttributeError: PlaywrightContextManager` only in full-suite runs; confirmed passing standalone (same isolation run) | yes (tests/skip_registry.py:101) |
| `test_reports_writer.py::test_html_report_has_description_column` | quarantined-skip | flaky (test-isolation / shared Playwright singleton) | `AttributeError: PlaywrightContextManager` only in full-suite runs; confirmed passing standalone (same isolation run) | yes (tests/skip_registry.py:102) |
| `test_reports_writer.py::test_docx_emitted_by_write_reports` | quarantined-skip | flaky (test-isolation / shared Playwright singleton) | `AttributeError: PlaywrightContextManager` only in full-suite runs; confirmed passing standalone (same isolation run) | yes (tests/skip_registry.py:103) |
| `test_reports_writer.py::test_docx_none_on_fail_not_in_output_files` | quarantined-skip | flaky (test-isolation / shared Playwright singleton) | `AttributeError: PlaywrightContextManager` only in full-suite runs; confirmed passing standalone (same isolation run) | yes (tests/skip_registry.py:104) |
| `test_report_injection_hardening.py::test_script_payload_in_cert_cn_is_escaped_in_html` | quarantined-skip | flaky (test-isolation / shared Playwright singleton) | `AttributeError: PlaywrightContextManager` only in full-suite runs; confirmed passing standalone (`pytest tests/test_report_injection_hardening.py -q -m ""` — 4 passed) | yes (tests/skip_registry.py:105) |
| `test_report_injection_hardening.py::test_javascript_url_in_finding_recommendation_stripped` | quarantined-skip | flaky (test-isolation / shared Playwright singleton) | `AttributeError: PlaywrightContextManager` only in full-suite runs; confirmed passing standalone (same isolation run) | yes (tests/skip_registry.py:106) |
| `test_report_injection_hardening.py::test_db_stored_raw_payload_preserved` | quarantined-skip | flaky (test-isolation / shared Playwright singleton) | `AttributeError: PlaywrightContextManager` only in full-suite runs; confirmed passing standalone (same isolation run) | yes (tests/skip_registry.py:107) |
| `test_report_injection_hardening.py::test_script_payload_in_cert_cn_is_escaped_in_pdf` | quarantined-skip | flaky (test-isolation / shared Playwright singleton) | `AttributeError: PlaywrightContextManager` only in full-suite runs; confirmed passing standalone (same isolation run) | yes (tests/skip_registry.py:108) |
| `test_pdf_metadata_constants.py::test_pdf_title_is_constant` | quarantined-skip | flaky (test-isolation / shared Playwright singleton) | `AttributeError: PlaywrightContextManager` only in full-suite runs; confirmed passing standalone (`pytest tests/test_pdf_metadata_constants.py -q -m ""` — 3 passed) | yes (tests/skip_registry.py:109) |
| `test_pdf_metadata_constants.py::test_pdf_author_is_constant` | quarantined-skip | flaky (test-isolation / shared Playwright singleton) | `AttributeError: PlaywrightContextManager` only in full-suite runs; confirmed passing standalone (same isolation run) | yes (tests/skip_registry.py:110) |
| `test_pdf_metadata_constants.py::test_pdf_renders_with_locked_context` | quarantined-skip | flaky (test-isolation / shared Playwright singleton) | `AttributeError: PlaywrightContextManager` only in full-suite runs; confirmed passing standalone (same isolation run) | yes (tests/skip_registry.py:111) |
| `test_writer.py::test_run_stats_ports_and_hosts_scanned` | quarantined-skip | flaky (test-isolation / shared Playwright singleton) | `AttributeError: PlaywrightContextManager` only in full-suite runs; confirmed passing standalone (`pytest tests/test_reports_writer.py tests/test_writer.py -q -m ""` — 7 passed) | yes (tests/skip_registry.py:112) |
| `test_pdf_export.py::test_pdf_export_endpoint` | quarantined-skip | flaky (test-isolation / shared Playwright singleton) | `AttributeError: PlaywrightContextManager` only in full-suite runs; confirmed passing standalone (`pytest tests/test_pdf_export.py -q -m ""` — 2 passed) | yes (tests/skip_registry.py:113) |

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
| `test_install_all_excludes_impacket.py::test_install_all_excludes_impacket` | quarantined-skip | flaky (pip --dry-run subprocess contention under full-suite load) | Fails only in full-suite runs; confirmed passing standalone (`pytest tests/test_install_all_excludes_impacket.py -q -m ""` — 1 passed, 7.75s) | yes (tests/skip_registry.py:116) |
| `test_install_all_excludes_pysnmp.py::test_install_all_excludes_pysnmp` | quarantined-skip | flaky (pip --dry-run subprocess contention under full-suite load) | Confirmed passing standalone (`pytest tests/test_install_all_excludes_pysnmp.py -q -m ""` — 1 passed, 5.95s) | yes (tests/skip_registry.py:117) |
| `test_install_all_excludes_schemathesis.py::test_install_all_excludes_schemathesis` | quarantined-skip | flaky (pip --dry-run subprocess contention under full-suite load) | Confirmed passing standalone (`pytest tests/test_install_all_excludes_schemathesis.py -q -m ""` — 2 passed, 5.35s; second test `test_install_api_includes_schemathesis` is out of Cluster 6 scope and unaffected) | yes (tests/skip_registry.py:118) |
| `test_install_all_includes_notify.py::test_install_all_includes_notify` | quarantined-skip | flaky (pip --dry-run subprocess contention under full-suite load) | Confirmed passing standalone (`pytest tests/test_install_all_includes_notify.py -q -m ""` — 1 passed, 5.11s) | yes (tests/skip_registry.py:119) |
| `test_install_all_includes_tickets.py::test_install_all_includes_tickets` | quarantined-skip | flaky (pip --dry-run subprocess contention under full-suite load) | Confirmed passing standalone (`pytest tests/test_install_all_includes_tickets.py -q -m ""` — 1 passed, 7.90s) | yes (tests/skip_registry.py:120) |
| `test_snmp_scanner_contract.py::test_install_all_excludes_pysnmp` | quarantined-skip | flaky (pip --dry-run subprocess contention under full-suite load) | RESEARCH.md-noted `AssertionError: pip install --dry-run -e <repo>[all] FAILED`; confirmed passing standalone (`pytest tests/test_snmp_scanner_contract.py::test_install_all_excludes_pysnmp -q -m ""` — 1 passed, 8.20s) | yes (tests/skip_registry.py:121) |

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
*Plan: 03*
*Updated: 2026-08-12*
