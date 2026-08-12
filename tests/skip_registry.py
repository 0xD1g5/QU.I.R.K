"""Phase 41 D-02: Central allowed-skip registry.

Each entry: (file_relative_to_tests_dir, line_number, category, reason)
category in {"optional_extra", "live_infra", "pre_existing_triage_149"}

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
    ("test_db_migrate_cli.py",               166, "optional_extra", "run_scan not importable in minimal dev env (optional reporting deps missing)"),
    ("test_distributed_topology.py",         48,  "live_infra",     "Requires docker binary"),
    ("test_identity_scanner_hardening.py",   80,  "optional_extra", "impacket not installed"),
    ("test_jobs_api.py",                     489, "live_infra",     "Linux-only /proc zombie-reconciliation check"),
    ("test_jwt_scanner.py",                  209, "optional_extra", "httpx not installed"),
    ("test_pdf_metadata_constants.py",       19,  "optional_extra", "playwright.sync_api not installed"),
    ("test_pdf_metadata_constants.py",       20,  "optional_extra", "pypdf not installed"),
    ("test_pdf_metadata_constants.py",       56,  "optional_extra", "Playwright Chromium runtime not available"),
    ("test_pqc_discriminator.py",            126, "live_infra",     "Requires oqs-nginx chaos-lab profile"),
    ("test_pqc_discriminator.py",            141, "live_infra",     "Requires oqs-nginx chaos-lab profile"),
    ("test_report_injection_hardening.py",   240, "optional_extra", "playwright.sync_api not installed"),
    ("test_report_injection_hardening.py",   241, "optional_extra", "pypdf not installed"),
    ("test_report_injection_hardening.py",   254, "optional_extra", "Playwright Chromium binary not available"),
    ("test_report_render_undetermined_hosts.py", 150, "optional_extra", "python-docx not installed"),
    ("test_report_render_undetermined_hosts.py", 162, "optional_extra", "python-docx not installed"),
    ("test_report_render_undetermined_hosts.py", 215, "optional_extra", "python-docx not installed"),
    ("test_scheduler_cmd.py",                314, "live_infra",     "SIGTERM not supported on Windows"),
    ("test_snmp_scanner_contract.py",        598, "optional_extra", "pysnmp not installed"),
    ("test_snmp_scanner_contract.py",        631, "optional_extra", "pysnmp not installed"),
    ("test_snmp_scanner_contract.py",        673, "optional_extra", "pysnmp not installed"),

    # Phase 149 D-02/D-03: test-suite triage quarantines — see docs/test-triage-149.md
    ("test_notify_email.py",       79,  "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_emailpy-test_starttls_path_timeout_and_recipients"),
    ("test_notify_email.py",       142, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_emailpy-test_ssl_path_timeout_passed"),
    ("test_notify_email.py",       196, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_emailpy-test_no_login_when_smtp_user_none"),
    ("test_notify_webhook.py",     135, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_webhookpy-test_no_hmac_when_key_env_not_set"),
    ("test_notify_webhook.py",     164, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_webhookpy-test_hmac_header_present_when_key_set"),
    ("test_notify_webhook.py",     207, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_webhookpy-test_hmac_absent_when_key_env_empty"),
    ("test_notify_webhook.py",     237, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_webhookpy-test_body_omits_topology_keys"),
    ("test_notify_webhook.py",     271, "pre_existing_triage_149", "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test_notify_webhookpy-test_non_2xx_raises_runtime_error"),
]
