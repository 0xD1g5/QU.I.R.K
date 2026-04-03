"""
Tests confirming single scoring path through intelligence/scoring.py in writer.py.

These tests use ast/inspect to verify import sources in writer.py:
- writer.py MUST import compute_readiness_score from quirk.intelligence.scoring
- writer.py MUST NOT import from quirk.assessment.readiness_score
- writer.py MUST import build_evidence_summary from quirk.intelligence.evidence

RED phase: tests fail until writer.py imports are consolidated.
"""
import ast
import importlib.util
import pathlib
import unittest


def _get_writer_source() -> str:
    writer_path = pathlib.Path(__file__).parent.parent / "quirk" / "reports" / "writer.py"
    return writer_path.read_text(encoding="utf-8")


def _collect_imports(source: str):
    """Parse all import statements from source, return list of (module, names) tuples."""
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [alias.name for alias in node.names]
            imports.append((module, names))
    return imports


class ScoringConsolidationImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = _get_writer_source()
        self.imports = _collect_imports(self.source)

    def test_no_assessment_readiness_import(self) -> None:
        """writer.py must NOT import from quirk.assessment.readiness_score."""
        for module, names in self.imports:
            self.assertNotEqual(
                module,
                "quirk.assessment.readiness_score",
                f"Found forbidden import 'from quirk.assessment.readiness_score import {names}' in writer.py",
            )

    def test_no_assessment_transition_planner_import(self) -> None:
        """writer.py must NOT import from quirk.assessment.transition_planner."""
        for module, names in self.imports:
            self.assertNotEqual(
                module,
                "quirk.assessment.transition_planner",
                f"Found forbidden import 'from quirk.assessment.transition_planner import {names}' in writer.py",
            )

    def test_no_assessment_confidence_import(self) -> None:
        """writer.py must NOT import from quirk.assessment.confidence."""
        for module, names in self.imports:
            self.assertNotEqual(
                module,
                "quirk.assessment.confidence",
                f"Found forbidden import 'from quirk.assessment.confidence import {names}' in writer.py",
            )

    def test_scoring_uses_intelligence_module(self) -> None:
        """writer.py must import compute_readiness_score from quirk.intelligence.scoring."""
        found = any(
            module == "quirk.intelligence.scoring" and "compute_readiness_score" in names
            for module, names in self.imports
        )
        self.assertTrue(
            found,
            "Expected 'from quirk.intelligence.scoring import compute_readiness_score' in writer.py",
        )

    def test_uses_build_evidence_summary(self) -> None:
        """writer.py must import build_evidence_summary from quirk.intelligence.evidence."""
        found = any(
            module == "quirk.intelligence.evidence" and "build_evidence_summary" in names
            for module, names in self.imports
        )
        self.assertTrue(
            found,
            "Expected 'from quirk.intelligence.evidence import build_evidence_summary' in writer.py",
        )

    def test_no_score_from_evidence_function(self) -> None:
        """Dead function _score_from_evidence must be deleted from writer.py."""
        self.assertNotIn(
            "_score_from_evidence",
            self.source,
            "_score_from_evidence is dead code and must be removed from writer.py",
        )

    def test_no_normalize_evidence_function(self) -> None:
        """Dead function _normalize_evidence must be deleted from writer.py."""
        self.assertNotIn(
            "_normalize_evidence",
            self.source,
            "_normalize_evidence is dead code and must be removed from writer.py",
        )


def _get_executive_source() -> str:
    exec_path = pathlib.Path(__file__).parent.parent / "quirk" / "reports" / "executive.py"
    return exec_path.read_text(encoding="utf-8")


class ExecutiveConsolidationTests(unittest.TestCase):
    """Wave 0 RED stubs for executive.py migration (Plan 02).

    Each test is marked expectedFailure because executive.py still imports from
    quirk.assessment.*. These decorators are removed in Plan 02 after migration.
    """

    def setUp(self) -> None:
        self.source = _get_executive_source()
        self.imports = _collect_imports(self.source)

    @unittest.expectedFailure
    def test_executive_no_assessment_readiness_import(self) -> None:
        """executive.py must NOT import from quirk.assessment.readiness_score."""
        for module, names in self.imports:
            self.assertNotEqual(
                module,
                "quirk.assessment.readiness_score",
                f"Found forbidden import 'from quirk.assessment.readiness_score import {names}' in executive.py",
            )

    @unittest.expectedFailure
    def test_executive_no_assessment_confidence_import(self) -> None:
        """executive.py must NOT import from quirk.assessment.confidence."""
        for module, names in self.imports:
            self.assertNotEqual(
                module,
                "quirk.assessment.confidence",
                f"Found forbidden import 'from quirk.assessment.confidence import {names}' in executive.py",
            )

    @unittest.expectedFailure
    def test_executive_no_assessment_transition_planner_import(self) -> None:
        """executive.py must NOT import from quirk.assessment.transition_planner."""
        for module, names in self.imports:
            self.assertNotEqual(
                module,
                "quirk.assessment.transition_planner",
                f"Found forbidden import 'from quirk.assessment.transition_planner import {names}' in executive.py",
            )

    @unittest.expectedFailure
    def test_executive_no_assessment_interpretation_import(self) -> None:
        """executive.py must NOT import from quirk.assessment.interpretation_engine."""
        for module, names in self.imports:
            self.assertNotEqual(
                module,
                "quirk.assessment.interpretation_engine",
                f"Found forbidden import 'from quirk.assessment.interpretation_engine import {names}' in executive.py",
            )

    @unittest.expectedFailure
    def test_executive_uses_intelligence_scoring(self) -> None:
        """executive.py must import compute_readiness_score from quirk.intelligence.scoring."""
        found = any(
            module == "quirk.intelligence.scoring" and "compute_readiness_score" in names
            for module, names in self.imports
        )
        self.assertTrue(
            found,
            "Expected 'from quirk.intelligence.scoring import compute_readiness_score' in executive.py",
        )

    @unittest.expectedFailure
    def test_executive_uses_intelligence_evidence(self) -> None:
        """executive.py must import build_evidence_summary from quirk.intelligence.evidence."""
        found = any(
            module == "quirk.intelligence.evidence" and "build_evidence_summary" in names
            for module, names in self.imports
        )
        self.assertTrue(
            found,
            "Expected 'from quirk.intelligence.evidence import build_evidence_summary' in executive.py",
        )

    @unittest.expectedFailure
    def test_executive_uses_now_next_later_roadmap(self) -> None:
        """executive.py roadmap must use NOW/NEXT/LATER labels, not wave_1/wave_2/wave_3."""
        self.assertIn("NOW", self.source, "Expected 'NOW' label in executive.py roadmap output")
        self.assertIn("NEXT", self.source, "Expected 'NEXT' label in executive.py roadmap output")
        self.assertIn("LATER", self.source, "Expected 'LATER' label in executive.py roadmap output")
        self.assertNotIn("wave_1", self.source, "Deprecated 'wave_1' attribute found in executive.py")
        self.assertNotIn("wave_2", self.source, "Deprecated 'wave_2' attribute found in executive.py")
        self.assertNotIn("wave_3", self.source, "Deprecated 'wave_3' attribute found in executive.py")


if __name__ == "__main__":
    unittest.main()
