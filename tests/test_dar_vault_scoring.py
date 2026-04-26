"""Tests for Phase 30 dar_vault_weak counter (evidence.py + scoring.py).

Decisions encoded:
  - D-11: dar_vault_weak_count increments ONLY on HIGH-severity VAULT endpoints
  - D-12: dar_vault_weak_ratio weight = 8.0 in SCORE_WEIGHTS
  - D-13: NUM_SUBSCORES stays 5 (vault impact appended to existing dar_impacts list)
"""
from __future__ import annotations

from datetime import datetime, timezone
from quirk.models import CryptoEndpoint
from quirk.intelligence.evidence import build_evidence_summary, _PROTOCOL_KEYS
from quirk.intelligence.scoring import SCORE_WEIGHTS, compute_readiness_score


def _ep(severity, **kw):
    return CryptoEndpoint(
        protocol="VAULT", port=8200, severity=severity,
        scanned_at=datetime(2026, 4, 26), **kw,
    )


def test_vault_in_protocol_keys():
    assert "VAULT" in _PROTOCOL_KEYS


def test_dar_vault_weak_count_high_pki_increments():
    ep = _ep("HIGH", host="vault://x/pki/pki", service_detail="PKI/pki", cert_pubkey_alg="RSA", cert_pubkey_size=2048)
    summary = build_evidence_summary([ep])
    assert summary["dar_vault_weak_count"] == 1


def test_dar_vault_weak_count_high_token_auth_increments():
    ep = _ep("HIGH", host="vault://x/auth/token", service_detail="auth/token", cert_pubkey_alg="token")
    summary = build_evidence_summary([ep])
    assert summary["dar_vault_weak_count"] == 1


def test_dar_vault_weak_count_medium_exportable_no_increment():
    ep = _ep("MEDIUM", host="vault://x/transit/keys/foo", service_detail="transit/foo", cert_pubkey_alg="RSA", cert_pubkey_size=2048)
    summary = build_evidence_summary([ep])
    assert summary["dar_vault_weak_count"] == 0


def test_dar_vault_weak_count_medium_userpass_no_increment():
    ep = _ep("MEDIUM", host="vault://x/auth/userpass", service_detail="auth/userpass", cert_pubkey_alg="userpass")
    summary = build_evidence_summary([ep])
    assert summary["dar_vault_weak_count"] == 0


def test_dar_vault_weak_count_no_severity_no_increment():
    ep = _ep(None, host="vault://x/transit/keys/foo", service_detail="transit/foo", cert_pubkey_alg="RSA", cert_pubkey_size=4096)
    summary = build_evidence_summary([ep])
    assert summary["dar_vault_weak_count"] == 0


def test_dar_vault_weak_ratio_calculated():
    eps = [
        _ep("HIGH", host="vault://x/pki/pki", service_detail="PKI/pki", cert_pubkey_alg="RSA", cert_pubkey_size=2048),
        _ep(None,  host="vault://x/transit/k1", service_detail="transit/k1", cert_pubkey_alg="ed25519"),
    ]
    summary = build_evidence_summary(eps)
    assert summary["dar_vault_weak_count"] == 1
    assert summary["dar_vault_weak_ratio"] == 0.5  # 1 / 2 endpoints


def test_score_weights_has_dar_vault_weak_ratio_8():
    assert SCORE_WEIGHTS["dar_vault_weak_ratio"] == 8.0


def test_compute_readiness_score_subscores_count_unchanged():
    """D-13: NUM_SUBSCORES must stay 5 — vault adds to existing dar_impacts, not a new subscore."""
    ev = {"totals": {"endpoints": 1, "findings": 0}, "dar_vault_weak_count": 1}
    result = compute_readiness_score(ev)
    assert set(result["subscores"].keys()) == {
        "hygiene", "modern_tls", "identity_trust", "agility_signals", "data_at_rest",
    }


def test_compute_readiness_score_vault_impacts_data_at_rest():
    """High vault count drops the data_at_rest subscore."""
    ev_clean = {"totals": {"endpoints": 10, "findings": 0}, "dar_vault_weak_count": 0}
    ev_dirty = {"totals": {"endpoints": 10, "findings": 0}, "dar_vault_weak_count": 5}
    s_clean = compute_readiness_score(ev_clean)["subscores"]["data_at_rest"]
    s_dirty = compute_readiness_score(ev_dirty)["subscores"]["data_at_rest"]
    assert s_dirty < s_clean
