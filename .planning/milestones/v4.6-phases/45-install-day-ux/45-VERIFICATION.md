---
phase: 45-install-day-ux
verified: 2026-05-03T21:30:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 45: Install-Day UX Verification Report

**Phase Goal:** Users can install QUIRK with `pip install quirk` (no extras) or `pip install quirk[all]` and run a scan without ImportError crashes; visible advisory notices surface for any optional scanner whose extras are absent.
**Verified:** 2026-05-03
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (mapped to INSTALL-01..04)

| #   | Truth (Requirement)                                                                                          | Status      | Evidence                                                                                                                                                                       |
| --- | ------------------------------------------------------------------------------------------------------------ | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | INSTALL-01 — Clean `pip install quirk` TLS-only scan produces zero ImportError                               | VERIFIED    | `quirk/util/optional_extra.py` uses `find_spec` (not `import`); grep for hard top-level imports of optional packages (`impacket`, `fastapi`, `psycopg2`, `googleapiclient`, `hvac`, `kubernetes`, `playwright`, `boto3`, `sslyze`, `kafka`, `redis`) found zero unguarded matches. Operator UAT confirmed minimal venv produced 5 findings, no ImportError. `tests/test_optional_extra.py::test_no_importerror_when_extras_missing` PASS. |
| 2   | INSTALL-02 — ADVISORY → coverage_gap mapping; Coverage Gaps section in HTML; D-07 sev/score exclusion; FindingItem.category | VERIFIED    | `quirk/engine/risk_engine.py:259-268` — ADVISORY rows with `scan_error_category="missing_extra"` produce `category="coverage_gap"` INFO findings. `quirk/reports/templates/report.html.j2:209-217` — `<h2>Coverage Gaps</h2>` section with `{% if coverage_gaps %}` guard; line 177/228 reject coverage_gap from top-10 + All Findings. `quirk/intelligence/evidence.py:65` filters coverage_gap from `finding_list`. `quirk/dashboard/api/schemas.py:55` adds `category: Optional[str] = None` to `FindingItem`. Operator UAT: gaps venv showed INFO=1/LOW=1/MEDIUM=1 (6 coverage_gaps excluded). |
| 3   | INSTALL-03 — `[all]` extra composes cloud+db+motion+redis+dashboard, impacket excluded                       | VERIFIED    | `pyproject.toml:62-72` — `all = ["quirk[cloud]", "quirk[db]", "quirk[motion]", "quirk[redis]", "quirk[dashboard]"]` with explicit comment that `[identity]` is omitted. `tests/test_install_all_excludes_impacket.py` exists and PASSES under `pytest -m slow` (1 passed in 4.29s). Operator UAT confirmed `import impacket` raises ModuleNotFoundError in `[all]` venv. |
| 4   | INSTALL-04 — Every advisory hint contains literal `pip install quirk[<extra>]`                               | VERIFIED    | `quirk/util/optional_extra.py` REGISTRY entries (lines 67/77/87/97) all contain `pip install quirk[identity]`, `pip install quirk[db]`, `pip install quirk[cloud]`, `pip install quirk[dashboard]`. `tests/test_optional_extra.py::test_all_hints_contain_pip_install_literal` PASS. Operator UAT confirmed hints rendered in HTML. (motion deliberately omitted per Q1 — Phase 41 inline path emits motion advisories.) |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact                                              | Expected                                            | Status     | Details                                                                                                  |
| ----------------------------------------------------- | --------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------- |
| `quirk/util/optional_extra.py`                        | REGISTRY + probe helpers                            | VERIFIED   | 6,372 bytes; 4 REGISTRY entries (identity/db/cloud/dashboard); `find_spec`-based probe; literal hints.   |
| `pyproject.toml` `[all]`                              | cloud+db+motion+redis+dashboard, impacket excluded  | VERIFIED   | Lines 62-72 confirmed; explicit exclusion comment.                                                       |
| `quirk/engine/risk_engine.py` ADVISORY branch         | Maps ADVISORY+missing_extra → coverage_gap finding  | VERIFIED   | Lines 259-268; `continue` after append prevents double-emission.                                         |
| `quirk/reports/templates/report.html.j2`              | Coverage Gaps section + filters                     | VERIFIED   | Lines 209-217 dedicated section; lines 177/228 filter from top-10 + All Findings.                        |
| `quirk/reports/html_renderer.py`                      | sev_counts skip coverage_gap (D-07)                 | VERIFIED   | Operator UAT confirmed no INFO badge for 6 coverage_gaps (minimal venv) + 1 INFO badge for the genuine non-coverage_gap INFO (gaps venv). |
| `quirk/intelligence/evidence.py`                      | Filter coverage_gap before totals/sev counts (D-07) | VERIFIED   | Line 65 list-comp filter at top of `build_evidence_summary`.                                             |
| `quirk/dashboard/api/schemas.py` FindingItem.category | Optional[str] = None                                | VERIFIED   | Line 55 confirmed.                                                                                       |
| `run_scan.py` probe wiring                            | `probe_missing_extras(cfg, error_endpoints)` call   | VERIFIED   | Lines 385-386 confirmed (1 occurrence).                                                                  |
| `tests/test_optional_extra.py`                        | INSTALL-01/02/04 contracts                          | VERIFIED   | 8 tests PASS.                                                                                            |
| `tests/test_install_all_excludes_impacket.py`         | INSTALL-03 regression guard                         | VERIFIED   | 1 test PASS under `-m slow` (4.29s).                                                                     |
| `tests/test_risk_engine_coverage_gap.py`              | ADVISORY → coverage_gap unit test                   | VERIFIED   | 3 tests PASS.                                                                                            |
| `tests/test_html_renderer_coverage_gaps.py`           | Section render + sev exclusion                      | VERIFIED   | 5 tests PASS.                                                                                            |
| `tests/test_evidence_coverage_gap.py`                 | D-07 evidence exclusion                             | VERIFIED   | 2 tests PASS.                                                                                            |
| `tests/test_dashboard_schemas_finding_category.py`    | FindingItem.category Pydantic                       | VERIFIED   | 2 tests PASS.                                                                                            |

### Key Link Verification

| From                       | To                                  | Via                                                       | Status | Details                                                          |
| -------------------------- | ----------------------------------- | --------------------------------------------------------- | ------ | ---------------------------------------------------------------- |
| `run_scan.main`            | `quirk.util.optional_extra`         | `from ... import probe_missing_extras` + invocation       | WIRED  | `run_scan.py:385-386`                                            |
| `probe_missing_extras`     | `risk_engine.evaluate_endpoints`    | `error_endpoints` list → `protocol="ADVISORY"` rows       | WIRED  | risk_engine ADVISORY branch consumes the same list                |
| `risk_engine` finding dict | HTML template `Coverage Gaps`       | `category="coverage_gap"` discriminator                   | WIRED  | Jinja `selectattr/rejectattr('category', 'equalto', 'coverage_gap')` |
| `FindingItem.category`     | Dashboard DTO consumers             | Pydantic optional field, additive                         | WIRED  | No DB migration needed; existing call sites unaffected.          |

### Behavioral Spot-Checks

| Behavior                                                 | Command                                                                                                                              | Result               | Status |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | -------------------- | ------ |
| Phase 45 unit tests pass                                 | `pytest tests/test_optional_extra.py tests/test_risk_engine_coverage_gap.py tests/test_html_renderer_coverage_gaps.py tests/test_evidence_coverage_gap.py tests/test_dashboard_schemas_finding_category.py -x` | 20 passed in 0.55s   | PASS   |
| Slow regression (impacket exclusion)                     | `pytest -m slow tests/test_install_all_excludes_impacket.py -x`                                                                      | 1 passed in 4.29s    | PASS   |
| Compileall clean                                         | `python -m compileall quirk run_scan.py`                                                                                             | rc 0 (no SyntaxError) | PASS   |
| No naked top-level imports of optional packages          | `grep -rn '^import (impacket\|fastapi\|psycopg2\|...)' quirk/ run_scan.py` (excluding try/except guards)                              | 0 hits                | PASS   |

### Requirements Coverage

| Requirement | Source Plans   | Description                                          | Status    | Evidence                                                                |
| ----------- | -------------- | ---------------------------------------------------- | --------- | ----------------------------------------------------------------------- |
| INSTALL-01  | 45-02          | No ImportError on bare `pip install quirk`          | SATISFIED | `find_spec` probe + zero hard imports + test 7 PASS + operator UAT.     |
| INSTALL-02  | 45-02, 45-03   | `missing_extra` advisory + Coverage Gaps section + D-07 | SATISFIED | risk_engine branch + HTML section + sev/score exclusion + 4 test files. |
| INSTALL-03  | 45-01          | `pip install quirk[all]` succeeds; impacket excluded | SATISFIED | pyproject `[all]` block + slow regression test PASS + operator UAT.     |
| INSTALL-04  | 45-02          | Literal `pip install quirk[<extra>]` in every hint   | SATISFIED | REGISTRY hints all contain literal + `test_all_hints_contain_pip_install_literal` PASS. |

REQUIREMENTS.md lines 13-16 mark all four as `[x]` complete; lines 105-108 confirm Phase 45 status `Complete`. ROADMAP.md Phase 45 (line 901) shows all four plans `[x]`. STATE.md line 28 records `Phase: 45-install-day-ux — COMPLETE`.

### Anti-Patterns Found

None. No TODO/FIXME/PLACEHOLDER markers in new files. No empty handlers. No naked top-level imports of optional packages.

### Vault Confirmation

| File                                                                                       | Status                  |
| ------------------------------------------------------------------------------------------ | ----------------------- |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-45-Install-Day-UX.md`              | EXISTS, `status: complete`, 7,142 bytes |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`                                  | EXISTS, 242,110 bytes; contains UAT-1-09/10/11 + Phase 45 wrap header |
| `docs/UAT-SERIES.md` UAT-1-09/10/11                                                        | PRESENT (lines 247, 272, 308) + Last Updated header |

### Human Verification Required

None remaining. Operator manually verified the four end-to-end success criteria in clean venvs (Plan 45-04 Task 1) before this verification run; observations recorded in 45-04-SUMMARY.md and Phase note. Automated unit + slow regression suites cover the same contracts.

### Gaps Summary

No gaps. All four phase requirements (INSTALL-01..04) are satisfied by codebase artifacts that exist, are substantive, are wired through the scan → risk_engine → renderer → evidence pipeline, and are guarded by 21 passing automated tests (20 unit + 1 slow regression). Operator UAT independently confirmed end-to-end behavior in clean venvs against the chaos lab. ROADMAP, REQUIREMENTS, STATE, and the Obsidian vault all reflect completion.

**Recommendation:** PASS. Phase 45 is complete; no closure plan required. Proceed to Phase 46 (TLS Finding Gaps) and/or Phase 47 (Nmap Multi-Target). Note: ROADMAP Phase 46 plan-stub list at lines 933-936 still references "45-01..03-PLAN.md" placeholders — minor cosmetic issue scoped to Phase 46 planning, not a Phase 45 gap.

---

_Verified: 2026-05-03T21:30:00Z_
_Verifier: Claude (gsd-verifier)_
