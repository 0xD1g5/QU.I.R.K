---
phase: 90-oqs-nginx-pqc-hybrid
plan: "04"
subsystem: docs/oracle/tests
tags: [pqc, oracle, discriminator, uat, obsidian, phase-completion]
dependency_graph:
  requires: [90-01, 90-02, 90-03]
  provides: [D-04-oracle, discriminator-regression, UAT-90-04-01, phase-90-obsidian-note]
  affects:
    - quantum-chaos-enterprise-lab/expected_results_v4.md
    - tests/test_pqc_discriminator.py
    - docs/UAT-SERIES.md
tech_stack:
  added: []
  patterns: [oracle-footnote, discriminator-regression, uat-documentation, obsidian-sync]
key_files:
  created:
    - tests/test_pqc_discriminator.py
  modified:
    - quantum-chaos-enterprise-lab/expected_results_v4.md
    - docs/UAT-SERIES.md
decisions:
  - "D-04 oracle documents canonical baseline 18 + live-observed 17 footnote; PQC uplift claim holds for both"
  - "Discriminator negative arm uses mocked subprocess (host OpenSSL 3.6.2 supports X25519MLKEM768 natively — a live Python TLS server would be indistinguishable from a PQC server)"
  - "Positive live arm skips cleanly when oqs-nginx lab profile is not running"
metrics:
  duration_seconds: 360
  completed_date: "2026-05-22"
  tasks_completed: 2
  files_changed: 3
---

# Phase 90 Plan 04: D-04 Consulting Demo Oracle + Discriminator Regression + Phase Completion Summary

**One-liner:** Finalized oqs-nginx expected_results oracle (genuine-component + advisory paths, D-04 agility before/after 18 → 25 with live footnote at 17); 9-test false-positive-free discriminator regression locks the headline PQC claim; all four CLAUDE.md phase-completion steps satisfied.

## What Was Built

### Task: Oracle footnote (live 17 vs canonical 18)

Per the `<oracle_footnote_instruction>` from the continuation prompt: added a brief footnote/parenthetical to the `## Profile: oqs-nginx` before/after agility table in `expected_results_v4.md` noting that the live `tls-modern` classical baseline observed agility **17** (RSA-only posture) while the canonical oracle documents **18** (50% HIGH finding ratio reference). The PQC uplift holds either way — live oqs-nginx returned agility **25**, strictly exceeding both. The canonical 18 row remains the documented reference.

The discriminator test `tests/test_pqc_discriminator.py` was already fully committed in the pre-checkpoint Task 1 commit (`15229bc`): 9 tests across three classes (positive live, negative mocked classical, mocked positive), all passing.

**Commit:** `0d25379`

### Task 2: Mandatory phase-completion steps (CLAUDE.md)

**Step 1 — Obsidian phase note finalized:**
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-90-OQS-Nginx-PQC-Hybrid.md` — updated from `status: active` to `status: complete`.
- All four plan subsections filled in with substantive "What Was Built" content drawn from the 90-01/02/03/04 SUMMARY files.
- Phase summary paragraph capturing the end-to-end PQC-01/02/03 story added.
- Written directly to the vault filesystem (not via CLI `content=` — file too large for shell expansion per CLAUDE.md).

**Step 2 — docs/UAT-SERIES.md updated:**
- `**Last Updated:**` line updated to document Phase 90 COMPLETE with all four plan UAT closures.
- Three new test cases appended to UAT Series 90:
  - `UAT-90-02-01` — PQC probe detection + classifier alias + evidence counter (PQC-02); 19 automated tests pass.
  - `UAT-90-03-01` — Agility PQC-hybrid bonus 8.0; scoring uplift 18 → 25; invariant 37/283.0; 12 automated tests pass.
  - `UAT-90-04-01` — D-04 consulting before/after oracle + discriminator regression; 9 tests pass; human-verify PASSED with live agility 25 vs 17.

**Step 3 — UAT-SERIES.md synced to Obsidian:**
- `printf/cat/cp` pattern per CLAUDE.md → `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` updated.

**Step 4 — docs/UAT-SERIES.md committed via gsd-tools:**
- Commit `325ac30` via `node gsd-tools.cjs commit "docs(phase-90): update UAT-SERIES.md"`.

## Deviations from Plan

### Oracle footnote addition

**Finding during continuation:** The human-verify checkpoint was approved with the note that the live `tls-modern` scan returned agility 17 (RSA-only posture) while the oracle canonical value is 18. Per the `<oracle_footnote_instruction>`, a brief footnote was added to the D-04 before/after table keeping the oracle faithful to observed scanner output (CLAUDE.md: "if detection logic changes, update expected_results accordingly"). This is a minor oracle clarification, not a logic change.

## Verification Results

- `QUIRK_DB_PATH=:memory: python -m pytest tests/test_pqc_discriminator.py -q` — **9 passed**
- `QUIRK_DB_PATH=:memory: python -m pytest tests/test_pqc_probe.py tests/test_pqc_agility_bonus.py tests/test_score_weights_invariant.py -q` — **31 passed** (combined full PQC regression: 40 total)
- `python -m compileall quirk run_scan.py -q` — **clean**
- `grep -q 'X25519MLKEM768' expected_results_v4.md && echo OK` — **OK**
- `grep -q 'oqs-nginx' docs/UAT-SERIES.md && echo OK` — **OK**
- Obsidian phase note exists at vault path — **FOUND**
- UAT-Series.md synced to vault — **DONE**

## Known Stubs

None — the oracle, discriminator tests, UAT cases, and Obsidian note are all fully populated. No TODO markers or placeholder text remain in any Plan 04 deliverable.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced in Plan 04. Documentation and test changes only. No threat flags to report.

## Self-Check: PASSED

- `quantum-chaos-enterprise-lab/expected_results_v4.md` contains live-run footnote — FOUND
- `tests/test_pqc_discriminator.py` — FOUND (pre-checkpoint commit `15229bc`)
- `docs/UAT-SERIES.md` contains `oqs-nginx`, `UAT-90-02-01`, `UAT-90-03-01`, `UAT-90-04-01` — FOUND
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-90-OQS-Nginx-PQC-Hybrid.md` status: complete — FOUND
- `0d25379` (oracle footnote commit) — FOUND in git log
- `325ac30` (UAT-SERIES.md commit) — FOUND in git log
