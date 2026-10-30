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
**Status:** mostly fixed (README + getting-started + master guide fixed 2026-10-12; the workflow comment's `gh` line fixed in v5.28.0; a residual `cosign` comment line and two stale UAT-85-07 steps still open)
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

Closed by Phase 235 plan 06 (`619b5ebb`, shipped in v5.28.0): the `.github/workflows/release.yml` header comment now gives
`pypi-attestations verify pypi --repository https://github.com/0xD1g5/QU.I.R.K pypi:<wheel-filename>` and says `gh attestation
verify` cannot see PyPI-stored PEP 740 attestations. The same form was exercised against the real published 5.28.0 on 2026-10-30:
wheel `OK` exit 0, sdist `OK` exit 0, while `gh attestation verify` still answers `HTTP 404` (see UAT-235-15 in `docs/UAT-SERIES.md`).
The published README names no `gh attestation` command (`git show v5.28.0:README.md | grep -n "gh attestation"` finds nothing).

Still open (re-checked 2026-10-30; owners in brackets):

- `.github/workflows/release.yml:31-32` still has an "or via cosign: `cosign verify-blob --bundle <attestation.sigstore.json>`" comment line,
  while `docs/release-process.md:301-304` says no `.sigstore` bundle is attached to the release so that flow has nothing to verify
  against. [owner: release workflow edit, 999.129; comment only]
- `docs/UAT-SERIES.md` UAT-85-07 steps 5-6 grep `docs/release-process.md` for `brew install` and `docker run`, which that file no longer
  contains (checked 2026-10-30: both patterns MISSING), yet the case is still recorded PASS from 2026-08-27. It needs an honest
  re-disposition with `docs/uat-coverage-gaps.md` and the UAT ledger regenerated together. [owner: 999.129]
  UAT-84's `grep -q 'gh attestation verify' docs/release-process.md` check still finds its pattern, so it is not stale.

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
