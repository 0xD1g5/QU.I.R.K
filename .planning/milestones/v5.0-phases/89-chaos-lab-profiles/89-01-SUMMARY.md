---
phase: 89-chaos-lab-profiles
plan: "01"
subsystem: chaos-lab
tags: [chaos-lab, tls, postgres, redis, kafka, lab-infra, docker-compose]
dependency_graph:
  requires: []
  provides:
    - postgres-tls chaos-lab profile (LAB-01, port 39432)
    - redis-tls chaos-lab profile (LAB-02, ports 39380/39379)
    - kafka-tls chaos-lab profile (LAB-04, ports 39093/39092)
  affects:
    - quantum-chaos-enterprise-lab/docker-compose.yml
    - quantum-chaos-enterprise-lab/README.md
    - quantum-chaos-enterprise-lab/expected_results_v4.md
    - tests/test_phase89_lab_expected_results.py
tech_stack:
  added:
    - postgres:16.6 (postgres-tls lab service)
    - redis:7.4.1-alpine (redis-tls lab service — already used in broker profile)
    - apache/kafka:3.9.0 (kafka-tls lab service — upgrade from 3.7.0 in broker)
  patterns:
    - RSA-2048 self-signed cert-gen via openssl req -x509 (labs/broker/Makefile pattern)
    - Docker Compose profile isolation (standalone per-protocol weak-TLS profiles)
    - PEM keystore with ssl.keystore.certificate.chain + ssl.keystore.key (Kafka Pitfall 2 avoidance)
    - Postgres SSL key under /var/lib/postgresql/ for uid 999 ownership (Pitfall 1 avoidance)
key_files:
  created:
    - labs/postgres-tls/Makefile
    - labs/postgres-tls/postgresql.conf
    - labs/postgres-tls/pg_hba.conf
    - labs/postgres-tls/README.md
    - labs/postgres-tls/certs/.gitkeep
    - labs/redis-tls/Makefile
    - labs/redis-tls/redis.conf
    - labs/redis-tls/README.md
    - labs/redis-tls/certs/.gitkeep
    - labs/kafka-tls/Makefile
    - labs/kafka-tls/server.properties
    - labs/kafka-tls/README.md
    - labs/kafka-tls/certs/.gitkeep
    - tests/test_phase89_lab_expected_results.py
  modified:
    - quantum-chaos-enterprise-lab/docker-compose.yml
    - quantum-chaos-enterprise-lab/README.md
    - quantum-chaos-enterprise-lab/expected_results_v4.md
decisions:
  - "Postgres SSL key mounted under /var/lib/postgresql/ (uid 999 owned) rather than /etc/ssl/private/ to satisfy PostgreSQL ssl key ownership requirement (Pitfall 1)"
  - "Kafka PEM keystore uses ssl.keystore.certificate.chain + ssl.keystore.key separate-file form to avoid combined-PEM ambiguity (Pitfall 2)"
  - "All three profiles in single docker-compose.yml commit (Task 1) with lab support files as follow-on commits (Tasks 2-3)"
  - "redis-tls is a standalone profile not nested inside broker profile (Pitfall 6 avoided)"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-22"
  tasks_completed: 4
  files_created: 14
  files_modified: 3
---

# Phase 89 Plan 01: Chaos Lab Profiles — postgres-tls, redis-tls, kafka-tls — Summary

**One-liner:** Three weak-TLS chaos-lab profiles (postgres-tls/redis-tls/kafka-tls) with intentional RSA-KX ciphers, full four-file lab-sync, and a doc-completeness pytest gate.

## What Was Built

### Task 0: Doc-completeness scaffold test (RED → GREEN)

Created `tests/test_phase89_lab_expected_results.py` — a pytest module that:
- Asserts `expected_results_v4.md` contains `## Profile: postgres-tls`, `## Profile: redis-tls`, and `## Profile: kafka-tls` sections
- Asserts each section body mentions the profile's published host port (39432 / 39380 / 39093 respectively)
- Asserts `README.md` Profile Summary table contains a row for each profile name

Started RED (all 9 assertions failed). Went GREEN after Tasks 1-3 added the oracle sections.

### Task 1: postgres-tls profile (LAB-01)

**labs/postgres-tls/** support directory:
- `Makefile` — RSA-2048 cert gen (`openssl req -x509 -newkey rsa:2048`), `chmod 640` on key (postgres uid 999 can group-read)
- `postgresql.conf` — `ssl_ciphers='AES128-SHA:AES256-SHA'` (RSA key exchange, no PFS), `ssl_min/max_protocol_version='TLSv1.2'`, key path under `/var/lib/postgresql/` (uid 999 ownership fix)
- `pg_hba.conf` — `hostssl all all 0.0.0.0/0 trust`
- `README.md` — weakness inventory + expected findings

**docker-compose.yml** postgres-tls service: `postgres:16.6`, profile `postgres-tls`, port `39432:5432`, health `pg_isready -U chaos`.

**expected_results_v4.md** `## Profile: postgres-tls` section: HIGH weak-cipher + MEDIUM RSA-2048 findings.
**README.md** profile summary row added.

### Task 2: redis-tls standalone profile (LAB-02)

**labs/redis-tls/** support directory:
- `Makefile` — RSA-2048 cert gen
- `redis.conf` — mirrors `labs/broker/redis/redis.conf`: `tls-ciphers "DES-CBC3-SHA:AES128-SHA:AES256-SHA"`, `tls-protocols "TLSv1.2"`, `port 6379` + `tls-port 6380`
- `README.md` — weakness inventory

**docker-compose.yml** redis-tls service: `redis:7.4.1-alpine`, profile `redis-tls`, ports `39380:6380` + `39379:6379`, standalone (NOT inside broker profile).

**expected_results_v4.md** `## Profile: redis-tls` section: HIGH weak-cipher (39380) + HIGH plaintext-port (39379).

### Task 3: kafka-tls profile (LAB-04)

**labs/kafka-tls/** support directory:
- `Makefile` — RSA-2048 cert gen
- `server.properties` — `ssl.cipher.suites=TLS_RSA_WITH_AES_128_CBC_SHA,TLS_RSA_WITH_AES_256_CBC_SHA`, `ssl.enabled.protocols=TLSv1.2`, PEM keystore via `ssl.keystore.certificate.chain` + `ssl.keystore.key` (separate-file form avoids Pitfall 2), KRaft listeners `PLAINTEXT:9092 + SSL:9093`
- `README.md` — weakness inventory + PEM keystore note

**docker-compose.yml** kafka-tls service: `apache/kafka:3.9.0`, profile `kafka-tls`, ports `39093:9093` + `39092:9092`, healthcheck on PLAINTEXT 9092.

**expected_results_v4.md** `## Profile: kafka-tls` section: HIGH plaintext (39092) + HIGH weak-cipher + MEDIUM RSA-2048 (39093).

## Verification Results

| Check | Result |
|-------|--------|
| `docker compose config -q` | PASS |
| `pytest test_chaos_lab_image_pinning.py` (CHAOS-05) | PASS — postgres:16.6, redis:7.4.1-alpine, apache/kafka:3.9.0 all tag-pinned |
| `pytest test_phase89_lab_expected_results.py` (Task 0 gate) | PASS — all 9 assertions GREEN |
| `./lab.sh profiles` lists postgres-tls | PASS |
| `./lab.sh profiles` lists redis-tls | PASS |
| `./lab.sh profiles` lists kafka-tls | PASS |
| broker profile unchanged | PASS — kafka-broker:3.7.0, redis-broker, rabbitmq-broker untouched |
| `python -m compileall` | PASS |
| Lab-sync four-file obligation (per profile) | PASS — compose + lab.sh auto-derive + README + expected_results all updated |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Kafka PEM keystore: separate-file form instead of combined PEM**
- **Found during:** Task 3 (read_first of labs/broker/kafka/server.properties vs compose mounts)
- **Issue:** The broker's `server.properties` uses `ssl.keystore.location=...kafka.keystore.pem` but docker-compose mounts separate `kafka.crt` and `kafka.key` files — the `.keystore.pem` path is never actually mounted, meaning the broker profile relies on an unresolved path (the broker may fall back to no-SSL or error at startup). For the new `kafka-tls` profile, using the ambiguous `ssl.keystore.location` form risked the same confusion.
- **Fix:** Used `ssl.keystore.certificate.chain` + `ssl.keystore.key` (the explicit two-property form for separate files) instead of `ssl.keystore.location` pointing to a combined PEM. RESEARCH Pitfall 2 option (b) explicitly recommended this.
- **Files modified:** `labs/kafka-tls/server.properties`
- **Commit:** 403be3d

None of the other plan tasks required deviation.

## Known Stubs

None — all three profiles have complete configuration files with real weak-TLS settings.
The `certs/` directories contain `.gitkeep` placeholders; actual certs are generated at
lab-spin-up time via `make certs` (by design — generated certs are gitignored).

## Threat Flags

None — no new network endpoints outside the documented lab ports (39432/39380/39379/39093/39092);
no new auth paths; no schema changes. All Docker images are official library images
(T-89-SC disposition: mitigate via CHAOS-05 pin gate, verified PASS).

## Self-Check: PASSED

Files exist:
- tests/test_phase89_lab_expected_results.py: FOUND
- labs/postgres-tls/postgresql.conf: FOUND
- labs/postgres-tls/pg_hba.conf: FOUND
- labs/redis-tls/redis.conf: FOUND
- labs/kafka-tls/server.properties: FOUND

Commits exist:
- 8856308 (Task 0 — test RED): FOUND
- a82dae7 (Task 1 — postgres-tls): FOUND
- 15782ca (Task 2 — redis-tls): FOUND
- 403be3d (Task 3 — kafka-tls): FOUND
