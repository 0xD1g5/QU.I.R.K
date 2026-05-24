"""Phase 98 — Shared executive content model (D-03 / EXEC-01..04, TRANS-01..03).

Single seam between scoring/findings data and the CLI/HTML report surfaces.
Both build_exec_markdown (executive.py) and render_html_report (html_renderer.py)
consume one ExecContent instance; neither re-derives content from raw inputs.

D-01: Deterministic rule-based composition — no LLM, fully offline.
D-02: top_risks from static ALGO_IMPACT_MAP (crypto class → impact sentences).
D-03: Shared content object — renderers format, never generate content.
D-04: Within-bucket roadmap ordering: high-impact/low-effort first.
D-05: Effort/impact from static EFFORT_IMPACT_MAP keyed on title keyword.
D-06: _check_congruence() raises ReportCongruenceError before any file I/O.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Dataclasses — plain @dataclass (mutable build-time objects, per PATTERNS.md)
# ---------------------------------------------------------------------------


@dataclass
class RiskItem:
    """One row in the Priority Business Risks list (EXEC-02 / D-02)."""

    risk_label: str       # e.g. "Harvest-now-decrypt-later exposure"
    impact_sentence: str  # e.g. "adversaries may already be archiving..."
    severity: str         # "CRITICAL" | "HIGH" | "MEDIUM"


@dataclass
class RoadmapItem:
    """Roadmap item with D-05 effort/impact metadata injected (EXEC-03).

    Phase 98 extends the raw roadmap dict with effort/impact bands and a
    priority_score used for within-bucket ordering (D-04).
    """

    phase: str              # "NOW" | "NEXT" | "LATER"
    title: str
    why: str
    owner_placeholder: str
    timeframe: str
    effort: str             # "LOW" | "MEDIUM" | "HIGH"
    impact: str             # "HIGH" | "MEDIUM" | "LOW"
    priority_score: float   # IMPACT_RANK * (4 - EFFORT_RANK) — higher is better


@dataclass
class ExecContent:
    """Single structured content object consumed by both renderers (D-03).

    Built once by build_exec_content(); renderers receive this instance and
    format its fields — they do not re-derive content from raw score/findings.
    """

    # EXEC-01: narrative
    narrative_lead: str            # band-specific opening sentence
    narrative_drivers: List[str]   # score driver clauses from score_raw["drivers"]

    # EXEC-02: top risks (D-02 static map)
    top_risks: List[RiskItem]

    # EXEC-03: roadmap with effort/impact, sorted within each bucket (D-04/D-05)
    roadmap_items: List[RoadmapItem]

    # TRANS-01 / D-07: score transparency — pass-through from score_raw
    score_total: int
    score_band: str
    subscores: Dict[str, Any]   # {hygiene, modern_tls, identity_trust, agility_signals, data_at_rest, data_in_motion}
    raw_sum: int                # sum(subscores.values()); 0 when subscores is empty — no error

    # TRANS-03 / D-06: severity counts computed once; feeds congruence guard + both renderers
    sev_counts: Dict[str, int]  # {"CRITICAL": n, "HIGH": n, ...}


# ---------------------------------------------------------------------------
# D-04: Ordering dicts for within-bucket priority sort
# ---------------------------------------------------------------------------

# D-04 / EXEC-03: impact and effort rank values for within-bucket priority scoring.
# priority_score = IMPACT_RANK[impact] * (4 - EFFORT_RANK[effort])
# High impact × low effort → largest score → sorted first.
EFFORT_RANK: Dict[str, int] = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
IMPACT_RANK: Dict[str, int] = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

# ---------------------------------------------------------------------------
# D-02: Algorithm-class → impact-band static map (EXEC-02)
# ---------------------------------------------------------------------------

# Keyed on crypto class keyword (matches against finding severity ≥ MEDIUM).
# Tuple: (risk_label, impact_sentence) — values from UI-SPEC Copywriting Contract.
ALGO_IMPACT_MAP: Dict[str, tuple[str, str]] = {
    # D-02 / EXEC-02: harvest-now-decrypt-later for asymmetric algorithms
    "RSA": (
        "Harvest-now-decrypt-later exposure",
        "adversaries may already be archiving encrypted traffic for future decryption.",
    ),
    "ECC": (
        "Harvest-now-decrypt-later exposure",
        "adversaries may already be archiving encrypted traffic for future decryption.",
    ),
    "ECDSA": (
        "Harvest-now-decrypt-later exposure",
        "adversaries may already be archiving encrypted traffic for future decryption.",
    ),
    "DH": (
        "Harvest-now-decrypt-later exposure",
        "adversaries may already be archiving encrypted traffic for future decryption.",
    ),
    "DSA": (
        "Harvest-now-decrypt-later exposure",
        "adversaries may already be archiving encrypted traffic for future decryption.",
    ),
    # D-02 / EXEC-02: weak hashing
    "WEAK_HASH": (
        "Integrity risk",
        "weak hashing algorithms undermine tamper-evidence guarantees.",
    ),
    "MD5": (
        "Integrity risk",
        "weak hashing algorithms undermine tamper-evidence guarantees.",
    ),
    "SHA1": (
        "Integrity risk",
        "weak hashing algorithms undermine tamper-evidence guarantees.",
    ),
    "SHA-1": (
        "Integrity risk",
        "weak hashing algorithms undermine tamper-evidence guarantees.",
    ),
    # D-02 / EXEC-02: weak key exchange / authentication
    "WEAK_KEY_EXCHANGE": (
        "Authentication exposure",
        "weak key exchange allows credential interception.",
    ),
    "DHE_EXPORT": (
        "Authentication exposure",
        "weak key exchange allows credential interception.",
    ),
    "RC4": (
        "Authentication exposure",
        "weak key exchange allows credential interception.",
    ),
    "3DES": (
        "Authentication exposure",
        "weak key exchange allows credential interception.",
    ),
    "DES": (
        "Authentication exposure",
        "weak key exchange allows credential interception.",
    ),
}

# D-02 / EXEC-02: minimum severity for a finding to generate a top-risk entry.
_RISK_SEVERITY_INCLUDE: frozenset[str] = frozenset({"CRITICAL", "HIGH", "MEDIUM"})

# D-02 / EXEC-02: keywords checked against finding title/category/check_id (case-insensitive).
# Ordered: first match wins for a given finding.
_ALGO_KEYWORDS: tuple[str, ...] = (
    "RSA",
    "ECC",
    "ECDSA",
    "DH",
    "DSA",
    "WEAK_HASH",
    "MD5",
    "SHA1",
    "SHA-1",
    "WEAK_KEY_EXCHANGE",
    "DHE_EXPORT",
    "RC4",
    "3DES",
    "DES",
)

# ---------------------------------------------------------------------------
# D-05: Finding-type → effort/impact static map (EXEC-03)
# ---------------------------------------------------------------------------

# Keyed on roadmap item title keyword (case-insensitive substring match).
# Tuple: (effort_band, impact_band)
EFFORT_IMPACT_MAP: Dict[str, tuple[str, str]] = {
    # D-05 / EXEC-03: low-effort high-impact quick wins
    "certificate": ("LOW", "HIGH"),
    "tls 1.0": ("LOW", "HIGH"),
    "tls 1.1": ("LOW", "HIGH"),
    "ssl": ("LOW", "HIGH"),
    "rc4": ("LOW", "HIGH"),
    "3des": ("LOW", "HIGH"),
    "md5": ("LOW", "HIGH"),
    "sha-1": ("LOW", "HIGH"),
    "sha1": ("LOW", "HIGH"),
    # D-05 / EXEC-03: medium-effort high-impact
    "key exchange": ("MEDIUM", "HIGH"),
    "hybrid": ("MEDIUM", "HIGH"),
    "migration": ("MEDIUM", "HIGH"),
    "pqc": ("MEDIUM", "HIGH"),
    "post-quantum": ("MEDIUM", "HIGH"),
    "agility": ("MEDIUM", "HIGH"),
    # D-05 / EXEC-03: high-effort high-impact (infrastructure overhauls)
    "pki": ("HIGH", "HIGH"),
    "ca": ("HIGH", "HIGH"),
    "hsm": ("HIGH", "HIGH"),
    "kms": ("HIGH", "HIGH"),
    "rekey": ("HIGH", "MEDIUM"),
    # D-05 / EXEC-03: low-effort medium-impact (config/tuning)
    "config": ("LOW", "MEDIUM"),
    "cipher": ("LOW", "MEDIUM"),
    "ssh": ("LOW", "MEDIUM"),
    "protocol": ("MEDIUM", "MEDIUM"),
    # D-05 / EXEC-03: scanning / inventory (foundation, medium effort/impact)
    "inventory": ("MEDIUM", "MEDIUM"),
    "cbom": ("MEDIUM", "MEDIUM"),
    "audit": ("MEDIUM", "MEDIUM"),
}

# ---------------------------------------------------------------------------
# D-01: Narrative lead sentences — 5 scoring bands collapsed to 4 narrative tones
# UI-SPEC Copywriting Contract exact strings.
# ---------------------------------------------------------------------------

# EXCELLENT and GOOD both map to the GOOD narrative lead (per RESEARCH Pattern 4).
# MODERATE → FAIR lead; FAIR → POOR lead; POOR → CRITICAL lead.
_NARRATIVE_LEADS: Dict[str, str] = {
    # D-01 / EXEC-01 / RESEARCH Pattern 4: 5→4 collapse
    "EXCELLENT": (
        "This organization demonstrates strong quantum-readiness across its"
        " cryptographic infrastructure."
    ),
    "GOOD": (
        "This organization demonstrates strong quantum-readiness across its"
        " cryptographic infrastructure."
    ),
    "MODERATE": (
        "This organization has foundational cryptographic controls in place"
        " with meaningful gaps requiring attention."
    ),
    "FAIR": (
        "This organization's cryptographic posture presents significant"
        " exposure to quantum-era threats."
    ),
    "POOR": (
        "This organization's cryptographic posture is critically deficient"
        " and requires immediate remediation."
    ),
}

_NARRATIVE_LEAD_FALLBACK = (
    "No findings were detected. Verify scan coverage before distributing this report."
)

# ---------------------------------------------------------------------------
# D-06: Congruence guard (TRANS-03)
# ---------------------------------------------------------------------------

# Threshold: number of CRITICAL findings allowed per headline band.
# None = no restriction (FAIR/POOR can coexist with any severity mix).
_BAND_CRITICAL_THRESHOLD: Dict[str, Optional[int]] = {
    "EXCELLENT": 0,   # D-06: zero CRITICAL allowed with EXCELLENT
    "GOOD": 0,        # D-06: zero CRITICAL allowed with GOOD
    "MODERATE": 0,    # D-06: zero CRITICAL allowed with MODERATE — per RESEARCH Pattern 2
    "FAIR": None,     # D-06: no restriction — FAIR can coexist with CRITICAL
    "POOR": None,     # D-06: no restriction — POOR can coexist with CRITICAL
}


class ReportCongruenceError(ValueError):
    """D-06 / TRANS-03: raised when exec headline band contradicts severity counts.

    Message matches UI-SPEC Copywriting Contract exactly:
      "Report generation halted: executive headline '{band}' is inconsistent
       with {n} CRITICAL finding(s). Review findings before generating the report."
    """


def _check_congruence(band: str, sev_counts: Dict[str, int]) -> None:
    """D-06 / TRANS-03: fail-fast if headline band contradicts finding severity counts.

    Called by build_exec_content() before returning — raises before any I/O.

    Args:
        band: The headline rating band from score_raw["rating"] ("EXCELLENT" …"POOR").
        sev_counts: Severity count dict from findings {"CRITICAL": n, "HIGH": n, …}.

    Raises:
        ReportCongruenceError: if band is EXCELLENT/GOOD/MODERATE and CRITICAL > 0.
    """
    threshold = _BAND_CRITICAL_THRESHOLD.get(band)
    if threshold is None:
        return  # D-06: FAIR / POOR — no restriction
    n_critical = sev_counts.get("CRITICAL", 0)
    if n_critical > threshold:
        raise ReportCongruenceError(
            f"Report generation halted: executive headline '{band}' is inconsistent"
            f" with {n_critical} CRITICAL finding(s)."
            f" Review findings before generating the report."
        )


def assert_congruent(band: str, findings: List[Dict[str, Any]]) -> None:
    """Public D-06 guard for callers that render WITHOUT a prebuilt ExecContent.

    WR-05: the backward-compat (`exec_content is None`) paths in both renderers
    must remain fail-closed — an EXCELLENT/GOOD/MODERATE band rendered alongside a
    CRITICAL finding is the exact incongruence ReportCongruenceError exists to block.
    Wraps the severity tally + guard so the rule lives in one place.

    Raises:
        ReportCongruenceError: if band contradicts the findings' CRITICAL count.
    """
    _check_congruence(band, _count_severities(findings))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _classify_finding(finding: Dict[str, Any]) -> Optional[str]:
    """D-02: map a finding to a crypto-class key in ALGO_IMPACT_MAP.

    Inspects finding severity (must be in _RISK_SEVERITY_INCLUDE) and then
    title/description/category/check_id for keyword matches (case-insensitive).
    Returns None if no match or severity below threshold.
    """
    severity = str(finding.get("severity", "")).upper()
    if severity not in _RISK_SEVERITY_INCLUDE:
        return None

    # Build search string from all available finding text fields
    search_text = " ".join([
        str(finding.get("title", "")),
        str(finding.get("description", "")),
        str(finding.get("category", "")),
        str(finding.get("check_id", "")),
    ]).upper()

    for keyword in _ALGO_KEYWORDS:
        if keyword.upper() in search_text:
            return keyword
    return None


def _build_top_risks(findings: List[Dict[str, Any]]) -> List[RiskItem]:
    """D-02 / EXEC-02: select top-risks from ALGO_IMPACT_MAP based on findings.

    Returns unique RiskItems ordered by severity (CRITICAL > HIGH > MEDIUM).
    Executive-tier framing only — no per-finding "so what" prose (Phase 99).
    """
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
    seen_labels: set[str] = set()
    candidates: List[tuple[int, RiskItem]] = []

    for finding in findings:
        crypto_class = _classify_finding(finding)
        if crypto_class is None:
            continue
        risk_label, impact_sentence = ALGO_IMPACT_MAP[crypto_class]
        if risk_label in seen_labels:
            continue
        seen_labels.add(risk_label)
        severity = str(finding.get("severity", "MEDIUM")).upper()
        sort_key = severity_order.get(severity, 99)
        candidates.append((sort_key, RiskItem(
            risk_label=risk_label,
            impact_sentence=impact_sentence,
            severity=severity,
        )))

    candidates.sort(key=lambda t: t[0])
    return [item for _, item in candidates]


def _enrich_roadmap_item(raw: Dict[str, Any]) -> RoadmapItem:
    """D-05 / EXEC-03: attach effort/impact bands to a raw roadmap item dict.

    Looks up the item title in EFFORT_IMPACT_MAP (case-insensitive substring).
    Falls back to ("MEDIUM", "MEDIUM") when no keyword matches.
    """
    title = str(raw.get("title", ""))
    title_lower = title.lower()

    effort = "MEDIUM"
    impact = "MEDIUM"
    for keyword, (e, i) in EFFORT_IMPACT_MAP.items():
        if keyword in title_lower:
            effort, impact = e, i
            break

    priority_score = float(IMPACT_RANK[impact]) * (4 - EFFORT_RANK[effort])

    return RoadmapItem(
        phase=str(raw.get("phase", "")),
        title=title,
        why=str(raw.get("why", "")),
        owner_placeholder=str(raw.get("owner_placeholder", "")),
        timeframe=str(raw.get("timeframe", "")),
        effort=effort,
        impact=impact,
        priority_score=priority_score,
    )


def _sort_roadmap_items(items: List[RoadmapItem]) -> List[RoadmapItem]:
    """D-04 / EXEC-03: sort within each NOW/NEXT/LATER bucket.

    High-impact/low-effort first (highest priority_score first).
    Tie-broken by original list order (stable sort preserves _priority ordering).
    """
    bucket_order = {"NOW": 0, "NEXT": 1, "LATER": 2}
    # Stable sort: primary key = bucket, secondary = -priority_score (descending)
    return sorted(
        items,
        key=lambda r: (bucket_order.get(r.phase, 99), -r.priority_score),
    )


def _count_severities(findings: List[Dict[str, Any]]) -> Dict[str, int]:
    """TRANS-03 / D-06: count findings by severity in a single pass.

    Computed once in build_exec_content(); injected into ExecContent.sev_counts
    so both renderers and the congruence guard share the same counts.
    """
    counts: Dict[str, int] = {}
    for finding in findings:
        sev = str(finding.get("severity", "UNKNOWN")).upper()
        counts[sev] = counts.get(sev, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------

def build_exec_content(
    score_raw: Dict[str, Any],
    findings: List[Dict[str, Any]],
    roadmap_items: List[Dict[str, Any]],
) -> ExecContent:
    """D-03: build the shared ExecContent from canonical scoring-engine output.

    Must be called with score_raw from compute_readiness_score() directly
    (canonical keys: "score", "rating", "subscores", "drivers") — NOT the
    writer.py compat wrapper (which uses "total"). See RESEARCH Pitfall 1.

    D-06 / TRANS-03: calls _check_congruence() before returning. Any
    ReportCongruenceError propagates to the caller (write_reports in writer.py)
    before any file I/O is performed.

    Args:
        score_raw: Output of compute_readiness_score() with keys:
                   "score" (int), "rating" (str), "subscores" (dict),
                   "drivers" (list[str]).
        findings: List of finding dicts (title, description, severity, …).
        roadmap_items: List of raw roadmap item dicts from build_phased_roadmap().

    Returns:
        ExecContent instance ready for both renderers.

    Raises:
        ReportCongruenceError: if the headline band contradicts severity counts (D-06).
    """
    # TRANS-01/D-07: extract from canonical score_raw keys (NOT "total" — Pitfall 1)
    score_total: int = int(score_raw.get("score", 0))
    score_band: str = str(score_raw.get("rating", "POOR"))
    subscores: Dict[str, Any] = dict(score_raw.get("subscores") or {})

    # TRANS-01: raw_sum from subscores; 0 when subscores is empty — no error (Pitfall 3).
    # Defensive against malformed/non-numeric subscore values (calibration-injected
    # strings, None, "—"): sum only numeric entries so build never raises mid-report
    # after earlier artifacts were already written (CR-01). bool is an int subclass
    # and is intentionally excluded as non-meaningful.
    raw_sum: int = int(
        sum(
            v
            for v in subscores.values()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        )
    )

    # D-01 / EXEC-01: narrative lead from band (5→4 collapse per RESEARCH Pattern 4)
    narrative_lead = _NARRATIVE_LEADS.get(score_band, _NARRATIVE_LEAD_FALLBACK)

    # D-01 / EXEC-01: narrative drivers from score_raw["drivers"]. The canonical
    # scoring schema emits driver dicts ({"reason"/"label": ..., ...}); normalize to
    # the reason clause here so renderers receive plain strings (matches writer.py
    # compat path `[d["reason"] for d in ...]`). Defensive against str/dict shapes;
    # a dict lacking both reason and label is dropped rather than rendered as a raw
    # Python dict repr in the narrative (WR-02).
    narrative_drivers: List[str] = []
    for _d in (score_raw.get("drivers") or []):
        if isinstance(_d, dict):
            _text = _d.get("reason") or _d.get("label")
        else:
            _text = _d
        if _text:
            narrative_drivers.append(str(_text))

    # TRANS-03 / D-06: severity counts computed ONCE — single source for guard + renderers
    sev_counts = _count_severities(findings)

    # D-06: congruence guard — raises before any I/O if band contradicts severity
    _check_congruence(score_band, sev_counts)

    # D-02 / EXEC-02: top-risks from static ALGO_IMPACT_MAP
    top_risks = _build_top_risks(findings)

    # D-05 / EXEC-03: enrich roadmap items with effort/impact, then D-04 sort
    enriched = [_enrich_roadmap_item(r) for r in roadmap_items]
    sorted_roadmap = _sort_roadmap_items(enriched)

    return ExecContent(
        narrative_lead=narrative_lead,
        narrative_drivers=narrative_drivers,
        top_risks=top_risks,
        roadmap_items=sorted_roadmap,
        score_total=score_total,
        score_band=score_band,
        subscores=subscores,
        raw_sum=raw_sum,
        sev_counts=sev_counts,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # Dataclasses
    "RiskItem",
    "RoadmapItem",
    "ExecContent",
    # Static maps
    "ALGO_IMPACT_MAP",
    "EFFORT_IMPACT_MAP",
    "EFFORT_RANK",
    "IMPACT_RANK",
    # Error
    "ReportCongruenceError",
    # Functions
    "_check_congruence",
    "build_exec_content",
]
