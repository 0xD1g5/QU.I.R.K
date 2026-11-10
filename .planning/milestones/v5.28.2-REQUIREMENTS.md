# Requirements: QU.I.R.K. — v5.28.1 Install & Source-Scan Truth (patch release)

**Defined:** 2026-11-03
**Core Value:** A consulting-grade cryptographic inventory whose findings a consultant can hand to a
client without qualification. That includes every number the tool shows being correct on every
surface that shows it.

**Milestone goal:** Ship a 5.28.1 patch that fixes the two Critical findings the Phase 235 post-GO
review found in the published 5.28.0 package (CR-01, CR-02), along with the release-evidence and
doctor defects from the same review. Then re-check the announcement against 5.28.1, so the social
launch is posted on a release whose known-issues list contains no false-clean result.

**Precedent:** v4.10.1 Scoring Correctness Hotfix (a patch milestone). Phases are numbered 235.1 and
235.2, inserted after Phase 235, so Phase 236 stays reserved for the v5.29 score-divergence
candidate (`999.132`), which two pending todos already cite.

**Deadline constraint:** tag and publish by **2026-11-23**. CMVP's `last_verified` window goes red
on 2026-11-24. A release after 2026-11-23 needs CMVP re-verified by hand against its `source_url`
first. Never run `quirk compliance cmvp refresh`, and never bump the date without re-verifying.

**Operator scoping decisions (2026-11-03 kickoff):**
- Core scope is CR-01, CR-02, the CHANGELOG/PyPI wording, the hero recapture, the release, and the
  announcement re-check.
- All four optional post-GO extras were accepted: the smoke-harness false passes, the doctor DB
  check, source-scanner error handling, and the gate-test blind spots.
- Dependabot: the four critical alerts only.
- Research was skipped, because every item is a reproduced or code-read defect with a candidate fix
  already recorded in its todo.

---

## Boundary verifications — read these before planning

Checked live at the milestone boundary (2026-11-03):

1. **PyPI serves 5.28.0 with `Requires-Python: <3.15,>=3.10`.** Read from the PyPI JSON API on
   2026-11-03. The CR-01 reproduction (unpinned 3.15 install resolves 5.27.0) is in the todo, from
   `python:3.15-slim`, Python 3.15.2. It was not re-run here.
2. **The 4 critical Dependabot alerts are all outside the shipped Python package:**
   - #84 and #83 are `tinypool` (GHSA-5gmw-xhrv-c9v3, GHSA-85c8-ppgw-ccpr), patched in 2.1.1 and
     2.1.2.
   - #31 is `vitest` (GHSA-5xrq-8626-4rwp), patched in 3.2.6.
   - All three are `src/dashboard/package-lock.json`, scope `development`.
   - #3 is `google.golang.org/grpc` (GHSA-p77j-4mvh-x3m3), patched in 1.79.3, in
     `labs/grpc-tls/go.mod`, a chaos-lab fixture.
3. **`main` is at `f4564d2c`** (the PR #65 merge, the v5.28 archive). This milestone's branch is
   `v5281-open`, cut from it.
4. **Source todos** (each carries its own `## Feasibility & Effort` section):
   - `261030-python-requires-cap-makes-pip-silently-install-5270-on-3.15.md` (CR-01, IN-01; owner
     `999.129`)
   - `261030-semgrep-missing-with-source-targets-records-ran-clean.md` (CR-02; owner `999.127`)
   - `261030-source-scanner-partial-result-loss-and-error-handling.md` (WR-01, WR-02, IN-03, IN-04)
   - `261030-doctor-check-db-false-ok.md` (WR-03, IN-02)
   - `261030-release-smoke-harness-false-pass-paths.md` (CR-03, WR-09, WR-10, IN-05)
   - `261030-audit-and-attribution-scripts-pass-vacuously.md` (WR-04, WR-05)
   - `261030-semgrep-claim-gate-proximity-and-phrasing-blind-spots.md` (WR-06)
   - `261030-changelog-parity-test-qualifier-substring-match.md` (IN-06)

---

## v5.28.1 Requirements

### Install truth (INSTALL)

- [x] **INSTALL-05**: The release smoke's 3.15 leg asserts that an *unpinned* resolve on Python
  3.15 never selects an older `quirk-scanner`, alongside the existing pinned check. 5.28.1 keeps
  `requires-python = ">=3.10,<3.15"` (CR-01, 235.1 D-01/D-02). *Corrected 2026-11-03 (235.1
  discuss):* this requirement first said "the upper cap is removed". A live Python 3.15.2
  measurement showed that would not work: unpinned 3.15 resolves **5.21.0** (not 5.27.0), even with
  an uncapped 5.28.1 available, because `sslyze` pins `nassl<6` and no nassl 5.x supports 3.15.
- [x] **INSTALL-06**: `quirk doctor` reports a Python version outside 3.10–3.14 as unsupported, so
  the stated range is enforced at runtime now that pip no longer enforces it. A bare clone on Python
  3.10 imports `quirk` without failing on `tomllib` (IN-01).

- [x] **INSTALL-07**: An unpinned `pip install quirk-scanner` on Python 3.15 fails loudly
  (`ResolutionImpossible`) instead of silently installing an old release. The operator yanks the
  un-yanked releases 4.10.0 through 5.21.0 on PyPI (17 as of 2026-11-03). The yank is reversible,
  and exact pins still install. It is verified after the yank by re-running the 3.15 dry-run against
  live PyPI. No agent yanks (235.1 D-01).

### Source-scan truth (SRCSCAN)

- [x] **SRCSCAN-01**: With `source_targets` set and `semgrep` not installed, the Source Code domain
  reads as skipped or Not assessed in Scan Coverage, the HTML/PDF/DOCX reports and the dashboard.
  It never reads as "ran" with zero findings (CR-02). The same holds for container scanning when
  `syft` is missing.
- [x] **SRCSCAN-02**: `quirk doctor` warns when source or container scanning is configured on but
  the binary it needs is not installed.
- [x] **SRCSCAN-03**: When one source target fails, the source scanner keeps the results from the
  others. It surfaces scanner errors instead of dropping them (WR-01, WR-02, IN-03, IN-04).

### Doctor (DOCTOR)

- [x] **DOCTOR-01**: `quirk doctor`'s database check fails, rather than reporting OK, when the
  configured DB path is unusable. That includes a path supplied through the environment variable
  (WR-03, IN-02).

### Release-evidence gates (HARNESS)

- [x] **HARNESS-04**: The release smoke harness (`scripts/release_smoke*.sh`) has no path that
  prints `RESULT: PASS` after a failed or skipped step (CR-03, WR-09, WR-10, IN-05).
- [x] **HARNESS-05**: The milestone-audit and score-attribution scripts fail on empty or
  out-of-range input instead of passing vacuously (WR-04, WR-05).
- [x] **HARNESS-06**: The Semgrep working-claim gate and the CHANGELOG parity test catch the
  proximity, phrasing and substring cases the post-GO review showed they miss (WR-06, IN-06).

### Dependencies (DEP)

- [x] **DEP-03**: The four critical Dependabot alerts (#3, #31, #83, #84) are closed by dependency
  bumps (`vitest`/`tinypool` in `src/dashboard`, `grpc` in `labs/grpc-tls`). An alert that cannot
  be bumped is dismissed only with a written reachability reason. The dashboard bundle and the
  `grpc-tls` lab still build, and their gates stay green. *Scoped 2026-11-03 (235.1 plan check):*
  Dependabot only re-evaluates the default branch, so 235.1 delivers the bumps on `v5281-open`, and
  #3/#31 reading `fixed` is verified after the 235.2 merge. *Status 2026-11-05:* bumps on the branch (vitest/@vitest/ui 3.2.7, grpc v1.79.3), #83/#84
  dismissed `tolerable_risk`; box left unchecked on purpose until #3/#31 read `fixed`. *Closed 2026-11-06:* #3 and #31 read `fixed` on `main` (2026-11-06T00:10Z, after the PR #66 merge).

### Release (REL)

- [x] **REL-08**: CHANGELOG has a `[5.28.1]` section describing the fixes. The `[5.28.0]` Semgrep
  known-defect wording is corrected to name both cases (ruleset unavailable, and semgrep not
  installed). Once SRCSCAN-01 lands, the repo README's CR-02 known-defect line is removed or
  rewritten to match the fixed behaviour. The doc-claim ledger gate stays green.
- [x] **REL-09**: The version is 5.28.1 in every declaring file (`pyproject.toml`, `README.md`,
  `docs/UAT-SERIES.md` UAT-1-02 and header). `v5.28.1` is tagged on a `main` merge commit whose CI
  is green (`branch_ci_state.py` exit 0). `release.yml` publishes it, PyPI lists 5.28.1, and the
  PyPI long description is true. All of this is done by 2026-11-23, or after a hand re-verification
  of CMVP.
- [x] **REL-10**: A clean install of 5.28.1 from PyPI passes the release smoke test on every leg.
  The legs are macOS, Linux 3.10, Linux 3.11, contributor, and the 3.15 leg with its new unpinned
  assertion. Attestations are verified.

### Launch (LAUNCH)

- [x] **LAUNCH-08**: The README hero image (`docs/images/dashboard-hero.png`) is recaptured from a
  5.28.1 scan, with a caption that describes that image, and the operator has accepted it visually.
  The recapture uses a snapshot DB, never the canonical DB.
- [x] **LAUNCH-09**: The announcement draft is re-checked sentence by sentence against 5.28.1 (claim
  table, leak grep, false-capability grep). The operator's go/no-go for the 5.28.1 announcement is
  recorded. No agent posts anything.

---

## v5.28.2 Connector Coverage Truth (patch release, opened 2026-11-06)

**Milestone goal:** a scan never records a connector as `ran` when it could not look at anything.
The 5.28.1 announcement was NO-GO on 2026-11-05 because dashboard scans recorded JWT, SAML and S3
as `ran` with zero rows when the server policy refused every internal URL or no AWS credentials were
available. Each unscanned surface added zero findings, so the score came out higher than the estate
deserved. Sources: todos `261105-unscanned-surfaces-inflate-score-in-real-engagements` (critical) and
`261105-connector-phase-ran-with-zero-output-when-url-guard-refuses-all-targets`.

### Coverage truth (COVTRUTH)

- [x] **COVTRUTH-01**: A connector phase reads `ran` only if at least one target answered. If none
  did, it reads `skipped` with a named reason. Partial refusal or failure reads `ran` plus one
  scan-error row per target that did not answer. A live endpoint that answers with nothing stays
  `ran` with 0 rows. This covers JWT, SAML, S3 and every other connector the source audit
  (COVTRUTH-03) finds.
- [x] **COVTRUTH-02**: Two new reasons are added to `SCAN_PHASE_SKIP_REASONS`: `internal-target-refused`
  (URL guard / server `security.allow_internal_targets` policy) and `auth-failed` (credentials
  present but rejected). `missing-credentials` (no credentials in the chain) and `failed` (every
  target unreachable) are reused. Each skip emits an ADVISORY scan-error row that counts in the score
  like 5.28.1's `missing-binary` (235.1 D-07). The rows are handled downstream (trends, sensor push,
  findings_evaluator) in the same way.
- [x] **COVTRUTH-03**: A test enumerates every connector phase from source at run time, with no hand
  list. It fails if any connector can return no rows from an exception or refusal path while its
  phase records `ran`. It is red on the pre-fix code.
- [x] **COVTRUTH-04**: The Scan Coverage chips, the dashboard page empty states (Data at Rest,
  Identity, Motion, …) and the reports show the recorded skip reason. Database targets that failed
  to connect appear as failed rows, not omitted.
- [x] **COVTRUTH-05**: The New Scan form warns when a JWT or SAML connector URL is loopback or RFC1918
  and the server's `security.allow_internal_targets` is false. *(Corrected 2026-11-07 from "a target or
  connector URL": the policy never refuses plain TLS/SSH targets; review C-WR-01.)*
- [x] **COVTRUTH-06**: `docs/operators-guide.md` §3.0 gets a "before a client scan" checklist (server
  `config.yaml` with `allow_internal_targets` and scoped `trusted_targets`; start `quirk serve` with
  the cloud credentials it should use; treat an enabled connector with zero results as unverified).
  CHANGELOG `[5.28.2]` describes the fix. The UAT series, `docs/uat-coverage-gaps.md` and the vault
  are regenerated or synced.

### Release (REL)

- [x] **REL-11**: The version is 5.28.2 in every declaring file. `v5.28.2` is tagged on a `main` merge
  commit with green CI (`branch_ci_state.py` exit 0), `release.yml` publishes it, and PyPI lists it,
  by 2026-11-23 (or after a hand re-verification of CMVP).
- [x] **REL-12**: A clean PyPI install of 5.28.2 passes the release smoke test on macOS, Linux 3.10,
  Linux 3.11, contributor and the 3.15 unpinned leg. Attestations verify.

### Launch (LAUNCH)

- [x] **LAUNCH-10**: The 2026-11-05 full chaos-lab dashboard walkthrough is re-run on 5.28.2. No
  enabled connector reads `ran` with 0 rows unless a target answered, and every skip names its true
  cause (operator, 2026-11-06: this is the GO evidence).
- [x] **LAUNCH-11**: The announcement draft is re-checked sentence by sentence against 5.28.2 (claim
  table, leak grep, false-capability grep). The operator's go/no-go is recorded. No agent posts anything.

### v5.28.2 Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COVTRUTH-01 | Phase 235.3 | Complete (2026-11-07, verified at dc055f3b) |
| COVTRUTH-02 | Phase 235.3 | Complete (2026-11-07, verified at dc055f3b) |
| COVTRUTH-03 | Phase 235.3 | Complete (2026-11-07, verified at dc055f3b) |
| COVTRUTH-04 | Phase 235.3 | Complete (2026-11-07, verified at dc055f3b) |
| COVTRUTH-05 | Phase 235.3 | Complete (2026-11-07, verified at dc055f3b) |
| COVTRUTH-06 | Phase 235.3 | Complete (2026-11-07, verified at dc055f3b) |
| REL-11 | Phase 235.4 | Complete (2026-11-08, verified at 52e1b604) |
| REL-12 | Phase 235.4 | Complete (2026-11-08, verified at 52e1b604) |
| LAUNCH-10 | Phase 235.4 | Complete (2026-11-08, verified at 52e1b604) |
| LAUNCH-11 | Phase 235.4 | Complete (2026-11-08, verified at 52e1b604) |

**Coverage:** 10 requirements, 10 mapped, 0 unmapped.

---

## Future Requirements

Deferred to v5.29 or later:

- Phase 236: close the four score-affecting dashboard/report divergences (`999.132`).
- Calibration profile ignored on trend/compare/merge/notify (`999.131`).
- QRAMM Scorecard legacy/stale branch unreachable (`999.139`).
- Sensor-push rows interleaving as the "previous" drift session (`999.135`).
- The remaining 76 Dependabot alerts (33 high).

## Out of Scope

| Item | Reason |
|------|--------|
| Azure Key Vault key scanning (`999.126`) | Disclosed known defect; a connector fix, not a patch-release truth fix |
| Windows `install.ps1` sensor identity (`999.129` item) | Disclosed known defect; needs installer design work |
| Announcing Python 3.15 support | INSTALL-05 stops pip backtracking; it does not claim 3.15 works. The announcement keeps "3.10 to 3.14" |
| Yanking 5.27.0 or 5.25.0 | Not needed: both are already unsatisfiable on 3.15 (they need sslyze, hence nassl<6). The yank set is the pre-sslyze releases only (INSTALL-07). *Superseded 2026-11-05 (235.2):* wrong in practice. Both had an uncapped `requires-python`, pip on 3.15-slim selected 5.27.0, and the operator yanked 5.25.0 and 5.27.0 too |
| Kerberos weak-etype findings in the report (DETECT-02) | Disclosed; feature work for v5.29 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INSTALL-05 | Phase 235.1 | Complete (2026-11-05, verified at af4f755c) |
| INSTALL-06 | Phase 235.1 | Complete (2026-11-05, verified at af4f755c) |
| SRCSCAN-01 | Phase 235.1 | Complete (2026-11-05, verified at af4f755c) |
| SRCSCAN-02 | Phase 235.1 | Complete (2026-11-05, verified at af4f755c) |
| SRCSCAN-03 | Phase 235.1 | Complete (2026-11-05, verified at af4f755c) |
| DOCTOR-01 | Phase 235.1 | Complete (2026-11-05, verified at af4f755c) |
| HARNESS-04 | Phase 235.1 | Complete (2026-11-05, verified at af4f755c) |
| HARNESS-05 | Phase 235.1 | Complete (2026-11-05, verified at af4f755c) |
| HARNESS-06 | Phase 235.1 | Complete (2026-11-05, verified at af4f755c) |
| DEP-03 | Phase 235.1 | Complete (2026-11-06, verified at 139ed513): delivered in 235.1; #3/#31 read `fixed` on `main` after the 235.2 merge; #83/#84 dismissed |
| REL-08 | Phase 235.1 | Complete (2026-11-05, verified at af4f755c) |
| INSTALL-07 | Phase 235.2 | Complete (2026-11-06, verified at 139ed513) |
| REL-09 | Phase 235.2 | Complete (2026-11-06, verified at 139ed513) |
| REL-10 | Phase 235.2 | Complete (2026-11-06, verified at 139ed513) |
| LAUNCH-08 | Phase 235.2 | Complete (2026-11-06, verified at 139ed513) |
| LAUNCH-09 | Phase 235.2 | Complete (2026-11-06, verified at 139ed513; operator decision NO-GO recorded) |

**Coverage:** 16 requirements, 16 mapped, 0 unmapped. (INSTALL-07 added 2026-11-03 at the 235.1 discuss.)

---
*Requirements defined: 2026-11-03*
