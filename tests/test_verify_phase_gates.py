"""Phase 151-01/151-02 ARTIFACT-01..04: Unit + integration tests for the
phase-completion artifact gate.

151-01 exercises `check_phase_close`, `check_destructive_archive`, and their
loaders/helpers from `scripts/verify_phase_gates.py` directly with literal
and real-fixture inputs — no subprocess, no network, no live git repo.
151-02 adds `_extract_phase_close_trigger()` / `main()` CLI-glue tests (with
an injectable `git_runner` seam so no real git subprocess is needed for
those) plus a `hook_integration` suite that drives a real disposable temp
git repo end-to-end through the installed `.githooks/pre-commit` hook.
`scripts/` is not an importable package, so the module is loaded via
`importlib.util.spec_from_file_location`.
"""
from __future__ import annotations

import importlib.util
import pathlib
import shutil
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "verify_phase_gates.py"

# docs/UAT-SERIES.md IS git-tracked, so it can be read from disk directly.
REAL_UAT_SERIES_PATH = REPO_ROOT / "docs" / "UAT-SERIES.md"

# .planning/ is entirely gitignored (see .gitignore: "PUBREPO-PLANNING-EXCL —
# internal planning artifacts excluded from public repo"), so it is not
# guaranteed to be present or complete in any given checkout/worktree (see
# project memory "Public-repo GSD gotchas"). The two fixtures below are
# embedded verbatim (copied from the real files on 2026-08-13) instead of
# read from disk at test time, per this plan's Interfaces block instruction
# to reuse real content rather than hand-inventing a synthetic shape.

# Verbatim copy of
# .planning/milestones/v5.11-phases/147-backlog-drain-lifecycle-ledger-tail/147-VALIDATION.md
REAL_147_VALIDATION_TEXT = """---
phase: 147
slug: backlog-drain-lifecycle-ledger-tail
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-10
updated: 2026-08-11
---

# Phase 147 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing project standard) |
| **Config file** | `pytest.ini` / `pyproject.toml` addopts (existing — deselects `@slow` by default per project memory) |
| **Quick run command** | `pytest tests/test_run_scan_otics_ssh_gate.py -x` (DRAIN-01); new BACnet-vendor test file (DRAIN-02) |
| **Full suite command** | `python -m pytest` |
| **Estimated runtime** | ~120 seconds (existing suite size) |

---

## Sampling Rate

- **After every task commit:** Run targeted `pytest` for the touched module (DRAIN-01/02 only; DRAIN-03/04 are doc-only, no automated command)
- **After every plan wave:** Run `python -m pytest` full suite (catches any regression from DRAIN-01's `run_scan.py` restructure — this file is heavily depended-upon)
- **Before `/gsd:verify-work`:** Full suite must be green, plus `python -m compileall` per CLAUDE.md
- **Max feedback latency:** ~120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 147-01-* | 01 | 1 | DRAIN-01 | — | Resume path with ssh-checkpointed-complete still fingerprints OT-only hosts | unit | `pytest tests/test_run_scan_otics_ssh_gate.py -x` (extended with Group C) | ✅ exists | ✅ green |
| 147-02-* | 02 | 1 | DRAIN-02 | — | BACnet vendor ID 5 resolves to "Johnson Controls" and correlates to the existing CVE entry | unit | `pytest tests/test_bacnet_vendor_resolution.py -x` | ✅ exists | ✅ green |
| 147-03-* | 03 | 1 | DRAIN-03 | T-WR-02 / T-CD-03 | Ledger has zero undecided/stale rows; WR-02 fixed, CD-03 accept-risk documented | manual (doc review) | N/A — markdown correctness, not code | N/A | ✅ green |
| 147-04-* | 04 | 1 | DRAIN-04 | — | STATE.md Deferred Items ledger re-triaged, Authenticode item folded in | manual (doc review) | N/A — markdown correctness, not code | N/A | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Post-execution result (2026-08-11, v5.11 milestone-audit closeout):**
`pytest -q tests/test_run_scan_otics_ssh_gate.py tests/test_bacnet_vendor_resolution.py` →
**27 passed**. Both manual doc-review rows were independently confirmed by `147-VERIFICATION.md`
(status `passed`, 4/4 must-haves, criteria 3 and 4) against the live ledger files, including
`git cat-file -e` confirmation of all eight cited commit SHAs.

---

## Wave 0 Requirements

- [x] `tests/test_run_scan_otics_ssh_gate.py` — extended with Group C (resume-path OT-supplemental coverage), covers DRAIN-01
- [x] New test file `tests/test_bacnet_vendor_resolution.py` — no existing test covered BACnet vendor-ID→name resolution, covers DRAIN-02
- Framework install: none — pytest already present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Audit ledger rows flipped to `[x] closed` with correct commit citations | DRAIN-03 | Markdown ledger correctness is not code-verifiable; requires human/agent cross-read against `git log -S` citations | Read `.planning/audit-2026-05-27/AUDIT-TASKS.md` after the plan's edits; confirm each of the 12 named rows has either `[x] closed` + commit SHA, or an explicit fresh fix-or-accept-risk call (WR-02, CD-03) |
| WR-02 CORS fix actually closes the origin/port mismatch | DRAIN-03 | Behavioral fix in `quirk/config.py::get_cors_origins` / `quirk/dashboard/api/app.py`; correctness verified by reading the diff against the documented mismatch, not a new automated CORS test (out of phase scope per drain-phase framing) | Read the diff; confirm default origins now include port; optionally curl-test if a local server is easy to stand up |
| STATE.md Deferred Items table re-triaged with accurate current status per row | DRAIN-04 | Ledger status of items like "Windows Authenticode production cert" is an external-state fact only the user can confirm | Read updated STATE.md table; confirm each row is either resolved with evidence, or re-confirmed blocked with a stated reason; Authenticode item explicitly flagged as awaiting user confirmation |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — DRAIN-03/04 are doc-only by design and are covered by the Manual-Only Verifications table below, both confirmed in `147-VERIFICATION.md`
- [x] Wave 0 covers all MISSING references — both test files now exist and are green
- [x] No watch-mode flags
- [x] Feedback latency < 120s — measured 6.7s for the combined targeted run
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-11 (retroactive closeout — this file was written pre-execution and
never updated when the phase completed; the v5.11 milestone audit flagged it as the milestone's
only `nyquist_compliant: false` phase. Closed by re-running both automated commands live and
cross-checking the two manual rows against `147-VERIFICATION.md`. No code changes were required.)
"""

# Verbatim frontmatter block from
# .planning/phases/150-test-suite-green-baseline-ci-gate/150-01-PLAN.md
REAL_150_01_PLAN_TEXT = """---
phase: 150-test-suite-green-baseline-ci-gate
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quirk/scanner/kerberos_scanner.py
  - tests/test_identity_scanner_hardening.py
  - tests/skip_registry.py
  - docs/test-triage-149.md
autonomous: true
requirements: [SUITE-02]
---

# Phase 150 Plan 01
"""


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "verify_phase_gates", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def vpg():
    return _load_module()


# ---------------------------------------------------------------------------
# ARTIFACT-01: VERIFICATION.md presence
# ---------------------------------------------------------------------------


def test_check_phase_close_blocks_when_verification_missing(vpg):
    blocked, reasons, _summary = vpg.check_phase_close(
        phase_num="999",
        verification_exists=False,
        validation_frontmatter={"nyquist_compliant": True},
        validation_body_text="",
        plan_files_modified=[],
        uat_series_text="",
    )
    assert blocked is True
    assert any("VERIFICATION.md" in r for r in reasons)


def test_check_phase_close_does_not_block_artifact01_when_verification_exists(vpg):
    blocked, reasons, _summary = vpg.check_phase_close(
        phase_num="999",
        verification_exists=True,
        validation_frontmatter={"nyquist_compliant": True},
        validation_body_text="",
        plan_files_modified=[],
        uat_series_text="",
    )
    assert blocked is False
    assert reasons == []


# ---------------------------------------------------------------------------
# ARTIFACT-02: is_validation_stale()
# ---------------------------------------------------------------------------


def test_is_validation_stale_true_on_nyquist_false(vpg):
    stale, reasons = vpg.is_validation_stale(
        {"nyquist_compliant": False}, "no pending rows here"
    )
    assert stale is True
    assert reasons


def test_is_validation_stale_true_on_genuine_pending_table_row(vpg):
    body = (
        "| Task ID | Plan | Status |\n"
        "|---------|------|--------|\n"
        "| 999-01-* | 01 | ⬜ pending |\n"
    )
    stale, reasons = vpg.is_validation_stale({"nyquist_compliant": True}, body)
    assert stale is True
    assert reasons


def test_is_validation_stale_false_on_real_147_validation_content(vpg):
    """Pitfall 4: the legend line contains the pending glyph even in a
    fully-green file — must NOT false-positive."""
    parts = REAL_147_VALIDATION_TEXT.split("---", 2)
    import yaml

    frontmatter = yaml.safe_load(parts[1])
    body = parts[2]
    assert "⬜ pending" in body  # sanity: the legend line IS present
    stale, reasons = vpg.is_validation_stale(frontmatter, body)
    assert stale is False
    assert reasons == []


def test_is_validation_stale_true_when_frontmatter_none(vpg):
    stale, reasons = vpg.is_validation_stale(None, "irrelevant body")
    assert stale is True
    assert reasons


# ---------------------------------------------------------------------------
# ARTIFACT-03: user_facing_plan_match() / uat_series_has_entry()
# ---------------------------------------------------------------------------


def test_user_facing_plan_match_true_for_dashboard_cli_and_new_scanner_paths(vpg):
    assert vpg.user_facing_plan_match(["src/dashboard/src/App.tsx"]) is True
    assert vpg.user_facing_plan_match(["quirk/cli/run_scan.py"]) is True
    assert vpg.user_facing_plan_match(["quirk/scanner/new_thing.py"]) is True


def test_user_facing_plan_match_false_for_internal_only_paths(vpg):
    assert (
        vpg.user_facing_plan_match(
            ["tests/test_foo.py", "scripts/bar.py", ".github/workflows/ci.yml"]
        )
        is False
    )


def test_uat_series_has_entry_true_for_real_series_150(vpg):
    text = REAL_UAT_SERIES_PATH.read_text(encoding="utf-8")
    assert vpg.uat_series_has_entry(text, "150") is True


def test_uat_series_has_entry_false_for_nonexistent_phase(vpg):
    text = REAL_UAT_SERIES_PATH.read_text(encoding="utf-8")
    assert vpg.uat_series_has_entry(text, "999999") is False


# ---------------------------------------------------------------------------
# load_phase_plan_files_modified()
# ---------------------------------------------------------------------------


def test_load_phase_plan_files_modified_parses_real_150_01_plan_verbatim(
    vpg, tmp_path
):
    phase_dir = tmp_path / "150-test-suite-green-baseline-ci-gate"
    phase_dir.mkdir()
    (phase_dir / "150-01-PLAN.md").write_text(
        REAL_150_01_PLAN_TEXT, encoding="utf-8"
    )

    result = vpg.load_phase_plan_files_modified(phase_dir)

    assert result == [
        [
            "quirk/scanner/kerberos_scanner.py",
            "tests/test_identity_scanner_hardening.py",
            "tests/skip_registry.py",
            "docs/test-triage-149.md",
        ]
    ]


def test_load_phase_plan_files_modified_multiple_plan_files_preserve_grouping(
    vpg, tmp_path
):
    phase_dir = tmp_path / "X-fixture-phase"
    phase_dir.mkdir()
    (phase_dir / "X-01-PLAN.md").write_text(
        "---\n"
        "phase: X\n"
        "plan: 01\n"
        "files_modified:\n"
        "  - quirk/foo.py\n"
        "---\n\n# Plan 1\n",
        encoding="utf-8",
    )
    (phase_dir / "X-02-PLAN.md").write_text(
        "---\n"
        "phase: X\n"
        "plan: 02\n"
        "files_modified:\n"
        "  - quirk/bar.py\n"
        "  - tests/test_bar.py\n"
        "---\n\n# Plan 2\n",
        encoding="utf-8",
    )

    result = vpg.load_phase_plan_files_modified(phase_dir)

    assert result == [
        ["quirk/foo.py"],
        ["quirk/bar.py", "tests/test_bar.py"],
    ]


def test_load_phase_plan_files_modified_empty_for_no_plan_files_or_missing_dir(
    vpg, tmp_path
):
    empty_dir = tmp_path / "empty-phase-dir"
    empty_dir.mkdir()
    assert vpg.load_phase_plan_files_modified(empty_dir) == []

    nonexistent = tmp_path / "does-not-exist"
    assert vpg.load_phase_plan_files_modified(nonexistent) == []


# ---------------------------------------------------------------------------
# check_phase_close() end-to-end with real loader output (ARTIFACT-03)
# ---------------------------------------------------------------------------


def test_check_phase_close_blocks_on_uat_series_using_real_loader_output(
    vpg, tmp_path
):
    phase_dir = tmp_path / "150-test-suite-green-baseline-ci-gate"
    phase_dir.mkdir()
    (phase_dir / "150-01-PLAN.md").write_text(
        REAL_150_01_PLAN_TEXT, encoding="utf-8"
    )

    plan_files_modified = vpg.load_phase_plan_files_modified(phase_dir)
    assert any(vpg.user_facing_plan_match(f) for f in plan_files_modified)

    blocked, reasons, _summary = vpg.check_phase_close(
        phase_num="150",
        verification_exists=True,
        validation_frontmatter={"nyquist_compliant": True},
        validation_body_text="",
        plan_files_modified=plan_files_modified,
        uat_series_text="no matching heading in this text at all",
    )
    assert blocked is True
    assert any("UAT-SERIES.md" in r for r in reasons)


def test_check_phase_close_artifact03_blocks_on_user_facing_no_entry_else_clean(vpg):
    blocked, reasons, _summary = vpg.check_phase_close(
        phase_num="999",
        verification_exists=True,
        validation_frontmatter={"nyquist_compliant": True},
        validation_body_text="",
        plan_files_modified=[["quirk/cli/run_scan.py"]],
        uat_series_text="no matching heading",
    )
    assert blocked is True
    assert any("UAT-SERIES.md" in r for r in reasons)

    blocked2, reasons2, _summary2 = vpg.check_phase_close(
        phase_num="999",
        verification_exists=True,
        validation_frontmatter={"nyquist_compliant": True},
        validation_body_text="",
        plan_files_modified=[["tests/test_foo.py"], ["scripts/bar.py"]],
        uat_series_text="no matching heading",
    )
    assert blocked2 is False
    assert reasons2 == []


def test_check_phase_close_clean_when_everything_green(vpg):
    blocked, reasons, summary = vpg.check_phase_close(
        phase_num="150",
        verification_exists=True,
        validation_frontmatter={"nyquist_compliant": True},
        validation_body_text="| Task | Status |\n|------|--------|\n| 1 | ✅ green |\n",
        plan_files_modified=[["quirk/cli/run_scan.py"]],
        uat_series_text="## Series 150: Test Suite Green Baseline + CI Gate (Phase 150 — v5.12)",
    )
    assert blocked is False
    assert reasons == []
    assert "Phase 150" in summary


# ---------------------------------------------------------------------------
# ARTIFACT-04: check_destructive_archive() and its loaders
# ---------------------------------------------------------------------------


def test_check_destructive_archive_blocks_on_archive_manifest_incident_shape(vpg):
    # Synthetic phase number (999) — NOT the real Phase 144, which is the one
    # accepted historical gap in _ACCEPTED_HISTORICAL_ARCHIVE_GAPS and must
    # NOT block (see the dedicated exception test below). This test proves
    # the general "unarchived incident" shape still blocks for any phase
    # that is not on that explicit, narrow allowlist.
    phase_map_rows = [("999", "v5.11")]
    disk_phase_dirs = {"145-liveness-pre-pass"}  # 999 absent
    archived_dirs_by_milestone = {"v5.11": set()}  # never archived

    blocked, reasons, _summary = vpg.check_destructive_archive(
        phase_map_rows, disk_phase_dirs, archived_dirs_by_milestone
    )
    assert blocked is True
    assert any("999" in r for r in reasons)


def test_check_destructive_archive_exempts_accepted_historical_phase_144(vpg):
    # Phase 144's directory was deleted with no archive by the exact
    # incident this gate exists to prevent (ARCHIVE-MANIFEST.md); D-06 in
    # 151-CONTEXT.md explicitly rejects backfilling it. Without this
    # exception, every future commit would be blocked forever once the hook
    # is installed, since Phase 144 can never gain a directory. Real repo
    # shape: reproduces .planning/STATE.md's actual v5.11 Phase Map row.
    phase_map_rows = [("144", "v5.11"), ("145", "v5.11")]
    disk_phase_dirs = set()
    archived_dirs_by_milestone = {"v5.11": {"145-liveness-pre-pass"}}

    blocked, reasons, _summary = vpg.check_destructive_archive(
        phase_map_rows, disk_phase_dirs, archived_dirs_by_milestone
    )
    assert blocked is False
    assert reasons == []


def test_check_destructive_archive_exception_is_milestone_scoped(vpg):
    # The exception is keyed on (phase_num, milestone_tag), not phase_num
    # alone — a hypothetical future "phase 144" reused under a different
    # milestone tag must still block normally.
    phase_map_rows = [("144", "v9.9")]
    disk_phase_dirs = set()
    archived_dirs_by_milestone = {"v9.9": set()}

    blocked, reasons, _summary = vpg.check_destructive_archive(
        phase_map_rows, disk_phase_dirs, archived_dirs_by_milestone
    )
    assert blocked is True
    assert any("144" in r for r in reasons)


def test_check_destructive_archive_does_not_block_when_properly_archived(vpg):
    phase_map_rows = [("144", "v5.11")]
    disk_phase_dirs = set()
    archived_dirs_by_milestone = {
        "v5.11": {"144-chunked-discovery-core"}
    }

    blocked, reasons, _summary = vpg.check_destructive_archive(
        phase_map_rows, disk_phase_dirs, archived_dirs_by_milestone
    )
    assert blocked is False
    assert reasons == []


def test_check_destructive_archive_does_not_block_when_still_live_on_disk(vpg):
    phase_map_rows = [("151", "v5.12")]
    disk_phase_dirs = {"151-phase-completion-artifact-gates"}
    archived_dirs_by_milestone = {}

    blocked, reasons, _summary = vpg.check_destructive_archive(
        phase_map_rows, disk_phase_dirs, archived_dirs_by_milestone
    )
    assert blocked is False
    assert reasons == []


def test_disk_phase_dirs_under_excludes_empty_directories(vpg, tmp_path):
    phases_root = tmp_path / "phases"
    phases_root.mkdir()
    populated = phases_root / "144-chunked-discovery-core"
    populated.mkdir()
    (populated / "144-01-PLAN.md").write_text("content", encoding="utf-8")
    empty = phases_root / "145-liveness-pre-pass"
    empty.mkdir()

    result = vpg.disk_phase_dirs_under(phases_root)
    assert result == {"144-chunked-discovery-core"}


def test_parse_state_phase_maps_extracts_rows_attributed_to_section(vpg):
    state_text = (
        "## v5.12 Phase Map\n"
        "\n"
        "| Phase | Name | Requirements | Gate | Status |\n"
        "|-------|------|--------------|------|--------|\n"
        "| 150 | Test Suite Green Baseline | SUITE-02 | None | Complete (2026-08-13) |\n"
        "| 151 | Phase-Completion Artifact Gates | ARTIFACT-01 | None | Not started |\n"
        "\n"
        "## v5.11 Phase Map (SHIPPED 2026-08-11)\n"
        "\n"
        "| Phase | Name | Requirements | Gate | Status |\n"
        "|-------|------|--------------|------|--------|\n"
        "| 144 | Chunked Discovery Core | DISC-01 | None | Complete (2026-08-10) |\n"
    )
    result = vpg.parse_state_phase_maps(state_text)

    assert ("150", "v5.12", "Complete (2026-08-13)") in result
    assert ("151", "v5.12", "Not started") in result
    assert ("144", "v5.11", "Complete (2026-08-10)") in result


def test_check_destructive_archive_untracked_file_deletion_case(vpg, tmp_path):
    """Pitfall 1: the mechanism must be git-tracking-independent — a plain
    filesystem write + plain filesystem delete, no `git add`/`git rm`
    involved, must still be detected via before/after snapshot diff.

    Uses a synthetic phase number (999), not the real Phase 144 — 144 is the
    one accepted historical gap in _ACCEPTED_HISTORICAL_ARCHIVE_GAPS and
    must NOT block (see test_check_destructive_archive_exempts_accepted_
    historical_phase_144); this test proves the general mechanism for any
    phase not on that narrow allowlist."""
    phases_root = tmp_path / "phases"
    phases_root.mkdir()
    phase_dir = phases_root / "999-chunked-discovery-core"
    phase_dir.mkdir()
    (phase_dir / "999-01-PLAN.md").write_text("plain content", encoding="utf-8")

    before = vpg.disk_phase_dirs_under(phases_root)
    assert "999-chunked-discovery-core" in before

    # Simulate phases.clear: a plain filesystem delete, never git-tracked.
    (phase_dir / "999-01-PLAN.md").unlink()

    after = vpg.disk_phase_dirs_under(phases_root)
    assert "999-chunked-discovery-core" not in after

    phase_map_rows = [("999", "v5.11")]
    blocked, reasons, _summary = vpg.check_destructive_archive(
        phase_map_rows, after, {"v5.11": set()}
    )
    assert blocked is True
    assert any("999" in r for r in reasons)


# ---------------------------------------------------------------------------
# 151-02: _extract_phase_close_trigger()
# ---------------------------------------------------------------------------


def test_extract_phase_close_trigger_matches_real_b09c9bc_hunk(vpg):
    """Real diff hunk shape from `git show b09c9bc -- .planning/ROADMAP.md`
    (Phase 150's actual close commit) — Pattern 5."""
    diff_text = (
        "diff --git a/.planning/ROADMAP.md b/.planning/ROADMAP.md\n"
        "--- a/.planning/ROADMAP.md\n"
        "+++ b/.planning/ROADMAP.md\n"
        "@@ -64,7 +64,7 @@\n"
        "-- [ ] **Phase 150: Test Suite Green Baseline + CI Gate** — `pytest -q` green on a clean\n"
        "+- [x] **Phase 150: Test Suite Green Baseline + CI Gate** — `pytest -q` green on a clean\n"
        "       environment, held by a CI gate that fails the build on any new failure\n"
    )
    assert vpg._extract_phase_close_trigger(diff_text) == "150"


def test_extract_phase_close_trigger_none_for_unrelated_roadmap_edit(vpg):
    diff_text = (
        "diff --git a/.planning/ROADMAP.md b/.planning/ROADMAP.md\n"
        "--- a/.planning/ROADMAP.md\n"
        "+++ b/.planning/ROADMAP.md\n"
        "@@ -10,3 +10,3 @@\n"
        "-Some wording tweak.\n"
        "+Some improved wording tweak.\n"
    )
    assert vpg._extract_phase_close_trigger(diff_text) is None


def test_extract_phase_close_trigger_handles_decimal_subphase_number(vpg):
    """Open Question 2: sub-phase closes (e.g. 64.1) must also trigger."""
    diff_text = "+- [x] **Phase 64.1: Audit Residual Blockers** — done\n"
    assert vpg._extract_phase_close_trigger(diff_text) == "64.1"


# ---------------------------------------------------------------------------
# 151-02: main() CLI glue
# ---------------------------------------------------------------------------


def _fake_git_result(returncode: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(
        args=["git"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_main_returns_0_when_no_trigger_and_destructive_archive_clean(vpg, tmp_path):
    (tmp_path / ".planning").mkdir()
    exit_code = vpg.main(
        repo_root=tmp_path,
        git_runner=lambda: _fake_git_result(0, stdout="no trigger in this diff\n"),
    )
    assert exit_code == 0


def test_main_returns_1_when_trigger_fires_and_verification_missing(vpg, tmp_path):
    planning = tmp_path / ".planning"
    phase_dir = planning / "phases" / "999-fixture-phase"
    phase_dir.mkdir(parents=True)
    # Deliberately no 999-VERIFICATION.md written (ARTIFACT-01 violation).
    (planning / "STATE.md").write_text("", encoding="utf-8")
    diff_text = "+- [x] **Phase 999: Fixture Phase** — done\n"

    exit_code = vpg.main(
        repo_root=tmp_path,
        git_runner=lambda: _fake_git_result(0, stdout=diff_text),
    )
    assert exit_code == 1


def test_main_returns_1_when_validation_stale_with_verification_present(vpg, tmp_path):
    planning = tmp_path / ".planning"
    phase_dir = planning / "phases" / "999-fixture-phase"
    phase_dir.mkdir(parents=True)
    (phase_dir / "999-VERIFICATION.md").write_text("verified", encoding="utf-8")
    (phase_dir / "999-VALIDATION.md").write_text(
        "---\nphase: 999\nnyquist_compliant: false\n---\n\nbody\n", encoding="utf-8"
    )
    (planning / "STATE.md").write_text("", encoding="utf-8")
    diff_text = "+- [x] **Phase 999: Fixture Phase** — done\n"

    exit_code = vpg.main(
        repo_root=tmp_path,
        git_runner=lambda: _fake_git_result(0, stdout=diff_text),
    )
    assert exit_code == 1


def test_main_returns_1_when_uat_series_missing_via_real_loader_output(vpg, tmp_path):
    """Assembly-level proof: main() wires load_phase_plan_files_modified()'s
    real output into check_phase_close(), not an empty list/placeholder."""
    planning = tmp_path / ".planning"
    phase_dir = planning / "phases" / "150-fixture-phase"
    phase_dir.mkdir(parents=True)
    (phase_dir / "150-VERIFICATION.md").write_text("verified", encoding="utf-8")
    (phase_dir / "150-VALIDATION.md").write_text(
        "---\nphase: 150\nnyquist_compliant: true\n---\n\nbody\n", encoding="utf-8"
    )
    (phase_dir / "150-01-PLAN.md").write_text(
        REAL_150_01_PLAN_TEXT, encoding="utf-8"
    )
    (planning / "STATE.md").write_text("", encoding="utf-8")
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "UAT-SERIES.md").write_text(
        "no matching heading in this fixture at all", encoding="utf-8"
    )
    diff_text = "+- [x] **Phase 150: Fixture Phase** — done\n"

    exit_code = vpg.main(
        repo_root=tmp_path,
        git_runner=lambda: _fake_git_result(0, stdout=diff_text),
    )
    assert exit_code == 1


def test_main_returns_1_when_no_trigger_but_destructive_archive_incident(vpg, tmp_path):
    # Synthetic phase number (999) -- not the real Phase 144, which is the
    # one accepted historical gap in _ACCEPTED_HISTORICAL_ARCHIVE_GAPS and
    # must NOT block. See test_check_destructive_archive_exempts_accepted_
    # historical_phase_144 for that dedicated case.
    planning = tmp_path / ".planning"
    planning.mkdir()
    (planning / "STATE.md").write_text(
        "## v5.11 Phase Map\n\n"
        "| Phase | Name | Requirements | Gate | Status |\n"
        "|-------|------|--------------|------|--------|\n"
        "| 999 | Chunked Discovery Core | DISC-01 | None | Complete (2026-08-10) |\n",
        encoding="utf-8",
    )
    # No .planning/phases/999-*/ dir and no .planning/milestones/v5.11-phases/999-*/
    # archive -- reproduces the ARCHIVE-MANIFEST.md incident shape.
    exit_code = vpg.main(
        repo_root=tmp_path,
        git_runner=lambda: _fake_git_result(0, stdout="no trigger in this diff\n"),
    )
    assert exit_code == 1


def test_main_returns_2_and_writes_stderr_when_git_subprocess_fails(
    vpg, tmp_path, capsys
):
    exit_code = vpg.main(
        repo_root=tmp_path,
        git_runner=lambda: _fake_git_result(
            1, stdout="", stderr="fatal: not a git repository"
        ),
    )
    assert exit_code == 2
    captured = capsys.readouterr()
    assert "not a git repository" in captured.err
    assert "not a git repository" not in captured.out


# ---------------------------------------------------------------------------
# 151-02: hook_integration -- real end-to-end proof against a temp git repo
# ---------------------------------------------------------------------------

HOOK_PATH = REPO_ROOT / ".githooks" / "pre-commit"


def test_hook_integration_pre_commit_file_exists_executable_and_references_script():
    assert HOOK_PATH.exists(), f"{HOOK_PATH} does not exist"
    mode = HOOK_PATH.stat().st_mode
    assert mode & 0o111, f"{HOOK_PATH} is not executable"
    content = HOOK_PATH.read_text(encoding="utf-8")
    assert "verify_phase_gates.py" in content


def _init_fixture_repo(repo_dir: pathlib.Path) -> None:
    """Build a disposable git repo with its own copy of
    scripts/verify_phase_gates.py and .githooks/pre-commit, so the hook's
    `git rev-parse --show-toplevel` resolution and the script's own
    REPO_ROOT (computed from `__file__`) both correctly resolve to
    `repo_dir`, not the real QUIRK checkout."""
    subprocess.run(["git", "init", "-q"], cwd=repo_dir, check=True)
    subprocess.run(
        ["git", "config", "user.email", "hook-integration-test@example.invalid"],
        cwd=repo_dir,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "hook-integration-test"],
        cwd=repo_dir,
        check=True,
    )

    (repo_dir / "scripts").mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "scripts" / "verify_phase_gates.py",
        repo_dir / "scripts" / "verify_phase_gates.py",
    )

    hooks_dir = repo_dir / ".githooks"
    hooks_dir.mkdir(parents=True)
    shutil.copy(HOOK_PATH, hooks_dir / "pre-commit")
    (hooks_dir / "pre-commit").chmod(0o755)

    subprocess.run(
        ["git", "config", "core.hooksPath", ".githooks"], cwd=repo_dir, check=True
    )

    planning = repo_dir / ".planning"
    planning.mkdir()
    (planning / "STATE.md").write_text("", encoding="utf-8")
    # Unchecked box: the initial-commit diff adds `+- [ ] **Phase 999...`
    # (space, not `x`) -- must NOT trigger the phase-close path.
    (planning / "ROADMAP.md").write_text(
        "# Roadmap\n\n- [ ] **Phase 999: Fixture Phase** — placeholder\n",
        encoding="utf-8",
    )
    docs_dir = repo_dir / "docs"
    docs_dir.mkdir()
    (docs_dir / "UAT-SERIES.md").write_text("no series yet\n", encoding="utf-8")


def _commit(repo_dir: pathlib.Path, message: str) -> subprocess.CompletedProcess:
    subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True)
    return subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )


def test_hook_integration_green_path_commit_succeeds(tmp_path):
    repo_dir = tmp_path / "hook-green-repo"
    repo_dir.mkdir()
    _init_fixture_repo(repo_dir)

    result = _commit(repo_dir, "chore: initial fixture commit")

    assert result.returncode == 0, (
        f"expected a clean commit to succeed, got stderr: {result.stderr}"
    )


def test_hook_integration_red_path_commit_rejected_on_missing_verification(tmp_path):
    repo_dir = tmp_path / "hook-red-repo"
    repo_dir.mkdir()
    _init_fixture_repo(repo_dir)

    # Baseline commit (unchecked Phase 999 box -- no trigger, no violation).
    baseline = _commit(repo_dir, "chore: initial fixture commit")
    assert baseline.returncode == 0, baseline.stderr

    # Flip Phase 999's checkbox to complete -- fires the phase-close trigger.
    # The fixture phase directory deliberately has no 999-VERIFICATION.md.
    phase_dir = repo_dir / ".planning" / "phases" / "999-fixture-phase"
    phase_dir.mkdir(parents=True)
    (phase_dir / "999-01-PLAN.md").write_text(
        "---\nphase: 999\nplan: 01\nfiles_modified:\n  - tests/test_fixture.py\n---\n\n# Plan\n",
        encoding="utf-8",
    )
    (repo_dir / ".planning" / "ROADMAP.md").write_text(
        "# Roadmap\n\n- [x] **Phase 999: Fixture Phase** — placeholder\n",
        encoding="utf-8",
    )

    result = _commit(repo_dir, "docs: mark Phase 999 complete")

    assert result.returncode != 0, (
        "expected the commit to be rejected when VERIFICATION.md is missing"
    )
    assert "VERIFICATION.md" in result.stderr
