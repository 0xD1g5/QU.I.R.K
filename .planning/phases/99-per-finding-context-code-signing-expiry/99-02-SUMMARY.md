---
phase: 99-per-finding-context-code-signing-expiry
plan: "02"
subsystem: engine/findings_evaluator + scanner/codesign_scanner
tags: [quantum-risk, per-finding-context, codesign-expiry, ctx-01, ctx-02, ctx-03, tdd]
requires: ["99-01"]
provides:
  - quantum_risk field on every finding (_build_finding chokepoint)
  - catalog-sourced remediation (D-04) replacing caller-supplied strings
  - conditional NIST_IR_8547_DEPRECATION (D-05 — catalog-miss only)
  - check_id param on _build_finding for codesign expiry classification
  - _classify_codesign_severity expiry branch (expired=HIGH, approaching=MEDIUM, stacking)
  - scan_codesign_from_tls_endpoints pseudo_parsed expiry fields (D-09)
  - evaluate_codesign_endpoints() — first-class codesign findings
  - run_scan.py wiring for codesign findings (CTX-03 crux)
  - D-06 confirmed: email/broker findings carry quantum_risk via _build_finding
affects:
  - quirk/engine/findings_evaluator.py
  - quirk/scanner/codesign_scanner.py
  - run_scan.py
  - tests/test_risk_engine.py
  - tests/test_codesign_expiry_classification.py
  - tests/test_codesign_findings_evaluator.py
tech-stack:
  added: []
  patterns:
    - _build_finding enrichment chokepoint (quantum_risk + catalog + conditional NIST)
    - evaluate_email/broker_endpoints pattern extended to evaluate_codesign_endpoints
    - _classify_codesign_severity independent expiry branch stacking with weak-crypto
    - D-09 pseudo_parsed expiry field injection for TLS path
key-files:
  modified:
    - quirk/engine/findings_evaluator.py (_build_finding, evaluate_codesign_endpoints)
    - quirk/scanner/codesign_scanner.py (_classify_codesign_severity, scan_codesign_from_tls_endpoints)
    - run_scan.py (import + call after broker findings block)
    - tests/test_risk_engine.py (Phase 99 assertions, D-05 boilerplate test update)
  created:
    - tests/test_codesign_expiry_classification.py
    - tests/test_codesign_findings_evaluator.py
decisions:
  - "catalog-wins (D-04): _build_finding replaces caller recommendation with REMEDIATION_CATALOG[crypto_class] when matched"
  - "NIST_IR_8547_DEPRECATION conditioned on catalog-miss only (D-05) — existing tests updated to reflect"
  - "quantum_risk excluded from _dedupe_findings key (same treatment as recommendation)"
  - "check_id stored in finding dict so _classify_finding can match codesign via CODESIGN_EXPIRY key"
  - "TLS path excludes not_after_dt from smime_scan_json (datetime not JSON-serializable); expired bool + reasons sufficient"
  - "D-06 confirmed via read: both evaluate_email_endpoints and evaluate_broker_endpoints route exclusively through _build_finding"
metrics:
  duration: "~35 minutes"
  completed: "2026-05-24"
  tasks_completed: 2
  files_modified: 4
  files_created: 2
requirements: [CTX-01, CTX-02, CTX-03]
---

# Phase 99 Plan 02: Finding Enrichment + Codesign Expiry — Implementation Summary

**One-liner:** `_build_finding` now injects catalog-sourced `quantum_risk` and weakness-specific remediation on every finding; `_classify_codesign_severity` gains an independent expiry branch; `evaluate_codesign_endpoints` turns CODE_SIGNING endpoints into first-class findings wired into run_scan.py.

## What Was Built

### Task 1: Enrich _build_finding (commits 329dc85 RED, 784f80a GREEN)

**`quirk/engine/findings_evaluator.py` — `_build_finding` changes:**

1. Added `from quirk.reports.content_model import ALGO_IMPACT_MAP, FALLBACK_QUANTUM_RISK, REMEDIATION_CATALOG, _classify_finding` import at module top.
2. Added optional `check_id: str = ""` parameter — stored in the returned dict so `_classify_finding` can match codesign expiry findings whose titles contain no RSA/SHA keyword.
3. After building the base dict, calls `_classify_finding` to map to a crypto class.
4. D-04 catalog-wins: when `crypto_class in REMEDIATION_CATALOG`, replaces the caller-supplied recommendation with `REMEDIATION_CATALOG[crypto_class]`.
5. D-05 conditional NIST: appends `NIST_IR_8547_DEPRECATION` ONLY when `quantum_vulnerable=True AND crypto_class not in REMEDIATION_CATALOG`.
6. D-02 quantum_risk: attaches `ALGO_IMPACT_MAP[crypto_class][2]` or `FALLBACK_QUANTUM_RISK`.
7. `_dedupe_findings` key tuple unchanged: `(host, port, title, recommendation)` — `quantum_risk` and `check_id` are NOT in the dedup key.

**`tests/test_risk_engine.py` updates:**
- Added imports for `ALGO_IMPACT_MAP`, `FALLBACK_QUANTUM_RISK`, `REMEDIATION_CATALOG`.
- Added 5 new Phase 99 assertions in `TestBuildFinding`: quantum_risk RSA match, fallback, catalog-wins recommendation, NIST-on-catalog-miss, check_id acceptance.
- Updated `test_returns_seven_key_dict` to expect `quantum_risk` and `check_id` keys (9 keys total).
- Updated `test_quantum_vulnerable_findings_cite_deprecation_and_fips` → `test_quantum_vulnerable_findings_cite_fips` (D-05: catalog-matched findings no longer carry NIST boilerplate, but all catalog entries include FIPS references inline).
- Updated `test_dedup_safety_for_quantum_findings` to assert dedup still works and recommendation equals `REMEDIATION_CATALOG["RSA"]` (not NIST boilerplate).
- Result: 41 tests pass.

### Task 2: Codesign Expiry + evaluate_codesign_endpoints (commits dbede7c RED, 18e338a GREEN)

**`quirk/scanner/codesign_scanner.py` changes:**

1. Added `timedelta` to datetime import.
2. `_classify_codesign_severity` — added independent expiry block after weak-crypto checks:
   - Reads `parsed.get("expired")` (bool) and `parsed.get("not_after_dt")` (datetime).
   - If expired → appends "expired".
   - elif not_after_dt present and `0 <= days_remaining <= 90` (UTC-normalized) → appends "approaching-expiry".
   - Return logic: expired or any weak-crypto reason → HIGH; approaching-expiry only → MEDIUM; nothing → (None, []).
3. `scan_codesign_from_tls_endpoints` — extended `pseudo_parsed` with `not_after_dt` (UTC-normalized) and `expired` (computed from comparison with now). `scan_dict` excludes `not_after_dt` (datetime not JSON-serializable).

**`quirk/engine/findings_evaluator.py` — new `evaluate_codesign_endpoints()`:**

Mirrors `evaluate_email_endpoints` structure. Three branches per endpoint:
- `"expired"` in reasons → HIGH `_build_finding(check_id="CODESIGN_EXPIRY", ...)` with verbatim UI-SPEC title/description. Catalog-wins D-04 automatically replaces fallback recommendation with `REMEDIATION_CATALOG["CODESIGN_EXPIRY"]`.
- `"approaching-expiry"` in reasons → MEDIUM `_build_finding(check_id="CODESIGN_APPROACHING_EXPIRY", ...)` with `{days_remaining}` interpolated in description.
- Other weak-crypto reasons → HIGH `_build_finding(quantum_vulnerable=True, ...)`.
- T-99-04 mitigated: malformed `smime_scan_json` catches exception, defaults `reasons=[]`, no crash.

**`run_scan.py` wiring:**
- Added `evaluate_codesign_endpoints` to import on line 37.
- Added call after broker findings block: `codesign_findings = evaluate_codesign_endpoints(codesign_endpoints)` with append pattern.

**D-06 confirmation (read-only verification):**
- `evaluate_email_endpoints` and `evaluate_broker_endpoints` confirmed to route ALL findings exclusively through `_build_finding` — no hand-rolled dict literals. No changes needed to these functions; Task 1's `_build_finding` enrichment automatically populates `quantum_risk` on those paths.
- Asserted in `tests/test_codesign_findings_evaluator.py` TestD06Coverage class.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated _classify_codesign_severity test for TLS path SAFE cert behavior**
- **Found during:** Task 2 GREEN — `test_no_expiry_safe_crypto_no_endpoint_emitted` expected len(results)==0 but TLS path always emits a CryptoEndpoint (severity=None for SAFE certs; evaluator skips severity=None)
- **Issue:** Test fixture mismatch with actual TLS path behavior (always emits endpoint regardless of severity — severity=None endpoints are filtered by evaluate_codesign_endpoints, not by the scanner)
- **Fix:** Updated test to assert `len(results)==1` and `results[0].severity is None`
- **Files modified:** `tests/test_codesign_expiry_classification.py`
- **Commit:** 18e338a

**2. [Rule 1 - Bug] Two existing test_risk_engine.py tests asserted NIST boilerplate on RSA/ECDSA findings**
- **Found during:** Task 1 GREEN — `test_quantum_vulnerable_findings_cite_deprecation_and_fips` and `test_dedup_safety_for_quantum_findings` asserted `NIST_IR_8547_DEPRECATION in recommendation` for RSA/ECDSA findings
- **Issue:** Post-D-05 implementation, catalog-matched findings replace recommendation with catalog entry (no NIST boilerplate). Tests captured the OLD unconditional behavior.
- **Fix:** Renamed boilerplate test to `test_quantum_vulnerable_findings_cite_fips` (FIPS references are in catalog entries); updated dedup test to assert `recommendation == REMEDIATION_CATALOG["RSA"]`
- **Files modified:** `tests/test_risk_engine.py`
- **Commit:** 784f80a

## D-06 Coverage Confirmation

Both `evaluate_email_endpoints` and `evaluate_broker_endpoints` route exclusively through `_build_finding` — confirmed by reading all finding construction sites in both functions. No hand-rolled dict literals found. Task 1's enrichment automatically covers these paths. Asserted in `test_codesign_findings_evaluator.py::TestD06Coverage`.

## Verification

- `python -m compileall quirk/ run_scan.py` — PASS (no errors)
- `python -m pytest tests/test_codesign_expiry_classification.py tests/test_codesign_findings_evaluator.py tests/test_risk_engine.py -x -q` — 68 passed
- `grep -c 'evaluate_codesign_endpoints' run_scan.py` → 2 (import + call)
- `grep -v '^#' quirk/scanner/codesign_scanner.py | grep -c 'approaching-expiry'` → 2
- Acceptance criteria one-liner: expired codesign finding `recommendation == REMEDIATION_CATALOG['CODESIGN_EXPIRY']` — PASS
- Full suite `python -m pytest tests/ -m "not slow" -q` — 35 pre-existing failures (version staleness, live-infra, skip-registry — confirmed pre-existing per project memory); 2113 passed

## Known Stubs

None — all copy is populated verbatim from 99-UI-SPEC.md locked strings. All `quantum_risk` and `recommendation` fields use catalog values.

## Threat Flags

None — Plan 99-02 modifies only finding construction logic and scanner classification. No new network endpoints, auth paths, or schema changes. T-99-03/T-99-04/T-99-05 mitigations applied as specified:
- T-99-04: `evaluate_codesign_endpoints` wraps `json.loads(smime_scan_json)` in try/except, defaults `reasons=[]`
- T-99-05: All datetime comparisons UTC-normalize before subtraction (both in `_classify_codesign_severity` and `scan_codesign_from_tls_endpoints`)
- T-99-SC: No package installs; zero new deps

## Self-Check: PASSED

- `quirk/engine/findings_evaluator.py` — exists and compiles; contains `def evaluate_codesign_endpoints` ✓
- `quirk/scanner/codesign_scanner.py` — exists and compiles; contains "approaching-expiry" ✓
- `run_scan.py` — contains `evaluate_codesign_endpoints` (import + call) ✓
- `tests/test_codesign_expiry_classification.py` — created; 12 tests pass ✓
- `tests/test_codesign_findings_evaluator.py` — created; 15 tests pass ✓
- `tests/test_risk_engine.py` — updated; 41 tests pass ✓
- Commits 329dc85, 784f80a, dbede7c, 18e338a — present in git log ✓
