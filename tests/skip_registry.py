"""Phase 41 D-02: Central allowed-skip registry.

Each entry: (file_relative_to_tests_dir, line_number, category, reason)
category in {"optional_extra", "live_infra", "pre_existing_triage_149",
"ci_extras_gap", "gitignored_planning_dir"}

Per CONTEXT.md D-01..D-05: stale skips are deleted; optional-extra and
live-infra skips are registered here so the meta-test gate (test_skip_registry.py)
can validate that no NEW unregistered skip slips into the suite.

Plan 05 deletes the stale skips identified in 41-RESEARCH.md "Skip-Marker
Triage Table" (D-04). Until Plan 05 lands, the meta-test will fail — that
is the intended behavior and the validation that D-04 deletions worked.
"""

ALLOWED_SKIPS = [
    ("test_broker_scanner_kafka.py",    12,  "optional_extra", "broker_scanner is [motion]; D-05"),
    ("test_broker_scanner_rabbitmq.py", 13,  "optional_extra", "broker_scanner is [motion]; D-05"),
    ("test_broker_scanner_redis.py",    13,  "optional_extra", "broker_scanner is [motion]; D-05"),
    ("test_chaos_storage.py",           44,  "live_infra",     "Requires Docker + MinIO"),
    ("test_chaos_storage.py",           71,  "live_infra",     "Requires Docker + MinIO"),
    ("test_dnssec_scanner.py",          480, "live_infra",     "Requires BIND9 chaos lab"),
    ("test_saml_scanner.py",            366, "live_infra",     "Requires SimpleSAMLphp chaos lab"),
    ("test_kerberos_scanner.py",        384, "live_infra",     "Requires Samba DC chaos lab"),
    ("test_cbom_motion_golden.py",      195, "live_infra",     "Fixture regen guard"),
    ("test_cbom_classifier_coverage.py", 84, "live_infra",     "Fixture regen guard (REGEN_CBOM_COVERAGE=1)"),
    ("test_uat_db_integration.py",       29, "live_infra",     "Requires PostgreSQL chaos lab (database profile)"),
    ("test_uat_db_integration.py",       49, "live_infra",     "Requires MySQL chaos lab (database profile)"),
    ("test_uat_db_integration.py",       69, "live_infra",     "Requires PostgreSQL chaos lab (database profile)"),
    ("test_uat_db_integration.py",       84, "live_infra",     "Requires MySQL chaos lab (database profile)"),
    ("test_vault_connector.py",          455, "live_infra",     "Requires Vault-30 chaos lab (vault profile)"),
    ("test_tls_scanner_chain_verified.py", 140, "optional_extra", "sslyze is [motion]; Phase 46 TLS-FIND-06"),
    ("test_tls_scanner_chain_verified.py", 152, "optional_extra", "sslyze is [motion]; Phase 46 TLS-FIND-06"),
    # Phase 65 Plan 01 stubs — replaced by real implementations in Plans 03/04
    ("test_jobs_api.py",  44, "live_infra", "Phase 65 Plan 03 stub — POST /api/jobs row insert"),
    ("test_jobs_api.py",  48, "live_infra", "Phase 65 Plan 03 stub — @file rejection"),
    ("test_jobs_api.py",  52, "live_infra", "Phase 65 Plan 03 stub — empty targets validation"),
    ("test_jobs_api.py",  56, "live_infra", "Phase 65 Plan 03 stub — auth dependency wiring"),
    ("test_jobs_api.py",  60, "live_infra", "Phase 65 Plan 03 stub — CSRF dependency wiring"),
    ("test_jobs_api.py",  64, "live_infra", "Phase 65 Plan 03 stub — GET /api/jobs/{id} response shape"),
    ("test_jobs_api.py",  68, "live_infra", "Phase 65 Plan 03 stub — 404 on unknown job_id"),
    ("test_jobs_api.py",  72, "live_infra", "Phase 65 Plan 03 stub — GET auth dependency"),
    ("test_jobs_api.py",  76, "live_infra", "Phase 65 Plan 03 stub — stage_index computation"),
    ("test_jobs_api.py",  80, "live_infra", "Phase 65 Plan 03 stub — DELETE SIGTERM + cancelled"),
    ("test_jobs_api.py",  84, "live_infra", "Phase 65 Plan 04 stub — lifespan _recover_stale_jobs"),

    # Phase 149 D-04: registered pre-existing drift
    ("test_aws_connector.py",                172, "optional_extra", "boto3 not installed"),
    ("test_cbom_vault_consistency.py",       50,  "live_infra",     "Fixture regen guard (REGEN_CBOM_FIXTURES=1)"),
    ("test_chaos_lab_idempotency.py",        111, "live_infra",     "macOS *:88 collides with system KDC; requires LAB_INCLUDE_KERBEROS=1 (BACK-89)"),
    ("test_cmvp_refresh.py",                 22,  "optional_extra", "bs4 not installed"),
    ("test_cmvp_refresh.py",                 23,  "optional_extra", "httpx not installed"),
    ("test_credential_leakage.py",           306, "live_infra",     "Defensive guard: dashboard_client get_db override not configured"),
    ("test_db_migrate_cli.py",               203, "optional_extra", "run_scan not importable in minimal dev env (optional reporting deps missing)"),
    ("test_distributed_topology.py",         48,  "live_infra",     "Requires docker binary"),
    ("test_identity_scanner_hardening.py",   80,  "optional_extra", "impacket not installed"),
    ("test_jobs_api.py",                     489, "live_infra",     "Linux-only /proc zombie-reconciliation check"),
    ("test_jwt_scanner.py",                  240, "optional_extra", "httpx not installed"),
    ("test_pdf_metadata_constants.py",       19,  "optional_extra", "playwright.sync_api not installed"),
    ("test_pdf_metadata_constants.py",       20,  "optional_extra", "pypdf not installed"),
    ("test_pdf_metadata_constants.py",       56,  "optional_extra", "Playwright Chromium runtime not available"),
    ("test_pqc_discriminator.py",            126, "live_infra",     "Requires oqs-nginx chaos-lab profile"),
    ("test_pqc_discriminator.py",            141, "live_infra",     "Requires oqs-nginx chaos-lab profile"),
    ("test_report_injection_hardening.py",   244, "optional_extra", "playwright.sync_api not installed"),
    ("test_report_injection_hardening.py",   245, "optional_extra", "pypdf not installed"),
    ("test_report_injection_hardening.py",   258, "optional_extra", "Playwright Chromium binary not available"),
    ("test_report_render_undetermined_hosts.py", 150, "optional_extra", "python-docx not installed"),
    ("test_report_render_undetermined_hosts.py", 162, "optional_extra", "python-docx not installed"),
    ("test_report_render_undetermined_hosts.py", 215, "optional_extra", "python-docx not installed"),
    ("test_scheduler_cmd.py",                314, "live_infra",     "SIGTERM not supported on Windows"),
    ("test_snmp_scanner_contract.py",        599, "optional_extra", "pysnmp not installed"),
    ("test_snmp_scanner_contract.py",        632, "optional_extra", "pysnmp not installed"),
    ("test_snmp_scanner_contract.py",        674, "optional_extra", "pysnmp not installed"),

    # Phase 149 D-02/D-03: test-suite triage quarantines — see docs/test-triage-149.md
    ("test_notify_email.py",       79,  "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_emailpy-test_starttls_path_timeout_and_recipients"),
    ("test_notify_email.py",       142, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_emailpy-test_ssl_path_timeout_passed"),
    ("test_notify_email.py",       196, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_emailpy-test_no_login_when_smtp_user_none"),
    ("test_notify_webhook.py",     135, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_webhookpy-test_no_hmac_when_key_env_not_set"),
    ("test_notify_webhook.py",     164, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_webhookpy-test_hmac_header_present_when_key_set"),
    ("test_notify_webhook.py",     207, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_webhookpy-test_hmac_absent_when_key_env_empty"),
    ("test_notify_webhook.py",     237, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_webhookpy-test_body_omits_topology_keys"),
    ("test_notify_webhook.py",     271, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_webhookpy-test_non_2xx_raises_runtime_error"),
    ("test_ticketing_servicenow.py", 90,  "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_ticketing_servicenowpy-test_create_incident"),
    ("test_ticketing_servicenow.py", 133, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_ticketing_servicenowpy-test_dedup_then_work_notes"),
    ("test_ticketing_servicenow.py", 215, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_ticketing_servicenowpy-test_correlation_id_is_fingerprint"),
    ("test_ticketing_servicenow.py", 328, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_ticketing_servicenowpy-test_credentials_not_in_logs"),
    ("test_ticketing_servicenow.py", 456, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_ticketing_servicenowpy-test_create_issue_missing_sys_id_raises_runtime_error"),
    ("test_ticketing_servicenow.py", 490, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_ticketing_servicenowpy-test_create_issue_non_json_response_raises_runtime_error"),
    ("test_sensor_cmd.py",           497, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_push_posts_to_correct_url"),
    ("test_sensor_cmd.py",           588, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_push_retry_on_5xx"),
    ("test_sensor_cmd.py",           659, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_push_no_retry_on_4xx"),
    ("test_sensor_cmd.py",           722, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_push_connect_error_retries"),
    ("test_sensor_cmd.py",           791, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_push_409_treated_as_success"),
    ("test_sensor_cmd.py",           864, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_spool_on_connect_failure"),
    ("test_sensor_cmd.py",           939, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_spool_flush_delivers_and_unlinks"),
    ("test_sensor_cmd.py",           1046, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_spool_409_unlinks_file"),
    ("test_sensor_cmd.py",           1119, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_spool_filename_is_uuid_pattern"),

    # Phase 149 Plan 03: Cluster 2 (Playwright cross-test pollution) — see docs/test-triage-149.md
    ("test_reports_writer.py",       118, "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_reports_writerpy-test_json_export_preserves_description"),
    ("test_reports_writer.py",       147, "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_reports_writerpy-test_json_export_preserves_deprecation_phrase"),
    ("test_reports_writer.py",       175, "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_reports_writerpy-test_html_report_has_description_column"),
    ("test_reports_writer.py",       264, "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_reports_writerpy-test_docx_emitted_by_write_reports"),
    ("test_reports_writer.py",       290, "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_reports_writerpy-test_docx_none_on_fail_not_in_output_files"),
    ("test_report_injection_hardening.py", 161, "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_report_injection_hardeningpy-test_script_payload_in_cert_cn_is_escaped_in_html"),
    ("test_report_injection_hardening.py", 183, "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_report_injection_hardeningpy-test_javascript_url_in_finding_recommendation_stripped"),
    ("test_report_injection_hardening.py", 197, "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_report_injection_hardeningpy-test_db_stored_raw_payload_preserved"),
    ("test_report_injection_hardening.py", 239, "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_report_injection_hardeningpy-test_script_payload_in_cert_cn_is_escaped_in_pdf"),
    ("test_pdf_metadata_constants.py", 63, "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_pdf_metadata_constantspy-test_pdf_title_is_constant"),
    ("test_pdf_metadata_constants.py", 77, "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_pdf_metadata_constantspy-test_pdf_author_is_constant"),
    ("test_pdf_metadata_constants.py", 91, "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_pdf_metadata_constantspy-test_pdf_renders_with_locked_context"),
    ("test_writer.py",               26,  "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_writerpy-test_run_stats_ports_and_hosts_scanned"),
    ("test_pdf_export.py",           7,   "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_pdf_exportpy-test_pdf_export_endpoint"),

    # Phase 149 Plan 03: Cluster 6 (pip --dry-run extras-install flakiness) — see docs/test-triage-149.md
    # Phase 149 Plan 04: Cluster 7 (optional GCP extra) — see docs/test-triage-149.md
    ("test_gcs_reuse.py", 29, "optional_extra", "googleapiclient/google not installed"),
    ("test_gcs_reuse.py", 50, "optional_extra", "googleapiclient/google not installed"),

    ("test_install_all_excludes_impacket.py",     36, "pre_existing_triage_149", "TRIAGE-149: flaky (pip --dry-run subprocess contention under full-suite load, passes standalone); see docs/test-triage-149.md#test_install_all_excludes_impacketpy-test_install_all_excludes_impacket"),
    ("test_install_all_excludes_pysnmp.py",       36, "pre_existing_triage_149", "TRIAGE-149: flaky (pip --dry-run subprocess contention under full-suite load, passes standalone); see docs/test-triage-149.md#test_install_all_excludes_pysnmppy-test_install_all_excludes_pysnmp"),
    ("test_install_all_excludes_schemathesis.py", 44, "pre_existing_triage_149", "TRIAGE-149: flaky (pip --dry-run subprocess contention under full-suite load, passes standalone); see docs/test-triage-149.md#test_install_all_excludes_schemathesispy-test_install_all_excludes_schemathesis"),
    ("test_install_all_includes_notify.py",       36, "pre_existing_triage_149", "TRIAGE-149: flaky (pip --dry-run subprocess contention under full-suite load, passes standalone); see docs/test-triage-149.md#test_install_all_includes_notifypy-test_install_all_includes_notify"),
    ("test_install_all_includes_tickets.py",      30, "pre_existing_triage_149", "TRIAGE-149: flaky (pip --dry-run subprocess contention under full-suite load, passes standalone); see docs/test-triage-149.md#test_install_all_includes_ticketspy-test_install_all_includes_tickets"),
    ("test_snmp_scanner_contract.py",             380, "pre_existing_triage_149", "TRIAGE-149: flaky (pip --dry-run subprocess contention under full-suite load, passes standalone); see docs/test-triage-149.md#test_snmp_scanner_contractpy-test_install_all_excludes_pysnmp"),

    # Phase 149 Plan 05: Cluster 5 (sensor_id shape / AUDIT-08 regression) — see docs/test-triage-149.md
    ("test_auto_merge_trigger.py",          210, "pre_existing_triage_149", "TRIAGE-149: outdated-fixture (AUDIT-08 UUID-shape guard added after these fixtures; fixture IDs need updating to valid UUIDs); see docs/test-triage-149.md#test_auto_merge_triggerpy-test_all_sensors_in_triggers_merge"),
    ("test_auto_merge_trigger.py",          248, "pre_existing_triage_149", "TRIAGE-149: outdated-fixture (AUDIT-08 UUID-shape guard added after these fixtures; fixture IDs need updating to valid UUIDs); see docs/test-triage-149.md#test_auto_merge_triggerpy-test_auto_merge_disabled"),
    ("test_auto_merge_trigger.py",          275, "pre_existing_triage_149", "TRIAGE-149: outdated-fixture (AUDIT-08 UUID-shape guard added after these fixtures; fixture IDs need updating to valid UUIDs); see docs/test-triage-149.md#test_auto_merge_triggerpy-test_revoked_sensor_excluded"),
    ("test_auto_merge_trigger.py",          310, "pre_existing_triage_149", "TRIAGE-149: outdated-fixture (AUDIT-08 UUID-shape guard added after these fixtures; fixture IDs need updating to valid UUIDs); see docs/test-triage-149.md#test_auto_merge_triggerpy-test_mixed_token_sensor_is_required_for_all_in"),
    ("test_auto_merge_trigger.py",          363, "pre_existing_triage_149", "TRIAGE-149: outdated-fixture (AUDIT-08 UUID-shape guard added after these fixtures; fixture IDs need updating to valid UUIDs); see docs/test-triage-149.md#test_auto_merge_triggerpy-test_zero_token_sensor_not_counted_as_active"),
    ("test_auto_merge_trigger.py",          408, "pre_existing_triage_149", "TRIAGE-149: outdated-fixture (AUDIT-08 UUID-shape guard added after these fixtures; fixture IDs need updating to valid UUIDs); see docs/test-triage-149.md#test_auto_merge_triggerpy-test_merge_failure_isolated"),
    ("test_auto_merge_trigger.py",          462, "pre_existing_triage_149", "TRIAGE-149: outdated-fixture (AUDIT-08 UUID-shape guard added after these fixtures; fixture IDs need updating to valid UUIDs); see docs/test-triage-149.md#test_auto_merge_triggerpy-test_double_fire_harmless"),
    ("test_auto_merge_trigger.py",          514, "pre_existing_triage_149", "TRIAGE-149: outdated-fixture (AUDIT-08 UUID-shape guard added after these fixtures; fixture IDs need updating to valid UUIDs); see docs/test-triage-149.md#test_auto_merge_triggerpy-test_cadence_window_triggers"),
    ("test_sensor_push_id_revalidation.py", 158, "pre_existing_triage_149", "TRIAGE-149: shared in-memory SQLite cache pollution (file::memory:?cache=shared&uri=true is a single process-wide DB shared with other test files that write SensorPush rows; the 400/0-new-rows contract itself is correct); see docs/test-triage-149.md#test_sensor_push_id_revalidationpy-test_malformed_sensor_id_path_traversal_rejected"),
    ("test_sensor_push_id_revalidation.py", 206, "pre_existing_triage_149", "TRIAGE-149: shared in-memory SQLite cache pollution (file::memory:?cache=shared&uri=true is a single process-wide DB shared with other test files that write SensorPush rows; the 400/0-new-rows contract itself is correct); see docs/test-triage-149.md#test_sensor_push_id_revalidationpy-test_malformed_sensor_id_short_string_rejected"),

    # Phase 149 Plan 06: Cluster 9 Group A (scanner/detection-logic failures) — see docs/test-triage-149.md
    ("test_jwt_hardening.py",       31, "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (idp.example.com fails CR-03's validate_external_url() dns_failure check before httpx.get is reached); see docs/test-triage-149.md#jwt-hardening-dns-blocked"),
    ("test_jwt_hardening.py",       66, "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (idp.example.com fails CR-03's validate_external_url() dns_failure check before httpx.get is reached); see docs/test-triage-149.md#jwt-hardening-dns-blocked"),
    ("test_broker_scanner_rabbitmq.py", 200, "pre_existing_triage_149", "TRIAGE-149: stale test predates CR-06 allow_cleartext opt-in guard on _enrich_rabbitmq_mgmt() (default allow_cleartext=False short-circuits to {}); see docs/test-triage-149.md#broker-rabbitmq-cr06-optin"),
    ("test_broker_scanner_rabbitmq.py", 236, "pre_existing_triage_149", "TRIAGE-149: stale test predates CR-06 allow_cleartext opt-in guard on _enrich_rabbitmq_mgmt() (default allow_cleartext=False short-circuits to {}); see docs/test-triage-149.md#broker-rabbitmq-cr06-optin"),
    ("test_jwt_scanner.py",         44, "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (api.example.com fails CR-03's validate_external_url() dns_failure check); see docs/test-triage-149.md#jwt-scanner-dns-blocked"),
    ("test_jwt_scanner.py",         67, "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (api.example.com fails CR-03's validate_external_url() dns_failure check); see docs/test-triage-149.md#jwt-scanner-dns-blocked"),
    ("test_jwt_scanner.py",         89, "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (api.example.com fails CR-03's validate_external_url() dns_failure check); see docs/test-triage-149.md#jwt-scanner-dns-blocked"),
    ("test_jwt_scanner.py",        132, "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (api.example.com fails CR-03's validate_external_url() dns_failure check); see docs/test-triage-149.md#jwt-scanner-dns-blocked"),
    ("test_jwt_scanner.py",        213, "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (api.example.com fails CR-03's validate_external_url() dns_failure check); see docs/test-triage-149.md#jwt-scanner-dns-blocked"),
    ("test_jwt_scanner.py",        321, "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (h1/h2.example.com fail CR-03's validate_external_url() dns_failure check); see docs/test-triage-149.md#jwt-scanner-dns-blocked"),
    ("test_openapi_scanner.py",    249, "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (api.example.com fails validate_external_url()'s dns_failure check inside scan_openapi_spec's SSRF gate); see docs/test-triage-149.md#openapi-scanner-dns-blocked"),
    ("test_gap_closure.py",         48, "pre_existing_triage_149", "TRIAGE-149: stale fixture (_make_endpoint() SimpleNamespace lacks sensor_id/segment, AttributeError silently swallowed by _derive_findings()'s broad except); see docs/test-triage-149.md#gap-closure-stale-fixture"),
    ("test_gap_closure.py",         74, "pre_existing_triage_149", "TRIAGE-149: stale fixture (_make_endpoint() SimpleNamespace lacks sensor_id/segment, AttributeError silently swallowed by _derive_findings()'s broad except); see docs/test-triage-149.md#gap-closure-stale-fixture"),

    # Phase 149 Plan 07: Cluster 9 Group B (dashboard/API/DB-migration failures) — see docs/test-triage-149.md
    ("test_dashboard_scan_history.py", 188, "pre_existing_triage_149", "TRIAGE-149: '+' query-encoding test-construction bug (f-string embeds unescaped '+' UTC offset, decoded as space, corrupting the ISO timestamp before datetime.fromisoformat); see docs/test-triage-149.md#dashboard-compare-plus-encoding"),
    ("test_dashboard_scan_history.py", 234, "pre_existing_triage_149", "TRIAGE-149: genuine API-contract drift (format_error() now wraps detail in a '[QRK-<CODE>] ... Fix: ...' envelope; 400 status + self-compare rejection are still correct); see docs/test-triage-149.md#dashboard-compare-error-envelope"),
    ("test_dashboard_scan_history.py", 268, "pre_existing_triage_149", "TRIAGE-149: '+' query-encoding test-construction bug (same root cause as test_compare_schema); see docs/test-triage-149.md#dashboard-compare-plus-encoding"),
    ("test_dashboard_scan_history.py", 321, "pre_existing_triage_149", "TRIAGE-149: '+' query-encoding test-construction bug (same root cause as test_compare_schema); see docs/test-triage-149.md#dashboard-compare-plus-encoding"),
    ("test_dashboard_scan_history.py", 359, "pre_existing_triage_149", "TRIAGE-149: '+' query-encoding test-construction bug (same root cause as test_compare_schema); see docs/test-triage-149.md#dashboard-compare-plus-encoding"),
    ("test_dashboard_theme.py",         12, "pre_existing_triage_149", "TRIAGE-149: confirmed intentional Obsidian Pro rebrand (commit ac242d1, 2026-05-07) shifted --primary from electric-blue 210 100% 56% to teal 180 37% 47% (#4ba8a8); see docs/test-triage-149.md#dashboard-theme-obsidian-pro-rebrand"),
    ("test_dashboard_theme.py",         32, "pre_existing_triage_149", "TRIAGE-149: confirmed intentional Obsidian Pro rebrand (commit ac242d1, 2026-05-07) shifted --accent from electric-blue 210 100% 56% to teal 180 37% 47% (#4ba8a8); see docs/test-triage-149.md#dashboard-theme-obsidian-pro-rebrand"),
    ("test_route_coverage.py",          18, "pre_existing_triage_149", "TRIAGE-149: stale test inventory, not a real unprotected route — GET /api/config is deliberately unauthenticated (module docstring: 'no auth required (frontend needs this before login)'), mirrors /api/health, returns only the vertical name; NOT flagged SECURITY; see docs/test-triage-149.md#route-coverage-api-config-stale-inventory"),
    ("test_db_migrate_cli.py",          53, "pre_existing_triage_149", "TRIAGE-149: stale fixture — _create_legacy_schema() predates the sensor_tokens entry Phase 113 AUTH-02 added to _ADDITIVE_MIGRATIONS, causing NoSuchTableError: sensor_tokens; see docs/test-triage-149.md#db-migrate-sensor-tokens-stale-fixture"),
    ("test_db_migrate_cli.py",         114, "pre_existing_triage_149", "TRIAGE-149: same sensor_tokens stale-fixture cause as test_fresh_db_reports_every_column_added; see docs/test-triage-149.md#db-migrate-sensor-tokens-stale-fixture"),
    ("test_db_migrate_cli.py",         145, "pre_existing_triage_149", "TRIAGE-149: same sensor_tokens stale-fixture cause as test_fresh_db_reports_every_column_added; see docs/test-triage-149.md#db-migrate-sensor-tokens-stale-fixture"),
    ("test_init_db_idempotent.py",      40, "pre_existing_triage_149", "TRIAGE-149: naming-convention drift — _ensure_columns(engine, table, expected) (Phase 77 D-21) is a generic shared helper with a 3-arg signature, not a single-arg per-table _ensure_*(engine) helper; needs the same dir()-discovery exclusion as _ensure_parent_dir; see docs/test-triage-149.md#init-db-ensure-columns-signature-drift"),

    # Phase 149 Plan 08: Cluster 9 Group C (QRAMM subsystem failures) — see docs/test-triage-149.md
    ("test_qramm_evidence_bridge.py",  135, "pre_existing_triage_149", "TRIAGE-149: cross-test sys.modules pollution (test_findings_evaluator_dedupe.py::test_dedupe_via_risk_engine_shim_works imports quirk.engine.risk_engine before this file runs alphabetically in full-suite order), not a real QRAMM-12 import-graph violation; see docs/test-triage-149.md#qramm-evidence-bridge-risk-engine-sys-modules-pollution"),
    ("test_qramm_evidence_bridge.py",  213, "pre_existing_triage_149", "TRIAGE-149: genuine API-contract drift — POST .../score now 422s (DASHBOARD-011) when zero QRAMMAnswer rows have answer_value set, before the unconfirmed-exclusion scoring logic under test ever runs; see docs/test-triage-149.md#qramm-evidence-bridge-score-422-unconfirmed"),
    # NOTE: this marker is inline (pytest.param(marks=pytest.mark.xfail(...))), not a
    # function/class decorator, so tests/test_skip_registry.py's AST walker (which only
    # inspects FunctionDef/AsyncFunctionDef/ClassDef.decorator_list) does not detect it and
    # this entry is not required for the meta-gate to pass. Registered anyway for ledger
    # completeness and audit-trail consistency with the other 3 Group C entries.
    ("test_qramm_model_stale.py",       52, "pre_existing_triage_149", "TRIAGE-149: stale fixture — boundary date (2026-08-04) hardcoded against QRAMM_MODEL['last_verified']=='2026-05-05' at test-authoring time; last_verified has since been re-verified/bumped forward (currently 2026-08-11) by the CLAUDE.md 90-day staleness cadence, so the fixture date is now on the wrong side of the boundary; see docs/test-triage-149.md#qramm-model-stale-boundary-drift"),
    ("test_qramm_models.py",           230, "pre_existing_triage_149", "TRIAGE-149: stale assertion strategy — Phase 85-01 LAUNCH-04 replaced init_db()'s named per-migration call chain with a generic _ADDITIVE_MIGRATIONS loop, so the literal '_PHASE46_COLUMNS' no longer appears in init_db's function source text; the actual ordering invariant (Phase 46 columns before _ensure_qramm_tables) is still upheld in _ADDITIVE_MIGRATIONS' declared order; see docs/test-triage-149.md#qramm-models-init-db-phase46-ordering-stale-grep"),

    # Phase 149 Plan 09: Cluster 9 Group D1 (CLI/compliance/posture failures, first half) — see docs/test-triage-149.md
    ("test_cbom_schema_validation.py",  77, "pre_existing_triage_149", "TRIAGE-149: genuine chaos-lab profile drift — docker-compose.yml declares an 'otics' profile (Phase 141-07) that tests/_cbom_profiles.py's PROFILE_ENDPOINTS never gained a synthesizer for; flagged for Phase 150 lab.sh/expected_results follow-up; see docs/test-triage-149.md#cbom-schema-otics-profile-drift"),
    ("test_cli_correctness.py",        179, "pre_existing_triage_149", "TRIAGE-149: stale 'quirk scan' references in historical docs (docs/UAT-SERIES.md, docs/chaos-lab.md, docs/release-notes/4.6.0.md) — none are live CLI documentation; see docs/test-triage-149.md#cli-correctness-quirk-scan-doc-drift"),
    ("test_cli_init.py",               126, "pre_existing_triage_149", "TRIAGE-149: quirk init's CR-01/D-13 path-traversal guard rejects pytest tmp_path (resolves outside repo CWD), so config.yaml is never created; test predates the CR-01 guard; see docs/test-triage-149.md#cli-init-cr01-tmp-path-guard"),
    ("test_cli_init.py",               153, "pre_existing_triage_149", "TRIAGE-149: same CR-01/D-13 path-traversal guard as test_init_creates_config — the first quirk init call never creates config.yaml, so os.path.getmtime raises before the overwrite-guard logic under test runs; see docs/test-triage-149.md#cli-init-cr01-tmp-path-guard"),
    ("test_compliance_title_join.py",   20, "pre_existing_triage_149", "TRIAGE-149: genuine coverage gap — 3 Phase 95 codesign finding titles (findings_evaluator.py:1026/1045/1080) were never added to COMPLIANCE_MAP or UNMAPPED_TITLES; see docs/test-triage-149.md#compliance-title-join-codesign-gap"),

    # Phase 149 Plan 09: Cluster 9 Group D1 (email/errors/install/posture failures, second half) — see docs/test-triage-149.md
    ("test_email_run_scan_wiring.py",   84, "pre_existing_triage_149", "TRIAGE-149: Logger.info's signature was intentionally widened to (msg, *args) in commit 01411acc (89-02 LAB-06, stdlib-compatibility fix); test enforces the pre-89-02 single-arg signature; see docs/test-triage-149.md#email-run-scan-logger-signature-widened"),
    ("test_install_errors.py",          90, "pre_existing_triage_149", "TRIAGE-149: environment-dependent — this sandbox has no uvicorn installed, so serve() emits QRK-INSTALL-002 before reaching the port-bind check that would surface QRK-INSTALL-004; see docs/test-triage-149.md#install-errors-port-conflict-missing-uvicorn"),
    ("test_install_errors.py",         126, "pre_existing_triage_149", "TRIAGE-149: stale lazy-import assumption — server.py's uvicorn import lives inside serve(), not module scope, so importing the module alone (never calling serve()) prints nothing; see docs/test-triage-149.md#install-errors-missing-uvicorn-stale-lazy-import"),

    # Phase 149 Plan 10: Cluster 9 Group D2 (docs-presence/security-gate/windows-smoke, second half of Group D) — see docs/test-triage-149.md
    ("test_phase135_docs_presence.py",  74, "pre_existing_triage_149", "TRIAGE-149: stale version pin — README.md has advanced to v5.11.0 ('## What's New in v5.10'); no longer contains literal 'v5.8.0' / \"what's new in v5.8\" substrings; all other required Phase 135 content still present; see docs/test-triage-149.md#phase135-docs-stale-version-pin"),
    ("test_phase136_docs_presence.py", 144, "pre_existing_triage_149", "TRIAGE-149: stale detection list, not a real leak — Phase 139 legitimately added its own §9.1.1 SNMPv3 Auth+Priv Scanning subsection to operators-guide.md §9 when it shipped SNMPv3 support, a properly-scoped later addition, not scope creep from Phase 137's admin guide; see docs/test-triage-149.md#phase136-docs-snmpv3-legitimate-addition"),
    ("test_safe_filter_audit.py",      137, "pre_existing_triage_149", "TRIAGE-149: stale-detection-logic, not a real unsanitized-usage finding — report.html.j2:389 narrative_lead is sourced from a small hardcoded static-prose dict (_NARRATIVE_LEADS), never scanner/user input; report.html.j2:508 hardware_section is pre-HTML-escaped in Python (render_hardware_section() calls _html.escape() on every dynamic field) before being marked safe, so sanitization happens outside the Jinja filter chain this gate inspects; see docs/test-triage-149.md#safe-filter-audit-two-legitimate-safe-usages"),
    ("test_scan_error_gate.py",        154, "pre_existing_triage_149", "TRIAGE-149: stale-detection-logic, not a real safe_str bypass — kerberos_scanner.py:312 writes a ternary (safe_str(tcp_error) if tcp_error is not None else None) whose branches are both individually safe, but _classify_rhs() does not recognize ast.IfExp as a SAFE shape at all; see docs/test-triage-149.md#scan-error-gate-kerberos-ternary-ifexp-gap"),

    # Phase 149 Plan 11: final reconciliation — fresh full-suite run surfaced 11 orphaned
    # failures not present in Plans 01-10's sandboxes (different extras installed: impacket/
    # sslyze/pysnmp present here, googleapiclient absent). 2 fixed in place (sslyze __version__
    # submodule shape, impacket MethodData rename); 9 newly quarantined below. See
    # docs/test-triage-149.md's Reconciliation section.
    ("test_posture_scorefix125.py",      39, "pre_existing_triage_149", "TRIAGE-149 (Plan 11): googleapiclient/google not installed in this sandbox — same optional_extra gap class as Cluster 7's test_gcs_reuse.py; Plan 09 found this passing because googleapiclient happened to be installed in that plan's sandbox, so gcp_connector.py's _GcpHttpError isinstance-gated 403 handling was reachable there. POSTURE-02's fix itself is not regressed. See docs/test-triage-149.md#reconciliation-gcp-googleapiclient-extras-gap"),
    ("test_posture_scorefix125.py",      62, "pre_existing_triage_149", "TRIAGE-149 (Plan 11): same googleapiclient/google optional_extra gap as test_gcp_kms_403_emits_scan_error; see docs/test-triage-149.md#reconciliation-gcp-googleapiclient-extras-gap"),
    ("test_qramm_staleness.py",          90, "pre_existing_triage_149", "TRIAGE-149 (Plan 11): intermittent SIGSEGV (exit=-11) reproducible under full-suite (`pytest -q -m \"\"`) load in this subprocess.run() spawn — confirmed via 'Fatal Python error: Segmentation fault' crash dumps inside CPython's fork/exec path at this exact call site across repeat full-suite runs (never in isolation). Plan 08 flagged this pair as a HIGH-PRIORITY re-verification item if it resurfaced; it has, and the trigger is now identified as systemic macOS fork()-under-load instability, shared with 4 other subprocess-spawning tests. See docs/test-triage-149.md#reconciliation-macos-fork-sigsegv-cluster"),
    ("test_qramm_staleness.py",         120, "pre_existing_triage_149", "TRIAGE-149 (Plan 11): same macOS fork()-under-load SIGSEGV as test_qramm_status_cli_smoke_fresh; see docs/test-triage-149.md#reconciliation-macos-fork-sigsegv-cluster"),
    ("test_sensor_windows_smoke.py",    209, "pre_existing_triage_149", "TRIAGE-149 (Plan 11): same macOS fork()-under-load SIGSEGV cluster — this run's crash dump showed the segfault inside subprocess spawning itself (subprocess.py _execute_child via _run_child_script), killing the pytest runner process. Plan 10 flagged this test as a second independent HIGH-PRIORITY SIGSEGV item; reconciliation now attributes both this and Plan 08's QRAMM pair to the same systemic cause, not two independent subsystem-specific crashes. See docs/test-triage-149.md#reconciliation-macos-fork-sigsegv-cluster"),
    ("test_vault_connector.py",         299, "pre_existing_triage_149", "TRIAGE-149 (Plan 11): same macOS fork()-under-load SIGSEGV cluster — the `openssl req -new -x509 -sha1` subprocess spawned by _make_test_pem_rsa crashes with returncode=-11. Supersedes Plan 06's 'OpenSSL SHA1 cert generation' environment-dependent hypothesis: SHA1 cert generation itself works fine (this test passes standalone); the actual trigger is fork() instability under full-suite load. See docs/test-triage-149.md#reconciliation-macos-fork-sigsegv-cluster"),
    ("test_version.py",                  59, "pre_existing_triage_149", "TRIAGE-149 (Plan 11): same macOS fork()-under-load SIGSEGV cluster as test_qramm_staleness.py — 'Fatal Python error: Segmentation fault' crash dump at this exact subprocess.run() call site. Not a CLI --version regression (Cluster 3's pip install -e . fix remains correct and necessary, just not sufficient to prevent this separate, load-dependent crash). See docs/test-triage-149.md#reconciliation-macos-fork-sigsegv-cluster"),

    # Phase 149 code review (CR-01): Plan 11's reconciliation sweep missed one orphaned
    # failure of the same shared-cache SQLite class it already diagnosed for Cluster 5 —
    # test_dashboard_trends.py was never touched by any Plan 01-11 and has no ledger row,
    # but full-suite runs can intermittently reproduce it (timing-dependent, not always
    # reproducible; 2 clean local full-suite runs post-fix, reviewer reproduced it twice).
    ("test_dashboard_trends.py",        347, "pre_existing_triage_149", "TRIAGE-149 (code review CR-01): shared in-memory SQLite cache pollution (file::memory:?cache=shared&uri=true is a single process-wide DB shared with other test files); an earlier test's leftover session row can leak into this empty-DB assertion depending on full-suite timing, same root cause as test_sensor_push_id_revalidation.py. Missed by Plan 11's reconciliation sweep because it doesn't always reproduce. See docs/test-triage-149.md#reconciliation-cr-01-test_dashboard_trendspy-orphaned-flake"),

    # ------------------------------------------------------------------
    # Phase 150 D-09/D-10 CI-parity gap closure (Plan 06): `.[all]` deliberately
    # excludes the `hw` (bacpypes3/pymodbus/pysnmp), `identity` (impacket) and
    # `api` (schemathesis/openapi-spec-validator) extras groups. These tests now
    # take a documented per-test skip when the corresponding extra is absent,
    # instead of hard-crashing with AttributeError/ModuleNotFoundError. Kept in
    # its own "ci_extras_gap" category, distinct from the pre-existing
    # "optional_extra" rows above, so Phase 150's CI-parity closure work stays
    # independently greppable. See 150-CONTEXT.md D-09/D-10/D-11.
    # ------------------------------------------------------------------
    ("test_bacnet_scanner.py",  78,  "ci_extras_gap", "hw extra absent from .[all]; bacpypes3 not installed"),
    ("test_bacnet_scanner.py",  108, "ci_extras_gap", "hw extra absent from .[all]; bacpypes3 not installed"),
    ("test_modbus_scanner.py",  64,  "ci_extras_gap", "hw extra absent from .[all]; pymodbus not installed"),
    ("test_modbus_scanner.py",  103, "ci_extras_gap", "hw extra absent from .[all]; pymodbus not installed"),
    ("test_modbus_scanner.py",  136, "ci_extras_gap", "hw extra absent from .[all]; pymodbus not installed"),
    ("test_snmp_scanner_contract.py", 711, "ci_extras_gap", "hw extra absent from .[all]; pysnmp not installed"),
    ("test_identity_surface.py", 484, "ci_extras_gap", "identity extra absent from .[all]; impacket not installed"),

    # Phase 150 D-09/D-10 CI-parity gap closure (Plan 06, Task 2): `api` extras
    # group (schemathesis, openapi-spec-validator) absent from .[all].
    ("test_rest_fuzzer_cascade.py",        105, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_cascade.py",        162, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_cascade.py",        229, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_dedup.py",          108, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_dedup.py",          168, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_dedup.py",          225, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_pinned_session.py",  63, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py",          97, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py",         136, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py",         214, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py",         272, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py",         322, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py",         374, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py",         428, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py",         649, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py",         708, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py",         786, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py",         825, "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_openapi_scanner.py",             90, "ci_extras_gap", "api extra absent from .[all]; openapi-spec-validator not installed"),
    ("test_openapi_scanner.py",            122, "ci_extras_gap", "api extra absent from .[all]; openapi-spec-validator not installed"),
    ("test_openapi_scanner.py",            143, "ci_extras_gap", "api extra absent from .[all]; openapi-spec-validator not installed"),
    ("test_openapi_scanner.py",            164, "ci_extras_gap", "api extra absent from .[all]; openapi-spec-validator not installed"),
    ("test_openapi_scanner.py",            189, "ci_extras_gap", "api extra absent from .[all]; openapi-spec-validator not installed"),
    ("test_openapi_scanner.py",            232, "ci_extras_gap", "api extra absent from .[all]; openapi-spec-validator not installed"),
]
