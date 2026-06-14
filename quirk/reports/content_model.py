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

Phase 99 — Per-finding context (CTX-01 / CTX-02):
D-01/Phase99: ALGO_IMPACT_MAP extended to 3-tuple adding quantum_risk_sentence.
D-04/Phase99: REMEDIATION_CATALOG added — same key set, weakness-specific copy.
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

    # Phase 128 D-08: hardware advisory — populated by writer.py from HardwareDevice rows
    # Advisory-only; never routed through _build_finding() / findings_evaluator.py (D-08 DISPOSITION).
    hardware_devices: List[dict] = field(default_factory=list)


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
# Phase 99 D-01/CTX-01: extended to 3-tuple — (risk_label, impact_sentence, quantum_risk_sentence).
# All quantum_risk_sentence values are verbatim from 99-UI-SPEC.md §Copywriting Contract.
# ---------------------------------------------------------------------------

# Keyed on crypto class keyword (matches against finding severity ≥ MEDIUM).
# Tuple: (risk_label, impact_sentence, quantum_risk_sentence)
# Index [0] and [1] are UNCHANGED from Phase 98; index [2] is Phase 99 addition.
ALGO_IMPACT_MAP: Dict[str, tuple[str, str, str]] = {
    # D-02 / EXEC-02: harvest-now-decrypt-later for asymmetric algorithms
    "RSA": (
        "Harvest-now-decrypt-later exposure",
        "adversaries may already be archiving encrypted traffic for future decryption.",
        "RSA key material is vulnerable to Shor's algorithm — a sufficiently powerful"
        " quantum computer can factor the modulus and recover the private key, breaking"
        " both confidentiality and non-repudiation.",
    ),
    "ECC": (
        "Harvest-now-decrypt-later exposure",
        "adversaries may already be archiving encrypted traffic for future decryption.",
        "Elliptic-curve key material is vulnerable to Shor's algorithm — quantum computers"
        " can solve the discrete logarithm problem and recover the private key, compromising"
        " authentication and forward secrecy.",
    ),
    "ECDSA": (
        "Harvest-now-decrypt-later exposure",
        "adversaries may already be archiving encrypted traffic for future decryption.",
        "Elliptic-curve key material is vulnerable to Shor's algorithm — quantum computers"
        " can solve the discrete logarithm problem and recover the private key, compromising"
        " authentication and forward secrecy.",
    ),
    "DH": (
        "Harvest-now-decrypt-later exposure",
        "adversaries may already be archiving encrypted traffic for future decryption.",
        "Diffie–Hellman key exchange is vulnerable to Shor's algorithm — a quantum"
        " adversary can solve the discrete log problem on recorded sessions, retroactively"
        " decrypting captured traffic.",
    ),
    "DSA": (
        "Harvest-now-decrypt-later exposure",
        "adversaries may already be archiving encrypted traffic for future decryption.",
        "DSA signatures rely on the discrete logarithm problem, which Shor's algorithm"
        " breaks — a quantum attacker can forge signatures and impersonate the signing entity.",
    ),
    # D-02 / EXEC-02: weak hashing
    "WEAK_HASH": (
        "Integrity risk",
        "weak hashing algorithms undermine tamper-evidence guarantees.",
        "MD5 collision resistance is already broken classically; quantum speedups (Grover's"
        " algorithm) further halve the effective security margin, making collision attacks"
        " feasible with modest resources.",
    ),
    "MD5": (
        "Integrity risk",
        "weak hashing algorithms undermine tamper-evidence guarantees.",
        "MD5 collision resistance is already broken classically; quantum speedups (Grover's"
        " algorithm) further halve the effective security margin, making collision attacks"
        " feasible with modest resources.",
    ),
    "SHA1": (
        "Integrity risk",
        "weak hashing algorithms undermine tamper-evidence guarantees.",
        "SHA-1 collision resistance is broken classically; Grover's algorithm halves the"
        " quantum bit-security to ~40 bits, making pre-image and collision attacks practical"
        " for state-level adversaries.",
    ),
    "SHA-1": (
        "Integrity risk",
        "weak hashing algorithms undermine tamper-evidence guarantees.",
        "SHA-1 collision resistance is broken classically; Grover's algorithm halves the"
        " quantum bit-security to ~40 bits, making pre-image and collision attacks practical"
        " for state-level adversaries.",
    ),
    # D-02 / EXEC-02: weak key exchange / authentication
    "WEAK_KEY_EXCHANGE": (
        "Authentication exposure",
        "weak key exchange allows credential interception.",
        "Export-grade and short-parameter key exchange can be broken in real time by a"
        " classical adversary today; quantum acceleration makes recovery of session keys"
        " trivially fast.",
    ),
    "DHE_EXPORT": (
        "Authentication exposure",
        "weak key exchange allows credential interception.",
        "Export-grade and short-parameter key exchange can be broken in real time by a"
        " classical adversary today; quantum acceleration makes recovery of session keys"
        " trivially fast.",
    ),
    "RC4": (
        "Authentication exposure",
        "weak key exchange allows credential interception.",
        "RC4 stream cipher is cryptographically broken classically; even without quantum"
        " acceleration it provides no meaningful confidentiality — remediation is overdue.",
    ),
    "3DES": (
        "Authentication exposure",
        "weak key exchange allows credential interception.",
        "Triple-DES and DES use 56–168-bit key lengths that Grover's algorithm reduces"
        " to at most 84 effective bits — insufficient for any security boundary beyond 2030.",
    ),
    "DES": (
        "Authentication exposure",
        "weak key exchange allows credential interception.",
        "Triple-DES and DES use 56–168-bit key lengths that Grover's algorithm reduces"
        " to at most 84 effective bits — insufficient for any security boundary beyond 2030.",
    ),
    # Phase 99 CTX-03: code-signing expiry — new keys (D-07/D-08)
    # quantum_risk_sentence verbatim from 99-UI-SPEC.md §Copywriting Contract.
    "CODESIGN_EXPIRY": (
        "Supply-chain trust failure",
        "expired code-signing certificate breaks software verification chains.",
        "An expired code-signing certificate breaks the trust chain — any software signed"
        " by this certificate can no longer be verified as authentic, enabling supply-chain"
        " attacks or silent malware delivery.",
    ),
    "CODESIGN_APPROACHING_EXPIRY": (
        "Imminent supply-chain risk",
        "code-signing certificate nearing expiry risks blocking deployments.",
        "A code-signing certificate expiring within 90 days creates operational risk —"
        " if not renewed before expiry, software signed by this certificate will fail"
        " verification, blocking deployments and breaking trust.",
    ),
}

# Phase 99 CTX-01: fallback quantum_risk sentence for findings with no crypto-class match.
# Verbatim from 99-UI-SPEC.md §Field Name Contract default-fallback string.
FALLBACK_QUANTUM_RISK: str = (
    "This cryptographic weakness reduces the security margin against quantum-capable"
    " adversaries. Migrate to NIST-approved post-quantum algorithms per NIST IR 8547."
)

# Phase 99 D-04/CTX-02: centralized remediation catalog — same key set as ALGO_IMPACT_MAP.
# Keys mirror ALGO_IMPACT_MAP — same key set, ordered identically.
# All copy verbatim from 99-UI-SPEC.md §Per-Finding Remediation Catalog (locked).
REMEDIATION_CATALOG: Dict[str, str] = {
    "RSA": (
        "Replace RSA keys with NIST PQC standard algorithms: ML-KEM (FIPS 203) for key"
        " encapsulation or ML-DSA (FIPS 204) for digital signatures. Prioritize certificates"
        " and TLS endpoints first."
    ),
    "ECC": (
        "Replace ECDSA/ECDH keys with ML-DSA (FIPS 204) for signatures or ML-KEM (FIPS 203)"
        " for key encapsulation. During transition, deploy hybrid TLS (X25519+ML-KEM) as an"
        " intermediate step."
    ),
    "ECDSA": (
        "Replace ECDSA/ECDH keys with ML-DSA (FIPS 204) for signatures or ML-KEM (FIPS 203)"
        " for key encapsulation. During transition, deploy hybrid TLS (X25519+ML-KEM) as an"
        " intermediate step."
    ),
    "DH": (
        "Disable finite-field Diffie–Hellman key exchange. Configure TLS to prefer X25519"
        " (classical) or X25519+ML-KEM hybrid groups; disable DHE cipher suites in the server's"
        " TLS configuration."
    ),
    "DSA": (
        "Disable DSA. Replace DSA-based SSH host keys and certificates with Ed25519 (short-term)"
        " or ML-DSA (FIPS 204) when library support is available."
    ),
    "WEAK_HASH": (
        "Replace MD5 in all signing, integrity, and authentication contexts. Use SHA-256 or"
        " SHA-3-256 as minimum. Reject MD5-signed certificates at the trust-store level."
    ),
    "MD5": (
        "Replace MD5 in all signing, integrity, and authentication contexts. Use SHA-256 or"
        " SHA-3-256 as minimum. Reject MD5-signed certificates at the trust-store level."
    ),
    "SHA1": (
        "Replace SHA-1 signatures with SHA-256 or stronger. Reissue any SHA-1-signed"
        " certificates. Configure TLS to reject SHA-1 in the signature_algorithms extension."
    ),
    "SHA-1": (
        "Replace SHA-1 signatures with SHA-256 or stronger. Reissue any SHA-1-signed"
        " certificates. Configure TLS to reject SHA-1 in the signature_algorithms extension."
    ),
    "WEAK_KEY_EXCHANGE": (
        "Remove all export-grade cipher suites from TLS configuration. Disable DHE_EXPORT and"
        " similar suites. Apply OS and application TLS hardening guides (e.g., Mozilla SSL"
        " Config Generator — Intermediate or Modern profile)."
    ),
    "DHE_EXPORT": (
        "Remove all export-grade cipher suites from TLS configuration. Disable DHE_EXPORT and"
        " similar suites. Apply OS and application TLS hardening guides (e.g., Mozilla SSL"
        " Config Generator — Intermediate or Modern profile)."
    ),
    "RC4": (
        "Disable RC4 in all TLS and non-TLS contexts. RC4 is prohibited by RFC 7465. Replace"
        " with AES-128-GCM or AES-256-GCM cipher suites."
    ),
    "3DES": (
        "Disable 3DES and DES cipher suites (Sweet32 / NIST SP 800-131A Rev 2 disallowed after"
        " 2023). Replace with AES-GCM. Verify no legacy application dependency remains before"
        " removal."
    ),
    "DES": (
        "Disable 3DES and DES cipher suites (Sweet32 / NIST SP 800-131A Rev 2 disallowed after"
        " 2023). Replace with AES-GCM. Verify no legacy application dependency remains before"
        " removal."
    ),
    # Phase 99 CTX-03: code-signing expiry remediation (D-07/D-08)
    "CODESIGN_EXPIRY": (
        "Renew the expired code-signing certificate immediately and re-sign all artifacts."
        " Revoke the expired certificate via the issuing CA and update any pinned certificate"
        " references in build pipelines."
    ),
    "CODESIGN_APPROACHING_EXPIRY": (
        "Renew this code-signing certificate before the not_after date. Update automated renewal"
        " policy and alert thresholds to trigger at 90 days remaining to prevent future expiry."
    ),
}

# D-02 / EXEC-02: minimum severity for a finding to generate a top-risk entry.
_RISK_SEVERITY_INCLUDE: frozenset[str] = frozenset({"CRITICAL", "HIGH", "MEDIUM"})

# D-02 / EXEC-02: keywords checked against finding title/category/check_id (case-insensitive).
# Ordered: first match wins for a given finding.
# Phase 99: codesign expiry keys MUST precede "DES" — "CODESIGN_EXPIRY" contains "DES" as
# a substring and would false-match if "DES" were checked first.
_ALGO_KEYWORDS: tuple[str, ...] = (
    # Phase 99 CTX-03: code-signing expiry — matched via check_id field (A1 route).
    # Placed first to prevent false-match against "DES" substring.
    "CODESIGN_APPROACHING_EXPIRY",
    "CODESIGN_EXPIRY",
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
        risk_label, impact_sentence, _ = ALGO_IMPACT_MAP[crypto_class]
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
    # Phase 99 CTX-01/CTX-02: per-finding context catalog + fallback
    "REMEDIATION_CATALOG",
    "FALLBACK_QUANTUM_RISK",
    # Error
    "ReportCongruenceError",
    # Functions
    "_check_congruence",
    "_classify_finding",
    "build_exec_content",
    "assert_congruent",
]
