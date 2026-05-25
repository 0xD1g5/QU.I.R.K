---
phase: 104-jira-ticketing
reviewed: 2026-05-25T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - quirk/ticketing/base.py
  - quirk/ticketing/jira.py
  - quirk/ticketing/config.py
  - quirk/cli/ticket_cmd.py
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 104: Code Review Report

**Reviewed:** 2026-05-25
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Four files reviewed covering the Jira ticketing backend: the ABC orchestration layer
(`base.py`), the Jira REST adapter (`jira.py`), the config loader (`config.py`), and
the CLI entry point (`ticket_cmd.py`). The overall architecture is sound — fingerprint
formula is stable and collision-resistant, `safe_str` wraps every exception path in the
hot dispatch loop, and the lazy jira import correctly avoids the optional-extra import
trap. The dedup half-state and audit-row commit ordering are acceptable.

Two blockers found: JQL injection via an unvalidated `project_key` and a credential
leak gap in `safe_str` for short Jira Server PAT tokens. Four warnings cover silent
misconfiguration paths and a session double-commit pattern. Three info items cover
dead imports, unnecessary lazy import of stdlib `os`, and misleading noqa comments.

---

## Critical Issues

### CR-01: JQL Injection via Unvalidated `project_key`

**File:** `quirk/ticketing/jira.py:97`

**Issue:** `find_by_fingerprint` builds JQL by double-quoting `project_key` sourced
from the YAML config:

```python
jql = f'project = "{self._cfg.project_key}" AND labels = "{fp}"'
```

A `project_key` containing a double-quote character breaks out of the quoted context.
For example, if a user (or attacker with config write access) sets:

```yaml
project_key: 'SEC" OR project = PRIVATE AND labels = "'
```

The resulting JQL becomes:

```jql
project = "SEC" OR project = PRIVATE AND labels = "" AND labels = "fp_value"
```

This makes `find_by_fingerprint` return issues from `PRIVATE` (an arbitrary project),
causing `add_rediscovery_comment` to append comments to tickets in unintended projects
rather than creating new issues. The `fp` label is 64-char hex so it is safe, but
`project_key` is entirely user/config-controlled and is never validated.

Note: `create_issue_from_finding` passes `project_key` as a JSON field value (not JQL),
so that path is not injectable — the injection is confined to the search.

**Fix:** Validate `project_key` in `_parse_jira_cfg` (config.py) against the Jira
project key format (`[A-Z][A-Z0-9]+`). Reject or strip invalid values at load time:

```python
import re as _re
_PROJECT_KEY_RE = _re.compile(r'^[A-Z][A-Z0-9]{1,99}$')

def _parse_jira_cfg(raw: dict) -> Optional[JiraTicketingCfg]:
    if not raw:
        return None
    jira_url = raw.get("jira_url")
    if not jira_url:
        return None
    project_key = str(raw.get("project_key", ""))
    if not _PROJECT_KEY_RE.match(project_key):
        return None   # treat as misconfigured — same path as missing jira_url
    return JiraTicketingCfg(
        ...
        project_key=project_key,
        ...
    )
```

Alternatively, escape `project_key` in the JQL string (Jira JQL escapes `"` as `\"`),
but input validation at config parse time is the safer and simpler approach.

---

### CR-02: `safe_str` Does Not Cover Short Jira Server PAT Tokens

**File:** `quirk/util/safe_exc.py` (affects `quirk/ticketing/base.py:124`)

**Issue:** `safe_str` redacts tokens using the pattern `\b[A-Za-z0-9+/]{40,}={0,2}\b`
(40+ character sequences). Jira Server Personal Access Tokens (PATs) can be shorter than
40 characters. If the `jira` Python library surfaces a PAT in an exception message as a
raw string (rather than the base64-encoded Authorization header), `safe_str` will not
redact it. The credential then flows into `error_summary` in the `integration_deliveries`
SQLite table, violating ISEC-02.

Plant-a-token test (24-char PAT, realistic for Jira Server):

```python
import re
token = "ABCDEFGHIJKLMNabcdefghij"          # 24 chars
msg = f"JIRAError: 401 Unauthorized, basic_auth=('user@co.com', '{token}')"
pattern = re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b")
assert not pattern.search(msg)              # token is NOT caught — leaks to DB
```

When the `jira` library encodes credentials as an `Authorization: Basic <base64>`
header value (56 chars), it IS caught. The gap is specifically raw credential reprs
in error messages (e.g., `JIRAError` `args` tuple, connection errors that include the
raw token string). The risk is lower for Jira Cloud (new ATATT tokens are 200+ chars)
but applies to Jira Server/Data Center PATs which have no length floor.

**Fix:** Add a Jira-specific pattern to `_SENSITIVE_PATTERNS` in `safe_exc.py` that
covers short alphanumeric tokens appearing in `basic_auth=` or `token_auth=` context:

```python
# Jira/generic basic_auth tuple repr: basic_auth=('user', 'token') or token_auth=value
re.compile(r"(basic_auth|token_auth)\s*=\s*[\('\"]\S+", re.IGNORECASE),
```

This catches the tuple repr `basic_auth=('user@co.com', 'shorttoken')` without
requiring the token to be 40+ chars. Combine with the existing 40+ pattern for defense
in depth.

---

## Warnings

### WR-01: Empty `project_key` Silently Causes All Findings to Fail

**File:** `quirk/ticketing/config.py:88`

**Issue:** `_parse_jira_cfg` defaults `project_key` to `""` when missing from config:

```python
project_key=str(raw.get("project_key", "")),
```

An empty `project_key` passes `_parse_jira_cfg` and `JiraChannel.__init__` without
error, but produces invalid JQL at dispatch time:

```jql
project = "" AND labels = "fp_value"
```

Jira rejects this, raising `JIRAError`. Because `dispatch_finding` catches all
exceptions, every finding silently logs `status="failed"` in the audit table. The user
sees `"Ticket run complete: N finding(s) processed."` at the CLI with no indication
that zero tickets were actually created.

**Fix:** Validate `project_key` is non-empty in `_parse_jira_cfg` (return `None` if
empty), which causes `ticket_cmd.py` to print a clear "ticketing config not found" error
at line 125 instead of silently failing per-finding. This fix is subsumed by CR-01's
regex validation.

---

### WR-02: `auth_mode` Is Not Validated Against Allowed Values

**File:** `quirk/ticketing/config.py:90`, `quirk/ticketing/jira.py:75`

**Issue:** `_parse_jira_cfg` normalizes `auth_mode` to lowercase but never validates it
against `{"cloud", "server"}`. `JiraChannel.__init__` uses `if cfg.auth_mode == "cloud"`
with an unguarded `else` — any value other than `"cloud"` (including typos like
`"Cloud"`, `"oauth"`, or `"cloud "`) silently falls to the `token_auth` branch,
constructing a Jira client with the wrong authentication mode. For the `"cloud"` case
this results in a 401 at query time; for `"server"` it would use `basic_auth` as a PAT
which the server rejects. Error is silent until dispatch time.

**Fix:** Add a validation guard in `_parse_jira_cfg` or `JiraChannel.__init__`:

```python
# In _parse_jira_cfg:
auth_mode = str(raw.get("auth_mode", "cloud")).lower()
if auth_mode not in {"cloud", "server"}:
    return None  # treat as misconfigured
```

---

### WR-03: `scan_id` Derived from Filename May Exceed `String(64)` Column Length

**File:** `quirk/cli/ticket_cmd.py:138`

**Issue:** `scan_id` is set to `Path(findings_path).name` — the bare filename of the
findings JSON. The `IntegrationDelivery.scan_id` column is declared `String(64)`. With
SQLite's advisory length semantics this does not raise an error (SQLite stores any
string length regardless of `VARCHAR(64)` declarations), but it is semantically wrong
and will break if the schema is ever migrated to a strict RDBMS.

A user passing `--input` with a long filename (e.g. 100+ chars) produces a `scan_id`
that silently exceeds the column declaration. For consistent audit records, `scan_id`
should match the ISO timestamp format used by other integration phases.

**Fix:** Truncate or canonicalize the scan_id to fit within 64 chars:

```python
scan_id = Path(findings_path).stem[:64]   # drop .json, cap at 64
```

Or, better: reuse the same `current_session_ts` approach as the notification and SIEM
phases to keep `scan_id` consistent across integration destinations.

---

### WR-04: `get_session` Auto-Commit on Exit Races With `dispatch_finding` Per-Row Commits

**File:** `quirk/cli/ticket_cmd.py:141-143`, `quirk/ticketing/base.py:141-144`

**Issue:** `dispatch_finding` calls `db.commit()` after each audit row (base.py:142),
then `get_session`'s context manager calls `session.commit()` again on normal exit
(db.py:430). While the final commit is a no-op when the session is clean, there is a
subtle interaction: if `db.commit()` inside `dispatch_finding` fails and is caught
(base.py:143-144), the un-committed row remains in the session. The row is eventually
committed by the next finding's `db.commit()` or by `get_session`'s exit commit. This
is broadly correct, but the intent (one commit per finding) and the actual behavior
(commit may be deferred) diverge silently.

More importantly, if ALL per-finding commits fail (e.g., disk full), all rows accumulate
in-session and `get_session`'s exit commit tries to commit all of them in one shot. If
that fails, `get_session`'s `except` block rolls back and re-raises, which the outer
`except` in `ticket_cmd.py:148` catches and exits 2 — losing all audit rows. The user
sees a DB error but no indication of which findings were attempted.

**Fix:** This is an architectural constraint of the WR-01 audit pattern. Mitigation:
document in `dispatch_finding`'s docstring that the per-row commit may be deferred to
the session exit commit, and ensure the caller (ticket_cmd.py) handles the DB exception
with a more descriptive message distinguishing "delivery failed" from "audit row lost".

---

## Info

### IN-01: Dead Import of `safe_str` in `jira.py` With Misleading Comment

**File:** `quirk/ticketing/jira.py:20`

**Issue:** `safe_str` is imported from `quirk.util.safe_exc` with `# noqa: F401` and
the comment "imported for subclass-context use". It is never called in `jira.py`'s
methods. `JiraChannel` has no subclasses, and even if it did, subclasses import from
their own scope. The base class already imports `safe_str` at `base.py:27`. The import
is dead code and the comment rationale is incorrect.

**Fix:** Remove the import:

```python
# Remove this line from jira.py:
from quirk.util.safe_exc import safe_str  # noqa: F401 — imported for subclass-context use
```

---

### IN-02: Unnecessary Lazy Import of Stdlib `os` in `ticket_cmd.py`

**File:** `quirk/cli/ticket_cmd.py:134`

**Issue:** `os` is imported inside the `try` block at line 134 alongside the optional
third-party imports (`get_session`, `JiraChannel`). This is unnecessarily unusual —
`os` is stdlib and always available. The comment `# noqa: PLC0415` (intentional local
import for optional-extra safety) is misleading; the rationale applies to `jira` and
`get_session`, not to `os`. Moving `os` to module-scope imports improves readability
and avoids confusing future readers about why a stdlib module is lazily imported.

**Fix:**

```python
# At module scope (with other imports):
import os
```

Remove `import os  # noqa: PLC0415` from the try block at line 134.

---

### IN-03: SSRF Error Message Omits the Rejected URL

**File:** `quirk/ticketing/jira.py:64-66`

**Issue:** When `validate_external_url` rejects `cfg.jira_url`, the raised `ValueError`
message is:

```python
raise ValueError(f"SSRF blocked ({result.reason}) for Jira URL")
```

`result.redacted_preview` (a ≤32-char control-char-stripped snippet of the URL) is
available but not included. The `jira_url` is not a credential — including the redacted
preview would help operators identify which URL is misconfigured without any security
downside.

**Fix:**

```python
raise ValueError(
    f"SSRF blocked ({result.reason}) for Jira URL: {result.redacted_preview!r}"
)
```

This matches the `redacted_preview` pattern from the existing validator design (D-08)
and does not expose any credential material.

---

_Reviewed: 2026-05-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
