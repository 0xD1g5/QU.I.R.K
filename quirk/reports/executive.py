from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List

from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.confidence import compute_confidence
from quirk.intelligence.roadmap import build_phased_roadmap
from quirk.assessment.migration_advisor import recommend_migration_paths
from quirk.reports._md_escape import md_cell  # Phase 78 / HARDEN-01: wrap scanner-controlled cells
from quirk.reports.html_renderer import build_algorithm_inventory  # Phase 81 / CMVP-06: shared inventory builder

# D-07 / WR-09 (Phase 73): fallback bullet when score dict is malformed.
_INTERPRETATION_UNAVAILABLE = "Score data unavailable for this run."


def _build_interpretation(
    evidence: Dict[str, Any],
    score: Dict[str, Any],
    endpoints=None,
    findings=None,
) -> Dict[str, Any]:
    """
    Produces human-friendly narrative bullets for executive reporting.
    Ported from quirk.assessment.interpretation_engine, adapted for intelligence dicts.
    """
    sev_counts = Counter(
        (f.get("severity", "UNKNOWN") for f in (findings or [])),
    )

    bullets: List[str] = []

    # Score framing — D-07 / WR-09 guard: score may be None, non-dict, or missing 'score' key.
    score_val = score.get("score") if isinstance(score, dict) else None
    if score_val is None:
        return {"bullets": [_INTERPRETATION_UNAVAILABLE]}
    rating_val = score.get("rating", "Unknown")
    bullets.append(
        f"Quantum Readiness Score is **{score_val}/100** (**{rating_val}**)."
    )

    # Drivers (top 3) — dict-based access (Pitfall 1: NOT tuple unpacking)
    drivers = score.get("drivers", [])
    if drivers:
        top = drivers[:3]
        drivers_txt = "; ".join(
            [f"{d['reason']} (-{d['points']})" for d in top]
        )
        bullets.append(f"Top score drivers: {drivers_txt}.")

    # TLS/SSH visibility framing
    tls_ok = len(
        [
            e
            for e in (endpoints or [])
            if getattr(e, "protocol", "") == "TLS" and not getattr(e, "scan_error", None)
        ]
    )
    ssh_ok = len(
        [
            e
            for e in (endpoints or [])
            if getattr(e, "protocol", "") == "SSH" and not getattr(e, "scan_error", None)
        ]
    )
    if tls_ok + ssh_ok == 0:
        bullets.append(
            "No successful deep TLS/SSH handshakes were captured in this run; "
            "expand visibility (scope, segmentation allowances, and ports) to improve confidence."
        )
    else:
        bullets.append(
            f"Successfully profiled **{tls_ok} TLS** and **{ssh_ok} SSH** "
            "endpoints in scope for cryptographic posture."
        )

    # TIMEOUT and NOT_TLS_ON_PORT event context from endpoints
    err_cats: Dict[str, int] = {}
    for e in (endpoints or []):
        err = getattr(e, "scan_error", None)
        if err:
            err_cats[str(err)] = err_cats.get(str(err), 0) + 1

    timeout = err_cats.get("TIMEOUT", 0)
    not_tls = err_cats.get("NOT_TLS_ON_PORT", 0)
    if timeout:
        bullets.append(
            f"Observed **{timeout} TIMEOUT** events, commonly indicating "
            "filtering/segmentation or unreachable hosts during scan."
        )
    if not_tls:
        bullets.append(
            f"Observed **{not_tls} NOT_TLS_ON_PORT** events, indicating services on "
            "TLS-like ports that do not speak TLS (common with device management interfaces)."
        )

    # CRITICAL+HIGH severity summary
    hi_crit = sev_counts.get("CRITICAL", 0) + sev_counts.get("HIGH", 0)
    bullets.append(
        f"High-impact items (CRITICAL+HIGH): **{hi_crit}**. "
        "Near-term hygiene accelerates crypto agility and reduces baseline risk."
    )

    return {"bullets": bullets}


def _count_noninfo(findings: List[Dict]) -> Counter:
    return Counter([f["severity"] for f in findings if f.get("severity") != "INFO"])


def build_exec_markdown(cfg, endpoints, findings) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    evidence = build_evidence_summary(endpoints, findings)
    score_raw = compute_readiness_score(
        evidence,
        profile=cfg.intelligence.profile,
        weights=cfg.intelligence.calibration_overrides or None,
    )
    conf_raw = compute_confidence(evidence)
    roadmap_raw = build_phased_roadmap(evidence, score_raw)
    recs = recommend_migration_paths(findings)
    interp = _build_interpretation(evidence, score_raw, endpoints=endpoints, findings=findings)

    sev_counts = _count_noninfo(findings)
    high_crit = sev_counts.get("HIGH", 0) + sev_counts.get("CRITICAL", 0)

    # Discovery counts from evidence
    tls_ok = len(
        [
            e
            for e in endpoints
            if getattr(e, "protocol", "") == "TLS" and not getattr(e, "scan_error", None)
        ]
    )
    ssh_ok = len(
        [
            e
            for e in endpoints
            if getattr(e, "protocol", "") == "SSH" and not getattr(e, "scan_error", None)
        ]
    )
    http_plain = evidence.get("plaintext_http_count", 0)
    unknown_open = evidence.get("protocol_counts", {}).get("UNKNOWN", 0)

    # Confidence section values
    coverage_pct = int(
        conf_raw.get("factor_breakdown", {})
        .get("coverage_ratio", {})
        .get("value", 0) * 100
    )
    tls_enum_coverage_pct = evidence.get("tls_enum_coverage_pct", 0)
    blockers_top = Counter(
        str(getattr(e, "scan_error", "")) for e in endpoints if getattr(e, "scan_error", None)
    ).most_common(5)

    lines: List[str] = []
    lines.append(f"# {cfg.assessment.name}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"- **Generated:** {now}")
    lines.append(f"- **Owner:** {cfg.assessment.report_owner}")
    lines.append(f"- **Data classification:** {cfg.assessment.data_classification}")
    lines.append("")

    lines.append("## Quantum Readiness Score")
    lines.append(f"**Score:** **{score_raw['score']}/100**  \n**Rating:** **{score_raw['rating']}**")
    lines.append("")
    lines.append("### Score Drivers (Top)")
    if score_raw.get("drivers"):
        for d in score_raw["drivers"][:8]:
            lines.append(f"- {md_cell(d['reason'])} (**-{d['points']}**)")

    lines.append("")
    lines.append("## Confidence & Coverage")
    lines.append(
        f"- **Confidence:** **{conf_raw['confidence_rating']}** ({conf_raw['confidence_score']}/100)"
    )
    lines.append(
        f"- **Coverage:** {coverage_pct}% "
        "(TLS+SSH successful / total in-scope endpoints)"
    )
    lines.append(
        f"- **TLS Enumeration Coverage:** {tls_enum_coverage_pct}% "
        "(TLS-success endpoints with capabilities captured)"
    )
    if blockers_top:
        lines.append("- **Top visibility blockers:**")
        for category, count in blockers_top:
            lines.append(f"  - {md_cell(category)}: {count}")

    lines.append("")
    lines.append("## Discovery and Coverage")
    lines.append(f"- **TLS endpoints successfully scanned:** {tls_ok}")
    lines.append(f"- **SSH endpoints successfully scanned:** {ssh_ok}")
    lines.append(f"- **Plaintext HTTP services detected:** {http_plain}")
    lines.append(f"- **Unknown open services detected:** {unknown_open}")
    lines.append("")

    # Phase 81 / CMVP-06: Algorithm Inventory with FIPS 140-3 CMVP Coverage column.
    # Empty matches render the literal "Not in CMVP catalog" (v4.10-D-01 invariant —
    # do not introduce alternative wording). coverage_for_algorithm is consumed via the shared
    # build_algorithm_inventory helper (which imports it lazily).
    algorithms = build_algorithm_inventory(endpoints or [])
    if algorithms:
        lines.append("## Algorithm Inventory (FIPS 140-3 Coverage)")
        lines.append("")
        lines.append("| Algorithm | NIST Level | FIPS Status | CMVP Coverage |")
        lines.append("|---|---|---|---|")
        for a in algorithms:
            cov = a.get("cmvp_coverage")
            cov_cell = md_cell(cov) if cov else "Not in CMVP catalog"
            lines.append(
                f"| {md_cell(a['name'])} | {a['nist_level']} | {md_cell(a['fips_status'])} | {cov_cell} |"
            )
        lines.append("")

    lines.append("## Findings Overview (Executive-Relevant)")
    lines.append(f"- **High-impact items (CRITICAL + HIGH):** {high_crit}")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        lines.append(f"- **{sev}:** {sev_counts.get(sev, 0)}")

    lines.append("")
    lines.append("## Interpretation")
    for b in interp.get("bullets", []):
        lines.append(f"- {md_cell(b)}")

    lines.append("")
    lines.append("## Transition Roadmap")
    lines.append("")
    roadmap_items = roadmap_raw.get("items", [])
    phase_labels = {
        "NOW": "NOW — Immediate (0-6 months)",
        "NEXT": "NEXT — Near-term (6-18 months)",
        "LATER": "LATER — Strategic (18+ months)",
    }
    for phase_key in ("NOW", "NEXT", "LATER"):
        phase_items = [r for r in roadmap_items if r.get("phase") == phase_key]
        if phase_items:
            lines.append(f"### {phase_labels[phase_key]}")
            for item in phase_items:
                lines.append(f"- **{md_cell(item['title'])}** — {md_cell(item['why'])}")
                lines.append(
                    f"  - Owner: {md_cell(item['owner_placeholder'])} | Timeframe: {md_cell(item['timeframe'])}"
                )
            lines.append("")

    if recs:
        lines.append("")
        lines.append("## Recommended Migration Paths (Top Items)")
        shown = 0
        for r in recs:
            if shown >= 10:
                break
            lines.append(f"- **{md_cell(r.get('path'))}** — {md_cell(r.get('recommendation'))}")
            if r.get("host") and r.get("port") is not None:
                lines.append(
                    f"  - Target: {md_cell(r.get('host'))}:{r.get('port')} | Severity: {r.get('severity')}"
                )
            shown += 1
        # closes cbom-intel-reports/IN-06 (Phase 77 D-12) — make truncation transparent.
        remaining = max(0, len(recs) - 10)
        if remaining:
            lines.append(f"- ... and {remaining} more (see full report)")

    lines.append("")
    lines.append("## Recommended Next Actions (30–60 days)")
    lines.append(
        "1. Confirm ownership for TLS termination points and certificate authorities "
        "(internal and cloud)."
    )
    lines.append(
        "2. Establish certificate lifecycle automation and renewal SLAs; "
        "address near-term expirations."
    )
    lines.append(
        "3. Launch crypto-agility baselining (standard TLS patterns, dependency mapping, "
        "upgrade paths)."
    )
    lines.append(
        "4. Identify 2–3 pilot candidates for PQC/hybrid readiness planning "
        "and vendor capability mapping."
    )
    lines.append("")

    return "\n".join(lines)
