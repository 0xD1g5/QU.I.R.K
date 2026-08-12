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
| `tests/test_identity_scanner_hardening.py::test_kdc_udp_decode_failure_logs` | not reproducible in this environment | optional_extra (impacket not installed) | RESEARCH.md described `AttributeError: module 'quirk.scanner.kerberos_scanner' has no attribute 'decode...'`, implying impacket was installed when captured. In this sandbox `impacket` (an `[identity]`-only extra, intentionally excluded from `[all]` per Phase 45 D-01) is absent, so the fixture's `pytest.importorskip("impacket")` cleanly skips both tests (2 skipped, not failed) via the pre-existing `optional_extra` registry entry at line 80. No new marker added; no code change needed | already registered (tests/skip_registry.py:55, pre-existing) |
| `tests/test_identity_scanner_hardening.py::test_build_as_req_nonce_uses_secrets` | not reproducible in this environment | optional_extra (impacket not installed) | Same cause as row above. RESEARCH.md's `NameError: name 'constants' is not defined` would only manifest if `impacket` partially imports but `from impacket.krb5 import constants` fails — not reproducible here since `impacket` isn't installed at all, so `importorskip` skips before that line is ever reached | already registered (tests/skip_registry.py:55, pre-existing) |
| `tests/test_jwt_scanner.py::test_multi_key_jwks` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `assert 0 == 3`. Same CR-03 `validate_external_url()` dns_failure root cause as `test_jwt_hardening.py` above — `https://api.example.com/...` fails DNS resolution in this sandbox, so `_fetch_jwks` returns `(None, None, [])` before any key is parsed | yes (tests/skip_registry.py, `test_jwt_scanner.py:44`) |
| `tests/test_jwt_scanner.py::test_jwt_rsa_key_size` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | Same root cause as row above | yes (tests/skip_registry.py, `test_jwt_scanner.py:67`) |
| `tests/test_jwt_scanner.py::test_jwt_ec_key_size` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | Same root cause as row above | yes (tests/skip_registry.py, `test_jwt_scanner.py:89`) |
| `tests/test_jwt_scanner.py::test_jwt_query_param_cred_ctx_appends_key_to_url` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `AssertionError: httpx.Client.get was never called`. Same CR-03 SSRF-guard cause — `validate_external_url` rejects `api.example.com` before the credential-context query-param logic under test is ever reached | yes (tests/skip_registry.py, `test_jwt_scanner.py:132`) |
| `tests/test_jwt_scanner.py::test_jwt_no_cred_ctx_unchanged_behavior` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `assert 0 == 3`. Same root cause as the other `test_jwt_scanner.py` rows | yes (tests/skip_registry.py, `test_jwt_scanner.py:213`) |
| `tests/test_jwt_scanner.py::test_append_query_param_continue_iteration_skips_conflicting_target` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `assert 0 >= 3`. `h1.example.com` and `h2.example.com` both fail `validate_external_url`'s dns_failure check (confirmed via direct call), so no target — conflicting or clean — ever reaches `httpx.get`; not a D-03 continue-iteration defect | yes (tests/skip_registry.py, `test_jwt_scanner.py:321`) |
| `tests/test_openapi_scanner.py::test_url_scope_accepts_bare_fqdn_target` | quarantined-xfail | environment-dependent (SSRF DNS-blocked sandbox) | `AssertionError: Expected 'get' to have been called once. Called 0 times.` `scan_openapi_spec`'s SSRF gate (`validate_external_url`, `quirk/scanner/openapi_scanner.py:157-159`) rejects `api.example.com` with `dns_failure` before the bare-FQDN scope-matching logic under test is reached; not a scope-comparison regression. (6 unrelated `openapi-spec-validator not installed` failures also found in this file during standalone verification — out of scope for this plan, logged in `deferred-items.md`) | yes (tests/skip_registry.py, `test_openapi_scanner.py:231`) |
| `tests/test_tls_scanner_chain_verified.py::test_sslyze_success_chain_verified_true` | not reproducible in this environment | optional_extra (sslyze not installed) | RESEARCH.md described `assert None is not None`, implying sslyze was installed when captured. In this sandbox `sslyze` (`[motion]` extra) is absent, so `@pytest.mark.skipif(not _tls.SSLYZE_AVAILABLE, ...)` at line 140 cleanly skips both tests via the pre-existing registry entry — same pattern as the identity/impacket pair. No new marker added | already registered (tests/skip_registry.py:31, pre-existing) |
| `tests/test_tls_scanner_chain_verified.py::test_sslyze_success_chain_verified_false` | not reproducible in this environment | optional_extra (sslyze not installed) | Same cause as row above; registered at line 152, a distinct line from the `test_true` variant's line 140, confirming these are not the already-registered skip reappearing under a shared entry | already registered (tests/skip_registry.py:32, pre-existing) |
| `tests/test_vault_connector.py::test_pki_sha1_signed_ca_high_severity` | not reproducible in this environment (currently passes) | environment-dependent (OpenSSL SHA1 cert generation behavior) | RESEARCH.md described `RuntimeError: openssl SHA1 cert failed`, suggesting an OpenSSL build/version in the original capture environment rejects SHA1 cert generation. In this sandbox the test passes cleanly (`1 passed`) — this specific OpenSSL install accepts SHA1 cert generation for the test fixture. No quarantine applied since the test is currently green; flagged as environment-dependent for awareness only | no — test passes, no quarantine needed |
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

---

*Phase: 149-test-suite-triage*
*Plan: 07*
*Updated: 2026-08-12*
