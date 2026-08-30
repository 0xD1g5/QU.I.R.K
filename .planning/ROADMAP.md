# Roadmap: QU.I.R.K. — Quantum Infrastructure Readiness Kit

## Milestones

- ✅ **v3.9 Gap Closure** — Phases 1–11, 40 plans (shipped 2026-04-04) → `.planning/milestones/v3.9-ROADMAP.md`
- ✅ **v4.1 Foundation Polish** — Phases 12–16, 17 plans (shipped 2026-04-08) → `.planning/milestones/v4.1-ROADMAP.md`
- ✅ **v4.2 Identity Crypto** — Phases 17–24, 14 plans (shipped 2026-04-24) → `.planning/milestones/v4.2-ROADMAP.md`
- ✅ **v4.3 Data at Rest** — Phases 25–31, 24 plans (shipped 2026-04-26) → `.planning/milestones/v4.3-ROADMAP.md`
- ✅ **v4.4 Data in Motion** — Phases 32–37, 33 plans (shipped 2026-04-29) → `.planning/milestones/v4.4-ROADMAP.md`
- ✅ **v4.5 Reliability & Gap Closure** — Phases 38–44, 40 plans (shipped 2026-05-03) → `.planning/milestones/v4.5-ROADMAP.md`
- ✅ **v4.6 Enterprise Readiness** — Phases 45–50, 24 plans (shipped 2026-05-05) → `.planning/milestones/v4.6-ROADMAP.md`
- ✅ **v4.7 Governance & Compliance** — Phases 51–56 (shipped 2026-05-08) → `.planning/milestones/v4.7-phases/`
- ✅ **v4.8 Pre-Primetime** — Phases 57–68, 53 plans (shipped 2026-05-14) → `.planning/milestones/v4.8-ROADMAP.md`
- ✅ **v4.9 Audit Depth** — Phases 69–77, 38 plans (shipped 2026-05-15) → `.planning/milestones/v4.9-ROADMAP.md`
- ✅ **v4.10 Launch Readiness** — Phases 78–85, 31 plans (shipped 2026-05-21) → `.planning/milestones/v4.10-ROADMAP.md`
- ✅ **v4.10.1 Scoring Correctness Hotfix** — Phase 86, 3 plans (shipped 2026-05-22) → `.planning/milestones/v4.10.1-ROADMAP.md`
- ✅ **v5.0 Stabilization + Tech Debt Sweep** — Phases 87–92, 16 plans (shipped 2026-05-22) → `.planning/milestones/v5.0-ROADMAP.md`
- ✅ **v5.1 Authenticated Scanning + API Surface Depth** — Phases 93–96, 16 plans (shipped 2026-05-23) → `.planning/milestones/v5.1-ROADMAP.md`
- ✅ **v5.2 Consulting-Grade Reporting** — Phases 97–100, 12 plans (shipped 2026-05-24) → `.planning/milestones/v5.2-ROADMAP.md`
- ✅ **v5.3 Adoption & Integration Surface** — Phases 101–105, 20 plans (shipped 2026-05-25) → `.planning/milestones/v5.3-ROADMAP.md`
- ✅ **v5.4 Distributed On-Prem Scanner Architecture** — Phases 106–112, 20 plans (shipped 2026-05-26) → `.planning/milestones/v5.4-ROADMAP.md`
- ✅ **v5.5 Distributed Hardening + Stabilization** — Phases 113–116, 11 plans (shipped 2026-05-27) → `.planning/milestones/v5.5-ROADMAP.md`
- ✅ **v5.6 Distributed Completion + Public Launch** — Phases 117–122, 20 plans (shipped 2026-06-12) → `.planning/milestones/v5.6-ROADMAP.md`
- ✅ **v5.7 Hardening + Hardware Compatibility & Lifecycle Remediation** — Phases 123–129, 24 plans (shipped 2026-06-14) → `.planning/milestones/v5.7-ROADMAP.md`
- ✅ **v5.8 Audit Closeout + SNMP Fingerprinting** — Phases 130–134, 21 plans (shipped 2026-06-18) → `.planning/milestones/v5.8-ROADMAP.md`
- ✅ **v5.9 Documentation Audit & Living Docs System** — Phases 135–138 + 138.1/138.2, 10 plans (shipped 2026-07-30) → `.planning/milestones/v5.9-ROADMAP.md`
- ✅ **v5.10 Hardware Lifecycle Depth** — Phases 139–143, 36 plans (shipped 2026-08-03) → `.planning/milestones/v5.10-ROADMAP.md`
- ✅ **v5.11 Discovery at Scale + Backlog Drain** — Phases 144–147, 16 plans (shipped 2026-08-11) → `.planning/milestones/v5.11-ROADMAP.md`
- ✅ **v5.12 Release & Verification Integrity** — Phases 148–153, 36 plans (shipped 2026-08-14) → `.planning/milestones/v5.12-ROADMAP.md`
- ⚠️ **v5.13 Continuous Hardware Lifecycle Monitoring** — Phases 154–156, 17 plans (development complete 2026-08-15; **never released** — see below) → `.planning/milestones/v5.13-ROADMAP.md`
- ⚠️ **v5.14 Hardware Lifecycle Tail — Fleet Coverage & Forecasting** — Phases 157–160, 16 plans (development complete 2026-08-19; **never released** — see below) → `.planning/milestones/v5.14-ROADMAP.md`
- ✅ **v5.15 Lifecycle Tail Drain** — Phases 161–163, 11 plans (shipped 2026-08-26; first published release since 5.12.0) → `.planning/milestones/v5.15-ROADMAP.md`
- 🚧 **v5.17 Defect Drain** — Phases 172–176 (in progress)
- ✅ **v5.16 Review Drain & Gate Integrity** — Phases 164–171, 47 plans (development complete 2026-08-28; **deliberately untagged** — see note) → `.planning/milestones/v5.16-ROADMAP.md`

### v5.16 deliberately untagged (2026-08-28)

v5.16 is archived but **not tagged and not released**, by explicit decision.

`pyproject.toml` still reads `5.15.0` — v5.16 was an ops milestone and never bumped it. Tagging
`v5.16.0` would have produced a tag whose source carries the wrong version string, which is exactly
the v5.13/v5.14 defect recorded below. Bumping properly is blocked behind a deferred toolchain
repair: a version bump alone fails `tests/test_version.py`, which needs `pip install -e . --no-deps`,
and the local editable install is currently broken (stale `__editable__.quirk-4.0.0.pth`).

`release.yml` now triggers on `v[0-9]*`, so any pushed tag fires a real release — the no-op failure
mode is fixed, which is precisely why an incorrect tag would now do damage rather than nothing.

v5.16's user-visible fixes (the first-run command, three screen-reader blockers, resume UX) are on
`main` and ship with the next release that bumps the version correctly.

### Release-integrity note (RVW-004, corrected 2026-08-25)

v5.13 and v5.14 were previously marked ✅ shipped. They were not. **The last
version published to PyPI is 5.12.0** (2026-08-14), and `pyproject.toml` still
carried `5.12.0` throughout both milestones — so even the tags contain the wrong
version string.

Root cause: `release.yml` triggered on `'v*.*.*'`, a **three**-component glob.
`v5.13` and `v5.14` are two-component tags, so pushing them matched nothing and
fired no workflow — no run, no failure, no signal. `v5.13` was never pushed to
origin at all. This is the third occurrence of the same defect; `v5.9` failed
identically and is recorded in `.github/tag-hygiene-baseline.txt`.

Disposition: the code shipped to `main` and is in use; only the *release* did
not happen. Rather than retro-publish two versions whose source never carried
those numbers, the record is corrected here and **v5.15 becomes the next real
release**, tagged with a 3-component version. `release.yml`'s trigger has been
broadened to `v[0-9]*` so a malformed tag can no longer silently no-op.

## Current Milestone: v5.17 Defect Drain

**Goal:** Fix the defects the v5.16 drain surfaced, and convert its misleading records into true
ones. Every phase traces to UAT cases with command / expected / observed evidence already captured.
Ops milestone — no net-new scanner surface.

**Phase Numbering:** Continues from v5.16's last phase (171). Integer phases only.

> [!important] Scope was re-measured before opening
> v5.16 reported "32 product FAILs" — a **ledger tally**, not a defect count. Re-measured
> 2026-08-28: **18 genuine defects** (9 product bugs, 9 case/doc defects), **13 chaos-lab-down
> artifacts**, and **1 spurious**. This is the fourth headline count on this project to fail
> re-measurement, after 5→3 duplicate IDs, 16→230 stale references, and 4→2 missing tests.

### Phases

- [x] **Phase 172: Fuzzing & Disclosure Safety** - `--fuzz` refuses to run non-interactively, the documented `--fuzz-budget` ceiling is enforced, and a spec-parsing failure never prints the raw target URL.
- [x] **Phase 173: Scanner Scope & Config Correctness** - Config that disables a scanner actually prevents the probe, and a disabled subsystem leaves no trace in run stats.
- [x] **Phase 174: Dashboard & API Correctness** - The dashboard score tracks the scan's score profile, the empty state loads clean, and the sidebar order and its documented lock agree.
- [x] **Phase 175: Case & Documentation Defect Correction** - Nine UAT cases where the product is right and the case is wrong are corrected, each verified as a case defect before being edited.
- [ ] **Phase 176: Chaos-Lab Re-Run** - The 13 cases that failed only because the lab was down are re-run with it up, and carry their true outcome.

## Phase Details

### Phase 172: Fuzzing & Disclosure Safety

**Goal**: QUIRK cannot fuzz a client's API without an interactive confirmation, cannot exceed its
own documented request ceiling, and cannot leak a raw target URL in an error message.
**Depends on**: Nothing (first phase; deliberately led with — these are the three defects with real
client-estate consequences)
**Requirements**: SAFE-01, SAFE-02, SAFE-03
**Success Criteria** (what must be TRUE):

  1. `--fuzz` with non-TTY stdin hard-aborts **before issuing any request**, printing a
     non-interactive-mode error and exiting non-zero. Reproduced today as: scan completed normally,
     exit 0, no message (`UAT-96-02`).

  2. `--fuzz-budget 501` is rejected at runtime. The documented hard maximum is 500; the argparse
     default of 50 is already correct and must not change (`UAT-96-03`).

  3. A `SpecParsingError` from `scan_openapi_spec` reports a redacted URL preview, never the full
     raw URL. Reproduced today with `evil.example.com` appearing in full (`UAT-94-05`). Any sibling
     error path with the same shape is covered.
**Plans**: 6 plans

Plans:
**Wave 1**

- [x] 172-01-PLAN.md — SAFE-01/02: argparse-time non-TTY refusal + budget ceiling, FUZZ-001/002 codes, CLI regression tests
- [x] 172-02-PLAN.md — SAFE-02 D-05: docs==code fuzz budget gate; layer-2 regression lock confirmed
- [x] 172-03-PLAN.md — SAFE-03 D-03: real URL redaction in url_allowlist, rename-only twin in subprocess_input, unit coverage

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 172-04-PLAN.md — D-04 UAT-94-05 disposition, UAT Series 172, corpus vault sync
- [x] 172-05-PLAN.md — operator docs (configuration, operators-guide, report-interpretation) + Obsidian sync

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 172-06-PLAN.md — invariant gate (full suite baseline, 28 fuzzer tests, UAT guards), VALIDATION/REQUIREMENTS/ROADMAP close, phase note

### Phase 173: Scanner Scope & Config Correctness

**Goal**: A config that says "do not scan this" prevents the scan, and a disabled subsystem leaves
no residue in run output.
**Depends on**: Nothing
**Requirements**: SCOPE-01, SCOPE-02, SCOPE-03
**Success Criteria** (what must be TRUE):

  1. ~~With `connectors.enable_email` at its default `False`, no SMTP/IMAP/POP3 port is probed and
     the Motion page's Email Protocols section renders its empty state.~~ **Ruled a case defect,
     not a product defect** — the `standard`/`deep` profile's deliberate, documented auto-enable of
     `enable_email`/`enable_broker` (Phase 32/33/72-D-02) is the intended behavior, and a fix
     implementing this criterion literally was built, shipped, and reverted the same day once shown
     to regress every real CLI config (`UAT-36-05` promoted to Phase 175; see
     `173-DISPOSITIONS.md`).

  2. `run_stats.timings_sec` contains no `broker_scanning` key when no broker phase ran. The key
     currently persists with a nonzero value while the row count is correctly 0 (`UAT-33-01`).

  3. Enabling a scanner whose optional extras are absent emits the documented missing-extra signal —
     stderr advisory plus a `scan_error_category=missing_extra` finding — for the broker/motion
     family as it already does for identity (`UAT-41-01`).
**Plans**: 4 plans

Plans:
- [x] 173-01-PLAN.md — SCOPE-01: CLI port-scope suppression with declared provenance (D-01/D-01a)
- [x] 173-02-PLAN.md — SCOPE-02: generic `_PHASE_SKIPPED` timing-key omission (D-02)
- [x] 173-03-PLAN.md — SCOPE-03: broker/smime/adcs missing-extra signal (D-03/D-05)
- [x] 173-04-PLAN.md — Docs, UAT Series 173, Obsidian sync, full-suite regression gate

### Phase 174: Dashboard & API Correctness

**Goal**: The dashboard reports the same score the CLI did, loads its empty state without errors,
and its navigation matches whatever the documentation says — with the disagreement resolved
deliberately rather than silently.
**Depends on**: Nothing
**Requirements**: DASH-06, DASH-07, DASH-08
**Success Criteria** (what must be TRUE):

  1. Scans run under `--score-profile strict` / `balanced` / `standard` produce three different
     dashboard scores matching their CLI scorecards, and `/api/scans` populates `profile` and
     `calibration` rather than null. Currently 93 / 91 / 90 on the CLI all render as 93
     (`UAT-8-07`).

  2. The dashboard empty state on a fresh database logs zero console errors. A
     `Failed to load resource 404` is currently logged (`UAT-10-08`).

  3. The sidebar order and the documented D-11 lock agree. An undocumented Hardware item currently
     sits between Motion and Data at Rest. **Decide which side is wrong** — do not re-order a
     shipped UI to satisfy a stale document without establishing that the document is right
     (`UAT-39-07`).
**Scope note (added 2026-08-29 during Phase 174 planning — the criteria text above is left INTACT; this records what was deliberately narrowed and why):**

- **Criterion 1 is partially superseded by locked decision D-01.** Ground truth (`174-ASSUMPTIONS.md` §A) established the real defect is a single call site: `quirk/dashboard/api/routes/scan.py:1227` computes the score without the calibration its sibling at `:1476` passes correctly. The `profile`/`calibration` nulls are NOT a defect — they are locked by a passing regression test (`test_clone_reconstruction`, UI-HIST-01) because those fields exist only for dashboard-launched jobs. Making the literal bare-CLI reproduction pass would require new DB persistence for CLI-run scans (schema migration, no reliable backfill key), **explicitly deferred by user decision** and not delivered here. Note also that `--score-profile standard` is not a legal value (legal: `lenient`/`balanced`/`strict`), so the reproduction as written could not have run; `UAT-8-07`'s case-text correction is recorded for Phase 175.
- **Criterion 2 is interpreted by locked decision D-02** as "no unhandled application error", which is already true. The only 404 on an empty DB is `GET /api/scan/latest` — an intentional, documented route (`QRK-DASHBOARD-006`) that the frontend already handles with correct empty-state text. The remaining DevTools entry is the browser logging any non-2xx fetch; it cannot be suppressed from frontend code, and silencing it would mean changing a documented error contract, which was **rejected by user decision**.
- **Criterion 3 was resolved in favour of the shipped UI** per locked decision D-03. Git archaeology proved Hardware's placement was deliberate (Phase 128, explicit commit message, 4 corroborating artifacts), and the cited D-11 "lock" is a stale Phase-39 note that five other shipped items also violate. The DOCUMENTS are corrected; the sidebar is NOT re-ordered.

**Plans**: 5 plans

Plans:
- [x] 174-01-PLAN.md — DASH-06: RED test then the minimal `list_scans` calibration fix (no schema change)
- [x] 174-02-PLAN.md — DASH-07: executed empty-DB evidence probe + 404-contract regression guard (no code change)
- [x] 174-03-PLAN.md — DASH-08: canonical nav-order record + lockstep correction of the stale Phase-39 D-11 note
- [x] 174-04-PLAN.md — UAT corpus: UAT-39-07 criteria corrected, three legacy cases re-dispositioned via the ledger, Series 174, sidebar drift guard
- [x] 174-05-PLAN.md — Obsidian sync + phase note, REQUIREMENTS.md close-out, blocking full-suite regression gate

### Phase 175: Case & Documentation Defect Correction

**Goal**: The nine UAT cases that record a FAIL against correct product behaviour are corrected, so
the corpus stops asserting defects that do not exist.
**Depends on**: Nothing
**Requirements**: CASEFIX-01, CASEFIX-02, CASEFIX-03, CASEFIX-04, CASEFIX-05

**Carried forward from Phase 172 (D-04):** `UAT-94-05`'s third pass-criterion ("Error message does
not expose the raw URL value (redacted preview only)") was ruled a CASE DEFECT, not a product bug —
it demands all-or-nothing URL redaction, which contradicts Phase 172's locked D-03 threat model
(credentials/tokens in userinfo/query are the disclosure risk; the operator-supplied hostname is
retained by design). The case's text and disposition were left byte-untouched in
`docs/UAT-SERIES.md`; the full argument and a proposed corrected wording are in
`.planning/phases/172-fuzzing-disclosure-safety/172-DISPOSITIONS.md` § 1. Phase 175 should also
consider adding a second, credential-bearing UAT case (mirroring
`https://user:hunter2@evil.example.com/openapi.json?token=SECRETVALUE`) since the current fixture
has no userinfo/query to strip and so cannot exercise D-03's actual redaction behaviour.

**Carried forward from Phase 173 (SCOPE-01):** `UAT-36-05` (Series 36) was ruled a CASE DEFECT, not
a product bug — its premise ("the compiled-default `connectors.enable_email: False` should govern
scanning under the `standard`/`deep` profiles") contradicts the intentional, documented Phase
32/33/72-D-02 auto-enable coverage feature (`docs/configuration.md`). A fix implementing the case's
literal premise (suppress auto-enable when `scan.ports_tls` is user-set) was built, shipped, and
live-verified in plan 173-01, then reverted the same day once it was shown to fire on every real
CLI config (`ports_tls` is a required YAML key with no default), silently reversing the coverage
feature for all CLI users. The case's text and disposition were left byte-untouched in
`docs/UAT-SERIES.md` (Series 36); the full argument, both rejected suppression mechanisms, and the
evidence they fail on real configs are in
`.planning/phases/173-scanner-scope-config/173-DISPOSITIONS.md`. The real operator-facing gap the
case surfaced — no CLI documentation stated that email/broker auto-enable is independent of
`scan.ports_tls` — is closed in `docs/configuration.md` (v5.17 / Phase 173), not by editing the
case.

**Carried forward from Phase 174 (DASH-06):** `UAT-8-07`'s own case text needs correction, not a
new product fix — its reproduction command uses `--score-profile standard`, an illegal value
(argparse only accepts `lenient`/`balanced`/`strict`), and its bare-CLI list-view path has no
`ScanJob` row to score under. The real, dashboard-launched-scan half of the defect was fixed in
Phase 174 (`scan.py:1263` now passes `profile=calibration`, covered by
`tests/test_dashboard_scans_score_profile.py`); `UAT-8-07` was dispositioned `DEFERRED` (not
rewritten) in `docs/uat-disposition-ledger.jsonl`. Phase 175 should replace the illegal
`--score-profile` value and re-scope the reproduction to a dashboard-launched scan.

Phase 175 therefore inherits **three** carried-forward case-text corrections at its start:
`UAT-94-05` (Phase 172), `UAT-36-05` (Phase 173), and `UAT-8-07` (Phase 174).

**Success Criteria** (what must be TRUE):

  1. Each of the nine is **verified as a case defect before it is edited**. If any turns out to be a
     real product bug, it is promoted to a product fix rather than quietly rewritten — the failure
     mode here is editing the specification until it matches whatever the code happens to do.

  2. `UAT-85-02` / `UAT-85-06` accept the quoted `'quirk-scanner[all]'` form the docs correctly use
     for zsh glob safety; `UAT-84-02` can pass against the real `changelog.d/` state;
     `UAT-110-06`'s impossible worked example is corrected.

  3. `UAT-55-01`'s `control_id` / `practice_number` mismatch is resolved on the correct side — this
     one may genuinely be an API naming problem rather than a case defect, and must be judged, not
     assumed.

  4. `UAT-58-07` is re-dispositioned as DEFERRED naming the deliberate `QRK-TARGET-002` design
     decision, or that decision is explicitly reopened.

  5. All four UAT guard suites stay green and the corpus stays at zero undispositioned throughout.

**Plans**: 7 plans

Plans:
- [x] 175-01-PLAN.md — Re-verify all twelve cases against the current checkout; capture the corpus baseline and the D-04 promotion gate
- [x] 175-02-PLAN.md — Correct UAT-85-02, UAT-85-06, UAT-84-02, UAT-110-06 case text (CASEFIX-01/02/03)
- [x] 175-03-PLAN.md — Correct UAT-51-02, UAT-55-01, UAT-9-10, UAT-10-11, UAT-58-07 case text (CASEFIX-04/05, D-01, D-02)
- [x] 175-04-PLAN.md — Correct the three inherited cases: UAT-94-05, UAT-36-05, UAT-8-07
- [x] 175-05-PLAN.md — Add the D-03 credential-bearing companion case to Series 94 with a demonstrated falsification proof
- [x] 175-06-PLAN.md — Re-disposition the eleven corrected cases through the ledger, including UAT-58-07 FAIL to DEFERRED naming T-164-01
- [x] 175-07-PLAN.md — Series 175, Obsidian sync, CASEFIX close-out, full-suite invariant sign-off

### Phase 176: Chaos-Lab Re-Run

**Goal**: The 13 cases that failed only because the chaos lab was down carry their true outcome,
and any genuine defect hiding behind them is surfaced.
**Depends on**: Nothing, but scheduled last so that defects it uncovers can be triaged against a
milestone whose other work is already complete
**Requirements**: LABRUN-01, LABRUN-02
**Success Criteria** (what must be TRUE):

  1. All 13 cases (`UAT-4-01`, `UAT-5-02/03/04/06/07/08/09/11/13`, `UAT-6-06/07/08`) are re-executed
     **with the chaos lab running** and carry a real outcome. Phase 168's D-01 forbade starting the
     lab; this phase has no such constraint.

  2. Any genuine defect the re-run uncovers is recorded with evidence and **explicitly triaged** —
     into this milestone or the backlog — rather than absorbed silently.

  3. `UAT-1-02` is correctly dispositioned. It currently records FAIL with evidence
     `Got: 'QU.I.R.K. v5.15.0', code=0`, which matches its own expected output. Phase 168-03 blamed
     a stale hardcoded check in `uat_runner.py`; no such literal exists there. Find the real cause.
**Plans**: TBD

### Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 172. Fuzzing & Disclosure Safety | 6/6 | Complete | 2026-08-29 |
| 173. Scanner Scope & Config Correctness | 4/4 | Complete | 2026-08-29 |
| 174. Dashboard & API Correctness | 5/5 | Complete | 2026-08-30 |
| 175. Case & Documentation Defect Correction | 7/7 | Complete | 2026-08-30 |
| 176. Chaos-Lab Re-Run | 0/TBD | Not started | - |

---

## Phases

<details>
<summary>✅ v5.16 Review Drain & Gate Integrity (Phases 164–171) — SHIPPED 2026-08-28</summary>

Closed every open finding from the 2026-08-24 third-party functional review. The UAT corpus went
from 325 unrecorded cases to **zero undispositioned across all 666**, guarded by a standing
zero-undispositioned CI gate proven load-bearing by mutating a scratch corpus. The substantive
output is the honest record it produced: **32 recorded FAIL dispositions — **18 of them genuine product defects**, 13 chaos-lab-down artifacts from a sweep that was required not to start the lab, and 1 spurious (its observed output matched the expectation) — plus 57 honest coverage GAPs**.
A CRITICAL evidence-newline injection (CR-01) that could splice a fabricated fully-PASSED case past
all three guards was found and fixed mid-milestone. Also: first-run correctness (164), 291
accessibility violations dispositioned with 3 screen-reader blockers fixed (165), e2e smoke +
XXE-safe XML parsing + a suite-wide macOS SIGSEGV fix (166), format unification (167), and a
traceability tail that backfilled CHANGELOG v5.9–v5.14 and repaired 230 stale cross-phase
references (170). 47 plans, 24/24 requirements, `gaps_found` audit with one gap accepted and
carried to v5.17 (GATE-03's fork-safety allowlist).

Full detail: `.planning/milestones/v5.16-ROADMAP.md`

</details>

<details>
<summary>✅ v5.14 Hardware Lifecycle Tail — Fleet Coverage & Forecasting (Phases 157–160) — SHIPPED 2026-08-19</summary>

See `.planning/milestones/v5.14-ROADMAP.md` for full phase details, `.planning/milestones/v5.14-REQUIREMENTS.md`
for requirements, and `.planning/milestones/v5.14-MILESTONE-AUDIT.md` for the closing audit.

4 phases (157-160), 16 plans, 5/5 HWLC requirements complete. Closed the sensor-fleet drift gap
left open by v5.13 and rounded out lifecycle monitoring: a table-wide calendar-cutoff retention
sweep bounds `hardware_drift_events` growth, a hedged catalog-cited 12-month EOL/tier forecast
narrative renders in every report format, sensor-scanned segments reach the console's drift
history exactly like console-direct scans via a new shared `persist_and_reconcile()` chokepoint,
a lightweight `--check-in` mode re-probes only already-known devices without a full scan, and a
new event-sourced table tracks vendor-level PQC catalog status changes — the least-precedented
item in the milestone, with a design flaw (single-host confirmation-gate domination) caught by
research before implementation ever touched it. Every phase closed via a code-review→fix→re-review
cycle; two closed BLOCKER-severity bugs (a session-rollback data-loss bug in Phase 158, a
dashboard surface silently dropping a backend-serialized field in Phase 159). Milestone audit
scored `tech_debt` (0 blockers, 5/5 requirements satisfied, 2 deferred human-UAT scenarios from
Phase 158, and Phase 160's `GET /api/hardware/vendor-trends` presentation layer intentionally
unwired per locked scope).

</details>

---
<details>
<summary>✅ v5.13 Continuous Hardware Lifecycle Monitoring (Phases 154–156) — SHIPPED 2026-08-15</summary>

See `.planning/milestones/v5.13-ROADMAP.md` for full phase details, `.planning/milestones/v5.13-REQUIREMENTS.md`
for requirements, and `.planning/milestones/v5.13-MILESTONE-AUDIT.md` for the closing audit.

3 phases (154-156), 17 plans, 12/12 requirements complete. Extended v5.10's point-in-time hardware
fingerprinting into ongoing lifecycle tracking: a stable SSH host-key-fingerprint secondary match
key survives DHCP/re-IP, failed re-probes never erase last-known-good device state, and a two-scan
drift-reconciliation engine surfaces CNSA 2.0 tier crossings, PQC/bridge-mitigation shifts,
EOL/EOS proximity, and CVE deltas as four distinct, N-of-M-confirmed event types — visible on the
dashboard (`/hardware`, `/compare`) and in HTML/DOCX reports as structurally separate advisory
content. Recurring OT/ICS (Modbus/BACnet) re-probing now requires explicit opt-in plus a hardcoded
168-hour cadence floor, closed by an independent `/gsd-secure-phase` review (19/19 threats, 0
high-severity findings).

</details>

---

<details>
<summary>✅ v5.12 Release & Verification Integrity (Phases 148–153) — SHIPPED 2026-08-14</summary>

See `.planning/milestones/v5.12-ROADMAP.md` for full phase details, `.planning/milestones/v5.12-REQUIREMENTS.md`
for requirements, and `.planning/milestones/v5.12-MILESTONE-AUDIT.md` for the closing audit.

6 phases (148-153), 36 plans, 14/14 requirements complete. Shipped the real `v5.12.0` release tag
(PyPI + Windows operator zip + GitHub Release), a green CI-held test-suite baseline, the
phase-completion artifact gate (`scripts/verify_phase_gates.py` + `.githooks/pre-commit`, now
installed and live), and empirically closed the Phase 144 nmap timing artifact (does not reproduce).

</details>

---

<details>
<summary>✅ v5.11 Discovery at Scale + Backlog Drain (Phases 144–147) — SHIPPED 2026-08-11</summary>

**v5.11** made large (>1024-host) range scans reachable end-to-end from the dashboard's
nmap-discovery path — chunked batches with per-batch failure isolation, a TCP-SYN/ACK liveness
pre-pass with explicit privilege-fallback detection, per-batch progress on the dashboard,
batch-scaled timeouts, one shared CLI/dashboard chunking call site, and undetermined-host
disclosure across all report surfaces — while draining the small debt tail accumulated since
v5.8/v5.10 (OT/ICS resume-checkpoint gap, BACnet CVE key coverage, 2026-05-27 audit ledger
reconciliation, deferred human-UAT re-triage). 4 phases, 16 plans, 11/11 requirements, audit
`passed`. Full phase details archived to `.planning/milestones/v5.11-ROADMAP.md`; audit
`.planning/milestones/v5.11-MILESTONE-AUDIT.md`.

- [x] Phase 144: Chunked Discovery Core (3/3 plans) — completed 2026-08-10
- [x] Phase 145: Liveness Pre-Pass (3/3 plans) — completed 2026-08-10
- [x] Phase 146: Progress, Scaling & Disclosure (6/6 plans) — completed 2026-08-11
- [x] Phase 147: Backlog Drain — Lifecycle & Ledger Tail (4/4 plans) — completed 2026-08-11

**Note:** approximately 39 of ~58 v5.11 phase artifact files (`.planning/phases/144-147/*`) were
permanently lost during the v5.12 `/gsd-new-milestone` opening when a destructive `phases.clear`
call ran without checking that `milestone.complete` had reported `archived.phases: false`. Code
and the decision record are unaffected — see
`.planning/milestones/v5.11-phases/ARCHIVE-MANIFEST.md`. This incident is the direct source of
v5.12's ARTIFACT-04 requirement.

</details>

---

<details>
<summary>✅ v3.9–v5.5 (Phases 1–116) — SHIPPED</summary>

All completed milestone roadmaps are archived in `.planning/milestones/`. The next milestone continues from Phase 123.

**v5.5 Distributed Hardening + Stabilization** (Phases 113–116) hardened the v5.4 distributed
scanner into production shape: per-sensor opaque Bearer-token authentication with revocation and a
two-router split (113), automatic merge on full sensor check-in via a failure-isolated FastAPI
BackgroundTask with a config toggle and two trigger conditions (114), a live-UAT stabilization sweep
of the four E2E-surfaced defects — idempotent enroll, importlib.resources cmvp packaging, scheduler
arg fix with target preservation, phantom-row elimination — plus a weak-TLS segment-b lab target so
the per-segment filter is exercisable end-to-end (115), and an evidence-backed Windows packaging
PyInstaller spike returning GO-conditional with a v5.6 effort estimate (116). Audit: 13/13
requirements satisfied, 0 blockers, integration clean. Full details:
`.planning/milestones/v5.5-ROADMAP.md`.

**v5.4 Distributed On-Prem Scanner Architecture** (Phases 106–112) split QU.I.R.K. into a sensor/console
model so a segmented enterprise network is scanned segment-by-segment and merged into one authoritative
CBOM + one quantum-readiness score, with no inbound access to any segment required. Full details:
`.planning/milestones/v5.4-ROADMAP.md`.

</details>

---

<details>
<summary>✅ v5.6 Distributed Completion + Public Launch (Phases 117–122) — SHIPPED 2026-06-12</summary>

**v5.6** shipped the production Windows frozen sensor (`--onedir` PyInstaller build + smoke + zip/Scheduled-Task installer + frozen E2E per-sensor auth + GitHub Release asset `quirk-windows-5.6.0.zip`), took the repository PUBLIC (gitleaks-clean 3-pass history rewrite, branch protection with required "Windows Sensor Smoke" check, SSRF guard hardening, Actions SHA-pinning), added port-scope discovery control (common/top1000/all/custom + zero-result signal), and closed 11 audit tech-debt items at version 5.6.0 (tag `v5.6.0`).

- [x] Phase 117: Windows Production Build + Smoke (1/1 plans) — completed 2026-05-27
- [x] Phase 118: Windows Packaging, E2E Auth + Release (3/3 plans) — completed 2026-05-27
- [x] Phase 119: Public-Repo Cutover (2/2 plans) — completed 2026-06-12
- [x] Phase 120: Go-Public Remediation (5/5 plans) — completed 2026-06-12
- [x] Phase 121: Port-Scope Discovery Control (5/5 plans) — completed 2026-06-11
- [x] Phase 122: Address Tech Debt + Milestone Closeout Docs (4/4 plans) — completed 2026-06-12

Audit: 21/21 requirements, 0 blockers (`.planning/milestones/v5.6-MILESTONE-AUDIT.md`). Full details: `.planning/milestones/v5.6-ROADMAP.md`.

</details>

---

<details>
<summary>✅ v5.7 Hardening + Hardware Compatibility & Lifecycle Remediation (Phases 123–129) — SHIPPED 2026-06-14</summary>

**v5.7** drained the 18 deferred audit rows from the v5.6 public launch (Wave A: SSRF hardening SP-02/03/04+WR-06+CD-03, scoring correctness SP-05+QC-02/03+WR-02/05, posture defaults WR-01/CE-04, distributed edges CD-05/06, ledger closeout + Dashboard Quality green), then shipped the HWCOMPAT capability arc (Wave B: agentless hardware fingerprinting from SSH/HTTP mgmt banners, 8-vendor PQC compatibility matrix + 90-day CI staleness gate, CNSA 2.0 tier assignment, full report surfacing in HTML/DOCX/executive/dashboard /hardware tab, crypto-bridge detection, CBOM Pass 4 FIRMWARE components). 7 phases, 24 plans, 24/24 requirements, 50 commits. Tag `v5.7.0`.

### Phases

- [x] **Phase 123: SSRF & URL-Allowlist Hardening** — Close all five SSRF warning rows from the 2026-05-27 audit; wire rest_fuzzer through the existing validate_external_url invariant; add GCP metadata aliases; fix path-ref injection into syft; block reflective self-SSRF; mitigate DNS-rebinding TOCTOU (completed 2026-06-13)
- [x] **Phase 124: Scoring & Evidence Correctness** — Fix five scoring/evidence correctness findings: KeyError abort on missing severity, QRAMM weakest-link inflation, EdDSA agility credit, AEAD cipher mis-classification, cross-tenant evidence contamination in distributed mode
- [x] **Phase 125: Posture Defaults + Distributed Edge Cases** — Harden two insecure-by-default deployment postures (auth token + bind address); surface IAM permission errors as scan-coverage findings; fix two distributed edge cases (same-second merge tiebreak, notify fan-out isolation) (completed 2026-06-13)
- [x] **Phase 126: Audit Ledger Closeout + Dashboard Quality Green-Up** — Close or formally disposition every remaining `deferred → v5.7` row in the audit ledger; bring Dashboard Quality CI green (a11y + E2E smoke) (completed 2026-06-13)
- [x] **Phase 127: Hardware Fingerprinting Foundation** — Agentless device fingerprinting from SSH banners + HTTP management interfaces; curated hardware-PQC compatibility matrix with staleness gate; `hwcompat` chaos lab profile; HardwareDevice ORM table; CI staleness assertion (completed 2026-06-14)
- [x] **Phase 128: Remediation Tiers + Report Surfacing** — Tier assignment logic per device (Tier 1/2/3/N/A + CNSA 2.0 timeline); hardware findings through the findings chokepoint; hardware PQC narrative in exec report; `/hardware` dashboard tab (completed 2026-06-14)
- [x] **Phase 129: Crypto-Bridge Detection + CBOM Pass 4** — Detect incompatible endpoints behind PQC-capable gateways with conservative defaults; CBOM Pass 4 (`ComponentType.FIRMWARE`) for hardware fleet visibility; `HARDWARE` added to Pass 2/3 skip-lists (completed 2026-06-14)

### Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 123. SSRF & URL-Allowlist Hardening | 4/4 | Complete   | 2026-06-13 |
| 124. Scoring & Evidence Correctness | 4/4 | Complete | 2026-06-13 |
| 125. Posture Defaults + Distributed Edge Cases | 2/2 | Complete | 2026-06-13 |
| 126. Audit Ledger Closeout + Dashboard Quality Green-Up | 1/1 | Complete | 2026-06-13 |
| 127. Hardware Fingerprinting Foundation | 4/4 | Complete   | 2026-06-14 |
| 128. Remediation Tiers + Report Surfacing | 4/4 | Complete   | 2026-06-14 |
| 129. Crypto-Bridge Detection + CBOM Pass 4 | 5/5 | Complete    | 2026-06-14 |

Audit: 24/24 requirements, 0 blockers (`.planning/milestones/v5.7-MILESTONE-AUDIT.md`). Full details: `.planning/milestones/v5.7-ROADMAP.md`.

</details>

---

<details>
<summary>✅ v5.8 Audit Closeout + SNMP Fingerprinting (Phases 130–134) — SHIPPED 2026-06-18</summary>

**v5.8** drained the 15 remaining audit rows from the 2026-05-27 ledger (Wave A: codesign column rename, fuzzer dedup, Kerberos RFC comment, DOCX exception logging, SOURCE algo-hint granularity, rate-limit idle eviction, job target 422 validation, sensor-push re-validation, SSRF TOCTOU doc, sensor CLI UUID guard, SIEM SSRF guard, console enroll single-session, CEF escaping, auth token sessionStorage + CSP header, HTML cover-page fix), then shipped SNMP fingerprinting as the third hardware signal source and the CBOM DEVICE/FIRMWARE component hierarchy (Wave B). 5 phases, 21 plans, 22/22 requirements, 73 commits. Tag `v5.8.0`. B-01 distributed SNMP field projection gap closed in `6eb512e` before tag.

### Phases

- [x] **Phase 130: Code Quality & Scanner Fixes** — codesign column rename (AUDIT-01), REST fuzzer dedup (AUDIT-02), Kerberos TCP→UDP comment (AUDIT-03), DOCX exception logging (AUDIT-04), SOURCE algo-hint granularity (AUDIT-05) (completed 2026-06-14)
- [x] **Phase 131: Dashboard & Delivery Hardening** — rate-limit idle eviction (AUDIT-06), job target 422 validation (AUDIT-07), sensor-push re-validation (AUDIT-08), SSRF TOCTOU doc (AUDIT-09), sensor CLI UUID guard (AUDIT-10), SIEM SSRF guard (AUDIT-11), console enroll single-session (AUDIT-12), CEF escaping (AUDIT-13) (completed 2026-06-15)
- [x] **Phase 132: Frontend & Report Polish** — auth token localStorage → sessionStorage + CSP header (AUDIT-14), HTML cover-page layout fix (AUDIT-15) (completed 2026-06-15)
- [x] **Phase 133: SNMP Hardware Fingerprinting** — opt-in `[hw]` extras (pysnmp>=7.1.0,<8 + sysdescrparser), 3-OID probe (sysDescr/sysName/sysObjectID), vendor regex + sysdescrparser dual-path, 4 HardwareDevice ORM columns, Cisco IOS Net-SNMP chaos lab container, CBOM quirk:hw-snmp-oid property, staleness gate (completed 2026-06-15)
- [x] **Phase 134: CBOM DEVICE Component Hierarchy** — DEVICE parent + FIRMWARE children via Component.components; HardwareComponent Pydantic schema on /api/scan/latest; dashboard CBOM tab HardwareInventory (completed 2026-06-16)

### Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 130. Code Quality & Scanner Fixes | 4/4 | Complete | 2026-06-14 |
| 131. Dashboard & Delivery Hardening | 5/5 | Complete | 2026-06-15 |
| 132. Frontend & Report Polish | 3/3 | Complete | 2026-06-15 |
| 133. SNMP Hardware Fingerprinting | 5/5 | Complete | 2026-06-15 |
| 134. CBOM DEVICE Component Hierarchy | 3/3 | Complete | 2026-06-16 |

Audit: 22/22 requirements, 0 blockers (`.planning/milestones/v5.8-MILESTONE-AUDIT.md`). Full details: `.planning/milestones/v5.8-ROADMAP.md`.

</details>

---

<details>
<summary>✅ v5.9 Documentation Audit & Living Docs System (Phases 135–138 + 138.1/138.2) — SHIPPED 2026-07-30</summary>

Full phase details, success criteria, and gap-closure history archived to `.planning/milestones/v5.9-ROADMAP.md`. Requirements archived to `.planning/milestones/v5.9-REQUIREMENTS.md`. Audit: `.planning/milestones/v5.9-MILESTONE-AUDIT.md`.

Audited every user-facing doc against what shipped in v5.4–v5.8, refreshed README/getting-started/architecture/operators-guide/report-interpretation, added a net-new `docs/admin-guide.md`, documented the chaos-lab hwcompat profile, and embedded a permanent doc-hygiene checklist in `CLAUDE.md`. Two gap-closure phases (138.1 CORE-04 tier-inversion fix, 138.2 LIVE-03 vault re-sync) closed defects the milestone's own audit found — 16/16 requirements satisfied, tech_debt disposition (deferred human-UAT only, no content gaps).

</details>

---

<details>
<summary>✅ v5.10 Hardware Lifecycle Depth (Phases 139–143) — SHIPPED 2026-08-03</summary>

Full phase details, gap-closure history, and success criteria archived to `.planning/milestones/v5.10-ROADMAP.md`. Requirements archived to `.planning/milestones/v5.10-REQUIREMENTS.md`. Audit: `.planning/v5.10-MILESTONE-AUDIT.md`.

Closed out the Hardware Compatibility & Lifecycle Remediation arc opened in v5.7/v5.8: SNMPv3
auth+priv support (139), evidence-backed SNMP-confirmed bridge mitigation (140), OT/ICS
Modbus/BACnet fingerprinting (141 — required two post-ship gap-closure rounds after a live
checkpoint caught a deeper orchestration bug the plan-checker had missed), advisory-only firmware
CVE correlation (142), and a small independent dashboard/security tail (143). 36 plans, 23/23
requirements satisfied, tech_debt disposition (0 blockers, 4 tracked non-blocking items).

</details>

---

## Backlog

Items to be organized into future milestones. Organized by theme.

### Release & Verification Integrity (v5.12 candidates)

Promoted into the v5.12 milestone and shipped 2026-08-14 (see `.planning/milestones/v5.12-ROADMAP.md`) — kept here for
backlog-history continuity:

- Windows release asset gap (v5.11.0 shipped no Windows build) → RELEASE-04 (Phase 148)
- Release dry-run / pre-tag validation → RELEASE-02 (Phase 148)
- Tag hygiene guard (`v5.9`/`v5.10.0` tag drift) → RELEASE-03 (Phase 148)
- Actual tag cut proving the repaired pipeline → RELEASE-01 (Phase 153)
- ~102 pre-existing suite failures → SUITE-01/02/03 (Phases 149–150)
- Phase-completion artifact enforcement (VERIFICATION.md/VALIDATION.md/UAT-SERIES.md gaps) →
  ARTIFACT-01/02/03 (Phase 151)

- `phases.clear` destructive-op guard — see `.planning/milestones/v5.11-phases/ARCHIVE-MANIFEST.md`
  incident → ARTIFACT-04 (Phase 151)

- DISC-09 segmented-network chaos lab profile + Phase 144 nmap timing artifact → DISC-09/DISC-10
  (Phase 152)

- Interactive nmap-discovery-first default N→Y → DISC-11 (Phase 152)

**Explicitly out of scope for v5.12:**

- DISC-08 sub-batch (mid-discovery) checkpoint/resume granularity — accepted boundary; batches are
  cheap (~30–60s) relative to what the checkpoint system protects. Revisit only if batch cost
  grows.

- Continuous hardware lifecycle monitoring — promoted into v5.13 (see above).

- SaaS multi-tenancy — still parked, no business-model signal.

### Hardware Compatibility & Lifecycle Remediation (v5.13+)

Promoted into v5.13 (see above) — kept here for backlog-history continuity:

- **Continuous hardware lifecycle monitoring** — HWLC-01..12, Phases 154–156.

~~OT/ICS resume-checkpoint gap~~ and ~~CVE table BACnet key coverage~~ — both closed by v5.11
Phase 147 as DRAIN-01/DRAIN-02; struck from this list 2026-08-11.

### Hardware Lifecycle Tail (v5.14) — SHIPPED

Promoted into v5.14 (see above) — all items shipped 2026-08-19, kept here for backlog-history
continuity:

- HWLC-13 — lightweight "check-in" scan mode (narrow re-probe of known devices only) → Phase 159 ✓
- HWLC-15 — fleet-wide sensor coverage for `hardware_devices` (deferred from v5.13) → Phase 158 ✓
- HWLC-16 — `hardware_drift_events` retention policy → Phase 157 ✓
- HWLC-17 — vendor PQC-status trend tracking (catalog-level, not per-device) → Phase 160 ✓
- HWLC-18 — consultant-facing "lifecycle risk forecast" narrative (12-month EOL/tier projections)
  → Phase 157 ✓

**Deferred out of v5.14, now promoted into v5.15 (see below):**

- HWLC-14, HWLC-19 (vendor-trend surfacing), HWLC-20 (check-in scheduling), DISC-08 — all promoted
  into v5.15 Lifecycle Tail Drain 2026-08-19.

**Still out of scope (v2+ / rejected):**

- Statistically-modeled EOL prediction beyond vendor-published catalog dates — explicitly rejected
  as an anti-feature.

- Cross-tenant/cross-client PQC trend aggregation — blocked on the still-parked SaaS multi-tenant
  architecture.

### Lifecycle Tail Drain (v5.15)

Promoted into v5.15 and shipped 2026-08-26 (see `.planning/milestones/v5.15-ROADMAP.md`) — kept here for backlog-history
continuity:

- HWLC-14 — email/webhook notification on tier-crossing/EOL events, reusing Phase 101 fan-out →
  Phase 161

- HWLC-19 — vendor-level PQC-trend dashboard/report surfacing (`GET /api/hardware/vendor-trends`
  has had zero consumers since Phase 160) → Phase 161

- HWLC-20 — recurring/scheduled check-in scan mode on top of HWLC-13, via existing `quirk schedule`
  CRUD/dispatcher (Phase 63) → Phase 162

- DISC-08 — sub-batch (mid-discovery) checkpoint/resume granularity, tightening the v5.11 Phase 144
  per-batch checkpoint system → Phase 163

### v1.x / v2+ (deferred, see PROJECT.md Active Requirements)

None currently — the standing DISC-08 boundary item above was promoted into v5.15.

### SaaS Platform (Future Milestone)

- [ ] Multi-tenant architecture design
- [ ] Scan job queue (Celery + Redis or similar)
- [ ] User auth and org management
- [ ] Cloud deployment (Docker Compose → Kubernetes)
- [ ] Hosted reporting and CBOM storage
