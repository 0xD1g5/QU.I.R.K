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
from __future__ import annotations

import logging
import os
from typing import Optional

from quirk.ticketing.base import TicketingChannel
from quirk.util.safe_exc import safe_str  # noqa: F401 — imported for subclass-context use
from quirk.util.url_allowlist import validate_external_url

logger = logging.getLogger(__name__)


class JiraChannel(TicketingChannel):
    """Jira ticketing backend (TICKET-01, TICKET-03).

    Implements the three abstract methods from TicketingChannel:
      - find_by_fingerprint(fp): JQL label search for existing issue.
      - create_issue_from_finding(finding, fp, evidence): create one Jira issue.
      - add_rediscovery_comment(issue_key, fp): append a rediscovery note.

    All shared logic (fingerprint, evidence build, dedup orchestration, audit)
    lives in the base class — this subclass only wraps the Jira REST API calls.

    Phase 105 ServiceNow adds servicenow.py only — zero changes to this file.
    """

    destination = "jira"

    def __init__(self, cfg: "JiraTicketingCfg") -> None:  # type: ignore[name-defined]
        """Construct JIRA client. Raises ImportError with advisory if jira missing.

        Args:
            cfg: JiraTicketingCfg — all fields are env-var NAMES, not credential values.

        Raises:
            ImportError: When jira package is not installed (advisory message included).
            ValueError: When cfg.jira_url fails SSRF validation (ISEC-01).
        """
        # Lazy import — NEVER at module scope (optional-extra import trap).
        # noqa: PLC0415 — intentional local import for optional-extra safety.
        try:
            from jira import JIRA  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "Jira ticketing skipped — run `pip install quirk[tickets]` to enable"
            ) from exc

        # SSRF guard at construction time, before any connection (ISEC-01).
        result = validate_external_url(cfg.jira_url, allow_internal=cfg.allow_internal)
        if not result.ok:
            raise ValueError(
                f"SSRF blocked ({result.reason}) for Jira URL"
            )

        self._cfg = cfg

        # Resolve credentials from env vars at connection time — NEVER from config
        # (credentials are env-var NAMES stored in cfg, not the values themselves).
        user = os.environ.get(cfg.jira_user_env, "")
        token = os.environ.get(cfg.jira_token_env, "")

        if cfg.auth_mode == "cloud":
            # Cloud: basic_auth=(email, api_token) tuple
            # [VERIFIED: jira.readthedocs.io/examples.html]
            self._client = JIRA(server=cfg.jira_url, basic_auth=(user, token))
        else:
            # Self-hosted >= 8.14: token_auth=PAT string
            # [VERIFIED: jira.readthedocs.io/examples.html]
            self._client = JIRA(server=cfg.jira_url, token_auth=token)

    def find_by_fingerprint(self, fp: str) -> Optional[str]:
        """JQL label search for an existing issue with the given fingerprint.

        fp is always 64-char hex [0-9a-f] — no JQL injection possible.
        Project key is double-quoted to handle multi-word or numeric-start keys
        (Pitfall 4: unquoted project key breaks JQL for non-trivial keys).

        Args:
            fp: SHA256 hex fingerprint (64 chars of [0-9a-f]).

        Returns:
            Issue key string (e.g. "SEC-42") if found, None otherwise.
        """
        jql = f'project = "{self._cfg.project_key}" AND labels = "{fp}"'
        issues = self._client.search_issues(jql, maxResults=1)
        if issues:
            return issues[0].key
        return None

    def create_issue_from_finding(
        self, finding: dict, fp: str, evidence: str
    ) -> str:
        """Create one Jira issue carrying QRAMM evidence in the description.

        The fingerprint is stored as a Jira label for dedup on subsequent scans
        (TICKET-03). Summary is truncated to 255 chars (Jira max).

        Args:
            finding: Raw finding dict from findings-*.json.
            fp: SHA256 hex fingerprint (64-char hex, also stored as label).
            evidence: Pre-built evidence string from build_ticket_evidence().

        Returns:
            Issue key string (e.g. "SEC-42").
        """
        fields = {
            "project": {"key": self._cfg.project_key},
            "issuetype": {"name": self._cfg.issue_type},
            "summary": str(finding.get("title", "QUIRK Finding"))[:255],
            "description": evidence,
            "labels": [fp],
        }
        issue = self._client.create_issue(fields=fields)
        return issue.key

    def add_rediscovery_comment(self, issue_key: str, fp: str) -> None:
        """Append a rediscovery note to an existing Jira issue.

        Called on the second (and subsequent) scan runs when find_by_fingerprint
        returns an existing issue key — prevents duplicate issue creation (TICKET-03).

        Args:
            issue_key: Jira issue key (e.g. "SEC-42").
            fp: SHA256 hex fingerprint for audit traceability.
        """
        body = (
            f"*Rediscovery*: QUIRK re-detected this finding on a subsequent scan.\n"
            f"Fingerprint: `{fp}`"
        )
        self._client.add_comment(issue_key, body)
