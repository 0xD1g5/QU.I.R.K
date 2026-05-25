"""quirk.ticketing.servicenow — ServiceNow ticketing backend (Phase 105 TICKET-02/TICKET-04).

Security controls:
  ISEC-01: validate_external_url() called at construction time, before any connection.
  ISEC-02: safe_str(exc) on all exception surfaces — never str(exc) or repr(exc).
  T-105-01: self._auth_header is NEVER logged — safe_str scrubs it if it leaks in exc.
  T-105-02: _parse_servicenow_cfg rejects http:// instance_url at parse time (returns None).
  T-105-03: validate_external_url blocks RFC1918/loopback/metadata IPs at __init__.
  T-105-04: _NoRedirectHandler copied verbatim from webhook.py blocks post-validation redirects.

Phase 105 adds this file only — zero changes to base.py or jira.py (TICKET-04).
"""
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


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Block all HTTP redirects to prevent post-validation SSRF bypass.

    Copied verbatim from quirk/notify/channels/webhook.py (T-105-04).
    urllib.request.urlopen follows 3xx redirects by default via HTTPRedirectHandler.
    An attacker-controlled endpoint returning 302 → http://169.254.169.254/... would
    bypass the validate_external_url() pre-connection check. This handler refuses
    any redirect by raising HTTPError, keeping the connection to the validated URL.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url, code, "Redirect blocked (SSRF guard)", headers, fp
        )


class ServiceNowChannel(TicketingChannel):
    """ServiceNow ticketing backend (TICKET-02, TICKET-04).

    Implements the three abstract methods from TicketingChannel:
      - find_by_fingerprint(fp): GET /api/now/table/{table}?sysparm_query=correlation_id=<fp>
      - create_issue_from_finding(finding, fp, evidence): POST to create incident, return sys_id
      - add_rediscovery_comment(sys_id, fp): PATCH work_notes journal entry

    All shared logic (fingerprint, evidence build, dedup orchestration, audit)
    lives in the base class — this subclass only wraps the ServiceNow Table API calls.

    Phase 105 adds this file only — zero changes to base.py or jira.py (TICKET-04).
    """

    destination = "servicenow"

    def __init__(self, cfg: "ServiceNowTicketingCfg") -> None:  # type: ignore[name-defined]
        """Construct ServiceNowChannel. Raises ValueError if SSRF validation fails.

        Args:
            cfg: ServiceNowTicketingCfg — instance_url validated here; user_env/password_env
                 are env-var NAMES resolved to values and stored only in self._auth_header.

        Raises:
            ValueError: When cfg.instance_url fails SSRF validation (ISEC-01/T-105-03).
        """
        # SSRF guard at construction time, before any connection (ISEC-01 / T-105-03)
        result = validate_external_url(cfg.instance_url, allow_internal=cfg.allow_internal)
        if not result.ok:
            raise ValueError(
                f"SSRF blocked ({result.reason}) for ServiceNow URL"
            )

        self._cfg = cfg

        # Resolve credentials at construction time — env-var NAMES in cfg, not values.
        # Mirrors jira.py lines 72-73 pattern.
        user = os.environ.get(cfg.user_env, "")
        password = os.environ.get(cfg.password_env, "")
        creds = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        self._auth_header = f"Basic {creds}"
        # self._auth_header is NEVER logged — safe_str scrubs it if it leaks in exc (T-105-01)

    def find_by_fingerprint(self, fp: str) -> Optional[str]:
        """Search ServiceNow for an incident with the given correlation_id fingerprint.

        GET /api/now/table/{table}?sysparm_query=correlation_id=<fp>&sysparm_limit=1

        Args:
            fp: SHA256 hex fingerprint (64-char [0-9a-f]) — inherited from base.

        Returns:
            sys_id string (32-char hex) if found, None otherwise.
        """
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

    def create_issue_from_finding(self, finding: dict, fp: str, evidence: str) -> str:
        """Create a ServiceNow incident carrying QRAMM evidence and the correlation_id.

        POST /api/now/table/{table} with short_description, description, correlation_id.
        Returns the sys_id (NOT the human-readable INC-number) — required for PATCH dedup
        (Pitfall 2: PATCH 404s when using INC-number as URL path variable).

        Args:
            finding: Raw finding dict from findings-*.json.
            fp: SHA256 hex fingerprint — stored as correlation_id for dedup (TICKET-03).
            evidence: Pre-built evidence string from build_ticket_evidence().

        Returns:
            sys_id string (32-char hex) — NOT the INC-number.
        """
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
            return data["result"]["sys_id"]  # 32-char hex — NOT INC-number (Pitfall 2)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"ServiceNow POST failed: HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("ServiceNow POST failed: connection error") from exc

    def add_rediscovery_comment(self, issue_key: str, fp: str) -> None:
        """Append a rediscovery work_notes journal entry to an existing ServiceNow incident.

        PATCH /api/now/table/{table}/{sys_id} with {"work_notes": "..."}.
        Must use PATCH (not POST or PUT) — POST/PUT do not append work_notes visibly
        in the ServiceNow task UI (KB0623936 — Pitfall 1).

        Args:
            issue_key: sys_id returned by create_issue_from_finding (32-char hex).
            fp: SHA256 hex fingerprint for audit traceability.
        """
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
            method="PATCH",  # MUST be PATCH — POST/PUT do not append work_notes visibly (KB0623936)
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
