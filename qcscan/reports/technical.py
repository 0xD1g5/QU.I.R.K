from datetime import datetime
from typing import Dict, List


def build_tech_markdown(cfg, endpoints, findings) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    lines: List[str] = []
    lines.append(f"# Technical Findings — {cfg.assessment.name}")
    lines.append("")
    lines.append(f"- **Generated:** {now}")
    lines.append("")

    # === TLS Capabilities (v3.6) ===
    tls_eps = [e for e in endpoints if getattr(e, "protocol", "") == "TLS" and not getattr(e, "scan_error", None)]
    if tls_eps:
        lines.append("## TLS Capabilities (v3.6)")
        lines.append("")
        lines.append("| Host | Port | Negotiated TLS | Supported Versions | Weak Ciphers | PFS | Cipher Sample | Notes |")
        lines.append("|---|---:|---|---|---|---|---|---|")
        for e in sorted(tls_eps, key=lambda x: (x.host, x.port)):
            sv = getattr(e, "tls_supported_versions", "") or ""
            weak = "YES" if getattr(e, "tls_weak_ciphers_present", False) else "NO"
            pfs = "YES" if getattr(e, "tls_pfs_supported", False) else "NO"
            sample = getattr(e, "tls_supported_ciphers_sample", "") or ""
            notes = getattr(e, "tls_enum_notes", "") or ""
            lines.append(
                f"| {e.host} | {e.port} | {getattr(e, 'tls_version', '') or ''} | {sv} | {weak} | {pfs} | {sample} | {notes} |"
            )
        lines.append("")

    # === Findings table ===
    lines.append("## Findings")
    lines.append("")
    lines.append("| Severity | Host | Port | Title | Recommendation |")
    lines.append("|---|---|---:|---|---|")
    for f in findings:
        sev = f.get("severity", "INFO")
        host = f.get("host", "")
        port = f.get("port", "")
        title = f.get("title", "")
        rec = f.get("recommendation", "")
        lines.append(f"| {sev} | {host} | {port} | {title} | {rec} |")

    lines.append("")
    return "\n".join(lines)
