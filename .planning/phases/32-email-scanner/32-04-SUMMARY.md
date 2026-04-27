---
phase: 32-email-scanner
plan: "04"
subsystem: risk-engine
tags: [email-scanner, risk-engine, run-scan, profiles, findings, integration, quirk]

dependency_graph:
  requires:
    - 32-02-db-config-foundation
    - 32-03-email-scanner-module
  provides:
    - "evaluate_email_endpoints(endpoints) -> List[Dict[str, Any]]"
    - "Profile gating for cfg.connectors.enable_email (standard/deep True; quick False)"
    - "run_scan.py email scan block + endpoints aggregation + findings merge"
  affects:
    - 32-05-chaos-lab-validation
    - 34-motion-intelligence
    - 35-cbom-integration

tech-stack:
  added: []
  patterns:
    - "Email findings emitted by their own evaluate_* function and concatenated to the main findings list (titles unique vs main findings → no dedup collisions)"
    - "ConnectorsCfg gating extended to per-profile flips with hasattr() guards"
    - "tls_targets reused as deduped host list for email scanning (D-01/D-02 — no new target enumeration)"

key-files:
  created: []
  modified:
    - quirk/engine/risk_engine.py
    - quirk/engine/profiles.py
    - run_scan.py
    - tests/test_email_findings.py
    - tests/test_email_run_scan_wiring.py

key-decisions:
  - "evaluate_email_endpoints lives at module-bottom of risk_engine.py (after evaluate_endpoints) and does NOT call _postprocess_findings — it is a side-emitter consumed by run_scan.py and merged into the main findings list"
  - "Findings merge happens INSIDE the existing risk_engine phase timer (single timer covers both calls) so the report retains a single risk_engine span"
  - "Profile gating uses defensive hasattr() guards — first cfg.connectors mutation in profiles.py history; preserves compatibility with future test configs that may construct cfg without ConnectorsCfg"

requirements-completed: [STRUCT-01, EMAIL-08, EMAIL-09]

metrics:
  duration: "~22 minutes"
  completed: "2026-04-27"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 3
---

# Phase 32 Plan 04: Risk-Engine Findings + Run-Scan Integration Summary

**One-liner:** Wired the Phase 32 email scanner into the report pipeline — `evaluate_email_endpoints()` emits EMAIL-08 (STARTTLS downgrade), EMAIL-09 HIGH (RSA-kex / 3DES / RC4), and EMAIL-09 MEDIUM (non-PFS ECDHE without TLS 1.3); `apply_profile()` flips `cfg.connectors.enable_email` for `standard`/`deep` profiles; `run_scan.py` invokes the scanner under the gate, aggregates `email_endpoints`, and merges email findings into the master list.

## Performance

- **Duration:** ~22 minutes
- **Started / Completed:** 2026-04-27
- **Tasks:** 2 (each TDD RED → GREEN)
- **Files created:** 2 (test_email_findings.py, test_email_run_scan_wiring.py)
- **Files modified:** 3 (risk_engine.py, profiles.py, run_scan.py)

## Accomplishments

### `quirk/engine/risk_engine.py` — `evaluate_email_endpoints()`

Appended a new module-level function (line 451+) that scans an iterable of email endpoints and returns `List[Dict[str, Any]]`:

| Trigger | Severity | Title |
|---|---|---|
| `port == 25 and protocol == "SMTP-STARTTLS" and tls_version` | MEDIUM | STARTTLS downgrade risk on SMTP |
| `cipher.startswith("TLS_RSA_WITH_")` / contains `AES128-SHA` / `AES256-SHA` / `3DES` / `RC4` AND no `ECDHE`/`DHE-` | HIGH | Weak cipher suite on email TLS endpoint |
| `pfs is False and tls_version != "TLSv1.3"` (else-branch of weak-cipher gate) | MEDIUM | Non-PFS cipher suite on email TLS endpoint |

D-11 layering preserved: a port-25 endpoint with `AES256-SHA` cipher emits BOTH the STARTTLS-downgrade MEDIUM AND the weak-cipher HIGH because `(host, port, title, recommendation)` keys differ — `_dedupe_findings()` does not collapse them.

### `quirk/engine/profiles.py` — profile-flip placement

| Profile | Branch line | Action |
|---|---|---|
| `quick` | line 75-91 | Comment-only documentation: `cfg.connectors.enable_email` stays at default `False` |
| `deep` | line 108-110 | hasattr-guarded: `cfg.connectors.enable_email = True` |
| standard (`else:`) | line 127-129 | hasattr-guarded: `cfg.connectors.enable_email = True` |

### `run_scan.py` — integration insertion points

| Insertion | Line(s) | Content |
|---|---|---|
| Scanner import | 25 | `from quirk.scanner.email_scanner import scan_email_targets` |
| Risk-engine import | 31 | `from quirk.engine.risk_engine import evaluate_endpoints, evaluate_email_endpoints` |
| Email scan block | 690-704 | `_phase_timer(run_stats, "email_scanning")` gated by `cfg.connectors.enable_email`; reuses deduped `tls_targets` host list |
| Aggregation | 714 | `+ email_endpoints` appended to master `endpoints = (...)` tuple |
| Findings merge | 725-727 | `email_findings = evaluate_email_endpoints(email_endpoints)`; concatenated into `findings` inside the existing `risk_engine` phase timer |

## Task Commits

1. **TDD RED — Task 1 tests** — `ea350a4` (`test(32-04): add failing tests for evaluate_email_endpoints + profile gating`)
2. **GREEN — Task 1 implementation** — `9799d8d` (`feat(32-04): add evaluate_email_endpoints + profile gating for enable_email`)
3. **TDD RED — Task 2 tests** — `82db887` (`test(32-04): add failing structural tests for run_scan.py email wiring`)
4. **GREEN — Task 2 implementation** — `23e9cdf` (`feat(32-04): wire email scanner + evaluate_email_endpoints into run_scan.py`)

## Verify-Snippet Output

The plan's `<verify>` snippet runs cleanly:

```
$ python3 -c "<plan verify snippet>"
OK
```

Layering proven (port 25 + AES256-SHA → 2 findings); port 587 STARTTLS-downgrade negative case proven; profile gating proven for standard/deep/quick.

## Acceptance Criteria — All Met

| Criterion | Result |
|---|---|
| `compileall risk_engine.py profiles.py run_scan.py` exit 0 | PASS |
| `^def evaluate_email_endpoints` in risk_engine.py | 1 |
| `STARTTLS downgrade risk on SMTP` | 1 |
| `Weak cipher suite on email TLS endpoint` | 1 |
| `Non-PFS cipher suite on email TLS endpoint` | 1 |
| `enable_email` in profiles.py | 7 (≥2 required) |
| `scan_email_targets` in run_scan.py | 2 (import + call) |
| `evaluate_email_endpoints` in run_scan.py | 2 (import + call) |
| `cfg.connectors.enable_email` in run_scan.py | 1 |
| `email_endpoints` in run_scan.py | 6 (≥3 required) |
| `"email_scanning"` phase-timer label | 1 |
| `pytest tests/test_email_scanner.py` | 18 passed |
| `pytest tests/test_email_findings.py` | 9 passed |
| `pytest tests/test_email_run_scan_wiring.py` | 7 passed |
| Full-suite regressions | 6 pre-existing failures (packaging/version drift) — unchanged from Plan 03 baseline |

## Test Status

```
$ python3 -m pytest tests/test_email_scanner.py tests/test_email_findings.py tests/test_email_run_scan_wiring.py -q
..................................                                       [100%]
34 passed in 0.21s
```

Full-suite: 527 passed, 6 failed (pre-existing baseline), 5 skipped — **no new failures**.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Plan verify-snippet used `AppConfig()` no-arg constructor**

- **Found during:** Task 1 verification preparation
- **Issue:** Plan's verify snippet calls `AppConfig()` with no args, but `AppConfig.__init__` requires 6 positional dataclass fields, and `ScanCfg.__init__` requires 3. Same defect as Plan 02 deviation #2.
- **Fix:** Test fixture `_mk_cfg()` constructs a `SimpleNamespace(scan=ScanCfg(timeout_seconds=5, concurrency=200, ports_tls=[443]), connectors=ConnectorsCfg())`. Sufficient because `apply_profile` only mutates `cfg.scan` and `cfg.connectors`, both of which are real config dataclasses on the duck-typed cfg.
- **Files modified:** tests/test_email_findings.py
- **Verification:** All 9 Y1–Y7 tests GREEN; verify-snippet adapted to same construction.
- **Committed in:** `9799d8d`

**2. [Rule 2 — Critical] Findings merge placed inside existing `risk_engine` phase timer**

- **Found during:** Task 2 wiring decision
- **Issue:** Plan suggested adding the merge after `evaluate_endpoints()`. Two valid placements existed: (a) inside the existing `_phase_timer(run_stats, "risk_engine")` block, or (b) after the block. Placing outside would have produced a phase-timer gap and made the email findings escape the canonical risk-engine timing window — a subtle metric correctness bug.
- **Fix:** Merged email_findings inside the existing `risk_engine` phase-timer block. Single timer span covers both `evaluate_endpoints` and `evaluate_email_endpoints`; report metrics remain consistent.
- **Files modified:** run_scan.py (line 720-727)
- **Verification:** Wiring tests pass; phase-timer label invariant preserved.
- **Committed in:** `23e9cdf`

---

**Total deviations:** 2 auto-fixed. No architectural decisions; no checkpoints reached.

## Issues Encountered

None beyond the deviations above.

## TDD Gate Compliance

- **Task 1 RED:** `ea350a4` — test-only, 1 failure on first import (no `evaluate_email_endpoints` symbol).
- **Task 1 GREEN:** `9799d8d` — implementation; 9/9 Y-tests GREEN.
- **Task 2 RED:** `82db887` — structural wiring tests; 6/7 failed.
- **Task 2 GREEN:** `23e9cdf` — wiring; 7/7 wiring tests GREEN.
- **REFACTOR:** None — both implementations passed acceptance criteria on first GREEN.

## Threat Surface

No new threat surface introduced beyond the plan's `<threat_model>` (T-32-11/T-32-12/T-32-13). The `email_findings` titles use literal strings; `host`/`port` flow through the same `_dedupe_findings()` and `writers.py` escape path as existing findings.

## Known Stubs

None. `evaluate_email_endpoints` is fully wired into `run_scan.py`; finding emission is exercised end-to-end by the layered test (Y6) and the verify-snippet.

## Next Phase Readiness

- Phase 32 Plan 05 (chaos-lab validation) can now drive the chaos-lab Postfix/Dovecot endpoints through the full scanner → risk-engine → report pipeline.
- Phase 34 (motion intelligence) can read `email_endpoints` from the master list and `email_findings` titles from the report findings.
- Phase 35 (CBOM integration) can iterate `email_endpoints` for Pass 1 algorithm registration; finding titles are stable.

## Self-Check: PASSED

- quirk/engine/risk_engine.py contains `def evaluate_email_endpoints`: FOUND
- quirk/engine/profiles.py contains `enable_email = True` in 2 branches: FOUND (deep + standard)
- run_scan.py imports + uses scan_email_targets and evaluate_email_endpoints: FOUND (lines 25, 31, 697, 725)
- run_scan.py has `"email_scanning"` phase timer: FOUND (line 692)
- run_scan.py aggregates `+ email_endpoints` in master endpoints tuple: FOUND (line 714)
- Commits ea350a4, 9799d8d, 82db887, 23e9cdf exist in git log: FOUND
- compileall on all 3 modified Python files: PASS
- `pytest tests/test_email_*` (3 files): 34 passed
- Full suite: no new failures vs Plan 03 baseline (6 pre-existing failures unchanged)

---
*Phase: 32-email-scanner*
*Completed: 2026-04-27*
