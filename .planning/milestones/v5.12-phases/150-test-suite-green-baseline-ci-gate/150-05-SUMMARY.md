---
phase: 150-test-suite-green-baseline-ci-gate
plan: "05"
subsystem: ci
tags: [chaos-lab, docker, ci, certs, docs]

# Dependency graph
requires:
  - phase: 150-test-suite-green-baseline-ci-gate
    plan: "04"
    provides: "CI-parity venv + authoritative failure inventory"
provides: "Category E root-cause fix — email/grpc-tls chaos-lab certs auto-generate; docs synced"
affects: [150-06, 150-07, 150-08, 150-09, SUITE-02, SUITE-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ensure_profile_certs() in lab.sh mirrors ensure_lab_certs()'s idempotent existence-guard pattern for per-profile Docker-bind-mounted certs"

key-files:
  created:
    - tests/test_lab_profile_certs.py
  modified:
    - quantum-chaos-enterprise-lab/lab.sh
    - quantum-chaos-enterprise-lab/README.md
    - quantum-chaos-enterprise-lab/expected_results_v4.md
    - labs/email/README.md
    - labs/email/expected_results.md
    - labs/grpc-tls/README.md
    - docs/chaos-lab.md
    - CONTRIBUTING.md

key-decisions:
  - "Cleaned up two leftover empty directories (labs/grpc-tls/certs/grpc-tls.{crt,key}) left on disk from a prior Docker bind-mount failure -- exactly the bug this plan fixes, confirmed via git status showing them untracked/gitignored before removal"
  - "D-12/D-13 implemented as a single new ensure_profile_certs() function (not per-profile duplication), covering all 3 cert pairs (postfix, dovecot, grpc-tls) with the same existence-guard idempotency contract as the pre-existing ensure_lab_certs()"

requirements-completed: []

# Metrics
duration: ~40min
completed: 2026-08-12
---

# Phase 150 Plan 05: Chaos-Lab Cert Auto-Generation (Category E) Summary

**Added `ensure_profile_certs()` to `lab.sh` so the `email` and `grpc-tls` chaos-lab profiles materialize their gitignored self-signed certs automatically on `up`/`all`/`reset` (and via a new standalone `certs` command), closing the Docker bind-mount failure that broke `test_chaos_lab_idempotency.py::test_profile_re_up_is_idempotent[email]` on real CI — then synced every doc surface (README, both lab READMEs, both expected-results oracles, `docs/chaos-lab.md`, the Obsidian vault, and `CONTRIBUTING.md`) to describe the new behavior.**

## What Was Built

### Task 1 — `ensure_profile_certs()` + regression test (D-12, D-13)

Wrote `tests/test_lab_profile_certs.py` first (TDD RED — `./lab.sh certs` did not
exist yet, confirmed via a failing `Unknown command: certs` run), then implemented
`ensure_profile_certs()` in `quantum-chaos-enterprise-lab/lab.sh` immediately after
the pre-existing `ensure_lab_certs()`, using the identical idempotent
existence-guard pattern (`if [[ ! -f key || ! -f crt ]]`) for three cert pairs:

- `labs/email/certs/postfix.{key,crt}` (CN `postfix.chaos.local`)
- `labs/email/certs/dovecot.{key,crt}` (CN `dovecot.chaos.local`)
- `labs/grpc-tls/certs/grpc-tls.{key,crt}` (CN `grpc-tls.chaos.local`)

Each invocation reuses the exact openssl parameters, key sizes, and chmod modes
from `labs/email/Makefile` / `labs/grpc-tls/Makefile` (RSA-2048, `-days 3650`,
`-nodes`; 644/600 for email, 644/640 for grpc-tls). Wired into the `up`, `all`,
and `reset` dispatch arms (right after `ensure_lab_certs`), and exposed as a new
standalone `certs` command that runs both cert functions and exits without ever
calling `compose` or `_validate_pinned_tags`.

**Environment note:** while writing the test, `labs/grpc-tls/certs/grpc-tls.{crt,key}`
were discovered to be leftover empty *directories* on this local working copy —
residue from a prior Docker bind-mount failure (the exact `mount ... not a
directory` error this plan closes). Confirmed untracked/gitignored via
`git status --porcelain`, then removed (`rm -rf`) so cert generation could
proceed; this is filesystem cleanup of Docker-created artifacts, not a
destructive git operation, and matches the failure mode Category E describes.

`tests/test_lab_profile_certs.py` (no skip/xfail/importorskip markers, not
`slow`-marked) asserts: all six files exist after `./lab.sh certs`; a second run
is byte-identical (SHA-256 hash comparison); each generated cert's subject CN
matches the expected value via `cryptography.x509`; and the command's combined
stdout/stderr never contains `starting lab`, `starting all profiles`, or
`pin policy` — proving the `certs` arm never touches Docker.

Verified: `bash -n lab.sh` exits 0; `pytest tests/test_lab_profile_certs.py -q -m ""`
→ 4 passed; `pytest tests/test_skip_registry.py -q -m ""` → 1 passed (no new
skip markers introduced); `git status --porcelain labs/ | grep -c "certs/"` → 0
(generated certs remain untracked).

### Task 2 — Doc surface sync (CLAUDE.md Chaos Lab Maintenance + LIVE-03)

Updated every doc surface the plan named to describe the new auto-generation
behavior, without altering any expected finding/port/severity content:

- `docs/chaos-lab.md` §2 Quick Start gained a paragraph on automatic cert
  generation + `./lab.sh certs`; §3.18 (email) gained a one-line note that certs
  materialize on first `up`. §3.19 (broker) intentionally left untouched — out
  of D-12/D-13 scope.
- `quantum-chaos-enterprise-lab/README.md` — new "Lab certificates" paragraph
  covering `email`/`grpc-tls`, plus `./lab.sh certs` added to the Quick Start
  command block.
- `labs/email/README.md` and `labs/grpc-tls/README.md` — `make certs` reframed
  as optional/manual-only, since `lab.sh` now generates the same files.
- `labs/email/expected_results.md` and
  `quantum-chaos-enterprise-lab/expected_results_v4.md` — prerequisite lines
  in the email and grpc-tls sections updated; verified via `git diff --stat`
  that only prerequisite prose changed (7 and 6 lines respectively), no
  finding/port/severity/requirement-ID text touched.
- Obsidian vault sync (LIVE-03): wrote the full updated `docs/chaos-lab.md`
  body to `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Guides/Chaos-Lab.md`,
  preserving its existing frontmatter with `updated: 2026-08-12` and
  `source: docs/chaos-lab.md`.

Verified: `grep -c "lab.sh certs" docs/chaos-lab.md quantum-chaos-enterprise-lab/README.md`
→ 1 and 2 respectively; `pytest tests/test_cli_correctness.py
tests/test_phase135_docs_presence.py tests/test_phase136_docs_presence.py -q -m ""`
→ 18 passed, 3 xfailed (0 failed); vault note exists with the expected
frontmatter.

### Task 3 — CONTRIBUTING.md Docker warning (D-14)

Added a new "Docker containers during `-m \"\"` runs" subsection to
`CONTRIBUTING.md`, immediately after "Running the test suite" and before "What
green means" — matching the existing document's voice. States that `pytest -q
-m ""` starts Docker containers for `slow`-marked chaos-lab tests when Docker is
reachable (intentional — CI's `ubuntu-latest` runner has Docker preinstalled),
that the tests tear themselves down via `./lab.sh down`, that a bare `pytest -q`
deselects them, and that `./lab.sh certs` can pre-generate profile certs. No
Obsidian sync was added for `CONTRIBUTING.md` (per D-08, it is a standalone
root file, not one of the mapped `docs/` → vault pairs).

Verified: `grep -ci docker CONTRIBUTING.md` → 5; all five pre-existing sections
("Running the test suite", "What green means", "Why some tests are
quarantined", "CI", "Before you open a PR") still present;
`pytest tests/test_cli_correctness.py -q -m ""` → 5 passed, 1 xfailed.

## Task Commits

| Task | Commit | Message |
|---|---|---|
| 1 | `693c19a` | `feat(150-05): add idempotent per-profile chaos-lab cert generation (D-12, D-13)` |
| 2 | `71f9174` | `docs(150-05): sync chaos-lab doc surfaces to new cert auto-generation` |
| 3 | `54dced4` | `docs(150-05): warn contributors that pytest -q -m "" starts Docker containers (D-14)` |

## Deviations from Plan

**None requiring Rule 1-4 action beyond the environment cleanup already
documented above.** The `labs/grpc-tls/certs/` empty-directory cleanup was
filesystem-only (untracked/gitignored paths), not a Rule 1-4 code change — it
was necessary for the plan's own new cert-generation logic to run correctly on
this machine and is exactly the pre-fix symptom Category E describes.

## Issues Encountered

None beyond the environment artifact noted above.

## User Setup Required

None. `ensure_profile_certs()` is Docker-free and requires only `openssl`
(already a prerequisite of `ensure_lab_certs()`).

## Next Phase Readiness

Category E (chaos-lab `email` profile Docker bind-mount failure) is closed at
the source for both `email` and `grpc-tls` (D-12/D-13 proactive extension).
Plan 150-06 (same wave, sequential execution since worktrees are disabled)
touches no files this plan modified — no conflict risk. Remaining phase scope
(Categories B/C/D/F skip guards, D-15 gitignored-planning-dir guards, and the
eventual live-fire CI re-run) is unaffected by this plan's changes.

## Self-Check: PASSED

- `tests/test_lab_profile_certs.py` — FOUND, contains `dovecot` (`grep -c
  dovecot` → 3), 4 tests pass
- `quantum-chaos-enterprise-lab/lab.sh` — FOUND, `ensure_profile_certs` count
  = 5 (definition + up + all + reset + certs arm)
- Commit `693c19a` — FOUND via `git log --oneline --all | grep 693c19a`
- Commit `71f9174` — FOUND via `git log --oneline --all | grep 71f9174`
- Commit `54dced4` — FOUND via `git log --oneline --all | grep 54dced4`
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Guides/Chaos-Lab.md` — FOUND,
  `source: docs/chaos-lab.md` present, `updated: 2026-08-12`
- `git status --porcelain labs/ | grep -c "certs/"` — `0` (confirmed)
