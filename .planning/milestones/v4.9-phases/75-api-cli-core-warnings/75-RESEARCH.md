# Phase 75: API + CLI + Core WARNINGs - Research

**Researched:** 2026-05-15
**Domain:** Dashboard API + CLI doctor + core platform input hardening (17 open WARNING rows)
**HEAD verified at:** `0f290e6` (post-Phase 71 review fixes)
**Confidence:** HIGH (every file:line in CONTEXT.md verified against HEAD)

## Summary

Phase 75 closes 17 open WARNING rows (`api-cli-core/WR-01..WR-17`) clustered into four APCL-NN requirements covering CLI doctor correctness (APCL-01), dashboard API time-window + multiplier correctness (APCL-02), QRAMM/DAR API error visibility (APCL-03), and interactive/validate/routes input hardening (APCL-04). CONTEXT.md locks 17 implementation decisions (D-01..D-17) plus D-18 do-not-touch. Every CONTEXT site has been verified against HEAD; **the file referenced as `quirk/cli/doctor.py` in D-01/D-02 is actually `quirk/cli/doctor_cmd.py`** (this is the only file-path discrepancy — all line numbers verified). Phase 58 path-traversal precedent for D-16 is `quirk/cli/init_cmd.py:21-40` (resolve-realpath + descend-from-CWD + reject `..` segments).

**Primary recommendation:** Four plans, one per APCL-NN requirement — mirrors Phase 74's three-plan structure but adds a fourth for APCL-04 (largest cluster, 7 fixes). All decisions are <30-line surgical edits except D-17 (new module-level regex + IP-fallback ladder in `parse_target_tokens`) and D-13 (declared `enable_nmap` field + remove single setattr injection).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

All 17 implementation decisions D-01..D-17 (plus D-18 do-not-touch) are locked in `.planning/phases/75-api-cli-core-warnings/75-CONTEXT.md`:

- **D-01** — `_check_dashboard` / `_check_network` return typed status dict `{"ok": bool, "detail": str, "remediation": str}`; real probes (HTTP HEAD for dashboard, DNS lookup for network) with structured failure messaging. (Currently `Tuple[bool, str]` — see C-1.)
- **D-02** — `_check_db` reads `QUIRK_DB_PATH` first; validates path exists+readable; falls back to `_default_db_path()` only when env unset.
- **D-03** — Replace mtime-newest-wins with single canonical path (`./quirk-output/quirk.db` per Phase 74 D-05 precedent). If multiple DBs exist in legacy search dirs, raise `ValueError(f"Multiple QU.I.R.K. DBs found at {paths}; set QUIRK_DB_PATH explicitly")`. Fail-loud.
- **D-04** — `get_latest_scan` `?scan_id=` time-window uses parsed datetime comparison; window `[start, end]` inclusive both sides. Parametrized test across microsecond range.
- **D-05** — `list_scans` grouping replaces string-formatted timestamp keys with `datetime.fromisoformat(...).replace(microsecond=0)` keys; output sorted on parsed datetime descending.
- **D-06** — Server-side multiplier validation before DB access: `multiplier ∈ [0.0, 4.0]` ⇒ `HTTPException(status_code=400, detail="multiplier must be numeric in [0.0, 4.0]")`. **[See C-2 — current code already validates server-side at `routes/qramm.py:347-355` but uses `[0.8, 1.5]` range matching Phase 54 spec. CONTEXT D-06's `[0.0, 4.0]` range conflicts with existing Phase 54 ScoreRequest Pydantic constraint. Planner must adjudicate which range is canonical.]**
- **D-07** — `_compute_multiplier` clamp-then-round: `round(clamp(value, lo, hi), 2)`. Current order: `max(0.8, min(1.5, round(value, 2)))` — rounds first. Swap order.
- **D-08** — `routes/qramm.py::read_session` JSON corruption ⇒ `HTTPException(status_code=422, detail=f"Session JSON corrupt: {safe_str(e)}")`. `safe_str` from Phase 59. **[See C-3 — current code at lines 272-276 catches `(TypeError, ValueError)` and returns `score=None`; CONTEXT's `(json.JSONDecodeError, ValidationError)` tuple is slightly off — `json.JSONDecodeError` IS a `ValueError` subclass; `ValidationError` is not raised here because `json.loads` is the only call. Planner should land tightened tuple `(json.JSONDecodeError, TypeError, ValueError)` and the 422 raise.]**
- **D-09** — Bare `except: dat = {}` in `_derive_dar_findings` replaced with `except (json.JSONDecodeError, KeyError, TypeError) as e: logger.warning("DAR finding parse skipped: %s", safe_str(e)); continue`. **[See C-4 — CONTEXT references `tests/test_safe_exc_gate.py` as the AST gate; no such file exists. There is `tests/test_safe_exc.py` (unit tests, not an AST gate). Planner must either drop the AST-gate sentence from the task or create the gate file as new work.]**
- **D-10** — `list_questions` adds defensive defaults: `q.get('id', '<missing-id>')`, `q.get('text', '')`, `q.get('options', [])`. **[See C-5 — `QuestionItem` does not have fields named `id`/`text`/`options`; it has `question_number`, `dimension`, `practice_area`, `text`, `maturity_labels`. CONTEXT wording reflects a generic shape; the actual defensive `.get()` keys must match the real `QuestionItem` fields.]**
- **D-11** — `_prompt_int` wraps `input()` in `try/except EOFError: return None` (or project-specific `InteractivePromptAborted`). Inventory all `_prompt_*` helpers for the same pattern. **[Current `_prompt` (the underlying helper) already catches `EOFError` and returns the default; `_prompt_int`'s bug is the `while True` loop with no EOF exit — see Pitfall 1.]**
- **D-12** — Exposure prompt accepts `{1, 2, 3}`; invalid prints `f"Invalid choice {raw!r}; expected 1, 2, or 3."` and reprompts up to 3 times; after 3 invalid retries raise `ValueError("Exposure selection exhausted retry budget")`. Composes with D-11 EOF path.
- **D-13** — Add `enable_nmap: bool = False` field to `ConnectorsCfg` dataclass at `quirk/config.py:192`. Remove single `setattr(cfg.connectors, "enable_nmap", ...)` site at `quirk/interactive.py:273`. Replace with `cfg.connectors.enable_nmap = _enable_nmap_wizard` (or pass as kwarg in the existing `ConnectorsCfg(...)` literal at `quirk/interactive.py:243-252`).
- **D-14** — `quirk/validate.py:117-126` `expected_files` list extended to include `f"intelligence-{stamp}.json"`.
- **D-15** — `qramm_cmd` env override `try/except (ValueError, KeyError)`. Site: `quirk/cli/qramm_cmd.py:29-32` (the `datetime.date.fromisoformat(override)` call).
- **D-16** — `routes/scan.py:998` reads `QUIRK_OUTPUT_DIR` env into a `Path` without validation. Add validation: path exists, is a directory, is writable, no path-traversal segments. Mirror Phase 58 HARDEN-API-04 / CR-01 guard at `quirk/cli/init_cmd.py:21-40`.
- **D-17** — Hostname validation regex `^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$`. Token-routing ladder: hostname regex → `ipaddress.ip_address(token)` for raw IPv4/IPv6 → else `ValueError`. Module-level `_HOSTNAME_RE = re.compile(...)`. Site: `quirk/util/targets.py:181-183` (`else` branch of token routing).

### Claude's Discretion

- D-03 canonical-DB path final selection between `./quirk-output/quirk.db` and `./quirk.db` (RESEARCH recommends `./quirk-output/quirk.db` to match Phase 74 + `interactive.py:180` precedent).
- D-11 `InteractivePromptAborted` exception class name vs returning `None` sentinel (RESEARCH recommends returning the in-range `default` on EOF for backward compatibility; raise only if `default` is out of `[minv, maxv]`).

### Deferred Ideas (OUT OF SCOPE)

- Hostname validation tolerance for underscores (common in AD/DNS) — capture if operators report rejections.
- `quirk doctor` JSON output format — current text-only; JSON could power CI integrations.
- `compute_overall_score` server-side audit logging of rejected multipliers.
- Wizard prompt for `QUIRK_DB_PATH` disambiguation when D-03 fail-loud fires.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| APCL-01 | doctor checks actionable + DB path deterministic (closes WR-01, WR-02, WR-03) | All three sites verified at `quirk/cli/doctor_cmd.py` (NOT `doctor.py` per CONTEXT — see C-1). `_check_db` at line 77, `_check_dashboard` at line 118, `_check_network` at line 108. `_default_db_path` at `quirk/dashboard/api/deps.py:12-26` with current mtime-newest-wins implementation matching CONTEXT description verbatim. |
| APCL-02 | API correctness: scan_id microsecond window + list_scans parsed-datetime grouping + multiplier validate + clamp-then-round (closes WR-04, WR-05, WR-06, WR-09) | `get_latest_scan` at `routes/scan.py:915-959`; current scan_id branch uses `target_ts + timedelta(seconds=1)` exclusive upper bound — matches CONTEXT WR-04 description. `list_scans` at `routes/scan.py:782-864` groups via `func.strftime("%Y-%m-%d %H:%M:%S", ...)` — matches WR-05. `compute_overall_score` lives at `quirk/qramm/scoring.py:49` (NOT `routes/qramm.py` — see C-2); the server-side multiplier guard is at `routes/qramm.py:347-355` (`score_session` callsite). `_compute_multiplier` at `routes/qramm.py:179-185` rounds then clamps — matches WR-09. |
| APCL-03 | QRAMM/DAR API hardening (closes WR-07, WR-08, WR-17) | `read_session` at `routes/qramm.py:263-286`; current code returns `score=None` on `(TypeError, ValueError)` — see C-3. `_derive_dar_findings` at `routes/scan.py:435-483` with bare `except Exception: dat = {}` at lines 458-461. `list_questions` at `routes/qramm.py:442-445` — pure spread `[QuestionItem(**q) for q in QRAMM_QUESTIONS]`, no `.get()` defaults. |
| APCL-04 | Interactive + validate + routes/scan input hardening + hostname validation (closes WR-10..WR-16) | `_prompt_int` at `interactive.py:49-59`. Exposure prompt at `interactive.py:206-216`. Single `setattr(cfg.connectors, "enable_nmap", …)` site at `interactive.py:273` (only one — see grep results). `validate.py` expected_files at lines 117-126. `qramm_cmd` env override at `cli/qramm_cmd.py:29-32`. `QUIRK_OUTPUT_DIR` consumer at `routes/scan.py:998`. `parse_target_tokens` bare-token branch at `util/targets.py:181-183`. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Doctor check return types + actionable probes | `quirk/cli/doctor_cmd.py` | — | CLI tier; D-01 typed dict propagates to `run_doctor` table renderer at line 128-176 |
| DB path resolution determinism | `quirk/dashboard/api/deps.py` + `quirk/cli/doctor_cmd.py` | — | Both tiers must agree: dashboard's `_default_db_path` and doctor's `_check_db` must use identical resolution rule |
| Scan-id microsecond window + list_scans grouping | `quirk/dashboard/api/routes/scan.py` | `quirk/dashboard/api/routes/trends.py` (D-05 grouping precedent — already uses `%H:%M:%f`) | trends.py already millisecond-grouped at line 49-50; list_scans is the laggard |
| Multiplier server-side validation | `quirk/dashboard/api/routes/qramm.py` (`score_session`) | `quirk/qramm/scoring.py::compute_overall_score` | Validation lives in the route; scoring helper consumes a validated value |
| Clamp-then-round multiplier compute | `quirk/dashboard/api/routes/qramm.py::_compute_multiplier` | — | Pure stdlib helper at line 179-185 |
| read_session structured error | `quirk/dashboard/api/routes/qramm.py` | `quirk/util/safe_exc.py::safe_str` (Phase 59) | Route raises; safe_str sanitizes error string |
| _derive_dar_findings logged exception | `quirk/dashboard/api/routes/scan.py` | `quirk/util/safe_exc.py::safe_str` | Same shape as D-08 |
| list_questions schema-drift safety | `quirk/dashboard/api/routes/qramm.py` | `quirk/qramm/questions.py::QRAMM_QUESTIONS` (read-only consumer) | Defensive `.get()` ladder lives in the route |
| _prompt_int EOF safety | `quirk/interactive.py` | — | Wizard tier; EOF path returns default when in-range |
| Exposure reprompt loop | `quirk/interactive.py` | — | Same wizard tier; composes with D-11 EOF handling |
| ConnectorsCfg.enable_nmap declared field | `quirk/config.py` | `quirk/interactive.py` (remove setattr) | Field added in dataclass; only one setattr injection site to remove |
| validate.py artifact list | `quirk/validate.py` | — | Pure list extension; no logic change |
| qramm_cmd env override try/except | `quirk/cli/qramm_cmd.py` | — | Single function `_resolve_today` at line 21-32 |
| QUIRK_OUTPUT_DIR validation | `quirk/dashboard/api/routes/scan.py` | `quirk/cli/init_cmd.py` (precedent at lines 21-40) | Mirror the Phase 58 init_cmd path-traversal guard |
| parse_target_tokens RFC-1123 hostname validation | `quirk/util/targets.py` | — | Module-local; new `_HOSTNAME_RE` constant + IP fallback at the bare-token branch |

## Standard Stack

### Core (no new deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| stdlib `re` | Python 3.11+ | D-17 `_HOSTNAME_RE` module-level compile | [VERIFIED] Already imported in `quirk/util/targets.py:32` |
| stdlib `ipaddress` | Python 3.11+ | D-17 IP-fallback ladder | [VERIFIED] Already imported in `quirk/util/targets.py:33` (`ipaddress.ip_network` used at line 176) |
| stdlib `datetime` | Python 3.11+ | D-04 microsecond-safe datetime compare; D-05 parsed-datetime grouping | [VERIFIED] Already used across `routes/scan.py:6` |
| stdlib `json` | Python 3.11+ | D-08, D-09 `json.JSONDecodeError` catch | [VERIFIED] `routes/scan.py:4`, `routes/qramm.py:17` |
| stdlib `logging` | Python 3.11+ | D-09, D-15 `logger.warning` | [VERIFIED] `routes/scan.py:46` (`logger = logging.getLogger(__name__)`); `routes/qramm.py:50` |
| stdlib `os.path` / `pathlib` | Python 3.11+ | D-16 path-traversal guard | [VERIFIED] Already imported in `routes/scan.py:994-995` |
| `quirk.util.safe_exc.safe_str` | Phase 59 helper | D-08, D-09 credential-safe exception stringification | [VERIFIED] `quirk/util/safe_exc.py:36`; 9 existing call sites across `quirk/scanner/*` and `quirk/cbom/writer.py` |
| `fastapi.HTTPException` | already in deps | D-06, D-08 structured error responses | [VERIFIED] `routes/qramm.py:24`, `routes/scan.py:9` |

### Supporting (pattern precedent — already present)

| Module | Pattern | Use Case |
|--------|---------|----------|
| `quirk/cli/init_cmd.py:21-40` | path-traversal guard (`os.path.realpath` + CWD-descent + `..` segment reject) | D-16 `QUIRK_OUTPUT_DIR` mirror |
| `quirk/util/targets.py:137-167` | Phase 58 / CR-09 `@file` path validation (realpath + blocked prefixes + size cap) | D-16 secondary precedent (more elaborate than init_cmd) |
| `quirk/dashboard/api/routes/trends.py:41-60` | `func.strftime("%Y-%m-%d %H:%M:%f", ...)` millisecond grouping + `datetime.fromisoformat` parse | D-05 `list_scans` mirror (note: trends.py already does this — D-05 is bringing scan.py up to parity) |
| `quirk/qramm/scoring.py::compute_overall_score` | `min(4.0, ...)` clamp + `round(..., 4)` ordering | D-07 clamp-then-round precedent (similar shape, already correct) |
| `quirk/scanner/db_connector.py:175` | `logger.v(f"... {safe_str(exc)}")` | D-08, D-09 logging shape |
| `quirk/dashboard/api/routes/qramm.py:347-355` | `if not (0.8 <= multiplier <= 1.5): raise HTTPException(...)` | D-06 mirror — but range conflict (C-2) |
| Phase 71 D-09 / WR-3 fix (`commit 9840862`) | `secrets.randbits(32)` fail-loud pattern | D-03 `ValueError` pattern |

### Alternatives Considered

None. CONTEXT.md locks every decision. **No new pip dependencies** — D-18 do-not-touch and zero-new-deps boundary in CONTEXT both explicit.

**Installation:** No new packages.

**Version verification:** [VERIFIED via `python3 -c "import sys; print(sys.version)"`] Python 3.11+ required per CLAUDE.md.

## Architecture Patterns

### System Architecture Diagram

```
APCL-01 (doctor checks + DB path determinism):
   ┌───────────────────────────────────────────────────────┐
   │ quirk/cli/doctor_cmd.py                                │
   │   _check_db(db_path)         ← D-02: read QUIRK_DB_PATH│
   │   _check_dashboard()         ← D-01: typed dict probe  │
   │   _check_network()           ← D-01: typed dict probe  │
   │   run_doctor()               (consumes typed dicts)    │
   └───────────────────────────────────────────────────────┘
                       ▲ shared resolution
   ┌───────────────────────────────────────────────────────┐
   │ quirk/dashboard/api/deps.py                            │
   │   _default_db_path()         ← D-03: fail-loud on multi│
   └───────────────────────────────────────────────────────┘

APCL-02 (API correctness):
   ┌───────────────────────────────────────────────────────┐
   │ quirk/dashboard/api/routes/scan.py                     │
   │   get_latest_scan(scan_id)   ← D-04: parsed datetime   │
   │   list_scans()               ← D-05: %f grouping       │
   └───────────────────────────────────────────────────────┘
   ┌───────────────────────────────────────────────────────┐
   │ quirk/dashboard/api/routes/qramm.py                    │
   │   score_session              ← D-06: validate first    │
   │   _compute_multiplier        ← D-07: clamp then round  │
   └───────────────────────────────────────────────────────┘

APCL-03 (QRAMM + DAR error visibility):
   ┌───────────────────────────────────────────────────────┐
   │ quirk/dashboard/api/routes/qramm.py                    │
   │   read_session               ← D-08: 422 + safe_str    │
   │   list_questions             ← D-10: .get() defaults   │
   └───────────────────────────────────────────────────────┘
   ┌───────────────────────────────────────────────────────┐
   │ quirk/dashboard/api/routes/scan.py                     │
   │   _derive_dar_findings       ← D-09: log not swallow   │
   └───────────────────────────────────────────────────────┘

APCL-04 (input hardening):
   ┌───────────────────────────────────────────────────────┐
   │ quirk/interactive.py                                   │
   │   _prompt_int                ← D-11: EOF returns default│
   │   exposure prompt            ← D-12: 3-retry reprompt  │
   │   setattr enable_nmap (rm)   ← D-13                    │
   └───────────────────────────────────────────────────────┘
   ┌───────────────────────────────────────────────────────┐
   │ quirk/config.py                                        │
   │   ConnectorsCfg              ← D-13: declared field    │
   └───────────────────────────────────────────────────────┘
   ┌───────────────────────────────────────────────────────┐
   │ quirk/validate.py            ← D-14: list extension    │
   │ quirk/cli/qramm_cmd.py       ← D-15: try/except        │
   │ quirk/dashboard/.../scan.py  ← D-16: OUTPUT_DIR guard  │
   │ quirk/util/targets.py        ← D-17: hostname regex    │
   └───────────────────────────────────────────────────────┘
```

### Recommended Plan Structure

```
75-01-PLAN.md  → APCL-01 (WR-01, WR-02, WR-03) — doctor + DB path
75-02-PLAN.md  → APCL-02 (WR-04, WR-05, WR-06, WR-09) — API correctness
75-03-PLAN.md  → APCL-03 (WR-07, WR-08, WR-17) — QRAMM + DAR error visibility
75-04-PLAN.md  → APCL-04 (WR-10..WR-16, 7 fixes) — input hardening
```

Mirrors Phase 74's per-requirement plan layout; the APCL-04 plan is the largest by task count but each fix is independent and parallelizable.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Credential-safe exception stringification | Custom regex sanitizer | `quirk.util.safe_exc.safe_str` (Phase 59) | Already does the work; 9 existing call sites; AST gate convention |
| Path-traversal guard for `QUIRK_OUTPUT_DIR` | New helper | Mirror `quirk/cli/init_cmd.py:21-40` shape | Phase 58 / CR-01 precedent; same realpath + CWD-descent + `..` reject pattern |
| Hostname validation | Custom DNS lookup | `re.fullmatch(_HOSTNAME_RE, token)` + `ipaddress.ip_address` fallback | Both stdlib; no network call required at parse time |
| Microsecond-precision SQLite datetime grouping | Custom timestamp parser | `func.strftime("%Y-%m-%d %H:%M:%f", col)` then `datetime.fromisoformat` | Already used in `trends.py:41-60`; D-05 brings `scan.py` to parity |
| Fail-loud DB path disambiguation | Heuristic mtime/size selection | `ValueError(f"Multiple ... found at {paths}; set QUIRK_DB_PATH explicitly")` | Phase 71 D-06 fail-loud pattern precedent |

**Key insight:** Five of seven APCL-04 fixes (D-13, D-14, D-15, D-16, D-17) are mechanical: declare-don't-setattr; extend-list; wrap-in-try-except; mirror-existing-guard; validate-via-regex. The only design freedom is D-11's EOF behavior (return default vs raise) and D-12's retry count phrasing.

## Common Pitfalls

### Pitfall 1: `_prompt_int` infinite loop not where you think

**What goes wrong:** Re-reading `_prompt_int` at `interactive.py:49-59`, the `while True:` loop iterates on integer-parse failure. The CONTEXT D-11 framing says "wraps `input()` in `try/except EOFError`" — but `_prompt_int` doesn't call `input()`. It calls `_prompt` (line 38-46), which DOES catch EOFError and returns the default str. The bug per WR-10 is: if `default=0, minv=1, maxv=100`, `_prompt` returns "0" on EOF, `int("0")` succeeds, bounds check fails, loop re-enters, EOFError again returns "0", forever.

**Why it happens:** The EOF catch lives at the wrong layer.

**How to avoid:** D-11 fix is at `_prompt_int`'s `except ValueError:` branch — extend it to also catch the bounds-failure case: if input is unreadable (EOF echoing default) AND default itself is out of range, return the in-range default OR raise. CONTEXT's "wraps `input()` in `try/except EOFError`" wording is shorthand for "make `_prompt_int` not loop on EOF" — planner should land the EOF-aware exit at the `_prompt_int` level, not at `_prompt`.

**Warning signs:** Non-TTY pytest runs hanging; CI timeouts on interactive tests.

### Pitfall 2: WR-06 server-side multiplier validation already exists

**What goes wrong:** A casual reader would conclude WR-06 is unstarted. In fact `routes/qramm.py:347-355` already validates `0.8 <= multiplier <= 1.5` server-side and raises `HTTPException(400, format_error("DASHBOARD-010"))`. The remaining gap is REVIEW.md's actual complaint: the multiplier is not re-validated against the **profile's stored multiplier**.

**Why it happens:** CONTEXT D-06 re-states the validation in a different range (`[0.0, 4.0]`) than the existing Pydantic constraint (`[0.8, 1.5]`).

**How to avoid:** Planner adjudication required (C-2). Two valid paths:
1. **Honor CONTEXT D-06 verbatim** — widen the range to `[0.0, 4.0]` (would diverge from Phase 54 Pydantic spec).
2. **Honor existing Phase 54 range** — interpret D-06 as "add `payload.profile_multiplier` re-check against `QRAMMProfile.multiplier`" (mirrors REVIEW WR-06's actual fix).

Planner MUST surface this in PLAN-CHECK before execute — per `feedback_planner_context_precedence.md`, CONTEXT D-06 wording supersedes RESEARCH inference unless user re-discusses.

**Warning signs:** Multiplier-related tests breaking after the fix lands; legitimate `1.2` calls returning 400.

### Pitfall 3: Phase 58 path-traversal guard precedent has two variants

**What goes wrong:** D-16 says "mirror Phase 58 HARDEN-API-04". There are two paths in the codebase that match: `quirk/cli/init_cmd.py:21-40` (simpler, 4 checks) and `quirk/util/targets.py:137-167` (Phase 58 CR-09, 4 checks including size cap + line cap + blocked prefixes).

**Why it happens:** Both are correct; `init_cmd.py` is for `quirk init --output`, `targets.py` is for `@file` target loading.

**How to avoid:** For `QUIRK_OUTPUT_DIR` (D-16), the **closer precedent is `init_cmd.py`** because `OUTPUT_DIR` is a directory (not a target file with size limits). The pattern:
```python
_out_real = os.path.realpath(env_value)
_cwd_real = os.path.realpath(os.getcwd())
if not (_out_real.startswith(_cwd_real + os.sep) or _out_real == _cwd_real):
    raise ValueError(f"QUIRK_OUTPUT_DIR resolves outside CWD: {env_value}")
if ".." in os.path.normpath(env_value).split(os.sep):
    raise ValueError(f"QUIRK_OUTPUT_DIR contains traversal segments: {env_value}")
if not os.path.isdir(_out_real):
    raise ValueError(f"QUIRK_OUTPUT_DIR is not a directory: {env_value}")
if not os.access(_out_real, os.R_OK):
    raise ValueError(f"QUIRK_OUTPUT_DIR is not readable: {env_value}")
```

**Warning signs:** Tests passing `..` segments silently accepted.

### Pitfall 4: `_default_db_path` is called from TWO places

**What goes wrong:** D-03 says "Replace mtime-newest-wins with single canonical path". But `_check_db` in `doctor_cmd.py:77` uses `_DB_DEFAULT_PATH = "./quirk.db"` (a module constant) — it does NOT call `_default_db_path()`. D-02 reconciles this: `_check_db` must resolve like `_default_db_path` does.

**Why it happens:** Two parallel resolution paths exist (deps.py + doctor_cmd.py).

**How to avoid:** Hoist the resolution into a shared helper (e.g., `quirk/util/db_path.py::resolve_db_path()`) and have both callsites use it. This is the right shape for D-02 + D-03 together; landing them as parallel hand-rolls invites drift.

**Warning signs:** `quirk doctor` greenlighting a different DB than `quirk dashboard` reads.

### Pitfall 5: `safe_str` is not stable JSON

**What goes wrong:** D-08 raises `HTTPException(422, detail=f"Session JSON corrupt: {safe_str(e)}")`. `safe_str` returns `"ClassName: message"` (or `"ClassName"` on credential match). The `detail` field is JSON-serialized by FastAPI — fine. But `safe_str(json.JSONDecodeError("Expecting value: line 1 column 1 (char 0)", "", 0))` returns the full message including the source position; tests pinning the exact error string will be fragile across Python minor versions.

**How to avoid:** Test assertions should match `detail.startswith("Session JSON corrupt: JSONDecodeError")`, not full equality.

**Warning signs:** D-08 tests flaking on Python upgrade.

### Pitfall 6: `list_questions` field-name mismatch (C-5)

**What goes wrong:** CONTEXT D-10 lists defensive defaults `q.get('id', '<missing-id>')`, `q.get('text', '')`, `q.get('options', [])`. But `QuestionItem` (at `routes/qramm.py:434-440`) has fields `question_number`, `dimension`, `practice_area`, `text`, `maturity_labels`. There is no `id` or `options` field.

**Why it happens:** CONTEXT generic shape doesn't match the actual model.

**How to avoid:** Use the real field names:
```python
return [
    QuestionItem(
        question_number=q.get("question_number", 0),
        dimension=q.get("dimension", ""),
        practice_area=q.get("practice_area", ""),
        text=q.get("text", ""),
        maturity_labels=q.get("maturity_labels", []),
    )
    for q in QRAMM_QUESTIONS
]
```
The intent (schema-drift-safe) holds; the keys differ.

**Warning signs:** Pydantic `ValidationError` at startup if any QRAMM_QUESTIONS entry drops a key.

## Code Examples

### Path-traversal guard for QUIRK_OUTPUT_DIR (D-16)

```python
# Source: derived from quirk/cli/init_cmd.py:21-40 (Phase 58 / CR-01)
def _resolve_output_dir() -> Path:
    raw = os.environ.get("QUIRK_OUTPUT_DIR", "./quirk-output")
    cwd_real = os.path.realpath(os.getcwd())
    out_real = os.path.realpath(raw)
    if not (out_real.startswith(cwd_real + os.sep) or out_real == cwd_real):
        raise ValueError(f"QUIRK_OUTPUT_DIR resolves outside CWD: {raw!r}")
    if ".." in os.path.normpath(raw).split(os.sep):
        raise ValueError(f"QUIRK_OUTPUT_DIR contains traversal segments: {raw!r}")
    p = Path(out_real)
    if not p.is_dir():
        raise ValueError(f"QUIRK_OUTPUT_DIR is not a directory: {raw!r}")
    if not os.access(out_real, os.R_OK):
        raise ValueError(f"QUIRK_OUTPUT_DIR is not readable: {raw!r}")
    return p
```

### Hostname validation ladder (D-17)

```python
# Source: derived from CONTEXT D-17 + ipaddress stdlib precedent at quirk/util/targets.py:176
_HOSTNAME_RE = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

def _validate_bare_token(token: str) -> str:
    if _HOSTNAME_RE.fullmatch(token):
        return token
    try:
        ipaddress.ip_address(token)
        return token
    except ValueError:
        raise ValueError(
            f"Invalid target token {token!r}: not a valid hostname or IP address"
        )
```

### Clamp-then-round multiplier (D-07)

```python
# Source: derived from CONTEXT D-07 + quirk/qramm/scoring.py:63 precedent
def _compute_multiplier(industry: str, data_sensitivity: str) -> float:
    base = _INDUSTRY_BASE.get(industry, 1.00)
    delta = _SENSITIVITY_DELTA.get(data_sensitivity, 0.0)
    value = base + delta
    # Clamp FIRST, then round — order matters at boundary
    clamped = max(0.8, min(1.5, value))
    return round(clamped, 2)
```

### read_session 422 with safe_str (D-08)

```python
# Source: derived from CONTEXT D-08 + quirk/scanner/db_connector.py:175 safe_str usage
from quirk.util.safe_exc import safe_str

@router.get("/qramm/sessions/{session_id}", response_model=SessionRead)
def read_session(session_id: int, db: Session = Depends(get_db)) -> SessionRead:
    session = _get_session_or_404(db, session_id)
    # ... answers_count ...
    score: Optional[Dict[str, Any]] = None
    if session.score_json:
        try:
            score = json.loads(session.score_json)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            raise HTTPException(
                status_code=422,
                detail=f"Session JSON corrupt: {safe_str(e)}",
            )
    # ... return SessionRead(...)
```

### _derive_dar_findings logged exception (D-09)

```python
# Source: derived from CONTEXT D-09 + quirk/scanner/db_connector.py:175 pattern
from quirk.util.safe_exc import safe_str

logger = logging.getLogger(__name__)  # already exists at routes/scan.py:46

# Replace lines 458-461:
if dat_raw:
    try:
        dat = json.loads(dat_raw)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("DAR finding parse skipped: %s", safe_str(e))
        continue
```

## Project Constraints (from CLAUDE.md)

- **PEP 8** — all Python changes
- **Minimal diffs** — no unnecessary refactors
- **`python -m compileall`** + relevant tests after changes
- **Mandatory phase completion steps** (after verify):
  1. Create Obsidian phase note at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-75-API-CLI-Core-Warnings.md` (write directly to vault FS)
  2. Update `docs/UAT-SERIES.md`
  3. Sync UAT-SERIES.md to Obsidian (vault FS write)
  4. Commit `docs/UAT-SERIES.md`
- **No chaos lab changes** anticipated — D-18 do-not-touch covers all surfaces
- **Staleness cadence** — not affected (no `model_meta.py` or `compliance/__init__.py` data touch)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Tuple[bool, str]` doctor returns | Typed dict per D-01 | Phase 75 | UI table renderer in `run_doctor()` consumes structured detail |
| mtime-newest-wins DB resolution | Single canonical + fail-loud | Phase 75 D-03 | Operators get explicit error instead of silent wrong-DB |
| Bare `except: pass` in DAR parse | Logged + narrow tuple | Phase 75 D-09 | Visible errors; consistent with `db_connector.py` shape (Phase 72) |
| `setattr` on dataclass for `enable_nmap` | Declared field | Phase 75 D-13 | `dataclasses.asdict()` / `.fields()` work; future `__slots__` migration safe |
| String-formatted timestamp grouping in `list_scans` | Parsed-datetime grouping (already done in trends.py) | Phase 75 D-05 | Microsecond-safe across both routes |

**Deprecated/outdated:**
- `_DB_DEFAULT_PATH = "./quirk.db"` module constant in `doctor_cmd.py:25` — replaced by env-aware resolution (D-02)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | D-03 canonical path is `./quirk-output/quirk.db` (matches Phase 74 D-05 + `interactive.py:180`) | User Constraints / Discretion | Wrong canonical path silently picks legacy `./quirk.db` |
| A2 | D-06 intent is "re-validate against profile multiplier", not "widen range to [0.0, 4.0]" | C-2 / Pitfall 2 | Wider range diverges from Phase 54 Pydantic spec |
| A3 | D-11 EOF behavior returns in-range default (else raises) — backward-compatible with existing tests | User Constraints / Discretion | New `InteractivePromptAborted` exception would break callers |
| A4 | The `tests/test_safe_exc_gate.py` mentioned in CONTEXT D-09 does NOT exist; planner drops or creates as new work | C-4 | If the gate is expected to already exist, D-09 task description misleads the executor |

## Open Questions

1. **D-06 multiplier range: `[0.0, 4.0]` (CONTEXT) vs `[0.8, 1.5]` (existing Pydantic)**
   - What we know: REVIEW WR-06 actual complaint is "validated client-side only" — but server-side validation already exists in code. CONTEXT specifies a new range.
   - What's unclear: Did CONTEXT author intend to widen the range, or restate the existing validation in different units?
   - Recommendation: Surface in PLAN-CHECK before execute; default to existing `[0.8, 1.5]` plus profile re-check unless user re-discusses.

2. **D-11 prompt API surface**
   - What we know: CONTEXT mentions both "return None" and "raise InteractivePromptAborted" as options.
   - What's unclear: Which surface do callers expect?
   - Recommendation: Return default when in `[minv, maxv]`; raise `ValueError` at function-entry when `default` is out of range (matches REVIEW WR-10 fix sketch verbatim).

3. **D-09 AST-gate test file**
   - What we know: `tests/test_safe_exc_gate.py` does not exist; `tests/test_safe_exc.py` is a unit-test file, not an AST gate.
   - What's unclear: Does CONTEXT D-09 expect us to create the gate as part of this phase, or did it conflate the unit test with a gate?
   - Recommendation: Drop the AST-gate sentence from D-09 task wording; add `_derive_dar_findings` to existing `tests/test_safe_exc.py` coverage if the unit test suite has the right shape.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All decisions | ✓ | 3.11+ (CLAUDE.md pin) | — |
| FastAPI + Pydantic | D-06, D-08, D-10 | ✓ | already in deps | — |
| SQLAlchemy | D-04, D-05 | ✓ | already in deps | — |
| `quirk.util.safe_exc` (Phase 59) | D-08, D-09 | ✓ | `quirk/util/safe_exc.py:36` | — |
| Phase 58 `init_cmd` path-traversal guard | D-16 | ✓ | `quirk/cli/init_cmd.py:21-40` | — |

**Nothing blocking.** All decisions can be implemented with existing stdlib + project helpers.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pytest.ini` / `pyproject.toml` (existing) |
| Quick run command | `pytest tests/test_doctor_actionable.py tests/test_api_scan_window.py tests/test_api_qramm_hardening.py tests/test_interactive_validate_routes.py -x` |
| Full suite command | `pytest -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| APCL-01 / WR-01 | doctor checks return typed dict | unit | `pytest tests/test_doctor_actionable.py::test_check_dashboard_typed_dict -x` | ❌ Wave 0 |
| APCL-01 / WR-02 | `_check_db` honors `QUIRK_DB_PATH` | unit | `pytest tests/test_doctor_actionable.py::test_check_db_env -x` | ❌ Wave 0 |
| APCL-01 / WR-03 | `_default_db_path` fail-loud on multi-DB | unit | `pytest tests/test_doctor_actionable.py::test_default_db_path_fail_loud -x` | ❌ Wave 0 |
| APCL-02 / WR-04 | scan_id microsecond window | unit (parametrized) | `pytest tests/test_api_scan_window.py::test_microsecond_window -x` | ❌ Wave 0 |
| APCL-02 / WR-05 | list_scans parsed-datetime grouping | unit | `pytest tests/test_api_scan_window.py::test_list_scans_parsed_grouping -x` | ❌ Wave 0 |
| APCL-02 / WR-06 | multiplier server-side 400 | integration | `pytest tests/test_api_scan_window.py::test_multiplier_server_validate -x` | ❌ Wave 0 |
| APCL-02 / WR-09 | clamp-then-round boundary | unit | `pytest tests/test_api_scan_window.py::test_compute_multiplier_clamp -x` | ❌ Wave 0 |
| APCL-03 / WR-07 | read_session 422 on JSON corrupt | integration | `pytest tests/test_api_qramm_hardening.py::test_read_session_422 -x` | ❌ Wave 0 |
| APCL-03 / WR-08 | _derive_dar_findings logged | unit | `pytest tests/test_api_qramm_hardening.py::test_dar_finding_logged -x` | ❌ Wave 0 |
| APCL-03 / WR-17 | list_questions schema-drift safe | unit | `pytest tests/test_api_qramm_hardening.py::test_list_questions_drift -x` | ❌ Wave 0 |
| APCL-04 / WR-10 | _prompt_int EOF-safe | unit | `pytest tests/test_interactive_validate_routes.py::test_prompt_int_eof -x` | ❌ Wave 0 |
| APCL-04 / WR-11 | exposure reprompt | unit | `pytest tests/test_interactive_validate_routes.py::test_exposure_reprompt -x` | ❌ Wave 0 |
| APCL-04 / WR-12 | enable_nmap declared field | unit | `pytest tests/test_interactive_validate_routes.py::test_enable_nmap_field -x` | ❌ Wave 0 |
| APCL-04 / WR-13 | validate artifact list | unit | `pytest tests/test_interactive_validate_routes.py::test_validate_artifact_list -x` | ❌ Wave 0 |
| APCL-04 / WR-14 | qramm_cmd try/except | unit | `pytest tests/test_interactive_validate_routes.py::test_qramm_cmd_invalid_env -x` | ❌ Wave 0 |
| APCL-04 / WR-15 | QUIRK_OUTPUT_DIR validated | unit | `pytest tests/test_interactive_validate_routes.py::test_output_dir_traversal -x` | ❌ Wave 0 |
| APCL-04 / WR-16 | hostname validation parametrized | unit (parametrized) | `pytest tests/test_interactive_validate_routes.py::test_hostname_validation -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_doctor_actionable.py tests/test_api_scan_window.py tests/test_api_qramm_hardening.py tests/test_interactive_validate_routes.py -x`
- **Per wave merge:** `pytest -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_doctor_actionable.py` — covers APCL-01 (WR-01, WR-02, WR-03)
- [ ] `tests/test_api_scan_window.py` — covers APCL-02 (WR-04, WR-05, WR-06, WR-09)
- [ ] `tests/test_api_qramm_hardening.py` — covers APCL-03 (WR-07, WR-08, WR-17)
- [ ] `tests/test_interactive_validate_routes.py` — covers APCL-04 (WR-10..WR-16)
- [ ] Existing FastAPI test client fixtures (used in `tests/test_*_route.py`) — reuse, no new conftest required

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (Phase 58 closed) | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | **yes** | Pydantic on API; manual validation on env vars (D-16) and hostnames (D-17); fail-loud on multi-DB (D-03) |
| V6 Cryptography | no | — |
| V7 Error Handling and Logging | **yes** | `safe_str` for credential-safe stringification (D-08, D-09); structured 422 instead of `score=None` (D-08); explicit logger.warning instead of bare except (D-09) |
| V12 File and Resources | **yes** | Path-traversal guard on `QUIRK_OUTPUT_DIR` (D-16); mirrors Phase 58 / CR-01 guard |

### Known Threat Patterns for FastAPI + CLI stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via env var (`QUIRK_OUTPUT_DIR`) | Tampering / Info Disclosure | realpath + CWD-descent + `..` reject (D-16) |
| Log injection via attacker-supplied hostname token | Tampering | RFC-1123 validation at parse time (D-17) |
| Silent failure masking quantum-vulnerable finding | Repudiation | Replace bare except with `logger.warning` + `safe_str` (D-09) |
| Credential leak via exception stringification | Info Disclosure | `safe_str` (Phase 59) — already routed for D-08, D-09 |
| Indeterministic DB selection picks attacker-controlled file | Tampering | Fail-loud on multi-DB (D-03) |
| Underscore-bearing AD hostnames falsely rejected | Availability (FP) | Captured in Deferred Ideas |

## Sources

### Primary (HIGH confidence)
- HEAD verification at `0f290e6` — every file:line in CONTEXT.md confirmed via Read tool
- `quirk/util/safe_exc.py:36` — `safe_str` Phase 59 helper, 9 existing call sites
- `quirk/cli/init_cmd.py:21-40` — Phase 58 / CR-01 path-traversal guard precedent
- `quirk/dashboard/api/routes/trends.py:41-60` — millisecond grouping precedent for D-05
- `quirk/dashboard/api/routes/qramm.py:347-355` — existing server-side multiplier validation (C-2 source)
- `.planning/audit-2026-05-08/api-cli-core/REVIEW.md` — file:line citations for every WR row
- `.planning/audit-2026-05-08/AUDIT-TASKS.md:186-202` — 17 open WR rows
- `.planning/REQUIREMENTS.md:54-57` — APCL-01..APCL-04 acceptance criteria
- `.planning/phases/74-qramm-compliance-warnings/74-RESEARCH.md` — template + Phase 74 D-05 canonical path precedent

### Secondary (MEDIUM confidence)
- Phase 74 RESEARCH C-1..C-9 concern shape — adopted for C-1..C-5 below

### Tertiary (LOW confidence)
- None — all claims verified against HEAD

<research_concerns>

## C-1: CONTEXT references `quirk/cli/doctor.py`; file is `quirk/cli/doctor_cmd.py`

CONTEXT D-01, D-02 say "`quirk/cli/doctor.py::_check_dashboard`" etc. No such file exists. The actual file is `quirk/cli/doctor_cmd.py` (verified — `_check_dashboard` at line 118, `_check_db` at line 77, `_check_network` at line 108). This is a CONTEXT shorthand, not a substantive discrepancy. Planner should land the fixes in `doctor_cmd.py`.

## C-2: CONTEXT D-06 multiplier range `[0.0, 4.0]` conflicts with existing Phase 54 Pydantic range `[0.8, 1.5]`

CONTEXT D-06 says "Server-side validation BEFORE DB access: multiplier ∈ [0.0, 4.0]". But:
- `routes/qramm.py:94-100` (`ScoreRequest`) — Pydantic `Field` description constrains `[0.8, 1.5]`.
- `routes/qramm.py:347-355` — existing server-side validation already enforces `0.8 <= multiplier <= 1.5`.
- `quirk/qramm/scoring.py:49-70` (`compute_overall_score`) — applies multiplier with `min(4.0, dim * multiplier)` ceiling; **the `4.0` is the OUTPUT ceiling, not the INPUT multiplier ceiling**.

Two interpretations:
1. **Widen the input range to [0.0, 4.0]** — diverges from Phase 54 spec; high-risk regression.
2. **Re-validate against profile's stored multiplier** (REVIEW WR-06's actual complaint) — keep range, add tampering guard.

Planner adjudication required before execute. Default per `feedback_planner_context_precedence.md`: CONTEXT D-06 wins unless user re-discusses. Recommend flagging in PLAN-CHECK and asking user.

## C-3: D-08 catch tuple `(json.JSONDecodeError, ValidationError)` is incorrect for the actual call site

CONTEXT D-08 says wrap parse in `try/except (json.JSONDecodeError, ValidationError)`. The actual call at `routes/qramm.py:273-276` is:
```python
try:
    score = json.loads(session.score_json)
except (TypeError, ValueError):
    score = None
```
Only `json.loads` is called — no Pydantic `ValidationError` is raised here. `json.JSONDecodeError` IS a subclass of `ValueError`. Correct catch tuple is `(json.JSONDecodeError, TypeError, ValueError)`. Planner should land the corrected tuple + the 422 raise.

## C-4: CONTEXT D-09 references `tests/test_safe_exc_gate.py` (does not exist)

CONTEXT D-09 says "AST gate `tests/test_safe_exc_gate.py` already enforces." File does not exist. There is `tests/test_safe_exc.py` (unit tests for `safe_str` itself, not an AST gate). Two paths:
1. Drop the "AST gate already enforces" sentence — treat as informational.
2. Create the AST gate as new Phase 75 work (scope creep — not in CONTEXT requirements).

Recommend path 1: planner drops the AST-gate sentence; D-09 implementation stays as specified.

## C-5: D-10 defensive-default keys (`id`, `text`, `options`) don't match real `QuestionItem` fields

CONTEXT D-10 says "Add defensive defaults: `q.get('id', '<missing-id>')`, `q.get('text', '')`, `q.get('options', [])`." But `QuestionItem` at `routes/qramm.py:434-440` has fields `question_number, dimension, practice_area, text, maturity_labels` — no `id` or `options`.

The CONTEXT keys reflect a generic shape; the intent (schema-drift-safe `.get()` defaults) is correct but the keys must match the real fields. See Pitfall 6 for the corrected code shape.

</research_concerns>

## Metadata

**Confidence breakdown:**
- File/line verifications: HIGH — every CONTEXT site read against HEAD `0f290e6`
- Helper availability (`safe_str`, `HTTPException`, `logger`): HIGH — verified imports + call-site precedent
- setattr enable_nmap inventory: HIGH — exactly one site at `quirk/interactive.py:273` (confirmed via grep)
- `compute_overall_score` location: HIGH — lives at `quirk/qramm/scoring.py:49` (NOT in routes)
- `_derive_dar_findings` location: HIGH — `quirk/dashboard/api/routes/scan.py:435`
- `parse_target_tokens` location: HIGH — `quirk/util/targets.py:92`
- Phase 58 path-traversal guard for D-16: HIGH — `quirk/cli/init_cmd.py:21-40` is the right precedent
- CONTEXT-vs-HEAD discrepancies (C-1..C-5): MEDIUM — flagged for planner adjudication; none of them block implementation but two (C-2, C-4) require explicit planner decisions

**Research date:** 2026-05-15
**Valid until:** 2026-06-14 (30 days; code domain is internal-only, stable surface)
