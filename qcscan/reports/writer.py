import json
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from qcscan.reports.executive import build_exec_markdown
from qcscan.reports.technical import build_tech_markdown
from qcscan.engine.migration_planner import categorize_waves

from qcscan.assessment.readiness_score import compute_readiness_score
from qcscan.assessment.transition_planner import build_transition_roadmap
from qcscan.assessment.migration_advisor import recommend_migration_paths
from qcscan.assessment.operator_context import get_context
from qcscan.assessment.confidence import compute_confidence


PLATFORM_VERSION = "3.8"
SCHEMA_VERSION = 2
INTELLIGENCE_VERSION = "3.8.0"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _json_dump(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, default=str)


def _count_findings(findings: List[Dict[str, Any]], title_contains: str) -> int:
    t = title_contains.lower()
    return sum(1 for f in (findings or []) if t in str(f.get("title", "")).lower())


def _extract_cert_key_type(ep: Any) -> Optional[str]:
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


def _normalize_evidence(endpoints: List[Any], findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(endpoints or [])
    if total == 0:
        return {
            "endpoint_count": 0,
            "finding_count": len(findings or []),
            "protocol_counts": {},
            "plaintext_http_count": 0,
            "http_on_tls_port_count": 0,
            "mtls_present_count": 0,
            "cert_key_type_counts": {},
            "expired_cert_count": 0,
            "expiring_cert_count": 0,
            "self_signed_cert_count": 0,
            "scan_error_rate": 0.0,
            "unknown_service_ratio": 0.0,
        }

    protocol_counts: Dict[str, int] = {}
    scan_errors = 0
    unknown = 0
    plaintext_http = 0
    mtls_count = 0

    key_type_counts: Dict[str, int] = {}
    expired = 0
    expiring = 0
    self_signed = 0

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    expiring_window = now + timedelta(days=30)

    for ep in endpoints:
        proto = str(getattr(ep, "protocol", None) or "UNKNOWN").upper()
        protocol_counts[proto] = protocol_counts.get(proto, 0) + 1

        if getattr(ep, "scan_error", None):
            scan_errors += 1

        if proto == "UNKNOWN":
            unknown += 1

        if proto == "HTTP":
            plaintext_http += 1

        if _mtls_present(ep):
            mtls_count += 1

        kt = _extract_cert_key_type(ep)
        if kt:
            key_type_counts[kt] = key_type_counts.get(kt, 0) + 1

        _, na = _extract_cert_dates(ep)
        if na:
            if na < now:
                expired += 1
            elif na <= expiring_window:
                expiring += 1

        ss = _is_self_signed(ep)
        if ss is True:
            self_signed += 1

    http_on_tls_port = _count_findings(findings, "http on tls")

    scan_error_rate = round(scan_errors / total, 4)
    unknown_ratio = round(unknown / total, 4)

    return {
        "endpoint_count": total,
        "finding_count": len(findings or []),
        "protocol_counts": dict(sorted(protocol_counts.items(), key=lambda kv: kv[0])),

        "plaintext_http_count": plaintext_http,
        "http_on_tls_port_count": http_on_tls_port,
        "mtls_present_count": mtls_count,

        "cert_key_type_counts": dict(sorted(key_type_counts.items(), key=lambda kv: kv[0])),
        "expired_cert_count": expired,
        "expiring_cert_count": expiring,
        "self_signed_cert_count": self_signed,

        "scan_error_rate": scan_error_rate,
        "unknown_service_ratio": unknown_ratio,
    }


def _drivers_from_evidence(ev: Dict[str, Any]) -> List[str]:
    d: List[str] = []
    if ev.get("plaintext_http_count", 0) > 0:
        d.append(f"Plaintext HTTP detected ({ev['plaintext_http_count']})")
    if ev.get("http_on_tls_port_count", 0) > 0:
        d.append(f"HTTP responded on TLS-designated ports ({ev['http_on_tls_port_count']})")
    if ev.get("expired_cert_count", 0) > 0:
        d.append(f"Expired certificates present ({ev['expired_cert_count']})")
    if ev.get("expiring_cert_count", 0) > 0:
        d.append(f"Certificates expiring in 30 days ({ev['expiring_cert_count']})")
    if ev.get("self_signed_cert_count", 0) > 0:
        d.append(f"Self-signed certs present ({ev['self_signed_cert_count']})")
    if ev.get("scan_error_rate", 0) > 0.0:
        d.append(f"Scan errors reduced coverage (error rate {ev['scan_error_rate']})")
    if ev.get("unknown_service_ratio", 0) > 0.0:
        d.append(f"Unknown services reduce inventory confidence (ratio {ev['unknown_service_ratio']})")
    return d[:5]


def _score_from_evidence(ev: Dict[str, Any]) -> Dict[str, Any]:
    # Simple, deterministic score model: 4 subscores 0–25
    hygiene = 25
    modern_tls = 25
    identity = 25
    agility = 25

    # Hygiene penalties
    hygiene -= min(25, int(ev.get("plaintext_http_count", 0)) * 3)
    hygiene -= min(10, int(ev.get("http_on_tls_port_count", 0)) * 2)

    # Identity penalties
    identity -= min(25, int(ev.get("expired_cert_count", 0)) * 6)
    identity -= min(15, int(ev.get("expiring_cert_count", 0)) * 3)
    identity -= min(10, int(ev.get("self_signed_cert_count", 0)) * 2)
    # Positive control
    if ev.get("mtls_present_count", 0) > 0:
        identity = min(25, identity + 3)

    # Agility penalties (inventory quality)
    agility -= int(min(25, float(ev.get("unknown_service_ratio", 0.0)) * 25))
    agility -= int(min(25, float(ev.get("scan_error_rate", 0.0)) * 25))

    # Modern TLS is conservative unless we have TLS facts; keep full score for now.
    # (If you later add TLS posture facts to evidence, this bucket can become real.)

    subscores = {
        "hygiene": max(0, min(25, int(hygiene))),
        "modern_tls": max(0, min(25, int(modern_tls))),
        "identity_trust": max(0, min(25, int(identity))),
        "agility_signals": max(0, min(25, int(agility))),
    }
    total = max(0, min(100, sum(subscores.values())))
    drivers = _drivers_from_evidence(ev)

    return {"total": total, "subscores": subscores, "drivers": drivers}


def _confidence_from_evidence(ev: Dict[str, Any]) -> Dict[str, Any]:
    # Start at 100, subtract penalties
    conf = 100
    scan_error_rate = float(ev.get("scan_error_rate", 0.0))
    unknown_ratio = float(ev.get("unknown_service_ratio", 0.0))

    conf -= int(min(40, scan_error_rate * 100))
    conf -= int(min(30, unknown_ratio * 60))

    conf = max(0, min(100, conf))

    factors = {
        "scan_error_rate": scan_error_rate,
        "unknown_service_ratio": unknown_ratio,
        "endpoint_count": int(ev.get("endpoint_count", 0)),
    }
    return {"confidence": conf, "confidence_factors": factors}


def _roadmap_from_evidence(ev: Dict[str, Any], drivers: List[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    def add(tf: str, title: str, why: str, deps: Optional[List[str]] = None):
        items.append({
            "timeframe": tf,
            "title": title,
            "why": why,
            "owner": "TBD",
            "dependencies": deps or [],
        })

    # NOW
    if ev.get("plaintext_http_count", 0) > 0:
        add("NOW", "Eliminate plaintext HTTP / enforce HTTPS",
            f"Detected plaintext HTTP services ({ev['plaintext_http_count']}).",
            ["Service owner confirmation", "Change window"])
    if ev.get("expiring_cert_count", 0) > 0 or ev.get("expired_cert_count", 0) > 0:
        add("NOW", "Certificate lifecycle SLAs + automation",
            f"Expired={ev.get('expired_cert_count',0)}, expiring(30d)={ev.get('expiring_cert_count',0)}.",
            ["PKI/team ownership", "Automation tooling selection"])
    if ev.get("unknown_service_ratio", 0.0) > 0.0:
        add("NOW", "Close inventory gaps (unknown services)",
            f"Unknown service ratio is {ev.get('unknown_service_ratio')}.",
            ["Deeper fingerprinting", "Asset/CMDB reconciliation"])

    # NEXT
    add("NEXT", "TLS uplift plan (standardize configs, remove legacy)",
        "Standardize TLS configs and reduce long-term crypto migration friction.",
        ["TLS termination inventory", "Golden config baseline"])
    add("NEXT", "PKI PQC readiness (hybrid planning + vendor mapping)",
        "Certificate public key cryptography requires PQC transition planning.",
        ["PKI hierarchy inventory", "Vendor capability mapping"])
    if ev.get("mtls_present_count", 0) > 0:
        add("NEXT", "Standardize mTLS onboarding & trust chains",
            f"mTLS signals detected ({ev.get('mtls_present_count')}).",
            ["Service mesh / platform standards", "Trust chain governance"])

    # LATER (always)
    add("LATER", "Hybrid TLS pilots (where supported)",
        "Pilot hybrid/PQC-ready endpoints in controlled scope.",
        ["Candidate selection", "Test environment"])
    add("LATER", "Crypto-agility governance & library baselines",
        "Formalize crypto-agility patterns (libraries, offload, policy, inventory).",
        ["Architecture standards", "SRE/platform alignment"])

    # Enforce 6–12 items max: pad if needed with low-noise defaults
    while len(items) < 6:
        add("NEXT", "Ownership + criticality tagging", "Tag endpoints with owner and business criticality.", [])
    return items[:12]


def _scorecard_markdown(cfg, score: Dict[str, Any], conf: Dict[str, Any], drivers: List[str], roadmap: List[Dict[str, Any]]) -> str:
    now_actions = [r for r in roadmap if r.get("timeframe") == "NOW"][:3]
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
        return [r for r in roadmap if r.get("timeframe") == tf]

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

    # 2) v3.7 Assessment JSON (legacy but still supported)
    confidence_legacy = compute_confidence(cfg, endpoints)
    readiness_legacy = compute_readiness_score(cfg, endpoints, findings).to_dict()
    transition_legacy = build_transition_roadmap(cfg, endpoints, findings).to_dict()

    assessment = {
        "platform_version": PLATFORM_VERSION,
        "schema_version": SCHEMA_VERSION,
        "context": get_context(cfg),
        "confidence": confidence_legacy,
        "readiness_score": readiness_legacy,
        "transition_roadmap": transition_legacy,
        "migration_paths": recommend_migration_paths(findings),
        "migration_waves": categorize_waves(findings),
        "run_stats": run_stats or {},
        "notes": "v3.8 adds intelligence outputs (scorecard/roadmap/intelligence.json) while keeping v3.7 assessment.json stable.",
    }
    assessment_path = os.path.join(outdir, f"assessment-{stamp}.json")
    _json_dump(assessment_path, assessment)

    # 3) Executive + Technical markdowns
    exec_md = build_exec_markdown(cfg, endpoints, findings)
    exec_path = os.path.join(outdir, f"executive-summary-{stamp}.md")
    with open(exec_path, "w", encoding="utf-8") as f:
        f.write(exec_md)

    tech_md = build_tech_markdown(cfg, endpoints, findings)
    tech_path = os.path.join(outdir, f"technical-findings-{stamp}.md")
    with open(tech_path, "w", encoding="utf-8") as f:
        f.write(tech_md)

    # 4) v3.8 Intelligence outputs
    evidence = _normalize_evidence(endpoints, findings)
    score = _score_from_evidence(evidence)
    conf = _confidence_from_evidence(evidence)
    roadmap = _roadmap_from_evidence(evidence, score.get("drivers", []))

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
        "roadmap": roadmap,
    }
    intelligence_path = os.path.join(outdir, f"intelligence-{stamp}.json")
    _json_dump(intelligence_path, intelligence)

    scorecard_path = os.path.join(outdir, f"scorecard-{stamp}.md")
    with open(scorecard_path, "w", encoding="utf-8") as f:
        f.write(_scorecard_markdown(cfg, score, conf, score.get("drivers", []), roadmap))

    roadmap_path = os.path.join(outdir, f"roadmap-{stamp}.md")
    with open(roadmap_path, "w", encoding="utf-8") as f:
        f.write(_roadmap_markdown(roadmap))

    # 5) Ensure reporting timing exists BEFORE writing run-stats file
    if run_stats is not None:
        run_stats.setdefault("timings_sec", {})
        # If run_scan already timed "reporting", don't clobber it; otherwise set it.
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

    print(f"\n🔐 Readiness Score (v3.8): {score.get('total')}/100")
    print(f"🧪 Confidence (v3.8): {conf.get('confidence')}/100")
    print(f"📦 Platform Version: {PLATFORM_VERSION} | Schema: {SCHEMA_VERSION} | Intelligence: {INTELLIGENCE_VERSION}")

    print("\n✅ Wrote reports:")
    for p in [findings_path, assessment_path, stats_path, exec_path, tech_path, scorecard_path, roadmap_path, intelligence_path]:
        if p:
            print(f"- {p}")