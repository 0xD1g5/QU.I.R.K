---
milestone: v5.25
milestone_name: Score Truth & Release Cut
phases_total: 5
phase_range: 210-214
---

# Roadmap: v5.25 Score Truth & Release Cut

**Goal:** Make the readiness score mean one thing on every surface a client can see, then ship it —
the first tagged release since v5.21, carrying three milestones of accumulated work.

**Sequencing (operator decision 2026-09-27): score first, release last.** A tag freezes whatever
number the scorer emits, so Phase 214 (`REL-*`) runs after every scoring phase lands. Phase numbering
continues from v5.24's last phase (209) — v5.25 starts at **Phase 210**.

No research phase — every requirement traces to a filed todo or backlog item with a CONFIRMED root
cause at an exact file:line. This milestone adds no new detection capability.

---

## Phases

- [ ] **Phase 210: Cross-Surface Score Parity** - One scan yields the same headline score, CRITICAL
  count and certificate count from the report pipeline and the dashboard pipeline. **All 8 plans
  done, all 4 requirements Complete; left unchecked because the phase's own stated goal is only
  PARTIALLY achieved** — CRITICAL count and certificate count now match exactly, but the headline
  score still diverges by 1 point (Success Criterion 5 NOT MET). See 210-08-SUMMARY.md.
  **UPDATE 2026-09-28 — Criterion 5 is now SATISFIED, by Phase 211's work, not by Phase 210's.**
  Live measurement `scan_run_id 2026-09-28T13:16:55.319715+00:00`: report 18/100 == dashboard
  18/100, all six subscores matching. Root cause was a finding-title vocabulary mismatch plus a
  LOW-severity-proxy structural zero, fixed in `127913ca` and `c1245a55`. This box is left
  UNCHECKED deliberately: the provenance matters, and whether to check it is a milestone-close
  decision for the operator. See `.planning/decisions/211-cross-surface-finding-vocabulary-is-a-scoring-input.md`.
- [x] **Phase 211: Denominator Correctness** - Every ratio penalty divides by the population its
  numerator is drawn from, decided by measurement against the calibration ladder and re-proved red
  before acceptance. **RE-SCOPED to verify + investigate (`1804d703`)** — DENOM-01/02/03 had already
  landed via `0b0ed1c7` (2026-09-13). 8 of 8 plans; `211-VERIFICATION.md` status **passed**, 8/8
  must-haves, goal-level and requirement-level verdicts AGREE. Closed Phase 210's unmet Criterion 5
  (18/100 == 18/100 live). DENOM-03's behavioural clause measured **INVERTED** (narrow 2-port 20/100
  vs wide 14-port 18/100) — Phase 212 owns whether width-neutrality is the target. One residual
  disclosed, NOT tag-blocking: `"HTTP on TLS-designated port"` is unbridgeable and measures 0 on the
  reference estate.
- [ ] **Phase 212: Score Dilution — Decision Only** - A written, measured denominator decision for
  P2b exists; no implementation ships.
- [ ] **Phase 213: Shipped Product Defects (Series 7)** - The two shipped `docs/UAT-SERIES.md` FAILs
  from v5.24 — certificate-table sort and theme-token colour literals — are fixed.
- [ ] **Phase 214: Release Cut** - `v5.25.0` is tagged, published to PyPI, and its release notes and
  the 7 backlogged release bodies are real.

---

## Phase Details

### Phase 210: Cross-Surface Score Parity
**Goal**: One scan produces the same headline score, CRITICAL count, and certificate count whether a
client receives it from the report pipeline or the dashboard pipeline.
**Depends on**: Nothing (first phase of the milestone)
**Requirements**: XSURF-01, XSURF-02, XSURF-03, XSURF-04
**Success Criteria** (what must be TRUE):
  1. A written decision (recorded in `.planning/decisions/`) states whether the SAML dual-`use`
     certificate case (`quirk/dashboard/api/routes/scan.py:480-498`) dedupes on
     `(host, port, cert serial)` or keeps both rows with accurate distinct titles, decided before any
     code changes; whichever is chosen, the `use=encryption` row no longer says "signing".
  2. `grep SAML` over a fresh run's `findings-*.json` returns a matching finding for every non-zero
     `identity_saml_weak_signing_ratio` in that same run's `intelligence-*.json` — the evidence path
     and the finding-emission path agree instead of diverging.
  3. The dashboard's no-`scan_id` "latest scan" branch resolves two runs 4m26s apart to one
     `scan_run_id`'s data (not the previous merged 34 certificates / 14 CRITICAL), while legacy
     NULL-`scan_run_id` rows remain reachable exactly as `get_latest_scan`'s docstring describes.
  4. A regression test asserts, for one `scan_run_id`, equal headline score, equal CRITICAL count and
     equal certificate count between the report pipeline and
     `GET /api/scan/latest?scan_id=` — and is shown to fail when a deliberately reintroduced
     double-count is present (the LIFT-05 four-surface-equality shape, extended to the headline
     number).
  5. The original reproducing scan — 15/100 + 5 CRITICAL from the report pipeline vs 19/100 + 7
     CRITICAL from the dashboard pipeline — is re-run and both pipelines now report the identical
     number.
  6. The two docs that currently document the divergence as EXPECTED behaviour are corrected in the
     same phase: `docs/report-interpretation.md` §26 (`:1988`, "Export PDF is not the same thing as
     these downloads") and `docs/operators-guide.md` §3.1.7 (`:419`). Both are synced to their vault
     counterparts under `20_Dev-Work/QUIRK/Guides/` per LIVE-03 — `Report-Interpretation.md` and
     `Operators-Guide.md`, vault `Digs` — and `docs/quirk-master-guide.md` is regenerated, since
     `operators-guide.md` is one of its five generator inputs and
     `tests/test_master_guide_freshness.py` gates the committed artifact byte-for-byte.
**Plans**: 8 plans in 6 waves

Plans:
**Wave 1**

- [x] 210-01-PLAN.md — XSURF-01 written decision, decision-only, before any code change (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 210-02-PLAN.md — extract evaluate_identity_endpoints() with the (host, port, serial) dedupe; route becomes a caller; CLI composition (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 210-03-PLAN.md — dedupe evidence.py's independent saml_weak_signing_count (wave 3)
- [x] 210-04-PLAN.md — resolve latest-scan by scan_run_id, window as NULL-only fallback; two stale comments corrected (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 210-05-PLAN.md — XSURF-04 three-number parity gate plus the required falsification (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 210-06-PLAN.md — live multihost re-run recording both pipelines' numbers (wave 5, non-autonomous) — evidence captured; Success Criterion 5 NOT fully met (residual 1-point score divergence, see 210-06-SUMMARY.md and filed todo)
- [x] 210-07-PLAN.md — doc retarget per D-20, master-guide regeneration, vault sync (wave 5)

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 210-08-PLAN.md — UAT-SERIES.md, Obsidian phase note, ground-truth completion check (wave 6)

### Phase 211: Denominator Correctness
**Goal**: Every ratio penalty in the readiness score divides by the population its own numerator is
drawn from, not by a probe count, and the change is proved to move a known scan in the predicted
direction before it is accepted.
**Depends on**: Phase 210. NOT independent, though it looks it: XSURF-03 stops `SESSION_BRACKET`
merging runs, which returns the certificate count from 34 to 17 — and DENOM-02 makes `certs_observed`
the *divisor* for every certificate ratio. Landing both independently moves that divisor for two
unrelated reasons at once, and DENOM-04's red-proof requires a *predicted* direction, which cannot be
predicted through two simultaneous changes to the same denominator. (Checked and ruled out as the
coupling: the consequence ceiling does NOT move — `DEEP_CRITICAL_COUNT = 5` and the reference estate
goes 5 -> 6 CRITICAL, both `>= 5`; `cap_band_for_severity` has no graduated N-CRITICAL ladder; and the
`high_impact` / `agility_high_impact_ratio` path that would have moved the number was removed by
999.115, `scoring.py:424,449`.)
**Requirements**: DENOM-01, DENOM-02, DENOM-03, DENOM-04
**RE-SCOPED 2026-09-28 (operator decision).** A live source audit before planning found this phase's
core implementation already on `main`: `0b0ed1c7` (2026-09-13) made every ratio divide by its own
population, with a red-proof pair (`a49c7dd6` -> `9fadfaa2`), a 152-line gate
(`tests/test_score_denominator_999_113.py`, 3 passed), a DECIDED decision record
(`.planning/decisions/999.113-denominator-semantics.md`, untracked) and a post-fix ladder
re-measurement (rungs dated 2026-09-14, `tests/test_score_properties.py` green). The phase therefore
delivers: proof-with-citations that DENOM-01/02/03 are satisfied; the decision doc committed;
DENOM-04's genuine residual (clamp saturation, golden/score-strings coupling, the 3 xfailed ladder
nodes); correction of the stale arithmetic below; and **the real open defect — Phase 210's residual
17-vs-18 headline-score divergence, isolated to Hygiene and Modern TLS, whose "denominator" cause is
now REFUTED and needs measuring.**
**Success Criteria** (what must be TRUE):
  1. `.planning/decisions/` contains a DENOM-01 decision document, reached by measurement against the
     calibration ladder (never by argument, per 999.113 D5), stating per ratio family which
     population is the correct divisor — certificate ratios over `certs_observed`, endpoint ratios
     over the assessable-endpoint count — and citing the measured ladder rows that produced it.
     **MET, by citation to a PRIOR commit — measured 2026-09-28.** `.planning/decisions/
     999.113-denominator-semantics.md` is DECIDED 2026-09-13 and tracked (committed in `1804d703`,
     Phase 211's own re-scope commit). `git ls-files --error-unmatch` confirms.
  2. **CORRECTED 2026-09-28 — the original prediction was measured against a stale tree. MET, by
     citation + live measurement — re-confirmed 2026-09-28 (211-01).** The
     `cert_denom = certs_observed` change ALREADY LANDED in `0b0ed1c7` (2026-09-13, ancestor of
     HEAD), so this criterion is discharged by citation + live measurement, not by new code. The
     original text predicted Identity moving 25/25 -> ~19/25 via `-(5/17) × 14.0 ≈ -4.12`, replacing
     `-(5/370) × 14.0`. Live (`quirk-output/intelligence-20260928-014244.json`, re-derived 211-01):
     `certs_observed` is **20** not 17, `assessable_endpoint_count` is **216** and `totals.endpoints`
     **775** not 370 — so the live term is `-(5/20) × 14.0 = -3.50` and Identity already scores
     **9/25**, not 25/25 (Phase 210's SAML fixes made it emit). The measured numbers are recorded
     here in place of the original -4.12 prediction, per this criterion's own instruction.
  3. **ALREADY SATISFIED for the first clause — corrected 2026-09-28. MET in full, both clauses —
     live-measured 2026-09-28 (211-05).** `endpoint_denom` and `domain_denom` already read
     `assessable_endpoint_count`, not `totals.endpoints` (`quirk/intelligence/scoring.py:412`/`:421`,
     gated by `tests/test_score_denominator_999_113.py`, 3 passed). **Behavioural clause, measured
     live rather than assumed**: a fresh multihost scan at the wide, committed `ports_tls` width (14
     ports, `scan_run_id 2026-09-28T13:16:55.319715+00:00`) scored **18/100**; the identical
     infrastructure re-scanned at a narrow 2-port width (`[443,993]`,
     `scan_run_id 2026-09-28T13:21:30.232752+00:00`) scored **20/100**. Relative to the historical
     pair this criterion cites (10-port=91 vs 2-port=89, `999.113-denominator-semantics.md:86` —
     widening RAISED the score by 2), the live pair **INVERTED**: widening now LOWERS the score by
     2. This is neither the historical direction nor a flat/noise result (the underlying pre-cap
     computed sums differ by 7: 78 vs 71) — it satisfies this criterion's own literal "inverts or
     flattens" acceptance test via the "inverts" branch. Full evidence:
     `211-LIVE-MEASUREMENT.md`.
  4. A known scan is red-proved to move in the predicted direction before the fix is accepted, all
     five calibration ladder rungs are re-measured, CBOM golden fixtures and `score-strings.json` are
     regenerated and pass their generator-drift gates, and `_apply_weighted_impacts`'s 25-point clamp
     is checked for saturation now that penalties are larger.
     **MET with ONE STATED DEVIATION — measured 2026-09-28 (211-01).** (a) Red-proof: already
     performed for the denominator change itself at `a49c7dd6`→`9fadfaa2` (both resolve as commits,
     predate this milestone). (b) Ladder: `24 passed, 3 xfailed`
     (`tests/test_score_properties.py`); the 3 xfails are the Phase-212-owned `test_p2b_...`
     dilution node, not a DENOM-04 gap. **(c) DEVIATION: CBOM golden fixtures and
     `score-strings.json` were NOT regenerated — dispositioned N/A with evidence instead.**
     Measurement found neither artifact encodes any score/ratio/denom key, so this criterion's
     literal "regenerated" instruction does not apply; `test_score_strings_freshness.py` stayed
     green (5 passed) throughout, confirming no drift was introduced by leaving them untouched. (d)
     Clamp saturation: measured and locked (`tests/test_score_clamp_property.py::
     test_agility_ceiling_saturates_on_reference_estate`) — Agility saturates at the 25-point
     ceiling (+11.59 absorbed), no category floors, Hygiene/Modern TLS sit clear of either boundary.
  **17-vs-18 outcome (the phase's actual centre of gravity, per its RE-SCOPE note above).** Root
  cause: a finding-title vocabulary mismatch (Hygiene, `evidence.py::_finding_targets` matching only
  CLI-canonical title strings against a deliberately independent dashboard vocabulary) plus a
  severity-proxy structural zero (Modern TLS, `legacy_tls_count = sev.get("LOW", 0)`, always 0 on
  the dashboard pipeline, which emits no LOW findings). Fixed in two legs: `211-02` (`127913ca`,
  routes titles through the existing `finding_title_bridge.py` translation) and `211-03`
  (`c1245a55`, derives `legacy_tls_count` from endpoint fields via a new shared predicate). Guarded
  by a run-time source-scan coverage gate (`211-04`, `tests/test_evidence_scoring_title_coverage.py`)
  so the mapping table cannot silently drift. Live verdict: **EQUAL** — report and dashboard both
  18/100 for `scan_run_id 2026-09-28T13:16:55.319715+00:00`, all six subscores matching exactly,
  cross-checked by an independent DB re-derivation (13/13 counters matched). Full decision record:
  `.planning/decisions/211-cross-surface-finding-vocabulary-is-a-scoring-input.md`. One residual —
  `"HTTP on TLS-designated port"` has no dashboard equivalent, measures 0 on the reference estate,
  dispositioned `unbridgeable-latent-divergence`, tag-blocking verdict NO — tracked at
  `.planning/todos/pending/211-http-on-tls-designated-port-has-no-dashboard-equivalent.md`.
**Plans**: 8 plans in 6 waves

Plans:

**Wave 1** *(no dependencies; disjoint files)*

- [x] 211-01-PLAN.md — DENOM-01/02/03 satisfaction record by re-derived citation + DENOM-04's four residual dispositions + clamp ceiling-saturation measured and locked (wave 1)
- [x] 211-02-PLAN.md — 17-vs-18 leg 1: wire `finding_title_bridge` into `evidence.py`'s title-matched counters per operator Decision A, with pinned-oracle parity test proven red (wave 1)

**Wave 2** *(shares `evidence.py` with 211-02)*

- [x] 211-03-PLAN.md — 17-vs-18 leg 2: replace the `sev["LOW"]` severity proxy with an endpoint-derived `legacy_tls_count`; the bridge cannot fix this leg (wave 2)

**Wave 3** *(needs the final title set from waves 1-2)*

- [x] 211-04-PLAN.md — run-time source-scan coverage gate over `evidence.py`'s scoring-critical finding titles + disposition ledger + todo for the unbridgeable latent divergence (wave 3)

**Wave 4** *(one lab raise, shared by both live measurements — operator Decision B)*

- [x] 211-05-PLAN.md — force-rebuild `mh-prober`, raise `multihost`, D-08 cross-surface live comparison + DENOM-03's two-`ports_tls`-width behavioural measurement (wave 4, non-autonomous)

**Wave 5** *(both plans state claims about 211-05's evidence, so both declare an explicit `depends_on` — wave co-membership is not ordering)*

- [x] 211-06-PLAN.md — DECIDED decision record, todo refutation, hand-marked REQUIREMENTS/ROADMAP/STATE with a full-file pre-image diff (wave 5, depends_on 211-01/211-04/211-05)
- [x] 211-07-PLAN.md — `report-interpretation.md` + `operators-guide.md` parity statements and score-contributor disclosure, master-guide regeneration, LIVE-03 vault sync (wave 5, depends_on 211-03/211-05)

**Wave 6**

- [x] 211-08-PLAN.md — UAT Series 211 + coverage-gaps regeneration, Obsidian phase note, VALIDATION map resolution, ground-truth completion check on an ENUMERATED PLAN/SUMMARY set (wave 6)

### Phase 212: Score Dilution — Decision Only
**Goal**: A written, measured denominator decision exists for the P2b healthy-endpoint dilution
defect. No implementation ships in this phase — the defect remains open at close, by design.
**Depends on**: Phase 211 (the spike must measure candidates against a ladder already re-measured
under the corrected DENOM-* denominators, not a stale one)
**Requirements**: DILUTE-01
**Success Criteria** (what must be TRUE):
  1. The spike measures all three candidate denominators (distinct hosts / an absolute exposure term
     / scan-scope normalisation) against the existing ladder harness in
     `tests/test_score_properties.py`, first confirming the control reproduces the unmodified
     baseline before trusting any candidate's row.
  2. A written decision in `.planning/decisions/` names which candidate is recommended for a future
     implementation phase and why, backed by each candidate's measured effect on the reference
     14× dilution case (71 → 82 today, masked to 18 → 20 only by `_consequence_ceiling()`).
  3. `test_p2b_...`'s pre-ceiling assertion is unweakened and still red-detects the 71 → 82 dilution
     independent of the consequence ceiling — the assertion that exists precisely so the ceiling
     cannot hide the defect from its own test.
  4. No production code implementing any candidate denominator ships in this phase. The decision
     document explicitly states the defect is deferred, not fixed, and names the phase where
     implementation belongs.
**Plans**: 5 plans (4 waves)
- [ ] 212-01-PLAN.md — Rebuild the two-axis measurement harness; establish and re-verify the control
- [ ] 212-02-PLAN.md — Measure the two population-swap candidates (scan-scope, distinct hosts) + falsifiability audit
- [ ] 212-03-PLAN.md — Settle and measure the absolute-exposure candidate via a monkeypatched wrapper
- [ ] 212-04-PLAN.md — Write the DILUTE-01 decision document and capture verbatim criterion evidence
- [ ] 212-05-PLAN.md — Close-out: UAT Series 212, coverage-gaps regeneration, vault sync, hand-edited tracking

### Phase 213: Shipped Product Defects (Series 7)
**Goal**: The two product defects v5.24's audit recorded rather than absorbed — both shipped
`docs/UAT-SERIES.md` FAILs — are fixed.
**Depends on**: Nothing (independent of the scoring phases; UI-only work)
**Requirements**: UIFIX-01, UIFIX-02
**Success Criteria** (what must be TRUE):
  1. `certificates.tsx` supports clicking the expiry column header to sort ascending and descending,
     flipping `UAT-7-12` from its accepted product-absence FAIL to PASS in `docs/UAT-SERIES.md`.
  2. COV-04's recorded shortfall closes from 27 of 28 to 28 of 28 in the regenerated
     `docs/uat-coverage-gaps.md`.
  3. The UIFIX-02 colour-literal count is re-derived with an instrument independent of both existing
     estimates (the todo's 50 literals across 8 files; the v5.24 audit's 95 across 9), and the phase
     records which prior estimate was closer and by what method — the disagreement itself is treated
     as a finding, not resolved by picking one number to inherit.
  4. Every hardcoded colour literal found by that re-derived count is replaced with a theme-token
     reference; `npm run build` and `npm run lint` pass clean in `src/dashboard/`, flipping
     `UAT-7-21` from its full-strength `it.fails` FAIL to PASS.
  5. The three Cytoscape call sites render the CBOM graph and the roadmap graph correctly under both
     light and dark theme with zero hardcoded hex/rgb literals remaining in those files — a real
     refactor of the Cytoscape style objects, not a sed pass.
**Plans**: TBD
**UI hint**: yes

### Phase 214: Release Cut
**Goal**: `v5.25.0` is tagged, published to PyPI, and every release-body defect this milestone can
close — the CHANGELOG composer's first live proof and 7 backlogged bodies — is closed.
**Depends on**: Phase 210, Phase 211, Phase 212, Phase 213 (a tag freezes whatever number the scorer
emits and whatever UI state ships — every other phase must land first)
**Requirements**: REL-01, REL-02, REL-03, REL-04
**Success Criteria** (what must be TRUE):
  1. `CHANGELOG.md` carries a real `## [5.25.0]` section — `[Unreleased]`'s ~100 lines spanning
     v5.22, v5.23 and v5.24 are promoted and the entry honestly describes three milestones of work,
     not one — and `release.yml:343`'s hard-fail-on-missing-section check passes for this version.
  2. `pyproject.toml`, `README.md`, and `docs/UAT-SERIES.md` (UAT-1-02 pass criteria + document
     header) all read `5.25.0` after `pip install -e . --no-deps`
     (`importlib.metadata` reads the installed dist, not `pyproject.toml`), and all 4
     `tests/test_version.py` tests pass. `docs/getting-started.md` is deliberately NOT in that list —
     it carries no version string at all, only a `(v5.23+)` feature marker, verified at both the
     v5.24 and v5.25 boundary reviews. Do not add one to satisfy this criterion.
  3. A real `v5.25.0` tag push — never a test tag — produces a GitHub release whose body is composed
     by `release.yml:293`/`:436` from `CHANGELOG.md` and contains the 5.25.0 section above the
     unsigned-binary notice, proven on the actual publish rather than a `workflow_dispatch` dry run.
  4. The 7 public releases carrying Windows-sensor boilerplate (v5.7.0, v5.8.0, v5.12.0, v5.15.0,
     v5.18.0, v5.19.0, v5.21.0) have real, backfilled release notes on GitHub, with their original
     bodies backed up before being overwritten; `v5.11.0` is left untouched.
**Plans**: TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|-----------------|--------|-----------|
| 210. Cross-Surface Score Parity | 8/8 | Partial — 4/4 requirements Complete, Success Criterion 5 (identical headline score) NOT MET, see 210-08-SUMMARY.md | 2026-09-27 |
| 211. Denominator Correctness | 0/? | Not started | - |
| 212. Score Dilution — Decision Only | 0/? | Not started | - |
| 213. Shipped Product Defects (Series 7) | 0/? | Not started | - |
| 214. Release Cut | 0/? | Not started | - |
