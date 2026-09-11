"""Phase 184.4, SCORE-05, D-12: build_evidence_summary() call-site
disposition scan gate.

D-08 (recorded here, not re-litigated at every call site): `findings`
remains an OPTIONAL parameter of
`quirk.intelligence.evidence.build_evidence_summary()`
(`findings: Optional[Iterable[Mapping[str, Any]]] = None`). It is
deliberately NOT made required -- 13 production and roughly 68 test call
sites make that a large, disruptive change that converts a real omission
into a deliberate `None` without making the `None` itself any more correct
at any individual site. This gate is the enforcement that replaces the
signature change: every findings-less call site must be dispositioned here,
by name, with a stated reason -- or the gate fails. A future contributor
should find that reasoning in this docstring rather than re-deriving it or
re-proposing the signature change.

Same run-time-derivation discipline as
`tests/test_band_producer_scan_gate.py` and
`tests/test_timestamp_serialization_gate.py`: `Path.rglob("*.py")` over
`quirk/` at TEST RUN TIME, never a hard-coded call-site file list. A ninth
findings-less site added in some future phase fails this gate with zero
list edits required to the DETECTOR -- only a ledger entry (if legitimate)
or a code fix (if not).

Detection is purely SYNTACTIC (matches the isoformat detector's approach in
`tests/test_timestamp_serialization_gate.py`): a call is flagged
findings-less when neither a `findings=<non-None>` keyword nor a
non-`None` second positional argument is present in the call's source
text. A variable that happens to be `None` at runtime (e.g.
`findings=maybe_none_var`) is NOT detectable statically -- stated here
rather than silently claimed away. The compensating, runtime-behavioural
controls are the D-13 regression
(`tests/test_score_severity_floor_regression.py`) and the dashboard route
tests added in plan 184.4-07
(`tests/test_dashboard_api.py::test_*_severity_floor*`), both of which
exercise the real call at runtime rather than its static shape.

The detector handles BOTH call forms:
  1. bare name -- `build_evidence_summary(endpoints, findings)`
  2. attribute access -- `evidence.build_evidence_summary(endpoints, findings)`
All 13 real call sites currently use the bare-name form (a direct `from
quirk.intelligence.evidence import build_evidence_summary` import), but the
detector must not assume that stays true -- an attribute-access call site
added later would otherwise be invisible. Both forms are exercised by
dedicated synthetic tests below.
"""
from __future__ import annotations

import ast
from pathlib import Path

import quirk

_REPO_ROOT = Path(quirk.__file__).resolve().parent.parent
_QUIRK_ROOT = Path(quirk.__file__).resolve().parent

_TARGET_FUNC_NAME = "build_evidence_summary"

# ---------------------------------------------------------------------------
# Disposition ledger.
#
# Keyed "<repo-relative-path>:<enclosing-function-name>". Reasons sourced
# from plan 184.4-07's verified per-site disposition table
# (184.4-07-SUMMARY.md "Site 2 Disposition Table"), not invented here.
# Multiple call sites sharing one enclosing function collapse to one ledger
# key, matching the isoformat gate's keying convention.
# ---------------------------------------------------------------------------
_DISPOSITIONS: dict[str, str] = {
    "quirk/intelligence/trends.py:_score_for_session": (
        "D-07 (184.4), verified in 184.4-07-SUMMARY.md -- the ONLY consumer "
        "of this function's return value is `return score_dict[\"score\"]` "
        "immediately below the call; no caller of _score_for_session() ever "
        "reads a rating/band from it, so a severity-blind evidence summary "
        "here can never diverge from a report band. Re-confirmed by plan "
        "184.4-07 (not just trusted from 184.4-CONTEXT.md's earlier guess)."
    ),
    "quirk/dashboard/api/routes/trends.py:get_trends_timeline": (
        "D-07 (184.4), verified in 184.4-07-SUMMARY.md -- "
        "TrendSessionPoint (quirk/dashboard/api/schemas.py) exposes only "
        "`score: Optional[float]` (Phase 199 / TRIAGE-10 widening) and "
        "`subscores: SubScores` (all ints); it has no rating/band field at "
        "all, so this timeline point can never render a severity-blind band."
    ),
    "quirk/merge/scan.py:merge_scan": (
        "D-07 (184.4), verified in 184.4-07-SUMMARY.md -- this call scores "
        "the merged union for the numeric score/subscores/drivers persisted "
        "on MergeRun.score and returned to CLI/dashboard sensor callers. "
        "The `rating` this call produces passes through the return dict but "
        "has no DB column (MergeRun has no rating field) and no schema "
        "consumer ever reads it -- MergeLatestData exposes only `score` and "
        "`per_segment_scores`, both Optional[float] as of Phase 199 / "
        "TRIAGE-10. No band is ever rendered from this call."
    ),
    "quirk/dashboard/api/routes/merge.py:get_merge_latest": (
        "D-07 (184.4), verified in 184.4-07-SUMMARY.md -- covers BOTH "
        "findings-less calls inside this function (per-segment score loop "
        "and the overall live-recompute call). Both feed exclusively "
        "float-capable, null-honest fields on MergeLatestData "
        "(`per_segment_scores: Dict[str, Optional[float]]` and "
        "`live_score: Optional[float]`, widened Phase 199 / TRIAGE-10); "
        "neither result's rating/band is ever read."
    ),
}


# ---------------------------------------------------------------------------
# Run-time source-file derivation -- no hard-coded file list, ever.
# ---------------------------------------------------------------------------
def _derive_source_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def _relpath(file_path: Path) -> str:
    return str(file_path.resolve().relative_to(_REPO_ROOT))


# ---------------------------------------------------------------------------
# Call-site walker, tracking enclosing function name -- same idiom as
# test_timestamp_serialization_gate.py's _walk_calls_with_func_context.
# ---------------------------------------------------------------------------
def _is_target_call(node: ast.AST) -> bool:
    """True if *node* is a Call to build_evidence_summary -- either the bare
    name form or the `<module>.build_evidence_summary` attribute form."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name) and func.id == _TARGET_FUNC_NAME:
        return True
    if isinstance(func, ast.Attribute) and func.attr == _TARGET_FUNC_NAME:
        return True
    return False


def _walk_target_calls_with_func_context(
    node: ast.AST, current_func: str | None = None
):
    """Yield (call_node, enclosing_function_name) for every
    build_evidence_summary() call in *node*'s subtree, tracking the nearest
    enclosing function via manual recursive descent."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        current_func = node.name
    if _is_target_call(node):
        yield node, current_func
    for child in ast.iter_child_nodes(node):
        yield from _walk_target_calls_with_func_context(child, current_func)


def _is_none_constant(value: ast.AST) -> bool:
    return isinstance(value, ast.Constant) and value.value is None


def _call_supplies_findings(call: ast.Call) -> bool:
    """True if *call* supplies a non-None findings argument: a `findings=`
    keyword whose value isn't the None constant, OR a second positional
    argument that isn't None. Purely syntactic -- a variable that happens to
    be None at runtime is not detectable here (see module docstring)."""
    for kw in call.keywords:
        if kw.arg == "findings":
            return not _is_none_constant(kw.value)
    if len(call.args) >= 2:
        return not _is_none_constant(call.args[1])
    return False


def _find_findings_less_offenders(
    tree: ast.AST, relpath: str, dispositions: dict[str, str]
) -> list[str]:
    """Offender messages for every findings-less build_evidence_summary()
    call not covered by a `_DISPOSITIONS` entry keyed on its enclosing
    function name."""
    messages: list[str] = []
    for call, func_name in _walk_target_calls_with_func_context(tree):
        if _call_supplies_findings(call):
            continue
        ledger_key = f"{relpath}:{func_name}" if func_name else None
        if ledger_key and ledger_key in dispositions:
            continue
        messages.append(
            f"{relpath}:{call.lineno}: build_evidence_summary() called "
            f"without a findings argument (or with findings=None), and not "
            f"covered by a _DISPOSITIONS entry keyed on its enclosing "
            f"function '{func_name}'"
        )
    return messages


# ---------------------------------------------------------------------------
# Ledger validation -- same shape as the sibling gates.
# ---------------------------------------------------------------------------
def _validate_disposition_ledger(ledger: dict[str, str]) -> list[str]:
    problems: list[str] = []
    for key, reason in ledger.items():
        if not reason.strip():
            problems.append(f"{key}: blank disposition reason")
            continue
        relpath, _, anchor = key.partition(":")
        file_path = _REPO_ROOT / relpath
        if not file_path.exists():
            problems.append(
                f"{key}: {relpath} no longer exists on disk -- remove the "
                f"stale entry"
            )
            continue
        if anchor and anchor not in file_path.read_text(encoding="utf-8"):
            problems.append(
                f"{key}: anchor {anchor!r} no longer found in {relpath} -- "
                f"remove or update the stale entry"
            )
    return problems


# ---------------------------------------------------------------------------
# The real gate, run against the real quirk/ tree.
# ---------------------------------------------------------------------------
def _run_gate(root: Path, dispositions: dict[str, str]) -> list[str]:
    offenders: list[str] = []
    for file_path in _derive_source_files(root):
        relpath = _relpath(file_path)
        tree = ast.parse(file_path.read_text(encoding="utf-8-sig"), filename=relpath)
        offenders.extend(_find_findings_less_offenders(tree, relpath, dispositions))
    return offenders


def test_no_undispositioned_findings_less_call_site() -> None:
    """Every findings-less build_evidence_summary() call site under quirk/
    must carry a validated _DISPOSITIONS entry."""
    offenders = _run_gate(_QUIRK_ROOT, _DISPOSITIONS)
    assert not offenders, (
        f"{len(offenders)} un-dispositioned findings-less "
        f"build_evidence_summary() call site(s) found: {offenders}"
    )


def test_disposition_ledger_is_valid() -> None:
    """_DISPOSITIONS ships non-empty and every entry resolves to a real
    file/anchor with a non-blank reason."""
    assert len(_DISPOSITIONS) >= 4, (
        "the disposition ledger must ship non-empty with named, concrete "
        "exemptions sourced from plan 184.4-07's verified table -- it "
        "should never be grown reflexively later just to make a failing "
        "assertion pass"
    )
    problems = _validate_disposition_ledger(_DISPOSITIONS)
    assert not problems, problems


def test_findings_remains_optional_parameter() -> None:
    """D-08: build_evidence_summary()'s `findings` parameter must stay
    optional -- this gate is the enforcement mechanism, not a signature
    change. Verified against the live signature via inspect, not assumed."""
    import inspect

    from quirk.intelligence.evidence import build_evidence_summary

    sig = inspect.signature(build_evidence_summary)
    findings_param = sig.parameters.get("findings")
    assert findings_param is not None, "findings parameter was removed entirely"
    assert findings_param.default is None, (
        "findings must default to None (stay optional) per D-08 -- the "
        "AST gate in this file carries the enforcement instead of a "
        "required-parameter signature change"
    )


# ---------------------------------------------------------------------------
# Synthetic self-tests: prove the detector, and the ledger validator, CAN
# fail. The real 5 sites are dispositioned by construction of plan 184.4-07
# -- a currently-green run against the real tree alone proves nothing.
# ---------------------------------------------------------------------------
def test_detector_flags_bare_name_call_with_no_findings(tmp_path: Path) -> None:
    fake = tmp_path / "fake_caller_bare.py"
    fake.write_text(
        "from quirk.intelligence.evidence import build_evidence_summary\n\n"
        "def handler(endpoints):\n"
        "    return build_evidence_summary(endpoints)\n"
    )
    tree = ast.parse(fake.read_text())
    offenders = _find_findings_less_offenders(tree, "fake_caller_bare.py", {})
    assert offenders, "a bare-name findings-less call was not flagged"
    assert any("fake_caller_bare.py:4" in o for o in offenders), offenders


def test_detector_flags_bare_name_call_with_explicit_none(tmp_path: Path) -> None:
    fake = tmp_path / "fake_caller_none.py"
    fake.write_text(
        "from quirk.intelligence.evidence import build_evidence_summary\n\n"
        "def handler(endpoints):\n"
        "    return build_evidence_summary(endpoints, findings=None)\n"
    )
    tree = ast.parse(fake.read_text())
    offenders = _find_findings_less_offenders(tree, "fake_caller_none.py", {})
    assert offenders, "an explicit findings=None call was not flagged"


def test_detector_flags_attribute_access_call_form(tmp_path: Path) -> None:
    """The `evidence.build_evidence_summary(...)` attribute-access form --
    all 13 real call sites use the bare-name form today, but the detector
    must not assume that stays true."""
    fake = tmp_path / "fake_caller_attr.py"
    fake.write_text(
        "from quirk.intelligence import evidence\n\n"
        "def handler(endpoints):\n"
        "    return evidence.build_evidence_summary(endpoints)\n"
    )
    tree = ast.parse(fake.read_text())
    offenders = _find_findings_less_offenders(tree, "fake_caller_attr.py", {})
    assert offenders, "an attribute-access findings-less call was not flagged"
    assert any("fake_caller_attr.py:4" in o for o in offenders), offenders


def test_detector_allows_bare_name_call_with_findings(tmp_path: Path) -> None:
    fake = tmp_path / "fake_caller_ok.py"
    fake.write_text(
        "from quirk.intelligence.evidence import build_evidence_summary\n\n"
        "def handler(endpoints, findings):\n"
        "    return build_evidence_summary(endpoints, findings)\n"
    )
    tree = ast.parse(fake.read_text())
    offenders = _find_findings_less_offenders(tree, "fake_caller_ok.py", {})
    assert not offenders, offenders


def test_detector_allows_attribute_access_call_with_findings_kwarg(
    tmp_path: Path,
) -> None:
    fake = tmp_path / "fake_caller_attr_ok.py"
    fake.write_text(
        "from quirk.intelligence import evidence\n\n"
        "def handler(endpoints, findings):\n"
        "    return evidence.build_evidence_summary(endpoints, findings=findings)\n"
    )
    tree = ast.parse(fake.read_text())
    offenders = _find_findings_less_offenders(tree, "fake_caller_attr_ok.py", {})
    assert not offenders, offenders


def test_detector_allows_ledger_disposition_by_function_name(tmp_path: Path) -> None:
    fake = tmp_path / "fake_caller_dispositioned.py"
    fake.write_text(
        "from quirk.intelligence.evidence import build_evidence_summary\n\n"
        "def handler(endpoints):\n"
        "    return build_evidence_summary(endpoints)\n"
    )
    tree = ast.parse(fake.read_text())
    ledger = {"fake_caller_dispositioned.py:handler": "synthetic disposition for test"}
    offenders = _find_findings_less_offenders(
        tree, "fake_caller_dispositioned.py", ledger
    )
    assert not offenders, offenders


def test_ninth_findings_less_site_is_flagged(tmp_path: Path) -> None:
    """The literal scenario D-12 exists to catch: a NINTH findings-less
    call site added later, with no ledger edit, fails the gate."""
    fake = tmp_path / "fake_ninth_site.py"
    fake.write_text(
        "from quirk.intelligence.evidence import build_evidence_summary\n\n"
        "def a_brand_new_route(endpoints):\n"
        "    evidence = build_evidence_summary(endpoints)\n"
        "    return evidence\n"
    )
    tree = ast.parse(fake.read_text())
    offenders = _find_findings_less_offenders(tree, "fake_ninth_site.py", {})
    assert offenders, "a ninth findings-less call site was not flagged"


def test_ledger_validator_flags_blank_reason() -> None:
    problems = _validate_disposition_ledger(
        {"quirk/merge/scan.py:merge_scan": "   "}
    )
    assert problems, "blank disposition reason was not flagged"
    assert any("blank disposition reason" in p for p in problems), problems


def test_ledger_validator_flags_stale_missing_file() -> None:
    problems = _validate_disposition_ledger(
        {"quirk/this_file_does_not_exist.py:x": "a fine reason"}
    )
    assert problems, "a ledger key naming a nonexistent file was not flagged"
    assert any("no longer exists on disk" in p for p in problems), problems


def test_ledger_validator_flags_stale_anchor() -> None:
    problems = _validate_disposition_ledger(
        {
            "quirk/merge/scan.py:this_identifier_will_never_exist_xyz": (
                "a fine reason, but a stale anchor"
            )
        }
    )
    assert problems, "a ledger key with a stale anchor was not flagged"
    assert any("no longer found in" in p for p in problems), problems


def test_derive_source_files_uses_rglob_not_a_written_list(tmp_path: Path) -> None:
    (tmp_path / "never_seen_before.py").write_text(
        "def f():\n    return build_evidence_summary(None)\n"
    )
    discovered = _derive_source_files(tmp_path)
    assert any(p.name == "never_seen_before.py" for p in discovered), discovered
