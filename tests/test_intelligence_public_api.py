"""Phase 77 D-15 / cbom-intel-reports/IN-09 — IntelligenceReport public-API
CI assertion.

User-directed pivot (override of original CONTEXT D-15 cascade-delete):
`IntelligenceReport` has live importers (`tests/test_intelligence_schema.py`
exercises its fields and constructs it). It is therefore the typed return
shape — preserved, NOT deleted. This module asserts:

  1. The dataclass remains importable from both `quirk.intelligence.schema`
     and the package re-export `quirk.intelligence`.
  2. The class carries a module-level docstring marking it as the typed
     return shape (preventing accidental future re-deletion).
  3. The live importer test module actually exercises the dataclass fields
     (the "CI assertion that importers actually use its fields" requirement).

If a future refactor decides to delete the dataclass, this test fails first
and forces the importer cascade to be re-examined.
"""
from __future__ import annotations

import inspect
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_intelligence_report_is_in_public_api() -> None:
    """Phase 77 D-15 pivot: IntelligenceReport REMAINS in the public API."""
    from quirk import intelligence

    assert hasattr(intelligence, "IntelligenceReport"), (
        "Phase 77 D-15 pivot: IntelligenceReport must remain exported from "
        "quirk.intelligence (cbom-intel-reports/IN-09)"
    )
    assert "IntelligenceReport" in getattr(intelligence, "__all__", []), (
        "IntelligenceReport must remain listed in quirk.intelligence.__all__"
    )


def test_intelligence_report_importable_from_schema() -> None:
    from quirk.intelligence.schema import IntelligenceReport  # noqa: F401


def test_intelligence_report_has_typed_return_shape_docstring() -> None:
    """The class must self-document its role as the typed return shape (D-15 pivot).

    This prevents a future refactor from quietly re-deleting the dataclass
    without re-examining the live importers.
    """
    from quirk.intelligence.schema import IntelligenceReport

    doc = inspect.getdoc(IntelligenceReport) or ""
    lower = doc.lower()
    assert doc, (
        "Phase 77 D-15 pivot: IntelligenceReport must have a docstring "
        "marking it as the typed return shape (cbom-intel-reports/IN-09)"
    )
    assert "typed return shape" in lower, (
        "IntelligenceReport docstring must explicitly state 'typed return shape' "
        "so future readers understand why the dataclass is preserved (D-15 pivot)"
    )


def test_live_importer_exercises_intelligence_report_fields() -> None:
    """CI assertion: tests/test_intelligence_schema.py must actually exercise
    IntelligenceReport's fields (not just import it).

    Without this gate, a future maintainer could trim the importer to a bare
    `from ... import IntelligenceReport` line — making the dataclass look
    unused and reopening the IN-09 cascade-delete question.
    """
    importer = REPO_ROOT / "tests" / "test_intelligence_schema.py"
    assert importer.exists(), "live importer module must exist"

    src = importer.read_text(encoding="utf-8")
    assert "IntelligenceReport(" in src, (
        "Live importer must construct IntelligenceReport(...) — proves field exercise"
    )
    # Verify the importer touches the actual dataclass fields (not just the symbol).
    for field in ("generated_utc", "score_inputs", "score_result", "confidence_result", "roadmap"):
        assert field in src, (
            f"Live importer test_intelligence_schema.py must exercise the "
            f"'{field}' field of IntelligenceReport (Phase 77 D-15 pivot CI guard)"
        )
