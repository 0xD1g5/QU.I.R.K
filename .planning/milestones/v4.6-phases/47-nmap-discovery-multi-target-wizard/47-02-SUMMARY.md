---
phase: 47-nmap-discovery-multi-target-wizard
plan: "02"
subsystem: nmap-discovery-ux
tags: [nmap, discovery, probe-budget, wizard, optional-extra, tdd]
dependency_graph:
  requires:
    - quirk.util.targets.parse_target_tokens (Plan 47-01)
    - quirk.util.targets.apply_targets_file_override (Plan 47-01)
  provides:
    - quirk.discovery.nmap_provider._default_nmap_args (--max-parallelism 100)
    - quirk.util.optional_extra.OptionalExtra.binary (optional field)
    - quirk.util.optional_extra.REGISTRY (nmap entry)
    - quirk.util.optional_extra.select_nmap_port_list
    - quirk.util.targets.projected_probe_count
    - quirk.util.targets.maybe_confirm_probe_budget
    - wizard nmap y/N global toggle (D-06)
    - run_scan.py D-09 flag reflection
  affects:
    - quirk/discovery/nmap_provider.py (--max-parallelism 100 appended)
    - quirk/util/optional_extra.py (binary field + nmap entry + select_nmap_port_list)
    - quirk/util/targets.py (projected_probe_count + maybe_confirm_probe_budget)
    - quirk/interactive.py (global nmap y/N prompt after target input)
    - run_scan.py (D-09 setattr, D-08 nmap-available gate, D-10/D-11/D-12 budget guard)
tech_stack:
  added:
    - shutil.which (binary-availability probe in optional_extra.py)
    - ipaddress.ip_network().hosts() (probe-count math in targets.py)
  patterns:
    - TDD (RED tests first, then GREEN implementation, for all 3 auto tasks)
    - Phase 45 optional-extra registry pattern extended with binary field
    - D-10 TTY-aware guard with injectable prompt_fn/stderr_print_fn for testing
key_files:
  created:
    - tests/test_nmap_provider.py
    - tests/test_run_scan_budget_guard.py
  modified:
    - quirk/discovery/nmap_provider.py
    - quirk/util/optional_extra.py
    - quirk/util/targets.py
    - quirk/interactive.py
    - run_scan.py
    - tests/test_optional_extra.py
decisions:
  - "binary field added as Optional[str] = None to OptionalExtra dataclass — keyword-only with default; existing 4 entries use kwargs so no breakage (Risks #6)"
  - "select_nmap_port_list placed in optional_extra.py (co-located with the nmap registry entry and is_extra_available); both run_scan.py and tests import from one canonical location"
  - "maybe_confirm_probe_budget uses injectable prompt_fn and stderr_print_fn so TTY/non-TTY branches are unit-testable without subprocess or stdin patching"
  - "No DiscoveryCfg sub-table added — D-09 satisfied via setattr on cfg.connectors (Risks #1); existing --discovery {builtin,nmap} CLI flag is authoritative"
  - "probe_missing_extras availability check: binary_ok = (entry.binary is None) OR (shutil.which(entry.binary) is not None); module check is separate — nmap has empty modules tuple so module gate is vacuously True"
  - "test_all_hints_contain_pip_install_literal updated to skip entries with empty modules tuple (binary-only extras have no pip package; rule 1 bug fix)"
metrics:
  duration: "~6 minutes"
  completed: "2026-05-04"
  tasks_completed: 4
  tasks_total: 4
  files_created: 2
  files_modified: 7
---

# Phase 47 Plan 02: Nmap Discovery UX + Budget Guard Summary

**One-liner:** Global wizard y/N nmap toggle, `--max-parallelism 100` hard-coded, missing-binary coverage_gap advisory via extended OptionalExtra registry, and TTY-aware probe-budget guard at 10,000 probes.

## What Was Built

### Task 1: `--max-parallelism 100` + `OptionalExtra.binary` + nmap registry entry (TDD)

**`quirk/discovery/nmap_provider.py`**
- Appended `"--max-parallelism", "100"` to `_default_nmap_args` return list. Inline comment: `# D-07: hard-coded; not configurable in Phase 47.`

**`quirk/util/optional_extra.py` — binary field extension (D-08 / Risks #6)**
- Added `binary: Optional[str] = None` to `OptionalExtra` dataclass. The field has a default so all 4 existing registry entries (identity, db, cloud, dashboard) are unaffected — they already use keyword args.
- `is_extra_available(extra)`: after the existing `find_spec` check, additionally checks `shutil.which(entry.binary) is not None` when `binary` is set.
- `probe_missing_extras`: availability gate now checks `binary_ok = (entry.binary is None) or (shutil.which(entry.binary) is not None)`. Entry is available only when `modules_ok AND binary_ok`.
- New REGISTRY entry (5th):
  ```python
  OptionalExtra(
      extra="nmap",
      modules=(),
      binary="nmap",
      scanner_label="nmap_discovery",
      install_hint="Nmap discovery unavailable — install nmap (https://nmap.org/) ...",
      enabled_attrs=("enable_nmap",),
  )
  ```

**Tests (RED before GREEN):**
- `test_nmap_provider.py::test_default_args_includes_max_parallelism` — asserts `--max-parallelism` and `100` are consecutive elements in the return list.
- `test_optional_extra.py` — 5 new tests: `test_binary_field_default_is_none`, `test_nmap_registry_entry_present`, `test_nmap_binary_missing_emits_advisory`, `test_nmap_binary_present_no_advisory`, `test_nmap_disabled_silent`.

**Deviation (Rule 1 — Bug fix):** `test_all_hints_contain_pip_install_literal` asserted every registry hint contains `pip install quirk[<extra>]`. Binary-only extras (nmap, `modules=()`) have no pip package — their hint contains system-package instructions. Fixed the test to skip entries with empty `modules` tuple.

### Task 2: Wizard nmap y/N prompt + CONSULTING_TLS_PORTS fallback (TDD)

**`quirk/interactive.py`**
- Added global nmap y/N prompt (using existing `_prompt_bool`) immediately after the target input block:
  ```python
  enable_nmap = _prompt_bool(
      "Run nmap port discovery first? (recommended for >10 hosts)",
      default=False,
  )  # D-06: single global toggle, NOT per-target
  ```
- After cfg construction: `setattr(cfg.connectors, "enable_nmap", _enable_nmap_wizard)` — defensive because `ConnectorsCfg` does not declare `enable_nmap`; no new `DiscoveryCfg` sub-table (Risks #1).

**`run_scan.py`**
- Added `from quirk.util.optional_extra import is_extra_available, select_nmap_port_list`.
- D-09 flag reflection immediately after `--targets-file` override: `setattr(cfg.connectors, "enable_nmap", args.discovery == "nmap")` with inline `# D-09` comment. Placed before `probe_missing_extras` so the registry advisory fires consistently in both wizard and `--config` modes.
- At the nmap call site: replaced hardcoded port list with `select_nmap_port_list(cfg, nmap_binary_available)`. Added `elif not nmap_binary_available` branch that falls back to `expand_targets(cfg)` without invoking `run_nmap_discovery` (D-08: no crash when binary absent).
- D-10/D-11/D-12 budget guard inserted before `with _phase_timer(...)` block (Task 3 fills the tests).

**`quirk/util/optional_extra.py` — `select_nmap_port_list` helper**
```python
def select_nmap_port_list(cfg, nmap_available: bool) -> list:
    if not nmap_available:
        from quirk.interactive import CONSULTING_TLS_PORTS
        return CONSULTING_TLS_PORTS
    return getattr(cfg.scan, "ports_tls", None) or []
```
Placed in `optional_extra.py` so both `run_scan.py` and `test_optional_extra.py` import from one canonical location (avoids circular imports; `interactive.py` is a lazy import inside the function body).

**`quirk/util/targets.py` — probe-budget helpers (implemented in Task 2, tested in Task 3)**

```python
def projected_probe_count(targets: list, ports: list) -> int:
    """Uses .hosts() for CIDRs (Risks #4: excludes network/broadcast on IPv4)."""

def maybe_confirm_probe_budget(
    targets, ports, threshold=10_000, is_tty=None, prompt_fn=input, stderr_print_fn=None
) -> bool:
    """D-10: TTY → y/N confirm. Non-TTY → stderr warn + auto-proceed. D-12: threshold pinned."""
```

Why `.hosts()` not `.num_addresses`: `ip_network("10.0.0.0/24").num_addresses == 256` but `.hosts()` returns 254 (excludes `.0` network and `.255` broadcast). The off-by-2 matters at /24 scope where probe budgets are near the 10,000 threshold. See Risks #4 in RESEARCH.md.

**Tests:**
- `test_optional_extra.py::test_nmap_fallback_uses_consulting_tls_ports` — verifies `select_nmap_port_list(cfg, nmap_available=False)` returns `CONSULTING_TLS_PORTS` and `(nmap_available=True)` returns `cfg.scan.ports_tls`.
- `tests/test_run_scan_budget_guard.py` — scaffolded (placeholder skip replaced in Task 3).

### Task 3: Budget guard tests (TDD)

**`tests/test_run_scan_budget_guard.py`** — 6 tests:

| Test | What it verifies |
|------|-----------------|
| `test_projected_probe_count_includes_cidr_hosts_excludes_net_bcast` | /30 → 2 hosts (not 4). Risks #4. |
| `test_projected_probe_count_mix` | `["a.com", "b.com", "10.0.0.0/24"]` × 2 ports = (2+254)×2 = 512 |
| `test_under_threshold_no_prompt` | <= 10,000 probes: `prompt_fn` never called, returns True |
| `test_over_threshold_tty_user_confirms_yes` | 10,200 probes + TTY + "y" → True |
| `test_over_threshold_tty_user_aborts_no` | 10,200 probes + TTY + "n" → False |
| `test_over_threshold_non_tty_prints_stderr_and_proceeds` | 10,200 + non-TTY → captures "10,200" in stderr msg, returns True |

All 6 pass. Isolated from `run_scan.py` import side-effects via direct import from `quirk.util.targets`.

### Task 4: Regression sweep

- `pytest tests/test_nmap_provider.py tests/test_optional_extra.py tests/test_run_scan_budget_guard.py`: 21 passed.
- Full suite (excluding pre-existing failures): 761 passed, 2 skipped.
- `python -m compileall quirk/ run_scan.py`: clean.

## Commits

| Hash | Message |
|------|---------|
| `a49f7fa` | feat(47-02): hard-code --max-parallelism 100 + add nmap to optional-extra registry (DISCOVER-02, DISCOVER-03) |
| `39b7524` | feat(47-02): wizard nmap y/N prompt + CONSULTING_TLS_PORTS fallback (DISCOVER-01, D-06, D-08, D-09) |
| `75d2248` | feat(47-02): add select_nmap_port_list helper + probe-budget functions to targets.py |
| `75c3e19` | feat(47-02): TTY-aware probe-budget guard tests (DISCOVER-04, D-10..D-12) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_all_hints_contain_pip_install_literal` fails for binary-only registry entries**
- **Found during:** Task 1 GREEN — after adding the nmap entry with `modules=()`
- **Issue:** Pre-existing test asserted every registry entry's `install_hint` contains `pip install quirk[<extra>]`. Binary-only extras (nmap) have no pip package — their hint contains system-package instructions (`install nmap`).
- **Fix:** Updated the test to `continue` (skip) entries whose `modules` tuple is empty.
- **Files modified:** `tests/test_optional_extra.py`
- **Commit:** `a49f7fa`

## Why No `DiscoveryCfg` Sub-table (Risks #1 / D-09)

The existing `--discovery {builtin,nmap}` CLI flag is the single source of truth for non-interactive runs. In interactive mode, the wizard y/N answer is captured and reflected via `setattr(cfg.connectors, "enable_nmap", ...)`. Both paths produce a consistent `cfg.connectors.enable_nmap` boolean visible to:
1. `probe_missing_extras` at ~L398 (registry advisory gate)
2. `is_extra_available("nmap")` at the nmap call site (~L344)

A new `DiscoveryCfg` schema sub-table would require updating `load_config`, `AppConfig`, config YAML format, and all existing config fixture files — significant blast radius for a flag that is effectively a one-shot runtime boolean. The `setattr` approach is self-documenting via `# D-09` comments and is covered by tests.

## Test Coverage Matrix

| Req ID | Test | Status |
|--------|------|--------|
| DISCOVER-01 | test_interactive_mode.py (wizard flow) + D-06 wizard prompt addition | PASS |
| DISCOVER-02 | test_nmap_binary_missing_emits_advisory, test_nmap_binary_present_no_advisory, test_nmap_disabled_silent | PASS |
| DISCOVER-03 | test_default_args_includes_max_parallelism | PASS |
| DISCOVER-04 | test_over_threshold_tty_user_confirms_yes, test_over_threshold_tty_user_aborts_no, test_over_threshold_non_tty_prints_stderr_and_proceeds | PASS |
| D-06 | test_nmap_disabled_silent, interactive_config wizard prompt | PASS |
| D-07 | test_default_args_includes_max_parallelism | PASS |
| D-08 | test_nmap_binary_missing_emits_advisory, test_nmap_fallback_uses_consulting_tls_ports | PASS |
| D-09 | run_scan.py setattr (source-level) | PASS |
| D-10 | test_over_threshold_tty_user_confirms_yes, test_over_threshold_tty_user_aborts_no, test_over_threshold_non_tty_prints_stderr_and_proceeds | PASS |
| D-11 | projected_probe_count uses resolved port list (run_scan.py) | PASS |
| D-12 | threshold=10_000 literal at call site; kwarg exists for tests only | PASS |
| Risks #4 | test_projected_probe_count_includes_cidr_hosts_excludes_net_bcast | PASS |
| Risks #6 | test_binary_field_default_is_none | PASS |

## Pre-existing Test Failures (Out of Scope, Unchanged)

1. `tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[broker]` — requires `cyclonedx-python-lib[json-validation]`; owned by Plan 47-03.
2. `tests/test_v41_gap_closure.py::TestV41GapClosure::test_package_manifest_version_is_4_1_0` — worktree egg-info reflects version 4.0.0 (installed package), but test expects 4.4.0; infrastructure artifact, not caused by Plan 47-02.
3. `tests/test_interactive_mode.py` — 0 failures (all 10 pass; wizard changes preserved existing prompt order).

## Known Stubs

None. All implemented functions are fully wired end-to-end:
- `select_nmap_port_list` is called in `run_scan.py` at the nmap port selection site.
- `maybe_confirm_probe_budget` is called in `run_scan.py` before `_phase_timer`.
- `probe_missing_extras` advisory loop already includes the nmap entry.

## Threat Flags

No new threat surface beyond the plan's threat model. All mitigations from the plan's STRIDE register are implemented:
- T-47-05 (DoS via large scope): `--max-parallelism 100` + probe-budget guard at 10,000 probes.
- T-47-07 (silent binary failure): coverage_gap INFO advisory emitted via registry (D-08).

## Self-Check: PASSED

| Item | Status |
|------|--------|
| quirk/discovery/nmap_provider.py | FOUND |
| quirk/util/optional_extra.py | FOUND |
| quirk/util/targets.py | FOUND |
| quirk/interactive.py | FOUND |
| run_scan.py | FOUND |
| tests/test_nmap_provider.py | FOUND |
| tests/test_optional_extra.py | FOUND |
| tests/test_run_scan_budget_guard.py | FOUND |
| commit a49f7fa | FOUND |
| commit 39b7524 | FOUND |
| commit 75d2248 | FOUND |
| commit 75c3e19 | FOUND |
