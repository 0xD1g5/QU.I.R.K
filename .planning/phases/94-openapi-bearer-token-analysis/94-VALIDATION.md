---
phase: 94
slug: openapi-bearer-token-analysis
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-23
---

# Phase 94 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (configured in `pyproject.toml` `[tool.pytest.ini_options]`) |
| **Config file** | `pyproject.toml` (no separate pytest.ini) |
| **Quick run command** | `pytest tests/test_analyze_token.py tests/test_openapi_scanner.py tests/test_score_weights_invariant.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~30 seconds (quick); full suite minus the slow-marked install test |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_analyze_token.py tests/test_openapi_scanner.py tests/test_score_weights_invariant.py -x`
- **After every plan wave:** Run `pytest` (full suite)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Wave 0 — Test Infrastructure

No new framework install required (pytest already configured). Test files are created
test-first as the opening action of each owning TDD task — Wave 0 obligations are
embedded in the feature tasks rather than a separate plan:

- `tests/test_analyze_token.py` — created in Plan 94-01 Task 1 (covers TOKEN-01/02/03)
- `tests/test_openapi_scanner.py` — created in Plan 94-02 Task 1 (covers SPEC-01/02/03)
- `tests/test_install_all_excludes_schemathesis.py` — created in Plan 94-02 Task 2 (PKG-01)
- `tests/test_score_weights_invariant.py` — already exists; updated in Plan 94-01 Task 2

`wave_0_complete: true` — every required test file has an owning task that creates it
before the implementation it covers.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 94-01-01 | 94-01 | 1 | TOKEN-01 | token-leak | Token never written to DB; opaque token handled gracefully | unit | `pytest tests/test_analyze_token.py::test_decode_rs256_token -x` | created in task | pending |
| 94-01-01 | 94-01 | 1 | TOKEN-01 | — | Opaque (non-JWT) token → INFO, exit 0 | unit | `pytest tests/test_analyze_token.py::test_opaque_token_graceful -x` | created in task | pending |
| 94-01-01 | 94-01 | 1 | TOKEN-03 | — | `alg:none` (all case variants) → CRITICAL + exit 1 | unit | `pytest tests/test_analyze_token.py::test_alg_none_critical -x` | created in task | pending |
| 94-01-02 | 94-01 | 1 | TOKEN-02 | — | CBOM bearer component labeled `declared_algorithm (unverified)` | unit | `pytest tests/test_analyze_token.py::test_cbom_bearer_classification -x` | created in task | pending |
| 94-01-02 | 94-01 | 1 | SCORE-01 | — | SCORE_WEIGHTS sum = 293.0 AND count = 39 (both invariants) | unit | `pytest tests/test_score_weights_invariant.py -x` | exists (updated) | pending |
| 94-02-01 | 94-02 | 2 | SPEC-01 | — | Local spec parsed; security schemes extracted | unit | `pytest tests/test_openapi_scanner.py::test_local_file_parse -x` | created in task | pending |
| 94-02-01 | 94-02 | 2 | SPEC-02 | scope-bypass | URL outside scan-target scope rejected before any network request | unit | `pytest tests/test_openapi_scanner.py::test_url_scope_rejected -x` | created in task | pending |
| 94-02-01 | 94-02 | 2 | SPEC-03 | dos | File > 10 MB → SpecParsingError before parse | unit | `pytest tests/test_openapi_scanner.py::test_oversize_rejected -x` | created in task | pending |
| 94-02-01 | 94-02 | 2 | SPEC-03 | ssrf | External/internal-network `$ref` → SpecParsingError, zero outbound request | unit | `pytest tests/test_openapi_scanner.py::test_external_ref_ssrf_guard -x` | created in task | pending |
| 94-02-02 | 94-02 | 2 | PKG-01 | supply-chain | `quirk[all]` resolves without schemathesis | slow | `pytest tests/test_install_all_excludes_schemathesis.py -m slow` | created in task | pending |
| 94-03-* | 94-03 | 3 | docs | — | Docs + UAT-SERIES + Obsidian sync present | grep | `grep -Eq "169\\.254\\.169\\.254\|SpecParsingError\|schemathesis" docs/UAT-SERIES.md` | n/a | pending |

---

## Dimension 8 Compliance

- **8a — every requirement has a test:** ✅ SPEC-01/02/03, TOKEN-01/02/03, SCORE-01, PKG-01 all mapped above.
- **8b — every test has an automated command:** ✅ all rows carry a `pytest`/`grep` command.
- **8c — security behaviors mapped:** ✅ SSRF, DoS, scope-bypass, token-leak all have threat refs + tests.
- **8d — Wave 0 completeness:** ✅ test files created test-first within owning tasks (`wave_0_complete: true`).
- **8e — VALIDATION.md present and populated:** ✅ this file.
