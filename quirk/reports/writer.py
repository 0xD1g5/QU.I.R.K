import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text as RichText

from quirk.reports.executive import build_exec_markdown
from quirk.reports.technical import build_tech_markdown
from quirk.reports._md_escape import md_cell  # Phase 78 / HARDEN-01: scanner-cell escape
from quirk.engine.migration_planner import categorize_waves

from quirk import __version__ as PLATFORM_VERSION  # closes cbom-intel-reports/IN-01 (Phase 77 D-07)
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.confidence import compute_confidence
from quirk.intelligence.roadmap import build_phased_roadmap
from quirk.cbom import build_cbom, write_cbom_files
from quirk.reports.html_renderer import render_html_report, render_pdf_report


def _unique_hosts(hosts) -> set:
    """Deduplicate hosts, filtering falsy entries (None, '').

    Phase 77 D-14 / cbom-intel-reports/IN-08: previously the set construction
    `{h for h in hosts}` collapsed None and "" into a single "" member which
    inflated hosts_count by 1 when any endpoint lacked a host. Filter falsy
    entries before deduplicating.
    """
    return {h for h in (hosts or []) if h}


SCHEMA_VERSION = 2
INTELLIGENCE_VERSION = "4.4.0"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _json_dump(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, default=str)


def _extract_cert_key_type(ep: Any) -> Optional[str]:
    # cert_pubkey_alg is the canonical field on CryptoEndpoint
    v = getattr(ep, "cert_pubkey_alg", None)
    if v:
        return str(v).upper()
    # Fallback probe for any legacy/duck-typed endpoints
    for attr in ("cert_key_type", "cert_pubkey_type", "cert_public_key_type", "cert_key_algo", "cert_pubkey_algo"):
        v = getattr(ep, attr, None)
        if v:
            return str(v).upper()
    cert = getattr(ep, "cert", None)
    if isinstance(cert, dict):
        for k in ("key_type", "public_key_type", "pubkey_type", "algo"):
            if cert.get(k):
                return str(cert.get(k)).upper()
    return None


def _scorecard_markdown(cfg, score: Dict[str, Any], conf: Dict[str, Any], drivers: List[str], roadmap: List[Dict[str, Any]]) -> str:
    now_actions = [r for r in roadmap if r.get("timeframe") == "NOW" or r.get("phase") == "NOW"][:3]
    lines = []
    lines.append("# Quantum Crypto Readiness — Scorecard\n")
    lines.append(f"- **Owner:** {cfg.assessment.report_owner}")
    lines.append(f"- **Data classification:** {cfg.assessment.data_classification}\n")
    lines.append(f"## Score\n- **Readiness Score:** **{score.get('total')} / 100**\n- **Confidence:** **{conf.get('confidence')} / 100**\n")
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

    # 2) Executive + Technical markdowns
    exec_md = build_exec_markdown(cfg, endpoints, findings)
    exec_path = os.path.join(outdir, f"executive-summary-{stamp}.md")
    with open(exec_path, "w", encoding="utf-8") as f:
        f.write(exec_md)

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
    )

    pdf_path = os.path.join(outdir, f"report-{stamp}.pdf")
    pdf_ok = render_pdf_report(html_path=html_path, pdf_path=pdf_path)
    if not pdf_ok:
        pdf_path = None  # Playwright unavailable — HTML report still written

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
    cbom = build_cbom(endpoints)
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
        html_path, pdf_path,
    ] if p]
    _console.print(f"\n[bold #3b9dff]Output files ({len(output_files)}):[/]")
    for p in output_files:
        _console.print(f"  [dim]{p}[/dim]")
