---
phase: 97-v5-1-tech-debt-cleanup
plan: "01"
subsystem: auth
tags: [credentials, docstring, comment, tech-debt, WR-02, WR-03, TD-01]
dependency_graph:
  requires: []
  provides: [corrected-from-cli-docstring, D-02-proliferation-comments]
  affects: [quirk/auth/credentials.py]
tech_stack:
  added: []
  patterns: [D-01-docstring-correction, D-02-accepted-proliferation-comment, decision-tag-inline-comment]
key_files:
  created: []
  modified:
    - quirk/auth/credentials.py
decisions:
  - "D-01: Corrected from_cli env-var docstring to 'any name present in the environment'; no isupper() enforcement (zero behavior change, per locked decision)"
  - "D-02: Added explicit D-05 proliferation comments at both decode sites in as_headers and query_param; no materialize-once refactor (per locked decision)"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-23"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 1
---

# Phase 97 Plan 01: Credential documentation corrections (D-01/D-02) Summary

**One-liner:** Corrected from_cli env-var docstring (no "all-caps" claim) and added accepted D-05 str-copy proliferation comments at both decode sites in as_headers/query_param — docstring and comment changes only, zero runtime behavior change.

## What Was Built

### Task 1: Correct from_cli env-var docstring (D-01 / WR-02)

The `from_cli` docstring in `quirk/auth/credentials.py` previously described the env-var
recognition rule as "Looks like an env-var name (all-caps, set in environment)" — but the
actual implementation at `_resolve_reference` uses `if ref in os.environ` with no case
constraint. This mismatch (WR-02 from 93-REVIEW) documented a contract that was never
enforced.

Changed the docstring bullet to:
```
- any name present in the environment (D-01): read and delete the env var
  (prevents subprocess inheritance, PITFALLS Pitfall 1)
```

No `isupper()` check added. No behavior changed. Decision tag `(D-01)` added for traceability.

**Commit:** `04e5b57`

### Task 2: Document accepted str-copy proliferation (D-02 / WR-03)

`as_headers()` and `query_param()` each call `self._secret_buf.decode("utf-8")` on every
invocation, materializing a new immortal `str` the GC controls and `close()` cannot zero
(WR-03 from 93-REVIEW). v5.1 D-05 already accepts best-effort zeroization, but the specific
per-call decode sites had no documentation acknowledging this accepted trade-off.

Added a 4-line comment directly above the decode line in both functions:
- States that the decode materializes an immortal str GC controls and close() cannot zero
- Notes the proliferation is explicitly accepted under v5.1 D-05
- Documents the once-per-endpoint-per-scan call bound (as_headers: once per scan_jwt_endpoint; query_param: once per _get)
- References `(D-05)` decision tag per established comment style

No refactoring to materialize-once. No signature or return type changes. Pure documentation.

**Commit:** `b30abf6`

## Verification

All checks passed:

- `grep -q "any name present in the environment" quirk/auth/credentials.py` — PASS
- `! grep -qi "all-caps" quirk/auth/credentials.py` — PASS
- `grep -A5 'def as_headers' ... | grep -q 'D-05'` — PASS
- `grep -A10 'def query_param' ... | grep -q 'D-05'` — PASS
- `python -m compileall quirk/auth/credentials.py` — exits 0
- `python -m pytest tests/test_credential_context.py tests/test_credential_leakage.py -q` — 51 passed

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 — from_cli docstring (D-01) | `04e5b57` | fix(97-01): correct from_cli env-var docstring — no all-caps requirement (D-01/WR-02) |
| 2 — as_headers/query_param comments (D-02) | `b30abf6` | docs(97-01): document accepted str-copy proliferation at decode sites (D-02/WR-03) |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. Both tasks are documentation-only; no new runtime surface, no new trust boundaries.
T-97-01 and T-97-02 both carry `accept` disposition in the plan threat register —
confirmed correct: no control was weakened.

## Self-Check: PASSED

- `quirk/auth/credentials.py` — modified and committed
- Commit `04e5b57` — confirmed in git log
- Commit `b30abf6` — confirmed in git log
- No isupper() guard added
- No signature or return type changes in as_headers/query_param
- All 51 credential tests pass
