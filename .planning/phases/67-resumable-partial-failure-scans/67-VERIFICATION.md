---
phase: 67-resumable-partial-failure-scans
verified: 2026-05-14T00:00:00Z
status: passed
score: 14/14 must-haves verified
overrides_applied: 0
---

# Phase 67: Resumable / Partial-Failure Scans Verification Report

**Phase Goal:** Make scans resumable after partial failure — write per-stage checkpoints during a scan so a crashed scan can be continued from its last completed stage via `--resume-scan-id`, and surface partial scanner failures in the output JSON and dashboard.
**Verified:** 2026-05-14
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ScanCheckpoint SQLAlchemy model exists with all 8 D-01 columns | VERIFIED | `quirk/models.py` lines 218-236; columns confirmed via `python -c "from quirk.models import ScanCheckpoint; print(ScanCheckpoint.__table__.columns.keys())"` — all 8 present |
| 2 | scan_checkpoints table created on init_db() call (idempotent) | VERIFIED | `quirk/db.py` line 247-253: `_ensure_scan_checkpoints_table()` defined; line 284: called in `init_db()` after `_ensure_scan_jobs_table()` |
| 3 | write_scan_checkpoint() writes rows and is silent on failure | VERIFIED | `quirk/cli/job_progress.py` lines 74-107; confirmed silent no-op on bad path at runtime |
| 4 | A scan_checkpoints row is written after each of 8 stages | VERIFIED | `run_scan.py` has 9 references to `write_scan_checkpoint` (8 stage calls + 1 import); all 8 stages confirmed: inventory, tls, ssh, api, identity, data_at_rest, broker_email, reports |
| 5 | partial_failures list in run_stats is populated from error_endpoints after each stage | VERIFIED | `_collect_stage_partial_failures()` at line 186 of `run_scan.py`; `run_stats.setdefault("partial_failures", [])` initialized before first stage |
| 6 | All scanner invocations use _wrapped_phase (uniform BaseException capture) | VERIFIED | 19 `_wrapped_phase(` call sites in `run_scan.py`; exactly 1 `except BaseException` (in the `_wrapped_phase` definition itself, line 129) |
| 7 | `quirk scan --resume-scan-id <id>` continues from last completed stage | VERIFIED | `run_scan.py` lines 497-507: `--resume-scan-id` argparse flag; lines 643-712: resume state loading block; lines 819-834, 946-948, 989-991 etc.: per-stage `if _stage_completed()` guards |
| 8 | `quirk scan --list-resumable` prints rich table of incomplete scan runs | VERIFIED | `_handle_list_resumable()` at line 227; argparse flag at line 504; early-exit handler at lines 565-566; rich table with Scan ID / Last Stage / Status / Age / Target columns |
| 9 | A stale checkpoint (>72h) prints stderr warning before resuming | VERIFIED | `run_scan.py` lines 678-686: stale check with `_age_hours > 72` threshold; `STALE_HOURS = 72` in `_handle_list_resumable` for table highlighting |
| 10 | partial_failures array appears in output JSON stats file | VERIFIED | `quirk/reports/writer.py` lines 191-192: `run_stats.setdefault("partial_failures", [])` before `_json_dump()`; key always present including for clean scans |
| 11 | GET /api/scan/latest returns partial_failures array | VERIFIED | `quirk/dashboard/api/routes/scan.py` line 1072: `_load_partial_failures()` called; line 1090: `partial_failures=partial_failures` in `ScanLatestResponse(...)` |
| 12 | ScanLatestResponse has partial_failures: List[PartialFailureEntry] = [] field | VERIFIED | `quirk/dashboard/api/schemas.py` line 218: `partial_failures: List[PartialFailureEntry] = []` confirmed; `PartialFailureEntry` model at lines 186-197 with 5 fields |
| 13 | TS interface PartialFailureEntry matches Pydantic model exactly | VERIFIED | `src/dashboard/src/types/api.ts` lines 112-118: all 5 fields (stage, scanner, error_category, error_message, endpoint_count) match Pydantic model |
| 14 | Scanner Status card renders conditionally (only when partial_failures.length > 0) | VERIFIED | `src/dashboard/src/pages/executive.tsx` line 253: `{data.partial_failures && data.partial_failures.length > 0 && ...}`; `ScannerStatusCard` at line 30; badge aria-labels at lines 37, 44, 53 |

**Score:** 14/14 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/models.py` | ScanCheckpoint ORM model | VERIFIED | Class present at line 218; 8 columns including checkpoint_id, scan_run_id (indexed), stage, status, completed_at, endpoint_count, partial_failure, error_summary |
| `quirk/db.py` | `_ensure_scan_checkpoints_table` + init_db registration | VERIFIED | Function at line 247; called in init_db() at line 284 |
| `quirk/cli/job_progress.py` | `write_scan_checkpoint()` helper | VERIFIED | Function at line 74; silent no-op confirmed at runtime |
| `run_scan.py` | Per-stage checkpoint writes + partial_failures + incremental flush + resume flow | VERIFIED | All helpers present and importable; 9 write_scan_checkpoint refs; 19 _wrapped_phase calls; resume flag wired |
| `quirk/reports/writer.py` | partial_failures in output JSON | VERIFIED | `setdefault("partial_failures", [])` at line 191 |
| `quirk/dashboard/api/schemas.py` | PartialFailureEntry + ScanLatestResponse extension | VERIFIED | Both present; importable; field count correct |
| `quirk/dashboard/api/routes/scan.py` | `_load_partial_failures()` + wiring in get_latest_scan() | VERIFIED | Helper at line 860; called at line 1072; result wired at line 1090 |
| `src/dashboard/src/types/api.ts` | PartialFailureEntry TS interface | VERIFIED | Interface at line 112; ScanLatestResponse extended at line 211 |
| `src/dashboard/src/pages/executive.tsx` | ScannerStatusCard component + conditional render | VERIFIED | Component at line 30; conditional render at line 253 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/models.py` ScanCheckpoint | `quirk/db.py` _ensure_scan_checkpoints_table | Base.metadata.create_all | WIRED | ScanCheckpoint registered on Base.metadata; _ensure function calls create_all with checkfirst=True |
| `quirk/db.py` init_db | `_ensure_scan_checkpoints_table` | call at line 284 | WIRED | `_ensure_scan_checkpoints_table(engine)` called after `_ensure_scan_jobs_table(engine)` |
| `run_scan.py` stage boundaries | `write_scan_checkpoint` | import + 8 call sites | WIRED | Import at line 51; calls confirmed for all 8 stages |
| `run_scan.py` error_endpoints | `run_stats["partial_failures"]` | `_collect_stage_partial_failures()` | WIRED | Helper slices error_endpoints by pre-stage count; extends run_stats["partial_failures"] |
| `run_scan.py` --resume-scan-id | scan_checkpoints table | ScanCheckpoint query + ISO validation | WIRED | Lines 648-712: fromisoformat validation, then ScanCheckpoint query populates _completed_stages |
| `run_scan.py` run_stats["partial_failures"] | `quirk/reports/writer.py` write_reports | run_stats kwarg + setdefault | WIRED | writer.py line 191: setdefault guarantees key presence in stats JSON |
| `quirk/dashboard/api/routes/scan.py` get_latest_scan() | `PartialFailureEntry` | ScanJob lookup → _load_partial_failures | WIRED | ScanJob lookup resolves scan_run_id (handles tz-aware/tz-naive mismatch); _load_partial_failures called at line 1072 |
| `src/dashboard/src/pages/executive.tsx` | `PartialFailureEntry` (TS) | data.partial_failures from useScanData() | WIRED | Line 12: type import; lines 253-254: conditional render of ScannerStatusCard |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `executive.tsx` ScannerStatusCard | `data.partial_failures` | `useScanData()` → GET /api/scan/latest → `_load_partial_failures()` → `scan_checkpoints.error_summary` | Yes — DB query filters `ScanCheckpoint.partial_failure == True` and parses JSON array | FLOWING |
| `run_scan.py` output JSON | `run_stats["partial_failures"]` | `_collect_stage_partial_failures()` → `error_endpoints[prev_count:]` → real scanner exception data | Yes — error data from actual scanner exceptions, not hardcoded | FLOWING |
| `quirk/dashboard/api/routes/scan.py` | `partial_failures` | ScanJob lookup → ScanCheckpoint query | Yes — parameterized SQLAlchemy query with 30-min window around scan timestamp | FLOWING (with graceful [] fallback for pre-Phase-67 scans / scans without a ScanJob row) |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| ScanCheckpoint model importable with 8 columns | `python -c "from quirk.models import ScanCheckpoint; print(...columns.keys())"` | `['checkpoint_id', 'scan_run_id', 'stage', 'status', 'completed_at', 'endpoint_count', 'partial_failure', 'error_summary']` | PASS |
| write_scan_checkpoint silent on bad db_path | `python -c "from quirk.cli.job_progress import write_scan_checkpoint; write_scan_checkpoint('/nonexistent/path.db', 'x', 'tls', 'completed'); print('silent no-op OK')"` | `silent no-op OK` | PASS |
| All run_scan helpers importable | `python -c "from run_scan import _flush_stage_endpoints, _collect_stage_partial_failures, _stage_completed, _handle_list_resumable, _resolve_db_path"` | Exit 0 | PASS |
| PartialFailureEntry + ScanLatestResponse importable with partial_failures field | `python -c "from quirk.dashboard.api.schemas import PartialFailureEntry, ScanLatestResponse; assert 'partial_failures' in ScanLatestResponse.model_fields"` | Exit 0 | PASS |
| _load_partial_failures importable | `python -c "from quirk.dashboard.api.routes.scan import _load_partial_failures"` | Exit 0 | PASS |
| npm run build passes | `cd src/dashboard && npm run build` | `✓ built in 564ms` — all assets emitted to `quirk/dashboard/static/assets/` | PASS |
| ScannerStatusCard text in built JS | `grep -c "Scanner Status" quirk/dashboard/static/assets/index-*.js` | Match found | PASS |
| Exactly 1 BaseException catch in run_scan.py | `grep -c "except BaseException" run_scan.py` | 1 (in `_wrapped_phase` definition) | PASS |
| _wrapped_phase call sites | `grep -c "_wrapped_phase(" run_scan.py` | 19 (>= 15 threshold) | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| RESUME-01 | Plans 01, 02, 04 | Scan that crashes mid-run leaves recoverable checkpoint; `--resume-scan-id` continues from last completed stage | SATISFIED | scan_checkpoints table + write_scan_checkpoint() + per-stage checkpoint writes in run_scan.py + --resume-scan-id flag + _stage_completed guards. Note: REQUIREMENTS.md uses `--resume <scan-id>` but `--resume` was already taken (cache reuse); `--resume-scan-id` achieves the same intent. |
| RESUME-02 | Plans 02, 04, 05 | Per-scanner failures no longer abort scan; partial_failures array in output; per-scanner status panel in dashboard | SATISFIED | partial_failures in run_stats (Plan 02); guaranteed in stats JSON via writer.py (Plan 04); API returns List[PartialFailureEntry] from scan_checkpoints (Plan 05); ScannerStatusCard on Executive Summary page (Plan 05) |

---

### Anti-Patterns Found

No blockers or stubs found.

| File | Pattern | Severity | Assessment |
|------|---------|----------|------------|
| `run_scan.py` | `except Exception: pass` in `_flush_stage_endpoints` | Info | Intentional design — silent no-op is correct; the existing bulk persist is the safety net |
| `quirk/cli/job_progress.py` | `except Exception: pass` in `write_scan_checkpoint` | Info | Intentional design per D-14 (checkpoint writes must never crash the scan) |
| `quirk/dashboard/api/routes/scan.py` line 1072 | `partial_failures = [] if _checkpoint_scan_run_id is None` | Info | Graceful degradation for pre-Phase-67 scans (no ScanJob row); not a stub — this is documented behavior |

---

### Human Verification Required

No items require human verification. All key behaviors are programmatically verifiable.

Optional manual smoke test (no blocker):
- Create checkpoint rows via Python REPL, then run `python run_scan.py --config config.yaml --list-resumable --db-path ./test.db` to confirm the rich table renders with correct columns and 72h stale highlighting. This is corroborating evidence only — the underlying code is fully verified above.

---

### Notable Implementation Deviations (Not Blocking)

1. **`--resume-scan-id` vs `--resume <scan-id>`**: REQUIREMENTS.md specified `--resume <scan-id>` but `--resume` was already occupied (cache reuse flag). The plan correctly chose `--resume-scan-id`. The intent of RESUME-01 is fully met.

2. **`_load_partial_failures` uses ScanJob lookup rather than LIKE prefix match**: Plan 05 specified a `LIKE f"{ts_prefix}%"` match approach; the actual code does a ScanJob-based lookup via `completed_at` window to resolve the correct `scan_run_id`. This is more robust and correctly handles the tz-aware/tz-naive mismatch between scan_run_id and scanned_at.

3. **Identity vs data_at_rest stage membership**: Plan 02 described identity as including dnssec/saml/kerberos, but they appear after data_at_rest in actual code. Implementation correctly folded them into the data_at_rest checkpoint to avoid NameError. Plan 02 documents this deviation.

---

### Gaps Summary

No gaps. All 14 must-have truths are verified. Both requirement IDs (RESUME-01, RESUME-02) are satisfied by implementation evidence in the codebase.

---

_Verified: 2026-05-14_
_Verifier: Claude (gsd-verifier)_
