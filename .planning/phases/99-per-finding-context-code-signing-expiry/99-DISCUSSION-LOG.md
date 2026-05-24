# Phase 99: Per-Finding Context + Code-Signing Expiry - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-24
**Phase:** 99-per-finding-context-code-signing-expiry
**Areas discussed:** Risk "so what" source/placement, Remediation organization, Coverage scope, Expiry severity, Copy lock, Render parity

---

## Risk "so what" source & placement (CTX-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Extend ALGO_IMPACT_MAP, new field | Reuse/extend the existing crypto-class map; attach a dedicated quantum_risk field, render as its own column/block | ✓ |
| Fold into existing description | Enrich existing description text; no new field | |
| New catalog keyed by finding type | Fresh per-finding-type risk catalog | |

**User's choice:** Extend ALGO_IMPACT_MAP, new field
**Notes:** Consistent with Phase 98's crypto-class map precedent.

---

## Remediation organization (CTX-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Centralized remediation catalog | Catalog keyed by finding type/crypto-class; call sites reference it | ✓ |
| Improve in-place strings | Keep per-call-site strings, audit for specificity | |

**User's choice:** Centralized remediation catalog
**Notes:** Auditable, consistent, easier to keep specific (not generic boilerplate).

---

## Coverage scope (CTX-01/02)

| Option | Description | Selected |
|--------|-------------|----------|
| All finding sources | Backfill every finding path incl. codesign/email/broker | ✓ |
| Primary crypto findings only | Enrich main TLS/container/protocol path only | |

**User's choice:** All finding sources
**Notes:** No finding should render with empty/generic context or remediation.

---

## Code-signing expiry classification (CTX-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Expired=HIGH, approaching=MEDIUM (90d) | Expired → HIGH; ≤90d to not_after → MEDIUM; independent stacking reason; both paths | ✓ |
| Expired only | Only surface already-expired certs (HIGH) | |
| Expired=HIGH, approaching=LOW (30d) | Tighter 30-day window → LOW | |

**User's choice:** Expired=HIGH, approaching=MEDIUM (90d)
**Notes:** Expiry is independent of weak-crypto reasons; applies to both LDAP and TLS-endpoint codesign paths.

---

## Copy lock

| Option | Description | Selected |
|--------|-------------|----------|
| Lock copy in UI-SPEC first | Run /gsd-ui-phase 99 to author/lock exact strings before planning | ✓ |
| Author copy inline in the plan | Planner/executor author strings, reviewed in PR | |

**User's choice:** Lock copy in UI-SPEC first
**Notes:** Mirrors Phase 98 Copywriting Contract discipline.

---

## Render parity (CTX-01)

| Option | Description | Selected |
|--------|-------------|----------|
| All three (CLI, HTML, PDF) | Render quantum_risk in markdown table, HTML section, PDF | ✓ |
| HTML + PDF only | Client-facing surfaces only | |

**User's choice:** All three (CLI, HTML, PDF)
**Notes:** Honors EXEC-04 same-story-across-formats contract.

---

## Claude's Discretion

- Exact field name (`quantum_risk` suggested), catalog data structure, dedupe-key handling for the new field, and column-vs-block presentation within the locked copy.

## Deferred Ideas

- DOCX export (FMT-03), PDF branding/layout (FMT-01/02), net-new scanner detection — out of scope for this phase.
