---
phase: 105-servicenow-ticketing
reviewed: 2026-05-25T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - quirk/ticketing/config.py
  - quirk/ticketing/servicenow.py
  - quirk/cli/ticket_cmd.py
findings:
  critical: 0
  warning: 0
  info: 1
  total: 1
status: clean
---

# Phase 105: Code Review Report (Iteration 2)

**Reviewed:** 2026-05-25
**Depth:** standard
**Files Reviewed:** 3
**Status:** clean

## Summary

Iteration-2 review of the Phase 105 ServiceNow ticketing backend. All four findings from
iteration 1 (CR-01 URL path injection, WR-01 bare `str(exc)` on URLError, WR-02 channel-init
inside dispatch try-block, WR-03 unguarded `json.loads` / `.sys_id`) are correctly closed.
One INFO-level observation is noted. The TICKET-04 structural invariant (zero changes to
`base.py` or `jira.py`) is confirmed via `git log`.

## Structural Findings (fallow)

No structural pre-pass provided for this iteration.

## Narrative Findings (AI reviewer)

### Closed findings — confirmation

**CR-01 — URL path injection via `table` config value (CLOSED)**

`_TABLE_NAME_RE = ^[a-z_][a-z0-9_]{0,79}$` is applied in `_parse_servicenow_cfg`
(`config.py:165`). The regex provably blocks `/`, `..`, `?`, `&`, `%`, uppercase, and the
empty string. It is the single gate for all config-controlled values that reach the URL path:

- `instance_url` — validated by `validate_external_url()` at `__init__` time (SSRF guard).
- `table` — gated by `_TABLE_NAME_RE` at parse time; reaches URL at `servicenow.py:109,145,193`.
- `correlation_id` (`fp`) — SHA-256 hex fingerprint, passed through `urlencode()` as a query
  param value; percent-encoding applied by the stdlib before transmission.
- `short_description` / `description` / `work_notes` — JSON body values encoded by
  `json.dumps`; not URL components; no injection vector.

No other config-controlled value reaches the URL or query string. **CLOSED.**

**WR-01 — bare `str(exc)` / `exc.reason` on URLError (CLOSED)**

All `urllib.error.URLError` branches apply `safe_str(exc)` (`servicenow.py:128,180,218`).
`urllib.error.HTTPError` branches use only `exc.code` (int) — inherently safe, no
server-controlled string content. `safe_str` scrubs base64-shaped tokens, Authorization
headers, and connection-string credentials per `quirk/util/safe_exc.py`. **CLOSED.**

**WR-02 — channel construction inside dispatch try-block (CLOSED)**

Channel construction is extracted to `ticket_cmd.py:155-180`, before the dispatch `try`
block at line 183. `ValueError` / `ImportError` from `ServiceNowChannel.__init__` or
`JiraChannel.__init__` now produce `"ERROR: ticketing backend init failed: ..."`. The
default-jira `else` branch at lines 164-180 is structurally equivalent to the prior code
and is untouched. Exit codes (2 on all failure paths) are unchanged. **CLOSED.**

**WR-03 — unguarded `json.loads` / `.sys_id` access (CLOSED)**

Both GET and POST responses wrap `json.loads` in `try/except ValueError` -> `RuntimeError`
(`servicenow.py:119-122`, `165-168`). `result.get("sys_id")` is guarded by an
`isinstance(result, dict)` check plus an explicit None-check with a descriptive
`RuntimeError` at lines 169-175. The happy path (valid JSON response with `result.sys_id`
present) returns `sys_id` directly without obstruction. **CLOSED.**

**TICKET-04 — zero changes to `base.py` / `jira.py` (CONFIRMED)**

`git log` confirms `quirk/ticketing/base.py` and `quirk/ticketing/jira.py` were last
modified in Phase 104 commits (`ccab2a4`, `04470de`, `e5c79a3`). No Phase 105 commit
touches either file. The structural invariant holds.

---

## Info

### IN-01: Server response body snippet reflected verbatim in RuntimeError

**File:** `quirk/ticketing/servicenow.py:173-175`
**Issue:** When the ServiceNow POST response is valid JSON but lacks `result.sys_id`, the
first 120 bytes of the raw response body are included in the `RuntimeError` message:
```python
f"ServiceNow POST response missing result.sys_id; body snippet: {raw[:120]!r}"
```
This is server-controlled content that surfaces in whatever logging or monitoring
infrastructure catches the exception. In normal operation the body is a ServiceNow API
response (not a request), so no QUIRK credentials are present. The ServiceNow server
itself could theoretically include unexpected content in the 120-char window.
**Fix:** Not required before ship. If hardening is desired, drop `raw[:120]` from the
message and rely on the structured error text alone. Alternatively, apply a regex or
`safe_str`-style scrub before reflecting the body.

---

_Reviewed: 2026-05-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 2 (final)_
