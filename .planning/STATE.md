---
gsd_state_version: 1.0
milestone: v4.10.1
milestone_name: Scoring Correctness Hotfix
status: planning
last_updated: "2026-05-22T03:39:11.344Z"
last_activity: 2026-05-22
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-16)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours
**Current focus:** v4.10 — roadmap defined, ready for phase planning

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-05-22 — Milestone v4.10.1 started

## Milestone Summary (v4.10 — in progress)

| Phase | Wave | Slug | Plans | Status |
|-------|------|------|-------|--------|
| 78 | A | html-pdf-injection-hardening | TBD | Not started |
| 79 | A | smime-ldap-discovery-scanner | TBD | Not started |
| 80 | A | windows-adcs-scanner | TBD | Not started |
| 81 | A | cmvp-attestation-feed | TBD | Not started |
| 82 | A/B | chaos-lab-fidelity | TBD | Not started |
| 83 | B | integration-gate-cleanup | TBD | Not started |
| 84 | B | release-engineering | TBD | Not started |
| 85 | C | public-launch-polish | TBD | Not started |

**Wave gating:** Wave A (78–82 parallel, 78 starts first) → Wave B (83, 84) → Wave C (85)

## Previous Milestone Summary (v4.9 — SHIPPED 2026-05-15)

| Phase | Slug | Plans | Status |
|-------|------|-------|--------|
| 69 | deferred-blockers-scanner-cloud | 6/6 | Complete 2026-05-15 |
| 69.1 | k8s-test-fixture-hardening (INSERTED) | 1/1 | Complete 2026-05-15 |
| 70 | deferred-blockers-api-qramm-model | 3/3 | Complete 2026-05-15 |
| 71 | protocol-scanner-warnings | 5/5 | Complete 2026-05-15 |
| 72 | cloud-scanner-warnings | 5/5 | Complete 2026-05-15 |
| 73 | cbom-intel-reports-warnings | 3/3 | Complete 2026-05-15 |
| 74 | qramm-compliance-warnings | 3/3 | Complete 2026-05-15 |
| 75 | api-cli-core-warnings | 4/4 | Complete 2026-05-15 |
| 76 | react-frontend-warnings | 3/3 | Complete 2026-05-15 |
| 77 | info-code-quality-audit-ledger | 5/5 | Complete 2026-05-15 |

**Audit ledger (v4.9):** zero `[ ] open` rows — 166 closed, 2 deferred-with-rationale, 4 wont-fix-with-rationale; CI gate `tests/test_audit_ledger_zero_open.py` locks the invariant forward.

## Accumulated Context

### Roadmap Evolution

- v4.9 shipped 2026-05-15. All 35 requirements satisfied; archive at `.planning/milestones/v4.9-ROADMAP.md` + `.planning/milestones/v4.9-REQUIREMENTS.md`.
- v4.10 roadmap created 2026-05-16. 8 phases (78–85), 52 requirements, 100% coverage. Three-wave structure mirrors v4.8 Wave A/B discipline.

### Decisions (v4.10 — pre-execution)

- v4.10-D-01 (pre-locked by research): CMVP module never emits `certified: true` — only `fips_140_3_coverage` informational list. CMVP-07 is the permanent CI invariant. (Source: SUMMARY.md cross-cutting recommendation 4)
- v4.10-D-02 (pre-locked by research): `certipy-ad` excluded — pins `cryptography~=42.0.8`, breaks TLS scanner. AD CS via impacket LDAP only. (Source: SUMMARY.md cross-cutting recommendation 2; mirrors v4.2 Key Decision)
- v4.10-D-03 (Phase 80-01 execution, 2026-05-16): adcs chaos-lab profile uses Bitnami-native `LDAP_CUSTOM_SCHEMA_DIR=/schemas` env hook for msPKI schema loading. Both originally planned branches (seed-time `ldapadd cn=config` + Dockerfile `COPY ... etc/schema/`) rejected at runtime under `bitnamilegacy/openldap:2.6.10`; Dockerfile preserved as tertiary fallback per D-80-R7 "ship both branches" contract.
- v4.10-D-04 (Phase 80-01 execution, 2026-05-16): msPKI schema overlay uses private OID arc `1.3.6.1.4.1.99999.80.*` rather than Microsoft's real `1.2.840.113556.1.4.20XX` — the latter collides with the bundled `msuser` schema (slapadd "Inconsistent duplicate attributeType"). Scanner keys off attribute NAMES (not OIDs) so the private arc is functionally equivalent; attribute names match Microsoft's real schema verbatim.
- v4.10-D-03 (pre-locked by research): S/MIME discovery is LDAP-only (`userCertificate`/`userSMIMECertificate`). No IMAP, no mailbox content. AST CI gate (SMIME-08) is preventative for future drift. (Source: SUMMARY.md cross-cutting recommendation 3)
- v4.10-D-04 (pending Phase 84 task 1): PyPI name `quirk` availability unknown. RELENG-01 is the first task of Phase 84; if taken, distribution name is changed before any packaging automation is written.

### Pending Todos

- Phase 78 must start before Phases 79–82 so downstream scanner additions land in a hardened report environment (soft ordering, not a hard dep)
- CHAOS-04 and CHAOS-06 cannot be fully verified until Phases 79+80 deliver `smime`/`adcs` profiles — Phase 82 has both Wave A tasks (CHAOS-01..03, CHAOS-05) and Wave B tasks (CHAOS-04, CHAOS-06)
- SCORE_WEIGHTS invariant test must be updated exactly once in Phase 83, after both SMIME and ADCS scanners have landed their four new weight entries

### Blockers/Concerns

None — roadmap is fully defined. All critical traps documented in SUMMARY.md and encoded as explicit success criteria or CI invariants.

## Deferred Items

Items carried forward from v4.9 close (still open):

| Category | Item | Status |
|----------|------|--------|
| uat_gap | Phase 43: 43-HUMAN-UAT.md (2 pending) — loading-state first paint + keyboard focus ring visibility | deferred — require live browser session |
| uat_gap | Phase 44: 44-HUMAN-UAT.md (1 pending) — Phase 29 K8s cloud-only justification review | deferred — human confirmation needed |
| verification_gap | Phase 46: 46-VERIFICATION.md not authored (code verified live) | deferred — retroactive authoring needed |
| uat_gap | Phase 47: 4 manual TTY tests pending (nmap wizard interactive flow) | deferred — require TTY session |
| test_infra | test_cbom_schema_validation.py fails when cyclonedx json-validation extra absent | deferred — optional dep, not blocking |

## Session Continuity

Last session: 2026-05-21T13:32:42.886Z
Stopped at: v4.10 SHIPPED 2026-05-21 — milestone lifecycle complete (audit→complete→cleanup)
Next action: `/gsd-plan-phase 80` continuation — run Plan 80-02 (scanner module)
