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

from typing import Dict, Iterable, Tuple

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


def row_coverage_status(dimension: str, answered: int) -> RowCoverageStatus:
    """Per-session coverage status for a compliance-map row (D-02, D-02a).

    Not assessed -> "pending" for every dimension. Assessed -> the scanner
    status when the scanner covers the dimension ("covered"/"partial"),
    "n/a" when the dimension is intentionally out of scope, otherwise
    "self-assessed".
    """
    if not is_dimension_assessed(answered):
        return "pending"
    static = SCANNER_COVERAGE_STATUS.get(dimension)
    if static in ("covered", "partial"):
        return static
    if static == "n/a":
        return "n/a"
    return "self-assessed"
