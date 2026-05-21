---
phase: 84-release-engineering
plan: 03
subsystem: release-engineering
tags: [releng, ci, pypi, trusted-publishers, sigstore, attestations, oidc]
requirements_closed: [RELENG-02, RELENG-03]
decisions_logged: []
dependency_graph:
  requires:
    - "v4.10-D-02 (plan 84-01) — distribution name `qu-i-r-k`"
  provides:
    - "Tag-triggered PyPI publish pipeline"
    - "Sigstore attestations on every release artifact"
  affects:
    - ".github/workflows/release.yml"
tech_stack:
  added:
    - "pypa/gh-action-pypi-publish@release/v1 (GHA marketplace action)"
    - "actions/upload-artifact@v4 / actions/download-artifact@v4"
  patterns:
    - "Trusted Publishers (GitHub OIDC → PyPI; no stored API tokens)"
    - "Sigstore keyless attestation (`attestations: true` flag)"
    - "Build-then-publish two-job pattern with artifact handoff"
key_files:
  created:
    - .github/workflows/release.yml
  modified: []
decisions: []
metrics:
  duration_minutes: 4
  completed: 2026-05-21
commit: 0f3bc4d
---

# Phase 84 Plan 03: Trusted Publishers Release Workflow + Sigstore Attestations Summary

Tag-triggered (`v*.*.*`) release pipeline that builds wheel + sdist via
`python -m build`, then publishes to PyPI through GitHub Actions Trusted
Publishers (OIDC, no stored tokens) with Sigstore attestations auto-generated
by `pypa/gh-action-pypi-publish@release/v1`.

## What Was Built

`.github/workflows/release.yml` (85 lines) with the following shape:

- **Trigger:** `on.push.tags: ['v*.*.*']` — strict semver filter, no untrusted
  user input reaches any `run:` step.
- **Job `build`** (ubuntu-latest):
  - `actions/checkout@v4`
  - `actions/setup-python@v5` (Python 3.11)
  - `python -m pip install --upgrade pip build`
  - `python -m build` (produces both wheel and sdist into `dist/`)
  - `actions/upload-artifact@v4` (name `dist`, path `dist/`)
- **Job `publish`** (`needs: build`, ubuntu-latest):
  - `environment: { name: release, url: https://pypi.org/p/qu-i-r-k }`
  - `permissions: { id-token: write, contents: read }` (OIDC required)
  - `actions/download-artifact@v4` retrieves the `dist` artifact
  - `pypa/gh-action-pypi-publish@release/v1` with `attestations: true`
  - **No** `password:` / `username:` / `TWINE_*` / `secrets.PYPI*` — Trusted
    Publishers + OIDC supplies the credential automatically.

## Distribution Name

Uses `qu-i-r-k` per **v4.10-D-02** (plan 84-01). The environment URL
(`https://pypi.org/p/qu-i-r-k`) and the Trusted Publisher PyPI-side project
name must match.

## Requirements Closed

- **RELENG-02** — GitHub Actions Trusted Publishers configured (OIDC, zero
  stored API tokens).
- **RELENG-03** — Sigstore attestations auto-generated via `attestations: true`
  on the PyPA publisher action. Downstream verification:
  `gh attestation verify <wheel> --repo <owner>/<repo>` or
  `cosign verify-blob --bundle <attestation.sigstore.json> <artifact>`.

## Manual Setup Required (One-Time, Post-Merge)

These steps are documented inline in the workflow's header comment AND will be
expanded into a full runbook in plan 84-04's `docs/release-process.md`. They
are intentionally NOT documented in this plan's deliverables (scope discipline):

1. After this file lands on `main` and the first `v*.*.*` tag is pushed:
   configure a Trusted Publisher at
   <https://pypi.org/manage/account/publishing/> with:
   - Project: `qu-i-r-k`
   - Repo owner/name: this repository
   - Workflow filename: `release.yml`
   - Environment name: `release`
2. Create a GitHub environment named `release` in repo
   `Settings → Environments` (no protection rules required initially).

## Verification

All five PLAN gates green:

| Check                                                              | Result |
| ------------------------------------------------------------------ | ------ |
| `.github/workflows/release.yml` exists                             | PASS   |
| Contains `pypa/gh-action-pypi-publish`                             | PASS   |
| Contains `attestations: true`                                      | PASS   |
| Contains `id-token: write`                                         | PASS   |
| Contains tag pattern `v*`                                          | PASS   |
| YAML parses cleanly (`python -c "import yaml; yaml.safe_load(...)"`)| PASS   |
| No `password:` / `TWINE_*` / `PYPI_API_TOKEN` / `secrets.PYPI*`    | PASS   |
| Single atomic commit, `feat(84-03):` subject                       | PASS   |

## Deviations from Plan

None — plan executed exactly as written. Two tasks, single commit, single
file, explicit `git add` path (no `git add -A`/`.`).

## Decisions Made

None. Distribution name (`qu-i-r-k`) was inherited verbatim from plan 84-01
decision v4.10-D-02; no new decisions required.

## Known Stubs

None. The workflow is fully wired and functional. The PyPI-side Trusted
Publisher configuration is a documented post-merge manual step (intentional,
not a stub), and is covered by plan 84-04's release runbook.

## Threat Flags

None. The workflow accepts no untrusted user input — the only event is
`push.tags` filtered to `v*.*.*`, and no `github.event.*` fields are
interpolated into any `run:` step. A `Security note:` comment in the file
header documents this for future maintainers.

## Self-Check: PASSED

- `.github/workflows/release.yml` — FOUND
- Commit `0f3bc4d` — FOUND (verified via `git log`)
