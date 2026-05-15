---
phase: 70
plan: 02
subsystem: api
tags: [block-08, cr-06, classifier, exception-narrowing, scan-route]
requires: []
provides:
  - "module-scope `_qs_for_alg` importable as `from quirk.dashboard.api.routes.scan import _qs_for_alg`"
  - "module-level `logger` in scan.py for future structured warnings"
  - "narrowed-except contract: KeyError/TypeError/AttributeError → 'Unknown' + WARNING; other types propagate"
affects:
  - quirk/dashboard/api/routes/scan.py
  - tests/test_cbom_scan_route.py
tech-stack:
  added: []  # stdlib `logging` only — already a project dependency
  patterns:
    - "module-level logger via `logging.getLogger(__name__)` (mirrors qramm.py)"
    - "narrow exception tuple at call site (Pitfall 5 from 70-RESEARCH.md)"
    - "lazy classifier import inside the lifted function to preserve dotted-path monkeypatch contract"
key-files:
  created:
    - tests/test_cbom_scan_route.py
  modified:
    - quirk/dashboard/api/routes/scan.py
decisions:
  - "Lifted `_qs_for_alg` from a closure inside `_derive_cbom` to module scope (closes RESEARCH Open Question 2). Cost: ~3 lines of indentation change; benefit: directly importable and monkeypatchable in unit tests without instantiating `_derive_cbom`."
  - "Kept the `from quirk.cbom.classifier import classify_algorithm, quantum_safety_label` import LAZY (inside `_qs_for_alg`) rather than promoting it to module scope. Rationale: `monkeypatch.setattr(\"quirk.cbom.classifier.classify_algorithm\", _raises)` patches the attribute on the classifier module; a lazy `from ... import ...` re-resolves that attribute on every call, so the patch takes effect. A module-scope import would bind `classify_algorithm` once at import time, before tests can patch it, breaking the test contract."
  - "Did NOT touch the other broad `except Exception:` clauses elsewhere in scan.py. Per CONTEXT D-07 / 70-CONTEXT.md `<deferred>`, those belong to Phase 75 (api-cli-core WARNINGs). This plan stays surgical to BLOCK-08/CR-06."
metrics:
  duration: ~12 min
  completed: 2026-05-15
---

# Phase 70 Plan 02: Classifier Except Narrowing Summary

Replaced the bare `except Exception:` at `quirk/dashboard/api/routes/scan.py::_qs_for_alg` with `except (KeyError, TypeError, AttributeError) as e:` plus a `logger.warning("classifier failed for alg=%r: %s", alg, e)`, lifted the function to module scope for direct testability, and added a dedicated test file proving both the swallowed-and-logged path and the propagation path.

## What Was Built

### Source change — `quirk/dashboard/api/routes/scan.py`

1. **Module logger added.** `import logging` joins the stdlib import block; `logger = logging.getLogger(__name__)` sits at module scope just before the `router` declaration, mirroring the established idiom from `quirk/dashboard/api/routes/qramm.py`.
2. **`_qs_for_alg` lifted to module scope.** Previously a closure inside `_derive_cbom`; now a top-level function with a docstring describing the BLOCK-08/D-05 narrowing and the lazy-import rationale.
3. **Exception narrowed.** `except Exception:` → `except (KeyError, TypeError, AttributeError) as e:`. A `logger.warning(...)` precedes the existing `raw = "unknown"` fallback. Any other exception type (`RuntimeError`, `ValueError`, etc.) now propagates to the route handler instead of being silently relabeled `"Unknown"`.
4. **Lazy classifier import retained.** `from quirk.cbom.classifier import classify_algorithm, quantum_safety_label` stays inside `_qs_for_alg` so the dotted-path `monkeypatch.setattr` contract used by the new tests works correctly.

### New test file — `tests/test_cbom_scan_route.py`

Six test cases (5 parametrized + 1 happy-path):

| Test | Purpose |
|------|---------|
| `test_qs_for_alg_returns_unknown_on_narrowed_exc[KeyError]` | KeyError → "Unknown" + "classifier failed" WARNING |
| `test_qs_for_alg_returns_unknown_on_narrowed_exc[TypeError]` | TypeError → "Unknown" + "classifier failed" WARNING |
| `test_qs_for_alg_returns_unknown_on_narrowed_exc[AttributeError]` | AttributeError → "Unknown" + "classifier failed" WARNING |
| `test_qs_for_alg_propagates_unrelated_exc[RuntimeError]` | RuntimeError propagates; no log |
| `test_qs_for_alg_propagates_unrelated_exc[ValueError]` | ValueError propagates; no log |
| `test_qs_for_alg_happy_path_no_warning` | Real "RSA-2048" classification returns non-empty string with no WARNING |

All six tests pass against the new code (GREEN). The first commit captured them in the RED state (ImportError, since `_qs_for_alg` was a closure) per the TDD gate sequence.

## Tasks & Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 (RED) | Failing tests for narrowed-except + propagation + logged warning + happy path | `f90ffe2` |
| 2 (GREEN) | Module logger, lifted `_qs_for_alg`, narrow except, warning log | `10edcf5` |

## Verification

- `python -m compileall quirk tests` — clean.
- `pytest tests/test_cbom_scan_route.py -v` — 6 passed in 0.20s.
- `pytest tests/ -k "(scan or cbom) and not broker" --ignore=tests/test_cbom_scan_route.py` — same 21 pre-existing failures as the pre-change baseline (verified via `git stash` round-trip). All pre-existing failures are out of scope (cyclonedx schema validation requires optional extras, see STATE.md deferred items; `test_cli_correctness::test_no_quirk_scan_references` and `test_dashboard_scan_history::test_compare_self` predate this plan).
- Acceptance grep checks all match exactly:
  - `import logging` — 1 match (line 5)
  - `logger = logging.getLogger(__name__)` — 1 match at module scope (line 46)
  - `def _qs_for_alg(` — 1 match at module scope (line 635)
  - `except (KeyError, TypeError, AttributeError)` — 1 match (line 652)
  - `logger.warning("classifier failed` — 1 match (line 653)

## Deviations from Plan

None — plan executed exactly as written. The lazy-import decision was anticipated by the plan's `<action>` block ("keep it lazy inside `_qs_for_alg` if it must remain lazy"); the test contract requires it.

## Threat Model Coverage

`T-70-04` (silent suppression / repudiation) is now mitigated: only the three narrow exception types are swallowed (with an audit-trail WARNING log), and all other types surface for normal error handling. `T-70-05` (input tampering) remains accepted per CONTEXT — `alg` is internally sourced from CryptoEndpoint records, not user free-text.

## Threat Flags

None — no new network surface, auth path, file access pattern, or schema change introduced. Scope is exception-handling and logger plumbing inside an existing helper.

## Known Stubs

None.

## Self-Check

- Files exist:
  - tests/test_cbom_scan_route.py — FOUND
  - quirk/dashboard/api/routes/scan.py — FOUND (modified)
- Commits exist:
  - f90ffe2 — FOUND
  - 10edcf5 — FOUND

## Self-Check: PASSED
