---
phase: 94-openapi-bearer-token-analysis
reviewed: 2026-05-22T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - quirk/cli/analyze_token_cmd.py
  - quirk/scanner/openapi_scanner.py
  - quirk/cbom/builder.py
  - quirk/intelligence/scoring.py
  - quirk/intelligence/evidence.py
  - run_scan.py
  - pyproject.toml
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
status: issues_found
---

# Phase 94: Code Review Report

**Reviewed:** 2026-05-22
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 94 adds passive OpenAPI/JWT analysis. The security-critical paths I was asked to scrutinize are **correctly implemented**:

- The `$ref` SSRF guard pre-scans ALL `$ref` values recursively (verified nested dict/list traversal and malformed dict-valued `$ref` both fail safe), runs BEFORE `validate()`, and the SSRF test proves `_oas_validate` and `httpx.get` are never called.
- The 10 MB gate is applied BEFORE `yaml.safe_load` on the file path (read of `MAX_SPEC_BYTES + 1`), verified by `test_oversize_rejected` mocking `yaml.safe_load`.
- The SPEC-02 scope gate fires before any network request.
- `alg:none` detection is case-insensitive across `none/None/NONE/NonE` (header-dict value, not raw string search); the raw token is never printed or persisted; opaque tokens exit 0.
- `SCORE_WEIGHTS` sum is 293.0 and count is 39 — consistent with the invariant test.
- Graceful degradation (`OPENAPI_AVAILABLE=False`) returns a `missing_extra` endpoint without raising and without reaching any parse path.
- `[api]` (with `openapi-spec-validator` / `schemathesis`) is correctly excluded from `[all]`.

However, the URL-based spec fetch path is functionally broken (CR-01), and several SCORE-01 / TOKEN-02 wiring elements are dead because no producer emits `BEARER_TOKEN` endpoints.

## Critical Issues

### CR-01: OpenAPI URL scope gate can never match — all `--openapi-spec <URL>` fetches are rejected

**File:** `quirk/scanner/openapi_scanner.py:140`, `run_scan.py:1363-1367`
**Issue:** The scope gate compares a full URL against bare FQDNs:
```python
if not any(url.startswith(t.rstrip("/")) for t in (cfg_targets or [])):
    raise SpecParsingError(... "outside configured scan-target scope" ...)
```
`run_scan.py:1365` populates `cfg_targets` from `cfg.targets.fqdns`, which are bare hostnames (`api.example.com`), not full URLs. A spec URL `https://api.example.com/openapi.yaml` will never `startswith("api.example.com")`, so every URL spec is rejected as out-of-scope. URL-based OpenAPI scanning (a stated SPEC-02 capability) is dead in production. It fails closed (no SSRF), but the feature does not work. The unit test `test_url_scope_rejected` passes a full-URL `cfg_targets` (`["https://safe.example.com"]`), so it never exercises the real `fqdns` shape and masks the defect.
**Fix:** Normalize both sides before comparison — derive the host from the URL and match against `fqdns`, e.g.:
```python
from urllib.parse import urlparse
url_host = urlparse(url).hostname or ""
targets = cfg_targets or []
in_scope = any(
    url_host == t or url_host.endswith("." + t)
    or url.startswith(t.rstrip("/"))   # keep prefix match for full-URL targets
    for t in targets
)
if not in_scope:
    raise SpecParsingError(...)
```
Add a test that passes bare-FQDN `cfg_targets` (the real shape) for an in-scope URL and asserts the fetch proceeds.

## Warnings

### WR-01: `--allow-internal-targets` is not propagated to the OpenAPI URL fetch

**File:** `quirk/scanner/openapi_scanner.py:148`
**Issue:** `validate_external_url(url)` is called with the default `allow_internal=False`. The CLI flag `--allow-internal-targets` (run_scan.py:623) is never threaded into `scan_openapi_spec`. Per project MEMORY, the chaos lab binds loopback and requires `--allow-internal-targets`; an in-scope loopback/private spec URL will be rejected even when the operator explicitly allowed internal targets. Combined with CR-01, URL fetch is doubly non-functional against the lab.
**Fix:** Add an `allow_internal: bool = False` parameter to `scan_openapi_spec`/`_fetch_spec_bytes_from_url`, pass it to `validate_external_url(url, allow_internal=allow_internal)`, and wire `cfg.security.allow_internal_targets` from `run_scan.py:1366`.

### WR-02: BEARER_TOKEN evidence/CBOM/score paths are dead — no producer emits the protocol

**File:** `quirk/intelligence/evidence.py:306-312`, `quirk/cbom/builder.py:441-449`, `quirk/intelligence/scoring.py:226-233`
**Issue:** No code anywhere creates a `CryptoEndpoint(protocol="BEARER_TOKEN")` (grep across `quirk/` and `run_scan.py` finds it only in the consumers). `analyze-token` is a standalone print-only command and never produces an endpoint. Consequently `bearer_token_weak_alg_count` is always 0 and the `agility_weak_jwt_alg_ratio` SCORE-01 weight (6.0) can never fire in a real scan. The TOKEN-02 CBOM branch is exercised only by a hand-built `FakeEndpoint` in tests. This is a wiring gap: the feature is half-built.
**Fix:** Either wire `analyze-token` (or a scan phase) to emit a `BEARER_TOKEN` endpoint into the evidence/CBOM pipeline, or explicitly document the branch as scaffolding for a later phase and remove the score weight until a producer exists (so the invariant sum/count reflects live signals).

### WR-03: OpenAPI evidence counter has a dead `http-server` branch and relies on a fragile substring

**File:** `quirk/intelligence/evidence.py:319-321`
**Issue:** The counter checks `"http-server" in _oa_detail or "plaintext" in _oa_detail`, but the scanner only ever sets `service_detail="plaintext_server"` (openapi_scanner.py:279). The `"http-server"` branch is dead code, and the comment ("sets service_detail to 'http-server' or similar") is wrong. The counter happens to work only because `"plaintext_server"` contains the substring `"plaintext"`. Any future rename of the scanner detail string silently breaks the SCORE-01 signal with no test catching it (the existing test asserts `>= 1` via the same coincidental substring).
**Fix:** Match the actual contract value: `if _oa_detail == "plaintext_server":` (or define a shared sentinel constant imported by both modules). Remove the misleading `http-server` branch and comment.

### WR-04: URL fetch buffers the full response before the 10 MB gate

**File:** `quirk/scanner/openapi_scanner.py:155-164`
**Issue:** `resp = httpx.get(...)` followed by `len(resp.content) > MAX_SPEC_BYTES` reads the entire body into memory before the size check. An in-scope (or, until CR-01 is fixed, would-be in-scope) server can stream an arbitrarily large response and exhaust memory before the gate rejects it. The file path correctly reads only `MAX_SPEC_BYTES + 1`; the URL path does not get the same protection.
**Fix:** Stream the response and abort once the cap is exceeded:
```python
with httpx.stream("GET", url, timeout=15, follow_redirects=True) as resp:
    resp.raise_for_status()
    buf = bytearray()
    for chunk in resp.iter_bytes():
        buf += chunk
        if len(buf) > MAX_SPEC_BYTES:
            raise SpecParsingError("Fetched spec content exceeds 10 MB limit.")
    return bytes(buf)
```

### WR-05: JWT with a missing `alg` header is not flagged as critical

**File:** `quirk/cli/analyze_token_cmd.py:80,97`
**Issue:** When the header has no `alg` key, `alg = ""`, `is_alg_none = "".lower() == "none"` is `False`, and the token reports `alg="UNKNOWN"`, exit 0. A JWT that omits `alg` is essentially as forgeable as `alg:none` (servers that default to no verification accept it). The tool downgrades this to a benign "UNKNOWN" instead of warning. Verified: a header `{"typ":"JWT"}` yields `is_alg_none=False`.
**Fix:** Treat a JWT-shaped token (valid header parse) with absent/empty `alg` as a HIGH/CRITICAL signal, or at minimum emit an explicit warning that the algorithm is undeclared and the token cannot be trusted.

## Info

### IN-01: `_decode_token` swallows claims-decode failures silently

**File:** `quirk/cli/analyze_token_cmd.py:92-94`
**Issue:** A `DecodeError` during `jwt.decode` is caught and claims set to `{}` with no indication to the user that the payload could not be decoded (e.g. corrupt base64 payload on an otherwise valid header). Expiry and any claim-derived output silently report as absent.
**Fix:** Set a flag (e.g. `claims_decode_failed=True`) and surface a one-line notice in the human/JSON output so the operator knows the payload was unreadable.

### IN-02: Duplicated inline `from urllib.parse import urlparse` imports

**File:** `quirk/scanner/openapi_scanner.py:232,270`
**Issue:** `urlparse` is imported twice inside loops in `extract_crypto_posture`. Minor style/clarity issue; the import is cheap but cluttered.
**Fix:** Hoist `from urllib.parse import urlparse` to module top.

### IN-03: `_fetch_spec_bytes_from_url` ignores `Content-Type`/charset and trusts redirects

**File:** `quirk/scanner/openapi_scanner.py:155`
**Issue:** `follow_redirects=True` with no cap; the scope/SSRF check is applied to the original URL only, not to the final redirect target. A redirect to an out-of-scope or metadata host would bypass the scope gate (the `validate_external_url` check also runs only on the initial URL). Lower priority because CR-01 currently blocks all URL fetches, but it becomes live once CR-01 is fixed.
**Fix:** Either set `follow_redirects=False`, or re-validate the final `resp.url` against the scope gate and `validate_external_url` after the request completes.

---

_Reviewed: 2026-05-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
