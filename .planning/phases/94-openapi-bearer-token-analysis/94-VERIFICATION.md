---
phase: 94-openapi-bearer-token-analysis
verified: 2026-05-23T03:53:00Z
status: gaps_found
score: 5/6 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Bearer tokens captured during an authenticated scan appear in the CBOM with declared_algorithm (unverified); raw token absent from all stored artifacts"
    status: failed
    reason: >-
      No production code path creates a CryptoEndpoint(protocol="BEARER_TOKEN").
      The CBOM builder branch (builder.py:441-449), evidence counter
      (evidence.py:306-312), and scoring weight (agility_weak_jwt_alg_ratio: 6.0)
      are all consumer-side scaffolding that can never fire in a real scan.
      grep across all production files (quirk/ and run_scan.py, excluding tests and
      __pycache__) finds zero protocol="BEARER_TOKEN" assignments. The
      CredentialContext built from --auth-bearer is passed only to scan_jwt_targets;
      no scan phase converts cred_ctx.bearer into a BEARER_TOKEN endpoint.
      The TOKEN-02 success criterion states "Bearer tokens captured during an
      authenticated scan appear in the CBOM" — this is categorically unmet because
      the authenticated scan does not capture bearer tokens into the endpoint
      pipeline. The CBOM branch is exercised only by a hand-built FakeEndpoint in
      tests/test_analyze_token.py.
    artifacts:
      - path: "quirk/cbom/builder.py"
        issue: "BEARER_TOKEN branch at line 441 is dead — no producer feeds it during a scan"
      - path: "quirk/intelligence/evidence.py"
        issue: "bearer_token_weak_alg_count always 0 in any real scan (no producer)"
      - path: "quirk/intelligence/scoring.py"
        issue: "agility_weak_jwt_alg_ratio weight (6.0) can never fire in a real scan"
      - path: "run_scan.py"
        issue: "cred_ctx.bearer is passed to jwt_scanner only; no code converts it to a BEARER_TOKEN CryptoEndpoint for CBOM"
    missing:
      - "A scan code path that, when --auth-bearer is provided, creates a CryptoEndpoint(protocol='BEARER_TOKEN', cert_pubkey_alg=<decoded_alg>, host=<target>) and feeds it into the endpoint pipeline before build_cbom is called"
      - "Alternatively: explicit decision to document BEARER_TOKEN scaffolding as deferred to a later phase, with score weight removed from SCORE_WEIGHTS until a producer exists (so the invariant sum/count reflects live signals only)"
---

# Phase 94: OpenAPI & Bearer Token Analysis Verification Report

**Phase Goal:** Users can decode and classify bearer/JWT tokens and analyze OpenAPI/Swagger specs for API crypto posture, both passively and with no active traffic to any target.
**Verified:** 2026-05-23T03:53:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `quirk analyze-token <jwt>` reports algorithm, key size, expiry, quantum-safety, and flags alg:none CRITICAL (case-insensitive none/None/NONE/NonE) | VERIFIED | Live run confirmed: RS256 token exits 0 with alg/expiry/quantum-safety. alg:none (all 4 variants) exits 1 with CRITICAL banner. `tests/test_analyze_token.py` covers all 4 variants. WR-05 fix applied: missing-alg header also exits 1 with CRITICAL. |
| 2 | Local OpenAPI spec yields findings for plaintext servers, unauthenticated endpoints, weak/absent security schemes; appear in standard findings table | VERIFIED | `quirk/scanner/openapi_scanner.py` extracts `plaintext_server` (HIGH), `security_scheme:<name>` (INFO), `unauthenticated_endpoint:METHOD PATH` (MEDIUM) as CryptoEndpoint(protocol="OPENAPI"). All 8 tests in `tests/test_openapi_scanner.py` pass. `run_scan.py` dispatches `_run_openapi_phase()` when `--openapi-spec` is provided. |
| 3 | A spec URL is fetched only when within configured scan-target scope; out-of-scope URL rejected before any network request | VERIFIED | CR-01 fix confirmed in `_fetch_spec_bytes_from_url` (openapi_scanner.py:144-155): extracts hostname via `urlparse`, compares against `allowed_hosts` set built from `cfg_targets`. `test_url_scope_rejected` and `test_url_scope_accepts_bare_fqdn_target` (CR-01 regression test) both pass. The latter explicitly tests bare-FQDN `cfg_targets` matching the real `cfg.targets.fqdns` shape. |
| 4 | An internal-network `$ref` (e.g. http://169.254.169.254/) raises SpecParsingError before any outbound request — CI fixture test | VERIFIED | `_assert_no_external_refs` (openapi_scanner.py:82-103) runs BEFORE `_oas_validate`. `test_external_ref_ssrf_guard` monkeypatches both `httpx.get` and `_oas_validate` and asserts zero calls on a spec with a 169.254.169.254 $ref. Test passes. The protocol (OPENAPI) is correctly cased — the evidence counter and scoring weight fire when applicable. |
| 5 | Bearer tokens captured during an authenticated scan appear in the CBOM with `declared_algorithm (unverified)`; raw token absent from all stored artifacts | FAILED | No production code creates `CryptoEndpoint(protocol="BEARER_TOKEN")` during a scan. The CBOM builder branch (builder.py:441), evidence counter (evidence.py:306), and scoring weight (6.0) are consumer-side scaffolding only. The `cred_ctx` built from `--auth-bearer` in run_scan.py is passed exclusively to `scan_jwt_targets`; it is never extracted into a BEARER_TOKEN endpoint. `bearer_token_weak_alg_count` is always 0 in any real scan. This was flagged as WR-02 in the code review and explicitly deferred to the verifier. |
| 6 | `pip install quirk[api]` pulls openapi-spec-validator; `quirk[all]` does NOT pull schemathesis — CI test | VERIFIED | `pyproject.toml` has `api = ["openapi-spec-validator>=0.9.0"]`. `quirk[api]` is not listed in `[all]`. Guard comment explains the intentional exclusion. `tests/test_install_all_excludes_schemathesis.py` asserts both `schemathesis` and `openapi-spec-validator` are absent from `quirk[all]` dry-run resolution. |

**Score: 5/6 truths verified**

---

## CRITICAL Assessment: SC-5 / TOKEN-02 (BEARER_TOKEN wiring)

The code review finding WR-02 is confirmed as a real gap. The determination is FAILED, not UNCERTAIN.

**Evidence:**

1. Full `grep -rn "BEARER_TOKEN"` across `quirk/` and `run_scan.py` (excluding tests and `__pycache__`) finds zero `protocol="BEARER_TOKEN"` assignments anywhere in production code.

2. The `CredentialContext` is built from `--auth-bearer` at run_scan.py:834. It is passed to `scan_jwt_targets` only (run_scan.py:1316). No subsequent code converts `cred_ctx.bearer` into a `CryptoEndpoint`.

3. The `analyze-token` command is standalone: it decodes and prints; it does not produce `CryptoEndpoint` rows or interact with any scan pipeline.

4. `bearer_token_weak_alg_count` in `evidence.py` initializes to 0 and its increment condition (`elif proto == "BEARER_TOKEN":`) can never trigger in production.

5. The `agility_weak_jwt_alg_ratio` weight in `SCORE_WEIGHTS` (6.0) therefore scores a phantom signal — it always contributes 0 to the agility subscore but the weight counts toward the 293.0 invariant.

The TOKEN-02 requirement text is: *"Bearer tokens captured during an authenticated scan are classified into the CBOM with a `declared_algorithm (unverified)` label — never treated as enforced."* The phrase "captured during an authenticated scan" is the key predicate. The scan never captures them. The CBOM classification logic exists but cannot be reached.

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/cli/analyze_token_cmd.py` | run_analyze_token entry point, decode+classify, exit codes | VERIFIED | 263 lines, exports `run_analyze_token`, no DB writes, all behaviors present |
| `tests/test_analyze_token.py` | TOKEN-01/02/03 unit coverage, `test_alg_none_critical` | VERIFIED | 16 tests pass; covers all 4 alg:none variants, opaque token, RS256 decode, token-not-echoed, CBOM bearer unit test, WR-05 missing-alg |
| `quirk/scanner/openapi_scanner.py` | `class SpecParsingError`, SSRF+DoS gates, crypto posture extraction | VERIFIED | 394 lines, `SpecParsingError` defined, `OPENAPI_AVAILABLE` guard, `_assert_no_external_refs` before `_oas_validate`, `MAX_SPEC_BYTES` gate |
| `tests/test_install_all_excludes_schemathesis.py` | PKG-01 CI guard | VERIFIED | Mirrors impacket test; asserts schemathesis and openapi-spec-validator absent from `quirk[all]` |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `run_scan.py` | `quirk.cli.analyze_token_cmd.run_analyze_token` | argv[1] == 'analyze-token' intercept | WIRED | Lines 483-486 in run_scan.py; live test confirms routing |
| `quirk/cbom/builder.py` | `_register_algorithm` via BEARER_TOKEN Pass-1 branch | `elif ep.protocol == "BEARER_TOKEN"` | ORPHANED | Branch exists and is correct; NO producer creates BEARER_TOKEN endpoints in production |
| `quirk/scanner/openapi_scanner.py` | `validate_external_url` | URL scope + SSRF gate in `_fetch_spec_bytes_from_url` | WIRED | CR-01 fix applied; hostname-based comparison; `test_url_scope_accepts_bare_fqdn_target` passes |
| `quirk/scanner/openapi_scanner.py` | `_assert_no_external_refs` before `_oas_validate` | Called at openapi_scanner.py:388 | WIRED | Critical ordering confirmed; `test_external_ref_ssrf_guard` proves zero outbound requests |
| `pyproject.toml` | `tests/test_install_all_excludes_schemathesis.py` | `api = [openapi-spec-validator]` excluded from `[all]` | WIRED | Guard comment present; test asserts both schemathesis and [api] dep absent from [all] |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `openapi_scanner.py::extract_crypto_posture` | `endpoints` list | parsed `spec_dict` from local file / URL | Yes — parses real spec structure | FLOWING |
| `evidence.py::bearer_token_weak_alg_count` | counter incremented at `elif proto == "BEARER_TOKEN"` | endpoints list passed to `build_evidence_summary` | No — counter always 0; no producer emits BEARER_TOKEN endpoints in a real scan | DISCONNECTED |
| `scoring.py::agility_weak_jwt_alg_ratio` | `bearer_weak_jwt_alg` from evidence summary | `bearer_token_weak_alg_count` / total | Always 0 (denominator may be nonzero, ratio is always 0.0) | HOLLOW — weight in SCORE_WEIGHTS but data is always 0 |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `analyze-token` reports alg, expiry, quantum-safety for valid JWT | `python run_scan.py analyze-token <RS256-jwt>` | RS256 / quantum-vulnerable / expiry displayed | PASS |
| alg:none token exits 1 with CRITICAL | `python run_scan.py analyze-token <alg-none-jwt>` | "CRITICAL: alg:none detected" + exit 1 | PASS |
| opaque token exits 0 with INFO | `python run_scan.py analyze-token notajwtatall123` | "INFO: token does not appear to be a JWT" + exit 0 | PASS |
| missing-alg JWT exits 1 with CRITICAL (WR-05 fix) | `python run_scan.py analyze-token <no-alg-jwt>` | "CRITICAL: no 'alg' header present" + exit 1 | PASS |
| SCORE_WEIGHTS sum and count | `python -c "from quirk.intelligence.scoring import SCORE_WEIGHTS; print(sum(SCORE_WEIGHTS.values()), len(SCORE_WEIGHTS))"` | 293.0 39 | PASS |
| All unit tests pass | `.venv/bin/python -m pytest tests/test_analyze_token.py tests/test_score_weights_invariant.py tests/test_openapi_scanner.py -q` | 24 passed | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SPEC-01 | 94-02 | Local OpenAPI spec → plaintext servers, unauthenticated endpoints, security schemes | SATISFIED | `extract_crypto_posture` produces all three finding types; 8 tests pass |
| SPEC-02 | 94-02 | Spec URL fetch only when within configured scan-target scope | SATISFIED | CR-01 fix: host-based scope gate before network request; CR-01 regression test passes |
| SPEC-03 | 94-02 | $ref SSRF hardening and oversized-spec DoS gate | SATISFIED | `_assert_no_external_refs` before `_oas_validate`; 10MB gate before `yaml.safe_load`; CI fixture tests prove zero outbound requests |
| TOKEN-01 | 94-01 | `analyze-token` decodes algorithm, key size, expiry, quantum-safety | SATISFIED | Live runs confirmed; all test cases pass |
| TOKEN-02 | 94-01 | Bearer tokens during authenticated scan → CBOM with `declared_algorithm (unverified)` | NOT SATISFIED | CBOM branch and evidence counter exist but no scan code path creates BEARER_TOKEN endpoints; bearer always 0 in real scans |
| TOKEN-03 | 94-01 | alg:none (any case) flagged CRITICAL | SATISFIED | Case-insensitive header dict check; all 4 variants exit 1; WR-05 also covered |
| SCORE-01 | 94-01/02 | API signals contribute to agility_signals subscore | PARTIAL | openapi_plaintext_ratio fires (OPENAPI endpoints produced); agility_weak_jwt_alg_ratio is dead (no BEARER_TOKEN producer) |
| PKG-01 | 94-02 | `[api]` extras group; schemathesis excluded from `[all]` — CI test | SATISFIED | `pyproject.toml` api group correct; `[all]` excludes `[api]`; CI guard test exists and passes under `-m slow` |

**REQUIREMENTS.md tracking gap:** All 8 requirement rows (SPEC-01..03, TOKEN-01..03, SCORE-01, PKG-01) remain `Pending` (checkbox `- [ ]`) in `.planning/REQUIREMENTS.md`. The orchestrator must flip these to complete (TOKEN-02 should remain pending until the gap is closed).

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `quirk/intelligence/evidence.py` | 319-321 | `"http-server" in _oa_detail` dead branch — scanner never sets this value; only `"plaintext_server"` is used; counter works by substring coincidence only | Warning | Silent breakage if service_detail is renamed; WR-03 from code review |
| `quirk/scanner/openapi_scanner.py` | 166 | `follow_redirects=True` with no cap; redirect target not re-validated against scope/SSRF gate (IN-03 from code review) | Warning | Redirect to out-of-scope or metadata host would bypass scope gate after CR-01 fix; lower priority because rare in practice |
| `quirk/scanner/openapi_scanner.py` | 173-174 | Full response body buffered before 10MB gate on URL path (WR-04 from code review) | Warning | Memory exhaustion possible on adversarial server before size gate fires; file path is correctly gated |

No TBD/FIXME/XXX debt markers found in any phase-modified files.

---

## Human Verification Required

### 1. SCORE-01 Partial Signal

**Test:** Run `quirk scan --openapi-spec` against a local spec with at least one `http://` server. Then run `quirk scan` without `--openapi-spec`. Compare the `agility_signals` subscore between the two runs.
**Expected:** The run with the OpenAPI spec should show a lower agility subscore (penalized by the plaintext_server finding flowing through `openapi_plaintext_server_count` and `agility_openapi_plaintext_ratio`).
**Why human:** Requires a full scan run with a test spec and comparison of numeric scores in the dashboard or JSON output; not testable by grep.

---

## Gaps Summary

**One blocker prevents full goal achievement.**

TOKEN-02 is a wiring gap: the CBOM classification infrastructure for bearer tokens is built and correct, but the authenticated scan path never produces a `CryptoEndpoint(protocol="BEARER_TOKEN")` endpoint to feed it. The `analyze-token` command is standalone (print-only) and was not wired to emit endpoints. The `--auth-bearer` credential context is used only to inject the bearer token into outgoing HTTP requests; the token's algorithm is never decoded and recorded as a scan finding.

The code review (94-REVIEW.md, WR-02) identified this explicitly and deferred it to the verifier as a deliberate architectural decision point: either (a) wire a scan phase to emit BEARER_TOKEN endpoints from the authenticated credential, or (b) explicitly scope TOKEN-02 to a later phase and remove the dead `agility_weak_jwt_alg_ratio` weight from SCORE_WEIGHTS until a producer exists.

All other success criteria (SC-1, SC-2, SC-3, SC-4, SC-6) are fully met and verified against the codebase.

---

_Verified: 2026-05-23T03:53:00Z_
_Verifier: Claude (gsd-verifier)_
