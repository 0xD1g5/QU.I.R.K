"""Phase 7 — BRAND-01: Dashboard CSS token audit."""
import os


CSS_FILE = os.path.join(
    os.path.dirname(__file__), "..", "src", "dashboard", "src", "index.css"
)


def _blocks():
    """Split index.css once on the literal '.light {' into (dark, light)."""
    with open(CSS_FILE, encoding="utf-8") as fh:
        content = fh.read()
    dark, light = content.split(".light {", 1)
    return dark, light


def test_primary_color_token():
    """--primary is the v2 Ink-violet accent (#af89f5 dark / #6933cc light)."""
    dark, light = _blocks()
    assert "--primary: 261 85% 75%" in dark, (
        "Phase 222.1 D-16 / BRAND-GUIDELINES v2: dark --primary must be 261 85% 75%"
    )
    assert "--primary: 261 60% 50%" in light, (
        "Phase 222.1 D-16 / BRAND-GUIDELINES v2: light --primary must be 261 60% 50%"
    )


def test_accent_color_token():
    """--accent is the v2 Ink-violet accent (#af89f5 dark / #6933cc light)."""
    dark, light = _blocks()
    assert "--accent: 261 85% 75%" in dark, (
        "Phase 222.1 D-16 / BRAND-GUIDELINES v2: dark --accent must be 261 85% 75%"
    )
    assert "--accent: 261 60% 50%" in light, (
        "Phase 222.1 D-16 / BRAND-GUIDELINES v2: light --accent must be 261 60% 50%"
    )


def test_sidebar_wordmark_present():
    """Sidebar component must contain the QU.I.R.K. text mark."""
    sidebar_file = os.path.join(
        os.path.dirname(__file__), "..", "src", "dashboard", "src",
        "components", "sidebar.tsx"
    )
    content = open(sidebar_file).read()
    assert "QU.I.R.K." in content
