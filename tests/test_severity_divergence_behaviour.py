"""Phase 236 (XSURF-13, D-07/D-08): behaviour-derived severity-divergence gate.

Replaces the AST-literal ``_severity_divergence_keys`` gate that lived in
``tests/test_finding_title_bridge.py``. That gate read the literal ``severity=``
of every title-emission site inside ONE function; it was blind to a severity
that a helper, a map entry or a post-loop rewrite produces. This gate does not
read source to find severities. It RUNS both derivers
(``derive_report_findings`` and the dashboard deriver) on the same fixture rows
(``tests/fixtures/divergence_rows.py::FAMILY_ROWS``, one family at a time) and
diffs the per-(host, port) HIGH/CRITICAL multisets in both directions.

Keying is (host, port, severity), not title: the two surfaces use different
titles on purpose (228 D-02 / 236 D-05), so what must agree is how many
HIGH/CRITICAL findings each surface raises per host:port. Score-neutral
findings (category ``coverage_gap`` or any of
``SCORE_NEUTRAL_FINDING_CATEGORIES``) are excluded, as the evidence builder
excludes them.

Disposition rule: a surplus residual for key (host, port, severity) on one side
is dispositioned iff ANY of that side's titles carrying that key maps, by
longest-prefix match on SEVERITY_DIVERGENCES keys, to an entry whose ``side``
equals the residual's side AND whose ``families`` list contains the family
being evaluated. Anything else is undispositioned and fails the gate.

Fixture completeness is also derived at run time: every HIGH/CRITICAL (or
variable-severity) title prefix that the dashboard derivation module and
findings_evaluator.py emit, found with ``ast``, must be produced by at least
one family through the real derivers, or sit in ``_COVERAGE_EXEMPT`` with a
reason. The dashboard derivation file is located with
``inspect.getsourcefile`` so it follows the block when it moves.
"""
from __future__ import annotations

import ast
import importlib.util
import inspect
import itertools
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import pytest

from quirk.dashboard.api.finding_title_bridge import (
    DASHBOARD_TITLE_BRIDGE,
    SEVERITY_DIVERGENCES,
    UNBRIDGED_DASHBOARD_TITLES,
    canonical_cli_title,
)
from quirk.dashboard.api.routes.scan import (
    derive_dashboard_scoring_findings,
    findings_for_endpoint,
)
from quirk.engine.findings_evaluator import derive_report_findings
from quirk.intelligence.evidence import SCORE_NEUTRAL_FINDING_CATEGORIES
from tests.fixtures.divergence_rows import FAMILY_ROWS

_REPO = Path(__file__).resolve().parent.parent
_SA_PATH = _REPO / "scripts" / "score_attribution.py"
_EVALUATOR_PY = _REPO / "quirk" / "engine" / "findings_evaluator.py"
_DERIVATION_PY = Path(inspect.getsourcefile(findings_for_endpoint))
_TODOS_PENDING = _REPO / ".planning" / "todos" / "pending"


def _load_attribution():
    spec = importlib.util.spec_from_file_location("score_attribution_236", _SA_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_SA = _load_attribution()

Key = Tuple[str, int, str]
Residual = Tuple[Key, str]

# Titles that no endpoint row can produce (cfg-dependent or externally fed).
# Value is the reason. A key here that IS emitted by a family fails the gate.
_COVERAGE_EXEMPT: Dict[str, str] = {}


# ---------------------------------------------------------------------------
# Core: run both derivers, diff HIGH/CRITICAL multisets
# ---------------------------------------------------------------------------
def _is_scored(f: dict) -> bool:
    cat = f.get("category")
    if cat == "coverage_gap" or cat in SCORE_NEUTRAL_FINDING_CATEGORIES:
        return False
    return str(f.get("severity", "")).upper() in ("HIGH", "CRITICAL")


def _scored(rows: List[dict]) -> List[Tuple[Key, str]]:
    out = []
    for f in rows:
        if _is_scored(f):
            key = (f["host"], int(f.get("port") or 0), str(f["severity"]).upper())
            out.append((key, f["title"]))
    return out


def _all_titles(findings: List[dict]) -> List[str]:
    return [f["title"] for f in findings]


def residuals(rows, dash_deriver: Optional[Callable] = None
              ) -> Tuple[List[Residual], List[Residual], List[dict], List[dict]]:
    """(dashboard_only, report_only, dashboard_findings, report_findings)."""
    deriver = dash_deriver or derive_dashboard_scoring_findings
    dash = deriver(rows)
    rep = derive_report_findings(rows)
    d_only, r_only = _SA.severity_multiset_diff(_scored(dash), _scored(rep))
    return d_only, r_only, dash, rep


def _longest_prefix_entry(title: str, ledger) -> Optional[str]:
    for key in sorted(ledger, key=len, reverse=True):
        if title.startswith(key):
            return key
    return None


def _disposition_key(side: str, key: Key, family: str, side_findings: List[dict],
                     ledger) -> Optional[str]:
    """The SEVERITY_DIVERGENCES key dispositioning this residual, else None."""
    for k, title in _scored(side_findings):
        if k != key:
            continue
        entry_key = _longest_prefix_entry(title, ledger)
        if entry_key is None:
            continue
        entry = ledger[entry_key]
        if entry.get("side") == side and family in (entry.get("families") or []):
            return entry_key
    return None


def _evaluate_family(family: str, ledger, dash_deriver=None):
    """Returns (undispositioned, dispositioned_keys, all_residuals)."""
    rows = FAMILY_ROWS[family]()
    d_only, r_only, dash, rep = residuals(rows, dash_deriver)
    undisp, hit, every = [], set(), []
    for side, items, findings in (("dashboard_only", d_only, dash),
                                  ("report_only", r_only, rep)):
        for key, title in items:
            every.append((side, key, title))
            dk = _disposition_key(side, key, family, findings, ledger)
            if dk is None:
                undisp.append((side, key, title))
            else:
                hit.add(dk)
    return undisp, hit, every


def _fmt(family, side, key, title) -> str:
    host, port, sev = key
    canon = canonical_cli_title(title) or title
    return "%s: %s %s:%s %s %r" % (family, side, host, port, sev, canon)


# ---------------------------------------------------------------------------
# (1)-(3) The gate proper
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("family", list(FAMILY_ROWS))
def test_every_residual_is_dispositioned(family):
    undisp, _hit, _every = _evaluate_family(family, SEVERITY_DIVERGENCES)
    assert not undisp, (
        "undispositioned dashboard/report HIGH/CRITICAL divergence:\n  "
        + "\n  ".join(_fmt(family, s, k, t) for s, k, t in undisp)
        + "\nFix the severity, or file a todo and add a SEVERITY_DIVERGENCES entry "
        "(reason, todo, score_moving, side, families)."
    )


def test_no_stale_disposition():
    hits = set()
    for family in FAMILY_ROWS:
        _u, hit, _e = _evaluate_family(family, SEVERITY_DIVERGENCES)
        hits |= {(k, family) for k in hit}
    for key, entry in SEVERITY_DIVERGENCES.items():
        for family in entry.get("families", []):
            assert (key, family) in hits, (
                "stale SEVERITY_DIVERGENCES entry: %r lists family %r but that "
                "family no longer produces a residual mapped to it. A fixed "
                "divergence must delete its entry." % (key, family))


def test_disposition_entries_are_well_formed():
    assert SEVERITY_DIVERGENCES, "no dispositions at all; the gate would be vacuous"
    assert _TODOS_PENDING.is_dir(), "%s missing" % _TODOS_PENDING
    for key, entry in SEVERITY_DIVERGENCES.items():
        assert str(entry.get("reason", "")).strip(), "%r has no reason" % key
        todo = str(entry.get("todo", ""))
        assert todo.endswith(".md") and (_TODOS_PENDING / todo).is_file(), (
            "%r cites todo %r, not a file in .planning/todos/pending/" % (key, todo))
        assert isinstance(entry.get("score_moving"), bool), "%r score_moving not bool" % key
        assert entry.get("side") in ("dashboard_only", "report_only"), "%r bad side" % key
        fams = entry.get("families") or []
        assert fams, "%r has no families" % key
        assert all(f in FAMILY_ROWS for f in fams), "%r names an unknown family" % key


# ---------------------------------------------------------------------------
# (4) Fixture completeness, regenerated from source
# ---------------------------------------------------------------------------
def _prefix_of(node: ast.expr) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        prefix = ""
        for part in node.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                prefix += part.value
            else:
                break
        return prefix
    return None


def _called_names(func: ast.AST) -> set:
    names = set()
    for n in ast.walk(func):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                names.add(n.func.id)
    return names


def _sites_in(root: ast.AST) -> set:
    """Title prefixes whose severity is HIGH/CRITICAL or not a literal."""
    found = set()
    for node in ast.walk(root):
        if isinstance(node, ast.Call):
            kw = {k.arg: k.value for k in node.keywords if k.arg}
            if "title" not in kw:
                continue
            prefix = _prefix_of(kw["title"])
            if not prefix:
                continue
            if "severity" in kw:
                sev = kw["severity"]
                if (isinstance(sev, ast.Constant) and isinstance(sev.value, str)
                        and sev.value.upper() not in ("HIGH", "CRITICAL")):
                    continue
            elif not any(k.arg is None for k in node.keywords):
                continue  # no severity and no **unpack: not a finding site
            found.add(prefix)
    # f["severity"] = "HIGH" / f["title"] = "..." in-place rewrites
    last_sev: Optional[str] = None
    assigns = sorted(
        (n for n in ast.walk(root) if isinstance(n, ast.Assign)
         and len(n.targets) == 1 and isinstance(n.targets[0], ast.Subscript)),
        key=lambda n: n.lineno)
    for n in assigns:
        sub = n.targets[0].slice
        if not (isinstance(sub, ast.Constant) and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str)):
            continue
        if sub.value == "severity":
            last_sev = n.value.value.upper()
        elif sub.value == "title" and last_sev in ("HIGH", "CRITICAL"):
            found.add(n.value.value)
    return found


def _dashboard_sites(path: Path) -> set:
    """Sites in the functions reachable from the dashboard deriver entry points.

    Scoped to the call closure so motion/dar/hardware routes that live in the
    same file today (and are not part of the scored derivation) are not
    mistaken for scored sites; it keeps working once the block moves out.
    """
    tree = ast.parse(path.read_text())
    funcs = {n.name: n for n in tree.body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    todo = ["derive_dashboard_finding_items", "derive_dashboard_scoring_findings"]
    seen = set()
    while todo:
        name = todo.pop()
        if name in seen or name not in funcs:
            continue
        seen.add(name)
        todo.extend(_called_names(funcs[name]))
    assert "findings_for_endpoint" in seen, "closure lost findings_for_endpoint"
    out = set()
    for name in seen:
        out |= _sites_in(funcs[name])
    return out


def _evaluator_sites(path: Path) -> set:
    return _sites_in(ast.parse(path.read_text()))


def _emitted_titles() -> set:
    titles = set()
    for build in FAMILY_ROWS.values():
        rows = build()
        titles |= set(_all_titles(derive_dashboard_scoring_findings(rows)))
        titles |= set(_all_titles(derive_report_findings(rows)))
    return titles


def test_fixture_families_cover_every_high_critical_title_site():
    sites = _dashboard_sites(_DERIVATION_PY) | _evaluator_sites(_EVALUATOR_PY)
    assert len(sites) >= 20, "AST extraction found only %d sites: vacuous" % len(sites)
    emitted = _emitted_titles()

    def is_emitted(prefix):
        return any(t.startswith(prefix) for t in emitted)

    uncovered = sorted(p for p in sites if not is_emitted(p) and p not in _COVERAGE_EXEMPT)
    assert not uncovered, (
        "HIGH/CRITICAL (or variable-severity) title sites no FAMILY_ROWS family "
        "emits: %s. Add a family to tests/fixtures/divergence_rows.py, or an "
        "_COVERAGE_EXEMPT entry with a reason." % uncovered)
    for prefix, reason in _COVERAGE_EXEMPT.items():
        assert reason.strip(), "exemption %r has no reason" % prefix
        assert not is_emitted(prefix), "stale exemption: %r IS emitted" % prefix


# ---------------------------------------------------------------------------
# (5)-(7) Mutation proof (D-08)
# ---------------------------------------------------------------------------
_UNIQ = itertools.count()


def _mutate_nsec(text: str) -> str:
    anchor = '"NSEC": ("MEDIUM",'
    assert text.count(anchor) == 1, "M1 anchor must occur exactly once"
    return text.replace(anchor, '"NSEC": ("HIGH",')


def _mutate_drop_scan_error_guard(text: str) -> str:
    """Remove the scan_error guard (236-09, XSURF-09): errored TLS rows then
    derive dashboard-only HIGH findings again."""
    anchor = 'if getattr(ep, "scan_error", None):'
    assert text.count(anchor) == 1, "M3 anchor must occur exactly once"
    return text.replace(anchor, "if False:")


def _mutate_untrusted_ca(text: str) -> str:
    """Post-loop rewrite of the untrusted-CA severity (a divergence no literal
    ``severity=`` reveals). Inserted before the last statement of
    findings_for_endpoint, located with ast so it survives block moves."""
    tree = ast.parse(text)
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef)
          and n.name == "findings_for_endpoint"]
    assert len(fn) == 1
    last = fn[0].body[-1]
    assert isinstance(last, ast.Return)
    lines = text.splitlines(keepends=True)
    indent = " " * last.col_offset
    inject = [
        indent + "for _f in findings:\n",
        indent + "    if _f.title == 'TLS certificate issued by untrusted CA':\n",
        indent + "        _f.severity = 'HIGH'\n",
    ]
    lines[last.lineno - 1:last.lineno - 1] = inject
    return "".join(lines)


def _load_deriver_from_text(text: str, tmp_path: Path) -> Callable:
    path = tmp_path / ("mutated_derivation_%d.py" % next(_UNIQ))
    path.write_text(text)
    name = "mutated_derivation_%d" % next(_UNIQ)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.derive_dashboard_scoring_findings


_MUTATIONS = (
    ("M1_dnssec_nsec_to_high", _mutate_nsec, "dnssec_nsec"),
    ("M2_untrusted_ca_to_high", _mutate_untrusted_ca, "tls_untrusted_ca"),
    ("M3_drop_scan_error_guard", _mutate_drop_scan_error_guard,
     "tls_scan_error_with_fields"),
)


@pytest.mark.parametrize("label,mutate,family", _MUTATIONS, ids=[m[0] for m in _MUTATIONS])
def test_injected_mutations_turn_new_gate_red(label, mutate, family, tmp_path):
    original = _DERIVATION_PY.read_text()
    mutated = mutate(original)
    assert mutated != original, "mutation is vacuous"
    # Clean at HEAD for this family, so any residual is the mutation's.
    base_undisp, _h, base_all = _evaluate_family(family, SEVERITY_DIVERGENCES)
    assert not base_undisp and not base_all, "family %s not clean at HEAD" % family
    deriver = _load_deriver_from_text(mutated, tmp_path)
    undisp, _h, _all = _evaluate_family(family, SEVERITY_DIVERGENCES, deriver)
    assert undisp, "%s: the behaviour gate stayed green under the injection" % label


@pytest.mark.parametrize("label,mutate,family", _MUTATIONS, ids=[m[0] for m in _MUTATIONS])
def test_gate_is_red_with_empty_dispositions(label, mutate, family, tmp_path):
    """Non-vacuity leg (c): tied to the injected mutations, not to live divergences."""
    deriver = _load_deriver_from_text(mutate(_DERIVATION_PY.read_text()), tmp_path)
    undisp, _h, _all = _evaluate_family(family, {}, deriver)
    assert undisp, "%s: empty ledger did not turn the gate red" % label
    clean, _h, _all = _evaluate_family(family, {})
    assert not clean, "%s: family is not residual-free unmutated" % family


# -- the retired AST-literal gate, copied verbatim (path constant aside) ------
def _old_title_prefix_of(node: ast.expr) -> Optional[str]:
    return _prefix_of(node)


def _old_ast_sites(source: str, func_name: Optional[str] = None):
    tree = ast.parse(source)
    roots: List[ast.AST] = [tree]
    if func_name is not None:
        roots = [n for n in tree.body
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name == func_name]
        assert roots, "def %s not found" % func_name
    sites = []
    for root in roots:
        for node in ast.walk(root):
            if not isinstance(node, ast.Call):
                continue
            kw = {k.arg: k.value for k in node.keywords if k.arg}
            if "title" not in kw or "severity" not in kw:
                continue
            sev = kw["severity"]
            if not (isinstance(sev, ast.Constant) and isinstance(sev.value, str)):
                continue
            title = _old_title_prefix_of(kw["title"])
            if title is None:
                continue
            sites.append((node.lineno, title, sev.value.upper()))
    return sites


def _old_effective_report_severity(cli_title: str, severity: str) -> str:
    from quirk.engine.findings_evaluator import _normalize_finding
    return _normalize_finding({"title": cli_title, "severity": severity})["severity"]


def _old_severity_divergence_keys(dashboard_sites, report_sites) -> Dict[str, str]:
    found: Dict[str, str] = {}
    for key, cli_title in DASHBOARD_TITLE_BRIDGE.items():
        dash = {sev for _, t, sev in dashboard_sites if t == key}
        rep = {_old_effective_report_severity(cli_title, sev)
               for _, t, sev in report_sites if t == cli_title}
        if dash != rep:
            found[key] = "bridged: dashboard %s vs report %s" % (sorted(dash), sorted(rep))
    for key in UNBRIDGED_DASHBOARD_TITLES:
        dash = {sev for _, t, sev in dashboard_sites if t == key}
        if dash & {"HIGH", "CRITICAL"}:
            found[key] = "unbridged: dashboard %s, no report counterpart" % sorted(dash)
    return found


def _old_gate_keys(derivation_text: str) -> Dict[str, str]:
    dash = _old_ast_sites(derivation_text, "findings_for_endpoint")
    rep = _old_ast_sites(_EVALUATOR_PY.read_text())
    return _old_severity_divergence_keys(dash, rep)


@pytest.mark.parametrize("label,mutate,family", _MUTATIONS, ids=[m[0] for m in _MUTATIONS])
def test_old_ast_gate_is_blind_to_the_same_mutations(label, mutate, family):
    """Mutation leg (b): the retired gate's key set is unchanged by the injection."""
    original = _DERIVATION_PY.read_text()
    mutated = mutate(original)
    assert mutated != original, "mutation is vacuous"
    assert _old_gate_keys(mutated) == _old_gate_keys(original), (
        "%s: the old AST-literal gate DID react, so it is not blind to it" % label)


# ---------------------------------------------------------------------------
# Census
# ---------------------------------------------------------------------------
def _census() -> List[Tuple[str, str, Key, str]]:
    out = []
    for family in FAMILY_ROWS:
        _u, _h, every = _evaluate_family(family, SEVERITY_DIVERGENCES)
        for side, key, title in every:
            out.append((family, side, key, title))
    return out


def test_census_report():
    rows = _census()
    print("\nCENSUS (measured): %d residual(s) across %d families"
          % (len(rows), len(FAMILY_ROWS)))
    for family, side, (host, port, sev), title in rows:
        print("  %s | %s | %s:%s | %s | %s" % (family, side, host, port, sev, title))
