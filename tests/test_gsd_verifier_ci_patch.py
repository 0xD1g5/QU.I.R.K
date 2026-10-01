"""Phase 220 (CITRUTH-03, D-14): revert detector for the gsd-verifier CI patch.

The operator's GSD toolchain carries a local patch in
``~/.claude/agents/gsd-verifier.md``. Step 9 gains rule 0. When
``scripts/branch_ci_state.py`` exists, the verifier runs it against the
current branch with ``--compare-main`` before it picks a status. Exit 1
(red/unobserved) and exit 2 (unknown) force ``status: gaps_found``. The
script's JSON is written verbatim as the VERIFICATION.md ``ci:`` frontmatter
block, which ``scripts/verify_phase_gates.py::check_ci_truth`` (ARTIFACT-05)
reads at phase close.

A ``/gsd-update`` reinstalls the agent definition from the npx package and
silently drops the patch. These tests assert behaviour-bearing text of the
LIVE file, plus its byte-equality with the durability snapshot at
``~/.claude/gsd-local-patches/agents/gsd-verifier.md``. A revert turns them red.

Honest-skip condition: the whole module skips when the live agent file is
absent, which is the case in the Linux Full Suite CI job (no operator
toolchain). A skip there is not a pass, and it is not evidence that the
patch is in force. See CLAUDE.md "Phase Verification Is Branch-CI-Aware
(CITRUTH-03)".
"""
from __future__ import annotations

from pathlib import Path

import pytest

VERIFIER = Path.home() / ".claude" / "agents" / "gsd-verifier.md"
SNAPSHOT = (
    Path.home() / ".claude" / "gsd-local-patches" / "agents" / "gsd-verifier.md"
)

# A module-level pytest.skip() call (not a `pytestmark = skipif(...)`
# assignment) so tests/test_skip_registry.py's AST walk sees this skip site
# and holds it to its "<module>" registry entry. That walk matches calls and
# decorators only; a pytestmark assignment is invisible to it.
if not VERIFIER.is_file():
    pytest.skip(
        "~/.claude/agents/gsd-verifier.md absent — no operator GSD toolchain "
        "in this environment (e.g. CI); a skip here is not evidence the "
        "CITRUTH-03 verifier patch is in force",
        allow_module_level=True,
    )

REAPPLY = (
    "re-apply from ~/.claude/gsd-local-patches/agents/gsd-verifier.md; a "
    "/gsd-update likely reverted the CITRUTH-03 patch"
)

INVOCATION = "scripts/branch_ci_state.py --branch"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _region(text: str, start: str, end: str) -> str:
    """Slice text from the `start` heading up to the `end` heading."""
    i = text.find(start)
    assert i != -1, f"heading {start!r} not found; {REAPPLY}"
    j = text.find(end, i + len(start))
    assert j != -1, f"heading {end!r} not found after {start!r}; {REAPPLY}"
    return text[i:j]


def _step9(path: Path) -> str:
    return _region(_text(path), "## Step 9:", "## Step 9b")


def _step9b(path: Path) -> str:
    return _region(_text(path), "## Step 9b", "## Step 10")


def _exit_clause(region: str, code: int) -> str:
    """The text of the `**Exit N**` bullet only: up to the next bullet or
    blank line, whichever comes first. Without the blank-line stop, the last
    bullet would run on into rule 1's own `gaps_found` and pass vacuously."""
    marker = f"**Exit {code}**"
    i = region.find(marker)
    assert i != -1, f"Step 9 has no {marker} clause; {REAPPLY}"
    ends = [j for j in (region.find("\n   - ", i), region.find("\n\n", i)) if j != -1]
    return region[i:min(ends)] if ends else region[i:]


def test_step9_invokes_branch_ci_state_with_compare_main():
    region = _step9(VERIFIER)
    assert INVOCATION in region, f"Step 9 lacks {INVOCATION!r}; {REAPPLY}"
    assert "--compare-main" in region, f"Step 9 lacks --compare-main; {REAPPLY}"


@pytest.mark.parametrize("code", [1, 2])
def test_step9_maps_nonzero_exit_to_gaps_found(code):
    clause = _exit_clause(_step9(VERIFIER), code)
    assert "gaps_found" in clause, (
        f"Step 9 exit {code} does not force gaps_found; {REAPPLY}"
    )


def test_step9_ci_rule_outranks_passed_and_human_needed():
    region = _step9(VERIFIER)
    assert "OUTRANKS" in region and "self-grant" in region, (
        f"Step 9 CI rule no longer outranks passed/human_needed or no longer "
        f"forbids a self-granted ci_waiver; {REAPPLY}"
    )


def test_frontmatter_template_has_ci_key():
    text = _text(VERIFIER)
    template = _region(text, "## Create VERIFICATION.md", "## Return to Orchestrator")
    assert "\nci: " in template, (
        f"VERIFICATION.md frontmatter template lacks a `ci:` key; {REAPPLY}"
    )
    assert "## CI State" in template, (
        f"report template lacks the `## CI State` section; {REAPPLY}"
    )


def test_step9b_ci_gaps_never_deferred():
    region = _step9b(VERIFIER)
    assert "CI truth gaps are never deferrable" in region, (
        f"Step 9b no longer states CI gaps are never deferred; {REAPPLY}"
    )


def test_snapshot_equals_live():
    assert SNAPSHOT.is_file(), f"snapshot {SNAPSHOT} missing; {REAPPLY}"
    assert SNAPSHOT.read_bytes() == VERIFIER.read_bytes(), (
        f"live verifier differs from the durability snapshot; {REAPPLY}"
    )


def test_snapshot_itself_carries_the_patch():
    # Guards against the snapshot being overwritten with a reverted file,
    # which would make test_snapshot_equals_live pass vacuously.
    assert SNAPSHOT.is_file(), f"snapshot {SNAPSHOT} missing; {REAPPLY}"
    assert INVOCATION in _step9(SNAPSHOT), (
        f"the snapshot's Step 9 lacks {INVOCATION!r}; {REAPPLY}"
    )
