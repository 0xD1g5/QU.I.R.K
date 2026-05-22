"""Regression test: build_cbom emits a quantum-safe KEM algorithm component for
X25519MLKEM768 hybrid endpoints (Phase 90 gap-closure).

Root cause: _KEX_MAP in quirk/cbom/builder.py lacked an entry for the bare hybrid
NamedGroup-4588 name "X25519MLKEM768" (no _WITH_ separator, not a TLS 1.3 suite).
_decompose_cipher_suite("X25519MLKEM768") returned [] — the classifier alias
'x25519mlkem768' was never reached from the builder's TLS cipher_suite path.

This test must FAIL without the _KEX_MAP entry and PASS with it.
"""
from __future__ import annotations

import pytest

from quirk.cbom.builder import build_cbom, _decompose_cipher_suite
from quirk.cbom.classifier import classify_algorithm, CryptoPrimitive
from quirk.models import CryptoEndpoint

try:
    from cyclonedx.model.crypto import CryptoAssetType
except ImportError:  # pragma: no cover
    CryptoAssetType = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Unit-level: _decompose_cipher_suite
# ---------------------------------------------------------------------------

class TestDecomposeCipherSuiteX25519MLKEM768:
    """_decompose_cipher_suite must return the bare hybrid group name as a single token."""

    def test_returns_nonempty_list(self):
        result = _decompose_cipher_suite("X25519MLKEM768")
        assert result, "_decompose_cipher_suite('X25519MLKEM768') must not return []"

    def test_returns_x25519mlkem768_token(self):
        result = _decompose_cipher_suite("X25519MLKEM768")
        assert "X25519MLKEM768" in result

    def test_no_side_effect_on_classical_suite(self):
        """Adding X25519MLKEM768 to _KEX_MAP must not change decomposition of a classical suite."""
        result = _decompose_cipher_suite("TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384")
        assert "X25519" in result
        assert "RSA" in result
        assert "AES-256-GCM" in result

    def test_no_side_effect_on_tls13_suite(self):
        """TLS 1.3 suite decomposition must be unaffected."""
        result = _decompose_cipher_suite("TLS_AES_256_GCM_SHA384")
        assert "AES-256-GCM" in result


# ---------------------------------------------------------------------------
# Integration-level: build_cbom
# ---------------------------------------------------------------------------

def _make_pqc_endpoint() -> CryptoEndpoint:
    """Mirror the endpoint shape produced by _run_pqc_phase in run_scan.py."""
    return CryptoEndpoint(
        host="pqc.example.com",
        port=39444,
        protocol="TLS",
        cipher_suite="X25519MLKEM768",
        service_detail="pqc-hybrid-detected|group=X25519MLKEM768",
    )


class TestBuildCbomPqcHybridKem:
    """build_cbom must emit a quantum-safe KEM ALGORITHM component for X25519MLKEM768."""

    @pytest.fixture(autouse=True)
    def _bom(self):
        ep = _make_pqc_endpoint()
        self.bom = build_cbom([ep])
        self.components = list(self.bom.components)

    def _algorithm_components(self):
        if CryptoAssetType is None:  # pragma: no cover
            return []
        return [
            c for c in self.components
            if c.crypto_properties
            and c.crypto_properties.asset_type == CryptoAssetType.ALGORITHM
        ]

    def test_at_least_one_algorithm_component(self):
        assert self._algorithm_components(), (
            "build_cbom([X25519MLKEM768 endpoint]) must produce at least one ALGORITHM component"
        )

    def test_algorithm_component_named_x25519mlkem768(self):
        names = [c.name for c in self._algorithm_components()]
        assert "X25519MLKEM768" in names, (
            f"Expected 'X25519MLKEM768' in algorithm components; got {names}"
        )

    def test_algorithm_primitive_is_kem(self):
        alg = next(
            c for c in self._algorithm_components()
            if c.name == "X25519MLKEM768"
        )
        prim = alg.crypto_properties.algorithm_properties.primitive
        assert prim == CryptoPrimitive.KEM, (
            f"Expected KEM primitive; got {prim}"
        )

    def test_algorithm_nist_level_is_3(self):
        alg = next(
            c for c in self._algorithm_components()
            if c.name == "X25519MLKEM768"
        )
        level = alg.crypto_properties.algorithm_properties.nist_quantum_security_level
        assert level == 3, f"Expected NIST level 3 (L3); got {level}"

    def test_fips_status_property_is_approved(self):
        """nist_level=3 => quirk:fips140-3-status must be 'approved'."""
        alg = next(
            c for c in self._algorithm_components()
            if c.name == "X25519MLKEM768"
        )
        props = {p.name: p.value for p in (alg.properties or [])}
        assert props.get("quirk:fips140-3-status") == "approved", (
            f"Expected 'approved' fips status; got {props.get('quirk:fips140-3-status')}"
        )

    def test_protocol_service_component_also_present(self):
        """The PROTOCOL-type service component must still be emitted alongside the KEM."""
        if CryptoAssetType is None:  # pragma: no cover
            return
        protocol_components = [
            c for c in self.components
            if c.crypto_properties
            and c.crypto_properties.asset_type == CryptoAssetType.PROTOCOL
        ]
        assert protocol_components, "Protocol service component must still be emitted"

    def test_total_component_count_is_exactly_two(self):
        """Endpoint with only cipher_suite (no cert fields) → exactly 2 components: KEM + PROTOCOL."""
        assert len(self.components) == 2, (
            f"Expected 2 components (1 algorithm + 1 protocol); got {len(self.components)}"
        )
