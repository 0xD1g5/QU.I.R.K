---
type: todo
created: 2026-10-12
source: Phase 224 gap closure F (DOC-04); ledger rows DCL-CONTRIB-0048..0059 and the new-text rows for CONTRIBUTING.md "Installing the pre-commit artifact gate"
priority: medium
area: .githooks/pre-commit, scripts/verify_phase_gates.py, CONTRIBUTING.md
status: pending
resolves_phase: null
---

# The pre-commit hook CONTRIBUTING.md used to tell contributors to install rejects every commit in a fresh clone

`CONTRIBUTING.md` told every contributor to run `git config core.hooksPath .githooks` and promised the hook was "cheap on
unrelated commits". Reproduced on a fresh `git clone` of this repo (the maintainers' phases directory is gitignored, so the
clone has none) with the hook installed and an unrelated one-line edit staged:

- With a Python that has PyYAML on PATH, `git commit` is **rejected** with a wall of
  `verify_phase_gates: Phase 172 (milestone v5.17) is marked Complete but has no live directory under ... — this is the
  ARCHIVE-MANIFEST.md incident shape`, one line per completed phase in the tracked `ROADMAP.md`. HEAD does not move. The
  destructive-archive check (ARTIFACT-04) compares the tracked roadmap's Complete phases against a directory that a public
  clone can never have, so it fires on every commit regardless of what is staged.
- With the system `python3` and no PyYAML (macOS system Python 3.9.6 here), the hook dies with
  `ModuleNotFoundError: No module named 'yaml'` and a traceback, which also blocks the commit. `.githooks/pre-commit:14`
  runs plain `python3`, not the project venv.

CI does not run the hook (`grep -c 'verify_phase_gates\|githooks' .github/workflows/*.yml` is 0 for every workflow), so
nothing in CI would have caught this.

`CONTRIBUTING.md` now says the hook is maintainer-only and that installing it in a fresh clone rejects every commit. That is
the honest text, but the product defect remains for any maintainer who works in a second clone, and for the claim itself:
a hook that is documented as optional should degrade to a no-op when its inputs are absent.

- [ ] In `scripts/verify_phase_gates.py`, make ARTIFACT-04 (and the other phase-close checks) a no-op when the phases
      directory does not exist at all, instead of treating every Complete phase as a missing directory.
- [ ] Make the hook exit 0 with one short stderr line (not a traceback) when PyYAML cannot be imported, or avoid the
      PyYAML import on the paths that do not need it.
- [ ] Add a regression test that runs the hook in a temp clone without the phases directory and asserts exit 0.
- [ ] After the fix, decide whether `CONTRIBUTING.md` can go back to recommending the hook to everyone (it should not,
      unless the checks are meaningful for contributors) and update the ledger rows if the page changes.

## Feasibility & Effort

**CONFIRMED** by a live reproduction in a scratch clone (commit rejected, HEAD unchanged; second run with
`/usr/bin/python3` shows the `ModuleNotFoundError`). Effort **S to M**: the guard is a few lines, the regression test needs a
temp-clone fixture (`tests/test_verify_phase_gates.py` already runs `git init` per its own comments). One unknown: whether
the maintainers want ARTIFACT-04 to stay strict when the phases directory is empty but the roadmap lists Complete phases
(the original archive-manifest incident); the guard should key on the directory being absent versus present-and-incomplete.
Spike not needed.
