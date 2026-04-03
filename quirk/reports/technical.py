from datetime import datetime, timezone
from typing import Dict, List


def _scan_error_category(scan_error: str) -> str:
    if not scan_error:
        return ""
    if ":" in scan_error:
        return scan_error.split(":", 1)[0].strip()
    return scan_error.strip()


def _service_detail(ep) -> str:
    detail = getattr(ep, "service_detail", "") or ""
    if detail:
        return detail
    if getattr(ep, "protocol", "") == "TLS":
        blocker = getattr(ep, "tls_blocker_reason", "") or ""
        if blocker:
            return blocker
    return getattr(ep, "tls_version", "") or ""


def build_tech_markdown(cfg, endpoints, findings) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: List[str] = []
    lines.append(f"# Technical Findings — {cfg.assessment.name}")
    lines.append("")
    lines.append(f"- **Generated:** {now}")
    lines.append("")

    # === Service Inventory ===
    inv_eps = [e for e in endpoints if getattr(e, "protocol", "") != "CLOSED"]
    if inv_eps:
        lines.append("## Service Inventory")
        lines.append("")
        lines.append("| Host | Port | Protocol | Detail |")
        lines.append("|---|---:|---|---|")
        for e in sorted(inv_eps, key=lambda x: (x.host, x.port, getattr(x, "protocol", ""))):
            lines.append(
                f"| {e.host} | {e.port} | {getattr(e, 'protocol', '') or ''} | {_service_detail(e)} |"
            )
        lines.append("")

    # === TLS Capabilities ===
    tls_eps = [e for e in endpoints if getattr(e, "protocol", "") == "TLS" and not getattr(e, "scan_error", None)]
    if tls_eps:
        lines.append("## TLS Capabilities")
        lines.append("")
        lines.append("| Host | Port | Negotiated TLS | Supported Versions | Weak Ciphers Present | Legacy Suites Present | PFS | Cipher Sample | Notes |")
        lines.append("|---|---:|---|---|---|---|---|---|---|")
        for e in sorted(tls_eps, key=lambda x: (x.host, x.port)):
            sv = getattr(e, "tls_supported_versions", "") or ""
            weak = "YES" if getattr(e, "tls_weak_ciphers_present", False) else "NO"
            legacy = "YES" if getattr(e, "tls_legacy_suites_present", False) else "NO"
            pfs = "YES" if getattr(e, "tls_pfs_supported", False) else "NO"
            sample = getattr(e, "tls_supported_ciphers_sample", "") or ""
            notes = getattr(e, "tls_enum_notes", "") or ""
            lines.append(
                f"| {e.host} | {e.port} | {getattr(e, 'tls_version', '') or ''} | {sv} | {weak} | {legacy} | {pfs} | {sample} | {notes} |"
            )
        lines.append("")

    # === TLS blockers ===
    blocker_allowed = {"MTLS_REQUIRED", "TLS_HANDSHAKE_FAILED", "TIMEOUT", "NOT_TLS_ON_PORT"}
    tls_blocked = []
    for e in endpoints:
        if getattr(e, "protocol", "") != "TLS":
            continue
        blocker = getattr(e, "tls_blocker_reason", None) or _scan_error_category(getattr(e, "scan_error", "") or "")
        if blocker in blocker_allowed:
            tls_blocked.append((e, blocker))
    if tls_blocked:
        lines.append("## TLS Blockers")
        lines.append("")
        lines.append("| Host | Port | Blocker | Scan Error |")
        lines.append("|---|---:|---|---|")
        for e, blocker in sorted(tls_blocked, key=lambda x: (x[0].host, x[0].port)):
            lines.append(
                f"| {e.host} | {e.port} | {blocker} | {getattr(e, 'scan_error', '') or ''} |"
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
