---
phase: 77-info-code-quality-audit-ledger
plan: 03
subsystem: api-cli-core
tags: [info, api, cli, qramm, db, audit-ledger, v4.9]
requires:
  - quirk/dashboard/api/routes/qramm.py
  - quirk/cli/banner.py
  - quirk/db.py
provides:
  - QrammScoreResponse Pydantic model on the public score endpoint (D-16)
  - MULTIPLIER_MIN/MAX/LOW_STEP/HIGH_STEP module-level constants (D-19)
  - Generic _ensure_columns helper + 8 per-feature column tuples (D-21)
affects:
  - tests/test_db_migrations.py
  - tests/test_db_connector.py
  - tests/test_qramm_answer.py
  - tests/test_qramm_models.py
  - tests/test_identity_infra.py
  - tests/test_tls_scanner_chain_verified.py
tech-stack:
  added: []
  patterns:
    - Pydantic response_model on FastAPI route
    - Generic SQLite ALTER-TABLE-IF-MISSING with allowlist guards
key-files:
  created:
    - tests/test_qramm_routes_typed_response.py
    - tests/test_banner_comment_corrected.py
    - tests/test_qramm_multiplier_constants.py
    - tests/test_db_ensure_columns_generic.py
  modified:
    - quirk/dashboard/api/routes/qramm.py
    - quirk/cli/banner.py
    - quirk/db.py
    - tests/test_db_migrations.py
    - tests/test_db_connector.py
    - tests/test_qramm_answer.py
    - tests/test_qramm_models.py
    - tests/test_identity_infra.py
    - tests/test_tls_scanner_chain_verified.py
decisions:
  - D-16 narrowed to public QRAMM score response (Discretion + Deferred per CONTEXT)
  - D-19 constants live in routes/qramm.py per RESEARCH C-2 (NOT scoring.py)
  - D-21 consolidates 8 column-adding helpers; 5 table-creating helpers preserved
  - D-22 wont-fix preserves Phase 65 Risks #4 deliberate .hosts() choice (VERIFY-FIRST)
metrics:
  duration: ~30m
  completed: 2026-05-15
  tasks: 3
  tests_added: 11
  audit_rows_flipped: 0  # all 7 INFO-03 row flips deferred to PLAN 77-05
---

# Phase 77 Plan 03: INFO-03 (API/CLI INFOs IN-01..IN-07) Summary

Closes INFO-03 via 3 production source edits, 4 new test modules, and 6 regression-test updates. Per-row audit dispositions finalized for IN-01..IN-07 with the row flips consolidated into PLAN 77-05.

## One-liner

QRAMM public score endpoint gains a `QrammScoreResponse` Pydantic response model; multiplier magic numbers extracted to named constants in `routes/qramm.py`; banner raw-string comment corrected; 8 `_ensure_*_columns` helpers in `quirk/db.py` consolidated into a single generic `_ensure_columns(engine, table, expected)` helper with per-feature tuple constants — D-18 / D-20 / D-22 close as audit-flip-only / wont-fix with rationale recorded.

## What Changed

### D-16 (api-cli-core/IN-01) — QRAMM typed response

`quirk/dashboard/api/routes/qramm.py`

- Added `QrammScoreResponse(BaseModel)` with the 5 canonical fields exactly matching the prior return-dict shape: `session_id`, `overall`, `maturity`, `dimensions`, `profile_multiplier`. The `dimensions` inner shape retains `Dict[str, Any]` — full per-dim breakdown narrowing is deferred to v5.0 per Discretion D-16 and CONTEXT Deferred Ideas.
- Annotated `@router.post("/qramm/sessions/{session_id}/score", response_model=QrammScoreResponse)` and changed the function's return type to `QrammScoreResponse`.
- Persistence path serializes `response.model_dump()` so `read_session` round-trips the same key set under `session.score_json`.
- The 7 other `Dict[str, Any]` sites in this module are intentionally untouched (deferred to v5.0).

### D-17 (api-cli-core/IN-02) — Banner comment fix

`quirk/cli/banner.py`

- Per RESEARCH C-5 / Pitfall 4: the audit row + CONTEXT both misread the literal. `_FACES = (r"…")` was already a raw string, so `\-` is literal text — only the comment was wrong.
- Rewrote the misleading comment to state the raw-string fact and added the audit-row closure citation. Code below is byte-for-byte unchanged.

### D-19 (api-cli-core/IN-04) — QRAMM multiplier constants

`quirk/dashboard/api/routes/qramm.py`

- **Location adjudication per RESEARCH C-2:** constants live in `quirk/dashboard/api/routes/qramm.py`, **NOT** in `quirk/qramm/scoring.py` (CONTEXT D-19 misread the source).
- Added module-level constants near the top of the file:
  ```python
  MULTIPLIER_MIN: float = 0.8
  MULTIPLIER_MAX: float = 1.5
  MULTIPLIER_LOW_STEP: float = 0.10
  MULTIPLIER_HIGH_STEP: float = 0.20
  ```
- Docstring ties the band to Phase 54 lineage and Phase 75-02 D-06 (WR-06 server-side validation + WR-09 clamp-before-round).
- Replaced 4 literal occurrences across 3 call sites:
  - `_SENSITIVITY_DELTA` map (4 substitutions: `-0.10`, `0.10`, `0.20`, `0.20`).
  - `_compute_multiplier` clamp (`max(0.8, min(1.5, value))`).
  - Score endpoint server-side validation (`not (0.8 <= multiplier <= 1.5)`).
- AST gate confirms zero stray multiplier literals remain outside the 4 constant-definition assignments.

### D-21 (api-cli-core/IN-06) — `_ensure_columns` consolidation

`quirk/db.py`

- Per RESEARCH Pattern 3: added a single generic `_ensure_columns(engine, table, expected)` SQLite ALTER-TABLE-IF-MISSING helper carrying the prior 8 helpers' security defenses (`_SAFE_COL_RE` + `_SAFE_COL_TYPE_RE`).
- Removed 8 per-feature column-adding helpers:
  `_ensure_identity_columns`, `_ensure_gcp_columns`, `_ensure_v43_columns`, `_ensure_email_columns`, `_ensure_broker_columns`, `_ensure_phase41_columns`, `_ensure_phase46_columns`, `_ensure_phase54_qramm_columns`.
- Their column lists became 8 module-level tuple constants (`_IDENTITY_COLUMNS`, `_GCP_COLUMNS`, `_V43_COLUMNS`, `_EMAIL_COLUMNS`, `_BROKER_COLUMNS`, `_PHASE41_COLUMNS`, `_PHASE46_COLUMNS`, `_PHASE54_QRAMM_ANSWER_COLUMNS`).
- The 5 table-creating / FK-rebuild helpers (`_ensure_qramm_profiles_fk`, `_ensure_qramm_tables`, `_ensure_scheduled_tables`, `_ensure_scan_jobs_table`, `_ensure_scan_checkpoints_table`) **remain UNTOUCHED** per RESEARCH inventory recommendation — they use `Base.metadata.create_all` / raw FK rebuild (different pattern).
- `init_db` call-site order preserved exactly.
- Net delta: ~169 LOC removed, ~73 LOC added; deduplication ratio ≈ 56%.

## D-18 / D-20 / D-22 Dispositions (audit-flip-only, deferred to PLAN 77-05)

### D-18 (api-cli-core/IN-03) — Interactive TZ fallback

**Disposition:** wont-fix — site not present at HEAD.

Wave-0 sweep:
```bash
grep -rn -E '(tzlocal|UTC.*fallback|datetime\.tzinfo|pytz)' quirk/cli/ quirk/dashboard/api/ quirk/qramm/
# (no matches)
```

Rationale: RESEARCH C-11 / Pitfall 6 / Q2 — researcher confirmed no `tzlocal` / UTC-string-fallback site exists at HEAD `cf2417a`. Audit row is stale or was pre-fixed by an earlier phase. No code change; PLAN 77-05 flips the row to wont-fix with this disposition.

### D-20 (api-cli-core/IN-05) — `_make_handler` factory pattern

**Disposition:** audit-flip-only — implementation already correct.

```bash
grep -n "_make_handler" quirk/dashboard/api/app.py
# 124:            def _make_handler(fp: str, mt: str):
# 129:            application.get(f"/{_filename}")(_make_handler(_filepath, _mime))
```

Rationale: RESEARCH C-6 — the audit row body itself says "No-op". The closure-via-default-argument pattern hypothesized in CONTEXT D-20 does not apply because the existing `_make_handler(fp, mt)` factory already captures parameters by value at call time. No code change; PLAN 77-05 flips the row.

### D-22 (api-cli-core/IN-07) — `projected_probe_count` CIDR counting

**Disposition:** wont-fix — Phase 65 Risks #4 documented decision preserved.

```bash
grep -n "Risks #4" quirk/util/targets.py
# 220:    each. Risks #4: uses .hosts() NOT .num_addresses to avoid off-by-2 on IPv4
```

Rationale: RESEARCH C-3 / Pitfall 3 / A2 / Q1 — `quirk/util/targets.py:215-240::projected_probe_count` carries an explicit Phase 65 Risks #4 comment requiring `.hosts()` to avoid IPv4 /24 off-by-2 in probe count. CONTEXT D-22 directed the opposite. Per the VERIFY-FIRST executor rule, Phase 65's documented decision takes precedence. No code change; PLAN 77-05 flips the row to wont-fix with the Phase 65 Risks #4 citation.

Threat T-77-03-04 in the plan threat register accepted this disposition explicitly — reversing Phase 65 Risks #4 would reintroduce the under-probe / over-probe DoS risk.

## Audit-Row Dispositions Consumed by PLAN 77-05

| Row                  | Disposition          | Basis                                         |
| -------------------- | -------------------- | --------------------------------------------- |
| api-cli-core/IN-01   | closed (code edit)   | D-16 QrammScoreResponse landed                |
| api-cli-core/IN-02   | closed (comment fix) | D-17 comment corrected per RESEARCH C-5       |
| api-cli-core/IN-03   | wont-fix             | D-18 site not present at HEAD (no matches)    |
| api-cli-core/IN-04   | closed (code edit)   | D-19 MULTIPLIER_* constants landed            |
| api-cli-core/IN-05   | closed-as-no-op      | D-20 already correct per RESEARCH C-6         |
| api-cli-core/IN-06   | closed (code edit)   | D-21 _ensure_columns consolidation landed     |
| api-cli-core/IN-07   | wont-fix             | D-22 Phase 65 Risks #4 deliberate choice      |

## Verification

```
$ python -m compileall -q quirk/dashboard quirk/cli quirk/db.py
(no output, exit 0)

$ python -m pytest tests/test_qramm_routes_typed_response.py \
                   tests/test_banner_comment_corrected.py \
                   tests/test_qramm_multiplier_constants.py \
                   tests/test_db_ensure_columns_generic.py
11 passed in 0.30s

$ QUIRK_DB_PATH=/tmp/quirk_t.db python -m pytest <14 test modules>
174 passed, 2 skipped in 1.34s
```

Untouched files confirmed:
- `quirk/dashboard/api/app.py` (D-20 audit-flip-only)
- `quirk/util/targets.py` (D-22 wont-fix)
- `quirk/qramm/scoring.py` (D-19 in routes/qramm.py per RESEARCH C-2)

The 5 table-creating helpers in `quirk/db.py` confirmed untouched via AST gate in `tests/test_db_ensure_columns_generic.py::test_table_creating_helpers_preserved`.

## Commits

| Hash      | Type | Description                                                                                                                |
| --------- | ---- | -------------------------------------------------------------------------------------------------------------------------- |
| b02c877   | test | Failing tests for D-16/D-17/D-19/D-21 + record D-18/D-20/D-22 dispositions per RESEARCH C-2/C-3/C-5/C-6/C-11                |
| cf8d7a6   | feat | Close INFO-03 (D-16, D-17, D-19, D-21) — qramm typed response, banner comment, db generic helper                            |
| 9f83e12   | fix  | Adjust regression tests for INFO-03 D-21 helper consolidation                                                              |

## Deviations from Plan

### Scope-boundary deferral

**[Scope] Pre-existing "multiple legacy DB files in cwd" environment issue surfaced during regression sweep**
- **Found during:** Task 3 regression band
- **Issue:** `tests/test_qramm_router.py` (and a few related modules) raise `ValueError: Multiple QU.I.R.K. DBs found at [...]` when run without `QUIRK_DB_PATH` because three legacy DB files (`./quirk.db`, `./output/quirk.db`, `./quirk-output/quirk.db`) coexist in the working tree.
- **Action:** Out of scope per executor scope-boundary rule — the failure mode is independent of any change in this plan. Tests pass cleanly with `QUIRK_DB_PATH=/tmp/...` (174/174). Logged for the next housekeeping pass.
- **Fix:** None applied in this plan.

### Auto-fixed regression tests (Rule 3 — blocking issues)

Six test modules imported the 8 removed `_ensure_*_columns` helpers (or the prior DDL dicts) by name. Their tests broke under D-21 consolidation. All six were updated to use the new `_ensure_columns(engine, table, _FEATURE_COLUMNS)` shape — semantic coverage is preserved (idempotency, allowlist guard, init_db call-ordering invariant, schema columns).

Updated:
- `tests/test_db_migrations.py` — poisoned-dict pattern → poisoned-tuple via the generic helper.
- `tests/test_db_connector.py::test_v43_columns_idempotent` — now uses `_V43_COLUMNS`.
- `tests/test_tls_scanner_chain_verified.py` — now uses `_PHASE46_COLUMNS`.
- `tests/test_qramm_answer.py` — three sites now use `_PHASE54_QRAMM_ANSWER_COLUMNS`.
- `tests/test_qramm_models.py::test_ensure_qramm_tables_called_after_phase46` — call-order invariant now checks `_PHASE46_COLUMNS` reference site inside `init_db`.
- `tests/test_identity_infra.py::test_schema_migration_idempotent` — now uses `_IDENTITY_COLUMNS`.

## Known Stubs

None. All changes implement complete behavior; no placeholder data flows to UI.

## Self-Check: PASSED

- `[x]` `tests/test_qramm_routes_typed_response.py` — FOUND
- `[x]` `tests/test_banner_comment_corrected.py` — FOUND
- `[x]` `tests/test_qramm_multiplier_constants.py` — FOUND
- `[x]` `tests/test_db_ensure_columns_generic.py` — FOUND
- `[x]` Commit `b02c877` (RED) — FOUND
- `[x]` Commit `cf8d7a6` (GREEN) — FOUND
- `[x]` Commit `9f83e12` (regression fixes) — FOUND
- `[x]` `quirk/dashboard/api/app.py` — UNCHANGED (D-20)
- `[x]` `quirk/util/targets.py` — UNCHANGED (D-22)
- `[x]` `quirk/qramm/scoring.py` — UNCHANGED (D-19 → routes/qramm.py)
- `[x]` 0 audit row flips (consolidated by 77-05)
