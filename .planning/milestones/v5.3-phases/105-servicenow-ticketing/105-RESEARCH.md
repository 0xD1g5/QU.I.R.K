# Phase 105: ServiceNow Ticketing — Research

**Researched:** 2026-05-25
**Domain:** ServiceNow Table API, stdlib urllib, TicketingChannel ABC subclassing
**Confidence:** HIGH (architecture), MEDIUM (ServiceNow API response shapes — no live instance)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Transport:** stdlib `urllib` against the ServiceNow Table API (`POST /api/now/table/incident`) — zero new pip deps beyond the existing `[tickets]` extra (v5.3-D-06).
- **Dedup key:** `correlation_id` field carries the SHA256 fingerprint; `find_by_fingerprint` does `GET /api/now/table/incident?sysparm_query=correlation_id=<fp>&sysparm_limit=1`.
- **Rediscovery:** When an incident with the fingerprint correlation_id exists, append a `work_notes` entry (no duplicate incident).
- **Incident fields:** `short_description` = finding title, `description` = QRAMM evidence, `correlation_id` = fingerprint.
- **CLI:** `quirk ticket create --backend servicenow` (default backend = jira); shared `quirk ticket create` entrypoint dispatches on `--backend`.
- **Config:** `[ticketing]` gains a `servicenow` sub-block (`instance_url`, `user_env`, `password_env`), mirroring the jira sub-block.
- **Auth:** HTTP Basic auth (user + password/token resolved from env-var NAMES) over HTTPS.
- **Credentials:** referenced by env-var name only; never written to SQLite, scan JSON, or logs.
- **Subclass scope:** New `quirk/ticketing/servicenow.py::ServiceNowChannel(TicketingChannel)` implementing ONLY the 3 abstract methods — ZERO changes to base.py or jira.py.
- **Fingerprint:** identical `compute_fingerprint` from base — NEVER override in ServiceNowChannel.
- **SSRF guard:** `validate_external_url(instance_url)` before any call.
- **Safe strings:** `safe_str` on all exceptions.
- **Extra gate:** `[tickets]` extra gate still applies to the servicenow backend (keep consistent — urllib is stdlib but CLI is shared; the decision per CONTEXT.md D-06 is to keep the gate for now unless trivially separable — keep it).
- **Audit:** `dispatch_finding` writes `integration_deliveries(destination="servicenow", finding_hash=fp)` with no new audit code.

### Claude's Discretion

- Whether the `[tickets]` extra gate should apply to the servicenow backend — CONTEXT.md §specifics says "confirm at plan time whether the [tickets] gate should apply." Research recommendation: **KEEP the gate** (see section "CLI Backend Dispatch and Extra Gate" below).

### Deferred Ideas (OUT OF SCOPE)

- ServiceNow OAuth token flow (Basic auth this phase).
- ServiceNow-specific record types beyond incident.
- Bidirectional sync / auto-close on finding resolution.
- Any refactor of the Phase 104 abstraction.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TICKET-02 | A user can auto-create a ServiceNow incident per finding (Table API), carrying QRAMM evidence | ServiceNow Table API POST /api/now/table/incident with short_description + description + correlation_id |
| TICKET-04 | Jira and ServiceNow share one ticketing abstraction — not two parallel code paths | ServiceNowChannel subclasses TicketingChannel; zero base.py/jira.py changes confirmed (ABC already coded with Phase 105 in mind) |

</phase_requirements>

---

## Summary

Phase 105 is a narrow, high-confidence implementation: add one file (`quirk/ticketing/servicenow.py`), one config dataclass, widen the config parser to recognize a `servicenow` sub-block, and add a `--backend` flag to `ticket_cmd.py`. The Phase 104 ABC was built explicitly anticipating this phase — the comments in `base.py` name Phase 105 by number four times.

The ServiceNow Table API is a standard REST API over HTTPS with JSON bodies and HTTP Basic auth. The three ABC methods map directly to three HTTP operations: GET (find by correlation_id), POST (create incident), and PATCH (append work_notes). All three use `urllib.request.Request(method=...)` which the project already employs in `quirk/notify/channels/webhook.py`. That file is the canonical template for the urllib mechanics: `_NoRedirectHandler`, `opener.open(req, timeout=N)`, JSON body encoding, and response status checking.

The only non-obvious pitfall is the `work_notes` journal-field append semantics: each PATCH with `{"work_notes": "..."}` appends a new timestamped entry to the journal (it does NOT overwrite). This is the correct behaviour for rediscovery notes. The implementation must use PATCH (not PUT, not POST) to update the record by sys_id path variable.

**Primary recommendation:** Mirror `JiraChannel` for structure and `webhook.py` for HTTP mechanics. The implementation is 80–120 lines of straightforward urllib code.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Incident creation (POST) | API/Backend (ServiceNow) | — | Outbound HTTP call from QUIRK CLI to external ServiceNow instance |
| Dedup search (GET) | API/Backend (ServiceNow) | — | Outbound GET to fetch existing incident by correlation_id |
| Rediscovery comment (PATCH) | API/Backend (ServiceNow) | — | Outbound PATCH to append work_notes journal entry |
| Fingerprint computation | QUIRK core (base.py) | — | Inherited staticmethod; ServiceNowChannel MUST NOT override |
| Evidence payload build | QUIRK core (base.py) | — | Inherited from base; whitelisted fields only (ISEC-03) |
| Dedup orchestration + audit | QUIRK core (base.py) | — | dispatch_finding owns flow; ServiceNowChannel is pure transport |
| Config parsing | QUIRK CLI layer | — | _parse_servicenow_cfg mirrors _parse_jira_cfg pattern |
| Backend dispatch | QUIRK CLI (ticket_cmd.py) | — | --backend flag selects JiraChannel or ServiceNowChannel |
| Credential resolution | OS env vars | — | os.environ.get(cfg.user_env) / cfg.password_env at call time |
| SSRF guard | QUIRK util (url_allowlist.py) | — | validate_external_url(instance_url) at __init__ time |
| Credential scrubbing | QUIRK util (safe_exc.py) | — | safe_str() on all exceptions; Basic auth pattern already in _SENSITIVE_PATTERNS |

---

## Standard Stack

### Core (all stdlib — zero new deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `urllib.request` | stdlib (Python 3.11+) | HTTP POST/GET/PATCH to ServiceNow Table API | v5.3-D-06: locked; already used in webhook.py |
| `urllib.error` | stdlib | Catch `HTTPError`, `URLError` from urllib | Consistent with webhook.py pattern |
| `base64` | stdlib | Build `Authorization: Basic base64(user:password)` header | No dep; correct encoding for HTTP Basic auth |
| `json` | stdlib | Encode request bodies and decode responses | Already used project-wide |

### Reused from Phase 104 (no new code)

| Asset | Source | Role |
|-------|--------|------|
| `TicketingChannel` ABC | `quirk/ticketing/base.py` | Superclass — 3 abstract methods + shared orchestration |
| `compute_fingerprint` | `base.py` staticmethod | SHA256(host:port::title) — inherited, NOT overridden |
| `build_ticket_evidence` | `base.py` staticmethod | QRAMM evidence text — inherited |
| `dispatch_finding` | `base.py` method | Dedup + audit orchestration — inherited |
| `validate_external_url` | `quirk/util/url_allowlist.py` | SSRF guard at construction time |
| `safe_str` | `quirk/util/safe_exc.py` | Credential-safe exception stringification |
| `load_ticketing_config` | `quirk/ticketing/config.py` | Config loader — extend, do not replace |
| `_NoRedirectHandler` | `quirk/notify/channels/webhook.py` | urllib redirect-blocking pattern (copy or inline) |

### No New pip Dependencies

ServiceNow uses stdlib urllib. The `[tickets]` extra remains `jira>=3.10.5` only. No new entry in `pyproject.toml` extras beyond the existing `[tickets]` extra gate.

---

## Package Legitimacy Audit

No new packages are installed in this phase. All HTTP transport uses stdlib `urllib`. The `[tickets]` extra (`jira>=3.10.5`) was already vetted in Phase 104.

**No package legitimacy audit required — zero new pip deps.**

---

## Architecture Patterns

### System Architecture Diagram

```
quirk ticket create --backend servicenow
          |
          v
   ticket_cmd.py::run_ticket()
          |-- is_extra_available("tickets") gate
          |-- load_ticketing_config() -> cfg.servicenow
          |-- ServiceNowChannel(cfg.servicenow)
          |       |-- validate_external_url(instance_url)  [SSRF guard]
          |       |-- resolve creds from env vars
          |
          |-- for finding in findings:
                 dispatch_finding(finding, db, scan_id)   [base.py]
                       |
                       |-- compute_fingerprint(finding)   [base.py]
                       |-- build_ticket_evidence(finding) [base.py]
                       |
                       |-- find_by_fingerprint(fp)
                       |    GET /api/now/table/incident
                       |       ?sysparm_query=correlation_id=<fp>
                       |       &sysparm_limit=1
                       |    returns: sys_id str | None
                       |
                       |-- [None]  -> create_issue_from_finding()
                       |              POST /api/now/table/incident
                       |              {short_description, description, correlation_id}
                       |              returns: sys_id str
                       |
                       |-- [sys_id] -> add_rediscovery_comment()
                       |              PATCH /api/now/table/incident/{sys_id}
                       |              {work_notes: "Rediscovery: ..."}
                       |
                       |-- IntegrationDelivery audit row -> db.commit()
```

### Recommended Project Structure

```
quirk/ticketing/
├── base.py          # DO NOT MODIFY (Phase 104 ABC)
├── jira.py          # DO NOT MODIFY (Phase 104 backend)
├── servicenow.py    # NEW: ServiceNowChannel(TicketingChannel)
└── config.py        # MODIFY: add ServiceNowTicketingCfg + update _parse_ticketing_cfg

quirk/cli/
└── ticket_cmd.py    # MODIFY: add --backend flag + servicenow dispatch path

tests/
└── test_ticketing_servicenow.py   # NEW: mocked urllib tests
```

### Pattern 1: ServiceNow Table API — HTTP Request Construction

The canonical urllib pattern in this project is `webhook.py`. ServiceNow uses the same mechanics with two additions: a `method=` parameter for GET/PATCH and a Basic auth header.

**Key mechanic — Basic auth header:**
[CITED: timdietrich.me/blog/servicenow-table-api-comments-work-notes/]
```python
# Source: webhook.py pattern + standard HTTP Basic Auth
import base64, os

user = os.environ.get(cfg.user_env, "")
password = os.environ.get(cfg.password_env, "")
credentials = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
auth_header = f"Basic {credentials}"
```

**Key mechanic — PATCH with method= parameter:**
[ASSUMED — based on Python docs + verified urllib.request.Request.method attribute exists in Python 3.14]
```python
# urllib.request.Request supports method= in Python 3.4+ — VERIFIED in this env
req = urllib.request.Request(
    url,
    data=json.dumps(body).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": auth_header,
    },
    method="PATCH",   # PATCH, POST, GET all work via method=
)
```

**Key mechanic — NoRedirectHandler (copy from webhook.py):**
```python
# Must block redirects to prevent post-validation SSRF bypass — identical to webhook.py
opener = urllib.request.build_opener(_NoRedirectHandler)
with opener.open(req, timeout=10) as resp:
    return json.loads(resp.read().decode("utf-8"))
```

### Pattern 2: ServiceNow Table API — Request/Response Shapes

**CREATE (POST):**
[CITED: vexpose.blog/2021/04/20/creating-servicenow-incidents-via-rest-api/]
[CITED: ServiceNow Table API docs — response shape confirmed via multiple sources]

```
POST {instance_url}/api/now/table/incident
Headers: Content-Type: application/json, Accept: application/json, Authorization: Basic <b64>
Body: {"short_description": "<title>", "description": "<evidence>", "correlation_id": "<fp>"}

Response (HTTP 201):
{
  "result": {
    "sys_id": "a79d926cdb234010e6e80d53ca9619fe",   # 32-char hex — THE issue key
    "number": "INC0012345",
    ... (all submitted fields + defaults)
  }
}
```

`create_issue_from_finding` returns `response["result"]["sys_id"]` — a 32-char hex string. This is the value stored as the "issue_key" in the base class orchestration and passed to `add_rediscovery_comment`. It fits the ABC's `str` return type.

**DEDUP SEARCH (GET):**
[CITED: servicenow.com community — sysparm_query=correlation_id=<fp> pattern]
[CITED: Multiple ServiceNow sources confirm sysparm_query=field=value for exact match]

```
GET {instance_url}/api/now/table/incident
    ?sysparm_query=correlation_id={fp}
    &sysparm_limit=1
    &sysparm_fields=sys_id
Headers: Accept: application/json, Authorization: Basic <b64>

Response:
{
  "result": []                            # not found — return None
  "result": [{"sys_id": "a79d9..."}]      # found — return result[0]["sys_id"]
}
```

`find_by_fingerprint` returns `response["result"][0]["sys_id"]` if `result` is non-empty, else `None`.

Note: `sysparm_fields=sys_id` limits the response to just the sys_id field, reducing payload size. The SHA256 fingerprint (64-char hex from `[0-9a-f]`) contains no characters that require URL-encoding.

**REDISCOVERY (PATCH):**
[CITED: timdietrich.me/blog/servicenow-table-api-comments-work-notes/]

```
PATCH {instance_url}/api/now/table/incident/{sys_id}
Headers: Content-Type: application/json, Accept: application/json, Authorization: Basic <b64>
Body: {"work_notes": "Rediscovery: QUIRK re-detected this finding.\nFingerprint: <fp>"}

Response (HTTP 200):
{"result": { ... updated record ... }}
```

`add_rediscovery_comment` sends the PATCH and returns None (abc signature: `-> None`). The `work_notes` field is a journal input field — each PATCH appends a new timestamped journal entry; it does NOT overwrite prior entries. [CITED: ServiceNow community — "journals are append-only, changes() detects whether a new entry was appended during that transaction"]

### Pattern 3: ServiceNowChannel Subclass Shape

Mirror `JiraChannel` exactly: lazy NO import (no third-party lib to import), `validate_external_url` at `__init__` time, three short methods.

```python
# Source: mirror of quirk/ticketing/jira.py structure
class ServiceNowChannel(TicketingChannel):
    destination = "servicenow"

    def __init__(self, cfg: ServiceNowTicketingCfg) -> None:
        # SSRF guard at construction time (ISEC-01)
        result = validate_external_url(cfg.instance_url, allow_internal=cfg.allow_internal)
        if not result.ok:
            raise ValueError(f"SSRF blocked ({result.reason}) for ServiceNow URL")
        self._cfg = cfg
        # Resolve creds at construction time (not per-call — avoids repeated env lookups)
        user = os.environ.get(cfg.user_env, "")
        password = os.environ.get(cfg.password_env, "")
        creds = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        self._auth_header = f"Basic {creds}"

    def find_by_fingerprint(self, fp: str) -> Optional[str]: ...
    def create_issue_from_finding(self, finding, fp, evidence) -> str: ...
    def add_rediscovery_comment(self, issue_key: str, fp: str) -> None: ...
```

### Pattern 4: Config Dataclass

```python
# Add to quirk/ticketing/config.py
@dataclass
class ServiceNowTicketingCfg:
    instance_url: str       # e.g. https://myco.service-now.com
    user_env: str           # env-var NAME holding username
    password_env: str       # env-var NAME holding password/token
    table: str = "incident" # default table — locked per CONTEXT.md
    allow_internal: bool = False

# Update TicketingCfg:
@dataclass
class TicketingCfg:
    jira: Optional[JiraTicketingCfg] = None
    servicenow: Optional[ServiceNowTicketingCfg] = None  # NEW
```

Validation in `_parse_servicenow_cfg`:
- `instance_url` must be present and start with `https://` (reject `http://` — creds over cleartext is a security failure)
- `user_env` and `password_env` must be non-empty strings (missing env-var names means creds can never resolve)
- Return `None` on any validation failure (same pattern as `_parse_jira_cfg`)

### Pattern 5: ticket_cmd.py --backend Dispatch

```python
parser.add_argument(
    "--backend",
    choices=["jira", "servicenow"],
    default="jira",
    help="Ticketing backend to use (default: jira)",
)

# In dispatch section:
if args.backend == "servicenow":
    if cfg.servicenow is None:
        print("ERROR: [ticketing.servicenow] block not configured.", file=sys.stderr)
        sys.exit(2)
    from quirk.ticketing.servicenow import ServiceNowChannel  # noqa: PLC0415
    channel = ServiceNowChannel(cfg.servicenow)
else:  # default: jira
    if cfg.jira is None:
        print("ERROR: [ticketing.jira] block not configured.", file=sys.stderr)
        sys.exit(2)
    from quirk.ticketing.jira import JiraChannel  # noqa: PLC0415
    channel = JiraChannel(cfg.jira)
```

The current `run_ticket` hard-codes `cfg.jira is None` check. This must be refactored into a backend-conditional block. The `is_extra_available("tickets")` gate stays at the top — unchanged — because the CLI is shared and the jira extra is the trigger. [See "CLI Backend Dispatch and Extra Gate" section.]

### Anti-Patterns to Avoid

- **Overriding compute_fingerprint:** The ABC comment and base.py docstring both prohibit this. ServiceNowChannel must NOT define `compute_fingerprint`. If it does, the SHA256 formula diverges from Jira and findings have different fingerprints on different backends — dedup breaks across-backend.
- **Using issue.number instead of sys_id:** ServiceNow incident numbers (INC0012345) are human-readable but NOT guaranteed unique across table partitions and change on restore. `sys_id` is the stable internal primary key. Use `sys_id` throughout.
- **Using PUT for work_notes:** The project pattern and community docs use PATCH. PUT replaces the entire record; PATCH is a partial update. Use `method="PATCH"`.
- **Using POST for work_notes:** There is a known ServiceNow bug (KB0623936) where POSTing to the work_notes field creates the journal entry but it does NOT display in the task UI. Use PATCH to an existing record by sys_id.
- **Storing Basic auth creds in config:** Config fields store env-var NAMES. `os.environ.get(cfg.user_env)` is called at `__init__` time. The resolved value is stored only in `self._auth_header` (a local object attribute, never logged or serialized).
- **Logging self._auth_header:** The `Authorization: Basic <b64>` pattern is already in `_SENSITIVE_PATTERNS` in `safe_exc.py` — any exception that leaks the header string will be scrubbed by `safe_str`. But never log the header directly.
- **Following redirects:** Must use `_NoRedirectHandler` (same as webhook.py) to prevent a post-validation SSRF bypass via 302 redirect.
- **HTTP (not HTTPS) instance_url:** Reject `http://` URLs at config parse time — Basic auth credentials transit in the Authorization header, which is plaintext over HTTP. The validator should return None for non-HTTPS instance URLs before `validate_external_url` even runs.
- **Allowing the extra gate to be skipped silently:** ServiceNow uses only stdlib, but the ticket_cmd CLI is shared. If someone installs with `pip install quirk` (no extras) and runs `quirk ticket create --backend servicenow`, the current gate would print a Jira advisory. The fix: keep the gate but update the error message to be backend-neutral (e.g., "run `pip install quirk[tickets]`") — or check backend-specifically. See "Open Questions" #1.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSRF validation | Custom IP-range check | `validate_external_url` | Already handles RFC1918, loopback, link-local, metadata IPs, DNS resolution |
| Credential scrubbing | Custom regex in servicenow.py | `safe_str(exc)` | `_SENSITIVE_PATTERNS` already covers `Authorization: Basic <b64>` (40+ char base64 pattern) and connection string shapes |
| Dedup logic | Custom "find before create" loop | `dispatch_finding` in base.py | Base handles find→create/comment + audit row + failure isolation |
| Evidence payload | Custom field extraction | `build_ticket_evidence` | Exfiltration whitelist (ISEC-03) — never extract fields directly from finding dict |
| Fingerprint | Custom hash | `compute_fingerprint` (staticmethod, inherited) | Byte-identical SHA256 across Jira and ServiceNow backends — changing formula breaks TICKET-03 |
| HTTP redirect blocking | None | `_NoRedirectHandler` from webhook.py | Prevents post-validation SSRF bypass — copy or import |
| Audit rows | Custom IntegrationDelivery writes | `dispatch_finding` orchestration | Base already writes `destination="servicenow"` when `ServiceNowChannel.destination = "servicenow"` |

**Key insight:** The ServiceNow backend is ~100 lines of "translate ABC calls into urllib HTTP requests." Everything else is inherited.

---

## CLI Backend Dispatch and Extra Gate

### Decision: Keep the `is_extra_available("tickets")` gate for both backends

**Rationale:** The `[tickets]` extra exists because the Jira library is the heavy dependency. ServiceNow uses only stdlib. However:

1. The CLI is shared — a single `quirk ticket create` command serves both backends
2. The extra gate is checked before the `--backend` flag is parsed (current code flow)
3. Changing the gate to be backend-conditional requires parsing `--backend` before the gate check, which complicates the argparse flow
4. The gate message can be updated to say "run `pip install quirk[tickets]`" generically

**Simpler approach:** Keep the gate. A user running `--backend servicenow` who hasn't installed `[tickets]` will get the advisory. This is slightly conservative (ServiceNow doesn't need jira) but consistent and simple.

**Alternative (if the user wants it):** Move the extra gate inside the `--backend jira` branch only. This is a one-liner change but requires `args = parser.parse_args(argv)` to happen before `is_extra_available`. Both approaches are valid — the simpler "keep gate at top" is recommended.

The CONTEXT.md §specifics says: "confirm at plan time whether the [tickets] gate should apply to the servicenow backend." **Research recommendation: keep the gate at the top but update the error message to be generic.** Flag this as a planner decision.

---

## Common Pitfalls

### Pitfall 1: work_notes POST vs. PATCH — UI Visibility
**What goes wrong:** Using POST with `{"work_notes": "..."}` creates the journal entry but it does NOT display in the task UI (ServiceNow known error KB0623936). The entry appears in sys_journal_field history only.
**Why it happens:** ServiceNow's Table API POST creates a new record; it doesn't update an existing one. To update a record, you MUST use PATCH (or PUT) with the sys_id in the URL path.
**How to avoid:** Always `PATCH {instance_url}/api/now/table/incident/{sys_id}` — never `POST {instance_url}/api/now/table/incident` with a sys_id body field for updates.
**Warning signs:** Test with `find_by_fingerprint` returns a sys_id, then PATCH that sys_id — the work note appears in the incident's Activity section.

### Pitfall 2: Using incident number (INC0012345) instead of sys_id for updates
**What goes wrong:** ServiceNow Table API PATCH and PUT require the sys_id as the URL path variable, not the human-readable incident number. `PATCH /api/now/table/incident/INC0012345` returns 404.
**Why it happens:** Incident numbers are display values, not API keys. The URL path segment must be the sys_id.
**How to avoid:** `create_issue_from_finding` returns `response["result"]["sys_id"]`, not `response["result"]["number"]`. The base class passes this as `issue_key` to `add_rediscovery_comment(issue_key, fp)` — which uses it in the PATCH URL path. Keep using sys_id throughout.
**Warning signs:** HTTP 404 on PATCH when using the INC-number format.

### Pitfall 3: HTTP Basic auth credential leakage via urllib HTTPError
**What goes wrong:** When `urllib.request.urlopen` throws an `HTTPError` (e.g. HTTP 401 Unauthorized), the exception's `str()` representation may include the request headers, which include `Authorization: Basic <b64creds>`.
**Why it happens:** urllib's HTTPError can capture the full response including headers that reference the request.
**How to avoid:** Every exception from urllib calls is passed through `safe_str(exc)` before logging or storage. The pattern `Authorization:\s*Basic\s+[A-Za-z0-9+/]{8,}` and the 40+ char base64 pattern in `_SENSITIVE_PATTERNS` both cover this case. Confirmed: the existing `safe_exc.py` already scrubs both patterns.
**Warning signs:** `RuntimeError: safe_str scrubbed to class-name only` in audit row error_summary means a credential was caught and stripped — this is correct behavior.

### Pitfall 4: HTTP (not HTTPS) instance_url
**What goes wrong:** If `instance_url` starts with `http://`, Basic auth credentials transit in plaintext.
**Why it happens:** `validate_external_url` accepts `http://` scheme (it's in `_ALLOWED_SCHEMES`). The SSRF validator won't reject it.
**How to avoid:** In `_parse_servicenow_cfg`, validate that `instance_url` starts with `https://` before calling `validate_external_url`. Return None for non-HTTPS URLs — a config error, not a runtime SSRF error.
**Warning signs:** `instance_url: http://` in YAML config silently succeeds config parse without this check.

### Pitfall 5: sysparm_query injection via fingerprint
**What goes wrong:** If the fingerprint formula ever produces characters that affect URL query parsing (`&`, `=`, `#`), sysparm_query is corrupted.
**Why it happens:** URL query parameter values need percent-encoding.
**How to avoid:** `compute_fingerprint` always returns a 64-char hex string (`[0-9a-f]` only). No percent-encoding needed. But: use `urllib.parse.urlencode({"sysparm_query": f"correlation_id={fp}", "sysparm_limit": "1"})` to URL-encode the query string rather than string formatting directly into the URL.
**Warning signs:** This is NOT a live risk for hex-only fingerprints, but the correct pattern prevents a future regression if the fingerprint formula ever changes.

### Pitfall 6: Redirect-based SSRF bypass
**What goes wrong:** ServiceNow instance_url passes `validate_external_url`. But the ServiceNow endpoint returns `302 → http://169.254.169.254/...`. urllib follows the redirect by default.
**Why it happens:** `validate_external_url` checks the original URL, not the redirect target.
**How to avoid:** Use `_NoRedirectHandler` (copy from `webhook.py`) to block all redirects. Any 3xx response raises `HTTPError` instead of being followed.
**Warning signs:** Missing `_NoRedirectHandler` in the opener construction.

### Pitfall 7: Extra gate message says "Jira ticketing" when --backend servicenow
**What goes wrong:** `ticket_cmd.py` currently prints `"ERROR: Jira ticketing skipped"` when the tickets extra is missing. With `--backend servicenow`, this message is misleading.
**Why it happens:** The current error message is hard-coded to mention Jira.
**How to avoid:** Update the error message to be generic: `"ERROR: Ticketing skipped — run pip install quirk[tickets] to enable."` This is a one-line change in ticket_cmd.py.

---

## Code Examples

All examples are [ASSUMED] unless marked — no live ServiceNow instance for verification; patterns are derived from the codebase's own webhook.py + standard urllib + ServiceNow community documentation.

### find_by_fingerprint — GET with sysparm_query

```python
# Source: derived from webhook.py pattern + ServiceNow community docs
# [CITED: servicenow.com community — sysparm_query=field=value syntax]
def find_by_fingerprint(self, fp: str) -> Optional[str]:
    from urllib.parse import urlencode  # noqa: PLC0415
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
        if results:
            return results[0]["sys_id"]
        return None
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"ServiceNow GET failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("ServiceNow GET failed: connection error") from exc
```

### create_issue_from_finding — POST

```python
# Source: derived from webhook.py pattern + ServiceNow Table API docs
# [CITED: vexpose.blog — short_description/description/correlation_id body shape]
# [CITED: ServiceNow docs — response result.sys_id]
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
        return data["result"]["sys_id"]  # 32-char hex, NOT INC-number
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"ServiceNow POST failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("ServiceNow POST failed: connection error") from exc
```

### add_rediscovery_comment — PATCH work_notes

```python
# Source: derived from webhook.py pattern
# [CITED: timdietrich.me — PATCH {instance_url}/api/now/table/incident/{sys_id}
#          with {"work_notes": "..."} body]
# [CITED: ServiceNow community — work_notes is journal-append, not overwrite]
def add_rediscovery_comment(self, issue_key: str, fp: str) -> None:
    # issue_key IS the sys_id (32-char hex) — confirmed by create_issue_from_finding return
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
        method="PATCH",
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

### Config YAML shape for users

```yaml
# Example: quirk-config.yaml
ticketing:
  jira:
    jira_url: https://myco.atlassian.net
    jira_user_env: QUIRK_JIRA_USER
    jira_token_env: QUIRK_JIRA_TOKEN
    project_key: SEC
  servicenow:
    instance_url: https://myco.service-now.com
    user_env: QUIRK_SNOW_USER
    password_env: QUIRK_SNOW_PASSWORD
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No ServiceNow backend | ServiceNow as second TicketingChannel backend | Phase 105 | Proves TICKET-04 abstraction works; teams using ServiceNow can adopt QUIRK |
| Single-backend ticket CLI | `--backend {jira,servicenow}` flag | Phase 105 | Backward compatible (default=jira) |
| Jira-library-based HTTP | stdlib urllib Table API | Phase 105 | Zero new pip dep; same pattern as webhook.py |

**Deprecated/outdated:**
- Nothing is deprecated by this phase. Jira backend is unchanged. Base ABC is unchanged.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ServiceNow Table API POST to /api/now/table/incident returns `{"result": {"sys_id": "...", "number": "..."}}` | API Response Shapes | Would need to adjust response parsing key; verifiable against a dev instance |
| A2 | GET with `sysparm_query=correlation_id=<fp>&sysparm_limit=1` returns `{"result": [{"sys_id": "..."}]}` (array) for matches | API Response Shapes | Array vs. object shape — community docs and multiple examples confirm array; low risk |
| A3 | PATCH to `/api/now/table/incident/{sys_id}` with `{"work_notes": "..."}` appends a new journal entry (does not overwrite) | Pitfall 1 / Code Examples | If overwrite: prior rediscovery notes lost. Community sources confirm journal-append semantics; low risk |
| A4 | HTTP 201 is the success status for POST incident creation (in addition to 200) | Code Examples | If 200-only: create_issue_from_finding raises on 201; handle both 200/201 in resp.status check |
| A5 | `sysparm_fields=sys_id` is a valid GET query parameter that limits response fields | Code Examples | If not supported on older instances: response includes extra fields but still has sys_id; no functional breakage |
| A6 | urllib.request.Request method= param works for GET/POST/PATCH in Python 3.11+ | HTTP Mechanics | Verified in this session on Python 3.14 — works; Python 3.4+ feature |

**Claim A3 is the highest-risk assumption:** The append-vs-overwrite semantics of `work_notes` via PATCH are confirmed by multiple community sources but not by a live instance test. The implementation should work correctly; if a user encounters overwrite, the workaround is to switch to `sys_journal_field` table endpoint (out of scope for this phase).

---

## Open Questions (RESOLVED)

1. **Extra gate message for `--backend servicenow`**
   - What we know: Current gate says "Jira ticketing skipped" even for `--backend servicenow`.
   - What's unclear: Whether to keep gate at top (simple, slightly confusing message) or move inside `--backend jira` branch only (requires parsing args before gate check).
   - Recommendation: Update error message to generic "Ticketing skipped — run `pip install quirk[tickets]` to enable" and keep gate at top. Flag this in the plan as a one-line text change.

2. **HTTP status handling for POST**
   - What we know: ServiceNow Table API POST returning 201 Created is standard REST behavior. Some instances return 200.
   - What's unclear: Which exact HTTP status codes are returned by ServiceNow POST (201 vs 200).
   - Recommendation: Accept 200 and 201 as success in `create_issue_from_finding` (check `resp.status not in (200, 201)` to raise).

3. **Timeout value**
   - What we know: webhook.py uses `cfg.timeout_seconds`. SIEM transport uses `timeout=5`.
   - What's unclear: Whether ServiceNowTicketingCfg should have a configurable timeout or hardcode 10s.
   - Recommendation: Hardcode 10s (matching the longest reasonable network call in this project). Adding a `timeout` config field is a nice-to-have but not needed for TICKET-02.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 105 is code/config-only changes. All HTTP is outbound to a user-supplied ServiceNow instance. No local service dependencies beyond the Python 3.11+ interpreter and the existing QUIRK dependencies (confirmed present).

---

## Validation Architecture

Nyquist validation is enabled (`workflow.nyquist_validation: true` in `.planning/config.json`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already configured project-wide) |
| Config file | `pytest.ini` or `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/test_ticketing_servicenow.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TICKET-02 | First scan: POST creates incident, returns sys_id | unit | `pytest tests/test_ticketing_servicenow.py::test_create_incident -x` | No — Wave 0 |
| TICKET-02 | Second scan: GET finds existing sys_id, PATCH adds work_notes | unit | `pytest tests/test_ticketing_servicenow.py::test_dedup_then_work_notes -x` | No — Wave 0 |
| TICKET-02 | correlation_id equals SHA256 fingerprint in POST body | unit | `pytest tests/test_ticketing_servicenow.py::test_correlation_id_is_fingerprint -x` | No — Wave 0 |
| TICKET-02 | Missing instance_url config → graceful skip (cfg returns None) | unit | `pytest tests/test_ticketing_servicenow.py::test_missing_instance_url -x` | No — Wave 0 |
| TICKET-02 | HTTP instance_url rejected at config parse time | unit | `pytest tests/test_ticketing_servicenow.py::test_http_instance_url_rejected -x` | No — Wave 0 |
| TICKET-02 | Credentials absent from error_summary (safe_str scrubs Basic auth) | unit | `pytest tests/test_ticketing_servicenow.py::test_credentials_not_in_logs -x` | No — Wave 0 |
| TICKET-02 | SSRF guard blocks internal/loopback instance_url at __init__ | unit | `pytest tests/test_ticketing_servicenow.py::test_ssrf_guard -x` | No — Wave 0 |
| TICKET-02 | --backend servicenow CLI flag dispatches ServiceNowChannel | unit | `pytest tests/test_ticket_cmd.py::test_backend_servicenow -x` | No — Wave 0 (new test in existing file) |
| TICKET-04 | Zero changes to base.py or jira.py (inheritance only) | unit (structural) | `pytest tests/test_ticketing_base.py -x` (existing tests must still pass) | Yes (existing) |

### Test Pattern — mocked urllib

Mirror `test_ticketing_jira.py` approach but mock `urllib.request.urlopen` / `opener.open` instead of the `jira.JIRA` client. Key mock patterns:

```python
# Mock the opener.open response for ServiceNow CREATE (POST)
mock_response = MagicMock()
mock_response.read.return_value = json.dumps({
    "result": {"sys_id": "abc123" * 5, "number": "INC0000042"}
}).encode("utf-8")
mock_response.status = 201
mock_response.__enter__ = lambda s: s
mock_response.__exit__ = MagicMock(return_value=False)

# Mock urllib.request.build_opener and the opener it returns
mock_opener = MagicMock()
mock_opener.open.return_value = mock_response
with patch("quirk.ticketing.servicenow.urllib.request.build_opener",
           return_value=mock_opener):
    result = channel.create_issue_from_finding(finding, fp, evidence)
    assert result == "abc123abc123abc123abc123abc123abc123abc123abc123abc123abc123abc1"
    # Verify POST was used (not GET or PATCH)
    req = mock_opener.open.call_args.args[0]
    assert req.method == "POST"
    body = json.loads(req.data)
    assert body["correlation_id"] == fp
```

For the creds-not-in-logs test, plant a fake Basic auth header in the HTTPError and confirm `safe_str` returns class-name only.

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_ticketing_servicenow.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_ticketing_servicenow.py` — covers TICKET-02 (all tests listed above)
- [ ] New tests in `tests/test_ticket_cmd.py` — covers `--backend servicenow` CLI dispatch
- [ ] `tests/test_ticketing_config.py` (if it exists) or new section — covers ServiceNowTicketingCfg validation (http rejected, missing fields)

*(Existing tests for base.py and jira.py must remain green — no changes to those files.)*

---

## Security Domain

Security enforcement is enabled (no explicit `false` in config.json).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | HTTP Basic auth — credentials resolved from env vars; never stored or logged |
| V3 Session Management | No | Stateless API calls; no session tokens |
| V4 Access Control | No | ServiceNow access control is server-side; QUIRK makes authenticated calls only |
| V5 Input Validation | Yes | `instance_url` validated at config parse (https-only) + `validate_external_url` at init |
| V6 Cryptography | No | No new crypto; SHA256 fingerprint is inherited from base.py |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSRF via ServiceNow instance_url | Elevation of Privilege | `validate_external_url(instance_url)` at `__init__` time; `_NoRedirectHandler` blocks redirect bypass |
| Credential leakage via exception message | Info Disclosure | `safe_str(exc)` on every exception; `Authorization: Basic` + base64 patterns already in `_SENSITIVE_PATTERNS` |
| Cleartext credential transmission | Info Disclosure | Reject `http://` instance URLs at config parse time (return None from `_parse_servicenow_cfg`) |
| Credential injection via env-var name | Tampering | Config stores env-var NAME only; the name itself is not a credential; resolved at `__init__` from `os.environ` |
| Fingerprint injection in sysparm_query | Tampering | SHA256 hex output is `[0-9a-f]` only — no injectable characters; use `urlencode` for additional safety |
| Redirect-based SSRF bypass | Elevation of Privilege | `_NoRedirectHandler` raises `HTTPError` on any 3xx response |

### safe_str Coverage Verification

The existing `_SENSITIVE_PATTERNS` in `quirk/util/safe_exc.py` (verified by direct code read) covers all ServiceNow credential leak patterns:

- `Authorization:\s*(Bearer|Basic)\s+\S+` — catches the header if it appears in exception text
- `\b[A-Za-z0-9+/]{40,}={0,2}\b` — catches any 40+ char base64 blob (covers most SNOW tokens)
- `Authorization:\s*Basic\s+[A-Za-z0-9+/]{8,}={0,2}` — specific Basic auth header pattern
- `://[^:@\s]+:[^@\s]+@` — connection strings with embedded password

No new patterns needed in `safe_exc.py` for ServiceNow Basic auth.

---

## Sources

### Primary (HIGH confidence)

- `quirk/ticketing/base.py` — TicketingChannel ABC, 3 abstract method signatures, `compute_fingerprint`, `dispatch_finding` — read directly from codebase
- `quirk/ticketing/jira.py` — JiraChannel analog structure — read directly from codebase
- `quirk/ticketing/config.py` — TicketingCfg, _parse_jira_cfg pattern — read directly from codebase
- `quirk/cli/ticket_cmd.py` — existing CLI structure, extra gate, dispatch pattern — read directly from codebase
- `quirk/notify/channels/webhook.py` — canonical urllib pattern with `_NoRedirectHandler`, `opener.open(req, timeout=N)`, JSON body, method= parameter — read directly from codebase
- `quirk/util/safe_exc.py` — `_SENSITIVE_PATTERNS` including Basic auth patterns — read directly from codebase
- `quirk/util/url_allowlist.py` — `validate_external_url` interface and behavior — read directly from codebase
- Python 3.14 stdlib — `urllib.request.Request(method=)` confirmed working in this environment

### Secondary (MEDIUM confidence)

- [Tim Dietrich — ServiceNow Table API: Working With Comments and Work Notes](https://timdietrich.me/blog/servicenow-table-api-comments-work-notes/) — PATCH method for work_notes, curl example with sys_id URL
- [vexpose.blog — Creating ServiceNow Incidents via REST API](https://vexpose.blog/2021/04/20/creating-servicenow-incidents-via-rest-api/) — POST body shape (short_description, description, correlation_id), response result.sys_id
- [ServiceNow Table API — zurich docs](https://www.servicenow.com/docs/r/zurich/api-reference/rest-apis/c_TableAPI.html) — confirmed POST/GET/PATCH endpoint structure, Basic auth header format
- [ServiceNow community — sysparm_query syntax](https://www.servicenow.com/community/servicenow-ai-platform-forum/sysparm-query-with-rest-table-api/m-p/1184756) — exact `sysparm_query=field=value` filter syntax
- [ServiceNow community — journal fields are append-only](https://www.servicenow.com/community/developer-forum/changes-and-journal-fields/m-p/3527577) — "journals are append-only; changes() detects whether a new entry was appended during that transaction"

### Tertiary (LOW confidence — used for pattern confirmation only)

- [ServiceNow community — REST API PUT for work_notes](https://www.servicenow.com/community/service-management-forum/rest-api-put-method-to-update-worknotes-on-given-incident/m-p/399644) — confirms sys_id required for Table API PUT/PATCH (incident number not accepted)
- [ServiceNow known error KB0623936](https://support.servicenow.com/kb?id=kb_article_view&sysparm_article=KB0623936) — POST work_notes creates journal entry but does NOT display in task UI (confirms: must use PATCH to existing record)

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all stdlib, zero new deps; urllib pattern verified in codebase
- Architecture: HIGH — ABC already built for this phase; 3-method subclass is the only deliverable
- ServiceNow API shapes: MEDIUM — confirmed via multiple community docs but not a live instance
- work_notes append semantics: MEDIUM — confirmed by community consensus ("journals are append-only"); practical risk is low
- Pitfalls: HIGH — derived from codebase analysis (redirect SSRF, http-not-https, sys_id vs. number) plus verified safe_str patterns

**Research date:** 2026-05-25
**Valid until:** 2026-08-25 (90 days — stable APIs, no version-gated behavior)
