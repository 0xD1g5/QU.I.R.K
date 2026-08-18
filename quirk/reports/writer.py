import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from quirk.reports.executive import build_exec_markdown
from quirk.reports.technical import build_tech_markdown
from quirk.reports._md_escape import md_cell  # Phase 78 / HARDEN-01: scanner-cell escape
from quirk.reports.content_model import build_exec_content, ReportCongruenceError  # D-03 / D-06

from quirk import __version__ as PLATFORM_VERSION  # closes cbom-intel-reports/IN-01 (Phase 77 D-07)
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.confidence import compute_confidence
from quirk.intelligence.roadmap import build_phased_roadmap
from quirk.cbom import build_cbom, write_cbom_files
from quirk.cbom.bridge import _detect_crypto_bridges, _confirm_upstream_mitigation  # Phase 129 HWCOMPAT-03 / Phase 140 BRIDGE-01
from quirk.scanner import hw_cve  # Phase 142 CVE-01: firmware CVE correlation
from quirk.reports.html_renderer import render_html_report, render_pdf_report
from quirk.reports.docx_renderer import render_docx_report


def _compute_undetermined_hosts(endpoints) -> tuple:
    """Phase 146 D-08/D-09 (DISC-07): pure count of hosts that could not be determined.

    Filters `endpoints` to rows where `port == 0` AND `scan_error_category` is one of
    ("discovery_exception", "liveness_skip") — the two Phase 144/145 discovery-stage
    advisory categories. Returns `(count, breakdown)` where breakdown always carries
    both keys, even when zero.

    Pitfall-3 invariant: `error_endpoints` (which feeds `endpoints`) accumulates
    advisory rows from EVERY scan stage, not just discovery — a bare
    `len(error_endpoints)` would overcount. The `port == 0` conjunct is load-bearing:
    a TLS/SSH/API handshake error on a live, fully-scanned host (port != 0) must NOT
    be counted as undetermined.

    CR-01: `scan_error_category` MUST NOT be the generic `"exception"` value that
    `_wrapped_phase()` in run_scan.py uses for uncaught exceptions in every other
    scanner stage (TLS, SSH, JWT, container, ...) — that value's `port=0` rows use
    a scanner-name label (e.g. "tls_scanner"), not a target host, and filtering on
    it here would conflate an unrelated scanner crash with host unreachability.
    Discovery-batch failures use the dedicated "discovery_exception" category
    instead (see run_scan.py's discovery batch loop).
    """
    breakdown = {"discovery_exception": 0, "liveness_skip": 0}
    count = 0
    for ep in (endpoints or []):
        if getattr(ep, "port", None) != 0:
            continue
        category = getattr(ep, "scan_error_category", None)
        if category not in ("discovery_exception", "liveness_skip"):
            continue
        breakdown[category] += 1
        count += 1
    return count, breakdown


def _unique_hosts(hosts) -> set:
    """Deduplicate hosts, filtering falsy entries (None, '').

    Phase 77 D-14 / cbom-intel-reports/IN-08: previously the set construction
    `{h for h in hosts}` collapsed None and "" into a single "" member which
    inflated hosts_count by 1 when any endpoint lacked a host. Filter falsy
    entries before deduplicating.
    """
    return {h for h in (hosts or []) if h}


def categorize_waves(findings):
    """Bucket findings into migration waves by severity.

    Phase 83 / CLEAN-01: Inlined from former ``quirk/engine/migration_planner.py``
    (now deleted). Test mocks at ``quirk.reports.writer.categorize_waves`` continue
    to resolve via namespace-of-use and remain valid without modification.
    """
    waves = {
        "NOW": [],
        "NEXT": [],
        "LATER": []
    }

    for f in findings:
        if f["severity"] == "CRITICAL":
            waves["NOW"].append(f)
        elif f["severity"] == "HIGH":
            waves["NEXT"].append(f)
        else:
            waves["LATER"].append(f)

    return waves


SCHEMA_VERSION = 2
# v4.10 D-02 / Phase 84-01: derive from pyproject.toml SoT via quirk.__version__
INTELLIGENCE_VERSION = PLATFORM_VERSION


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _json_dump(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, default=str)



def _scorecard_markdown(cfg, score: Dict[str, Any], conf: Dict[str, Any], drivers: List[str], roadmap: List[Dict[str, Any]]) -> str:
    now_actions = [r for r in roadmap if r.get("timeframe") == "NOW" or r.get("phase") == "NOW"][:3]
    lines = []
    lines.append("# Quantum Crypto Readiness — Scorecard\n")
    lines.append(f"- **Owner:** {cfg.assessment.report_owner}")
    lines.append(f"- **Data classification:** {cfg.assessment.data_classification}\n")
    lines.append(f"## Score\n- **Readiness Score:** **{score.get('total')} / 100**\n- **Confidence:** **{conf.get('confidence')} / 100**\n")

    # D-07 / SCORE-XPARENCY-01: subscore decomposition block
    _SUBSCORE_LABELS = [
        ("hygiene",         "Hygiene"),
        ("modern_tls",      "Modern TLS"),
        ("identity_trust",  "Identity"),
        ("agility_signals", "Agility"),
        ("data_at_rest",    "Data at Rest"),
        ("data_in_motion",  "Data in Motion"),
    ]
    subscores = score.get("subscores") or {}
    lines.append("## Score Decomposition\n")
    lines.append("| Category | Score | Budget |")
    lines.append("|----------|-------|--------|")
    for key, label in _SUBSCORE_LABELS:
        lines.append(f"| {label} | {subscores.get(key, '—')} | /25 |")
    raw_sum = sum(subscores.get(k, 0) for k, _ in _SUBSCORE_LABELS)
    lines.append(f"\n**Rollup:** {raw_sum} ÷ 1.5 = **{score.get('total')} / 100**\n")

    lines.append("## Why this score\n")
    for d in (drivers or []):
        lines.append(f"- {md_cell(d)}")
    if not drivers:
        lines.append("- Evidence was limited; expand scope and reduce scan errors to improve confidence.")
    lines.append("\n## Next 30–60 days\n")
    if now_actions:
        for a in now_actions:
            lines.append(f"- **{md_cell(a.get('title'))}** — {md_cell(a.get('why'))}")
    else:
        lines.append("- Establish ownership + inventory closure for crypto endpoints.\n")
    return "\n".join(lines).rstrip() + "\n"


def _roadmap_markdown(roadmap: List[Dict[str, Any]]) -> str:
    def section(tf: str) -> List[Dict[str, Any]]:
        return [r for r in roadmap if r.get("timeframe") == tf or r.get("phase") == tf]

    lines = ["# Quantum Crypto Transition Roadmap\n"]
    for tf in ("NOW", "NEXT", "LATER"):
        lines.append(f"## {tf}\n")
        for r in section(tf):
            deps = r.get("dependencies") or []
            # Phase 78 / HARDEN-01: wrap each scanner-derived dep title in md_cell
            # before joining, then build the parenthetical wrapper from literals.
            dep_txt = (
                f" _(deps: {', '.join(md_cell(d) for d in deps)})_" if deps else ""
            )
            lines.append(f"- **{md_cell(r.get('title'))}** — {md_cell(r.get('why'))}{dep_txt}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_reports(cfg, endpoints, findings, run_stats=None, *, error_endpoints=None):
    # D-15 (Phase 47 / Plan 03): error_endpoints is passed through to write_cbom_files
    # so schema-validation failures can be recorded as coverage_gap WARN findings.
    outdir = cfg.output.directory
    os.makedirs(outdir, exist_ok=True)

    stamp = _utc_stamp()
    report_start = time.perf_counter()

    # 1) Findings JSON (raw)
    findings_path = os.path.join(outdir, f"findings-{stamp}.json")
    _json_dump(findings_path, findings)

    # 2) Technical markdown (no score dependency — compute first)
    tech_md = build_tech_markdown(cfg, endpoints, findings)
    tech_path = os.path.join(outdir, f"technical-findings-{stamp}.md")
    with open(tech_path, "w", encoding="utf-8") as f:
        f.write(tech_md)

    # 3) Intelligence outputs — single authoritative scoring path
    evidence = build_evidence_summary(endpoints, findings)
    score_raw = compute_readiness_score(
        evidence,
        profile=cfg.intelligence.profile,
        weights=cfg.intelligence.calibration_overrides or None,
    )
    conf_raw = compute_confidence(evidence)
    roadmap_raw = build_phased_roadmap(evidence, score_raw)

    # D-03 / D-06: build shared content object BEFORE compat wrapper — score_raw uses
    # canonical keys ("score", "rating", "subscores"), not the writer compat wrapper keys
    # ("total"). ReportCongruenceError propagates to CLI before any exec report is written.
    exec_content = build_exec_content(
        score_raw=score_raw,
        findings=findings,
        roadmap_items=roadmap_raw.get("items", []),
    )

    # Compat wrappers: map intelligence schema to writer's internal format
    score = {
        "total": score_raw["score"],
        "subscores": score_raw["subscores"],
        "drivers": [d["reason"] for d in score_raw.get("drivers", [])],
    }
    conf = {
        "confidence": conf_raw.get("confidence_score", 0),
        "confidence_factors": conf_raw.get("factor_breakdown", {}),
    }
    # roadmap_raw["items"] is a list of dicts; keep the list for markdown helpers
    roadmap_items = roadmap_raw.get("items", [])

    intelligence = {
        "intelligence_version": INTELLIGENCE_VERSION,
        "assessment": {
            "name": cfg.assessment.name,
            "owner": cfg.assessment.report_owner,
            "data_classification": cfg.assessment.data_classification,
            "timezone": cfg.assessment.timezone,
        },
        "evidence_summary": evidence,
        "score": {
            "total": score.get("total"),
            "subscores": score.get("subscores"),
            "drivers": score.get("drivers"),
        },
        "confidence": conf,
        "roadmap": roadmap_raw,
        "calibration": {
            "profile": cfg.intelligence.profile,
            "overrides_applied": bool(cfg.intelligence.calibration_overrides),
        },
    }
    intelligence_path = os.path.join(outdir, f"intelligence-{stamp}.json")
    _json_dump(intelligence_path, intelligence)

    # Phase 128 D-08: load HardwareDevice rows for hardware advisory section.
    # Phase 154 D-13/D-14: per-(host, port) latest probe_status="success" row
    # — a failed re-probe never displaces a device's last-known-good state, so
    # the device stays present in the CLI/PDF/DOCX advisory instead of
    # vanishing. Pre-Phase-154 rows (probe_status IS NULL) are excluded until
    # re-scanned (D-06 append-only; no backfill). This is one of four
    # identical projection sites (D-14); see quirk/dashboard/api/routes/scan.py
    # and quirk/merge/scan.py for the dashboard/merge-path twins.
    # Advisory-only — non-fatal; uses advisory path (NOT _build_finding / findings_evaluator).
    hardware_devices: list = []
    try:
        from quirk.db import get_session as _get_session
        # Phase 154 WR-02: shared helper — see quirk/models_util.py for the
        # subquery/join/tie-break-dedupe contract every projection site relies on.
        from quirk.models_util import latest_successful_hardware_devices as _latest_hw_devices

        with _get_session(cfg.output.db_path) as _hw_sess:
            _hw_rows = _latest_hw_devices(_hw_sess)
            if _hw_rows:
                for _d in _hw_rows:
                    _tier = getattr(_d, "remediation_tier", "Tier N/A") or "Tier N/A"
                    # Phase 142 CVE-01/D-03: skip correlation entirely for
                    # unidentified vendors — no cve_* keys are set, so the
                    # renderer emits no CVE cell (call-site gate, D-03/Pitfall 4).
                    _cve_matches = None
                    _cve_confidence = None
                    _cve_attempted = None
                    if _d.vendor and _d.vendor != "Unknown":
                        _cve_firmware = hw_cve.firmware_for_correlation(_d)
                        _cve_result = hw_cve.correlate_device(_d.vendor, _d.model, _cve_firmware)
                        _cve_matches = _cve_result.matches
                        _cve_confidence = _cve_result.confidence
                        _cve_attempted = _cve_result.attempted
                    hardware_devices.append({
                        "vendor":             _d.vendor,
                        "model":              _d.model,
                        "host":               _d.host,
                        "port":               _d.port,
                        "pqc_status":         _d.pqc_status,
                        "remediation_tier":   _tier,
                        "confidence":         _d.confidence,
                        "fingerprint_method": _d.fingerprint_method,
                        "eol_date":           _d.eol_date.isoformat() if _d.eol_date else None,
                        "cnsa_deadline":      {
                            "Tier 1": "Replace by 2030",
                            "Tier 2": "Upgrade firmware 2030–2033",
                            "Tier 3": "Accept + monitor, re-evaluate 2033+",
                            "Tier N/A": "EOL before PQC migration window",
                        }.get(_tier, ""),
                        # SNMP-02 / Phase 133: nullable SNMP fingerprint fields
                        "snmp_sysdescr":      getattr(_d, "snmp_sysdescr", None),
                        "snmp_sysname":       getattr(_d, "snmp_sysname", None),
                        "snmp_sysobjectid":   getattr(_d, "snmp_sysobjectid", None),
                        "snmp_vendor":        getattr(_d, "snmp_vendor", None),
                        # SNMPV3-02 / Phase 139: nullable SNMPv3 negotiation fields
                        "snmp_version":       getattr(_d, "snmp_version", None),
                        "snmp_auth_protocol": getattr(_d, "snmp_auth_protocol", None),
                        "snmp_priv_protocol": getattr(_d, "snmp_priv_protocol", None),
                        "bridge_evidence_json": getattr(_d, "bridge_evidence_json", None),
                        "bridge_confirmed_at": getattr(_d, "bridge_confirmed_at", None),
                        # OTICS-06 / Phase 141: nullable Modbus/BACnet fingerprint fields
                        "modbus_vendor":       getattr(_d, "modbus_vendor", None),
                        "modbus_model":        getattr(_d, "modbus_model", None),
                        "modbus_firmware":     getattr(_d, "modbus_firmware", None),
                        "modbus_probe_state":  getattr(_d, "modbus_probe_state", None),
                        "bacnet_vendor":       getattr(_d, "bacnet_vendor", None),
                        "bacnet_model":        getattr(_d, "bacnet_model", None),
                        "bacnet_firmware":     getattr(_d, "bacnet_firmware", None),
                        "bacnet_probe_state":  getattr(_d, "bacnet_probe_state", None),
                        # Phase 142 CVE-01: per-device curated CVE correlation
                        "cve_matches":         _cve_matches,
                        "cve_confidence":      _cve_confidence,
                        "cve_attempted":       _cve_attempted,
                        # Phase 159 HWLC-13/D-159-M: check-in re-probe marker. The column
                        # is nullable with no DDL default, so NULL must read as False —
                        # bool(getattr(...)) is mandatory, never a bare attribute read.
                        "is_partial_scan":     bool(getattr(_d, "is_partial_scan", False)),
                    })
    except Exception:
        import logging as _log
        _log.getLogger(__name__).warning("hardware advisory section skipped (non-fatal)", exc_info=True)
    exec_content.hardware_devices = _confirm_upstream_mitigation(_detect_crypto_bridges(hardware_devices))
    # Phase 142 D-11: snapshot-stale flag for renderers' staleness caveat.
    exec_content.cve_snapshot_stale = hw_cve.is_cve_table_stale()

    # Phase 157 HWLC-18 / D-01: advisory-only forward-looking EOL/tier forecast.
    # Consumes the FINAL exec_content.hardware_devices list (post bridge-detection/
    # mitigation enrichment) so the forecast and the hardware table can never
    # disagree about the device set. No new DB session — build_eol_forecast never
    # reads hardware_drift_events, which is the structural half of D-01's
    # forward-only guarantee. Non-fatal: eol_forecast stays {} on failure.
    eol_forecast: dict = {}
    try:
        from quirk.scanner.hardware_forecast import build_eol_forecast as _build_eol_forecast

        eol_forecast = _build_eol_forecast(exec_content.hardware_devices)
    except Exception:
        import logging as _log
        _log.getLogger(__name__).warning(
            "hardware EOL/tier forecast section skipped (non-fatal)", exc_info=True
        )
    exec_content.eol_forecast = eol_forecast

    # Phase 156 D-11/HWLC-10: hardware lifecycle drift events — read-and-serialize block
    # only; Phase 155 owns drift computation. Scoped to the latest-scan slice (Pitfall 5) —
    # the bounded historical disclosure (D-09/D-10) is a dashboard-only affordance, not
    # reproduced in the report. Advisory-only — non-fatal on read failure.
    hardware_drift_events: list = []
    try:
        from sqlalchemy import func as _func
        from quirk.models import HardwareDevice as _HardwareDevice, HardwareDriftEvent as _HardwareDriftEvent
        from quirk.scanner import hardware_drift as _hardware_drift

        with _get_session(cfg.output.db_path) as _drift_sess:
            # Phase 159 WR-01: scope to successful probes only — see matching
            # rationale in quirk/dashboard/api/routes/hardware_drift.py.
            _latest_ts = (
                _drift_sess.query(_func.max(_HardwareDevice.scanned_at))
                .filter(_HardwareDevice.probe_status == "success")
                .scalar()
            )
            if _latest_ts is not None:
                # Phase 159 HWLC-13/D-159-A: a drift event inherits its triggering
                # device row's is_partial_scan provenance via this (host, port) join —
                # no column was added to HardwareDriftEvent for it (detected_at ==
                # scanned_at join rationale, RESEARCH.md Pattern 3).
                _drift_lookup = {
                    (_d.host, _d.port): (_d.vendor, _d.model, bool(getattr(_d, "is_partial_scan", False)))
                    for _d in _latest_hw_devices(_drift_sess)
                }
                _drift_rows = (
                    _drift_sess.query(_HardwareDriftEvent)
                    .filter(_HardwareDriftEvent.detected_at == _latest_ts)
                    .order_by(
                        _HardwareDriftEvent.host,
                        _HardwareDriftEvent.port,
                        _HardwareDriftEvent.event_type,
                    )
                    .all()
                )
                for _row in _drift_rows:
                    if _row.event_type == "tier_crossing":
                        _raw_direction = _hardware_drift.tier_direction(_row.old_value, _row.new_value)
                        _direction = _raw_direction if _raw_direction in ("improved", "worsened") else "neutral"
                    else:
                        _direction = "neutral"
                    _vendor, _model, _is_partial = _drift_lookup.get((_row.host, _row.port), (None, None, False))
                    hardware_drift_events.append({
                        "host":         _row.host,
                        "port":         _row.port,
                        "event_type":   _row.event_type,
                        "old_value":    _row.old_value,
                        "new_value":    _row.new_value,
                        "direction":    _direction,
                        "detected_at":  _row.detected_at.isoformat(),
                        "vendor":       _vendor,
                        "model":        _model,
                        "is_partial_scan": _is_partial,
                    })
    except Exception:
        import logging as _log
        _log.getLogger(__name__).warning(
            "hardware lifecycle drift section skipped (non-fatal)", exc_info=True
        )
    exec_content.hardware_drift_events = hardware_drift_events

    # Phase 146 D-08/D-09 (DISC-07): undetermined-host disclosure — one shared computation
    # feeds markdown/HTML/DOCX/terminal summary; no renderer recomputes this.
    _undetermined_count, _undetermined_breakdown = _compute_undetermined_hosts(endpoints)
    exec_content.undetermined_hosts_count = _undetermined_count
    exec_content.undetermined_hosts_breakdown = _undetermined_breakdown

    # 3a) Executive markdown — built here (after score_raw/exec_content) with shared model
    exec_md = build_exec_markdown(cfg, endpoints, findings, exec_content=exec_content)
    exec_path = os.path.join(outdir, f"executive-summary-{stamp}.md")
    with open(exec_path, "w", encoding="utf-8") as f:
        f.write(exec_md)

    scorecard_path = os.path.join(outdir, f"scorecard-{stamp}.md")
    with open(scorecard_path, "w", encoding="utf-8") as f:
        f.write(_scorecard_markdown(cfg, score, conf, score.get("drivers", []), roadmap_items))

    roadmap_path = os.path.join(outdir, f"roadmap-{stamp}.md")
    with open(roadmap_path, "w", encoding="utf-8") as f:
        f.write(_roadmap_markdown(roadmap_items))

    # 3b) Standalone HTML report (D-08) + PDF via Playwright (D-11)
    html_path = os.path.join(outdir, f"report-{stamp}.html")
    render_html_report(
        path=html_path,
        cfg=cfg,
        endpoints=endpoints,
        findings=findings,
        score=score,
        conf=conf,
        roadmap_items=roadmap_items,
        exec_content=exec_content,  # D-03: shared content for narrative/risks/roadmap/subscores
    )

    pdf_path = os.path.join(outdir, f"report-{stamp}.pdf")
    pdf_ok = render_pdf_report(html_path=html_path, pdf_path=pdf_path)
    if not pdf_ok:
        pdf_path = None  # Playwright unavailable — HTML report still written

    # Phase 100 / FMT-03 / D-11: DOCX auto-emit every run; skip gracefully if python-docx absent.
    # CR-02: belt-and-suspenders outer guard — any exception that escapes render_docx_report
    # (e.g. from future changes above the doc.save call) cannot abort CBOM or run-stats flush.
    docx_path = os.path.join(outdir, f"report-{stamp}.docx")
    try:
        docx_ok = render_docx_report(
            path=docx_path,
            cfg=cfg,
            findings=findings,
            exec_content=exec_content,
        )
    except Exception as e:
        import sys as _sys
        print(f"DOCX export failed unexpectedly: {e}", file=_sys.stderr)
        docx_ok = False
    if not docx_ok:
        docx_path = None

    # 4) Ensure reporting timing exists BEFORE writing run-stats file
    if run_stats is not None:
        run_stats.setdefault("timings_sec", {})
        run_stats["timings_sec"].setdefault("reporting", round(time.perf_counter() - report_start, 3))
        # Phase 67 RESUME-02: ensure partial_failures key present even for clean scans
        run_stats.setdefault("partial_failures", [])

    stats_path = None
    if run_stats:
        stats_path = os.path.join(outdir, f"run-stats-{stamp}.json")
        _json_dump(stats_path, run_stats)

    # 5) CBOM artifacts
    # WR-03 (Phase 129): guard against AttributeError if ExecContent was constructed
    # without hardware_devices (e.g. unit tests or future backward-compat paths).
    _hw_for_cbom = getattr(exec_content, "hardware_devices", None) or []
    cbom = build_cbom(
        endpoints,
        hw_devices=_confirm_upstream_mitigation(_detect_crypto_bridges(_hw_for_cbom)),
    )
    cbom_json_path, cbom_xml_path = write_cbom_files(
        cbom, outdir, stamp, error_endpoints=error_endpoints
    )

    # Rich scan summary table (D-05)
    _console = Console()

    # Migration waves summary (kept as before, but using rich)
    waves = categorize_waves(findings)
    wave_table = Table(title="Migration Waves", show_header=True, header_style="bold #3b9dff")
    wave_table.add_column("Wave", style="bold cyan")
    wave_table.add_column("Findings", justify="right")
    for wave, items in waves.items():
        wave_table.add_row(str(wave), str(len(items)))
    _console.print(wave_table)

    # Scan summary table
    summary_table = Table(title="[bold #3b9dff]QU.I.R.K. Scan Summary[/]", show_header=True, header_style="bold")
    summary_table.add_column("Metric", style="bold cyan", min_width=24)
    summary_table.add_column("Value", justify="right", min_width=16)

    hosts_count = len(
        _unique_hosts(getattr(ep, "host", None) or getattr(ep, "target", "") for ep in (endpoints or []))
    )  # closes cbom-intel-reports/IN-08 (Phase 77 D-14)
    crit_count = sum(1 for f in (findings or []) if str(f.get("severity", "")).upper() == "CRITICAL")
    high_count = sum(1 for f in (findings or []) if str(f.get("severity", "")).upper() == "HIGH")
    medium_count = sum(1 for f in (findings or []) if str(f.get("severity", "")).upper() == "MEDIUM")
    total_score = score.get("total", 0)
    total_conf = conf.get("confidence", 0)

    summary_table.add_row("Hosts scanned", str(hosts_count))
    summary_table.add_row("Hosts undetermined", str(exec_content.undetermined_hosts_count))
    summary_table.add_row("CRITICAL findings", f"[red]{crit_count}[/red]" if crit_count else "0")
    summary_table.add_row("HIGH findings", f"[orange1]{high_count}[/orange1]" if high_count else "0")
    summary_table.add_row("MEDIUM findings", f"[yellow]{medium_count}[/yellow]" if medium_count else "0")
    summary_table.add_row("Readiness score", f"[bold]{total_score}/100[/bold]")
    summary_table.add_row("Confidence", f"{total_conf}/100")
    summary_table.add_row("Platform version", PLATFORM_VERSION)
    _console.print(summary_table)

    # Output files list
    output_files = [p for p in [
        findings_path, stats_path, exec_path, tech_path,
        scorecard_path, roadmap_path, intelligence_path,
        cbom_json_path, cbom_xml_path,
        html_path, pdf_path, docx_path,  # Phase 100 / FMT-03: DOCX joins output files
    ] if p]
    _console.print(f"\n[bold #3b9dff]Output files ({len(output_files)}):[/]")
    for p in output_files:
        _console.print(f"  [dim]{p}[/dim]")
