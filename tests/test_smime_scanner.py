"""Phase 79 Plan 04 — Unit tests for quirk/scanner/smime_scanner.py.

Mocks the LDAP bind+paged-search layer by patching
`quirk.scanner.smime_scanner._bind_and_search` to return a synthetic
iterable of searchResEntry dicts carrying our pre-built DER fixtures.

Asserts the contract from Phase 79 Plan 79-02:

  - alice.der (RSA-1024 SHA-1)  -> HIGH, reasons include both
                                   `weak-signing-alg` AND `weak-rsa-key`.
  - bob.der   (RSA-1024 SHA-256) -> HIGH, reasons include `weak-rsa-key`
                                   and NOT `weak-signing-alg`.
  - carol.der (RSA-2048 SHA-256) -> SAFE, zero endpoints emitted.

Every emitted CryptoEndpoint must carry `protocol="SMIME"` and a
populated `smime_scan_json` (SMIME-01 / SMIME-02 / SMIME-05 / SMIME-06).
"""
from __future__ import annotations

import json
import pathlib
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from quirk.scanner import smime_scanner
from quirk.scanner.smime_scanner import scan_smime_targets


FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures" / "smime"


def _load(name: str) -> bytes:
    return (FIXTURE_DIR / name).read_bytes()


def _entry(uid: str, der: bytes, attr: str = "userSMIMECertificate") -> dict:
    """Build a fake ldap3 searchResEntry dict matching what
    `paged_search(... generator=True)` yields."""
    return {
        "type": "searchResEntry",
        "dn": f"uid={uid},ou=people,dc=quirk,dc=lab",
        "raw_attributes": {
            attr: [der],
            "cn": [uid.encode()],
            "uid": [uid.encode()],
        },
    }


def _target() -> SimpleNamespace:
    return SimpleNamespace(host="smime-openldap", port=38900, realm="QUIRK.LAB")


def _run_with_entries(entries: list[dict]) -> list:
    """Call scan_smime_targets with _bind_and_search patched to yield
    the supplied entries. Also forces LDAP3_AVAILABLE=True so the test
    suite runs in environments where the optional `ldap3` dep isn't
    installed (the `[identity]` extra)."""
    with patch.object(smime_scanner, "LDAP3_AVAILABLE", True), \
         patch.object(smime_scanner, "_bind_and_search", return_value=iter(entries)):
        return scan_smime_targets([_target()], timeout=5)


# ---------------------------------------------------------------------------
# Per-fixture contract assertions
# ---------------------------------------------------------------------------

def test_alice_rsa1024_sha1_emits_high_with_two_reasons():
    """alice (RSA-1024 SHA-1) → HIGH with both weak-signing-alg and
    weak-rsa-key reasons."""
    eps = _run_with_entries([_entry("alice", _load("alice.der"))])
    assert len(eps) == 1, f"expected 1 endpoint, got {len(eps)}"
    ep = eps[0]
    assert ep.protocol == "SMIME"
    assert ep.severity == "HIGH"
    assert ep.cert_pubkey_alg == "RSA"
    assert ep.cert_pubkey_size == 1024
    assert ep.smime_scan_json, "smime_scan_json must be populated"
    blob = json.loads(ep.smime_scan_json)
    assert "weak-signing-alg" in blob["reasons"]
    assert "weak-rsa-key" in blob["reasons"]


def test_bob_rsa1024_sha256_emits_high_weak_key_only():
    """bob (RSA-1024 SHA-256) → HIGH with weak-rsa-key only (no
    weak-signing-alg since SHA-256 is not weak)."""
    eps = _run_with_entries([_entry("bob", _load("bob.der"))])
    assert len(eps) == 1, f"expected 1 endpoint, got {len(eps)}"
    ep = eps[0]
    assert ep.protocol == "SMIME"
    assert ep.severity == "HIGH"
    assert ep.cert_pubkey_alg == "RSA"
    assert ep.cert_pubkey_size == 1024
    assert ep.smime_scan_json, "smime_scan_json must be populated"
    blob = json.loads(ep.smime_scan_json)
    assert "weak-rsa-key" in blob["reasons"]
    assert "weak-signing-alg" not in blob["reasons"]


def test_carol_rsa2048_sha256_emits_zero_endpoints():
    """carol (RSA-2048 SHA-256) → SAFE, no finding emitted."""
    eps = _run_with_entries([_entry("carol", _load("carol.der"))])
    assert eps == [], f"expected zero endpoints for SAFE cert, got {len(eps)}"


def test_three_fixtures_together_produce_two_high_findings():
    """All three users in one paged search: alice + bob HIGH, carol
    suppressed. End-to-end multi-entry assertion."""
    eps = _run_with_entries(
        [
            _entry("alice", _load("alice.der")),
            _entry("bob", _load("bob.der")),
            _entry("carol", _load("carol.der")),
        ]
    )
    assert len(eps) == 2
    assert {ep.protocol for ep in eps} == {"SMIME"}
    assert {ep.severity for ep in eps} == {"HIGH"}
    # Every emitted endpoint has a populated smime_scan_json
    for ep in eps:
        assert ep.smime_scan_json
        assert json.loads(ep.smime_scan_json)["reasons"]


def test_user_certificate_attribute_also_picked_up():
    """SMIME-01 says BOTH `userCertificate` AND `userSMIMECertificate`
    must be enumerated. Verify the legacy attribute path classifies."""
    eps = _run_with_entries(
        [_entry("alice", _load("alice.der"), attr="userCertificate")]
    )
    assert len(eps) == 1
    assert eps[0].protocol == "SMIME"
    assert eps[0].severity == "HIGH"


def test_no_entries_yields_no_endpoints():
    """Empty paged_search result → zero findings, no crash."""
    eps = _run_with_entries([])
    assert eps == []
