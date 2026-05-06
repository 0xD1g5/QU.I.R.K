---
phase: 40-chaos-lab-parity
plan: "05"
subsystem: documentation
tags: [chaos-lab, docs, operator-guide, v4.2, v4.3, v4.4]
dependency_graph:
  requires: []
  provides: [docs/chaos-lab.md full v4.4 coverage]
  affects: [docs/chaos-lab.md]
tech_stack:
  added: []
  patterns: [markdown prose sections, port-reference table]
key_files:
  created: []
  modified:
    - docs/chaos-lab.md
decisions:
  - "SAML port is 8080 (compose source of truth); 8880 mentioned only as historical drift note"
  - "Section 5 port rows appended in ascending port-number order for 24 new rows"
  - "Dovecot TLS 1.3 caveat documented in 3.18 so consultants understand the weak-cipher scope"
metrics:
  duration: "2 minutes"
  completed: "2026-04-29"
  tasks_completed: 1
  files_modified: 1
---

# Phase 40 Plan 05: Chaos Lab Operator Guide — v4.2/v4.3/v4.4 Extension Summary

**One-liner:** Extended `docs/chaos-lab.md` with 8 new profile sub-sections (dnssec/saml/kerberos/vault/database/storage-s3/email/broker), a D-12 oracle pointer, 24 new port-reference rows, and `./lab.sh profiles` documentation.

## What Was Built

### Task 1: Add v4.2/v4.3/v4.4 prose sub-sections + D-12 oracle pointer

**Commit:** `c7f05b3`

`docs/chaos-lab.md` grew from 425 lines to 702 lines (+277 lines net) with these changes:

**§1 Overview changes:**
- Replaced the outdated "Phase 4 scanner coverage (JWT, container registry, ...)" sentence with a full enumeration of all 18 profiles through v4.4
- Added the D-12 blockquote pointer: `> **For UAT-grade expected scanner findings, see quantum-chaos-enterprise-lab/expected_results_v4.md**`

**New sub-sections added (§3.12–§3.19):**

| Section | Profile | Era | Key findings documented |
|---------|---------|-----|------------------------|
| 3.12 | dnssec | v4.2 | RSASHA1 CRITICAL, unsigned zone HIGH, NSEC MEDIUM |
| 3.13 | saml | v4.2 | RSA-1024 signing cert CRITICAL, SHA-1 algorithm URI HIGH |
| 3.14 | kerberos | v4.2 | rc4-hmac HIGH, aes128-cts-hmac-sha1-96 HIGH; port-collision warning |
| 3.15 | vault | v4.3 | PKI/pki HIGH, auth/token HIGH, exportable transit MEDIUM |
| 3.16 | database | v4.3 | PostgreSQL/ssl-off HIGH, plaintext-connections-allowed HIGH, MySQL/ssl-off HIGH |
| 3.17 | storage-s3 | v4.3 | S3/unencrypted HIGH (unencrypted-bucket); S3/sse-s3 no finding |
| 3.18 | email | v4.4 | 3x weak-cipher HIGH (postfix), 1x STARTTLS-downgrade MEDIUM; Dovecot TLS 1.3 caveat |
| 3.19 | broker | v4.4 | 6 HIGH (3 plaintext + 3 weak-cipher across Kafka/RabbitMQ/Redis) |

Each section includes: H3 heading, intro paragraph, ports table, `PROFILE_ARGS` invocation, expected findings bullets, and a pointer to the relevant expected_results file.

**§4 Starting Multiple Profiles:**
- Appended `./lab.sh profiles` example with description ("live read — never out of date")

**§5 Complete Port Reference:**
- Appended 24 new rows covering all v4.2/v4.3/v4.4 ports:
  - dnssec: 15353/udp, 15353/tcp
  - saml: 8080
  - kerberos: 88, 389
  - vault: 28200
  - database: 25432, 23306
  - storage-s3: 29000, 29001
  - email: 30025, 30110, 30143, 30465, 30587, 30993, 30995
  - broker: 25671, 25672, 26379, 26380, 29092, 29093

## Deviations from Plan

None — plan executed exactly as written.

The `8880` appearing in section 3.13 is intentional: it appears only in the explanatory note ("Earlier versions of this guide and the v3 oracle incorrectly listed 8880 — 8080 is correct") documenting the SAML port drift correction. The operative port throughout is 8080.

## Known Stubs

None. All new sub-sections are fully populated with real port data, real finding strings, and correct cross-references.

## Threat Flags

None — documentation only. No runtime attack surface introduced.

## Self-Check: PASSED

- `docs/chaos-lab.md` exists and is 702 lines: FOUND
- Commit `c7f05b3` exists: FOUND
- 8 new H3 sections (3.12–3.19): VERIFIED
- `expected_results_v4.md` pointer present: VERIFIED
- All required ports present (28200, 25432, 23306, 29000, 30025, 29092, 88, 389, 15353, 8080): VERIFIED
- `./lab.sh profiles` documented: VERIFIED
- `PostgreSQL/ssl-off` literal string present: VERIFIED
- `S3/unencrypted` literal string present: VERIFIED
- SAML port is 8080 (not 8880 as operative port): VERIFIED
