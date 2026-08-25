---
phase: 163
slug: discovery-sub-batch-checkpoint-granularity
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-25
---

# Phase 163 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Sourced from `163-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, project-wide) |
| **Config file** | `pytest.ini` / `pyproject.toml` (existing, unchanged) |
| **Quick run command** | `pytest tests/test_discovery_batch_checkpoint.py -x -q` |
| **Full suite command** | `pytest -x -q` (excludes `-m slow` per project convention) |
| **Estimated runtime** | ~15 seconds (quick) / full suite per existing baseline |

---

## Sampling Rate

- **After every task commit:** `pytest tests/test_discovery_batch_checkpoint.py -x -q`
- **After every plan wave:** `pytest tests/test_discovery_batch_progress.py tests/test_cli_dashboard_discovery_parity.py tests/test_discovery_batch_checkpoint.py -x -q`
- **Before `/gsd:verify-work`:** Full suite green (`pytest -x -q`)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

> Task IDs are filled in by the planner. The behavior/command columns below are
> pre-seeded from RESEARCH.md and are the authoritative coverage contract —
> every row must map to at least one task.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 163-01-T2 / 163-01-T3 | 163-01 | 1 | DISC-08 (c1) | — | Resume skips batches completed before interruption; no re-probe | unit | `pytest tests/test_discovery_batch_checkpoint.py::test_resume_skips_completed_batches -x` | ❌ W0 | ⬜ pending |
| 163-02-T1 | 163-02 | 2 | DISC-08 (c2) | — | No new checkpoint table or `ScanCheckpoint` model change | structural (AST) | `pytest tests/test_discovery_batch_checkpoint.py::test_no_new_checkpoint_table_or_model_change -x` | ❌ W0 | ⬜ pending |
| 163-01-T2 / 163-02-T2 | 163-01, 163-02 | 1 | DISC-08 (c3 / DISC-02) | T-163-01 | A `RuntimeError` batch writes no checkpoint; loop continues; later batches still checkpoint | unit | `pytest tests/test_discovery_batch_checkpoint.py::test_failed_batch_writes_no_checkpoint_and_loop_continues -x` | ❌ W0 | ⬜ pending |
| 163-02-T2 | 163-02 | 2 | DISC-08 (c4 / DISC-06) | — | Single shared chunked-discovery call site preserved (AST lock still passes) | structural (AST) | `pytest tests/test_cli_dashboard_discovery_parity.py -x` | ✅ existing | ⬜ pending |
| 163-01-T2 / 163-02-T1 | 163-01, 163-02 | 1 | DISC-08 (D-02) | — | Batch payloads written unconditionally, not gated on `--cache` | unit | `pytest tests/test_discovery_batch_checkpoint.py::test_batch_cache_written_without_cache_flag -x` | ❌ W0 | ⬜ pending |
| 163-01-T2 | 163-01 | 1 | DISC-08 (D-02) | — | Batch cache ignored on a fresh (non-resume) run | unit | `pytest tests/test_discovery_batch_checkpoint.py::test_batch_cache_ignored_on_fresh_non_resume_run -x` | ❌ W0 | ⬜ pending |
| 163-01-T2 / 163-02-T2 | 163-01, 163-02 | 1 | DISC-08 (D-05) | — | A fully-dead batch (liveness filtered every host) still gets a completion checkpoint | unit | `pytest tests/test_discovery_batch_checkpoint.py::test_fully_dead_batch_still_checkpoints -x` | ❌ W0 | ⬜ pending |
| 163-01-T2 / 163-02-T1 | 163-01, 163-02 | 1 | DISC-08 (D-06) | — | Resume-only cache read uses the 720h TTL, not `args.cache_ttl_hours` | unit | `pytest tests/test_discovery_batch_checkpoint.py::test_resume_read_uses_generous_ttl -x` | ❌ W0 | ⬜ pending |
| 163-01-T1 | 163-01 | 1 | DISC-08 (D-07) | T-163-02 | `NmapOpenPort` round-trips through the serializer pair preserving host/port/protocol/service | unit | `pytest tests/test_discovery_batch_checkpoint.py::test_nmap_open_port_serializer_roundtrip -x` | ❌ W0 | ⬜ pending |
| 163-01-T2 | 163-01 | 1 | DISC-08 (Pitfall 4) | — | A batch already in `_completed_stages` never duplicates its checkpoint row | unit | `pytest tests/test_discovery_batch_checkpoint.py::test_skipped_batch_does_not_duplicate_checkpoint_row -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Planner addenda (2026-08-25)

Four coverage rows added during `/gsd-plan-phase 163` beyond the pre-seeded ten:

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 163-01-T3 | 163-01 | 1 | DISC-08 (c1) | T-163-01 | Two-invocation real-SQLite interruption simulation: batches 1-2 skipped, batch 3 re-attempted, no duplicate rows | integration | `pytest tests/test_discovery_batch_checkpoint.py::test_resume_skips_completed_batches_against_real_db -x` | ❌ W0 | ⬜ pending |
| 163-01-T2 | 163-01 | 1 | DISC-08 (D-06) | T-163-01 | A completed batch whose cache entry expired or was deleted falls through and IS re-probed — a checkpoint alone never causes a skip | unit | `pytest tests/test_discovery_batch_checkpoint.py::test_completed_stage_without_cache_hit_reprobes -x` | ❌ W0 | ⬜ pending |
| 163-02-T1 | 163-02 | 2 | DISC-08 (D-02) | T-163-01 | Per-batch writes are gated on `args.db_path` alone — not `args.cache`, not `args.job_id` | structural (AST) | `pytest tests/test_discovery_batch_checkpoint.py::test_batch_writes_are_not_gated_on_args_job_id -x` | ❌ W0 | ⬜ pending |
| 163-03-T4 | 163-03 | 3 | DISC-08 (c1) | T-163-01 | HUMAN-UAT: resumed inventory equals uninterrupted inventory (zero silently dropped hosts) | manual | UAT-163-04 in `docs/UAT-SERIES.md` | ❌ W3 | ⬜ pending |

**Threat coverage note:** T-163-05 (batch-ordinal drift on target-scope change) and T-163-06
(inventory in `{output_dir}/.cache/` without `--cache`) are documentation-mitigated only and are
verified by Plan 163-03 Task 1's grep acceptance criteria, not by a pytest case.

---

## Wave 0 Requirements

- [ ] `tests/test_discovery_batch_checkpoint.py` — new file covering every DISC-08 criterion
      above. Follow the two-part convention already established by
      `tests/test_discovery_batch_progress.py`:
      - **Part A (mirror-shape unit tests):** a standalone re-implementation of the loop logic
        with mocked nmap calls and a real temp-SQLite-backed `ScanCheckpoint` table via
        `get_session`.
      - **Part B (AST-structural tests):** read the real `run_scan.py` and confirm the
        checkpoint/cache calls are lexically inside the `_chunked` for-loop and correctly gated,
        mirroring `test_cli_dashboard_discovery_parity.py::test_run_nmap_discovery_call_is_inside_chunked_batch_loop`.
- [ ] **Deterministic interruption simulation.** Real interruption (SIGKILL mid-scan) cannot be
      driven from a unit test. Simulate with two sequential invocations against one shared temp
      SQLite DB:
      1. Run the mirror loop with a mocked `run_nmap_discovery` over only the first N batches'
         worth of hosts; let it write real `ScanCheckpoint` rows.
      2. Re-invoke the loop with the FULL host list and assert (a) the
         `run_nmap_discovery` / `run_nmap_liveness_check` mocks are **not** called for batches
         1..N, and (b) `all_open_ports` after the second run is the union of both runs' ports
         (batches 1..N from cache, N+1.. from fresh probing).
      Closest existing precedent for constructing `ScanCheckpoint` rows directly against a temp
      DB: `tests/test_rvw003_scan_session_identity.py`.
- [ ] Framework install: **none required** — pytest, `unittest.mock`, and SQLAlchemy
      `get_session` are already project dependencies with in-repo usage patterns to copy.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end resume of a genuinely interrupted large-CIDR discovery scan | DISC-08 (c1) | Requires a real multi-batch nmap run against the chaos lab and a real process kill; unit tests prove the logic, not the live wiring | Start `quirk scan --discovery nmap` against a >1024-host range, note the `scan_run_id`, `Ctrl-C` after several batches, re-run with `--resume-scan-id <id>`, and confirm the log shows completed batches skipped rather than re-probed |

---

## Security Domain (ASVS L1)

| ASVS Category | Applies | Note |
|---------------|---------|------|
| V2 Authentication | No | No auth surface touched — internal scan-loop state persistence |
| V3 Session Management | No | `scan_run_id` is an internal timestamp-derived identifier; its existing ISO-timestamp validation (`run_scan.py:1499-1504`) is unchanged |
| V4 Access Control | No | No new API surface; `--resume-scan-id` and the SQLite DB are existing local-trust-boundary resources |
| V5 Input Validation | Marginal | New cache key `f"discovery-batch-{scan_run_id}-{batch_num}"` is built only from already-validated `scan_run_id` and an internally-generated integer `batch_num` |
| V6 Cryptography | No | No cryptographic material involved |

### Threats to carry into PLAN.md `<threat_model>`

| ID | Pattern | STRIDE | Mitigation |
|----|---------|--------|------------|
| T-163-01 | A failed batch is wrongly treated as complete, silently dropping hosts from the inventory | Tampering (integrity of the deliverable) | The completion write lives only on the success path of the existing `try/except RuntimeError`; asserted by `test_failed_batch_writes_no_checkpoint_and_loop_continues` |
| T-163-02 | Unbounded disk growth from unconditional per-batch cache writes — D-02 removes the `--cache` gate, so a thousands-of-batches scan writes thousands of small JSON files to `{output_dir}/.cache/` where previously one file was written per scan | Denial of Service (resource exhaustion) | LOW severity — each payload is a small ports list, not raw scan output. Bound by the D-06 720h TTL and documented in `docs/operators-guide.md` as resume state proportional to batch count |
| T-163-03 | Cache-key path traversal via an unsanitized key string | Tampering | Not new: `save_cache`/`load_cache` already build `os.path.join(cdir, f"{key}.json")` from caller-supplied keys project-wide. No externally-controlled input enters the new key |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
