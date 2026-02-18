from collections import Counter, defaultdict
from typing import Dict, List, Tuple


def _parse_error_category(desc: str) -> str:
    """
    We store errors like:
      'TIMEOUT: ...'
      'NOT_TLS_ON_PORT: ...'
      'TLS_ERROR: ...'
      'CLOSED: Timeout (filtered or host down)'
    Return the leading category token if present.
    """
    if not desc:
        return "UNKNOWN_ERROR"

    # Common pattern: "CATEGORY: details"
    if ":" in desc:
        head = desc.split(":", 1)[0].strip()
        # Keep categories short + consistent
        if 2 <= len(head) <= 40 and " " not in head:
            return head

    # Fallback if no "CATEGORY:" pattern
    return "UNCLASSIFIED"


def _top_items(counter: Counter, n: int = 10) -> List[Tuple[str, int]]:
    return counter.most_common(n)


def build_tech_markdown(cfg, endpoints, findings) -> str:
    lines: List[str] = []

    lines.append(f"# Technical Findings — {cfg.assessment.name}")
    lines.append("")

    # ==============================
    # SUMMARY
    # ==============================
    sev_counts = Counter([f.get("severity", "UNKNOWN") for f in findings])
    total_findings = len(findings)

    lines.append("## Summary")
    lines.append(f"- **Total findings:** {total_findings}")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        lines.append(f"- **{sev}:** {sev_counts.get(sev, 0)}")
    lines.append("")

    # ==============================
    # SCAN ERROR BREAKDOWN (POLISH)
    # ==============================
    info_scan_errors = [
        f for f in findings
        if f.get("severity") == "INFO" and f.get("title") == "Scan error"
    ]

    if info_scan_errors:
        cat_counts = Counter()
        host_counts = Counter()
        port_counts = Counter()

        for f in info_scan_errors:
            cat = _parse_error_category(f.get("description", ""))
            cat_counts[cat] += 1
            host_counts[f.get("host", "unknown")] += 1
            port_counts[str(f.get("port", "unknown"))] += 1

        lines.append("## Scan Error Breakdown (INFO)")
        lines.append("")
        lines.append("### By Category")
        lines.append("| Category | Count | Notes |")
        lines.append("|---|---:|---|")

        # Add short notes to the common categories
        notes_map: Dict[str, str] = {
            "TIMEOUT": "Filtered/firewalled, host down, or silent drop.",
            "CONNECTION_REFUSED": "Port closed or actively refused.",
            "NOT_TLS_ON_PORT": "Service is likely not TLS on that port (HTTP/proprietary).",
            "TLS_HANDSHAKE_FAILURE": "TLS present but handshake failed (policy/mTLS/old stack).",
            "RESET_BY_PEER": "Service reset connection (rate-limit, IPS, policy).",
            "TLS_ERROR": "Generic TLS failure; review raw message in findings JSON.",
            "CLOSED": "Fingerprinter marked as closed/filtered; see detail.",
            "SSH_ERROR": "SSH probe failed; validate SSH exposure/controls.",
            "UNCLASSIFIED": "No category prefix; improve categorization if frequent.",
            "UNKNOWN_ERROR": "Missing description text.",
        }

        for cat, cnt in _top_items(cat_counts, n=50):
            note = notes_map.get(cat, "")
            lines.append(f"| {cat} | {cnt} | {note} |")

        lines.append("")
        lines.append("### Top Hosts Generating Scan Errors")
        lines.append("| Host | Count |")
        lines.append("|---|---:|")
        for host, cnt in _top_items(host_counts, n=15):
            lines.append(f"| {host} | {cnt} |")

        lines.append("")
        lines.append("### Top Ports Generating Scan Errors")
        lines.append("| Port | Count |")
        lines.append("|---|---:|")
        for port, cnt in _top_items(port_counts, n=15):
            lines.append(f"| {port} | {cnt} |")

        lines.append("")
        lines.append("**Interpretation tips:**")
        lines.append("- A high count of `NOT_TLS_ON_PORT` often indicates management UIs speaking HTTP/proprietary protocols on common TLS ports (8443/5001/etc).")
        lines.append("- A high count of `TIMEOUT` often indicates segmentation or firewall filtering — useful for coverage/assurance reporting.")
        lines.append("- `TLS_HANDSHAKE_FAILURE` can indicate mTLS requirements, incompatible versions/ciphers, or policy enforcement devices.")
        lines.append("")

    # ==============================
    # FINDINGS TABLE
    # ==============================
    lines.append("## Findings Table")
    lines.append("| Severity | Host | Port | Title | Recommendation |")
    lines.append("|---|---:|---:|---|---|")
    for f in findings[:500]:
        lines.append(
            f"| {f.get('severity','')} | {f.get('host','')} | {f.get('port','')} | "
            f"{f.get('title','')} | {f.get('recommendation','')} |"
        )

    lines.append("")
    lines.append("## Endpoint Inventory (sample)")
    lines.append("| Protocol | Host | Port | Version/Banner | Cipher | PubKey | KeySize | SigAlg | NotAfter | Error |")
    lines.append("|---|---|---:|---|---|---|---:|---|---|---|")

    for e in endpoints[:300]:
        # For SSH and UNKNOWN/HTTP, we reuse tls_version as banner/status/detail.
        lines.append(
            f"| {getattr(e,'protocol','') or ''} | {getattr(e,'host','') or ''} | {getattr(e,'port','') or ''} | "
            f"{getattr(e,'tls_version','') or ''} | {getattr(e,'cipher_suite','') or ''} | "
            f"{getattr(e,'cert_pubkey_alg','') or ''} | {getattr(e,'cert_pubkey_size','') or ''} | "
            f"{getattr(e,'cert_sig_alg','') or ''} | {getattr(e,'cert_not_after','') or ''} | "
            f"{getattr(e,'scan_error','') or ''} |"
        )

    lines.append("")
    return "\n".join(lines)
