import argparse
import glob
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str = ""
    fatal: bool = True  # if False, will not fail exit code


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_json(path: str):
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


def _find_latest_run_files(outdir: str, stamp: Optional[str]) -> Dict[str, Optional[str]]:
    def by_stamp(prefix: str, ext: str) -> Optional[str]:
        if not stamp:
            return None
        p = os.path.join(outdir, f"{prefix}-{stamp}.{ext}")
        return p if os.path.exists(p) else None

    return {
        "assessment": by_stamp("assessment", "json") or _latest_file(os.path.join(outdir, "assessment-*.json")),
        "findings": by_stamp("findings", "json") or _latest_file(os.path.join(outdir, "findings-*.json")),
        "run_stats": by_stamp("run-stats", "json") or _latest_file(os.path.join(outdir, "run-stats-*.json")),
        "exec_md": by_stamp("executive-summary", "md") or _latest_file(os.path.join(outdir, "executive-summary-*.md")),
        "tech_md": by_stamp("technical-findings", "md") or _latest_file(os.path.join(outdir, "technical-findings-*.md")),
    }


def _check_exists(name: str, path: Optional[str]) -> CheckResult:
    ok = bool(path and os.path.exists(path))
    return CheckResult(name=name, ok=ok, details=_maybe(path), fatal=True)


def _detect_platform_version(assessment: Dict) -> str:
    v = str(assessment.get("platform_version") or "").strip()
    if v:
        return v
    # backward compat for older v3.7 outputs
    return "3.7"


def _version_tuple(v: str) -> Tuple[int, int]:
    m = re.match(r"^\s*(\d+)\.(\d+)", v)
    if not m:
        return (0, 0)
    return (int(m.group(1)), int(m.group(2)))


def _check_assessment_common(a: Dict) -> List[CheckResult]:
    results: List[CheckResult] = []

    required_top = ["confidence", "readiness_score", "transition_roadmap"]
    missing = [k for k in required_top if k not in a]
    results.append(CheckResult(
        name="assessment.json has required top-level keys",
        ok=(len(missing) == 0),
        details=("missing: " + ", ".join(missing)) if missing else "ok",
        fatal=True
    ))

    conf = a.get("confidence") or {}
    conf_required = ["confidence_score", "confidence_rating", "coverage_pct", "tls_enum_coverage_pct"]
    conf_missing = [k for k in conf_required if k not in conf]
    results.append(CheckResult(
        name="assessment.json confidence block fields",
        ok=(len(conf_missing) == 0),
        details=("missing: " + ", ".join(conf_missing)) if conf_missing else "ok",
        fatal=True
    ))

    rs = a.get("readiness_score") or {}
    rs_required = ["score", "rating"]
    rs_missing = [k for k in rs_required if k not in rs]
    results.append(CheckResult(
        name="assessment.json readiness_score fields",
        ok=(len(rs_missing) == 0),
        details=("missing: " + ", ".join(rs_missing)) if rs_missing else "ok",
        fatal=True
    ))

    tr = a.get("transition_roadmap") or {}
    tr_required = ["wave_1", "wave_2", "wave_3"]
    tr_missing = [k for k in tr_required if k not in tr]
    results.append(CheckResult(
        name="assessment.json transition_roadmap waves exist",
        ok=(len(tr_missing) == 0),
        details=("missing: " + ", ".join(tr_missing)) if tr_missing else "ok",
        fatal=True
    ))

    # v3.7+: run_stats expected but treat as non-fatal for backward compat
    rs_stats = a.get("run_stats")
    results.append(CheckResult(
        name="assessment.json includes run_stats (v3.7+)",
        ok=(rs_stats is not None),
        details="present" if rs_stats is not None else "missing (non-fatal for older outputs)",
        fatal=False
    ))

    return results


def _check_assessment_v38(a: Dict) -> List[CheckResult]:
    """
    v3.8 checks: keep these light + useful.
    If you have specific 3.8 tickets, tell me what fields you added and I’ll make these stricter.
    """
    results: List[CheckResult] = []

    # v3.8: versioned outputs recommended
    pv = a.get("platform_version")
    sv = a.get("schema_version")

    results.append(CheckResult(
        name="assessment.json includes platform_version (v3.8)",
        ok=(pv is not None and str(pv).strip() != ""),
        details=str(pv),
        fatal=False  # allow if you haven't rolled this everywhere yet
    ))
    results.append(CheckResult(
        name="assessment.json includes schema_version (v3.8)",
        ok=(sv is not None),
        details=str(sv),
        fatal=False
    ))

    return results


def _check_run_stats(path: str) -> List[CheckResult]:
    results: List[CheckResult] = []
    s = _read_json(path)

    if "timings_sec" not in s or not isinstance(s["timings_sec"], dict):
        results.append(CheckResult(
            name="run-stats.json has timings_sec dict",
            ok=False,
            details="missing timings_sec",
            fatal=True
        ))
        return results

    timings = s["timings_sec"]
    required_phases = ["discovery", "fingerprinting", "tls_scanning", "ssh_scanning", "risk_engine", "reporting"]
    missing = [p for p in required_phases if p not in timings]
    results.append(CheckResult(
        name="run-stats.json contains required phase timings",
        ok=(len(missing) == 0),
        details=("missing: " + ", ".join(missing)) if missing else "ok",
        fatal=True
    ))

    bad = []
    for k, v in timings.items():
        try:
            fv = float(v)
            if fv < 0:
                bad.append(k)
        except Exception:
            bad.append(k)
    results.append(CheckResult(
        name="run-stats.json timing values are valid numbers",
        ok=(len(bad) == 0),
        details=("bad keys: " + ", ".join(bad)) if bad else "ok",
        fatal=True
    ))

    results.append(CheckResult(
        name="run-stats.json includes protocol_counts",
        ok=("protocol_counts" in s),
        details="present" if "protocol_counts" in s else "missing (non-fatal)",
        fatal=False
    ))

    return results


def _check_markdown_exec(path: str) -> List[CheckResult]:
    txt = _read_text(path)

    required_sections = [r"^## Quantum Readiness Score", r"^## Confidence & Coverage", r"^## Transition Roadmap"]
    missing = [pat for pat in required_sections if not re.search(pat, txt, flags=re.MULTILINE)]

    out = [
        CheckResult(
            name="executive-summary.md contains key sections",
            ok=(len(missing) == 0),
            details=("missing patterns: " + ", ".join(missing)) if missing else "ok",
            fatal=True
        )
    ]

    has_score = bool(re.search(r"\*\*Score:\*\*\s*\*\*\d{1,3}/100\*\*", txt))
    out.append(CheckResult(
        name="executive-summary.md includes formatted score line",
        ok=has_score,
        details="ok" if has_score else "missing '**Score:** **X/100**' line",
        fatal=True
    ))
    return out


def _check_markdown_tech(path: str) -> List[CheckResult]:
    txt = _read_text(path)

    required_sections = [r"^## TLS Capabilities", r"^## Technical Findings"]
    missing = [pat for pat in required_sections if not re.search(pat, txt, flags=re.MULTILINE)]

    out = [
        CheckResult(
            name="technical-findings.md contains key sections",
            ok=(len(missing) == 0),
            details=("missing patterns: " + ", ".join(missing)) if missing else "ok",
            fatal=True
        )
    ]
    out.append(CheckResult(
        name="technical-findings.md appears to include tables",
        ok=("|" in txt),
        details="ok" if ("|" in txt) else "no table separators found",
        fatal=False
    ))
    return out


def _db_table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,))
    return cur.fetchone() is not None


def _db_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table});")
    rows = cur.fetchall()
    return [r[1] for r in rows]


def _check_db(db_path: str) -> List[CheckResult]:
    if not os.path.exists(db_path):
        return [CheckResult(name="db file exists", ok=False, details=db_path, fatal=False)]

    conn = sqlite3.connect(db_path)
    try:
        table = "crypto_endpoints"
        if not _db_table_exists(conn, table):
            return [CheckResult(name="db has crypto_endpoints table", ok=False, details="missing table", fatal=True)]

        cols = _db_columns(conn, table)
        out = [
            CheckResult(name="db has crypto_endpoints table", ok=True, details=f"columns={len(cols)}", fatal=True)
        ]

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

        cur = conn.cursor()
        cur.execute(
            "SELECT host,port,tls_supported_versions "
            "FROM crypto_endpoints WHERE protocol='TLS' "
            "ORDER BY rowid DESC LIMIT 10;"
        )
        rows = cur.fetchall()
        out.append(CheckResult(
            name="db contains TLS endpoints",
            ok=(len(rows) > 0),
            details=f"tls_rows_last10={len(rows)}",
            fatal=False
        ))
        if rows:
            filled = sum(1 for r in rows if (r[2] or "").strip())
            out.append(CheckResult(
                name="db TLS endpoints have tls_supported_versions populated",
                ok=(filled > 0),
                details=f"populated_in_last10={filled}",
                fatal=False
            ))

        return out
    finally:
        conn.close()


def _check_cache(outdir: str) -> CheckResult:
    cdir = os.path.join(outdir, ".cache")
    return CheckResult(
        name="cache directory exists (when --cache used)",
        ok=os.path.isdir(cdir),
        details=cdir if os.path.isdir(cdir) else f"missing dir: {cdir}",
        fatal=True
    )


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
    results.append(_check_exists("assessment file exists", paths["assessment"]))
    results.append(_check_exists("run-stats file exists", paths["run_stats"]))
    results.append(_check_exists("executive md exists", paths["exec_md"]))
    results.append(_check_exists("technical md exists", paths["tech_md"]))
    results.append(_check_exists("findings json exists", paths["findings"]))

    if args.expect_cache:
        results.append(_check_cache(outdir))

    # Load assessment (if present) to detect version
    detected_version = "unknown"
    assessment = None
    if paths["assessment"] and os.path.exists(paths["assessment"]):
        assessment = _read_json(paths["assessment"])
        detected_version = _detect_platform_version(assessment)

    expect_version = (args.expect_version or detected_version).strip()
    vt = _version_tuple(expect_version)

    # Common checks for 3.7+
    if assessment is not None:
        results.extend(_check_assessment_common(assessment))

    if paths["run_stats"] and os.path.exists(paths["run_stats"]):
        results.extend(_check_run_stats(paths["run_stats"]))

    if paths["exec_md"] and os.path.exists(paths["exec_md"]):
        results.extend(_check_markdown_exec(paths["exec_md"]))

    if paths["tech_md"] and os.path.exists(paths["tech_md"]):
        results.extend(_check_markdown_tech(paths["tech_md"]))

    # Version-specific checks
    if assessment is not None and vt >= (3, 8):
        results.extend(_check_assessment_v38(assessment))

    # DB checks (applies to both)
    results.extend(_check_db(db_path))

    # Print header
    print("\n🔎 qcscan validation results")
    print("-" * 34)
    print(f"Detected platform_version: {detected_version}")
    if args.expect_version:
        print(f"Forced expect_version: {args.expect_version}")
    print("")

    # Print checks
    fatal_failures = 0
    for r in results:
        print(f"{_human(r.ok)} | {r.name}")
        if r.details:
            print(f"    ↳ {r.details}")
        if r.fatal and not r.ok:
            fatal_failures += 1

    if fatal_failures == 0:
        print("\n🎉 All fatal checks passed. Ship it! 🚀")
        sys.exit(0)
    else:
        print(f"\n⚠️ Validation failed with {fatal_failures} fatal check(s). 🔧")
        sys.exit(2)


if __name__ == "__main__":
    main()