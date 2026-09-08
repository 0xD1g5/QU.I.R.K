# Requirements: QU.I.R.K. — Milestone v5.20 Release & Correctness Drain

**Defined:** 2026-09-07
**Core Value:** Complete, defensible cryptographic inventory with CBOM deliverable and
quantum-readiness score — handed to a client in under two hours.

**Milestone goal:** Ship v5.19's content as a real release, then make the score and the scanners
stop overstating — no unassessed domain scores full marks, no probe silently fails, no config
silently no-ops.

**Sourcing:** every requirement traces to `.planning/HORIZON.md`'s Open-Item Ledger (canonical as
of 2026-09-07) and `.planning/reports/backlog-reconciliation-2026-09-07.md`. No net-new scope.

## v5.20 Requirements

### Release

- [x] **REL-01**: Operator can `pip install quirk-scanner==5.19.0` — `v5.19.0` tag cut, release
      workflow green (PyPI + Windows asset), with all bump surfaces updated in the same change:
      `pyproject.toml`, README heading/What's New, `CHANGELOG.md` entry, `docs/UAT-SERIES.md`
      UAT-1-02 pass criteria + document header. Editable reinstall (`pip install -e . --no-deps`)
      run so `tests/test_version.py` passes. [ledger: v5.19 untagged]

### Scoring Integrity

- [x] **SCORE-06**: A readiness-score domain with zero collected evidence no longer contributes a
      full 25/25 subscore — assessment coverage is reflected in (or explicitly disclosed alongside)
      the headline number, such that the full chaos lab can no longer score 96/100. The formula
      change ships with a recorded migration/communication decision (historical numbers move) —
      deliberate design, not a drive-by. [999.95, P1]
- [x] **SCORE-07**: Dashboard `ScoreGauge.tsx` band thresholds derive from the same single producer
      as `quirk/scoring/severity_bands.py` — no frontend/backend band divergence, guarded by a test
      that fails if either side drifts. [999.92; completes v5.19 SCORE-05's deferred frontend half]

### Correctness Drain

- [ ] **TRIAGE-03**: The `config-lab-core.yaml` example in `docs/chaos-lab.md` loads verbatim
      against the current config schema (docs==code, with a guard consistent with the existing
      drift-gate pattern). [999.93]
- [ ] **TRIAGE-04**: Scan-config port-list fields coerce quoted YAML values to int on the load path
      (or reject them loudly) — a `"8444"` override can no longer silently no-op. All port fields
      covered, not one-field patching. [999.97 / 186-REVIEW IN-01]
- [ ] **TRIAGE-05**: The port-22-in-`ports_tls` question in `docs/sample-config.yaml` is resolved —
      either removed or kept with the TLS-on-22 probe rationale recorded where the reconciliation
      audit can see it. [BACK-59]
- [ ] **TRIAGE-06**: Broker scanner (Kafka/RabbitMQ/Redis) accepts operator-specified ports instead
      of hardcoded defaults, verified against the chaos lab's mapped ports (29092/25671/26380).
      [BACK-68, broker sense]
- [ ] **TRIAGE-07**: Modbus fingerprinting activates end-to-end — the Step-4 gate is satisfiable
      and a live (or lab) Modbus target produces hardware fingerprint output. [999.91]
- [ ] **TRIAGE-08**: BACK-51 (migration-planner dual categorization) is dispositioned with recorded
      evidence — one targeted check; a "no user-visible duality remains" verdict closes it without
      code. [BACK-51, UNCERTAIN in audit]
- [ ] **TRIAGE-09**: A derived CI gate enumerates every BACK-*/999.* ID from the archived roadmaps
      and backlog at run time (never a hand-written list) and fails when any ID is neither
      closed-with-evidence nor listed in HORIZON.md's Open-Item Ledger. Keys on title+ID (BACK-68
      names two unrelated items); counts requirement-section-heading citations as closure. Closes
      the reconciliation todo's step 3. [todo: backlog-reconciliation-and-derived-gate]

## Deferred (tracked in HORIZON.md Open-Item Ledger — not in v5.20)

- **999.100** Executive Verdict layer (implemented on `origin/UX-Updates`, flag-gated)
- **999.96** Ten connectors unreachable from dashboard + silent skip observability
- **todo: dashboard-cert-view-phantom-tls-rows** — phantom certs reach the client PDF
- **999.98 → 999.99** SPKI fingerprint → Quantum Exposure Map (milestone-sized arc)
- **999.101/BACK-07, 999.102/BACK-88-drawer, BACK-01, BACK-03, BACK-08** — UX/presentation set
- **GSD tooling todos** — `phase.complete` semantic class, `planned-phase` misleading return,
  bold-field unscoped latent

## Out of Scope

| Feature | Reason |
|---------|--------|
| Score formula changes beyond evidence-coverage handling | SCORE-06 is a scoped correction, not a rebalance; profile multipliers and weights unchanged |
| Ticketing readback / SaaS multi-tenancy | Parked since v5.4 — no business-model signal |
| Detection breadth (AD CS live, S/MIME content, passive capture) | HORIZON gate: no demand signal; excluded five boundaries running |
| `.planning/backlog/` directory cleanup | Reconciliation audit recorded closure evidence, but dir deletion stays deferred per the todo's own guard |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| REL-01 | Phase 187 | Complete (2026-09-07, verified 4/4 in 187-VERIFICATION.md) |
| SCORE-06 | Phase 188 | Complete (2026-09-08, 188-VERIFICATION 9/9 + operator UAT) |
| SCORE-07 | Phase 188 | Complete (2026-09-08, 188-VERIFICATION 9/9 + operator UAT) |
| TRIAGE-03 | Phase 189 | Pending |
| TRIAGE-04 | Phase 189 | Pending |
| TRIAGE-05 | Phase 189 | Pending |
| TRIAGE-06 | Phase 190 | Pending |
| TRIAGE-07 | Phase 190 | Pending |
| TRIAGE-08 | Phase 189 | Pending |
| TRIAGE-09 | Phase 189 | Pending |
