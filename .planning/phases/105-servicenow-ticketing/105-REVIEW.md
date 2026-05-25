---
phase: 105-servicenow-ticketing
reviewed: 2026-05-25T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - quirk/ticketing/servicenow.py
  - quirk/ticketing/config.py
  - quirk/cli/ticket_cmd.py
findings:
  critical: 1
  warning: 3
  info: 1
  total: 5
status: issues_found
---

# Phase 105: Code Review Report

**Reviewed:** 2026-05-25T00:00:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Phase 105 adds the ServiceNow Table API ticketing backend (`ServiceNowChannel`) on top
of the Phase 104 `TicketingChannel` ABC. The SSRF guard, https-only enforcement at parse
time, `_NoRedirectHandler`, and dedup logic are all correctly wired. The `safe_str`
scrubbing in `dispatch_finding` (inherited from `base.py`) operates correctly for the
realistic HTTPError exception shapes. However, one missing input-validation guard in
`_parse_servicenow_cfg` permits URL path injection via a config-controlled `table` value,
and three further issues degrade correctness, security posture confidence, and
operability.

---

## Critical Issues

### CR-01: `table` name accepted without validation — URL path injection

**File:** `quirk/ticketing/config.py:163`

**Issue:** `_parse_servicenow_cfg` validates `instance_url` (https-only check) and
`user_env`/`password_env` (non-empty check) but accepts any string for `table` and
interpolates it verbatim into three URL path segments:

```python
# servicenow.py:106
url = f"{self._cfg.instance_url}/api/now/table/{self._cfg.table}?{params}"

# servicenow.py:138
url = f"{self._cfg.instance_url}/api/now/table/{self._cfg.table}"

# servicenow.py:175
url = f"{self._cfg.instance_url}/api/now/table/{self._cfg.table}/{issue_key}"
```

A config-controlled value such as `table: "incident/../../admin"` or
`table: "incident?sysparm_query=active=true"` produces:

```
https://myco.service-now.com/api/now/table/incident/../../admin
https://myco.service-now.com/api/now/table/incident?sysparm_query=active=true&sysparm_limit=1...
```

urllib does NOT normalize `..` path segments before sending the request. The path
traversal variant lets an attacker redirect the POST/PATCH to arbitrary Table API
endpoints. The query-injection variant appends operator-controlled query parameters
before the legitimate `sysparm_query=correlation_id=<fp>` pair, which may cause the GET
to match against unintended records and suppress incident creation.

While exploiting this requires write access to the YAML config file, the analogous Jira
`project_key` field is already gated by `_PROJECT_KEY_RE` precisely because config values
are an injection surface. Parity with Jira's precedent is missing here.

**Fix:**
```python
# In quirk/ticketing/config.py — add before _parse_servicenow_cfg returns

# ServiceNow table names: lowercase letters, digits, underscores; 1-80 chars.
_TABLE_NAME_RE = _re.compile(r"^[a-z_][a-z0-9_]{0,79}$")

def _parse_servicenow_cfg(raw: dict) -> Optional[ServiceNowTicketingCfg]:
    ...
    table = str(raw.get("table", "incident"))
    if not _TABLE_NAME_RE.match(table):
        return None          # misconfigured — same pattern as invalid project_key
    return ServiceNowTicketingCfg(
        instance_url=str(instance_url),
        user_env=user_env,
        password_env=password_env,
        table=table,
        allow_internal=bool(raw.get("allow_internal", False)),
    )
```

---

## Warnings

### WR-01: `safe_str` is imported but never called — ISEC-02 claim is inaccurate

**File:** `quirk/ticketing/servicenow.py:25`

**Issue:** The module docstring declares `ISEC-02: safe_str(exc) on all exception
surfaces — never str(exc) or repr(exc)`. The import is marked `noqa: F401` with a
comment `imported for subclass-context use`, which is semantically incorrect: this file
IS the subclass; there is no further subclassing. More critically, none of the three
`except` blocks call `safe_str`. They call it implicitly safe because they discard `exc`
entirely and raise new `RuntimeError` with hardcoded strings — which is actually a
correct and safe pattern, but it contradicts the stated ISEC-02 contract. This creates
a documentation-to-code mismatch that misleads future reviewers into believing safe_str
is active on these paths when it is not:

```python
except urllib.error.HTTPError as exc:
    raise RuntimeError(f"ServiceNow GET failed: HTTP {exc.code}") from exc
    # safe_str is never called here; exc.reason is never interpolated either.
```

If a future developer changes an error message to include `exc.reason` (a
server-controlled string that CAN contain reflected credentials in theory), the
missing safe_str call becomes a real leak.

**Fix:** Either call `safe_str` explicitly and remove the misleading ISEC-02 claim from
the module docstring, or update the docstring to accurately describe the actual
credential-safety technique used (discarding `exc`, interpolating only `exc.code`):

```python
# Option A — make the claim true by using safe_str
except urllib.error.HTTPError as exc:
    raise RuntimeError(f"ServiceNow GET failed: HTTP {exc.code}: {safe_str(exc)}") from exc

# Option B — update module docstring to accurate language
#   ISEC-02: all except blocks raise new RuntimeError with exc.code only (integer);
#            exc.reason (server-controlled) is never interpolated. safe_str is imported
#            by base class convention but is not required here.
```

---

### WR-02: Misleading error message when `ServiceNowChannel.__init__` fails in `ticket_cmd.py`

**File:** `quirk/cli/ticket_cmd.py:175-186`

**Issue:** The outer `except Exception` block in `run_ticket` prints:

```
ERROR: ticket command failed — audit-row persistence failed, no audit records were saved: ...
```

This message is displayed for *every* exception that escapes the try block, including
`ValueError` from `ServiceNowChannel.__init__` (SSRF blocked), `ImportError` if a
required module fails, or a DB-connection failure at `get_session`. When an operator
sees `SSRF blocked (loopback) for ServiceNow URL` appended to the phrase
`audit-row persistence failed`, they are given an actively wrong diagnosis. The comment
in the code also describes the handler as catching "DB error after dispatch loop" — but
the try block begins before channel construction, so many non-DB errors land here.

**Fix:** Separate channel-construction errors from the dispatch/DB loop:

```python
# Build the channel outside the dispatch try block
if args.backend == "servicenow":
    if cfg.servicenow is None:
        print("ERROR: ...", file=sys.stderr)
        sys.exit(2)
    try:
        from quirk.ticketing.servicenow import ServiceNowChannel  # noqa: PLC0415
        channel = ServiceNowChannel(cfg.servicenow)
    except (ValueError, ImportError) as exc:
        print(f"ERROR: could not initialize ServiceNow channel: {safe_str(exc)}", file=sys.stderr)
        sys.exit(2)
else:
    ...  # same pattern for jira

# Then the dispatch loop in its own try block with the accurate error message
try:
    with get_session(db_path) as db:
        for finding in findings:
            channel.dispatch_finding(finding, db, scan_id=scan_id)
    print(f"Ticket run complete: {len(findings)} finding(s) processed.")
except Exception as exc:
    print(f"ERROR: audit-row persistence failed, no audit records saved: {safe_str(exc)}", file=sys.stderr)
    sys.exit(2)
```

---

### WR-03: `create_issue_from_finding` raises undiagnosed `KeyError` on malformed POST response

**File:** `quirk/ticketing/servicenow.py:158`

**Issue:** After a successful POST (HTTP 201), the code unconditionally indexes:

```python
return data["result"]["sys_id"]  # 32-char hex — NOT INC-number (Pitfall 2)
```

If the ServiceNow instance returns a 201 with a non-standard body (missing `"result"`
key, `"result"` is `null`, or `"sys_id"` absent from the result dict), this raises a
bare `KeyError` or `TypeError`. The `dispatch_finding` base class catches it, but the
audit `error_summary` recorded in the DB will be `"KeyError: 'result'"` or
`"KeyError: 'sys_id'"` with no indication that a ServiceNow POST response was malformed.
Additionally, `find_by_fingerprint` has the same gap for the `"result"` key (though
`data.get("result", [])` makes that path safer).

The same `data["result"]["sys_id"]` pattern also fires in `create_issue_from_finding`
without any JSON parse error handling — `json.loads` raising `ValueError`/`JSONDecodeError`
is also uncaught at this layer (propagates to `dispatch_finding`, again with poor context).

**Fix:**

```python
try:
    with opener.open(req, timeout=10) as resp:
        raw = resp.read().decode("utf-8")
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise RuntimeError("ServiceNow POST returned non-JSON response") from exc
    result = data.get("result") or {}
    sys_id = result.get("sys_id") if isinstance(result, dict) else None
    if not sys_id:
        raise RuntimeError(
            f"ServiceNow POST response missing result.sys_id; body snippet: {raw[:120]!r}"
        )
    return sys_id
except urllib.error.HTTPError as exc:
    raise RuntimeError(f"ServiceNow POST failed: HTTP {exc.code}") from exc
except urllib.error.URLError as exc:
    raise RuntimeError("ServiceNow POST failed: connection error") from exc
```

Apply the same pattern to `find_by_fingerprint` for the JSON parse path.

---

## Info

### IN-01: `test_credentials_not_in_logs` only exercises the long-base64 path through `safe_str`

**File:** `tests/test_ticketing_servicenow.py:331-333`

**Issue:** The test deliberately selects a 46-char base64 string and asserts it is
`>= 40` chars to trigger the `_SENSITIVE_PATTERNS` long-base64 scrubber. The test
leaves uncovered a class of short credentials (e.g., `base64("admin:abc")` = 12 chars)
where `safe_str` would NOT suppress the value — unless the `"Authorization: Basic "`
prefix pattern fires. Concretely, `"Basic YWRtaW46YWJj"` (12-char payload, no header
name prefix) passes through `safe_str` unchanged. While `urllib.error.HTTPError`
does not currently include request headers in `str(exc)`, the test does not guard the
path where a future error message includes the bare `"Basic <short_b64>"` auth header
value.

This is an informational gap — not a current exploit path — but it represents a
latent hole in the safe_str coverage that a refactor could activate.

**Suggestion:** Add a test case with `"Basic YWRtaW46YWJj"` (short base64, no prefix)
to confirm behaviour, and document whether the current design intentionally relies on
urllib never including request headers in exception text.

---

_Reviewed: 2026-05-25T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
