"""quirk.ticketing.config — TicketingCfg dataclasses + config loader (Phase 104 TICKET-01).

Mirrors quirk/notify/config.py and quirk/siem/config.py patterns exactly.

Config failure MUST NEVER abort a running scan. All exceptions silently return None.
"""
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
    """Top-level ticketing config container."""

    jira: Optional[JiraTicketingCfg] = None


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
    return TicketingCfg(jira=_parse_jira_cfg(jira_raw))


def _parse_jira_cfg(raw: dict) -> Optional[JiraTicketingCfg]:
    """Parse the jira sub-block dict into a JiraTicketingCfg. Returns None if missing."""
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
