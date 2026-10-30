---
type: todo
created: 2026-10-12
source: Phase 224 plan 08 (docs/release-process.md audit)
priority: high
area: .github/workflows/release.yml (header comment), docs/UAT-SERIES.md
status: pending
resolves_phase: null
owner: "999.129"
---

# README and getting-started tell users to run `gh attestation verify`, which fails for the PyPI wheel

**Filed:** 2026-10-12 (Phase 224 plan 08, docs/release-process.md audit)
**Priority:** P1 for the launch doc review — a security verification instruction that cannot succeed
**Status:** partially fixed (README + getting-started + master guide fixed 2026-10-12; workflow comment and UAT cases still open)
Frontmatter added by Phase 227 (D-02): priority: high derived literally from the body "P1 for the launch doc review"; the launch gate closed 2026-10-15, but no priority is invented here (orchestrator ruling on RESEARCH Open Question 2). This is a fifth out-of-scope high todo, named in HORIZON 999.129.

## What happens

`docs/release-process.md` was corrected in plan 224-08 after two live checks against the published
`quirk_scanner-5.25.0-py3-none-any.whl`:

- `gh attestation verify --owner 0xD1g5 <wheel>` and `gh attestation verify --repo 0xD1g5/QU.I.R.K <wheel>` both
  fail with `HTTP 404` from `api.github.com/.../attestations/sha256:...`: the release workflow's
  `pypa/gh-action-pypi-publish` `attestations: true` stores PEP 740 attestations on PyPI, not in GitHub's store.
- `pypi-attestations verify pypi --repository https://github.com/0xD1g5/QU.I.R.K pypi:<file>` prints `OK` for the
  wheel and the sdist.

Fixed 2026-10-12 (Phase 224 wave-2 fix-up): `README.md:144` and `docs/getting-started.md:19` now point at
`docs/release-process.md#attestation-verification-for-downstream-consumers`; `docs/quirk-master-guide.md` regenerated.
Ledger rows (224-03, 224-04) re-dispositioned FIXED/REMOVED.

Still open (owners in brackets):

- `.github/workflows/release.yml:28-31` header comment (`gh attestation verify ...`, `cosign verify-blob --bundle`) [owner: release workflow edit, not a doc plan; .github/workflows is off limits to phase 224 doc plans]
- `docs/UAT-SERIES.md` UAT-84 (grep for `gh attestation verify` in release-process.md) and UAT-85-07 steps 5-6
  (`brew install`, `docker run` greps), plus the Homebrew/GHCR sections other UAT cases cite, all of which
  assume text plan 224-08 removed. [owner: plan 224-18 (UAT)]

## Fix

Replace the instruction with the `pypi-attestations verify pypi` form (or link to the release-process section),
edit the workflow comment, and re-disposition the affected UAT cases honestly (SKIP/GAP annotations, not ticks).

## Feasibility & Effort

- Feasibility: CONFIRMED, both directions run live (404 vs OK).
- Effort: S for README/getting-started/workflow comment (+ master guide regen); S-M for the UAT re-dispositions
  because `docs/uat-coverage-gaps.md` and the UAT ledger must be regenerated together.
- Unknowns: whether the project wants to also publish GitHub-store attestations (`actions/attest-build-provenance`)
  so that `gh attestation verify` becomes true.
- Spike needed: no.
