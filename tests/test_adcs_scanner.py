"""Phase 80 Plan 04 — Unit tests for quirk/scanner/adcs_scanner.py.

Patches `quirk.scanner.adcs_scanner._bind_and_query` to return a MagicMock
`ldap3.Connection` whose `.extend.standard.paged_search` yields canned
searchResEntry dicts from `tests/fixtures/adcs/templates.json` plus a CA
entry built from `tests/fixtures/adcs/ca-weak.der`.

Asserts the contract from Phase 80 Plan 02 (commit 73f92e0):

  - BadTemplate-ESC1 (NameFlag=1, EKU=client-auth, RA-Sig=0) -> 1 ESC1 HIGH
  - BadTemplate-ESC4 (NameFlag=0, nTSecurityDescriptor)       -> 0 misconfig
  - SafeTemplate (NameFlag=0, EKU=email-protection)           -> 0
  - Weak CA cert (RSA-1024 SHA-1)                              -> 1 HIGH
  - Per target: exactly 4 LOW COVERAGE-GAP (ESC4/5/7/8) per D-80-R8

Plus an ADCS-UNREACH case (ADCS-04 SC#2): bind failure -> exactly one LOW
finding, scan_error_category="exception", no exception propagation.
"""
from __future__ import annotations

import json
import pathlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from quirk.scanner import adcs_scanner
from quirk.scanner.adcs_scanner import scan_adcs_targets


FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures" / "adcs"


class _FakeLDAPBindError(Exception):
    """Stand-in for ldap3.core.exceptions.LDAPBindError when ldap3 is
    not installed in the test environment (base CI runs without the
    [adcs] / [identity] extras)."""


def _fake_ldap3_module() -> SimpleNamespace:
    """Minimal ldap3 stub providing the symbols `adcs_scanner` accesses
    at runtime (SUBTREE constant + nested core.exceptions.LDAPBindError).
    Server / Connection / ALL / SIMPLE / ANONYMOUS aren't touched in
    the test paths (we patch _bind_and_query directly)."""
    fake = SimpleNamespace()
    fake.SUBTREE = "SUBTREE"
    fake.ALL = "ALL"
    fake.SIMPLE = "SIMPLE"
    fake.ANONYMOUS = "ANONYMOUS"
    fake.core = SimpleNamespace(
        exceptions=SimpleNamespace(LDAPBindError=_FakeLDAPBindError)
    )
    return fake


def _load_templates() -> list[dict]:
    return json.loads((FIXTURE_DIR / "templates.json").read_text())


def _ca_entry() -> dict:
    """Build a searchResEntry dict carrying the weak CA cert DER as
    `raw_attributes['cACertificate']` per the scanner's contract.
    """
    der = (FIXTURE_DIR / "ca-weak.der").read_bytes()
    return {
        "type": "searchResEntry",
        "dn": "CN=QuirkLabCA,CN=Enrollment Services,CN=Public Key Services,CN=Services,CN=Configuration,DC=quirk,DC=lab",
        "raw_attributes": {
            "cn": [b"QuirkLabCA"],
            "cACertificate": [der],
            "dNSHostName": [b"adcs.quirk.lab"],
        },
    }


def _target() -> SimpleNamespace:
    return SimpleNamespace(host="adcs-openldap", port=38910, realm="QUIRK.LAB")


def _mock_conn_yielding(ca_entries: list[dict], tpl_entries: list[dict]) -> MagicMock:
    """Build a MagicMock ldap3.Connection whose paged_search returns the
    CA list on its first call and the template list on its second call.
    """
    mock_conn = MagicMock(name="ldap3.Connection")
    # paged_search is called twice per target. The scanner constructs a
    # fresh generator-style iterable each time it iterates the result.
    # Use side_effect with iter() copies to avoid generator exhaustion.
    mock_conn.extend.standard.paged_search.side_effect = [
        iter(list(ca_entries)),
        iter(list(tpl_entries)),
    ]
    mock_conn.unbind.return_value = None
    return mock_conn


def _run_scan_with_mock_conn(
    mock_conn: MagicMock,
    *,
    config_base: str = "CN=Configuration,DC=quirk,DC=lab",
) -> list:
    """Patch _bind_and_query to return (mock_conn, config_base) and
    drive scan_adcs_targets over a single target."""
    with patch.object(adcs_scanner, "LDAP3_AVAILABLE", True), \
         patch.object(adcs_scanner, "ldap3", _fake_ldap3_module(), create=True), \
         patch.object(
             adcs_scanner, "_bind_and_query",
             return_value=(mock_conn, config_base),
         ):
        return scan_adcs_targets([_target()], timeout=5)


# ---------------------------------------------------------------------------
# Full contract assertion — three templates + 1 weak CA + 4 coverage-gaps
# ---------------------------------------------------------------------------

def test_full_chaos_lab_contract_against_mocked_ldap() -> None:
    """The deterministic 6-finding-per-target contract from
    `quantum-chaos-enterprise-lab/expected_results_v4.md` §profile-adcs."""
    mock_conn = _mock_conn_yielding([_ca_entry()], _load_templates())
    eps = _run_scan_with_mock_conn(mock_conn)

    # Every finding carries protocol="ADCS" (ADCS-06).
    assert {ep.protocol for ep in eps} == {"ADCS"}, (
        f"non-ADCS protocols leaked: {sorted({ep.protocol for ep in eps})}"
    )

    high = [ep for ep in eps if ep.severity == "HIGH"]
    low = [ep for ep in eps if ep.severity == "LOW"]

    # ---- Weak CA: exactly one HIGH with weak-signing-alg in service_detail.
    weak_ca = [ep for ep in high if "weak-signing-alg" in (ep.service_detail or "")]
    assert len(weak_ca) == 1, (
        f"expected exactly 1 weak-signing-alg HIGH, got {len(weak_ca)}: "
        f"{[ep.service_detail for ep in high]}"
    )
    ca_ep = weak_ca[0]
    assert ca_ep.cert_pubkey_alg == "RSA"
    assert ca_ep.cert_pubkey_size == 1024
    assert ca_ep.adcs_scan_json, "adcs_scan_json must be populated on CA HIGH"
    blob = json.loads(ca_ep.adcs_scan_json)
    assert blob.get("ca_cn") == "QuirkLabCA"
    assert "weak-signing-alg" in blob.get("reasons", [])

    # ---- ESC1: exactly one HIGH with esc1- in service_detail.
    esc1 = [ep for ep in high if "esc1-" in (ep.service_detail or "")]
    assert len(esc1) == 1, (
        f"expected exactly 1 ESC1 HIGH, got {len(esc1)}: "
        f"{[ep.service_detail for ep in high]}"
    )
    esc1_blob = json.loads(esc1[0].adcs_scan_json)
    assert esc1_blob["esc"] == "ESC1"
    assert esc1_blob["template_cn"] == "BadTemplate-ESC1"

    # ---- SafeTemplate: zero findings.
    safe_findings = [
        ep for ep in eps
        if "SafeTemplate" in (ep.service_detail or "")
    ]
    assert safe_findings == [], (
        f"SafeTemplate must emit zero findings, got {safe_findings}"
    )

    # ---- BadTemplate-ESC4: no ESC4 misconfig finding (D-80-R8 — coverage-gap only).
    esc4_misconfig = [
        ep for ep in eps
        if "BadTemplate-ESC4" in (ep.service_detail or "")
        and "coverage-gap" not in (ep.service_detail or "")
    ]
    assert esc4_misconfig == [], (
        f"BadTemplate-ESC4 must NOT emit a misconfig finding (D-80-R8); "
        f"got {[(e.service_detail, e.severity) for e in esc4_misconfig]}"
    )

    # ---- COVERAGE-GAP: exactly four LOW with service_detail starting "coverage-gap|".
    coverage_gaps = [
        ep for ep in low
        if (ep.service_detail or "").startswith("coverage-gap|")
    ]
    assert len(coverage_gaps) == 4, (
        f"expected exactly 4 COVERAGE-GAP LOW, got {len(coverage_gaps)}: "
        f"{[ep.service_detail for ep in coverage_gaps]}"
    )
    esc_classes = sorted(
        json.loads(ep.adcs_scan_json)["esc"] for ep in coverage_gaps
    )
    assert esc_classes == ["ESC4", "ESC5", "ESC7", "ESC8"], (
        f"COVERAGE-GAP ESC classes mismatch: {esc_classes}"
    )

    # ---- adcs_scan_json populated on every emitted finding (ADCS-03).
    for ep in eps:
        assert ep.adcs_scan_json, (
            f"adcs_scan_json missing on {ep.severity} {ep.service_detail}"
        )

    # ---- Top-line count: 1 weak-CA + 1 ESC1 + 4 coverage-gap = 6 per target.
    assert len(eps) == 6, (
        f"expected 6 findings per target, got {len(eps)}: "
        f"{[(e.severity, e.service_detail) for e in eps]}"
    )


# ---------------------------------------------------------------------------
# ADCS-UNREACH (ADCS-04 SC#2)
# ---------------------------------------------------------------------------

def test_bind_failure_emits_adcs_unreachable_no_propagation() -> None:
    """When LDAP bind fails the scanner emits exactly one LOW
    `adcs-unreachable` finding per target and NEVER raises."""
    with patch.object(adcs_scanner, "LDAP3_AVAILABLE", True), \
         patch.object(adcs_scanner, "ldap3", _fake_ldap3_module(), create=True), \
         patch.object(
             adcs_scanner, "_bind_and_query",
             side_effect=_FakeLDAPBindError("bind-rejected"),
         ):
        eps = scan_adcs_targets([_target()], timeout=5)

    assert len(eps) == 1, f"expected exactly 1 ADCS-UNREACH finding, got {len(eps)}"
    ep = eps[0]
    assert ep.protocol == "ADCS"
    assert ep.severity == "LOW"
    assert (ep.service_detail or "").startswith("adcs-unreachable|"), (
        f"service_detail must start with 'adcs-unreachable|', got {ep.service_detail!r}"
    )
    assert ep.scan_error_category == "exception"
    assert ep.scan_error  # non-empty error string


def test_safe_only_input_yields_just_coverage_gaps() -> None:
    """A target with NO CA cert and only SafeTemplate emits exactly the
    4 COVERAGE-GAP findings — no false positives."""
    templates = _load_templates()
    safe_only = [t for t in templates if t["raw_attributes"]["cn"] == ["SafeTemplate"]]
    assert len(safe_only) == 1, "fixtures changed — SafeTemplate missing"
    mock_conn = _mock_conn_yielding([], safe_only)
    eps = _run_scan_with_mock_conn(mock_conn)

    assert len(eps) == 4, f"expected 4 coverage-gap LOWs, got {len(eps)}"
    assert all(ep.severity == "LOW" for ep in eps)
    assert all((ep.service_detail or "").startswith("coverage-gap|") for ep in eps)
