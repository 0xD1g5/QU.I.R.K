"""Phase 7 — BRAND-01: Dashboard CSS token audit."""
import os
import re


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
    """Sidebar renders the generated BrandLogo, which carries the accessible name QU.I.R.K. (Phase 223 D-16)."""
    base = os.path.join(
        os.path.dirname(__file__), "..", "src", "dashboard", "src", "components"
    )
    content = open(os.path.join(base, "sidebar.tsx")).read()
    assert 'import { BrandLogo } from "@/components/BrandLogo"' in content
    assert '<BrandLogo variant="logo"' in content
    assert '<BrandLogo variant="glyph"' in content
    squashed = re.sub(r"\s+", "", content)
    assert ">QU.I.R.K.<" not in squashed
    assert ">Q<" not in squashed
    brand = open(os.path.join(base, "BrandLogo.tsx")).read()
    assert 'aria-label="QU.I.R.K."' in brand
