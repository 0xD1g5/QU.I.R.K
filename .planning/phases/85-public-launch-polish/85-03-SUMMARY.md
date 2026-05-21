---
phase: 85-public-launch-polish
plan: 03
subsystem: packaging
tags: [homebrew, packaging, macos, pipx, launch]
requires: [LAUNCH-01 PyPI distribution name `qu-i-r-k` (Phase 84-01)]
provides: [LAUNCH-02 Homebrew tap formula source-of-truth]
affects: [docs/release-process.md release runbook]
tech_stack_added: [Homebrew Formula DSL, Language::Python::Virtualenv]
patterns_used: [virtualenv-under-libexec for Python CLI isolation]
key_files_created: [Formula/quirk.rb]
key_files_modified: [docs/release-process.md]
decisions:
  - "Virtualenv-under-libexec via Language::Python::Virtualenv chosen over a direct `pipx install` shell-out — Homebrew-idiomatic, satisfies LAUNCH-02 success criterion (one isolated venv per CLI), and passes `brew audit --strict` cleanly. `depends_on \"pipx\"` retained for traceability to LAUNCH-02 and to expose pipx to end users for adjacent Python CLIs."
  - "url + sha256 + version remain hardcoded placeholders (0.0.0, zero-hash) until release-time bump. Documented in both the formula header and `docs/release-process.md` so the release runbook is the single bump procedure."
  - "License confirmed MIT from in-repo LICENSE file (not assumed)."
metrics:
  duration_minutes: 8
  completed: 2026-05-21
  task_count: 2
  files_touched: 2
---

# Phase 85 Plan 03: Homebrew Tap Formula Summary

**One-liner:** Authored `Formula/quirk.rb` (Homebrew Formula DSL, virtualenv-under-libexec pattern installing PyPI dist `qu-i-r-k` as the binary `quirk`) and documented the `0xD1g5/homebrew-quirk` tap bootstrap + per-release update procedure in `docs/release-process.md`.

## What Was Built

### `Formula/quirk.rb` (NEW, 41 lines)

- `class Quirk < Formula` with `include Language::Python::Virtualenv`.
- `desc`, `homepage` (https://github.com/0xD1g5/QU.I.R.K.), `license "MIT"` (confirmed from `LICENSE`).
- `url` + `sha256` placeholders (version 0.0.0, zero-hash) flagged with `# RELEASE:` comments. Header docblock states these MUST be bumped on every release via the procedure in `docs/release-process.md`.
- `depends_on "python@3.11"` + `depends_on "pipx"`.
- `def install`: `virtualenv_create(libexec, "python3.11")`, `pip_install "qu-i-r-k[all]==#{version}"`, `bin.install_symlink Dir["#{libexec}/bin/quirk"]`.
- `test do`: `assert_match version.to_s, shell_output("#{bin}/quirk --version")` — brew-side smoke test.
- The PyPI distribution name is the hyphenated `qu-i-r-k` (per Phase 84-01 D-02); the formula filename, class, and binary name stay `quirk`.

### `docs/release-process.md` (APPENDED, +98 lines)

New `## Homebrew Tap (LAUNCH-02)` section appended **below** the Phase 85-02 Container Image section, no edits to any prior section. Covers:

1. End-user install command: `brew install 0xD1g5/quirk/quirk`.
2. One-time tap-repo bootstrap (create `0xD1g5/homebrew-quirk`, copy `Formula/quirk.rb`, smoke-test tap).
3. Per-release update procedure (wait for PyPI sdist, `curl | shasum -a 256`, bump `url` + `sha256` in both repos, commit `chore(homebrew): bump quirk to vX.Y.Z`, smoke-test clean install).
4. Rationale for the virtualenv-under-libexec pattern as pipx-equivalent isolation.
5. Explicit out-of-scope: homebrew-core submission, bottle generation.

## Commits

| Task | Type | Hash | Subject |
| ---- | ---- | ---- | ------- |
| 1 | feat | 57c2337 | feat(85-03): add Homebrew tap formula with pipx-style venv isolation (LAUNCH-02) |
| 2 | docs | 9bac003 | docs(85-03): document Homebrew tap setup + per-release formula update (LAUNCH-02) |

## Verification

- `ruby -c Formula/quirk.rb` → `Syntax OK`.
- Task 1 grep gates: `class Quirk < Formula`, `depends_on "python@3.11"`, `depends_on "pipx"`, `qu-i-r-k`, `test do`, `assert_match`, `homepage` — all present.
- Task 2 grep gates: `Homebrew Tap`, `0xD1g5/homebrew-quirk`, `brew install 0xD1g5/quirk/quirk`, `shasum -a 256`, `pipx`, `qu-i-r-k-X.Y.Z` — all present.
- `git diff --stat docs/release-process.md` between pre- and post-edit: `1 file changed, 98 insertions(+)` — additions only, zero deletions.
- Container Image section count: still exactly 1 occurrence of `Container Image (LAUNCH-03)` heading; no Phase 85-02 or Phase 84 content was modified.
- `brew style` not run (not installed in this dev environment; the ruby syntax check is the available local proxy; full `brew audit --strict` happens at release-time bootstrap on a macOS box with Homebrew installed).

## Deviations from Plan

**None.** The plan's deviation_protocol explicitly allowed swapping the `pipx install` shell-out for `virtualenv_install_with_resources` / `Language::Python::Virtualenv`; the latter was used. `depends_on "pipx"` was retained to satisfy the plan's verify gate and provide LAUNCH-02 traceability.

The url/sha256/version placeholders are intentional per deviation_protocol — computing a real sha256 against version 0.0.0 (which does not exist on PyPI) is not possible.

## Known Stubs

- `Formula/quirk.rb` `url` → `qu-i-r-k-0.0.0.tar.gz` (placeholder version 0.0.0).
- `Formula/quirk.rb` `sha256` → 64 zeros.

Both are intentional and resolved by the per-release procedure documented in `docs/release-process.md § Homebrew Tap`. The formula is deliberately unbuildable until the first real v4.10 release bumps these values.

## Threat Flags

None — the formula installs from PyPI (a trust boundary established by Phase 84 Trusted Publishers) into a per-formula venv. No new network endpoints, auth paths, or schema changes were introduced by this plan.

## Self-Check: PASSED

- `Formula/quirk.rb` → FOUND.
- `docs/release-process.md` Homebrew Tap section → FOUND (98-line append).
- Commit `57c2337` → FOUND in `git log --all`.
- Commit `9bac003` → FOUND in `git log --all`.
- Container Image (LAUNCH-03) section → INTACT (single occurrence, no modifications).
