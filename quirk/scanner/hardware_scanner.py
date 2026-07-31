"""Agentless hardware device fingerprinting — Phase 127 (HWCOMPAT-01).

Reads the SSH banner already stored in ``CryptoEndpoint.service_detail`` by
``ssh_scanner.py`` (D-03), probes HTTP management interfaces best-effort (D-04),
matches against ``HARDWARE_MATRIX``, assigns a confidence grade (D-05), and
returns ``List[HardwareDevice]`` — including never-suppressed ``vendor=Unknown``
rows (D-06).

Hardware findings are advisory-only: no counter is added to SCORE_WEIGHTS and
``compute_readiness_score()`` is not modified (D-01).

Phase 127 — HWCOMPAT-01.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date as _date, timezone
from typing import List, Optional

from quirk.models import CryptoEndpoint, HardwareDevice
from quirk.scanner.hardware_meta import HARDWARE_MATRIX
from quirk.logging_util import Logger
from quirk.util.safe_exc import safe_str

_LOG = logging.getLogger(__name__)

# HTTP management probe: candidate ports and paths (D-04)
_HTTP_MGMT_PORTS = (443, 8443, 8080, 80)
_HTTP_MGMT_PATHS = ("/api/system/info", "/mgmt/", "/")

# Read a bounded body slice to avoid consuming large responses (T-127-04)
_BODY_SLICE = 4096

# ---------------------------------------------------------------------------
# Phase 140 BRIDGE-04 D-03: sensor-local /24 gateway pre-check.
#
# Replicates the pairing predicate from the cbom bridge module's
# _detect_crypto_bridges as a SCOPED LOCAL helper — the scanner layer must
# never depend on the cbom layer (cross-layer import direction prohibited,
# RESEARCH Open Question 2). This is
# a pre-filtering optimization only; it makes NO cross-device promotion
# decision (that stays console-side in _confirm_upstream_mitigation, 140-02).
# ---------------------------------------------------------------------------
_BRIDGE_PQC_CAPABLE: frozenset[str] = frozenset({"partial", "supported"})
_BRIDGE_LEGACY_STATUS: frozenset[str] = frozenset({"unsupported", "vendor-silent", "unknown"})

# Bound the stored bridge_evidence_json size before writing (V5 input
# validation) — an oversized/malicious ARP table must not bloat the DB row.
_BRIDGE_EVIDENCE_MAX_BYTES = 8192


def _match_matrix(text: str) -> Optional[dict]:
    """Return the first HARDWARE_MATRIX entry whose model_pattern matches *text*.

    Uses ``re.search`` with ``re.IGNORECASE`` on a bounded string.
    Returns None if no entry matches.
    """
    if not text:
        return None
    for entry in HARDWARE_MATRIX.get("entries", []):
        pattern = entry.get("model_pattern", "")
        if not pattern:
            continue
        try:
            if re.search(pattern, text, re.IGNORECASE):
                return entry
        except re.error:
            # Malformed pattern — skip silently (T-127-04 guard)
            continue
    return None


def _apply_entry(device: HardwareDevice, entry: dict, method: str, body: str = "") -> None:
    """Populate device fields from a matched HARDWARE_MATRIX entry.

    Confidence per D-05:
    - ``high``   — explicit model token captured (regex match beyond bare vendor)
    - ``medium`` — vendor pattern matched, no distinct model token in text
    Caller is responsible for setting ``fingerprint_method``.
    """
    device.vendor = entry.get("vendor", "Unknown")
    device.pqc_status = entry.get("pqc_status", "unknown")
    device.fingerprint_method = method

    # Parse eol_date safely
    eol_raw = entry.get("eol_date")
    if eol_raw:
        try:
            device.eol_date = _date.fromisoformat(eol_raw)
        except (ValueError, TypeError):
            device.eol_date = None
    else:
        device.eol_date = None

    # Confidence: high if a version/model token follows the vendor keyword (D-05)
    # We use a secondary check: does the matched text contain digit sequences or
    # additional model tokens beyond the bare vendor name?
    pattern = entry.get("model_pattern", "")
    combined = body if body else (device.raw_banner or "")
    try:
        m = re.search(pattern, combined, re.IGNORECASE) if pattern else None
    except re.error:
        m = None

    if m:
        full_match = m.group(0)
        # High confidence when the match string itself contains digits or a
        # model-differentiating token (e.g. "Cisco-1.25", "iLO5", "BIG-IP")
        if re.search(r"\d", full_match):
            device.confidence = "high"
        elif len(full_match.split()) > 1 or "-" in full_match or "_" in full_match:
            device.confidence = "high"
        else:
            device.confidence = "medium"
        # Capture model from matched group when a version token is present
        device.model = full_match if full_match != device.vendor else None
    else:
        device.confidence = "medium"


def _probe_http_mgmt(host: str, port: int, timeout: int) -> Optional[dict]:
    """Best-effort HTTP management interface probe (D-04).

    GETs candidate paths on a single port. Parses response headers and a
    bounded body slice for vendor tokens. Returns a match dict with keys
    ``"entry"`` (HARDWARE_MATRIX entry) and ``"body"`` (matched text fragment)
    on first match, or ``None`` on any exception or no match.

    Connection refused / timeout silently returns None (D-04 — fail to Unknown).
    Body slice is bounded to ``_BODY_SLICE`` bytes (T-127-04).
    """
    scheme = "https" if port in (443, 8443) else "http"
    for path in _HTTP_MGMT_PATHS:
        url = f"{scheme}://{host}:{port}{path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "QUIRK-HW/1.0"})
            ctx = None
            if scheme == "https":
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                # Collect headers into a single searchable string
                header_text = " ".join(
                    f"{k}: {v}" for k, v in resp.headers.items()
                )
                body_raw = resp.read(_BODY_SLICE)
                body_text = body_raw.decode(errors="ignore")
                combined = header_text + " " + body_text

                entry = _match_matrix(combined)
                if entry:
                    return {"entry": entry, "body": combined}
        except Exception:
            # Any error (connection refused, timeout, SSL, HTTP error, etc.)
            # is silently swallowed — D-04: best-effort, fail to Unknown.
            continue
    return None


def _subnet_24(ip: str) -> str:
    """Return the /24 prefix of *ip*, or *ip* unchanged for non-IPv4 addresses.

    Duplicated verbatim from ``quirk.cbom.bridge._subnet_24`` — do not import
    across the scanner/cbom layer boundary (see module-level comment above).
    """
    parts = ip.split(".")
    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        return ".".join(parts[:3])
    return ip


def _local_gateway_candidates(devices: List[HardwareDevice]) -> List[HardwareDevice]:
    """D-03 sensor-local pre-check: flag PQC-capable gateway devices sharing a
    /24 subnet with a legacy backend, scoped to this sensor's own scan batch.

    This is a pre-filtering optimization only — it performs NO cross-device
    promotion decision (that stays console-side in
    ``quirk.cbom.bridge._confirm_upstream_mitigation``, plan 140-02). If a
    sensor's local batch misses a cross-sensor pair, that device simply never
    gets probed and stays ``partial_only`` — no correctness regression.
    """
    subnet_to_devices: dict[str, list[int]] = {}
    for i, dev in enumerate(devices):
        prefix = _subnet_24(getattr(dev, "host", "") or "")
        subnet_to_devices.setdefault(prefix, []).append(i)

    gateway_indices: set[int] = set()
    for _prefix, indices in subnet_to_devices.items():
        if len(indices) < 2:
            continue
        pqc_indices = [
            i for i in indices
            if (devices[i].pqc_status or "").lower() in _BRIDGE_PQC_CAPABLE
        ]
        legacy_indices = [
            i for i in indices
            if (devices[i].pqc_status or "").lower() in _BRIDGE_LEGACY_STATUS
        ]
        if pqc_indices and legacy_indices:
            gateway_indices.update(pqc_indices)

    return [devices[i] for i in sorted(gateway_indices)]


def _confirm_bridge_evidence(device: HardwareDevice, timeout: int, cfg=None) -> None:
    """Walk *device*'s (a pre-check-flagged gateway candidate's) ARP table and
    persist raw evidence into ``bridge_evidence_json``/``bridge_confirmed_at``
    ONLY when the walk returned a non-empty table (BRIDGE-02).

    Zero cross-device promotion decision happens here — pure per-device
    evidence collection; the console decides promotion in the cbom bridge
    module's ``_confirm_upstream_mitigation`` (plan 140-02). Stores only
    IP/MAC/OID
    facts — never the community string or USM passphrase (T-140-03). Bounds
    the stored JSON size before writing (V5 input validation / T-140-04).
    """
    try:
        from quirk.scanner.snmp_scanner import walk_arp_table

        host = getattr(device, "host", "")
        _connectors = getattr(cfg, "connectors", None) if cfg is not None else None
        _v3_creds_map = getattr(_connectors, "snmp_v3_credentials", None) or {}
        _v3_cred = _v3_creds_map.get(host)

        entries = walk_arp_table(host, community="public", timeout=timeout, v3_credential=_v3_cred)
        if not entries:
            return  # D-05: silently stays partial_only — no evidence collected

        payload = json.dumps(entries)
        if len(payload.encode("utf-8")) > _BRIDGE_EVIDENCE_MAX_BYTES:
            # Truncate oversized evidence before persisting (V5 input validation).
            while entries and len(json.dumps(entries).encode("utf-8")) > _BRIDGE_EVIDENCE_MAX_BYTES:
                entries = entries[: len(entries) // 2] if len(entries) > 1 else []
            if not entries:
                return  # still oversized after truncation — reject silently
            payload = json.dumps(entries)

        device.bridge_evidence_json = payload
        device.bridge_confirmed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    except Exception as exc:
        _LOG.debug(
            "Bridge-evidence ARP walk %s failed: %s", getattr(device, "host", "?"), safe_str(exc)
        )


def fingerprint_one(
    ep: CryptoEndpoint,
    timeout: int = 3,
    logger: Optional[Logger] = None,
    cfg=None,
) -> HardwareDevice:
    """Fingerprint a single ``CryptoEndpoint`` against the HARDWARE_MATRIX.

    Returns a ``HardwareDevice`` for every input endpoint including
    ``vendor="Unknown"`` rows (D-06 — Unknown rows are never suppressed).

    Pipeline:
    1. Read SSH banner from ``ep.service_detail`` (D-03).
    2. Match against HARDWARE_MATRIX; assign confidence grade (D-05).
    3. If banner yielded no known vendor, probe HTTP management interfaces (D-04).
    4. Return device — never raises (exceptions are logged via safe_str).

    Args:
        cfg: Optional ``AppConfig``. When present, ``cfg.connectors.
            snmp_v3_credentials`` drives the Step 3 SNMPv3-first fallback
            ladder (Phase 139 SNMPV3-02); when absent, Step 3 behaves exactly
            as before (v2c-only, unauthenticated).
    """
    # Default: Unknown device — always returned on any code path (D-06)
    device = HardwareDevice(
        host=getattr(ep, "host", ""),
        port=getattr(ep, "port", 0),
        vendor="Unknown",
        pqc_status="unknown",
        confidence="unknown",
        fingerprint_method="unknown",
        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        raw_banner=getattr(ep, "service_detail", None),
    )

    try:
        banner = getattr(ep, "service_detail", "") or ""

        # ── Step 1: SSH banner match (D-03) ─────────────────────────────
        if banner:
            device.fingerprint_method = "ssh_banner"
            entry = _match_matrix(banner)
            if entry:
                _apply_entry(device, entry, method="ssh_banner", body=banner)
            else:
                # Banner present but no matrix match → low confidence (D-05)
                device.confidence = "low"

        # ── Step 2: HTTP management probe (D-04) ────────────────────────
        # Only attempt if the SSH banner path did not already identify a known vendor.
        # This avoids redundant network calls when the banner is sufficient.
        if device.vendor == "Unknown":
            host = getattr(ep, "host", "")
            for port in _HTTP_MGMT_PORTS:
                result = _probe_http_mgmt(host, port, timeout)
                if result:
                    _apply_entry(
                        device,
                        result["entry"],
                        method="http_mgmt",
                        body=result["body"],
                    )
                    break  # First match wins

        # ── Step 3: SNMP probe (Phase 133 SNMP-01 / D-01/D-02) ─────────────
        # Only attempt if SSH banner + HTTP mgmt both failed to identify a known vendor.
        if device.vendor == "Unknown":
            from quirk.scanner.snmp_scanner import (
                probe_snmp_target,
                parse_sysdescr as _parse_sd,
                SNMP_MODE_V3_AUTH_PRIV,
                SNMP_MODE_V3_NOAUTH,
                SNMP_MODE_V2C,
                SNMP_MODE_V3_FAILED,
                SNMP_MODE_V3_PROTOCOL_MISMATCH,
                SNMP_MODE_NONE,
            )
            host = getattr(ep, "host", "")

            # Phase 139 SNMPV3-02: v3 -> v2c -> none fallback ladder. A
            # per-host credential (cfg.connectors.snmp_v3_credentials)
            # triggers a v3 attempt first; the outcome dictates whether v2c
            # still runs and which distinct snmp_version state is recorded
            # (D-02 protocol-mismatch vs D-03 failed-fell-back vs plain v2c).
            _connectors = getattr(cfg, "connectors", None) if cfg is not None else None
            _v3_creds_map = getattr(_connectors, "snmp_v3_credentials", None) or {}
            _v3_cred = _v3_creds_map.get(host)

            _snmp_version_label = None
            _snmp_result = None

            if _v3_cred is not None:
                _v3_result = probe_snmp_target(
                    host, version="v3", v3_credential=_v3_cred, timeout=timeout
                )
                if _v3_result.get("snmp_version_used") == "v3":
                    # SUCCESS — never collapse noAuthNoPriv into authPriv (D-02/Pitfall 3).
                    _snmp_result = _v3_result
                    _snmp_version_label = (
                        SNMP_MODE_V3_AUTH_PRIV
                        if _v3_result.get("snmp_security_level") == "authPriv"
                        else SNMP_MODE_V3_NOAUTH
                    )
                    # Protocol names are accurate because 139-02's probe used
                    # exactly these protocol objects — only on success.
                    try:
                        device.snmp_auth_protocol = _v3_cred.auth_protocol
                        device.snmp_priv_protocol = _v3_cred.priv_protocol
                    except AttributeError:
                        pass
                    # Do NOT run the v2c fallback on v3 success.
                elif _v3_result.get("snmp_v3_failure_kind") == "protocol-mismatch":
                    # D-02: target offered only weaker-than-configured protocols.
                    # Distinct crypto-hygiene state takes precedence over the
                    # benign v2c fallback outcome; still probe v2c for continuity.
                    _snmp_version_label = SNMP_MODE_V3_PROTOCOL_MISMATCH
                    _snmp_result = probe_snmp_target(host, community="public", timeout=timeout)
                else:
                    # Generic v3 failure (auth-failed or unset). v3 WAS
                    # configured and attempted, so a v2c success must not
                    # masquerade as an intentional v2c-only scan (D-03).
                    _snmp_version_label = SNMP_MODE_V3_FAILED
                    _snmp_result = probe_snmp_target(host, community="public", timeout=timeout)
            else:
                _snmp_result = probe_snmp_target(host, community="public", timeout=timeout)
                _snmp_version_label = (
                    SNMP_MODE_V2C if _snmp_result.get("snmp_sysdescr") else SNMP_MODE_NONE
                )

            _raw = _snmp_result.get("snmp_sysdescr") if _snmp_result else None
            if _raw:
                _parsed = _parse_sd(_raw)
                if _parsed.get("vendor") and _parsed["vendor"] != "Unknown":
                    device.vendor = _parsed["vendor"]
                    device.model = _parsed.get("model")
                    device.fingerprint_method = "snmp"
                    device.confidence = "medium"
                    # Attempt HARDWARE_MATRIX match for pqc_status
                    _entry = _match_matrix(_raw)
                    if _entry:
                        _apply_entry(device, _entry, method="snmp", body=_raw)
            # Store raw SNMP fields; ORM columns added in Plan 133-02 / 139-01
            try:
                device.snmp_sysdescr = _raw
                device.snmp_sysname = _snmp_result.get("snmp_sysname") if _snmp_result else None
                device.snmp_sysobjectid = (
                    _snmp_result.get("snmp_sysobjectid") if _snmp_result else None
                )
                device.snmp_vendor = (
                    _parsed.get("vendor", "Unknown")
                    if _raw
                    else None
                )
                device.snmp_version = _snmp_version_label
            except AttributeError:
                # ORM columns not yet migrated — skip assignment
                pass

    except Exception as e:
        if logger:
            logger.v(
                f"HW {getattr(ep, 'host', '?')}:{getattr(ep, 'port', '?')} "
                f"fingerprint error: {safe_str(e)}"
            )
        # Never re-raise — always return device (D-06)

    return device


def fingerprint_hardware(
    endpoints: List[CryptoEndpoint],
    timeout: int = 3,
    logger: Optional[Logger] = None,
    cfg=None,
) -> List[HardwareDevice]:
    """Fingerprint a batch of ``CryptoEndpoint`` objects concurrently.

    Mirrors ``scan_ssh_targets`` concurrency pattern (ThreadPoolExecutor).
    Returns exactly one ``HardwareDevice`` per input endpoint (D-06).
    ``vendor=Unknown`` rows are never dropped.

    Args:
        endpoints: Pre-scanned SSH endpoints with ``service_detail`` set.
        timeout:   Per-probe timeout in seconds (default 3 s).
        logger:    Optional structured logger for verbose output.
        cfg:       Optional ``AppConfig`` — forwarded to ``fingerprint_one``
                   so Step 3's SNMPv3-first ladder (Phase 139) can look up
                   per-host credentials.

    Returns:
        List of ``HardwareDevice`` rows, same length as ``endpoints``.
    """
    results: List[HardwareDevice] = []

    if not endpoints:
        return results

    if logger:
        logger.stamp(f"Starting hardware fingerprint: {len(endpoints)} endpoints")

    with ThreadPoolExecutor(max_workers=min(8, len(endpoints))) as ex:
        futures = {
            ex.submit(fingerprint_one, ep, timeout, logger, cfg): ep
            for ep in endpoints
        }
        for f in as_completed(futures):
            results.append(f.result())

    # ── Phase 140 BRIDGE-04 D-03: sensor-local gateway pre-check + ARP walk ──
    # Targeted, not run for every SNMP-enabled device — only gateway
    # candidates the local /24 pre-check flags get the extra ARP-table walk.
    _gateway_candidates = _local_gateway_candidates(results)
    for _gw in _gateway_candidates:
        _confirm_bridge_evidence(_gw, timeout=timeout, cfg=cfg)

    if logger:
        identified = sum(1 for d in results if d.vendor != "Unknown")
        logger.stamp(
            f"hardware fingerprint complete: {identified}/{len(results)} identified"
        )

    return results
