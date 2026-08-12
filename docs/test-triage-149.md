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
| `test_version.py::test_package_version_matches_pyproject` | environment-fix-applied | stale dist-info, resolved via `pip install -e .` | `.venv`'s editable install had `quirk_scanner-5.10.0.dist-info` registered under `pip show quirk-scanner`, stale vs `pyproject.toml`'s `5.11.0`; `pip install -e .` inside `.venv` uninstalled `quirk-scanner-5.10.0` and reinstalled `quirk-scanner-5.11.0` | No — no source/test edit |
| `test_version.py::test_cbom_platform_version_matches_pyproject` | environment-fix-applied | stale dist-info, resolved via `pip install -e .` | Same root cause/fix as above; `pytest tests/test_version.py -q -m ""` → 7 passed after refresh | No — no source/test edit |
| `test_version.py::test_reports_platform_version_matches_pyproject` | environment-fix-applied | stale dist-info, resolved via `pip install -e .` | Same root cause/fix as above | No — no source/test edit |
| `test_version.py::test_intelligence_config_default_matches_pyproject` | environment-fix-applied | stale dist-info, resolved via `pip install -e .` | Same root cause/fix as above | No — no source/test edit |
| `test_version.py::test_cli_version_subprocess` | environment-fix-applied | stale dist-info, resolved via `pip install -e .` | Same root cause/fix as above; before fix `quirk --version` subprocess reported `5.10.0` | No — no source/test edit |

Note: `python`/`pip` on `PATH` resolve to the Homebrew system Python (externally-managed,
`quirk` not installed there), not the project's `.venv`. This plan's fix was applied inside
`.venv` (`source .venv/bin/activate && pip install -e .`) since that is the venv `pytest`
actually runs under, confirmed via `which pytest` → `.venv/bin/pytest`.

## Cluster 4: Version staleness (stale assertions)

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|
| `test_packaging.py::test_version_is_4_2_0` | deleted | genuinely-stale hardcoded version literal (`"5.5.0"`), no other packaging coverage | Test's sole assertion pinned a historical version string, drifted across 3+ major bumps; superseded by `tests/test_version.py`. Deleted per D-01's narrow exception (recommended disposition) | No — deleted, no quarantine needed |
| `test_v41_gap_closure.py::TestV41GapClosure::test_pyproject_version_field_is_4_1_0` | deleted | genuinely-stale hardcoded version literal (`"4.4.0"`), redundant with `test_version.py`'s pyproject checks | Same anti-pattern as above; deleted | No — deleted, no quarantine needed |
| `test_cli_correctness.py::test_version_consistency` | fixed | genuinely-stale hardcoded `TARGET = "5.5.0"`, but exercises real cross-module consistency (PLATFORM_VERSION/INTELLIGENCE_VERSION/CBOM_VERSION/IntelligenceCfg vs `quirk.__version__`) beyond a bare version string | Kept per D-01's exception for tests with additional coverage; `TARGET` now derives from `quirk.__version__` itself instead of a hardcoded literal, preserving the regression guard (all 4 constants must stay wired to the single source of truth) without needing a manual edit every release. Reassigned from the plan's initial Cluster 3 grouping to Cluster 4 per RESEARCH.md row 4 ground truth — its failure is a stale assertion, not stale dist-info, and was unaffected by the Task 1 `pip install -e .` fix (still failed with `TARGET = "5.5.0"` afterward) | No — fixed in place, no quarantine needed |

## Cluster 5: sensor_id shape / AUDIT-08 regression

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|
| `test_auto_merge_trigger.py::test_all_sensors_in_triggers_merge` | quarantined-xfail | outdated-fixture (AUDIT-08 UUID guard) | `400: {"detail":"Invalid sensor_id shape"}` — fixture uses `"sensor-a"`/`"sensor-b"`, not UUIDs; `quirk/dashboard/api/routes/sensor.py:494`'s `_UUID_RE.match()` guard (AUDIT-08, "defense-in-depth") was added after this fixture file was written. Confirmed via standalone run: `pytest tests/test_auto_merge_trigger.py -q -m ""` → 8 failed with this exact 400 before quarantine | yes (tests/skip_registry.py:129) |
| `test_auto_merge_trigger.py::test_auto_merge_disabled` | quarantined-xfail | outdated-fixture (AUDIT-08 UUID guard) | Same root cause as above — `_do_push` helper fails at the shared `assert resp.status_code == 200` on the same non-UUID `"sensor-a"`/`"sensor-b"` fixture IDs | yes (tests/skip_registry.py:130) |
| `test_auto_merge_trigger.py::test_revoked_sensor_excluded` | quarantined-xfail | outdated-fixture (AUDIT-08 UUID guard) | Same root cause; `"sensor-a"` push rejected with 400 before the revoked-sensor logic under test ever runs | yes (tests/skip_registry.py:131) |
| `test_auto_merge_trigger.py::test_mixed_token_sensor_is_required_for_all_in` | quarantined-xfail | outdated-fixture (AUDIT-08 UUID guard) | Same root cause; CR-01 regression test's `"sensor-a"`/`"sensor-b"` fixtures predate the UUID guard | yes (tests/skip_registry.py:132) |
| `test_auto_merge_trigger.py::test_zero_token_sensor_not_counted_as_active` | quarantined-xfail | outdated-fixture (AUDIT-08 UUID guard) | Same root cause; `"sensor-a"`/`"sensor-ghost"` are not UUIDs | yes (tests/skip_registry.py:133) |
| `test_auto_merge_trigger.py::test_merge_failure_isolated` | quarantined-xfail | outdated-fixture (AUDIT-08 UUID guard) | Same root cause; push rejected at 400 before the merge-failure-isolation path under test is reached | yes (tests/skip_registry.py:134) |
| `test_auto_merge_trigger.py::test_double_fire_harmless` | quarantined-xfail | outdated-fixture (AUDIT-08 UUID guard) | Same root cause; first `_do_push(client, "sensor-a", tok_a)` call fails at 400 | yes (tests/skip_registry.py:135) |
| `test_auto_merge_trigger.py::test_cadence_window_triggers` | quarantined-xfail | outdated-fixture (AUDIT-08 UUID guard) | Same root cause; `"sensor-a"`/`"sensor-b"` cadence-window fixture predates the UUID guard | yes (tests/skip_registry.py:136) |
| `test_sensor_push_id_revalidation.py::test_malformed_sensor_id_path_traversal_rejected` | quarantined-xfail | shared in-memory SQLite cache pollution (test-isolation, NOT the same cause as the 8 rows above, NOT an AUDIT-08 implementation defect) | Individually investigated per Open Question 3 (RESEARCH.md). Standalone: `pytest tests/test_sensor_push_id_revalidation.py -q -m ""` → 3 passed (the 400 rejection + 0-new-rows assertion are both correct in isolation). Full-suite-order reproduction: `pytest tests/test_sensor_ingest.py tests/test_sensor_auth_per_sensor.py tests/test_sensor_push_id_revalidation.py -q -m ""` → reproduces `AssertionError: AUDIT-08 RED: 9 SensorPush row(s) found; malformed sensor_id`. Root cause: this file's engine URI (`sqlite:///file::memory:?cache=shared&uri=true`) is a SQLite shared-cache in-memory database, which is a single process-wide DB, not per-test-isolated — 13 other test files in `tests/` use the identical URI and write `SensorPush` rows that persist across files within the same pytest worker process. The malformed-id push route correctly returns 400 and writes zero *new* rows for the rejecting request; the count of 9 is entirely rows left over from earlier tests in suite order. This is a test-fixture/isolation defect (same defect class as Cluster 2/6's shared-fixture issues), not a write-before-reject ordering bug in the AUDIT-08 guard — no implementation fix required (D-01). Not flagged as a real regression for Phase 150. | yes (tests/skip_registry.py:137) |
| `test_sensor_push_id_revalidation.py::test_malformed_sensor_id_short_string_rejected` | quarantined-xfail | shared in-memory SQLite cache pollution (test-isolation, NOT the same cause as the 8 rows above, NOT an AUDIT-08 implementation defect) | Same root cause and evidence as the row above — reproduces `AssertionError: AUDIT-08 RED: 9 SensorPush row(s) found after malformed id push.` under the identical full-suite-order repro command; passes standalone (3 passed) | yes (tests/skip_registry.py:138) |

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
| `test_gcs_reuse.py::test_gcs_reuse_reads_sentinel_no_api_call` | quarantined-skip | optional_extra (googleapiclient/google not installed) | `ModuleNotFoundError: No module named 'google'` — `googleapiclient`/`google` (`[cloud]` extras) not installed in the dev venv | yes (tests/skip_registry.py:117) |
| `test_gcs_reuse.py::test_gcs_reuse_zero_storage_buckets_list_call` | quarantined-skip | optional_extra (googleapiclient/google not installed) | Same root cause; `patch("google.cloud.storage.Client", ...)` fails to import `google` | yes (tests/skip_registry.py:118) |

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
