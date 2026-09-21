---
phase: 206-dashboard-ui-coverage-drain
plan: 04
subsystem: testing
tags: [vitest, react-testing-library, radix-select, radix-sheet, dashboard, uat-coverage]

requires:
  - phase: 206-01
    provides: hasPointerCapture/setPointerCapture/releasePointerCapture and scrollIntoView jsdom stubs on Element.prototype in src/dashboard/src/test-setup.ts
  - phase: 206-03
    provides: findings.tsx left byte-clean after its own red-proof, and the findings-a fragment's row formatting
provides:
  - New vitest coverage for UAT-7-08 (severity filter narrows rows), UAT-7-09 (detail slide-out carries the selected finding's fields), UAT-7-37 (protocol filter combined with severity)
  - Red-proof fragment for the findings-b group (3 rows + citations) at red-proof/206-RED-PROOF-findings-b.md
affects: [206-13]

tech-stack:
  added: []
  patterns:
    - "Radix Select driven through the real control: click getByRole('combobox', { name }) then findAllByRole('option') and click the option whose textContent matches exactly (the ScanSelector.test.tsx pattern)"
    - "Row-set-before/after comparison on the Host column, with an explicit queryByText(...).toBeNull() absence check per excluded row — a presence-only assertion would pass against a filter that does nothing"
    - "Two-disjoint-findings fixture for the slide-out, asserting every field of the SECOND finding present and every distinctive value of the FIRST absent"

key-files:
  created:
    - src/dashboard/src/pages/__tests__/findings-filtering.test.tsx
    - src/dashboard/src/pages/__tests__/findings-protocol-filter.test.tsx
    - src/dashboard/src/pages/__tests__/findings-detail-slideout.test.tsx
    - .planning/phases/206-dashboard-ui-coverage-drain/red-proof/206-RED-PROOF-findings-b.md
  modified:
    - src/dashboard/src/pages/findings.tsx (temporarily, for red-proof only — byte-identical to pre-plan sha 3f7f448d after revert)

key-decisions:
  - "UAT-7-08's Steps say 'Type CRITICAL in the filter' but the product implements severity filtering as a Radix Select dropdown, not a text input. The test drives the dropdown — the control whose effect the Pass Criteria and the case's own GAP reason describe — rather than fabricating a text-entry path. Recorded as a Steps-vs-product divergence in the fragment; all three Pass Criteria bullets are still covered."
  - "UAT-7-37's first candidate mutation (constant-true protocol predicate) DID turn the node red, but at the protocol-only assertion, which does not exercise the combination claim that is the case's distinctive subject. A second candidate (clobbering on the severity branch) passed GREEN, because severity is applied first and protocol second. The recorded mutation clobbers on the protocol branch, leaving each filter correct in isolation and breaking only their intersection — it fails at the intersection assertion itself."
  - "UAT-7-09's fifth Pass Criteria bullet (panel closes on outside-click or X) is deliberately NOT folded into this node; it would give the node two subjects. Named verbatim as uncovered in the fragment, with three existing findings-storyline.test.tsx nodes identified that already assert SheetContent unmount, for 206-13 to cite as supplementary if it chooses."
  - "No new test-setup.ts shim was needed — 206-01's hasPointerCapture/scrollIntoView stubs already cover both the Select and Sheet interactions. Nothing was added speculatively."

requirements-completed: [COV-04]

duration: 40min
completed: 2026-09-21
---

# Phase 206 Plan 04: Findings Filters and Detail Slide-out Coverage Summary

**Three new vitest tests for the Radix-driven half of the Findings page (severity filter, protocol+severity combination, detail slide-out field fidelity), each red-proved against a mutation chosen to exercise that case's own seam.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 3 completed
- **Files modified:** 5 (3 new test files, 1 new red-proof fragment, 1 temporarily-mutated-then-reverted source file)

## Accomplishments

- `findings-filtering.test.tsx` (UAT-7-08) — asserts the pre-filter row set, then that selecting CRITICAL leaves exactly the two CRITICAL hosts, that each non-CRITICAL host is gone from the document, that row count strictly decreased, and that selecting "All Severities" restores the original set.
- `findings-protocol-filter.test.tsx` (UAT-7-37) — a four-row fixture where protocol-only, severity-only and both-applied each yield a different row set. Asserts the dropdown's exact option list, KERBEROS-alone, TLS-alone, the TLS+CRITICAL intersection, that releasing only the protocol filter leaves severity still in force, and full restore.
- `findings-detail-slideout.test.tsx` (UAT-7-09) — two findings with disjoint values; clicks the SECOND row's Title cell and asserts the drawer carries that finding's host, port, protocol, severity, description, remediation and quantum risk, with all eight of the first finding's distinctive values asserted absent.
- All three red-proved via one `TEMPORARY(206-04)` commit carrying three mutations, immediately reverted. `git diff 3f7f448d -- src/dashboard/src/pages/findings.tsx` is empty.

## Task Commits

1. **Task 1: UAT-7-08 severity filter + UAT-7-37 protocol filter tests** - `ee5a77d8` (test)
2. **Task 2: UAT-7-09 detail slide-out test** - `240abb10` (test)
3. **Task 3: Red-prove all three cases** - `69d05cc0` (TEMPORARY mutation) + `96592fca` (revert) + `76762956` (fragment)

## Red-Proof Evidence

| Case | Mutation | Verbatim failure |
|---|---|---|
| UAT-7-08 | severity predicate constant-true | `AssertionError: expected [ 'crit-a.example.com', …(3) ] to deeply equal [ 'crit-a.example.com', …(1) ]` |
| UAT-7-09 | row click always opens `findings[0]` | `TestingLibraryElementError: Unable to find an accessible element with the role "heading" and name "Bravo finding about an undersized RSA key"` |
| UAT-7-37 | protocol branch clobbers instead of intersecting | `AssertionError: expected [ 'tls-crit.example.com', …(1) ] to deeply equal [ 'tls-crit.example.com' ]` |

Full rows, including the two rejected UAT-7-37 mutations and why, are in
`red-proof/206-RED-PROOF-findings-b.md`.

## Verification

- Three cited nodes, each run alone with `-t "<exact title>"`: **1 passed (1)** each.
- Three files together: **Test Files 3 passed (3) / Tests 3 passed (3)**.
- Full dashboard suite: **Test Files 1 failed | 76 passed (77), Tests 1 failed | 451 passed | 2 skipped (454)**. The single failure is `src/pages/__tests__/print-view-layout.test.tsx`, an **untracked, in-flight file belonging to a concurrent sibling agent** (`git status` shows it as `??`, no commit touches it) — not caused by and not touched by this plan.
- `npm run build` exits 0; `npm run lint` exits 0 with 1 pre-existing warning in `ConnectorsPanel.test.tsx` (unused eslint-disable), a file this plan did not touch.
- `git diff 3f7f448d -- src/dashboard/src/pages/findings.tsx` → empty.
- No commit from this plan touches `docs/`.
- Neither new test file contains `readFileSync`; each contains exactly one `it(`.

## Deviations from Plan

**1. [Rule 1 — method correction] UAT-7-37's suggested mutation did not exercise the asserted seam**

- **Found during:** Task 3
- **Issue:** The plan suggested "make the protocol filter ignore its selected value" for UAT-7-37. That mutation does turn the node red, but at line 106 — the protocol-ONLY assertion — leaving the combination claim (the case's distinctive subject, and the whole reason the plan insisted on a combined test) unproven. A second candidate, clobbering on the severity branch, ran **green**, because severity is applied first and protocol second so the intersection still came out right.
- **Fix:** Used a third mutation — clobber on the protocol branch — which leaves each filter correct in isolation and breaks only their combination, failing at line 117, the intersection assertion. Recorded all three attempts in the fragment.
- **Files modified:** `src/dashboard/src/pages/findings.tsx` (temporary), fragment
- **Commit:** `69d05cc0` / `96592fca` / `76762956`

**2. [Documented divergence, not a fix] UAT-7-08's Steps describe a control the product does not have**

The case says "Type `CRITICAL` in the filter"; the product has a Radix Select for severity plus a separate free-text search `Input` bound to TanStack's `globalFilter`. These are different controls. The test drives the severity dropdown, which is what the Pass Criteria and the case's GAP reason actually describe. No product change, no fabricated fixture. Named in the fragment so 206-13 can qualify the disposition.

## Issues Encountered

None beyond the mutation-selection correction above. No Radix jsdom `TypeError` occurred — 206-01's shims were sufficient, so `test-setup.ts` was not touched.

## Partial / Non-Conversions

- **UAT-7-09 — partial.** Uncovered bullet, verbatim: "Panel closes when clicking outside or X button". Named in the fragment; 206-13 must qualify rather than flip an unqualified PASS.
- **UAT-7-08 — full Pass Criteria coverage**, with the Steps-vs-product divergence noted above.
- **UAT-7-37 — full Pass Criteria coverage** (all seven bullets).

## Product Defects Filed

None. No product defect was surfaced by these three cases — the severity filter, protocol filter, and detail slide-out all behave as their Pass Criteria describe. (UAT-7-08's Steps-vs-control mismatch is a documentation divergence in the UAT case, not a product defect; the case's own GAP reason already describes the dropdown's effect.)

## User Setup Required

None.

## Next Phase Readiness

- `red-proof/206-RED-PROOF-findings-b.md` is committed with 3 body rows + citations, ready for 206-12's assembly.
- `docs/UAT-SERIES.md`, `docs/uat-disposition-ledger.jsonl` and `docs/uat-coverage-gaps.md` are untouched — fenced into 206-13.
- Vitest baseline contribution: +3 files, +3 passing tests.

---
*Phase: 206-dashboard-ui-coverage-drain*
*Completed: 2026-09-21*

## Self-Check: PASSED

- FOUND: src/dashboard/src/pages/__tests__/findings-filtering.test.tsx
- FOUND: src/dashboard/src/pages/__tests__/findings-protocol-filter.test.tsx
- FOUND: src/dashboard/src/pages/__tests__/findings-detail-slideout.test.tsx
- FOUND: .planning/phases/206-dashboard-ui-coverage-drain/red-proof/206-RED-PROOF-findings-b.md
- FOUND: .planning/phases/206-dashboard-ui-coverage-drain/206-04-SUMMARY.md
- FOUND commit: ee5a77d8 (Task 1)
- FOUND commit: 240abb10 (Task 2)
- FOUND commit: 69d05cc0 (Task 3 TEMPORARY)
- FOUND commit: 96592fca (Task 3 revert)
- FOUND commit: 76762956 (Task 3 fragment)
