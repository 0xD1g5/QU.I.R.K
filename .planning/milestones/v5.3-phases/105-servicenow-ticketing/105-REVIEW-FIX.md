---
phase: 105-servicenow-ticketing
fixed_at: 2026-05-25T00:00:00Z
review_path: .planning/phases/105-servicenow-ticketing/105-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 105: Code Review Fix Report

**Fixed at:** 2026-05-25T00:00:00Z
**Source review:** .planning/phases/105-servicenow-ticketing/105-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (CR-01, WR-01, WR-02, WR-03)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: `table` name accepted without validation — URL path injection

**Files modified:** `quirk/ticketing/config.py`, `tests/test_ticketing_servicenow.py`
**Commit:** b313a73
**Applied fix:** Added `_TABLE_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]{0,79}$")` as a
module-level constant in `config.py` (mirrors the existing `_PROJECT_KEY_RE` Jira pattern).
In `_parse_servicenow_cfg`, the `table` value is now extracted before building the dataclass
and rejected (returns `None`) if it does not match the regex. The docstring was updated to
document the new guard. Added 4 regression tests:
`test_table_path_traversal_rejected`, `test_table_query_injection_rejected`,
`test_table_uppercase_rejected`, `test_table_valid_custom_accepted`.

---

### WR-01: `safe_str` is imported but never called — ISEC-02 claim is inaccurate

**Files modified:** `quirk/ticketing/servicenow.py`
**Commit:** 3508f68
**Applied fix:** Removed the `# noqa: F401 — imported for subclass-context use` comment
from the `safe_str` import (it is now actively called). Applied `safe_str(exc)` to all
three `except urllib.error.URLError` branches (GET, POST, PATCH) — `exc.reason` is a
server-controlled string and safe_str provides defense-in-depth against credential leakage
in any future refactor. Updated the ISEC-02 module docstring to accurately describe the
technique: safe_str wraps server-controlled exception detail; `exc.code` (int) is always
safe and used directly.

---

### WR-02: Misleading error message when `ServiceNowChannel.__init__` fails in `ticket_cmd.py`

**Files modified:** `quirk/cli/ticket_cmd.py`, `tests/test_ticket_cmd.py`
**Commit:** 035de63
**Applied fix:** Extracted channel construction out of the outer dispatch `try` block into
its own dedicated `try/except (ValueError, ImportError)` block for each backend. Init errors
(SSRF `ValueError`, missing extra `ImportError`) now produce:
`"ERROR: ticketing backend init failed: <detail>"` with exit code 2.
The remaining dispatch `try` block retains the accurate `"audit-row persistence failed"`
message for DB-level failures after successful construction. Added regression test
`test_servicenow_init_error_labelled_correctly` confirming SSRF ValueError produces the
correct label and not the misleading "audit-row persistence" message.

---

### WR-03: `create_issue_from_finding` raises undiagnosed `KeyError` on malformed POST response

**Files modified:** `quirk/ticketing/servicenow.py`, `tests/test_ticketing_servicenow.py`
**Commit:** cc3a50b
**Applied fix:** In `create_issue_from_finding`: wrapped `json.loads` in a
`try/except ValueError` that raises `RuntimeError("ServiceNow POST returned non-JSON response")`;
replaced bare `data["result"]["sys_id"]` with `.get()` + explicit `None` check that raises
`RuntimeError(f"ServiceNow POST response missing result.sys_id; body snippet: {raw[:120]!r}")`.
In `find_by_fingerprint`: same `json.loads` guard raises
`RuntimeError("ServiceNow GET returned non-JSON response")`. The `data.get("result", [])` for
GET was already safe. Added two regression tests: `test_create_issue_missing_sys_id_raises_runtime_error`
(201 with no sys_id) and `test_create_issue_non_json_response_raises_runtime_error` (HTML body).

---

## Skipped Issues

None — all findings were fixed.

---

**Post-fix verification:**
- `python -m compileall quirk/ticketing quirk/cli/ticket_cmd.py` — clean (no output)
- `python -m pytest tests/test_ticketing_servicenow.py tests/test_ticketing_jira.py tests/test_ticketing_base.py tests/test_ticket_cmd.py -q` — **40 passed**
- `git diff --quiet quirk/ticketing/base.py quirk/ticketing/jira.py` — **PASS** (TICKET-04 invariant)

---

_Fixed: 2026-05-25T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
