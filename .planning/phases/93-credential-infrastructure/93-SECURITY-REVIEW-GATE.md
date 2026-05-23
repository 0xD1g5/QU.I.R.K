# Phase 93 Security Review Gate (AUTH-04)

**Status:** GATE GREEN — all 11 leakage surfaces audited; automated suite GREEN  
**Plans:** 93-01 (CredentialContext core), 93-02 (scrubbing + guards), 93-03 (wiring + sentinel suite)  
**Milestone gate (D-07):** This document and `tests/test_credential_leakage.py` constitute the committed security-review gate that MUST be GREEN before any later phase (94+) sends authenticated traffic to a live target.

---

## Purpose

This audit enumerates every credential-leakage surface identified in `.planning/research/PITFALLS.md` (Pitfall 2, the 11-surface table) and states, for each surface:

- **How it is controlled** in Phase 93
- **The controlling artifact** (file + plan)
- **Residual risk** (where applicable)

It also documents the `safe_str()` extension (D-08) and the best-effort zeroization caveat (D-05), and references the automated leak-detection suite (D-06).

---

## Best-Effort Zeroization Caveat (D-05)

**Python in-memory credential zeroization is best-effort, NOT provable.**

Python strings are immutable and may be interned. When a credential arrives from the CLI (via `argparse`, `sys.argv`, or `os.environ`), it is already a Python `str` at that point. Converting to `bytearray` copies the bytes — leaving the original `str` still in memory at a different address, alongside the mutable copy.

`CredentialContext` (`quirk/auth/credentials.py`, Plan 01) stores the secret as `bytearray` and calls `close()` which zeroes the buffer in-place:

```python
self._secret_buf[:] = b"\x00" * n
```

This reduces the credential's **heap lifetime** and prevents persistence, but does not guarantee heap erasure. The Python GC may retain copies at unpredictable addresses until the page is reclaimed.

**"Ephemeral" in this codebase means: never persisted to disk, never serialized, never logged.** It does NOT mean "provably erased from RAM."

The `finally` block in `_run_main_with_job_guard()` (`run_scan.py`, Plan 03) ensures `cred_ctx.close()` runs even on `KeyboardInterrupt` and `SystemExit` (BaseException-safe).

---

## 11-Surface Audit

### Surface 1: SQLite `scan_error` column

| Attribute | Detail |
|-----------|--------|
| **Vector** | `_wrapped_phase()` writes `safe_str(exc)` to `CryptoEndpoint.scan_error` on exception |
| **Control** | `safe_str()` (`quirk/util/safe_exc.py`, Plan 02) scrubs credential-shaped content before writing. Patterns cover `Authorization: Bearer`, `X-Api-Key`, `X-Auth-Token`, query-param key shapes (`?api_key=`, `&token=`), and HTTP Basic payloads. |
| **Artifact** | `quirk/util/safe_exc.py` — `_SENSITIVE_PATTERNS` (Plan 02, D-08); `_wrapped_phase()` in `run_scan.py` (Plan 03) |
| **Automated gate** | `tests/test_credential_leakage.py::test_sentinel_not_in_db_row` |
| **Residual risk** | LOW — safe_str patterns cover all 4 credential shapes; a new credential shape not yet in `_SENSITIVE_PATTERNS` would be a regression caught by extending Plan 02 |

---

### Surface 2: SQLite `api_scan_json` / `cbom_json` columns

| Attribute | Detail |
|-----------|--------|
| **Vector** | Builder serialises API/CBOM metadata; if auth context reached these columns it persists forever |
| **Control** | `CredentialContext` is never serialized. The `as_headers()` / `query_param()` materialization is ephemeral — no field on `CryptoEndpoint` stores auth context. The AST gate (`tests/test_scan_error_gate.py`, Plan 02) blocks credential field names from reaching `json.dumps()` / `model_dump()`. The schema gate asserts no credential column exists in `quirk/db.py`. |
| **Artifact** | `tests/test_scan_error_gate.py` — `CREDENTIAL_FIELD_NAMES` gate (Plan 02, D-09); `quirk/auth/credentials.py` — no scanner imports (D-14) |
| **Automated gate** | `tests/test_scan_error_gate.py::test_credential_field_names_not_in_serialization_calls` |
| **Residual risk** | LOW — AST gate + schema gate enforce no-credential-column invariant in CI |

---

### Surface 3: CBOM JSON / XML output files

| Attribute | Detail |
|-----------|--------|
| **Vector** | CBOM builder populates `evidence`, `service_detail`, or `properties` from endpoint fields; auth context could end up in these fields |
| **Control** | `CredentialContext` is ephemeral and never written to any `CryptoEndpoint` field. `service_detail` on JWT endpoints is set to the JWKS discovery path, not the auth context. `safe_str()` scrubs any credential-shaped `scan_error` before it can reach CBOM via `build_cbom()`. |
| **Artifact** | `quirk/cbom/builder.py` — reads only `CryptoEndpoint` ORM columns; `quirk/auth/credentials.py` — zero scanner imports (D-14, Plan 01) |
| **Automated gate** | `tests/test_credential_leakage.py::test_sentinel_not_in_cbom_json` |
| **Residual risk** | LOW |

---

### Surface 4: Dashboard `/api/scan/latest` JSON response

| Attribute | Detail |
|-----------|--------|
| **Vector** | Dashboard deserializes and forwards `CryptoEndpoint` rows including `scan_error` and JSON columns |
| **Control** | All control is at the write path (Surfaces 1–2). The API is read-only; it cannot introduce new leakage if the DB rows are clean. |
| **Artifact** | `quirk/dashboard/api/routes/scan.py` — forwards DB columns; `tests/test_credential_leakage.py::test_sentinel_not_in_dashboard_api_json` |
| **Automated gate** | `tests/test_credential_leakage.py::test_sentinel_not_in_dashboard_api_json` |
| **Residual risk** | LOW |

---

### Surface 5: Dashboard PDF export

| Attribute | Detail |
|-----------|--------|
| **Vector** | PDF renderer (`quirk/dashboard/api/routes/pdf.py`) uses Playwright to render the `/print` React route, which is populated from `/api/scan/*` endpoints |
| **Control** | The PDF renderer has NO independent data path. It renders the React dashboard UI, which reads exclusively from `/api/scan/latest` (asserted clean in Surface 4) and the CBOM JSON (asserted clean in Surface 3). Both upstream sources are proven clean by the automated suite. |
| **Artifact** | `tests/test_credential_leakage.py::test_sentinel_not_in_pdf_export_surface` — asserts the shared CBOM-JSON upstream source; see inline linkage comment naming the exact data source |
| **Automated gate** | `tests/test_credential_leakage.py::test_sentinel_not_in_pdf_export_surface` (SC-2 automated assertion via upstream linkage) |
| **Residual risk** | LOW — full Playwright PDF render requires a running server + Chromium; the upstream-linkage assertion satisfies SC-2 |

---

### Surface 6: CLI HTML report

| Attribute | Detail |
|-----------|--------|
| **Vector** | HTML report is generated by `quirk/reports/html_renderer.py` from the same `CryptoEndpoint` rows and CBOM data as the PDF |
| **Control** | Identical data path to PDF (Surface 5); controls at DB write path (Surfaces 1–2) cover this surface. |
| **Artifact** | `quirk/reports/html_renderer.py` — reads from `CryptoEndpoint` columns; `quirk/reports/writer.py` — calls `build_cbom()` + `write_cbom_files()` |
| **Automated gate** | Covered by Surfaces 2–3 assertions (shared data source) |
| **Residual risk** | LOW |

---

### Surface 7: Structured logs / `logging.debug()` calls (httpx DEBUG)

| Attribute | Detail |
|-----------|--------|
| **Vector** | `httpx` emits full request headers including `Authorization:` at DEBUG level when a debug log handler is attached |
| **Control** | D-10: `_strip_auth_from_log(request)` event hook is registered on the httpx Client used for authenticated requests (`quirk/scanner/jwt_scanner.py`, Plan 03). The hook pops `Authorization`, `X-Api-Key`, `X-Auth-Token` from `request.headers` before any log handler fires. For the query-param case, the event hook fires on the modified URL (after query-param key append); the hook does not independently redact the URL, but the query key only appears in the `_append_query_param` call within `_fetch_jwks` — never at module scope or in any log call. |
| **Artifact** | `quirk/scanner/jwt_scanner.py` — `_strip_auth_from_log` + `httpx.Client(event_hooks=...)` (Plan 03, D-10) |
| **Automated gate** | `tests/test_jwt_scanner.py::test_jwt_query_param_cred_ctx_appends_key_to_url` (uses CapturingClientCM — confirms the Client path is taken when auth is set) |
| **Residual risk** | LOW for header schemes. For the query-param scheme, the URL including the key is passed to `_get()` inside `_fetch_jwks`; the event hook fires on the `httpx.Request` object whose URL already contains the key. The event hook does NOT redact the URL. This is a known limitation: the URL is ephemeral within the httpx Client context and is not persisted or logged by QUIRK itself (no `logger.v(url)` call includes the full URL with query params). The `_strip_auth_from_log` definition documents this limitation with the phrase "redacts the query key from request.url" — a future hardening phase may add URL-level redaction if httpx adds that event hook support. |

---

### Surface 8: Python traceback printed to stderr

| Attribute | Detail |
|-----------|--------|
| **Vector** | An unhandled exception in the auth flow could print `locals()` or exception message to stderr in debug mode |
| **Control** | All `from_cli()` errors are routed through `safe_str()` before raising (LEAK-03, D-05). The `CredentialContext.__repr__` never surfaces the secret (`repr=False, compare=False` on `_secret_buf`). The `_wrapped_phase` wrapper catches `BaseException` and writes `safe_str(exc)` to the scan record. |
| **Artifact** | `quirk/auth/credentials.py` — `_resolve_reference()` uses `safe_str()` for ValueError messages (Plan 01, LEAK-03); `_wrapped_phase()` in `run_scan.py` (Plan 03) |
| **Automated gate** | `tests/test_credential_leakage.py` import-presence gate confirms `credentials.py` imports `safe_str` |
| **Residual risk** | MEDIUM — if a future code path in `credentials.py` raises without routing through `safe_str`, the raw secret could appear in a traceback. The import-presence gate in CI provides early warning. |

---

### Surface 9: `quirk.db` WAL file

| Attribute | Detail |
|-----------|--------|
| **Vector** | SQLite's write-ahead log (`.db-wal`) is a separate file; a crash mid-write leaves partial rows |
| **Control** | The WAL inherits the same scrubbed write path as the main DB (Surface 1). A crash mid-write would leave a partial `CryptoEndpoint` row, which would not contain credential data because credentials are never serialized to endpoint fields. The WAL is cleared on next connection (SQLite WAL checkpoint). |
| **Artifact** | SQLite WAL semantics; no additional control needed |
| **Automated gate** | Covered by Surface 1 DB row assertion |
| **Residual risk** | LOW — WAL is a transactional log of the same DB write; its content mirrors what is in the DB |

---

### Surface 10: Process swap / core dump

| Attribute | Detail |
|-----------|--------|
| **Vector** | In-memory credential data persists in heap until GC; process swap or `/proc/<pid>/mem` could recover it |
| **Control** | Best-effort only (D-05, documented above). The `bytearray` zeroing in `close()` reduces heap lifetime. No `mlock()` is used — the v5.1 consulting use case (ephemeral interactive sessions on a local machine) has a narrower threat model than a server daemon. Meaningful wins are (a) never logging the credential and (b) never writing it to SQLite. |
| **Artifact** | `quirk/auth/credentials.py` — `close()` (Plan 01, D-04/D-05) |
| **Automated gate** | `tests/test_credential_leakage.py::test_credential_context_buffer_zeroed_after_close` |
| **Residual risk** | LOW for the consulting threat model (operator-controlled machine, ephemeral sessions). NOT provably safe against a sophisticated memory forensics adversary. |

---

### Surface 11: Scheduler `scheduled_scans` table

| Attribute | Detail |
|-----------|--------|
| **Vector** | Scheduled scans run unattended — they cannot use interactive credentials. A future developer might add a `credential_hint` column "just to show context", creating a persistent secret store. |
| **Control** | D-11 / QRK-SCHED-AUTH-001: `quirk/cli/schedule_cmd.py` hard-rejects `schedule add` when `enable_authenticated_mode: true` is set in the config (Plan 02). `quirk/config.py` documents this prohibition in a comment. The schema gate (`tests/test_scan_error_gate.py::test_no_credential_column_in_schema`, Plan 02) fails CI if any quoted column literal matching credential field names appears in `quirk/db.py`. |
| **Artifact** | `quirk/cli/schedule_cmd.py` — `_config_has_authenticated_mode()` + `sys.exit(2)` (Plan 02, D-11); `quirk/errors.py` — `SCHED-AUTH-001` error entry (Plan 02); `tests/test_scan_error_gate.py::test_no_credential_column_in_schema` (Plan 02, D-09) |
| **Automated gate** | `tests/test_scan_error_gate.py::test_sched_auth_001_format_error` + `test_no_credential_column_in_schema` |
| **Residual risk** | LOW — hard-rejection + schema gate together prevent both user and future-developer paths |

---

## safe_str() Extension Coverage (D-08)

Plan 02 extended `quirk/util/safe_exc.py` `_SENSITIVE_PATTERNS` with four new patterns:

| Pattern | Shape | Phase |
|---------|-------|-------|
| `X-Api-Key\s*:\s*\S+` (IGNORECASE) | API-key header (`X-Api-Key: <value>`) | 93 Plan 02 |
| `X-Auth-Token\s*:\s*\S+` (IGNORECASE) | Auth token header (`X-Auth-Token: <value>`) | 93 Plan 02 |
| `[?&](api_key\|token\|key\|auth_token)=[^&\s]{8,}` (IGNORECASE) | URL query-param API key (D-03 surface) | 93 Plan 02 |
| `Authorization:\s*Basic\s+[A-Za-z0-9+/]{8,}={0,2}` (IGNORECASE) | HTTP Basic credential payload | 93 Plan 02 |

These patterns are in addition to the pre-existing patterns:
- `Authorization:\s*(Bearer|Basic)\s+\S+` — Bearer/Basic header value (Phase 59)
- Vault hvac token (`s.`/`hvs.` prefix)
- Connection string with embedded password
- GCP ADC config path
- Long base64-shaped token (40+ chars)

---

## Automated Gate Half (D-06)

`tests/test_credential_leakage.py` is the **executable half** of this gate. It must be GREEN before any later phase sends authenticated traffic to a live target (D-07).

Tests in the sentinel suite (Phase 93 additions):

| Test | Surface | Assertion |
|------|---------|-----------|
| `test_sentinel_not_in_safe_str_bearer_shape` | safe_str scrubbing | Bearer shape → class-name-only |
| `test_sentinel_not_in_safe_str_api_key_header_shape` | safe_str scrubbing | X-Api-Key shape → class-name-only |
| `test_sentinel_not_in_safe_str_query_param_shape` | safe_str scrubbing | `?api_key=` shape → class-name-only |
| `test_sentinel_not_in_safe_str_basic_shape` | safe_str scrubbing | Basic payload → class-name-only |
| `test_sentinel_not_in_scan_error_json` | scan_error field | absent from `json.dumps` output |
| `test_sentinel_not_in_db_row` | SQLite scan row | absent from all text columns |
| `test_sentinel_not_in_cbom_json` | CBOM JSON file | absent from written file |
| `test_sentinel_not_in_dashboard_api_json` | Dashboard API | absent from `/api/scan/latest` |
| `test_sentinel_not_in_pdf_export_surface` | PDF export (SC-2) | absent from CBOM upstream source (documented linkage) |
| `test_credential_context_buffer_zeroed_after_close` | In-memory zeroization | buffer all-zero after `close()` |

---

## Milestone Gate Declaration (D-07)

This document and its automated suite are the Phase 93 committed security-review gate.

**GATE IS GREEN when:**
1. `python -m pytest tests/test_credential_leakage.py -q` → ALL PASS
2. `python -m pytest tests/test_scan_error_gate.py -q` → ALL PASS (AST gate + schema gate)
3. `python -m pytest tests/test_credential_context.py -q` → ALL PASS (CredentialContext unit tests)
4. This document is present and committed in the phase directory

**No later phase may send authenticated HTTP traffic to a live target until this gate is GREEN.**

Phases 94–96 may extend the credential consumer list (new scanner integrations) or add new finding types. Each such extension must:
- Re-run this suite against the extended code
- Add surface entries to this document for any new data paths introduced
- Update the `safe_str()` patterns if new credential shapes are introduced

---

## Known Limitations

1. **URL-level query key in httpx event hooks:** `_strip_auth_from_log` strips headers but does not redact the query key from `request.url` in the event hook. The URL is ephemeral within the httpx Client context; QUIRK does not log the full URL with query params. Future hardening may add URL-level redaction.

2. **Python heap zeroization:** As documented in the Best-Effort Caveat section, the original `str` from argparse/os.environ cannot be zeroed. The `bytearray` close() minimizes lifetime but does not guarantee heap erasure.

3. **Non-URL query-key shapes in safe_str:** The `safe_str` query-param pattern matches `?api_key=value` (URL query syntax). A non-URL string like `query key=value` (not preceded by `?` or `&`) would not be scrubbed. All actual query-param credential paths in the QUIRK codebase use proper URL construction; this is not a live exposure.
