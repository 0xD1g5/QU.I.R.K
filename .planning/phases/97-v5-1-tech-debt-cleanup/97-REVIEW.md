---
phase: 97-v5-1-tech-debt-cleanup
reviewed: 2026-05-23T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - quirk/auth/credentials.py
  - quirk/cli/schedule_cmd.py
  - quirk/scanner/jwt_scanner.py
  - quirk/scanner/rest_fuzzer.py
  - tests/test_rest_fuzzer_cascade.py
  - tests/test_jwt_scanner.py
  - tests/test_schedule_auth_reject.py
  - tests/test_credential_leakage.py
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 97: Code Review Report

**Reviewed:** 2026-05-23
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 97 closes credential-handling design-judgment items (TD-01, TD-02) deferred
from reviews 93/96. The four production diffs (credential docstring fix, parse-based
scheduler auth check with SQLite carve-out, JWT pre-existing-param guard, REST fuzzer
combined cascade counter) are largely sound and faithful to the locked decisions
(D-01..D-06, D-11). Intentional accepted tradeoffs under D-05 (best-effort
zeroization / str-copy) were not flagged.

The review surfaces no Critical issues. Four Warnings concern correctness gaps that
the new code itself introduces or leaves: a malformed-URL path-append in the JWT
fetcher that the WR-04 guard partially masks, a silent swallow of the WR-04 reject
in `_fetch_jwks`, an under-tested cascade-reset semantic in the alg-confusion path,
and a leak-test that still asserts on test-scrubbed data while claiming real-path
coverage. Four Info items cover dead/duplicated code and a SQLite carve-out edge.

## Warnings

### WR-01: JWT fetch appends path AFTER query string, producing a malformed URL

**File:** `quirk/scanner/jwt_scanner.py:147,169`
**Issue:** `_fetch_jwks` does `base_url = base_url.rstrip("/")` then `url = base_url + path`
for each JWKS path. When `base_url` already carries a query string (e.g. an operator
target `https://h1.example.com?api_key=PROBED`), the discovery path is concatenated
*after* the query, yielding `https://h1.example.com?api_key=PROBED/.well-known/jwks.json`.
The `?api_key=...` value becomes `PROBED/.well-known/jwks.json` and the intended JWKS
path is never actually probed. The new WR-04 guard in `_append_query_param` happens to
trip on the `api_key` token and reject, which *masks* the malformed-URL behavior in the
one tested case — but for a base URL carrying a non-key query param (e.g. `?tenant=acme`),
the malformed URL is fetched as-is and discovery silently fails.
This is the actual realism gap behind `test_append_query_param_continue_iteration_skips_conflicting_target`
(jwt_scanner test:307), which only passes because the guard fires, not because the path is well-formed.
**Fix:** Build the probe URL via `urllib.parse` so the path is inserted before the query,
e.g.:
```python
from urllib.parse import urlparse, urlunparse
_p = urlparse(base_url)
url = urlunparse(_p._replace(path=_p.path.rstrip("/") + path))
```
or document that `base_url` must be scheme+host only (no query/path) and validate it.

### WR-02: WR-04 reject is silently swallowed by the broad `except Exception: continue` in `_fetch_jwks`

**File:** `quirk/scanner/jwt_scanner.py:157,216-217`
**Issue:** `_append_query_param` raises `ValueError` to reject a target that already
carries a key param (D-03). That call sits inside `_get`, which is invoked at line 188
inside the `try: ... except Exception: continue` block (216-217). The `ValueError` is
therefore caught and swallowed per-path: `_fetch_jwks` returns `(None, None, fetched_urls)`
and `scan_jwt_endpoint` returns `[]`. The only operator-visible signal is the `logger.warning`
emitted inside `_append_query_param`; the caller (`scan_jwt_targets`) cannot distinguish
"target rejected for safety" from "endpoint had no JWKS." The CONTEXT (D-03) intent is to
"reject the target with a clear message" and "skip (continue) the affected target" — the
skip works, but the rejection is indistinguishable from a normal miss at the caller level.
**Fix:** Let the `ValueError` propagate past the per-path `except` (e.g. catch it explicitly
before the broad handler and `raise`, or special-case it in `scan_jwt_targets` so the
target is logged as rejected rather than empty):
```python
except ValueError:
    raise  # D-03 reject must not be masked as "no JWKS found"
except Exception:
    continue
```

### WR-03: Alg-confusion cascade reset diverges from documented "reset only on genuine success"

**File:** `quirk/scanner/rest_fuzzer.py:697-700`
**Issue:** D-06 specifies the combined `consecutive_failures` counter resets "only on a
genuine success response." In the alg-confusion branch the reset is `consecutive_failures = 0`
for any `alg_status < 500`. But the forged-token request is *expected* to be rejected by a
non-vulnerable server with 401/403 — that is the normal, healthy outcome, yet it is treated
as a "success" that resets the back-off counter. A server that is degrading (timeouts on real
ops) but still cheaply returns 401 to the forged probe will have its cascade counter reset on
every alg-confusion iteration, defeating the very back-off TD-02 strengthens. The main-path
reset (line 639) has the same `< 500` semantics, which is defensible for real ops, but the
alg-confusion path piggybacks on the same per-endpoint iteration and can reset between real
dispatches. There is also no regression test covering interleaved alg-confusion responses and
the cascade counter (the three cascade tests all run `run_alg_confusion=False`).
**Fix:** Either exclude 4xx-on-forged-token from the reset (only 2xx/3xx should reset, since a
4xx here is the *negative* security result, not a health signal), or do not let the
alg-confusion branch reset the counter at all and leave reset solely to the main dispatch path.
Add a test exercising the alg-confusion path's interaction with the cascade counter.

### WR-04: PDF leak test claims a "surface" but asserts on test-scrubbed CBOM data, not the renderer

**File:** `tests/test_credential_leakage.py:330-389`
**Issue:** Per D-04/WR-05 the goal was to route at least one surface through the *real*
write/scrub path. `test_sentinel_not_in_scan_error_json` (145-185) does this correctly
(real `_scan_one_fallback`, no `safe_str` in the test body). However
`test_sentinel_not_in_pdf_export_surface` still constructs `scan_error=safe_str(Exception(...))`
in the test body (line 376) and asserts the sentinel is absent from CBOM JSON — i.e. it
asserts on data the test itself scrubbed. The docstring is honest that this is a "DOCUMENTED
COVERAGE GAP" and not a live render, which satisfies the letter of D-04 ("mark the PDF
assertion explicitly as a documented coverage gap"). The residual risk: the module docstring
(line 8) and the suite still advertise "11 stored/rendered surfaces" as if mechanically
verified, and this test name reads like coverage. A regression that injected an unscrubbed
value into the PDF print-route template (not the CBOM JSON) would not be caught.
**Fix:** Rename to make the non-coverage explicit (e.g. `test_pdf_upstream_linkage_documented`)
and update the module docstring (line 8) to state how many surfaces are *mechanically* verified
vs. linkage-only, so the suite does not overstate the security control.

## Info

### IN-01: Duplicated cascade-break block across main and exception paths

**File:** `quirk/scanner/rest_fuzzer.py:617-622,631-637`
**Issue:** The "increment + check `_CONSECUTIVE_5XX_LIMIT` + log + break" logic is duplicated
verbatim across the exception handler and the 5xx handler, with a third partial copy in the
alg-confusion branch. Divergence risk if the threshold semantics change again.
**Fix:** Extract a small helper, e.g. `_register_failure(count) -> (count, should_break)`.

### IN-02: `bearer_declared_alg` uses a broad `except Exception` that can hide import errors

**File:** `quirk/auth/credentials.py:101-109`
**Issue:** The `try` block wraps both `import jwt` and the decode. A missing PyJWT install
(core dep, but minimal installs drift per the optional-extra trap noted in project memory)
returns `None` silently, indistinguishable from "opaque token." Low impact since PyJWT is a
core dep, but the conflation makes diagnosis harder.
**Fix:** Catch the import separately, or narrow to `(jwt.InvalidTokenError, ValueError, KeyError)`
for the decode.

### IN-03: SQLite carve-out reads only 16 bytes and trusts the magic without size check

**File:** `quirk/cli/schedule_cmd.py:50-57`
**Issue:** A YAML config whose first 16 bytes happen to equal `b"SQLite format 3\x00"` (effectively
impossible by accident, but the check is content-sniff not extension-bound) would be allowed
without the auth check. This is acceptable given the carve-out's purpose and the near-zero
collision probability, but a 0-15 byte file returns fewer than 16 bytes and the `==` is simply
False (falls through to YAML), which is correct. Noting for completeness — no change required
beyond a comment that short reads fall through intentionally.
**Fix:** Optional: add a brief comment that a short read (<16 bytes) deliberately falls through
to the YAML attempt.

### IN-04: `_resolve_db_path` docstring still says YAML parsing is "deferred" — now contradicted

**File:** `quirk/cli/schedule_cmd.py:80-82`
**Issue:** `_resolve_db_path`'s docstring states "YAML config file parsing is deferred (not needed
for SCHED-01 scope)." Phase 97 now does parse YAML in `_config_has_authenticated_mode` on the same
`--config` arg. The two functions consume the same overloaded `--config` value with opposite
assumptions (one treats it as a DB path, the other YAML-sniffs it). The docstring is now stale and
the overload is a latent footgun for future maintainers.
**Fix:** Update the docstring to note that `--config` is overloaded (DB path AND auth-config sniff
target) and cross-reference `_config_has_authenticated_mode`.

---

_Reviewed: 2026-05-23_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
