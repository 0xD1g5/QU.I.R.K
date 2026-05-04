"""Phase 46 Plan 02 — Wave 0 sentinel tests for cert-defect findings.

Covers TLS-FIND-01..05 severity corrections, D-02 multi-defect independence,
D-04 self-signed/untrusted-CA mutual exclusivity, and the _chain_verified()
direct-column-vs-JSON-fallback ordering.

Engine reality note: the TLS-FIND-05 elliptic-curve branch in risk_engine.py
matches the alg string ``"ECDSA"`` (after ``.strip().upper()``); these tests
use that exact spelling so they exercise the live branch.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from quirk.engine.risk_engine import _chain_verified, evaluate_endpoints


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg():
    cfg = MagicMock()
    cfg.scan.ports_tls = []
    return cfg


def _tls_ep(**kwargs):
    """Minimal TLS endpoint — direct chain_verified column attribute supported."""
    defaults = dict(
        host="10.0.0.1",
        port=443,
        protocol="TLS",
        scan_error=None,
        tls_version="TLSv1.3",
        tls_supported_versions="TLSv1.3",
        tls_weak_ciphers_present=False,
        tls_legacy_suites_present=False,
        cert_not_after=None,
        cert_issuer="CN=Trusted CA",
        cert_subject="CN=example.com",
        tls_capabilities_json=None,
        cert_pubkey_alg=None,
        cert_pubkey_size=None,
        chain_verified=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _find(findings, title):
    return next((f for f in findings if f["title"] == title), None)


# ---------------------------------------------------------------------------
# A1 — Expired cert → CRITICAL (TLS-FIND-01)
# ---------------------------------------------------------------------------

def test_expired_cert_emits_critical():
    past = datetime(2020, 1, 1)
    ep = _tls_ep(cert_not_after=past)
    findings = evaluate_endpoints(_cfg(), [ep])
    f = _find(findings, "TLS certificate expired")
    assert f is not None
    assert f["severity"] == "CRITICAL"
    assert "expired" in f["title"].lower()


# ---------------------------------------------------------------------------
# A2 — Self-signed (issuer == subject) → HIGH (TLS-FIND-02)
# ---------------------------------------------------------------------------

def test_self_signed_emits_high():
    ep = _tls_ep(cert_issuer="CN=foo", cert_subject="CN=foo")
    findings = evaluate_endpoints(_cfg(), [ep])
    f = _find(findings, "TLS certificate is self-signed")
    assert f is not None
    assert f["severity"] == "HIGH"


# ---------------------------------------------------------------------------
# A3 — Untrusted CA (issuer != subject AND chain_verified is False) → MEDIUM
# ---------------------------------------------------------------------------

def test_untrusted_ca_emits_medium_via_direct_column():
    ep = _tls_ep(
        cert_issuer="CN=Foo CA",
        cert_subject="CN=foo",
        chain_verified=False,
    )
    findings = evaluate_endpoints(_cfg(), [ep])
    f = _find(findings, "TLS certificate issued by untrusted CA")
    assert f is not None
    assert f["severity"] == "MEDIUM"
    assert "untrusted" in f["title"].lower() or "ca" in f["title"].lower()


# ---------------------------------------------------------------------------
# A4 — D-04 mutual exclusivity: self-signed + chain_verified=False → only HIGH self-signed
# ---------------------------------------------------------------------------

def test_d04_self_signed_does_not_also_emit_untrusted_ca():
    ep = _tls_ep(
        cert_issuer="CN=selfie",
        cert_subject="CN=selfie",
        chain_verified=False,
    )
    findings = evaluate_endpoints(_cfg(), [ep])
    self_signed = _find(findings, "TLS certificate is self-signed")
    untrusted = _find(findings, "TLS certificate issued by untrusted CA")
    assert self_signed is not None
    assert self_signed["severity"] == "HIGH"
    assert untrusted is None, "D-04 violation: untrusted-CA finding must not co-fire with self-signed"


# ---------------------------------------------------------------------------
# A5 — RSA < 2048 → HIGH (TLS-FIND-04)
# ---------------------------------------------------------------------------

def test_rsa_1024_emits_high():
    ep = _tls_ep(cert_pubkey_alg="RSA", cert_pubkey_size=1024)
    findings = evaluate_endpoints(_cfg(), [ep])
    f = _find(findings, "TLS certificate uses undersized RSA key")
    assert f is not None
    assert f["severity"] == "HIGH"


# ---------------------------------------------------------------------------
# A6 — EC < 256 → HIGH (TLS-FIND-05) — engine matches alg string "ECDSA"
# ---------------------------------------------------------------------------

def test_ecdsa_192_emits_high():
    ep = _tls_ep(cert_pubkey_alg="ECDSA", cert_pubkey_size=192)
    findings = evaluate_endpoints(_cfg(), [ep])
    f = _find(findings, "TLS certificate uses undersized ECDSA key")
    assert f is not None
    assert f["severity"] == "HIGH"


# ---------------------------------------------------------------------------
# A7 — D-02 multi-defect: expired + self-signed + RSA-1024 → 3 findings
# ---------------------------------------------------------------------------

def test_d02_multi_defect_emits_three_findings_no_rollup():
    past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=10)
    ep = _tls_ep(
        cert_not_after=past,
        cert_issuer="CN=selfie",
        cert_subject="CN=selfie",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=1024,
    )
    findings = evaluate_endpoints(_cfg(), [ep])
    titles = [f["title"] for f in findings]

    expired = _find(findings, "TLS certificate expired")
    self_signed = _find(findings, "TLS certificate is self-signed")
    rsa = _find(findings, "TLS certificate uses undersized RSA key")
    untrusted = _find(findings, "TLS certificate issued by untrusted CA")

    assert expired is not None and expired["severity"] == "CRITICAL"
    assert self_signed is not None and self_signed["severity"] == "HIGH"
    assert rsa is not None and rsa["severity"] == "HIGH"
    # D-04: no untrusted-CA finding even though chain doesn't verify (self-signed precludes)
    assert untrusted is None
    # D-02: exactly the three defect-class findings (plus no surprise extras among cert-defect titles)
    cert_titles = {
        "TLS certificate expired",
        "TLS certificate is self-signed",
        "TLS certificate uses undersized RSA key",
    }
    cert_findings = [t for t in titles if t in cert_titles or t == "TLS certificate issued by untrusted CA"]
    assert len(cert_findings) == 3


# ---------------------------------------------------------------------------
# A8 — _chain_verified() prefers direct column when set
# ---------------------------------------------------------------------------

def test_chain_verified_prefers_direct_column():
    ep = _tls_ep(chain_verified=True, tls_capabilities_json=None)
    assert _chain_verified(ep) is True

    ep_false = _tls_ep(chain_verified=False, tls_capabilities_json=None)
    assert _chain_verified(ep_false) is False


def test_chain_verified_direct_column_wins_over_json_blob():
    # Direct column is True; JSON blob says False — column must win.
    blob = json.dumps({"chain_verified": False})
    ep = _tls_ep(chain_verified=True, tls_capabilities_json=blob)
    assert _chain_verified(ep) is True


# ---------------------------------------------------------------------------
# A9 — _chain_verified() falls back to JSON blob when column is None
# ---------------------------------------------------------------------------

def test_chain_verified_falls_back_to_json_when_column_none():
    blob = json.dumps({"chain_verified": False})
    ep = _tls_ep(chain_verified=None, tls_capabilities_json=blob)
    assert _chain_verified(ep) is False

    blob_true = json.dumps({"chain_verified": True})
    ep_true = _tls_ep(chain_verified=None, tls_capabilities_json=blob_true)
    assert _chain_verified(ep_true) is True


# ---------------------------------------------------------------------------
# A10 — None is neutral: untrusted-CA branch must NOT fire when cv is None
# ---------------------------------------------------------------------------

def test_chain_verified_none_does_not_fire_untrusted_ca():
    # Network failure path: chain_verified is None, no JSON blob.
    ep = _tls_ep(
        cert_issuer="CN=Some CA",
        cert_subject="CN=example.com",
        chain_verified=None,
        tls_capabilities_json=None,
    )
    assert _chain_verified(ep) is None
    findings = evaluate_endpoints(_cfg(), [ep])
    assert _find(findings, "TLS certificate issued by untrusted CA") is None
    assert _find(findings, "TLS certificate is self-signed") is None
