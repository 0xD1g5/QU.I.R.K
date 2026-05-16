---
phase: 67-resumable-partial-failure-scans
plan: "04"
subsystem: scan-orchestration
tags: [resumable-scans, checkpoint, partial-failures, resume-cli, run_scan, writer]
one_liner: "Resume CLI surface (--resume-scan-id / --list-resumable) wired into run_scan.py with per-stage skip guards and partial_failures guaranteed in stats JSON"
requires:
  - run_scan._flush_stage_endpoints       # from plan 02
  - run_scan._collect_stage_partial_failures  # from plan 02
  - quirk.models.ScanCheckpoint           # from plan 01
  - quirk.models.ScanJob                  # from plan 01
  - quirk.cli.job_progress.write_scan_checkpoint  # from plan 01
provides:
  - run_scan.--resume-scan-id argparse flag
  - run_scan.--list-resumable argparse flag
  - run_scan._handle_list_resumable
  - run_scan._resolve_db_path
  - run_scan._stage_completed
  - run_scan resume flow (_completed_stages, _resumed_endpoints)
  - quirk.reports.writer partial_failures guaranteed in run-stats JSON
affects:
  - run_scan.py
  - quirk/reports/writer.py
tech_stack:
  added: []
  patterns:
    - Early-exit handler pattern (args.list_resumable -> _handle_list_resumable -> sys.exit)
    - if _stage_completed() / else guard wrapping each scan stage
    - datetime.fromisoformat() for ISO timestamp validation before DB query (T-67-04-01)
    - run_stats.setdefault("partial_failures", []) idempotency in writer.py
key_files:
  created: []
  modified:
    - run_scan.py
    - quirk/reports/writer.py
decisions:
  - "broker_email resume guard unifies email + broker in one if/else block — plan describes them as a single stage in scan_checkpoints and this keeps the resume logic consistent with checkpoint schema"
  - "data_at_rest resume guard wraps all 8 sub-scanners (S3, Blob, K8S, GCS, DNSSEC, SAML, Kerberos, Vault) in a single if/else to avoid deep nesting that would make the code unreadable"
  - "inventory resume guard also reconstructs tls_targets and ssh_targets from _resumed_endpoints (best-effort protocol filtering) so scanner stages can use them on resume even if fingerprinting is skipped"
  - "reports stage always re-runs even if 'reports' in _completed_stages — cheap operation, user wants fresh output files"
metrics:
  duration: "~18 min"
  completed: "2026-05-14"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 67 Plan 04: Resume CLI Surface + Output JSON partial_failures Summary

Resume CLI surface (--resume-scan-id and --list-resumable) added to run_scan.py. Per-stage skip guards wired for all 7 scanner stages. partial_failures key guaranteed in stats JSON output via writer.py. Closes RESUME-01 (resumable scans) and the output-JSON half of RESUME-02.

## What Was Built

### Task 1: --list-resumable flag + --resume-scan-id flag in run_scan.py

**Argparse additions** — Two new arguments added after the existing `--resume` flag:

- `--resume-scan-id SCAN_RUN_ID` — takes an ISO timestamp scan_run_id to resume
- `--list-resumable` — flag that exits after printing a rich table of incomplete scans

**`_resolve_db_path(args)`** — Module-level helper that reads `--db-path` or falls back to loading `cfg.output.db_path` from `--config`, or defaults to `./quirk.db`.

**`_handle_list_resumable(args)`** — Module-level function that queries `scan_checkpoints` for runs that have checkpoint rows but no completed `reports` stage. Prints a rich table with columns: Scan ID | Last Stage | Status | Age | Target. Rows older than 72h are highlighted yellow. Empty result prints plain text message.

**`_stage_completed(completed_stages, stage)`** — Module-level predicate helper. Returns `True` if `stage` is in the completed stages set.

**Early-exit handler** — `if args.list_resumable: _handle_list_resumable(args); sys.exit(0)` added immediately after `args = parser.parse_args()`.

Commit: `9b468ec`

### Task 2: Resume flow in run_scan() + partial_failures in output JSON

**Resume state loading block** (in `main()`, after `scan_run_id` assignment):

1. Read `args.resume_scan_id`
2. Validate ISO timestamp format via `datetime.fromisoformat()` (T-67-04-01 mitigation — invalid value → start fresh scan)
3. Override `scan_run_id` with the supplied value so all checkpoints write to the correct run
4. Load `_completed_stages` from `scan_checkpoints` (status in completed|partial)
5. Check age of last checkpoint → emit `>72h` warning to stderr if stale
6. Load `_resumed_endpoints` from `CryptoEndpoint` where `scanned_at` is within 1 second of the original scan timestamp

**Per-stage skip guards** — Each of the 7 scanner stages wrapped in `if _stage_completed() / else`:

| Stage | Skip behavior when completed |
|-------|------------------------------|
| inventory | Reconstructs inventory_endpoints, tls_targets, ssh_targets from _resumed_endpoints by protocol |
| tls | Restores tls_endpoints (protocol starts with TLS or HTTPS) |
| ssh | Restores ssh_endpoints (protocol == SSH) |
| api | Restores jwt, container, source endpoints separately |
| identity | Restores aws, azure, gcp, db endpoints separately |
| data_at_rest | Restores s3, blob, k8s, gcs, dnssec, saml, kerberos, vault endpoints |
| broker_email | Restores email, kafka, rabbit, redis endpoints |
| reports | Always re-runs with log notice (cheap, fresh output files) |

**`partial_failures` in writer.py** — `run_stats.setdefault("partial_failures", [])` added before `_json_dump(stats_path, run_stats)`. Guarantees the key is always present (even on clean scans) in the run-stats JSON file so consumers never get a `KeyError`.

Commit: `78e41bd`

## Verification Results

All plan verification commands passed:

1. `python -m compileall run_scan.py quirk/reports/writer.py` — PASS (no syntax errors)
2. `--resume-scan-id` in source — PASS
3. `--list-resumable` in source — PASS
4. `_handle_list_resumable` defined — PASS
5. `_resolve_db_path` defined — PASS
6. `Resumable Scans` table title present — PASS
7. `No resumable scans found.` empty state message — PASS
8. `_stage_completed` defined — PASS
9. `resume_scan_id` in source — PASS
10. `_completed_stages` in source — PASS
11. `72` and `old` in source (stale warning) — PASS
12. `_resumed_endpoints` in source — PASS
13. `fromisoformat` in source (ISO validation) — PASS
14. `partial_failures` in writer.py — PASS

## Deviations from Plan

### Deviation 1: broker_email guard unifies email + broker in single if/else

**Rule:** Rule 1 (auto-fix — separate if/else blocks would split a single checkpoint stage into two independent guards, potentially leaving `kafka_endpoints` undefined if email block runs but broker block is skipped)

**Found during:** Task 2

**Issue:** The plan describes broker_email as a single stage in scan_checkpoints, but email and broker are separate code blocks. Independent skip guards would mean the resume logic for one could run without the other, leaving some endpoint variables undefined when the outer stage guard fires.

**Fix:** Unified broker_email into a single `if _stage_completed(_completed_stages, "broker_email") / else` block that covers both email and broker sub-scanners together.

**Files modified:** run_scan.py

**Commit:** 78e41bd

### Deviation 2: data_at_rest all 8 sub-scanners in one block

**Rule:** Rule 2 (correctness — consistent with Plan 02's decision that data_at_rest is a single checkpoint covering all 8 scanners)

**Found during:** Task 2

**Issue:** Wrapping each sub-scanner individually would create 8 separate stage checks against `data_at_rest`, all reading the same checkpoint row. One if/else block is cleaner and consistent with Plan 02's checkpoint design.

**Fix:** All 8 data_at_rest sub-scanners (S3, Blob, K8S, GCS, DNSSEC, SAML, Kerberos, Vault) wrapped in a single `if _stage_completed(_completed_stages, "data_at_rest") / else` block.

**Files modified:** run_scan.py

**Commit:** 78e41bd

## Threat Surface Scan

T-67-04-01 mitigated: `datetime.fromisoformat(scan_run_id)` validation added before using the user-supplied value as a SQLAlchemy filter. ValueError on invalid input → start fresh (logged). SQLAlchemy parameterised queries prevent SQL injection regardless.

No new network endpoints, auth paths, or schema changes introduced. All DB reads are bounded by a single scan_run_id (T-67-04-03 accepted). list-resumable only displays data to the same OS user who ran the scan (T-67-04-04 accepted).

## Known Stubs

None.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| run_scan.py (modified) | FOUND |
| quirk/reports/writer.py (modified) | FOUND |
| commit 9b468ec (Task 1) | FOUND |
| commit 78e41bd (Task 2) | FOUND |
| `--resume-scan-id` in run_scan.py | FOUND |
| `--list-resumable` in run_scan.py | FOUND |
| `_handle_list_resumable` in run_scan.py | FOUND |
| `_resolve_db_path` in run_scan.py | FOUND |
| `_stage_completed` in run_scan.py | FOUND |
| `_completed_stages` in run_scan.py | FOUND |
| `_resumed_endpoints` in run_scan.py | FOUND |
| `fromisoformat` in run_scan.py | FOUND |
| `partial_failures` in writer.py | FOUND |
| `compile run_scan.py` | PASS |
| `compile writer.py` | PASS |
