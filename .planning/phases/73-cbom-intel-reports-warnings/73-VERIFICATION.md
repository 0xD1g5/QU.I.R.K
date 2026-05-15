---
phase: 73-cbom-intel-reports-warnings
verified: 2026-05-15T00:00:00Z
status: passed
score: 3/3 success criteria + 13/13 WR rows verified
overrides_applied: 0
re_verification: false
---

# Phase 73: CBOM + Intelligence + Reports WARNINGs Verification Report

**Phase Goal:** All three WARNING clusters in the CBOM/intelligence/reports subsystem are resolved — PDF resources cleaned up, weak-crypto predicates consistent, and score weights / roadmap output / cipher labels corrected. Closes audit findings `cbom-intel-reports/WR-01..WR-14` (WR-05 previously closed by Phase 60).
**Verified:** 2026-05-15
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | PDF render exceptions caught by type, Playwright resources released in `finally`, user-visible warning printed without crashing | VERIFIED | `quirk/reports/html_renderer.py:131` `except (PlaywrightError, PlaywrightTimeoutError, OSError, RuntimeError) as e:`; `:137` `finally:` block; `:133` stderr advisory via `safe_str`. 7 tests pass in `tests/test_pdf_render_hardening.py` |
| 2 | `motion_broker_weak_tls_count` predicate uppercase-consistent; ECDSA detection matches `cert_pubkey_alg` (EC/ECDSA); SAML mixed-case SHA-1; email/broker unified via shared helper | VERIFIED | `quirk/intelligence/evidence.py:7` imports `is_weak_cipher, is_legacy_tls_version`; `:132` `startswith(("EC", "ECDSA"))`; `:160` `is_weak_cipher(_saml_alg)`; `:245` legacy TLS check; `:253` broker `is_weak_cipher`; `:273` email `is_weak_cipher`. Tests in `test_intelligence_evidence.py` + 27 cases in `test_weak_crypto_helper.py` |
| 3 | `SCORE_WEIGHTS` documented/invariant-gated; roadmap double-period removed; executive `_build_interpretation` guards `score['score']`; TLS 1.2 non-PFS RSA returns `RSA-kex`; confidence overrides pass clamp+validation | VERIFIED | `quirk/intelligence/scoring.py:5-18` invariant docstring; sum=261.0/count=29 (live verified); `quirk/intelligence/roadmap.py:50` `hint.rstrip('.')`; `quirk/reports/executive.py:12,32,34` `_INTERPRETATION_UNAVAILABLE` + `isinstance(score, dict)` guard; `quirk/cbom/builder.py:142` `"RSA": "RSA-kex"`; `quirk/intelligence/confidence.py:58-62` ValueError + clamp + `_LOGGER.warning`. Test files `test_score_weights_invariant.py`, `test_executive_score_guard.py`, `test_tls_kex_label.py` all pass |

**Score:** 3/3 ROADMAP success criteria verified.

### Audit Ledger Verification (13 WR rows)

```
$ grep -cE "cbom-intel-reports/WR-(01|02|03|04|06|07|08|09|10|11|12|13|14).*Phase 73.*\[x\] closed" \
    .planning/audit-2026-05-08/AUDIT-TASKS.md
13

$ grep -cE "cbom-intel-reports/WR-.*\[ \] open" .planning/audit-2026-05-08/AUDIT-TASKS.md
0
```

All 13 in-scope rows flipped to `Phase 73 | [x] closed` with per-row evidence (D-cite, fix-site, test references). WR-05 remains `Phase 60` closure (out of scope, correct). Zero `[ ] open` rows remain in the `cbom-intel-reports/WR-*` cluster.

| WR | Plan | Closure Evidence (excerpt) | Status |
| -- | ---- | ----------------------- | ------ |
| WR-01 | 73-01 | Narrowed except tuple at `html_renderer.py:131` — KeyError propagates | VERIFIED |
| WR-02 | 73-01 | `finally:` block at `html_renderer.py:137` calls `browser.close()` defensively | VERIFIED |
| WR-03 | 73-02 | `evidence.py:245,253` route through `is_legacy_tls_version` + `is_weak_cipher` | VERIFIED |
| WR-04 | 73-02 | `evidence.py:132` `startswith(("EC", "ECDSA"))` | VERIFIED |
| WR-06 | 73-03 | `scoring.py:5-18` invariant docstring + `test_score_weights_invariant.py` (sum=261.0, count=29) | VERIFIED |
| WR-07 | 73-03 | `roadmap.py:50` `hint.rstrip('.')` | VERIFIED |
| WR-08 | 73-03 | `_add_candidate` docstring documenting merge rule | VERIFIED |
| WR-09 | 73-03 | `executive.py:12,32,34` `_INTERPRETATION_UNAVAILABLE` + isinstance guard | VERIFIED |
| WR-10 | 73-02 | `evidence.py:160` `is_weak_cipher(_saml_alg)` (mixed-case SHA-1) | VERIFIED |
| WR-11 | 73-02 | `evidence.py:273` email predicate uses `is_weak_cipher` | VERIFIED |
| WR-12 | 73-03 | `cbom/builder.py:142` `"RSA": "RSA-kex"` | VERIFIED |
| WR-13 | 73-03 | `confidence.py:58-62` ValueError + clamp + `_LOGGER.warning` | VERIFIED |
| WR-14 | 73-01 | `html_renderer.py:133` stderr advisory via `safe_str(e)` | VERIFIED |

### D-01..D-10, D-14 Decision Compliance

| Decision | Locked Requirement | Codebase Evidence | Status |
| -------- | ------------------ | ----------------- | ------ |
| D-01 | Narrowed except + finally + safe_str stderr advisory | `html_renderer.py:131,133,137` | VERIFIED |
| D-02 | `quirk/util/weak_crypto.py::is_weak_cipher` shared helper | Module exists, evidence.py imports + uses | VERIFIED |
| D-02a | `_WEAK_CIPHER_TOKENS` private, helper public | `weak_crypto.py:23` (private), `:36` (public) | VERIFIED |
| D-03 | ECDSA `startswith(("EC", "ECDSA"))` tuple | `evidence.py:132` | VERIFIED |
| D-04 | SCORE_WEIGHTS NOT normalized; documented invariant; CI gate | sum=261.0 unchanged; docstring `scoring.py:5-18`; `test_score_weights_invariant.py` | VERIFIED |
| D-05 | Roadmap `_why` rstrip then re-append `.` | `roadmap.py:50` | VERIFIED |
| D-06 | `_add_candidate` merge rule documented | Docstring present (RESEARCH C-6 — figurative "mutation-after-yield"); 3 tests | VERIFIED |
| D-07 | `_build_interpretation` guards `score['score']` with `_INTERPRETATION_UNAVAILABLE` fallback | `executive.py:12,32,34` | VERIFIED |
| D-08 | TLS 1.2 non-PFS RSA → `RSA-kex` label | `cbom/builder.py:142` | VERIFIED |
| D-09 | Confidence override clamp + fail-loud + WARN | `confidence.py:58-62` | VERIFIED |
| D-10 | `is_legacy_tls_version` co-located in `weak_crypto.py` | `weak_crypto.py:48`; `evidence.py:245` | VERIFIED |
| D-14 | Do-not-touch boundary | SCORE_WEIGHTS values unchanged (sum=261.0); `_apply_weighted_impacts` untouched; `trends.py` / `technical.py` / `cbom/builder.py` pass-logic untouched (only `_KEX_MAP` single-token relabel at :142) | VERIFIED |

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `quirk/util/weak_crypto.py` | `is_weak_cipher` public + `_WEAK_CIPHER_TOKENS` private incl. `CBC3` | VERIFIED | 57 lines; CBC3 present at line 24; helpers public; tokens private with `Final[frozenset[str]]` |
| `tests/test_score_weights_invariant.py` | exists + passes | VERIFIED | 2 assertions (sum=261.0, count=29) — pass |
| `tests/test_weak_crypto_helper.py` | exists | VERIFIED | 27 cases pass |
| `tests/test_pdf_render_hardening.py` | exists + passes | VERIFIED | 7 tests pass |
| `tests/test_executive_score_guard.py` | exists | VERIFIED | 5 tests pass |
| `tests/test_tls_kex_label.py` | exists | VERIFIED | 10 parametrized cases pass |
| `tests/test_confidence_clamp.py` | requested by verifier | NOT PRESENT — but coverage exists in `tests/test_intelligence_confidence.py` (7 new cases per 73-03 SUMMARY: below-zero / above-one / in-range / non-numeric / None / list / unknown-key) | ACCEPTED (alternative impl) |

### Test Execution

```
$ pytest tests/test_score_weights_invariant.py tests/test_weak_crypto_helper.py \
    tests/test_pdf_render_hardening.py tests/test_intelligence_confidence.py \
    tests/test_executive_score_guard.py tests/test_tls_kex_label.py \
    tests/test_intelligence_evidence.py tests/test_intelligence_roadmap.py -q
81 passed in 0.17s
```

The verifier's requested `tests/test_confidence_clamp.py` does not exist as a file by that name; the confidence clamp coverage lives in `tests/test_intelligence_confidence.py` per 73-03 SUMMARY task 5, which passes. This matches CONTEXT test_strategy line 139 listing `tests/test_confidence_clamp.py` as the WR-13 micro-module name — implementation moved the cases into the existing `test_intelligence_confidence.py` (RESEARCH C-5 colocation). Functionally equivalent, all 7 cases assert.

### Compileall

```
$ python -m compileall quirk/ -q
$ echo $?
0
```

### Anti-Patterns Found

None. No TBD/FIXME/XXX markers added in Phase 73 file scope.

### Human Verification Required

None — Phase 73 is entirely internal-contract hardening (PDF advisory text, predicate routing, invariant assertion). No UI changes, no UAT cases per CONTEXT test_strategy line 145.

### Gaps Summary

None. All 3 ROADMAP success criteria verified at HEAD; all 13 in-scope WR rows flipped to `[x] closed` with per-row evidence; all 11 locked decisions (D-01..D-10, D-14) honored; new module `quirk/util/weak_crypto.py` present with correct public/private surface and CBC3 token; targeted test suite (81 tests) passes clean; `python -m compileall quirk/` exits 0.

---

_Verified: 2026-05-15_
_Verifier: Claude (gsd-verifier)_
