"""Adversarial markdown injection corpus for technical report (REPORT-SAN-02).

Phase 61 / REPORT-SAN-02: render build_tech_markdown() with hostile field
values containing pipes, newlines, CRLF, and ASCII control chars; assert the
output is a structurally valid GFM table (no row breaks, consistent column
counts, no unescaped pipes inside data cells).

The test would PASS without Task 1/2 escaping only if the input corpus is
clean — the corpus is deliberately hostile so the test fails RED if md_cell
wrapping is removed.
"""
from __future__ import annotations

import re
from types import SimpleNamespace

import pytest

from quirk.models import CryptoEndpoint
from quirk.reports.technical import build_tech_markdown


def _cfg():
    return SimpleNamespace(assessment=SimpleNamespace(name="Adversarial Test"))


def _adversarial_endpoint():
    return CryptoEndpoint(
        host="bad.host.com|injected-col",
        port=443,
        protocol="TLS",
        tls_version="TLSv1.2|fake",
        cipher_suite="WEAK\x07CIPHER|x",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_subject="CN=evil|injected",
        cert_issuer="CN=evil-ca\nrow-break",
        cert_not_before=None,
        cert_not_after=None,
        tls_capabilities_json=None,
        ssh_audit_json=None,
    )


def _adversarial_finding():
    return {
        "severity": "HIGH",
        "host": "bad.host.com|injected-col",
        "port": 443,
        "title": "Finding\nWith Newline",
        "description": "Desc with | multiple | pipes",
        "recommendation": "Fix\r\nwith CRLF",
    }


@pytest.fixture
def rendered_md():
    cfg = _cfg()
    ep = _adversarial_endpoint()
    finding = _adversarial_finding()
    return build_tech_markdown(cfg, [ep], [finding])


def _table_rows(md: str) -> list[str]:
    """Lines that begin with '|' (table rows including header + separator)."""
    return [line for line in md.splitlines() if line.startswith("|")]


def _count_unescaped_pipes(line: str) -> int:
    """Count `|` characters NOT preceded by `\\`."""
    # Use a regex with negative lookbehind for `\`.
    return len(re.findall(r"(?<!\\)\|", line))


def test_no_unescaped_pipe_in_data_cells(rendered_md):
    """Assert data rows contain no MORE unescaped pipes than the header row.

    The structural column delimiters (one per cell boundary) are intentional
    unescaped pipes.  Any additional unescaped pipe beyond the header count
    means a data cell leaked a raw `|` character that md_cell() should have
    escaped as `\\|`.

    Splitting cells on the unescaped-pipe delimiter is tautological for
    per-cell checking (the split consumes the very chars we'd be looking for),
    so we instead compare per-row pipe counts against the column count
    established by the header row.
    """
    all_lines = rendered_md.splitlines()
    _separator_re = re.compile(r"\|[\s\-:|]+\|")

    # Build a mapping: for each table block (header → separator → data rows),
    # record the unescaped-pipe count of the header row as the expected count
    # for all data rows in that block.
    expected_pipe_count: dict[int, int] = {}  # line-index → expected count
    for idx, line in enumerate(all_lines):
        if _separator_re.fullmatch(line) and idx >= 2:
            header_line = all_lines[idx - 1]
            expected = _count_unescaped_pipes(header_line)
            # Tag all subsequent data rows (until a non-pipe line or end)
            j = idx + 1
            while j < len(all_lines) and all_lines[j].startswith("|"):
                expected_pipe_count[j] = expected
                j += 1

    assert expected_pipe_count, "No table data rows found to validate"

    for idx, line in enumerate(all_lines):
        if idx not in expected_pipe_count:
            continue
        actual = _count_unescaped_pipes(line)
        expected = expected_pipe_count[idx]
        assert actual == expected, (
            f"Data row has {actual} unescaped pipes but header has {expected}; "
            f"a data cell likely leaked a raw '|'. Row: {line!r}"
        )


def test_consistent_column_count_per_section(rendered_md):
    """Within each contiguous block of `|`-prefixed lines, every row has the
    same unescaped-pipe count (i.e., same column count)."""
    rows = _table_rows(rendered_md)  # noqa: F841 — used indirectly via groups
    # Group contiguous rows; reset on a non-`|` line
    groups: list[list[str]] = []
    current: list[str] = []
    for line in rendered_md.splitlines():
        if line.startswith("|"):
            current.append(line)
        else:
            if current:
                groups.append(current)
                current = []
    if current:
        groups.append(current)

    for grp in groups:
        counts = {_count_unescaped_pipes(r) for r in grp}
        assert len(counts) == 1, (
            f"Inconsistent column counts in table group: {counts}. Rows: {grp}"
        )


def test_no_raw_newline_or_control_char_in_data_rows(rendered_md):
    """Data rows must not contain raw \\r, \\n inside the row, and no ASCII
    control chars (< 0x20 except space)."""
    rows = _table_rows(rendered_md)
    for line in rows:
        # `splitlines()` already stripped row-terminator newlines, so any \r or \n
        # appearing here is in-cell injection that survived md_cell()
        assert "\r" not in line, f"Carriage return inside row: {line!r}"
        assert "\n" not in line, f"Newline inside row: {line!r}"
        for ch in line:
            if ch == " ":
                continue
            if ch == "\t":
                pytest.fail(f"Tab character inside row: {line!r}")
            assert ord(ch) >= 0x20, f"Control char 0x{ord(ch):02x} in row: {line!r}"


def test_finding_title_newline_collapsed(rendered_md):
    """Specific regression: title='Finding\\nWith Newline' must render as
    'Finding With Newline' on a single row, not split into two rows."""
    assert "Finding\nWith Newline" not in rendered_md
    assert "Finding With Newline" in rendered_md


def test_pipe_in_host_escaped(rendered_md):
    """Specific regression: host='bad.host.com|injected-col' must render as
    'bad.host.com\\|injected-col' (escaped pipe)."""
    assert "bad.host.com\\|injected-col" in rendered_md
