# Phase 45 — Validation Strategy

**Source:** `.planning/phases/45-install-day-ux/45-RESEARCH.md` § "Validation Architecture" (lines 572-602).
**Status:** Authoritative validation contract for Phase 45.
**Updated:** 2026-05-03

---

## Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing — `pyproject.toml [tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` (testpaths=`tests`, addopts=`-m 'not slow'`) |
| Quick run command | `pytest tests/test_optional_extra.py -x` |
| Full suite command | `pytest` (excludes slow) + `pytest -m slow` (CI only) |

---

## Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Test File (status) |
|--------|----------|-----------|-------------------|--------------------|
| INSTALL-01 | TLS-only scan in minimal venv produces no ImportError | unit (mock `find_spec`) | `pytest tests/test_optional_extra.py::test_no_importerror_when_extras_missing -x` | `tests/test_optional_extra.py` (Wave 0 — Plan 02) |
| INSTALL-02 | One advisory per enabled-but-missing scanner | unit | `pytest tests/test_optional_extra.py::test_probe_emits_one_advisory_per_missing_extra -x` | `tests/test_optional_extra.py` (Wave 0 — Plan 02) |
| INSTALL-02 | Coverage Gaps section renders in HTML report | unit (template render) | `pytest tests/test_html_renderer_coverage_gaps.py -x` | `tests/test_html_renderer_coverage_gaps.py` (Wave 0 — Plan 03 Task 2) |
| INSTALL-02 | risk_engine maps ADVISORY rows to coverage_gap finding | unit | `pytest tests/test_risk_engine_coverage_gap.py -x` | `tests/test_risk_engine_coverage_gap.py` (Wave 0 — Plan 03 Task 1) |
| INSTALL-03 | `pip install quirk[all]` succeeds + impacket absent | integration / slow | `pytest -m slow tests/test_install_all_excludes_impacket.py -x` | `tests/test_install_all_excludes_impacket.py` (Wave 0 — Plan 01) |
| INSTALL-04 | Hint string contains literal `pip install quirk[<extra>]` | unit | `pytest tests/test_optional_extra.py::test_all_hints_contain_pip_install_literal -x` | `tests/test_optional_extra.py` (Wave 0 — Plan 02) |
| D-07 | Coverage gap findings excluded from severity counts in renderer | unit | `pytest tests/test_html_renderer_coverage_gaps.py::test_sev_counts_exclude_coverage_gap -x` | `tests/test_html_renderer_coverage_gaps.py` (Wave 0 — Plan 03 Task 2) |
| D-07 | Coverage gap findings excluded from evidence summary (totals + sev counts) | unit | `pytest tests/test_evidence_coverage_gap.py -x` | `tests/test_evidence_coverage_gap.py` (Wave 0 — Plan 03 Task 3) |
| Q2 | Dashboard FindingItem has optional `category` field | unit (Pydantic) | `pytest tests/test_dashboard_schemas_finding_category.py -x` | `tests/test_dashboard_schemas_finding_category.py` (Wave 0 — Plan 03 Task 4) |

---

## Sampling Rate

| Trigger | Command |
|---------|---------|
| Per task commit | `pytest tests/test_optional_extra.py tests/test_html_renderer_coverage_gaps.py tests/test_risk_engine_coverage_gap.py tests/test_evidence_coverage_gap.py tests/test_dashboard_schemas_finding_category.py -x` |
| Per wave merge | `pytest` (full default suite, excludes slow) |
| Phase gate (Plan 03 Task 5 sweep) | `pytest -x` AND `pytest -m slow tests/test_install_all_excludes_impacket.py -x` — both GREEN |

---

## Wave 0 Test File Inventory

The following test files MUST be created (RED) before the matching implementation tasks
GREEN them. The Nyquist coverage gate enforces test-first ordering.

- [ ] `tests/test_optional_extra.py` — covers INSTALL-01, INSTALL-02 (probe behavior), INSTALL-04 — owned by **Plan 02**.
- [ ] `tests/test_html_renderer_coverage_gaps.py` — covers INSTALL-02 (rendering) + D-07 (sev-count exclusion) — owned by **Plan 03 Task 2**.
- [ ] `tests/test_install_all_excludes_impacket.py` — covers INSTALL-03 + D-01 (slow-marked) — owned by **Plan 01**.
- [ ] `tests/test_risk_engine_coverage_gap.py` — covers INSTALL-02 (risk-engine ADVISORY → coverage_gap mapping) — owned by **Plan 03 Task 1**.
- [ ] `tests/test_evidence_coverage_gap.py` — covers D-07 (coverage_gap excluded from `totals.findings` and `finding_severity_counts`) — owned by **Plan 03 Task 3**.
- [ ] `tests/test_dashboard_schemas_finding_category.py` — covers Q2 (FindingItem.category default-None + explicit-value behaviors) — owned by **Plan 03 Task 4**.

---

## Manual / Checkpoint Validation

The four phase-level success criteria (SC #1–#4 in ROADMAP.md Phase 45) are exercised
end-to-end by **Plan 04 Task 1** — a `checkpoint:human-verify` step that runs a clean-venv
smoke test against the chaos lab and confirms the Coverage Gaps section, top-10 preview
exclusion, severity-count = 0, and `pip install quirk[<extra>]` literal recommendation.

---

## Phase Gate Criteria

Phase 45 is complete when ALL of the following are GREEN:

1. `pytest -x` (default suite) — all tests pass.
2. `pytest -m slow tests/test_install_all_excludes_impacket.py -x` — impacket regression GREEN.
3. `python -m compileall quirk run_scan.py` — no SyntaxError.
4. Plan 04 Task 1 manual checkpoint — operator approves end-to-end smoke test.
5. CLAUDE.md mandatory phase-completion steps complete: `docs/UAT-SERIES.md` updated and
   committed, vault `UAT-Series.md` mirror in place, vault `Phase-45-Install-Day-UX.md`
   note in place with `status: complete`.
