---
phase: 74-qramm-compliance-warnings
plan: 02
subsystem: qramm/evidence-bridge + assessment/operator-context
tags: [qramm, evidence-bridge, attach-context, idempotency, tz-safety, audit-warnings]
dependency_graph:
  requires:
    - quirk/qramm/evidence_bridge.py (Phase 53 surface)
    - quirk/assessment/operator_context.py (Phase 64.1 surface)
    - sqlalchemy.exc.SQLAlchemyError
  provides:
    - TZ-symmetric date filter invariant (D-05)
    - idempotent CVI UPDATE loop (D-06)
    - SQLAlchemyError-handled commit (D-06)
    - narrowed AttributeError + Exception-fallback in attach_context (D-07)
  affects:
    - tests/test_evidence_bridge_correctness.py (new)
    - .planning/audit-2026-05-08/AUDIT-TASKS.md (4 rows closed)
tech_stack:
  added: []
  patterns:
    - "logger.warning + db.rollback + return for SQLAlchemy commit failures"
    - "pre-query + all(...) predicate for idempotent UPDATE loops"
    - "narrowed AttributeError except + fallback Exception that logs AND re-raises"
key_files:
  created:
    - tests/test_evidence_bridge_correctness.py
    - .planning/phases/74-qramm-compliance-warnings/deferred-items.md
  modified:
    - quirk/qramm/evidence_bridge.py (D-05 comment, D-06 idempotency, D-06 commit handler — landed in 74-01 combined commit 528b699)
    - quirk/assessment/operator_context.py (D-07 narrowed excepts + logger)
    - .planning/audit-2026-05-08/AUDIT-TASKS.md (4 WR rows flipped)
decisions:
  - D-05: kept SQL filter (RESEARCH C-3 path (a)); added inline invariant comment + regression test
  - D-06: idempotent pre-query + commit-failure SQLAlchemyError handler in same task
  - D-07: user-override — narrow AttributeError AND keep fallback `except Exception: log + raise`
metrics:
  duration_minutes: ~25
  completed_date: 2026-05-15
---

# Phase 74 Plan 02: QWARN-02 Evidence Bridge Correctness Summary

**One-liner:** Locked the evidence bridge TZ-symmetric invariant, made the CVI UPDATE loop idempotent + commit-failure-safe, and narrowed `attach_context` to log AttributeError while re-raising unexpected exceptions.

## What Shipped

### D-05 (WR-01) — TZ-symmetric date filter

- Existing SQL filter at `evidence_bridge.py:60-66` already uses `func.date(...)` on both sides — engine-symmetric, no TZ drift possible across the comparison.
- Added inline invariant comment naming this property and the downstream `datetime.date.fromisoformat(max_date_str)` requirement.
- Regression test `test_max_date_filter_is_tz_symmetric` inserts two endpoints with TZ-equivalent timestamps and asserts both bucket together.
- Regression test `test_max_date_str_parses_as_datetime_date` asserts the engine-returned string parses as `datetime.date.fromisoformat`.

### D-06 (WR-03) — Idempotent UPDATE

- Per-practice loop in `populate_cvi_suggestions` now pre-queries existing `QRAMMAnswer` rows for `(session_id, dimension='CVI', practice_area)`. If every existing row matches the target `(suggested_answer, evidence_source)` tuple, the `.update(...)` call is skipped (`continue`).
- First-time write path preserved: empty `existing` falls through to the UPDATE.
- Verified by `test_idempotent_repeat_call_does_not_rewrite` which spies on `.update(...)` invocations across two consecutive calls (expects 0 on call 2).

### D-06 (WR-07) — Commit-failure handler

- `db.commit()` wrapped in `try/except SQLAlchemyError as e: logger.warning("evidence_bridge UPDATE failed: %s", e); db.rollback(); return`.
- Verified by `test_commit_failure_logs_and_rolls_back` which patches commit to raise `SQLAlchemyError("boom")`, asserts rollback was called, caplog captures the WARNING, and the function returns without propagating.

### D-07 (WR-08) — `attach_context` narrowed excepts (user-override pattern)

- Per RESEARCH C-7 + user input override: both `except Exception:` blocks at `operator_context.py:85, 94` replaced with the two-clause pattern:
  ```python
  except AttributeError as e:
      logger.warning("attach_context skipped — source object missing attribute: %s", e)
  except Exception as e:
      logger.warning("attach_context unexpected: %s", e)
      raise
  ```
- Added `import logging` + `logger = logging.getLogger(__name__)` at module top.
- The first clause closes WR-08 (silent AttributeError swallow path). The second clause is the user-override safety net: unexpected exceptions (e.g. dataclass `FrozenInstanceError`, custom `__setattr__` raising `RuntimeError`) get logged AND re-raised — preserves visibility AND propagation.
- Verified by `test_attach_context_attribute_error_logged` (slots-locked cfg → AttributeError logged, no raise) and `test_attach_context_unexpected_exception_reraised` (RuntimeError logged AND re-raised via `pytest.raises`).

## Tests

- `tests/test_evidence_bridge_correctness.py` — 6 tests, all GREEN.
- `tests/test_qramm_staleness.py` (6 tests) + `tests/test_compliance_freshness.py` (1 test) — no regression.

## RED → GREEN cadence

| Commit | Type | Description |
|--------|------|-------------|
| `bf23c4a` | test | RED — 6 failing tests for D-05..D-07 |
| `971eeb9` | feat | GREEN — D-07 narrowed excepts in operator_context.py + test refinement (D-05/D-06 implementation already landed in 74-01 combined commit `528b699`) |
| `9c9762c` | docs | Audit ledger flip — WR-01, WR-03, WR-07, WR-08 → `Phase 74 \| [x] closed` |

## Audit ledger flips

- `qramm-compliance/WR-01` — Evidence bridge date-string equality vulnerable to TZ drift → **closed**
- `qramm-compliance/WR-03` — evidence_bridge synchronize_session=fetch suboptimal; no idempotency → **closed**
- `qramm-compliance/WR-07` — evidence_bridge does not handle db.commit failure → **closed**
- `qramm-compliance/WR-08` — attach_context swallows AttributeError; user context dropped → **closed**

## Deviations from Plan

### Auto-fixed / planner-anticipated

1. **[Plan deviation] D-05 + D-06 source edits already landed in 74-01 commit `528b699`**
   - Discovered during Task 2 GREEN step: 74-01 (`feat: implement QWARN-01 fixes`) bundled the `SQLAlchemyError` import, D-05 TZ invariant comment, D-06 idempotent UPDATE, and D-06 commit handler alongside its primary D-01..D-04 scope.
   - Action: did NOT duplicate edits in `evidence_bridge.py`; verified via grep that all required markers were already present (`SQLAlchemyError` import, "TZ-symmetric" comment, "idempotent skip" continue, "evidence_bridge UPDATE failed" log, db.rollback). Task 2 commit shipped only the `operator_context.py` D-07 edits + the test-fixture refinement.

2. **[Rule 1 - Test fix] `test_max_date_filter_is_tz_symmetric` initial assertion was overspecified**
   - Found during: Task 2 verification.
   - Issue: asserted `suggested_answer == 2`, but `score_1_1` is multiplied by `_discovery_factor(2) ≈ 0.25` per D-02 from 74-01 → actual value 0.5.
   - Fix: replaced numeric-value assertion with SQL-bucket-count assertion (both endpoints land in the same `func.date(max(...))` bucket → `count == 2`) plus a "suggested_answer is not None / evidence_source is not None" smoke check. Decouples this test from the Practice 1.1 scoring formula.

### Deferred (out of scope)

1. **Pre-existing `tests/test_qramm_evidence_bridge.py::test_unconfirmed_excluded_from_score` 422 failure**
   - The POST `/api/qramm/sessions/{id}/score` endpoint returns 422 (FastAPI request-body validation) regardless of the body content. Reproduced on `git stash` baseline (before 74-02 edits), so the failure is **not** caused by D-05..D-07 changes.
   - Logged to `.planning/phases/74-qramm-compliance-warnings/deferred-items.md`. Belongs to a router/schema fix outside QWARN-02 scope.

## Decisions Made

- **D-05 path (a) over path (b)** — preferred RESEARCH C-3 recommendation: keep the engine-symmetric SQL filter and document the invariant in code + test, rather than refactor the comparison to Python-side `datetime.date` math (which would require parsing both sides and is strictly worse for performance on large endpoint sets).
- **D-07 user override** — applied user's explicit refinement: the trailing `except Exception as e: logger.warning(...); raise` is mandatory in BOTH attach attempts. Pure narrow-`AttributeError` (as the CONTEXT textual diff implied) would silently regress dataclass `FrozenInstanceError` / custom-`__setattr__`-raising-`ValueError` paths.

## Threat Surface

No new attack surface introduced. The threat-model mitigations T-74-05 (silent state corruption), T-74-06 (lost commit), T-74-07 (silent context drop), and T-74-08 (missing audit trail) are now in place per `<threat_model>`.

## Self-Check: PASSED

- `tests/test_evidence_bridge_correctness.py` — exists, 6 tests, all GREEN
- `quirk/qramm/evidence_bridge.py` — `SQLAlchemyError`, `TZ-symmetric`, `idempotent skip`, `evidence_bridge UPDATE failed`, `db.rollback` all present
- `quirk/assessment/operator_context.py` — `import logging`, `logger = logging.getLogger`, 2× `except AttributeError as e`, `attach_context skipped`, `attach_context unexpected` all present
- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — 4 rows (WR-01/03/07/08) flipped to `Phase 74 | [x] closed`
- Commits: `bf23c4a` (test), `971eeb9` (feat), `9c9762c` (docs) — all present in `git log --oneline`
