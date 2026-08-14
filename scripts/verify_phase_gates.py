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
parsing helpers that feed them real data. It does NOT wire a git hook —
that is a separate plan. `check_destructive_archive()`'s only achievable
guarantee is that *the next commit* after an unarchived destructive
deletion is blocked until the gap is resolved — a git hook has zero
visibility into (and zero ability to prevent) a plain filesystem delete
that happens outside of any git operation; it cannot make the delete
itself refuse to run.

Lives under scripts/ -- NOT imported by any runtime code.
"""
from __future__ import annotations

import pathlib
import re

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PHASES_ROOT = REPO_ROOT / ".planning" / "phases"
MILESTONES_ROOT = REPO_ROOT / ".planning" / "milestones"
STATE_PATH = REPO_ROOT / ".planning" / "STATE.md"
ROADMAP_PATH = REPO_ROOT / ".planning" / "ROADMAP.md"
UAT_SERIES_PATH = REPO_ROOT / "docs" / "UAT-SERIES.md"

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

