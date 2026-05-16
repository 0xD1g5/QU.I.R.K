"""Phase 80 ADCS-09 — Read-only runtime invariant test.

The AD CS scanner MUST perform read-only LDAP enumeration and MUST NEVER
construct a certificate signing request. This test enforces the runtime
arm of that contract (the static arm is `tests/test_adcs_ast_gate.py`):

  1. `scan_adcs_targets` never calls `conn.add` / `conn.modify` /
     `conn.delete` / `conn.modify_dn` on the ldap3 connection (the four
     mutating LDAP methods).
  2. `scan_adcs_targets` never instantiates
     `cryptography.x509.CertificateSigningRequestBuilder` (the only
     way the library generates new CSRs — every enrollment-style
     misuse goes through this builder).

The MagicMock-based approach catches drift that an AST gate misses:
imports that hide behind feature flags, lazy imports, or
`getattr(conn, "ad" + "d")` obfuscation.
"""
from __future__ import annotations

import json
import pathlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import cryptography.x509 as _x509  # for monkeypatch target
from quirk.scanner import adcs_scanner
from quirk.scanner.adcs_scanner import scan_adcs_targets


FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures" / "adcs"


class _FakeLDAPBindError(Exception):
    pass


def _fake_ldap3_module() -> SimpleNamespace:
    fake = SimpleNamespace()
    fake.SUBTREE = "SUBTREE"
    fake.ALL = "ALL"
    fake.SIMPLE = "SIMPLE"
    fake.ANONYMOUS = "ANONYMOUS"
    fake.core = SimpleNamespace(
        exceptions=SimpleNamespace(LDAPBindError=_FakeLDAPBindError)
    )
    return fake


def _ca_entry() -> dict:
    der = (FIXTURE_DIR / "ca-weak.der").read_bytes()
    return {
        "type": "searchResEntry",
        "dn": "CN=QuirkLabCA,...",
        "raw_attributes": {
            "cn": [b"QuirkLabCA"],
            "cACertificate": [der],
        },
    }


def _templates() -> list[dict]:
    return json.loads((FIXTURE_DIR / "templates.json").read_text())


def _mock_conn() -> MagicMock:
    mc = MagicMock(name="ldap3.Connection")
    mc.extend.standard.paged_search.side_effect = [
        iter([_ca_entry()]),
        iter(_templates()),
    ]
    mc.unbind.return_value = None
    return mc


def _target() -> SimpleNamespace:
    return SimpleNamespace(host="adcs-openldap", port=38910, realm="QUIRK.LAB")


# ---------------------------------------------------------------------------
# ADCS-09 runtime invariant — no LDAP write methods called
# ---------------------------------------------------------------------------

def test_scanner_never_calls_ldap_write_methods() -> None:
    """A full ADCS scan against the chaos lab fixtures must NEVER
    invoke conn.add / conn.modify / conn.delete / conn.modify_dn on
    the ldap3 Connection. ADCS-09 runtime arm."""
    mc = _mock_conn()
    with patch.object(adcs_scanner, "LDAP3_AVAILABLE", True), \
         patch.object(adcs_scanner, "ldap3", _fake_ldap3_module(), create=True), \
         patch.object(
             adcs_scanner, "_bind_and_query",
             return_value=(mc, "CN=Configuration,DC=quirk,DC=lab"),
         ):
        eps = scan_adcs_targets([_target()], timeout=5)

    # Sanity: the scan actually emitted findings — otherwise this test
    # could vacuously pass on a no-op execution.
    assert eps, "scan emitted zero findings — test setup broken"

    mc.add.assert_not_called()
    mc.modify.assert_not_called()
    mc.delete.assert_not_called()
    mc.modify_dn.assert_not_called()


def test_scanner_never_instantiates_csr_builder(monkeypatch) -> None:
    """Patch `cryptography.x509.CertificateSigningRequestBuilder` with a
    sentinel whose construction raises AssertionError. Run a full scan.
    If any code path in adcs_scanner constructs a CSR builder (including
    a future drift adding `if foo: CertificateSigningRequestBuilder(...)`
    behind a flag), the AssertionError surfaces and fails this test."""

    def _forbidden(*args, **kwargs):
        raise AssertionError(
            "ADCS-09 violation: CertificateSigningRequestBuilder() "
            "called from inside scan_adcs_targets — enrollment forbidden."
        )

    # Patch the symbol on the cryptography.x509 module itself so even a
    # late `from cryptography.x509 import CertificateSigningRequestBuilder`
    # at function scope would resolve to our sentinel. The scanner's
    # top-level imports do NOT include this name (verified by the AST
    # gate); this sentinel catches dynamic / runtime-imported drift.
    monkeypatch.setattr(
        _x509, "CertificateSigningRequestBuilder", _forbidden, raising=True,
    )

    mc = _mock_conn()
    with patch.object(adcs_scanner, "LDAP3_AVAILABLE", True), \
         patch.object(adcs_scanner, "ldap3", _fake_ldap3_module(), create=True), \
         patch.object(
             adcs_scanner, "_bind_and_query",
             return_value=(mc, "CN=Configuration,DC=quirk,DC=lab"),
         ):
        # Full scan over the full fixture set — if CSR builder is ever
        # constructed, the monkeypatch raises AssertionError and pytest
        # reports it as a test failure.
        eps = scan_adcs_targets([_target()], timeout=5)

    # Belt-and-braces: scan returned findings and zero AssertionErrors leaked.
    assert eps, "scan emitted zero findings — test setup broken"
