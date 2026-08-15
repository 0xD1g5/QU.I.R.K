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
- ✅ **v5.12 Release & Verification Integrity** — Phases 148–153, 36 plans (shipped 2026-08-14) → `.planning/milestones/v5.12-ROADMAP.md`
- 🚧 **v5.13 Continuous Hardware Lifecycle Monitoring** — Phases 154–156 (in progress)

---

## v5.13 Continuous Hardware Lifecycle Monitoring

**Goal:** Extend v5.10's hardware-fingerprinting foundation (`HardwareDevice` table, `hw_cve.py`,
CNSA 2.0 tier assignment) from a point-in-time scan into ongoing lifecycle tracking — detecting
drift in firmware/EOL/vendor-PQC-status over time and alerting when a device crosses a CNSA 2.0
tier boundary. Research (4 parallel passes, unanimous) confirmed this is a scheduling/diffing/
reporting layer over data QU.I.R.K. already collects, not a new scanner surface — no new
dependencies, no new database, no new background worker.

### Phases

- [ ] **Phase 154: Identity & Data-Model Foundation** — Stable device re-identification across
      scans (secondary match key + low-confidence flagging), failed-probe-safe writes, and a
      bounded retention policy — the blocking dependency every later phase's diff logic sits on

- [ ] **Phase 155: Drift Detection + EOL Tracking** — Two-scan reconciliation across CNSA 2.0
      tier, vendor PQC status, EOL/EOS proximity, and CVE set; named tier-crossing events;
      N-of-M confirmation gating; curated EOL/EOS catalog populating `HardwareDevice.eol_date`

- [ ] **Phase 156: Reporting & OT/ICS Safety** — "What changed since last scan" hardware
      surfacing in dashboard/reports as visually distinct advisory-only content, plus an explicit
      opt-in + cadence floor for recurring OT/ICS (Modbus/BACnet) re-probing (`/gsd-secure-phase`
      required)

### Phase Details

#### Phase 154: Identity & Data-Model Foundation

**Goal**: A device is reliably recognized as "the same device" across repeated scans even when its
IP changes, and the underlying scan-history data model is safe against partial failures and
unbounded growth — the foundation every drift/alert feature in this milestone is built on top of.
**Depends on**: Nothing (first phase, blocking dependency for Phases 155–156)
**Requirements**: HWLC-01, HWLC-02, HWLC-03
**Success Criteria** (what must be TRUE):

  1. A device re-scanned after a DHCP/re-IP change is still recognized as the same device via a
     stable secondary match key, not just `host:port`.

  2. A match made on `host:port` alone (no secondary signal available) is explicitly flagged
     low-confidence in the stored data, not treated as equal-confidence to a stronger match.

  3. A failed or partial hardware re-probe never overwrites or discards the device's last-known-good
     state — the most recent *successful* observation remains the current projected state.

  4. Hardware scan history per device is bounded by a configurable retention policy, so repeated
     engagements don't grow storage unboundedly.
**Plans**: 5 plans

- [x] 154-01-PLAN.md — Schema: 3 nullable HardwareDevice columns + additive migration + ScanCfg.hardware_history_retention_days [HWLC-01/02/03]
- [x] 154-02-PLAN.md — Write path: SSH host-key fingerprint extraction, match_confidence, probe_status [HWLC-01/02]
- [x] 154-03-PLAN.md — Read path: per-device latest-successful-row projection at all 4 sites (D-13/D-14) [HWLC-02]
- [x] 154-04-PLAN.md — Retention: guarded opportunistic per-scan purge helper + wiring [HWLC-03]
- [x] 154-05-PLAN.md — Docs (configuration/operators-guide/report-interpretation/UAT-SERIES) + Obsidian sync [HWLC-01/02/03]

#### Phase 155: Drift Detection + EOL Tracking

**Goal**: QU.I.R.K. computes and surfaces real lifecycle change for a device across scans — tier
crossings, PQC-status shifts, EOL/EOS proximity, and new CVEs — while filtering out probe
flakiness, and an EOL/EOS catalog finally populates the dormant `eol_date` column.
**Depends on**: Phase 154 (stable device identity required for any cross-scan diff)
**Requirements**: HWLC-04, HWLC-05, HWLC-06, HWLC-07, HWLC-08, HWLC-09
**Success Criteria** (what must be TRUE):

  1. Reconciling the two most recent scans for the same device surfaces changes in CNSA 2.0 tier,
     vendor PQC-readiness status, EOL/EOS proximity, and the device's CVE set.

  2. A tier-boundary crossing (e.g. Tier 2 → Tier 1) or a change in `upstream_mitigated` status is
     reported as a distinct, named event, not buried in a generic diff.

  3. The number of new CVEs affecting a device since its last scan is computed as an explicit delta,
     reusing the existing `hw_cve.py` correlation.

  4. A single anomalous probe result (dropped packet, transient network issue) is not reported as a
     lifecycle event — only a change confirmed across an N-of-M observation window is surfaced.

  5. `HardwareDevice.eol_date` is populated on scan from a new curated, staleness-gated EOL/EOS
     catalog (mirroring `hw_cve.py`/`model_meta.py`), and devices approaching or past their EOL/EOS
     date are surfaced with an explicit "approaching"/"passed" state.
**Plans**: 6 plans

Plans:
**Wave 1**

- [x] 155-01-PLAN.md — Curated EOL/EOS catalog module + 365-day staleness gate + CI/CLAUDE.md wiring [HWLC-08/09]
- [x] 155-02-PLAN.md — hardware_drift_events table + N-of-M window query helper + shared TIER_ORDER [HWLC-04/05/07]

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 155-03-PLAN.md — Pure drift computation: N-of-M gate, tier/bridge/EOL state, CVE delta [HWLC-05/06/07/09]

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 155-04-PLAN.md — reconcile_device_history() with dedup-on-write + advisory-firewall guard test [HWLC-04/05/07]

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 155-05-PLAN.md — Pipeline wiring: eol_date population + reconciliation at both hw commit sites [HWLC-04/09]

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 155-06-PLAN.md — Docs (operators-guide, UAT-SERIES) + Obsidian sync + REQUIREMENTS flips [HWLC-04..09]

#### Phase 156: Reporting & OT/ICS Safety

**Goal**: Lifecycle changes are visible to the consultant wherever they already look (dashboard,
reports) as unmistakably advisory content, and recurring probing of fragile OT/ICS devices is
opt-in and rate-floored rather than inheriting the default hardware re-scan cadence.
**Depends on**: Phase 155 (drift events must exist before they can be surfaced or scheduled)
**Requirements**: HWLC-10, HWLC-11, HWLC-12
**Success Criteria** (what must be TRUE):

  1. A "what changed since last scan" hardware section appears on the dashboard (extending the
     existing `/compare` and `/hardware` surfaces) and in generated reports, distinct from the
     current-state hardware view.

  2. Hardware lifecycle findings (drift, tier crossings, EOL proximity) are visually and
     structurally distinct from scored findings — no reuse of scored-finding UI components
     (e.g. `RegressionAlertChip`), and a grep confirms zero new `SCORE_WEIGHTS` references.

  3. Recurring re-scans of OT/ICS devices (Modbus/BACnet) require an explicit, separate opt-in
     from the default hardware re-scan cadence.

  4. Scheduled OT/ICS re-probing is bounded by a minimum cadence floor materially longer than the
     default hardware/TLS/SSH re-scan cadence, and cannot be configured below it.

  5. This phase has passed a dedicated `/gsd-secure-phase` review before shipping, given the
     new recurring-probe risk surface against fragile production control systems.
**Plans**: 6 plans

Plans:
**Wave 1**

- [x] 156-01-PLAN.md — OT/ICS cadence-floor module (OTICS_MIN_INTERVAL_HOURS, cron min-gap derivation) + ConnectorsCfg opt-in [HWLC-12]
- [x] 156-03-PLAN.md — Drift read API: Pydantic models, GET /api/hardware/drift, CompareResponse block [HWLC-10/11]

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 156-02-PLAN.md — Enforcement: dispatch-time strip-and-warn + two write-time advisories + write-path inventory guard [HWLC-12]
- [ ] 156-04-PLAN.md — Report parity: ExecContent field, HTML/DOCX drift section, unconditional advisory caption, score-guard extension [HWLC-10/11]
- [ ] 156-05-PLAN.md — Dashboard: LifecycleEventList/Row, /hardware + /compare wiring, frontend advisory guard, visual checkpoint [HWLC-10/11]

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 156-06-PLAN.md — Docs + Obsidian sync + UAT Series 156 + REQUIREMENTS flips + terminal /gsd-secure-phase 156 gate [HWLC-10/11/12]
**UI hint**: yes

### Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 154. Identity & Data-Model Foundation | 5/5 | Complete    | 2026-08-14 |
| 155. Drift Detection + EOL Tracking | 6/6 | Complete    | 2026-08-14 |
| 156. Reporting & OT/ICS Safety | 2/6 | In Progress|  |

---

<details>
<summary>✅ v5.12 Release & Verification Integrity (Phases 148–153) — SHIPPED 2026-08-14</summary>

See `.planning/milestones/v5.12-ROADMAP.md` for full phase details, `.planning/milestones/v5.12-REQUIREMENTS.md`
for requirements, and `.planning/milestones/v5.12-MILESTONE-AUDIT.md` for the closing audit.

6 phases (148-153), 36 plans, 14/14 requirements complete. Shipped the real `v5.12.0` release tag
(PyPI + Windows operator zip + GitHub Release), a green CI-held test-suite baseline, the
phase-completion artifact gate (`scripts/verify_phase_gates.py` + `.githooks/pre-commit`, now
installed and live), and empirically closed the Phase 144 nmap timing artifact (does not reproduce).

</details>

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

- Continuous hardware lifecycle monitoring — promoted into v5.13 (see above).

- SaaS multi-tenancy — still parked, no business-model signal.

### Hardware Compatibility & Lifecycle Remediation (v5.13+)

Promoted into v5.13 (see above) — kept here for backlog-history continuity:

- **Continuous hardware lifecycle monitoring** — HWLC-01..12, Phases 154–156.

~~OT/ICS resume-checkpoint gap~~ and ~~CVE table BACnet key coverage~~ — both closed by v5.11
Phase 147 as DRAIN-01/DRAIN-02; struck from this list 2026-08-11.

### v1.x / v2+ (deferred from v5.13, see REQUIREMENTS.md Future Requirements)

- HWLC-13 — lightweight "check-in" scan mode (narrow re-probe of known devices only)
- HWLC-14 — optional email/webhook notification on tier-crossing/EOL events (reuses Phase 101
  fan-out)

- Vendor PQC-status trend tracking (catalog-level, not per-device)
- Consultant-facing "lifecycle risk forecast" narrative (12-month EOL/tier projections)
- Fleet-wide sensor coverage — `PushEnvelope`/ingest route gains a `hardware_devices` field so
  sensor-scanned segments reach the console's drift history (v5.13 covers console-direct scans
  only; real gap found during v5.13 research, `sensor_cmd.py::_build_envelope()`)

### SaaS Platform (Future Milestone)

- [ ] Multi-tenant architecture design
- [ ] Scan job queue (Celery + Redis or similar)
- [ ] User auth and org management
- [ ] Cloud deployment (Docker Compose → Kubernetes)
- [ ] Hosted reporting and CBOM storage
