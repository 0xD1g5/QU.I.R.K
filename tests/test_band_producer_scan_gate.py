"""Phase 184.4, SCORE-05, D-11(2): run-time band-producer AST scan gate.

CLAUDE.md's "GSD state.* Verb Integrity" TOOL-04 section states the rule
this gate exists to apply here: a written list of known sites is not a
safeguard -- the gate must regenerate its occurrence set from source at run
time. This file AST-walks every `.py` file under `quirk/` at TEST RUN TIME
(``Path.rglob``, never a hard-coded file-path list) looking for any function
that can return one of the five band literals
(``quirk.severity_bands.BAND_ORDER`` -- imported, never re-typed here) as a
``Constant``. Any hit must either be the shared producer
(``quirk/severity_bands.py``) or a dispositioned ``_DISPOSITIONS`` ledger
entry; an un-dispositioned hit fails the gate.

Modelled structurally on ``tests/test_timestamp_serialization_gate.py``
(``_derive_source_files`` for run-time ``Path.rglob`` derivation, the
enclosing-``FunctionDef``-context walk idiom, the ``_DISPOSITIONS`` ledger +
``test_disposition_ledger_is_valid`` self-check, and the synthetic
``tmp_path`` prove-it-can-fail tests) -- the SHAPE is copied, not any
datetime-specific logic.

Node shapes handled (RESEARCH.md's enumeration):
  1. Direct ``return "FAIR"`` -- ``Return(Constant)``.
  2. Ternary ``return "FAIR" if x else "POOR"`` -- ``Return(IfExp(...))``,
     recursing into ``.body`` and ``.orelse``.
  3. Chained ``if/elif/else: return "X"`` -- covered for free by walking
     every ``Return`` statement in the function's own body (not just its
     final statement) -- this is the ACTUAL shape both
     ``quirk.severity_bands.band_for_score()`` and the pre-184.4
     ``_score_band()``/``_rating()`` producers used.

KNOWN FALSE NEGATIVE, stated rather than silently claimed away: a band
literal built via f-string interpolation or string concatenation (e.g.
``return "".join(["F", "AIR"])`` or ``return f"{prefix}AIR"``) is NOT
detected -- this detector only resolves literal ``ast.Constant`` values, not
arbitrary runtime string construction. The compensating controls are (a) the
D-11(1) matrix walk (`tests/test_band_severity_matrix_gate.py`), which
exercises the ACTUAL runtime band values `cap_band_for_severity()` emits
against the real congruence guard regardless of how those strings were
built, and (b) the D-13 regression
(`tests/test_score_severity_floor_regression.py`), which exercises the real
end-to-end scoring pipeline. Both catch a wrong *value* at runtime even when
this static detector cannot see how that value was constructed.

DEFERRED, stated rather than silently claimed away: the dict/table-lookup
shape (e.g. ``return {0: "POOR", 1: "FAIR"}[idx]``) is not specifically
walked for constant band-literal VALUES inside dict/list literals -- only
``ast.Constant`` values that are the direct/ternary return expression are
inspected. The same two compensating controls named above (the D-11(1)
matrix walk and the D-13 regression) apply.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional

import quirk
from quirk.severity_bands import BAND_ORDER

_REPO_ROOT = Path(quirk.__file__).resolve().parent.parent
_QUIRK_ROOT = Path(quirk.__file__).resolve().parent

_BAND_LITERALS = set(BAND_ORDER)

# ---------------------------------------------------------------------------
# Disposition ledger.
#
# Keyed "<repo-relative-path>:<enclosing-function-name>". Every reason must
# be non-blank and every key's file/anchor must still exist -- enforced by
# test_disposition_ledger_is_valid, the same self-check pattern as
# tests/test_timestamp_serialization_gate.py's ledger. Ships non-empty:
# quirk/severity_bands.py's OWN producer function is itself a legitimate
# hit and is dispositioned here, not special-cased inside the detector.
# ---------------------------------------------------------------------------
_DISPOSITIONS: dict[str, str] = {
    "quirk/severity_bands.py:band_for_score": (
        "THIS IS THE SHARED PRODUCER (D-04/D-11(2)) -- the one legitimate "
        "band-literal-returning function in the codebase. Every other "
        "producer (the old quirk/intelligence/scoring.py::_rating() chain "
        "and the deleted quirk/reports/html_renderer.py::_score_band(), "
        "Phase 184.4 plans 04/05) now delegates to this function rather "
        "than re-implementing the threshold chain. Not a false positive; "
        "recorded here as the detector's designed self-match."
    ),
    "quirk/notify/payload.py:_score_to_band": (
        "GENUINE FALSE POSITIVE, not a band producer -- _score_to_band() "
        "maps a drift-notification score to an UNRELATED five-tier scale "
        "(CRITICAL/HIGH/MEDIUM/LOW/GOOD) used only by "
        "quirk/notify/payload.py::build_drift_summary()'s Slack/webhook "
        "payload severity field. It shares exactly one literal ('GOOD') "
        "with quirk.severity_bands.BAND_ORDER by coincidence of English "
        "vocabulary, the same class of collision "
        "quirk/intelligence/confidence.py::_rating() has with "
        "quirk/intelligence/scoring.py::_rating() (out of scope per "
        "184.4-CONTEXT.md). Never read by _check_congruence() or any "
        "report-band consumer -- verified by grep: no import of "
        "quirk.notify.payload appears anywhere under quirk/reports/ or "
        "quirk/intelligence/scoring.py. Disposed here per the plan's "
        "instruction to never add a detector exception branch for this "
        "class of false positive."
    ),
}


# ---------------------------------------------------------------------------
# Run-time source-file derivation -- no hard-coded file list, ever.
# ---------------------------------------------------------------------------
def _derive_source_files(root: Path) -> list[Path]:
    """Every ``.py`` file under *root*, discovered by globbing at call time."""
    return sorted(root.rglob("*.py"))


def _relpath(file_path: Path) -> str:
    return str(file_path.resolve().relative_to(_REPO_ROOT))


# ---------------------------------------------------------------------------
# Return-value classification.
# ---------------------------------------------------------------------------
def _resolves_to_band_literal(value: Optional[ast.AST], literals: set[str]) -> bool:
    """True if *value* (a Return statement's `.value`) resolves to one of
    *literals* as a literal Constant -- handling direct Constant and ternary
    IfExp (recursing into both branches). See module docstring for the
    stated false-negative (f-string/concatenation) and deferred (dict/table
    lookup) shapes."""
    if value is None:
        return False
    if isinstance(value, ast.Constant) and value.value in literals:
        return True
    if isinstance(value, ast.IfExp):
        return _resolves_to_band_literal(
            value.body, literals
        ) or _resolves_to_band_literal(value.orelse, literals)
    return False


def _collect_own_returns(func_node: ast.AST) -> list[ast.Return]:
    """Every ``Return`` statement belonging DIRECTLY to *func_node* -- i.e.
    every chained if/elif/else return inside its own body -- WITHOUT
    descending into a nested FunctionDef/AsyncFunctionDef/Lambda's own
    returns (those belong to a different enclosing function and are
    collected separately when that nested def is itself visited)."""
    found: list[ast.Return] = []

    def _walk(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Return):
                found.append(child)
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue  # a nested def's returns belong to IT, not func_node
            _walk(child)

    _walk(func_node)
    return found


def _find_band_producer_offenders(
    tree: ast.AST, relpath: str, dispositions: dict[str, str], literals: set[str]
) -> list[str]:
    """Offender messages for every FunctionDef/AsyncFunctionDef in *tree*
    that can return one of *literals* as a literal Constant, not covered by
    a `_DISPOSITIONS` entry keyed on its own name."""
    messages: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        offending_lines = [
            ret.lineno
            for ret in _collect_own_returns(node)
            if _resolves_to_band_literal(ret.value, literals)
        ]
        if not offending_lines:
            continue
        ledger_key = f"{relpath}:{node.name}"
        if ledger_key in dispositions:
            continue
        messages.append(
            f"{relpath}:{min(offending_lines)}: function '{node.name}' can "
            f"return a band literal ({sorted(literals)}) but is neither "
            f"quirk/severity_bands.py's shared producer nor a "
            f"_DISPOSITIONS ledger entry"
        )
    return messages


# ---------------------------------------------------------------------------
# Ledger validation -- same shape as test_timestamp_serialization_gate.py.
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
def _run_gate(root: Path, dispositions: dict[str, str], literals: set[str]) -> list[str]:
    offenders: list[str] = []
    for file_path in _derive_source_files(root):
        relpath = _relpath(file_path)
        # utf-8-sig transparently strips a leading BOM (present on at least
        # one file in this tree, e.g. quirk/assessment/operator_context.py)
        # while behaving identically to utf-8 for ordinary files.
        tree = ast.parse(file_path.read_text(encoding="utf-8-sig"), filename=relpath)
        offenders.extend(
            _find_band_producer_offenders(tree, relpath, dispositions, literals)
        )
    return offenders


def test_no_undispositioned_band_producer_exists() -> None:
    """Every function under quirk/ that can return a band literal must be
    the shared producer or carry a validated ledger disposition."""
    offenders = _run_gate(_QUIRK_ROOT, _DISPOSITIONS, _BAND_LITERALS)
    assert not offenders, (
        f"{len(offenders)} un-dispositioned band-producing function(s) "
        f"found: {offenders}"
    )


def test_disposition_ledger_is_valid() -> None:
    """_DISPOSITIONS ships non-empty and every entry resolves to a real
    file/anchor with a non-blank reason."""
    assert len(_DISPOSITIONS) >= 2, (
        "the disposition ledger must ship non-empty with named, concrete "
        "exemptions -- it should never be grown reflexively later just to "
        "make a failing assertion pass"
    )
    problems = _validate_disposition_ledger(_DISPOSITIONS)
    assert not problems, problems


def test_confidence_rating_is_not_flagged() -> None:
    """quirk/intelligence/confidence.py::_rating() returns
    HIGH/MEDIUM/LOW/VERY_LOW -- a different scale with zero overlap against
    BAND_ORDER. Confirmed empirically (not assumed) that it does not appear
    as an offender and requires no ledger entry."""
    confidence_file = _QUIRK_ROOT / "intelligence" / "confidence.py"
    tree = ast.parse(confidence_file.read_text(encoding="utf-8"))
    relpath = _relpath(confidence_file)
    offenders = _find_band_producer_offenders(tree, relpath, {}, _BAND_LITERALS)
    assert not offenders, (
        f"confidence.py::_rating() was unexpectedly flagged, meaning its "
        f"scale now overlaps BAND_ORDER: {offenders}"
    )


# ---------------------------------------------------------------------------
# Synthetic self-tests: prove the detector, and the ledger validator, CAN
# fail. The real source tree is dispositioned by construction of this
# plan -- a currently-green run against it alone proves nothing on its own.
# ---------------------------------------------------------------------------
def test_detector_flags_direct_return_clone(tmp_path: Path) -> None:
    """A fresh, never-before-seen `_score_band`-shaped clone -- the exact
    future-fourth-producer scenario D-11(2) exists to catch, with NO list
    edit anywhere in this file."""
    fake = tmp_path / "fake_producer.py"
    fake.write_text(
        "def _score_band(score):\n"
        "    if score >= 85:\n"
        "        return 'EXCELLENT'\n"
        "    if score >= 70:\n"
        "        return 'GOOD'\n"
        "    if score >= 55:\n"
        "        return 'MODERATE'\n"
        "    if score >= 35:\n"
        "        return 'FAIR'\n"
        "    return 'POOR'\n"
    )
    tree = ast.parse(fake.read_text())
    offenders = _find_band_producer_offenders(
        tree, "fake_producer.py", {}, _BAND_LITERALS
    )
    assert offenders, "a fresh _score_band clone was not flagged"
    assert any("_score_band" in o for o in offenders), offenders


def test_detector_flags_ternary_return(tmp_path: Path) -> None:
    fake = tmp_path / "fake_ternary.py"
    fake.write_text(
        "def band_of(score):\n"
        "    return 'GOOD' if score >= 70 else 'POOR'\n"
    )
    tree = ast.parse(fake.read_text())
    offenders = _find_band_producer_offenders(
        tree, "fake_ternary.py", {}, _BAND_LITERALS
    )
    assert offenders, "a ternary band-literal return was not flagged"


def test_detector_allows_ledger_disposition_by_function_name(tmp_path: Path) -> None:
    fake = tmp_path / "fake_dispositioned.py"
    fake.write_text(
        "def band_of(score):\n"
        "    return 'GOOD' if score >= 70 else 'POOR'\n"
    )
    tree = ast.parse(fake.read_text())
    ledger = {"fake_dispositioned.py:band_of": "synthetic disposition for test"}
    offenders = _find_band_producer_offenders(
        tree, "fake_dispositioned.py", ledger, _BAND_LITERALS
    )
    assert not offenders, offenders


def test_detector_ignores_nested_function_returns_of_outer(tmp_path: Path) -> None:
    """A nested inner function's band-literal return must be attributed to
    the INNER function's own name, not silently folded into the outer
    function (which itself returns something unrelated)."""
    fake = tmp_path / "fake_nested.py"
    fake.write_text(
        "def outer(x):\n"
        "    def inner(y):\n"
        "        return 'FAIR'\n"
        "    return inner(x) + 1\n"
    )
    tree = ast.parse(fake.read_text())
    offenders = _find_band_producer_offenders(
        tree, "fake_nested.py", {}, _BAND_LITERALS
    )
    assert any("inner" in o for o in offenders), offenders
    assert not any("'outer'" in o for o in offenders), offenders


def test_ledger_validator_flags_blank_reason() -> None:
    problems = _validate_disposition_ledger(
        {"quirk/severity_bands.py:band_for_score": "   "}
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
            "quirk/severity_bands.py:this_identifier_will_never_exist_xyz": (
                "a fine reason, but a stale anchor"
            )
        }
    )
    assert problems, "a ledger key with a stale anchor was not flagged"
    assert any("no longer found in" in p for p in problems), problems


def test_derive_source_files_uses_rglob_not_a_written_list(tmp_path: Path) -> None:
    """Proves the derivation mechanism itself: a brand-new, never-seen file
    dropped into a throwaway root is picked up by _derive_source_files with
    zero edits to any list, anywhere."""
    (tmp_path / "never_seen_before.py").write_text(
        "def f():\n    return 'FAIR'\n"
    )
    discovered = _derive_source_files(tmp_path)
    assert any(p.name == "never_seen_before.py" for p in discovered), discovered
