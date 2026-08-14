#!/usr/bin/env python3
"""Pure decision core for QUIRK's phase-completion artifact gate (ARTIFACT-01..04).

Why this exists: three v5.11 gaps shipped silently because nothing checked
phase-close artifacts before the phase was marked Complete —

  - Phase 145's VERIFICATION.md was written retroactively, months after the
    phase closed (ARTIFACT-01).
  - Phase 147's VALIDATION.md sat at `nyquist_compliant: false` for the
    entire v5.11 milestone, only caught by a manual audit closeout
    (ARTIFACT-02).
  - Phase 144 shipped a user-facing scanner change with no matching
    docs/UAT-SERIES.md entry, only caught by a later PM review
    (ARTIFACT-03).

A fourth incident — the `phases.clear` operation described in
`.planning/milestones/v5.11-phases/ARCHIVE-MANIFEST.md` — deleted ~39
unrecoverable phase files from `.planning/phases/` as a plain filesystem
operation with zero git-visible trigger, because 91% of files under that
directory were never `git add`-ed (`.planning/` is gitignored). Only 19 of
~58 phase files survived (ARTIFACT-04).

This module implements the pure, unit-testable decision logic that would
have caught all four incidents: `check_phase_close()` (ARTIFACT-01/02/03)
and `check_destructive_archive()` (ARTIFACT-04), plus the file-loading /
parsing helpers that feed them real data (151-01), and `main()` — the CLI
glue that reads `git diff --cached` output plus on-disk `.planning/`/`docs/`
state and wires it all into an actual git pre-commit hook via
`.githooks/pre-commit` (151-02). `check_destructive_archive()`'s only
achievable guarantee is that *the next commit* after an unarchived
destructive deletion is blocked until the gap is resolved — a git hook has
zero visibility into (and zero ability to prevent) a plain filesystem delete
that happens outside of any git operation; it cannot make the delete
itself refuse to run.

Run modes:
    python3 scripts/verify_phase_gates.py           # invoked by .githooks/pre-commit

Exit codes: 0 = clean, 1 = a real gate violation (block the commit), 2 = a
hard/unexpected error (e.g. the `git diff` subprocess itself failed) —
both 1 and 2 must abort the commit from the shell wrapper's perspective.

Lives under scripts/ -- NOT imported by any runtime code.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys
from typing import Callable

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
# NOTE: no PHASES_ROOT/MILESTONES_ROOT/STATE_PATH/ROADMAP_PATH/UAT_SERIES_PATH
# module constants here by design -- every real call site (_run_phase_close_
# check(), _run_destructive_archive_check(), main()) routes through the
# injectable `repo_root` parameter instead, which is required for the test
# suite's tmp_path-based fixtures to work. Do not add hardcoded-REPO_ROOT
# path constants; they would bypass that seam.

# ARTIFACT-03: path prefixes/globs considered "user-facing" per CONTEXT.md D-05
# and RESEARCH.md Assumption A1. tests/, scripts/, .github/, and docs/-only
# paths never match.
_USER_FACING_PREFIXES = (
    "src/dashboard/",
    "quirk/cli/",
    "quirk/reports/",
    "quirk/scanner/",
    "quirk/hardware",
)

_PENDING_GLYPH = "⬜ pending"  # "⬜ pending"


# ---------------------------------------------------------------------------
# ARTIFACT-01/02/03: check_phase_close()
# ---------------------------------------------------------------------------


def is_validation_stale(
    frontmatter: dict | None, body_text: str
) -> tuple[bool, list[str]]:
    """Pure. Decide whether a phase's VALIDATION.md is stale.

    Stale when:
      - the file is missing entirely (frontmatter is None) — a phase cannot
        close with no VALIDATION.md either;
      - `nyquist_compliant` is explicitly False;
      - the body contains a genuine pending table row (a `|`-delimited line
        whose cells include the literal pending glyph), NOT the legend line
        (`*Status: ...`) that documents the glyph vocabulary (Pitfall 4).

    Returns (stale, reasons).
    """
    reasons: list[str] = []

    if frontmatter is None:
        reasons.append("VALIDATION.md is missing or has no parseable frontmatter")
        return True, reasons

    if frontmatter.get("nyquist_compliant") is False:
        reasons.append("VALIDATION.md frontmatter has nyquist_compliant: false")

    for line in (body_text or "").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if stripped.startswith("*Status:"):
            continue
        if _PENDING_GLYPH in stripped:
            reasons.append(
                f"VALIDATION.md has a pending table row: {stripped!r}"
            )

    return bool(reasons), reasons


def user_facing_plan_match(files_modified: list[str]) -> bool:
    """Pure. True if any path in files_modified looks user-facing per the
    D-05 glob list."""
    for path in files_modified or []:
        for prefix in _USER_FACING_PREFIXES:
            if path.startswith(prefix):
                return True
    return False


def uat_series_has_entry(uat_series_text: str, phase_num: str) -> bool:
    """Pure. True if docs/UAT-SERIES.md has a `## Series N: ... (Phase
    {phase_num}` heading for this phase number."""
    pattern = re.compile(
        rf"^## Series \d+:.*\(Phase {re.escape(phase_num)}\b", re.MULTILINE
    )
    return pattern.search(uat_series_text or "") is not None


def check_phase_close(
    phase_num: str,
    verification_exists: bool,
    validation_frontmatter: dict | None,
    validation_body_text: str | None,
    plan_files_modified: list[list[str]],
    uat_series_text: str,
) -> tuple[bool, list[str], str]:
    """Pure. Aggregate ARTIFACT-01/02/03 into one verdict.

    Returns (blocked, reasons, summary_markdown). One reason string per
    violated gate (not one combined string).
    """
    reasons: list[str] = []

    # ARTIFACT-01: VERIFICATION.md must exist.
    if not verification_exists:
        reasons.append(
            f"Phase {phase_num}: VERIFICATION.md is missing — a phase cannot "
            "close without a verification report."
        )

    # ARTIFACT-02: VALIDATION.md must not be stale.
    stale, stale_reasons = is_validation_stale(
        validation_frontmatter, validation_body_text or ""
    )
    if stale:
        for reason in stale_reasons:
            reasons.append(f"Phase {phase_num}: {reason}")

    # ARTIFACT-03: user-facing plans need a matching UAT-SERIES.md entry.
    any_user_facing = any(
        user_facing_plan_match(files) for files in plan_files_modified
    )
    if any_user_facing and not uat_series_has_entry(uat_series_text, phase_num):
        reasons.append(
            f"Phase {phase_num}: one or more plans touch user-facing paths but "
            "docs/UAT-SERIES.md has no matching Series entry for this phase."
        )

    blocked = bool(reasons)

    lines = [f"## Phase {phase_num} Close Gate", ""]
    if blocked:
        lines.append("### BLOCKED")
        for reason in reasons:
            lines.append(f"- {reason}")
    else:
        lines.append(
            "Clean — VERIFICATION.md present, VALIDATION.md current, "
            "UAT-SERIES.md coverage satisfied (or not required)."
        )
    summary_markdown = "\n".join(lines) + "\n"

    return blocked, reasons, summary_markdown


def load_validation_frontmatter(path: pathlib.Path) -> dict | None:
    """Loader. Missing file, missing frontmatter delimiters, or malformed
    YAML -> None, never raise."""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def load_phase_plan_files_modified(phase_dir: pathlib.Path) -> list[list[str]]:
    """Loader. Glob `phase_dir` for `*-PLAN.md` files (sorted), extract each
    one's `files_modified` frontmatter key as one inner list per file.

    A PLAN.md with missing/malformed frontmatter or no files_modified key
    contributes an empty inner list rather than being skipped. A nonexistent
    or empty phase_dir returns [], never raises.
    """
    if not phase_dir.exists() or not phase_dir.is_dir():
        return []

    result: list[list[str]] = []
    for plan_path in sorted(phase_dir.glob("*-PLAN.md")):
        text = plan_path.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        files_modified: list[str] = []
        if len(parts) >= 3:
            try:
                data = yaml.safe_load(parts[1])
            except yaml.YAMLError:
                data = None
            if isinstance(data, dict):
                raw = data.get("files_modified")
                if isinstance(raw, list):
                    files_modified = [str(item) for item in raw]
        result.append(files_modified)

    return result


# ---------------------------------------------------------------------------
# ARTIFACT-04: check_destructive_archive()
# ---------------------------------------------------------------------------


def disk_phase_dirs_under(phases_root: pathlib.Path) -> set[str]:
    """Non-empty phase directory names currently present under phases_root.
    An empty directory (all files removed but the directory left behind)
    counts as absent — this is what makes an untracked-file deletion
    (Pitfall 1) detectable via a before/after snapshot diff at the caller
    level, with no git involvement here at all."""
    if not phases_root.exists():
        return set()
    return {
        p.name
        for p in phases_root.iterdir()
        if p.is_dir() and any(p.iterdir())
    }


def archived_phase_dirs(
    milestones_root: pathlib.Path, milestone_tag: str
) -> set[str]:
    """Directory names under `.planning/milestones/{milestone_tag}-phases/`."""
    archive_dir = milestones_root / f"{milestone_tag}-phases"
    if not archive_dir.exists():
        return set()
    return {p.name for p in archive_dir.iterdir() if p.is_dir()}


_PHASE_MAP_HEADING_RE = re.compile(r"^## v(\d+\.\d+) Phase Map")
_PHASE_MAP_ROW_RE = re.compile(r"^\|\s*(\S+)\s*\|.*\|\s*([^|]*?)\s*\|\s*$")


def parse_state_phase_maps(state_text: str) -> list[tuple[str, str, str]]:
    """Pure. Regex-scan `## v<version> Phase Map` section headers and, for
    each, parse the markdown table rows immediately following. Returns a
    list of (phase_num, milestone_tag, status_cell) tuples."""
    results: list[tuple[str, str, str]] = []
    current_milestone: str | None = None

    for raw_line in (state_text or "").splitlines():
        stripped_line = raw_line.strip()

        heading_match = _PHASE_MAP_HEADING_RE.match(stripped_line)
        if heading_match:
            current_milestone = f"v{heading_match.group(1)}"
            continue

        if stripped_line.startswith("##"):
            # Any other heading ends the current phase-map section.
            current_milestone = None
            continue

        if current_milestone is None:
            continue

        row_match = _PHASE_MAP_ROW_RE.match(raw_line.rstrip())
        if not row_match:
            continue
        phase_num, status_cell = row_match.group(1), row_match.group(2)
        # Skip separator rows (e.g. "---") and the header row ("Phase").
        # `\d+(?:\.\d+)?` (not `.isdigit()`) so decimal sub-phase rows (e.g.
        # "64.1") are kept -- matches the trigger regex's handling of the
        # same shape (Open Question 2).
        if not re.match(r"^\d+(?:\.\d+)?$", phase_num):
            continue
        results.append((phase_num, current_milestone, status_cell))

    return results


# Historical deletions accepted as permanent, closed facts before this gate
# existed — NOT a growing allowlist. Adding to this set requires the same
# "accepted historical fact, future-only enforcement" bar as D-06 in
# 151-CONTEXT.md, and a citation to the incident record. Phase 144's
# directory was deleted with no archive by the exact incident this gate
# exists to prevent going forward (.planning/milestones/v5.11-phases/
# ARCHIVE-MANIFEST.md); D-06 explicitly rejects backfilling it. Without this
# exception, check_destructive_archive() would block every future commit
# once the hook is installed, since Phase 144 can never gain a directory.
_ACCEPTED_HISTORICAL_ARCHIVE_GAPS: frozenset[tuple[str, str]] = frozenset(
    {("144", "v5.11")}
)


def check_destructive_archive(
    phase_map_rows: list[tuple[str, str]],
    disk_phase_dirs: set[str],
    archived_dirs_by_milestone: dict[str, set[str]],
) -> tuple[bool, list[str], str]:
    """Pure. For every (phase_num, milestone_tag) row whose status is
    Complete, verify a matching directory exists either on disk or in the
    milestone's archive. Neither existing means the phase's content has
    vanished with no matching milestone archive.

    Rows matching `_ACCEPTED_HISTORICAL_ARCHIVE_GAPS` are skipped — pre-gate
    incidents already recorded and accepted as closed, not new deletions.

    NOTE on scope (Pitfall 2): this function proves that *the next commit*
    after an unarchived deletion is blocked — it cannot prove, and does not
    claim, that the delete itself never happens. A git hook has no
    visibility into non-git filesystem operations.

    Returns (blocked, reasons, summary_markdown).
    """
    reasons: list[str] = []

    for phase_num, milestone_tag in phase_map_rows:
        if (phase_num, milestone_tag) in _ACCEPTED_HISTORICAL_ARCHIVE_GAPS:
            continue

        on_disk = any(
            name == phase_num or name.startswith(f"{phase_num}-")
            for name in disk_phase_dirs
        )
        if on_disk:
            continue

        archived = archived_dirs_by_milestone.get(milestone_tag, set())
        is_archived = any(
            name == phase_num or name.startswith(f"{phase_num}-")
            for name in archived
        )
        if is_archived:
            continue

        reasons.append(
            f"Phase {phase_num} (milestone {milestone_tag}) is marked Complete "
            "but has no live directory under .planning/phases/ and no archived "
            "directory under .planning/milestones/ — this is the "
            "ARCHIVE-MANIFEST.md incident shape "
            "(.planning/milestones/v5.11-phases/ARCHIVE-MANIFEST.md)."
        )

    blocked = bool(reasons)

    lines = ["## Destructive Archive Gate", ""]
    if blocked:
        lines.append("### BLOCKED")
        for reason in reasons:
            lines.append(f"- {reason}")
    else:
        lines.append(
            "Clean — every Complete-marked phase has a live or archived "
            "directory."
        )
    summary_markdown = "\n".join(lines) + "\n"

    return blocked, reasons, summary_markdown


# ---------------------------------------------------------------------------
# 151-02: main() CLI glue
# ---------------------------------------------------------------------------

# Pattern 5 (real, verified via `git show b09c9bc`): a phase-close commit
# adds a `- [x] **Phase N: Name**` line to the staged diff of
# .planning/ROADMAP.md. `\d+(?:\.\d+)?` (Open Question 2) also matches
# decimal sub-phase numbers (e.g. `64.1`). Applied only to added lines
# (`^\+`, never `^\+\+\+`, since the second char of `+++` is `+` not `-`).
_PHASE_CLOSE_TRIGGER_RE = re.compile(
    r"^\+- \[x\] \*\*Phase (\d+(?:\.\d+)?):", re.MULTILINE
)


def _extract_phase_close_triggers(diff_text: str) -> list[str]:
    """Pure. Return EVERY phase number string whose checkbox flips to
    complete in `diff_text` (the staged diff of .planning/ROADMAP.md), in
    order of appearance, deduplicated. A commit closing several phases at
    once (e.g. a batch/squashed milestone-closeout commit) must run
    ARTIFACT-01/02/03 for all of them, not just the first match."""
    seen: list[str] = []
    for match in _PHASE_CLOSE_TRIGGER_RE.finditer(diff_text or ""):
        phase_num = match.group(1)
        if phase_num not in seen:
            seen.append(phase_num)
    return seen


def _run_git(args: list[str], cwd: pathlib.Path) -> subprocess.CompletedProcess:
    """Thin wrapper: list-form argv, `check=False`, caller handles the
    returncode. Matches `release_tag_hygiene.py`'s `_run_gh_json` pattern.
    This is the seam mocked/injected in unit tests so `main()`'s branching
    logic can be tested without a real git repo."""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
    )


def _run_phase_close_check(phase_num: str, repo_root: pathlib.Path) -> int:
    """Disk-reading wrapper around check_phase_close(). Resolves the
    triggered phase's on-disk directory, assembles all five arguments from
    real disk state — including a mandatory call to
    load_phase_plan_files_modified() (never an empty-list placeholder) —
    and returns 0 (clean) or 1 (blocked)."""
    phases_root = repo_root / ".planning" / "phases"
    matches = sorted(phases_root.glob(f"{phase_num}-*"))
    phase_dir = matches[0] if matches else phases_root / phase_num

    verification_path = phase_dir / f"{phase_num}-VERIFICATION.md"
    verification_exists = verification_path.exists()

    validation_path = phase_dir / f"{phase_num}-VALIDATION.md"
    validation_frontmatter = load_validation_frontmatter(validation_path)
    validation_body_text = ""
    if validation_path.exists():
        text = validation_path.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        if len(parts) >= 3:
            validation_body_text = parts[2]

    # Mandatory: real loader output, never an empty-list stand-in.
    plan_files_modified = load_phase_plan_files_modified(phase_dir)

    uat_series_path = repo_root / "docs" / "UAT-SERIES.md"
    uat_series_text = (
        uat_series_path.read_text(encoding="utf-8")
        if uat_series_path.exists()
        else ""
    )

    blocked, reasons, summary_markdown = check_phase_close(
        phase_num,
        verification_exists,
        validation_frontmatter,
        validation_body_text,
        plan_files_modified,
        uat_series_text,
    )
    print(summary_markdown)
    if blocked:
        for reason in reasons:
            sys.stderr.write(f"verify_phase_gates: {reason}\n")
        return 1
    return 0


def _run_destructive_archive_check(repo_root: pathlib.Path) -> int:
    """Disk-reading wrapper around check_destructive_archive(). Runs
    unconditionally (not diff-gated) — must catch damage with no
    git-visible trigger event."""
    state_path = repo_root / ".planning" / "STATE.md"
    state_text = (
        state_path.read_text(encoding="utf-8") if state_path.exists() else ""
    )
    phase_map_rows_all = parse_state_phase_maps(state_text)
    phase_map_rows = [
        (phase_num, milestone_tag)
        for phase_num, milestone_tag, status_cell in phase_map_rows_all
        if "Complete" in status_cell
    ]

    disk_phase_dirs = disk_phase_dirs_under(repo_root / ".planning" / "phases")

    milestones_root = repo_root / ".planning" / "milestones"
    milestone_tags = {milestone_tag for _phase_num, milestone_tag in phase_map_rows}
    archived_dirs_by_milestone = {
        milestone_tag: archived_phase_dirs(milestones_root, milestone_tag)
        for milestone_tag in milestone_tags
    }

    blocked, reasons, summary_markdown = check_destructive_archive(
        phase_map_rows, disk_phase_dirs, archived_dirs_by_milestone
    )
    print(summary_markdown)
    if blocked:
        for reason in reasons:
            sys.stderr.write(f"verify_phase_gates: {reason}\n")
        return 1
    return 0


def main(
    argv: list[str] | None = None,
    *,
    repo_root: pathlib.Path | None = None,
    git_runner: Callable[[], subprocess.CompletedProcess] | None = None,
) -> int:
    """CLI entrypoint invoked by `.githooks/pre-commit`.

    D-03 diff-gate for the phase-close checks (cheap no-op on unrelated
    commits); check_destructive_archive() runs unconditionally per
    RESEARCH.md Open Question 1's resolution. `repo_root`/`git_runner` are
    injectable seams for testing `main()`'s branching logic without a real
    git repo or touching the real filesystem.
    """
    resolved_repo_root = repo_root if repo_root is not None else REPO_ROOT

    if git_runner is None:
        roadmap_path = resolved_repo_root / ".planning" / "ROADMAP.md"

        def git_runner() -> subprocess.CompletedProcess:
            return _run_git(
                ["diff", "--cached", "--", str(roadmap_path)],
                cwd=resolved_repo_root,
            )

    git_result = git_runner()
    if git_result.returncode != 0:
        sys.stderr.write(
            "verify_phase_gates: hard error: `git diff --cached` exited "
            f"{git_result.returncode}: {git_result.stderr.strip()}\n"
        )
        return 2

    phase_nums = _extract_phase_close_triggers(git_result.stdout)

    exit_code = 0
    for phase_num in phase_nums:
        exit_code = max(exit_code, _run_phase_close_check(phase_num, resolved_repo_root))

    exit_code = max(exit_code, _run_destructive_archive_check(resolved_repo_root))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
