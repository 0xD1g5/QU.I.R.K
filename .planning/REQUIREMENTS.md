# Requirements: QU.I.R.K. — Milestone v5.24 UAT Coverage Drain

**Defined:** 2026-09-13
**Core Value:** Complete, defensible cryptographic inventory with CBOM deliverable and
quantum-readiness score — handed to a client in under two hours. This milestone turns QU.I.R.K.'s
own release-gate document from a record of *what was checked* into a record of *what is covered*.

**Research basis:** None — research deliberately skipped at the boundary. v5.24's evidence is
entirely in-repo and already enumerated per-case: `docs/uat-coverage-gaps.md`'s "coverage that would
be needed" column, Phase 169-06's per-case vitest rejection record, and two named guard defects.
Four external researchers would have re-derived what the repo already states. The one genuinely
external question — Playwright scope for the jsdom-impossible cases, and Node-in-CI for the vitest
slow leg — is scoped inside COV-05 and GUARD-02 as in-phase work.

**Measurement basis (live parse of `docs/UAT-SERIES.md`, 2026-09-13 — not carried from any prior
document):** 878 case headings; **70** carry a `GAP — no substitute coverage` annotation; **45** of
those are series ≤163 and **25** are series 164–202; **31** are series-7 dashboard-UI cases, of
which **28** are jsdom-tractable and **3** are not. Every count in this file was re-derived at
definition time. Where a count here disagrees with a prior document, treat the disagreement as a
finding to investigate (COV-03), not as an error in either.

## v1 Requirements

### Catalog Freshness (gating drain — sequenced first)

`tests/test_hardware_staleness.py` is RED on `main` at milestone open (91 days vs a 90-day
threshold). A red staleness gate is a poor backdrop for a coverage-integrity milestone, and
`hw_cve.py`'s 30-day cadence trips ≈2026-10-02 — mid-milestone — if not handled in the same pass.

- [ ] **STALE-01**: `HARDWARE_MATRIX` is re-verified against **all 8 per-vendor `source_url`s**
      (F5, Cisco, Palo Alto, Fortinet, Juniper, HPE, Intel, Thales) plus the top-level NSA CNSA 2.0
      page — not the NSA page alone, since the per-vendor entries are the catalog's actual
      PQC-readiness claims. Any source that could not be reached is **named explicitly in the commit
      message**, never papered over (NSA / `media.defense.gov` return HTTP 403 to non-browser
      agents — an expected obstacle, not a silent skip). `last_verified` is bumped only for what was
      really verified. A correction found is a success, not a failure.
      `tests/test_hardware_staleness.py` green.

- [x] **STALE-02**: `quirk/scanner/hw_cve.py` is re-verified in the same pass so its 30-day cadence
      does not trip mid-milestone, and the ages of **all** date-gated catalogs are recomputed from
      source (`grep -rln "STALENESS_THRESHOLD_DAYS" quirk/`) rather than read off CLAUDE.md's
      hand-maintained list — that list said "eight" and omitted `hardware_meta.py` until a live CI
      trip exposed it.

### Coverage Worklist Integrity

- [x] **COV-01**: `docs/uat-coverage-gaps.md` is **regenerated from the live corpus** and covers
      every series, not just 1–163. The generator reads `docs/UAT-SERIES.md` (and/or the ledger, per
      COV-03's verdict) at run time; the committed file is its output. Enumeration loses entries and
      derivation does not — this project has been bitten by hand-maintained site lists at least five
      separate times.
      **Closed Phase 204 plan 204-03**: `scripts/generate_uat_coverage_gaps.py` +
      `tests/test_uat_coverage_gaps_freshness.py` (byte-reproducibility + drift gate, mirrors the
      `error-codes.md`/`severity-bands.json`/`score-strings.json` precedent). Re-verified live at
      204-05 close: `scripts/generate_uat_coverage_gaps.py` output diffs empty against the committed
      file.

- [x] **COV-02**: a standing gate fails when a GAP-dispositioned case exists that the regenerated
      worklist does not name, so the worklist cannot silently fall behind the corpus again. Same
      derived-gate shape as the shipped backlog-reconciliation gate: it must fail for the honest
      reason (a real un-absorbed case), never be satisfied by narrowing its own enumeration.
      **Closed Phase 204 plans 204-04/204-04b**: `tests/test_uat_worklist_reconciliation_gate.py` +
      `.planning/phases/204-worklist-truth-derivation/204-RED-PROOF.md` (three recorded RED
      inductions — numeric id, non-numeric id, Notes-line-only GAP — with md5 pre/post byte-identical
      reverts). 204-04b widened the gate's own enumeration after a live orchestrator probe found a
      real scoping gap in 204-04's first version; see 204-05-SUMMARY.md for the closure record.

- [x] **COV-03**: the GAP-count disagreement between the two sources of truth is reconciled with
      per-case evidence. `docs/uat-coverage-gaps.md` reports **57** GAP rows for series 1–163 from
      `docs/uat-disposition-ledger.jsonl`'s `outcome` field; parsing the document's own
      `GAP — no substitute coverage` annotations for the same series gives **45**. The on-disk
      checkbox grammar renders both `DEFERRED` and `GAP` as a checked SKIP, so the document alone
      cannot distinguish a verified substitute from an honest absence. The requirement is a written
      verdict naming which source is authoritative, why they diverged, and which count the drain is
      measured against — not a silent pick.
      **Closed Phase 204 plan 204-01/204-02**: `docs/uat-coverage-reconciliation.md` is the written
      verdict — `docs/UAT-SERIES.md` is the single authoritative source going forward (D-02), the
      12-case divergence decomposes into 5 named causes with arithmetic closure asserted
      programmatically, and all 12 cases were resolved into the document with per-case evidence. The
      **57**/**45** figures above are this requirement's own historical measurement and are left
      unedited; the live re-derived counts have moved twice since (66, then 76 once 204-04b widened
      the standing gate's own enumeration) — recompute via
      `.venv/bin/python -m scripts.uat_corpus reconcile` before citing any GAP count, per
      `docs/uat-coverage-reconciliation.md`'s own provenance section.

### Dashboard UI Coverage

Phase 169-06 already spent the vitest-citation dialect against all 31 series-7 cases and converted
**zero**, having read every `it()`/`test()` title in all 21 existing `.test.tsx` files. That is the
finding this category acts on: no genuine substitute exists today, so the tests must be written.

- [ ] **COV-04**: each of the **28** jsdom-tractable series-7 GAP cases has a real vitest test that
      asserts the behaviour the case actually describes, and its disposition is updated to cite that
      node. A test whose title merely resembles the case is not coverage — Phase 169-06 explicitly
      rejected `sensors-loading.test.tsx` as a substitute for `UAT-7-34` on exactly this ground
      (same component pattern, wrong subject).

- [ ] **COV-05**: the **3** structurally jsdom-impossible cases — `UAT-7-01` (SPA mounts without a
      blank screen), `UAT-7-17` (click Export PDF, assert a valid downloaded PDF), `UAT-7-32` (zero
      console errors across every route) — receive either real Playwright E2E coverage or a
      recorded, reasoned permanent disposition naming why no substitute can exist. A fabricated PASS
      is never acceptable; an honest permanent GAP is.

### Guard Integrity

Both items are cases where a guard's own limitation is what makes real coverage uncitable — the
gate, not the coverage, is the defect.

- [ ] **GUARD-01**: `NODE_REF_RE` in `tests/test_uat_disposition_integrity.py` resolves natural
      `Class::method` pytest node syntax (it currently cannot span a second `::`), retiring the
      `ClassName*method_name` glob workaround class-based substitutes were forced to use.

- [ ] **GUARD-02**: the vitest `-m slow` execution leg actually **executes** in CI rather than being
      existence-checked only. `Linux Full Suite` installs no Node, so `VITEST_TOOLCHAIN_AVAILABLE`
      is False there; `dashboard-quality.yml` already exists and is the candidate home. This closes
      the existence-vs-execution asymmetry that pytest substitutes already had removed, reappearing
      one layer down for vitest.

### Security & Report Coverage

- [ ] **COV-06**: `UAT-104-04` — a test constructs a `JiraChannel` with an internal/RFC1918
      `jira_url` and asserts `validate_external_url` raises. The guard is confirmed **wired** by
      source inspection in `quirk/ticketing/jira.py`, but the case's own `-k ssrf` filter matches
      **0 of 8** collected tests: today nothing anywhere proves it actually fires. Security-relevant.

- [ ] **COV-07**: `UAT-88-02` / `UAT-88-03` — the six-row score-decomposition table
      (`quirk/reports/templates/report.html.j2`) is asserted at **render-output** level in HTML, and
      in the Playwright PDF. Today only data-layer parity and markdown presence are covered; the PDF
      leg has no pytest coverage of this table at all.

- [ ] **COV-08**: `UAT-8-04` / `UAT-8-05` — the hygiene subscore (plaintext ratio) and the
      identity-trust subscore (mTLS bonus) are each asserted **in isolation**, holding other evidence
      fixed, rather than inferred from movement in the overall score.

### Worklist Hygiene

- [x] **COV-09**: rows that can never close are retired as recorded OBSOLETE with evidence, not
      carried as perpetual GAPs. **Closed Phase 204 plan 204-02 with a corrected, evidenced outcome —
      2 retirements, not the 3 originally proposed below:** `UAT-92-01` (a one-time historical
      v5.0.0 tag-creation gate — the event already happened and is not repeatable) and `UAT-5-18`
      (HashiCorp Vault Transit has no `rsa-1024` key type at all, so the case's own dual-flag premise
      is untestable) were retired `SKIP (OBSOLETE — <reason>)`, structurally distinct from GAP in
      both the document grammar and `scripts/uat_corpus.py::reconcile()`
      (`tests/test_uat_obsolete_grammar.py`). The third candidate named below,
      `UAT-47-04` (originally proposed as "the interactive nmap y/N prompt no longer exists,
      superseded by the `--discovery` flag"), was checked against source per this requirement's own
      "recorded decision" standard and found **false**: `quirk/interactive.py`'s
      `enable_nmap = _prompt_bool(...)` prompt is still live via `run_scan.py`'s wizard-mode path
      (`run_scan.py:1908`); `--discovery` is a separate, coexisting CLI-mode-only flag
      (`run_scan.py:1532`), not a supersession. `UAT-47-04` was corrected to an honest `GAP` instead
      of retired on a false premise — see `docs/uat-coverage-reconciliation.md`'s "Retirements
      (COV-09)" section for the full evidence trail. A GAP that can never close is noise in the
      worklist, not honesty — but the retirement must be a recorded decision with its reason, never a
      quiet deletion, which is exactly what the `UAT-47-04` correction demonstrates.

### Carried Doc Debt (from the v5.23 boundary review)

- [ ] **DOC-01**: `ROADMAP.md`'s Phase 202 criterion-3 wording is corrected from per-finding
      score-lift to the theme-level behaviour actually shipped (`score_lift` is keyed by remediation
      theme covering N findings; v5.23 D-01/D-08/D-09). Recorded as stale in STATE.md at the v5.23
      close with the correction pending.

- [ ] **DOC-02**: `docs/report-interpretation.md` gains the 999.112 precondition note — LIFT-05's
      four-surface numeric-equality guarantee holds only for **unmodified** report templates,
      because RPT-02's operator override is a full-file override that can drop the roadmap section
      and nothing validates its presence.

## v2 Requirements

Deferred to future milestones. Tracked in `.planning/HORIZON.md`'s Open-Item Ledger, which is the
canonical home — archived roadmaps swallow backlog items (`BACK-A11Y-01` was invisible for three
months that way).

### Coverage / Lab

- **999.110**: Multi-host chaos-lab topology (P2, effort M, feasibility CONFIRMED). Considered as a
  GAP-enabler at this boundary — it would convert the 2 unexercisable Phase 195 UAT GAPs
  (crown-jewel badge, hardware-bridge edge styling) into real live-data cases — and set aside to
  keep this drain's anchor sharp. Re-read at the next boundary alongside 999.107.
- **999.107**: Exposure Map Tier B (P2). Gated on 999.110's live data; HORIZON already records that
  "needs a client engagement" is no longer the binding constraint.

### Correctness

- **999.111**: Drawer and roadmap disagree on score-lift where endpoints lack a shared
  `scan_run_id` (P2, v5.23's operator-accepted blocker). Fix shape is one shared endpoint-resolution
  helper, but `get_latest_scan`'s window/fallback tree is exercised by multiple pinned tests — needs
  its own phase and verification, not a post-review patch.
- **999.109**: Every GitHub release body is static Windows-sensor boilerplate (P2, effort S).
  Validates only on the next real release, so it wants a release-carrying milestone.

### Reporting

- **999.105 Tier 2**: Section-composition profiles (P3). Explicit **NO-GO** — ~15–16 plans, blocked
  behind a congruence-guard redesign spike and a 9-file parity-matrix redesign.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Rewriting `uat_runner.py` | `UAT-1-02`'s FAIL is a stale hardcoded version-substring check inside the runner itself — a real finding, but a tooling rewrite is its own scope and would swamp the drain |
| Converting existing DEFERRED substitutes to PASS | The drain's target is *absent* coverage. A verified substitute is already honest; churning dispositions inflates apparent progress without adding a test |
| Closing the 6 recorded FAIL dispositions | Those are product defects with their own evidence trail, not coverage gaps. Mixing defect-fixing into a coverage milestone is how the anchor gets lost |
| Tier 4 config-file parity | Needs its own threat-model decision (server-side `config.yaml` write surface) |
| Detection breadth (AD CS live, S/MIME content, passive capture) | Standing gate: no demand signal. Do not open without one |
| SaaS multi-tenancy | Parked since v5.4 — gate is a business-model signal, none has appeared |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| STALE-01 | Phase 203 | **PARTIAL — deliberately not closed** (1 of 8 vendors verified; 7 source documents gone. `tests/test_hardware_staleness.py::test_hardware_matrix_not_stale` is RED by design under a dated deferral in STATE.md. Operator owns URL re-sourcing — `.planning/todos/pending/hardware-matrix-source-urls-broadly-rotted.md`) |
| STALE-02 | Phase 203 | Closed (203-02) — `hw_cve.py` `last_verified` 2026-09-13, 6/6 rows re-verified against the live NVD API, `tests/test_cve_staleness.py` 6 passed. Flipped 2026-09-13 by Phase 204's close-out after Phase 203's backfilled verification found it left Pending despite being fully discharged |
| COV-01 | Phase 204 | Closed (204-03) |
| COV-02 | Phase 204 | Closed (204-04/204-04b) |
| COV-03 | Phase 204 | Closed (204-01/204-02) |
| COV-04 | Phase 206 | Pending |
| COV-05 | Phase 207 | Pending |
| COV-06 | Phase 208 | Pending |
| COV-07 | Phase 208 | Pending |
| COV-08 | Phase 208 | Pending |
| COV-09 | Phase 204 | Closed (204-02, 2 of 3 proposed retirements; UAT-47-04 corrected to GAP) |
| GUARD-01 | Phase 205 | Pending |
| GUARD-02 | Phase 205 | Pending |
| DOC-01 | Phase 208 | Pending |
| DOC-02 | Phase 208 | Pending |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15 ✓
- Unmapped: 0 ✓

## Standing Constraints Carried Into This Milestone

See `CLAUDE.md` for full detail. Named here because they change how work is executed, not just what.

- **All mutating GSD `state.*` / `phase.complete` / `milestone.complete` verbs remain UNSAFE on this
  machine** (semantic defect class — well-formed but wrong values; `phase.complete` marked a phase
  complete at 5/7 plans with an impossible `completed_plans: 142`, and both textual corruption
  signatures read CLEAN on it). Every phase and milestone close in v5.24 is hand-written under the
  pre-image + signature-diff protocol.

- **`requirements mark-complete` over-flips multi-phase requirements** — it has no per-phase
  granularity. Hand-flip single-phase requirements; verify this file by hand after any call that
  touches a requirement spanning more than one phase.

- **Never bump a `last_verified` date without actually re-verifying against the `source_url`.** The
  date is an attestation. Bumping it to clear a red gate fabricates that attestation and silently
  extends the stale window by a full cadence. A deferral recorded in STATE.md is honest; a bumped
  date is not. This constraint is load-bearing for STALE-01/02 specifically.

- **STALE-01/02 re-verification goes through Chrome browser automation** (operator decision,
  2026-09-13). NSA / `media.defense.gov` and likely several vendor advisories 403 non-browser
  agents, so the sources are read via the `mcp__claude-in-chrome__*` tools in the **main session** —
  those tools are unavailable inside worktree subagents, so Phase 203 must not be fanned out. A
  source that still cannot be read through the browser is an honest, dated deferral; the browser
  path removes an expected obstacle, it does not license bumping a date. See ROADMAP.md's
  "Autonomy Plan" section.

- **A hand-derived list of sites is not a safeguard.** Only a scan that regenerates its occurrence
  set from source at run time is. This is the fifth time the project has had to name this lesson,
  and it is the direct rationale for COV-01 and COV-02.

- **An honest GAP beats a fabricated PASS, every time.** A corpus reading 100% PASS would be worth
  nothing — v5.16's real deliverable was 32 recorded FAILs and 57 honest GAPs, not green gates.

---
*Requirements defined: 2026-09-13*
*Last updated: 2026-09-13 after initial definition*
