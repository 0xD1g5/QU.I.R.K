---
phase: 104-jira-ticketing
fixed_at: 2026-05-25T00:00:00Z
review_path: .planning/phases/104-jira-ticketing/104-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 104: Code Review Fix Report

**Fixed at:** 2026-05-25
**Source review:** `.planning/phases/104-jira-ticketing/104-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (CR-01, CR-02, WR-01, WR-02, WR-03, WR-04)
- Fixed: 6
- Skipped: 0

## Fixed Issues

### CR-01: JQL Injection via Unvalidated `project_key`

**Files modified:** `quirk/ticketing/config.py`, `tests/test_ticketing_jira.py`
**Commit:** `72d5c72`
**Applied fix:** Added `_PROJECT_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]{1,99}$")` constant
to `config.py`. In `_parse_jira_cfg`, `project_key` is now validated against this regex;
any value that fails (empty string, lowercase, injection chars like `"`) causes the function
to return `None`, treating the Jira config as misconfigured — same path as missing `jira_url`.
Added regression tests: `test_invalid_project_key_rejected` (covers JQL breakout string,
lowercase, numeric start, spaces, hyphens), `test_empty_project_key_rejected`.

### CR-02: `safe_str` Does Not Cover Short Jira Server PAT Tokens

**Files modified:** `quirk/util/safe_exc.py`, `tests/test_notify_safe_str_secrets.py`
**Commit:** `49da2d9`
**Applied fix:** Added one new pattern to `_SENSITIVE_PATTERNS` (ADD only, no existing patterns
modified):
```python
re.compile(r"(basic_auth|token_auth)\s*=\s*[\('\"]\S+", re.IGNORECASE)
```
This catches the `basic_auth=('user@co.com', 'shortpat')` and `token_auth='shortpat'` shapes
in exception messages without requiring 40+ char tokens. Existing patterns are unaffected.
Added regression tests: `test_jira_basic_auth_short_pat_is_redacted` (24-char PAT),
`test_jira_token_auth_is_redacted` (13-char PAT).

### WR-01: Empty `project_key` Silently Causes All Findings to Fail

**Files modified:** `quirk/ticketing/config.py`, `tests/test_ticketing_jira.py`
**Commit:** `72d5c72` (subsumed by CR-01 fix — same commit)
**Applied fix:** The `_PROJECT_KEY_RE` regex requires at least one character matching
`[A-Z][A-Z0-9]{1,99}`, so the empty string `""` (default when `project_key` is absent from
config) fails the match and returns `None`. No separate code change needed beyond CR-01.
Covered by `test_empty_project_key_rejected`.

### WR-02: `auth_mode` Not Validated Against Allowed Values

**Files modified:** `quirk/ticketing/config.py`, `tests/test_ticketing_jira.py`
**Commit:** `72d5c72` (same commit as CR-01/WR-01)
**Applied fix:** Added `_VALID_AUTH_MODES = frozenset({"cloud", "server"})` constant.
In `_parse_jira_cfg`, after lowercasing `auth_mode`, if the value is not in
`_VALID_AUTH_MODES`, the function returns `None`. Unknown values such as `"oauth"`,
`"cloud "` (trailing space), `"basic"`, and `""` are all rejected. Note: `"Cloud"` (mixed
case) is normalised to `"cloud"` by `.lower()` before validation — this is correct and
permissive behaviour matching the original intent. Regression test: `test_invalid_auth_mode_rejected`.

### WR-03: `scan_id` Derived from Filename May Exceed `String(64)`

**Files modified:** `quirk/cli/ticket_cmd.py`
**Commit:** `9566f9c`
**Applied fix:** Changed `scan_id = Path(findings_path).name` to
`scan_id = Path(findings_path).stem[:64]`. Using `.stem` drops the `.json` extension
(keeping the timestamp portion), and `[:64]` caps the value to fit within the
`IntegrationDelivery.scan_id` column declaration.

### WR-04: Per-Row Commit Silent Failure Mode

**Files modified:** `quirk/ticketing/base.py`, `quirk/cli/ticket_cmd.py`
**Commit:** `e5c79a3`
**Applied fix:** Added a docstring note to `dispatch_finding` explaining the deferred-commit
semantics — that a failed per-row `db.commit()` leaves the row in-session to be committed
by the next successful commit or the `get_session` exit commit, and what happens when all
commits fail. Improved the catch-all error message in `ticket_cmd.py` to explicitly state
"audit-row persistence failed, no audit records were saved" so users can distinguish a DB
storage failure from individual per-finding delivery failures.

---

_Fixed: 2026-05-25_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
