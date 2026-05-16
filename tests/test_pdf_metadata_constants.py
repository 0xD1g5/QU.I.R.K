"""Phase 78 / HARDEN-04 — PDF metadata verification + JS-disabled invariant.

These tests render a minimal synthetic HTML through `render_pdf_report` and use
pypdf to inspect the resulting PDF's Title and Author metadata. Per D-78-R2,
Playwright's page.pdf() exposes no title/author kwargs — the constants flow
exclusively from the HTML <head>'s <title> and <meta name="author"> tags
(established in Plan 78-02's template hardening).

The third test (test_pdf_renders_with_locked_context) acts as the empirical
proof that browser.new_context(java_script_enabled=False) is effective: a
<script>document.title='HACKED'</script> payload appears BEFORE the <title>
tag, so if JS executed, it would mutate the title before the parser reaches
the static value. JS-off means the static <title> wins.
"""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")
pytest.importorskip("pypdf")

import pypdf  # noqa: E402

from quirk.reports.html_renderer import render_pdf_report  # noqa: E402


EXPECTED_TITLE = "QU.I.R.K. Cryptographic Readiness Report"
EXPECTED_AUTHOR = "QU.I.R.K. Scanner"


def _write_minimal_html(path, *, prepend_script: bool = False) -> None:
    """Write a minimal valid HTML fixture mirroring the production <head> constants."""
    script_block = (
        "<script>document.title='HACKED';document.querySelector("
        "'meta[name=author]').setAttribute('content','PWNED');</script>"
        if prepend_script
        else ""
    )
    html = (
        "<!DOCTYPE html>\n"
        "<html><head>\n"
        '<meta charset="utf-8">\n'
        f"{script_block}\n"
        f"<title>{EXPECTED_TITLE}</title>\n"
        f'<meta name="author" content="{EXPECTED_AUTHOR}">\n'
        "</head><body><h1>Test</h1></body></html>\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def _render_or_skip(html_path: str, pdf_path: str) -> None:
    """Render through render_pdf_report; skip if Playwright runtime is unavailable."""
    result = render_pdf_report(html_path, pdf_path)
    if result is False:
        pytest.skip(
            "render_pdf_report returned False — Playwright runtime not available "
            "(browser binary missing or environment cannot launch Chromium)."
        )
    assert result is True


def test_pdf_title_is_constant(tmp_path):
    """Rendered PDF's metadata.title MUST equal the constant from the HTML <title>."""
    html_path = str(tmp_path / "in.html")
    pdf_path = str(tmp_path / "out.pdf")
    _write_minimal_html(html_path)

    _render_or_skip(html_path, pdf_path)

    reader = pypdf.PdfReader(pdf_path)
    assert reader.metadata is not None
    assert reader.metadata.title == EXPECTED_TITLE


def test_pdf_author_is_constant(tmp_path):
    """Rendered PDF's metadata.author MUST equal the constant from <meta name=author>."""
    html_path = str(tmp_path / "in.html")
    pdf_path = str(tmp_path / "out.pdf")
    _write_minimal_html(html_path)

    _render_or_skip(html_path, pdf_path)

    reader = pypdf.PdfReader(pdf_path)
    assert reader.metadata is not None
    assert reader.metadata.author == EXPECTED_AUTHOR


def test_pdf_renders_with_locked_context(tmp_path):
    """JS-disabled invariant: a <script> that mutates title MUST NOT run during render.

    Empirical proof that browser.new_context(java_script_enabled=False) takes effect.
    If JS executed, the title would be 'HACKED' (script runs before parser reaches
    the static <title> tag). With JS off, the static value wins.
    """
    html_path = str(tmp_path / "in.html")
    pdf_path = str(tmp_path / "out.pdf")
    _write_minimal_html(html_path, prepend_script=True)

    _render_or_skip(html_path, pdf_path)

    reader = pypdf.PdfReader(pdf_path)
    assert reader.metadata is not None
    assert reader.metadata.title == EXPECTED_TITLE, (
        "PDF Title was mutated — java_script_enabled=False is NOT effective"
    )
    assert reader.metadata.author == EXPECTED_AUTHOR, (
        "PDF Author was mutated — java_script_enabled=False is NOT effective"
    )
