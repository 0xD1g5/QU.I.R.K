# Phase 148: Release Pipeline Repair + Windows Asset Backfill - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-11
**Phase:** 148-Release Pipeline Repair + Windows Asset Backfill
**Areas discussed:** Windows asset gap disposition, Dry-run mechanism design, Tag hygiene guard design

---

## Windows asset gap disposition (D-148-RELEASE04)

| Option | Description | Selected |
|--------|-------------|----------|
| Option A — backfill the asset | Build a Windows zip now from the `v5.11.0` tag with the repaired workflow, attach it, note post-hoc provenance in the release body | |
| Option B — disposition the gap | Leave v5.11.0 PyPI-only; state explicitly in release notes / Releases page; `v5.12.0` is first version with verified Windows artifact | ✓ |

**User's choice:** Deferred to Claude's recommendation ("I think these areas are well understood. I will defer to you and take the recommended actions.")
**Notes:** Live scouting during discussion found no GitHub Release object exists for `v5.11.0` at all — the `windows-package` job failed at the self-test step, before the release-creation step ever ran. `publish` (PyPI) succeeded independently. This tipped the recommendation firmly to Option B: backfilling would mean fabricating a Release page and binary provenance for a tag whose actual pipeline run never produced either. Recommendation: create a bare `v5.11.0` GitHub Release with zero assets, explicit PyPI-only disposition text, plus a new `docs/release-notes/5.11.0.md`.

---

## Dry-run mechanism design (RELEASE-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Add `workflow_dispatch`, guard mutating steps by `github.ref` tag-prefix, upload dry-run zip as workflow artifact | Proves build/sign/self-test/zip-assembly end-to-end without touching PyPI or GitHub Releases | ✓ |

**User's choice:** Deferred to Claude's recommendation.
**Notes:** The `publish` job and the "Attach zip to GitHub Release" step are the two state-mutating points in `release.yml`; both gated with `if: startsWith(github.ref, 'refs/tags/')`. **[Corrected 2026-08-11 at plan-check: the guard is `github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')` — the ref-only form is bypassable by dispatching against a tag ref. See 148-CONTEXT.md D-06.]** The self-test step itself is unconditional, so a dry-run run is real evidence the repair (`1a6effc`) works, not just code inspection.

---

## Tag hygiene guard design (RELEASE-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Scheduled drift-check workflow, reusing `python-staleness.yml`'s Monday-09:00-UTC cron pattern | Diffs tags matching `v[0-9]*` against successful `release.yml` runs; fails the job on any gap | ✓ |

**User's choice:** Deferred to Claude's recommendation.
**Notes:** The original incidents (`v5.9` glob mismatch, `v5.10.0` never pushed) produced zero events for a push-trigger to react to — only a scheduled sweep can catch "a tag exists but nothing ran for it." Reuses an existing pattern already established in this repo rather than inventing a new mechanism.

---

## Claude's Discretion

- Exact `gh release create` invocation and notes wording for the v5.11.0 disposition.
- Exact YAML step naming/structure for the new tag-hygiene workflow.
- Whether `workflow_dispatch` takes any inputs (default: none, unless research surfaces a need).

## Deferred Ideas

- Authenticode signing for the Windows binary — already deferred to a future milestone spike per `release.yml`'s existing UNSIGNED BINARY NOTICE.
- Backfilling missing `docs/release-notes/5.7.0.md`–`5.10.0.md` — pre-existing drift noticed during scouting, unrelated to this phase's scope.
