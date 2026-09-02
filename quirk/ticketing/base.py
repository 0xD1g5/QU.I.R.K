"""quirk.ticketing.base — TicketingChannel ABC + shared orchestration (Phase 104 TICKET-04).

This module is the integration seam that:
  1. Computes the stable fingerprint SHA256(host:port::title) for each finding.
  2. Builds QRAMM evidence text for ticket descriptions.
  3. Orchestrates dedup: find_by_fingerprint -> add_rediscovery_comment or create_issue.
  4. Writes one IntegrationDelivery audit row per finding attempt.

CRITICAL CONSTRAINTS:
  - dispatch_finding MUST NOT raise into callers — failure isolation is absolute.
  - error_summary is ALWAYS safe_str(exc) — never str(exc) or repr(exc) (ISEC-02).
  - Fingerprint formula: SHA256(f"{host}:{port}::{normalize_finding_title(title,
    FINGERPRINT_TITLE_ALIASES)}") — NEVER override compute_fingerprint in
    subclasses (shared contract with Phase 105 ServiceNow). Phase 178 IDENT-01
    added the normalization step; see compute_fingerprint's own docstring for
    the full rationale and the one-time re-key consequence.
  - find_by_fingerprint returns Optional[str] (string key/sys_id), NEVER a Jira
    Issue object — Phase 105 ServiceNow returns a sys_id string, not a Jira type.
  - Credentials MUST NOT appear in logs or error_summary — always safe_str(exc).
"""
from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from quirk.compliance import FINGERPRINT_TITLE_ALIASES, normalize_finding_title
from quirk.models import IntegrationDelivery
from quirk.util.safe_exc import safe_str

logger = logging.getLogger(__name__)


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

    # ------------------------------------------------------------------ #
    # Shared: fingerprint, evidence, dispatch, audit                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def compute_fingerprint(finding: dict) -> str:
        """SHA256(host:port::normalize_finding_title(title)) hex.

        Formula: ``SHA256(f"{host}:{port}::{title}")`` where ``title`` is
        first passed through ``quirk.compliance.normalize_finding_title``
        using the ``FINGERPRINT_TITLE_ALIASES`` IDENTITY policy table (Phase
        178 IDENT-01). This is NOT the same table used for compliance
        framework mapping (``TITLE_PREFIX_ALIASES``) — the two policies are
        declared separately because they disagree on purpose: compliance
        mapping collapses the two `({name}@{version})` container-library
        titles down to a class, while fingerprinting must NOT, because
        `{name}` is a discriminator between genuinely different findings at
        the same host:port (T-178-01). See
        ``quirk.compliance.FINGERPRINT_TITLE_ALIASES`` for the full policy
        and rationale.

        NOTE: findings-*.json has NO 'protocol' or 'category' keys (verified
        against real output). Formula uses title as category proxy, empty
        protocol. Produces 64-char hex safe as a Jira label.
        Phase 105 inherits this staticmethod — NEVER override in subclasses.

        ONE-TIME RE-KEY: prior to Phase 178, this formula hashed the RAW
        title, so any already-issued ticket for a title that now normalizes
        differently (in practice, only the "Certificate expiring in {N}
        day(s)" family — the only title whose classification changed) will
        no longer match its old fingerprint. On the next scan/dispatch
        cycle, the dedup lookup for that finding misses exactly ONCE:
        Jira's ``find_by_fingerprint`` (quirk/ticketing/jira.py) matches on
        the fingerprint stored as an issue **label** (``labels: [fp]``,
        queried via ``JQL labels = "<fp>"``), and ServiceNow's
        (quirk/ticketing/servicenow.py) matches on the fingerprint stored in
        the **``correlation_id``** field (queried via
        ``sysparm_query=correlation_id=<fp>``) — neither lookup will find
        the old-fingerprint record, so one duplicate ticket is created.
        After that one miss, the new fingerprint is stable and dedup works
        normally. No migration of already-issued tickets is performed;
        tracker readback/migration is explicitly out of scope per
        REQUIREMENTS.md. Only the cert-expiry family is affected — it is
        the only title whose fingerprint-relevant classification changed in
        Phase 178.
        """
        host = str(finding.get("host") or "")
        port = str(finding.get("port") or "")
        title = normalize_finding_title(
            str(finding.get("title") or ""), FINGERPRINT_TITLE_ALIASES
        )
        raw = f"{host}:{port}::{title}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def build_ticket_evidence(finding: dict) -> str:
        """Build evidence string for ticket description (exfiltration whitelist).

        Sources ONLY from whitelisted finding fields:
          title, severity, host, port, description, recommendation, quantum_risk

        NEVER includes: compliance, check_id, raw cert/PEM material.
        Returns a multi-line string for use as the ticket description body.
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

    def dispatch_finding(self, finding: dict, db, scan_id: str) -> None:
        """Orchestrate dedup + create/update + audit for one finding.

        Never raises — all failures captured in audit row (NOTIFY-07 pattern).
        Commit is always outside the try block (WR-01): the row is committed
        even on delivery failure so the audit record is never lost.

        Commit-deferral note (WR-04): db.commit() is called once per row.
        If that commit fails (e.g. disk full), the row remains in the session
        and will be committed by the next successful per-row commit or by the
        get_session exit commit. If ALL per-row commits fail and the exit commit
        also fails, get_session rolls back all rows and re-raises; ticket_cmd.py
        catches this with a descriptive "audit-row persistence failed" message.
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
            error_summary = safe_str(exc)  # NEVER str(exc) — may contain credentials
            logger.warning(
                "Ticket delivery failed [%s] finding=%r: %s",
                self.destination,
                finding.get("title", ""),
                error_summary,
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
