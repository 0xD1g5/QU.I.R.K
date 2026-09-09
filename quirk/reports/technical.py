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


# Phase 161 HWLC-19: locked advisory caption — must be byte-identical across
# HTML, DOCX, CLI and the dashboard (note the em dash, U+2014).
VENDOR_TREND_ADVISORY_CAPTION = "Advisory — vendor PQC status trends do not affect the readiness score."

# Phase 181 SURF-02: locked advisory caption for the Remediation Burndown
# section — byte-identical to html_renderer.BURNDOWN_ADVISORY_CAPTION and
# docx_renderer._BURNDOWN_ADVISORY_CAPTION. Per-renderer duplication is the
# established Phase 161 convention (see VENDOR_TREND_ADVISORY_CAPTION above),
# NOT a shared constant in content_model.py — a parity test
# (test_advisory_caption_is_identical_across_all_three_surfaces) fails loudly
# if the three surfaces ever drift apart.
BURNDOWN_ADVISORY_CAPTION = "Advisory - remediation burndown does not affect the readiness score."

# Phase 181 SURF-02 / D-35/D-36: fixed bucket iteration order so per-deadline
# sections are stable and `unmapped` is always rendered last, never omitted.
_BURNDOWN_BUCKET_ORDER = ("key_establishment", "digital_signature", "unmapped")

# Phase 191 Plan 04 (SPKI-02) / D-01: locked advisory caption for the Key
# Reuse section — must be reproduced byte-identically in html_renderer.py
# and docx_renderer.py by plan 191-05. Per-renderer duplication is the
# established Phase 161 convention (see VENDOR_TREND_ADVISORY_CAPTION
# above), NOT a shared constant in content_model.py.
KEY_REUSE_ADVISORY_CAPTION = "Advisory - key reuse does not affect the readiness score."

# Phase 161 HWLC-19: human-readable labels for VendorPqcTrendEvent.event_type
# values. Unknown/future event types fall back to the raw value unchanged.
_VENDOR_TREND_EVENT_TYPE_LABELS: Dict[str, str] = {"pqc_status_change": "PQC status change"}


def build_tech_markdown(
    cfg,
    endpoints,
    findings,
    *,
    vendor_pqc_trends: List[dict] | None = None,
    burndown: dict | None = None,
    closure_refusal: dict | None = None,
    scan_completed_at: "datetime | None" = None,
    key_reuse: dict | None = None,
    coverage: dict | None = None,
) -> str:
    """Build the CLI technical-findings markdown report.

    Phase 161 HWLC-19: `vendor_pqc_trends` is the first hardware-related
    content of any kind in this report — a keyword-only, `None`-defaulted
    parameter so every pre-existing three-positional-argument call site and
    test keeps working unmodified. Per D-09, device-level drift / EOL
    forecast backfill into this report is explicitly out of scope.

    Phase 181 SURF-02: `burndown` and `closure_refusal` are likewise
    keyword-only, `None`-defaulted parameters carrying the Plan 181-05
    ExecContent payload — every pre-existing call site keeps working
    unmodified.

    Phase 191 Plan 04 (SPKI-02): `key_reuse` is likewise a keyword-only,
    `None`-defaulted parameter. Unlike the sections above, the Key Reuse
    section is never gated on truthiness of the whole payload — it always
    renders (D-06), including when `key_reuse` is `None` or `{}` (loader
    failed or not wired).

    Phase 192 Plan 07 (OBS-02): `coverage` is likewise a keyword-only,
    `None`-defaulted parameter carrying `quirk.reports.coverage.load_scan_coverage()`'s
    payload. Like `key_reuse`, it is never gated on truthiness of the whole
    payload — the Scan Coverage section always renders, including when
    `coverage` is `None` or `{}`, so a pre-v5.21 scan (no recorded rows)
    produces an honest absence notice rather than a missing section (D-15).

    SCORE-03 / D-16b (Phase 184.3): `scan_completed_at` is the naive-UTC
    scan instant (from `CryptoEndpoint.scanned_at`, derived once in
    writer.py), rendered as a `Scan completed:` line distinct from the
    pre-existing `Generated:` (report-build) line. Formatted via
    `quirk.reports.writer.format_scan_completed_at`, which renders the
    shared unknown marker rather than ever falling back to the render time.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    # Local import to avoid a circular import (writer.py imports this module
    # at module load time).
    from quirk.reports.writer import format_scan_completed_at

    lines: List[str] = []
    lines.append(f"# Technical Findings — {cfg.assessment.name}")
    lines.append("")
    lines.append(f"- **Generated:** {now}")
    lines.append(f"- **Scan completed:** {format_scan_completed_at(scan_completed_at)}")
    lines.append("")

    # === Scan Coverage (Phase 192 Plan 07 / OBS-02, D-13/D-15) ===
    # D-13: this section is the first content section, before any findings —
    # a reader should learn what the findings do not cover before reading
    # them. Unconditional heading (never gated on truthiness of `coverage`);
    # only the body varies. Distinct from the pre-existing per-endpoint
    # "Confidence & Coverage" / "Discovery and Coverage" sections elsewhere
    # in this report suite — this section answers "which scanner phases ran
    # at all", not "how much of what we scanned did we get data for".
    from quirk.reports.coverage import COVERAGE_NOT_RECORDED_NOTICE, PHASE_LABELS

    _coverage = coverage or {}
    lines.append("## Scan Coverage")
    lines.append("")
    if not _coverage.get("recorded"):
        lines.append(COVERAGE_NOT_RECORDED_NOTICE)
        lines.append("")
    else:
        lines.append(f"**{_coverage.get('ran', 0)} ran / {_coverage.get('skipped', 0)} skipped**")
        lines.append("")
        lines.append("| Phase | Status | Detail |")
        lines.append("|---|---|---|")
        for entry in _coverage.get("phases") or []:
            label = entry.get("label") or PHASE_LABELS.get(entry.get("phase_name", ""), entry.get("phase_name", ""))
            status = entry.get("status", "")
            if status == "ran":
                detail = f"{entry.get('duration_sec')}s" if entry.get("duration_sec") is not None else ""
            else:
                reason = entry.get("reason") or ""
                detail_text = entry.get("detail") or ""
                detail = f"{reason} — {detail_text}" if detail_text else reason
            lines.append(f"| {md_cell(label)} | {md_cell(status)} | {md_cell(detail)} |")
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

    # === TLS Capabilities (D-14 / Phase 192 Plan 08: renderer-side skip note) ===
    from quirk.reports.coverage import format_skip_note, get_phase_entry

    tls_eps = [e for e in endpoints if getattr(e, "protocol", "") == "TLS" and not getattr(e, "scan_error", None)]
    _tls_skip_entry = get_phase_entry(_coverage, "tls_scanning")
    _tls_skipped = _tls_skip_entry is not None and _tls_skip_entry.get("status") == "skipped"
    if tls_eps or _tls_skipped:
        lines.append("## TLS Capabilities")
        lines.append("")
        if not tls_eps and _tls_skipped:
            # D-14: the phase was skipped, not merely empty — say so instead of
            # rendering an empty table or omitting the heading entirely.
            lines.append(format_skip_note(_tls_skip_entry))
            lines.append("")
        else:
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
    # Phase 99 CTX-01: Quantum Risk column placed between Description and Recommendation
    # per UI-SPEC CLI-markdown contract (§Scope point 2, §Interaction table: the markdown
    # surface places Quantum Risk between Description and Recommendation — distinct from the
    # HTML "All Findings" table, which puts it 7th after Recommendation).
    lines.append("| Severity | Host | Port | Title | Description | Quantum Risk | Recommendation |")
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
            f"| {sev} | {md_cell(host)} | {port} | {md_cell(title)} | {md_cell(desc)} | {md_cell(qr)} | {md_cell(rec)} |"
        )

    lines.append("")

    # === Vendor PQC Status Trends (Phase 161 HWLC-19) ===
    # Advisory-only, vendor-scoped — mirrors the gating idiom of every other
    # section: `if <list>:` prevents an orphan heading when there is no data.
    if vendor_pqc_trends:
        lines.append("## Vendor PQC Status Trends")
        lines.append("")
        lines.append(f"_{VENDOR_TREND_ADVISORY_CAPTION}_")
        lines.append("")
        lines.append("| Vendor | Change | Transition | Detected |")
        lines.append("|---|---|---|---|")
        for t in vendor_pqc_trends:
            event_type = t.get("event_type") or ""
            change = _VENDOR_TREND_EVENT_TYPE_LABELS.get(event_type, event_type)
            old_val = t.get("old_value") or "—"
            new_val = t.get("new_value") or "—"
            transition = f"{old_val} -> {new_val}"
            lines.append(
                f"| {md_cell(t.get('vendor'))} | {md_cell(change)} | {md_cell(transition)} | {md_cell(t.get('detected_at'))} |"
            )
        lines.append("")

    # === Remediation Burndown (Phase 181 SURF-02) ===
    # Refusal branch emitted FIRST — a refused scan must never be presented as
    # a measured (e.g. "zero closed") result, and emits no table at all.
    if closure_refusal:
        lines.append("## Remediation Burndown")
        lines.append("")
        lines.append(f"_{BURNDOWN_ADVISORY_CAPTION}_")
        lines.append("")
        lines.append(md_cell(closure_refusal.get("statement", "")))
        lines.append("")
    elif burndown:
        lines.append("## Remediation Burndown")
        lines.append("")
        lines.append(f"_{BURNDOWN_ADVISORY_CAPTION}_")
        lines.append("")
        lines.append("| Bucket | Deadline | Standard | Open | Closed | Not Observed | Resurfaced |")
        lines.append("|---|---|---|---:|---:|---:|---:|")
        # D-36 / CLOSE-03: buckets overlap by design and are NEVER summed — no
        # total row, no percentage, no sum across buckets. Computing one would
        # recreate the single-scalar failure this milestone corrected.
        for bucket_key in _BURNDOWN_BUCKET_ORDER:
            bucket = burndown.get(bucket_key)
            if bucket is None:
                continue
            deadline = bucket.get("date") or "No deadline mapped"
            lines.append(
                f"| {md_cell(bucket_key)} | {md_cell(deadline)} | {md_cell(bucket.get('standard'))} "
                f"| {bucket.get('open', 0)} | {bucket.get('closed', 0)} | {bucket.get('not_observed', 0)} "
                f"| {bucket.get('resurfaced', 0)} |"
            )
        lines.append("")

    # === Key Reuse (Phase 191 Plan 04 / SPKI-02) ===
    # D-06: this section renders unconditionally, on every run — never gated
    # on truthiness of `key_reuse` (a failed/unwired loader still produces the
    # heading, caption, and coverage line). D-12: coverage is disclosed in
    # both the zero- and non-zero-cluster cases. D-05: each cluster is framed
    # as remediation leverage, never as N separate discoveries. D-04:
    # clusters render in the order `compute_key_reuse_clusters` returns them
    # (member-count descending) — never re-sorted here.
    _key_reuse = key_reuse or {}
    _clusters = _key_reuse.get("clusters") or []
    _fingerprinted = _key_reuse.get("fingerprinted", 0)
    _total = _key_reuse.get("total", 0)
    lines.append("## Key Reuse")
    lines.append("")
    lines.append(f"_{KEY_REUSE_ADVISORY_CAPTION}_")
    lines.append("")
    lines.append(f"{_fingerprinted} of {_total} TLS endpoints have SPKI fingerprints.")
    lines.append("")
    if _clusters:
        for cluster in _clusters:
            member_count = cluster.get("member_count", len(cluster.get("members") or []))
            fingerprint = cluster.get("fingerprint") or ""
            fingerprint_display = fingerprint[:16] + "..." if len(fingerprint) > 16 else fingerprint
            lines.append(f"Re-keying this certificate remediates {member_count} endpoints.")
            lines.append("")
            lines.append(
                f"- **Cert subject:** {md_cell(cluster.get('cert_subject'))}\n"
                f"- **Public key:** {md_cell(cluster.get('cert_pubkey_alg'))} "
                f"{cluster.get('cert_pubkey_size', '')}\n"
                f"- **SPKI fingerprint:** {md_cell(fingerprint_display)}"
            )
            lines.append("")
            for member in cluster.get("members") or []:
                lines.append(f"  - {md_cell(member.get('host'))}:{member.get('port')}")
            lines.append("")
    else:
        lines.append(f"No shared keys detected across {_fingerprinted} fingerprinted endpoints.")
        lines.append("")

    return "\n".join(lines)
