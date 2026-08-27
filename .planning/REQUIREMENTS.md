# Requirements: QU.I.R.K. v5.16 — Review Drain & Gate Integrity

**Defined:** 2026-08-26
**Core Value:** Produce a complete, defensible cryptographic inventory with a CBOM deliverable and
quantum-readiness score that a consultant can hand to a client in under two hours.

**Milestone framing.** Every requirement below traces to an open finding in
`docs/reviews/2026-08-24-functional-review-action-plan.md`, an independent third-party functional
review conducted against commit `49f9094`. The review's Milestones A and B (scan integrity, release
integrity) were closed during and around v5.15; what remains is Themes 3 and 4 plus two partials.
This is an ops cycle — the 2:1 capability/ops ratio has owed one since v5.12 (2026-08-14).

**Sourcing note.** The reviewer wrote remediation text in requirement phrasing specifically so rows
could be promoted without rewriting. Where a requirement below restates a finding, the finding's
wording is preserved and only made testable; where re-verification during this milestone's open
changed the facts, the corrected figure is used and the discrepancy is called out.

---

## v1 Requirements

### First-Run Correctness

- [x] **FIRSTRUN-01**: A new user following the dashboard's empty state is given a command that
  exists. `src/dashboard/src/.../findings.tsx:119` currently instructs `quirk scan --targets ...`;
  there is no `scan` subcommand and no `--targets` flag. The instructed command must run
  successfully against a real target.
- [x] **FIRSTRUN-02**: An unparseable or unrecognized target argument fails with a coded error
  message, not a Python traceback. `--targets` currently prefix-matches `--targets-file` and raises
  an uncaught `FileNotFoundError`. This is the existing UX-02 contract applied to the target-argument
  path.
- [x] **FIRSTRUN-03**: Every documented invocation of the corrected command is consistent across
  surfaces — `docs/chaos-lab.md:676` and the six UAT step definitions in `docs/UAT-SERIES.md` that
  reference the nonexistent form.

*Source: RVW-021 (MEDIUM).*

### Accessibility

> **These requirements supersede `BACK-A11Y-01`**, filed 2026-05-22 during v5.0 Phase 87 and lost
> from the live backlog when v5.0's roadmap was archived — it survives only in
> `.planning/milestones/v5.0-ROADMAP.md`. RVW-012 is the same debt, rediscovered externally three
> months later. Phase 87's entry carries a root-cause analysis and file pointers the review does
> not; use both. That an item could disappear from every subsequent milestone review by being
> archived is itself the RVW-018 record-drift class, and is why TRACE-05 exists.

- [x] **A11Y-01**: Every one of the 291 accepted violations in
  `src/dashboard/tests/a11y/baseline-*.json` carries a recorded impact level and WCAG criterion, so
  each acceptance is a decision with a reason rather than an accumulation.
- [x] **A11Y-02**: The 3 `button-name` violations are fixed in the UI, not baselined. Icon-only
  radix dropdown triggers get discernible text or an `aria-label`. These are screen-reader blockers;
  a screen-reader blocker must never appear in an accepted baseline.
- [x] **A11Y-03**: The `color-contrast` violations are triaged into fixed and explicitly-accepted
  sets, with the accepted set justified in writing. Phase 87 identified the likely lever as design
  tokens in `src/dashboard/src/index.css` (`--muted-foreground`, accent and severity-badge hsl
  values) reaching 4.5:1.
- [x] **A11Y-04**: Baselines are keyed on an identifier stable across UI refactors and browser
  upgrades, rather than axe's full CSS-selector path — the mechanism that made the v5.0-era baselines
  stale within one milestone and that breaks the gate on Chromium updates.
- [x] **A11Y-05**: `@axe-core/puppeteer` is pinned to an exact version rather than a `^` range, so a
  transitive upgrade cannot silently change what the gate reports.

*Source: RVW-012 (MEDIUM, raised from LOW — scope was understated 23 → 291). Supersedes BACK-A11Y-01.*

### Gate Robustness

- [ ] **GATE-01**: `npm run e2e:smoke` passes on a developer machine with services listening on
  common ports. It currently cannot: the scan takes ~140s against a 120s budget. Fix by raising the
  budget, narrowing the scan scope, or pinning the port scope for E2E — whichever is defensible, but
  the gate must be able to pass.
- [ ] **GATE-02**: `uat_runner.py` parses XML with `defusedxml` rather than stdlib `ElementTree`,
  which is XXE- and billion-laughs-vulnerable by default. The project already made this migration
  once in v5.0 for the SAML path; the tooling never followed.

- [ ] **GATE-03**: A full-suite `python -m pytest` run on macOS does not crash subprocess-based
  CLI tests. Four `tests/test_target_cli.py` cases (added in Phase 164) die on a **fatal signal**,
  not an assertion: `fork` -> `_pthread_atfork_child_handlers` -> `nw_settings_child_has_forked`,
  the macOS "fork() after Network.framework initialised" crash. They pass 7/7 standalone. This is
  ordering-dependent and broader than the one file — `test_compliance_cli.py` and
  `test_db_migrate_cli.py` use the same `subprocess.run(..., cwd=...)` pattern and survive only by
  running alphabetically earlier. Linux CI is unaffected (no Network.framework).

  **Diagnosed, do not re-derive:** the obvious fix does not work. CPython reaches the safe
  `posix_spawn` path only when `(not close_fds or _HAVE_POSIX_SPAWN_CLOSEFROM)` **and**
  `cwd is None`. On this Python 3.14 build `_HAVE_POSIX_SPAWN_CLOSEFROM` is `False`, so with the
  default `close_fds=True` `posix_spawn` is never selected — with or without `cwd`. A fix needs
  BOTH `close_fds=False` AND `cwd=None`, and `close_fds=False` leaks inherited file descriptors
  into the child, which is a real trade-off requiring a decision. Full evidence and the probe
  table: `.planning/phases/164-first-run-correctness/164-FINDING-fork-crash.md`.

  Explicitly NOT to be folded into the repo's existing "known macOS-only failures" bucket — a
  crash is materially worse than a failure.

*Source: RVW-011 (MEDIUM), RVW-020 (OBSERVATION), GATE-03 from the Phase 164 post-merge test gate (2026-08-26).*

### UAT Record Integrity

> **Sizing verified at the v5.16 open, not inherited.** The review reported "353 of 601 cases."
> Direct measurement of `docs/UAT-SERIES.md` (19,202 lines) gives **628** `### UAT-` case headings,
> **636** `**Result:**` blocks, **325** with every checkbox empty, **259** marked `[x] PASS`, and
> **3** duplicate case IDs (UAT-144-01/02/03), not 5. The 636-vs-628 mismatch between result blocks
> and case headings is itself RVW-014 evidence, which is why UATREC-01 is sequenced first.

- [ ] **UATREC-01**: `docs/UAT-SERIES.md` uses exactly one UAT result format, and the count of
  result blocks equals the count of case headings. This is the precondition that makes drain
  completeness mechanically checkable rather than asserted.
- [ ] **UATREC-02**: The duplicate case IDs are resolved — every case ID in the document is unique.
  **Count corrected 2026-08-26 during Phase 164 close: there are 5 duplicates, not 3.** Measured
  directly with `grep -o '^### UAT-[0-9]*-[0-9]*' docs/UAT-SERIES.md | sort | uniq -d`:
  `UAT-144-01`, `UAT-144-02`, `UAT-144-03` (the three originally named) **plus `UAT-89-02` and
  `UAT-89-03`**, which the original sizing missed. Verified identical before and after Phase 164,
  so these are pre-existing and Phase 164 introduced none. Do not inherit the "3" figure.
- [ ] **UATREC-03**: Every one of the ~325 unrecorded cases carries either a recorded result or an
  explicit deferral naming a substitute test. **A deferral must name a specific test, not infer
  coverage from a requirement-ID annotation** — the review's own re-verification found annotation an
  unreliable proxy in both directions. `UAT-33-03` is the model to follow.
- [ ] **UATREC-04**: A check enforces the invariant going forward, so a case cannot be added to the
  gating document without a disposition and the corpus cannot silently re-accumulate.

*Source: RVW-008 (MEDIUM, counts corrected upward), RVW-014 (LOW). Full drain agreed at the v5.16
open; expected to span multiple phases.*

### Traceability & Documentation

- [ ] **TRACE-01**: `CHANGELOG.md` documents every shipped milestone. v5.9 through v5.14 are absent
  — noting that v5.13/v5.14 were developed but never released, so their entries must describe that
  accurately rather than claim a release.
- [ ] **TRACE-02**: v4.7's ROADMAP and REQUIREMENTS are either reconstructed from `v4.7-phases/` or
  ROADMAP.md's dead link to them is corrected. It is the only milestone of 40 with neither.
- [ ] **TRACE-03**: DEBT-02, GAP-02, QRAMM-08 and QRAMM-09 each gain a discoverable test —
  respectively `lab.sh` PROFILE_ARGS precedence, the re-enabled SAML scan-window test, the
  120-question/4-tab assessment page, and the Org Profile multiplier.
- [ ] **TRACE-04**: AUTH-05, DEBT-04, GAP-01, QRAMM-11 and TAIL-04 — which have tests but no
  linkage — gain a requirement-ID annotation. GAUGE-01/02/03 likewise in `ScoreGauge.test.tsx`
  (code independently verified correct; only the link is missing).
- [ ] **TRACE-05**: Planning summaries reference sibling phase artifacts by a path that survives
  archival, or are rewritten on archive. 16 references are currently broken. This is the same failure
  mode that lost BACK-A11Y-01 from the live backlog.
- [ ] **TRACE-06**: The five archive documents recording no completion status (v4.10, v4.3, v5.1,
  v5.12, v5.4) gain a `**Status:**` header.
- [ ] **TRACE-07**: New requirement documents use exactly one declaration format. Backfilling
  existing archives is explicitly optional and out of scope.

*Source: RVW-007, RVW-009, RVW-010, RVW-014, RVW-015, RVW-018, RVW-019.*

### Maintenance Runbook

- [ ] **RUNBOOK-01**: `CLAUDE.md`'s Staleness Review Cadence lists every catalog that
  `.github/workflows/python-staleness.yml` actually gates. The CMVP, error-codes and SNMP-contract
  catalogs are enforced by CI but absent from the runbook — and CMVP was the one that failed. The
  refresh half is already unblocked and run (RVW-022 fixed in `a7cf302`; cache `last_verified`
  current).

*Source: RVW-006 (HIGH, partly done).*

### Resume UX Tail

- [ ] **RESUME-05**: Resuming an already-complete scan short-circuits instead of re-appending
  `discovery`/`inventory`/`reports` checkpoint rows. Pre-existing stage-level behaviour; batch rows
  are already correct.
- [ ] **RESUME-06**: `quirk --list-resumable` shows the target for `--targets-file` runs. It
  currently recovers the target by joining `scan_jobs`, which only has a row when `--job-id` is
  passed, leaving the column blank.

*Source: Phase 163 human UAT, 2026-08-26 — surfaced but not actioned in that phase.*

---

## Future Requirements (deferred)

- **RVW-002 remainder** — wholesale merge of the dashboard's finding derivation onto
  `findings_evaluator`. TLS certificate findings already converged with a cross-surface parity test
  in v5.15; what remains is a design-judgment refactor, not an open review finding.
- **Phase 158 human-UAT** — 2 visual scenarios confirming sensor-pushed devices render on
  `/hardware` and `/compare`. HWLC-15 is independently satisfied at code and test level;
  opportunistic follow-up only.
- **UAT-143-03 production Authenticode signing** — engineering-complete and proven end-to-end by the
  v5.15.0 release. Blocked solely on procuring a real signing certificate, which is a purchasing
  decision. Re-triage at v5.16 close.
- **Archive backfill for RVW-014** — normalizing requirement and UAT formats across historical
  archives. TRACE-07 covers new documents only.

## Out of Scope

| Item | Reason |
|---|---|
| SaaS multi-tenancy | Still parked, unchanged since v5.4 — the gate is a business-model signal and none has appeared |
| `test_verify_phase_gates` "fix" | Not a defect. Phase 162's VERIFICATION.md established the two failures as macOS-only subprocess SIGSEGV (a signal-killed child produces no stderr, so asserting on it is a false failure); Linux CI never takes the branch and the Full Suite is green |
| Net-new scanner surfaces | This is an ops milestone; detection breadth is sketched in HORIZON.md as an uncommitted post-v5.16 candidate requiring a demand signal |
| Statistically-modeled EOL prediction | Standing anti-feature rejection, carried from v5.14 |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIRSTRUN-01 | Phase 164 | Complete |
| FIRSTRUN-02 | Phase 164 | Complete |
| FIRSTRUN-03 | Phase 164 | Complete |
| A11Y-01 | Phase 165 | Complete |
| A11Y-02 | Phase 165 | Complete |
| A11Y-03 | Phase 165 | Complete |
| A11Y-04 | Phase 165 | Complete |
| A11Y-05 | Phase 165 | Complete |
| GATE-01 | Phase 166 | Pending |
| GATE-02 | Phase 166 | Pending |
| GATE-03 | Phase 166 | Pending |
| UATREC-01 | Phase 167 | Pending |
| UATREC-02 | Phase 167 | Pending |
| UATREC-03 | Phase 168, 169 | Pending |
| UATREC-04 | Phase 169 | Pending |
| TRACE-01 | Phase 170 | Pending |
| TRACE-02 | Phase 170 | Pending |
| TRACE-03 | Phase 170 | Pending |
| TRACE-04 | Phase 170 | Pending |
| TRACE-05 | Phase 170 | Pending |
| TRACE-06 | Phase 170 | Pending |
| TRACE-07 | Phase 170 | Pending |
| RUNBOOK-01 | Phase 170 | Pending |
| RESUME-05 | Phase 171 | Pending |
| RESUME-06 | Phase 171 | Pending |

All 24 v5.16 requirements mapped. 0 orphans.
