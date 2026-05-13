"""Phase 41 D-02: Central allowed-skip registry.

Each entry: (file_relative_to_tests_dir, line_number, category, reason)
category in {"optional_extra", "live_infra"}

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
    ("test_chaos_storage.py",           41,  "live_infra",     "Requires Docker + MinIO"),
    ("test_chaos_storage.py",           67,  "live_infra",     "Requires Docker + MinIO"),
    ("test_dnssec_scanner.py",          475, "live_infra",     "Requires BIND9 chaos lab"),
    ("test_saml_scanner.py",            366, "live_infra",     "Requires SimpleSAMLphp chaos lab"),
    ("test_kerberos_scanner.py",        360, "live_infra",     "Requires Samba DC chaos lab"),
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
]
