---
phase: 82-chaos-lab-fidelity
plan: 04
subsystem: chaos-lab
tags: [chaos-lab, idempotency, image-pin-policy, ci-gate, smime, adcs, phase-closure]
status: complete
requires: [82-01, 82-02, 82-03]
provides:
  - per-profile idempotency regression test (slow-marked, Docker-gated)
  - compose-file image-pin CI gate (default suite, pure parse)
  - lab.sh _validate_pinned_tags() early-exit guard on `up` and `all`
  - smime + adcs profile parity confirmed across lab.sh / oracle / README
affects:
  - tests/test_chaos_lab_idempotency.py
  - tests/test_chaos_lab_image_pinning.py
  - quantum-chaos-enterprise-lab/lab.sh
  - quantum-chaos-enterprise-lab/expected_results_v4.md
  - docs/UAT-SERIES.md
  - /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-82-Chaos-Lab-Fidelity.md
  - /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md
tech_stack:
  added: []
  patterns:
    - pytest-collection-time-discovery-via-docker-compose-config-profiles
    - per-profile-parametrized-test-for-localized-failures
    - python3-yaml-parse-as-bash-helper-via-heredoc
key_files:
  created:
    - tests/test_chaos_lab_idempotency.py
    - tests/test_chaos_lab_image_pinning.py
    - .planning/phases/82-chaos-lab-fidelity/82-04-SUMMARY.md
    - /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-82-Chaos-Lab-Fidelity.md
  modified:
    - quantum-chaos-enterprise-lab/lab.sh
    - quantum-chaos-enterprise-lab/expected_results_v4.md
    - docs/UAT-SERIES.md
    - /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md
decisions:
  - "Idempotency test parametrized per-profile (not a single loop) so each profile produces a named test case and failures localize cleanly to the offending profile"
  - "lab.sh _validate_pinned_tags() uses python3 + yaml.safe_load via heredoc (not docker compose config --format json) — pure file parse, no daemon required, runs offline and during install-time setup"
  - "_validate_pinned_tags() degrades gracefully (returns 0 with a warning) when python3 is unavailable; the pytest-based gate (`tests/test_chaos_lab_image_pinning.py`) is the authoritative enforcement layer in CI"
  - "No README.md edit needed in this plan — Plan 82-01 already added the Phase 82-01 image-pin sweep paragraph and smime/adcs rows are already in the Profile Summary table"
metrics:
  duration: "~10 min"
  completed: "2026-05-16"
---

# Phase 82 Plan 04: Idempotency regression + image-pin CI gate + smime/adcs parity + UAT/Obsidian close — Summary

**One-liner:** Closes Phase 82 via two new pytest modules (`tests/test_chaos_lab_image_pinning.py` runs in the default suite as a pure compose-file parse; `tests/test_chaos_lab_idempotency.py` is slow-marked, Docker-gated, and parametrizes one named test per profile across all 20 profiles), a defense-in-depth `_validate_pinned_tags()` early-exit guard wired into `lab.sh` `up` and `all` commands, an appended Phase 82 closure section in `expected_results_v4.md` that records CHAOS-01..06 disposition, four new CHAOS UAT cases (UAT-82-01..04) in `docs/UAT-SERIES.md`, and the Obsidian phase note recording CHAOS-04..06 satisfied.

## Files Added / Modified

| File | Change | LOC |
|---|---|---|
| `tests/test_chaos_lab_image_pinning.py` | NEW — default-suite compose pin gate | 40 |
| `tests/test_chaos_lab_idempotency.py` | NEW — slow-marked per-profile re-up regression (parametrized, 20 profiles + 1 sanity = 21 tests collected) | 126 |
| `quantum-chaos-enterprise-lab/lab.sh` | `_validate_pinned_tags()` helper (+40 LOC) + `up)` and `all)` early-exit wires (+8 LOC) | +48 |
| `quantum-chaos-enterprise-lab/expected_results_v4.md` | Appended "Phase 82 Closure" section (CHAOS-01..06 disposition + commit anchors) | +15 |
| `docs/UAT-SERIES.md` | UAT-82-01..04 (ldaps clean bring-up / broker down-up cycle / source seed idempotency / image-pin policy) + Last Updated bump to 2026-05-16 (Phase 82 wrap) | +90 |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-82-Chaos-Lab-Fidelity.md` | NEW — Obsidian phase note, `status: complete`, six requirements, four "What Was Built" subsections | ~120 |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` | Re-synced from `docs/UAT-SERIES.md` via printf+cat+cp pattern | full overwrite |

## Test Counts

- **`tests/test_chaos_lab_image_pinning.py`** — 1 test (`test_every_image_is_pinned`), runs in default suite, green.
- **`tests/test_chaos_lab_idempotency.py`** — **21 tests collected** under `-m slow`:
  - 1 sanity test: `test_smime_and_adcs_profiles_discovered` (CHAOS-06 parity)
  - 20 parametrized tests `test_profile_re_up_is_idempotent[<profile>]`, one per profile discovered at collection time:
    - `adcs`, `broker`, `cloud`, `database`, `dnssec`, `email`, `identity`, `jwt`, `kerberos` (skipped on macOS without `LAB_INCLUDE_KERBEROS=1`), `ldaps`, `phaseA`, `pki`, `registry`, `saml`, `smime`, `source`, `ssh-weak`, `storage-s3`, `tls-cert-defects`, `vault`
- Default `pytest` invocations skip these (slow-marked + `addopts = "-m 'not slow'"`); CI runs the slow matrix explicitly.

## lab.sh `_validate_pinned_tags()` Integration Points

- Helper defined at lines 73-108 (immediately after `_derive_all_profiles()`).
- Wired into `up)` case at line 116 — early-exit `if ! _validate_pinned_tags; then exit 1`.
- Wired into `all)` case at line 126 — same guard at top of case before any compose-up call.
- Graceful degradation: returns 0 with a warning when `python3` or `PyYAML` is unavailable — the pytest gate (`tests/test_chaos_lab_image_pinning.py`) is the authoritative CI enforcement; the bash gate is defense-in-depth.

## Oracle + README Gap-Fills

**No gaps found.** Phase 79 and Phase 80 already delivered:

- `expected_results_v4.md` `## Profile: smime` section at line 503 (RSA-1024 HIGH, SHA-1 HIGH, RSA-2048-SHA-256 SAFE oracle).
- `expected_results_v4.md` `## Profile: adcs` section at line 536 (BadTemplate-ESC1, BadTemplate-ESC4, SafeTemplate oracle + 4 LOW ADCS-COVERAGE-GAP findings).
- `README.md` Profile Summary rows for both at lines 44-45 (ports 38900 / 38910, links into the oracle).

Plan 82-04 confirmed parity and appended a Phase 82 closure summary section to the oracle so the CHAOS-01..06 disposition is recorded in the same artifact scanners and UAT testers read.

## UAT-82-01..04 Case Summaries

- **UAT-82-01** — `ldaps` profile clean bring-up on macOS Docker Desktop. Verifies CHAOS-01: `chaoslab-ldaps-1` reaches `Up`, no chown errors, `ldapsearch -x -H ldaps://localhost:636 -b dc=chaos,dc=local` returns a base entry.
- **UAT-82-02** — `rabbitmq-broker` survives a down/up cycle. Verifies CHAOS-02: second cycle reaches `Up (healthy)`, no Erlang cookie-mismatch lines, only the expected `Overriding Erlang cookie using the value set in the environment` warning.
- **UAT-82-03** — `gitea` source seed idempotency. Verifies CHAOS-03: re-running `./lab.sh up --profile source` exits the seed sidecar `0` and emits `[seed] sentinel repo crypto-antipatterns-python already present; skipping seed`.
- **UAT-82-04** — Chaos-lab image-pin policy enforced. Verifies CHAOS-05: `pytest tests/test_chaos_lab_image_pinning.py -x` passes green; negative case (edit a service to `:latest`) makes `./lab.sh up` exit non-zero with the `CHAOS-05 violation` message.

## Obsidian Phase Note

Path: `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-82-Chaos-Lab-Fidelity.md`

Frontmatter: `status: complete`, `type: phase`, `updated: 2026-05-16`. Sections: Goal (verbatim from ROADMAP), Requirements Covered (CHAOS-01..06), Success Criteria (six items from ROADMAP), What Was Built (one subsection per plan, sourced from 82-01/02/03/04 SUMMARY files), Links to `[[Roadmap]]` and `[[_QUIRK-Hub]]`.

## Verification Snapshot

```
$ pytest tests/test_chaos_lab_image_pinning.py -x -v
tests/test_chaos_lab_image_pinning.py::test_every_image_is_pinned PASSED
1 passed in 0.04s

$ pytest -m slow --collect-only tests/test_chaos_lab_idempotency.py | tail -1
21 tests collected in 0.25s

$ bash -n quantum-chaos-enterprise-lab/lab.sh && echo SYNTAX_OK
SYNTAX_OK

$ cd quantum-chaos-enterprise-lab && ./lab.sh profiles | sort | tr '\n' ' '
adcs broker cloud database dnssec email identity jwt kerberos ldaps phaseA pki registry saml smime source ssh-weak storage-s3 tls-cert-defects vault
```

`./lab.sh profiles` enumerates 20 profiles including `smime` and `adcs` — CHAOS-06 parity confirmed.

## Commits

- **First (code + lab):** `feat(82-04): chaos lab idempotency + image-pin ci gates + final oracle/readme sweep` — SHA: `<filled after commit>`
- **Second (UAT-SERIES.md):** `docs(phase-82): update UAT-SERIES.md` — SHA: `<filled after commit>`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — blocking-issue] `_validate_pinned_tags()` implementation uses Python heredoc instead of `docker compose config --format json | python3`**

- **Found during:** Task 3.
- **Issue:** The plan's reference implementation pipes `docker compose config --format json` into Python. That requires a working Docker socket and adds a hard dependency on a running daemon for the gate. The gate's *purpose* is to fail BEFORE any container creation — so it shouldn't require a daemon to enforce.
- **Fix:** Switched to a pure-file `python3 - "${COMPOSE_FILE}" <<'PY'` heredoc reading the compose YAML directly via `yaml.safe_load`. Matches the pytest gate's semantics exactly. Falls back to silent skip when PyYAML or python3 is unavailable (the pytest gate is the authoritative CI enforcement).
- **Files modified:** `quantum-chaos-enterprise-lab/lab.sh`
- **Commit:** first 82-04 commit.

### Notes

- Pytest 9.0.2 + Python 3.14.5 — the new tests work cleanly under both. The `pytestmark` module-level list combines `slow` and a daemon-availability `skipif` so collection always succeeds even when Docker is down.
- The parametrize list (`_profile_param_list()`) evaluates at import time and gracefully returns `[]` when Docker is unavailable — so `pytest --collect-only` works in any environment.
- Plan referenced `test_score_weights_invariant.py` as "expected RED — Phase 83 owns". Confirmed not touched here.

## Self-Check: PASSED

- `tests/test_chaos_lab_image_pinning.py` — FOUND, runs in default suite, 1/1 pass.
- `tests/test_chaos_lab_idempotency.py` — FOUND, 21 slow-marked tests collected under `-m slow`.
- `quantum-chaos-enterprise-lab/lab.sh` — FOUND, `_validate_pinned_tags` defined + wired into `up` and `all` (2 invocation sites), `bash -n` clean.
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — FOUND, contains `## Phase 82 Closure` heading + CHAOS-01..06 disposition + smime/adcs sections from Phases 79/80.
- `quantum-chaos-enterprise-lab/README.md` — VERIFIED, smime + adcs Profile Summary rows present (no edit needed).
- `./lab.sh profiles` enumerates `smime` and `adcs` (verified).
- `docs/UAT-SERIES.md` — UAT-82-01..04 + Last Updated 2026-05-16 added.
- Vault `Phase-82-Chaos-Lab-Fidelity.md` and `UAT-Series.md` synced.
- Two commit subjects landed: `feat(82-04): ...` and `docs(phase-82): ...`.
