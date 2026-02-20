import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from qcscan.reports.executive import build_exec_markdown
from qcscan.reports.technical import build_tech_markdown
from qcscan.engine.migration_planner import categorize_waves

from qcscan.assessment.readiness_score import compute_readiness_score
from qcscan.assessment.transition_planner import build_transition_roadmap
from qcscan.assessment.migration_advisor import recommend_migration_paths
from qcscan.assessment.operator_context import get_context
from qcscan.assessment.confidence import compute_confidence


# ✅ bump these as you evolve outputs
PLATFORM_VERSION = "3.8"
SCHEMA_VERSION = 2  # increment when output structure changes
INTELLIGENCE_VERSION = "3.8.0"


def _utc_stamp() -> str:
    # timezone-aware UTC timestamp, stable formatting
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _json_dump(path: str, obj: Any) -> None:
    # Deterministic JSON output (stable ordering)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, default=str)


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def _extract_drivers(readiness_dict: Dict[str, Any], max_n: int = 5) -> List[str]:
    """
    Try to extract top drivers in a human-readable list from readiness_score dict.
    Supports strings, dicts (with title/why), or mixed forms.
    """
    drivers = readiness_dict.get("drivers") or readiness_dict.get("top_drivers") or []
    out: List[str] = []
    for d in _as_list(drivers):
        if isinstance(d, str):
            out.append(d.strip())
        elif isinstance(d, dict):
            title = (d.get("title") or d.get("name") or d.get("driver") or "").strip()
            why = (d.get("why") or d.get("detail") or d.get("reason") or "").strip()
            if title and why:
                out.append(f"{title} — {why}")
            elif title:
                out.append(title)
            elif why:
                out.append(why)
        else:
            out.append(str(d))
        if len(out) >= max_n:
            break
    return [x for x in out if x]


def _extract_now_actions(roadmap_dict: Dict[str, Any], max_n: int = 3) -> List[str]:
    """
    Pull "NOW" items from roadmap. Supports a few shapes:
      - {"now":[...], "next":[...], "later":[...]}
      - {"waves":{"NOW":[...], ...}}
      - {"items":[{"timeframe":"NOW", ...}, ...]}
    """
    now_items: List[Any] = []

    if isinstance(roadmap_dict.get("now"), list):
        now_items = roadmap_dict.get("now", [])
    elif isinstance(roadmap_dict.get("waves"), dict):
        waves = roadmap_dict.get("waves", {})
        now_items = waves.get("NOW") or waves.get("Now") or waves.get("now") or []
    elif isinstance(roadmap_dict.get("items"), list):
        for it in roadmap_dict.get("items", []):
            if isinstance(it, dict) and str(it.get("timeframe", "")).upper() == "NOW":
                now_items.append(it)

    out: List[str] = []
    for it in _as_list(now_items):
        if isinstance(it, str):
            out.append(it.strip())
        elif isinstance(it, dict):
            title = (it.get("title") or it.get("name") or "").strip()
            why = (it.get("why") or it.get("reason") or "").strip()
            if title and why:
                out.append(f"{title} — {why}")
            elif title:
                out.append(title)
            elif why:
                out.append(why)
        else:
            out.append(str(it))

        if len(out) >= max_n:
            break

    return [x for x in out if x]


def _build_scorecard_md(cfg, assessment: Dict[str, Any], roadmap_dict: Dict[str, Any]) -> str:
    ctx = assessment.get("context") or {}
    readiness = assessment.get("readiness_score") or {}
    confidence = assessment.get("confidence") or {}

    score = readiness.get("score", readiness.get("total_score", ""))
    rating = readiness.get("rating", readiness.get("band", ""))
    conf_score = confidence.get("confidence_score", confidence.get("score", ""))
    conf_rating = confidence.get("confidence_rating", confidence.get("rating", ""))

    drivers = _extract_drivers(readiness, max_n=5)
    now_actions = _extract_now_actions(roadmap_dict, max_n=3)

    owner = ctx.get("owner") or getattr(cfg.assessment, "report_owner", "Security Team")
    classification = ctx.get("data_classification") or getattr(cfg.assessment, "data_classification", "confidential")
    name = ctx.get("name") or getattr(cfg.assessment, "name", "Quantum Crypto Readiness")

    lines: List[str] = []
    lines.append(f"# Quantum Readiness Scorecard")
    lines.append("")
    lines.append(f"- **Assessment:** {name}")
    lines.append(f"- **Owner:** {owner}")
    lines.append(f"- **Data classification:** {classification}")
    lines.append("")
    lines.append(f"## Score")
    lines.append(f"- **Readiness Score:** {score}/100 {f'({rating})' if rating else ''}".strip())
    lines.append(f"- **Confidence:** {conf_score}/100 {f'({conf_rating})' if conf_rating else ''}".strip())
    lines.append("")
    lines.append("## What it means")
    lines.append("- This score reflects current crypto hygiene + readiness signals for a post-quantum transition.")
    lines.append("- Confidence reflects scan coverage and evidence quality (errors/unknown services reduce it).")
    lines.append("- Use the roadmap actions to raise readiness while building PQC transition momentum.")
    lines.append("")
    lines.append("## Top drivers")
    if drivers:
        for d in drivers:
            lines.append(f"- {d}")
    else:
        lines.append("- (No drivers available in current scoring output.)")
    lines.append("")
    lines.append("## Next 30–60 days")
    if now_actions:
        for a in now_actions:
            lines.append(f"- {a}")
    else:
        lines.append("- (No NOW actions detected — roadmap generator may not be wired yet.)")

    return "\n".join(lines) + "\n"


def _build_roadmap_md(cfg, assessment: Dict[str, Any], roadmap_dict: Dict[str, Any]) -> str:
    ctx = assessment.get("context") or {}
    owner = ctx.get("owner") or getattr(cfg.assessment, "report_owner", "Security Team")
    classification = ctx.get("data_classification") or getattr(cfg.assessment, "data_classification", "confidential")
    name = ctx.get("name") or getattr(cfg.assessment, "name", "Quantum Crypto Readiness")

    # normalize into NOW/NEXT/LATER buckets
    now_items = _extract_now_actions(roadmap_dict, max_n=50)

    next_items: List[str] = []
    later_items: List[str] = []

    if isinstance(roadmap_dict.get("next"), list):
        for it in roadmap_dict.get("next", []):
            next_items.append(it if isinstance(it, str) else (it.get("title") if isinstance(it, dict) else str(it)))
    if isinstance(roadmap_dict.get("later"), list):
        for it in roadmap_dict.get("later", []):
            later_items.append(it if isinstance(it, str) else (it.get("title") if isinstance(it, dict) else str(it)))

    # fallback: parse roadmap_dict["items"] by timeframe if present
    if (not next_items or not later_items) and isinstance(roadmap_dict.get("items"), list):
        for it in roadmap_dict.get("items", []):
            if not isinstance(it, dict):
                continue
            tf = str(it.get("timeframe", "")).upper()
            title = (it.get("title") or it.get("name") or "").strip()
            why = (it.get("why") or it.get("reason") or "").strip()
            line = f"{title} — {why}".strip(" —")
            if not line:
                continue
            if tf == "NEXT":
                next_items.append(line)
            elif tf == "LATER":
                later_items.append(line)

    next_items = [x for x in next_items if x]
    later_items = [x for x in later_items if x]

    lines: List[str] = []
    lines.append("# Transition Roadmap")
    lines.append("")
    lines.append(f"- **Assessment:** {name}")
    lines.append(f"- **Owner:** {owner}")
    lines.append(f"- **Data classification:** {classification}")
    lines.append("")
    lines.append("## NOW")
    if now_items:
        for x in now_items[:12]:
            lines.append(f"- {x}")
    else:
        lines.append("- (No NOW actions detected.)")
    lines.append("")
    lines.append("## NEXT")
    if next_items:
        for x in next_items[:12]:
            lines.append(f"- {x}")
    else:
        lines.append("- (No NEXT actions detected.)")
    lines.append("")
    lines.append("## LATER")
    if later_items:
        for x in later_items[:12]:
            lines.append(f"- {x}")
    else:
        lines.append("- (No LATER actions detected.)")

    lines.append("")
    lines.append("## Owners & Dependencies")
    lines.append("- Owners: (fill in per action)")
    lines.append("- Dependencies: (PKI, app teams, network, vendors, change windows)")

    return "\n".join(lines) + "\n"


def _build_intelligence_json(cfg, assessment: Dict[str, Any], endpoints, findings) -> Dict[str, Any]:
    """
    Minimal v3.8 intelligence output: stable, versioned, no secrets.
    We reuse existing assessment computations and include light evidence summary.
    """
    ctx = assessment.get("context") or {}
    readiness = assessment.get("readiness_score") or {}
    confidence = assessment.get("confidence") or {}
    roadmap = assessment.get("transition_roadmap") or {}

    # lightweight evidence summary (safe + stable)
    proto_counts: Dict[str, int] = {}
    scan_errors = 0
    for e in endpoints or []:
        proto = getattr(e, "protocol", None) or "UNKNOWN"
        proto_counts[proto] = proto_counts.get(proto, 0) + 1
        if getattr(e, "scan_error", None):
            scan_errors += 1

    evidence_summary = {
        "protocol_counts": dict(sorted(proto_counts.items(), key=lambda kv: kv[0])),
        "scan_error_count": scan_errors,
        "endpoint_count": len(endpoints or []),
        "finding_count": len(findings or []),
    }

    return {
        "intelligence_version": INTELLIGENCE_VERSION,
        "platform_version": PLATFORM_VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "assessment": {
            "name": ctx.get("name") or getattr(cfg.assessment, "name", "Quantum Crypto Readiness"),
            "owner": ctx.get("owner") or getattr(cfg.assessment, "report_owner", "Security Team"),
            "data_classification": ctx.get("data_classification") or getattr(cfg.assessment, "data_classification", "confidential"),
            "timezone": getattr(cfg.assessment, "timezone", "UTC"),
        },
        "evidence_summary": evidence_summary,
        "readiness_score": readiness,
        "confidence": confidence,
        "transition_roadmap": roadmap,
        # Important: do NOT include raw cert PEMs or secrets
    }


def write_reports(cfg, endpoints, findings, run_stats=None):
    outdir = cfg.output.directory
    os.makedirs(outdir, exist_ok=True)

    stamp = _utc_stamp()

    # Core outputs
    json_path = os.path.join(outdir, f"findings-{stamp}.json")
    _json_dump(json_path, findings)

    confidence = compute_confidence(cfg, endpoints)

    readiness_obj = compute_readiness_score(cfg, endpoints, findings)
    roadmap_obj = build_transition_roadmap(cfg, endpoints, findings)

    assessment = {
        "platform_version": PLATFORM_VERSION,
        "schema_version": SCHEMA_VERSION,

        "context": get_context(cfg),
        "confidence": confidence,
        "readiness_score": readiness_obj.to_dict() if hasattr(readiness_obj, "to_dict") else dict(readiness_obj),
        "transition_roadmap": roadmap_obj.to_dict() if hasattr(roadmap_obj, "to_dict") else dict(roadmap_obj),
        "migration_paths": recommend_migration_paths(findings),
        "migration_waves": categorize_waves(findings),

        # v3.7+
        "run_stats": run_stats or {},

        "notes": (
            "v3.7 adds profiles, caching/resume, phase tuning, confidence engine, and run telemetry. "
            "v3.8 adds assessment intelligence artifacts (scorecard/roadmap/intelligence json) + deterministic outputs."
        ),
    }

    assess_path = os.path.join(outdir, f"assessment-{stamp}.json")
    _json_dump(assess_path, assessment)

    exec_md = build_exec_markdown(cfg, endpoints, findings)
    exec_path = os.path.join(outdir, f"executive-summary-{stamp}.md")
    with open(exec_path, "w", encoding="utf-8") as f:
        f.write(exec_md)

    tech_md = build_tech_markdown(cfg, endpoints, findings)
    tech_path = os.path.join(outdir, f"technical-findings-{stamp}.md")
    with open(tech_path, "w", encoding="utf-8") as f:
        f.write(tech_md)

    # run stats file
    stats_path = None
    if run_stats:
        stats_path = os.path.join(outdir, f"run-stats-{stamp}.json")
        _json_dump(stats_path, run_stats)

    # v3.8 DoD outputs
    roadmap_dict = assessment.get("transition_roadmap") or {}
    scorecard_md = _build_scorecard_md(cfg, assessment, roadmap_dict)
    scorecard_path = os.path.join(outdir, f"scorecard-{stamp}.md")
    with open(scorecard_path, "w", encoding="utf-8") as f:
        f.write(scorecard_md)

    roadmap_md = _build_roadmap_md(cfg, assessment, roadmap_dict)
    roadmap_path = os.path.join(outdir, f"roadmap-{stamp}.md")
    with open(roadmap_path, "w", encoding="utf-8") as f:
        f.write(roadmap_md)

    intelligence = _build_intelligence_json(cfg, assessment, endpoints, findings)
    intelligence_path = os.path.join(outdir, f"intelligence-{stamp}.json")
    _json_dump(intelligence_path, intelligence)

    # Console summary
    waves = categorize_waves(findings)
    print("\n📊 Migration Waves:")
    for wave, items in waves.items():
        print(f"  {wave}: {len(items)} findings")

    rs = assessment["readiness_score"]
    print(f"\n🔐 Quantum Readiness Score: {rs.get('score')}/100 ({rs.get('rating')})")
    print(f"🧪 Confidence: {confidence.get('confidence_rating')} ({confidence.get('confidence_score')}/100)")
    print(f"📦 Platform Version: {assessment.get('platform_version')} | Schema: {assessment.get('schema_version')} | Intelligence: {INTELLIGENCE_VERSION}")

    print("\n✅ Wrote reports:")
    print(f"- {json_path}")
    print(f"- {assess_path}")
    if stats_path:
        print(f"- {stats_path}")
    print(f"- {exec_path}")
    print(f"- {tech_path}")
    print(f"- {scorecard_path}")
    print(f"- {roadmap_path}")
    print(f"- {intelligence_path}")