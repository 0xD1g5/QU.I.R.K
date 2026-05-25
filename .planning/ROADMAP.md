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

---

<details>
<summary>✅ v3.9–v5.3 (Phases 1–105) — SHIPPED</summary>

All completed milestone roadmaps are archived in `.planning/milestones/`. The next milestone continues from Phase 106.

**v5.3 Adoption & Integration Surface** (Phases 101–105) made QU.I.R.K. load-bearing in others' workflows: notification fan-out (Slack/email/webhook) + the shared integration-security foundation (101), dashboard token auth + login UX + score-tax fix (102), SIEM CEF export (103), Jira ticketing + the shared `TicketingChannel` abstraction (104), and ServiceNow ticketing as a zero-base-change second backend (105). Full details: `.planning/milestones/v5.3-ROADMAP.md`.

</details>

---

## v5.4 — Distributed On-Prem Scanner Architecture

**Started:** 2026-05-25
**Core constraint:** Single-tenant only; additive schema only (NULL sensor_id = implicit local); no new heavy infra; OS-agnostic wire contract; reuse v5.3 security primitives throughout.

### Phases

- [x] **Phase 106: Architecture Documentation** — No-code gating anchor; locks wire contract, data-model keying, PM decisions, and forbidden-additions list before any v5.4 code ships (completed 2026-05-25)
- [x] **Phase 107: Distributed Data Model** — Additive nullable columns + enrollment manifest + token + dedup tables; migration regression test; backward-compatible fixture (completed 2026-05-25)
- [x] **Phase 108: Sensor Push CLI + Windows CI** — `quirk sensor enroll/push/export-results`; POSIX-ism audit; `platformdirs`; `tenacity` retry; `_NoRedirectHandler` extraction; `windows-latest` hard-gate CI smoke job (completed 2026-05-25)
- [ ] **Phase 109: Console Ingestion API** — `POST /api/sensor/push` with `require_auth`, body-size limit, payload-ID dedup, clock-skew window, delivery audit, `safe_str` coverage
- [ ] **Phase 110: Cross-Sensor Merge & Scoring** — `quirk/sensor/merge.py`; Option A union scoring; `coverage_warning` for offline sensors; CBOM `sensor_id` component identity; `quirk sensor merge` CLI
- [ ] **Phase 111: Console Dashboard Awareness** — Sensor registry UI; per-segment filter on findings/CBOM/score APIs; per-segment score gauges; `coverage_warning` banner; `sensor_id`/`segment` Pydantic fields
- [ ] **Phase 112: Distributed Chaos-Lab + Stabilization** — Multi-segment Docker topology; overlapping RFC1918 lab validation; `lab.sh`/README/oracle updates; operators-guide; dep hygiene; UAT-SERIES.md close-out

---

## Phase Details

### Phase 106: Architecture Documentation

**Goal**: Every design decision that would be expensive to change mid-milestone is locked in a written document before any v5.4 code ships
**Depends on**: Nothing (first phase of v5.4)
**Requirements**: ARCH-01, ARCH-02, ARCH-03, ARCH-04
**Success Criteria** (what must be TRUE):

  1. A document exists at `docs/architecture-distributed.md` (or equivalent) that fully specifies the sensor→console wire payload schema including `payload_id`, `pushed_at`, `received_at`, `schema_version`, and `sensor_version` fields
  2. The document locks the additive data-model design: `sensor_id` and `segment` as nullable columns on `CryptoEndpoint`, and the `(sensor_id, host, port)` uniqueness key that distinguishes same RFC1918 IPs across segments
  3. The document records three committed PM decisions: Option A unified scoring (union of findings through existing engine), one-time-use enrollment tokens, and the Windows v5.4 scope (floor vs. ceiling determination)
  4. The document explicitly enumerates forbidden additions (Celery, Redis, MQTT/RabbitMQ, Postgres, JWT per-sensor tokens, mTLS/PKI infra, `tenant_id`) so downstream plans have a concrete violation reference

**Plans**: 2 plans

- [x] 106-01-PLAN.md — Author the 10-section distributed-scanner architecture doc (wire contract, data-model keying, PM decisions, forbidden additions, Windows scope) + 2 Mermaid diagrams
- [x] 106-02-PLAN.md — Verify seam citations against current code + ARCH-0N coverage; sync to Obsidian

### Phase 107: Distributed Data Model

**Goal**: The database has all tables and columns needed for sensor tracking before any ingestion or merge code is written
**Depends on**: Phase 106
**Requirements**: MODEL-01, MODEL-02, MODEL-03, MODEL-04
**Success Criteria** (what must be TRUE):

  1. `CryptoEndpoint` gains `sensor_id` (nullable String, indexed) and `segment` (nullable String) columns via the existing `_ensure_columns` / `_ADDITIVE_MIGRATIONS` pattern; `quirk scan` runs unchanged against an existing SQLite database
  2. A pre-v5.4 SQLite fixture (loaded with no sensor columns) passes all existing tests without any data loss or schema error
  3. A `sensors` enrollment manifest table exists (sensor UUID, segment label, optional engagement label, `last_push_at`, expected cadence)
  4. A `sensor_tokens` table exists storing SHA-256 hashes of per-sensor enrollment tokens (raw token never persisted)
  5. A `sensor_pushes` dedup table exists storing accepted `payload_id`s with `sensor_id` and `received_at`

**Plans**: 2 plans

- [x] 107-01-PLAN.md — ORM models (Sensor/SensorToken/SensorPush) + sensor_id/segment columns on CryptoEndpoint; _V54_SENSOR_COLUMNS in _ADDITIVE_MIGRATIONS + CREATE INDEX step in init_db
- [x] 107-02-PLAN.md — Backward-compat regression (pre-v5.4 DB migrates, no data loss, score-stable), CASCADE-delete proof, allowlist poison-tuple, smoke-test update

### Phase 108: Sensor Push CLI + Windows CI

**Goal**: A consultant can enroll a sensor and push results from any OS, with Windows correctness validated on a real Windows runner before merging
**Depends on**: Phase 107
**Requirements**: SENSOR-01, SENSOR-02, SENSOR-03, SENSOR-04, SENSOR-05, SENSOR-06, STAB-02
**Success Criteria** (what must be TRUE):

  1. `quirk sensor enroll <console-url> --segment <label>` writes a bound config (console URL, sensor UUID, segment label) and returns a one-time-use enrollment token
  2. `quirk sensor push` runs a local scan via `run_scan.py` and POSTs the result to the console over HTTPS with `tenacity` exponential-backoff retry; `verify=True` is enforced and a CI grep gate confirms it cannot be overridden
  3. When the console is unreachable, push payloads spool to a bounded file-per-payload directory and re-attempt on the next `quirk sensor push` invocation
  4. `quirk sensor export-results` produces a transferable file and `quirk console import-results` ingests it on an air-gapped console (sneakernet path)
  5. `_NoRedirectHandler` is extracted to `quirk/util/no_redirect.py` and the sensor push client imports from there (no duplication)
  6. The `windows-latest` CI smoke job passes without `continue-on-error: true`: payload serialization contains no backslash paths, and the sensor process shuts down cleanly on Windows

**Plans**: 4 plans

- [x] 108-01-PLAN.md — STAB-02 _NoRedirectHandler extraction + platformdirs/tenacity/zstandard deps + scheduler POSIX-ism fixes
- [x] 108-02-PLAN.md — quirk sensor enroll/push: bound sensor.yaml + one-time token, wire envelope + HMAC + tenacity HTTPS push, bounded store-and-forward spool
- [x] 108-03-PLAN.md — air-gap: quirk sensor export-results (byte-identical .qpush) + quirk console import-results ingest stub
- [x] 108-04-PLAN.md — windows-latest hard-gate CI smoke job + no-backslash/clean-shutdown tests + docs/UAT-SERIES.md update & Obsidian sync
**UI hint**: no

### Phase 109: Console Ingestion API

**Goal**: The console securely accepts pushed sensor payloads with no authentication bypass, no replay vulnerability, and a full audit trail
**Depends on**: Phase 107 (columns exist), Phase 108 (wire format defined and tested)
**Requirements**: CONSOLE-01, CONSOLE-02, CONSOLE-03, CONSOLE-04, CONSOLE-05
**Success Criteria** (what must be TRUE):

  1. `POST /api/sensor/push` exists on the running `quirk serve` FastAPI app and returns 200 for a valid authenticated push
  2. An unauthenticated request to `POST /api/sensor/push` returns 401 (gating test is part of the phase verification)
  3. A payload exceeding the body-size limit returns 413; a replayed `payload_id` returns 409; a push with a timestamp outside the ±15-minute clock-skew window returns 4xx with `console_utc` in the response for diagnosis
  4. Each push attempt — success or failure — writes an `IntegrationDelivery` audit row with all exception text passed through `safe_str()`; the extended AST gate covers the new module
  5. A sensor running a newer schema version than the console (or vice versa) gets a degraded-graceful response (not an unhandled 422/500) due to `extra='ignore'` and `schema_version` awareness

**Plans**: 3 plans

Plans:
- [x] 109-01-PLAN.md — `quirk console enroll` provisioning command (writes sensors + sensor_tokens, mints bearer token)
- [ ] 109-02-PLAN.md — POST /api/sensor/push route + PushEnvelope model + failure-mode ladder + audit-per-attempt + real _ingest_envelope
- [ ] 109-03-PLAN.md — ingestion + enroll tests, safe_str AST gate extension, docs/UAT-SERIES.md update & Obsidian sync

### Phase 110: Cross-Sensor Merge & Scoring

**Goal**: A consultant can trigger a merge across all sensor data and receive one canonical CBOM and one quantum-readiness score, with explicit warning when any enrolled sensor is missing
**Depends on**: Phase 109
**Requirements**: MERGE-01, MERGE-02, MERGE-03, MERGE-04, MERGE-05
**Success Criteria** (what must be TRUE):

  1. `quirk sensor merge` produces a new merged `scan_id` with a unified CBOM and score derived by running `build_evidence_summary()` → `compute_readiness_score()` → `build_cbom()` over the union of all pushed endpoints (the scoring/CBOM engines are not modified)
  2. The merged score is computed by Option A (union of findings through the existing engine), never by averaging pre-scored per-segment results
  3. A regression test proves that when two sensors report the same RFC1918 `host:port` in different segments, the merged CBOM contains two distinct components (one per `sensor_id`), not one collapsed entry
  4. When an enrolled sensor has not pushed within its expected cadence, the score JSON carries a non-null `coverage_warning` listing the missing sensor IDs; the merge does not silently proceed as if complete
  5. Sensor-local `scanned_at` timestamps are preserved in the merged result; the merge command does not rewrite them to its own execution time

**Plans**: TBD

### Phase 111: Console Dashboard Awareness

**Goal**: A consultant using the dashboard can see which sensors are active, filter findings by segment, and immediately notice when a merged score is based on incomplete sensor coverage
**Depends on**: Phase 110
**Requirements**: DASH-01, DASH-02, DASH-03
**Success Criteria** (what must be TRUE):

  1. The dashboard displays a sensor registry panel showing each sensor's ID, segment label, version, last-seen timestamp, and a status badge (green/stale/unknown)
  2. The findings table and CBOM view expose a `sensor_id`/`segment` dimension with a working per-segment filter on `/api/scan/latest`, `/api/findings`, and `/api/cbom`
  3. The dashboard displays per-segment score gauges alongside the org-wide score gauge; if a merge ran with sensors missing, a `coverage_warning` banner is visible on the dashboard

**Plans**: TBD
**UI hint**: yes

### Phase 112: Distributed Chaos-Lab + Stabilization

**Goal**: The distributed scanner is validated end-to-end in a real multi-segment topology, pre-existing housekeeping is resolved, and all v5.4 documentation and UAT coverage is complete
**Depends on**: Phase 110 (merge works), Phase 111 (dashboard works)
**Requirements**: LAB-01, LAB-02, LAB-03, STAB-01, STAB-03
**Success Criteria** (what must be TRUE):

  1. A multi-segment chaos-lab Docker Compose topology exists with at least two isolated Docker networks with overlapping RFC1918 address space, crypto targets per segment, one sensor container per segment, and one console container; running `enroll → scan-local → push → merge` end-to-end produces one CBOM and one score
  2. The same-IP-in-two-segments scenario is physically reproduced in that topology (a real two-network deployment, not only the unit regression test), confirming MERGE-03 holds under real Docker networking
  3. `quantum-chaos-enterprise-lab/lab.sh` `ALL_PROFILES`, the chaos-lab `README.md`, and the `expected_results_*.md` oracle are updated for the new distributed profile(s); no drift between script and compose profiles (per CLAUDE.md chaos-lab maintenance rule)
  4. `docs/operators-guide.md` covers the full distributed workflow (enroll → push → merge) including Windows sensor installation steps; the all-configurations/settings coverage gap noted in backlog 999.59 is closed
  5. `docs/UAT-SERIES.md` is updated to cover all v5.4 phases (106–112) and dep hygiene is resolved

**Plans**: TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 106. Architecture Documentation | 2/2 | Complete    | 2026-05-25 |
| 107. Distributed Data Model | 2/2 | Complete    | 2026-05-25 |
| 108. Sensor Push CLI + Windows CI | 4/4 | Complete   | 2026-05-25 |
| 109. Console Ingestion API | 1/3 | In Progress|  |
| 110. Cross-Sensor Merge & Scoring | 0/? | Not started | - |
| 111. Console Dashboard Awareness | 0/? | Not started | - |
| 112. Distributed Chaos-Lab + Stabilization | 0/? | Not started | - |
