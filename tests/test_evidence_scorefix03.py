"""Phase 124 — SCOREFIX-03 RED scaffold.

Pins the post-fix behavior for evidence.py::build_evidence_summary key-type tally:
  - Ed25519 cert_pubkey_alg → ECDSA (or EdDSA) count > 0 (currently 0 → RED).
  - Ed448 cert_pubkey_alg → ECDSA count > 0 (currently 0 → RED).
  - EdDSA cert_pubkey_alg → ECDSA count > 0 (currently 0 → RED).

Current evidence.py:167-170 only matches "RSA" and ("EC", "ECDSA") prefixes.
"ED25519", "ED448", "EDDSA" (uppercased) fall through → no agility credit.
Wave 1 adds `elif key_alg.startswith(("ED25519", "ED448", "EDDSA"))` branch (D-04).
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any


from quirk.intelligence.evidence import build_evidence_summary


def _ep(cert_pubkey_alg: str) -> Any:
    """Minimal endpoint stub exposing the fields build_evidence_summary reads."""
    return SimpleNamespace(
        host="test.example",
        port=443,
        protocol="TLS",
        cert_pubkey_alg=cert_pubkey_alg,
        # Fields that build_evidence_summary reads but are not relevant here:
        service_detail=None,
        tls_supported_versions=None,
        scan_error=None,
        tls_blocker_reason=None,
        cert_not_after=None,
        cert_subject=None,
        cert_issuer=None,
        scanned_at=None,
        tls_version=None,
        cipher_suite=None,
        cert_sig_alg=None,
        cert_pubkey_size=None,
        ssh_audit_json=None,
        jwt_scan_json=None,
        container_scan_json=None,
        cloud_scan_json=None,
        kerberos_scan_json=None,
        saml_scan_json=None,
        sensor_id=None,
        segment=None,
        scan_id=None,
    )


def _ecdsa_count(summary: dict) -> int:
    """Extract ECDSA count from the returned cert_key_type_counts dict.

    Post-fix may fold EdDSA into ECDSA key (D-04, option A) OR add a sibling
    "EdDSA" key (D-04, option B). Either way the test passes when ECDSA > 0.
    """
    counts = summary.get("cert_key_type_counts", {})
    return counts.get("ECDSA", 0) + counts.get("EdDSA", 0)


# SF03a — Ed25519 receives ECDSA agility credit.
def test_ed25519_receives_ecdsa_credit():
    """Ed25519 cert_pubkey_alg must increment the ECDSA (or EdDSA) agility count.

    RED: current source matches ("EC", "ECDSA") but "ED25519" does not start
    with "EC" or "ECDSA" → count stays 0.
    """
    summary = build_evidence_summary([_ep("Ed25519")])
    ecdsa = _ecdsa_count(summary)
    assert ecdsa > 0, (
        f"Expected Ed25519 to receive ECDSA agility credit (count > 0), got {ecdsa}. "
        f"Full cert_key_type_counts: {summary.get('cert_key_type_counts')}"
    )


# SF03b — Ed448 receives ECDSA agility credit.
def test_ed448_receives_ecdsa_credit():
    """Ed448 cert_pubkey_alg must increment the ECDSA (or EdDSA) agility count.

    RED: "ED448" does not start with "EC" or "ECDSA" → falls through, count stays 0.
    """
    summary = build_evidence_summary([_ep("Ed448")])
    ecdsa = _ecdsa_count(summary)
    assert ecdsa > 0, (
        f"Expected Ed448 to receive ECDSA agility credit (count > 0), got {ecdsa}. "
        f"Full cert_key_type_counts: {summary.get('cert_key_type_counts')}"
    )


# SF03c — EdDSA (GCP connector string) receives ECDSA agility credit.
def test_eddsa_string_receives_ecdsa_credit():
    """EdDSA cert_pubkey_alg (as emitted by GCP connector) must receive agility credit.

    RED: "EDDSA" does not start with "EC" or "ECDSA" → falls through, count stays 0.
    """
    summary = build_evidence_summary([_ep("EdDSA")])
    ecdsa = _ecdsa_count(summary)
    assert ecdsa > 0, (
        f"Expected EdDSA to receive ECDSA agility credit (count > 0), got {ecdsa}. "
        f"Full cert_key_type_counts: {summary.get('cert_key_type_counts')}"
    )
