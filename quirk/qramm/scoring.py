"""QRAMM weakest-link scoring engine — Phase 51 QRAMM-04.

Formulas verified from github.com/csnp/qramm/framework/scoring-methodology.md:

  Practice Score  = sum(question_scores) / len(question_scores)
  Dimension Score = min(practice_A, practice_B, practice_C)   <- weakest-link (D-06)
  Overall Score   = mean(weighted_CVI, weighted_SGRM, weighted_DPE, weighted_ITR)
  Weighted Score  = dimension_score * profile_multiplier

D-09 ISOLATION CONSTRAINT: This module MUST NOT import risk_engine, any
scanner module, quirk.db, or quirk.models. Only stdlib + typing. This
prevents circular imports and is enforced by Phase 53's evidence bridge
design (QRAMM-12).
"""
from __future__ import annotations

from typing import Dict, List


def compute_practice_score(answers: List[int]) -> float:
    """Average of question answers within a single practice area.

    CSNP toolkit uses 4-point scale (1-4). Empty list returns 0.0.
    Result rounded to 4 decimal places to avoid float representation noise.
    """
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
) -> Dict[str, object]:
    """Compute overall QRAMM score from 4 dimension scores.

    Applies profile multiplier to each dimension score, then averages.
    Returns a dict with overall, weighted dimensions, and maturity label.

    Args:
      dimension_scores: keys "CVI", "SGRM", "DPE", "ITR" -> float (1.0-4.0)
      multiplier: profile multiplier (typically 0.8-1.5; default 1.0 neutral)
    """
    dims = ["CVI", "SGRM", "DPE", "ITR"]
    weighted = {d: round(dimension_scores.get(d, 0.0) * multiplier, 4) for d in dims}
    overall = round(sum(weighted.values()) / len(dims), 4)
    return {
        "overall": overall,
        "dimensions": weighted,
        "maturity": _maturity_label(overall),
        "profile_multiplier": multiplier,
    }


def _maturity_label(score: float) -> str:
    """Map aggregated score to CSNP maturity level name.

    Thresholds verified from github.com/csnp/qramm/framework/maturity-levels.md:
      1.0-1.4: Basic
      1.5-2.4: Developing
      2.5-3.4: Established
      3.5-3.9: Advanced
      4.0:     Optimizing
    """
    if score >= 4.0:
        return "Optimizing"
    if score >= 3.5:
        return "Advanced"
    if score >= 2.5:
        return "Established"
    if score >= 1.5:
        return "Developing"
    return "Basic"
