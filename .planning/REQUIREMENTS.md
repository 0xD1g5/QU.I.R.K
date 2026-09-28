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

- [ ] **XSURF-01**: One certificate produces one finding. A SAML IdP publishing a single certificate
      under two `use` values (`signing`, `encryption`, identical serial) currently yields two
      CRITICAL findings from `quirk/dashboard/api/routes/scan.py:480-498`, inflating the cap input
      and accounting for the whole 19-vs-15 gap. Either dedupe on `(host, port, cert serial)` or
      keep both rows with accurate distinct titles — the choice is recorded as a decision before any
      code changes. The `use=encryption` row's title must stop saying "signing" either way.
- [ ] **XSURF-02**: A weakness the CLI scores is a weakness the CLI reports. `grep SAML` over
      `findings-*.json` returns nothing while the same run's `intelligence-*.json` carries
      `identity_saml_weak_signing_ratio: 0.0054`. The evidence path and the finding-emission path
      have diverged; the evidence path is the correct one.
- [x] **XSURF-03**: The dashboard's "latest scan" is one scan. `SESSION_BRACKET = 5min`
      (`routes/scan.py`, mirrored `quirk/merge/scan.py:31`) resolves the no-`scan_id` branch by time
      window with no `scan_run_id` filter, merging runs 4m26s apart into 34 certificates (17×2) and
      14 CRITICAL. The window is **load-bearing for legacy NULL-`scan_run_id` rows** — narrow it
      without orphaning that data, and read `get_latest_scan`'s docstring before changing it.
- [ ] **XSURF-04**: A regression that reintroduces cross-surface divergence fails a gate. A test
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

- [ ] **DENOM-01**: A written denominator decision exists before any denominator changes, recorded in
      `.planning/decisions/`. It states, per ratio family, which population is the correct divisor
      and why — certificate ratios over `certs_observed`, endpoint ratios over the assessable count —
      and it is reached **by measurement against the calibration ladder, not by argument** (999.113
      D5). One of the two current readings has to be wrong; the decision says which.
- [ ] **DENOM-02**: Certificate ratios divide by certificates. `identity_expired_ratio` (weight 14.0)
      currently computes `-(5/370) × 14.0`, which rounds away entirely; over `certs_observed` it is
      `-(5/17) × 14.0 = -4.12`, moving Identity 25 → ~19 on the reference estate. Applies to the
      expired / expiring / self-signed family.
- [ ] **DENOM-03**: Endpoint ratios divide by assessable endpoints, not probes. `endpoint_denom`
      (`quirk/intelligence/scoring.py:412`) and `domain_denom` (`:421`) and their ~20 consumers at
      `:481-502` stop reading `totals.endpoints`. Widening `ports_tls` must no longer raise a score:
      the 10-port vs 2-port measurement on the `multihost` profile (91 vs 89 on identical
      infrastructure) inverts or flattens.
- [ ] **DENOM-04**: The change is red-proved and the ladder re-measured. A known scan moves in the
      **predicted** direction before the fix is accepted; all five calibration rungs are re-measured;
      CBOM golden fixtures and `score-strings.json` are regenerated (both generator-drift-gated); and
      `_apply_weighted_impacts`' 25-point clamp is checked for saturation now that penalties are
      larger.

### Score Dilution — Decision Only

Adding **only healthy** endpoints still raises the computed score (71 → 82 across a 14× dilution).
999.115's `_consequence_ceiling()` masks this to an emitted 18 → 20, which reads almost like a fix
and is not one — the dilution still computes, and surfaces at full size on any estate the ceiling
does not bind, i.e. exactly the healthier clients. Source:
`todos/pending/p2b-healthy-endpoints-dilute-the-readiness-score.md` (P1).

- [ ] **DILUTE-01**: A spike produces a written, measured denominator decision for P2b — and no
      implementation. The three candidates (distinct hosts / an absolute exposure term / scan-scope
      normalisation) are **unvalidated**, so this milestone decides and defers rather than guessing.
      The spike reuses the existing ladder harness in `tests/test_score_properties.py`, verifies the
      control reproduces the baseline before trusting any row, and **must not weaken
      `test_p2b_...`'s pre-ceiling assertion** — that assertion exists precisely so the ceiling
      cannot hide the defect from its own test.

### Shipped Product Defects (series 7)

v5.24's audit recorded these rather than absorbing them. Both are `docs/UAT-SERIES.md` FAILs shipped
into a closed milestone.

- [ ] **UIFIX-01**: The certificates table sorts by expiry. `certificates.tsx` has no sort state, no
      column handler and no table library across 116 lines, which is why `UAT-7-12` is an accepted
      product-absence FAIL and why COV-04 closed at 27 of 28. Size S; the pattern is a direct port
      from a page already running it. Flips `UAT-7-12` and closes COV-04's remainder.
- [ ] **UIFIX-02**: Dashboard colours come from theme tokens. Hardcoded colour literals bypass the
      tokens and break theming, recorded via a full-strength `it.fails` as `UAT-7-21`. **Re-derive
      the count first:** the todo says 50 literals across 8 files, the v5.24 audit says 95 across 9.
      The disagreement is itself a finding — report which is right and by what instrument, and do not
      inherit either number. The three Cytoscape call sites are a real refactor, not a sed.

### Release Cut

`pyproject.toml` reads **5.21.0**, the latest tag is **v5.21.0**, and `CHANGELOG.md` carries ~100
lines under `## [Unreleased]` spanning v5.22, v5.23 and v5.24. The `999.109` workflow blocker is
**already discharged on `main`** — `release.yml:293` composes the body from CHANGELOG and `:436`
consumes it via `body_path`; the static `body:` is gone and `:343` hard-fails when the version's
`## [x.y.z]` section is missing. What remains is an actual release, never yet proven on a live tag.

- [ ] **REL-01**: `CHANGELOG.md` carries a real `## [5.25.0]` section. `[Unreleased]` is promoted and
      the entry honestly describes three milestones of work, not one. The composer hard-fails without
      this section, so it is a precondition and not a courtesy.
- [ ] **REL-02**: The version string is consistent everywhere it is declared — `pyproject.toml`,
      `README.md`, `docs/getting-started.md`, `docs/UAT-SERIES.md` (UAT-1-02 pass criteria + header) —
      and the editable reinstall is run (`pip install -e . --no-deps`), because
      `importlib.metadata` reads the installed dist rather than `pyproject.toml` and four
      `tests/test_version.py` tests fail without it.
- [ ] **REL-03**: A published release carries its own release notes. The composer is proven on a
      **real tag push** — it has only ever run on `workflow_dispatch` dry-runs — and the resulting
      GitHub release body contains the 5.25.0 CHANGELOG section above the unsigned-binary notice.
      **No test tags**: `release.yml` fires on `v[0-9]*` and publishes to PyPI (Phase 187).
- [ ] **REL-04**: The 7 public releases carrying Windows-sensor boilerplate are backfilled —
      v5.7.0, v5.8.0, v5.12.0, v5.15.0, v5.18.0, v5.19.0, v5.21.0. `v5.11.0` already has a proper
      custom body and is left alone. **Back up the current bodies first**; they are not recoverable
      from GitHub once overwritten.

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
| XSURF-01 | Phase 210 | Pending |
| XSURF-02 | Phase 210 | Pending |
| XSURF-03 | Phase 210 | Complete |
| XSURF-04 | Phase 210 | Pending |
| DENOM-01 | Phase 211 | Pending |
| DENOM-02 | Phase 211 | Pending |
| DENOM-03 | Phase 211 | Pending |
| DENOM-04 | Phase 211 | Pending |
| DILUTE-01 | Phase 212 | Pending |
| UIFIX-01 | Phase 213 | Pending |
| UIFIX-02 | Phase 213 | Pending |
| REL-01 | Phase 214 | Pending |
| REL-02 | Phase 214 | Pending |
| REL-03 | Phase 214 | Pending |
| REL-04 | Phase 214 | Pending |

---
*Requirements defined: 2026-09-27*
