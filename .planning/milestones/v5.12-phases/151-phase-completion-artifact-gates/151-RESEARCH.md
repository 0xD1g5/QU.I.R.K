# Phase 151: Phase-Completion Artifact Gates - Research

**Researched:** 2026-08-13
**Domain:** Local git-hook enforcement of GSD workflow artifact hygiene (QUIRK-repo-local, not GSD SDK)
**Confidence:** HIGH

## Summary

This phase is pure QUIRK-repo tooling: one new Python script (`scripts/verify_phase_gates.py`),
one new git hook wired to it, and a matching pytest test file — following the exact shape of the
existing `scripts/release_tag_hygiene.py` / `tests/test_release_tag_hygiene.py` precedent already
in this repo. No GSD SDK code is touched (confirmed out of scope by REQUIREMENTS.md's own
Out-of-Scope table).

The most important finding from this research is a **verified technical gap in D-04's literal
mechanism**: `.planning/` is gitignored (`.gitignore:67`), and `git check-ignore -v` confirms the
overwhelming majority of phase content is genuinely untracked — only 6 of 70 on-disk files under
`.planning/phases/` are currently tracked by git (`git ls-files .planning/phases/ | wc -l` = 6).
`git diff --cached` (or any staged-diff inspection) **cannot see a deletion of an untracked file**
— git has no record of it existing in the first place, so there is nothing to diff. A pre-commit
hook that "inspects the staged diff for deletions under `.planning/phases/*`" will therefore see
**nothing** for ~91% of the exact incident class it exists to prevent, because `phases.clear`
deleting untracked working-tree files never touches the git index at all. This is not a
theoretical concern — it is the literal mechanism of the actual incident: `phases.clear` ran a
filesystem delete, no commit was involved, and the loss was invisible to git until someone later
ran `git status` and got nothing back for the missing files (because git had never tracked them).

A second, related structural fact: **a git hook cannot make `phases.clear` itself "refuse to
run."** `phases.clear` is a `gsd-sdk` CLI/Node operation, not a `git commit`. Git hooks only fire
on git plumbing/porcelain operations (`pre-commit`, `pre-push`, etc.) — they have no interception
point over an arbitrary external program deleting files. Given D-04 explicitly rules out modifying
GSD tooling (the only place that could genuinely intercept the delete call before it executes),
the achievable guarantee within this phase's stated constraints is **not** "the delete never
happens" — it is "the *next* git commit after an unarchived deletion is blocked until the archive
gap is resolved." That is a materially real, valuable, and testable guarantee (it converts a
silent, permanent loss into a loud, blocking one at the very next commit), but the planner should
word ARTIFACT-04's task and its VERIFICATION evidence around that corrected claim, not the literal
"refuses to run" phrasing, to avoid writing an unverifiable success criterion. Recommended
detection mechanism (filesystem-state comparison, not diff-based): on every commit, compare the
set of phase directories currently on disk under `.planning/phases/` against the phases the
current milestone's `STATE.md` "Phase Map" table lists as `Complete`/tracked; if the on-disk
directory for a listed-complete phase is now absent or empty AND no
`.planning/milestones/v<X.Y>-phases/<same-dir>/` archive exists, block the commit. This works
regardless of what deleted the files and regardless of git-tracking status, because it reads
working-tree state directly rather than relying on git's diff machinery.

**Primary recommendation:** Build `scripts/verify_phase_gates.py` with two pure, unit-testable
functions (`check_phase_close()`, `check_destructive_archive()`), a thin `.githooks/pre-commit`
shell wrapper that calls it with `git diff --cached --name-only` output piped in, install via
`git config core.hooksPath .githooks` documented in `CONTRIBUTING.md`, and for
`check_destructive_archive()` specifically use working-tree directory-listing comparison (not
staged-diff deletion detection) since the latter is structurally blind to untracked-file loss.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Phase-close artifact presence check (ARTIFACT-01) | Local git hook (pre-commit) | Pure Python function (unit-testable) | Only point where `.planning/phases/` is guaranteed present on disk before the commit that would otherwise "hide" it; CI never sees `.planning/` (D-01, verified) |
| VALIDATION.md staleness check (ARTIFACT-02) | Local git hook (pre-commit) | Pure Python function | Same enforcement point; frontmatter is YAML (PyYAML already a project dependency, `pyproject.toml:13`) |
| UAT-SERIES.md entry requirement (ARTIFACT-03) | Local git hook (pre-commit) | Pure Python function | `docs/UAT-SERIES.md` IS git-tracked (unlike phase dirs) so this check could technically also run in CI, but is kept in the same hook per D-02's single-script decision |
| Destructive-deletion guard (ARTIFACT-04) | Local git hook (pre-commit, unconditional/every-commit) | Filesystem-state comparison (not git diff) | Untracked-file deletion is invisible to `git diff --cached`; only a working-tree snapshot comparison at commit time can catch it (see Summary) |
| Hook installation/bootstrap | `CONTRIBUTING.md` documentation + checked-in `.githooks/` dir | `git config core.hooksPath` | `.git/hooks/` itself is never committed; must document manual one-time setup per contributor (no existing pre-commit framework config found — verified) |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyYAML | 6.0.3 (installed; `pyproject.toml` pins `>=6.0`) | Parse VALIDATION.md/VERIFICATION.md YAML frontmatter | Already a project runtime dependency — `import yaml` confirmed working in this env `[VERIFIED: installed 6.0.3, pyproject.toml:13]` |
| Python stdlib `re` | 3.11+ (project floor) | Regex-based diff/status-line parsing for ROADMAP.md/STATE.md phase-close detection | No new dependency; matches `release_tag_hygiene.py`'s existing `re`-only approach |
| Python stdlib `subprocess` | 3.11+ | Invoke `git diff --cached --name-only` / `git diff --cached` from the hook script | Matches `release_tag_hygiene.py`'s `subprocess` usage pattern for `gh`/`git` calls |
| Python stdlib `pathlib` | 3.11+ | Filesystem walks of `.planning/phases/`, `.planning/milestones/` | Matches every existing `scripts/*.py` convention in this repo |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | existing project pin | Unit tests for the two check functions, loaded via `importlib.util.spec_from_file_location` since `scripts/` is not an importable package | Matches `tests/test_release_tag_hygiene.py`'s exact loading pattern — required because `scripts/` has no `__init__.py` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled `core.hooksPath` + checked-in `.githooks/` | `pre-commit` framework (`pre-commit-config.yaml`) | Framework adds a new Python dependency + `.pre-commit-config.yaml` + `pre-commit install` step for every contributor; this repo has zero existing `pre-commit` framework footprint (`find . -iname ".pre-commit*"` returned nothing) and one project-local script doesn't justify pulling in a general-purpose plugin framework. `core.hooksPath` is zero-dependency and matches the project's existing "single-purpose script, no new frameworks" bias. |
| Staged-diff deletion detection for ARTIFACT-04 | Working-tree directory-listing comparison against STATE.md's phase map | Staged-diff detection is the literally-worded D-04 mechanism but is **structurally blind** to the exact incident class it exists to prevent, per the verified untracked-file gap above — must be corrected at planning time |

**Installation:** No new packages required — PyYAML is already installed and pinned.

**Version verification:** `python3 -c "import yaml; print(yaml.__version__)"` → `6.0.3`, matching `pyproject.toml:13`'s `PyYAML>=6.0` pin. `[VERIFIED: local environment + pyproject.toml]`

## Package Legitimacy Audit

Not applicable — this phase installs zero new packages. PyYAML is an existing, already-audited
project dependency; no new `pip install` targets exist for this phase's scope.

## Architecture Patterns

### System Architecture Diagram

```
git commit (developer types `git commit`)
        │
        ▼
.githooks/pre-commit  (shell wrapper, installed via `git config core.hooksPath .githooks`)
        │
        ▼
python3 scripts/verify_phase_gates.py --staged-files <(git diff --cached --name-only)
        │
        ├─► check_phase_close()
        │     │
        │     ├─ parse staged diff to STATE.md / ROADMAP.md for a phase-status flip
        │     │  to Complete (regex on `- [ ] **Phase NNN` → `- [x] **Phase NNN`
        │     │  and/or STATE.md phase-map `Status` column flip to `Complete`)
        │     │
        │     ├─ if no flip detected → exit 0 (cheap no-op on unrelated commits)
        │     │
        │     └─ if flip detected → read .planning/phases/<N>-*/ from disk:
        │           ├─ ARTIFACT-01: <N>-VERIFICATION.md must exist
        │           ├─ ARTIFACT-02: <N>-VALIDATION.md frontmatter must have
        │           │   nyquist_compliant: true AND no per-task rows left ⬜ pending
        │           └─ ARTIFACT-03: if any <N>-NN-PLAN.md files_modified matches a
        │               user-facing path glob → docs/UAT-SERIES.md must contain a
        │               "## Series N: ... (Phase N — vX.Y)" heading
        │
        └─► check_destructive_archive()
              │
              ├─ list .planning/phases/*/ directories currently on disk
              ├─ cross-reference against STATE.md's phase-map "Complete" rows
              │  for phases belonging to a milestone whose ROADMAP has been
              │  archived (i.e. milestone.complete already ran)
              └─ if a Complete-listed phase's directory is absent/empty AND no
                 matching .planning/milestones/v<X.Y>-phases/<same-dir>/ exists
                 → BLOCK commit (nonzero exit, stderr message pointing at the gap)
        │
        ▼
exit 0 → commit proceeds   |   exit 1 → commit rejected, message printed
```

### Recommended Project Structure
```
scripts/
├── verify_phase_gates.py       # NEW — both check functions, pure/testable
├── release_tag_hygiene.py      # existing precedent, same shape
.githooks/
├── pre-commit                  # NEW — thin shell wrapper invoking the script
tests/
├── test_verify_phase_gates.py  # NEW — unit tests, importlib.util loading pattern
├── test_release_tag_hygiene.py # existing precedent to mirror
CONTRIBUTING.md                 # UPDATED — add "Installing the pre-commit hook" section
```

### Pattern 1: Non-package script loaded via `importlib.util` for testing
**What:** `scripts/` has no `__init__.py` and is not on `sys.path` by convention; tests load the
module directly from its file path.
**When to use:** Any test file for a `scripts/*.py` guard script in this repo.
**Example:**
```python
# Source: tests/test_release_tag_hygiene.py (existing repo file, lines 1-30)
import importlib.util
import pathlib

SCRIPT_PATH = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "verify_phase_gates.py"

def _load_module():
    spec = importlib.util.spec_from_file_location("verify_phase_gates", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
```

### Pattern 2: Pure decision functions, no subprocess/network in the tested core
**What:** `release_tag_hygiene.py`'s `evaluate_tags()` takes plain Python data (lists, dicts, sets)
and returns plain Python data — all `subprocess`/`gh` calls live in a separate `main()`/CLI-glue
layer that is NOT unit tested directly.
**When to use:** `check_phase_close()` and `check_destructive_archive()` should each be splittable
into a pure "given this parsed state, what's the verdict" function plus a thin
disk-reading/git-invoking wrapper, exactly like the existing precedent.
**Example:**
```python
# Source: scripts/release_tag_hygiene.py (existing repo file)
def evaluate_tags(
    tags: list[str],
    released_tags: set[str],
    baseline: dict[str, str],
) -> tuple[list[str], list[str], str]:
    """Pure: no subprocess, no network, no env reads."""
    ...
```

### Pattern 3: VALIDATION.md frontmatter shape (confirmed on-disk, ARTIFACT-02 basis)
**What:** Every `<N>-VALIDATION.md` in this repo has YAML frontmatter with a `nyquist_compliant:
true|false` boolean, and a body table of per-task rows using a `Status` column with literal
`⬜ pending` / `✅ green` / `❌ red` / `⚠️ flaky` glyphs (see legend line
`*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*`).
**When to use:** ARTIFACT-02's staleness check.
**Example (verified on-disk, `.planning/milestones/v5.11-phases/147-backlog-drain-lifecycle-ledger-tail/147-VALIDATION.md`):**
```yaml
---
phase: 147
slug: backlog-drain-lifecycle-ledger-tail
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-10
updated: 2026-08-11
---
```
Detection approach: `yaml.safe_load()` the frontmatter block (split on `---` delimiters, first
document), assert `nyquist_compliant is True`; separately regex/line-scan the per-task table body
for any row still containing the literal `⬜ pending` glyph in its Status column. Both conditions
must be clean to pass ARTIFACT-02.

### Pattern 4: docs/UAT-SERIES.md phase-entry heading shape (ARTIFACT-03 basis)
**What:** Every phase that shipped a UAT series has a heading of the exact form
`## Series <N>: <Name> (Phase <N> — v<X.Y>)`.
**Example (verified, `docs/UAT-SERIES.md:17228`):**
```
## Series 150: Test Suite Green Baseline + CI Gate (Phase 150 — v5.12)
```
Detection approach: `re.search(rf"^## Series \d+:.*\(Phase {phase_num}\b", uat_series_text,
re.MULTILINE)`.

### Pattern 5: ROADMAP.md / STATE.md phase-close diff signal (D-03 basis, confirmed via git log)
**What:** A phase-close commit flips two independent, both git-tracked, textual markers in the
same or a paired commit:
- `ROADMAP.md`: `- [ ] **Phase NNN: Name**` → `- [x] **Phase NNN: Name**` (verified via
  `git show b09c9bc -- .planning/ROADMAP.md`, the actual Phase 150 close commit)
- `STATE.md`: phase-map table row's trailing `Status` cell text changes to contain `Complete`
  (verified via `git show b09c9bc -- .planning/STATE.md`, same commit — cell went from
  `Not started` to a `Complete (...)` string)

**Example (real diff hunk, Phase 150 close, commit `b09c9bc`):**
```diff
-- [ ] **Phase 150: Test Suite Green Baseline + CI Gate** — `pytest -q` green on a clean
+- [x] **Phase 150: Test Suite Green Baseline + CI Gate** — `pytest -q` green on a clean
       environment, held by a CI gate that fails the build on any new failure
```
Detection approach: `git diff --cached -- .planning/ROADMAP.md` and grep the added-lines (`^\+`)
for `^\+- \[x\] \*\*Phase (\d+):`; capture the phase number as `N`. This is the trigger that gates
`check_phase_close()`'s expensive disk-reading path (D-03's "cheap on unrelated commits"
requirement).

### Anti-Patterns to Avoid
- **Trusting `git diff --cached` for `.planning/phases/*` deletion detection:** Verified structurally
  broken for the majority of files (91% untracked). Use working-tree directory-listing comparison
  instead (Pattern in Common Pitfalls below).
- **Parsing VALIDATION.md/VERIFICATION.md with a full markdown AST library:** Existing repo
  convention is targeted YAML-frontmatter-split + line/regex scan (see `release_tag_hygiene.py`,
  `tests/skip_registry.py`'s AST-only-for-Python-not-markdown approach). Don't introduce a new
  markdown-parsing dependency for two small, structurally simple documents.
- **Making the hook block ALL commits with an expensive full-repo scan:** D-03 explicitly requires
  the phase-close checks to be diff-gated and cheap on unrelated commits; only
  `check_destructive_archive()`'s directory-listing comparison needs to run unconditionally, and
  that comparison itself is cheap (a directory listing + a table read, no subprocess/network).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML frontmatter parsing | A hand-rolled `---`-delimiter + line-split parser | `yaml.safe_load()` on the extracted frontmatter block | PyYAML is already a pinned dependency (`pyproject.toml:13`); hand-rolling risks silent misparse on edge cases (multi-line strings, nested keys) that a real YAML parser handles correctly |
| Git plumbing invocation | Raw `os.popen` / shell string interpolation | `subprocess.run([...], capture_output=True, text=True)` with a list-form argv | Matches `release_tag_hygiene.py`'s existing subprocess pattern; avoids shell-injection surface entirely |
| Hook framework | A custom multi-hook dispatcher system | `git config core.hooksPath .githooks` + one `pre-commit` file | Single hook is enough for this phase's scope; a dispatcher framework is unjustified complexity for one script |

**Key insight:** Every piece of this phase already has a near-identical implemented precedent
somewhere in the repo (`release_tag_hygiene.py` for script shape + testing pattern,
`tests/skip_registry.py` for the "meta-gate over conventions" concept, `VALIDATION.md`'s own
frontmatter for the YAML shape). The job is assembly and correct wiring, not invention — except
for the working-tree-comparison correction to D-04's literal mechanism documented above.

## Common Pitfalls

### Pitfall 1: Staged-diff deletion detection silently no-ops on untracked files (ARTIFACT-04)
**What goes wrong:** A hook that runs `git diff --cached --diff-filter=D -- .planning/phases/`
(or equivalent) will report **zero** deletions when `phases.clear` (or `rm -rf`) removes untracked
phase files, because git has no record of them to diff against. The hook appears to work in
testing (if the test fixture happens to `git add` the phase files first) but is blind in the real
incident scenario.
**Why it happens:** `.planning/` is gitignored; only 6/70 files under `.planning/phases/` are
currently tracked (`git ls-files .planning/phases/ | wc -l`).
**How to avoid:** Detect via working-tree state comparison, not git diff: on every commit,
enumerate `.planning/phases/*/` directories on disk, cross-reference against phases the current
milestone's `STATE.md` phase-map table marks `Complete` (i.e., phases that should still have a
live working directory or, if the milestone has since closed, an archived counterpart under
`.planning/milestones/v<X.Y>-phases/`), and block if a supposedly-complete phase's content is
gone from both locations.
**Warning signs:** A test suite for `check_destructive_archive()` that only exercises the
`git add`+`git rm`+commit path will pass while missing the real incident shape entirely — write at
least one test that creates an untracked file, deletes it via plain `os.remove` (no `git rm`), and
confirms the hook still catches it via directory/count comparison, not diff inspection.

### Pitfall 2: Git hooks cannot intercept non-git destructive operations (ARTIFACT-04 scope)
**What goes wrong:** Planning ARTIFACT-04's task as "make `phases.clear` refuse to run" and then
being unable to verify it, because a `pre-commit` hook only fires on `git commit` — it has zero
visibility into (and zero ability to block) a `gsd-sdk query phases.clear --confirm` invocation
itself, which is a plain filesystem delete with no git operation involved.
**Why it happens:** Confusing "the destructive operation" (a `gsd-sdk`/Node CLI delete) with "the
commit that follows it." These are different events; only the second is git-hook-addressable.
**How to avoid:** Scope ARTIFACT-04's task and its VERIFICATION.md language around "the next
commit after an unarchived destructive deletion is blocked until the gap is resolved" — a real,
testable, valuable guarantee — rather than "the delete never executes," which this phase's
locked constraints (no GSD tooling modification) cannot achieve.
**Warning signs:** A VERIFICATION.md criterion phrased as "phases.clear refuses to run" that can
only be demonstrated by manually invoking the Python check function directly (bypassing
`phases.clear` entirely) rather than by an actual `phases.clear` invocation failing — that gap is
the tell that the criterion's literal wording doesn't match what was built.

### Pitfall 3: Hook installation has no automatic enforcement — contributors can simply not install it
**What goes wrong:** `core.hooksPath` is a per-clone git config setting; a contributor who never
runs the one-time `git config core.hooksPath .githooks` setup command gets **zero** enforcement,
silently. The gate provides no CI backstop (by design — CI can't see `.planning/`), so a
contributor who skips setup can still make a phase-close commit that violates ARTIFACT-01/02/03.
**Why it happens:** This is architecturally inherent to D-01's finding, not a coding bug — accepted
scope, but must be documented, not silently assumed to be universal.
**How to avoid:** Document the one-time setup prominently in `CONTRIBUTING.md` (near the top, not
buried), and consider an optional low-cost self-check: a `Makefile`/`scripts/` target or a comment
in `STATE.md`'s own bootstrapping docs that verifies `git config core.hooksPath` is set and warns
if not.
**Warning signs:** None automatically detectable from inside the hook itself (a hook that isn't
installed can't warn you it isn't installed) — this must be a documentation/process mitigation,
not a code one.

### Pitfall 4: VALIDATION.md "pending" detection false-positiving on the legend line
**What goes wrong:** Every VALIDATION.md includes a literal legend line
`*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*` that contains the `⬜ pending` glyph even in a
fully-passing file — a naive `"⬜ pending" in text` substring check will always fire.
**Why it happens:** The glyph legend documents the vocabulary; it isn't itself a pending row.
**How to avoid:** Scope the pending-glyph search to actual table rows (lines starting with `|` and
matching the per-task table's column structure), excluding lines starting with `*Status:` or
matching the legend pattern, and/or search for `⬜ pending` immediately following a `|` table-cell
delimiter rather than anywhere in the file.
**Warning signs:** A hook that blocks every single phase close because the legend line always
matches — write a unit test against a real, fully-green VALIDATION.md fixture (e.g. the actual
`147-VALIDATION.md` content) to catch this before it ships.

## Code Examples

### Loading a `scripts/*.py` module for testing (existing repo pattern)
```python
# Source: tests/test_release_tag_hygiene.py (verified in this repo)
import importlib.util
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "verify_phase_gates.py"

def _load_module():
    spec = importlib.util.spec_from_file_location("verify_phase_gates", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
```

### Detecting staged git-tracked-file deletions (works only for tracked files — use for
verifying the diff-detection PATH of `check_phase_close`'s trigger logic, NOT for ARTIFACT-04)
```bash
# Source: git plumbing, verified in this repo (git 2.50.1)
git diff --cached --name-only --diff-filter=D -- '.planning/phases/*'
# Returns nothing for untracked-file deletions — confirmed empirically in this repo
# where only 6/70 .planning/phases/ files are tracked.
```

### Working-tree directory-listing comparison (recommended ARTIFACT-04 mechanism)
```python
# New pattern for this phase — no direct existing precedent, composed from
# pathlib idioms already used throughout scripts/*.py
import pathlib

def phase_dirs_on_disk(phases_root: pathlib.Path) -> set[str]:
    """Non-empty phase directories currently present under .planning/phases/."""
    if not phases_root.exists():
        return set()
    return {
        p.name for p in phases_root.iterdir()
        if p.is_dir() and any(p.iterdir())
    }

def archived_phase_dirs(milestones_root: pathlib.Path, milestone_tag: str) -> set[str]:
    archive_dir = milestones_root / f"{milestone_tag}-phases"
    if not archive_dir.exists():
        return set()
    return {p.name for p in archive_dir.iterdir() if p.is_dir()}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| CI-based meta-gate (`tests/test_skip_registry.py` pattern) proposed for ARTIFACT-01..03 | Local pre-commit git hook | Ruled out during `/gsd:discuss-phase 151` (D-01) after confirming `.gitignore:67` strips `.planning/` from every CI checkout | CI cannot enforce phase-artifact hygiene at all for this repo; must be a local, opt-in-by-setup hook instead — a real capability regression vs. a CI-enforced gate, documented as an accepted constraint (Pitfall 3) |

**Deprecated/outdated:** N/A — this is new infrastructure, not a replacement for an existing
mechanism.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The "files_modified path heuristic" glob list in D-05 (`src/dashboard/**`, `quirk/cli/**`, report-renderer files, new scanner/detector modules) is complete enough to catch all genuinely user-facing phases without excessive false positives/negatives | ARTIFACT-03 detection design | A too-narrow glob list lets a user-facing phase close without a UAT-SERIES.md entry (repeats Phase 144); a too-broad list forces UAT entries on internal-only phases, adding friction. Verified `quirk/cli/` exists on disk as the correct path; the report-renderer and "new scanner/detector modules" globs are less precisely specified and should be refined during planning against a sample of past `files_modified` lists (e.g. `150-*-PLAN.md`, `141-*-PLAN.md`) |
| A2 | No contributor currently has `core.hooksPath` set to anything other than the git default (`.git/hooks`) | Hook installation mechanism | Verified via `git config core.hooksPath` returning the default `.git/hooks` path in this working copy — low risk, but only checked in this one clone, not across all contributor machines |

**If this table is empty:** N/A — see rows above.

## Open Questions (RESOLVED)

1. **Should `check_destructive_archive()` run on every single commit, or only when
   `.planning/phases/` or `.planning/milestones/` paths are touched?**
   - What we know: D-03 explicitly scopes ONLY the phase-close checks (ARTIFACT-01/02/03) to be
     diff-gated for cheapness; D-04 doesn't state the same constraint for ARTIFACT-04.
   - What's unclear: Whether running the directory-listing comparison on every commit is cheap
     enough to be acceptable (it should be — a few `pathlib.iterdir()` calls, no subprocess), or
     whether it should also be gated somehow.
   - Recommendation: Run it unconditionally but cheaply (no git subprocess needed, just
     filesystem reads) on every commit — the whole point (Pitfall 1/2) is that it must catch
     damage that happened *between* commits with no git-visible trigger event to gate on.

2. **How should the phase-number extraction handle multi-digit vs. sub-phase numbering
   (e.g. `64.1-audit-residual-blockers`, seen in the codebase)?**
   - What we know: STATE.md/ROADMAP.md history shows at least one gap-closure sub-phase
     (`64.1`) with a decimal phase number.
   - What's unclear: Whether the phase-close regex (`\*\*Phase (\d+):`) needs a `(\d+(?:\.\d+)?)`
     variant to correctly match sub-phase closes, or whether sub-phases are out of scope for this
     gate.
   - Recommendation: Use a `\d+(?:\.\d+)?` capture group defensively; write a unit test against a
     literal `64.1` fixture line.

3. **Does `check_phase_close()` need to handle a phase-close commit that bundles STATE.md AND
   ROADMAP.md changes with unrelated other file changes in the same commit (the common case,
   confirmed via `git show b09c9bc`)?**
   - What we know: The real Phase 150 close commit touched `REQUIREMENTS.md`, `ROADMAP.md`, and
     `STATE.md` together in one commit — the diff-gate only needs to fire on the presence of the
     Phase-flip pattern in the staged diff, not on the commit being "pure."
   - What's unclear: None — this confirms the diff-gate design is correct as scoped.
   - Recommendation: No change needed; documented for planner confidence.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PyYAML | ARTIFACT-02 frontmatter parsing | ✓ | 6.0.3 | — |
| git | Hook mechanism itself | ✓ | 2.50.1 | — |
| Python 3.11+ | Script runtime | ✓ (project floor) | — | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing project standard) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| Quick run command | `pytest tests/test_verify_phase_gates.py -x` |
| Full suite command | `pytest -q -m ""` (per `CONTRIBUTING.md`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARTIFACT-01 | `check_phase_close()` blocks when `<N>-VERIFICATION.md` missing | unit | `pytest tests/test_verify_phase_gates.py -x -k verification_missing` | ❌ Wave 0 |
| ARTIFACT-02 | `check_phase_close()` blocks on `nyquist_compliant: false` and on any `⬜ pending` table row (excluding the legend line — Pitfall 4) | unit | `pytest tests/test_verify_phase_gates.py -x -k validation_stale` | ❌ Wave 0 |
| ARTIFACT-03 | `check_phase_close()` blocks when a files_modified path matches the user-facing glob set and no matching `## Series N` heading exists in `docs/UAT-SERIES.md` | unit | `pytest tests/test_verify_phase_gates.py -x -k uat_series` | ❌ Wave 0 |
| ARTIFACT-04 | `check_destructive_archive()` blocks when a `STATE.md`-Complete phase's on-disk directory is empty/absent with no matching milestone archive — including the untracked-file case (Pitfall 1) | unit | `pytest tests/test_verify_phase_gates.py -x -k destructive_archive` | ❌ Wave 0 |
| All | End-to-end hook wiring: `.githooks/pre-commit` correctly invokes the script and respects its exit code | integration (optional, can be a subprocess-based test invoking the hook script directly against a temp git repo fixture) | `pytest tests/test_verify_phase_gates.py -x -k hook_integration` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_verify_phase_gates.py -x`
- **Per wave merge:** `pytest -q -m ""` (full suite, per CONTRIBUTING.md)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_verify_phase_gates.py` — new file, covers all four requirements
- [ ] Fixture VALIDATION.md/VERIFICATION.md/UAT-SERIES.md snippets (can reuse the real
  `147-VALIDATION.md` and `docs/UAT-SERIES.md` Series 150 heading as literal test fixtures —
  both already exist on disk and are quoted in this research)
- [ ] `.githooks/pre-commit` — new file, no existing hook infrastructure to extend (confirmed:
  `.git/hooks/` contains only `.sample` files, no `.githooks/` directory exists)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — local dev-tooling script, no auth surface |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | Yes (minor) | The hook parses file content it reads from disk (frontmatter, markdown) — use `yaml.safe_load()` (never `yaml.load()` without a `Loader`) to avoid arbitrary-object deserialization, consistent with the project's existing YAML usage elsewhere |
| V6 Cryptography | No | N/A |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Shell injection via unsanitized filenames/branch names passed to `subprocess` | Tampering | Use list-form `subprocess.run([...])` argv, never `shell=True` with interpolated strings — matches `release_tag_hygiene.py`'s existing pattern |
| YAML deserialization of untrusted content executing arbitrary Python objects | Tampering | `yaml.safe_load()` only, never bare `yaml.load()` |
| Hook bypass via `git commit --no-verify` | Repudiation | Out of scope to prevent (git's own escape hatch by design) — document in `CONTRIBUTING.md` that `--no-verify` bypasses this local safety net entirely, so contributors understand the guarantee's real boundary |

## Sources

### Primary (HIGH confidence)
- Local repo inspection: `git check-ignore -v`, `git ls-files .planning/phases/`,
  `find .planning/phases -type f | wc -l` — verified untracked-file gap directly, this session
- `scripts/release_tag_hygiene.py`, `tests/test_release_tag_hygiene.py` — read in full, existing
  repo precedent for script shape and test-loading pattern
- `.planning/milestones/v5.11-phases/ARCHIVE-MANIFEST.md` — the exact incident record, read in full
- `.planning/milestones/v5.11-phases/145-liveness-pre-pass/145-VERIFICATION.md`,
  `.planning/milestones/v5.11-phases/147-backlog-drain-lifecycle-ledger-tail/147-VALIDATION.md` —
  real on-disk artifact shapes, read in full
- `docs/UAT-SERIES.md` (grep for `## Series` headings) — real phase-entry heading format
- `git show b09c9bc` — the actual Phase 150 phase-close commit diff against `ROADMAP.md` and
  `STATE.md`, confirming D-03's diff-detection basis empirically
- `CONTRIBUTING.md` — read in full, confirmed no existing hook-setup instructions
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md` — read in full per task instructions

### Secondary (MEDIUM confidence)
- None used — all findings in this research were directly verified against this repository's own
  files and git history rather than external/general git-hook documentation, since the phase's
  entire scope is repo-internal conventions.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, PyYAML version confirmed installed and pinned
- Architecture: HIGH — every pattern quoted is copied from real, currently-committed files in this
  repository, not external documentation
- Pitfalls: HIGH — the untracked-file gap (Pitfall 1) and the hook-scope gap (Pitfall 2) are both
  derived from direct `git check-ignore`/`git ls-files` verification in this session, not inference

**Research date:** 2026-08-13
**Valid until:** No fixed expiry — this research is tied to this repo's own committed conventions
(`.gitignore`, `release_tag_hygiene.py` shape, VALIDATION.md format) rather than an external,
time-sensitive ecosystem. Re-verify only if any of those source files change materially before
planning begins.
