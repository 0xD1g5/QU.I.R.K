---
type: todo
created: 2026-09-13
source: phase-206 plan 05 (COV-04); filed at plan 206-05 close
priority: low
requirement: none (UAT-7-12 disposition input, not itself a requirement)
---

# `certificates.tsx` has no expiry-column sort — UAT-7-12 describes an absent feature

`docs/UAT-SERIES.md`'s UAT-7-12 ("Certificates Page — Expiry Sorting") describes clicking the
Expiry column header to sort the certificate inventory table ascending/descending. Confirmed
against live source (2026-09-13, re-verifying RESEARCH.md's finding rather than citing it forward):

```
$ grep -n "sort\|Sort\|tanstack" src/dashboard/src/pages/certificates.tsx
```

returns zero matches. `certificates.tsx` has no `useState<SortingState>`, no `onClick` handler on
any `TableHead`, and no `@tanstack/react-table` import at all. By contrast, the sibling
`findings.tsx` page imports `@tanstack/react-table` (line 11) and implements exactly this kind of
sortable-column interaction for its own table (the subject of UAT-7-07, which is covered).

## Why this matters

The case's three Pass Criteria bullets ("Expired cert (port 9443) appears in the correct sort
position", "Near-expiry certs show days remaining", "Date format is human-readable") assume an
interaction that does not exist. Writing an interaction test against a click handler that isn't
there would either fabricate passing behavior or fail permanently — neither is honest coverage.

## What a real fix would look like

Port the same `@tanstack/react-table` pattern `findings.tsx` and `identity.tsx` already use:
`useState<SortingState>`, a `useReactTable` instance with `getSortedRowModel()`, and
`onClick={h.column.getToggleSortingHandler()}` on the Expiry `TableHead`. The natural sort
comparator is by parsed `cert_not_after` date (via the existing `toDate()` helper), not by the
formatted display string, since the display format ("MMM d, yyyy") does not sort lexicographically
in date order.

## Acceptance (for whoever picks this up)

- `certificates.tsx` gains a sortable Expiry column, defaulting to ascending (soonest-expiring
  first) to surface the highest-risk certs on load.
- A vitest test (following the `findings-sorting.test.tsx` model) asserts clicking the Expiry
  header reorders rows and that a second click reverses the order.
- Once built, UAT-7-12 can be re-dispositioned from GAP to PASS citing the new test.
