"""Phase 141 Plan 11 — outer SSH-gate fix regression coverage.

141-08 fixed Step 4's Modbus gate to key on host-level confirmed-open-502
evidence (``confirmed_open_ports``) instead of the SSH endpoint's own port.
But that inner fix only ever matters if ``fingerprint_hardware()`` is called
at all — and it was (and, absent this plan's fix, still would be) only ever
invoked from inside ``run_scan.py``'s ``_run_ssh_phase()``, whose first line
is ``if not ssh_targets: return []``. A host with ZERO SSH-classified
endpoints (the realistic pure-Modbus/BACnet OT device) never reached the
hardware-fingerprint call at all.

Group A tests pin the contract of a new module-level helper,
``run_scan.build_ot_supplemental_endpoints``, that computes the supplemental
OT/ICS-only host set (hosts with OT/ICS evidence MINUS hosts already covered
by an SSH endpoint, to avoid double-probing).

Group B tests pin the contract of a new additive ``ot_only`` keyword on
``fingerprint_one`` that restricts the waterfall to Steps 4/5 (Modbus/BACnet)
for supplemental OT-only endpoints — skipping Steps 2 (HTTP mgmt) and 3
(SNMP) to honor D-04/D-05's minimal-footprint posture against fragile OT
gear that has no SSH/IT-management endpoint at all.

No network connections are made — HTTP/SNMP probe functions are patched at
their import site.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch


def _make_cfg(enable_modbus: bool = False, enable_bacnet: bool = False):
    connectors = SimpleNamespace(
        enable_modbus=enable_modbus,
        enable_bacnet=enable_bacnet,
        snmp_v3_credentials={},
    )
    return SimpleNamespace(connectors=connectors)


def _make_ep(host: str, port: int, service_detail: str = ""):
    from quirk.models import CryptoEndpoint

    ep = CryptoEndpoint.__new__(CryptoEndpoint)
    ep.__dict__["host"] = host
    ep.__dict__["port"] = port
    ep.__dict__["protocol"] = "TCP"
    ep.__dict__["service_detail"] = service_detail
    return ep


# ============================================================
# Group A — build_ot_supplemental_endpoints(targets, ssh_targets,
#           confirmed_open_ports, cfg)
# ============================================================

def test_modbus_host_included_when_502_confirmed() -> None:
    from run_scan import build_ot_supplemental_endpoints

    cfg = _make_cfg(enable_modbus=True)
    eps = build_ot_supplemental_endpoints(
        targets=[("10.0.0.5", 502)],
        ssh_targets=[],
        confirmed_open_ports={"10.0.0.5": {502}},
        cfg=cfg,
    )

    assert len(eps) == 1
    assert eps[0].host == "10.0.0.5"
    assert eps[0].port == 0


def test_modbus_host_excluded_without_502_evidence() -> None:
    from run_scan import build_ot_supplemental_endpoints

    cfg = _make_cfg(enable_modbus=True)
    eps = build_ot_supplemental_endpoints(
        targets=[("10.0.0.5", 22), ("10.0.0.5", 80)],
        ssh_targets=[],
        confirmed_open_ports={"10.0.0.5": {22, 80}},
        cfg=cfg,
    )

    assert eps == []


def test_bacnet_includes_all_scanned_hosts_flag_only() -> None:
    from run_scan import build_ot_supplemental_endpoints

    cfg = _make_cfg(enable_bacnet=True)
    eps = build_ot_supplemental_endpoints(
        targets=[("10.0.0.5", 47808), ("10.0.0.6", 161)],
        ssh_targets=[],
        confirmed_open_ports={},
        cfg=cfg,
    )

    assert {ep.host for ep in eps} == {"10.0.0.5", "10.0.0.6"}
    assert len(eps) == 2


def test_ssh_hosts_excluded_no_double_probe() -> None:
    from run_scan import build_ot_supplemental_endpoints

    cfg = _make_cfg(enable_modbus=True)
    eps = build_ot_supplemental_endpoints(
        targets=[("10.0.0.5", 502), ("10.0.0.5", 22)],
        ssh_targets=[("10.0.0.5", 22)],
        confirmed_open_ports={"10.0.0.5": {502}},
        cfg=cfg,
    )

    assert eps == []


def test_no_supplemental_when_flags_off() -> None:
    from run_scan import build_ot_supplemental_endpoints

    cfg = _make_cfg(enable_modbus=False, enable_bacnet=False)
    eps = build_ot_supplemental_endpoints(
        targets=[("10.0.0.5", 502)],
        ssh_targets=[],
        confirmed_open_ports={"10.0.0.5": {502}},
        cfg=cfg,
    )

    assert eps == []


# ============================================================
# Group B — fingerprint_one ot_only footprint control
# ============================================================

def test_ot_only_skips_http_and_snmp() -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    ep = _make_ep("10.0.0.5", 0, service_detail="")
    cfg = _make_cfg(enable_modbus=False, enable_bacnet=False)

    with patch(
        "quirk.scanner.hardware_scanner._probe_http_mgmt"
    ) as mock_http, patch(
        "quirk.scanner.snmp_scanner.probe_snmp_target"
    ) as mock_snmp:
        fingerprint_one(ep, timeout=1, cfg=cfg, ot_only=True)

    mock_http.assert_not_called()
    mock_snmp.assert_not_called()


def test_default_path_still_runs_http_snmp() -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    ep = _make_ep("10.0.0.5", 0, service_detail="")
    cfg = _make_cfg(enable_modbus=False, enable_bacnet=False)

    with patch(
        "quirk.scanner.hardware_scanner._probe_http_mgmt"
    ) as mock_http:
        mock_http.return_value = None
        fingerprint_one(ep, timeout=1, cfg=cfg, ot_only=False)

    mock_http.assert_called()
