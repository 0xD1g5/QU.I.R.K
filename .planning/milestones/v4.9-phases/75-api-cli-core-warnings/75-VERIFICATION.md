---
phase: 75-api-cli-core-warnings
verified: 2026-05-15T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 75: API + CLI + Core WARNINGs Verification Report

**Phase Goal:** All four WARNING clusters in the API/CLI/core subsystem are resolved — doctor checks return meaningful data, scan-id time-window is microsecond-safe, list_scans grouping is correct, and QRAMM/interactive/validate/route input hardening is complete. Closes audit findings api-cli-core/WR-01 through WR-17.

**Verified:** 2026-05-15
**Status:** passed

## Goal Achievement — Observable Truths (ROADMAP SCs)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `quirk doctor` returns typed status, `_check_db` honors `QUIRK_DB_PATH`, `_default_db_path` deterministic | VERIFIED | `quirk/cli/doctor_cmd.py:35,93-132` (`safe_str`, env-precedence, typed dict, remediation); `deps.py` fail-loud ValueError observable in test-collection — multi-DB raises as designed |
| 2 | `get_latest_scan` microsecond-safe, `list_scans` parsed-datetime grouping, `compute_overall_score` multiplier server-side validated, range stays [0.8, 1.5] | VERIFIED | `quirk/dashboard/api/routes/scan.py:978` `microsecond=999_999`; `qramm.py:184-194` clamp-then-round; `qramm.py:360-374` pre-DB guard with literal `multiplier must be numeric in [0.8, 1.5]`; `Field` at line 96 ge=0.8 le=1.5 |
| 3 | `routes/qramm read_session` 422 on JSON corruption; `_derive_dar_findings` logged; `list_questions` schema-drift safe | VERIFIED | `qramm.py:287` `Session JSON corrupt: {safe_str(e)}`; `scan.py:494` `logger.warning("DAR finding parse skipped: %s", safe_str(e))`; `qramm.py:471-480` `.get()` defaults over real `QuestionItem` fields |
| 4 | Interactive EOF-safe, exposure validated, declared `enable_nmap` (no setattr), validate.py expects `intelligence-{stamp}.json`, qramm_cmd try/except, QUIRK_OUTPUT_DIR validated, hostname format validated | VERIFIED | `config.py:200 enable_nmap: bool = False`; `interactive.py:309` direct assignment (no `setattr`); `validate.py:118` `intelligence-{stamp}.json`; `targets.py:41,200,208` `_HOSTNAME_RE` + fullmatch + error |

**Score:** 4/4 ROADMAP success criteria verified.

## Audit Ledger Closure

`grep -cE "api-cli-core/WR-(0[1-9]|1[0-7]).*Phase 75.*\[x\] closed"` → **17** (all rows WR-01..WR-17 closed under Phase 75).

## Decision Coverage (D-01..D-17)

| Decision | Site at HEAD | Status |
|----------|--------------|--------|
| D-01 typed status dict | doctor_cmd.py:93-132 | VERIFIED |
| D-02 QUIRK_DB_PATH precedence | doctor_cmd.py:97-115 | VERIFIED |
| D-03 fail-loud single canonical | deps.py:29 ValueError observed during test collection | VERIFIED |
| D-04 microsecond=999_999 window | scan.py:978 | VERIFIED |
| D-05 parsed-datetime grouping | scan.py (datetime.fromisoformat groupings) | VERIFIED |
| D-06 server-side multiplier guard, range [0.8, 1.5] | qramm.py:360-374 | VERIFIED — range NOT widened |
| D-07 clamp-then-round | qramm.py:192-194 | VERIFIED |
| D-08 422 on corrupt score_json | qramm.py:287 `Session JSON corrupt` | VERIFIED |
| D-09 logged + continue DAR | scan.py:494 | VERIFIED |
| D-10 / C-5 .get() defaults on real fields | qramm.py:471-480 | VERIFIED |
| D-11 _prompt_int EOF safety | interactive.py:49-79 | VERIFIED |
| D-12 _prompt_exposure 3-retry | interactive.py | VERIFIED |
| D-13 declared enable_nmap | config.py:200 + interactive.py:309 (no setattr) | VERIFIED |
| D-14 intelligence-{stamp}.json | validate.py:118 | VERIFIED |
| D-15 qramm_cmd try/except | qramm_cmd.py (logger.warning) | VERIFIED |
| D-16 _resolve_output_dir helper | scan.py (inherited from 75-02 commit dacb578) | VERIFIED |
| D-17 _HOSTNAME_RE + ip fallback | targets.py:41,200,208 | VERIFIED |

## Key Wiring Checks

- `enable_nmap` is a declared dataclass field: `quirk/config.py:200 enable_nmap: bool = False` — VERIFIED
- No `setattr.*enable_nmap` remains anywhere in `quirk/`: grep returned zero matches — VERIFIED
- Multiplier range remains [0.8, 1.5] (not widened): Pydantic Field, _compute_multiplier clamp, and pre-DB guard literal phrase all match — VERIFIED

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Compilation clean | `python -m compileall quirk/` | exit 0 | PASS |
| Targeted Phase 75 tests | `pytest tests/test_doctor_actionable.py tests/test_api_scan_window.py tests/test_api_qramm_hardening.py tests/test_interactive_validate_routes.py -q` (with `QUIRK_DB_PATH=./quirk-output/quirk.db`) | 57 passed | PASS |

Note: Running pytest without `QUIRK_DB_PATH` set raises `ValueError: Multiple QU.I.R.K. DBs found` at app-creation time — this is the intended D-03 fail-loud behavior, not a regression. The dev workstation has all three legacy DB files present.

## Anti-Patterns Found

None. No new TODO/FIXME/XXX markers in modified files. No stubs. No bare `except`. All exception stringification routes through `safe_str`.

## Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| APCL-01 (doctor + DB path) | SATISFIED | doctor_cmd.py + deps.py changes verified |
| APCL-02 (scan window + multiplier) | SATISFIED | scan.py + qramm.py changes verified |
| APCL-03 (qramm/DAR hardening) | SATISFIED | qramm.py:287 + scan.py:494 + qramm.py:471-480 |
| APCL-04 (interactive + validate + routes) | SATISFIED | All seven D-11..D-17 surfaces verified |

## Gaps

None.

---

_Verified: 2026-05-15_
_Verifier: Claude (gsd-verifier)_
