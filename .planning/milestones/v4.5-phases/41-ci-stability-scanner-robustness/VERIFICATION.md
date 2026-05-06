---
phase: 41-ci-stability-scanner-robustness
verified: 2026-04-29T00:00:00Z
status: gaps_found
score: 6/7 must-haves verified
overrides_applied: 0
gaps:
  - truth: "pytest runs to completion with zero failing tests (CI-01 / Success Criterion #1)"
    status: failed
    reason: "`pytest -m 'not slow'` reports 1 FAILED — `tests/test_cli_correctness.py::test_no_quirk_scan_references` fails because Plan 07 added UAT-41-01 entries to docs/UAT-SERIES.md using the legacy `quirk scan ...` invocation form, which an existing CLI-hygiene test forbids. The phase's own closing plan introduced this regression."
    artifacts:
      - path: docs/UAT-SERIES.md
        issue: "Lines 5147, 5155, 5168 contain literal `quirk scan` references; should be `quirk --config <yaml>` per CLI conventions"
    missing:
      - "Rewrite `quirk scan` references in UAT-41-01 (and any other Phase 41 UAT entries) to use the `quirk --config ...` CLI invocation form"
      - "Re-run `pytest -m 'not slow' tests/ -q` and confirm 681 passed / 0 failed"
human_verification:
  - test: "Run a scan with `[motion]` extra not installed against a target with broker enabled; observe canonical stderr advisory line and exit 0 (UAT-41-01)"
    expected: "Single stderr line `[advisory] scanner=broker_scanner extra=motion not installed -- run `pip install quirk[motion]` to enable`; exit code 0; CryptoEndpoint row with scan_error_category='missing_extra' present"
    why_human: "Requires uninstalling kafka-python/pika/redis in a clean venv and running the live CLI; not feasible in unit-test budget"
  - test: "Scan a deliberately-slow TLS target and verify overall scan completes within documented upper bound (UAT-41-02 / ROBUST-02)"
    expected: "Wall clock ≤ 36 s (single host) per docs/configuration.md formula; no per-scanner stall"
    why_human: "Needs a real slow/unreachable host harness (toxiproxy or similar)"
  - test: "lab.sh down + reset profile-sweep verification (UAT-41-03)"
    expected: "After `./lab.sh up <profile>` then `./lab.sh down`, `docker ps` shows zero project containers regardless of which profile was active"
    why_human: "Requires Docker daemon and live compose project state"
---

# Phase 41: CI Stability & Scanner Robustness Verification Report

**Phase Goal:** "The CI test suite runs green with zero skipped-for-code-reasons tests and completes deterministically in under 60 seconds; all scanners degrade gracefully under missing extras, slow targets, and unexpected exceptions with a consistent, documented timeout/retry policy"

**Verified:** 2026-04-29
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `pytest` runs to completion with zero `skip`/`xfail` markers on tests deferred for code reasons; SAML scan-window test from Phase 38 is GREEN | ✗ FAILED | `pytest -m 'not slow' tests/ -q` produces **1 failed, 680 passed, 10 deselected** in 4.40 s. Failing test: `test_cli_correctness.py::test_no_quirk_scan_references` — caused by Phase 41 Plan 07's own additions to `docs/UAT-SERIES.md` using forbidden `quirk scan` invocation form (lines 5147, 5155, 5168). Suite is NOT green. |
| 2 | Running a scan with `[motion]` not installed produces a clear advisory, completes normally, no ImportError crash | ✓ VERIFIED | `run_scan.py:122` defines `_emit_missing_extra_advisory`. `run_scan.py:782` and `:827` invoke it for email_scanner / broker_scanner missing-motion paths; produces canonical advisory line and `CryptoEndpoint(scan_error_category='missing_extra')`. Test `test_scan_robustness.py` ROBUST-01 stub flipped to real assertion (per Plan 04 SUMMARY) and passes (in 680 passed count). |
| 3 | A scan against a target that exceeds the per-scanner timeout budget does not stall indefinitely; finishes within documented upper bound | ✓ VERIFIED (auto) | TLS/SSH scanners read `cfg.scan.timeouts.tls_seconds` / `.ssh_seconds` directly; `_wrapped_phase` enforces phase boundary with BaseException protection. Upper-bound formula documented in `docs/configuration.md:117`. Live wall-clock confirmation deferred to UAT-41-02 (human). |
| 4 | An unexpected scanner exception is captured in `scan_errors[]` with scanner name, target, reason; scan continues | ✓ VERIFIED | `_wrapped_phase` (run_scan.py:91–120) re-raises KeyboardInterrupt/SystemExit, captures every other BaseException into `CryptoEndpoint(scan_error_category='exception', scan_error=<reason>)`. Wired into TLS (line 488), SSH (line 512), broker (line 865) phases. Email phase uses inline try/except inside `with _phase_timer('email_scanning')` (Plan 04 noted decision; preserves AST shape required by guard test). |
| 5 | Timeout, retry count, backoff defaults defined in a single location and documented; divergences reconciled | ✓ VERIFIED | `quirk/config.py:18 class TimeoutsCfg`, `:43 class RetryCfg`, `:75 ScanCfg.timeouts` / `:76 ScanCfg.retry`. `docs/configuration.md §Timeout & Retry Policy (v4.5+)` (line 67) + `docs/timeout-retry-audit.md` (4435 bytes, ROBUST-04 audit table). Deprecation aliases on legacy flat fields emit DeprecationWarning on read (observed in pytest output). |
| 6 | Default `pytest` run (excluding slow) finishes in under 60 s on dev machine | ✓ VERIFIED | Measured: 4.40 s pytest wall, ~5.14 s total `time` real — >10x headroom under 60 s budget. `pyproject.toml:80 addopts = "-m 'not slow'"` enforces the exclusion by default. |
| 7 | (Implicit) `_wrapped_phase` D-14 wrapper covers TLS/SSH/broker; missing-extra advisories for [motion] gated scanners | ✓ VERIFIED | Confirmed at run_scan.py:91, 122, 488, 512, 782, 827, 865 (grep evidence). |

**Score:** 6/7 truths verified — Success Criterion #1 (CI-01 GREEN) FAILED.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml [tool.pytest.ini_options]` | slow marker + addopts excluding slow + testpaths | ✓ VERIFIED | Lines 75–81; markers slow + live_infra; addopts `-m 'not slow'`. |
| `tests/skip_registry.py` | 9 ALLOWED_SKIPS entries | ✓ VERIFIED | File present (1491 bytes). |
| `tests/test_skip_registry.py` | AST-walk meta-gate | ✓ VERIFIED | File present (4753 bytes); test passes in suite (in 680 passed). |
| `tests/test_scan_robustness.py` | ROBUST-01/02/03 + KeyboardInterrupt | ✓ VERIFIED | File present (5633 bytes). |
| `tests/test_timeouts_config.py` | 4 deprecation/alias tests | ✓ VERIFIED | File present (3828 bytes). |
| `quirk/config.py TimeoutsCfg + RetryCfg` | dataclasses with sub-tables | ✓ VERIFIED | Lines 18, 43, 75, 76, 87, 88. |
| `run_scan.py _wrapped_phase + _emit_missing_extra_advisory` | helpers + wired phases | ✓ VERIFIED | Lines 91, 122; wired at 488, 512, 782, 827, 865. |
| `quirk/intelligence/trends.py D-15 exclusion` | filter `scan_error_category=='missing_extra'` | ✓ VERIFIED | Lines 256–267 implement category-aware exclusion. |
| `quirk/models.py scan_error_category column` | new column on CryptoEndpoint | ✓ VERIFIED | (per 41-01 SUMMARY; DB migration helper `_ensure_phase41_columns` added to db.py). |
| `docs/configuration.md` | §Timeout & Retry Policy + upper-bound formula | ✓ VERIFIED | Lines 67, 117. |
| `docs/timeout-retry-audit.md` | ROBUST-04 audit table | ✓ VERIFIED | File present (4435 bytes). |
| `quantum-chaos-enterprise-lab/lab.sh` | profile-sweep on down + reset | ✓ VERIFIED | Lines 99 (down) and 104 (reset) use `--profile "*" --remove-orphans`. |
| `docs/UAT-SERIES.md UAT-41-01..04` | 4 UAT entries | ⚠️ ORPHANED | Entries present but content uses forbidden `quirk scan` syntax — breaks `test_no_quirk_scan_references`. |
| Vault `Phase-41-CI-Stability-Scanner-Robustness.md` | obsidian phase note | ✓ VERIFIED | Present at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-41-CI-Stability-Scanner-Robustness.md`. |
| `.planning/ROADMAP.md Phase 41 [x]` | marked complete | ✓ VERIFIED | Line 753: `- [x] **Phase 41: ...** ... (completed 2026-04-29)`. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Default pytest (non-slow) green | `python -m pytest -m 'not slow' tests/ -q --tb=line` | 1 failed, 680 passed, 10 deselected, 4.40 s | ✗ FAIL |
| Default pytest under 60 s budget | `time python -m pytest -m 'not slow' tests/ -q` | 5.14 s real | ✓ PASS |
| TimeoutsCfg importable | `python -c "from quirk.config import TimeoutsCfg, RetryCfg, ScanCfg; ScanCfg()"` | (implicit — referenced in passing tests) | ✓ PASS |
| `_wrapped_phase` exists in run_scan | grep | line 91 | ✓ PASS |
| Missing-extra advisory canonical form | grep `pip install quirk` in run_scan.py | line 132 (helper output) | ✓ PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| CI-01 | Zero skip/xfail on code-reason-deferred tests; suite GREEN | ✗ BLOCKED | One unrelated CLI-hygiene test fails on Phase 41's own UAT-SERIES additions; technically code-reason failure introduced by this phase. |
| CI-02 | Deterministic suite, no order/global-state coupling | ✓ SATISFIED | 680 tests pass; no flake observed. |
| CI-03 | Slow tests marked with `pytest.mark.slow`; default <60 s | ✓ SATISFIED | pyproject.toml addopts + 5.14 s real wall. |
| ROBUST-01 | Missing-extra advisory + scan continues | ✓ SATISFIED | `_emit_missing_extra_advisory` + `scan_error_category='missing_extra'` rows; ROBUST-01 unit test green (per Plan 04). |
| ROBUST-02 | Per-scanner timeout enforced; documented upper bound | ✓ SATISFIED (auto) | Scanners read `cfg.scan.timeouts.*_seconds`; upper-bound formula documented. Live verification in UAT-41-02 (human). |
| ROBUST-03 | Unexpected exceptions captured to scan_errors[] with name/target/reason; scan continues | ✓ SATISFIED | `_wrapped_phase` BaseException capture; ROBUST-03 + KeyboardInterrupt-ordering tests green. |
| ROBUST-04 | Timeout/retry single source of truth; audit reconciles divergences | ✓ SATISFIED | `quirk/config.py` (canonical); `docs/timeout-retry-audit.md` (audit). |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| docs/UAT-SERIES.md | 5147, 5155, 5168 | Forbidden `quirk scan` CLI invocation | 🛑 Blocker | Causes `tests/test_cli_correctness.py::test_no_quirk_scan_references` to FAIL — directly violates Phase 41's own Success Criterion #1 (suite GREEN). |

### Human Verification Required

1. **UAT-41-01 missing-extra advisory live test** — uninstall `kafka-python`/`pika`/`redis` in a clean venv, run a scan with `--enable-broker`, observe stderr advisory + exit 0 + scan_error_category='missing_extra' row.
   - Expected: canonical advisory line per format established in run_scan.py; CryptoEndpoint row visible in CBOM/scan_errors output.
   - Why human: requires venv manipulation + live CLI run.

2. **UAT-41-02 timeout upper-bound live test** — scan a deliberately-slow TLS target; verify wall clock within docs/configuration.md formula.
   - Why human: requires toxiproxy or equivalent latency injector.

3. **UAT-41-03 lab.sh profile-sweep** — `./lab.sh up <profile>; ./lab.sh down; docker ps` shows zero project containers.
   - Why human: requires Docker daemon + live compose project.

### Gaps Summary

Phase 41 substantively delivers all 7 declared requirements (CI-01, CI-02, CI-03, ROBUST-01..04) at the code level — TimeoutsCfg/RetryCfg are landed, `_wrapped_phase` BaseException protection is wired into TLS/SSH/broker phases, missing-extra advisory emits the canonical line and category-tagged row, trends.py excludes `missing_extra` from regression counts, lab.sh profile-sweep is fixed on both `down` and `reset`, and the configuration/audit documentation is complete.

**However**, the closing plan (41-07) introduced a regression: the new UAT-41-01 entries in `docs/UAT-SERIES.md` use the legacy `quirk scan ...` invocation form, which an existing CLI-correctness test (`test_no_quirk_scan_references`) explicitly forbids. As a direct consequence, Success Criterion #1 — "pytest runs to completion ... GREEN" — is NOT met. The suite reports `1 failed, 680 passed`.

This is a single-file, mechanical fix: rewrite the three `quirk scan` references in docs/UAT-SERIES.md (lines 5147, 5155, 5168) to use `quirk --config <yaml>` per project CLI conventions, then re-run pytest to confirm 681/681 passing. After that fix, Phase 41 should re-verify cleanly.

The wall-clock budget (CI-03) is comfortably met at 4.4 s pytest / 5.14 s real — well under the 60 s D-16 ceiling.

**Verdict: PARTIAL** — code deliverables fully satisfy phase intent; one self-introduced documentation regression breaks the GREEN-suite contract.

---

*Verified: 2026-04-29*
*Verifier: Claude (gsd-verifier)*
