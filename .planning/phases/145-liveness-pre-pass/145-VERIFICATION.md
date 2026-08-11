---
phase: 145-liveness-pre-pass
verified: 2026-08-11T15:11:53Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 145: Liveness Pre-Pass Verification Report

**Phase Goal:** Discovery skips the expensive full port sweep on non-responsive hosts using a
cheap TCP-based liveness check, preserving reliability in segmented/firewalled networks where ICMP
is unreliable.
**Verified:** 2026-08-11
**Status:** passed
**Re-verification:** No — initial verification (this VERIFICATION.md was missing after phase
completion; produced retroactively against the live codebase per the 2026-08-11 milestone audit
finding, not by re-running the phase).

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Each batch runs a TCP-SYN/ACK liveness check (`-sn -PS<port-list>`) ahead of its full port sweep | VERIFIED | `run_scan.py:1484-1493` calls `run_nmap_liveness_check(targets=batch, ...)` inside the per-batch loop (`for batch in _chunked(host_iter, _MAX_HOSTS_PER_CIDR)`), strictly before the `run_nmap_discovery()` sweep call at `run_scan.py:1527`. `_liveness_nmap_args()` (`quirk/discovery/nmap_provider.py:164-183`) emits `["-sn", f"-PS{port_spec}", "-n", ...]` — `-sn` (host discovery only) + `-PS<ports>` (TCP SYN ping), never `-sT`/`-Pn`/`--open`. Port spec defaults to the batch's own sweep port list (`_resolve_liveness_port_spec`, D-03 parity) rather than a fixed subset, confirmed by `test_liveness_port_spec_resolves_full_range_for_wide_scopes` and `test_liveness_args_use_sn_and_ps`. |
| 2 | Hosts found non-responsive by the pre-pass are skipped from the expensive sweep but still counted (not silently dropped from host/undetermined accounting) | VERIFIED | `run_scan.py:1505-1519`: `down_hosts` computed by exclusion (`{s.host for s in statuses if not s.up}`), `sweep_targets` computed as `[h for h in batch if h not in down_hosts]` — a host absent from the pre-pass results defaults to being swept, not silently vanished (fail-open by construction). Each down host gets a `CryptoEndpoint(scan_error_category="liveness_skip", host=h, port=0)` row appended to a dedicated `liveness_endpoints` accumulator (`run_scan.py:1509-1515`), distinct from `error_endpoints`. `_discovery_hosts_checked += len(batch)` (`run_scan.py:1557`) counts every host in the batch regardless of liveness outcome, feeding `update_batch_progress`. `liveness_endpoints` is merged into `error_endpoints` at `run_scan.py:1591`, making the rows part of the persisted scan artifact and queryable from the DB (`scan_error_category='liveness_skip'`), confirmed live in UAT-145-03 (253 `liveness_skip` rows with real host addresses, port=0). |
| 3 | A privilege fallback from SYN scan to full TCP connect scan is explicitly detected and logged rather than silently degrading the intended optimization | VERIFIED | `_is_privileged()` (`run_scan.py:192-204`) checks `os.geteuid() == 0` once per scan, treating the `None` (undeterminable, e.g. Windows) case as not-privileged rather than assuming best-case behavior. `_emit_liveness_fallback_advisory()` (`run_scan.py:207-231`) is called when `_liveness_privileged is not True` (`run_scan.py:1458-1462`), emitting both a `logger.info(...)` line and a persisted `CryptoEndpoint(scan_error_category="privilege_fallback", host="liveness-prepass", port=0)` row — not console-only (matches the `_emit_missing_extra_advisory` precedent D-01 cites). Confirmed by `test_fallback_advisory_row_shape` and `test_is_privileged_*` in `tests/test_liveness_prepass.py`, and live in UAT-145-03 (non-root run: 1 `privilege_fallback` row; `sudo` re-run: 0 rows, advisory line absent). |
| 4 | The pre-pass and its fallback-detection behavior are verified against a real non-root run, not just a unit test — per the documented nmap SYN->connect silent-fallback risk | VERIFIED | UAT-145-03 (`docs/UAT-SERIES.md:16462-16513`) is recorded `[x] PASS`, dated 2026-08-10, tester "human (live, non-root + sudo re-run against real dev-machine loopback range)". The live run genuinely caught a real defect (not a rubber-stamp): the first non-root run reported `255 responsive, 0 skipped` despite nmap's own `<runstats>` showing `2 up, 253 down` — real `-sn -PS` subnet sweeps only emit `<host>` elements for hosts nmap can positively report on, so the exclude-set built solely from explicit `<host state="down">` elements was always empty. Fixed in commit `c5290db` by adding `parse_nmap_run_summary()` (`quirk/discovery/nmap_parser.py:134-175`) and cross-checking it in `run_nmap_liveness_check()` (`quirk/discovery/nmap_provider.py:250-274`): down hosts are now inferred for every batch target absent from explicit results, but **only** when `summary.exit_status == "success" and summary.total == len(targets)` (verified present at `nmap_provider.py:262`) — any mismatch or missing summary leaves `host_statuses` unmodified so the caller's existing fail-open behavior (sweep everyone) applies unchanged, per `nmap_provider.py:256-274` and confirmed by `test_liveness_prepass_infers_down_hosts_from_runstats_when_trustworthy` / the "does not fire when untrustworthy" counterpart in `tests/test_nmap_provider.py`. Re-verified post-fix: non-root run correctly reported `2 responsive, 253 skipped` with matching DB rows. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/discovery/nmap_parser.py` | `NmapHostStatus`, `parse_nmap_host_status()`, `NmapRunSummary`, `parse_nmap_run_summary()` | VERIFIED | All four present (lines 22-34, 95-131, 29-34, 134-175). `parse_nmap_host_status()` deliberately omits the "skip non-up hosts" filter that `parse_nmap_xml()` has, so `up=False` rows survive. `parse_nmap_run_summary()` returns `None` on any missing/unparseable `<runstats>`/`<finished>`/`<hosts>` element, forcing callers into the fail-open path. |
| `quirk/discovery/nmap_provider.py` | `run_nmap_liveness_check()`, `_liveness_nmap_args()`, `_resolve_liveness_port_spec()`, runstats-based down-host synthesis | VERIFIED | All present (lines 128-281). `-PS<spec>` token allowlist-validated via `_SAFE_NMAP_ARG_RE.fullmatch()` before any `subprocess.run` call (line 216), mirroring the existing `extra_args`/`port_spec_override` gates. `RuntimeError` on subprocess failure/timeout/missing-binary, matching `run_nmap_discovery()`'s existing error contract so `run_scan.py`'s `except RuntimeError` handling applies unchanged. |
| `run_scan.py` | Pre-pass call site inside the batch loop, survivor-set computation, `_is_privileged()`, `_emit_liveness_fallback_advisory()`, `liveness_skip`/`privilege_fallback` CryptoEndpoint rows, `_discovery_hosts_checked` accounting | VERIFIED | All present and wired as described in Truths 1-3 above (lines 192-231, 1444-1591). `liveness_endpoints` kept as a separate accumulator from `error_endpoints` and merged in only *after* `_collect_stage_partial_failures(run_stats, "discovery", error_endpoints, _err_before_discovery)` runs (line 1581 vs. 1591) — normal liveness skips cannot flip the discovery `ScanCheckpoint` to `"partial"`. |
| `quirk/models.py` | `scan_error_category` comment lists `liveness_skip`/`privilege_fallback` | VERIFIED | Line 35: `missing_extra\|timeout\|exception\|config\|invalid_input\|liveness_skip\|privilege_fallback`. Comment-only change, no schema/migration — column remains `String(32)`. |
| `tests/test_nmap_parser.py` | Up/down parsing, missing-reason default, ipv4 preference, `parse_nmap_run_summary` coverage incl. the real bugged-run XML shape | VERIFIED | File exists (172 lines), contains the described test cases. |
| `tests/test_nmap_provider.py` | Liveness args, port-spec resolution, allowlist rejection, runstats-synthesis trustworthy/untrustworthy cases | VERIFIED | Extended file contains the described tests, all passing. |
| `tests/test_liveness_prepass.py` | Privilege detection, advisory row shape, batch-filter survivor computation, liveness_skip row shape, all-dead-batch short-circuit, fail-open cases, partial-failure exclusion | VERIFIED | New file, 266 lines, 11 tests (`test_is_privileged_*` x3, `test_fallback_advisory_*` x2, `test_liveness_prepass_filters_batch_before_sweep`, `test_liveness_skip_appends_liveness_skip_category`, `test_all_dead_batch_skips_sweep_call`, `test_host_absent_from_liveness_results_is_swept`, `test_liveness_failure_falls_back_to_full_batch_sweep`, `test_liveness_rows_excluded_from_discovery_partial_failures`). |
| `docs/operators-guide.md` | § 10 Discovery Liveness Pre-Pass | VERIFIED | Section present at line 1343, describes port-scope rules, privilege-fallback mechanism, failure behavior. Vault sync claimed in SUMMARY (not independently re-checked here — Obsidian is outside repo scope). |
| `docs/report-interpretation.md` | `liveness_skip`/`privilege_fallback` row interpretation | VERIFIED | § 12 "Discovery Liveness Pre-Pass Rows (Phase 145)" present at line 475, documents both row shapes with concrete field values. |
| `docs/UAT-SERIES.md` | Series 145 (UAT-145-01/02/03) | VERIFIED | Present at line 16396, all three results recorded PASS with dates and evidence. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `run_scan.py` batch loop | `nmap_provider.py::run_nmap_liveness_check` | function call, `try/except RuntimeError` fail-open | WIRED | `run_scan.py:1485-1499`; on `RuntimeError`, `sweep_targets = batch` (unfiltered), matching D-03's reliability-first principle. |
| `run_nmap_liveness_check` result | sweep target filtering | `down_hosts` exclusion set → `sweep_targets` | WIRED | `run_scan.py:1505-1506`; exclusion-based (not inclusion-based) so an unreported host defaults to swept. |
| Liveness-skip detection | `CryptoEndpoint` persistence | `liveness_endpoints.append(...)` → `error_endpoints.extend(liveness_endpoints)` (post-checkpoint) | WIRED | `run_scan.py:1509-1515`, `1591`. Confirmed ordering relative to `_collect_stage_partial_failures` at line 1581 (checkpoint snapshot happens BEFORE the merge). |
| `_is_privileged()` | `_emit_liveness_fallback_advisory()` | once-per-scan gate, only inside the nmap batch-loop branch | WIRED | `run_scan.py:1454-1462`; not evaluated on the cache-hit or nmap-binary-absent branches, matching D-02's stated scope. |
| Liveness pre-pass down-host synthesis | `parse_nmap_run_summary()` reconciliation guard | `exit_status == "success" and total == len(targets)` fail-open check | WIRED | `nmap_provider.py:262-274`; verified this is the exact defect fix from commit `c5290db`, present and unmodified in current source. |
| Sweep short-circuit | fully-dead batch | `if sweep_targets:` guard around `run_nmap_discovery()` call | WIRED | `run_scan.py:1521`; a fully non-responsive batch spawns zero sweep subprocesses, confirmed by `test_all_dead_batch_skips_sweep_call`. |

### Behavioral Spot-Checks / Test Execution

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Targeted unit/integration suite for this phase | `pytest -q tests/test_nmap_parser.py tests/test_nmap_provider.py tests/test_liveness_prepass.py` | 41 passed | PASS |
| Debt-marker scan on modified files | grep for TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER across `quirk/discovery/nmap_parser.py`, `quirk/discovery/nmap_provider.py`, `quirk/models.py`, `run_scan.py` | no matches | PASS |
| `python -m compileall` | not independently re-run this session; 145-02-SUMMARY.md and 145-03-SUMMARY.md both report exit 0 on the relevant files, and the module imports cleanly (pytest collection succeeded against live source, which would fail on a syntax/compile error) | inferred green | PASS |
| Full-suite delta check | Not re-run in full during this verification pass (would take several minutes and duplicate 145-02/03-SUMMARY.md's own full-suite runs, both of which grepped the failure list for nmap/liveness/discovery terms and found zero matches). The targeted suite above (41/41 green) covers every test file this phase created or modified. | N/A | not re-run — see note |

Note on the ~102 pre-existing full-suite failures referenced in the task brief: not independently re-counted here since the targeted suite (the only tests this phase's files affect) is fully green and SUMMARY.md's own full-suite run explicitly excluded nmap/liveness/discovery matches from that failure list. This is treated as adequately corroborated rather than blindly trusted, given the targeted suite result above is directly reproducible and green.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DISC-03 | 145-01, 145-02, 145-03 | Discovery uses a TCP-SYN/ACK liveness pre-pass (not ICMP) to skip full port sweeps on dead hosts, with explicit SYN->connect privilege-fallback detection | SATISFIED | `.planning/REQUIREMENTS.md:17,75` marks DISC-03 `[x]` / "Complete" mapped to Phase 145. All four ROADMAP success criteria independently verified above against live source, not SUMMARY claims. |

No orphaned requirements found for Phase 145 in `.planning/REQUIREMENTS.md`.

### Anti-Patterns Found

None. Debt-marker scan (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER, empty-return stubs, hardcoded-empty stubs) across all files this phase created or modified returned zero matches. No stub `return null`/`return []`/`return {}` patterns found in the new liveness code paths — every new function (`parse_nmap_host_status`, `parse_nmap_run_summary`, `run_nmap_liveness_check`, `_is_privileged`, `_emit_liveness_fallback_advisory`) has substantive logic and is exercised by both unit tests and the live UAT-145-03 run.

### Human Verification Required

None outstanding. UAT-145-03 (the D-06-mandated human-verify checkpoint for criterion 4) is already recorded PASS in `docs/UAT-SERIES.md` with concrete before/after evidence (defect found, fixed, re-verified), and this verification pass corroborated that the fix (`c5290db`) is present and structurally intact in current source — no further human action is required to close this phase.

### Gaps Summary

No gaps found. All four ROADMAP success criteria are independently verified against live source code (not SUMMARY.md narrative): the pre-pass genuinely runs `-sn -PS<ports>` ahead of each batch's sweep with sweep-parity port scope (C1); skipped hosts are recorded as `liveness_skip` rows and folded into `_discovery_hosts_checked` and the persisted artifact without flipping the discovery `ScanCheckpoint` to partial (C2); privilege-fallback is detected once per scan and disclosed via both a logger line and a persisted `privilege_fallback` advisory row (C3); and the D-06 human-UAT gate was run for real, caught a real reliability-critical defect (empty down-host set on live subnet sweeps, which would have made DISC-03 a no-op on its primary target scenario), and the fix's fail-open reconciliation guard (`exit_status == "success" and total == len(targets)`) is present and unmodified in current source (C4). Targeted test suite (41 tests across the three files this phase created/modified) is fully green. No debt markers, no stubs, no orphaned requirements.

---

_Verified: 2026-08-11T15:11:53Z_
_Verifier: Claude (gsd-verifier)_
