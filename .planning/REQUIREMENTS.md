# Requirements: QU.I.R.K. — Milestone v5.22 Release & Parity Tail

**Defined:** 2026-09-10
**Core Value:** Complete, defensible cryptographic inventory with CBOM deliverable and
quantum-readiness score — handed to a client in under two hours. This milestone ships the two
milestones of accumulated unreleased content as a real release, then finishes the dashboard
parity residue and drains the small standing items.

Sources: PM-approved scope from the 2026-09-10 boundary review (`PROJECT.md` §Current Milestone),
HORIZON.md Open-Item Ledger (999.104 tiers 2–3 residue per `194-PARITY-AUDIT.md`), pending todo
`backlog-reconciliation-and-derived-gate.md` (step 3), and the v5.21 audit's deferred items
(Phase-192 browser checks).

## v1 Requirements

### Release Integrity

- [ ] **REL-02**: Operator can `pip install quirk-scanner==5.21.0` — the `v5.21.0` tag is cut
      with every bump surface updated in the same change (pyproject bump + editable reinstall
      passing `tests/test_version.py`), and `release.yml` completes green across all three jobs
      (build, Windows package, PyPI publish) with Sigstore attestation verified against the
      published artifact. Gating — nothing else in this milestone ships ahead of the release it
      depends on for a clean version baseline (v5.18/v5.20 precedent).
- [ ] **REL-03**: CHANGELOG's `[Unreleased]` content moves under `5.21.0` documenting v5.20 +
      v5.21 user-visible changes (scoring v2, dashboard parity, Exposure Map), and README /
      `docs/getting-started.md` / UAT-1-02 version surfaces read 5.21.0 consistently.

### Connector Parity Tail (999.104 Tier 2 residue — 37 fields)

- [ ] **PARITY-05**: Operator can set per-connector target lists (jwt/container/source/identity
      connector families) from the dashboard scan form through the existing delta-overlay path
      (`build_job_config_dict` connectors overlay — never a `ScanJob` blob column).
- [ ] **PARITY-06**: Operator can set connector endpoint/identifier fields (cloud provider IDs,
      k8s config, `vault_addr`) from the dashboard through the same overlay path with 422
      validation at both submit and preview.
- [ ] **PARITY-07**: Remaining connector credential sub-fields ride the Phase-193 in-memory-only
      credential path — never in `ScanJob`, job `config.yaml`, or logs — with the no-leak
      sentinel guard extended to cover them.

### Scan-Behavior Parity Tail (999.104 Tier 3 residue — 23 fields)

- [ ] **PARITY-08**: Operator can set the 11 per-scanner timeout fields from the Advanced
      section, delta-only, composing with vertical presets under the single recorded precedence
      rule (`docs/configuration.md` §Dashboard form vs. presets precedence).
- [ ] **PARITY-09**: Operator can set the 4 concurrency knobs, retry backoff, and remaining
      misc scan-behavior fields from the Advanced section under the same delta-only/422 rules.

### Standing Drain

- [ ] **GATE-04**: The derived backlog-reconciliation gate (todo
      `backlog-reconciliation-and-derived-gate.md`, step 3) is enforced as a standing test — no
      BACK-*/999.* ID may be neither closed-with-evidence nor listed in HORIZON.md's Open-Item
      Ledger; keyed on **title+ID** (BACK-68 names two unrelated items) and counting
      requirement-section-heading citations as closure.
- [ ] **HOUSE-01**: Repo-root untracked clutter (`config-lab-*.yaml`, `output-*/` directories)
      is dispositioned — each file gitignored, relocated, or deleted with a recorded rationale.
- [ ] **HUAT-01**: Phase 192's two deferred browser checks (Scan Coverage chips render/colors;
      Effective-config Raw YAML tab redaction — security-relevant) are executed against the
      released build and dispositioned in `docs/UAT-SERIES.md`.

## Future Requirements (deferred, visible in HORIZON.md)

- **999.107** — Tier B Exposure Map (operator-declared reachability + crown jewels); build when a
  client engagement needs it.
- **999.106** — real `ports_ssh` backend capability (config field + scanner targeting).
- **PARITY-T4** — server-side `config.yaml` editing; needs its own threat model first.
- **999.105** — customizable reporting engine (three-tier shape in its IDEA.md).
- `docs/uat-coverage-gaps.md` worklist (P2 aggregate, milestone-sized test-writing effort).

## Out of Scope

| Item | Reason |
|------|--------|
| Tier 4 config-file editing | New security surface; explicitly out since v5.21, unchanged |
| P3 UX set (999.101/102, BACK-01/03/08, BACK-51) | Re-triage before building; not drain-first |
| Broker scanner-logic noise (999.103, BACK-68 ports, 999.97 coercion) | Scanner-internals cycle, not parity/release work |
| GSD toolchain todos (phase.complete semantic class etc.) | Upstream/toolchain work, not product scope |
| SaaS multi-tenancy | Still parked; no business-model signal |

## Traceability

(Filled by roadmap creation.)

| Requirement | Phase | Status |
|-------------|-------|--------|
