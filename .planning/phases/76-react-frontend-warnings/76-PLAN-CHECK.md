# Phase 76 Plan Check — React Frontend WARNINGs

**Checked:** 2026-05-15
**Plans verified:** 76-01-PLAN.md, 76-02-PLAN.md, 76-03-PLAN.md
**Dimensions:** context_compliance, success_criteria_coverage, audit_row_coverage, research_concern_handling, build_gate, commit_atomicity

---

## Summary verdict

**ISSUES FOUND — 1 BLOCKER (wave/file-conflict), 2 WARNINGs.** Plans deliver every locked decision, every open WR row, every research concern, every SC, build-gate-before-flip, and atomic commits. The only blocker is that all three plans declare `wave: 1` with `depends_on: []` while their `files_modified` overlap (executive.tsx, print.tsx, AUDIT-TASKS.md) — parallel execution will race.

---

## Dimension 1: context_compliance (D-01..D-12)

| Decision | Plan | Task | Status |
|----------|------|------|--------|
| D-01 (useScanList error + consumer banner / WR-02) | 76-01 | T1 Part B + T3 audit-flip | PASS — RESEARCH C-1 says hook + consumer already correct; plan correctly takes audit-flip-only path with test evidence |
| D-02 (executive body.detail coercion / WR-06) | 76-01 | T2 step 1-2 | PASS — exported `coerceErrorDetail` helper |
| D-03 (print data-ready guard + alert / WR-07) | 76-01 | T2 step 3-4 | PASS — explicit BR-05 do-not-touch guard in step 5 |
| D-04 (qramm-profile submitError coercion / WR-08) | 76-01 | T2 step 6 | PASS — inline reuse of D-02 pattern |
| D-05 (VALID_THEMES allowlist / WR-04) | 76-02 | T2 step 1-2 | PASS — `as const`, exported helper, no console.warn |
| D-06 (useRef timer + blob URL cleanup / WR-05) | 76-02 | T2 step 3-5 | PASS — matches RESEARCH Pattern 2 exactly |
| D-07 (ComplianceMapTab dep narrow / WR-13) | 76-02 | T2 step 6-7 | PASS — narrowed to `[ctx.sessionId]` per C-4 (NOT `ctx.scoreResult?.session_id`) |
| D-08 (RFC-2253 CN regex / WR-09) | 76-03 | T2 step 1-3 | PASS — new `lib/cert-parse.ts`, 3 consumer sites rewired |
| D-09 (cytoscape module augment / WR-10) | 76-03 | T2 step 4-6 | PASS — sibling `.d.ts`, both `cbom.tsx` AND `roadmap.tsx` cast removed |
| D-10 (Scorecard math + bar class / WR-11, WR-12) | 76-03 | T2 step 7-12 | PASS — `DIMENSION_COUNT` (per C-5 semantic), `MATURITY_BAR_CLASS` separate from `MATURITY_BADGE_CLASS`, Indeterminate em-dash |
| D-11 | — | — | N/A — explicitly absent in CONTEXT (numbering gap, RESEARCH C-6) |
| D-12 (do-not-touch list) | all 3 | — | PASS — each plan reiterates D-12 in its action/success_criteria; BR-05 cleanup, Phase 55 Recharts/CalculateScore, Phase 62 hooks, MATURITY_BADGE_CLASS Badge usage all guarded |

**Deferred ideas (Out of Scope):** Centralized error banner, README hoist, broader cytoscape typing, theme animation — none appear in plans. PASS.

**Result:** PASS.

---

## Dimension 2: success_criteria_coverage (3 SCs)

| SC | Maps To | Plan | Status |
|----|---------|------|--------|
| SC-1: useScanList error / body.detail coercion / print sentinel / submitError | REACT-01 | 76-01 | PASS — all 4 sub-claims covered by D-01..D-04 truths |
| SC-2: Theme validation / PDF cleanup / ComplianceMapTab targeted refetch | REACT-02 | 76-02 | PASS — D-05/D-06/D-07 truths |
| SC-3: Cert regex / Cytoscape typing / Scorecard math + classes | REACT-03 | 76-03 | PASS — D-08/D-09/D-10 truths |

**Result:** PASS — 3/3 SCs covered.

---

## Dimension 3: audit_row_coverage (11 open WR rows)

| Audit Row | Plan | Status |
|-----------|------|--------|
| WR-02 | 76-01 T3 | PASS (audit-flip-only per C-1, with test evidence) |
| WR-04 | 76-02 T3 | PASS |
| WR-05 | 76-02 T3 | PASS |
| WR-06 | 76-01 T3 | PASS |
| WR-07 | 76-01 T3 | PASS |
| WR-08 | 76-01 T3 | PASS |
| WR-09 | 76-03 T3 | PASS |
| WR-10 | 76-03 T3 | PASS |
| WR-11 | 76-03 T3 | PASS |
| WR-12 | 76-03 T3 | PASS |
| WR-13 | 76-02 T3 | PASS |

76-03 Task 3 acceptance criterion explicitly cross-checks all 11 closed under Phase 76. PASS — 11/11.

---

## Dimension 4: research_concern_handling

| Concern | Plan resolution | Status |
|---------|----------------|--------|
| C-1: useScanList already correct | 76-01 takes audit-flip-only with Wave-0-equivalent test evidence (Task 1 Part B) | PASS |
| C-2: 3 regex sites, no `lib/cert-parse.ts` | 76-03 creates `lib/cert-parse.ts`, rewires all 3 sites (certificates.tsx Subject, Issuer, print.tsx Subject) | PASS |
| C-3: Cast is `as cytoscape.Ext` not `as any`, 2 sites | 76-03 drops cast at both `cbom.tsx:20` and `roadmap.tsx:13` | PASS |
| C-4: `ctx.scoreResult?.session_id` doesn't exist; use `ctx.sessionId` | 76-02 narrows to `[ctx.sessionId]` | PASS |
| C-5: `4` is DIMENSION_COUNT semantic, not MATURITY_MAX | 76-03 names constant `DIMENSION_COUNT` with explicit comment | PASS |
| C-6: D-11 absent | Acknowledged, no action needed | PASS |
| C-7: Spot-check Phase 65/66 untouched | 76-01 T1 read_first lists scan-history.tsx; D-12 reiterated; 76-01 confirms NO code edit there | PASS (light) |
| Pitfall 3: BR-05 cleanup at print.tsx:332-335 | 76-01 T2 step 5 + acceptance criterion grep ensures BR-05 cleanup preserved | PASS |
| Pitfall 5: MATURITY_BADGE_CLASS preserved | 76-03 T2 step 12 + acceptance criterion `MATURITY_BADGE_CLASS == 1` (Badge usage) + Task 1 regression test | PASS |
| Pitfall 6: Indeterminate frontend type unverified (A2) | 76-03 T2 step 11 references conditional "matches Phase 74's null-safe shape" | WARNING — assumption A2 still open; planner did not add a Wave 0 read of `QRAMMScoreResponse` type to confirm `dimensions[d].score: number \| null` is the actual TS shape. If the type is `number`, the `score === null` branch dead-codes and Indeterminate behavior is unreachable. |

**Result:** PASS with 1 WARNING (Pitfall 6 / A2 unverified).

---

## Dimension 5: build_gate

All three plans place `cd src/dashboard && npm run build` as **Step 1 of Task 3, BEFORE** the audit-row flip in Step 2, with explicit guard: "If non-zero, do NOT flip audit rows; fix the build first."

- 76-01 T3: build → flip WR-02, 06, 07, 08
- 76-02 T3: build → flip WR-04, 05, 13
- 76-03 T3: build → flip WR-09, 10, 11, 12 (build also doubles as TS module-augmentation gate for D-09)

**Result:** PASS — 3/3 plans gate audit-flip on green build.

---

## Dimension 6: commit_atomicity

Each plan = 3 commits with clear conventional-commit subject lines:

| Plan | Task 1 (RED) | Task 2 (GREEN) | Task 3 (DOCS) |
|------|-------------|---------------|--------------|
| 76-01 | `test(76-01): add failing tests for REACT-01 ...` | `feat(76-01): implement REACT-01 fixes ...` | `docs(76-01): close react-frontend WR-02/WR-06/WR-07/WR-08 in audit ledger` |
| 76-02 | `test(76-02): add failing tests for REACT-02 ...` | `feat(76-02): implement REACT-02 fixes ...` | `docs(76-02): close react-frontend WR-04/WR-05/WR-13 in audit ledger` |
| 76-03 | `test(76-03): add failing tests for REACT-03 ...` | `feat(76-03): implement REACT-03 fixes ...` | `docs(76-03): close react-frontend WR-09/WR-10/WR-11/WR-12 in audit ledger` |

Source + test colocated in the feat commit (RED→GREEN sequenced via the prior test commit); docs commit is audit-ledger-only ("No other rows touched. Single docs commit.").

**Result:** PASS.

---

## Issues

### BLOCKER-1: Wave-1 parallel execution races on shared files

**Severity:** blocker
**Dimension:** dependency_correctness

All three plans declare `wave: 1` with `depends_on: []`, but their `files_modified` sets overlap:

| File | 76-01 | 76-02 | 76-03 |
|------|-------|-------|-------|
| `src/dashboard/src/pages/executive.tsx` | ✓ (D-02) | ✓ (D-06) | — |
| `src/dashboard/src/pages/print.tsx` | ✓ (D-03) | — | ✓ (D-08 site #3) |
| `.planning/audit-2026-05-08/AUDIT-TASKS.md` | ✓ (4 rows) | ✓ (3 rows) | ✓ (4 rows) |

If the orchestrator runs all three in parallel as Wave 1 implies, simultaneous edits to `executive.tsx`, `print.tsx`, and `AUDIT-TASKS.md` will conflict. Each plan's Task 2 also runs `npm run build` and the full test pattern, which races against in-flight edits from sibling plans.

**Fix options (pick one):**
1. **Serialize:** Set `depends_on: ["01"]` on 76-02 (executive.tsx + AUDIT-TASKS), `depends_on: ["01","02"]` on 76-03 (print.tsx + AUDIT-TASKS). Assign waves 1→2→3.
2. **De-conflict files:** Move WR-05 (executive.tsx) out of 76-02 into 76-01 (or vice versa), move WR-09 print.tsx Subject site into 76-01, and have a single closing plan flip all 11 audit rows. This collapses the wave into one serial chain anyway.

Recommendation: Option 1 — minimal restructuring. The phase has only 11 audit rows and ~10 source files; sequential execution is fast and avoids merge logic in the orchestrator.

### WARNING-1: Pitfall 6 / Assumption A2 unverified

**Severity:** warning
**Dimension:** research_concern_handling

RESEARCH A2 states the `QRAMMScoreResponse` TS type should be checked to confirm `dimensions[d].score: number | null`. If the actual type is `number` (not `number | null`), 76-03 Task 2 step 11's Indeterminate em-dash branch is unreachable from real data, and the D-10 test for Indeterminate (Task 1 `it('renders em-dash row for Indeterminate ...')`) will only pass via a manually constructed fixture — not against real backend output.

**Fix:** Add a one-line `read_first` entry in 76-03 Task 2 (e.g., `src/dashboard/src/lib/api.ts` or wherever `QRAMMScoreResponse` is declared) and either (a) confirm the type already accepts `null` per-dimension, or (b) widen the type as part of the fix. The plan currently asserts behavior without verifying the type contract.

### WARNING-2: WR-02 audit-flip-only path is contingent on Wave 0 outcome

**Severity:** warning
**Dimension:** task_completeness

76-01 Task 1 acceptance criteria for the WR-02 Part B test say "EITHER outcome is acceptable for Task 1 — log the result." If Part B fails (consumer banner missing), the audit-flip-only premise breaks and a code edit to `scan-history.tsx` is required — but no task is planned for that contingency. Task 3 unconditionally flips WR-02 to closed.

**Fix:** Either (a) commit to the audit-flip-only path explicitly (require Part B test to PASS as a Task 1 acceptance criterion, fail the plan if it doesn't), or (b) add a contingency Task 1.5 that adds the banner to `scan-history.tsx` if Part B fails. Current language ("EITHER outcome is acceptable") leaves the planner with no defined branch.

Note: RESEARCH C-1 says the consumer already renders the error card, so this is low-probability — but the plan should not leave a contingent path undefined.

---

## Per-plan summary

| Plan | Tasks | Files modified | Wave | Verdict |
|------|-------|---------------|------|---------|
| 76-01 | 3 | 8 | 1 (overlap) | Content PASS, blocker is wave-only |
| 76-02 | 3 | 7 | 1 (overlap) | Content PASS, blocker is wave-only |
| 76-03 | 3 | 11 | 1 (overlap) | Content PASS, blocker is wave-only |

Per-plan task counts (3 each) and file counts (7–11) are within thresholds.

---

## Recommendation

Return to planner with one targeted revision: re-wave the plans serially (76-01 → 76-02 → 76-03 via `depends_on`). Optionally address WARNING-1 (add A2 type-shape read_first to 76-03) and WARNING-2 (commit to WR-02 audit-flip-only path or add contingency).

Content of every plan is otherwise execution-ready — D-01..D-10, all 11 WR rows, all 7 research concerns, all 3 SCs, build-gate-before-flip, atomic conventional-commits.

