---
phase: 93-credential-infrastructure
verified: 2026-05-23T00:00:00Z
status: passed
score: 5/5
overrides_applied: 0
gaps: []
human_verification:
  - test: "Authenticated scan run via interactive bare flag (getpass prompt)"
    expected: "Running `quirk --config config.yaml --auth-bearer` without a REF value triggers an interactive getpass prompt and the scan completes without error"
    why_human: "Requires a real TTY and a live JWT-serving target; cannot be exercised programmatically without running the server"
  - test: "PDF export is free of credentials on a live authenticated scan"
    expected: "A real Playwright-rendered PDF export of a scan that ran with --auth-bearer contains no raw credential value"
    why_human: "The automated test uses upstream-linkage assertion (CBOM JSON) rather than a live Playwright render, which requires a running server + Chromium install. The upstream is proven clean; the final render path needs a human live-run for full confidence"
---

# Phase 93: Credential Infrastructure Verification Report

**Phase Goal:** Users can supply ephemeral Bearer/OAuth2, API-key, or HTTP Basic credentials for a single authenticated scan run, with a committed security-review gate ensuring credentials never leak into stored artifacts.
**Verified:** 2026-05-23T00:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can pass credentials via --auth-bearer, --auth-api-key (header AND query), --auth-basic, env vars, or interactive prompt; authenticated scan run completes | VERIFIED | `run_scan.py` has all four argparse flags with `nargs="?"`, `const="PROMPT"` (lines 673-712). `CredentialContext.from_cli()` resolves `@file`, env-var name (deleted after read), bare flag → getpass, error for inline. `from_cli()` called at line 809 after config load. `_run_jwt_phase` captures `cred_ctx=cred_ctx`. 22/22 unit tests green. |
| 2 | A completed scan's SQLite row, CBOM output, dashboard API response, PDF export, and log files contain no raw credential value — scrubbing verified by automated test | VERIFIED | `tests/test_credential_leakage.py` 25 tests GREEN (run confirmed). Covers: safe_str all 4 shapes, scan_error JSON, SQLite DB round-trip (scan_error/jwt_scan_json/host/service_detail columns), CBOM JSON file, dashboard `/api/scan/latest`, PDF export via upstream-linkage assertion with documented comment. CR-02 fix (commit 624f55a) routes jwt scanner exception log through `safe_str(exc)`. CR-04 fix persists `safe_str(exc)` in `mark_job_failed`. |
| 3 | Running `quirk schedule add` with enable_authenticated_mode: true exits with error code QRK-SCHED-AUTH-001 and a clear message | VERIFIED | `quirk/cli/schedule_cmd.py` has `_config_has_authenticated_mode()` helper using `yaml.safe_load`; rejection branch calls `format_error('SCHED-AUTH-001')` + `sys.exit(2)` before DB write (lines 76-78). `quirk/errors.py` has the `SCHED-AUTH-001` ErrorEntry (line 161). `format_error("SCHED-AUTH-001")` verified to contain `QRK-SCHED-AUTH-001`. All 14 `test_scan_error_gate` tests GREEN. |
| 4 | A committed security-review gate deliverable documents all 11 credential-leakage surfaces, the safe_str() extension, and the best-effort nature of in-memory zeroization | VERIFIED | `93-SECURITY-REVIEW-GATE.md` present (241 lines). Enumerates all 11 surfaces (SQLite scan_error, api_scan_json/cbom_json, CBOM files, dashboard API, PDF export, CLI HTML report, structured/debug logs, Python traceback, WAL file, process swap/core dump, scheduler scheduled_scans). Each surface has control mechanism + cited artifact. Documents `safe_str()` 4 new patterns (D-08). States best-effort zeroization caveat explicitly ("NOT provable"). Declares D-07 milestone gate. |
| 5 | The AST CI gate deny-list is extended to flag bearer/api_key/authorization/token in json.dumps()/model_dump() calls, and CI is green | VERIFIED | `tests/test_scan_error_gate.py` defines `CREDENTIAL_FIELD_NAMES = frozenset({"bearer","api_key","authorization","token","password","credential","secret","key"})`. `SCANNER_DIRS` includes `quirk/auth`. Positive self-test proves synthetic `json.dumps(token=...)` is flagged; negative self-test proves clean code is not flagged. Schema column gate asserts no credential-named column in `quirk/db.py`. 14/14 tests GREEN. `test_error_codes_freshness.py` 3/3 GREEN (commit 2188109 added SCHED-AUTH-001 to ERROR-CODES.md regenerated artifact). |

**Score:** 5/5 truths verified

---

## Code Review Remediation (Commit 624f55a) — Explicitly Verified

The code review (93-REVIEW.md) found 4 BLOCKER defects post-execution. All 4 are confirmed fixed in the codebase:

| Finding | Fix Verified |
|---------|-------------|
| CR-01: `_strip_auth_from_log` did not redact query-param secret in `request.url` | VERIFIED — `jwt_scanner.py` lines 51-56: `copy_set_param` loop over `_KEY_PARAM_NAMES` rewrites URL with "REDACTED"; `_KEY_PARAM_NAMES` constant defined at line 30 |
| CR-02: JWT scan exception logged raw via `logger.v(f"... {exc}")` | VERIFIED — `jwt_scanner.py` line 339: `logger.v(f"JWT scan error for {base_url}: {safe_str(exc)}")` |
| CR-03: Base JWKS probe URLs fetched without `validate_external_url` (SSRF) | VERIFIED — `jwt_scanner.py` lines 152-154: `_vr_base = validate_external_url(url); if not _vr_base.ok: continue` for every path in `JWKS_PATHS` |
| CR-04: `mark_job_failed` persisted raw exception without `safe_str` | VERIFIED — `run_scan.py` line 1982: `mark_job_failed(db_path, job_id, f"{type(exc).__name__}: {safe_str(exc)}")` |

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/auth/__init__.py` | Package init | VERIFIED | Exists; empty with `from __future__ import annotations` |
| `quirk/auth/credentials.py` | CredentialContext dataclass | VERIFIED | 200 lines; `class CredentialContext`, `as_headers`, `query_param`, `close`, `from_cli`, context manager; zero `quirk.scanner.*` imports (D-14); `safe_str` imported (LEAK-03) |
| `quirk/config.py` | `enable_authenticated_mode` on ConnectorsCfg | VERIFIED | Line 270: `enable_authenticated_mode: bool = False` |
| `quirk/util/safe_exc.py` | 4 new `_SENSITIVE_PATTERNS` entries | VERIFIED | Lines 34-38: X-Api-Key, X-Auth-Token, query-param, Basic — all 4 present |
| `quirk/errors.py` | SCHED-AUTH-001 ErrorEntry | VERIFIED | Lines 161-164: `SCHED-AUTH-001` registered |
| `quirk/cli/schedule_cmd.py` | Auth-mode rejection with QRK-SCHED-AUTH-001 | VERIFIED | `_config_has_authenticated_mode()` + `sys.exit(2)` present |
| `tests/test_scan_error_gate.py` | AST + schema gates, `quirk/auth` in SCANNER_DIRS | VERIFIED | `CREDENTIAL_FIELD_NAMES` frozenset; `quirk/auth` in `SCANNER_DIRS`; positive/negative self-tests |
| `run_scan.py` | 4 `--auth-*` flags + CredentialContext build + finally-zeroize | VERIFIED | Flags at lines 673-712; build at 808-814; `_run_jwt_phase` passes `cred_ctx=cred_ctx`; normal-exit close at 1959-1961; BaseException-safe close via `_run_main_with_job_guard` finally (line 1982-1995) |
| `quirk/scanner/jwt_scanner.py` | `cred_ctx=` param + `_strip_auth_from_log` + `_append_query_param` + SSRF guard | VERIFIED | All four present; `_strip_auth_from_log` redacts query params (CR-01); `validate_external_url` on base probes (CR-03) |
| `tests/test_credential_leakage.py` | 25-test sentinel suite covering all 11 surfaces incl PDF | VERIFIED | `SENTINEL` defined; `quirk/auth/credentials.py` in `MODIFIED_FILES`; all surfaces covered; 25 tests GREEN |
| `.planning/phases/93-credential-infrastructure/93-SECURITY-REVIEW-GATE.md` | 11-surface audit + safe_str coverage + best-effort caveat | VERIFIED | 241-line document; all 11 surfaces; PDF cites automated assertion; "best-effort" present; milestone gate declared (D-07) |
| `docs/configuration.md` | Authenticated scanning section | VERIFIED | `--auth-bearer`, `--auth-api-key`, `--auth-api-key-query`, `--auth-basic` documented; reference-not-secret model; QRK-SCHED-AUTH-001 scheduler rejection; ephemeral-only invariant |
| `docs/UAT-SERIES.md` | Phase 93 UAT cases (UAT-93-01/02/03) | VERIFIED | All three cases present; QRK-SCHED-AUTH-001 present; Last Updated 2026-05-23 |
| Obsidian Phase-93 note | vault Phase-93-Credential-Infrastructure.md | VERIFIED | `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-93-Credential-Infrastructure.md` exists |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `run_scan.py` `_run_jwt_phase` closure | `jwt_scanner.scan_jwt_targets(cred_ctx=...)` | closure capture (D-14 — `_wrapped_phase` signature unchanged) | VERIFIED | `cred_ctx=cred_ctx` at line 1290; `_wrapped_phase` still 6 params at line 116 |
| `jwt_scanner.py` httpx request | `CredentialContext.as_headers()` + `CredentialContext.query_param()` | `as_headers()` → headers dict; `query_param()` → `_append_query_param()` URL injection | VERIFIED | Lines 227-228: `_auth_headers` + `_auth_query` extracted per call; `_fetch_jwks` applies both |
| `jwt_scanner.py` `_strip_auth_from_log` | `request.headers` + `request.url` | event hook pops headers + `copy_set_param` for query-param key | VERIFIED | Lines 43-56; `_KEY_PARAM_NAMES` frozenset at line 30; `httpx.Client(event_hooks=...)` at line 142 |
| `quirk/cli/schedule_cmd.py` `_cmd_add` | `quirk/errors.py` `format_error('SCHED-AUTH-001')` | rejection branch before DB write | VERIFIED | Lines 76-78 |
| `tests/test_scan_error_gate.py` | `quirk/auth/` + `quirk/db.py` | AST walk scope + schema column grep | VERIFIED | `SCANNER_DIRS` contains `quirk/auth`; `test_no_credential_column_in_schema` reads `quirk/db.py` |
| `run_scan.py` `mark_job_failed` | `safe_str(exc)` | scrub before DB persistence (CR-04) | VERIFIED | Line 1982: `f"{type(exc).__name__}: {safe_str(exc)}"` |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `tests/test_credential_leakage.py` | `SENTINEL` → DB row text columns | `CredentialContext.from_cli()` via env var | Yes — real CredentialContext seeded via env var; `safe_str()` scrubs scan_error before write | FLOWING |
| `quirk/auth/credentials.py` `as_headers()` | `_secret_buf.decode("utf-8")` | bytearray seeded by `_resolve_reference()` | Yes — real secret from env/file/getpass | FLOWING |
| `quirk/scanner/jwt_scanner.py` `_fetch_jwks` | `_hdrs`/`_query` | `cred_ctx.as_headers()` / `cred_ctx.query_param()` | Yes — flows from caller's CredentialContext | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| CredentialContext unit tests green | `python3 -m pytest tests/test_credential_context.py -q` | 22 passed | PASS |
| Scrubbing + gate tests green | `python3 -m pytest tests/test_safe_exc.py tests/test_scan_error_gate.py tests/test_credential_leakage.py -q` | 53 passed | PASS |
| JWT scanner tests green | `python3 -m pytest tests/test_jwt_scanner.py -q` | 11 passed | PASS |
| All Phase 93 test suites combined | `python3 -m pytest tests/test_credential_context.py tests/test_safe_exc.py tests/test_scan_error_gate.py tests/test_credential_leakage.py tests/test_jwt_scanner.py -q` | 86 passed | PASS |
| Error codes freshness gate | `python3 -m pytest tests/test_error_codes_freshness.py -q` | 3 passed | PASS |
| `format_error('SCHED-AUTH-001')` contains error code | `python3 -c "from quirk.errors import format_error; assert 'QRK-SCHED-AUTH-001' in format_error('SCHED-AUTH-001')"` | exit 0 | PASS |
| `ConnectorsCfg().enable_authenticated_mode` defaults False | `python3 -c "from quirk.config import ConnectorsCfg; assert ConnectorsCfg().enable_authenticated_mode is False"` | exit 0 | PASS |
| D-14: no `quirk.scanner.*` imports in credentials.py | `grep "from quirk.scanner\|import quirk.scanner" quirk/auth/credentials.py` | empty | PASS |
| LEAK-03: `safe_str` imported in credentials.py | `grep -q "from quirk.util.safe_exc import safe_str" quirk/auth/credentials.py` | found at line 28 | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AUTH-01 | 93-01, 93-03 | Bearer/API-key (header+query)/Basic via CLI/env/prompt | SATISFIED | All 4 argparse flags wired; `from_cli()` resolves all reference types; JWT scanner accepts `cred_ctx=`; 22 unit tests + 11 jwt tests GREEN |
| AUTH-02 | 93-03 | Credentials never persisted | SATISFIED | 25-test sentinel suite GREEN; CR-02 + CR-04 fixes prevent raw cred in log/DB; `_strip_auth_from_log` + CR-01 fix prevent header/URL cred in httpx log |
| AUTH-03 | 93-02 | Schedule add rejects authenticated-mode configs | SATISFIED | `_config_has_authenticated_mode()` + `sys.exit(2)` with QRK-SCHED-AUTH-001; 14 scan_error_gate tests GREEN |
| AUTH-04 | 93-03 | Security-review gate deliverable | SATISFIED | `93-SECURITY-REVIEW-GATE.md` present; 11 surfaces audited; best-effort caveat stated; D-07 gate declared |
| AUTH-05 | 93-02 | `safe_str()` + AST gate extended to API-key/token shapes | SATISFIED | 4 new `_SENSITIVE_PATTERNS`; `CREDENTIAL_FIELD_NAMES` AST gate; `quirk/auth` in SCANNER_DIRS; schema column gate; positive+negative self-tests |

**Tracking Gap (non-blocking):** All five AUTH rows in `.planning/REQUIREMENTS.md` still show `[ ]` (Pending) in both the checkbox section (lines 28-32) and the progress table (lines 90-94). The implementation is complete and tests are GREEN — this is a bookkeeping-only gap that the orchestrator must close by flipping the rows to `[x]` / `Complete`.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TBD/FIXME/XXX/PLACEHOLDER markers found in Phase 93 modified files | — | — |

No debt markers, empty implementations, or hardcoded stubs found in any Phase 93 modified file. The deferred items from `93-03-SUMMARY.md` (WR-02 through WR-06, IN-02) are code-review warnings explicitly scheduled for v5.1 hardening — they are not blocking and are documented design-judgment items, not unresolved debt markers.

---

## Human Verification Required

### 1. Interactive getpass prompt path

**Test:** Run `quirk --config config.yaml --auth-bearer` (bare flag, no REF value) against a local JWT endpoint in the chaos lab
**Expected:** Terminal displays a `getpass`-style prompt ("Bearer token: "); entering a token value causes the scan to complete without error; the JWT scanner attaches the Bearer header to JWKS probe requests
**Why human:** Requires a real TTY attached to the process; cannot be triggered programmatically. The unit tests verify the `"PROMPT"` const flows into `_resolve_reference` which calls `getpass.getpass()`, but the interactive behavior itself requires a human session.

### 2. Live PDF export is credential-free

**Test:** Perform an authenticated scan with `--auth-bearer @token.txt`, then export the PDF report from the dashboard
**Expected:** The downloaded PDF does not contain the bearer token value
**Why human:** The automated sentinel test (`test_sentinel_not_in_pdf_export_surface`) asserts on the shared CBOM-JSON upstream source rather than running a live Playwright render (requires a running server + Chromium). The upstream is proven clean by the automated suite, but a live PDF render is the final confirmation that the renderer introduces no new credential-exposure path.

---

## Deferred Items

None — all phase must-haves verified. The REQUIREMENTS.md tracking row update (AUTH-01..05 `[ ]` → `[x]`) is a bookkeeping task for the orchestrator, not a verification gap.

---

## Gaps Summary

No gaps. All 5 success criteria verified against the codebase. The 4 BLOCKER defects from the code review (commit 624f55a) are confirmed fixed. The deferred code-review warnings (WR-02 through WR-06, IN-02) are design-judgment items explicitly tracked for v5.1 hardening — none block the phase goal.

The only outstanding item is the REQUIREMENTS.md tracking state: AUTH-01..05 rows still show `Pending` / `[ ]`. This must be closed by the orchestrator but does not affect phase goal achievement.

---

_Verified: 2026-05-23T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
