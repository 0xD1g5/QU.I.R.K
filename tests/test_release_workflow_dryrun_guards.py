"""Phase 148 RELEASE-02: Static guard — release.yml dry-run mechanism must stay sound.

Loads .github/workflows/release.yml and locks in place the workflow_dispatch dry-run
mechanism added in Phase 148:
  - workflow_dispatch trigger present alongside the existing push: tags: v*.*.* trigger (D-05).
  - The `publish` job (PyPI Trusted Publishers + Sigstore) and the "Attach zip to GitHub
    Release" step are both gated on the triggering EVENT, not merely on the ref shape (D-06).
  - A dedicated dry-run artifact-upload step exists and is the exact logical complement of
    the release guard (D-07).

This test runs locally on every pytest invocation, preventing a reviewer from silently
weakening any of these guards (RELEASE-02).
"""
from __future__ import annotations

import pathlib
import re

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RELEASE_FILE = REPO_ROOT / ".github" / "workflows" / "release.yml"

# The canonical release guard. Deliberately includes the `github.event_name == 'push'`
# conjunct: a `workflow_dispatch` run can target a tag ref
# (`gh workflow run release.yml --ref v5.11.0`, or the tag dropdown in the Actions UI), which
# makes `github.ref` start with `refs/tags/` while `github.event_name` is `workflow_dispatch`.
# A ref-only guard would therefore evaluate TRUE on a manual run against a tag, and the
# "dry run" would really publish to PyPI and really attach a zip to a real GitHub Release.
RELEASE_GUARD = "github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')"

# The weaker, unsound form that must never appear on its own.
REF_ONLY_GUARD = "startsWith(github.ref, 'refs/tags/')"


def _load() -> dict:
    return yaml.safe_load(RELEASE_FILE.read_text(encoding="utf-8"))


def _triggers(wf: dict) -> dict:
    # PyYAML 1.1 gotcha: the `on:` key parses to the Python boolean True, not the string "on".
    return wf.get("on", wf.get(True))


def _step_by_name(job: dict, name: str) -> dict:
    steps = job.get("steps", [])
    for step in steps:
        if step.get("name") == name:
            return step
    raise AssertionError(
        f"Step named {name!r} not found in job steps: {[s.get('name') for s in steps]} "
        "(RELEASE-02)"
    )


def test_workflow_dispatch_trigger_present():
    """D-05: workflow_dispatch must be a trigger on release.yml."""
    wf = _load()
    triggers = _triggers(wf)
    assert "workflow_dispatch" in triggers, (
        f"'workflow_dispatch' not found in triggers {list(triggers.keys())} — "
        "RELEASE-02 D-05 requires a manual dry-run trigger."
    )


def test_tag_push_trigger_preserved():
    """D-05: a tag-push trigger must still be present.

    Asserts the *intent* — that release tags trigger the workflow — rather than
    one literal glob. The literal used to be 'v*.*.*'; see the RVW-004 test below
    for why that exact pattern was the defect, not the contract.
    """
    wf = _load()
    triggers = _triggers(wf)
    push = triggers.get("push", {})
    tags = push.get("tags", [])
    assert tags, (
        f"push.tags is {tags!r} — adding workflow_dispatch must not remove the "
        "tag-push trigger (RELEASE-02 D-05)."
    )


def test_two_component_tag_still_triggers_a_release(): 
    """RVW-004: a two-component tag must not silently match nothing.

    release.yml triggered on 'v*.*.*' — three components. `v5.9`, `v5.13` and
    `v5.14` are two-component tags, so pushing them matched no pattern, fired no
    workflow, and produced no error. Three milestones were recorded as shipped
    while PyPI stayed on an older version.

    The convention is still 3-component semver; this guard only ensures a
    mistyped tag produces a visible release run instead of silence.
    """
    import fnmatch

    wf = _load()
    tags = _triggers(wf).get("push", {}).get("tags", [])
    for candidate in ("v5.15.0", "v5.15", "v6.0"):
        assert any(fnmatch.fnmatch(candidate, pat) for pat in tags), (
            f"tag {candidate!r} matches none of push.tags {tags!r} — pushing it "
            f"would fire no workflow at all, which is the RVW-004 defect"
        )


def test_tag_trigger_agrees_with_the_hygiene_guard():
    """The release trigger and the tag-hygiene guard must consider the same
    tags release-like, or the guard will flag tags the workflow ignores."""
    import fnmatch

    wf = _load()
    tags = _triggers(wf).get("push", {}).get("tags", [])
    # scripts/release_tag_hygiene.py treats `v[0-9]*` as release-like.
    for candidate in ("v5.9", "v5.13", "v5.14", "v5.15.0"):
        assert any(fnmatch.fnmatch(candidate, pat) for pat in tags), (
            f"the hygiene guard considers {candidate!r} a release tag but "
            f"release.yml's push.tags {tags!r} would not fire for it"
        )


def test_publish_job_gated_on_push_event_and_tag_ref():
    """D-06: the publish job must be gated on the full event+ref RELEASE_GUARD."""
    wf = _load()
    job_if = wf["jobs"]["publish"].get("if", "")
    assert RELEASE_GUARD in job_if, (
        f"jobs.publish.if is {job_if!r}; expected it to contain the RELEASE_GUARD literal "
        f"{RELEASE_GUARD!r} — a workflow_dispatch run must never reach PyPI (RELEASE-02 D-06)."
    )
    assert "!" not in job_if, (
        f"jobs.publish.if is {job_if!r} and contains '!' — the publish gate must be the "
        "positive (non-negated) RELEASE_GUARD, not its complement (RELEASE-02 D-06)."
    )


def test_windows_package_job_not_gated():
    """D-06: windows-package must have no job-level if — it must still run on dispatch."""
    wf = _load()
    job = wf["jobs"]["windows-package"]
    assert "if" not in job, (
        f"jobs.windows-package has an 'if' key ({job.get('if')!r}) — the whole job must still "
        "run on workflow_dispatch so build/sign/self-test/zip-assembly are provable in "
        "dry-run mode; only the release-mutating STEP should be gated (RELEASE-02 D-06)."
    )


def test_release_attach_step_gated_on_push_event_and_tag_ref():
    """D-06: the 'Attach zip to GitHub Release' step must carry the full RELEASE_GUARD."""
    wf = _load()
    step = _step_by_name(wf["jobs"]["windows-package"], "Attach zip to GitHub Release")
    step_if = step.get("if", "")
    assert RELEASE_GUARD in step_if, (
        f"'Attach zip to GitHub Release'.if is {step_if!r}; expected it to contain the "
        f"RELEASE_GUARD literal {RELEASE_GUARD!r} (RELEASE-02 D-06)."
    )
    assert "!" not in step_if, (
        f"'Attach zip to GitHub Release'.if is {step_if!r} and contains '!' — this step's "
        "guard must be the positive (non-negated) RELEASE_GUARD (RELEASE-02 D-06)."
    )


def test_no_guard_is_ref_shape_only():
    """D-06 regression guard: every ref-shape guard must also test the triggering event.

    workflow_dispatch accepts a tag as its target ref, so `startsWith(github.ref,
    'refs/tags/')` alone is TRUE on a manual run against a tag and would permit a real PyPI
    publish and a real Release mutation. Every `if:` in this file that mentions the ref-shape
    check must also carry `github.event_name == 'push'`.
    """
    text = RELEASE_FILE.read_text(encoding="utf-8")
    offending = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        # Only inspect actual `if:` directives, not prose/comments that happen to quote the
        # guard literal (e.g. explanatory comments referencing the guard by name).
        if not stripped.startswith("if:"):
            continue
        if REF_ONLY_GUARD in line and "github.event_name == 'push'" not in line:
            offending.append((line_no, line.strip()))
    assert not offending, (
        f"Found ref-shape-only guard(s) missing the event-name conjunct: {offending}. "
        "workflow_dispatch can target a tag ref, so a ref-only guard is unsound — it would "
        "let a manual dispatch against a tag really publish to PyPI and really mutate a "
        "GitHub Release (RELEASE-02 D-06)."
    )


def test_both_release_guards_are_identical():
    """D-06: the publish job's guard and the Attach-zip step's guard must never drift apart."""
    wf = _load()
    publish_if = wf["jobs"]["publish"].get("if", "")
    step_if = _step_by_name(wf["jobs"]["windows-package"], "Attach zip to GitHub Release").get(
        "if", ""
    )
    assert publish_if.strip() == step_if.strip(), (
        f"publish job if ({publish_if!r}) and Attach-zip step if ({step_if!r}) have drifted "
        "apart — both release-mutating guards must remain byte-identical (RELEASE-02 D-06)."
    )


def test_dry_run_upload_step_present_and_exactly_complementary():
    """D-07: the dry-run upload step must exist and be the exact complement of RELEASE_GUARD."""
    wf = _load()
    step = _step_by_name(wf["jobs"]["windows-package"], "Upload dry-run zip artifact")
    step_if = step.get("if", "")
    assert "!" in step_if and RELEASE_GUARD in step_if, (
        f"'Upload dry-run zip artifact'.if is {step_if!r}; expected the exact complement "
        f"'!({RELEASE_GUARD})' — a weaker form like '!startsWith(...)' would double-upload on "
        "a dispatch against a tag (RELEASE-02 D-07)."
    )
    uses = step.get("uses", "")
    assert uses.startswith("actions/upload-artifact@"), (
        f"'Upload dry-run zip artifact'.uses is {uses!r}; expected an actions/upload-artifact "
        "pin, reusing the existing pin rather than introducing a new action (RELEASE-02 D-07)."
    )


def test_dry_run_upload_precedes_release_attach():
    """D-07: the dry-run upload step must sit between zip assembly and the Release attach."""
    wf = _load()
    steps = wf["jobs"]["windows-package"]["steps"]
    names = [s.get("name") for s in steps]
    assemble_idx = names.index("Assemble Windows operator zip")
    upload_idx = names.index("Upload dry-run zip artifact")
    attach_idx = names.index("Attach zip to GitHub Release")
    assert assemble_idx < upload_idx < attach_idx, (
        f"Expected step order Assemble({assemble_idx}) < Upload dry-run({upload_idx}) < "
        f"Attach({attach_idx}) in jobs.windows-package.steps; got names={names} "
        "(RELEASE-02 D-07)."
    )


def test_all_uses_are_sha_pinned():
    """WR-03: every `uses:` value across every job must be pinned to a full commit SHA."""
    wf = _load()
    pattern = re.compile(r"^[\w./-]+@[0-9a-f]{40}$")
    violations = []
    for job_name, job in wf["jobs"].items():
        for step in job.get("steps", []):
            uses = step.get("uses")
            if uses is not None and not pattern.match(uses):
                violations.append((job_name, step.get("name"), uses))
    assert not violations, (
        f"Found non-SHA-pinned 'uses:' values: {violations} — every third-party action must "
        "be pinned to a 40-hex-char commit SHA (WR-03)."
    )


def test_self_test_step_still_present():
    """RELEASE-01 precondition: the 1a6effc CI self-test repair must not be silently reverted."""
    wf = _load()
    steps = wf["jobs"]["windows-package"]["steps"]
    self_test_steps = [s for s in steps if "CI self-test" in (s.get("name") or "")]
    assert self_test_steps, (
        "No step with 'CI self-test' in its name found in jobs.windows-package.steps — the "
        "1a6effc signing self-test repair appears to have been removed (RELEASE-01)."
    )
    run_block = self_test_steps[0].get("run", "")
    assert "Cert:\\LocalMachine\\Root" in run_block, (
        "'CI self-test' step's run block no longer contains 'Cert:\\LocalMachine\\Root' — "
        "the 1a6effc fix (trusting the ephemeral root for the verify) must not be reverted "
        "(RELEASE-01)."
    )
