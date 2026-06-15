"""RED test — AUDIT-13: CEF extension values must escape spaces as \\s.

Per CISA ArcSight CEF guidance, spaces inside extension key=value tokens
must be escaped as \\s (backslash + s) so that SIEM parsers can correctly
split the extension string on unescaped spaces.

Current state: _cef_escape_extension does NOT escape spaces (the formatter
has a comment noting this intentionally). These tests MUST FAIL against
current main. Wave 2 (plan 131-03) will add space escaping.

pytest -q tests/test_cef_space_escaping.py
"""
from __future__ import annotations

import pytest

from quirk.siem.formatter import _cef_escape_extension, build_cef_event


# ---------------------------------------------------------------------------
# Unit test: _cef_escape_extension escapes spaces as \\s
# ---------------------------------------------------------------------------

def test_cef_escape_extension_escapes_space():
    """AUDIT-13 RED: _cef_escape_extension("a b") must return "a\\sb".

    Spaces in CEF extension values are token delimiters; they must be
    escaped as backslash-s (\\s) so the extension parser can split on
    real token boundaries.

    EXPECTED FAILURE: current implementation does not escape spaces.
    """
    result = _cef_escape_extension("a b")
    assert result == r"a\sb", (
        f"AUDIT-13 RED: expected 'a\\\\sb' (backslash-s), got {result!r}. "
        "Wave 2 (131-03) will add space → \\\\s escaping to _cef_escape_extension."
    )


def test_cef_escape_extension_escapes_multiple_spaces():
    """AUDIT-13 RED: multiple spaces in a value must each become \\s."""
    result = _cef_escape_extension("hello world foo")
    assert result == r"hello\sworld\sfoo", (
        f"AUDIT-13 RED: expected all spaces escaped as \\\\s, got {result!r}."
    )


def test_cef_escape_extension_space_and_equals():
    """AUDIT-13 RED: space escaping must compose with existing = escaping.

    A value with both spaces and equals must escape BOTH.
    Expected: "a=b c" -> "a\\=b\\sc"
    """
    result = _cef_escape_extension("a=b c")
    # Both = and space must be escaped
    assert "\\=" in result and "\\s" in result, (
        f"AUDIT-13 RED: both '=' (as \\\\=) and space (as \\\\s) must be escaped, "
        f"got {result!r}."
    )
    assert result == r"a\=b\sc", (
        f"AUDIT-13 RED: expected 'a\\\\=b\\\\sc', got {result!r}."
    )


# ---------------------------------------------------------------------------
# Integration test: build_cef_event — msg= extension value has no raw spaces
# ---------------------------------------------------------------------------

def test_build_cef_event_msg_no_raw_spaces():
    """AUDIT-13 RED: the msg= extension token in a CEF event must not contain
    raw (unescaped) spaces.

    build_cef_event passes the recommendation (or description) through
    _cef_escape_extension before emitting msg=.  After AUDIT-13 is fixed,
    the msg= value must have spaces encoded as \\s.

    EXPECTED FAILURE: current build_cef_event does not escape spaces in msg=.
    """
    finding = {
        "severity": "HIGH",
        "host": "10.0.0.1",
        "port": 443,
        "title": "Weak Cipher",
        "category": "tls-weak-cipher",
        "description": "TLS uses a weak cipher suite",
        "recommendation": "Upgrade to AES GCM cipher suites immediately",
    }
    cef_line = build_cef_event(finding, version="5.8.0")

    # Extract the extension portion (everything after the 7th pipe)
    parts = cef_line.split("|", 7)
    assert len(parts) == 8, f"CEF line must have 8 pipe-delimited parts, got: {cef_line!r}"
    extension = parts[7]

    # Find the msg= field value — it's the last field (no key= after it)
    # The msg field contains "Upgrade to AES GCM cipher suites immediately"
    # After AUDIT-13 fix, spaces in the msg value become \s
    msg_start = extension.find("msg=")
    assert msg_start != -1, f"msg= not found in extension: {extension!r}"
    msg_value = extension[msg_start + 4:]  # everything after "msg="

    # Assert no raw (unescaped) spaces in the msg value
    # A raw space is one NOT preceded by a backslash
    # We check by confirming all spaces appear as \s sequences
    import re
    # Find spaces that are NOT preceded by a backslash (i.e. raw spaces)
    raw_spaces = re.findall(r'(?<!\\) ', msg_value)
    assert len(raw_spaces) == 0, (
        f"AUDIT-13 RED: msg= value contains {len(raw_spaces)} raw unescaped space(s): "
        f"{msg_value!r}. Wave 2 (131-03) will escape spaces as \\\\s."
    )
