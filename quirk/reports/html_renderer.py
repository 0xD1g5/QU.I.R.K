"""Jinja2-based standalone HTML report renderer for QU.I.R.K. (Phase 7, D-08 to D-12)."""
import base64
import html as _html
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from quirk.util.safe_exc import safe_str
from quirk.util.sanitize import sanitize_scanner_text
from quirk.reports.content_model import ExecContent, assert_congruent, NOT_COMPUTED_STATEMENT, effective_score_divisor, effective_domain_counts  # D-03 / Phase 98: shared content model
from quirk.scanner import hw_cve  # Phase 142 CVE-01: NVD link helper
from quirk.severity_bands import band_for_score, cap_band_for_severity, cap_reason  # Phase 184.4 D-05


# Phase 78 / HARDEN-04: PDF metadata constants. Title flows from HTML <title>;
# Author is injected post-render via pypdf because Chromium's print-to-PDF does
# not honor <meta name="author">.
PDF_TITLE = "QU.I.R.K. Cryptographic Readiness Report"
PDF_AUTHOR = "QU.I.R.K. Scanner"


def _score_color(band: str) -> str:
    return {
        "EXCELLENT": "#4caf50",
        "GOOD": "#66bb6a",
        "MODERATE": "#f9a825",
        "FAIR": "#f57c00",
        "POOR": "#e53935",
    }.get(band, "#aaaaaa")


def _collect_algorithm_names(endpoints: List[Any]) -> List[str]:
    """Derive the unique algorithm names observed in this scan from endpoints.

    Sources: cipher_suite, cert_pubkey_alg, tls_supported_ciphers_sample.
    Returns a sorted list of unique non-empty algorithm/suite strings.
    """
    names: set = set()
    for ep in endpoints or []:
        for attr in ("cipher_suite", "cert_pubkey_alg"):
            val = getattr(ep, attr, "") or ""
            if isinstance(val, str) and val.strip():
                names.add(val.strip())
        sample = getattr(ep, "tls_supported_ciphers_sample", "") or ""
        if isinstance(sample, str) and sample.strip():
            for tok in sample.split(","):
                tok = tok.strip()
                if tok:
                    names.add(tok)
    return sorted(names)


def build_algorithm_inventory(endpoints: List[Any]) -> List[Dict[str, Any]]:
    """Build the `algorithms` template context (Phase 81 / CMVP-06).

    Each row carries: name, nist_level, fips_status, cmvp_coverage.

    `cmvp_coverage` is a comma-joined list of CMVP module names that cover the
    algorithm, or None for empty matches (the template renders the literal
    "Not in CMVP catalog" in that case).

    Implementation notes:
    - `quirk.compliance.cmvp.coverage_for_algorithm` is imported LAZILY (inside
      this function body) so module-import-time isn't broken if Plan 81-02 has
      not yet committed the cmvp module.
    - `quirk.cbom.classifier.classify_algorithm` provides the NIST level used
      by the existing _fips_status helper; both imports are deferred to keep
      module-load cost low for non-HTML reporting paths.
    - NEVER emits any `certified` boolean — only informational coverage strings
      (v4.10-D-01 invariant).
    """
    rows: List[Dict[str, Any]] = []

    # Lazy imports — Plan 81-02 lands quirk/compliance/cmvp.py concurrently;
    # quirk/cbom/builder.py + classifier.py are foundational and always present
    # but we defer to keep this helper cheap to import.
    try:
        from quirk.compliance.cmvp import coverage_for_algorithm
    except ImportError:
        # Plan 81-02 hasn't committed yet — render with empty coverage so the
        # template gracefully falls back to "Not in CMVP catalog" for every row.
        def coverage_for_algorithm(_name: str):  # type: ignore[no-redef]
            return []

    try:
        from quirk.cbom.classifier import classify_algorithm
        from quirk.cbom.builder import _fips_status
    except ImportError:
        def classify_algorithm(_name: str):  # type: ignore[no-redef]
            return (None, None, None)

        def _fips_status(_lvl):  # type: ignore[no-redef]
            return "non-approved"

    for name in _collect_algorithm_names(endpoints):
        try:
            _, nist_level, _ = classify_algorithm(name)
        except Exception:
            nist_level = None
        fips_status = _fips_status(nist_level)  # IN-02: prior `... or True` made the else branch dead
        try:
            coverage = coverage_for_algorithm(name) or []
        except Exception:
            coverage = []
        module_names = [
            (m.get("name") if isinstance(m, dict) else str(m))
            for m in coverage
            if (isinstance(m, dict) and m.get("name")) or (not isinstance(m, dict))
        ]
        cmvp_coverage = ", ".join(module_names) if module_names else None
        rows.append({
            "name": name,
            "nist_level": nist_level if nist_level is not None else "—",
            "fips_status": fips_status,
            "cmvp_coverage": cmvp_coverage,
        })
    return rows


def _severity_color(severity: str) -> str:
    return {
        "CRITICAL": "#e53935",
        "HIGH": "#f57c00",
        "MEDIUM": "#f9a825",
        "LOW": "#5c9cff",
        "INFO": "#888888",
    }.get(str(severity).upper(), "#888888")


# Use FileSystemLoader so templates are found without pip reinstall (RESEARCH.md Pattern 2).
# This works for both development installs and editable installs without package data rebuild.
_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# Phase 100 / CR-01: maximum logo file size (bytes) — generous for any real logo.
# Files larger than this are rejected with a stderr advisory; logo is omitted.
_MAX_LOGO_BYTES = 5 * 1024 * 1024  # 5 MB


def _load_logo_b64(logo_path):
    """Return (b64_string, mime_subtype) or (None, 'png') when logo absent/unreadable.

    Phase 100 / D-01 / D-03: base64-embed for offline HTML; None means omit logo region.
    T-100-LOGO: guards against missing/invalid/permission/large-file errors (graceful omit).

    Raises nothing — any failure path returns (None, 'png') per the D-03 contract.
    """
    if not logo_path:
        return None, "png"
    try:
        size = os.path.getsize(logo_path)
        if size > _MAX_LOGO_BYTES:
            print(
                f"Logo at {logo_path!r} exceeds size limit ({size} bytes > {_MAX_LOGO_BYTES}); "
                "logo omitted from report.",
                file=sys.stderr,
            )
            return None, "png"
        with open(logo_path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode("ascii")
        ext = os.path.splitext(logo_path)[1].lower().lstrip(".")
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png",
                "gif": "gif", "svg": "svg+xml"}.get(ext, "png")
        return b64, mime
    except Exception:
        return None, "png"


_SNMP_LABEL_MAP = {
    "v3 auth+priv": "v3 auth+priv",
    "v3 noAuthNoPriv": "v3 noAuthNoPriv",
    "v2c": "v2c",
    "v3-failed-fell-back": "v3 failed → v2c",
    "none": "No SNMP",
}


def _snmp_badge_label(d: Dict[str, Any]) -> str:
    """Map the projected snmp_version field to the verbatim UI-SPEC label.

    Returns "—" (em dash) when snmp_version is absent/null (SNMP never
    attempted for this device), reserving "No SNMP" for attempted-no-response.
    Reuses the exact five label strings from the UI-SPEC Copywriting Contract
    (Phase 139 SNMPV3-02) — no report-only synonyms.
    """
    raw = d.get("snmp_version")
    if not raw:
        return "—"
    return _SNMP_LABEL_MAP.get(raw, str(raw))


_BRIDGE_LABEL_MAP = {
    "upstream_mitigated": "SNMP-confirmed",
    "partial_only": "Partial (assumed)",
}

_BRIDGE_COLORS = {
    "upstream_mitigated": "hsl(213 94% 68%)",  # blue — NEVER the green success hue
    "partial_only": "hsl(38 92% 50%)",  # amber
}

_BRIDGE_CAVEAT = (
    "Based on SNMP-derived network-path evidence; not independently confirmed"
    " by traffic inspection."
)


def _bridge_badge_label(d: Dict[str, Any]) -> str:
    """Map the projected bridge_status field to the verbatim UI-SPEC label.

    Returns "" when bridge_status is absent/null (device is not part of a
    detected bridge pair) — callers render an em-dash cell in that case.
    Never surfaces the raw enum string ("partial_only" / "upstream_mitigated").
    """
    raw = d.get("bridge_status")
    if not raw:
        return ""
    return _BRIDGE_LABEL_MAP.get(raw, "")


# Phase 141 OTICS-05 — Modbus/TCP + BACnet/IP fingerprint badge labels.
# Both columns share one probe_state vocabulary (UI-SPEC); the "identified"
# label is column-specific ("Modbus" or "BACnet").
_PROBE_STATE_LABEL_MAP = {
    "no_response": "No response",
    "no_match": "No match",
    "aborted_anomalous_response": "Probe aborted",
}

_OTICS_ABORT_CAVEAT = (
    "Modbus/BACnet probe aborted — anomalous response. The device returned a"
    " malformed frame, reset the connection, or timed out; QU.I.R.K. stopped"
    " probing this host per its one-strike safety policy. Worth a closer"
    " manual look."
)


def _probe_state_label(raw: Any, identified_label: str) -> str:
    """Map a raw modbus_probe_state/bacnet_probe_state value to its UI-SPEC label.

    Returns "—" (em dash) when the probe was never attempted for this device
    (null/absent) — distinct from "No response"/"No match" (attempted, no
    usable answer) and from "Probe aborted" (D-13 circuit-breaker state).
    """
    if not raw:
        return "—"
    if raw == "identified":
        return identified_label
    return _PROBE_STATE_LABEL_MAP.get(raw, str(raw))


def _modbus_badge_label(d: Dict[str, Any]) -> str:
    return _probe_state_label(d.get("modbus_probe_state"), "Modbus")


def _bacnet_badge_label(d: Dict[str, Any]) -> str:
    return _probe_state_label(d.get("bacnet_probe_state"), "BACnet")


# Phase 142 CVE-01/D-13/D-14/D-15 — curated firmware CVE advisory column.
# Neutral badge only — never the green success hue nor a red severity hue
# (this is advisory correlation, not a scored/severity finding, CVE-01).
_CVE_BADGE_COLOR = "hsl(38 92% 50%)"  # amber — distinct from --accent blue (report links/headings
# use the same blue family as the old badge hue, hsl(213...), so the badge blended into the CVE-ID
# links directly beneath it; amber matches the docx_renderer palette precedent and stays non-severity

_CVE_NO_CORRELATION_CAVEAT = "no CVE correlation attempted"

_CVE_STALENESS_CAVEAT = (
    "CVE snapshot last verified {last_verified} — may be outdated (re-verified"
    " every {threshold} days)."
)

_CVE_SECTION_NOTE = (
    "CVE correlation is advisory — not a severity finding or score input."
    " Verify each CVE against the linked NVD entry before acting on it."
)


def _cve_cell_html(d: Dict[str, Any]) -> str:
    """Renders the per-device CVE advisory cell (D-13/D-14/D-15).

    Three distinguishable states (Pitfall 4 — never collapsed):
    (a) cve_attempted falsy -> "" (D-03 silent skip, vendor unidentified —
        callers render an em-dash cell in that case, matching other columns).
    (b) cve_attempted True and matches empty -> literal caveat text (CVE-03).
    (c) matches present -> neutral badge + per-CVE clickable NVD links.
    """
    if not d.get("cve_attempted"):
        return ""

    matches = d.get("cve_matches") or []
    if not matches:
        return f'<span style="color:#888;font-size:11px">{_html.escape(_CVE_NO_CORRELATION_CAVEAT)}</span>'

    confidence = _html.escape(str(d.get("cve_confidence") or ""))
    badge = (
        f'<span style="background:{_CVE_BADGE_COLOR};color:#000;padding:2px 7px;'
        f'border-radius:4px;font-size:11px;font-weight:600">'
        f"{len(matches)} CVEs ({confidence})</span>"
    )
    links = []
    for m in matches:
        cve_id = _html.escape(str(m.get("cve_id", "")))
        href = _html.escape(hw_cve.nvd_url(str(m.get("cve_id", ""))))
        links.append(f'<a href="{href}" target="_blank" rel="noopener">{cve_id}</a>')
    return f'{badge}<br/><span style="font-size:11px">{", ".join(links)}</span>'


def render_hardware_section(devices: list) -> str:
    """Generate HTML advisory table for hardware devices (Phase 128 D-10).

    Returns a collapsible <details> block with tier-colored badges.
    Tier 1 = red, Tier 2 = orange, Tier 3 = blue, N/A = gray.
    Advisory-only — clearly labeled; never in the score section.
    Returns "" when no devices are present.
    """
    if not devices:
        return ""

    TIER_ORDER = {"Tier 1": 0, "Tier 2": 1, "Tier 3": 2, "Tier N/A": 3}
    TIER_COLORS = {
        "Tier 1":   "#dc2626",  # red
        "Tier 2":   "#ea580c",  # orange
        "Tier 3":   "#3b82f6",  # blue
        "Tier N/A": "#6b7280",  # gray
    }
    CNSA_DEADLINE = {
        "Tier 1":   "Replace by 2030 (CNSA 2.0 deadline)",
        "Tier 2":   "Firmware upgrade target: 2030-2033",
        "Tier 3":   "Accept and monitor; re-evaluate by 2033",
        "Tier N/A": "EOL before PQC migration window",
    }

    sorted_devs = sorted(
        devices,
        key=lambda d: TIER_ORDER.get(d.get("remediation_tier", ""), 99),
    )

    rows_html = []
    for d in sorted_devs:
        tier = d.get("remediation_tier", "Tier N/A")
        color = TIER_COLORS.get(tier, "#6b7280")
        # tier is from our own lookup table — safe; scanner values below need escaping
        badge = (
            f'<span style="background:{color};color:#fff;padding:2px 7px;'
            f'border-radius:4px;font-size:11px;font-weight:600">{_html.escape(tier)}</span>'
        )
        host_port = f"{_html.escape(str(d.get('host', '')))}:{_html.escape(str(d.get('port', '')))}"
        eol = _html.escape(str(d.get("eol_date") or "—"))
        cnsa = _html.escape(CNSA_DEADLINE.get(tier, ""))
        snmp_label = _html.escape(_snmp_badge_label(d))
        modbus_label = _html.escape(_modbus_badge_label(d))
        bacnet_label = _html.escape(_bacnet_badge_label(d))
        bridge_raw = d.get("bridge_status")
        bridge_label = _bridge_badge_label(d)
        if bridge_label:
            bridge_color = _BRIDGE_COLORS.get(bridge_raw, "#6b7280")
            bridge_cell = (
                f'<span style="background:{bridge_color};color:#000;padding:2px 7px;'
                f'border-radius:4px;font-size:11px;font-weight:600">'
                f"{_html.escape(bridge_label)}</span>"
            )
        else:
            bridge_cell = "—"
        cve_cell = _cve_cell_html(d) or "—"
        rows_html.append(
            f"<tr>"
            f"<td>{badge}</td>"
            f"<td>{_html.escape(str(d.get('vendor', '')))}</td>"
            f"<td>{_html.escape(str(d.get('model') or 'Unknown'))}</td>"
            f"<td><code>{host_port}</code></td>"
            f"<td>{_html.escape(str(d.get('pqc_status', '')))}</td>"
            f"<td>{_html.escape(str(d.get('confidence', '')))}</td>"
            f"<td>{eol}</td>"
            f"<td>{cnsa}</td>"
            f"<td>{snmp_label}</td>"
            f"<td>{modbus_label}</td>"
            f"<td>{bacnet_label}</td>"
            f"<td>{bridge_cell}</td>"
            f"<td>{cve_cell}</td>"
            f"</tr>"
        )

    rows_joined = "\n".join(rows_html)
    caveat_html = ""
    if any(d.get("bridge_status") == "upstream_mitigated" for d in devices):
        caveat_html = f" {_html.escape(_BRIDGE_CAVEAT)}"
    otics_caveat_html = ""
    if any(
        d.get("modbus_probe_state") == "aborted_anomalous_response"
        or d.get("bacnet_probe_state") == "aborted_anomalous_response"
        for d in devices
    ):
        otics_caveat_html = (
            f'<p style="font-size:12px;color:#888;margin-bottom:8px">'
            f"{_html.escape(_OTICS_ABORT_CAVEAT)}</p>"
        )
    cve_staleness_caveat_html = ""
    if any(d.get("cve_snapshot_stale") for d in devices):
        staleness_text = _CVE_STALENESS_CAVEAT.format(
            last_verified=hw_cve.CVE_TABLE_META["last_verified"],
            threshold=hw_cve.STALENESS_THRESHOLD_DAYS,
        )
        cve_staleness_caveat_html = (
            f'<p style="font-size:12px;color:#888;margin-bottom:8px">'
            f"{_html.escape(staleness_text)}</p>"
        )
    cve_note_html = ""
    if any(d.get("cve_attempted") for d in devices):
        cve_note_html = (
            f'<p style="font-size:12px;color:#888;margin-bottom:8px">'
            f"{_html.escape(_CVE_SECTION_NOTE)}</p>"
        )
    # Phase 159 HWLC-13/D-159-N: always-visible banner sits OUTSIDE <details> so it
    # is visible without expanding the block — never collapsible, never behind a toggle.
    partial_scan_banner_html = ""
    if any(d.get("is_partial_scan") for d in devices):
        partial_scan_banner_html = (
            f'<p class="partial-scan-banner" style="font-size:12px;color:#888;margin-bottom:8px">'
            f"{_html.escape(PARTIAL_SCAN_BANNER)}</p>"
        )
    return (
        f"{partial_scan_banner_html}"
        '<details style="margin:24px 0">'
        '<summary style="cursor:pointer;font-weight:600;color:#3b9dff">'
        "Hardware PQC Advisory &#x25BC; &nbsp;"
        '<span style="font-weight:400;color:#888;font-size:12px">'
        "not included in readiness score</span></summary>"
        '<div style="margin-top:12px">'
        '<p style="font-size:12px;color:#888;margin-bottom:8px">'
        "Advisory only — hardware findings are not scored and do not affect the"
        " readiness score. Listed for CNSA 2.0 migration planning purposes only."
        f"{caveat_html}</p>"
        f"{otics_caveat_html}"
        f"{cve_note_html}"
        f"{cve_staleness_caveat_html}"
        '<table style="width:100%;border-collapse:collapse;font-size:13px">'
        "<thead><tr>"
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Tier</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Vendor</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Model</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Host:Port</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">PQC Status</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Confidence</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">EOL Date</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">CNSA 2.0 Timeline</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">SNMP</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Modbus</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">BACnet</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Bridge Status</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">CVEs</th>'
        "</tr></thead>"
        f"<tbody>{rows_joined}</tbody>"
        "</table></div></details>"
    )


# ---------------------------------------------------------------------------
# Phase 156 D-11/D-13/HWLC-10/HWLC-11: "Recent Lifecycle Changes" drift section
# ---------------------------------------------------------------------------

# D-13: exact copy string, verbatim across HTML/DOCX (156-UI-SPEC.md §Advisory Caption).
DRIFT_ADVISORY_CAPTION = (
    "Advisory — hardware lifecycle changes do not affect the readiness score."
)

# Phase 159 HWLC-13/D-159-M: locked banner copy, verbatim across HTML/DOCX/CLI.
# Always-visible — never rendered inside a <details>/collapsible element (D-159-N)
# — whenever a check-in-sourced device or drift row is displayed.
PARTIAL_SCAN_BANNER = "Partial re-probe — check-in scan; not a full assessment."

# 156-UI-SPEC.md §Event type differentiation — verbatim display labels.
_DRIFT_EVENT_TYPE_LABELS: Dict[str, str] = {
    "tier_crossing": "Tier crossing",
    "upstream_mitigated_change": "Bridge mitigation change",
    "cve_delta": "CVE correlation change",
    "eol_state_change": "EOL/EOS state change",
}

# 156-UI-SPEC.md §Color / §Copywriting Contract — verbatim direction display labels.
_DRIFT_DIRECTION_LABELS: Dict[str, str] = {
    "improved": "Improved",
    "worsened": "Worsened",
    "neutral": "Changed",
}

# Phase 161 HWLC-19: LOCKED caption copy, byte-identical to
# quirk/reports/technical.py's VENDOR_TREND_ADVISORY_CAPTION and to
# docx_renderer._VENDOR_TREND_ADVISORY_CAPTION. Per-renderer duplication is the
# established convention here (see the drift caption above) — a parity test
# fails loudly if the three surfaces ever drift apart.
VENDOR_TREND_ADVISORY_CAPTION = (
    "Advisory — vendor PQC status trends do not affect the readiness score."
)

# Phase 181 SURF-02: LOCKED caption copy for the "Remediation Burndown"
# section, byte-identical to quirk/reports/technical.py's
# BURNDOWN_ADVISORY_CAPTION and to docx_renderer._BURNDOWN_ADVISORY_CAPTION.
# Per-renderer duplication is the established Phase 161 convention (see
# VENDOR_TREND_ADVISORY_CAPTION above) — NOT a shared constant in
# content_model.py; a parity test fails loudly if the three surfaces drift.
BURNDOWN_ADVISORY_CAPTION = (
    "Advisory - remediation burndown does not affect the readiness score."
)

# Phase 191 Plan 05 (SPKI-02 / D-01): LOCKED caption copy for the "Key Reuse"
# section, byte-identical to quirk/reports/technical.py's
# KEY_REUSE_ADVISORY_CAPTION and to docx_renderer.KEY_REUSE_ADVISORY_CAPTION.
# Per-renderer duplication is the established Phase 161 convention (see
# VENDOR_TREND_ADVISORY_CAPTION above) — NOT a shared constant in
# content_model.py; a parity test fails loudly if the three surfaces drift.
KEY_REUSE_ADVISORY_CAPTION = "Advisory - key reuse does not affect the readiness score."

# Phase 181 SURF-02 / D-35/D-36: fixed bucket iteration order so per-deadline
# sections are stable and `unmapped` is always rendered last, never omitted.
_BURNDOWN_BUCKET_ORDER = ("key_establishment", "digital_signature", "unmapped")

# Phase 161 HWLC-19 — verbatim display labels for vendor-scoped trend events.
_VENDOR_TREND_EVENT_TYPE_LABELS: Dict[str, str] = {
    "pqc_status_change": "PQC status change",
}


def render_drift_section(events: list) -> str:
    """Generate the HTML "Recent Lifecycle Changes" section (Phase 156 D-11/D-13).

    Pure function, sibling to render_hardware_section — a separate data shape
    (drift events, not point-in-time device state) gets its own function per
    RESEARCH.md's Anti-Patterns (do NOT widen render_hardware_section).

    Returns "" for an empty list — no empty table, no orphan heading. Every
    interpolated value is html.escape()'d (T-156-04 — first phase to render
    old_value/new_value to HTML). Uses a dedicated non-severity palette
    (D-07 layer 2) — never the tier/PQC/confidence hex literals.
    """
    if not events:
        return ""

    rows_html = []
    for e in events:
        event_type = e.get("event_type", "")
        type_label = _html.escape(_DRIFT_EVENT_TYPE_LABELS.get(event_type, event_type))
        host_port = f"{_html.escape(str(e.get('host', '')))}:{_html.escape(str(e.get('port', '')))}"
        vendor = e.get("vendor") or ""
        model = e.get("model") or ""
        device_meta = f"{vendor} {model}".strip()
        device_cell = f"<code>{host_port}</code>"
        if device_meta:
            device_cell += f'<br><span style="color:#888;font-size:11px">{_html.escape(device_meta)}</span>'
        old_value = _html.escape(str(e.get("old_value") if e.get("old_value") is not None else "—"))
        new_value = _html.escape(str(e.get("new_value") if e.get("new_value") is not None else "—"))
        transition = f"{old_value} &#x2192; {new_value}"
        direction = e.get("direction", "neutral")
        direction_label = _html.escape(_DRIFT_DIRECTION_LABELS.get(direction, "Changed"))
        direction_color = {
            "improved": "#2f9e8f",   # hsl(172 45% 42%) — 156-UI-SPEC.md declared lifecycle palette
            "worsened": "#b352a8",   # hsl(300 45% 55%) — 156-UI-SPEC.md declared lifecycle palette
        }.get(direction, "#888")     # neutral — muted, text-only, no filled pill (D-07)
        detected = _html.escape(str(e.get("detected_at", "")))
        rows_html.append(
            "<tr>"
            f"<td>{device_cell}</td>"
            f"<td>{type_label}</td>"
            f"<td>{transition}</td>"
            f'<td><span style="color:{direction_color}">{direction_label}</span></td>'
            f"<td>{detected}</td>"
            "</tr>"
        )
    rows_joined = "\n".join(rows_html)

    # Phase 159 HWLC-13/D-159-P: independently gated on this section's own list, so
    # a report showing only drift events (no devices) still shows the banner.
    partial_scan_banner_html = ""
    if any(e.get("is_partial_scan") for e in events):
        partial_scan_banner_html = (
            f'<p class="partial-scan-banner" style="font-size:12px;color:#888;margin-bottom:8px">'
            f"{_html.escape(PARTIAL_SCAN_BANNER)}</p>"
        )

    return (
        '<section class="drift-section" style="margin:24px 0;'
        'border-left:4px solid #2b8a86;padding-left:12px">'
        '<h2 style="font-size:16px;font-weight:600;margin-bottom:4px">Recent Lifecycle Changes</h2>'
        f'<p class="drift-advisory-caption" style="font-size:12px;color:#888;margin-bottom:8px">'
        f"{_html.escape(DRIFT_ADVISORY_CAPTION)}</p>"
        f"{partial_scan_banner_html}"
        '<table style="width:100%;border-collapse:collapse;font-size:13px">'
        "<thead><tr>"
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Device</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Change</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Transition</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Direction</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Detected</th>'
        "</tr></thead>"
        f"<tbody>{rows_joined}</tbody>"
        "</table></section>"
    )


def render_eol_forecast_section(forecast: dict) -> str:
    """Generate the HTML "EOL/Tier Forecast" subsection (Phase 157 HWLC-18 / D-05).

    Pure function, sibling to render_drift_section — sits under "Recent Lifecycle
    Changes" as its own subsection, never merged into the drift changes list
    (D-05: own subheading, one level below render_drift_section's <h2>).

    Returns "" when *forecast* is falsy or carries no populated buckets — no
    orphan heading, matching render_drift_section's empty-guard convention.
    Every interpolated string (bucket sentences, catalog_last_verified) is
    escaped with html.escape() before interpolation (T-157-09).
    """
    if not forecast or not forecast.get("buckets"):
        return ""

    sentences_html = "".join(
        f"<p>{_html.escape(bucket.get('sentence', ''))}</p>"
        for bucket in forecast["buckets"]
    )

    stale_html = ""
    if forecast.get("catalog_stale"):
        last_verified = _html.escape(str(forecast.get("catalog_last_verified", "")))
        stale_html = (
            '<p class="eol-forecast-stale-caveat" style="font-size:12px;color:#b352a8;margin-top:8px">'
            f"The curated EOL/EOS catalog (last verified {last_verified}) has not been "
            "re-verified within its review cadence; treat this projection accordingly."
            "</p>"
        )

    return (
        '<section class="eol-forecast-section" style="margin:24px 0;'
        'border-left:4px solid #2b8a86;padding-left:12px">'
        '<h3 style="font-size:14px;font-weight:600;margin-bottom:4px">EOL/Tier Forecast</h3>'
        '<p class="eol-forecast-advisory-caption" style="font-size:12px;color:#888;margin-bottom:8px">'
        "Advisory only — not included in the readiness score."
        "</p>"
        f"{sentences_html}"
        f"{stale_html}"
        "</section>"
    )


def render_vendor_trend_section(events: list) -> str:
    """Generate the HTML "Vendor PQC Status Trends" section (Phase 161 HWLC-19).

    Pure function, and a sibling of render_drift_section — NOT a widening of it.
    The data shape differs: vendor-trend rows are catalog-level and carry only
    vendor / event_type / old_value / new_value / detected_at / confirmed_at,
    with no host, port, direction or severity. The table therefore has four
    columns (Vendor | Change | Transition | Detected) rather than the drift
    table's five — the Device and Direction columns are omitted outright, not
    rendered blank.

    Returns "" for an empty or None list — no empty table, no orphan heading.
    Every interpolated value is html.escape()'d without exception (T-161-18);
    the template interpolates the result with ``| safe``, so escaping here is
    the whole of the defence.

    Advisory-only: this section has zero score coupling and uses the
    established non-severity advisory teal, never a tier/PQC/confidence hex.
    """
    if not events:
        return ""

    rows_html = []
    for e in events:
        event_type = e.get("event_type", "")
        type_label = _html.escape(
            _VENDOR_TREND_EVENT_TYPE_LABELS.get(event_type, event_type)
        )
        vendor = _html.escape(str(e.get("vendor") or ""))
        old_value = _html.escape(
            str(e.get("old_value") if e.get("old_value") is not None else "—")
        )
        new_value = _html.escape(
            str(e.get("new_value") if e.get("new_value") is not None else "—")
        )
        transition = f"{old_value} &#x2192; {new_value}"
        detected = _html.escape(str(e.get("detected_at", "")))
        rows_html.append(
            "<tr>"
            f"<td>{vendor}</td>"
            f"<td>{type_label}</td>"
            f"<td>{transition}</td>"
            f"<td>{detected}</td>"
            "</tr>"
        )
    rows_joined = "\n".join(rows_html)

    return (
        '<section class="vendor-trend-section" style="margin:24px 0;'
        'border-left:4px solid #2b8a86;padding-left:12px">'
        '<h2 style="font-size:16px;font-weight:600;margin-bottom:4px">'
        "Vendor PQC Status Trends</h2>"
        f'<p class="vendor-trend-advisory-caption" style="font-size:12px;color:#888;margin-bottom:8px">'
        f"{_html.escape(VENDOR_TREND_ADVISORY_CAPTION)}</p>"
        '<table style="width:100%;border-collapse:collapse;font-size:13px">'
        "<thead><tr>"
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Vendor</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Change</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Transition</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Detected</th>'
        "</tr></thead>"
        f"<tbody>{rows_joined}</tbody>"
        "</table></section>"
    )


def render_burndown_section(burndown: dict, closure_refusal: dict | None) -> str:
    """Generate the HTML "Remediation Burndown" section (Phase 181 SURF-02).

    Pure function, sibling to render_vendor_trend_section. The refusal branch
    is emitted FIRST — a refused scan is never presented as a measured (e.g.
    "zero closed") result, and emits no ``<table>`` at all. Otherwise, iterates
    the three fixed buckets (key_establishment, digital_signature, unmapped)
    in order — `unmapped` is always rendered, labelled "No deadline mapped"
    rather than omitted or blanked.

    D-36 / CLOSE-03: buckets overlap by design and are never summed — no
    total row, no percentage anywhere in this function.

    Every interpolated value is html.escape()'d without exception, matching
    render_vendor_trend_section's contract.
    """
    if not burndown and not closure_refusal:
        return ""

    caption_html = (
        f'<p class="burndown-advisory-caption" style="font-size:12px;color:#888;'
        f'margin-bottom:8px">{_html.escape(BURNDOWN_ADVISORY_CAPTION)}</p>'
    )

    if closure_refusal:
        statement = _html.escape(str(closure_refusal.get("statement", "")))
        return (
            '<section class="burndown-section" style="margin:24px 0;'
            'border-left:4px solid #2b8a86;padding-left:12px">'
            '<h2 style="font-size:16px;font-weight:600;margin-bottom:4px">'
            "Remediation Burndown</h2>"
            f"{caption_html}"
            f'<p class="burndown-refusal-statement">{statement}</p>'
            "</section>"
        )

    rows_html = []
    for bucket_key in _BURNDOWN_BUCKET_ORDER:
        bucket = burndown.get(bucket_key)
        if bucket is None:
            continue
        deadline = _html.escape(str(bucket.get("date") or "No deadline mapped"))
        standard = _html.escape(str(bucket.get("standard") or "—"))
        rows_html.append(
            "<tr>"
            f"<td>{_html.escape(bucket_key)}</td>"
            f"<td>{deadline}</td>"
            f"<td>{standard}</td>"
            f"<td>{bucket.get('open', 0)}</td>"
            f"<td>{bucket.get('closed', 0)}</td>"
            f"<td>{bucket.get('not_observed', 0)}</td>"
            f"<td>{bucket.get('resurfaced', 0)}</td>"
            "</tr>"
        )
    rows_joined = "\n".join(rows_html)

    return (
        '<section class="burndown-section" style="margin:24px 0;'
        'border-left:4px solid #2b8a86;padding-left:12px">'
        '<h2 style="font-size:16px;font-weight:600;margin-bottom:4px">'
        "Remediation Burndown</h2>"
        f"{caption_html}"
        '<table style="border-collapse:collapse;font-size:13px">'
        "<thead><tr>"
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Bucket</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Deadline</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Standard</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Open</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Closed</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Not Observed</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Resurfaced</th>'
        "</tr></thead>"
        f"<tbody>{rows_joined}</tbody>"
        "</table></section>"
    )


def render_key_reuse_section(key_reuse: dict) -> str:
    """Generate the HTML "Key Reuse" section (Phase 191 Plan 05 / SPKI-02 / D-01).

    Pure function, sibling to render_burndown_section. Returns "" ONLY when
    *key_reuse* is falsy overall (loader failure / no data at all) — when it
    is present but `clusters` is empty, the full section still renders with
    an explicit zero-reuse `<p>` (D-06 forbids silent omission). The coverage
    line renders in both the zero- and non-zero-cluster cases (D-12).

    Each cluster is framed as remediation leverage ("Re-keying this
    certificate remediates N endpoints." — D-05). Incoming cluster order is
    preserved (already member-count descending per
    `compute_key_reuse_clusters` — D-04); never re-sorted here.

    Every interpolated value is html.escape()'d without exception (T-191-13,
    matching render_burndown_section's contract).
    """
    if not key_reuse:
        return ""

    clusters = key_reuse.get("clusters") or []
    fingerprinted = key_reuse.get("fingerprinted", 0)
    total = key_reuse.get("total", 0)

    caption_html = (
        f'<p class="key-reuse-advisory-caption" style="font-size:12px;color:#888;'
        f'margin-bottom:8px">{_html.escape(KEY_REUSE_ADVISORY_CAPTION)}</p>'
    )
    coverage_html = (
        f'<p class="key-reuse-coverage">{_html.escape(str(fingerprinted))} of '
        f"{_html.escape(str(total))} TLS endpoints have SPKI fingerprints.</p>"
    )

    if not clusters:
        return (
            '<section class="key-reuse-section" style="margin:24px 0;'
            'border-left:4px solid #2b8a86;padding-left:12px">'
            '<h2 style="font-size:16px;font-weight:600;margin-bottom:4px">Key Reuse</h2>'
            f"{caption_html}"
            f"{coverage_html}"
            f'<p class="key-reuse-none">No shared keys detected across '
            f"{_html.escape(str(fingerprinted))} fingerprinted endpoints.</p>"
            "</section>"
        )

    clusters_html_parts = []
    for cluster in clusters:
        member_count = cluster.get("member_count", len(cluster.get("members") or []))
        fingerprint = cluster.get("fingerprint") or ""
        fingerprint_display = fingerprint[:16] + "..." if len(fingerprint) > 16 else fingerprint
        members_html = "".join(
            f"<li><code>{_html.escape(str(m.get('host', '')))}:"
            f"{_html.escape(str(m.get('port', '')))}</code></li>"
            for m in (cluster.get("members") or [])
        )
        clusters_html_parts.append(
            '<div class="key-reuse-cluster" style="margin:12px 0">'
            f"<p><strong>Re-keying this certificate remediates "
            f"{_html.escape(str(member_count))} endpoints.</strong></p>"
            "<ul>"
            f"<li><strong>Cert subject:</strong> {_html.escape(str(cluster.get('cert_subject', '')))}</li>"
            f"<li><strong>Public key:</strong> {_html.escape(str(cluster.get('cert_pubkey_alg', '')))} "
            f"{_html.escape(str(cluster.get('cert_pubkey_size', '')))}</li>"
            f"<li><strong>SPKI fingerprint:</strong> {_html.escape(fingerprint_display)}</li>"
            "</ul>"
            f"<ul>{members_html}</ul>"
            "</div>"
        )
    clusters_joined = "".join(clusters_html_parts)

    return (
        '<section class="key-reuse-section" style="margin:24px 0;'
        'border-left:4px solid #2b8a86;padding-left:12px">'
        '<h2 style="font-size:16px;font-weight:600;margin-bottom:4px">Key Reuse</h2>'
        f"{caption_html}"
        f"{coverage_html}"
        f"{clusters_joined}"
        "</section>"
    )


def render_scan_coverage_section(coverage: dict | None) -> str:
    """Generate the HTML "Scan Coverage" section (Phase 192 Plan 08 / OBS-02, D-13/D-15).

    D-15 / INVERTED CONTRACT vs. render_key_reuse_section: that sibling function
    returns `""` when its payload is falsy (loader failure / no data at all) — this
    one must ALWAYS return a non-empty section, even for `{}` or `None`. That
    difference is the entire point of D-15 (an unrecorded scan states its own
    absence rather than silently vanishing from the report). Do NOT "fix" this
    function to match render_key_reuse_section's truthiness contract.

    Every interpolated value (`label`, `reason`, `detail`) is passed through
    `html.escape()` without exception, matching render_key_reuse_section's and
    render_burndown_section's contract (T-192-27).
    """
    from quirk.reports.coverage import COVERAGE_NOT_RECORDED_NOTICE

    _coverage = coverage or {}

    if not _coverage.get("recorded"):
        return (
            '<section class="scan-coverage-section" style="margin:24px 0;'
            'border-left:4px solid #2b8a86;padding-left:12px">'
            '<h2 style="font-size:16px;font-weight:600;margin-bottom:4px">Scan Coverage</h2>'
            f'<p class="scan-coverage-not-recorded">{_html.escape(COVERAGE_NOT_RECORDED_NOTICE)}</p>'
            "</section>"
        )

    ran = _coverage.get("ran", 0)
    skipped = _coverage.get("skipped", 0)
    phases = _coverage.get("phases") or []

    summary_html = (
        f'<p class="scan-coverage-summary">'
        f"<strong>{_html.escape(str(ran))} ran / {_html.escape(str(skipped))} skipped</strong></p>"
    )

    rows_html_parts = []
    for entry in phases:
        label = entry.get("label") or entry.get("phase_name", "")
        status = entry.get("status", "")
        if status == "ran":
            # Review WR-01: duration_sec key is always present (None when the
            # DB column is NULL) — guard like technical.py/executive.py do so
            # a NULL duration never renders the literal "Nones".
            _dur = entry.get("duration_sec")
            detail_text = f"{_dur}s" if _dur is not None else ""
        else:
            reason = entry.get("reason") or ""
            detail = entry.get("detail")
            detail_text = f"{reason} ({detail})" if detail else reason
        rows_html_parts.append(
            "<tr>"
            f"<td>{_html.escape(str(label))}</td>"
            f"<td>{_html.escape(str(status))}</td>"
            f"<td>{_html.escape(str(detail_text))}</td>"
            "</tr>"
        )
    rows_joined = "".join(rows_html_parts)

    table_html = (
        '<table style="width:100%;border-collapse:collapse;margin-top:8px">'
        "<thead><tr>"
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Phase</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Status</th>'
        '<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #333">Detail</th>'
        "</tr></thead>"
        f"<tbody>{rows_joined}</tbody>"
        "</table>"
    )

    return (
        '<section class="scan-coverage-section" style="margin:24px 0;'
        'border-left:4px solid #2b8a86;padding-left:12px">'
        '<h2 style="font-size:16px;font-weight:600;margin-bottom:4px">Scan Coverage</h2>'
        f"{summary_html}"
        f"{table_html}"
        "</section>"
    )


def render_tls_capabilities_skip_note(coverage: dict | None) -> str:
    """D-14 (Phase 192 Plan 08 / OBS-02): TLS domain skip note, mirroring
    technical.py's renderer-side "## TLS Capabilities" skip note.

    OPPOSITE contract from render_scan_coverage_section: this returns `""`
    unless the `tls_scanning` phase is recorded `skipped`. The Endpoint
    Inventory table this note sits beside already renders unconditionally
    with an honest "No endpoints recorded" empty state (report.html.j2),
    so this note exists only to say WHY that table is TLS-empty when the
    reason is a skip, not to replace the table's own empty-state handling.
    """
    from quirk.reports.coverage import format_skip_note, get_phase_entry

    entry = get_phase_entry(coverage, "tls_scanning")
    if entry is None or entry.get("status") != "skipped":
        return ""

    return (
        '<section class="tls-capabilities-skip-note" style="margin:16px 0">'
        '<h2 style="font-size:16px;font-weight:600;margin-bottom:4px">TLS Capabilities</h2>'
        f"<p>{_html.escape(format_skip_note(entry))}</p>"
        "</section>"
    )


def render_html_report(
    path: str,
    cfg: Any,
    endpoints: List[Any],
    findings: List[Dict[str, Any]],
    score: Dict[str, Any],
    conf: Dict[str, Any],
    roadmap_items: List[Dict[str, Any]],
    *,
    exec_content: "ExecContent | None" = None,
    scan_completed_at: "datetime | None" = None,
) -> None:
    """Render a self-contained HTML report to *path*.

    All CSS is inlined. No CDN references. Works offline (D-08).

    D-03 / Phase 98: exec_content carries the shared narrative/risks/roadmap/subscores
    built by writer.py. When provided, the template context sources exec_content fields
    for narrative, top_risks, roadmap sections, and subscores (D-07 — extend, not rebuild).

    SCORE-03 / D-16b (Phase 184.3): scan_completed_at is the naive-UTC scan instant
    (CryptoEndpoint.scanned_at, derived once in writer.py), rendered by the template as
    a "Scan Completed" row distinct from the pre-existing generated_at ("Generated") rows.
    """
    # SCORE-03 / D-16b (Phase 184.3): local import avoids a circular import
    # (writer.py imports this module at load time).
    from quirk.reports.writer import format_scan_completed_at

    env = Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "j2"]),
    )
    env.filters["sanitize"] = sanitize_scanner_text
    template = env.get_template("report.html.j2")

    # WR-04: when exec_content is present, source the band/total from the guarded model
    # (score_band is what _check_congruence validated) instead of recomputing locally —
    # avoids a duplicated-source-of-truth hazard if the numeric/severity band thresholds drift.
    if exec_content is not None:
        total_score = exec_content.score_total
        band = exec_content.score_band
        # Phase 184.4 D-09: mirror the shared model's cap reason on the primary path.
        # 184.4 WR-01: sourced from exec_content, not the `score` dict — this is
        # the D-03 seam every other score-derived value on this path already uses
        # (total_score/band above), so the key cannot be dropped by a compat-dict
        # refactor without also breaking score_total/score_band.
        rating_cap_reason = exec_content.rating_cap_reason
        # Phase 188 SCORE-06 / 188-03: coverage-disclosure seam, sourced from the
        # shared model — never re-derived.
        # effective_domain_counts()/effective_score_divisor(): fall back to the
        # legacy full-six-domain shape for a pre-188 exec_content (score
        # computed, no domains_total/score_divisor) so the rollup and coverage
        # prose keep rendering unchanged for callers that never adopted SCORE-06.
        domains_assessed, domains_total = effective_domain_counts(
            total_score, exec_content.domains_assessed, exec_content.domains_total
        )
        score_divisor = effective_score_divisor(total_score, exec_content.score_divisor)
        coverage_disclosure = exec_content.coverage_disclosure
        scoring_version = exec_content.scoring_version
    else:
        # WR-06: canonical key is "score", not "total". 188 review CR-03: the
        # key is present with value None for a not-computed (zero-assessed)
        # SCORE-06 dict — dict.get's default never fires, so total_score can be
        # None here and every band derivation below must guard it (mirroring
        # executive.py's compat branch, which handles None correctly).
        total_score = score.get("score")
        # Phase 184.4 D-05: severity-aware band via the shared module — the old
        # severity-blind band helper is deleted outright. Cap using CRITICAL findings counted directly from
        # `findings`, NOT from the `sev_counts` display tally built below (which skips
        # `category == "coverage_gap"`, Phase 45 / D-07). This is inert today because
        # coverage_gap findings are emitted at INFO severity
        # (quirk/scanner/findings_evaluator.py:445) and can never be CRITICAL, but counting
        # independently here means a future severity change to coverage_gap cannot silently
        # reintroduce a split between the counting basis used here and the one
        # `_count_severities()` (content_model.py) uses inside assert_congruent() below.
        # 184.4 WR-02: the "can never be CRITICAL" clause above is no longer merely
        # documented — `tests/test_coverage_gap_severity_invariant.py` enforces it at
        # run time (behavioural INFO check on the emitter, a differential proving the
        # two CRITICAL counting bases agree, and a source scan that fails on any new,
        # undispositioned coverage_gap site). Do not weaken that gate to make a new
        # emitter pass; state the new emitter's severity in its ledger entry instead.
        if total_score is None:
            # 188 review CR-03: band_for_score(None) raises TypeError. A
            # not-computed score has no numeric band and no cap — surface the
            # producer's own rating (NOT_ASSESSED), matching executive.py's
            # compat branch and the template's `total_score is none` support.
            band = str(score.get("rating", "NOT_ASSESSED"))
            rating_cap_reason = None
        else:
            numeric_band = band_for_score(total_score)
            _critical_count = sum(
                1 for f in (findings or [])
                if str(f.get("severity", "INFO")).upper() == "CRITICAL"
            )
            band = cap_band_for_severity(numeric_band, _critical_count)
            rating_cap_reason = cap_reason(numeric_band, band, _critical_count, total_score)
        # Phase 188 SCORE-06 / 188-03: backward-compat path — `score` is the
        # writer.py compat dict (or a canonical score_raw dict from an external
        # caller); both carry these keys under the same names (RQ-1: not
        # re-derived here, just read through).
        domains_assessed, domains_total = effective_domain_counts(
            total_score, score.get("domains_assessed") or 0, score.get("domains_total") or 0
        )
        score_divisor = effective_score_divisor(total_score, score.get("score_divisor"))
        coverage_disclosure = score.get("coverage_disclosure") or ""
        scoring_version = score.get("scoring_version")

    # Severity counts
    sev_counts: Dict[str, int] = {}
    for f in (findings or []):
        # Phase 45 / D-07: coverage_gap findings are advisory-only and MUST NOT
        # inflate severity counts in the executive summary.
        if f.get("category") == "coverage_gap":
            continue
        s = str(f.get("severity", "INFO")).upper()
        sev_counts[s] = sev_counts.get(s, 0) + 1

    # Roadmap sections
    # Phase 77 D-13 / cbom-intel-reports/IN-07: C-7 verification — both branches
    # (timeframe match and phase match) are reachable; closes IN-07 as
    # audit-flip-only. See tests/test_html_renderer_roadmap_section.py for the
    # mutation evidence.
    def roadmap_section(tf: str) -> List[Dict]:
        return [r for r in (roadmap_items or []) if r.get("timeframe") == tf or r.get("phase") == tf]

    # Phase 81 / CMVP-06: build the Algorithm Inventory `algorithms` context.
    algorithms = build_algorithm_inventory(endpoints or [])

    # D-03 / D-07 / Phase 98: route subscores + narrative/risks/roadmap through exec_content
    # when available — single source of truth (D-03). Falls back to raw score dict (D-07 compat).
    if exec_content is not None:
        # D-07: source subscores from exec_content to guarantee structural identity with CLI
        subscores_ctx = exec_content.subscores or {}
        # EXEC-01: narrative lead + drivers for the narrative-block template section
        narrative_lead = exec_content.narrative_lead
        narrative_drivers = exec_content.narrative_drivers
        # EXEC-02: top_risks list for the risks-list template section
        top_risks = exec_content.top_risks
        # EXEC-03: roadmap items carry effort/impact; split by phase bucket
        roadmap_now_ctx = [r for r in exec_content.roadmap_items if r.phase == "NOW"]
        roadmap_next_ctx = [r for r in exec_content.roadmap_items if r.phase == "NEXT"]
        roadmap_later_ctx = [r for r in exec_content.roadmap_items if r.phase == "LATER"]
        # WR-03 / IN-01: consume the model's pre-computed numerator so the HTML rollup
        # matches the CLI markdown exactly (and survives a future 7th subscore).
        raw_sum = exec_content.raw_sum
    else:
        # Backward-compat path: no exec_content — source raw dicts from score/roadmap_items.
        # WR-05: keep this path fail-closed with the same D-06 guard the model path runs.
        # 188 review CR-03: explicit not-computed bypass, mirroring
        # build_exec_content's NOT_ASSESSED skip — a not-computed score has no
        # real band to contradict severity counts. (_check_congruence happens
        # to no-op on an unknown band, but relying on that would be implicit.)
        if total_score is not None:
            assert_congruent(band, findings or [])
        subscores_ctx = score.get("subscores", {})
        narrative_lead = None
        narrative_drivers = []
        top_risks = []
        roadmap_now_ctx = roadmap_section("NOW")
        roadmap_next_ctx = roadmap_section("NEXT")
        roadmap_later_ctx = roadmap_section("LATER")
        # WR-03: mirror the CLI's six-key sum on the compat path (no exec_content available).
        raw_sum = sum(int(v) for v in subscores_ctx.values()
                      if isinstance(v, (int, float)) and not isinstance(v, bool))

    # 188 review CR-01: pre-map unassessed (None) subscores to an em dash ONCE,
    # after raw_sum above has consumed the numeric values. The template's
    # `subscores.get(key, '—')` default never fires for a present-but-None key
    # (dict.get semantics), and Jinja renders None as the literal string "None"
    # (no `finalize` is configured on the Environment) — so the None→"—"
    # substitution must happen here, before the context is built.
    subscores_ctx = {k: ("—" if v is None else v) for k, v in (subscores_ctx or {}).items()}

    # Phase 100 / FMT-01 / D-01: extract logo_path and base64-encode for cover page
    logo_path = getattr(getattr(cfg, "assessment", None), "logo_path", None)
    logo_b64, logo_mime = _load_logo_b64(logo_path)

    # Phase 128 D-10: render hardware advisory section (advisory-only, not scored)
    _hw_devices_for_render = exec_content.hardware_devices if exec_content is not None else []
    # Phase 142 D-11: propagate the exec_content-level snapshot-stale flag onto
    # each device dict so render_hardware_section (a pure devices-list function)
    # can surface the staleness caveat without needing exec_content directly.
    if exec_content is not None and getattr(exec_content, "cve_snapshot_stale", False):
        for _hw_d in _hw_devices_for_render:
            _hw_d["cve_snapshot_stale"] = True
    hardware_section = render_hardware_section(_hw_devices_for_render)

    # Phase 156 D-11: render "Recent Lifecycle Changes" drift section (advisory-only)
    _drift_events_for_render = (
        exec_content.hardware_drift_events if exec_content is not None else []
    )
    drift_section = render_drift_section(_drift_events_for_render)

    # Phase 157 HWLC-18: render "EOL/Tier Forecast" subsection (advisory-only).
    # Sits alongside the drift wiring above so it renders independently of
    # whether this run produced any drift events (157-RESEARCH.md Open Q2).
    _eol_forecast_for_render = getattr(exec_content, "eol_forecast", {}) if exec_content is not None else {}
    eol_forecast_section = render_eol_forecast_section(_eol_forecast_for_render)

    # Phase 161 HWLC-19: vendor PQC trend section (advisory-only). getattr guard
    # so an older ExecContent instance without the field cannot raise.
    _vendor_trends_for_render = getattr(exec_content, "vendor_pqc_trends", []) if exec_content is not None else []
    vendor_trend_section = render_vendor_trend_section(_vendor_trends_for_render)

    # Phase 181 SURF-02: remediation burndown section (advisory-only).
    # getattr guard so an older ExecContent instance without the field
    # cannot raise.
    _burndown_for_render = getattr(exec_content, "burndown", {}) if exec_content is not None else {}
    _closure_refusal_for_render = (
        getattr(exec_content, "closure_refusal", {}) if exec_content is not None else {}
    )
    burndown_section = render_burndown_section(_burndown_for_render, _closure_refusal_for_render)

    # Phase 191 Plan 05 (SPKI-02 / D-01): key reuse section (advisory-only).
    # getattr guard so an older ExecContent instance without the field cannot raise.
    _key_reuse_for_render = getattr(exec_content, "key_reuse", {}) if exec_content is not None else {}
    key_reuse_section = render_key_reuse_section(_key_reuse_for_render)

    # Phase 192 Plan 08 (OBS-02 / D-13/D-15): scan coverage section (unconditional —
    # ALWAYS renders, unlike every other advisory section above). getattr guard so an
    # older ExecContent instance without the field cannot raise.
    _coverage_for_render = getattr(exec_content, "coverage", {}) if exec_content is not None else {}
    scan_coverage_section = render_scan_coverage_section(_coverage_for_render)

    # D-14 (Phase 192 Plan 08): TLS domain skip note (empty string unless
    # tls_scanning was recorded skipped) — see render_tls_capabilities_skip_note.
    tls_capabilities_skip_note = render_tls_capabilities_skip_note(_coverage_for_render)

    # Phase 146 D-08/D-09 (DISC-07): undetermined-host disclosure — same guard pattern as
    # hardware_section above; the template renders these, it never recomputes them.
    undetermined_hosts_count = (
        getattr(exec_content, "undetermined_hosts_count", 0) if exec_content is not None else 0
    )
    undetermined_hosts_breakdown = (
        getattr(exec_content, "undetermined_hosts_breakdown", {}) if exec_content is not None else {}
    )

    html = template.render(
        org_name=getattr(getattr(cfg, "assessment", None), "name", "Unknown"),
        report_owner=getattr(getattr(cfg, "assessment", None), "report_owner", ""),
        data_classification=getattr(getattr(cfg, "assessment", None), "data_classification", "CONFIDENTIAL"),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        # SCORE-03 / D-16b (Phase 184.3): shared helper renders the explicit
        # unknown marker rather than ever falling back to generated_at above.
        scan_completed_at=format_scan_completed_at(scan_completed_at),
        total_score=total_score,
        score_band=band,
        score_color=_score_color(band),
        rating_cap_reason=rating_cap_reason,  # Phase 184.4 D-09
        confidence=conf.get("confidence", 0),
        sev_counts=sev_counts,
        drivers=score.get("drivers", []),
        findings=findings or [],
        endpoints=endpoints or [],
        algorithms=algorithms,
        roadmap_now=roadmap_now_ctx,
        roadmap_next=roadmap_next_ctx,
        roadmap_later=roadmap_later_ctx,
        subscores=subscores_ctx,  # D-07 / SCORE-XPARENCY-01 — int values, no sanitize needed
        raw_sum=raw_sum,  # WR-03 / IN-01: shared rollup numerator (matches CLI markdown)
        # Phase 188 SCORE-06 / 188-03: coverage-disclosure seam — dynamic divisor
        # (never the retired fixed rollup literal), the assessed-domain count, and the
        # once-composed disclosure/not-computed sentences.
        domains_assessed=domains_assessed,
        domains_total=domains_total,
        score_divisor=score_divisor,
        coverage_disclosure=coverage_disclosure,
        scoring_version=scoring_version,
        not_computed_statement=NOT_COMPUTED_STATEMENT,
        severity_color=_severity_color,
        # D-03 / Phase 98: exec_content-derived template vars (None when exec_content absent)
        narrative_lead=narrative_lead,
        narrative_drivers=narrative_drivers,
        top_risks=top_risks,
        # Phase 128 D-10: hardware advisory section (pre-rendered HTML string)
        hardware_section=hardware_section,
        # Phase 156 D-11: drift section (pre-rendered HTML string)
        drift_section=drift_section,
        # Phase 157 HWLC-18: EOL/Tier forecast subsection (pre-rendered HTML string)
        eol_forecast_section=eol_forecast_section,
        # Phase 161 HWLC-19: vendor PQC trend section (pre-rendered HTML string)
        vendor_trend_section=vendor_trend_section,
        # Phase 181 SURF-02: remediation burndown section (pre-rendered HTML string)
        burndown_section=burndown_section,
        # Phase 191 Plan 05 (SPKI-02 / D-01): key reuse section (pre-rendered HTML string)
        key_reuse_section=key_reuse_section,
        # Phase 192 Plan 08 (OBS-02 / D-13/D-15): scan coverage section (pre-rendered
        # HTML string; always non-empty, unlike the sibling sections above)
        scan_coverage_section=scan_coverage_section,
        # D-14 (Phase 192 Plan 08): TLS domain skip note (pre-rendered HTML string,
        # "" when TLS was not skipped)
        tls_capabilities_skip_note=tls_capabilities_skip_note,
        # Phase 146 D-08/D-09 (DISC-07): undetermined-host disclosure
        undetermined_hosts_count=undetermined_hosts_count,
        undetermined_hosts_breakdown=undetermined_hosts_breakdown,
        # Phase 100 / FMT-01 / D-01: logo embed for cover page
        logo_b64=logo_b64,
        logo_mime=logo_mime,
    )
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def _inject_pdf_metadata(pdf_path: str) -> None:
    """Post-process a rendered PDF to inject /Title and /Author metadata.

    Phase 78 / HARDEN-04: Chromium's headless print-to-PDF embeds <title> as
    /Title but ignores <meta name="author">. We open the freshly rendered PDF
    with pypdf, copy pages into a new writer, set both metadata fields to the
    locked module-level constants, and overwrite the file. This preserves the
    locked Playwright context (JS disabled, offline, CSP enforced) and adds
    Author as a deterministic post-render step.

    pypdf is imported lazily so that `pip install quirk-scanner` (without the
    `[dashboard]` extra) does not break the always-imported report module
    chain — this function is only ever called from render_pdf_report, which
    short-circuits on missing Playwright.
    """
    import pypdf
    reader = pypdf.PdfReader(pdf_path)
    writer = pypdf.PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({"/Title": PDF_TITLE, "/Author": PDF_AUTHOR})
    with open(pdf_path, "wb") as f:
        writer.write(f)


def render_pdf_report(html_path: str, pdf_path: str) -> bool:
    """Render html_path to pdf_path using Playwright headless Chromium.

    Returns True on success, False if Playwright is unavailable (graceful degradation, D-11).
    """
    try:
        from playwright.sync_api import sync_playwright
        from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
    except ImportError:
        return False
    browser = None
    context = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            # Phase 78 / HARDEN-04: explicit deny on JS, network, and CSP bypass.
            context = browser.new_context(
                java_script_enabled=False,
                offline=True,
                bypass_csp=False,
            )
            page = context.new_page()
            page.goto(f"file://{os.path.abspath(html_path)}")
            page.pdf(
                path=pdf_path,
                format="A4",
                margin={"top": "15mm", "bottom": "15mm", "left": "12mm", "right": "12mm"},
                print_background=True,
                display_header_footer=False,
            )
        # Phase 78 / HARDEN-04: post-render metadata injection. Chromium's
        # print-to-PDF honors <title> but not <meta name="author">, so we
        # inject /Author (and re-affirm /Title) via pypdf.
        _inject_pdf_metadata(pdf_path)
        return True
    except (PlaywrightError, PlaywrightTimeoutError, OSError, RuntimeError) as e:
        print(
            f"PDF generation failed: {safe_str(e)}; scan complete, HTML report at {html_path}",
            file=sys.stderr,
        )
        return False
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                pass
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
