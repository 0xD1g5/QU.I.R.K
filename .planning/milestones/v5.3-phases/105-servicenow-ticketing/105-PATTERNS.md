# Phase 105: ServiceNow Ticketing - Pattern Map

**Mapped:** 2026-05-25
**Files analyzed:** 4 (1 new service, 1 config modify, 1 CLI modify, 1 new test)
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/ticketing/servicenow.py` | service | request-response | `quirk/ticketing/jira.py` (subclass shape) + `quirk/notify/channels/webhook.py` (urllib mechanics) | exact (two analogs combined) |
| `quirk/ticketing/config.py` | config | CRUD | `quirk/ticketing/config.py` existing JiraTicketingCfg + _parse_jira_cfg pattern | self-analog (extend in-place) |
| `quirk/cli/ticket_cmd.py` | controller | request-response | `quirk/cli/ticket_cmd.py` existing run_ticket dispatch | self-analog (extend in-place) |
| `tests/test_ticketing_servicenow.py` | test | request-response | `tests/test_ticketing_jira.py` (mocked-client structure) + `tests/test_notify_webhook.py` (_FakeOpener / build_opener patch pattern) | exact (two analogs combined) |

---

## Pattern Assignments

### `quirk/ticketing/servicenow.py` (service, request-response)

**Primary analog:** `quirk/ticketing/jira.py` — subclass shape, __init__ structure, method signatures
**Secondary analog:** `quirk/notify/channels/webhook.py` — urllib mechanics, _NoRedirectHandler, build_opener

**Imports pattern** (from `quirk/ticketing/jira.py` lines 13-23):
```python
from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Optional
from urllib.parse import urlencode

from quirk.ticketing.base import TicketingChannel
from quirk.util.safe_exc import safe_str  # noqa: F401 — imported for subclass-context use
from quirk.util.url_allowlist import validate_external_url

logger = logging.getLogger(__name__)
```

**_NoRedirectHandler pattern — copy verbatim** (from `quirk/notify/channels/webhook.py` lines 29-41):
```python
class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Block all HTTP redirects to prevent post-validation SSRF bypass."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url, code, "Redirect blocked (SSRF guard)", headers, fp
        )
```

**destination class var + __init__ pattern** (mirroring `quirk/ticketing/jira.py` lines 40-82):
```python
class ServiceNowChannel(TicketingChannel):
    destination = "servicenow"

    def __init__(self, cfg: "ServiceNowTicketingCfg") -> None:
        # SSRF guard at construction time (ISEC-01) — mirror jira.py lines 61-66
        result = validate_external_url(cfg.instance_url, allow_internal=cfg.allow_internal)
        if not result.ok:
            raise ValueError(
                f"SSRF blocked ({result.reason}) for ServiceNow URL"
            )

        self._cfg = cfg

        # Resolve creds at construction time — env-var NAMES in cfg, not values
        # Mirror jira.py lines 70-73 (os.environ.get(cfg.<env_name>, ""))
        user = os.environ.get(cfg.user_env, "")
        password = os.environ.get(cfg.password_env, "")
        creds = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        self._auth_header = f"Basic {creds}"
        # self._auth_header is NEVER logged — safe_str scrubs it if it leaks in exc
```

**Core urllib request pattern — GET** (derived from `quirk/notify/channels/webhook.py` lines 74-94 + method= extension):
```python
def find_by_fingerprint(self, fp: str) -> Optional[str]:
    params = urlencode({
        "sysparm_query": f"correlation_id={fp}",
        "sysparm_limit": "1",
        "sysparm_fields": "sys_id",
    })
    url = f"{self._cfg.instance_url}/api/now/table/{self._cfg.table}?{params}"
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Authorization": self._auth_header},
        method="GET",
    )
    opener = urllib.request.build_opener(_NoRedirectHandler)
    try:
        with opener.open(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = data.get("result", [])
        return results[0]["sys_id"] if results else None
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"ServiceNow GET failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("ServiceNow GET failed: connection error") from exc
```

**Core urllib request pattern — POST** (from `quirk/notify/channels/webhook.py` lines 74-94):
```python
def create_issue_from_finding(self, finding: dict, fp: str, evidence: str) -> str:
    url = f"{self._cfg.instance_url}/api/now/table/{self._cfg.table}"
    body = json.dumps({
        "short_description": str(finding.get("title", "QUIRK Finding"))[:255],
        "description": evidence,
        "correlation_id": fp,
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self._auth_header,
        },
        method="POST",
    )
    opener = urllib.request.build_opener(_NoRedirectHandler)
    try:
        with opener.open(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["result"]["sys_id"]   # 32-char hex — NOT INC-number
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"ServiceNow POST failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("ServiceNow POST failed: connection error") from exc
```

**Core urllib request pattern — PATCH** (method= same as above; note PATCH not PUT for work_notes):
```python
def add_rediscovery_comment(self, issue_key: str, fp: str) -> None:
    # issue_key IS the sys_id returned by create_issue_from_finding
    url = f"{self._cfg.instance_url}/api/now/table/{self._cfg.table}/{issue_key}"
    body = json.dumps({
        "work_notes": (
            f"Rediscovery: QUIRK re-detected this finding on a subsequent scan.\n"
            f"Fingerprint: {fp}"
        )
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self._auth_header,
        },
        method="PATCH",   # MUST be PATCH — POST/PUT do not append work_notes visibly (KB0623936)
    )
    opener = urllib.request.build_opener(_NoRedirectHandler)
    try:
        with opener.open(req, timeout=10) as resp:
            if resp.status not in (200, 201):
                raise RuntimeError(f"ServiceNow PATCH returned HTTP {resp.status}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"ServiceNow PATCH failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("ServiceNow PATCH failed: connection error") from exc
```

**DO NOT override:** `compute_fingerprint` — inherited from `base.py` line 66. Overriding breaks cross-backend fingerprint identity.

---

### `quirk/ticketing/config.py` — MODIFY (config, CRUD)

**Analog:** `quirk/ticketing/config.py` — self-analog; extend the existing JiraTicketingCfg pattern

**Existing dataclass pattern to mirror** (lines 24-41):
```python
@dataclass
class JiraTicketingCfg:
    jira_url: str
    jira_user_env: str        # env-var NAME, not the credential value
    jira_token_env: str       # env-var NAME, not the credential value
    project_key: str
    issue_type: str = "Bug"
    auth_mode: str = "cloud"
    allow_internal: bool = False
```

**New dataclass to add** (mirror shape exactly):
```python
@dataclass
class ServiceNowTicketingCfg:
    instance_url: str         # e.g. https://myco.service-now.com — MUST be https://
    user_env: str             # env-var NAME holding username
    password_env: str         # env-var NAME holding password/token
    table: str = "incident"   # default table — locked by CONTEXT.md
    allow_internal: bool = False
```

**TicketingCfg container — extend** (currently line 44-47):
```python
# BEFORE (line 44-47):
@dataclass
class TicketingCfg:
    jira: Optional[JiraTicketingCfg] = None

# AFTER:
@dataclass
class TicketingCfg:
    jira: Optional[JiraTicketingCfg] = None
    servicenow: Optional[ServiceNowTicketingCfg] = None   # ADD
```

**_parse_ticketing_cfg — extend** (currently line 79-82):
```python
# BEFORE:
def _parse_ticketing_cfg(raw: dict) -> TicketingCfg:
    jira_raw = raw.get("jira") or {}
    return TicketingCfg(jira=_parse_jira_cfg(jira_raw))

# AFTER:
def _parse_ticketing_cfg(raw: dict) -> TicketingCfg:
    jira_raw = raw.get("jira") or {}
    servicenow_raw = raw.get("servicenow") or {}
    return TicketingCfg(
        jira=_parse_jira_cfg(jira_raw),
        servicenow=_parse_servicenow_cfg(servicenow_raw),   # ADD
    )
```

**New _parse_servicenow_cfg — mirror _parse_jira_cfg** (lines 85-112 as template):
```python
def _parse_servicenow_cfg(raw: dict) -> Optional[ServiceNowTicketingCfg]:
    """Parse the servicenow sub-block. Returns None if missing or invalid.

    Validation guards:
      - instance_url must start with https:// (cleartext Basic auth is a security failure).
      - user_env and password_env must be non-empty strings.
    """
    if not raw:
        return None
    instance_url = raw.get("instance_url")
    if not instance_url:
        return None
    # Reject http:// at parse time — creds in Authorization header must not transit plaintext
    if not str(instance_url).startswith("https://"):
        return None
    user_env = str(raw.get("user_env", ""))
    password_env = str(raw.get("password_env", ""))
    if not user_env or not password_env:
        return None
    return ServiceNowTicketingCfg(
        instance_url=str(instance_url),
        user_env=user_env,
        password_env=password_env,
        table=str(raw.get("table", "incident")),
        allow_internal=bool(raw.get("allow_internal", False)),
    )
```

---

### `quirk/cli/ticket_cmd.py` — MODIFY (controller, request-response)

**Analog:** `quirk/cli/ticket_cmd.py` — self-analog; extend existing run_ticket

**add_argument pattern to add** (after the existing `--output-dir` argument, before `args = parser.parse_args(argv)`):
```python
parser.add_argument(
    "--backend",
    choices=["jira", "servicenow"],
    default="jira",
    help="Ticketing backend to use (default: jira)",
)
```

**Extra gate message — update** (currently line 89):
```python
# BEFORE (line 89):
"ERROR: Jira ticketing skipped — run `pip install quirk[tickets]` to enable.",

# AFTER:
"ERROR: Ticketing skipped — run `pip install quirk[tickets]` to enable.",
```

**Config check + dispatch block — replace** (currently lines 123-143):
```python
# BEFORE (lines 123-143): hard-coded jira check + JiraChannel dispatch

# AFTER: backend-conditional dispatch
cfg = load_ticketing_config()
if cfg is None:
    print(
        "ERROR: ticketing config not found. Set QUIRK_CONFIG_PATH.",
        file=sys.stderr,
    )
    sys.exit(2)

# --- Dispatch findings through selected backend ---
try:
    from quirk.db import get_session  # noqa: PLC0415
    import os  # noqa: PLC0415

    db_path = os.environ.get("QUIRK_DB_PATH") or "quirk.db"
    scan_id = Path(findings_path).stem[:64]

    if args.backend == "servicenow":
        if cfg.servicenow is None:
            print(
                "ERROR: [ticketing.servicenow] block not configured. "
                "Add a servicenow sub-block to QUIRK_CONFIG_PATH.",
                file=sys.stderr,
            )
            sys.exit(2)
        from quirk.ticketing.servicenow import ServiceNowChannel  # noqa: PLC0415
        channel = ServiceNowChannel(cfg.servicenow)
    else:  # default: jira
        if cfg.jira is None:
            print(
                "ERROR: [ticketing.jira] block not configured. "
                "Add a jira sub-block to QUIRK_CONFIG_PATH.",
                file=sys.stderr,
            )
            sys.exit(2)
        from quirk.ticketing.jira import JiraChannel  # noqa: PLC0415
        channel = JiraChannel(cfg.jira)

    with get_session(db_path) as db:
        for finding in findings:
            channel.dispatch_finding(finding, db, scan_id=scan_id)

    print(f"Ticket run complete: {len(findings)} finding(s) processed.")
except SystemExit:
    raise
except Exception as exc:
    err_msg = safe_str(exc)
    print(
        f"ERROR: ticket command failed — audit-row persistence failed, "
        f"no audit records were saved: {err_msg}",
        file=sys.stderr,
    )
    sys.exit(2)
```

---

### `tests/test_ticketing_servicenow.py` (test, request-response)

**Primary analog:** `tests/test_ticketing_jira.py` — file structure, helper functions, monkeypatch env var pattern, dispatch_finding + DB audit row verification
**Secondary analog:** `tests/test_notify_webhook.py` — _FakeOpener / build_opener patch pattern for urllib mocking

**File header + imports pattern** (from `tests/test_ticketing_jira.py` lines 1-22):
```python
"""Unit tests for quirk.ticketing.servicenow — ServiceNowChannel (Phase 105 TICKET-02/TICKET-04).

Covers:
  - test_create_incident: POST creates incident, returns sys_id
  - test_dedup_then_work_notes: second scan finds existing sys_id, PATCHes work_notes
  - test_correlation_id_is_fingerprint: correlation_id in POST body equals compute_fingerprint()
  - test_http_instance_url_rejected: http:// instance_url rejected at config parse
  - test_missing_instance_url: missing instance_url → _parse_servicenow_cfg returns None
  - test_ssrf_guard: internal/loopback instance_url → ValueError at __init__
  - test_credentials_not_in_logs: Basic auth in HTTPError → absent from error_summary (safe_str)
"""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from quirk.ticketing.config import ServiceNowTicketingCfg, _parse_servicenow_cfg
```

**_make_cfg helper pattern** (mirror `tests/test_ticketing_jira.py` lines 30-47):
```python
def _make_cfg(
    instance_url: str = "https://myco.service-now.com",
    user_env: str = "QUIRK_SNOW_USER",
    password_env: str = "QUIRK_SNOW_PASSWORD",
    table: str = "incident",
    allow_internal: bool = False,
) -> ServiceNowTicketingCfg:
    return ServiceNowTicketingCfg(
        instance_url=instance_url,
        user_env=user_env,
        password_env=password_env,
        table=table,
        allow_internal=allow_internal,
    )


def _sample_finding() -> dict:
    return {
        "title": "Weak TLS cipher",
        "severity": "HIGH",
        "host": "example.com",
        "port": "443",
        "description": "TLS 1.0 accepted",
        "recommendation": "Disable TLS 1.0",
    }
```

**_FakeOpener / build_opener mock pattern** (from `tests/test_notify_webhook.py` lines 69-89):
```python
class _FakeHTTPResponse:
    """Minimal mock of context-manager returned by opener.open()."""
    def __init__(self, status: int = 201, body: dict | None = None):
        self.status = status
        self._body = body or {}

    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return json.dumps(self._body).encode("utf-8")


class _FakeOpener:
    def __init__(self, callback): self._callback = callback
    def open(self, req, timeout=None): return self._callback(req, timeout=timeout)
```

**POST test pattern — verify sys_id return + correlation_id in body** (from `tests/test_ticketing_jira.py` lines 96-121 as shape template):
```python
def test_create_incident(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUIRK_SNOW_USER", "admin")
    monkeypatch.setenv("QUIRK_SNOW_PASSWORD", "secret")

    cfg = _make_cfg()
    finding = _sample_finding()

    from quirk.ticketing.servicenow import ServiceNowChannel

    fake_sys_id = "a" * 32
    response_body = {"result": {"sys_id": fake_sys_id, "number": "INC0000042"}}
    captured = []

    def _fake_open(req, timeout=None):
        captured.append(req)
        return _FakeHTTPResponse(status=201, body=response_body)

    with patch("quirk.ticketing.servicenow.urllib.request.build_opener",
               return_value=_FakeOpener(_fake_open)):
        channel = ServiceNowChannel(cfg)
        fp = channel.compute_fingerprint(finding)
        evidence = channel.build_ticket_evidence(finding)
        result = channel.create_issue_from_finding(finding, fp, evidence)

    assert result == fake_sys_id
    assert captured[0].method == "POST"
    body = json.loads(captured[0].data)
    assert body["correlation_id"] == fp
    assert body["short_description"] == "Weak TLS cipher"
```

**Dedup + work_notes PATCH test pattern** (mirror `tests/test_ticketing_jira.py` lines 124-173):
```python
def test_dedup_then_work_notes(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    # First call: GET returns empty result → POST creates
    # Second call: GET returns sys_id → PATCH appends work_notes
    # Uses tmp_path for real DB (mirror jira test lines 146-173)
    # Verifies: create NOT called again on second dispatch; PATCH called once
```

**Credential scrubbing test pattern** (mirror `tests/test_ticketing_jira.py` lines 217-261):
```python
def test_credentials_not_in_logs(monkeypatch, tmp_path) -> None:
    # Plant a fake Basic auth string in the HTTPError message
    # Run dispatch_finding → check audit row error_summary
    # Assert fake creds absent from error_summary (safe_str enforcement)
    # The fake creds string must be at least 40 chars (matches _SENSITIVE_PATTERNS base64 rule)
```

**Config validation tests — mirror _parse_jira_cfg tests** (from `tests/test_ticketing_jira.py` lines 298-373):
```python
def test_http_instance_url_rejected() -> None:
    raw = {"instance_url": "http://myco.service-now.com",
           "user_env": "U", "password_env": "P"}
    assert _parse_servicenow_cfg(raw) is None

def test_missing_instance_url() -> None:
    raw = {"user_env": "U", "password_env": "P"}
    assert _parse_servicenow_cfg(raw) is None

def test_missing_env_fields_rejected() -> None:
    raw = {"instance_url": "https://myco.service-now.com", "user_env": "", "password_env": "P"}
    assert _parse_servicenow_cfg(raw) is None
```

**SSRF guard test — mirror `tests/test_notify_webhook.py` lines 112-118**:
```python
def test_ssrf_guard(monkeypatch) -> None:
    monkeypatch.setenv("QUIRK_SNOW_USER", "u")
    monkeypatch.setenv("QUIRK_SNOW_PASSWORD", "p")
    from quirk.ticketing.servicenow import ServiceNowChannel
    cfg = _make_cfg(instance_url="https://127.0.0.1/")
    with pytest.raises(ValueError, match="SSRF"):
        ServiceNowChannel(cfg)
```

---

## Shared Patterns

### Authentication — Basic auth header construction
**Source:** `quirk/ticketing/jira.py` lines 70-82 (env-var resolution) + stdlib base64
**Apply to:** `quirk/ticketing/servicenow.py` __init__ only
```python
user = os.environ.get(cfg.user_env, "")
password = os.environ.get(cfg.password_env, "")
creds = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
self._auth_header = f"Basic {creds}"
```

### SSRF Guard
**Source:** `quirk/ticketing/jira.py` lines 61-66 + `quirk/notify/channels/webhook.py` lines 65-69
**Apply to:** `quirk/ticketing/servicenow.py` __init__, triggered before any HTTP call
```python
result = validate_external_url(cfg.instance_url, allow_internal=cfg.allow_internal)
if not result.ok:
    raise ValueError(f"SSRF blocked ({result.reason}) for ServiceNow URL")
```

### Redirect Blocking
**Source:** `quirk/notify/channels/webhook.py` lines 29-41 + 89
**Apply to:** All three urllib methods in `quirk/ticketing/servicenow.py`
```python
opener = urllib.request.build_opener(_NoRedirectHandler)
with opener.open(req, timeout=10) as resp:
    ...
```

### Error Handling — safe_str on all exceptions
**Source:** `quirk/ticketing/base.py` line 131 + `quirk/ticketing/jira.py` line 20
**Apply to:** All `except` blocks in `quirk/ticketing/servicenow.py` that surface messages
```python
# Never use str(exc) or repr(exc) — safe_str scrubs Basic auth patterns
error_summary = safe_str(exc)  # ISEC-02
```

### Config — return None on any validation failure
**Source:** `quirk/ticketing/config.py` lines 85-112 (_parse_jira_cfg)
**Apply to:** `_parse_servicenow_cfg` in `quirk/ticketing/config.py`
Pattern: check for missing required field → `return None`, check for invalid value → `return None`, construct dataclass only on all-valid path.

### Lazy import for optional channel
**Source:** `quirk/ticketing/jira.py` lines 52-59 + `quirk/cli/ticket_cmd.py` lines 133-136
**Apply to:** `quirk/cli/ticket_cmd.py` servicenow dispatch branch
```python
from quirk.ticketing.servicenow import ServiceNowChannel  # noqa: PLC0415
```
Note: Unlike jira.py, servicenow.py has NO third-party import to guard — but the local import inside the dispatch branch is still required to maintain the same lazy-load pattern.

### Test DB setup for dispatch_finding integration tests
**Source:** `tests/test_ticketing_jira.py` lines 146-153
**Apply to:** `tests/test_ticketing_servicenow.py` dedup test + credential-scrub test
```python
db_path = str(tmp_path / "test.db")
from quirk.db import get_session, init_db
init_db(db_path)
with get_session(db_path) as db:
    channel.dispatch_finding(finding, db, "scan-001")
```

---

## No Analog Found

No files fall into this category. All four files have clear analogs in the existing codebase.

---

## Constraints Summary (for planner enforcement)

| Constraint | Source | Enforcement |
|------------|--------|-------------|
| ZERO changes to `quirk/ticketing/base.py` | CONTEXT.md TICKET-04 | Plan task must not include base.py |
| ZERO changes to `quirk/ticketing/jira.py` | CONTEXT.md TICKET-04 | Plan task must not include jira.py |
| `compute_fingerprint` NEVER overridden in ServiceNowChannel | `base.py` line 13 docstring | Structural: if `def compute_fingerprint` appears in servicenow.py, it is a bug |
| Return `sys_id` (not INC-number) from create_issue_from_finding | RESEARCH.md Pitfall 2 | `data["result"]["sys_id"]` — not `data["result"]["number"]` |
| PATCH (not POST/PUT) for work_notes | RESEARCH.md Pitfall 1 / KB0623936 | `method="PATCH"` in add_rediscovery_comment |
| Reject `http://` at config parse | RESEARCH.md Pitfall 4 | `_parse_servicenow_cfg`: `if not str(instance_url).startswith("https://")` → return None |
| `_NoRedirectHandler` on every opener | RESEARCH.md Pitfall 6 | `urllib.request.build_opener(_NoRedirectHandler)` in all three methods |

## Metadata

**Analog search scope:** `quirk/ticketing/`, `quirk/notify/channels/`, `quirk/cli/`, `tests/`
**Files read:** 7 (jira.py, config.py, webhook.py, ticket_cmd.py, base.py, test_ticketing_jira.py, test_notify_webhook.py)
**Pattern extraction date:** 2026-05-25
