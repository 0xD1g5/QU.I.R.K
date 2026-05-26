# Requirements: QU.I.R.K. v5.4 — Distributed On-Prem Scanner Architecture

**Defined:** 2026-05-25
**Core Value:** Produce a complete, defensible cryptographic inventory with a CBOM deliverable and quantum-readiness score that a consultant can hand to a client in under two hours — now **across every segment of a segmented enterprise network**, merged into one authoritative CBOM and one score.

**Milestone goal:** An agent/console split — lightweight sensors scan locally inside each network segment and push results *outbound* to a single-tenant console that merges them into one CBOM + one quantum-readiness score. No inbound access to any segment required.

**Locked constraints (apply to every requirement below):**

- **Single-tenant only.** No `tenant_id`, no per-tenant isolation. SaaS multi-tenancy is PARKED.
- **No new heavy infra.** No Celery, Redis, RabbitMQ, MQTT, Postgres. SQLite stays the store; FastAPI stays the server.
- **Additive schema only.** New columns/tables must be nullable/independent; existing single-host scans keep working unchanged (NULL `sensor_id` = implicit local sensor).
- **OS-agnostic sensor↔console contract.** The wire contract must not bake in POSIX assumptions; a Windows sensor must interoperate with a Linux console.
- **Reuse v5.3 primitives.** `require_auth`, the `IntegrationDelivery` delivery-audit table, `safe_str()` scrubbing, and the SSRF URL allowlist are reused, not reinvented.

---

## v1 Requirements (v5.4)

Requirements for this milestone. Each maps to exactly one roadmap phase.

### Architecture & Design (ARCH) — *no-code gating phase*

- [x] **ARCH-01**: A comprehensive architecture document exists describing the sensor/console split — service roles, the sensor→console wire payload schema (incl. `payload_id`, `pushed_at`, `received_at`, `schema_version`, `sensor_version`), the enrollment/auth model, and the merge pipeline — before any v5.4 code ships. (folds in backlog 999.58)
- [x] **ARCH-02**: The architecture document locks the additive data-model design: `sensor_id` and `segment` as nullable columns on `CryptoEndpoint` (NULL = implicit local sensor), and the `(sensor_id, host, port)` uniqueness key that distinguishes the same RFC1918 IP appearing in two segments.
- [x] **ARCH-03**: The architecture document records the resolved PM decisions: unified-score methodology (**Option A** — union of findings re-run through the existing scoring engine — as the committed start), enrollment-token expiry policy (**one-time-use** committed default), and the Windows scope decision for v5.4 (floor committed; ceiling — full PyInstaller/Scheduled-Task packaging — decided here as in-v5.4 or split to v5.5).
- [x] **ARCH-04**: The architecture document explicitly enumerates the forbidden additions (Celery, Redis, MQTT/RabbitMQ, Postgres, JWT per-sensor tokens, mTLS/PKI infra, `tenant_id`) so no downstream plan can introduce them without a documented violation.

### Distributed Data Model (MODEL)

- [x] **MODEL-01**: `CryptoEndpoint` gains nullable `sensor_id` and `segment` columns via the existing `_ensure_columns` / `_ADDITIVE_MIGRATIONS` pattern; a pre-v5.4 SQLite fixture loads and scores unchanged (backward-compatible).
- [x] **MODEL-02**: A `sensors` enrollment manifest table exists (sensor UUID, segment label, optional engagement label, `last_push_at`, expected cadence) so the console knows which sensors are expected.
- [x] **MODEL-03**: A `sensor_tokens` table stores SHA-256 hashes of per-sensor enrollment tokens (mirrors the existing `token_cmd.py` pattern; raw token never persisted).
- [x] **MODEL-04**: A `sensor_pushes` dedup table stores accepted `payload_id`s so replayed/duplicate pushes are rejected idempotently.

### Sensor Mode (SENSOR)

- [x] **SENSOR-01**: A consultant can enroll a sensor against a console via `quirk sensor enroll`, binding it to a console URL + segment label and receiving a one-time-use token + stable sensor UUID.
- [x] **SENSOR-02**: A sensor runs a local scan (reusing `run_scan.py` unchanged) and pushes the resulting endpoints to the console via `quirk sensor push` over authenticated HTTPS, with `tenacity` exponential-backoff retry and `verify=True` enforced.
- [x] **SENSOR-03**: A sensor in a degraded/offline segment spools pushes to a bounded file-per-payload directory and retries delivery when connectivity returns (store-and-forward).
- [x] **SENSOR-04**: A consultant can export a sensor's results to a transferable file (`quirk sensor export-results`) and import them on the console (`quirk console import-results`) for truly air-gapped segments (sneakernet).
- [x] **SENSOR-05**: The sensor runtime is OS-agnostic — a POSIX-ism audit removes/guards platform-specific code (at minimum `scheduler_cmd.py:136` relative path → `cfg.output_root`-anchored, and `:258-259` SIGTERM → `sys.platform != 'win32'`-guarded), and `platformdirs` resolves data/config directories on Windows and POSIX.
- [x] **SENSOR-06**: A `windows-latest` CI smoke job validates the sensor contract on real Windows (payload serialization has no backslash paths, clean shutdown), and is a hard gate (not `continue-on-error`). The Linux chaos lab does not satisfy this.

### Console Ingestion (CONSOLE)

- [x] **CONSOLE-01**: The console exposes `POST /api/sensor/push` on the existing `quirk serve` FastAPI app, accepting a pushed sensor scan payload.
- [x] **CONSOLE-02**: The ingestion endpoint requires authentication via router-level `Depends(require_auth)`; an unauthenticated request returns 401 (gating test).
- [x] **CONSOLE-03**: The ingestion endpoint enforces a body-size limit (413 on excess), rejects replayed `payload_id`s against `sensor_pushes` (409), and tolerates clock skew within a ±15-minute window (returning `console_utc` on rejection for diagnosis).
- [x] **CONSOLE-04**: Each push attempt writes an `IntegrationDelivery` audit row, with all exception text passed through `safe_str()` (extended AST gate covers the new module).
- [x] **CONSOLE-05**: The payload schema deserializes with `extra='ignore'` and honors `schema_version`, so a newer sensor pushing to an older console (or vice-versa) degrades gracefully rather than erroring.

### Cross-Sensor Merge & Scoring (MERGE)

- [x] **MERGE-01**: The console merges endpoints from N sensors into one CBOM by re-running the canonical `build_evidence_summary()` → `build_cbom()` pipeline over the union of pushed endpoints — the scoring/CBOM/evidence engines are not forked or modified.
- [x] **MERGE-02**: The merged quantum-readiness score is computed by re-running `compute_readiness_score()` over the union (Option A), never by averaging pre-scored per-segment results.
- [x] **MERGE-03**: The CBOM correctly emits two distinct components when two sensors report the same RFC1918 `host:port` in different segments (`sensor_id` included in the component identity), proven by a regression test.
- [x] **MERGE-04**: When an enrolled sensor is overdue/offline, the merged score JSON carries a non-null `coverage_warning` listing the missing sensor(s); partial data is never silently presented as complete.
- [x] **MERGE-05**: A consultant triggers a merge via `quirk sensor merge`, producing the unified CBOM + score as a normal scan result (new merged `scan_id`; sensor-local `scanned_at` not rewritten).

### Console Dashboard Awareness (DASH)

- [x] **DASH-01**: A consultant sees a sensor registry on the console dashboard — each sensor's ID, segment label, version, last-seen, and status badge (green/stale/unknown).
- [x] **DASH-02**: Findings and CBOM views expose the `sensor_id`/`segment` dimension (nullable, backward-compatible Pydantic fields) and offer a per-segment filter across `/api/scan/latest`, `/api/findings`, and `/api/cbom`.
- [x] **DASH-03**: The dashboard surfaces per-segment score gauges alongside the org-wide score, and a `coverage_warning` banner when a merge ran with sensors missing.

### Distributed Chaos-Lab Validation (LAB)

- [x] **LAB-01**: A multi-segment chaos-lab topology (≥2 isolated Docker networks with overlapping RFC1918 space, crypto targets per segment, one sensor per segment, one console) validates the end-to-end distributed flow on Linux: enroll → scan-local → push → merge → one CBOM + one score.
- [x] **LAB-02**: The same-IP-in-two-segments scenario is physically reproduced in the lab topology, proving MERGE-03 end-to-end (a real two-network deployment, not only the unit regression test).
- [x] **LAB-03**: `quantum-chaos-enterprise-lab/lab.sh` `ALL_PROFILES`, the chaos-lab `README.md`, and the `expected_results_*.md` oracle are updated for the new distributed profile(s), per the CLAUDE.md chaos-lab maintenance rule (no profile/script drift).

### Stabilization Tail (STAB)

- [x] **STAB-01**: `docs/operators-guide.md` covers the full distributed workflow (enroll → push → merge), including Windows sensor install, and the operators-guide all-configurations/settings coverage gap is closed. (folds in backlog 999.59)
- [x] **STAB-02**: The duplicated `_NoRedirectHandler` is extracted to `quirk/util/no_redirect.py` and reused by the sensor push client (ship no later than the sensor phase — treat as a sensor-phase prerequisite if it slips).
- [x] **STAB-03**: Residual dependency hygiene is resolved and `docs/UAT-SERIES.md` is updated to cover all v5.4 phases.

---

## Future Requirements (deferred — likely v5.5)

Tracked, not in this milestone's roadmap.

### Windows Packaging (WINPKG)

- **WINPKG-01**: Full PyInstaller frozen `.exe` packaging for Python-less locked-down Windows boxes *(pulled into v5.4 only if the Phase 1 arch-doc decides the ceiling is in scope; otherwise committed v5.5 fast-follow)*.
- **WINPKG-02**: Windows Scheduled Task host wrapper for the sensor scan cadence (no admin elevation).
- **WINPKG-03**: Windows Service via `pywin32` (the PyInstaller + pywin32 service combo is poorly maintained — deferred).
- **WINPKG-04**: MSI/MSIX installer (needs an explicit enterprise demand signal).
- **WINPKG-05**: Windows Event Log integration.
- **WINPKG-06**: Authenticode signing of the Windows EXE (AV false-positive mitigation; pairs with the existing Sigstore pipeline).

### Distributed Depth (DIST)

- **DIST-01**: Weighted-by-host-count unified score (Option B) — validate Option A with real consultants first.
- **DIST-02**: Automatic console-side merge trigger when all expected sensors have checked in (v5.4 ships manual `quirk sensor merge`).
- **DIST-03**: Time-windowed enrollment tokens (v5.4 ships one-time-use).
- **DIST-04**: mTLS / PKI sensor authentication (httpx supports it later without interface change).

---

## Out of Scope

Explicitly excluded for v5.4. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| SaaS multi-tenancy / per-tenant isolation / `tenant_id` | Different problem, bigger lift — gated on a business-model signal that does not yet exist. Distributed on-prem is a topology necessity, not a SaaS bet. |
| Celery / Redis / RabbitMQ / MQTT / Postgres | Violates the no-new-heavy-infra + single-tenant constraint; SQLite + FastAPI + file-spool cover the v5.4 use case. |
| Pull-based scanning (console reaches into segments) | Architecturally impossible given the "no inbound access to segments" premise; outbound push + sneakernet only. |
| Inter-sensor / sensor-to-sensor communication | Sensors only talk to the console; a mesh adds attack surface and infra for no v5.4 value. |
| Real-time streaming of findings | Batch push per scan session is sufficient; streaming implies infra (queues) that's out of scope. |
| Validating Windows sensor correctness via the chaos lab | The Linux-container chaos lab cannot run a Windows sensor; Windows correctness is validated by the `windows-latest` CI smoke job instead. |

## Traceability

Which phases cover which requirements.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ARCH-01 | Phase 106 | Complete |
| ARCH-02 | Phase 106 | Complete |
| ARCH-03 | Phase 106 | Complete |
| ARCH-04 | Phase 106 | Complete |
| MODEL-01 | Phase 107 | Complete |
| MODEL-02 | Phase 107 | Complete |
| MODEL-03 | Phase 107 | Complete |
| MODEL-04 | Phase 107 | Complete |
| SENSOR-01 | Phase 108 | Complete |
| SENSOR-02 | Phase 108 | Complete |
| SENSOR-03 | Phase 108 | Complete |
| SENSOR-04 | Phase 108 | Complete |
| SENSOR-05 | Phase 108 | Complete |
| SENSOR-06 | Phase 108 | Complete |
| STAB-02 | Phase 108 | Complete |
| CONSOLE-01 | Phase 109 | Complete |
| CONSOLE-02 | Phase 109 | Complete |
| CONSOLE-03 | Phase 109 | Complete |
| CONSOLE-04 | Phase 109 | Complete |
| CONSOLE-05 | Phase 109 | Complete |
| MERGE-01 | Phase 110 | Complete |
| MERGE-02 | Phase 110 | Complete |
| MERGE-03 | Phase 110 | Complete |
| MERGE-04 | Phase 110 | Complete |
| MERGE-05 | Phase 110 | Complete |
| DASH-01 | Phase 111 | Complete |
| DASH-02 | Phase 111 | Complete |
| DASH-03 | Phase 111 | Complete |
| LAB-01 | Phase 112 Plan 01 | In Progress (topology built; live run is human-UAT) |
| LAB-02 | Phase 112 Plan 01 | In Progress (alias mechanism + linchpin confirmed; live run is human-UAT) |
| LAB-03 | Phase 112 Plan 02 | Pending (lab.sh arm done; README + oracle in Plan 02) |
| STAB-01 | Phase 112 | Complete |
| STAB-03 | Phase 112 | Pending |

**Coverage:**

- v1 (v5.4) requirements: 33 total (ARCH 4, MODEL 4, SENSOR 6, CONSOLE 5, MERGE 5, LAB 3, DASH 3, STAB 3)
- Mapped to phases: 33 ✓
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-25*
*Last updated: 2026-05-25 — v5.4 roadmap complete; all 33 requirements mapped to Phases 106–112*
