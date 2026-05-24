"""Phase 99 CTX-03 — Tests for codesign expiry classification (D-07/D-08/D-09).

Covers:
- _classify_codesign_severity expiry branch (expired=HIGH, approaching=MEDIUM)
- Stacking with weak-crypto reasons
- SAFE-crypto-but-expired cert emits HIGH (no longer dropped)
- scan_codesign_from_tls_endpoints pseudo_parsed includes not_after_dt + expired fields
"""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from quirk.scanner.codesign_scanner import (
    _classify_codesign_severity,
    scan_codesign_from_tls_endpoints,
)

_CODE_SIGNING_OID = "1.3.6.1.5.5.7.3.3"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_utc():
    return datetime.now(timezone.utc)


def _tls_ep_with_eku(**kwargs):
    """Build a minimal TLS endpoint carrying the CodeSigning EKU OID."""
    defaults = dict(
        host="10.0.0.1",
        port=443,
        protocol="TLS",
        cert_subject="CN=Code Signer",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=4096,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_not_after=_now_utc() + timedelta(days=365),
        tls_capabilities_json=json.dumps({"eku_oids": [_CODE_SIGNING_OID]}),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# _classify_codesign_severity — expiry branch (D-07/D-08)
# ---------------------------------------------------------------------------

class TestClassifyCodesignSeverityExpiry:
    def test_expired_returns_high(self):
        parsed = {
            "sig_hash": "sha256",
            "key_alg": "RSA",
            "key_bits": 4096,
            "expired": True,
            "not_after_dt": _now_utc() - timedelta(days=1),
        }
        severity, reasons = _classify_codesign_severity(parsed)
        assert severity == "HIGH"
        assert "expired" in reasons

    def test_approaching_expiry_returns_medium(self):
        parsed = {
            "sig_hash": "sha256",
            "key_alg": "RSA",
            "key_bits": 4096,
            "expired": False,
            "not_after_dt": _now_utc() + timedelta(days=30),
        }
        severity, reasons = _classify_codesign_severity(parsed)
        assert severity == "MEDIUM"
        assert "approaching-expiry" in reasons

    def test_approaching_exactly_90_days_is_medium(self):
        parsed = {
            "sig_hash": "sha256",
            "key_alg": "RSA",
            "key_bits": 4096,
            "expired": False,
            "not_after_dt": _now_utc() + timedelta(days=90),
        }
        severity, reasons = _classify_codesign_severity(parsed)
        assert severity == "MEDIUM"
        assert "approaching-expiry" in reasons

    def test_not_approaching_91_days_is_safe(self):
        """91+ days remaining with no weak crypto → no finding."""
        parsed = {
            "sig_hash": "sha256",
            "key_alg": "RSA",
            "key_bits": 4096,
            "expired": False,
            "not_after_dt": _now_utc() + timedelta(days=91),
        }
        severity, reasons = _classify_codesign_severity(parsed)
        assert severity is None
        assert "approaching-expiry" not in reasons

    def test_safe_crypto_but_expired_returns_high(self):
        """D-08: SAFE-crypto-but-expired cert must emit HIGH (no longer dropped)."""
        parsed = {
            "sig_hash": "sha256",
            "key_alg": "RSA",
            "key_bits": 4096,
            "expired": True,
            "not_after_dt": _now_utc() - timedelta(days=5),
        }
        severity, reasons = _classify_codesign_severity(parsed)
        assert severity == "HIGH"
        assert "expired" in reasons

    def test_expiry_stacks_with_weak_crypto(self):
        """D-08: expired + weak-crypto reasons both appear; severity is HIGH."""
        parsed = {
            "sig_hash": "sha1",  # weak signing alg → weak-signing-alg
            "key_alg": "RSA",
            "key_bits": 1024,    # weak RSA key → weak-rsa-key
            "expired": True,
            "not_after_dt": _now_utc() - timedelta(days=1),
        }
        severity, reasons = _classify_codesign_severity(parsed)
        assert severity == "HIGH"
        assert "expired" in reasons
        assert "weak-rsa-key" in reasons

    def test_no_expiry_fields_still_classifies_weak_crypto(self):
        """Existing weak-crypto behavior unchanged when no expiry fields present."""
        parsed = {
            "sig_hash": "sha1",
            "key_alg": "RSA",
            "key_bits": 4096,
        }
        severity, reasons = _classify_codesign_severity(parsed)
        assert severity == "HIGH"
        assert "weak-signing-alg" in reasons

    def test_safe_no_expiry_returns_none(self):
        """Existing SAFE cert behavior unchanged when no expiry fields present."""
        parsed = {
            "sig_hash": "sha256",
            "key_alg": "RSA",
            "key_bits": 4096,
        }
        severity, reasons = _classify_codesign_severity(parsed)
        assert severity is None


# ---------------------------------------------------------------------------
# scan_codesign_from_tls_endpoints — pseudo_parsed expiry fields (D-09)
# ---------------------------------------------------------------------------

class TestTlsPathExpiryFields:
    def test_pseudo_parsed_includes_not_after_dt_and_expired_when_expired(self):
        """D-09: TLS path sets pseudo_parsed['not_after_dt'] + pseudo_parsed['expired']."""
        past = _now_utc() - timedelta(days=2)
        ep = _tls_ep_with_eku(cert_not_after=past)
        results = scan_codesign_from_tls_endpoints([ep])
        # Must produce a CODE_SIGNING endpoint
        assert len(results) == 1
        # smime_scan_json must reflect expiry
        scan_data = json.loads(results[0].smime_scan_json)
        assert scan_data.get("expired") is True
        assert "approaching-expiry" not in (scan_data.get("reasons") or [])
        # severity on the resulting endpoint must be HIGH
        assert results[0].severity == "HIGH"

    def test_pseudo_parsed_approaching_expiry(self):
        """D-09: TLS path detects approaching expiry (within 90 days)."""
        future_30 = _now_utc() + timedelta(days=30)
        ep = _tls_ep_with_eku(cert_not_after=future_30)
        results = scan_codesign_from_tls_endpoints([ep])
        assert len(results) == 1
        scan_data = json.loads(results[0].smime_scan_json)
        assert "approaching-expiry" in (scan_data.get("reasons") or [])
        assert results[0].severity == "MEDIUM"

    def test_no_expiry_safe_crypto_no_endpoint_emitted(self):
        """D-09: TLS path with SAFE crypto + no expiry does not emit endpoint."""
        future = _now_utc() + timedelta(days=365)
        ep = _tls_ep_with_eku(cert_not_after=future)
        results = scan_codesign_from_tls_endpoints([ep])
        assert len(results) == 0

    def test_none_not_after_defaults_to_not_expired(self):
        """D-09: None cert_not_after → expired defaults to False (no false positive)."""
        # cert with no expiry info but weak crypto still emits
        ep = _tls_ep_with_eku(cert_not_after=None,
                               cert_pubkey_alg="RSA", cert_pubkey_size=1024)
        results = scan_codesign_from_tls_endpoints([ep])
        assert len(results) == 1
        scan_data = json.loads(results[0].smime_scan_json)
        assert scan_data.get("expired") is False
