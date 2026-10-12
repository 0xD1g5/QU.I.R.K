"""Phase 222 BRAND-01/BRAND-05 gate: brand assets must match their generators.

A generator-drift gate in the same family as test_severity_bands_freshness.py.
There is no last_verified date to bump. Four legs (D-17, Phase 223 D-11):

1. every docs/brand/*.svg byte-matches a fresh run of docs/brand/build_logo.py
2. the packaged/dashboard copies (incl. public/favicon.svg) byte-match their docs/brand source
3. every scripts.build_brand_rasters.TARGETS PNG (incl. the favicon PNG) byte-matches a fresh render
4. the favicon ICO byte-matches a fresh pack_ico render, and the committed file's structure is parsed

Regenerate with:
    python3 docs/brand/build_logo.py
    python -m scripts.build_brand_rasters
    cp docs/brand/quirk-logo.svg quirk/reports/assets/quirk-logo.svg
    cp docs/brand/quirk-logo-dark.svg quirk/reports/assets/quirk-logo-dark.svg
    cp docs/brand/quirk-logo.svg src/dashboard/src/assets/brand/quirk-logo.svg
    cp docs/brand/quirk-favicon-dark.svg src/dashboard/public/favicon.svg
    then: cd src/dashboard && npm run build (copies public/ into quirk/dashboard/static/)
Do not hand-edit these files.

PNG comparison is bytes only: the D-24 spike showed a linux/amd64 render of
resvg-py==0.5.0 is byte-identical to two macOS renders. There is deliberately
no tolerance threshold; if a future renderer bump changes bytes, regenerate.

The PNG leg needs resvg-py ([dev] extra). Locally it skips without it; with CI
set it FAILS, so the required Linux Full Suite job cannot skip the gate.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import re
import struct
import tomllib
from pathlib import Path

import pytest

from scripts import build_brand_component, build_brand_rasters

REPO_ROOT = Path(__file__).resolve().parent.parent
BRAND_DIR = REPO_ROOT / "docs" / "brand"
PIN = "resvg-py==0.5.0"

COPIES = [
    ("docs/brand/quirk-logo.svg", "quirk/reports/assets/quirk-logo.svg"),
    ("docs/brand/quirk-logo-dark.svg", "quirk/reports/assets/quirk-logo-dark.svg"),
    ("docs/brand/quirk-logo.svg", "src/dashboard/src/assets/brand/quirk-logo.svg"),
    ("docs/brand/quirk-favicon-dark.svg", "src/dashboard/public/favicon.svg"),
]


def _load_build_logo():
    spec = importlib.util.spec_from_file_location("build_logo", BRAND_DIR / "build_logo.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _regenerate(mod, out: Path) -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        mod.build(out)


def _require_renderer():
    try:
        import resvg_py  # noqa: F401
    except ImportError:
        if os.environ.get("CI"):
            pytest.fail(
                "resvg-py missing in CI; the brand PNG drift gate must execute, not skip. "
                'Install with: pip install "resvg-py==0.5.0"'
            )
        pytest.skip("resvg-py not installed locally ([dev] extra)")


def test_brand_svgs_regenerate_byte_identical(tmp_path):
    _regenerate(_load_build_logo(), tmp_path)
    fresh = {p.name for p in tmp_path.glob("*.svg")}
    committed = {p.name for p in BRAND_DIR.glob("*.svg")}
    assert fresh == committed, (
        f"docs/brand/*.svg set differs from generator output (extra={sorted(committed - fresh)}, "
        f"missing={sorted(fresh - committed)}). Regenerate with: python3 docs/brand/build_logo.py"
    )
    for name in sorted(fresh):
        assert (tmp_path / name).read_bytes() == (BRAND_DIR / name).read_bytes(), (
            f"docs/brand/{name} is stale. Regenerate with: python3 docs/brand/build_logo.py"
        )


def test_brand_generator_gate_is_not_vacuous(tmp_path):
    mod = _load_build_logo()
    # THEMES is evaluated at import time, so mutating INK alone never reaches the
    # quirk-logo*/quirk-mark* variants; rebind THEMES (what those loops read) as well.
    mod.INK = "#0D0125"
    mod.THEMES = (("", "#0D0125", None), ("-dark", mod.PAPER, "#0D0125"))
    _regenerate(mod, tmp_path)
    differing = [
        p.name for p in tmp_path.glob("*.svg")
        if not (BRAND_DIR / p.name).exists() or p.read_bytes() != (BRAND_DIR / p.name).read_bytes()
    ]
    assert differing, "mutating the generator's Ink colour changed no SVG; the gate is vacuous"
    # The packaged/rasterised/README-pinned logo must itself be sensitive (WR-04).
    for name in ("quirk-logo.svg", "quirk-logo-dark.svg"):
        assert (tmp_path / name).read_bytes() != (BRAND_DIR / name).read_bytes(), (
            f"mutating the generator's Ink colour left {name} unchanged; the gate is vacuous for it"
        )


@pytest.mark.parametrize("src,dst", COPIES)
def test_packaged_brand_copies_byte_equal(src, dst):
    assert (REPO_ROOT / dst).read_bytes() == (REPO_ROOT / src).read_bytes(), (
        f"{dst} is stale. Regenerate with: cp {src} {dst}"
    )


def test_report_logo_png_matches_fresh_render(tmp_path):
    _require_renderer()
    build_brand_rasters.render_all(tmp_path)
    for _src, dst, _h in build_brand_rasters.TARGETS:
        assert (tmp_path / dst).read_bytes() == (REPO_ROOT / dst).read_bytes(), (
            f"{dst} is stale. Regenerate with: python -m scripts.build_brand_rasters"
        )


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _parse_ico(data: bytes):
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    entries = []
    for i in range(count):
        w, h, cc, rsv, planes, bits, length, offset = struct.unpack(
            "<BBBBHHII", data[6 + 16 * i : 22 + 16 * i]
        )
        entries.append((w, h, cc, rsv, planes, bits, length, offset))
    return (reserved, kind, count), entries


def test_pack_ico_layout():
    a, b = PNG_MAGIC + b"A", PNG_MAGIC + b"BB"
    out = build_brand_rasters.pack_ico([(16, a), (32, b)])
    header, entries = _parse_ico(out)
    assert header == (0, 1, 2)
    assert entries[0][7] == 6 + 16 * 2
    assert entries[1][7] == entries[0][7] + len(a)
    for (w, h, _cc, _r, planes, bits, length, offset), size, payload in zip(
        entries, (16, 32), (a, b)
    ):
        assert (w, h, planes, bits, length) == (size, size, 1, 32, len(payload))
        assert out[offset : offset + length] == payload
    big = build_brand_rasters.pack_ico([(256, a)])
    _h, e = _parse_ico(big)
    assert (e[0][0], e[0][1]) == (0, 0)


def test_favicon_ico_structure():
    data = (REPO_ROOT / "src/dashboard/public/favicon.ico").read_bytes()
    header, entries = _parse_ico(data)
    assert header == (0, 1, 3)
    assert {e[0] for e in entries} == {16, 32, 48}
    for w, _h, _cc, _r, _p, _b, length, offset in entries:
        payload = data[offset : offset + length]
        assert payload.startswith(PNG_MAGIC)
        assert struct.unpack(">II", payload[16:24]) == (w, w)


def test_favicon_ico_matches_fresh_render():
    _require_renderer()
    for src, dst, sizes in build_brand_rasters.ICO_TARGETS:
        fresh = build_brand_rasters.pack_ico(
            [(s, build_brand_rasters.render(REPO_ROOT / src, s)) for s in sizes]
        )
        assert (REPO_ROOT / dst).read_bytes() == fresh, (
            f"{dst} is stale. Regenerate with: python -m scripts.build_brand_rasters"
        )


def test_renderer_pin_is_dev_only_and_matches_ci():
    extras = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"]["optional-dependencies"]
    holders = [k for k, v in extras.items() if any(x.split("#")[0].strip() == PIN for x in v)]
    assert holders == ["dev"], f"{PIN} must be pinned in [dev] only, found in {holders}"
    assert not any("resvg" in x for x in extras["all"])
    ci = (REPO_ROOT / ".github" / "workflows" / "python-ci.yml").read_text(encoding="utf-8")
    assert f'pip install "{PIN}"' in ci, f"python-ci.yml must install {PIN} (D-16)"


def test_require_renderer_fails_closed_in_ci(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "resvg_py", None)
    monkeypatch.setenv("CI", "true")
    with pytest.raises(pytest.fail.Exception):
        _require_renderer()
    monkeypatch.delenv("CI")
    with pytest.raises(pytest.skip.Exception):
        _require_renderer()


# --- Phase 223 BRAND-02: generated BrandLogo component (stdlib only, runs everywhere) ---

COMPONENT_PATH = REPO_ROOT / "src" / "dashboard" / "src" / "components" / "BrandLogo.tsx"


def _component_text() -> str:
    return COMPONENT_PATH.read_text(encoding="utf-8", newline="")


def test_brand_component_matches_generator():
    assert build_brand_component.render() == _component_text(), (
        f"src/dashboard/src/components/BrandLogo.tsx is stale. "
        f"Regenerate with: {build_brand_component.REGEN_COMMAND}"
    )


def test_brand_component_contract():
    tsx = _component_text()
    ink_in_sources = sum(
        (REPO_ROOT / p).read_text(encoding="utf-8").upper().count("#0D0124")
        for p in build_brand_component.SOURCES.values()
    )
    assert ink_in_sources > 0
    assert tsx.upper().count("#0D0124") == 0
    assert tsx.count("#7FE001") == 2
    assert tsx.count("currentColor") == ink_in_sources
    assert re.findall(r' (?!aria-|data-)[a-z]+-[a-z-]+="', tsx) == []
    for banned in ("<title", "<desc", "aria-labelledby", 'id="t"'):
        assert banned not in tsx, banned
    assert tsx.count('aria-label="QU.I.R.K."') == 2
    assert tsx.count('role="img"') == 2
    assert tsx.count('data-brand-variant="logo"') == 1
    assert tsx.count('data-brand-variant="glyph"') == 1
    assert "useId" in tsx
    for line in tsx.splitlines():
        if "<svg" in line:
            assert " width=" not in line and " height=" not in line
    assert tsx.startswith("// GENERATED by scripts/build_brand_component.py")
    assert tsx.endswith("\n") and not tsx.endswith("\n\n")
    assert "\r" not in tsx


def test_brand_component_gate_is_not_vacuous():
    real = {
        k: (REPO_ROOT / p).read_text(encoding="utf-8")
        for k, p in build_brand_component.SOURCES.items()
    }
    mutated = dict(real)
    mutated["glyph"] = real["glyph"].replace("#0D0124", "#123456", 1)
    assert mutated["glyph"] != real["glyph"]
    out = build_brand_component.render(sources=mutated)
    assert out != _component_text()
    assert "#123456" in out
    assert build_brand_component.render(sources=real) == _component_text()


def test_brand_component_sources_are_light_variants():
    assert build_brand_component.SOURCES == {
        "logo": "docs/brand/quirk-logo.svg",
        "glyph": "docs/brand/quirk-favicon.svg",
    }
