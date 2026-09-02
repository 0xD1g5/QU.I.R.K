---
phase: 177-release-toolchain-repair
plan: 05
subsystem: release-documentation
tags: [uat-series, roadmap, version-bump, obsidian-sync]

# Dependency graph
requires: ["177-04"]
provides:
  - "docs/UAT-SERIES.md header + UAT-1-02 pass criteria at 5.18.0, UAT-1-02 re-executed live"
  - "Series 177: Release Verification (v5.18.0) — 3 honestly-dispositioned GAP cases, zero PASS"
  - ".planning/ROADMAP.md untagged/RVW-004 notes reframed as resolved history"
  - "Obsidian vault synced: UAT-Series.md, Phase-177 note (status: active)"
affects: [177-06, 177-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ledger-driven UAT-1-02 evidence updated via docs/uat-disposition-ledger.jsonl + scripts/uat_disposition_apply.py, not hand-edited in the document (it's a ledger-scoped case, unlike Series 177 which uses the documented MAX_SERIES=163 hand-write exception)"
    - "Honest SKIP(GAP) disposition for release-verification cases whose subject (a published v5.18.0 release) does not exist yet — UATREC-04 gate accepts GAP as a passing, non-fabricated disposition"

key-files:
  created: []
  modified:
    - docs/UAT-SERIES.md
    - docs/uat-disposition-ledger.jsonl
    - .planning/ROADMAP.md

key-decisions:
  - "UAT-1-02 is a ledger-driven case (series <= 163), so its Result-line update was made by editing docs/uat-disposition-ledger.jsonl's evidence/recorded fields and confirming agreement via scripts/uat_disposition_apply.py verify, not by hand-editing the document directly — this keeps the ledger and document from silently drifting apart, per D-04's discipline"
  - "All three Series 177 cases dispositioned SKIP (GAP — no substitute coverage) rather than PASS, per the plan's explicit honesty requirement — the v5.18.0 release (PyPI package, Sigstore attestation, pushed tag) does not exist at authoring time; git tag --list 'v5.18*' confirmed empty"
  - "docs/getting-started.md carries no version literal (grep confirmed — only IP-address-shaped false positives matched the version regex) — verified, not edited, per the plan's explicit instruction not to fabricate a change"
  - "ROADMAP.md's 'deliberately untagged' and RVW-004 notes were reframed as resolved history, not deleted — the v5.13/v5.14 two-component-tag defect record (reason release.yml's trigger was broadened) is preserved verbatim"
  - "Corrected ROADMAP.md Success Criterion 1's stale premise: the __editable__.quirk-4.0.0.pth residue did not itself reproduce a pip build-backend failure — the real, delivered fix (177-01/177-03) was a three-competing-distributions purge plus test_single_distribution_provides_quirk"
  - "Obsidian Phase 177 note written with status: active, not complete — the tag push (plans 177-06/177-07) is still a pending human handoff"

requirements-completed: []

# Metrics
duration: 45min
completed: 2026-09-02
---

# Phase 177 Plan 05: UAT-SERIES Bump, ROADMAP Reframing, Obsidian Vault Sync Summary

**Bumped `docs/UAT-SERIES.md` to 5.18.0 with UAT-1-02 genuinely re-executed against the live install and a new Series 177 (Release Verification) carrying three honestly-dispositioned `SKIP (GAP)` cases with zero fabricated PASS, reframed `.planning/ROADMAP.md`'s untagged/RVW-004 notes as resolved history without deleting the v5.13/v5.14 institutional-memory record, and re-synced the Obsidian vault including a new Phase 177 note explicitly marked `status: active` pending the still-outstanding tag push.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 3
- **Files modified:** 3 in-repo (`docs/UAT-SERIES.md`, `docs/uat-disposition-ledger.jsonl`, `.planning/ROADMAP.md`) + 2 vault writes (`UAT-Series.md`, `Phases/Phase-177-Release-Toolchain-Repair.md`)

## Accomplishments

- `docs/UAT-SERIES.md` header now reads `**Version:** 5.18.0` with a Phase 177 narrative paragraph
  naming the version bump, the single-distribution regression guard, and that this is the first
  release since 5.15.0.
- `UAT-1-02`'s pass criteria changed from `QU.I.R.K. v5.15.0` to `QU.I.R.K. v5.18.0`, and the case
  was genuinely re-executed: `.venv/bin/python run_scan.py --version` → `QU.I.R.K. v5.18.0`, exit
  0. Because UAT-1-02 is ledger-driven (in `MAX_SERIES=163` scope), the evidence update was made
  through `docs/uat-disposition-ledger.jsonl` and confirmed via
  `scripts/uat_disposition_apply.py verify` (378 rows agree), not by hand-editing the document.
- New `## Series 177: Release Verification (v5.18.0)` section added under the documented
  `MAX_SERIES=163` hand-write exception (same convention as Series 175/176): `UAT-177-01` (PyPI
  install), `UAT-177-02` (Sigstore attestation verify), `UAT-177-03` (three-component tag push +
  green `release.yml` publish job). All three are `SKIP (GAP — no substitute coverage)` — zero
  `[x] PASS` in the Series 177 block, verified by grep.
- All four UAT corpus-integrity guard suites green:
  `.venv/bin/pytest tests/test_uat_zero_undispositioned_gate.py tests/test_uat_series_format.py tests/test_uat_disposition_integrity.py tests/test_uat_apply_injection_guard.py -q -m ""`
  → 53 passed.
- `.planning/ROADMAP.md`'s "v5.16 deliberately untagged" and "Release-integrity note (RVW-004)"
  sections rewritten to read as resolved history: both milestones' content ships together in
  `v5.18.0`, the toolchain repair that unblocked the bump is named, and the tag push remains a
  deliberate human handoff. The original v5.13/v5.14 two-component-tag defect record — the reason
  `release.yml`'s trigger was broadened to `v[0-9]*` — is preserved verbatim, not deleted.
- ROADMAP.md's Phase 177 Success Criterion 1 corrected: the plan's originally-stated
  `__editable__.quirk-4.0.0.pth` "breaking pip's build backend" premise did not reproduce; the real,
  delivered fix (177-01/177-03) was a three-competing-distributions purge plus
  `tests/test_version.py::test_single_distribution_provides_quirk`.
- `docs/getting-started.md` verified via `grep -nE '[0-9]+\.[0-9]+\.[0-9]+'` to carry **zero**
  version literals (the two regex hits were `127.0.0.1` and `169.254.169.254`, IP addresses, not
  versions) — no edit made, as instructed.
- `.planning/ROADMAP.md`'s Phase 177 checkbox remains unflipped (`grep -c '^\- \[x\] .*Phase 177'`
  → 0) — gated on `177-VERIFICATION.md`, not produced by this plan.
- Obsidian vault synced: `docs/UAT-SERIES.md` → `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`
  (byte-matches the repo file after the frontmatter offset, verified via `diff`), and
  `docs/getting-started.md`'s vault counterpart confirmed already byte-current (Task 2 made no
  edit to the source, so no sync was needed — verified by diff, not silence). A new Phase 177 note
  written at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-177-Release-Toolchain-Repair.md`
  with `status: active`, all four requirement IDs, and a `[[Roadmap]]` link, explicitly stating the
  tag push (plans 177-06/177-07) is still pending.
- `git tag --list 'v5.18*'` confirmed empty throughout — no tag created, no release published, no
  `gh workflow run`/`gh release create`/`twine upload` invoked.

## Task Commits

1. **Task 1: Bump the UAT-SERIES header, re-execute UAT-1-02, add Series 177** - `6814a666` (docs)
2. **Task 2: Reframe ROADMAP.md's untagged/RVW-004 notes as history; verify getting-started.md** - `c5c8854e` (docs)
3. **Task 3: Sync the Obsidian vault + write the Phase 177 note** - no repo commit (vault-only writes, outside version control per LIVE-03)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Series 177 Result lines initially wrapped across multiple physical lines, breaking `CANONICAL_RESULT_RE`**
- **Found during:** Task 1 verification (`test_uat_series_format.py::test_all_result_lines_canonical`)
- **Issue:** The first draft of the three Series 177 `**Result:**` lines wrapped the parenthetical
  GAP annotation across 2-3 physical lines for readability. The canonical grammar regex is
  anchored `^...$` on a single line, so wrapped lines fail the format gate.
- **Fix:** Collapsed each `**Result:**` line to a single physical line.
- **Files modified:** `docs/UAT-SERIES.md`
- **Commit:** `6814a666`

**2. [Rule 1 - Bug] UAT-1-02's evidence text, if hand-edited directly in the document, would have desynced from the ledger**
- **Found during:** Task 1 verification (`test_uat_disposition_integrity.py::test_ledger_matches_document`)
- **Issue:** `UAT-1-02` is a ledger-driven case (series 1, in `MAX_SERIES=163` scope). Editing only
  the document's `**Result:**` line — as an initial draft did — creates a document/ledger
  mismatch that `test_ledger_matches_document` correctly flags.
- **Fix:** Updated `docs/uat-disposition-ledger.jsonl`'s `UAT-1-02` row (`evidence`, `recorded`
  fields) to match the intended document text, then confirmed agreement with
  `scripts/uat_disposition_apply.py verify` (378 rows agree, exit 0).
- **Files modified:** `docs/uat-disposition-ledger.jsonl`, `docs/UAT-SERIES.md`
- **Commit:** `6814a666`

**3. [Rule 1 - Bug] ROADMAP.md's corrected Success Criterion 1 text initially still contained the literal stale phrase it was correcting**
- **Found during:** Task 2 acceptance-criteria check (`grep -c "breaking pip's build backend"`)
- **Issue:** The first draft of the correction quoted the stale phrase verbatim inside the
  correction sentence itself, so the grep-based staleness check the plan specifies still matched.
- **Fix:** Reworded the correction to avoid repeating the literal stale phrase while still
  explaining what was corrected and why.
- **Files modified:** `.planning/ROADMAP.md`
- **Commit:** `c5c8854e`

None of the other deviation rules applied — no missing critical functionality, no blocking issues
requiring architectural changes.

## Known Discrepancy (Not Fixed, Out of Scope)

`scripts/uat_disposition_apply.py verify` and this repo's various narrative references
(`177-04-SUMMARY.md`, STATE.md, prior phase notes) cite **377** agreeing ledger rows. The actual,
independently re-measured count both before and after this plan's edits is **378** —
`wc -l docs/uat-disposition-ledger.jsonl` and `verify`'s own printed count both say 378, and this
plan did not add or remove any ledger row (only edited `UAT-1-02`'s existing row in place). This
is a pre-existing off-by-one in the repo's own narrative record, not something introduced or
correctable by this plan's scope — flagged here rather than silently perpetuated as "377."

## Self-Check: PASSED

- `docs/UAT-SERIES.md` header: `grep -c '^\*\*Version:\*\* 5.18.0'` → 1 — FOUND
- `docs/UAT-SERIES.md` UAT-1-02 pass criteria: `v5.18.0` present, `v5.15.0` absent from the
  criteria line — VERIFIED
- `docs/UAT-SERIES.md` Series 177: `grep -c '^### UAT-177-0[123]'` → 3 — FOUND
- Zero `[x] PASS` in Series 177: `sed -n '/^## Series 177/,$p' | grep -c '\[x\] PASS'` → 0 (the one
  substring hit is prose "zero `[x] PASS`", not a checked box) — VERIFIED
- Heading/Result parity: `grep -c '^### UAT-'` == `grep -c '^\*\*Result:\*\*'` → 694 == 694 — VERIFIED
- `.venv/bin/pytest tests/test_uat_zero_undispositioned_gate.py tests/test_uat_series_format.py tests/test_uat_disposition_integrity.py tests/test_uat_apply_injection_guard.py -q -m ""` → 53 passed — VERIFIED
- `.venv/bin/python scripts/uat_disposition_apply.py verify` → "verified 378 ledger row(s) against document -- all agree" — VERIFIED
- `.planning/ROADMAP.md`: `grep -c 'v5.18.0'` → 7 — VERIFIED
- `.planning/ROADMAP.md`: `grep -c "breaking pip's build backend\|breaks pip's build backend"` → 0 — VERIFIED
- `.planning/ROADMAP.md`: `grep -c '^\- \[x\] .*Phase 177'` → 0 (checkbox correctly left unflipped) — VERIFIED
- `docs/getting-started.md`: `git diff --stat` empty — VERIFIED (no edit made)
- Commit `6814a666` — FOUND in `git log --oneline -5`
- Commit `c5c8854e` — FOUND in `git log --oneline -5`
- Vault `UAT-Series.md`: `tail -n +9 | diff -q - docs/UAT-SERIES.md` → MATCH — VERIFIED
- Vault `Phases/Phase-177-Release-Toolchain-Repair.md`: exists, `status: active`, all 4 requirement
  IDs present (8 occurrences), `[[Roadmap]]` link present (2 occurrences) — VERIFIED
- `git tag --list 'v5.18*'` → empty — VERIFIED
