---
phase: 40-chaos-lab-parity
plan: "03"
subsystem: infra
tags: [oracle, expected-results, database, s3, vault, email, broker, postgresql, mysql, minio, kafka, rabbitmq, redis]

# Dependency graph
requires:
  - phase: 40-chaos-lab-parity plan 40-02
    provides: v4 oracle scaffold + listener profile sections (core through kerberos); trailing append anchor

provides:
  - "## Profile: database — D-06 schema with literal PostgreSQL/ssl-off + MySQL/ssl-off service_detail strings"
  - "## Profile: storage-s3 — D-06 schema with S3/unencrypted + S3/sse-s3 strings; MinIO console noted as unscanned"
  - "## Profile: vault — D-06 schema with transit/rsa-2048-exportable, PKI/pki, auth/token, auth/userpass"
  - "## Profile: storage — legacy hybrid deprecated; pointer to v4.3 successors; config-introspection sub-list"
  - "## Profile: email — 7 host ports with SMTP-STARTTLS/SMTPS/IMAP-STARTTLS/IMAPS/POP3-STARTTLS/POP3S labels; TLS 1.3 caveat"
  - "## Profile: broker — 6 host ports; 6 HIGH findings; KAFKA-PLAIN/KAFKA-TLS/AMQP-PLAIN/AMQPS/REDIS-PLAIN/REDIS-TLS"
  - "v4 oracle complete: 19 ## Profile: sections covering all chaos lab profiles through v4.4"

affects: [40-04-README, 40-05-chaos-lab-md, 40-06-docs-uat]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-06 category-tuned oracle schema: DAR profiles use domain-specific columns (Engine, Encryption Mode, Mount Type) vs listener D-05 schema"
    - "Dual-style expected condition: Oracle alias (DB_POSTGRESQL_SSL_OFF) paired with literal scanner output (protocol=POSTGRESQL, service_detail=PostgreSQL/ssl-off)"
    - "Deprecation annotation pattern: legacy profile gets Deprecated header + pointer to v4.3 successors"

key-files:
  created: []
  modified:
    - quantum-chaos-enterprise-lab/expected_results_v4.md

key-decisions:
  - "Used dual oracle-alias + literal-scanner-string format for database profile (e.g. DB_POSTGRESQL_SSL_OFF → protocol=POSTGRESQL, service_detail=PostgreSQL/ssl-off) so both docs/UAT-SERIES.md aliases and regression test matching work"
  - "storage profile uses D-06 hybrid schema: D-05 listener table for ports + config-introspection sub-list for KMS/pgcrypto findings, consistent with D-06 definition"
  - "email profile uses D-05 listener schema (not D-06) because email endpoints are TLS listeners, consistent with plan 40-03 task 2 instruction"

patterns-established:
  - "Category-tuned oracle columns: database (Port|Service|Engine|TLS in Transit|Encryption-at-Rest|...), storage-s3 (Port|Service|Provider|Encryption Mode|Public Access|KMS Key|Versioning|...), vault (Port|Service|Mount Type|Seal Type|Auto-Unseal|...)"

requirements-completed: [LAB-03]

# Metrics
duration: 2min
completed: 2026-04-29
---

# Phase 40 Plan 03: DAR + Messaging Oracle Sections Summary

**Six category-tuned oracle sections (database, storage-s3, vault, storage legacy, email, broker) appended to expected_results_v4.md using verbatim scanner output strings, completing the 19-profile v4 oracle through v4.4**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-29T21:35:55Z
- **Completed:** 2026-04-29T21:37:43Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Appended `## Profile: database` with D-06 schema: PostgreSQL 15 (port 25432) and MySQL 8 (port 23306), both SSL-off. Literal service_detail strings `PostgreSQL/ssl-off` and `MySQL/ssl-off` plus UAT-SERIES oracle aliases (`DB_POSTGRESQL_SSL_OFF`, `DB_MYSQL_SSL_OFF`).
- Appended `## Profile: storage-s3` with D-06 schema: MinIO on port 29000 — `encrypted-bucket` (S3/sse-s3, no finding) and `unencrypted-bucket` (S3/unencrypted, HIGH). MinIO console (29001) noted as unscanned.
- Appended `## Profile: vault` with D-06 schema: vault-30 on port 28200 — transit keys, PKI mount (PKI/pki HIGH), and auth methods (auth/token HIGH, auth/userpass MEDIUM).
- Appended `## Profile: storage` (legacy hybrid deprecated): D-06 hybrid schema with listener table (20007/20009/20010) + config-introspection sub-list. Deprecation annotation points to v4.3 successors.
- Appended `## Profile: email` with D-05 listener schema: 7 host ports (30025/30465/30587/30143/30993/30110/30995). Risk titles verbatim: "STARTTLS downgrade risk on SMTP" (MEDIUM) + "Weak cipher suite on email TLS endpoint" (HIGH). TLS 1.3 caveat for Dovecot documented.
- Appended `## Profile: broker` with D-05 listener schema: 6 host ports, 6 HIGH findings. Risk titles verbatim: "Kafka plaintext listener detected", "AMQP plaintext listener detected", "Redis plaintext listener (no authentication)", "Weak cipher suite on broker TLS endpoint".
- v4 oracle now totals 19 `## Profile:` sections — complete coverage of all chaos lab profiles through v4.4.

## Task Commits

Each task was committed atomically:

1. **Task 1: Append database, storage-s3, vault, and legacy storage sections (DAR core)** - `1e52d16` (feat)
2. **Task 2: Append email and broker sections (v4.4 messaging)** - `3e909b4` (feat)

**Plan metadata:** (docs commit — created below)

## Files Created/Modified
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — 121 lines appended; 6 new `## Profile:` sections; v4 oracle complete at 19 profiles

## Decisions Made
- **Dual oracle-alias + literal-string format for database profile:** Both `DB_POSTGRESQL_SSL_OFF` (UAT-SERIES alias) and `protocol=POSTGRESQL, service_detail=PostgreSQL/ssl-off` (literal scanner output) appear in the same cell so UAT scripts using the alias and regression tests matching literal output both work without translation.
- **storage profile uses D-06 hybrid schema:** Listener table for the three legacy ports (20007/20009/20010) plus a config-introspection sub-list for KMS/pgcrypto findings. This mirrors the D-06 definition exactly (the one profile that mixes types because it predates the v4.3 split).
- **email profile uses D-05 listener schema:** Email endpoints are TLS listeners, not config-introspection targets, so the standard `Port | Service | Expected protocol | Expected condition / tag | Notes` schema applies (per plan task 2 instruction to use D-05).

## Sections Added — Literal Scanner Strings Used

| Section | Schema | Literal service_detail strings | Ports |
|---------|--------|-------------------------------|-------|
| database | D-06 | `PostgreSQL/ssl-off`, `PostgreSQL/plaintext-connections-allowed (N non-SSL)`, `MySQL/ssl-off` | 25432, 23306 |
| storage-s3 | D-06 | `S3/sse-s3`, `S3/unencrypted` | 29000, 29001 |
| vault | D-06 | `transit/rsa-2048-classification`, `transit/rsa-2048-exportable`, `PKI/pki`, `auth/token`, `auth/userpass` | 28200 |
| storage (legacy) | D-06 hybrid | `RSA_2048`, `RSA_1024`, `AES_256`, `ECC_P256`, `pgp_sym_encrypt (weak passphrase)` | 20007, 20009, 20010 |
| email | D-05 | `SMTP-STARTTLS:25`, `SMTPS:465`, `SMTP-STARTTLS:587`, `IMAP-STARTTLS:143`, `IMAPS:993`, `POP3-STARTTLS:110`, `POP3S:995` | 30025, 30465, 30587, 30143, 30993, 30110, 30995 |
| broker | D-05 | `KAFKA-PLAIN:29092`, `KAFKA-TLS:29093`, `AMQP-PLAIN:25672`, `AMQPS:25671`, `REDIS-PLAIN:26379`, `REDIS-TLS:26380` | 29092, 29093, 25672, 25671, 26379, 26380 |

## Legacy storage Deprecation Annotation

The `## Profile: storage` section carries the following deprecation note (verbatim):

> **Deprecated** — split in v4.3 into `database` (PostgreSQL/MySQL SSL detection), `storage-s3` (MinIO/S3 buckets), and `vault` (Vault transit/PKI/auth audit). Retained for backwards compatibility with v4.1 / v4.2 UAT runs. Predates the clean per-resource split.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None — all expected condition / tag cells reference real scanner output strings verified from RESEARCH §Style B (which was verified against scanner source files by the researcher).

## Threat Flags

No runtime attack surface — documentation only.

## Next Phase Readiness
- `expected_results_v4.md` is now complete (19 profiles). Plan 40-04 can use `## Profile: <name>` anchors as cross-reference targets in the README profile summary table (D-11).
- All anchor names follow GitHub's convention (lowercase, colons stripped, spaces to dashes): `#profile-database`, `#profile-storage-s3`, `#profile-vault`, `#profile-storage`, `#profile-email`, `#profile-broker`.

---
*Phase: 40-chaos-lab-parity*
*Completed: 2026-04-29*

## Self-Check: PASSED

- `quantum-chaos-enterprise-lab/expected_results_v4.md` exists and contains 19 `## Profile:` sections
- Task 1 commit `1e52d16` verified in git log
- Task 2 commit `3e909b4` verified in git log
