---
phase: 01-foundation-fixes
plan: 01
subsystem: scoring
tags: [scoring, intelligence, cert, tls, writer, assessment, evidence]

# Dependency graph
requires: []
provides:
  - Single authoritative scoring path through qcscan/intelligence/scoring.py
  - cert_pubkey_alg as first probe in _extract_cert_key_type (CORE-02)
  - Dead code removed from writer.py (5 inline functions deleted)
  - Assessment layer removed from writer.py output pipeline
affects: [02-ssh-scanner, 03-sslyze-integration, 04-package-rename, web-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Intelligence layer pattern: build_evidence_summary -> compute_readiness_score -> compute_confidence -> build_phased_roadmap"
    - "Canonical cert key field: cert_pubkey_alg is checked first before fallback attributes"

key-files:
  created:
    - tests/test_cert_pubkey_fix.py
    - tests/test_scoring_consolidation.py
  modified:
    - qcscan/reports/writer.py

key-decisions:
  - "Removed assessment-TIMESTAMP.json output entirely — assessment layer is deprecated, no backward compat needed"
  - "Created compat wrapper dicts (score, conf) mapping intelligence schema to existing writer internals — avoids touching _scorecard_markdown and _roadmap_markdown"
  - "Kept _extract_cert_dates, _is_self_signed, _mtls_present helpers — used by upstream delta/diff logic"

patterns-established:
  - "Intelligence layer is the single scoring source: build_evidence_summary() -> compute_readiness_score()"
  - "All new scanner output modules must import from qcscan.intelligence.*, not qcscan.assessment.*"

requirements-completed: [CORE-01, CORE-02]

# Metrics
duration: 3min
completed: 2026-03-29
---

# Phase 01 Plan 01: Scoring Fixes Summary

**Consolidated writer.py onto single intelligence-layer scoring path and fixed cert_pubkey_alg field extraction bug — both were silent data quality blockers**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-29T19:00:48Z
- **Completed:** 2026-03-29T19:03:30Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Fixed `_extract_cert_key_type()` to check `cert_pubkey_alg` (canonical `CryptoEndpoint` field) first — previously it was never found because only legacy attribute names were probed
- Removed all `qcscan.assessment.*` imports from `writer.py` and replaced with `qcscan.intelligence.*` calls — scoring now flows through a single authoritative path
- Deleted 5 dead inline functions: `_normalize_evidence`, `_score_from_evidence`, `_confidence_from_evidence`, `_drivers_from_evidence`, `_roadmap_from_evidence` (net -219 lines)
- All 27 tests pass including 13 new tests covering both fixes

## Task Commits

1. **Task 1: Write failing tests (RED phase)** - `051b369` (test)
2. **Task 2: Fix writer.py — cert extraction + scoring consolidation** - `c4a7e68` (feat)

## Files Created/Modified

- `tests/test_cert_pubkey_fix.py` - Unit tests for _extract_cert_key_type checking cert_pubkey_alg first
- `tests/test_scoring_consolidation.py` - AST-based tests verifying writer.py import structure
- `qcscan/reports/writer.py` - Fixed extraction, consolidated imports, deleted dead code, removed legacy assessment block

## Decisions Made

- Removed `assessment-TIMESTAMP.json` output entirely — the assessment layer (v3.7) is deprecated and no backward compat is needed for internal tooling
- Created compat wrapper dicts mapping intelligence schema keys (`score`, `confidence_score`) to the existing internal keys (`total`, `confidence`) to avoid cascading changes in `_scorecard_markdown` and `_roadmap_markdown`
- Kept `_extract_cert_dates`, `_is_self_signed`, `_mtls_present` helper functions — checked for upstream usage, kept as still-valid delta/diff utilities

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Project venv had stale shebang path (`/Users/digs/Repos/` vs `/Volumes/Digs-1TB/`). Resolved by using `python -m pip` directly through venv Python binary. pytest installed successfully, all tests ran cleanly.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Intelligence layer is now the sole scoring path; Plans 02–04 can build on this without assessment layer concerns
- cert_pubkey_alg data will now flow correctly into scoring and reports once endpoints are scanned
- Deferred: `qcscan/reports/executive.py` and `qcscan/reports/technical.py` may still reference assessment layer — not touched in this plan (out of scope), tracked for future cleanup

---
*Phase: 01-foundation-fixes*
*Completed: 2026-03-29*
