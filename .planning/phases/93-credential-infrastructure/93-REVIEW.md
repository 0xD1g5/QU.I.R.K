---
phase: 93-credential-infrastructure
reviewed: 2026-05-22T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - quirk/auth/__init__.py
  - quirk/auth/credentials.py
  - quirk/cli/schedule_cmd.py
  - quirk/config.py
  - quirk/errors.py
  - quirk/scanner/jwt_scanner.py
  - quirk/util/safe_exc.py
  - run_scan.py
  - tests/test_credential_context.py
  - tests/test_credential_leakage.py
  - tests/test_jwt_scanner.py
  - tests/test_safe_exc.py
  - tests/test_scan_error_gate.py
findings:
  critical: 4
  warning: 6
  info: 3
  total: 13
status: issues_found
---

# Phase 93: Code Review Report

**Reviewed:** 2026-05-22
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 93 ships ephemeral-credential infrastructure for authenticated JWT/API
scanning: `CredentialContext` (bytearray-backed, zeroized in `finally`), CLI
reference-only flags, the `safe_str` scrub corpus, a scheduler reject path, and
the JWT-scanner auth wiring with an `httpx` event-hook auth-strip.

Adversarial review found **four BLOCKER-class credential-leakage / SSRF
defects**, all in the security-critical leakage surface this phase exists to
protect:

1. The event-hook auth-strip (`_strip_auth_from_log`) does **not** redact the
   query-param secret it documents redacting — the `api_key_query` secret rides
   in `request.url` and reaches every log handler and redirect intact (D-10
   violation).
2. The JWT scanner's exception logger writes the raw exception (and therefore
   the query-param-bearing URL) without `safe_str`, leaking the secret to the
   verbose log — a path the LEAK-03 AST gate does not cover (it only inspects
   `scan_error=` writes).
3. The base JWKS probe URLs are fetched **without** `validate_external_url`,
   directly contradicting the in-file comment claiming the guard "still runs on
   every JWKS URI before fetching" — an SSRF gap that is materially worse with
   credentials attached.
4. `_run_main_with_job_guard` writes the raw exception string into
   `mark_job_failed`, persisting a potentially credential-bearing message to the
   DB without `safe_str`.

The bytearray zeroization itself is correct under `BaseException` (the
`finally` block in `_run_main_with_job_guard` covers `KeyboardInterrupt` /
`SystemExit`). The scheduler-reject and `safe_str` corpus are sound.

## Critical Issues

### CR-01: Event-hook auth-strip never redacts the query-param secret it claims to redact

**File:** `quirk/scanner/jwt_scanner.py:28-38`
**Issue:** `_strip_auth_from_log` is the D-10 control that runs before any log
handler / redirect sees the request. Its docstring states it "Redacts any query
parameter whose name matches known key param names from request.url." The body
only pops three headers and **does nothing to `request.url`**. For the
`api_key_query` scheme, the secret lives entirely in the URL query string
(`?api_key=<secret>`), so it survives into httpx's request logging, any
redirect target, and exception text. This is a direct credential-leakage
regression for the exact scheme the phase added (D-03 / D-10), and no test
exercises the hook against a query-param context.

**Fix:** Rewrite the request URL inside the hook to mask known key params:
```python
from urllib.parse import urlencode, parse_qs

_REDACT_PARAMS = {"api_key", "token", "key", "auth_token"}

def _strip_auth_from_log(request) -> None:
    request.headers.pop("Authorization", None)
    request.headers.pop("X-Api-Key", None)
    request.headers.pop("X-Auth-Token", None)
    url = request.url
    qs = parse_qs(url.query.decode() if isinstance(url.query, bytes) else url.query,
                  keep_blank_values=True)
    if any(p in qs for p in _REDACT_PARAMS):
        for p in list(qs):
            if p.lower() in _REDACT_PARAMS:
                qs[p] = ["REDACTED"]
        request.url = url.copy_with(query=urlencode(qs, doseq=True).encode())
```
Note: httpx event hooks run *after* the actual request is sent, so masking
`request.url` only protects post-send logging, not the wire. Confirm the threat
model (log/redirect leakage) is what D-10 targets; if the secret must never
appear even in the sent request line, query-param auth cannot be made safe and
should be documented as such.

### CR-02: JWT scan exception logged raw — leaks query-param secret to verbose log

**File:** `quirk/scanner/jwt_scanner.py:311-313`
**Issue:** `except Exception as exc: ... logger.v(f"JWT scan error for {base_url}: {exc}")`.
When `cred_ctx` is an `api_key_query` context, the fetch URL carries
`?api_key=<secret>`. Many httpx/connection exceptions embed the request URL in
their message, so the secret lands in the verbose log in plaintext. The LEAK-03
AST gate (`tests/test_scan_error_gate.py`) only inspects `scan_error=` keyword
writes and `*.scan_error` assignments — it never sees `logger.v(...)` calls, so
this bypass is invisible to CI.

**Fix:** Route the exception through `safe_str` before logging:
```python
from quirk.util.safe_exc import safe_str
...
except Exception as exc:
    if logger:
        logger.v(f"JWT scan error for {base_url}: {safe_str(exc)}")
```
Also consider extending the LEAK-03 gate to flag f-strings interpolating a bare
exception variable into `logger.*` calls within scanner modules.

### CR-03: Base JWKS probe URLs fetched without validate_external_url (SSRF) — contradicts in-file comment

**File:** `quirk/scanner/jwt_scanner.py:129-143` (and comment at line 142)
**Issue:** The comment asserts "validate_external_url() still runs on every JWKS
URI before fetching." It does not. `validate_external_url` is only called on the
OIDC-discovery-followed `jwks_uri` (line 154). The primary probe URLs
(`base_url + path` for each of `JWKS_PATHS`) go straight into `_get()` with no
allowlist / internal-IP / metadata-service check. With credentials now attached,
an attacker-influenced or misconfigured `jwt_targets` entry can drive an
authenticated request to an internal/metadata endpoint, forwarding the bearer/
API-key secret to an unintended host. The false comment also masks the gap from
future reviewers.

**Fix:** Validate every base URL before fetching, and correct the comment:
```python
for path in JWKS_PATHS:
    url = base_url + path
    _vr = validate_external_url(url)
    if not _vr.ok:
        continue
    try:
        fetched_urls.append(url)
        resp = _get(url)
        ...
```

### CR-04: Raw exception persisted to DB via mark_job_failed without safe_str

**File:** `run_scan.py:1983`
**Issue:** `mark_job_failed(db_path, job_id, f"{type(exc).__name__}: {exc}")`
stringifies the live exception and persists it to the job row. On an
authenticated run, a credential-bearing exception (e.g. an httpx error carrying
the `?api_key=<secret>` URL, or a misconfigured connection string) writes the
secret into the database — exactly the stored-surface leak D-06/D-07 forbid.
The sentinel leak suite (`test_credential_leakage.py`) asserts on `scan_error`,
CBOM, and dashboard surfaces but never on the `ScanJob.error`/`mark_job_failed`
column, so this is uncovered.

**Fix:**
```python
from quirk.util.safe_exc import safe_str
...
if job_id and db_path:
    mark_job_failed(db_path, job_id, safe_str(exc))
```
Add a sentinel assertion against the persisted job-failure column.

## Warnings

### WR-01: get_cors_origins calls load_config() with no path argument — always raises into bare except

**File:** `quirk/config.py:490`
**Issue:** `load_config()` is defined as `def load_config(path: str)` (line 476)
and has no default. The call `cfg = load_config()` at line 490 raises
`TypeError: load_config() missing 1 required positional argument: 'path'` on
every invocation, which the `except Exception` at line 493 silently swallows.
The YAML `cors_origins` branch is therefore dead code — the function always
falls through to the hardcoded default unless `QUIRK_CORS_ORIGINS` is set. This
silently disables operator-configured CORS allowlists from YAML.

**Fix:** Resolve the config path explicitly (env/default) and pass it, or guard
the YAML branch behind a real path:
```python
path = os.environ.get("QUIRK_CONFIG_PATH")
if path:
    try:
        cfg = load_config(path)
        if cfg.security.cors_origins:
            return list(cfg.security.cors_origins)
    except Exception:
        pass
```

### WR-02: Env-var credential reference is not all-caps validated — docstring/behavior mismatch

**File:** `quirk/auth/credentials.py:148-186` (esp. 183)
**Issue:** The `from_cli` docstring (lines 104-106) says an env-var reference is
recognized when it "Looks like an env-var name (all-caps, set in environment)".
The implementation (`if ref in os.environ`) accepts *any* name present in the
environment, all-caps or not, and otherwise raises `ValueError`. A lowercase
secret accidentally passed inline that happens to collide with an existing env
var name would be silently consumed (and that env var deleted). The behavior is
defensible but the "all-caps" contract is unenforced and misleading.

**Fix:** Either enforce the documented constraint
(`if ref.isupper() and ref in os.environ:`) or correct the docstring to state
"any name present in the environment is read and deleted."

### WR-03: as_headers()/query_param() decode the secret into immortal str copies on every call

**File:** `quirk/auth/credentials.py:58, 76`
**Issue:** Each call to `as_headers()` / `query_param()` does
`self._secret_buf.decode("utf-8")`, materializing a new immutable `str` the GC
controls and `close()` cannot zero (acknowledged generally by D-05, but these
are repeatable, per-call copies). In the JWT path `as_headers()` is invoked once
per `scan_jwt_endpoint` and `query_param()` once per `_get`, so a multi-target
authenticated scan scatters many secret-bearing `str` objects across the heap
for the full scan lifetime. This widens the zeroization gap beyond the
single-construction copy.

**Fix:** Materialize the header/query dict once at the injection boundary and
pass it down, rather than re-decoding per call; or document explicitly that
str-copy proliferation is accepted under D-05 and bound the number of calls.

### WR-04: _append_query_param silently overwrites an existing same-named query param

**File:** `quirk/scanner/jwt_scanner.py:41-51`
**Issue:** `existing[param_name] = [param_value]` replaces any pre-existing value
of that param on the target URL. If a `jwt_targets` URL already contains
`?api_key=...` (e.g. a deliberately probed endpoint), the operator-supplied
value is dropped without warning. Minor correctness/operator-surprise issue;
worth a deliberate decision rather than silent overwrite.

**Fix:** Decide and document: either reject targets that already carry the param
name, or append rather than replace. If replace is intended, add a code comment
stating so.

### WR-05: Sentinel "PDF export" and "dashboard API" leak tests do not exercise the real surfaces

**File:** `tests/test_credential_leakage.py:303-356` and `:145-158`
**Issue:** `test_sentinel_not_in_pdf_export_surface` performs no PDF render — it
re-asserts the CBOM-JSON upstream and argues linkage in a comment. Likewise
`test_sentinel_not_in_scan_error_json` only checks `json.dumps` of a value the
test itself already scrubbed via `safe_str`. These tests cannot catch a
regression in the actual PDF renderer or in an unscrubbed write path; they
assert on data the test pre-sanitized. The leak suite's coverage claim
("11 stored/rendered surfaces") overstates what is mechanically verified.

**Fix:** For at least one surface, inject the sentinel through the *real*
write/scrub path (e.g. construct a `CryptoEndpoint` whose `scan_error` is set by
the actual scanner exception handler) rather than calling `safe_str` in the test
body. Mark the PDF assertion as a documented coverage gap, not coverage.

### WR-06: Scheduler auth-reject relies on a brittle .yml/.yaml extension heuristic

**File:** `quirk/cli/schedule_cmd.py:33, 24-46`
**Issue:** `_config_has_authenticated_mode` returns `False` for any config path
not ending in `.yml`/`.yaml` (line 33). `quirk schedule add --config` also
accepts raw `.db` paths and `:memory:` (per `_resolve_db_path`). An operator
who points `--config` at a YAML file lacking the extension, or who relies on
authenticated mode being on via an unconventional path, bypasses the D-11
reject and the scheduler proceeds. The reject is also keyed solely on
`enable_authenticated_mode`; a config that supplies auth another way is not
caught. Defense is shallow for a "credentials must never be persisted" control.

**Fix:** Do not gate on file extension — attempt the YAML parse for any existing
file and reject on parse-as-dict-with-flag. Consider also rejecting when the
scheduled config path cannot be definitively classified as non-authenticated.

## Info

### IN-01: Dead/unused parameter `_query_param` redaction list never centralized

**File:** `quirk/scanner/jwt_scanner.py:28-38`
**Issue:** The set of "known key param names" referenced in the docstring is not
defined anywhere; `safe_exc.py` has its own copy in a regex, and `query_param()`
defaults to `"api_key"`. The redaction param names are duplicated implicitly
across modules.
**Fix:** Define one `_KEY_PARAM_NAMES` constant and reference it from the hook,
`safe_str` patterns, and the default param name.

### IN-02: from_cli reads first matching scheme but does not warn on multiple flags

**File:** `quirk/auth/credentials.py:113-145`
**Issue:** "first non-None wins" silently ignores additional `--auth-*` flags
when more than one is supplied. The CLI help says "Only one ... may be active
(first provided wins)" but argparse `dest` ordering, not user CLI order,
determines the winner here (bearer > api_key > query > basic), which may not
match operator intent.
**Fix:** Detect >1 non-None scheme arg and raise a clear error instead of
silently choosing by hardcoded precedence.

### IN-03: Misleading comment in run_scan main()

**File:** `run_scan.py:1955-1958`
**Issue:** The comment "this sentinel is never executed — failures are caught in
the except clause" sits above live zeroization code and refers to a try/except
that is in a different function (`_run_main_with_job_guard`). Confusing for
future maintainers tracing the credential-lifecycle.
**Fix:** Remove or correct the stale comment block.

---

_Reviewed: 2026-05-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
