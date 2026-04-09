# Phase 21: Identity Surface - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-09
**Phase:** 21-identity-surface
**Mode:** discuss
**Areas discussed:** Scoring integration, API design, Identity tab layout

## Gray Areas Presented

| Area | Presented | Selected for Discussion |
|------|-----------|------------------------|
| Scoring integration (IDENT-01) | Yes | Yes |
| identity_findings API design (IDENT-02) | Yes | Yes |
| Identity tab layout (IDENT-03) | Yes | Yes |

## Decisions Made

### Scoring Integration
- **Question:** Named weight drivers under identity_trust vs. flow through agility naturally?
- **Answer:** Named drivers under identity_trust (Recommended)
- **Rationale:** Consultants see labeled score drivers ("RC4/DES Kerberos etypes detected: -N pts");
  automatic profile multiplier inheritance via `identity_` prefix in PROFILE_MULTIPLIERS.

### API Design

**identity_findings relationship to findings:**
- **Question:** Derive once, expose twice vs. separate derivation paths?
- **Answer:** Derive once, expose twice (Recommended)
- **Rationale:** Single `_derive_identity_findings()` function; results converted to FindingItem
  for main findings array AND exposed as IdentityFinding in identity_findings. No logic duplication.

**IdentityFinding model:**
- **Question:** Just `algorithm` field vs. protocol-specific bonus fields?
- **Answer:** Just algorithm (Recommended)
- **Rationale:** `algorithm: str` carries the human-readable algorithm/etype name; sufficient for
  Identity tab display and dashboard filtering without added model complexity.

### Identity Tab Layout

**Summary cards:**
- **Question:** Count + worst severity + status vs. count + severity breakdown?
- **Answer:** Count + worst severity + status (Recommended)
- **Rationale:** Clear at-a-glance posture per protocol. Status labels (Critical/At Risk/Clean/
  Not Scanned) give consultant-friendly summary without requiring severity count parsing.

**Findings list:**
- **Question:** Reuse TanStack table pattern vs. custom simple list?
- **Answer:** Reuse findings table pattern (Recommended)
- **Rationale:** Existing FindingsPage has the full TanStack table pattern (sort, filter, Sheet
  drawer) — reusing it avoids a bespoke component for essentially the same affordance.

## Assumptions Confirmed Without Discussion

- Two-plan TDD structure (Plan 01 = RED scaffold, Plan 02 = GREEN) — established universal
  pattern across all 8 prior v4.2 phases
- Protocol filter dropdown (ALL/TLS/SSH/KERBEROS/SAML/DNSSEC) for IDENT-04 — clean extension
  of existing severity filter pattern
- `/identity` route with `Fingerprint` icon in sidebar — standard Nav item addition
- No new scanner code — Phases 18–20 complete; Phase 21 is wiring only
