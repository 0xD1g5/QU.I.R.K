"""Identity Findings Accuracy — RED scaffold for Phase 25.

Tests define the acceptance contract for three bug fixes:
  - SAML-04 / IDENT-02 / IDENT-03: RS-family OIDC endpoints routed to
    _derive_identity_findings, not _derive_findings (TLS-bleed fix)
  - KERB-03: ldap3>=2.9.1 present in pyproject.toml [identity] extras

Tests MUST FAIL before Plan 02 implementation lands. Imports succeed because
the modules exist; only the behaviors are absent.

Covers GAP-01 — routes RS-family OIDC endpoints to _derive_identity_findings
(not _derive_findings), the substance of the GAP-01 fix.
"""
from __future__ import annotations

import pathlib
import unittest
from dataclasses import dataclass
from typing import Optional

from quirk.dashboard.api.routes.scan import _derive_findings, _derive_identity_findings
from quirk.engine.findings_evaluator import evaluate_identity_endpoints


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


    # --- Test 4: 25-03-01 / INFRA-03 — chaos lab oracle sections ---

    def test_chaos_lab_expected_results_phase25(self) -> None:
        """INFRA-03 / 25-03-01: expected_results_v3.md must contain all three Phase 25
        identity chaos lab oracle sections with the required algorithm marker strings.

        Verifies:
        - '## Phase 25 — DNSSEC Profile' section is present (with RSASHA1 marker)
        - '## Phase 25 — SAML/OIDC Profile' section is present (with RSA-1024 marker)
        - '## Phase 25 — Kerberos Profile' section is present (with rc4-hmac marker)
        - Exactly 3 '## Phase 25' headings exist in the file
        """
        _REPO_ROOT = pathlib.Path(__file__).parent.parent
        oracle_path = _REPO_ROOT / "quantum-chaos-enterprise-lab" / "expected_results_v3.md"
        content = oracle_path.read_text(encoding="utf-8")

        # DNSSEC section
        self.assertIn(
            "## Phase 25 — DNSSEC Profile",
            content,
            "expected_results_v3.md missing '## Phase 25 — DNSSEC Profile' section",
        )
        self.assertIn(
            "RSASHA1",
            content,
            "expected_results_v3.md DNSSEC section missing 'RSASHA1' algorithm marker",
        )

        # SAML/OIDC section
        self.assertIn(
            "## Phase 25 — SAML/OIDC Profile",
            content,
            "expected_results_v3.md missing '## Phase 25 — SAML/OIDC Profile' section",
        )
        self.assertIn(
            "RSA-1024",
            content,
            "expected_results_v3.md SAML/OIDC section missing 'RSA-1024' marker",
        )

        # Kerberos section
        self.assertIn(
            "## Phase 25 — Kerberos Profile",
            content,
            "expected_results_v3.md missing '## Phase 25 — Kerberos Profile' section",
        )
        self.assertIn(
            "rc4-hmac",
            content,
            "expected_results_v3.md Kerberos section missing 'rc4-hmac' etype marker",
        )

        # Exactly 3 Phase 25 headings
        phase25_headings = [line for line in content.splitlines() if "## Phase 25" in line]
        self.assertEqual(
            len(phase25_headings),
            3,
            f"Expected exactly 3 '## Phase 25' headings, found {len(phase25_headings)}: {phase25_headings}",
        )


# ===========================================================================
# Phase 210 (XSURF-01/XSURF-02, D-01/D-05/D-08): evaluate_identity_endpoints()
# ===========================================================================

class TestEvaluateIdentityEndpointsDedupe(unittest.TestCase):
    """Behavioral contract for the shared evaluator's `(host, port, serial)`
    dedupe (XSURF-01) plus D-08's three-branch extraction (XSURF-02).
    """

    def _weak_saml_ep(self, use: str, serial: str, host: str = "10.80.0.41", port: int = 8080) -> _Ep:
        return _Ep(
            host=host,
            port=port,
            protocol="SAML",
            cert_pubkey_alg="RSA",
            cert_pubkey_size=1024,
            service_detail=f"urn:x|use={use}|serial={serial}",
        )

    def test_dual_use_same_serial_collapses_to_one_critical(self) -> None:
        """XSURF-01: one certificate published under both `use=signing` and
        `use=encryption` with the SAME serial yields exactly ONE finding."""
        endpoints = [
            self._weak_saml_ep("signing", "0a1b"),
            self._weak_saml_ep("encryption", "0a1b"),
        ]
        results = evaluate_identity_endpoints(endpoints)
        self.assertEqual(len(results), 1, f"Expected 1 finding, got {results}")
        self.assertEqual(results[0]["severity"], "CRITICAL")

    def test_distinct_serials_yield_two_findings(self) -> None:
        """The dedupe-falsifying case (T-210-02-01): a dedupe keyed on
        (host, port) alone, or on `use`, or an unconditional collapse, all
        fail this assertion. Two DISTINCT certificates must never collapse.

        Node id: this is the test that would FAIL if the dedupe were
        widened to `(host, port)` — see SUMMARY for the exact node id quoted
        back from this file.
        """
        endpoints = [
            self._weak_saml_ep("signing", "0a1b"),
            self._weak_saml_ep("encryption", "0a1c"),
        ]
        results = evaluate_identity_endpoints(endpoints)
        self.assertEqual(len(results), 2, f"Expected 2 findings for distinct serials, got {results}")

    def test_same_serial_different_host_yields_two_findings(self) -> None:
        endpoints = [
            self._weak_saml_ep("signing", "0a1b", host="10.80.0.41"),
            self._weak_saml_ep("encryption", "0a1b", host="10.80.0.42"),
        ]
        results = evaluate_identity_endpoints(endpoints)
        self.assertEqual(len(results), 2, f"Expected 2 findings for different hosts, got {results}")

    def test_same_serial_different_port_yields_two_findings(self) -> None:
        endpoints = [
            self._weak_saml_ep("signing", "0a1b", port=8080),
            self._weak_saml_ep("encryption", "0a1b", port=8443),
        ]
        results = evaluate_identity_endpoints(endpoints)
        self.assertEqual(len(results), 2, f"Expected 2 findings for different ports, got {results}")

    def test_missing_serial_token_never_deduped(self) -> None:
        """A row whose `service_detail` carries no `serial=` token at all is
        NOT deduped away against another absent-serial row — absent serial
        must never be treated as "same as another absent serial"."""
        endpoints = [
            _Ep(host="10.80.0.41", port=8080, protocol="SAML",
                cert_pubkey_alg="RSA", cert_pubkey_size=1024,
                service_detail="urn:x|use=signing"),
            _Ep(host="10.80.0.41", port=8080, protocol="SAML",
                cert_pubkey_alg="RSA", cert_pubkey_size=1024,
                service_detail="urn:x|use=encryption"),
        ]
        results = evaluate_identity_endpoints(endpoints)
        self.assertEqual(len(results), 2, f"Expected 2 findings when serial is absent, got {results}")

    def test_oidc_rs_family_branch_extracted(self) -> None:
        endpoints = [
            _Ep(host="auth.example.com", port=443, protocol="SAML",
                cert_pubkey_alg="RS256", cert_pubkey_size=None,
                service_detail="oidc-discovery|https://auth.example.com/.well-known/openid-configuration"),
        ]
        results = evaluate_identity_endpoints(endpoints)
        self.assertEqual(len(results), 1)
        self.assertIn("OIDC RS-family algorithm: RS256", results[0]["title"])
        self.assertEqual(results[0]["protocol"], "SAML")
        self.assertEqual(results[0]["source"], "saml")
        self.assertEqual(results[0]["algorithm"], "RS256")

    def test_sha1_branch_extracted_mixed_case(self) -> None:
        endpoints = [
            _Ep(host="idp.example.com", port=443, protocol="SAML",
                cert_pubkey_alg="sha1", cert_pubkey_size=None,
                service_detail="https://idp.example.com|algo_uri=...sha1"),
        ]
        results = evaluate_identity_endpoints(endpoints)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "SHA-1 algorithm URI detected in SAML metadata")
        self.assertEqual(results[0]["source"], "saml")

    def test_every_finding_has_protocol_source_algorithm(self) -> None:
        endpoints = [
            self._weak_saml_ep("signing", "0a1b"),
            _Ep(host="auth.example.com", port=443, protocol="SAML",
                cert_pubkey_alg="RS256", cert_pubkey_size=None,
                service_detail="oidc-discovery|..."),
        ]
        results = evaluate_identity_endpoints(endpoints)
        self.assertEqual(len(results), 2)
        for f in results:
            self.assertTrue(f.get("protocol"))
            self.assertTrue(f.get("source"))
            self.assertTrue(f.get("algorithm"))


if __name__ == "__main__":
    unittest.main()
