# Phase 148: Release Pipeline Repair + Windows Asset Backfill - Context

**Gathered:** 2026-08-11
**Status:** Ready for planning

<domain>
## Phase Boundary

A release job that is broken must be caught before a tag is cut (dry-run mechanism), a malformed
or unpushed tag must be detectable instead of silently doing nothing (tag hygiene guard), and the
v5.11.0 Windows-asset gap must be closed with an explicit, defensible provenance story — not by
adding new release capabilities or a Windows signing certificate (that's a separate deferred
milestone spike per the existing UNSIGNED BINARY NOTICE in `release.yml`).

</domain>

<decisions>
## Implementation Decisions

### D-148-RELEASE04 — Windows asset gap disposition (Option B: explicit disposition, not backfill)

- **D-01:** Do NOT backfill a Windows zip onto a `v5.11.0` GitHub Release. Live scouting during
  this discussion found there is **no GitHub Release object for v5.11.0 at all** — `gh release
  view v5.11.0` returns "release not found." The `windows-package` job (run 31510295324) failed at
  the "CI self-test — ephemeral cert signing round-trip" step, which runs *before*
  `softprops/action-gh-release` (the step that creates the Release). The `publish` job (PyPI) in
  that same run succeeded — PyPI already has `5.11.0` (confirmed via PyPI JSON API). So the actual
  gap is: PyPI has the release, GitHub has no Release object at all, and no Windows asset exists.
- **D-02:** Create a **bare `v5.11.0` GitHub Release with zero assets attached** (`gh release
  create v5.11.0 --notes-file ...` or equivalent). This satisfies "operator reading the Releases
  page can tell without guessing" (Success Criterion 4) without creating a Release page that has
  to exist first for the disposition to be written on it.
- **D-03:** Release body / notes state explicitly: this release is **PyPI-only**; the Windows
  operator zip was not produced because the `windows-package` job failed on the signing self-test
  at the time this tag was cut (root cause: `signtool verify /pa` requires an Authenticode chain
  terminating in a trusted root, which a self-signed cert in `CurrentUser\My` can never satisfy —
  fixed by `1a6effc`, already on `main`, but *after* the `v5.11.0` tag was pushed). State plainly
  that `v5.12.0` (Phase 153) is the first version with a verified Windows artifact.
- **D-04:** Create `docs/release-notes/5.11.0.md` following the existing pattern (`4.4.0.md`,
  `4.5.0.md`, `4.6.0.md`, `5.0.0.md`, `5.6.0.md` already exist; `5.7.0.md`–`5.10.0.md` are
  missing — do not backfill those, out of scope) documenting the same disposition, and link it
  from the GitHub Release body.
- **Rationale (why not Option A / backfill):** Building a zip *now* from a `release.yml` that has
  since changed (`1a6effc`) and attaching it to the `v5.11.0` tag would misrepresent what that
  tag's pipeline actually produced — exactly the supply-chain provenance risk the roadmap flagged
  as non-trivial on a project that ships Sigstore attestations and PyPI Trusted Publishers.
  Disposition keeps release history strictly reproducible-from-tag.

### RELEASE-02 — Dry-run mechanism

- **D-05:** Add `workflow_dispatch:` as a trigger on `.github/workflows/release.yml` alongside the
  existing `push: tags: v*.*.*`.
- **D-06:** Guard every step that mutates external state (creates/updates a GitHub Release,
  publishes to PyPI) with
  `if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')`
  so a `workflow_dispatch` run never touches PyPI or GitHub Releases:
  - The `publish` job (PyPI, Trusted Publishers + Sigstore) — gate the whole job.
  - The "Attach zip to GitHub Release" step inside `windows-package` — gate the step, not the
    whole job, so build/sign/self-test/zip-assembly still run and are provable in dry-run mode.
  - **Corrected 2026-08-11 during plan-checking (correctness fix to this decision's own stated
    intent, not a scope change):** this guard was originally written as
    `if: startsWith(github.ref, 'refs/tags/')` — a ref-SHAPE test. That form is bypassable:
    `workflow_dispatch` lets the operator select any branch *or tag* as the target ref
    (`gh workflow run release.yml --ref v5.11.0`, or the Actions UI tag dropdown). Dispatched
    against a tag, `github.ref` is `refs/tags/<tag>` while `github.event_name` is
    `workflow_dispatch`, so the ref-only guard evaluates TRUE and the "dry run" would really
    publish to PyPI and really attach a zip to a real GitHub Release — the exact outcome this
    decision and Success Criterion 1 forbid, and the exact provenance risk D-01..D-04 exist to
    avoid. The `github.event_name == 'push'` conjunct is therefore mandatory. `push` only fires
    via this workflow's `on: push: tags: ['v*.*.*']` filter, so the event test alone is
    sufficient; the `startsWith` conjunct is retained as defense-in-depth should a branch push
    trigger ever be added. The dry-run artifact-upload step uses the exact logical complement
    `${{ !(github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')) }}`.
- **D-07:** On dry-run, upload the assembled zip as a GitHub Actions workflow artifact
  (`actions/upload-artifact`, matching the existing pattern used by the `build` job) instead of
  attaching it to a Release, so the dry-run's output is inspectable without creating any Release
  side-effect.
- **D-08:** This dry-run run itself is how Success Criterion 2 gets proven — a manually-triggered
  `workflow_dispatch` run must go green end-to-end (self-test included) as the real evidence, not
  code inspection of `1a6effc` alone.

### RELEASE-03 — Tag hygiene guard

- **D-09:** Build a **scheduled** GitHub Actions workflow (new file, e.g.
  `.github/workflows/release-tag-hygiene.yml`), reusing the cron pattern already established by
  `.github/workflows/python-staleness.yml` (`schedule: cron: '0 9 * * 1'`, Mondays 09:00 UTC).
  A push-time-only check cannot catch this failure mode — the actual incidents (`v5.9` glob
  mismatch, `v5.10.0` never pushed) produced **zero events**, so there was nothing for a push
  trigger to react to.
- **D-10:** The job lists all local/pushed git tags matching a loose release-like pattern (e.g.
  `v[0-9]*`, broader than the strict `v*.*.*` the release workflow itself requires — the guard's
  job is to catch tags that look intended as releases but don't match, not just validate already-
  matching ones) and cross-references each against `gh run list --workflow=release.yml` (or the
  GitHub Releases API) for a corresponding successful run.
- **D-11:** Any tag with no corresponding successful `release.yml` run is flagged in the job
  summary and fails the job (visible in the Actions tab, consistent with how the staleness gates
  already surface drift in this repo).
- **D-12:** This guard is what makes Success Criterion 3 concrete: a malformed tag (`v5.9`) or
  unpushed tag (`v5.10.0`) becomes "detectably different" via this workflow's red X, not by an
  operator remembering to check.

### Claude's Discretion

- Exact `gh release create` invocation, notes file structure, and wording for the D-148-RELEASE04
  disposition text — content must match the decisions above but phrasing is left to the executor.
- Exact YAML structure/step naming for the new tag-hygiene workflow, as long as it follows the
  scheduled-check pattern from `python-staleness.yml` and produces a failing job on drift.
- Whether the dry-run's `workflow_dispatch` trigger takes any inputs (e.g. a version override) —
  default to no required inputs unless research surfaces a concrete need.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Release workflow (subject of this phase)
- `.github/workflows/release.yml` — the workflow being repaired; contains the `build`, `publish`,
  and `windows-package` jobs, the self-test step fixed by `1a6effc`, and the existing UNSIGNED
  BINARY NOTICE (Authenticode signing is a separate deferred milestone spike, not in scope here).
- Commit `1a6effc` (`fix(release): trust the ephemeral root so the signing self-test can actually
  pass`) — already on `main`. The repair this phase must prove passing via an actual dry-run.

### Staleness/scheduled-check pattern to reuse for RELEASE-03
- `.github/workflows/python-staleness.yml` — existing scheduled workflow (Monday 09:00 UTC cron)
  whose structure (checkout → setup → run gate → fail on drift) is the template for the new
  tag-hygiene guard.
- `CLAUDE.md` §"Staleness Review Cadence" — documents the existing cadence philosophy for this
  repo; the tag hygiene guard should read as a natural extension of this pattern, not a new one.

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` — RELEASE-01 (Phase 153, depends on this phase's dry-run mechanism),
  RELEASE-02, RELEASE-03, RELEASE-04 (all Phase 148).
- `.planning/ROADMAP.md` §"Phase 148: Release Pipeline Repair + Windows Asset Backfill" — full
  goal, success criteria, and the original D-148-RELEASE04 framing (Option A vs Option B) this
  CONTEXT.md resolves.

### Release notes pattern for D-148-RELEASE04
- `docs/release-notes/5.6.0.md` and `docs/release-notes/5.0.0.md` — closest existing examples of
  the release-notes file format/structure to follow for the new `docs/release-notes/5.11.0.md`.
  Note: `5.7.0.md` through `5.10.0.md` do not exist — this is pre-existing drift, out of scope to
  backfill in this phase.

### Live release-state evidence gathered during this discussion (do not re-derive, verify if stale)
- `gh release list` (as of 2026-08-11): no `v5.9`, `v5.10.0`, or `v5.11.0` GitHub Release exists.
  Latest is `v5.8.0`.
- `gh run view 31510295324` (the `v5.11.0` tag-push run): `build` job succeeded, `publish` job
  (PyPI) succeeded, `windows-package` job failed at "CI self-test — ephemeral cert signing
  round-trip" — before the release-creation step ever ran.
- PyPI (`pypi.org/pypi/quirk-scanner/json`) confirms `5.11.0` is published.
- Current `pyproject.toml` version is `5.11.0` (repo HEAD is ahead of the last real release tag).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.github/workflows/python-staleness.yml` — direct structural template for the RELEASE-03
  scheduled guard (cron trigger, checkout/setup/run-gate/fail-on-drift shape).
- `actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02` (v4.6.2) — already used by the
  `build` job in `release.yml`; reuse the same pinned action/version for the dry-run zip artifact
  upload (D-07) rather than introducing a new pin.

### Established Patterns
- All third-party Actions in `release.yml` are pinned to commit SHA with a version comment (WR-03
  supply-chain pattern) — any new steps/actions added for the dry-run or tag-hygiene guard must
  follow the same pin-to-SHA convention.
- Jobs declare least-privilege `permissions:` blocks explicitly (WR-04) — the new tag-hygiene
  workflow should declare its own minimal `permissions:` rather than relying on any default.

### Integration Points
- `windows-package` job's "Attach zip to GitHub Release" step (near the end of the job) is the
  exact point to add the `if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')`
  guard for D-06 (see the D-06 correction note above — the event-name conjunct is mandatory).
- The `publish` job's `needs: build` + `environment: release` block is the exact point to add the
  same tag-ref guard so `workflow_dispatch` never triggers a real PyPI publish.

</code_context>

<specifics>
## Specific Ideas

No additional specific ideas beyond the decisions above — the user deferred to the recommended
approach for all three areas after reviewing the framing and live-state findings.

</specifics>

<deferred>
## Deferred Ideas

- Authenticode signing for the Windows binary — already explicitly deferred in `release.yml`'s
  UNSIGNED BINARY NOTICE to "a future milestone spike"; not reopened by this phase.
- Backfilling missing `docs/release-notes/5.7.0.md` through `5.10.0.md` — pre-existing drift
  discovered during scouting, unrelated to the v5.11.0 Windows-asset gap this phase closes.

### Reviewed Todos (not folded)
None — no matching todos surfaced.

</deferred>

---

*Phase: 148-Release Pipeline Repair + Windows Asset Backfill*
*Context gathered: 2026-08-11*
