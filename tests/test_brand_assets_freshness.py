"""Phase 222 BRAND-01/BRAND-05 gate: brand assets must match their generators.

A generator-drift gate in the same family as test_severity_bands_freshness.py.
There is no last_verified date to bump. Three legs (D-17):

1. every docs/brand/*.svg byte-matches a fresh run of docs/brand/build_logo.py
2. the three packaged/dashboard copies byte-match their docs/brand source
3. every scripts.build_brand_rasters.TARGETS PNG byte-matches a fresh render

Regenerate with:
    python3 docs/brand/build_logo.py
    python -m scripts.build_brand_rasters
    cp docs/brand/quirk-logo.svg quirk/reports/assets/quirk-logo.svg
    cp docs/brand/quirk-logo-dark.svg quirk/reports/assets/quirk-logo-dark.svg
    cp docs/brand/quirk-logo.svg src/dashboard/src/assets/brand/quirk-logo.svg
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
import tomllib
from pathlib import Path

import pytest

from scripts import build_brand_rasters

REPO_ROOT = Path(__file__).resolve().parent.parent
BRAND_DIR = REPO_ROOT / "docs" / "brand"
PIN = "resvg-py==0.5.0"

COPIES = [
    ("docs/brand/quirk-logo.svg", "quirk/reports/assets/quirk-logo.svg"),
    ("docs/brand/quirk-logo-dark.svg", "quirk/reports/assets/quirk-logo-dark.svg"),
    ("docs/brand/quirk-logo.svg", "src/dashboard/src/assets/brand/quirk-logo.svg"),
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
    mod.INK = "#0D0125"  # post-import mutation; build() reads the global at call time
    _regenerate(mod, tmp_path)
    differing = [
        p.name for p in tmp_path.glob("*.svg")
        if not (BRAND_DIR / p.name).exists() or p.read_bytes() != (BRAND_DIR / p.name).read_bytes()
    ]
    assert differing, "mutating the generator's Ink colour changed no SVG; the gate is vacuous"


@pytest.mark.parametrize("src,dst", COPIES)
def test_packaged_brand_copies_byte_equal(src, dst):
    assert (REPO_ROOT / dst).read_bytes() == (REPO_ROOT / src).read_bytes(), (
        f"{dst} is stale. Regenerate with: cp {src} {dst}"
    )


def test_report_logo_png_matches_fresh_render(tmp_path):
    _require_renderer()
    for _src, dst, _h in build_brand_rasters.TARGETS:
        build_brand_rasters.render_all(tmp_path)
        assert (tmp_path / dst).read_bytes() == (REPO_ROOT / dst).read_bytes(), (
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
