# Phase 147: Backlog Drain — Lifecycle & Ledger Tail - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-10
**Phase:** 147-Backlog Drain — Lifecycle & Ledger Tail
**Areas discussed:** None — user selected the "proceed straight to research/planning" option

---

## Gray Areas Offered

| Option | Description | Selected |
|--------|-------------|----------|
| BACnet CVE coverage (DRAIN-02) | Traced code: BACnet vendor/model stored raw (numeric ID + raw model string); CVE_TABLE keyed on vendor name + product family; no resolution layer exists, so BACnet devices get zero CVE matches today despite a Facility Explorer entry existing. Real decision: build ID→name mapping vs. formally mark out-of-scope. | |
| Audit ledger fix-or-accept-risk (DRAIN-03) | WR-02 (CORS origin/port) and CD-03 (SSRF TOCTOU/DNS rebinding) are the two rows the roadmap calls out for a final fix-or-accept-risk decision; other ~10 rows just need re-verification/citation. | |
| Windows Authenticode cert status (DRAIN-04) | Only the user knows whether a production signing cert now exists — determines whether this ledger item resolves or stays blocked. | |
| None — proceed straight to research/planning | All four items are mechanical enough that root causes are already documented; user is fine letting research/planner make the calls. | ✓ |

**User's choice:** "None — proceed straight to research/planning"
**Notes:** User did not want to discuss any of the offered gray areas at this stage. Codebase
reconnaissance performed during analysis (BACnet vendor-ID/name mismatch, audit ledger row status,
Authenticode item's actual current location) was still captured in CONTEXT.md as research starting
material, but none of it reflects a user-confirmed decision — research/planning must still bring
the fix-or-accept-risk calls (DRAIN-02, DRAIN-03 WR-02/CD-03) and the Authenticode cert status
(DRAIN-04) back to the user before locking in a plan.

---

## Claude's Discretion

All four DRAIN items — user deferred discussion entirely to research/planning. See CONTEXT.md's
`<decisions>` section for the specific open questions each item still carries into planning.

## Deferred Ideas

None — no scope-creep ideas surfaced.
