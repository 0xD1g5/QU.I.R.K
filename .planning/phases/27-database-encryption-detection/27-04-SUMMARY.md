---
phase: 27-database-encryption-detection
plan: "04"
subsystem: integration
tags: [integration-wiring, run-scan, cbom-builder, chaos-lab, expected-results]
dependency_graph:
  requires:
    - "27-02: db_connector.py with scan_pg_targets/scan_mysql_targets"
    - "27-03: dar_ scoring infrastructure in evidence.py and scoring.py"
  provides:
    - "run_scan.py db_scanning phase timer block (after session_start, before dnssec)"
    - "db_endpoints in endpoint aggregation expression"
    - "CBOM builder Pass 1 explicit elif for POSTGRESQL/MYSQL/RDS"
    - "CBOM builder Pass 2 and Pass 3 skip lists include POSTGRESQL, MYSQL, RDS"
    - "docker-compose.yml database profile: postgres-ssl-off (25432) and mysql-ssl-off (23306)"
    - "expected_results_v3.md Phase 27 section with DB_POSTGRESQL_SSL_OFF and DB_MYSQL_SSL_OFF"
  affects:
    - "run_scan.py end-to-end scan pipeline (db endpoints now flow through)"
    - "quirk/cbom/builder.py (DB protocols no longer fall through to TLS else)"
    - "quantum-chaos-enterprise-lab docker-compose.yml (new database profile)"
    - "quantum-chaos-enterprise-lab/expected_results_v3.md (Phase 27 section appended)"
tech_stack:
  added: []
  patterns:
    - "lazy import inside _phase_timer block (established pattern from SAML/Kerberos blocks)"
    - "session_start passthrough to both pg and mysql scan functions (ISSUE-3 pattern)"
    - "explicit elif pass branch before TLS else in CBOM Pass 1 (prevents fall-through)"
    - "Docker profile isolation for chaos lab services (profile: database)"
key_files:
  created: []
  modified:
    - run_scan.py
    - quirk/cbom/builder.py
    - quantum-chaos-enterprise-lab/docker-compose.yml
    - quantum-chaos-enterprise-lab/expected_results_v3.md
decisions:
  - "db_scanning block positioned after session_start (line 475) and before dnssec_endpoints block — satisfies D-10 and T-27-04-1 placement threat mitigation"
  - "lazy import of scan_pg_targets/scan_mysql_targets inside the with _phase_timer block — consistent with SAML and Kerberos patterns in run_scan.py"
  - "CBOM Pass 1 explicit elif before TLS else — prevents DB endpoints from reaching TLS cipher decomposition (T-27-04-2 mitigated)"
  - "Ports 25432 and 23306 confirmed conflict-free with existing chaos lab ports (15432, 20010, 16379)"
metrics:
  duration: "184 seconds"
  completed: "2026-04-25"
  tasks: 2
  files: 4
---

# Phase 27 Plan 04: Integration Wiring — run_scan.py, CBOM Builder, Chaos Lab

Wave 3 integration wiring: DB scanner connected into the main scan pipeline via db_scanning phase timer block; CBOM builder protected from new protocol values; Docker chaos lab gets database profile with postgres-ssl-off and mysql-ssl-off services; expected_results_v3.md documents Phase 27 findings.

## What Was Built

### Task 1: run_scan.py and quirk/cbom/builder.py (commit 2173e68)

**run_scan.py:**
- `db_scanning` phase timer block inserted at line 481 — after `session_start = datetime.now(timezone.utc)` (line 475) and before `dnssec_endpoints = []`
- Block uses lazy import: `from quirk.scanner.db_connector import scan_pg_targets, scan_mysql_targets` inside the `with _phase_timer` context — consistent with SAML and Kerberos lazy import pattern
- Calls `scan_pg_targets` if `cfg.connectors.pg_targets` is populated; calls `scan_mysql_targets` if `cfg.connectors.mysql_targets` is populated — both receive `session_start=session_start` (ISSUE-3 pattern)
- Endpoint aggregation updated: `+ db_endpoints` inserted between `gcp_endpoints` and `dnssec_endpoints`

**quirk/cbom/builder.py:**
- Pass 1: Added `elif ep.protocol in ("POSTGRESQL", "MYSQL", "RDS"): pass` after KERBEROS branch — explicit no-op prevents fall-through to TLS `else` handler that would attempt cipher decomposition on DB endpoints (T-27-04-2)
- Pass 2: Extended skip tuple to include `"POSTGRESQL", "MYSQL", "RDS"` — no X.509 certificate properties emitted for DB endpoints (T-27-04-4)
- Pass 3: Extended skip tuple to include `"POSTGRESQL", "MYSQL", "RDS"` — no ProtocolProperties TLS component emitted for DB endpoints (T-27-04-4)

### Task 2: docker-compose.yml and expected_results_v3.md (commit a1e6fd7)

**quantum-chaos-enterprise-lab/docker-compose.yml:**
- `postgres-ssl-off` service: postgres:15 with `command: postgres -c ssl=off`, port 25432:5432, profile `database`, POSTGRES_USER/PASSWORD=quirk_scanner — exercises HIGH DB_POSTGRESQL_SSL_OFF finding path
- `mysql-ssl-off` service: mysql:8 with `command: --skip-ssl`, port 23306:3306, profile `database`, MYSQL_USER/PASSWORD=quirk_scanner — exercises HIGH DB_MYSQL_SSL_OFF finding path
- Both ports verified conflict-free (existing lab uses 15432, 20010, 16379)

**quantum-chaos-enterprise-lab/expected_results_v3.md:**
- Phase 27 section appended after Phase 25 Kerberos entry
- Documents postgres-ssl-off target (localhost:25432), expected HIGH `DB_POSTGRESQL_SSL_OFF`, service_detail `PostgreSQL/ssl-off`, Protocol `POSTGRESQL`
- Documents mysql-ssl-off target (localhost:23306), expected HIGH `DB_MYSQL_SSL_OFF`, service_detail `MySQL/ssl-off`, Protocol `MYSQL`
- Includes behavior description: when SHOW ssl returns 'off' / Ssl_cipher returns empty, scanner emits HIGH finding immediately

## Deviations from Plan

### Pre-existing Test Failures (out of scope — logged to deferred-items.md)

Three tests were already failing before Plan 04 changes, confirmed via `git stash` baseline check:

1. `tests/test_cli_correctness.py::test_no_quirk_scan_references` — `docs/UAT-SERIES.md` lines 1526 and 3190 contain `quirk scan` instead of `quirk --config`; pre-existing documentation issue
2. `tests/test_identity_surface.py::Issue3ScanWindowRegressionTest::test_issue3_scan_window_returns_all_identity_protocols` — pre-existing regression
3. `tests/test_v41_gap_closure.py::TestV41GapClosure::test_package_manifest_version_is_4_1_0` — installed package version 4.0.0 vs expected 4.1.0 in test environment

All three confirmed pre-existing. Plan 04 changes introduce zero new test failures. 364 tests pass (excluding pre-existing failures).

## Known Stubs

None — all integration wiring is complete. db_endpoints flow from config through run_scan.py to the CBOM builder via the established connector pattern. Docker chaos lab targets are real services with known-bad configuration.

## Threat Surface Scan

No new network endpoints or auth paths introduced. The Docker chaos lab services are lab-only (T-27-04-3 accepted: MYSQL_ALLOW_EMPTY_PASSWORD in lab context only, scoped to `profiles: ["database"]`). The CBOM builder changes are purely defensive — they prevent DB protocol values from being processed by the TLS handler.

| Threat | Disposition | Status |
|--------|-------------|--------|
| T-27-04-1: db_scanning before session_start | mitigate | Block at line 481, session_start at line 475 — verified by placement check |
| T-27-04-2: CBOM Pass 1 fall-through to TLS else | mitigate | Explicit elif pass branch added before TLS else |
| T-27-04-3: MySQL ALLOW_EMPTY_PASSWORD in lab | accept | Lab-only, database profile only |
| T-27-04-4: CBOM Pass 2/3 processing DB endpoints | mitigate | POSTGRESQL, MYSQL, RDS in both skip tuples |

## Self-Check: PASSED

| Item | Status |
|------|--------|
| run_scan.py contains `with _phase_timer(run_stats, "db_scanning"):` | FOUND (line 481) |
| run_scan.py db_scanning after session_start (line 475) | VERIFIED (481 > 475) |
| run_scan.py endpoint aggregation contains `+ db_endpoints` | FOUND (line 545) |
| quirk/cbom/builder.py Pass 1 elif POSTGRESQL/MYSQL/RDS | FOUND (line 410) |
| quirk/cbom/builder.py Pass 2 skip includes POSTGRESQL | FOUND (line 437) |
| quirk/cbom/builder.py Pass 3 skip includes POSTGRESQL | FOUND (line 517) |
| docker-compose.yml postgres-ssl-off service | FOUND (line 824) |
| docker-compose.yml profiles: ["database"] | FOUND (lines 826, 837) |
| docker-compose.yml port 25432:5432 | FOUND (line 833) |
| docker-compose.yml mysql-ssl-off service | FOUND (line 835) |
| docker-compose.yml port 23306:3306 | FOUND (line 846) |
| docker-compose.yml command: --skip-ssl | FOUND (line 844) |
| expected_results_v3.md DB_POSTGRESQL_SSL_OFF | FOUND (line 277) |
| expected_results_v3.md DB_MYSQL_SSL_OFF | FOUND (line 287) |
| expected_results_v3.md Phase 27 section | FOUND (line 270) |
| commit 2173e68 (Task 1) | FOUND |
| commit a1e6fd7 (Task 2) | FOUND |
| 364 tests pass (excluding 3 pre-existing failures) | CONFIRMED |
