---
phase: 40-chaos-lab-parity
plan: "02"
subsystem: chaos-lab-oracle
tags: [oracle, documentation, chaos-lab, expected-results, v4]
dependency_graph:
  requires: []
  provides: [expected_results_v4.md listener sections, expected_results_v3.md archive]
  affects: [plan 40-03 (appends DAR sections), plan 40-04 (README cross-links), plan 40-06 (UAT-SERIES)]
tech_stack:
  added: []
  patterns: [per-profile H2 sections, D-05 listener schema, D-07 section structure]
key_files:
  created:
    - quantum-chaos-enterprise-lab/expected_results_v4.md
  modified:
    - quantum-chaos-enterprise-lab/expected_results_v3.md
decisions:
  - "Used compose profile names as authoritative source for all profile identifiers (D-14)"
  - "pki section added fresh — v3 oracle had no pki entry, sourced from docs/chaos-lab.md line 367"
  - "SAML port fixed to 8080 from compose; v3 oracle drift value 8880 retained verbatim in v3 (historical reference only)"
  - "Stable append anchor comment left at end of v4 file for clean plan 40-03 extension"
  - "kerberos section includes port 389 LDAP row + privileged-port collision warning"
metrics:
  duration_minutes: 2
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
  completed_date: "2026-04-29"
---

# Phase 40 Plan 02: Create v4 Oracle — Listener Profile Sections Summary

**One-liner:** New `expected_results_v4.md` oracle with 13 listener-profile H2 sections (core through kerberos) using D-05 schema, drift fixes applied; v3 oracle archived with superseded notice.

---

## What Was Built

### Task 1: v4 Oracle Scaffold + Core/PhaseA/Cloud/Identity/Pki Sections

Created `quantum-chaos-enterprise-lab/expected_results_v4.md` from scratch with:

- H1 title and header block declaring scope, status (Authoritative, supersedes v3), schema description, and cross-reference guidance
- 5 listener-profile H2 sections in era order: `core`, `phaseA`, `cloud`, `identity`, `pki`
- Each section includes: D-07 required elements (H2 anchor, intro line, lab.sh invocation, D-05 schema table)
- `pki` section is entirely new content (absent from v3 oracle) — port 17443, `MTLS_STEPCA` tag, `identity` profile dependency note
- `phaseA` section preserves all three sub-sections (A1 service inventory, A2 TLS chain, A3 ingress/SNI) with validation commands
- Stable append comment at end of file for plan 40-03 DAR sections

**Commit:** `1d7f8da`

### Task 2: Remaining Listener Sections (jwt through kerberos) + v3 Archive

Appended 8 more listener-profile sections to v4 oracle, bringing total to 13:

| Section | Drift Fix Applied |
|---------|------------------|
| `## Profile: jwt` | None — rows copied verbatim from v3 lines 114-127 |
| `## Profile: registry` | None — rows copied verbatim from v3 lines 131-146 |
| `## Profile: source` | None — rows copied verbatim from v3 lines 150-165 |
| `## Profile: ssh-weak` | None — rows copied verbatim from v3 lines 189-204 |
| `## Profile: ldaps` | None — rows copied verbatim from v3 lines 208-220 |
| `## Profile: dnssec` | Profile name: `bind9` → `dnssec` (compose source of truth) |
| `## Profile: saml` | Profile name: `simpla-samlphp` → `saml`; port: `8880` → `8080` |
| `## Profile: kerberos` | Profile name: `samba-dc` → `kerberos` |

Archived `expected_results_v3.md` by inserting the "Superseded by" blockquote notice immediately after the H1 title (lines 1-3), verbatim as specified in D-01.

**Commit:** `1fe7d51`

---

## Sections Added to v4 Oracle

All 13 listener-profile sections (this plan's contribution):

1. `## Profile: core` — 10 always-on services (443, 8443, 9443, 10443, 11443, 12443, 8444, 8000, 2222, 5555)
2. `## Profile: phaseA` — 14 rows across 3 sub-sections (A1/A2/A3); ports 5556, 13443-15443, 15001, 15432, 15672, 16379, 18000, 24443
3. `## Profile: cloud` — 4 rows; ports 21000-21002, 24566
4. `## Profile: identity` — 5 rows; ports 13890, 15449, 16443, 18082, 19000
5. `## Profile: pki` — 1 row; port 17443, MTLS_STEPCA (NEW — not in v3)
6. `## Profile: jwt` — 4 rows; ports 20001-20004
7. `## Profile: registry` — 6 rows; port 20005
8. `## Profile: source` — 6 rows; port 20006
9. `## Profile: ssh-weak` — 6 rows; port 20022
10. `## Profile: ldaps` — 3 rows; port 636
11. `## Profile: dnssec` — 4 rows; port 15353 (UDP+TCP); drift-fixed from `bind9`
12. `## Profile: saml` — 2 rows; port 8080 (corrected from 8880); drift-fixed from `simpla-samlphp`
13. `## Profile: kerberos` — 3 rows; ports 88, 389; drift-fixed from `samba-dc`

DAR/messaging sections (database, storage-s3, vault, storage, email, broker) will be appended by plan 40-03, bringing total to 18+ profiles.

---

## Drift Fixes Applied

| Fix | v3 Oracle (wrong) | v4 Oracle (correct) | Source |
|-----|------------------|---------------------|--------|
| DNSSEC profile name | `bind9` | `dnssec` | docker-compose.yml profile key |
| SAML profile name | `simpla-samlphp` | `saml` | docker-compose.yml profile key |
| SAML port | `8880` | `8080` | docker-compose.yml ports binding |
| Kerberos profile name | `samba-dc` | `kerberos` | docker-compose.yml profile key |

The v3 oracle content is preserved verbatim — drift values remain in v3 for historical reference. Only the v4 oracle applies these corrections.

---

## Deviations from Plan

None — plan executed exactly as written. The kerberos section added a port 389 row (LDAP) and a privileged-port collision warning beyond what v3 contained — this is Rule 2 (completeness) since the RESEARCH inventory explicitly called out the 88+389 port-collision risk as a sharp edge consultants need to know about.

---

## Known Stubs

None. All 13 sections contain complete, sourced data. DAR/messaging sections are explicitly deferred to plan 40-03 (by design, not a stub gap).

---

## Threat Flags

None. This plan creates documentation only — no runtime attack surface introduced.

---

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `quantum-chaos-enterprise-lab/expected_results_v4.md` exists | FOUND |
| `quantum-chaos-enterprise-lab/expected_results_v3.md` exists | FOUND |
| `.planning/phases/40-chaos-lab-parity/40-02-SUMMARY.md` exists | FOUND |
| Commit `1d7f8da` exists | FOUND |
| Commit `1fe7d51` exists | FOUND |
| 13 `## Profile:` H2 sections in v4 oracle | PASSED |
| No drift profile names in v4 oracle | PASSED |
| SAML port is 8080 | PASSED |
| v3 oracle has "Superseded by" notice | PASSED |
