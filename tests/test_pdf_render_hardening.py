"""Phase 73 INTEL-01 — PDF render hardening tests (WR-01, WR-02, WR-14).

Covers D-01 narrowed except, try/finally browser cleanup, and stderr advisory.
"""
from __future__ import annotations

import sys
from unittest import mock

import pytest

from quirk.reports.html_renderer import render_pdf_report


def _build_mock_sync_playwright(side_effect):
    """Construct a sync_playwright() context-manager mock whose page.pdf raises *side_effect*.

    Returns (mock_sync_playwright, mock_browser) so tests can also assert
    browser.close behavior.
    """
    mock_browser = mock.MagicMock(name="browser")
    mock_page = mock.MagicMock(name="page")
    mock_page.pdf.side_effect = side_effect
    mock_browser.new_page.return_value = mock_page

    mock_p = mock.MagicMock(name="p")
    mock_p.chromium.launch.return_value = mock_browser

    cm = mock.MagicMock(name="sync_playwright_cm")
    cm.__enter__.return_value = mock_p
    cm.__exit__.return_value = False

    mock_sync_playwright = mock.MagicMock(name="sync_playwright_factory", return_value=cm)
    return mock_sync_playwright, mock_browser


def _patch_playwright(side_effect):
    """Return a list of patch context managers that simulate Playwright availability."""
    # We can't easily patch the in-function `from playwright.sync_api import sync_playwright`
    # — instead, install a fake playwright.sync_api module so the import succeeds.
    mock_sync_playwright, mock_browser = _build_mock_sync_playwright(side_effect)
    fake_module = mock.MagicMock(name="playwright.sync_api")
    fake_module.sync_playwright = mock_sync_playwright

    # Real Playwright Error classes must remain real subclasses of Exception so the
    # narrowed except catches them. We expose real exception classes on the fake module.
    class _FakePlaywrightError(Exception):
        pass

    class _FakePlaywrightTimeoutError(Exception):
        pass

    fake_module.Error = _FakePlaywrightError
    fake_module.TimeoutError = _FakePlaywrightTimeoutError

    return fake_module, mock_browser, _FakePlaywrightError, _FakePlaywrightTimeoutError


def test_render_pdf_returns_false_on_playwright_error(tmp_path, capsys):
    """WR-01 + WR-14: PlaywrightError caught, returns False, stderr advisory emitted."""
    html_path = str(tmp_path / "in.html")
    pdf_path = str(tmp_path / "out.pdf")

    fake_mod, _browser, PWErr, _PWTOErr = _patch_playwright(None)
    fake_mod.sync_playwright.return_value.__enter__.return_value.chromium.launch.return_value.new_page.return_value.pdf.side_effect = PWErr("simulated playwright error")

    with mock.patch.dict(sys.modules, {"playwright.sync_api": fake_mod}):
        result = render_pdf_report(html_path, pdf_path)

    assert result is False
    err = capsys.readouterr().err
    assert "PDF generation failed:" in err
    assert f"scan complete, HTML report at {html_path}" in err


def test_render_pdf_returns_false_on_runtime_error(tmp_path, capsys):
    """WR-01: RuntimeError is in narrowed tuple → caught, returns False, advisory emitted."""
    html_path = str(tmp_path / "in.html")
    pdf_path = str(tmp_path / "out.pdf")

    fake_mod, _browser, _PWErr, _PWTOErr = _patch_playwright(RuntimeError("boom"))

    with mock.patch.dict(sys.modules, {"playwright.sync_api": fake_mod}):
        result = render_pdf_report(html_path, pdf_path)

    assert result is False
    err = capsys.readouterr().err
    assert "PDF generation failed:" in err
    assert "RuntimeError" in err


def test_render_pdf_returns_false_on_os_error(tmp_path, capsys):
    """WR-01: OSError is in narrowed tuple → caught, returns False, advisory emitted."""
    html_path = str(tmp_path / "in.html")
    pdf_path = str(tmp_path / "out.pdf")

    fake_mod, _browser, _PWErr, _PWTOErr = _patch_playwright(OSError("disk full"))

    with mock.patch.dict(sys.modules, {"playwright.sync_api": fake_mod}):
        result = render_pdf_report(html_path, pdf_path)

    assert result is False
    err = capsys.readouterr().err
    assert "PDF generation failed:" in err


def test_render_pdf_propagates_unexpected_exception(tmp_path):
    """WR-01 RED-then-GREEN: KeyError NOT in narrowed tuple → propagates (blanket-except gone)."""
    html_path = str(tmp_path / "in.html")
    pdf_path = str(tmp_path / "out.pdf")

    fake_mod, _browser, _PWErr, _PWTOErr = _patch_playwright(KeyError("programmer bug"))

    with mock.patch.dict(sys.modules, {"playwright.sync_api": fake_mod}):
        with pytest.raises(KeyError):
            render_pdf_report(html_path, pdf_path)


def test_render_pdf_closes_browser_in_finally(tmp_path):
    """WR-02: When page.pdf raises, browser.close() is still invoked in finally."""
    html_path = str(tmp_path / "in.html")
    pdf_path = str(tmp_path / "out.pdf")

    fake_mod, mock_browser, PWErr, _PWTOErr = _patch_playwright(None)
    fake_mod.sync_playwright.return_value.__enter__.return_value.chromium.launch.return_value.new_page.return_value.pdf.side_effect = PWErr("inner raise")
    # The browser handle we want to assert on is the one returned by chromium.launch
    real_browser = fake_mod.sync_playwright.return_value.__enter__.return_value.chromium.launch.return_value

    with mock.patch.dict(sys.modules, {"playwright.sync_api": fake_mod}):
        result = render_pdf_report(html_path, pdf_path)

    assert result is False
    assert real_browser.close.called, "browser.close() must be invoked by finally even on inner-raise"


def test_render_pdf_close_failure_does_not_mask(tmp_path, capsys):
    """WR-02 defensive: close-time error during finally must NOT mask original return-False."""
    html_path = str(tmp_path / "in.html")
    pdf_path = str(tmp_path / "out.pdf")

    fake_mod, _browser, PWErr, _PWTOErr = _patch_playwright(None)
    launched = fake_mod.sync_playwright.return_value.__enter__.return_value.chromium.launch.return_value
    launched.new_page.return_value.pdf.side_effect = PWErr("first failure")
    launched.close.side_effect = OSError("close-time failure")

    with mock.patch.dict(sys.modules, {"playwright.sync_api": fake_mod}):
        # Must not propagate the close-time OSError
        result = render_pdf_report(html_path, pdf_path)

    assert result is False
    err = capsys.readouterr().err
    assert "PDF generation failed:" in err  # original advisory preserved


def test_render_pdf_import_error_returns_false(tmp_path, capsys, monkeypatch):
    """D-01a: When playwright.sync_api import fails, returns False with no stderr advisory."""
    html_path = str(tmp_path / "in.html")
    pdf_path = str(tmp_path / "out.pdf")

    # Force ImportError by inserting a module that raises on attribute access
    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def fake_import(name, *args, **kwargs):
        if name == "playwright.sync_api" or name.startswith("playwright"):
            raise ImportError("playwright not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    result = render_pdf_report(html_path, pdf_path)
    assert result is False
    err = capsys.readouterr().err
    # ImportError branch must NOT emit the narrowed-except advisory
    assert "PDF generation failed:" not in err
