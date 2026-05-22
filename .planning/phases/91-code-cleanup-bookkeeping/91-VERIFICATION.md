---
phase: 91-code-cleanup-bookkeeping
verified: 2026-05-22T00:00:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 91: Code Cleanup + Bookkeeping — Verification Report

**Phase Goal:** Dead code (BACK-49–57) removed with static-analysis confidence, deprecation warnings eliminated, Nyquist VALIDATION.md files current, JWT verify=False advisory documented — all with CI guards against regression.
**Verified:** 2026-05-22
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Deprecation-as-error pytest gate passes on tests/test_dashboard_scan_history.py | ✓ VERIFIED | `python -W error::DeprecationWarning -m pytest tests/test_dashboard_scan_history.py -q` → 5 failed / 4 passed; zero DeprecationWarning errors raised. The 5 failures are pre-existing assertion errors (compare endpoint returning 400 vs 200, predating this phase). No `utcnow` occurrences remain in the file (grep count = 0). |
| 2 | Test suite collects with 0 errors without QUIRK_DB_PATH set | ✓ VERIFIED | `python -m pytest tests/ --collect-only -q` → grep for "Multiple QU.I.R.K. DBs found" = 0. conftest.py sets `os.environ["QUIRK_DB_PATH"]` at module import time (collection-time fix) plus an autouse `_isolate_quirk_db` fixture per test. |
| 3 | No v3.x version string is printed to stdout by operator_context.py | ✓ VERIFIED | `grep -n 'v3\.5\.1' quirk/assessment/operator_context.py` → empty. print() at line 33 reads `"\n🧠 Assessment Context"` with no version suffix. |
| 4 | VALIDATION.md frontmatter for phases 87/88/89 reads nyquist_compliant: true; a 90-VALIDATION.md exists | ✓ VERIFIED | All four files confirmed: 87-VALIDATION.md `nyquist_compliant: true`, 88-VALIDATION.md `nyquist_compliant: true`, 89-VALIDATION.md `nyquist_compliant: true`, 90-VALIDATION.md exists with `nyquist_compliant: true`. `tests/test_infra03_nyquist_coverage.py` → 18/18 passed. |
| 5 | Stale CONCERNS.md entries describing deleted files / dual-engine are removed or marked resolved | ✓ VERIFIED | All dual-engine sections (§4.1–§4.4) carry `**Resolved:**` annotations. All deleted-file sections (§1.1, §1.2, §1.3, §1.4, §1.5, §1.6, §1.7, §1.8, §6.1, §6.2) carry `**Resolved:**` annotations. 22 total resolved markers confirmed. No live dual-engine claim remains. |
| 6 | JWT verify=False inspection-mode is documented in both jwt_scanner.py (inline) and docs/operators-guide.md | ✓ VERIFIED | `grep -n 'WHY:' quirk/scanner/jwt_scanner.py` → matches at lines 73 and 98 (both httpx.get call sites). `grep -n 'allow_insecure_jwks' docs/operators-guide.md` → lines 207–220 with full security note. `grep -n 'allow_insecure_jwks' docs/configuration.md` → line 233 with config table entry. |
| 7 | _extract_cert_key_type removed from writer.py; test_cert_pubkey_fix.py deleted; 5 intelligence dataclasses PRESERVED per D-15 | ✓ VERIFIED | `grep -n '_extract_cert_key_type\|RichText' quirk/reports/writer.py` → empty. `test -f tests/test_cert_pubkey_fix.py` → DELETED. `quirk/intelligence/schema.py` preserved with all 5 dataclasses (ScoreInputs, ScoreResult, ConfidenceResult, RoadmapItem, IntelligenceReport). `tests/test_intelligence_public_api.py` and `tests/test_intelligence_schema.py` preserved. `python -c "import quirk.intelligence; import quirk.reports.writer"` → IMPORT_OK. |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/conftest.py` | Autouse QUIRK_DB_PATH=tmp_path isolation fixture | ✓ VERIFIED | Contains `os.environ["QUIRK_DB_PATH"]` at module import + `_isolate_quirk_db` autouse fixture with `monkeypatch.setenv("QUIRK_DB_PATH", ...)`. CLEAN-03 docstring present. |
| `.planning/phases/90-oqs-nginx-pqc-hybrid/90-VALIDATION.md` | Phase 90 Nyquist validation contract | ✓ VERIFIED | File exists; frontmatter contains `nyquist_compliant: true`, `wave_0_complete: true`, `status: complete`. |
| `docs/operators-guide.md` | JWT allow_insecure_jwks security note | ✓ VERIFIED | Lines 207–220 document `allow_insecure_jwks` with security context, operator guidance, and cross-reference to configuration.md. |
| `docs/dead-code-candidates.md` | Reviewed dead-code backlog (D-02b), no deletions | ✓ VERIFIED | File exists; references vulture 2.16; declares "REVIEWED BACKLOG — for future per-item review only"; explicitly states "This file is a reviewed catalogue, NOT an action list." |
| `quirk/intelligence/__init__.py` | Package re-exports consistent with preserved schema | ✓ VERIFIED | `import quirk.intelligence` succeeds; `IntelligenceReport` present in public API; `SCHEMA_VERSION` exported. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/conftest.py` | `quirk/dashboard/api/deps.py _default_db_path()` | `monkeypatch.setenv(QUIRK_DB_PATH)` sidesteps ambient resolver | ✓ WIRED | `grep 'monkeypatch.*setenv.*QUIRK_DB_PATH'` → line 35 confirms; collection-time `os.environ` set at lines 20–22 also confirmed. |
| `quirk/scanner/jwt_scanner.py httpx.get` | `docs/operators-guide.md security note` | `verify=verify_tls` / `allow_insecure_jwks` documented in both surfaces | ✓ WIRED | `# WHY:` advisory at both httpx.get call sites (lines 73 and 98); `allow_insecure_jwks` security note in operators-guide.md (lines 207–220) and configuration.md (line 233). |
| `quirk/reports/writer.py` | `quirk/cbom/builder.py` | `builder reads ep.cert_pubkey_alg directly; does NOT call _extract_cert_key_type` | ✓ WIRED | `_extract_cert_key_type` fully absent from writer.py; `cert_pubkey_alg` direct-access pattern confirmed by successful `import quirk.reports.writer`. |

---

### Data-Flow Trace (Level 4)

Not applicable — phase is source cleanup, documentation, and bookkeeping only. No new data-rendering components introduced.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Deprecation gate: no DeprecationWarning in test_dashboard_scan_history.py | `python -W error::DeprecationWarning -m pytest tests/test_dashboard_scan_history.py -q` | 5 failed (pre-existing assertions), 4 passed; zero DeprecationWarning errors | ✓ PASS |
| Collection errors: 0 without QUIRK_DB_PATH | `python -m pytest tests/ --collect-only -q` (no env var) | grep "Multiple QU.I.R.K. DBs found" = 0 | ✓ PASS |
| Imports clean after deletions | `python -c "import quirk.intelligence; import quirk.reports.writer"` | IMPORT_OK | ✓ PASS |
| Nyquist coverage test | `python -m pytest tests/test_infra03_nyquist_coverage.py -q` | 18/18 passed | ✓ PASS |
| compileall clean | `python -m compileall quirk tests -q` | No output (clean) | ✓ PASS |
| Full suite regression gate | `QUIRK_DB_PATH=/tmp/quirk91.db python -m pytest tests/ -q` | 44 failed / 1876 passed / 7 skipped — matches pre-plan baseline (delta = 6 test cases deleted from test_cert_pubkey_fix.py) | ✓ PASS |

---

### Probe Execution

No probes declared in PLAN files. Behavioral spot-checks above serve as the equivalent confirmation.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CLEAN-01 | 91-01 | datetime.utcnow deprecation + stale comments (BACK-55, BACK-56) | ✓ SATISFIED | 0 utcnow occurrences in test_dashboard_scan_history.py; deprecation gate passes; v3.5.1 absent from operator_context.py; v3.x/v4.x era comments stripped from models.py, db.py, tls_scanner.py, fingerprint.py, findings_evaluator.py. Commits 67786fe confirmed in git log. |
| CLEAN-02 | 91-02 | Tier-B dead-code removal (BACK-49/50/51/52/54); vulture D-02b catalogue | ✓ SATISFIED | `_extract_cert_key_type` + `RichText` deleted from writer.py; test_cert_pubkey_fix.py deleted; BACK-52 schema portion recorded superseded-by-D-15 (option-a, IntelligenceReport preserved per Phase 77 D-15 CI gate); docs/dead-code-candidates.md created as report-only catalogue. Commits d027474, 6fd5f98 confirmed. |
| CLEAN-03 | 91-01 | Nyquist VALIDATION.md currency + conftest DB isolation + stale CONCERNS.md (BACK-62) | ✓ SATISFIED | 87/88/89/90-VALIDATION.md all have `nyquist_compliant: true`; conftest.py autouse fixture eliminates 7 collection errors; CONCERNS.md dual-engine sections annotated Resolved. Commits 7ea806a, 89e8063 confirmed. |
| CLEAN-04 | 91-01 | JWT verify=False inspection-mode advisory (BACK-58) | ✓ SATISFIED | `# WHY:` comments at both httpx.get call sites in jwt_scanner.py; `allow_insecure_jwks` security note in docs/operators-guide.md AND docs/configuration.md. Commit 89e8063 confirmed. |

---

### Anti-Patterns Found

| File | Pattern | Severity | Notes |
|------|---------|----------|-------|
| `.planning/phases/91-code-cleanup-bookkeeping/91-VALIDATION.md` | `nyquist_compliant: false`, `status: draft`, `wave_0_complete: false` | ℹ Info | The phase's own validation strategy document was never updated to `status: complete` after all plans shipped. This is bookkeeping-only (the Nyquist test does not read this file's frontmatter; it tests scanner behavior). The plan's explicit scope was "v5.0 phases 87-90 ONLY". Not a blocker. |

No `TBD`, `FIXME`, or `XXX` markers found in files modified by this phase.

---

### Human Verification Required

None — all must-haves are verifiable programmatically. The pre-existing 5 assertion failures in test_dashboard_scan_history.py and 44 total suite failures are all pre-existing (CBOM compose-profile drift, stale v4.1/v4.2 version-string assertions, dashboard themes, qramm — DB-independent, identical count pre-phase). No new failures introduced by this phase.

---

## Gaps Summary

No gaps. All four CLEAN requirements are satisfied in the codebase. The preservation of the 5 intelligence schema dataclasses (option-a, Phase 77 D-15 honored) is correct per the user decision — this is not a gap against CLEAN-02, which explicitly records BACK-52 schema portion as superseded-by-D-15 in both REQUIREMENTS.md and CONCERNS.md.

The only informational note is that `91-VALIDATION.md` (the phase's own strategy document) still carries `nyquist_compliant: false / status: draft` in its frontmatter — plan scope covered phases 87-90 only. This does not affect the Nyquist CI test, which tests scanner behavior, not file frontmatter. It is cosmetic bookkeeping that could be updated at any time.

---

_Verified: 2026-05-22T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
