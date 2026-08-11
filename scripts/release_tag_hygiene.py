#!/usr/bin/env python3
"""Scheduled guard: catch a release-like tag that never produced a successful
`release.yml` run (RELEASE-03).

Why this exists: three milestones (v5.9, v5.10.0, v5.11.0's Windows asset)
shipped with silent release-pipeline gaps. `v5.9` never matched
`release.yml`'s strict `v*.*.*` glob (it is a two-component tag) and
`v5.10.0` was created locally but never pushed to origin. Both incidents
produced *zero* Actions events — a push-time-only check has nothing to react
to. This script is invoked from a scheduled workflow
(`.github/workflows/release-tag-hygiene.yml`) so drift is caught on a
cadence, not only reactively.

Run modes:
    python scripts/release_tag_hygiene.py

Lives under scripts/ -- NOT imported by any runtime code.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
BASELINE_PATH = REPO_ROOT / ".github" / "tag-hygiene-baseline.txt"

# D-10: deliberately looser than release.yml's strict `v*.*.*` glob, so a
# malformed tag like `v5.9` (two components, no `v*.*.*` match) IS evaluated
# by this guard instead of silently skipped.
LOOSE_RELEASE_TAG_RE = re.compile(r"^v[0-9]")


def load_baseline(path: pathlib.Path) -> dict[str, str]:
    """Parse `.github/tag-hygiene-baseline.txt`.

    Format: `<tag><whitespace><reason>` per line. `#`-prefixed lines and
    blank lines are ignored. Returns {tag: reason}.
    """
    baseline: dict[str, str] = {}
    if not path.exists():
        return baseline
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        tag = parts[0]
        reason = parts[1].strip() if len(parts) > 1 else ""
        baseline[tag] = reason
    return baseline


def collect_backed_tags(
    run_records: list[dict],
    release_tag_names: list[str],
) -> set[str]:
    """Union of tags backed by a successful release.yml run OR an existing
    Release object.

    A run backs a tag when the tag equals its `headBranch` or appears in its
    `displayTitle` (containment). Pure: no subprocess, no network — every
    branch is unit-testable.
    """
    backed: set[str] = set()

    for record in run_records:
        head_branch = record.get("headBranch") or ""
        display_title = record.get("displayTitle") or ""
        if head_branch:
            backed.add(head_branch)
        # displayTitle containment fallback: a run record whose headBranch is
        # empty/mismatched can still back its tag if the tag name literally
        # appears in the display title (e.g. "v5.8.0 release").
        for candidate in _candidate_tags_in_text(display_title):
            backed.add(candidate)

    for tag_name in release_tag_names:
        if tag_name:
            backed.add(tag_name)

    return backed


def _candidate_tags_in_text(text: str) -> set[str]:
    """Extract release-like tag substrings from free text (displayTitle)."""
    if not text:
        return set()
    return {m.group(0) for m in re.finditer(r"v[0-9]+(?:\.[0-9A-Za-z]+)*", text)}


def evaluate_tags(
    tags: list[str],
    released_tags: set[str],
    baseline: dict[str, str],
) -> tuple[list[str], list[str], str]:
    """Cross-reference every release-like tag against `released_tags` and
    `baseline`.

    Returns (flagged, exempted, summary_markdown):
      flagged   = release-like tags with no successful release run and no
                  baseline entry
      exempted  = release-like tags with no successful release run that ARE
                  baselined
      summary_markdown = a `## Release Tag Hygiene` section listing OK /
                  EXEMPT / FLAGGED tags

    Pure: no subprocess, no network, no env reads.
    """
    release_like = [t for t in tags if LOOSE_RELEASE_TAG_RE.match(t)]

    ok: list[str] = []
    exempted: list[str] = []
    flagged: list[str] = []

    for tag in release_like:
        if tag in released_tags:
            ok.append(tag)
        elif tag in baseline:
            exempted.append(tag)
        else:
            flagged.append(tag)

    lines = ["## Release Tag Hygiene", ""]
    if ok:
        lines.append("### OK (backed by a successful release run)")
        for tag in ok:
            lines.append(f"- `{tag}`")
        lines.append("")
    if exempted:
        lines.append("### EXEMPT (baselined historical disposition)")
        for tag in exempted:
            reason = baseline.get(tag, "")
            lines.append(f"- `{tag}` — {reason}")
        lines.append("")
    if flagged:
        lines.append("### FLAGGED (no successful release run, no baseline entry)")
        for tag in flagged:
            lines.append(f"- `{tag}`")
        lines.append("")
    else:
        lines.append("No flagged tags.")
        lines.append("")

    summary_markdown = "\n".join(lines)
    return flagged, exempted, summary_markdown


def _run_gh_json(args: list[str]) -> list[dict]:
    """Run a `gh` CLI command and parse its JSON stdout. Hard error on
    non-zero exit or unparseable JSON — never treated as "everything is
    backed" (T-148-09)."""
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command {args!r} exited {result.returncode}: {result.stderr.strip()}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"command {args!r} produced unparseable JSON: {exc}"
        ) from exc


def main(argv: list[str] | None = None) -> int:
    import os

    try:
        tags_result = subprocess.run(
            ["git", "tag", "--list"],
            capture_output=True,
            text=True,
            check=False,
            cwd=REPO_ROOT,
        )
        if tags_result.returncode != 0:
            sys.stderr.write(
                f"git tag --list exited {tags_result.returncode}: "
                f"{tags_result.stderr.strip()}\n"
            )
            return 2
        tags = [t for t in tags_result.stdout.splitlines() if t.strip()]

        run_records = _run_gh_json(
            [
                "gh",
                "run",
                "list",
                "--workflow",
                "release.yml",
                "--status",
                "success",
                "--limit",
                "200",
                "--json",
                "displayTitle,headBranch",
            ]
        )
        release_records = _run_gh_json(
            ["gh", "release", "list", "--json", "tagName"]
        )
        release_tag_names = [r.get("tagName", "") for r in release_records]
    except RuntimeError as exc:
        sys.stderr.write(f"release_tag_hygiene: hard error: {exc}\n")
        return 2

    released_tags = collect_backed_tags(run_records, release_tag_names)
    baseline = load_baseline(BASELINE_PATH)

    flagged, _exempted, summary_markdown = evaluate_tags(tags, released_tags, baseline)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write(summary_markdown)
            fh.write("\n")
    else:
        print(summary_markdown)

    if flagged:
        sys.stderr.write(
            f"release_tag_hygiene: {len(flagged)} flagged tag(s): {flagged}\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
