def calculate_coverage(target_count, reachable_hosts, tls_endpoints):
    if target_count == 0:
        return 0

    coverage = (tls_endpoints / target_count) * 100
    return round(coverage, 2)


def quantum_readiness_score(findings, endpoints):
    score = 100

    # Penalize deprecated TLS
    for f in findings:
        if f["severity"] == "CRITICAL":
            score -= 25
        elif f["severity"] == "HIGH":
            score -= 10
        elif f["severity"] == "MEDIUM":
            score -= 5

    # Penalize lack of discovery
    if len(endpoints) < 5:
        score -= 20

    return max(score, 0)
