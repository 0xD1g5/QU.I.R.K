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
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Dict, List, Optional

from quirk.util.safe_exc import safe_str

if TYPE_CHECKING:
    from quirk.config import SnmpV3Credential

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
    # Phase 139 SNMPV3-01/02/04: v3arch sibling import block. Both v1arch
    # (v2c) and v3arch (v3 USM) live in the SAME pysnmp package/pin — one
    # _PYSNMP_AVAILABLE flag covers both.
    from pysnmp.hlapi.v3arch.asyncio import (
        ObjectIdentity as ObjectIdentityV3,
        ObjectType as ObjectTypeV3,
        SnmpEngine,
        UdpTransportTarget as UdpTransportTargetV3,
        UsmUserData,
        get_cmd as get_cmd_v3,
        usmAesCfb128Protocol,
        usmAesCfb192Protocol,
        usmAesCfb256Protocol,
        usmHMAC128SHA224AuthProtocol,
        usmHMAC192SHA256AuthProtocol,
        usmHMAC256SHA384AuthProtocol,
        usmHMAC384SHA512AuthProtocol,
        usmHMACSHAAuthProtocol,
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
    "snmp_version_used": None,
    "snmp_security_level": None,
    "snmp_v3_failure_kind": None,
}

# ---------------------------------------------------------------------------
# Phase 139 SNMPV3-02: distinct SNMP mode/security-level labels.
#
# Six distinct strings — never collapse noAuthNoPriv into authenticated v3,
# and never collapse a target-side protocol mismatch (D-02) into the generic
# v3-failed-fell-back state.
# ---------------------------------------------------------------------------
SNMP_MODE_V3_AUTH_PRIV = "v3 auth+priv"
SNMP_MODE_V3_NO_AUTH_PRIV = "v3 noAuthNoPriv"
# Alias — 139-02 acceptance criteria references this name; same value as
# SNMP_MODE_V3_NO_AUTH_PRIV (the name the 139-00 RED contract test imports).
SNMP_MODE_V3_NOAUTH = SNMP_MODE_V3_NO_AUTH_PRIV
SNMP_MODE_V2C = "v2c"
SNMP_MODE_V3_FAILED = "v3-failed-fell-back"
SNMP_MODE_V3_PROTOCOL_MISMATCH = "v3-protocol-mismatch"
SNMP_MODE_NONE = "none"

# ---------------------------------------------------------------------------
# Phase 139 SNMPV3-04: v3 USM engine-ID discovery round-trip needs a larger
# per-OID timeout budget than the v2c path.
# ---------------------------------------------------------------------------
SNMP_V3_TIMEOUT_MULTIPLIER = 2


def _derive_v3_timeout(timeout: int) -> int:
    """Re-derive the per-OID timeout budget for the v3 USM discovery round-trip.

    SNMPV3-04: the v3 budget must NOT reuse the v2c budget verbatim — engine-ID
    discovery adds an extra round-trip.
    """
    return timeout * SNMP_V3_TIMEOUT_MULTIPLIER


# ---------------------------------------------------------------------------
# Phase 139 SNMPV3-02 (blocker fix): the operator's configured auth/priv
# protocol name must select the ACTUAL pysnmp protocol object — never
# hardcoded to base SHA-1/AES-128. Key sets MUST equal
# quirk.config._SNMP_V3_AUTH_ALLOWED / _SNMP_V3_PRIV_ALLOWED.
# ---------------------------------------------------------------------------
if _PYSNMP_AVAILABLE:
    _SNMP_V3_AUTH_PROTO_MAP = {
        "SHA": usmHMACSHAAuthProtocol,
        "SHA224": usmHMAC128SHA224AuthProtocol,
        "SHA256": usmHMAC192SHA256AuthProtocol,
        "SHA384": usmHMAC256SHA384AuthProtocol,
        "SHA512": usmHMAC384SHA512AuthProtocol,
    }
    _SNMP_V3_PRIV_PROTO_MAP = {
        "AES": usmAesCfb128Protocol,
        "AES128": usmAesCfb128Protocol,
        "AES192": usmAesCfb192Protocol,
        "AES256": usmAesCfb256Protocol,
    }
else:
    _SNMP_V3_AUTH_PROTO_MAP = {}
    _SNMP_V3_PRIV_PROTO_MAP = {}


def _classify_v3_failure(error_indication: object) -> str:
    """Classify a pysnmp USM errorIndication as a distinct crypto-hygiene state.

    D-02 (RESEARCH Open Question 1): a target-side weak-protocol offering
    (unsupported security level / unsupported auth or priv protocol) surfaces
    as a DISTINCT "protocol-mismatch" state, never collapsed into the generic
    wrong-password/timeout "auth-failed" bucket.
    """
    text = safe_str(error_indication) if isinstance(error_indication, BaseException) else str(error_indication or "")
    lowered = text.lower()
    if (
        "unsupportedsecuritylevel" in lowered
        or "usmstatsunsupportedseclevels" in lowered
        or ("unsupported" in lowered and "security" in lowered)
        or ("decryptionerror" in lowered and "security" in lowered)
    ):
        return "protocol-mismatch"
    return "auth-failed"

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
            except Exception as exc:
                _LOG.debug("SNMP OID %s probe %s failed: %s", oid_str, host, safe_str(exc))
    except Exception as exc:
        _LOG.debug("SNMP transport %s failed: %s", host, safe_str(exc))
    finally:
        try:
            dispatcher.transport_dispatcher.close_dispatcher()
        except Exception:
            pass
    return result


async def _async_probe_v3(
    host: str,
    credential: "SnmpV3Credential",
    timeout: int,
) -> Dict[str, Optional[str]]:
    """Async SNMPv3 USM GET for sysDescr, sysName, sysObjectID via pysnmp 7.

    Mirrors ``_async_probe`` exactly except: uses USM (UsmUserData) instead of
    a plain community string, selects the operator's CONFIGURED auth/priv
    protocol objects (never hardcoded to base SHA-1/AES-128 — blocker fix),
    re-derives the timeout budget (SNMPV3-04), and records the ACTUAL
    negotiated security level (SNMPV3-02 / D-02 Pitfall 3). Resolved
    auth_key/priv_key values never leave this function's scope — only
    protocol-name metadata is returned (SNMPV3-03).
    """
    result: Dict[str, Optional[str]] = dict(_NULL_RESULT)
    engine = SnmpEngine()
    try:
        auth_key = os.environ.get(credential.auth_key_env, "") if credential.auth_key_env else ""
        priv_key = os.environ.get(credential.priv_key_env, "") if credential.priv_key_env else ""
        auth_proto = _SNMP_V3_AUTH_PROTO_MAP[credential.auth_protocol]
        priv_proto = _SNMP_V3_PRIV_PROTO_MAP[credential.priv_protocol] if priv_key else None
        usm_data = UsmUserData(
            credential.username,
            authKey=auth_key or None,
            authProtocol=auth_proto if auth_key else None,
            privKey=priv_key or None,
            privProtocol=priv_proto,
        )
        target = await UdpTransportTargetV3.create(
            (host, 161),
            timeout=_derive_v3_timeout(timeout),
            retries=1,
        )
        failure_kind: Optional[str] = None
        for oid_str, key in (
            (_OID_SYSDESCR, "snmp_sysdescr"),
            (_OID_SYSNAME, "snmp_sysname"),
            (_OID_SYSOBJECTID, "snmp_sysobjectid"),
        ):
            try:
                err_indication, err_status, _err_index, var_binds = await get_cmd_v3(
                    engine,
                    usm_data,
                    target,
                    ObjectTypeV3(ObjectIdentityV3(oid_str)),
                )
                if err_indication:
                    failure_kind = _classify_v3_failure(err_indication)
                    _LOG.debug(
                        "SNMPv3 OID %s probe %s failed: %s", oid_str, host, safe_str(err_indication)
                    )
                    continue
                if not err_status and var_binds:
                    _oid, val = var_binds[0]
                    str_val = str(val) if val is not None else None
                    if str_val and str_val not in ("", "noSuchObject", "noSuchInstance"):
                        result[key] = str_val
            except Exception as exc:
                failure_kind = _classify_v3_failure(exc)
                _LOG.debug("SNMPv3 OID %s probe %s failed: %s", oid_str, host, safe_str(exc))

        if failure_kind is not None and not any(
            result[k] for k in ("snmp_sysdescr", "snmp_sysname", "snmp_sysobjectid")
        ):
            result["snmp_v3_failure_kind"] = failure_kind
            # snmp_version_used stays None (fell through) — never claim v3
            # succeeded when every OID failed.
        else:
            result["snmp_version_used"] = "v3"
            if not auth_key:
                result["snmp_security_level"] = "noAuthNoPriv"
            elif priv_key:
                result["snmp_security_level"] = "authPriv"
            else:
                result["snmp_security_level"] = "authNoPriv"
    except Exception as exc:
        result["snmp_v3_failure_kind"] = _classify_v3_failure(exc)
        _LOG.debug("SNMPv3 probe %s failed: %s", host, safe_str(exc))
    finally:
        try:
            engine.close_dispatcher()
        except Exception as exc:
            _LOG.debug("SNMPv3 engine close %s failed: %s", host, safe_str(exc))
    return result


def probe_snmp_target(
    host: str,
    community: str = "public",
    timeout: int = 3,
    version: str = "v2c",
    v3_credential: Optional["SnmpV3Credential"] = None,
) -> Dict[str, Optional[str]]:
    """Probe a single host via SNMPv2c (or SNMPv3 USM) and return sysDescr OIDs.

    Advisory guard: if pysnmp is not installed, logs a WARNING and returns a
    null-safe dict — never raises ImportError.

    Args:
        host:          IP address or hostname to probe (UDP port 161).
        community:     SNMPv2c community string (default "public"); ignored
                        when ``version="v3"``.
        timeout:       Per-OID GET timeout in seconds (default 3); re-derived
                        for the v3 USM discovery round-trip (SNMPV3-04).
        version:       "v2c" (default, unchanged path) or "v3" (SNMPv3 USM —
                        requires ``v3_credential``).
        v3_credential: SnmpV3Credential to use when ``version="v3"``.

    Returns:
        Dict with keys: ``snmp_sysdescr``, ``snmp_sysname``, ``snmp_sysobjectid``,
        ``snmp_version_used``, ``snmp_security_level``, ``snmp_v3_failure_kind``.
        All values are ``str | None``; None on failure or when pysnmp absent.
    """
    if not _PYSNMP_AVAILABLE:
        _LOG.warning(
            "SNMP probe skipped: install quirk-scanner[hw] to enable "
            "hardware SNMP fingerprinting (pysnmp not found)"
        )
        return dict(_NULL_RESULT)

    if version == "v3" and v3_credential is not None:
        try:
            return asyncio.run(_async_probe_v3(host, v3_credential, timeout))
        except Exception as exc:
            _LOG.debug("SNMPv3 probe %s failed: %s", host, safe_str(exc))
            return dict(_NULL_RESULT)

    try:
        result = asyncio.run(_async_probe(host, community, timeout))
        result.setdefault("snmp_version_used", "v2c")
        for key in ("snmp_security_level", "snmp_v3_failure_kind"):
            result.setdefault(key, None)
        return result
    except Exception as exc:
        _LOG.debug("SNMP probe %s failed: %s", host, safe_str(exc))
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
