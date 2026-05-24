from datetime import datetime, timezone
from typing import Dict, List

from quirk.reports._md_escape import md_cell
# Phase 81 / CMVP-06: shared Algorithm Inventory builder. The HTML helper consumes
# coverage_for_algorithm lazily so this module remains import-safe even before
# Plan 81-02 lands quirk/compliance/cmvp.py.
from quirk.reports.html_renderer import build_algorithm_inventory
from quirk.reports.content_model import FALLBACK_QUANTUM_RISK

# Phase 99 CTX-01: fallback for findings with no quantum_risk field.
# Imported from the shared content model (single source of truth).
FALLBACK_QR = FALLBACK_QUANTUM_RISK


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
                f"| {md_cell(e.host)} | {e.port} | {md_cell(getattr(e, 'protocol', '') or '')} | {md_cell(_service_detail(e))} |"
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
                f"| {md_cell(e.host)} | {e.port} | {md_cell(getattr(e, 'tls_version', '') or '')} | {md_cell(sv)} | {weak} | {legacy} | {pfs} | {md_cell(sample)} | {md_cell(notes)} |"
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
                f"| {md_cell(e.host)} | {e.port} | {md_cell(blocker)} | {md_cell(getattr(e, 'scan_error', '') or '')} |"
            )
        lines.append("")

    # === Algorithm Inventory (Phase 81 / CMVP-06) ===
    # Adds a CMVP Coverage column populated via build_algorithm_inventory, which
    # delegates to quirk.compliance.cmvp.coverage_for_algorithm (lazy import).
    # Empty matches render the literal "Not in CMVP catalog" (v4.10-D-01 invariant —
    # do not introduce alternative wording).
    algorithms = build_algorithm_inventory(endpoints or [])
    if algorithms:
        lines.append("## Algorithm Inventory (FIPS 140-3 Coverage)")
        lines.append("")
        lines.append("| Algorithm | NIST Level | FIPS Status | CMVP Coverage |")
        lines.append("|---|---|---|---|")
        for a in algorithms:
            cov = a.get("cmvp_coverage")
            cov_cell = md_cell(cov) if cov else "Not in CMVP catalog"
            lines.append(
                f"| {md_cell(a['name'])} | {a['nist_level']} | {md_cell(a['fips_status'])} | {cov_cell} |"
            )
        lines.append("")

    # === Findings table ===
    lines.append("## Findings")
    lines.append("")
    # Phase 99 CTX-01: Quantum Risk column added after Recommendation per UI-SPEC
    # §Interaction Contract (WR-01 fix: Quantum Risk is the 7th column, after Recommendation).
    lines.append("| Severity | Host | Port | Title | Description | Recommendation | Quantum Risk |")
    lines.append("|---|---|---:|---|---|---|---|")
    for f in findings:
        sev = f.get("severity", "INFO")
        host = f.get("host", "")
        port = f.get("port", "")
        title = f.get("title", "")
        desc = f.get("description", "")
        rec = f.get("recommendation", "")
        # Phase 99 CTX-01: read quantum_risk; fall back to FALLBACK_QR, truncate to 120.
        qr = (f.get("quantum_risk") or FALLBACK_QR)[:120]
        lines.append(
            f"| {sev} | {md_cell(host)} | {port} | {md_cell(title)} | {md_cell(desc)} | {md_cell(rec)} | {md_cell(qr)} |"
        )

    lines.append("")
    return "\n".join(lines)
