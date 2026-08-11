# Requirements: QU.I.R.K. — v5.12 Release & Verification Integrity

**Defined:** 2026-08-11
**Core Value:** Produce a complete, defensible cryptographic inventory with a CBOM deliverable
and quantum-readiness score that a consultant can hand to a client in under two hours.

**Milestone framing:** every requirement below fixes a *measurement* failure rather than a
capability gap. QU.I.R.K.'s stated bar is "every detected weakness is real, every missed weakness
is intentional" (Primetime gate 2) — this milestone applies that same bar to the project's own
release, test, and verification signals, all of which were found silently no-opping during the
v5.11 cycle.

## v5.12 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Release Integrity (anchor)

- [ ] **RELEASE-01**: Cutting a release tag produces a Windows operator zip attached to the
      GitHub Release — the repaired signing self-test (`1a6effc`) is proven by an actual green
      run, not by inspection
- [ ] **RELEASE-02**: A broken release job is caught *before* a tag is cut — a dry-run or
      equivalent pre-release check exercises the release path on demand, so a defect cannot
      first surface on an immutable tag
- [ ] **RELEASE-03**: A malformed or unpushed release tag cannot silently skip the release
      pipeline — tag format is guarded and a missing release run is detectable
      (`v5.9` never matched `v*.*.*`; `v5.10.0` was never pushed; three milestones shipped no
      Windows build with zero signal)
- [ ] **RELEASE-04**: The v5.11.0 release is retroactively completed or explicitly dispositioned
      — the operator can tell from the GitHub Releases page whether a Windows artifact exists for
      a given shipped version, with no silent gaps in the release history

### Test Signal Integrity

- [ ] **SUITE-01**: Every pre-existing full-suite failure (~102, red since roughly Phase 97) has
      an explicit written disposition — fixed, quarantined with a reason, or deleted as obsolete
- [ ] **SUITE-02**: `pytest -q` on a clean supported environment produces a green baseline, so a
      new failure is visible as a new failure
- [ ] **SUITE-03**: The green baseline is held by CI — a newly-introduced failing test fails the
      build rather than joining a permanent red background

### Phase Artifact Integrity

- [ ] **ARTIFACT-01**: A phase cannot be reported complete while its VERIFICATION.md is missing —
      the gap surfaces at phase close rather than at milestone-audit time (v5.11 Phase 145 shipped
      with no VERIFICATION.md and was caught weeks later)
- [ ] **ARTIFACT-02**: A phase's VALIDATION.md reflects post-execution reality before the phase
      closes — pre-execution `pending` rows and a stale `nyquist_compliant: false` cannot survive
      phase completion (v5.11 Phase 147)
- [ ] **ARTIFACT-03**: A phase that shipped user-facing behavior cannot close without its
      `docs/UAT-SERIES.md` series entry (v5.11 Phase 144, the anchor phase, shipped without one)
- [ ] **ARTIFACT-04**: A destructive planning operation refuses to run when the archive it
      depends on is absent or empty — `phases.clear` deleted ~39 unrecoverable v5.11 phase
      artifacts on 2026-08-11 because `milestone.complete` had reported
      `archived.phases: false` and nothing gated on it
      (see `.planning/milestones/v5.11-phases/ARCHIVE-MANIFEST.md`)

### Discovery Empirical Closure

- [ ] **DISC-09**: A segmented-network chaos lab profile exists so chunked discovery and
      partial-result tolerance can be exercised against realistic unreachable hosts rather than
      unassigned loopback aliases (deferred from v5.11)
- [ ] **DISC-10**: The Phase 144 nmap timing-engine artifact is settled empirically against
      DISC-09's profile — either it does not reproduce on a realistic segmented network (finding
      closed), or it does and a scoped mitigation is chosen with its false-negative tradeoffs
      documented
- [ ] **DISC-11**: Interactive setup opts users into nmap discovery by default — the current
      `default=False` on "Run nmap port discovery first?" silently routes users past the entire
      v5.11 chunked-discovery and liveness path

## Future Requirements

Deferred to a later milestone.

- **Continuous hardware lifecycle monitoring** — v5.13 capability anchor. Needs its own research
  pass first: is it a new scanner surface, or a scheduling/diffing layer over data QUIRK already
  collects? The answer changes its size roughly 3x.
- **DISC-08**: Sub-batch (mid-discovery) checkpoint/resume granularity — accepted boundary;
  batches are cheap (~30–60s) relative to what the checkpoint system protects. Revisit only if
  batch cost grows.

## Out of Scope

| Feature | Reason |
|---------|--------|
| SaaS multi-tenancy | Still parked — no business-model signal, unchanged since v5.4 |
| New scanner families / detection capability | This is an ops cycle; the 2:1 capability/ops ratio is eleven milestones overdue for ops (last true ops milestone was v5.0, 2026-05-22) |
| Rewriting the GSD tooling itself | ARTIFACT-01..04 are enforcement gates on QUIRK's own workflow, not a fork or reimplementation of GSD |
| Recovering the lost v5.11 phase artifacts | Unrecoverable — untracked, not in trash, no disk copy. The decision record survives in the milestone audit, ROADMAP archive, MILESTONES.md, UAT-SERIES.md, and the Obsidian phase notes; only the raw working papers are gone |
| Republishing / yanking v5.11.0 on PyPI | The Python package published correctly; only the Windows asset is missing. RELEASE-04 dispositions that gap rather than reissuing the version |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| RELEASE-01 | TBD | Pending |
| RELEASE-02 | TBD | Pending |
| RELEASE-03 | TBD | Pending |
| RELEASE-04 | TBD | Pending |
| SUITE-01 | TBD | Pending |
| SUITE-02 | TBD | Pending |
| SUITE-03 | TBD | Pending |
| ARTIFACT-01 | TBD | Pending |
| ARTIFACT-02 | TBD | Pending |
| ARTIFACT-03 | TBD | Pending |
| ARTIFACT-04 | TBD | Pending |
| DISC-09 | TBD | Pending |
| DISC-10 | TBD | Pending |
| DISC-11 | TBD | Pending |
