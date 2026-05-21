---
phase: 85-public-launch-polish
plan: 02
subsystem: release-engineering
tags: [docker, ghcr, multi-arch, ci, release, launch]
requires: [85-01]
provides: [LAUNCH-03]
affects: [release-pipeline, distribution]
tech_stack_added: [docker/build-push-action@v6, docker/setup-qemu-action@v3, docker/setup-buildx-action@v3, docker/login-action@v3, GHCR]
patterns: [tag-triggered-workflow, multi-arch-container, pypi-poll-before-build, non-root-runtime-user, OCI-image-labels]
key_files_created:
  - Dockerfile
  - .dockerignore
  - .github/workflows/release-container.yml
key_files_modified:
  - docs/release-process.md
decisions:
  - "Sibling workflow release-container.yml (not extending release.yml) — separates packages:write from id-token:write surface; container failure cannot block PyPI publish."
  - "PyPI-availability poll (curl /pypi/qu-i-r-k/${version}/json, 20×30s) is the cross-workflow gate; no GitHub Actions `needs:` across workflow files."
  - "Single base image python:3.11-slim — Alpine and distroless rejected per Phase 85 D-LAUNCH Docker (cryptography wheel compat + first-run debuggability)."
  - "playwright browsers deliberately omitted from base image — optional extra, out of scope for v4.10 GHCR ship."
metrics:
  duration_seconds: 154
  tasks_completed: 3
  files_changed: 4
  commits: 3
  completed_date: 2026-05-21
---

# Phase 85 Plan 02: Multi-arch GHCR Container Image Summary

One-liner: Tag-triggered GitHub Actions workflow publishes `ghcr.io/0xd1g5/quirk:{latest,vX.Y.Z}` for `linux/amd64` + `linux/arm64`, installing QU.I.R.K. from the matching PyPI wheel (not the local source tree) via `docker/build-push-action@v6` with QEMU.

## What Shipped

| File                                            | Role                                                                                          |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `Dockerfile`                                    | `python:3.11-slim` base, `nmap`+`curl`+`ca-certificates`, non-root `quirk` user, `pip install "qu-i-r-k[all]==${QUIRK_VERSION}"`, default `CMD ["quirk", "--help"]`, OCI provenance labels. |
| `.dockerignore`                                 | Excludes `.git`, `.planning`, `tests`, `chaos-lab/`, `quantum-chaos-enterprise-lab/`, `docs/`, `examples/`, venvs, build artifacts, OS junk, vault paths. Build context stays tight. |
| `.github/workflows/release-container.yml`       | `on: push.tags: ['v*.*.*']`. Polls PyPI for wheel availability (max 10 min), then runs QEMU + buildx multi-arch build, pushes via GHCR login with `GITHUB_TOKEN`. `permissions: { contents: read, packages: write }`. `provenance: true`. |
| `docs/release-process.md` (appended)            | New `## Container Image (LAUNCH-03)` section covering workflow coordinates, verification commands (`docker pull` + `docker buildx imagetools inspect`), one-time GHCR public-visibility flip, and the "what's NOT included" notes (playwright, alpine/distroless). |

## Tasks Executed

| # | Task                                            | Commit    | Files                                                  |
| - | ----------------------------------------------- | --------- | ------------------------------------------------------ |
| 1 | Author Dockerfile + .dockerignore               | `ef4b67b` | `Dockerfile`, `.dockerignore`                          |
| 2 | Add .github/workflows/release-container.yml     | `eceba3c` | `.github/workflows/release-container.yml`              |
| 3 | Append "Container Image" section to release-process.md | `bb7e1f3` | `docs/release-process.md`                         |

## Verification

Automated gates from PLAN.md (all green):

- `python -c "import yaml; yaml.safe_load(open('.github/workflows/release-container.yml'))"` exits 0.
- `Dockerfile` contains the required markers: `python:3.11-slim`, `qu-i-r-k[all]`, `CMD ["quirk", "--help"]`, `USER quirk`, `QUIRK_VERSION`.
- `.dockerignore` excludes `.git` (top-level marker).
- `release-container.yml` contains `linux/amd64,linux/arm64`, `ghcr.io/0xd1g5/quirk`, `QUIRK_VERSION=`, `packages: write`, `docker/setup-qemu-action`.
- `docs/release-process.md` contains `Container Image`, `ghcr.io/0xd1g5/quirk`, `linux/amd64`, `release-container.yml`, `docker pull`.
- `git diff --stat docs/release-process.md` shows additions only (+76 lines, 0 deletions).

`hadolint` is not installed on the executor host — Dockerfile lint was skipped per plan ("via `hadolint` if available else skip"). Suggest adding hadolint to a future CI workflow if shift-left lint is desired.

Repo-wide version-literal scan: `grep '4\.10\.0'` against `Dockerfile` and `release-container.yml` returned only two **example** occurrences inside comments (`v4.10.0` shown to illustrate the strip-leading-`v` step). No hard-coded version pinning that could drift from `pyproject.toml`.

## Success Criterion (ROADMAP Phase 85 #2)

> "`docker run ghcr.io/<org>/quirk:latest --help` prints the QU.I.R.K. help text on both `linux/amd64` and `linux/arm64`."

Status: **structurally true** — workflow + Dockerfile are in place to produce the image. The proof-of-publish event happens at the first v4.10 tag push (post-merge), at which point operators verify per the `## Container Image` runbook section.

## Deviations from Plan

None — the plan was executed exactly as written across all 3 tasks.

A single Write was momentarily blocked by the `security_reminder_hook` (workflow-injection lint) on first attempt; resolved by refactoring `github.ref_name` consumption through an explicit `env: REF_NAME:` block (the canonical safe pattern). Final workflow file uses env-var indirection for all attacker-influenceable context. This is not a plan deviation — it is the standard workflow-injection mitigation pattern and the resulting YAML is cleaner.

## Authentication Gates

None encountered. The workflow itself uses `secrets.GITHUB_TOKEN` (automatically scoped by `permissions: { packages: write }`) — no PAT or org-level credential provisioning needed.

## File Overlap Notes (for Plan 85-03)

The new section in `docs/release-process.md` lives under heading `## Container Image (LAUNCH-03)` and is **appended** at end-of-file with no edits to prior content. Plan 85-03 (Homebrew tap, LAUNCH-02) can safely append its own `## Homebrew Tap` heading below this one with zero merge conflict.

## Known Stubs

None. No placeholder values, no empty data sources, no TODO/FIXME markers introduced.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: new-trust-boundary | `.github/workflows/release-container.yml` | New OCI artifact (GHCR container image) signed with `provenance: true`. Trust chain: PyPI Trusted Publisher → wheel → `pip install` inside container build → GHCR push via `GITHUB_TOKEN`. No additional secrets introduced. Container is not yet cosign-signed (that is deferred to a future phase — current Phase 85 ships the build path, not separate attestation infrastructure beyond build-push-action's `provenance:`). |

## Follow-ups

- Post-tag verification: after first `v4.10.0` push, confirm `docker buildx imagetools inspect ghcr.io/0xd1g5/quirk:v4.10.0` shows both `linux/amd64` and `linux/arm64` manifests.
- One-time GHCR visibility flip to public after first successful publish (documented in the appended runbook section).
- Optional future hardening: add `hadolint` as a CI lint step on `Dockerfile`; add `cosign sign` to `release-container.yml` if/when project policy requires container signing beyond the build-push-action provenance attestation.

## Self-Check: PASSED

- `Dockerfile`: FOUND
- `.dockerignore`: FOUND
- `.github/workflows/release-container.yml`: FOUND
- `docs/release-process.md`: FOUND (modified)
- Commit `ef4b67b`: FOUND
- Commit `eceba3c`: FOUND
- Commit `bb7e1f3`: FOUND
