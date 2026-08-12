"""Unit tests for the BACnet/IP OT-ICS fingerprint probe — Phase 141 Plan 03.

Encodes the OTICS-02/OTICS-03 contract for ``quirk.scanner.bacnet_scanner``:

  - probe_bacnet_target is null-safe and never raises, even when bacpypes3 is
    absent (advisory import guard mirroring quirk/scanner/snmp_scanner.py and
    quirk/scanner/modbus_scanner.py).
  - The single bounded read-only Who-Is/I-Am unicast round-trip operationally
    satisfies D-04's port-gating intent for BACnet (RESEARCH.md Open Question
    #1, Option a) — documented in the module docstring, not silently skipped.
  - Who-Is is a single DIRECTED UNICAST request at Address(host) — never a
    subnet broadcast.
  - A single anomalous response (who_is raising) triggers a one-strike
    circuit breaker — no retry.
  - Only read-only Who-Is/I-Am + ReadProperty(model-name, firmware-revision)
    is ever sent; the module source must never reference any BACnet write
    symbol.

All bacpypes3 network boundaries are mocked — no real UDP socket is ever
opened (RESEARCH.md Validation Architecture: CI unit tests mock the
Application).
"""
from __future__ import annotations

import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


_MODULE_PATH = pathlib.Path(__file__).parent.parent / "quirk" / "scanner" / "bacnet_scanner.py"

# Deny-list of write symbols. OTICS-03: only read-only Who-Is/I-Am +
# ReadProperty may ever appear in this module.
_WRITE_SYMBOLS = (
    "write_property",
    "WriteProperty",
    "WritePropertyRequest",
)

# Deny-list of broadcast symbols — Who-Is MUST be directed unicast only.
_BROADCAST_SYMBOLS = (
    "GlobalBroadcast",
    "LocalBroadcast",
    "broadcast",
)


def test_disabled_by_default() -> None:
    """Importing the module with bacpypes3 absent yields a null-safe dict via the guard.

    The waterfall only ever invokes probe_bacnet_target when enable_bacnet is
    True (verified in 141-04) — here we assert the module-level advisory
    import guard itself: when bacpypes3 is unavailable, probe_bacnet_target
    must return the null-safe dict rather than raising or sending traffic. No
    Application is constructed.
    """
    import quirk.scanner.bacnet_scanner as bacnet_mod

    with patch.object(bacnet_mod, "_PYBACNET_AVAILABLE", False), patch.object(
        bacnet_mod, "_build_ephemeral_application"
    ) as mock_build_app:
        result = bacnet_mod.probe_bacnet_target("127.0.0.1")

    assert isinstance(result, dict)
    assert result["bacnet_probe_state"] == "no_response"
    assert result["bacnet_vendor"] is None
    assert result["bacnet_model"] is None
    assert result["bacnet_firmware"] is None
    mock_build_app.assert_not_called()


def test_parse_device_object() -> None:
    """A clean Who-Is/I-Am + ReadProperty round trip maps vendor/model/firmware."""
    import quirk.scanner.bacnet_scanner as bacnet_mod

    if not bacnet_mod._PYBACNET_AVAILABLE:
        pytest.skip("bacpypes3 not installed")

    mock_i_am = MagicMock()
    mock_i_am.vendorID = 999
    mock_i_am.iAmDeviceIdentifier = ("device", 1234)
    mock_i_am.pduSource = bacnet_mod.Address("127.0.0.1")

    mock_app = MagicMock()
    mock_app.who_is = AsyncMock(return_value=[mock_i_am])
    mock_app.read_property = AsyncMock(side_effect=["BACnet Controller X", "2.3"])
    mock_app.close = MagicMock()

    with patch.object(bacnet_mod, "_PYBACNET_AVAILABLE", True), patch.object(
        bacnet_mod, "_build_ephemeral_application", return_value=mock_app
    ):
        result = bacnet_mod.probe_bacnet_target("127.0.0.1")

    assert result["bacnet_vendor"] == "999"
    assert result["bacnet_model"] == "BACnet Controller X"
    assert result["bacnet_firmware"] == "2.3"
    assert result["bacnet_probe_state"] == "identified"
    assert mock_app.who_is.await_count == 1
    assert mock_app.read_property.await_count == 2


def test_single_inflight_no_writes_unicast() -> None:
    """No write symbols, no broadcast symbols; one anomalous who_is aborts with no retry; unicast only."""
    import quirk.scanner.bacnet_scanner as bacnet_mod

    if not bacnet_mod._PYBACNET_AVAILABLE:
        pytest.skip("bacpypes3 not installed")

    source_text = _MODULE_PATH.read_text(encoding="utf-8")
    lowered = source_text.lower()
    for symbol in _WRITE_SYMBOLS:
        assert symbol.lower() not in lowered, (
            f"Forbidden write symbol '{symbol}' found in bacnet_scanner.py "
            "— OTICS-03 requires read-only Who-Is/I-Am + ReadProperty only."
        )
    for symbol in _BROADCAST_SYMBOLS:
        assert symbol.lower() not in lowered, (
            f"Forbidden broadcast symbol '{symbol}' found in bacnet_scanner.py "
            "— Who-Is MUST be directed unicast at Address(host), never a subnet broadcast."
        )

    mock_app = MagicMock()
    mock_app.who_is = AsyncMock(side_effect=RuntimeError("malformed I-Am"))
    mock_app.read_property = AsyncMock()
    mock_app.close = MagicMock()

    with patch.object(bacnet_mod, "_PYBACNET_AVAILABLE", True), patch.object(
        bacnet_mod, "_build_ephemeral_application", return_value=mock_app
    ):
        result = bacnet_mod.probe_bacnet_target("127.0.0.1")

    assert result["bacnet_probe_state"] == "aborted_anomalous_response"
    assert mock_app.who_is.await_count == 1
    mock_app.read_property.assert_not_called()

    # Directed unicast: the who_is call must carry the target host's Address,
    # never rely on a subnet broadcast default.
    call_kwargs = mock_app.who_is.await_args.kwargs
    assert call_kwargs.get("address") == bacnet_mod.Address("127.0.0.1")
