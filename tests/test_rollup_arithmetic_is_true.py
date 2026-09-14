"""The rendered rollup equation must be arithmetically TRUE on every surface.

Until 2026-09-14 every report surface rendered `raw_sum ÷ divisor = <score>`
with the **capped** score on the right-hand side. On a capped estate that
sentence is false. The multihost reference estate printed:

    Rollup: 76 ÷ 1.25 = 15 / 100

76 ÷ 1.25 is 61. 15 is what the consequence ceiling compressed 61 down to. The
cap was separately disclosed in a `Cap reason:` line, so no information was
missing — but the equation itself did not compute, and a client checking a
two-digit division on the scoring page finds what looks like a arithmetic bug
in the product.

This suite pins two distinct things:

1. `rollup_computed_score()` agrees with `compute_readiness_score()`'s OWN
   pre-cap value. The renderer re-derives that number (it is not exposed as a
   structured key — it survives only inside `rating_cap_reason` prose as
   "(computed N)"), so this is the guard that keeps the re-derivation honest if
   the model's derivation ever moves. It compares against the model's prose
   rather than against a hard-coded constant, so it cannot go stale when the
   scoring model legitimately changes the number.

2. The Markdown surfaces actually render a true equation.

Deliberately NOT asserted: the exact wording of the capped sentence. The three
Markdown/DOCX/HTML surfaces have always differed in markup, and pinning prose
here would make this a change-detector rather than a correctness test.
"""
from __future__ import annotations

import re
from typing import Any, Dict

import pytest

from quirk.intelligence.scoring import compute_readiness_score
from quirk.reports.content_model import (
    effective_score_divisor,
    rollup_computed_score,
)

_COMPUTED_RE = re.compile(r"\(computed (\d+)\)")


def _capped_estate() -> Dict[str, Any]:
    """An estate with open CRITICALs, so the consequence ceiling fires.

    Shaped like the measured 31-host multihost chaos-lab estate (2026-09-14),
    which is the case that exposed the defect.
    """
    return {
        "totals": {"endpoints": 370, "findings": 400},
        "protocol_counts": {
            "TLS": 40, "HTTP": 10, "SSH": 3, "UNKNOWN": 2,
            "POSTGRESQL": 1, "S3": 1, "SAML": 1,
        },
        "assessable_endpoint_count": 38,
        "plaintext_http_count": 10,
        "http_on_tls_port_count": 0,
        "mtls_present_count": 0,
        "cert_key_type_counts": {"RSA": 18, "ECDSA": 1},
        "certificate_observations": {
            "certs_observed": 17,
            "expired_count": 5,
            "expiring_count": 1,
            "self_signed_count": 3,
        },
        "scan_error": {"count": 335, "rate": 0.9054},
        "finding_severity_counts": {
            "CRITICAL": 5, "HIGH": 14, "MEDIUM": 33, "LOW": 16, "INFO": 332,
        },
    }


def _raw_sum(result: Dict[str, Any]) -> int:
    """Sum of the ASSESSED subscores — an unassessed domain is None, not 0."""
    return sum(v for v in (result.get("subscores") or {}).values() if v is not None)


def test_helper_agrees_with_the_models_own_precap_value() -> None:
    """The re-derivation must reproduce what compute_readiness_score computed.

    This is the anti-drift guard named in `rollup_computed_score`'s docstring:
    the pre-cap value is not a structured key, so if scoring.py ever changes how
    it derives the pre-cap total, this fails instead of the product silently
    printing a wrong equation into a client report.
    """
    result = compute_readiness_score(_capped_estate())
    reason = result.get("rating_cap_reason") or ""
    match = _COMPUTED_RE.search(reason)
    assert match, (
        "This fixture is supposed to be a CAPPED estate, but rating_cap_reason "
        f"carries no '(computed N)': {reason!r}. If the scoring model changed so "
        "that 5 open CRITICALs no longer cap, re-shape the fixture to something "
        "that does cap — do NOT delete this test, and do NOT relax the model to "
        "make it pass (999.113 D5: never tune to a target)."
    )
    model_precap = int(match.group(1))

    divisor = effective_score_divisor(result["score"], result.get("score_divisor"))
    assert rollup_computed_score(_raw_sum(result), divisor) == model_precap


def test_the_capped_case_is_actually_exercised() -> None:
    """Guard against this suite passing vacuously on an uncapped fixture.

    If the emitted score equalled the computed one, every assertion above would
    hold trivially and the regression would be undetected.
    """
    result = compute_readiness_score(_capped_estate())
    divisor = effective_score_divisor(result["score"], result.get("score_divisor"))
    computed = rollup_computed_score(_raw_sum(result), divisor)
    assert computed != result["score"], (
        "Fixture is no longer capped — the test would pass without proving "
        f"anything (computed {computed} == emitted {result['score']})."
    )


@pytest.mark.parametrize("raw_sum,divisor,expected", [
    (76, 1.25, 61),      # the measured multihost case: 60.8 -> 61
    (100, 1.0, 100),     # full coverage, no rescale
    (150, 1.5, 100),     # legacy six-domain divisor
    (0, 1.25, 0),        # floor
])
def test_rollup_arithmetic(raw_sum: int, divisor: float, expected: int) -> None:
    assert rollup_computed_score(raw_sum, divisor) == expected


@pytest.mark.parametrize("raw_sum,divisor", [(None, 1.25), (76, None), (76, 0)])
def test_missing_inputs_return_none(raw_sum, divisor) -> None:
    """Matches effective_score_divisor()'s contract so callers guard once."""
    assert rollup_computed_score(raw_sum, divisor) is None


class _StubAssessment:
    report_owner = "TEST OWNER"
    data_classification = "confidential"
    name = "Test Assessment"
    branding = None


class _StubCfg:
    assessment = _StubAssessment()


def test_markdown_scorecard_equation_is_true() -> None:
    """The scorecard's rendered rollup line must divide correctly.

    Parses the numbers back out of the rendered Markdown and checks the
    division, rather than asserting a fixed sentence — so a wording change does
    not fail this, but a false equation does.
    """
    from quirk.reports.writer import _scorecard_markdown  # noqa: PLC0415

    result = compute_readiness_score(_capped_estate())
    # The renderer reads `total`, the model returns `score` (writer.py:349 vs
    # scoring.py's return dict) — a translation the report pipeline performs
    # upstream. Bridge it here explicitly rather than silently, so this test
    # fails loudly if that seam moves instead of quietly rendering no rollup.
    rendered_score = {**result, "total": result["score"]}
    md = _scorecard_markdown(_StubCfg(), rendered_score, {"confidence": 64}, [], [])

    match = re.search(r"\*\*Rollup:\*\*\s*(\d+)\s*÷\s*([\d.]+)\s*=\s*\*\*(\d+)", md)
    assert match, f"No rollup line found in rendered scorecard:\n{md}"
    raw_sum, divisor, rendered = int(match.group(1)), float(match.group(2)), int(match.group(3))
    assert rendered == int(round(raw_sum / divisor)), (
        f"Rendered rollup does not compute: {raw_sum} / {divisor} = "
        f"{raw_sum / divisor:.2f}, but the report printed {rendered}.\n{md}"
    )
