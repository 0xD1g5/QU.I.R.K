#!/usr/bin/env python3
"""Score parity check across the three surfaces that print a readiness score.

Inputs (all produced by one scan):
  * the newest ``intelligence-*.json``        -> ``score.total``
  * the HTML report headline score            -> ``--html-score``
  * ``GET /api/scan/latest`` (dashboard JSON) -> ``score.score``

Rules:
  * SCORE-STRICT: intel == html. Same pipeline; any difference is a bug and is
    never attributable.
  * SCORE-PARITY: dashboard == html, OR every finding that differs between the
    dashboard and the report is part of the disclosed divergence set, with both
    numbers and one ``ATTRIBUTED:`` line per item. An item outside the set is
    ``UNATTRIBUTED:`` and fails. Unknown is never green: if the bridge module
    cannot be imported while the scores differ, the check fails.

Finding sources. The dashboard side is every finding array in
``ScanLatestResponse`` (findings, identity_findings, motion_findings,
dar_findings, hardware_findings). The report side is the ``findings-*.json``
the scan writes beside the intelligence file (a list of objects with ``title``
and ``severity``); the intelligence JSON itself carries no findings list
(its keys are assessment, calibration, confidence, evidence_summary,
intelligence_version, roadmap, score), so ``--findings-json`` supplies it and a
top-level ``findings`` key in the intelligence JSON is used only as a fallback.

Divergence set. The code half is read live from the INSTALLED package
(``quirk.dashboard.api.finding_title_bridge``: ``SEVERITY_DIVERGENCES``,
``UNBRIDGED_DASHBOARD_TITLES``, ``canonical_cli_title``). Their keys are title
PREFIXES, matched with ``startswith`` longest-first against the ORIGINAL
dashboard title. The other half is an optional ``--divergence-set`` JSON file:
``{"patterns": [{"match": "<substring>", "phrase": "<user-term phrase>"}]}``.

Exit 0 only when SCORE-STRICT passes and SCORE-PARITY is equal or attributed.
Stdlib only.
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import sys
from contextlib import redirect_stdout
from typing import Dict, List, Optional, Tuple

DASHBOARD_ARRAYS = (
    "findings", "identity_findings", "motion_findings", "dar_findings",
    "hardware_findings",
)


class Bridge:
    """The code half of the divergence set (real or stubbed)."""

    def __init__(self, severity_divergences, unbridged, canonical):
        self.severity_divergences = severity_divergences
        self.unbridged = unbridged
        self.canonical = canonical

    def prefix_key(self, title: str) -> Optional[str]:
        keys = sorted(
            set(self.severity_divergences) | set(self.unbridged),
            key=len, reverse=True)
        for key in keys:
            if title.startswith(key):
                return key
        return None


def load_bridge() -> Optional[Bridge]:
    try:
        from quirk.dashboard.api import finding_title_bridge as b
    except ImportError:
        return None
    return Bridge(b.SEVERITY_DIVERGENCES, b.UNBRIDGED_DASHBOARD_TITLES,
                  b.canonical_cli_title)


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt(value) -> str:
    n = _num(value)
    if n is None:
        return str(value)
    return str(int(n)) if n == int(n) else str(n)


def dashboard_items(dash: dict, bridge: Optional[Bridge]) -> List[Tuple[str, str, str]]:
    items = []
    for name in DASHBOARD_ARRAYS:
        for f in dash.get(name) or []:
            orig = f.get("title", "")
            canon = None
            if bridge is not None:
                canon = bridge.canonical(orig)
            items.append((orig, canon or orig, str(f.get("severity", ""))))
    return items


def evaluate(intel, html, dash_score, dash_items, report_items, bridge,
             patterns) -> Tuple[List[str], bool]:
    """Return (output lines, ok). ``report_items`` is [(title, severity)]."""
    out = ["SCORES: intel=%s html=%s dashboard=%s"
           % (_fmt(intel), _fmt(html), _fmt(dash_score))]
    strict_ok = _num(intel) is not None and _num(intel) == _num(html)
    out.append("SCORE-STRICT: intel==html " + ("PASS" if strict_ok else "FAIL"))

    if _num(dash_score) is not None and _num(dash_score) == _num(html):
        out.append("SCORE-PARITY: equal dashboard=%s report=%s"
                   % (_fmt(dash_score), _fmt(html)))
        return out, strict_ok

    d, h = _fmt(dash_score), _fmt(html)
    if bridge is None:
        out.append("SCORE-PARITY: FAIL attribution unavailable "
                   "dashboard=%s report=%s" % (d, h))
        return out, False

    dash_side = collections.defaultdict(list)
    for orig, canon, sev in dash_items:
        dash_side[(canon, sev)].append(orig)
    rep_side = collections.defaultdict(list)
    for title, sev in report_items:
        rep_side[(title, sev)].append(title)

    dash_only, rep_only = [], []
    for key in set(dash_side) | set(rep_side):
        nd, nr = len(dash_side.get(key, [])), len(rep_side.get(key, []))
        if nd > nr:
            dash_only += [(key, o) for o in dash_side[key][nr:]]
        elif nr > nd:
            rep_only += [(key, key[0])] * (nr - nd)

    def pattern_for(*titles):
        for p in patterns:
            needle = p.get("match", "").lower()
            if needle and any(needle in t.lower() for t in titles):
                return p.get("phrase") or p["match"]
        return None

    lines, unattributed = [], []
    counterpart: Dict[str, str] = {}
    other_sev: Dict[str, str] = {}
    for (canon, sev), _o in rep_only:
        other_sev.setdefault(canon, sev)
    dash_sev_by_canon = {}
    for (canon, sev), _o in dash_only:
        dash_sev_by_canon.setdefault(canon, sev)

    for (canon, sev), orig in dash_only:
        why = bridge.prefix_key(orig) or pattern_for(orig, canon)
        if why:
            counterpart[canon] = why
            lines.append(
                "ATTRIBUTED: dashboard=%s report=%s | %s | %s | "
                "dashboard-severity=%s report-severity=%s"
                % (d, h, why, orig, sev, other_sev.get(canon, "absent")))
        else:
            unattributed.append(
                "UNATTRIBUTED: %s | dashboard-severity=%s report-severity=%s"
                % (orig, sev, other_sev.get(canon, "absent")))
    for (title, sev), _o in rep_only:
        why = counterpart.get(title) or pattern_for(title)
        if why:
            lines.append(
                "ATTRIBUTED: dashboard=%s report=%s | %s | %s | "
                "dashboard-severity=%s report-severity=%s"
                % (d, h, why, title, dash_sev_by_canon.get(title, "absent"),
                   sev))
        else:
            unattributed.append(
                "UNATTRIBUTED: %s | dashboard-severity=%s report-severity=%s"
                % (title, dash_sev_by_canon.get(title, "absent"), sev))

    if not dash_only and not rep_only:
        unattributed.append("UNATTRIBUTED: score gap with identical finding sets")
    if unattributed:
        out += unattributed
        out.append("SCORE-PARITY: FAIL unattributed dashboard=%s report=%s"
                   % (d, h))
        return out, False
    out += lines
    out.append("SCORE-PARITY: attributed dashboard=%s report=%s items=%d"
               % (d, h, len(lines)))
    return out, strict_ok


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def run(args, bridge) -> int:
    dash = _load(args.dashboard_json)
    intel_doc = _load(args.intel_json)
    intel = (intel_doc.get("score") or {}).get("total")
    dash_score = (dash.get("score") or {}).get("score")
    if args.findings_json:
        rep = _load(args.findings_json)
    else:
        rep = intel_doc.get("findings") or []
    report_items = [(f.get("title", ""), str(f.get("severity", "")))
                    for f in rep]
    patterns = []
    if args.divergence_set:
        patterns = _load(args.divergence_set).get("patterns", [])
    lines, ok = evaluate(intel, args.html_score, dash_score,
                         dashboard_items(dash, bridge), report_items, bridge,
                         patterns)
    print("\n".join(lines))
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# Self-test: stub bridge, no quirk install needed
# ---------------------------------------------------------------------------

LEGACY_CANON = "Legacy TLS versions allowed (TLS 1.0/1.1)"


def _stub(prefix_keys=(), unbridged=()):
    def canonical(title):
        if title.startswith("Legacy TLS version: "):
            return LEGACY_CANON
        return None
    return Bridge({k: {} for k in prefix_keys}, {k: "" for k in unbridged},
                  canonical)


def self_test() -> int:
    legacy = ("Legacy TLS version: TLSv1.0", LEGACY_CANON, "HIGH")
    cases = []

    def case(name, expect_ok, must, must_not, **kw):
        buf = io.StringIO()
        with redirect_stdout(buf):
            lines, ok = evaluate(**kw)
            print("\n".join(lines))
        text = buf.getvalue()
        good = (ok == expect_ok and all(m in text for m in must)
                and not any(m in text for m in must_not))
        cases.append((name, good))

    base = dict(patterns=[])
    case("equal", True, ["SCORE-PARITY: equal"], ["ATTRIBUTED"],
         intel=80, html=80, dash_score=80, dash_items=[legacy],
         report_items=[(LEGACY_CANON, "HIGH")], bridge=_stub(), **base)
    case("prefix-key", True,
         ["ATTRIBUTED: dashboard=69 report=84 | Legacy TLS version: ",
          "dashboard-severity=HIGH report-severity=LOW",
          "SCORE-PARITY: attributed dashboard=69 report=84 items=2"],
         ["UNATTRIBUTED"],
         intel=84, html=84, dash_score=69, dash_items=[legacy],
         report_items=[(LEGACY_CANON, "LOW")],
         bridge=_stub(prefix_keys=["Legacy TLS version: "]), **base)
    case("pattern", True, ["ATTRIBUTED:", "legacy tls phrase"],
         ["UNATTRIBUTED"],
         intel=84, html=84, dash_score=69, dash_items=[legacy],
         report_items=[(LEGACY_CANON, "LOW")], bridge=_stub(),
         patterns=[{"match": "legacy tls", "phrase": "legacy tls phrase"}])
    case("unattributed", False,
         ["UNATTRIBUTED: Some new finding", "SCORE-PARITY: FAIL unattributed"],
         [],
         intel=84, html=84, dash_score=69,
         dash_items=[("Some new finding", "Some new finding", "HIGH")],
         report_items=[], bridge=_stub(prefix_keys=["Legacy TLS version: "]),
         **base)
    case("strict-mismatch", False, ["SCORE-STRICT: intel==html FAIL"], [],
         intel=80, html=84, dash_score=84, dash_items=[], report_items=[],
         bridge=_stub(), **base)
    q = "Quantum-vulnerable algorithm: RSA-2048"
    case("unbridged-prefix", True,
         ["ATTRIBUTED: dashboard=70 report=75 | Quantum- |"],
         ["UNATTRIBUTED"],
         intel=75, html=75, dash_score=70, dash_items=[(q, q, "HIGH")],
         report_items=[], bridge=_stub(unbridged=["Quantum-"]), **base)
    passed = sum(1 for _n, g in cases if g)
    for name, good in cases:
        print("  %s %s" % ("ok  " if good else "FAIL", name))
    print("self-test: %d/%d" % (passed, len(cases)))
    return 0 if passed == len(cases) == 6 else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dashboard-json")
    ap.add_argument("--intel-json")
    ap.add_argument("--findings-json",
                    help="findings-*.json written beside the intelligence file")
    ap.add_argument("--html-score", type=float)
    ap.add_argument("--divergence-set")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if not (args.dashboard_json and args.intel_json
            and args.html_score is not None):
        ap.error("--dashboard-json, --intel-json and --html-score are required")
    return run(args, load_bridge())


if __name__ == "__main__":
    sys.exit(main())
