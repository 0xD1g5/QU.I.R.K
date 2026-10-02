#!/usr/bin/env python3
"""Render brand SVGs to PNG for surfaces that cannot embed SVG (DOCX colophon).

WHY THIS IS SEPARATE FROM docs/brand/build_logo.py
--------------------------------------------------
build_logo.py is stdlib-only so anyone can regenerate the vector sources.
Rasterising needs a renderer (resvg-py), which is a dev-only dependency
(Phase 222 D-15: pinned in [dev], never in [all] or a runtime extra). Keeping
the two apart means the SVG generator never grows a native-wheel dependency.

The committed PNG is gated by tests/test_brand_assets_freshness.py.

    .venv/bin/python -m scripts.build_brand_rasters [--out-dir DIR]

The report logo is rendered at 150 px high for a 0.25 in print height, which
is 600 dpi (above the 300 dpi floor).
"""
from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# (source svg, output png, height in px). Phase 223 appends favicon rows here.
TARGETS = [
    ("docs/brand/quirk-logo.svg", "quirk/reports/assets/quirk-logo.png", 150),
]


def render(src: Path, height: int) -> bytes:
    import resvg_py  # lazy: dev-only dependency

    return bytes(resvg_py.svg_to_bytes(svg_path=str(src), height=height, skip_system_fonts=True))


def render_all(out_root: Path = REPO_ROOT) -> list[Path]:
    written = []
    for src, dst, height in TARGETS:
        out = Path(out_root) / dst
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(render(REPO_ROOT / src, height))
        written.append(out)
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path, default=REPO_ROOT)
    for p in render_all(ap.parse_args().out_dir):
        print("wrote", p)


if __name__ == "__main__":
    main()
