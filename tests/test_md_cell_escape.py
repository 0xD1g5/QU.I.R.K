"""Phase 78 / HARDEN-01 escape unit tests for md_cell().

Encodes the ACTUAL contract of quirk/reports/_md_escape.py::md_cell:
  - pipe `|` escaped to `\\|`
  - LF `\\n` collapsed to single space
  - CR `\\r` collapsed to single space (CRLF first, then LF/CR singletons)
  - ASCII control chars below 0x20 (except space) stripped
  - None coerced to ""
  - non-str coerced via str()
  - backtick "`": PASSTHROUGH (CONTEXT.md / module docstring R-4 — deferred
    backtick guard; documented technical debt for Phase 78. The output is
    still a string and pipe/newline neutralization still applies.)
"""
from __future__ import annotations

from quirk.reports._md_escape import md_cell


def test_pipe_escaped() -> None:
    out = md_cell("a|b")
    # The output must not contain a raw pipe that would split a GFM column.
    assert "\\|" in out
    # Verify no unescaped pipe remains (every `|` is preceded by a backslash).
    for idx, ch in enumerate(out):
        if ch == "|":
            assert idx > 0 and out[idx - 1] == "\\", f"unescaped pipe at {idx}: {out!r}"


def test_newline_neutralized() -> None:
    out = md_cell("a\nb")
    assert "\n" not in out
    assert "a b" == out  # collapsed to single space


def test_crlf_neutralized() -> None:
    out = md_cell("a\r\nb")
    assert "\r" not in out
    assert "\n" not in out
    # CRLF -> single space
    assert out == "a b"


def test_cr_only_neutralized() -> None:
    out = md_cell("a\rb")
    assert "\r" not in out
    assert out == "a b"


def test_backtick_handled() -> None:
    """Backtick passthrough — per _md_escape.py module docstring, backticks
    are deliberately NOT escaped (deferred to a later phase per CONTEXT.md
    R-4 / cbom-intel-reports WR-01). Assert the output is a str and the
    backtick survives unchanged; this encodes the truthful contract.
    """
    out = md_cell("a`b")
    assert isinstance(out, str)
    # Documented passthrough — backtick should appear unchanged.
    assert "`" in out
    assert out == "a`b"


def test_control_char_handled() -> None:
    # 0x07 (BEL) is < 0x20 and not space → stripped without raising.
    out = md_cell("a\x07b")
    assert isinstance(out, str)
    assert "\x07" not in out
    assert out == "ab"


def test_none_returns_empty() -> None:
    # Contract: None -> "" (avoid literal "None" in tables).
    assert md_cell(None) == ""


def test_integer_passes() -> None:
    # Contract: non-str coerced via str().
    assert md_cell(42) == "42"


def test_pipe_and_newline_combined() -> None:
    # Defense-in-depth combo: both row-break and column-break vectors.
    out = md_cell("a|b\nc|d")
    assert "\n" not in out
    # Both pipes must be escaped.
    raw_pipe_count = sum(
        1
        for idx, ch in enumerate(out)
        if ch == "|" and (idx == 0 or out[idx - 1] != "\\")
    )
    assert raw_pipe_count == 0
