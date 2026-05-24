---
phase: 98
slug: executive-narrative-score-transparency
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-24
---

# Phase 98 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python -m pytest tests/test_exec_content_model.py tests/test_congruence_guard.py tests/test_exec_narrative_ordering.py tests/test_cross_surface_parity.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~20 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

> Requirement→behavior→command map from RESEARCH.md §Validation Architecture. Task IDs
> are assigned by the planner; the planner maps each row to the task that delivers it.

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| EXEC-01 | Narrative prose appears before any finding table in CLI output | unit | `pytest tests/test_exec_narrative_ordering.py::test_narrative_before_findings_cli -x` | ❌ W0 | ⬜ pending |
| EXEC-01 | Narrative prose appears before `<table>` in HTML output | unit | `pytest tests/test_exec_narrative_ordering.py::test_narrative_before_table_html -x` | ❌ W0 | ⬜ pending |
| EXEC-02 | Top-risks list present in CLI with business-impact sentences | unit | `pytest tests/test_exec_content_model.py::test_top_risks_populated -x` | ❌ W0 | ⬜ pending |
| EXEC-02 | `.risks-list` element present in HTML with ≥1 item when findings exist | unit | `pytest tests/test_exec_narrative_ordering.py::test_risks_list_in_html -x` | ❌ W0 | ⬜ pending |
| EXEC-03 | Roadmap items carry effort/impact; sorted high-impact-first within bucket | unit | `pytest tests/test_exec_content_model.py::test_roadmap_priority_ordering -x` | ❌ W0 | ⬜ pending |
| EXEC-03 | Priority labels appear in HTML roadmap items | unit | `pytest tests/test_exec_narrative_ordering.py::test_priority_labels_in_html_roadmap -x` | ❌ W0 | ⬜ pending |
| EXEC-04 | CLI narrative lead and HTML narrative lead are identical strings | unit | `pytest tests/test_cross_surface_parity.py::test_narrative_content_parity -x` | ❌ W0 | ⬜ pending |
| EXEC-04 | CLI and HTML top-risks carry identical item count and labels | unit | `pytest tests/test_cross_surface_parity.py::test_top_risks_parity -x` | ❌ W0 | ⬜ pending |
| TRANS-01 | `ExecContent.subscores` exposes all six pillar keys | unit | `pytest tests/test_exec_content_model.py::test_subscores_all_keys_present -x` | ❌ W0 | ⬜ pending |
| TRANS-01 | Score decomposition table present in HTML (regression gate) | unit | `pytest tests/test_score_transparency.py -x` | ✅ exists | ⬜ pending |
| TRANS-02 | Rollup formula text (÷1.5) present in HTML output | unit | `pytest tests/test_exec_narrative_ordering.py::test_rollup_formula_in_html -x` | ❌ W0 | ⬜ pending |
| TRANS-03 | `_check_congruence("GOOD", {"CRITICAL": 3})` raises `ReportCongruenceError` | unit | `pytest tests/test_congruence_guard.py::test_good_band_with_critical_raises -x` | ❌ W0 | ⬜ pending |
| TRANS-03 | `_check_congruence("FAIR", {"CRITICAL": 5})` does NOT raise | unit | `pytest tests/test_congruence_guard.py::test_fair_band_with_critical_ok -x` | ❌ W0 | ⬜ pending |
| TRANS-03 | `write_reports()` surfaces error before writing any file when guard fires | integration | `pytest tests/test_congruence_guard.py::test_guard_blocks_report_generation -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_exec_content_model.py` — ExecContent dataclass, `build_exec_content()` shape, top-risks population, roadmap priority ordering, subscores pass-through (EXEC-02, EXEC-03, TRANS-01)
- [ ] `tests/test_congruence_guard.py` — `_check_congruence()` all band cases, `ReportCongruenceError` message format, `write_reports()` blocking on guard fire (TRANS-03)
- [ ] `tests/test_exec_narrative_ordering.py` — CLI narrative-before-findings, HTML narrative-before-table, risks-list in HTML, priority labels in HTML roadmap, rollup formula in HTML (EXEC-01, EXEC-02, EXEC-03, TRANS-02)
- [ ] `tests/test_cross_surface_parity.py` — narrative content identity across CLI/HTML (EXEC-04)

**Existing regression gates (must continue to pass):**

- `tests/test_score_transparency.py` — Score Decomposition in CLI + scorecard (TRANS-01/02)
- `tests/test_score_render_parity.py` — single scoring engine identity (RENDER-CLI-01)
- `tests/test_executive_score_guard.py` — `_build_interpretation()` score dict guard
- `tests/test_html_report.py` — HTML report structure (wordmark, self-contained CSS, sections)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PDF renders the same narrative/score story as HTML (visual confirmation) | EXEC-04, success criterion 6 | PDF is Playwright-rendered from HTML; pixel-level rendering is observed visually, not asserted in code (content parity IS automated via the shared-model tests) | Run `quirk report` on a fixture scan, open the HTML in a browser and export the PDF; confirm narrative, top-risks, roadmap, and score-decomposition sections appear identically |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (test files created alongside production code in plans 98-01/98-02/98-03 — no separate Wave 0)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-24
