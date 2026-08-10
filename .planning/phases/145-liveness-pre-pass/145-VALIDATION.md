---
phase: 145
slug: liveness-pre-pass
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-10
updated: 2026-08-10
---

# Phase 145 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing repo standard) |
| **Config file** | `pyproject.toml` — `addopts = "-m 'not slow'"` (default run excludes `@slow`) |
| **Quick run command** | `pytest tests/test_nmap_provider.py tests/test_nmap_parser.py tests/test_liveness_prepass.py -x` |
| **Full suite command** | `pytest` (repo default; excludes `@slow` unless `-m slow` explicitly added) |
| **Estimated runtime** | ~30 seconds (quick), full suite per repo baseline |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_nmap_provider.py tests/test_nmap_parser.py tests/test_liveness_prepass.py -x`
- **After every plan wave:** Run `pytest` (full suite, `not slow` default)
- **Before `/gsd:verify-work`:** Full suite must be green, plus D-06's human-UAT non-root pass signed off separately (cannot be gated by automated suite per D-06)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 145-01-T1 | 01 | 1 | DISC-03 | T-145-02 | `parse_nmap_host_status()` returns a row for every reported host incl. `state="down"`, and parses only via the `make_safe_parser()` WR-06 XXE chokepoint | unit (inline XML fixtures via `tmp_path`) | `pytest tests/test_nmap_parser.py::test_parse_host_status_up_and_down -x` | ❌ W0 (new file) | ⬜ pending |
| 145-01-T1 | 01 | 1 | DISC-03 | T-145-02 | XXE payload does not resolve through the new parser (existing invariant unregressed) | unit / invariant | `pytest tests/test_xml_safe.py::test_nmap_parser_blocks_xxe_lxml -x` | ✅ exists | ⬜ pending |
| 145-01-T2 | 01 | 1 | DISC-03 | — | Liveness args use `-sn` + `-PS<ports>` (never `-sT`/`-Pn`/`--open`) and carry the sweep's retry/timeout/parallelism caps | unit | `pytest tests/test_nmap_provider.py::test_liveness_args_use_sn_and_ps -x` | ❌ W0 (extend existing file) | ⬜ pending |
| 145-01-T2 | 01 | 1 | DISC-03 | — | `-PS` port spec reuses the sweep's port list (D-03); wide scopes (`-p-`, `--top-ports 1000`) resolve to the full-range `-` superset | unit | `pytest tests/test_nmap_provider.py::test_liveness_port_spec_resolves_full_range_for_wide_scopes -x` | ❌ W0 | ⬜ pending |
| 145-01-T2 | 01 | 1 | DISC-03 | T-145-01 | Port-list string for `-PS<ports>` passes `_SAFE_NMAP_ARG_RE` allowlist validation before `subprocess.run`; unsafe spec raises `ValueError` | unit | `pytest tests/test_nmap_provider.py::test_liveness_port_spec_validated -x` | ❌ W0 | ⬜ pending |
| 145-02-T1 | 02 | 2 | DISC-03 (D-02) | — | `_is_privileged()` returns True/False on POSIX and `None` when `os.geteuid` is absent (Windows guard) | unit (monkeypatch `os.geteuid`) | `pytest tests/test_liveness_prepass.py::test_is_privileged_none_when_geteuid_missing -x` | ❌ W0 (new file) | ⬜ pending |
| 145-02-T1 | 02 | 2 | DISC-03 (D-01) | T-145-05 | Privilege fallback is disclosed as a logger message **and** a persisted `privilege_fallback` CryptoEndpoint advisory row (not console-only) | unit | `pytest tests/test_liveness_prepass.py::test_fallback_advisory_row_shape -x` | ❌ W0 | ⬜ pending |
| 145-02-T2 | 02 | 2 | DISC-03 | — | Pre-pass filters batch hosts before the `run_nmap_discovery()` sweep call | unit (fake callable) | `pytest tests/test_liveness_prepass.py::test_liveness_prepass_filters_batch_before_sweep -x` | ❌ W0 | ⬜ pending |
| 145-02-T2 | 02 | 2 | DISC-03 (D-04/D-05) | — | Liveness-skipped hosts produce per-host `CryptoEndpoint(scan_error_category="liveness_skip")` rows with real host identity, not silently dropped | unit | `pytest tests/test_liveness_prepass.py::test_liveness_skip_appends_liveness_skip_category -x` | ❌ W0 | ⬜ pending |
| 145-02-T2 | 02 | 2 | DISC-03 | — | A fully non-responsive batch spawns zero sweep subprocesses (Pitfall 4) | unit | `pytest tests/test_liveness_prepass.py::test_all_dead_batch_skips_sweep_call -x` | ❌ W0 | ⬜ pending |
| 145-02-T2 | 02 | 2 | DISC-03 | — | A host absent from the pre-pass XML is swept anyway (fail-open, RESEARCH.md A1); a pre-pass `RuntimeError` sweeps the whole batch unfiltered | unit | `pytest tests/test_liveness_prepass.py::test_host_absent_from_liveness_results_is_swept tests/test_liveness_prepass.py::test_liveness_failure_falls_back_to_full_batch_sweep -x` | ❌ W0 | ⬜ pending |
| 145-02-T2 | 02 | 2 | DISC-03 | — | Liveness rows do not flip the Phase 144 discovery `ScanCheckpoint` to `partial` | unit | `pytest tests/test_liveness_prepass.py::test_liveness_rows_excluded_from_discovery_partial_failures -x` | ❌ W0 | ⬜ pending |
| 145-03-T1 | 03 | 3 | DISC-03 | T-145-07 | Degraded mode + both new `scan_error_category` values are documented and vault-synced | doc assertion | `grep -c "## 10. Discovery Liveness Pre-Pass" docs/operators-guide.md && grep -c "liveness_skip" docs/report-interpretation.md` | ✅ exists | ⬜ pending |
| 145-03-T2 | 03 | 3 | DISC-03 | — | UAT Series 145 present and vault-synced | doc assertion | `grep -c "## Series 145: Liveness Pre-Pass" docs/UAT-SERIES.md` | ✅ exists | ⬜ pending |
| 145-03-T3 | 03 | 3 | DISC-03 (D-06) | T-145-05 | Real non-root nmap invocation triggers fallback detection end-to-end | manual-only | N/A — human-UAT walkthrough (UAT-145-03) | manual gate, not automatable per D-06 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_nmap_parser.py` — does not exist today; created by Plan 01 Task 1 to cover `parse_nmap_host_status()`. Confirmed during planning: no existing file exercises `parse_nmap_xml()` directly except `tests/test_nmap_hardening.py`'s XXE invariant, so a new dedicated file is correct.
- [ ] `tests/test_liveness_prepass.py` — new file, created by Plan 02 Task 1, covering the privilege helpers and (Task 2) the batch-loop pre-pass shape. Kept separate from `tests/test_nmap_provider.py` so Plan 01 and Plan 02 own disjoint test files.
- [ ] Inline XML strings for up/down host test cases written to `tmp_path` — no live nmap binary required in CI.
- [ ] `os.geteuid` monkeypatch pattern for the privilege-check unit tests (`unittest.mock.patch` / `monkeypatch.delattr`), standard and low-risk.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Non-root SYN→connect silent fallback detection | DISC-03 (D-06) | nmap's XML output is byte-identical whether privileged or not (verified live against nmap 7.991) — no automatable signal exists to distinguish the fallback from nmap's own output; only a real non-root process run against a real host proves the `os.geteuid()` pre-check actually fires the advisory in practice | Run QUIRK as a non-root user against a chaos-lab `common` target (no new lab profile required); confirm the D-01 advisory (logger message + persisted `privilege_fallback` CryptoEndpoint row) plus per-host `liveness_skip` rows for dead addresses; re-run under `sudo` and confirm the advisory row is absent. Gated as documented human-UAT checkpoint UAT-145-03 per D-06 (mirrors the UAT-118-01 pattern). Plan 03 Task 3. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner-approved 2026-08-10 (task IDs bound to 145-01/02/03 PLAN.md tasks)
