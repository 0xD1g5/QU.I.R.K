"""
Tests for Phase 121-01 — parse_port_spec unit tests (PORT-01, PORT-02).

Covers:
- Valid comma list, range expansion, dedup, sort (PORT-01)
- Bounds checking (1–65535), expansion cap rejection, malformed input (PORT-02)
"""
from __future__ import annotations

import pytest

from quirk.util.port_spec import parse_port_spec


# ---------------------------------------------------------------------------
# PORT-01: Valid inputs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "input_str,expected",
    [
        ("443", [443]),
        ("443,8443", [443, 8443]),
        ("8000-8003", [8000, 8001, 8002, 8003]),
        ("8443,8000-8002,443", [443, 8000, 8001, 8002, 8443]),  # dedup + sort
        ("443,443", [443]),                                       # dedup
        ("22,80,443", [22, 80, 443]),                             # sorted list
        ("1,65535", [1, 65535]),                                  # boundary values
    ],
)
def test_parse_port_spec_valid(input_str: str, expected: list[int]) -> None:
    """parse_port_spec returns a sorted, deduplicated list of ints (PORT-01)."""
    assert parse_port_spec(input_str) == expected


# ---------------------------------------------------------------------------
# PORT-02: Invalid inputs — all must raise ValueError
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad_input",
    [
        "",          # empty string
        "0",         # below lower bound
        "65536",     # above upper bound
        "abc",       # non-numeric
        "443-",      # malformed range (trailing dash)
        "-443",      # malformed range (leading dash)
        "443--8443", # double dash
        "8000-7999", # inverted range
    ],
)
def test_parse_port_spec_invalid_raises(bad_input: str) -> None:
    """parse_port_spec raises ValueError on invalid input (PORT-02)."""
    with pytest.raises(ValueError):
        parse_port_spec(bad_input)


def test_parse_port_spec_expansion_cap_rejects_oversized_spec() -> None:
    """An over-cap spec like '1-65535' must raise ValueError (PORT-02 expansion cap)."""
    with pytest.raises(ValueError):
        parse_port_spec("1-65535")
