---
status: partial
phase: 27-database-encryption-detection
source: [27-VERIFICATION.md]
started: 2026-04-25T00:00:00Z
updated: 2026-04-25T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live scan with database chaos lab containers

expected: Start `docker compose --profile database up -d`, configure QUIRK with `enable_db: true`, `pg_targets: ["localhost:25432"]`, `mysql_targets: ["localhost:23306"]`, run a full scan. HIGH `PostgreSQL/ssl-off` and `MySQL/ssl-off` findings appear in output; both flow through CBOM correctly (not as TLS entries); `data_at_rest` subscore reflects the findings.
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
