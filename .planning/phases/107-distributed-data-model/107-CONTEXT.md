# Phase 107: Distributed Data Model - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase lands the **complete SQLite schema for sensor tracking** — and nothing
that consumes it. It adds two nullable columns to `CryptoEndpoint` plus three new
tables (`sensors`, `sensor_tokens`, `sensor_pushes`), wires them into the existing
`quirk/db.py` migration/creation machinery, and proves strict backward compatibility
against a pre-v5.4 database. No ingestion, merge, CLI, or API code — those are
Phases 108–110. The deliverable is: "every table and column the sensor system needs
exists, and `quirk scan` runs unchanged against an existing DB."

Satisfies MODEL-01, MODEL-02, MODEL-03, MODEL-04.

**Out of scope:** sensor enroll/push CLI (108), ingestion endpoint (109), merge
pipeline (110), dashboard (111). No data is *written* to the new tables in this
phase beyond what tests require — only the schema lands.

</domain>

<decisions>
## Implementation Decisions

### Pre-locked from Phase 106 architecture doc (carried forward — do NOT re-litigate)
These were decided in `106-CONTEXT.md` / `docs/architecture-distributed.md` and are
binding inputs to this phase's schema:
- **(106 D-03):** `CryptoEndpoint` keying is `(sensor_id, host, port)`. Add `sensor_id`
  (nullable String, **indexed**) and `segment` (nullable String). **NULL `sensor_id`
  = implicit local sensor** (backward-compatible).
- **(106 D-13):** `sensors` field set: `sensor_id` (UUID, PK), `segment` (String),
  `engagement` (String, nullable), `enrolled_at` (datetime), `last_push_at` (datetime,
  nullable), `expected_cadence_minutes` (int), `sensor_version` (String, nullable).
- **(106 D-02):** `sensor_tokens` stores **SHA-256 hashes** of one-time enrollment
  tokens; the raw token is never persisted. Mirrors `quirk/cli/token_cmd.py`.
- **(106 D-07/D-10):** `sensor_pushes` stores accepted `payload_id` + `sensor_id` +
  `received_at`; `payload_id` is **unique** (duplicate → 409 in Phase 109); rows are
  retained **indefinitely** (no TTL/cleanup job in v5.4).

### Table declaration idiom
- **D-01:** The three new tables (`sensors`, `sensor_tokens`, `sensor_pushes`) are
  declared as **SQLAlchemy declarative ORM models in `quirk/models.py`**, alongside
  `CryptoEndpoint`, so `Base.metadata.create_all(engine, checkfirst=True)` in `init_db`
  picks them up automatically. Do **not** hand-write `_ensure_*_table(engine)` helpers
  for them — that raw pattern (`scheduled_*`, `scan_jobs`, `integration_deliveries`) is
  reserved for tables needing FK-rebuild/non-declarative control, which these don't need.

### Index creation seam (sensor_id on crypto_endpoints)
- **D-02:** `sensor_id` must be indexed, but the additive-column path
  (`_ADDITIVE_MIGRATIONS` → `_ensure_columns`) only issues `ALTER TABLE … ADD COLUMN`
  and **cannot create indexes**. Add an explicit, idempotent
  **`CREATE INDEX IF NOT EXISTS`** step in `init_db` (after the additive-column
  migration runs), in the same allowlist-guarded spirit as `_ensure_columns`. This is
  the only path that correctly indexes a **pre-existing** `crypto_endpoints` table —
  `Column(..., index=True)` + `create_all(checkfirst=True)` will NOT retro-add an index
  to a table that already exists, so it is insufficient on its own for the
  backward-compat requirement (MODEL-01).
  - Planner note: the new `crypto_endpoints` columns (`sensor_id`, `segment`) should be
    added as a new `_V54_SENSOR_COLUMNS` tuple appended to `_ADDITIVE_MIGRATIONS` so
    `init_db` and `run_additive_migration` stay in sync (the single-source-of-truth
    contract established in Phase 85-01).

### Foreign keys & delete semantics
- **D-03:** `sensor_tokens.sensor_id` and `sensor_pushes.sensor_id` are **real
  FOREIGN KEYs** to `sensors.sensor_id`. SQLite FK enforcement is already active via the
  module-level `_sqlite_fk_pragma` listener (`db.py:31`), so these constraints are
  enforced at runtime, not decorative. (Note: `CryptoEndpoint.sensor_id` stays a plain
  nullable String with NO FK — NULL = implicit local sensor per 106 D-03, which an FK
  would forbid.)
- **D-04:** Both FKs use **`ON DELETE CASCADE`**. Deleting a `sensors` row removes its
  token hashes and its push-dedup records. Re-enrollment always mints a fresh
  `sensor_id` (UUID), so cascading away old dedup history cannot enable a cross-sensor
  `payload_id` replay. Clean teardown, no orphan rows.

### Backward-compatibility fixture
- **D-05:** The pre-v5.4 compatibility fixture (Success Criterion #2) is
  **generated programmatically at test time** — the test builds an old-schema SQLite
  (`crypto_endpoints` WITHOUT the sensor columns/tables) in a tmp dir, then runs
  `init_db` / `run_additive_migration` and asserts no data loss, no schema error, and
  that existing rows still score unchanged. Do **not** check a binary `.sqlite` golden
  file into the repo — the generated approach is self-documenting, reviewable, and
  survives future schema drift.

### Claude's Discretion
- Exact column DDL fragments (must satisfy `_SAFE_COL_TYPE_RE`: `TEXT|INTEGER|REAL|
  BOOLEAN|DATETIME|VARCHAR(\d{1,4})`), index names, and ORM class naming.
- Whether `sensor_pushes.payload_id` uniqueness is expressed as a `UniqueConstraint`
  vs a unique `Index` — either satisfies the 409-dedup contract.
- Whether `last_push_at` / `enrolled_at` use `DateTime` defaults or are set by callers
  in later phases (no writers exist yet in 107).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture contract (binding)
- `docs/architecture-distributed.md` — the v5.4 distributed-scanner contract. §5
  (data-model keying), §6 (enrollment & auth model), §3 (wire contract — `payload_id`),
  §8 (committed PM decisions), §9 (forbidden additions). Every schema decision here
  must conform to this doc.
- `.planning/phases/106-architecture-documentation/106-CONTEXT.md` — source of the
  pre-locked decisions (D-02, D-03, D-07, D-10, D-13) carried forward above.

### Code seams (must integrate with, not replace)
- `quirk/db.py` §`_ADDITIVE_MIGRATIONS` (L172) + `_ensure_columns` (L127) — the
  additive-column registry the new `crypto_endpoints` columns plug into.
- `quirk/db.py` §`init_db` (L370–402) — table-creation + migration orchestration; the
  new `CREATE INDEX IF NOT EXISTS` step and ORM tables land here / via `create_all`.
- `quirk/db.py` §`_sqlite_fk_pragma` (L31) — confirms FK constraints are enforced.
- `quirk/db.py` §`run_additive_migration` (L184) — must stay in sync with `init_db`
  via the shared `_ADDITIVE_MIGRATIONS` registry.
- `quirk/models.py` §`CryptoEndpoint` (L9) — declarative ORM style to mirror for the
  three new model classes (classic `Column(...)`, not `mapped_column`).
- `quirk/cli/token_cmd.py` (L100) — `secrets.token_urlsafe(32)` token-minting pattern
  that the SHA-256 hashing in `sensor_tokens` mirrors.

### Requirements
- `.planning/REQUIREMENTS.md` — MODEL-01 … MODEL-04 (the four requirements this phase
  closes).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_ensure_columns(engine, table, expected)` — allowlist-guarded
  `ALTER TABLE ADD COLUMN` helper; the new `crypto_endpoints` columns flow through it
  via `_ADDITIVE_MIGRATIONS`.
- `run_additive_migration(engine, dry_run=…)` — idempotent migration walker; already
  the single source of truth paired with `init_db`. New columns get coverage for free
  once added to the registry.
- `Base.metadata.create_all(engine, checkfirst=True)` — auto-creates any new ORM model
  declared in `models.py`; no new helper needed for the three tables (D-01).
- `_sqlite_fk_pragma` listener — makes `ON DELETE CASCADE` (D-04) actually enforced.

### Established Patterns
- **Two table-creation idioms coexist**: declarative ORM (`CryptoEndpoint`) vs raw
  `_ensure_*_table` helpers (`scheduled_*`, `scan_jobs`). D-01 picks ORM for the new
  tables.
- **Migration registry single-source-of-truth** (Phase 85-01): never add a column via
  `_ensure_columns` without also listing it in `_ADDITIVE_MIGRATIONS`, or `init_db` and
  `run_additive_migration` drift.
- **Allowlist-guarded DDL**: column names → `_SAFE_COL_RE`, types → `_SAFE_COL_TYPE_RE`.
  Any new DDL fragment must pass these or `_ensure_columns` raises.
- **Token hashing**: store SHA-256 of secrets, never the raw value (token_cmd pattern).

### Integration Points
- New `crypto_endpoints` columns → append `_V54_SENSOR_COLUMNS` to `_ADDITIVE_MIGRATIONS`.
- New index on `crypto_endpoints.sensor_id` → explicit `CREATE INDEX IF NOT EXISTS`
  step inside `init_db`.
- Three new ORM models → `quirk/models.py`; auto-created by the existing `create_all`
  call in `init_db`. No `init_db` edit needed for table *creation* (only the index step).

</code_context>

<specifics>
## Specific Ideas

- The backward-compat test should assert both schema integrity AND scoring stability:
  load old data, migrate, then confirm `compute_readiness_score()` produces the same
  result it did pre-migration (NULL `sensor_id` rows = local sensor, must score
  identically to today).
- `CLAUDE.md` mandate: run `python -m compileall` + relevant tests after changes; this
  phase changes no detection logic so `labs/*/expected_results.md` need no update.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. Writers/consumers of these tables
(enrollment, push ingest, merge) are already scoped to Phases 108–110 and were not
re-opened here.

</deferred>

---

*Phase: 107-distributed-data-model*
*Context gathered: 2026-05-25*
