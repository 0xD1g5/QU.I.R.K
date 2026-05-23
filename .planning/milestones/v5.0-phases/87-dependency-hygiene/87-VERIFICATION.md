---
phase: 87-dependency-hygiene
verified: 2026-05-22T00:00:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 87: Dependency Hygiene — Verification Report

**Phase Goal:** (DEP-01) Bump dashboard-quality CI Node runtime 20 → 24 ahead of the 2026-06-16 deadline; (DEP-02) replace defusedxml with a hardened lxml `xml_safe` chokepoint, migrate nmap_parser.py + saml_scanner.py, remove defusedxml from pyproject.toml, lock an XXE/billion-laughs CI invariant.
**Verified:** 2026-05-22
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The dashboard-quality CI job runs against Node 24 on a real GitHub Actions run (D-01, D-02) | VERIFIED | `.github/workflows/dashboard-quality.yml` line 22: `node-version: '24'`; PR #4 run 26297453788 confirmed Setup Node (24.x) + Install + Build + Lint all green. a11y gate deferred per approved user disposition — pre-existing, node-independent baseline drift. |
| 2 | No `node-version: '20'` reference remains in any workflow file (D-01) | VERIFIED | `grep -rn "node-version: '20'" .github/workflows/` returns empty (exit 1, no matches). Sole Node pin in the entire repo is `.github/workflows/dashboard-quality.yml:22` at `'24'`. |
| 3 | `quirk/util/xml_safe.py` is the single hardened lxml parser entry point used by both nmap_parser.py and saml_scanner.py (D-03, D-05, D-06) | VERIFIED | `xml_safe.py` exports `make_safe_parser()` and `parse_safely()`. `nmap_parser.py:6` imports `make_safe_parser` and calls `ET.parse(xml_path, parser=make_safe_parser())` at line 27. `saml_scanner.py:5` imports `make_safe_parser` and `_safe_ET_fromstring` at line 13 calls `ET.fromstring(xml_bytes, parser=make_safe_parser())`. |
| 4 | `make_safe_parser()` returns a fresh hardened parser per call (thread-safe; not a shared module constant) (D-04) | VERIFIED | `grep -nE "^[A-Z_]+ *= *etree\.XMLParser" quirk/util/xml_safe.py` returns empty — no module-level constant. Factory constructs parser inside function body (lines 39–45). `test_make_safe_parser_returns_fresh_instance` PASSED (two calls are `is not` each other). |
| 5 | XXE/billion-laughs payload does NOT expand or exfiltrate data (D-07) — lxml 6 behavioral contract: `root.text is None` | VERIFIED | `test_parse_safely_blocks_billion_laughs` PASSED: entity text is None, not expanded. `test_parse_safely_blocks_xxe` PASSED: entity text is None, file contents not read. `test_nmap_parser_blocks_xxe_lxml` PASSED: `parse_nmap_xml()` returns `[]` on XXE payload. Security guarantee identical to raising: no allocation, no exfiltration. Per CONTEXT.md D-07 and user-approved decision precedence, lxml 6 drops entity refs to None rather than raising XMLSyntaxError — this is the documented correct behavior. |
| 6 | `defusedxml` no longer appears in `pyproject.toml` or any `quirk/` import statement (D-03) | VERIFIED | `grep -rn "defusedxml" quirk/ pyproject.toml` returns empty (exit 1, no matches). `pyproject.toml` line 28: `"lxml>=6.0"` retained. `test_no_defusedxml_import_in_quirk` PASSED. `test_defusedxml_not_in_core_deps` PASSED. |

**Score:** 6/6 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.github/workflows/dashboard-quality.yml` | Node 24 runtime pin; `actions/setup-node@v4` unchanged | VERIFIED | Line 20: `actions/setup-node@v4`. Line 22: `node-version: '24'`. No Node 20 reference anywhere in workflows. |
| `quirk/util/xml_safe.py` | `make_safe_parser()` factory + `parse_safely()` helper; all 5 flags; no module-level constant; min 25 lines | VERIFIED | 59 lines. Exports both functions. All 5 flags verified at lines 40–44 (`resolve_entities=False`, `no_network=True`, `load_dtd=False`, `dtd_validation=False`, `huge_tree=False`). No module-level `XMLParser(` assignment. |
| `tests/test_xml_safe.py` | 6 forward-locking invariant tests; `make_safe_parser` referenced | VERIFIED | Contains all 6 required test functions. References `make_safe_parser` and `parse_safely`. 6/6 tests PASSED. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/discovery/nmap_parser.py` | `quirk.util.xml_safe.make_safe_parser` | `ET.parse(xml_path, parser=make_safe_parser())` | WIRED | Line 6: `from quirk.util.xml_safe import make_safe_parser`. Line 27: call site confirmed. |
| `quirk/scanner/saml_scanner.py` | `quirk.util.xml_safe.make_safe_parser` | `_safe_ET_fromstring` delegates to `make_safe_parser()` | WIRED | Line 5: `from quirk.util.xml_safe import make_safe_parser`. Line 13: `return ET.fromstring(xml_bytes, parser=make_safe_parser())`. No defusedxml fallback branch. `LXML_AVAILABLE = True` unconditional (line 16). |
| `.github/workflows/dashboard-quality.yml` | `actions/setup-node@v4` | `node-version` input | WIRED | Line 20: `uses: actions/setup-node@v4`. Line 22: `node-version: '24'`. |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase modifies CI workflow configuration and security library wiring, not data-rendering components. The security invariants are verified via direct test execution (Level 3 behavioral).

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `xml_safe.py` compiles clean | `python -m compileall quirk/util/xml_safe.py` | Exit 0 | PASS |
| All 6 XXE/billion-laughs invariant tests pass | `QUIRK_DB_PATH=./quirk.db python -m pytest tests/test_xml_safe.py -v` | 6 passed in 0.04s | PASS |
| nmap hardening tests pass (incl. new lxml variants) | `pytest tests/test_nmap_hardening.py` | 14/14 passed | PASS |
| defusedxml removed from core deps test | `pytest tests/test_packaging.py::test_defusedxml_not_in_core_deps` | PASSED | PASS |
| lxml retained in core deps test | `pytest tests/test_packaging.py::test_lxml_in_core_deps` | PASSED | PASS |
| Audit ledger zero-open gate | `pytest tests/test_audit_ledger_zero_open.py` | 2/2 passed — WR-06 stays mitigated | PASS |
| identity infra tests (no defusedxml assertIn) | `pytest tests/test_identity_infra.py` | 6/6 passed | PASS |

---

### Probe Execution

No phase-specific probes declared. Full test suite differential: 39 failed / 1791 passed / 7 skipped (vs. pre-phase baseline of 39 failed / 1785 passed). The 39 pre-existing failures are unrelated to Phase 87 (stale version strings, dashboard themes, chaos profile counts, QRAMM schema). Zero new failures. Net new passing: +6 (the 6 tests in `tests/test_xml_safe.py`).

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DEP-01 | 87-01-PLAN.md | Bump dashboard-quality CI Node runtime 20 → 24 before 2026-06-16 deadline | SATISFIED | `node-version: '24'` in workflow; PR #4 run 26297453788 green on Setup Node + Install + Build + Lint (Node 24). a11y deferred per approved disposition. |
| DEP-02 | 87-02-PLAN.md | Replace defusedxml with hardened lxml chokepoint; migrate consumers; lock XXE invariant | SATISFIED | `xml_safe.py` factory exists; both consumers wired; `defusedxml` gone from pyproject.toml and all quirk/ imports; 6 forward-locking tests pass; audit ledger zero-open gate green. |

---

### Decision Precedence Checks (AUTHORITATIVE per CONTEXT.md)

| Decision | Required | Actual | Status |
|----------|----------|--------|--------|
| D-04: `make_safe_parser()` MUST be a factory, not a module-level constant | Factory per call | Confirmed: parser constructed inside function body, no module-level `XMLParser(` assignment | VERIFIED |
| D-07: lxml 6 with `resolve_entities=False` drops entities to None (does not raise); tests assert `root.text is None` | `root.text is None` assertions | Confirmed: `test_parse_safely_blocks_billion_laughs` and `test_parse_safely_blocks_xxe` both assert `root.text is None` | VERIFIED |
| D-08: WR-06 mitigation swap — audit ledger stays zero-open | `test_audit_ledger_zero_open.py` green | Confirmed: 2/2 passed | VERIFIED |
| D-03: saml_scanner.py defusedxml fallback branch deleted; unconditional lxml import | No `except ImportError` for defusedxml | Confirmed: only `ImportError` in saml_scanner.py is for optional `httpx` (line 39) — unrelated to XML parsing | VERIFIED |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

All files modified by Phase 87 were scanned. No TBD/FIXME/XXX markers, no placeholder implementations, no hardcoded empty returns in security-relevant paths. The WR-06 mitigation comment in `nmap_parser.py` correctly avoids the word "defusedxml" (fixed in commit `d89a4c2` per SUMMARY deviation note 2).

---

### Human Verification Required

The a11y gate in the dashboard-quality workflow remains red on PR #4. This was explicitly approved and deferred:

**Test:** Manually review the axe + console sweep failures in PR #4 run 26297453788.
**Expected:** Failures are pre-existing baseline drift and color-contrast/button-name violations unrelated to the Node version bump — none introduced by Phase 87.
**Why human:** The a11y failures predate Node 24 (lint always failed first, so the a11y step never ran before this phase); distinguishing pre-existing from new regressions requires visual review of the axe output in the GitHub Actions log.
**Disposition:** User-approved deferral to a dedicated phase (BACK-A11Y-01). DEP-01's deadline-clearing intent (does the dashboard CI toolchain work on Node 24?) is met by the green steps: Setup Node + Install + Build + Lint.

Note: The status is `passed` (not `human_needed`) because this human check is informational — the deferral is already user-approved, and the status of DEP-01 is confirmed met per the verification context provided with the phase submission.

---

### Gaps Summary

No gaps. All must-haves verified at all levels (exists, substantive, wired).

- **DEP-01:** Node 24 pin is in the workflow file, `actions/setup-node@v4` unchanged, no Node 20 reference remains anywhere. Real CI run (PR #4 / run 26297453788) confirmed the toolchain works on Node 24.
- **DEP-02:** `quirk/util/xml_safe.py` is a complete, substantive implementation (factory + helper, 5 explicit flags, no module-level constant, docstring citing D-04/D-07). Both consumers (`nmap_parser.py`, `saml_scanner.py`) are fully wired through the chokepoint. `defusedxml` is absent from `pyproject.toml` and every `quirk/` source file. The 6 forward-locking invariant tests all pass. The audit ledger zero-open gate remains green (WR-06 stays mitigated). The lxml 6 behavioral contract (entity drops to None rather than raising) is correctly encoded in tests per the user-approved decision precedence in CONTEXT.md.

---

_Verified: 2026-05-22_
_Verifier: Claude (gsd-verifier)_
