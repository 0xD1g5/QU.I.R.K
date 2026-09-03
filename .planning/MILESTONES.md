# Milestones

## v5.17 Defect Drain (Shipped: 2026-09-01)

**Phases completed:** 5 phases (172-176), 28 plans + 2 user-directed addenda = 30 execution units
**Git range:** `09adf147` (2026-08-28) → `05d96fb0` (2026-09-01) — 107 commits, 5 days
**Requirements:** 16/16 satisfied (15 complete, 1 satisfied-by-override)

**What this milestone was:** a drain of the 18 genuine defects surfaced by v5.16's UAT corpus
drain, plus the 13 cases that had failed only because the chaos lab was down. Scope was
re-measured from the ledger before opening rather than inherited from v5.16's prose — the reported
"32 product FAILs" resolved to **18 genuine defects** (9 product bugs, 9 case/doc defects),
13 lab-down artifacts, and 1 spurious.

**Key accomplishments:**

- **Fuzzing & disclosure safety (SAFE-01/02/03).** `--fuzz` on a non-TTY stdin and
  `--fuzz-budget` over 500 now hard-abort at argument-validation time with coded FUZZ-001/FUZZ-002
  errors and exit 2, before any config load or scan phase runs. Spec-parsing failures now redact
  real URL components instead of printing the raw target — the old `_redact_preview` only
  truncated, and its byte-identical non-URL twin was renamed `_truncate_preview` to kill the
  "two helpers, one misleading name" trap that let the defect survive review. A docs==code drift
  gate ties the documented budget ceiling to the enforced constant, proven to fail loudly by
  actually perturbing the docs.

- **Scanner scope & config correctness (SCOPE-02/03).** A module-level `_PHASE_SKIPPED` sentinel
  makes `timings_sec` omit keys for the 19 scanner phases that never ran, with an inversion-guard
  test proving phases that ran-but-found-nothing keep theirs. Broker's missing-extra gate now
  consults all three availability flags instead of SSLYZE alone, and smime/adcs got their
  first-ever missing-extra advisory wiring — a silent exit-0 gap that the existing source-grep
  tests were proven blind to.

- **Dashboard & API correctness (DASH-06/07/08).** `GET /api/scans` now scores each
  dashboard-launched session under its own stored calibration instead of silently defaulting every
  row to "balanced" — a one-line `profile=` omission diverging from its already-correct sibling
  call. The empty-database path was re-probed against a genuinely empty DB and locked with a
  regression guard, and the 14-item sidebar order was derived live from `sidebar.tsx` and
  reconciled with its documentation via a new bidirectional guard.

- **Case-defect correction (CASEFIX-01..05) — zero product code changed.** Twelve UAT cases whose
  own grep patterns, pass criteria, and worked examples were wrong against correct product
  behaviour were corrected, each carrying its argument and a citation to the source disposition.
  All twelve were independently re-confirmed by live execution against a post-172/174 checkout
  before any text was touched. Two cases were left DEFERRED rather than force-fixed. A new
  detector (`UAT-94-09`) was added — the first Series-94 case able to catch a redaction
  regression — with falsifiability proven by running it against a neutered module and watching it
  flip RED.

- **Chaos-lab re-run (LABRUN-01/02) — final tally 10 PASS / 3 FAIL / 0 GAP.** All 13 lab-down
  cases were re-executed with the lab actually up (33 containers, 18 ports verified listening) and
  now carry their true outcome instead of a four-month-old artifact. `UAT-1-02`'s false FAIL was
  root-caused to a harness bug: `uat_runner.py:154` gated PASS on
  `'4.2.0' in ver or 'quirk' in ver.lower()`, **both disjuncts unsatisfiable** against
  `QU.I.R.K. v5.15.0` (the dots defeat the substring check). Every genuine defect the re-run
  surfaced was explicitly triaged rather than absorbed.

- **The re-run falsified its own conclusion — and found a live scanner bug.** Plan 176-07 blamed
  two remaining GAPs on a missing `ssh-audit` binary. Installing it exposed TRIAGE-176-03:
  `quirk/scanner/ssh_scanner.py` passed two positionals to a tool that takes one `host:port`, so
  **every SSH scan since that integration shipped had silently degraded to a banner grab with
  `ssh_audit_json` NULL**. Fixed with an argv-asserting regression test the pre-existing mocks
  never had. A rubber-stamp re-run would have pocketed the PASS.

**Method note.** This milestone repeatedly falsified its own premises rather than inheriting them:
v5.16's defect count was re-derived from the ledger; SCOPE-01's fix was built, shipped,
live-verified, then **reverted the same day** once shown to regress every real CLI config;
Phase 176's own success criterion ("no such literal exists in `uat_runner.py`") was proven wrong
with a `git show`; and 176-07's root cause was overturned by 176-08.

### Known Gaps

- **SCOPE-01** — closed as **satisfied-by-override**, not as a defect. Its own text asserts
  behaviour the product deliberately does not have (`standard`/`deep` profiles auto-enable
  `enable_email`/`enable_broker` by design since Phase 32/33/72-D-02). The literal fix was built,
  shipped, live-verified, and reverted the same day. The real operator-facing gap — no docs said
  auto-enable is independent of `scan.ports_tls` — was closed in `docs/configuration.md`. Its
  checkbox is intentionally `[ ]`; do not flip it.
- **TRIAGE-176-01 / TRIAGE-176-02** — two genuine defects surfaced by the lab re-run, explicitly
  triaged to the ROADMAP Backlog with evidence. Each needs its own plan and tests. Candidates for
  v5.18 opening scope.
- Two `UAT-6-08` case-text corrections carried forward to the Backlog, following the
  `UAT-94-05`/`UAT-36-05`/`UAT-8-07` precedent.

Known deferred items at close: **8** (see STATE.md `## Deferred Items`, re-triaged 2026-09-01).
Only one — a11y route coverage for `/hardware` and `/compare` — is a genuine product gap; the rest
are a known scanner false positive, two test-hygiene items (`DEFER-172-01/02`), a procurement
block (Windows Authenticode certificate), and correctly-triaged Phase 176 backlog output.

**Verification:** all 5 phases carry a `NN-VERIFICATION.md`. Phase 176's was produced on
2026-09-01 (`status: passed`, 15/15 must-haves, 0 overrides) and closed the only two gaps the
v5.17 milestone audit had raised — see the Resolution Addendum in
`milestones/v5.17-MILESTONE-AUDIT.md`. Full suite at close: **1 failed, 3802 passed** — the sole
failure being the pre-existing `DEFER-172-01` `test_skip_registry` node.

**Not tagged.** Milestone numbering has drifted from the product version (`pyproject.toml` remains
`5.15.0`); v5.16 was likewise archived without a tag.

---

## v5.16 Review Drain & Gate Integrity (Development complete: 2026-08-28 — untagged)

**Phases completed:** 8 phases (164-171), 47 plans
**Git range:** `9b1f5a3b` → `41150ab9` — **187 commits in two days** (opened 2026-08-26)
**Scope:** 145 tracked files (+9,770 / −2,462); much of the work landed in gitignored `.planning/` paths and is not in those counts
**Requirements:** 24/24 complete, 0 orphans. All 8 phases verified `passed`.

*(Entry authored retroactively 2026-09-01 from the v5.16 archives; not written at close.)*

**What this milestone was:** closing every open finding from the 2026-08-24 third-party functional
review, so QUIRK's own gating documents, accessibility baseline, and first-run path became as
trustworthy as the scan pipeline v5.15 had fixed.

**Key accomplishments:**

- **The release-gate document went from 377 unrecorded cases to zero undispositioned across all
  666** (168, 169), held there by a standing CI gate (`tests/test_uat_zero_undispositioned_gate.py`)
  proven load-bearing by mutating a scratch corpus and confirming it names the offending case by ID
  and line. Built on `scripts/uat_disposition_apply.py` (classify/apply/verify), a 377-row JSONL
  ledger, and an anti-fabrication guard requiring every named substitute node to both resolve via
  `pytest --collect-only` *and* pass.

- **The substantive deliverable was the honest record, not the green gate.** Final dispositions: 202
  PASS, 32 FAIL, 42 DEFERRED, 44 SKIP, **57 named coverage GAPs** — each stating what would be
  needed to close it. `docs/uat-coverage-gaps.md` is the resulting worklist. A corpus reading 100%
  PASS would have been worth nothing.

- **First-run correctness (164).** `allow_abbrev=False` on all 10 parsers, because `--targets` was
  prefix-matching `--targets-file` into an uncaught `FileNotFoundError`. Added a `TARGET` error
  domain, fixed the dashboard empty state, and swept the repo for a documented invocation that
  did not exist.

- **Accessibility baseline made meaningful (165).** Replaced axe's CSS-selector-path baseline key —
  which breaks on any UI refactor — with a per-route/per-rule count-budget schema carrying a ratchet
  and a refusal to write `critical`-impact entries. Pinned `@axe-core/puppeteer` exactly.

- **Gate robustness (166).** E2E smoke went from failing to **3.1s against a 180s budget**;
  `uat_runner.py` migrated onto the hardened `xml_safe.parse_safely()` chokepoint with an AST import
  gate; and a suite-wide macOS `fork()`-after-`Network.framework` SIGSEGV class was closed — **zero
  fatal signals, down from 14 across 6 files**.

- **Traceability tail (170).** CHANGELOG backfilled for v5.9.0–v5.14.0, honestly marking v5.13/v5.14
  as developed-but-never-released, plus a large cross-phase reference repair (see Known Gaps for the
  count caveat).

**CRITICAL security finding — CR-01, caught by Phase 169's code review.** An `evidence` field
containing a **JSON-escaped** `\n` (two ASCII bytes, valid JSONL, decoding to a real newline) could
splice a fabricated, fully-`[x] PASS` UAT case into the gating document past **all three guards
simultaneously**: the zero-undispositioned gate saw a PASS, heading/result parity was preserved
(one heading, one result line added), and the fabricated ID was novel. Root cause was
`CANONICAL_RESULT_RE`'s `[^)]*` annotation group — a negated character class matches newlines, and
the pattern carried neither DOTALL nor MULTILINE, so it swallowed an entire injected block while the
line still matched. Reproduced end-to-end: `apply` reported `applied 1 rewrite(s)`, exit 0, and
`find_undispositioned_cases()` returned `[]`. Fixed in two layers (`9580ab09`) — reject CR/LF in
evidence, and narrow the group to `[^)\n]*` so a multi-line render cannot satisfy the grammar even
if layer 1 were bypassed — applied to all three lockstep copies of the regex, with
`tests/test_uat_apply_injection_guard.py` (10 tests, **8 failing against the pre-fix code**).

**Every count the 2026-08-24 review asserted failed re-measurement.** The symptoms held up; the
numbers never did:

| Claimed | Actual | What happened |
|---|---|---|
| 5 duplicate case IDs | **3** | The "5" was a tooling artifact — `grep -o '^### UAT-[0-9]*-[0-9]*'` truncates three-segment IDs, manufacturing phantom duplicates |
| 4 genuinely-missing tests | **2** | GAP-02 and QRAMM-09 already had real coverage the review's search missed; they were annotated, not duplicated |
| 16 stale references | **230** (headline) | Re-measurement went the other direction — see Known Gaps for the reconciliation caveat |
| ~325 unrecorded cases | **377** | 299 in series 1-100, 78 in series 101-163 |
| 291 a11y violations | **81** live pre-fix, **1** post-fix | The committed 291 baseline was stale — "the number RVW-012 restated without re-measuring"; 72% overstated before any remediation |

### Known Gaps

- **Milestone audit scored `gaps_found` with one gap, explicitly accepted by the user and carried to
  v5.17: GATE-03's fork-safety forward-lock is an allowlist, not a sweep.**
  `tests/test_cli_helper_usage.py::_COVERED_FILES` names 11 files; applying the gate's *own*
  criterion across `tests/` finds **18 uncovered files with 38 offending call sites**. The
  docstring claims protection "regardless of which subset of tests is run", which a hand-maintained
  list cannot deliver. Latent and order-dependent — the full unfiltered suite passes with zero fatal
  signals, and all 18 files predate the gate. Recorded in `HORIZON.md`, not ROADMAP Backlog.
- **The "230 stale references" headline does not reconcile with its own component figures.**
  REQUIREMENTS TRACE-05 records 68 broken lines across 25 files; `170-VERIFICATION.md:110` gives
  `68 + 28 + 6 + 174`. ROADMAP, PROJECT.md, and HORIZON.md all state 230. No file derives 230 from
  the components. Treat 230 as the headline the record uses, not as an audited figure.
- **The "3 screen-reader blockers fixed" claim is looser than the phase record.**
  `165-VERIFICATION.md` records 2 of the 3 `button-name` violations as **confirmed phantoms** (stale
  baselines predating existing `aria-label`s); only `ScanSelector.tsx:33` was genuinely unlabelled,
  and it was fixed "on structural/textual merit, not live axe evidence."
- Seven further items carried forward in `HORIZON.md` — deliberately not in ROADMAP's Backlog,
  because archived roadmaps swallow backlog items (`BACK-A11Y-01` was invisible for three months
  that way). Chief among them: **closing the 57 UAT coverage GAPs** (its own milestone-sized effort)
  and **actioning the 18 genuine product FAILs**, which became v5.17.
- **Not tagged.** `pyproject.toml` remains `5.15.0`. Recorded deliberately in `03656097`.

**Test baseline at close:** `pytest -q -m ""` → **3,684 passed, 4 failed, zero fatal signals.** The
4 are `test_skip_registry::test_no_unregistered_skips` plus 3 environmental
`test_extras_install_matrix` failures (a stale `__editable__.quirk-4.0.0.pth` breaks pip's
build-backend locally; CI installs fresh), proven pre-existing by stash-and-reproduce.

---

## v5.15 Lifecycle Tail Drain (Shipped: 2026-08-26)

**Phases completed:** 3 phases (161-163), 11 plans
**Git range:** `23932695` (2026-08-20) → `87ad578e` (2026-08-26), release commit `09b13e32` — 63 commits in range, 7 days
**Requirements:** 4/4 complete — none dropped, none deferred
**Released:** tag `v5.15.0` — **the first published release since 5.12.0**

*(Entry authored retroactively 2026-09-01 from the v5.15 archives; not written at close.)*

**Key accomplishments:**

- **Hardware lifecycle notifications (HWLC-14).** Opt-in email/webhook fan-out when a monitored
  device crosses a CNSA 2.0 tier boundary or an EOL/EOS date, reusing the Phase 101 delivery layer
  with no new channel or credential model. Wired as a never-raising terminal hook *inside*
  `persist_and_reconcile()` so all four call sites fire it — deliberately not per-call-site, because
  a per-site wiring "would be correct today and wrong on the addition of a fifth path."

- **Vendor PQC trends got their first consumer (HWLC-19).** `GET /api/hardware/vendor-trends` had
  shipped in v5.14 Phase 160 with zero consumers. v5.15 gave it a `/hardware` dashboard section plus
  CLI, HTML, and DOCX report sections — advisory-only, with byte-identical captions enforced across
  all three surfaces by test, and scoring isolation enforced by a single
  `_VENDOR_TREND_SURFACE_MODULES` tuple covering six surfaces.

- **Check-in scans on a cadence (HWLC-20).** `quirk schedule add --check-in` put HWLC-13's
  lightweight re-probe on the existing scheduler, with `--target` optional for check-ins.

- **Discovery batch checkpointing (DISC-08) — built, not tightened.** The roadmap assumed a
  per-batch checkpoint layer existed and asked for it to be tightened. Verification against the tree
  found none: `write_scan_checkpoint(..., "discovery", ...)` fired once after the whole loop. The
  phase built the missing layer instead. A /16 interrupted at batch 60 of 64 now re-probes ~4,000
  hosts on resume rather than ~65,000 — with no new table and no schema change.

- **Release integrity closed (RVW-004).** `pyproject.toml` moved 5.12.0 → 5.15.0 with a
  three-component tag. v5.13 and v5.14 had never published because their two-component tags missed
  `release.yml`'s `v*.*.*` glob; that trigger is now `v[0-9]*`. The Windows Authenticode self-test
  succeeded on a real tagged build and `quirk-windows-5.15.0.zip` (58.6 MB) attached — the first
  Windows asset since v5.8.0.

**Latent defect found: SCHED-02, live for ~3 months.** `_dispatch_schedule()` fell back to
`schedule.profile or "balanced"` — a *score* profile value that `run_scan --profile` rejects. Every
CLI-created schedule without an explicit profile died at argparse and was logged "failed" with no
reason. It survived that long because the dispatched argv was reachable only through `Popen`; the
fix extracted a pure `build_scan_argv()` so it could be tested without a subprocess. Fixed
separately in `ac219e4` *before* Phase 162 built on it — the criterion was literally unverifiable
when the phase began.

**The human-UAT gate earned its cost.** Phase 163's blocking checkpoint caught a defect every
automated criterion passed over: a resumed scan reported the correct endpoint count while silently
under-reporting swept coverage (`1014 scanned / 1008 undetermined` versus `4034 / 4029` on a real
/20), moving a client-facing Confidence score from 22 to 19/100. The criterion was right in intent
("zero silently dropped hosts") and wrong in scope ("host/port inventory count"). The report did not
look broken — it looked like a completed smaller engagement. An unplanned plan (163-04) was created
in response, with four RED-verified regression tests.

**Test baseline at close:** `3593 passed, 2 failed` — both `test_verify_phase_gates.py::test_hook_integration_*`,
order-dependent (44 passed in isolation), a macOS subprocess SIGSEGV later root-caused and fixed in
v5.16 Phase 166-05.

### Known Gaps

- Phase 162 was executed inline at the user's direction and left **no PLAN or SUMMARY artifacts** —
  recorded deliberately in `162-VERIFICATION.md`, but the milestone's plan accounting for 162 is a
  placeholder (`1/1`).
- No `v5.15-MILESTONE-AUDIT.md` was produced.
- True sub-batch (intra-batch) discovery resume explicitly deferred.
- Two items promoted into v5.16: duplicate stage rows when resuming an already-complete scan, and
  the blank `--list-resumable` Target column for `--targets-file` runs.
- Vault hygiene failed at close (Phase-162 note absent, `_QUIRK-Hub.md` missing links, `Roadmap.md`
  stale by 12 days) and was only repaired the next day at the v5.16 boundary review.

---

## v5.14 Hardware Lifecycle Tail — Fleet Coverage & Forecasting (Shipped: 2026-08-19)

**Phases completed:** 4 phases, 16 plans, 38 tasks

**Key accomplishments:**

- Table-wide calendar-cutoff retention sweep for `hardware_drift_events`, structurally distinct from the Phase 154 scan-scoped `HardwareDevice` purge, via a new `ScanCfg.hardware_drift_event_retention_days` field (default 365) and `run_scan._purge_stale_drift_events()`.
- Pure `build_eol_forecast()` bucketing + hedged, catalog-cited 12-month EOL narrative engine, with the advisory-only firewall extended by name.
- ExecContent gains an `eol_forecast` field populated non-fatally by writer.py, and html_renderer.py gains a `render_eol_forecast_section()` that renders an escaped, advisory-framed EOL/Tier Forecast subsection independent of drift events.
- All three report formats (HTML from Plan 03, now DOCX and CLI/markdown) render the 12-month EOL/tier forecast narrative, closing ROADMAP success criterion #2 for HWLC-18 — with the CLI subsection built as genuinely net-new prose rather than an extension of a section that was never shipped.
- Closes CLAUDE.md's Per-Phase Documentation Checklist and Mandatory Phase Completion Steps for Phase 157 — documents `hardware_drift_event_retention_days`, expands the EOL/Tier Forecast section with an explicit retention-reconciliation guarantee (ROADMAP success criterion #5), adds UAT Series 157, and re-syncs all four Obsidian vault guide/reference files plus a new phase note.
- Extracted the duplicated hardware persist/purge/commit/reconcile block from two `run_scan.py` call sites into one shared `persist_and_reconcile()` helper in `quirk/scanner/hardware_drift.py`, eliminating a would-be fourth copy for the upcoming sensor-ingest path.
- Sensor-side `hardware_devices` field end-to-end: `PushEnvelope.hardware_devices: list | None = None` on the console model, `_hardware_device_to_dict()`/`_read_scan_hardware_devices()` on the sensor, wired into both the HTTPS push and air-gap export `_build_envelope()` call sites, proven by a 7-test round-trip module.
- Wired `persist_and_reconcile()` into `_ingest_envelope()`'s shared HTTPS-push/air-gap-import path, closing HWLC-15: sensor-scanned segments now reach `hardware_devices`/`hardware_drift_events` identically to console-direct scans, with `None`-vs-`[]` correctly distinguishing "old sensor, no observation" from "new sensor, confirmed zero devices."
- HardwareDevice.is_partial_scan marker column + check_in_fingerprint_devices() dispatch wrapper that re-probes a known device via only its originally-identifying probe family (SSH/SNMP/Modbus/BACnet), never re-running a full port scan.
- `--check-in` CLI flag short-circuits `run_scan.py` immediately after `init_db()` into `run_check_in()`, which re-probes only the known hardware fleet via the Plan-01 dispatch wrapper, persists through the unmodified Phase 158 `persist_and_reconcile()` chokepoint, and exits 0 — never touching discovery, non-hardware scanner phases, or `compute_readiness_score`.
- `HardwareDriftEventItem.is_partial_scan` badge threaded through the shared `build_device_lookup()`/`serialize_drift_event()` helpers so every drift item on `/api/hardware/drift` and `/api/compare` discloses check-in provenance, backed by 5 regression tests proving `/trends` and `/compare`'s score paths stay structurally immune to check-in rows.
- Threaded `is_partial_scan` from persisted `HardwareDevice`/drift rows into the report payload and rendered a locked, always-visible "Partial re-probe — check-in scan; not a full assessment." banner in the HTML, DOCX, and CLI/markdown reports whenever a check-in-sourced device or drift row is displayed.
- Documented the `--check-in` CLI flag (operators-guide §9.9, getting-started cross-reference) and the partial re-probe banner (report-interpretation §10.12) exactly as shipped in Plans 02-04, added UAT Series 159 (4 cases), and synced all four touched docs to the Obsidian vault — closing CLAUDE.md's Per-Phase Documentation Checklist for Phase 159.
- New vendor-scoped `vendor_pqc_trend_events` table + `vendor_fleet_snapshot()` distinct-device fleet window + `reconcile_vendor_pqc_trend()` N-of-M detection function, reusing the existing `_confirmed_value()` gate verbatim.
- Wired `reconcile_vendor_pqc_trend()` into the shared `persist_and_reconcile()` chokepoint so every hardware scan batch (console-direct, sensor-ingested, check-in) participates in vendor-level PQC trend tracking, and extended the machine-enforced advisory-only scoring firewall to cover the new surface by name.
- `GET /api/hardware/vendor-trends` — authenticated, bounded, newest-first vendor-scoped read of `vendor_pqc_trend_events`, extending the existing hardware_drift route module and its T-160-04 scoring firewall, plus operator docs and UAT Series 160, closing out HWLC-17 and Phase 160.

---

## v5.13 Continuous Hardware Lifecycle Monitoring (Shipped: 2026-08-15)

**Phases completed:** 3 phases (154–156), 17 plans, 44 tasks

**Delivered:** Extended v5.10's point-in-time hardware fingerprinting into ongoing lifecycle
tracking. 12/12 HWLC requirements satisfied, milestone audit `passed`.

**Key accomplishments:**

- Stable device re-identification across scans — SSH host-key fingerprint secondary match key
  (unconditional on vendor match) with explicit low-confidence fallback to host:port, surviving
  DHCP/re-IP between engagements.

- Failed-probe-safe hardware state — a genuine per-device latest-successful-row projection at all
  four read sites (dashboard, CBOM merge, CLI/PDF/DOCX reports), so a failing re-probe never erases
  a device's last-known-good data; plus a configurable retention purge (`hardware_history_retention_days`,
  default 180).

- Drift reconciliation engine — two-scan diff across CNSA 2.0 tier, PQC/bridge-mitigation status,
  EOL/EOS proximity, and CVE set, each a distinct N-of-M-confirmed, deduplicated event type
  persisted to `hardware_drift_events`.

- Curated EOL/EOS catalog (`hardware_eol.py`, 4th instance of the staleness-gated curated-catalog
  pattern) finally populating `HardwareDevice.eol_date`, dormant since Phase 127.

- Dashboard + report "what changed since last scan" surfacing — `GET /api/hardware/drift`,
  `CompareResponse.hardware_drift`, `LifecycleEventList` on `/hardware`/`/compare`, HTML/DOCX
  "Recent Lifecycle Changes" sections — structurally distinct from scored findings, zero
  `SCORE_WEIGHTS` references, machine-enforced.

- OT/ICS recurring-rescan safety rail — explicit `enable_recurring_otics` opt-in plus a hardcoded,
  non-configurable 168-hour cadence floor enforced as the sole scheduler dispatch chokepoint;
  `/gsd-secure-phase 156` independently SECURED 19/19 threats, 0 high-severity findings.

---

## v5.12 Release & Verification Integrity (Shipped: 2026-08-14)

**Phases completed:** 6 phases (148–153), 36 plans
**Requirements:** 14/14 (RELEASE-01..04, SUITE-01..03, ARTIFACT-01..04, DISC-09..11)
**Audit:** `passed` — 14/14 requirements, 6/6 phases verified, one real integration gap found and
fixed during the audit itself (`.planning/milestones/v5.12-MILESTONE-AUDIT.md`)
**Version:** 5.11.0 → 5.12.0

**Delivered:** QU.I.R.K.'s own release, test, and verification signals are trustworthy again. The
release pipeline is proven live (not by code inspection), a green test-suite baseline is held by
CI, a phase-completion artifact gate is built, tested, and now actually installed and enforcing,
and the real `v5.12.0` tag was cut and independently verified against live GitHub Actions and
PyPI — including one real, human-approved recovery when the first tag push silently didn't fire
the release pipeline.

**Key accomplishments:**

- **Release pipeline repair + proof (Phase 148)** — a `workflow_dispatch` dry-run mechanism
  exercises `release.yml`'s Windows build without a real tag; a scheduled tag-hygiene guard
  (`scripts/release_tag_hygiene.py`) catches malformed/unpushed tags; the v5.11.0 Windows-asset
  gap is explicitly dispositioned (PyPI-only, documented) rather than backfilled with a
  provenance-questionable post-hoc build.

- **Test suite triage + green baseline (Phases 149–150)** — all ~102 pre-existing full-suite
  failures given an explicit written disposition (fixed/quarantined/deleted); `pytest -q` genuinely
  green, held by a CI gate proven live with both a green run and a deliberate red-smoke run on
  real GitHub Actions.

- **Phase-completion artifact gate (Phase 151)** — `scripts/verify_phase_gates.py` +
  `.githooks/pre-commit` block a phase-close commit missing `VERIFICATION.md`, a stale
  `VALIDATION.md`, or a missing `docs/UAT-SERIES.md` entry, plus a destructive-archive guard
  scoped to `(phase_num, milestone_tag)` — closing the exact incident class that deleted ~39
  v5.11 phase files. A design flaw (the gate would have permanently blocked every future commit
  because of Phase 144's un-backfillable historical gap) was caught before shipping and fixed with
  a narrow, documented exemption.

- **Discovery empirical closure (Phase 152)** — a genuinely routed two-subnet chaos-lab topology
  (iptables REJECT gateway, not loopback aliases) settled the year-old Phase 144 nmap timing-engine
  artifact once and for all: **does not reproduce**, across 3 independent live-fire runs.

- **Real release tag cut (Phase 153)** — `v5.12.0` tagged, pushed, and independently re-verified
  against live GitHub Actions AND PyPI's own JSON API (not just SUMMARY.md prose) — Windows
  operator zip attached, PyPI package published. One real deviation: the initial combined
  branch+tag push silently didn't fire `release.yml`'s push-event trigger (a documented GitHub
  Actions limitation); caught, independently verified, and fixed via a human-approved standalone
  tag re-push.

- **Milestone audit caught the gate testing itself** — Phase 151's own `VALIDATION.md` docs (and
  Phase 153's) were left in their pre-execution draft state post-close, because the pre-commit
  hook they built was never actually *installed* (`core.hooksPath` unset). Fixed during the audit;
  the gate is now live for all future commits — the strongest possible proof it achieved its goal.

## v5.11 Discovery at Scale + Backlog Drain (Shipped: 2026-08-11)

**Phases completed:** 4 phases (144–147), 16 plans, 35 tasks
**Requirements:** 11/11 (DISC-01..07, DRAIN-01..04)
**Audit:** `passed` — 11/11 requirements, 4/4 phases verified, 8/8 cross-phase seams, 3/3 E2E
flows, Nyquist compliant (`.planning/milestones/v5.11-MILESTONE-AUDIT.md`)
**Version:** 5.10.0 → 5.11.0

**Delivered:** Large-range nmap discovery is reachable end-to-end from the dashboard for the
first time — chunked into batches, tolerant of a bad batch, liveness-filtered, progress-visible,
and honest about what it could not determine — while the debt tail accumulated since v5.8/v5.10
was drained to zero.

**Key accomplishments:**

- **Chunked discovery core (Phase 144)** — the anchor fix. Both hard-reject gates that made large
  ranges unreachable were relaxed *in the same phase* as the chunking that replaces them
  (`target_expander.py::_MAX_HOSTS_PER_CIDR` and `jobs.py`'s 422 stopgap), deliberately avoiding a
  repeat of the Phase 141 "feature built, never reachable" bug shape. Discovery became a strictly
  sequential per-batch loop with the `try/except` **inside** the loop, so one unresponsive batch no
  longer aborts the job, plus a `stage="discovery"` ScanCheckpoint matching every other stage.
  Batches derive from a deduplicated flat host list — a multi-port host can never straddle a
  boundary. Live-verified end-to-end twice; failure isolation observed live.

- **Liveness pre-pass (Phase 145)** — each batch now runs a cheap `-sn -PS<ports>` TCP probe before
  its full sweep, skipping dead hosts while still *counting* them, with explicit SYN→connect
  privilege-fallback detection instead of silent degradation. **The D-06 non-root human gate earned
  its place:** the first live run reported `255 responsive, 0 skipped` while nmap's own runstats
  said `2 up, 253 down` — real subnet sweeps emit `<host>` elements only for hosts nmap can
  positively report on, so the down-host exclude set was always empty and the pre-pass was
  filtering nothing in its primary target scenario. Fixed by reconciling against the `<runstats>`
  aggregate, guarded to fail open unless the accounting proves complete.

- **Progress, scaling, parity and disclosure (Phase 146)** — per-batch progress through the
  existing poll loop to a dashboard sub-line; timeout and `-T` timing derived from each batch's own
  size instead of one hardcoded 300s; an AST regression test locking CLI and dashboard to a single
  shared discovery call site; and an undetermined-host count rendered identically across CLI
  markdown, HTML, DOCX and the terminal summary. Code review caught a real correctness defect here
  that the phase's own green tests missed — see Lessons.

- **Backlog drain (Phase 147)** — the `--resume-scan-id` outer-gate bug fixed by hoisting the OT/ICS
  supplemental pass above the ssh-stage branch, so a resumed scan still fingerprints OT-only
  hosts; a curated BACnet vendor-ID + model-family catalog (the fourth instance of the
  staleness-gated catalog pattern) that finally makes the dead "Johnson Controls / Facility
  Explorer" CVE entry reachable; a port-aware default CORS allowlist closing WR-02; and the
  2026-05-27 audit ledger reconciled to zero undecided rows with verified commit citations.

- **Milestone-audit closeout** — the audit surfaced six findings, all closed: Phase 145's missing
  VERIFICATION.md (written, passed 4/4), WR-02's undisposed per-batch SQLAlchemy engine (fixed
  TDD-style), Phase 147's stale `nyquist_compliant: false`, a missing `requirements-completed`
  frontmatter line, an audit self-correction on WR-01, and a STATE.md rationale resting on facts
  that had decayed. UAT Series 144 was also backfilled — the anchor phase had shipped without one.

**Lessons:**

- **Green tests over a false assumption.** `_compute_undetermined_hosts()` originally filtered on
  the generic `"exception"` category that `_wrapped_phase()` emits at 20+ scanner call sites, so a
  TLS-scanner crash on a reachable host would have been reported as "unreachable/filtered" in a
  client deliverable. The phase's own regression test passed because it asserted the wrong
  exclusion case. Caught by code review, not by CI; fixed with a dedicated `discovery_exception`
  category.

- **Human-verify gates keep paying.** Both Phase 145 and Phase 146 had their human UAT surface a
  real defect that automated verification had cleared.

- **Dispositions decay.** A deferred item can be correctly *concluded* while its stated evidence
  goes stale — and reviewers check verdicts, not reasoning. UAT-143-03's blocker turned out to be
  structural (no `v*.*.*` release tag since v5.9) rather than the claimed absence of pushes.

**Known deferred at close:** 5 tech-debt items, none blocking — the Phase 144 nmap timing-engine
artifact (needs a real routed segment; best paired with DISC-09), ~102 pre-existing unrelated
suite failures, IN-01's batch-column reset coupling (accepted by design), and DISC-08/DISC-09
deferred by explicit scope decision. One `audit-open` quick-task row
(`260611-g0b-merge-healthcare-vertical`) reports `[missing]` but is a false positive — both PLAN
and SUMMARY exist and merge commit `9967d8a` is in history. See STATE.md Deferred Items.

---

## v5.10 Hardware Lifecycle Depth (Shipped: 2026-08-03)

**Phases completed:** 5 phases, 36 plans, 76 tasks

**Key accomplishments:**

- **SNMPv3 auth+priv fingerprinting (Phase 139)** — per-host `SnmpV3Credential` config (env-var
  secrets, SHA/AES-only allowlist), a real v3 USM probe path with a v3→v2c→none fallback ladder
  wired into both SNMP entry points, zero credential leakage (`safe_str` scrubbing on every
  exception path), and a doubled v3 timeout budget empirically validated against a live chaos-lab
  target — including two real defects (a pysnmp missing-argument bug, a container double-bind)
  caught only by the live end-to-end check.

- **SNMP-confirmed bridge mitigation (Phase 140)** — a sensor-side ARP-table walk persists raw
  evidence; a pure in-memory, zero-network-I/O promotion function upgrades `partial_only` to
  `upstream_mitigated` only when the paired gateway's real ARP table proves the legacy backend
  sits behind it. Distinct amber/blue badges + mandatory caveat across HTML/PDF/DOCX/dashboard;
  never enters `SCORE_WEIGHTS`.

- **OT/ICS fingerprinting — Modbus/TCP + BACnet/IP (Phase 141)** — read-only, circuit-breakered
  probes for both protocols, a new `otics` chaos-lab profile with two fragility-simulating
  containers, and CBOM/dashboard wiring for both. Required two gap-closure rounds after the
  initial ship: 141-08 fixed an unsatisfiable inner gate condition, and a live test then revealed
  a deeper outer bug — `fingerprint_hardware()` was only reachable when at least one SSH-classified
  endpoint existed, silently skipping OT/ICS-only devices entirely. 141-11 fixed the outer gate;
  both fixes were then live re-validated together against the real chaos-lab containers with zero
  SSH endpoints present, confirming Modbus and BACnet now activate end-to-end for real OT/ICS-only
  devices, not just multi-service hosts.

- **Firmware CVE correlation (Phase 142)** — a curated, staleness-gated CVE table correlated
  against fingerprinted vendor/model/firmware, surfaced as an advisory badge (never scored),
  fail-closed on ambiguous firmware strings, with a dedicated `quirk cve status` CLI and CI
  staleness gate.

- **Dashboard & security tail (Phase 143)** — a persistent scan-date sidebar badge, a
  server-enforced trusted-targets scan-consent allowlist (both CLI and dashboard entry points),
  and Windows Authenticode signing CI (secret-gated no-op + ephemeral self-test, since no
  production cert exists yet). The allowlist and signing-CI changes each passed a dedicated
  `/gsd-secure-phase` review (SECURED, 0 threats open).

---

## v5.9 Documentation Audit & Living Docs System (Shipped: 2026-07-30)

**Phases completed:** 6 phases (135–138 + gap-closure phases 138.1, 138.2), 10 plans. Audit: tech_debt disposition — 16/16 requirements satisfied, integration clean, 0 blockers. Timeline 2026-06-18 → 2026-07-30. Docs-only milestone; no version bump (software remains v5.8.0).

**Key accomplishments:**

- **Core docs refresh (Phase 135):** README updated to v5.8.0 with hardware fingerprinting/CNSA 2.0/CBOM DEVICE-FIRMWARE bullets and a What's New v5.6–v5.8 section; CHANGELOG gets the missing [5.7.0] and [5.8.0] entries; `docs/getting-started.md` gains an Optional Hardware Scanning `[hw]` section; `docs/architecture.md` gains §12 Hardware Scanning (SSH/HTTP/SNMP signal chain, CNSA 2.0 tiers, CBOM hierarchy) plus a mermaid flowchart update.
- **Operators guide expansion (Phase 136):** `docs/operators-guide.md` §9 Hardware Scanning (SNMP enable, CNSA 2.0 tiers, crypto-bridge) — every config default and tier severity value cross-checked verbatim against `hardware_tier.py`/`scan.py` source constants.
- **Report interpretation + admin guide (Phase 137):** `docs/report-interpretation.md` §10 Hardware Inventory (DEVICE/FIRMWARE hierarchy, advisory-only score relationship); brand-new `docs/admin-guide.md` covering console deployment, sensor enrollment, auth lifecycle, and SNMP setup — closing the admin-facing documentation gap the v5.4+ distributed architecture had left open.
- **Chaos lab docs + living docs system (Phase 138):** `docs/chaos-lab.md` §3.22 documents the hwcompat SNMP profile (all three services, `[hw]` prerequisite, port table); `CLAUDE.md` gains a permanent Per-Phase Documentation Checklist and Milestone-Boundary Doc Review Template — structural enforcement, not a one-time sweep.
- **Self-proving governance (gap closures 138.1, 138.2):** the milestone's own audit caught two real defects the phases had shipped — CORE-04 (architecture.md §12 CNSA 2.0 tier severity was inverted relative to the shipping code and operators-guide.md) and LIVE-03 (2 Obsidian vault guides gone stale). Both closed by inserted phases, re-verified independently by a follow-up re-audit, and both gap-closure phases correctly followed the new CLAUDE.md checklist (UAT-SERIES.md updates, vault re-sync) — proof the governance machinery works in practice, not just on paper.

**Known deferred items at close:** 4 (see STATE.md Deferred Items) — 3 verification_gap entries (human-UAT prose/visual reviews on Phases 132/135/137, none content gaps) and 1 stale quick-task tracking entry (healthcare vertical branch merge, already completed 2026-06-11).

---

## v5.8 Audit Closeout + SNMP Fingerprinting (Shipped: 2026-06-18)

**Phases completed:** 5 phases (130–134), 21 plans. Audit: 22/22 requirements satisfied, 0 blockers (B-01 closed before tag). Timeline 2026-06-14 → 2026-06-18 (4 days), 73 commits, +5,913/−333 lines. Tag `v5.8.0`.

**Key accomplishments:**

- **Wave A audit drain (Phases 130–132):** Closed all 15 deferred audit rows — codesign column rename (AUDIT-01), REST fuzzer per-scan dedup (AUDIT-02), Kerberos TCP→UDP RFC comment (AUDIT-03), DOCX exception logging (AUDIT-04), SOURCE algo-hint granularity for RSA/AES variants (AUDIT-05), rate-limit idle eviction (AUDIT-06), job target 422 validation (AUDIT-07), sensor-push re-validation (AUDIT-08), SSRF TOCTOU accepted-risk doc (AUDIT-09), sensor CLI UUID guard (AUDIT-10), SIEM SSRF guard (AUDIT-11), console enroll single-session race (AUDIT-12), CEF space escaping (AUDIT-13), auth token localStorage → sessionStorage + CSP header (AUDIT-14), HTML cover-page layout fix (AUDIT-15).
- **SNMP hardware fingerprinting (Phase 133):** Opt-in `[hw]` extras (`pysnmp>=7.1.0,<8` + `sysdescrparser>=0.0.8`); 3-OID probe (sysDescr/sysName/sysObjectID) via pysnmp 7 sync HLAPI; dual-path vendor parsing (sysdescrparser primary, SNMP_VENDOR_MATRIX regex fallback); 4 new nullable HardwareDevice ORM columns with additive migration; Cisco IOS Net-SNMP chaos lab container (alpine, port 20223/udp); CBOM Pass 4 `quirk:hw-snmp-oid` conditional property; staleness gate extended to cover `snmp_meta.py`.
- **CBOM DEVICE/FIRMWARE hierarchy (Phase 134):** `HardwareComponent` Pydantic schema + `_derive_hw_components()` on `/api/scan/latest`; dashboard CBOM tab `HardwareInventory` two-row table (DEVICE row + FIRMWARE detail row) with distinct Badge labels; omitted when no hardware devices present.
- **B-01 distributed path fix (post-audit):** `merge/scan.py` `hw_devices_for_cbom` dict now projects all 4 SNMP fields via `getattr`; `quirk:hw-snmp-oid` now emitted on the distributed/merge path (was silently absent). Commit `6eb512e`.

**Known deferred items at close:** Nyquist VALIDATION.md files for all 5 phases; human Docker SNMP lab verification; HardwareInventory FIRMWARE row distinct data (W-01, intentional per D-02); SNMPv3/OT-ICS/firmware-CVE in v5.9 backlog.

---

## v5.7 Hardening + Hardware Compatibility & Lifecycle Remediation (Shipped: 2026-06-14)

**Phases completed:** 7 phases (123–129), 24 plans. Audit: 24/24 requirements satisfied, 0 blockers, integration clean. Timeline 2026-06-13 → 2026-06-14 (2 days), 50 commits, +3,864/−139 lines. Tag `v5.7.0`.

**Key accomplishments:**

- **SSRF & URL-allowlist hardening (Phase 123):** Five SSRF audit rows closed — REST fuzzer raw-socket bypass fixed via `PinnedIPAdapter` at 3 dispatch sites; GCP metadata aliases added to always-blocked set; path-shaped image refs rejected before syft; console self-SSRF block inserted before `allow_internal` short-circuit; DNS-rebinding mitigated via `resolved_ip` pinning. 154 regression tests GREEN.
- **Scoring & evidence correctness (Phase 124):** Five correctness bugs fixed — severity KeyError replaced with LOW fallback; QRAMM partial-answer inflation resolved (0.0 injected for unanswered practices); EdDSA now credits ECDSA agility bucket; AES-CCM_8 classified as distinct truncated-tag AEAD; cross-tenant evidence contamination resolved via `session_created_at` temporal anchor (zero schema migration).
- **Posture defaults + distributed edges (Phase 125):** GCP/AWS connectors surface HttpError 403/AccessDenied as `scan_error` findings; same-second merge tiebreak fixed with `MAX(id)` secondary key; notify fan-out isolated from `run.scan_id` commit failures.
- **Audit ledger closeout + Dashboard Quality (Phase 126):** All 7 criticals remain closed; 29 warning rows explicitly dispositioned; FE-01/03/04 frontend bugs fixed; Dashboard Quality CI green.
- **Hardware fingerprinting foundation (Phase 127):** Agentless SSH-banner + HTTP-mgmt fingerprinting via 8-vendor `HARDWARE_MATRIX` with 90-day CI staleness gate; `HardwareDevice` ORM wired into `run_scan.py`; `hwcompat` chaos lab profile with oracle.
- **Remediation tiers + report surfacing (Phase 128):** CNSA 2.0 `assign_tier()` pure function (Tier 1/2/3/N/A + confidence cap); advisory surfacing in HTML collapsible, executive narrative, DOCX table, and `/hardware` dashboard tab. Advisory-only — zero `SCORE_WEIGHTS` references.
- **Crypto-bridge detection + CBOM Pass 4 (Phase 129):** /24 subnet heuristic detects PQC-gateway + legacy-backend pairs; CBOM Pass 4 emits `ComponentType.FIRMWARE` with `quirk:hw-*` properties; `HARDWARE` in Pass 2/3 skip-lists; CycloneDX 1.6 schema validates with FIRMWARE components.

**Known deferred items at close:** PinnedIPAdapter SNI (low-impact urllib3 limitation); 13 deferred-to-v5.8 audit rows with rationale; UAT-118-01 live Windows walkthrough; UI-01 cover-page gap (report polish).

---

## v5.6 Distributed Completion + Public Launch (Shipped: 2026-06-12)

**Phases completed:** 6 phases (117–122), 20 plans, 36 tasks. Audit: 21/21 requirements satisfied, 0 blockers, 6/6 integration seams WIRED (status `tech_debt` — debt accepted and ledgered). Timeline 2026-05-27 → 2026-06-12 (16 days), 119 commits, +8,639/−526 lines (post-history-rewrite numbering). Tag `v5.6.0` pushed @ `4981340`.

**Key accomplishments:**

- **Production Windows frozen sensor (Phase 117):** `--onedir` PyInstaller build + runtime smoke on `windows-latest`, no `continue-on-error` — live CI green (run 26543032560). Three Windows-only defects fixed that the v5.5 spike missed (repo trailing-dot rename, missing `.lark` data file, cp1252 UnicodeEncodeError).
- **Windows operator packaging + release (Phase 118):** zip + PowerShell Scheduled-Task installer (install.ps1/uninstall.ps1), frozen-sensor E2E enroll→push under per-sensor Bearer auth on CI, and `quirk-windows-5.6.0.zip` published as a GitHub Release asset (release run 27432669479).
- **Public launch (Phases 119–120):** full-history gitleaks sweep (2,986 commits, 0 live credentials), 3-pass git-filter-repo history rewrite (12 paths stripped, 989→901 files), repo flipped PUBLIC, branch protection on main with required "Windows Sensor Smoke" check (display-name match fix 579f6bf).
- **SSRF guard hardening (Phase 120):** `validate_external_url` rebuilt fail-closed with AF_UNSPEC + IPv6 blocklist; `allow_internal_targets` removed from the client API (server policy only); all 30 GitHub Actions `uses:` SHA-pinned; chaos-lab keys regenerate on demand.
- **Port-scope discovery control (Phase 121):** four scan scopes (Common TLS / Top-1000 default / All / Custom) wired GUI→API→job-config→nmap with strict port-spec validation, plus an explicit zero-result completion signal. Human UAT 3/3 PASS against the live chaos lab.
- **Tech-debt closeout + ship (Phase 122):** 11 bounded 2026-05-27 audit findings fixed (confidence-bonus gate, AKS advisory, ARN-safe redaction, SHA-1 reason, safe-mode baseline, int-cast, score clamp, production compliance-staleness gate, DEL/C1 stripping, score-key fix); version 5.6.0 across 6 parity surfaces; CHANGELOG + release notes + archive pair; v5.6.0 tag on green required CI.

**Known deferred items at close:** 6 acknowledged (see STATE.md Deferred Items) — headline: 18 audit rows deferred → v5.7 (SSRF/scoring cluster), Dashboard Quality red on main (pre-existing, non-required), UAT-118-01 live Windows-host walkthrough, 119/120 doc backfill.

---

## v5.5 Distributed Hardening + Stabilization (Shipped: 2026-05-27)

**Phases completed:** 4 phases (113–116), 11 plans, 26 tasks. Audit: 13/13 requirements satisfied, 0 blockers, integration 12/12 + 3/3 E2E flows clean.

**Key accomplishments:**

- **Per-sensor authentication (Phase 113):** opaque per-sensor Bearer tokens (SHA-256 hash, `hmac.compare_digest`) replacing the v5.4 shared token; `revoke-sensor` CLI + `revoked_at` additive migration; two-router split keeps operator routes on `require_auth`. Security audit: threats_open 0 (10 mitigate + 3 accept).
- **Automatic merge trigger (Phase 114):** console auto-merges once every non-revoked enrolled sensor has checked in, via a FastAPI BackgroundTask scheduled after the push commit (structural failure isolation); config toggle + two trigger conditions (`all-sensors-in`, `cadence-window`); manual `quirk sensor merge` regression-free. Code review caught + fixed an inverted revoked-sensor filter (CR-01).
- **Live-UAT stabilization (Phase 115):** idempotent enroll (lab re-runnable without `down -v`), `cmvp_cache.json` shipped via importlib.resources, scheduler no longer passes unsupported `--target`/`--output` to run_scan (target preserved via a generated config), phantom `email/broker_scanner` rows eliminated at the read/export boundary.
- **Distributed lab testability (LAB-01):** weak-TLS `tls-weak-b` target on segment-b so the Phase 111 per-segment filter is exercisable end-to-end; lab.sh/oracle/README updated together (no-drift).
- **Windows packaging spike (Phase 116):** evidence-backed PyInstaller feasibility assessment + non-blocking `windows-packaging-spike` CI job (onefile build of run_scan.py) → **GO (conditional on live CI build)**, Scheduled Task host model, ~4–5 day v5.6 estimate. No artifact ships.

**Known deferred items at close:** 2 human-UAT (UAT-114-03 doc review, UAT-116-02 live windows-latest CI build) + cosmetic empty SUMMARY frontmatter — see STATE.md Deferred Items.

---

## v5.4 Distributed On-Prem Scanner Architecture (Shipped: 2026-05-26)

**Phases completed:** 7 phases (106–112), 20 plans
**Delivered:** QU.I.R.K. now scans a segmented enterprise network segment-by-segment — lightweight sensors scan locally and push results *outbound* to a single-tenant console that merges them into one authoritative CBOM + one quantum-readiness score, with no inbound access to any segment required. Milestone audit PASSED (0 blockers, 7/7 phases verified, 33/33 requirements delivered, cross-phase E2E chain wired). Single-tenant, additive-schema-only, OS-agnostic wire contract, reusing v5.3 security primitives throughout.

**Key accomplishments:**

- **Phase 106 (ANCHOR, no-code) — Architecture lock.** A single `docs/architecture-distributed.md` locks every expensive-to-change decision before code shipped: the sensor→console wire payload (`payload_id`/`pushed_at`/`received_at`/`schema_version`/`sensor_version`), `(sensor_id, host, port)` data-model keying with NULL=implicit-local, **Option A** unified scoring (union re-scored through the existing engine, never averaged), one-time-use enrollment tokens, the Windows floor-vs-ceiling split, and an explicit forbidden-additions list (no Celery/Redis/MQTT/Postgres/per-sensor-JWT/mTLS/tenant_id).
- **Phase 107 — Additive data model.** `CryptoEndpoint` gained nullable indexed `sensor_id` + `segment`; new `sensors` / `sensor_tokens` (SHA-256 hashes) / `sensor_pushes` (payload_id dedup) tables — all via the existing `_ADDITIVE_MIGRATIONS` path. A pre-v5.4 SQLite fixture migrates with no data loss and scores identically.
- **Phase 108 — Sensor CLI + Windows CI.** `quirk sensor enroll/push/export-results` (atomic `sensor.yaml`, `tenacity` retry, hardcoded `verify=True` + grep gate, bounded store-and-forward spool, byte-identical air-gap `.qpush`); `_NoRedirectHandler` extracted to `quirk/util/no_redirect.py` (STAB-02); POSIX-ism audit + `platformdirs`; a hard-gated `windows-latest` CI smoke job (no `continue-on-error`).
- **Phase 109 — Console ingestion.** `POST /api/sensor/push` on the existing FastAPI app with router-level `require_auth` (401 anti-bypass gating test), the full failure ladder (413/422+`console_utc`/409 dedup), an `IntegrationDelivery` audit row per attempt with `safe_str` scrubbing + AST gate, `extra='ignore'` version-skew tolerance, and `quirk console enroll` provisioning. One shared `_ingest_envelope` path for HTTPS push + air-gap import.
- **Phase 110 — Cross-sensor merge.** `quirk sensor merge` → one canonical CBOM + one score via Option-A union scoring; `coverage_warning` for overdue sensors (`2×cadence`); CBOM component identity threaded with `sensor_id` at four `bom_ref` sites so the same `host:port` in two segments yields two components; `merge_runs` persistence with per-endpoint `scanned_at` preserved (no rewrite).
- **Phase 111 — Console dashboard awareness.** Sensor registry page (green/stale/unknown badges), a shared per-segment filter, per-segment score gauges alongside the org-wide gauge, and a `coverage_warning` banner — backed by `GET /api/sensor/registry` + `GET /api/merge/latest` (per-segment recompute on read) + a NULL-safe `?segment=` filter.
- **Phase 112 — Distributed chaos-lab + stabilization.** A multi-segment `docker-compose.distributed.yml` (two isolated networks, `crypto.internal` hostname-alias reproducing the same-`host:port`-across-segments scenario after the Docker same-subnet constraint was discovered), `lab.sh distributed` arm + oracle + README (CLAUDE.md no-drift), operators-guide §8 (distributed workflow + Windows install + settings gap closed), and dependency/`datetime.utcnow()` hygiene.
- **Hardening via layered review gates.** Code review caught bugs that passed unit tests + verification across every phase: a zstd decompression bomb + path traversal + missing air-gap HMAC framing (108); audit-on-rolled-back-session + `UnknownSensorError`→404 (109); a *discarded CBOM artifact* and a cross-sensor dedup collision (110); an empty-`?segment=` 404 trap + a non-functional CBOM segment filter (111); and three lab showstoppers including an **SSRF allowlist that blocked the internal on-prem console** — a real product bug fixed via opt-in `--allow-internal-console` (112). The milestone-audit integration check then surfaced and fixed the `sensor_version` registry-display gap and reconciled the shared-token auth model (TD-1).

**Deferred (human-UAT, live infrastructure):** live enroll/spool round-trip (108), live merge + two-component CBOM inspection (110), dashboard visual fidelity vs UI-SPEC (111), the live multi-container `enroll→push→merge` E2E + MERGE-03 physical reproduction (112), GitHub branch-protection for the windows-smoke gate.

**Carry-forward to v5.5:** per-sensor token authentication + revocation (TD-1), automatic merge-trigger / poll-on-full-check-in (106 D-06), full Windows packaging ceiling — PyInstaller EXE + Scheduled Task (106 D-05).

Local tag `v5.4.0`.

## v5.3 Adoption & Integration Surface (Shipped: 2026-05-25)

**Phases completed:** 5 phases (101–105), 20 plans, 50 tasks
**Delivered:** QU.I.R.K. became load-bearing in others' workflows — scheduled-scan drift events now fan out to Slack/email/webhook, findings push to any SIEM as CEF, and per-finding tickets auto-open in both Jira and ServiceNow with idempotent dedup — all on one shared, SSRF-safe, secret-scrubbing delivery layer. Audit PASSED (21/21 requirements, 18/18 integration, 3/3 E2E flows).

**Key accomplishments:**

- **Phase 101 (ANCHOR) — Notification fan-out + the 7 integration-security primitives.** Scheduled-scan drift now delivers to Slack/email/webhook via a shared `DriftSummary` content model + per-channel fan-out, with the conservative trigger (new HIGH/CRITICAL OR score regression beyond −5, never on first scan). Shipped the primitives every later phase inherits: the `integration_deliveries` audit table, `safe_str` secret-scrubbing patterns, delivery-time SSRF (`validate_external_url`), the outbound-field whitelist, and the optional-extra lazy-import discipline. Delivery failures never touch the committed scan record.
- **Phase 102 — Dashboard auth UX + score-tax.** `quirk token` CLI (generate/rotate/show, atomic YAML round-trip); `require_auth` extended to accept `X-API-Key` (timing-safe) alongside bearer, with a CI route-coverage gate guarding every data route; a React login form with localStorage token + mid-session 401→logout. TRANS-04 repointed the CLI executive score to the shared `exec_content` — which surfaced and fixed a real cross-surface bug (CLI had shown 91/EXCELLENT vs the canonical 42/FAIR).
- **Phase 103 — SIEM export.** `quirk export --siem` pushes one CEF event per finding over stdlib syslog (UDP/TCP), vendor-neutral (Splunk/Elastic/QRadar), zero new pip deps; an explicit `to_cef_finding` whitelist keeps cert PEM / PKI topology out of the payload.
- **Phase 104 — Jira ticketing + the shared `TicketingChannel` abstraction.** Per-finding Jira issues carry QRAMM evidence; `SHA256(host:port::title)` fingerprint stored as a label, JQL-searched before create so re-scans add a rediscovery comment instead of duplicates. `jira` lives behind a lazy `[tickets]` extra (joined `[all]` + CI guard).
- **Phase 105 — ServiceNow ticketing as a pure second backend.** `quirk ticket create --backend servicenow` creates incidents via the stdlib `urllib` Table API (correlation_id dedup → work_notes rediscovery), proving TICKET-04: a second backend dropped in with **zero changes to `base.py` or `jira.py`** (git-verified).
- **Hardening via layered review gates.** Code review caught and fixed bugs that passed unit tests: an SSRF redirect-bypass (webhook urllib following 302→cloud-metadata), CEF header newline log-forgery + missing TCP framing, and JQL/URL-path injection via config-controlled `project_key`/`table`.

**Known deferred items at close:** 19 live-delivery human-UAT scenarios across 5 phases (Slack/email/webhook/syslog/Jira/ServiceNow against real servers — network sends are unit-tested with mocked transports), tracked in per-phase `*-HUMAN-UAT.md`. 1 LOW tech-debt item (extract the duplicated `_NoRedirectHandler` to a shared util). See STATE.md Deferred Items.

---

## v5.2 Consulting-Grade Reporting (Shipped: 2026-05-24)

**Phases completed:** 4 phases (97–100), 12 plans, 24 tasks
**Stats:** 109 commits, ~5,000 source LOC across 34 files (Python/Jinja2/TOML), 2026-05-23 → 2026-05-24

**Delivered:** QU.I.R.K.'s report is now a consulting-grade deliverable. From a single scan and ONE shared content model, a consultant gets a CISO-readable executive narrative with transparent scoring, a finding list that reads like an advisory document, a branded client-ready PDF, and an editable DOCX — the same story across every surface.

**Key accomplishments:**

- **v5.1 tech-debt cleanup (97):** corrected the `from_cli` env-var docstring and added the accepted str-copy proliferation comments (docstring/comment only, zero behavior change); REST-fuzzer combined failure-cascade counter so connection exceptions also count toward `_CONSECUTIVE_5XX_LIMIT` (timeout-only servers can't escape back-off); jwt_scanner query-param guard + fail-closed scheduler auth-reject; real-path credential-leakage sentinel test routed through the actual TLS scanner exception handler.
- **Executive narrative + score transparency (98):** shared `ExecContent` dataclass + `ALGO_IMPACT_MAP`/`EFFORT_IMPACT_MAP` static maps; a readiness narrative, top business risks, and effort/impact remediation roadmap wired across CLI + HTML; full subscore decomposition with the ÷1.5 rollup explanation; a `_check_congruence` guard that blocks a GOOD/EXCELLENT band from coexisting with CRITICAL findings (exits before any report is written); belt-and-suspenders cross-surface parity test (EXEC-04).
- **Per-finding context + code-signing expiry (99):** `ALGO_IMPACT_MAP` extended to a 3-tuple + new `REMEDIATION_CATALOG`, making `_build_finding` inject a plain-language quantum-risk "so what" and weakness-specific remediation on every finding (catalog-wins over generic NIST boilerplate); `_classify_codesign_severity` gained an independent expiry branch (expired→HIGH, ≤90d→MEDIUM); `evaluate_codesign_endpoints` turns CODE_SIGNING endpoints into first-class report findings for the first time, wired into run_scan.py; Quantum Risk surfaced across CLI/HTML/PDF with `| sanitize` discipline.
- **Professional & editable report delivery (100):** branded PDF cover page with a configurable base64-embedded logo (graceful omit) + print CSS (`@media print`, fixed table-layout, no mid-row splits, repeating headers); new `render_docx_report` auto-emitting an editable Word document (cover/exec/findings/roadmap/score, Heading 1/2, native tables, logo placeholder) on every run, derived from the same `exec_content` pipeline, gated behind a `[docx]` optional extra with graceful skip.

**Audit:** PASSED — 13/13 requirements satisfied (EXEC/TRANS/CTX/FMT), 4/4 phases verified, cross-phase integration intact (one shared content model → CLI + HTML + PDF + DOCX), E2E consultant flow complete, 0 blockers.

**Quality gates of note:** code review caught + fixed real robustness gaps the happy-path verifier missed — Phase 100's unbounded logo read + narrow except (could abort a scan) and unguarded `doc.save` (could abort CBOM generation), both now honoring their graceful-degradation contracts. Human UAT caught a PDF/DOCX findings-table header-wrap defect (FMT-02), fixed via HTML `white-space:nowrap`/widened columns and DOCX landscape orientation + pinned column widths.

**Known deferred items at close:** 1 acknowledged audit false-positive (Phase 98 HUMAN-UAT shows as "open" in audit-open because the parser keys on walkthrough checkboxes, not the `**Result:**` line — it is `status: passed`, 0 pending scenarios). 1 non-blocking tech-debt item carried to backlog: CLI executive markdown re-derives the score locally instead of sourcing `exec_content` (de-facto identical / deterministic; thread from `exec_content` + add a score-number parity test in a future milestone).

---

## v5.1 Authenticated Scanning + API Surface Depth (Shipped: 2026-05-23)

**Phases completed:** 4 phases (93–96), 16 plans

**Delivered:** An optional, ephemeral credential model that unlocks deeper crypto findings across the API surface — without QU.I.R.K. ever becoming a secret store. Credentials are in-memory-only and never persisted; the milestone's sharpest edge (active fuzzing) ships off-by-default behind a defensive gate.

**Key accomplishments:**

- **Credential infrastructure (93):** ephemeral `CredentialContext` (bytearray-backed, BaseException-safe zeroization) supporting Bearer/OAuth2 + API-key (header/query) + HTTP Basic via CLI flag/env/prompt; a committed 11-surface security-review gate; `safe_str` scrubbing extended to credential shapes with an AST CI gate; `QRK-SCHED-AUTH-001` hard-rejects authenticated scheduled scans. Code review caught + fixed 4 leakage/SSRF BLOCKERs (query-param log redaction, scan-error log scrub, JWKS-probe SSRF, DB error-message scrub).
- **OpenAPI & bearer-token analysis (94):** `analyze-token` JWT classifier (alg:none / missing-alg → CRITICAL); OpenAPI spec scanner hardened against `$ref` SSRF (pre-validate raw-ref reject — subclassing the resolver is insufficient), 10 MB pre-parse DoS gate, and scope-gated URL fetch; CBOM bearer classification `declared_algorithm (unverified)` wired end-to-end through the authenticated scan path (TOKEN-02 gap closed).
- **Code-signing certificate inventory (95):** LDAP `userCertificate` (CodeSigning EKU) + in-process TLS-EKU discovery; RSA<2048 / EC<256 / SHA-1 → HIGH `CODE-SIGN/weak-algorithm`; SHA-256-fingerprint + surrogate-key cross-source CBOM dedup (TLS-derived component wins). Code review caught + fixed a production-dead dedup (scanner wasn't populating the surrogate-key ORM columns).
- **Active REST fuzzing (96):** schemathesis-driven crypto-posture probes (TLS downgrade, cipher, HSTS, HTTP-only cred) + RS256→HS256 alg-confusion (stdlib-hmac forge); literal `CONFIRM` gate, hard non-TTY abort, six guardrails, and an unbypassable budget ceiling (default 50 / hard max 500) now bounding ALL traffic (two budget-bypass BLOCKERs — uncounted alg-confusion + per-iteration socket probes — found and fixed). New `fuzz-target` chaos profile.
- **Packaging + scoring:** `[api]` extras group (openapi-spec-validator + schemathesis) excluded from `[all]` with a CI guard; `SCORE_WEIGHTS` walked 283.0/37 → 293.0 → 299.0 → **303.0 / 41** via the existing `agility_signals` subscore (no 7th pillar).

**Audit:** PASSED — 21/21 requirements satisfied, 21/21 cross-phase integration seams wired, 5/5 E2E flows complete, 0 blockers (1 cosmetic OPENAPI-CBOM finding resolved inline).

**Known deferred items at close:** 6 human-UAT (environment/TTY-gated, non-blocking) — getpass TTY prompt + live PDF export (93); live ldaps code-signing scan (95); TTY CONFIRM gate + non-TTY abort + live alg-confusion vs fuzz-target container (96). Minor design-judgment tech-debt tracked for v5.2 (see v5.1-MILESTONE-AUDIT.md).

---

## v5.0 Stabilization + Tech Debt Sweep (Shipped: 2026-05-22)

**Phases completed:** 6 phases (87–92), 16 plans

**Delivered:** A deliberate stabilization cycle after four heavy capability milestones — dependency hygiene, scoring correctness/transparency, chaos-lab coverage, a demoable post-quantum scoring ceiling, dead-code cleanup, and the v5.0.0 release. No new capability surface.

**Key accomplishments:**

- **Dependency hygiene (87):** Node 20→24 CI bump ahead of GitHub's 2026-06-16 default-switch deadline; `defusedxml` replaced by a hardened lxml `make_safe_parser()` factory (XXE/billion-laughs safe) across `nmap_parser.py` + `saml_scanner.py`.
- **Scoring correctness + transparency (88):** single canonical scoring engine confirmed; six subscores surfaced against their /25 budget with the ÷1.5 rollup across CLI/HTML/PDF; orthogonal-subscore contract locked; five previously zero-algo CBOM profiles now emit real components or affirmative `quirk:coverage-note` markers (closes Phase 42 OBS-1).
- **Chaos-lab expansion (89):** five new weak-TLS lab profiles (postgres-tls, redis-tls, kafka-tls, grpc-tls; smtp covered by the existing email profile); identity evidence (DNSSEC=2, SAML=2) verified end-to-end into the identity subscore, surfacing + fixing a latent Logger-API crash.
- **Post-quantum scoring ceiling (90):** digest-pinned OQS-nginx `X25519MLKEM768` hybrid lab profile + a raw-`openssl s_client` PQC probe (outside the sslyze path) feeding a genuine quantum-safe CBOM component and an `agility` bonus — the milestone's one demoable capability anchor.
- **Code cleanup + bookkeeping (91):** Tier-A then vulture-confirmed Tier-B dead-code removal; a permanent `conftest.py` DB-isolation fix eliminating the recurring 7-module "Multiple QU.I.R.K. DBs" collection error; JWT `verify=False` inspection-mode advisory documented in code + operator docs.
- **v5.0.0 release (92):** version bumped to 5.0.0 (single-source pyproject), towncrier CHANGELOG + `docs/release-notes/5.0.0.md` built, UAT-SERIES + Obsidian synced, local `v5.0.0` tag created.

**Audit:** PASSED — 21/21 requirements satisfied, 4/4 cross-phase integration seams verified, 0 blockers.

**Known deferred items at close:** 4 human-UAT (non-blocking, environment-gated) — 88's three rendered-report visual checks (CLI/HTML/PDF Score Decomposition tables) + 89's kerberos `identity_weak_etype_count` (needs impacket + live KDC; macOS port-88 caveat). See STATE.md Deferred Items.

---

## v4.10.1 Scoring Correctness Hotfix (Shipped: 2026-05-22)

**Phases completed:** 1 phase, 3 plans, 6 tasks

**Delivered:** Fixed the marquee overall-readiness score that always displayed `100 / EXCELLENT` regardless of posture — a triple-layer bug spanning backend aggregation and frontend gauge math, fixed atomically as a single-phase vertical MVP slice.

**Key accomplishments:**

- Backend aggregator at `quirk/intelligence/scoring.py` rewritten: `_clamp(sum, 0, 100)` → `int(round(sum / 1.5))`. Canonical `25+25+23+3+25+19 = 120` now displays as **80 GOOD**, not **100 EXCELLENT**. Penalty model (`SCORE_WEIGHTS`, `_apply_weighted_impacts`) unchanged; boundary tests assert 100 only at all-25 ceiling, 0 only at all-zero.
- `ScoreGauge.tsx` gained a `maxValue?: number` prop (default 100) and a `_gaugeColor()` rewrite onto a normalized 0–1 fraction (red < 50 %, amber 50–79 %, green ≥ 80 %); six executive subscore radials + the Data at Rest tab gauge wired to `maxValue={25}`, with vitest coverage.
- Version bumped 4.10.0 → 4.10.1 (SoT in `pyproject.toml`); towncrier changelog fragment in operator language documenting the accepted 100 → ~80 visual jump; HUMAN-UAT operator walkthrough closed **PASS** (4/4 criteria, post-hard-refresh), verifier PASSED 5/5.

**Deferred to v5.0 Phase 01 (Stabilization):** EVIDENCE-TALLY-01 (evidence-summarizer tally gap), RENDER-CLI-01 + RENDER-PDF-01 (same-bug-class audit of CLI/HTML/PDF renderers).

---

## v4.8 Pre-Primetime Hardening + Operating Model (Shipped: 2026-05-14)

**Phases completed:** 13 phases, 53 plans, 122 tasks

**Key accomplishments:**

- One-liner:
- One-liner:
- SAML metadata fetcher routes all outbound URLs through validate_external_url before httpx.get, blocking RFC1918/loopback/link-local/file:///metadata IPs by default and emitting a HIGH advisory CryptoEndpoint per internal target when operator opts in via allow_internal_targets
- One-liner:
- broker_scanner.py changes:
- Bearer-token auth (hmac.compare_digest) and CSRF header check middleware for the FastAPI dashboard API, with configurable CORS allowlist and api_token fields in SecurityCfg
- Sliding-window rate limiter (60 POST/PUT/DELETE/PATCH/min/IP, Retry-After) and configurable CORSMiddleware registered in FastAPI app factory via get_cors_origins() — zero new pip dependencies
- One-liner:
- Full 16-test auth/CSRF/rate-limit/CORS/GET-auth/introspection/pdf-port-clamp suite; require_auth + require_csrf wired at router level on pdf, qramm, scan, and trends routers via TDD RED/GREEN cycle
- One-liner:
- fetchApi() TypeScript wrapper in src/dashboard/src/lib/api.ts enforcing X-Quirk-Request CSRF header and Bearer token on all 14 API call sites across 9 dashboard files, with 401/403/429 error handling at each site
- One-liner:
- Substitution table:
- 1. [Rule 1 - Bug] Refined _is_fstring_with_safe_str to handle benign Name + safe_str pattern
- One-liner:
- One-liner:
- 1. [Rule 1 - Bug] Regenerated expected_vault_cbom.json golden fixture
- One-liner:
- One-liner:
- One-liner:
- SQLite-backed scheduled_scans/scheduled_runs tables with argparse CRUD subcommands (add/list/enable/disable/remove) using croniter for cron validation and path-traversal-safe name allowlist
- 60-second sleep-loop dispatcher with SIGINT/SIGTERM signal handling, croniter next-run computation, subprocess.Popen crash-isolated dispatch, and startup recovery for orphaned runs
- FastAPI GET/POST/PATCH/DELETE /api/schedules router (first writable dashboard route, D-04) + React /schedules page with Switch toggles, delete Dialog, and optimistic UI — 11 pytest tests, production build verified
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- 1. [Rule 3 - Blocking] Added Phase 63 model/helper prereqs missing from worktree
- 1. [Rule 2 - Missing] Register Plan 01 test stubs in skip_registry.py
- 1. [Rule 3 - Blocking] Worktree branch was 14 commits behind main
- `src/dashboard/src/types/api.ts`
- One-liner:
- 1. [Rule 3 - Blocker] Worktree missing Phase 63/64/65 infrastructure
- One-liner:
- Import addition
- Argparse additions
- quirk/dashboard/api/schemas.py:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:

---

## v4.6 Enterprise Readiness (Shipped: 2026-05-05)

**Phases completed:** 6 phases (45–50), 24 plans
**Files changed:** 125 files, +20,560 / -405 lines
**Timeline:** 2026-05-03 → 2026-05-05 (3 days), 105 commits
**Audit:** passed_with_followup — 36/36 requirements, 6/6 integration flows

**Key accomplishments:**

- `[all]` meta-extra + `quirk.util.optional_extra` probe registry eliminate ImportError crashes on `pip install quirk`; coverage-gap advisory findings surface missing extras gracefully
- 5 new TLS finding types (expired CRITICAL, self-signed HIGH, untrusted-CA MEDIUM, RSA<2048 HIGH, EC<256 HIGH) + `tls-cert-defects` chaos lab profile for end-to-end verification
- Comma/`@file`/CIDR multi-target ingestion and optional nmap pre-scan port discovery with 10,000-probe TTY budget guard wired into both interactive mode and CLI
- `_build_finding` chokepoint enforces non-empty `description`/`remediation` on every finding; FIPS 203/204/205 algorithm names replace stale Kyber/Dilithium terminology project-wide; CI grep gate enforces compliance
- `quirk/compliance/` maps 24 finding categories to PCI-DSS 4.0.1/HIPAA/FIPS 140-3; staleness CI gate; `quirk compliance status` CLI; Compliance Summary in HTML/PDF reports
- `docs/architecture.md` (3 Mermaid diagrams, connector matrix) and `docs/operators-guide.md` (compliance runbook) authored and synced to Obsidian vault Reference/

**Deferred to v4.7:** COMPLY-10 (CBOM FIPS annotations), COMPLY-11 (SOC2/ISO27001 mapping), DOCS-05 (quirk doctor health check)

---

## v4.5 Reliability & Gap Closure (Shipped: 2026-05-03)

**Phases completed:** 7 phases, 40 plans, 69 tasks

**Key accomplishments:**

- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- Typed DarFinding Pydantic model + _derive_dar_findings() projection with 7-protocol dispatch, wired into ScanLatestResponse — all 8 Wave 0 tests GREEN
- lab.sh ALL_PROFILES replaced with _derive_all_profiles() bash parser reading docker-compose.yml at runtime, adding profiles subcommand, covering all 18 profiles including v4.3+v4.4 additions
- One-liner:
- Six category-tuned oracle sections (database, storage-s3, vault, storage legacy, email, broker) appended to expected_results_v4.md using verbatim scanner output strings, completing the 19-profile v4 oracle through v4.4
- One-liner:
- One-liner:
- Pytest config with slow-marker exclusion, AST-walk skip-registry gate, scan_error_category column with idempotent migration, and 9 xfail stubs that downstream plans turn green.
- Canonical [scan.timeouts] / [scan.retry] sub-tables landed on ScanCfg with warn-on-read deprecation aliases for the four legacy flat fields; config_from_dict loads sub-tables and falls back to legacy flat keys when no sub-table is present.
- BACK-45 cfg.scan mutation pattern eliminated; TLS/SSH/db/vault/jwt/container/source/email/broker scanners now read timeouts from the canonical cfg.scan.timeouts sub-table; run_scan.py:743 broker AttributeError fixed; ROBUST-02 TLS-timeout test green.
- `_wrapped_phase` helper added to run_scan.py with BaseException protection (re-raises KeyboardInterrupt/SystemExit, captures everything else as `scan_error_category='exception'`); broker_scanner and email_scanner emit canonical D-12 advisory + `scan_error_category='missing_extra'` row when the [motion] extra is absent; trends.py cur_err/prev_err exclude `missing_extra` so absent extras never register as regressions; 4 ROBUST-01/03 xfail stubs flipped to real assertions plus one new D-15 trends test — all green.
- Deletes 13 stale code-reason skips, converts defensive skips to pytest.fail, marks 9 slow tests, and turns the Plan 01 skip-registry meta-gate green — default `pytest` now runs in ~6s with zero stale skip markers.
- Consultant-facing timeout/retry documentation landed (configuration.md sub-table reference + D-10 upper-bound formula + ROBUST-04 audit doc), and the Phase 40 carry-over `lab.sh` profile-sweep gap is closed on both `down` and `reset` arms.
- Phase 41 closed across all four artifacts: UAT-SERIES.md gained UAT-41-01..04 entries (stderr advisory, upper-bound formula, lab.sh profile sweep, 60s budget); vault UAT-Series.md mirror synced; vault Phase-41 phase note created with status: complete sourcing all 6 prior plan SUMMARYs; ROADMAP.md Phase 41 checkbox flipped to [x]; STATE.md updated with Phase 41 close-out decisions and progress 4/7 phases (22/22 plans, 100%).
- 1. [Rule 3 — Blocker] Added `tests/__init__.py` to make `tests` a real package
- 3 shape-golden synthesizers
- 1. [Rule 3 — Blocking] Added `pythonpath = ["."]` to `[tool.pytest.ini_options]`
- Vault UAT mirror
- 1. [Rule 1 - Bug] Corrected trends API path in fixture middleware
- Sidebar Link primitives now receive visible keyboard focus rings via Tailwind focus-visible utilities; axe color-contrast audit confirmed zero new violations against the seeded fixture baseline.
- 1. [Rule 1 - Bug] Fixed Cytoscape HSL syntax error in roadmap.tsx
- DOM sentinel pattern closes UAT Gap 2: print.tsx sets `body[data-ready]` after data loads; pdf.py waits for that attribute before calling `page.pdf()`
- 1. [Rule 1 - Bug] Fixed pre-existing skip_registry drift
- One-liner:
- 1. [Rule 1 - Bug] Used correct scan_vault_targets signature
- One-liner:
- One-liner:
- 7 of 14 deferred UAT/VERIFICATION items closed in STATE.md via chaos lab automation and pytest tests, satisfying UAT-02 (Phase 29 cloud-only rationale) and UAT-04 (>=50% net reduction)

---

## v4.4 Data in Motion (Shipped: 2026-04-29)

**Phases completed:** 6 phases (32–37), 33 plans
**Files changed:** 162 files, +26,973 / -233 lines
**Timeline:** 2026-04-27 → 2026-04-29
**Tests:** 662 passed, 7 skipped, 1 deferred (pre-existing SAML scan-window regression — Phase 24 ISSUE-3, out of scope)
**Tag:** `v4.4.0` (commit `b72797a`)

**Key accomplishments:**

1. Email protocol scanning (Phase 32) — SMTP/SMTPS, IMAP/IMAPS, POP3/POP3S TLS posture across all 7 standard ports with STARTTLS-stripping detection on port 25; new `email` Docker chaos lab (Postfix + Dovecot, weak TLS).
2. Message broker TLS scanning (Phase 33) — Kafka (9092/9093/9094), RabbitMQ AMQPS (5671) + management API, Redis TLS (6380), Azure Service Bus, AWS SQS; plaintext-listener HIGH findings for all three local broker types; new `broker` Docker chaos lab (Kafka + RabbitMQ + Redis, weak TLS).
3. Data-in-motion intelligence (Phase 34) — six new `motion_*` evidence counters, three `motion_*_ratio` scoring weights with `strict`/`balanced`/`lenient` profile multipliers, and a 6th named `data_in_motion` subscore alongside `tls`/`ssh`/`api`/`identity`/`data_at_rest`; legacy v4.3 scans preserve full credit (D-12 backward compatibility).
4. Motion CBOM integration (Phase 35) — email and broker TLS endpoints generate Pass-1 algorithm components with quantum-safety classification; plaintext-only labels (`KAFKA-PLAIN`, `AMQP-PLAIN`, `REDIS-PLAIN`, `SMTP-STARTTLS`) excluded from Pass-2/Pass-3; golden snapshot fixtures lock the output shape.
5. Dashboard Motion tab (Phase 36) — new `/motion` React route with email per-port table + STARTTLS warnings, broker per-family grouped sections + plaintext flags, "Data in Motion" 6th `ScoreGauge`; `/api/scan/latest` carries `motion_findings`.
6. v4.4.0 release artifacts (Phase 37) — version bump locked across 6 surfaces by `tests/test_version.py`; `[motion]` meta-extra over `[email]+[broker]+[kafka]`; INFRA-03 18-test Nyquist coverage module; first top-level `CHANGELOG.md` + `docs/release-notes/4.4.0.md`.

**Requirements:** 50/50 mapped, 50/50 complete (100%) ✓

**Known deferred items at close:** 2 (see STATE.md `## Deferred Items`)

- **DEF-v4.4-01** — Phase 36 `wave_0_complete: false` flip — gated on the SAML scan-window regression below; documented in `37-VALIDATION.md` "Deferred Gaps" #1.
- **DEF-v4.4-02** — SAML/OIDC missing from `/api/scan/latest` `identity_findings` (real functional regression, ISSUE-3 from Phase 24, predates v4.4) — out of scope for v4.4.0; tracked for v4.5 follow-up.

**Carry-over from prior milestones:** 14 audit-open items (UAT gaps on phases 04–31, verification gaps on 25/28/31) — all pre-v4.4, non-blocking, retained in STATE.md `## Deferred Items`.

**Archived:** `.planning/milestones/v4.4-ROADMAP.md`, `.planning/milestones/v4.4-REQUIREMENTS.md`

---

## v4.3 Data at Rest (Shipped: 2026-04-26)

**Phases completed:** 7 phases (25–31), 24 plans, 504 tests collected

**Key accomplishments:**

1. Identity Findings Accuracy (Phase 25) — OIDC RS-family routing fix in `_derive_identity_findings()`, TLS-bleed guard in `_derive_findings()`, `ldap3>=2.9.1` in `[identity]` extras, chaos lab expected results oracle for all three v4.2 identity scanner profiles (DNSSEC/SAML/Kerberos) — closes NEW-ISSUE-1, ISSUE-2, NEW-ISSUE-3 from v4.2 audit
2. GCP Connector (Phase 26) — 47-entry `GCP_KMS_ALGORITHM_MAP` including PQC, Cloud SQL TLS enforcement, GCS CMEK detection; `gcs_scan_json` ORM column; `[cloud]` extras group; CBOM Pass 1/2/3 integration; `DefaultCredentialsError` explicit catch
3. Database Encryption Detection (Phase 27) — PostgreSQL 3-tier SSL probe (`pg_has_role`), MySQL `Ssl_cipher` scanner, RDS `StorageEncrypted`+`KmsKeyId`; `dat_scan_json` ORM column; `dar_` 5th subscore prefix; `[db]` extras; Docker database chaos lab (25432/23306)
4. Object Storage Audit (Phase 28) — S3 severity ladder via `ThreadPoolExecutor(max_workers=10)`, Azure Blob `keySource` ladder, GCS sentinel reuse (zero duplicate API calls); `dar_storage_*` evidence counters (SCORE_WEIGHTS 12.0/4.0); MinIO chaos lab (storage-s3 profile)
5. Kubernetes Secrets Inspection (Phase 29) — EKS/GKE/AKS managed encryption APIs, secret type enumeration, RBAC-403 graceful degradation, `encryption-config-inaccessible` invariant; `dar_k8s_*` evidence counters; gap closure CR-01/02/03
6. HashiCorp Vault Connector (Phase 30) — Transit keys with PQC positive findings (`ml-dsa`/`slh-dsa`), PKI CA cert detection, auth method risk tiering; `dar_vault_weak_count` HIGH-only counter; CBOM Pass 2+3 VAULT skip; dedicated chaos lab at port 28200 with seed.sh
7. Trend Analysis (Phase 31) — `compute_trend_report()` with score delta and net-new/resolved findings by severity; `GET /api/trends` FastAPI route; React `TrendsPage` with `useTrendsData` hook and `/trends` route; `scanned_at`-based session grouping — no new SQLite table

**Archived:** `.planning/milestones/v4.3-ROADMAP.md`, `.planning/milestones/v4.3-REQUIREMENTS.md`

**Known deferred items at close:** 16 (see STATE.md Deferred Items)

- B-1: OIDC ep.severity always None (cosmetic — downstream correct via scan.py re-derivation)
- W-2: dat_scan_json always NULL for DB rows (scoring correct via service_detail; JSON contract broken)
- W-1: Vault CBOM Pass 1 fragile — future VAULT skip list addition could break transit key registration
- 9 UAT deferred items (live Docker/cloud/browser environment required)
- Pre-existing carry-over UAT/verification gaps from prior milestones (acknowledged, non-blocking)

---

## v4.2 Identity Crypto (Shipped: 2026-04-24)

**Phases completed:** 8 phases (17–24), 14 plans, 352 tests passing

**Key accomplishments:**

1. Three new identity protocol scanners — DNSSEC (RFC 8624/9905 algorithm classification), SAML/OIDC (defusedxml XXE-safe metadata parsing), and Kerberos (impacket AS-REQ unauthenticated probe) — expanding QU.I.R.K.'s cryptographic surface to identity protocols
2. Three Docker Compose chaos lab profiles — BIND9 with 4 DNSSEC zones, SimpleSAMLphp with RSA-1024 signing cert, Samba DC with RC4-enabled realm — providing testbeds for all three identity scanners
3. Full identity CBOM pipeline — all three protocols produce CycloneDX components via dedicated elif branches; Pass 2/3 skip lists prevent hollow X.509 artifacts for non-certificate identity records
4. Identity surface in dashboard — React Identity tab with per-protocol summary cards (Kerberos/SAML/DNSSEC), FastAPI IdentityFinding model and identity_findings array in /api/scan/latest, Findings table protocol column filter
5. Intelligence layer extended — identity_weak_etype_count, saml_weak_signing_count, dnssec_weak_algo_count counters in evidence.py wired into compute_readiness_score()
6. Scan-session timestamp isolation (Phase 24) — ISSUE-3 HIGH gap eliminated: shared session_start from run_scan.py passed into all 3 identity scanners; scan-window query no longer silently excludes early-stamped endpoints

**Archived:** `.planning/milestones/v4.2-ROADMAP.md`, `.planning/milestones/v4.2-REQUIREMENTS.md`

**Known deferred items at close:** 12 (see STATE.md Deferred Items)

- ISSUE-2 (MEDIUM): ldap3 absent from pyproject.toml → Phase 25 in v4.3
- NEW-ISSUE-1 (MEDIUM): OIDC RS256 findings mislabeled as TLS-sourced → Phase 25 in v4.3
- NEW-ISSUE-3 (LOW): expected_results_v3.md missing identity chaos lab entries → Phase 25 in v4.3
- Pre-existing carry-over UAT/verification gaps from v3.9/v4.1 (acknowledged, non-blocking)

---

## v4.1 Foundation Polish (Shipped: 2026-04-08)

**Phases completed:** 9 phases, 17 plans, 29 tasks

**Key accomplishments:**

- 1. [Rule 1 - Bug] Cleaned stale version tag in code comment
- Removed enable_windows_adcs from ConnectorsCfg and interactive.py; added JWT/container/source scanner prompts with correct AWS/Azure labels
- One-liner:
- One-liner:
- PROFILE_MULTIPLIERS constant (strict=1.4x, balanced=1.0x, lenient=0.7x) added to compute_readiness_score() with prefix-based agility/identity weight scaling, plus 7 Wave 0 expectedFailure stubs for executive.py migration
- executive.py fully migrated from assessment/ imports to intelligence call sequence with ported _build_interpretation(), NOW/NEXT/LATER roadmap, and profile+calibration wired at both call sites
- One-liner:
- TDD RED scaffold establishing the Phase 12 contract: 3 failing tests prove version inconsistency (4.0.0 vs 4.1.0), stale config fallback, and [owner] placeholder; 3 passing tests guard already-clean areas (config template, no quirk scan refs, load_config integrity)
- Version bump to 4.1.0 across all 5 canonical locations and dev-install workflow replacing [owner] placeholder in Getting Started guide — all 6 Phase 12 contract tests GREEN, 205 total tests passing
- 10 RED expectedFailure tests in tests/test_interactive_mode.py defining the complete Plan 02 implementation contract for interactive_config() overhaul
- Rewrote interactive_config() implementing all 10 INTER requirements with auto-detected timezone, hardcoded consulting-grade TLS ports and SNI, targets-first prompt order, profile selection menu, unified 4-tier data classification menu, and AWS/Azure credential warnings; updated run_scan.py to unpack tuple return and remove deprecated prompt_for_context() call.
- 7-test RED scaffold covering SCORE-01 through SCORE-04: profile multipliers verified, validate.py dead param caught, migration advisor regression-guarded, dashboard profile gap exposed
- SCORE-02 and SCORE-04 made GREEN: dead validate_run parameter removed and dashboard now reads calibration.profile from intelligence JSON to produce profile-aware readiness scores
- 7-test Wave 0 scaffold asserting quirk/connectors/ absent (GREEN), cfg.scan SSH mutation guard structure (RED), scorecard.py absent (RED), and all 14 phase VALIDATION.md files nyquist_compliant (RED)
- Deleted orphaned scorecard.py and co-deleted its test, moved SSH cfg.scan mutations inside try block for correct finally-guard semantics, and updated all 14 completed phase VALIDATION.md files to nyquist_compliant: true (11 updated, 2 created) — turning all 7 test_hygiene.py tests GREEN
- 4-test RED TDD scaffold proves CLI-04 (pyproject.toml manifest version = 4.0.0) and SCORE-04 (interactive.py output dir defaults to "output" not "quirk-output") gaps exist before Plan 02 fixes
- pyproject.toml bumped to 4.1.0 and interactive.py output defaults corrected to "quirk-output", turning all 4 RED TDD tests GREEN and closing CLI-04 and SCORE-04 milestone gaps

---

## v3.9 Gap Closure (Shipped: 2026-04-04)

**Phases completed:** 13 phases, 40 plans, 75 tasks

**Key accomplishments:**

- Consolidated writer.py onto single intelligence-layer scoring path and fixed cert_pubkey_alg field extraction bug — both were silent data quality blockers
- Threaded SSH scanner with ssh-audit subprocess integration storing full KEX/hostkey/MAC JSON in new ssh_audit_json column, replacing sequential banner-only scan
- One-liner:
- Full qcscan -> quirk rename with pyproject.toml: zero remaining qcscan/QuRisk references in .py files, all 56 tests pass, `python3 -c "import quirk; print(quirk.__version__)"` prints 3.9.0
- classify_algorithm() lookup table mapping 50+ algorithm strings from TLS/SSH/cert scanners to CycloneDX CryptoPrimitive enum values and NIST PQC quantum security levels via cyclonedx-python-lib 11.7.0
- CycloneDX Bom builder with TLS cipher suite decomposition, SSH kex/key/enc/mac parsing, certificate components, and bom_ref deduplication via in-memory registry
- CycloneDX 1.6 JSON+XML file output with write_cbom_files() wired into write_reports() as step 5, producing cbom-{stamp}.cdx.{json,xml} alongside every scan run
- CryptoEndpoint extended with four JSON blob columns (jwt/container/source/cloud), ConnectorsCfg extended with Phase 3 flags and cloud config, all eight Phase 3 dependencies installed, and Wave 0 test scaffolds defining contracts for SCAN-03 through SCAN-07
- Three new CryptoEndpoint-producing scanners (JWT/JWKS via httpx, container images via syft, source code via semgrep) expanding QU.I.R.K. from 2 to 5 scan surfaces with graceful degradation when tools are absent
- AWS boto3 connector (ACM/KMS/CloudFront/ELBv2) and Azure SDK connector (KeyVault/AppGateway) with paginator-based enumeration and graceful SDK degradation
- quirk/cbom/classifier.py
- 4 FastAPI JWT microservices (RS256/2048-bit, HS256-weak/128-bit, RSA-1024, alg:none) deployed as docker-compose jwt profile on ports 20001-20004 with JWKS + /token endpoints matching SCAN-03 scanner field expectations
- Docker Registry v2 profile on port 20005 with 3 seeded test images containing openssl, cryptography==2.9.2, and pyOpenSSL==19.1.0 that Syft's CRYPTO_LIB_ALLOWLIST will detect
- Gitea instance seeded with 3 repos (Python/Go/Java) covering all 4 D-08 crypto anti-pattern categories for semgrep p/cryptography validation
- LocalStack KMS + HashiCorp Vault transit engine + postgres-pgcrypto storage profile with 5 Docker Compose services seeded with real crypto key material for scanner validation
- ubuntu:18.04 OpenSSH ssh-weak service (port 20022) with group1-sha1/ssh-dss/hmac-md5 weak config, osixia/openldap ldaps service (port 636) with TLS via modern.crt, and expected_results_v3.md updated with all 6 Phase 4 scanner oracle sections
- One-liner:
- GET /api/scan/latest endpoint wired to SQLite intelligence functions, with Executive (5 arc gauges + severity chart), Findings (TanStack Table + Sheet), and Certificate Inventory (expiry color-coded + quantum-safety badges) pages
- Cytoscape.js CBOM bipartite graph and migration DAG pages with shadcn/ui table, full route wiring in App.tsx
- POST /api/export/pdf Playwright headless PDF generation from /print React page with white-bg print layout and graceful 503 degradation when chromium absent
- README fully replaced and docs/getting-started.md + docs/installation.md written: zero-to-first-scan consultant path in under 10 minutes covering macOS, Linux, and Windows WSL
- Complete config.yaml and CLI flag reference in docs/configuration.md — all 6 top-level blocks, scan profiles, score profiles, and copy-pasteable minimal and full config templates
- Four copy-paste-ready connector guides covering AWS IAM policy (7 actions), Azure RBAC roles, Syft-based container scanning, and semgrep p/cryptography source scanning — all permissions derived from the actual connector source code.
- Consultant-facing report interpretation guide with exact scoring thresholds, all four subscore driver tables, severity tier definitions, and Client Conversation sideboxes for live client meetings
- Three-section CBOM guide for compliance officers, consultants, and auditors — covering what a CBOM is, QU.I.R.K.'s five-step CycloneDX pipeline, and copy-pasteable audit language for NIST SP 800-208, CNSA 2.0, and ISO 27002:2022
- Authoritative chaos lab operator guide covering all 10 profiles (core through ldaps) with per-profile port matrices, copy-pasteable start commands, and connector config snippets
- One-liner:
- Rich Panel startup banner, --version/--quiet flags, and rich scan summary table replacing tqdm/print output in QU.I.R.K. CLI
- quirk/reports/html_renderer.py
- SVG redesigned:
- Version bumped to 4.0.0 across __init__.py, pyproject.toml, and writer.py; quirk init implemented using importlib.resources with bundled config_template.yaml; getting-started.md updated to git+https install path
- 1. [Rule 1 - Bug] Cleaned stale version tag in code comment
- Removed enable_windows_adcs from ConnectorsCfg and interactive.py; added JWT/container/source scanner prompts with correct AWS/Azure labels
- One-liner:
- One-liner:
- PROFILE_MULTIPLIERS constant (strict=1.4x, balanced=1.0x, lenient=0.7x) added to compute_readiness_score() with prefix-based agility/identity weight scaling, plus 7 Wave 0 expectedFailure stubs for executive.py migration
- executive.py fully migrated from assessment/ imports to intelligence call sequence with ported _build_interpretation(), NOW/NEXT/LATER roadmap, and profile+calibration wired at both call sites
- One-liner:
- Added `dashboard/static/
- Two-line fix closes GAP-INT-01 and GAP-INT-02: deps.py default db_path aligned to './quirk.db' (config_template.yaml) and server.py now sets QUIRK_SERVE_PORT before uvicorn starts so PDF export inherits the correct port
- SSH algorithm parsing added to _derive_cbom() in scan.py: kex/key/enc/mac sections from ssh_audit_json now produce classified CbomComponent entries in the dashboard CBOM viewer, closing GAP-INT-03

---
- **v5.18 Migration Execution** — shipped 2026-09-03 as `v5.18.0` (first PyPI release since 5.12.0; carries v5.16 + v5.17 content). Phases 177–181, 37 plans, 142 commits. Closure tracking end to end: stable finding identity, remediation item model, machine-observed closure with `resurfaced`, per-deadline burndown, CycloneDX VEX. 16/16 requirements; audit passed, 0 blockers.
