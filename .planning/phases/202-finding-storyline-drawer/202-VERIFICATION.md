---
phase: 202-finding-storyline-drawer
verified: 2026-09-13T00:15:00Z
status: human_needed
score: 4/4 must-haves verified (criteria 2 and 3 verified under operator-confirmed reframings, not literal readings)
overrides_applied: 0
human_verification:
  - test: "Live-dashboard visual/keyboard walkthrough of the storyline drawer"
    expected: "Drawer opens by keyboard on the Storyline trigger; theme lift reads as non-individual (never implies 'resolving this finding alone yields N pts'); A5 honest-absence narrative reads as intentional, not broken; Esc closes and focus returns to the triggering row's button; tab through a finding with a theme and one without"
    why_human: "This repo's render tests assert presence, not appearance (documented project pattern); D-01's core claim is a perceptual one ('does the lift read as non-individual') that a DOM assertion cannot settle. This is UAT-202-02 (keyboard/focus-return) and UAT-202-11 (disabled trigger), both honestly dispositioned GAP — no substitute coverage in docs/UAT-SERIES.md, not fabricated as passed."
---

# Phase 202: Finding Storyline Drawer Verification Report

**Phase Goal:** Operator can open a per-finding storyline drawer from the dashboard findings table
that narrates the finding's quantum-risk story and its score-lift attribution, reusing the existing
Phase-99 narrative catalogs rather than forking a new one.
**Verified:** 2026-09-13
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths / Success Criteria

| # | Truth (ROADMAP success criterion) | Status | Evidence |
|---|---|---|---|
| 1 | Operator can open a per-finding storyline drawer directly from the findings table without navigating away | VERIFIED | `src/dashboard/src/pages/findings.tsx` renders a `Storyline` column (line 152-186) with a focusable trigger button (`aria-haspopup="dialog"`), wired to `openStoryline` which sets `selectedFinding`, driving a state-controlled `<Sheet open={!!selectedFinding}>` (line 319) rendered inline on the same page — no route change, no new page. |
| 2 | Narrative sourced from existing `ALGO_IMPACT_MAP`/`REMEDIATION_CATALOG` catalogs, no fourth generator | VERIFIED (with the documented D-07 caveat — see judgement below) | `quirk/dashboard/api/routes/storyline.py` imports `ALGO_IMPACT_MAP`, `REMEDIATION_CATALOG`, `_classify_finding` directly from `quirk/reports/content_model.py` (line 44) and composes narrative text verbatim from those tables (lines 260-265); zero new narrative strings are authored in the route or in the frontend. `grep -rn "ALGO_IMPACT_MAP\|REMEDIATION_CATALOG"` shows a single source of truth, no duplicate table under `dashboard/`. |
| 3 | Drawer displays the finding's score-lift attribution, consuming LIFT-01's number | VERIFIED (under the operator-confirmed D-01/D-08/D-09 theme-level reframing — see judgement below) | `_theme_attribution_for_finding` (`storyline.py:71-186`) computes theme slug (D-08/D-09 tie-break), theme title, `theme_score_lift` via the SAME `lift_context_for_scan` helper the roadmap surface uses, and closure counts via `item_progress()`. `FindingStorylineSections.tsx` renders these as a bordered attribution panel with the non-individual-contribution disclaimer. `test_numeric_equality_with_roadmap_surface` (real, unmocked pipeline) proves the drawer's number equals the roadmap page's number for the same slug/scan. |
| 4 | Open/close/focus interaction passes a new a11y baseline consistent with WCAG AA discipline | VERIFIED | Live re-run of `VITE_A11Y_FIXTURE=1 node tests/a11y/run-a11y.mjs` (this session, not trusted from SUMMARY) shows `PASS [findings-storyline]: no regressions (0 live)`, matching the committed `baseline-findings-storyline-default.json` (`entries: []`). Focus contract (F1-F9: open by keyboard/click, Esc closes, focus returns to exact triggering `aria-label`, no cross-finding leakage) is covered by `findings-storyline.test.tsx`'s F1-F9 vitest suite (13/13, confirmed passing in the full frontend run: 49 files / 404 passed / 2 skipped). |

**Score:** 4/4 criteria verified — 2 of the 4 (criteria 2 and 3) required accepting operator-confirmed reframings over the literal ROADMAP text; see judgement calls below. Criterion 4's live keyboard/perceptual walkthrough remains outstanding for human UAT (this is why overall status is `human_needed`, not `passed`).

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `quirk/dashboard/api/routes/storyline.py` | New auth-gated GET endpoint, catalog-sourced narrative, D-06/D-08/D-09 theme join | VERIFIED | Exists, substantive (287 lines, real logic, no stubs), registered in `quirk/dashboard/api/app.py:39,133`, wired via `include_router(storyline.router, prefix="/api")`. |
| `quirk/dashboard/api/finding_title_bridge.py` | Dashboard↔CLI title bridge (D-06) | VERIFIED | Exists; `canonical_cli_title()` used by the route; `tests/test_finding_title_bridge.py` (part of the 36-test green run) exercises it including a reachability census. |
| `quirk/dashboard/api/schemas.py::FindingStoryline` | 10-field response contract, zero optional members | VERIFIED | Present at line 168; TS mirror `FindingStoryline` in `src/dashboard/src/types/api.ts` confirmed by 202-UI-REVIEW's audited file list. |
| `src/dashboard/src/components/FindingStorylineSections.tsx` | Narrative + attribution panel, 8-state matrix | VERIFIED | Exists; covered by `finding-storyline-sections.test.tsx`, part of the green 404-test frontend run. |
| `src/dashboard/src/hooks/useFindingStoryline.ts` | Lazy fetch-on-open hook, retry/cancellation, error vs. absence separated | VERIFIED | Exists; `useFindingStoryline.test.tsx` present and green. |
| `src/dashboard/src/pages/findings.tsx` (modified) | Storyline column + Sheet wiring | VERIFIED | Trigger column, `openStoryline`, focus-return `triggerRefs`, A6 disabled-trigger guard (WR-01 fix, commit `9122fa1f`) all present and wired. |
| `src/dashboard/tests/a11y/*` (fixture, baseline, ledger) | Drawer a11y capture | VERIFIED | `fixture-storyline.json`, `baseline-findings-storyline-default.json` (0 entries), `HOOK_TARGETS`/`fixture-coverage.test.ts` entries all present; live re-run this session reproduces `PASS [findings-storyline]: no regressions (0 live)`. |
| `tests/test_dashboard_finding_storyline.py`, `tests/test_finding_title_bridge.py` | Backend regression coverage | VERIFIED | Both present, 36 tests total, all green in a live run this session. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `findings.tsx` Storyline trigger | `useFindingStoryline` hook | `openStoryline` → `useFindingStoryline(selectedFinding)` | WIRED | Confirmed by reading the file; hook consumed and its `data`/`loading`/`error`/`retry` destructured and passed to `StorylineSections`. |
| `useFindingStoryline` | `GET /api/findings/{id}/storyline` | fetch call keyed by `(finding.id, finding.title)` | WIRED | Confirmed via hook file grep and the route's required `title` query param matching D-06. |
| `storyline.py` route | `ALGO_IMPACT_MAP`/`REMEDIATION_CATALOG` | direct import, no dashboard-local copy | WIRED | `from quirk.reports.content_model import ALGO_IMPACT_MAP, REMEDIATION_CATALOG, _classify_finding` |
| `storyline.py` route | `lift_context_for_scan` (shared with roadmap surface) | direct function call, `scan.py` | WIRED, with a documented divergence risk (WR-02(b)) | Same helper function is called by both surfaces, but the ARGUMENT (a strict `scan_run_id` equality vs. the roadmap's session-bracket window resolution) can differ — see judgement below. |
| Storyline trigger | a11y drawer capture | `/api/findings` + `/api/findings/{id}/storyline` fixture handlers in `vite.config.ts`, `HOOK_TARGETS` entry | WIRED | Live re-run this session confirms the captured DOM is the opened drawer state (0 violations is a real pass on a real page, not a 404/error masquerading as clean — corroborated independently by 202-UI-REVIEW's file audit). |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|---|---|---|---|
| STORY-01 | Operator can open a per-finding storyline drawer, narrative sourced from Phase-99 catalogs, no forked generator | SATISFIED | Drawer opens in-place (criterion 1, VERIFIED); narrative composed only from `ALGO_IMPACT_MAP`/`REMEDIATION_CATALOG` (criterion 2, VERIFIED with D-07 caveat below). Still `[ ]` in REQUIREMENTS.md per explicit instruction not to flip it here — this VERIFICATION.md is the unblock artifact. |
| STORY-02 | Drawer shows the finding's score-lift attribution, consuming LIFT-01's per-item number | SATISFIED under the operator-confirmed theme-level reframing (D-01/D-08/D-09) | See criterion 3 judgement below — a literal "per-item number" was proven not implementable honestly (the number is theme-keyed, not finding-keyed); the theme-framed rendering with disclaimer is what the operator confirmed and what code delivers. Still `[ ]` in REQUIREMENTS.md per explicit instruction. |

### Anti-Patterns Found

None blocking. Scanned `storyline.py`, `FindingStorylineSections.tsx`, `findings.tsx`, `useFindingStoryline.ts` for TBD/FIXME/XXX/TODO/HACK/placeholder markers, empty-return stubs, and hardcoded-empty state: none found. All `None`/absence branches are deliberate, documented (D-07/A1-A6 state matrix), and covered by tests rather than silent stubs.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Backend storyline + bridge test suite | `.venv/bin/python -m pytest -q tests/test_finding_title_bridge.py tests/test_dashboard_finding_storyline.py` | 36 passed | PASS |
| Frontend build (statics parity) | `cd src/dashboard && npm run build` | Clean build, 8 output files, no errors | PASS |
| Frontend lint | `cd src/dashboard && npm run lint` | 0 errors, 1 pre-existing unrelated warning (`ConnectorsPanel.test.tsx`) | PASS |
| Frontend test suite | `cd src/dashboard && npm run test` | 49 files / 404 passed / 2 skipped — matches documented baseline | PASS |
| a11y drawer capture (live re-run, not trusted from SUMMARY) | `cd src/dashboard && VITE_A11Y_FIXTURE=1 node tests/a11y/run-a11y.mjs` | `PASS [findings-storyline]: no regressions (0 live)`. One unrelated pre-existing FAIL on `data-at-rest` (a documented render-dependent count drift, `deferred-items.md` item 2, not touched by this phase). | PASS (scoped to phase) |

### Full Suite

Not re-run in full (18 min) — relied on the orchestrator-provided definitive SET (`{test_hardware_staleness.py::test_hardware_matrix_not_stale}`, an unrelated 91-day calendar trip, operator-deferred) plus this session's own targeted re-runs of every file this phase touches, all green. No new failing node was introduced by anything checked in this session.

### Human Verification Required

### 1. Live-dashboard visual/keyboard walkthrough

**Test:** Load the findings page against a scanned DB. Open the drawer via keyboard on the `Storyline` trigger for (a) a finding with a theme and (b) a finding with no catalog narrative (D-07 honest absence). Tab through, confirm Esc closes, confirm focus returns to the triggering row's button.
**Expected:** The theme lift sentence never reads as "resolving this finding yields N pts" (D-01's whole design goal); A5 honest-absence reads as an intentional, worded state, not a broken/empty panel; keyboard open/close/focus-return works as F1-F9 describe.
**Why human:** This repo's own documented pattern is that render tests assert DOM presence, not perceptual/appearance correctness (see project memory `feedback_render_tests_presence_not_appearance`). D-01's central claim — "does the lift read as non-individual" — is a wording/perception question, not a DOM-structure question. This is exactly `docs/UAT-SERIES.md`'s own honest dispositions: UAT-202-02 (keyboard/focus-return) and UAT-202-11 (disabled trigger) are both `SKIP (GAP — no substitute coverage)`, not fabricated PASS. `202-VALIDATION.md`'s own Manual-Only table names this row as "OUTSTANDING for human UAT" — this verification agrees with that self-assessment rather than overriding it.

---

## Judgement Calls (explicit reasoning, not deferred to prose elsewhere)

### 1. D-01/D-09 theme-level reframing of success criterion 3

**Verdict: Accept as satisfying STORY-02 / criterion 3.** The literal ROADMAP text ("consuming
Phase 201's LIFT-01 per-item number") is genuinely not implementable honestly: `score_lift` is a
`RoadmapNode` field joined by remediation-theme `slug` (`schemas.py:501`), and one theme's lift
covers N findings by construction (`item_progress()` returns `(closed, total)` per slug, proving
non-1:1 cardinality). A literal per-finding number would have to be either (a) fabricated by
dividing the theme lift by constituent count — explicitly rejected in D-01 as manufacturing a
number the scorer never computed, and correctly identified as the same defect class as a prior
score-fabrication incident (Phase 194 IN-02) — or (b) require a new scoring capability entirely
out of this phase's scope (single-finding-resolution modeling, explicitly filed as a Deferred
Idea). Given that constraint, D-01's theme-framed rendering (theme name + conditioned lift +
closure progress + explicit non-individual-contribution disclaimer) is the most honest available
implementation, and it was put to the operator with evidence and confirmed — not silently
substituted by the executor. The code matches the decision exactly (verified by reading
`storyline.py` and the rendered `FindingStorylineSections.tsx` disclaimer). I judge this an
acceptable, well-justified deviation from the literal roadmap text rather than a gap — but it is
worth flagging to a human that the ROADMAP.md success-criterion wording itself is now stale
relative to what was built and confirmed, and a future phase or doc pass should update it to match
D-01 rather than leave the literal text uncorrected indefinitely.

### 2. D-07's usually-absent narrative against success criterion 2

**Verdict: Accept as satisfying criterion 2, with a real fidelity caveat worth naming.** The
catalogs are keyed by crypto-algorithm keyword substring match (`content_model.py:690-710`), so
the highest-volume finding classes (plaintext HTTP, legacy TLS, expired/expiring/self-signed/
untrusted-CA certs) never match and correctly resolve to honest absence (A5), not an error. The
operator's framing — "the report has no narrative for these classes either, so absence IS
consistency, not failure" — is factually accurate: this phase did not fork a new generator, and it
did not invent narrative to paper over the gap (D-05 held). Criterion 2 asks for the SOURCE of the
narrative to be the existing catalogs and for no fourth generator to exist; it does not ask for the
catalogs' own coverage to be complete. On that reading, criterion 2 is met. The caveat: a drawer
whose narrative section is absent for most of what an operator will actually see is a real product
gap relative to what "narrates the finding's quantum-risk story" evokes in the phase goal's own
language — D-07 correctly identifies that the attribution block, not the narrative, becomes the
reliably useful part of the drawer for most findings. This is a scope/expectation question the
operator already adjudicated with full evidence in front of them (D-07's amendment), so I am not
treating it as a gap, but it should not be read as "the drawer usually tells a rich story" — it
usually does not, by design, and that is the honest state to report forward.

### 3. WR-02(b) — documented-not-closed `scan_run_id` divergence

**Verdict: Not a gap for THIS phase's must-haves, but worth flagging for a human decision on
whether it should become one.** `test_scan_run_id_divergence_between_storyline_and_roadmap_surfaces`
is a genuine characterization test — it seeds a real legacy row (`scan_run_id=None`), proves the
roadmap surface resolves it via its session-bracket window fallback and returns a real non-null
lift, and proves the storyline route's `lift_context_for_scan` call (strict `scan_run_id`
equality) returns `None` for the identical finding. This is not a fabricated proof of correctness
dressed up as a test — the test's own docstring and the code comments in both `scan.py` and
`storyline.py` name the divergence honestly rather than asserting it is fixed. I verified this
independently by reading the actual filtering logic at both call sites (`storyline.py:161-169`,
`scan.py:1268-1351` vs. `scan.py:1700-1762`), not just trusting the test's docstring, and the
asymmetry is real: one path is a strict equality filter with an early `{}` return on falsy
`scan_run_id`, the other is a time-window resolution with documented fallbacks specifically because
`scan_run_id` uniformity is not guaranteed. **This does affect the numeric-equality half of
criterion 3** ("consuming LIFT-01's number," which criterion 3 and D-01 both require to agree with
the roadmap surface) for the specific, real-world case of legacy/distributed-sensor endpoints
lacking a shared `scan_run_id` — for those rows, the drawer will show honest absence while the
roadmap page shows a real number, for the same finding. That is a live, if narrow, violation of the
"same story for the same finding" principle the phase goal itself states. Because it is
scoped, tested, and explicitly out-of-band per the code review's own severity classification (a
Warning, not a Blocker, and explicitly deferred with a locking test rather than silently left
unaddressed), I am not blocking phase closure on it — but I am surfacing it here rather than
letting the green test imply resolution, per the orchestrator's explicit instruction. Recommend
filing this as a backlog item for a future phase to unify the two endpoint-resolution strategies,
distinct from the `int(delta)` truncation and `FindingItem.id` non-uniqueness items already filed.
