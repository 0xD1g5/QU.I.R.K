from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.confidence import compute_confidence
from quirk.intelligence.roadmap import build_phased_roadmap
from quirk.assessment.migration_advisor import recommend_migration_paths
from quirk.reports._md_escape import md_cell  # Phase 78 / HARDEN-01: wrap scanner-controlled cells
from quirk.reports.content_model import assert_congruent  # WR-05: fail-closed guard on compat path
from quirk.reports.html_renderer import build_algorithm_inventory  # Phase 81 / CMVP-06: shared inventory builder
from quirk.reports.content_model import ExecContent  # D-03 / Phase 98: shared content model
from quirk.reports.content_model import NOT_COMPUTED_STATEMENT, effective_score_divisor  # Phase 188 SCORE-06 / 188-03

# D-07 / WR-09 (Phase 73): fallback bullet when score dict is malformed.
_INTERPRETATION_UNAVAILABLE = "Score data unavailable for this run."

# Phase 200 Plan 04 / RPT-01: ordered (label, cfg-attr) pairs for the identity
# lines carried onto CLI-visible surfaces (executive markdown, scorecard
# markdown, Rich console summary). Image-based branding is deliberately
# excluded — no CLI surface can honestly render an image.
_IDENTITY_FIELD_ORDER = (
    ("Client", "client_name"),
    ("Engagement", "engagement_name"),
    ("Prepared by", "prepared_by"),
    ("Cover date", "cover_date"),
    ("Confidentiality", "confidentiality_line"),
)


def resolve_identity_pairs(cfg) -> List[tuple]:
    """Return the ordered (label, value) identity pairs set on cfg.report.branding.

    Phase 200 Plan 04 / RPT-01: the ONE shared resolution used by every
    CLI-visible surface (executive.py, writer.py's scorecard and Rich console).
    Double-getattr throughout — a cfg with no `report` section (e.g. existing
    SimpleNamespace test fixtures) must yield an empty list, not raise.
    No image-based branding field is ever included here (T-200-12).
    """
    branding = getattr(getattr(cfg, "report", None), "branding", None)
    pairs: List[tuple] = []
    for label, attr in _IDENTITY_FIELD_ORDER:
        value = getattr(branding, attr, None)
        if value:
            pairs.append((label, value))
    return pairs


def _build_interpretation(
    evidence: Dict[str, Any],
    score: Dict[str, Any],
    endpoints=None,
    findings=None,
) -> Dict[str, Any]:
    """
    Produces human-friendly narrative bullets for executive reporting.
    Ported from quirk.assessment.interpretation_engine, adapted for intelligence dicts.
    """
    sev_counts = Counter(
        (f.get("severity", "UNKNOWN") for f in (findings or [])),
    )

    bullets: List[str] = []

    # Score framing — D-07 / WR-09 guard: score may be None, non-dict, or missing 'score' key.
    score_val = score.get("score") if isinstance(score, dict) else None
    if score_val is None:
        return {"bullets": [_INTERPRETATION_UNAVAILABLE]}
    rating_val = score.get("rating", "Unknown")
    bullets.append(
        f"Quantum Readiness Score is **{score_val}/100** (**{rating_val}**)."
    )

    # Drivers (top 3) — dict-based access (Pitfall 1: NOT tuple unpacking)
    drivers = score.get("drivers", [])
    if drivers:
        top = drivers[:3]
        drivers_txt = "; ".join(
            [f"{d['reason']} (-{d['points']})" for d in top]
        )
        bullets.append(f"Top score drivers: {drivers_txt}.")

    # TLS/SSH visibility framing
    tls_ok = len(
        [
            e
            for e in (endpoints or [])
            if getattr(e, "protocol", "") == "TLS" and not getattr(e, "scan_error", None)
        ]
    )
    ssh_ok = len(
        [
            e
            for e in (endpoints or [])
            if getattr(e, "protocol", "") == "SSH" and not getattr(e, "scan_error", None)
        ]
    )
    if tls_ok + ssh_ok == 0:
        bullets.append(
            "No successful deep TLS/SSH handshakes were captured in this run; "
            "expand visibility (scope, segmentation allowances, and ports) to improve confidence."
        )
    else:
        bullets.append(
            f"Successfully profiled **{tls_ok} TLS** and **{ssh_ok} SSH** "
            "endpoints in scope for cryptographic posture."
        )

    # TIMEOUT and NOT_TLS_ON_PORT event context from endpoints
    err_cats: Dict[str, int] = {}
    for e in (endpoints or []):
        err = getattr(e, "scan_error", None)
        if err:
            err_cats[str(err)] = err_cats.get(str(err), 0) + 1

    timeout = err_cats.get("TIMEOUT", 0)
    not_tls = err_cats.get("NOT_TLS_ON_PORT", 0)
    if timeout:
        bullets.append(
            f"Observed **{timeout} TIMEOUT** events, commonly indicating "
            "filtering/segmentation or unreachable hosts during scan."
        )
    if not_tls:
        bullets.append(
            f"Observed **{not_tls} NOT_TLS_ON_PORT** events, indicating services on "
            "TLS-like ports that do not speak TLS (common with device management interfaces)."
        )

    # CRITICAL+HIGH severity summary
    hi_crit = sev_counts.get("CRITICAL", 0) + sev_counts.get("HIGH", 0)
    bullets.append(
        f"High-impact items (CRITICAL+HIGH): **{hi_crit}**. "
        "Near-term hygiene accelerates crypto agility and reduces baseline risk."
    )

    return {"bullets": bullets}


def _count_noninfo(findings: List[Dict]) -> Counter:
    return Counter([f["severity"] for f in findings if f.get("severity") != "INFO"])


def build_exec_markdown(
    cfg,
    endpoints,
    findings,
    *,
    exec_content: "ExecContent | None" = None,
    scan_completed_at: "datetime | None" = None,
    coverage: dict | None = None,
) -> str:
    # D-03 / Phase 98: exec_content carries shared narrative/risks/roadmap from writer.py seam.
    # When provided, narrative/risks/roadmap are sourced from exec_content (D-03 guarantee).
    # When None (backward-compat), compute locally — legacy path without the shared model.
    #
    # SCORE-03 / D-16b (Phase 184.3): scan_completed_at is the naive-UTC scan
    # instant (CryptoEndpoint.scanned_at, derived once in writer.py),
    # rendered as a "Scan completed:" line distinct from the report-build
    # "Generated:" line below. Local import avoids a circular import
    # (writer.py imports this module at load time).
    from quirk.reports.writer import format_scan_completed_at

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    evidence = build_evidence_summary(endpoints, findings)
    score_raw = compute_readiness_score(
        evidence,
        profile=cfg.intelligence.profile,
        weights=cfg.intelligence.calibration_overrides or None,
    )
    conf_raw = compute_confidence(evidence)
    roadmap_raw = build_phased_roadmap(evidence, score_raw)
    recs = recommend_migration_paths(findings)
    interp = _build_interpretation(evidence, score_raw, endpoints=endpoints, findings=findings)

    sev_counts = _count_noninfo(findings)
    high_crit = sev_counts.get("HIGH", 0) + sev_counts.get("CRITICAL", 0)

    # Discovery counts from evidence
    tls_ok = len(
        [
            e
            for e in endpoints
            if getattr(e, "protocol", "") == "TLS" and not getattr(e, "scan_error", None)
        ]
    )
    ssh_ok = len(
        [
            e
            for e in endpoints
            if getattr(e, "protocol", "") == "SSH" and not getattr(e, "scan_error", None)
        ]
    )
    http_plain = evidence.get("plaintext_http_count", 0)
    unknown_open = evidence.get("protocol_counts", {}).get("UNKNOWN", 0)

    # Confidence section values
    coverage_pct = int(
        conf_raw.get("factor_breakdown", {})
        .get("coverage_ratio", {})
        .get("value", 0) * 100
    )
    tls_enum_coverage_pct = evidence.get("tls_enum_coverage_pct", 0)
    blockers_top = Counter(
        str(getattr(e, "scan_error", "")) for e in endpoints if getattr(e, "scan_error", None)
    ).most_common(5)

    lines: List[str] = []
    lines.append(f"# {cfg.assessment.name}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"- **Generated:** {now}")
    lines.append(f"- **Scan completed:** {format_scan_completed_at(scan_completed_at)}")
    lines.append(f"- **Owner:** {cfg.assessment.report_owner}")
    lines.append(f"- **Data classification:** {cfg.assessment.data_classification}")
    # Phase 200 Plan 04 / RPT-01: identity lines, each individually conditional —
    # absent branding must produce byte-identical output to today.
    for _label, _value in resolve_identity_pairs(cfg):
        lines.append(f"- **{_label}:** {_value}")
    lines.append("")

    # === Scan Coverage (Phase 192 Plan 07 / OBS-02, D-13/D-15) ===
    # D-13: placed after Executive Summary, before Readiness Assessment.
    # Unconditional heading (never gated on truthiness of `coverage`); only
    # the body varies — mirrors technical.py's identical section, and is
    # distinct from the pre-existing per-endpoint "Confidence & Coverage" /
    # "Discovery and Coverage" sections further below in this report, which
    # are untouched by this plan.
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

    # EXEC-01 / D-03 / Phase 98: Readiness Assessment narrative prose block.
    # Sourced from exec_content when provided (shared model, guaranteed identical to HTML).
    # Falls back to _build_interpretation bullets for backward-compat when exec_content is None.
    lines.append("## Readiness Assessment")
    lines.append("")
    if exec_content is not None:
        lines.append(exec_content.narrative_lead)
        lines.append("")
        if exec_content.narrative_drivers:
            # WR-01: wrap scanner-derived driver text in md_cell for parity with the
            # HTML template's `| sanitize` chokepoint on the same data.
            drivers = "; ".join(md_cell(d) for d in exec_content.narrative_drivers)
            lines.append("Key factors: " + drivers + ".")
        lines.append("")
    else:
        # Backward-compat path: narrative_lead not available; render interpretation bullets.
        # WR-05: keep this path fail-closed — run the same D-06 congruence guard the
        # shared-model path enforces, so an EXCELLENT/GOOD/MODERATE headline can never be
        # rendered here alongside a CRITICAL finding.
        assert_congruent(score_raw["rating"], findings)
        for b in interp.get("bullets", []):
            lines.append(f"- {md_cell(b)}")
        lines.append("")

    # D-07 / SCORE-XPARENCY-01: subscore decomposition in executive markdown
    _SUBSCORE_LABELS = [
        ("hygiene",         "Hygiene"),
        ("modern_tls",      "Modern TLS"),
        ("identity_trust",  "Identity"),
        ("agility_signals", "Agility"),
        ("data_at_rest",    "Data at Rest"),
        ("data_in_motion",  "Data in Motion"),
    ]

    lines.append("## Quantum Readiness Score")
    if exec_content is not None:
        # TRANS-04 / Phase 102: source score total/band/subscores/rollup from the shared
        # exec_content model so CLI output is numerically identical to HTML/PDF/DOCX.
        # Phase 188 SCORE-06 / 188-03: score_total is None when zero domains were
        # assessed -- render the disclosure + the once-composed not-computed
        # statement instead of a fabricated "None/100" or "0/100".
        if exec_content.score_total is None:
            lines.append(f"**{exec_content.coverage_disclosure}**")
            lines.append("")
            lines.append(NOT_COMPUTED_STATEMENT)
        else:
            lines.append(
                f"**Score:** **{exec_content.score_total}/100**  \n"
                f"**Rating:** **{exec_content.score_band}**"
            )
            lines.append("")
            lines.append(exec_content.coverage_disclosure)
        lines.append("")
        lines.append("### Score Drivers (Top)")
        if score_raw.get("drivers"):
            for d in score_raw["drivers"][:8]:
                lines.append(f"- {md_cell(d['reason'])} (**-{d['points']}**)")
        lines.append("")
        subscores = exec_content.subscores  # replaces score_raw.get("subscores") or {}
        lines.append("### Score Decomposition")
        lines.append("")
        lines.append("| Category | Score | Budget |")
        lines.append("|----------|-------|--------|")
        for key, label in _SUBSCORE_LABELS:
            # 188 review CR-01: the key is always present with value None for an
            # unassessed category — dict.get's default never fires. Branch on
            # None explicitly so the cell renders an honest em dash, never "None".
            _v = subscores.get(key)
            lines.append(f"| {label} | {'—' if _v is None else _v} | /25 |")
        lines.append("")
        # WR-03 / IN-01: raw_sum from shared model (identical to HTML surface).
        # Phase 188 SCORE-06 / 188-03: dynamic divisor (never the retired fixed rollup literal),
        # and the rollup arithmetic is only meaningful when a score was computed.
        # effective_score_divisor() falls back to the legacy fixed divisor for a
        # pre-188 exec_content (score computed, no score_divisor) so this line
        # keeps rendering unchanged for callers that never adopted SCORE-06.
        _divisor = effective_score_divisor(exec_content.score_total, exec_content.score_divisor)
        if _divisor:
            lines.append(
                f"**Rollup:** {exec_content.raw_sum} ÷ {_divisor:g}"
                f" = **{exec_content.score_total} / 100**"
            )
        # D-09 / 184.4-06: annotate a capped band beside the arithmetic that would
        # otherwise contradict it (BACK-89 in mirror image). Structured value from
        # quirk.severity_bands.cap_reason() via compute_readiness_score() — never
        # re-derived or re-worded here.
        # 184.4 WR-01: read from the shared model, not score_raw, so this surface
        # shares the D-03 seam with score_total/score_band/subscores/raw_sum
        # instead of re-fetching the key independently. None when uncapped.
        _rating_cap_reason = exec_content.rating_cap_reason
        if _rating_cap_reason:
            lines.append(f"**Cap reason:** {_rating_cap_reason}")
        if exec_content.scoring_version:
            lines.append(f"*Scoring version: {exec_content.scoring_version}*")
    else:
        # Backward-compat path: exec_content not available (external callers only).
        # writer.py always passes exec_content, so this path is legacy only.
        _score_total = score_raw.get("score")
        _coverage_disclosure = score_raw.get("coverage_disclosure", "") or ""
        _scoring_version = score_raw.get("scoring_version")
        if _score_total is None:
            lines.append(f"**{_coverage_disclosure}**")
            lines.append("")
            lines.append(NOT_COMPUTED_STATEMENT)
        else:
            lines.append(f"**Score:** **{_score_total}/100**  \n**Rating:** **{score_raw['rating']}**")
            lines.append("")
            lines.append(_coverage_disclosure)
        lines.append("")
        lines.append("### Score Drivers (Top)")
        if score_raw.get("drivers"):
            for d in score_raw["drivers"][:8]:
                lines.append(f"- {md_cell(d['reason'])} (**-{d['points']}**)")
        lines.append("")
        subscores = score_raw.get("subscores") or {}
        lines.append("### Score Decomposition")
        lines.append("")
        lines.append("| Category | Score | Budget |")
        lines.append("|----------|-------|--------|")
        for key, label in _SUBSCORE_LABELS:
            # 188 review CR-01: explicit None branch — dict.get's default never
            # fires for a present-but-None key (unassessed category).
            _v = subscores.get(key)
            lines.append(f"| {label} | {'—' if _v is None else _v} | /25 |")
        # Phase 188 SCORE-06: subscores.get(k) is None for an unassessed category
        # (exclude-and-rescale) -- `or 0` prevents a TypeError here.
        raw_sum = sum((subscores.get(k) or 0) for k, _ in _SUBSCORE_LABELS)
        lines.append("")
        # Phase 188 SCORE-06 / 188-03: dynamic divisor, read from score_raw since
        # exec_content is unavailable on this legacy path. Falls back to the
        # legacy fixed divisor for a pre-188 score_raw dict (see
        # effective_score_divisor's docstring).
        _divisor = effective_score_divisor(_score_total, score_raw.get("score_divisor"))
        if _divisor:
            lines.append(f"**Rollup:** {raw_sum} ÷ {_divisor:g} = **{_score_total} / 100**")
        # D-09 / 184.4-06: same cap-reason annotation as the exec_content branch,
        # so both surfaces agree (see comment above).
        # 184.4 WR-01: this branch reads score_raw by necessity — it is the
        # legacy path taken only when exec_content is None (external callers;
        # writer.py always passes one), so the shared model is unavailable
        # here. This is the one remaining score_raw read of the key outside
        # build_exec_content(), and it is unreachable from the shipped
        # pipeline.
        _rating_cap_reason = score_raw.get("rating_cap_reason")
        if _rating_cap_reason:
            lines.append(f"**Cap reason:** {_rating_cap_reason}")
        if _scoring_version:
            lines.append(f"*Scoring version: {_scoring_version}*")
    lines.append("")

    # EXEC-02 / D-03 / Phase 98: Priority Business Risks from shared content model.
    # Risk labels and impact sentences come from ALGO_IMPACT_MAP (static map, D-02).
    # Finding-derived bullet labels wrapped with md_cell per HARDEN-01.
    if exec_content is not None and exec_content.top_risks:
        lines.append("## Priority Business Risks")
        lines.append("")
        for risk in exec_content.top_risks:
            lines.append(
                f"- **{md_cell(risk.risk_label)}** — {md_cell(risk.impact_sentence)}"
            )
        lines.append("")

    lines.append("## Confidence & Coverage")
    lines.append(
        f"- **Confidence:** **{conf_raw['confidence_rating']}** ({conf_raw['confidence_score']}/100)"
    )
    # 184.1-06 / SC-3 / D-12 / D-15: emit the formula-version marker so a client
    # reading this exec summary can tell which confidence formula produced the
    # number. D-15's rule is stated in terms of the field NAME being present or
    # absent, so the literal string must appear, not only the value. Omit the
    # bullet entirely rather than render "None" when the value is missing.
    _formula_version = conf_raw.get("confidence_formula_version")
    if _formula_version:
        lines.append(f"- **confidence_formula_version:** {_formula_version}")
    # 184.1 / SC-4 / D-16: this caption must describe the CURRENT coverage_ratio
    # definition. coverage_pct is derived from factor_breakdown["coverage_ratio"]
    # above, which since Phase 184.1 is assessed_crypto_count / assessable_endpoint_count
    # — NOT the pre-184.1 "TLS+SSH successful / total in-scope endpoints". Keep this
    # wording in sync with docs/report-interpretation.md's coverage_ratio row.
    lines.append(
        f"- **Coverage:** {coverage_pct}% "
        "(crypto-bearing endpoints assessed / assessable endpoints)"
    )
    lines.append(
        f"- **TLS Enumeration Coverage:** {tls_enum_coverage_pct}% "
        "(TLS-success endpoints with capabilities captured)"
    )
    if blockers_top:
        lines.append("- **Top visibility blockers:**")
        for category, count in blockers_top:
            lines.append(f"  - {md_cell(category)}: {count}")

    lines.append("")
    lines.append("## Discovery and Coverage")
    lines.append(f"- **TLS endpoints successfully scanned:** {tls_ok}")
    lines.append(f"- **SSH endpoints successfully scanned:** {ssh_ok}")
    lines.append(f"- **Plaintext HTTP services detected:** {http_plain}")
    lines.append(f"- **Unknown open services detected:** {unknown_open}")
    # Phase 146 D-08/D-09/D-10 (DISC-07): undetermined-host disclosure — reads the
    # shared ExecContent field only; never recomputes from raw endpoints/error category.
    _undetermined_n = getattr(exec_content, "undetermined_hosts_count", 0) if exec_content is not None else 0
    _undetermined_breakdown = (
        getattr(exec_content, "undetermined_hosts_breakdown", {}) if exec_content is not None else {}
    )
    lines.append(f"- **Hosts undetermined (unreachable/filtered):** {_undetermined_n}")
    if _undetermined_n > 0:
        _liveness_skip_n = _undetermined_breakdown.get("liveness_skip", 0)
        _exception_n = _undetermined_breakdown.get("discovery_exception", 0)
        lines.append(f"  - no response to liveness pre-pass: {_liveness_skip_n}")
        lines.append(f"  - discovery batch errors: {_exception_n}")
    lines.append("")

    # Phase 81 / CMVP-06: Algorithm Inventory with FIPS 140-3 CMVP Coverage column.
    # Empty matches render the literal "Not in CMVP catalog" (v4.10-D-01 invariant —
    # do not introduce alternative wording). coverage_for_algorithm is consumed via the shared
    # build_algorithm_inventory helper (which imports it lazily).
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

    lines.append("## Findings Overview (Executive-Relevant)")
    lines.append(f"- **High-impact items (CRITICAL + HIGH):** {high_crit}")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        lines.append(f"- **{sev}:** {sev_counts.get(sev, 0)}")

    lines.append("")
    # Pitfall 6 / EXEC-01 / Phase 98: Interpretation section removed per plan 98-02.
    # Its content is now subsumed into the Readiness Assessment narrative block above
    # (narrative_lead + narrative_drivers from exec_content, or interp bullets in fallback path).
    # Do NOT re-add a separate interpretation section.

    lines.append("## Transition Roadmap")
    lines.append("")
    # EXEC-03 / D-03 / Phase 98: roadmap items with effort/impact labels.
    # When exec_content is provided, use exec_content.roadmap_items (RoadmapItem dataclasses
    # with effort/impact already attached). When not, fall back to raw roadmap_raw items.
    phase_labels = {
        "NOW": "NOW — Immediate (0-6 months)",
        "NEXT": "NEXT — Near-term (6-18 months)",
        "LATER": "LATER — Strategic (18+ months)",
    }
    if exec_content is not None:
        for phase_key in ("NOW", "NEXT", "LATER"):
            phase_items = [r for r in exec_content.roadmap_items if r.phase == phase_key]
            if phase_items:
                lines.append(f"### {phase_labels[phase_key]}")
                for item in phase_items:
                    # EXEC-03: effort/impact labels appended to each roadmap bullet (HARDEN-01: md_cell on derived text)
                    effort_label = f"{item.effort} EFFORT"
                    impact_label = f"{item.impact} IMPACT"
                    lines.append(
                        f"- **{md_cell(item.title)}** — {md_cell(item.why)}"
                        f" [{effort_label} · {impact_label}]"
                    )
                    lines.append(
                        f"  - Owner: {md_cell(item.owner_placeholder)} | Timeframe: {md_cell(item.timeframe)}"
                    )
                lines.append("")
    else:
        # Backward-compat: no exec_content — render without effort/impact labels
        roadmap_items_raw = roadmap_raw.get("items", [])
        for phase_key in ("NOW", "NEXT", "LATER"):
            phase_items = [r for r in roadmap_items_raw if r.get("phase") == phase_key]
            if phase_items:
                lines.append(f"### {phase_labels[phase_key]}")
                for item in phase_items:
                    lines.append(f"- **{md_cell(item['title'])}** — {md_cell(item['why'])}")
                    lines.append(
                        f"  - Owner: {md_cell(item['owner_placeholder'])} | Timeframe: {md_cell(item['timeframe'])}"
                    )
                lines.append("")

    if recs:
        lines.append("")
        lines.append("## Recommended Migration Paths (Top Items)")
        shown = 0
        for r in recs:
            if shown >= 10:
                break
            lines.append(f"- **{md_cell(r.get('path'))}** — {md_cell(r.get('recommendation'))}")
            if r.get("host") and r.get("port") is not None:
                lines.append(
                    f"  - Target: {md_cell(r.get('host'))}:{r.get('port')} | Severity: {r.get('severity')}"
                )
            shown += 1
        # closes cbom-intel-reports/IN-06 (Phase 77 D-12) — make truncation transparent.
        remaining = max(0, len(recs) - 10)
        if remaining:
            lines.append(f"- ... and {remaining} more (see full report)")

    lines.append("")
    lines.append("## Recommended Next Actions (30–60 days)")
    lines.append(
        "1. Confirm ownership for TLS termination points and certificate authorities "
        "(internal and cloud)."
    )
    lines.append(
        "2. Establish certificate lifecycle automation and renewal SLAs; "
        "address near-term expirations."
    )
    lines.append(
        "3. Launch crypto-agility baselining (standard TLS patterns, dependency mapping, "
        "upgrade paths)."
    )
    lines.append(
        "4. Identify 2–3 pilot candidates for PQC/hybrid readiness planning "
        "and vendor capability mapping."
    )
    lines.append("")

    # Phase 128 D-09: Hardware PQC Advisory paragraph — advisory-only, not scored.
    # Appended as a sub-section under Strategic Recommendations.
    # Guard: only emit when hardware_devices is non-empty.
    if exec_content is not None and getattr(exec_content, "hardware_devices", []):
        hw_devs = exec_content.hardware_devices
        tier_counts: dict = {}
        for _hw in hw_devs:
            _t = _hw.get("remediation_tier", "Tier N/A")
            tier_counts[_t] = tier_counts.get(_t, 0) + 1
        lines.append("### Hardware PQC Advisory")
        lines.append("")
        lines.append(
            f"> **Advisory only — not included in readiness score.** "
            f"{len(hw_devs)} hardware device(s) fingerprinted. "
            f"Tier 1 (replace by 2030): {tier_counts.get('Tier 1', 0)}, "
            f"Tier 2 (firmware upgrade 2030–2033): {tier_counts.get('Tier 2', 0)}, "
            f"Tier 3 (monitor, re-evaluate 2033+): {tier_counts.get('Tier 3', 0)}, "
            f"N/A (EOL before migration window): {tier_counts.get('Tier N/A', 0)}. "
            f"See full report for device-level detail."
        )
        lines.append("")
        # Phase 159 HWLC-13/D-159-O: the CLI banner lives here, inside the existing
        # Hardware PQC Advisory block, because executive.py has no lifecycle-drift
        # section at all (Phase 156 D-12 stands, not revisited — no new CLI drift
        # section is added by this plan).
        if any(_d.get("is_partial_scan") for _d in hw_devs):
            lines.append(
                "> **Partial re-probe — check-in scan; not a full assessment.**"
            )
            lines.append("")
        # Phase 129 D-05: bridge topology disclaimer — fires only when bridge pairs detected.
        if any(d.get("bridge_status") == "partial_only" for d in hw_devs):
            lines.append(
                "> **Important — Partial Protection Detected.** This scan identified "
                "network devices where quantum-safe encryption is in place at one point "
                "in the connection path, but legacy (non-quantum-safe) devices on the "
                "same network segment remain directly reachable. This means an attacker "
                "could bypass the quantum-safe device and target the unprotected backend "
                "directly. The protection shown above should be considered **incomplete** "
                "until all devices on each network segment are upgraded. A full network "
                "topology assessment (including routing and SNMP data) is required to "
                "confirm end-to-end quantum-safe coverage — this capability is on "
                "the roadmap for the next assessment cycle."
            )
            lines.append("")
        # Phase 140 BRIDGE-03: SNMP-confirmed upstream mitigation narrative —
        # fires only when at least one device has been evidence-gated-promoted.
        _upstream_mitigated_count = sum(
            1 for d in hw_devs if d.get("bridge_status") == "upstream_mitigated"
        )
        if _upstream_mitigated_count:
            lines.append(
                f"> **SNMP-Confirmed Upstream Mitigation.** For "
                f"{_upstream_mitigated_count} device(s), SNMP evidence collected "
                "from the gateway (ARP/forwarding-table data) confirms the legacy "
                "device is reachable only through a PQC-capable upstream gateway "
                "on this network segment. This is based on SNMP-derived "
                "network-path evidence and has not been independently confirmed "
                "by traffic inspection — treat as a stronger signal than 'partial "
                "protection' but not as an unqualified guarantee of end-to-end "
                "quantum-safe coverage. This designation does not affect the "
                "readiness score."
            )
            lines.append("")

    # Phase 157 HWLC-18 / D-04, D-05: forward-looking EOL/tier forecast subsection.
    # THIS IS NET-NEW — executive.py has no CLI lifecycle-drift section to
    # extend (Phase 156 D-12 deliberately deferred CLI drift rendering). Do not
    # fold this into the Hardware PQC Advisory block above; it is a sibling
    # subsection gated independently on exec_content.eol_forecast so the two
    # blocks are independently suppressible.
    if (
        exec_content is not None
        and getattr(exec_content, "eol_forecast", None)
        and exec_content.eol_forecast.get("buckets")
    ):
        eol_forecast = exec_content.eol_forecast
        lines.append("### EOL/Tier Forecast")
        lines.append("")
        lines.append(
            "> **Advisory only — not included in readiness score.** "
            "Forward-looking projection over vendor-published lifecycle dates."
        )
        lines.append("")
        for _bucket in eol_forecast["buckets"]:
            lines.append(f"- {_bucket.get('sentence', '')}")
        lines.append("")
        if eol_forecast.get("catalog_stale"):
            lines.append(
                "> The curated EOL/EOS catalog (last verified "
                f"{eol_forecast.get('catalog_last_verified', '')}) has not been "
                "re-verified within its review cadence; treat this projection "
                "accordingly."
            )
            lines.append("")

    return "\n".join(lines)
