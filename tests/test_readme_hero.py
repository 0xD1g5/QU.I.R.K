"""Static contract for the README hero image (Phase 225 D-08/D-09/D-12).

PyPI renders the README outside the repository, so a repo-relative image path
shows as a broken image there; the hero must use an absolute
raw.githubusercontent.com URL (D-08). The PNG is a 2x-DPR capture of the
executive summary, kept under 1 MiB (D-09). Regenerate it with
``python -m scripts.capture_readme_hero``.

PNG bounds: width 2048..3600 (2x DPR of a 1024..1800 css-px viewport; the
approved capture is 3360 wide); height only has to be positive because the
capture sizes its viewport to the content, so height varies (approved: 2362).
"""

import shutil
import struct
from pathlib import Path

from tests.cli_helpers import run_fork_safe

REPO_ROOT = Path(__file__).resolve().parent.parent
HERO_REL = "docs/images/dashboard-hero.png"
RAW_HERO = "https://raw.githubusercontent.com/0xD1g5/QU.I.R.K/main/" + HERO_REL
MAX_BYTES = 1_048_576
LEDGERS = {"docs/doc-classification.jsonl", "docs/doc-claim-ledger.jsonl"}
TEXT_SUFFIXES = {".md", ".py", ".txt", ".rst", ".toml", ".yml", ".yaml", ".json", ".ts", ".tsx"}


def _readme() -> str:
    return (REPO_ROOT / "README.md").read_text(encoding="utf-8")


def _tracked() -> list[str]:
    r = run_fork_safe([shutil.which("git") or "/usr/bin/git", "-C", str(REPO_ROOT), "ls-files", "-z"], check=True)
    return [p for p in r.stdout.split("\0") if p]


def test_readme_hero_uses_absolute_raw_url():
    assert _readme().count(f"]({RAW_HERO})") == 1, (
        "Phase 225 D-08: README must embed the hero exactly once by absolute raw URL "
        "so it renders on PyPI"
    )


def test_readme_has_no_relative_docs_images_link():
    assert "](docs/images/" not in _readme(), (
        "Phase 225 D-08: a repo-relative image link breaks on PyPI"
    )


def test_hero_png_dimensions_and_size():
    path = REPO_ROOT / HERO_REL
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "Phase 225 D-09: hero is not a PNG"
    width, height = struct.unpack(">II", data[16:24])
    assert 2048 <= width <= 3600, (
        f"Phase 225 D-09: width {width} not a 2x capture; "
        "re-run python -m scripts.capture_readme_hero"
    )
    assert height > 0
    assert len(data) < MAX_BYTES, f"Phase 225 D-09: hero is {len(data)} bytes (>= 1 MiB)"


def test_no_orphan_images_in_docs_images():
    tracked = _tracked()
    images = [p for p in tracked if p.startswith("docs/images/")]
    assert images, "Phase 225 D-12: no tracked docs/images/* found"
    corpus = ""
    for p in tracked:
        if p in LEDGERS or p.startswith("docs/images/"):
            continue
        if Path(p).suffix.lower() not in TEXT_SUFFIXES:
            continue
        f = REPO_ROOT / p
        if f.is_file():
            corpus += f.read_text(encoding="utf-8", errors="ignore")
    orphans = [p for p in images if Path(p).name not in corpus]
    assert not orphans, f"Phase 225 D-12: orphan images (no tracked doc references them): {orphans}"
