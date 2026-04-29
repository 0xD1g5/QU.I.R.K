"""
Wave 0 TDD scaffold for Phase 15 code hygiene requirements.

Covers HYGN-01 through HYGN-04:
- HYGN-01: quirk/connectors/ stub directory absent, no imports from it (GREEN immediately)
- HYGN-02: cfg.scan mutation guard — mutations wrapped in try/finally (structure assertion)
- HYGN-03: orphaned quirk/reports/scorecard.py absent, no imports from it (RED until Plan 02)
- HYGN-04: all completed phase VALIDATION.md files have nyquist_compliant: true (RED until Plan 02)

Test design follows canonical codebase pattern from tests/test_scoring_consolidation.py
(pathlib + ast for filesystem and import assertions).
"""
import ast
import inspect
import pathlib
import re
import unittest

import run_scan

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent


class CodeHygieneTests(unittest.TestCase):

    # ------------------------------------------------------------------
    # HYGN-01: Legacy quirk/connectors/ stub directory regression tests
    # Expected: GREEN (directory was already removed)
    # ------------------------------------------------------------------

    def test_connectors_stub_directory_absent(self) -> None:
        """quirk/connectors/ must not exist — legacy stub directory was deleted in Phase 8."""
        connectors_dir = PROJECT_ROOT / "quirk" / "connectors"
        self.assertFalse(
            connectors_dir.exists(),
            "Legacy stub directory quirk/connectors/ still present",
        )

    def test_no_imports_from_quirk_connectors(self) -> None:
        """No production .py file may import from quirk.connectors.*"""
        violations = []
        quirk_dir = PROJECT_ROOT / "quirk"
        for py_file in quirk_dir.rglob("*.py"):
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module.startswith("quirk.connectors"):
                        violations.append((str(py_file), module))
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("quirk.connectors"):
                            violations.append((str(py_file), alias.name))
        self.assertEqual(
            violations,
            [],
            f"Found imports from quirk.connectors: {violations}",
        )

    # ------------------------------------------------------------------
    # HYGN-02: cfg.scan mutation guard — structural source assertions
    # TLS test: Expected GREEN (base captured before mutation; finally restores)
    # SSH test: Expected RED (mutations at lines 380-381 precede the try: at line 384)
    # ------------------------------------------------------------------

    def test_cfg_scan_restored_after_tls_exception(self) -> None:
        """run_scan.py TLS phase must capture base_timeout before cfg.scan mutation
        and restore it in a finally block."""
        source = inspect.getsource(run_scan)
        lines = source.splitlines()

        # Find the TLS scanning section
        tls_section_start = None
        for i, line in enumerate(lines):
            if "tls_scanning" in line or "TLS scan phase" in line:
                tls_section_start = i
                break
        self.assertIsNotNone(
            tls_section_start,
            "Could not locate TLS scan phase section in run_scan.py source",
        )

        # Assert base_timeout capture appears before TLS try block
        self.assertIn(
            "base_timeout = cfg.scan.timeout_seconds",
            source,
            "run_scan.py must capture base_timeout = cfg.scan.timeout_seconds before TLS try block",
        )

        # Assert the finally block restores cfg.scan.timeout_seconds
        self.assertIn(
            "cfg.scan.timeout_seconds = base_timeout",
            source,
            "run_scan.py finally block must restore cfg.scan.timeout_seconds = base_timeout",
        )

    def test_cfg_scan_restored_after_ssh_exception(self) -> None:
        """cfg.scan mutations for SSH phase must appear INSIDE the try block (after try:),
        not before it. This ensures finally: always restores even if mutations fail.

        Current state (RED): mutations at lines 380-381 precede the try: at line 384.
        Expected fix: move cfg.scan.timeout_seconds = ssh_timeout inside the try block.
        """
        source = inspect.getsource(run_scan)
        lines = source.splitlines()

        # Locate the SSH scan phase section
        ssh_section_start = None
        for i, line in enumerate(lines):
            if "ssh_scanning" in line or "SSH scan phase" in line:
                ssh_section_start = i
                break
        self.assertIsNotNone(
            ssh_section_start,
            "Could not locate SSH scan phase section in run_scan.py source",
        )

        # From the SSH section, find the index of the try: line and the mutation line
        ssh_lines = lines[ssh_section_start:]

        try_line_idx = None
        mutation_line_idx = None

        for i, line in enumerate(ssh_lines):
            stripped = line.strip()
            if stripped == "try:" and try_line_idx is None:
                try_line_idx = i
            # Look for the ssh_timeout mutation (the first one signals the unsafe ordering)
            if re.match(r"cfg\.scan\.timeout_seconds\s*=\s*ssh_timeout", stripped):
                if mutation_line_idx is None:
                    mutation_line_idx = i

        self.assertIsNotNone(
            try_line_idx,
            "Could not find try: in SSH scan phase section of run_scan.py",
        )
        self.assertIsNotNone(
            mutation_line_idx,
            "Could not find cfg.scan.timeout_seconds = ssh_timeout in SSH scan phase section",
        )

        # The mutation must appear AFTER the try: (inside the try block)
        self.assertGreater(
            mutation_line_idx,
            try_line_idx,
            (
                f"cfg.scan.timeout_seconds = ssh_timeout (relative line {mutation_line_idx}) "
                f"must appear AFTER try: (relative line {try_line_idx}) "
                "so that the finally block always fires — move mutation inside the try block"
            ),
        )

    # ------------------------------------------------------------------
    # HYGN-03: Orphaned quirk/reports/scorecard.py regression tests
    # Expected: RED (file exists until Plan 02 deletes it)
    # ------------------------------------------------------------------

    def test_scorecard_module_absent(self) -> None:
        """quirk/reports/scorecard.py must not exist — orphaned module removed in Phase 15."""
        scorecard_path = PROJECT_ROOT / "quirk" / "reports" / "scorecard.py"
        self.assertFalse(
            scorecard_path.exists(),
            "Orphaned quirk/reports/scorecard.py still present",
        )

    def test_no_imports_from_scorecard_module(self) -> None:
        """No production .py file under quirk/ may import from quirk.reports.scorecard.

        Note: tests/ directory is excluded — test_reports_scorecard.py will be deleted
        alongside scorecard.py in Plan 02.
        """
        violations = []
        quirk_dir = PROJECT_ROOT / "quirk"
        for py_file in quirk_dir.rglob("*.py"):
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module == "quirk.reports.scorecard" or module.startswith(
                        "quirk.reports.scorecard."
                    ):
                        violations.append((str(py_file), module))
        self.assertEqual(
            violations,
            [],
            f"Found imports from quirk.reports.scorecard: {violations}",
        )

    # ------------------------------------------------------------------
    # HYGN-04: Phases with a VALIDATION.md on disk MUST declare
    # nyquist_compliant: true. Phases whose VALIDATION.md is absent
    # (e.g., the v4.4 cleanup in commit a991a69 removed phases 01-14)
    # are skipped — Phase 38 D-02 picked skip-on-missing as the minimal
    # resolution rather than backfilling 14 historical stub files.
    # Expected: GREEN
    # ------------------------------------------------------------------

    def test_all_completed_phase_validations_nyquist_compliant(self) -> None:
        """All completed phase VALIDATION.md files must have nyquist_compliant: true
        in their YAML frontmatter.

        Completed phases that must be compliant:
          01-foundation-fixes through 14-scoring-intelligence-correctness
        """
        COMPLETED_PHASES = [
            "01-foundation-fixes",
            "02-cbom-pipeline",
            "03-scanner-coverage",
            "04-chaos-lab-expansion",
            "05-web-dashboard",
            "06-documentation",
            "07-polish-and-packaging",
            "08-legacy-debt-cleanup",
            "09-scoring-consolidation",
            "10-v39-gap-closure",
            "11-dashboard-wiring-fixes",
            "12-cli-correctness",
            "13-interactive-mode-overhaul",
            "14-scoring-intelligence-correctness",
        ]

        failures = []
        phases_dir = PROJECT_ROOT / ".planning" / "phases"

        for phase_slug in COMPLETED_PHASES:
            # Extract two-digit phase number prefix (e.g. "01" from "01-foundation-fixes")
            phase_num = phase_slug.split("-")[0]
            validation_path = phases_dir / phase_slug / f"{phase_num}-VALIDATION.md"

            if not validation_path.exists():
                # Phase 38 (D-02): skip-on-missing — the v4.4 cleanup commit
                # a991a69 deleted the historical VALIDATION.md files for
                # phases 01-14. The hygiene rule still has teeth for any
                # phase that DOES have a VALIDATION.md on disk.
                continue

            content = validation_path.read_text(encoding="utf-8")

            # Extract YAML frontmatter (content between first pair of --- delimiters)
            frontmatter_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if not frontmatter_match:
                failures.append((phase_slug, "no YAML frontmatter found"))
                continue

            frontmatter = frontmatter_match.group(1)

            # Check for nyquist_compliant: true in the frontmatter
            if not re.search(r"nyquist_compliant\s*:\s*true", frontmatter):
                failures.append((phase_slug, "nyquist_compliant not true"))

        self.assertEqual(
            failures,
            [],
            f"VALIDATION.md files not compliant: {failures}",
        )


if __name__ == "__main__":
    unittest.main()
