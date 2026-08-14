# Phase 148: Release Pipeline Repair + Windows Asset Backfill - Pattern Map

**Mapped:** 2026-08-11
**Files analyzed:** 3 (1 modified, 2 new)
**Analogs found:** 3 / 3

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `.github/workflows/release.yml` (modify) | CI/CD pipeline (workflow config) | event-driven (tag push / manual dispatch) | itself (existing file, being repaired in place) | exact — self-analog |
| `.github/workflows/release-tag-hygiene.yml` (new) | CI/CD pipeline (scheduled guard) | batch / event-driven (cron) | `.github/workflows/python-staleness.yml` | exact — same role (scheduled drift gate) + same data flow (cron) |
| `docs/release-notes/5.11.0.md` (new) | docs (release notes) | transform (structured markdown authoring) | `docs/release-notes/5.6.0.md` (primary), `docs/release-notes/5.0.0.md` (secondary) | exact — same file family, most recent + most structurally similar disposition-style note |

## Pattern Assignments

### `.github/workflows/release.yml` (modify in place)

**Analog:** itself — apply the four changes below to the existing structure. No external analog needed; the file already contains every pattern (SHA-pinning, permissions blocks, artifact upload) that the new steps must match.

**1. Add `workflow_dispatch:` trigger (D-05)** — current trigger block (lines 35-38):
```yaml
on:
  push:
    tags:
      - 'v*.*.*'
```
Add `workflow_dispatch:` as a sibling key under `on:` (no required inputs per CONTEXT.md discretion note — default to none unless research surfaces a concrete need):
```yaml
on:
  push:
    tags:
      - 'v*.*.*'
  workflow_dispatch:
```

**2. Tag-ref guard on the `publish` job (D-06)** — current job header (lines 78-87):
```yaml
  publish:
    name: Publish to PyPI (Trusted Publishers + Sigstore)
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: release
      url: https://pypi.org/p/quirk-scanner
    permissions:
      id-token: write
      contents: read
```
Add `if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')` at the job level (gates the *whole job*, per D-06 — dry-run `workflow_dispatch` runs must never reach PyPI, **including a dispatch targeting a tag ref**, which is why the event-name conjunct is mandatory and a ref-shape-only guard is unsound):
```yaml
  publish:
    name: Publish to PyPI (Trusted Publishers + Sigstore)
    needs: build
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    environment:
      name: release
      url: https://pypi.org/p/quirk-scanner
    permissions:
      id-token: write
      contents: read
```

**3. Tag-ref guard on the "Attach zip to GitHub Release" step only (D-06)** — current step (lines 272-278):
```yaml
      - name: Attach zip to GitHub Release
        # T-118-SC: action pinned to commit SHA for supply-chain safety (WR-03).
        # SHA corresponds to softprops/action-gh-release v2.2.1.
        # Verify: https://github.com/softprops/action-gh-release/releases/tag/v2.2.1
        # Uses GITHUB_TOKEN only (T-118-NS, T-118-REL-PERM)
        uses: softprops/action-gh-release@c95fe1489396fe8a9eb87c0abf8aa5b2ef267fda  # v2.2.1 (verified via GitHub API)
        with:
```
Per D-06, gate the *step*, not the whole `windows-package` job — build/sign/self-test/zip-assembly must still run on `workflow_dispatch` so dry-run is provable:
```yaml
      - name: Attach zip to GitHub Release
        if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')
        # T-118-SC: action pinned to commit SHA for supply-chain safety (WR-03).
        # SHA corresponds to softprops/action-gh-release v2.2.1.
        # Verify: https://github.com/softprops/action-gh-release/releases/tag/v2.2.1
        # Uses GITHUB_TOKEN only (T-118-NS, T-118-REL-PERM)
        uses: softprops/action-gh-release@c95fe1489396fe8a9eb87c0abf8aa5b2ef267fda  # v2.2.1 (verified via GitHub API)
        with:
```

**4. Artifact upload for dry-run zip (D-07)** — reuse the exact pinned action/version already used by the `build` job (lines 72-76):
```yaml
      - name: Upload dist artifacts
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02  # v4.6.2
        with:
          name: dist
          path: dist/
```
Add a new step in `windows-package`, immediately after "Assemble Windows operator zip" and before (or as a sibling to) "Attach zip to GitHub Release", gated to the *inverse* condition so it only runs on dry-run:
```yaml
      - name: Upload dry-run zip artifact
        if: ${{ !(github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')) }}
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02  # v4.6.2
        with:
          name: quirk-windows-dry-run
          path: quirk-windows-*.zip
```

**Action-pinning convention (apply to any new `uses:` line):** every third-party action is pinned to a full commit SHA with a trailing `# vX.Y.Z` comment, e.g.:
```yaml
uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5  # v4.3.1
```
No new actions are introduced by this phase's changes — `actions/upload-artifact` at the exact same pin already used in the `build` job is reused verbatim (per CONTEXT.md D-07 explicit instruction: "reuse the same pinned action/version for the dry-run zip artifact upload... rather than introducing a new pin").

**Permissions-block convention (WR-04):** each job declares its own least-privilege `permissions:` explicitly; the workflow-level default is `contents: read` (lines 43-44). No permissions changes are needed for the guard additions — `if:` conditions do not require new scopes.

---

### `.github/workflows/release-tag-hygiene.yml` (new)

**Analog:** `.github/workflows/python-staleness.yml` (full file, 42 lines — read in full above)

**Cron trigger pattern** (lines 3-8 of the analog):
```yaml
on:
  pull_request:
  push:
    branches: [main]
  schedule:
    - cron: '0 9 * * 1'  # Mondays 09:00 UTC
```
Per D-09, the new workflow only needs the `schedule:` trigger (the guard's whole reason to exist is that push events produce nothing to react to — CONTEXT.md D-09 explicitly notes "the actual incidents... produced zero events"). Optionally also allow `workflow_dispatch:` for manual re-checks (consistent with the release.yml dry-run precedent), but `pull_request`/`push` triggers from the staleness analog are NOT appropriate here — a per-PR/per-push run would be checking tag state that hasn't changed:
```yaml
on:
  schedule:
    - cron: '0 9 * * 1'  # Mondays 09:00 UTC
  workflow_dispatch:
```

**Checkout/setup shape** (lines 10-20 of the analog):
```yaml
jobs:
  staleness:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5  # v4.3.1

      - name: Setup Python
        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065  # v5.6.0
        with:
          python-version: '3.11'
```
Direct template for the new job — same checkout pin, same Python setup pin. Note: `actions/checkout` on a scheduled workflow that lists tags needs `fetch-depth: 0` (or at least `fetch-tags: true`) since the default shallow checkout does not fetch tags — this is a deviation from the analog that must be added explicitly, since `python-staleness.yml` never needs tag history.

**Run-gate/fail-on-drift shape** (lines 27-41 of the analog — the "run a check, fail the job on violation" idiom):
```yaml
      - name: Run staleness gates
        run: |
          pytest \
            tests/test_qramm_staleness.py \
            ...
            -v -k "staleness or freshness"
```
The tag-hygiene guard's equivalent step (per D-10/D-11) should be a `gh` CLI (or `gh api`) script that: (1) lists local/pushed tags matching a loose pattern (`v[0-9]*`, per D-10 — intentionally broader than the strict `v*.*.*` `release.yml` itself requires), (2) cross-references each against `gh run list --workflow=release.yml` for a corresponding successful run, and (3) exits non-zero (failing the job) when any tag has no corresponding successful run, printing the flagged tags to the job summary (`$GITHUB_STEP_SUMMARY`) per D-11's "visible in the Actions tab" requirement. This is Claude's Discretion territory per CONTEXT.md — exact script structure is left to the executor, but the *shape* (single run-step that both checks and fails) mirrors the analog's `Run staleness gates` step.

**No `permissions:` block currently exists in `python-staleness.yml`** — it relies on the default `GITHUB_TOKEN` read scope. Per CONTEXT.md code_context note (WR-04 pattern), the new tag-hygiene workflow should declare its own minimal `permissions:` block explicitly rather than relying on defaults, e.g.:
```yaml
permissions:
  contents: read
  actions: read  # needed for `gh run list` against release.yml
```
This is a deliberate *departure* from the staleness analog (which has no explicit `permissions:` block) — apply the stricter `release.yml` convention instead, since CONTEXT.md's code_context section explicitly calls this out as an established pattern to follow for the new workflow.

---

### `docs/release-notes/5.11.0.md` (new)

**Analog:** `docs/release-notes/5.6.0.md` (primary — most structurally similar disposition/known-issues framing) and `docs/release-notes/5.0.0.md` (secondary — header/footer boilerplate)

**Header pattern** (5.6.0.md lines 1-5, 5.0.0.md lines 1-5 — identical shape):
```markdown
# QU.I.R.K. 5.6.0 — Distributed Completion + Public Launch

**Released:** 2026-06-12
**Milestone:** v5.6

## What's New
```
Apply directly: `# QU.I.R.K. 5.11.0 — <one-line milestone theme>`, `**Released:** <actual tag-push date>`, `**Milestone:** v5.11`.

**Windows Unsigned/Disposition note pattern** (5.6.0.md lines 124-132 — closest existing precedent for documenting a Windows-asset caveat in release notes):
```markdown
### Windows — Unsigned Binary

The Windows sensor zip is **unsigned**. Authenticode code-signing is deferred to a future spike
(requires an EV certificate + CI secret-handling design). Windows SmartScreen may warn on first run.

Workaround: right-click `quirk.exe` → Properties → Unblock, or run `Unblock-File` in PowerShell:
```powershell
Unblock-File -Path .\quirk-windows-sensor\quirk.exe
```
```
For 5.11.0, this section must be adapted per D-03 into an explicit **"PyPI-only release / no Windows asset"** disposition note (not the unsigned-binary caveat — v5.11.0 has NO Windows asset at all, a stronger statement). Suggested structure under a `## Known Issues` heading (matching 5.6.0.md's `## Known Issues` → `### Windows — Unsigned Binary` nesting at lines 105-124):
```markdown
## Known Issues

### Windows — No Asset Produced (PyPI-only release)

This release is **PyPI-only**. The `windows-package` job failed at the "CI self-test — ephemeral
cert signing round-trip" step (root cause: `signtool verify /pa` requires an Authenticode chain
terminating in a trusted root, which a self-signed cert in `CurrentUser\My` can never satisfy) —
before the release-creation step ever ran. No `quirk-windows-5.11.0.zip` asset exists for this
version.

This was fixed in commit `1a6effc`, already on `main`, but *after* the `v5.11.0` tag was pushed.
**`v5.12.0` (Phase 153) is the first version with a verified Windows artifact.**

Operators needing a Windows sensor build for this version should build from source, or upgrade
to `v5.12.0` or later.
```

**See Also / footer pattern** (5.6.0.md lines 164-175):
```markdown
## See Also

- [CHANGELOG.md](../../CHANGELOG.md)
- [5.5.0 Release Notes](5.5.0.md) — previous release
- `docs/UAT-SERIES.md` — user-acceptance test cases
- `docs/operators-guide.md` — Windows install, Scheduled Task workflow
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — chaos-lab oracle

---

*Generated for the v5.6 milestone close. For previous releases see `.planning/milestones/`.*
```
Apply directly, but note: **`docs/release-notes/5.8.0.md` does NOT exist on disk** (confirmed via directory listing — only `4.4.0.md`, `4.5.0.md`, `4.6.0.md`, `5.0.0.md`, `5.6.0.md` exist), even though `gh release list` shows `v5.8.0` as the latest actual GitHub Release per CONTEXT.md's live-state evidence. This is the same pre-existing 5.7.0–5.10.0.md drift D-04 explicitly puts out of scope. Do NOT link to a non-existent `5.8.0.md`; use `[5.6.0 Release Notes](5.6.0.md)` as the "previous release" link instead (the closest file that actually exists), or omit the per-version link and rely on `[CHANGELOG.md](../../CHANGELOG.md)`.

**Upgrade Guidance pattern** (both analogs, near-identical shape — 5.6.0.md lines 136-149, 5.0.0.md lines 114-124): include a minimal `pip install --upgrade quirk-scanner` block and a "No breaking changes" statement, adapted to note that this release has no distributable Windows change (since none shipped).

## Shared Patterns

### GitHub Actions SHA-pinning convention (WR-03)
**Source:** `.github/workflows/release.yml` (every `uses:` line, e.g. lines 59, 62, 73, 90, 96, 110, 113, 277) and `.github/workflows/python-staleness.yml` (lines 15, 18)
**Apply to:** Any new `uses:` step added to `release.yml` or the new `release-tag-hygiene.yml`.
```yaml
uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5  # v4.3.1
uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065  # v5.6.0
uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02  # v4.6.2
```
Full commit SHA + trailing `# vX.Y.Z` comment on every line, no exceptions. No unpinned/tag-referenced actions anywhere in the two files.

### Least-privilege `permissions:` blocks (WR-04)
**Source:** `.github/workflows/release.yml` lines 43-44 (workflow-level default) and per-job blocks at lines 55-56, 85-87, 103-104
**Apply to:** The new `release-tag-hygiene.yml` workflow (declare its own `permissions:` block; do not rely on the org/repo default) and any job-level changes in `release.yml` (no new scopes needed for the tag-ref guards themselves, since `if:` conditions consume no permissions).
```yaml
permissions:
  contents: read
```
(job-level, narrowest applicable scope; widen only where a specific step needs it, e.g. `id-token: write` for the PyPI OIDC publish, `contents: write` for the GitHub Release asset attach)

### Event+ref dry-run guard idiom (new to this phase, no prior in-repo precedent)
**Source:** N/A — this is new logic introduced by D-06, not copied from an existing analog. Both instances in `release.yml` must use the byte-identical expression for consistency:
```yaml
if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')
```
and its exact logical complement for the dry-run-only artifact-upload step:
```yaml
if: ${{ !(github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')) }}
```

**Do NOT reduce these to the ref-shape-only form** `startsWith(github.ref, 'refs/tags/')` (the shape originally written into D-06 and corrected 2026-08-11). `workflow_dispatch` accepts a tag as its target ref, so on `gh workflow run release.yml --ref v5.11.0` the ref-only guard is TRUE while the event is `workflow_dispatch` — the "dry run" would publish to PyPI and create/overwrite a real GitHub Release. Note also that the complement must wrap the WHOLE expression: `!startsWith(...)` is not the complement of the corrected guard and would cause both the upload step and the attach step to run on a dispatch-against-a-tag. `tests/test_release_workflow_dryrun_guards.py::test_no_guard_is_ref_shape_only` enforces this.

## No Analog Found

None — all three files have a strong analog (self-analog for the modify case, direct structural templates for both new files).

## Metadata

**Analog search scope:** `.github/workflows/`, `docs/release-notes/`
**Files scanned:** `.github/workflows/release.yml`, `.github/workflows/python-staleness.yml`, `docs/release-notes/5.6.0.md`, `docs/release-notes/5.0.0.md`, `.planning/phases/148-release-pipeline-repair-windows-asset-backfill/148-CONTEXT.md`
**Pattern extraction date:** 2026-08-11
</content>
