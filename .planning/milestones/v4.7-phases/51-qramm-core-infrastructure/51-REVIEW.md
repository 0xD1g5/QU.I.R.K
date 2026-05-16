---
phase: 51-qramm-core-infrastructure
reviewed: 2026-05-06T11:30:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - quirk/models.py
  - quirk/db.py
  - quirk/qramm/__init__.py
  - quirk/qramm/questions.py
  - quirk/qramm/scoring.py
  - quirk/qramm/model_meta.py
  - quirk/dashboard/api/routes/qramm.py
  - quirk/dashboard/api/app.py
  - tests/test_qramm_models.py
  - tests/test_qramm_questions.py
  - tests/test_qramm_scoring.py
  - tests/test_qramm_router.py
  - tests/test_saml_scanner.py
  - tests/test_broker_scanner_redis.py
findings:
  critical: 0
  warning: 6
  info: 4
  total: 10
status: issues_found
---

# Phase 51: Code Review Report

**Reviewed:** 2026-05-06T11:30:00Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Phase 51 introduces the QRAMM ORM models (`QRAMMSession`, `QRAMMAnswer`, `QRAMMProfile`),
the 120-question catalog, a weakest-link scoring engine, and a five-endpoint CRUD router.
The isolation constraint on `scoring.py` is correctly enforced, the question catalog is
well-structured, and the explicit SQLite FK cascade in the DELETE handler is the right
call. That said, there are six warnings — none are blockers, but two will cause silent
data corruption under realistic conditions: duplicate question numbers within a single
batch request, and timezone stripping that loses the UTC offset in stored timestamps.
There is also a logic gap where scoring a session with zero answers returns HTTP 200 with
`maturity="Basic"`, which is semantically wrong and untested. Additional warnings cover
the `get_db()` dependency calling `init_db()` on every HTTP request, a multiplier range
mismatch between the model docstring and API validation, and a missing `db.rollback()` in
the FastAPI DB dependency. Four informational items cover a disconnected `QRAMMProfile`
model, a redundant `create_all` call, an untested zero-answer edge case, and a
`source_url` that points to a different domain than the canonical GitHub source.

---

## Warnings

### WR-01: Duplicate question_number in a single batch silently creates multiple rows

**File:** `quirk/dashboard/api/routes/qramm.py:169-193`

**Issue:** `save_answers` iterates over `payload.answers` with `autoflush=False`. When the
same `question_number` appears more than once in a single payload, the first iteration adds
a new `QRAMMAnswer` to the session identity map (not yet flushed to the DB). The second
iteration calls `one_or_none()` against the database, which cannot see the unflushed row,
so it also creates a new insert. After `db.commit()`, two rows exist for the same
`(session_id, question_number)` pair. There is no `UNIQUE` constraint on those columns in
`QRAMMAnswer`, so the DB accepts both rows silently. Downstream, `answers_count` will be
inflated and `score_session` will double-count the answer value for that question,
corrupting the dimension and overall scores. The test suite covers the upsert across two
separate requests (`test_save_answers_upsert_overwrites`) but does not cover duplicates
within a single request.

**Fix:** Deduplicate the input payload before processing. Because Pydantic v2 already
validates each item individually, the simplest fix is a pre-loop dedup that keeps the last
occurrence (matching "last write wins" upsert semantics):

```python
# Deduplicate: keep last occurrence per question_number within this payload
seen: dict[int, AnswerItem] = {}
for item in payload.answers:
    seen[item.question_number] = item
for item in seen.values():
    meta = get_question(item.question_number)
    existing = (
        db.query(QRAMMAnswer)
        ...
    )
```

---

### WR-02: Timezone-aware datetime stored in SQLite DateTime strips `tzinfo` on read-back

**File:** `quirk/dashboard/api/routes/qramm.py:92-93`, `quirk/models.py:106-107`

**Issue:** `_now_iso()` returns `datetime.now(timezone.utc)` — a timezone-aware datetime.
SQLAlchemy's `DateTime` column type (without `timezone=True`) stores the value as a
naive string in SQLite. On read-back, `tzinfo` is silently dropped. This means:

1. `created_at` and `updated_at` are stored as UTC but returned by the API without a `+00:00`
   suffix. Consumers cannot distinguish these timestamps from local-time values.
2. Any comparison between a freshly-constructed `_now_iso()` value (tz-aware) and a
   value read from the DB (tz-naive) will raise `TypeError: can't compare offset-naive
   and offset-aware datetimes` in Python code that does such comparisons.
3. The test in `test_saml_scanner.py:412` already documents this behaviour as a known
   stripping requirement (`expected_naive = datetime(2026, 1, 15, 12, 0, 0)  # tzinfo stripped`),
   confirming it is a real pattern rather than a theoretical concern.

**Fix (option A — preferred):** Use `DateTime(timezone=True)` in the ORM columns. SQLite
will store as ISO string with offset; SQLAlchemy will return tz-aware datetimes.

```python
# quirk/models.py
from sqlalchemy import Column, DateTime
created_at = Column(DateTime(timezone=True), nullable=True)
updated_at = Column(DateTime(timezone=True), nullable=True)
```

**Fix (option B — minimal):** Strip `tzinfo` at write time in `_now_iso()` to store
consistently naive UTC datetimes, and document the implicit UTC assumption:

```python
def _now_iso() -> datetime:
    # Store as UTC-naive; SQLite DateTime strips tzinfo on write anyway.
    return datetime.now(timezone.utc).replace(tzinfo=None)
```

---

### WR-03: `score_session` returns HTTP 200 with `maturity="Basic"` for a session with zero answers

**File:** `quirk/dashboard/api/routes/qramm.py:208-270`

**Issue:** When `score_session` is called on a session that has no answers, `rows` is
empty, all `dimension_scores` default to `0.0`, `compute_overall_score` returns
`overall=0.0`, and `_maturity_label(0.0)` falls through all thresholds to return `"Basic"`.
The QRAMM scale is 1-4; `0.0` is off-scale and does not map to any CSNP maturity level.
The response persists `status="scored"` and `score_json` with `overall=0.0, maturity="Basic"`,
which is semantically incorrect and misleading (a session that has no data should not
appear as a measured "Basic" maturity organisation). No test covers this code path.

**Fix:** Add a guard that returns a 422 or 400 if zero answered questions exist:

```python
rows = (
    db.query(QRAMMAnswer)
    .filter(QRAMMAnswer.session_id == session_id, QRAMMAnswer.answer_value.isnot(None))
    .all()
)
if not rows:
    raise HTTPException(
        status_code=422,
        detail="Session has no answered questions; cannot compute score.",
    )
```

---

### WR-04: `get_db()` calls `init_db()` — and therefore all migration checks — on every HTTP request

**File:** `quirk/dashboard/api/deps.py:37-38`

**Issue:** `init_db()` runs `Base.metadata.create_all()` plus eight `_ensure_*` migration
functions (each executing `sa_inspect(engine).get_columns(...)`) on every invocation.
`get_db()` calls `init_db()` on each request, meaning every API call pays the cost of all
schema migration probes. In addition, `get_db()` creates a new `Engine` per request via
`get_engine()`, which allocates a new connection pool each time. On a local SQLite setup
this is slow but survivable; if this dependency pattern is ever used against a remote DB
it will be a connection leak.

**Fix:** Initialise the engine once at application startup (e.g., in `create_app()` or via
a FastAPI `lifespan` event) and cache it. The dependency should only create a session from
the cached engine:

```python
# In quirk/dashboard/api/deps.py
_engine: Engine | None = None

def init_engine(db_path: str) -> None:
    global _engine
    _engine = init_db(db_path)

def get_db() -> Generator[Session, None, None]:
    assert _engine is not None, "call init_engine() at startup"
    db = sessionmaker(bind=_engine, autoflush=False, autocommit=False,
                      expire_on_commit=False)()
    try:
        yield db
    finally:
        db.close()
```

---

### WR-05: `get_db()` dependency does not rollback on exception

**File:** `quirk/dashboard/api/deps.py:46-49`

**Issue:** The `get_db()` generator only calls `db.close()` in `finally`. It does not call
`db.rollback()` on exception. If an endpoint raises after staging ORM changes (e.g., after
`db.add(...)` but before `db.commit()`), those staged changes are left in the session.
SQLAlchemy's `Session.close()` does release connections but does not guarantee a rollback
call path that clears pending state in all versions. The safe pattern for a generator-based
FastAPI dependency is:

```python
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

The current router endpoints call `db.commit()` manually and do not wrap those calls in
`try/except`, so an exception between the `db.add()` and `db.commit()` calls in
`create_session` (lines 122-125) or `save_answers` (lines 188-195) would leave dirty state
without a rollback.

---

### WR-06: `profile_multiplier` validation range in the API (0.5–2.0) contradicts the model docstring (0.8–1.5)

**File:** `quirk/dashboard/api/routes/qramm.py:87`, `quirk/models.py:140`

**Issue:** `ScoreRequest.profile_multiplier` is validated as `ge=0.5, le=2.0`. The
`QRAMMProfile` model docstring and the `multiplier` column comment both state the range is
`0.8-1.5`. The scoring docstring (`compute_overall_score`) says "typically 0.8-1.5".
Accepting `0.5` or `2.0` through the API while the data model documents `0.8-1.5` is a
contract inconsistency. A multiplier of `0.5` would halve all dimension scores, producing
results well outside the expected QRAMM 1-4 scale that `_maturity_label` is calibrated for;
a multiplier of `2.0` would push scores above `4.0` (e.g., `4.0 * 2.0 = 8.0`), which
`_maturity_label` handles by returning `"Optimizing"` for anything `>= 4.0`, masking the
out-of-range condition.

**Fix:** Align the Pydantic validation range with the documented range. If the wider range
is intentional for future phases, update the model docstring to match:

```python
# Option A: tighten to match model docstring
profile_multiplier: Optional[float] = Field(default=None, ge=0.8, le=1.5)

# Option B: update QRAMMProfile docstring to document the wider range
# "multiplier is the computed Float (range 0.5-2.0) applied to dimension scores"
```

---

## Info

### IN-01: `QRAMMProfile` model is created in the DB but never read or written by the router

**File:** `quirk/dashboard/api/routes/qramm.py:26`

**Issue:** `QRAMMProfile` is defined in `quirk/models.py` and included in `_ensure_qramm_tables`.
The router imports only `QRAMMAnswer` and `QRAMMSession`. The `QRAMMSession.profile_id` foreign
key field exists but is never populated by any endpoint. The `ScoreRequest.profile_multiplier`
is accepted as a raw float rather than looked up from a stored profile row. This means
`QRAMMProfile` has zero active callers in Phase 51 — it is dead infrastructure. This is
likely intentional (deferred to Phase 53/profile management), but it should be explicitly
noted as a `# TODO (Phase 53)` comment in the router to avoid confusion.

---

### IN-02: `_ensure_qramm_tables` is redundant — `Base.metadata.create_all(engine)` at line 223 already creates QRAMM tables

**File:** `quirk/db.py:193-204`, `quirk/db.py:223`

**Issue:** `init_db()` calls `Base.metadata.create_all(engine)` at line 223 with no
`checkfirst` argument (defaults to `False` — creates tables that don't exist, skips those
that do). Since `QRAMMSession`, `QRAMMAnswer`, and `QRAMMProfile` are registered on
`Base.metadata` at import time, they are already created by line 223. The subsequent call
to `_ensure_qramm_tables(engine)` at line 231 calls `Base.metadata.create_all(engine,
checkfirst=True)` again — this is a no-op after the first call. The function is harmless
but misleading; the docstring's claim that "these are entirely new tables — not new columns
— so we use create_all" conflates the reason for using `create_all` (correct) with the
claim that the function is necessary (incorrect). No fix is required for correctness, but
the second `create_all` call should be removed or the function should be documented as a
safety net only.

---

### IN-03: Maturity label `_maturity_label(0.0)` returns `"Basic"` — undocumented behaviour below the 1-4 scale

**File:** `quirk/qramm/scoring.py:66-84`

**Issue:** `_maturity_label` documents thresholds for `1.0-4.0` but silently returns
`"Basic"` for any score below `1.0` (including `0.0`). This is a consequence of WR-03 but
also an independent documentation gap: the docstring should state what happens for
out-of-range inputs.

```python
def _maturity_label(score: float) -> str:
    """...
    Thresholds verified from ...:
      < 1.0:  unscored (callers should guard before calling)
      1.0-1.4: Basic
      ...
    """
```

---

### IN-04: `model_meta.py` `source_url` points to `https://qramm.org`, not the canonical GitHub source

**File:** `quirk/qramm/model_meta.py:19`

**Issue:** `QRAMM_MODEL["source_url"]` is `"https://qramm.org"`. The module docstring and
`github_url` field both point to `https://github.com/csnp/qramm`. The `questions.py`
module header also cites the GitHub URL as the fetch source. `qramm.org` resolves (HTTP
200) but is a separate marketing site, not the canonical source for question catalog
versioning. Any staleness check that uses `source_url` to fetch the current model version
(planned for the CLI `quirk qramm status` command in Phase 55) would be checking the wrong
resource. The `source_url` should point to the authoritative release artifact or at
minimum to `https://github.com/csnp/qramm`.

---

_Reviewed: 2026-05-06T11:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
