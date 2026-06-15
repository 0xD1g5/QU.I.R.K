"""SNMP hardware fingerprinting probe — Phase 133 (SNMP-01).

Probes sysDescr (OID 1.3.6.1.2.1.1.1.0), sysName (1.3.6.1.2.1.1.5.0), and
sysObjectID (1.3.6.1.2.1.1.2.0) via SNMPv2c using pysnmp 7 asyncio HLAPI.

Advisory import guard: if pysnmp is not installed (i.e. the [hw] extras are
absent), all probe functions log a WARNING and return None-dicts — they never
raise ImportError (D-03).

sysdescrparser is used as the primary vendor extractor when available; the
stdlib re table (SNMP_VENDOR_MATRIX entries) is the fallback.
"""
from __future__ import annotations

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Advisory import guard: pysnmp ([hw] extras — SNMP-01 / D-03)
# ---------------------------------------------------------------------------
try:
    from pysnmp.hlapi.v1arch.asyncio import (
        CommunityData,
        ObjectIdentity,
        ObjectType,
        SnmpDispatcher,
        UdpTransportTarget,
        get_cmd,
    )
    _PYSNMP_AVAILABLE = True
except ImportError:
    _PYSNMP_AVAILABLE = False

# ---------------------------------------------------------------------------
# Advisory import guard: sysdescrparser ([hw] extras — SNMP-01 / D-07)
# ---------------------------------------------------------------------------
try:
    # sysdescrparser exposes sub-modules per vendor; we use the top-level
    # sysdescrparser callable as the dispatch function.
    from sysdescrparser import sysdescrparser as _sdp_parse
    # Each sub-module exposes a class whose .parse() returns the object on
    # match, or False/None.  The top-level callable returns UNKNOWN on miss.
    from sysdescrparser import (
        cisco_ios,
        cisco_iosxr,
        cisco_nxos,
        juniper_junos,
        juniper_screenos,
        paloalto_panos,
        linux as _linux_mod,
        freebsd,
    )
    _SYSDESCRPARSER_AVAILABLE = True
except ImportError:
    _SYSDESCRPARSER_AVAILABLE = False

# OIDs queried in every SNMP probe
_OID_SYSDESCR = "1.3.6.1.2.1.1.1.0"
_OID_SYSNAME = "1.3.6.1.2.1.1.5.0"
_OID_SYSOBJECTID = "1.3.6.1.2.1.1.2.0"

_NULL_RESULT: Dict[str, Optional[str]] = {
    "snmp_sysdescr": None,
    "snmp_sysname": None,
    "snmp_sysobjectid": None,
}

# ---------------------------------------------------------------------------
# sysdescrparser dispatch table (classes that expose .parse() returning self
# on match or False on miss).
# ---------------------------------------------------------------------------
_SDPARSER_CLASSES = None if not _SYSDESCRPARSER_AVAILABLE else [
    cisco_ios.CiscoIOS,
    cisco_iosxr.CiscoIOSXR,
    cisco_nxos.CiscoNXOS,
    juniper_junos.JuniperJunos,
    juniper_screenos.JuniperScreenOS,
    paloalto_panos.PaloAltoPANOS,
    _linux_mod.Linux,
    freebsd.FreeBSD,
]


def _try_sysdescrparser(text: str) -> Optional[Dict[str, Optional[str]]]:
    """Attempt vendor extraction via sysdescrparser sub-modules.

    Iterates each known parser class; returns a dict on first match.
    Returns None if no parser matches (caller falls through to regex).
    """
    if not _SYSDESCRPARSER_AVAILABLE or not _SDPARSER_CLASSES:
        return None

    # Vendor name mapping: sysdescrparser uses uppercase vendor strings.
    _VENDOR_MAP = {
        "CISCO": "Cisco",
        "JUNIPER": "Juniper",
        "PALOALTO": "Palo Alto",
        "LINUX": "Linux",
        "FREEBSD": "FreeBSD",
        "UNKNOWN": "Unknown",
    }

    for cls in _SDPARSER_CLASSES:
        try:
            obj = cls(text)
            result = obj.parse()
            if result:
                vendor_raw = getattr(result, "vendor", "UNKNOWN") or "UNKNOWN"
                vendor_norm = _VENDOR_MAP.get(vendor_raw.upper(), vendor_raw.title())
                if vendor_norm and vendor_norm != "Unknown":
                    return {
                        "vendor": vendor_norm,
                        "model": getattr(result, "model", None) or None,
                        "os_version": getattr(result, "version", None) or None,
                    }
        except Exception:
            continue
    return None


def parse_sysdescr(text: Optional[str]) -> Dict[str, Optional[str]]:
    """Extract vendor, model, and OS version from an SNMP sysDescr string.

    Primary path: sysdescrparser (when [hw] extras installed).
    Fallback: stdlib re table from SNMP_VENDOR_MATRIX entries.

    Returns a dict with keys ``vendor`` (str), ``model`` (str | None),
    ``os_version`` (str | None). Never raises; returns ``vendor='Unknown'``
    on no match or on None input.

    Args:
        text: Raw sysDescr string from an SNMP GET response, or None.

    Returns:
        Dict with keys: ``vendor``, ``model``, ``os_version``.
    """
    _empty: Dict[str, Optional[str]] = {
        "vendor": "Unknown",
        "model": None,
        "os_version": None,
    }

    if not text:
        return _empty

    # --- Primary: sysdescrparser ------------------------------------------
    parsed = _try_sysdescrparser(text)
    if parsed:
        return parsed

    # --- Fallback: SNMP_VENDOR_MATRIX regex table -------------------------
    from quirk.scanner.snmp_meta import SNMP_VENDOR_MATRIX

    for entry in SNMP_VENDOR_MATRIX.get("entries", []):
        pattern = entry.get("model_pattern", "")
        if not pattern:
            continue
        try:
            if re.search(pattern, text, re.IGNORECASE):
                return {
                    "vendor": entry.get("vendor", "Unknown"),
                    "model": None,
                    "os_version": None,
                }
        except re.error:
            continue

    return _empty


async def _async_probe(
    host: str,
    community: str,
    timeout: int,
) -> Dict[str, Optional[str]]:
    """Async SNMP GET for sysDescr, sysName, sysObjectID via pysnmp 7.

    Returns a dict with keys snmp_sysdescr, snmp_sysname, snmp_sysobjectid.
    On any error, all values are None.
    """
    result: Dict[str, Optional[str]] = {
        "snmp_sysdescr": None,
        "snmp_sysname": None,
        "snmp_sysobjectid": None,
    }
    dispatcher = SnmpDispatcher()
    try:
        target = await UdpTransportTarget.create(
            (host, 161),
            timeout=timeout,
            retries=1,
        )
        for oid_str, key in (
            (_OID_SYSDESCR, "snmp_sysdescr"),
            (_OID_SYSNAME, "snmp_sysname"),
            (_OID_SYSOBJECTID, "snmp_sysobjectid"),
        ):
            try:
                err_indication, err_status, _err_index, var_binds = await get_cmd(
                    dispatcher,
                    CommunityData(community),
                    target,
                    ObjectType(ObjectIdentity(oid_str)),
                )
                if not err_indication and not err_status and var_binds:
                    _oid, val = var_binds[0]
                    str_val = str(val) if val is not None else None
                    if str_val and str_val not in ("", "noSuchObject", "noSuchInstance"):
                        result[key] = str_val
            except Exception:
                pass  # individual OID failure — leave as None
    except Exception:
        pass  # transport / target creation failure
    finally:
        try:
            dispatcher.transport_dispatcher.close_dispatcher()
        except Exception:
            pass
    return result


def probe_snmp_target(
    host: str,
    community: str = "public",
    timeout: int = 3,
) -> Dict[str, Optional[str]]:
    """Probe a single host via SNMPv2c and return the three sysDescr OID values.

    Advisory guard: if pysnmp is not installed, logs a WARNING and returns a
    dict with all three keys set to None — never raises ImportError.

    Args:
        host:      IP address or hostname to probe (UDP port 161).
        community: SNMPv2c community string (default "public").
        timeout:   Per-OID GET timeout in seconds (default 3).

    Returns:
        Dict with keys: ``snmp_sysdescr``, ``snmp_sysname``, ``snmp_sysobjectid``.
        All values are ``str | None``; None on failure or when pysnmp absent.
    """
    if not _PYSNMP_AVAILABLE:
        _LOG.warning(
            "SNMP probe skipped: install quirk-scanner[hw] to enable "
            "hardware SNMP fingerprinting (pysnmp not found)"
        )
        return dict(_NULL_RESULT)

    try:
        return asyncio.run(_async_probe(host, community, timeout))
    except Exception as exc:
        _LOG.debug("SNMP probe %s failed: %s", host, exc)
        return dict(_NULL_RESULT)


def scan_snmp_targets(
    hosts: List[str],
    community: str = "public",
    timeout: int = 3,
    logger=None,
) -> List[Dict[str, Optional[str]]]:
    """Probe a list of hosts via SNMPv2c concurrently.

    Mirrors ``fingerprint_hardware()`` concurrency pattern using
    ThreadPoolExecutor.  Each result dict includes the probe keys plus
    ``host``, ``vendor``, and ``model`` from ``parse_sysdescr``.

    Args:
        hosts:     List of IP addresses or hostnames to probe.
        community: SNMPv2c community string (default "public").
        timeout:   Per-probe timeout in seconds (default 3).
        logger:    Optional structured logger for verbose output.

    Returns:
        List of result dicts, same length as ``hosts``. Each dict has keys:
        ``host``, ``snmp_sysdescr``, ``snmp_sysname``, ``snmp_sysobjectid``,
        ``vendor``, ``model``.
    """
    results: List[Dict[str, Optional[str]]] = []

    if not hosts:
        return results

    def _probe_one(host: str) -> Dict[str, Optional[str]]:
        probe = probe_snmp_target(host, community=community, timeout=timeout)
        parsed = parse_sysdescr(probe.get("snmp_sysdescr"))
        return {
            "host": host,
            "snmp_sysdescr": probe.get("snmp_sysdescr"),
            "snmp_sysname": probe.get("snmp_sysname"),
            "snmp_sysobjectid": probe.get("snmp_sysobjectid"),
            "vendor": parsed.get("vendor", "Unknown"),
            "model": parsed.get("model"),
        }

    with ThreadPoolExecutor(max_workers=min(8, len(hosts))) as ex:
        futures = {ex.submit(_probe_one, h): h for h in hosts}
        for f in as_completed(futures):
            try:
                results.append(f.result())
            except Exception as exc:
                host = futures[f]
                _LOG.debug("scan_snmp_targets %s error: %s", host, exc)
                results.append({
                    "host": host,
                    "snmp_sysdescr": None,
                    "snmp_sysname": None,
                    "snmp_sysobjectid": None,
                    "vendor": "Unknown",
                    "model": None,
                })

    return results
