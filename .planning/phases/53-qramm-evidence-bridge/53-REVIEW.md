---
phase: 53-qramm-evidence-bridge
reviewed: 2026-05-07T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - tests/test_qramm_evidence_bridge.py
  - quirk/qramm/evidence_bridge.py
  - quirk/dashboard/api/routes/qramm.py
  - tests/test_qramm_router.py
findings:
  critical: 2
  warning: 4
  info: 2
  total: 8
status: issues_found
---

# Phase 53: Code Review Report

**Reviewed:** 2026-05-07T00:00:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed the QRAMM Evidence Bridge implementation (Phase 53): `evidence_bridge.py`, the QRAMM
router, and both test suites. The bridge logic is generally sound in its approach to SESSION_BRACKET
scoping and quartile scoring. However, two blockers exist: an unhandled `IndexError` that can crash
the `save_answers` endpoint on any non-CVI question number in a CVI-seeded session, and a silent
data integrity failure where `populate_cvi_suggestions` calls `db.commit()` unconditionally — if
the bridge is ever called when `create_session` has not yet committed, this double-commit can
produce inconsistent state. There are also four warnings around error handling, scoring logic
edge cases, and test isolation, plus two minor info items.

---

## Critical Issues

### CR-01: `get_question` IndexError not caught in `save_answers` — crashes on valid Pydantic input

**File:** `quirk/dashboard/api/routes/qramm.py:193`

**Issue:** `get_question(item.question_number)` raises `IndexError` (see `questions.py:207`) when
`question_number` is not in 1..120. Pydantic validates `ge=1, le=120`, so any integer in that
range passes Pydantic. However, `get_question` performs its own bounds check and raises
`IndexError` — not `HTTPException`. Because the caller does not catch `IndexError`, FastAPI will
propagate it as an unhandled 500. This is currently masked by test coverage that only exercises
Q1-Q2, but any future question-number that maps to a gap in `QRAMM_QUESTIONS` (if the list ever
has fewer than 120 entries due to a catalog build error) will crash in production.

More immediately: `save_answers` is called for questions 1-120, but `QRAMM_QUESTIONS` is
built by a series of `_entry()` calls that must produce exactly 120 entries. If it produces
fewer, Pydantic allows `question_number=N` through but `QRAMM_QUESTIONS[N-1]` raises
`IndexError`. The router converts nothing — FastAPI returns HTTP 500.

**Fix:**
```python
# quirk/dashboard/api/routes/qramm.py  ~line 193
try:
    meta = get_question(item.question_number)
except IndexError:
    raise HTTPException(
        status_code=422,
        detail=f"question_number {item.question_number} not found in question catalog",
    )
```

---

### CR-02: `populate_cvi_suggestions` calls `db.commit()` without exception handling — can leave session in partial state

**File:** `quirk/qramm/evidence_bridge.py:127`

**Issue:** `populate_cvi_suggestions` ends with an unconditional `db.commit()`. This is called
from `create_session` (router line 147) after the caller already called `db.commit()` at line 141.
Any exception raised between lines 114-126 in the bridge (e.g., a `SQLAlchemyError` during the
bulk `update()`) leaves the session DB state mid-transaction — the 30 CVI rows have already been
committed to the DB by `create_session`, but the `update()` call inside the bridge may have
partially mutated the session. SQLAlchemy will auto-rollback on connection close, but the caller
has no visibility into what happened. There is no `try/except` in the bridge and no `try/except`
in `create_session` wrapping `populate_cvi_suggestions`. A DB error in the bridge produces an
HTTP 500 with a session row that was committed but with no `suggested_answer` values set — an
inconsistent state the caller cannot distinguish from a successful no-scan-data skip.

**Fix:**
```python
# quirk/qramm/evidence_bridge.py — wrap the update loop
try:
    for practice_area, suggested_value in practice_scores.items():
        db.query(QRAMMAnswer).filter(
            QRAMMAnswer.session_id == session_id,
            QRAMMAnswer.dimension == "CVI",
            QRAMMAnswer.practice_area == practice_area,
        ).update(
            {
                QRAMMAnswer.suggested_answer: suggested_value,
                QRAMMAnswer.evidence_source: evidence_source,
            },
            synchronize_session="fetch",
        )
    db.commit()
except Exception:
    logger.exception("evidence_bridge: failed to persist suggestions, rolling back")
    db.rollback()
    raise
```

And in `create_session` (router line 147), wrap the call:
```python
try:
    populate_cvi_suggestions(session.id, db)
except Exception:
    logger.warning("evidence_bridge failed for session %s; suggestions unavailable", session.id)
    # Session is already committed; bridge failure is non-fatal
```

---

## Warnings

### WR-01: Score 1.1 (Discovery) is always >= 2 when any endpoints exist — score 1 is unreachable

**File:** `quirk/qramm/evidence_bridge.py:79-87`

**Issue:** The Practice 1.1 scoring branch sets `score_1_1 = 1` only when `total_endpoints == 0`.
But `total_endpoints == 0` is already handled before this block by the `not endpoints` check at
line 53-55 (which returns early). So by the time execution reaches line 82, `total_endpoints`
is always >= 1, making the `score_1_1 = 1` branch dead code. The minimum score for 1.1 will
always be 2 even if a single endpoint from a single protocol is seen, which misrepresents an
org with minimal coverage as "Developing" rather than "Basic". The logic should instead gate on
a minimum endpoint count threshold, not a zero check that can never be true at that point.

**Fix:** Replace the unreachable `total_endpoints == 0` guard with a meaningful threshold, for
example `total_endpoints < 5`, or remove the dead `score_1_1 = 1` arm and document that score 1
for 1.1 is only assigned when the session has no scan data (i.e., the function returns early at
line 53). At minimum, add a comment acknowledging the branch is logically unreachable to prevent
future maintainers from assuming it fires.

---

### WR-02: `_walk_json_for_alg_strings` double-counts values when an ALG key also contains nested structures

**File:** `quirk/qramm/evidence_bridge.py:179-183`

**Issue:** In the dict branch of `_walk_json_for_alg_strings`, when a key is in `_ALG_KEYS` and
its value is a string, the string is appended (line 181). But if the value is a `dict` or `list`,
the code falls through to the `elif isinstance(value, (dict, list))` branch (line 182-183) and
recurses. This means a value that is both an ALG key AND a dict/list is only recursed — the
mutual exclusivity is correct. However, any key that is NOT in `_ALG_KEYS` but has a string value
is silently skipped rather than recursed. This is intentional per the docstring, but the subtle
interaction means that if a blob has `{"name": {"algorithm": "rc4-hmac"}}` (name maps to a dict),
the outer `"name"` key is in `_ALG_KEYS`, the value is a dict, so the outer ALG key check
produces nothing and the `elif` recurse branch is NOT taken (because the `if` matched first, even
though no string was appended). The inner `"algorithm": "rc4-hmac"` is silently lost.

**Fix:** Rewrite the condition to always recurse into nested structures regardless of whether the
key matched:
```python
if isinstance(obj, dict):
    for key, value in obj.items():
        if key in _ALG_KEYS and isinstance(value, str) and value:
            out.append(value)
        if isinstance(value, (dict, list)):  # always recurse — was elif, causing missed nesting
            out.extend(_walk_json_for_alg_strings(value))
```

---

### WR-03: `save_answers` silently ignores `answer_value=0` due to truthiness check

**File:** `quirk/dashboard/api/routes/qramm.py:219`

**Issue:** The `confirmed_at` auto-set condition is:
```python
if existing.suggested_answer is not None and item.answer_value is not None:
```
Pydantic enforces `ge=1` so `answer_value=0` can never reach the handler — this is safe.
However, the analogous creation path (lines 203-210) sets `answer_value=item.answer_value`
without setting `confirmed_at`. If a new QRAMMAnswer row is being created (the `existing is None`
branch) for a question that happens to have a `suggested_answer` set (which cannot happen for new
rows, since `suggested_answer` is only populated by the bridge at session-create time and no new
row is seeded), then `confirmed_at` would not be auto-set. This is currently safe only because
bridge suggestions never create rows; they bulk-update pre-seeded rows. If the bridge is ever
extended to handle non-CVI questions, the `existing is None` branch will silently omit
`confirmed_at`. The guard should be made symmetric or a comment should explicitly document why
the create path cannot produce a row with `suggested_answer is not None`.

**Fix:** Add a clarifying assertion or comment in the `existing is None` branch:
```python
# New row: bridge never creates rows, only updates pre-seeded ones, so
# suggested_answer is always None here and confirmed_at is not set intentionally.
```

---

### WR-04: `test_confirmed_at_auto_set` assumes Q5 has a suggestion — breaks if bridge mapping changes

**File:** `tests/test_qramm_evidence_bridge.py:264`

**Issue:** `test_confirmed_at_auto_set` seeds `aes256_only` endpoints, creates a session, then
confirms Q5 with `answer_value=4` and asserts `row.suggested_answer is not None`. The assertion
that Q5 has a suggestion depends on the bridge having assigned `suggested_answer` to Q5, which
is within practice area 1.2. This is currently true because practice 1.2 covers Q11-20 per the
question catalog distribution (CVI 1.1=Q1-10, 1.2=Q11-20, 1.3=Q21-30). But Q5 is in practice 1.1,
not 1.2. With `aes256_only` scenario, practice 1.2 score will be 4, and the bridge assigns
`suggested_answer` to all practice-1.1, 1.2, and 1.3 rows. So Q5 (practice 1.1) will have a
suggestion. The test assertion on line 269 (`assert row.suggested_answer is not None`) is correct
today but is fragile: it will silently pass even if the bridge stops assigning to practice 1.1,
or silently fail if question numbering is reorganized. The test should assert both the explicit
expected `suggested_answer` value AND explain why Q5 must have a suggestion.

**Fix:** Make the assertion explicit:
```python
assert row.suggested_answer is not None, (
    "Q5 is practice 1.1; bridge must set suggested_answer for aes256_only scenario"
)
assert row.suggested_answer == 4, "aes256_only -> practice 1.1 score should be 4 (>=4 distinct protocols check)"
```
Or use a question number that is unambiguously in the confirmed practice area.

---

## Info

### IN-01: `_EVIDENCE_SOURCE_VERSION` constant has no enforcement or increment policy

**File:** `quirk/qramm/evidence_bridge.py:23`

**Issue:** The module-level constant `_EVIDENCE_SOURCE_VERSION = "v1"` is embedded into every
`evidence_source` string written to the DB. There is no comment, test, or migration logic
describing when/how this version should be bumped. If the scoring formula for practices 1.1-1.3
changes in a future phase, stale `evidence_source` strings referencing `v1` will remain in the
DB, making it impossible to distinguish suggestions generated by the old formula from those
generated by the new one. A comment describing the versioning policy would suffice.

**Fix:** Add a comment:
```python
# Bump this version whenever the scoring formula for any practice changes,
# so stale suggestions can be identified and re-computed.
_EVIDENCE_SOURCE_VERSION = "v1"
```

---

### IN-02: Unused import `QRAMM_QUESTIONS` in router

**File:** `quirk/dashboard/api/routes/qramm.py:29`

**Issue:** `QRAMM_QUESTIONS` is imported at line 29 (`from quirk.qramm.questions import
QRAMM_QUESTIONS, get_question`) but the loop at line 130 that previously iterated over it has
been moved inside `create_session` using the same `QRAMM_QUESTIONS` reference. The import
is actually used (line 130). On review, the import is used — this is a false alarm. However,
the import line mixes `QRAMM_QUESTIONS` (used at line 130) with `get_question` (used at line
193). The real concern is that if `create_session` is ever refactored to call a helper, the
`QRAMM_QUESTIONS` import could become stale and no linter would catch it without running mypy
with `--strict`. Low severity; no action required unless the project adds an unused-import
linter gate.

**Fix:** No immediate action required. Ensure `ruff` or `flake8` is run as part of CI to catch
future drift.

---

_Reviewed: 2026-05-07T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
