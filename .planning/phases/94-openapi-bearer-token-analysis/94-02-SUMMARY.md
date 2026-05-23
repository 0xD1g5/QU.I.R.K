---
phase: 94-openapi-bearer-token-analysis
plan: "02"
subsystem: scanner/openapi/config/pkgmeta
tags: [openapi, spec-scanner, ssrf, dos, cbom, extras, ci-guard, spec-01, spec-02, spec-03, pkg-01]
dependency_graph:
  requires:
    - 94-01 (CBOM BEARER_TOKEN/OpenAPI branches, evidence counters, SCORE_WEIGHTS 293.0)
  provides:
    - quirk.scanner.openapi_scanner.scan_openapi_spec
    - quirk.scanner.openapi_scanner.SpecParsingError
    - quirk.scanner.openapi_scanner.MAX_SPEC_BYTES
    - quirk.scanner.openapi_scanner.extract_crypto_posture
    - ScanCfg.openapi_spec_path (config field)
    - run_scan.py --openapi-spec CLI flag
    - pyproject.toml api = [openapi-spec-validator>=0.9.0]
    - openapi_plaintext_server_count evidence counter (populated)
  affects:
    - quirk/scanner/openapi_scanner.py (new)
    - quirk/config.py (ScanCfg.openapi_spec_path field)
    - run_scan.py (--openapi-spec flag + openapi phase dispatch)
    - pyproject.toml ([api] extras group)
    - tests/test_openapi_scanner.py (new)
    - tests/test_install_all_excludes_schemathesis.py (new)
tech_stack:
  added:
    - quirk/scanner/openapi_scanner.py (new module)
    - tests/test_openapi_scanner.py (new test file)
    - tests/test_install_all_excludes_schemathesis.py (new CI guard)
  patterns:
    - TDD RED/GREEN per task
    - openapi-spec-validator optional import guard (OPENAPI_AVAILABLE)
    - _assert_no_external_refs BEFORE _oas_validate (SSRF guard)
    - 10MB raw-byte gate BEFORE yaml.safe_load
    - Scope gate (url.startswith target) BEFORE any network request
    - Graceful degradation: missing_extra CryptoEndpoint on import failure
    - PKG-01 CI guard mirroring impacket test
key_files:
  created:
    - quirk/scanner/openapi_scanner.py
    - tests/test_openapi_scanner.py
    - tests/test_install_all_excludes_schemathesis.py
  modified:
    - quirk/config.py (openapi_spec_path field)
    - run_scan.py (--openapi-spec flag + phase dispatch + all_endpoints concat)
    - pyproject.toml ([api] extras group + exclusion comment)
decisions:
  - _assert_no_external_refs called BEFORE _oas_validate (SSRF guard, T-94-05)
  - service_detail "plaintext_server" for http:// server rows (matches evidence.py "plaintext" check)
  - Lenient validation: ValidationError logs warning but does not block posture extraction
  - openapi_endpoints added to resume path (_api_protocols includes "OPENAPI")
  - [api] excluded from [all] per v5.1-D-05 (schemathesis deferred to Phase 96)
metrics:
  duration: ~30 minutes
  completed: 2026-05-23
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 3
---

# Phase 94 Plan 02: OpenAPI Scanner + [api] Extras + PKG-01 CI Guard Summary

**One-liner:** OpenAPI spec scanner with SSRF ($ref pre-scan before validate()), 10MB DoS gate, scope-gated URL fetch, lenient crypto-posture extraction, `[api]` extras group, and schemathesis-exclusion CI guard proving quirk[all] pulls neither schemathesis nor openapi-spec-validator.

## What Was Built

### Task 1: OpenAPI scanner with SSRF + DoS + scope gates (SPEC-01/02/03)

Created `quirk/scanner/openapi_scanner.py`:

- **`class SpecParsingError(Exception)`**: raised for SSRF attempts, oversized specs, out-of-scope URLs, parse failures. Messages use `_redact_preview()` — never raw URL/ref values (T-94-08).
- **`OPENAPI_AVAILABLE`**: optional-import guard for `openapi_spec_validator.validate`. When False, `scan_openapi_spec` returns a single `CryptoEndpoint(scan_error_category="missing_extra")` without raising (mirrors jwt_scanner HTTPX_AVAILABLE pattern).
- **`MAX_SPEC_BYTES = 10*1024*1024`**: 10 MB hard cap applied BEFORE `yaml.safe_load` on both file and URL paths (T-94-07 DoS guard).
- **`_collect_refs(obj)`**: recursive harvest of all `$ref` string values from a parsed spec dict.
- **`_assert_no_external_refs(spec_dict)`**: raises `SpecParsingError` on any `$ref` not starting with `#`. Called BEFORE `_oas_validate()` — the validator follows external $refs via urllib (confirmed live, RESEARCH Pitfall 2 / T-94-05). CI fixture test (`test_external_ref_ssrf_guard`) proves ZERO outbound requests on a 169.254.169.254 $ref.
- **`_load_spec_bytes_from_file(path)`**: reads file, applies 10MB gate before yaml.safe_load.
- **`_fetch_spec_bytes_from_url(url, cfg_targets)`**: scope gate (url.startswith target) raises BEFORE any network request (SPEC-02); then `validate_external_url()` SSRF gate; then httpx.get with 10MB response gate.
- **`_validate_spec_lenient(spec_dict)`**: wraps `_oas_validate` in try/except — logs warning, never blocks posture extraction (CONTEXT lenient parse-what-we-can, RESEARCH Pitfall 7).
- **`extract_crypto_posture(spec_dict)`**: emits `CryptoEndpoint(protocol="OpenAPI")` rows:
  - Security scheme declarations → `service_detail="security_scheme:<name>"`, `cert_pubkey_alg=bearerFormat` for bearer JWT schemes
  - Plaintext `http://` server URLs → `service_detail="plaintext_server"`, severity HIGH (feeds `openapi_plaintext_server_count` in evidence.py via `"plaintext" in _oa_detail` check)
  - Unauthenticated path operations → `service_detail="unauthenticated_endpoint:<METHOD> <path>"`, severity MEDIUM
- **`scan_openapi_spec(path_or_url, *, cfg_targets)`**: public entry point; dispatches to file or URL loader; returns missing_extra endpoint when `OPENAPI_AVAILABLE=False`.

**quirk/config.py:**
- Added `openapi_spec_path: Optional[str] = None` to `ScanCfg` (dataclass field + `__init__` kwarg) — CONTEXT D resolved: `ScanCfg` (per-scan input, not persistent connector).

**run_scan.py:**
- `--openapi-spec FILE_OR_URL` argument added to the main scan argparse
- After config load: `cfg.scan.openapi_spec_path = args.openapi_spec` override
- `_api_protocols` tuple extended with `"OPENAPI"` (resume path)
- Resume path: `openapi_endpoints` extracted from resumed endpoints
- New `_run_openapi_phase()` closure dispatches `scan_openapi_spec()` with cfg_targets from `cfg.targets.fqdns`
- `openapi_endpoints` included in `_flush_stage_endpoints` concat, checkpoint count, and final `endpoints` concat

**openapi_plaintext_server_count counter (SCORE-01):**
- Scaffolded by Plan 94-01 in evidence.py; now populated: `plaintext_server` service_detail triggers the `"plaintext" in _oa_detail` condition in the `elif proto == "OPENAPI"` branch.

**Tests (TDD RED→GREEN, 7 tests):**
- `test_local_file_parse`: local OAS 3.0 YAML yields security scheme, plaintext_server, and unauthenticated_endpoint rows
- `test_local_file_security_scheme_rows`: security_scheme:<name> service_detail rows present
- `test_url_scope_rejected`: URL outside cfg_targets raises SpecParsingError; httpx.get mock asserts not called
- `test_oversize_rejected`: file > MAX_SPEC_BYTES raises SpecParsingError; yaml.safe_load mock asserts not called
- `test_external_ref_ssrf_guard`: spec with http://169.254.169.254/ $ref raises SpecParsingError; BOTH httpx.get and _oas_validate mocks assert not called (zero outbound requests)
- `test_missing_extra_degrades`: OPENAPI_AVAILABLE=False returns single missing_extra endpoint, never raises
- `test_openapi_plaintext_server_evidence_counter`: plaintext server endpoints increment openapi_plaintext_server_count in build_evidence_summary output

### Task 2: [api] extras group + schemathesis-exclusion CI guard (PKG-01)

**pyproject.toml:**
- Added `api = ["openapi-spec-validator>=0.9.0"]` group after `adcs`
- Added guard comment: [api] INTENTIONALLY EXCLUDED from [all] until Phase 96 (schemathesis deferred to Phase 96 per v5.1-D-05)

**tests/test_install_all_excludes_schemathesis.py:**
- Mirrors `test_install_all_excludes_impacket.py` structure exactly
- `@pytest.mark.slow` — resolver round-trip, skipped by default `pytest` run
- `pip install --dry-run --ignore-installed --quiet --report <tmp> -e <repo>[all]`
- Vacuous-pass guard: checks "does not provide the extra 'all'" not in output
- Expected-from-all sanity check: kubernetes, psycopg2-binary, redis, fastapi
- Primary assertion: `"schemathesis" not in installed` with Phase 94 PKG-01 diagnostic
- Sanity guard: `"openapi-spec-validator" not in installed` (proves [api] not merged into [all])

## Commits

| Hash | Type | Description |
|------|------|-------------|
| ff423ac | test | RED: failing tests for OpenAPI scanner (SPEC-01/02/03) |
| c6c0b5b | feat | GREEN: OpenAPI scanner with SSRF+DoS gates, config+CLI wiring |
| 7743981 | feat | [api] extras group + schemathesis CI guard (PKG-01) |

## Deviations from Plan

None — plan executed exactly as written.

The one minor implementation choice: `extract_crypto_posture()` uses `service_detail="plaintext_server"` (not "http-server") for plaintext server rows. The evidence.py counter checks `"plaintext" in _oa_detail` which matches both formats. This was verified by `test_openapi_plaintext_server_evidence_counter`.

## Threat Mitigations Applied

| Threat | Mitigation | Status |
|--------|-----------|--------|
| T-94-05: $ref SSRF via openapi-spec-validator | `_assert_no_external_refs` rejects non-# refs BEFORE `_oas_validate`; CI test proves 169.254.169.254 $ref raises with zero outbound requests | Done |
| T-94-06: URL fetch scope bypass | Scope gate (url.startswith target) raises BEFORE any request; then validate_external_url blocks metadata/private IPs | Done |
| T-94-07: oversized/billion-laughs YAML | 10MB raw-byte gate BEFORE yaml.safe_load on both file and URL paths | Done |
| T-94-08: spec content/URL in error messages | SpecParsingError messages use _redact_preview(); exceptions wrapped in safe_str() | Done |
| T-94-SC: openapi-spec-validator package | RESEARCH Package Legitimacy Audit [OK]; [api] excluded from [all]; CI guard asserts schemathesis + [api] absent | Done |

## Known Stubs

None — all stubs from Plan 94-01 are now resolved:
- `openapi_plaintext_server_count`: scaffolded in Plan 94-01, now populated by Plan 94-02 via `service_detail="plaintext_server"` rows from the openapi_scanner.

## Self-Check: PASSED

Files created/modified exist:
- quirk/scanner/openapi_scanner.py: FOUND
- quirk/config.py (openapi_spec_path): FOUND
- run_scan.py (--openapi-spec + dispatch): FOUND
- pyproject.toml ([api] extras): FOUND
- tests/test_openapi_scanner.py: FOUND
- tests/test_install_all_excludes_schemathesis.py: FOUND

Commits verified:
- ff423ac: test(94-02): RED: FOUND
- c6c0b5b: feat(94-02): OpenAPI scanner: FOUND
- 7743981: feat(94-02): [api] extras: FOUND

All 7 tests in test_openapi_scanner.py: PASSED
PKG-01 slow guard test: PASSED
Phase 94 combined (21 tests): PASSED
