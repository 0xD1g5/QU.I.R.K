"""QRAMM per-dimension assessed state — Phase 231 QRAMM-18 / QRAMM-19.

Pure module. The one Python definition of "assessed / self-assessed / not
assessed" per dimension (D-09):

- A dimension is assessed when at least one of its questions has an answer
  (D-07, D-08). It is never a score test: SCOREFIX-02 injects 0.0 for
  unanswered practices, so a 0.0 score does not mean "not assessed".
- A dimension with zero answered questions is "pending" ("Not assessed") for
  all four dimensions, CVI included (D-02a).
- An assessed dimension keeps its scanner coverage status when the scanner
  covers it (CVI: "covered"); an assessed manual dimension (SGRM/DPE/ITR) is
  "self-assessed" (D-02).

Questions are mapped to dimensions through the QRAMM_QUESTIONS catalog (the
same catalog GET /api/qramm/questions serves and the dashboard's qnToDim
reads), not through the QRAMMAnswer.dimension column and not through
question-number range arithmetic, so both dialects count the same way.

The dashboard's TypeScript dialect is pinned to this one by the shared
contract fixture src/dashboard/src/lib/__fixtures__/qramm-assessment-contract.json
(tests/test_qramm_assessment_parity.py and the vitest parity test).

Per Phase 51 D-09: zero engine or scanner imports allowed.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from quirk.qramm.compliance_map import (
    SCANNER_COVERAGE_STATUS,
    RowCoverageStatus,
)
from quirk.qramm.questions import QRAMM_QUESTIONS

DIMENSIONS: Tuple[str, ...] = ("CVI", "SGRM", "DPE", "ITR")

# question_number -> dimension, derived once at import from the catalog.
_QUESTION_DIMENSION: Dict[int, str] = {}
for _q in QRAMM_QUESTIONS:
    if _q["dimension"] in DIMENSIONS:
        _QUESTION_DIMENSION[int(_q["question_number"])] = _q["dimension"]


def question_dimension_map() -> Dict[int, str]:
    """Return a copy of the catalog's question_number -> dimension map."""
    return dict(_QUESTION_DIMENSION)


def answered_by_dimension(
    answered_question_numbers: Iterable[int],
) -> Dict[str, int]:
    """Count distinct answered questions per dimension.

    Keys are always the four dimensions. Duplicates count once; question
    numbers absent from the catalog are ignored.
    """
    counts: Dict[str, int] = {dim: 0 for dim in DIMENSIONS}
    for qn in set(answered_question_numbers):
        dim = _QUESTION_DIMENSION.get(qn)
        if dim is not None:
            counts[dim] += 1
    return counts


def is_dimension_assessed(answered: int) -> bool:
    """The one "assessed" predicate: at least one answered question (D-07)."""
    return answered >= 1


def row_coverage_status(
    dimension: str,
    answered: int,
    scored_answered: Optional[int] = None,
    *,
    score_has_counts: bool = True,
) -> RowCoverageStatus:
    """Per-session coverage status for a compliance-map row (D-02, D-02a).

    Precedence (Phase 234 D-15 / D-25):

    1. Not assessed (zero live answers) -> "pending" for every dimension.
       Checked first: nothing was answered, so nothing can be mislabelled.
    2. ``score_has_counts`` False -> "stale" (D-25: the saved score predates
       persisted answered counts, so newer answers cannot be ruled out).
    3. ``scored_answered`` given and != ``answered`` -> "stale" (D-15: answers
       changed after the score was saved; todo 261025, WR-01).
    4. Otherwise the scanner status when the scanner covers the dimension
       ("covered"/"partial"), "n/a" when the dimension is intentionally out
       of scope, else "self-assessed".

    A stale dimension is never "self-assessed" and never counts toward a
    maturity level. D-21: staleness compares COUNTS, not values, so
    re-answering an already-answered question with a different value is not
    detected (disclosed; an answers-digest todo is filed in plan 234-08).
    """
    if not is_dimension_assessed(answered):
        return "pending"
    if not score_has_counts:
        return "stale"
    if scored_answered is not None and scored_answered != answered:
        return "stale"
    static = SCANNER_COVERAGE_STATUS.get(dimension)
    if static in ("covered", "partial"):
        return static
    if static == "n/a":
        return "n/a"
    return "self-assessed"


def score_answered_counts(
    score_data: Optional[Mapping[str, Any]],
) -> Optional[Dict[str, int]]:
    """The per-dimension answered counts persisted with a score, or None.

    None when the session is unscored or the score_json carries no
    dict-valued ``answered_by_dimension`` (a pre-Phase-234 legacy score,
    D-25). Values that are not integers are dropped rather than trusted: a
    persisted blob can only make a dimension stale, never upgrade it.

    Phase 234 review D-31 (IN-04): "not an integer" is judged exactly as the
    TS twin judges it (``typeof count === "number"`` and strict equality with
    the live count). A string ("30") or a fraction (30.9) is dropped, so the
    dimension reads stale; it used to be coerced with ``int()`` and could
    vouch for a live count of 30. A float with an integer value (30.0) is
    kept, because JSON and JavaScript cannot tell it from 30. Booleans are
    dropped (``True`` is an ``int`` in Python, not a count).
    """
    if not isinstance(score_data, Mapping):
        return None
    raw = score_data.get("answered_by_dimension")
    if not isinstance(raw, Mapping):
        return None
    counts: Dict[str, int] = {}
    for dim in DIMENSIONS:
        value = raw.get(dim)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            counts[dim] = value
        elif isinstance(value, float) and value.is_integer():
            counts[dim] = int(value)
    return counts


def overall_state(
    score_data: Optional[Mapping[str, Any]],
    *,
    stale: bool = False,
) -> Optional[str]:
    """State of a saved QRAMM overall (Phase 234 D-25, D-27).

    - None: the session is unscored (no score to describe).
    - "recalculate": the score carries no dict-valued
      ``answered_by_dimension``, i.e. it was saved before Phase 234, when the
      overall still averaged a Not-assessed dimension in as 0. Every surface
      shows "Recalculate to apply the updated overall", never a maturity
      level. Checked first: such a score cannot even rule out newer answers.
    - "stale" (Phase 234 review D-27, CR-01): a current-format score whose
      answers changed after it was saved (``stale`` is ``is_score_stale``'s
      result). Its overall no longer describes the answers, so every surface
      shows "Stale — recalculate", never a maturity level or "N of 4
      dimensions assessed".
    - "current": the score was saved with its answered counts (D-14 overall)
      and the live answers still match them.
    """
    if score_data is None:
        return None
    if not (isinstance(score_data, Mapping) and isinstance(
        score_data.get("answered_by_dimension"), Mapping
    )):
        return "recalculate"
    if stale:
        return "stale"
    return "current"


def is_score_stale(
    answered: Dict[str, int],
    scored_answered: Optional[Dict[str, int]],
    *,
    score_has_counts: bool = True,
) -> bool:
    """Session-level stale flag (Phase 234 D-15 / D-25).

    True when ``score_has_counts`` is False and any dimension is assessed
    live (D-25: a legacy score cannot rule out newer answers). Otherwise
    True when any live-assessed dimension's answered count differs from the
    count persisted with the score, or has no persisted count at all
    (Tampering, T-234-02). Same precedence as row_coverage_status:
    a dimension with zero live answers never makes the score stale.
    D-21: counts, not values (see row_coverage_status).
    """
    live_assessed = [
        d for d in DIMENSIONS if is_dimension_assessed(answered.get(d, 0))
    ]
    if not score_has_counts:
        return bool(live_assessed)
    if scored_answered is None:
        return False
    # A count missing for a live-assessed dimension reads stale (None != n):
    # a persisted blob can never vouch for answers it does not count.
    return any(
        scored_answered.get(d) != answered.get(d, 0) for d in live_assessed
    )
