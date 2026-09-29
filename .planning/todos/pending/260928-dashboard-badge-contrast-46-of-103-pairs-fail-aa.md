---
resolves_phase: 218
---

# 45 dashboard badge colour pairs fail WCAG AA — see backlog 999.117

**Filed:** 2026-09-28 (v5.25 milestone audit)
**Status:** DEFERRED AS ONE UNIT by operator decision, 2026-09-28
**Tag-blocking:** no

This todo is a **pointer, not a second copy.** The single source of truth is:

- `.planning/backlog/999.117-dashboard-accessibility-debt/IDEA.md` — full per-class site
  inventory, root-cause analysis, and a `## Feasibility & Effort` table with spike flags
- `.planning/HORIZON.md` § "Carried forward from v5.25 — Dashboard Accessibility Debt" — the
  8-item work breakdown and sequencing

**Do not maintain scope detail here.** Two records of one finding is how counts drift, which is
the failure mode this project has been bitten by repeatedly.

## One-line summary

103 badge `bg-token` + `text-*` pairs across 11 dashboard pages; **46 fail AA 4.5:1 in at least
one theme**; 1 fixed (the `cbom.tsx` Safe badge, a v5.25 regression from plan 213-07 that was
turning `Axe + Console Gate` red), **45 remain, all pre-existing**.

This is a **reopening of `BACK-A11Y-01`** (filed 2026-05-22, v5.0 Phase 87, lost at that
milestone's archive), not a new finding.

**Operator intent: work these together — own milestone, or bundled whole into the next one.
Not piecemeal.**
