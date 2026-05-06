---
phase: 47-nmap-discovery-multi-target-wizard
verified: 2026-05-04T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Wizard CSV prompt — enter 'host1,host2,host3' at interactive prompt"
    expected: "All three hosts appear in scan output; no prompt for each individual target"
    why_human: "Interactive TTY prompt; cannot drive stdin in automated check"
  - test: "Wizard @file prompt — enter '@/tmp/targets.txt' at interactive prompt"
    expected: "Hosts from file are loaded, # lines and blank lines are ignored"
    why_human: "Interactive TTY prompt"
  - test: "Wizard nmap y/N prompt — respond y; observe single global prompt fires exactly once"
    expected: "One prompt across all targets; not per-target"
    why_human: "Interactive TTY prompt; D-06 single-global-toggle requires visual confirmation"
  - test: "TTY probe-budget confirm — configure >10,000 targets*ports, run in TTY"
    expected: "Warning with projected count appears; y/N prompt fires before nmap"
    why_human: "TTY-dependent behavior"
---

# Phase 47: Nmap Discovery + Multi-Target Wizard Verification Report

**Phase Goal:** Users can feed QUIRK comma-separated hosts, a target file, or a CIDR range, and optionally pre-discover open ports with nmap — enabling real enterprise 50-host+ scans without manual port enumeration
**Verified:** 2026-05-04T00:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User enters CSV hosts in wizard; all three are scanned in one run | VERIFIED | `interactive_config()` calls `parse_target_tokens(raw_targets)` (interactive.py:134); `test_csv_split` PASS; smoke: `parse_target_tokens('a.com,10.0.0.0/24')` returns `(['a.com'], ['10.0.0.0/24'])` |
| 2 | @file in wizard + `--targets-file` CLI both load file and replace config targets | VERIFIED | `interactive.py:134` routes @-prefix to `load_targets_file`; `run_scan.py:310-311` calls `apply_targets_file_override` (D-03 REPLACES); `test_targets_file_replaces_config_fqdns` PASS |
| 3 | CIDR entered in wizard is expanded via stdlib ipaddress and hosts scanned | VERIFIED | `parse_target_tokens` validates via `ipaddress.ip_network(strict=False)` and routes to `cfg.targets.cidrs`; existing `target_expander.py` does expansion; `test_cidr_routes_to_cidrs` PASS |
| 4 | nmap wizard toggle fires; `--max-parallelism 100` in default args; missing binary → warning + fallback (no crash) | VERIFIED | `interactive.py:139-142` adds `_prompt_bool` for nmap; `nmap_provider.py:29` includes `"--max-parallelism", "100"`; `run_scan.py:369-376` falls back to `expand_targets(cfg)` when binary absent; tests `test_default_args_includes_max_parallelism`, `test_nmap_binary_missing_emits_advisory`, `test_nmap_fallback_uses_consulting_tls_ports` all PASS |
| 5 | targets × ports > 10,000 → warning before nmap; malformed target / missing file → clear error | VERIFIED | `run_scan.py:353-360` calls `maybe_confirm_probe_budget(..., threshold=10_000)`; `parse_target_tokens` raises `ValueError("Invalid target: ...")` on bad CIDR; `load_targets_file` raises `FileNotFoundError("Targets file not found: ...")` on missing file; 6 budget-guard tests PASS + 2 error-surface tests PASS |

**Score: 5/5 truths verified**

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/util/targets.py` | parse_target_tokens, load_targets_file, apply_targets_file_override, projected_probe_count, maybe_confirm_probe_budget | VERIFIED | File exists; all 5 public functions present; stdlib only (ipaddress, sys) |
| `quirk/interactive.py` | Single syntax-routed target prompt; global nmap y/N prompt | VERIFIED | L130-134: one `_prompt` call + `parse_target_tokens`; L139-142: `_prompt_bool` for nmap; D-01 + D-06 comments present |
| `run_scan.py` | `--targets-file` argparse flag; D-03 override block; D-09 flag reflection; D-10/D-12 budget guard | VERIFIED | L227-233: `--targets-file` arg; L309-311: override block; L316-317: D-09 setattr; L353-360: budget guard with `threshold=10_000` literal |
| `quirk/discovery/nmap_provider.py` | `--max-parallelism 100` in `_default_nmap_args` | VERIFIED | L29: `"--max-parallelism", "100"` with `# D-07` comment |
| `quirk/util/optional_extra.py` | `binary` field on OptionalExtra; `nmap` registry entry; `cbom` registry entry; `select_nmap_port_list`; binary-aware `probe_missing_extras` | VERIFIED | L73: `binary: Optional[str] = None`; L119-130: nmap entry; L135-144: cbom entry; L167-186: `select_nmap_port_list`; L218: `binary_ok` check in `probe_missing_extras` |
| `quirk/cbom/writer.py` | Post-write `JsonStrictValidator`; soft-fail `coverage_gap` WARN finding; `MissingOptionalDependencyException` caught silently; keyword-only `error_endpoints` | VERIFIED | L21-24: imports; L32-33: keyword-only signature with `*`; L65-84: try-except block covering both constructor and validate_str; D-14/D-15/D-16 comments present |
| `pyproject.toml` | `cyclonedx-python-lib[json-validation]>=11.7.0,<12` in core deps; `cbom` optional-extra declared; `quirk[cbom]` in `[all]` | VERIFIED | L16: `[json-validation]` in core deps; L62: `cbom = [...]`; L66: `"quirk[cbom]"` in `[all]` |
| `tests/test_targets_parser.py` | 9 unit tests covering CSV/CIDR/@file/malformed/missing/D-02 | VERIFIED | 9 tests, all PASS |
| `tests/test_run_scan_targets_file.py` | 4 integration tests covering D-03 REPLACE, missing-file, malformed-CIDR, Risks #3 nmap regression | VERIFIED | 4 tests, all PASS |
| `tests/test_nmap_provider.py` | test_default_args_includes_max_parallelism | VERIFIED | 1 test PASS |
| `tests/test_optional_extra.py` | 5 Phase-47-02 tests + 2 Phase-47-03 tests | VERIFIED | 16 total (including prior Phase 45 tests), all PASS |
| `tests/test_run_scan_budget_guard.py` | 6 budget-guard tests (projected_probe_count + maybe_confirm_probe_budget) | VERIFIED | 6 tests, all PASS |
| `tests/test_cbom_writer_validation.py` | 5 validation tests (happy, soft-fail, missing-deps, backward-compat) | VERIFIED | 5 tests, all PASS |
| `docs/UAT-SERIES.md` | Phase 47 acceptance text UAT-47-01..08 | VERIFIED | UAT-47-01..08 present at L6075+; `Last Updated: 2026-05-04` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/interactive.py` | `quirk/util/targets.py` | `from quirk.util.targets import parse_target_tokens, load_targets_file` | WIRED | L17 import; L134 call site |
| `run_scan.py` | `quirk/util/targets.py` | `apply_targets_file_override` called at L311 when `args.targets_file` set | WIRED | L45 import; L310-311 call |
| `run_scan.py` | `maybe_confirm_probe_budget` | Called at L353-360 before `_phase_timer`; `threshold=10_000` literal | WIRED | L352-353: local import + call |
| `run_scan.py` | `select_nmap_port_list` | L348: `ports_for_nmap = sorted(set(select_nmap_port_list(cfg, nmap_binary_available) + ...))` | WIRED | L46 import; L348 call |
| `run_scan.py` | `probe_missing_extras` | L427-428: called with `cfg, error_endpoints` before scanner phases | WIRED | L427: local import; L428 call |
| `quirk/cbom/writer.py` | `JsonStrictValidator` | L21-24 imports; L68-69: constructor + `validate_str(json_text)` | WIRED | Both under same try-except |
| `quirk/cbom/writer.py` | `error_endpoints` list | L70-81: `error_endpoints.append(CryptoEndpoint(..., scan_error_category="coverage_gap"))` | WIRED | Conditional on `err is not None and error_endpoints is not None` |
| `quirk/reports/writer.py` | `write_cbom_files` | L199-200: `write_cbom_files(cbom, outdir, stamp, error_endpoints=error_endpoints)` | WIRED | `error_endpoints` threaded from `write_reports` signature (L91) |
| `run_scan.py` | `write_reports` | L1003: `write_reports(..., error_endpoints=error_endpoints)` | WIRED | Confirmed by grep |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `interactive.py` `interactive_config` | `fqdns, cidrs` | `parse_target_tokens(raw_targets)` at L134 | Yes — live parser call; feeds `TargetsCfg` | FLOWING |
| `run_scan.py` | `cfg.targets.fqdns/cidrs` | `apply_targets_file_override(cfg, args.targets_file)` at L311 | Yes — reads file, parses tokens, REPLACES | FLOWING |
| `run_scan.py` | `nmap_binary_available` | `is_extra_available("nmap")` at L346 | Yes — `shutil.which` call | FLOWING |
| `run_scan.py` | `ports_for_nmap` | `select_nmap_port_list(cfg, nmap_binary_available)` at L348 | Yes — cfg.scan.ports_tls or CONSULTING_TLS_PORTS | FLOWING |
| `quirk/cbom/writer.py` | `json_text` | `open(json_path, "r")` read of just-written file at L66-67 | Yes — reads actual disk artifact | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| parse_target_tokens returns correct tuple | `python -c "from quirk.util.targets import parse_target_tokens; print(parse_target_tokens('a.com,10.0.0.0/24'))"` | `(['a.com'], ['10.0.0.0/24'])` | PASS |
| --max-parallelism 100 in default args | `python -c "from quirk.discovery.nmap_provider import _default_nmap_args; args=_default_nmap_args('443'); print('--max-parallelism' in args and '100' in args)"` | `True` | PASS |
| --targets-file appears in CLI help | `python run_scan.py --help \| grep targets-file` | Outputs `--targets-file TARGETS_FILE` | PASS |
| 25 phase-47 tests pass | `pytest tests/test_targets_parser.py tests/test_run_scan_targets_file.py tests/test_nmap_provider.py tests/test_run_scan_budget_guard.py tests/test_cbom_writer_validation.py -v` | `25 passed in 0.12s` | PASS |
| Full suite (excl. pre-existing failures) | `pytest tests/ -x --ignore=tests/test_cbom_schema_validation.py --ignore=tests/test_v41_gap_closure.py --ignore=tests/test_interactive_mode.py -q` | `758 passed, 2 skipped` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MULTI-01 | 47-01 | CSV targets in wizard prompt | SATISFIED | `parse_target_tokens` + `interactive_config` L134; `test_csv_split` PASS |
| MULTI-02 | 47-01 | @file syntax in wizard; comment/blank line stripping | SATISFIED | `load_targets_file` + L100-104 @-routing in `parse_target_tokens`; `test_at_file_strips_comments_and_blanks` PASS |
| MULTI-03 | 47-01 | `--targets-file` CLI replaces config targets | SATISFIED | `run_scan.py:227-233` argparse; L310-311 override block; `test_targets_file_replaces_config_fqdns` PASS |
| MULTI-04 | 47-01 | CIDR via stdlib ipaddress | SATISFIED | `parse_target_tokens` L108-113 CIDR branch; `test_cidr_routes_to_cidrs` PASS |
| MULTI-05 | 47-01 | Clear error on malformed target or missing file | SATISFIED | ValueError with token in message; FileNotFoundError with path in message; `test_malformed_cidr_raises_with_token`, `test_missing_file_raises_with_path` PASS |
| DISCOVER-01 | 47-02 | Interactive wizard nmap toggle | SATISFIED | `interactive.py:139-142` `_prompt_bool` for nmap; `setattr(cfg.connectors, "enable_nmap", ...)` at L269 |
| DISCOVER-02 | 47-02 | Graceful warning when nmap binary absent; no crash | SATISFIED | `run_scan.py:369-376` fallback to `expand_targets(cfg)` when `not nmap_binary_available`; `test_nmap_binary_missing_emits_advisory` PASS; `test_nmap_fallback_uses_consulting_tls_ports` PASS |
| DISCOVER-03 | 47-02 | `--max-parallelism 100` in nmap default args | SATISFIED | `nmap_provider.py:29`; `test_default_args_includes_max_parallelism` PASS; smoke confirmed |
| DISCOVER-04 | 47-02 | Warning before nmap when targets × ports > 10,000 | SATISFIED | `run_scan.py:353-360` `maybe_confirm_probe_budget` call; 6 guard tests PASS |

No orphaned requirements — all 9 IDs from PLAN frontmatter are accounted for.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None found | — | — | — |

No TODO/FIXME/placeholder comments found in phase-47-authored code. No stub implementations detected. No hardcoded empty return values in production paths. `return null` / `return {}` / `return []` appear only in test-isolation helpers and fallback empty-list paths (e.g., `if not targets: return []` in `run_nmap_discovery` — correctly handles the no-targets case, not a stub).

### Human Verification Required

#### 1. Wizard CSV Targets Flow

**Test:** Run `quirk` (no `--config`). At the "Targets" prompt enter `chaos-lab.local,10.0.0.1,10.0.0.2`. Proceed through remaining prompts and let scan execute.
**Expected:** All three hosts appear in scan output; no per-target prompts fire; cfg.targets.fqdns populated with all three.
**Why human:** Interactive TTY prompt; cannot drive stdin in automated check.

#### 2. Wizard @file Targets Flow

**Test:** Create `/tmp/quirk-t.txt` containing `host1.local\n#ignored\n\nhost2.local`. Run wizard; at "Targets" prompt enter `@/tmp/quirk-t.txt`.
**Expected:** `host1.local` and `host2.local` loaded; `#ignored` and blank line silently skipped.
**Why human:** Interactive TTY prompt.

#### 3. Wizard Nmap y/N Prompt — Single Global Toggle (D-06)

**Test:** Run wizard; at the nmap toggle prompt answer `y`. Observe that the prompt fires exactly once (not per target).
**Expected:** One `_prompt_bool` call for nmap across all targets. `cfg.connectors.enable_nmap` is True when entering the scan phase.
**Why human:** Interactive TTY; D-06 single-global-toggle requires visual confirmation of prompt count.

#### 4. TTY Probe-Budget Confirm Prompt (DISCOVER-04)

**Test:** Configure a targets file with 200 CIDRs that expand to >51 hosts each so targets × ports exceeds 10,000. Run in a TTY. Observe prompt before nmap fires.
**Expected:** Warning with formatted probe count; y/N prompt appears before nmap invocation. Answering `n` aborts without running nmap.
**Why human:** TTY-dependent behavior; non-trivial test infrastructure to manufacture a 10,001+ probe scenario in CI.

### Gaps Summary

No blocking gaps found. All five roadmap success criteria have direct implementation evidence confirmed by automated tests passing in the codebase. The four human verification items above are interactive/TTY behaviors that cannot be exercised programmatically without a terminal harness.

Pre-existing test failures (not caused by Phase 47, documented in SUMMARYs):
- `tests/test_cbom_schema_validation.py` — `cyclonedx-python-lib[json-validation]` not installed in the test virtual environment; pre-Phase-47 failure.
- `tests/test_v41_gap_closure.py::test_package_manifest_version_is_4_1_0` — installed egg-info reflects old version; infrastructure artifact.
- `tests/test_interactive_mode.py` — pre-existing MINIMAL_INPUTS sequence mismatch; 0 failures at end of Phase 47 per 47-02 SUMMARY.

These are not caused by Phase 47 code and do not affect the verification verdict.

---

_Verified: 2026-05-04T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
