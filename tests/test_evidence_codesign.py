"""Phase 95 SCORE-01 — evidence.py CODE_SIGNING counter + scoring weight tests.

Tests:
  - test_codesign_protocol_key_present: "CODE_SIGNING" is in evidence._PROTOCOL_KEYS
  - test_codesign_weak_algo_count_increments: CODE_SIGNING endpoint with "weak" in
    service_detail increments codesign_weak_algo_count
  - test_codesign_weak_algo_count_no_increment_without_weak: CODE_SIGNING endpoint
    WITHOUT "weak" in service_detail does NOT increment codesign_weak_algo_count
  - test_codesign_ratio_in_evidence_dict: evidence dict contains both
    codesign_weak_algo_count and agility_codesign_weak_algo_ratio
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from quirk.intelligence.evidence import build_evidence_summary, _PROTOCOL_KEYS
from quirk.models import CryptoEndpoint


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_codesign_ep(
    service_detail: str = "fingerprint=aabb|weak",
    cert_pubkey_alg: str = "RSA",
    cert_pubkey_size: int = 1024,
    host: str = "cs.example.com",
    port: int = 0,
) -> CryptoEndpoint:
    ep = MagicMock(spec=CryptoEndpoint)
    ep.protocol = "CODE_SIGNING"
    ep.host = host
    ep.port = port
    ep.cert_pubkey_alg = cert_pubkey_alg
    ep.cert_pubkey_size = cert_pubkey_size
    ep.service_detail = service_detail
    ep.severity = "HIGH"
    ep.tls_version = None
    ep.cipher_suite = None
    ep.cert_sig_alg = None
    ep.cert_subject = "CN=Test CodeSign"
    ep.cert_issuer = "CN=Test CA"
    ep.cert_not_before = None
    ep.cert_not_after = None
    ep.cert_sans = None
    ep.ssh_audit_json = None
    ep.tls_capabilities_json = None
    ep.tls_supported_versions = None
    ep.tls_blocker_reason = None
    ep.scan_error = None
    ep.smime_scan_json = None
    return ep


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_codesign_protocol_key_present():
    """CODE_SIGNING must appear in evidence._PROTOCOL_KEYS (Phase 95 SCORE-01)."""
    assert "CODE_SIGNING" in _PROTOCOL_KEYS, (
        "Phase 95 SCORE-01: 'CODE_SIGNING' must be in evidence._PROTOCOL_KEYS; "
        f"current keys: {sorted(_PROTOCOL_KEYS)}"
    )


def test_codesign_weak_algo_count_increments():
    """A CODE_SIGNING endpoint with 'weak' in service_detail must increment
    codesign_weak_algo_count in the returned evidence dict."""
    ep = _make_codesign_ep(service_detail="fingerprint=deadbeef|weak")
    result = build_evidence_summary([ep])
    count = result.get("codesign_weak_algo_count", None)
    assert count is not None, (
        "evidence dict missing 'codesign_weak_algo_count' key (Phase 95 SCORE-01)"
    )
    assert count == 1, (
        f"Expected codesign_weak_algo_count == 1 for CODE_SIGNING endpoint with 'weak' "
        f"in service_detail, got {count}"
    )


def test_codesign_weak_algo_count_no_increment_without_weak():
    """A CODE_SIGNING endpoint WITHOUT 'weak' in service_detail must NOT increment
    codesign_weak_algo_count."""
    ep = _make_codesign_ep(service_detail="fingerprint=cafebabe")
    result = build_evidence_summary([ep])
    count = result.get("codesign_weak_algo_count", 0)
    assert count == 0, (
        f"Expected codesign_weak_algo_count == 0 for CODE_SIGNING endpoint without "
        f"'weak' in service_detail, got {count}"
    )


def test_codesign_ratio_in_evidence_dict():
    """evidence dict must contain both codesign_weak_algo_count and
    agility_codesign_weak_algo_ratio keys."""
    ep = _make_codesign_ep(service_detail="fingerprint=aabbcc|weak")
    result = build_evidence_summary([ep])
    assert "codesign_weak_algo_count" in result, (
        "evidence dict missing 'codesign_weak_algo_count'"
    )
    assert "agility_codesign_weak_algo_ratio" in result, (
        "evidence dict missing 'agility_codesign_weak_algo_ratio'"
    )
    ratio = result["agility_codesign_weak_algo_ratio"]
    assert isinstance(ratio, float), f"agility_codesign_weak_algo_ratio must be float, got {type(ratio)}"
    assert 0.0 <= ratio <= 1.0, f"ratio {ratio} out of [0,1] range"
