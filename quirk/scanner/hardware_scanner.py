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


def fingerprint_one(
    ep: CryptoEndpoint,
    timeout: int = 3,
    logger: Optional[Logger] = None,
) -> HardwareDevice:
    """Fingerprint a single ``CryptoEndpoint`` against the HARDWARE_MATRIX.

    Returns a ``HardwareDevice`` for every input endpoint including
    ``vendor="Unknown"`` rows (D-06 — Unknown rows are never suppressed).

    Pipeline:
    1. Read SSH banner from ``ep.service_detail`` (D-03).
    2. Match against HARDWARE_MATRIX; assign confidence grade (D-05).
    3. If banner yielded no known vendor, probe HTTP management interfaces (D-04).
    4. Return device — never raises (exceptions are logged via safe_str).
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
            from quirk.scanner.snmp_scanner import probe_snmp_target, parse_sysdescr as _parse_sd
            host = getattr(ep, "host", "")
            _snmp_result = probe_snmp_target(host, community="public", timeout=timeout)
            _raw = _snmp_result.get("snmp_sysdescr")
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
            # Store raw SNMP fields; ORM columns added in Plan 133-02
            try:
                device.snmp_sysdescr = _raw
                device.snmp_sysname = _snmp_result.get("snmp_sysname")
                device.snmp_sysobjectid = _snmp_result.get("snmp_sysobjectid")
                device.snmp_vendor = (
                    _parsed.get("vendor", "Unknown")
                    if _raw
                    else None
                )
            except AttributeError:
                # ORM columns not yet migrated (Plan 133-02) — skip assignment
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
) -> List[HardwareDevice]:
    """Fingerprint a batch of ``CryptoEndpoint`` objects concurrently.

    Mirrors ``scan_ssh_targets`` concurrency pattern (ThreadPoolExecutor).
    Returns exactly one ``HardwareDevice`` per input endpoint (D-06).
    ``vendor=Unknown`` rows are never dropped.

    Args:
        endpoints: Pre-scanned SSH endpoints with ``service_detail`` set.
        timeout:   Per-probe timeout in seconds (default 3 s).
        logger:    Optional structured logger for verbose output.

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
            ex.submit(fingerprint_one, ep, timeout, logger): ep
            for ep in endpoints
        }
        for f in as_completed(futures):
            results.append(f.result())

    if logger:
        identified = sum(1 for d in results if d.vendor != "Unknown")
        logger.stamp(
            f"hardware fingerprint complete: {identified}/{len(results)} identified"
        )

    return results
