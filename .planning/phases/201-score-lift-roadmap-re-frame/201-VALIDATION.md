---
phase: 201
slug: score-lift-roadmap-re-frame
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-11
---

# Phase 201 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend, src/dashboard/) |
| **Config file** | `pyproject.toml` / src/dashboard vitest config |
| **Quick run command** | `.venv/bin/python -m pytest -q tests/test_score_lift.py tests/test_forward_projection_firewall.py tests/test_intelligence_roadmap.py tests/test_reports_writer.py` |
| **Full suite command** | `.venv/bin/python -m pytest -q -m ""` + `cd src/dashboard && npm run test` |
| **Estimated runtime** | quick ~60s; full ~18min |

---

## Sampling Rate

- **After every task commit:** scoped quick command + `.venv/bin/python -m compileall -q quirk`
- **After every plan wave:** the new test files + roadmap/report regression set (parity files, congruence tests); `npm run build && npm run lint && npm run test` after any `.tsx` change
- **Before verification:** full suite green (failing-node SET empty — compare SETS, never raw counts)
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

*One row per task. The ADVISORY-02 firewall test is Wave 0 and leads (201-01 Task 1).*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 201-01-T1 | 201-01 | 1 | LIFT-03 | T-201-01/02/03/04 | AST reverse-import ban over 8 guarded modules + negative control + runtime purity (evidence deep-equality, DB-session-raises, base-score invariance, no projected key on real score surfaces) | guard | `pytest tests/test_forward_projection_firewall.py -k "never_import or all_exist or negative_control or real_score_surfaces"` | ✅ | ✅ green |
| 201-01-T2 | 201-01 | 1 | LIFT-01, LIFT-02 | — | Per-item lift = real rescore delta; aggregate = one independent rescore; honest absence; SCORE-06 gate — authored failing-first, now fully green against the landed module | unit | `pytest tests/test_score_lift.py` | ✅ | ✅ green |
| 201-03-T1 | 201-03 | 1 | LIFT-04 | T-201-08 | categorize_waves deleted; console Migration Waves re-derived from build_phased_roadmap items, tolerant of stub items lacking `phase` | unit | `pytest tests/test_reports_writer.py` | ✅ | ✅ green |
| 201-03-T2 | 201-03 | 1 | LIFT-04 | T-201-09 | 8 test files' patch decorators removed with no mock-parameter shift regression | unit | `pytest tests/test_reports_writer.py tests/test_cmvp_report_column.py tests/test_cbom_vex.py tests/test_report_template_sandbox.py tests/test_report_injection_hardening.py tests/test_report_branding_cli.py tests/test_burndown_writer_load.py tests/test_cbom_integration.py` | ✅ | ✅ green |
| 201-03-T3 | 201-03 | 1 | LIFT-04 | T-201-10 | One categorization source across CLI/HTML/DOCX/dashboard; categorize_waves stays deleted | parity | `pytest tests/test_roadmap_categorization_unification.py` | ✅ | ✅ green |
| 201-02-T1 | 201-02 | 2 | LIFT-01, LIFT-03 | T-201-02/05/06 | 9 slug-keyed evidence deltas over deep copies; scoring.py/roadmap.py unchanged; firewall runtime legs green | unit + guard | `pytest tests/test_score_lift.py -k "not aggregate and not additiv" tests/test_forward_projection_firewall.py` | ✅ | ✅ green |
| 201-02-T2 | 201-02 | 2 | LIFT-02 | T-201-07 | Aggregate = ONE rescore of an all-resolved copy; strict `sum(lifts) > aggregate` on a clamp-binding fixture | unit | `pytest tests/test_score_lift.py tests/test_forward_projection_firewall.py tests/test_intelligence_roadmap.py tests/test_remediation_advisory_guard.py` | ✅ | ✅ green |
| 201-04-T1 | 201-04 | 3 | LIFT-05 | T-201-11 | RoadmapNode.score_lift + top-level ScanLatestResponse.projected_score as additive Optionals; ScoreData untouched; TS mirrors `number \| null` | schema unit | `python -c "<schema field assertion>"` + `cd src/dashboard && npm run lint` | ✅ | ✅ green |
| 201-04-T2 | 201-04 | 3 | LIFT-01, LIFT-03, LIFT-05 | T-201-12/13/14/15 | Lifts joined by slug in `_derive_roadmap`; projection at the endpoint with `profile=stored_profile`, no weights; failure degrades to absence with HTTP 200 | integration | `pytest tests/test_scan_roadmap_score_lift.py tests/test_forward_projection_firewall.py` | ✅ | ✅ green |
| 201-05-T1 | 201-05 | 3 | LIFT-05 | — | RoadmapItem.score_lift / ExecContent.projected_score appended with defaults; congruence guard and all existing callers untouched | unit + parity | `pytest tests/test_congruence_guard.py tests/test_cross_surface_parity.py tests/test_report_render_parity.py tests/test_score_render_parity.py` | ✅ | ✅ green |
| 201-05-T2 | 201-05 | 3 | LIFT-01, LIFT-02, LIFT-03, LIFT-05 | T-201-16/17/18/19 | Lifts attached outside build_phased_roadmap with each caller's own profile/weights; CLI markdown + scorecard render locked copy; intelligence-JSON `score` allowlist unchanged | unit | `pytest tests/test_score_lift_report_surfaces.py tests/test_reports_writer.py tests/test_roadmap_categorization_unification.py tests/test_forward_projection_firewall.py tests/test_intelligence_roadmap.py` | ✅ | ✅ green |
| 201-06-T1 | 201-06 | 4 | LIFT-05 | T-201-20/21/22 | Lift badge + Projected Score card per UI-SPEC; absence renders nothing; verbatim disclaimer; no chart | vitest | `cd src/dashboard && npm run test -- roadmap-score-lift && npm run lint` | ✅ | ✅ green |
| 201-06-T2 | 201-06 | 4 | LIFT-05 | T-201-23 | Rebuilt statics committed and proven to contain the new copy | build gate | `cd src/dashboard && npm run build && npm run lint && npm run test` | ✅ | ✅ green |
| 201-06-T3 | 201-06 | 4 | LIFT-05 | T-201-20/21 | Operator-confirmed placement, tone, absence, and cross-surface number agreement | human-verify | (manual — see Manual-Only Verifications) | n/a | ✅ green (operator-approved 2026-09-12) |
| 201-07-T1 | 201-07 | 4 | LIFT-05 | T-201-24/26/27 | HTML + DOCX roadmap sections render lift/projection/advisory, read-only, `\| sanitize` preserved, raw-dict path safe | unit | `pytest tests/test_html_renderer_roadmap_section.py tests/test_report_render_parity.py tests/test_report_coverage_parity.py tests/test_report_injection_hardening.py tests/test_report_template_sandbox.py` | ✅ | ✅ green |
| 201-07-T2 | 201-07 | 4 | LIFT-02, LIFT-05 | T-201-25 | Four-surface numeric equality for one scan + surface-level non-additivity, with the check proven able to fail | parity | `pytest tests/test_score_lift_cross_surface_numbers.py tests/test_cross_surface_parity.py tests/test_score_lift.py tests/test_forward_projection_firewall.py` | ✅ | ✅ green |
| 201-08-T1 | 201-08 | 5 | LIFT-01..LIFT-05 | T-201-30 | Docs explain the real-rescore basis, honest absence, non-additivity, the advisory posture, and the Migration Waves semantic change | doc gate | `grep -c "Projected score if all items resolved" docs/report-interpretation.md` and the sibling greps | ✅ | ✅ green |
| 201-08-T2 | 201-08 | 5 | LIFT-01..LIFT-05 | T-201-28 | UAT Series 201, 11 cases, every Result box dispositioned; citations `--collect-only` resolvable | gate | `pytest tests/test_uat_zero_undispositioned_gate.py tests/test_uat_disposition_integrity.py tests/test_error_codes_freshness.py` | ✅ | ✅ green |
| 201-08-T3 | 201-08 | 5 | LIFT-01..LIFT-05 | T-201-29/31/32 | HORIZON BACK-51 closed by recorded decision; vault synced byte-for-byte; validation closed before the ROADMAP flip; no mutating GSD verb | gate | vault `diff <(tail -n +9 ...)` chain + `pytest -q -m ""` SET comparison + `npm run test` | ✅ | ✅ green (see `deferred-items.md`: 8-node failing SET, all pre-existing/out-of-scope — 7 same-class-as-TRIAGE-149 Playwright order-pollution on an untouched 201-05 test file, 1 unrelated calendar-time hardware-catalog staleness trip; zero nodes touch anything this plan modified) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_forward_projection_firewall.py` — ADVISORY-02 forward-projection firewall (leads Wave 0, plan 201-01 Task 1; RED-verified live against `quirk/intelligence/scoring.py`)
- [ ] `tests/test_score_lift.py` — LIFT-01/02 unit spec, authored failing-first (plan 201-01 Task 2)
- [ ] `src/dashboard/src/pages/__tests__/roadmap-score-lift.test.tsx` — LIFT-05 badge/card/absence (plan 201-06 Task 1; vitest cannot land earlier because it asserts against the payload fields created in 201-04)
- [ ] No framework install needed — pytest and vitest are already present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard lift badge + Projected Score card visual appearance, placement, and tone | LIFT-05 | This repo's render tests assert presence, not appearance; vitest citations also cannot satisfy the UAT integrity gate's execution leg | Plan 201-06 Task 3's checkpoint: load the dashboard roadmap page against a scanned DB, confirm badge placement on the existing badge row in `--ds-ok` tone, no badge for process items, the Projected Score card directly above Remediation Burndown with the verbatim advisory and no chart, the real readiness score unmoved, and the CLI report's numbers matching the dashboard for the same items |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-09-12 — all 20 Per-Task Verification Map rows re-run green this session
(commands re-executed live, not carried forward from stale plan-time evidence); the one Manual-Only
row is discharged by plan 201-06's operator-approved live walkthrough (verbatim "approved",
2026-09-12); the phase's full backend (`pytest -q -m ""`) and frontend (`npm run test`) suites were
re-run in full as part of this close-out — see `201-08-SUMMARY.md` for the failing-node SET
comparison against the empty pre-phase baseline.
