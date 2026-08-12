"""Phase 7 — BRAND-01: Dashboard CSS token audit."""
import os

import pytest


CSS_FILE = os.path.join(
    os.path.dirname(__file__), "..", "src", "dashboard", "src", "index.css"
)


@pytest.mark.xfail(
    reason=(
        "TRIAGE-149: confirmed intentional rebrand, not a regression — commit "
        "ac242d1 ('feat(ui): apply Obsidian Pro design system foundation', "
        "2026-05-07) explicitly changed '--primary' from the electric-blue token "
        "'210 100% 56%' to the Obsidian Pro teal token '180 37% 47%' (#4ba8a8), per "
        "its own commit message: 'Accent shifted from blue (210 100% 56%) to "
        "Obsidian Pro teal (#4ba8a8)'. This test predates that rebrand. See "
        "docs/test-triage-149.md#dashboard-theme-obsidian-pro-rebrand"
    ),
    strict=False,
)
def test_primary_color_token():
    """--primary CSS variable must be the electric-blue token: 210 100% 56%"""
    content = open(CSS_FILE).read()
    assert "--primary: 210 100% 56%" in content, (
        f"Expected '--primary: 210 100% 56%' in {CSS_FILE}"
    )


@pytest.mark.xfail(
    reason=(
        "TRIAGE-149: same confirmed intentional Obsidian Pro rebrand (commit "
        "ac242d1, 2026-05-07) as test_primary_color_token — '--accent' is now "
        "'180 37% 47%' (#4ba8a8 teal), not the pre-rebrand electric-blue "
        "'210 100% 56%' this test asserts. See "
        "docs/test-triage-149.md#dashboard-theme-obsidian-pro-rebrand"
    ),
    strict=False,
)
def test_accent_color_token():
    """--accent CSS variable must be the electric-blue token: 210 100% 56%"""
    content = open(CSS_FILE).read()
    assert "--accent: 210 100% 56%" in content


def test_sidebar_wordmark_present():
    """Sidebar component must contain the QU.I.R.K. text mark."""
    sidebar_file = os.path.join(
        os.path.dirname(__file__), "..", "src", "dashboard", "src",
        "components", "sidebar.tsx"
    )
    content = open(sidebar_file).read()
    assert "QU.I.R.K." in content
