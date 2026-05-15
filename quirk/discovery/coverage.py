def calculate_coverage(target_count, reachable_hosts, tls_endpoints):
    if target_count == 0:
        return 0.0

    coverage = (tls_endpoints / target_count) * 100
    # Clamp per audit WR-01 (Phase 71): never report >100% or negative coverage.
    return max(0.0, min(1.0, round(coverage, 2)))


def quantum_readiness_score(findings, endpoints):
    score = 100

    # Penalize deprecated TLS
    for f in findings:
        # Normalize severity case per audit WR-02 (Phase 71): uppercase comparison.
        severity = str(f["severity"]).upper()
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
