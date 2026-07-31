"""Modbus/TCP OT-ICS fingerprint probe — Phase 141 (OTICS-01, OTICS-03).

Performs exactly one read-only FC 43/14 (Read Device Identification) exchange
per host, mirroring quirk/scanner/snmp_scanner.py's advisory-import-guard +
async-probe-with-sync-wrapper shape.

Advisory import guard: if pymodbus is not installed (i.e. the [hw] extras are
absent), probe_modbus_target logs a WARNING and returns a null-safe dict — it
never raises ImportError (mirrors D-03 from Phase 133/139).

Safety (OTICS-03 / D-05 one-strike circuit breaker):
  - Only FC 43/14 Read Device Identification (Basic category, read_code=0x01,
    object_id=0x00 VendorName) is ever sent. No write function code appears
    anywhere in this module.
  - Exactly one in-flight request per host — a single anomalous response
    (timeout, connection reset, malformed payload, error response) aborts
    immediately with no retry and no backoff.
  - Dedicated conservative default timeout of 2s (D-08) — shorter than the
    general 3s scan default; never sourced from cfg.scan.timeout_seconds.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, Optional

from quirk.util.safe_exc import safe_str

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Advisory import guard: pymodbus ([hw] extras — OTICS-01)
# ---------------------------------------------------------------------------
try:
    from pymodbus.client import AsyncModbusTcpClient

    # pymodbus reorganized mei_message under pymodbus.pdu in the 3.8+ series
    # (RESEARCH A3 confirmed against the installed 3.14.0 [hw] extra at
    # execution time); fall back to the legacy top-level path for older
    # 3.x releases still satisfying the pyproject.toml pin.
    try:
        from pymodbus.pdu.mei_message import ReadDeviceInformationRequest
    except ImportError:
        from pymodbus.mei_message import ReadDeviceInformationRequest  # type: ignore[no-redef]

    _PYMODBUS_AVAILABLE = True
except ImportError:
    _PYMODBUS_AVAILABLE = False

_NULL_RESULT: Dict[str, Optional[str]] = {
    "modbus_vendor": None,
    "modbus_model": None,
    "modbus_firmware": None,
    "modbus_probe_state": "no_response",
}

# Standard Modbus/TCP port — hardcoded per D-06/RESEARCH Pitfall 3; no
# per-host config field.
_MODBUS_PORT = 502

# Basic category Read Device Identification: read_code=0x01, object_id=0x00
# (VendorName) — RESEARCH Pattern 3.
_READ_CODE_BASIC = 0x01
_OBJECT_ID_VENDOR_NAME = 0x00

# Read Device Identification object-ID numbering (Basic category).
_OBJ_VENDOR = 0
_OBJ_MODEL = 1
_OBJ_FIRMWARE = 2


async def _async_probe(host: str, timeout: int) -> Dict[str, Optional[str]]:
    """Async Modbus/TCP FC 43/14 Read Device Identification probe.

    Sends exactly ONE read-only request. Any anomalous response (timeout,
    connection reset, malformed payload, transport error, error PDU) is a
    one-strike abort — no retry, no backoff (D-05).
    """
    result: Dict[str, Optional[str]] = dict(_NULL_RESULT)
    client = AsyncModbusTcpClient(host, port=_MODBUS_PORT, timeout=timeout)
    try:
        connected = await asyncio.wait_for(client.connect(), timeout=timeout)
        if not connected or not client.connected:
            return result

        request = ReadDeviceInformationRequest(
            read_code=_READ_CODE_BASIC, object_id=_OBJECT_ID_VENDOR_NAME
        )
        response = await asyncio.wait_for(
            client.execute(False, request), timeout=timeout
        )

        if response is None or response.isError():
            result["modbus_probe_state"] = "aborted_error_response"
            return result

        information = getattr(response, "information", None) or {}
        vendor = information.get(_OBJ_VENDOR)
        model = information.get(_OBJ_MODEL)
        firmware = information.get(_OBJ_FIRMWARE)

        result["modbus_vendor"] = str(vendor) if vendor else None
        result["modbus_model"] = str(model) if model else None
        result["modbus_firmware"] = str(firmware) if firmware else None
        result["modbus_probe_state"] = "identified" if result["modbus_vendor"] else "no_match"
    except (asyncio.TimeoutError, ConnectionResetError, OSError, Exception) as exc:
        _LOG.debug("Modbus probe %s failed: %s", host, safe_str(exc))
        result = dict(_NULL_RESULT)
        result["modbus_probe_state"] = "aborted_anomalous_response"
    finally:
        try:
            client.close()
        except Exception:
            pass
    return result


def probe_modbus_target(host: str, timeout: int = 2) -> Dict[str, Optional[str]]:
    """Probe a single host via Modbus/TCP FC 43/14 and return device identity fields.

    Advisory guard: if pymodbus is not installed, logs a WARNING and returns
    a null-safe dict — never raises ImportError.

    Args:
        host:    IP address or hostname to probe (TCP port 502, hardcoded).
        timeout: Dedicated conservative timeout in seconds (default 2 — D-08,
                 shorter than the general 3s scan default).

    Returns:
        Dict with keys: ``modbus_vendor``, ``modbus_model``, ``modbus_firmware``,
        ``modbus_probe_state``. All values are ``str | None`` except
        ``modbus_probe_state`` which is always a str. Never raises.
    """
    if not _PYMODBUS_AVAILABLE:
        _LOG.warning(
            "Modbus probe skipped: install quirk-scanner[hw] to enable "
            "OT/ICS Modbus fingerprinting (pymodbus not found)"
        )
        return dict(_NULL_RESULT)

    try:
        return asyncio.run(_async_probe(host, timeout))
    except Exception as exc:
        _LOG.debug("Modbus probe %s failed: %s", host, safe_str(exc))
        return dict(_NULL_RESULT)
