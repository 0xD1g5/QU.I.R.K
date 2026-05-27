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
- 🚧 **v5.5 Distributed Hardening + Stabilization** — Phases 113–116 (in progress)

---

<details>
<summary>✅ v3.9–v5.4 (Phases 1–112) — SHIPPED</summary>

All completed milestone roadmaps are archived in `.planning/milestones/`. The next milestone continues from Phase 113.

**v5.4 Distributed On-Prem Scanner Architecture** (Phases 106–112) split QU.I.R.K. into a sensor/console
model so a segmented enterprise network is scanned segment-by-segment and merged into one authoritative
CBOM + one quantum-readiness score, with no inbound access to any segment required. It locked the wire
contract and forbidden-additions in an architecture doc (106), landed the additive sensor data model
(107), shipped the OS-agnostic `quirk sensor enroll/push/export-results` CLI with a hard-gated
`windows-latest` smoke job (108), the authenticated `POST /api/sensor/push` ingestion endpoint with
dedup/replay/audit (109), Option-A cross-sensor merge with `coverage_warning` and `sensor_id`-keyed CBOM
components (110), console dashboard awareness — sensor registry, per-segment filter, per-segment gauges,
coverage banner (111), and a multi-segment chaos-lab + operators-guide + stabilization close-out (112).
Full details: `.planning/milestones/v5.4-ROADMAP.md`.

</details>

---

## 🚧 v5.5 Distributed Hardening + Stabilization (Phases 113–116)

**Milestone Goal:** Harden the v5.4 distributed scanner into production shape — per-sensor authentication, automatic merge, and a clean re-runnable lab — while sweeping the defects the live distributed E2E surfaced. Honors the 2:1 stabilization breather deliberately deferred from v5.4.

**Locked constraints:** Single-tenant only; additive schema only; no new heavy infra (Celery/Redis/RabbitMQ/MQTT/Postgres); reuse v5.3/v5.4 primitives (`require_auth`, `sensor_tokens`, `IntegrationDelivery`, `safe_str()`, SSRF allowlist); OS-agnostic sensor↔console contract unchanged; public-repo cutover and full Windows binary build are OUT of scope.

### Phases

- [ ] **Phase 113: Per-Sensor Authentication** - Replace the v5.4 shared-token model with per-sensor opaque tokens, full revocation, and documented migration
- [ ] **Phase 114: Automatic Merge Trigger** - Console auto-merges once all enrolled sensors have checked in, with configurable trigger and no regression to manual merge
- [ ] **Phase 115: Live-UAT Stabilization + Lab Testability** - Sweep the four E2E-surfaced defects and add a weak-crypto distributed lab target so the Phase 111 segment filter is exercisable end-to-end
- [ ] **Phase 116: Windows Packaging Spike** - Produce a written feasibility and sizing assessment for PyInstaller frozen EXE + Windows Scheduled Task; go/no-go recommendation for v5.6

### Phase Details

### Phase 113: Per-Sensor Authentication
**Goal**: Operators can issue, manage, and revoke individual sensor tokens so each sensor is independently authenticated at ingestion and a compromised sensor can be cut off without affecting others
**Depends on**: Phase 112 (v5.4 complete)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04
**Success Criteria** (what must be TRUE):
  1. `quirk console enroll-sensor` issues a per-sensor opaque token bound to the sensor UUID; the raw token is shown once and never stored (SHA-256 hash only in `sensor_tokens` table)
  2. `quirk console revoke-sensor <sensor-id>` succeeds and immediately causes that sensor's next `POST /api/sensor/push` to return 401, while other enrolled sensors continue to push without interruption
  3. `POST /api/sensor/push` with an unknown or revoked token returns 401 and logs the rejection; a valid per-sensor token is accepted and the push is attributed to the correct sensor UUID
  4. Operators running the v5.4 shared-token model can migrate to per-sensor tokens following the updated operators guide without re-enrolling from scratch
**Plans**: 3 plans
- [ ] 113-01-PLAN.md — Add nullable revoked_at column + AUTH-01..04 gating test scaffold (Wave 0)
- [ ] 113-02-PLAN.md — require_sensor_auth dependency + push-route split + token-authoritative identity + revoke-sensor CLI (cutover)
- [ ] 113-03-PLAN.md — Update existing push tests + enroll printout/sensor semantics + operators-guide migration + lab oracle + Obsidian/UAT sync

### Phase 114: Automatic Merge Trigger
**Goal**: The console automatically merges all pushed sensor results once every enrolled sensor has checked in, eliminating the mandatory manual `quirk sensor merge` step for the common deployment case
**Depends on**: Phase 113
**Requirements**: AUTOMERGE-01, AUTOMERGE-02, AUTOMERGE-03
**Success Criteria** (what must be TRUE):
  1. After all enrolled sensors push results, the console triggers a merge automatically and the merged CBOM + quantum-readiness score are available in the dashboard without a manual command
  2. Auto-merge can be disabled in config so operators who prefer explicit control keep the manual-only workflow; toggling does not affect in-flight pushes
  3. A merge failure (e.g. bad payload from one sensor) is logged and surfaced to the operator but does not block or roll back other sensors' successful pushes
  4. `quirk sensor merge` still executes correctly and produces the same Option-A union CBOM + `coverage_warning` + sensor-local `scanned_at` output as in v5.4, with no regression
**Plans**: TBD

### Phase 115: Live-UAT Stabilization + Lab Testability
**Goal**: The four defects surfaced by the distributed E2E are root-caused and eliminated so the lab is re-runnable without teardown, and the Phase 111 per-segment filter is exercisable end-to-end against a real weak-crypto target in the distributed lab
**Depends on**: Phase 112 (v5.4 base); can execute in parallel with Phase 113 / 114 if needed
**Requirements**: STAB-01, STAB-02, STAB-03, STAB-04, LAB-01
**Success Criteria** (what must be TRUE):
  1. `lab.sh distributed e2e` completes successfully on a second consecutive run without `docker compose down -v`; `quirk console enroll` and `quirk sensor enroll` are idempotent for already-provisioned entities
  2. `quirk sensor merge` on an installed (non-source-tree) package produces no "CMVP cache unavailable" warning; `cmvp_cache.json` is declared as package data and ships in the wheel
  3. `quirk scheduler` runs to completion with exit code 0; it passes no unsupported `--output` / `--target` arguments to `run_scan`, and a regression test locks this invariant alongside the existing sensor fix
  4. Merged console output contains no phantom `email_scanner` / `broker_scanner` rows with `scanned_at=None` or port 0; the root cause is identified and eliminated at the source
  5. The distributed chaos lab includes a weak-crypto target reachable from at least one non-default segment; `lab.sh distributed`, the `expected_results_*.md` oracle, and the chaos-lab README are all updated in the same change per the CLAUDE.md no-drift rule
**Plans**: TBD

### Phase 116: Windows Packaging Spike
**Goal**: Produce a written, evidence-backed feasibility and sizing assessment for packaging the QUIRK sensor as a PyInstaller frozen EXE hosted as a Windows Scheduled Task (or Service), ending in an explicit go/no-go recommendation and effort estimate for v5.6
**Depends on**: Phase 113 (per-sensor auth final; spike validates wire contract compatibility)
**Requirements**: WINPKG-01
**Success Criteria** (what must be TRUE):
  1. A written assessment document (`docs/windows-packaging-spike.md`) exists covering: PyInstaller spec viability, hidden-import surface, Scheduled Task vs Windows Service trade-offs, CI validation results on `windows-latest`, and estimated effort for the full v5.6 build
  2. The `windows-latest` CI job executes the spike validation (e.g. a dry-run `pyinstaller --collect-all quirk`) and the result (pass or documented failure with root cause) is captured in the assessment document
  3. The assessment ends with an unambiguous go/no-go recommendation: "go" if the spike finds a clean PyInstaller path with bounded effort, "no-go" or "defer" if blockers are found, with rationale
  4. No production packaging artifact (frozen EXE, installer, NSIS script) is committed or published; the phase deliverable is the assessment only
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 113. Per-Sensor Authentication | v5.5 | 0/TBD | Not started | - |
| 114. Automatic Merge Trigger | v5.5 | 0/TBD | Not started | - |
| 115. Live-UAT Stabilization + Lab Testability | v5.5 | 0/TBD | Not started | - |
| 116. Windows Packaging Spike | v5.5 | 0/TBD | Not started | - |
