"""SCORE-03 (Phase 184.3, plan 09) forward-locking gate: serialization
correctness for every instant that reaches the wire from
``quirk/dashboard/api/**`` (Pydantic response fields + hand-rolled
``.isoformat()`` route sites) and every renderer timestamp in
``quirk/reports/**`` (``strftime`` calls).

D-03 / CLAUDE.md's "GSD state.* Verb Integrity" TOOL-04 section states the
rule this gate exists to apply here: an enumeration of known
offense/exemption sites that is hand-written and never regenerated is NOT a
safeguard -- it is decoration that reads as protection. TOOL-04's own
precedent (182-07's run-time source-scan gate) was built specifically
because a hand-derived enumeration missed an instance living inside the very
command handler it audited. The exact same failure mode recurred at THIS
plan's own construction time: plan 03's hand-derived enumeration of
``scan.py``'s two "identity, not instant" sites (:1350, :1671) missed a
third real one at :1319 (the legacy per-second grouping-key fallback that
becomes ``ScanSession.scan_id``) -- found only because this gate re-derives
its occurrence set from source at every run rather than trusting plan 03's
SUMMARY.md list. That third site is now fenced in-place with the same
inline "identity, not instant" comment convention and is exercised by
this gate exactly like the other two. See 184.3-09-SUMMARY.md for the full
account.

Three detectors, all AST-based (never regex/substring-only), all deriving
their occurrence set via ``Path.rglob`` at test-collection/run time against
the LIVE imported ``quirk`` package location -- never a hard-coded path
literal, never a written file list:

1. Field detector -- every Pydantic ``ClassDef`` field under
   ``quirk/dashboard/api/**`` whose annotation resolves to bare
   ``datetime`` (handling ``Optional[datetime]`` / ``Union[datetime, None]``
   / ``datetime | None`` explicitly, not just the bare ``ast.Name`` form --
   a walk that only understands the bare form silently passes most fields
   in this codebase, which are ``Optional[...]``) must instead be
   ``UTCDateTime`` (``quirk/dashboard/api/_timestamp_utils.py``, plan 02).

2. Call detector -- every ``.isoformat()`` call under
   ``quirk/dashboard/api/**`` (outside ``_timestamp_utils.py`` itself, the
   canonical implementation) must either be dispositioned via an inline
   "identity, not instant" source comment within a few lines above the call
   (the convention plan 03 established for ``scan.py``'s two originally
   fenced sites) or via a matching ``_DISPOSITIONS`` ledger entry keyed by
   its enclosing function name.

3. Renderer detector (D-16) -- every ``strftime()`` call under
   ``quirk/reports/**`` must either carry an explicit ``UTC`` zone token in
   its format string, or carry the same disposition as (2). This is what
   makes a future unlabeled renderer timestamp fail the gate rather than
   ship silently as ``generated_at`` did before plan 08.

A dedicated, independent check (see ``_IDENTITY_FIELD_NAMES`` and
``test_field_detector_identity_field_cannot_be_exempted_by_ledger``) makes
a field named ``scan_id`` or ``scan_run_id`` an offender if it is EVER typed
``datetime`` -- regardless of any ``_DISPOSITIONS`` ledger entry naming it.
An identity key may be exempt from carrying an offset; it may never be
exempt from remaining a string (RESEARCH.md Pitfall 2).

The real source tree is clean by the time this file lands, so a green run
against it alone proves nothing (CLAUDE.md again: "The behavioural test is
the safeguard," not a written list, and not a currently-passing assertion
either). The synthetic ``tmp_path`` self-tests below exist specifically to
prove each detector CAN fail -- every one of them drives the exact same
module-level detector function the real gate tests call, never a
reimplementation.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional

import quirk

_REPO_ROOT = Path(quirk.__file__).resolve().parent.parent
_API_ROOT = Path(quirk.__file__).resolve().parent / "dashboard" / "api"
_REPORTS_ROOT = Path(quirk.__file__).resolve().parent / "reports"

_UTC_TYPE_NAME = "UTCDateTime"
_TIMESTAMP_UTILS_BASENAME = "_timestamp_utils.py"
_IDENTITY_COMMENT_MARKER = "identity, not instant"
_ZONE_TOKEN = "UTC"

# Field names that are identity keys, never instants, no matter what a
# ledger entry claims. See test_field_detector_identity_field_cannot_be_
# exempted_by_ledger -- this is the RESEARCH.md Pitfall 2 regression guard.
_IDENTITY_FIELD_NAMES = {"scan_id", "scan_run_id"}

# ---------------------------------------------------------------------------
# Disposition ledger.
#
# Keyed "<repo-relative-path>:<anchor>", where <anchor> is either a plain
# field/identifier name (documentation-only entries) or an enclosing
# function name (entries actually consulted by the call-site detectors,
# f"{relpath}:{func_name}"). Every key's anchor must be a literal substring
# still present in the named file -- test_disposition_ledger_is_valid
# enforces this so an entry cannot silently rot as the file changes, and
# every reason must be non-blank. Ships non-empty (D-05, RESEARCH Pitfall 1
# and 2) -- these are concrete, named exemptions, not placeholders.
# ---------------------------------------------------------------------------
_DISPOSITIONS: dict[str, str] = {
    "quirk/dashboard/api/schemas.py:scan_id": (
        "identity, not instant (SCORE-03/D-05) -- scan_id is a string "
        "identity key (an ISO-timestamp-SHAPED value used as a lookup key, "
        "round-tripped by the UI as the ?scan_id= query parameter), never "
        "rendered as an instant. It is not currently datetime-typed; "
        "_IDENTITY_FIELD_NAMES forward-locks it so it can never silently "
        "become one -- this ledger entry is documentation, not the "
        "enforcement mechanism for that guarantee."
    ),
    "quirk/dashboard/api/schemas.py:scan_run_id": (
        "identity, not instant (SCORE-03/D-05) -- scan_run_id is the "
        "ScanJob/CryptoEndpoint join key, never an instant. Same "
        "forward-lock via _IDENTITY_FIELD_NAMES as scan_id; this entry is "
        "documentation only."
    ),
    "quirk/dashboard/api/schemas.py:cert_not_after": (
        "date-only, not an instant (out of scope) -- CertItem.cert_not_after "
        "is an ISO date string field (a distinct model from the "
        "Optional[UTCDateTime] cert_not_after used elsewhere), per "
        "184.3-RESEARCH.md Pitfall 1. Not datetime-typed, so the field "
        "detector never flags it; documentation only."
    ),
    "quirk/reports/writer.py:_utc_stamp": (
        "identity, not instant (a filename) -- the %Y%m%d-%H%M%S string "
        "returned by _utc_stamp() feeds an on-disk report FILENAME, not a "
        "displayed instant, so it deliberately carries no UTC zone token. "
        "Consulted by the strftime detector via its enclosing-function-name "
        "anchor."
    ),
    "quirk/dashboard/api/routes/scan.py:list_scans": (
        "identity, not instant (SCORE-03/D-05) -- list_scans() constructs "
        "two identity-key .isoformat() call sites: the legacy per-second "
        "grouping-key fallback (row_run_id or "
        "row_ts.replace(microsecond=0).isoformat(sep=' ')) that becomes "
        "ScanSession.scan_id for pre-scan_run_id rows (found by THIS "
        "gate's run-time scan -- plan 03's hand-derived enumeration missed "
        "it, see module docstring), and the prefix-LIKE match key "
        "(ts.isoformat()[:19]) against stored scan_run_id strings. Both "
        "are additionally fenced in-place with an inline 'identity, not "
        "instant' comment and must stay byte-unchanged. Consulted by the "
        "isoformat detector via its enclosing-function-name anchor."
    ),
    "quirk/dashboard/api/routes/scan.py:get_latest_scan": (
        "identity, not instant (SCORE-03/D-05) -- response_scan_id is "
        "round-tripped by the UI as the ?scan_id= query parameter; fenced "
        "in-place with an inline 'identity, not instant' comment. "
        "Consulted by the isoformat detector via its enclosing-function-"
        "name anchor."
    ),
}


# ---------------------------------------------------------------------------
# Run-time source-file derivation -- no hard-coded file list, ever.
# ---------------------------------------------------------------------------
def _derive_source_files(root: Path) -> list[Path]:
    """Every ``.py`` file under *root*, discovered by globbing at call time.

    ``root`` is a required parameter (never a module-level constant read
    directly by a detector) so the synthetic self-tests below can point the
    real derivation mechanism at a throwaway ``tmp_path`` tree."""
    return sorted(root.rglob("*.py"))


def _relpath(file_path: Path) -> str:
    return str(file_path.resolve().relative_to(_REPO_ROOT))


# ---------------------------------------------------------------------------
# Annotation classification -- explicit ast.Subscript / ast.BinOp handling.
# ---------------------------------------------------------------------------
def _annotation_datetime_kind(annotation: ast.AST) -> Optional[str]:
    """Classify a field annotation: "bare" (resolves to stdlib ``datetime``
    without the ``UTCDateTime`` wrapper -- an offender candidate), "utc"
    (resolves to ``UTCDateTime`` -- compliant), or ``None`` (unrelated to
    datetime entirely).

    Handles four annotation shapes explicitly:
      - bare ``ast.Name`` (``datetime`` / ``UTCDateTime``)
      - ``ast.Attribute`` (``datetime.datetime``)
      - ``ast.Subscript`` -- ``Optional[X]`` / ``Union[X, None]`` /
        ``Union[X, Y, None]``
      - ``ast.BinOp`` with ``ast.BitOr`` -- ``X | None``

    A walker that only recognizes the bare ``ast.Name`` form silently
    passes every ``Optional[datetime]`` field, which is most of the
    datetime-bearing fields in this codebase -- this is why (3) and (4)
    are handled as their own explicit branches rather than folded into a
    blanket ``ast.walk``.
    """
    if isinstance(annotation, ast.Name):
        if annotation.id == _UTC_TYPE_NAME:
            return "utc"
        if annotation.id == "datetime":
            return "bare"
        return None
    if isinstance(annotation, ast.Attribute):
        if annotation.attr == _UTC_TYPE_NAME:
            return "utc"
        if annotation.attr == "datetime":
            return "bare"
        return None
    if isinstance(annotation, ast.Subscript):
        inner = annotation.slice
        candidates = inner.elts if isinstance(inner, ast.Tuple) else [inner]
        for candidate in candidates:
            kind = _annotation_datetime_kind(candidate)
            if kind is not None:
                return kind
        return None
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        left_kind = _annotation_datetime_kind(annotation.left)
        if left_kind is not None:
            return left_kind
        return _annotation_datetime_kind(annotation.right)
    return None


def _scan_class_datetime_fields(tree: ast.AST) -> list[tuple[str, str, int]]:
    """Every (class_name, field_name, lineno) for a ``ClassDef`` field whose
    annotation resolves to bare ``datetime`` (offender candidates only)."""
    found: list[tuple[str, str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.AnnAssign):
                continue
            if not isinstance(stmt.target, ast.Name):
                continue
            if _annotation_datetime_kind(stmt.annotation) == "bare":
                found.append((node.name, stmt.target.id, stmt.lineno))
    return found


def _find_field_offenders(
    tree: ast.AST, relpath: str, dispositions: dict[str, str]
) -> list[str]:
    """Offender messages for every bare-datetime Pydantic field in *tree*.

    A field named ``scan_id`` / ``scan_run_id`` is reported UNCONDITIONALLY
    -- checked and reported before any ledger lookup -- so no
    ``_DISPOSITIONS`` entry can ever suppress it (RESEARCH.md Pitfall 2).
    """
    messages: list[str] = []
    for class_name, field_name, lineno in _scan_class_datetime_fields(tree):
        if field_name in _IDENTITY_FIELD_NAMES:
            messages.append(
                f"{relpath}:{lineno}: {class_name}.{field_name} is an "
                f"identity key (scan_id/scan_run_id) typed as bare "
                f"datetime -- identity keys must stay str and can NEVER be "
                f"exempted by the disposition ledger (RESEARCH.md Pitfall 2)"
            )
            continue
        ledger_key = f"{relpath}:{field_name}"
        if ledger_key in dispositions:
            continue
        messages.append(
            f"{relpath}:{lineno}: {class_name}.{field_name} is typed bare "
            f"datetime, not {_UTC_TYPE_NAME} -- route it through "
            f"quirk/dashboard/api/_timestamp_utils.py::{_UTC_TYPE_NAME}"
        )
    return messages


# ---------------------------------------------------------------------------
# Call-site walkers (isoformat / strftime), tracking enclosing function name.
# ---------------------------------------------------------------------------
def _walk_calls_with_func_context(
    node: ast.AST, attr_name: str, current_func: Optional[str] = None
):
    """Yield (call_node, enclosing_function_name) for every ``Call`` whose
    ``func`` is an ``ast.Attribute`` with ``attr == attr_name`` in *node*'s
    subtree, tracking the nearest enclosing function via manual recursive
    descent -- plain ``ast.walk`` loses this context, and the isoformat/
    strftime disposition-ledger lookup needs it."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        current_func = node.name
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == attr_name
    ):
        yield node, current_func
    for child in ast.iter_child_nodes(node):
        yield from _walk_calls_with_func_context(child, attr_name, current_func)


def _has_identity_comment_nearby(
    source_lines: list[str], lineno: int, window: int = 6
) -> bool:
    """True if a line at or up to *window* lines above 1-indexed *lineno*
    contains the ``"identity, not instant"`` disposition marker."""
    start = max(0, lineno - window)
    return any(_IDENTITY_COMMENT_MARKER in line for line in source_lines[start:lineno])


def _find_isoformat_offenders(
    tree: ast.AST,
    source_lines: list[str],
    relpath: str,
    dispositions: dict[str, str],
) -> list[str]:
    """Offender messages for every ``.isoformat()`` call in *tree* not
    dispositioned via an inline "identity, not instant" comment nearby, and
    not covered by a ``_DISPOSITIONS`` entry keyed on its enclosing
    function name."""
    messages: list[str] = []
    for node, func_name in _walk_calls_with_func_context(tree, "isoformat"):
        lineno = node.lineno
        if _has_identity_comment_nearby(source_lines, lineno):
            continue
        ledger_key = f"{relpath}:{func_name}" if func_name else None
        if ledger_key and ledger_key in dispositions:
            continue
        messages.append(
            f"{relpath}:{lineno}: bare .isoformat() call, not routed "
            f"through stamp_utc_iso, and not fenced with an inline "
            f"'identity, not instant' comment or a _DISPOSITIONS entry"
        )
    return messages


def _strftime_has_zone_token(node: ast.Call) -> bool:
    if not node.args:
        return False
    fmt_arg = node.args[0]
    if not (isinstance(fmt_arg, ast.Constant) and isinstance(fmt_arg.value, str)):
        return False
    return _ZONE_TOKEN in fmt_arg.value


def _find_strftime_offenders(
    tree: ast.AST,
    source_lines: list[str],
    relpath: str,
    dispositions: dict[str, str],
) -> list[str]:
    """D-16: offender messages for every ``strftime()`` call in *tree*
    whose format string carries no explicit ``UTC`` zone token and is not
    dispositioned (inline comment or ledger, same mechanism as
    ``_find_isoformat_offenders``)."""
    messages: list[str] = []
    for node, func_name in _walk_calls_with_func_context(tree, "strftime"):
        if _strftime_has_zone_token(node):
            continue
        lineno = node.lineno
        if _has_identity_comment_nearby(source_lines, lineno):
            continue
        ledger_key = f"{relpath}:{func_name}" if func_name else None
        if ledger_key and ledger_key in dispositions:
            continue
        messages.append(
            f"{relpath}:{lineno}: strftime() call with no explicit UTC "
            f"zone token in its format string, and not fenced with an "
            f"inline 'identity, not instant' comment or a _DISPOSITIONS "
            f"entry -- a renderer timestamp must say UTC explicitly (D-16)"
        )
    return messages


# ---------------------------------------------------------------------------
# Ledger validation.
# ---------------------------------------------------------------------------
def _validate_disposition_ledger(ledger: dict[str, str]) -> list[str]:
    """Return problem descriptions for *ledger* -- a blank reason, a key
    naming a file that no longer exists, or an anchor substring no longer
    present in that file's text. Empty return means the ledger is clean.
    A ledger that cannot go stale is the whole point (CLAUDE.md TOOL-04)."""
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
# Wrappers over the real quirk/dashboard/api and quirk/reports trees.
# ---------------------------------------------------------------------------
def _run_field_gate(root: Path, dispositions: dict[str, str]) -> list[str]:
    offenders: list[str] = []
    for file_path in _derive_source_files(root):
        if file_path.name == _TIMESTAMP_UTILS_BASENAME:
            continue
        relpath = _relpath(file_path)
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=relpath)
        offenders.extend(_find_field_offenders(tree, relpath, dispositions))
    return offenders


def _run_isoformat_gate(root: Path, dispositions: dict[str, str]) -> list[str]:
    offenders: list[str] = []
    for file_path in _derive_source_files(root):
        if file_path.name == _TIMESTAMP_UTILS_BASENAME:
            continue
        relpath = _relpath(file_path)
        text = file_path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=relpath)
        offenders.extend(
            _find_isoformat_offenders(tree, text.splitlines(), relpath, dispositions)
        )
    return offenders


def _run_strftime_gate(root: Path, dispositions: dict[str, str]) -> list[str]:
    offenders: list[str] = []
    for file_path in _derive_source_files(root):
        relpath = _relpath(file_path)
        text = file_path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=relpath)
        offenders.extend(
            _find_strftime_offenders(tree, text.splitlines(), relpath, dispositions)
        )
    return offenders


# ---------------------------------------------------------------------------
# The real gate.
# ---------------------------------------------------------------------------
def test_no_bare_datetime_fields_in_api_schemas() -> None:
    """Every Pydantic response field under quirk/dashboard/api/** typed
    datetime must be UTCDateTime instead (plan 02's contract)."""
    offenders = _run_field_gate(_API_ROOT, _DISPOSITIONS)
    assert not offenders, (
        f"{len(offenders)} bare-datetime Pydantic field(s) found: {offenders}"
    )


def test_no_unrouted_isoformat_calls_under_api() -> None:
    """Every hand-rolled .isoformat() call under quirk/dashboard/api/**
    must be routed through stamp_utc_iso or carry a validated identity
    disposition (plan 03's contract)."""
    offenders = _run_isoformat_gate(_API_ROOT, _DISPOSITIONS)
    assert not offenders, (
        f"{len(offenders)} unrouted/undispositioned .isoformat() call(s) "
        f"found: {offenders}"
    )


def test_no_unlabeled_strftime_calls_under_reports() -> None:
    """D-16: every renderer strftime() call under quirk/reports/** must
    carry an explicit UTC zone token or a validated disposition."""
    offenders = _run_strftime_gate(_REPORTS_ROOT, _DISPOSITIONS)
    assert not offenders, (
        f"{len(offenders)} unlabeled renderer strftime() call(s) found: "
        f"{offenders}"
    )


def test_disposition_ledger_is_valid() -> None:
    """_DISPOSITIONS ships non-empty (D-05) and every entry must resolve
    to a real file/anchor with a non-blank reason."""
    assert len(_DISPOSITIONS) >= 5, (
        "the disposition ledger must ship non-empty with named, concrete "
        "exemptions (D-05) -- it should never be grown reflexively later "
        "just to make a failing assertion pass"
    )
    problems = _validate_disposition_ledger(_DISPOSITIONS)
    assert not problems, problems
