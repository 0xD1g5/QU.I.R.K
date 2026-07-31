"""BACnet/IP OT-ICS fingerprint probe — Phase 141 (OTICS-02, OTICS-03).

Performs exactly one read-only, directed-unicast Who-Is/I-Am round-trip per
host, followed by a ReadProperty for model-name and firmware-revision on the
Device object, mirroring quirk/scanner/snmp_scanner.py's and
quirk/scanner/modbus_scanner.py's advisory-import-guard +
async-probe-with-sync-wrapper shape.

UDP-gating design note (D-04 interpretation for BACnet):
    QUIRK has no UDP port-scan capability (the nmap path is -sT / tcp_only=
    True — TCP SYN/connect scanning only). BACnet/IP is a UDP-only protocol,
    so there is no equivalent "confirmed open port" signal available to gate
    on before probing. This module therefore operationally defines D-04's
    port-gating intent for BACnet as: the single bounded, read-only Who-Is/
    I-Am unicast round-trip succeeding IS the confirmation that port 47808/
    UDP is open and speaking BACnet. This is a deliberate, explicit,
    protocol-specific interpretation of D-04 (RESEARCH.md Open Question #1,
    recommended Option a) — it is documented here in-source, not silently
    skipped or left implicit.

Advisory import guard: if bacpypes3 is not installed (i.e. the [hw] extras
are absent), probe_bacnet_target logs a WARNING and returns a null-safe dict
— it never raises ImportError (mirrors D-03 from Phase 133/139).

Safety (OTICS-03 / D-05 one-strike circuit breaker):
  - Only read-only Who-Is/I-Am discovery plus ReadProperty(model-name,
    firmware-revision) on the Device object is ever sent. This module never
    issues any property-write request to a target — read-only access only.
  - Who-Is is a single DIRECTED UNICAST request at Address(host) — it is
    never addressed to every device on the segment — a Security Domain
    mitigation limiting blast radius (only the target host is queried, no
    segment-wide discovery flood).
  - Exactly one in-flight Who-Is per host — any anomalous response (raised
    exception, malformed I-Am, transport error) aborts immediately with no
    retry and no backoff.
  - Dedicated conservative default timeout of 2s (D-08) — never sourced from
    cfg.scan.timeout_seconds.
  - No BAC0-style stateful device cache — the Application is torn down in a
    finally block after every probe (RESEARCH anti-pattern).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, Optional

from quirk.util.safe_exc import safe_str

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Advisory import guard: bacpypes3 ([hw] extras — OTICS-02 / D-03)
# ---------------------------------------------------------------------------
try:
    from bacpypes3.app import Application
    from bacpypes3.pdu import Address

    _PYBACNET_AVAILABLE = True
except ImportError:
    _PYBACNET_AVAILABLE = False

_NULL_RESULT: Dict[str, Optional[str]] = {
    "bacnet_vendor": None,
    "bacnet_model": None,
    "bacnet_firmware": None,
    "bacnet_probe_state": "no_response",
}

# Standard BACnet/IP port — hardcoded per D-06/RESEARCH Pitfall 3; no
# per-host config field. bacpypes3's Application binds its own UDP socket;
# the port constant is documented here for clarity/verification only.
_BACNET_PORT = 47808

# Device object ReadProperty identifiers (BACnet standard property names).
_PROP_MODEL_NAME = "model-name"
_PROP_FIRMWARE_REVISION = "firmware-revision"


async def _async_probe(host: str, timeout: int) -> Dict[str, Optional[str]]:
    """Async BACnet/IP Who-Is/I-Am + ReadProperty probe.

    Sends exactly ONE directed unicast Who-Is at ``Address(host)`` — never
    addressed to every device on the segment. Any anomalous response
    (timeout, malformed I-Am, transport error, ReadProperty failure) is a
    one-strike abort — no retry, no backoff (D-05).
    """
    result: Dict[str, Optional[str]] = dict(_NULL_RESULT)
    app = Application()
    try:
        address = Address(host)

        # Single bounded, directed-unicast Who-Is — this round-trip itself IS
        # the D-04 port-gating confirmation for BACnet (see module docstring).
        i_ams = await asyncio.wait_for(
            app.who_is(address=address, timeout=timeout), timeout=timeout
        )
        if not i_ams:
            return result

        i_am = i_ams[0]
        vendor_id = getattr(i_am, "vendorID", None)
        result["bacnet_vendor"] = str(vendor_id) if vendor_id is not None else None

        device_id = i_am.iAmDeviceIdentifier
        source = getattr(i_am, "pduSource", address)

        model = await asyncio.wait_for(
            app.read_property(source, device_id, _PROP_MODEL_NAME), timeout=timeout
        )
        result["bacnet_model"] = str(model) if model else None

        firmware = await asyncio.wait_for(
            app.read_property(source, device_id, _PROP_FIRMWARE_REVISION),
            timeout=timeout,
        )
        result["bacnet_firmware"] = str(firmware) if firmware else None

        result["bacnet_probe_state"] = (
            "identified" if result["bacnet_vendor"] else "no_match"
        )
    except (asyncio.TimeoutError, OSError, Exception) as exc:
        _LOG.debug("BACnet probe %s failed: %s", host, safe_str(exc))
        result = dict(_NULL_RESULT)
        result["bacnet_probe_state"] = "aborted_anomalous_response"
    finally:
        try:
            app.close()
        except Exception:
            pass
    return result


def probe_bacnet_target(host: str, timeout: int = 2) -> Dict[str, Optional[str]]:
    """Probe a single host via BACnet/IP Who-Is/I-Am and return device identity fields.

    Advisory guard: if bacpypes3 is not installed, logs a WARNING and returns
    a null-safe dict — never raises ImportError.

    Args:
        host:    IP address or hostname to probe (UDP port 47808, hardcoded).
        timeout: Dedicated conservative timeout in seconds (default 2 — D-08,
                 shorter than the general 3s scan default).

    Returns:
        Dict with keys: ``bacnet_vendor``, ``bacnet_model``, ``bacnet_firmware``,
        ``bacnet_probe_state``. All values are ``str | None`` except
        ``bacnet_probe_state`` which is always a str. Never raises.
    """
    if not _PYBACNET_AVAILABLE:
        _LOG.warning(
            "BACnet probe skipped: install quirk-scanner[hw] to enable "
            "OT/ICS BACnet fingerprinting (bacpypes3 not found)"
        )
        return dict(_NULL_RESULT)

    try:
        return asyncio.run(_async_probe(host, timeout))
    except Exception as exc:
        _LOG.debug("BACnet probe %s failed: %s", host, safe_str(exc))
        return dict(_NULL_RESULT)
