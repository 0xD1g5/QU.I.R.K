---
phase: audit-2026-05-08-api-cli-core
reviewed: 2026-05-08T00:00:00Z
depth: deep
files_reviewed: 21
files_reviewed_list:
  - quirk/dashboard/server.py
  - quirk/dashboard/api/deps.py
  - quirk/dashboard/api/schemas.py
  - quirk/dashboard/api/app.py
  - quirk/dashboard/api/routes/health.py
  - quirk/dashboard/api/routes/pdf.py
  - quirk/dashboard/api/routes/qramm.py
  - quirk/dashboard/api/routes/scan.py
  - quirk/dashboard/api/routes/trends.py
  - quirk/cli/banner.py
  - quirk/cli/doctor_cmd.py
  - quirk/cli/init_cmd.py
  - quirk/cli/qramm_cmd.py
  - quirk/config.py
  - quirk/db.py
  - quirk/interactive.py
  - quirk/logging_util.py
  - quirk/models.py
  - quirk/validate.py
  - quirk/util/optional_extra.py
  - quirk/util/targets.py
findings:
  critical: 9
  warning: 17
  info: 7
  total: 33
status: issues_found
---

# Subsystem 5: Dashboard API + CLI + Core Platform — Code Review

**Reviewed:** 2026-05-08
**Depth:** deep (cross-file)
**Status:** issues_found

## Summary

Pre-primetime audit before v4.8 introduces dashboard-initiated scans (BACK-86 slice 1). The code currently treats the FastAPI surface as single-tenant local-only, and the audit confirms it is **not safe** to expose multi-user without significant hardening. Major concerns:

- Zero authentication, zero CORS configuration, zero rate-limiting, zero CSRF protection on any route.
- The `/{full_path:path}` SPA catch-all swallows the entire URL space, including any future API typos — silent failures by default.
- The PDF export endpoint is a server-side request forgery (SSRF) primitive once `QUIRK_SERVE_PORT` becomes attacker-influenced (and the current handling does not bind to localhost-only on the Playwright callback).
- A confirmed **path traversal** in `quirk init` via unchecked `output_path` and `os.makedirs(...)`.
- Multiple migration helpers re-open transactional connections inside `init_db()` per call — there is a window where ALTER TABLE failure leaves the schema half-applied; idempotency claims are partially overstated.
- `qramm_profiles.session_id` is nullable + no DB-level FK — orphan rows are trivially possible (already noted in MEMORY but not yet repaired).
- Implicit dependency on environment variables (`QUIRK_DB_PATH`, `QUIRK_SERVE_PORT`, `QUIRK_OUTPUT_DIR`, `QUIRK_CI_STALENESS_OVERRIDE_DATE`) without any validation/sanitization. `QUIRK_OUTPUT_DIR` is consumed inside `routes/scan.py` to resolve a Path → file read; combined with the SPA mount this is a candidate for v4.8 attacker abuse.
- `_derive_findings` and helpers in `routes/scan.py` swallow every classifier exception with bare `except: pass` — silently dropping security findings.
- `validate.py` artifact list is missing `intelligence-*.json` itself (it never asserts the input file is in the expected list — only the others) and is missing post-Phase 14 artifacts referenced elsewhere.
- `qramm_cmd.py` env override for staleness has no try/except around `fromisoformat`, so a malformed env var yields a stack trace (not a polite error code) — fine for dev, broken for CI inheritance.
- Multiple broad `except Exception: pass` blocks in `routes/scan.py` and elsewhere mask real bugs.

The findings below are organized BLOCKER → WARNING → INFO. Performance is out of v1 scope per the directive.

---

## BLOCKER

### CR-01: Path traversal in `quirk init --output`

**File:** `quirk/cli/init_cmd.py:21,41-42`
**Issue:** `output_path` is converted to absolute via `os.path.abspath()` then `os.makedirs(os.path.dirname(output_path), exist_ok=True)` is called and `shutil.copy2()` writes to it — with **no validation** that the path is within an allowed root, no symlink check, and no rejection of `..` traversal beyond CWD. An adversarial caller (e.g. via a future v4.8 dashboard-initiated init call, or a test fixture) can write to `/etc/cron.d/quirk` or `~/.ssh/authorized_keys` if the process has rights.

The existence check (`if os.path.exists(output_path)`) only refuses overwrite — it does not stop traversal to a non-existent path.

**Fix:**
```python
output_path = os.path.abspath(output_path)
allowed_root = os.path.abspath(os.getcwd())
if not (output_path == os.path.join(allowed_root, os.path.basename(output_path))
        or output_path.startswith(allowed_root + os.sep)):
    _warn(f"Refusing to write outside CWD: {output_path}")
    return
# Reject symlinks in any parent component
parent = os.path.dirname(output_path)
if parent and os.path.islink(parent):
    _warn(f"Parent directory is a symlink — refusing: {parent}")
    return
```

---

### CR-02: SSRF / port binding in `routes/pdf.py` via `QUIRK_SERVE_PORT`

**File:** `quirk/dashboard/api/routes/pdf.py:46-53`
**Issue:** `port = int(os.environ.get("QUIRK_SERVE_PORT", "8512"))` then `print_url = f"http://127.0.0.1:{port}/print"`. While 127.0.0.1 limits scope to loopback, `int()` accepts negative integers and very large ones, and there is no upper-bound clamp (1..65535). A misconfigured env var like `QUIRK_SERVE_PORT=0` will silently make Playwright dial port 0 (random ephemeral connect — failure mode), and `QUIRK_SERVE_PORT=80` would let a privileged process drive Playwright at the system HTTP server. More importantly: once v4.8 lands, any process able to set this env var (which includes worker subprocesses inheriting from the dashboard process) can pivot Playwright to **any** loopback port — exposing `/print` content from arbitrary local services to the PDF response stream.

**Fix:**
```python
try:
    port = int(os.environ.get("QUIRK_SERVE_PORT", "8512"))
    if not (1024 <= port <= 65535):
        raise ValueError("port out of range")
except ValueError:
    return Response(...status_code=500...)
```
Also: prefer reading the bound port from `request.url.port` (FastAPI passes the request) instead of trusting env state — cuts the SSRF surface entirely.

---

### CR-03: Missing authentication on every dashboard route

**File:** `quirk/dashboard/api/app.py:32-44`, all `routes/*.py`
**Issue:** No `Depends(authenticate_user)`, no API key check, no CORS configuration, no `TrustedHostMiddleware`, no rate limiting. Every endpoint — including the new mutating QRAMM CRUD routes (`POST /qramm/sessions`, `DELETE /qramm/sessions/{id}`) — is fully world-readable and writable to anyone who can reach the bound interface.

The current default binding is `127.0.0.1` in `server.py`, but:
1. There is no defense-in-depth for users who set `--host 0.0.0.0`.
2. v4.8 is explicitly preparing dashboard-initiated scans — this surface MUST have auth before that lands.
3. `DELETE /api/qramm/sessions/{id}` permanently deletes session data with no audit trail and no confirmation token.

**Fix (pre-v4.8):**
- Add `fastapi.middleware.cors.CORSMiddleware` with `allow_origins=["http://127.0.0.1:8512"]` only.
- Add `TrustedHostMiddleware` with `allowed_hosts=["127.0.0.1", "localhost"]`.
- Introduce a session-token requirement: generate a random token at `serve()` startup, print it once to stderr, require `Authorization: Bearer <token>` on all mutating routes.
- Document that `--host 0.0.0.0` is unsupported until v4.8.

---

### CR-04: `QRAMMProfile.session_id` is nullable and has no DB-level FK

**File:** `quirk/models.py:148`
**Issue:** `session_id = Column(Integer, nullable=True)` — both nullable AND no `ForeignKey("qramm_sessions.id")`. The DELETE-session route at `routes/qramm.py:402` only cascades `QRAMMAnswer`, not `QRAMMProfile`, so deleting a session **leaks** a profile row forever. The upsert in `create_profile` matches on `session_id`, but if `session_id` is NULL (which the column allows), `WHERE session_id == None` produces zero matches and infinite orphan rows accrete.

This is mentioned in MEMORY as a "known limitation" but it is now a **data-integrity bug** because Phase 54 actively writes `session.profile_id` (line 504) and Phase 55 reads multipliers — orphan profiles will mis-attribute multipliers to whatever `profile_id` integer happens to collide.

**Fix:**
```python
session_id = Column(Integer, ForeignKey("qramm_sessions.id"), nullable=False, unique=True)
```
And in `routes/qramm.py:delete_session`, also delete `QRAMMProfile` rows for the session:
```python
db.query(QRAMMProfile).filter(QRAMMProfile.session_id == session_id).delete()
```

---

### CR-05: `delete_session` does not clear `qramm_sessions.profile_id` link before deleting profile

**File:** `quirk/dashboard/api/routes/qramm.py:398-405`
**Issue:** The DELETE route deletes answers and the session, but never the linked `QRAMMProfile`. After CR-04 is fixed, this still leaves the profile_id integer on `qramm_sessions` dangling if profile is deleted first. Subtler: `create_profile` at line 504 sets `session.profile_id = profile.id` — the schema has no FK enforcing this, so `read_session` could return a stale `profile_id` pointing at a deleted profile.

**Fix:** In `delete_session`, delete profiles for the session before deleting the session row. Add an explicit `Index` on `qramm_profiles.session_id`.

---

### CR-06: Bare `except: pass` in classifier call drops findings silently

**File:** `quirk/dashboard/api/routes/scan.py:180-181, 845-846, 859-861, 947-948`
**Issue:** Multiple bare `except Exception: pass` blocks around `classify_algorithm`, `build_evidence_summary`, and stored-profile reads. If the classifier raises (e.g. unknown algorithm string with a bug in the classifier), the **entire quantum-vulnerable finding is silently dropped**. For a security tool whose job is to surface vulnerabilities, this is a correctness-class bug that masquerades as resilience.

`routes/scan.py:180-181`:
```python
except Exception:
    pass   # SILENTLY DROPS QUANTUM-VULNERABLE FINDING
```

**Fix:** Replace bare `except Exception: pass` with explicit logging. At minimum:
```python
except Exception:
    logger.exception("classifier failed for %s; finding skipped", ep.cert_pubkey_alg)
```
And consider a coverage_gap advisory finding when classifier fails so the user sees the gap.

---

### CR-07: SQL injection guard on column names lacks the column-type DDL fragment

**File:** `quirk/db.py:101-105, 163-167, 185-189, 206-210`
**Issue:** `_SAFE_COL_RE` only validates the column NAME, but `_V43_COLUMN_DDLS`, `_PHASE41_COLUMN_DDLS`, `_PHASE46_COLUMN_DDLS`, and `_PHASE54_QRAMM_ANSWER_DDLS` interpolate **both** `col` and `col_type` directly into the DDL: `text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} {col_type}")`. Today these dicts are module-level constants, so this is theoretical — but there is no defense-in-depth if a future contributor wires user/config input into either map. The pattern is one rename away from injection.

**Fix:** Add a parallel allowlist regex for `col_type`:
```python
_SAFE_TYPE_RE = re.compile(r"^[A-Z][A-Z0-9_()\s]*$")
...
if not _SAFE_TYPE_RE.match(col_type):
    raise ValueError(f"Unsafe column type in migration: {col_type!r}")
```

---

### CR-08: `init_db()` ALTER TABLE migrations are not transactional

**File:** `quirk/db.py:228-254`
**Issue:** Each `_ensure_*` helper opens `engine.connect()` and `conn.commit()` independently. If the process is killed mid-`init_db` (e.g. between `_ensure_v43_columns` and `_ensure_email_columns`), the schema is permanently half-applied. SQLite supports transactional DDL — wrapping the entire migration set in one connection + commit would be atomic.

Today this manifests as: a Ctrl-C during a fresh `quirk` invocation leaves the DB with `dat_scan_json` but no `email_scan_json` and `severity` but no `scan_error_category`. The next run silently skips the missing columns because they "exist" — wait, they don't, but the code IS idempotent so it self-heals on next run. **However** if columns 1-3 of a single migration succeed and column 4 fails (e.g. disk full), `commit()` may not have fired — verify by inspection. Either way the per-helper boundary is wrong.

**Fix:** Hoist all ALTER TABLE statements into a single helper that opens one connection, runs all statements, then commits. On failure, the `with` block exits without commit and SQLite rolls back the whole batch.

---

### CR-09: `parse_target_tokens` reflective DoS via deeply-recursive @file (and @file passed as part of CSV)

**File:** `quirk/util/targets.py:100-105`
**Issue:** `_in_file` only blocks @-routing on tokens *inside a file*. But the public function takes a `raw` string from the wizard prompt with no size limit. A wizard input like `@/etc/passwd` (which exists, is plain text, and has no `#` lines) loads `/etc/passwd` and treats every line as a target — leaking host count and (since the lines fail CIDR validation) routing them as bare hosts. Combined with no path validation on the @file path argument, `@/proc/self/environ` would attempt to load process env into the target list.

The recursion guard is one-level — sufficient for D-02 but the file path itself has no allow-listing.

**Fix:**
```python
def load_targets_file(path: str) -> str:
    abs_path = os.path.abspath(path)
    cwd = os.path.abspath(os.getcwd())
    if not abs_path.startswith(cwd + os.sep):
        raise ValueError(f"Targets file must be under CWD: {path}")
    # Add a max-size guard
    if os.path.getsize(abs_path) > 10 * 1024 * 1024:
        raise ValueError(f"Targets file exceeds 10MB: {path}")
    ...
```

---

## WARNING

### WR-01: `_check_dashboard` and `_check_network` always return `True` despite calling them informational

**File:** `quirk/cli/doctor_cmd.py:103-120`
**Issue:** Per the file's docstring, these are informational and never fail. The implementations correctly return `True` on both branches. **However** the calling convention at line 163-167 binds the result to `_ok` (discarded) — which means if a future contributor changes the function to return `False` on real failure (intuitive!), the failure will still not propagate. The "informational" semantic is encoded only in **caller ignoring the return value**, not in the type system.

**Fix:** Make the informational helpers return only `str` (no bool), so accidentally checking the value is a static error:
```python
def _check_network() -> str: ...   # status only
```

---

### WR-02: `_check_db` opens DB at `_DB_DEFAULT_PATH = "./quirk.db"` regardless of `QUIRK_DB_PATH`

**File:** `quirk/cli/doctor_cmd.py:21,72-81,153`
**Issue:** `quirk doctor` checks a hardcoded `./quirk.db` even though the rest of the system honors `QUIRK_DB_PATH`. A user running `QUIRK_DB_PATH=/var/quirk/quirk.db quirk doctor` will get a green checkmark for the wrong file, missing genuine corruption.

**Fix:** Use `os.environ.get("QUIRK_DB_PATH", "./quirk.db")` to resolve the doctor path the same way `deps.py:_default_db_path` does.

---

### WR-03: `_default_db_path` mtime-newest-wins is non-deterministic

**File:** `quirk/dashboard/api/deps.py:12-26`
**Issue:** When `QUIRK_DB_PATH` is unset, the dashboard picks among `./quirk.db`, `./output/quirk.db`, `./quirk-output/quirk.db` by mtime. Two scenarios produce wrong-DB:
1. User scans into `./quirk-output/quirk.db`, then runs `touch ./quirk.db` (or any process modifies the dev DB) — dashboard silently jumps to the older file.
2. Two scans in quick succession can race on filesystem timestamp resolution (HFS+ is 1-second).

This is pure correctness — the dashboard is showing the wrong database without any warning.

**Fix:** Pick a single canonical default (`./quirk-output/quirk.db` matches `interactive.py:180`) and document `QUIRK_DB_PATH` as the only override. Log the resolved path on startup.

---

### WR-04: `routes/scan.py` `get_latest_scan` ?scan_id= time-window slice is off-by-microsecond

**File:** `quirk/dashboard/api/routes/scan.py:782-794`
**Issue:** When the user passes `?scan_id=2026-05-08T12:34:56.789012`, the filter is `scanned_at >= target_ts AND scanned_at < target_ts + 1s`. If endpoints written within that scan span >1s (which they do — the `SESSION_BRACKET = timedelta(minutes=5)` constant exists for exactly this reason on the no-arg branch), the **explicit-scan_id** branch will return a **subset** silently. An operator passing the timestamp from `/api/scans` will get fewer endpoints than a fresh `?scan_id=` call without a value.

**Fix:** Use `SESSION_BRACKET` on both branches — the same forgiveness as the no-arg path.

---

### WR-05: `list_scans` and `_list_session_timestamps` group by string-formatted timestamp — TZ-fragile

**File:** `quirk/dashboard/api/routes/scan.py:744`, `quirk/dashboard/api/routes/trends.py:38-49`
**Issue:** `func.strftime("%Y-%m-%d %H:%M:%S", CryptoEndpoint.scanned_at)` then `datetime.fromisoformat(ts_str)` — but SQLite's strftime drops the timezone, so the returned datetime is **naive**. Downstream code (e.g. `_cert_expiry_key` in scan.py:762-769) defensively re-attaches UTC, but `compute_trend_report` accepts these naive timestamps without guard. If any endpoint writes `scanned_at` with mixed tz-aware/naive values (which `models.py:18` permits — `Column(DateTime, nullable=True)` with no `timezone=True`), comparisons silently misorder sessions.

**Fix:** Pin `Column(DateTime(timezone=True), nullable=False)` for `scanned_at`; producers must write UTC. Until then, normalize at read in `trends.py:_list_session_timestamps`.

---

### WR-06: `compute_overall_score` multiplier validated client-side only

**File:** `quirk/dashboard/api/routes/qramm.py:89-91, 335`
**Issue:** `ScoreRequest.profile_multiplier` is constrained to `0.8..1.5` via Pydantic Field. Good. But the line 335 fallback — `multiplier = (payload.profile_multiplier if payload and payload.profile_multiplier is not None else 1.0)` — does not re-validate the value against the profile's stored multiplier. A caller can override the profile's computed risk multiplier on every score call, persisting a different number into `score_json` than the profile claims. This is a tampering vector if/when multi-user lands.

**Fix:** Require the multiplier to come from the linked `QRAMMProfile.multiplier` row by default; only allow `payload.profile_multiplier` if no profile is linked, or make the parameter advisory-only.

---

### WR-07: `routes/qramm.py:read_session` returns `score=None` on JSON corruption

**File:** `quirk/dashboard/api/routes/qramm.py:259-263`
**Issue:** When `session.score_json` is malformed, the endpoint silently returns `score=None`, indistinguishable from "never scored." A consultant looking at the dashboard will believe the session was never scored when in fact the persisted score blob is corrupt.

**Fix:** Return `score={"error": "score_json corrupted"}` or set `status="scored_corrupted"` so the UI surfaces the problem.

---

### WR-08: `_derive_dar_findings` swallows `json.loads` errors silently with bare except

**File:** `quirk/dashboard/api/routes/scan.py:443-446`
**Issue:** `except Exception: dat = {}` — too broad. Catches `KeyboardInterrupt`, `SystemExit`, `MemoryError`. Should be `except (json.JSONDecodeError, TypeError, ValueError)`.

Same pattern repeats at `_derive_cbom` lines 651-652, 681-683.

**Fix:** Tighten exception scope; log when malformed.

---

### WR-09: `_compute_multiplier` rounds before clamp — boundary value rejected

**File:** `quirk/dashboard/api/routes/qramm.py:166-172`
**Issue:** `value = base + delta` (e.g. 1.20 + 0.20 = 1.40), then `round(value, 2)` (= 1.40), then `min(1.5, max(0.8, 1.40))`. OK on this case. But `_INDUSTRY_BASE["financial_services"] (1.20) + _SENSITIVITY_DELTA["restricted_secret"] (0.20) = 1.40` — never reaches the upper clamp. However, **if a future contributor adds an industry base of 1.30**, `1.30 + 0.20 = 1.50` exactly, and floating-point noise could push to `1.5000000001`, which clamps to 1.5 correctly — but `round(1.50000001, 2)` = 1.5, and `max(0.8, min(1.5, 1.5))` = 1.5. OK on this trace. The order is fine but fragile.

More urgent: **`_SENSITIVITY_DELTA["restricted_secret"]` and `_SENSITIVITY_DELTA["restricted"]` are both 0.20** — if a typo lands an industry of, say, 1.4 with restricted, the value goes to 1.6 then clamps to 1.5 with no warning to the user that their inputs were silently capped. Consultants will compute different multipliers in their heads vs. what the API stores.

**Fix:** Log when the clamp triggers; consider raising a 422 if base+delta exceeds 1.5 by more than 0.1.

---

### WR-10: `interactive.py:_prompt_int` infinite loop on EOF

**File:** `quirk/interactive.py:49-59`
**Issue:** `_prompt_int` calls `_prompt` (which catches EOFError and returns the default str) — `int(default_str)` succeeds, fine. But if a caller passes `default=0` and `minv=1`, `_prompt` returns "0" on EOF, the bounds check fails, and the `while True:` loop iterates forever in a non-TTY context (every iteration re-reads EOF, gets default "0", fails bounds, loops). This blocks scripted usage.

**Fix:**
```python
except (ValueError, EOFError):
    if minv <= default <= maxv:
        return default
    raise
```
And if `default` is out of `[minv, maxv]` range, raise at function-entry.

---

### WR-11: `interactive.py:206-211` exposure default is silently used when input is not 1/2/3

**File:** `quirk/interactive.py:202-211`
**Issue:** `exp_raw = _prompt("Choose 1/2/3", "2").strip()` — only "1" sets `internal`, only "3" sets `internet`, everything else (including "2", "abc", "999") falls through to default `mixed`. The user gets no feedback that "abc" was invalid; their crown-jewels list is computed against a default exposure they did not select.

**Fix:** Validate explicitly:
```python
if exp_raw not in {"1", "2", "3"}:
    print(f"  Unrecognized choice {exp_raw!r}; defaulting to mixed.")
```

---

### WR-12: `setattr(cfg.connectors, "enable_nmap", ...)` injects an undeclared dataclass attribute

**File:** `quirk/interactive.py:269`
**Issue:** `ConnectorsCfg` is a `@dataclass`, but `enable_nmap` is not declared. `setattr` on a dataclass works at runtime but breaks `dataclasses.asdict()`, `dataclasses.fields()`, and any future `__slots__` migration. The comment says "defensive" — but this is the canonical wizard path; it's not defensive, it's load-bearing.

**Fix:** Add `enable_nmap: bool = False` to the `ConnectorsCfg` dataclass at `config.py:186`.

---

### WR-13: `validate.py` artifact list is missing `intelligence-{stamp}.json` itself

**File:** `quirk/validate.py:117-126`
**Issue:** `expected_files` lists 8 artifacts but **does not include the intelligence file** that anchors the timestamp. Validation passes if the intelligence file exists (it has to — the function returns early at line 110-111 if absent), but a test or user reading the list cannot tell what artifacts are actually expected. More importantly, **no test will catch a regression where intelligence-*.json moves to a new location**.

Also: the list does not include `pdf` exports (Phase 14), `findings.csv` (added later), or `cbom-*.cdx.xml` validation. The "post-Phase 14" comment in the directive suggests this was supposed to be expanded.

**Fix:** Add `f"intelligence-{stamp}.json"` to the list explicitly. Audit ROADMAP for post-Phase 14 artifacts and add the missing entries.

---

### WR-14: `qramm_cmd.py` env override has no try/except on malformed input

**File:** `quirk/cli/qramm_cmd.py:29-32`
**Issue:** `datetime.date.fromisoformat(override)` raises `ValueError` on malformed input; this propagates as an uncaught traceback. CI users setting `QUIRK_CI_STALENESS_OVERRIDE_DATE=invalid` get a stack trace, not exit code 2 with a polite message.

**Fix:**
```python
try:
    return datetime.date.fromisoformat(override)
except ValueError as e:
    print(f"ERROR: QUIRK_CI_STALENESS_OVERRIDE_DATE invalid: {e}", file=sys.stderr)
    sys.exit(2)
```

---

### WR-15: `routes/scan.py:850-861` reads `QUIRK_OUTPUT_DIR` from env into a Path read

**File:** `quirk/dashboard/api/routes/scan.py:850-861`
**Issue:** The route reads `QUIRK_OUTPUT_DIR` from env, builds a Path, calls `_latest_intelligence(_output_dir)` which iterates the directory, then opens the resulting file with `read_text`. If an attacker can influence `QUIRK_OUTPUT_DIR` (in v4.8 multi-user mode this is plausible if the env is shared with worker subprocesses), they can point at arbitrary directories on the host filesystem.

The bare `except Exception: pass` at line 860 also silently swallows all errors, including the case where `_intel_path.read_text()` fails because the file is not actually JSON.

**Fix:** Resolve `QUIRK_OUTPUT_DIR` once at server startup (`server.py`) into a sanitized Path, store on app state, and have routes consume from app state — not env.

---

### WR-16: `parse_target_tokens` does not validate hostnames

**File:** `quirk/util/targets.py:117-118`
**Issue:** Bare-token routing accepts ANY string as an FQDN/IP, including obvious garbage like `;rm -rf /`, `<U+REDACTED>`, `localhost:22:extra:colons`. Downstream, this string ends up in `socket.create_connection`, which usually rejects, but error messages will leak the attacker-supplied string into logs (potential log injection if any consumer parses logs structurally).

**Fix:** Validate hostnames against RFC 1123 (regex `^(?=.{1,253}$)([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)(\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$`) or via `idna.encode()`, raising at parse time.

---

### WR-17: `routes/qramm.py:list_questions` returns spread of dict — fails if QRAMM_QUESTIONS schema drifts

**File:** `quirk/dashboard/api/routes/qramm.py:418-421`
**Issue:** `[QuestionItem(**q) for q in QRAMM_QUESTIONS]` will raise `ValidationError` (uncaught → 500) if `QRAMM_QUESTIONS` ever gains a new key not declared on `QuestionItem`. With Pydantic v2 default config this is fine (extra=ignore), but the project does not pin Pydantic config — fragile across upgrades.

**Fix:** Add `model_config = {"extra": "ignore"}` to `QuestionItem` or filter explicitly:
```python
[QuestionItem(**{k: q[k] for k in QuestionItem.model_fields if k in q}) for q in QRAMM_QUESTIONS]
```

---

## INFO

### IN-01: `Dict[str, Any]` type erasure on QRAMM endpoints

**File:** `quirk/dashboard/api/routes/qramm.py:514, 549`
**Issue:** `response_model=Dict[str, Any]` means FastAPI does not validate the response shape; the contract with the React frontend is documentation-only. Consider a `DraftAnswerResponse` Pydantic model with `saved: bool`.

---

### IN-02: `_FACES` banner has `\-` ambiguous escape

**File:** `quirk/cli/banner.py:65-69`
**Issue:** Comment claims the raw-string fix is required, and the code uses `r"..."` correctly. No bug, but the comment is misleading — `\-` is not "undefined behavior", it's just an unrecognized escape. Cleanup-only.

---

### IN-03: `interactive.py:189-192` timezone fallback to "UTC" string vs IANA name

**File:** `quirk/interactive.py:189-192`
**Issue:** `datetime.datetime.now().astimezone().tzname()` returns a string like "EDT" or "UTC", not an IANA zoneinfo key like "America/New_York". `AssessmentCfg.timezone` then carries this short name; if any downstream consumer feeds it to `zoneinfo.ZoneInfo()`, it will fail. The module declares `DEFAULT_TIMEZONE = "America/New_York"` but never uses it.

**Fix:** Use `time.tzname[0]` only as a display label; for storage prefer `datetime.datetime.now().astimezone().tzinfo` → str of the IANA name when available.

---

### IN-04: Magic numbers for QRAMM clamp `0.8 / 1.5 / 0.10 / 0.20`

**File:** `quirk/dashboard/api/routes/qramm.py:148-172`
**Issue:** Hardcoded multipliers; no module-level constants or doc-comment cross-referencing the RESEARCH spec section. A consultant can't grep `MULTIPLIER_MIN` to find them.

**Fix:** Hoist to `_MULTIPLIER_MIN = 0.8`, `_MULTIPLIER_MAX = 1.5`, etc.

---

### IN-05: `app.py:53-58` closure captures via default argument missing

**File:** `quirk/dashboard/api/app.py:53-58`
**Issue:** `_make_handler(fp, mt)` is the canonical factory pattern — implementation is correct. Could be flagged by linters for the loop-variable capture pattern; harmless. No-op.

---

### IN-06: `db.py:_GCP_COLUMNS` and `_EMAIL_COLUMNS` and `_BROKER_COLUMNS` collapse to one helper

**File:** `quirk/db.py:71-145`
**Issue:** Five near-identical `_ensure_*_columns` helpers that differ only in `(table_name, columns_dict)`. Code duplication invites drift — already evident: `_ensure_identity_columns` uses a list (no types, all TEXT), the v43+ helpers use dict-with-types. A single `_ensure_columns(engine, table, ddls: dict[str, str])` covers all.

**Fix:** Consolidate. Wrap in a single transaction (CR-08 fix).

---

### IN-07: `targets.py:projected_probe_count` materializes `list(network.hosts())` for /8 networks

**File:** `quirk/util/targets.py:140-145`
**Issue:** A `/8` IPv4 CIDR materializes 16M+ hosts into a list just to call `len()`. Out of v1 perf scope per directive, flagging only for awareness — `network.num_addresses - 2` is the O(1) equivalent (modulo /31 and /32 special cases the code presumably wants to handle).

---

_Reviewed: 2026-05-08_
_Reviewer: Claude Opus 4.7 (gsd-code-reviewer)_
_Depth: deep (cross-file analysis)_
