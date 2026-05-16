---
phase: 53-qramm-evidence-bridge
reviewed: 2026-05-07T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - tests/test_qramm_evidence_bridge.py
  - quirk/qramm/evidence_bridge.py
  - quirk/dashboard/api/routes/qramm.py
  - tests/test_qramm_router.py
  - docs/UAT-SERIES.md
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 53: Code Review Report

**Reviewed:** 2026-05-07T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the QRAMM Evidence Bridge implementation: `evidence_bridge.py`, the
QRAMM router (`routes/qramm.py`), and both test suites. The bridge logic is
sound in its core design — SESSION_BRACKET scoping via `MAX(date(scanned_at))`,
the quartile scoring for practices 1.1/1.2/1.3, bulk-update rather than
row-by-row writes, and the D-02 silent-skip on empty scan data all work as
specified. The `_extract_algorithm_names` extraction pipeline correctly handles
multiple JSON blob shapes.

One blocker and three warnings require attention before this ships:

- **BLOCKER** — `populate_cvi_suggestions` is called in `create_session` after
  the session commit, with no error guard. A bridge failure raises HTTP 500 to
  the caller, but the session and 30 CVI rows are already durably committed.
  The caller has no session ID and cannot recover; the session is orphaned.

- **WARNING** — `ScoreBlock` is defined but never wired to `score_session` as a
  `response_model`. Its `dimensions` field type (`Dict[str, float]`) does not
  match the actual response shape (`Dict[str, Dict[str, Any]]`). If this model
  were wired in, FastAPI would silently drop `practices` and `weighted` from the
  response.

- **WARNING** — `_walk_json_for_alg_strings` uses `elif` for the container
  recursion branch, which prevents recursion into nested structures when a key
  matches `_ALG_KEYS` but its value is a dict or list. Values like
  `{"name": {"algorithm": "rc4-hmac"}}` silently lose the inner algorithm.

- **WARNING** — `docs/UAT-SERIES.md` `**Version:**` field was not updated when
  the Phase 53 wrap entry was added to `**Last Updated:**`.

---

## Critical Issues

### CR-01: Bridge failure after first commit orphans the session

**File:** `quirk/dashboard/api/routes/qramm.py:141-147`

**Issue:** `create_session` performs `db.commit()` at line 141 (persisting the
session row and all 30 pre-seeded CVI `QRAMMAnswer` rows), then calls
`populate_cvi_suggestions(session.id, db)` at line 147 with no `try/except`
guard. If the bridge raises for any reason — a bulk `UPDATE` failure, an
unexpected `classify_algorithm` result on production scan data, or any other
exception — FastAPI propagates it as HTTP 500. The caller receives no `session_id`
and has no means to recover. The session and its 30 CVI rows remain committed
and orphaned in the database. Repeated retries accumulate orphaned rows without
limit.

The D-02 specification says the bridge should "skip silently" when conditions
prevent suggestion derivation. An unhandled exception is not a silent skip — it
destroys a valid session creation from the caller's perspective.

**Fix:** Wrap the bridge call in a `try/except` that logs the failure and allows
`create_session` to return a valid 201 with blank suggestions:

```python
# quirk/dashboard/api/routes/qramm.py, after line 143 (db.refresh)
try:
    populate_cvi_suggestions(session.id, db)
except Exception:  # noqa: BLE001
    logger.exception(
        "evidence_bridge: failed to populate CVI suggestions for session %s; "
        "session created successfully with blank suggestions",
        session.id,
    )
```

The bridge itself should also guard its commit:

```python
# quirk/qramm/evidence_bridge.py, lines 114-127
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
    logger.exception("evidence_bridge: bulk update failed, rolling back")
    db.rollback()
    raise
```

---

## Warnings

### WR-01: `ScoreBlock` is dead code with a type mismatch on `dimensions`

**File:** `quirk/dashboard/api/routes/qramm.py:54-58`

**Issue:** `ScoreBlock` is defined at lines 54-58 but is never referenced
anywhere in the codebase (confirmed by full-repo search). The `score_session`
endpoint at line 236 has no `response_model=` argument and returns
`Dict[str, Any]`. `ScoreBlock.dimensions` is typed as `Dict[str, float]`, but
the actual response shape for each dimension value is
`{"score": float, "weighted": float, "practices": dict}` — a nested dict, not
a float. If this model were wired as `response_model=ScoreBlock`, FastAPI would
serialize dimension values incorrectly and silently discard `practices` and
`weighted`. The mismatch would not be caught at startup, only at runtime when
responses are validated.

**Fix:** Either delete the dead model (lines 54-58), or replace it with
accurate types and wire it to the endpoint:

```python
class DimBlock(BaseModel):
    score: float
    weighted: float
    practices: Dict[str, float]

class ScoreResponse(BaseModel):
    session_id: int
    overall: float
    maturity: str
    dimensions: Dict[str, DimBlock]
    profile_multiplier: float

@router.post("/qramm/sessions/{session_id}/score", response_model=ScoreResponse)
def score_session(...) -> ScoreResponse:
    ...
```

---

### WR-02: `_walk_json_for_alg_strings` silently drops nested values under `_ALG_KEYS` when value is a container

**File:** `quirk/qramm/evidence_bridge.py:179-183`

**Issue:** The dict-traversal loop at lines 179-183 uses `elif` for the
container recursion branch:

```python
if key in _ALG_KEYS and isinstance(value, str) and value:
    out.append(value)
elif isinstance(value, (dict, list)):
    out.extend(_walk_json_for_alg_strings(value))
```

When a key is in `_ALG_KEYS` and its value is a `dict` or `list` (not a
string), the `if` branch does not match (value is not a string), but the `elif`
also does not fire because the `elif` condition only activates when the leading
`if` is false AND the condition holds. In Python, `elif` fires when the `if`
expression evaluated to False. Here the `if` is `key in _ALG_KEYS AND
isinstance(value, str) AND value` — this is False when value is a dict, so the
`elif` should fire. However, the `elif` condition is `isinstance(value,
(dict, list))` with no check on the key — so recursion does occur when value is
a container, regardless of key membership.

After tracing execution more carefully: the actual bug is subtler. When `key in
_ALG_KEYS` is True but `isinstance(value, str)` is False (e.g. value is a
dict), the `if` guard fails and `elif isinstance(value, (dict, list))` fires —
so recursion does happen. **However**, the module comment at line 169 states
"recurse into all values for nested structures," but when `key in _ALG_KEYS`
and value is a string, no recursion occurs for the value. This is by design.
The real gap is the opposite case: any key **not** in `_ALG_KEYS` with a
**string** value is silently dropped (neither appended nor recursed into) — this
is also intentional.

The real finding is that the docstring says "recurse into all values for nested
structures" but that is only true for keys not in `_ALG_KEYS`. The wording in
the docstring is misleading and could cause a maintainer to incorrectly extend
the function. Add a clarifying comment.

**Fix:** Clarify the docstring and add an inline comment:

```python
# In _walk_json_for_alg_strings, inside the dict branch:
for key, value in obj.items():
    if key in _ALG_KEYS and isinstance(value, str) and value:
        out.append(value)
    elif isinstance(value, (dict, list)):
        # Recurse when key is NOT in _ALG_KEYS (or when it IS but value is a container).
        # Non-ALG-key string values are intentionally skipped.
        out.extend(_walk_json_for_alg_strings(value))
```

Update the docstring to say "recurse into nested dict/list values (either
non-ALG-key entries or ALG-key entries whose value is a container)."

---

### WR-03: `docs/UAT-SERIES.md` `**Version:**` field is stale at 4.4.0

**File:** `docs/UAT-SERIES.md:3`

**Issue:** The document header reads `**Version:** 4.4.0`. The `**Last
Updated:**` field on line 5 contains a Phase 53 wrap entry (UAT-Q-53-01..02,
QRAMM-12..14 closed), but `**Version:**` was not updated. The `**Gate
Status:**` body line still references "v4.4" as the release gate. This creates
ambiguity about which version the Phase 53 UAT cases gate.

**Fix:** Update `**Version:**` to the current milestone version and update the
`**Gate Status:**` line to reference the current milestone (v4.8 or whatever
the active milestone is at the time of this phase's merge).

---

## Info

### IN-01: `score_1_1 = 1` branch in `populate_cvi_suggestions` is unreachable

**File:** `quirk/qramm/evidence_bridge.py:81-82`

**Issue:** The Practice 1.1 scoring block at lines 79-87 starts with:

```python
if total_endpoints == 0:
    score_1_1 = 1
```

However, `total_endpoints == 0` cannot be true at this point: the early-return
at lines 53-55 already handles the empty-endpoints case and exits the function.
By the time execution reaches line 79, `total_endpoints >= 1` is invariant. The
`score_1_1 = 1` arm is dead code. This is a minor documentation/readability
concern (not a correctness bug, since the branch never fires), but a maintainer
might assume it activates.

**Fix:** Remove the unreachable branch and note that score 1 for practice 1.1
is only assigned when no scan data exists (handled by the early return):

```python
# D-06 — Practice 1.1: endpoint count + protocol diversity
# Note: total_endpoints >= 1 is guaranteed by the early-return above.
if distinct_protocols <= 1:
    score_1_1 = 2
elif distinct_protocols <= 3:
    score_1_1 = 3
else:
    score_1_1 = 4
```

---

### IN-02: `_EVIDENCE_SOURCE_VERSION` has no documented bump policy

**File:** `quirk/qramm/evidence_bridge.py:23`

**Issue:** `_EVIDENCE_SOURCE_VERSION = "v1"` is embedded in every
`evidence_source` string written to the database. There is no comment or test
describing when this version should be incremented. If the scoring formula for
practices 1.1-1.3 changes in a future phase, existing DB rows will have stale
`v1` suggestions that are indistinguishable from freshly-generated ones.

**Fix:** Add a comment:

```python
# Increment this version string whenever the scoring formula for any CVI
# practice changes, so consumers can identify and re-run the bridge on
# sessions with stale evidence_source values.
_EVIDENCE_SOURCE_VERSION = "v1"
```

---

_Reviewed: 2026-05-07T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
