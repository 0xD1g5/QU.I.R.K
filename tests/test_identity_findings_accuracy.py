"""Identity Findings Accuracy — RED scaffold for Phase 25.

Tests define the acceptance contract for three bug fixes:
  - SAML-04 / IDENT-02 / IDENT-03: RS-family OIDC endpoints routed to
    _derive_identity_findings, not _derive_findings (TLS-bleed fix)
  - KERB-03: ldap3>=2.9.1 present in pyproject.toml [identity] extras

Tests MUST FAIL before Plan 02 implementation lands. Imports succeed because
the modules exist; only the behaviors are absent.
"""
from __future__ import annotations

import pathlib
import unittest
from dataclasses import dataclass
from typing import Optional

from quirk.dashboard.api.routes.scan import _derive_findings, _derive_identity_findings


# ---------------------------------------------------------------------------
# Shared test fixture — _Ep dataclass (same contract as test_identity_surface)
# ---------------------------------------------------------------------------

@dataclass
class _Ep:
    host: str
    port: int
    protocol: str
    cert_pubkey_alg: Optional[str] = None
    cert_pubkey_size: Optional[int] = None
    service_detail: Optional[str] = None
    scanned_at: Optional[object] = None
    scan_error: Optional[str] = None
    tls_blocker_reason: Optional[str] = None
    cert_not_after: Optional[object] = None
    cert_subject: Optional[str] = None
    cert_issuer: Optional[str] = None
    tls_version: Optional[str] = None
    tls_weak_ciphers_present: bool = False
    id: Optional[int] = None


def _oidc_rs256_ep() -> _Ep:
    """OIDC RS256 endpoint — stored as protocol=SAML per saml_scanner convention."""
    return _Ep(
        host="auth.example.com",
        port=443,
        protocol="SAML",
        cert_pubkey_alg="RS256",
        cert_pubkey_size=None,
        service_detail="oidc-discovery|https://auth.example.com/.well-known/openid-configuration",
    )


def _oidc_rs384_ep() -> _Ep:
    """OIDC RS384 endpoint — should also produce IdentityFinding (HIGH)."""
    return _Ep(
        host="auth.example.com",
        port=443,
        protocol="SAML",
        cert_pubkey_alg="RS384",
        cert_pubkey_size=None,
        service_detail="oidc-discovery|https://auth.example.com/.well-known/openid-configuration",
    )


def _oidc_ecdsa_ep() -> _Ep:
    """OIDC ES256 endpoint — quantum-safe; should produce NO identity finding."""
    return _Ep(
        host="auth.example.com",
        port=443,
        protocol="SAML",
        cert_pubkey_alg="ES256",
        cert_pubkey_size=None,
        service_detail="oidc-discovery|https://auth.example.com/.well-known/openid-configuration",
    )


# ===========================================================================
# Phase 25 RED tests
# ===========================================================================

class TestIdentityFindingsAccuracy(unittest.TestCase):
    """RED scaffold for Phase 25 identity findings accuracy fixes.

    All 4 tests MUST FAIL before Plan 02 implementation lands.
    """

    # --- Test 1: SAML-04 / IDENT-03 ---

    def test_rs256_oidc_produces_identity_finding(self) -> None:
        """SAML-04 / IDENT-03: RS256 OIDC endpoint must produce IdentityFinding
        (source='saml', severity='HIGH', algorithm='RS256') from _derive_identity_findings().

        FAILS RED because SAML branch currently has no RS-family check — RS256
        falls through the elif chain without emitting anything.
        """
        results = _derive_identity_findings([_oidc_rs256_ep()])
        self.assertEqual(len(results), 1, "Expected 1 IdentityFinding for RS256 OIDC endpoint")
        finding = results[0]
        self.assertEqual(finding.source, "saml")
        self.assertEqual(finding.severity, "HIGH")
        self.assertEqual(finding.algorithm, "RS256")
        self.assertEqual(finding.protocol, "SAML")

    def test_rs384_oidc_produces_identity_finding(self) -> None:
        """IDENT-03: RS384 OIDC endpoint must produce IdentityFinding (HIGH) via
        OIDC_ALG_SEVERITY lookup — confirms lookup applies to all RS-family algs.

        FAILS RED for the same reason as test_rs256.
        """
        results = _derive_identity_findings([_oidc_rs384_ep()])
        self.assertEqual(len(results), 1, "Expected 1 IdentityFinding for RS384 OIDC endpoint")
        self.assertEqual(results[0].severity, "HIGH")
        self.assertEqual(results[0].algorithm, "RS384")

    # --- Test 2: IDENT-02 — TLS bleed guard ---

    def test_saml_endpoint_absent_from_tls_findings(self) -> None:
        """IDENT-02: SAML/OIDC endpoints must not appear in _derive_findings() output.

        Currently, an RS256 OIDC endpoint (cert_pubkey_alg='RS256') passes through
        the quantum-vulnerable block in _derive_findings() and emits a source='tls'
        FindingItem. This test asserts ZERO tls-sourced findings for a SAML endpoint.

        FAILS RED because the broad protocol guard (D-03) does not yet exist in
        _derive_findings().
        """
        tls_findings = _derive_findings([_oidc_rs256_ep()])
        self.assertEqual(
            len(tls_findings),
            0,
            f"SAML/OIDC endpoint must not produce TLS findings; got: {tls_findings}",
        )

    # --- Test 3: KERB-03 — ldap3 dependency ---

    def test_pyproject_ldap3_in_identity_extras(self) -> None:
        """KERB-03: pyproject.toml [identity] extras group must contain 'ldap3>=2.9.1'.

        FAILS RED because pyproject.toml currently has only impacket in [identity].
        """
        _REPO_ROOT = pathlib.Path(__file__).parent.parent
        source = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn(
            '"ldap3>=2.9.1"',
            source,
            "pyproject.toml [identity] group missing ldap3>=2.9.1 — add per D-04",
        )


if __name__ == "__main__":
    unittest.main()
