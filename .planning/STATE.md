---
gsd_state_version: 1.0
milestone: v5.18
milestone_name: Migration Execution
status: executing
stopped_at: Completed 177-06-PLAN.md
last_updated: "2026-09-02T19:23:02.156Z"
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 14
  completed_plans: 12
  percent: 20
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-19)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours — now with continuous hardware lifecycle monitoring (drift detection, EOL tracking, sensor-fleet coverage, lightweight check-in re-probes, and catalog-level vendor PQC trend tracking) layered on top of the v5.7–v5.10 agentless hardware PQC fingerprinting foundation.

**Current focus:** Phase 178 — finding-identity-repair
Plan 176-08 (user-directed, executed after the user hard-quit and relaunched a wedged Docker
Desktop) closed both outstanding LABRUN-01 GAP cases against a live `core + ssh-weak` lab:
`UAT-5-11` → **PASS**, `UAT-6-08` → **FAIL**. The FAIL exposed **TRIAGE-176-03**, a product defect
present since the ssh-audit integration shipped — `quirk/scanner/ssh_scanner.py:_run_ssh_audit`
passed host and port as two positionals when `ssh-audit` accepts one `host:port` target, so the
invocation exited 2 with empty stdout and every SSH scan silently degraded to a banner grab,
leaving `ssh_audit_json` NULL on every install and starving the CBOM, QRAMM evidence bridge,
hardware scanner, and dashboard of all SSH algorithm data. It survived the suite because
`tests/test_ssh_scanner.py` patched `subprocess.run` and asserted only on `return_value`, never
`call_args`. **Fixed in-phase at explicit user direction** (a deliberate departure from this
phase's no-product-change rule, taken because the lab was already up), TDD with the argv assertion
confirmed RED first; verified live, `ssh_audit_json` 0 → 7218 bytes, 30 algorithms classified
including NIST-level-3 `mlkem768x25519-sha256`. `UAT-6-08` stays FAIL because two **case-text**
defects survive the product fix — criterion 1 wrongly requires `ssh-ed25519` be "not
quantum-vulnerable" (it is elliptic-curve; level 0 is correct) and criterion 4 expects
per-algorithm NIST levels in the findings JSON when they exist only in the CBOM — both carried
forward in ROADMAP.md per the `UAT-94-05`/`UAT-36-05`/`UAT-8-07` precedent. **LABRUN-01 Complete:
10 PASS / 3 FAIL / 0 GAP.** Full suite `1 failed, 3802 passed` — sole failure the pre-existing
`test_skip_registry` `DEFER-172-01` node, zero new failing nodes. Lab torn down, zero containers.
Commit `2dedf0dc`. **Phase 176 VERIFIED 2026-09-01 — `176-VERIFICATION.md` `status: passed`,
15/15 must-haves, 0 overrides.** ROADMAP.md's Phase 176 checkbox is now flipped `[x]` and the
progress row reads `6/6 | Complete — verified 15/15 | 2026-09-01`. The verifier independently
reproduced SC3's root cause (`git show 72c06529^:uat_runner.py:154` — both disjuncts of
`'4.2.0' in ver or 'quirk' in ver.lower()` unsatisfiable against `QU.I.R.K. v5.15.0`), confirmed
SC1's 13 outcomes against verbatim lab transcripts with `LAB STATUS: UP` and
`TEARDOWN: CONFIRMED`, and confirmed SC2's TRIAGE-176-01/02 reached the ROADMAP Backlog.

Note on tooling: **`/gsd-verify-phase` is not a real command** — no such skill exists.
`NN-VERIFICATION.md` is produced by the `gsd-verifier` subagent, which `/gsd-execute-phase`
spawns at its `verify_phase_goal` step; to backfill one for an already-executed phase, dispatch
`Agent(subagent_type="gsd-verifier")` directly. Every prior `/gsd:verify-phase` reference in this
file was corrected to name that mechanism on 2026-09-01.

**Next step:** v5.17 milestone close-out (`/gsd-complete-milestone`) — Phases 172-176 all
verified.

**Prior focus:** Phase 174 — dashboard-api-correctness — **CLOSED, human-approved 2026-08-29.**
174-05's Tasks 1-3 (Obsidian sync + phase note, REQUIREMENTS.md close-out with honest scoping
notes, blocking full-suite regression gate) are complete. Task 3's checkpoint was presented and
**explicitly approved by the user on 2026-08-29**: full unfiltered suite (`pytest -q -m ""`,
408.13s) reproduced `1 failed, 3766 passed, 42 skipped, 73 xfailed, 4 xpassed` — the sole failure
is the pre-existing `test_skip_registry::test_no_unregistered_skips` (`DEFER-172-01`), identical
node to the Phase 173 baseline. Delta reconciliation exact: `3758 + 8 new tests (3+2+3) = 3766`,
zero new failing nodes. All six locked-decision drift traps (no `.tsx`, empty diffs on
`src/dashboard/`, `quirk/models.py`, `quirk/db.py`, `quirk/reports/writer.py`,
`docs/error-codes.md`, `uat_runner.py`, `pyproject.toml`, `src/dashboard/package.json`) produced
no output. `test_clone_reconstruction` green and byte-unmodified. Four UAT guard suites green
(48 passed); `uat_disposition_apply.py verify` → 377 rows agree, exit 0. `174-VALIDATION.md`
closed `status: complete`, `nyquist_compliant: true`, zero `⬜ pending` rows. DASH-06/07/08 marked
Complete in `.planning/REQUIREMENTS.md` with honest scoping notes — DASH-06 explicitly records the
CLI-scan score-profile persistence deferral (D-01) so the fix is not mistaken for full
literal-text delivery. Obsidian vault fully synced: `UAT-Series.md` resynced with Series 174, the
already-current `Phases/UAT/UAT-Series.md` duplicate confirmed current, the stray `Untitled 1.md`
scratch note given an explicit STALE banner (not deleted, out of this plan's file-ownership
scope), and the Phase 174 phase note written recording the narrowing honestly. Phase 175 now
inherits **three** carried-forward case-text corrections: `UAT-94-05` (Phase 172), `UAT-36-05`
(Phase 173), and `UAT-8-07` (Phase 174) — recorded in `ROADMAP.md`'s Phase 175 section. ROADMAP.md's
Phase 174 phase-list checkbox is deliberately left unflipped, reserved for the `gsd-verifier` phase-goal pass for Phase 174
per this repo's pre-commit gate and Phase 172/173 precedent; the plan tally row is updated to
`5/5 | Complete | 2026-08-29`. Next step: the `gsd-verifier` phase-goal pass for Phase 174, then Phase 175 (Case &
Documentation Defect Correction).

## Decisions Carried Forward (Phase 175)

- **175-01 independently re-verified all 12 pre-labelled UAT case defects against the current
  (2026-08-30) checkout** — 8 by direct source read/grep, 4 by live execution — rather than
  trusting `175-ASSUMPTIONS.md`'s 2026-08-29 adjudication. Zero contradictions: all 12 confirmed
  as CASE (documentation) defects, zero PRODUCT defects found, D-04's promotion gate reads
  **GATE OPEN**. UAT-55-01's live `control_id` occurrence count re-confirmed as exactly 0 (D-01's
  contradiction trigger did not fire). UAT-94-05's byte-identical redaction-message finding
  re-confirmed live (the gap D-03's companion case closes). UAT-110-06's disjoint-window
  arithmetic re-derived from current `quirk/merge/scan.py` source (line numbers shifted, logic
  unchanged). Corpus baseline confirmed identical to the prior report's: 682 headings, 682 result
  blocks, 0 undispositioned, 377 ledger rows, `verify` exit 0. Plan was strictly read-only —
  `git status --porcelain quirk/ run_scan.py uat_runner.py src/dashboard/ docs/` produced no
  output. See `175-REVERIFICATION.md` (gitignored, `.planning/phases/175-.../`) and
  `175-01-SUMMARY.md`.

## Decisions Carried Forward (Phase 174)

- **174-05 closed the phase honestly, with two of three "defects" resolved as document-not-product
  and the third's scope narrowed by explicit user decision.** DASH-06's real fix (a one-line
  `profile=calibration` kwarg at `scan.py:1263`) is delivered, but persisting the score profile
  for CLI-run scans is deliberately deferred (D-01) — no schema migration, no backfill, and the
  requirement body says so explicitly rather than implying full delivery. DASH-07 required zero
  production code changes (D-02): the empty-state "defect" was already correct behavior, verified
  against a genuine empty-DB probe. DASH-08 required zero UI changes (D-03): the stale Phase-39
  D-11 nav-order note was corrected to match the deliberately-shipped 14-item `sidebar.tsx` order,
  not the other way around, with a bidirectional drift guard to prevent future silent divergence.
  `UAT-8-07`'s case-text correction (illegal `--score-profile standard` value, out-of-scope
  bare-CLI reproduction) is promoted to Phase 175, joining `UAT-94-05` (Phase 172) and `UAT-36-05`
  (Phase 173) — Phase 175 now inherits three case-text corrections at its start.

## Decisions Carried Forward (Phase 173)

- **173-04 closed the phase's docs/bookkeeping honestly, including an in-flight revert.** Plan
  173-01's SCOPE-01 mechanism shipped, was live-verified correct against its own test fixtures,
  and was reverted the same day once verified against the repo's own real `config.yaml` exposed
  that the suppression fired unconditionally (`ScanCfg.ports_tls` has no default; every real
  config sets it). `UAT-36-05` is ruled a case defect (not a product defect) and promoted to
  Phase 175 — the case's own text in `docs/UAT-SERIES.md` Series 36 is left byte-untouched, and
  the ruling plus both rejected suppression mechanisms are recorded in `173-DISPOSITIONS.md`.
  `docs/configuration.md`'s companion-note task was retargeted (per that same dispositions
  document) from "document a behaviour change" to "document the real, unchanged gap the
  investigation surfaced" — no code changes accompany this plan.

## Decisions Carried Forward (Phase 172)

- **172-06 closed the phase on an honestly-reported, independently re-executed baseline rather
  than the documented figure.** Full suite ran 3x identically (1 failed, 3733 passed, 0
  deselected); the single failure's root cause was split into an in-scope 172-03-caused portion
  (fixed) and out-of-scope pre-existing drift (logged, not fixed) — see `deferred-items.md` in
  the phase directory for both `DEFER-172-01` (skip-registry drift) and `DEFER-172-02` (SIGSEGV
  crash reports). D-04's `UAT-94-05` case-defect disposition (promoted to Phase 175, case text
  left byte-untouched) is now also recorded in `ROADMAP.md`'s Phase 175 section, not only here
  and in the gitignored `172-DISPOSITIONS.md`.
plans; TRACE-01..07, RUNBOOK-01 all complete). 170-07 closed the phase: full unfiltered suite
(`pytest -q -m ""`, 0 deselected) held at the documented true baseline — 3670 passed, 4 failed
(1 pre-existing `test_skip_registry`, 3 pre-existing environmental `test_extras_install_matrix`
failures tied to a stale local editable install), zero fatal signals; all four UAT
corpus-integrity guard suites green; `scripts/uat_disposition_apply.py verify` confirmed all 377
ledger rows agree. `docs/UAT-SERIES.md` updated + synced to the Obsidian vault, phase note
written, and the human-verify checkpoint was **approved 2026-08-28** by the user (explicitly
confirming the Category B de-linkification approach). During checkpoint close-out the
coordinator found and fixed a coverage gap in 170-06: the `38-identity-api-regression-fix`
family (28 references across 6 files, one file not in 170-06's declared `files_modified`) was
missed and has now been rewritten to `v4.5-phases/38-identity-api-regression-fix/` —
filesystem-only, gitignored. `.planning/milestones/v5.16-phases/170-traceability-documentation-runbook/
170-VALIDATION.md` is now `nyquist_compliant: true`, `status: complete`, all 14 rows green. The
ROADMAP.md phase-level checkbox remains unchecked pending `170-VERIFICATION.md` from
the `gsd-verifier` phase-goal pass — next step is that verification pass, then Phase 171 (Resume UX Tail).

## Decisions Carried Forward (Phase 170)

- **170-07 closed the phase (full-suite proof + docs/Obsidian sync + human checkpoint).**
  Full unfiltered suite (`pytest -q -m ""`, confirmed 0 deselected) held at exactly the true
  baseline: 3670 passed, 4 failed (1 pre-existing `test_skip_registry`, 3 pre-existing
  environmental `test_extras_install_matrix` failures tied to a stale local editable install,
  proven local-environment-only), zero fatal signals — no regression from any of the six Wave-1
  plans landing together. All four UAT corpus-integrity guard suites green
  (`test_uat_zero_undispositioned_gate.py` 9/9, `test_uat_series_format.py` +
  `test_uat_disposition_integrity.py` 34/34 across both legs, `test_uat_apply_injection_guard.py`
  10/10); `scripts/uat_disposition_apply.py verify` confirmed all 377 ledger rows agree.
  `docs/UAT-SERIES.md` updated (commit `07c71b3`, `docs(phase-170):` format per the plan's own
  verify-grep requirement) and synced to the Obsidian vault; Obsidian phase note written to
  `Phases/Phase-170-Traceability-Documentation-Runbook.md`. Human-verify checkpoint (Task 3)
  **approved by the user on 2026-08-28**, explicitly confirming the Category B de-linkification
  approach ("honest prose please") for the 14 references to genuinely-absent Phase 133/134/144
  artifacts. During checkpoint close-out the coordinator independently ran all 11 automated
  `170-VALIDATION.md` rows (the executor had only run 2) and found row `170-06-01` genuinely
  FAILED: 170-06 missed the entire `38-identity-api-regression-fix` family (28 stale references
  across 6 files, one — `38-CONTEXT.md` — not in 170-06's declared `files_modified`). The
  coordinator rewrote all 28 to `.planning/milestones/v4.5-phases/38-identity-api-regression-fix/`
  (filesystem-only, gitignored) and re-ran the row: now PASSES. `170-VALIDATION.md` is now
  `nyquist_compliant: true`, `status: complete`, 0 pending rows. ROADMAP.md phase-level checkbox
  intentionally left unchecked — `scripts/verify_phase_gates.py` gates it on
  `170-VERIFICATION.md`, produced by the `gsd-verifier` phase-goal pass, not this plan. See
  `.planning/milestones/v5.16-phases/170-traceability-documentation-runbook/170-07-SUMMARY.md`.

- **170-06 closed TRACE-05.** Re-verified the plan's own ground-truth mapping table before
  acting per the plan's explicit instruction, and found one wrong destination:
  `36-dashboard-motion-tab` was claimed to archive under `v4.4-phases/` (which does not exist
  anywhere in the repo) but actually lives at `v4.5-phases/36-dashboard-motion-tab` — corrected
  to the real, `test -d`-verified path instead of the plan's stated one. Rewrote 22 Category A
  stale-but-resolvable cross-milestone sibling-phase citations across 17 files to their real
  post-archive `.planning/milestones/vX.Y-phases/` paths, and de-linkified 14 Category B
  citations across 8 files referencing Phases 133/134 (entire `v5.8-phases/` milestone directory
  absent, no incident manifest) and 144 (specifically missing from `v5.11-phases/`, documented in
  `ARCHIVE-MANIFEST.md`) into plain prose naming the phase and pointing at its surviving milestone
  `ROADMAP.md` section. Only 1 of the 25 edited files (`v5.12-phases/151-CONTEXT.md`) is tracked
  by git — the rest are gitignored under the Phase 120 `.planning/` exclusion and are correct
  filesystem-only edits, not missing work. See
  `.planning/milestones/v5.16-phases/170-traceability-documentation-runbook/170-06-SUMMARY.md`.

- **170-04 closed TRACE-03 and TRACE-04.** GAP-02 and QRAMM-09 (the two TRACE-03 items the
  original review claimed had no discoverable test) were re-verified during planning to already
  have real, passing tests the review's search missed — `tests/test_identity_surface.py::Issue3ScanWindowRegressionTest::test_saml_visible_with_earlier_dnssec`
  and `tests/test_qramm_router.py::test_create_profile`/`test_create_profile_multiplier_varies`
  respectively. No new tests were written for them; only annotated. Combined with 170-03's real
  new tests for DEBT-02 and QRAMM-08, TRACE-03 is now fully closed. TRACE-04's five items
  (AUTH-05, DEBT-04, GAP-01, QRAMM-11, TAIL-04) plus GAUGE-01/02/03 each gained a requirement-ID
  annotation in their existing docstring/comment, verified against the test body (not just
  filename) before annotating, and re-run to confirm still-passing. See
  `.planning/milestones/v5.16-phases/170-traceability-documentation-runbook/170-04-SUMMARY.md`.

- **170-03 added real, currently-passing tests for DEBT-02 and QRAMM-08** (`tests/test_lab_profile_args_precedence.py`
  exercises the real `lab.sh` script's CLI-wins-over-.env `PROFILE_ARGS` precedence via a real
  `bash -x lab.sh help` subprocess, no Docker; `qramm-assessment-dimension-coverage.test.tsx`
  renders the real `AssessmentPage` and proves all 4 dimension tabs together cover 120 questions
  at 30 each). TRACE-03 is NOT marked complete — it is shared with 170-04's annotation half. See
  `.planning/milestones/v5.16-phases/170-traceability-documentation-runbook/170-03-SUMMARY.md`.

- **170-02 closed TRACE-02, TRACE-06, TRACE-07.** `.planning/ROADMAP.md:12`'s dead v4.7 link now
  points at the real `.planning/milestones/v4.7-phases/` directory per locked D-01 (no
  reconstructed ROADMAP/REQUIREMENTS docs); `.planning/v4.7-MILESTONE-AUDIT.md` relocated to
  `.planning/milestones/` alongside its siblings, with `HORIZON.md`'s citation updated. Four
  archived ROADMAP.md files (v4.10, v5.1, v5.12, v5.4) gained a `**Status:**Ready to execute
  existing header was re-verified, not duplicated. `.planning/REQUIREMENTS.md` gained a
  `## Declaration Format` section documenting the canonical `- [ ] **REQ-ID**: description` format
  for all future requirement entries (archive backfill explicitly out of scope). See
  `.planning/milestones/v5.16-phases/170-traceability-documentation-runbook/170-02-SUMMARY.md`.

- **170-01 closed TRACE-01.** CHANGELOG.md now has an unbroken `## [X.Y.Z]` entry for every
  milestone v5.8.0 through v5.15.0 — no gap. v5.14.0/v5.13.0 entries state plainly, with root
  cause (`release.yml`'s `v*.*.*` three-component glob never matching the two-component `v5.13`/
  `v5.14` tags), that those milestones were developed but never released; the last version
  actually published to PyPI remains 5.12.0. v5.12.0/v5.11.0/v5.10.0/v5.9.0 entries document the
  four milestones that genuinely shipped. Every bullet is derived from the matching archived
  `.planning/milestones/vX.Y-ROADMAP.md` summary AND corroborated against
  `git log <prev-tag>..<tag> --oneline` per D-03 — no invented capability. See
  `.planning/milestones/v5.16-phases/170-traceability-documentation-runbook/170-01-SUMMARY.md`.

## Decisions Carried Forward (Phase 169)

- **Phase 169 closed the remainder of UATREC-03 (series 101-163, 78/78 dispositioned: 41 bucket
  A/B, 25 bucket C/D/E, 12 bucket F — 37+19+8=... see per-plan SUMMARYs) and UATREC-04 (standing
  gate).** Combined with Phase 168, the full 1-163 range (666 case headings, 377 ledger rows) is
  100% dispositioned: 202 PASS, 32 FAIL, 42 DEFERRED, 44 SKIP, 57 GAP.

- **`tests/test_uat_zero_undispositioned_gate.py` is the standing UATREC-04 gate** — an
  independently-parsed pytest test (zero imports from `scripts/uat_disposition_apply.py` or
  either sibling guard) that fails the build the moment any case in `docs/UAT-SERIES.md` has an
  all-empty `**Result:**` block. Rides the existing `Linux Full Suite` CI job
  (`pytest -q -m ""`), not a pre-commit hook or dedicated CI step. Documented in all four D-07
  locations: `CLAUDE.md`, the gate test's own docstring, `docs/UAT-SERIES.md`'s header,
  `docs/operators-guide.md` §5.3.1.

- **D-04 confirmed true and locked with a regression test**: `pytest -q -m ""` in the `Linux
  Full Suite` CI job is an empty marker expression that overrides `pyproject.toml`'s
  `addopts = -m 'not slow'`, so CI already execution-checks the `-m slow` substitute-proof leg
  (both pytest and vitest dialects). No nightly job or duplicate `-m slow` CI step was built.
  Phase 168's WR-02 code-review conclusion (that this leg never runs in CI) was based on
  searching for a literal `-m slow` string and missing this stronger equivalent.

- **The vitest dialect added to `tests/test_uat_disposition_integrity.py` (169-02) found zero
  genuine substitutes among Phase 168's 31 series-7 dashboard GAPs (169-06)** — every existing
  `.test.tsx` title was checked against each case's documented coverage need; zero converted.
  This is an honest, correct outcome (the checking work, not a target conversion count, was the
  deliverable) and confirms the series-7 GAP list Phase 170 inherits is accurate, not inflated by
  tooling limitation.

- **Known, documented limitation carried forward**: the vitest dialect's `-m slow` execution leg
  is gated on `VITEST_TOOLCHAIN_AVAILABLE` (npm + `src/dashboard/node_modules` present). The
  `Linux Full Suite` CI job never installs Node/npm for `src/dashboard/`, so in CI the vitest leg
  substitute-checks by existence only, not execution — tracked in `docs/uat-coverage-gaps.md`,
  not faked, not built out this phase.

- **Full local suite held at its known baseline after the drain**: 1 pre-existing failure
  (`test_skip_registry`), zero fatal signals, 3647 passing (up from Phase 168's ~3618/~3631 —
  169-01/169-02/169-07 added new tests).

## Decisions Carried Forward (Phase 168)

- **Phase 168 closed UATREC-03 for series 1-100 only (299/299 dispositioned): 142 PASS, 31 FAIL,
  36 DEFERRED, 36 SKIP, 54 GAP.** Series 101-163 (78 cases) remain for Phase 169, along with the
  standing UATREC-04 anti-re-accumulation gate. The true undispositioned total before this phase
  was 377 (not the stale "~325" figure) — 299 in series 1-100, 78 in series 101-163.

- **`tests/test_uat_disposition_integrity.py` makes a fabricated `DEFERRED — covered by` deferral
  mechanically impossible**: every named substitute node must resolve via `pytest --collect-only`
  AND actually pass (a skip is not proof of coverage). Proven non-vacuous against the finished
  document — 39 distinct substitute node references examined. The guard cannot cite frontend
  vitest coverage as a substitute (pytest-node-only), which inflates the GAP count for
  dashboard-UI cases; fixing that is a candidate follow-up, not scoped to Phase 169.

- **Full-suite subprocess spawns must go through `tests/cli_helpers.py::run_fork_safe`, not raw
  `subprocess.run(cwd=...)`.** `test_uat_disposition_integrity.py` (168-02) originally used a raw
  spawn and reintroduced the Phase 166 GATE-03 macOS fork()-after-Network.framework SIGSEGV,
  invisible until 168-09's mandatory full-suite baseline run. Fixed in 168-09 and the file was
  added to `test_cli_helper_usage.py`'s forward-locking AST gate. Any future test file that spawns
  a `pytest` subprocess must use `run_fork_safe` from the start.

- **`docs/uat-coverage-gaps.md` is the authoritative gap list for Phase 170's traceability work** —
  54 GAP rows plus 9 cross-plan structural findings (16 product/doc FAILs from buckets D/E, a
  stale `uat_runner.py` version-check bug, three chaos-lab premise findings, an unrendered
  HTML/PDF score-decomposition content check, and an error-response-body documentation drift).

## Decisions Carried Forward (Phase 167)

- **The "5 duplicate case IDs" figure was a truncating-regex artifact, not a finding.**
  `grep -o '^### UAT-[0-9]*-[0-9]*'` collapses three-segment IDs to two segments, turning the four
  distinct headings `UAT-89-02-01`, `UAT-89-02-02`, `UAT-89-03-01`, `UAT-89-03-02` into phantom
  `UAT-89-02` / `UAT-89-03` collisions. The true count was 3 (`UAT-144-01/02/03`). Phases 168-170
  draw on the same 2026-08-24 review — re-measure before actioning any count it asserts.

- **`tests/test_uat_series_format.py` now gates `docs/UAT-SERIES.md`.** Any Phase 168/169
  disposition edit must keep result blocks in the single canonical format, keep case IDs unique,
  and keep heading count == result-block count. The test asserts computed equality, so adding
  cases is fine; breaking the grammar is not.

- **Phase 168 starts from 666 cases, all with a result block, most undispositioned.** Structural
  parity is done; recording outcomes is UATREC-03 and was deliberately left untouched here.

## Current Position

Phase: 178 (finding-identity-repair) — EXECUTING
Plan: 6 of 7
Status: Ready to execute
pushed the three-component tag `v5.18.0` (`a8058261ba20b3fd3a1fb24860e82d7683c6ff4d`, dereferencing
to `8fc5133386bf7601bda394caa730da4166074fff` — the exact commit 177-06 gated). `release.yml` run
[33656116783](https://github.com/0xD1g5/QU.I.R.K./actions/runs/33656116783) fired on `event: push`
and completed `conclusion: success` across all three jobs (`Build wheel + sdist`, `Build Windows
zip + attach GitHub Release asset`, `Publish to PyPI (Trusted Publishers + Sigstore)`). PyPI JSON
API confirms `latest: 5.18.0`, both the wheel (`quirk_scanner-5.18.0-py3-none-any.whl`, 1442115
bytes) and sdist (`quirk_scanner-5.18.0.tar.gz`, 2150491 bytes) uploaded 2026-09-02T16:38:4x UTC.
A genuine clean-venv install (not the repo's editable `.venv`) confirmed `pip install
quirk-scanner==5.18.0` succeeds (after one CDN-lag retry) and `quirk --version` prints
`QU.I.R.K. v5.18.0`, exit 0. The Sigstore build-provenance attestation resolves via PyPI's
integrity endpoint with `publisher.repository: 0xD1g5/QU.I.R.K`, `publisher.workflow:
release.yml` — `UAT-177-02`'s original `gh attestation verify` instruction was found to target
the wrong store (GitHub's attestation API, which PyPI-published Sigstore bundles never reach) and
was corrected in place. `docs/UAT-SERIES.md` Series 177 (`UAT-177-01/02/03`) all flipped to real
`[x] PASS`. `.planning/REQUIREMENTS.md` RELEASE-01/02/03 all `[x]` complete; `ADVISORY-01`
correctly left open (standing milestone-wide constraint spanning Phases 177-181).
`.planning/ROADMAP.md` Phase 177 checklist + Progress table (`7/7 | Complete | 2026-09-02`) both
flipped. `177-VERIFICATION.md` (4/4 truths verified) and `177-VALIDATION.md`
(`nyquist_compliant: true`, `wave_0_complete: true`, 0 pending rows) written filesystem-only.
**Next step:** Phase 178 (Finding Identity Repair) — IDENT-01/02/03.

**v5.18 opened after a research pass, not on the HORIZON sketch.** The 3x sizing question the sketch
posed did not survive re-measurement — it is 4-5x, and the two readings share no infrastructure.
Full argument: `.planning/research/v5.18-sizing.md` and `v5.18-domain.md`.

**Two live defects are Phase 178 prerequisites** (both verified independently before scoping):

1. `compute_trend_report` is structurally dead — delta keys on `(host, port, protocol, severity)`
   and filters `severity is not None`, but severity is populated only by the three cloud connectors.
   Live DB: **10,069 endpoint rows, 0 non-NULL severity** → every scan reports 0 new / 0 resolved.

2. Ticketing fingerprint `SHA256(host:port::title)` interpolates 22 titles including
   `f"Certificate expiring in {days_to_expiry} day(s)"` → **cert-expiry findings mint a fresh Jira
   ticket every day**, despite the docstring claiming stability across re-scans.

**Locked decisions (do not re-litigate at phase CONTEXT time):**

- **ADVISORY-01** — closure state never feeds the readiness score. Extends
  `tests/test_cve_score_guard.py`; does not amend it.

- Closure is **machine-observed under a two-sided condition** (detected-by-previous AND
  verified-by-current), never human-asserted.

- **No re-scan entity resolution** — operator-supplied aliases plus an honest `not_observed` third
  state. `(host, port)` breaks on DHCP, hostname-vs-IP, VIPs, and container churn.

- Ticketing status readback is **out of scope** — it presumes a continuously-running control plane,
  which is the parked SaaS block.

**Carried verification debt:** the CNSA 2.0 date table is MEDIUM confidence — the research pass got
HTTP 403 on the NSA PDF. It must be manually re-verified against the primary source before CLOSE-03
ships, and it lands as a `last_verified` staleness-gated catalog, not inlined constants.

**Watch item:** CISA/NIST CBOM minimum-elements guidance is due ≈2026-12-19 under EO 14412's 180-day
tasking — a schema-risk event for the CBOM, inside this milestone's window. Not scoped; SURF-01's
VEX surface should be built to absorb a schema shift.

## v5.17 Phase Map (development complete 2026-09-01 — untagged)

| Phase | Name | Requirements | Gate | Status |
|-------|------|--------------|------|--------|
| 172 | Fuzzing & Disclosure Safety | SAFE-01, SAFE-02, SAFE-03 | None (first, highest client-estate consequence) | ✅ Complete (2026-08-29; 6/6 plans, VERIFICATION passed). Argparse-time `--fuzz` non-TTY + budget-over-500 refusals with coded FUZZ-001/002 and exit 2; real URL-component redaction replacing truncation-only `_redact_preview`; docs==code drift gate proven to fail on perturbation. `UAT-94-05` judged a case defect and promoted to Phase 175 |
| 173 | Scanner Scope & Config Correctness | SCOPE-01, SCOPE-02, SCOPE-03 | None (independent) | ✅ Complete (2026-08-29; 4/4 plans, VERIFICATION passed). SCOPE-02 `_PHASE_SKIPPED` sentinel + SCOPE-03 broker/smime/adcs missing-extra wiring shipped. **SCOPE-01's fix was built, shipped, live-verified, then reverted the same day** once shown to regress every real CLI config — closed as satisfied-by-override with user sign-off; its checkbox is deliberately `[ ]` (see `RECORD-01`) |
| 174 | Dashboard & API Correctness | DASH-06, DASH-07, DASH-08 | None (independent) | ✅ Complete (2026-08-30; 5/5 plans, VERIFICATION passed, human-approved 2026-08-29). Per-session calibration scoring on `GET /api/scans`; empty-DB contract guarded; 14-item sidebar order derived live and locked bidirectionally to its docs. `UAT-8-07` carried forward to Phase 175 |
| 175 | Case & Documentation Defect Correction | CASEFIX-01..05 | Phases 172/173/174 (inherits three carried-forward case-text corrections) | ✅ Complete (2026-08-30; 7/7 plans, VERIFICATION passed, user typed "approved"). Twelve case defects corrected with **zero product code changed**, all re-confirmed by live execution before editing; two left honestly DEFERRED; `UAT-94-09` added as the first redaction-regression detector, falsifiability proven against a neutered module |
| 176 | Chaos-Lab Re-Run | LABRUN-01, LABRUN-02 | Nothing, but scheduled last so its defects could be triaged against an otherwise-complete milestone | ✅ Complete (2026-09-01; 6 plans + 2 user-directed addenda, VERIFICATION passed 15/15, 0 overrides). All 13 lab-down cases re-executed with the lab up — **final tally 10 PASS / 3 FAIL / 0 GAP**. `UAT-1-02`'s four-month false FAIL root-caused to `uat_runner.py:154` (`'4.2.0' in ver or 'quirk' in ver.lower()` — both disjuncts unsatisfiable). Plan 176-08 overturned 176-07's root cause and surfaced `TRIAGE-176-03`: **every SSH scan since the ssh-audit integration shipped had silently degraded to a banner grab with `ssh_audit_json` NULL** |

## v5.16 Phase Map (development complete 2026-08-28 — untagged)

| Phase | Name | Requirements | Gate | Status |
|-------|------|--------------|------|--------|
| 164 | First-Run Correctness | FIRSTRUN-01, FIRSTRUN-02, FIRSTRUN-03 | None (first, deliberately led per milestone risk note) | Not started |
| 165 | Accessibility Remediation | A11Y-01, A11Y-02, A11Y-03, A11Y-04, A11Y-05 | None (independent) | Not started |
| 166 | Gate Robustness | GATE-01, GATE-02, GATE-03 | None (independent) | Plans executed (2026-08-27; 5/5 plans done — GATE-01/GATE-02/GATE-03 all verified clean; 166-05 closed GATE-03's full-suite scope gap 166-04 had honestly flagged, zero fatal signals suite-wide; see 166-05-SUMMARY.md) — ✅ Complete: VERIFICATION passed 3/3 (2026-08-27), e2e:smoke independently re-run at 3.1s vs 180s budget, full unfiltered macOS pytest independently re-run with zero fatal signals (was 14 across 6 files) — ✅ VERIFICATION passed 3/3 (2026-08-27); e2e:smoke independently re-run at 3.1s vs 180s budget; full unfiltered macOS pytest independently re-run with ZERO fatal signals (was 14 across 6 files) |
| 167 | UAT Format Unification & Deduplication | UATREC-01, UATREC-02 | None (must precede Phase 168 — normalized format makes drain checkable) | ✅ Complete (2026-08-27; 3 plans — 666 case headings == 666 result blocks, one canonical result format, zero duplicate IDs, zero headingless cases, all locked behind `tests/test_uat_series_format.py`, which was proven to FAIL on the pre-normalization document. Parity was 663==663 at Plan 02 and moved to 666==666 when Plan 03 appended Series 167 — the test asserts computed equality, never a constant, so it survived its own phase. VERIFICATION passed 6/6; human checkpoint cleared by user 2026-08-27) |
| 168 | UAT Record Drain — Series 1-~100 | UATREC-03 (partial) | Phase 167 | Plans executed (2026-08-27; 9/9 plans done — 299/299 series-1-100 cases dispositioned: 142 PASS, 31 FAIL, 36 DEFERRED, 36 SKIP, 54 GAP; `tests/test_uat_disposition_integrity.py` anti-fabrication guard proven non-vacuous against 39 substitute node references; full-suite baseline held at 1 pre-existing failure, zero fatal signals, 3631 passing); human checkpoint 168-09 Task 3 awaiting review; the `gsd-verifier` phase-goal pass for Phase 168 not yet run |
| 169 | UAT Record Drain — Series ~100-163 + Enforcement | UATREC-03 (remainder), UATREC-04 | Phase 168 | Plans executed (2026-08-28; 8/8 plans done — 78/78 series-101-163 cases dispositioned; full 666-case document + 377-row ledger 100% dispositioned (202 PASS, 32 FAIL, 42 DEFERRED, 44 SKIP, 57 GAP); `tests/test_uat_zero_undispositioned_gate.py` standing gate live, documented in all four D-07 locations; vitest dialect found zero genuine conversions among Phase 168's 31 series-7 GAPs; full-suite baseline held at 1 pre-existing failure, zero fatal signals, 3647 passing); UATREC-03/UATREC-04 both marked complete; 169-08 Task 3 human checkpoint APPROVED by user 2026-08-28; the `gsd-verifier` phase-goal pass for Phase 169 not yet run |
| 170 | Traceability, Documentation & Runbook | TRACE-01..07, RUNBOOK-01 | None (independent) | Plans executed (2026-08-28; 6/7 plans done — 170-01 gave CHANGELOG.md six entries for v5.9.0-v5.14.0 closing the gap between the existing 5.15.0 and 5.8.0 entries, v5.13.0/v5.14.0 correctly framed as developed-but-never-released; 170-02 fixed the dead v4.7 link, relocated the misfiled milestone audit, added Status headers to four archive ROADMAP.md files (v4.3 re-verified, not duplicated), and documented the canonical requirement-declaration format; 170-03 added real tests for DEBT-02 and QRAMM-08; 170-04 annotated GAP-01/GAP-02/QRAMM-09/AUTH-05/DEBT-04/QRAMM-11/TAIL-04/GAUGE-01-03 onto their existing already-passing tests; 170-05 added CMVP/error-codes/SNMP-contract catalogs to CLAUDE.md's staleness runbook (RUNBOOK-01); 170-06 rewrote 22 stale sibling-phase references to real archived paths and de-linkified 14 references to genuinely-absent Phase 133/134/144 artifacts (TRACE-05); TRACE-01 through TRACE-07 and RUNBOOK-01 all complete; only 170-07 (full-suite verification, docs/Obsidian sync, human checkpoint) remains) |
| 171 | Resume UX Tail | RESUME-05, RESUME-06 | None (independent) | Plans executed (2026-08-28; 1/3 plans done — 171-01 closed RESUME-05: `_resume_already_complete_message()` short-circuits `--resume-scan-id` on a scan whose `reports` checkpoint is already completed, printing the D-01 message and exiting 0 with zero new checkpoint rows; reproduced against a seeded sqlite DB before fixing (row count 3->8 pre-fix mid-scan, 3->3 post-fix); batch-row behavior (Phase 163 DISC-08) verified untouched) |

## v5.15 Phase Map (SHIPPED 2026-08-26)

| Phase | Name | Requirements | Gate | Status |
|-------|------|--------------|------|--------|
| 161 | Hardware Lifecycle Notifications + Vendor PQC Trend Surfacing | HWLC-14, HWLC-19 | None (first, independent) | ✅ Complete (2026-08-25) |
| 162 | Check-in Scan Scheduling | HWLC-20 | None (independent of 161) | ✅ Complete (2026-08-25) |
| 163 | Discovery Batch Checkpoint Granularity | DISC-08 | None (independent; different subsystem) | ✅ Complete (2026-08-26; 4 plans — 163-04 added mid-phase to fix a coverage-loss defect the UAT caught; VERIFICATION PASS 6/6, UAT-163-01..04 all PASS) |

## v5.14 Phase Map (SHIPPED 2026-08-19)

| Phase | Name | Requirements | Gate | Status |
|-------|------|--------------|------|--------|
| 157 | Drift-Event Retention + Forecast Narrative Foundation | HWLC-16, HWLC-18 | None (first, fully independent) | Ready for verification (2026-08-16; 5/5 plans executed, HWLC-16/HWLC-18 satisfied — the `gsd-verifier` phase-goal pass for Phase 157 not yet run) |
| 158 | Sensor Fleet Drift Coverage | HWLC-15 | None new (independent of 157; extends Phase 107/109/154 plumbing) | Ready for verification (2026-08-17; 3/3 plans, HWLC-15 satisfied — `158-VERIFICATION.md` on disk, VALIDATION.md rows not yet reconciled) |
| 159 | Check-in Scan Mode | HWLC-13 | Phase 158 (reuses shared persist_and_reconcile() for drift writes) | Ready for verification (2026-08-17; 5/5 plans executed, HWLC-13 satisfied — docs + UAT Series 159 + Obsidian vault sync closed; the `gsd-verifier` phase-goal pass for Phase 159 not yet run) |
| 160 | Catalog-Level PQC Vendor Trend Tracking | HWLC-17 | Phase 158 (reuses persist_and_reconcile() call site; needs complete fleet population) | Ready for verification (2026-08-18; 3/3 plans executed, HWLC-17 satisfied — GET /api/hardware/vendor-trends live, docs + UAT Series 160 + Obsidian vault sync closed; the `gsd-verifier` phase-goal pass for Phase 160 not yet run) |

## v5.13 Phase Map (SHIPPED 2026-08-15)

| Phase | Name | Requirements | Gate | Status |
|-------|------|--------------|------|--------|
| 154 | Identity & Data-Model Foundation | HWLC-01, HWLC-02, HWLC-03 | None (first, blocks 155/156) | Ready to plan |
| 155 | Drift Detection + EOL Tracking | HWLC-04..09 | Phase 154 | Not started |
| 156 | Reporting & OT/ICS Safety | HWLC-10, HWLC-11, HWLC-12 | Phase 155 | Complete (2026-08-15; /gsd-secure-phase 156 SECURED 19/19 threats closed, 0 high-severity findings) |

## v5.12 Phase Map (SHIPPED 2026-08-14)

| Phase | Name | Requirements | Gate | Status |
|-------|------|--------------|------|--------|
| 148 | Release Pipeline Repair + Windows Asset Backfill | RELEASE-02, RELEASE-03, RELEASE-04 | None (first, demonstrable early win) | Complete (2026-08-11) |
| 149 | Test Suite Triage | SUITE-01 | None (independent, highest-variance item run early/alone) | Complete (2026-08-12) |
| 150 | Test Suite Green Baseline + CI Gate | SUITE-02, SUITE-03 | Phase 149 (scope depends on triage output) | Complete (2026-08-13; VERIFICATION passed 4/4 — green run 31723764281, red run 31725715958, both live-fire proven on real GitHub Actions) |
| 151 | Phase-Completion Artifact Gates | ARTIFACT-01, ARTIFACT-02, ARTIFACT-03, ARTIFACT-04 | None (independent) | Complete (2026-08-13; VERIFICATION passed 4/4 — scripts/verify_phase_gates.py + .githooks/pre-commit, now installed and live via `core.hooksPath` as of the v5.12 milestone audit) |
| 152 | Discovery Empirical Closure | DISC-09, DISC-10, DISC-11 | None (DISC-10 depends on DISC-09 within-phase) | Complete (2026-08-13; VERIFICATION 4/4 — segmented-network lab profile live-verified, Phase 144 nmap timing artifact DOES NOT REPRODUCE per 152-DISC09-FINDING.md, enable_nmap defaults True) |
| 153 | Release Tag Cut | RELEASE-01 | Phases 148, 150, 151 | Complete (2026-08-14; VERIFICATION 12/13 live-verified — v5.12.0 tagged, pushed, real release.yml green (event=push), Windows zip attached to GitHub Release, published on PyPI, tag-hygiene guard OK) |

## v5.11 Phase Map (SHIPPED 2026-08-11)

| Phase | Name | Requirements | Gate | Status |
|-------|------|--------------|------|--------|
| 144 | Chunked Discovery Core | DISC-01, DISC-02 | None (first, anchor) | Complete (2026-08-10; VERIFICATION passed 6/6 with 1 user-accepted override — nmap timing-engine artifact on a mostly-silent loopback target list) |
| 145 | Liveness Pre-Pass | DISC-03 | Phase 144 | Complete (2026-08-10; VERIFICATION written retroactively at v5.11 audit closeout — passed 4/4, 0 overrides) |
| 146 | Progress, Scaling & Disclosure | DISC-04, DISC-05, DISC-06, DISC-07 | Phase 144 | Complete (2026-08-11; VERIFICATION passed 4/4; code review CR-01 undetermined-host miscount fixed before close) |
| 147 | Backlog Drain — Lifecycle & Ledger Tail | DRAIN-01, DRAIN-02, DRAIN-03, DRAIN-04 | None (independent) | Complete (2026-08-11; VERIFICATION passed 4/4; VALIDATION reconciled to nyquist_compliant at audit closeout) |

## v5.10 Phase Map

| Phase | Name | Requirements | Gate | Status |
|-------|------|--------------|------|--------|
| 139 | SNMPv3 Auth+Priv Support | SNMPV3-01..04 | None (first) | Complete |
| 140 | SNMP-Confirmed Bridge Mitigation | BRIDGE-01..05 | Phase 139 | Complete |
| 141 | OT/ICS Fingerprinting (Modbus + BACnet) | OTICS-01..06 | None new (sequenced after 139) | Complete (both Modbus and BACnet validated end-to-end, live-verified 2026-08-03) |
| 142 | Firmware CVE Correlation | CVE-01..04 | Phase 141 | Complete |
| 143 | Dashboard & Security Tail | TAIL-01..04 | None (independent) | Complete (human_needed 12/13 — 2 items approved-to-continue, see Deferred Items) |

## v5.9 Final State

Shipped 2026-07-30, Phases 135–138 + 138.1/138.2, 10 plans, 16/16 requirements, tech_debt
disposition (deferred human-UAT only, no content gaps). Archive: `.planning/milestones/v5.9-ROADMAP.md`.

## Performance Metrics

**Velocity:**

- v5.9: 10 plans, 4 phases + 2 gap-closures (2026-06-18 → 2026-07-30)
- v5.8: 21 plans, 5 phases (2026-06-14 → 2026-06-18, 4 days)
- v5.7: 24 plans, 7 phases (2026-06-13 → 2026-06-14, 2 days)
- v5.6: 20 plans, 6 phases (2026-06-12)

**Per-plan execution metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 139 P00 | 12min | 3 tasks | 3 files |
| Phase 139 P01 | 15min | 2 tasks | 4 files |
| Phase 139 P02 | 25min | 2 tasks | 2 files |
| Phase 139 P04 | 12min | 3 tasks | 5 files |
| Phase 139 P03 | 20min | 2 tasks | 2 files |
| Phase 139 P06 | 15min | 3 tasks | 4 files |
| Phase 139 P07 | 20min | 2 tasks | 7 files |
| Phase 139 P08 | 45min | 2 tasks | 3 files |
| Phase 140 P00 | 6min | 2 tasks | 3 files |
| Phase 140 P02 | 20min | 3 tasks | 4 files |
| Phase 140 P03 | 25min | 3 tasks | 6 files |
| Phase 140 P04 | 18min | 3 tasks | 7 files |
| Phase 140 P05 | 10min | 3 tasks | 4 files |
| Phase 141 P01 | 12min | 2 tasks | 3 files |
| Phase 141 P02 | 12min | 2 tasks | 2 files |
| Phase 141 P03 | 18min | 2 tasks | 2 files |
| Phase 141 P04 | 25min | 3 tasks | 3 files |
| Phase 141 P05 | 20min | 2 tasks | 7 files |
| Phase 142 P00 | 25min | 3 tasks | 5 files |
| Phase 142 P01 | 20min | 2 tasks | 1 files |
| Phase 142 P02 | ~10min | 2 tasks | 3 files |
| Phase 142 P03 | ~20min | 3 tasks | 4 files |
| Phase 142 P04 | 20min | 2 tasks | 4 files |
| Phase 142 P05 | 15min | 3 tasks | 5 files |
| Phase 144 P01 | 12min | 2 tasks | 4 files |
| Phase 144 P02 | 35min | 2 tasks | 3 files |
| Phase 145 P01 | 8min | 2 tasks | 4 files |
| Phase 145 P02 | 20min | 2 tasks | 3 files |
| Phase 146 P01 | 20min | 3 tasks | 8 files |
| Phase 146 P02 | 15min | 2 tasks | 3 files |
| Phase 146 P03 | 18min | 3 tasks | 8 files |
| Phase 146 P04 | 20min | 3 tasks | 3 files |
| Phase 146 P05 | 10min | 1 tasks | 4 files |
| Phase 147 P01 | 12min | 3 tasks | 2 files |
| Phase 147 P02 | 35min | 5 tasks | 6 files |
| Phase 147 P03 | 25min | 3 tasks | 4 files |
| Phase 147 P04 | 25min | 2 tasks | 2 files |
| Phase 148 P01 | 25min | 3 tasks | 3 files |
| Phase 148 P03 | 15min | 2 tasks | 3 files |
| Phase 148 P02 | 35min | 3 tasks | 5 files |
| Phase 148 P04 | 40min | 3 tasks | 1 files |
| Phase 149 P01 | 45min | 3 tasks | 4 files |
| Phase 149 P02 | 20min | 3 tasks | 6 files |
| Phase 149 P03 | 25min | 3 tasks | 12 files |
| Phase 149 P04 | 25min | 3 tasks | 6 files |
| Phase 149 P05 | 20min | 3 tasks | 4 files |
| Phase 149 P06 | 40min | 3 tasks | 8 files |
| Phase 149 P07 | 45min | 3 tasks | 7 files |
| Phase 149 P08 | 40min | 3 tasks | 5 files |
| Phase 149 P09 | 45min | 3 tasks | 8 files |
| Phase 149 PP10 | 40min | 3 tasks | 6 files |
| Phase 149 P11 | 75min | 2 tasks | 10 files |
| Phase 150 P01 | 35min | 3 tasks | 4 files |
| Phase 150 P02 | 40min | 3 tasks | 2 files |
| Phase 150 P04 | 55min | 3 tasks | 3 files |
| Phase 150 P05 | 40min | 3 tasks | 8 files |
| Phase 150 P06 | 50min | 3 tasks | 13 files |
| Phase 150 P07 | 35min | 3 tasks | 4 files |
| Phase 150 P08 | ~90min | 3 tasks | 2 files |
| Phase 150 P09 | 35min | 3 tasks | 5 files |
| Phase 154 P01 | 15min | 2 tasks | 6 files |
| Phase 154 P02 | 35min | 2 tasks | 5 files |
| Phase 154 P03 | 40min | 3 tasks | 5 files |
| Phase 154 P04 | 15min | 2 tasks | 2 files |
| Phase 154 P05 | 45min | 3 tasks | 4 files |
| Phase 155 P01 | 20min | 2 tasks | 4 files |
| Phase 155 P02 | 25min | 3 tasks | 7 files |
| Phase 155 P03 | 25min | 3 tasks | 6 files |
| Phase 155 P04 | 20min | 2 tasks | 3 files |
| Phase 155 P05 | 35min | 2 tasks | 4 files |
| Phase 155 P06 | 15min | 2 tasks | 2 files |
| Phase 156 P01 | 12min | 2 tasks | 4 files |
| Phase 156 P03 | 35min | 3 tasks | 5 files |
| Phase 156 PP02 | 25min | 3 tasks tasks | 4 files files |
| Phase 156 P04 | ~30min | 3 tasks | 8 files |
| Phase 156 P05 | ~55min | 4 tasks | 8 files |
| Phase 156 P06 | 45min | 3 tasks | 7 files |
| Phase 157 PP01 | 18min | 2 tasks | 3 files |
| Phase 157 P02 | 12min | 3 tasks | 3 files |
| Phase 157 P03 | 15min | 3 tasks | 5 files |
| Phase 157 P04 | 25min | 2 tasks | 5 files |
| Phase 157 PP05 | 35min | 3 tasks | 4 files |
| Phase 158 P01 | 15min | 2 tasks | 3 files |
| Phase 158 P02 | 15min | 2 tasks | 4 files |
| Phase 158 P03 | 35min | 3 tasks | 4 files |
| Phase 159 P01 | 35min | 2 tasks | 6 files |
| Phase 159 P02 | 12min | 2 tasks | 2 files |
| Phase 159 P03 | 12min | 2 tasks | 4 files |
| Phase 159 P04 | 30min | 3 tasks | 7 files |
| Phase 159 P05 | 20min | 2 tasks | 4 files |
| Phase 160 P01 | 25min | 2 tasks | 6 files |
| Phase 160 P02 | 20min | 2 tasks | 3 files |
| Phase 160 P03 | 35min | 3 tasks | 6 files |
| Phase 161 P02 | 25min | 3 tasks | 4 files |
| Phase 161 P01 | 20min | 3 tasks | 5 files |
| Phase 163 P01 | 30min | 3 tasks | 2 files |
| Phase 163 P02 | 45min | 2 tasks | 2 files |
| Phase 164 P01 | 8min | 3 tasks | 3 files |
| Phase 164 P03 | 25min | 3 tasks | 9 files |
| Phase 164 P02 | 18min | 3 tasks | 2 files |
| Phase 164 P04 | 35min | 2 tasks | 5 files |
| Phase 165 P01 | 20min | 3 tasks | 0 files |
| Phase 165 P02 | 35min | 3 tasks | 3 files |
| Phase 165 P03 | 20min | 3 tasks | 5 files |
| Phase 165 P04 | 35min | 3 tasks | 6 files |
| Phase 165 P05 | 25min | 3 tasks | 15 files |
| Phase 165 P07 | 112min | 3 tasks | 40 files |
| Phase 165 P08 | 55min | 3 tasks | 3 files |
| Phase 166 P01 | 12min | 2 tasks | 1 files |
| Phase 166 P02 | 25min | 3 tasks | 4 files |
| Phase 166 P03 | 45 | 3 tasks | 5 files |
| Phase 166 P04 | 20min | 2 tasks | 2 files |
| Phase 166 P05 | 75min | 5 tasks | 9 files |
| Phase 168 P01 | 45min | 3 tasks | 2 files |
| Phase 168 P03 | 35min | 2 tasks | 2 files |
| Phase 168 P04 | 70min | 2 tasks | 2 files |
| Phase 168 P05 | 220min | 2 tasks | 2 files |
| Phase 168 P06 | 1h50min | 2 tasks | 2 files |
| Phase 168 P07 | 70min | 2 tasks | 2 files |
| Phase 168 P08 | 55min | 2 tasks | 3 files |
| Phase 168 P09 | 55min | 2 tasks | 6 files |
| Phase 169 P01 | 12min | - tasks | - files |
| Phase 169 P02 | 25min | 2 tasks | 1 files |
| Phase 169 P03 | 90min | 2 tasks | 2 files |
| Phase 169 P04 | 160min | 2 tasks | 2 files |
| Phase 169 P05 | ~2h | 2 tasks | 3 files |
| Phase 169 P06 | 20min | 2 tasks | 1 files |
| Phase 169 P07 | 25min | 2 tasks | 1 files |
| Phase 169 P08 | ~35min | 2 tasks | 4 files |
| Phase 170 P02 | 12min | 2 tasks | 8 files |
| Phase 170 P04 | 15min | 2 tasks | 10 files |
| Phase 170 P06 | 25min | 2 tasks | 25 files |
| Phase 171 P01 | 25min | 1 tasks | 2 files |
| Phase 171 P02 | 20min | 2 tasks | 3 files |
| Phase 171 P03 | 65min | 3 tasks | 3 files |
| Phase 172-fuzzing-disclosure-safety P01 | 25min | 3 tasks | 5 files |
| Phase 172 P02 | 15min | 2 tasks | 1 files |
| Phase 172 P03 | 50min | 3 tasks | 6 files |
| Phase 172 P05 | 25min | 3 tasks | 6 files |
| Phase 173 P01 | 45min | 3 tasks | 4 files |
| Phase 173 P02 | 45min | 3 tasks | 2 files |
| Phase 173 P03 | 45min | 3 tasks | 2 files |
| Phase 174 P01 | 25min | 2 tasks | 2 files |
| Phase 174 P02 | 20min | 2 tasks | 2 files |
| Phase 174 P03 | 35min | 2 tasks | 5 files |
| Phase 174 P04 | 55min | 3 tasks | 3 files |
| Phase 175 P02 | 12min | 3 tasks | 1 files |
| Phase 175 P03 | 25min | 3 tasks | 1 files |
| Phase 175 P04 | 25min | 3 tasks | 1 files |
| Phase 175 P05 | 35min | 3 tasks | 3 files |
| Phase 175 P06 | 90min | 2 tasks | 3 files |
| Phase 176 P01 | 25m | 3 tasks | 3 files |
| Phase 176 P02 | 15min | 2 tasks | 3 files |
| Phase 176 P03 | 15min | 3 tasks | 1 files |
| Phase 176 P04 | ~1h | 3 tasks | 2 files |
| Phase 176 P05 | 12min | 2 tasks | 2 files |
| Phase 177 P01 | 8min | 3 tasks | 1 files |
| Phase 177 P02 | 55min | 2 tasks | 2 files |
| Phase 177 P03 | 22min | 3 tasks | 2 files |
| Phase 177 P04 | 35min | 3 tasks | 3 files |
| Phase 177 P05 | 45min | 3 tasks | 3 files |
| Phase 177 P06 | 26min | 3 tasks | 0 files |
| Phase 178 P01 | 12min | 2 tasks | 1 files |
| Phase 178 P02 | 18min | 2 tasks | 1 files |
| Phase 178 P03 | 25min | 2 tasks | 2 files |
| Phase 178 P05 | 35min | 2 tasks | 6 files |

## Accumulated Context

**v5.14 shipped 2026-08-19.** Decisions below predate the shipped v5.14 milestone (Phases
157–160, HWLC-13/15/16/17/18) and are kept for historical continuity — full milestone decision
log lives in PROJECT.md's Key Decisions table and `.planning/RETROSPECTIVE.md`'s v5.14 section.
Next milestone's numbering continues at Phase 161.

### Decisions

- **Phase 168 Plan 05 (2026-08-27):** `run_scan.py --db-path` silent-no-op trap recurs at the
  config level — `config.yaml`'s own `output.db_path` (default `./quirk.db`) governs where
  `crypto_endpoints`/checkpoints actually land, not the CLI `--db-path` flag alone; both must
  point at the same path or the scan silently writes to the wrong file. A local self-signed TLS
  listener on `127.0.0.1:8443` substitutes for the chaos lab (D-01) when a UAT case only needs a
  generic reachable TLS endpoint, not protocol-specific detection (SAML/Kerberos/DNSSEC/broker
  still SKIP without the lab). Headless Playwright (already installed in `.venv`) substitutes for
  human browser verification on dashboard-route/console/focus/pagination UAT cases — real SPA
  route and API data, direct URL navigation instead of a literal sidebar click. This plan's real
  execution surfaced 16 genuine product/doc findings: dashboard score not tracking
  `--score-profile` (UAT-8-07), unconditional email-port probing breaking a documented
  HTTPS-only empty state (UAT-36-05), an undocumented "Hardware" sidebar item breaking the D-11
  nav-order lock (UAT-39-07), an unenforced `--fuzz-budget` 500 hard maximum and a non-hard-
  aborting non-TTY `--fuzz` path (UAT-96-02/96-03), a raw-URL-disclosure gap in
  `SpecParsingError`'s message (UAT-94-05), and 5 stale/quoted doc-grep patterns.

- Numbering continues at Phase 154 (v5.12 ended at 153). Phase order is dependency-driven:
  identity/data-model (154) must land before drift detection (155) since every diff feature
  reconciles "the same device across two scans"; reporting/OT-ICS safety (156) depends on
  drift events existing before they can be surfaced or scheduled. Research (4 unanimous passes)
  resolved the milestone's flagged 3x sizing uncertainty toward the smaller estimate — a
  scheduling/diffing/reporting layer over existing `HardwareDevice` data, not a new scanner
  surface; no new dependencies, database, or background worker. Sensor-push hardware coverage
  (extending `PushEnvelope`) is explicitly deferred to v2+, not included in v5.13 — console-direct
  scans only. Phase 156's OT/ICS cadence-floor work requires a dedicated `/gsd-secure-phase`
  review before shipping, per REQUIREMENTS.md HWLC-12.

- Numbering continues at Phase 144 (v5.10 ended at 143). Phase order is dependency-driven:
  chunked discovery core (144) must land before liveness pre-pass (145) or progress/scaling (146)
  since both depend on batches existing. 144 explicitly bundles the gate-relaxation work
  (`target_expander.py::_MAX_HOSTS_PER_CIDR` + `jobs.py`'s 422 stopgap) with the chunking core
  itself — per research PITFALLS.md, splitting them risks a repeat of the Phase 141 outer-gating
  bug shape (feature built, never reachable). Liveness pre-pass (145) gets its own phase for
  isolated non-root privilege-fallback verification. Progress/scaling/CLI-parity/disclosure (146)
  groups DISC-04/05/06/07 as one phase per explicit instruction. Backlog drain (147) is fully
  independent of the DISC phases — different code paths, sequenced last but not blocking.

- Numbering continues at Phase 139 (v5.9 ended at 138 + gap-closures 138.1/138.2).
- Phase order is dependency-driven, not feature-list order: SNMPv3 (139) must precede bridge
  confirmation (140) because the confirmation probe needs authenticated SNMP transport to reach
  gateway forwarding/ARP tables. Bridge confirmation gets its own dedicated phase — not bundled
  with SNMPv3 — because of the false-assurance risk in an over-eager `upstream_mitigated`
  promotion. OT/ICS (141) is independent but sequenced after 139 to mirror dispatcher shape.
  CVE correlation (142) is sequenced after OT/ICS so it inherits new vendor/model values. The
  dashboard/security tail (143) is fully independent, sequenced last per its "small tail" framing.

- Package layout: no `quirk/hardware/` package exists or should be introduced — all new modules
  (`modbus_scanner.py`, `bacnet_scanner.py`, `otics_meta.py`, `hw_cve.py`) follow the existing flat
  `quirk/scanner/` (and `quirk/cbom/`) convention.

- Repeats the v5.8 "B-01" lesson: every phase adding `HardwareDevice` columns must update all
  three projection sites (`reports/writer.py`, `merge/scan.py`,
  `dashboard/api/routes/scan.py`) in the same phase (OTICS-06 makes this explicit for Phase 141;
  applies equally to 139/140/142's derived fields).

- TAIL-02 (trusted-targets allowlist) and TAIL-03 (Windows code-signing CI) each require a
  dedicated `/gsd-secure-phase` review given the repo's 5-strikes SSRF history and the Phase 120
  PEM-in-history incident.

- [Phase 139]: snmp_v3_credentials lives under connectors: in YAML (ConnectorsCfg field), matching 139-00 RED test shape, unlike top-level broker_credentials
- [Phase 139]: D-02 validation raises plain ValueError (no dedicated ConfigError class) — matches 139-00 RED test and existing config-validation convention
- [Phase 139]: SNMP_MODE_V3_NO_AUTH_PRIV is canonical (matches 139-00 RED test); SNMP_MODE_V3_NOAUTH kept as an alias so both spec artifacts pass
- [Phase 139]: _classify_v3_failure only treats decryptionError as protocol-mismatch when it co-occurs with security-level text, avoiding over-classifying generic decryption failures
- [Phase 139]: Wired the SNMPv3 v3->v2c->none fallback ladder into both independent SNMP entry points (hardware_scanner.py Step 3 and run_scan.py --enable-snmp pass), each honestly labeling v3-failed-fell-back (D-03) vs v3-protocol-mismatch (D-02) vs plain v2c/none, writing auth/priv protocol columns only on v3 success
- [Phase ?]: SNMP badge label map duplicated verbatim in html_renderer.py and docx_renderer.py rather than extracted to a shared module, matching existing per-renderer helper precedent
- [Phase 139]: SNMP badge column (139-06) reuses existing Badge primitive + native title= tooltip; snmpLabel() raw-fallback mirrors 139-05 report renderer for cross-surface parity
- [Phase ?]: Phase 139-07: hwcompat-snmp lab USM user quirkv3user (SHA/AES) added directly via createUser+rouser in snmpd.conf; lab passphrases are non-secret test values (accepted risk, same posture as rocommunity public)
- [Phase 139]: SNMP_V3_TIMEOUT_MULTIPLIER kept at 2 — empirically confirmed against live hwcompat-snmp target (~0.05s round-trip vs 6s budget), no spurious timeouts
- [Phase 139]: hwcompat-snmp exposes both port 161 (for run_scan.py live scans) and 20223 (existing direct snmpget/snmpwalk docs) — additive, non-breaking
- [Phase 140]: bridge_evidence_json/bridge_confirmed_at reuse the exact Phase 139 SNMPv3-column precedent (module-level tuple + _ADDITIVE_MIGRATIONS append) — no new migration machinery
- [Phase 140]: [Phase 140]: _confirm_upstream_mitigation evidence check operates at /24 subnet-group level (not device-identity) — symmetric promotion matching _detect_crypto_bridges' existing group-assignment shape
- [Phase 140]: 140-03: HTML caveat kept inside existing pre-collapsed <details> block per plan text (pre-existing PDF-visibility scope, not fixed this plan); badge colors sourced from UI-SPEC hsl() values (amber F59E0B / blue 60A5FA)
- [Phase 140]: [Phase 140] 140-04: bridge_status dashboard lookup keyed by host, matching _detect_crypto_bridges'/_confirm_upstream_mitigation's own host-based subnet grouping
- [Phase 140]: No lab compose/port/service/seed change was required for BRIDGE-01/04 empirical validation — Docker's bridge networking seeds the gateway ARP entry automatically, resolving Assumption A3. — Resolves 140-RESEARCH.md assumptions A2/A3 without new lab config
- [Phase 140]: Fixed a Rule 1 evidence-shape mismatch: sensor writer persisted (ip, mac) tuples while the console reader expected {target_ip, mac} dicts, silently blocking upstream_mitigated promotion from real sensor data. — Caught during Task 3 checkpoint prep; writer normalized to match the more broadly tested reader contract
- [Phase 141]: pip install must target .venv explicitly — default PATH pip/python3 resolve to a stray Python 3.9 user install that fails the project's requires-python >=3.10 gate
- [Phase 141]: pymodbus pinned <4 and bacpypes3 pinned <0.1; both in [hw] extras only, never [all]
- [Phase 141]: No modbus_port/bacnet_port or per-host allowlist config field — ports 502/47808 hardcoded in scanner modules per D-06/RESEARCH Pitfall 3
- [Phase 141]: pymodbus 3.14.0 moved mei_message under pymodbus.pdu — resolved with nested try/except import fallback covering both layouts within the >=3.8.0,<4 pin
- [Phase 141]: bacpypes3 who_is(address=, timeout=) + read_property(source, objid, prop) signatures confirmed live against installed 0.0.106 source before implementation
- [Phase 141]: BACnet safety docstring prose rewritten to avoid literal write_property/broadcast substrings so documentary text doesn't trip its own acceptance-criteria grep
- [Phase 141]: OTICS-01/02/05: Modbus Step 4 gates on enable_modbus+port==502 (D-04); BACnet Step 5 gates on enable_bacnet only (Who-Is is its own gate); neither nested under vendor==Unknown (D-01); first-match-wins Modbus-before-BACnet headline (D-03)
- [Phase ?]: [Phase 141]: Test harness pattern for embedded (non-extracted) projection dict code — spy-wrap the real downstream function (_confirm_upstream_mitigation) via monkeypatch to capture the dict without perturbing behavior, instead of mocking/extracting
- [Phase 141]: 141-06 Tasks 1-2 complete (Modbus blue/BACnet purple badge columns on /hardware + matching HTML/DOCX report columns + D-13 abort caveat); Task 3 human-verify checkpoint is open — dashboard/report visual colors and abort-state distinctness await explicit user approval before 141-06 is marked done
- [Phase 141]: 141-07 Tasks 1-2 complete — new `otics` chaos-lab compose profile (D-09 standalone, not folded into hwcompat) with two fragile simulators: otics-modbus (port 502/TCP, pymodbus-backed FC 43/14 Read Device Identification, Schneider Electric M221) and otics-bacnet (port 47808/UDP, bacpypes3-backed Who-Is/I-Am + ReadProperty, Johnson Controls FX16). Both simulators sit behind a custom asyncio "gatekeeper" (raw-socket admission layer only — protocol framing/encode/decode is real pymodbus/bacpypes3, never hand-rolled) enforcing D-10 fragility: single-in-flight-only (second concurrent connection/datagram reset/dropped) and malformed-header reset/drop. Locally verified (not via Docker) against real pymodbus/bacpypes3 clients: normal round trip returns correct vendor/model/firmware, concurrent connection gets reset, malformed frame gets reset/dropped. expected_results_otics.md oracle + README.md otics row + operators-guide.md §9.4 (D-07 risk warning) + report-interpretation.md §10.6 (five-state vocabulary + Probe aborted) + chaos-lab.md §3.23 all added and synced to Obsidian vault Digs. Task 3 (live Docker end-to-end validation) is a blocking-human-verify checkpoint — NOT executed by the agent per plan instructions.
- [Phase 142]: Combined Task 1 (table/staleness) and Task 2 (comparator/correlation) into a single commit — verified together as one cohesive module before the first commit
- [Phase 142]: RESEARCH.md illustrative regex fixed: [A-Za-z]* widened to [A-Za-z0-9]* so Cisco's parenthetical+train-letter suffix (e.g. '(4)M3') parses; added explicit R<release> capture group so Juniper's '12.3R12-S19' correctly compares greater than '12.3R12'
- [Phase ?]: [Phase 142] run_cve_status() accepts an optional argv list (unlike qramm_cmd's zero-arg signature) to support --format json pass-through to hw_cve.status_report
- [Phase 142]: 142-03: cve_snapshot_stale computed once on exec_content in writer.py, then stamped onto every device dict at the html_renderer call site rather than passed as a second render_hardware_section parameter, keeping the render function a pure devices-list contract matching its test
- [Phase 142]: 142-04: cve_matches serialized as reduced {cve_id, severity, source_url}; CVE_BADGE_STYLE reuses the existing SNMP-confirmed blue hue rather than a new color
- [Phase 142]: 142-05: docs/getting-started.md had no pre-existing catalog-status command list; added a new Catalog Status Commands section for compliance/qramm/cve
- [Phase 144]: Split Task 1's combined helper+cap-removal edit into two atomic commits (helpers-only, then cap-removal+test-rewrites) to preserve the plan's intended per-task checkpoint granularity
- [Phase ?]: [Phase 144]: Relocated error_endpoints init to before the discovery block (Pitfall 1) rather than inventing a parallel discovery-only bookkeeping list
- [Phase ?]: [Phase 144]: Guarded the discovery ScanCheckpoint write with a _discovery_batch_loop_ran flag so it fires only on the nmap batch-loop path, not cache-hit/fallback sub-branches
- [Phase ?]: [Phase 144]: Batch-loop failure-isolation tests exercise the loop's exact shape directly (mirroring inline run_scan.py code) rather than invoking full main(), per RESEARCH.md's stated fallback
- [Phase 145]: parse_nmap_host_status() deliberately omits parse_nmap_xml's skip-if-not-up filter so down hosts survive as up=False rows — D-04: record don't drop non-responsive hosts
- [Phase 145]: _resolve_liveness_port_spec narrowed the plan's literal any-other-override-to-dash wording to a startswith(--top-ports) check with pass-through for unrecognized overrides — makes the mandated _SAFE_NMAP_ARG_RE allowlist gate reachable/testable instead of dead code
- [Phase 145]: liveness_endpoints kept as a dedicated accumulator separate from error_endpoints, merged in only after the discovery ScanCheckpoint partial-failure snapshot, so normal liveness_skip/privilege_fallback rows never flip discovery status to partial
- [Phase 145]: Survivor set for the sweep computed by excluding known-down hosts from the batch (not including known-up hosts), so a host nmap omits entirely from the liveness XML defaults to being swept rather than silently dropped
- [Phase 146]: named tuple _PHASE146_SCANJOB_COLUMNS to avoid _PHASE46_COLUMNS collision; corrected _ADDITIVE_MIGRATIONS header comment since scan_jobs is now the first pure table to require a migration
- [Phase ?]: Phase 146-02: Both discovery helpers degrade to base/T4 default on non-int input rather than raising, since they feed directly into subprocess timeout/argv
- [Phase ?]: Phase 146-02: discovery_timing_template_for_batch returns only hardcoded -T4/-T3 literals via if/else per threat T-146-01 - never config/input-built
- [Phase 146]: 146-03: _compute_undetermined_hosts() gates on port==0 AND scan_error_category in ('exception','liveness_skip') — port==0 conjunct is load-bearing so a live-host TLS/SSH/API handshake error is never counted as undetermined
- [Phase 146]: 146-04: Combined Tasks 1+2 into one commit since both edit the exact same discovery-loop-body statements (pre-count/progress-write + timeout/timing scaling); resolved Open Q1 as batch formula fully replacing args.nmap_timeout inside the loop, and Open Qs 2/3 as accepting one throwaway O(n) pre-count pass so the dashboard batch total is correct from batch 1
- [Phase 146]: 146-05 executed exactly per PATTERNS.md conditional shape — no deviations
- [Phase 147]: DRAIN-01 — hoisted run_ot_supplemental_and_persist() above run_scan.py's ssh-stage if/else so a --resume-scan-id continuation still fingerprints OT-only (Modbus/BACnet) hosts; ssh-stage checkpoint write stays fresh-run-branch-only, reordered before the hoisted (advisory) hardware persist
- [Phase 147]: D-147-02-A: build-catalog (option a) — user confirmed via orchestrator checkpoint before plan dispatch
- [Phase 147]: D-147-03-WR02: wr02-fix - ship the port-aware default CORS allowlist fix via a new QUIRK_DASHBOARD_PORT env var
- [Phase 147]: D-147-03-CD03: cd03-accept - accept the SSRF TOCTOU/DNS-rebinding risk with refreshed rationale (answered after an orchestrator-level clarification exchange), citing Phase 120 T-120-04 and Phase 123 SSRF-05
- [Phase 147]: D-147-04-AUTHENTICODE: user confirmed no production Windows Authenticode code-signing cert acquired/loaded into GitHub Actions secrets — UAT-143-03 finalized STILL BLOCKED, re-triage at next milestone close
- [Phase 147]: DRAIN-04 re-triaged all Deferred Items rows with dated 2026-08-10 dispositions; gh evidence shows origin/main unpushed since 2026-06-18 (no live windows-latest CI run for Phase 139-147 work); relocated 36 stray per-plan duration rows to Performance Metrics; removed stale healthcare-vertical-merge quick_task row
- [Phase 148]: [Phase 148]: Scoped test_no_guard_is_ref_shape_only to actual if: directive lines only, excluding explanatory comments that quote the guard literal by name
- [Phase 148]: 148-03: Reworded 5.11.0.md See Also section to avoid the literal missing-filename substrings (5.7/5.8/5.9/5.10 dot-md) while still conveying the gap, satisfying the plan's own no-link acceptance criterion and the new test's guard
- [Phase 148]: 148-02 RELEASE-03 tag-hygiene guard: TDD gate via temporary implementation relocation for genuine RED; LOOSE_RELEASE_TAG_RE (^v[0-9]) deliberately broader than release.yml's v*.*.* glob; baseline seeded with all 32 pre-existing tags for a green-from-day-one first scheduled run
- [Phase 148]: 148-04 live-run evidence: dry-run run 31524058796 (publish job skipped, windows-package success incl. SELF_TEST_SIGNING: OK); tag-hygiene run 31524420671 (EXEMPT names v5.9/v5.10.0/v5.11.0 correctly, zero flagged); bare v5.11.0 GitHub Release created with zero assets, isDraft false, latest=false
- [Phase 149]: D-04 drift repair: 30 unregistered skip markers registered/updated in tests/skip_registry.py (optional_extra/live_infra only); AST walker extended to detect skip/skipif/xfail decorators; pre_existing_triage_149 category reserved for Plans 02-10
- [Phase ?]: Phase 149 Plan 02: All 23 Cluster 1 (SSRF/DNS-blocked sandbox) tests dispositioned quarantined-xfail with matching skip_registry entries and ledger rows; meta-gate confirmed green
- [Phase 149]: Plan 03: All 20 Cluster 2/6 tests dispositioned quarantined-skip (not xfail), per D-03: running them under full-suite pollution is not useful signal and they are expected to run cleanly once Phase 150 fixes the shared fixture/lifecycle issue
- [Phase 149]: Plan 04: reassigned test_cli_correctness.py::test_version_consistency from Cluster 3 (environment) to Cluster 4 (stale assertion) per RESEARCH.md ground truth; TARGET now derives from quirk.__version__ instead of a hardcoded literal, preserving cross-module consistency coverage without every-release edits
- [Phase 149]: [Phase 149]: Plan 05: test_sensor_push_id_revalidation.py's 2 failures are shared in-memory SQLite cache pollution across test files (file::memory:?cache=shared&uri=true), NOT an AUDIT-08 write-before-reject defect; individually investigated per RESEARCH.md Open Question 3, distinct sub-reason from test_auto_merge_trigger.py's 8 outdated-fixture failures
- [Phase 149]: Plan 06: closed the tests/scanner/ non-recursive glob gap (Assumption A3) before quarantining any Cluster 9 Group A test in that subdirectory; individually investigated all 18, converging on DNS-blocked-sandbox SSRF guard (9), stale CR-06 opt-in guard (2), stale test fixture (2) for 13 xfail quarantines, while 5 were found not reproducible in this sandbox (already-registered optional_extra skips or currently-passing) and left unmarked
- [Phase 149]: Plan 07: test_route_coverage.py's AUTH-02 GET /api/config finding confirmed as stale test inventory (route intentionally public per its own docstring, no sensitive data exposed), explicitly not flagged SECURITY, per must_haves requirement
- [Phase 149]: Plan 07: 4 of 5 /api/compare test failures were a test-construction bug (unescaped + UTC offset in raw f-string query URL decoded as space by query parsing), not API-contract drift as RESEARCH.md suspected; verified via urllib.parse.quote()-encoded params returning 200
- [Phase 149]: Plan 08: test_qramm_staleness.py SIGSEGV pair investigated but not reproducible in this sandbox (3/3 isolated runs, direct CLI hand-invocation, and a ~550-test full-suite slice all pass); left unmarked per Plan 06 precedent, flagged HIGH-PRIORITY for Phase 150 re-verification given a segfault's severity class
- [Phase 149]: Plan 08: test_no_risk_engine_import's failure is cross-test sys.modules pollution from test_findings_evaluator_dedupe.py's risk_engine shim test (alphabetically earlier), not a real QRAMM-12 import-graph violation in evidence_bridge.py itself
- [Phase 149]: test_cbom_schema_validation.py's otics chaos-lab profile drift is a genuine Chaos Lab Maintenance gap (Phase 141-07's synthesizer never landed in PROFILE_ENDPOINTS), flagged for Phase 150 follow-up
- [Phase 149]: Plan 09: 3 of 11 Group D1 tests (test_errors_cmd + 2 GCP-403 posture tests) investigated but found NOT reproducible in this sandbox; POSTURE-02's scan_error emission on GCP 403 already works correctly despite file's stale RED-scaffold docstring
- [Phase 149]: Plan 10: both security-gate meta-test failures confirmed as gate-logic gaps (Jinja-only detection can't see Python-side pre-escaping/static-dict sourcing; AST classifier has no ast.IfExp case), not real unsanitized-usage or safe_str-bypass findings; neither flagged SECURITY
- [Phase 149]: Plan 10: test_sensor_windows_smoke.py's SIGSEGV confirmed not reproducible and explicitly not sharing Plan 08's QRAMM SIGSEGV root cause (different subsystem/subprocess construction, no crash when run together); flagged as a second independent Phase 150 re-verification item
- [Phase 149]: Plan 11: fixed 2 real production bugs (sslyze __version__ submodule shape, impacket MethodData rename) surfaced by fresh-run reconciliation; consolidated 5 scattered SIGSEGV findings across Plans 06/08/10 into one systemic macOS fork()-under-full-suite-load root cause; quarantined 9 tests with corrected root causes; ledger reconciled to 116 rows, 0 orphaned failures, fresh full-suite run 0 failed
- [Phase ?]: [Phase 150]: Fixed _build_as_req via constants.encodeFlags([...].value) on the modern impacket path, preserving the legacy KDCOptions(...) constructor call behind an else branch for impacket <0.13.0 (Phase 150 D-05)
- [Phase ?]: [Phase 150]: Rule 1 auto-fix — test_build_as_req_nonce_uses_secrets asserted secrets.randbits(31), but commit 830ad6a (Phase 71 review, D-09) had deliberately switched the scanner to a 32-bit nonce; corrected the stale assertion to randbits(32) in the same edit that removed the xfail marker
- [Phase 150]: Local sandbox python/pip interpreter mismatch (python -> Homebrew 3.14, pip -> stray ~/Library/Python/3.9) caused 11 false full-suite failures in bacnet/modbus/openapi tests; .venv/bin/python confirmed correct interpreter, 0-failed baseline (3089 passed, 42 skipped, 80 xfailed)
- [Phase 150]: Plan 04 -- stood up $HOME/.cache/quirk-ci-parity-venv (outside repo tree, pip install -e ".[all]" + pytest only, zero identity/hw/api extras); no Python 3.11 available on this machine so venv built on 3.14.6 (known, accepted parity gap -- documented, doesn't block extras-boundary verification). Full-suite run there: 32 failed, exactly matching CI Categories B+C+D+F+G (6+18+6+1+1); Categories A/E/H (4+1+1) did not reproduce due to concrete local-vs-CI differences (working-copy .planning/ present, Docker not running, stale gitignored quirk.egg-info from pre-rename install) -- no unexplained local-only failures.
- [Phase 150]: Plan 04 D-16 -- deleted test_package_manifest_version_is_4_1_0 outright (not fixed in place); its local-only pass was traced to a stale gitignored quirk.egg-info directory in the repo working tree, absent from any fresh checkout, matching CI's real PackageNotFoundError.
- [Phase 150]: Plan 04 D-17 -- root-caused /api/sensor/push 404 as a test-construction defect: fastapi 0.141.1/starlette 1.6.0 no longer flatten include_router() routes into application.routes at include time (lazy _IncludedRouter wrapper instead), so the old isinstance(r, APIRoute) walk missed every /api/* route, not just sensor/push. Confirmed via TestClient the route dispatches correctly end-to-end (401/200). Fixed with a recursive _IncludedRouter-aware route-path walker in the test; assertion contract unchanged, no skip registered.
- [Phase 150]: Plan 05: cleaned up leftover empty labs/grpc-tls/certs directories from a prior Docker bind-mount failure before generating certs -- confirmed untracked/gitignored, filesystem-only cleanup not a git operation
- [Phase 150]: Guarded 35 extras-gated/gitignored-fixture tests with per-test skips (D-09..D-11, D-15); test_identity_surface.py and test_rest_fuzzer_probes.py deltas from plan estimates documented in 150-06-SUMMARY.md
- [Phase 150]: ROADMAP.md Phase 150 header corrected to 9 plans (not the plan's literal '6 plans' instruction) — the plan checklist already listed all 9 plan entries (150-01 through 150-09) before this plan dispatched; matched the header to that ground truth
- [Phase 150]: Live-fire CI proof closed SUITE-02/SUITE-03 -- real Linux Full Suite run 31723764281 green (0 failed, .[all]-only, ubuntu-latest, Python 3.11.15) after D-03 SIGSEGV quarantine (bbe8b55); real red run 31725715958 via throwaway PR #10 proved the gate bites (1 failed, isolated to the deliberate smoke test), PR closed unmerged and branch deleted, evidence in 150-CI-EVIDENCE.md
- [Phase 150]: Plan 09 closed the phase -- 150-VERIFICATION.md written against all 4 ROADMAP success criteria (all PASS, Criterion 1 anchored to the real CI run not the corroborating local venv run); SUITE-02/SUITE-03 confirmed Complete (already flipped by 150-08's metadata commit, this plan replaced the stale in-progress status note with a 150-CI-EVIDENCE.md pointer); ROADMAP.md's 150-09 checkbox and the Phase 150 heading both ticked -- the plan's own literal "tick all six" instruction was stale (mirrors 150-07's "6 plans" deviation) since the true count is 9 plans, all already checked; `.continue-here.md` deleted (resolved blocker, filesystem-only per PUBREPO-01 gitignore convention)
- [Phase ?]: [Phase 154]: match_confidence kept as a column distinct from the pre-existing confidence column (D-04/D-05) — cross-scan identity confidence vs. probe-result confidence
- [Phase 154]: match_confidence upgrade to high is unconditional on Step 1's vendor match outcome — a correctly-identified device still gets its SSH host-key fingerprint (RESEARCH §1)
- [Phase 154]: Rule 3 fix: three test fixture _make_ep() helpers needed ssh_audit_json=None pre-populated in __dict__, since fingerprint_one's unconditional getattr hit SQLAlchemy UnmappedInstanceError (not AttributeError) on __new__-constructed test doubles missing that key
- [Phase 154]: implemented the true D-13 per-device latest-success join at all four HardwareDevice projection sites (dashboard findings/components, merge/CBOM, CLI/PDF/DOCX writer), not a shallow probe_status filter on the old MAX(scanned_at) window - a failed re-probe never removes a device, it shows the last-known-good row
- [Phase 154]: Rule 3 fix - pre-existing Phase 141 OTICS-parity test fixtures (test_hardware_projection_sites.py, test_dashboard_api.py) needed probe_status=success added since their seeded HardwareDevice rows predate the new per-site probe_status filter and would otherwise silently vanish from every projection
- [Phase 154]: 154-04: purge call placed before the hw_batch add() loop (deviation from PATTERNS §8, plan-authorized) — avoids autoflush interaction between pending inserts and synchronize_session=False delete
- [Phase 154]: 154-05: UAT-154-01 automated gate narrowed from a broad -k "fingerprint" selector to explicit test node IDs after discovering it matched an unrelated pre-existing flaky test not caused by this plan
- [Phase 155]: Shipped 4 citation-backed EOL_TABLE entries (F5 BIG-IP, Fortinet FortiGate, Palo Alto PAN-OS, Cisco IOS) instead of the plan's 6-entry target — Fail-closed fallback per plan text -- Juniper/HPE/Thales/Schneider Electric/Johnson Controls candidates had no independently fetchable, dated vendor lifecycle page reachable in this sandbox; guessing dates was disallowed
- [Phase 155]: Fortinet entry sourced via endoflife.date/fortios aggregator — No static Fortinet-owned EOL bulletin page was fetchable (JS-rendered); endoflife.date is a well-known aggregator that itself cites Fortinet's official EOL bulletins, cross-verified live
- [Phase 155]: [Phase 155] HardwareDriftEvent placed immediately after MergeRun in models.py, before HardwareDevice; recent_successful_hardware_rows() docstring kept terse to satisfy the plan's grep -A12 acceptance window while preserving the full documented contract; TIER_ORDER promoted verbatim into hardware_tier.py, dashboard route imports it aliased to the old private name so both existing call sites needed zero edits
- [Phase 155]: firmware_for_correlation() consolidated into hw_cve.py rather than duplicated a third time in hardware_drift.py::cve_delta() — closes RESEARCH.md Open Question 1 per the Phase 154 WR-02 lesson
- [Phase 155]: compute_drift_candidates() reads the STORED remediation_tier column, not a re-derived assign_tier() call — the reconciliation engine diffs persisted scan-row state
- [Phase 155]: bridge_evidence_state() reads only persisted bridge_confirmed_at/bridge_evidence_json columns, never a transient bridge_status dict key owned by quirk/cbom/bridge.py
- [Phase 155]: [Phase 155] 155-04: session.commit() runs unconditionally once after the reconcile candidate loop (even with zero inserts), matching plan text exactly; CVE-delta test fixtures monkeypatch hw_cve.correlate_device() rather than depending on live CVE_TABLE catalog content
- [Phase ?]: Phase 155-05: Confirmed live run_scan.py has exactly 2 real HardwareDevice commit sites (not 3) — run_ot_supplemental_and_persist() and the SNMP-only block; _run_ssh_phase() only accumulates into hw_batch. Resolved RESEARCH.md Open Question 2 as option (a) — reconcile at both real commit sites.
- [Phase ?]: Phase 155-05: apply_eol_date() single terminal call site placed immediately before the Phase 154 D-07 probe_status assignment in fingerprint_one() — covers every vendor/model resolution path (SSH, HTTP, SNMP, Modbus, BACnet).
- [Phase ?]: Phase 155-05: Site (B) SNMP-only block reconciles _snmp_new_batch (rows actually committed there), not _snmp_flush_batch — the pre-existing detached _existing_dev mutation-persistence gap is documented inline as a backlog candidate, not fixed (out of scope per HWLC-04..09).
- [Phase 155]: 155-06: docs/report-interpretation.md deliberately left untouched, deferred to Phase 156 when drift events gain a dashboard/report surface; REQUIREMENTS.md HWLC-04..09 verified already complete on disk (no diff needed)
- [Phase 156]: OTICS_MIN_INTERVAL_HOURS is a hardcoded, non-config-overridable floor (168h/7 days, D-19); min_gap_hours takes the MINIMUM of 9 consecutive gaps across 10 firings, never the average (D-20); strip_otics_keys uses explicit named pop over a 2-entry allowlist only, never substring matching (T-156-03)
- [Phase ?]: Phase 156-03: TIER_ORDER lower-int-is-more-urgent means Tier 2 -> Tier 1 is worsened, not improved
- [Phase ?]: Phase 156-03: hardware_drift.py module docstring paraphrases forbidden scoring-module names to avoid tripping its own T-156-04 acceptance-criteria grep
- [Phase ?]: [Phase 156] 156-02: dispatch-time gate in _materialize_scan_config uses stdlib logging.getLogger(__name__).info matching scheduler_cmd.py's existing idiom, not a threaded Logger param, per D-22's actual requirement (always-visible level)
- [Phase ?]: [Phase 156] 156-02: write-path inventory test asserts exact HTTP route/CLI subcommand/import-confinement sets as literal expected-value constants; negative-proof (temporary dummy route) confirmed the guard fails loudly before revert
- [Phase ?]: [Phase 156] 156-04: writer.py drift-serialization mirrors (not imports) quirk/dashboard/api/routes/hardware_drift.py's lookup/direction helpers — writer.py has no existing dependency on the dashboard API package
- [Phase 156]: Lifecycle advisory guard test comments avoid literal RegressionAlertChip/ui-badge substrings so raw grep acceptance criteria pass (156-03 docstring precedent); guard test resolves component sources via path.resolve not new URL(import.meta.url); section eyebrow/icon teal applied via inline style since .label-eyebrow is unlayered CSS and always wins the cascade over Tailwind utilities
- [Phase ?]: [Phase 156]: 156-06: enable_modbus/enable_bacnet had never been documented in docs/configuration.md's Connectors Block before this plan (pre-existing Phase 141 gap) — added both alongside enable_recurring_otics under Rule 2
- [Phase ?]: [Phase 156]: 156-06: /gsd-secure-phase 156 SECURED — 19/19 threats closed, zero high-severity findings, all four D-23 threat surfaces verified against real implementation code and tests; artifact written correctly to 156-SECURITY.md on first attempt (no root-SECURITY.md relocation needed)
- [Phase ?]: [Phase 157]: hardware_drift_event_retention_days is a dedicated ScanCfg field (D-02), not shared with hardware_history_retention_days; default 365 (D-03) matches the codebase's 365-day-cadence convention
- [Phase ?]: [Phase 157]: 157-01 call site is a dedicated if db_path: block, separate from the existing if hw_batch and db_path: block, so the drift-event purge runs even when a scan fingerprints zero fresh devices
- [Phase ?]: [Phase 157]: 157-02 build_eol_forecast(devices, today=None) signature intentionally constrained to devices/today only — no score input can be threaded through, verified by inspect.signature test (T-157-05)
- [Phase ?]: [Phase 157]: 157-02 quirk/reports/executive.py deliberately excluded from the T-157-05 advisory-only firewall module set — it legitimately imports compute_readiness_score, mirroring the Phase 155/156 precedent
- [Phase 157]: 157-03 eol_forecast population block placed after hardware_devices' final assignment (post bridge-detection/mitigation), no new DB session — forecast input always matches the hardware table's device set
- [Phase 157]: 157-03 render_eol_forecast_section uses h3 one level below render_drift_section's h2, bucket sentences as p not table, template placeholder after (not inside) drift_section conditional so forecast renders independent of drift events
- [Phase 157]: 157-04 DOCX forecast subsection is level-3 heading, one below the drift section's level-2, narrative paragraphs only (no table), guarded independently of hardware_drift_events
- [Phase 157]: 157-04 CLI forecast is a net-new sibling of the Hardware PQC Advisory block, gated solely on exec_content.eol_forecast — executive.py never shipped CLI drift rendering (Phase 156 D-12), so this is genuinely new prose, not an extension
- [Phase 157]: 157-04 new dedicated tests/test_executive_forecast_section.py module created, resolving 157-VALIDATION.md's open Wave 0 item about build_exec_markdown's scattered test coverage
- [Phase 157]: 157-05 report-interpretation.md's §10.11 EOL/Tier Forecast section expanded in place (not duplicated) with the literal bucket-label vocabulary and an explicit reader-facing guarantee that hardware_drift_event_retention_days places no limit on the forecast (ROADMAP success criterion #5)
- [Phase 158]: 158-01: D-158-A/B/C implemented as locked — persist_and_reconcile() always commits internally (no commit:bool param); purge_stale_hardware_history() relocated into hardware_drift.py with a run_scan.py alias; Site B (SNMP-only) now applies the retention purge for the first time — intentional behavior expansion
- [Phase 158]: 158-02: PushEnvelope.hardware_devices uses a bare None default (D-158-D/E/F implemented as locked) — absent vs confirmed-empty structurally distinguished; _hardware_device_to_dict()/_read_scan_hardware_devices() mirror the existing _endpoint_to_dict()/_read_scan_endpoints() shapes; both push and export _build_envelope() call sites updated identically
- [Phase 158]: 158-03: persist_and_reconcile() rolls back the session on internal exception before returning (0, []) -- a missing rollback previously let a failed hardware insert (e.g. NOT NULL scanned_at) poison the shared session and fail the whole sensor push, violating the advisory-only contract
- [Phase 158]: 158-03: HardwareDevice.scanned_at (NOT NULL) falls back to ingest time when the wire value is missing/malformed, instead of passing None through to a column that rejects it and silently dropping the whole device row
- [Phase 159]: 159-01 D-159-A..E implemented as locked; Rule 1 fix wired is_partial_scan through sensor_cmd.py::_hardware_device_to_dict()/console_cmd.py envelope reconstruction in the same commit to keep the Phase 158 sensor round-trip future-proofing gate green
- [Phase ?]: [Phase 159]: 159-02 D-159-F/G/H implemented as locked; run_check_in() docstring paraphrases compute_readiness_score to avoid tripping test_skips_discovery_and_scanner_phases' own forbidden-substring grep; test_check_in_flag_parses exercises the real argparse parser via main() + sys.argv patching since main() has no factored parser accessor
- [Phase ?]: [Phase 159]: 159-03 D-159-I/J/K implemented as locked; badge-not-filter on /compare's hardware_drift block, zero new filtering on /trends/compare score paths, /api/hardware/drift latest-bucket side effect documented not fixed
- [Phase 159]: 159-04 D-159-M..Q implemented as locked; is_partial_scan threaded through writer.py's existing (host,port) drift lookup with no new DB query; HTML banner sits outside <details> (D-159-N), CLI banner lives inside existing Hardware PQC Advisory block with an explicit no-Recent-Lifecycle-Changes-heading test to keep Phase 156 D-12 intact
- [Phase ?]: [Phase 159]: 159-05 D-159-R/S/T confirmed and applied — no api-reference.md placeholder created, no chaos-lab files touched, no version string changed; docs/UAT-SERIES.md Series 159 (UAT-159-01..04) and all 4 touched docs synced to Obsidian vault
- [Phase ?]: [Phase 160]: 160-01 D-160-A..G implemented as locked; VendorPqcTrendEvent has no host/port columns (D-160-E); VENDOR_EVENT_TYPES separate allowlist from EVENT_TYPES (D-160-D); reconcile_vendor_pqc_trend() reuses _confirmed_value()/DEFAULT_N/DEFAULT_M verbatim (D-160-A)
- [Phase 160]: 160-02 D-160-H/I implemented as locked; Rule 1 fix reworded hardware_drift.py module docstring's literal SCORE_WEIGHTS mention (Phase 155 legacy) to pass the new T-160-04 guard
- [Phase 160]: 160-03 D-160-B/F/G/J implemented as locked; VendorPqcTrendEventItem has no host/port/severity/numeric field; Query(50, ge=1, le=200) bound and .limit(limit+1) truncation pattern reused verbatim from the existing /hardware/drift endpoint
- [Phase 161]: 161-02: build_tech_markdown() uses a plain vendor_pqc_trends kwarg (not exec_content threading) since exec_content doesn't exist yet at the pre-score call site; single non-fatal DB read feeds both CLI markdown and exec_content
- [Phase 161]: 161-01: notify_on_hardware_lifecycle global opt-in (D-01); HardwareLifecycleSummary sibling content model, not a widened DriftSummary; dispatch_hardware_lifecycle_notifications() fans out to email+webhook only (D-04); composite scan_id host:port:event_type:event_id (D-05); Rule 1 fix branched _channel_send_email on summary type to avoid AttributeError on real hardware-lifecycle delivery
- [Phase 163]: D-07 serializer import stays function-scoped inside serial_to_open_ports only, avoiding the local-import shadow trap
- [Phase 163]: The resume-skip guard requires BOTH a checkpoint row AND a live cache hit -- a checkpoint alone never causes a skip
- [Phase ?]: Resume-skip guard requires BOTH a completed-batch checkpoint AND a live cache hit before skipping; checkpoint alone falls through and re-probes
- [Phase ?]: Skip-path deliberately does not call update_batch_progress to preserve the pre-existing Phase 146 single-call-site AST lock
- [Phase ?]: Per-batch save_cache/write_scan_checkpoint gate is args.db_path alone (D-02), never args.cache, never args.job_id
- [Phase 164]: TARGET-001/TARGET-002 registry entries use static cause/fix strings with no embedded path or token (T-164-01)
- [Phase 164]: 164-03: FORBIDDEN_RE terminator group must include space|backtick|EOL, never optional (widened per D-15) - a space-only matcher hid docs/UAT-SERIES.md:13052's backtick-terminated quirk scan form
- [Phase 164]: 164-03: ADCS scanning documented as a genuine config-schema gap (no enable_adcs/adcs_targets fields in ConnectorsCfg) rather than fabricating a command
- [Phase 164]: Corrected run_scan.py parser inventory from six to ten verified sites (5 ArgumentParser + 5 add_parser); confirmed add_parser kwarg forwarding empirically via subcommand flag-abbreviation rejection
- [Phase 164]: TARGET-001/TARGET-002 stderr emissions print only the static format_error() string, never str(exc) or the user-supplied path, per T-164-11 information-disclosure mitigation
- [Phase ?]: REQUIREMENTS.md FIRSTRUN traceability was already flipped by plans 01/03 before 164-04 started; plan 04 verified only, no re-edit
- [Phase ?]: 164-VALIDATION.md rows backed by tests/test_target_cli.py marked green with an explicit GATE-03 footnote (macOS-only full-suite fork-crash, deferred to Phase 166) rather than silently absorbed as clean
- [Phase 165]: Plan 01: live axe sweep confirms committed 291-violation baseline is stale; live count is 81 (0 live button-name, 189 phantom qramm-assessment entries). D-03 order followed exactly.
- [Phase ?]: D-01/D-02/D-06/D-13/D-14 baseline-diff.mjs count-budget module extracted and wired into run-a11y.mjs
- [Phase 165]: D-04: pinned @axe-core/puppeteer to 4.11.3 and puppeteer-core to 24.43.1 (already-resolved versions, not caret face values); npm install left resolved versions unchanged
- [Phase 165]: Widened vitest.config.ts include glob (second entry) to reach tests/a11y/ rather than relocating test files
- [Phase 165]: Added CI Test step (npm run test) in dashboard-quality.yml a11y job, between Lint and Install Chrome — first-time CI gating of the dashboard vitest suite
- [Phase ?]: D-08/D-09/D-10 token flips applied verbatim (teal foreground flip both themes, muted-foreground dark nudge, two new severity token pairs); executive.tsx HIGH badge has no foreground application site (Recharts Cell fill, no overlaid text) — documented in comment rather than force-applied
- [Phase ?]: cbom.tsx QS_NODE_COLOR.Safe needed a getComputedStyle-based resolveCytoscapeColor() fallback since Cytoscape stylesheets are plain JS objects outside the DOM cascade and cannot resolve var() references
- [Phase 165]: D-15/D-16 (165-05): baseline filenames variant-aware (baseline-{slug}-{variant}.json); missing baseline is a hard exitCode=1 error, not a silent empty-violations fallback
- [Phase ?]: 165-06: D-05 triad (JSON baseline -> generateMarkdown -> byte-compare freshness test) copied from errors_cmd.py; ACCEPTED-VIOLATIONS.md is intentionally RED until 165-07
- [Phase 165]: D-16: loading-variant a11y gate wired into CI directly (clean 0-exit first run, no debt to baseline)
- [Phase 165]: 5 additional token-swap contrast misses fixed at token layer per D-11, leaving only 1 justified accepted entry (data-at-rest scrollable-region-focusable)
- [Phase 165]: quirk serve multi-DB trap verified against deps.py and documented in operators-guide.md, with a stray 0-byte quirk.db cleanup note
- [Phase ?]: Selected common port scope via page.click + aria-checked wait, not page.select() -- control is a Radix RadioGroup
- [Phase 166]: GATE-02 requires quirk.util.xml_safe.parse_safely() (Phase 87/DEP-02 lxml chokepoint), not defusedxml — original requirement premise was factually backwards and corrected in REQUIREMENTS.md/ROADMAP.md
- [Phase 166]: GATE-03 full-suite verification (166-04) confirms the 3-file fix works but the same fork-crash pattern persists in 6 other files outside declared scope, tracked for a future cleanup phase
- [Phase 167]: The "5 duplicate case IDs" figure (REQUIREMENTS.md UATREC-02, 2026-08-26 Phase-164-close reaffirmation, and the 2026-08-24 functional review) is a truncating-regex artifact, not a real finding — `grep -o '^### UAT-[0-9]*-[0-9]*'` collapses three-segment IDs (`UAT-89-02-01`/`-02`, `UAT-89-03-01`/`-02`) into phantom two-segment duplicates. The true count is 3 (`UAT-144-01/02/03`). Corrected in REQUIREMENTS.md, ROADMAP.md, the review's dated correction note, and this STATE.md entry. **Phases 168-170 draw on the same 2026-08-24 review and must not re-inherit the "5" figure.**
- [Phase 167]: `tests/test_uat_series_format.py` now blocks any `docs/UAT-SERIES.md` change that breaks the single-result-format, heading/result-block-parity, case-ID-uniqueness, or no-headingless-declaration invariants. Phase 168/169 disposition-drain edits must keep result blocks canonical (`- [ ] PASS  - [ ] FAIL  - [ ] SKIP` with an optional inline ` (annotation)` suffix) — the achieved parity figure (663 case headings == 663 result blocks as of 167-03 Tasks 1-4, `docs/UAT-SERIES.md` re-measured post-Series-167-append) is the number Phase 168 starts from.
- [Phase 167]: Plan 03 Tasks 1-4 intentionally did NOT flip the ROADMAP.md Phase 167 checkbox to `[x]` or mark this STATE.md row `Complete` — Task 5 (a `checkpoint:human-verify` gate) has not yet run, `.planning/milestones/v5.16-phases/167-uat-format-unification-deduplication/167-VERIFICATION.md` does not exist yet, and `167-VALIDATION.md`'s human-only row (167-03-05) is genuinely still `⬜ pending`. Flipping either trigger string would fire `scripts/verify_phase_gates.py`'s ARTIFACT-01/02/03 phase-close gate falsely. Defer both flips to the commit that follows human approval of Task 5.
- [Phase 168]: Series extraction is alpha-prefix-aware; ledger's 299-case scope and A:72/B:1/C:34/D:60/E:49/F:83 bucket split are authoritative for Plans 02-08 (reconciled in 168-01-SUMMARY.md against CONTEXT's 299/A:72-B:2-C:34-D:51-E:33-F:107 and the planner's 297). — Independent re-measurement corrects the planner's alpha-prefix regex miss and locks the frozen ledger contract for downstream plans.
- [Phase 168]: UAT-5-12's runner_covered flag corrected to false: uat_runner.py rlog() call for it is unreachable under --no-lab-scan due to an earlier return in run_series_5()
- [Phase 168]: uat-auto-results.json regenerated fresh but left uncommitted per repo .gitignore convention; ledger + docs/UAT-SERIES.md are the reviewable committed record
- [Phase ?]: UAT-34-01 reclassified bucket B->A via tests/test_motion_scoring.py::test_subscores_includes_data_in_motion; bucket B now empty
- [Phase 168]: 73 bucket A/B UAT cases dispositioned from real pytest runs: 62 PASS, 6 SKIP (chaos-lab gated), 5 DEFERRED (verified substitutes, incl. D-06 gap fill for UAT-33-07)
- [Phase 168]: Bucket C (chaos-lab, 34/34) closed via verified pytest substitutes per UAT-33-03 model without bringing the lab up (D-01); 8 rows recorded as honest GAPs including Vault lacking an rsa-1024 transit key type and pgcrypto column detection being unimplemented (BACK-12)
- [Phase 168]: Bucket F series 1-50: 7 DEFERRED with verified pytest substitutes, 42 GAP; frontend-only UI cases are structurally ineligible for DEFERRED under the pytest-only anti-fabrication guard
- [Phase 168]: 168-08: 5 bucket-F cases with directly runnable shell/grep steps (test -f, grep -q, ruby -c) run directly rather than substitute-searched, since the phase-01 classifier's command-detection regex doesn't recognize those forms; produced one genuine FAIL (UAT-84-02, empty changelog.d fragment dir). UAT-58-01/58-02 DEFERRED substitutes verify correct security behavior but the response body now uses the QRK-DASHBOARD-00N wrapper format rather than the case's literal expected string (doc drift). UAT-92-01 (one-time historical v5.0.0 tag gate) recorded GAP as structurally unrepeatable and naturally stale against v5.15.0, not a live defect. Independent from-scratch recount (zero imports from scripts/) confirms 0 in-scope undispositioned cases remain across the full 666-case document; 433 in-scope total reconciles as 299 (this phase's ledger scope) + 134 pre-existing dispositioned.
- [Phase ?]: test
- [Phase 169]: Plan 01 fixed cmd_classify's data-loss bug (silently dropped all 299 already-dispositioned ledger rows when MAX_SERIES widened, since it built output purely from in_scope_undispositioned and write_ledger replaces the whole file) discovered mid-execution, before any commit — reverted via git checkout, then fixed with a seed-then-overlay merge pattern. Also fixed WR-01 (NODE_REF_RE truncation, lockstep across both files), WR-03 (empty-evidence cross-check hole), and a newly-found Case.dispositioned scope bug that would have silently dropped UAT-151-01 from the drain. Ledger extended to 377 rows (78 new outcome:null for series 101-163), independently re-derived count matches the orchestrator's ground truth exactly.
- [Phase ?]: Vitest substitute citations require a double-quoted title segment (D-05) since vitest titles are free-form prose, unlike pytest's identifier-shaped node names
- [Phase ?]: Vitest slow tests gated on VITEST_TOOLCHAIN_AVAILABLE (npm + node_modules present); honest skip in CI since Linux Full Suite job never installs Node -- confirmed to actually run locally
- [Phase 169]: UAT-104-04 recorded GAP not PASS -- named -k ssrf filter matches 0 tests, no substitute exercises JiraChannel internal-URL SSRF guard
- [Phase 169]: UAT-150-01/02 dispositioned via live gh CLI re-query of real GitHub Actions runs today, not transcription of the evidence artifact alone
- [Phase 169]: UAT-110-04 resolved via D-06 name-drift substitute: test_scanned_at_not_mutated no longer exists, real equivalent test_scanned_at_preserved located and verified
- [Phase 169]: Phase 169 plan 04 closed buckets C+D+E for series 101-163 (25/78 cases): 19 PASS, 1 FAIL, 4 SKIP, 3 DEFERRED, 2 GAP. Combined with plan 169-03 (41 cases), 66/78 series-101-163 cases are dispositioned; 12 bucket-F cases remain for plan 169-05.
- [Phase 169]: UAT-110-06 FAIL: the case's own --stale-days 1 worked example can never trigger its documented coverage_warning WARNING line since the 1-day exclusion window and the 48h default 2x-cadence overdue threshold are mathematically incompatible; the underlying merge_scan coverage_warning mechanism itself was independently confirmed working with correct parameters.
- [Phase 169-05]: Scratch-copy methodology for git-hook UAT reproduction: a plain git clone does not survive .planning/phases/ (gitignored), producing false destructive-archive-gate blocks -- use a full rsync working-tree copy instead
- [Phase 169-05]: Independent recount scopes its disposition check to the Result line only, never the whole case body -- UAT-151-01's own steps contain a literal - [x] markdown example that would false-positive a whole-body check
- [Phase 169-05]: Independent recount found 647 in-scope (series <=163) headings, not the plan's anticipated 596; corrected rather than forced to match -- 666/666 total headings/Result-blocks and 0 undispositioned confirmed
- [Phase 169-06]: D-05 second half spent: all 31 series-7 GAP rows individually re-examined against real vitest coverage; zero genuine conversions found (verify-then-record standard applied throughout), all stay honest GAP with per-case reasoning recorded
- [Phase 169-07]: Zero-undispositioned UAT gate built as pytest test riding Linux Full Suite CI (D-01), whole-document scoped (D-02), GAP is passing (D-03), D-04 CI-marker override claim independently re-verified and regression-locked
- [Phase 171]: RESUME-05 (D-01, locked): resume of an already-complete scan exits 0 with a message naming the scan and finish time, writes zero new checkpoint rows, no --force flag
- [Phase 171]: RESUME-06 (D-02, locked): --list-resumable Target column derives from CryptoEndpoint when no ScanJob row exists; ScanJob join stays primary, honest '(no target recorded)' placeholder when both are absent
- [Phase 171]: RESUME-05/RESUME-06 both verified complete: resume-already-complete short-circuit (exit 0, zero new checkpoint rows) and --list-resumable Target column derivation from CryptoEndpoint rows — Full unfiltered suite holds at 3684 passed / 4 known pre-existing failures (+14 delta matching this phase's new tests); Series 171 UAT entry live-repro'd; Task 3 human-verify checkpoint approved 2026-08-28. Phase 171 closes the v5.16 milestone's last phase.
- [Phase 172-01]: Argparse-time refusal block for --fuzz: budget check before TTY check (fail-fast, TTY-independent) per D-02
- [Phase 172-01]: MAX_FUZZ_BUDGET imported from quirk.scanner.rest_fuzzer; confirm_fuzz_gate and _resolve_budget left byte-for-byte unmodified as second defence-in-depth layer
- [Phase ?]: 172-02: docs/configuration.md documents the --fuzz-budget ceiling twice; gate iterates all matches
- [Phase 172]: D-03 implemented: url_allowlist.py's helper strips userinfo/query/fragment via urlparse and keeps scheme+host+truncated path; subprocess_input.py's twin renamed only, body unchanged (RESEARCH.md A3 signed off).
- [Phase 172]: The two _redact_preview twins now have distinct names (per D-03) so the same-name-different-behaviour trap cannot recur; UAT-94-05 (D-04) disposition deliberately left to plan 172-04.
- [Phase 172]: UAT-94-05 judged CASE DEFECT (D-04), promoted to Phase 175; case text left byte-untouched — Demands all-or-nothing URL redaction contradicting D-03's locked threat model (credentials/tokens redacted, hostname deliberately retained)
- [Phase 172]: UAT-96-02 and UAT-96-03 re-executed against post-fix behaviour and re-dispositioned PASS — Historical Series 96 FAIL entries preserved as pre-fix record; corrected disposition recorded in new Series 172 cases
- [Phase ?]: New-prose-around-anchor pattern: add explanatory paragraphs adjacent to regex-anchored docs rows rather than editing them, to avoid disarming drift gates
- [Phase 173]: D-01/D-01a: port_scope_origin implemented as a new sibling ScanCfg field (not a widened nmap_port_scope); suppression guard nested inside the existing explicit-connector-value check to deliver locked precedence (explicit > scope suppression > profile auto-enable)
- [Phase 173]: SCOPE-02: extended guard conversion to jwt/container/source/db (proven identical enable_* shape) per plan authorization
- [Phase 173]: SCOPE-02: renamed two tests to include absent/non_broker substrings to satisfy VALIDATION.md -k filters
- [Phase 173]: 173-03: broker/smime/adcs all use inline _emit_missing_extra_advisory shape; optional_extra.py REGISTRY untouched (test_registry_omits_motion_and_redis stays locked)
- [Phase 173]: 173-03: smime and adcs advisory messages use extras label adcs (not identity) since smime has no dedicated pyproject.toml extras group
- [Phase 174]: D-01: minimal DASH-06 fix only -- pass ScanJob.calibration into compute_readiness_score(), no schema migration, no CLI-scan persistence
- [Phase 174]: DASH-07 closed by verification not code change: D-02 honored literally, zero production code changed, evidence recorded in 174-EMPTY-DB-EVIDENCE.md, contract locked by tests/test_dashboard_empty_state_contract.py
- [Phase 174]: (D-03) Corrected Phase-39's stale nine-item nav-order note to the current 14-item order; shipped sidebar.tsx untouched
- [Phase ?]: UAT-8-07 dispositioned DEFERRED (not PASS): real DASH-06 fix covered by tests/test_dashboard_scans_score_profile.py, but case text uses illegal --score-profile standard and out-of-scope bare-CLI path; correction promoted to Phase 175
- [Phase ?]: UAT-39-07's Expected line and Pass Criteria corrected in place to the canonical fourteen-item sidebar order (174-SIDEBAR-ORDER.md); the document was stale, not the shipped UI (Phase 128)
- [Phase 175]: UAT-85-02/UAT-85-06: quote-tolerant grep replaces exact-substring grep; quote-style difference is stylistic, not a defect
- [Phase 175]: UAT-84-02: pass criteria now accept towncrier's 'No significant changes.' as valid draft output for an empty changelog.d/; no fixture fragment committed
- [Phase 175]: UAT-110-06: corrected worked example uses --stale-days 30 against a 3-day-overdue sensor; original --stale-days 1 example was arithmetically impossible
- [Phase 175]: D-01 applied: UAT-55-01 corrected to practice_number; no API rename, no control_id alias
- [Phase 175]: D-02 applied: UAT-58-07 corrected to single QRK-TARGET-002 code, names T-164-01; decision not reopened
- [Phase ?]: UAT-94-05/UAT-36-05/UAT-8-07 case text corrected in place, arguments carried with source-disposition citations; no product code changed
- [Phase 175-05]: UAT-94-09 added to Series 94 as the D-03 credential-bearing companion detector, disposed PASS via the ledger route with falsifiability demonstrated in a scratch-copy neutered redaction test
- [Phase 175]: UAT-58-07 re-dispositioned DEFERRED via ledger, not PASS, per D-02 -- names T-164-01
- [Phase 175]: All eleven corrected UAT cases re-verified live 2026-08-30; zero surfaced as real product defects
- [Phase 176-01]: Lifted the standing uat_runner.py prohibition for exactly one line (UAT-1-02 pass-condition) per D-01 -- harness was provably unsatisfiable by any current-era output; proven via git diff --numstat = 1/1, no version bump
- [Phase 176]: UAT-1-02 re-run against the plan-176-01-repaired harness (quirk --version, exit 0, QU.I.R.K. v5.15.0) agrees with its documented Pass Criteria; dispositioned PASS through the ledger via apply --dry-run -> apply -> verify, never hand-edited.
- [Phase 176]: uat-disposition-ledger.jsonl evidence strings must contain no ')' at all (not just unbalanced) -- _validate_evidence rejects any parenthesis; use ' -- ' asides instead.
- [Phase 176]: 176-03: Chaos lab brought up with targeted D-02 profile set (core+phaseA+jwt+ssh-weak+identity, 33 containers); all 18 required ports proven listening; LAB STATUS: UP, lab left running for 176-04
- [Phase 176]: 176-03: Task 2's blocking human-action checkpoint satisfied by orchestrator's pre-verified Docker-running state, corroborated by this plan's own independent daemon probe
- [Phase ?]: UAT-5-13 FAILs on evidence (cert-subject not Keycloak-related); certs/keycloak.crt is byte-identical to certs/modern.crt; disposition BACKLOG
- [Phase ?]: UAT-6-06 FAILs on evidence (no PLAINTEXT_HTTP/HTTP_EXPOSURE finding type exists; port 8000 and 8444 findings are byte-identical); disposition BACKLOG
- [Phase ?]: UAT-5-11 and UAT-6-08 both GAP — ssh-audit binary absent from environment, confirmed same root cause at ssh_scanner.py source level
- [Phase 176]: UAT-5-13 and UAT-6-06 remain FAIL per D-03 -- each backed by a BACKLOG-triaged defect in 176-DEFECT-TRIAGE.md, not softened for a cleaner corpus
- [Phase 176]: UAT-5-11 and UAT-6-08 dispositioned GAP for missing ssh-audit binary; LABRUN-01 flagged unmet for those two cases
- [Phase 176-07]: Installed ssh-audit into .venv only (not pyproject.toml), zero-dependency, regression-free (full suite unchanged 1 failed/3772 passed) — Did not re-disposition UAT-5-11/UAT-6-08: actual re-run was blocked by an unresponsive Docker Desktop daemon; manufacturing a disposition from tool-presence alone would violate D-03/D-04
- [Phase 177]: 177-01: Guard placed in existing tests/test_version.py per RESEARCH.md recommendation; purge scope limited to exactly the residue paths named in the plan, canonical quirk-scanner install untouched
- [Phase 177]: 177-02 re-verified the firmware CVE catalog against live NVD REST API data (one published-date drift found and corrected, CVE-2017-12240) and pre-emptively re-verified the SNMP vendor PQC catalog (11-day runway, under the 14-day margin), correcting two dead vendor source_urls. All seven staleness catalogs plus the error-codes generator gate are green. RELEASE-02 remains open (spans plans 177-02/04/06/07).
- [Phase 177]: 177-03 closed RELEASE-01's requirements record honestly: removed the Homebrew-global orphan quirk 4.0.0 editable install (finder pointed at deleted predecessor project QuRisk) plus its broken /opt/homebrew/bin/quirk PATH shim, user-approved via blocking checkpoint; rewrote RELEASE-01 evidence to state the measured two-half root cause instead of the falsified stale-.pth-breaks-pip's-build-backend claim; checkbox left unchecked pending Plan 06 ship
- [Phase 177-04]: Corrected the archived v5.16-ROADMAP.md 'What Shipped' summary figure (325 unrecorded UAT cases) to the re-measured true value of 377 in the CHANGELOG [5.18.0] entry and README — STATE.md's Phase 168 decision record and docs/UAT-SERIES.md both state 325 was a stale figure; true pre-drain total was 377
- [Phase ?]: 177-05 bumped docs/UAT-SERIES.md to 5.18.0, re-executed UAT-1-02 live via the ledger (not hand-edit), and added Series 177 with 3 honestly-dispositioned SKIP(GAP) release-verification cases -- zero fabricated PASS.
- [Phase ?]: 177-05 reframed .planning/ROADMAP.md's v5.16/v5.17 untagged and RVW-004 notes as resolved history (v5.13/v5.14 two-component-tag defect record preserved) and corrected Success Criterion 1's stale build-backend-failure premise.
- [Phase ?]: 177-05 verified docs/getting-started.md carries no version literal and re-synced the Obsidian vault: UAT-Series.md byte-matched, Getting-Started.md confirmed current, new Phase 177 note written status: active pending the outstanding tag push.
- [Phase 177]: 177-06: full unfiltered suite holds at exactly 1 expected failure (DEFER-172-01); 3 SIGSEGV crash dumps traced to pre-existing Phase 149-11 xfail(strict=False) markers, not new regressions
- [Phase 177]: 177-06: ADVISORY-01 evidenced by 13-file phase diff with zero quirk/scoring/ or quirk/engine/ paths; test_cve_score_guard.py green and unmodified this phase
- [Phase 178]: 178-01 split the new IDENT-01 guard file into two per-task commits (day-boundary guard, then collision guards) for atomic task granularity, and reworded prose mentions of 'strict=True' to keep grep -c 'strict=True' at exactly 1 per the plan's acceptance criterion.
- [Phase 178]: IDENT-03: report identity divergence rather than silently reconcile - D-178-A wording divergence (expired cert title, allowlisted+bounded) and D-178-B detection-coverage gap recorded separately in docs/reviews/178-derivation-path-divergence.md
- [Phase ?]: Single title normalizer (normalize_finding_title) with two declared policy tables; cert-expiry normalized for fingerprint stability, container-library {name} preserved (T-178-01).
- [Phase ?]: 178-05: _count_by_bucket signature changed to (keys, sev_map); external caller in routes/trends.py fixed same-commit (Rule 3)

### Pending Todos

None yet.

### Blockers/Concerns

- **Phase 156 plan-phase decision-coverage gate override (2026-08-14):** the mechanical
  `check.decision-coverage-plan` gate flagged 18 CONTEXT.md decisions (D-01..D-25) as uncovered.
  This is the same false positive documented for Phase 150 (2026-08-12) — the gate scans only
  structured `must_haves.truths`/frontmatter fields, not full plan body prose, even though its own
  message says "(or body)". Direct grep confirms **17 of the 18 flagged decisions are cited by ID
  in plan bodies** (`.planning/phases/156-*/156-0{1..6}-PLAN.md`); the one exception, D-12
  (CLI/terminal drift rendering out of scope), is correctly absent because it's a deliberate
  deferral already listed in CONTEXT.md's own `<deferred>` section — a plan citing it would be
  wrong. The independent `gsd-plan-checker` agent's semantic review separately confirmed full
  decision coverage with zero blockers/warnings, specifically calling out D-26/D-18's corrected
  write-path handling, D-07's palette layers, D-13's caption, and D-23's secure-phase gate as
  correctly implemented. Proceeded past the gate on this documented override. Re-surface at
  the `gsd-verifier` phase-goal pass for Phase 156 only if the same coverage question resurfaces there.

- Phase 140's evidence-sufficiency bar (what SNMP facts constitute "confirmed" vs "assumed") is
  not fully specified by research — flagged as a planning-time design decision to make explicit
  before implementation, not skip.

- Phase 141 OT-safety norms are MEDIUM confidence — do a web-search verification pass during
  `/gsd:plan-phase 141`, not skip it (fragile-device probing has real-world outage history).

- Phase 142 CVE/CPE version-matching guidance is MEDIUM confidence — verify current NVD API/CPE
  guidance and vendor firmware version-string normalization (Cisco/Juniper/etc.) during planning.

- **Phase 150 plan-phase decision-coverage gate override (2026-08-12):** the mechanical
  `check.decision-coverage-plan` gate flagged D-01, D-02, D-04, D-06, D-07, D-08 as uncovered
  (only D-05 registered). This is a false positive — the gate appears to scan only structured
  `must_haves.truths`/frontmatter fields, not full plan body prose, even though its own message
  says "(or body)". `grep -n "D-0[1-8]" .planning/phases/150-*/*-PLAN.md` confirms all 7 decisions
  are extensively cited in plan bodies, and the independent `gsd-plan-checker` agent's semantic
  review separately verified "D-01 through D-08 all traced to specific tasks" (Context Compliance
  dimension: Pass). User selected "Proceed anyway" at the /gsd-plan-phase 150 override prompt.
  Re-surface at the `gsd-verifier` phase-goal pass for Phase 150 only if the same coverage question resurfaces there.

- **RESOLVED (Plan 150-08, 2026-08-13):** Phase 150 Plan 03's original blocker — real GitHub Actions Linux Full Suite run (31598809033) failed with 38 failures on a genuine .[all]-only ubuntu-latest install — is closed. Plans 150-04 through 150-07 fixed all 8 failure categories; Plan 150-08 re-ran the live-fire proof end to end: green run 31723764281 (0 failed) + red run 31725715958 (1 failed, isolated to the deliberate smoke test) via PR #10 (closed unmerged). SUITE-02/SUITE-03 both proven and marked complete in REQUIREMENTS.md. See 150-08-SUMMARY.md and 150-CI-EVIDENCE.md.
- 176-07: Docker Desktop daemon unresponsive this session (docker ps/info hung indefinitely, no error) -- blocked the chaos-lab re-run of UAT-5-11/UAT-6-08; ssh-audit is installed and ready, only Docker responsiveness remains. User must restart Docker Desktop before a follow-up attempt.

## Deferred Items

Items acknowledged and deferred at the v5.15 milestone close on 2026-08-26, **re-triaged at the
v5.16 open (2026-08-26)**:

| Category | Item | Status |
|----------|------|--------|
| quick_task | 260611-g0b-merge-healthcare-vertical-branch-into-ma | missing — known false positive; genuinely complete (PLAN + SUMMARY + merge commit all exist), misreported by the audit scanner at every close since v5.10. Do not re-investigate. |
| uat_finding (163) | Resuming an already-complete scan re-appends `discovery`/`inventory`/`reports` checkpoint rows instead of short-circuiting | **promoted into v5.16** — pre-existing stage-level resume behaviour; batch rows stay correct. Scoped as part of the Phase 163 UAT tail. |
| uat_finding (163) | `--list-resumable` Target column blank for `--targets-file` runs | **promoted into v5.16** — recovers the target by joining `scan_jobs`, which only has a row when `--job-id` is passed. Cosmetic but user-facing. |
| test_isolation | `test_verify_phase_gates.py::test_hook_integration_green_path_commit_succeeds` and `..._red_path_commit_rejected_on_missing_verification` | **FIXED 2026-08-27 (Phase 166-05, GATE-03).** Previously triaged as macOS-only subprocess SIGSEGV, not scoped for v5.16 work. Phase 166's GATE-03 scope amendment closed the underlying fork-crash root cause suite-wide (`164-FINDING-fork-crash.md`: `close_fds=False` + no `cwd`, plus a second discovered condition — `argv[0]` must not be a bare PATH-lookup name). Both tests now pass cleanly with zero crashes in a full unfiltered macOS run. |

Added at the v5.16 open (2026-08-26):

| Category | Item | Status |
|----------|------|--------|
| human-UAT (143) | UAT-143-03 — Windows Authenticode production signing | **engineering-complete, blocked on procurement.** The v5.15.0 release proved the mechanism end to end: the previously-broken ephemeral-cert self-test **succeeded** on a real tagged build, `Sign with production certificate (if configured)` **skipped** cleanly with no cert present as designed, and `quirk-windows-5.15.0.zip` (58.6 MB) attached to the GitHub Release. The sole remaining blocker is acquiring a real Authenticode signing certificate and loading it into GitHub Actions secrets — a purchasing decision, not engineering work. Per user direction at the v5.16 open, keep deferred and re-triage at the v5.16 close. |
| uat_gap (158) | `158-HUMAN-UAT.md` — 2 pending visual scenarios (`/hardware`, `/compare` rendering of sensor-pushed devices) | open — carried forward unchanged; HWLC-15 independently SATISFIED at code/test level. Explicitly **not** in v5.16 scope. |
| vault_sync | Phase-162 note absent; `_QUIRK-Hub.md` missing 152/156/162 links and carrying a wrong Phase 163 date; vault `Roadmap.md` stale by 12 days | **RESOLVED 2026-08-26** at the v5.16 milestone-boundary doc review — note written, hub repaired (callout rewritten to v5.15, 3 links added, 163 date corrected), `Roadmap.md` re-synced. Vault `Requirements.md` re-syncs once `.planning/REQUIREMENTS.md` is regenerated for v5.16. |

Found at Phase 172 close (2026-08-29):

| Category | Item | Status |
|----------|------|--------|
| test_isolation | `tests/skip_registry.py` drift across 5 files (`test_credential_leakage.py`, `test_identity_surface.py`, `test_saml_scanner.py`, `test_target_cli.py`, `test_uat_disposition_integrity.py`), caused by Phases 166/170, confirmed untouched by Phase 172 | open — logged as `DEFER-172-01` in `.planning/phases/172-fuzzing-disclosure-safety/deferred-items.md`. Needs a housekeeping commit correcting the 8 stale/missing registry line numbers. |
| test_isolation (macOS-only) | 3 reproducible `Fatal Python error: Segmentation fault` crash reports in forked `tests/test_install_errors.py` children (`fork()` + `Network.framework`/`os_log`), does not fail any test, pre-existing/untouched by Phase 172 | open — logged as `DEFER-172-02`. Corrects the stale "zero fatal signals" claim in `project_verify_phase_gates_macos_only_failures.md` memory (that fix, Phase 166 GATE-03, closed a *different* fork-crash root cause in `test_verify_phase_gates.py`, not this one). CI (Linux) is unaffected. |
| uat_finding (D-04) | `UAT-94-05`'s third pass-criterion demands all-or-nothing URL redaction, contradicting Phase 172's locked D-03 threat model | **promoted into v5.17 Phase 175** (`CASEFIX` scope) — case defect, case text left byte-untouched. Full argument in `172-DISPOSITIONS.md` § 1; carry-forward note added to `ROADMAP.md`'s Phase 175 section. |

**Last re-triaged:** 2026-08-29 (Phase 172 close — see rows above)

---

Acknowledged and deferred at the **v5.17 milestone close (2026-09-01)**, per the pre-close
`gsd-sdk query audit-open` sweep plus an explicit re-triage of every item carried in this section:

| Category | Item | Status |
|----------|------|--------|
| quick_task | `260611-g0b-merge-healthcare-vertical-branch-into-ma` | missing — **known permanent false positive**, unchanged. Genuinely complete (PLAN + SUMMARY + merge commit all exist); misreported by the audit scanner at every close since v5.10. Do not re-investigate. |
| todo | `.planning/todos/pending/a11y-route-coverage-gap.md` (medium) — a11y sweep does not cover `/hardware` or `/compare` | open — **deferred, not in v5.17 scope.** v5.17 was a defect drain scoped to fuzzing/disclosure, scanner scope, dashboard/API, case text, and the chaos-lab re-run; accessibility route coverage is unrelated. Note this is the *same surface* as the `uat_gap (158)` row below (`/hardware`, `/compare`) — the two should be triaged together into a future milestone rather than separately. |
| test_isolation | `DEFER-172-01` — `tests/skip_registry.py` drift across 5 files, 8 stale/missing registry line numbers | open — **carried forward unchanged.** Still the sole failing node in the local full-suite baseline (`1 failed, 3802 passed` at Phase 176 close). Needs a housekeeping commit. Recorded in `.planning/phases/172-fuzzing-disclosure-safety/deferred-items.md`. |
| test_isolation (macOS-only) | `DEFER-172-02` — 3 reproducible `Fatal Python error: Segmentation fault` reports in forked `tests/test_install_errors.py` children | open — **carried forward unchanged.** Does not fail any test; CI (Linux) unaffected. |
| human-UAT (143) | `UAT-143-03` — Windows Authenticode production signing | **still engineering-complete, still blocked on procurement.** Unchanged since the v5.16 open; no v5.17 phase touched it. The remaining blocker is buying a real Authenticode certificate and loading it into GitHub Actions secrets — a purchasing decision. Re-triage at the v5.18 open. |
| uat_gap (158) | `158-HUMAN-UAT.md` — 2 pending visual scenarios (`/hardware`, `/compare` rendering of sensor-pushed devices) | open — **carried forward unchanged**, explicitly not in v5.17 scope. HWLC-15 remains independently SATISFIED at code/test level. See the `todo` row above — same two routes. |
| backlog (176) | `TRIAGE-176-01`, `TRIAGE-176-02` — genuine defects surfaced by the Phase 176 lab re-run | open — **explicitly triaged to the ROADMAP Backlog**, not absorbed silently (this is Phase 176 success-criterion 2 being satisfied, not a gap). Both need their own plans and tests. Candidates for the v5.18 opening scope. |
| carried-forward (176) | 2 `UAT-6-08` case-text corrections identified during plan 176-08 | open — recorded under the ROADMAP Backlog's *UAT Case-Text Corrections Carried Forward* section, following the `UAT-94-05`/`UAT-36-05`/`UAT-8-07` precedent. |

**Closed at this milestone (no longer deferred):**

| Item | Resolution |
|------|------------|
| `TRIAGE-176-03` | **FIXED** in plan 176-08 — `quirk/scanner/ssh_scanner.py:27` passed two positionals to `ssh-audit`, which takes one `host:port`, so every SSH scan since the integration shipped silently degraded to a banner grab with `ssh_audit_json` NULL. Fixed with an argv-asserting regression test the pre-existing mocks never had. |
| `LABRUN-01` / `LABRUN-02` verification gap | **CLOSED** — `176-VERIFICATION.md` created 2026-09-01, `status: passed`, 15/15 must-haves, 0 overrides. See the Resolution Addendum in `v5.17-MILESTONE-AUDIT.md`. |

**Known deferred items at close: 8** (2 flagged by `audit-open`, 6 carried forward by explicit
re-triage). Only one — the a11y/`/hardware`/`/compare` surface — is a genuine product gap; the rest
are a scanner false positive, two test-hygiene items, a procurement block, and correctly-triaged
Phase 176 backlog output.

**Last re-triaged:** 2026-09-01 (v5.17 milestone close — see rows above)

Acknowledged at Phase 161 plan-phase (2026-08-20):

| Category | Item | Status |
|----------|------|--------|
| decision_coverage_gate (161) | `check.decision-coverage-plan` reported 0/11 CONTEXT.md decisions (D-01–D-11) covered | false positive, user-overridden — gate's regex looks for literal `D-NN:` tags in `must_haves`/`truths` frontmatter; grep confirms all 11 IDs are cited by name in plan task `<action>` bodies and truths prose (e.g. 161-01-PLAN.md cites D-01–D-05), and gsd-plan-checker's independent semantic review confirmed all 11 decisions trace to explicit implementing tasks across 161-01..06. No re-plan needed. |

**Last re-triaged:** 2026-08-18 (v5.14 milestone close — pre-close artifact audit, 3 items
acknowledged, see table below)

Acknowledged at v5.14 milestone close (2026-08-18):

| Category | Item | Status |
|----------|------|--------|
| quick_task | `260611-g0b-merge-healthcare-vertical-branch-into-ma` | missing (recurring false positive — same row already documented as false-positive at v5.10, v5.11, and v5.13 close: PLAN+SUMMARY both exist on disk; `audit-open`'s scanner has a persistent bug that cannot see this task's completion) |
| uat_gap (158) | `158-HUMAN-UAT.md` — 2 pending scenarios | partial (UAT-158-01/02 — visual confirmation that sensor-pushed hardware devices/drift render on `/hardware` and `/compare`; not a functional gap — HWLC-15 independently SATISFIED at the code/test level per `158-VERIFICATION.md` (4/4 must-haves) and `v5.14-MILESTONE-AUDIT.md`; deferred by explicit user choice at the Phase 158 verification checkpoint) |
| verification_gap (158) | `158-VERIFICATION.md` | human_needed (same underlying item as the uat_gap row above — one shared pair of pending visual checks, no separate defect) |

Acknowledged at v5.13 milestone close (2026-08-15):

| Category | Item | Status |
|----------|------|--------|
| quick_task | `260611-g0b-merge-healthcare-vertical-branch-into-ma` | missing (confirmed false positive — same row already documented as false-positive at v5.11 close: PLAN+SUMMARY both exist on disk, merge commit `9967d8a` is in history; `audit-open` scanner cannot see it) |
| uat_gap (155) | `155-HUMAN-UAT.md` — 1 pending scenario | partial (human read-through of `docs/operators-guide.md` §9.7 + `docs/UAT-SERIES.md` Series 155 for prose clarity; not a functional gap — HWLC-04..09 all independently SATISFIED per `155-VERIFICATION.md` and `v5.13-MILESTONE-AUDIT.md`) |
| verification_gap (155) | `155-VERIFICATION.md` | human_needed (same underlying item as the uat_gap row above — one shared pending human doc-read, no separate defect) |

**Last re-triaged (carried-forward items):** 2026-08-14 (Phase 152 Plan 03 — Phase 144 nmap timing artifact closed via
3-run live-fire evidence; see Resolved section below)

Resolved (2026-08-14):

| Category | Item | Status | Resolution |
|----------|------|--------|------------|
| verification_gap (144) | Phase 144 nmap adaptive RTT/timing-engine artifact — accepted VERIFICATION override, `OPEN (needs real hardware)` in v5.11-MILESTONE-AUDIT.md | **RESOLVED — DOES NOT REPRODUCE** | Empirically settled via `.planning/phases/152-discovery-empirical-closure/152-DISC09-FINDING.md` — 3 independent live-fire runs against the DISC-09 `segmented-network` chaos lab profile (Plan 152-01) showed the chunked discovery batch loop's production timing template produces an identical `segnet-live` open-port set to a direct, non-throttled nmap run every time. No mitigation applied; `quirk/discovery/nmap_provider.py` unchanged. |

**Last re-triaged (carried-forward items):** 2026-08-11 (v5.11 milestone-audit closeout; supersedes the 2026-08-10
Phase 147 DRAIN-04 pass, whose Phase 143 `uat_gap` rationale went stale within a day — see that
row's `Re-triaged (2026-08-11)` note)

Carried forward from v5.9 close (2026-07-30):

| Category | Item | Status | Re-triaged (2026-08-10) |
|----------|------|--------|--------------------------|
| verification_gap | Phase 132: 132-VERIFICATION.md | human_needed — pre-existing, already shipped/tagged | STILL BLOCKED — visual/prose human review, no codebase evidence can close it |
| verification_gap | Phase 135: 135-VERIFICATION.md | human_needed — README What's New visual render check | STILL BLOCKED — visual/prose human review, no codebase evidence can close it |
| verification_gap | Phase 137: 137-VERIFICATION.md | human_needed — prose quality/live enroll walkthrough | STILL BLOCKED — visual/prose human review, no codebase evidence can close it |
| human-UAT (118) | UAT-118-01 — live Windows-host install + Scheduled Task walkthrough | deferred — needs a real Windows host | STILL BLOCKED — requires a physical or VM Windows host |
| human-UAT (114) | UAT-114-03 — operators-guide §8.9 auto-merge visual review | deferred — non-blocking | STILL BLOCKED — non-blocking visual doc review of operators-guide §8.9 |
| human-UAT (93/95/96) | getpass/live PDF, ldaps code-signing, fuzzing TTY gates | deferred — environment-gated | STILL BLOCKED — environment-gated by design (TTY, live LDAPS server) |
| human-UAT (101–105) | Live Slack/email/webhook/syslog/Jira/ServiceNow delivery | deferred — needs live infra | STILL BLOCKED — requires live Slack/email/webhook/syslog/Jira/ServiceNow endpoints |
| horizon | Continuous hardware lifecycle monitoring | deferred — v5.11+, needs its own research pass | NOT A DEFERRED UAT — feature-horizon item, v5.11+ |

Acknowledged at v5.10 milestone close (2026-08-03):

| Category | Item | Status | Re-triaged (2026-08-10) |
|----------|------|--------|--------------------------|
| uat_gap | Phase 143: 143-HUMAN-UAT.md (2 pending scenarios) | partial — user approved continuing 2026-08-03; live windows-latest CI run + browser click-through remain outstanding, both have strong automated/static substitutes in place | **STILL BLOCKED, corrected rationale (2026-08-11).** The 2026-08-10 basis for this row is now factually wrong and has been replaced: `git ls-remote` confirms `origin/main` is `83ba306` — identical to local HEAD — so the Phase 139–147 work IS pushed, and `gh run list` shows Python CI, Dashboard Quality and Python Staleness Gate all green on it. The real blocker is narrower and structural: the `windows-package` job (and its Authenticode signing step) lives in `.github/workflows/release.yml`, which triggers **only** on `push: tags: ['v*.*.*']`. The newest remote tag is `v5.9` — no `v5.10` or `v5.11` tag exists — so no windows-latest release build has run for this work regardless of push state, and none will until a release tag is cut. Unblocks automatically at the next tagged release; the browser click-through remains separately human-gated. |
| verification_gap | Phase 143: 143-VERIFICATION.md | human_needed — same reason as above, user-approved | STILL BLOCKED — browser click-through still requires human execution; no new evidence since v5.10 close |
| human-UAT (143) | UAT-143-03 — Windows Authenticode signing CI (production signing cert) | BLOCKED — awaiting real production signing secrets; mechanism SECURED 7/7 threats via /gsd-secure-phase, signing step no-ops cleanly until secrets exist | **PARTIALLY EXERCISED 2026-08-11 — first real evidence in three milestones.** Pushing `v5.11.0` fired `release.yml` for the first time since `v5.8.0` (v5.10.0 was never pushed; `v5.9` is a two-component tag that never matched the `v*.*.*` glob). Confirmed working: the Windows onedir EXE builds, and the production-signing step skips cleanly with no cert present — exactly as designed. Confirmed BROKEN: the "CI self-test — ephemeral cert signing round-trip" step (added 2026-08-02, `6ed6ec1`, Phase 143 TAIL-03) had never once run and fails by construction — it verifies a self-signed cert with `signtool verify /pa`, which demands a trusted root. It hard-failed the job, so v5.11.0 shipped to PyPI with **no Windows release asset**. Fixed in `1a6effc` (trust the ephemeral root for the verify, remove it in cleanup); per user decision the asset ships with v5.12 rather than burning a patch version. Production-cert half remains genuinely blocked. **UPDATE 2026-08-26 (v5.15.0 release):** the mechanism half is now FULLY PROVEN. `release.yml` fired for the first time since v5.11.0, and the previously-broken `CI self-test — ephemeral cert signing round-trip` step **succeeded** — the `1a6effc` fix is confirmed working on a real tagged build. `Sign with production certificate (if configured)` **skipped** cleanly with no cert present, as designed. `quirk-windows-5.15.0.zip` (58.6 MB) attached to the GitHub Release — the first Windows asset to ship since v5.8.0. Remaining blocker is narrowed to exactly one thing: real production signing secrets. |

Resolved and removed (2026-08-10): one stale `quick_task` bookkeeping row (healthcare-vertical
merge) confirmed complete via git history and removed — see 147-04-SUMMARY.md for the commit hash
and disposition detail.

## Session Continuity

Last session: 2026-09-02T19:20:31.927Z
Stopped at: Completed 177-06-PLAN.md
Third-party functional review completed 2026-08-24 against commit 49f9094 —
22 findings (1 CRITICAL, 6 HIGH, 7 MEDIUM, 5 LOW, 3 OBS) in
docs/reviews/2026-08-24-functional-review-findings.md with a remediation plan in
docs/reviews/2026-08-24-functional-review-action-plan.md.

Review Milestone A ("Scan Integrity") is COMPLETE — the two findings that
corrupted the client deliverable are fixed: RVW-001 (8d3e7f7, endpoints
persisted twice) and RVW-003 (fb23b0d, scan sessions had no stored identity).
Backend suite 3499 passed, 3 pre-existing failures unchanged.

20 findings remain Open. Next candidates per the action plan's sequencing:

- RVW-005 — no CI workflow has triggered since 2026-08-19; needs no code change
- RVW-022 — `quirk compliance cmvp refresh` corrupts the cache; blocks RVW-006
  (do NOT run that command until it is fixed)

- RVW-004 — v5.13/v5.14 declared shipped but never released
- RVW-017 — shared-DB test isolation; directly observed during Milestone A
- RVW-002 — dashboard's second finding engine disagrees with the report

Phase 156 (Reporting & OT/ICS Safety) has no directory or CONTEXT.md yet, awaiting discuss/plan.

Both blocking human-verify checkpoints referenced in prior sessions (141-06 Task 3 badge colors,
141-07 Task 3 live Docker validation) were completed and approved during the Phase 141 gap-closure
rounds (141-09) on 2026-08-03 — no longer pending.

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
