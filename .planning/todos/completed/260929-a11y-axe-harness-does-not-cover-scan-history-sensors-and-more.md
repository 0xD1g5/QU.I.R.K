# The axe harness covers 12 routes; pages Phase 217 edited (`scan-history`) and a FIX-04 site (`sensors`) have no route at all

**Filed:** 2026-09-29, from Phase 217 (217-01 executor observation; `217-UI-REVIEW.md` top fix #2).
**Priority:** P2 — silent coverage gap in a gate whose green is read as "the dashboard is AA".
**Owner:** 999.118 (HORIZON.md ledger row; backlog .planning/backlog/999.118-a11y-design-calls-and-instrument-blind-spots/).
**Re-pointed:** 2026-10-01 by Phase 221 (INT-01). The previous owner phase closed without picking this up.

## Evidence (enumerated 2026-09-29, not from a list)

`src/dashboard/tests/a11y/routes.json` slugs: root, findings, identity, motion, data-at-rest,
certificates, cbom, roadmap, trends, qramm, hardware, compare.

Page components in `src/dashboard/src/pages/` with **no** route: `scan-history` (edited by 217-01,
FIX-01 swap), `sensors` (holds a live FIX-04 badge-baseline key,
`pages/sensors.tsx|quantum-safe|--quantum-safe-foreground|light`), `executive`, `exposure-map`,
`healthcare`, `schedules`, `scan-job`, `scan-new` (plus `login`/`print`, likely intentional).

## Also

`motion`'s three FIX-01 badges render conditionally and do not appear in the `default` fixture, so
the `/motion` sweep reports 0 violations without ever rendering the fixed badges.

Re-derive the route/page set at fix time — this list is a snapshot.

## Resolution (Phase 221, 2026-10-01)

`/scans` and `/sensors` are swept with Linux baselines (Linux gate run 36913079235 green with the
new routes). The remaining pages are named UNMEASURED-EXCLUSIONS rows (UX-NN, enforced from source
by `unmeasured-exclusions.test.ts`), owned by backlog 999.118. That ownership lives on there and in
`src/dashboard/tests/a11y/UNMEASURED-EXCLUSIONS.md`.
