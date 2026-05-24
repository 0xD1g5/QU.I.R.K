---
phase: 99-per-finding-context-code-signing-expiry
verified: 2026-05-24T00:00:00Z
status: human_needed
score: 3/3 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open the HTML report in a browser and confirm each finding block shows a 'Quantum Risk' column (All Findings table) and a '.quantum-risk-block' inside Top Findings cells, with non-empty per-finding text"
    expected: "Every finding in the HTML report displays a distinct quantum-risk sentence; no finding renders a blank Quantum Risk cell; Top Findings Description cell shows the risk label + sentence block"
    why_human: "HTML visual render requires a browser; automated tests confirm the template has the correct structure and data but cannot verify final browser rendering"
  - test: "Export the report to PDF and open it — confirm each finding carries the Quantum Risk text alongside the remediation, and the text is not truncated or overflowing"
    expected: "PDF findings section shows Quantum Risk per row (or per block); text is readable; no cell overflow"
    why_human: "PDF rendering requires a running server + Playwright; the template is verified correct but visual PDF output must be human-confirmed (consistent with Phase 98 deferrals)"
---

# Phase 99: Per-Finding Context + Code-Signing Expiry — Verification Report

**Phase Goal:** Every finding in the report carries a quantum-risk explanation and actionable remediation guidance, turning the finding list into an advisory document; code-signing certificate expiry is surfaced as a first-class finding.
**Verified:** 2026-05-24
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Each finding row/block displays a plain-language "so what" explanation (CISO understands PQ risk without lookups) | ✓ VERIFIED | `quantum_risk` field injected by `_build_finding` via `ALGO_IMPACT_MAP[crypto_class][2]`; fallback to `FALLBACK_QUANTUM_RISK` when no crypto-class match; `technical.py` adds "Quantum Risk" column between Description and Recommendation; `report.html.j2` adds `<th>Quantum Risk</th>` (All Findings) + `.quantum-risk-block` div (Top Findings); all 85 Phase-99 tests pass |
| 2 | Each finding carries actionable remediation specific to the detected weakness (not generic PQC boilerplate) | ✓ VERIFIED | `REMEDIATION_CATALOG` exists with same key set as `ALGO_IMPACT_MAP`; `_build_finding` applies `REMEDIATION_CATALOG[crypto_class]` on catalog hit and drops `NIST_IR_8547_DEPRECATION`; boilerplate retained only on catalog miss; confirmed via inline Python probe: RSA finding `recommendation` starts with "Replace RSA keys with NIST PQC standard algorithms: ML-KEM" and does NOT contain the NIST IR 8547 appendage |
| 3 | A code-signing cert that is expired or approaching expiry appears as a finding with severity-appropriate classification | ✓ VERIFIED | `_classify_codesign_severity` fires an independent expiry branch: `expired=True` → `("HIGH", ["expired"])`; `not_after_dt` within 90 days → `("MEDIUM", ["approaching-expiry"])`; SAFE-crypto-but-expired cert returns `HIGH` (no longer silently dropped); both LDAP path (`_parse_codesign_cert` sets `not_after_dt` + `expired`) and TLS path (`pseudo_parsed` includes `not_after_dt` + `expired` at D-09 lines 463–484) produce severity; `evaluate_codesign_endpoints()` in `findings_evaluator.py` turns these into finding dicts; `run_scan.py` imports and calls it at L37 + L2127–2129 |

**Score:** 3/3 truths verified

---

### Additional D-06 and Oracle Checks

| Check | Status | Evidence |
|-------|--------|----------|
| D-06: email-path findings carry `quantum_risk` | ✓ VERIFIED | `evaluate_email_endpoints` routes all findings through `_build_finding`; probe with KAFKA-PLAIN email endpoint confirms non-empty `quantum_risk` |
| D-06: broker-path findings carry `quantum_risk` | ✓ VERIFIED | `evaluate_broker_endpoints` routes all findings through `_build_finding`; probe with KAFKA-PLAIN broker endpoint confirms non-empty `quantum_risk` |
| Chaos-lab oracle `expected_results_v4.md` documents codesign expiry paths | ✓ VERIFIED | `grep -ic 'expiry'` returns 18 in the oracle file; ldaps/CODE-SIGN section updated for both LDAP and TLS-EKU paths |
| REQUIREMENTS.md CTX rows marked complete | ✗ NOT UPDATED | CTX-01/02/03 remain `[ ]` and `Pending` in REQUIREMENTS.md — recurring executor gap (noted in project memory: "executors leave REQUIREMENTS.md rows pending"). Code is complete; tracking file is stale. |

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/reports/content_model.py` | 3-tuple ALGO_IMPACT_MAP, REMEDIATION_CATALOG, codesign keys, exports | ✓ VERIFIED | All entries are 3-tuples; `REMEDIATION_CATALOG` key set == `ALGO_IMPACT_MAP` key set; `CODESIGN_EXPIRY` + `CODESIGN_APPROACHING_EXPIRY` present in both; `_classify_finding` exported; `FALLBACK_QUANTUM_RISK` exported |
| `quirk/engine/findings_evaluator.py` | `_build_finding` quantum_risk injection + conditional NIST + `evaluate_codesign_endpoints()` | ✓ VERIFIED | `def evaluate_codesign_endpoints` at L968; `_build_finding` sets `finding["quantum_risk"]`; catalog-wins and conditional NIST confirmed by probe |
| `quirk/scanner/codesign_scanner.py` | `_classify_codesign_severity` expiry branch + TLS `pseudo_parsed` expiry fields | ✓ VERIFIED | Lines 176–198 contain independent expiry block; `pseudo_parsed` at L476–483 includes `not_after_dt` and `expired`; `approaching-expiry` string present |
| `run_scan.py` | `evaluate_codesign_endpoints` import + call | ✓ VERIFIED | L37: imported in function-evaluator import line; L2127–2129: `codesign_findings = evaluate_codesign_endpoints(codesign_endpoints)` + append |
| `quirk/reports/technical.py` | Quantum Risk markdown column | ✓ VERIFIED | L120: `"| Severity | Host | Port | Title | Description | Quantum Risk | Recommendation |"`; L129: fallback applied |
| `quirk/reports/templates/report.html.j2` | Quantum Risk column (All Findings) + `.quantum-risk-block` (Top Findings) + CSS | ✓ VERIFIED | 2 occurrences of `quantum-risk-block`; 3 lines with `quantum_risk` + `sanitize`; CSS rules present |
| `tests/test_content_model_phase99.py` | Unit coverage for catalog parity + quantum_risk sentence | ✓ VERIFIED | File exists; 85 tests pass (combined suite) |
| `tests/test_codesign_expiry_classification.py` | Expiry classification tests (both paths, stacking) | ✓ VERIFIED | File exists; all pass |
| `tests/test_codesign_findings_evaluator.py` | evaluate_codesign_endpoints + D-04 catalog-wins + D-06 email/broker | ✓ VERIFIED | File exists; all pass |
| `tests/test_quantum_risk_render_parity.py` | Render-parity gate (markdown + HTML) | ✓ VERIFIED | File exists; all pass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `run_scan.py` | `evaluate_codesign_endpoints` | import at L37 + call at L2127 | ✓ WIRED | Confirmed by grep; `codesign_endpoints` (already assembled) passed directly |
| `quirk/engine/findings_evaluator.py:_build_finding` | `quirk.reports.content_model` | `from quirk.reports.content_model import ALGO_IMPACT_MAP, REMEDIATION_CATALOG, FALLBACK_QUANTUM_RISK, _classify_finding` | ✓ WIRED | Import present; `_classify_finding(finding)` called inside `_build_finding` |
| `quirk/reports/templates/report.html.j2` | `quantum_risk` field | `{{ f.get('quantum_risk', ...) | sanitize }}` | ✓ WIRED | 3 lines combine `quantum_risk` access with `sanitize` filter; XSS mitigated |
| `quirk/reports/technical.py` | `quantum_risk` field | `f.get("quantum_risk") or FALLBACK_QR` | ✓ WIRED | Column present; `md_cell(qr)` escapes pipe/markdown specials |
| `_classify_codesign_severity` LDAP path | expiry fields in parsed dict | `_parse_codesign_cert` sets `not_after_dt` + `expired` | ✓ WIRED | `_parse_codesign_cert` L134–135 confirmed |
| `_classify_codesign_severity` TLS path | expiry fields in pseudo_parsed | `pseudo_parsed` constructed at L476–483 in `scan_codesign_from_tls_endpoints` | ✓ WIRED | D-09 lines confirmed in source |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `technical.py` markdown table | `f.get("quantum_risk")` | `_build_finding` → `ALGO_IMPACT_MAP[crypto_class][2]` | Yes — static catalog keyed by detected crypto class | ✓ FLOWING |
| `report.html.j2` All Findings | `f.get('quantum_risk', ...)` | Same `_build_finding` enrichment | Yes — same catalog | ✓ FLOWING |
| `report.html.j2` Top Findings | `.quantum-risk-block` div | Same finding dict | Yes | ✓ FLOWING |
| `evaluate_codesign_endpoints` → finding dict | `recommendation` | `REMEDIATION_CATALOG["CODESIGN_EXPIRY"]` via `_build_finding` catalog-wins | Yes — catalog value confirmed by probe | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `_build_finding` produces `quantum_risk` for RSA finding | `python -c "from quirk.engine.findings_evaluator import _build_finding; ..."` | `quantum_risk` = "RSA key material is vulnerable to Shor's algorithm..."; NIST boilerplate absent | ✓ PASS |
| `_build_finding` applies fallback for unknown finding | Same probe, title="Unknown finding xyz" | `quantum_risk` = `FALLBACK_QUANTUM_RISK` value | ✓ PASS |
| `evaluate_codesign_endpoints` expired cert → catalog-wins recommendation | Inline Python probe with `expired=True` endpoint | `recommendation == REMEDIATION_CATALOG["CODESIGN_EXPIRY"]` | ✓ PASS |
| `_classify_codesign_severity` SAFE-crypto-but-expired → HIGH | `_classify_codesign_severity({'expired': True, 'not_after_dt': ..., key_bits=4096, ...})` | `("HIGH", ["expired"])` | ✓ PASS |
| `_classify_codesign_severity` approaching ≤90d → MEDIUM | Same function, `expired=False`, `not_after_dt` 45 days out | `("MEDIUM", ["approaching-expiry"])` | ✓ PASS |
| Email-path finding carries `quantum_risk` | `evaluate_email_endpoints([AES256-SHA endpoint])` | Non-empty `quantum_risk` | ✓ PASS |
| Broker-path finding carries `quantum_risk` | `evaluate_broker_endpoints([KAFKA-PLAIN endpoint])` | Non-empty `quantum_risk` | ✓ PASS |
| All Phase-99 tests | `python -m pytest tests/test_content_model_phase99.py tests/test_exec_content_model.py tests/test_codesign_expiry_classification.py tests/test_codesign_findings_evaluator.py tests/test_risk_engine.py tests/test_quantum_risk_render_parity.py -q` | **85 passed in 0.32s** | ✓ PASS |
| `python -m compileall quirk/ run_scan.py` | Full compile | No errors | ✓ PASS |

---

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|---------|
| CTX-01 | Each finding carries a plain-language quantum-risk "so what" explanation | ✓ SATISFIED | `quantum_risk` field on every `_build_finding` output; rendered in all 3 surfaces; 85 tests pass |
| CTX-02 | Each finding carries actionable remediation guidance specific to the detected weakness | ✓ SATISFIED | `REMEDIATION_CATALOG` with per-crypto-class strings; catalog-wins over boilerplate; NIST dropped on catalog hit |
| CTX-03 | Code-signing cert expiry surfaced as a finding [WR-05] | ✓ SATISFIED | `_classify_codesign_severity` expiry branch; SAFE-expired emits finding; `evaluate_codesign_endpoints` wired into `run_scan.py`; both LDAP + TLS paths confirmed |

**Note:** REQUIREMENTS.md tracking rows remain `[ ] Pending` (not flipped to `[x]`) — recurring executor gap. Does not affect code correctness.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `.planning/REQUIREMENTS.md` | CTX-01/02/03 rows still `[ ]` and `Pending` | ℹ️ Info | Documentation staleness only; recurring executor gap per project memory; no code impact |

No `TBD`, `FIXME`, `XXX`, or unimplemented stubs found in Phase 99 modified files.

---

### Human Verification Required

#### 1. HTML Quantum Risk Column — Browser Visual Confirm

**Test:** Run a scan against any target, open the HTML report in a browser, inspect the "All Findings" section and the "Top Findings" section.
**Expected:** All Findings table has a "Quantum Risk" column with non-empty text per finding row. Top Findings Description cells contain a distinct risk block (styled with `.quantum-risk-block`). No finding renders a blank Quantum Risk cell (fallback string appears for any finding without a crypto-class match).
**Why human:** HTML visual render requires a browser. Automated tests confirm the template has correct structure and data injection, but final browser rendering — column layout, CSS display, no broken HTML — requires human inspection.

#### 2. PDF Quantum Risk Rendering — Visual Confirm

**Test:** Export the report to PDF (via `quirk report --format pdf` or equivalent), open in a PDF viewer.
**Expected:** Each finding in the PDF shows the Quantum Risk text alongside the remediation. Text is readable and not truncated, overflowed, or absent.
**Why human:** PDF rendering uses Playwright against a running server — environment-gated. The template is verified correct at the HTML level (PDF inherits HTML); PDF visual output must be confirmed by a human (consistent with Phase 98 deferrals documented in VALIDATION.md).

---

### Gaps Summary

No blocking gaps. All three success criteria are implemented and verified in code. Two items are deferred to human verification:
1. HTML browser visual rendering of the Quantum Risk column and block.
2. PDF visual rendering of Quantum Risk per finding.

The REQUIREMENTS.md tracking rows not being flipped to `[x]` is a documentation gap, not a code gap.

---

_Verified: 2026-05-24_
_Verifier: Claude (gsd-verifier)_
