"""QRAMM weakest-link scoring engine — Phase 51 QRAMM-04.

Formulas verified from github.com/csnp/qramm/framework/scoring-methodology.md:

  Practice Score  = sum(question_scores) / len(question_scores)
  Dimension Score = min(practice_A, practice_B, practice_C)   <- weakest-link (D-06)
  Overall Score   = mean(weighted score of each ASSESSED dimension)
                    (Phase 234 D-14: Not-assessed dimensions are excluded;
                    None when no dimension is assessed)
  Weighted Score  = dimension_score * profile_multiplier

D-09 ISOLATION CONSTRAINT: This module MUST NOT import risk_engine, any
scanner module, quirk.db, or quirk.models. Only stdlib + typing. This
prevents circular imports and is enforced by Phase 53's evidence bridge
design (QRAMM-12).
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple


def compute_practice_score(answers: List[int], practice_id: str = "") -> float:
    """Average of question answers within a single practice area.

    CSNP toolkit uses 0-4 scale (D-01 widens docstring's "1-4" to {0,1,2,3,4}).
    Empty list returns 0.0. Out-of-range answers fail loud (D-01 / WR-02) BEFORE
    summation — no silent clamping. Result rounded to 4 decimal places to avoid
    float representation noise.
    """
    for answer in answers:
        if answer not in (0, 1, 2, 3, 4):
            raise ValueError(
                f"Practice score answer {answer!r} for {practice_id} out of range [0, 4]"
            )
    if not answers:
        return 0.0
    return round(sum(answers) / len(answers), 4)


def compute_dimension_score(practice_scores: List[float]) -> float:
    """Weakest-link rule (D-06): minimum of the 3 practice scores.

    NOT an average — this is the defining QRAMM scoring decision per
    CSNP scoring-methodology.md.
    """
    if not practice_scores:
        return 0.0
    return min(practice_scores)


def compute_overall_score(
    dimension_scores: Dict[str, float],
    multiplier: float = 1.0,
    *,
    assessed: Iterable[str],
) -> Dict[str, object]:
    """Compute overall QRAMM score from the ASSESSED dimension scores.

    Applies profile multiplier to each dimension score, then averages the
    weighted scores of the assessed dimensions only. Returns a dict with
    overall, weighted dimensions (all four), maturity label and the
    assessed-dimension disclosure ("N of 4 assessed").

    Phase 234 D-14 (SCORE-10): a Not-assessed dimension is EXCLUDED from the
    mean, never averaged in as 0 (SCOREFIX-02's 0.0 is a placeholder, not a
    measurement). When no dimension is assessed the overall is None and the
    maturity is "Indeterminate". The assessed set is supplied by the caller
    (quirk.qramm.assessment_state.is_dimension_assessed over the answered
    counts) so this module stays stdlib-only (D-09 isolation). ``assessed``
    is keyword-only and has NO default: a default of "all four" would
    silently restore the defect.

    Args:
      dimension_scores: keys "CVI", "SGRM", "DPE", "ITR" -> float (0.0-4.0)
      multiplier: profile multiplier (typically 0.8-1.5; default 1.0 neutral)
      assessed: the dimension names that have at least one answered question
    """
    dims = ["CVI", "SGRM", "DPE", "ITR"]
    weighted = {d: round(min(4.0, dimension_scores.get(d, 0.0) * multiplier), 4) for d in dims}
    assessed_set = set(assessed)
    included = [d for d in dims if d in assessed_set]
    # QC-04: clamp the overall average at the function level so compute_overall_score
    # can never return a value above 4.0 regardless of multiplier, matching the
    # per-dimension min(4.0, ...) clamp applied to weighted above.
    overall: Optional[float] = None
    if included:
        overall = round(min(4.0, sum(weighted[d] for d in included) / len(included)), 4)
    return {
        "overall": overall,
        "dimensions": weighted,
        "maturity": _maturity_label(overall),
        "profile_multiplier": multiplier,
        "assessed_dimensions": included,
        "dimensions_assessed": len(included),
        "dimensions_total": len(dims),
    }


# The one overall maturity mapping, (floor, label), highest first. Phase 234
# code review D-31 (WR-05): the CSNP levels start at Basic = 1.0, so a mean
# below 1.0 has no CSNP level; it used to fall through to "Basic", beside a
# number below Basic's own floor. Under SCOREFIX-02 a partly answered
# dimension scores 0.0 (weakest link over its placeholder practices), so
# sub-1.0 overalls are common (the shared contract's 0.6667). They now read
# "Below Basic". The TS twin (src/dashboard/src/lib/qramm-assessment.ts
# OVERALL_MATURITY_LEVELS) and this table are both pinned to the contract
# fixture's overall_maturity_levels, so neither can drift alone.
OVERALL_MATURITY_LEVELS: Tuple[Tuple[float, str], ...] = (
    (3.95, "Optimizing"),
    (3.5, "Advanced"),
    (2.5, "Established"),
    (1.5, "Developing"),
    (1.0, "Basic"),
    (0.0, "Below Basic"),
)


def _maturity_label(score: float | None) -> str:
    """Map aggregated score to CSNP maturity level name.

    Thresholds verified from github.com/csnp/qramm/framework/maturity-levels.md:
      None:    Indeterminate  (D-03 / WR-05: no algos found → cannot grade)
      <1.0:    Below Basic    (Phase 234 review D-31: below CSNP's Basic floor)
      1.0-1.4: Basic
      1.5-2.4: Developing
      2.5-3.4: Established
      3.5-3.94: Advanced
      >=3.95:  Optimizing  (D-04 / WR-06: lowered from 4.0 to absorb FP noise at sub-1.0 multipliers)
    """
    if score is None:
        return "Indeterminate"
    for floor, label in OVERALL_MATURITY_LEVELS:
        if score >= floor:
            return label
    return OVERALL_MATURITY_LEVELS[-1][1]
