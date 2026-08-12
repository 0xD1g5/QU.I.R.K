# Roadmap: QU.I.R.K. — Quantum Infrastructure Readiness Kit

## Milestones

- ✅ **v3.9 Gap Closure** — Phases 1–11, 40 plans (shipped 2026-04-04) → `.planning/milestones/v3.9-ROADMAP.md`
- ✅ **v4.1 Foundation Polish** — Phases 12–16, 17 plans (shipped 2026-04-08) → `.planning/milestones/v4.1-ROADMAP.md`
- ✅ **v4.2 Identity Crypto** — Phases 17–24, 14 plans (shipped 2026-04-24) → `.planning/milestones/v4.2-ROADMAP.md`
- ✅ **v4.3 Data at Rest** — Phases 25–31, 24 plans (shipped 2026-04-26) → `.planning/milestones/v4.3-ROADMAP.md`
- ✅ **v4.4 Data in Motion** — Phases 32–37, 33 plans (shipped 2026-04-29) → `.planning/milestones/v4.4-ROADMAP.md`
- ✅ **v4.5 Reliability & Gap Closure** — Phases 38–44, 40 plans (shipped 2026-05-03) → `.planning/milestones/v4.5-ROADMAP.md`
- ✅ **v4.6 Enterprise Readiness** — Phases 45–50, 24 plans (shipped 2026-05-05) → `.planning/milestones/v4.6-ROADMAP.md`
- ✅ **v4.7 Governance & Compliance** — Phases 51–56 (shipped 2026-05-08) → `.planning/milestones/v4.7-ROADMAP.md`
- ✅ **v4.8 Pre-Primetime** — Phases 57–68, 53 plans (shipped 2026-05-14) → `.planning/milestones/v4.8-ROADMAP.md`
- ✅ **v4.9 Audit Depth** — Phases 69–77, 38 plans (shipped 2026-05-15) → `.planning/milestones/v4.9-ROADMAP.md`
- ✅ **v4.10 Launch Readiness** — Phases 78–85, 31 plans (shipped 2026-05-21) → `.planning/milestones/v4.10-ROADMAP.md`
- ✅ **v4.10.1 Scoring Correctness Hotfix** — Phase 86, 3 plans (shipped 2026-05-22) → `.planning/milestones/v4.10.1-ROADMAP.md`
- ✅ **v5.0 Stabilization + Tech Debt Sweep** — Phases 87–92, 16 plans (shipped 2026-05-22) → `.planning/milestones/v5.0-ROADMAP.md`
- ✅ **v5.1 Authenticated Scanning + API Surface Depth** — Phases 93–96, 16 plans (shipped 2026-05-23) → `.planning/milestones/v5.1-ROADMAP.md`
- ✅ **v5.2 Consulting-Grade Reporting** — Phases 97–100, 12 plans (shipped 2026-05-24) → `.planning/milestones/v5.2-ROADMAP.md`
- ✅ **v5.3 Adoption & Integration Surface** — Phases 101–105, 20 plans (shipped 2026-05-25) → `.planning/milestones/v5.3-ROADMAP.md`
- ✅ **v5.4 Distributed On-Prem Scanner Architecture** — Phases 106–112, 20 plans (shipped 2026-05-26) → `.planning/milestones/v5.4-ROADMAP.md`
- ✅ **v5.5 Distributed Hardening + Stabilization** — Phases 113–116, 11 plans (shipped 2026-05-27) → `.planning/milestones/v5.5-ROADMAP.md`
- ✅ **v5.6 Distributed Completion + Public Launch** — Phases 117–122, 20 plans (shipped 2026-06-12) → `.planning/milestones/v5.6-ROADMAP.md`
- ✅ **v5.7 Hardening + Hardware Compatibility & Lifecycle Remediation** — Phases 123–129, 24 plans (shipped 2026-06-14) → `.planning/milestones/v5.7-ROADMAP.md`
- ✅ **v5.8 Audit Closeout + SNMP Fingerprinting** — Phases 130–134, 21 plans (shipped 2026-06-18) → `.planning/milestones/v5.8-ROADMAP.md`
- ✅ **v5.9 Documentation Audit & Living Docs System** — Phases 135–138 + 138.1/138.2, 10 plans (shipped 2026-07-30) → `.planning/milestones/v5.9-ROADMAP.md`
- ✅ **v5.10 Hardware Lifecycle Depth** — Phases 139–143, 36 plans (shipped 2026-08-03) → `.planning/milestones/v5.10-ROADMAP.md`
- ✅ **v5.11 Discovery at Scale + Backlog Drain** — Phases 144–147, 16 plans (shipped 2026-08-11) → `.planning/milestones/v5.11-ROADMAP.md`

- **v5.12 Release & Verification Integrity** — Phases 148–153 (in progress, opened 2026-08-11)

---

## Current Milestone: v5.12 Release & Verification Integrity

**Goal:** Make QU.I.R.K.'s own signals trustworthy again — cutting a tag produces a complete,
verified artifact set without supervision; a phase cannot be marked complete while its
verification artifacts are missing; and a green test suite means something.

**Why this shape:** every requirement in this milestone fixes a *measurement* failure rather than
a capability gap. The v5.11 cycle surfaced five independent measurement failures in one milestone
— a release pipeline that produced no Windows build for three consecutive milestones, a signing
self-test that could never pass and had never run, three of four phases shipping without a
completion artifact, a deferred item's rationale that decayed within a day, and ~102 test
failures red since roughly Phase 97 — and they compound: a saturated test signal cannot flag a
regression, a silent release pipeline cannot flag a missing artifact, absent verification
artifacts cannot flag an unproven phase. Full rationale: `.planning/HORIZON.md`.

**Explicitly out of scope:** continuous hardware lifecycle monitoring (v5.13 capability anchor —
needs a research pass); SaaS multi-tenancy (still parked); DISC-08 sub-batch checkpoint/resume
granularity (accepted boundary, revisit only if batch cost grows).

**Per-phase requirement:** every phase below includes documentation updates and an Obsidian vault
sync as part of its close-out, and a `docs/UAT-SERIES.md` entry, per `CLAUDE.md`'s Per-Phase
Documentation Checklist.

### Phases

- [ ] **Phase 148: Release Pipeline Repair + Windows Asset Backfill** — Prove the repaired
      signing self-test with a real run, add a pre-tag dry-run mechanism, add a tag-format guard,
      and close the v5.11.0 Windows-asset gap

- [ ] **Phase 149: Test Suite Triage** — Give every one of the ~102 pre-existing failing tests an
      explicit written disposition (fixed / quarantined / deleted)

- [ ] **Phase 150: Test Suite Green Baseline + CI Gate** — `pytest -q` green on a clean
      environment, held by a CI gate that fails the build on any new failure

- [ ] **Phase 151: Phase-Completion Artifact Gates** — A phase cannot close with a missing
      VERIFICATION.md, a stale VALIDATION.md, or a missing UAT-SERIES.md entry; a destructive
      planning operation cannot run against an unarchived milestone

- [ ] **Phase 152: Discovery Empirical Closure** — Segmented-network chaos lab profile, empirical
      resolution of the Phase 144 nmap timing artifact, and the interactive nmap-discovery-first
      default flipped to Y

- [ ] **Phase 153: Release Tag Cut** — Cut the real v5.12.0 tag and prove every repaired signal
      end-to-end, including the new phase-artifact gates applied to itself

### Phase Details

#### Phase 148: Release Pipeline Repair + Windows Asset Backfill

**Goal**: A release job that is broken can be caught before a tag is cut, and the specific
Windows-asset gap left by v5.11.0 is closed with a real, verified artifact
**Depends on**: Nothing (first phase — concrete, demonstrable deliverable early, per the milestone
risk mitigation that an integrity milestone is easy to defer without a visible early win)
**Requirements**: RELEASE-02, RELEASE-03, RELEASE-04
**Success Criteria** (what must be TRUE):

  1. A manually-triggered dry-run of the release workflow (e.g. `workflow_dispatch`) exercises the
     `windows-package` job end-to-end without requiring a git tag, and reports pass/fail

  2. The repaired signing self-test (`1a6effc`) is proven passing by an actual green CI run of that
     dry-run — not by code inspection alone

  3. A malformed tag (e.g. `v5.9`, which never matched `v*.*.*`) or an unpushed tag is detectably
     different from a successful release run via a documented check or workflow guard

  4. The v5.11.0 Windows-asset gap is resolved per the D-148-RELEASE04 decision below — either a
     Windows operator zip is attached to a `v5.11.0` GitHub Release, or an explicit written
     disposition in `docs/release-notes/` and on the Releases page records that v5.11.0 is
     PyPI-only and why. Either way, an operator reading the Releases page can tell without
     guessing whether a Windows artifact exists for that version.

**Open decisions — resolve at `/gsd-discuss-phase 148`, do NOT let an executor pick silently:**

- **D-148-RELEASE04 — how to close the v5.11.0 Windows-asset gap.** This is a *provenance*
  judgment call, not a feasibility one. Attaching the zip is technically trivial
  (`gh release create v5.11.0` + `gh release upload`), but the binary would be built **now**, from
  a `release.yml` that has since changed (`1a6effc` repaired the signing self-test). That attaches
  an artifact to a version tag which the actual v5.11.0 pipeline never produced and could not
  reproduce — on a project that ships Sigstore attestations and PyPI Trusted Publishers, that is a
  supply-chain posture question, not a chore.

  - **Option A — backfill the asset:** build from the `v5.11.0` tag, attach, and note in the
    release body that the artifact was produced post-hoc with the repaired workflow. Operators get
    a Windows binary for the version; provenance is documented rather than implied.

  - **Option B — disposition the gap:** leave v5.11.0 PyPI-only, state it explicitly in the
    release notes and Releases page, and let `v5.12.0` (Phase 153) be the first version with a
    verified Windows artifact. Release history stays strictly reproducible-from-tag.

  - Both are defensible. The requirement (RELEASE-04) deliberately does not pick, because the
    right answer depends on how strictly the project wants "release artifact" to mean
    "reproducible from that tag's pipeline."

  - **RESOLVED 2026-08-11 (`148-CONTEXT.md` D-01..D-04): Option B — explicit disposition.** No zip
    is backfilled onto `v5.11.0`. A bare `v5.11.0` GitHub Release (zero assets) plus
    `docs/release-notes/5.11.0.md` record that the release is PyPI-only and why; `v5.12.0`
    (Phase 153) is the first version with a verified Windows artifact.

**Plans**: 4 plans

Plans:

- [x] 148-01-PLAN.md — Dry-run mechanism in release.yml (workflow_dispatch + tag-ref guards + dry-run artifact) [RELEASE-02]
- [x] 148-02-PLAN.md — Scheduled tag-hygiene guard + testable decision script + baseline [RELEASE-03]
- [x] 148-03-PLAN.md — v5.11.0 PyPI-only disposition notes + GitHub Release body [RELEASE-04]
- [x] 148-04-PLAN.md — Live proof: green dry-run, live guard run, bare v5.11.0 Release [RELEASE-02/03/04]

#### Phase 149: Test Suite Triage

**Goal**: Every pre-existing full-suite test failure has an explicit, written disposition, so the
scope of the green-baseline work in Phase 150 is known rather than guessed
**Depends on**: Nothing (independent of release and artifact-gate work; highest-variance item in
the milestone, sequenced early and alone so its output can re-scope what follows)
**Requirements**: SUITE-01
**Success Criteria** (what must be TRUE):

  1. Every test failing in a clean full-suite run (not just the `-m 'not slow'` default) appears in
     a written triage ledger with one of: fixed / quarantined-with-reason / deleted-as-obsolete

  2. The ledger's total failure count matches the actual full-suite run — no failure is left
     unclassified

  3. Quarantined tests are marked in a machine-checkable way (explicit skip/xfail referencing the
     ledger), not silently passing or invisibly excluded

**Plans**: 11 plans

Plans:

- [x] 149-01-PLAN.md — D-04 skip-registry gate repair + AST walker extension (skip/xfail) + ledger skeleton
- [x] 149-02-PLAN.md — Cluster 1: SSRF/DNS-blocked sandbox (23 tests)
- [x] 149-03-PLAN.md — Cluster 2 + 6: Playwright pollution + pip dry-run flakiness (20 tests)
- [x] 149-04-PLAN.md — Cluster 3 + 4 + 7: version staleness + GCP optional extra (10 tests)
- [x] 149-05-PLAN.md — Cluster 5: sensor_id shape / AUDIT-08 regression (10 tests)
- [x] 149-06-PLAN.md — Cluster 9 Group A: scanner/detection-logic failures (18 tests)
- [x] 149-07-PLAN.md — Cluster 9 Group B: dashboard/API/DB-migration failures (12 tests)
- [x] 149-08-PLAN.md — Cluster 9 Group C: QRAMM subsystem + SIGSEGV investigation (6 tests)
- [x] 149-09-PLAN.md — Cluster 9 Group D1: CLI/compliance/posture failures (11 tests)
- [x] 149-10-PLAN.md — Cluster 9 Group D2: docs-presence/security-gate/windows-smoke (5 tests)
- [x] 149-11-PLAN.md — Final reconciliation: fresh full-suite run vs. ledger exact-count match

#### Phase 150: Test Suite Green Baseline + CI Gate

**Goal**: `pytest -q` produces a green baseline on a clean supported environment, and CI holds that
baseline so a newly introduced failure is visible as a new failure instead of joining the red
background
**Depends on**: Phase 149 (the triage output determines whether this phase is small — mostly
quarantines already applied — or large; cannot be scoped before triage completes)
**Requirements**: SUITE-02, SUITE-03
**Success Criteria** (what must be TRUE):

  1. `pytest -q` run on a clean environment matching CI's Python version exits 0
  2. CI runs the same full-suite gate (not a narrower `-m 'not slow'` subset that silently
     deselects known failures) on every PR and every push to `main`

  3. A newly introduced failing test, added deliberately as a smoke check during this phase, fails
     the CI build

  4. The green-baseline standard and how to run it locally are documented for future contributors

**Plans**: 6 plans

*(Plans 150-01..150-03 were the original scope. Plan 150-03's live-fire push surfaced 38 real-CI
failures across 8 categories — the local baseline had been validated against a broader extras
surface than CI installs — and halted at its own stop condition. Plans 150-04..150-09 are the
remediation pass planned from 150-CONTEXT.md's D-09..D-17 addendum.)*

Plans:
**Wave 1**

- [x] 150-01-PLAN.md — D-05 impacket KDCOptions fix + un-quarantine 2 Kerberos tests + ledger correction
- [x] 150-02-PLAN.md — Local full-suite baseline + gating `Linux Full Suite` CI job + CONTRIBUTING.md

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 150-03-PLAN.md — D-07 live-fire smoke check — HALTED at its Task 1 stop condition (real CI red, 38 failures); superseded by 150-08

**Remediation Wave 1** *(D-09..D-17)*

- [x] 150-04-PLAN.md — CI-parity venv + failure inventory + D-16 dead-test deletion + D-17 /api/sensor/push root-cause

**Remediation Wave 2** *(blocked on 150-04's CI-parity venv)*

- [ ] 150-05-PLAN.md — D-12/D-13 chaos-lab cert generation in lab.sh + lab doc sync + D-14 CONTRIBUTING note
- [ ] 150-06-PLAN.md — D-09/D-10/D-11 extras skip guards (31 tests) + D-15 gitignored-planning guards (4 tests) + registry

**Remediation Wave 3**

- [ ] 150-07-PLAN.md — Ledger addendum + honest SUITE-02/03 status + roadmap plan list + UAT-150 cases

**Remediation Wave 4**

- [ ] 150-08-PLAN.md — Green real-CI run (SUITE-02) + live-fire red run + evidence artifact + human checkpoint (SUITE-03)

**Remediation Wave 5**

- [ ] 150-09-PLAN.md — 150-VERIFICATION.md + SUITE-02/03 flip to Complete + Obsidian phase note and hub refresh

#### Phase 151: Phase-Completion Artifact Gates

**Goal**: A phase cannot be reported complete while its verification artifacts are missing or
stale, and a destructive planning operation refuses to run against an unarchived milestone —
closing the exact gap that let three of four v5.11 phases ship without a completion artifact and
let `phases.clear` delete ~39 unrecoverable v5.11 phase files
**Depends on**: Nothing (independent of release/test-suite work; same workflow surface as
ARTIFACT-01..03, plus the destructive-operation guard from the same incident class)
**Requirements**: ARTIFACT-01, ARTIFACT-02, ARTIFACT-03, ARTIFACT-04
**Success Criteria** (what must be TRUE):

  1. Attempting to report a phase complete with a missing `VERIFICATION.md` is blocked or clearly
     flagged before the phase is recorded as done — reproducing and closing the exact Phase 145 gap

  2. Attempting to close a phase whose `VALIDATION.md` still has pending task rows or
     `nyquist_compliant: false` is blocked or clearly flagged — reproducing and closing the exact
     Phase 147 gap

  3. A phase that shipped user-facing behavior cannot close without a corresponding
     `docs/UAT-SERIES.md` entry — enforced by the workflow, not left to a documentation checklist
     alone — reproducing and closing the exact Phase 144 gap

  4. `phases.clear` (or the equivalent destructive planning operation) refuses to run when the
     current milestone's `.planning/milestones/v<X.Y>-phases/` archive is absent or empty,
     verified against the exact scenario recorded in
     `.planning/milestones/v5.11-phases/ARCHIVE-MANIFEST.md`

**Plans**: TBD

#### Phase 152: Discovery Empirical Closure

**Goal**: The Phase 144 nmap timing-engine artifact is settled against a realistic segmented
network instead of remaining an open question forever, and interactive setup opts users into the
recommended discovery path by default
**Depends on**: Nothing structurally at the milestone level (independent of release/test-suite/
artifact-gate work), but DISC-10 depends on DISC-09 within this phase — the lab profile must exist
before the artifact can be re-verified against it
**Requirements**: DISC-09, DISC-10, DISC-11
**Success Criteria** (what must be TRUE):

  1. A segmented-network chaos lab profile exists, is listed in `lab.sh`'s `ALL_PROFILES`, and
     produces realistic unreachable hosts (RST/ICMP-unreachable on a routed segment) rather than
     unassigned loopback aliases

  2. Running chunked discovery + partial-result tolerance against that profile produces a written
     finding on the Phase 144 nmap timing artifact: either it does not reproduce (closed) or it
     does and a scoped mitigation is chosen with its false-negative tradeoffs documented

  3. Interactive setup's "Run nmap port discovery first?" prompt (`quirk/interactive.py:176-179`)
     defaults to Yes; a user who accepts the default gets nmap discovery and the Phase 145 liveness
     pre-pass without having to opt in explicitly

  4. `docs/chaos-lab.md`, `README.md`, and the profile's `expected_results_*.md` oracle all
     reflect the new profile in the same change, per `CLAUDE.md`'s Chaos Lab Maintenance rule

**Plans**: TBD

**UI hint**: yes

#### Phase 153: Release Tag Cut

**Goal**: Cutting the real `v5.12.0` release tag proves every repaired signal end-to-end on an
actual immutable tag — the only proof RELEASE-01 admits — and the milestone's own close-out is the
first phase gated by the new ARTIFACT enforcement
**Depends on**: Phase 148 (pipeline repair + dry-run mechanism must exist first), Phase 150 (the
CI gate this tag's build runs under must already be green and enforced), Phase 151 (this phase's
own completion is the first to be gated by the new VERIFICATION/VALIDATION/UAT-SERIES enforcement,
dogfooding it immediately)
**Requirements**: RELEASE-01
**Success Criteria** (what must be TRUE):

  1. Pushing the `v5.12.0` tag triggers `release.yml`, and the `windows-package` job completes with
     a green signing self-test — not the dry-run from Phase 148, an actual tagged run

  2. The GitHub Release for `v5.12.0` has a Windows operator zip attached and downloadable
  3. The Phase 148 tag-hygiene guard does not flag `v5.12.0` as malformed or missing
  4. Phase 153 itself closes with a `VERIFICATION.md`, a post-execution `VALIDATION.md`, and a
     `docs/UAT-SERIES.md` entry — the Phase 151 gates applied to the phase that ships them, proving
     the enforcement machinery works in practice and not just on paper

**Plans**: TBD

### Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 148. Release Pipeline Repair + Windows Asset Backfill | 4/4 | Complete    | 2026-08-11 |
| 149. Test Suite Triage | 11/11 | Complete    | 2026-08-12 |
| 150. Test Suite Green Baseline + CI Gate | 4/9 | In Progress|  |
| 151. Phase-Completion Artifact Gates | 0/TBD | Not started | - |
| 152. Discovery Empirical Closure | 0/TBD | Not started | - |
| 153. Release Tag Cut | 0/TBD | Not started | - |

---

<details>
<summary>✅ v5.11 Discovery at Scale + Backlog Drain (Phases 144–147) — SHIPPED 2026-08-11</summary>

**v5.11** made large (>1024-host) range scans reachable end-to-end from the dashboard's
nmap-discovery path — chunked batches with per-batch failure isolation, a TCP-SYN/ACK liveness
pre-pass with explicit privilege-fallback detection, per-batch progress on the dashboard,
batch-scaled timeouts, one shared CLI/dashboard chunking call site, and undetermined-host
disclosure across all report surfaces — while draining the small debt tail accumulated since
v5.8/v5.10 (OT/ICS resume-checkpoint gap, BACnet CVE key coverage, 2026-05-27 audit ledger
reconciliation, deferred human-UAT re-triage). 4 phases, 16 plans, 11/11 requirements, audit
`passed`. Full phase details archived to `.planning/milestones/v5.11-ROADMAP.md`; audit
`.planning/milestones/v5.11-MILESTONE-AUDIT.md`.

- [x] Phase 144: Chunked Discovery Core (3/3 plans) — completed 2026-08-10
- [x] Phase 145: Liveness Pre-Pass (3/3 plans) — completed 2026-08-10
- [x] Phase 146: Progress, Scaling & Disclosure (6/6 plans) — completed 2026-08-11
- [x] Phase 147: Backlog Drain — Lifecycle & Ledger Tail (4/4 plans) — completed 2026-08-11

**Note:** approximately 39 of ~58 v5.11 phase artifact files (`.planning/phases/144-147/*`) were
permanently lost during the v5.12 `/gsd-new-milestone` opening when a destructive `phases.clear`
call ran without checking that `milestone.complete` had reported `archived.phases: false`. Code
and the decision record are unaffected — see
`.planning/milestones/v5.11-phases/ARCHIVE-MANIFEST.md`. This incident is the direct source of
v5.12's ARTIFACT-04 requirement.

</details>

---

<details>
<summary>✅ v3.9–v5.5 (Phases 1–116) — SHIPPED</summary>

All completed milestone roadmaps are archived in `.planning/milestones/`. The next milestone continues from Phase 123.

**v5.5 Distributed Hardening + Stabilization** (Phases 113–116) hardened the v5.4 distributed
scanner into production shape: per-sensor opaque Bearer-token authentication with revocation and a
two-router split (113), automatic merge on full sensor check-in via a failure-isolated FastAPI
BackgroundTask with a config toggle and two trigger conditions (114), a live-UAT stabilization sweep
of the four E2E-surfaced defects — idempotent enroll, importlib.resources cmvp packaging, scheduler
arg fix with target preservation, phantom-row elimination — plus a weak-TLS segment-b lab target so
the per-segment filter is exercisable end-to-end (115), and an evidence-backed Windows packaging
PyInstaller spike returning GO-conditional with a v5.6 effort estimate (116). Audit: 13/13
requirements satisfied, 0 blockers, integration clean. Full details:
`.planning/milestones/v5.5-ROADMAP.md`.

**v5.4 Distributed On-Prem Scanner Architecture** (Phases 106–112) split QU.I.R.K. into a sensor/console
model so a segmented enterprise network is scanned segment-by-segment and merged into one authoritative
CBOM + one quantum-readiness score, with no inbound access to any segment required. Full details:
`.planning/milestones/v5.4-ROADMAP.md`.

</details>

---

<details>
<summary>✅ v5.6 Distributed Completion + Public Launch (Phases 117–122) — SHIPPED 2026-06-12</summary>

**v5.6** shipped the production Windows frozen sensor (`--onedir` PyInstaller build + smoke + zip/Scheduled-Task installer + frozen E2E per-sensor auth + GitHub Release asset `quirk-windows-5.6.0.zip`), took the repository PUBLIC (gitleaks-clean 3-pass history rewrite, branch protection with required "Windows Sensor Smoke" check, SSRF guard hardening, Actions SHA-pinning), added port-scope discovery control (common/top1000/all/custom + zero-result signal), and closed 11 audit tech-debt items at version 5.6.0 (tag `v5.6.0`).

- [x] Phase 117: Windows Production Build + Smoke (1/1 plans) — completed 2026-05-27
- [x] Phase 118: Windows Packaging, E2E Auth + Release (3/3 plans) — completed 2026-05-27
- [x] Phase 119: Public-Repo Cutover (2/2 plans) — completed 2026-06-12
- [x] Phase 120: Go-Public Remediation (5/5 plans) — completed 2026-06-12
- [x] Phase 121: Port-Scope Discovery Control (5/5 plans) — completed 2026-06-11
- [x] Phase 122: Address Tech Debt + Milestone Closeout Docs (4/4 plans) — completed 2026-06-12

Audit: 21/21 requirements, 0 blockers (`.planning/milestones/v5.6-MILESTONE-AUDIT.md`). Full details: `.planning/milestones/v5.6-ROADMAP.md`.

</details>

---

<details>
<summary>✅ v5.7 Hardening + Hardware Compatibility & Lifecycle Remediation (Phases 123–129) — SHIPPED 2026-06-14</summary>

**v5.7** drained the 18 deferred audit rows from the v5.6 public launch (Wave A: SSRF hardening SP-02/03/04+WR-06+CD-03, scoring correctness SP-05+QC-02/03+WR-02/05, posture defaults WR-01/CE-04, distributed edges CD-05/06, ledger closeout + Dashboard Quality green), then shipped the HWCOMPAT capability arc (Wave B: agentless hardware fingerprinting from SSH/HTTP mgmt banners, 8-vendor PQC compatibility matrix + 90-day CI staleness gate, CNSA 2.0 tier assignment, full report surfacing in HTML/DOCX/executive/dashboard /hardware tab, crypto-bridge detection, CBOM Pass 4 FIRMWARE components). 7 phases, 24 plans, 24/24 requirements, 50 commits. Tag `v5.7.0`.

### Phases

- [x] **Phase 123: SSRF & URL-Allowlist Hardening** — Close all five SSRF warning rows from the 2026-05-27 audit; wire rest_fuzzer through the existing validate_external_url invariant; add GCP metadata aliases; fix path-ref injection into syft; block reflective self-SSRF; mitigate DNS-rebinding TOCTOU (completed 2026-06-13)
- [x] **Phase 124: Scoring & Evidence Correctness** — Fix five scoring/evidence correctness findings: KeyError abort on missing severity, QRAMM weakest-link inflation, EdDSA agility credit, AEAD cipher mis-classification, cross-tenant evidence contamination in distributed mode
- [x] **Phase 125: Posture Defaults + Distributed Edge Cases** — Harden two insecure-by-default deployment postures (auth token + bind address); surface IAM permission errors as scan-coverage findings; fix two distributed edge cases (same-second merge tiebreak, notify fan-out isolation) (completed 2026-06-13)
- [x] **Phase 126: Audit Ledger Closeout + Dashboard Quality Green-Up** — Close or formally disposition every remaining `deferred → v5.7` row in the audit ledger; bring Dashboard Quality CI green (a11y + E2E smoke) (completed 2026-06-13)
- [x] **Phase 127: Hardware Fingerprinting Foundation** — Agentless device fingerprinting from SSH banners + HTTP management interfaces; curated hardware-PQC compatibility matrix with staleness gate; `hwcompat` chaos lab profile; HardwareDevice ORM table; CI staleness assertion (completed 2026-06-14)
- [x] **Phase 128: Remediation Tiers + Report Surfacing** — Tier assignment logic per device (Tier 1/2/3/N/A + CNSA 2.0 timeline); hardware findings through the findings chokepoint; hardware PQC narrative in exec report; `/hardware` dashboard tab (completed 2026-06-14)
- [x] **Phase 129: Crypto-Bridge Detection + CBOM Pass 4** — Detect incompatible endpoints behind PQC-capable gateways with conservative defaults; CBOM Pass 4 (`ComponentType.FIRMWARE`) for hardware fleet visibility; `HARDWARE` added to Pass 2/3 skip-lists (completed 2026-06-14)

### Phase Details

#### Phase 123: SSRF & URL-Allowlist Hardening

**Goal**: All URL-validation bypass paths surfaced in the 2026-05-27 audit are closed — no scanner request can reach blocked metadata ranges, loopback, or internal targets via raw sockets, path-shaped refs, or DNS-rebinding
**Depends on**: Nothing (Wave A, first parallel group)
**Requirements**: SSRF-01, SSRF-02, SSRF-03, SSRF-04, SSRF-05
**Success Criteria** (what must be TRUE):

  1. A REST fuzzer scan against any target routes through `validate_external_url`; a probe to a metadata IP is blocked and logged, not silently attempted
  2. GCP `metadata.google.internal` and its documented aliases appear in the always-blocked set and are rejected by the validator
  3. A path-shaped image ref such as `etc/passwd` is rejected before reaching syft; a well-formed ref passes normally
  4. A request with `allow_internal=True` cannot reach the console's own `addr:port` (reflective self-SSRF blocked, as a peer to the always-blocked metadata check); non-console loopback targets remain reachable under `allow_internal=True` so the chaos lab (`--allow-internal-targets`) keeps working — per locked decision D-01 (supersedes the original "block all loopback" wording)
  5. DNS resolution and connection use a pinned address (or equivalent mitigation); a rebinding attempt that changes the IP after validation is blocked or documented with a compensating control

**Plans**: 4 plans

- [x] 123-00-PLAN.md — Wave 0 RED test scaffolds for SSRF-01..05 (Nyquist gate)
- [x] 123-01-PLAN.md — url_allowlist resolved_ip + console self-SSRF block + QUIRK_SERVE_HOST + SSRF-02 regression lock
- [x] 123-02-PLAN.md — validate_image_ref path-shaped-ref guard (SSRF-03)
- [x] 123-03-PLAN.md — rest_fuzzer raw-socket validate+pin + PinnedIPAdapter + smtplib compensating-control doc (SSRF-01/05)

#### Phase 124: Scoring & Evidence Correctness

**Goal**: The readiness score, QRAMM assessments, and CBOM evidence tally produce accurate results across all algorithm types, partial answers, and distributed deployments — no aborts, no inflation, no silent data gaps
**Depends on**: Nothing (Wave A, disjoint from Phase 123 code paths)
**Requirements**: SCOREFIX-01, SCOREFIX-02, SCOREFIX-03, SCOREFIX-04, SCOREFIX-05
**Success Criteria** (what must be TRUE):

  1. A scan that includes a finding with a missing `severity` field still produces a complete readiness score — no KeyError, no score abort
  2. A QRAMM session with some practices unanswered in a dimension scores lower than a fully-answered dimension with the same answered values — unanswered practices are not ignored in the weakest-link calculation
  3. An endpoint using Ed25519 or Ed448 contributes agility credit in the evidence key-type tally, visible in the score decomposition
  4. A TLS cipher string of `AES-128-CCM_8` is classified as a truncated-tag AEAD variant distinct from standard CCM in the CBOM output
  5. In a multi-sensor console, two sensors' scan cohorts produce separate QRAMM evidence populations — evidence from Sensor A does not appear in Sensor B's evidence bridge output

**Plans**: 4 plans

- [x] 124-00-PLAN.md — Wave 0 RED scaffolds (5 test files for SCOREFIX-01..05)
- [x] 124-01-PLAN.md — SCOREFIX-01 (severity KeyError) + SCOREFIX-02 (QRAMM partial-answer inflation)
- [x] 124-02-PLAN.md — SCOREFIX-03 (EdDSA agility credit) + SCOREFIX-04 (CCM_8 AEAD decomposition)
- [x] 124-03-PLAN.md — SCOREFIX-05 (session-scoped evidence-bridge cohort)

#### Phase 125: Posture Defaults + Distributed Edge Cases

**Goal**: The default deployment posture is safe (not permissive), IAM permission gaps surface as explicit findings, and two distributed race conditions are deterministically resolved
**Depends on**: Nothing (Wave A, disjoint from Phases 123–124 code paths)
**Requirements**: POSTURE-01, POSTURE-02, DIST-01, DIST-02
**Success Criteria** (what must be TRUE):

  1. Starting the dashboard with an empty auth token bound to a non-loopback interface either refuses to start with a clear error message or prints a loud startup warning that is impossible to miss in operator logs
  2. A scan against a GCP or AWS account where one API returns a permission-denied error produces an explicit scan-coverage finding (not a clean result) — the operator can see which APIs were inaccessible
  3. When two sensors push results with identical `scanned_at` timestamps, the merge produces a deterministic result (latest-push-per-sensor tiebreak) and the merged CBOM is identical on repeated runs with the same input
  4. A notification fan-out where one event's `run.scan_id` commit fails does not drop subsequent events — other events in the same cycle still dispatch successfully

**Plans**: TBD

#### Phase 126: Audit Ledger Closeout + Dashboard Quality Green-Up

**Goal**: Zero `deferred → v5.7` rows remain open in the audit ledger (each has a fix or a structured disposition), and the Dashboard Quality CI workflow is green on `main`
**Depends on**: Phases 123, 124, 125 (many ledger rows are closed by those phases; this phase closes the remainder and cleans up CI)
**Requirements**: LEDGER-01, DASHQ-01, DASHQ-02
**Success Criteria** (what must be TRUE):

  1. Every row in `.planning/audit-2026-05-27/AUDIT-TASKS.md` previously marked `deferred → v5.7` is either marked `[x] closed` with a commit SHA or carries an explicit written disposition (won't-fix with rationale, or deferred to a named future milestone)
  2. The Dashboard Quality CI workflow passes on `main` with no axe-core a11y violations suppressed without a documented disposition
  3. The Dashboard E2E smoke job passes on `main`; any previously failing smoke flows are repaired or their scope is corrected with a written rationale committed to the phase artifacts

**Plans**: 4 plans

- [x] 143-01-PLAN.md — Persistent scan-date badge in the dashboard sidebar (TAIL-01)
- [x] 143-02-PLAN.md — Server-enforced trusted-targets allowlist at both scan entry points (TAIL-02, TAIL-04)
- [x] 143-03-PLAN.md — Windows Authenticode signing in the release CI (TAIL-03, TAIL-04)
- [x] 143-04-PLAN.md — Docs + Obsidian sync for the badge, allowlist, and signing pipeline (TAIL-01/02/03)

**UI hint**: yes

#### Phase 127: Hardware Fingerprinting Foundation

**Goal**: The scanner identifies hardware devices from SSH banners and HTTP management interfaces, grades every match with a confidence level, and resolves identified devices against a staleness-gated PQC compatibility matrix — with a working chaos lab profile to validate the full pipeline
**Depends on**: Phase 126 (Wave A complete)
**Requirements**: HWCOMPAT-01, HWCOMPAT-02, HWCOMPAT-06
**Success Criteria** (what must be TRUE):

  1. A scan against an SSH service with a Cisco, F5, Juniper, Palo Alto, Fortinet, or HPE iLO banner produces a `HardwareDevice` row with `vendor`, `model`, `pqc_status`, `eol_date`, and a `confidence` grade (`high`/`medium`/`low`/`unknown`); a service with an unrecognized banner produces a `vendor=Unknown` row (never suppressed)
  2. The `hwcompat` chaos lab profile starts cleanly, and running a scan against it produces at least one identified device with PQC matrix data and at least one `vendor=Unknown` device from an unrecognized service
  3. The `lab.sh` `ALL_PROFILES` list includes `hwcompat`, `./lab.sh up hwcompat` works without script edits, and `expected_results_hwcompat.md` documents the expected scanner findings for that profile
  4. The CI staleness assertion for `hardware_meta.py` fails the build when `last_verified` is older than 90 days — mirroring the `model_meta.py` staleness gate behavior
  5. `hardware_meta.py` carries at least the appliance-first vendor set (F5 BIG-IP, Cisco ASA/FTD, Palo Alto PAN-OS, Fortinet FortiGate, Juniper SRX/MX, HPE iLO 3/4/5/6/7, IPMI, Thales Luna HSM) with per-row `last_verified` and `source_url`

**Plans**: TBD

#### Phase 128: Remediation Tiers + Report Surfacing

**Goal**: Every fingerprinted device receives a consulting-grade remediation tier with CNSA 2.0 timeline context, visible in the CLI summary, HTML/PDF/DOCX reports, executive narrative, and the dashboard `/hardware` tab — hardware findings are advisory-only and do not enter the readiness score
**Depends on**: Phase 127 (HardwareDevice table and PQC matrix required for tier assignment)
**Requirements**: HWCOMPAT-04, HWCOMPAT-07
**Success Criteria** (what must be TRUE):

  1. Every `HardwareDevice` row in a scan result carries a remediation tier (Tier 1 / Tier 2 / Tier 3 / Tier N/A) and `low`- or `unknown`-confidence devices are capped at Tier 2; a Tier 1 finding includes explicit CNSA 2.0 deadline context
  2. Hardware findings appear in the CLI scan summary, the HTML report findings table, and the PDF/DOCX export — sourced through the `_build_finding()` chokepoint with non-empty `description` and `remediation` fields
  3. The executive narrative paragraph in the report addresses hardware PQC posture when any hardware device is detected — at minimum a summary of the fleet's Tier 1 / Tier 2 / Tier 3 breakdown
  4. The `/hardware` dashboard tab renders a per-device table showing vendor, model/firmware, PQC status, remediation tier, and confidence for all devices in the latest scan
  5. A grep over `SCORE_WEIGHTS` and `compute_readiness_score()` finds zero hardware counter references — advisory-only lock is CI-verifiable

**Plans**: 4 plans

- [x] 128-00-PLAN.md — Wave 0 RED test scaffold for assign_tier() tier taxonomy + confidence cap (Nyquist gate)
- [x] 128-01-PLAN.md — Tier core: hardware_tier.py assign_tier() + remediation_tier column + run_scan.py assignment & advisory CLI summary
- [x] 128-02-PLAN.md — Report surfacing: ExecContent.hardware_devices + writer population + HTML/executive/DOCX advisory rendering
- [x] 128-03-PLAN.md — Dashboard /hardware tab: HardwareFinding schema + route + types + page + sidebar + route

**UI hint**: yes

#### Phase 129: Crypto-Bridge Detection + CBOM Pass 4

**Goal**: The scanner identifies when a legacy device sits behind a PQC-capable gateway and assigns a conservative classification; hardware devices appear as first-class `ComponentType.FIRMWARE` components in the CBOM so procurement teams can act on machine-readable fleet data
**Depends on**: Phases 127, 128 (HardwareDevice objects and tier data required for both bridge detection and CBOM enrichment)
**Requirements**: HWCOMPAT-03, HWCOMPAT-05
**Success Criteria** (what must be TRUE):

  1. When a scan finds a PQC-capable gateway in front of a directly-reachable legacy backend, the backend is classified `partial_only` (never `upstream_mitigated`) — the conservative default unit test passes
  2. When the backend is not directly reachable in the same scan, the gateway may classify as `upstream_mitigated`; this designation appears with a report disclaimer advising direct reachability verification
  3. Bridge detection operates correctly in both single-sensor and distributed-merge runs — the `_detect_crypto_bridges()` function is called from both `run_scan.py` and `merge/scan.py`
  4. The CBOM output for a scan with identified hardware devices includes `ComponentType.FIRMWARE` components in Pass 4, each carrying `quirk:hw-vendor`, `quirk:hw-pqc-supported`, and `quirk:hw-remediation-tier` properties; `"HARDWARE"` is present in Pass 2 and Pass 3 skip-lists
  5. The CBOM output validates against the CycloneDX 1.6 schema with hardware components present — the existing schema validation gate does not regress

**Plans**: TBD

### Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 123. SSRF & URL-Allowlist Hardening | 4/4 | Complete   | 2026-06-13 |
| 124. Scoring & Evidence Correctness | 4/4 | Complete | 2026-06-13 |
| 125. Posture Defaults + Distributed Edge Cases | 2/2 | Complete | 2026-06-13 |
| 126. Audit Ledger Closeout + Dashboard Quality Green-Up | 1/1 | Complete | 2026-06-13 |
| 127. Hardware Fingerprinting Foundation | 4/4 | Complete   | 2026-06-14 |
| 128. Remediation Tiers + Report Surfacing | 4/4 | Complete   | 2026-06-14 |
| 129. Crypto-Bridge Detection + CBOM Pass 4 | 5/5 | Complete    | 2026-06-14 |

Audit: 24/24 requirements, 0 blockers (`.planning/milestones/v5.7-MILESTONE-AUDIT.md`). Full details: `.planning/milestones/v5.7-ROADMAP.md`.

</details>

---

<details>
<summary>✅ v5.8 Audit Closeout + SNMP Fingerprinting (Phases 130–134) — SHIPPED 2026-06-18</summary>

**v5.8** drained the 15 remaining audit rows from the 2026-05-27 ledger (Wave A: codesign column rename, fuzzer dedup, Kerberos RFC comment, DOCX exception logging, SOURCE algo-hint granularity, rate-limit idle eviction, job target 422 validation, sensor-push re-validation, SSRF TOCTOU doc, sensor CLI UUID guard, SIEM SSRF guard, console enroll single-session, CEF escaping, auth token sessionStorage + CSP header, HTML cover-page fix), then shipped SNMP fingerprinting as the third hardware signal source and the CBOM DEVICE/FIRMWARE component hierarchy (Wave B). 5 phases, 21 plans, 22/22 requirements, 73 commits. Tag `v5.8.0`. B-01 distributed SNMP field projection gap closed in `6eb512e` before tag.

### Phases

- [x] **Phase 130: Code Quality & Scanner Fixes** — codesign column rename (AUDIT-01), REST fuzzer dedup (AUDIT-02), Kerberos TCP→UDP comment (AUDIT-03), DOCX exception logging (AUDIT-04), SOURCE algo-hint granularity (AUDIT-05) (completed 2026-06-14)
- [x] **Phase 131: Dashboard & Delivery Hardening** — rate-limit idle eviction (AUDIT-06), job target 422 validation (AUDIT-07), sensor-push re-validation (AUDIT-08), SSRF TOCTOU doc (AUDIT-09), sensor CLI UUID guard (AUDIT-10), SIEM SSRF guard (AUDIT-11), console enroll single-session (AUDIT-12), CEF escaping (AUDIT-13) (completed 2026-06-15)
- [x] **Phase 132: Frontend & Report Polish** — auth token localStorage → sessionStorage + CSP header (AUDIT-14), HTML cover-page layout fix (AUDIT-15) (completed 2026-06-15)
- [x] **Phase 133: SNMP Hardware Fingerprinting** — opt-in `[hw]` extras (pysnmp>=7.1.0,<8 + sysdescrparser), 3-OID probe (sysDescr/sysName/sysObjectID), vendor regex + sysdescrparser dual-path, 4 HardwareDevice ORM columns, Cisco IOS Net-SNMP chaos lab container, CBOM quirk:hw-snmp-oid property, staleness gate (completed 2026-06-15)
- [x] **Phase 134: CBOM DEVICE Component Hierarchy** — DEVICE parent + FIRMWARE children via Component.components; HardwareComponent Pydantic schema on /api/scan/latest; dashboard CBOM tab HardwareInventory (completed 2026-06-16)

### Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 130. Code Quality & Scanner Fixes | 4/4 | Complete | 2026-06-14 |
| 131. Dashboard & Delivery Hardening | 5/5 | Complete | 2026-06-15 |
| 132. Frontend & Report Polish | 3/3 | Complete | 2026-06-15 |
| 133. SNMP Hardware Fingerprinting | 5/5 | Complete | 2026-06-15 |
| 134. CBOM DEVICE Component Hierarchy | 3/3 | Complete | 2026-06-16 |

Audit: 22/22 requirements, 0 blockers (`.planning/milestones/v5.8-MILESTONE-AUDIT.md`). Full details: `.planning/milestones/v5.8-ROADMAP.md`.

</details>

---

<details>
<summary>✅ v5.9 Documentation Audit & Living Docs System (Phases 135–138 + 138.1/138.2) — SHIPPED 2026-07-30</summary>

Full phase details, success criteria, and gap-closure history archived to `.planning/milestones/v5.9-ROADMAP.md`. Requirements archived to `.planning/milestones/v5.9-REQUIREMENTS.md`. Audit: `.planning/milestones/v5.9-MILESTONE-AUDIT.md`.

Audited every user-facing doc against what shipped in v5.4–v5.8, refreshed README/getting-started/architecture/operators-guide/report-interpretation, added a net-new `docs/admin-guide.md`, documented the chaos-lab hwcompat profile, and embedded a permanent doc-hygiene checklist in `CLAUDE.md`. Two gap-closure phases (138.1 CORE-04 tier-inversion fix, 138.2 LIVE-03 vault re-sync) closed defects the milestone's own audit found — 16/16 requirements satisfied, tech_debt disposition (deferred human-UAT only, no content gaps).

</details>

---

<details>
<summary>✅ v5.10 Hardware Lifecycle Depth (Phases 139–143) — SHIPPED 2026-08-03</summary>

Full phase details, gap-closure history, and success criteria archived to `.planning/milestones/v5.10-ROADMAP.md`. Requirements archived to `.planning/milestones/v5.10-REQUIREMENTS.md`. Audit: `.planning/v5.10-MILESTONE-AUDIT.md`.

Closed out the Hardware Compatibility & Lifecycle Remediation arc opened in v5.7/v5.8: SNMPv3
auth+priv support (139), evidence-backed SNMP-confirmed bridge mitigation (140), OT/ICS
Modbus/BACnet fingerprinting (141 — required two post-ship gap-closure rounds after a live
checkpoint caught a deeper orchestration bug the plan-checker had missed), advisory-only firmware
CVE correlation (142), and a small independent dashboard/security tail (143). 36 plans, 23/23
requirements satisfied, tech_debt disposition (0 blockers, 4 tracked non-blocking items).

</details>

---

## Backlog

Items to be organized into future milestones. Organized by theme.

### Release & Verification Integrity (v5.12 candidates)

Promoted into the v5.12 milestone (see Current Milestone section above) — kept here for
backlog-history continuity:

- Windows release asset gap (v5.11.0 shipped no Windows build) → RELEASE-04 (Phase 148)
- Release dry-run / pre-tag validation → RELEASE-02 (Phase 148)
- Tag hygiene guard (`v5.9`/`v5.10.0` tag drift) → RELEASE-03 (Phase 148)
- Actual tag cut proving the repaired pipeline → RELEASE-01 (Phase 153)
- ~102 pre-existing suite failures → SUITE-01/02/03 (Phases 149–150)
- Phase-completion artifact enforcement (VERIFICATION.md/VALIDATION.md/UAT-SERIES.md gaps) →
  ARTIFACT-01/02/03 (Phase 151)

- `phases.clear` destructive-op guard — see `.planning/milestones/v5.11-phases/ARCHIVE-MANIFEST.md`
  incident → ARTIFACT-04 (Phase 151)

- DISC-09 segmented-network chaos lab profile + Phase 144 nmap timing artifact → DISC-09/DISC-10
  (Phase 152)

- Interactive nmap-discovery-first default N→Y → DISC-11 (Phase 152)

**Explicitly out of scope for v5.12:**

- DISC-08 sub-batch (mid-discovery) checkpoint/resume granularity — accepted boundary; batches are
  cheap (~30–60s) relative to what the checkpoint system protects. Revisit only if batch cost
  grows.

- Continuous hardware lifecycle monitoring — v5.13 capability anchor, needs its own research pass
  first.

- SaaS multi-tenancy — still parked, no business-model signal.

### Hardware Compatibility & Lifecycle Remediation (v5.13+)

- **Continuous hardware lifecycle monitoring** — least-scoped backlog item; needs its own research
  pass to determine whether it is a new scanner surface or a scheduling/diffing layer over data
  QUIRK already collects (the answer changes its size roughly 3x); v5.13 capability anchor.

~~OT/ICS resume-checkpoint gap~~ and ~~CVE table BACnet key coverage~~ — both closed by v5.11
Phase 147 as DRAIN-01/DRAIN-02; struck from this list 2026-08-11.

### SaaS Platform (Future Milestone)

- [ ] Multi-tenant architecture design
- [ ] Scan job queue (Celery + Redis or similar)
- [ ] User auth and org management
- [ ] Cloud deployment (Docker Compose → Kubernetes)
- [ ] Hosted reporting and CBOM storage

</content>
