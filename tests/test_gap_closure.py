"""Regression tests for MISMATCH-01 gap closure.

MISMATCH-01: quantum_safety_label() receives a raw algorithm string instead of
the integer NIST level in two call sites in scan.py. These tests confirm the
correct behaviour:
  - _derive_findings produces "Vulnerable" for DSA and ECDSA certificates
  - _cert_quantum_safety returns display labels ("Vulnerable", "Safe") not raw
    enum strings ("quantum-vulnerable", "quantum-safe")
"""
from __future__ import annotations

import types


def _make_endpoint(**kwargs):
    """Create a minimal mock CryptoEndpoint using SimpleNamespace."""
    defaults = dict(
        id=1,
        host="test.example.com",
        port=443,
        protocol="TLS",
        cert_pubkey_alg=None,
        cert_pubkey_size=2048,
        tls_version=None,
        cipher_suite=None,
        ssh_host_key_alg=None,
        ssh_kex_alg=None,
        ssh_mac_alg=None,
        ssh_audit_json=None,
        tls_capabilities_json=None,
        api_algorithm=None,
        container_algorithm=None,
        source_algorithm=None,
        cloud_algorithm=None,
        scan_ts=None,
        # Additional fields used by _derive_findings
        tls_weak_ciphers_present=False,
        cert_not_after=None,
        jwt_scan_json=None,
        cloud_scan_json=None,
    )
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def test_findings_quantum_label_dsa():
    """MISMATCH-01: _derive_findings with DSA cert produces finding with quantum_risk='Vulnerable'."""
    from quirk.dashboard.api.routes.scan import _derive_findings

    ep = _make_endpoint(cert_pubkey_alg="DSA")
    findings = _derive_findings([ep])

    quantum_findings = [f for f in findings if f.quantum_risk == "Vulnerable"]
    assert len(quantum_findings) >= 1, (
        f"Expected at least one Vulnerable finding for DSA, got: {[f.quantum_risk for f in findings]}"
    )
    assert any("Quantum-vulnerable" in f.title for f in quantum_findings), (
        f"Expected title containing 'Quantum-vulnerable', got titles: {[f.title for f in quantum_findings]}"
    )


def test_findings_quantum_label_ecdsa():
    """MISMATCH-01: _derive_findings with ECDSA cert produces finding with quantum_risk='Vulnerable'."""
    from quirk.dashboard.api.routes.scan import _derive_findings

    ep = _make_endpoint(cert_pubkey_alg="ECDSA")
    findings = _derive_findings([ep])

    quantum_findings = [f for f in findings if f.quantum_risk == "Vulnerable"]
    assert len(quantum_findings) >= 1, (
        f"Expected at least one Vulnerable finding for ECDSA, got: {[f.quantum_risk for f in findings]}"
    )
    assert any("Quantum-vulnerable" in f.title for f in quantum_findings), (
        f"Expected title containing 'Quantum-vulnerable', got titles: {[f.title for f in quantum_findings]}"
    )


def test_cert_quantum_safety_display_label():
    """MISMATCH-01: _cert_quantum_safety('RSA') returns 'Vulnerable' (display label, not raw enum)."""
    from quirk.dashboard.api.routes.scan import _cert_quantum_safety

    result = _cert_quantum_safety("RSA")
    assert result == "Vulnerable", (
        f"Expected 'Vulnerable' for RSA, got: {result!r}"
    )


def test_cert_quantum_safety_pqc_safe():
    """MISMATCH-01: _cert_quantum_safety('ML-KEM-768') returns 'Safe'."""
    from quirk.dashboard.api.routes.scan import _cert_quantum_safety

    result = _cert_quantum_safety("ML-KEM-768")
    assert result == "Safe", (
        f"Expected 'Safe' for ML-KEM-768, got: {result!r}"
    )
