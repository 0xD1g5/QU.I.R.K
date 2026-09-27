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
  count and certificate count from the report pipeline and the dashboard pipeline.
- [ ] **Phase 211: Denominator Correctness** - Every ratio penalty divides by the population its
  numerator is drawn from, decided by measurement against the calibration ladder and re-proved red
  before acceptance.
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
**Plans**: TBD

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
**Success Criteria** (what must be TRUE):
  1. `.planning/decisions/` contains a DENOM-01 decision document, reached by measurement against the
     calibration ladder (never by argument, per 999.113 D5), stating per ratio family which
     population is the correct divisor — certificate ratios over `certs_observed`, endpoint ratios
     over the assessable-endpoint count — and citing the measured ladder rows that produced it.
  2. On the 31-host reference estate, `identity_expired_ratio` (weight 14.0) moves Identity from
     25/25 to ~19/25 — computed as `-(5/17) × 14.0 ≈ -4.12` over `certs_observed`, replacing today's
     `-(5/370) × 14.0`, which rounds away entirely.
  3. `endpoint_denom` (`quirk/intelligence/scoring.py:412`) and `domain_denom` (`:421`) and their
     ~20 consumers at `:481-502` no longer read `totals.endpoints`; the 10-port vs 2-port `multihost`
     profile measurement — 91 vs 89 on identical infrastructure today — inverts or flattens.
  4. A known scan is red-proved to move in the predicted direction before the fix is accepted, all
     five calibration ladder rungs are re-measured, CBOM golden fixtures and `score-strings.json` are
     regenerated and pass their generator-drift gates, and `_apply_weighted_impacts`'s 25-point clamp
     is checked for saturation now that penalties are larger.
**Plans**: TBD

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
**Plans**: TBD

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
| 210. Cross-Surface Score Parity | 0/? | Not started | - |
| 211. Denominator Correctness | 0/? | Not started | - |
| 212. Score Dilution — Decision Only | 0/? | Not started | - |
| 213. Shipped Product Defects (Series 7) | 0/? | Not started | - |
| 214. Release Cut | 0/? | Not started | - |
