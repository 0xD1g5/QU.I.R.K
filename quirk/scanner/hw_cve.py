"""Phase 142 (CVE-01/02/03): curated firmware CVE correlation.

Third instance of the curated-catalog + staleness-gate + status-report triad
already established by ``quirk/compliance/__init__.py`` (Phase 49) and
``quirk/qramm/model_meta.py`` (Phase 51). This module is advisory-only:
CVE correlation output is never read by ``quirk/intelligence/scoring.py``
(``SCORE_WEIGHTS``) or ``quirk/scanner/hardware_tier.py`` (``assign_tier()``)
(CVE-04, guarded by tests/test_cve_score_guard.py).

Zero network calls, stdlib only (``re`` + ``datetime``) — CVE-02.

``correlate_device()`` does NOT gate on ``vendor == "Unknown"`` (D-03); that
skip decision is the CALL SITE's responsibility (RESEARCH.md Pitfall 4) —
callers must check ``vendor != "Unknown"`` before invoking this function.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Staleness gate (D-09) — mirrors quirk/qramm/model_meta.py::is_qramm_model_stale
# ---------------------------------------------------------------------------

# D-09: shorter than QRAMM's 90-day cadence — CVE data churns faster.
# See CLAUDE.md "Staleness Review Cadence" for the re-verification bump procedure.
STALENESS_THRESHOLD_DAYS: int = 30

CVE_TABLE_META = {
    "last_verified": "2026-08-02",
    "source": "NVD",
    "source_url": "https://nvd.nist.gov",
}


def is_cve_table_stale(today: Optional[datetime.date] = None) -> bool:
    """Returns True when the CVE snapshot has not been re-verified within
    ``STALENESS_THRESHOLD_DAYS`` (30) days of ``today`` (default: ``today()``).

    Boundary: ``age > STALENESS_THRESHOLD_DAYS`` (strict greater-than), so
    exactly 30 days is NOT stale (D-09).
    """
    reference = today or datetime.date.today()
    last_verified = datetime.date.fromisoformat(CVE_TABLE_META["last_verified"])
    age = (reference - last_verified).days
    return age > STALENESS_THRESHOLD_DAYS


def nvd_url(cve_id: str) -> str:
    """Single source of truth for the NVD detail-page URL format (D-15)."""
    return f"https://nvd.nist.gov/vuln/detail/{cve_id}"


# ---------------------------------------------------------------------------
# Curated CVE table (D-05/D-06) — per-entry builder mirrors compliance's _pci()
# ---------------------------------------------------------------------------


def _cve(
    cve_id: str,
    severity: str,
    description: str,
    affected_before: Optional[str],
    published: str,
) -> dict:
    """Per-entry CVE builder (D-06). ``affected_before`` is exclusive
    ("firmware < affected_before" is the affected range) — ``None`` means a
    vendor+model-only match (D-08 'medium' confidence, no version distinction
    is available/needed for this entry)."""
    return {
        "cve_id": cve_id,
        "severity": severity,  # CVSS v3.x baseSeverity: CRITICAL|HIGH|MEDIUM|LOW
        "description": description,
        "affected_before": affected_before,
        "published": published,
        "last_verified": CVE_TABLE_META["last_verified"],
        "source_url": nvd_url(cve_id),
    }


# Source: NVD (nvd.nist.gov) — each entry independently verified during
# 142-RESEARCH.md (2026-08-02). See that file's Sources section for the
# per-CVE fetch citations.
CVE_TABLE: dict = {
    ("Schneider Electric", "M221"): [
        _cve(
            "CVE-2018-7789", "HIGH",
            "Improper exception handling allows unauthorized remote reboot of "
            "Modicon M221 via crafted programming-protocol frames.",
            affected_before="1.6.2.0", published="2018-08-29",
        ),
        _cve(
            "CVE-2018-7821", "HIGH",
            "Cycle-time impact when flooding the M221 Ethernet interface while "
            "the EtherNet/IP adapter is activated (affects SoMachine Basic too).",
            affected_before="1.10.0.0", published="2019-05-22",
        ),
    ],
    ("Cisco", "IOS"): [
        _cve(
            "CVE-2017-12240", "CRITICAL",
            "Buffer overflow in the DHCP relay subsystem allows unauthenticated "
            "remote code execution via crafted DHCPv4 packets (Cisco IOS 12.2-15.6).",
            affected_before="15.6", published="2017-09-28",
        ),
        _cve(
            "CVE-2016-6382", "HIGH",
            "Malformed IPv6 PIM register packet causes unauthenticated remote "
            "device restart / DoS (Cisco IOS 15.2-15.6).",
            affected_before="15.6", published="2016-10-05",
        ),
    ],
    ("Juniper", "Junos"): [
        _cve(
            "CVE-2021-0283", "HIGH",
            "TCP/IP stack buffer overflow triggers SYSTEM_ABNORMAL_SHUTDOWN via "
            "crafted packet sequences targeting the device directly (multi-branch).",
            affected_before="12.3R12-S19", published="2021-07-15",
        ),
    ],
    # RESEARCH.md Open Question 1: no NVD/CISA advisory names "FX16"
    # specifically — Johnson Controls' documented CVE history sits under the
    # "Facility Explorer" / Tridium Niagara product family, which FX16 field
    # controllers register under. Keyed on the real-CVE product family
    # ("Facility Explorer") per Recommendation (a); affected_before=None
    # (vendor+model-only match, D-08 'medium' confidence, CVE-03-safe
    # default — no FX16-specific version range is NVD-verifiable).
    ("Johnson Controls", "Facility Explorer"): [
        _cve(
            "CVE-2017-16744", "HIGH",
            "Path-traversal flaw in Tridium Niagara (used by Facility Explorer) "
            "exploitable by an authenticated admin on Windows installations.",
            affected_before=None, published="2018-08-20",
        ),
    ],
}


# ---------------------------------------------------------------------------
# Firmware version comparator (D-07) — fail-closed, format-tolerant tuple parser
# ---------------------------------------------------------------------------

# ReDoS-safe (T-142-01): no nested/overlapping quantifiers. Handles the 5
# verified real-world formats from 142-RESEARCH.md Pattern 2:
#   "1.6.2.0"        Schneider M221 (4-part dotted)
#   "9.0.1"          Johnson Controls FX16 (3-part dotted)
#   "15.2(4)M3"      Cisco classic IOS (parenthetical rebuild + train letters)
#   "16.9.1"         Cisco IOS-XE (plain 3-part dotted)
#   "12.3R12-S19"    Juniper Junos (release + service-patch suffix)
_FW_RE = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)"
    r"(?:\.(?P<patch>\d+))?"
    r"(?:\.(?P<build>\d+))?"
    r"(?:R(?P<release>\d+))?"
    r"(?:\((?P<rebuild>\d+)\))?"
    r"[A-Za-z0-9]*"
    r"(?:-S(?P<service>\d+))?"
    r"$"
)


def parse_firmware(raw: Optional[str]) -> Optional[tuple]:
    """Parses a firmware string into a comparable int tuple, or returns
    ``None`` if the string doesn't cleanly parse (CVE-03: fail-closed —
    never a guessed/fuzzy comparable value).

    Service-patch level sorts LAST so Juniper's "-S19" compares greater than
    the bare "R12" release it patches (more patched = greater), per
    142-RESEARCH.md's documented Juniper anti-pattern.
    """
    if not raw:
        return None
    m = _FW_RE.match(raw.strip())
    if not m:
        return None
    g = m.groupdict()
    return (
        int(g["major"]),
        int(g["minor"]),
        int(g["patch"] or 0),
        int(g["build"] or 0),
        int(g["release"] or 0),
        int(g["rebuild"] or 0),
        int(g["service"] or 0),
    )


def _in_range(fw_tuple: tuple, affected_before: str) -> bool:
    """Returns True when ``fw_tuple`` is strictly less than the parsed form
    of ``affected_before`` (RESEARCH.md Pitfall 2: "prior to X" NVD language
    is exclusive — strict `<`, not `<=`). If ``affected_before`` itself
    doesn't parse, the range is unusable and this returns False (fail-closed,
    never guess)."""
    boundary = parse_firmware(affected_before)
    if boundary is None:
        return False
    return fw_tuple < boundary


# ---------------------------------------------------------------------------
# Correlation join (D-01..D-04, D-08)
# ---------------------------------------------------------------------------

# NVD CVSS v3.x baseSeverity ordinal — most severe first (D-04).
_SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


@dataclass
class CveMatchResult:
    """Result of a ``correlate_device()`` call."""

    matches: list = field(default_factory=list)
    confidence: Optional[str] = None  # "high" | "medium" | None
    attempted: bool = False


def correlate_device(
    vendor: Optional[str], model: Optional[str], firmware: Optional[str]
) -> CveMatchResult:
    """Joins a fingerprinted device against the curated ``CVE_TABLE``.

    NOTE: this function does NOT gate on ``vendor == "Unknown"`` (D-03) —
    that skip decision (no CVE annotation rendered at all) is the CALL
    SITE's responsibility, exercised before invoking this function
    (RESEARCH.md Pitfall 4). Callers must check ``vendor != "Unknown"``
    themselves; calling this with an unidentified/absent vendor+model simply
    yields an empty (attempted, no-match) result here.

    Logic (D-02/D-07/D-08):
    - If ``(vendor, model)`` is absent from ``CVE_TABLE``: attempted=True,
      matches=[], confidence=None.
    - For each candidate CVE entry:
      - ``affected_before is None`` -> vendor+model-only match (append,
        contributes "medium" confidence, D-08).
      - ``affected_before`` is set -> parse ``firmware``; if it parses AND
        falls strictly inside the affected range, append (contributes
        "high" confidence). If ``firmware`` is None/unparseable, that entry
        does not match (CVE-03: never fuzzy-match).
    - Overall confidence: "high" if any high-confidence match, else "medium"
      if any vendor+model-only match, else None.
    - Matches sorted by severity, most severe first (D-04).
    """
    entries = CVE_TABLE.get((vendor, model))
    if not entries:
        return CveMatchResult(matches=[], confidence=None, attempted=True)

    fw_tuple = parse_firmware(firmware) if firmware else None

    matches: list = []
    saw_high = False
    saw_medium = False
    for entry in entries:
        affected_before = entry["affected_before"]
        if affected_before is None:
            matches.append(entry)
            saw_medium = True
        elif fw_tuple is not None and _in_range(fw_tuple, affected_before):
            matches.append(entry)
            saw_high = True
        # else: unparseable/None firmware against a version-ranged entry, or
        # firmware outside the range -> that entry does not match (D-07).

    confidence = "high" if saw_high else ("medium" if saw_medium else None)
    matches.sort(key=lambda m: _SEVERITY_ORDER.get(m["severity"], len(_SEVERITY_ORDER)))

    return CveMatchResult(matches=matches, confidence=confidence, attempted=True)


# ---------------------------------------------------------------------------
# status_report() — mirrors compliance.status_report()'s print-table shape
# ---------------------------------------------------------------------------


def status_report(fmt: str = "text") -> None:
    """Prints ``CVE_TABLE_META`` version/last_verified/verdict plus a
    per-entry (vendor, model, cve_id, severity, affected_before, source_url)
    table. Used by ``quirk cve status`` (D-10, wired in Plan 02)."""
    verdict = "STALE" if is_cve_table_stale() else "FRESH"

    rows = []
    for (vendor, model), entries in CVE_TABLE.items():
        for entry in entries:
            rows.append(
                {
                    "vendor": vendor,
                    "model": model,
                    "cve_id": entry["cve_id"],
                    "severity": entry["severity"],
                    "affected_before": entry["affected_before"],
                    "source_url": entry["source_url"],
                }
            )

    if fmt == "json":
        import json as _json

        print(
            _json.dumps(
                {
                    "source": CVE_TABLE_META["source"],
                    "last_verified": CVE_TABLE_META["last_verified"],
                    "verdict": verdict,
                    "entries": rows,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    print(f"Source: {CVE_TABLE_META['source']}")
    print(f"Last Verified: {CVE_TABLE_META['last_verified']}")
    print(f"Verdict: {verdict}")
    print()
    print(f"{'Vendor':<20} {'Model':<22} {'CVE ID':<18} {'Severity':<10} "
          f"{'Affected Before':<18} Source URL")
    print("-" * 120)
    for row in rows:
        print(
            f"{row['vendor']:<20} {row['model']:<22} {row['cve_id']:<18} "
            f"{row['severity']:<10} {str(row['affected_before']):<18} "
            f"{row['source_url']}"
        )


__all__ = [
    "STALENESS_THRESHOLD_DAYS",
    "CVE_TABLE_META",
    "CVE_TABLE",
    "CveMatchResult",
    "is_cve_table_stale",
    "nvd_url",
    "parse_firmware",
    "correlate_device",
    "status_report",
]
