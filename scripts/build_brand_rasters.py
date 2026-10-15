#!/usr/bin/env python3
"""Render brand SVGs to PNG/ICO for surfaces that cannot embed SVG (DOCX colophon, favicon).

WHY THIS IS SEPARATE FROM docs/brand/build_logo.py
--------------------------------------------------
build_logo.py is stdlib-only so anyone can regenerate the vector sources.
Rasterising needs a renderer (resvg-py), which is a dev-only dependency
(Phase 222 D-15: pinned in [dev], never in [all] or a runtime extra). Keeping
the two apart means the SVG generator never grows a native-wheel dependency.

The dashboard favicon PNG and PNG-embedded ICO are rendered here too (Phase 223).
The committed PNG/ICO are gated by tests/test_brand_assets_freshness.py.

    .venv/bin/python -m scripts.build_brand_rasters [--out-dir DIR]

The report logo is rendered at 150 px high for a 0.25 in print height, which
is 600 dpi (above the 300 dpi floor).
"""
from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# (source svg, output png, height in px). The favicon PNG (Phase 223 D-09) is rendered
# from the self-grounded Ink tile because a transparent glyph vanishes on dark tab strips (D-08).
TARGETS = [
    ("docs/brand/quirk-logo.svg", "quirk/reports/assets/quirk-logo.png", 150),
    ("docs/brand/quirk-favicon-dark.svg", "src/dashboard/public/favicon.png", 32),
]

# (source svg, output ico, sizes). PNG-embedded ICO, stdlib struct only (Phase 223 D-10)
ICO_TARGETS = [
    ("docs/brand/quirk-favicon-dark.svg", "src/dashboard/public/favicon.ico", (16, 32, 48)),
]

# Bundled font so resvg draws the hero descriptor <text> (skip_system_fonts drops it otherwise).
FONT_FILES = [REPO_ROOT / "src/dashboard/public/fonts/JetBrainsMono[wght].ttf"]

# (source svg, output png, viewBox crop, (width, height) px). GitHub social preview
# card (Phase 226 D-12/D-20): dark hero cropped to 2:1, not padded or stretched.
CARD_TARGETS = [
    ("docs/brand/quirk-hero-dark.svg", "docs/brand/quirk-social-preview.png", "0 50 1600 800", (1280, 640)),
]


def pack_ico(pngs: list[tuple[int, bytes]]) -> bytes:
    """Pack (size, png_bytes) pairs into a PNG-embedded ICO.

    Layout, little-endian: ICONDIR <HHH (0, 1, count); per image an ICONDIRENTRY
    <BBBBHHII (width, height, 0, 0, 1, 32, payload length, payload offset), where a
    size of 256 is encoded as 0; then the raw PNG payloads in entry order.
    """
    n = len(pngs)
    out = struct.pack("<HHH", 0, 1, n)
    offset = 6 + 16 * n
    for size, png in pngs:
        dim = 0 if size >= 256 else size
        out += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
    return out + b"".join(png for _s, png in pngs)


def render(src: Path, height: int) -> bytes:
    import resvg_py  # lazy: dev-only dependency

    return bytes(resvg_py.svg_to_bytes(svg_path=str(src), height=height, skip_system_fonts=True))


def render_card(src: Path, view_box: str, size: tuple[int, int]) -> bytes:
    import resvg_py  # lazy: dev-only dependency

    w, h = size
    svg = Path(src).read_text(encoding="utf-8")
    root = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" width="{w}" height="{h}">'
    svg = re.sub(r"<svg\b[^>]*>", lambda _m: root, svg, count=1)
    return bytes(
        resvg_py.svg_to_bytes(
            svg_string=svg,
            skip_system_fonts=True,
            font_files=[str(p) for p in FONT_FILES],
        )
    )


def render_all(out_root: Path = REPO_ROOT) -> list[Path]:
    written = []
    for src, dst, height in TARGETS:
        out = Path(out_root) / dst
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(render(REPO_ROOT / src, height))
        written.append(out)
    for src, dst, sizes in ICO_TARGETS:
        out = Path(out_root) / dst
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pack_ico([(s, render(REPO_ROOT / src, s)) for s in sizes]))
        written.append(out)
    for src, dst, view_box, size in CARD_TARGETS:
        out = Path(out_root) / dst
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(render_card(REPO_ROOT / src, view_box, size))
        written.append(out)
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path, default=REPO_ROOT)
    for p in render_all(ap.parse_args().out_dir):
        print("wrote", p)


if __name__ == "__main__":
    main()
