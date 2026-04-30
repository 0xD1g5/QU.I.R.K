# Requirements — Milestone v4.5: Reliability & Gap Closure

**Goal:** Close v4.4 deferred items, harden scanner/CBOM/dashboard correctness, and
automate the long-tail UAT debt — putting QU.I.R.K. in solid shape before the next
capability and performance milestones.

**Phase numbering:** continues from Phase 38.

---

## v4.5 Requirements

### Gap Closure

Close v4.4 known deferred items so the v4.4.0 ship audit shows zero red.

- [x] **GAP-01**: User running an identity scan sees SAML/OIDC entries restored in `/api/scan/latest` `identity_findings[]` (closes DEF-v4.4-02 / ISSUE-3 from Phase 24).
- [x] **GAP-02**: After GAP-01 lands, the deferred SAML scan-window pytest is re-enabled and passes; the test goes from `skip`/`xfail` to GREEN in CI.
- [ ] **GAP-03**: Phase 36 `wave_0_complete: false` is flipped to `true` in `36-VALIDATION.md` and the matrix shows `nyquist_compliant: true, wave_0_complete: true` (closes DEF-v4.4-01).
- [ ] **GAP-04**: User opens the dashboard and sees a "Data at Rest" tab alongside the existing tabs, listing DB / object storage / K8s secrets / Vault findings with the existing v4.3 data shape (closes DASH-05 deferred from Phase 27).

### CI Stability

Eliminate test flakiness and deferred tests so CI green is a meaningful signal.

- [x] **CI-01**: User runs `pytest` locally or in CI and sees zero `skip`/`xfail` markers on tests that were deferred for code reasons (live-infra skips remain — see UAT-* below).
- [ ] **CI-02**: Test suite executes deterministically — no test is order-dependent, no test relies on global state from another test, no test uses real time/sleep beyond what's necessary. Audit identifies and fixes any such cases.
- [x] **CI-03**: Long-running and slow tests are marked with `pytest.mark.slow` (or equivalent) so the default `pytest` run finishes in under 60 seconds on a developer machine.

### Scanner Robustness

Improve graceful degradation across all scanners so partial failures don't poison full scans.

- [x] **ROBUST-01**: User runs a scan against a target where one scanner's optional dependency is missing (e.g., `[motion]` not installed); the scan completes, surfaces a clear advisory, and the other scanners produce normal output.
- [x] **ROBUST-02**: User runs a scan against a slow or partially-unreachable target; each scanner respects a documented per-target timeout budget and the overall scan does not stall beyond a documented upper bound.
- [x] **ROBUST-03**: User runs a scan where a scanner raises an unexpected exception; the exception is captured into `scan_errors[]` with scanner name + target + reason, and the rest of the scan continues to completion.
- [x] **ROBUST-04**: Timeout/retry policy across scanners is consistent and documented (one source of truth for default timeout, retry count, backoff) — audit identifies and reconciles divergences.

### CBOM Correctness

Audit CBOM output against CycloneDX 1.6 spec, classifier coverage, and golden snapshots.

- [ ] **CBOM-01**: CBOM JSON and XML outputs validate against the official CycloneDX 1.6 schema for every shipped chaos lab profile; validation is automated as a pytest check.
- [ ] **CBOM-02**: User reviews the algorithm classifier coverage report: every algorithm name observed in test fixtures and chaos labs is mapped to a NIST PQC classification, with no `unknown` fallbacks for in-scope cases.
- [ ] **CBOM-03**: Golden snapshot drift between v4.4 and v4.5 is reviewed; any change is intentional, documented, and accompanied by a snapshot update commit with rationale.
- [ ] **CBOM-04**: Pass-2 / Pass-3 skip-list logic is unit-tested for all motion plaintext labels and all v4.3 DAR skip cases — coverage gaps closed.

### Dashboard Polish

Eliminate visible papercuts across the React dashboard.

- [ ] **DASH-01**: User opens `/motion`, `/trends`, `/findings`, `/data-at-rest` (GAP-04), and other top-level routes; browser console shows zero errors and zero React warnings.
- [ ] **DASH-02**: Each route displays an explicit loading state on first paint and an explicit empty state when data is missing — no flashes of "no data" before data arrives.
- [ ] **DASH-03**: Dashboard meets baseline accessibility: keyboard navigation works on all interactive elements, focus indicators are visible, semantic heading order is correct, color contrast on findings tables passes WCAG AA — verified by axe-core or equivalent automated check.

### Chaos Lab Parity

Bring `quantum-chaos-enterprise-lab/` up to date with everything that shipped in v4.3 + v4.4 so consultants running the lab see scanner-equivalent coverage.

- [x] **LAB-01**: User runs `./lab.sh all` and the command starts every chaos lab profile that ships in the repo, including v4.3 additions (`database`, `storage-s3`, `vault`) and v4.4 additions (`email`, `broker`); the profile list in `lab.sh` matches `docker-compose.yml` 1:1 with no missing profiles.
- [x] **LAB-02**: User opens `quantum-chaos-enterprise-lab/README.md` and sees every shipped profile (v4.0 → v4.4) documented with port assignments, expected scanner findings, and any required setup steps; v4.3 + v4.4 profiles are not absent.
- [x] **LAB-03**: A successor to `expected_results_v3.md` (e.g., `expected_results_v4.md`) documents the expected scanner output oracle for v4.3 + v4.4 profiles (DB, object storage, K8s, Vault, email, broker) — used by chaos lab UAT runs and by GAP-04 / UAT-01 / UAT-02 / UAT-03 verification.
- [x] **LAB-04**: `./lab.sh status` and `./lab.sh logs <service>` work cleanly against every v4.3 + v4.4 profile (no broken service names, no orphan containers from renamed services).

### UAT Debt Automation

Burn down the 14 carry-over UAT/verification gaps where automation is feasible without live cloud credentials.

- [ ] **UAT-01**: Phase 27 DB UAT scenarios run against the existing `database` chaos lab profile in CI — previously deferred items move from `pending`/`partial` to `passing` where the chaos lab covers the scenario.
- [ ] **UAT-02**: Phase 29 K8s UAT scenarios run against a minikube (or kind) fixture in CI — previously deferred items move to `passing` where the local cluster can simulate the case; cloud-managed encryption (EKS/GKE/AKS) cases remain documented as cloud-only.
- [ ] **UAT-03**: Phase 25 (identity) and Phase 30 (Vault) UAT scenarios that already have chaos lab profiles are re-run and updated; failing scenarios get fixes or explicit "cloud-only" justification.
- [ ] **UAT-04**: The `## Deferred Items` table in `STATE.md` is updated to reflect what was automated, what remains cloud-bound, and what was closed — net reduction of at least 50% of the 14 carry-over items.

---

## Future Requirements (Deferred)

Items intentionally deferred from v4.5 — surfaced for future milestones.

- New scanner coverage (additional cloud broker probes, live-cluster K8s motion scanning)
- Performance & scale work (large-network optimization, parallelism rework, scan resumption)
- CBOM v2 features (signing, diff between scans, SPDX export, per-finding remediation playbooks)
- Compliance mapping (NIST 800-53, PCI, HIPAA crosswalk to findings)
- Scheduled scanning, distributed agents, multi-tenancy / SaaS scaffolding
- Cloud-credentialed UAT scenarios (live S3 / Azure Blob / GCP / Vault) — remain deferred until a CI cloud sandbox exists

## Out of Scope (this milestone)

| Feature | Reason |
|---------|--------|
| New scanners (broker depth, live K8s motion, ADCS, Confluent Cloud) | Reliability milestone — no new scanning surface |
| Cloud-credentialed UAT runs | No CI cloud sandbox exists; would require ongoing infra cost |
| CBOM schema evolution (v2, signing, SPDX) | Deliverable evolution belongs in a dedicated milestone |
| Performance optimization | Reserved for a dedicated scale milestone |
| SaaS / multi-tenancy | Future strategic milestone |
| Mobile app | Web-first; future milestone |

---

## Traceability

Requirements → phases mapping filled in by roadmapper 2026-04-29.

| REQ-ID | Phase | Status |
|--------|-------|--------|
| GAP-01 | Phase 38 | Complete |
| GAP-02 | Phase 38 | Complete |
| GAP-03 | Phase 38 | pending |
| GAP-04 | Phase 39 | pending |
| CI-01 | Phase 41 | Complete |
| CI-02 | Phase 41 | pending |
| CI-03 | Phase 41 | Complete |
| ROBUST-01 | Phase 41 | Complete |
| ROBUST-02 | Phase 41 | Complete |
| ROBUST-03 | Phase 41 | Complete |
| ROBUST-04 | Phase 41 | Complete |
| CBOM-01 | Phase 42 | pending |
| CBOM-02 | Phase 42 | pending |
| CBOM-03 | Phase 42 | pending |
| CBOM-04 | Phase 42 | pending |
| DASH-01 | Phase 43 | pending |
| DASH-02 | Phase 43 | pending |
| DASH-03 | Phase 43 | pending |
| LAB-01 | Phase 40 | Complete |
| LAB-02 | Phase 40 | Complete |
| LAB-03 | Phase 40 | Complete |
| LAB-04 | Phase 40 | Complete |
| UAT-01 | Phase 44 | pending |
| UAT-02 | Phase 44 | pending |
| UAT-03 | Phase 44 | pending |
| UAT-04 | Phase 44 | pending |

---
*Last updated: 2026-04-29 — v4.5 milestone initialized*
