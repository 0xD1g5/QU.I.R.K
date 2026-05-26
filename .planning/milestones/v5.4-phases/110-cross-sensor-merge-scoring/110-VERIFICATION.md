---
phase: 110-cross-sensor-merge-scoring
verified: 2026-05-25T00:00:00Z
status: human_needed
score: 7/7 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run `quirk sensor merge` against a console with at least one enrolled sensor that has pushed data and one that is overdue"
    expected: "Command prints Merged scan_id, Score (rating), and a WARNING block listing the overdue sensor; exits 0"
    why_human: "Requires a live console DB with real Sensor rows and scanned CryptoEndpoint data; CLI unit tests use monkeypatched merge_scan"
  - test: "Run `quirk sensor merge` from two physically separate sensor pushes (same RFC1918 host:port, different segment/sensor_id) and inspect the produced CBOM JSON"
    expected: "CBOM contains two distinct certificate components and two distinct TLS-protocol components for the shared host:port, each bom_ref prefixed with its sensor_id"
    why_human: "UAT-110-06 (Series 110) — end-to-end multi-sensor deployment scenario; unit test covers the logic but not the physical push path"
---

# Phase 110: Cross-Sensor Merge Scoring Verification Report

**Phase Goal:** A consultant can trigger a merge across all sensor data and receive one canonical CBOM and one quantum-readiness score, with explicit warning when any enrolled sensor is missing.
**Verified:** 2026-05-25
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | merge_scan() runs build_evidence_summary → compute_readiness_score → build_cbom over the union; engines not forked | VERIFIED | quirk/merge/scan.py L200-204: single call chain; `grep -c "compute_readiness_score" quirk/merge/scan.py` = 1; no engine code copied |
| 2 | Single compute_readiness_score call over the union (Option A), never an average; no `/ len(` in score path; test_option_a_score_not_averaged passes | VERIFIED | `grep "/ *len(" quirk/merge/scan.py` returns nothing in score path; test PASSES (1/1 collected) |
| 3 | _sensor_prefix threaded through exactly 4 bom_ref sites; two sensors same host:port → 2 distinct CBOM components; NULL sensor_id byte-stable; CODE_SIGNING fallback excluded | VERIFIED | `grep -n "_sensor_prefix" builder.py` = 1 def (L441) + 4 call sites (L711, L772, L858, L911); codesign/ lines (L807, L811) untouched; test_two_sensors_same_ip_two_components PASSES; test_null_sensor_id_backward_compat PASSES |
| 4 | coverage_warning derived from Sensor.last_push_at + 2×cadence; null when all current; never-pushed = overdue | VERIFIED | quirk/merge/scan.py L49-60: `if s.last_push_at is None` → overdue; `now > last_push_at + 2*cadence` → overdue; L62-70: returns None when overdue list empty; tests test_coverage_warning_overdue_sensor and test_coverage_warning_null_when_current PASS |
| 5 | merge does NOT rewrite CryptoEndpoint.scanned_at; merged result persisted as MergeRun row with new scan_id | VERIFIED | `grep -n "\.scanned_at *=" quirk/merge/scan.py` returns only a SQLAlchemy filter `==` on L102 (not assignment); MergeRun persisted at L210-219; test_scanned_at_preserved PASSES; test_merge_run_persisted PASSES |
| 6 | `quirk sensor merge` CLI is a thin wrapper printing scan_id + score + coverage summary | VERIFIED | quirk/cli/sensor_cmd.py _cmd_merge (L701-723): lazy imports merge_scan, calls it once, prints result; `grep "build_evidence_summary\|compute_readiness_score" quirk/cli/sensor_cmd.py` returns nothing (no inlined logic); test_merge_cli_no_merge_logic_inlined PASSES |
| 7 | MergeRun table declared via additive ORM-model path (no backward-compat break) | VERIFIED | quirk/models.py L338-357: plain Column class, no relationship(); quirk/db.py L376 _ensure_merge_runs_table def + L421 call in init_db; test_sensor_ingest.py (26 tests) and test_console_cmd.py all PASS with no regression |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/cbom/builder.py` | _sensor_prefix helper + 4 call sites | VERIFIED | 1 def L441, calls at L711/L772/L858/L911 |
| `tests/test_cbom_builder.py` | MERGE-03 two-segment + NULL backward-compat tests | VERIFIED | test_two_sensors_same_ip_two_components + test_null_sensor_id_backward_compat present and PASS; full suite 34/34 |
| `quirk/merge/__init__.py` | Package marker | VERIFIED | File exists (empty package marker) |
| `quirk/merge/scan.py` | merge_scan() standalone callable | VERIFIED | 231 lines; exports merge_scan; full pipeline implemented |
| `quirk/models.py` | MergeRun ORM model (plain Column, no relationship()) | VERIFIED | class MergeRun at L338; no relationship() in class body |
| `quirk/db.py` | _ensure_merge_runs_table called from init_db | VERIFIED | def at L376; called at L421 inside init_db |
| `tests/test_merge_scan.py` | Option A, coverage_warning, scanned_at-preserved unit tests | VERIFIED | 8 tests; all named variants present and PASS |
| `quirk/cli/sensor_cmd.py` | merge subparser + dispatch + _cmd_merge thin wrapper | VERIFIED | add_parser("merge") at L118; dispatch at L139-140; _cmd_merge at L701 |
| `tests/test_merge_cli.py` | CLI dispatch test asserting scan_id/score/warning output | VERIFIED | 4 tests; all PASS |
| `docs/UAT-SERIES.md` | merge command UAT coverage + Last Updated bump | VERIFIED | "sensor merge" present; Series 110 block exists |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| quirk/merge/scan.py:merge_scan | build_evidence_summary → compute_readiness_score → build_cbom | single call over union (findings=None) | VERIFIED | L200: `evidence = build_evidence_summary(union, findings=None)`; L201: `score_result = compute_readiness_score(...)`; L204: `build_cbom(union)` |
| quirk/merge/scan.py:_build_coverage_warning | Sensor.last_push_at + expected_cadence_minutes | overdue = now > last_push_at + 2*cadence | VERIFIED | L49-60: None check + cadence arithmetic using Sensor.last_push_at |
| quirk/db.py:init_db | merge_runs table | _ensure_merge_runs_table(engine) | VERIFIED | L421: `_ensure_merge_runs_table(engine)` inside init_db |
| quirk/cli/sensor_cmd.py:_cmd_merge | quirk.merge.scan.merge_scan | lazy import + get_session + print result | VERIFIED | L707: `from quirk.merge.scan import merge_scan`; L714: `result = merge_scan(db, stale_days=args.stale_days)` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| quirk/merge/scan.py | union (list of CryptoEndpoint) | _assemble_union() DB query via func.max subquery join | Yes — SQLAlchemy queries against CryptoEndpoint table | FLOWING |
| quirk/merge/scan.py | coverage_warning | _build_coverage_warning() reading Sensor.last_push_at | Yes — DB query against Sensor table | FLOWING |
| quirk/merge/scan.py | score_result | compute_readiness_score(build_evidence_summary(union)) | Yes — real scoring pipeline over union | FLOWING |
| quirk/cli/sensor_cmd.py | result dict | merge_scan(db, ...) return value | Yes — delegated to merge_scan; no hardcoded returns | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| python -m compileall quirk run_scan.py | `python -m compileall quirk run_scan.py -q` | 0 errors | PASS |
| All merge + CBOM tests | `pytest tests/test_merge_scan.py tests/test_merge_cli.py tests/test_cbom_builder.py -q` | 46 passed | PASS |
| Regression: test_sensor_ingest + test_console_cmd | `pytest tests/test_sensor_ingest.py tests/test_console_cmd.py -q` | 26 passed | PASS |
| test_option_a_score_not_averaged (MERGE-02) | `pytest -k test_option_a_score_not_averaged -v` | PASSED | PASS |
| test_two_sensors_same_ip_two_components (MERGE-03) | `pytest -k two_sensors_same_ip -v` | PASSED | PASS |
| test_null_sensor_id_backward_compat (MERGE-03) | `pytest -k null_sensor_id_backward_compat -v` | PASSED | PASS |
| test_scanned_at_preserved (MERGE-05) | `pytest -k test_scanned_at_preserved -v` | PASSED | PASS |
| No / len( in score path | `grep "/ *len(" quirk/merge/scan.py` | no output | PASS |
| No .scanned_at = assignment in merge_scan | `grep -n "\.scanned_at *=" quirk/merge/scan.py` | only SQLAlchemy == filter on L102 | PASS |
| No TBD/FIXME/XXX debt markers in phase files | `grep "TBD\|FIXME\|XXX" quirk/merge/scan.py quirk/cbom/builder.py quirk/models.py quirk/db.py quirk/cli/sensor_cmd.py` | no output | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| MERGE-01 | 110-02 | Canonical build_evidence_summary → compute_readiness_score → build_cbom over the union; engines not forked | SATISFIED | merge_scan() calls existing engines unmodified; test_merge_pipeline_uses_existing_engines PASSES |
| MERGE-02 | 110-02 | Option A union scoring, never averaged | SATISFIED | Single compute_readiness_score call (L201); no `/ len(` in score path; test_option_a_score_not_averaged PASSES |
| MERGE-03 | 110-01 | Two distinct CBOM components for same RFC1918 host:port in different segments | SATISFIED | _sensor_prefix threaded through 4 sites; test_two_sensors_same_ip_two_components PASSES; NULL backward-compat confirmed |
| MERGE-04 | 110-02 | coverage_warning for overdue/offline sensors | SATISFIED | _build_coverage_warning uses Sensor.last_push_at; both warning tests PASS |
| MERGE-05 | 110-02, 110-03 | quirk sensor merge CLI, new scan_id, source scanned_at not rewritten | SATISFIED | _cmd_merge thin wrapper exists; MergeRun persisted; test_scanned_at_preserved PASSES |

---

### Anti-Patterns Found

None. No TBD/FIXME/XXX markers, no placeholder returns, no inlined scoring logic in CLI, no averaging in score path, no scanned_at mutation.

---

### Human Verification Required

#### 1. End-to-End CLI Run with Live Sensor Data

**Test:** Start a console with at least two enrolled sensors. Allow one to go overdue (or set last_push_at in the past). Run `quirk sensor merge`.
**Expected:** Output contains `Merged scan_id:`, `Score: N (rating)`, and a `WARNING:` block listing the overdue sensor ID(s) with `  - sensor-id` indented lines. Exit code 0.
**Why human:** CLI unit tests monkeypatch merge_scan. Real execution requires a console DB with live Sensor rows and CryptoEndpoint push data from the Phase 109 ingest path.

#### 2. Two-Segment Same-IP CBOM Component Verification

**Test:** Push data from two sensors (sensor-a / sensor-b) both reporting host 10.0.0.5:443 (or any shared RFC1918 address). Run `quirk sensor merge`. Inspect the CBOM JSON output.
**Expected:** The CBOM JSON contains two certificate components: `crypto/certificate/sensor-a:10.0.0.5:443` and `crypto/certificate/sensor-b:10.0.0.5:443`, and two TLS-protocol components with the same per-sensor prefixes. No collision.
**Why human:** Unit tests inject in-memory CryptoEndpoint objects. This test requires real sensor pushes through the Phase 109 HTTP ingest path to verify the full end-to-end bom_ref keying works in practice (UAT-110-05/06).

---

### Gaps Summary

None. All 7 must-haves are VERIFIED by direct code inspection and live test execution. The two human verification items are operational deployment checks for the full sensor push → merge → CBOM path, not code defects.

---

_Verified: 2026-05-25_
_Verifier: Claude (gsd-verifier)_
