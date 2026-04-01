"""Phase 7 — BRAND-01: Dashboard CSS token audit."""
import os


CSS_FILE = os.path.join(
    os.path.dirname(__file__), "..", "src", "dashboard", "src", "index.css"
)


def test_primary_color_token():
    """--primary CSS variable must be the electric-blue token: 210 100% 56%"""
    content = open(CSS_FILE).read()
    assert "--primary: 210 100% 56%" in content, (
        f"Expected '--primary: 210 100% 56%' in {CSS_FILE}"
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
