# The axe harness covers 12 routes; pages Phase 217 edited (`scan-history`) and a FIX-04 site (`sensors`) have no route at all

**Filed:** 2026-09-29, from Phase 217 (217-01 executor observation; `217-UI-REVIEW.md` top fix #2).
**Priority:** P2 — silent coverage gap in a gate whose green is read as "the dashboard is AA".
**Owner:** Phase 220 (CI Instrument Truth). Relevant to Phase 218 FIX-05's "anywhere" wording.

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
