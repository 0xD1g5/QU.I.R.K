---
phase: 111
slug: console-dashboard-awareness
type: ui-review
status: complete
overall_score: 21/24
baseline: 111-UI-SPEC.md
audited: 2026-05-26
---

# Phase 111 — UI Audit (6-Pillar)

**Overall: 21/24** — code-only audit (no dev server captured). Advisory/non-blocking.
Two of the three priority findings were remediated immediately after the audit (see Resolution).

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | All spec-mandated copy matches exactly; error/empty/loading states present |
| 2. Visuals | 3/4 | Coverage banner placement diverged from spec order; CBOM Graph tab hidden-filter gap |
| 3. Color | 4/4 | All hardcoded hex spec-authorized; no unauthorized accent/primary overuse |
| 4. Typography | 3/4 | Two `font-medium` (500) instances in the CBOM graph legend (pre-existing Phase 77 code) |
| 5. Spacing | 4/4 | 8-point scale consistent; no arbitrary px/rem |
| 6. Experience Design | 3/4 | CBOM Graph tab segment filter was inaccessible when graph tab active |

## Priority Findings

1. **CBOM Graph tab hidden segment filter** — the segment Select lived inside `CbomTable`, so on the
   Graph tab the filter was invisible/uncontrollable though `filteredComponents` was still filtered.
   **RESOLVED** (commit `b1e620e`): Select JSX moved up to `CbomPage` scope above `<Tabs>` — always visible.
2. **Coverage banner render order** — banner rendered before `<RegressionAlertChip />`, separating it
   from the gauges. **RESOLVED** (commit `a5a8cb4`): order swapped so the banner sits immediately above
   the gauges Card it qualifies (per UI-SPEC §4).
3. **Findings filter-bar height mismatch** — Phase 111's correctly-sized segment Select (`h-8 text-sm`)
   made the pre-existing severity/protocol Selects' missing `h-8 text-sm` visually prominent.
   **DEFERRED** (pre-existing; opportunistic normalization).

## Minor

- `font-medium` (weight 500) in the CBOM graph legend (`cbom.tsx:356,363`) — pre-existing Phase 77
  code; spec says 400/600 only. Remediate opportunistically.

## Accessibility (all PASS)

Badge color never the sole status signal (text label always present); coverage banner
`role="alert"` + `aria-live="polite"`; all `<TableHead>` have `scope="col"`; segment Select has
`aria-label="Filter by segment"`; nav link `min-h-[44px]` + `aria-label`; sensors skeleton
`role="status"`.

## Resolution

Findings #1 and #2 (Phase-111-introduced / spec-fidelity) were fixed and rebuilt immediately after
the audit (`tsc` clean, `npm run build` exit 0, vitest 77/77). Finding #3 and the `font-medium`
minor are pre-existing and left for opportunistic cleanup. Visual fidelity confirmation remains
deferred human UAT (open the built dashboard against 111-UI-SPEC.md).
