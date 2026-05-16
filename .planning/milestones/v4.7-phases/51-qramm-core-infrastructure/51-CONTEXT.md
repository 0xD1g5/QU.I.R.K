---
phase: 51-qramm-core-infrastructure
type: context
status: active
source: /gsd-discuss-phase 51
updated: 2026-05-05
milestone: v4.7 Governance & Compliance Platform
requirements: [QRAMM-01, QRAMM-02, QRAMM-03, QRAMM-04, DEBT-01]
---

# Phase 51: QRAMM Core Infrastructure - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

The entire QRAMM backend foundation is created in this phase — everything
Phases 53–56 build on top of:

1. **Three SQLite tables** via ORM declarative models in `quirk/models.py`:
   `QRAMMSession`, `QRAMMAnswer`, `QRAMMProfile` — created idempotently via
   `_ensure_qramm_tables()` called from `init_db()`, no migration error on
   an existing v4.6 `quirk.db`.

2. **`quirk/qramm/` module** (new top-level package) containing:
   - `questions.py` — `QRAMM_QUESTIONS` constant, exactly 120 entries
   - `scoring.py` — weakest-link scoring engine + profile multiplier
   - `model_meta.py` — `QRAMM_MODEL` staleness constant (mirrors compliance
     pattern from v4.6 Phase 49)

3. **FastAPI CRUD router** at `quirk/dashboard/api/routes/qramm.py`:
   create session, read session, save/update answers, score session, delete
   session — registered in `app.py` at `/api/qramm/`.

4. **DEBT-01**: Replace all `datetime.utcnow()` calls with
   `datetime.now(timezone.utc)` across `quirk/logging_util.py`,
   `quirk/discovery/nmap_provider.py`, and any other affected modules.

**In scope:**
- `quirk/models.py` — three new ORM model classes
- `quirk/db.py` — `_ensure_qramm_tables()` + `init_db()` registration
- `quirk/qramm/__init__.py`, `questions.py`, `scoring.py`, `model_meta.py`
- `quirk/dashboard/api/routes/qramm.py` — CRUD router with inline Pydantic models
- `quirk/dashboard/api/app.py` — router registration
- `tests/test_qramm_questions.py` — count + schema unit test
- `tests/test_qramm_scoring.py` — weakest-link + multiplier unit tests
- `tests/test_qramm_router.py` — TestClient smoke tests (correct HTTP status
  codes, Pydantic validation per endpoint)
- DEBT-01 utcnow fix across all affected modules

**Out of scope:**
- Evidence bridge (Phase 53: auto-populating answers from scan findings)
- Assessment UI (Phase 54: React QRAMM pages)
- Compliance mapping view (Phase 55)
- PDF export with QRAMM section (Phase 56)
- `quirk qramm status` CLI subcommand (Phase 51 only wires model_meta.py;
  the CLI surface is QRAMM-07, part of Phase 55 requirements)

</domain>

<decisions>
## Implementation Decisions

### Question Catalog (QRAMM-03)
- **D-01:** Source the 120 question texts **verbatim from the publicly available
  CSNP QRAMM toolkit at qramm.org**. Researcher fetches docs directly and
  transcribes questions — no paraphrasing, no custom authoring.
- **D-02:** `maturity_labels` per question are **verbatim from the CSNP
  toolkit** (not adapted for QUIRK). Labels match the standard exactly so
  consultants can cross-reference with official QRAMM documentation.
- **D-03:** If qramm.org content turns out to be paywalled or inaccessible
  at research time, researcher surfaces the gap and falls back to a
  hand-crafted minimal catalog (correct schema, placeholder text) — does
  NOT block the phase.

### SQLite Tables (QRAMM-01)
- **D-04:** Three new tables use **SQLAlchemy ORM declarative models**
  (`QRAMMSession`, `QRAMMAnswer`, `QRAMMProfile` extending `Base`) added to
  `quirk/models.py`. This is consistent with the `CryptoEndpoint` pattern
  and gives better query ergonomics in the router.
- **D-05:** `_ensure_qramm_tables()` calls `Base.metadata.create_all()`
  scoped to the QRAMM models with `checkfirst=True`. No raw DDL strings, no
  duplicate column-existence guards. The function is called from `init_db()`
  alongside the existing `_ensure_*` functions.

### Scoring Engine (QRAMM-04)
- **D-06:** **Dimension score = `min()` of its 3 practice scores** (weakest-link
  rule, NOT average). Profile multiplier (0.8–1.5×) applied to weighted
  dimension scores. Overall score = average of 4 weighted dimensions.
- **D-07:** Unit tests cover **both paths**: (a) weakest-link formula — assert
  exact numeric agreement with a CSNP QRAMM reference calculation if
  researcher finds one, else a synthetic known-good example; (b) profile
  multiplier path — assert the multiplier is correctly applied to dimension
  scores before averaging.
- **D-08:** Fallback if no CSNP reference calculation is findable: use a
  hand-crafted synthetic example (e.g. practice scores `[2, 4, 3]` →
  dimension score `2`; multiplier `1.2` → weighted score `2.4`). Do NOT
  block on finding the official worked example.
- **D-09:** `scoring.py` MUST NOT import `risk_engine` or any scanner module
  (circular import prevention, per QRAMM-12 note that applies from Phase 51
  onward).

### Computed Score Persistence
- **D-10:** `POST /api/qramm/sessions/{id}/score` computes AND persists the
  score to `qramm_sessions` (a `score_json` column or equivalent). Subsequent
  reads return the stored score. Re-calling the endpoint triggers fresh
  computation and updates the stored value. Phase 54 UI reads stored score —
  no re-computation on every page load.

### FastAPI Router & Pydantic Models (QRAMM-02)
- **D-11:** QRAMM Pydantic request/response models live **inline** in
  `quirk/dashboard/api/routes/qramm.py`. Consistent with `scan.py`,
  `trends.py`, `health.py` pattern. Refactor to a separate models file is
  deferred unless the file grows unwieldy.
- **D-12:** Router includes **TestClient smoke tests** in
  `tests/test_qramm_router.py` covering all 5 endpoint families (create,
  read, save answers, score, delete) — correct HTTP status codes and
  Pydantic-validated payloads. These protect the Phase 51 surface from silent
  breakage before Phase 53 builds on it.

### datetime.utcnow Tech Debt (DEBT-01)
- **D-13:** All `datetime.utcnow()` calls replaced with
  `datetime.now(timezone.utc)` across `quirk/logging_util.py`,
  `quirk/discovery/nmap_provider.py`, and **any other affected modules**
  discovered by a project-wide grep. Test suite must produce zero
  `DeprecationWarning: datetime.utcnow()` messages after the fix.

### Claude's Discretion
- `qramm_sessions` column naming for stored score — `score_json` (JSON blob)
  or separate `score_float` + `score_detail_json` columns — planner decides
  what best fits the Phase 54 UI needs.
- Exact field names on ORM models beyond the schema specified in QRAMM-01 —
  researcher may add `created_at`, `updated_at` timestamps following the
  `CryptoEndpoint` convention.
- `model_meta.py` initial `last_verified` date and `qramm_version` string —
  planner sets based on what the CSNP toolkit version researcher finds.
- Whether `_ensure_qramm_tables()` belongs in `db.py` alongside existing
  `_ensure_*` functions or in a new `quirk/qramm/db.py` — planner decides
  based on whether co-location or module separation is cleaner.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/ROADMAP.md` §"Phase 51: QRAMM Core Infrastructure" — goal,
  depends on Phase 50, success criteria 1–5 (the authoritative spec)
- `.planning/REQUIREMENTS.md` — QRAMM-01 (table schema), QRAMM-02 (CRUD
  endpoints), QRAMM-03 (question catalog schema + count), QRAMM-04
  (weakest-link scoring + reference test), DEBT-01 (utcnow fix scope)

### Existing Codebase Patterns to Follow
- `quirk/db.py` — `_ensure_*` migration pattern, `init_db()` registration
  sequence, SQLAlchemy engine setup, `_SAFE_COL_RE` allowlist pattern
- `quirk/models.py` — `CryptoEndpoint` ORM declarative model (extend `Base`
  the same way for QRAMM tables)
- `quirk/dashboard/api/routes/scan.py` — inline Pydantic model pattern,
  `APIRouter` setup, `Depends(get_db)` injection
- `quirk/dashboard/api/app.py` — `include_router()` registration pattern
- `quirk/compliance/__init__.py` — staleness pattern (`version`,
  `last_verified`, `source_url`, `STALENESS_THRESHOLD_DAYS`) that
  `model_meta.py` must mirror

### External Source Material (Researcher Must Fetch)
- `https://qramm.org` — CSNP QRAMM toolkit; researcher fetches 120
  questions, maturity labels, and any reference calculation examples for
  the scoring unit test

### Project / Workflow Mandates
- `CLAUDE.md` §"Mandatory Phase Completion Steps" — Obsidian phase note,
  UAT-SERIES.md update + sync, commit pattern
- `CLAUDE.md` §"Code Standards" — PEP 8, minimal diffs, `compileall` after
  changes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`quirk/db.py:_ensure_identity_columns()`** — template for the new
  `_ensure_qramm_tables()` function; same idempotency contract, same
  `init_db()` call site
- **`quirk/models.py:CryptoEndpoint`** — extend `Base` the same way for
  `QRAMMSession`, `QRAMMAnswer`, `QRAMMProfile`; follow column type choices
  (`String`, `Integer`, `Float`, `JSON`/`Text` for JSON blobs)
- **`quirk/compliance/__init__.py`** — `_pci()` / `_hipaa()` / `_fips()`
  builder pattern + `STALENESS_THRESHOLD_DAYS` + `_PHASE_49_VERIFIED` date
  constant → copy this pattern for `QRAMM_MODEL` in `model_meta.py`
- **`quirk/dashboard/api/routes/scan.py:router`** — inline Pydantic models
  at top of file, `APIRouter()` instance, `@router.get/post/delete` decorators

### Established Patterns
- **`_ensure_*` idempotency** — every DB evolution function uses `ADD COLUMN IF NOT EXISTS`
  or SQLAlchemy `checkfirst=True`; QRAMM tables follow via `create_all(checkfirst=True)`
- **FastAPI router registration** — one file per domain area in
  `quirk/dashboard/api/routes/`; registered in `app.py` with `prefix="/api"`
- **No `risk_engine` imports in data-layer modules** — isolation prevents
  circular imports; `scoring.py` is pure math, no scanner or engine imports

### Integration Points
- `quirk/db.py:init_db()` — call `_ensure_qramm_tables(engine)` at the end
  of the existing `_ensure_*` call sequence
- `quirk/dashboard/api/app.py` — `application.include_router(qramm.router, prefix="/api")`
  after the existing router registrations
- `tests/` — existing test suite uses `pytest`; new test files follow the
  `tests/test_*.py` naming convention and can use `tmp_path` fixtures for
  isolated SQLite test DBs

</code_context>

<specifics>
## Specific Ideas

- Score storage: the computed score must be persisted to `qramm_sessions` so
  Phase 54 UI can read it without re-computing on every page load.
- `scoring.py` isolation: zero imports from `risk_engine`, scanner modules,
  or anything that creates circular import chains — this constraint is
  established here so Phase 53's evidence bridge design respects it.
- The `quirk/qramm/` package sits at the same level as `quirk/compliance/`,
  `quirk/scanner/`, `quirk/cbom/` — a proper top-level subdirectory, not
  nested inside dashboard or assessment.

</specifics>

<deferred>
## Deferred Ideas

- **`quirk qramm status` CLI subcommand** (QRAMM-07) — model_meta.py is
  created here, but the CLI surface lives in Phase 55 requirements.
- **Refactor Pydantic models to dedicated `quirk/qramm/models.py`** — deferred
  unless the router file grows unwieldy; can be a cleanup task in a later phase.
- **Evidence bridge for SGRM/DPE/ITR dimensions** (QRAMM-F01) — deferred to
  v4.8; CVI bridge quality must be validated in Phase 53 first.

</deferred>

---

*Phase: 51-qramm-core-infrastructure*
*Context gathered: 2026-05-05*
