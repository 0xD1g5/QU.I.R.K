# Requirements: v5.17 — Defect Drain

**Milestone:** v5.17 Defect Drain
**Opened:** 2026-08-28
**Source:** every requirement traces to a UAT case recorded FAIL during the v5.16 drain
(Phases 168/169), with command / expected / observed evidence already captured in
`docs/uat-disposition-ledger.jsonl`.

> [!important] Scope was re-measured before opening
> The v5.16 close reported "32 product FAILs". That was a **ledger tally**, not a defect count.
> Re-measured 2026-08-28: **18 genuine defects**, 13 chaos-lab-down artifacts, 1 spurious.
> Of the 18, **9 are product bugs** and **9 are case/doc defects** where the product is correct and
> the UAT case is wrong. This milestone fixes all of them, and re-runs the 13 lab cases properly.
> Every count in this document was derived from the ledger, not inherited from prose.

---

## Fuzzing & Disclosure Safety (Phase 172)

The three defects with real client-estate consequences. A scanner that fuzzes an API without
asking, past its own documented ceiling, and then prints the target URL in an error, is a
liability in an engagement.

- [x] **SAFE-01**: `--fuzz` with non-interactive (non-TTY) stdin hard-aborts before issuing any
  request, with a non-interactive-mode error message. Currently the scan completes normally and
  exits 0.
  *Evidence: `UAT-96-02` — `echo | quirk ... --fuzz` completed and exited 0; no error printed.*

- [x] **SAFE-02**: The documented `--fuzz-budget` hard maximum of 500 is enforced at runtime; a
  larger value is rejected rather than silently honoured. The argparse default of 50 is already
  correct and must not change.
  *Evidence: `UAT-96-03` — `--fuzz-budget 501` completed normally and exited 0.*

- [x] **SAFE-03**: A spec-parsing failure reports a redacted preview of the target URL, never the
  full raw URL. Applies to the `SpecParsingError` path in
  `quirk.scanner.openapi_scanner.scan_openapi_spec` and any sibling path with the same shape.
  *Evidence: `UAT-94-05` — exception message contained the full raw `evil.example.com` URL.*

## Scanner Scope & Config Correctness (Phase 173)

Config that says "do not scan this" must actually prevent the scan, and disabled subsystems must
leave no trace in run output.

- [ ] **SCOPE-01**: ~~Email port probing (SMTP/IMAP/POP3) does not run when
  `connectors.enable_email` is `False`. The Motion page's Email Protocols section shows its
  empty state rather than real findings.~~ **Ruled a case defect (2026-08-29), promoted to
  Phase 175, not left silently Pending.** This requirement's own text asserts behavior the
  product deliberately does not have: `standard`/`deep` profiles intentionally auto-enable
  `enable_email`/`enable_broker` regardless of other config, by design since Phase 32/33/72-D-02.
  A fix implementing this requirement's literal wording was built, shipped, and live-verified in
  plan 173-01, then reverted the same day once shown to regress every real CLI config (`ports_tls`
  is a required YAML key, so "user narrowed the scan" was true unconditionally). See
  `173-DISPOSITIONS.md` for the full argument and both rejected suppression mechanisms. The real
  operator-facing gap — no docs stated auto-enable is independent of `scan.ports_tls` — is closed
  in `docs/configuration.md` (v5.17). No further code work is planned against this requirement's
  literal text; case-text correction is Phase 175's job.
  *Evidence: `UAT-36-05` — promoted to Phase 175, case text left byte-untouched in
  `docs/UAT-SERIES.md` Series 36.*

- [x] **SCOPE-02**: `run_stats.timings_sec` contains no `broker_scanning` key when no
  broker-scanning phase ran. Currently the key persists with a nonzero value while the broker row
  count is correctly 0.
  *Evidence: `UAT-33-01` — `COUNT` was 0 as expected but `timings_sec.broker_scanning` was present
  and nonzero. Fixed and re-verified 2026-08-29: generic `_PHASE_SKIPPED` sentinel closes the
  contract for 19 scanner phases (broker included), covered by
  `tests/test_phase_timer_omission.py` (6/6 passing, includes a ran-but-empty inversion guard).*

- [x] **SCOPE-03**: Enabling a scanner whose optional extras are absent produces the documented
  missing-extra signal — a stderr advisory line and a `scan_error_category=missing_extra` finding —
  consistently across scanner families. The broker/motion family currently produces neither.
  *Evidence: `UAT-41-01` — `enable_broker=true` with `kafka-python`/`pika`/`redis` absent exited 0
  silently. Contrast the identity family, which does emit the advisory.*

## Dashboard & API Correctness (Phase 174)

- [x] **DASH-06**: The dashboard score reflects the `--score-profile` the scan was run under, and
  the `profile` / `calibration` fields on `/api/scans` are populated rather than null.
  *Evidence: `UAT-8-07` — CLI scorecards were 93 / 91 / 90 across strict / balanced / standard
  while `/api/scans` reported 93 for all three, with both fields null.*

- [x] **DASH-07**: The dashboard empty state loads with zero console errors. A 404 for a missing
  resource is currently logged on a fresh database.
  *Evidence: `UAT-10-08` — page loaded 200 with correct empty-state text but logged
  `Failed to load resource 404`.*

- [ ] **DASH-08**: The sidebar navigation order matches its documented lock, or the documented lock
  is corrected to match the shipped navigation — whichever is right. An undocumented Hardware item
  currently sits between Motion and Data at Rest, contradicting the D-11 order.
  *Evidence: `UAT-39-07`. Decide deliberately which side is wrong; do not silently re-order a
  shipped UI to satisfy a stale document.*

## Case & Documentation Defect Correction (Phase 175)

Nine cases where the **product is correct and the UAT case is wrong**. Fixing these means
correcting the specification, not the code. Each must be verified as a case defect before it is
edited — if any turns out to be a real product bug, it is promoted, not quietly rewritten.

- [ ] **CASEFIX-01**: `UAT-85-02` and `UAT-85-06` grep for unquoted `pip install quirk-scanner[all]`
  while `README.md` and `docs/upgrade-guide.md` correctly quote it (`'quirk-scanner[all]'`) for zsh
  glob safety. The cases must accept the quoted form.

- [ ] **CASEFIX-02**: `UAT-84-02` cannot pass while `changelog.d/` holds only `README.md` — a
  towncrier draft over an empty fragment directory renders "No significant changes." with no
  sectioned headings. Either the case gains a fixture fragment or its pass criteria are corrected.

- [ ] **CASEFIX-03**: `UAT-110-06`'s own worked example is impossible — its `--stale-days 1`
  invocation can never trigger the `coverage_warning` line it documents (mathematically
  incompatible thresholds). `merge_scan()` itself was independently confirmed correct.

- [ ] **CASEFIX-04**: Copy and field-name mismatches where the case quotes a literal the product
  does not emit — `UAT-51-02` (capital-S "Session not found" vs the emitted lowercase),
  `UAT-55-01` (names a `control_id` field; the API returns `practice_number`), `UAT-9-10`
  (expected "Baseline scan recorded" vs the shipped empty-state copy), `UAT-10-11` (expects literal
  extras text; the product emits coded `QRK-INSTALL-001`). For each, decide whether the product's
  wording or the case's expectation is correct — `UAT-55-01` in particular may be an API naming
  problem rather than a case defect.

- [ ] **CASEFIX-05**: `UAT-58-07` records a FAIL against behaviour that is a **documented,
  deliberate deferral** — `run_scan.py` collapses all `@`-file guard reasons into a single generic
  `QRK-TARGET-002` message by design. Re-disposition as DEFERRED naming the design decision, or
  reopen the decision explicitly.

## Chaos-Lab Re-Run (Phase 176)

- [ ] **LABRUN-01**: The 13 cases recorded FAIL solely because the chaos lab was not running are
  re-executed **with the lab up**, and carry their true outcome — PASS, or a genuine defect not
  previously seen. Any new defect discovered is recorded with evidence and triaged into this
  milestone or the backlog explicitly.
  *Cases: `UAT-4-01`, `UAT-5-02`, `UAT-5-03`, `UAT-5-04`, `UAT-5-06`, `UAT-5-07`, `UAT-5-08`,
  `UAT-5-09`, `UAT-5-11`, `UAT-5-13`, `UAT-6-06`, `UAT-6-07`, `UAT-6-08`.*
  *Context: Phase 168's decision D-01 forbade starting the lab, so the sweep recorded "port not
  reachable" honestly. v5.17 carries no such constraint.*

- [ ] **LABRUN-02**: `UAT-1-02` is re-run and correctly dispositioned. It is currently recorded
  FAIL with evidence `Got: 'QU.I.R.K. v5.15.0', code=0` — which **matches** its own expected
  output. Phase 168-03 attributed this to a stale hardcoded check in `uat_runner.py`, but no such
  literal was found there; determine the real cause before dispositioning.

---

## Out of Scope (deliberate)

- The **57 coverage GAPs** — writing the missing tests is its own milestone-sized effort;
  `docs/uat-coverage-gaps.md` remains the worklist.

- **GATE-03's fork-safety allowlist** (18 files / 38 crash-exposed call sites) — recorded in
  `HORIZON.md`; needs a scoped phase and a decision between `run_fork_safe` migration and
  kwargs-only fixes.

- The remaining **HORIZON carry-forward items**: vitest `-t` anchoring, `cmd_classify` orphan-row
  pruning, vitest `-m slow` in CI, the stale editable install, and persisting the literal scan
  target.

- **Migration Execution** (HORIZON Candidate A) — still needs its shaping conversation.

## Traceability

| Requirement | Phase | Status |
|---|---|---|
| SAFE-01 | Phase 172 | Complete |
| SAFE-02 | Phase 172 | Complete |
| SAFE-03 | Phase 172 | Complete |
| SCOPE-01 | Phase 173 | Case defect — promoted to Phase 175 |
| SCOPE-02 | Phase 173 | Complete |
| SCOPE-03 | Phase 173 | Complete |
| DASH-06 | Phase 174 | Complete |
| DASH-07 | Phase 174 | Complete |
| DASH-08 | Phase 174 | Pending |
| CASEFIX-01 | Phase 175 | Pending |
| CASEFIX-02 | Phase 175 | Pending |
| CASEFIX-03 | Phase 175 | Pending |
| CASEFIX-04 | Phase 175 | Pending |
| CASEFIX-05 | Phase 175 | Pending |
| LABRUN-01 | Phase 176 | Pending |
| LABRUN-02 | Phase 176 | Pending |
