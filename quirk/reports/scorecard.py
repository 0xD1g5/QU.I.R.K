from datetime import datetime, timezone
from typing import Any, Dict, List

from quirk.intelligence.confidence import compute_confidence
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.roadmap import build_phased_roadmap
from quirk.intelligence.scoring import compute_readiness_score


def _impact_text(points: int) -> str:
    if points > 0:
        return f"+{points}"
    return str(points)


def _interpretation_bullets(
    evidence: Dict[str, Any],
    score: Dict[str, Any],
    confidence: Dict[str, Any],
) -> List[str]:
    bullets: List[str] = []

    bullets.append(
        f"Readiness is **{score.get('rating', 'UNKNOWN')}** at "
        f"**{score.get('score', 0)}/100**."
    )
    bullets.append(
        f"Confidence is **{confidence.get('confidence_rating', 'UNKNOWN')}** at "
        f"**{confidence.get('confidence_score', 0)}/100**."
    )

    sev = evidence.get("finding_severity_counts", {})
    high_impact = int(sev.get("CRITICAL", 0) or 0) + int(sev.get("HIGH", 0) or 0)
    if high_impact > 0:
        bullets.append(f"High-impact findings (CRITICAL+HIGH): **{high_impact}**.")
    else:
        bullets.append("No CRITICAL or HIGH findings were observed in this run.")

    plaintext_http = int(evidence.get("plaintext_http_count", 0) or 0)
    http_on_tls = int(evidence.get("http_on_tls_port_count", 0) or 0)
    if plaintext_http + http_on_tls > 0:
        bullets.append(
            "Plaintext HTTP risk remains: "
            f"{plaintext_http} plaintext HTTP and {http_on_tls} HTTP-on-TLS-port "
            "endpoint(s)."
        )

    return bullets


def build_scorecard_markdown(cfg, endpoints, findings) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    evidence = build_evidence_summary(endpoints, findings)
    score = compute_readiness_score(evidence)
    confidence = compute_confidence(evidence)
    roadmap = build_phased_roadmap(evidence, score)

    drivers = list(score.get("drivers", []))[:5]
    now_actions = [
        item for item in roadmap.get("items", []) if item.get("phase") == "NOW"
    ][:3]

    lines: List[str] = []
    lines.append(f"# Scorecard — {cfg.assessment.name}")
    lines.append("")
    lines.append("## Snapshot")
    lines.append(f"- **Generated:** {now}")
    lines.append(
        f"- **Readiness Score:** **{score.get('score', 0)}/100** "
        f"({score.get('rating', 'UNKNOWN')})"
    )
    lines.append(
        f"- **Confidence:** **{confidence.get('confidence_score', 0)}/100** "
        f"({confidence.get('confidence_rating', 'UNKNOWN')})"
    )
    lines.append("")

    lines.append("## Interpretation")
    for bullet in _interpretation_bullets(evidence, score, confidence):
        lines.append(f"- {bullet}")
    lines.append("")

    lines.append("## Top Drivers (5)")
    if drivers:
        lines.append("| Driver | Impact |")
        lines.append("|---|---:|")
        for driver in drivers:
            reason = driver.get("reason", "")
            points = int(driver.get("points", 0) or 0)
            lines.append(f"| {reason} | {_impact_text(points)} |")
    else:
        lines.append("- Not found.")
    lines.append("")

    lines.append("## NOW Actions (Top 3)")
    for idx in range(1, 4):
        action = now_actions[idx - 1] if idx <= len(now_actions) else None
        if action:
            lines.append(
                f"{idx}. **{action.get('title', 'Untitled action')}** "
                f"({action.get('timeframe', 'timeframe not set')})"
            )
            lines.append(f"   - Why: {action.get('why', '')}")
            lines.append(
                f"   - Owner: {action.get('owner_placeholder', '[owner: TBD]')}"
            )
        else:
            lines.append(f"{idx}. Not found in roadmap.")
    lines.append("")

    return "\n".join(lines)
