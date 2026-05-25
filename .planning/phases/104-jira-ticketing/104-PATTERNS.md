# Phase 104: Jira Ticketing - Pattern Map

**Mapped:** 2026-05-25
**Files analyzed:** 12 (8 new, 4 modified)
**Analogs found:** 12 / 12

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/ticketing/__init__.py` | package init | — | `quirk/notify/__init__.py` | exact |
| `quirk/ticketing/base.py` | service / ABC | request-response + CRUD | `quirk/notify/dispatcher.py` + `quirk/siem/dispatcher.py` | role-match |
| `quirk/ticketing/jira.py` | service / backend | request-response | `quirk/notify/channels/slack.py` | exact (lazy-import + optional-extra) |
| `quirk/ticketing/config.py` | config | — | `quirk/notify/config.py` (nested) + `quirk/siem/config.py` (flat) | exact |
| `quirk/cli/ticket_cmd.py` | CLI entrypoint | request-response | `quirk/cli/export_cmd.py` | exact |
| `run_scan.py` (modify) | CLI interception | — | `run_scan.py` lines 496–500 (export block) | exact |
| `pyproject.toml` (modify) | config | — | `pyproject.toml` lines 87–105 (`[notify]`/`[all]`) | exact |
| `quirk/util/optional_extra.py` (modify) | utility | — | `quirk/util/optional_extra.py` REGISTRY entries (lines 79–148) | exact |
| `tests/test_ticketing_base.py` | test | — | `tests/test_install_all_includes_notify.py` (structure) | role-match |
| `tests/test_ticketing_jira.py` | test | — | `tests/test_install_all_includes_notify.py` (structure) | role-match |
| `tests/test_ticket_cmd.py` | test | — | `quirk/cli/export_cmd.py` + existing CLI tests | role-match |
| `tests/test_install_all_includes_tickets.py` | test (slow, CI guard) | — | `tests/test_install_all_includes_notify.py` | exact |

---

## Pattern Assignments

### `quirk/ticketing/__init__.py` (package init)

**Analog:** `quirk/notify/__init__.py` (lines 1–22)

**Imports and re-export pattern** (lines 1–22):
```python
"""quirk.ticketing — Ticketing fan-out package (Phase 104 TICKET-01/03/04).

Public re-exports:
  TicketingChannel        — ABC (TICKET-04)
  JiraChannel             — Jira backend (TICKET-01)
  TicketingCfg            — config dataclass
  load_ticketing_config   — config loader
"""
from __future__ import annotations

from quirk.ticketing.base import TicketingChannel
from quirk.ticketing.jira import JiraChannel
from quirk.ticketing.config import TicketingCfg, load_ticketing_config

__all__ = [
    "TicketingChannel",
    "JiraChannel",
    "TicketingCfg",
    "load_ticketing_config",
]
```

**Note:** Keep `JiraChannel` import here; it will raise lazily only when the class is
instantiated (lazy-import inside `__init__`), not at package import time.

---

### `quirk/ticketing/base.py` (service ABC, request-response + CRUD)

**Primary analogs:**
- `quirk/siem/dispatcher.py` — `IntegrationDelivery` audit row pattern, `safe_str`, commit-after-delivery structure (lines 98–111)
- `quirk/notify/dispatcher.py` — per-channel failure isolation, `audit_rows` collect-then-commit (WR-01) (lines 200–269)

**Module docstring pattern** (from `quirk/siem/dispatcher.py` lines 1–17):
```python
"""quirk.ticketing.base — TicketingChannel ABC + shared orchestration (Phase 104 TICKET-04).

This module is the integration seam that:
  1. Computes the stable fingerprint SHA256(host:port::title) for each finding.
  2. Builds QRAMM evidence text for ticket descriptions.
  3. Orchestrates dedup: find_by_fingerprint → add_rediscovery_comment or create_issue.
  4. Writes one IntegrationDelivery audit row per finding attempt.

CRITICAL CONSTRAINTS:
  - dispatch_finding MUST NOT raise into callers — failure isolation is absolute.
  - error_summary is ALWAYS safe_str(exc) — never str(exc) or repr(exc) (ISEC-02).
  - Fingerprint formula: SHA256(f"{host}:{port}::{title}") — NEVER override
    compute_fingerprint in subclasses (shared contract with Phase 105 ServiceNow).
  - find_by_fingerprint returns Optional[str] (string key/sys_id), NEVER a Jira
    Issue object — Phase 105 ServiceNow returns a sys_id string, not a Jira type.
  - Credentials MUST NOT appear in logs or error_summary — always safe_str(exc).
"""
```

**Imports pattern**:
```python
from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from quirk.models import IntegrationDelivery
from quirk.util.safe_exc import safe_str

logger = logging.getLogger(__name__)
```

**ABC + abstractmethod pattern** (use `abc.ABC` + `@abstractmethod`):
```python
class TicketingChannel(ABC):
    """Shared orchestration layer for all ticketing backends (TICKET-04).

    Subclasses implement ONLY:
      - find_by_fingerprint(fp) -> Optional[str]
      - create_issue_from_finding(finding, fp, evidence) -> str
      - add_rediscovery_comment(issue_key, fp) -> None

    The base class owns: fingerprint, evidence build, dedup logic, audit rows.
    Phase 105 ServiceNow adds servicenow.py only — zero changes to base.py.
    """

    destination: str = "unknown"  # subclasses declare "jira" or "servicenow"

    @abstractmethod
    def find_by_fingerprint(self, fp: str) -> Optional[str]:
        """Return issue key/sys_id string if found, None otherwise."""
        ...

    @abstractmethod
    def create_issue_from_finding(self, finding: dict, fp: str, evidence: str) -> str:
        """Create a new ticket. Returns issue key/sys_id string."""
        ...

    @abstractmethod
    def add_rediscovery_comment(self, issue_key: str, fp: str) -> None:
        """Append a rediscovery note to an existing ticket."""
        ...
```

**Fingerprint static method** (TICKET-03; no override in subclasses):
```python
    @staticmethod
    def compute_fingerprint(finding: dict) -> str:
        """SHA256(host:port::title) hex — stable across re-scans (TICKET-03).

        NOTE: findings-*.json has NO 'protocol' or 'category' keys (verified
        against real output). Formula uses title as category proxy, empty
        protocol. Produces 64-char hex safe as a Jira label.
        Phase 105 inherits this staticmethod — NEVER override in subclasses.
        """
        host = str(finding.get("host") or "")
        port = str(finding.get("port") or "")
        title = str(finding.get("title") or "")
        raw = f"{host}:{port}::{title}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
```

**Dispatch + audit row pattern** (mirror `quirk/siem/dispatcher.py` lines 61–111, adapted for per-finding):
```python
    def dispatch_finding(self, finding: dict, db, scan_id: str) -> None:
        """Orchestrate dedup + create/update + audit for one finding.

        Never raises — all failures captured in audit row (NOTIFY-07 pattern).
        Commit is always outside the try block (WR-01): the row is committed
        even on delivery failure so the audit record is never lost.
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
            error_summary = safe_str(exc)   # NEVER str(exc) — may contain credentials
            logger.warning(
                "Ticket delivery failed [%s] finding=%r: %s",
                self.destination, finding.get("title", ""), error_summary,
            )

        row = IntegrationDelivery(
            scan_id=scan_id,
            finding_hash=fp,            # SHA256 dedup key — TICKET-03
            destination=self.destination,
            status=status,
            attempted_at=datetime.now(timezone.utc).replace(tzinfo=None),
            error_summary=error_summary,
        )
        db.add(row)
        try:
            db.commit()                 # commit outside try — WR-01 pattern
        except Exception as exc:
            logger.warning("Ticket audit row commit failed: %s", safe_str(exc))
```

**WR-01 note:** The commit is intentionally outside the delivery try/except block. This matches the
`quirk/siem/dispatcher.py` lines 106–110 pattern exactly. A DB commit failure must not prevent the
delivery attempt from being attempted, and a delivery failure must not cause the audit row to be
skipped.

---

### `quirk/ticketing/jira.py` (service backend, request-response)

**Primary analog:** `quirk/notify/channels/slack.py` — lazy-import + optional-extra guard + SSRF
validation pattern (lines 1–74).

**Module docstring + lazy-import guard pattern** (from `quirk/notify/channels/slack.py` lines 1–22):
```python
"""quirk.ticketing.jira — Jira ticketing backend (Phase 104 TICKET-01/TICKET-03).

Security controls:
  ISEC-01: validate_external_url() called at construction time, before any connection.
  ISEC-04: jira is an optional extra ([tickets]). Missing jira → ImportError with
           advisory message; is_extra_available("tickets") checked first in ticket_cmd.py.

Local-import shadow trap guard (MEMORY note):
  The `from jira import JIRA` import MUST live inside JiraChannel.__init__, AFTER the
  try/except gate. It must NEVER appear at module top level. Top-level import breaks
  minimal installs (optional-extra import trap — feedback_optional_extra_import_trap.md).
"""
```

**Imports (module-scope only — NO jira import here)**:
```python
from __future__ import annotations

import logging
import os
from typing import Optional

from quirk.ticketing.base import TicketingChannel
from quirk.util.safe_exc import safe_str
from quirk.util.url_allowlist import validate_external_url

logger = logging.getLogger(__name__)
```

**Lazy-import + SSRF + auth construction pattern** (adapted from `slack.py` lines 36–66):
```python
class JiraChannel(TicketingChannel):
    destination = "jira"

    def __init__(self, cfg: "JiraTicketingCfg") -> None:
        # Lazy import — NEVER at module scope (optional-extra import trap)
        try:
            from jira import JIRA  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "Jira ticketing skipped — run `pip install quirk[tickets]` to enable"
            ) from exc

        # SSRF guard at construction time, before any connection (ISEC-01)
        result = validate_external_url(cfg.jira_url)
        if not result.ok:
            raise ValueError(f"SSRF blocked ({result.reason}) for Jira URL")

        self._cfg = cfg
        # Resolve credentials from env vars at connection time — NEVER from config
        user = os.environ.get(cfg.jira_user_env, "")
        token = os.environ.get(cfg.jira_token_env, "")
        if cfg.auth_mode == "cloud":
            # Cloud: basic_auth=(email, api_token) tuple
            self._client = JIRA(server=cfg.jira_url, basic_auth=(user, token))
        else:
            # Self-hosted >= 8.14: token_auth=PAT string
            self._client = JIRA(server=cfg.jira_url, token_auth=token)
```

**JQL label search pattern** (TICKET-03 dedup):
```python
    def find_by_fingerprint(self, fp: str) -> Optional[str]:
        # fp is 64-char hex [0-9a-f] — no JQL metacharacters; safe to embed directly
        # Project key double-quoted to handle multi-word or numeric-start keys
        jql = f'project = "{self._cfg.project_key}" AND labels = "{fp}"'
        issues = self._client.search_issues(jql, maxResults=1)
        if issues:
            return issues[0].key
        return None
```

**Create issue pattern** (TICKET-01):
```python
    def create_issue_from_finding(self, finding: dict, fp: str, evidence: str) -> str:
        fields = {
            "project": {"key": self._cfg.project_key},
            "issuetype": {"name": self._cfg.issue_type},
            "summary": str(finding.get("title", "QUIRK Finding"))[:255],  # Jira max
            "description": evidence,
            "labels": [fp],
        }
        issue = self._client.create_issue(fields=fields)
        return issue.key

    def add_rediscovery_comment(self, issue_key: str, fp: str) -> None:
        body = (
            f"*Rediscovery*: QUIRK re-detected this finding on a subsequent scan.\n"
            f"Fingerprint: `{fp}`"
        )
        self._client.add_comment(issue_key, body)
```

---

### `quirk/ticketing/config.py` (config, loader)

**Primary analogs:**
- `quirk/notify/config.py` — nested dataclasses + `_parse_*` helpers + `load_*_config()` pattern (all lines)
- `quirk/siem/config.py` — flat dataclass + single `_parse_*` + `load_siem_config()` pattern (all lines)

**Dataclass pattern with env-var-NAME fields** (from `quirk/notify/config.py` lines 30–82):
```python
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import yaml


@dataclass
class JiraTicketingCfg:
    """Jira ticketing configuration (TICKET-01).

    jira_user_env  — NAME of env var holding Jira username/email (not the value)
    jira_token_env — NAME of env var holding Jira API token or PAT (not the value)
    auth_mode      — "cloud" (basic_auth tuple) or "server" (token_auth PAT string)
    allow_internal — False for Jira Cloud; True for self-hosted on RFC1918 networks
    """
    jira_url: str
    jira_user_env: str        # env-var NAME, not the credential value
    jira_token_env: str       # env-var NAME, not the credential value
    project_key: str
    issue_type: str = "Bug"
    auth_mode: str = "cloud"  # "cloud" or "server"
    allow_internal: bool = False


@dataclass
class TicketingCfg:
    jira: Optional[JiraTicketingCfg] = None
```

**Config loader pattern** (from `quirk/notify/config.py` lines 159–184 and `quirk/siem/config.py`
lines 68–95 — the two are identical in structure; use this exact shape):
```python
def load_ticketing_config(path: str | None = None) -> "TicketingCfg | None":
    """Load the [ticketing] block from the QUIRK YAML config.

    Priority: explicit path > QUIRK_CONFIG_PATH env var > None (disabled).

    Returns None when:
    - No path is resolvable (ticketing disabled — not an error).
    - The file does not exist.
    - The file is not valid YAML (e.g. a SQLite .db file — Pitfall: SQLite
      DB path guard; scheduler passes --config which is a .db path).
    - The YAML has no [ticketing] top-level key.

    Ticketing config failure MUST NEVER abort a running scan.
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
        # Binary / malformed / non-YAML files return None silently.
        return None
```

**`_parse_ticketing_cfg` helper** (from `quirk/notify/config.py` `_parse_notify_cfg` pattern lines
136–151):
```python
def _parse_ticketing_cfg(raw: dict) -> TicketingCfg:
    jira_raw = raw.get("jira") or {}
    return TicketingCfg(jira=_parse_jira_cfg(jira_raw))


def _parse_jira_cfg(raw: dict) -> Optional[JiraTicketingCfg]:
    if not raw:
        return None
    jira_url = raw.get("jira_url")
    if not jira_url:
        return None
    return JiraTicketingCfg(
        jira_url=str(jira_url),
        jira_user_env=str(raw.get("jira_user_env", "")),
        jira_token_env=str(raw.get("jira_token_env", "")),
        project_key=str(raw.get("project_key", "")),
        issue_type=str(raw.get("issue_type", "Bug")),
        auth_mode=str(raw.get("auth_mode", "cloud")).lower(),
        allow_internal=bool(raw.get("allow_internal", False)),
    )
```

---

### `quirk/cli/ticket_cmd.py` (CLI entrypoint, request-response)

**Primary analog:** `quirk/cli/export_cmd.py` (all lines 1–166) — exact mirror.

**Module docstring + imports pattern** (from `quirk/cli/export_cmd.py` lines 1–30):
```python
"""quirk.cli.ticket_cmd — `quirk ticket` CLI entrypoint (Phase 104 TICKET-01).

Entry point for creating Jira tickets from scan findings.

Usage:
  quirk ticket create [--input PATH] [--output-dir DIR]

Exit codes:
  0  Success — tickets created/updated for all findings.
  1  Usage error — no subcommand or required config missing.
  2  Total failure — no findings processed (bad config, missing file, missing extra).
  3  Partial failure — some findings ticketed, some failed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from quirk.ticketing.config import load_ticketing_config
from quirk.util.optional_extra import is_extra_available
from quirk.util.safe_exc import safe_str
```

**Findings file discovery** (from `quirk/cli/export_cmd.py` lines 35–40):
```python
def _find_latest_findings(output_dir: str) -> str | None:
    """Return the path to the newest findings-*.json in *output_dir*, or None."""
    candidates = list(Path(output_dir).glob("findings-*.json"))
    if not candidates:
        return None
    return str(max(candidates, key=lambda p: p.stat().st_mtime))
```

**`run_ticket(argv)` entry point pattern** (from `quirk/cli/export_cmd.py` `run_export` lines 48–166,
adapted):
```python
def run_ticket(argv: list[str]) -> None:
    """quirk ticket entry point. argv is sys.argv[2:] (after the subcommand name)."""
    parser = argparse.ArgumentParser(prog="quirk ticket", ...)
    parser.add_argument("action", choices=["create"], ...)
    parser.add_argument("--input", default=None, metavar="PATH", ...)
    parser.add_argument("--output-dir", default="output", metavar="DIR", ...)
    args = parser.parse_args(argv)

    # ISEC-04: advisory + graceful skip if [tickets] not installed
    if not is_extra_available("tickets"):
        print(
            "ERROR: Jira ticketing skipped — run `pip install quirk[tickets]` to enable.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Resolve findings file (mirrors export_cmd.py lines 101–112)
    if args.input:
        findings_path = args.input
    else:
        findings_path = _find_latest_findings(args.output_dir)

    if not findings_path or not Path(findings_path).exists():
        print("ERROR: no findings file found. Run a scan first, or pass --input <path>.",
              file=sys.stderr)
        sys.exit(2)

    try:
        with open(findings_path, encoding="utf-8") as f:
            findings = json.load(f)
    except Exception as exc:
        print(f"ERROR: could not read findings file: {safe_str(exc)}", file=sys.stderr)
        sys.exit(2)

    if not isinstance(findings, list):
        print(f"ERROR: findings file does not contain a list — got {type(findings).__name__}",
              file=sys.stderr)
        sys.exit(2)

    # Load ticketing config + acquire DB session (mirrors export_cmd.py lines 128–165)
    cfg = load_ticketing_config()
    if cfg is None or cfg.jira is None:
        print("ERROR: ticketing config not found. Set QUIRK_CONFIG_PATH.", file=sys.stderr)
        sys.exit(2)

    try:
        from quirk.db import get_session
        import os
        from quirk.ticketing.jira import JiraChannel

        db_path = os.environ.get("QUIRK_DB_PATH") or "quirk.db"
        scan_id = Path(findings_path).name
        channel = JiraChannel(cfg.jira)

        with get_session(db_path) as db:
            for finding in findings:
                channel.dispatch_finding(finding, db, scan_id=scan_id)

        print(f"Ticket run complete: {len(findings)} finding(s) processed.")
    except SystemExit:
        raise
    except Exception as exc:
        print(f"ERROR: ticket command failed: {safe_str(exc)}", file=sys.stderr)
        sys.exit(2)
```

---

### `run_scan.py` (modify — add ticket interception)

**Analog:** `run_scan.py` lines 496–500 (the export block, the freshest interception pattern).

**Exact pattern to copy and adapt** (from `run_scan.py` lines 496–500):
```python
    # --- export subcommand: intercept before scan argparse (Phase 103 SIEM-01/02) ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "export":
        from quirk.cli.export_cmd import run_export
        run_export(_sys.argv[2:])
        return
```

**New block to add immediately after the export block** (~line 500):
```python
    # --- ticket subcommand: intercept before scan argparse (Phase 104 TICKET-01) ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "ticket":
        from quirk.cli.ticket_cmd import run_ticket
        run_ticket(_sys.argv[2:])
        return
```

**Note:** Use `return` (not `_sys.exit(0)`) to match the existing `token` and `export` pattern at
lines 494 and 500. The `_run_main_with_job_guard` wrapper handles exit codes.

---

### `pyproject.toml` (modify — add `[tickets]` extra + join `[all]`)

**Analog:** `pyproject.toml` lines 87–105 (`[notify]` entry + `[all]` block).

**Addition to `[project.optional-dependencies]`** (after the `notify` block at line 91):
```toml
tickets = [
    "jira>=3.10.5",  # Phase 104 TICKET-01 — Jira issue creation; Cloud/Server auth
]
```

**Addition to `[all]` list** (after the `quirk-scanner[notify]` line at line 104):
```toml
    "quirk-scanner[tickets]",   # Phase 104 TICKET-01 — jira>=3.10.5; no cryptography downgrade
```

**Note:** The INTENTIONAL EXCLUSION comment for `[identity]` (lines 106–109) must be preserved
unchanged. The `tickets` extra has no cryptography downgrade chain (jira 3.10.5 depends on
requests, not pyOpenSSL).

---

### `quirk/util/optional_extra.py` (modify — add tickets to REGISTRY)

**Analog:** `quirk/util/optional_extra.py` lines 79–148 — any existing `OptionalExtra` entry.

**New REGISTRY entry to append** (after the `cbom` entry at line 148):
```python
    OptionalExtra(
        extra="tickets",
        modules=("jira",),
        scanner_label="jira_ticketing",
        install_hint=(
            "Jira ticketing skipped — run `pip install quirk[tickets]` to enable"
        ),
        enabled_attrs=(),  # always probe — CLI command, not gated by enable_* flag
    ),
```

**`enabled_attrs=()` rationale:** Mirrors the `dashboard` and `cbom` entries (lines 109–121 and
136–148). Ticketing is a CLI-invoked command, not a scan-time flag — no `cfg.connectors.enable_*`
attribute gates it. `probe_missing_extras` will emit an advisory if `jira` is not installed.

---

### `tests/test_install_all_includes_tickets.py` (CI guard, slow)

**Primary analog:** `tests/test_install_all_includes_notify.py` (all lines 1–117) — exact mirror.

**Module docstring pattern** (from `tests/test_install_all_includes_notify.py` lines 1–21):
```python
"""Inclusion guard: ``pip install quirk[all]`` MUST pull jira.

Phase 104 / TICKET-01 rationale
---------------------------------
``jira>=3.10.5`` is the Jira delivery backend. It is included in ``quirk[tickets]``
which is in turn bundled into ``quirk[all]``. jira has no cryptography downgrade
chain (slopcheck [OK], official pycontribs/jira, production-stable since 2011).

Marked ``@pytest.mark.slow`` because the resolver round-trip is several seconds.
"""
```

**Test function pattern** (from `tests/test_install_all_includes_notify.py` lines 35–116):
```python
@pytest.mark.slow
def test_install_all_includes_tickets(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    cmd = [sys.executable, "-m", "pip", "install", "--dry-run",
           "--ignore-installed", "--quiet", "--report", str(report_path),
           "-e", f"{REPO_ROOT}[all]"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

    assert result.returncode == 0, (
        "pip install --dry-run -e <repo>[all] FAILED. "
        "Phase 104 / TICKET-01: the [all] meta-extra must resolve cleanly. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )

    combined_output = (result.stdout or "") + (result.stderr or "")
    assert "does not provide the extra 'all'" not in combined_output
    assert "does not provide the extra 'tickets'" not in combined_output, (
        "pyproject.toml does not define the [tickets] extra. "
        "Phase 104 / TICKET-01: add tickets = [\"jira>=3.10.5\"] to "
        "[project.optional-dependencies]."
    )

    report = json.loads(report_path.read_text())
    installed = {
        item["metadata"]["name"].lower().replace("-", "_")
        for item in report.get("install", [])
        if item.get("metadata", {}).get("name")
    }

    assert "jira" in installed, (
        "REGRESSION: jira is NOT present in the resolved set for quirk[all]. "
        "Phase 104 / TICKET-01: quirk[tickets] must be included in the [all] "
        "meta-extra in pyproject.toml. "
        f"Resolved packages: {sorted(installed)}"
    )
```

---

### `tests/test_ticketing_base.py` (unit tests for ABC)

**Test pattern:** `pytest` unit tests with `unittest.mock` for the DB session. No analog test exists
in the codebase for an ABC, but the following structure is drawn from existing SIEM/notify test
patterns.

**Key test cases to cover:**
1. `test_fingerprint_stable` — same input dict → same 64-char hex output on repeated calls
2. `test_fingerprint_formula` — `SHA256(f"{host}:{port}::{title}")` verified against known input
3. `test_fingerprint_missing_fields` — finding dict with no keys → does not raise; uses empty strings
4. `test_build_ticket_evidence` — returns a non-empty string containing title, severity, host, port
5. `test_dispatch_finding_creates_issue` — first call with mock subclass → `create_issue_from_finding` called once
6. `test_dispatch_finding_dedup` — second call with same fingerprint → `add_rediscovery_comment` called, `create_issue_from_finding` not called again
7. `test_audit_row_finding_hash` — `IntegrationDelivery.finding_hash` equals `compute_fingerprint(finding)` in the row committed to DB
8. `test_audit_row_on_delivery_failure` — when `create_issue_from_finding` raises, row is committed with `status="failed"` and `error_summary` set to `safe_str(exc)`

**Concrete helper for a stub subclass (avoids abstractmethod instantiation error):**
```python
class _StubChannel(TicketingChannel):
    destination = "stub"
    def __init__(self):
        self.created = []
        self.commented = []
        self._next_fp = None  # set per test to control find_by_fingerprint return
    def find_by_fingerprint(self, fp): return self._next_fp
    def create_issue_from_finding(self, finding, fp, evidence):
        self.created.append(fp); return "STUB-1"
    def add_rediscovery_comment(self, issue_key, fp):
        self.commented.append((issue_key, fp))
```

---

### `tests/test_ticketing_jira.py` (unit tests for JiraChannel)

**Key test cases:**
1. `test_create_issue_per_finding` — mock `JIRA` client; `create_issue` called once; returns issue key
2. `test_dedup_creates_once_then_comments` — first call: `create_issue` called; second call with same fp: `add_comment` called, `create_issue` NOT called again
3. `test_missing_extra_graceful_skip` — when `jira` import fails (monkeypatch `builtins.__import__`), `ImportError` raised with advisory message
4. `test_credentials_not_in_logs` — exception message containing fake token → `safe_str(exc)` result does NOT include the raw token string
5. `test_jql_project_key_quoted` — verify JQL string uses `project = "KEY"` (double-quoted) not unquoted

**Mock JIRA client pattern:**
```python
from unittest.mock import MagicMock, patch

@patch("quirk.ticketing.jira.JiraChannel.__init__.__globals__")  # use importlib mock instead
def test_create_issue_per_finding(monkeypatch):
    mock_jira_cls = MagicMock()
    mock_client = MagicMock()
    mock_jira_cls.return_value = mock_client
    mock_client.search_issues.return_value = []  # no existing issue
    mock_issue = MagicMock(); mock_issue.key = "SEC-1"
    mock_client.create_issue.return_value = mock_issue

    # Monkeypatch the lazy import inside __init__
    with patch.dict("sys.modules", {"jira": MagicMock(JIRA=mock_jira_cls)}):
        channel = JiraChannel(cfg)
        result = channel.create_issue_from_finding(finding, fp, evidence)
    assert result == "SEC-1"
    mock_client.create_issue.assert_called_once()
```

---

### `tests/test_ticket_cmd.py` (CLI end-to-end tests)

**Key test cases:**
1. `test_missing_extra_advisory` — when `is_extra_available("tickets")` returns False, exits with code 2 and advisory message
2. `test_no_findings_file` — when output dir has no `findings-*.json`, exits with code 2
3. `test_input_flag` — `--input <path>` reads the specified file instead of latest
4. `test_exit_0_all_dispatched` — happy path with mocked `JiraChannel.dispatch_finding`; exits 0
5. `test_missing_config` — when `load_ticketing_config()` returns None, exits 2

**CLI invocation pattern** (from `quirk/cli/export_cmd.py` test analogs):
```python
import sys
from unittest.mock import patch
from quirk.cli.ticket_cmd import run_ticket

def test_missing_extra_advisory(capsys):
    with patch("quirk.cli.ticket_cmd.is_extra_available", return_value=False):
        with pytest.raises(SystemExit) as exc_info:
            run_ticket(["create"])
        assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "pip install quirk[tickets]" in captured.err
```

---

## Shared Patterns

### Error Handling — `safe_str(exc)` Discipline
**Source:** `quirk/util/safe_exc.py::safe_str`
**Apply to:** ALL exception handlers in `base.py`, `jira.py`, `ticket_cmd.py`

```python
# CORRECT — from quirk/siem/dispatcher.py line 87 and quirk/notify/dispatcher.py line 215
error_summary = safe_str(exc)
logger.warning("Delivery failed [%s]: %s", self.destination, safe_str(exc))

# WRONG — never use these:
# str(exc)    — may contain Jira auth headers / credentials on connection errors
# repr(exc)   — same risk
```

### SSRF Validation — `validate_external_url`
**Source:** `quirk/util/url_allowlist.py::validate_external_url`
**Apply to:** `quirk/ticketing/jira.py` `__init__` (at construction, before any network call)

```python
# From quirk/notify/channels/slack.py lines 53–58
result = validate_external_url(url)
if not result.ok:
    raise ValueError(f"SSRF blocked ({result.reason}) for Jira URL")
```

**Note for self-hosted Jira:** `allow_internal` field in `JiraTicketingCfg` controls this. Cloud
deployments default to `allow_internal=False`. Pass `allow_internal=cfg.allow_internal` to
`validate_external_url` if the signature supports it; otherwise gate the SSRF check on `auth_mode`.

### Credential Isolation — env-var-NAME-only storage
**Source:** `quirk/notify/config.py` (NOTIFY-06 pattern)
**Apply to:** `quirk/ticketing/config.py`, `quirk/ticketing/jira.py`

```python
# CORRECT — store only the env var NAME in the config dataclass
jira_user_env: str = "QUIRK_JIRA_USER"   # NAME, not the value
jira_token_env: str = "QUIRK_JIRA_TOKEN" # NAME, not the value

# Resolve at delivery time inside jira.py __init__:
user = os.environ.get(cfg.jira_user_env, "")
token = os.environ.get(cfg.jira_token_env, "")

# WRONG — never store or log the actual credential value
```

### Optional-Extra Lazy Import — Shadow Trap Safe Pattern
**Source:** `quirk/notify/channels/slack.py` lines 60–64
**Apply to:** `quirk/ticketing/jira.py` `__init__`

```python
# CORRECT — inside __init__ body only, after all gates
try:
    from jira import JIRA  # noqa: PLC0415
except ImportError as exc:
    raise ImportError("...advisory...") from exc

# WRONG — never at module top level:
# from jira import JIRA   ← breaks minimal installs
```

### Audit Row Commit Pattern (WR-01)
**Source:** `quirk/notify/dispatcher.py` lines 262–269; `quirk/siem/dispatcher.py` lines 106–111
**Apply to:** `quirk/ticketing/base.py` `dispatch_finding`

```python
# Commit is OUTSIDE the delivery try/except — WR-01
db.add(row)
try:
    db.commit()
except Exception as exc:
    logger.warning("Ticket audit row commit failed: %s", safe_str(exc))
```

### Config Loader SQLite Guard
**Source:** `quirk/notify/config.py` lines 172–184; `quirk/siem/config.py` lines 83–95
**Apply to:** `quirk/ticketing/config.py` `load_ticketing_config`

```python
# Binary/malformed/SQLite DB files are silently ignored — never abort a scan
try:
    with open(effective_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    ...
except Exception:
    return None   # Pitfall: SQLite DB path guard — silently return None
```

### run_scan.py Interception — Return Pattern
**Source:** `run_scan.py` lines 490–500
**Apply to:** New `ticket` block in `run_scan.py`

```python
# Use `return` not `_sys.exit(0)` — matches token and export blocks at lines 494, 500
if len(_sys.argv) > 1 and _sys.argv[1] == "ticket":
    from quirk.cli.ticket_cmd import run_ticket
    run_ticket(_sys.argv[2:])
    return
```

---

## No Analog Found

All files have clear analogs in the codebase. No entries in this section.

---

## Metadata

**Analog search scope:** `quirk/notify/`, `quirk/siem/`, `quirk/cli/`, `quirk/util/`, `run_scan.py`,
`pyproject.toml`, `tests/`
**Files read:** 11 source files
**Pattern extraction date:** 2026-05-25

**Critical gotchas captured:**
1. Fingerprint formula is `SHA256(host:port::title)` — NOT `SHA256(host:port:protocol:category)`;
   real findings JSON has no `protocol`/`category` keys (verified against real output).
2. `find_by_fingerprint` must return `Optional[str]`, never a Jira-typed object (Phase 105 compat).
3. `from jira import JIRA` must NEVER appear at module top level — lazy inside `__init__` only.
4. `compute_fingerprint` is a `@staticmethod` in base.py — must not be overridden in subclasses.
5. Audit row commit is outside the delivery try/except (WR-01).
6. JQL project key must be double-quoted: `project = "KEY"` not `project = KEY`.
7. `run_scan.py` interception uses `return`, not `_sys.exit(0)`.
