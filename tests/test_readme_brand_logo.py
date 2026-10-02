"""Static contract for the README brand logo block (Phase 222 D-06/D-07/D-08).

PyPI's sanitizer strips every <source>, so the <img> fallback must be the Ink
variant; GitHub honours the two prefers-color-scheme sources.
"""

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW = "https://raw.githubusercontent.com/0xD1g5/QU.I.R.K/main/docs/brand/"
LIGHT = RAW + "quirk-logo.svg"
DARK = RAW + "quirk-logo-dark.svg"


def _readme() -> str:
    return (REPO_ROOT / "README.md").read_text(encoding="utf-8")


def _block() -> str:
    text = _readme()
    first = next(line for line in text.splitlines() if line.strip())
    assert first.strip() == "<picture>", (
        "Phase 222 D-08: first non-blank README line must open <picture>"
    )
    start = text.index("<picture>")
    end = text.index("</picture>") + len("</picture>")
    assert end <= text.index("[!["), (
        "Phase 222 D-08: logo block must sit above the first badge line"
    )
    return text[start:end]


def test_sources_one_dark_one_light():
    block = _block()
    sources = re.findall(r"<source\b[^>]*>", block)
    assert len(sources) == 2, "Phase 222 D-06: exactly two <source> elements"
    dark = [s for s in sources if 'media="(prefers-color-scheme: dark)"' in s]
    light = [s for s in sources if 'media="(prefers-color-scheme: light)"' in s]
    assert len(dark) == 1 and f'srcset="{DARK}"' in dark[0], (
        "Phase 222 D-06/D-07: dark source must point at quirk-logo-dark.svg on main"
    )
    assert len(light) == 1 and f'srcset="{LIGHT}"' in light[0], (
        "Phase 222 D-06/D-07: light source must point at quirk-logo.svg on main"
    )


def test_img_fallback_is_ink_logo_with_min_height():
    block = _block()
    imgs = re.findall(r"<img\b[^>]*>", block)
    assert len(imgs) == 1, "Phase 222 D-06: exactly one <img>"
    img = imgs[0]
    assert f'src="{LIGHT}"' in img, "Phase 222 D-06: <img> fallback must be Ink logo"
    assert 'alt="QU.I.R.K."' in img
    m = re.search(r'height="(\d+)"', img)
    assert m and int(m.group(1)) >= 48, "Phase 222 D-08: render height >= 48 px"


def test_no_relative_or_other_assets_in_block():
    block = _block()
    assert "docs/brand/" not in block.replace(RAW, ""), (
        "Phase 222 D-07: no relative docs/brand path"
    )
    assert "quirk-mark" not in block and "descriptor" not in block, (
        "Phase 222 D-08: primary logo only (no mark, no descriptor)"
    )


def test_h1_unchanged():
    # Derived from pyproject.toml so a version bump does not turn this red (WR-03).
    ver = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    assert f"\n# QU.I.R.K. — v{ver}\n" in "\n" + _readme(), (
        "Phase 222 D-08: H1 must be kept unchanged"
    )
