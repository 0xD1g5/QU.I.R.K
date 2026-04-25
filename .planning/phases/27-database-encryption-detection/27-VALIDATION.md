---
phase: 27
slug: database-encryption-detection
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-25
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/ -x -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -v --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 27-01-01 | 01 | 1 | DB-01 | — | pg_stat_ssl ssl=off → HIGH finding | unit | `python -m pytest tests/test_db_connector.py -x -q` | ❌ W0 | ⬜ pending |
| 27-01-02 | 01 | 1 | DB-01 | — | pg_has_role absent → scan_error INFO | unit | `python -m pytest tests/test_db_connector.py -x -q` | ❌ W0 | ⬜ pending |
| 27-01-03 | 01 | 1 | DB-02 | — | MySQL Ssl_cipher empty → HIGH | unit | `python -m pytest tests/test_db_connector.py -x -q` | ❌ W0 | ⬜ pending |
| 27-01-04 | 01 | 1 | DB-03 | — | RDS StorageEncrypted=false → HIGH | unit | `python -m pytest tests/test_db_connector.py -x -q` | ❌ W0 | ⬜ pending |
| 27-02-01 | 02 | 2 | DB-01 | — | _ensure_v43_columns() idempotent | unit | `python -m pytest tests/test_db.py -x -q` | ✅ | ⬜ pending |
| 27-02-02 | 02 | 2 | DB-01, DB-02, DB-03 | — | dar_ counters flow into scoring | unit | `python -m pytest tests/test_intelligence_scoring.py -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_db_connector.py` — RED stubs for DB-01, DB-02, and DB-03 (PostgreSQL, MySQL, and RDS)
- [ ] Mock fixtures for psycopg2, PyMySQL, and boto3 RDS describe_db_instances (none installed in dev environment)

*Note: pytest infrastructure already present (pyproject.toml). No framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Chaos lab postgres-ssl-off → HIGH finding | DB-01 | Requires Docker `database` profile | `docker compose --profile database up -d && python -m quirk scan --config labs/database/quirk.yaml` |
| Chaos lab mysql-ssl-off → HIGH finding | DB-02 | Requires Docker `database` profile | Same as above, check MySQL endpoint in output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
