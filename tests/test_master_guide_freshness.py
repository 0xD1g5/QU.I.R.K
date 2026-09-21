"""Generator-drift gate: docs/quirk-master-guide.md must match build() output.

Mirrors tests/test_error_codes_freshness.py and
tests/test_severity_bands_freshness.py -- all three prevent silent drift
between a generator and its committed output.

WHY THIS GATE, AND WHY IT IS NOT OPTIONAL
-----------------------------------------
scripts/build_master_guide.py's own docstring argues that deriving the master
"means the master cannot disagree with its sources, only lag them." That is
true of the *generator*. It is not true of the *committed artifact*, which is
a 6,500-line file no reviewer re-reads and which nothing measured the lag of.

tests/test_master_guide_build.py tests the generator: its fixture is
`master() -> build()`, freshly generated every run. It never opens
docs/quirk-master-guide.md. So before this file existed, every one of those
eleven tests could pass while the committed document contradicted all five of
its sources.

That is not hypothetical. On 2026-09-20, one day after PR #30 was opened,
merging PR #31 (sslyze declared as a core dependency) edited
docs/operators-guide.md and left the committed master six hunks stale --
still telling operators that email TLS probing needs `quirk-scanner[motion]`,
the exact claim PR #31 existed to correct. The suite was green throughout.

A generated artifact without a freshness gate is a hand-merged artifact with
extra steps.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts.build_master_guide import PARTS, build

REPO_ROOT = Path(__file__).resolve().parent.parent
MASTER_GUIDE_MD = REPO_ROOT / "docs" / "quirk-master-guide.md"

REGEN = ".venv/bin/python -m scripts.build_master_guide > docs/quirk-master-guide.md"


def test_master_guide_exists():
    assert MASTER_GUIDE_MD.exists(), (
        f"docs/quirk-master-guide.md is missing. Generate with: {REGEN}"
    )


def test_master_guide_is_current():
    """docs/quirk-master-guide.md must byte-match a fresh build()."""
    generated = build().rstrip("\n")
    current = MASTER_GUIDE_MD.read_text(encoding="utf-8").rstrip("\n")
    assert generated == current, (
        "docs/quirk-master-guide.md is stale -- one of its five source guides "
        f"was edited without regenerating it. Regenerate with: {REGEN}"
    )


def test_master_guide_gate_is_not_vacuous(tmp_path, monkeypatch):
    """Prove the gate catches a SOURCE edit, the drift that actually happens.

    Sensitivity must be proven by mutating what build() itself reads -- a
    source guide's bytes -- not by editing the committed artifact, which would
    only prove the comparison operator works. Mirrors
    test_severity_bands_freshness.py's WR-04 reasoning: a proof that bypasses
    the real generator can stay green after the generator stops reading its
    inputs.
    """
    import scripts.build_master_guide as bmg

    # Baseline is an UNMUTATED build, never the committed artifact: comparing
    # against the artifact would pass trivially whenever the artifact happens
    # to be stale, making this proof vacuous exactly when the gate above is
    # already red and the proof matters most.
    baseline = bmg.build()

    fake_docs = tmp_path / "docs"
    fake_docs.mkdir()
    for filename, _, _ in PARTS:
        shutil.copy2(REPO_ROOT / "docs" / filename, fake_docs / filename)

    victim = fake_docs / PARTS[0][0]
    victim.write_text(
        victim.read_text(encoding="utf-8") + "\nA line no source guide contains.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(bmg, "REPO_ROOT", tmp_path)

    assert bmg.build() != baseline, (
        f"Appending a line to docs/{PARTS[0][0]} did NOT change build()'s "
        "output -- the generator is no longer reading its source guides, so "
        "the freshness gate above is vacuous."
    )


@pytest.mark.parametrize("filename", [f for f, _, _ in PARTS])
def test_every_source_guide_is_reachable(filename):
    """Each declared source must exist; a renamed guide must fail loudly here
    rather than silently dropping a whole part from the master."""
    assert (REPO_ROOT / "docs" / filename).exists(), (
        f"docs/{filename} is declared in build_master_guide.PARTS but does "
        "not exist. Renaming a source guide requires updating PARTS."
    )
