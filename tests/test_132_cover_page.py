"""Phase 132 Wave 0 RED + GREEN tests — HTML report cover-page layout and contrast (AUDIT-15).

test_cover_meta_block_no_margin_auto  — RED: fails until Wave 1 removes margin-top: auto (D-06)
test_dark_mode_contrast_ratio         — GREEN: passes today; pins WCAG AA contract (D-07)
"""
from __future__ import annotations

import re
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_minimal_cfg():
    """Return a minimal cfg-like namespace for renderer calls."""
    from types import SimpleNamespace
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Test Org",
            report_owner="Test Owner",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
        ),
        output=SimpleNamespace(directory="/tmp/quirk_test_132_cover"),
    )


# ---------------------------------------------------------------------------
# RED: cover-page layout — no margin-top: auto
# ---------------------------------------------------------------------------


def test_cover_meta_block_no_margin_auto(tmp_path):
    """cover-meta-block must NOT use margin-top: auto (AUDIT-15 / D-06).

    RED: This test fails until Wave 1 replaces 'margin-top: auto' with
    'margin-top: 40px' in quirk/reports/templates/report.html.j2.
    """
    from quirk.reports.html_renderer import render_html_report

    cfg = _make_minimal_cfg()
    out = str(tmp_path / "report.html")
    render_html_report(
        path=out,
        cfg=cfg,
        endpoints=[],
        findings=[],
        score={"total": 75, "subscores": {}, "drivers": []},
        conf={"confidence": 80, "confidence_factors": {}},
        roadmap_items=[],
    )
    content = open(out).read()
    # Extract the .cover-meta-block CSS rule body
    block = re.search(r'\.cover-meta-block\s*\{([^}]+)\}', content)
    assert block is not None, ".cover-meta-block rule not found in rendered output"
    assert "margin-top: auto" not in block.group(1)


# ---------------------------------------------------------------------------
# GREEN: dark-mode contrast ratio — WCAG AA >= 4.5:1 (pins contract)
# ---------------------------------------------------------------------------


def test_dark_mode_contrast_ratio():
    """--text and --text-muted must meet WCAG AA (>=4.5:1) against --bg (AUDIT-15 / D-07).

    GREEN: Current palette (#e8e8f0 and #8888aa on #0a0a0f) is already compliant.
    This test pins the contract so a future palette edit cannot regress contrast silently.
    Values are parsed from the live template — not hardcoded.
    """
    template = Path("quirk/reports/templates/report.html.j2").read_text()

    # Parse the :root CSS variable block
    root_match = re.search(r':root\s*\{([^}]+)\}', template)
    assert root_match, ":root block not found in report.html.j2"
    root_block = root_match.group(1)

    def _hex(var_name: str) -> str:
        m = re.search(rf'--{var_name}:\s*(#[0-9a-fA-F]{{6}})', root_block)
        assert m, f"CSS var --{var_name} not found in :root block"
        return m.group(1)

    bg = _hex("bg")              # expected: #0a0a0f
    text = _hex("text")          # expected: #e8e8f0
    text_muted = _hex("text-muted")  # expected: #8888aa

    def _relative_luminance(hex_color: str) -> float:
        r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))

        def _lin(c: float) -> float:
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

        return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)

    def _contrast(fg: str, bg_hex: str) -> float:
        L1 = _relative_luminance(fg)
        L2 = _relative_luminance(bg_hex)
        lighter, darker = max(L1, L2), min(L1, L2)
        return (lighter + 0.05) / (darker + 0.05)

    ratio_text = _contrast(text, bg)
    ratio_muted = _contrast(text_muted, bg)

    assert ratio_text >= 4.5, (
        f"--text vs --bg contrast {ratio_text:.2f} < 4.5 (WCAG AA) — "
        f"values: {text} on {bg}"
    )
    assert ratio_muted >= 4.5, (
        f"--text-muted vs --bg contrast {ratio_muted:.2f} < 4.5 (WCAG AA) — "
        f"values: {text_muted} on {bg}"
    )
