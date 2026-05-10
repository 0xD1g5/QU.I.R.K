"""VAULT CBOM golden snapshot — Phase 61 CBOM-COVER-02 / D-02.

Asserts that the sorted list of (component.name, str(component.type)) tuples
emitted by build_cbom() for 3 deterministic VAULT endpoints is byte-identical
across runs. The full CycloneDX JSON is not snapshotted because UUIDs and
serialNumber are non-deterministic; the (name, type) tuple list captures the
structural commitment without the volatile fields.

Regenerate fixture: REGEN_CBOM_FIXTURES=1 pytest tests/test_cbom_vault_consistency.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from quirk.cbom.builder import build_cbom
from quirk.models import CryptoEndpoint

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "cbom" / "cbom_vault_golden.json"


def _build_vault_endpoints():
    """Three deterministic VAULT endpoints exercising distinct transit key types."""
    common = dict(
        port=8200, protocol="VAULT",
        tls_version=None, cipher_suite=None,
        cert_sig_alg=None, cert_subject=None, cert_issuer=None,
        cert_not_before=None, cert_not_after=None,
        tls_capabilities_json=None, ssh_audit_json=None,
        service_detail=None,
    )
    return [
        CryptoEndpoint(host="vault-rsa", cert_pubkey_alg="rsa-2048", cert_pubkey_size=2048, **common),
        CryptoEndpoint(host="vault-aes", cert_pubkey_alg="aes256-gcm96", cert_pubkey_size=256, **common),
        CryptoEndpoint(host="vault-ed", cert_pubkey_alg="ed25519", cert_pubkey_size=None, **common),
    ]


def _vault_snapshot_key(bom):
    """Return sorted (name, str(type)) tuples — stable across UUID/serialNumber churn."""
    return sorted(
        [c.name, str(c.type)]
        for c in bom.components
    )


@pytest.mark.skipif(
    os.environ.get("REGEN_CBOM_FIXTURES") != "1",
    reason="set REGEN_CBOM_FIXTURES=1 to regenerate the vault golden fixture",
)
def test_regenerate_vault_golden():
    bom = build_cbom(_build_vault_endpoints())
    snap = _vault_snapshot_key(bom)
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(snap, indent=2, sort_keys=True) + "\n")


def test_vault_cbom_matches_snapshot():
    bom = build_cbom(_build_vault_endpoints())
    actual = _vault_snapshot_key(bom)
    assert FIXTURE_PATH.exists(), (
        f"Fixture {FIXTURE_PATH} missing. Generate it with: "
        f"REGEN_CBOM_FIXTURES=1 pytest tests/test_cbom_vault_consistency.py"
    )
    expected = json.loads(FIXTURE_PATH.read_text())
    assert actual == expected, (
        "VAULT CBOM diverged from golden snapshot. If this change is "
        "intentional, regenerate with: "
        "REGEN_CBOM_FIXTURES=1 pytest tests/test_cbom_vault_consistency.py"
    )
