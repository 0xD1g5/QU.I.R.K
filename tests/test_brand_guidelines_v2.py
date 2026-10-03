"""Static contract for BRAND-GUIDELINES v2 (Phase 222.1 BRAND-08, D-02/D-03/D-04/D-10/D-14/D-15).

The doc's quoted accent hexes are cross-checked against index.css so the
document and the tokens cannot drift. The 48 px lattice-mark minimum is pinned
(palette B / glyph A, revised 2026-10-02): the favicon construction covers
every rendering below 48 px, so no minimum is lowered.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _doc() -> str:
    return (REPO_ROOT / "docs/brand/BRAND-GUIDELINES.md").read_text(encoding="utf-8")


def _sheet() -> str:
    return (REPO_ROOT / "docs/brand/brand-sheet.html").read_text(encoding="utf-8")


def _css() -> str:
    return (REPO_ROOT / "src/dashboard/src/index.css").read_text(encoding="utf-8")


def _section(heading: str) -> str:
    lines = _doc().splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.strip() == heading), None)
    assert start is not None, f"heading {heading!r} missing from BRAND-GUIDELINES.md"
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## ") or lines[j].startswith("### "):
            end = j
            break
    return "\n".join(lines[start:end])


def _row(label: str) -> str:
    rows = [ln for ln in _doc().splitlines() if ln.startswith(f"| **{label}**")]
    assert len(rows) == 1, f"expected exactly one table row for {label!r}"
    return rows[0]


def _accent(block: str) -> str:
    m = re.search(r"--ds-accent:\s*(#[0-9a-fA-F]{6})\s*;", block)
    assert m, "no --ds-accent hex found"
    return m.group(1).lower()


def test_version_is_2():
    header = next(ln for ln in _doc().splitlines() if ln.startswith("**Version"))
    assert "Version 2.0" in header, "Phase 222.1 D-14: header must read Version 2.0"
    assert "Version 1.0" not in header


def test_product_ui_section_exists_under_colour():
    doc = _doc()
    colour = doc.index("## 5. Colour")
    pui = doc.index("### Product UI")
    typo = doc.index("## 6.")
    assert colour < pui < typo, "Phase 222.1 D-14: Product UI sits inside section 5"


def test_product_ui_accent_hexes_match_tokens():
    sec = _section("### Product UI").lower()
    dark_css, light_css = _css().split(".light {", 1)
    dark, light = _accent(dark_css), _accent(light_css)
    assert dark in sec, "Phase 222.1 D-01: dark accent hex must equal :root --ds-accent"
    assert light in sec, "Phase 222.1 D-01: light accent hex must equal .light --ds-accent"
    assert "261 85% 75%" in sec and "261 60% 50%" in sec, (
        "Phase 222.1 D-01: HSL triples must be quoted"
    )


def test_product_ui_grounds_unchanged():
    sec = _section("### Product UI")
    assert "Paper-hued" in sec and "unchanged" in sec, (
        "Phase 222.1 D-04/D-05: grounds stated as unchanged"
    )


def test_product_ui_states_monotone_rule():
    sec = _section("### Product UI")
    assert "luminance" in sec and "monotone" in sec, (
        "Phase 222.1 D-04: luminance-monotone rule must be stated"
    )


def test_product_ui_status_colours_separate():
    sec = _section("### Product UI")
    assert "status colours are a separate system" in sec.lower(), (
        "Phase 222.1 D-10: status colours separate"
    )
    assert "--severity-low" in sec


def test_signal_never_a_ui_token():
    sec = _section("### Product UI")
    assert "#7FE001" in sec and "never a UI token" in sec, (
        "Phase 222.1 D-03: Signal is the logo error point only"
    )
    assert "7fe001" not in _css().lower(), "Phase 222.1 D-03: Signal must not be a token"


def test_mark_minimum_stays_48px():
    doc = _doc()
    assert _row("Mark").rstrip().endswith("48 px |"), (
        "Phase 222.1 D-14: Mark row minimum stays 48 px"
    )
    assert "48 px     mark" in doc, "Phase 222.1 D-14: size ladder keeps 48 px mark"
    assert "below 48 px" in doc.split("## 8. Don'ts", 1)[1], (
        "Phase 222.1 D-14: Don'ts keeps below 48 px"
    )
    assert "40 px" not in doc, "Phase 222.1 D-14: no 48 -> 40 change"


def test_favicon_row_covers_below_48_and_narrow_sidebar():
    row = _row("Favicon")
    for needle in ("48 px", "narrow sidebar", "24 px"):
        assert needle in row, f"Phase 222.1 D-02: favicon row must mention {needle!r}"
    assert row.rstrip().endswith("16 px |")


def test_mark_row_sidebar_qualified():
    row = _row("Mark")
    if "sidebar" in row:
        assert "at least 48 px" in row.lower(), (
            "Phase 222.1 D-02: mark sidebar use must be qualified"
        )


def test_choosing_a_version_routes_small_slots_to_favicon():
    sec = _section("### Choosing a version")
    bullet = next(ln for ln in sec.splitlines() if "**mark**" in ln)
    assert "favicon" in bullet and "48 px" in bullet, (
        "Phase 222.1 D-02: mark bullet routes below-48 px slots to the favicon"
    )


def test_descriptor_minimum_unchanged():
    assert _row("Primary + descriptor").rstrip().endswith("48 px tall |")


def test_sketch_evidence_quoted():
    doc = _doc().lower()
    assert "sketch 001" in doc and "sketch 002" in doc, (
        "Phase 222.1 D-15: sketch evidence quoted inline"
    )
    assert "3.16" in doc, "Phase 222.1 D-15: measured figure quoted inline"


def test_raster_claim_corrected():
    doc = _doc()
    assert "Raster exports (PNG, ICO) are not generated yet" not in doc
    assert "build_brand_rasters" in doc


def test_brand_sheet_keeps_48_and_qualifies_sidebar():
    sheet = _sheet()
    for needle in ("needs 48 px", "below about 48 px", "min 48 px tall"):
        assert needle in sheet, f"Phase 222.1 D-02: brand-sheet must keep {needle!r}"
    assert "40 px" not in sheet
    assert "app icon, avatar, sidebar ·" not in sheet
