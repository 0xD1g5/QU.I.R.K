"""Phase 127 — HWCOMPAT-01 hardware scanner behavior contract tests.

No network connections are made. CryptoEndpoint fixtures have service_detail
set directly to simulate SSH banner data already captured by ssh_scanner.py.
HTTP mgmt path is out of scope for these unit tests (no live socket/HTTP).

Fixture note: CryptoEndpoint.__new__(CryptoEndpoint) creates an uninstrumented
SQLAlchemy object. Attributes are set via ep.__dict__ to bypass ORM
instrumentation (avoids AttributeError on NoneType in SQLAlchemy 2.x when
there is no active mapper state — the conftest DB session is not required for
these pure-logic tests).
"""
from __future__ import annotations

import json


def _make_ep(host: str, port: int, service_detail: str, ssh_audit_json=None):
    """Create a CryptoEndpoint fixture without DB/ORM setup."""
    from quirk.models import CryptoEndpoint
    ep = CryptoEndpoint.__new__(CryptoEndpoint)
    ep.__dict__["host"] = host
    ep.__dict__["port"] = port
    ep.__dict__["protocol"] = "SSH"
    ep.__dict__["service_detail"] = service_detail
    ep.__dict__["ssh_audit_json"] = ssh_audit_json
    return ep


# ------------ Cisco SSH banner: high-confidence match ------------

def test_cisco_ssh_banner_high_confidence() -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    ep = _make_ep("10.0.0.1", 22, "SSH-2.0-Cisco-1.25")
    device = fingerprint_one(ep, timeout=3)

    assert device.vendor == "Cisco"
    assert device.confidence in {"high", "medium"}
    assert device.fingerprint_method == "ssh_banner"


# ------------ Unknown banner: never suppressed (D-06) ------------

def test_unknown_banner_not_suppressed() -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    ep = _make_ep("10.0.0.2", 22, "SSH-2.0-OpenSSH_9.6")
    device = fingerprint_one(ep)

    # D-06: vendor=Unknown rows are never suppressed
    assert device.vendor == "Unknown"
    assert device.confidence in {"low", "unknown"}


# ------------ Batch function: one result per endpoint, Unknown emitted ------------

def test_fingerprint_hardware_returns_one_per_endpoint() -> None:
    from quirk.scanner.hardware_scanner import fingerprint_hardware

    ep_cisco = _make_ep("10.0.0.1", 22, "SSH-2.0-Cisco-1.25")
    ep_unknown = _make_ep("10.0.0.3", 22, "SSH-2.0-dropbear_2022.83")

    results = fingerprint_hardware([ep_cisco, ep_unknown])

    assert len(results) == 2

    hosts_in_output = {d.host for d in results}
    assert "10.0.0.1" in hosts_in_output
    assert "10.0.0.3" in hosts_in_output

    # D-06: Unknown rows must appear in results (not dropped)
    unknown_rows = [d for d in results if d.vendor == "Unknown"]
    assert len(unknown_rows) >= 1


# ------------ Phase 154 HWLC-01/02: SSH host-key fingerprint extraction ------------

_SSH_AUDIT_JSON_HIGH = json.dumps(
    {
        "fingerprints": [
            {"hash_alg": "SHA256", "hash": "SHA256:abc123"},
        ]
    }
)


def _no_op_probes(monkeypatch) -> None:
    """Monkeypatch outbound network probes so no test makes a real connection."""
    import quirk.scanner.hardware_scanner as hw_mod

    monkeypatch.setattr(hw_mod, "_probe_http_mgmt", lambda host, port, timeout: None)
    monkeypatch.setattr(
        "quirk.scanner.snmp_scanner.probe_snmp_target",
        lambda *a, **kw: {"snmp_sysdescr": None, "snmp_sysname": None, "snmp_sysobjectid": None},
    )


def test_fingerprint_one_extracts_ssh_host_key_fingerprint(monkeypatch) -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    _no_op_probes(monkeypatch)
    ep = _make_ep(
        "10.0.0.4", 22, "SSH-2.0-dropbear_2022.83", ssh_audit_json=_SSH_AUDIT_JSON_HIGH
    )
    device = fingerprint_one(ep, timeout=3)

    assert device.ssh_host_key_fingerprint == "SHA256:abc123"
    assert device.match_confidence == "high"


def test_fingerprint_one_without_ssh_audit_is_low_confidence(monkeypatch) -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    _no_op_probes(monkeypatch)
    ep = _make_ep("10.0.0.5", 22, "SSH-2.0-dropbear_2022.83", ssh_audit_json=None)
    device = fingerprint_one(ep, timeout=3)

    assert device.ssh_host_key_fingerprint is None
    assert device.match_confidence == "low"


def test_fingerprint_one_extracts_fingerprint_even_when_vendor_identified() -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    ep = _make_ep(
        "10.0.0.6", 22, "SSH-2.0-Cisco-1.25", ssh_audit_json=_SSH_AUDIT_JSON_HIGH
    )
    device = fingerprint_one(ep, timeout=3)

    assert device.vendor != "Unknown"
    assert device.match_confidence == "high"


def test_fingerprint_one_malformed_ssh_audit_json_is_low_confidence(monkeypatch) -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    _no_op_probes(monkeypatch)
    ep = _make_ep(
        "10.0.0.7", 22, "SSH-2.0-dropbear_2022.83", ssh_audit_json="{not json"
    )
    device = fingerprint_one(ep, timeout=3)

    assert device.match_confidence == "low"
    assert device.ssh_host_key_fingerprint is None


# ------------ Phase 154 HWLC-01/02: probe_status classification ------------

def test_probe_status_success_on_unknown_vendor(monkeypatch) -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    _no_op_probes(monkeypatch)
    ep = _make_ep("10.0.0.8", 22, "SSH-2.0-dropbear_2022.83")
    device = fingerprint_one(ep, timeout=3)

    assert device.vendor == "Unknown"
    assert device.probe_status == "success"


def test_probe_status_failed_when_nothing_responds(monkeypatch) -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    _no_op_probes(monkeypatch)
    ep = _make_ep("10.0.0.9", 22, "")
    device = fingerprint_one(ep, timeout=3)

    assert device.probe_status == "failed"


def test_probe_status_failed_on_probe_exception(monkeypatch) -> None:
    import quirk.scanner.hardware_scanner as hw_mod
    from quirk.scanner.hardware_scanner import fingerprint_one

    def _raise(*a, **kw):
        raise RuntimeError("simulated probe failure")

    monkeypatch.setattr(hw_mod, "_match_matrix", _raise)
    ep = _make_ep("10.0.0.10", 22, "SSH-2.0-Cisco-1.25")
    device = fingerprint_one(ep, timeout=3)

    assert device.probe_status == "failed"


def test_probe_status_success_on_http_response_without_vendor_match(monkeypatch) -> None:
    import quirk.scanner.hardware_scanner as hw_mod
    from quirk.scanner.hardware_scanner import fingerprint_one

    monkeypatch.setattr(
        hw_mod,
        "_probe_http_mgmt",
        lambda host, port, timeout: {"entry": None, "body": "", "responded": True},
    )
    monkeypatch.setattr(
        "quirk.scanner.snmp_scanner.probe_snmp_target",
        lambda *a, **kw: {"snmp_sysdescr": None, "snmp_sysname": None, "snmp_sysobjectid": None},
    )
    ep = _make_ep("10.0.0.11", 22, "")
    device = fingerprint_one(ep, timeout=3)

    assert device.probe_status == "success"
    assert device.vendor == "Unknown"


# ------------ Phase 155 HWLC-09/D-16/D-18: catalog-sourced eol_date ------------

import datetime as _dt_mod  # noqa: E402


def test_eol_date_populated_from_catalog_when_vendor_model_match(monkeypatch) -> None:
    from quirk.scanner import hardware_eol
    from quirk.scanner.hardware_scanner import fingerprint_one

    _no_op_probes(monkeypatch)
    fake_eol_date = _dt_mod.date(2028, 6, 1)
    monkeypatch.setattr(
        hardware_eol,
        "EOL_TABLE",
        {("Cisco", None): {"eol_date": "2028-06-01", "eos_date": None, "source_url": "https://example.test"}},
    )
    ep = _make_ep("10.0.0.20", 22, "SSH-2.0-Cisco-1.25")
    device = fingerprint_one(ep, timeout=3)

    assert device.vendor == "Cisco"
    assert device.eol_date == fake_eol_date
    assert isinstance(device.eol_date, _dt_mod.date)
    assert not isinstance(device.eol_date, str)


def test_eol_date_none_when_no_catalog_match(monkeypatch) -> None:
    from quirk.scanner import hardware_eol
    from quirk.scanner.hardware_scanner import fingerprint_one

    _no_op_probes(monkeypatch)
    monkeypatch.setattr(hardware_eol, "EOL_TABLE", {})
    ep = _make_ep("10.0.0.21", 22, "SSH-2.0-Cisco-1.25")
    device = fingerprint_one(ep, timeout=3)

    assert device.eol_date is None


def test_eol_date_never_a_string(monkeypatch) -> None:
    from quirk.scanner import hardware_eol
    from quirk.scanner.hardware_scanner import fingerprint_one

    _no_op_probes(monkeypatch)
    monkeypatch.setattr(
        hardware_eol,
        "EOL_TABLE",
        {("Cisco", None): {"eol_date": "2028-06-01", "eos_date": None, "source_url": "https://example.test"}},
    )
    ep = _make_ep("10.0.0.22", 22, "SSH-2.0-Cisco-1.25")
    device = fingerprint_one(ep, timeout=3)

    assert device.eol_date is None or not isinstance(device.eol_date, str)


def test_eol_date_populated_after_bacnet_resolved_vendor_model(monkeypatch) -> None:
    """A device whose vendor/model is only resolved by the BACnet step still
    receives its catalog eol_date — the apply_eol_date() call site runs after
    every vendor/model-resolution path in fingerprint_one()."""
    from types import SimpleNamespace
    from unittest.mock import patch

    from quirk.models import CryptoEndpoint
    from quirk.scanner import hardware_eol
    from quirk.scanner.hardware_scanner import fingerprint_one

    _no_op_probes(monkeypatch)

    monkeypatch.setattr(
        hardware_eol,
        "EOL_TABLE",
        {
            ("Johnson Controls", "Facility Explorer"): {
                "eol_date": "2027-01-01",
                "eos_date": None,
                "source_url": "https://example.test",
            }
        },
    )
    # bacnet_vendors resolves the raw numeric vendorID/model-name into these
    # canonical strings before EOL_TABLE lookup — patch resolution directly
    # so the test doesn't depend on the live curated resolver catalog.
    monkeypatch.setattr(
        "quirk.scanner.bacnet_vendors.resolve_bacnet_vendor",
        lambda raw: "Johnson Controls",
    )
    monkeypatch.setattr(
        "quirk.scanner.bacnet_vendors.resolve_bacnet_model_family",
        lambda vendor, raw: "Facility Explorer",
    )

    ep = CryptoEndpoint.__new__(CryptoEndpoint)
    ep.__dict__["host"] = "10.0.0.23"
    ep.__dict__["port"] = 80
    ep.__dict__["protocol"] = "TCP"
    ep.__dict__["service_detail"] = None
    ep.__dict__["ssh_audit_json"] = None

    cfg = SimpleNamespace(
        connectors=SimpleNamespace(
            enable_modbus=False, enable_bacnet=True, snmp_v3_credentials={}
        )
    )
    with patch("quirk.scanner.bacnet_scanner.probe_bacnet_target") as mock_probe:
        mock_probe.return_value = {
            "bacnet_vendor": "999",
            "bacnet_model": "raw-model-token",
            "bacnet_firmware": "2.3",
            "bacnet_probe_state": "identified",
        }
        device = fingerprint_one(ep, timeout=1, cfg=cfg)

    assert device.vendor == "Johnson Controls"
    assert device.model == "Facility Explorer"
    assert device.eol_date == _dt_mod.date(2027, 1, 1)


def test_apply_eol_date_exception_leaves_eol_date_none(monkeypatch) -> None:
    import quirk.scanner.hardware_scanner as hw_mod
    from quirk.scanner.hardware_scanner import fingerprint_one

    _no_op_probes(monkeypatch)

    def _raise(vendor, model):
        raise RuntimeError("simulated catalog failure")

    monkeypatch.setattr("quirk.scanner.hardware_eol.correlate_eol", _raise)
    ep = _make_ep("10.0.0.24", 22, "SSH-2.0-Cisco-1.25")
    device = fingerprint_one(ep, timeout=3)

    # Catalog failure must not propagate out of fingerprint_one()
    assert device.eol_date is None
    assert device.vendor == "Cisco"


def test_apply_eol_date_unit_never_reparses_string() -> None:
    """apply_eol_date() must assign correlate_eol()'s already-parsed date
    directly — never re-parse via fromisoformat (RESEARCH.md Pitfall 5)."""
    from quirk.models import HardwareDevice
    from quirk.scanner.hardware_scanner import apply_eol_date

    device = HardwareDevice(
        host="10.0.0.30",
        port=22,
        vendor="NoSuchVendor",
        model="NoSuchModel",
    )
    apply_eol_date(device)

    assert device.eol_date is None


def test_assign_tier_returns_na_for_pre_2030_catalog_eol_date(monkeypatch) -> None:
    """D-18: a device that received a pre-2030 catalog eol_date must be
    classified Tier N/A by the pre-existing assign_tier() override."""
    from quirk.scanner import hardware_eol
    from quirk.scanner.hardware_scanner import fingerprint_one
    from quirk.scanner.hardware_tier import assign_tier

    _no_op_probes(monkeypatch)
    monkeypatch.setattr(
        hardware_eol,
        "EOL_TABLE",
        {("Cisco", None): {"eol_date": "2028-06-01", "eos_date": None, "source_url": "https://example.test"}},
    )
    ep = _make_ep("10.0.0.25", 22, "SSH-2.0-Cisco-1.25")
    device = fingerprint_one(ep, timeout=3)

    assert device.eol_date == _dt_mod.date(2028, 6, 1)
    assert assign_tier(device) == "Tier N/A"
