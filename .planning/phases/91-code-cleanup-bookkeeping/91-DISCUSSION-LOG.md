# Phase 91: Code Cleanup + Bookkeeping - Discussion Log

> **Audit trail only.** Decisions are in CONTEXT.md.

**Date:** 2026-05-22
**Phase:** 91-code-cleanup-bookkeeping
**Areas discussed:** carry-in fold-in, Tier-B scope (revisited), JWT advisory location

---

## Carry-in fold-in (CLEAN-03)

| Option | Selected |
|--------|----------|
| Fold them in (conftest QUIRK_DB_PATH fix + remove stale CONCERNS §1.11) | ✓ |
| Literal CLEAN-01..04 only | |

**Choice:** Fold in. 91 owns the conftest DB-isolation fix and the stale-CONCERNS removal as bookkeeping.

---

## Tier-B dead-code scope (revisited at user request)

| Option | Selected |
|--------|----------|
| Listed items + report the rest (vulture report, no delete) | ✓ |
| Listed items only | |
| Aggressive — delete all confident vulture hits | |
| Per-candidate review | |

**Choice:** Delete only BACK-49/50/51/52/54 (vulture/AST-confirmed + smoke test); ALSO run a repo-wide vulture pass and write `dead-code-candidates.md` as a reviewed backlog WITHOUT deleting. Rationale: QUIRK's optional-extra/dynamic-import/re-export patterns make vulture over-report; the happy-path smoke test can't exercise every install path, so deletion of raw hits is risky. Report captures the signal safely.

**Note:** user re-opened this after initially selecting "listed only" — the report-the-rest middle path was added on revisit.

---

## JWT verify=False advisory (CLEAN-04)

| Option | Selected |
|--------|----------|
| Code comment + brief docs note | ✓ |
| Docs only | |
| Code comment only | |

**Choice:** Inline comment at the call site + a brief docs note.

## Deferred Ideas

- Opportunistic dead-code beyond the listed BACK items (captured in the D-02b report, not acted on).
- BACK-A11Y-01 — separate UI/a11y workstream, not part of 91.
