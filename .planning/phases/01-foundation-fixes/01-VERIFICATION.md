---
phase: 01-foundation-fixes
verified: 2026-03-29T20:00:00Z
status: passed
score: 6/6 must-haves verified
re_verification: false
---

# Phase 01: Foundation Fixes Verification Report

**Phase Goal:** Fix what is broken, make the codebase correct and consistent, rename to QU.I.R.K., and replace the banner-only SSH scanner and basic TLS scanner with deep-enumeration implementations (ssh-audit and sslyze). No new scan surfaces, no CBOM, no UI.
**Verified:** 2026-03-29T20:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Single scoring path through intelligence/scoring.py — no assessment/readiness_score imports in writer.py | VERIFIED | `quirk/reports/writer.py` line 12: `from quirk.intelligence.scoring import compute_readiness_score`; no `assessment.readiness_score` import present (AST-verified) |
| 2 | `cert_pubkey_alg` is the first probe in `_extract_cert_key_type()` | VERIFIED | `quirk/reports/writer.py` lines 37–38: `getattr(ep, "cert_pubkey_alg", None)` is first; fallback loop follows at line 42. Runtime spot-check confirmed correct return |
| 3 | Package renamed qcscan → quirk; zero remaining `qcscan` or `QuRisk` references in .py files | VERIFIED | `qcscan/` directory gone; `quirk/` exists; `python -c "import quirk; print(quirk.__version__)"` prints `3.9.0`; grep of live codebase (excluding `.claude/worktrees`) returns 0 matches |
| 4 | SSH scanner uses ThreadPoolExecutor (not sequential) and stores `ssh_audit_json` | VERIFIED | `quirk/scanner/ssh_scanner.py` line 110: `ThreadPoolExecutor(max_workers=cfg.scan.concurrency)`. Line 51: `ep.ssh_audit_json = json.dumps(audit_data)`. `tls_version` not used at all (grep returns 0) |
| 5 | sslyze is the primary TLS scanner with fallback to existing ssl+cryptography scanner | VERIFIED | `quirk/scanner/tls_scanner.py`: `SSLYZE_AVAILABLE` flag at module level (line 30/32), `_scan_one_sslyze()` at line 103, `_scan_one_fallback()` at line 329, routing logic at lines 439–449 |
| 6 | ssh-audit subprocess integration with `ssh_audit_json` column in models | VERIFIED | `quirk/scanner/ssh_scanner.py` lines 13–26: `_run_ssh_audit()` calls `subprocess.run([exe, "-j", host, str(port)])`. `quirk/models.py` line 54: `ssh_audit_json = Column(Text, nullable=True)` |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/reports/writer.py` | Single scoring path, cert_pubkey_alg fix | VERIFIED | 58-line `_extract_cert_key_type()` checks canonical field first; intelligence imports at lines 11–12; `build_evidence_summary` + `compute_readiness_score` called at lines 158–159; dead functions (`_score_from_evidence`, `_normalize_evidence`, etc.) deleted |
| `tests/test_cert_pubkey_fix.py` | Unit tests for cert_pubkey_alg fix | VERIFIED | 58 lines; tests canonical field priority, fallback chain, None handling |
| `tests/test_scoring_consolidation.py` | Tests for single scoring path | VERIFIED | 106 lines; AST-based import checks confirm no assessment.readiness_score import |
| `quirk/scanner/ssh_scanner.py` | Threaded SSH scanner with ssh-audit | VERIFIED | 327 lines; `ThreadPoolExecutor` at line 5 (import) and line 110 (usage); `_run_ssh_audit()` subprocess function; `ssh_audit_json` population at line 51 |
| `quirk/models.py` | `ssh_audit_json` and `tls_capabilities_json` columns | VERIFIED | Line 54: `ssh_audit_json`; line 49: `tls_capabilities_json`; both `Column(Text, nullable=True)` |
| `tests/test_ssh_scanner.py` | Threaded SSH scan and ssh-audit JSON parsing tests | VERIFIED | 327 lines; covers happy path, ssh-audit absent fallback, timeout fallback, thread pool behavior |
| `quirk/scanner/tls_scanner.py` | sslyze primary scanner with fallback | VERIFIED | `SSLYZE_AVAILABLE` flag; `_scan_one_sslyze()` + `_scan_one_fallback()` + routing in `scan_one()`; `tls_capabilities_json` populated at line 308 |
| `tests/test_sslyze_integration.py` | Tests for sslyze primary and fallback paths | VERIFIED | 494 lines; 12+ tests covering happy path, ImportError fallback, scan error fallback, cert field mapping, tls_capabilities_json structure |
| `quirk/` | Renamed package directory (was qcscan/) | VERIFIED | Directory exists; `qcscan/` gone |
| `pyproject.toml` | Package metadata name=quirk with entry point | VERIFIED | `name = "quirk"`, `quirk = "run_scan:main"`, `version = "3.9.0"` |
| `quirk/__init__.py` | Package init with `__version__` | VERIFIED | `__version__ = "3.9.0"` confirmed via `python -c "import quirk; print(quirk.__version__)"` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/reports/writer.py` | `quirk/intelligence/scoring.py` | `compute_readiness_score(evidence)` call | WIRED | Import at line 12; called at line 159 |
| `quirk/reports/writer.py` | `quirk/intelligence/evidence.py` | `build_evidence_summary(endpoints, findings)` call | WIRED | Import at line 11; called at line 158 |
| `quirk/scanner/ssh_scanner.py` | `quirk/models.py` | `CryptoEndpoint.ssh_audit_json` field population | WIRED | `ep.ssh_audit_json = json.dumps(audit_data)` at line 51 |
| `quirk/scanner/ssh_scanner.py` | ssh-audit subprocess | `subprocess.run` with `-j` flag | WIRED | `_run_ssh_audit()` at line 19: `subprocess.run([exe, "-j", host, str(port)])` |
| `quirk/scanner/tls_scanner.py` | sslyze library | `Scanner.queue_scans()` and `get_results()` | WIRED | Conditional import at line 20–32; `_scan_one_sslyze()` implementation at line 103 |
| `quirk/scanner/tls_scanner.py` | `quirk/models.py` | `CryptoEndpoint.tls_capabilities_json` population | WIRED | `ep.tls_capabilities_json = json.dumps(caps)` at line 308 |
| `run_scan.py` | `quirk/` | All imports use `from quirk.xxx` | WIRED | Zero `from qcscan.` references in live codebase; all imports updated |
| `pyproject.toml` | `run_scan.py` | Console scripts entry point | WIRED | `quirk = "run_scan:main"` in `[project.scripts]` |

### Data-Flow Trace (Level 4)

N/A for this phase — no UI components or pages with rendered dynamic data. Phase delivers scanner engine and CLI tooling, not user-facing rendering components.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `cert_pubkey_alg` returned first (canonical field wins) | `_extract_cert_key_type(SimpleNamespace(cert_pubkey_alg='RSA'))` | `'RSA'` | PASS |
| Canonical field beats legacy fallback | `_extract_cert_key_type(SimpleNamespace(cert_pubkey_alg='ECDSA', cert_key_type='RSA'))` | `'ECDSA'` | PASS |
| Fallback works when canonical is None | `_extract_cert_key_type(SimpleNamespace(cert_pubkey_alg=None, cert_key_type='RSA'))` | `'RSA'` | PASS |
| No assessment.readiness_score import in writer.py | AST walk of writer.py for ImportFrom nodes | No match | PASS |
| All core imports work from quirk namespace | `from quirk.scanner.tls_scanner import scan_one` etc. | `All core imports: PASS` | PASS |
| ThreadPoolExecutor in scan_ssh_targets | `inspect.getsource(scan_ssh_targets)` check | Both `ThreadPoolExecutor` and `as_completed` present | PASS |
| sslyze conditional import structure | `hasattr(tls_scanner, 'SSLYZE_AVAILABLE')` etc. | All three symbols present | PASS |
| Model columns present at runtime | SQLAlchemy inspect of CryptoEndpoint | `ssh_audit_json` and `tls_capabilities_json` both present | PASS |
| Full test suite | `.venv/bin/python -m pytest tests/ -q` | `56 passed in 0.29s` | PASS |
| Package version | `python -c "import quirk; print(quirk.__version__)"` | `3.9.0` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CORE-01 | 01-PLAN-scoring-fixes.md | Single scoring path through intelligence/scoring.py | SATISFIED | writer.py imports and calls `compute_readiness_score` from `quirk.intelligence.scoring`; no assessment layer import present |
| CORE-02 | 01-PLAN-scoring-fixes.md | `cert_pubkey_alg` is first probe in `_extract_cert_key_type()` | SATISFIED | Lines 37–38 of writer.py; runtime-verified via spot-check |
| CORE-03 | 04-PLAN-package-rename.md | Package renamed qcscan → quirk; zero remaining qcscan/QuRisk references | SATISFIED | `qcscan/` gone; `quirk/` exists; 0 grep matches in live .py files; pyproject.toml has `name = "quirk"` |
| CORE-04 | 02-PLAN-ssh-scanner.md | SSH scanner uses ThreadPoolExecutor; `ssh_audit_json` stored | SATISFIED | `ThreadPoolExecutor` in `scan_ssh_targets`; `ep.ssh_audit_json` populated; `tls_version` not misused (0 occurrences) |
| SCAN-01 | 03-PLAN-sslyze-integration.md | sslyze is primary TLS scanner with fallback | SATISFIED | `SSLYZE_AVAILABLE` flag; `_scan_one_sslyze()` primary path; `_scan_one_fallback()` for existing ssl+cryptography code; `tls_capabilities_json` stores extended data |
| SCAN-02 | 02-PLAN-ssh-scanner.md | ssh-audit subprocess integration; `ssh_audit_json` column | SATISFIED | `_run_ssh_audit()` calls `subprocess.run([exe, "-j", ...])` with JSON parsing; `CryptoEndpoint.ssh_audit_json = Column(Text, nullable=True)` in models |

### Anti-Patterns Found

None. No TODOs, FIXMEs, placeholder returns, or stub patterns found in modified files. SSLYZE_AVAILABLE=False in the test environment is expected behavior — sslyze is not installed in `.venv`, which is correct since it is an optional dependency and the fallback path exists.

### Human Verification Required

None. All phase objectives are verifiable programmatically. The phase explicitly excludes UI and focuses on engine-level code.

### Gaps Summary

No gaps. All six requirements are fully satisfied:

- CORE-01 (scoring consolidation): writer.py uses intelligence layer exclusively; dead assessment functions deleted
- CORE-02 (cert_pubkey_alg fix): canonical field checked first; runtime-verified
- CORE-03 (package rename): qcscan/ gone, quirk/ live, pyproject.toml created, zero stale references in live code
- CORE-04 (SSH threading): ThreadPoolExecutor replaces sequential loop; tls_version no longer misused
- SCAN-01 (sslyze primary): primary/fallback architecture present and wired; tls_capabilities_json populated
- SCAN-02 (ssh-audit subprocess): -j flag invocation; ssh_audit_json column added and populated

Note: 10 `qcscan` references exist in `.claude/worktrees/` (stale agent work trees) — these are not part of the live codebase and do not affect any requirement.

---

_Verified: 2026-03-29T20:00:00Z_
_Verifier: Claude (gsd-verifier)_
