---
phase: 194-advanced-scan-fields-executive-verdict-phantom-cert-fix
plan: 08
subsystem: docs/planning
tags: [parity-audit, horizon-ledger, full-suite-gate]
dependency-graph:
  requires: [194-06, 194-05, 194-02]
  provides: [194-PARITY-AUDIT.md]
  affects: [".planning/HORIZON.md 999.104/999.106 rows"]
tech-stack:
  added: []
  patterns: ["source-derived enumeration over carried-forward estimate (per CLAUDE.md TOOL section's standing lesson)"]
key-files:
  created:
    - .planning/phases/194-advanced-scan-fields-executive-verdict-phantom-cert-fix/194-PARITY-AUDIT.md
    - .planning/phases/194-advanced-scan-fields-executive-verdict-phantom-cert-fix/deferred-items.md
  modified:
    - .planning/HORIZON.md
decisions: []
metrics:
  duration: "~55 minutes"
  completed: "2026-09-09"
---

# Phase 194 Plan 08: CLI-vs-dashboard field parity audit + phase gate Summary

D-15's full CLI-config-vs-dashboard-form field parity audit, closing 999.104's tier 1-3 evidence
requirement with a counted, source-derived field universe — not the PM-era "~138 fields" estimate.

## What Was Built

**Task 1 — `194-PARITY-AUDIT.md`.** Enumerated every operator-settable field by reading
`quirk/config_template.yaml` and `quirk/config.py`'s 9 dataclasses (`AssessmentCfg`, `TimeoutsCfg`,
`RetryCfg`, `ScanCfg`, `TargetsCfg`, `ConnectorsCfg`, `OutputCfg`, `IntelligenceCfg`, `SecurityCfg`)
plus `AppConfig`'s 2 top-level dict fields (`broker_credentials`, `remediation_aliases`) at audit
time, git SHA `9af9d038bd7b4f207f3641cf31d6872c9e929a35`. **Counted field universe: 121
operator-settable fields** (`IntelligenceCfg.intelligence_version` excluded — it is
version-derived, never operator-set). Reconciliation finding: `config_template.yaml` documents
every dataclass field via a comment or example EXCEPT `scan.timeouts`/`scan.retry`'s 17 fields,
which have no template-level documentation at all (a doc gap, not a code defect — their defaults
live only in the dataclass field defaults).

150 table rows tabled against dashboard coverage (`Status`: `covered`/`covered-indirectly`/
`intentional-gap`/`not-yet-covered`), tallying to **35 covered, 6 covered-indirectly, 15
intentional-gap, 65 not-yet-covered** (35+6+15+65=121, cross-checked against the 121-field
enumeration). `ports_ssh` — which is NOT a real `config.py` field anywhere in the codebase
(confirmed by `grep -rn "ports_ssh" quirk/ src/dashboard/src/` returning zero hits outside
source-comment explanations of its absence) — is recorded in the Intentional-gaps section with the
required reason ("no CLI-side equivalent exists to achieve parity with — SSH targets derive from
protocol-classified open ports during discovery"), cross-referenced to backlog ledger item
999.106.

Tier roll-up against 999.104: **Tier 1 (visibility) CLOSED** — `EffectiveConfigPanel` renders the
server-resolved effective config for every `covered`/`covered-indirectly` field. **Tier 2
(connector parity) PARTIALLY CLOSED** — all 25 `enable_*` flags dispositioned (22 covered via
`ConnectorsPanel`, 3 intentional-gap: `enable_codesign`/`enable_authenticated_mode`/
`enable_recurring_otics`, each CLI-flag- or scheduler-driven per the template's own disposition
comments), but only 6 of 46 credential/endpoint/target sub-fields are covered or
covered-indirectly (3 more intentional-gap, 37 not-yet-covered) — the residue is concentrated in
per-connector target lists (`jwt_targets`, `container_targets`, `source_targets`, and every
identity-connector `*_targets` field), meaning several connectors are dashboard-toggleable but
inert without a target list the form has no field for. **Tier 3 (scan-behavior parity) PARTIALLY
CLOSED** — 7 covered + 1 covered-indirectly of the 30 `scan.*`/`timeouts.*`/`retry.*` fields (the
exact set 194-05's `AdvancedPanel` plan text scoped), 22 not-yet-covered (11 per-scanner timeouts,
4 concurrency knobs, 2 retry-backoff, misc). **Tier 4 (config-file parity) confirmed explicitly OUT
of scope** — no server-side `config.yaml` write route exists. The audit states the honest partial
verdict plainly rather than asserting closure the table does not support, per the plan's own
instruction.

**Task 2 — HORIZON.md ledger update + full-suite gate.** Rewrote the `999.104` row to cite
`194-PARITY-AUDIT.md` by path and replace the "~138 YAML fields / 6 knobs" characterization with
the audit's counted figures and tier verdicts; a second stale "~138 YAML fields" mention in the
v5.21 milestone-boundary rationale log row (a historical PM-decision record, not the 999.104 row
itself) was also updated with a forward pointer ("later audited at 194-08 to 121 real
operator-settable fields") rather than deleted, preserving the historical record while satisfying
the phase's own acceptance criterion that zero live occurrences of the stale phrase remain. The
`999.106` row's own text was left as filed (per plan instruction) and gained one added sentence
pointing to the audit's ports_ssh intentional-gap entry. No `state.*`/`phase.complete`/
`milestone.complete`/`requirements mark-complete` verb was invoked; `git status --short
.planning/STATE.md .planning/ROADMAP.md .planning/REQUIREMENTS.md` confirms zero changes to any of
the three excluded files across this plan's commits.

**Phase gate results (all run with `.venv/bin/python`, the project venv per CLAUDE.md's known
system-python gotcha):**
- `.venv/bin/python -m compileall -q quirk` — exit 0.
- `.venv/bin/python -m pytest -q -m ""` — **4719 passed, 42 skipped, 72 xfailed, 5 xpassed, 1
  failed**, 1080.81s. The single failure,
  `tests/test_backlog_reconciliation_gate.py::test_full_corpus_local_only_leg`, is a pre-existing,
  out-of-scope finding (see "Deferred Issues" below) — confirmed unrelated to this plan's changes
  (`git log --oneline -- .planning/milestones/v5.20-phases/189-config-correctness-drain/` shows no
  194-08 commits touching that path) and reproduced individually.
- `cd src/dashboard && npm run build && npm run lint && npm run test` — all exit 0: build produces
  8 asset chunks with zero errors; lint reports 0 errors (1 pre-existing unused-eslint-disable
  warning on an unrelated test file); test suite is 44 files / 313 tests, all green — identical
  counts to 194-05/194-07's last-recorded baseline, confirming this plan added zero frontend
  regressions (it touched no frontend files).

## Deferred Issues

**`test_backlog_reconciliation_gate.py::test_full_corpus_local_only_leg` — pre-existing, out of
scope.** Full detail in
`.planning/phases/194-advanced-scan-fields-executive-verdict-phantom-cert-fix/deferred-items.md`.
Summary: 4 fake/example `BACK-*` IDs (`BACK-1`, `BACK-900`, `BACK-9999`, `BACK-99`) used as worked
examples inside Phase 189's (v5.20) `189-REVIEW.md`/`189-VERIFICATION.md`/`189-03-PLAN.md`/
`189-03-SUMMARY.md` trip the gate's local-only full-corpus leg because they are neither
closed-with-evidence nor listed in `HORIZON.md`. Not fixed here — out of scope for this plan's
file set (Rule scope boundary: only auto-fix issues directly caused by the current task's
changes). Reproduction command and a suggested fix for a future phase are recorded in
`deferred-items.md`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Arithmetic self-correction, not a Rule 1-4 deviation] Corrected the audit's own Summary
counts table and tier-2/tier-3 roll-up numbers before committing.** A first-pass tally of the
150-row table (25/9/13/74) did not match a careful recount (35/6/15/65); both sum to 121, but only
the second is correct against the actual per-row dispositions. Recounted by hand against every row
in the field-by-field table before the Task 1 commit landed — the committed artifact carries the
correct figures throughout (Summary counts, Tier 2/3 roll-up percentages, and the "Remaining
not-yet-covered fields" theme-grouped list all cross-checked to sum to 65/121). No commit of the
incorrect numbers exists in git history — the correction happened before `git commit`, not as a
follow-up fix.

## Self-Check

- `test -f .planning/phases/194-advanced-scan-fields-executive-verdict-phantom-cert-fix/194-PARITY-AUDIT.md` → FOUND
- `test -f .planning/phases/194-advanced-scan-fields-executive-verdict-phantom-cert-fix/deferred-items.md` → FOUND
- `grep -c "^|" 194-PARITY-AUDIT.md` → 150 (>= 30 required)
- `grep -c "ports_ssh" 194-PARITY-AUDIT.md` → 3 (>= 1 required)
- `grep -c "999.104" 194-PARITY-AUDIT.md` → 2 (>= 1 required)
- `grep -c "Tier 4" 194-PARITY-AUDIT.md` → 2 (>= 1 required)
- `grep -c "194-PARITY-AUDIT" .planning/HORIZON.md` → 2 (>= 1 required)
- `grep -c "138 YAML fields" .planning/HORIZON.md` → 0 (required)
- Commits `1e72f1f5`, `47d6fcec`, `d0d4612f` exist in `git log --oneline`: FOUND (all three, verified via `git log --oneline -5` above)

## Self-Check: PASSED
