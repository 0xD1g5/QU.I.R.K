---
phase: 69
plan: 06
subsystem: engine/rate_limiter
tags: [block-06, cr-07, cr-08, threading, condition, rate-limiter]
requires: []
provides:
  - "TokenBucket with capacity guard and Condition-based wait"
affects:
  - quirk/run_scan.py
tech_stack:
  added: []
  patterns:
    - "threading.Condition replaces threading.Lock + time.sleep busy-wait"
    - "Capacity guard raises ValueError on oversized acquire (no infinite loop)"
key_files:
  created:
    - tests/test_rate_limiter.py
  modified:
    - quirk/engine/rate_limiter.py
decisions:
  - "D-01: oversized acquire (tokens > capacity) raises ValueError"
  - "D-02: threading.Condition replaces Lock + sleep(0.01) busy-wait"
  - "D-03: rate <= 0 fast-path returns before Condition block"
metrics:
  duration_minutes: 4
  tasks_completed: 1
  files_changed: 2
  completed: 2026-05-14
---

# Phase 69 Plan 06: BLOCK-06 TokenBucket Hardening Summary

Closed BLOCK-06 (CR-07, CR-08) by replacing `quirk/engine/rate_limiter.py::TokenBucket`'s
`threading.Lock` + `time.sleep(0.01)` busy-wait with a `threading.Condition` wait loop
and adding a capacity guard that raises `ValueError` immediately when the caller requests
more tokens than the bucket can ever hold.

## Goal

Eliminate the infinite-loop hazard (CR-07: `acquire(n > capacity)` could never satisfy
the refill condition) and the thundering-herd contention (CR-08: every blocked thread
spun on `time.sleep(0.01)` regardless of refill rate).

## What Changed

### `quirk/engine/rate_limiter.py` (modified)

- `__init__`: `self.lock = threading.Lock()` → `self._cond = threading.Condition()`.
  All other fields unchanged.
- `acquire(tokens=1.0)`:
  1. `if self.rate <= 0: return` — unlimited fast path (D-03), avoids Condition acquisition entirely.
  2. `if tokens > self.capacity: raise ValueError(...)` — capacity guard (D-01); message
     mentions both `tokens` and `capacity` for diagnosability.
  3. `with self._cond: while True: <refill> ; if enough: deduct + notify_all + return ; else: wait(timeout=wait_secs)` —
     Condition-based wait (D-02). `wait_secs` is computed from the deficit and the configured rate, so threads sleep
     exactly long enough for the next refill rather than spinning at 100 Hz.
- No `time.sleep` references remain in the module. `time.perf_counter` is still used for refill accounting,
  so the `import time` line stays.

### `tests/test_rate_limiter.py` (created from scratch)

Four unit tests:

| Test | Asserts |
|------|---------|
| `test_acquire_raises_when_tokens_exceed_capacity` | `TokenBucket(rate=10, capacity=5).acquire(tokens=6)` raises `ValueError` mentioning "tokens" and "capacity" |
| `test_unlimited_rate_fast_path` | `TokenBucket(rate=0).acquire()` returns in < 100 ms |
| `test_acquire_blocks_via_condition_no_busy_wait` | After draining a `rate=10, capacity=1` bucket, a second `acquire()` from a worker thread completes within 2 s while `time.sleep` is monkey-patched to raise — proves `Condition.wait` is the only wait primitive |
| `test_acquire_default_token_one_succeeds` | Default `acquire()` (tokens=1.0) on a fresh bucket succeeds |

## Acceptance Checks

| Check | Result |
|-------|--------|
| `pytest tests/test_rate_limiter.py -x -q` | 4 passed in 0.11s |
| `grep -c 'time.sleep' quirk/engine/rate_limiter.py` | 0 |
| `grep -c '_cond' quirk/engine/rate_limiter.py` | 4 (≥ 3 required) |
| `grep -c 'self.lock' quirk/engine/rate_limiter.py` | 0 |
| `python -m compileall quirk/engine/rate_limiter.py` | exit 0 |

## Public API Stability

`TokenBucket(rate_per_sec, capacity=None)` constructor and `acquire(tokens=1.0)` signature
unchanged. The sole caller, `run_scan.py:716`, instantiates `TokenBucket(args.rate_limit, capacity=max(1.0, args.rate_limit))`
and calls `.acquire()` with no `tokens=` argument — both call shapes remain valid. The new
`ValueError` is reachable only when a future caller explicitly passes `tokens > capacity`,
which no current caller does.

## Commits

- `a4251f0` — `test(69-06): add failing tests for TokenBucket capacity guard and Condition wait` (RED gate)
- `03649b8` — `fix(69-06): replace TokenBucket lock+sleep with threading.Condition` (GREEN gate)

## Deviations from Plan

None — plan executed exactly as written. CONTEXT.md D-02 code shape applied verbatim.

## Self-Check: PASSED

- File `quirk/engine/rate_limiter.py` exists and contains `_cond` (4 refs), no `time.sleep`, no `self.lock`.
- File `tests/test_rate_limiter.py` exists with all four named tests.
- Commit `a4251f0` (test RED) present in git log.
- Commit `03649b8` (fix GREEN) present in git log.

## TDD Gate Compliance

- RED gate (`test(69-06): ...`) — `a4251f0`
- GREEN gate (`fix(69-06): ...`) — `03649b8`
- REFACTOR gate — not needed (implementation matched D-02 shape on first pass)
