# Phase 74 — Deferred Items

## 74-02 collateral discovery (pre-existing, out of scope)

- `tests/test_qramm_evidence_bridge.py::test_unconfirmed_excluded_from_score` —
  POST `/api/qramm/sessions/{id}/score` returns 422 (FastAPI request-body
  validation). Reproduced on `git stash` baseline (before 74-02 edits), so the
  failure is **not** caused by D-05..D-07 changes. Belongs to a separate
  router/schema fix outside QWARN-02 scope.
