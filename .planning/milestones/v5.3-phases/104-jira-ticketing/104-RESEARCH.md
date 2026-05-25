# Phase 104: Jira Ticketing - Research

**Researched:** 2026-05-25
**Domain:** Jira REST API (Python `jira` library), TicketingChannel ABC design, idempotent dedup, CLI integration
**Confidence:** HIGH (core API and codebase verified; jira library version constraint flag below)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- `TicketingChannel` ABC in `quirk/ticketing/base.py` with `create_or_update(finding, fingerprint, evidence)` and `find_by_fingerprint(fp)` — Jira and ServiceNow each subclass it.
- Shared layer owns: fingerprint computation, dedup orchestration, evidence-payload build, and `integration_deliveries` audit writes; ONLY backend API calls are subclass-specific.
- `build_ticket_evidence(finding)` sources QRAMM dimension evidence (via `quirk/qramm/evidence_bridge.py`) and feeds both backends identically.
- Module layout: `quirk/ticketing/{base,jira,servicenow}.py` — Phase 105 adds servicenow.py only, no changes to base/jira.
- `jira>=3.10.5` behind a new `[tickets]` extra, lazy-imported with graceful skip (ISEC-04).
- `[tickets]` JOINS `[all]` with a CI guard test (like `[notify]`); verify no dependency conflict via pip dry-run at execute time.
- Issue fields: project key + issue type from `[ticketing]` config; summary = finding title; description = QRAMM evidence + the fingerprint label.
- One Jira issue per finding.
- Fingerprint = `SHA256(host:port:protocol:category)` (hex), stored as a Jira LABEL AND in `integration_deliveries.finding_hash`.
- Dedup: JQL label search before create; if matching ticket found → update with "rediscovery" comment; no duplicate created.
- Each attempt writes an `integration_deliveries` row (destination="jira", finding_hash=fingerprint, status ok/failed).
- CLI: `quirk ticket create` reading a completed scan's findings (latest in output dir or `--input <path>`).
- Jira URL / user / API-token resolved from env vars (names referenced in a `[ticketing]` config block); credentials NEVER written to SQLite or logs.
- Missing `[tickets]` extra → `is_extra_available("tickets")` advisory + graceful skip, never an ImportError (ISEC-04).
- All errors routed through `safe_str`; validate the Jira base URL with `validate_external_url`.
- Phase 105 must require no changes to base.py or jira.py.

### Claude's Discretion

- None explicitly noted (all major decisions locked).

### Deferred Ideas (OUT OF SCOPE)

- ServiceNow backend (TICKET-02) — Phase 105.
- Bidirectional sync / ticket auto-close on finding resolution.
- Custom Jira field mapping beyond project + issue type.
- Per-schedule ticketing routing (global config only, per v5.3-D-07).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TICKET-01 | A user can auto-create a Jira issue per finding, carrying QRAMM evidence in the description, via the `jira` library behind a `[tickets]` extra | jira 3.10.5 confirmed on PyPI; create_issue API verified via official docs |
| TICKET-03 | Ticket creation is idempotent across re-scans — stable fingerprint searched before create; re-scans do not proliferate duplicates | JQL `labels = "FP"` syntax verified; SHA256 hex is safe as label value |
| TICKET-04 | Jira and ServiceNow share one ticketing abstraction and the same fingerprint/dedup + evidence-payload logic | ABC design + ServiceNow forward-compat analysis completed; see Architecture Patterns |
</phase_requirements>

---

## Summary

Phase 104 builds the `quirk/ticketing/` package: a `TicketingChannel` ABC (base.py), a `JiraChannel` subclass (jira.py), and a `quirk ticket create` CLI command. The ABC layer owns all the logic that must be identical for Phase 105 (ServiceNow): fingerprint computation, dedup orchestration, evidence-payload construction, and `integration_deliveries` audit writes. Only the Jira-specific API calls (client construction, JQL label search, `create_issue`, `add_comment`) live in the subclass.

The most important pre-planning discovery: **real findings-*.json files do NOT have `protocol` or `category` keys.** The `_build_finding` chokepoint in `quirk/engine/findings_evaluator.py` outputs `host`, `port`, `severity`, `title`, `description`, `recommendation`, `check_id`, `quantum_risk`, `compliance` — but not `protocol` (that is a `CryptoEndpoint` DB column) and not `category` (only advisory findings have it). The CONTEXT.md fingerprint formula `SHA256(host:port:protocol:category)` requires a pragmatic adaptation: use `finding.get("title", "")` as the `category` proxy and `""` for `protocol`, giving `SHA256(host:port::title)`. This is stable across re-scans because `_build_finding` produces deterministic titles. The planner must lock this concrete formula.

The `jira` library's latest release is 3.10.5 (2025-07-28 on PyPI). The local pip index showed only 3.8.0 due to index caching — `pip install "jira>=3.10.5"` will resolve correctly from PyPI. Cloud auth uses `basic_auth=(email, api_token)` tuple; self-hosted uses `token_auth="PAT"`. Both paths must be supported in `JiraTicketingCfg`.

**Primary recommendation:** Build the ABC first, then JiraChannel, then the CLI — in that order. Design every ABC method signature against both Jira's JQL approach and ServiceNow's Table API GET approach simultaneously to guarantee Phase 105 requires zero base.py changes.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| TicketingChannel ABC | Library / service module | — | Pure business logic; no HTTP, no DB directly |
| JiraChannel (API calls) | Library / service module | — | Thin Jira REST wrapper; testable via mock |
| Fingerprint computation | Library / service module (base.py) | — | Must be identical across Jira + ServiceNow |
| Dedup orchestration | Library / service module (base.py) | — | Must be identical across Jira + ServiceNow |
| Evidence-payload build | Library / service module (base.py) | — | Calls evidence_bridge; identical for both backends |
| `integration_deliveries` audit | Library / service module (base.py) | SQLite/DB | Base layer owns writes; subclass never touches DB |
| Config loading | Library / config module (config.py) | — | Mirrors notify/config.py and siem/config.py |
| CLI `quirk ticket create` | CLI / run_scan.py interception | quirk/cli/ticket_cmd.py | Follows export_cmd.py pattern exactly |
| SSRF URL validation | Utility (url_allowlist.py) | — | Phase 101 primitive; call at delivery time |
| Credential isolation | Env-var-name references only | — | Mirrors NOTIFY-06; never persist |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `jira` | `>=3.10.5` | Jira REST API client (create_issue, add_comment, search_issues) | Official Python client; slopcheck [OK]; 3.10.5 released 2025-07-28 |
| `stdlib hashlib` | built-in | SHA256 fingerprint computation | No dep needed |
| `stdlib abc` | built-in | ABC / abstractmethod for TicketingChannel | No dep needed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `quirk.util.optional_extra.is_extra_available` | existing | Graceful skip when `[tickets]` not installed | At CLI entry point and in dispatcher |
| `quirk.util.safe_exc.safe_str` | existing | Scrub credentials from error messages (ISEC-02) | All `except Exception` blocks |
| `quirk.util.url_allowlist.validate_external_url` | existing | SSRF guard on Jira base URL | In `JiraChannel.__init__` or connect() |
| `quirk.models.IntegrationDelivery` | existing | Audit row for each ticket attempt | In base.py `dispatch_finding` |
| `quirk.qramm.evidence_bridge` | existing | QRAMM dimension evidence source | In `build_ticket_evidence()` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `jira>=3.10.5` | `requests` + raw Jira REST | Jira lib handles auth, retry, multipart; raw requests only makes sense for ServiceNow (stdlib urllib) which has simpler Table API |
| ABC `abstractmethod` | Protocol (structural subtyping) | ABC is clearer intent for plan-checker enforcement; Protocol would work but gives no error at class definition time |

**Installation (pyproject.toml addition):**
```toml
tickets = [
    "jira>=3.10.5",  # Phase 104 TICKET-01 — Jira issue creation; Cloud/Server auth
]
```

And in `[all]`:
```toml
"quirk-scanner[tickets]",   # Phase 104 TICKET-01 — jira>=3.10.5; no cryptography downgrade
```

---

## Package Legitimacy Audit

| Package | Registry | Age | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|
| `jira` | PyPI | ~14 years (since 2011) | [OK] | Approved — `github.com/pycontribs/jira`, production-stable |

**Packages removed due to slopcheck [SLOP] verdict:** none

**Packages flagged as suspicious [SUS]:** none

**Registry verification:**
- `jira 3.10.5` confirmed on PyPI via `https://pypi.org/pypi/jira/json` (released 2025-07-28). [VERIFIED: pypi.org]
- `jira` requires Python >=3.10; QUIRK requires Python >=3.10 (pyproject.toml line 9). No conflict.
- `jira` depends on `requests`, `requests-toolbelt`, `defusedxml`, `Pillow`, `packaging`, `typing-extensions`. QUIRK core uses `httpx` not `requests` — no version conflict. [VERIFIED: pip dry-run on dev machine, slopcheck install output]
- No `postinstall` scripts in jira package (pure Python wheel). [ASSUMED — not explicitly checked via npm tooling; Python wheels do not use postinstall scripts by convention]

---

## Architecture Patterns

### System Architecture Diagram

```
quirk ticket create <args>
        │
        ▼
run_scan.py interception block
  (argv[1] == "ticket")
        │
        ▼
quirk/cli/ticket_cmd.py::run_ticket(argv)
  │  load findings-*.json
  │  load_ticketing_config()  ──► QUIRK_CONFIG_PATH [ticketing] block
  │  is_extra_available("tickets") → advisory + exit if missing
  │  validate_external_url(jira_url) → SSRF check (ISEC-01)
  │  get_session(db_path)
        │
        ▼
quirk/ticketing/base.py::TicketingChannel (ABC)
  dispatch_finding(finding, db, scan_id)
  │  compute_fingerprint(finding)  ──► SHA256(host:port::title) hex
  │  build_ticket_evidence(finding) ──► evidence_bridge (QRAMM dims)
  │  find_by_fingerprint(fp)       ──► [ABSTRACT: subclass implements]
  │       │
  │       ├── found → add_rediscovery_comment(issue_key, fp)  [ABSTRACT]
  │       └── not found → create_issue_from_finding(finding, fp, evidence)  [ABSTRACT]
  │  write_audit_row(db, scan_id, fp, destination, status, error)
        │
        ▼
quirk/ticketing/jira.py::JiraChannel(TicketingChannel)
  find_by_fingerprint(fp)
  │  search_issues(f'labels = "{fp}"')
  │  return first result or None
        │
  create_issue_from_finding(finding, fp, evidence)
  │  create_issue(fields={project, issuetype, summary, description, labels:[fp]})
        │
  add_rediscovery_comment(issue_key, fp)
  │  add_comment(issue_key, body="Rediscovery: ...")
        │
        ▼
quirk/models.py::IntegrationDelivery
  (destination="jira", finding_hash=fp, status="ok"/"failed")
```

### Recommended Project Structure

```
quirk/
├── ticketing/
│   ├── __init__.py           # exports TicketingChannel
│   ├── base.py               # ABC + fingerprint + evidence + audit (Phase 104)
│   └── jira.py               # JiraChannel subclass (Phase 104)
│   # servicenow.py           # Phase 105 only — no changes to base/jira
quirk/cli/
│   └── ticket_cmd.py         # run_ticket(argv) — mirror of export_cmd.py
quirk/ticketing/ config.py    # TicketingCfg dataclass + load_ticketing_config()
tests/
├── test_ticketing_base.py    # fingerprint, evidence, dispatch_finding unit tests
├── test_ticketing_jira.py    # JiraChannel: mock JIRA client, create/dedup/comment
├── test_ticket_cmd.py        # CLI: end-to-end with mock JiraChannel
├── test_install_all_includes_tickets.py  # CI guard (slow)
```

### Pattern 1: TicketingChannel ABC

**What:** Abstract base class in `base.py` that owns all shared logic. Subclasses implement only the backend API calls.

**When to use:** Any new ticketing backend (ServiceNow, GitHub Issues, etc.) subclasses this without touching the base.

```python
# Source: [VERIFIED: CONTEXT.md decisions + ABC stdlib]
# quirk/ticketing/base.py
from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from quirk.models import IntegrationDelivery
from quirk.util.safe_exc import safe_str

logger = logging.getLogger(__name__)


class TicketingChannel(ABC):
    """Shared orchestration layer for all ticketing backends (TICKET-04).

    Subclasses implement only the backend API calls:
      - find_by_fingerprint(fp) -> Optional[str]  (returns issue key/sys_id or None)
      - create_issue_from_finding(finding, fp, evidence) -> str  (returns issue key)
      - add_rediscovery_comment(issue_key, fp) -> None

    The base class owns: fingerprint, evidence build, dedup logic, audit rows.
    """

    # Subclasses declare: destination = "jira" or "servicenow"
    destination: str = "unknown"

    @abstractmethod
    def find_by_fingerprint(self, fp: str) -> Optional[str]:
        """Search backend for an existing ticket matching fingerprint fp.
        Returns the issue key/sys_id string if found, None otherwise."""
        ...

    @abstractmethod
    def create_issue_from_finding(
        self, finding: dict, fp: str, evidence: str
    ) -> str:
        """Create a new ticket in the backend. Returns the issue key/sys_id."""
        ...

    @abstractmethod
    def add_rediscovery_comment(self, issue_key: str, fp: str) -> None:
        """Append a rediscovery note to an existing ticket."""
        ...

    # ------------------------------------------------------------------ #
    # Shared: fingerprint, evidence, dispatch, audit                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def compute_fingerprint(finding: dict) -> str:
        """SHA256(host:port::title) hex — stable across re-scans (TICKET-03).

        NOTE: findings-*.json does NOT include 'protocol' or 'category' keys
        (verified against real output: keys are host, port, severity, title,
        description, recommendation, compliance, check_id, quantum_risk).
        Use title as the category proxy; protocol is empty string.
        Formula: SHA256(f"{host}:{port}::{title}") — deterministic because
        _build_finding produces deterministic titles.
        """
        host = str(finding.get("host") or "")
        port = str(finding.get("port") or "")
        title = str(finding.get("title") or "")
        raw = f"{host}:{port}::{title}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def build_ticket_evidence(finding: dict) -> str:
        """Build QRAMM dimension evidence string for ticket description.

        Currently provides a structured summary of the finding's fields plus
        the quantum_risk sentence. The evidence_bridge.py populates CVI
        dimension scores from DB scan data — for per-finding ticket descriptions,
        the relevant evidence is the finding-level fields.

        Returns a multi-line string for use as Jira issue description body.
        """
        lines = [
            f"**Finding:** {finding.get('title', 'Unknown')}",
            f"**Severity:** {finding.get('severity', 'LOW')}",
            f"**Host:** {finding.get('host', '')}:{finding.get('port', '')}",
            "",
            f"**Description:** {finding.get('description', '')}",
            "",
            f"**Recommendation:** {finding.get('recommendation', '')}",
        ]
        qr = finding.get("quantum_risk")
        if qr:
            lines += ["", f"**Quantum Risk:** {qr}"]
        return "\n".join(lines)

    def dispatch_finding(
        self, finding: dict, db, scan_id: str
    ) -> None:
        """Orchestrate dedup + create/update + audit for one finding.

        Called once per finding by the CLI. Never raises; all failures are
        captured in the audit row (mirrors siem/dispatcher.py pattern).
        """
        fp = self.compute_fingerprint(finding)
        evidence = self.build_ticket_evidence(finding)
        status = "ok"
        error_summary: Optional[str] = None

        try:
            existing_key = self.find_by_fingerprint(fp)
            if existing_key:
                self.add_rediscovery_comment(existing_key, fp)
            else:
                self.create_issue_from_finding(finding, fp, evidence)
        except Exception as exc:
            status = "failed"
            error_summary = safe_str(exc)
            logger.warning(
                "Ticket delivery failed [%s] finding=%r: %s",
                self.destination, finding.get("title", ""), error_summary,
            )

        row = IntegrationDelivery(
            scan_id=scan_id,
            finding_hash=fp,
            destination=self.destination,
            status=status,
            attempted_at=datetime.now(timezone.utc).replace(tzinfo=None),
            error_summary=error_summary,
        )
        db.add(row)
        try:
            db.commit()
        except Exception as exc:
            logger.warning("Ticket audit row commit failed: %s", safe_str(exc))
```

**ServiceNow forward-compat proof:** `ServiceNowChannel(TicketingChannel)` implements `find_by_fingerprint` via `urllib.request` GET to `/<table>?sysparm_query=u_quirk_fingerprint={fp}`, `create_issue_from_finding` via POST to `/<table>`, and `add_rediscovery_comment` via PATCH. Zero changes to base.py or jira.py required. [ASSUMED — ServiceNow Table API design; not executed]

### Pattern 2: JiraChannel Implementation

```python
# Source: [VERIFIED: jira.readthedocs.io/examples.html + CONTEXT.md]
# quirk/ticketing/jira.py
from __future__ import annotations

import logging
from typing import Optional

from quirk.ticketing.base import TicketingChannel
from quirk.util.safe_exc import safe_str

logger = logging.getLogger(__name__)


class JiraChannel(TicketingChannel):
    """Jira ticketing backend (TICKET-01, TICKET-03).

    Lazy-imports `jira` at __init__ time — never at module scope (ISEC-04).
    """

    destination = "jira"

    def __init__(self, cfg: "JiraTicketingCfg") -> None:
        """Construct JIRA client. Raises ImportError with advisory if jira missing."""
        # Lazy import — NEVER at module scope (optional-extra import trap)
        try:
            from jira import JIRA  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "Jira ticketing skipped — run `pip install quirk[tickets]` to enable"
            ) from exc
        import os
        self._cfg = cfg
        jira_url = cfg.jira_url
        user = os.environ.get(cfg.jira_user_env, "")
        token = os.environ.get(cfg.jira_token_env, "")
        if cfg.auth_mode == "cloud":
            # Cloud: basic_auth=(email, api_token) [VERIFIED: jira.readthedocs.io]
            self._client = JIRA(server=jira_url, basic_auth=(user, token))
        else:
            # Self-hosted Jira >= 8.14: token_auth=PAT [VERIFIED: jira.readthedocs.io]
            self._client = JIRA(server=jira_url, token_auth=token)

    def find_by_fingerprint(self, fp: str) -> Optional[str]:
        """JQL: labels = "<fp>" in the configured project. Returns issue key or None."""
        # fp is always 64-char hex — no JQL injection possible (no special chars)
        jql = f'project = {self._cfg.project_key} AND labels = "{fp}"'
        issues = self._client.search_issues(jql, maxResults=1)
        if issues:
            return issues[0].key
        return None

    def create_issue_from_finding(
        self, finding: dict, fp: str, evidence: str
    ) -> str:
        """Create one Jira issue. Returns the issue key (e.g. 'SEC-42')."""
        fields = {
            "project": {"key": self._cfg.project_key},
            "issuetype": {"name": self._cfg.issue_type},
            "summary": str(finding.get("title", "QUIRK Finding"))[:255],
            "description": evidence,
            "labels": [fp],
        }
        issue = self._client.create_issue(fields=fields)
        return issue.key  # type: ignore[return-value]

    def add_rediscovery_comment(self, issue_key: str, fp: str) -> None:
        """Append a rediscovery note to an existing Jira issue."""
        body = (
            f"*Rediscovery*: QUIRK re-detected this finding on a subsequent scan.\n"
            f"Fingerprint: `{fp}`"
        )
        self._client.add_comment(issue_key, body)
```

### Pattern 3: JiraTicketingCfg + Config Loader

```python
# Source: [ASSUMED — mirrors quirk/notify/config.py pattern exactly]
# quirk/ticketing/config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import yaml


@dataclass
class JiraTicketingCfg:
    """Jira ticketing configuration (TICKET-01).

    jira_user_env  — NAME of env var holding Jira username/email
    jira_token_env — NAME of env var holding Jira API token or PAT
    auth_mode      — "cloud" (basic_auth tuple) or "server" (token_auth PAT)
    """
    jira_url: str
    jira_user_env: str        # env-var NAME, not the value
    jira_token_env: str       # env-var NAME, not the value
    project_key: str
    issue_type: str = "Bug"
    auth_mode: str = "cloud"  # "cloud" or "server"


@dataclass
class TicketingCfg:
    jira: Optional[JiraTicketingCfg] = None


def load_ticketing_config(path: str | None = None) -> "TicketingCfg | None":
    """Load [ticketing] block from QUIRK YAML config.

    Returns None (not an error) when config absent or block missing.
    Binary/malformed files return None silently (Pitfall: SQLite DB path guard).
    """
    effective_path = path or os.environ.get("QUIRK_CONFIG_PATH")
    if not effective_path or not os.path.isfile(effective_path):
        return None
    try:
        with open(effective_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        ticketing_raw = (raw or {}).get("ticketing")
        if not ticketing_raw:
            return None
        return _parse_ticketing_cfg(ticketing_raw)
    except Exception:
        return None
```

**Sample YAML config block:**
```yaml
ticketing:
  jira:
    jira_url: "https://yourco.atlassian.net"
    jira_user_env: "QUIRK_JIRA_USER"
    jira_token_env: "QUIRK_JIRA_TOKEN"
    project_key: "SEC"
    issue_type: "Bug"
    auth_mode: "cloud"
```

### Pattern 4: CLI Interception (run_scan.py)

```python
# Source: [VERIFIED: run_scan.py line 496-499 — export_cmd pattern]
# Add immediately after the export block (~line 499):
if len(_sys.argv) > 1 and _sys.argv[1] == "ticket":
    from quirk.cli.ticket_cmd import run_ticket
    run_ticket(_sys.argv[2:])
    _sys.exit(0)
```

`ticket_cmd.py` mirrors `export_cmd.py` (Phase 103): argparse with `create` subcommand, `--input PATH`, `--output-dir DIR`.

### Pattern 5: `[tickets]` → `[all]` CI Guard Test

Mirrors `tests/test_install_all_includes_notify.py` exactly:
- `@pytest.mark.slow`
- `pip install --dry-run --report report.json -e <repo>[all]`
- Assert `jira` in the resolved set
- Assert no `"does not provide the extra 'tickets'"` in output

### Anti-Patterns to Avoid

- **Module-scope `import jira`:** Always lazy-import inside `__init__` or the function that needs it. A top-level `from jira import JIRA` in jira.py breaks minimal installs (Optional-extra import trap — see feedback_optional_extra_import_trap.md).
- **ABC too Jira-specific:** `find_by_fingerprint` must return `Optional[str]` (the issue key/sys_id), not a Jira Issue object. ServiceNow returns a sys_id string, Jira returns an issue key string. A Jira Issue object in the return type would break Phase 105.
- **`project = {key}` in JQL without quoting:** If project_key contains a space or special char, the JQL is malformed. Use parameterized project key: `f'project = "{self._cfg.project_key}" AND labels = "{fp}"'` (double-quoting both sides).
- **Per-finding db.commit() inside the try block:** Follows siem/dispatcher.py's WR-01 pattern — build audit row, handle delivery error, then commit. Don't commit inside the try; the row must be committed even on failure.
- **Logging raw token or password:** `safe_str(exc)` only — NEVER `str(exc)`. The Jira client may include credentials in exception messages on auth failure.
- **Storing Jira credentials in SQLite:** Only store env-var NAMES in `TicketingCfg`; resolve `os.environ[name]` at connection time, not config-load time.
- **Designing `build_ticket_evidence` against `evidence_bridge.populate_cvi_suggestions`:** That function updates `QRAMMAnswer` rows in the DB for a QRAMM session — it is not a finding-level evidence extractor. For per-finding ticket descriptions, use the finding dict fields directly. (See §QRAMM Evidence section below.)

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Jira REST HTTP calls | Raw `requests.post` to Jira API | `jira>=3.10.5` client | Auth, session management, multipart, retry, pagination all handled |
| Credential scrubbing | Custom regex on exc messages | `safe_str(exc)` (existing) | Phase 101 established pattern; regex misses all exception classes |
| SSRF validation | IP range checks inline | `validate_external_url()` (existing) | Phase 101 covers metadata service, RFC1918, link-local, loopback |
| SHA256 computation | Roll own hex encoding | `hashlib.sha256(...).hexdigest()` | stdlib, zero deps, produces 64-char hex safe as Jira label |
| Findings file discovery | Custom glob | `_find_latest_findings_in()` from `siem/dispatcher.py` or duplicate pattern | Already exists and tested; import or duplicate (prefer import) |
| Audit row writing | Custom table | `IntegrationDelivery` (existing, Phase 101) | `finding_hash` column was added specifically for this phase |

---

## Critical Research Finding: Fingerprint Formula Adaptation

**The CONTEXT.md formula `SHA256(host:port:protocol:category)` cannot be used literally.** [VERIFIED against real findings output]

**Evidence:** Real `findings-*.json` files (verified 2026-05-25 against 3 separate output files):
```
Keys in all findings: compliance, description, host, port, recommendation, severity, title
```
Neither `protocol` nor `category` appear in any finding dict. The `protocol` field exists on `CryptoEndpoint` DB rows but is not propagated to the findings JSON. The `category` key only appears in advisory findings (coverage_gap entries) set at `quirk/engine/findings_evaluator.py:475`.

**Recommended formula:**
```python
raw = f"{host}:{port}::{title}"  # protocol="" category=title
fp = hashlib.sha256(raw.encode("utf-8")).hexdigest()
```

**Why `title` as category proxy:** `_build_finding` at `findings_evaluator.py:71-143` produces deterministic titles for each finding type (the title is a constant string per check, e.g. "Legacy TLS cipher suites accepted"). This gives stable fingerprints across re-scans of the same host/port/finding.

**Fingerprint safety as Jira label:** SHA256 hex is 64 chars of `[0-9a-f]` — no JQL metacharacters (no `"`, `=`, spaces). Safe to embed in `labels = "{fp}"` JQL without escaping. [VERIFIED: hashlib output format]

**Phase 105 compatibility:** ServiceNow can store the same fingerprint in a custom field (`u_quirk_fingerprint`) and search with `sysparm_query=u_quirk_fingerprint={fp}`. Both backends compute the same formula via the shared `compute_fingerprint()` in base.py.

**The planner must lock this formula explicitly** — do not leave it as "per CONTEXT.md" since CONTEXT.md assumes fields that don't exist in the output.

---

## QRAMM Evidence: What `evidence_bridge.py` Provides

[VERIFIED: reading `quirk/qramm/evidence_bridge.py`]

`quirk/qramm/evidence_bridge.py` exports `populate_cvi_suggestions(session_id, db)` — this function:
- Queries `CryptoEndpoint` rows for the latest scan date
- Computes CVI dimension scores (1.1 Discovery, 1.2 Vulnerability Assessment, 1.3 Dependency Mapping)
- Updates `QRAMMAnswer` rows with `suggested_answer` and `evidence_source`
- Returns `None`; writes directly to DB

**This is NOT a per-finding evidence extractor.** It operates on the entire scan's endpoint set and writes to the QRAMM session answer table. It does not produce a string or dict of evidence for a single finding.

**For ticket descriptions (TICKET-01), the approach is:**
1. Use the finding dict's own fields (`title`, `severity`, `host`, `port`, `description`, `recommendation`, `quantum_risk`) as the primary evidence content.
2. Optionally query the latest QRAMM session scores from the DB (`QRAMMAnswer` rows where `dimension="CVI"`) and append them as context.
3. The simplest correct implementation that satisfies TICKET-01 is `build_ticket_evidence(finding: dict) -> str` using only the finding dict — no DB query required.

**If the planner wants QRAMM dimension scores in tickets**, a separate helper `_get_qramm_summary(db) -> str` can query `QRAMMAnswer` rows — but this is optional and not required by TICKET-01.

---

## Fingerprint Dedup: JQL Label Search Mechanics

[VERIFIED: jira.readthedocs.io/examples.html]

```python
# JQL syntax for label search — verified from official docs
jql = f'project = "SEC" AND labels = "{fp}"'
issues = jira_client.search_issues(jql, maxResults=1)
# Returns a jira.ResultList; truthy if non-empty
if issues:
    issue_key = issues[0].key  # e.g. "SEC-42"
```

**JQL label filter exact syntax:** `labels = "LABELVALUE"` — double-quoted label value, single equals. [VERIFIED: jira.readthedocs.io] The fingerprint (64-char hex) contains no chars requiring escaping.

**`search_issues` return type:** `jira.ResultList` — a list-like object. `issues[0]` is a `jira.resources.Issue`. `issues[0].key` is the issue key string (e.g. `"SEC-42"`).

**`maxResults=1`:** Sufficient since fingerprint is a SHA256 hex and should be globally unique per finding identity. Adding `maxResults=1` avoids fetching all matching issues.

---

## Jira Library API Reference

[VERIFIED: jira.readthedocs.io/examples.html + pypi.org/project/jira]

### Client Construction

```python
from jira import JIRA

# Cloud (email + API token):
client = JIRA(server="https://yourco.atlassian.net", basic_auth=("user@co.com", "api_token"))

# Self-hosted >= 8.14 (Personal Access Token):
client = JIRA(server="https://jira.internal.com", token_auth="your_pat_here")
```

Auth mode must be configurable — Cloud and Server use different constructor arguments.

### create_issue Field Dict

```python
# Source: [VERIFIED: jira.readthedocs.io/examples.html]
fields = {
    "project": {"key": "SEC"},          # project key (not ID)
    "issuetype": {"name": "Bug"},       # issuetype by name
    "summary": "Finding title here",    # max 255 chars enforced by Jira
    "description": "Evidence body...",  # plain text or Jira markup
    "labels": ["64-char-hex-fp"],       # list of label strings
}
issue = client.create_issue(fields=fields)
issue_key = issue.key  # "SEC-42"
```

### add_comment

```python
# Source: [VERIFIED: jira.readthedocs.io/examples.html]
client.add_comment("SEC-42", "Comment body text here")
```

### search_issues (JQL)

```python
# Source: [VERIFIED: jira.readthedocs.io/examples.html]
issues = client.search_issues('project = "SEC" AND labels = "abc123def456..."', maxResults=1)
```

---

## Common Pitfalls

### Pitfall 1: `import jira` at Module Scope
**What goes wrong:** `quirk/ticketing/jira.py` has `from jira import JIRA` at the top of the file. On minimal install (`pip install quirk-scanner` without `[tickets]`), importing any module in `quirk/ticketing/` raises `ModuleNotFoundError`, breaking `quirk` startup.
**Why it happens:** Python resolves top-level imports at module import time, not call time. Any code path that imports `quirk.ticketing.jira` will fail.
**How to avoid:** Lazy-import inside `JiraChannel.__init__`: `from jira import JIRA` inside the function body. The `is_extra_available("tickets")` check in ticket_cmd.py provides the advisory before the constructor is called.
**Warning signs:** Any test that imports jira.py without `[tickets]` installed raises ImportError at import, not at test execution.

### Pitfall 2: ABC Too Jira-Specific
**What goes wrong:** `find_by_fingerprint` returns a `jira.resources.Issue` object. Phase 105 `ServiceNowChannel` cannot return a Jira Issue object — ServiceNow returns a sys_id dict.
**Why it happens:** Designing the ABC before thinking through the ServiceNow return type.
**How to avoid:** `find_by_fingerprint(fp) -> Optional[str]` — returns the string key/sys_id or None. Both backends return strings; the base class passes this string to `add_rediscovery_comment`.
**Warning signs:** Any type annotation in `base.py` that references `jira.*` types.

### Pitfall 3: Fingerprint Formula Mismatch Between Phases
**What goes wrong:** Phase 104 computes `SHA256(host:port::title)`, Phase 105 computes `SHA256(host:port:protocol:category)`. A finding ticketed in Jira and ServiceNow gets different fingerprints, breaking the shared dedup contract.
**Why it happens:** Phase 105 developer uses the raw CONTEXT.md formula without reading the Phase 104 research.
**How to avoid:** `compute_fingerprint` is a `@staticmethod` in `base.py` — both JiraChannel and ServiceNowChannel inherit the identical implementation. Never override it in subclasses.
**Warning signs:** Any `compute_fingerprint` method in servicenow.py.

### Pitfall 4: JQL Project Key Without Quotes
**What goes wrong:** `f'project = {cfg.project_key} AND labels = "{fp}"'` — if project_key is `SEC` this works, but if it's a multi-word name or starts with a digit the JQL is malformed.
**How to avoid:** Always double-quote the project key: `f'project = "{cfg.project_key}" AND labels = "{fp}"'`.

### Pitfall 5: Credentials Leaking Through Exception Messages
**What goes wrong:** `logger.warning("Jira error: %s", str(exc))` — the jira library may include the Authorization header value or token in connection error messages.
**How to avoid:** Always `safe_str(exc)`, never `str(exc)`. [VERIFIED: existing QUIRK discipline from Phase 101 ISEC-02]

### Pitfall 6: SQLite DB Path Passed to `load_ticketing_config`
**What goes wrong:** The scheduler's `--config` is a SQLite .db path. If `load_ticketing_config()` is ever called from the scheduler hook with that path, `yaml.safe_load` raises (or returns None from the except guard). (No scheduler hook is in scope for Phase 104 — CLI only. But the config loader must still guard against this.)
**How to avoid:** The `except Exception: return None` guard in the config loader handles this silently. Document the constraint in the docstring as with notify/config.py.

### Pitfall 7: `jira>=3.10.5` Version Not on Local pip Index
**What goes wrong:** `pip install "jira>=3.10.5"` resolves to 3.8.0 because the local pip cache only knows about 3.8.0. This only manifests if `--no-index` or a private index is in use.
**Why it happens:** The local pip index showed `jira (3.8.0)` as the available version, but PyPI shows 3.10.5 as the latest (released 2025-07-28). `pip install` against the public PyPI index will resolve correctly.
**How to avoid:** At execute time, run `pip install "jira>=3.10.5"` against the public PyPI index and verify the resolved version. If using an internal PyPI mirror, confirm 3.10.5 is mirrored. [VERIFIED: 3.10.5 exists on pypi.org/project/jira/]

---

## Runtime State Inventory

This is a greenfield module addition — no renames, no refactors, no migration needed. All new files; no existing runtime state affected.

**Step 2.5: SKIPPED — new module, not a rename/refactor/migration phase.**

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All | ✓ | system Python 3.14 (dev machine) | — |
| PyPI internet access | `jira>=3.10.5` install | ✓ | — | Private mirror (operator concern) |
| Jira instance | TICKET-01 (runtime) | not probed | — | Tests mock the JIRA client |

**Missing dependencies with no fallback:**
- A live Jira instance is required for end-to-end manual UAT, not for CI. All CI tests mock the jira client.

**Missing dependencies with fallback:**
- `jira>=3.10.5` not yet installed in the project venv — install task in Wave 0 plan.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pytest.ini` or `setup.cfg` (existing) |
| Quick run command | `python -m pytest tests/test_ticketing_base.py tests/test_ticketing_jira.py tests/test_ticket_cmd.py -x -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TICKET-01 | Jira issue created per finding with QRAMM evidence | unit | `pytest tests/test_ticketing_jira.py::test_create_issue_per_finding -x` | ❌ Wave 0 |
| TICKET-01 | Missing `[tickets]` extra → advisory + graceful skip | unit | `pytest tests/test_ticketing_jira.py::test_missing_extra_graceful_skip -x` | ❌ Wave 0 |
| TICKET-03 | First run: create_issue called; second run: add_comment called, no new issue | unit | `pytest tests/test_ticketing_jira.py::test_dedup_creates_once_then_comments -x` | ❌ Wave 0 |
| TICKET-03 | `finding_hash` in `integration_deliveries` row equals computed fingerprint | unit | `pytest tests/test_ticketing_base.py::test_audit_row_finding_hash -x` | ❌ Wave 0 |
| TICKET-04 | `compute_fingerprint` returns identical 64-char hex for same input | unit | `pytest tests/test_ticketing_base.py::test_fingerprint_stable -x` | ❌ Wave 0 |
| TICKET-04 | Fingerprint input: `host:port::title` format; no protocol/category | unit | `pytest tests/test_ticketing_base.py::test_fingerprint_formula -x` | ❌ Wave 0 |
| ISEC-02 | Credentials never appear in error_summary (safe_str enforced) | unit | `pytest tests/test_ticketing_jira.py::test_credentials_not_in_logs -x` | ❌ Wave 0 |
| ISEC-04 | Missing extra → advisory printed, no ImportError raised | unit | `pytest tests/test_ticket_cmd.py::test_missing_extra_advisory -x` | ❌ Wave 0 |
| CI guard | `quirk[all]` pulls `jira` | slow | `pytest tests/test_install_all_includes_tickets.py -m slow` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_ticketing_base.py tests/test_ticketing_jira.py -x -q`
- **Per wave merge:** `python -m pytest tests/test_ticketing_base.py tests/test_ticketing_jira.py tests/test_ticket_cmd.py -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_ticketing_base.py` — fingerprint stability, evidence build, dispatch_finding, audit row
- [ ] `tests/test_ticketing_jira.py` — mock JIRA client, create/dedup/comment, missing-extra skip, creds scrubbing
- [ ] `tests/test_ticket_cmd.py` — CLI entry point, missing-extra advisory, --input flag, exit codes
- [ ] `tests/test_install_all_includes_tickets.py` — slow CI guard for `[all]` including jira
- [ ] `quirk/ticketing/__init__.py` — package init
- [ ] `quirk/ticketing/base.py` — ABC
- [ ] `quirk/ticketing/jira.py` — JiraChannel
- [ ] `quirk/ticketing/config.py` — TicketingCfg + loader

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes — Jira credentials | Env-var-name references only; resolve at delivery time; never persist |
| V3 Session Management | no — stateless per-call | — |
| V4 Access Control | no — CLI tool, not multi-user | — |
| V5 Input Validation | yes — Jira URL, project_key, finding fields | `validate_external_url()` for SSRF; JQL injection blocked by hex fingerprint |
| V6 Cryptography | yes — fingerprint | `hashlib.sha256` stdlib; never hand-roll |

### Known Threat Patterns for Jira Integration Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSRF via user-supplied Jira URL | Spoofing / Info Disclosure | `validate_external_url(cfg.jira_url)` at connection time; allow_internal=False for Cloud, operator decides for self-hosted |
| Credential leakage in logs | Info Disclosure | `safe_str(exc)` on ALL exception handlers; never `str(exc)` |
| JQL injection via label value | Tampering | Fingerprint is 64-char hex `[0-9a-f]` — no JQL special chars possible |
| Exfiltration of sensitive finding fields | Info Disclosure | `build_ticket_evidence()` is the whitelist function — only include named fields; never send `compliance`, `check_id`, raw PEM/certs |
| Duplicate ticket storm on re-scan | Denial of Service | find_by_fingerprint() JQL before create; dedup is load-bearing |
| Optional-extra import at module scope | Availability | Lazy `from jira import JIRA` inside `__init__` only |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Parallel hand-built Jira + ServiceNow code paths | Shared `TicketingChannel` ABC | Phase 104 design decision | Phase 105 zero changes to base/jira |
| Per-finding DB commit in dispatcher | Collect row, commit after dispatch | Phase 101 WR-01 pattern | Prevents one channel's DB error from silently skipping the audit row |
| `jira` library `basic_auth` string | Cloud: `basic_auth=(email, token)` tuple; Server: `token_auth=PAT` | jira 3.x | Auth mode must be configurable per deployment type |

**Deprecated/outdated:**
- `jira` library cookie-based auth: not recommended for new integrations; use `basic_auth` (Cloud) or `token_auth` (Server).

---

## Open Questions

1. **Auth mode config field**
   - What we know: Cloud requires `basic_auth=(email, token)` tuple; Server requires `token_auth=PAT`. Both need to be supported.
   - What's unclear: Should `auth_mode` default to `"cloud"` or should the planner require explicit configuration? Jira Cloud is the most common deployment for teams that don't self-host.
   - Recommendation: Default `auth_mode = "cloud"` in `JiraTicketingCfg`. Document Server mode in the config block comment.

2. **`build_ticket_evidence` scope: finding-dict-only vs DB QRAMM scores**
   - What we know: `evidence_bridge.populate_cvi_suggestions` operates on the entire scan's DB data, not per-finding. Per-finding evidence = the finding dict fields.
   - What's unclear: Does TICKET-01 require QRAMM dimension scores (CVI 1.1/1.2/1.3) in each ticket, or is the finding-level evidence sufficient?
   - Recommendation: Ship finding-dict-only evidence for Phase 104. QRAMM scores are scan-level context, not per-finding evidence. A follow-up can add an optional `_get_qramm_summary(db)` call if the user requests it.

3. **`is_extra_available` registry entry for `tickets`**
   - What we know: `is_extra_available(extra)` looks up `extra` in `REGISTRY` (tuple of `OptionalExtra` in `optional_extra.py`). It returns `False` for any extra not in REGISTRY.
   - What's unclear: Does Phase 104 need to add a `tickets` entry to `REGISTRY`, or can `ticket_cmd.py` call `is_extra_available("tickets")` directly via a simpler `find_spec("jira")` check?
   - Recommendation: Add a `tickets` entry to REGISTRY with `modules=("jira",)` and `enabled_attrs=()` (always-probe, like the dashboard entry). This keeps the advisory pattern consistent and allows `probe_missing_extras` to surface the advisory automatically if `[tickets]` is missing.

4. **SSRF: allow_internal for self-hosted Jira**
   - What we know: `validate_external_url(url, allow_internal=False)` rejects RFC1918/loopback. Self-hosted Jira on an internal network would be rejected.
   - What's unclear: Should `allow_internal` be configurable in `JiraTicketingCfg`?
   - Recommendation: Add `allow_internal: bool = False` to `JiraTicketingCfg`. Operators running self-hosted Jira set `allow_internal: true` in their YAML. Metadata service IPs are always blocked regardless.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Fingerprint formula adapted to `SHA256(host:port::title)` due to absence of `protocol`/`category` in findings JSON | Critical Research Finding | Fingerprints differ from Phase 105 expected formula; must align both phases |
| A2 | `build_ticket_evidence` uses finding dict fields only (no DB QRAMM scores) | QRAMM Evidence section | Missing QRAMM context in tickets; low risk, optional enhancement |
| A3 | `jira 3.10.5` requires Python >=3.10; no dep conflict with QUIRK core deps (httpx, requests coexist) | Package Legitimacy Audit | Dep conflict at install time; risk LOW (httpx and requests coexist routinely) |
| A4 | `auth_mode = "cloud"` as default in JiraTicketingCfg | Pattern 3 | Server deployments break without explicit config; risk LOW (user must configure) |
| A5 | `allow_internal=False` default; config field for self-hosted Jira | Security Domain | Self-hosted Jira operators blocked by SSRF guard; risk LOW (configurable) |
| A6 | `jira` package has no postinstall scripts (Python wheel, no npm tooling) | Package Legitimacy Audit | Risk effectively zero for pure Python wheels |

---

## Sources

### Primary (HIGH confidence)

- `quirk/engine/findings_evaluator.py:71-143` — `_build_finding` chokepoint; confirmed findings keys; `protocol`/`category` absence confirmed against real output files
- `output/findings-20260522-011356.json` and `output/findings-20260509-190256.json` — real findings output; all keys verified
- `quirk/notify/config.py`, `quirk/notify/dispatcher.py` — `[notify]` pattern for config loader and dispatcher
- `quirk/siem/config.py`, `quirk/siem/dispatcher.py` — `[siem]` pattern; freshest analog for the ticketing dispatcher
- `quirk/cli/export_cmd.py` — freshest CLI pattern; `run_ticket` mirrors `run_export`
- `quirk/util/optional_extra.py` — `is_extra_available` implementation verified
- `quirk/models.py:244-261` — `IntegrationDelivery` schema with `finding_hash` column confirmed
- `run_scan.py:496-499` — export interception block; ticket interception placement confirmed
- `pyproject.toml:87-105` — `[notify]`→`[all]` pattern confirmed; `[tickets]` addition site identified
- `tests/test_install_all_includes_notify.py` — CI guard pattern; `test_install_all_includes_tickets.py` mirrors this
- [VERIFIED: pypi.org/project/jira] — jira 3.10.5 released 2025-07-28; Python >=3.10 requirement
- [VERIFIED: jira.readthedocs.io/examples.html] — `basic_auth=(email, token)`, `token_auth=PAT`, `create_issue(fields=...)`, `add_comment`, `search_issues(jql)` API confirmed
- [VERIFIED: slopcheck install jira] — `[OK]` verdict; `github.com/pycontribs/jira`

### Secondary (MEDIUM confidence)

- [CITED: jira.readthedocs.io] — Cloud vs Server auth mode distinction (`basic_auth` tuple vs `token_auth` string)
- `quirk/qramm/evidence_bridge.py` — `populate_cvi_suggestions` signature confirmed; per-finding evidence note derived from reading the implementation

### Tertiary (LOW confidence — marked [ASSUMED])

- ServiceNow Table API forward-compat design (A1-A6 in assumptions log) — based on training knowledge of ServiceNow REST API; not verified against live instance
- `jira` postinstall script absence (Python wheel convention) — not verified via `npm view` equivalent for Python

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — jira 3.10.5 on PyPI verified; slopcheck OK
- Architecture: HIGH — ABC design derived from verified codebase patterns
- Fingerprint formula: HIGH — derived from verified real output files; critical finding
- Pitfalls: HIGH — optional-extra import trap is a documented project feedback item
- QRAMM evidence: MEDIUM — evidence_bridge.py read and confirmed; per-finding approach is inferred

**Research date:** 2026-05-25
**Valid until:** 2026-08-25 (jira library API stable; fingerprint formula is a codebase contract)
