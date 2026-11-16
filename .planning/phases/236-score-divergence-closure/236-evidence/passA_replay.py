"""Phase 236 D-12/D-22: replay a scan run from a sqlite SNAPSHOT and print the report
vs dashboard headline plus the HIGH/CRITICAL multiset residuals.

Usage (from the repo root, never against a live DB):
    PYTHONPATH=. .venv/bin/python -I <this file> <snapshot.db> <scan_run_id>

Make the snapshot first:
    sqlite3 "file:<live.db>?mode=ro" ".backup <snapshot.db>"
"""
from __future__ import annotations

import os
import sys

# `python -I` ignores PYTHONPATH and the cwd; the repo root is the cwd by contract.
sys.path.insert(0, os.getcwd())

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.finding_derivation import derive_dashboard_scoring_findings
from quirk.dashboard.api.finding_title_bridge import canonical_cli_title
from quirk.engine.findings_evaluator import derive_report_findings
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.models import CryptoEndpoint
from scripts.score_attribution import severity_multiset_diff


def _hp_items(findings, canonicalise):
    items = []
    for f in findings:
        sev = f.get("severity")
        if sev not in ("HIGH", "CRITICAL"):
            continue
        title = f.get("title", "")
        if canonicalise:
            title = canonical_cli_title(title) or title
        key = (f.get("host"), f.get("port"), sev)
        items.append((key, title))
    return items


def main(snapshot: str, scan_run_id: str) -> int:
    engine = create_engine(f"sqlite:///file:{snapshot}?mode=ro&uri=true")
    with sessionmaker(bind=engine)() as db:
        eps = list(db.execute(
            select(CryptoEndpoint).where(CryptoEndpoint.scan_run_id == scan_run_id)
        ).scalars())
        print(f"endpoints: {len(eps)}")
        out = {}
        for name, deriver, canon in (
            ("report", derive_report_findings, False),
            ("dashboard", derive_dashboard_scoring_findings, True),
        ):
            findings = deriver(eps)
            ev = build_evidence_summary(eps, findings)
            sc = compute_readiness_score(ev)
            counts = ev.get("finding_severity_counts", {})
            print(
                f"{name:9s} score={sc['score']} CRITICAL={counts.get('CRITICAL', 0)} "
                f"HIGH={counts.get('HIGH', 0)} ceiling_reason={sc.get('rating_cap_reason')!r}"
            )
            out[name] = _hp_items(findings, canon)
        dash_only, rep_only = severity_multiset_diff(out["dashboard"], out["report"])
        print(f"dashboard-only residuals: {len(dash_only)}")
        for key, label in dash_only:
            print(f"  DASH-ONLY {key} {label}")
        print(f"report-only residuals: {len(rep_only)}")
        for key, label in rep_only:
            print(f"  REPORT-ONLY {key} {label}")
    engine.dispose()
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
