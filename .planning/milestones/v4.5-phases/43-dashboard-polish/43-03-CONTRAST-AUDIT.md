# Phase 43-03: Severity-Badge Contrast Audit

**Date:** 2026-05-01
**Auditor:** Plan 43-03 Task 2 execution

## Procedure

Built the production bundle and ran `VITE_A11Y_FIXTURE=1 npm run a11y:check` with the seeded
fixture data active. Checked output for `color-contrast` rule violations.

## Result: No New Violations

`grep -c 'color-contrast'` on the a11y:check output returned **0**. The axe harness reported
"no new violations" across all 9 routes against the Plan 01 baselines.

## Baseline Context

The Plan 01 baseline JSON files do record pre-existing `color-contrast` violations in several
routes (root, findings, identity, data-at-rest, cbom, trends). These are severity-badge
inline `hsl()` classes (`bg-[hsl(24_95%_53%)]` for HIGH severity) that were already present
when Phase 43 began. The baseline mechanism treats these as accepted known violations — the
a11y:check harness only fails on **new** violations beyond the baseline.

The failing elements use inline Tailwind arbitrary values (e.g., `bg-[hsl(24_95%_53%)]
text-white`) on severity badge components. These are NOT CSS variable tokens in `index.css`
— they are inline arbitrary classes written in page TSX files. Per D-18, contrast fixes must
be made via CSS variables, not by modifying inline `hsl()` strings in TSX files. Since there
are no NEW violations, and the existing violations are pre-Phase-43 baseline items, no
`index.css` changes were required.

## Conclusion

No changes made to `src/dashboard/src/index.css`. The CSS variable token system
(`--severity-low`, `--severity-high`, etc.) was reviewed and found not to be the source of
the existing baseline violations. Those violations originate from inline arbitrary Tailwind
classes in page components, which are out of scope for Plan 43-03.

The existing baseline violations will be addressed in a future pass if the badges are
refactored to use CSS variable tokens rather than inline arbitrary values.
