---
status: deferred
phase: 27-database-encryption-detection
source: [27-01-SUMMARY.md, 27-02-SUMMARY.md, 27-03-SUMMARY.md, 27-04-SUMMARY.md]
started: 2026-04-25T00:00:00Z
updated: 2026-04-25T00:00:00Z
deferred_reason: Not blocking next phase. Tests captured in docs/UAT-SERIES.md as UAT-5-25. Requires Docker database profile (postgres-ssl-off, mysql-ssl-off).
---

## Current Test

number: 1
name: Cold Start Smoke Test
expected: |
  Kill any running scanner process. Clear any temp state.
  Run: python3 run_scan.py
  The CLI should start cleanly — no import errors, no crash on startup.
  The scanner should reach the prompt (interactive mode) or complete a
  no-targets scan without traceback. run_scan.py now includes a db_scanning
  phase timer block — startup should be unaffected.
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running scanner process. Clear any temp state. Run `python3 run_scan.py`. The CLI should start cleanly — no import errors, no crash on startup. The scanner should reach the interactive prompt or complete a no-targets scan without traceback. (run_scan.py includes the new db_scanning phase timer block.)
result: [pending]

### 2. Chaos Lab Database Services Start
expected: From the quantum-chaos-enterprise-lab directory, run `docker compose --profile database up -d`. Both `postgres-ssl-off` (port 25432) and `mysql-ssl-off` (port 23306) services should start without errors. Verify: `docker compose --profile database ps` shows both containers running.
result: [pending]

### 3. PostgreSQL SSL-off Detection
expected: With postgres-ssl-off running (localhost:25432), configure QUIRK with `enable_db: true` and `pg_targets: ["localhost:25432"]` and a valid pg_scanner_user/password (quirk_scanner/quirk_scanner). Run a scan. The output should include a HIGH finding with protocol `POSTGRESQL` and service_detail `PostgreSQL/ssl-off` (finding code DB_POSTGRESQL_SSL_OFF).
result: [pending]

### 4. MySQL SSL-off Detection
expected: With mysql-ssl-off running (localhost:23306), configure QUIRK with `mysql_targets: ["localhost:23306"]` and mysql_scanner_user/password (quirk_scanner/quirk_scanner). Run a scan. The output should include a HIGH finding with protocol `MYSQL` and service_detail `MySQL/ssl-off` (finding code DB_MYSQL_SSL_OFF).
result: [pending]

### 5. data_at_rest Subscore in Readiness Report
expected: After the DB scan above (tests 3 and 4), the quantum readiness report should show a `data_at_rest` subscore alongside the existing subscores (hygiene, modern_tls, identity_trust, agility_signals). The total score cap is now 125 (5 subscores × 25 max). The data_at_rest score should be reduced from 25 by the DB plaintext findings.
result: [pending]

### 6. CBOM — DB Endpoints Not TLS-Decomposed
expected: Inspect the generated CBOM (JSON or XML output) after scanning DB targets. POSTGRESQL and MYSQL endpoints should NOT appear as TLS protocol components — no cipher suite decomposition, no X.509 certificate properties for those entries. They should appear as their own component type only.
result: [pending]

### 7. Unreachable DB Target Surfaces as scan_error
expected: Configure a pg_target pointing at a non-existent host (e.g., 127.0.0.1:19999). Run a scan. The output should include a scan_error endpoint for that target — the target should NOT silently disappear from the results. The finding should indicate a connection error (e.g., "connection-error: OperationalError" or similar).
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps
