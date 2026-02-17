from collections import Counter
from datetime import datetime
from typing import Dict, List


def _parse_error_category(desc: str) -> str:
    """
    Errors typically look like:
      'TIMEOUT: ...'
      'NOT_TLS_ON_PORT: ...'
      'CONNECTION_REFUSED: ...'
      'CLOSED: ...'
    Return leading token if present.
    """
    if not desc:
        return "UNKNOWN_ERROR"

    if ":" in desc:
        head = desc.split(":", 1)[0].strip()
        if 2 <= len(head) <= 40 and " " not in head:
            return head

    return "UNCLASSIFIED"


def _count_noninfo(findings: List[Dict]) -> Counter:
    # Exec counts exclude INFO
    return Counter([f["severity"] for f in findings if f.get("severity") != "INFO"])


def _count_info_scan_errors(findings: List[Dict]) -> Counter:
    # Only INFO scan errors
    cats = []
    for f in findings:
        if f.get("severity") == "INFO" and f.get("title") == "Scan error":
            cats.append(_parse_error_category(f.get("description", "")))
    return Counter(cats)


def build_exec_markdown(cfg, endpoints, findings) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Endpoint stats
    attempted = len(endpoints)

    # What counts as "identified services"?
    # Anything not CLOSED, and not a pure scan_error-only record.
    identified = [
        e for e in endpoints
        if (getattr(e, "protocol", None) not in ("CLOSED", None))
    ]

    tls_ok = [e for e in endpoints if getattr(e, "protocol", "") == "TLS" and not getattr(e, "scan_error", None)]
    ssh_ok = [e for e in endpoints if getattr(e, "protocol", "") == "SSH" and not getattr(e, "scan_error", None)]
    http_plain = [e for e in endpoints if getattr(e, "protocol", "") == "HTTP"]
    unknown_open = [e for e in endpoints if getattr(e, "protocol", "") == "UNKNOWN"]

    # Findings overview (excluding INFO)
    sev_counts = _count_noninfo(findings)

    # INFO scan error categories (coverage / filtering story)
    info_error_counts = _count_info_scan_errors(findings)

    # Quick “themes” for execs
    theme_counts = Counter()
    for f in findings:
        if f.get("severity") == "INFO":
            continue
        title = (f.get("title") or "").strip()
        if title:
            theme_counts[title] += 1

    top_themes = theme_counts.most_common(5)

    # Risk posture: simple messaging
    high_crit = sev_counts.get("HIGH", 0) + sev_counts.get("CRITICAL", 0)

    lines: List[str] = []
    lines.append(f"# {cfg.assessment.name}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"- **Generated:** {now}")
    lines.append(f"- **Owner:** {cfg.assessment.report_owner}")
    lines.append(f"- **Data classification:** {cfg.assessment.data_classification}")
    lines.append("")

    # ------------------------------
    # Discovery / Coverage
    # ------------------------------
    lines.append("## Discovery and Coverage")
    lines.append(f"- **Total endpoints attempted:** {attempted}")
    lines.append(f"- **Services identified (protocol fingerprinted):** {len(identified)}")
    lines.append(f"- **TLS endpoints successfully scanned:** {len(tls_ok)}")
    lines.append(f"- **SSH endpoints detected:** {len(ssh_ok)}")
    lines.append(f"- **Plaintext HTTP services detected:** {len(http_plain)}")
    lines.append(f"- **Unknown open services detected:** {len(unknown_open)}")

    if info_error_counts:
        # Highlight the “why didn’t we scan everything?” story
        timeout = info_error_counts.get("TIMEOUT", 0)
        refused = info_error_counts.get("CONNECTION_REFUSED", 0)
        not_tls = info_error_counts.get("NOT_TLS_ON_PORT", 0)
        closed = info_error_counts.get("CLOSED", 0)

        lines.append("")
        lines.append("### Coverage Notes (why some targets did not yield TLS data)")
        if timeout:
            lines.append(f"- **TIMEOUT:** {timeout} (often filtering/segmentation, host down, or silent drops)")
        if refused:
            lines.append(f"- **CONNECTION_REFUSED:** {refused} (port closed or actively refused)")
        if not_tls:
            lines.append(f"- **NOT_TLS_ON_PORT:** {not_tls} (service likely not TLS on that port)")
        if closed:
            lines.append(f"- **CLOSED/UNREACHABLE:** {closed} (not reachable during scan)")

    lines.append("")
    # ------------------------------
    # Findings overview (no INFO)
    # ------------------------------
    lines.append("## Findings Overview (Executive-Relevant)")
    lines.append(f"- **High-impact items (CRITICAL + HIGH):** {high_crit}")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        lines.append(f"- **{sev}:** {sev_counts.get(sev, 0)}")

    lines.append("")
    lines.append("## Key Takeaways")
    lines.append("- Most environments rely on classical public-key cryptography (RSA/ECDSA/EdDSA), which remains secure today but requires **post-quantum transition planning**.")
    lines.append("- The highest priority is identifying long-lived sensitive data flows and trust anchors (PKI roots/intermediates, identity, and signing workflows).")
    lines.append("- Near-term hygiene (deprecated protocols, expiring certs, unmanaged endpoints) reduces current risk and accelerates crypto agility.")

    # ------------------------------
    # Top themes
    # ------------------------------
    if top_themes:
        lines.append("")
        lines.append("## Top Risk Themes")
        for title, cnt in top_themes:
            lines.append(f"- **{title}:** {cnt}")

    lines.append("")
    lines.append("## Recommended Next Actions (30–60 days)")
    lines.append("1. Confirm ownership for all TLS termination points and certificate authorities (internal and cloud).")
    lines.append("2. Establish certificate lifecycle automation and renewal SLAs; address near-term expirations.")
    lines.append("3. Launch a crypto-agility workstream (standard TLS patterns, upgrade baselines, dependency mapping).")
    lines.append("4. Build a PQC transition roadmap: vendor readiness, pilot candidates, and migration waves (Now / Next / Later).")
    lines.append("")

    return "\n".join(lines)
