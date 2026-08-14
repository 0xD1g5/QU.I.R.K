"""Phase 151-01 ARTIFACT-01..04: Unit tests for the phase-completion
artifact gate decision core.

Exercises `check_phase_close`, `check_destructive_archive`, and their
loaders/helpers from `scripts/verify_phase_gates.py` directly with literal
and real-fixture inputs — no subprocess, no network, no live git repo.
`scripts/` is not an importable package, so the module is loaded via
`importlib.util.spec_from_file_location`.
"""
from __future__ import annotations

import importlib.util
import pathlib

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
    phase_map_rows = [("144", "v5.11")]
    disk_phase_dirs = {"145-liveness-pre-pass"}  # 144 absent
    archived_dirs_by_milestone = {"v5.11": set()}  # never archived

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
    involved, must still be detected via before/after snapshot diff."""
    phases_root = tmp_path / "phases"
    phases_root.mkdir()
    phase_dir = phases_root / "144-chunked-discovery-core"
    phase_dir.mkdir()
    (phase_dir / "144-01-PLAN.md").write_text("plain content", encoding="utf-8")

    before = vpg.disk_phase_dirs_under(phases_root)
    assert "144-chunked-discovery-core" in before

    # Simulate phases.clear: a plain filesystem delete, never git-tracked.
    (phase_dir / "144-01-PLAN.md").unlink()

    after = vpg.disk_phase_dirs_under(phases_root)
    assert "144-chunked-discovery-core" not in after

    phase_map_rows = [("144", "v5.11")]
    blocked, reasons, _summary = vpg.check_destructive_archive(
        phase_map_rows, after, {"v5.11": set()}
    )
    assert blocked is True
    assert any("144" in r for r in reasons)
