# Phase 51: QRAMM Core Infrastructure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 51-qramm-core-infrastructure
**Areas discussed:** Question catalog content, SQLite table approach, Scoring test reference values, Router & Pydantic model placement

---

## Question Catalog Content

### Q1: Where do the 120 question texts come from?

| Option | Description | Selected |
|--------|-------------|----------|
| CSNP QRAMM toolkit | Researcher adapts/transcribes from publicly available CSNP QRAMM documentation at qramm.org | ✓ |
| Draft from scratch | Author 120 questions based on 4 dimensions and NIST PQC guidance | |
| Placeholders for now | Stub text with correct schema; real questions authored in Phase 54 | |

**User's choice:** CSNP QRAMM toolkit (verbatim from qramm.org)

### Q2: Is the CSNP QRAMM toolkit freely available?

| Option | Description | Selected |
|--------|-------------|----------|
| Freely available | Researcher can fetch docs directly from qramm.org | ✓ |
| Requires access | User would need to provide source material | |
| Not sure — researcher finds out | Researcher investigates and adapts accordingly | |

**User's choice:** Freely available

### Q3: Should maturity_labels be verbatim from CSNP or adapted?

| Option | Description | Selected |
|--------|-------------|----------|
| Verbatim from CSNP | Labels exactly match framework — cross-referenceable with official docs | ✓ |
| Adapted for QUIRK | Researcher rewrites for QUIRK tone and consultant workflow | |

**User's choice:** Verbatim from CSNP

---

## SQLite Table Approach

### Q1: How should the three QRAMM tables be created?

| Option | Description | Selected |
|--------|-------------|----------|
| ORM declarative models | QRAMMSession/Answer/Profile extending Base in quirk/models.py; create_all() handles idempotency | ✓ |
| Raw DDL in _ensure_qramm_tables() | CREATE TABLE IF NOT EXISTS strings; consistent with column-add migration pattern | |
| You decide | Researcher and planner pick best fit | |

**User's choice:** ORM declarative models

### Q2: What does _ensure_qramm_tables() do internally?

| Option | Description | Selected |
|--------|-------------|----------|
| Base.metadata.create_all() only | ORM handles idempotency via checkfirst=True; no duplicate DDL | ✓ |
| create_all() + column-existence guards | Extra defensive checks for future schema evolution | |

**User's choice:** Base.metadata.create_all() only

---

## Scoring Test Reference Values

### Q1: Where do the known-good scoring values come from?

| Option | Description | Selected |
|--------|-------------|----------|
| Researcher derives from CSNP docs | Read CSNP QRAMM toolkit reference calculation; extract worked example | ✓ |
| Hand-crafted minimal example | Synthetic case proving weakest-link formula (no CSNP reference needed) | |
| Both — synthetic + CSNP reference | Belt-and-suspenders approach | |

**User's choice:** Researcher derives from CSNP docs

### Q2: Fallback if CSNP docs have no worked calculation?

| Option | Description | Selected |
|--------|-------------|----------|
| Fall back to hand-crafted test | Synthetic example proves formula; keep moving | ✓ |
| Block and ask the user | Surface gap and wait for user-provided values | |

**User's choice:** Fall back to hand-crafted test

### Q3: Should tests cover the multiplier path too?

| Option | Description | Selected |
|--------|-------------|----------|
| Cover both | Weakest-link test + multiplier path test | ✓ |
| Weakest-link formula only | Multiplier is simple; test it in Phase 54 | |

**User's choice:** Cover both (weakest-link + profile multiplier)

---

## Router & Pydantic Model Placement

### Q1: Where should QRAMM Pydantic models live?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline in the router file | Consistent with scan.py, trends.py, health.py pattern | ✓ |
| Separate quirk/qramm/models.py | Cleaner separation; reusable across router and evidence bridge | |

**User's choice:** Inline in the router file

### Q2: Score endpoint — persist to DB or on-demand?

| Option | Description | Selected |
|--------|-------------|----------|
| Persist to DB | Computed and stored in qramm_sessions; Phase 54 reads stored score | ✓ |
| On-demand only | Always freshly computed; not persisted in Phase 51 | |

**User's choice:** Persist to DB

### Q3: Router test coverage depth?

| Option | Description | Selected |
|--------|-------------|----------|
| Unit tests + basic router tests | tests/test_qramm_router.py with TestClient smoke tests per endpoint | ✓ |
| Unit tests only | Success criteria only require questions/scoring unit tests | |

**User's choice:** Unit tests + basic router tests

---

## Claude's Discretion

- `qramm_sessions` column naming for stored score (`score_json` vs `score_float` + `score_detail_json`)
- Exact ORM field names beyond QRAMM-01 schema (e.g. `created_at`, `updated_at` timestamps)
- `model_meta.py` initial `last_verified` date and `qramm_version` string
- Whether `_ensure_qramm_tables()` lives in `quirk/db.py` or `quirk/qramm/db.py`

## Deferred Ideas

- `quirk qramm status` CLI subcommand (QRAMM-07) — model_meta.py created here; CLI surface is Phase 55
- Refactor Pydantic models to `quirk/qramm/models.py` — deferred unless router grows unwieldy
- Evidence bridge for SGRM/DPE/ITR dimensions (QRAMM-F01) — deferred to v4.8
