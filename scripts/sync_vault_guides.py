"""Sync tracked repo docs to their Obsidian vault counterparts (LIVE-03).

WHY: CLAUDE.md's LIVE-03 rule says every user-facing ``docs/*.md`` must have a
vault copy under ``20_Dev-Work/QUIRK/`` whose body matches the source. A
hand-maintained table of those pairs drifted repeatedly (it omitted the master
guide, the connector pages, ...). This script replaces the table with a
committed MAPPING + EXEMPT pair that is enforced against ``git ls-files`` at
run time, and cross-checked against each vault note's own ``source:`` key.
Folds todo 260928-claude-md-live03-table-missing-master-guide-row
(Phase 225 D-05 / D-06).

Run::

    .venv/bin/python -m scripts.sync_vault_guides --check
    .venv/bin/python -m scripts.sync_vault_guides --write

Exit codes:
    0  every mapped pair is body-equal and no tracked doc is unmapped
    1  drift (a vault body differs or is missing) or an unmapped tracked doc
    2  vault root absent or unreadable -- verdict unknown, never green

Vault note convention: ``---\\n`` + frontmatter lines + ``---\\n`` + ONE blank
line + the source bytes verbatim. A write preserves every frontmatter line
except ``updated:`` (and the note's own LF/CRLF frontmatter line endings),
writes only when the body differs, and never deletes.

Ownership guard (225-REVIEW CR-01): an EXISTING vault note is only ever
overwritten when its frontmatter parses and declares ``source:`` equal to the
MAPPING source. A note with no/unparseable frontmatter, no ``source:`` key, or
a different ``source:`` is reported as ``refused`` (exit 1) and left
byte-identical -- in both ``--check`` and ``--write`` modes.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import difflib
import fnmatch
import json
import os
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_VAULT_ROOT = pathlib.Path.home() / "vaults/Digs/20_Dev-Work/QUIRK"
FIX_CMD = "python -m scripts.sync_vault_guides --write"

_NO_COUNTERPART = "no vault counterpart; not created (Phase 225 D-04)"

# repo path -> vault target (relative to the QUIRK vault root)
MAPPING: dict[str, str] = {
    "docs/admin-guide.md": "Guides/Admin-Guide.md",
    "docs/architecture-distributed.md": "Guides/Architecture-Distributed.md",
    "docs/architecture.md": "Guides/Architecture.md",
    "docs/cbom-guide.md": "Guides/CBOM-Guide.md",
    "docs/chaos-lab.md": "Guides/Chaos-Lab.md",
    "docs/configuration.md": "Guides/Configuration.md",
    "docs/connector-field-reference.md": "Guides/Connector-Field-Reference.md",
    "docs/dead-code-candidates.md": "Guides/Dead-Code-Candidates.md",
    "docs/demo-runbook-2026-09-18.md": "Guides/Demo-Runbook-2026-09-18.md",
    "docs/getting-started.md": "Guides/Getting-Started.md",
    "docs/installation.md": "Guides/Installation.md",
    "docs/operators-guide.md": "Guides/Operators-Guide.md",
    "docs/quirk-master-guide.md": "Guides/Complete-Guide.md",
    "docs/quirk-overview.md": "Guides/QUIRK-Overview.md",
    "docs/release-process.md": "Guides/Release-Process.md",
    "docs/report-interpretation.md": "Guides/Report-Interpretation.md",
    "docs/test-triage-149.md": "Guides/Test-Triage-149.md",
    "docs/uat-coverage-gaps.md": "Guides/UAT-Coverage-Gaps.md",
    "docs/uat-coverage-reconciliation.md": "Guides/UAT-Coverage-Reconciliation.md",
    "docs/windows-packaging-spike.md": "Guides/Windows-Packaging-Spike.md",
    "docs/connectors/aws.md": "Guides/Connectors/AWS.md",
    "docs/connectors/azure.md": "Guides/Connectors/Azure.md",
    "docs/connectors/docker.md": "Guides/Connectors/Docker.md",
    "docs/connectors/git.md": "Guides/Connectors/Git.md",
    "docs/connectors/gcp.md": "Guides/Connectors/GCP.md",
    "docs/connectors/k8s.md": "Guides/Connectors/K8s.md",
    "docs/connectors/vault.md": "Guides/Connectors/Vault.md",
    "docs/connectors/db.md": "Guides/Connectors/DB.md",
    "docs/UAT-SERIES.md": "UAT-Series.md",
}

# exact tracked path -> written reason it has no vault counterpart
EXEMPT: dict[str, str] = {
    "README.md": _NO_COUNTERPART,
    "CHANGELOG.md": _NO_COUNTERPART,
    "CONTRIBUTING.md": _NO_COUNTERPART,
    "SECURITY.md": _NO_COUNTERPART,
    "CODE_OF_CONDUCT.md": _NO_COUNTERPART,
    "docs/intelligence-schema.md": _NO_COUNTERPART,
    "docs/deployment-cloud-console.md": _NO_COUNTERPART,
    "docs/upgrade-guide.md": _NO_COUNTERPART,
    "docs/error-codes.md": (
        "generated artifact (errors --dump-md); no vault counterpart"),
    "docs/cbom-classifier-coverage.md": (
        "internal coverage audit; no vault counterpart"),
    "docs/timeout-retry-audit.md": (
        "internal audit; no vault counterpart"),
}

EXEMPT_GLOBS: dict[str, str] = {
    "docs/brand/*.md": _NO_COUNTERPART,
    "docs/release-notes/*": "historical release notes; no vault counterpart",
    "docs/reviews/*": "historical review records; no vault counterpart",
    "docs/superpowers/*": "historical design specs/plans; no vault counterpart",
}


class VaultPathError(ValueError):
    """A vault target escapes the vault root (or is a symlink)."""


@dataclasses.dataclass
class PairResult:
    source: str
    target: str
    status: str  # in-sync | drift | missing | written | created | refused
    diff_lines: int = 0
    detail: str = ""


# --------------------------------------------------------------------------
# Pure helpers
# --------------------------------------------------------------------------

def note_newline(text: str) -> str | None:
    """Line ending of a note's opening ``---`` fence, or None if absent."""
    if text.startswith("---\r\n"):
        return "\r\n"
    if text.startswith("---\n"):
        return "\n"
    return None


def parse_note(text: str) -> tuple[list[str], str]:
    """Split a vault note into (frontmatter lines, body).

    Accepts LF or CRLF fences. Exactly one blank separator line after the
    closing ``---`` is stripped. A note without a leading ``---`` fence (or
    with an unterminated one) returns ([], text).
    """
    nl = note_newline(text)
    if nl is None:
        return [], text
    rest = text[3 + len(nl):]
    lines = rest.splitlines(keepends=True)
    for idx, line in enumerate(lines):
        if line.rstrip("\r\n") == "---":
            fm = [ln.rstrip("\r\n") for ln in lines[:idx]]
            body = "".join(lines[idx + 1:])
            for sep in ("\r\n", "\n"):
                if body.startswith(sep):
                    body = body[len(sep):]
                    break
            return fm, body
    return [], text


def render_note(fm_lines: list[str], body: str, today: str,
                newline: str = "\n") -> str:
    """Render a note: frontmatter verbatim except ``updated:``.

    ``newline`` is the frontmatter's own line ending, so a CRLF note keeps
    CRLF frontmatter on rewrite.
    """
    out = []
    for line in fm_lines:
        out.append(f"updated: {today}" if line.startswith("updated:") else line)
    nl = newline
    return "---" + nl + nl.join(out) + nl + "---" + nl + nl + body


def declared_source(fm_lines: list[str]) -> str | None:
    for line in fm_lines:
        if line.startswith("source:"):
            return line.split(":", 1)[1].strip()
    return None


def ownership_problem(fm_lines: list[str], source_rel: str) -> str | None:
    """Why an existing note must NOT be overwritten for ``source_rel``.

    None means the note provably is a sync of ``source_rel``.
    """
    if not fm_lines:
        return "no parseable frontmatter; not provably a sync of this source"
    src = declared_source(fm_lines)
    if src is None:
        return "frontmatter has no source: key; not provably a sync"
    if src != source_rel:
        return f"vault source: {src!r} but MAPPING says {source_rel!r}"
    return None


def new_note_frontmatter(source_rel: str, today: str) -> list[str]:
    return [
        "project: QU.I.R.K.",
        "type: guide",
        "status: active",
        f"source: {source_rel}",
        f"updated: {today}",
    ]


def diff_count(a: str, b: str) -> int:
    n = 0
    for line in difflib.unified_diff(
            a.splitlines(keepends=True), b.splitlines(keepends=True),
            lineterm=""):
        if line.startswith(("+++", "---")):
            continue
        if line.startswith(("+", "-")):
            n += 1
    return n


def resolve_target(vault_root: pathlib.Path, rel: str) -> pathlib.Path:
    """Resolve ``rel`` under ``vault_root`` or raise VaultPathError."""
    if os.path.isabs(rel):
        raise VaultPathError(f"absolute vault target refused: {rel!r}")
    root = vault_root.resolve()
    joined = root / rel
    if joined.is_symlink():
        raise VaultPathError(f"symlinked vault target refused: {joined}")
    resolved = joined.resolve()
    if not resolved.is_relative_to(root):
        raise VaultPathError(f"vault target escapes root: {rel!r} -> {resolved}")
    return resolved


def _read_text(path: pathlib.Path) -> str:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def _atomic_write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-sync")
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def write_pair(repo_root: pathlib.Path, vault_root: pathlib.Path,
               source_rel: str, target_rel: str, today: str,
               write: bool = True) -> PairResult:
    """Sync one pair. Writes only when the body differs; never deletes."""
    target = resolve_target(vault_root, target_rel)
    source = _read_text(repo_root / source_rel)
    if not target.exists():
        if write:
            fm = new_note_frontmatter(source_rel, today)
            _atomic_write(target, render_note(fm, source, today))
            return PairResult(source_rel, target_rel, "created",
                              diff_count("", source))
        return PairResult(source_rel, target_rel, "missing",
                          diff_count("", source))
    text = _read_text(target)
    fm, body = parse_note(text)
    n = diff_count(body, source)
    # CR-01: ownership is checked BEFORE any write decision. A note that is
    # not provably a sync of this source is never touched.
    problem = ownership_problem(fm, source_rel)
    if problem is not None:
        return PairResult(source_rel, target_rel, "refused", n, problem)
    if n == 0:
        return PairResult(source_rel, target_rel, "in-sync", 0)
    if not write:
        return PairResult(source_rel, target_rel, "drift", n)
    _atomic_write(target, render_note(fm, source, today,
                                      newline=note_newline(text) or "\n"))
    return PairResult(source_rel, target_rel, "written", n)


# --------------------------------------------------------------------------
# Enumeration and cross-check
# --------------------------------------------------------------------------

def tracked_markdown(repo_root: pathlib.Path = REPO_ROOT) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "-z"],
        capture_output=True, text=True, check=True).stdout
    files = [p for p in out.split("\0") if p]
    return sorted(
        p for p in files
        if p.endswith(".md") and (p.startswith("docs/") or "/" not in p))


def find_unmapped(tracked, mapping, exempt, exempt_globs) -> list[str]:
    bad = []
    for path in tracked:
        if path in mapping or path in exempt:
            continue
        if any(fnmatch.fnmatch(path, g) for g in exempt_globs):
            continue
        bad.append(path)
    return bad


def _source_of(path: pathlib.Path) -> str | None:
    try:
        fm, _ = parse_note(_read_text(path))
    except (OSError, UnicodeDecodeError):
        return None
    return declared_source(fm)


def scan_vault_sources(vault_root: pathlib.Path,
                       mapping: dict[str, str] | None = None
                       ) -> dict[str, str]:
    """vault-relative path -> declared ``source:`` value."""
    found: dict[str, str] = {}
    candidates = set((mapping or MAPPING).values())
    guides = vault_root / "Guides"
    if guides.is_dir():
        candidates.update(
            str(p.relative_to(vault_root)) for p in guides.rglob("*.md"))
    for rel in sorted(candidates):
        p = vault_root / rel
        if p.is_file():
            src = _source_of(p)
            if src is not None:
                found[rel] = src
    return found


def cross_check(mapping, vault_sources, tracked) -> list[str]:
    msgs = []
    inverse = {v: k for k, v in mapping.items()}
    for rel, src in vault_sources.items():
        if rel in inverse:
            if src != inverse[rel]:
                msgs.append(
                    f"MISMATCH {rel}: vault source: {src!r} but MAPPING "
                    f"says {inverse[rel]!r}")
        else:
            note = ("resolves to a tracked file" if src in tracked
                    else "resolves to no tracked file")
            msgs.append(f"info: unmapped vault note {rel} (source: {src!r} "
                        f"{note}); left untouched")
    return msgs


def plan_sync(repo_root, vault_root, tracked, today, write) -> list[PairResult]:
    results = []
    tracked_set = set(tracked)
    for src, tgt in MAPPING.items():
        if src not in tracked_set:
            continue
        results.append(write_pair(repo_root, vault_root, src, tgt, today,
                                  write=write))
    return results


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _report(results, unmapped, xcheck) -> None:
    for r in results:
        extra = f" REFUSED: {r.detail}; left untouched" if r.detail else ""
        print(f"{r.status:9s} {r.source} -> {r.target} "
              f"(diff lines: {r.diff_lines}){extra}", file=sys.stderr)
    for u in unmapped:
        print(f"UNMAPPED tracked doc: {u} (add to MAPPING or EXEMPT, "
              f"Phase 225 D-06)", file=sys.stderr)
    for m in xcheck:
        print(m, file=sys.stderr)


def main(argv=None, *, tracked=None, today=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    ap.add_argument("--vault-root", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root_str = (args.vault_root or os.environ.get("QUIRK_VAULT_ROOT")
                or str(DEFAULT_VAULT_ROOT))
    vault_root = pathlib.Path(root_str).expanduser()
    if not vault_root.is_dir() or not os.access(vault_root, os.R_OK):
        print(f"vault root absent or unreadable: {vault_root}",
              file=sys.stderr)
        return 2

    if tracked is None:
        tracked = tracked_markdown(REPO_ROOT)
    today = today or datetime.date.today().isoformat()

    # CR-01: the source: cross-check runs BEFORE any write; write_pair then
    # independently refuses every pair whose note is not provably its sync.
    xcheck = cross_check(MAPPING, scan_vault_sources(vault_root), set(tracked))
    unmapped = find_unmapped(tracked, MAPPING, EXEMPT, EXEMPT_GLOBS)
    results = plan_sync(REPO_ROOT, vault_root, tracked, today,
                        write=args.write)

    if args.write:
        # Re-run as a check so the exit code reflects the post-write state.
        results_after = plan_sync(REPO_ROOT, vault_root, tracked, today,
                                  write=False)
        _report(results, unmapped, xcheck)
        results = results_after
    else:
        _report(results, unmapped, xcheck)

    bad = [r for r in results if r.status in ("drift", "missing", "refused")]
    mismatches = [m for m in xcheck if m.startswith("MISMATCH")]
    code = 1 if (bad or unmapped or mismatches) else 0
    if any(r.status in ("drift", "missing") for r in bad) and not args.write:
        print(f"drift: fix with `{FIX_CMD}`", file=sys.stderr)
    if any(r.status == "refused" for r in bad):
        print("refused: a mapped vault note is not provably a sync of its "
              "source; repair it by hand (Phase 225 CR-01)", file=sys.stderr)
    if args.json:
        print(json.dumps({
            "exit": code,
            "pairs": [dataclasses.asdict(r) for r in results],
            "unmapped": unmapped,
            "cross_check": xcheck,
        }, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
