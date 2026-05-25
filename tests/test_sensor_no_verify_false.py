"""Phase 108 verify=False grep gate for sensor push client (SENSOR-02).

Copied from tests/scanner/test_phase57_invariants.py _strip_comments approach.
Asserts that sensor_cmd.py and console_cmd.py never contain a literal verify=False
outside of Python comments.
"""
from __future__ import annotations

import io
import pathlib
import tokenize

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

SENSOR_FILES = [
    REPO_ROOT / "quirk" / "cli" / "sensor_cmd.py",
    REPO_ROOT / "quirk" / "cli" / "console_cmd.py",
]


def _strip_comments(src: str) -> str:
    """Strip Python comments using tokenize (handles # in string literals correctly).

    Copied from tests/scanner/test_phase57_invariants.py — authoritative version.
    """
    chars = list(src)
    for tok_type, tok_string, tok_start, tok_end, _ in tokenize.generate_tokens(
        io.StringIO(src).readline
    ):
        if tok_type == tokenize.COMMENT:
            lines = src.splitlines(keepends=True)
            start_offset = sum(len(lines[i]) for i in range(tok_start[0] - 1)) + tok_start[1]
            end_offset = sum(len(lines[i]) for i in range(tok_end[0] - 1)) + tok_end[1]
            for i in range(start_offset, end_offset):
                chars[i] = " "
    return "".join(chars)


@pytest.mark.parametrize("sensor_file", SENSOR_FILES, ids=lambda p: p.name)
def test_sensor_no_verify_false(sensor_file):
    """SENSOR-02: sensor_cmd.py / console_cmd.py must never use verify=False."""
    src = _strip_comments(sensor_file.read_text())
    assert "verify=False" not in src, (
        f"{sensor_file.name} contains literal verify=False outside comments — "
        "regression of SENSOR-02 TLS enforcement"
    )
