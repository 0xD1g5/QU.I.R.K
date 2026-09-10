---
phase: 194-advanced-scan-fields-executive-verdict-phantom-cert-fix
plan: 07
subsystem: docs
tags: [documentation, uat, obsidian, configuration, report-interpretation, operators-guide]

# Dependency graph
requires:
  - phase: 194-02
    provides: AdvancedScanFields backend overlay (field names, bounds, D-19/D-21 vocabulary)
  - phase: 194-03
    provides: Executive Verdict layer (band mapping, cap-reason string, honest-absence wording)
  - phase: 194-04
    provides: phantom-cert disclosure line + D-14 empty-state wording
  - phase: 194-05
    provides: Advanced scan-fields panel UI (field set, D-16/D-18 shape)
  - phase: 194-06
    provides: operator walkthrough dispositions (10/13 steps PASS, 3 honest GAP) transcribed into Series 194
provides:
  - One canonical "Dashboard form vs. presets precedence" section in docs/configuration.md (D-16)
  - Advanced scan-fields reference table + D-18/D-19/D-21 research-corrected notes
  - docs/operators-guide.md §3.1.5 Advanced panel operating instructions
  - docs/report-interpretation.md §19.5 Executive Verdict + §19.6 Certificate inventory completeness (D-17)
  - docs/UAT-SERIES.md Series 194 (12 cases, 9 PASS / 3 honest GAP)
  - Obsidian vault sync for all four touched docs
affects: [194-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One canonical precedence section (D-16) referenced by, not duplicated in, per-panel notes"
    - "UAT cases transcribed verbatim from an operator walkthrough SUMMARY, never re-derived or upgraded to PASS on test-suite evidence alone (T-194-20)"

key-files:
  created: []
  modified:
    - docs/configuration.md
    - docs/operators-guide.md
    - docs/report-interpretation.md
    - docs/UAT-SERIES.md

key-decisions:
  - "D-16's canonical precedence section replaces the prior connectors-only precedence prose header; the per-panel D-13/D-14 notes now cross-reference it instead of restating the mechanism"
  - "Series 194's 3 GAP cases (cap reason positive branch, honest-absence card, certificate positive-count branches) are NOT upgraded to PASS despite unit-test corroboration — T-194-20 requires a GAP stay GAP when the operator didn't visually confirm it"
  - "Did not call phase.complete, milestone.complete, or requirements mark-complete — all three are recorded unsafe on this machine (CLAUDE.md TOOL-01/05, project_gsd_phase_complete_premature)"

patterns-established: []

requirements-completed: []

# Metrics
duration: 1 session
completed: 2026-09-09
---

# Phase 194 Plan 07: Documentation, UAT Series 194 & Obsidian Sync Summary

**Four docs updated (configuration.md's canonical D-16 precedence section + advanced-field reference, operators-guide.md's Advanced panel instructions, report-interpretation.md's Executive Verdict + certificate-completeness sections, and UAT-SERIES.md's Series 194 with 9 PASS / 3 honest GAP transcribed from the 194-06 operator walkthrough) — all four synced to the Obsidian vault.**

## Performance

- **Duration:** 1 session, 3 tasks
- **Tasks:** 3 (Task 1: configuration.md + operators-guide.md; Task 2: report-interpretation.md; Task 3: UAT-SERIES.md + Obsidian sync)
- **Files modified:** 4 docs files + this SUMMARY

## Accomplishments

### Task 1 — Canonical precedence + advanced-field reference (D-16/D-18/D-19/D-21)

`docs/configuration.md` gained a single canonical `### Dashboard form vs. presets precedence`
section (D-16) covering both the Connectors panel and the Advanced scan-fields panel: delta-only
writes, `_user_set_fields` beating profile/preset defaults, overlay-merged-last beating port-scope
defaults, and the Effective Config preview resolving through the identical real load path the scan
uses. The prior connectors-only D-13/D-14 precedence prose now opens by cross-referencing this
section rather than restating the mechanism. A new "Advanced scan-fields reference" table lists all
8 shipped fields (YAML path, accepted values/bounds, default), with three explicit research-corrected
notes: D-19 (`tls_enum_mode` has no `off` behavior — `tls_scanner.py` coerces anything outside
`{fast, deep}` to `fast`), D-21 (`data_classification`'s exact four-value vocabulary, matching
`_DATA_CLASS_MAP`), and D-18 (no SSH port list exists anywhere — SSH targets derive from
protocol-classified open ports during discovery, tracked as backlog 999.106 if ever wanted).
`docs/operators-guide.md` gained a new §3.1.5 immediately after the Connectors §3.1.4 material,
covering the Advanced section's collapsed-by-default placement, its 8 controls, the
advisory-client/authoritative-server 422 relationship, and the live Effective Config preview
refresh — cross-referencing configuration.md's precedence section rather than duplicating it.

### Task 2 — Executive Verdict + certificate-honesty sections (D-17)

`docs/report-interpretation.md` gained §19.5 "Executive Verdict" (band mapping table
EXCELLENT/GOOD->QUANTUM-READY green, MODERATE/FAIR->PARTIALLY READY amber, POOR->NOT
QUANTUM-READY red; the band-comes-from-rating-not-score guarantee tied to §19's severity floor;
the `Score capped: <reason>` inline note; and the honest-absence
`Verdict not available for this scan (pre-v5.21 data).` wording explicitly framed as "not a poor
result") and §19.6 "Certificate inventory completeness" (only-real-certificates rule, the
`N TLS endpoints failed handshake and are not shown.` disclosure line sourced from the
server-authoritative `excluded_cert_count`, and the reconciliation reading for `No TLS certificates
discovered in this scan` appearing alongside a non-zero exclusion count — a real TLS-reachable-but-
zero-handshake finding, not an empty scan).

### Task 3 — Series 194 UAT cases, header refresh, Obsidian sync

`docs/UAT-SERIES.md` gained `## Series 194: Advanced Scan Fields, Executive Verdict &
Phantom-Cert Fix (Phase 194 — v5.21)` with 12 `### UAT-194-NN` cases, one per surface behavior
this phase shipped (Advanced panel placement/provenance/422 rejection/dropdown vocabularies,
Executive Verdict default render/rating-not-score band/cap-reason/honest-absence, certificate
row-integrity/print-parity/empty-state). Every disposition is transcribed directly from
`194-06-SUMMARY.md`'s operator walkthrough table: 9 cases `[x] PASS` (UAT-194-01 through -07, -11,
-12) citing the operator's "Approved" confirmation plus corroborating unit-test nodes; 3 cases
(`UAT-194-08` cap-reason positive branch, `UAT-194-09` honest-absence card, `UAT-194-10`
certificate positive-count branches) `[x] SKIP` with `GAP — no substitute coverage`, naming the
exact live-data condition (`rating: GOOD` not null, `rating_cap_reason: null`,
`excluded_cert_count: 0`) that made the positive branch unexercisable, per T-194-20's
never-upgrade-a-GAP-on-test-evidence-alone rule. The document header's `**Last Updated:**` line was
refreshed with a Phase 194 note (today's date, series name, 9/3 PASS/GAP split), prepended ahead of
the existing Phase 192 note — Phase 193's own header-refresh step appears to have been skipped by
that plan; this plan does not attempt to backfill it, only adds its own entry correctly. All four
touched docs (`configuration.md`, `operators-guide.md`, `report-interpretation.md`,
`UAT-SERIES.md`) were synced directly to the vault filesystem at
`/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/` with standard frontmatter
(`project`/`type`/`status`/`source`/`updated: 2026-09-09`) via the printf+cat pattern (not CLI
`content=`, per CLAUDE.md — the files are too large for shell-expanded content parameters).
`Configuration.md` and `Report-Interpretation.md` were found already synced (byte-identical body,
apparently from an earlier partial run of this same plan); `Operators-Guide.md` and `UAT-Series.md`
were not yet current and were freshly written.

## Verification

```
.venv/bin/python -m pytest tests/test_uat_zero_undispositioned_gate.py tests/test_uat_disposition_integrity.py -q
```
-> **29 passed, 5 deselected** (0 failures). Both UAT corpus-integrity gates green.

Acceptance criteria checked directly:
- `grep -c "Dashboard form vs. presets precedence" docs/configuration.md` -> `1`
- `grep -n "tls_enum_mode" docs/configuration.md` -> 5 lines; `grep -c "coerce" docs/configuration.md` -> `4`
- `grep -c "regulated" docs/configuration.md` -> `4`; `grep -ci "restricted" docs/configuration.md` -> `0`
- `grep -c "ports_ssh\|SSH port list" docs/configuration.md` -> `2`
- `grep -ci "advanced" docs/operators-guide.md` -> `6`
- `grep -c "Executive Verdict" docs/report-interpretation.md` -> `2`
- `grep -c "Verdict not available for this scan (pre-v5.21 data)." docs/report-interpretation.md` -> `1`
- `grep -c "Score capped:" docs/report-interpretation.md` -> `1`
- `grep -c "TLS endpoints failed handshake and are not shown" docs/report-interpretation.md` -> `1`
- `grep -c "No TLS certificates discovered in this scan" docs/report-interpretation.md` -> `1`
- `grep -c "^### UAT-194-" docs/UAT-SERIES.md` -> `12`
- All four vault files confirmed present with `updated: 2026-09-09` frontmatter and matching content (line counts and `grep -c` markers checked against the repo source)

## Deviations from Plan

**1. [Rule 1 - minor wording correction]** The initial D-21 note draft used the word "restricted" in
prose (`"there is no restricted value anywhere in the codebase"`), which tripped the plan's own
acceptance criterion (`grep -ci "restricted" docs/configuration.md` must return `0`). Reworded to
"no fifth, legacy-named value exists anywhere in the codebase" before committing — no functional
content lost, same claim stated without the trigger word.

**2. [Rule 1 - cross-reference literal-match fix]** The first draft of the connectors-specific
D-13/D-14 note cross-referenced the canonical section by literally repeating its exact heading text
in prose ("...rule stated in 'Dashboard form vs. presets precedence' above"), which made
`grep -c "Dashboard form vs. presets precedence" docs/configuration.md` return `2` instead of the
required exactly-`1`. Reworded the cross-reference to "the canonical precedence section immediately
above" — same pointer, no literal heading-text duplication.

No other deviations — plan executed as written, including the explicit instruction not to invoke
`phase.complete`, `milestone.complete`, or `requirements mark-complete`.

## Issues Encountered

None blocking. Found (not fixed, out of scope for this plan): Phase 193's own close-out plan
(193-08) added a per-series "Last Updated" paragraph at the *end* of `docs/UAT-SERIES.md` but never
refreshed the *document header's* `**Last Updated:**` line at the top of the file — the header
still read "Phase 192 Plan 11" immediately before this plan's edit. This plan's Task 3 prepends its
own correct Phase 194 entry ahead of the stale Phase 192 text; it does not attempt to retroactively
insert a missing Phase 193 entry, since that would be rewriting another plan's already-committed
work rather than documenting this phase's own changes.

## User Setup Required

None — documentation-only plan, no external service configuration.

## Next Phase Readiness

- All four Per-Phase Documentation Checklist rows this phase triggered (new config options, new
  report surface, new dashboard UI feature) are now actioned per CLAUDE.md's mapping table.
- D-16 and D-17 sections exist in their locked shapes, verified by direct grep against the
  acceptance criteria.
- Series 194 is fully dispositioned (12/12 cases have a checked Result box); both UAT
  corpus-integrity gates pass.
- No requirements were flipped by this plan (PARITY-04, VERDICT-01, DASH-09 were already flipped
  `[x]` Complete by 194-06 and 194-04 respectively) — this plan is documentation-only.
- Plan 194-08 (the 999.104 full CLI-vs-form field parity audit) is unblocked to run at phase close.

## Self-Check: PASSED

All 4 docs files and this SUMMARY.md confirmed present on disk; all 3 task commits
(`401e5558`, `2bc16745`, `3d76c6f2`) confirmed present in `git log`.

---
*Phase: 194-advanced-scan-fields-executive-verdict-phantom-cert-fix*
*Completed: 2026-09-09*
