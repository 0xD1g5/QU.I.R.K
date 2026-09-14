---
type: todo
created: 2026-09-13
source: phase-206 plan 06 (COV-04); filed at plan 206-06 close
priority: low
requirement: none (UAT-7-25 partial-coverage input, not itself a requirement)
---

# `cbom.tsx` table tab shows an empty `<tbody>`, not an empty state, when a search/filter yields zero rows

`docs/UAT-SERIES.md`'s UAT-7-25 ("CBOM Page — Algorithm Search") lists "No results shows empty
state (not a crash)" as its fourth Pass Criterion. Discovered while writing this case's new vitest
coverage (`src/dashboard/src/pages/__tests__/cbom-algorithm-search.test.tsx`, 206-06-SUMMARY.md):
reading `cbom.tsx`'s `CbomTable` component shows the `EmptyStateCard` guard
(`if (!components.length) return <EmptyStateCard .../>`) checks the **unfiltered** `components`
prop, not the post-search/post-quantum-safety-filter `filtered` array that actually feeds the
table body. When a search term or dropdown selection matches zero rows, the component does not
crash (satisfying the parenthetical), but it also renders no dedicated empty-state message — just
a `<table>` with a populated `<thead>` and a completely empty `<tbody>`.

## Why this matters

A user who types a typo'd algorithm name, or selects a quantum-safety classification with zero
matching components, sees a table that looks broken or still-loading rather than a clear "no
matches" signal. This is the same class of gap as `certificates-self-signed-flag-absent.md` and
`certificates-expiry-sort-absent.md`: a UAT Pass Criterion bullet the current component does not
implement.

## What a real fix would look like

Add a zero-row branch inside `CbomTable`'s render — e.g. when `filtered.length === 0` but
`components.length > 0`, render a `TableRow` with a single "No algorithms match your filters"
`TableCell` spanning all columns, or reuse `EmptyStateCard` with filter-aware copy distinct from
the "No CBOM components in this scan" no-data message it already shows for the true-empty case.

## Acceptance (for whoever picks this up)

- A visible "no matches" indicator (not a bare empty `<tbody>`) when a search term or
  quantum-safety filter narrows the CBOM table to zero rows, distinct from the existing
  zero-scan-data `EmptyStateCard` message.
- A vitest test (extending `cbom-algorithm-search.test.tsx` or adding a sibling) asserting the
  indicator appears for a no-match query and is absent when rows are present.
- Once built, UAT-7-25 can be re-dispositioned from partial-PASS to full PASS citing the extended
  test.
