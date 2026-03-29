from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from quirk.assessment.readiness_score import ReadinessScore


def build_interpretation(cfg, endpoints, findings, score: ReadinessScore) -> Dict[str, Any]:
    """
    Produces human-friendly narrative blocks for executive reporting.
    """
    sev_counts = Counter([f.get("severity", "UNKNOWN") for f in findings])

    coverage = score.breakdown.coverage
    proto_counts = coverage.get("protocol_counts", {})
    err_cats = coverage.get("error_categories", {})

    bullets: List[str] = []

    # Score framing
    bullets.append(f"Quantum Readiness Score is **{score.score}/100** (**{score.rating}**).")

    # Drivers (top 3)
    if score.breakdown.drivers:
        top = score.breakdown.drivers[:3]
        drivers_txt = "; ".join([f"{name} (-{pts})" for name, pts in top])
        bullets.append(f"Top score drivers: {drivers_txt}.")

    # Visibility framing
    tls_ok = coverage.get("tls_success", 0)
    ssh_ok = coverage.get("ssh_success", 0)
    if tls_ok + ssh_ok == 0:
        bullets.append("No successful deep TLS/SSH handshakes were captured in this run; expand visibility (scope, segmentation allowances, and ports) to improve confidence.")
    else:
        bullets.append(f"Successfully profiled **{tls_ok} TLS** and **{ssh_ok} SSH** endpoints in scope for cryptographic posture.")

    # Coverage notes
    timeout = err_cats.get("TIMEOUT", 0)
    not_tls = err_cats.get("NOT_TLS_ON_PORT", 0)
    if timeout:
        bullets.append(f"Observed **{timeout} TIMEOUT** events, commonly indicating filtering/segmentation or unreachable hosts during scan.")
    if not_tls:
        bullets.append(f"Observed **{not_tls} NOT_TLS_ON_PORT** events, indicating services on TLS-like ports that do not speak TLS (common with device management interfaces).")

    # Severity framing (exec relevant)
    hi_crit = sev_counts.get("CRITICAL", 0) + sev_counts.get("HIGH", 0)
    bullets.append(f"High-impact items (CRITICAL+HIGH): **{hi_crit}**. Near-term hygiene accelerates crypto agility and reduces baseline risk.")

    return {
        "bullets": bullets,
        "proto_counts": proto_counts,
        "error_categories": err_cats,
        "severity_counts": dict(sev_counts),
    }

