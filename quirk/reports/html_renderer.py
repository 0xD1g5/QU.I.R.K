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
from quirk.reports.content_model import ExecContent, assert_congruent  # D-03 / Phase 98: shared content model
from quirk.scanner import hw_cve  # Phase 142 CVE-01: NVD link helper


# Phase 78 / HARDEN-04: PDF metadata constants. Title flows from HTML <title>;
# Author is injected post-render via pypdf because Chromium's print-to-PDF does
# not honor <meta name="author">.
PDF_TITLE = "QU.I.R.K. Cryptographic Readiness Report"
PDF_AUTHOR = "QU.I.R.K. Scanner"


def _score_band(total: int) -> str:
    if total >= 85:
        return "EXCELLENT"
    if total >= 70:
        return "GOOD"
    if total >= 55:
        return "MODERATE"
    if total >= 35:
        return "FAIR"
    return "POOR"


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
    return (
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

    return (
        '<section class="drift-section" style="margin:24px 0;'
        'border-left:4px solid #2b8a86;padding-left:12px">'
        '<h2 style="font-size:16px;font-weight:600;margin-bottom:4px">Recent Lifecycle Changes</h2>'
        f'<p class="drift-advisory-caption" style="font-size:12px;color:#888;margin-bottom:8px">'
        f"{_html.escape(DRIFT_ADVISORY_CAPTION)}</p>"
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
) -> None:
    """Render a self-contained HTML report to *path*.

    All CSS is inlined. No CDN references. Works offline (D-08).

    D-03 / Phase 98: exec_content carries the shared narrative/risks/roadmap/subscores
    built by writer.py. When provided, the template context sources exec_content fields
    for narrative, top_risks, roadmap sections, and subscores (D-07 — extend, not rebuild).
    """
    env = Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "j2"]),
    )
    env.filters["sanitize"] = sanitize_scanner_text
    template = env.get_template("report.html.j2")

    # WR-04: when exec_content is present, source the band/total from the guarded model
    # (score_band is what _check_congruence validated) instead of recomputing locally —
    # avoids a duplicated-source-of-truth hazard if _rating()/_score_band() thresholds drift.
    if exec_content is not None:
        total_score = exec_content.score_total
        band = exec_content.score_band
    else:
        total_score = score.get("score", 0)  # WR-06: canonical key is "score", not "total"
        band = _score_band(total_score)

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
        total_score=total_score,
        score_band=band,
        score_color=_score_color(band),
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
