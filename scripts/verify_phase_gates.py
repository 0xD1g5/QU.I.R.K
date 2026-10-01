#!/usr/bin/env python3
"""Pure decision core for QUIRK's phase-completion artifact gate (ARTIFACT-01..05).

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

ARTIFACT-05 (Phase 220, CITRUTH-03 / D-13): in v5.25, five phases were
verified `passed` while CI was red, because nobody had to show a green run
at the commit being closed. `check_ci_truth()` requires the closing phase's
NN-VERIFICATION.md frontmatter to carry a `ci:` block (the JSON report of
`scripts/branch_ci_state.py --compare-main`). Every required job must be
`success`, with required-ness re-derived through branch_ci_state.job_gating
rather than read from the block. `ci.head_sha` must equal the local HEAD,
which is the parent of the commit being made. The one escape is an honest
`ci_waiver:` bound to main's own recorded failing-node set. The check stays
offline. It only reads the frontmatter plus `git rev-parse HEAD`, so the
hook never needs network access or a gh token.

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
    {phase_num}` heading for this phase number.

    The series number accepts a decimal suffix (`## Series 184.1:`) because
    gap-closure phases are numbered X.Y and carry their own series. The
    original `\\d+:` could not match past the dot, so it matched "184" and then
    demanded a colon it would never find — meaning NO decimal phase could ever
    satisfy this gate. Caught at Phase 184.1's close, the first decimal phase
    to reach one; the gate blocked a commit whose Series heading was present
    and correctly formatted.

    Separately, `\\b` alone let a query for integer phase "184" be satisfied by
    a `(Phase 184.1 ...)` heading, since a word boundary sits between "4" and
    ".". That fail-open predates the decimal fix above and is closed here with
    `(?!\\.\\d)`: a gap-closure series must not discharge its parent phase's gate.
    """
    pattern = re.compile(
        rf"^## Series \d+(?:\.\d+)*:.*\(Phase {re.escape(phase_num)}\b(?!\.\d)",
        re.MULTILINE,
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


# ---------------------------------------------------------------------------
# ARTIFACT-05 (CITRUTH-03 / D-13): check_ci_truth()
# ---------------------------------------------------------------------------

_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_BRANCH_CI_STATE_CACHE: dict[str, object] = {}


def _branch_ci_state():
    """Lazy, cached load of the sibling scripts/branch_ci_state.py, the single
    source of required-ness (REQUIRED_WORKFLOWS / REQUIRED_JOBS / job_gating).
    Uses spec_from_file_location so sys.path is never mutated. Returns None
    when the file is missing or fails to import; check_ci_truth() turns that
    into a blocking reason instead of crashing the hook."""
    if "module" in _BRANCH_CI_STATE_CACHE:
        return _BRANCH_CI_STATE_CACHE["module"]
    module = None
    path = pathlib.Path(__file__).with_name("branch_ci_state.py")
    if path.exists():
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "_vpg_branch_ci_state", path
            )
            if spec is not None and spec.loader is not None:
                candidate = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(candidate)
                module = candidate
        except Exception:  # noqa: BLE001 - any import failure blocks, never crashes
            module = None
    _BRANCH_CI_STATE_CACHE["module"] = module
    return module


def _str_list(value) -> list[str] | None:
    """A list of non-empty strings, or None when the shape is anything else."""
    if not isinstance(value, list):
        return None
    if not all(isinstance(item, str) and item.strip() for item in value):
        return None
    return list(value)


def _check_ci_waiver(waiver, ci: dict, red_jobs: list) -> list[str]:
    """Return why `waiver` does NOT cover `red_jobs` (empty list = covered)."""
    if not isinstance(waiver, dict):
        return ["ci_waiver is malformed (expected a mapping with `reason` and "
                "`failing_nodes`)."]
    problems: list[str] = []
    reason = waiver.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        problems.append("ci_waiver has no non-empty `reason`.")
    nodes = _str_list(waiver.get("failing_nodes"))
    if not nodes:
        problems.append("ci_waiver.failing_nodes must be a non-empty list of "
                        "pytest node ids.")
        nodes = []
    waiver_set = set(nodes)

    main = ci.get("main")
    main_set: set[str] | None = None
    if isinstance(main, dict) and isinstance(main.get("workflows"), list):
        main_set = set()
        for entry in main["workflows"]:
            if not isinstance(entry, dict):
                main_set = None
                break
            entry_nodes = _str_list(entry.get("failing_nodes", []))
            if entry_nodes is None:
                main_set = None
                break
            main_set.update(entry_nodes)
    if main_set is None:
        problems.append("ci_waiver requires a well-formed `ci.main` block "
                        "(run branch_ci_state.py --compare-main) to compare "
                        "against; none was recorded.")
    elif waiver_set and waiver_set != main_set:
        problems.append(
            "ci_waiver.failing_nodes does not equal main's recorded failing "
            f"set (only in waiver: {sorted(waiver_set - main_set)}; only on "
            f"main: {sorted(main_set - waiver_set)})."
        )

    for workflow, job, _conclusion, job_nodes in red_jobs:
        if not job_nodes:
            problems.append(
                f"ci_waiver cannot cover required job {job!r} ({workflow}): no "
                "failing nodes were extracted, and a job-level red is never "
                "waivable."
            )
            continue
        uncovered = sorted(set(job_nodes) - waiver_set)
        if uncovered:
            problems.append(
                f"ci_waiver does not cover required job {job!r} ({workflow}) "
                f"failing nodes {uncovered}."
            )
    return problems


def _check_ci_workflow(
    bcs, wf: str, entries: list, ci_head: str | None, red_jobs: list
) -> list[str]:
    """Check one required workflow's recorded entry. Appends every red
    required job (re-derived via job_gating) to `red_jobs` as
    (workflow, job, conclusion, failing_nodes); returns non-waivable
    problems (absent, duplicated, unobserved, sha mismatch, malformed,
    missing required job)."""
    if not entries:
        return [f"required workflow {wf!r} is absent from `ci.workflows`."]
    if len(entries) > 1:
        return [f"required workflow {wf!r} appears more than once in "
                "`ci.workflows`."]
    entry = entries[0]
    if entry.get("observed") is not True:
        return [f"{wf}: not observed (no completed run at HEAD); dispatch it "
                "and re-verify."]
    if ci_head is not None and entry.get("head_sha") != ci_head:
        return [f"{wf}: run head_sha {entry.get('head_sha')!r} does not match "
                f"`ci.head_sha` {ci_head}."]
    event = entry.get("event")
    if not isinstance(event, str):
        event = ""
    jobs = entry.get("jobs")
    if not isinstance(jobs, list):
        return [f"{wf}: `jobs` is missing or not a list."]

    problems: list[str] = []
    seen: set[str] = set()
    for job in jobs:
        if not isinstance(job, dict) or not isinstance(job.get("name"), str):
            problems.append(f"{wf}: malformed job entry {job!r}.")
            continue
        jname = job["name"]
        seen.add(jname)
        required, _why = bcs.job_gating(wf, jname, event)
        conclusion = job.get("conclusion")
        if required and conclusion != "success":
            nodes = _str_list(job.get("failing_nodes", [])) or []
            red_jobs.append((wf, jname, conclusion, nodes))
    for jname in bcs.REQUIRED_JOBS.get(wf, ()):
        if jname not in seen and bcs.job_gating(wf, jname, event)[0]:
            problems.append(
                f"{wf}: required job {jname!r} is missing from the recorded run."
            )
    return problems


def check_ci_truth(
    phase_num: str,
    verification_frontmatter: dict | None,
    current_head_sha: str | None,
) -> list[str]:
    """Pure. ARTIFACT-05: decide whether a phase's recorded CI truth allows
    it to close. Returns blocking reasons, each one prefixed
    `Phase {N}: ARTIFACT-05 (CITRUTH-03):`. An empty list means clean. It
    never raises, and every malformed shape becomes a reason.

    `ci:` schema (the JSON report of `scripts/branch_ci_state.py
    --compare-main`, pasted into NN-VERIFICATION.md frontmatter):
        ci:
          head_sha: <40-hex>           # branch HEAD that was observed
          workflows:
            - name: Python CI | Dashboard Quality
              head_sha: <40-hex>       # must equal ci.head_sha
              event: workflow_dispatch | pull_request | push
              observed: true           # completed run AT head_sha
              jobs:
                - {name, conclusion, failing_nodes: [node ids]}
          main:                        # required only when a waiver is used
            workflows: [{name, failing_nodes: [node ids]}]
    `verdict`, `reasons`, and the per-job `required` / `advisory_reason`
    fields may be present, but they are NEVER treated as authority.
    Required-ness is recomputed with branch_ci_state.job_gating(workflow, job,
    event), so hand-editing a flag cannot turn a red job advisory (T-220-20).

    `ci_waiver:` schema:
        ci_waiver:
          reason: <non-empty str>
          failing_nodes: [<node id>, ...]   # non-empty
    A waiver covers red required jobs only when all of the following hold:
    the reason is non-empty; set(failing_nodes) equals the union of
    `ci.main.workflows[*].failing_nodes`; and every red required job has a
    non-empty failing_nodes list fully contained in the waiver. A job-level
    red with no extractable nodes is never waivable. A waiver never covers
    a stale, unobserved, missing, or malformed observation (T-220-21).

    HEAD-equality rule (D-12): `ci.head_sha` must equal `current_head_sha`.
    In a pre-commit hook that is the local HEAD, i.e. the parent of the
    commit being made. A green run at any other sha does not count as an
    observation of what is being closed, so the caller must push,
    re-dispatch, and re-verify (T-220-22).

    Why it stays offline: the hook runs on every commit under system
    python3. It must be deterministic, need no gh token, and never go red
    because the network is down. The live GitHub query belongs in
    branch_ci_state.py, which runs at verification time. This gate only
    proves that the recorded evidence is complete, current, and green.
    Forging a block with copied run ids is accepted risk T-220-23.

    `status: passed` combined with any blocking reason adds an explicit
    "status: passed over red/absent CI" violation.
    """
    prefix = f"Phase {phase_num}: ARTIFACT-05 (CITRUTH-03):"
    fm = verification_frontmatter if isinstance(verification_frontmatter, dict) else {}
    status_passed = str(fm.get("status", "")).strip().lower() == "passed"
    problems: list[str] = []
    red_jobs: list[tuple[str, str, object, list[str]]] = []

    ci = fm.get("ci")
    if ci is None:
        problems.append(
            "VERIFICATION.md has no `ci:` block. Record the observation with "
            "`python3 scripts/branch_ci_state.py --compare-main` at the "
            "current HEAD and paste its report under `ci:`."
        )
    elif not isinstance(ci, dict):
        problems.append("`ci:` block is malformed (expected a mapping).")
    else:
        bcs = _branch_ci_state()
        if bcs is None:
            problems.append(
                "scripts/branch_ci_state.py is missing or failed to import, so "
                "required-ness cannot be derived; refusing to close."
            )
        ci_head = ci.get("head_sha")
        if not isinstance(ci_head, str) or not _SHA40_RE.match(ci_head):
            problems.append(
                f"`ci.head_sha` is not a 40-hex commit sha (got {ci_head!r})."
            )
            ci_head = None
        elif current_head_sha is None:
            problems.append(
                "cannot resolve the local HEAD sha (`git rev-parse HEAD` "
                "failed), so the recorded CI cannot be matched to it."
            )
        elif ci_head != current_head_sha:
            problems.append(
                f"`ci.head_sha` {ci_head} is not the current HEAD "
                f"{current_head_sha}. Commits landed after CI was observed: "
                "push, re-dispatch CI at the new HEAD, re-verify, and record "
                "the fresh `ci:` block (D-12)."
            )

        workflows = ci.get("workflows")
        if not isinstance(workflows, list):
            problems.append("`ci.workflows` is missing or not a list.")
        elif bcs is not None:
            by_name: dict[str, list[dict]] = {}
            for entry in workflows:
                if not isinstance(entry, dict) or not isinstance(
                    entry.get("name"), str
                ):
                    problems.append(
                        f"`ci.workflows` has a malformed entry: {entry!r}."
                    )
                    continue
                by_name.setdefault(entry["name"], []).append(entry)
            for wf in bcs.REQUIRED_WORKFLOWS:
                problems.extend(_check_ci_workflow(
                    bcs, wf, by_name.get(wf, []), ci_head, red_jobs
                ))

    if red_jobs:
        red_reasons = [
            f"{wf}: required job {job!r} concluded {conclusion}"
            + (f" (failing nodes: {nodes})" if nodes else "")
            + "."
            for wf, job, conclusion, nodes in red_jobs
        ]
        waiver = fm.get("ci_waiver")
        if waiver is None:
            problems.extend(red_reasons)
        else:
            waiver_problems = _check_ci_waiver(waiver, ci, red_jobs)
            if waiver_problems:
                problems.extend(red_reasons)
                problems.extend(waiver_problems)

    if problems and status_passed:
        problems.append(
            "VERIFICATION.md says `status: passed` over red/absent/unobserved "
            "CI. That is a gate violation, not a verification."
        )

    return [f"{prefix} {p}" for p in problems]


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


# D-03 (151-CONTEXT.md) / RESEARCH.md Pattern 5: phase-close is also
# detected via a STATE.md phase-map row whose Status cell is added/changed
# to "Complete" in the staged diff — a dual-source trigger, alongside the
# ROADMAP.md checkbox flip above. Matches only added table rows (`^\+\|`),
# and reuses the same `\d+(?:\.\d+)?` phase-number shape (Open Question 2)
# as the ROADMAP.md trigger, so decimal sub-phases also trigger from a
# STATE.md-only edit.
_STATE_PHASE_ROW_ADDED_RE = re.compile(
    r"^\+\|\s*(\d+(?:\.\d+)?)\s*\|.*\|\s*([^|]*?)\s*\|\s*$", re.MULTILINE
)


def _extract_state_phase_close_triggers(diff_text: str) -> list[str]:
    """Pure. Return every phase number string whose STATE.md phase-map row
    is added/changed to a Status cell containing "Complete" in `diff_text`
    (the staged diff of .planning/STATE.md), in order of appearance,
    deduplicated. This is the second of the two trigger sources D-03
    describes -- a phase-close whose only git-visible signal lives in
    STATE.md (e.g. a retroactive/out-of-band status correction with no
    matching ROADMAP.md checkbox flip in the same commit) must still fire
    ARTIFACT-01/02/03."""
    seen: list[str] = []
    for match in _STATE_PHASE_ROW_ADDED_RE.finditer(diff_text or ""):
        phase_num, status_cell = match.group(1), match.group(2)
        if "Complete" in status_cell and phase_num not in seen:
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


def _run_phase_close_check(
    phase_num: str,
    repo_root: pathlib.Path,
    head_sha: str | None = None,
) -> int:
    """Disk-reading wrapper around check_phase_close(). Resolves the
    triggered phase's on-disk directory, assembles all five arguments from
    real disk state — including a mandatory call to
    load_phase_plan_files_modified() (never an empty-list placeholder) —
    and returns 0 (clean) or 1 (blocked). ARTIFACT-05 (check_ci_truth) is
    evaluated here too, against `head_sha` (the local HEAD resolved by
    main()), and its reasons are merged into the same verdict."""
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

    # ARTIFACT-05: reuse the generic frontmatter loader (only if the file exists).
    verification_frontmatter = (
        load_validation_frontmatter(verification_path)
        if verification_exists
        else None
    )
    ci_reasons = check_ci_truth(phase_num, verification_frontmatter, head_sha)
    ci_lines = ["### ARTIFACT-05 CI truth", ""]
    if ci_reasons:
        ci_lines.append("BLOCKED")
        ci_lines.extend(f"- {reason}" for reason in ci_reasons)
    else:
        ci_lines.append(
            f"Clean: recorded CI is green at HEAD {head_sha} (or honestly waived)."
        )
    summary_markdown = summary_markdown + "\n" + "\n".join(ci_lines) + "\n"
    reasons = list(reasons) + ci_reasons
    blocked = blocked or bool(ci_reasons)

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
    head_sha_resolver: Callable[[], str | None] | None = None,
) -> int:
    """CLI entrypoint invoked by `.githooks/pre-commit`.

    D-03 diff-gate for the phase-close checks (cheap no-op on unrelated
    commits) — dual-source per D-03/Pattern 5: a phase-close is detected via
    EITHER a ROADMAP.md checkbox flip to `[x]` OR a STATE.md phase-map
    Status cell change to `Complete`, unioned. check_destructive_archive()
    runs unconditionally per RESEARCH.md Open Question 1's resolution.
    `repo_root`/`git_runner` are injectable seams for testing `main()`'s
    branching logic without a real git repo or touching the real
    filesystem. `head_sha_resolver` (220-05, ARTIFACT-05) returns the local
    HEAD sha the recorded `ci:` block must match; the default runs
    `git rev-parse HEAD` and returns None on failure. It is only called when
    a phase-close trigger fired.
    """
    resolved_repo_root = repo_root if repo_root is not None else REPO_ROOT

    if git_runner is None:
        roadmap_path = resolved_repo_root / ".planning" / "ROADMAP.md"
        state_path = resolved_repo_root / ".planning" / "STATE.md"

        def git_runner() -> subprocess.CompletedProcess:
            return _run_git(
                ["diff", "--cached", "--", str(roadmap_path), str(state_path)],
                cwd=resolved_repo_root,
            )

    git_result = git_runner()
    if git_result.returncode != 0:
        sys.stderr.write(
            "verify_phase_gates: hard error: `git diff --cached` exited "
            f"{git_result.returncode}: {git_result.stderr.strip()}\n"
        )
        return 2

    phase_nums: list[str] = []
    for phase_num in _extract_phase_close_triggers(
        git_result.stdout
    ) + _extract_state_phase_close_triggers(git_result.stdout):
        if phase_num not in phase_nums:
            phase_nums.append(phase_num)

    if head_sha_resolver is None:

        def head_sha_resolver() -> str | None:
            result = _run_git(["rev-parse", "HEAD"], cwd=resolved_repo_root)
            if result.returncode != 0:
                return None
            return result.stdout.strip() or None

    head_sha = head_sha_resolver() if phase_nums else None

    exit_code = 0
    for phase_num in phase_nums:
        exit_code = max(
            exit_code,
            _run_phase_close_check(phase_num, resolved_repo_root, head_sha),
        )

    exit_code = max(exit_code, _run_destructive_archive_check(resolved_repo_root))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
