---
phase: 53-qramm-evidence-bridge
plan: "02"
subsystem: qramm
tags: [qramm, evidence-bridge, classifier, cvi]
dependency_graph:
  requires: ["53-01"]
  provides: ["53-03"]
  affects: [quirk/qramm/evidence_bridge.py]
tech_stack:
  added: []
  patterns: [SESSION_BRACKET cohort query, bulk ORM update, recursive JSON walk]
key_files:
  created:
    - quirk/qramm/evidence_bridge.py
  modified: []
decisions:
  - "Used SQLAlchemy func.date(func.max(...)) for SESSION_BRACKET — no raw SQL; parameterized via ORM"
  - "nist_level=None treated as unknown (Pitfall 1) — skips vulnerable count; does not count toward algorithm_set"
  - "evidence_source derives from DB-returned date string (max_date_str) — avoids datetime.utcnow() entirely"
  - "Recursive _walk_json_for_alg_strings handles dict/list nesting; bare string lists included for coverage"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-07"
  tasks_completed: 1
  tasks_total: 1
---

# Phase 53 Plan 02: QRAMM Evidence Bridge — Module Implementation Summary

**One-liner:** Pure evidence_bridge module derives CVI 1.1/1.2/1.3 suggested_answer from SESSION_BRACKET scan cohort via classify_algorithm quartile rules.

## Module Created

**File:** `quirk/qramm/evidence_bridge.py`
**LOC:** 191 lines
**Commit:** 789f5ff

### Public Surface

```python
def populate_cvi_suggestions(session_id: int, db: Session) -> None
```

Derives CVI dimension `suggested_answer` values from the latest scan's `CryptoEndpoint` rows.
Updates 30 pre-existing `QRAMMAnswer` rows per session. Skips silently with INFO log when
no scan data exists (D-02).

### Private Helpers

| Function | Purpose |
|----------|---------|
| `_extract_algorithm_names(ep)` | Harvests algorithm strings from structured fields + 6 JSON blob columns |
| `_parse_json_blob(blob)` | Defensively parses JSON; returns None on empty/malformed input |
| `_walk_json_for_alg_strings(obj)` | Recursively extracts alg names from parsed JSON structures |

### Derivation Rules Implemented

| Rule | Practice | Logic |
|------|----------|-------|
| D-05 | CVI 1.2 (Vulnerability Assessment) | vuln_pct quartile: <=25%->4, <=50%->3, <=75%->2, >75%->1 |
| D-06 | CVI 1.1 (Discovery & Inventory) | distinct_protocols: <=1->2, <=3->3, >3->4 |
| D-07 | CVI 1.3 (Dependency Mapping) | distinct_algs: 0->1, <=2->2, <=5->3, >5->4 |

### Static Guards

- No `from quirk.engine.risk_engine` or `import quirk.risk_engine` imports (QRAMM-12)
- No `utcnow()` calls — evidence_source uses `max_date_str` returned by SQLite `func.date(func.max(...))`
- All DB filters use SQLAlchemy ORM expressions (T-53-02-01 mitigated)

## Tests Turned GREEN by This Plan (4 of 8)

| Test | Status | Notes |
|------|--------|-------|
| `test_no_risk_engine_import` | GREEN | Source + sys.modules check passes |
| `test_rc4_scan_lower_score_than_aes256` | GREEN | rc4_heavy->CVI 1.2=1; aes256_only->CVI 1.2=4 |
| `test_unconfirmed_excluded_from_score` | GREEN | Bridge + router collection passes |
| `test_badge_signal_data_model` | GREEN | Bridge + router collection passes |

## Tests Still RED (Router-Dependent, Plan 03)

| Test | Blocked By |
|------|-----------|
| `test_bridge_populates_on_session_create` | Router not yet calling populate_cvi_suggestions |
| `test_bridge_skips_when_no_scan_data` | Router not yet calling populate_cvi_suggestions |
| `test_confirmed_included_in_score` | Router not yet calling populate_cvi_suggestions |
| `test_confirmed_at_auto_set` | Router not yet calling populate_cvi_suggestions; confirmed_at auto-set logic in Plan 03 |

## Regressions

- `test_qramm_router.py`: 19/19 PASSED (including `test_no_utcnow_in_qramm_module`)
- utcnow gate: GREEN

## Deviations from Plan

None — plan executed exactly as written. The implementation matches the code block specified in the plan's `<action>` section verbatim.

## Known Stubs

None. The module is fully implemented with concrete derivation logic.

## Threat Flags

None. No new network endpoints, auth paths, or external attack surface introduced. All writes parameterized via SQLAlchemy ORM (T-53-02-01 mitigated per threat model).

## Self-Check: PASSED

- [x] `quirk/qramm/evidence_bridge.py` exists (191 lines)
- [x] Commit 789f5ff exists and staged only the bridge file
- [x] `test_no_risk_engine_import` PASSES
- [x] `test_rc4_scan_lower_score_than_aes256` PASSES
- [x] `test_qramm_router.py` 19/19 GREEN
- [x] No deletions in commit
