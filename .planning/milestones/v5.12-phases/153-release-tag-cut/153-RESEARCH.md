# Phase 153: Release Tag Cut - Research

**Researched:** 2026-08-13
**Domain:** Git release engineering / GitHub Actions tag-triggered CI-CD / documentation version-bump hygiene
**Confidence:** HIGH

## Summary

This phase does not build anything new — it *executes* the release runbook that Phase 148 already
wrote (`docs/release-process.md`) and *proves* that Phase 150's CI gate and Phase 151's phase-close
artifact gates hold up against a real, immutable tag. The runbook is fully specified, numbered,
and already battle-tested in prose (it explicitly narrates the exact `v5.11.0` failure this phase
exists to not repeat). The planner's job is to sequence that runbook into GSD tasks, insert the
locked human-confirmation checkpoint immediately before `git tag`/`git push --tags`/`gh release`,
and add the close-out artifacts (`VERIFICATION.md`, `VALIDATION.md`, `docs/UAT-SERIES.md` entry)
that Phase 151's pre-commit hook (`scripts/verify_phase_gates.py`) will mechanically check for on
this phase's own close commit.

One fact materially changes the plan shape versus a naive reading of the phase description:
**local `main` is 40 commits ahead of `origin/main`** (Phases 151 and 152 are fully merged locally
but never pushed). The release runbook's Step 1 ("Verify CI is green on `main`") and Step 2 (the
`workflow_dispatch` dry-run) are both meaningless against unpushed commits — GitHub Actions only
sees what's on `origin`. The plan must push local `main` to `origin/main` first, then verify the
resulting Python CI / Dashboard Quality / Python Staleness Gate runs are green on that exact SHA,
before any dry-run or version bump work begins. This is not a phase-scope violation (pushing
already-complete, already-verified phase work is not "further scanner feature work" per the
CONTEXT.md boundary) — it is a hard prerequisite the runbook silently assumes.

A second fact worth flagging: two GitHub Actions workflows trigger on `push: tags: v*.*.*`, not
one — `release.yml` (PyPI publish + Windows zip, the one the phase description names) and
`release-container.yml` (GHCR image). The phase's stated success criteria only ask about
`release.yml`'s `windows-package` job, but a genuinely green tag push should be verified holistically
(both tag-triggered workflows conclude successfully) so a container-build regression isn't waved
through as "the release is fine."

**Primary recommendation:** Sequence the plan as (1) push local `main` + verify real CI green,
(2) run the Phase 148 `workflow_dispatch` dry-run and confirm the self-test signing step passes,
(3) bump `pyproject.toml` to `5.12.0` + `towncrier build` + `docs/UAT-SERIES.md` version-string
edits + commit, (4) **pause for explicit human confirmation** before `git tag v5.12.0` / `git push
origin main --tags`, (5) after the human approves and the tag is pushed, watch `release.yml` and
`release-container.yml` to green, verify the GitHub Release has the Windows zip attached and the
tag-hygiene guard doesn't flag it, and (6) close the phase with `VERIFICATION.md` +
`VALIDATION.md` + a new `docs/UAT-SERIES.md` Series entry, which is itself the payload that
`scripts/verify_phase_gates.py`'s pre-commit hook will check on the closing commit.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Push local commits to origin | Git / CI trigger surface | — | Prerequisite: GitHub Actions cannot act on unpushed refs |
| Pre-tag verification (dry-run, version parity) | CI / GitHub Actions | Local dev shell | `workflow_dispatch` runs the real pipeline with zero external side effects |
| Version bump | Build config (`pyproject.toml`) | Docs (README/UAT-SERIES) | Single source of truth already enforced by `tests/test_version.py` |
| Tag creation + push | Git (external, human-gated) | — | Locked decision: irreversible, requires explicit human confirmation |
| Release pipeline execution | CI / GitHub Actions (`release.yml`, `release-container.yml`) | GitHub Releases API | Triggered automatically by the tag push; not modified by this phase |
| Tag-format/hygiene guard | CI / GitHub Actions (`release-tag-hygiene.yml`) | `scripts/release_tag_hygiene.py` | Scheduled + on-demand backstop, already built in Phase 148 |
| Phase close-out artifact enforcement | Git hook (`.githooks/pre-commit` → `scripts/verify_phase_gates.py`) | Phase docs (`VERIFICATION.md`/`VALIDATION.md`/`docs/UAT-SERIES.md`) | Phase 151 machinery this phase dogfoods on itself |

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **The actual `git tag v5.12.0` + `git push origin v5.12.0` step (and any GitHub Release
  creation/publish step) is a hard-to-reverse, externally-visible action.** Per standing operating
  guidance, this requires an explicit pause for user confirmation before it runs, regardless of
  what a PLAN.md task says or how confident an executor is. Pre-tag verification (dry-run,
  version-string checks, full suite green) can and should run freely without a pause — only the
  actual tag/release creation step itself is gated.

### Claude's Discretion
- Exact plan/task breakdown for pre-tag checks (tag-hygiene guard dry-run, full test suite green,
  version string consistency) vs. the tag-push-and-verify step itself — follow whatever shape the
  planner and researcher find cleanest, informed by Phase 148's existing dry-run mechanism and
  tag-format guard.
- Exact wording/structure of Phase 153's own VERIFICATION.md / VALIDATION.md / UAT-SERIES.md entry
  — this phase deliberately dogfoods Phase 151's own gates on itself (Success Criterion 4), so
  follow the same shape those gates expect.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. No further scanner feature work; no changes to the
release pipeline mechanics themselves (fixed in Phase 148, used not modified here).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RELEASE-01 | Cutting a release tag produces a Windows operator zip attached to the GitHub Release — the repaired signing self-test (`1a6effc`) is proven by an actual green run, not by inspection | The `release.yml` `windows-package` job (verified below) already contains the fixed self-test step; this phase's job is to trigger it for real on `v5.12.0` and capture the run URL/asset link as evidence, exactly mirroring the `VERIFICATION.md` evidence style Phase 150 used for its own live-fire proof |

## Prerequisite: Unpushed Local Commits [VERIFIED: git]

`git rev-list --left-right --count origin/main...HEAD` returns `0  40` — local `main` (HEAD
`e619de4`) is 40 commits ahead of `origin/main` (HEAD `b0c99df`, Phase 150's close commit).
Phases 151 (Phase-Completion Artifact Gates) and 152 (Discovery Empirical Closure) are fully
committed locally but have never been pushed. `gh run list --branch main` confirms GitHub Actions'
most recent view of `main` is still `b0c99df` (2026-08-13T20:59:55Z, all three jobs green) — it has
no knowledge of anything after that.

**Consequence for the plan:** Step 1 of `docs/release-process.md` ("Verify CI is green on `main`")
and Step 2 (the `workflow_dispatch` dry-run) are executed *against whatever SHA is on `origin`* —
GitHub Actions has no visibility into local, unpushed commits. The plan MUST include an explicit
"push local `main` to `origin/main`" task before the dry-run task, followed by a real
`gh run list --branch main` check that Python CI / Dashboard Quality / Python Staleness Gate all
report `success` on the newly-pushed SHA. Skipping this would mean the dry-run and subsequent tag
are validated against 40-commit-old code, defeating the entire point of the phase.

This push is not a scope violation: it contains only already-completed, already-planned,
already-verified phase work (Phase 151, Phase 152) with no new code. `git status` on the local
repo shows a clean working tree — nothing uncommitted.

## Existing Assets This Phase Uses (Not Modifies)

### `docs/release-process.md` — the canonical runbook [CITED: docs/release-process.md]

A 9-step runbook already exists and is directly actionable:

1. Verify CI is green on `main`.
2. Run a release dry-run (`gh workflow run release.yml --ref main` + `gh run watch <run-id>`) —
   this exercises `build` and the *full* `windows-package` job (PyInstaller build,
   production-signing skip, the CI self-test signing round-trip, zip assembly) with **zero**
   external side effects: `publish` (PyPI) and "Attach zip to GitHub Release" are both gated on
   `github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')`, so even a dispatch
   targeting a tag ref does not publish.
3. Bump `pyproject.toml [project.version]` — the **only** edit; every other surface derives from
   it (`quirk/__init__.py`, CBOM `PLATFORM_VERSION`, reports `PLATFORM_VERSION`,
   `IntelligenceCfg.intelligence_version`) via `importlib.metadata`/`tomllib` fallback, enforced by
   `tests/test_version.py`.
4. `towncrier build --version X.Y.Z --yes` — consumes `changelog.d/*.md` fragments into
   `CHANGELOG.md`.
5. `git add pyproject.toml CHANGELOG.md changelog.d/` + `git commit -m "chore(release): vX.Y.Z"`
   — explicit paths only, never `git add -A`.
6. `git tag vX.Y.Z` + `git push origin main --tags`.
7. Monitor `release.yml` — the real `push` event additionally runs `publish` (PyPI) and attaches
   the Windows zip to the GitHub Release.
8. Verify: `pip index versions quirk-scanner` lists the new version; the GitHub Release carries
   wheel + sdist + attestation bundle + Windows zip; run the Sigstore attestation verification
   command as a sanity check.
9. Update milestone docs; propagate the version into README badges if version-embedded.

**Explicit stop rule already documented:** "if the dry-run is red, do NOT proceed to tag. An
immutable tag turns a pipeline bug into a permanent gap in release history — this is exactly what
happened with `v5.11.0`."

### `.github/workflows/release.yml` — what "green" means [VERIFIED: file read]

Three jobs, all runnable/verifiable via `gh run watch` or `gh run view <id> --log`:

- **`build`** (ubuntu-latest): `python -m build`, uploads `dist/` artifact. No tag-vs-dispatch
  distinction.
- **`publish`** (ubuntu-latest, needs `build`): PyPI Trusted Publishers OIDC + Sigstore
  attestations via `pypa/gh-action-pypi-publish`. Gated `if: github.event_name == 'push' &&
  startsWith(github.ref, 'refs/tags/')` — only runs on the real tag push, never on dispatch.
- **`windows-package`** (windows-latest, `contents: write`): builds the PyInstaller onedir EXE,
  reads the version via `python -c "from quirk import __version__; print(__version__)"`,
  determines signing capability from `QUIRK_SIGNING_CERT_BASE64`/`QUIRK_SIGNING_CERT_PASSWORD`
  secrets (currently absent — production signing stays deferred, expected and documented),
  runs the **CI self-test — ephemeral cert signing round-trip** step (the exact step that failed
  on `v5.11.0` and was fixed in `1a6effc` by trusting the ephemeral root for the `signtool verify
  /pa` call, then removing that trust in cleanup), assembles
  `quirk-windows-<version>.zip`, and — only `if: github.event_name == 'push' &&
  startsWith(github.ref, 'refs/tags/')` — attaches it to the GitHub Release via
  `softprops/action-gh-release`. On a `workflow_dispatch` run the zip instead uploads as an
  inspectable workflow artifact named `quirk-windows-dry-run`.

**What "green" looks like for RELEASE-01 specifically:** the `windows-package` job's "CI self-test
— ephemeral cert signing round-trip" step must print `SELF_TEST_SIGNING: OK — signtool wiring
verified end-to-end` (not fail as it did on `v5.11.0`'s first real tag run), and the "Attach zip to
GitHub Release" step must run (not be skipped) and the resulting `gh release view v5.12.0 --json
assets` must show the `quirk-windows-5.12.0.zip` asset.

### `.github/workflows/release-container.yml` — the second tag-triggered workflow [VERIFIED: file read]

Also triggers on `push: tags: v*.*.*` (builds/pushes a GHCR image). Not named in the phase's
success criteria, but it fires on the exact same tag push and should be checked green as part of
"the tag push worked cleanly" — a plan that only watches `release.yml` could let a broken container
build through unnoticed. Recommend adding it to the verification task's `gh run list` sweep, even
though only `release.yml`'s outcome is a formal success criterion.

### `scripts/release_tag_hygiene.py` + `.github/tag-hygiene-baseline.txt` — the tag-format guard [VERIFIED: file read]

- Loose regex `^v[0-9]` (deliberately broader than `release.yml`'s strict `v*.*.*` glob) flags any
  release-like tag lacking either (a) a successful `release.yml` run whose `headBranch` or
  `displayTitle` contains the tag, or (b) a baseline entry in
  `.github/tag-hygiene-baseline.txt`.
- Runs on a Monday 09:00 UTC cron (`release-tag-hygiene.yml`) and via `workflow_dispatch`; can be
  run locally too (`python scripts/release_tag_hygiene.py`, requires `gh` auth + network).
- `v5.12.0` needs **no** baseline entry — it will be picked up automatically once `release.yml`
  reports a successful run whose `headBranch`/`displayTitle` contains `v5.12.0` (this is exactly
  what Success Criterion 3 asks the plan to confirm — run the guard, or wait for its scheduled
  run, and show `v5.12.0` lands in the "OK" bucket, not "FLAGGED").
- The baseline file's existing entries (`v5.9`, `v5.10.0`, `v5.11.0` with incident-specific
  reasons, plus a long historical-baseline block) are read-only reference material for this phase
  — do not add a `v5.12.0` line to it; a clean tag should need zero baseline exemption.

### `tests/test_release_tag_hygiene.py` and `tests/test_version.py` [VERIFIED: file read]

Existing pytest coverage already exercises the pure decision logic
(`evaluate_tags`/`collect_backed_tags` in the hygiene script, six-surface version parity in
`test_version.py`). Running the full suite (already gated green by Phase 150's CI) is sufficient
pre-tag verification for these — no new tests are needed for this phase; RELEASE-01's proof is a
live CI run, not more unit tests.

## Version String Inventory [VERIFIED: file read]

| Surface | Current value | Needs edit for v5.12.0? |
|---------|---------------|--------------------------|
| `pyproject.toml [project.version]` | `5.11.0` | **YES — the only canonical edit** |
| `quirk/__init__.py::__version__` | derives via `importlib.metadata`/`tomllib` | No — automatic |
| `quirk/cbom/builder.py::PLATFORM_VERSION` | derives from `quirk.__version__` | No — automatic |
| `quirk/reports/writer.py::PLATFORM_VERSION` | derives from `quirk.__version__` | No — automatic |
| `quirk/config.py::IntelligenceCfg.intelligence_version` default | derives from `quirk.__version__` | No — automatic |
| `README.md` line 7 heading | `# QU.I.R.K. — v5.11.0` | **YES — manual literal, not derived** |
| `docs/UAT-SERIES.md` line 3 header | `**Version:** 5.11.0` | **YES — manual literal** |
| `docs/UAT-SERIES.md` UAT-1-02 (lines ~211-227) | pass criteria example `QU.I.R.K. v5.11.0`, Notes citing v5.11.0 | **YES — per project CLAUDE.md "Version bump" doc-checklist row** |
| `docs/getting-started.md` | no hardcoded version string found (only Python-version prereq text) | No |
| `CHANGELOG.md` | latest entry `## [5.8.0]` (towncrier hasn't been run since; more recent milestones documented via `docs/release-notes/*.md` instead) | Handled by `towncrier build --version 5.12.0 --yes` in the runbook's Step 4 |
| `changelog.d/` | contains `README.md` (towncrier fragment format doc) but the researcher found **no pending `.md` fragments** for un-released changes | **Open question — see below** |

`tests/test_version.py::test_pyproject_version_is_well_formed` /
`test_package_version_matches_pyproject` / `test_cbom_platform_version_matches_pyproject` /
`test_reports_platform_version_matches_pyproject` /
`test_intelligence_config_default_matches_pyproject` / `test_distribution_name_is_canonical` are
the six-surface parity gate (per `docs/release-process.md`'s "Single source of truth" section) —
running these after the `pyproject.toml` edit is a cheap, immediate correctness check before the
tag is cut.

## Standard Stack

No new libraries are introduced by this phase. Tooling already in the repo and used verbatim:

| Tool | Version | Purpose | Source |
|------|---------|---------|--------|
| `gh` CLI | 2.97.0 (confirmed installed + authenticated as `0xD1g5`) | Trigger `workflow_dispatch`, watch runs, inspect releases, check tag-hygiene status | `[VERIFIED: gh --version / gh auth status]` |
| `towncrier` | pinned per `docs/release-process.md` (already a project dependency for changelog generation) | Build `CHANGELOG.md` from `changelog.d/` fragments | `[CITED: docs/release-process.md]` |
| `git` | system | Tag creation, push | n/a |

No `npm install`/`pip install` of new packages — Package Legitimacy Audit is not applicable to
this phase (no new external packages).

## Package Legitimacy Audit

Not applicable — this phase installs no new packages. All tooling (`gh`, `towncrier`, `git`) is
pre-existing project infrastructure, already vetted in prior phases.

## Architecture Patterns

### Release cut sequence (data flow)

```
local main (40 commits ahead)
        │
        ▼
  git push origin main          ← must happen first; GH Actions can't see unpushed refs
        │
        ▼
  gh run list --branch main     ← confirm Python CI / Dashboard Quality / Staleness Gate green
        │  (green)
        ▼
  gh workflow run release.yml --ref main   (workflow_dispatch dry-run)
        │
        ▼
  gh run watch <run-id>         ← build + windows-package run; publish/attach-asset SKIPPED
        │  (green: self-test signing step prints SELF_TEST_SIGNING: OK)
        ▼
  edit pyproject.toml → 5.12.0
  towncrier build --version 5.12.0 --yes
  edit README.md / docs/UAT-SERIES.md version literals
  pytest tests/test_version.py -x        ← six-surface parity check
  git commit "chore(release): v5.12.0"
        │
        ▼
  ══════ LOCKED HUMAN-CONFIRMATION CHECKPOINT (CONTEXT.md decision) ══════
        │  (user approves)
        ▼
  git tag v5.12.0
  git push origin main --tags
        │
        ▼
  ┌─────────────────────────┬──────────────────────────────┐
  ▼                         ▼                               ▼
release.yml            release-container.yml       release-tag-hygiene.yml
(build/publish/         (GHCR image build)          (on-demand or next
 windows-package)                                    scheduled run)
        │
        ▼
  gh run watch <run-id>  ← publish job ran (PyPI), windows-package attached zip
        │
        ▼
  gh release view v5.12.0 --json assets   ← confirm quirk-windows-5.12.0.zip present
  python scripts/release_tag_hygiene.py   ← confirm v5.12.0 lands OK, not FLAGGED
        │
        ▼
  Write 153-VERIFICATION.md / 153-VALIDATION.md / docs/UAT-SERIES.md Series entry
        │
        ▼
  git commit (phase close)  ← scripts/verify_phase_gates.py pre-commit hook fires
                               (ARTIFACT-01/02/03 checked automatically — dogfooding proof)
```

### Recommended plan/wave shape

Given the CONTEXT.md discretion note ("follow whatever shape... found cleanest"), the natural
split is:

1. **Pre-tag verification wave** (no human gate needed): push local main, confirm real CI green,
   run the dry-run, confirm self-test signing passes.
2. **Version bump wave** (no human gate needed): `pyproject.toml`, towncrier, README/UAT-SERIES
   literal edits, six-surface parity test, commit.
3. **Tag cut task, isolated and clearly marked** as the `checkpoint:human-verify` (or equivalent
   GSD human-gate primitive) — `git tag` + `git push --tags`, and if the project's release
   convention also calls `gh release create`/edit (see Open Question below), that too sits behind
   the same gate.
4. **Post-tag verification wave**: watch both tag-triggered workflows, confirm Windows zip
   attached, run the tag-hygiene guard.
5. **Phase close wave**: `153-VERIFICATION.md`, `153-VALIDATION.md`, `docs/UAT-SERIES.md` Series
   153 entry, Obsidian phase note + UAT-SERIES sync (per CLAUDE.md Mandatory Phase Completion
   Steps), then the close commit that exercises `scripts/verify_phase_gates.py` for real.

### Anti-Patterns to Avoid
- **Treating the local venv/dry-run as sufficient proof of RELEASE-01.** Phase 150's own
  `VERIFICATION.md` explicitly rejects "local-only run as CI proof" as the exact class of mistake
  to avoid; RELEASE-01 demands an actual green *tagged* run, not the dry-run and not local
  inspection.
- **Running the dry-run or CI-green check against unpushed local commits.** GitHub Actions state
  reflects `origin`, not the local working tree — verify against the pushed SHA.
- **Preemptively adding a `v5.12.0` line to `.github/tag-hygiene-baseline.txt`** when the *actual*
  problem is a tag that hasn't triggered a release run yet — wait for `release.yml`'s real run, or
  trigger `release-tag-hygiene.yml` manually, before touching the baseline file.
- **Bundling the tag-cut step into a task the executor can complete without a pause.** The locked
  CONTEXT.md decision requires this to be a distinct, clearly-flagged human-confirmation point in
  the plan — not folded into a larger "cut and verify the release" task where an autonomous
  executor might run through it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Verifying a workflow run's outcome | Custom polling/log-scraping script | `gh run watch <run-id>` / `gh run view <run-id> --json conclusion` | Already the pattern used in Phase 148/150's own evidence-gathering; `gh` is authenticated and installed |
| Checking whether the tag is "backed" by a release run | Ad hoc `gh api` grep | `python scripts/release_tag_hygiene.py` (already parses `gh run list --workflow release.yml --status success` + `gh release list`) | Purpose-built, already unit-tested, exact match for Success Criterion 3 |
| Changelog generation | Hand-editing `CHANGELOG.md` | `towncrier build --version X.Y.Z --yes` | Documented as the project's Step 4; consumes `changelog.d/*.md` fragments automatically |

**Key insight:** every mechanism this phase needs already exists and is already proven working in
isolation (Phase 148 built and dry-run-verified the pipeline; Phase 150 proved the CI gate holds;
Phase 151 built the phase-close gate). This phase's entire job is sequencing + one irreversible
human-gated action + honest evidence capture — not building anything new.

## Common Pitfalls

### Pitfall 1: Verifying against the wrong SHA
**What goes wrong:** Running the dry-run or checking "CI is green" without first pushing local
`main`, so the verification silently validates 40-commit-stale code.
**Why it happens:** `docs/release-process.md`'s Step 1 assumes `main` is already in sync with
`origin`; that assumption is false right now.
**How to avoid:** Explicit push task before any CI-green check; confirm via `git rev-list
--left-right --count origin/main...HEAD` returning `0 0` before proceeding, and via `gh run list
--branch main --limit 3` showing the pushed SHA.
**Warning signs:** `gh run list` showing a `headSha` that doesn't match `git rev-parse HEAD`.

### Pitfall 2: Treating the dry-run's green result as the RELEASE-01 proof
**What goes wrong:** Success Criterion 1 explicitly says "not the dry-run from Phase 148, an
actual tagged run" — a plan that stops at a green dry-run and calls RELEASE-01 satisfied fails
verification.
**Why it happens:** The dry-run and the real run share the same `windows-package` job definition
and look identical in the Actions UI except for the trigger event.
**How to avoid:** The `VERIFICATION.md` evidence for RELEASE-01 must cite a run whose trigger is
`push` on a `refs/tags/v5.12.0` ref, not `workflow_dispatch` — check `gh run view <id> --json
event,headBranch`.
**Warning signs:** Citing a run ID from before the tag was pushed.

### Pitfall 3: Missing the second tag-triggered workflow
**What goes wrong:** Only watching `release.yml`, missing a `release-container.yml` failure on
the same tag push.
**Why it happens:** The phase description and success criteria only name `release.yml`.
**How to avoid:** `gh run list --branch main` (or filter by the tag ref) after pushing the tag
should show both workflows' runs; check both for `conclusion: success` even though only
`release.yml`'s outcome is a formal gate.
**Warning signs:** A GHCR image silently failing to publish while the phase is marked complete.

### Pitfall 4: Forgetting the manual (non-derived) version-string literals
**What goes wrong:** Bumping `pyproject.toml` and assuming `test_version.py`'s six-surface parity
test covers everything, missing `README.md`'s heading and `docs/UAT-SERIES.md`'s header/UAT-1-02
pass-criteria/Notes, none of which are covered by that test (they're prose, not code).
**Why it happens:** The six derived-surface test creates a false sense of "the version is fully
consistent now."
**How to avoid:** Follow the CLAUDE.md "Version bump" row in the Per-Phase Documentation Checklist
explicitly: `README.md`, `docs/getting-started.md` (confirmed no literal to change, but re-check),
`docs/UAT-SERIES.md` (UAT-1-02 pass criteria + document header).
**Warning signs:** `grep -rn "5\.11\.0" README.md docs/` still returning hits after the phase
claims to close.

### Pitfall 5: Skipping the human-confirmation pause because the executor is confident
**What goes wrong:** An autonomous plan-executor treats the tag-push task like any other shell
command and runs it without pausing.
**Why it happens:** GSD's default execution mode can be fully autonomous; nothing in a PLAN.md
task's literal text enforces a pause unless the task is explicitly marked as a checkpoint.
**How to avoid:** Per CONTEXT.md's locked decision, the plan MUST mark the tag/push/release-create
step with whatever GSD checkpoint primitive forces a real pause (e.g. `checkpoint:human-verify`),
regardless of how mechanical the preceding steps were.
**Warning signs:** A plan where the tag-push task has no distinct checkpoint marker separating it
from the pre-tag verification tasks.

### Pitfall 6: Adding a v5.12.0 baseline entry preemptively
**What goes wrong:** "Just in case" adding `v5.12.0 <reason>` to `.github/tag-hygiene-baseline.txt`
to make Success Criterion 3 pass trivially, defeating the guard's purpose.
**Why it happens:** It's the fastest way to make `release_tag_hygiene.py` exit 0 for a new tag.
**How to avoid:** The guard file's own header explicitly warns against this ("NEVER a way to make
a *new* release failure quiet"). `v5.12.0` should pass because `release.yml` produced a real
successful run whose `headBranch`/`displayTitle` contains the tag — verify that instead.
**Warning signs:** A diff touching `.github/tag-hygiene-baseline.txt` in this phase's plan.

## Code Examples

### Verified pre-tag CI check
```bash
# Source: docs/release-process.md Step 1, adapted with an explicit push-first step
# because local main is currently 40 commits ahead of origin/main.
git push origin main
gh run list --branch main --limit 3 --json headSha,name,conclusion,createdAt
# Expect: all three ("Python CI", "Dashboard Quality", "Python Staleness Gate")
# report conclusion "success" for the just-pushed headSha.
```

### Dry-run trigger and watch
```bash
# Source: docs/release-process.md Step 2
gh workflow run release.yml --ref main
gh run watch <run-id>
# The "CI self-test — ephemeral cert signing round-trip" step must print:
#   SELF_TEST_SIGNING: OK — signtool wiring verified end-to-end
```

### Version bump + parity check
```bash
# Source: docs/release-process.md Steps 3-5, tests/test_version.py
# 1. Edit pyproject.toml [project.version] = "5.12.0" (only edit).
# 2. towncrier build --version 5.12.0 --yes
# 3. Manual literal edits: README.md line 7, docs/UAT-SERIES.md header + UAT-1-02.
pytest tests/test_version.py -x
git add pyproject.toml CHANGELOG.md changelog.d/ README.md docs/UAT-SERIES.md
git commit -m "chore(release): v5.12.0"
```

### Post-tag verification
```bash
# After the human-confirmed tag push:
gh run list --branch main --limit 6   # both release.yml and release-container.yml runs
gh run view <release.yml-run-id> --json conclusion,event,headBranch
gh release view v5.12.0 --json assets,body,isDraft,tagName
python scripts/release_tag_hygiene.py   # confirm v5.12.0 lands in the OK bucket
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Tag pushed with no pre-flight check (`v5.9`, `v5.10.0` incidents) | `workflow_dispatch` dry-run exercises the full `windows-package` job before any tag exists | Phase 148 (2026-08-11) | This phase is the first real-world use of that dry-run against the actual production cut |
| Silent release gaps caught only by manual audit | Scheduled `release-tag-hygiene.yml` (Monday cron) + on-demand `workflow_dispatch` | Phase 148 | v5.12.0 will be the first tag created *after* this guard existed, cut in the intended order (dry-run → tag → guard confirms) |
| Phase close-out artifacts written retroactively or skipped | Pre-commit hook (`scripts/verify_phase_gates.py`) blocks a phase-close commit missing `VERIFICATION.md`/current `VALIDATION.md`/`UAT-SERIES.md` coverage | Phase 151 (2026-08-13, still unpushed to origin) | This phase's own close commit is the first real test of that hook outside its own test suite |

**Deprecated/outdated:** None relevant — all mechanisms referenced are current-state, built in the
same milestone (v5.12, "Release & Verification Integrity") this phase closes.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `changelog.d/` currently has no pending fragment files beyond its own `README.md` doc file, so `towncrier build` may produce an empty or near-empty new section | Version String Inventory | Low — if fragments do exist, towncrier will simply consume them as designed; if none exist, the plan should still run the command (idempotent) and may need a manually-written `CHANGELOG.md` entry summarizing the v5.12 milestone (Phases 148-153) instead, mirroring the `docs/release-notes/*.md` pattern already used for 5.0.0/5.6.0/5.11.0 |
| A2 | The project's established convention for the actual GitHub Release object is `git tag` + `git push --tags` and letting `release.yml`'s automatic `softprops/action-gh-release` step create/update the Release (as opposed to a separate manual `gh release create`) | Standard Stack / Architecture Patterns | Medium — the `v5.11.0` precedent (`docs/UAT-SERIES.md` UAT-148-03) shows `gh release create v5.11.0 --notes-file ...` was run *manually* for that PyPI-only-disposition case, which is a documented exception (no Windows asset expected). For a normal Windows-asset-bearing tag like `v5.12.0`, `release.yml`'s own `softprops/action-gh-release@...` step is the standard mechanism and should create the Release automatically on tag push — no manual `gh release create` step should be needed. Flagged for discuss-phase/planner confirmation since getting this wrong could create a duplicate or premature Release object. |

## Open Questions

1. **Does `changelog.d/` need a fragment authored before `towncrier build` runs for v5.12.0, or is a hand-written milestone summary (matching the `docs/release-notes/*.md` pattern) the intended v5.12 changelog artifact?**
   - What we know: `towncrier` is documented as Step 4 of the runbook and is clearly wired up
     (`changelog.d/README.md` exists documenting the fragment format); `CHANGELOG.md`'s most recent
     real entry is `## [5.8.0]` — nothing was towncrier'd for v5.9 through v5.11 milestones,
     which instead got standalone `docs/release-notes/X.Y.Z.md` files.
   - What's unclear: whether towncrier is still the live mechanism or has been informally
     superseded by the `docs/release-notes/` pattern for the last several milestones.
   - Recommendation: planner should have the executor check `changelog.d/*.md` for real fragment
     files (not just the README) at plan time; if none exist, either author one covering
     Phases 148-153 before running towncrier, or explicitly follow the `docs/release-notes/`
     pattern instead and skip towncrier for this cut — either is defensible, but the plan should
     pick one explicitly rather than leaving it to the executor's discretion mid-task.

2. **Does the phase also need a `docs/release-notes/5.12.0.md` (matching the pattern for 5.0.0, 5.6.0, 5.11.0)?**
   - What we know: three prior milestone-closing tags got a matching `docs/release-notes/X.Y.Z.md`
     file; not every tag did (e.g. no file found for 5.1.0-5.5.x, 5.7.0, 5.8.0's exact match
     wasn't checked exhaustively).
   - What's unclear: whether this is a hard convention or opportunistic documentation.
   - Recommendation: given this phase's entire purpose is proving release integrity end-to-end,
     err toward writing `docs/release-notes/5.12.0.md` summarizing the v5.12 milestone
     (Phases 148-153: pipeline repair, test suite triage, CI gate, phase-close artifact gates,
     discovery empirical closure, this tag cut) — cheap, consistent with precedent, and gives the
     GitHub Release body something substantive to link to.

3. **Is `release-container.yml`'s success a de facto requirement for this phase to be considered fully closed, given it fires on the identical tag push?**
   - What we know: it is not named in ROADMAP.md's success criteria or RELEASE-01's wording.
   - What's unclear: whether a plan that verifies `release.yml` green but is silent about
     `release-container.yml` would pass `/gsd:verify-phase`.
   - Recommendation: include it in the post-tag verification sweep as a non-blocking secondary
     check (documented, not a formal success criterion) — cheap insurance, avoids an
     easily-overlooked gap.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `gh` CLI | Every verification/monitoring step in this phase | ✓ | 2.97.0, authenticated as `0xD1g5` | — |
| `git` | Push, tag, commit | ✓ | system git | — |
| GitHub Actions (`release.yml`, `release-container.yml`, `release-tag-hygiene.yml`) | Success criteria 1-3 | ✓ (all three workflows exist and have run successfully before) | — | — |
| `towncrier` | Changelog build (runbook Step 4) | Not independently verified in this research pass — assumed present as an existing project dependency per `docs/release-process.md` | — | If absent, `pip install towncrier` (already a documented, non-novel dependency; not subject to Package Legitimacy Audit as pre-existing tooling) |
| PyPI Trusted Publisher config | `publish` job | Assumed configured (release.yml has run successfully to PyPI for v5.11.0 per `gh release list` showing it as a real prior release) | — | — |
| Windows code-signing production cert (`QUIRK_SIGNING_CERT_BASE64`/`_PASSWORD` secrets) | Optional production signing step | ✗ (confirmed absent in prior runs; expected/by-design, self-test covers the wiring instead) | — | None needed — job no-ops cleanly by design (D-08 in `release.yml` comments) |

**Missing dependencies with no fallback:** None identified.

**Missing dependencies with fallback:** Production signing certificate (intentionally absent;
out of scope for this phase per the v5.11.0 disposition already recorded in
`docs/release-notes/5.11.0.md`/`5.11.0-github-release-body.md`).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already the project standard; `pytest.ini`/`pyproject.toml` config in place) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| Quick run command | `pytest tests/test_version.py -x` |
| Full suite command | `pytest -q` (Phase 150 confirmed green on CI: 3076 passed / 0 failed as of `bbe8b55` on the CI parity venv) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RELEASE-01 | Real tagged `release.yml` run: `windows-package` job green, self-test passes, GitHub Release carries the Windows zip | live-fire / manual-verified (not a pytest test — this is inherently an external CI proof, matching Phase 150's SUITE-02/03 pattern) | `gh run watch <run-id>` + `gh release view v5.12.0 --json assets` | N/A — evidence lives in `153-VERIFICATION.md`, not a test file |
| (supporting) tag format not flagged | Tag-hygiene guard passes for `v5.12.0` | automated CLI check | `python scripts/release_tag_hygiene.py` (pre-existing script, pre-existing tests in `tests/test_release_tag_hygiene.py`) | ✅ |
| (supporting) version parity | Six-surface version consistency | unit | `pytest tests/test_version.py -x` | ✅ |
| (dogfood) phase-close artifact gate | Phase 153's own close commit passes ARTIFACT-01/02/03 | pre-commit hook (not pytest, but has its own unit suite) | `.githooks/pre-commit` fires `scripts/verify_phase_gates.py` automatically on `git commit` once `.planning/ROADMAP.md`/`.planning/STATE.md` show Phase 153 flipping to Complete | ✅ (`scripts/verify_phase_gates.py`, tests already exist per Phase 151) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_version.py -x` (fast, targeted) after the version-bump
  task; no code changes elsewhere in this phase warrant a broader per-commit run.
- **Per wave merge:** `pytest -q` (full suite) once before the tag-cut checkpoint, as the final
  pre-tag gate — this is effectively runbook Step 1's "CI is green" already covers it via the real
  GitHub Actions run, so a redundant local full-suite run is optional insurance, not a hard
  requirement.
- **Phase gate:** the live-fire GitHub Actions run of `release.yml` on the real `v5.12.0` tag push
  IS the phase gate for RELEASE-01 — no pytest substitute is acceptable per the phase's own
  design (mirrors Phase 150's SUITE-02/03 "real CI run, not local" precedent).

### Wave 0 Gaps
None — existing test infrastructure (`tests/test_version.py`, `tests/test_release_tag_hygiene.py`)
and existing CI workflows (`release.yml`, `release-tag-hygiene.yml`, `release-container.yml`,
`python-ci.yml`) fully cover everything this phase needs to verify. No new test files or fixtures
required.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | No auth surfaces touched |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | No | No new user input surfaces |
| V6 Cryptography | Marginal — code-signing wiring is exercised (not modified) | Existing self-signed ephemeral cert self-test (`release.yml`), production Authenticode cert stays deferred/absent by design; no cryptographic code is written in this phase |

### Known Threat Patterns for this phase's surface

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Accidental publish from a `workflow_dispatch` dry-run | Tampering / Elevation | Already mitigated by `release.yml`'s `github.event_name == 'push'` guard (Phase 148, D-06) — this phase relies on, does not modify, that guard |
| Premature/irreversible tag push without review | Repudiation / operational risk | Locked CONTEXT.md human-confirmation checkpoint before `git tag`/`git push --tags`/`gh release create` |
| Secrets exposure via signing steps | Information Disclosure | `release.yml` already writes the cert to a temp `.pfx` and deletes it in an `if: always()` cleanup step; unchanged by this phase |

This phase performs no new code changes to production scanner logic, so a full ASVS sweep is not
warranted — the above reflects the actual surface touched (CI/release tooling).

## Sources

### Primary (HIGH confidence)
- `docs/release-process.md` — full runbook, version policy, semver commitments (read in full)
- `.github/workflows/release.yml` — read in full, all three jobs
- `.github/workflows/release-container.yml` — trigger condition confirmed
- `.github/workflows/release-tag-hygiene.yml` — read in full
- `scripts/release_tag_hygiene.py` — read in full
- `scripts/verify_phase_gates.py` — read through `check_destructive_archive()` and the trigger regexes
- `tests/test_version.py` — read in full (six-surface parity assertions)
- `.github/tag-hygiene-baseline.txt` — read in full
- `pyproject.toml` — version field + full `[project]` dependency block
- `docs/UAT-SERIES.md` — UAT-1-02, Series 148/150/151/152 headers, version header
- `README.md` — version heading line
- `.planning/REQUIREMENTS.md` — RELEASE-01..04 wording, phase-map row
- `.planning/ROADMAP.md` — Phase 148/153 goal/success-criteria text, D-01..D-04 148-CONTEXT resolution
- `.planning/phases/153-release-tag-cut/153-CONTEXT.md` — locked decision + discretion areas
- `.planning/phases/150-*/150-VERIFICATION.md` — evidence-writing style precedent (live-CI-run-first)
- `git rev-list --left-right --count origin/main...HEAD`, `git log`, `git status` — direct repo inspection
- `gh run list --branch main`, `gh release list`, `gh auth status`, `gh api .../branches/main/protection` — direct GitHub state inspection

### Secondary (MEDIUM confidence)
- None — all findings in this research were verified directly against repo files or live `gh`/`git` queries; no WebSearch was needed since every mechanism this phase touches is already fully built and documented in-repo.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new tooling; every command verified against actual installed
  binaries (`gh --version`, `git`) or existing project scripts.
- Architecture: HIGH — the entire pipeline (release.yml, tag-hygiene, phase-close gate) is
  pre-built and read in full; this phase is pure sequencing + evidence-gathering.
- Pitfalls: HIGH — Pitfalls 1-2 are derived from directly-observed repo state (the unpushed-commits
  fact, the explicit "not the dry-run" wording in ROADMAP.md); Pitfalls 3-6 are derived from
  reading the actual guard/hook source code and its own inline warnings.

**Research date:** 2026-08-13
**Valid until:** This research describes a one-shot, largely irreversible operational phase (tag
cut) rather than an evolving codebase area — validity is bounded by the moment `v5.12.0` is
actually pushed (after which the "unpushed local commits" and "current version is 5.11.0" facts
become stale) rather than a calendar window. Re-verify the `origin/main` sync state and current
`pyproject.toml` version immediately before planning execution if more than a few days elapse.
