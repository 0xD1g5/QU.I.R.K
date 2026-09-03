# Requirements: v5.19 — Drain

**Milestone:** v5.19 Drain
**Opened:** 2026-09-03
**Source:** PM review at the v5.18 boundary. Every item below was **re-measured on 2026-09-03**
rather than inherited from its original report — two had drifted since they were recorded.

> [!important] Three of these five are one defect class
> **A hand-maintained enumeration that has drifted from the criterion it claims to enforce.**
> GATE-03's allowlist, `tests/skip_registry.py`'s line-keyed entries, and the a11y baselines are
> each a list asserting coverage it no longer has. The remedy in each case is **derivation, or a
> guard that checks the enumeration against its own criterion** — following Phase 178's
> `FINGERPRINT_TITLE_ALIASES`-derived-from-`TITLE_PREFIX_ALIASES` precedent, not a bigger list.

> [!warning] `DEFER-172-01` is an accumulator, not a static known-failure
> It absorbed a **new** skip during v5.18 — `test_closure_burndown.py:296` (Phase 180) — without
> anyone noticing, because the node was already red. A permanently-failing test is where new
> failures go to hide; it is what made Phase 180's genuine second failure hard to distinguish from
> the carried one. This is the reason it is in scope now rather than deferred a fourth time.

---

## Tooling Integrity (GSD state corruption)

- [ ] **TOOL-01**: `gsd-sdk` / `gsd-tools` `state.*` verbs stop silently corrupting `STATE.md`.
  **Bug A** (root-caused, patched locally 2026-09-03): `stateReplaceField()`'s bold pattern at
  `bin/lib/state-document.generated.cjs:42` lacks a `^` anchor and `/m`, so `**Field:**` matches
  mid-prose and `(.*)` eats the rest of the line. The plain-text branch below it is correctly
  anchored — only the bold branch was wrong.
  *Evidence: 9 corruptions across Phases 179-181; reproduced in isolation; fix verified.*

- [ ] **TOOL-02**: **Bug B** — `begin-phase` rebuilds frontmatter from a fixed schema instead of
  preserving it. `stopped_at` and the entire `progress:` block are **deleted** even with
  `ROADMAP.md` present; `milestone`/`milestone_name` survive only because they are re-derived from
  the roadmap, and reset to `v1.0`/`milestone` without it. **Not patched.** Either patch locally
  with a preserve-unknown-keys pass, or make hand-editing the documented protocol and land the
  upstream report.
  *Evidence: `.planning/reports/gsd-sdk-state-corruption-2026-09-03.md`, reproduced both ways.*

- [ ] **TOOL-03**: The local patch survives a GSD update, or its loss is detected. The patched file
  is `.generated.cjs` — regeneration silently reverts it. Needs either a re-apply check (there is a
  `verify-reapply-patches.cjs` precedent in `bin/`) or an upstream fix landed.

## Enumeration Drift (the shared defect class)

- [ ] **DRIFT-01**: `tests/test_cli_helper_usage.py`'s GATE-03 fork-safety check derives its file
  set instead of enumerating it. **Measured 2026-09-03:** the allowlist names **14** files while
  **21 unlisted files carry 35 direct `subprocess.*` call sites**. The docstring claims protection
  "regardless of which subset of tests is run" — a hand-maintained list cannot deliver that.
  Decide per site whether it migrates to `run_fork_safe` or gains the kwargs, and **grandfather
  explicitly rather than silently**.
  *Note: HORIZON recorded this as 11 files / 18 / 38 sites at the v5.16 audit — it has drifted
  further since, which is itself the argument for derivation.*

- [ ] **DRIFT-02**: `DEFER-172-01` closed — `tests/test_skip_registry.py::test_no_unregistered_skips`
  passes. **Measured 2026-09-03: 10 unregistered skips**, four of them in
  `test_uat_disposition_integrity.py`, one new from v5.18 (`test_closure_burndown.py:296`).
  Each skip is either registered with a real justification or deleted per Phase 41 D-01/D-04 —
  **never registered merely to quiet the gate**. The registry keys on `(file, LINENO)`, so also
  decide whether that keying survives or becomes content-addressed.

- [ ] **DRIFT-03**: a11y baselines are generated in the environment that enforces them. **33
  baselines were generated on macOS on 2026-08-27 in a single batch; the gate runs on Linux CI;
  31 have never been checked against the runner.** Regenerate via `--update-baselines` on a Linux
  runner rather than hand-patching counts. Folds in the route-coverage gap: `/hardware` and
  `/compare` are uncovered, and the same two routes are the 2 pending visual scenarios in
  `158-HUMAN-UAT.md` — triage together.
  *Evidence: `.planning/todos/pending/a11y-baseline-environment-mismatch.md`,
  `a11y-route-coverage-gap.md`.*

## Carried Defects

- [ ] **TRIAGE-01**: `TRIAGE-176-01` closed — surfaced by the Phase 176 chaos-lab re-run and
  explicitly triaged rather than absorbed. Needs its own plan and tests.

- [ ] **TRIAGE-02**: `TRIAGE-176-02` closed — same origin, same treatment.

## Out of scope (v5.19)

- **Sensor-origin closure coverage** — needs shaping first; the ingest envelope may not carry port
  scope / profile / extras at all, so a signature could be structurally present but semantically
  empty. Backlog item stands.
- **Candidate B — detection breadth** (AD CS live, S/MIME content, passive capture) — still gated
  on a demand signal. Deferred three times on this basis.
- **SaaS multi-tenancy** — still parked; the gate is a business-model signal.
- **Retro-fixing v5.18's accepted limitations** (CNSA 2.0 dates, D-178-A/B divergence, CDXA
  declarations) — each documented and bounded; none is a defect.

## Traceability

| Requirement | Phase | Status |
|---|---|---|
| TOOL-01 | TBD | Pending |
| TOOL-02 | TBD | Pending |
| TOOL-03 | TBD | Pending |
| DRIFT-01 | TBD | Pending |
| DRIFT-02 | TBD | Pending |
| DRIFT-03 | TBD | Pending |
| TRIAGE-01 | TBD | Pending |
| TRIAGE-02 | TBD | Pending |
