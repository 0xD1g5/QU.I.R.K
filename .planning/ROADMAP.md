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

- **v5.11 Discovery at Scale + Backlog Drain** — Phases 144–147 (in progress, opened 2026-08-03)

---

## Current Milestone: v5.11 Discovery at Scale + Backlog Drain

**Goal:** Close backlog 999.90 — make chunked, partial-result-tolerant nmap discovery reachable
end-to-end from the dashboard's job-creation endpoint for large (>1024-host) IP ranges — while
draining the small debt tail accumulated since v5.8/v5.10 (OT/ICS resume-checkpoint gap, BACnet
CVE coverage decision, 2026-05-27 audit ledger reconciliation, deferred human-UAT re-triage).

### Phases

- [ ] **Phase 144: Chunked Discovery Core** — Batch-split large host ranges on a deduplicated host
      list, tolerate a single bad batch without failing the whole job, and relax both existing
      hard-reject gates (`target_expander.py::_MAX_HOSTS_PER_CIDR`, `jobs.py`'s 422 stopgap) in the
      same phase so chunking is actually reachable end-to-end

- [ ] **Phase 145: Liveness Pre-Pass** — TCP-SYN/ACK liveness check ahead of the full port sweep per
      batch, with explicit privilege-fallback (SYN→connect) detection instead of silent degradation

- [ ] **Phase 146: Progress, Scaling & Disclosure** — Per-batch progress visible on the dashboard,
      timeout/parallelism derived from batch size, one shared CLI/dashboard chunking implementation,
      and undetermined-host counts disclosed in the report

- [ ] **Phase 147: Backlog Drain — Lifecycle & Ledger Tail** — OT/ICS resume-checkpoint fix, BACnet
      CVE coverage decision, 2026-05-27 audit ledger reconciliation, deferred human-UAT re-triage

### Phase Details

#### Phase 144: Chunked Discovery Core

**Goal**: Operators can submit a large (>1024-host) IP range scan via the dashboard and have
discovery actually complete — one slow/unresponsive batch no longer fails the entire job, and the
range is no longer rejected outright by either existing hard-reject gate
**Depends on**: Nothing (first phase, anchor capability)
**Requirements**: DISC-01, DISC-02
**Success Criteria** (what must be TRUE):

  1. An operator submits a >1024-host CIDR through the actual job-creation API endpoint and the job
     completes instead of being rejected with a 422 or timing out at the old fixed 300s ceiling

  2. A single unresponsive batch within a large range does not abort the whole discovery job — hosts
     in other batches are still fully scanned and reported

  3. Batches are derived from a deduplicated host list, not `(host, port)` tuples — a multi-port
     host straddling a batch boundary never has its ports split across two batches

  4. Both `target_expander.py::_MAX_HOSTS_PER_CIDR` and `jobs.py`'s 422 stopgap are relaxed in this
     same phase (not deferred), verified by a live end-to-end submission of a real >1024-host range
     through the job-creation endpoint — not just unit tests on the chunking function in isolation

**Plans**: 3 plans

Plans:
**Wave 1**

- [x] 144-01-PLAN.md — Relax both host-count reject gates (D-02/D-05) + add lazy host-expansion & chunking helpers (DISC-01)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 144-02-PLAN.md — Sequential per-batch nmap loop with failure isolation + discovery ScanCheckpoint (DISC-02)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 144-03-PLAN.md — Live end-to-end >1024-host submission checkpoint (DISC-01, DISC-02)

#### Phase 145: Liveness Pre-Pass

**Goal**: Discovery skips the expensive full port sweep on non-responsive hosts using a cheap
TCP-based liveness check, preserving reliability in segmented/firewalled networks where ICMP is
unreliable
**Depends on**: Phase 144 (batches must exist before a pre-pass can slot into the batch loop)
**Requirements**: DISC-03
**Success Criteria** (what must be TRUE):

  1. Each batch runs a TCP-SYN/ACK liveness check (`-sn -PS<port-list>`) ahead of its full port sweep
  2. Hosts found non-responsive by the pre-pass are skipped from the expensive sweep but still
     counted (not silently dropped from host/undetermined accounting)

  3. A privilege fallback from SYN scan to full TCP connect scan is explicitly detected and logged
     rather than silently degrading the intended optimization

  4. The pre-pass and its fallback-detection behavior are verified against a real non-root run, not
     just a unit test — per the documented nmap SYN→connect silent-fallback risk

**Plans**: 3 plans

Plans:
- [x] 145-01-PLAN.md — Host-status XML parser + `-sn -PS` liveness probe primitives
- [x] 145-02-PLAN.md — Batch-loop pre-pass wiring, privilege detection + fallback/skip disclosure
- [x] 145-03-PLAN.md — Docs, Obsidian sync, UAT Series 145 + D-06 non-root human verification

#### Phase 146: Progress, Scaling & Disclosure

**Goal**: Operators watching a large-range scan see real incremental progress instead of silence
until pass/fail, per-batch timeout and parallelism scale to what the batch actually needs, the CLI
gets the identical chunking fix the dashboard got, and reports tell the operator how many hosts
could not be determined
**Depends on**: Phase 144 (progress/scaling/CLI-parity are additive on top of the chunking core;
independent of Phase 145's liveness pre-pass)
**Requirements**: DISC-04, DISC-05, DISC-06, DISC-07
**Success Criteria** (what must be TRUE):

  1. An operator watching a large-range scan on the dashboard sees incremental discovery progress
     (batch N of M / hosts checked so far) via the existing job-status poll loop, instead of silence
     until the job finishes or fails

  2. Per-batch timeout and parallelism are derived from that batch's size, replacing the single
     hardcoded `timeout_seconds=300` constant used regardless of range size

  3. The CLI's `--discovery nmap` path calls the same shared chunked-discovery function the
     dashboard path calls — verified by a test asserting both entry points share one call site

  4. The scan report/summary discloses a count of undetermined (unreachable/filtered) hosts
     alongside successfully scanned hosts, for both CLI and dashboard-triggered scans

**Plans**: TBD
**UI hint**: yes

#### Phase 147: Backlog Drain — Lifecycle & Ledger Tail

**Goal**: The small debt items accumulated since v5.8/v5.10 are resolved so they stop aging across
milestones — independent of the discovery-at-scale work, safe to sequence in parallel or after
**Depends on**: Nothing (independent of Phases 144–146's discovery code paths)
**Requirements**: DRAIN-01, DRAIN-02, DRAIN-03, DRAIN-04
**Success Criteria** (what must be TRUE):

  1. A `--resume-scan-id` continuation correctly scans OT-only hosts even when the SSH stage was
     already checkpointed complete — the outer-gate skip bug tracked since v5.10 is fixed

  2. The hardware CVE table has an explicit, documented decision on BACnet key coverage: either a
     real vendor CVE entry is added, or the gap is formally marked lab-only/out of scope with
     written rationale

  3. The 2026-05-27 audit ledger has zero rows with an undecided or stale disposition — already-fixed
     rows are flipped to `[x] closed` with commit citations, and WR-02/CD-03 each get a final
     fix-or-accept-risk call

  4. The deferred human-UAT ledger in STATE.md is re-triaged — every actionable item (e.g. the
     Windows Authenticode production cert) is either resolved or explicitly re-confirmed as still
     blocked, with a reason

**Plans**: TBD

### Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 144. Chunked Discovery Core | 3/3 | Complete   | 2026-08-10 |
| 145. Liveness Pre-Pass | 3/3 | Complete   | 2026-08-10 |
| 146. Progress, Scaling & Disclosure | 0/TBD | Not started | - |
| 147. Backlog Drain — Lifecycle & Ledger Tail | 0/TBD | Not started | - |

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

### Hardware Compatibility & Lifecycle Remediation (v5.11+)

- **Continuous hardware lifecycle monitoring** — least-scoped backlog item; needs its own research pass; explicitly deferred past v5.10
- **OT/ICS resume-checkpoint gap** — Phase 141's outer-gate fix (`_run_ot_supplemental_phase()`) only runs in `run_scan.py`'s non-resume code path; a `--resume-scan-id` continuation from a checkpoint where the SSH stage was already marked complete could still skip OT-only hosts. Narrow edge case, tracked in v5.10-MILESTONE-AUDIT.md.
- **CVE table BACnet key coverage** — `hw_cve.py`'s CVE_TABLE has no entry keyed on the chaos-lab's synthetic BACnet fixture model string ("FX16"); consider whether real-world Johnson Controls FX-series devices need their own table entry beyond the "Facility Explorer" one, or whether this stays a lab-only cosmetic gap.

### Discovery & Scanning UX

- **Flip interactive setup's nmap-discovery-first default from N to Y** — `quirk/interactive.py:176-179`
  (`_prompt_bool("Run nmap port discovery first? (recommended for >10 hosts)", default=False)`)
  defaults to no, so users hitting enter/default silently skip the nmap batch-discovery path (and
  the Phase 145 liveness pre-pass) entirely. Discovered during Phase 145 D-06 human-UAT: two
  consecutive interactive-setup scans both took the default and never touched nmap discovery,
  wasting two verification attempts. Flip `default=True` so interactive setup opts users into the
  recommended path by default; users who want a bare fingerprint-only scan can still say `n`.

### SaaS Platform (Future Milestone)

- [ ] Multi-tenant architecture design
- [ ] Scan job queue (Celery + Redis or similar)
- [ ] User auth and org management
- [ ] Cloud deployment (Docker Compose → Kubernetes)
- [ ] Hosted reporting and CBOM storage
