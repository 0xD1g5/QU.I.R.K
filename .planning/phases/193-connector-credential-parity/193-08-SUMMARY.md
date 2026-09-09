---
phase: 193-connector-credential-parity
plan: 08
subsystem: docs
tags: [documentation, uat, obsidian, connectors, credentials]

requires:
  - phase: 193-connector-credential-parity
    provides: "Connectors panel UI (193-07), submit-time 422 gate + credential env injection (193-06), availability route (193-04), overlay plumbing (193-01/02/03/05)"
provides:
  - "docs/operators-guide.md §3.1.4: Connectors panel operator procedure, GET /api/connectors/availability documentation"
  - "docs/configuration.md: five credential env-var reference table, D-13/D-14 dashboard-toggle precedence rules"
  - "docs/report-interpretation.md: missing-credentials vs disabled-by-config vs missing-extra distinction"
  - "docs/UAT-SERIES.md Series 193: 10 dispositioned UAT cases for PARITY-02/PARITY-03"
  - "Obsidian vault: phase note, hub link, 3 re-synced guides, UAT-Series.md, Roadmap.md, Requirements.md"
affects: [phase-194-planning, future-uat-audit]

tech-stack:
  added: []
  patterns: ["DEFERRED — covered by <test-node> / GAP — no substitute coverage UAT disposition convention"]

key-files:
  created:
    - "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-193-Connector-Credential-Parity.md"
  modified:
    - docs/operators-guide.md
    - docs/configuration.md
    - docs/report-interpretation.md
    - docs/UAT-SERIES.md
    - "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Guides/Operators-Guide.md"
    - "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Guides/Configuration.md"
    - "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Guides/Report-Interpretation.md"
    - "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md"
    - "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/_QUIRK-Hub.md"
    - "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Roadmap.md"
    - "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Requirements.md"

key-decisions:
  - "The initial full-suite run's 9 'failures' (all email/broker-connector 422 rejections in unrelated tests) were an environmental artifact — running with system Python instead of .venv/bin/python (which lacks sslyze) — not a real regression from 193-06's new submit-time gate. Re-ran with .venv/bin/python: 4674 passed, 0 failed."
  - "3 of 10 new UAT cases (cross-component Connectors-panel<->Effective-config integration, missing-credentials end-to-end via the new submission path, D-14 explicit-toggle-beats-custom-scope end-to-end) are honestly dispositioned GAP rather than PASS, since no automated test currently exercises those exact integration paths end-to-end even though the individual halves are each separately covered."

requirements-completed: [PARITY-02, PARITY-03]

duration: 55min
completed: 2026-09-09
---

# Phase 193 Plan 08: Docs, UAT-SERIES, Obsidian Vault Sync, Full-Suite Gate Summary

**Closed the Per-Phase Documentation Checklist for Phase 193's new dashboard connector/credential
surface — three user-facing guides updated, 10 new UAT-193 cases honestly dispositioned (7 PASS to
named tests, 3 GAP), and the full backend+frontend suite confirmed green (4674 passed / 0 failed
backend, 281/281 frontend) after ruling out an environmental false-positive from the wrong Python
interpreter.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3/3 completed
- **Files modified:** 4 repo docs + 1 repo test-doc (UAT-SERIES.md) + 7 vault files (3 guides,
  UAT-Series, phase note, hub, Roadmap, Requirements)

## Accomplishments

### Task 1 — Operator, configuration, report-interpretation doc updates
- `docs/operators-guide.md` gained new §3.1.4 "Connectors panel — enabling connectors and
  supplying credentials from the dashboard": category grouping, unavailable-with-reason display,
  server-side 422 enforcement, masked/non-persisted credential entry, ambient-auth cloud note,
  `missing-credentials` non-blocking submission, and documentation of the new auth-gated
  `GET /api/connectors/availability` endpoint (noting `docs/api-reference.md` does not yet exist).
- `docs/configuration.md` gained a five-variable credential env-var reference table
  (`VAULT_TOKEN`, `QUIRK_ADCS_PASSWORD`, `QUIRK_PG_SCANNER_PASSWORD`,
  `QUIRK_MYSQL_SCANNER_PASSWORD`, `QUIRK_SNMP_COMMUNITY`) sourced from `CREDENTIAL_REGISTRY` at
  write time, framed explicitly as CLI-usable, plus a new "Dashboard connector toggles vs.
  custom-port-scope suppression" subsection recording D-13 (delta-only overlay writes) and D-14
  (explicit toggle beats custom-scope suppression) precedence rules.
- `docs/report-interpretation.md`'s existing §22 Scan Coverage section gained a subsection
  distinguishing `missing-credentials` from `disabled-by-config` and `missing-extra` for the new
  dashboard-submittable case of an enabled-but-uncredentialed connector.
- All acceptance-criteria greps/scripted checks pass, including the registry-parity check
  (`CREDENTIAL_REGISTRY` env names all present in `docs/configuration.md`) and the no-real-secret
  grep (the one hit, `QUIRK_AUTH_TOKEN="eyJhbGci..."`, is pre-existing content in an unrelated
  section, not part of this task's edits).

### Task 2 — UAT-SERIES.md cases and Obsidian sync
- Added 10 new `### UAT-193-*` cases covering: category-grouped rendering, unavailable-with-reason
  display, Effective-Config-panel provenance integration (GAP), server-side 422 rejection including
  direct-API bypass, masked/not-saved credential fields, no-leak guarantee, blank-credential
  non-blocking submission + `missing-credentials` skip (GAP), ambient-auth cloud note, D-14
  explicit-toggle-vs-custom-scope precedence (GAP), and D-09 CLI env-var parity.
- 7 cases are `[x] PASS`, each citing a specific currently-passing test node (verified live: all 25
  referenced backend test functions pass, plus all 9 `ConnectorsPanel.test.tsx` vitest cases).
- 3 cases are honestly `[x] SKIP` / `GAP — no substitute coverage`, each naming the closest existing
  coverage and the precise unexercised integration path — no case was checked merely to satisfy the
  gate.
- `tests/test_uat_zero_undispositioned_gate.py` and `tests/test_uat_disposition_integrity.py` both
  pass (9 and 20 passed respectively).
- Synced `docs/UAT-SERIES.md` and the three Task-1-updated guides to the Digs vault filesystem
  directly, each with the standard frontmatter block.

### Task 3 — Full-suite gate and Obsidian phase note
- Backend full suite (`python -m pytest -q -m ""`) initially showed 9 failures, all
  `assert 422 == 201` in unrelated pre-existing tests (`test_job_trusted_targets.py`,
  `test_jobs_nmap_scope_cap.py`, `test_jobs_target_validation.py`,
  `test_scan_submit_request_no_internal.py`) whose job submissions use the `standard` profile,
  which auto-enables email/broker — rejected by 193-06's new submit-time availability gate because
  `sslyze` was unavailable in the invoking interpreter. Root-caused: `python` resolved to the
  system Python 3.14 (no `sslyze` installed), not `.venv/bin/python` (which has it). Re-ran with
  `.venv/bin/python -m pytest -q -m ""`: **4674 passed, 41 skipped, 72 xfailed, 5 xpassed, 0
  failed** — failing-node SET is empty, matching the pre-phase baseline. This was an interpreter
  artifact of this execution session, not a code regression from any 193 plan.
- Frontend: `npm run build` (2441 modules, clean), `npm run lint` (0 errors, 1 pre-existing unused
  eslint-disable warning in the new `ConnectorsPanel.test.tsx`, non-blocking), `npm run test --run`
  (40 files, 281 tests, all passed) — all exit 0.
- Wrote the Obsidian phase note at
  `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-193-Connector-Credential-Parity.md`
  (frontmatter `status: complete`, Goal, Requirements Covered, 3 Success Criteria, 8 "What Was
  Built" subsections — one per plan), linked it from `_QUIRK-Hub.md`'s callout and phase table, and
  re-synced `Roadmap.md`/`Requirements.md` from their `.planning/` sources.
- Did **not** invoke `gsd-sdk query phase.complete` or `gsd-tools.cjs phase.complete` — per
  CLAUDE.md's documented hazard (well-formed-but-wrong completion values without checking plan
  status), phase closure is left to the orchestrator's normal flow.

## Deviations from Plan

### Auto-fixed Issues

None — no code changes were required or made. This plan's `files_modified` scope
(`docs/operators-guide.md`, `docs/configuration.md`, `docs/report-interpretation.md`,
`docs/UAT-SERIES.md`) was followed exactly; no Rule 1/2/3 fixes were needed.

**1. [Rule 3 — investigation, not a fix] Diagnosed and ruled out a false-positive full-suite
regression**
- **Found during:** Task 3
- **Issue:** `python -m pytest -q -m ""` reported 9 failures, all `422` rejections in tests using
  the `standard` profile (which auto-enables email/broker).
- **Root cause:** the invoking `python` resolved to the system interpreter (no `sslyze`), not
  `.venv/bin/python` (has `sslyze`). 193-06's new submit-time availability gate correctly rejected
  those jobs given a real absence of `sslyze` in that interpreter's environment — the gate was
  working as designed, not misbehaving.
- **Resolution:** re-ran with `.venv/bin/python -m pytest -q -m ""`; 0 failures. No source file was
  changed.
- **Files modified:** none.

## Known Stubs

None.

## Threat Flags

None — this plan touched only documentation and the UAT corpus; no new network endpoints, auth
paths, file-access patterns, or schema changes were introduced.

## Self-Check: PASSED

- `docs/operators-guide.md`, `docs/configuration.md`, `docs/report-interpretation.md`,
  `docs/UAT-SERIES.md` — FOUND, diffs confirmed present via `git show`.
- Commits `0d3742a3` (Task 1) and `e3fd6f37` (Task 2) — FOUND in `git log`.
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-193-Connector-Credential-Parity.md` —
  FOUND, mtime 2026-09-09.
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/{UAT-Series.md,Roadmap.md,Requirements.md,Guides/
  Operators-Guide.md,Guides/Configuration.md,Guides/Report-Interpretation.md}` — all FOUND, mtime
  2026-09-09, all start with `---` frontmatter.
- `_QUIRK-Hub.md` references `Phase-193-Connector-Credential-Parity` twice (callout + table row) —
  confirmed via grep.
