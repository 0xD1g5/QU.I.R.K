from collections import Counter
from datetime import datetime
from typing import Dict, List

from quirk.assessment.readiness_score import compute_readiness_score
from quirk.assessment.transition_planner import build_transition_roadmap
from quirk.assessment.migration_advisor import recommend_migration_paths
from quirk.assessment.interpretation_engine import build_interpretation
from quirk.assessment.confidence import compute_confidence


def _count_noninfo(findings: List[Dict]) -> Counter:
    return Counter([f["severity"] for f in findings if f.get("severity") != "INFO"])


def build_exec_markdown(cfg, endpoints, findings) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    score = compute_readiness_score(cfg, endpoints, findings)
    roadmap = build_transition_roadmap(cfg, endpoints, findings)
    recs = recommend_migration_paths(findings)
    interp = build_interpretation(cfg, endpoints, findings, score)
    conf = compute_confidence(cfg, endpoints)

    sev_counts = _count_noninfo(findings)
    high_crit = sev_counts.get("HIGH", 0) + sev_counts.get("CRITICAL", 0)

    tls_ok = score.breakdown.coverage.get("tls_success", 0)
    ssh_ok = score.breakdown.coverage.get("ssh_success", 0)
    http_plain = score.breakdown.coverage.get("http_plain", 0)
    unknown_open = score.breakdown.coverage.get("unknown_open", 0)

    lines: List[str] = []
    lines.append(f"# {cfg.assessment.name}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"- **Generated:** {now}")
    lines.append(f"- **Owner:** {cfg.assessment.report_owner}")
    lines.append(f"- **Data classification:** {cfg.assessment.data_classification}")
    lines.append("")

    lines.append("## Quantum Readiness Score")
    lines.append(f"**Score:** **{score.score}/100**  \n**Rating:** **{score.rating}**")
    lines.append("")
    lines.append("### Score Drivers (Top)")
    if score.breakdown.drivers:
        for label, pts in score.breakdown.drivers[:8]:
            lines.append(f"- {label} (**-{pts}**)")

    lines.append("")
    lines.append("## Confidence & Coverage (v3.7)")
    lines.append(f"- **Confidence:** **{conf.get('confidence_rating')}** ({conf.get('confidence_score')}/100)")
    lines.append(f"- **Coverage:** {conf.get('coverage_pct')}% (TLS+SSH successful / total in-scope endpoints)")
    lines.append(f"- **TLS Enumeration Coverage:** {conf.get('tls_enum_coverage_pct')}% (TLS-success endpoints with capabilities captured)")
    blockers = conf.get("blockers_top") or []
    if blockers:
        lines.append("- **Top visibility blockers:**")
        for b in blockers[:5]:
            lines.append(f"  - {b.get('category')}: {b.get('count')}")

    lines.append("")
    lines.append("## Discovery and Coverage")
    lines.append(f"- **TLS endpoints successfully scanned:** {tls_ok}")
    lines.append(f"- **SSH endpoints successfully scanned:** {ssh_ok}")
    lines.append(f"- **Plaintext HTTP services detected:** {http_plain}")
    lines.append(f"- **Unknown open services detected:** {unknown_open}")
    lines.append("")

    lines.append("## Findings Overview (Executive-Relevant)")
    lines.append(f"- **High-impact items (CRITICAL + HIGH):** {high_crit}")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        lines.append(f"- **{sev}:** {sev_counts.get(sev, 0)}")

    lines.append("")
    lines.append("## Interpretation")
    for b in interp.get("bullets", []):
        lines.append(f"- {b}")

    lines.append("")
    lines.append("## Transition Roadmap")
    lines.append("")
    lines.append("### Wave 1 — Hygiene (0–6 months)")
    for item in roadmap.wave_1:
        lines.append(f"- **{item.title}** — {item.rationale}")
        lines.append(f"  - Deliverable: {item.deliverable}")
        lines.append(f"  - Owner: {item.owner_hint} | Effort: {item.effort}")

    lines.append("")
    lines.append("### Wave 2 — Modernization (6–24 months)")
    for item in roadmap.wave_2:
        lines.append(f"- **{item.title}** — {item.rationale}")
        lines.append(f"  - Deliverable: {item.deliverable}")
        lines.append(f"  - Owner: {item.owner_hint} | Effort: {item.effort}")

    lines.append("")
    lines.append("### Wave 3 — PQC Preparation (24+ months)")
    for item in roadmap.wave_3:
        lines.append(f"- **{item.title}** — {item.rationale}")
        lines.append(f"  - Deliverable: {item.deliverable}")
        lines.append(f"  - Owner: {item.owner_hint} | Effort: {item.effort}")

    if recs:
        lines.append("")
        lines.append("## Recommended Migration Paths (Top Items)")
        shown = 0
        for r in recs:
            if shown >= 10:
                break
            lines.append(f"- **{r.get('path')}** — {r.get('recommendation')}")
            if r.get("host") and r.get("port") is not None:
                lines.append(f"  - Target: {r.get('host')}:{r.get('port')} | Severity: {r.get('severity')}")
            shown += 1

    lines.append("")
    lines.append("## Recommended Next Actions (30–60 days)")
    lines.append("1. Confirm ownership for TLS termination points and certificate authorities (internal and cloud).")
    lines.append("2. Establish certificate lifecycle automation and renewal SLAs; address near-term expirations.")
    lines.append("3. Launch crypto-agility baselining (standard TLS patterns, dependency mapping, upgrade paths).")
    lines.append("4. Identify 2–3 pilot candidates for PQC/hybrid readiness planning and vendor capability mapping.")
    lines.append("")

    return "\n".join(lines)
