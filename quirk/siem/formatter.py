"""quirk/siem/formatter.py — CEF:0 transformation layer (Phase 103 SIEM-02).

Pure string transformation — no I/O, no network, fully unit-testable.

Exports:
    to_cef_finding(finding: dict) -> dict
        ISEC-03 explicit whitelist: extracts only named fields from a raw
        finding dict.  Never uses an exclusion-list comprehension — this is
        the same discipline as to_integration_payload() in notify/payload.py.

    build_cef_event(finding: dict, version: str) -> str
        Returns a complete CEF:0 line (8 pipe-delimited fields) ready for
        transport.  Does NOT prepend the syslog <PRI> byte — that is the
        transport layer's responsibility.

    _CEF_SEVERITY: dict[str, int]
        Maps CRITICAL/HIGH/MEDIUM/LOW to the CEF 0-10 severity scale.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Severity mapping (CONTEXT.md D-01)
# ---------------------------------------------------------------------------

_CEF_SEVERITY: dict[str, int] = {
    "CRITICAL": 10,
    "HIGH": 8,
    "MEDIUM": 5,
    "LOW": 3,
}

_DEFAULT_SEVERITY = 3  # Default when severity is absent or unrecognised

# ---------------------------------------------------------------------------
# CEF escaping — two distinct functions, one per context
# ---------------------------------------------------------------------------

def _cef_escape_header(value: str) -> str:
    """Escape a CEF header field value.

    CEF header rules (ArcSight CEF Implementation Standard):
      - Backslash (\\) -> \\\\   MUST be escaped FIRST (avoids double-escape)
      - Pipe (|)       -> \\|
      - Newlines       -> stripped (no valid CEF header value contains a newline;
                          a bare \\n in a header splits the syslog line into two
                          physical lines — log injection / CWE-117)
      - Equals (=)     is NOT escaped in header fields (only in extension values)
    """
    # Backslash MUST be replaced first — see RESEARCH.md Pitfall 1
    # NOTE: '=' is intentionally NOT escaped in header fields per CEF spec
    # (section 5, ArcSight CEF Implementation Standard). Only extension values escape '='.
    return (
        value
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r\n", "")
        .replace("\r", "")
        .replace("\n", "")
    )


def _cef_escape_extension(value: str) -> str:
    """Escape a CEF extension key-value pair's value.

    CEF extension rules (ArcSight CEF Implementation Standard):
      - Backslash (\\)   -> \\\\   MUST be escaped FIRST
      - Equals (=)       -> \\=
      - CRLF (\\r\\n)   -> literal \\n   (CRLF checked before CR to avoid double-replace)
      - CR (\\r)         -> literal \\n
      - LF (\\n)         -> literal \\n
    """
    # Backslash MUST be replaced first — see RESEARCH.md Pitfall 1
    return (
        value
        .replace("\\", "\\\\")
        .replace("=", "\\=")
        .replace("\r\n", "\\n")
        .replace("\r", "\\n")
        .replace("\n", "\\n")
    )


# ---------------------------------------------------------------------------
# Slug helper — for signature fallback when category/id absent
# ---------------------------------------------------------------------------

def _slugify(title: str) -> str:
    """Convert a title string to a URL-safe slug for use as a CEF signature ID.

    Rules:
      - Lowercase the input
      - Replace runs of non-alphanumeric characters with a single hyphen
      - Strip leading/trailing hyphens
      - If the result is empty, return "unknown"
    """
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug if slug else "unknown"


# ---------------------------------------------------------------------------
# ISEC-03 per-finding whitelist
# ---------------------------------------------------------------------------

def to_cef_finding(finding: dict) -> dict:
    """Extract only whitelisted fields from a raw finding dict for CEF emission.

    ISEC-03 enforcement: this function uses EXPLICIT named .get() extraction
    only — it never uses a dict comprehension or exclusion-list approach.
    This ensures that cert_pem, cert_sans, private_key, compliance, and any
    future sensitive fields added to the finding dict can NEVER leak into a
    CEF event.

    Fields included (CONTEXT.md):
        severity     — mapped to CEF integer 0-10
        host         — destination host (SIEM dhost field)
        port         — destination port (SIEM dpt field)
        title        — human-readable finding name (CEF name field)
        category     — CEF signature; falls back to slugified title
        description  — evidence summary, truncated to 256 chars
        recommendation — remediation advice, truncated to 256 chars

    Fields explicitly excluded:
        compliance   — internal control mapping; not a standard CEF field
        cert_pem     — raw certificate PEM (not in findings JSON, defensive)
        cert_sans    — Subject Alternative Names (not in findings JSON, defensive)
        cert_subject — certificate subject DN (not in findings JSON, defensive)
        cert_issuer  — certificate issuer DN (not in findings JSON, defensive)
        private_key  — private key material (not in findings JSON, defensive)
        key_material — raw key bytes (not in findings JSON, defensive)
        <all other keys> — never passed through
    """
    title = str(finding.get("title") or "Finding")
    raw_category = finding.get("category") or finding.get("id") or _slugify(title)
    raw_desc = str(finding.get("description") or "")
    raw_rec = str(finding.get("recommendation") or "")

    # Coerce port to a bounded int so str(port) in the extension can NEVER carry
    # CEF metacharacters (=, space, newline) — a non-numeric/out-of-range port
    # is dropped to "" rather than risking dpt= extension injection (CR-01 iter-2).
    try:
        _port_int = int(finding.get("port"))
        safe_port = _port_int if 0 < _port_int <= 65535 else ""
    except (TypeError, ValueError):
        safe_port = ""

    return {
        "severity": str(finding.get("severity") or "LOW").upper(),
        "host": str(finding.get("host") or ""),
        "port": safe_port,
        "title": title,
        "category": str(raw_category),
        "description": raw_desc[:256],
        "recommendation": raw_rec[:256],
    }


# ---------------------------------------------------------------------------
# CEF:0 event builder
# ---------------------------------------------------------------------------

def build_cef_event(finding: dict, version: str) -> str:
    """Build a complete CEF:0 event line from a raw finding dict.

    Calls to_cef_finding() first to apply the ISEC-03 whitelist, then
    formats the 8-pipe-delimited CEF:0 header followed by space-separated
    key=value extension pairs.

    Does NOT prepend a syslog <PRI> prefix — that is transport's responsibility
    (see quirk/siem/transport.py).

    Args:
        finding: Raw finding dict (e.g. from findings-*.json output)
        version: Scanner version string (e.g. "1.0.0")

    Returns:
        A complete CEF:0 line:
        ``CEF:0|QUIRK|scanner|<version>|<signature>|<name>|<severity>|<extension>``
    """
    safe = to_cef_finding(finding)

    # --- Header field values (escape backslash and pipe) ---
    escaped_version = _cef_escape_header(version)
    signature = _cef_escape_header(safe["category"])
    name = _cef_escape_header(safe["title"])
    cef_sev = _CEF_SEVERITY.get(safe["severity"], _DEFAULT_SEVERITY)

    # --- Extension field values (escape backslash, equals, and newlines) ---
    dhost = _cef_escape_extension(safe["host"])
    dpt = str(safe["port"])
    cs1 = _cef_escape_extension(safe["category"])
    cs2 = _cef_escape_extension(safe["description"])
    msg_raw = safe["recommendation"] if safe["recommendation"] else safe["description"]
    msg = _cef_escape_extension(msg_raw)

    # --- Assemble the 8-field CEF:0 line ---
    # Fields: CEF:0 | Vendor | Product | Version | SignatureID | Name | Severity | Extension
    header = f"CEF:0|QUIRK|scanner|{escaped_version}|{signature}|{name}|{cef_sev}"
    ext = (
        f"dhost={dhost} dpt={dpt} "
        f"cs1={cs1} cs1Label=Category "
        f"cs2={cs2} cs2Label=EvidenceSummary "
        f"msg={msg}"
    )
    return f"{header}|{ext}"
