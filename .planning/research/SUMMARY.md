# Project Research Summary

**Project:** QU.I.R.K. v5.4 — Distributed On-Prem Scanner Architecture
**Domain:** Agent/console split for segmented-network cryptographic inventory scanning
**Researched:** 2026-05-25
**Confidence:** HIGH

---

## Executive Summary

v5.4 extends QUIRK from a single-host scanner into a distributed sensor-and-console system where lightweight sensors run in isolated network segments (DMZ, PCI zones, OT/ICS VLANs, air-gapped enclaves), push results outbound over HTTPS to a central console, and the console merges all sensor findings through the existing canonical scoring and CBOM engines to produce one authoritative quantum-readiness score and one aggregate CBOM. All four research streams converged on a single design principle: this is an additive, single-tenant, no-new-infra extension of what already exists. The sensor is a thin wrapper around `run_scan.py`; the console is the existing FastAPI dashboard with one new ingestion route; the data model gains exactly two nullable columns; and the scoring/CBOM/evidence engines are called unchanged over the union of pushed endpoints.

The single highest-risk item — identified independently by every researcher — is the `(sensor_id, host, port)` uniqueness problem. The existing `CryptoEndpoint` fingerprint formula treats `(host, port)` as globally unique, which is correct for a single-node scanner but catastrophically wrong in a distributed deployment where two sensors in different segments can scan different machines at the same RFC1918 address. This data-model migration must be fully designed and locked in the architecture-doc phase before a single line of ingestion code is written; every other v5.4 feature is downstream of it. The architecture doc is therefore not optional groundwork — it is the gating deliverable for the entire milestone.

Three open questions require PM confirmation before the requirements doc is finalized: (1) which scoring methodology to use when merging findings from multiple sensors — Option A (union of findings through the existing engine, recommended to start) vs. Option B (weighted average of per-segment scores by host count, more complex, deferred) vs. Option C (weakest-link, not recommended); (2) whether full Windows sensor packaging (PyInstaller frozen EXE + Windows Scheduled Task) lands in v5.4 or the v5.5 fast-follow, with v5.4's non-negotiable floor being an OS-agnostic sensor/console contract that works on Python 3.11+ on Windows without POSIX dependencies; and (3) the enrollment token expiry policy — one-time-use (recommended for a consulting tool) vs. time-windowed (e.g., 60-minute window as Rapid7 uses). These are not implementation details; getting them wrong late in the milestone is expensive.

---

## Key Findings

### Recommended Stack

The stack addition for v5.4 is deliberately minimal: exactly two new runtime pip dependencies (`platformdirs>=4.3.7` for OS-appropriate data directory resolution; `tenacity>=9.1.4` for sensor push retry with exponential backoff) plus one build-time tool (`PyInstaller>=6.20.0` for the Windows frozen EXE, if the arch-doc phase decides full Windows packaging lands in v5.4). Everything else — httpx, zstandard, cyclonedx-python-lib, FastAPI, SQLite/SQLAlchemy, `secrets`/`hmac`/`hashlib` — is already present in the codebase and is directly reused. The explicit prohibitions (Celery, Redis, RabbitMQ, MQTT, PostgreSQL, JWT per-sensor tokens, mTLS/PKI infrastructure, sbommerge, `tenant_id`) are as important as the additions; they enforce the single-tenant, no-new-infra constraint that all researchers agreed was the central design invariant.

**Core new technologies:**
- `platformdirs>=4.3.7` — OS-appropriate data/config directories (`user_data_dir`) — replaces the implicit `./quirk.db` assumption that breaks on Windows; zero transitive deps; add to core `dependencies`
- `tenacity>=9.1.4` — exponential-backoff retry decorator for sensor->console HTTPS push — composable, async-compatible, no transitive deps; add to `[sensor]` extras group
- `PyInstaller>=6.20.0` — frozen EXE for locked-down Windows sensor deployment — build-time only (not in `pyproject.toml` dependencies), runs on `windows-latest` GitHub Actions runner
- `pywin32>=311` — Windows Service Control Manager integration — Windows-only optional, explicitly a **v5.5 candidate**; do NOT add in v5.4

**Wire transport:** httpx (already in core) + zstandard level-3 compression (already in codebase) + `X-Sensor-Signature: hmac-sha256=<hex>` header for application-layer integrity. Single POST per scan session; file-per-payload spool directory (not SQLite) for store-and-forward.

**Sensor enrollment:** stdlib `secrets.token_urlsafe(32)` + SHA-256 hash stored in `sensor_tokens` table — exact mirror of `token_cmd.py` pattern. Per-sensor tokens, not a shared bearer token. No JWT (clock-sync hostile to air-gapped sensors). No mTLS for v5.4.

### Expected Features

All four research streams independently flagged `(sensor_id, host, port)` data-model keying as a blocking prerequisite for every other v5.4 feature. Nothing downstream can be built until the data model is locked.

**Must ship (table stakes, blocking):**
- `(sensor_id, host, port)` data model — blocks all downstream v5.4 work; arch-doc phase locks the design
- Sensor enrollment: one-time token + stable UUID assigned at enrollment (mirrors Rapid7/Qualys/Wazuh pattern)
- Outbound-push results endpoint (`POST /api/sensor/push`) with idempotent re-push by `(sensor_id, scan_job_id)`
- Per-sensor CBOM stored per push; unified org-wide CBOM merged via canonical `build_cbom()` engine
- Unified org-wide quantum-readiness score via Option A (union of findings through existing `compute_readiness_score()` — needs PM confirmation)
- Heartbeat last-seen tracking + sensor status/registry page on console
- De-registration (explicit sensor removal from console)
- Segment filter on all existing dashboard views
- Manual export/import for air-gapped sneakernet (`quirk sensor export-results` + `quirk console import-results`)
- Windows sensor: POSIX-ism audit (at minimum `scheduler_cmd.py:136` relative path + `:258-259` SIGTERM) + Windows CI `windows-latest` smoke job
- Store-and-forward spool (file-per-payload spool directory, bounded depth)
- Version skew warning on heartbeat (non-blocking)

**Should add once merge semantics confirmed:**
- Per-segment score gauges in dashboard alongside org-wide score
- Cross-segment algorithm frequency map ("algorithm X appears in 4 of 5 segments")
- Offline sensor alert (configurable last-seen threshold)
- Scan result staleness flag (default 30-day window)
- Segment coverage table in PDF report
- Engagement-label field on sensor enrollment

**Defer to v5.5:**
- MSI/MSIX installer — needs explicit enterprise demand signal
- Weighted scoring by host count (Option B) — validate Option A with real consultants first
- Windows Service via pywin32 — Scheduled Task covers v5.4 use case without admin elevation
- Windows Event Log integration
- Full PyInstaller frozen EXE packaging (if the arch-doc phase decides to defer it)

### Architecture Approach

The architecture follows a "same package, new mode flags" pattern: `quirk sensor` and `quirk console` are two new subcommand intercepts in `run_scan.py` using the identical dispatch pattern already used for `serve`, `schedule`, `token`, `export`, `ticket`, and all other subcommands. No package split. The sensor is a thin wrapper that invokes `run_scan.py` locally (exactly as the scheduler does via `sys.executable -m run_scan`), reads the resulting `CryptoEndpoint` rows, serializes them, and POSTs to the console. Scoring, CBOM building, and evidence collection never run on the sensor; they run only on the console after the merge step re-feeds the union of pushed endpoints through the unchanged canonical engines.

**Major components:**

1. **`quirk/cli/sensor_cmd.py`** (net-new) — sensor subcommand: `enroll`, `push`, `merge`, `export-results`, `check-clock`; OS-agnostic throughout; `pathlib.Path` everywhere
2. **`quirk/dashboard/api/routes/sensor.py`** (net-new) — `POST /api/sensor/push` ingestion endpoint; `Depends(require_auth)` applied at router level; idempotent upsert on `(host, port, sensor_id, scan_id)`; writes `IntegrationDelivery` audit row via `safe_str()` pattern
3. **`quirk/sensor/merge.py`** (net-new) — console merge pipeline: gathers `CryptoEndpoint` rows by `sensor_id` + time window, feeds `build_evidence_summary()` -> `compute_readiness_score()` -> `build_cbom()` unchanged; checks enrollment manifest for partial-result warning; triggers existing notification/SIEM hooks
4. **`quirk/models.py`** (modified, additive) — two new nullable columns: `sensor_id = Column(String(128), nullable=True, index=True)` and `segment = Column(String(255), nullable=True)`; NULL = implicit local sensor; backward-compatible
5. **`quirk/db.py`** (modified, additive) — one new entry in `_ADDITIVE_MIGRATIONS` using the Phase 77 `_ensure_columns` helper; no Alembic needed
6. **Windows CI smoke job** (net-new, `.github/workflows/`) — `windows-latest` runner; distinct from and not replaceable by the Linux chaos lab

**Key canonical engine invariant:** The merge pipeline re-runs `build_evidence_summary()` + `compute_readiness_score()` + `build_cbom()` over the full union of sensor endpoints. It never merges pre-scored sub-results. Averaging sensor scores is mathematically wrong because the six subscores use ratio-based penalties over the full endpoint population as denominator; a partial-population score is not comparable to a full-population score.

**Untouched by v5.4:** `scoring.py`, `evidence.py`, `cbom/builder.py`, `cbom/writer.py`, `middleware/auth.py`, `models.py:IntegrationDelivery`, `util/safe_exc.py`, `util/url_allowlist.py`, `scheduler_cmd.py`, `notify/dispatcher.py`.

### Critical Pitfalls

1. **(Segment, host) collision — same RFC1918 IP in two segments** — The single highest data-model risk. `CryptoEndpoint` currently keys on `(host, port)`; two sensors scanning different machines at `10.0.0.5:443` collide and corrupt the merged CBOM. Prevention: add `sensor_id` (nullable, indexed) and `segment` (nullable) columns before any ingestion code; change all dedup/merge queries to include `sensor_id` in the uniqueness key; update CBOM builder Pass 1 component identity hash to include `sensor_id`; write regression test (two sensors, same RFC1918 host/port, different `sensor_id` -> two distinct CBOM components). Must be locked in architecture-doc phase.

2. **Ingest endpoint bypasses `require_auth` + `safe_str`** — A new route file in a separate module can fail to inherit the existing `require_auth` dependency, opening unauthenticated result injection. Prevention: apply `Depends(require_auth)` at the `APIRouter(dependencies=[...])` level; write a gating test that calls the ingest endpoint without credentials and asserts 401; extend the `safe_str()` AST gate to the new module paths.

3. **Merge scores partial sensor data without warning** — When one enrolled sensor is offline, the console silently merges two-of-three sensors and presents the result as the org-wide score. Prevention: maintain a `sensors` enrollment manifest with `last_push_at` and expected cadence; emit a `coverage_warning` field in score JSON listing overdue sensor IDs; do NOT score partial data as if complete.

4. **Windows POSIX-isms break the sensor service** — `scheduler_cmd.py:258-259` registers `signal.SIGTERM` (not meaningful for arbitrary Windows processes); `:136` uses a relative path `output/scheduled` (wrong CWD when running as a Windows service); `os.kill(pid, SIGTERM)` in `jobs.py:204` does not work as expected on Windows. Prevention: POSIX-ism audit as an explicit phase task; wrap SIGTERM with `sys.platform != 'win32'`; replace relative path with `cfg.output_root / "scheduled"`.

5. **Replay and oversized-payload attacks on the ingest surface** — FastAPI has no default body-size limit; a sensor (or impersonator) can DoS the console or replay stale results to re-roll a remediated score. Prevention: enforce 10 MB body limit (413 on excess); add `payload_id` UUID field in sensor push schema; persist accepted IDs in a `sensor_pushes` dedup table (409 on replay); include `pushed_at` + `received_at`; ±15-minute replay window for clock-skew tolerance.

6. **Backward compatibility break for single-node local scans** — If `sensor_id` is added as `NOT NULL`, all existing rows in SQLite fail the constraint. Prevention: `sensor_id` must be `nullable=True`; `compute_readiness_score()` signature must not change; write migration regression test with pre-v5.4 SQLite fixture.

7. **Over-engineering toward SaaS/multi-tenant patterns** — Distributed-system tutorials lead to Celery + Redis; `tenant_id` feels forward-compatible. Prevention: arch-doc phase explicitly enumerates forbidden additions; every subsequent phase plan reviewed against it.

---

## Implications for Roadmap

All four researchers independently converged on the same phase ordering: architecture doc first (no exceptions), then additive data model, then sensor push and console ingestion, then merge pipeline, then dashboard exposure, with Windows CI validation threaded through the sensor phase and a stabilization tail for pre-existing housekeeping. The rationale is dependency-driven: every downstream deliverable is blocked by the data-model keying decision, and the data-model keying decision cannot be safely made without the architecture doc locking the wire contract.

### Phase 1: Architecture Documentation (arch-doc anchor, no code)

**Rationale:** Every researcher and the existing HORIZON.md entry (`999.58`) agree this comes first. The data-model keying decision, the wire contract shape, the enrollment token design, the Windows floor/ceiling decision, and the scoring methodology choice are all interconnected. Making any one of them in a coding phase without the others locked creates rework debt.

**Delivers:** Locked decisions on (a) `sensor_id`/`segment` nullable column names and types, (b) the sensor->console wire payload schema including `payload_id`, `pushed_at`, `schema_version`, and `sensor_version` fields, (c) Windows scope floor vs. ceiling, (d) scoring methodology (Option A/B confirmation from PM), (e) enrollment token expiry policy, (f) enrollment manifest and partial-result `coverage_warning` contract, (g) explicit enumeration of forbidden infra additions. No code ships.

**Avoids:** Premature code that must be refactored when keying or wire contract changes; SaaS over-engineering (Pitfall 8); scope creep (Pitfall 14).

**Research flag:** This phase IS the research materialization — no further research needed; execute directly.

---

### Phase 2: Data Model Migration

**Rationale:** Purely additive; zero risk to existing functionality; blocks all ingestion and merge code. Ships immediately after the arch doc locks the column names and types.

**Delivers:** `sensor_id` and `segment` nullable columns on `crypto_endpoints`; one new `_ADDITIVE_MIGRATIONS` entry using `_ensure_columns` helper; `sensors` enrollment manifest table; `sensor_tokens` table; `sensor_pushes` dedup table; migration regression test with pre-v5.4 SQLite fixture.

**Uses:** Existing `_ensure_columns` / `_ADDITIVE_MIGRATIONS` pattern (Phase 77 helper); `SQLite ALTER TABLE ADD COLUMN` — no Alembic.

**Avoids:** Pitfall 4 (segment/host collision — keying established before ingestion writes rows), Pitfall 5 (backward compat — nullable columns, existing rows unaffected).

**Research flag:** Well-documented pattern in this codebase; skip research phase.

---

### Phase 3: Sensor Push CLI + Windows CI Smoke Test

**Rationale:** The sensor is the value-delivery unit; the Windows CI smoke test belongs in the same phase because it validates the POSIX-ism audit on a real Windows runner, and deferring it guarantees regression.

**Delivers:** `quirk/cli/sensor_cmd.py` with `enroll`, `push`, `export-results`, and `check-clock` subcommands; subcommand dispatch intercept in `run_scan.py`; `platformdirs` integration; `tenacity` retry in push client; POSIX-ism fixes (`scheduler_cmd.py:136` relative path -> `cfg.output_root / "scheduled"`; `:258-259` SIGTERM -> platform-conditional); `verify=True` enforced with CI grep gate; `windows-latest` CI smoke job (not `continue-on-error: true`) validating payload serialization (no backslash paths) and clean shutdown.

**Uses:** `platformdirs>=4.3.7` (new, core dep); `tenacity>=9.1.4` (new, `[sensor]` extras); httpx + zstandard (existing); `validate_external_url()` (existing SSRF guard); `safe_str()` (existing).

**Avoids:** Pitfall 11 (SIGTERM on Windows), Pitfall 12 (relative paths), Pitfall 13 (chaos lab cannot validate Windows — this phase creates the real Windows validation path), Pitfall 3 (console impersonation — `verify=True` and CI grep gate).

**Research flag:** POSIX-ism audit scope is well-understood from research; Windows CI job is straightforward. Skip research phase.

---

### Phase 4: Console Ingestion API

**Rationale:** Depends on Phase 2 (columns exist) and Phase 3 (wire format is defined and tested).

**Delivers:** `quirk/dashboard/api/routes/sensor.py` with `POST /api/sensor/push`; `Depends(require_auth)` applied at `APIRouter` level; 10 MB body size limit (413 on excess); payload deserialization with `extra='ignore'` and `schema_version` field; idempotent upsert on `(host, port, sensor_id, scan_id)`; `payload_id` dedup against `sensor_pushes` table (409 on replay); `pushed_at` + `received_at` stored; `console_utc` included in rejection responses for clock-skew diagnosis; `IntegrationDelivery` audit row per push; `safe_str()` on all exception stringification; 401-without-credentials test as gating success criterion.

**Avoids:** Pitfall 1 (ingest auth bypass), Pitfall 2 (replay + DoS), Pitfall 9 (clock skew), Pitfall 10 (version skew — `extra='ignore'` + `schema_version`).

**Research flag:** All patterns established. Skip research phase.

---

### Phase 5: Cross-Sensor Merge Pipeline

**Rationale:** Depends on Phase 4 (endpoints being pushed and stored with `sensor_id` set). The merge pipeline is the core product value of v5.4; CBOM correctness invariants must be rigorously enforced here.

**Delivers:** `quirk/sensor/merge.py` with `merge_scan()` feeding `build_evidence_summary()` -> `compute_readiness_score()` -> `build_cbom()` unchanged; enrollment manifest check before scoring; `coverage_warning` field in score JSON (list of overdue sensor IDs, or null); `quirk sensor merge` subcommand; CBOM regression tests (two sensors, same RFC1918 host/port, different `sensor_id` -> two distinct CBOM components); offline-sensor test (`coverage_warning` non-null).

**Avoids:** Pitfall 6 (CBOM over/under-merge — `sensor_id` included in component identity hash), Pitfall 7 (partial-result score — `coverage_warning` and enrollment manifest check).

**Research flag:** CBOM identity hash change (Pass 1 skip logic in `builder.py`) needs careful implementation review at plan time. Not full research, but flag for explicit seam audit.

---

### Phase 6: Console Dashboard Awareness

**Rationale:** First phase touching the frontend; depends on Phase 5 delivering a working merged result. Keep frontend changes batched to one phase to avoid React build churn.

**Delivers:** `sensor_id`/`segment` fields added to `FindingItem` Pydantic schema (nullable, backward-compat); scan route populates those fields; React findings table adds sensor/segment column with segment filter; sensor registry page showing sensor ID, segment label, version, last-seen, status badge; per-segment filter on `/api/scan/latest`, `/api/findings`, `/api/cbom`; offline sensor alert; scan result staleness flag; per-segment score gauges alongside org-wide gauge.

**Research flag:** Established React + shadcn/ui + FastAPI patterns in this codebase. Skip research phase.

---

### Phase 7: Stabilization Tail

**Rationale:** Pre-existing housekeeping items from HORIZON (`999.59` operators-guide all-configurations coverage, `_NoRedirectHandler` extraction to `quirk/util/no_redirect.py`, residual dep hygiene) that are independent of the sensor feature train. Note: `_NoRedirectHandler` extraction should ship no later than Phase 3 (the sensor push client needs it); if it slips, treat it as a Phase 3 blocker.

**Delivers:** `docs/operators-guide.md` expanded to cover Windows sensor install; `quirk/util/no_redirect.py` extracted; dep hygiene; UAT-SERIES.md updated for all v5.4 phases.

**Research flag:** No research needed.

---

### Phase Ordering Rationale

The ordering is entirely dependency-driven. The data-model keying decision (arch-doc -> data-model phase) gates everything. The sensor push (Phase 3) must exist before the ingest endpoint (Phase 4) has something to send. The merge pipeline (Phase 5) requires ingested data with `sensor_id` set. The dashboard (Phase 6) requires a working merged result to display. This is a strict linear dependency chain with one parallel opportunity: the Windows CI smoke test work in Phase 3 can be developed concurrently with Phase 4 ingest work once the wire format is locked in the arch-doc.

The grouping of Windows CI into Phase 3 (not a separate phase) is deliberate: the POSIX-ism audit and the Windows smoke test are part of the same correctness concern as the sensor push client. Separating them would allow the sensor to ship without Windows validation, which all researchers flagged as a recurrence risk.

### Research Flags

Phases with established patterns (skip research phase):
- **Phase 2 (Data Model):** `_ensure_columns` / `_ADDITIVE_MIGRATIONS` is the documented pattern.
- **Phase 3 (Sensor CLI):** Modeled exactly on `scheduler_cmd.py` dispatch; POSIX-ism scope is enumerated.
- **Phase 4 (Ingestion API):** All patterns established (auth middleware, delivery audit, `safe_str`).
- **Phase 6 (Dashboard):** Established React + FastAPI patterns in this codebase.
- **Phase 7 (Stabilization):** Housekeeping.

Phases needing careful implementation review (not full research, but explicit seam audit at plan time):
- **Phase 5 (Merge Pipeline):** CBOM builder Pass 1 component identity hash must include `sensor_id` — review `builder.py` Pass 1 skip logic before writing the Phase 5 plan.

Phases requiring PM decision confirmation before planning:
- **Phase 1 (Arch-Doc):** Three open PM questions must be resolved as outputs: (a) scoring Option A vs. B, (b) Windows floor/ceiling scope, (c) enrollment token expiry policy.

---

## Open PM Decisions Required

| Decision | Options | Recommendation | Risk of Deferring |
|----------|---------|----------------|-------------------|
| **Unified score methodology** | Option A: union of findings through existing engine (recommended); Option B: weighted average of per-segment scores by host count; Option C: weakest-link (not recommended) | Start with Option A — zero changes to existing engine; add `per_segment_scores` breakdown in report for context | If deferred past arch-doc, merge pipeline is built for the wrong model and must be reworked |
| **Windows packaging scope for v5.4** | Floor only (OS-agnostic contract + pip install + Windows CI smoke); ceiling (full PyInstaller frozen EXE + Scheduled Task + signed packaging) | Arch-doc phase decides; STACK research recommends Scheduled Task (not pywin32 Service) in v5.4 if full packaging is in scope | If unconstrained, Windows work balloons and slips the milestone |
| **Enrollment token expiry** | One-time-use (consumed on enrollment, recommended); time-windowed (e.g., 60-minute window as Rapid7 uses) | One-time-use — simpler, more secure for a consulting tool where deployment timelines are controlled | If not decided, sensor enrollment UX is ambiguous and must be retro-fitted |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Versions verified against live PyPI; integration points confirmed from source review of `auth.py`, `token_cmd.py`, `safe_exc.py`, `dispatcher.py`; no speculative additions |
| Features | HIGH | Grounded in official docs from Tenable, Rapid7/InsightVM, Qualys, Wazuh; dependency graph is deterministic |
| Architecture | HIGH | Grounded in real repo symbols (line numbers cited for all seams); patterns traced from existing subcommand dispatch, `_ensure_columns`, `_dispatch_schedule` |
| Pitfalls | HIGH | All pitfalls grounded in existing codebase inspection and confirmed line references; v5.x security posture review; zero speculative risks |

**Overall confidence:** HIGH

### Gaps to Address During Planning

- **CBOM Pass 1 `sensor_id` hash inclusion:** The exact change needed in `builder.py` is known (include `sensor_id` in the component identity key), but the specific line and data structure must be reviewed at Phase 5 plan time.
- **`_NoRedirectHandler` extraction timing:** Sensor push client needs `_NoRedirectHandler` from `quirk/util/no_redirect.py` before or concurrent with Phase 3. If not yet extracted, treat it as a Phase 3 prerequisite task, not Phase 7.
- **`sensor_pushes` table schema:** The exact dedup table design (`payload_id`, `sensor_id`, `received_at`, TTL/cleanup policy) is sketched but not fully specified. Phase 1 arch-doc should nail this so Phase 2 can create it in the same migration pass.
- **Merge trigger mechanism:** The arch-doc must decide between manual `quirk sensor merge` (simpler, v5.4 floor) and automatic console-side poll when all expected sensors have checked in (possible v5.5). Research recommends manual trigger for v5.4.

---

## Sources

### Primary (HIGH confidence — official docs + codebase source review)

- `quirk/dashboard/api/middleware/auth.py` — `require_auth` pattern, `hmac.compare_digest`, `HTTPBearer` + `X-API-Key` dual-header support
- `quirk/cli/token_cmd.py` — `secrets.token_urlsafe(32)` enrollment pattern
- `quirk/cli/scheduler_cmd.py` — `_dispatch_schedule` subcommand pattern; `signal.SIGTERM` at lines 258-259; relative path `output/scheduled` at line 136
- `quirk/intelligence/scoring.py` — six-subscore rollup `/1.5` at lines 288-291; `compute_readiness_score` signature
- `quirk/cbom/builder.py` — three-pass architecture; Pass 1 `algo_registry` dedup at line 461
- `quirk/db.py` — `_ensure_columns` helper (lines 127-157); `_ADDITIVE_MIGRATIONS` registry
- `quirk/models.py` — `CryptoEndpoint` schema (lines 9-94); `IntegrationDelivery` (lines 245-260)
- `quirk/util/safe_exc.py` — `safe_str()` ISEC-02 pattern
- `quirk/util/url_allowlist.py` — `validate_external_url()` SSRF guard
- `run_scan.py` — subcommand dispatch (lines 381-514); `scan_run_id` (line 913)
- `.planning/HORIZON.md` — v5.4 scope, Windows sizing-risk note, SaaS parked constraint
- [pypi.org/project/tenacity/](https://pypi.org/project/tenacity/) — version 9.1.4 confirmed
- [pypi.org/project/platformdirs/](https://pypi.org/project/platformdirs/) — version 4.3.7 confirmed
- [pyinstaller.org/en/stable/](https://pyinstaller.org/en/stable/) — version 6.20.0 confirmed
- [Rapid7 InsightVM — Configuring Distributed Scan Engines](https://docs.rapid7.com/insightvm/configuring-distributed-scan-engines/) — pairing key, engine status, version matching
- [Rapid7 InsightVM — Linking Assets Across Sites](https://docs.rapid7.com/insightvm/linking-assets-across-sites/) — same-IP problem, per-site dedup
- [Qualys — Heartbeat interval](https://success.qualys.com/support/s/article/000006611) — 15-minute default
- [Wazuh — Agent Enrollment](https://documentation.wazuh.com/current/user-manual/agent/agent-enrollment/index.html) — enrollment token pattern
- [Tenable — Export a Scan](https://docs.tenable.com/nessus/Content/ExportAScan.htm) — air-gap file export pattern
- [sqlite.org/wal.html](https://sqlite.org/wal.html) — WAL shared-memory on Windows local filesystem
- [sqlite.org/useovernet.html](https://sqlite.org/useovernet.html) — WAL on network shares explicitly unsupported

### Secondary (MEDIUM confidence — evaluated and rejected)

- [pypi.org/project/sbommerge/](https://pypi.org/project/sbommerge/) — evaluated; rejected (file-based, not Python model API)
- [CycloneDX CLI](https://github.com/CycloneDX/cyclonedx-cli) — merge subcommand evaluated; known issue: does not remove duplicates; rejected in favor of in-process merge
- PyInstaller + pywin32 Windows Service combination — documented as "not well maintained" in PyInstaller issues; pywin32 Windows Service deferred to v5.5

---

*Research completed: 2026-05-25*
*Ready for roadmap: yes*
