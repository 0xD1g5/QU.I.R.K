"""Tests for BACK-74: TLS finding coverage gaps in risk_engine.evaluate_endpoints().

Covers the four rules added to close the gap between what the TLS scanner collects
and what the risk engine surfaces as actionable findings.
"""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from quirk.engine.findings_evaluator import (
    NIST_IR_8547_DEPRECATION,
    _build_finding,
    evaluate_endpoints,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg():
    """Minimal config stub with an empty TLS port list."""
    cfg = MagicMock()
    cfg.scan.ports_tls = []
    return cfg


def _tls_ep(**kwargs):
    """Build a minimal TLS CryptoEndpoint-like object with sensible defaults."""
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
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _titles(findings):
    return [f["title"] for f in findings]


def _find(findings, title):
    return next((f for f in findings if f["title"] == title), None)


# ---------------------------------------------------------------------------
# Phase 48 — _build_finding helper (D-02, D-06)
# ---------------------------------------------------------------------------


class TestBuildFinding:
    def test_rejects_empty_description(self):
        with pytest.raises(ValueError):
            _build_finding(severity="LOW", host="h", port=1, title="t",
                           description="", recommendation="r")

    def test_rejects_whitespace_description(self):
        with pytest.raises(ValueError):
            _build_finding(severity="LOW", host="h", port=1, title="t",
                           description="   ", recommendation="r")

    def test_rejects_empty_recommendation(self):
        with pytest.raises(ValueError):
            _build_finding(severity="LOW", host="h", port=1, title="t",
                           description="d", recommendation="")

    def test_rejects_whitespace_recommendation(self):
        with pytest.raises(ValueError):
            _build_finding(severity="LOW", host="h", port=1, title="t",
                           description="d", recommendation="  \t")

    def test_quantum_vulnerable_appends_deprecation_phrase(self):
        f = _build_finding(
            severity="HIGH", host="h", port=1, title="t",
            description="d",
            recommendation="Migrate to ML-KEM (FIPS 203).",
            quantum_vulnerable=True,
        )
        assert NIST_IR_8547_DEPRECATION in f["recommendation"]
        assert f["recommendation"].endswith(NIST_IR_8547_DEPRECATION)

    def test_non_quantum_does_not_append(self):
        f = _build_finding(severity="LOW", host="h", port=1, title="t",
                           description="d", recommendation="r")
        assert NIST_IR_8547_DEPRECATION not in f["recommendation"]

    def test_constant_exact_string(self):
        assert NIST_IR_8547_DEPRECATION == (
            "Per NIST IR 8547, RSA and ECC are deprecated after 2030 and "
            "disallowed after 2035."
        )

    def test_returns_seven_key_dict(self):
        # Phase 49 D-02: _build_finding now eagerly attaches a `compliance`
        # list[dict] key alongside the original six.
        f = _build_finding(severity="LOW", host="h", port=1, title="t",
                           description="d", recommendation="r")
        assert set(f.keys()) == {"severity", "host", "port", "title",
                                  "description", "recommendation",
                                  "compliance"}
        assert f["compliance"] == []  # unmapped title → empty list


# ---------------------------------------------------------------------------
# BUG-01: Legacy cipher suites
# ---------------------------------------------------------------------------

class TestLegacyCipherSuites:
    def test_legacy_suites_present_produces_low_finding(self):
        ep = _tls_ep(tls_legacy_suites_present=True)
        findings = evaluate_endpoints(_cfg(), [ep])
        f = _find(findings, "Legacy TLS cipher suites accepted")
        assert f is not None, "Expected legacy cipher suite finding"
        assert f["severity"] == "LOW"

    def test_no_legacy_suites_no_finding(self):
        ep = _tls_ep(tls_legacy_suites_present=False)
        findings = evaluate_endpoints(_cfg(), [ep])
        assert _find(findings, "Legacy TLS cipher suites accepted") is None

    def test_legacy_suites_none_treated_as_false(self):
        ep = _tls_ep(tls_legacy_suites_present=None)
        findings = evaluate_endpoints(_cfg(), [ep])
        assert _find(findings, "Legacy TLS cipher suites accepted") is None


# ---------------------------------------------------------------------------
# BUG-02: Certificate expiry
# ---------------------------------------------------------------------------

class TestCertExpiry:
    def _expired_ep(self, days_ago=10):
        past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_ago)
        return _tls_ep(cert_not_after=past)

    def _expiring_ep(self, days_ahead=15):
        future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days_ahead)
        return _tls_ep(cert_not_after=future)

    def _valid_ep(self, days_ahead=365):
        future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days_ahead)
        return _tls_ep(cert_not_after=future)

    def test_expired_cert_produces_critical_finding(self):
        ep = self._expired_ep()
        findings = evaluate_endpoints(_cfg(), [ep])
        f = _find(findings, "TLS certificate expired")
        assert f is not None
        assert f["severity"] == "CRITICAL"

    def test_expiring_soon_produces_medium_finding(self):
        ep = self._expiring_ep(days_ahead=10)
        findings = evaluate_endpoints(_cfg(), [ep])
        f = _find(findings, "TLS certificate expiring within 30 days")
        assert f is not None
        assert f["severity"] == "MEDIUM"

    def test_cert_expiring_at_29_days_produces_finding(self):
        ep = self._expiring_ep(days_ahead=29)
        findings = evaluate_endpoints(_cfg(), [ep])
        assert _find(findings, "TLS certificate expiring within 30 days") is not None

    def test_valid_cert_no_expiry_finding(self):
        ep = self._valid_ep()
        findings = evaluate_endpoints(_cfg(), [ep])
        assert _find(findings, "TLS certificate expired") is None
        assert _find(findings, "TLS certificate expiring within 30 days") is None

    def test_no_cert_not_after_no_finding(self):
        ep = _tls_ep(cert_not_after=None)
        findings = evaluate_endpoints(_cfg(), [ep])
        assert _find(findings, "TLS certificate expired") is None

    def test_expired_beats_expiring_soon(self):
        # Expired cert must produce CRITICAL, not the MEDIUM expiring-soon finding
        past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        ep = _tls_ep(cert_not_after=past)
        findings = evaluate_endpoints(_cfg(), [ep])
        assert _find(findings, "TLS certificate expired") is not None
        assert _find(findings, "TLS certificate expiring within 30 days") is None


# ---------------------------------------------------------------------------
# BUG-03: Self-signed / chain-unverified
# ---------------------------------------------------------------------------

class TestSelfSigned:
    def test_self_signed_issuer_eq_subject_produces_high(self):
        ep = _tls_ep(
            cert_issuer="CN=myserver",
            cert_subject="CN=myserver",
        )
        findings = evaluate_endpoints(_cfg(), [ep])
        f = _find(findings, "TLS certificate is self-signed")
        assert f is not None
        assert f["severity"] == "HIGH"
        # D-04: self-signed must NOT also fire the untrusted-CA branch
        assert _find(findings, "TLS certificate issued by untrusted CA") is None

    def test_chain_unverified_false_produces_medium(self):
        # D-04: untrusted-CA fires only when issuer != subject AND chain_verified is False
        caps = json.dumps({"chain_verified": False, "chain_depth": 1})
        ep = _tls_ep(
            cert_issuer="CN=Unknown CA",
            cert_subject="CN=example.com",
            tls_capabilities_json=caps,
        )
        findings = evaluate_endpoints(_cfg(), [ep])
        f = _find(findings, "TLS certificate issued by untrusted CA")
        assert f is not None
        assert f["severity"] == "MEDIUM"
        assert _find(findings, "TLS certificate is self-signed") is None

    def test_chain_verified_true_no_finding(self):
        caps = json.dumps({"chain_verified": True, "chain_depth": 3})
        ep = _tls_ep(
            cert_issuer="CN=Trusted CA",
            cert_subject="CN=example.com",
            tls_capabilities_json=caps,
        )
        findings = evaluate_endpoints(_cfg(), [ep])
        assert _find(findings, "TLS certificate is self-signed") is None
        assert _find(findings, "TLS certificate issued by untrusted CA") is None

    def test_different_issuer_subject_no_caps_no_finding(self):
        ep = _tls_ep(
            cert_issuer="CN=DigiCert",
            cert_subject="CN=example.com",
            tls_capabilities_json=None,
        )
        findings = evaluate_endpoints(_cfg(), [ep])
        assert _find(findings, "TLS certificate is self-signed") is None
        assert _find(findings, "TLS certificate issued by untrusted CA") is None

    def test_empty_issuer_subject_no_finding(self):
        # Missing cert data — do not produce spurious cert-trust findings
        ep = _tls_ep(cert_issuer="", cert_subject="")
        findings = evaluate_endpoints(_cfg(), [ep])
        assert _find(findings, "TLS certificate is self-signed") is None
        assert _find(findings, "TLS certificate issued by untrusted CA") is None


# ---------------------------------------------------------------------------
# BUG-04: Quantum-vulnerable cert key (RSA / ECDSA)
# ---------------------------------------------------------------------------

class TestQuantumVulnerableCertKey:
    def test_rsa_2048_produces_medium(self):
        ep = _tls_ep(cert_pubkey_alg="RSA", cert_pubkey_size=2048)
        findings = evaluate_endpoints(_cfg(), [ep])
        f = _find(findings, "TLS certificate uses quantum-vulnerable RSA key")
        assert f is not None
        assert f["severity"] == "MEDIUM"

    def test_rsa_4096_produces_medium(self):
        ep = _tls_ep(cert_pubkey_alg="RSA", cert_pubkey_size=4096)
        findings = evaluate_endpoints(_cfg(), [ep])
        f = _find(findings, "TLS certificate uses quantum-vulnerable RSA key")
        assert f is not None
        assert f["severity"] == "MEDIUM"

    def test_rsa_1024_produces_high(self):
        ep = _tls_ep(cert_pubkey_alg="RSA", cert_pubkey_size=1024)
        findings = evaluate_endpoints(_cfg(), [ep])
        f = _find(findings, "TLS certificate uses undersized RSA key")
        assert f is not None
        assert f["severity"] == "HIGH"
        # Undersized finding should NOT also emit the generic quantum finding
        assert _find(findings, "TLS certificate uses quantum-vulnerable RSA key") is None

    def test_ecdsa_256_produces_medium(self):
        ep = _tls_ep(cert_pubkey_alg="ECDSA", cert_pubkey_size=256)
        findings = evaluate_endpoints(_cfg(), [ep])
        f = _find(findings, "TLS certificate uses quantum-vulnerable ECDSA key")
        assert f is not None
        assert f["severity"] == "MEDIUM"

    def test_ecdsa_192_produces_high(self):
        ep = _tls_ep(cert_pubkey_alg="ECDSA", cert_pubkey_size=192)
        findings = evaluate_endpoints(_cfg(), [ep])
        f = _find(findings, "TLS certificate uses undersized ECDSA key")
        assert f is not None
        assert f["severity"] == "HIGH"

    def test_ed25519_no_quantum_finding(self):
        # Ed25519 is quantum-safe — no finding expected
        ep = _tls_ep(cert_pubkey_alg="Ed25519", cert_pubkey_size=256)
        findings = evaluate_endpoints(_cfg(), [ep])
        assert _find(findings, "TLS certificate uses quantum-vulnerable RSA key") is None
        assert _find(findings, "TLS certificate uses quantum-vulnerable ECDSA key") is None

    def test_unknown_alg_no_quantum_finding(self):
        ep = _tls_ep(cert_pubkey_alg="Unknown", cert_pubkey_size=None)
        findings = evaluate_endpoints(_cfg(), [ep])
        assert _find(findings, "TLS certificate uses quantum-vulnerable RSA key") is None

    def test_no_alg_no_quantum_finding(self):
        ep = _tls_ep(cert_pubkey_alg=None, cert_pubkey_size=None)
        findings = evaluate_endpoints(_cfg(), [ep])
        assert _find(findings, "TLS certificate uses quantum-vulnerable RSA key") is None


# ---------------------------------------------------------------------------
# Integration: multiple rules fire on same endpoint
# ---------------------------------------------------------------------------

class TestRichFindingContext:
    """Phase 48 Plan 01 invariants: every finding emitted by evaluate_endpoints
    has a non-empty description; every quantum-vulnerable finding cites the
    NIST IR 8547 deprecation phrase and a FIPS 203/204/205 designation; no
    finding contains stale Kyber/Dilithium/'when standards are adopted'
    terminology.
    """

    @pytest.fixture
    def all_findings(self):
        past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=10)
        soon = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=15)
        caps_unverified = json.dumps({"chain_verified": False, "chain_depth": 1})
        eps = [
            # Legacy TLS versions
            _tls_ep(host="10.0.0.10", tls_version="TLSv1.0",
                    tls_supported_versions="TLSv1.0,TLSv1.2"),
            # Legacy cipher suites
            _tls_ep(host="10.0.0.11", tls_legacy_suites_present=True),
            # Expired cert
            _tls_ep(host="10.0.0.12", cert_not_after=past),
            # Expiring cert
            _tls_ep(host="10.0.0.13", cert_not_after=soon),
            # Self-signed
            _tls_ep(host="10.0.0.14", cert_issuer="CN=self",
                    cert_subject="CN=self"),
            # Untrusted CA
            _tls_ep(host="10.0.0.15", cert_issuer="CN=Unknown CA",
                    cert_subject="CN=example.com",
                    tls_capabilities_json=caps_unverified),
            # RSA undersized — quantum_vulnerable
            _tls_ep(host="10.0.0.16", cert_pubkey_alg="RSA",
                    cert_pubkey_size=1024),
            # RSA — quantum_vulnerable
            _tls_ep(host="10.0.0.17", cert_pubkey_alg="RSA",
                    cert_pubkey_size=2048),
            # ECDSA undersized — quantum_vulnerable
            _tls_ep(host="10.0.0.18", cert_pubkey_alg="ECDSA",
                    cert_pubkey_size=192),
            # ECDSA — quantum_vulnerable
            _tls_ep(host="10.0.0.19", cert_pubkey_alg="ECDSA",
                    cert_pubkey_size=256),
            # SSH advisory — quantum_vulnerable
            SimpleNamespace(host="10.0.0.20", port=22, protocol="SSH",
                            scan_error=None),
            # UNKNOWN open service
            SimpleNamespace(host="10.0.0.21", port=9999, protocol="UNKNOWN",
                            scan_error=None),
            # HTTP plaintext
            SimpleNamespace(host="10.0.0.22", port=80, protocol="HTTP",
                            scan_error=None),
        ]
        return evaluate_endpoints(_cfg(), eps)

    def test_every_finding_has_non_empty_description(self, all_findings):
        assert all_findings, "fixture should yield findings"
        for f in all_findings:
            desc = f.get("description")
            assert desc, f"Missing description: {f}"
            assert isinstance(desc, str) and desc.strip(), \
                f"Whitespace-only description: {f}"

    def test_no_stale_pqc_terms(self, all_findings):
        forbidden = ("kyber", "dilithium", "when standards are adopted")
        for f in all_findings:
            blob = (f.get("description", "") + " " +
                    f.get("recommendation", "")).lower()
            for term in forbidden:
                assert term not in blob, \
                    f"Stale term '{term}' in finding: {f}"

    def test_quantum_vulnerable_findings_cite_deprecation_and_fips(
            self, all_findings):
        # Heuristic: quantum-vulnerable findings have RSA/ECDSA in title or
        # are SSH advisory (per plan tasks).
        qv_titles = ("RSA", "ECDSA", "SSH quantum")
        qv_findings = [
            f for f in all_findings
            if any(t in f.get("title", "") for t in qv_titles)
        ]
        assert qv_findings, \
            "Fixture should produce at least one quantum-vulnerable finding"
        for f in qv_findings:
            rec = f.get("recommendation", "")
            assert NIST_IR_8547_DEPRECATION in rec, \
                f"Missing deprecation phrase: {f}"
            assert any(s in rec for s in ("FIPS 203", "FIPS 204", "FIPS 205")), \
                f"Missing FIPS designation: {f}"

    def test_non_quantum_findings_omit_deprecation_phrase(self, all_findings):
        non_qv_titles = (
            "Legacy TLS versions",
            "Legacy TLS cipher suites",
            "TLS certificate expired",
            "TLS certificate expiring",
            "TLS certificate is self-signed",
            "TLS certificate issued by untrusted CA",
            "Plaintext HTTP service detected",
            "Unknown open service",
        )
        non_qv = [
            f for f in all_findings
            if any(f.get("title", "").startswith(t) for t in non_qv_titles)
        ]
        assert non_qv, "Fixture should produce non-quantum findings"
        for f in non_qv:
            assert NIST_IR_8547_DEPRECATION not in f.get("recommendation", ""), \
                f"Non-quantum finding leaked deprecation phrase: {f}"

    def test_dedup_safety_for_quantum_findings(self):
        """T-48-03: two quantum-vulnerable endpoints with identical
        (host, port, title) collapse to one finding because the deterministic
        deprecation suffix preserves recommendation equality."""
        ep1 = _tls_ep(host="10.0.0.50", port=443,
                      cert_pubkey_alg="RSA", cert_pubkey_size=2048)
        ep2 = _tls_ep(host="10.0.0.50", port=443,
                      cert_pubkey_alg="RSA", cert_pubkey_size=2048)
        findings = evaluate_endpoints(_cfg(), [ep1, ep2])
        rsa_findings = [
            f for f in findings
            if f.get("title") == "TLS certificate uses quantum-vulnerable RSA key"
        ]
        assert len(rsa_findings) == 1, \
            f"Expected 1 deduped RSA finding, got {len(rsa_findings)}"
        assert NIST_IR_8547_DEPRECATION in rsa_findings[0]["recommendation"]


class TestMultipleRulesOnOneEndpoint:
    def test_expired_self_signed_rsa1024_all_fire(self):
        past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=5)
        ep = _tls_ep(
            cert_not_after=past,
            cert_issuer="CN=selfie",
            cert_subject="CN=selfie",
            cert_pubkey_alg="RSA",
            cert_pubkey_size=1024,
            tls_legacy_suites_present=True,
        )
        findings = evaluate_endpoints(_cfg(), [ep])
        titles = _titles(findings)
        # D-02: each defect class emits an independent finding (no rollup)
        assert "TLS certificate expired" in titles
        assert "TLS certificate is self-signed" in titles
        assert "TLS certificate uses undersized RSA key" in titles
        assert "Legacy TLS cipher suites accepted" in titles
        # D-04: self-signed precludes the untrusted-CA finding
        assert "TLS certificate issued by untrusted CA" not in titles
        # Severity bumps per TLS-FIND-01 / TLS-FIND-02
        expired = _find(findings, "TLS certificate expired")
        assert expired is not None and expired["severity"] == "CRITICAL"
        self_signed = _find(findings, "TLS certificate is self-signed")
        assert self_signed is not None and self_signed["severity"] == "HIGH"
        rsa = _find(findings, "TLS certificate uses undersized RSA key")
        assert rsa is not None and rsa["severity"] == "HIGH"
