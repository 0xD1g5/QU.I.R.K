# Phase 107: Distributed Data Model - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-25
**Phase:** 107-distributed-data-model
**Areas discussed:** Table declaration idiom, Index creation seam, Foreign key constraints, ON DELETE semantics, Backward-compat fixture

---

## Table declaration idiom

| Option | Description | Selected |
|--------|-------------|----------|
| ORM models in models.py | Declarative classes alongside CryptoEndpoint; create_all picks them up | ✓ |
| Raw _ensure_*_table helpers | Hand-written CREATE TABLE in db.py, like scheduled_*/scan_jobs | |
| Hybrid | ORM for sensors, raw for sensor_pushes | |

**User's choice:** ORM models in models.py
**Notes:** Cleanest, least db.py churn, consistent with the primary model; create_all handles creation automatically.

---

## Index creation seam (sensor_id)

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit CREATE INDEX IF NOT EXISTS in init_db | Idempotent index step after additive-column migration; works for pre-existing DBs | ✓ |
| index=True on ORM column only | Relies on create_all — won't retro-index an existing crypto_endpoints table | |

**User's choice:** Explicit CREATE INDEX IF NOT EXISTS in init_db
**Notes:** `_ensure_columns` only does ALTER TABLE ADD COLUMN; index needs a dedicated step. The explicit path is the only one that satisfies MODEL-01 backward-compat for pre-existing tables.

---

## Foreign key constraints

| Option | Description | Selected |
|--------|-------------|----------|
| Real FKs with ON DELETE | ForeignKey to sensors.sensor_id, enforced by existing PRAGMA | ✓ |
| Loose String columns | Plain indexed strings, no FK | |

**User's choice:** Real FKs with ON DELETE
**Notes:** sensor_tokens/sensor_pushes get real FKs; CryptoEndpoint.sensor_id stays FK-free (NULL=local sensor per 106 D-03).

---

## ON DELETE semantics

| Option | Description | Selected |
|--------|-------------|----------|
| CASCADE both | Deleting a sensor removes its tokens and push-dedup records | ✓ |
| RESTRICT | Block sensor deletion while children exist | |
| CASCADE tokens, RESTRICT pushes | Tokens cascade, push audit trail blocks deletion | |

**User's choice:** CASCADE both
**Notes:** Re-enrollment mints a fresh sensor_id (UUID), so cascading away dedup history cannot enable cross-sensor payload_id replay. Clean teardown, no orphans.

---

## Backward-compat fixture

| Option | Description | Selected |
|--------|-------------|----------|
| Generated programmatically at test time | Build old-schema SQLite in tmp, migrate, assert no data loss | ✓ |
| Checked-in binary .sqlite fixture | Commit a frozen golden DB file | |

**User's choice:** Generated programmatically at test time
**Notes:** No binary blob in git; self-documenting; survives future schema changes.

---

## Claude's Discretion

- Exact column DDL fragments (subject to `_SAFE_COL_TYPE_RE`), index names, ORM class names.
- UniqueConstraint vs unique Index for `sensor_pushes.payload_id`.
- DateTime defaults vs caller-set timestamps (no writers in 107).

## Deferred Ideas

None — discussion stayed within phase scope.
