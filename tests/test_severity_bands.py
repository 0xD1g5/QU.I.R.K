"""Phase 184.4 — quirk/severity_bands.py unit + import-boundary coverage
(SCORE-05 / D-04, D-01, D-02).

Covers:
  1. band_for_score() boundary walk (off-by-one is the realistic defect).
  2. band_for_score() agrees with quirk.intelligence.scoring._rating() for
     every score 0..100 — the migration-safety proof that the extracted
     chain is behaviourally identical to the pre-184.4-04 one it replaces.
     Running this BEFORE plan 184.4-04 rewires _rating() is what actually
     proves the extraction was faithful; after that rewiring this becomes
     trivially true by construction.
  3-4. cap_band_for_severity() identity + no-graduated-ladder (D-02).
  5. The D-13 reproduction numbers: 89 + 1 CRITICAL -> FAIR.
  6. cap_reason() shape and no-finding-argument guarantee.
  7-8. Import-boundary tests (D-04) — parsed with ast at run time, per the
     project's standing "derive, don't enumerate" rule (CLAUDE.md TOOL-04 /
     182-07): no hand-written list of allowed imports.
"""
from __future__ import annotations

import ast
import inspect

import pytest

from quirk.severity_bands import (
    BAND_ORDER,
    BAND_THRESHOLDS,
    BAND_CRITICAL_ALLOWANCE,
    band_for_score,
    cap_band_for_severity,
    cap_reason,
)


# ---------------------------------------------------------------------------
# 1. band_for_score boundary walk
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("score,expected_band", [
    (100, "EXCELLENT"),
    (85, "EXCELLENT"),   # D-02 locked boundary
    (84, "GOOD"),
    (70, "GOOD"),        # D-02 locked boundary
    (69, "MODERATE"),
    (55, "MODERATE"),    # D-02 locked boundary
    (54, "FAIR"),
    (35, "FAIR"),        # D-02 locked boundary
    (34, "POOR"),
    (0, "POOR"),
])
def test_band_for_score_boundaries(score, expected_band):
    assert band_for_score(score) == expected_band


# ---------------------------------------------------------------------------
# 2. Migration-safety proof: band_for_score agrees with the pre-existing
#    quirk.intelligence.scoring._rating() for every possible score.
# ---------------------------------------------------------------------------

def test_band_for_score_agrees_with_rating_for_every_score():
    from quirk.intelligence.scoring import _rating

    for score in range(0, 101):
        assert band_for_score(score) == _rating(score), (
            f"band_for_score({score}) diverges from _rating({score}) — the "
            "extraction is not behaviourally identical to the pre-184.4-04 "
            "hardcoded chain."
        )


# ---------------------------------------------------------------------------
# 3. cap_band_for_severity identity at critical_count=0
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("band", BAND_ORDER)
def test_cap_band_identity_when_no_critical(band):
    assert cap_band_for_severity(band, 0) == band


# ---------------------------------------------------------------------------
# 4. No-graduated-ladder assertion (D-02) — same result for 1, 2, 7.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("critical_count", [1, 2, 7])
@pytest.mark.parametrize("numeric_band,expected_capped", [
    ("EXCELLENT", "FAIR"),
    ("GOOD", "FAIR"),
    ("MODERATE", "FAIR"),
    ("FAIR", "FAIR"),
    ("POOR", "POOR"),
])
def test_cap_band_no_graduated_ladder(critical_count, numeric_band, expected_capped):
    assert cap_band_for_severity(numeric_band, critical_count) == expected_capped


# ---------------------------------------------------------------------------
# 5. D-13 reproduction numbers.
# ---------------------------------------------------------------------------

def test_d13_reproduction_89_with_one_critical_yields_fair():
    numeric_band = band_for_score(89)
    assert numeric_band == "EXCELLENT"
    assert cap_band_for_severity(numeric_band, 1) == "FAIR"


# ---------------------------------------------------------------------------
# 6. cap_reason shape.
# ---------------------------------------------------------------------------

def test_cap_reason_none_when_uncapped():
    assert cap_reason("FAIR", "FAIR", 0, 40) is None
    assert cap_reason("POOR", "POOR", 5, 10) is None


def test_cap_reason_capped_contains_band_count_and_score():
    reason = cap_reason("EXCELLENT", "FAIR", 1, 89)
    assert reason is not None
    assert "Band capped at" in reason
    assert "FAIR" in reason
    assert "1 CRITICAL" in reason
    assert "89" in reason


def test_cap_reason_signature_accepts_no_finding_argument():
    """D-09: the string must never be built from a finding's title/description."""
    params = list(inspect.signature(cap_reason).parameters)
    assert params == ["numeric_band", "capped_band", "critical_count", "score"], (
        "cap_reason() gained a parameter that could carry finding-derived text; "
        "D-09 requires the reason string to be built only from static band "
        "names and integers."
    )


# ---------------------------------------------------------------------------
# 7. Import-boundary test: content_model.py's only `quirk`-rooted import must
#    be quirk.severity_bands (D-04). Parsed with ast at run time — no
#    hand-written list of allowed imports.
# ---------------------------------------------------------------------------

def test_content_model_only_imports_severity_bands_from_quirk():
    import quirk.reports.content_model as content_model

    source = inspect.getsource(content_model)
    tree = ast.parse(source, filename=content_model.__file__)

    quirk_rooted_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("quirk"):
            quirk_rooted_imports.append(node.module)
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("quirk"):
                    quirk_rooted_imports.append(alias.name)

    assert quirk_rooted_imports == ["quirk.severity_bands"], (
        f"content_model.py's quirk-rooted imports are {quirk_rooted_imports!r}, "
        "expected exactly ['quirk.severity_bands']. content_model.py must stay "
        "stdlib-only plus this one shared module to preserve its pre-I/O guard "
        "property (D-04)."
    )


# ---------------------------------------------------------------------------
# 8. Import-boundary test: severity_bands.py itself has zero quirk imports.
# ---------------------------------------------------------------------------

def test_severity_bands_module_is_stdlib_only():
    import quirk.severity_bands as severity_bands

    source = inspect.getsource(severity_bands)
    tree = ast.parse(source, filename=severity_bands.__file__)

    quirk_rooted_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("quirk"):
            quirk_rooted_imports.append(node.module)
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("quirk"):
                    quirk_rooted_imports.append(alias.name)

    assert quirk_rooted_imports == [], (
        f"quirk/severity_bands.py has quirk-rooted imports {quirk_rooted_imports!r} "
        "— it must remain stdlib-only so it can be safely imported from both "
        "quirk/intelligence and quirk/reports (D-04)."
    )


# ---------------------------------------------------------------------------
# Sanity: BAND_THRESHOLDS / BAND_CRITICAL_ALLOWANCE key-set contracts.
# ---------------------------------------------------------------------------

def test_poor_not_a_threshold_key_but_is_an_allowance_key():
    assert "POOR" not in BAND_THRESHOLDS
    assert "POOR" in BAND_CRITICAL_ALLOWANCE
    assert BAND_CRITICAL_ALLOWANCE["POOR"] is None
