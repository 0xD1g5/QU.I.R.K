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

- [x] **TOOL-01**: `gsd-sdk` / `gsd-tools` `state.*` verbs stop silently corrupting `STATE.md`.
  **Bug A** (root-caused, patched locally 2026-09-03): `stateReplaceField()`'s bold pattern at
  `bin/lib/state-document.generated.cjs:42` lacks a `^` anchor and `/m`, so `**Field:**` matches
  mid-prose and `(.*)` eats the rest of the line. The plain-text branch below it is correctly
  anchored — only the bold branch was wrong.
  *Evidence: 9 corruptions across Phases 179-181; reproduced in isolation; fix verified.*
  **Reopened 2026-09-03 (182-05):** the live phase-close demonstration of `state begin-phase`
  against the real `.planning/STATE.md` reproduced a **second, unpatched** instance of the same
  defect class in the sibling read function `stateExtractField()`
  (`bin/lib/state-document.generated.cjs:29`), which has an unanchored `**Field:**` bold pattern
  that 182-01's patch never touched (the patch only fixed the write-side `stateReplaceField()`).
  This let a `` `**Status:**` ``-in-prose sentence at `.planning/STATE.md:82` (itself part of this
  phase's own test-writing) get read as the live Status value, producing a garbage
  `status:` frontmatter field and a false-negative on the idempotency "already executing" check,
  which in turn reset `Plan: 4 of 5` back to `Plan: 1 of 5`. A second, related defect in the
  `Stopped At` extractor's session-scoping guard (upstream bug #2444) requires the literal header
  `## Session`; this project's convention is `## Session Continuity`, which does not match, so the
  guard fell through to an unscoped full-body search and picked up a stale
  `Stopped at:` line from the archived `## Session Continuity` section instead of the current
  value. Both hazards were caught by the pre/post-write diff inspection mandated by 182-05's own
  protocol; the write was reverted before commit (`git status --porcelain .planning/STATE.md`
  confirmed clean afterward). See `182-05-SUMMARY.md` for the full reproduction. Filed as
  **TOOL-04** below.
  **Closed 2026-09-04 (182-06):** `stateExtractField()` anchored to
  `` ^\s*\*\*${escaped}:\*\*[ \t]*(.+)$ ``/`im` — the exact anchor fix `stateReplaceField()`
  already had — proven RED against the installed, pre-patch toolchain via a full-COMMAND
  regression test (`test_begin_phase_does_not_read_body_prose_as_machine_fields`, run against a
  fixture shaped like this real file, not just the function in isolation) before the patch, then
  GREEN after. **Re-demonstrated 2026-09-04 (182-08):** the live `state begin-phase` verb was run
  again against this real, live `.planning/STATE.md` (the same file, the same command, the same
  hazard-detection protocol as the 182-05 reproduction) and the diff came back clean against both
  named corruption signatures — no garbled bold-field prose, no dropped frontmatter key. See
  `182-08-SUMMARY.md` for the full diff and key-by-key frontmatter comparison.

- [x] **TOOL-02**: **Bug B** — `begin-phase` rebuilds frontmatter from a fixed schema instead of
  preserving it. `stopped_at` and the entire `progress:` block are **deleted** even with
  `ROADMAP.md` present; `milestone`/`milestone_name` survive only because they are re-derived from
  the roadmap, and reset to `v1.0`/`milestone` without it. **Not patched.** Either patch locally
  with a preserve-unknown-keys pass, or make hand-editing the documented protocol and land the
  upstream report.
  *Evidence: `.planning/reports/gsd-sdk-state-corruption-2026-09-03.md`, reproduced both ways.*

- [x] **TOOL-03**: The local patch survives a GSD update, or its loss is detected. The patched file
  is `.generated.cjs` — regeneration silently reverts it. Needs either a re-apply check (there is a
  `verify-reapply-patches.cjs` precedent in `bin/`) or an upstream fix landed.

- [x] **TOOL-04** (new 2026-09-03, discovered during 182-05's live `state begin-phase`
  demonstration): two unpatched read-side defects in
  `bin/lib/state-document.generated.cjs`/`bin/lib/state.cjs` still silently corrupt
  `.planning/STATE.md`, independent of the TOOL-01 write-side (`stateReplaceField`) fix.
  (a) `stateExtractField()` (`state-document.generated.cjs:29`) has the identical unanchored
  `\*\*Field:\*\*[ \t]*(.+)` bold pattern that `stateReplaceField()` had before 182-01's patch —
  never anchored, never fixed — so it can read a `` `**Status:**` ``-quoted sentence anywhere in
  the body as the live Status value. (b) The `Stopped At` extractor's session-scoping guard
  (`state.cjs`, upstream bug #2444) matches only the literal header `## Session`; this project's
  own convention is `## Session Continuity`, which does not match `/##\s*Session\s*\n/i`, so the
  guard silently falls through to an unscoped full-body search and can pick up a stale value from
  an archived section. *Evidence: reproduced live against the real `.planning/STATE.md` during
  182-05; see `182-05-SUMMARY.md` for the full diff and root-cause trace. The corrupted write was
  caught pre-commit and reverted — no data was actually lost.*
  **Closed 2026-09-04 (182-06, 182-07):** 182-06 anchored `stateExtractField()` (item (a)) and
  widened the session-scoping guard in `buildStateFrontmatter()` to
  `` ^##\s+Session\b[^\n]*\n([\s\S]*?)(?=\n##|$) ``/`im` (item (b)), plus anchored `focusPattern`
  inside `cmdStateBeginPhase` itself — a write-path instance the plan's own hand-derived
  orientation list missed and a plan reviewer found. 182-07 then enumerated every remaining
  `**Field:**`-shaped bold-field construct in both files via a run-time source scan (not a
  hand-written list) locked by `test_bold_field_regex_class_is_fully_dispositioned`, anchored the
  one remaining write-path instance found that way (`boldProgressPattern` in
  `cmdStateUpdateProgress`), and dispositioned the scan's one new, previously-undocumented find
  (`cmdStateGet`'s `boldPattern`) `accepted-read-only` since it only ever reaches stdout display,
  never a STATE.md write. All four write-path instances are anchored; the durability layer
  (`gsd-local-patches/`/`gsd-pristine/`) is re-seeded so none of it silently reverts.
  **Re-demonstrated 2026-09-04 (182-08):** the live verb was re-run against this real,
  live `.planning/STATE.md` and the diff came back clean against both named hazard signatures.
  See `182-06-SUMMARY.md`, `182-07-SUMMARY.md`, and `182-08-SUMMARY.md`.

## Enumeration Drift (the shared defect class)

- [x] **DRIFT-01**: `tests/test_cli_helper_usage.py`'s GATE-03 fork-safety check derives its file
  set instead of enumerating it. **Measured 2026-09-03, corrected 2026-09-04 at Phase 183 close:**
  the allowlist named 14 files (of 15 `_COVERED_FILES` entries) while the true unlisted set was
  **18 files carrying 28 direct `subprocess.*` call sites** (the planning-time 21/35 figure was
  itself stale). The docstring claims protection "regardless of which subset of tests is run" —
  a hand-maintained list cannot deliver that. **COMPLETE:** all 28 sites migrated to
  `run_fork_safe`/`run_cli` (Phase 183, plans 01-04); the gate itself rewritten to derive its file
  set via `Path.glob("tests/**/*.py")` at test-run time instead of reading `_COVERED_FILES`, with
  bare-name `subprocess` import detection added and 4 permanent, mutation-killed falsifiability
  self-tests (Phase 183, plan 05). `_GRANDFATHERED` ships empty — zero sites needed grandfathering.
  *Note: HORIZON recorded this as 11 files / 18 / 38 sites at the v5.16 audit — it had drifted
  further since, which was itself the argument for derivation over a longer list.*

- [ ] **DRIFT-02**: `DEFER-172-01` closed — `tests/test_skip_registry.py::test_no_unregistered_skips`
  passes. **Measured 2026-09-03: 10 unregistered skips**, four of them in
  `test_uat_disposition_integrity.py`, one new from v5.18 (`test_closure_burndown.py:296`).
  Each skip is either registered with a real justification or deleted per Phase 41 D-01/D-04 —
  **never registered merely to quiet the gate**. The registry keys on `(file, LINENO)`, so also
  decide whether that keying survives or becomes content-addressed.

- [x] **SCORE-01**: `coverage_ratio` measures assessment coverage, not protocol composition.
  **Measured 2026-09-04 against a live 20-endpoint chaos-lab scan** (`scan_run_id
  2026-09-04T15:28:54`): `quirk/intelligence/confidence.py:90` computes
  `(tls_count + ssh_count) / endpoints`, so **8 endpoints whose cryptography QUIRK successfully
  assessed are excluded from coverage** — SMTP-STARTTLS x2, SMTPS, IMAPS, IMAP-STARTTLS, POP3S,
  POP3-STARTTLS, KERBEROS. `ADVISORY` pseudo-endpoints (scanner self-reports such as
  `liveness-prepass`, not scanned assets) sit in the denominator, so every advisory emitted
  mathematically lowers coverage.

  Impact is not cosmetic: 8/20 = 0.40 -> 14.0 of 35 points -> confidence **77 MEDIUM**. Counting
  all crypto-bearing protocols gives 16/20 = 0.80 -> 28.0 points -> **91 HIGH**; also excluding
  ADVISORY from the denominator gives 16/19 = 0.84 -> 29.5 -> **92 HIGH**. Same evidence, same
  scan, different client-facing confidence rating.

  The restriction is **undocumented**: no comment in `confidence.py` justifies it (contrast the
  adjacent `CR-01` comment, which carefully explains the TLS-enum bonus guard), and no
  operator-facing doc defines `coverage_ratio` at all — `docs/report-interpretation.md` never
  mentions it.

  **Locked at capture (2026-09-04): versioned, not silent.** `compute_confidence()` returns a
  dedicated formula-version marker (`CONFIDENCE_FORMULA_VERSION`); a report without one is
  pre-184.1 by definition, and this rule is stated explicitly in `docs/report-interpretation.md`.
  **There is no historical confidence data to migrate.** The premise that the formula feeds
  `/api/trends` and compares stored historical scan sessions is verified false:
  `quirk/intelligence/trends.py` and `quirk/dashboard/api/routes/trends.py` call
  `compute_readiness_score` exclusively and contain zero occurrences of `confidence`; all three
  live `compute_confidence()` call sites (`quirk/reports/writer.py:397`,
  `quirk/reports/executive.py:131`, `quirk/dashboard/api/routes/scan.py:1610`) call
  `build_evidence_summary(endpoints, findings)` fresh immediately beforehand, so re-running a
  report against an old scan already yields the new number because every surface recomputes; and
  `quirk/models.py` has no `confidence_score` or `confidence_rating` column. This lock does not
  require bumping `intelligence.intelligence_version` — per D-12 that config value is one of three
  drifting values, none of which means "which scoring formula produced this," and reconciling them
  is deferred to its own phase. A step change in a client's score across two reports is
  explainable via the formula-version marker and the documentation, not via a backfill.

  **Gap found and closed (2026-09-04, plans 184.1-06/07):** `184.1-VERIFICATION.md` found the
  formula-version marker above was inert on every shipped surface — `quirk/reports/writer.py`'s
  compat `conf` dict, `quirk/reports/executive.py`'s generated markdown, and
  `quirk/dashboard/api/schemas.py`'s `ConfidenceData` all dropped the field before it reached a
  client (independently flagged as CR-01 in `184.1-REVIEW.md`, never previously fixed). Plan
  `184.1-06` wired all three consumers and locked each with a dedicated emitted-artifact test in
  `tests/test_confidence_formula_version_surfaces.py`; plan `184.1-07` made
  `docs/report-interpretation.md`'s D-15 rule name the three exact surfaces and corrected
  `UAT-184.1-01` to exercise those emitted artifacts instead of `compute_confidence()` in
  isolation. SC-3 is now genuinely satisfied, not merely locked at capture.

- [x] **SCORE-02**: the shipped config template enables a defensible out-of-the-box scanning
  baseline, and template/working-config drift is closed. **Measured 2026-09-04:**
  `grep -c '^\s*enable_[a-z]*: true' quirk/config_template.yaml` returns **0** — every connector
  ships `false` or commented out (`enable_aws`, `enable_azure`, `enable_jwt`, `enable_container`,
  `enable_source` explicit `false`; kerberos/saml/dnssec/gcp/db commented). A new user generating a
  config gets TLS/SSH port scanning only.

  This compounds SCORE-01: the narrowest possible default surface, scored by a metric that only
  rewards that same narrow surface, so nothing signals what is missing. This repo's own
  `config.yaml` enables Kerberos, SAML and DNSSEC — hand-tuned for the chaos lab and never
  propagated back to the template, the same drift class as the `db_path` divergence fixed in
  `87cff201`.

  Decide per connector whether "enabled by default" is meaningful (JWT/container/source require
  targets to do anything, so enabling them without targets may be noise rather than coverage) and
  either enable it, or state in the template why it ships off. Silence is what this requirement
  removes.

- [x] **SCORE-03**: timestamps mean the same thing end to end. **Measured and reproduced
  2026-09-04.** The backend stores **naive UTC** — `datetime.now(timezone.utc).replace(tzinfo=None)`
  is the deliberate house pattern (`merge/scan.py:186`, `otics_cadence.py:61`,
  `notify/dispatcher.py` x5) — and the API serializes it **without an offset**:
  `"scanned_at": "2026-09-04T15:28:56.218111"`. Per ECMAScript, a no-offset date-time string is
  parsed as **local time**, so `new Date(scannedAt)` in
  `src/dashboard/src/components/ScanDateBadge.tsx:6` renders a UTC clock as local. Demonstrated: a
  scan that ran at **11:12:58 EDT** displays as **"Last scan: Sep 4, 2026 3:13 PM"** — a
  **4-hour** skew.

  The codebase contradicts itself: sibling `scan_run_id` on the same row IS timezone-aware
  (`2026-09-04T15:28:54.125544+00:00`), and scan logs stamp `[15:29:52Z]` — one row carries an
  offset, an adjacent column does not.

  **Blast radius: every file the run-time source scan identifies** as calling `new Date(` on API
  timestamps (`sensors`, `scan-history`, `motion`, `schedules`, `certificates`, `executive`,
  `print`, `trends`, `compare`, `hardware`, `ScanDateBadge`, ...); the existing suite is blind to it.

  **Re-derived 2026-09-05:** `quirk/` has **zero** `datetime.utcnow()` calls — the two occurrences
  originally counted here are comments (Phase 51 DEBT-01 ban, `qramm_cmd.py:9`, `cve_cmd.py:10`),
  not calls. Real target: `tests/` — **36 actual call sites across 12 files** (38 textual
  occurrences across 13 files; two are the existing gate's own docstring/assertion literal at
  `tests/test_qramm_router.py:523,531`, not calls). Locked by generalizing the existing
  QRAMM-scoped source scan to all of `quirk/`.

  Report output must also state the scan instant alongside the render instant, each zone-labeled,
  per the D-16a widening — see ROADMAP.md SC-6.

  Fixing this is a **client-credibility** issue, not cosmetic: a report timestamped four hours off
  cannot be reconciled against a client's own logs during an engagement.

  **Closed 2026-09-05 (Phase 184.3, plans 184.3-01 through 184.3-11).** API responses carry an
  explicit `+00:00` offset (`UTCDateTime`/`stamp_utc_iso()`,
  `quirk/dashboard/api/_timestamp_utils.py`); `quirk/` has zero `datetime.utcnow()` calls and the
  36 `tests/` sites are migrated; the frontend routes every timestamp render through
  `src/dashboard/src/lib/datetime.ts`; `/print` and all four report renderers state a labeled-UTC
  scan instant (`Scan Completed`) distinct from the render instant (`Generated`); two run-time
  source-scan gates (`tests/test_timestamp_serialization_gate.py`,
  `new-date-argument-guard.test.ts`) lock the convention in. The 184.3-11 Task 3 human-verify
  checkpoint confirmed 4 of 5 cross-surface behaviors live (dashboard badge, scan selector,
  `/print`, report exports). The 5th — a live certificate-expiry calendar-day comparison — is
  **DEFERRED**, not fixed: the live DB's certificates all expire midday UTC, which makes that
  specific manual check vacuous by construction regardless of correctness; substitute coverage is
  the real, executing, TZ-pinned test at `src/dashboard/src/lib/__tests__/datetime.test.ts:39`. A
  separate, pre-existing, out-of-phase-scope defect (dashboard certificate view renders phantom
  rows for failed TLS handshakes, `quirk/dashboard/api/routes/scan.py:1656-1669`) was found during
  this closure and is tracked separately in STATE.md Deferred Items — not part of this
  requirement's scope and not blocking its closure.

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
| TOOL-01 | 182-01, 182-03, 182-06 | Complete (re-closed 2026-09-04, 182-08 re-demonstration clean) |
| TOOL-02 | 182-02 | Complete |
| TOOL-03 | 182-03, 182-04 | Complete |
| TOOL-04 | 182-06, 182-07 | Complete (closed 2026-09-04, 182-08 re-demonstration clean) |
| DRIFT-01 | 183-01, 183-02, 183-03, 183-04, 183-05, 183-06 | Complete |
| DRIFT-02 | TBD | Pending |
| SCORE-01 | 184.1-01, 184.1-02, 184.1-03, 184.1-04, 184.1-05, 184.1-06, 184.1-07 | Complete |
| SCORE-02 | 184.2-01, 184.2-02, 184.2-03, 184.2-04, 184.2-05, 184.2-06 | Complete |
| SCORE-03 | 184.3-01, 184.3-02, 184.3-03, 184.3-04, 184.3-05, 184.3-06, 184.3-07, 184.3-08, 184.3-09, 184.3-10, 184.3-11 | Complete (closed 2026-09-05; 1 manual leg DEFERRED with cited substitute coverage) |
| DRIFT-03 | TBD | Pending |
| TRIAGE-01 | TBD | Pending |
| TRIAGE-02 | TBD | Pending |
