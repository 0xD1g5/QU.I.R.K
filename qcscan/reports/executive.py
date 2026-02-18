from collections import Counter
from datetime import datetime
from typing import Dict, List

from qcscan.assessment.readiness_score import compute_readiness_score
from qcscan.assessment.transition_planner import build_transition_roadmap
from qcscan.assessment.migration_advisor import recommend_migration_paths
from qcscan.assessment.interpretation_engine import build_interpretation


def _count_noninfo(findings: List[Dict]) -> Counter:
    return Counter([f["severity"] for f in findings if f.get("severity") != "INFO"])


def build_exec_markdown(cfg, endpoints, findings) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # v3.5 assessment brain outputs
    score = compute_readiness_score(cfg, endpoints, findings)
    roadmap = build_transition_roadmap(cfg, endpoints, findings)
    recs = recommend_migration_paths(findings)
    interp = build_interpretation(cfg, endpoints, findings, score)

    # Findings overview (excluding INFO)
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

    # Score headline
    lines.append("## Quantum Readiness Score")
    lines.append(f"**Score:** **{score.score}/100**  \n**Rating:** **{score.rating}**")
    lines.append("")
    lines.append("### Score Breakdown (drivers)")
    if score.breakdown.drivers:
        for label, pts in score.breakdown.drivers:
            lines.append(f"- {label} (**-{pts}**)")

    lines.append("")
    lines.append("## Discovery and Coverage")
    lines.append(f"- **TLS endpoints successfully scanned:** {tls_ok}")
    lines.append(f"- **SSH endpoints successfully scanned:** {ssh_ok}")
    lines.append(f"- **Plaintext HTTP services detected:** {http_plain}")
    lines.append(f"- **Unknown open services detected:** {unknown_open}")
    lines.append("")

    # Findings overview (exec relevant)
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

    # Migration guidance (top actionable recs)
    if recs:
        lines.append("")
        lines.append("## Recommended Migration Paths (Top Items)")
        # show first 10 (sorted by severity-ish order already in findings)
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
