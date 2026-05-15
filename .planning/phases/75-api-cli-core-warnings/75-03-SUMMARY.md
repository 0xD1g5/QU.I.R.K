---
phase: 75-api-cli-core-warnings
plan: 03
subsystem: dashboard-api
tags: [hardening, qramm, dar, error-handling, schema-drift, apcl-03]
requires:
  - quirk.util.safe_exc.safe_str  # Phase 59 LEAK-01 helper (existing)
provides:
  - routes/qramm.read_session 422 on corrupt score_json (D-08 / WR-07)
  - routes/scan._derive_dar_findings logged + continue on bad JSON (D-09 / WR-08)
  - routes/qramm.list_questions schema-drift safe via .get() defaults (D-10 + C-5 / WR-17)
affects:
  - operators (visible 422 instead of silent score=None)
  - scan-quality observability (parse failures now logged)
tech-stack:
  added: []
  patterns:
    - "safe_str-sanitized HTTPException detail at trust boundary"
    - "logger.warning + continue (not bare-except swallow)"
    - "Pydantic .get() defaults for forward-compatible API contracts"
key-files:
  created:
    - tests/test_api_qramm_hardening.py
  modified:
    - quirk/dashboard/api/routes/qramm.py
    - quirk/dashboard/api/routes/scan.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions:
  - "C-3 honored: D-08 catch tuple is (json.JSONDecodeError, TypeError, ValueError) — NOT CONTEXT's (JSONDecodeError, ValidationError). No Pydantic ValidationError is raised at the read_session call site (only json.loads is called); the original CONTEXT shape was over-specified."
  - "C-4 honored: D-09 AST-gate sentence dropped — tests/test_safe_exc_gate.py does NOT exist and was NOT created. Behavior is verified via direct unit tests in tests/test_api_qramm_hardening.py, not via an AST grep gate."
  - "C-5 honored: D-10 defensive defaults use the REAL QuestionItem fields (question_number, dimension, practice_area, text, maturity_labels) — NOT the CONTEXT placeholder fields (id, text, options) which do not exist on the real model."
metrics:
  duration_seconds: 183
  completed_date: 2026-05-15
  tasks_completed: 3
  files_changed: 4
  tests_added: 7
---

# Phase 75 Plan 03: APCL-03 QRAMM/DAR API Hardening Summary

QRAMM `read_session` now surfaces corrupt `score_json` as `HTTP 422` with a `safe_str`-sanitized detail (WR-07), `_derive_dar_findings` logs and skips on bad `dat_scan_json` instead of silently swallowing (WR-08), and `list_questions` survives `QRAMM_QUESTIONS` schema drift via `.get()` defaults on the real `QuestionItem` fields (WR-17).

## What changed

### D-08 / WR-07 — `read_session` 422 on corrupt JSON

`quirk/dashboard/api/routes/qramm.py::read_session` previously caught
`(TypeError, ValueError)` and silently returned `score=None` to the operator,
masking persisted-data corruption. Now wraps `json.loads(session.score_json)`
in `try / except (json.JSONDecodeError, TypeError, ValueError) as e: raise
HTTPException(status_code=422, detail=f"Session JSON corrupt: {safe_str(e)}")`.

RESEARCH C-3 correction: the CONTEXT D-08 catch tuple
`(JSONDecodeError, ValidationError)` is wrong — no Pydantic is invoked at this
call site (only `json.loads`). Final tuple is
`(json.JSONDecodeError, TypeError, ValueError)`.

### D-09 / WR-08 — `_derive_dar_findings` logged + continue

`quirk/dashboard/api/routes/scan.py::_derive_dar_findings` bare
`except Exception: dat = {}` (old lines 458-461) replaced with
`except (json.JSONDecodeError, KeyError, TypeError) as e: logger.warning("DAR
finding parse skipped: %s", safe_str(e)); continue`. The endpoint with corrupt
`dat_scan_json` is now skipped and the failure is visible in operator logs;
subsequent valid endpoints are still processed.

RESEARCH C-4 correction: the CONTEXT D-09 "add AST gate at
tests/test_safe_exc_gate.py" sentence was dropped. That test module does not
exist on `main`; creating it would have been scope creep. Behavior is verified
directly via `caplog` assertions in `tests/test_api_qramm_hardening.py`.

### D-10 + C-5 / WR-17 — `list_questions` drift-safe

`quirk/dashboard/api/routes/qramm.py::list_questions` replaced the pure spread
`[QuestionItem(**q) for q in QRAMM_QUESTIONS]` with a `.get()`-defaulted
constructor over the REAL `QuestionItem` fields:

```
QuestionItem(
    question_number=q.get("question_number", 0),
    dimension=q.get("dimension", ""),
    practice_area=q.get("practice_area", ""),
    text=q.get("text", ""),
    maturity_labels=q.get("maturity_labels", []),
)
```

RESEARCH C-5 correction: CONTEXT D-10 named placeholder fields
(`id`, `text`, `options`) that do not exist on the real `QuestionItem` model
(`question_number, dimension, practice_area, text, maturity_labels`). Using
the CONTEXT names would have raised on every call. The real fields are now
used, so future schema drops in `QRAMM_QUESTIONS` degrade to a valid `200`
with default values instead of cascading to `500`.

## Tests

`tests/test_api_qramm_hardening.py` — 7 tests, all passing post-Task 2:

| # | Test | Covers |
|---|------|--------|
| 1 | `test_read_session_returns_422_on_corrupt_score_json` | D-08 happy: 422 + `Session JSON corrupt: ` prefix |
| 2 | `test_read_session_happy_path_still_200` | D-08 regression: valid JSON still 200 |
| 3 | `test_derive_dar_findings_logs_and_skips_corrupt_dat_scan_json` | D-09 happy: `logger.warning` emitted |
| 4 | `test_derive_dar_findings_valid_row_no_warning` | D-09 negative: no warning on clean row |
| 5 | `test_derive_dar_findings_continues_past_corrupt_row` | D-09: iteration continues past bad row |
| 6 | `test_list_questions_drift_safe_missing_keys` | D-10/C-5: 200 with defaults on missing keys |
| 7 | `test_list_questions_full_shape_unchanged` | D-10 regression: real catalog still served |

Assertion uses `.startswith("Session JSON corrupt: ")` not full equality, per
RESEARCH Pitfall 5 (`safe_str` output varies across Python minor versions).

## Audit closures

`.planning/audit-2026-05-08/AUDIT-TASKS.md`:

| Row | Status |
|-----|--------|
| api-cli-core/WR-07 | `Phase 75 \| [x] closed` |
| api-cli-core/WR-08 | `Phase 75 \| [x] closed` |
| api-cli-core/WR-17 | `Phase 75 \| [x] closed` |

Verification: `grep -cE "api-cli-core/WR-(07|08|17).*Phase 75.*\[x\] closed" .planning/audit-2026-05-08/AUDIT-TASKS.md` == **3**.

## Commit cadence (RED → GREEN → DOCS)

| Step | Commit | Message |
|------|--------|---------|
| 1 RED | `7e7372d` | `test(75-03): add failing tests for APCL-03 (D-08 422, D-09 logged, D-10 drift-safe)` |
| 2 GREEN | `aa4867b` | `feat(75-03): implement APCL-03 fixes (D-08 422 read_session, D-09 logged DAR, D-10/C-5 drift-safe list_questions)` |
| 3 DOCS | `226d3b0` | `docs(75-03): close api-cli-core WR-07/WR-08/WR-17 in audit ledger` |

RED state at `7e7372d`: 3 of 7 tests fail (one per WR), all with assertion / `ValidationError` shapes tied to the unfixed sites. GREEN state at `aa4867b`: all 7 pass.

## Verification

- `python -m compileall quirk/dashboard/api/routes/qramm.py quirk/dashboard/api/routes/scan.py` — clean
- `pytest tests/test_api_qramm_hardening.py` — 7 passed
- `pytest tests/ -k "qramm or scan"` — 550 passed, 8 pre-existing failures unrelated to APCL-03 (verified by stash-and-rerun on `main` HEAD: identical 3 failures in `test_dashboard_scan_history`, `test_broker_scanner_rabbitmq`, `test_api_scan_window::test_score_session_out_of_range_returns_400_with_literal_detail`, plus 5 others scoped to other in-flight plans). None touch APCL-03 surface.
- `grep -E "api-cli-core/WR-(07|08|17).*Phase 75.*\[x\] closed" .planning/audit-2026-05-08/AUDIT-TASKS.md` — 3 hits
- `tests/test_safe_exc_gate.py` — NOT created (C-4 honored)
- `QuestionItem` field names verified against real model at `quirk/dashboard/api/routes/qramm.py` lines 434-440 (C-5 honored)

## Deviations from Plan

None. Plan executed exactly as written with all three RESEARCH corrections (C-3, C-4, C-5) preserved.

## Self-Check: PASSED

- `tests/test_api_qramm_hardening.py` — FOUND
- `quirk/dashboard/api/routes/qramm.py` D-08 + D-10 edits — FOUND (`Session JSON corrupt`, `q.get('question_number'`)
- `quirk/dashboard/api/routes/scan.py` D-09 edit — FOUND (`DAR finding parse skipped`)
- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — 3 flipped rows confirmed
- Commits `7e7372d`, `aa4867b`, `226d3b0` — all present in `git log`
