# Phase 106: Architecture Documentation - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers a **single, no-code architecture document** that locks every v5.4
distributed-scanner design decision that would be expensive to change mid-milestone.
It produces `docs/architecture-distributed.md` and ships zero runtime code. Every
downstream phase (107 data-model → 108 sensor/WinCI → 109 ingestion → 110 merge →
111 dashboard → 112 chaos-lab/stab) cites this doc as its canonical contract.

Satisfies ARCH-01, ARCH-02, ARCH-03, ARCH-04.

**Out of scope:** any code, schema migration, or CLI work — those belong to 107+.
Discussion clarified WHAT the doc must commit, not HOW to implement the sensor system.

</domain>

<decisions>
## Implementation Decisions

### Committed PM Decisions (carried forward — pre-locked before this discussion)
- **D-01:** Unified scoring = **Option A** — union of all sensor findings re-run through
  the existing `compute_readiness_score()` engine, unchanged. NOT weighted-average
  (Option B) or weakest-link (Option C). `per_segment_scores` breakdown added for context
  only. Averaging pre-scored sub-results is mathematically wrong (ratio penalties use
  full-population denominators).
- **D-02:** Enrollment tokens = **one-time-use** — `secrets.token_urlsafe(32)`, SHA-256
  hash stored in `sensor_tokens` (raw token never persisted), consumed at enrollment.
  NOT time-windowed. Mirrors `token_cmd.py`.
- **D-03:** Data-model keying = **`(sensor_id, host, port)`** uniqueness. `sensor_id`
  (nullable String, indexed) and `segment` (nullable String) added to `CryptoEndpoint`.
  **NULL `sensor_id` = implicit local sensor** (backward-compatible). CBOM Pass-1 component
  identity hash must include `sensor_id`.
- **D-04:** Forbidden additions (doc MUST enumerate as a concrete violation reference):
  Celery, Redis, MQTT/RabbitMQ, PostgreSQL, JWT per-sensor tokens, mTLS/PKI infra,
  `tenant_id`, sbommerge, CycloneDX CLI merge, pywin32 Service.

### Windows Scope (ARCH-03 — formally decided HERE)
- **D-05:** **Floor in v5.4; ceiling → v5.5.**
  - **Floor (v5.4):** OS-agnostic sensor/console wire contract; `pip install` on Python
    3.11+ with no POSIX dependencies; POSIX-ism audit (`scheduler_cmd.py:136` relative
    path → `cfg.output_root / "scheduled"`; `:258-259` SIGTERM → platform-conditional);
    `platformdirs` for data dirs; `windows-latest` CI smoke job as a **hard gate**
    (not `continue-on-error`).
  - **Ceiling (v5.5):** full PyInstaller frozen EXE + Windows Scheduled Task registration
    + signed packaging.
  - `pywin32` Windows Service is **out entirely** (Scheduled Task covers the v5.4 use case
    without admin elevation).

### Merge Trigger Mechanism
- **D-06:** **Manual `quirk sensor merge`** in v5.4 (operator-invoked command / console
  button). The merge function (`merge_scan()`) is designed as a **standalone callable**
  so a v5.5 automatic poll-on-full-check-in trigger can invoke it without refactoring.
  No poller / scheduler state is built in v5.4 — the doc records the seam only.

### Ingest Dedup & Replay Policy (feeds the `sensor_pushes` table in Phase 107)
- **D-07:** `payload_id` (UUID) unique per push; duplicate → **HTTP 409**.
- **D-08:** Replay window **±15 min** (`pushed_at` vs `received_at`); outside window →
  reject with `console_utc` in the response for clock-skew diagnosis.
- **D-09:** Body-size limit **10 MB** → **HTTP 413** (FastAPI has no default limit).
- **D-10:** Accepted `payload_id`s retained **indefinitely — no TTL/cleanup job in v5.4**
  (single-tenant on-prem volume is low). Revisit in v5.5 if a deployment grows unbounded.

### Version-Skew Handling
- **D-11:** **Warn-only / accept.** Pydantic ingest model uses `extra='ignore'`
  (forward-compat: unknown fields dropped). Version mismatch (`schema_version` /
  `sensor_version`) **never blocks ingest** — it surfaces a non-blocking version-skew
  warning on the sensor registry/heartbeat page. Keeps air-gapped / lagging sensors working.

### Document Form & Structure
- **D-12:** **Single doc** at `docs/architecture-distributed.md` **with Mermaid diagrams**
  (topology + sensor→console push sequence — render in GitHub/Obsidian). One canonical
  source downstream plans cite by section. Section outline:
  1. Overview & design invariants
  2. Topology diagram (Mermaid)
  3. Wire contract (payload schema + `payload_id`, `pushed_at`, `received_at`,
     `schema_version`, `sensor_version`)
  4. Push sequence diagram (Mermaid)
  5. Data-model keying — `(sensor_id, host, port)`
  6. Enrollment & auth model
  7. Merge pipeline
  8. Committed PM decisions
  9. Forbidden additions
  10. Windows scope (floor / ceiling)

### Enrollment Manifest Fields (feeds the `sensors` table in Phase 107)
- **D-13:** Full field set: `sensor_id` (UUID, PK), `segment` (String, label),
  `engagement` (String, **nullable** — consulting/client context, in-scope for v5.4),
  `enrolled_at` (datetime), `last_push_at` (datetime, nullable),
  `expected_cadence_minutes` (int), `sensor_version` (String, nullable — drives skew warning).

### Coverage-Warning & Staleness Thresholds
- **D-14:** Default `expected_cadence_minutes` = **1440 (24h)**; a sensor is **overdue** when
  `now > last_push_at + 2× cadence`; merge emits `coverage_warning` listing overdue
  `sensor_id`s (or null when all current). Partial coverage **is scored but always flagged** —
  never silently merged as complete. Scan results flagged **stale after 30 days**. All
  thresholds operator-overridable.

### Air-Gap Export/Import Contract
- **D-15:** **Identical wire payload** for `quirk sensor export-results` →
  `quirk console import-results`. Export writes the exact same payload (same `payload_id`,
  `schema_version`, `pushed_at`, fields, zstd compression, HMAC) to a file; import runs it
  through the **same ingest + dedup path**. One schema, one merge path — export is
  "push-to-file."
  - **Transport-conditional replay rule:** the **±15-min replay window applies to HTTPS push
    only**. Air-gap import **skips the time-window check** (sneakernet transit may take days)
    but **keeps `payload_id` dedup → 409 on replay**. The doc must state this carve-out
    explicitly: replay-window is transport-conditional, NOT payload-conditional.

### Claude's Discretion
- Exact Mermaid diagram styling and the prose depth of each section.
- Whether the wire-contract section presents the payload as a JSON example, a field table,
  or both (planner/writer's call — both is fine).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v5.4 Research (this milestone — primary grounding)
- `.planning/research/SUMMARY.md` — synthesized v5.4 design; PM-decision table; phase
  ordering rationale; "Gaps to Address During Planning"
- `.planning/research/ARCHITECTURE.md` — component map, subcommand-dispatch pattern,
  cited repo seams
- `.planning/research/STACK.md` — minimal dep additions (`platformdirs>=4.3.7`,
  `tenacity>=9.1.4`, `PyInstaller>=6.20.0` build-time), prohibitions
- `.planning/research/FEATURES.md` — must-ship vs should-add vs defer-to-v5.5 feature tiers
- `.planning/research/PITFALLS.md` — 7 grounded pitfalls (same-IP collision, auth bypass,
  partial-merge, Windows POSIX-isms, replay/DoS, backward-compat, SaaS over-engineering)

### Project Planning
- `.planning/ROADMAP.md` §"v5.4 — Distributed On-Prem Scanner Architecture" — Phase 106
  goal + success criteria; downstream phase chain 107–112
- `.planning/REQUIREMENTS.md` — ARCH-01..04 (this phase); MODEL-01..04 (Phase 107 — the
  tables this doc's schemas feed)
- `.planning/backlog/999.22-distributed-multi-node-scanner-architecture` — original backlog
  origin of the milestone
- `.planning/HORIZON.md` — v5.4 scope, Windows sizing-risk note, SaaS-parked constraint

### Codebase Seams the Doc Must Reference (cited in research, verify at write time)
- `quirk/models.py` — `CryptoEndpoint` schema (~L9-94); `IntegrationDelivery` (~L245-260)
- `quirk/db.py` — `_ensure_columns` helper (~L127-157) + `_ADDITIVE_MIGRATIONS` registry
- `quirk/intelligence/scoring.py` — `compute_readiness_score()`; six-subscore `/1.5` rollup (~L288-291)
- `quirk/cbom/builder.py` — three-pass build; Pass-1 `algo_registry` dedup (~L461)
- `quirk/dashboard/api/middleware/auth.py` — `require_auth`, `hmac.compare_digest`
- `quirk/cli/token_cmd.py` — `secrets.token_urlsafe(32)` + SHA-256 hash enrollment pattern
- `quirk/cli/scheduler_cmd.py` — `_dispatch_schedule` subcommand pattern; POSIX-isms at L136 / L258-259
- `quirk/util/safe_exc.py` — `safe_str()` (ISEC-02); `quirk/util/url_allowlist.py` — `validate_external_url()` SSRF guard
- `run_scan.py` — subcommand dispatch (~L381-514); `scan_run_id` (~L913)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Subcommand dispatch in `run_scan.py`** — `quirk sensor` / `quirk console` follow the
  exact intercept pattern already used by `serve`, `schedule`, `token`, `export`, `ticket`.
  No package split; the doc documents "same package, new mode flags."
- **`_ensure_columns` / `_ADDITIVE_MIGRATIONS` (Phase 77)** — the additive-migration path
  the doc commits for `sensor_id`/`segment` + the three new tables. No Alembic.
- **`token_cmd.py` enrollment pattern** — directly mirrored for one-time sensor tokens.
- **Canonical engines (`build_evidence_summary` → `compute_readiness_score` → `build_cbom`)**
  — re-run unchanged over the union of pushed endpoints. The doc's merge section commits
  "never merge pre-scored sub-results."

### Established Patterns
- `Depends(require_auth)` applied at `APIRouter(dependencies=[...])` level — the ingest
  route inherits auth; doc must state this to prevent the auth-bypass pitfall.
- `safe_str()` on all exception stringification (AST-gated).
- zstandard level-3 compression + httpx — already in the codebase; reused for the wire transport.

### Integration Points
- New ingest route plugs into the existing FastAPI dashboard (one new route file).
- `IntegrationDelivery` audit row written per push (existing pattern).
- Merge pipeline triggers existing notification/SIEM hooks (v5.3 surface) unchanged.

</code_context>

<specifics>
## Specific Ideas

- Wire transport uses an `X-Sensor-Signature: hmac-sha256=<hex>` header for
  application-layer integrity (per-sensor token-derived). No mTLS in v5.4.
- File-per-payload spool directory (NOT SQLite) for sensor-side store-and-forward.
- `console_utc` echoed in rejection responses for clock-skew diagnosis.

</specifics>

<deferred>
## Deferred Ideas

- **Windows ceiling → v5.5:** PyInstaller frozen EXE, Scheduled Task registration, signed
  packaging. (D-05)
- **Automatic merge trigger → v5.5:** console-side poll-on-full-check-in; the v5.4
  `merge_scan()` is built standalone so this needs no refactor. (D-06)
- **`sensor_pushes` dedup TTL/cleanup → v5.5:** add only if a long-running deployment shows
  unbounded growth. (D-10)
- **Weighted scoring by host count (Option B) → v5.5:** validate Option A with real
  consultants first.
- **`pywin32` Windows Service, Windows Event Log, MSI/MSIX installer → v5.5+:** need explicit
  enterprise demand signal.

</deferred>

---

*Phase: 106-Architecture Documentation*
*Context gathered: 2026-05-25*
