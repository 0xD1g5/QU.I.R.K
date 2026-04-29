"""Phase 16 -- v4.1 Gap Closure RED scaffold.

Tests assert the correct end-state for CLI-04 and SCORE-04.
Both tests MUST FAIL before Plan 02 fixes land:
- CLI-04: importlib.metadata.version("quirk") returns "4.0.0" (pyproject.toml stale)
- SCORE-04: interactive.py output dir default is "output" (dashboard expects "quirk-output")
"""

import importlib.metadata
import pathlib
import unittest


class TestV41GapClosure(unittest.TestCase):
    """RED scaffold for Phase 16 v4.1 gap closure requirements CLI-04 and SCORE-04."""

    def test_package_manifest_version_is_4_1_0(self):
        """importlib.metadata.version('quirk') must return '4.1.0'.

        RED because: pyproject.toml has version = "4.0.0", installed egg-info
        reflects that value. importlib.metadata reads the installed egg-info,
        not the module __version__ attribute.
        """
        version = importlib.metadata.version("quirk")
        assert version == "4.4.0", (
            f"importlib.metadata.version('quirk') = {version!r}; "
            f"expected '4.4.0' -- bump pyproject.toml version field and reinstall"
        )

    def test_pyproject_version_field_is_4_1_0(self):
        """pyproject.toml must contain 'version = "4.4.0"' (Phase 37 v4.4 release).

        Name retained for git history; assertion bumped per Plan 37-04 sweep.
        """
        source = pathlib.Path("pyproject.toml").read_text(encoding="utf-8")
        assert 'version = "4.4.0"' in source, (
            "pyproject.toml does not contain 'version = \"4.4.0\"'"
        )

    def test_interactive_output_dir_default_is_quirk_output(self):
        """interactive.py must use 'quirk-output' as the output directory default.

        RED because: quirk/interactive.py line 165 has
        _prompt("Output directory", "output"). The dashboard reads from
        QUIRK_OUTPUT_DIR which defaults to './quirk-output/', so an interactive
        user who accepts the current default writes to ./output/ while the dashboard
        looks in ./quirk-output/, causing silent profile fallback.
        """
        source = pathlib.Path("quirk/interactive.py").read_text(encoding="utf-8")
        assert '_prompt("Output directory", "quirk-output")' in source, (
            "interactive.py does not use 'quirk-output' as output dir default -- "
            "current default is 'output'"
        )

    def test_interactive_db_path_default_is_quirk_output(self):
        """interactive.py must use 'quirk-output/quirk.db' as the SQLite DB path default.

        RED because: quirk/interactive.py line 166 has
        _prompt("SQLite DB path", "output/quirk.db"). db_path default must be
        consistent with the output directory default.
        """
        source = pathlib.Path("quirk/interactive.py").read_text(encoding="utf-8")
        assert '_prompt("SQLite DB path", "quirk-output/quirk.db")' in source, (
            "interactive.py does not use 'quirk-output/quirk.db' as db_path default -- "
            "current default is 'output/quirk.db'"
        )


if __name__ == "__main__":
    unittest.main()
