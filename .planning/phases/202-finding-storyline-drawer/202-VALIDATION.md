---
phase: 202
slug: finding-storyline-drawer
status: in_progress
nyquist_compliant: true
wave_0_complete: false
created: 2026-09-12
---

# Phase 202 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
>
> **Authored at plan-review time, not at close-out.** The plan-checker blocked Phase 202 because this
> file was missing from the plan-creation commit (`4d440579`), diverging from Phase 201's precedent
> where `201-VALIDATION.md` landed in the same commit as its 8 plans (`c303d658`). The point of the
> artifact is to be a live map that tasks are checked off against *as waves execute* — deferring it to
> the close-out plan would leave waves 1-4 running without one. Status rows start unchecked and are
> flipped to green by the executor that discharges each task.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend, `src/dashboard/`) + `@axe-core/puppeteer` 4.11.3 (a11y harness) |
| **Config file** | `pyproject.toml` / `src/dashboard` vitest config / `src/dashboard/tests/a11y/run-a11y.mjs` |
| **Quick run command** | `.venv/bin/python -m pytest -q tests/test_finding_title_bridge.py tests/test_dashboard_finding_storyline.py` |
| **Full suite command** | `.venv/bin/python -m pytest -q -m ""` + `cd src/dashboard && npm run test` + `npm run a11y` |
| **Estimated runtime** | quick ~30s; full ~18min backend, ~30s frontend, a11y ~2min |

**Interpreter:** always `.venv/bin/python`, never bare `python` — the system interpreter lacks `sslyze`
and silently produces 9 phantom connector failures in the full suite.

---

## Sampling Rate

- **After every task commit:** scoped quick command + `.venv/bin/python -m compileall -q quirk`
- **After every plan wave:** the wave's new test files plus the dashboard-API regression set; and after
  ANY `.tsx` change, `npm run build && npm run lint && npm run test` from `src/dashboard/` with the
  rebuilt statics under `quirk/dashboard/static/` committed alongside the source
- **Before verification:** full suite green — compare failing-node **SETS**, never raw pass counts.
  The expected inherited SET is `{tests/test_hardware_staleness.py::test_hardware_matrix_not_stale}`,
  a 91-day calendar-time staleness trip unrelated to this phase and operator-deferred with a record
  (`.planning/todos/pending/hardware-matrix-staleness-reverify.md`). Anything beyond that one node is
  this phase's to explain.
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

*One row per task, 22 rows across 8 plans. Wave 1 is the gating wave: 202-01's title bridge is the
join every theme lookup passes through, so nothing downstream is trustworthy until its gate is green.*

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|--------|
| 202-01-T1 | 202-01 | 1 | STORY-01, STORY-02 (D-06) | Both title vocabularies re-verified class by class on FIRING CONDITIONS, not title similarity; bridge ledger authored; the planner's own hypothesis table treated as falsifiable, with agreement or disagreement with RESEARCH's "~5 diverge / 3 match" stated either way | unit | `.venv/bin/python -m pytest -q tests/test_finding_title_bridge.py` | green |
| 202-01-T2 | 202-01 | 1 | STORY-01, STORY-02 (D-06) | Run-time source scan regenerates BOTH occurrence sets from installed source every run, with a minimum-count guard against a vacuously-matching regex, plus RED demonstrations in both directions (delete a ledger entry; add a fake title) with transcripts in the SUMMARY | guard | `.venv/bin/python -m pytest -q tests/test_finding_title_bridge.py` | green |
| 202-01-T3 | 202-01 | 1 | STORY-02 (D-07, D-08) | Constituency reachability census derived from source, not hand-listed; consumed by 202-05 so theme-selection branches are written against data rather than a guess | unit | `.venv/bin/python -m pytest -q tests/test_finding_title_bridge.py -k reachability` | green |
| 202-02-T1 | 202-02 | 1 | STORY-01, STORY-02 (D-01, D-06, D-07) | `FindingStoryline` contract with zero optional (`?:`) members; `FindingItem.id` corrected from `id?: number` to `number \| null` because it is the fetch key — the 201-UI-E2 class at the exact point the A6 disabled-trigger decision is made | type gate | `cd src/dashboard && npm run build && npm run lint` | green |
| 202-02-T2 | 202-02 | 1 | STORY-01 (D-02, D-07) | `useFindingStoryline` hook: retry, cancellation, and **error separated from absence** — a failed fetch reads differently from a genuinely absent catalog entry | vitest | `cd src/dashboard && npm run test -- use` | green |
| 202-03-T1 | 202-03 | 2 | STORY-01 (D-06) | Shared single-finding lookup extracted from `_derive_findings` so the route and the list cannot diverge on what a finding is | unit | `.venv/bin/python -m pytest -q tests/test_dashboard_api.py tests/test_finding_engine_parity.py tests/test_dashboard_finding_segment_field.py tests/test_dashboard_empty_state_contract.py` | green |
| 202-03-T2 | 202-03 | 2 | STORY-01 (D-02, D-05, D-06) | Auth-gated route keyed by `(id, title)`; narrative sourced ONLY from the Phase-99 catalogs; no new narrative content written | integration | `.venv/bin/python -m pytest -q tests/test_dashboard_finding_storyline.py` | green |
| 202-03-T3 | 202-03 | 2 | STORY-01 (D-06, D-07) | Disambiguation proven (two findings sharing one endpoint id resolve to different storylines), narrative presence AND absence, auth gating, 422 on a bad param, and a FIXED 500 detail string that never leaks a path | integration | `.venv/bin/python -m pytest -q tests/test_dashboard_finding_storyline.py tests/test_dashboard_api.py tests/test_finding_engine_parity.py` | green |
| 202-04-T1 | 202-04 | 2 | STORY-01, STORY-02 (D-01, D-07) | `StorylineSections`: narrative section, attribution block rendered LAST as a bordered panel (never a header chip), loading and error states; A5 built as a first-class state because D-07 makes it the common path | vitest | `cd src/dashboard && npm run test -- finding-storyline-sections` | green |
| 202-04-T2 | 202-04 | 2 | STORY-01, STORY-02 (D-01) | Eight states parametrised off the UI-SPEC State Matrix; Invariant 1 (the `<p>` matching `/\+\d/` also matches `/when all/`); Invariant 2 (disclaimer co-presence across all enumerated states); **Invariant 3 division trip-wire** — `theme_score_lift: 7, theme_finding_count: 2` must render `7` and `2` while `3.5` and `3` appear nowhere; plus the `4.27` → `+4.3` formatting regression | vitest | `cd src/dashboard && npm run test -- finding-storyline-sections && npm run lint` | green |
| 202-05-T1 | 202-05 | 3 | STORY-02 (D-01) | Shared lift-context helper so the drawer and the roadmap page cannot diverge on the same number | unit | `.venv/bin/python -m pytest -q tests/test_dashboard_api.py tests/test_scan_roadmap_score_lift.py tests/test_score_lift.py tests/test_dashboard_finding_storyline.py` | unchecked |
| 202-05-T2 | 202-05 | 3 | STORY-02 (D-01, D-08, D-09) | Fingerprint join; D-08 tie-break prefers the specific theme over the `high-impact-findings` catch-all; **D-09**: when the catch-all is the ONLY theme it IS rendered, because suppressing it asserts a false absence about a finding that genuinely constitutes a real theme with a real lift; `finding_position` returns `null` unconditionally per A4 and no ordinal is computed at all | unit | `.venv/bin/python -m pytest -q tests/test_dashboard_finding_storyline.py` | unchecked |
| 202-05-T3 | 202-05 | 3 | STORY-02 (D-01, D-08, D-09) | Tie-break test derives the overlap partition from `REMEDIATION_CONSTITUENCY` at run time with a non-vacuity guard — **no literal slug string as the expected winner**, per D-08's explicit prohibition on hand-maintained lists; graceful degradation when fingerprint rows are absent (A3, not a 500); numeric equality with the roadmap surface | unit + parity | `.venv/bin/python -m pytest -q tests/test_dashboard_finding_storyline.py tests/test_scan_roadmap_score_lift.py tests/test_remediation_persist.py tests/test_score_lift.py tests/test_dashboard_api.py` | unchecked |
| 202-06-T1 | 202-06 | 3 | STORY-01, STORY-02 (D-03, D-07) | Focusable `Storyline` trigger column with `aria-haspopup="dialog"` — this ADDS a keyboard path where the bare `<TableRow onClick>` had none, which is what makes success criterion 4 achievable at all; A6 disabled state when no stable id exists | vitest | `cd src/dashboard && npm run test` | unchecked |
| 202-06-T2 | 202-06 | 3 | STORY-01 (D-03) | Sheet extended: `SheetDescription` rendered (F8 — Radix's `DescriptionWarning` is unguarded by `NODE_ENV` in `@radix-ui/react-dialog@1.1.15`, so the console gate fails without it; an allowlist entry is NOT the fix), responsive width replacing the hardcoded `style={{width: 480}}`, and a `flex-1 overflow-y-auto min-h-0` scroll region | vitest | `cd src/dashboard && npm run test && npm run lint` | unchecked |
| 202-06-T3 | 202-06 | 3 | STORY-01, STORY-02 (D-03) | Focus contract F1-F9 integration tests including F6 focus-return by exact `aria-label` across all three close paths and both open modalities; cross-finding leakage ruled out; **rebuilt statics committed with the source** | vitest + build gate | `cd src/dashboard && npm run build && npm run lint && npm run test` | unchecked |
| 202-07-T1 | 202-07 | 4 | STORY-01, STORY-02 (D-04) | `/api/findings` fixture handler added to `a11yFixture()` in `src/dashboard/vite.config.ts` **plus** its `HOOK_TARGETS` entry in `fixture-coverage.test.ts` — without the handler the request 404s and the capture silently baselines the ERROR state; the fixture payload carries `finding_position: null` so the baselined DOM is one that can actually occur | gate | `cd src/dashboard && npm run test -- fixture-coverage` | unchecked |
| 202-07-T2 | 202-07 | 4 | STORY-01, STORY-02 (D-04) | Per-route interaction step opens the drawer; **logged** (never silent) no-op for the `empty`/`loading` variants, since a silent selector miss is indistinguishable from a broken trigger; `accepted-violations-freshness.test.ts` derivation extended to include each entry's `interaction.slug` programmatically, closing the ledger-blindness hole where a baseline under a non-route slug would be invisible to `ACCEPTED-VIOLATIONS.md` | gate | `cd src/dashboard && npm run test -- fixture-coverage && npm run a11y` | unchecked |
| 202-07-T3 | 202-07 | 4 | STORY-01, STORY-02 (D-04) | **BLOCKING human-verify checkpoint.** Baselines and ledger regenerated, three variant gates run, and the captured DOM confirmed to be the opened drawer rather than a 404/error state. The freshness test must be observed failing as STALE before regeneration, with that transcript in the SUMMARY as proof the derivation is live rather than vacuous | human-verify | (manual — see Manual-Only Verifications) | unchecked |
| 202-08-T1 | 202-08 | 5 | STORY-01, STORY-02 (D-01, D-07, D-08) | Docs explain the theme framing, that the lift is NOT an individual contribution, honest absence as the common case, and the one-theme rule including D-09's catch-all-only branch | doc gate | `grep -c` chain per the plan's acceptance criteria | unchecked |
| 202-08-T2 | 202-08 | 5 | STORY-01, STORY-02 | UAT Series 202 — every case with exactly ONE checked Result box; `GAP — no substitute coverage` is a valid honest disposition and must never be inflated to PASS; DEFERRED pytest citations `--collect-only` resolvable | gate | `.venv/bin/python -m pytest -q tests/test_uat_zero_undispositioned_gate.py tests/test_uat_disposition_integrity.py tests/test_error_codes_freshness.py` | unchecked |
| 202-08-T3 | 202-08 | 5 | STORY-01, STORY-02 | Vault sync, phase note, backlog todos filed (incl. the `FindingItem.id` non-uniqueness trap for future per-finding features), **this file closed green BEFORE or in the same commit as the ROADMAP change**, and the permitted checkbox flips only — the phase heading is NOT flipped here (ARTIFACT-01 needs `202-VERIFICATION.md`, which the orchestrator's verifier produces) | gate | `.venv/bin/python -m pytest -q -m ""` SET comparison + `npm run test` + vault diff chain | unchecked |

*Status legend: unchecked · green · red · flaky. Rows are flipped by the executor that discharges the
task. **Do not write a verification command that greps this file for an unchecked-status glyph** — a
row containing the glyph in its own command text can never reach zero (self-referentially unclosable,
recorded against phases 157/158/159). Verify by frontmatter key plus a count of green rows.*

---

## Wave 0 / Gating Requirements

Phase 202 has no separate Wave 0; **Wave 1 is the gating wave** and 202-01 is its critical path.

- [ ] `tests/test_finding_title_bridge.py` — the dashboard↔CLI title bridge, its run-time source-scan
      gate, and the constituency reachability census (202-01, all three tasks). Every theme lookup in
      the phase joins through this; nothing downstream is trustworthy until it is green.
- [ ] `tests/test_dashboard_finding_storyline.py` — authored in 202-03, extended by 202-05
- [ ] `src/dashboard/src/components/__tests__/finding-storyline-sections.test.tsx` — authored in 202-04
- [ ] No framework install needed — pytest, vitest, and `@axe-core/puppeteer` are all already present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The a11y capture baselines the **opened drawer**, not a 404 or error state | STORY-01, STORY-02 (D-04, success criterion 4) | An axe capture reports violations in whatever DOM it finds. A fixture miss produces a clean-looking baseline of the wrong page — the "covered but blind" failure class Phase 185's D-14 guard exists to prevent. Only a human reading the captured DOM can confirm it is the drawer | 202-07 Task 3: regenerate baselines and the ledger, run the three variant gates, then inspect the captured DOM for the drawer's own markers (`SheetDescription` text, the attribution panel, the `Storyline` trigger's `aria-label`). Confirm the freshness test was observed failing as STALE before regeneration |
| Drawer visual appearance, attribution framing, and keyboard feel against a live dashboard | STORY-01, STORY-02 (D-01, D-07) | This repo's render tests assert presence, not appearance — and D-01's whole problem is whether the theme lift *reads* as non-individual, which is a perceptual question a DOM assertion cannot settle | Load the findings page against a scanned DB, open the drawer on a finding with a theme and one without, confirm the lift never reads as this finding's own contribution, confirm A5 absence reads as honest rather than broken, and tab through: open by keyboard, Esc closes, focus returns to the triggering row's button |

---

## Validation Sign-Off

- [x] All 22 tasks have an automated verify command or a named Manual-Only row
- [x] Sampling continuity: no 3 consecutive tasks without an automated verify
- [x] Gating-wave requirements named (202-01's bridge gate leads)
- [x] No watch-mode flags in any command
- [x] Feedback latency < 60s for the scoped commands
- [x] `nyquist_compliant: true` set in frontmatter
- [ ] All Per-Task Verification Map rows green
- [ ] Both Manual-Only rows discharged
- [ ] Full-suite failing-node SET equals the inherited one-node set, or the difference is explained

**Approval:** pending — not approved. This file is authored at plan-review time (2026-09-12) to satisfy
the plan-checker's dimension-8e gate. It is closed green by 202-08 Task 3, which must confirm every row
above rather than author them fresh.
