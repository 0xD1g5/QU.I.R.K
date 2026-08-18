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
- ✅ **v5.13 Continuous Hardware Lifecycle Monitoring** — Phases 154–156, 17 plans (shipped 2026-08-15) → `.planning/milestones/v5.13-ROADMAP.md`
- 🚧 **v5.14 Hardware Lifecycle Tail — Fleet Coverage & Forecasting** — Phases 157–160 (in progress)

---

## Current Milestone: v5.14 Hardware Lifecycle Tail — Fleet Coverage & Forecasting

**Goal:** Close the sensor-fleet drift gap left open by v5.13 and round out lifecycle monitoring
with a low-cost check-in scan mode and catalog-level PQC trend forecasting.

**Phase Numbering:** Continues from v5.13's last phase (156). Integer phases only for this
milestone — no urgent insertions anticipated.

### Phases

- [x] **Phase 157: Drift-Event Retention + Forecast Narrative Foundation** - Bound `hardware_drift_events` growth via a calendar-cutoff sweep and add a hedged, catalog-cited 12-month EOL/tier forecast narrative to every report format, structurally isolated from scoring.
- [ ] **Phase 158: Sensor Fleet Drift Coverage** - Sensor-scanned segments reach the console's drift history exactly like console-direct scans, via a `hardware_devices` field on `PushEnvelope` and a shared `persist_and_reconcile()` helper.
- [ ] **Phase 159: Check-in Scan Mode** - Consultants can re-probe only already-known devices via a distinct opt-in mode (never a 4th `--profile` value), excluded from scored comparisons and always visually flagged as partial.
- [ ] **Phase 160: Catalog-Level PQC Vendor Trend Tracking** - Vendor-level PQC support status changes in the curated hardware catalog are recorded over time as discrete, structured, cross-device/cross-vendor events.

## Phase Details

### Phase 157: Drift-Event Retention + Forecast Narrative Foundation

**Goal**: `hardware_drift_events` growth is bounded on long-running deployments, and consultants
get a forward-looking, catalog-grounded EOL/tier forecast in every report format — without either
capability becoming score-visible.
**Depends on**: Nothing (first phase of milestone; extends Phase 154/155/156 patterns)
**Requirements**: HWLC-16, HWLC-18
**Success Criteria** (what must be TRUE):

  1. `hardware_drift_events` rows older than a configurable retention window are purged via a
     calendar-cutoff sweep over the whole table — structurally distinct from the scan-scoped
     `HardwareDevice` purge pattern (Phase 154), so idle-device drift history is neither purged
     prematurely nor retained forever.

  2. HTML, DOCX, and CLI reports each include a 12-month EOL/tier forecast narrative for the
     scanned fleet, derived at render time from existing `HardwareDevice.eol_date` and tier data.

  3. The forecast narrative cites the underlying catalog's `last_verified` date and uses hedged,
     non-absolute language — never an unqualified "will".

  4. `tests/test_cve_score_guard.py` is extended by name (in this same phase, not deferred) to
     assert the forecast module never references `SCORE_WEIGHTS` or feeds `compute_readiness_score`.

  5. The drift-event retention window and the forecast's advertised look-back window are explicitly
     reconciled — the forecast never implies visibility into a period the retention sweep has
     already purged.
**Plans**: 5 plans

Plans:
**Wave 1**

- [x] 157-01-PLAN.md — Drift-event calendar-cutoff retention sweep + `hardware_drift_event_retention_days` config (HWLC-16)
- [x] 157-02-PLAN.md — `hardware_forecast.py` bucketing/hedged-narrative engine + score-guard extension (HWLC-18)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 157-03-PLAN.md — `ExecContent.eol_forecast` field, writer population, HTML forecast subsection (HWLC-18)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 157-04-PLAN.md — DOCX forecast subsection + net-new CLI/markdown forecast subsection (HWLC-18)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 157-05-PLAN.md — Config/report docs, UAT Series 157, Obsidian vault sync + phase note (HWLC-16, HWLC-18)

### Phase 158: Sensor Fleet Drift Coverage

**Goal**: Hardware devices discovered by a sensor's local scan reach the console's
`hardware_drift_events` history the same way console-direct scans do, closing the real gap found
during v5.13 research.
**Depends on**: Nothing new (extends Phase 107/109/154 sensor-console plumbing); independent of
Phase 157
**Requirements**: HWLC-15
**Success Criteria** (what must be TRUE):

  1. A sensor push envelope carrying `hardware_devices` results in those devices' changes appearing
     on `/hardware`, `/compare`, and in reports — identical treatment to a console-direct scan of
     the same segment.

  2. An old, un-upgraded sensor binary that omits `hardware_devices` entirely produces zero drift
     events — field-absent ("no observation") is never misread as field-present-empty ("confirmed
     zero devices").

  3. `PushEnvelope`, `sensor_cmd.py::_build_envelope()`, and `console_cmd.py::_ingest_envelope()`
     changes ship together in the same commit, proven by a round-trip envelope schema test (sender
     and receiver never drift apart silently under `extra="ignore"`).

  4. A shared `persist_and_reconcile()` helper is extracted and used by both the console-direct and
     sensor-ingest persistence paths — no duplicated purge/commit/reconcile logic remains.
**Plans**: 3 plans

Plans:
**Wave 1**

- [x] 158-01-PLAN.md — Shared `persist_and_reconcile()` helper + both `run_scan.py` persist sites refactored onto it (HWLC-15)
- [x] 158-02-PLAN.md — `hardware_devices` field on `PushEnvelope` + sensor-side serialization/read + round-trip schema test (HWLC-15)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 158-03-PLAN.md — Console `_ingest_envelope()` hardware persist/reconcile wiring + None-vs-empty ingest tests + UAT/Obsidian sync (HWLC-15)

### Phase 159: Check-in Scan Mode

**Goal**: Consultants can run a lightweight check-in scan that cheaply re-probes only already-known
devices, without repeating a full network discovery or non-hardware scanner phases.
**Depends on**: Phase 158 (check-in's drift-writing path reuses the shared `persist_and_reconcile()`
helper; console-direct target resolution itself has no sensor dependency)
**Requirements**: HWLC-13
**Success Criteria** (what must be TRUE):

  1. A check-in run is invoked via a distinct opt-in flag/subcommand — never a 4th `--profile`
     value — and re-probes only devices already present in `HardwareDevice`, skipping full network
     discovery and non-hardware scanner phases.

  2. Check-in runs carry a `scan_type`/`is_partial_scan` marker and are excluded from `/trends` and
     `/compare` like-for-like score comparisons.

  3. Every rendered report format (HTML, DOCX, CLI) shows an always-visible "partial re-probe"
     banner whenever a check-in result is displayed.

  4. A check-in run persists `HardwareDevice`/`hardware_drift_events` rows only — it does not go
     through `compute_readiness_score` and does not write a scored scan session.
**Plans**: 5 plans

Plans:
- [x] 159-01-PLAN.md — `HardwareDevice.is_partial_scan` marker column + `check_in_fingerprint_devices()` re-probe dispatch (wave 1)
- [x] 159-02-PLAN.md — `--check-in` CLI flag, `run_check_in()` short-circuit, CLI summary (wave 2)
- [x] 159-03-PLAN.md — API badge on drift events + `/trends`//`/compare` immunity regression tests (wave 2)
- [ ] 159-04-PLAN.md — Partial re-probe banner in HTML/DOCX/CLI report renderers (wave 2)
- [ ] 159-05-PLAN.md — Docs, UAT Series 159, Obsidian vault sync (wave 3)

### Phase 160: Catalog-Level PQC Vendor Trend Tracking

**Goal**: The system tracks vendor-level PQC support status changes in the curated hardware catalog
over time as discrete, structured events — a genuinely novel cross-device/cross-vendor aggregate
view with no direct precedent elsewhere in QUIRK.
**Depends on**: Phase 158 (reuses the `persist_and_reconcile()` call site as the natural chokepoint
for the new vendor-diff check, and needs the complete sensor+console fleet population to avoid
under-representing sensor-scanned segments)
**Requirements**: HWLC-17
**Success Criteria** (what must be TRUE):

  1. A confirmed change in `HARDWARE_MATRIX`'s PQC support status for a vendor is recorded as a
     discrete event in a new event-sourced table — never as a free-text or numeric risk-score field.

  2. The trend-event writer is wired into the shared `persist_and_reconcile()` call site established
     in Phase 158, not a bespoke new call site.

  3. Vendor PQC trend events are queryable at the catalog level (cross-device, cross-vendor), not
     only per individual device.

  4. The new trend-event table's schema mirrors the scalar/enum-only `old_value`/`new_value`
     contract already established for `hardware_drift_events`.
**Plans**: TBD

**Note (research flag for this phase's own planning):** Phase 160 is the least-precedented item in
this milestone — no existing QUIRK subsystem does cross-device/cross-vendor aggregation, only
per-device drift. Display/statistics design (how to bucket/summarize "vendor X's fleet-wide PQC
posture trend") needs a `--research-phase` pass or an explicit CONTEXT.md decision during
`/gsd:discuss-phase 160`, not a locked answer here.

**Note (research flag, Phase 159):** Whether a check-in run writes a full scan session / goes
through `compute_readiness_score` at all is architecturally recommended as "no" (rows only) but is
a decision for `/gsd:discuss-phase 159`'s CONTEXT.md, not locked by this roadmap.

### Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 157. Drift-Event Retention + Forecast Narrative Foundation | 5/5 | Complete    | 2026-08-16 |
| 158. Sensor Fleet Drift Coverage | 3/3 | Complete    | 2026-08-17 |
| 159. Check-in Scan Mode | 3/5 | In Progress|  |
| 160. Catalog-Level PQC Vendor Trend Tracking | 0/TBD | Not started | - |

---

<details>
<summary>✅ v5.13 Continuous Hardware Lifecycle Monitoring (Phases 154–156) — SHIPPED 2026-08-15</summary>

See `.planning/milestones/v5.13-ROADMAP.md` for full phase details, `.planning/milestones/v5.13-REQUIREMENTS.md`
for requirements, and `.planning/milestones/v5.13-MILESTONE-AUDIT.md` for the closing audit.

3 phases (154-156), 17 plans, 12/12 requirements complete. Extended v5.10's point-in-time hardware
fingerprinting into ongoing lifecycle tracking: a stable SSH host-key-fingerprint secondary match
key survives DHCP/re-IP, failed re-probes never erase last-known-good device state, and a two-scan
drift-reconciliation engine surfaces CNSA 2.0 tier crossings, PQC/bridge-mitigation shifts,
EOL/EOS proximity, and CVE deltas as four distinct, N-of-M-confirmed event types — visible on the
dashboard (`/hardware`, `/compare`) and in HTML/DOCX reports as structurally separate advisory
content. Recurring OT/ICS (Modbus/BACnet) re-probing now requires explicit opt-in plus a hardcoded
168-hour cadence floor, closed by an independent `/gsd-secure-phase` review (19/19 threats, 0
high-severity findings).

</details>

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

### Hardware Lifecycle Tail (v5.14)

Promoted into v5.14 (see Current Milestone section above) — kept here for backlog-history
continuity:

- HWLC-13 — lightweight "check-in" scan mode (narrow re-probe of known devices only) → Phase 159
- HWLC-15 — fleet-wide sensor coverage for `hardware_devices` (deferred from v5.13) → Phase 158
- HWLC-16 — `hardware_drift_events` retention policy → Phase 157
- HWLC-17 — vendor PQC-status trend tracking (catalog-level, not per-device) → Phase 160
- HWLC-18 — consultant-facing "lifecycle risk forecast" narrative (12-month EOL/tier projections)
  → Phase 157

**Deferred out of v5.14 (see REQUIREMENTS.md Future Requirements):**

- HWLC-14 — optional email/webhook notification on tier-crossing/EOL events (reuses Phase 101
  fan-out); deferred pending validation of the core diff mechanism on real engagement data.

- Sub-batch check-in scheduling / recurring cadence — worth building only once HWLC-13's on-demand
  form is proven useful.

- Statistically-modeled EOL prediction beyond vendor-published catalog dates — explicitly rejected
  as an anti-feature.

- Cross-tenant/cross-client PQC trend aggregation — blocked on the still-parked SaaS multi-tenant
  architecture.

### v1.x / v2+ (deferred, see REQUIREMENTS.md Future Requirements)

- DISC-08 sub-batch (mid-discovery) checkpoint/resume granularity — deferred as an accepted
  boundary since v5.11; revisit only if batch cost grows.

### SaaS Platform (Future Milestone)

- [ ] Multi-tenant architecture design
- [ ] Scan job queue (Celery + Redis or similar)
- [ ] User auth and org management
- [ ] Cloud deployment (Docker Compose → Kubernetes)
- [ ] Hosted reporting and CBOM storage

</content>
