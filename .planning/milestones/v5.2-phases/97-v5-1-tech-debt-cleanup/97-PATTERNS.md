# Phase 97: v5.1 Tech-Debt Cleanup — Pattern Map

**Mapped:** 2026-05-23
**Files analyzed:** 5 modified files (no new files)
**Analogs found:** 5 / 5 (all are self-analogs — each file's surrounding code is the pattern)

---

## File Classification

| Modified File | Role | Data Flow | Change Type | Closest Analog Region |
|---|---|---|---|---|
| `quirk/auth/credentials.py` | utility/auth | request-response | docstring + comment (D-01, D-02) | same file: `_resolve_reference` env-var block (lines 206-222) |
| `quirk/scanner/jwt_scanner.py` | scanner | request-response | pre-existing-param guard (D-03) | same file: `_strip_auth_from_log` redaction pattern (lines 35-56) |
| `tests/test_credential_leakage.py` | test | CRUD/write-path | real-path injection for ≥1 surface (D-04) | same file: `test_sentinel_not_in_db_row` (lines 161-226) |
| `quirk/cli/schedule_cmd.py` | CLI/middleware | request-response | parse-based auth detection replacing extension heuristic (D-05) | same file: surrounding `_config_has_authenticated_mode` (lines 24-46) |
| `quirk/scanner/rest_fuzzer.py` | scanner | event-driven | combined failure counter (D-06) | same file: WR-04 per-op try/except+continue (lines 570-577) |

---

## Pattern Assignments

### `quirk/auth/credentials.py` — D-01 (WR-02) and D-02 (WR-03)

**Change:** Correct the `from_cli` docstring env-var description (D-01); add a comment
to `as_headers`/`query_param` acknowledging the per-call str-copy proliferation (D-02).

**Analog — env-var block the docstring describes** (`_resolve_reference`, lines 206-210):
```python
    # 3. Env-var name → read and delete (prevents subprocess inheritance)
    if ref in os.environ:
        raw = os.environ[ref]
        del os.environ[ref]
        return raw
```
The env-var check uses `ref in os.environ` — no `isupper()` guard. The docstring in
`from_cli` (lines ~129) currently says "all-caps"; correct it to "any name present in
the environment is read and deleted."

**Analog — str-only-at-injection comment style** (`as_headers`, line 54):
```python
    def as_headers(self) -> dict[str, str]:
        """Materialize auth headers — str only at injection boundary (D-04).

        Returns {} for api_key_query scheme; query placement via query_param() (D-03).
        """
        secret = self._secret_buf.decode("utf-8")
```
For D-02: add a comment directly above `secret = self._secret_buf.decode("utf-8")` in
both `as_headers` (line 58) and `query_param` (line 76) documenting the accepted
proliferation and call-count bound. Follow the `# comment (decision-tag)` style already
present on line 65 (`# api_key_query: secret goes on query string, never in headers (D-03)`).

**Module-level docstring enforcement block** (lines 3-6) — the "Decision enforcement"
block pattern to copy if adding a D-02 entry at the top:
```python
"""Ephemeral credential context for QU.I.R.K. authenticated scans (Phase 93).

Decision enforcement:
  D-04: Secret stored as bytearray; zeroed in close()/finally block.
  D-05: Zeroization is best-effort — Python GC may retain heap copies.
  D-14: Zero imports from quirk.scanner.* to prevent circular deps.
```

---

### `quirk/scanner/jwt_scanner.py` — D-03 (WR-04)

**Change:** `_append_query_param` (lines 59-69) silently overwrites a pre-existing
same-named param. Add a guard: detect pre-existing param → reject/skip with a scrubbed
log message instead of overwriting.

**Target function** (lines 59-69):
```python
def _append_query_param(url: str, param_name: str, param_value: str) -> str:
    """Append a query parameter to a URL string.

    Phase 93 / D-03: query-param key placement — secret goes on the URL query
    string, never in a header.
    """
    parsed = urlparse(url)
    existing = parse_qs(parsed.query, keep_blank_values=True)
    existing[param_name] = [param_value]   # ← silently overwrites; fix here
    new_query = urlencode(existing, doseq=True)
    return urlunparse(parsed._replace(query=new_query))
```

**Pattern — scrubbed log message style** (lines 584-589 of rest_fuzzer.py, same project):
```python
            logger.warning(
                "Fuzz target URL rejected by scope gate (%s): %s",
                scope_result.reason,
                safe_str(url),
            )
            continue  # skip — no budget consumed
```
Apply same `logger.warning(...)` + `safe_str(url)` pattern for the reject message in
`_append_query_param`. The function currently returns a `str`; after the fix it must
signal failure. Options: raise `ValueError`, return `None` (change signature to
`Optional[str]`), or have callers pass a flag. Planner chooses; the caller's loop must
`continue` on rejection (see WR-04 integration note below).

**`_KEY_PARAM_NAMES` constant** (lines 30-32) — already defined in this file; reference
it in the pre-existing-param check rather than hard-coding param names:
```python
_KEY_PARAM_NAMES = frozenset({
    "api_key", "apikey", "key", "token", "auth_token", "access_token",
})
```

**`safe_str` import** (line 25) — already present:
```python
from quirk.util.safe_exc import safe_str
```

**Caller integration note:** `_append_query_param` is called in the target-list
iteration upstream of the JWT scanner dispatch. A rejected target must `continue` to the
next target, not abort. The same `try/except + continue` pattern applies (see rest_fuzzer
analog below).

---

### `tests/test_credential_leakage.py` — D-04 (WR-05)

**Change:** Route ≥1 sentinel surface through the real scanner/scrub path rather than
asserting data already pre-scrubbed by the test. Mark the PDF test explicitly as a
documented coverage gap.

**Current PDF test** (lines 303-356) — the test to update with a coverage-gap docstring:
```python
def test_sentinel_not_in_pdf_export_surface(tmp_path) -> None:
    """AUTH-02 / SC-2: sentinel must not appear in the PDF export surface.
    ...
    NOTE: A live Playwright PDF render is not performed here because it requires
    a running server + Playwright Chromium install. The upstream-linkage approach
    satisfies SC-2 per the plan: "assert on that exact upstream data source explicitly
    AND document the linkage in the test (a comment naming the shared CBOM-JSON/DB
    column the PDF reads from)".
    """
    ...
    # scan_error would carry a safe_str-scrubbed message; SENTINEL absent
    scan_error=safe_str(Exception(f"Bearer {SENTINEL}")),  # ← pre-scrubbed; not real path
```

**Current scan_error JSON test** (lines 145-158) — current test pre-scrubs via safe_str
before constructing the endpoint; the real path must instead build a `CryptoEndpoint`
with `scan_error` populated by the actual exception handler:
```python
def test_sentinel_not_in_scan_error_json() -> None:
    """AUTH-02 / D-06: sentinel in a CryptoEndpoint scan_error must not appear in json.dumps output."""
    from quirk.models import CryptoEndpoint

    # scan_error is written via safe_str in _wrapped_phase; safe_str must scrub it
    scrubbed = safe_str(Exception(f"Authorization: Bearer {SENTINEL}"))  # ← pre-scrubbed here
    ep = CryptoEndpoint(
        host="example.com",
        port=443,
        protocol="JWT",
        scan_error=scrubbed,
    )
    dumped = json.dumps({"scan_error": ep.scan_error})
    assert SENTINEL not in dumped, f"Sentinel leaked into JSON scan_error: {dumped!r}"
```

**Best existing real-path test analog** — `test_sentinel_not_in_db_row` (lines 161-226)
already exercises the real `CredentialContext.from_cli` + `safe_str` path + DB write/read
cycle. Use it as the structural template for the new real-path test:
```python
def test_sentinel_not_in_db_row(tmp_path) -> None:
    ...
    # Build a real CredentialContext with SENTINEL as the secret via env var
    os.environ["_QUIRK_SENTINEL_TEST_ENV"] = SENTINEL
    try:
        ctx = CredentialContext.from_cli(api_key_query="_QUIRK_SENTINEL_TEST_ENV")
    finally:
        os.environ.pop("_QUIRK_SENTINEL_TEST_ENV", None)

    assert ctx is not None

    # Simulate what _wrapped_phase would write: scan_error routed via safe_str.
    error_text = safe_str(Exception(f"https://api.example.com?api_key={SENTINEL}"))

    ep = CryptoEndpoint(
        host="jwt.example.com",
        ...
        scan_error=error_text,   # ← safe_str applied, then stored — real path
        ...
    )
```
The target for the new real-path surface is `scan_error` populated via
`safe_str(exc)` from a `CryptoEndpoint` whose exception is raised by a real
scanner path — not constructed manually. Build a `CryptoEndpoint` whose
`scan_error` is set by calling the real JWT scanner's exception handler
(or the `_wrapped_phase` equivalent) with a SENTINEL-bearing input,
then assert the sentinel is absent from `json.dumps({"scan_error": ep.scan_error})`.

**SENTINEL constant** (line 38) — reuse unchanged:
```python
SENTINEL = "QUIRK_SENTINEL_CRED_d41d8cd9"
```

---

### `quirk/cli/schedule_cmd.py` — D-05 (WR-06)

**Change:** `_config_has_authenticated_mode` (lines 24-46) returns `False` for any path
not ending `.yml`/`.yaml` (line 33), bypassing the security control for auth configs at
unconventional paths. Replace the extension gate with: attempt YAML parse for any
existing file; reject on parse-as-dict-with-auth-flag; fail-closed when the file cannot
be definitively classified as non-authenticated.

**Current function** (lines 24-46 — full target):
```python
def _config_has_authenticated_mode(config_path: str | None) -> bool:
    """Return True if the YAML config at config_path has connectors.enable_authenticated_mode set truthy.

    Uses yaml.safe_load only — does NOT import load_config to avoid pulling in scanner deps.
    Returns False if config_path is None, missing, not YAML, or the key is absent/falsy.
    """
    if config_path is None:
        return False
    # Only attempt YAML parse if the path looks like a config file (not a .db path)
    if not config_path.endswith((".yml", ".yaml")):
        return False                            # ← BUG: extension gate bypasses security control
    try:
        import yaml  # stdlib-safe: PyYAML is a base dependency of quirk
        with open(config_path, encoding="utf-8") as fh:
            data: Any = yaml.safe_load(fh)
        if not isinstance(data, dict):
            return False
        connectors = data.get("connectors")
        if not isinstance(connectors, dict):
            return False
        return bool(connectors.get("enable_authenticated_mode", False))
    except Exception:
        return False                            # ← fail-open on parse error; consider fail-closed
```

**Pattern — fail-closed security control** (from D-11 established pattern): the fix
should treat an unclassifiable file as potentially authenticated (return `True`) so the
scheduler rejects it. Match the existing `yaml.safe_load` + `isinstance(data, dict)`
pattern; remove the extension gate; add `os.path.exists(config_path)` check before
attempting parse (skip None + non-existent paths only, not non-`.yml` paths).

**Caller** (lines 75-78) — unchanged; callers do not need to know the implementation
changed:
```python
    # T-93-09: reject authenticated-mode configs — credentials are ephemeral (D-11)
    if _config_has_authenticated_mode(args.config):
        console.print(f"[red]{format_error('SCHED-AUTH-001')}[/red]")
        sys.exit(2)
```

---

### `quirk/scanner/rest_fuzzer.py` — D-06 (TD-02)

**Change:** `consecutive_5xx` (initialized line 493, reset line 603, incremented lines
611/676, reset lines 618/678) currently resets to 0 on connection exceptions (line 603),
defeating the cascade pause for timeout-only servers. Treat exceptions as cascade signal:
increment instead of reset on exception; reset only on genuine success response.

**Counter initialization** (line 493):
```python
    consecutive_5xx = 0
```

**Exception branch — current (bug)** (lines 601-604):
```python
            except Exception as exc:
                logger.warning("Fuzz request failed: %s", safe_str(str(exc)))
                consecutive_5xx = 0   # ← BUG: resets counter, breaks cascade on timeout-only servers
                continue
```

**5xx cascade tracker — current** (lines 609-618):
```python
            # 5xx cascade tracker (FUZZ-02 guardrail 6)
            if resp_status >= 500:
                consecutive_5xx += 1
                if consecutive_5xx >= _CONSECUTIVE_5XX_LIMIT:
                    logger.warning(
                        "REST fuzzer: %d consecutive 5xx responses; pausing scan.", _CONSECUTIVE_5XX_LIMIT
                    )
                    break
            else:
                consecutive_5xx = 0
```

**Alg-confusion cascade path** (lines 674-678):
```python
                            # WR-01: alg-confusion responses feed the 5xx cascade tracker too.
                            if alg_status >= 500:
                                consecutive_5xx += 1
                            else:
                                consecutive_5xx = 0
```

**`_CONSECUTIVE_5XX_LIMIT` constant** (lines 85-86):
```python
#: Number of consecutive 5xx responses that trigger a cascade pause/abort.
_CONSECUTIVE_5XX_LIMIT: int = 3
```

**Per-operation try/except + continue pattern** (lines 570-577 — the WR-04 analog to
follow for exception handling style):
```python
            # WR-04: one malformed operation must not abort the whole fuzz loop.
            try:
                op = result.ok()
                case = op.as_strategy().example()
                kwargs = case.as_transport_kwargs(base_url=base_url)
            except Exception as exc:
                logger.debug("Skipping operation (case generation failed): %s", safe_str(str(exc)))
                continue
```

**Fix pattern to apply at lines 601-604:** Change `consecutive_5xx = 0` to
`consecutive_5xx += 1`. Add cascade-limit check immediately after (same structure as
lines 612-616) so the break fires on connection-exception cascade too. Rename the
variable to `consecutive_failures` or keep `consecutive_5xx` with broadened semantics —
planner/executor's call per CONTEXT.md Claude's Discretion.

Both cascade increment sites (main dispatch ~line 611, alg-confusion ~line 676) already
use `consecutive_5xx += 1` for 5xx responses — the exception branch is the only site
that diverges. The alg-confusion branch has no exception path of its own (it is nested
inside the outer try/except); the outer exception branch (line 601) handles all
connection-level failures uniformly, so fixing that one site is sufficient.

---

## Shared Patterns

### `safe_str` — credential-safe exception stringification
**Source:** `quirk/util/safe_exc.py` (full file, 60 lines)
**Apply to:** All new log/reject messages in WR-04 (`jwt_scanner.py`) and any new
warning messages in WR-06 (`schedule_cmd.py`). Also exercised in WR-05 real-path test.

```python
from quirk.util.safe_exc import safe_str

# Usage pattern (never pass raw exception message to logger directly):
logger.warning("Fuzz request failed: %s", safe_str(str(exc)))
logger.warning("Scope gate rejected (%s): %s", reason, safe_str(url))
```

The function strips credential-bearing content (Authorization headers, connection
strings, base64 tokens, query-param secrets) and returns class-name-only on match.
Import already present in `jwt_scanner.py` (line 25) and `rest_fuzzer.py`.

### Decision-enforcement comment style
**Source:** `quirk/auth/credentials.py` lines 3-6 (module docstring) and inline
comments (e.g. line 65 `# api_key_query: secret goes on query string, never in headers (D-03)`)
**Apply to:** All new comments in D-01/D-02 changes. Reference the decision tag
`(D-NN)` in every new comment so the rationale is traceable.

### Fail-closed security control pattern (D-11)
**Source:** `quirk/cli/schedule_cmd.py` lines 75-78 (caller) + the intent of
`_config_has_authenticated_mode` itself.
**Apply to:** WR-06 fix — when `config_path` names an existing file that cannot be
parsed or classified, return `True` (reject) rather than `False` (allow). Non-existent
paths remain `False` (nothing to parse).

### `_KEY_PARAM_NAMES` constant
**Source:** `quirk/scanner/jwt_scanner.py` lines 30-32
**Apply to:** WR-04 pre-existing-param check in `_append_query_param` — reference this
constant rather than re-listing param names inline.

---

## No Analog Found

None. All five changes modify existing files whose surrounding code provides the
authoritative pattern.

---

## Metadata

**Analog search scope:** `quirk/auth/`, `quirk/scanner/`, `quirk/cli/`, `quirk/util/`, `tests/`
**Files read:** 5 source files + 1 util file (safe_exc.py)
**Pattern extraction date:** 2026-05-23
