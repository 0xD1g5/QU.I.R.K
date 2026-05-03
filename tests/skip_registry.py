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
    ("test_cbom_classifier_coverage.py", 84, "live_infra",     "REGEN_CBOM_COVERAGE guard"),
    ("test_uat_db_integration.py",       29, "live_infra",     "Requires PostgreSQL chaos lab (database profile)"),
    ("test_uat_db_integration.py",       49, "live_infra",     "Requires MySQL chaos lab (database profile)"),
    ("test_uat_db_integration.py",       69, "live_infra",     "Requires PostgreSQL chaos lab (database profile)"),
    ("test_uat_db_integration.py",       84, "live_infra",     "Requires MySQL chaos lab (database profile)"),
]
