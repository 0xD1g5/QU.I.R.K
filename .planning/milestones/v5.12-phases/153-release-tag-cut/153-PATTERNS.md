# Phase 153: Release Tag Cut - Pattern Map

**Mapped:** 2026-08-13
**Files analyzed:** 9 (2 canonical edits + 3 doc/version-literal edits + 4 phase-close artifacts)
**Analogs found:** 9 / 9

This phase creates almost no new application code — it is an operational sequencing phase
(push, dry-run, version bump, human-gated tag, post-tag verification, phase close). Every file
touched already has a direct, recent analog from the v5.11.0 cut (commit `4b73940`,
2026-08-11) or from Phase 150/151's close-out artifacts. Follow those literally; do not invent
new formats.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `pyproject.toml` (`[project.version]`) | config | batch (one-line literal edit) | Same file, prior bump `4b73940` (`5.10.0` → `5.11.0`) | exact |
| `README.md` (line 7 heading) | config/doc | batch | Same file, prior bump `4b73940` | exact |
| `docs/UAT-SERIES.md` (header + UAT-1-02 pass criteria/Notes) | doc | batch | Same file, prior bump `4b73940`; also Phase 151's own `## Series 151: ...` entry for the *new-series* shape | exact |
| `docs/UAT-SERIES.md` (new `## Series 153: ...` section) | doc | batch | `## Series 151: Phase-Completion Artifact Gates (Phase 151 — v5.12)` (`docs/UAT-SERIES.md:17309`) | exact |
| `CHANGELOG.md` (towncrier-built section, or hand-written milestone entry) | doc | batch | `docs/release-process.md` Step 4 (towncrier invocation); `CHANGELOG.md`'s existing `## [5.8.0]` entry as the last real towncrier-built section | role-match (towncrier hasn't run since 5.8.0; last 3 milestones used `docs/release-notes/*.md` instead — see Open Question A1 in RESEARCH.md) |
| `docs/release-notes/5.12.0.md` (recommended, not mandatory) | doc | batch | `docs/release-notes/5.11.0.md` (full file read below) | exact |
| `.planning/phases/153-release-tag-cut/153-VERIFICATION.md` | doc (phase-close artifact) | event-driven (produced by verifier at phase close) | `.planning/phases/150-*/150-VERIFICATION.md` (live-CI-evidence style) and `.planning/phases/151-*/151-VERIFICATION.md` (frontmatter + criteria-table shape) | exact |
| `.planning/phases/153-release-tag-cut/153-VALIDATION.md` | doc (phase-close artifact) | event-driven | `.planning/phases/151-*/151-VALIDATION.md` | exact |
| Obsidian phase note `Phase-153-Release-Tag-Cut.md` | doc | event-driven | Existing `Phase-151-...md` pattern per CLAUDE.md "Mandatory Phase Completion Steps" §1 | exact |

There are no controller/component/service/model/middleware files in this phase — everything is
either a config literal, a markdown doc, or an operational git/gh command sequence. No "No
Analog Found" files exist.

## Pattern Assignments

### `pyproject.toml` `[project.version]`

**Analog:** same file, commit `4b73940` (2026-08-11, `5.10.0` → `5.11.0`)

**Exact diff to replicate** (only this one line changes in the file — this is the sole
canonical edit; every other version surface derives from it via `importlib.metadata`/
`tomllib`, per `tests/test_version.py`):
```diff
 [project]
 name = "quirk-scanner"
-version = "5.10.0"
+version = "5.11.0"
```
For this phase: `version = "5.11.0"` → `version = "5.12.0"`.

**Do not** touch `quirk/__init__.py`, `quirk/cbom/builder.py::PLATFORM_VERSION`,
`quirk/reports/writer.py::PLATFORM_VERSION`, or `quirk/config.py::IntelligenceCfg` — all four
derive automatically and are proven by `tests/test_version.py`.

---

### `README.md` (line 7 heading)

**Analog:** same file, commit `4b73940`

**Exact diff shape:**
```diff
-# QU.I.R.K. — v5.10.0
+# QU.I.R.K. — v5.11.0
```
For this phase: `v5.11.0` → `v5.12.0`.

---

### `docs/UAT-SERIES.md` — header + UAT-1-02 literal edits

**Analog:** same file, commit `4b73940`

**Header pattern** (top of file):
```diff
-**Version:** 5.10.0
-**Last Updated:** 2026-08-11 (Phase 147 wrap — ...)
+**Version:** 5.11.0
+**Last Updated:** 2026-08-11 (v5.11 milestone close — **Series 144 backfilled**: ...)
```
For this phase, prepend a new "v5.12 milestone close / Phase 153 tag cut" clause to the
`**Last Updated:**` line (don't delete prior milestone-close prose — the file accretes a running
narrative, confirmed by the diff pattern above which prepends new context and keeps
"Earlier: ...").

**UAT-1-02 pass-criteria pattern** (`docs/UAT-SERIES.md` ~line 211-227):
```diff
 **Pass Criteria:**
-- Output matches format: `QU.I.R.K. v5.10.0`
+- Output matches format: `QU.I.R.K. v5.11.0`
 - Exit code 0

 **Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
 **Date:**   **Tester:**
-**Notes:** Version bumped to v5.10.0 at v5.10 milestone close (pyproject.toml sole SoT; importlib.metadata derives it). Re-test required against v5.10.0 install.
+**Notes:** Version bumped to v5.11.0 at v5.11 milestone close (pyproject.toml sole SoT; importlib.metadata derives it). Re-test required against v5.11.0 install.
```
For this phase: replace all `5.11.0`/`v5.11.0` occurrences in this block with `5.12.0`/`v5.12.0`.

---

### `docs/UAT-SERIES.md` — new `## Series 153: ...` section

**Analog:** `## Series 151: Phase-Completion Artifact Gates (Phase 151 — v5.12)` (in
`docs/UAT-SERIES.md`, appended near line 17309 by Phase 151)

**Structure to copy** (per-UAT-entry shape — this is the load-bearing template every Series
entry in this file follows, confirmed identically in the 144/151 series additions):
```markdown
## Series 153: Release Tag Cut (Phase 153 — v5.12)

**Last Updated:** <date>

### UAT-153-01: <scenario name> (RELEASE-01) — Human (live) / Automated

**What to test:** <one paragraph>

**Steps:**
1. ...

**Pass criteria:**
- ...

**Automated gate:** <pytest command, or "N/A — inherently a live end-to-end checkpoint" (this
exact phrase is the established convention for live-CI-only proof, taken verbatim from
UAT-144-03)>

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:**   **Tester:**
**Notes:** <requirement IDs, context>

---
```
Given RELEASE-01's nature (a real tagged CI run, not a unit test — see RESEARCH.md's
Validation Architecture table), this phase's Series 153 entry should mirror **UAT-144-03**'s
"Human (live)" shape exactly (real command outputs cited as evidence, `Automated gate: N/A —
inherently a live end-to-end checkpoint`) rather than the automated-pytest shape used by
UAT-144-01/02 or UAT-151-01/02.

---

### `docs/release-notes/5.12.0.md` (recommended per RESEARCH.md Open Question 2)

**Analog:** `docs/release-notes/5.11.0.md` (full file, 78 lines)

**Structure to copy exactly:**
- H1 title: `# QU.I.R.K. <version> — <milestone theme>`
- `**Released:**` / `**Milestone:**` metadata lines
- `## What's New` — one bullet per phase in the milestone, `**<Feature name> (Phase NNN):**`
  prefix
- `## Known Issues` — only if there is a real disposition to record (5.11.0's file used this
  section for the PyPI-only/no-Windows-asset gap; for 5.12.0 this section should likely be
  **absent or state "None"**, since RELEASE-01's entire point is that the Windows asset issue
  from 5.11.0 is now fixed — a `docs/release-notes/5.12.0.md` that omits "Known Issues" or
  states none is itself evidence RELEASE-01 succeeded)
- `## Upgrade Guidance` — `pip install --upgrade quirk-scanner` + breaking-change note
- `## See Also` — links to `CHANGELOG.md`, prior release notes file, `docs/release-process.md`,
  `docs/UAT-SERIES.md`
- Closing italic milestone-close attribution line

---

### `.planning/phases/153-release-tag-cut/153-VERIFICATION.md`

**Analog:** `.planning/phases/150-*/150-VERIFICATION.md` (live-CI-evidence style, most relevant
because this phase's RELEASE-01 criterion is *also* "a real GitHub Actions run, not a local
run") + `.planning/phases/151-*/151-VERIFICATION.md` (frontmatter + criteria-table shape)

**Frontmatter pattern** (from 151-VERIFICATION.md lines 1-7):
```yaml
---
phase: 153-release-tag-cut
verified: <ISO 8601 timestamp>
status: passed
score: N/N must-haves verified
overrides_applied: 0
---
```

**"Not from memory" evidence-citation discipline** (from 150-VERIFICATION.md lines 17-20 —
directly applicable since RELEASE-01 has the identical "real CI run, not local/dry-run" shape):
> "No criterion below is marked PASS from memory or from a local-only run; every PASS cites a
> run URL, a file path with a line reference, or a command's captured output."

For RELEASE-01 specifically, the evidence entry must cite:
- The `gh run view <id> --json conclusion,event,headBranch` output showing `event: "push"` and
  `headBranch` containing `v5.12.0` (NOT `workflow_dispatch` — Pitfall 2 in RESEARCH.md)
- The self-test step's literal stdout line: `SELF_TEST_SIGNING: OK — signtool wiring verified
  end-to-end`
- `gh release view v5.12.0 --json assets` showing `quirk-windows-5.12.0.zip` present

**Required-Artifacts / Requirements-Coverage table shape:** copy the two-column-plus-evidence
table format from 151-VERIFICATION.md lines 32-41 and 69-79 verbatim, substituting this phase's
requirement (RELEASE-01) and artifacts (the tag, the GitHub Release, the two `VERIFICATION.md`/
`VALIDATION.md` files, the `docs/UAT-SERIES.md` Series 153 entry, the Obsidian phase note).

---

### `.planning/phases/153-release-tag-cut/153-VALIDATION.md`

**Analog:** `.planning/phases/151-*/151-VALIDATION.md`

**Frontmatter pattern** (lines 1-8):
```yaml
---
phase: 153
slug: release-tag-cut
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-13
---
```
Update `status`/`nyquist_compliant` as the phase's plan-checker/executor progresses, mirroring
151's document — this file starts in draft state at plan time and is finalized at close.

**Section structure to copy verbatim:** `## Test Infrastructure` table, `## Sampling Rate`
bullets, `## Per-Task Verification Map` table, `## Wave 0 Requirements`, `## Manual-Only
Verifications`, `## Validation Sign-Off` checklist — all present in 151-VALIDATION.md and
directly reusable as headings; content differs (this phase has no new pytest suite — its
"automated command" column entries are `gh run ...`/`pytest tests/test_version.py -x`/
`python scripts/release_tag_hygiene.py` rather than a new `tests/test_*.py` file).

---

## Shared Patterns

### Version single-source-of-truth discipline
**Source:** `tests/test_version.py` (full file, 81 lines)
**Apply to:** `pyproject.toml` edit task, and the parity-check task run immediately after it

```python
_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"
_PROJECT = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))["project"]
TRUTH = _PROJECT["version"]

def test_package_version_matches_pyproject():
    import quirk
    assert quirk.__version__ == TRUTH

def test_cbom_platform_version_matches_pyproject():
    from quirk.cbom.builder import PLATFORM_VERSION
    assert PLATFORM_VERSION == TRUTH
```
Run `pytest tests/test_version.py -x` immediately after editing `pyproject.toml` — 6 assertions,
all pass once the single literal is updated (5 derive automatically; `test_distribution_name_is_canonical`
is unaffected by a version bump and stays green as a canary).

### Towncrier changelog build
**Source:** `docs/release-process.md` Step 4 + `pyproject.toml` `[tool.towncrier]` block
(lines 161-183, comment: "RELENG-04 (Phase 84-02): towncrier CHANGELOG automation")
**Apply to:** the changelog task

```bash
towncrier build --version 5.12.0 --yes
```
`changelog.d/` currently contains only its own `README.md` format-doc — no pending fragment
files (verified: `ls changelog.d/` → `README.md` only). This exact "no fragments" situation
recurred for 5.9 through 5.11 too (`CHANGELOG.md`'s last real towncrier section is `## [5.8.0]`);
those milestones used a standalone `docs/release-notes/X.Y.Z.md` file (see the `5.11.0.md`
analog above) instead of forcing an empty towncrier section. Follow that same precedent for
5.12.0 rather than inventing a new mechanism.

### Tag-hygiene guard — read-only reference, do not edit
**Source:** `.github/tag-hygiene-baseline.txt` (full file header)
**Apply to:** the post-tag verification task

```
# Format: one `<tag> <reason>` per line. ... Adding a line here is an explicit,
# reviewable disposition — NEVER a way to make a *new* release failure quiet.
```
`v5.12.0` must land in the guard's "OK" bucket purely because `release.yml` produced a real
successful run whose `headBranch`/`displayTitle` contains `v5.12.0` — do **not** add a
`v5.12.0` baseline line (Pitfall 6 in RESEARCH.md; confirmed by reading the file's own header
warning, reproduced above verbatim).

### Human-confirmation checkpoint before the tag/push
**Source:** CONTEXT.md locked decision (no prior in-repo code pattern exists for this —
this is a process/workflow pattern from the GSD checkpoint primitive, not a code file)
**Apply to:** the tag-cut task, isolated as its own task/plan step

The tag/push/release-create step must be its own distinct task marked with the project's
`checkpoint:human-verify` (or equivalent) primitive — never folded into a larger "cut and verify
the release" task an autonomous executor could run through unpaused (Pitfall 5 in
RESEARCH.md). Pre-tag verification tasks (push, dry-run, version bump, parity test) carry no
such gate and should run freely.

## No Analog Found

None — every file this phase touches (config literal, three doc files, one optional new
release-notes file, and the standard phase-close artifact trio) has a direct, recently-modified
in-repo analog.

## Metadata

**Analog search scope:** `pyproject.toml`, `README.md`, `docs/UAT-SERIES.md`,
`docs/release-notes/`, `tests/test_version.py`, `.github/tag-hygiene-baseline.txt`,
`.planning/phases/150-*/`, `.planning/phases/151-*/`, git history (`git log --all --grep`,
`git show 4b73940`)
**Files scanned:** 12 (read in full or targeted) + 2 git-history diffs
**Pattern extraction date:** 2026-08-13
