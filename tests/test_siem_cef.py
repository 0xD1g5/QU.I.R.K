"""Tests for quirk/siem/formatter.py — CEF format, escaping, severity mapping.

Covers:
- build_cef_event() produces exactly 8 pipe-delimited fields
- Severity mapping: CRITICAL->10, HIGH->8, MEDIUM->5, LOW->3; unknown -> 3
- Header escaping: backslash and pipe; equals NOT escaped in header
- Extension escaping: backslash, equals, and newlines
- Backslash escaped FIRST in both functions (injection guard)
- Signature fallback: slugified title when category/id is absent
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _minimal_finding(**overrides) -> dict:
    """Return a minimal finding dict matching the actual findings-*.json shape."""
    base = {
        "severity": "HIGH",
        "host": "10.0.0.1",
        "port": 443,
        "title": "TLS certificate expired",
        "description": "The certificate has expired.",
        "recommendation": "Renew the certificate immediately.",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests — CEF header field count
# ---------------------------------------------------------------------------

class TestCefHeaderFieldCount:
    """build_cef_event must produce exactly 8 pipe-delimited fields (CEF:0 spec)."""

    def test_cef_header_field_count(self):
        from quirk.siem.formatter import build_cef_event

        line = build_cef_event(_minimal_finding(), "1.0.0")
        parts = line.split("|")
        assert len(parts) == 8, (
            f"Expected exactly 8 pipe-delimited fields, got {len(parts)}: {parts}"
        )

    def test_cef_starts_with_cef0(self):
        from quirk.siem.formatter import build_cef_event

        line = build_cef_event(_minimal_finding(), "1.0.0")
        assert line.startswith("CEF:0|"), f"CEF line must start with 'CEF:0|', got: {line[:20]}"

    def test_cef_vendor_is_quirk(self):
        from quirk.siem.formatter import build_cef_event

        line = build_cef_event(_minimal_finding(), "1.0.0")
        parts = line.split("|")
        assert parts[1] == "QUIRK"

    def test_cef_product_is_scanner(self):
        from quirk.siem.formatter import build_cef_event

        line = build_cef_event(_minimal_finding(), "1.0.0")
        parts = line.split("|")
        assert parts[2] == "scanner"

    def test_cef_version_field(self):
        from quirk.siem.formatter import build_cef_event

        line = build_cef_event(_minimal_finding(), "2.3.4")
        parts = line.split("|")
        assert parts[3] == "2.3.4"

    def test_cef_severity_integer_in_field7(self):
        """Field index 6 (0-based) must be an integer string."""
        from quirk.siem.formatter import build_cef_event

        line = build_cef_event(_minimal_finding(severity="CRITICAL"), "1.0.0")
        parts = line.split("|")
        # severity is field index 6 (7th field)
        assert parts[6].isdigit(), f"Severity field must be an integer, got: {parts[6]}"


# ---------------------------------------------------------------------------
# Tests — Severity mapping
# ---------------------------------------------------------------------------

class TestSeverityMapping:
    """CRITICAL->10, HIGH->8, MEDIUM->5, LOW->3; unknown -> 3."""

    def test_severity_critical(self):
        from quirk.siem.formatter import build_cef_event

        line = build_cef_event(_minimal_finding(severity="CRITICAL"), "1.0.0")
        parts = line.split("|")
        assert parts[6] == "10"

    def test_severity_high(self):
        from quirk.siem.formatter import build_cef_event

        line = build_cef_event(_minimal_finding(severity="HIGH"), "1.0.0")
        parts = line.split("|")
        assert parts[6] == "8"

    def test_severity_medium(self):
        from quirk.siem.formatter import build_cef_event

        line = build_cef_event(_minimal_finding(severity="MEDIUM"), "1.0.0")
        parts = line.split("|")
        assert parts[6] == "5"

    def test_severity_low(self):
        from quirk.siem.formatter import build_cef_event

        line = build_cef_event(_minimal_finding(severity="LOW"), "1.0.0")
        parts = line.split("|")
        assert parts[6] == "3"

    def test_severity_unknown_defaults_to_3(self):
        from quirk.siem.formatter import build_cef_event

        line = build_cef_event(_minimal_finding(severity="UNKNOWN_LEVEL"), "1.0.0")
        parts = line.split("|")
        assert parts[6] == "3"

    def test_severity_missing_defaults_to_3(self):
        finding = _minimal_finding()
        del finding["severity"]
        from quirk.siem.formatter import build_cef_event

        line = build_cef_event(finding, "1.0.0")
        parts = line.split("|")
        assert parts[6] == "3"

    def test_severity_map_exported(self):
        from quirk.siem.formatter import _CEF_SEVERITY

        assert _CEF_SEVERITY["CRITICAL"] == 10
        assert _CEF_SEVERITY["HIGH"] == 8
        assert _CEF_SEVERITY["MEDIUM"] == 5
        assert _CEF_SEVERITY["LOW"] == 3


# ---------------------------------------------------------------------------
# Tests — Header escaping
# ---------------------------------------------------------------------------

class TestHeaderEscaping:
    """CEF header fields escape backslash and pipe; equals is NOT escaped."""

    def test_pipe_in_title_escaped(self):
        r"""A pipe in the title (name field) becomes \| in the raw CEF line.

        NOTE: A naive str.split("|") will produce more than 8 parts when the
        title contains an escaped pipe, because str.split() does not understand
        CEF escape sequences.  A compliant CEF parser treats \| as a literal
        pipe in the value, not as a field separator.  We verify that the escaped
        form \| is present in the raw line (not a bare unescaped pipe inside the
        name field), not by counting raw splits.
        """
        from quirk.siem.formatter import build_cef_event

        line = build_cef_event(_minimal_finding(title="TLS|Failure"), "1.0.0")
        # The escaped pipe \| must appear in the line
        assert r"\|" in line, f"Expected escaped pipe in line: {line}"
        # The title without escaping ("TLS" followed immediately by "|" then "Failure"
        # as three separate split tokens) must NOT appear — i.e. the bare pipe is escaped
        # NOTE: we can confirm this by checking the name field directly using _cef_escape_header
        from quirk.siem.formatter import _cef_escape_header
        assert _cef_escape_header("TLS|Failure") == r"TLS\|Failure"

    def test_backslash_in_title_escaped(self):
        """A backslash in the title becomes \\\\."""
        from quirk.siem.formatter import build_cef_event

        line = build_cef_event(_minimal_finding(title=r"TLS\Failure"), "1.0.0")
        assert r"\\" in line, f"Expected escaped backslash in line: {line}"

    def test_equals_not_escaped_in_header(self):
        """An equals sign in a header field is NOT escaped (only extension values are)."""
        from quirk.siem.formatter import _cef_escape_header

        result = _cef_escape_header("a=b")
        assert result == "a=b", (
            f"Equals must NOT be escaped in header fields. Got: {result}"
        )

    def test_cef_escape_header_pipe(self):
        from quirk.siem.formatter import _cef_escape_header

        assert _cef_escape_header("a|b") == r"a\|b"

    def test_cef_escape_header_backslash(self):
        from quirk.siem.formatter import _cef_escape_header

        assert _cef_escape_header("a\\b") == r"a\\b"


# ---------------------------------------------------------------------------
# Tests — Extension escaping
# ---------------------------------------------------------------------------

class TestExtensionEscaping:
    """Extension values escape backslash, equals, and newlines."""

    def test_equals_escaped_in_extension(self):
        from quirk.siem.formatter import _cef_escape_extension

        result = _cef_escape_extension("key=value")
        assert result == r"key\=value", f"Got: {result}"

    def test_backslash_escaped_in_extension(self):
        from quirk.siem.formatter import _cef_escape_extension

        result = _cef_escape_extension("back\\slash")
        assert result == r"back\\slash", f"Got: {result}"

    def test_newline_escaped_in_extension(self):
        from quirk.siem.formatter import _cef_escape_extension

        result = _cef_escape_extension("line1\nline2")
        assert result == r"line1\nline2", f"Got: {result}"

    def test_crlf_escaped_in_extension(self):
        from quirk.siem.formatter import _cef_escape_extension

        result = _cef_escape_extension("line1\r\nline2")
        assert result == r"line1\nline2", f"Got: {result}"

    def test_cr_escaped_in_extension(self):
        from quirk.siem.formatter import _cef_escape_extension

        result = _cef_escape_extension("line1\rline2")
        assert result == r"line1\nline2", f"Got: {result}"


# ---------------------------------------------------------------------------
# Tests — Backslash-first ordering (the #1 CEF bug guard)
# ---------------------------------------------------------------------------

class TestEscapingBackslashFirst:
    r"""Input '\|' must yield '\\|' (not '\\\|') in a header field.

    If pipe is escaped BEFORE backslash:
        \|  ->  \|  (after pipe escape, becomes \\|)
             then backslash escape doubles the \\ -> \\\\|
    If backslash escaped FIRST (correct):
        \|  ->  \\|  (backslash -> \\)
             then pipe: | -> \|  so total: \\\|  ... wait
    Let us be precise:
      Input literal string: backslash followed by pipe  (2 chars: \ and |)
      Correct sequence:
        Step 1 (backslash first): \ -> \\   result is \\| (3 chars: \, \, |)
        Step 2 (pipe):            | -> \|   result is \\\| (4 chars: \, \, \, |)
      WRONG sequence:
        Step 1 (pipe first):  | -> \|       result is \\| (3 chars: \, \, |)
        Step 2 (backslash):   \ -> \\  (each backslash doubled)  -> \\\\|
    So: input \| with correct order => \\| (escaped backslash + escaped pipe = 4 raw chars)
    and: input \| with WRONG order => \\\\| (double-escaped backslash + escaped pipe).
    The test asserts the correct output: the raw string "\\\\|" appears (i.e. two backslashes
    then escaped pipe), which in Python repr is r'\\|' but written as 4 chars.
    """

    def test_backslash_pipe_header_correct_order(self):
        r"""Input: '\|' (one backslash, one pipe) -> '\\|' in header escape.

        This asserts correct behaviour: backslash-first gives '\\\\|'
        (escaped-backslash followed by escaped-pipe).
        """
        from quirk.siem.formatter import _cef_escape_header

        # Input: one backslash + one pipe (2 chars)
        inp = "\\" + "|"
        result = _cef_escape_header(inp)
        # Expected: \\ (escaped backslash = 2 chars) + \| (escaped pipe = 2 chars) = 4 chars
        expected = "\\\\" + "\\|"
        assert result == expected, (
            f"Backslash-first escaping failed.\n"
            f"Input repr: {repr(inp)}\n"
            f"Expected repr: {repr(expected)}\n"
            f"Got repr: {repr(result)}"
        )

    def test_backslash_equals_extension_correct_order(self):
        r"""Input: '\=' (one backslash, one equals) -> '\\\\\\=' in extension escape.

        Correct: backslash -> \\; then = -> \=; result = \\\= (escaped-bs + escaped-eq).
        """
        from quirk.siem.formatter import _cef_escape_extension

        inp = "\\" + "="
        result = _cef_escape_extension(inp)
        expected = "\\\\" + "\\="
        assert result == expected, (
            f"Backslash-first extension escaping failed.\n"
            f"Input repr: {repr(inp)}\n"
            f"Expected repr: {repr(expected)}\n"
            f"Got repr: {repr(result)}"
        )


# ---------------------------------------------------------------------------
# Tests — Category fallback (slugified title)
# ---------------------------------------------------------------------------

class TestCategoryFallback:
    """When category and id are absent, signature is derived from slugified title."""

    def test_category_fallback_when_absent(self):
        from quirk.siem.formatter import build_cef_event

        finding = _minimal_finding(title="TLS Certificate Expired")
        # Ensure no category or id key
        finding.pop("category", None)
        finding.pop("id", None)

        line = build_cef_event(finding, "1.0.0")
        parts = line.split("|")
        # The signature is field index 4 (5th field)
        signature = parts[4]
        # Should be a slug: lowercase, hyphens replace non-alnum runs
        assert signature == "tls-certificate-expired", (
            f"Expected slug 'tls-certificate-expired', got: {signature!r}"
        )

    def test_category_used_when_present(self):
        from quirk.siem.formatter import build_cef_event

        finding = _minimal_finding(category="tls_expiry", title="TLS Certificate Expired")
        line = build_cef_event(finding, "1.0.0")
        parts = line.split("|")
        signature = parts[4]
        assert signature == "tls_expiry", f"Expected 'tls_expiry', got: {signature!r}"

    def test_id_fallback_before_slug(self):
        """id is used when category absent but id present."""
        from quirk.siem.formatter import build_cef_event

        finding = _minimal_finding(title="Some Finding")
        finding.pop("category", None)
        finding["id"] = "FIND-001"
        line = build_cef_event(finding, "1.0.0")
        parts = line.split("|")
        assert parts[4] == "FIND-001", f"Expected 'FIND-001', got: {parts[4]!r}"

    def test_slug_empty_title_gives_unknown(self):
        """If title is empty/missing after slugify, fallback to 'unknown'."""
        from quirk.siem.formatter import _slugify

        assert _slugify("") == "unknown"
        assert _slugify("   ") == "unknown"
        assert _slugify("---") == "unknown"
