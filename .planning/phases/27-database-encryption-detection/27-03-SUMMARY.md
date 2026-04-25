---
phase: 27-database-encryption-detection
plan: "03"
subsystem: intelligence
tags: [tdd, green-implementation, dar-scoring, evidence, scoring]
dependency_graph:
  requires:
    - "27-01: RED scaffold (test_dar_db_counters stub, test_compute_readiness_score_shape updated)"
  provides:
    - "dar_db_plaintext_count / dar_db_weak_ssl_count counters in evidence.py"
    - "dar_db_plaintext_ratio / dar_db_weak_ssl_ratio in evidence summary dict"
    - "dar_ as 5th subscore prefix in scoring.py (data_at_rest subscore)"
    - "POSTGRESQL and MYSQL branches in evidence endpoint loop"
    - "dar_ key in all three PROFILE_MULTIPLIERS profiles"
    - "SCORE_WEIGHTS entries for dar_db_plaintext_ratio (12.0) and dar_db_weak_ssl_ratio (6.0)"
  affects:
    - "quirk/intelligence/evidence.py build_evidence_summary return dict (4 new keys)"
    - "quirk/intelligence/scoring.py compute_readiness_score total_score and subscores"
    - "test_intelligence_evidence.py test_dar_db_counters (GREEN)"
    - "test_intelligence_scoring.py test_compute_readiness_score_shape (GREEN)"
tech_stack:
  added: []
  patterns:
    - "Optional findings parameter with None default for backward-compatible test call"
    - "dar_ subscore parallel to identity_ — 5th prefix in SCORE_WEIGHTS and PROFILE_MULTIPLIERS"
    - "POSTGRESQL insufficient-privilege guard (T-27-03-2 mitigated)"
key_files:
  created: []
  modified:
    - quirk/intelligence/evidence.py
    - quirk/intelligence/scoring.py
decisions:
  - "findings parameter made Optional[Iterable] with None default — test_dar_db_counters calls build_evidence_summary([]) with one arg; making findings optional is the correct fix (Rule 2 — missing critical functionality for test compatibility)"
  - "dar_ SCORE_WEIGHTS placed before agility_ entries to keep subscore groups contiguous"
  - "scan_error guard in POSTGRESQL branch uses getattr(ep, 'scan_error', None) == 'insufficient-privilege' — exact string match, not substring, for precise privilege-gap detection"
metrics:
  duration: "187 seconds"
  completed: "2026-04-25"
  tasks: 2
  files: 2
---

# Phase 27 Plan 03: dar_ Scoring Infrastructure — evidence.py and scoring.py

TDD GREEN wave: dar_ DB evidence counters in evidence.py and dar_ as 5th subscore prefix in scoring.py; turns test_dar_db_counters and test_compute_readiness_score_shape GREEN.

## What Was Built

### Task 1: evidence.py — dar_ DB counters (commit a24d759)

- **_PROTOCOL_KEYS** extended with `"POSTGRESQL"`, `"MYSQL"`, `"RDS"` — protocol counting now includes DB protocols
- **findings parameter** made `Optional` with `None` default — `build_evidence_summary([])` is now valid; existing callers with explicit `findings` argument are unaffected
- **Counter declarations** — `dar_db_plaintext_count = 0` and `dar_db_weak_ssl_count = 0` added after `dnssec_weak_algo_count`
- **POSTGRESQL branch** — `elif proto == "POSTGRESQL":` increments `dar_db_plaintext_count` when `service_detail` contains `"ssl-off"`, skips `scan_error == "insufficient-privilege"` (T-27-03-2 mitigated)
- **MYSQL branch** — `elif proto == "MYSQL":` increments `dar_db_plaintext_count` on `"ssl-off"`, `dar_db_weak_ssl_count` on `"-weak"` in service_detail
- **Return dict** — 4 new keys appended: `dar_db_plaintext_count`, `dar_db_weak_ssl_count`, `dar_db_plaintext_ratio`, `dar_db_weak_ssl_ratio`

### Task 2: scoring.py — dar_ as 5th subscore (commit 9cdb22f)

- **SCORE_WEIGHTS** — `"dar_db_plaintext_ratio": 12.0` and `"dar_db_weak_ssl_ratio": 6.0` added after identity_ entries
- **PROFILE_MULTIPLIERS** — `"dar_": 1.4 / 1.0 / 0.7` added to strict/balanced/lenient profiles respectively (T-27-03-3 mitigated)
- **Evidence extraction** — `dar_db_plaintext` and `dar_db_weak_ssl` extracted from evidence dict with `max(0, _as_int(...))` guards
- **dar_impacts block** — two negative impacts: database plaintext connections and database weak SSL configuration, producing `dar_score` and `dar_drivers`
- **total_score** — updated to 5-addend sum: `hygiene + modern_tls + identity_trust + agility + dar_score` (max now 125)
- **subscores dict** — `"data_at_rest": dar_score` added as 5th key
- **all_drivers** — `+ dar_drivers` appended to driver chain

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Made findings parameter optional in build_evidence_summary**

- **Found during:** Task 1 RED baseline check
- **Issue:** `test_dar_db_counters` calls `build_evidence_summary([])` with a single positional argument. The existing function signature requires two positional arguments (`endpoints`, `findings`), causing `TypeError: missing 1 required positional argument: 'findings'` — the test was failing for the wrong reason (TypeError instead of AssertionError for missing keys)
- **Fix:** Changed `findings: Iterable[Mapping[str, Any]]` to `findings: Optional[Iterable[Mapping[str, Any]]] = None`; added `finding_list = list(findings) if findings is not None else []`
- **Files modified:** `quirk/intelligence/evidence.py`
- **Commit:** a24d759
- **Impact:** Backward-compatible — all existing callers pass findings explicitly and are unaffected; adds convenience for no-findings evidence queries

## Known Stubs

None — all dar_ counters are fully wired to protocol branches and return dict. No placeholder values.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. Evidence counters consume existing `service_detail` string fields already present on `CryptoEndpoint` objects — no new trust boundary crossings. The `insufficient-privilege` guard (T-27-03-2) is correctly implemented as an exact-string `scan_error` check, preventing false positive plaintext-count inflation.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| quirk/intelligence/evidence.py contains `dar_db_plaintext_count = 0` | FOUND (line 78) |
| quirk/intelligence/evidence.py contains `elif proto == "POSTGRESQL":` | FOUND (line 145) |
| quirk/intelligence/evidence.py contains `elif proto == "MYSQL":` | FOUND (line 153) |
| quirk/intelligence/evidence.py contains `"dar_db_plaintext_count": dar_db_plaintext_count` | FOUND (line 210) |
| quirk/intelligence/scoring.py contains `"dar_db_plaintext_ratio": 12.0` | FOUND (line 19) |
| quirk/intelligence/scoring.py contains `"dar_": 1.4` in strict profile | FOUND (line 28) |
| quirk/intelligence/scoring.py contains `dar_score, dar_drivers = _apply_weighted_impacts` | FOUND (line 172) |
| quirk/intelligence/scoring.py contains `"data_at_rest": dar_score` | FOUND (line 191) |
| quirk/intelligence/scoring.py total_score contains `+ dar_score` | FOUND (line 174) |
| test_intelligence_evidence.py test_dar_db_counters GREEN | PASSED |
| test_intelligence_scoring.py all 8 tests GREEN | PASSED |
| commit a24d759 (Task 1) | FOUND |
| commit 9cdb22f (Task 2) | FOUND |
