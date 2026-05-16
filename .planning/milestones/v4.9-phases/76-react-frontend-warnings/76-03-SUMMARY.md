---
phase: 76-react-frontend-warnings
plan: 03
subsystem: dashboard
tags: [react, frontend, certificates, cytoscape, qramm, scorecard]
requires: [REACT-03]
provides:
  - lib/cert-parse.ts (RFC-2253-aware extractCN + parseDistinguishedName)
  - types/cytoscape-augment.d.ts (cytoscape.use module augmentation)
  - lib/qramm-constants.ts::DIMENSION_COUNT
  - lib/qramm-constants.ts::MATURITY_BAR_CLASS
affects:
  - pages/certificates.tsx (Subject + Issuer renderers)
  - pages/print.tsx (Subject renderer)
  - pages/cbom.tsx (cytoscape.use cast removed)
  - pages/roadmap.tsx (cytoscape.use cast removed)
  - components/qramm/ScorecardTab.tsx (bar math + class + Indeterminate)
tech-stack:
  added: []
  patterns: ["TS module augmentation for third-party libs", "RFC-2253 escape-aware regex with post-process unescape", "data-testid hook for non-text DOM selection in Vitest"]
key-files:
  created:
    - src/dashboard/src/lib/cert-parse.ts
    - src/dashboard/src/types/cytoscape-augment.d.ts
    - src/dashboard/src/lib/__tests__/cert-parse.test.ts
    - src/dashboard/src/components/qramm/__tests__/scorecard-maturity.test.tsx
  modified:
    - src/dashboard/src/pages/certificates.tsx
    - src/dashboard/src/pages/print.tsx
    - src/dashboard/src/pages/cbom.tsx
    - src/dashboard/src/pages/roadmap.tsx
    - src/dashboard/src/lib/qramm-constants.ts
    - src/dashboard/src/components/qramm/ScorecardTab.tsx
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions:
  - D-08 confirmed — shared helper at lib/cert-parse.ts is the single source of CN extraction; 3 inline regex sites collapsed to extractCN()
  - D-09 confirmed — module augmentation pattern; both `as cytoscape.Ext` casts dropped at cbom.tsx:20 and roadmap.tsx:13
  - D-10 confirmed — DIMENSION_COUNT named per dimension-count semantic (not MATURITY_MAX); MATURITY_BAR_CLASS added alongside (not replacing) MATURITY_BADGE_CLASS
metrics:
  duration: 3m 37s
  completed: 2026-05-15
  tasks_completed: 3
  tests_added: 20
---

# Phase 76 Plan 03: REACT-03 Cert regex / Cytoscape / Scorecard math Summary

**One-liner:** Closed REACT-03 (WR-09, WR-10, WR-11, WR-12) — extracted RFC-2253-aware CN parser to `lib/cert-parse.ts`, replaced `as cytoscape.Ext` casts with a `cytoscape.use` module-augmentation `.d.ts`, and corrected ScorecardTab Maturity Distribution to use `DIMENSION_COUNT` for width math + `MATURITY_BAR_CLASS` (solid `bg-*` only) for bar fill + em-dash row for the Phase 74 "Indeterminate" sentinel.

## What Shipped

### D-08 (WR-09) — RFC-2253 cert CN parser

- **New `src/dashboard/src/lib/cert-parse.ts`** exports:
  - `extractCN(dn)` — regex `/CN=((?:[^,\\]|\\.)*)(,|$)/` + `.replace(/\\(.)/g, '$1')` post-processing. Returns `'—'` for null/undefined/empty input, the input verbatim when no `CN=` match, otherwise the unescaped CN.
  - `parseDistinguishedName(dn)` — thin wrapper exposing the CN slot (broader DN parsing deferred per RESEARCH Open Q2 / D-12, no current consumer needs O / OU).
- **3 inline regex sites collapsed to the helper** (RESEARCH C-2 confirmed):
  - `pages/certificates.tsx:60-61` → `extractCN(cert.cert_subject)`
  - `pages/certificates.tsx:62-64` → `extractCN(cert.cert_issuer)`
  - `pages/print.tsx:88` → `extractCN(c.cert_subject)`
- Verified cases (parametrized): `CN=plain` → `plain`; `CN=plain,O=Corp` → `plain`; `CN=O\,reilly` → `O,reilly`; `CN=Smith\, John,O=Acme` → `Smith, John`; `CN=alpha\\beta,O=Acme` → `alpha\beta`; `null`/`undefined`/`''` → `'—'`; `O=Corp` → passthrough; `OU=CNothing` → passthrough (regex anchored to `CN=` only).

### D-09 (WR-10) — Cytoscape module augmentation

- **New `src/dashboard/src/types/cytoscape-augment.d.ts`** with `declare module 'cytoscape' { function use(extension: unknown): void }`. Sibling to existing `cytoscape-extensions.d.ts` (which declares the extension modules themselves) — concerns kept independently auditable per RESEARCH Standard Stack note.
- **Both `as cytoscape.Ext` casts removed** (RESEARCH C-3 confirmed both sites cast the extension, not cytoscape itself):
  - `pages/cbom.tsx:20` → `cytoscape.use(coseBilkent)`
  - `pages/roadmap.tsx:13` → `cytoscape.use(dagre)`
- `npm run build` (which type-checks via tsc) exits 0 — confirms the augmentation is valid TypeScript.

### D-10 (WR-11, WR-12) — ScorecardTab maturity bars

- **`lib/qramm-constants.ts`** gained:
  - `DIMENSION_COUNT = 4` — named per dimension-count semantic (CVI/SGRM/DPE/ITR), NOT maturity max (RESEARCH C-5). Doc comment makes the distinction explicit.
  - `MATURITY_BAR_CLASS: Record<number, string>` — solid `bg-quantum-vulnerable` / `bg-quantum-at-risk` / `bg-severity-low` / `bg-quantum-safe`. No `/20`, no `text-*`, no `border-*`.
- **`MATURITY_BADGE_CLASS` preserved untouched** for the Dimension Summary table Badge usage at line 249 (RESEARCH Pitfall 5 — Badges legitimately want the `bg-X/20 text-X border-X` token cluster).
- **`components/qramm/ScorecardTab.tsx`**:
  - Bar fill className: `MATURITY_BADGE_CLASS[level]` → `MATURITY_BAR_CLASS[level]` (D-10 / WR-12).
  - Bar width: `${(count / 4) * 100}%` → `${(count / DIMENSION_COUNT) * 100}%` (D-10 / WR-11).
  - `data-testid={\`maturity-bar-${level}\`}` added to the bar `<div>` for clean Vitest selection.
  - New `isIndeterminate` memo: when `scoreResult.maturity === 'Indeterminate'` OR every per-dimension score is null, the distribution rows render em-dashes in place of bars (D-10 Indeterminate row, mirrors Phase 74 backend sentinel).

## Test Cadence

- **Task 1 (RED)** — `test(76-03): add failing tests for REACT-03 (D-08 cert-parse RFC-2253, D-10 maturity math + bar class)` — 20 new assertions (11 cert-parse + 9 scorecard-maturity). All failing (missing helper, missing `MATURITY_BAR_CLASS` / `DIMENSION_COUNT` exports, badge tokens at bar site). Commit `9fbd6c0`.
- **Task 2 (GREEN)** — `feat(76-03): implement REACT-03 fixes (D-08 cert-parse, D-09 cytoscape augment, D-10 maturity bar + DIMENSION_COUNT)` — 20/20 tests pass. Commit `390424b`.
- **Task 3 (docs + build gate)** — `docs(76-03): close react-frontend WR-09/WR-10/WR-11/WR-12 in audit ledger` — `npm run build` exits 0; 4 audit rows flipped; rebuilt dashboard statics committed. Commit `21e1dc6`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] ScorecardTab Dimension Summary table crashed on null `d.score`**

- **Found during:** Task 1 (RED test "Indeterminate" exposed `TypeError: Cannot read properties of null (reading 'toFixed')` at `ScorecardTab.tsx:239`).
- **Issue:** The Dimension Summary table guarded `d != null` but then called `d.score.toFixed(2)` — for Phase 74 Indeterminate dimensions, `d` is non-null but `d.score` is null, so `.toFixed()` crashed.
- **Fix:** Replaced `d != null ? d.score.toFixed(2) : '—'` with a numeric `typeof` guard (`const dscore = typeof d?.score === 'number' ? d.score : null`) applied uniformly to score, weighted, and the `maturityInt` derivation. Mirrors the bar-section's `isIndeterminate` shape.
- **Files modified:** `src/dashboard/src/components/qramm/ScorecardTab.tsx`
- **Why this is in scope:** Plan explicitly requires Indeterminate handling (D-10); the crash made that test path impossible to satisfy. The fix is the same Phase 74 null-safety pattern referenced in RESEARCH Pitfall 6.
- **Commit:** Bundled into `390424b` (GREEN commit).

## Threat Flags

None — surfaces stay inside the existing trust boundaries documented in the plan's `<threat_model>`. No new network endpoints, auth paths, file access patterns, or schema changes. All four STRIDE entries (T-76-08..T-76-11) mitigated as planned.

## Audit Ledger

`react-frontend/WR-09`, `WR-10`, `WR-11`, `WR-12` flipped from `— | [ ] open` to `Phase 76 | [x] closed`. Combined with 76-01 and 76-02, all 11 Phase 76 react-frontend WR rows are now closed (`grep -cE "react-frontend/WR-(02|04|05|06|07|08|09|10|11|12|13).*Phase 76.*\[x\] closed"` returns `11`).

## Known Stubs

None. All consumers of the new helpers are wired to live data; `MATURITY_BAR_CLASS` and `DIMENSION_COUNT` are referenced from ScorecardTab; both cytoscape sites compile clean without the cast.

## Self-Check: PASSED

- src/dashboard/src/lib/cert-parse.ts → FOUND
- src/dashboard/src/types/cytoscape-augment.d.ts → FOUND
- src/dashboard/src/lib/__tests__/cert-parse.test.ts → FOUND
- src/dashboard/src/components/qramm/__tests__/scorecard-maturity.test.tsx → FOUND
- Commit 9fbd6c0 (RED) → FOUND
- Commit 390424b (GREEN) → FOUND
- Commit 21e1dc6 (docs) → FOUND
- `npm run build` exit 0 → CONFIRMED
- `npm test -- cert-parse scorecard-maturity` 20/20 passing → CONFIRMED
- 4 audit rows flipped (WR-09/10/11/12) → CONFIRMED via grep
- All 11 Phase 76 WR rows closed → CONFIRMED via grep
- `MATURITY_BADGE_CLASS` preserved untouched in qramm-constants.ts → CONFIRMED
