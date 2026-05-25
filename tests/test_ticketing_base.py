"""Unit tests for quirk.ticketing.base — TicketingChannel ABC contract (Phase 104 TICKET-03/04).

Covers:
  - Fingerprint formula: SHA256(host:port::title), stable + formula-pinned
  - Fingerprint missing fields: no raise, deterministic output
  - Evidence build: whitelist enforced (check_id NOT included)
  - dispatch_finding: create path (find returns None)
  - dispatch_finding: dedup path (find returns existing key)
  - Audit row: finding_hash equals compute_fingerprint(finding), destination correct
  - Failure isolation: dispatch never raises; status=failed; safe_str scrubs token
"""
from __future__ import annotations

import hashlib
from typing import Optional

import pytest

from quirk.db import init_db, get_session
from quirk.models import IntegrationDelivery
from quirk.ticketing.base import TicketingChannel


# ---------------------------------------------------------------------------
# Stub subclass — implements only the 3 abstract methods
# ---------------------------------------------------------------------------


class _StubChannel(TicketingChannel):
    """Minimal concrete subclass to satisfy the ABC contract in tests."""

    destination = "stub"

    def __init__(self, next_fp: Optional[str] = None) -> None:
        self.created: list[str] = []        # fingerprints passed to create
        self.commented: list[tuple[str, str]] = []  # (issue_key, fp) pairs
        self._next_fp = next_fp             # return value of find_by_fingerprint

    def find_by_fingerprint(self, fp: str) -> Optional[str]:
        return self._next_fp

    def create_issue_from_finding(self, finding: dict, fp: str, evidence: str) -> str:
        self.created.append(fp)
        return "STUB-1"

    def add_rediscovery_comment(self, issue_key: str, fp: str) -> None:
        self.commented.append((issue_key, fp))


class _RaisingChannel(_StubChannel):
    """Stub that always raises from create_issue_from_finding.

    The exception message embeds an Authorization header value — this is
    what the jira library leaks on auth failure. safe_str must scrub it.
    """

    def create_issue_from_finding(self, finding: dict, fp: str, evidence: str) -> str:
        # Simulate jira library leaking an auth header in the exception message
        raise RuntimeError(
            "Jira auth failed: Authorization: Bearer FAKE_JIRA_TOKEN_abc123xyz"
        )


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _make_db(tmp_path):
    db_path = str(tmp_path / "quirk_test.db")
    init_db(db_path)
    return db_path


# ---------------------------------------------------------------------------
# Fingerprint tests
# ---------------------------------------------------------------------------


def test_fingerprint_stable():
    """Same finding dict returns identical 64-char hex on repeated calls."""
    finding = {"host": "h", "port": 443, "title": "Some Title"}
    fp1 = TicketingChannel.compute_fingerprint(finding)
    fp2 = TicketingChannel.compute_fingerprint(finding)
    assert fp1 == fp2
    assert len(fp1) == 64
    assert all(c in "0123456789abcdef" for c in fp1)


def test_fingerprint_formula():
    """Fingerprint matches SHA256(host:port::title) exactly — formula locked (TICKET-03)."""
    finding = {"host": "h", "port": 443, "title": "Some Title"}
    expected = hashlib.sha256(b"h:443::Some Title").hexdigest()
    assert TicketingChannel.compute_fingerprint(finding) == expected


def test_fingerprint_missing_fields():
    """Empty finding dict does not raise; returns deterministic hex for empty strings."""
    fp = TicketingChannel.compute_fingerprint({})
    # Formula: f"{host}:{port}::{title}" with all empty = ":::" (3 chars)
    expected = hashlib.sha256(b":::").hexdigest()
    assert fp == expected
    assert len(fp) == 64


# ---------------------------------------------------------------------------
# Evidence build tests
# ---------------------------------------------------------------------------


def test_build_ticket_evidence():
    """Evidence string contains whitelisted fields; check_id is excluded."""
    finding = {
        "title": "Legacy TLS cipher suites accepted",
        "severity": "HIGH",
        "host": "10.0.0.1",
        "port": 443,
        "description": "Server accepts weak ciphers.",
        "recommendation": "Disable RC4 and DES.",
        "check_id": "TLS-WEAK-001",    # must NOT appear in evidence
        "quantum_risk": "Vulnerable to Grover's algorithm.",
    }
    evidence = TicketingChannel.build_ticket_evidence(finding)
    # Required whitelisted fields
    assert "Legacy TLS cipher suites accepted" in evidence
    assert "HIGH" in evidence
    assert "10.0.0.1" in evidence
    assert "443" in evidence
    assert "Disable RC4 and DES." in evidence
    assert "Vulnerable to Grover's algorithm." in evidence
    # Exfiltration: check_id must NOT appear
    assert "TLS-WEAK-001" not in evidence
    assert len(evidence) > 0


# ---------------------------------------------------------------------------
# dispatch_finding path tests
# ---------------------------------------------------------------------------


def test_dispatch_creates_issue(tmp_path):
    """When find returns None, create_issue_from_finding is called once."""
    db_path = _make_db(tmp_path)
    channel = _StubChannel(next_fp=None)
    finding = {"host": "a.example.com", "port": 443, "title": "Weak Cipher"}

    with get_session(db_path) as db:
        channel.dispatch_finding(finding, db, scan_id="findings-test.json")

    assert len(channel.created) == 1
    assert len(channel.commented) == 0


def test_dispatch_dedup(tmp_path):
    """When find returns an existing key, add_rediscovery_comment is called; create is NOT called."""
    db_path = _make_db(tmp_path)
    channel = _StubChannel(next_fp="STUB-1")
    finding = {"host": "a.example.com", "port": 443, "title": "Weak Cipher"}

    with get_session(db_path) as db:
        channel.dispatch_finding(finding, db, scan_id="findings-test.json")

    assert len(channel.created) == 0
    assert len(channel.commented) == 1
    assert channel.commented[0][0] == "STUB-1"  # issue_key passed correctly


def test_audit_row_finding_hash(tmp_path):
    """After dispatch, the committed IntegrationDelivery row has finding_hash == compute_fingerprint and destination == 'stub'."""
    db_path = _make_db(tmp_path)
    channel = _StubChannel(next_fp=None)
    finding = {"host": "b.example.com", "port": 8443, "title": "Expired Certificate"}

    with get_session(db_path) as db:
        channel.dispatch_finding(finding, db, scan_id="findings-audit.json")

    expected_fp = TicketingChannel.compute_fingerprint(finding)
    with get_session(db_path) as db:
        rows = db.query(IntegrationDelivery).all()
    assert len(rows) == 1
    assert rows[0].finding_hash == expected_fp
    assert rows[0].destination == "stub"
    assert rows[0].status == "ok"
    assert rows[0].scan_id == "findings-audit.json"


def test_dispatch_failure_isolation(tmp_path):
    """dispatch_finding never raises even when create raises; row committed with status=failed; token scrubbed."""
    db_path = _make_db(tmp_path)
    channel = _RaisingChannel(next_fp=None)
    finding = {"host": "c.example.com", "port": 22, "title": "Weak SSH Key"}

    # Must NOT raise
    with get_session(db_path) as db:
        channel.dispatch_finding(finding, db, scan_id="findings-fail.json")

    with get_session(db_path) as db:
        rows = db.query(IntegrationDelivery).all()
    assert len(rows) == 1
    assert rows[0].status == "failed"
    assert rows[0].error_summary is not None
    # safe_str must have scrubbed the planted Authorization header token (ISEC-02)
    assert "FAKE_JIRA_TOKEN_abc123xyz" not in (rows[0].error_summary or "")
