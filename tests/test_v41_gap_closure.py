"""Phase 16 -- v4.1 Gap Closure RED scaffold.

Tests assert the correct end-state for SCORE-04.
- SCORE-04: interactive.py output dir default is "output" (dashboard expects "quirk-output")

Note: the original CLI-04 assertion (importlib.metadata.version("quirk") ==
"4.4.0") was deleted in Phase 150 D-16 -- it was a dead Phase-16-era RED
scaffold querying a distribution name ("quirk") that has not existed since
the v4.10 PyPI rename to "quirk-scanner". It only ever passed in dev
sandboxes carrying stale pre-rename egg-info metadata.
"""

import pathlib
import unittest


class TestV41GapClosure(unittest.TestCase):
    """RED scaffold for Phase 16 v4.1 gap closure requirement SCORE-04."""

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
