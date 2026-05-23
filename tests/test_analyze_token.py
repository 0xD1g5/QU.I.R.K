"""Unit tests for quirk analyze-token command (TOKEN-01, TOKEN-02, TOKEN-03).

Phase 94 / Plan 01 — TDD RED phase.
"""
from __future__ import annotations

import base64
import json
import sys
from io import StringIO
from unittest import mock

import pytest


# ---------------------------------------------------------------------------
# Test JWT token builder helpers
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    """Standard base64url encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_jwt(header: dict, payload: dict, signature: str = "fakesig") -> str:
    """Build a hand-crafted JWT with the given header and payload (unsigned)."""
    h = _b64url_encode(json.dumps(header).encode())
    p = _b64url_encode(json.dumps(payload).encode())
    s = _b64url_encode(signature.encode())
    return f"{h}.{p}.{s}"


# Standard RS256 JWT with future expiry
RS256_JWT = _make_jwt(
    {"alg": "RS256", "typ": "JWT"},
    {"sub": "1234567890", "name": "Test User", "exp": 9999999999},
)

# alg:none JWT variants
ALG_NONE_JWT_lower = _make_jwt({"alg": "none", "typ": "JWT"}, {"sub": "test"}, "")
ALG_NONE_JWT_UPPER = _make_jwt({"alg": "NONE", "typ": "JWT"}, {"sub": "test"}, "")
ALG_NONE_JWT_Mixed = _make_jwt({"alg": "None", "typ": "JWT"}, {"sub": "test"}, "")
ALG_NONE_JWT_NonE = _make_jwt({"alg": "NonE", "typ": "JWT"}, {"sub": "test"}, "")

# Opaque (non-JWT) token
OPAQUE_TOKEN = "ya29.A0ARrdaM-opaque-oauth-token-not-a-jwt"


# ---------------------------------------------------------------------------
# Task 1 — Token analyzer command tests (TOKEN-01, TOKEN-03)
# ---------------------------------------------------------------------------

class TestDecodeRS256Token:
    """TOKEN-01: Decode RS256 JWT and report algorithm, nist_level, quantum_safety."""

    def test_decode_rs256_token(self, capsys):
        from quirk.cli.analyze_token_cmd import run_analyze_token

        with pytest.raises(SystemExit) as exc_info:
            run_analyze_token([RS256_JWT])
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        out = captured.out
        assert "RS256" in out
        # Quantum safety should be present
        assert "quantum" in out.lower() or "nist" in out.lower()

    def test_json_flag(self, capsys):
        """--json emits machine-readable dict with required keys."""
        from quirk.cli.analyze_token_cmd import run_analyze_token

        with pytest.raises(SystemExit) as exc_info:
            run_analyze_token(["--json", RS256_JWT])
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "alg" in data
        assert "is_alg_none" in data
        assert "expired" in data
        assert "nist_level" in data
        assert "quantum_safety" in data
        assert data["alg"] == "RS256"
        assert data["is_alg_none"] is False


class TestOpaquTokenGraceful:
    """TOKEN-01: Opaque (non-JWT) token reports INFO and exits 0."""

    def test_opaque_token_graceful(self, capsys):
        from quirk.cli.analyze_token_cmd import run_analyze_token

        with pytest.raises(SystemExit) as exc_info:
            run_analyze_token([OPAQUE_TOKEN])
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        out = captured.out.lower()
        assert "opaque" in out


class TestAlgNoneCritical:
    """TOKEN-03: alg:none variants must print CRITICAL and exit 1."""

    @pytest.mark.parametrize("token,alg_variant", [
        (ALG_NONE_JWT_lower, "none"),
        (ALG_NONE_JWT_UPPER, "NONE"),
        (ALG_NONE_JWT_Mixed, "None"),
        (ALG_NONE_JWT_NonE, "NonE"),
    ])
    def test_alg_none_critical(self, token, alg_variant, capsys):
        from quirk.cli.analyze_token_cmd import run_analyze_token

        with pytest.raises(SystemExit) as exc_info:
            run_analyze_token([token])
        assert exc_info.value.code == 1, (
            f"Expected exit code 1 for alg:{alg_variant!r} token"
        )

        captured = capsys.readouterr()
        out = captured.out.upper()
        assert "CRITICAL" in out, (
            f"Expected 'CRITICAL' in output for alg:{alg_variant!r} token"
        )


class TestTokenValueNotEchoed:
    """T-94-02: Raw token string must never appear in captured stdout."""

    def test_token_value_not_echoed_rs256(self, capsys):
        from quirk.cli.analyze_token_cmd import run_analyze_token

        with pytest.raises(SystemExit):
            run_analyze_token([RS256_JWT])

        captured = capsys.readouterr()
        # The JWT is a long base64url string; its first segment must not appear verbatim
        token_header_part = RS256_JWT.split(".")[0]
        assert token_header_part not in captured.out, (
            "Raw token value (first JWT segment) leaked into stdout"
        )

    def test_token_value_not_echoed_none(self, capsys):
        from quirk.cli.analyze_token_cmd import run_analyze_token

        with pytest.raises(SystemExit):
            run_analyze_token([ALG_NONE_JWT_lower])

        captured = capsys.readouterr()
        # The raw token must not appear verbatim
        token_header_part = ALG_NONE_JWT_lower.split(".")[0]
        assert token_header_part not in captured.out, (
            "Raw token value (first JWT segment) leaked into stdout for alg:none"
        )


# ---------------------------------------------------------------------------
# Task 2 — CBOM BEARER_TOKEN branch tests (TOKEN-02)
# ---------------------------------------------------------------------------

class TestCbomBearerClassification:
    """TOKEN-02: CryptoEndpoint(protocol='BEARER_TOKEN', cert_pubkey_alg='RS256')
    produces a CBOM algorithm component with declared_algorithm (unverified) label."""

    def _make_bearer_endpoint(self, alg: str = "RS256", key_size: int | None = None):
        """Build a minimal CryptoEndpoint stub for BEARER_TOKEN protocol."""
        from datetime import datetime

        class FakeEndpoint:
            protocol = "BEARER_TOKEN"
            cert_pubkey_alg = alg
            cert_pubkey_size = key_size
            host = "scan-target"
            port = 0
            service_detail = "declared_algorithm (unverified)"
            tls_version = None
            cipher_suite = None
            cert_not_after = None
            cert_not_before = None
            cert_subject = None
            cert_issuer = None
            cert_sig_alg = None
            cert_serial = None
            cert_fingerprint_sha256 = None
            scan_error = None
            tls_blocker_reason = None
            cert_key_type = None
            cloud_scan_json = None
            tls_supported_versions = None
            tls_supported_ciphers_sample = None
            ssh_audit_json = None
            severity = "MEDIUM"
            scanned_at = datetime(2026, 5, 22, 12, 0, 0)

        return FakeEndpoint()

    def test_cbom_bearer_classification(self):
        """CBOM build includes a component for BEARER_TOKEN protocol."""
        from quirk.cbom.builder import build_cbom

        ep = self._make_bearer_endpoint("RS256")
        bom = build_cbom([ep])
        # The BOM should have at least one component
        components = list(bom.components)
        assert len(components) > 0, "Expected at least one CBOM component for BEARER_TOKEN endpoint"

        # At least one component should relate to RS256
        component_names = [c.name for c in components if c.name]
        alg_names_upper = [n.upper() for n in component_names]
        assert any("RS256" in n or "RSA" in n for n in alg_names_upper), (
            f"Expected RS256/RSA algorithm component, got: {component_names}"
        )

    def test_cbom_bearer_coverage_note(self):
        """CBOM root component carries bearer-token-declared-algorithm coverage note."""
        from quirk.cbom.builder import build_cbom

        ep = self._make_bearer_endpoint("RS256")
        bom = build_cbom([ep])

        # Check root component properties for coverage note
        root_component = bom.metadata.component if bom.metadata else None
        assert root_component is not None, "BOM must have a root component"

        props = list(root_component.properties or [])
        prop_values = [p.value for p in props if p.name == "quirk:coverage-note"]
        assert any("bearer-token-declared-algorithm" in v for v in prop_values), (
            f"Expected 'bearer-token-declared-algorithm' in coverage notes, got: {prop_values}"
        )

    def test_cbom_bearer_never_enforced(self):
        """CBOM bearer component must not be flagged as enforced."""
        from quirk.cbom.builder import build_cbom

        ep = self._make_bearer_endpoint("RS256")
        bom = build_cbom([ep])

        components = list(bom.components)
        for comp in components:
            props = list(comp.properties or [])
            for prop in props:
                assert "enforced" not in (prop.value or "").lower() or "unverified" in (prop.value or "").lower(), (
                    f"Component {comp.name!r} property {prop.name!r}={prop.value!r} "
                    "must not be marked enforced without unverified caveat"
                )
