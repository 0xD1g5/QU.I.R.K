"""quirk.ticketing.config — TicketingCfg dataclasses + config loader (Phase 104 TICKET-01).

Mirrors quirk/notify/config.py and quirk/siem/config.py patterns exactly.

Config failure MUST NEVER abort a running scan. All exceptions silently return None.
"""
from __future__ import annotations

import os
import re as _re
from dataclasses import dataclass
from typing import Optional

import yaml

# Jira project keys: uppercase letter followed by 1-99 uppercase letters/digits.
# Validates at config parse time to prevent JQL injection via project_key (CR-01).
_PROJECT_KEY_RE = _re.compile(r"^[A-Z][A-Z0-9]{1,99}$")

# Allowed auth_mode values — any other value is a misconfiguration (WR-02).
_VALID_AUTH_MODES = frozenset({"cloud", "server"})


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
class ServiceNowTicketingCfg:
    """ServiceNow ticketing configuration (TICKET-02).

    instance_url  — ServiceNow instance URL (MUST be https://)
    user_env      — NAME of env var holding ServiceNow username (not the value)
    password_env  — NAME of env var holding ServiceNow password/token (not the value)
    table         — Table to create incidents in (default: "incident")
    allow_internal — False for external instances; True for internal test instances
    """

    instance_url: str         # e.g. https://myco.service-now.com — MUST be https://
    user_env: str             # env-var NAME, not the credential value
    password_env: str         # env-var NAME, not the credential value
    table: str = "incident"   # default table — locked by CONTEXT.md
    allow_internal: bool = False


@dataclass
class TicketingCfg:
    """Top-level ticketing config container."""

    jira: Optional[JiraTicketingCfg] = None
    servicenow: Optional[ServiceNowTicketingCfg] = None


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


def _parse_ticketing_cfg(raw: dict) -> TicketingCfg:
    """Parse the ticketing block dict into a TicketingCfg."""
    jira_raw = raw.get("jira") or {}
    servicenow_raw = raw.get("servicenow") or {}
    return TicketingCfg(
        jira=_parse_jira_cfg(jira_raw),
        servicenow=_parse_servicenow_cfg(servicenow_raw),
    )


def _parse_jira_cfg(raw: dict) -> Optional[JiraTicketingCfg]:
    """Parse the jira sub-block dict into a JiraTicketingCfg. Returns None if missing or invalid.

    Validation guards (treat any failure as misconfigured — same path as missing jira_url):
      - project_key must match ^[A-Z][A-Z0-9]{1,99}$ to prevent JQL injection (CR-01/WR-01).
      - auth_mode must be "cloud" or "server"; unknown values are rejected (WR-02).
    """
    if not raw:
        return None
    jira_url = raw.get("jira_url")
    if not jira_url:
        return None
    project_key = str(raw.get("project_key", ""))
    if not _PROJECT_KEY_RE.match(project_key):
        # Empty string, lowercase, or injection chars (e.g. ") fail the regex.
        return None
    auth_mode = str(raw.get("auth_mode", "cloud")).lower()
    if auth_mode not in _VALID_AUTH_MODES:
        return None
    return JiraTicketingCfg(
        jira_url=str(jira_url),
        jira_user_env=str(raw.get("jira_user_env", "")),
        jira_token_env=str(raw.get("jira_token_env", "")),
        project_key=project_key,
        issue_type=str(raw.get("issue_type", "Bug")),
        auth_mode=auth_mode,
        allow_internal=bool(raw.get("allow_internal", False)),
    )


def _parse_servicenow_cfg(raw: dict) -> Optional[ServiceNowTicketingCfg]:
    """Parse the servicenow sub-block dict into a ServiceNowTicketingCfg.

    Returns None if missing or invalid.

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
