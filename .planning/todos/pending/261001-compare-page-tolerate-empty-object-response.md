# ComparePage dereferences `data.added_findings.length` on an empty `{}` body

**Filed:** 2026-10-01, by Phase 221 (RESEARCH Finding 3 / Open Question 3).
**Priority:** P3. The harness fixture was corrected in 221-03, so nothing is red; this is production hardening.
**Owner:** unassigned. A separate decision; fold into a dashboard-hardening pass.

## What happens

`src/dashboard/src/pages/compare.tsx:99-101` computes `data.added_findings.length + data.removed_findings.length`
straight from the fetched body. A `{}` response (what the old empty-variant fixture returned) makes that throw.
The real API returns a full zero-diff body, so this is not a known live failure.

## Disposition

221-03 made the `empty` compare fixture a faithful zero-diff response (`compareZeroDiff`), removing the harness
dependence on the page tolerating `{}`. Whether the page should also tolerate a malformed body is a separate
product decision; no code was changed here.
