# Requirements: QU.I.R.K. v5.15 — Lifecycle Tail Drain

**Defined:** 2026-08-19
**Core Value:** Produce a complete, defensible cryptographic inventory with a CBOM deliverable and
quantum-readiness score that a consultant can hand to a client in under two hours.

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases. All four items are drain-before-net-new
carry-forwards from the v5.10–v5.14 hardware-lifecycle arc and the v5.11 discovery-at-scale work —
no net-new capability territory.

### Hardware Lifecycle Notifications

- [x] **HWLC-14**: Consultant can opt in to email/webhook notification when a monitored device
  crosses a CNSA 2.0 tier boundary or an EOL/EOS date, reusing the existing Phase 101 notification
  fan-out layer (SIEM CEF / Jira / ServiceNow / email/webhook) rather than a new delivery path.

### Vendor PQC Trend Surfacing

- [x] **HWLC-19**: Consultant can view catalog-level vendor PQC-status trend data
  (`GET /api/hardware/vendor-trends`, shipped in v5.14 Phase 160 with zero consumers) in the
  dashboard and/or exported reports, so the existing backend has a first user-facing home.

### Check-in Scan Scheduling

- [ ] **HWLC-20**: Consultant can schedule HWLC-13's on-demand `--check-in` re-probe mode on a
  recurring cadence via the existing `quirk schedule` CRUD/dispatcher (Phase 63), instead of only
  triggering it manually.

### Discovery Checkpoint Granularity

- [ ] **DISC-08**: A discovery scan interrupted mid-batch resumes from the last completed sub-batch
  boundary rather than re-running the entire in-flight batch, tightening the granularity of the
  existing per-batch checkpoint/resume system (v5.11 Phase 144).

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Hardware Lifecycle

- **HWLC-99**: Statistically-modeled EOL prediction beyond vendor-published catalog dates —
  explicitly rejected as an anti-feature (v5.14 rationale, still holds).

- **HWLC-98**: Cross-tenant/cross-client PQC trend aggregation — blocked on the still-parked SaaS
  multi-tenant architecture.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Statistically-modeled EOL prediction | Rejected as an anti-feature at v5.14; vendor-published dates only |
| Cross-tenant/cross-client PQC trend aggregation | Blocked on parked SaaS multi-tenant architecture |
| Phase 158 human-UAT (2 deferred visual scenarios) | Code-level criteria independently satisfied; opportunistic follow-up only, not scoped into v5.15 |
| SaaS multi-tenancy | Still parked, no business-model signal |
| New scanner surfaces / detection capability | This milestone is a backlog drain, not a capability expansion |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| HWLC-14 | Phase 161 | Complete |
| HWLC-19 | Phase 161 | Complete |
| HWLC-20 | Phase 162 | Pending |
| DISC-08 | Phase 163 | Pending |
