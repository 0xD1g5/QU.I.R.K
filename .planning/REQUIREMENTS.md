---
milestone: v5.25
milestone_name: Score Truth & Release Cut
defined: 2026-09-27
requirements_total: 15
---

# Requirements: v5.25 Score Truth & Release Cut

**Goal:** Make the readiness score mean one thing on every surface a client can see, then ship it —
the first tagged release since v5.21, carrying three milestones of accumulated work.

**Sequencing (operator decision 2026-09-27):** score first, release last. A tag freezes whatever
number the scorer emits, so `REL-*` runs after `XSURF-*` and `DENOM-*` land.

Every requirement below traces to a filed todo or backlog item whose root cause is CONFIRMED at an
exact file:line. This milestone adds no new detection capability and does no research — it makes an
existing number honest and ships it.

---

## v1 Requirements

### Cross-Surface Score Parity

One scan currently yields **15/100 + 5 CRITICAL** from the report pipeline and **19/100 + 7
CRITICAL** from the dashboard pipeline. Since Phase 209 both are downloadable from the same
executive view, one click apart, so an operator following the recorded mitigation exactly can still
hand a client two PDFs with different headline scores. Source:
`todos/pending/cli-dashboard-score-divergence-same-scan.md` (P1, reproduced twice, escalated
2026-09-16).

- [x] **XSURF-01**: One certificate produces one finding. A SAML IdP publishing a single certificate
      under two `use` values (`signing`, `encryption`, identical serial) currently yields two
      CRITICAL findings from `quirk/dashboard/api/routes/scan.py:480-498`, inflating the cap input
      and accounting for the whole 19-vs-15 gap. Either dedupe on `(host, port, cert serial)` or
      keep both rows with accurate distinct titles — the choice is recorded as a decision before any
      code changes. The `use=encryption` row's title must stop saying "signing" either way.
      Confirmed live on a freshly-rebuilt `multihost` re-run (plan 210-06, 2026-09-28): the
      dual-`use` `mh-saml-idp` certificate produced exactly ONE finding, not two.
- [x] **XSURF-02**: A weakness the CLI scores is a weakness the CLI reports. `grep SAML` over
      `findings-*.json` returns nothing while the same run's `intelligence-*.json` carries
      `identity_saml_weak_signing_ratio: 0.0054`. The evidence path and the finding-emission path
      have diverged; the evidence path is the correct one.
      Confirmed live (plan 210-06, 2026-09-28): `grep SAML` over the same-run
      `findings-20260928-014244.json` returns a matching CRITICAL finding for the non-zero
      `identity_saml_weak_signing_ratio: 0.0013` in the paired `intelligence-20260928-014244.json`.
- [x] **XSURF-03**: The dashboard's "latest scan" is one scan. `SESSION_BRACKET = 5min`
      (`routes/scan.py`, mirrored `quirk/merge/scan.py:31`) resolves the no-`scan_id` branch by time
      window with no `scan_run_id` filter, merging runs 4m26s apart into 34 certificates (17×2) and
      14 CRITICAL. The window is **load-bearing for legacy NULL-`scan_run_id` rows** — narrow it
      without orphaning that data, and read `get_latest_scan`'s docstring before changing it.
- [x] **XSURF-04**: A regression that reintroduces cross-surface divergence fails a gate. A test
      asserts the report pipeline and the dashboard pipeline emit the same headline score, the same
      CRITICAL count and the same certificate count for one `scan_run_id` — the four-surface
      equality `LIFT-05` claims for score-lift, extended to the headline number.

### Denominator Correctness

Every ratio penalty divides by `totals.endpoints` — a **probe count** — rather than the population
its own numerator is drawn from. Measured on a deliberately vulnerable 31-host estate: 5 CRITICAL,
14 HIGH, **5 of 17 certificates expired**, Identity scored **25/25**, headline **91/100**. Four
successive rounds of adding real detected vulnerabilities moved every subscore by exactly zero.
Source: `todos/pending/readiness-score-denominator-is-probe-count-not-assessable-endpoints.md`,
tracked as `999.113` at P1 in HORIZON's Open-Item Ledger.

- [x] **DENOM-01**: A written denominator decision exists before any denominator changes, recorded in
      `.planning/decisions/`. It states, per ratio family, which population is the correct divisor
      and why — certificate ratios over `certs_observed`, endpoint ratios over the assessable count —
      and it is reached **by measurement against the calibration ladder, not by argument** (999.113
      D5). One of the two current readings has to be wrong; the decision says which.
      **MARKED COMPLETE 2026-09-28 (Phase 211, by citation to a PRIOR commit, not by new Phase 211
      work).** `.planning/decisions/999.113-denominator-semantics.md` is DECIDED 2026-09-13 and was
      committed tracked in `1804d703` (Phase 211's own re-scope commit, 2026-09-28) — `git
      ls-files --error-unmatch` confirms tracked. Satisfied entirely by pre-Phase-211 work; this
      milestone did not re-derive or re-argue the decision.
- [x] **DENOM-02**: Certificate ratios divide by certificates. Applies to the expired / expiring /
      self-signed family. **CORRECTED 2026-09-28, MARKED COMPLETE 2026-09-28 (Phase 211, by citation
      to a PRIOR commit plus live re-measurement) — this requirement's arithmetic was written against
      a stale tree and the implementation has ALREADY LANDED.** `cert_denom = certs_observed` is live
      at `quirk/intelligence/scoring.py:404`, shipped in `0b0ed1c7` (2026-09-13, an ancestor of
      HEAD), two weeks before this milestone was defined. Gated by
      `tests/test_score_denominator_999_113.py` (3 passed, re-run 211-01). The original text claimed
      `identity_expired_ratio` "currently computes `-(5/370) × 14.0`" and would become
      `-(5/17) × 14.0 = -4.12`, moving Identity 25 → ~19. All four numbers are stale. Live
      measurement (`quirk-output/intelligence-20260928-014244.json`, Phase 210's re-run, re-derived
      211-01): `certs_observed = 20`, `expired_count = 5`, `assessable_endpoint_count = 216`,
      `totals.endpoints = 775` — so the live computation is `-(5/20) × 14.0 = -3.50`, the pre-fix
      value would have been `-(5/775) × 14.0 = -0.090`, and Identity already scores **9/25** (Phase
      210's SAML fixes made it emit). Phase 211 proves satisfaction by citation + live measurement
      rather than re-implementing working code.
- [x] **DENOM-03**: Endpoint ratios divide by assessable endpoints, not probes. **ALREADY LANDED for
      the unit clause — corrected 2026-09-28. Behavioural clause MEASURED LIVE 2026-09-28 (Phase
      211-05) and MARKED COMPLETE.** `endpoint_denom = evidence.get("assessable_endpoint_count",
      endpoints)` and `domain_denom = endpoint_denom` are live at
      `quirk/intelligence/scoring.py:412`/`:421`; the only remaining mentions of `totals.endpoints`
      in that file are comments explaining it is deliberately NOT used. Gated by
      `tests/test_score_denominator_999_113.py` (3 passed). **Behavioural clause**: the live
      wide-vs-narrow `ports_tls` measurement (`211-05-SUMMARY.md`,
      `211-LIVE-MEASUREMENT.md`) — 14-port `scan_run_id 2026-09-28T13:16:55.319715+00:00` = 18/100
      vs 2-port `scan_run_id 2026-09-28T13:21:30.232752+00:00` = 20/100 — is **INVERTED** relative to
      the historical pair this requirement cites (91 vs 89 on a 10-port vs 2-port comparison,
      `999.113-denominator-semantics.md:86`): historically widening RAISED the score by 2; live,
      widening LOWERS the score by 2. This requirement's own literal text accepts either "inverts or
      flattens" as satisfaction — INVERTED is the measured outcome, so this requirement is
      discharged by that live measurement, not assumed from the landed unit-clause fix alone.
- [x] **DENOM-04**: The change is red-proved and the ladder re-measured. A known scan moves in the
      **predicted** direction before the fix is accepted; all five calibration rungs are re-measured;
      CBOM golden fixtures and `score-strings.json` are regenerated (both generator-drift-gated); and
      `_apply_weighted_impacts`' 25-point clamp is checked for saturation now that penalties are
      larger. **MARKED COMPLETE 2026-09-28 (Phase 211-01, `211-DENOM-EVIDENCE.md`), all four
      sub-items dispositioned by measurement, ONE with a stated deviation from the criterion's
      literal text:**
      1. **Ladder re-measured**: `24 passed, 3 xfailed` (`tests/test_score_properties.py`). The 3
         xfails are the same parametrized node (`test_p2b_score_does_not_improve_by_observing_more_
         healthy_endpoints`), confirmed denominator-related but a DIFFERENT denominator
         (`assessable_endpoint_count` dilution, not this requirement's `totals.endpoints` defect),
         owned by Phase 212's DILUTE-01 — not a DENOM-04 gap.
      2. **CBOM golden fixtures + `score-strings.json`: DEVIATION — dispositioned N/A with evidence,
         deliberately NOT regenerated.** The criterion's literal text says "regenerated"; measurement
         found neither artifact encodes any score/ratio/denom key (`211-DENOM-EVIDENCE.md`), so
         regenerating either would be ceremony with no content change. `test_score_strings_freshness.py`
         green (5 passed) confirms no drift was introduced by leaving them untouched.
      3. **Clamp saturation measured and locked**: `tests/test_score_clamp_property.py::
         test_agility_ceiling_saturates_on_reference_estate` (211-01) — Agility saturates at the
         25-point ceiling (pre-clamp 36.5918, +11.59 absorbed), no category floors at 0, Hygiene/
         Modern TLS sit clear of either clamp boundary (locking the clamp out as an explanation for
         the separate 17-vs-18 divergence). Red-proofed live (cap raised 25.0→40.0, both tests went
         RED, reverted, confirmed clean).
      4. **Red-proof discipline**: already satisfied by the denominator fix's own red-proof pair
         `a49c7dd6`→`9fadfaa2` (both resolve as commits, predating this milestone). This phase's OWN
         red-proof obligation — for the SEPARATE 17-vs-18 fix — was performed independently in
         211-02/211-03 (sed/Edit-based single-line reverts, both reproducing the original failure
         shape exactly).

### Score Dilution — Decision Only

Adding **only healthy** endpoints still raises the computed score (71 → 82 across a 14× dilution).
999.115's `_consequence_ceiling()` masks this to an emitted 18 → 20, which reads almost like a fix
and is not one — the dilution still computes, and surfaces at full size on any estate the ceiling
does not bind, i.e. exactly the healthier clients. Source:
`todos/pending/p2b-healthy-endpoints-dilute-the-readiness-score.md` (P1).

- [x] **DILUTE-01**: A spike produces a written, measured denominator decision for P2b — and no
      implementation. The three candidates (distinct hosts / an absolute exposure term / scan-scope
      normalisation) are **unvalidated**, so this milestone decides and defers rather than guessing.
      The spike reuses the existing ladder harness in `tests/test_score_properties.py`, verifies the
      control reproduces the baseline before trusting any row, and **must not weaken
      `test_p2b_...`'s pre-ceiling assertion** — that assertion exists precisely so the ceiling
      cannot hide the defect from its own test.
      **Complete (Phase 212, 2026-09-28):** `.planning/decisions/212-score-dilution-denominator-decision.md`
      is DECIDED — verdict `RECOMMEND NONE`, all three candidates measured on both axes against a
      re-verified control. **This closes the DECISION only — it does NOT close the underlying
      defect.** `test_p2b_score_does_not_improve_by_observing_more_healthy_endpoints` remains
      `xfail(strict=True)`, `git status --porcelain -- quirk/ tests/` is empty, and the decision
      names a post-v5.25, OPERATOR-RESERVED owner phase (explicitly not Phase 214) for any future
      implementation attempt. A later reader must not mistake this checkbox for the dilution being
      fixed.

### Shipped Product Defects (series 7)

v5.24's audit recorded these rather than absorbing them. Both are `docs/UAT-SERIES.md` FAILs shipped
into a closed milestone.

- [x] **UIFIX-01**: The certificates table sorts by expiry. `certificates.tsx` has no sort state, no
      column handler and no table library across 116 lines, which is why `UAT-7-12` is an accepted
      product-absence FAIL and why COV-04 closed at 27 of 28. Size S; the pattern is a direct port
      from a page already running it. Flips `UAT-7-12` and closes COV-04's remainder.
      **Complete (Phase 213, plan 213-03, closed by plan 213-10 2026-09-28)** — `certificates.tsx`
      gained a TanStack `accessorFn`-on-parsed-`Date` sortable Expiry column, ported from
      `findings.tsx`/`identity.tsx`; 5 vitest nodes in `certificates-expiry-sort.test.tsx` plus
      operator browser confirmation (plan 213-09). `UAT-7-12` PASS in `docs/UAT-SERIES.md`.
      COV-04's remainder is NOT closed as a `docs/uat-coverage-gaps.md` figure — see criterion 2's
      NOT MET AS WRITTEN finding in `.planning/ROADMAP.md`'s Phase 213 entry; the underlying product
      absence that caused the 27-of-28 tally IS fixed.
- [x] **UIFIX-02**: Dashboard colours come from theme tokens. Hardcoded colour literals bypass the
      tokens and break theming, recorded via a full-strength `it.fails` as `UAT-7-21`. **Re-derive
      the count first:** the todo says 50 literals across 8 files, the v5.24 audit says 95 across 9.
      The disagreement is itself a finding — report which is right and by what instrument, and do not
      inherit either number. The three Cytoscape call sites are a real refactor, not a sed.
      **Complete (Phases 213-01 through 213-08, closed by plan 213-10 2026-09-28)** — v5.24 audit's
      "95 across 9" was CORRECT against the narrow detector; the todo's "50 across 8" was REFUTED.
      A further finding surfaced at planning time (D-14): the narrow detector itself had a blind
      spot (Tailwind underscore-HSL, comma-HSL) the size of the defect it reported. TRUE pre-fix
      total, re-derived four independent ways: **205 literals across 17 files.** All 205 tokenised;
      the widened gate proved genuinely RED before the fix and reports `1 passed` honestly after
      (0 remaining). All three Cytoscape call sites refactored via a shared literal-free theme
      resolver with live re-resolution on toggle, confirmed rendering correctly in both themes by
      the operator (plan 213-09). `UAT-7-21` PASS (qualified — two Pass Criteria bullets remain
      named as uncovered by any instrument) in `docs/UAT-SERIES.md`.

### Release Cut

`pyproject.toml` reads **5.21.0**, the latest tag is **v5.21.0**, and `CHANGELOG.md` carries ~100
lines under `## [Unreleased]` spanning v5.22, v5.23 and v5.24. The `999.109` workflow blocker is
**already discharged on `main`** — `release.yml:293` composes the body from CHANGELOG and `:436`
consumes it via `body_path`; the static `body:` is gone and `:343` hard-fails when the version's
`## [x.y.z]` section is missing. What remains is an actual release, never yet proven on a live tag.

- [x] **REL-01**: `CHANGELOG.md` carries a real `## [5.25.0]` section. `[Unreleased]` is promoted and
      the entry honestly describes three milestones of work, not one. The composer hard-fails without
      this section, so it is a precondition and not a courtesy.
      **COMPLETE (Phase 214, 214-02; commit `de9f2e2a`).** `CHANGELOG.md:10` carries
      `## [5.25.0] - 2026-09-28` — exactly one such heading, with exactly one `## [Unreleased]`
      heading above it and that one empty. Every bullet traces to a real `file:line` via
      `.planning/phases/214-release-cut/214-CHANGELOG-SOURCING.md` (18 sourced rows). The composer's
      extraction was proven locally (206 lines captured) **and red-proved** against a
      `## [v5.25.0]` mutant that correctly produced NO MATCH, then proven live by the
      `workflow_dispatch` dry run's green compose step (`214-DRYRUN-EVIDENCE.md`).
      **Deviation, deliberate:** the entry describes **four** milestones (v5.22, v5.23, v5.24,
      v5.25), not the "three" written above — no tag was cut after `v5.21.0` (2026-09-10), so v5.25
      is unreleased alongside the other three. Spirit exceeded, letter deviated from, on evidence;
      recorded in `.planning/phases/214-release-cut/214-NOT-MET-AS-WRITTEN.md` § Section B rather
      than quietly satisfied by omitting the fourth milestone.
- [x] **REL-02**: The version string is consistent everywhere it is declared — `pyproject.toml`,
      `README.md`, `docs/UAT-SERIES.md` (UAT-1-02 pass criteria + header) —
      and the editable reinstall is run (`pip install -e . --no-deps`), because
      `importlib.metadata` reads the installed dist rather than `pyproject.toml` and 8
      `tests/test_version.py` tests fail without it (measured live,
      `grep -c "^def test_" tests/test_version.py` = 8; local `pytest tests/test_version.py
      --collect-only -q` reports `7/8 tests collected (1 deselected)` under `pyproject.toml`'s
      `addopts = -m 'not slow'`, CI's `pytest -m ""` runs all 8).
      **CORRECTED (Phase 214, 214-03)** — one file dropped from the bump-surface list above and
      the test count fixed; see the footnote below REL-04 for what changed and why.
      **COMPLETE (Phase 214, 214-04 commits `ee4598af`+`3626a56a`; 214-05 commit `07157599`).**
      All three surfaces read 5.25.0: `pyproject.toml:7`, `README.md:7` (H1) with `## What's New in
      v5.25` rewritten across four milestones, and `docs/UAT-SERIES.md` header + `UAT-1-02` pass
      criteria. `.venv/bin/pip install -e . --no-deps` was run (`Successfully installed
      quirk-scanner-5.25.0`), and three independent post-reinstall readings agree — `pip show`,
      `quirk.__version__`, and `quirk --version` → `QU.I.R.K. v5.25.0`. `214-BASELINE.md` recorded
      all three at `5.21.0` beforehand, so this is a before/after pair, not a tautology.
      **The version-parity gate is reported at its measured size, not as "4 tests":**
      `.venv/bin/pytest tests/test_version.py -q` → **`7 passed, 1 deselected, 2 warnings in
      0.35s`** (8 test functions; `addopts = -m 'not slow'` deselects one locally; CI's
      `pytest -m ""` collects all 8). `docs/getting-started.md` deliberately untouched — it carries
      no version string.
- [ ] **REL-03**: A published release carries its own release notes. The composer is proven on a
      **real tag push** — it has only ever run on `workflow_dispatch` dry-runs — and the resulting
      GitHub release body contains the 5.25.0 CHANGELOG section above the unsigned-binary notice.
      **No test tags**: `release.yml` fires on `v[0-9]*` and publishes to PyPI (Phase 187).
      **PENDING — operator-reserved.** Left unchecked on purpose at Phase 214's close. The version
      cut is an operator decision (see § Constraints below, and `214-CONTEXT.md`'s
      "DO NOT PUSH THE TAG", taken at discuss). Phase 214 delivered the strongest evidence
      obtainable without a tag and stopped: `workflow_dispatch` run `36490856185` at
      `793ae987c948bee51d6032ce0f92c81b335af3cd` composed a body whose `## [5.25.0]` heading sits at
      line **1** and the unsigned-binary notice at line **209**, byte-identical (`cmp` IDENTICAL,
      sha256 `6fc7c8eb50a0…`) to a local re-extraction from `git show origin/main:CHANGELOG.md`.
      That is **PARTIAL** and is not this requirement: the `publish` job and the Attach-zip step
      both read `skipped`, `gh release view v5.25.0` → `release not found`, PyPI (queried directly,
      independent of `gh`) still serves `5.21.0`, no `v5.25*` tag exists locally or on `origin`
      (with a `v5.21*` positive control returning 2 refs), and `release.yml:436`'s `body_path`
      consumption path is untested because no dry run can reach it. **A green dry run is not a
      publish.** Full record, verdict and operator handoff:
      `.planning/phases/214-release-cut/214-NOT-MET-AS-WRITTEN.md` § Section A.
- [x] **REL-04**: The 7 public releases carrying Windows-sensor boilerplate are backfilled —
      v5.7.0, v5.8.0, v5.12.0, v5.15.0, v5.18.0, v5.19.0, v5.21.0. `v5.11.0` already has a proper
      custom body and is left alone. **Back up the current bodies first**; they are not recoverable
      from GitHub once overwritten.
      **COMPLETE (Phase 214, 214-03) — the end state already held before the phase began, and no
      release body was edited.** Two independent instruments (`gh release view --json body` per tag,
      and `gh api .../releases --paginate`) agree that all 7 tags named above already carry their
      own `## [x.y.z]` CHANGELOG body; see
      `.planning/phases/214-release-cut/214-REL04-EVIDENCE.md` for the per-tag first lines. Zero
      GitHub write verbs were run, so the "back up first" instruction had nothing to protect —
      nothing needed overwriting. The genuinely-boilerplate set is a **different**, larger one (8
      pre-v5.7 tags at 1153 bytes, first line `## Windows Sensor Asset`: `v5.5.1`, `v5.5.2`,
      `v5.5.2.1`–`.5`, `v5.6.0`), outside this requirement's stated 7 and **filed, not actioned**,
      as backlog `999.116` (`.planning/backlog/999.116-boilerplate-release-bodies-pre-v5.7/`).

**Footnote (Phase 214, 214-03) — REL-02 correction:** the REL-02 bullet above previously also
listed `docs/getting-started.md` in the bump-surface file set. That file carries no version
string — only a `(v5.23+)` feature marker at line 202 (`grep -n "5\.2[0-9]"` on that file returns
exactly that one line, live-verified 2026-09-28) — and `ROADMAP.md` criterion 2 already excluded
it, so the bullet's file list was dropped down to `pyproject.toml`, `README.md`,
`docs/UAT-SERIES.md`. The bullet also previously said "four" `tests/test_version.py` tests;
`grep -c "^def test_" tests/test_version.py` measures 8, and a local
`pytest tests/test_version.py --collect-only -q` reports `7/8 tests collected (1 deselected)`
under `pyproject.toml`'s `addopts = -m 'not slow'` (CI's `pytest -m ""` runs all 8) — corrected to
the measured figure; the original "four" was copied forward without running the command.
**Also corrects the same claim in this repo's `CLAUDE.md` Per-Phase Documentation Checklist,
which listed the same file for the same reason and was fixed in the same phase.**

**Footnote (Phase 214, 214-03) — REL-04 evidence:** live re-confirmation with two independent
instruments (`gh release view --json body`, `gh api .../releases --paginate`) shows all 7 tags
named above already carry their own `## [x.y.z]` CHANGELOG body — see
`.planning/phases/214-release-cut/214-REL04-EVIDENCE.md`. No release body was edited by Phase
214; nothing above needed backing up because nothing needed overwriting.

---

## v2 Requirements (deferred, not dropped)

### Score model

- **P2b implementation** — deferred by design. `DILUTE-01` produces the decision; the implementation
  re-scores every ladder rung and belongs in its own phase with its own measurement pass.
- **999.112** — LIFT-05's four-surface numeric-equality guarantee holds only for *unmodified* report
  templates; RPT-02's operator override is a full-file override.
- **`score-drivers-leak-from-domains-excluded-from-the-headline`** — LATENT, unreachable from today's
  producer; medium only because the thing preventing it is an incidental coupling nothing pins.
- **`999.113-domain-connector-ratio-denominator-is-approximate`** — a narrower residual after
  `DENOM-*`, explicitly not P1.
- **`r5-ladder-fixture-is-not-the-measurement-it-claims`** — re-read this before `DILUTE-01`'s spike
  trusts the R5 rung.

### Carried, unchanged

- `999.104` CLI ↔ dashboard field parity (65 of 121 operator-settable fields uncovered).
- `999.110` multi-host chaos-lab topology; `999.107` operator-declared reachability + crown jewels;
  `999.105` customizable reporting engine; `999.101`/`999.102`; `999.103`; `BACK-68` (broker ports);
  `BACK-01`/`BACK-03`/`BACK-08`.
- Scanner correctness set: kerberos UDP probe timeout, email-scanner host derivation invisibility,
  lifecycle-event unknown-type crash, `finding-item-id` uniqueness.
- Dashboard gap set: CBOM empty state, self-signed flag, roadmap detail panel, storyline drawer,
  a1 copy.
- `hardware-matrix-doc-id-decouple-url-from-identity` (high) — re-sourcing bought one cycle; the
  claims were the real rot.
- The four GSD-toolchain todos — operator machine, not product.

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Net-new detection breadth (Windows AD CS live connector, S/MIME, passive capture) | HORIZON Candidate B explicitly requires a demand signal. There is no engagement asking for any of the three. Breadth for its own sake. |
| Migration Execution (remediation tracking across re-scans) | HORIZON Candidate A. Needs a shaping conversation and carries an unresolved 3× sizing question — QUIRK feature vs Jira/ServiceNow deepening on the Phase 101–105 surface. |
| SaaS multi-tenancy | Parked since v5.4. Gate is a business-model signal, unchanged. |
| P2b implementation | `DILUTE-01` decides; implementing an unvalidated denominator whose blast radius is every ladder rung, in the same milestone as `DENOM-*`, would make both unmeasurable. |
| A `UAT-206-05` qualification-honesty gate | Real gap (18 of 24 COV-04 conversions are QUALIFIED PASSes with no gate policing the text) but it polices v5.24's coverage claims, not this milestone's score claims. Named here so it is deferred rather than forgotten. |
| Fixing the flaky `test_vitest_substitute_nodes_pass` node | Intermittent inside the **required** CI job and measured pre-existing on `main`. It will be met during this milestone and must not be misattributed to a v5.25 PR — but chasing an intermittent is not this milestone's goal. |

---

## Constraints

- **999.113 D5 — never tune to a target.** Fitting to the operator's blind-set calibration bands is
  the ladder's intended use. Adjusting a denominator because a number demos well is not, and the two
  are easy to confuse now that a fitting harness exists. Fixing a genuine double-count (`XSURF-01`)
  is correctness, not tuning — **any plan doing so must state that distinction explicitly** rather
  than leave a reader to infer it.
- **A score that drops because the estate is bad is honest; one that drops because the scorer was
  nudged is not.** Do not "fix" a denominator to make a demo score worse.
- **Never push a test tag.** `release.yml` triggers on `v[0-9]*` and publishes to PyPI. Validation
  before `REL-03` is workflow-syntax plus `workflow_dispatch` dry-run only. The version cut is an
  operator-reserved decision.
- **Re-derive every count with an instrument independent of the thing being counted.** `UIFIX-02`
  ships with two contradicting counts already; `999.109` was carried as open in the canonical ledger
  for two weeks after its fix landed on `main`; HORIZON's `999.114` row still says Phase 206 is
  paused at 5 of 13 when STATE.md records it complete at 13 of 13. A count is a hypothesis.
- **`hw_cve.py` trips its 30-day staleness gate around 2026-10-13**, inside this milestone's likely
  window. Re-verify against the live NVD API and bump the date honestly; never bump to clear a red
  gate.
- **Dashboard changes need an explicit build.** `.tsx` edits require `npm run build` and
  `npm run lint` in `src/dashboard/`; FastAPI serves pre-built statics from
  `quirk/dashboard/static`, which are committed.
- **`phase.complete` remains unsafe on this machine** for closing a phase or milestone (SEMANTIC
  defect class: well-formed wrong values). Hand-verify plan completion before any close.

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| XSURF-01 | Phase 210 | Complete |
| XSURF-02 | Phase 210 | Complete |
| XSURF-03 | Phase 210 | Complete |
| XSURF-04 | Phase 210 | Complete |
| DENOM-01 | Phase 211 | Complete (satisfied by prior commit `1804d703`, decision DECIDED 2026-09-13) |
| DENOM-02 | Phase 211 | Complete (prior commit `0b0ed1c7` + live measurement 211-01) |
| DENOM-03 | Phase 211 | Complete (unit clause prior `0b0ed1c7`; behavioural clause measured INVERTED, live 211-05) |
| DENOM-04 | Phase 211 | Complete (4 sub-items dispositioned 211-01; fixtures/score-strings N/A-dispositioned, not regenerated — deviation from literal text) |
| DILUTE-01 | Phase 212 | Complete (decision only — RECOMMEND NONE; defect still xfails) |
| UIFIX-01 | Phase 213 | Complete (`UAT-7-12` PASS; COV-04's 27-of-28 artifact-level closure recorded NOT MET AS WRITTEN — see ROADMAP.md Phase 213 entry) |
| UIFIX-02 | Phase 213 | Complete (true pre-fix count 205 across 17 files, not 95 across 9; `UAT-7-21` PASS qualified) |
| REL-01 | Phase 214 | Complete (`de9f2e2a`; one `## [5.25.0]`, composer red-proved then dry-run-proved — entry describes FOUR milestones not three, a deliberate evidenced deviation, see 214-NOT-MET-AS-WRITTEN.md § B) |
| REL-02 | Phase 214 | Complete (`ee4598af`+`3626a56a`+`07157599`; 3 surfaces at 5.25.0, editable reinstall run, 3 independent readings agree, gate `7 passed, 1 deselected` — 8 functions, not the stale "4") |
| REL-03 | Phase 214 | **PENDING — operator-reserved** (dry run `36490856185` is PARTIAL only: publish job + attach step both `skipped`, no Release object, PyPI still 5.21.0, no `v5.25` tag; criterion 3 recorded NOT MET AS WRITTEN — see 214-NOT-MET-AS-WRITTEN.md § A) |
| REL-04 | Phase 214 | Complete (two-instrument live evidence, `214-REL04-EVIDENCE.md`; end state already held pre-phase, zero GitHub write verbs, nothing backed up because nothing overwritten; the different 8-release pre-v5.7 set filed as backlog `999.116`) |

---
*Requirements defined: 2026-09-27*
