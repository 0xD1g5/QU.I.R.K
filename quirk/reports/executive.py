from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.confidence import compute_confidence
from quirk.intelligence.roadmap import build_phased_roadmap
from quirk.assessment.migration_advisor import recommend_migration_paths
from quirk.reports._md_escape import md_cell  # Phase 78 / HARDEN-01: wrap scanner-controlled cells
from quirk.reports.html_renderer import build_algorithm_inventory  # Phase 81 / CMVP-06: shared inventory builder
from quirk.reports.content_model import ExecContent  # D-03 / Phase 98: shared content model

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


def build_exec_markdown(
    cfg,
    endpoints,
    findings,
    *,
    exec_content: "ExecContent | None" = None,
) -> str:
    # D-03 / Phase 98: exec_content carries shared narrative/risks/roadmap from writer.py seam.
    # When provided, narrative/risks/roadmap are sourced from exec_content (D-03 guarantee).
    # When None (backward-compat), compute locally — legacy path without the shared model.
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

    # EXEC-01 / D-03 / Phase 98: Readiness Assessment narrative prose block.
    # Sourced from exec_content when provided (shared model, guaranteed identical to HTML).
    # Falls back to _build_interpretation bullets for backward-compat when exec_content is None.
    lines.append("## Readiness Assessment")
    lines.append("")
    if exec_content is not None:
        lines.append(exec_content.narrative_lead)
        lines.append("")
        if exec_content.narrative_drivers:
            lines.append("Key factors: " + "; ".join(exec_content.narrative_drivers) + ".")
        lines.append("")
    else:
        # Backward-compat path: narrative_lead not available; render interpretation bullets
        for b in interp.get("bullets", []):
            lines.append(f"- {md_cell(b)}")
        lines.append("")

    lines.append("## Quantum Readiness Score")
    lines.append(f"**Score:** **{score_raw['score']}/100**  \n**Rating:** **{score_raw['rating']}**")
    lines.append("")
    lines.append("### Score Drivers (Top)")
    if score_raw.get("drivers"):
        for d in score_raw["drivers"][:8]:
            lines.append(f"- {md_cell(d['reason'])} (**-{d['points']}**)")

    lines.append("")

    # D-07 / SCORE-XPARENCY-01: subscore decomposition in executive markdown
    _SUBSCORE_LABELS = [
        ("hygiene",         "Hygiene"),
        ("modern_tls",      "Modern TLS"),
        ("identity_trust",  "Identity"),
        ("agility_signals", "Agility"),
        ("data_at_rest",    "Data at Rest"),
        ("data_in_motion",  "Data in Motion"),
    ]
    subscores = score_raw.get("subscores") or {}
    lines.append("### Score Decomposition")
    lines.append("")
    lines.append("| Category | Score | Budget |")
    lines.append("|----------|-------|--------|")
    for key, label in _SUBSCORE_LABELS:
        lines.append(f"| {label} | {subscores.get(key, '—')} | /25 |")
    raw_sum = sum(subscores.get(k, 0) for k, _ in _SUBSCORE_LABELS)
    lines.append("")
    lines.append(f"**Rollup:** {raw_sum} ÷ 1.5 = **{score_raw['score']} / 100**")
    lines.append("")

    # EXEC-02 / D-03 / Phase 98: Priority Business Risks from shared content model.
    # Risk labels and impact sentences come from ALGO_IMPACT_MAP (static map, D-02).
    # Finding-derived bullet labels wrapped with md_cell per HARDEN-01.
    if exec_content is not None and exec_content.top_risks:
        lines.append("## Priority Business Risks")
        lines.append("")
        for risk in exec_content.top_risks:
            lines.append(
                f"- **{md_cell(risk.risk_label)}** — {md_cell(risk.impact_sentence)}"
            )
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
    # Pitfall 6 / EXEC-01 / Phase 98: Interpretation section removed per plan 98-02.
    # Its content is now subsumed into the Readiness Assessment narrative block above
    # (narrative_lead + narrative_drivers from exec_content, or interp bullets in fallback path).
    # Do NOT re-add a separate interpretation section.

    lines.append("## Transition Roadmap")
    lines.append("")
    # EXEC-03 / D-03 / Phase 98: roadmap items with effort/impact labels.
    # When exec_content is provided, use exec_content.roadmap_items (RoadmapItem dataclasses
    # with effort/impact already attached). When not, fall back to raw roadmap_raw items.
    phase_labels = {
        "NOW": "NOW — Immediate (0-6 months)",
        "NEXT": "NEXT — Near-term (6-18 months)",
        "LATER": "LATER — Strategic (18+ months)",
    }
    if exec_content is not None:
        for phase_key in ("NOW", "NEXT", "LATER"):
            phase_items = [r for r in exec_content.roadmap_items if r.phase == phase_key]
            if phase_items:
                lines.append(f"### {phase_labels[phase_key]}")
                for item in phase_items:
                    # EXEC-03: effort/impact labels appended to each roadmap bullet (HARDEN-01: md_cell on derived text)
                    effort_label = f"{item.effort} EFFORT"
                    impact_label = f"{item.impact} IMPACT"
                    lines.append(
                        f"- **{md_cell(item.title)}** — {md_cell(item.why)}"
                        f" [{effort_label} · {impact_label}]"
                    )
                    lines.append(
                        f"  - Owner: {md_cell(item.owner_placeholder)} | Timeframe: {md_cell(item.timeframe)}"
                    )
                lines.append("")
    else:
        # Backward-compat: no exec_content — render without effort/impact labels
        roadmap_items_raw = roadmap_raw.get("items", [])
        for phase_key in ("NOW", "NEXT", "LATER"):
            phase_items = [r for r in roadmap_items_raw if r.get("phase") == phase_key]
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
