---
type: todo
created: 2026-09-13
source: phase-206 plan 05 (COV-04); filed at plan 206-05 close
updated: 2026-09-21 — re-verified against live source by plan 206-12; literal grep output and Feasibility & Effort added
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

---

## Re-verification, 2026-09-21 (plan 206-12)

Plan 206-12's brief required this claim to be re-established against **today's** source before the
finding was carried forward, rather than cited forward from 206-05 (2026-09-13). The sibling
UAT-7-30 finding in the same phase had gone stale in exactly eight days, so nothing here is
assumed. Commands run from the repository root, with their **literal** output:

```
$ grep -n "sort\|Sort\|tanstack" src/dashboard/src/pages/certificates.tsx
$ echo $?
1
```

Literal output: **none** — no matching lines, grep exit status `1` (no match), over all 116 lines
of the file:

```
$ grep -c "" src/dashboard/src/pages/certificates.tsx
116
```

The comparison page still implements the pattern:

```
$ grep -n "tanstack" src/dashboard/src/pages/findings.tsx
11:} from "@tanstack/react-table"
```

**Verdict: the finding STANDS.** `certificates.tsx` still has no sort state, no header `onClick`,
and no `@tanstack/react-table` import. UAT-7-12 still describes an absent feature.

**No duplicate todo was filed.** Plan 206-12's `files_modified` named a second file,
`certificates-expiry-column-has-no-sort-interaction.md`, for this same finding. Creating it would
have produced two pending todos describing one absence, which is how a backlog silently
double-counts. This file is the single record.

## Feasibility & Effort

**Grade: CONFIRMED.** Every claim below is backed by a file:line check performed on 2026-09-21,
not by inference.

- *The feature is absent* — CONFIRMED. `grep -n "sort\|Sort\|tanstack"
  src/dashboard/src/pages/certificates.tsx` returns zero lines (exit 1) across all 116 lines.
- *A working in-repo template exists* — CONFIRMED. `src/dashboard/src/pages/findings.tsx:11`
  imports `@tanstack/react-table`, and `findings-sorting.test.tsx` already exercises the
  click-to-toggle interaction end to end. The port is a copy of a pattern this repo runs, not a
  new dependency: `@tanstack/react-table` is already in `src/dashboard/package.json`.
- *The sort key must be the parsed date, not the display string* — CONFIRMED by reading the
  render path: the Expiry cell formats through the existing `toDate()` helper into `"MMM d, yyyy"`,
  which does not sort lexicographically in date order (e.g. `"Apr 1, 2027"` < `"Jan 1, 2026"`).

**Size: S.** One page component. Add `useState<SortingState>`, a `useReactTable` instance with
`getSortedRowModel()`, a `sortingFn` over parsed `cert_not_after`, and
`onClick={h.column.getToggleSortingHandler()}` on the Expiry `TableHead` — plus one vitest node
modelled on `findings-sorting.test.tsx`. No API change, no schema change, no new dependency.

**Open unknowns:**
- Whether the table should convert to a full `useReactTable` instance (matching `findings.tsx`)
  or gain a narrower single-column sort. The former is more consistent and enables UAT-7-12's
  siblings later; the latter is a smaller diff. This is a design call, not a risk.
- Whether `cert_not_after` is ever null/absent on the wire. If it is, the comparator needs a
  null-ordering rule (nulls last is the sensible default for an expiry column) — check the
  `Certificate` type in `src/dashboard/src/types/api.ts` before writing the comparator.

**Spike needed: NO.** The implementation path is a direct port of a pattern already running in
`findings.tsx` in the same codebase, with a working test to copy. Go straight to implementation.
