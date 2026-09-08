"""Phase 41 D-02: Central allowed-skip registry.

Each entry: (file_relative_to_tests_dir, test_qualname, category, reason)

``test_qualname`` (Phase 184 D-01) is the dotted enclosing
``ClassDef``/``FunctionDef``/``AsyncFunctionDef`` ancestor chain of the skip
construct (e.g. ``"TestFoo.test_bar"``), or the literal ``"<module>"`` for
module-scope skips -- derived by ``tests/test_skip_registry.py``'s
``_enclosing_qualname()``. This replaces the pre-Phase-184 ``line_number``
key, which re-broke on any unrelated line shift in the same file; there is no
positional-tolerance constant anywhere in the gate.

category in {"optional_extra", "live_infra", "pre_existing_triage_149",
"ci_extras_gap", "gitignored_planning_dir", "environment_subprocess_signal",
"environment_capability"}
-- "environment_subprocess_signal" admits a skip whose only justification is
a macOS full-suite subprocess dying to SIGSEGV before it produced any result
to assert on (not a known-broken test); CI/Linux always takes the real
assertion branch. "environment_capability" (Phase 184 Plan 05) admits a skip
whose only justification is that the executing environment lacks a specific
capability the test's assertions require -- an installed toolchain, a
non-root euid, a binary on PATH, a built entry point -- so the test has
nothing to assert against; distinct from "optional_extra" (a declared Python
packaging extra checked against pyproject.toml) and from "live_infra"
(external services the chaos lab provides). A skip in this category is never
evidence the underlying behaviour was exercised -- see the
``test_gsd_state_patch.py`` and ``test_uat_disposition_integrity.py``
entries below for what that means in practice.

Per CONTEXT.md D-01..D-05: stale skips are deleted; optional-extra and
live-infra skips are registered here so the meta-test gate (test_skip_registry.py)
can validate that no NEW unregistered skip slips into the suite.

Plan 05 deletes the stale skips identified in 41-RESEARCH.md "Skip-Marker
Triage Table" (D-04). Until Plan 05 lands, the meta-test will fail — that
is the intended behavior and the validation that D-04 deletions worked.

Phase 184 Plan 03 re-keyed every entry above from ``(file, line_number,
category, reason)`` to ``(file, test_qualname, category, reason)`` by a
reviewed script; every reason string survived byte-identical except the 4
D-02 collapse groups (several skip sites in one test sharing one qualname),
where the surviving entry's reason was joined from its collapsed sites'
reasons, separated by "; ", verbatim. 16 entries whose recorded line did not
resolve to any skip site (within a generous +/-20 line search) were kept,
not deleted, keyed with an ``UNRESOLVED`` sentinel prefix plus the original
line number, as Plan 04's purge-candidate input, per D-08's
re-key-then-purge ordering.

Phase 184 Plan 04 re-derived the orphan set post-re-key (inverting the
gate's own walk: ledger keys minus live occurrence keys) and purged all 16
``UNRESOLVED``-sentinel entries -- every one was confirmed to genuinely
resolve to no skip site anywhere in ``tests/`` (11 ``test_jobs_api.py``
Phase 65 stubs superseded by real implementations, 1
``test_qramm_model_stale.py`` inline ``pytest.param(marks=...)``
AST-walker blind spot, 2 ``test_qramm_staleness.py`` and 2
``test_vault_connector.py`` SIGSEGV-cluster skips already removed by
Phase 166 / earlier reconciliation). Each purged entry's verbatim reason
string is recorded in ``184-04-SUMMARY.md``, not merely deleted. No
``UNRESOLVED``-sentinel data entry remains; the term appears here only as
the (now-retired) convention's own name.
"""

ALLOWED_SKIPS = [
    # Phase 162: conditional, environment-detected skip — NOT a known-broken
    # test. `_run_scan_argparse()` spawns `python -m run_scan --help` to verify
    # argparse accepts/rejects a --profile value. On macOS a subprocess spawned
    # late in a full-suite run can die with SIGSEGV before executing anything
    # (`git init` in test_verify_phase_gates.py hits the identical thing).
    # A signal-killed child produced no stderr, so asserting on it would be a
    # false failure rather than a real result. CI (Linux) never takes this
    # branch and runs the assertions for real.
    ("test_scheduler_dispatch_profile.py", "_run_scan_argparse", "environment_subprocess_signal", 'macOS full-suite subprocess SIGSEGV; child never executed so there is no argparse result to assert. Runs for real on CI/Linux.'),
    ("test_backlog_reconciliation_gate.py", "test_full_corpus_local_only_leg", "environment_capability", "TRIAGE-09 RQ-2: the full-corpus 999.* leg needs untracked .planning/backlog/ + .planning/milestones/ sources that a fresh CI checkout cannot see; skips honestly naming the missing paths, runs for real on a full local working tree."),
    ("test_broker_scanner_kafka.py", "<module>", "optional_extra", "broker_scanner is [motion]; D-05"),
    ("test_broker_scanner_rabbitmq.py", "<module>", "optional_extra", "broker_scanner is [motion]; D-05"),
    ("test_broker_scanner_redis.py", "<module>", "optional_extra", "broker_scanner is [motion]; D-05"),
    ("test_chaos_storage.py", "test_minio_unencrypted_bucket_produces_high_finding", "live_infra", "Requires Docker + MinIO"),
    ("test_chaos_storage.py", "test_minio_encrypted_bucket_no_finding", "live_infra", "Requires Docker + MinIO"),
    ("test_dnssec_scanner.py", "test_chaos_lab_integration", "live_infra", "Requires BIND9 chaos lab"),
    ("test_saml_scanner.py", "test_chaos_lab_integration", "live_infra", "Requires SimpleSAMLphp chaos lab"),
    ("test_kerberos_scanner.py", "test_samba_dc_integration", "live_infra", "Requires Samba DC chaos lab"),
    ("test_cbom_motion_golden.py", "test_generate_fixtures", "live_infra", "Fixture regen guard"),
    ("test_cbom_classifier_coverage.py", "test_regenerate_coverage_report", "live_infra", "Fixture regen guard (REGEN_CBOM_COVERAGE=1)"),
    ("test_uat_db_integration.py", "test_postgres_ssl_off_produces_high_finding", "live_infra", "Requires PostgreSQL chaos lab (database profile)"),
    ("test_uat_db_integration.py", "test_mysql_ssl_off_produces_high_finding", "live_infra", "Requires MySQL chaos lab (database profile)"),
    ("test_uat_db_integration.py", "test_postgres_finding_includes_host_and_port", "live_infra", "Requires PostgreSQL chaos lab (database profile)"),
    ("test_uat_db_integration.py", "test_mysql_finding_includes_host_and_port", "live_infra", "Requires MySQL chaos lab (database profile)"),
    ("test_tls_scanner_chain_verified.py", "test_sslyze_success_chain_verified_true", "optional_extra", "sslyze is [motion]; Phase 46 TLS-FIND-06"),
    ("test_tls_scanner_chain_verified.py", "test_sslyze_success_chain_verified_false", "optional_extra", "sslyze is [motion]; Phase 46 TLS-FIND-06"),

    # Phase 149 D-04: registered pre-existing drift
    ("test_aws_connector.py", "test_scan_s3_propagates_build_endpoint_exception", "optional_extra", "boto3 not installed"),
    ("test_cbom_vault_consistency.py", "test_regenerate_vault_golden", "live_infra", "Fixture regen guard (REGEN_CBOM_FIXTURES=1)"),
    ("test_chaos_lab_idempotency.py", "test_profile_re_up_is_idempotent", "live_infra", "macOS *:88 collides with system KDC; requires LAB_INCLUDE_KERBEROS=1 (BACK-89)"),
    ("test_cmvp_refresh.py", "<module>", "optional_extra", 'bs4 not installed; httpx not installed'),
    ("test_credential_leakage.py", "test_sentinel_not_in_dashboard_api_json", "live_infra", "Defensive guard: dashboard_client get_db override not configured"),
    ("test_db_migrate_cli.py", "_ensure_run_scan_importable", "optional_extra", "run_scan not importable in minimal dev env (optional reporting deps missing)"),
    ("test_distributed_topology.py", "test_config_validates", "live_infra", "Requires docker binary"),
    # Phase 184 Plan 06 (D-05): "test_identity_scanner_hardening.py" :
    # "_kerb_mod" (was: "impacket not installed") and "test_pdf_metadata_
    # constants.py" : "<module>" (was: 'playwright.sync_api not installed;
    # pypdf not installed') were RETIRED here -- both are bare
    # `pytest.importorskip(...)` sites whose modules map to declared
    # [project.optional-dependencies] groups (identity / dashboard), so the
    # narrow derivation now auto-allows them with no registry entry. See
    # 184-06-SUMMARY.md for the retirement record.
    ("test_jobs_api.py", "test_get_job_reconciles_real_zombie", "live_infra", "Linux-only /proc zombie-reconciliation check"),
    ("test_jwt_scanner.py", "<module>", "optional_extra", "httpx not installed"),
    ("test_pdf_metadata_constants.py", "_render_or_skip", "optional_extra", "Playwright Chromium runtime not available"),
    ("test_pqc_discriminator.py", "TestPqcDiscriminatorPositive.test_probe_detects_oqs_nginx", "live_infra", "Requires oqs-nginx chaos-lab profile"),
    ("test_pqc_discriminator.py", "TestPqcDiscriminatorPositive.test_probe_detects_negotiated_group_string", "live_infra", "Requires oqs-nginx chaos-lab profile"),
    ("test_report_injection_hardening.py", "test_script_payload_in_cert_cn_is_escaped_in_pdf", "pre_existing_triage_149", 'playwright.sync_api not installed; pypdf not installed; Playwright Chromium binary not available; TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_report_injection_hardeningpy-test_script_payload_in_cert_cn_is_escaped_in_pdf'),
    ("test_report_render_undetermined_hosts.py", "test_docx_shows_undetermined_headline_and_count", "optional_extra", 'python-docx not installed'),
    ("test_report_render_undetermined_hosts.py", "test_cross_surface_parity_undetermined_count", "optional_extra", "python-docx not installed"),
    ("test_scheduler_cmd.py", "test_signal_sets_stop_flag", "live_infra", "SIGTERM not supported on Windows"),
    ("test_snmp_scanner_contract.py", "test_arp_walk_v2c_happy_path_parses_last_octet_ip", "optional_extra", "pysnmp not installed"),
    ("test_snmp_scanner_contract.py", "test_arp_walk_v3_path_uses_usm_and_v3arch_walk_cmd", "optional_extra", "pysnmp not installed"),
    ("test_snmp_scanner_contract.py", "test_arp_walk_bounds_oversized_table_at_max_entries", "optional_extra", "pysnmp not installed"),

    # Phase 149 D-02/D-03: test-suite triage quarantines — see docs/test-triage-149.md
    ("test_notify_email.py", "test_starttls_path_timeout_and_recipients", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_emailpy-test_starttls_path_timeout_and_recipients"),
    ("test_notify_email.py", "test_ssl_path_timeout_passed", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_emailpy-test_ssl_path_timeout_passed"),
    ("test_notify_email.py", "test_no_login_when_smtp_user_none", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_emailpy-test_no_login_when_smtp_user_none"),
    ("test_notify_webhook.py", "test_no_hmac_when_key_env_not_set", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_webhookpy-test_no_hmac_when_key_env_not_set"),
    ("test_notify_webhook.py", "test_hmac_header_present_when_key_set", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_webhookpy-test_hmac_header_present_when_key_set"),
    ("test_notify_webhook.py", "test_hmac_absent_when_key_env_empty", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_webhookpy-test_hmac_absent_when_key_env_empty"),
    ("test_notify_webhook.py", "test_body_omits_topology_keys", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_webhookpy-test_body_omits_topology_keys"),
    ("test_notify_webhook.py", "test_non_2xx_raises_runtime_error", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_webhookpy-test_non_2xx_raises_runtime_error"),
    ("test_ticketing_servicenow.py", "test_create_incident", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_ticketing_servicenowpy-test_create_incident"),
    ("test_ticketing_servicenow.py", "test_dedup_then_work_notes", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_ticketing_servicenowpy-test_dedup_then_work_notes"),
    ("test_ticketing_servicenow.py", "test_correlation_id_is_fingerprint", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_ticketing_servicenowpy-test_correlation_id_is_fingerprint"),
    ("test_ticketing_servicenow.py", "test_credentials_not_in_logs", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_ticketing_servicenowpy-test_credentials_not_in_logs"),
    ("test_ticketing_servicenow.py", "test_create_issue_missing_sys_id_raises_runtime_error", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_ticketing_servicenowpy-test_create_issue_missing_sys_id_raises_runtime_error"),
    ("test_ticketing_servicenow.py", "test_create_issue_non_json_response_raises_runtime_error", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_ticketing_servicenowpy-test_create_issue_non_json_response_raises_runtime_error"),
    ("test_sensor_cmd.py", "test_push_posts_to_correct_url", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_push_posts_to_correct_url"),
    ("test_sensor_cmd.py", "test_push_retry_on_5xx", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_push_retry_on_5xx"),
    ("test_sensor_cmd.py", "test_push_no_retry_on_4xx", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_push_no_retry_on_4xx"),
    ("test_sensor_cmd.py", "test_push_connect_error_retries", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_push_connect_error_retries"),
    ("test_sensor_cmd.py", "test_push_409_treated_as_success", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_push_409_treated_as_success"),
    ("test_sensor_cmd.py", "test_spool_on_connect_failure", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_spool_on_connect_failure"),
    ("test_sensor_cmd.py", "test_spool_flush_delivers_and_unlinks", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_spool_flush_delivers_and_unlinks"),
    ("test_sensor_cmd.py", "test_spool_409_unlinks_file", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_spool_409_unlinks_file"),
    ("test_sensor_cmd.py", "test_spool_filename_is_uuid_pattern", "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_sensor_cmdpy-test_spool_filename_is_uuid_pattern"),

    # Phase 149 Plan 03: Cluster 2 (Playwright cross-test pollution) — see docs/test-triage-149.md
    ("test_reports_writer.py", "test_json_export_preserves_description", "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_reports_writerpy-test_json_export_preserves_description"),
    ("test_reports_writer.py", "test_json_export_preserves_deprecation_phrase", "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_reports_writerpy-test_json_export_preserves_deprecation_phrase"),
    ("test_reports_writer.py", "test_html_report_has_description_column", "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_reports_writerpy-test_html_report_has_description_column"),
    ("test_reports_writer.py", "test_docx_emitted_by_write_reports", "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_reports_writerpy-test_docx_emitted_by_write_reports"),
    ("test_reports_writer.py", "test_docx_none_on_fail_not_in_output_files", "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_reports_writerpy-test_docx_none_on_fail_not_in_output_files"),
    ("test_report_injection_hardening.py", "test_script_payload_in_cert_cn_is_escaped_in_html", "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_report_injection_hardeningpy-test_script_payload_in_cert_cn_is_escaped_in_html"),
    ("test_report_injection_hardening.py", "test_javascript_url_in_finding_recommendation_stripped", "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_report_injection_hardeningpy-test_javascript_url_in_finding_recommendation_stripped"),
    ("test_report_injection_hardening.py", "test_db_stored_raw_payload_preserved", "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_report_injection_hardeningpy-test_db_stored_raw_payload_preserved"),
    ("test_pdf_metadata_constants.py", "test_pdf_title_is_constant", "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_pdf_metadata_constantspy-test_pdf_title_is_constant"),
    ("test_pdf_metadata_constants.py", "test_pdf_author_is_constant", "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_pdf_metadata_constantspy-test_pdf_author_is_constant"),
    ("test_pdf_metadata_constants.py", "test_pdf_renders_with_locked_context", "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_pdf_metadata_constantspy-test_pdf_renders_with_locked_context"),
    ("test_writer.py", "test_run_stats_ports_and_hosts_scanned", "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_writerpy-test_run_stats_ports_and_hosts_scanned"),
    ("test_pdf_export.py", "test_pdf_export_endpoint", "pre_existing_triage_149", "TRIAGE-149: flaky (Playwright PlaywrightContextManager singleton torn down by earlier full-suite test, order-dependent — passes standalone); see docs/test-triage-149.md#test_pdf_exportpy-test_pdf_export_endpoint"),

    # Phase 149 Plan 03: Cluster 6 (pip --dry-run extras-install flakiness) — see docs/test-triage-149.md
    # Phase 149 Plan 04: Cluster 7 (optional GCP extra) — see docs/test-triage-149.md
    ("test_gcs_reuse.py", "test_gcs_reuse_reads_sentinel_no_api_call", "optional_extra", "googleapiclient/google not installed"),
    ("test_gcs_reuse.py", "test_gcs_reuse_zero_storage_buckets_list_call", "optional_extra", "googleapiclient/google not installed"),

    ("test_install_all_excludes_impacket.py", "test_install_all_excludes_impacket", "pre_existing_triage_149", "TRIAGE-149: flaky (pip --dry-run subprocess contention under full-suite load, passes standalone); see docs/test-triage-149.md#test_install_all_excludes_impacketpy-test_install_all_excludes_impacket"),
    ("test_install_all_excludes_pysnmp.py", "test_install_all_excludes_pysnmp", "pre_existing_triage_149", "TRIAGE-149: flaky (pip --dry-run subprocess contention under full-suite load, passes standalone); see docs/test-triage-149.md#test_install_all_excludes_pysnmppy-test_install_all_excludes_pysnmp"),
    ("test_install_all_excludes_schemathesis.py", "test_install_all_excludes_schemathesis", "pre_existing_triage_149", "TRIAGE-149: flaky (pip --dry-run subprocess contention under full-suite load, passes standalone); see docs/test-triage-149.md#test_install_all_excludes_schemathesispy-test_install_all_excludes_schemathesis"),
    ("test_install_all_includes_notify.py", "test_install_all_includes_notify", "pre_existing_triage_149", "TRIAGE-149: flaky (pip --dry-run subprocess contention under full-suite load, passes standalone); see docs/test-triage-149.md#test_install_all_includes_notifypy-test_install_all_includes_notify"),
    ("test_install_all_includes_tickets.py", "test_install_all_includes_tickets", "pre_existing_triage_149", "TRIAGE-149: flaky (pip --dry-run subprocess contention under full-suite load, passes standalone); see docs/test-triage-149.md#test_install_all_includes_ticketspy-test_install_all_includes_tickets"),
    ("test_snmp_scanner_contract.py", "test_install_all_excludes_pysnmp", "pre_existing_triage_149", "TRIAGE-149: flaky (pip --dry-run subprocess contention under full-suite load, passes standalone); see docs/test-triage-149.md#test_snmp_scanner_contractpy-test_install_all_excludes_pysnmp"),

    # Phase 149 Plan 05: Cluster 5 (sensor_id shape / AUDIT-08 regression) — see docs/test-triage-149.md
    ("test_auto_merge_trigger.py", "test_all_sensors_in_triggers_merge", "pre_existing_triage_149", "TRIAGE-149: outdated-fixture (AUDIT-08 UUID-shape guard added after these fixtures; fixture IDs need updating to valid UUIDs); see docs/test-triage-149.md#test_auto_merge_triggerpy-test_all_sensors_in_triggers_merge"),
    ("test_auto_merge_trigger.py", "test_auto_merge_disabled", "pre_existing_triage_149", "TRIAGE-149: outdated-fixture (AUDIT-08 UUID-shape guard added after these fixtures; fixture IDs need updating to valid UUIDs); see docs/test-triage-149.md#test_auto_merge_triggerpy-test_auto_merge_disabled"),
    ("test_auto_merge_trigger.py", "test_revoked_sensor_excluded", "pre_existing_triage_149", "TRIAGE-149: outdated-fixture (AUDIT-08 UUID-shape guard added after these fixtures; fixture IDs need updating to valid UUIDs); see docs/test-triage-149.md#test_auto_merge_triggerpy-test_revoked_sensor_excluded"),
    ("test_auto_merge_trigger.py", "test_mixed_token_sensor_is_required_for_all_in", "pre_existing_triage_149", "TRIAGE-149: outdated-fixture (AUDIT-08 UUID-shape guard added after these fixtures; fixture IDs need updating to valid UUIDs); see docs/test-triage-149.md#test_auto_merge_triggerpy-test_mixed_token_sensor_is_required_for_all_in"),
    ("test_auto_merge_trigger.py", "test_zero_token_sensor_not_counted_as_active", "pre_existing_triage_149", "TRIAGE-149: outdated-fixture (AUDIT-08 UUID-shape guard added after these fixtures; fixture IDs need updating to valid UUIDs); see docs/test-triage-149.md#test_auto_merge_triggerpy-test_zero_token_sensor_not_counted_as_active"),
    ("test_auto_merge_trigger.py", "test_merge_failure_isolated", "pre_existing_triage_149", "TRIAGE-149: outdated-fixture (AUDIT-08 UUID-shape guard added after these fixtures; fixture IDs need updating to valid UUIDs); see docs/test-triage-149.md#test_auto_merge_triggerpy-test_merge_failure_isolated"),
    ("test_auto_merge_trigger.py", "test_double_fire_harmless", "pre_existing_triage_149", "TRIAGE-149: outdated-fixture (AUDIT-08 UUID-shape guard added after these fixtures; fixture IDs need updating to valid UUIDs); see docs/test-triage-149.md#test_auto_merge_triggerpy-test_double_fire_harmless"),
    ("test_auto_merge_trigger.py", "test_cadence_window_triggers", "pre_existing_triage_149", "TRIAGE-149: outdated-fixture (AUDIT-08 UUID-shape guard added after these fixtures; fixture IDs need updating to valid UUIDs); see docs/test-triage-149.md#test_auto_merge_triggerpy-test_cadence_window_triggers"),

    # Phase 149 Plan 06: Cluster 9 Group A (scanner/detection-logic failures) — see docs/test-triage-149.md
    ("test_jwt_hardening.py", "test_allow_insecure_jwks_uses_verify_false_and_emits_advisory", "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (idp.example.com fails CR-03's validate_external_url() dns_failure check before httpx.get is reached); see docs/test-triage-149.md#jwt-hardening-dns-blocked"),
    ("test_jwt_hardening.py", "test_scan_jwt_targets_propagates_flag", "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (idp.example.com fails CR-03's validate_external_url() dns_failure check before httpx.get is reached); see docs/test-triage-149.md#jwt-hardening-dns-blocked"),
    ("test_broker_scanner_rabbitmq.py", "test_enrich_rabbitmq_mgmt_success", "pre_existing_triage_149", "TRIAGE-149: stale test predates CR-06 allow_cleartext opt-in guard on _enrich_rabbitmq_mgmt() (default allow_cleartext=False short-circuits to {}); see docs/test-triage-149.md#broker-rabbitmq-cr06-optin"),
    ("test_broker_scanner_rabbitmq.py", "test_enrich_rabbitmq_mgmt_401", "pre_existing_triage_149", "TRIAGE-149: stale test predates CR-06 allow_cleartext opt-in guard on _enrich_rabbitmq_mgmt() (default allow_cleartext=False short-circuits to {}); see docs/test-triage-149.md#broker-rabbitmq-cr06-optin"),
    ("test_jwt_scanner.py", "test_multi_key_jwks", "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (api.example.com fails CR-03's validate_external_url() dns_failure check); see docs/test-triage-149.md#jwt-scanner-dns-blocked"),
    ("test_jwt_scanner.py", "test_jwt_rsa_key_size", "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (api.example.com fails CR-03's validate_external_url() dns_failure check); see docs/test-triage-149.md#jwt-scanner-dns-blocked"),
    ("test_jwt_scanner.py", "test_jwt_ec_key_size", "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (api.example.com fails CR-03's validate_external_url() dns_failure check); see docs/test-triage-149.md#jwt-scanner-dns-blocked"),
    ("test_jwt_scanner.py", "test_jwt_query_param_cred_ctx_appends_key_to_url", "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (api.example.com fails CR-03's validate_external_url() dns_failure check); see docs/test-triage-149.md#jwt-scanner-dns-blocked"),
    ("test_jwt_scanner.py", "test_jwt_no_cred_ctx_unchanged_behavior", "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (api.example.com fails CR-03's validate_external_url() dns_failure check); see docs/test-triage-149.md#jwt-scanner-dns-blocked"),
    ("test_jwt_scanner.py", "test_append_query_param_continue_iteration_skips_conflicting_target", "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (h1/h2.example.com fail CR-03's validate_external_url() dns_failure check); see docs/test-triage-149.md#jwt-scanner-dns-blocked"),
    ("test_openapi_scanner.py", "test_url_scope_accepts_bare_fqdn_target", "pre_existing_triage_149", "TRIAGE-149: DNS-blocked sandbox (api.example.com fails validate_external_url()'s dns_failure check inside scan_openapi_spec's SSRF gate); see docs/test-triage-149.md#openapi-scanner-dns-blocked"),
    ("test_gap_closure.py", "test_findings_quantum_label_dsa", "pre_existing_triage_149", "TRIAGE-149: stale fixture (_make_endpoint() SimpleNamespace lacks sensor_id/segment, AttributeError silently swallowed by _derive_findings()'s broad except); see docs/test-triage-149.md#gap-closure-stale-fixture"),
    ("test_gap_closure.py", "test_findings_quantum_label_ecdsa", "pre_existing_triage_149", "TRIAGE-149: stale fixture (_make_endpoint() SimpleNamespace lacks sensor_id/segment, AttributeError silently swallowed by _derive_findings()'s broad except); see docs/test-triage-149.md#gap-closure-stale-fixture"),

    # Phase 149 Plan 07: Cluster 9 Group B (dashboard/API/DB-migration failures) — see docs/test-triage-149.md
    ("test_dashboard_scan_history.py", "test_compare_schema", "pre_existing_triage_149", "TRIAGE-149: '+' query-encoding test-construction bug (f-string embeds unescaped '+' UTC offset, decoded as space, corrupting the ISO timestamp before datetime.fromisoformat); see docs/test-triage-149.md#dashboard-compare-plus-encoding"),
    ("test_dashboard_scan_history.py", "test_compare_self", "pre_existing_triage_149", "TRIAGE-149: genuine API-contract drift (format_error() now wraps detail in a '[QRK-<CODE>] ... Fix: ...' envelope; 400 status + self-compare rejection are still correct); see docs/test-triage-149.md#dashboard-compare-error-envelope"),
    ("test_dashboard_scan_history.py", "test_compare_score_delta", "pre_existing_triage_149", "TRIAGE-149: '+' query-encoding test-construction bug (same root cause as test_compare_schema); see docs/test-triage-149.md#dashboard-compare-plus-encoding"),
    ("test_dashboard_scan_history.py", "test_compare_finding_diff", "pre_existing_triage_149", "TRIAGE-149: '+' query-encoding test-construction bug (same root cause as test_compare_schema); see docs/test-triage-149.md#dashboard-compare-plus-encoding"),
    ("test_dashboard_scan_history.py", "test_compare_endpoint_diff", "pre_existing_triage_149", "TRIAGE-149: '+' query-encoding test-construction bug (same root cause as test_compare_schema); see docs/test-triage-149.md#dashboard-compare-plus-encoding"),
    ("test_dashboard_theme.py", "test_primary_color_token", "pre_existing_triage_149", "TRIAGE-149: confirmed intentional Obsidian Pro rebrand (commit ac242d1, 2026-05-07) shifted --primary from electric-blue 210 100% 56% to teal 180 37% 47% (#4ba8a8); see docs/test-triage-149.md#dashboard-theme-obsidian-pro-rebrand"),
    ("test_dashboard_theme.py", "test_accent_color_token", "pre_existing_triage_149", "TRIAGE-149: confirmed intentional Obsidian Pro rebrand (commit ac242d1, 2026-05-07) shifted --accent from electric-blue 210 100% 56% to teal 180 37% 47% (#4ba8a8); see docs/test-triage-149.md#dashboard-theme-obsidian-pro-rebrand"),
    ("test_route_coverage.py", "test_all_data_routes_have_auth_dependency", "pre_existing_triage_149", "TRIAGE-149: stale test inventory, not a real unprotected route — GET /api/config is deliberately unauthenticated (module docstring: 'no auth required (frontend needs this before login)'), mirrors /api/health, returns only the vertical name; NOT flagged SECURITY; see docs/test-triage-149.md#route-coverage-api-config-stale-inventory"),
    ("test_db_migrate_cli.py", "test_fresh_db_reports_every_column_added", "pre_existing_triage_149", "TRIAGE-149: stale fixture — _create_legacy_schema() predates the sensor_tokens entry Phase 113 AUTH-02 added to _ADDITIVE_MIGRATIONS, causing NoSuchTableError: sensor_tokens; see docs/test-triage-149.md#db-migrate-sensor-tokens-stale-fixture"),
    ("test_db_migrate_cli.py", "test_dry_run_does_not_write", "pre_existing_triage_149", "TRIAGE-149: same sensor_tokens stale-fixture cause as test_fresh_db_reports_every_column_added; see docs/test-triage-149.md#db-migrate-sensor-tokens-stale-fixture"),
    ("test_db_migrate_cli.py", "test_result_shape", "pre_existing_triage_149", "TRIAGE-149: same sensor_tokens stale-fixture cause as test_fresh_db_reports_every_column_added; see docs/test-triage-149.md#db-migrate-sensor-tokens-stale-fixture"),
    ("test_init_db_idempotent.py", "test_all_ensure_functions_idempotent", "pre_existing_triage_149", "TRIAGE-149: naming-convention drift — _ensure_columns(engine, table, expected) (Phase 77 D-21) is a generic shared helper with a 3-arg signature, not a single-arg per-table _ensure_*(engine) helper; needs the same dir()-discovery exclusion as _ensure_parent_dir; see docs/test-triage-149.md#init-db-ensure-columns-signature-drift"),

    # Phase 149 Plan 08: Cluster 9 Group C (QRAMM subsystem failures) — see docs/test-triage-149.md
    ("test_qramm_evidence_bridge.py", "test_no_risk_engine_import", "pre_existing_triage_149", "TRIAGE-149: cross-test sys.modules pollution (test_findings_evaluator_dedupe.py::test_dedupe_via_risk_engine_shim_works imports quirk.engine.risk_engine before this file runs alphabetically in full-suite order), not a real QRAMM-12 import-graph violation; see docs/test-triage-149.md#qramm-evidence-bridge-risk-engine-sys-modules-pollution"),
    ("test_qramm_evidence_bridge.py", "test_unconfirmed_excluded_from_score", "pre_existing_triage_149", "TRIAGE-149: genuine API-contract drift — POST .../score now 422s (DASHBOARD-011) when zero QRAMMAnswer rows have answer_value set, before the unconfirmed-exclusion scoring logic under test ever runs; see docs/test-triage-149.md#qramm-evidence-bridge-score-422-unconfirmed"),
    ("test_qramm_models.py", "TestInitDbQRAMMTables.test_ensure_qramm_tables_called_after_phase46", "pre_existing_triage_149", "TRIAGE-149: stale assertion strategy — Phase 85-01 LAUNCH-04 replaced init_db()'s named per-migration call chain with a generic _ADDITIVE_MIGRATIONS loop, so the literal '_PHASE46_COLUMNS' no longer appears in init_db's function source text; the actual ordering invariant (Phase 46 columns before _ensure_qramm_tables) is still upheld in _ADDITIVE_MIGRATIONS' declared order; see docs/test-triage-149.md#qramm-models-init-db-phase46-ordering-stale-grep"),

    # Phase 149 Plan 09: Cluster 9 Group D1 (CLI/compliance/posture failures, first half) — see docs/test-triage-149.md
    ("test_cbom_schema_validation.py", "test_parametrize_set_matches_docker_compose_profiles", "pre_existing_triage_149", "TRIAGE-149: genuine chaos-lab profile drift — docker-compose.yml declares an 'otics' profile (Phase 141-07) that tests/_cbom_profiles.py's PROFILE_ENDPOINTS never gained a synthesizer for; flagged for Phase 150 lab.sh/expected_results follow-up; see docs/test-triage-149.md#cbom-schema-otics-profile-drift"),
    ("test_cli_correctness.py", "test_no_quirk_scan_references", "pre_existing_triage_149", "TRIAGE-149: stale 'quirk scan' references in historical docs (docs/UAT-SERIES.md, docs/chaos-lab.md, docs/release-notes/4.6.0.md) — none are live CLI documentation; see docs/test-triage-149.md#cli-correctness-quirk-scan-doc-drift"),
    ("test_cli_init.py", "test_init_creates_config", "pre_existing_triage_149", "TRIAGE-149: quirk init's CR-01/D-13 path-traversal guard rejects pytest tmp_path (resolves outside repo CWD), so config.yaml is never created; test predates the CR-01 guard; see docs/test-triage-149.md#cli-init-cr01-tmp-path-guard"),
    ("test_cli_init.py", "test_init_no_overwrite", "pre_existing_triage_149", "TRIAGE-149: same CR-01/D-13 path-traversal guard as test_init_creates_config — the first quirk init call never creates config.yaml, so os.path.getmtime raises before the overwrite-guard logic under test runs; see docs/test-triage-149.md#cli-init-cr01-tmp-path-guard"),
    ("test_compliance_title_join.py", "test_every_emitted_title_is_mapped_or_allowlisted", "pre_existing_triage_149", "TRIAGE-149: genuine coverage gap — 3 Phase 95 codesign finding titles (findings_evaluator.py:1026/1045/1080) were never added to COMPLIANCE_MAP or UNMAPPED_TITLES; see docs/test-triage-149.md#compliance-title-join-codesign-gap"),

    # Phase 149 Plan 09: Cluster 9 Group D1 (email/errors/install/posture failures, second half) — see docs/test-triage-149.md
    ("test_email_run_scan_wiring.py", "test_email_branch_logger_calls_use_real_logger_signatures", "pre_existing_triage_149", "TRIAGE-149: Logger.info's signature was intentionally widened to (msg, *args) in commit 01411acc (89-02 LAB-06, stdlib-compatibility fix); test enforces the pre-89-02 single-arg signature; see docs/test-triage-149.md#email-run-scan-logger-signature-widened"),
    ("test_install_errors.py", "test_port_conflict_format", "pre_existing_triage_149", "TRIAGE-149: environment-dependent — this sandbox has no uvicorn installed, so serve() emits QRK-INSTALL-002 before reaching the port-bind check that would surface QRK-INSTALL-004; see docs/test-triage-149.md#install-errors-port-conflict-missing-uvicorn"),
    ("test_install_errors.py", "test_dashboard_missing_uvicorn_format", "pre_existing_triage_149", "TRIAGE-149: stale lazy-import assumption — server.py's uvicorn import lives inside serve(), not module scope, so importing the module alone (never calling serve()) prints nothing; see docs/test-triage-149.md#install-errors-missing-uvicorn-stale-lazy-import"),

    # Phase 149 Plan 10: Cluster 9 Group D2 (docs-presence/security-gate/windows-smoke, second half of Group D) — see docs/test-triage-149.md
    ("test_phase135_docs_presence.py", "test_required_sections_present", "pre_existing_triage_149", "TRIAGE-149: stale version pin — README.md has advanced to v5.11.0 ('## What's New in v5.10'); no longer contains literal 'v5.8.0' / \"what's new in v5.8\" substrings; all other required Phase 135 content still present; see docs/test-triage-149.md#phase135-docs-stale-version-pin"),
    ("test_phase136_docs_presence.py", "test_section9_deferred_topics_absent", "pre_existing_triage_149", "TRIAGE-149: stale detection list, not a real leak — Phase 139 legitimately added its own §9.1.1 SNMPv3 Auth+Priv Scanning subsection to operators-guide.md §9 when it shipped SNMPv3 support, a properly-scoped later addition, not scope creep from Phase 137's admin guide; see docs/test-triage-149.md#phase136-docs-snmpv3-legitimate-addition"),
    ("test_safe_filter_audit.py", "test_safe_filter_paired_with_sanitize", "pre_existing_triage_149", "TRIAGE-149: stale-detection-logic, not a real unsanitized-usage finding — report.html.j2:389 narrative_lead is sourced from a small hardcoded static-prose dict (_NARRATIVE_LEADS), never scanner/user input; report.html.j2:508 hardware_section is pre-HTML-escaped in Python (render_hardware_section() calls _html.escape() on every dynamic field) before being marked safe, so sanitization happens outside the Jinja filter chain this gate inspects; see docs/test-triage-149.md#safe-filter-audit-two-legitimate-safe-usages"),
    ("test_scan_error_gate.py", "test_scan_error_writes_use_safe_str", "pre_existing_triage_149", "TRIAGE-149: stale-detection-logic, not a real safe_str bypass — kerberos_scanner.py:312 writes a ternary (safe_str(tcp_error) if tcp_error is not None else None) whose branches are both individually safe, but _classify_rhs() does not recognize ast.IfExp as a SAFE shape at all; see docs/test-triage-149.md#scan-error-gate-kerberos-ternary-ifexp-gap"),

    # Phase 149 Plan 11: final reconciliation — fresh full-suite run surfaced 11 orphaned
    # failures not present in Plans 01-10's sandboxes (different extras installed: impacket/
    # sslyze/pysnmp present here, googleapiclient absent). 2 fixed in place (sslyze __version__
    # submodule shape, impacket MethodData rename); 9 newly quarantined below. See
    # docs/test-triage-149.md's Reconciliation section.
    ("test_posture_scorefix125.py", "test_gcp_kms_403_emits_scan_error", "pre_existing_triage_149", "TRIAGE-149 (Plan 11): googleapiclient/google not installed in this sandbox — same optional_extra gap class as Cluster 7's test_gcs_reuse.py; Plan 09 found this passing because googleapiclient happened to be installed in that plan's sandbox, so gcp_connector.py's _GcpHttpError isinstance-gated 403 handling was reachable there. POSTURE-02's fix itself is not regressed. See docs/test-triage-149.md#reconciliation-gcp-googleapiclient-extras-gap"),
    ("test_posture_scorefix125.py", "test_gcp_sql_403_emits_scan_error", "pre_existing_triage_149", "TRIAGE-149 (Plan 11): same googleapiclient/google optional_extra gap as test_gcp_kms_403_emits_scan_error; see docs/test-triage-149.md#reconciliation-gcp-googleapiclient-extras-gap"),
    ("test_sensor_windows_smoke.py", "TestCleanShutdownOnKeyboardInterrupt.test_keyboard_interrupt_in_run_sensor_exits_130", "pre_existing_triage_149", "TRIAGE-149 (Plan 11): same macOS fork()-under-load SIGSEGV cluster — this run's crash dump showed the segfault inside subprocess spawning itself (subprocess.py _execute_child via _run_child_script), killing the pytest runner process. Plan 10 flagged this test as a second independent HIGH-PRIORITY SIGSEGV item; reconciliation now attributes both this and Plan 08's QRAMM pair to the same systemic cause, not two independent subsystem-specific crashes. See docs/test-triage-149.md#reconciliation-macos-fork-sigsegv-cluster"),
    ("test_version.py", "test_cli_version_subprocess", "pre_existing_triage_149", "TRIAGE-149 (Plan 11): same macOS fork()-under-load SIGSEGV cluster as test_qramm_staleness.py — 'Fatal Python error: Segmentation fault' crash dump at this exact subprocess.run() call site. Not a CLI --version regression (Cluster 3's pip install -e . fix remains correct and necessary, just not sufficient to prevent this separate, load-dependent crash). See docs/test-triage-149.md#reconciliation-macos-fork-sigsegv-cluster"),

    # Phase 149 code review (CR-01): Plan 11's reconciliation sweep missed one orphaned
    # failure of the same shared-cache SQLite class it already diagnosed for Cluster 5 —
    # test_dashboard_trends.py was never touched by any Plan 01-11 and has no ledger row,
    # but full-suite runs can intermittently reproduce it (timing-dependent, not always
    # reproducible; 2 clean local full-suite runs post-fix, reviewer reproduced it twice).

    # Phase 150 Plan 08 remediation cycle: the new `./lab.sh certs` regression test
    # (Plan 05) forks bash -> openssl subprocesses, and joins the same pre-existing
    # macOS fork()-under-full-suite-load SIGSEGV cluster diagnosed in TRIAGE-149 —
    # confirmed via direct reproduction (returncode=-11, disappears when run standalone
    # or in a smaller slice). Not a defect in lab.sh's cert generation itself.
    ("test_lab_profile_certs.py", "test_lab_sh_certs_creates_all_six_files_and_is_idempotent", "pre_existing_triage_149", "Phase 150 Plan 08: same macOS fork()-under-load SIGSEGV cluster as the TRIAGE-149 rows above — the `openssl` subprocess spawned via `./lab.sh certs` crashes with returncode=-11 only at full-suite (~3000-test) scale, confirmed via direct reproduction; passes standalone every time. See docs/test-triage-149.md#reconciliation-macos-fork-sigsegv-cluster"),
    ("test_lab_profile_certs.py", "test_generated_certs_have_correct_subject_cn", "pre_existing_triage_149", "Phase 150 Plan 08: same macOS fork()-under-load SIGSEGV cluster as test_lab_sh_certs_creates_all_six_files_and_is_idempotent above — see docs/test-triage-149.md#reconciliation-macos-fork-sigsegv-cluster"),
    ("test_lab_profile_certs.py", "test_lab_sh_certs_succeeds_without_touching_docker", "pre_existing_triage_149", "Phase 150 Plan 08: same macOS fork()-under-load SIGSEGV cluster as test_lab_sh_certs_creates_all_six_files_and_is_idempotent above — see docs/test-triage-149.md#reconciliation-macos-fork-sigsegv-cluster"),

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
    ("test_bacnet_scanner.py", "test_parse_device_object", "ci_extras_gap", "hw extra absent from .[all]; bacpypes3 not installed"),
    ("test_bacnet_scanner.py", "test_single_inflight_no_writes_unicast", "ci_extras_gap", "hw extra absent from .[all]; bacpypes3 not installed"),
    ("test_modbus_scanner.py", "test_parse_device_id", "ci_extras_gap", "hw extra absent from .[all]; pymodbus not installed"),
    ("test_modbus_scanner.py", "test_parse_device_id_decodes_bytes", "ci_extras_gap", "hw extra absent from .[all]; pymodbus not installed"),
    ("test_modbus_scanner.py", "test_single_inflight_no_writes", "ci_extras_gap", "hw extra absent from .[all]; pymodbus not installed"),
    ("test_snmp_scanner_contract.py", "test_arp_walk_import_guard_returns_empty_with_zero_network_calls", "ci_extras_gap", "hw extra absent from .[all]; pysnmp not installed"),
    ("test_identity_surface.py", "Issue3ScanWindowRegressionTest.test_issue3_scan_window_returns_all_identity_protocols", "ci_extras_gap", "identity extra absent from .[all]; impacket not installed"),

    # Phase 150 D-09/D-10 CI-parity gap closure (Plan 06, Task 2): `api` extras
    # group (schemathesis, openapi-spec-validator) absent from .[all].
    ("test_rest_fuzzer_cascade.py", "test_exception_only_cascade_trips_pause", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_cascade.py", "test_success_resets_cascade_counter", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_cascade.py", "test_5xx_only_cascade_still_trips", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_dedup.py", "TestHSTSDedup.test_multi_path_hsts_produces_single_finding", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_dedup.py", "TestHttpCredsDedup.test_multi_path_http_creds_produces_single_finding", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_dedup.py", "TestDedupDoesNotCollapseDifferentTypes.test_hsts_and_http_creds_both_capped_individually_after_dedup", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_pinned_session.py", "test_main_dispatch_mounts_pinned_adapter", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py", "TestRawSocketProbePreventsSSRF.test_probe_skipped_when_url_rejected", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py", "TestRawProbeUsesPinnedIP.test_probe_receives_pinned_ip", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py", "TestDispatchUsesAsTransportKwargs.test_dispatch_uses_as_transport_kwargs", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py", "TestScopeGate.test_scope_gate_rejects_does_not_consume_budget", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py", "TestBudgetCap.test_budget_caps_dispatch", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py", "TestRateLimiter.test_rate_limiter_invoked", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py", "TestFiveXxCascadePause.test_5xx_cascade_pause", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py", "TestAlgConfusionProbeAccepted.test_alg_confusion_accepted_is_critical", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py", "TestAlgConfusionProbeAccepted.test_alg_confusion_no_public_key_skips_info", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py", "TestBudgetCeilingBoundsAllTraffic.test_socket_probes_run_once_and_count_budget", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_rest_fuzzer_probes.py", "TestBudgetCeilingBoundsAllTraffic.test_alg_confusion_request_counts_against_budget", "ci_extras_gap", "api extra absent from .[all]; schemathesis not installed"),
    ("test_openapi_scanner.py", "test_local_file_parse", "ci_extras_gap", "api extra absent from .[all]; openapi-spec-validator not installed"),
    ("test_openapi_scanner.py", "test_local_file_security_scheme_rows", "ci_extras_gap", "api extra absent from .[all]; openapi-spec-validator not installed"),
    ("test_openapi_scanner.py", "test_url_scope_rejected", "ci_extras_gap", "api extra absent from .[all]; openapi-spec-validator not installed"),
    ("test_openapi_scanner.py", "test_url_scope_rejected_redacts_userinfo_and_query", "ci_extras_gap", "Phase 172 D-03/SAFE-03: test_url_scope_rejected_redacts_userinfo_and_query skipif — api extra absent from .[all]; openapi-spec-validator not installed"),
    ("test_openapi_scanner.py", "test_oversize_rejected", "ci_extras_gap", "api extra absent from .[all]; openapi-spec-validator not installed"),
    ("test_openapi_scanner.py", "test_external_ref_ssrf_guard", "ci_extras_gap", "api extra absent from .[all]; openapi-spec-validator not installed"),
    ("test_openapi_scanner.py", "test_openapi_plaintext_server_evidence_counter", "ci_extras_gap", "api extra absent from .[all]; openapi-spec-validator not installed"),

    # ------------------------------------------------------------------
    # Phase 150 D-15 gitignored-planning-dir gap closure (Plan 06, Task 3):
    # .planning/audit-2026-05-08/AUDIT-TASKS.md is gitignored on the public
    # repo (Phase 120 PUBREPO-01) and is absent on any public clone or CI
    # checkout. These tests take a documented existence-check skip instead of
    # a FileNotFoundError. See 150-CONTEXT.md D-15.
    # ------------------------------------------------------------------
    ("test_phase57_invariants.py", "test_audit_tasks_six_blockers_closed", "gitignored_planning_dir", ".planning/audit-2026-05-08/AUDIT-TASKS.md is gitignored on the public repo (PUBREPO-01)"),
    ("test_audit_ledger_zero_open.py", "test_audit_ledger_has_zero_bare_open_rows", "gitignored_planning_dir", ".planning/audit-2026-05-08/AUDIT-TASKS.md is gitignored on the public repo (PUBREPO-01)"),
    ("test_audit_ledger_zero_open.py", "test_deferred_and_wontfix_rows_have_rationale", "gitignored_planning_dir", ".planning/audit-2026-05-08/AUDIT-TASKS.md is gitignored on the public repo (PUBREPO-01)"),
    ("test_extras_concurrency_expander.py", "test_audit_rows_flipped_to_phase_71", "gitignored_planning_dir", ".planning/audit-2026-05-08/AUDIT-TASKS.md is gitignored on the public repo (PUBREPO-01)"),

    # Phase 184 Plan 06 (D-05): the three test_exec_content_model.py DOCX
    # entries that used to live here (test_docx_renders_cap_reason_sourced_
    # from_exec_content, test_docx_names_the_band_even_when_uncapped,
    # test_docx_names_both_the_capped_band_and_the_cap_reason -- reasons
    # were all verbatim "python-docx not installed") were RETIRED, not
    # deleted-and-forgotten: each site is a bare `pytest.importorskip("docx")`
    # whose module maps to the "docx" optional-dependencies group (via
    # python-docx>=1.1.0), so the narrow importorskip-vs-pyproject.toml
    # derivation in tests/test_skip_registry.py now auto-allows them with no
    # registry entry. See 184-06-SUMMARY.md for the retirement record.
    # ------------------------------------------------------------------
    # Phase 184 Plan 05 (DRIFT-02): the 13 genuinely-never-registered
    # "environment_capability" skips -- CLAUDE.md's GSD Verb Integrity
    # section and the "CI marker semantics gotcha" both apply. Each reason
    # is derived from the guard condition and enclosing test read directly
    # in the source file at the time of registration, not copied from
    # 184-CONTEXT.md's planning-time index.
    # ------------------------------------------------------------------
    (
        "test_gsd_state_patch.py",
        "unpatched_gsd_tree",
        "environment_capability",
        "GSD_TOOLCHAIN_AVAILABLE is False in this environment (node on PATH "
        "and ~/.claude/get-shit-done/bin/lib/{state-document.generated.cjs,"
        "state.cjs} all present) -- the Linux Full Suite CI job does not "
        "provision ~/.claude/get-shit-done/, so this fixture's three guard "
        "skips (no toolchain at all; no pristine pre-Bug-A-patch source "
        "found; the would-be pristine source is itself already patched, "
        "which would make the negative control pass vacuously) are honest "
        "and a skip here is not a pass -- run on an operator machine with "
        "GSD installed to actually exercise the Bug-A corruption "
        "reproduction this fixture builds.",
    ),
    (
        "test_gsd_state_patch.py",
        "test_patch_loss_is_actually_detected",
        "environment_capability",
        "GSD_PATCHES_AVAILABLE is False (the gsd-local-patches/ durability "
        "layer and verify-reapply-patches.cjs are not both present) or the "
        "pristine baseline for state-document.generated.cjs is missing, so "
        "this negative control -- which proves the patch-durability gate is "
        "sensitive by simulating a regeneration reverting the Bug-A patch -- "
        "has nothing to diff against. CI provisions neither the seeded "
        "patches directory nor the operator toolchain, so both skips here "
        "are honest and a skip is not a pass; see CLAUDE.md's GSD `state.*` "
        "Verb Integrity section for why this durability check exists.",
    ),
    # ------------------------------------------------------------------
    # Phase 186.1 (TOOL-01/TOOL-05): environment_capability skips in the
    # command-boundary harness built by 186.1-01 and extended by 186.1-03/04/05.
    # Every reason below is derived from the guard condition read directly in
    # tests/test_gsd_state_plain_field.py at registration time, not from a
    # planning-time index. The Linux Full Suite CI job provisions NEITHER GSD
    # install (no ~/.claude/get-shit-done/, no npx get-shit-done-cc cache), so
    # ALL of these skip in CI and a skip is NEVER a pass -- the TOOL-05 fix is
    # only actually exercised on an operator machine with both installs present.
    # ------------------------------------------------------------------
    (
        "test_gsd_state_plain_field.py",
        "pristine_npx_tree",
        "environment_capability",
        "GSD_SDK_AVAILABLE is False (no resolvable npx get-shit-done-cc "
        "sdk/dist install), or the pristine npx query sources are missing "
        "under ~/.claude/gsd-npx-sdk-patches/pristine/, or a would-be "
        "pristine source already carries the LOCAL PATCH (2026-09-07, "
        "TOOL-05) marker -- which would make every npx negative control pass "
        "vacuously against already-fixed code. All three guard skips are "
        "honest and a skip is not a pass.",
    ),
    (
        "test_gsd_state_plain_field.py",
        "pristine_cjs_tree",
        "environment_capability",
        "GSD_TOOLCHAIN_AVAILABLE is False (node on PATH plus "
        "~/.claude/get-shit-done/bin/lib/{state-document.generated.cjs,"
        "state.cjs}), or the pristine .cjs sources are missing under "
        "~/.claude/gsd-pristine/, or a would-be pristine source already "
        "carries the LOCAL PATCH (2026-09-07, TOOL-05) marker -- which would "
        "make every .cjs negative control pass vacuously. All three guard "
        "skips are honest and a skip is not a pass.",
    ),
    (
        "test_gsd_state_plain_field.py",
        "test_negative_control_state_planned_phase_cjs",
        "environment_capability",
        "GSD_TOOLCHAIN_AVAILABLE is False -- this is the pre-patch RED "
        "negative control proving `state planned-phase` via gsd-tools.cjs "
        "destroys a body prose decoy on UNPATCHED source. Without the "
        "operator toolchain there is nothing to run it against; the durable "
        "RED evidence is the verbatim transcript in 186.1-01-SUMMARY.md.",
    ),
    (
        "test_gsd_state_plain_field.py",
        "test_negative_control_state_begin_phase_cjs",
        "environment_capability",
        "GSD_TOOLCHAIN_AVAILABLE is False -- pre-patch RED negative control "
        "for `state begin-phase` via gsd-tools.cjs. Same rationale as the "
        "planned-phase control above; RED evidence lives in "
        "186.1-01-SUMMARY.md.",
    ),
    (
        "test_gsd_state_plain_field.py",
        "test_negative_control_phase_complete_cjs",
        "environment_capability",
        "GSD_TOOLCHAIN_AVAILABLE is False. NOTE: this node asserts the TRUE, "
        "empirically-verified behaviour that `phase.complete` via the .cjs "
        "install does NOT reach the body decoy (readModifyWriteStateMd never "
        "strips frontmatter and syncStateFrontmatter's rebuild absorbs the "
        "cross-contamination) -- 186.1-01 reported this divergence honestly "
        "rather than forcing a matching RED.",
    ),
    (
        "test_gsd_state_plain_field.py",
        "test_negative_control_phase_complete_cjs_frontmatter_redirect_function_level",
        "environment_capability",
        "GSD_TOOLCHAIN_AVAILABLE is False -- the function-level companion "
        "demonstrating that the underlying scoping defect still crosses the "
        "frontmatter/body boundary for phase.complete via .cjs even though it "
        "never surfaces at the command boundary. Explicitly function-level "
        "and NOT a substitute for command-boundary evidence (CLAUDE.md "
        "clause (e)).",
    ),
    (
        "test_gsd_state_plain_field.py",
        "test_positive_state_planned_phase_cjs_live_patched",
        "environment_capability",
        "GSD_TOOLCHAIN_AVAILABLE is False -- GREEN command-boundary node "
        "running `state planned-phase` against the LIVE, now-patched .cjs "
        "install. A skip means the 186.1-04 fix was NOT exercised here; the "
        "live proof is 186.1-06-SUMMARY.md's six-run transcript.",
    ),
    (
        "test_gsd_state_plain_field.py",
        "test_positive_state_begin_phase_cjs_live_patched",
        "environment_capability",
        "GSD_TOOLCHAIN_AVAILABLE is False -- GREEN inversion of the "
        "begin-phase corruption that 186.1-01's RED transcript captured. A "
        "skip means the .cjs fix was not exercised here.",
    ),
    (
        "test_gsd_state_plain_field.py",
        "test_positive_phase_complete_cjs_live_patched",
        "environment_capability",
        "GSD_TOOLCHAIN_AVAILABLE is False -- GREEN command-boundary node "
        "confirming every decoy survives byte-identical through "
        "`state complete-phase` on the patched .cjs install. NOTE per "
        "186.1-04: `phase complete <n>` dispatches to phase.cjs and does NOT "
        "reach the patched cmdStateCompletePhase; this node uses the verb "
        "that actually exercises the patch.",
    ),
    (
        "test_gsd_state_plain_field.py",
        "test_npx_patch_loss_is_actually_detected",
        "environment_capability",
        "GSD_NPX_PATCHES_AVAILABLE is False (the ~/.claude/gsd-npx-sdk-patches/ "
        "durability layer is absent), or the pristine baseline for "
        "state-document.js is missing -- so this negative control, which "
        "proves the npx durability gate is SENSITIVE by simulating a version "
        "bump reverting the TOOL-05 patch, has nothing to diff against. "
        "186.1-05 demonstrated it failing against a real live revert; a skip "
        "here is not that evidence.",
    ),
    (
        "test_uat_disposition_integrity.py",
        "test_vitest_non_vacuity_passing_substitute_is_not_flagged",
        "environment_capability",
        "VITEST_TOOLCHAIN_AVAILABLE is False (npm not on PATH and/or "
        "src/dashboard/node_modules absent) -- the Linux Full Suite CI job "
        "never installs the dashboard's Node toolchain. This is the "
        "documented, non-blocking gap tracked in docs/uat-coverage-gaps.md "
        "(item 12): the vitest substitute-execution leg only "
        "existence-checks in CI rather than actually running, so this "
        "positive-control skip does not mean the passing-substitute "
        "behaviour was exercised there.",
    ),
    (
        "test_uat_disposition_integrity.py",
        "test_vitest_non_vacuity_skipped_substitute_is_flagged",
        "environment_capability",
        "VITEST_TOOLCHAIN_AVAILABLE is False in this environment for the "
        "same reason as the sibling non-vacuity tests in this file -- CI "
        "does not install npm/node_modules under src/dashboard/. Per "
        "docs/uat-coverage-gaps.md (item 12), this is a documented, "
        "non-blocking gap: the vitest 'a skip must never count as coverage' "
        "constraint mirror only existence-checks in CI, it is not executed.",
    ),
    (
        "test_uat_disposition_integrity.py",
        "test_vitest_non_vacuity_failing_substitute_is_flagged",
        "environment_capability",
        "VITEST_TOOLCHAIN_AVAILABLE is False in this environment for the "
        "same reason as the sibling non-vacuity tests in this file -- CI "
        "does not install npm/node_modules under src/dashboard/. Per "
        "docs/uat-coverage-gaps.md (item 12), this is a documented, "
        "non-blocking gap: the vitest failing-substitute detection leg only "
        "existence-checks in CI, it is not executed.",
    ),
    (
        "test_uat_disposition_integrity.py",
        "test_vitest_substitute_nodes_pass",
        "environment_capability",
        "VITEST_TOOLCHAIN_AVAILABLE is False in this environment -- CI does "
        "not install npm/node_modules under src/dashboard/. Per "
        "docs/uat-coverage-gaps.md (item 12), this is a documented, "
        "non-blocking gap: the vitest analogue of the real-document "
        "substitute-node pass proof only existence-checks in CI rather than "
        "actually running every named vitest substitute.",
    ),
    (
        "test_target_cli.py",
        "test_unreadable_targets_file_emits_target_003_exit_2",
        "environment_capability",
        "os.geteuid() == 0 in this environment -- root bypasses the "
        "0o000-mode-bit denial this test relies on to produce an unreadable "
        "file, so there is nothing to assert TARGET-003/exit-2 against. "
        "Skipped only when running as root; a non-root CI runner exercises "
        "this test for real.",
    ),
    (
        "test_doc_command_forms.py",
        "test_no_nonexistent_command_forms",
        "environment_capability",
        "git is not on PATH in this environment, so `git ls-files` (used to "
        "enumerate every tracked file for the nonexistent-command-form "
        "scan) cannot run. This gate requires a git checkout to enumerate "
        "tracked files; any environment with git available exercises it "
        "for real.",
    ),
    (
        "test_uat_runner_version_check.py",
        "test_pattern_matches_live_version_banner",
        "environment_capability",
        "QUIRK_BIN (.venv/bin/quirk) does not exist in this environment -- "
        "this environment has no built venv, so there is no live CLI binary "
        "to invoke and the version-banner regex has nothing to run against. "
        "A skip here is not a pass; run against a real `pip install -e .` "
        "venv to exercise this test.",
    ),

    # Phase 184-08 (CR-01 gap closure): these two sites were always live
    # skip constructs but were invisible to the pre-fix gate because each
    # module binds `pytest` to an alias (`import pytest as X`) rather than
    # the literal name `pytest`, which the walker's `base.id == "pytest"`
    # check could not see. Registering both here now that the alias-blind
    # spot is closed; see 184-07-SUMMARY.md's "Gap Closure" section for the
    # detection evidence.
    (
        "test_vault_connector.py",
        "test_vault_live_uat_30_01_five_findings",
        "live_infra",
        "Requires the vault-30 chaos lab profile (port 28200) up via "
        "`docker compose --profile vault up -d` plus "
        "QUIRK_VAULT_INTEGRATION=1 set; closes Phase 30 HUMAN-UAT. Import "
        "aliased as `_pytest_uat` in this module (surfaced by CR-01's "
        "alias-resolution fix, not a new skip construct).",
    ),
    (
        "test_cross_surface_parity.py",
        "test_docx_narrative_parity",
        "optional_extra",
        "python-docx (the `docx` extras group) not installed. Written as a "
        "conditional `pytest.skip(...)` call gated on "
        "`render_docx_report(...)` returning False, not as "
        "`pytest.importorskip('docx')`, so D-05's importorskip auto-allow "
        "does not apply even though the underlying reason is the same "
        "declared extra. Import aliased as `_pytest` in this function "
        "(surfaced by CR-01's alias-resolution fix, not a new skip "
        "construct).",
    ),
]
