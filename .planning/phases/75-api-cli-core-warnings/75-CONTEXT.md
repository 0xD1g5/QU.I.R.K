# Phase 75: API + CLI + Core WARNINGs - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Close all 17 WARNING-severity audit findings in the API/CLI/core subsystem (`api-cli-core/WR-01..WR-17`). Internal contract changes and input-hardening only — no new pip dependencies, no new CLI surfaces.

**In scope (mapped to APCL-NN requirements):**

- **APCL-01** — doctor checks return actionable data, DB path resolution deterministic (closes WR-01, WR-02, WR-03)
- **APCL-02** — API correctness: scan_id time-window microsecond-safe, list_scans groups by parsed datetime, multiplier server-validated, _compute_multiplier clamp-before-round (closes WR-04, WR-05, WR-06, WR-09)
- **APCL-03** — QRAMM/DAR API hardening: read_session structured error on JSON corruption, _derive_dar_findings logs not swallows, list_questions schema-drift-safe (closes WR-07, WR-08, WR-17)
- **APCL-04** — Interactive + validate + routes/scan input hardening: _prompt_int EOF-safe, exposure default validated, enable_nmap declared field, validate.py artifacts include intelligence-{stamp}.json, qramm_cmd try/except, routes/scan QUIRK_OUTPUT_DIR validated, parse_target_tokens RFC-1123 hostname validation (closes WR-10, WR-11, WR-12, WR-13, WR-14, WR-15, WR-16)

**Out of scope (deferred / do-not-touch):**

- React frontend WARNINGs (Phase 76)
- INFO/code-quality findings (Phase 77)
- All BLOCKER-severity rows (closed in Phase 58, 60, 64.1, 70)
- Any change to existing scan output schema — D-15 do-not-touch
- `quirk doctor` exit-code semantics — closed by Phase 52 DOCS-05, do not touch

</domain>

<decisions>
## Implementation Decisions

### doctor _check_dashboard / _check_network actionable status (APCL-01 / WR-01)

- **D-01 (locked):** `quirk/cli/doctor.py::_check_dashboard` returns a typed status dict `{"ok": bool, "detail": str, "remediation": str}`. `_check_network` similarly. Replace any `return True` with a real probe (e.g., HTTP HEAD against the dashboard endpoint, DNS lookup for network) and structured failure messaging. Researcher confirms current return shape.

### doctor _check_db respects QUIRK_DB_PATH (APCL-01 / WR-02)

- **D-02 (locked):** `_check_db` reads `os.environ.get("QUIRK_DB_PATH")` first; if set, validates the path exists and is readable. Falls back to `_default_db_path()` (per D-03) only when env is unset. Mirrors how `quirk` CLI resolves DB elsewhere.

### _default_db_path determinism (APCL-01 / WR-03)

- **D-03 (locked):** Replace mtime-newest-wins with: single canonical path (`~/.quirk/quirk.db` or whatever the project already considers canonical — researcher confirms). If multiple DB files exist in legacy search directories, raise `ValueError(f"Multiple QU.I.R.K. DBs found at {paths}; set QUIRK_DB_PATH explicitly")`. Fail-loud — never silently pick a non-deterministic file. Test parametrizes single-DB-OK and multiple-DB-fail-loud.

### get_latest_scan microsecond time-window (APCL-02 / WR-04)

- **D-04 (locked):** `quirk/dashboard/api/routes/scan.py::get_latest_scan` time-window slice currently uses second-precision comparison; SQLite `datetime()` stores microseconds. Fix: compare via `datetime.fromisoformat(...)` objects, NOT formatted strings. Window inclusion is `[start, end]` (inclusive both sides) — researcher confirms current behavior. Add parametrized test with timestamps `2026-05-15T12:00:00.000000` through `2026-05-15T12:00:00.999999`.

### list_scans groups by parsed datetime (APCL-02 / WR-05)

- **D-05 (locked):** `list_scans` grouping replaces string-formatted timestamp keys with `datetime.fromisoformat(...).replace(microsecond=0)` keys. TZ-fragile string keys removed. Output ordering preserved by sorting on the parsed datetime descending.

### compute_overall_score server-side multiplier validation (APCL-02 / WR-06)

- **D-06 (locked):** Server-side validation BEFORE DB access: multiplier ∈ [0.0, 4.0]; non-numeric or out-of-range raises `HTTPException(status_code=400, detail="multiplier must be numeric in [0.0, 4.0]")`. The client-side check stays but no longer is authoritative.

### _compute_multiplier clamp-before-round (APCL-02 / WR-09)

- **D-07 (locked):** Order is: `clamp(value, lo, hi)` → `round(clamped, 2)`. Current order rounds then clamps, allowing `4.005` to land at `4.01` outside the [0.0, 4.0] band. Swap order. Test asserts `_compute_multiplier(4.0049) == 4.0` and `_compute_multiplier(4.005) == 4.0`.

### routes/qramm read_session structured error (APCL-03 / WR-07)

- **D-08 (locked):** `routes/qramm.py::read_session` JSON corruption currently returns `score=None` (silent). Wrap parse in `try/except (json.JSONDecodeError, ValidationError) as e: raise HTTPException(status_code=422, detail=f"Session JSON corrupt: {safe_str(e)}")`. `safe_str` from Phase 59 LEAK-01 helper.

### _derive_dar_findings log not swallow (APCL-03 / WR-08)

- **D-09 (locked):** Bare `except` in `_derive_dar_findings` replaced with `except (json.JSONDecodeError, KeyError, TypeError) as e: logger.warning("DAR finding parse skipped: %s", safe_str(e)); continue`. Routes through `quirk/util/safe_exc.py::safe_str`. AST gate `tests/test_safe_exc_gate.py` already enforces.

### list_questions schema-drift-safe (APCL-03 / WR-17)

- **D-10 (locked):** `routes/qramm.py::list_questions` currently assumes a fixed shape on `QRAMM_QUESTIONS`. Add defensive defaults: `q.get('id', '<missing-id>')`, `q.get('text', '')`, `q.get('options', [])`. If the underlying schema drifts, the API surface stays a valid 200 with degraded data, not a 500.

### interactive _prompt_int EOF-safe (APCL-04 / WR-10)

- **D-11 (locked):** `quirk/interactive.py::_prompt_int` wraps `input()` in `try/except EOFError: return None` (or raise a project-specific `InteractivePromptAborted`). Caller decides whether to abort or fall back to a default. Mirror the same pattern for any other `_prompt_*` helpers in the same file (researcher inventories).

### interactive exposure default validated + reprompt (APCL-04 / WR-11)

- **D-12 (locked):** Exposure prompt accepts `{1, 2, 3}`. Invalid input prints `f"Invalid choice {raw!r}; expected 1, 2, or 3."` and reprompts up to 3 times. After 3 invalid retries, raise `ValueError("Exposure selection exhausted retry budget")`. Composes with D-11: EOF during prompt aborts cleanly via `EOFError` path.

### ConnectorsCfg.enable_nmap declared field (APCL-04 / WR-12)

- **D-13 (locked):** Add `enable_nmap: bool = False` field to `ConnectorsCfg` dataclass in `quirk/config.py`. Remove all `setattr(cfg.connectors, "enable_nmap", ...)` injection sites in the wizard and config loader. Replace with normal assignment `cfg.connectors.enable_nmap = ...`. Researcher inventories all setattr sites.

### validate.py artifact list includes intelligence-{stamp}.json (APCL-04 / WR-13)

- **D-14 (locked):** `quirk/validate.py` artifact expectation list extended to include `intelligence-{stamp}.json`. Current list misses it, causing validate to silently pass on incomplete output. Researcher confirms the exact filename pattern + place to add.

### qramm_cmd env override try/except (APCL-04 / WR-14)

- **D-15 (locked):** Locate the `qramm_cmd` env override site (likely `quirk/cli/__init__.py` or `quirk/qramm/__init__.py`). Wrap the env lookup + parse in `try/except (ValueError, KeyError) as e: logger.warning("QRAMM cmd env override invalid: %s", e); use_default = True`. Falls back to default on malformed input.

### routes/scan QUIRK_OUTPUT_DIR validated (APCL-04 / WR-15)

- **D-16 (locked):** `routes/scan.py` reads `QUIRK_OUTPUT_DIR` env into a `Path` without validation. Add validation: path exists, is a directory, is writable, no path-traversal segments. Mirror the Phase 58 HARDEN-API-04 `quirk init` path-traversal guard.

### parse_target_tokens RFC-1123 hostname validation (APCL-04 / WR-16)

- **D-17 (locked):** Hostname validation regex: `^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$`. If token doesn't match the hostname pattern, fall through to `ipaddress.ip_address(token)` for raw IPv4/IPv6. If neither matches, raise `ValueError(f"Invalid target token {token!r}: not a valid hostname or IP address")`. Module-level `_HOSTNAME_RE = re.compile(...)` constant.

### Phase-75 do-not-touch list

- **D-18 (locked):**
  - Existing scan output schema (JSON/HTML structure) — no field renames or additions outside D-14
  - `quirk doctor` exit-code semantics (Phase 52 DOCS-05) — only `_check_*` content
  - QRAMM 120-question taxonomy — Phase 74 D-14 boundary preserved
  - React frontend — Phase 76
  - Any CLI flag rename — surface preservation absolute

</decisions>

<canonical_refs>
## Canonical References

- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — 17 rows `api-cli-core/WR-01..WR-17`
- `.planning/audit-2026-05-08/api-cli-core/REVIEW.md` — file:line citations
- `.planning/REQUIREMENTS.md` — APCL-01..APCL-04
- `.planning/ROADMAP.md` Phase 75 — 4 success criteria
- `.planning/phases/74-qramm-compliance-warnings/74-CONTEXT.md` — Phase 74 precedent (fail-loud + reprompt pattern in D-12 mirrors Phase 74 D-01)
- `.planning/phases/58-dashboard-api-hardening/` (if exists) — Phase 58 HARDEN-API-04 path-traversal guard precedent for D-16
- `.planning/phases/52-compliance-uplift-doctor/` (if exists) — Phase 52 DOCS-05 doctor semantics
- `quirk/cli/doctor.py` — WR-01, WR-02 sites
- `quirk/util/safe_exc.py::safe_str` (Phase 59) — D-08, D-09 sink
- `quirk/dashboard/api/routes/scan.py` — WR-04, WR-05, WR-15 sites
- `quirk/dashboard/api/routes/qramm.py` — WR-07, WR-17 sites
- `quirk/intelligence/scoring.py` or wherever `compute_overall_score` lives — WR-06 site
- `quirk/interactive.py` — WR-10, WR-11 sites
- `quirk/config.py` — D-13 ConnectorsCfg.enable_nmap field
- `quirk/validate.py` — WR-13 site
- `quirk/qramm/scoring.py` or core CLI — WR-08 `_derive_dar_findings` site

</canonical_refs>

<code_context>
## Reusable Assets / Patterns

- **`quirk/util/safe_exc.py::safe_str`** — Phase 59 helper; D-08, D-09 route through it.
- **Phase 58 HARDEN-API-04 path-traversal guard** — `quirk init` path validator; D-16 mirrors the same shape (resolve, no symlink-escape, must-be-under-base-dir).
- **Phase 71 D-06 clamp + ValueError pattern** — D-03, D-12 fail-loud follow this.
- **Phase 74 D-11 `is_qramm_model_stale` helper pattern** — small, public, testable. D-01 doctor checks adopt similar shape.
- **`HTTPException(status_code=..., detail=...)` from FastAPI** (existing in `quirk/dashboard/api/routes/`) — D-06, D-08 use this.
- **`@dataclass` field defaults** (existing in `quirk/config.py`) — D-13 ConnectorsCfg new field slots in alongside existing flags.

</code_context>

<test_strategy>
## Test Approach

- **One test module per APCL-NN requirement** (4 modules):
  - `tests/test_doctor_actionable.py` — APCL-01 (WR-01, WR-02, WR-03 fail-loud)
  - `tests/test_api_scan_window.py` — APCL-02 (microsecond window, parsed-datetime grouping, multiplier clamp+validate)
  - `tests/test_api_qramm_hardening.py` — APCL-03 (read_session 422, _derive_dar_findings log, list_questions schema drift)
  - `tests/test_interactive_validate_routes.py` — APCL-04 (EOF, exposure reprompt, enable_nmap field, validate artifact, qramm_cmd, OUTPUT_DIR, hostname validation)
- **RED-then-GREEN** per fix.
- **D-04 parametrized**: timestamps spanning microsecond range.
- **D-17 parametrized**: valid hostnames (good.example.com, sub.domain.co.uk), valid IPs (1.2.3.4, ::1, 2001:db8::1), invalid (`-leading.com`, `a..b.com`, `host_with_underscore` — depends on policy; per D-17 we REJECT underscores), empty string.
- **Audit ledger flip** — 17 rows.

</test_strategy>

<deferred>
## Deferred Ideas

- **Hostname validation tolerance for underscores** (common in internal AD/DNS) — capture if operators report rejections.
- **`quirk doctor` JSON output format** — current text-only; JSON could power CI integrations.
- **`compute_overall_score` server-side audit logging** — D-06 returns 400 on bad input; a structured audit log of rejected multipliers could surface anomalous client behavior. Defer.
- **Wizard prompt for QUIRK_DB_PATH disambiguation** when D-03 fail-loud fires — operators may want a CLI selection prompt. Defer.

</deferred>
