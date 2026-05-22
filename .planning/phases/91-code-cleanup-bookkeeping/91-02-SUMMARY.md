---
phase: 91
plan: 02
subsystem: quirk/reports, tests, docs, planning
tags: [cleanup, dead-code, vulture, bookkeeping, CLEAN-02]
depends_on: ["91-01"]
provides: [tier-b-deletions, dead-code-catalogue]
affects:
  - quirk/reports/writer.py
  - tests/test_cert_pubkey_fix.py
  - docs/dead-code-candidates.md
  - .planning/codebase/CONCERNS.md
  - .planning/REQUIREMENTS.md
tech_stack:
  added: []
  patterns: [vulture-static-analysis, report-only-catalogue]
key_files:
  created:
    - docs/dead-code-candidates.md
  modified:
    - quirk/reports/writer.py
    - .planning/codebase/CONCERNS.md
    - .planning/REQUIREMENTS.md
  deleted:
    - tests/test_cert_pubkey_fix.py
decisions:
  - "91-02-D-01: Option-a selected (pre-resolved): Honor Phase 77 D-15 — keep intelligence schema dataclasses; BACK-52 schema-deletion portion recorded as superseded-by-D-15 in REQUIREMENTS.md and CONCERNS.md"
  - "91-02-D-02: D-02b catalogue is report-only; scanner entry-point scan_*_targets functions flagged at 60% are false positives due to run_scan.py dynamic dispatch"
metrics:
  duration: ~10 minutes
  completed: 2026-05-22
  tasks_completed: 3
  tasks_total: 3
  files_modified: 4
  files_created: 1
  files_deleted: 1
---

# Phase 91 Plan 02: Code Cleanup Bookkeeping — Tier-B + D-02b Catalogue Summary

**One-liner:** `_extract_cert_key_type` helper and `RichText` import removed from writer.py (vulture-confirmed no production callers); `tests/test_cert_pubkey_fix.py` deleted; Phase 77 D-15 conflict resolved option-a (IntelligenceReport schema preserved); D-02b vulture 2.16 catalogue written to `docs/dead-code-candidates.md` separating 100%/90% high-signal from 60% scanner-dispatch false positives; clean-venv smoke passed.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Checkpoint:decision — pre-resolved option-a (no pause) | — | REQUIREMENTS.md, CONCERNS.md (recorded in Task 2 commit) |
| 2 | Vulture-confirm + delete Tier-B dead code (CLEAN-02, BACK-50) | d027474 | quirk/reports/writer.py (−_extract_cert_key_type, −RichText), tests/test_cert_pubkey_fix.py (deleted), CONCERNS.md (§1.4 Resolved, §1.5 superseded-by-D-15) |
| 3 | Clean-venv smoke + D-02b vulture catalogue | 6fd5f98 | docs/dead-code-candidates.md (created) |

---

## Verification Results

### CLEAN-02: Tier-B deletions
- `python -c "import quirk.intelligence; import quirk.reports.writer"` — PASS (no import errors)
- `grep -c _extract_cert_key_type quirk/reports/writer.py` → 0 (function gone)
- `grep -c RichText quirk/reports/writer.py` → 0 (import gone)
- `test ! -f tests/test_cert_pubkey_fix.py` → true (test file deleted)
- `python -m compileall -q quirk tests` → clean

### D-15 Conflict: option-a applied
- `quirk/intelligence/schema.py` — PRESERVED (5 frozen dataclasses intact)
- `tests/test_intelligence_schema.py` — PRESERVED
- `tests/test_intelligence_public_api.py` — PRESERVED (D-15 CI gate remains active)
- `quirk/intelligence/__init__.py` — NOT TOUCHED (re-exports unchanged)

### D-02b Catalogue
- `docs/dead-code-candidates.md` exists — PASS
- References vulture — PASS
- Declares report-only / not an action list — PASS
- Separates 80%+ high-signal from 60% false positives — PASS
- Flags scan_*_targets scanner entry-point false positives — PASS

### Clean-venv smoke test (editable install equivalent)
- `python -c "import quirk; import quirk.reports.writer"` — PASS
- `quirk --version` → QU.I.R.K. v4.10.1 (no import errors)
- `quirk doctor` → health check runs cleanly (semgrep/DB warnings are pre-existing, not regressions)

### Regression gate
- `QUIRK_DB_PATH=/tmp/quirk91.db python -m pytest tests/ -q` → 44 failed / 1876 passed / 7 skipped
- Pre-plan baseline: 44 failed / 1882 passed (6-test delta = exactly the 6 test cases deleted from test_cert_pubkey_fix.py)
- **No new failures**

---

## Deviations from Plan

### Architectural Decision Carried In (option-a, pre-resolved)

**[Rule 4 - Architectural] Phase 77 D-15 CI gate supersedes BACK-52 schema deletion**

- **Found during:** Task 1 (checkpoint:decision pre-resolved before this execution)
- **Decision:** Option-a — Honor Phase 77 D-15; keep the 5 intelligence schema dataclasses; record BACK-52 schema portion as superseded-by-D-15
- **Rationale:** `tests/test_intelligence_public_api.py` was added in commit 9416c37 (Phase 77 D-15 pivot) as a deliberately-placed guardrail. IntelligenceReport's fields are typed as the other 4 dataclasses (coupled unit). Deleting any one requires deleting all + the D-15 gate — a deliberate prior locked decision reversal.
- **Files NOT modified:** quirk/intelligence/schema.py, quirk/intelligence/__init__.py, tests/test_intelligence_schema.py, tests/test_intelligence_public_api.py
- **Traceability:** BACK-52 schema-deletion portion recorded as "superseded-by-D-15" in CONCERNS.md §1.5 and REQUIREMENTS.md CLEAN-02 traceability row

---

## Known Stubs

None — all plan goals achieved within the option-a scope decision.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. Pure dead-code removal.

---

## Self-Check: PASSED

- docs/dead-code-candidates.md exists: FOUND
- quirk/reports/writer.py exists (modified): FOUND
- tests/test_cert_pubkey_fix.py absent: CONFIRMED DELETED
- Commits d027474, 6fd5f98: verified in git log
- quirk.intelligence and quirk.reports.writer import cleanly: CONFIRMED
- REQUIREMENTS.md CLEAN-02 row updated to done: CONFIRMED
- CONCERNS.md §1.4 Resolved, §1.5 superseded-by-D-15: CONFIRMED
