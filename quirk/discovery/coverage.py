import logging

logger = logging.getLogger(__name__)


def calculate_coverage(target_count, reachable_hosts, tls_endpoints):
    if target_count == 0:
        return 0.0

    coverage = (tls_endpoints / target_count) * 100
    # Clamp percent to [0.0, 100.0] per audit WR-01 (Phase 71): never report
    # >100% or negative coverage. The function returns a percent (0–100), not
    # a fraction — see CONTEXT D-06a (correction, 2026-05-15).
    return max(0.0, min(100.0, round(coverage, 2)))


def quantum_readiness_score(findings, endpoints):
    score = 100

    # Penalize deprecated TLS
    for f in findings:
        # Normalize severity case per audit WR-02 (Phase 71): uppercase comparison.
        # D-01: guard against missing/None severity (SCOREFIX-01).
        raw_sev = f.get("severity")
        if raw_sev is None or str(raw_sev).upper() not in (
            "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"
        ):
            logger.warning(
                "quantum_readiness_score: finding missing/invalid severity %r"
                " — treating as LOW",
                raw_sev,
            )
            raw_sev = "LOW"
        severity = str(raw_sev).upper()
        if severity == "CRITICAL":
            score -= 25
        elif severity == "HIGH":
            score -= 10
        elif severity == "MEDIUM":
            score -= 5

    # Penalize lack of discovery
    if len(endpoints) < 5:
        score -= 20

    return max(score, 0)
