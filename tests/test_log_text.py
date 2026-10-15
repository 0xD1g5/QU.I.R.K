"""strip_control_chars: printable-text helper for untrusted strings (SECH-04, D-11)."""
from __future__ import annotations

from quirk.util.log_text import strip_control_chars


def test_strips_c0_del_and_c1():
    assert strip_control_chars("CN=ev\nil\x1b[31m\x85x\x7f") == "CN=evil[31mx"


def test_non_str_and_none():
    assert strip_control_chars(None) == ""
    assert strip_control_chars(12) == "12"


def test_printable_unicode_preserved():
    assert strip_control_chars("CN=Müller") == "CN=Müller"
