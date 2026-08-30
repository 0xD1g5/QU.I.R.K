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
  *Scope note: fixed for dashboard-launched (`ScanJob`-backed) sessions only —
  `scan.py:1263` now passes `profile=calibration` into `compute_readiness_score()`, matching the
  already-correct `GET /api/scan/latest` sibling. Persisting the score profile for CLI-run scans
  (so `profile`/`calibration` stop being null on those rows) is a deliberate deferral per D-01:
  it would require a new schema column/table with no reliable backfill key for historical rows,
  and is explicitly NOT built here — a follow-up candidate, not delivered.*

- [x] **DASH-07**: The dashboard empty state loads with zero console errors. A 404 for a missing
  resource is currently logged on a fresh database.
  *Evidence: `UAT-10-08` — page loaded 200 with correct empty-state text but logged
  `Failed to load resource 404`.*
  *Scope note: resolved as "no unhandled application error" per D-02, which was already true —
  re-verified against a genuinely empty DB (`174-EMPTY-DB-EVIDENCE.md`). The documented,
  intentional `QRK-DASHBOARD-006` 404 contract on `GET /api/scan/latest` is unchanged by design;
  the residual DevTools network-panel log line is a browser artifact, not an application error,
  and cannot be suppressed from application code.*

- [x] **DASH-08**: The sidebar navigation order matches its documented lock, or the documented lock
  is corrected to match the shipped navigation — whichever is right. An undocumented Hardware item
  currently sits between Motion and Data at Rest, contradicting the D-11 order.
  *Evidence: `UAT-39-07`. Decide deliberately which side is wrong; do not silently re-order a
  shipped UI to satisfy a stale document.*
  *Scope note: the document was wrong, not the product — Hardware's placement was planned,
  reviewed and shipped deliberately in Phase 128 (commit `07db14d75cc0f0da9546bcdd11d5c0ecf3cd9772`).
  The stale Phase-39 D-11 note was corrected to the canonical fourteen-item order derived live
  from `sidebar.tsx`; see `174-SIDEBAR-ORDER.md` for the full evidence chain. `sidebar.tsx` itself
  was never modified.*

## Case & Documentation Defect Correction (Phase 175)

Nine cases where the **product is correct and the UAT case is wrong**. Fixing these means
correcting the specification, not the code. Each must be verified as a case defect before it is
edited — if any turns out to be a real product bug, it is promoted, not quietly rewritten.

- [x] **CASEFIX-01**: `UAT-85-02` and `UAT-85-06` grep for unquoted `pip install quirk-scanner[all]`
  while `README.md` and `docs/upgrade-guide.md` correctly quote it (`'quirk-scanner[all]'`) for zsh
  glob safety. The cases must accept the quoted form.
  *Closed Phase 175 (175-02): corrected both cases to a quote-tolerant extended-regex grep;
  both greps confirmed exit 0 against the real files. `Result:` lines re-dispositioned PASS via
  175-06's ledger cycle.*

- [x] **CASEFIX-02**: `UAT-84-02` cannot pass while `changelog.d/` holds only `README.md` — a
  towncrier draft over an empty fragment directory renders "No significant changes." with no
  sectioned headings. Either the case gains a fixture fragment or its pass criteria are corrected.
  *Closed Phase 175 (175-02): pass criteria corrected to accept towncrier's documented empty-state
  message; no fixture fragment added (would leak into the real changelog at next release).*

- [x] **CASEFIX-03**: `UAT-110-06`'s own worked example is impossible — its `--stale-days 1`
  invocation can never trigger the `coverage_warning` line it documents (mathematically
  incompatible thresholds). `merge_scan()` itself was independently confirmed correct.
  *Closed Phase 175 (175-02): worked example replaced with `--stale-days 30`
  (`_DEFAULT_STALE_DAYS`) against a sensor forced overdue 3 days; `merge_scan()` unmodified.*

- [x] **CASEFIX-04**: Copy and field-name mismatches where the case quotes a literal the product
  does not emit — `UAT-51-02` (capital-S "Session not found" vs the emitted lowercase),
  `UAT-55-01` (names a `control_id` field; the API returns `practice_number`), `UAT-9-10`
  (expected "Baseline scan recorded" vs the shipped empty-state copy), `UAT-10-11` (expects literal
  extras text; the product emits coded `QRK-INSTALL-001`). For each, decide whether the product's
  wording or the case's expectation is correct — `UAT-55-01` in particular may be an API naming
  problem rather than a case defect.
  *Closed Phase 175 (175-03, 175-04, 175-05). `UAT-55-01` was judged, not assumed (D-01): the
  case is corrected to name `practice_number`, consistent across the Pydantic model, TS type and
  PDF renderer — the QRAMM API field was NOT renamed and NO `control_id` alias was added, a
  breaking-change alternative explicitly declined by the user. Also covers `UAT-94-05` (D-03
  criterion corrected to userinfo/query/fragment stripping, host retained by design; companion
  case `UAT-94-09` added in 175-05 to detect a redaction regression the original fixture could
  not) and `UAT-36-05` (prerequisite corrected to an explicit connectors opt-out) and `UAT-8-07`
  (re-scoped to a legal dashboard-launched calibration comparison; DEFERRED disposition
  unchanged).*

- [x] **CASEFIX-05**: `UAT-58-07` records a FAIL against behaviour that is a **documented,
  deliberate deferral** — `run_scan.py` collapses all `@`-file guard reasons into a single generic
  `QRK-TARGET-002` message by design. Re-disposition as DEFERRED naming the design decision, or
  reopen the decision explicitly.
  *Closed Phase 175 (175-03, 175-06). Re-dispositioned DEFERRED (not PASS) naming `T-164-01`
  explicitly, per D-02. The `QRK-TARGET-002` collapsing decision was NOT reopened — this remains a
  named, deliberate information-disclosure mitigation left in place, not endorsed as clean-slate
  correct.*

## Chaos-Lab Re-Run (Phase 176)

- [ ] **LABRUN-01**: The 13 cases recorded FAIL solely because the chaos lab was not running are
  re-executed **with the lab up**, and carry their true outcome — PASS, or a genuine defect not
  previously seen. Any new defect discovered is recorded with evidence and triaged into this
  milestone or the backlog explicitly.
  *Cases: `UAT-4-01`, `UAT-5-02`, `UAT-5-03`, `UAT-5-04`, `UAT-5-06`, `UAT-5-07`, `UAT-5-08`,
  `UAT-5-09`, `UAT-5-11`, `UAT-5-13`, `UAT-6-06`, `UAT-6-07`, `UAT-6-08`.*
  *Context: Phase 168's decision D-01 forbade starting the lab, so the sweep recorded "port not
  reachable" honestly. v5.17 carries no such constraint.*
  **PARTIALLY MET (2026-08-30) — not Complete.** All 13 cases were genuinely re-executed against a
  live 33-container `core + phaseA + jwt + ssh-weak + identity` chaos lab (176-03/176-04):
  **9 PASS / 2 FAIL / 2 GAP.** PASS: `UAT-4-01`, `UAT-5-02/03/04/06/07/08/09`, `UAT-6-07`. The 2
  FAILs are real, root-caused, evidenced, and BACKLOGGED, not fixed in this phase —
  `UAT-5-13` (`TRIAGE-176-01`: chaos-lab `certs/keycloak.crt` is byte-identical to
  `certs/modern.crt`, a lab-fixture defect) and `UAT-6-06` (`TRIAGE-176-02`: no
  `PLAINTEXT_HTTP`/`HTTP_EXPOSURE` finding-type token exists in `quirk/`; ports 8000 and 8444
  produce byte-identical findings once both are in `ports_tls`, root-caused to
  `_postprocess_findings` in `quirk/engine/findings_evaluator.py` — a genuine PRODUCT
  classification gap). The 2 GAPs (`UAT-5-11`, `UAT-6-08`) both trace to a missing `ssh-audit`
  binary in this execution environment (confirmed at `quirk/scanner/ssh_scanner.py` source level)
  — a tooling gap, not a lab or product defect; the binary was not installed to manufacture a
  cleaner board, per this milestone's package-install exclusion. Because two of the thirteen cases
  did not reach a lab-verified outcome, LABRUN-01's own "re-execute with the lab actually running"
  success criterion is not fully satisfied for those two. Both BACKLOG items are promoted verbatim
  into `.planning/ROADMAP.md`'s Backlog section. See `176-DEFECT-TRIAGE.md`,
  `176-LABRUN-EVIDENCE.md`, and `docs/UAT-SERIES.md` Series 176 for full evidence.

- [x] **LABRUN-02**: `UAT-1-02` is re-run and correctly dispositioned. It is currently recorded
  FAIL with evidence `Got: 'QU.I.R.K. v5.15.0', code=0` — which **matches** its own expected
  output. Phase 168-03 attributed this to a stale hardcoded check in `uat_runner.py`, but no such
  literal was found there; determine the real cause before dispositioning.
  **Complete (2026-08-30).** Root cause found: `uat_runner.py:154`'s pass-condition contained a
  stale `'4.2.0'` version literal (frozen since commit `bebb1d8fc`, 2026-04-16) plus a
  `'quirk' in ver.lower()` substring check broken by the dotted `QU.I.R.K.` acronym (`.lower()` of
  `QU.I.R.K. v5.15.0` never contains the contiguous substring `quirk`), making the condition
  unsatisfiable by any current-era product output regardless of what shipped. Fixed under D-01's
  narrow, explicitly-recorded lift — exactly one line of `uat_runner.py` changed
  (`git diff --numstat` = `1 1`), scoped to this pass-condition only. Guarded by a falsifiable
  shape-pinning regression test, `tests/test_uat_runner_version_check.py` (6 nodes), demonstrated
  RED against the historical condition and GREEN against the fix. `UAT-1-02` re-executed against
  the repaired harness and dispositioned PASS through the ledger (`scripts/uat_disposition_apply.py
  apply` → `verify`). **No version bump was made** — v5.16 shipped deliberately untagged (commit
  `03656097`); v5.17 is a planning-milestone label, not a release. The `UAT-5-*` SKIP-vs-FAIL text
  discrepancy at `uat_runner.py` lines 531-545 is a separate, deliberately deferred item, named and
  scoped out in `176-HARNESS-LIFT.md` — not touched by this fix.

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
| DASH-08 | Phase 174 | Complete |
| CASEFIX-01 | Phase 175 | Complete |
| CASEFIX-02 | Phase 175 | Complete |
| CASEFIX-03 | Phase 175 | Complete |
| CASEFIX-04 | Phase 175 | Complete — UAT-55-01 field not renamed, no alias (D-01) |
| CASEFIX-05 | Phase 175 | Complete — DEFERRED, T-164-01 not reopened (D-02) |
| LABRUN-01 | Phase 176 | Partially Met, not Complete — 9/13 PASS, 2 BACKLOG, 2 GAP (ssh-audit) |
| LABRUN-02 | Phase 176 | Complete |
