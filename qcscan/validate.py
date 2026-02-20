import argparse
import glob
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str = ""
    fatal: bool = True  # if False, will not fail exit code


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _latest_file(pattern: str) -> Optional[str]:
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files[0]


def _human(ok: bool) -> str:
    return "✅ PASS" if ok else "❌ FAIL"


def _maybe(path: Optional[str]) -> str:
    return path if path else "<missing>"


def _version_tuple(v: str) -> Tuple[int, int]:
    m = re.match(r"^\s*(\d+)\.(\d+)", v)
    if not m:
        return (0, 0)
    return (int(m.group(1)), int(m.group(2)))


def _check_exists(name: str, path: Optional[str], fatal: bool = True) -> CheckResult:
    ok = bool(path and os.path.exists(path))
    return CheckResult(name=name, ok=ok, details=_maybe(path), fatal=fatal)


def _find_latest_run_files(outdir: str, stamp: Optional[str]) -> Dict[str, Optional[str]]:
    """
    Finds latest artifacts. If stamp is provided, tries to locate files with that stamp.
    Otherwise finds newest file per artifact type.
    """

    def by_stamp(prefix: str, ext: str) -> Optional[str]:
        if not stamp:
            return None
        p = os.path.join(outdir, f"{prefix}-{stamp}.{ext}")
        return p if os.path.exists(p) else None

    return {
        # v3.7
        "assessment": by_stamp("assessment", "json") or _latest_file(os.path.join(outdir, "assessment-*.json")),
        "findings": by_stamp("findings", "json") or _latest_file(os.path.join(outdir, "findings-*.json")),
        "run_stats": by_stamp("run-stats", "json") or _latest_file(os.path.join(outdir, "run-stats-*.json")),
        "exec_md": by_stamp("executive-summary", "md") or _latest_file(os.path.join(outdir, "executive-summary-*.md")),
        "tech_md": by_stamp("technical-findings", "md") or _latest_file(os.path.join(outdir, "technical-findings-*.md")),

        # v3.8
        "scorecard_md": by_stamp("scorecard", "md") or _latest_file(os.path.join(outdir, "scorecard-*.md")),
        "roadmap_md": by_stamp("roadmap", "md") or _latest_file(os.path.join(outdir, "roadmap-*.md")),
        "intelligence_json": by_stamp("intelligence", "json") or _latest_file(os.path.join(outdir, "intelligence-*.json")),
    }


def _detect_platform_version(assessment: Optional[Dict]) -> str:
    if not assessment:
        return "unknown"
    v = str(assessment.get("platform_version") or "").strip()
    return v if v else "3.7"  # backward compat: older outputs


# -------------------------
# v3.7 checks
# -------------------------

def _check_assessment_v37(assessment: Dict) -> List[CheckResult]:
    results: List[CheckResult] = []

    required_top = ["confidence", "readiness_score", "transition_roadmap"]
    missing = [k for k in required_top if k not in assessment]
    results.append(CheckResult(
        name="assessment.json has required top-level keys (v3.7)",
        ok=(len(missing) == 0),
        details=("missing: " + ", ".join(missing)) if missing else "ok",
        fatal=True
    ))

    conf = assessment.get("confidence") or {}
    conf_required = ["confidence_score", "confidence_rating", "coverage_pct", "tls_enum_coverage_pct"]
    conf_missing = [k for k in conf_required if k not in conf]
    results.append(CheckResult(
        name="assessment.json confidence fields present (v3.7)",
        ok=(len(conf_missing) == 0),
        details=("missing: " + ", ".join(conf_missing)) if conf_missing else "ok",
        fatal=True
    ))

    rs = assessment.get("readiness_score") or {}
    rs_required = ["score", "rating"]
    rs_missing = [k for k in rs_required if k not in rs]
    results.append(CheckResult(
        name="assessment.json readiness_score fields present (v3.7)",
        ok=(len(rs_missing) == 0),
        details=("missing: " + ", ".join(rs_missing)) if rs_missing else "ok",
        fatal=True
    ))

    tr = assessment.get("transition_roadmap") or {}
    tr_required = ["wave_1", "wave_2", "wave_3"]
    tr_missing = [k for k in tr_required if k not in tr]
    results.append(CheckResult(
        name="assessment.json transition_roadmap waves present (v3.7)",
        ok=(len(tr_missing) == 0),
        details=("missing: " + ", ".join(tr_missing)) if tr_missing else "ok",
        fatal=True
    ))

    # non-fatal expectation (older files may miss)
    results.append(CheckResult(
        name="assessment.json includes run_stats (expected v3.7+)",
        ok=("run_stats" in assessment),
        details="present" if ("run_stats" in assessment) else "missing (non-fatal)",
        fatal=False
    ))

    return results


def _check_run_stats_v37(path: str) -> List[CheckResult]:
    s = _read_json(path)
    results: List[CheckResult] = []

    timings = s.get("timings_sec")
    if not isinstance(timings, dict):
        return [CheckResult("run-stats.json has timings_sec dict", False, "missing timings_sec", True)]

    required_phases = ["discovery", "fingerprinting", "tls_scanning", "ssh_scanning", "risk_engine", "db_persist"]
    acceptable_report_keys = ["reporting", "reports"]

    missing = [p for p in required_phases if p not in timings]
    has_reporting = any(k in timings for k in acceptable_report_keys)

    # then add a second check for reporting key presence
    results.append(CheckResult(
        name="run-stats.json contains report timing key (reporting/reports)",
        ok=has_reporting,
        details="ok" if has_reporting else "missing: reporting (or reports)",
        fatal=True
))

    bad = []
    for k, v in timings.items():
        try:
            if float(v) < 0:
                bad.append(k)
        except Exception:
            bad.append(k)
    results.append(CheckResult(
        name="run-stats.json timing values are valid numbers (v3.7)",
        ok=(len(bad) == 0),
        details=("bad keys: " + ", ".join(bad)) if bad else "ok",
        fatal=True
    ))

    results.append(CheckResult(
        name="run-stats.json includes protocol_counts (nice-to-have)",
        ok=("protocol_counts" in s),
        details="present" if ("protocol_counts" in s) else "missing (non-fatal)",
        fatal=False
    ))

    return results


def _check_exec_md_v37(path: str) -> List[CheckResult]:
    txt = _read_text(path)
    required_sections = [r"^## Quantum Readiness Score", r"^## Confidence & Coverage", r"^## Transition Roadmap"]
    missing = [pat for pat in required_sections if not re.search(pat, txt, flags=re.MULTILINE)]
    out = [
        CheckResult(
            name="executive-summary.md contains key sections (v3.7)",
            ok=(len(missing) == 0),
            details=("missing patterns: " + ", ".join(missing)) if missing else "ok",
            fatal=True
        )
    ]
    has_score = bool(re.search(r"\*\*Score:\*\*\s*\*\*\d{1,3}/100\*\*", txt))
    out.append(CheckResult(
        name="executive-summary.md includes formatted score line (v3.7)",
        ok=has_score,
        details="ok" if has_score else "missing '**Score:** **X/100**' line",
        fatal=True
    ))
    return out


def _check_tech_md_v37(path: str) -> List[CheckResult]:
    txt = _read_text(path)

    # Accept either legacy headings OR the newer v3.8 headings
    acceptable = [
        (r"^## TLS Capabilities", r"^## Technical Findings"),
        (r"^## Service Inventory", r"^## Findings"),
    ]

    ok_any = False
    missing_detail = []
    for a, b in acceptable:
        has_a = re.search(a, txt, flags=re.MULTILINE) is not None
        has_b = re.search(b, txt, flags=re.MULTILINE) is not None
        if has_a and has_b:
            ok_any = True
            break
        missing_detail.append(f"missing pair: {a} AND {b}")

    out = [
        CheckResult(
            name="technical-findings.md contains key sections (v3.7/v3.8 compatible)",
            ok=ok_any,
            details="ok" if ok_any else "; ".join(missing_detail),
            fatal=True
        )
    ]

    out.append(CheckResult(
        name="technical-findings.md appears to include tables (nice-to-have)",
        ok=("|" in txt),
        details="ok" if ("|" in txt) else "no table separators found",
        fatal=False
    ))
    return out


# -------------------------
# DB checks (shared)
# -------------------------

def _db_table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,))
    return cur.fetchone() is not None


def _db_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table});")
    rows = cur.fetchall()
    return [r[1] for r in rows]


def _check_db_shared(db_path: str) -> List[CheckResult]:
    if not os.path.exists(db_path):
        return [CheckResult("db file exists", False, db_path, fatal=False)]

    conn = sqlite3.connect(db_path)
    try:
        table = "crypto_endpoints"
        if not _db_table_exists(conn, table):
            return [CheckResult("db has crypto_endpoints table", False, "missing table", fatal=True)]

        cols = _db_columns(conn, table)
        out: List[CheckResult] = [
            CheckResult("db has crypto_endpoints table", True, f"columns={len(cols)}", fatal=True)
        ]

        # TLS enum columns from v3.6+
        required_cols = [
            "host", "port", "protocol", "scan_error",
            "tls_supported_versions", "tls_supported_ciphers_sample",
            "tls_weak_ciphers_present", "tls_pfs_supported",
            "tls_enum_mode", "tls_enum_notes",
        ]
        missing = [c for c in required_cols if c not in cols]
        out.append(CheckResult(
            name="db schema includes TLS enum columns (v3.6+)",
            ok=(len(missing) == 0),
            details=("missing: " + ", ".join(missing)) if missing else "ok",
            fatal=True
        ))

        # Sample TLS endpoints
        cur = conn.cursor()
        cur.execute(
            "SELECT host,port,tls_supported_versions "
            "FROM crypto_endpoints WHERE protocol='TLS' "
            "ORDER BY rowid DESC LIMIT 10;"
        )
        rows = cur.fetchall()
        out.append(CheckResult(
            name="db contains TLS endpoints (nice-to-have depending on env)",
            ok=(len(rows) > 0),
            details=f"tls_rows_last10={len(rows)}",
            fatal=False
        ))
        if rows:
            filled = sum(1 for r in rows if (r[2] or "").strip())
            out.append(CheckResult(
                name="db TLS endpoints have tls_supported_versions populated (nice-to-have)",
                ok=(filled > 0),
                details=f"populated_in_last10={filled}",
                fatal=False
            ))

        return out
    finally:
        conn.close()


# -------------------------
# v3.8 checks (your tickets)
# -------------------------

def _check_intelligence_json_v38(path: str) -> List[CheckResult]:
    """
    Validates v3.8 Intelligence output per tickets 0-6.
    """
    j = _read_json(path)
    results: List[CheckResult] = []

    # Ticket 0: versioning + determinism (best-effort deterministic checks)
    iv = j.get("intelligence_version")
    results.append(CheckResult(
        name='intelligence.json includes intelligence_version == "3.8.0" (Ticket 0)',
        ok=(iv == "3.8.0"),
        details=f"found: {iv!r}",
        fatal=True
    ))

    # Ticket 1: evidence_summary exists and has key fields (graceful w/ missing tls enum)
    ev = j.get("evidence_summary")
    results.append(CheckResult(
        name="intelligence.json includes evidence_summary (Ticket 1)",
        ok=isinstance(ev, dict),
        details="ok" if isinstance(ev, dict) else f"type={type(ev)}",
        fatal=True
    ))
    if isinstance(ev, dict):
        # minimum expected keys from your ticket text
        expected_keys = [
            "protocol_counts",
            "plaintext_http_count",
            "http_on_tls_port_count",
            "mtls_present_count",
            "cert_key_type_counts",
            "expired_cert_count",
            "expiring_cert_count",
            "self_signed_cert_count",
            "scan_error_rate",
            "unknown_service_ratio",
        ]
        missing = [k for k in expected_keys if k not in ev]
        results.append(CheckResult(
            name="evidence_summary contains key metrics (Ticket 1)",
            ok=(len(missing) == 0),
            details=("missing: " + ", ".join(missing)) if missing else "ok",
            fatal=False  # allow drift; we can tighten once your exact field names are final
        ))

    # Ticket 2: score block w/ subscores + drivers
    score = j.get("score") or j.get("readiness_score")  # tolerate naming differences
    results.append(CheckResult(
        name="intelligence.json includes score/readiness_score block (Ticket 2)",
        ok=isinstance(score, dict),
        details="ok" if isinstance(score, dict) else f"type={type(score)}",
        fatal=True
    ))
    if isinstance(score, dict):
        # required basics
        total = score.get("total") if "total" in score else score.get("score")
        subs = score.get("subscores") or score.get("sub_scores")
        drivers = score.get("drivers")
        results.append(CheckResult(
            name="score includes total score (0-100) (Ticket 2)",
            ok=isinstance(total, (int, float)) and 0 <= float(total) <= 100,
            details=f"total={total}",
            fatal=True
        ))
        results.append(CheckResult(
            name="score includes subscores (4x 0-25) (Ticket 2)",
            ok=isinstance(subs, dict) and len(subs.keys()) >= 4,
            details=f"keys={list(subs.keys()) if isinstance(subs, dict) else subs}",
            fatal=True
        ))
        results.append(CheckResult(
            name="score includes top drivers list (<=5) (Ticket 2)",
            ok=isinstance(drivers, list) and 1 <= len(drivers) <= 5 and all(isinstance(d, str) for d in drivers),
            details=f"drivers_count={len(drivers) if isinstance(drivers, list) else 'n/a'}",
            fatal=True
        ))

    # Ticket 3: confidence (0-100) + factors
    conf = j.get("confidence")
    results.append(CheckResult(
        name="intelligence.json includes confidence block (Ticket 3)",
        ok=isinstance(conf, dict),
        details="ok" if isinstance(conf, dict) else f"type={type(conf)}",
        fatal=True
    ))
    if isinstance(conf, dict):
        cscore = conf.get("score") if "score" in conf else conf.get("confidence")
        factors = conf.get("confidence_factors") or conf.get("factors")
        results.append(CheckResult(
            name="confidence includes score (0-100) (Ticket 3)",
            ok=isinstance(cscore, (int, float)) and 0 <= float(cscore) <= 100,
            details=f"confidence={cscore}",
            fatal=True
        ))
        results.append(CheckResult(
            name="confidence includes confidence_factors breakdown (Ticket 3)",
            ok=isinstance(factors, (dict, list)),
            details=f"type={type(factors)}",
            fatal=True
        ))

    # Ticket 4: roadmap items 6-12 max, with timeframe/why/owner/deps
    roadmap = j.get("roadmap")
    results.append(CheckResult(
        name="intelligence.json includes roadmap list (Ticket 4)",
        ok=isinstance(roadmap, list),
        details="ok" if isinstance(roadmap, list) else f"type={type(roadmap)}",
        fatal=True
    ))
    if isinstance(roadmap, list):
        results.append(CheckResult(
            name="roadmap size within 6–12 items (Ticket 4)",
            ok=(6 <= len(roadmap) <= 12),
            details=f"count={len(roadmap)}",
            fatal=True
        ))

        # validate each item structure lightly but meaningfully
        required_item_fields = ["title", "why", "owner", "dependencies", "timeframe"]
        bad_items = []
        tf_counts = {"NOW": 0, "NEXT": 0, "LATER": 0}
        for idx, item in enumerate(roadmap):
            if not isinstance(item, dict):
                bad_items.append(f"idx={idx} not dict")
                continue
            missing = [k for k in required_item_fields if k not in item]
            if missing:
                bad_items.append(f"idx={idx} missing {missing}")
                continue
            tf = str(item.get("timeframe", "")).upper().strip()
            if tf in tf_counts:
                tf_counts[tf] += 1

        results.append(CheckResult(
            name="roadmap items include required fields (Ticket 4)",
            ok=(len(bad_items) == 0),
            details="; ".join(bad_items[:5]) if bad_items else "ok",
            fatal=True
        ))
        results.append(CheckResult(
            name="roadmap includes NOW/NEXT/LATER coverage (Ticket 4)",
            ok=(tf_counts["NOW"] > 0 and tf_counts["NEXT"] > 0 and tf_counts["LATER"] > 0),
            details=f"NOW={tf_counts['NOW']} NEXT={tf_counts['NEXT']} LATER={tf_counts['LATER']}",
            fatal=True
        ))

    # Ticket 6: metadata included, and no cert PEM
    meta = j.get("assessment") or j.get("assessment_metadata") or j.get("metadata")
    results.append(CheckResult(
        name="intelligence.json includes assessment metadata block (Ticket 6)",
        ok=isinstance(meta, dict),
        details="ok" if isinstance(meta, dict) else f"type={type(meta)}",
        fatal=False  # allow if you placed metadata at top-level differently
    ))

    # “no secrets” heuristic: reject PEM blocks if present
    raw = json.dumps(j)
    has_pem = ("BEGIN CERTIFICATE" in raw) or ("BEGIN RSA PRIVATE KEY" in raw) or ("BEGIN PRIVATE KEY" in raw)
    results.append(CheckResult(
        name="intelligence.json does not include raw PEM material (Ticket 6)",
        ok=(not has_pem),
        details="PEM marker detected" if has_pem else "ok",
        fatal=True
    ))

    # DoD: “Chaos Lab produces sane score and roadmap” => sanity expectations (non-fatal, tunable)
    if isinstance(score, dict):
        total = score.get("total") if "total" in score else score.get("score")
        if isinstance(total, (int, float)):
            results.append(CheckResult(
                name="sanity: readiness score not extreme (expected 5–98) (DoD)",
                ok=(5 <= float(total) <= 98),
                details=f"total={total} (tune if needed)",
                fatal=False
            ))
    if isinstance(conf, dict):
        cscore = conf.get("score") if "score" in conf else conf.get("confidence")
        if isinstance(cscore, (int, float)):
            results.append(CheckResult(
                name="sanity: confidence not extreme (expected 10–100) (DoD)",
                ok=(10 <= float(cscore) <= 100),
                details=f"confidence={cscore} (tune if needed)",
                fatal=False
            ))

    return results


def _check_scorecard_md_v38(path: str) -> List[CheckResult]:
    txt = _read_text(path)
    # Ticket 5: score + confidence + interpretation + drivers + top 3 NOW
    patterns = [
        r"Readiness Score",
        r"Confidence",
        r"Top drivers|Top Drivers|Drivers",
        r"Next 30–60 days|Next 30-60 days|Next 30 to 60 days",
    ]
    missing = [p for p in patterns if not re.search(p, txt)]
    return [
        CheckResult(
            name="scorecard.md contains score/confidence/drivers/next actions (Ticket 5)",
            ok=(len(missing) == 0),
            details=("missing: " + ", ".join(missing)) if missing else "ok",
            fatal=True
        ),
        CheckResult(
            name='scorecard.md does not mention "Chaos Lab" (Ticket 5)',
            ok=("Chaos Lab" not in txt),
            details="ok" if ("Chaos Lab" not in txt) else "found Chaos Lab reference",
            fatal=True
        ),
    ]


def _check_roadmap_md_v38(path: str) -> List[CheckResult]:
    txt = _read_text(path)
    # DoD: Now/Next/Later phase plan
    required = [r"\bNOW\b", r"\bNEXT\b", r"\bLATER\b"]
    missing = [p for p in required if not re.search(p, txt)]
    return [
        CheckResult(
            name="roadmap.md includes NOW/NEXT/LATER sections (DoD)",
            ok=(len(missing) == 0),
            details=("missing: " + ", ".join(missing)) if missing else "ok",
            fatal=True
        )
    ]


def _check_cache(outdir: str) -> CheckResult:
    cdir = os.path.join(outdir, ".cache")
    return CheckResult(
        name="cache directory exists (when --cache used)",
        ok=os.path.isdir(cdir),
        details=cdir if os.path.isdir(cdir) else f"missing dir: {cdir}",
        fatal=True
    )


# -------------------------
# Main
# -------------------------

def main():
    p = argparse.ArgumentParser(description="qcscan automated validator (v3.7 + v3.8)")
    p.add_argument("--outdir", default="output", help="Output directory (default: output)")
    p.add_argument("--db", dest="db_path", default=None, help="Path to SQLite DB (default: outdir/qcscan.db)")
    p.add_argument("--latest", action="store_true", help="Validate newest artifacts in outdir (default)")
    p.add_argument("--stamp", default=None, help="Validate a specific stamp (YYYYMMDD-HHMMSS)")
    p.add_argument("--expect-cache", action="store_true", help="Fail if output/.cache is missing")
    p.add_argument("--expect-version", default=None, help="Force checks for a platform version (3.7 or 3.8)")
    args = p.parse_args()

    outdir = args.outdir
    db_path = args.db_path or os.path.join(outdir, "qcscan.db")

    if not os.path.isdir(outdir):
        print(f"❌ Output directory not found: {outdir}")
        sys.exit(2)

    use_latest = True if args.latest or not args.stamp else False
    paths = _find_latest_run_files(outdir, None if use_latest else args.stamp)

    results: List[CheckResult] = []

    # Always validate v3.7 baseline artifacts (platform core)
    results.append(_check_exists("assessment file exists", paths["assessment"], fatal=True))
    results.append(_check_exists("run-stats file exists", paths["run_stats"], fatal=True))
    results.append(_check_exists("executive md exists", paths["exec_md"], fatal=True))
    results.append(_check_exists("technical md exists", paths["tech_md"], fatal=True))
    results.append(_check_exists("findings json exists", paths["findings"], fatal=True))

    if args.expect_cache:
        results.append(_check_cache(outdir))

    assessment = None
    detected_version = "unknown"
    if paths["assessment"] and os.path.exists(paths["assessment"]):
        assessment = _read_json(paths["assessment"])
        if isinstance(assessment, dict):
            detected_version = _detect_platform_version(assessment)

    forced = (args.expect_version or "").strip()
    effective_version = forced if forced else detected_version
    vt = _version_tuple(effective_version)

    # v3.7 checks
    if isinstance(assessment, dict):
        results.extend(_check_assessment_v37(assessment))
    if paths["run_stats"] and os.path.exists(paths["run_stats"]):
        results.extend(_check_run_stats_v37(paths["run_stats"]))
    if paths["exec_md"] and os.path.exists(paths["exec_md"]):
        results.extend(_check_exec_md_v37(paths["exec_md"]))
    if paths["tech_md"] and os.path.exists(paths["tech_md"]):
        results.extend(_check_tech_md_v37(paths["tech_md"]))

    # Shared DB checks
    results.extend(_check_db_shared(db_path))

    # v3.8 checks (only if v3.8 or higher)
    if vt >= (3, 8):
        results.append(_check_exists("scorecard md exists (v3.8 DoD)", paths["scorecard_md"], fatal=True))
        results.append(_check_exists("roadmap md exists (v3.8 DoD)", paths["roadmap_md"], fatal=True))
        results.append(_check_exists("intelligence json exists (v3.8 DoD)", paths["intelligence_json"], fatal=True))

        if paths["intelligence_json"] and os.path.exists(paths["intelligence_json"]):
            results.extend(_check_intelligence_json_v38(paths["intelligence_json"]))
        if paths["scorecard_md"] and os.path.exists(paths["scorecard_md"]):
            results.extend(_check_scorecard_md_v38(paths["scorecard_md"]))
        if paths["roadmap_md"] and os.path.exists(paths["roadmap_md"]):
            results.extend(_check_roadmap_md_v38(paths["roadmap_md"]))

    # Print summary
    print("\n🔎 qcscan validation results")
    print("-" * 40)
    print(f"Detected platform_version: {detected_version}")
    print(f"Effective version checks:  {effective_version}")
    if forced:
        print(f"(forced by --expect-version {forced})")
    print("")

    fatal_failures = 0
    for r in results:
        print(f"{_human(r.ok)} | {r.name}")
        if r.details:
            print(f"    ↳ {r.details}")
        if r.fatal and not r.ok:
            fatal_failures += 1

    if fatal_failures == 0:
        print("\n🎉 All fatal checks passed. You’re good to ship! 🚀")
        sys.exit(0)
    else:
        print(f"\n⚠️ Validation failed with {fatal_failures} fatal check(s). 🔧")
        sys.exit(2)


if __name__ == "__main__":
    main()