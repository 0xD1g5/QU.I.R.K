"""Unit tests for the Modbus/TCP OT-ICS fingerprint probe — Phase 141 Plan 02.

Encodes the OTICS-01/OTICS-03 contract for ``quirk.scanner.modbus_scanner``:

  - probe_modbus_target is null-safe and never raises, even when pymodbus is
    absent (advisory import guard mirroring quirk/scanner/snmp_scanner.py).
  - A single anomalous response (timeout/reset/malformed/error) triggers a
    one-strike circuit breaker — no retry.
  - Only read-only FC 43/14 (Read Device Identification) is ever sent; the
    module source must never reference any write function code.

All pymodbus network boundaries are mocked — no real socket is ever opened
(RESEARCH.md Validation Architecture: CI unit tests mock the client).
"""
from __future__ import annotations

import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


_MODULE_PATH = pathlib.Path(__file__).parent.parent / "quirk" / "scanner" / "modbus_scanner.py"

# Deny-list of write function-code symbols. OTICS-03: only read-only FC 43/14
# (Read Device Identification) may ever appear in this module.
_WRITE_SYMBOLS = (
    "WriteSingleRegister",
    "WriteMultipleRegisters",
    "WriteSingleCoil",
    "WriteMultipleCoils",
    "write_register",
    "write_registers",
    "write_coil",
    "write_coils",
)


def test_disabled_by_default() -> None:
    """Importing the module with pymodbus absent yields a null-safe dict via the guard.

    The waterfall only ever invokes probe_modbus_target when enable_modbus is
    True (verified in 141-04) — here we assert the module-level advisory
    import guard itself: when pymodbus is unavailable, probe_modbus_target
    must return the null-safe dict rather than raising or sending traffic.
    """
    import quirk.scanner.modbus_scanner as modbus_mod

    with patch.object(modbus_mod, "_PYMODBUS_AVAILABLE", False):
        result = modbus_mod.probe_modbus_target("127.0.0.1")

    assert isinstance(result, dict)
    assert result["modbus_probe_state"] == "no_response"
    assert result["modbus_vendor"] is None
    assert result["modbus_model"] is None
    assert result["modbus_firmware"] is None


def test_parse_device_id() -> None:
    """A clean Read Device Identification response maps vendor/model/firmware."""
    import quirk.scanner.modbus_scanner as modbus_mod

    mock_response = MagicMock()
    mock_response.isError.return_value = False
    mock_response.information = {
        0: "Schneider Electric",
        1: "M221",
        2: "1.6",
    }

    mock_client = MagicMock()
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.connected = True
    mock_client.execute = AsyncMock(return_value=mock_response)
    mock_client.close = MagicMock()

    with patch.object(modbus_mod, "_PYMODBUS_AVAILABLE", True), patch.object(
        modbus_mod, "AsyncModbusTcpClient", return_value=mock_client
    ):
        result = modbus_mod.probe_modbus_target("127.0.0.1")

    assert result["modbus_vendor"] == "Schneider Electric"
    assert result["modbus_model"] == "M221"
    assert result["modbus_probe_state"] == "identified"
    assert mock_client.execute.await_count == 1


def test_parse_device_id_decodes_bytes() -> None:
    """pymodbus returns Basic-category identification fields as raw bytes.

    Regression test: str(bytes) yields the Python repr (e.g.
    "b'Schneider Electric'") rather than the decoded text. Confirmed live
    against the otics-modbus chaos-lab simulator — the prior implementation
    reported modbus_vendor="b'Schneider Electric'" on real pymodbus 3.14.0
    responses, which the string-fixture unit test above never caught.
    """
    import quirk.scanner.modbus_scanner as modbus_mod

    mock_response = MagicMock()
    mock_response.isError.return_value = False
    mock_response.information = {
        0: b"Schneider Electric",
        1: b"M221",
        2: b"1.6.2.0",
    }

    mock_client = MagicMock()
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.connected = True
    mock_client.execute = AsyncMock(return_value=mock_response)
    mock_client.close = MagicMock()

    with patch.object(modbus_mod, "_PYMODBUS_AVAILABLE", True), patch.object(
        modbus_mod, "AsyncModbusTcpClient", return_value=mock_client
    ):
        result = modbus_mod.probe_modbus_target("127.0.0.1")

    assert result["modbus_vendor"] == "Schneider Electric"
    assert result["modbus_model"] == "M221"
    assert result["modbus_firmware"] == "1.6.2.0"
    assert result["modbus_probe_state"] == "identified"
    assert "b'" not in result["modbus_vendor"]


def test_single_inflight_no_writes() -> None:
    """No write function-code symbols in source; one anomalous response aborts with no retry."""
    source_text = _MODULE_PATH.read_text(encoding="utf-8")
    lowered = source_text.lower()
    for symbol in _WRITE_SYMBOLS:
        assert symbol.lower() not in lowered, (
            f"Forbidden write-function-code symbol '{symbol}' found in modbus_scanner.py "
            "— OTICS-03 requires read-only FC 43/14 only."
        )

    import quirk.scanner.modbus_scanner as modbus_mod

    mock_client = MagicMock()
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.connected = True
    mock_client.execute = AsyncMock(side_effect=ConnectionResetError("reset"))
    mock_client.close = MagicMock()

    with patch.object(modbus_mod, "_PYMODBUS_AVAILABLE", True), patch.object(
        modbus_mod, "AsyncModbusTcpClient", return_value=mock_client
    ):
        result = modbus_mod.probe_modbus_target("127.0.0.1")

    assert result["modbus_probe_state"] == "aborted_anomalous_response"
    assert mock_client.execute.await_count == 1
