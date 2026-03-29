import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from qcscan.reports.executive import build_exec_markdown
from qcscan.reports.technical import build_tech_markdown
from qcscan.engine.migration_planner import categorize_waves

from qcscan.intelligence.evidence import build_evidence_summary
from qcscan.intelligence.scoring import compute_readiness_score
from qcscan.intelligence.confidence import compute_confidence
from qcscan.intelligence.roadmap import build_phased_roadmap


PLATFORM_VERSION = "3.9"
SCHEMA_VERSION = 2
INTELLIGENCE_VERSION = "3.9.0"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _json_dump(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, default=str)


def _count_findings(findings: List[Dict[str, Any]], title_contains: str) -> int:
    t = title_contains.lower()
    return sum(1 for f in (findings or []) if t in str(f.get("title", "")).lower())


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


def _extract_cert_dates(ep: Any) -> Tuple[Optional[datetime], Optional[datetime]]:
    nb = getattr(ep, "cert_not_before", None)
    na = getattr(ep, "cert_not_after", None)

    def _to_dt(x):
        if x is None:
            return None
        if isinstance(x, datetime):
            return x
        try:
            return datetime.fromisoformat(str(x))
        except Exception:
            return None

    return _to_dt(nb), _to_dt(na)


def _is_self_signed(ep: Any) -> Optional[bool]:
    v = getattr(ep, "cert_self_signed", None)
    if isinstance(v, bool):
        return v

    subj = getattr(ep, "cert_subject", None)
    issuer = getattr(ep, "cert_issuer", None)
    if subj and issuer:
        return str(subj) == str(issuer)

    cert = getattr(ep, "cert", None)
    if isinstance(cert, dict):
        subj = cert.get("subject")
        issuer = cert.get("issuer")
        if subj and issuer:
            return str(subj) == str(issuer)

    return None


def _mtls_present(ep: Any) -> bool:
    for attr in ("mtls", "mtls_present", "client_auth", "requires_client_cert"):
        v = getattr(ep, attr, None)
        if isinstance(v, bool):
            return v
    return False


def _scorecard_markdown(cfg, score: Dict[str, Any], conf: Dict[str, Any], drivers: List[str], roadmap: List[Dict[str, Any]]) -> str:
    now_actions = [r for r in roadmap if r.get("timeframe") == "NOW" or r.get("phase") == "NOW"][:3]
    lines = []
    lines.append("# Quantum Crypto Readiness — Scorecard\n")
    lines.append(f"- **Owner:** {cfg.assessment.report_owner}")
    lines.append(f"- **Data classification:** {cfg.assessment.data_classification}\n")
    lines.append(f"## Score\n- **Readiness Score:** **{score.get('total')} / 100**\n- **Confidence:** **{conf.get('confidence')} / 100**\n")
    lines.append("## Why this score\n")
    for d in (drivers or []):
        lines.append(f"- {d}")
    if not drivers:
        lines.append("- Evidence was limited; expand scope and reduce scan errors to improve confidence.")
    lines.append("\n## Next 30–60 days\n")
    if now_actions:
        for a in now_actions:
            lines.append(f"- **{a.get('title')}** — {a.get('why')}")
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
            dep_txt = f" _(deps: {', '.join(deps)})_" if deps else ""
            lines.append(f"- **{r.get('title')}** — {r.get('why')}{dep_txt}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_reports(cfg, endpoints, findings, run_stats=None):
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
    score_raw = compute_readiness_score(evidence)
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
    }
    intelligence_path = os.path.join(outdir, f"intelligence-{stamp}.json")
    _json_dump(intelligence_path, intelligence)

    scorecard_path = os.path.join(outdir, f"scorecard-{stamp}.md")
    with open(scorecard_path, "w", encoding="utf-8") as f:
        f.write(_scorecard_markdown(cfg, score, conf, score.get("drivers", []), roadmap_items))

    roadmap_path = os.path.join(outdir, f"roadmap-{stamp}.md")
    with open(roadmap_path, "w", encoding="utf-8") as f:
        f.write(_roadmap_markdown(roadmap_items))

    # 4) Ensure reporting timing exists BEFORE writing run-stats file
    if run_stats is not None:
        run_stats.setdefault("timings_sec", {})
        run_stats["timings_sec"].setdefault("reporting", round(time.perf_counter() - report_start, 3))

    stats_path = None
    if run_stats:
        stats_path = os.path.join(outdir, f"run-stats-{stamp}.json")
        _json_dump(stats_path, run_stats)

    # Console summary
    waves = categorize_waves(findings)
    print("\n📊 Migration Waves:")
    for wave, items in waves.items():
        print(f"  {wave}: {len(items)} findings")

    print(f"\n🔐 Readiness Score (v3.9): {score.get('total')}/100")
    print(f"🧪 Confidence (v3.9): {conf.get('confidence')}/100")
    print(f"📦 Platform Version: {PLATFORM_VERSION} | Schema: {SCHEMA_VERSION} | Intelligence: {INTELLIGENCE_VERSION}")

    print("\n✅ Wrote reports:")
    for p in [findings_path, stats_path, exec_path, tech_path, scorecard_path, roadmap_path, intelligence_path]:
        if p:
            print(f"- {p}")
