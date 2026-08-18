"""Phase 159 HWLC-13: check-in scan mode dispatch coverage.

Coverage:
    - check_in_fingerprint_devices() dispatches per known.fingerprint_method,
      calling only the identifying probe family for each device.
    - skip_http_mgmt gate on fingerprint_one() — default behavior unchanged,
      Step 2 (HTTP management) skipped only when the flag is explicitly set.
    - run_scan.py's --check-in CLI flag, run_check_in() short-circuit, and
      persistence-boundary control flow (Plan 02).
"""
from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

import run_scan
from quirk.models import HardwareDevice
from quirk.scanner.hardware_scanner import (
    check_in_fingerprint_devices,
    fingerprint_one,
)


def _known(host="10.0.0.1", port=22, fingerprint_method="ssh_banner"):
    return HardwareDevice(
        host=host,
        port=port,
        vendor="Cisco",
        pqc_status="unsupported",
        confidence="high",
        fingerprint_method=fingerprint_method,
        probe_status="success",
    )


class _Connectors:
    def __init__(self, enable_modbus=False, enable_bacnet=False):
        self.enable_modbus = enable_modbus
        self.enable_bacnet = enable_bacnet


class _Cfg:
    def __init__(self, enable_modbus=False, enable_bacnet=False):
        self.connectors = _Connectors(enable_modbus, enable_bacnet)


# ---------------------------------------------------------------------------
# skip_http_mgmt gate
# ---------------------------------------------------------------------------


def test_skip_http_mgmt_default_preserves_existing_behavior() -> None:
    """Omitting skip_http_mgmt must not change Step 2's gate — a
    vendor-Unknown device with no matrix match still probes HTTP mgmt."""
    from quirk.models import CryptoEndpoint

    ep = CryptoEndpoint(host="10.0.0.5", port=22, service_detail="")
    with patch(
        "quirk.scanner.hardware_scanner._probe_http_mgmt", return_value=None
    ) as mock_probe:
        fingerprint_one(ep, timeout=1)
    assert mock_probe.called


def test_skip_http_mgmt_true_skips_step2() -> None:
    from quirk.models import CryptoEndpoint

    ep = CryptoEndpoint(host="10.0.0.5", port=22, service_detail="")
    with patch(
        "quirk.scanner.hardware_scanner._probe_http_mgmt", return_value=None
    ) as mock_probe:
        fingerprint_one(ep, timeout=1, skip_http_mgmt=True)
    assert not mock_probe.called


# ---------------------------------------------------------------------------
# check_in_fingerprint_devices dispatch
# ---------------------------------------------------------------------------


def test_dispatch_ssh_banner_calls_scan_ssh_one_once() -> None:
    known = _known(fingerprint_method="ssh_banner")
    with patch(
        "quirk.scanner.ssh_scanner.scan_ssh_one"
    ) as mock_ssh, patch(
        "quirk.scanner.hardware_scanner.fingerprint_one"
    ) as mock_fp:
        from quirk.models import CryptoEndpoint

        mock_ssh.return_value = CryptoEndpoint(
            host=known.host, port=known.port, service_detail="SSH-2.0-Cisco"
        )
        mock_fp.return_value = HardwareDevice(
            host=known.host,
            port=known.port,
            vendor="Cisco",
            pqc_status="unsupported",
            confidence="high",
            fingerprint_method="ssh_banner",
            probe_status="success",
        )
        result = check_in_fingerprint_devices([known], cfg=None, timeout=1)

    mock_ssh.assert_called_once_with(known.host, known.port, 1, None)
    assert mock_fp.call_count == 1
    call_args = mock_fp.call_args
    assert call_args[0][0] is mock_ssh.return_value
    assert "skip_http_mgmt" not in call_args[1]
    assert "ot_only" not in call_args[1]
    assert len(result) == 1
    assert result[0].is_partial_scan is True
    assert (result[0].host, result[0].port) == (known.host, known.port)


def test_dispatch_http_mgmt_does_not_call_scan_ssh_one_uses_synthetic_endpoint() -> None:
    known = _known(fingerprint_method="http_mgmt")
    with patch(
        "quirk.scanner.ssh_scanner.scan_ssh_one"
    ) as mock_ssh, patch(
        "quirk.scanner.hardware_scanner.fingerprint_one"
    ) as mock_fp:
        mock_fp.return_value = HardwareDevice(
            host=known.host,
            port=known.port,
            vendor="Cisco",
            pqc_status="unsupported",
            confidence="high",
            fingerprint_method="http_mgmt",
            probe_status="success",
        )
        check_in_fingerprint_devices([known], cfg=None, timeout=1)

    assert not mock_ssh.called
    ep_arg = mock_fp.call_args[0][0]
    assert ep_arg.host == known.host
    assert ep_arg.port == known.port
    assert ep_arg.service_detail == ""


def test_dispatch_snmp_uses_skip_http_mgmt_true() -> None:
    known = _known(fingerprint_method="snmp")
    with patch("quirk.scanner.hardware_scanner.fingerprint_one") as mock_fp:
        mock_fp.return_value = HardwareDevice(
            host=known.host,
            port=known.port,
            vendor="Cisco",
            pqc_status="unsupported",
            confidence="medium",
            fingerprint_method="snmp",
            probe_status="success",
        )
        check_in_fingerprint_devices([known], cfg=None, timeout=1)

    call_args = mock_fp.call_args
    assert call_args[1].get("skip_http_mgmt") is True


def test_dispatch_modbus_enabled_seeds_confirmed_open_ports_and_ot_only() -> None:
    known = _known(host="10.0.0.9", port=22, fingerprint_method="modbus")
    cfg = _Cfg(enable_modbus=True)
    with patch("quirk.scanner.hardware_scanner.fingerprint_one") as mock_fp:
        mock_fp.return_value = HardwareDevice(
            host=known.host,
            port=known.port,
            vendor="Schneider Electric",
            pqc_status="unsupported",
            confidence="medium",
            fingerprint_method="modbus",
            probe_status="success",
        )
        check_in_fingerprint_devices([known], cfg=cfg, timeout=1)

    call_args = mock_fp.call_args
    assert call_args[1].get("confirmed_open_ports") == {known.host: {502}}
    assert call_args[1].get("ot_only") is True


def test_dispatch_modbus_disabled_skips_device_entirely() -> None:
    known = _known(host="10.0.0.9", port=22, fingerprint_method="modbus")
    cfg = _Cfg(enable_modbus=False)
    with patch("quirk.scanner.hardware_scanner.fingerprint_one") as mock_fp:
        result = check_in_fingerprint_devices([known], cfg=cfg, timeout=1)

    assert not mock_fp.called
    assert result == []


def test_dispatch_bacnet_enabled_uses_ot_only() -> None:
    known = _known(host="10.0.0.10", port=22, fingerprint_method="bacnet")
    cfg = _Cfg(enable_bacnet=True)
    with patch("quirk.scanner.hardware_scanner.fingerprint_one") as mock_fp:
        mock_fp.return_value = HardwareDevice(
            host=known.host,
            port=known.port,
            vendor="Johnson Controls",
            pqc_status="unsupported",
            confidence="medium",
            fingerprint_method="bacnet",
            probe_status="success",
        )
        check_in_fingerprint_devices([known], cfg=cfg, timeout=1)

    call_args = mock_fp.call_args
    assert call_args[1].get("ot_only") is True
    assert "confirmed_open_ports" not in call_args[1]


def test_dispatch_bacnet_disabled_skips_device_entirely() -> None:
    known = _known(host="10.0.0.10", port=22, fingerprint_method="bacnet")
    cfg = _Cfg(enable_bacnet=False)
    with patch("quirk.scanner.hardware_scanner.fingerprint_one") as mock_fp:
        result = check_in_fingerprint_devices([known], cfg=cfg, timeout=1)

    assert not mock_fp.called
    assert result == []


def test_dispatch_unknown_method_full_waterfall_no_skip_flags() -> None:
    known = _known(host="10.0.0.11", port=22, fingerprint_method="unknown")
    with patch("quirk.scanner.hardware_scanner.fingerprint_one") as mock_fp:
        mock_fp.return_value = HardwareDevice(
            host=known.host,
            port=known.port,
            vendor="Unknown",
            pqc_status="unknown",
            confidence="unknown",
            fingerprint_method="unknown",
            probe_status="failed",
        )
        check_in_fingerprint_devices([known], cfg=None, timeout=1)

    call_args = mock_fp.call_args
    assert "skip_http_mgmt" not in call_args[1]
    assert "ot_only" not in call_args[1]


def test_dispatch_none_method_full_waterfall() -> None:
    known = _known(host="10.0.0.12", port=22, fingerprint_method=None)
    with patch("quirk.scanner.hardware_scanner.fingerprint_one") as mock_fp:
        mock_fp.return_value = HardwareDevice(
            host=known.host,
            port=known.port,
            vendor="Unknown",
            pqc_status="unknown",
            confidence="unknown",
            fingerprint_method="unknown",
            probe_status="failed",
        )
        check_in_fingerprint_devices([known], cfg=None, timeout=1)

    assert mock_fp.called


def test_dispatch_no_port_zero_used_for_synthetic_endpoints() -> None:
    known = _known(host="10.0.0.13", port=22, fingerprint_method="snmp")
    with patch("quirk.scanner.hardware_scanner.fingerprint_one") as mock_fp:
        mock_fp.return_value = HardwareDevice(
            host=known.host,
            port=known.port,
            vendor="Cisco",
            pqc_status="unsupported",
            confidence="medium",
            fingerprint_method="snmp",
            probe_status="success",
        )
        check_in_fingerprint_devices([known], cfg=None, timeout=1)

    ep_arg = mock_fp.call_args[0][0]
    assert ep_arg.port == 22
    assert ep_arg.port != 0


def test_dispatch_every_device_marked_is_partial_scan_true() -> None:
    known1 = _known(host="10.0.0.20", port=22, fingerprint_method="ssh_banner")
    known2 = _known(host="10.0.0.21", port=22, fingerprint_method="unknown")
    with patch(
        "quirk.scanner.ssh_scanner.scan_ssh_one"
    ) as mock_ssh, patch(
        "quirk.scanner.hardware_scanner.fingerprint_one"
    ) as mock_fp:
        from quirk.models import CryptoEndpoint

        mock_ssh.return_value = CryptoEndpoint(
            host=known1.host, port=known1.port, service_detail=""
        )

        def _make_device(ep, *a, **kw):
            return HardwareDevice(
                host=ep.host,
                port=ep.port,
                vendor="Unknown",
                pqc_status="unknown",
                confidence="unknown",
                fingerprint_method="unknown",
                probe_status="success",
            )

        mock_fp.side_effect = _make_device
        results = check_in_fingerprint_devices([known1, known2], cfg=None, timeout=1)

    assert len(results) == 2
    for device in results:
        assert device.is_partial_scan is True


def test_dispatch_probe_exception_does_not_abort_batch() -> None:
    known1 = _known(host="10.0.0.30", port=22, fingerprint_method="unknown")
    known2 = _known(host="10.0.0.31", port=22, fingerprint_method="unknown")

    def _side_effect(ep, *a, **kw):
        if ep.host == known1.host:
            raise RuntimeError("boom")
        return HardwareDevice(
            host=ep.host,
            port=ep.port,
            vendor="Unknown",
            pqc_status="unknown",
            confidence="unknown",
            fingerprint_method="unknown",
            probe_status="success",
        )

    with patch(
        "quirk.scanner.hardware_scanner.fingerprint_one", side_effect=_side_effect
    ):
        results = check_in_fingerprint_devices([known1, known2], cfg=None, timeout=1)

    assert len(results) == 1
    assert results[0].host == known2.host


# ---------------------------------------------------------------------------
# run_scan.py --check-in control flow / persistence boundary (Plan 02)
# ---------------------------------------------------------------------------


class _RunScanConnectors:
    def __init__(self):
        self.enable_modbus = False
        self.enable_bacnet = False


class _RunScanTimeouts:
    def __init__(self):
        self.default_seconds = 1


class _RunScanScan:
    def __init__(self):
        self.timeouts = _RunScanTimeouts()


class _RunScanOutput:
    def __init__(self, db_path="unused.db"):
        self.db_path = db_path


class _RunScanCfg:
    def __init__(self):
        self.output = _RunScanOutput()
        self.connectors = _RunScanConnectors()
        self.scan = _RunScanScan()


def _persisted_device(host="10.0.0.1", port=22, probe_status="success"):
    return HardwareDevice(
        host=host,
        port=port,
        vendor="Cisco",
        pqc_status="unsupported",
        confidence="high",
        fingerprint_method="ssh_banner",
        probe_status=probe_status,
        is_partial_scan=True,
        scanned_at=None,
    )


def test_empty_fleet_no_writes() -> None:
    cfg = _RunScanCfg()
    args = MagicMock()
    logger = MagicMock()

    with patch("run_scan.get_session"), \
         patch("run_scan.latest_successful_hardware_devices", return_value=[]), \
         patch("run_scan.check_in_fingerprint_devices") as mock_dispatch, \
         patch("run_scan.persist_and_reconcile") as mock_persist:
        result = run_scan.run_check_in(cfg, args, logger)

    assert result == 0
    assert not mock_dispatch.called
    assert not mock_persist.called
    logged = " ".join(str(c) for c in logger.info.call_args_list)
    assert "No known devices to check in on" in logged


def test_never_scores() -> None:
    cfg = _RunScanCfg()
    args = MagicMock()
    logger = MagicMock()
    known = [_persisted_device()]
    device = _persisted_device()

    with patch("run_scan.get_session"), \
         patch("run_scan.latest_successful_hardware_devices", return_value=known), \
         patch("run_scan.check_in_fingerprint_devices", return_value=[device]), \
         patch("run_scan.persist_and_reconcile", return_value=(0, [])), \
         patch("quirk.intelligence.scoring.compute_readiness_score") as mock_score:
        result = run_scan.run_check_in(cfg, args, logger)

    assert result == 0
    assert not mock_score.called


def test_persists_via_chokepoint() -> None:
    cfg = _RunScanCfg()
    args = MagicMock()
    logger = MagicMock()
    known = [_persisted_device()]
    devices = [_persisted_device()]

    with patch("run_scan.get_session"), \
         patch("run_scan.latest_successful_hardware_devices", return_value=known), \
         patch("run_scan.check_in_fingerprint_devices", return_value=devices), \
         patch("run_scan.persist_and_reconcile", return_value=(0, [])) as mock_persist:
        run_scan.run_check_in(cfg, args, logger)

    assert mock_persist.call_count == 1
    call = mock_persist.call_args
    # positional args: (session, devices, cfg, logger) — no extra kwargs
    assert call.args[1] is devices
    assert call.args[2] is cfg
    assert call.kwargs == {}


def test_marker_set_on_persisted_devices() -> None:
    cfg = _RunScanCfg()
    args = MagicMock()
    logger = MagicMock()
    known = [_persisted_device()]
    devices = [_persisted_device(), _persisted_device(host="10.0.0.2")]

    with patch("run_scan.get_session"), \
         patch("run_scan.latest_successful_hardware_devices", return_value=known), \
         patch("run_scan.check_in_fingerprint_devices", return_value=devices), \
         patch("run_scan.persist_and_reconcile", return_value=(0, [])) as mock_persist:
        run_scan.run_check_in(cfg, args, logger)

    persisted_devices = mock_persist.call_args.args[1]
    for dev in persisted_devices:
        assert dev.is_partial_scan is True


def test_skips_discovery_and_scanner_phases() -> None:
    src = inspect.getsource(run_scan.run_check_in)
    forbidden = [
        "compute_readiness_score",
        "write_report",
        "expand_targets",
        "scan_tls_targets",
        "scan_ssh_targets",
        "scan_jwt_targets",
        "scan_container_targets",
        "scan_source_targets",
    ]
    for name in forbidden:
        assert name not in src, f"run_check_in must not reference {name}"


def test_summary_reports_drift_count() -> None:
    logger = MagicMock()
    device = _persisted_device()
    drift_events = [MagicMock(), MagicMock(), MagicMock()]

    run_scan._print_check_in_summary([device], drift_events, logger)

    assert logger.info.called
    logged_args = logger.info.call_args[0]
    formatted = logged_args[0] % tuple(logged_args[1:])
    assert "3" in formatted


def test_check_in_flag_parses(capsys) -> None:
    """run_scan.py's real argparse parser (built inline in main()) accepts
    --check-in and rejects "check-in" as a --profile value. Exercised via
    main() + sys.argv patching (SystemExit around argparse), not a
    subprocess, per the plan's stated fallback since main() has no
    factored-out parser accessor."""
    import pytest

    with patch("sys.argv", ["run_scan.py", "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            run_scan.main()
        assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "--check-in" in captured.out

    with patch("sys.argv", ["run_scan.py", "--profile", "check-in"]):
        with pytest.raises(SystemExit) as exc_info:
            run_scan.main()
        assert exc_info.value.code != 0
