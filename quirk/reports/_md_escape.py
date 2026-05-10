"""Markdown table cell escaping utility for GFM report output.

Phase 61 / REPORT-SAN-01 (closes audit CR-07): adversary-controllable
strings interpolated into GFM tables in quirk/reports/*.py must pass
through md_cell() to neutralize pipe / newline / CRLF / control-char
injection.
"""
from __future__ import annotations


def md_cell(value) -> str:
    """Escape a value for safe interpolation into a GFM table cell.

    Transformations applied in order:
      1. None → "" (avoid the literal "None" appearing in tables).
      2. Coerce non-str via str().
      3. CRLF / LF / CR → single space (row-break injection).
      4. "|" → "\\|" (column-break injection).
      5. Strip ASCII control chars (< 0x20) except space (0x20).

    The function deliberately does NOT escape backticks, asterisks, or
    HTML entities — those are not table-row break vectors in GFM. The
    consuming HTML/PDF renderers handle them at their own layer
    (deferred to v4.9 per D-11 / cbom-intel-reports/WR-01).
    """
    if value is None:
        return ""
    text = str(value)
    # Collapse CRLF first, then any remaining CR or LF singletons.
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    text = text.replace("|", "\\|")
    # Strip ASCII control chars (< 0x20) but keep space (0x20).
    text = "".join(c for c in text if c == " " or c >= "\x20")
    return text
