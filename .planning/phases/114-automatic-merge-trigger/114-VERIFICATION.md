---
phase: 114-automatic-merge-trigger
verified: 2026-05-26T00:00:00Z
status: human_needed
score: 9/9 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Visual review of operators-guide.md §8.9 Automatic Merge completeness against 114-CONTEXT.md decisions"
    expected: "Section covers toggle, both trigger conditions, default-ON, in-flight safety, IntegrationDelivery auto_merge audit rows, and unchanged manual merge command — all matching CONTEXT D-07 through D-10"
    why_human: "Documentation quality and completeness against a design-decision checklist cannot be verified by grep alone; human must confirm the narrative accurately reflects all 114-CONTEXT.md decisions and is operator-actionable"
---

# Phase 114: Automatic Merge Trigger Verification Report

**Phase Goal:** The console automatically merges all pushed sensor results once every enrolled sensor has checked in, eliminating the mandatory manual `quirk sensor merge` step for the common deployment case.
**Verified:** 2026-05-26
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After the last non-revoked enrolled sensor pushes (auto-merge ON, all-sensors-in), a MergeRun row is produced with no manual `quirk sensor merge` call | VERIFIED | `test_all_sensors_in_triggers_merge` passes: sensor-a push → 0 MergeRun; sensor-b push → exactly 1 MergeRun. BackgroundTask fires synchronously under TestClient immediately after `client.post()`. |
| 2 | With auto-merge disabled in config, the same final push produces no MergeRun | VERIFIED | `test_auto_merge_disabled` passes: `enabled=false` in config → 0 MergeRun after both sensors push. `_eval_trigger_condition` fast-exits `False` when `enabled` is falsey. |
| 3 | A merge that raises leaves the triggering push's accepted response and ingested rows intact, and writes an IntegrationDelivery destination=auto_merge status=failed row with safe_str(exc) | VERIFIED | `test_merge_failure_isolated` passes: merge_scan patched to raise RuntimeError → `push.status == "accepted"`, 0 MergeRun, exactly 1 IntegrationDelivery(destination="auto_merge", status="failed") with non-empty error_summary. Test asserts `"Traceback" not in audit_row.error_summary`. Production code uses `safe_str(exc)` with comment `# T-109-07: never str(exc)`. |
| 4 | cadence-window mode triggers a merge on the push that crosses the elapsed-window boundary, emitting coverage_warning for not-yet-in sensors | VERIFIED | `test_cadence_window_triggers` passes: `cadence_window_minutes=0` + prior MergeRun in past → new MergeRun produced; `coverage_warning_json` names the missing sensor. |
| 5 | Revoked sensors (SensorToken.revoked_at set) are excluded from the all-sensors-in set | VERIFIED | `test_revoked_sensor_excluded` passes: sensor-b token revoked → pushing only sensor-a (sole active sensor) → exactly 1 MergeRun. `_eval_trigger_condition` uses SensorToken.revoked_at subquery to exclude revoked sensors. |
| 6 | All 6 CONTEXT acceptance tests exist and pass with no manual merge call | VERIFIED | 7 tests in `tests/test_auto_merge_trigger.py` (6 plan-mandated + 1 D-04 discrete test). All 7 pass: `python -m pytest tests/test_auto_merge_trigger.py -q` → `7 passed`. |
| 7 | Regression: pre-existing sensor_ingest and sensor_merge tests remain green | VERIFIED | `python -m pytest tests/ -k "sensor_ingest or sensor_merge or auto_merge" -q` → `17 passed, 2650 deselected`. Zero regressions. |
| 8 | Operators can read in operators-guide.md how to enable/disable auto-merge, select the trigger condition, and find auto-merge audit rows | VERIFIED | `docs/operators-guide.md` contains `auto_merge`, `all-sensors-in`, `cadence-window` (grep confirmed). §8.9 added with toggle, both trigger conditions, IntegrationDelivery audit row table, SQLite query example, and explicit AUTOMERGE-03 statement that `quirk sensor merge` is unchanged. |
| 9 | The distributed lab e2e oracle notes the auto-merge MergeRun fires before the manual Step 3 merge | VERIFIED | `quantum-chaos-enterprise-lab/expected_results_distributed.md` references `auto_merge` and `auto-merge` (grep confirmed). Oracle documents: auto-merge fires after sensor-b push with MergeRun + IntegrationDelivery(destination="auto_merge",status="ok"); Step 3 manual merge retained as harmless duplicate and AUTOMERGE-03 regression proof. |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/dashboard/api/routes/sensor.py` | `_load_auto_merge_config`, `_eval_trigger_condition`, `run_auto_merge`; BackgroundTasks wired into sensor_push after final commit | VERIFIED | All 4 functions confirmed at lines 128, 148, 204, 347/537. `background_tasks.add_task(run_auto_merge, db_path, config_path)` at L537, after `db.commit()` at L522. Committed at `4684062`. |
| `config.yaml` | `console.auto_merge.{enabled, trigger_condition}` sub-block | VERIFIED | Lines 61-66: `console:` → `auto_merge:` → `enabled: true`, `trigger_condition: all-sensors-in`, commented `cadence_window_minutes: 1440`. YAML parses correctly. Committed at `e977dc2`. |
| `tests/test_auto_merge_trigger.py` | 6+ acceptance tests covering AUTOMERGE-01/02/03 + D-05 + cadence-window | VERIFIED | 7 tests confirmed at lines 210, 247, 273, 307, 360, 411, 471. All 7 pass. Committed at `b07d210`. |
| `docs/operators-guide.md` | Auto-merge operator section (toggle, two trigger conditions, default-ON, audit rows) | VERIFIED | `auto_merge`, `all-sensors-in`, `cadence-window` present (grep pass). Committed at `e8ebd58`. |
| `quantum-chaos-enterprise-lab/expected_results_distributed.md` | Oracle note: auto-merge MergeRun before manual Step 3 | VERIFIED | `auto_merge`/`auto-merge` present (grep pass). Committed at `a0eae5c`. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `sensor_push` | `run_auto_merge` background task | `background_tasks.add_task(run_auto_merge` after final `db.commit()` | VERIFIED | L534-537: `db_path = _default_db_path()`, `config_path = os.environ.get(...)`, `if _eval_trigger_condition(db, config_path): background_tasks.add_task(run_auto_merge, db_path, config_path)`. Only scalar strings passed (Pitfall 1 honored). |
| `run_auto_merge` | `quirk.merge.scan.merge_scan` | `from quirk.merge.scan import merge_scan` inside function + `merge_scan(db, output_dir=output_dir)` | VERIFIED | L212-213 (local import), L229: `result = merge_scan(db, output_dir=output_dir)`. merge_scan called unchanged (D-12). |
| `run_auto_merge` failure path | `IntegrationDelivery(destination="auto_merge", status="failed")` | `safe_str(exc)` in except block | VERIFIED | L244-260: except block logs via `safe_str(exc)`, opens fresh `get_session`, writes `IntegrationDelivery(error_summary=safe_str(exc))`. Comment: `# T-109-07: never str(exc)`. |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `sensor_push` → `_eval_trigger_condition` | `active_sensors`, `latest_merge` | SQLAlchemy queries on `Sensor`, `SensorToken`, `MergeRun` in the request-scoped session (just-committed push data) | Yes — live DB queries | FLOWING |
| `run_auto_merge` | `result["scan_id"]` | `merge_scan(db, output_dir=output_dir)` → real `MergeRun` write + CBOM pipeline | Yes — calls unmodified merge_scan() which queries CryptoEndpoint, writes MergeRun | FLOWING |
| `test_merge_failure_isolated` error_summary | `audit_row.error_summary` | `safe_str(RuntimeError("simulated merge failure"))` via `run_auto_merge` except path | Yes — non-empty string confirmed by test assertion | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `_load_auto_merge_config` returns defaults for nonexistent file | `python -c "from quirk.dashboard.api.routes.sensor import _load_auto_merge_config; r=_load_auto_merge_config('/nonexistent.yaml'); assert r=={'enabled':True,'trigger_condition':'all-sensors-in'}"` | Exit 0, no exception | PASS |
| `sensor_push` signature includes `background_tasks` | `python -c "import inspect; from quirk.dashboard.api.routes import sensor; assert 'background_tasks' in inspect.signature(sensor.sensor_push).parameters"` | Exit 0 | PASS |
| `run_auto_merge` importable with correct attributes | `python -c "from quirk.dashboard.api.routes.sensor import run_auto_merge; import inspect; src=inspect.getsource(run_auto_merge); assert 'safe_str(exc)' in src and 'merge_scan' in src"` | Exit 0 | PASS |
| `config.yaml` parses with correct auto_merge block | `python -c "import yaml; d=yaml.safe_load(open('config.yaml')); am=d['console']['auto_merge']; assert am['enabled'] is True; assert am['trigger_condition']=='all-sensors-in'"` | Exit 0 | PASS |
| All 7 acceptance tests pass | `python -m pytest tests/test_auto_merge_trigger.py -q` | `7 passed, 0 failures` | PASS |
| Regression suite green | `python -m pytest tests/ -k "sensor_ingest or sensor_merge or auto_merge" -q` | `17 passed, 0 failures` | PASS |

---

### Probe Execution

No `probe-*.sh` files declared or present for Phase 114. Step 7c: SKIPPED (no probes declared in PLAN or SUMMARY files).

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AUTOMERGE-01 | 114-01, 114-02 | Console automatically merges once all enrolled sensors have checked in, without manual `quirk sensor merge` | SATISFIED | `background_tasks.add_task(run_auto_merge...)` after final commit; `test_all_sensors_in_triggers_merge` proves 1 MergeRun produced with no manual merge call. REQUIREMENTS.md row marked `[x]`. |
| AUTOMERGE-02 | 114-01, 114-02 | Auto-merge configurable (enable/disable + trigger condition); merge failure never blocks/fails/rolls back in-flight push | SATISFIED | `_load_auto_merge_config` + `_eval_trigger_condition` config-gated; `test_auto_merge_disabled` proves disabled=0 MergeRun; `test_merge_failure_isolated` proves push=accepted on merge raise; entire merge in task-owned try/except after response sent (D-11). REQUIREMENTS.md row marked `[x]`. |
| AUTOMERGE-03 | 114-01, 114-02, 114-03 | Manual `quirk sensor merge` command still works, coexists with auto-merge, no regression to v5.4 merge behavior | SATISFIED | git log confirms `quirk/merge/scan.py` and `quirk/cli/sensor_cmd.py` have zero changes in Phase 114 commits. `test_manual_merge_regression` passes: Option-A union, endpoint_count≥2, sensor_count=2, scanned_at not rewritten. operators-guide.md §8.9 explicitly states manual merge unchanged. REQUIREMENTS.md row marked `[x]`. |

All 3 requirement IDs from PLAN frontmatter accounted for. No orphaned requirements found in REQUIREMENTS.md for Phase 114.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `tests/test_auto_merge_trigger.py` L88 | `datetime.utcnow()` (DeprecationWarning) | Info | Deprecated usage in test harness helper `_build_envelope`, not in production code. Matches pattern in `tests/test_sensor_ingest.py` (pre-existing test style). Not a blocker — test passes cleanly, warning only. |

No `TBD`, `FIXME`, `XXX`, `HACK`, or `PLACEHOLDER` markers found in any Phase 114 modified files. No stub patterns (empty returns, hardcoded `[]` or `{}`) in production code paths.

---

### Human Verification Required

#### 1. operators-guide.md §8.9 Automatic Merge Completeness

**Test:** Open `docs/operators-guide.md` and review the Automatic Merge section (§8.9, located between §8.6 and §8.7 in the Distributed Sensor Deployment section). Confirm the section covers all of the following from 114-CONTEXT.md:
- Default-ON behavior with explanation of BackgroundTask timing
- `console.auto_merge.enabled: false` config snippet for manual-only control
- `all-sensors-in` condition explanation (non-revoked enrolled sensors, revoked_at exclusion)
- `cadence-window` condition explanation (elapsed time, coverage_warning)
- Optional `cadence_window_minutes` (defaults to per-sensor expected_cadence_minutes / 1440)
- In-flight safety note (toggle read per-push)
- IntegrationDelivery audit row table (destination="auto_merge", status ok/failed, error_summary)
- Explicit statement that `quirk sensor merge` is unchanged and fully available (AUTOMERGE-03)

**Expected:** All 8 items above are present, accurate, and operator-actionable without requiring a code read.

**Why human:** Documentation quality and narrative completeness against a design-decision checklist cannot be verified by grep. Human must confirm the section is accurate, clearly written, and covers all CONTEXT D-07 through D-10 decisions.

---

### Gaps Summary

No gaps. All automated checks pass. One human verification item remains (UAT-114-03: operator docs visual review), which prevents status from reaching `passed`.

---

_Verified: 2026-05-26_
_Verifier: Claude (gsd-verifier)_
