"""Scanner build identity, for stamping into scan output.

WHY THIS EXISTS
---------------
On 2026-09-14 a chaos-lab scan reported a confident **91/100**. The same
evidence scores **15/100** under the scoring model that had been on `main`
since earlier that day. The scan exited 0, wrote 11 report artifacts, and
warned about nothing: `lab.sh up` runs `compose up -d` with no `--build`, so
it had silently reused a prober image built before the scoring change.

Nothing in the output named the scanner build, so there was no way to tell a
v2 score from a v3 score by looking at the result -- only the magnitude
betrayed it, and only to someone who already knew both numbers. `Platform
version` was no help: it read `5.21.0` in both cases, because `pyproject.toml`
has not bumped since the PyPI release. A released version string identifies
the release, not the code actually running.

`SCORING_VERSION` is the decisive datum -- it is a Python constant, so it is
always knowable, and printing it alone would have caught this immediately.
The commit SHA is the corroborating one, and is knowable only sometimes; this
module is explicit about which case it is in rather than guessing.

NO SUBPROCESS
-------------
The SHA is read from `.git` as plain files, never via `git rev-parse`. A scan
has no reason to fork, and this repo has a standing macOS hazard where any
default-`close_fds` spawn reintroduces a fork()-after-Network.framework
SIGSEGV (see tests/test_cli_helper_usage.py). Reading two small files avoids
the question entirely and works when `git` is not installed at all -- which is
the norm inside the slim container images this stamp most needs to describe.
"""
from __future__ import annotations

import os
from pathlib import Path

#: Baked into container images at build time (see sensor.Dockerfile). Set this
#: when there is no `.git` to read, which is the usual case for a built image.
BUILD_SHA_ENV = "QUIRK_BUILD_SHA"

UNKNOWN = "unknown"

_SHA_LEN = 12


def _read_sha_from_git_dir(start: Path) -> str | None:
    """Resolve HEAD to a commit SHA by reading `.git`, or None.

    Handles the three on-disk shapes that occur in practice: a detached HEAD
    (HEAD holds the SHA directly), a normal branch (HEAD points at a ref file),
    and a packed ref (the loose ref file is absent and the SHA lives in
    `packed-refs`, which is what a fresh clone looks like before any commit).
    """
    for parent in [start, *start.parents]:
        git = parent / ".git"
        if git.is_file():
            # A worktree or submodule: `.git` is a file holding `gitdir: <path>`.
            try:
                pointer = git.read_text(encoding="utf-8").strip()
            except OSError:
                return None
            if not pointer.startswith("gitdir:"):
                return None
            git = Path(pointer.split(":", 1)[1].strip())
            if not git.is_absolute():
                git = (parent / git).resolve()
        elif not git.is_dir():
            continue

        try:
            head = (git / "HEAD").read_text(encoding="utf-8").strip()
        except OSError:
            return None

        if not head.startswith("ref:"):
            return head or None  # detached HEAD

        ref = head.split(":", 1)[1].strip()
        try:
            return (git / ref).read_text(encoding="utf-8").strip() or None
        except OSError:
            pass

        try:
            packed = (git / "packed-refs").read_text(encoding="utf-8")
        except OSError:
            return None
        for line in packed.splitlines():
            if line.startswith(("#", "^")):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2 and parts[1].strip() == ref:
                return parts[0].strip()
        return None
    return None


def scanner_build_stamp() -> str:
    """Return a short identifier for the running scanner build.

    Precedence, most to least authoritative about what is actually installed:

    1. ``$QUIRK_BUILD_SHA`` -- baked in at image build time. Preferred inside a
       container, where any `.git` present describes the build *context* rather
       than the installed code.
    2. ``.git`` on disk -- correct for an editable/dev checkout.
    3. ``"unknown"`` -- an installed wheel with neither. Stated plainly rather
       than substituting the package version, which is precisely the
       substitution that made the stale-prober scan unreadable.
    """
    env = os.environ.get(BUILD_SHA_ENV, "").strip()
    if env:
        return env[:_SHA_LEN]

    sha = _read_sha_from_git_dir(Path(__file__).resolve().parent)
    if sha:
        return sha[:_SHA_LEN]

    return UNKNOWN
