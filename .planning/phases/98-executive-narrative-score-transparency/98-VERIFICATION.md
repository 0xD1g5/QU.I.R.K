---
phase: 98-executive-narrative-score-transparency
verified: 2026-05-24T15:10:00Z
status: passed
score: 11/11
overrides_applied: 0
human_verification_result: "passed 2026-05-24 — both items confirmed (see 98-HUMAN-UAT.md). HTML↔PDF parity verified via real OQS scan + QUIRK Playwright render; congruence guard verified fail-closed via real write_reports pipeline (EXCELLENT band + 1 CRITICAL → ReportCongruenceError, no executive files written). Non-blocking UX note: run_scan.py surfaces the guard as a traceback rather than a clean one-liner."
human_verification:
  - test: "Run quirk scan on a fixture target and open the generated HTML report in a browser. Export to PDF (or use the auto-generated PDF). Confirm: (1) Readiness Assessment narrative appears before the score card, (2) Priority Business Risks section is present, (3) rollup formula 'How this score was computed' block is present, (4) roadmap items show EFFORT/IMPACT labels. Compare PDF and HTML for visual parity."
    expected: "PDF and HTML carry identical narrative lead text, identical Priority Business Risks entries, identical rollup-formula prose, and identical roadmap structure. No content is present in HTML that is absent in PDF or vice versa."
    why_human: "PDF rendering requires Playwright (not available in CI). Structural single-source guarantee is automated via D-03/test_cross_surface_parity.py, but visual layout parity and PDF output fidelity require a human with a browser."
  - test: "Trigger the congruence guard by constructing a scan result with an EXCELLENT/GOOD/MODERATE headline band coexisting with CRITICAL findings (e.g., mock or craft a score_raw with rating='GOOD' and a CRITICAL finding), then run write_reports and confirm the CLI aborts with a ReportCongruenceError message before writing any executive-summary file."
    expected: "CLI prints the congruence error message and no executive-summary-*.md file is created in the output directory. The message reads: \"Report generation halted: executive headline 'GOOD' is inconsistent with N CRITICAL finding(s). Review findings before generating the report.\""
    why_human: "The automated test (test_guard_blocks_report_generation) covers this path via mocks. A consultant wants to see it fire on a real scan invocation with a crafted fixture scan result, which requires running the full CLI."
---

# Phase 98: Executive Narrative + Score Transparency Verification Report

**Phase Goal:** A consultant running any output surface (CLI, HTML, PDF) receives a CISO-readable executive report that leads with the readiness story, shows a prioritized remediation roadmap, and surfaces the full subscore decomposition — all three surfaces carry identical content.
**Verified:** 2026-05-24
**Status:** human_needed (all automated checks pass; 2 items need human/live testing)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | build_exec_content() returns ExecContent with narrative, top_risks, roadmap_items (with effort/impact + within-bucket ordering), subscores (all six pillars), and sev_counts | VERIFIED | content_model.py:423-510; test_exec_content_model.py::test_subscores_all_keys_present, test_roadmap_priority_ordering, test_top_risks_populated — all pass |
| 2 | _check_congruence raises ReportCongruenceError when EXCELLENT/GOOD/MODERATE band coexists with any CRITICAL finding; does not raise for FAIR/POOR | VERIFIED | content_model.py:279-300; _BAND_CRITICAL_THRESHOLD: EXCELLENT/GOOD/MODERATE→0, FAIR/POOR→None; test_congruence_guard.py::test_good_band_with_critical_raises, test_fair_band_with_critical_ok — pass |
| 3 | Top-risks sentences are derived from the static ALGO_IMPACT_MAP (crypto-class → impact-band map), not per-finding prose | VERIFIED | content_model.py:95-155 ALGO_IMPACT_MAP; _build_top_risks():332-359 sources only from map values; no per-finding text in RiskItem.impact_sentence |
| 4 | Roadmap items within each NOW/NEXT/LATER bucket are ordered high-impact/low-effort first (priority_score = IMPACT_RANK * (4 - EFFORT_RANK)) | VERIFIED | content_model.py:392-403 _sort_roadmap_items(); test_exec_content_model.py::test_roadmap_priority_ordering passes |
| 5 | write_reports() builds one ExecContent and passes it to both build_exec_markdown() and render_html_report() before any file I/O; congruence guard fires here | VERIFIED | writer.py:165-169 build_exec_content() called at line 165; compat wrapper at line 173; exec_md at line 209; render_html_report at line 224. Guard fires before any executive file is written. test_congruence_guard.py::test_guard_blocks_report_generation passes. |
| 6 | CLI markdown opens with a Readiness Assessment narrative prose block BEFORE any finding table, and includes a Priority Business Risks section and effort/impact-labelled roadmap items | VERIFIED | executive.py:181-191 ## Readiness Assessment inserted after ## Executive Summary; Priority Business Risks at line 232-239; roadmap items with effort/impact at lines 306-321. test_exec_narrative_ordering.py::test_narrative_before_findings_cli passes. |
| 7 | HTML report renders a .narrative-block before the score card, a .risks-list, the rollup-formula prose, and .priority-label spans on roadmap items | VERIFIED | report.html.j2:197-207 narrative-block before h2 Quantum Readiness Score at line 209; risks-list at lines 242-252; rollup-formula at lines 234-237; priority-label at line 306. test_exec_narrative_ordering.py::test_narrative_before_table_html, test_risks_list_in_html, test_rollup_formula_in_html, test_priority_labels_in_html_roadmap — all pass. |
| 8 | Score Decomposition + rollup sourced from exec_content.subscores in HTML (D-07 extend, not rebuild) | VERIFIED | html_renderer.py:200 subscores_ctx = exec_content.subscores; template line 221 renders subscores; backward-compat path at line 212 falls back to score.get('subscores') only when exec_content is None. |
| 9 | Finding-derived text in new markdown cells is wrapped with md_cell; finding-derived text in new template content pipes through | sanitize | VERIFIED | executive.py:189 md_cell applied to narrative_drivers; lines 237, 315-316 md_cell on risk/roadmap items. report.html.j2:204 narrative_drivers | sanitize. WR-01 fix confirmed at executive.py:189. |
| 10 | A single ExecContent instance passed to both build_exec_markdown() and render_html_report() produces identical narrative-lead text and identical top-risks count/labels in both surfaces | VERIFIED | test_cross_surface_parity.py::test_narrative_content_parity, test_top_risks_parity — both pass. Same instance assertion confirmed in tests. |
| 11 | docs/UAT-SERIES.md reflects the new executive narrative / top-risks / roadmap-priority / rollup-formula sections and is synced to Obsidian vault | VERIFIED | grep confirms "readiness assessment", "priority business risk", "how this score was computed" in docs/UAT-SERIES.md; /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md exists. |

**Score:** 11/11 truths verified (automated)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/reports/content_model.py` | ExecContent/RiskItem/RoadmapItem dataclasses, ALGO_IMPACT_MAP, EFFORT_IMPACT_MAP, build_exec_content(), _check_congruence(), ReportCongruenceError | VERIFIED | All classes and functions present; `class ExecContent`, `class ReportCongruenceError`, both maps defined; __all__ exports all public names |
| `tests/test_exec_content_model.py` | Unit coverage for build_exec_content shape, top-risks, roadmap ordering, subscores pass-through | VERIFIED | test_top_risks_populated, test_roadmap_priority_ordering, test_subscores_all_keys_present all pass |
| `tests/test_congruence_guard.py` | Unit + integration coverage for _check_congruence band/severity cases + guard integration | VERIFIED | test_good_band_with_critical_raises, test_fair_band_with_critical_ok, test_guard_blocks_report_generation all pass |
| `quirk/reports/writer.py` | build_exec_content seam before compat wrapper; exec_content passed to both renderers | VERIFIED | Line 165 < line 173 (compat); exec_content kwarg in render_html_report call at line 232 |
| `quirk/reports/executive.py` | build_exec_markdown(..., exec_content=...) consuming shared model; narrative before findings | VERIFIED | exec_content keyword at line 119; ## Readiness Assessment inserted before ## Quantum Readiness Score; ## Interpretation removed |
| `quirk/reports/html_renderer.py` | render_html_report(..., exec_content=...) routing narrative/risks/roadmap/subscores | VERIFIED | exec_content kwarg at line 155; subscores/narrative/top_risks/roadmap sourced from exec_content when provided |
| `quirk/reports/templates/report.html.j2` | .narrative-block, .risks-list, .rollup-formula, .priority-label additions | VERIFIED | 14 occurrences of these class names across CSS and HTML body confirmed by grep |
| `tests/test_exec_narrative_ordering.py` | Ordering + presence tests for CLI and HTML | VERIFIED | All 5 VALIDATION.md node IDs exist and pass |
| `tests/test_cross_surface_parity.py` | Cross-surface content identity gate (EXEC-04 corroboration) | VERIFIED | test_narrative_content_parity, test_top_risks_parity both pass |
| `docs/UAT-SERIES.md` | Updated UAT cases for Phase 98 report sections | VERIFIED | UAT-98-01..07 present; Last Updated 2026-05-24 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| build_exec_content | _check_congruence | called internally before returning ExecContent | VERIFIED | content_model.py:491 `_check_congruence(score_band, sev_counts)` called before return at line 500 |
| build_exec_content | score_raw['score'] | canonical key, NOT compat 'total' | VERIFIED | content_model.py:452 `score_raw.get("score", 0)` |
| writer.py:write_reports | build_exec_content | called at line 165, before compat wrapper at line 173 | VERIFIED | Line ordering confirmed; build_exec_content at 165, compat wrapper at 173 |
| html_renderer.py | exec_content.subscores | subscores_ctx = exec_content.subscores | VERIFIED | html_renderer.py:200 |
| report.html.j2 | exec_content fields | narrative-block / risks-list / priority-label rendering | VERIFIED | All four class patterns present in template |
| tests/test_cross_surface_parity.py | build_exec_content | one instance shared to both renderers, asserted identical | VERIFIED | Pattern confirmed in test file |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `quirk/reports/executive.py` | exec_content.narrative_lead | build_exec_content() from score_raw["rating"] → _NARRATIVE_LEADS map | Yes — static map keyed on real scoring band | FLOWING |
| `quirk/reports/executive.py` | exec_content.top_risks | _build_top_risks(findings) → ALGO_IMPACT_MAP | Yes — real findings drive map lookup | FLOWING |
| `quirk/reports/html_renderer.py` | subscores_ctx | exec_content.subscores (D-07) | Yes — sourced from compute_readiness_score() output | FLOWING |
| `quirk/reports/templates/report.html.j2` | narrative_lead, top_risks, roadmap_now/next/later | exec_content fields passed via template.render() context | Yes — real ExecContent instance from writer.py seam | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 23 Phase 98 tests pass | `python -m pytest tests/test_exec_content_model.py tests/test_congruence_guard.py tests/test_exec_narrative_ordering.py tests/test_cross_surface_parity.py -x -q` | 23 passed in 0.26s | PASS |
| content_model.py imports cleanly | `python -c "import quirk.reports.content_model as m; print(m.build_exec_content, m._check_congruence)"` | verified via test suite | PASS |
| Template markers present | grep narrative-block/risks-list/rollup-formula/priority-label in report.html.j2 | 14 matches | PASS |
| build_exec_content called before compat wrapper | grep line numbers in writer.py | line 165 < line 173 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| EXEC-01 | 98-01, 98-02 | Executive summary opens with plain-language readiness narrative before finding tables | SATISFIED | ## Readiness Assessment inserted before ## Findings Overview in executive.py; test_narrative_before_findings_cli passes |
| EXEC-02 | 98-01, 98-02 | Executive summary surfaces top prioritized risks framed by business impact | SATISFIED | Priority Business Risks section with ALGO_IMPACT_MAP-derived labels; test_risks_list_in_html passes |
| EXEC-03 | 98-01, 98-02 | Report includes prioritized remediation roadmap with effort/impact | SATISFIED | RoadmapItem.effort/impact fields; D-04 within-bucket ordering; priority-label in template; test_priority_labels_in_html_roadmap passes |
| EXEC-04 | 98-02, 98-03 | Consistent content across CLI markdown, HTML, and PDF | SATISFIED (automated; PDF visual needs human) | D-03 structural single-source; test_cross_surface_parity.py::test_narrative_content_parity and test_top_risks_parity pass; PDF visual parity deferred to human UAT (Playwright-gated) |
| TRANS-01 | 98-01, 98-02 | Six-pillar subscore decomposition shown against budget | SATISFIED | Score Decomposition table in executive.py and report.html.j2; all six pillars present; test_subscores_all_keys_present passes |
| TRANS-02 | 98-02 | Report explains how overall score is computed (÷1.5 rollup) | SATISFIED | rollup-formula block in report.html.j2 lines 234-237; "How this score was computed" + "Six pillar subscores" text confirmed by test_rollup_formula_in_html |
| TRANS-03 | 98-01, 98-02 | Headline score and severity language are consistent — no contradiction | SATISFIED | _check_congruence() guard; test_good_band_with_critical_raises passes; test_guard_blocks_report_generation confirms guard fires before file I/O |

All 7 Phase 98 requirements satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| quirk/reports/html_renderer.py | 173 | Band recomputed via _score_band() instead of sourcing exec_content.score_band (WR-04) | Warning | If _score_band() thresholds diverge from scoring._rating() in a future change, HTML could display a band the congruence guard never validated. Does NOT affect current parity — thresholds are identical. Documented in 98-REVIEW.md. |
| quirk/reports/templates/report.html.j2 | 230 | Rollup numerator uses `subscores.values() \| sum` (all keys) vs CLI uses named-key sum (WR-03) | Warning | If a 7th subscore is ever added, HTML "How this score was computed" numerator would silently diverge from CLI markdown. Does NOT undermine current parity — exactly 6 keys emitted today. Documented in 98-REVIEW.md. |
| quirk/reports/executive.py + html_renderer.py | 189-193, 210-218 | Backward-compat exec_content=None paths bypass congruence guard (WR-05) | Warning | Public functions callable without exec_content can render contradictory reports. write_reports() always passes exec_content; production path is guarded. Documented in 98-REVIEW.md. |

No TBD/FIXME/XXX debt markers found in phase-modified files.

**CR-01 status:** The raw_sum malformed-subscore crash was fixed in content_model.py:461-467 with the defensive numeric-only sum (`isinstance(v, (int, float)) and not isinstance(v, bool)`). The CR-01 blocker from 98-REVIEW.md is resolved in the submitted code.

**WR-01/WR-02 status:** Both fixed. WR-01 (md_cell on narrative_drivers in executive.py) fixed at line 189. WR-02 (dict repr fallback) fixed at content_model.py:478-485 with the empty-clause skip pattern.

### Human Verification Required

#### 1. PDF Visual Parity (EXEC-04 / UAT-98-07)

**Test:** Run `quirk report` (or equivalent CLI invocation) on a fixture scan result. Open the generated HTML in a browser. Open or print the auto-generated PDF. Compare: narrative lead text, Priority Business Risks entries, "How this score was computed" block, roadmap section with effort/impact labels.

**Expected:** PDF and HTML carry identical narrative content — same narrative lead sentence, same risk labels and impact sentences, same rollup formula text, same roadmap structure. Format differences (typography, layout) are acceptable; content differences are not.

**Why human:** Playwright (PDF rendering) is not available in CI/automated testing. The structural guarantee is automated via D-03 (single ExecContent instance), but visual/layout parity in the PDF output requires a real Playwright environment and human inspection.

#### 2. Congruence Guard Live Behavior (TRANS-03 / UAT-98-05)

**Test:** Craft or mock a scan session where the overall score falls in EXCELLENT/GOOD/MODERATE band but CRITICAL findings are present. Run `quirk report` against that fixture. Observe CLI output.

**Expected:** The CLI aborts with the congruence error message before writing any executive-summary file. Message format: "Report generation halted: executive headline 'GOOD' is inconsistent with N CRITICAL finding(s). Review findings before generating the report." No executive-summary-*.md file in the output directory.

**Why human:** The automated test (test_guard_blocks_report_generation) covers this with mocks. A live end-to-end invocation confirming the error surfaces correctly in the CLI UX (not swallowed, formatting readable) requires human observation.

### Gaps Summary

No automated gaps. All 11 must-have truths are VERIFIED, all artifacts exist and are substantive and wired, all key links confirmed, all 7 requirements satisfied, test suite 23/23 pass.

The three deferred review findings (WR-03, WR-04, WR-05) are acknowledged warnings:
- **WR-03** (rollup numerator divergence under a 7th subscore): latent, does not affect current parity.
- **WR-04** (band recomputed in HTML vs exec_content.score_band): sources agree today due to identical thresholds; risk is future drift.
- **WR-05** (compat None paths bypass guard): production write_reports() always passes exec_content; risk is direct callers only.

None of these undermine the phase goal as currently deployed. They are technical debt for a follow-up phase if the scoring model evolves.

Phase status is `human_needed` because PDF visual parity (UAT-98-07) and live congruence-guard CLI behavior (UAT-98-05) require human verification that cannot be automated in this environment.

---

_Verified: 2026-05-24_
_Verifier: Claude (gsd-verifier)_
