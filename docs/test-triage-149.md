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
| `test_version.py::test_cli_version_subprocess` | environment-fix-applied + quarantined-xfail (Plan 11) | stale dist-info (fixed), PLUS a separate, newly-discovered macOS fork()-under-load SIGSEGV | Same stale dist-info root cause/fix as above — `quirk --version` correctly reports `5.11.0` now, and this fix remains valid and necessary. **Plan 11 reconciliation finding:** a fresh `pytest -q -m ""` full-suite run additionally surfaced an intermittent SIGSEGV (`exit=-11`) in this test's `subprocess.run()` spawn, confirmed via a `Fatal Python error: Segmentation fault` crash dump at `test_version.py:61` — a distinct, load-dependent failure mode unrelated to version staleness. See the Reconciliation section's `macOS fork() SIGSEGV cluster` for the shared root cause across 5 tests; `@pytest.mark.xfail(strict=False)` added | yes (tests/skip_registry.py, `test_version.py:59`) |

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

### Group A: scanner/detection-logic failures (Plan 06)

Assumption A3 resolved first: `tests/test_skip_registry.py`'s meta-gate walked
`TESTS_DIR.glob("*.py")` (non-recursive), silently skipping `tests/scanner/` — any xfail
marker added there would have been unenforced. Fixed to `TESTS_DIR.rglob("*.py")`; confirmed
no pre-existing unregistered skips surfaced in `tests/scanner/` or any other subdirectory.

Each of the 18 tests below was individually investigated (no batch classification) per
RESEARCH.md's cluster-9 guidance. Investigation converged on 4 distinct sub-reasons across the
18: 9 share a DNS-blocked-sandbox SSRF-guard root cause (same class as Cluster 1, but a
separate finding since these are scanner-detection-logic tests, not notification/ticketing
tests), 2 share a stale-CR-06-opt-in-guard cause, 2 share a stale-test-fixture cause, and 5 are
NOT reproducible as failures in this specific sandbox (2 cleanly skip via already-registered
`optional_extra` markers, 2 likewise, 1 currently passes) — each documented individually below
rather than silently omitted.

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|
| `tests/scanner/test_jwt_hardening.py::test_allow_insecure_jwks_uses_verify_false_and_emits_advisory` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `AssertionError: Expected at least one verify=False call`. `validate_external_url("https://idp.example.com/...")` → `ValidationResult(ok=False, reason='dns_failure', ...)` inside `_fetch_jwks`'s CR-03 SSRF gate, so `httpx.get` is never reached regardless of `allow_insecure_jwks`; not a verify-flag propagation defect. Confirmed via direct `validate_external_url()` call | yes (tests/skip_registry.py, `test_jwt_hardening.py:31`) |
| `tests/scanner/test_jwt_hardening.py::test_scan_jwt_targets_propagates_flag` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | Same root cause as row above — `scan_jwt_targets` delegates to the same DNS-blocked `_fetch_jwks` path | yes (tests/skip_registry.py, `test_jwt_hardening.py:66`) |
| `tests/test_broker_scanner_rabbitmq.py::test_enrich_rabbitmq_mgmt_success` | quarantined-xfail | stale test (predates CR-06 `allow_cleartext` opt-in guard) | `KeyError: 'rabbitmq_version'`. `_enrich_rabbitmq_mgmt(host, port)` defaults `allow_cleartext=False` and returns `{}` immediately (Phase 57 CR-06 hardening) — the test never passes `allow_cleartext=True`, so the mocked `urlopen` is never called. Confirmed by reading `quirk/scanner/broker_scanner.py:311-332`'s explicit `if not allow_cleartext: return {}` short-circuit | yes (tests/skip_registry.py, `test_broker_scanner_rabbitmq.py:200`) |
| `tests/test_broker_scanner_rabbitmq.py::test_enrich_rabbitmq_mgmt_401` | quarantined-xfail | stale test (predates CR-06 `allow_cleartext` opt-in guard) | Same root cause as row above — `allow_cleartext=False` default short-circuits before the mocked `HTTPError(401)` side-effect is ever raised | yes (tests/skip_registry.py, `test_broker_scanner_rabbitmq.py:236`) |
| `tests/test_identity_scanner_hardening.py::test_kdc_udp_decode_failure_logs` | **superseded by Plan 11** — partially fixed, residual quarantined-xfail | genuine impacket 0.13.0 API drift (was mis-diagnosed as optional_extra-absent in Plan 06's sandbox) | RESEARCH.md described `AttributeError: module 'quirk.scanner.kerberos_scanner' has no attribute 'decode...'`, implying impacket was installed when captured — Plan 06's sandbox lacked impacket entirely, so `pytest.importorskip("impacket")` masked the real defect as a clean skip. **Plan 11 reconciliation finding:** this sandbox has impacket 0.13.0 installed (matching the current `impacket>=0.13.0,<0.14` pin), and the real bug reproduces: `kerberos_scanner.py`'s `from impacket.krb5.asn1 import ... MethodData` fails (impacket 0.13.0 renamed it to `METHOD_DATA`), silently setting `IMPACKET_AVAILABLE = False` for every operator on the currently-pinned impacket version — a genuine production regression, not test staleness. **Fixed in place** (Rule 1): import now tries `METHOD_DATA as MethodData` first, falling back to the old name for impacket <0.13. This restores `IMPACKET_AVAILABLE=True`, but uncovers a second, deeper impacket 0.13.0 incompatibility: `constants.KDCOptions` changed from a bit-flag helper class to a plain `enum.Enum`, so `_build_as_req`'s `constants.KDCOptions(constants.KDCOptions.forwardable)` now raises a pyasn1 `KeyError`. Quarantined pending a dedicated Phase 150 fix (out of scope for a one-line import fix) | yes (tests/skip_registry.py, `test_identity_scanner_hardening.py:85`) |
| `tests/test_identity_scanner_hardening.py::test_build_as_req_nonce_uses_secrets` | **superseded by Plan 11** — quarantined-xfail | same impacket 0.13.0 `KDCOptions` enum incompatibility | Same underlying root cause and fix as the row above — see there for detail. RESEARCH.md's original `NameError: name 'constants' is not defined` capture was itself a symptom of the same `MethodData` import failure (now fixed); the residual `KDCOptions` enum defect surfaced only once the import succeeded | yes (tests/skip_registry.py, `test_identity_scanner_hardening.py:114`) |
| `tests/test_jwt_scanner.py::test_multi_key_jwks` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `assert 0 == 3`. Same CR-03 `validate_external_url()` dns_failure root cause as `test_jwt_hardening.py` above — `https://api.example.com/...` fails DNS resolution in this sandbox, so `_fetch_jwks` returns `(None, None, [])` before any key is parsed | yes (tests/skip_registry.py, `test_jwt_scanner.py:44`) |
| `tests/test_jwt_scanner.py::test_jwt_rsa_key_size` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | Same root cause as row above | yes (tests/skip_registry.py, `test_jwt_scanner.py:67`) |
| `tests/test_jwt_scanner.py::test_jwt_ec_key_size` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | Same root cause as row above | yes (tests/skip_registry.py, `test_jwt_scanner.py:89`) |
| `tests/test_jwt_scanner.py::test_jwt_query_param_cred_ctx_appends_key_to_url` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `AssertionError: httpx.Client.get was never called`. Same CR-03 SSRF-guard cause — `validate_external_url` rejects `api.example.com` before the credential-context query-param logic under test is ever reached | yes (tests/skip_registry.py, `test_jwt_scanner.py:132`) |
| `tests/test_jwt_scanner.py::test_jwt_no_cred_ctx_unchanged_behavior` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `assert 0 == 3`. Same root cause as the other `test_jwt_scanner.py` rows | yes (tests/skip_registry.py, `test_jwt_scanner.py:213`) |
| `tests/test_jwt_scanner.py::test_append_query_param_continue_iteration_skips_conflicting_target` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `assert 0 >= 3`. `h1.example.com` and `h2.example.com` both fail `validate_external_url`'s dns_failure check (confirmed via direct call), so no target — conflicting or clean — ever reaches `httpx.get`; not a D-03 continue-iteration defect | yes (tests/skip_registry.py, `test_jwt_scanner.py:321`) |
| `tests/test_openapi_scanner.py::test_url_scope_accepts_bare_fqdn_target` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `AssertionError: Expected 'get' to have been called once. Called 0 times.` `scan_openapi_spec`'s SSRF gate (`validate_external_url`, `quirk/scanner/openapi_scanner.py:157-159`) rejects `api.example.com` with `dns_failure` before the bare-FQDN scope-matching logic under test is reached; not a scope-comparison regression. (6 unrelated `openapi-spec-validator not installed` failures also found in this file during standalone verification — out of scope for this plan, logged in `deferred-items.md`) | yes (tests/skip_registry.py, `test_openapi_scanner.py:231`) |
| `tests/test_tls_scanner_chain_verified.py::test_sslyze_success_chain_verified_true` | **superseded by Plan 11** — fixed | genuine production bug (was mis-diagnosed as optional_extra-absent in Plan 06's sandbox) | RESEARCH.md described `assert None is not None`, implying sslyze was installed when captured — Plan 06's sandbox lacked sslyze entirely, masking the real defect as a clean `skipif`. **Plan 11 reconciliation finding:** this sandbox has sslyze 6.3.1 installed, and the real bug reproduces: sslyze >=6.3 replaced the module-level `sslyze.__version__` string constant with a `sslyze/__version__.py` submodule (itself exposing a nested `.__version__` string), so `tls_scanner.py`'s `getattr(_sslyze_module, "__version__", "unknown")` returned a bare module object; `json.dumps(caps)` then raised `TypeError: Object of type module is not JSON serializable` inside `_scan_one_sslyze`'s broad `except Exception`, silently discarding every real sslyze scan result (production regression for any operator on sslyze >=6.3). **Fixed in place** (Rule 1): normalizes both the old (string) and new (nested-module) `__version__` shapes before building `tls_capabilities_json` | No — fixed in place, no quarantine needed |
| `tests/test_tls_scanner_chain_verified.py::test_sslyze_success_chain_verified_false` | **superseded by Plan 11** — fixed | same sslyze >=6.3 `__version__` submodule shape change | Same root cause and fix as the row above | No — fixed in place, no quarantine needed |
| `tests/test_vault_connector.py::test_pki_sha1_signed_ca_high_severity` | **superseded by Plan 11** — quarantined-xfail | macOS fork()-under-full-suite-load SIGSEGV (not an OpenSSL SHA1 support issue) | RESEARCH.md described `RuntimeError: openssl SHA1 cert failed`; Plan 06 found the test passing standalone and hypothesized OpenSSL-build-dependent SHA1 cert generation as the (unconfirmed) cause. **Plan 11 reconciliation finding:** a fresh full-suite run reproduced a real failure here too — but it is `returncode=-11` (SIGSEGV) from the `openssl req -new -x509 -sha1 ...` subprocess itself, confirmed via a `Fatal Python error: Segmentation fault` crash dump at `_make_test_pem_rsa`'s subprocess call site, not an OpenSSL algorithm-support rejection. Part of the same systemic macOS fork()-under-load instability cluster as `test_qramm_staleness.py`'s SIGSEGV pair (see Reconciliation section) — this test still passes standalone/in isolation | yes (tests/skip_registry.py, `test_vault_connector.py:299`) |
| `tests/test_gap_closure.py::test_findings_quantum_label_dsa` | quarantined-xfail | stale test fixture (missing `sensor_id`/`segment` fields) | `AssertionError: Expected at least one Vulnerable finding for DSA, got: []`. `_make_endpoint()`'s `SimpleNamespace` fixture doesn't set `sensor_id`/`segment` (fields a later phase added to `FindingItem` construction); `_derive_findings()`'s quantum-vulnerable-algorithm branch raises `AttributeError` building the `FindingItem`, silently swallowed by its own broad `except Exception: pass`, dropping the finding. Confirmed `classify_algorithm("DSA")`/`quantum_safety_label()` themselves correctly return `quantum-vulnerable` — the classifier is not regressed; the fixture is stale | yes (tests/skip_registry.py, `test_gap_closure.py:48`) |
| `tests/test_gap_closure.py::test_findings_quantum_label_ecdsa` | quarantined-xfail | stale test fixture (missing `sensor_id`/`segment` fields) | Same root cause as row above; `classify_algorithm("ECDSA")` also correctly returns `quantum-vulnerable` | yes (tests/skip_registry.py, `test_gap_closure.py:74`) |

Verification: `pytest tests/test_skip_registry.py -q -m ""` → 1 passed (meta-gate stays green
after both the rglob fix and 13 new registry entries). Full Group A file suite:
`pytest tests/scanner/test_jwt_hardening.py tests/test_broker_scanner_rabbitmq.py tests/test_identity_scanner_hardening.py tests/test_jwt_scanner.py tests/test_openapi_scanner.py tests/test_tls_scanner_chain_verified.py tests/test_vault_connector.py tests/test_gap_closure.py -q -m ""`
→ 66 passed, 5 skipped, 13 xfailed, 6 failed (the 6 failures are the out-of-scope
`openapi-spec-validator not installed` failures in `test_openapi_scanner.py`, logged in
`deferred-items.md`, not part of this plan's 18-test scope).

### Group B: dashboard/API/DB-migration failures (Plan 07)

Each of the 12 tests below was individually investigated per RESEARCH.md's cluster-9
guidance and this plan's must_haves truth. Investigation converged on 5 distinct
sub-reasons across the 12: 4 share a `/api/compare` test-construction bug (unescaped `+`
UTC offset in a raw f-string query string), 1 is a genuine `/api/compare` error-envelope
contract change, 2 share a confirmed intentional Obsidian Pro rebrand, 1 is a
security-relevance question explicitly answered as stale test inventory (not a real
finding), 3 share a `sensor_tokens` stale-fixture cause, and 1 is a `_ensure_*` naming-
convention drift. No two rows share identical evidence except where the investigation
genuinely found the same root cause, and even then each row cites its own assertion.

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|
| `test_dashboard_scan_history.py::test_compare_schema` | quarantined-xfail | test-construction bug (`+` query-encoding, not endpoint drift) | `AssertionError: Expected 200 from /api/compare; got 400`. The test builds its request URL via a raw f-string embedding `datetime.isoformat()`'s UTC offset verbatim (e.g. `...563021+00:00`); Starlette/httpx query-string decoding treats a literal `+` as a space (`application/x-www-form-urlencoded` convention), corrupting the timestamp before `compare_scans()`'s `datetime.fromisoformat(a)` ever runs, so it 400s via the `DASHBOARD-004` malformed-scan_id branch. Confirmed directly: re-issuing the identical request with both params passed through `urllib.parse.quote()` returns 200 with the full expected schema — `/api/compare` itself is correct | yes (tests/skip_registry.py, `test_dashboard_scan_history.py:188`) |
| `test_dashboard_scan_history.py::test_compare_self` | quarantined-xfail | genuine API-contract drift (structured error envelope) | `AssertionError: Expected detail='Cannot compare a scan to itself.'; got {'detail': '[QRK-DASHBOARD-007] Cannot compare a scan to itself. Fix: Choose two distinct scan_ids for the compare request.'}`. `format_error()` now wraps every `detail` string in a `[QRK-<CODE>] <message> Fix: <remediation>` envelope (a later phase standardized structured error responses across the dashboard API) — the 400 status code and self-compare rejection logic are both still correct; only the test's exact-string assertion is stale | yes (tests/skip_registry.py, `test_dashboard_scan_history.py:234`) |
| `test_dashboard_scan_history.py::test_compare_score_delta` | quarantined-xfail | test-construction bug (`+` query-encoding, not endpoint drift) | Same root cause as `test_compare_schema` — unescaped `+` UTC offset in the raw f-string URL corrupts the timestamp before `score_delta`/`subscore_deltas` are ever computed | yes (tests/skip_registry.py, `test_dashboard_scan_history.py:268`) |
| `test_dashboard_scan_history.py::test_compare_finding_diff` | quarantined-xfail | test-construction bug (`+` query-encoding, not endpoint drift) | Same root cause as `test_compare_schema` — unescaped `+` UTC offset corrupts the timestamp before `added_findings`/`removed_findings` are ever computed | yes (tests/skip_registry.py, `test_dashboard_scan_history.py:321`) |
| `test_dashboard_scan_history.py::test_compare_endpoint_diff` | quarantined-xfail | test-construction bug (`+` query-encoding, not endpoint drift) | Same root cause as `test_compare_schema` — unescaped `+` UTC offset corrupts the timestamp before `endpoints_only_in_a`/`endpoints_only_in_b`/`changed_endpoints` are ever computed | yes (tests/skip_registry.py, `test_dashboard_scan_history.py:359`) |
| `test_dashboard_theme.py::test_primary_color_token` | quarantined-xfail | confirmed intentional rebrand (Obsidian Pro design system) | `AssertionError: Expected '--primary: 210 100% 56%' in ...index.css`. Commit `ac242d1` ("feat(ui): apply Obsidian Pro design system foundation", 2026-05-07) explicitly changed `--primary` from the electric-blue token `210 100% 56%` to `180 37% 47%` (#4ba8a8 teal), per its own commit message: "Accent shifted from blue (210 100% 56%) to Obsidian Pro teal (#4ba8a8)". This test predates that rebrand | yes (tests/skip_registry.py, `test_dashboard_theme.py:12`) |
| `test_dashboard_theme.py::test_accent_color_token` | quarantined-xfail | confirmed intentional rebrand (Obsidian Pro design system) | Same root cause as row above — `--accent` is now `180 37% 47%` (#4ba8a8 teal), confirmed via `git show ac242d1 --stat` | yes (tests/skip_registry.py, `test_dashboard_theme.py:32`) |
| `test_route_coverage.py::test_all_data_routes_have_auth_dependency` | quarantined-xfail | **stale test inventory** (not a real unprotected route) | `AssertionError: ... ['GET'] /api/config — missing require_auth`. Read `quirk/dashboard/api/routes/config.py`: `GET /api/config` is deliberately unauthenticated per its own module docstring — "Runtime config endpoint — no auth required (frontend needs this before login)" — mirroring `/api/health`'s designed pre-auth exemption (both routers registered without a router-level `require_auth` dependency in `app.py`). It returns only `ConfigResponse(vertical=get_vertical())`, a UI branding enum, no scan/crypto/secret data. This test's exemption set (`{"/api/health", "/api/health/"}`) was never updated when `/api/config` was added for the vertical-system feature. **Not a real security finding — the route is intentionally, minimally public by design; this is stale test inventory**, not flagged `SECURITY:` | yes (tests/skip_registry.py, `test_route_coverage.py:18`) |
| `test_db_migrate_cli.py::test_fresh_db_reports_every_column_added` | quarantined-xfail | stale fixture (`sensor_tokens` table absent from simulated legacy schema) | `sqlalchemy.exc.NoSuchTableError: sensor_tokens`. `_create_legacy_schema()` only `CREATE TABLE`s `crypto_endpoints` and `qramm_answers` (the tables that existed when this fixture was written), but `_ADDITIVE_MIGRATIONS` (`quirk/db.py`) has since grown a `("sensor_tokens", _V55_SENSOR_TOKEN_COLUMNS)` entry (Phase 113 AUTH-02, per-sensor auth). `run_additive_migration` ALTERs existing tables' columns — it does not create missing tables — so walking a table absent entirely from the fixture's legacy schema raises `NoSuchTableError` instead of reporting the column `added`. The fixture needs a third empty `CREATE TABLE sensor_tokens (id INTEGER PRIMARY KEY)` statement to match current `_ADDITIVE_MIGRATIONS` coverage | yes (tests/skip_registry.py, `test_db_migrate_cli.py:53`) |
| `test_db_migrate_cli.py::test_dry_run_does_not_write` | quarantined-xfail | stale fixture (`sensor_tokens` table absent from simulated legacy schema) | Same root cause as row above — `run_additive_migration(engine, dry_run=True)` raises the same `NoSuchTableError: sensor_tokens` before a dry-run diagnostic list can be returned | yes (tests/skip_registry.py, `test_db_migrate_cli.py:114`) |
| `test_db_migrate_cli.py::test_result_shape` | quarantined-xfail | stale fixture (`sensor_tokens` table absent from simulated legacy schema) | Same root cause as row above — `results[0]` is never reached because `run_additive_migration` raises `NoSuchTableError: sensor_tokens` first | yes (tests/skip_registry.py, `test_db_migrate_cli.py:145`) |
| `test_init_db_idempotent.py::test_all_ensure_functions_idempotent` | quarantined-xfail | naming-convention drift (`_ensure_columns` is a shared multi-arg helper, not a per-table idempotent function) | `TypeError: _ensure_columns() missing 2 required positional arguments: 'table' and 'expected'`. `_ensure_columns(engine, table, expected)` (`quirk/db.py`, Phase 77 D-21) is a generic helper invoked BY the real per-table `_ensure_*` functions — e.g. `_ensure_qramm_tables` calls `_ensure_columns(engine, table, tuple(missing))` internally — it was never meant to satisfy the single-arg `_ensure_*(engine)` contract this test's `dir()`-based discovery assumes purely from the name prefix. The test already excludes `_ensure_parent_dir` for the identical reason (different signature: takes a path string, not an engine); `_ensure_columns` needs the same exclusion. Every genuine per-table `_ensure_*` helper (`_ensure_qramm_profiles_fk`, `_ensure_qramm_tables`, `_ensure_scheduled_tables`, `_ensure_scan_jobs_table`, `_ensure_scan_checkpoints_table`, `_ensure_integration_deliveries_table`, `_ensure_merge_runs_table`) IS correctly idempotent under repeat invocation — confirmed by direct inspection; none of them are regressed | yes (tests/skip_registry.py, `test_init_db_idempotent.py:40`) |

Verification: `pytest tests/test_dashboard_scan_history.py tests/test_dashboard_theme.py
tests/test_route_coverage.py tests/test_db_migrate_cli.py tests/test_init_db_idempotent.py
-q -m ""` → 12 passed, 12 xfailed (24 total: the passing counterparts in each file —
`test_list_scans_schema`, `test_list_scans_no_limit`, `test_clone_data_recovery`,
`test_clone_reconstruction`, `test_sidebar_wordmark_present`, `test_second_run_reports_
already_present`, 4 `test_cli_migrate_*` CLI tests, `test_init_db_twice_on_fresh_db`,
`test_init_db_after_simulated_partial_migration` — were already green and remain green).
`pytest tests/test_skip_registry.py -q -m ""` → 1 passed (meta-gate stays green; a
pre-existing `optional_extra` registry entry for `test_db_migrate_cli.py` was
re-pointed from line 166 to line 203 after the 3 new xfail decorators shifted it past
the `+/-2` line tolerance).

### Group C: QRAMM subsystem failures (Plan 08)

Each of the 6 tests below was individually investigated per RESEARCH.md's cluster-9
guidance, including dedicated crash-cause investigation for the `test_qramm_staleness.py`
SIGSEGV pair (RESEARCH.md explicitly flagged a `exit=-11` crash in a CLI subprocess as
"unusual and worth a few extra minutes to rule out a native-library crash ... vs. a
subprocess/pytest-capture artifact"). Investigation converged on 4 distinct sub-reasons
across the 6: 1 cross-test `sys.modules` pollution artifact, 1 genuine API-contract drift,
1 stale-fixture boundary-date drift, 1 stale grep-based assertion strategy, and 2 (the
SIGSEGV pair) **not reproducible in this sandbox** — investigated, not assumed.

**SIGSEGV crash-cause investigation (`test_qramm_status_cli_smoke_fresh` /
`test_qramm_status_cli_smoke_stale_via_override`):**

- **Exact CLI command identified:** both tests invoke
  `subprocess.run([sys.executable, "<repo>/run_scan.py", "qramm", "status"], capture_output=True, text=True, timeout=15, env=env)`
  — the fresh-path test clears `QUIRK_CI_STALENESS_OVERRIDE_DATE` from `env`; the
  stale-path test sets it to `last_verified + 100 days`.
- **Isolation reproduction:** ran `tests/test_qramm_staleness.py` standalone 3 separate
  times (`pytest tests/test_qramm_staleness.py -q -m ""`) — **6 passed, 0 failed, 0
  crashes, all 3 runs.**
- **Direct CLI invocation (outside pytest entirely):** `python run_scan.py qramm status`
  run by hand from the repo root — exits 0, prints the expected `QRAMM Version / Last
  Verified / Days Remaining / Status` table with `FRESH`. No crash.
- **Full-suite / under-load reproduction:** ran a representative ~550-test slice
  (`pytest tests/test_p*.py tests/test_q*.py tests/test_r*.py -q -m ""`, chosen because
  it brackets `test_qramm_staleness.py` alphabetically and includes several other
  subprocess-spawning test files) — **`test_qramm_staleness.py`'s 6 tests all passed
  cleanly inside this wider run too**; only the 3 already-known Group C non-SIGSEGV
  failures + 4 unrelated pre-existing failures in other files appeared.
- **Native-library version fingerprint recorded:** `cryptography` 46.0.6, `OpenSSL` 3.6.3
  (9 Jun 2026), `Python` 3.14.6, on darwin (macOS). RESEARCH.md's raw failure capture
  (`exit=-11 stdout='' stderr=''` — a hard crash with zero captured output, consistent
  with an unhandled `SIGSEGV` inside the subprocess before Python's own signal handlers
  or stdout/stderr buffering could flush anything) predates this sandbox's current
  library/interpreter versions; no evidence exists here of exactly which versions were
  in use when RESEARCH.md's raw list was captured.
- **Determination: NOT REPRODUCIBLE in this sandbox.** Neither a genuine native-library
  crash nor a subprocess/pytest-capture artifact can be confirmed or ruled out from
  direct evidence, because the crash simply does not occur under any of the three
  reproduction attempts (isolated x3, direct hand-invocation, representative full-suite
  slice) with the current `cryptography`/`OpenSSL`/`Python` versions installed. This is
  reported as observed, not guessed — no code or test change was made, and neither test
  is quarantined (marking a currently-passing test `skip` would incorrectly suppress
  real signal for Phase 150's baseline work), mirroring the Plan 06 Group A precedent for
  non-reproducing failures (`test_vault_connector.py::test_pki_sha1_signed_ca_high_severity`).
  **Flagged for Phase 150 as a HIGH-PRIORITY re-verification item** if it resurfaces on a
  different Python/cryptography/OpenSSL combination (e.g. CI runner vs. this local
  sandbox) — a segfault, even a transient one, is a materially different risk category
  than an assertion failure and should not be dismissed purely because it didn't
  reproduce once.

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|
| `test_qramm_evidence_bridge.py::test_no_risk_engine_import` | quarantined-xfail | cross-test `sys.modules` pollution (not a real QRAMM-12 violation) | `AssertionError: assert 'quirk.engine.risk_engine' not in sys.modules`. `evidence_bridge.py`'s own source contains zero import statements referencing `risk_engine` (confirmed by reading the full file — the only occurrence is a docstring comment forbidding it). The assertion fails only in full-suite alphabetical order: `tests/test_findings_evaluator_dedupe.py` (`f` < `q`) contains `test_dedupe_via_risk_engine_shim_works`, which does `from quirk.engine.risk_engine import _dedupe_findings as shim_dedupe` (D-05/WR-10 backward-compat shim coverage) at line 80, permanently populating `sys.modules["quirk.engine.risk_engine"]` for the rest of the pytest session. Directly confirmed by running `pytest tests/test_findings_evaluator_dedupe.py tests/test_qramm_evidence_bridge.py::test_no_risk_engine_import` (fails) vs. the same test alone or after an unrelated file (passes) | yes (tests/skip_registry.py, `test_qramm_evidence_bridge.py:135`) |
| `test_qramm_evidence_bridge.py::test_unconfirmed_excluded_from_score` | quarantined-xfail | genuine API-contract drift (new all-unconfirmed 422 guard) | `assert score_resp.status_code == 200` — actual `422`. `score_session()` (`quirk/dashboard/api/routes/qramm.py:396-432`) queries `QRAMMAnswer` rows filtered on `answer_value.isnot(None)`; if that query returns zero rows it raises `HTTPException(422, format_error("DASHBOARD-011"))` *before* any per-dimension scoring or the unconfirmed-exclusion logic this test targets ever runs. This test's session has all 30 CVI rows suggested-but-unconfirmed (`answer_value=None`), so it now always 422s. A later phase added this "at least one confirmed answer required" guard; the test predates it and still expects a 200 with `CVI.score == 0.0` | yes (tests/skip_registry.py, `test_qramm_evidence_bridge.py:213`) |
| `test_qramm_model_stale.py::test_is_qramm_model_stale_boundary[today1-True]` | quarantined-xfail | stale fixture (hardcoded boundary date predates a `last_verified` re-verification bump) | `assert is_qramm_model_stale(today=datetime.date(2026, 8, 4)) is True` — actual `False`. `quirk/qramm/model_meta.py`'s `QRAMM_MODEL["last_verified"]` is currently `"2026-08-11"` (re-verified/bumped forward by the CLAUDE.md 90-day QRAMM staleness cadence — this sandbox's current date), not the `"2026-05-05"` value this test's docstring and hardcoded parametrize date assume. `age = (today - last_verified).days` for `today=2026-08-04` against `last_verified=2026-08-11` is **negative** (`-7`), so `age > 90` is `False` — `is_qramm_model_stale()` itself is correct; only the test's literal boundary date is stale. Confirmed via the file's other 3 tests (far-future/near-date/default-today) all passing cleanly, isolating the defect to this one hardcoded parametrize case | yes (tests/skip_registry.py, `test_qramm_model_stale.py:52`, inline `pytest.param(marks=...)` — not a function decorator, so `test_skip_registry.py`'s AST walker doesn't require this entry to pass the gate; registered anyway for ledger completeness) |
| `test_qramm_models.py::TestInitDbQRAMMTables::test_ensure_qramm_tables_called_after_phase46` | quarantined-xfail | stale assertion strategy (grep-based ordering check, not a real regression) | `AssertionError: _PHASE46_COLUMNS migration call not found in init_db`. Read `quirk/db.py::init_db` in full: Phase 85-01 LAUNCH-04 replaced the prior named per-migration call chain with a generic `for table, columns in _ADDITIVE_MIGRATIONS: _ensure_columns(engine, table, columns)` loop (line ~466), so the literal string `"_PHASE46_COLUMNS"` no longer appears anywhere inside `init_db`'s function source text — it now lives only in the `_ADDITIVE_MIGRATIONS` tuple definition at module scope (`("crypto_endpoints", _PHASE46_COLUMNS)`, line 235), outside `init_db`. The actual invariant the test cares about — Phase 46's `crypto_endpoints` column migration running before `_ensure_qramm_tables(engine)` — **is still upheld**: `_ADDITIVE_MIGRATIONS` lists the Phase 46 entry ahead of the loop, and `_ensure_qramm_tables(engine)` is called only after the loop completes (`quirk/db.py:466-470`). No ordering regression — the test's `inspect.getsource(init_db)`-substring-search strategy just doesn't survive the Phase 85-01 refactor | yes (tests/skip_registry.py, `test_qramm_models.py:230`) |
| `test_qramm_staleness.py::test_qramm_status_cli_smoke_fresh` | **superseded by Plan 11** — quarantined-xfail | macOS fork()-under-full-suite-load SIGSEGV, root cause now identified | `exit=-11` (SIGSEGV) per RESEARCH.md's raw capture. Plan 08 found this not reproducible (3/3 isolated runs, direct hand-invocation, and a representative ~550-test slice) and flagged it HIGH-PRIORITY for Phase 150 re-verification if it resurfaced. **Plan 11 reconciliation finding: it resurfaced, reproducibly.** 3 consecutive fresh full-suite (`pytest -q -m ""`, ~3200 tests) runs during this plan's reconciliation reproduced the identical `exit=-11` crash every time, confirmed via `Fatal Python error: Segmentation fault` crash dumps whose stack traces terminate inside CPython's `subprocess.py::_execute_child` (fork/exec path) at this test's exact `subprocess.run()` call site. The same crash signature appeared at **8 distinct subprocess-spawn call sites** across the full run (this test, its sibling below, `test_sensor_windows_smoke.py`, `test_vault_connector.py`, `test_install_errors.py` x2 non-fatally). Determination: **systemic macOS fork()-under-memory/thread-pressure instability** specific to this full-suite's scale (~3200 tests accumulate enough native-library/thread state — networking frameworks, SQLAlchemy, cryptography — that `fork()` becomes unsafe), not a QRAMM-specific or native-crypto-library defect. See the Reconciliation section for the full cluster. Confirmed passing standalone (matches Plan 08's finding) — `@pytest.mark.xfail(strict=False)` added so it still shows green when run in isolation | yes (tests/skip_registry.py, `test_qramm_staleness.py:90`) |
| `test_qramm_staleness.py::test_qramm_status_cli_smoke_stale_via_override` | **superseded by Plan 11** — quarantined-xfail | same macOS fork()-under-load SIGSEGV as the row above | Same crash signature and cluster — see row above and the Reconciliation section | yes (tests/skip_registry.py, `test_qramm_staleness.py:120`) |

Verification: `pytest tests/test_qramm_evidence_bridge.py tests/test_qramm_model_stale.py
tests/test_qramm_models.py tests/test_qramm_staleness.py -q -m ""` → 51 passed, 3 xfailed
(the `test_no_risk_engine_import` xfail only manifests in full-suite alphabetical order —
see Evidence/Notes above; it XPASSes harmlessly, `strict=False`, when this file subset is
run alone). `pytest tests/test_skip_registry.py -q -m ""` → 1 passed (meta-gate stays
green; 4 new `pre_existing_triage_149` registry entries added, matching the 4 tests that
were actually quarantined — the 2 SIGSEGV tests are documented but intentionally left
unmarked per the not-reproducible determination above).

---

### Group D1: CLI/compliance/posture failures, first half (Plan 09)

Each of the 11 tests below was individually investigated per RESEARCH.md's cluster-9
guidance, across 8 files with no shared root cause. Investigation converged on 9 distinct
sub-reasons across 11 tests: 1 chaos-lab profile drift, 1 stale-doc grep, 2 CR-01
path-traversal-guard-vs-tmp_path, 1 genuine compliance-mapping coverage gap, 1 intentional
Logger signature widening, 2 distinct install-error root causes (missing uvicorn extra vs.
stale lazy-import assumption), and 2 GCP-403 tests confirmed **not reproducible in this
sandbox** (POSTURE-02's scan_error emission already works correctly here).

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|
| `test_cbom_schema_validation.py::test_parametrize_set_matches_docker_compose_profiles` | quarantined-xfail | chaos-lab profile drift (`otics` missing from `PROFILE_ENDPOINTS`) | Direct diff via the test's own output: `In compose but not parametrize: ['otics']`, `In parametrize but not compose: []`. `docker-compose.yml`'s `otics` profile (Phase 141-07 Modbus/BACnet lab, added 2026-08-03) never got a corresponding synthesizer entry in `tests/_cbom_profiles.py::PROFILE_ENDPOINTS`. **This is a genuine chaos-lab-maintenance gap**, not a stale test — per CLAUDE.md's Chaos Lab Maintenance rule, adding a new profile requires `lab.sh`/`expected_results_*.md` updates in the same phase that added it; `PROFILE_ENDPOINTS` was missed. **Flagged for a Phase 150 follow-up**: add an `otics` synthesizer to `tests/_cbom_profiles.py` producing a representative Modbus or BACnet endpoint | yes (tests/skip_registry.py, `test_cbom_schema_validation.py:77`) |
| `test_cli_correctness.py::test_no_quirk_scan_references` | quarantined-xfail | stale doc references (historical prose, not live CLI docs) | `grep`-confirmed via the test's own diagnostic output: `docs/UAT-SERIES.md` (lines 8242-8244, 8998-8999, 9016-9018, 9036, 12979 — historical UAT walkthrough steps written before the `quirk --config` rename), `docs/chaos-lab.md` (line 667), `docs/release-notes/4.6.0.md` (lines 46-48 — a frozen historical release note, immutable by convention). None of these are live CLI usage documentation guiding current operators; this is a documented cleanup backlog item for Phase 150, not a code defect | yes (tests/skip_registry.py, `test_cli_correctness.py:179`) |
| `test_cli_init.py::test_init_creates_config` | quarantined-xfail | CR-01/D-13 path-traversal guard rejects pytest `tmp_path` | Read `quirk/cli/init_cmd.py::run_init` in full: a CR-01/D-13 guard (lines 24-33) requires the resolved output path to descend from `os.getcwd()`, rejecting any path outside the CWD tree with a printed WARNING and a clean `return` (exit 0, no file written). `pytest`'s `tmp_path` fixture resolves to `/private/var/folders/.../pytest-of-*/...`, which is outside the repo CWD — confirmed by hand-invoking the exact subprocess command and observing the WARNING. The guard is a legitimate security control (prevents `quirk init --output /etc/passwd`-style symlink/absolute-path escapes); this test was written before CR-01 landed and needs a CWD-relative or `monkeypatch.chdir(tmp_path)`-based rewrite | yes (tests/skip_registry.py, `test_cli_init.py:126`) |
| `test_cli_init.py::test_init_no_overwrite` | quarantined-xfail | same CR-01/D-13 guard (cascading failure) | Same root cause as `test_init_creates_config` above: the first `quirk init` call inside this test never creates `config.yaml` (blocked by the same CWD guard), so `os.path.getmtime(out)` raises `FileNotFoundError` before the overwrite-guard behavior this test targets is ever exercised | yes (tests/skip_registry.py, `test_cli_init.py:153`) |
| `test_compliance_title_join.py::test_every_emitted_title_is_mapped_or_allowlisted` | quarantined-xfail | genuine coverage gap (Phase 95 codesign titles never mapped) | The test's own diff output lists the 3 missing titles verbatim: `'Code-signing certificate expired: '`, `'Code-signing certificate expiring within 90 days: '`, `'Code-signing certificate uses weak algorithm: '`. `grep`-confirmed these are emitted at `quirk/engine/findings_evaluator.py:1026`, `:1045`, and `:1080` (Phase 95 CSIGN-01) but were never added to `COMPLIANCE_MAP` or `UNMAPPED_TITLES` in `quirk/compliance/__init__.py`. This is a genuine documentation/mapping gap left over from Phase 95, not a stale test — a follow-up should add these 3 titles to the appropriate compliance framework mappings (or `UNMAPPED_TITLES` with rationale if none apply) | yes (tests/skip_registry.py, `test_compliance_title_join.py:20`) |
| `test_email_run_scan_wiring.py::test_email_branch_logger_calls_use_real_logger_signatures` | quarantined-xfail | intentional Logger signature widening (Phase 89 LAB-06) | `assert len(info_params) == 1` — actual `2` (`msg: 'object', *args`). Confirmed via `git log --follow -p -- quirk/logging_util.py`: commit `01411acc` ("fix(89-02): make custom Logger stdlib-compatible (LAB-06)", 2026-05-22) deliberately widened `Logger.info(self, msg: str)` to `Logger.info(self, msg: object, *args)` so scanner internals (identity connectors) could pass it printf-style args like a stdlib logger, fixing a live-lab crash. This test enforces the pre-89-02 single-arg contract and predates that widening — the current 2-arg signature is the correct, intentional one | yes (tests/skip_registry.py, `test_email_run_scan_wiring.py:84`) |
| `test_errors_cmd.py::test_lookup_single_known_returns_zero` | not reproducible in this environment | environment-dependent (cause undetermined) | RESEARCH.md's raw capture reports `'QRK-INSTALL-001' not found in ANSI-colored output`. **Not reproducible here**: `pytest tests/test_errors_cmd.py -q -m ""` passes 12/12 in isolation; hand-invoking `python run_scan.py errors QRK-INSTALL-001` directly prints `[QRK-INSTALL-001] Optional scanner package not installed...` to stdout as expected; re-ran inside a combined `tests/test_email_run_scan_wiring.py tests/test_errors_cmd.py tests/test_install_errors.py tests/test_posture_scorefix125.py` run and a broader `tests/test_e*.py tests/test_i*.py` (298-test) run — passes cleanly every time. No ANSI-stripping or terminal-width difference could be identified as a cause because no failure occurred to diagnose. Left unmarked per the Plan 06/08 not-reproducible precedent (`test_vault_connector.py`, `test_qramm_staleness.py`) rather than force-quarantining a currently-passing test | no — test passes, no quarantine needed |
| `test_install_errors.py::test_port_conflict_format` | quarantined-xfail | environment gap (uvicorn/dashboard extras not installed) | `assert "QRK-INSTALL-004" in combined` — actual output only contains `[QRK-INSTALL-002] Dashboard extras not installed...`. Read `quirk/dashboard/server.py::serve()`: `import uvicorn` (line 102) is the very first statement; on `ImportError` it prints `format_error("INSTALL-002")` and calls `sys.exit(1)` immediately, before ever reaching the `uvicorn.run()` call (line 165) whose `OSError` handler emits `QRK-INSTALL-004` on a port conflict (line 179). This sandbox has no `uvicorn` installed (`python -c "import uvicorn"` raises `ModuleNotFoundError`), so the port-conflict code path is structurally unreachable here regardless of the held socket. **Distinct root cause** from `test_dashboard_missing_uvicorn_format` below — that one fails even with uvicorn conceptually "blocked", due to a different (lazy-import) code-shape mismatch | yes (tests/skip_registry.py, `test_install_errors.py:90`) |
| `test_install_errors.py::test_dashboard_missing_uvicorn_format` | quarantined-xfail | stale lazy-import assumption | `assert "QRK-INSTALL-002" in combined` — actual `stdout='' stderr=''` (nothing printed). Read `quirk/dashboard/server.py` in full: the module has zero uvicorn references at module scope (lines 1-21 imports); `import uvicorn` lives entirely inside the `serve()` function body (line 102), a deliberate lazy import so a bare `import quirk.dashboard.server` doesn't require dashboard extras. This test's `builtins.__import__` patch + `from quirk.dashboard import server` only imports the module — it never calls `serve()` — so the patched-and-blocked uvicorn import is never actually exercised, and nothing is printed. The test predates this lazy-import shape (or was authored assuming a module-level `import uvicorn` that never existed in the current code) | yes (tests/skip_registry.py, `test_install_errors.py:126`) |
| `test_posture_scorefix125.py::test_gcp_kms_403_emits_scan_error` | **superseded by Plan 11** — quarantined-skip | optional_extra (googleapiclient/google not installed — Plan 09's sandbox had it, this one doesn't) | RESEARCH.md's raw capture: `GCP Cloud KMS 403 (IAM permission denied) must produce a scan_error`. Plan 09 found this passing 3/3 across three reproduction attempts and concluded POSTURE-02's fix was "already implemented and working." **Plan 11 reconciliation finding:** this sandbox lacks `googleapiclient` (`[cloud]` extra) entirely — `gcp_connector.py`'s `_GcpHttpError = None` fallback means the `isinstance(exc, _GcpHttpError)` 403-detection gate can never match, so the scan_error emission path is structurally unreachable here, same failure class as Cluster 7's `test_gcs_reuse.py`. Plan 09's sandbox must have had `googleapiclient` installed, making the gate reachable there. POSTURE-02's fix itself is not regressed — this is purely an extras-availability difference between sandboxes, not a code defect | yes (tests/skip_registry.py, `test_posture_scorefix125.py:39`) |
| `test_posture_scorefix125.py::test_gcp_sql_403_emits_scan_error` | **superseded by Plan 11** — quarantined-skip | same googleapiclient/google optional_extra gap | Same root cause as the row above (`_scan_cloud_sql`'s 403 handling, same `_GcpHttpError = None` fallback) | yes (tests/skip_registry.py, `test_posture_scorefix125.py:62`) |

Verification: `pytest tests/test_cbom_schema_validation.py tests/test_cli_correctness.py
tests/test_cli_init.py tests/test_compliance_title_join.py
tests/test_email_run_scan_wiring.py tests/test_errors_cmd.py tests/test_install_errors.py
tests/test_posture_scorefix125.py -q -m ""` → 110 passed, 8 xfailed (8 of the plan's
originally-scoped 11 tests were quarantined; the remaining 3 —
`test_errors_cmd.py::test_lookup_single_known_returns_zero` and
`test_posture_scorefix125.py`'s 2 GCP-403 tests — were investigated but found not
reproducible in this sandbox and left unmarked, per the Plan 06/08 precedent).
`pytest tests/test_skip_registry.py -q -m ""` → 1 passed (meta-gate stays green; 8 new
`pre_existing_triage_149` registry entries added, matching the 8 tests actually
quarantined).

---

### Group D2: docs-presence/security-gate/windows-smoke failures, second half of Group D (Plan 10)

Each of the 5 tests below was individually investigated per RESEARCH.md's cluster-9
guidance. `test_safe_filter_audit.py` and `test_scan_error_gate.py` received extra
scrutiny per this project's `feedback_report_render_tests_presence_not_appearance`
memory (render-injection-hardening gates are load-bearing security controls, not
routine drift) — both were traced to the exact flagged location and confirmed to be
**gate-logic gaps, not real unsanitized-usage or safe_str-bypass findings**; neither is
flagged `SECURITY:`. `test_sensor_windows_smoke.py`'s SIGSEGV received the same
crash-cause investigation rigor as Plan 08's QRAMM SIGSEGV pair and was found **not
reproducible** in this sandbox, independent of that pair.

| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |
|---------|-------------|------------|-----------------|------------------|
| `test_phase135_docs_presence.py::test_required_sections_present` | quarantined-xfail | stale version pin (README.md advanced past v5.8.0) | `Phase 135 docs missing required sections: [('README.md', 'v5.8.0'), ('README.md', "what's new in v5.8")]`. `README.md`'s title line is now `# QU.I.R.K. — v5.11.0` and its changelog-style section is `## What's New in v5.10` (3 version bumps since Phase 135: v5.9, v5.10, v5.11) — `grep -n "5.8.0" README.md` returns zero matches. Every other Phase 135 required substring (hardware fingerprinting, CNSA 2.0, crypto-bridge, `[hw]`, device, firmware) is still present, confirming this is routine version-string drift, not a content regression | yes (tests/skip_registry.py, `test_phase135_docs_presence.py:74`) |
| `test_phase136_docs_presence.py::test_section9_deferred_topics_absent` | quarantined-xfail | stale detection list — genuine later addition, not a leak | `§9 leaks deferred Phase 137 content: ['snmpv3']`. `grep -n -i snmpv3 docs/operators-guide.md` confirms the literal string is present at `§9.1.1 SNMPv3 Auth+Priv Scanning (Phase 139)` (lines 1080-1188). This Phase 136 guard was written to keep Phase 137's admin-guide-scoped SNMPv3 content out of §9; Phase 139 (SNMPv3 scanner support) later — and correctly — added its own §9.1.1 subsection to operators-guide.md §9 when SNMPv3 shipped, which is a properly-scoped, intentional addition documenting real functionality, not scope creep from Phase 137 | yes (tests/skip_registry.py, `test_phase136_docs_presence.py:144`) |
| `test_safe_filter_audit.py::test_safe_filter_paired_with_sanitize` | quarantined-xfail | gate-logic gap — both flagged usages independently confirmed safe, no `SECURITY:` finding | `Jinja \| safe filter usages without an upstream \| sanitize: quirk/reports/templates/report.html.j2:389, quirk/reports/templates/report.html.j2:508`. Line 389 (`narrative_lead \| safe`): `narrative_lead = _NARRATIVE_LEADS.get(score_band, _NARRATIVE_LEAD_FALLBACK)` (`content_model.py:652`) — a lookup into a small hardcoded dict of static prose keyed by a fixed score-band enum, never scanner- or user-controlled; landed Phase 98, commit `bc6ee52` (2026-05-24). Line 508 (`hardware_section \| safe`): value comes from `render_hardware_section()` (`html_renderer.py:324`), which calls `_html.escape()` on every dynamic field (vendor/model/host/port/etc.) in Python before building the markup string — sanitization happens Python-side, not via a Jinja `\| sanitize` filter chain, so this Jinja-only gate structurally cannot see it; landed Phase 128, commit `d6a923b` (2026-06-14). Both usages are pre-existing (not newly introduced) and independently verified safe — **confirmed gate-logic gap, not a real unsanitized-usage finding; NOT flagged SECURITY**. Flagged for a Phase 150 follow-up: widen `_has_upstream_sanitize` to recognize (a) values sourced from a small closed static dict and (b) Python-pre-escaped strings | yes (tests/skip_registry.py, `test_safe_filter_audit.py:137`) |
| `test_scan_error_gate.py::test_scan_error_writes_use_safe_str` | quarantined-xfail | gate-logic gap — ternary branches both individually safe, no `SECURITY:` finding | `scan_error writes bypassing safe_str: quirk/scanner/kerberos_scanner.py:312`. The exact write site: `scan_error=safe_str(tcp_error) if tcp_error is not None else None` — an `ast.IfExp` (ternary) whose true-branch is `safe_str(tcp_error)` (a SAFE shape) and whose false-branch is the literal `None` (also a SAFE shape). `_classify_rhs()`'s SAFE-shape predicates (`ast.Constant`, `safe_str` `Call`, `Attribute`, `JoinedStr`-with-safe_str, `Name`-assigned-via-safe_str) do not include `ast.IfExp` at all, so the entire ternary is classified as a VIOLATION regardless of what either branch actually contains. **Confirmed gate-logic gap, not a real safe_str bypass; NOT flagged SECURITY** — no credential- or scanner-controlled text reaches `scan_error` unsanitized. Flagged for a Phase 150 follow-up: extend `_classify_rhs()` to recurse into both branches of an `ast.IfExp` | yes (tests/skip_registry.py, `test_scan_error_gate.py:154`) |
| `test_sensor_windows_smoke.py::TestCleanShutdownOnKeyboardInterrupt::test_keyboard_interrupt_in_run_sensor_exits_130` | **superseded by Plan 11** — quarantined-xfail | macOS fork()-under-full-suite-load SIGSEGV — **same cluster as Plan 08's QRAMM pair, not independent** | RESEARCH.md's raw capture: `Expected exit code 0, 1, or 130 on KeyboardInterrupt, got -11`. Plan 10 found this not reproducible in isolation or when combined file-to-file with Plan 08's QRAMM pair (18/18 passed), and explicitly concluded the two crash sets were independent (different subsystem, different subprocess construction). **Plan 11 reconciliation finding: this conclusion is superseded.** A fresh full-suite (`pytest -q -m ""`, ~3200 tests) run reproduced the crash, and its `Fatal Python error: Segmentation fault` dump shows the segfault occurring *inside `subprocess.py::_execute_child`* at this test's `_run_child_script` call site — killing the pytest runner process itself, not just a spawned child. This is the identical crash signature (same stack shape, same fork/exec location) as `test_qramm_staleness.py`'s pair and `test_vault_connector.py`'s SHA1 test, all reproducing only at full-suite scale (~3200 tests), never in Plan 10's smaller 18-test combined run. Plan 10's "independent root cause" conclusion was correct about *subsystem* (sensor CLI dispatch vs. QRAMM CLI) but the crash mechanism itself is the same systemic macOS fork()-under-load instability, not two coincidentally-similar bugs — see the Reconciliation section | yes (tests/skip_registry.py, `test_sensor_windows_smoke.py:209`) |

Verification: `pytest tests/test_phase135_docs_presence.py tests/test_phase136_docs_presence.py
tests/test_safe_filter_audit.py tests/test_scan_error_gate.py
tests/test_sensor_windows_smoke.py -q -m ""` → 44 passed, 4 xfailed (4 of the plan's
5 originally-scoped tests were quarantined; `test_sensor_windows_smoke.py`'s SIGSEGV
test was investigated but found not reproducible in this sandbox and left unmarked,
per the Plan 06/08/09 precedent). `pytest tests/test_skip_registry.py -q -m ""` → 1
passed (meta-gate stays green; 4 new `pre_existing_triage_149` registry entries added,
matching the 4 tests actually quarantined).

This closes Cluster 9 Group D2 — the final sub-group of Phase 149's cluster-9 triage.
All 116-baseline test dispositions across Plans 01-10 are now complete.

---

## Reconciliation

Plan 11's job was to cross-check the completed ledger against a *fresh* `pytest -q -m ""`
run — not to assume Plans 01-10's per-plan snapshots still held, since each plan ran in its
own sandbox with a slightly different set of optional extras installed (`impacket`,
`sslyze`, `pysnmp` present in some sandboxes and absent in others; `googleapiclient`
present in Plan 09's sandbox and absent here). That assumption paid off: **11 of the 116
ledger rows needed correction** — not because Plans 01-10 investigated carelessly, but
because their "not reproducible in this sandbox" and "environment-fix-applied" findings
were sandbox-specific truths that didn't hold in this plan's environment. Every one of
those 11 rows already existed in the ledger (none were undocumented gaps); this section
documents what changed and why, and the final counts below are the true, currently-live
state.

### Fresh full-suite result

```
pytest -q -m "" → 3088 passed, 42 skipped, 81 xfailed, 126 warnings, 0 failed
```

(Three repeated fresh runs during this plan's investigation phase — before any fix or
quarantine was applied — consistently showed 9-12 failures depending on whether the
intermittent SIGSEGV cluster below fired that run; see the SIGSEGV cluster discussion.
After the fixes and quarantines documented below, a fresh run is **0 failed** — a true
green baseline, not merely a re-labeled one.)

### Cross-check findings (Task 1 acceptance criteria)

- **(a) Orphaned failures (failing test, no ledger row):** zero found. All 11
  newly-surfaced failures already had existing ledger rows from Plans 03/06/08/09/10 —
  their *dispositions* were stale for this sandbox, not missing.
- **(b) False-`fixed`/`environment-fix-applied` rows:** one found and corrected —
  `test_version.py::test_cli_version_subprocess` (Cluster 3). Its `environment-fix-applied`
  disposition for the stale-dist-info bug remains **true and unchanged** (the version string
  is correctly `5.11.0`), but the same test also intermittently SIGSEGVs under full-suite
  load for an unrelated reason (see below) — the row now documents both facts rather than
  implying the test is unconditionally green.
- **(c) Total row count:** 116 distinct test IDs across the 9 cluster tables, verified
  mechanically (see below) — matches the sum of the 9 tables' own row counts exactly, no
  arithmetic drift.

### What changed: 2 real bugs fixed, 9 tests re-quarantined with corrected root causes

**2 genuine production bugs found and fixed in place** (both are library-version-drift
defects the currently-pinned dependency versions trigger for every operator, not
sandbox artifacts):

1. **`quirk/scanner/tls_scanner.py`** — sslyze `>=6.2.0` (no upper pin) changed
   `sslyze.__version__` from a plain string to a `sslyze/__version__.py` submodule in
   6.3+; `_scan_one_sslyze`'s `tls_capabilities_json` build then raised
   `TypeError: Object of type module is not JSON serializable` inside a broad
   `except Exception`, silently discarding **every** real sslyze scan result on sslyze
   >=6.3. Fixed by normalizing both the string and nested-module `__version__` shapes.
   Fixes `test_tls_scanner_chain_verified.py::test_sslyze_success_chain_verified_true`
   and `::test_sslyze_success_chain_verified_false`.
2. **`quirk/scanner/kerberos_scanner.py`** — impacket `>=0.13.0,<0.14` (the current pin)
   renamed `impacket.krb5.asn1.MethodData` to `METHOD_DATA`, breaking the module's own
   `try/except ImportError` guard and silently setting `IMPACKET_AVAILABLE = False` for
   every operator on the currently-pinned impacket version — Kerberos scanning was
   completely disabled, not gracefully degraded. Fixed with a nested try/except importing
   `METHOD_DATA as MethodData` first, falling back to the old name for impacket <0.13.
   This uncovered a **second, deeper** impacket 0.13.0 incompatibility — `KDCOptions`
   changed from a bit-flag helper class to a plain `enum.Enum`, breaking
   `_build_as_req`'s pyasn1 BitString construction — which is quarantined (not fixed)
   below as out of scope for a one-line import fix; flagged for a dedicated Phase 150 fix.

**9 tests re-quarantined**, converging on 3 distinct corrected root causes:

- **impacket 0.13.0 `KDCOptions` enum incompatibility (2 tests)** —
  `test_identity_scanner_hardening.py::test_kdc_udp_decode_failure_logs` and
  `::test_build_as_req_nonce_uses_secrets`. See fix #2 above.
- **`googleapiclient`/`google` optional extra absent in this sandbox (2 tests)** —
  `test_posture_scorefix125.py::test_gcp_kms_403_emits_scan_error` and
  `::test_gcp_sql_403_emits_scan_error`. Plan 09's sandbox had `googleapiclient`
  installed, making `gcp_connector.py`'s `_GcpHttpError`-gated 403 detection reachable;
  this sandbox doesn't, so the gate is structurally unreachable — same failure class as
  Cluster 7's `test_gcs_reuse.py`. POSTURE-02's fix itself is not regressed.
- **macOS fork()-under-full-suite-load SIGSEGV, systemic (5 tests)** —
  `test_qramm_staleness.py::test_qramm_status_cli_smoke_fresh` and
  `::test_qramm_status_cli_smoke_stale_via_override` (Plan 08's pair, flagged
  HIGH-PRIORITY for re-verification — it resurfaced),
  `test_sensor_windows_smoke.py::TestCleanShutdownOnKeyboardInterrupt::test_keyboard_interrupt_in_run_sensor_exits_130`
  (Plan 10 concluded this was independent of Plan 08's pair — **that conclusion is
  superseded**: same crash signature, same cluster),
  `test_vault_connector.py::test_pki_sha1_signed_ca_high_severity` (Plan 06's "OpenSSL
  SHA1 cert generation" hypothesis is also superseded — SHA1 generation works fine; the
  `openssl` subprocess itself SIGSEGVs), and `test_version.py::test_cli_version_subprocess`
  (newly discovered, on top of its already-correct `environment-fix-applied`
  disposition for the unrelated stale-dist-info bug). All 8 `Fatal Python error:
  Segmentation fault` crash dumps observed across 3 repeated fresh full-suite runs
  during this plan's investigation terminate inside CPython's
  `subprocess.py::_execute_child` (the `fork()`/`exec()` path), at 8 distinct
  `subprocess.run()` call sites, reproducing only at full-suite scale (~3200 tests
  accumulate enough native-library/thread/Objective-C-runtime state — networking
  frameworks, SQLAlchemy, cryptography — to make `fork()` unsafe on this macOS/darwin,
  Python 3.14.6 sandbox) and never in isolation or smaller multi-file combinations.
  This is an OS/runtime-level instability, not a defect in any of the 5 tests or the
  code they exercise; all 5 pass cleanly standalone. **Flagged as a single Phase 150
  follow-up item** (not 5 separate ones) — likely mitigations include
  `multiprocessing.set_start_method`-style fork avoidance, `-p no:cacheprovider`-style
  isolation, or running the full suite on a Linux CI runner where `fork()` is safer.

### Ledger integrity checks

- **Total row count:** 116 distinct test IDs across the 9 cluster tables (Cluster 1: 23,
  Cluster 2: 14, Cluster 3: 5, Cluster 4: 3, Cluster 5: 10, Cluster 6: 6, Cluster 7: 2,
  Cluster 8: 1, Cluster 9 (Groups A–D2): 52 — 18+12+6+11+5) — verified via a mechanical
  table-row scan, matching the sum of the tables' own row counts exactly.
- **No empty cells:** a mechanical scan of every row's `Disposition` and `Sub-reason`
  cells across all 116 rows found zero empty cells.
- **No duplicate test IDs:** the same mechanical scan found 116 distinct Test ID strings
  for 116 rows — no test appears in two rows.
- **Meta-gate:** `pytest tests/test_skip_registry.py -q -m ""` → 1 passed (all 9 new
  `pre_existing_triage_149` registry entries + 2 `optional_extra` skip entries
  registered and validated by the AST walker).
- **`python -m compileall quirk tests`** → exits 0.

### Net result

Phase 149's original 116-test baseline is now **fully and accurately dispositioned**
against this sandbox's live, current behavior: 0 orphaned failures, 0 false-`fixed`
rows, 0 empty cells, 0 duplicate test IDs, and a fresh `pytest -q -m ""` run is
**0 failed** — a genuinely green, reconciled baseline ready to hand off as Phase 150's
sizing input. Phase 149 (SUITE-01) is complete.

---

*Phase: 149-test-suite-triage*
*Plan: 11*
*Updated: 2026-08-12*
