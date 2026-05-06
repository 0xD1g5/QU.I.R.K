# Phase 47: Nmap Discovery + Multi-Target Wizard — Research

**Researched:** 2026-05-03
**Domain:** Multi-target ingestion (CSV/`@file`/CIDR), nmap pre-discovery wiring, CycloneDX JSON schema validation
**Confidence:** HIGH (every finding cited to a specific file:line or verified against the installed `cyclonedx-python-lib==11.7.0` distribution)

## User Constraints (from CONTEXT.md)

### Locked Decisions
D-01..D-16 from `.planning/phases/47-nmap-discovery-multi-target-wizard/47-CONTEXT.md` apply verbatim. Highlights this research depends on:
- D-01: one syntax-routed wizard prompt; per-token routing (`@`/`/`/`,`/bare host).
- D-03: `--targets-file` REPLACES `config.targets.fqdns` and `config.targets.cidrs` entirely.
- D-04: CIDR expansion happens at config-load / argument-parse time, BEFORE scanner dispatch.
- D-07: hard-code `--max-parallelism 100` in `_default_nmap_args`.
- D-08: missing `nmap` binary → coverage_gap INFO finding + fall back to `CONSULTING_TLS_PORTS`.
- D-10/D-11: TTY-aware probe-budget guard (`targets × ports > 10_000`), uses post-config resolved port list, `sys.stdout.isatty()`.
- D-13: replace `cyclonedx-python-lib[validation]` → `[json-validation]`, keep `>=11.7.0,<12`.
- D-14: post-write JSON validation in `cbom/writer.py`; file is NOT deleted on failure.
- D-15: schema violation → `coverage_gap` WARN finding (soft-fail).
- D-16: missing json-validation deps → Phase 45 coverage_gap INFO + skip validation.

### Claude's Discretion
- Binary-probe helper naming/shape in `optional_extra.py`.
- Wording of advisory finding messages (must contain actionable hint).
- Scan-orchestrator insertion point for the probe-budget guard.
- New `quirk/util/targets.py` vs co-locating in `interactive.py`.
- CycloneDX JSON schema version to validate against.

### Deferred Ideas (OUT OF SCOPE)
- MULTI-06 exclude-list `!host` syntax + trailing-comma validation.
- IPv6 CIDR expansion (stdlib `ipaddress` supports it; AC names IPv4 only).
- nmap discovery for non-TLS scanners (motion/broker/etc.).
- Migrating per-scanner `*_AVAILABLE` flag pattern (Phase 45 D-11).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DISCOVER-01 | Wizard prompt to enable nmap | §F4 — single global y/N prompt added to `interactive_config()`; gated by `sys.stdin.isatty()` per D-09 |
| DISCOVER-02 | Graceful warning when nmap binary missing | §F4 — extend `optional_extra.REGISTRY` with binary-probe entry; INFO finding pattern in §F4 |
| DISCOVER-03 | `--max-parallelism 100` default | §F9 — verified ABSENT from `nmap_provider._default_nmap_args` today; one-line append needed |
| DISCOVER-04 | Probe-budget warning at >10 000 | §F8 — guard inserted just before `run_nmap_discovery` call at `run_scan.py:337` |
| MULTI-01 | CSV targets in wizard | §F1 — single parser handles CSV split per token |
| MULTI-02 | `@filepath` syntax in wizard | §F1 — `@`-prefix routed to file load; `#`-comments stripped |
| MULTI-03 | `--targets-file <path>` CLI flag | §F3 — argparse insertion at `run_scan.py:226`; replaces config (D-03) |
| MULTI-04 | IPv4 CIDR via stdlib `ipaddress` | §F2 — expansion already implemented at `quirk/scanner/target_expander.py:14`; reuse, do not duplicate |
| MULTI-05 | Clear error on malformed/missing | §F1 — re-raise `ValueError`/`FileNotFoundError` with actionable message |

## Phase Summary

Phase 47 has three orthogonal slices: (1) a syntax-routed multi-target parser shared between the wizard (`quirk/interactive.py`) and a new `--targets-file` CLI flag (`run_scan.py:221+`); (2) wiring the existing `quirk/discovery/nmap_provider.py:run_nmap_discovery` into the wizard with a TTY-aware probe-budget guard and binary-availability check; and (3) swapping `cyclonedx-python-lib[validation]` → `[json-validation]` and adding a post-write `JsonStrictValidator` call in `quirk/cbom/writer.py`. All three slices reuse the Phase 45 `optional_extra` registry pattern (`quirk/util/optional_extra.py:61`) for advisory findings — there is no new infrastructure invention required.

**Primary recommendation:** create a new `quirk/util/targets.py` for the parser (reused by wizard + CLI + targets-file lines), extend `optional_extra.OptionalExtra` to support an optional `binary` field (or add a sibling `BinaryDependency` tuple), keep CIDR expansion at the existing `target_expander.expand_targets` site (D-04 already satisfied for the YAML path), and call `JsonStrictValidator(SchemaVersion.V1_6).validate_str(...)` immediately after `output_to_file` in the writer.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Target ingestion (CSV / `@file` / CIDR) | Util layer (`quirk/util/targets.py`) | Wizard + CLI consume | Two callers (wizard, `--targets-file`), pure-string transformation, deserves its own module |
| CIDR → host expansion | Pre-dispatch (`quirk/scanner/target_expander.py`) | — | Already lives there; CONTEXT D-04 confirms |
| nmap subprocess invocation | Discovery (`quirk/discovery/nmap_provider.py`) | — | Already exists; only needs `--max-parallelism 100` default + budget guard upstream |
| Probe-budget TTY guard | Scan orchestrator (`run_scan.py` ~L337) | — | Decision is workflow-level (TTY + interactive choice), not discovery-level |
| Optional-binary advisory | Util (`quirk/util/optional_extra.py`) | run_scan.py emits | Phase 45 pattern: registry + probe + advisory `CryptoEndpoint` |
| CBOM JSON validation | CBOM writer (`quirk/cbom/writer.py`) | error_endpoints list | Validation is intrinsic to the write contract; failure becomes a finding |

## Findings

### F1 — Target parser location: NEW `quirk/util/targets.py` [VERIFIED]

Two callers will need the parser — `quirk/interactive.py` (wizard, replacing the four `_prompt_list` calls at L129–132) and `run_scan.py` (new `--targets-file` flag, post-argparse). Co-locating in `interactive.py` would force `run_scan.py` to import from a UI module — anti-pattern given `interactive.py` already imports config + operator-context machinery. A standalone module also matches the existing util shelf (`quirk/util/optional_extra.py`).

**Proposed surface:**
```python
# quirk/util/targets.py
def parse_target_tokens(raw: str) -> tuple[list[str], list[str]]:
    """Returns (fqdns_or_ips, cidrs). Routes per token: @file, /CIDR, host."""

def load_targets_file(path: str) -> str:
    """Read non-blank, non-#-prefixed lines; return as comma-joined string for parse_target_tokens."""
```

Re-raise `ValueError` (bad CIDR from `ipaddress.ip_network`) and `FileNotFoundError` with the offending token in the message — satisfies MULTI-05 / D-05.

### F2 — CIDR expansion site: existing `quirk/scanner/target_expander.py:14` [VERIFIED]

The expansion loop already exists and is canonical:
```python
# quirk/scanner/target_expander.py:14-21
for cidr in (cfg.targets.cidrs or []):
    net = ipaddress.ip_network(cidr, strict=False)
    for ip in net.hosts():
        ...
```
Called from `run_scan.py:359` (`targets = expand_targets(cfg)`). **No duplication needed.** D-04 says expansion at config-load/arg-parse "before scanner dispatch" — `expand_targets` is the dispatch boundary today and both call paths (builtin + nmap) need the host list, so the pre-dispatch invariant is already satisfied. The new parser should populate `TargetsCfg.cidrs` (string CIDRs) and `TargetsCfg.fqdns`/`include_ips` rather than pre-expanding.

**For the nmap path specifically:** `_build_nmap_target_list` at `run_scan.py:55-60` passes raw CIDR strings to nmap (nmap parses CIDR natively). This is correct — no change needed there.

### F3 — Argparse / CLI insertion point: `run_scan.py:221` block [VERIFIED]

```python
# run_scan.py:221
parser = argparse.ArgumentParser(description="QU.I.R.K. ...")
parser.add_argument("--version", ...)
parser.add_argument("--config", help="Path to config.yaml (skip prompts)")
```

Insert `--targets-file <path>` adjacent to `--config` (both are config-source mutually-exclusive flags). Recommended group:
```python
parser.add_argument("--targets-file", help="Path to file of targets (one per line, # comments). Replaces config targets.")
```

After `parse_args` (L260), apply BEFORE the `if args.config:` block (L280) so it composes correctly:
```python
if args.targets_file:
    raw = load_targets_file(args.targets_file)
    fqdns, cidrs = parse_target_tokens(raw)
    cfg.targets.fqdns = fqdns       # D-03: REPLACES
    cfg.targets.cidrs = cidrs       # D-03: REPLACES
```
But cfg doesn't exist until L282/L285 — so the override block goes after L298 (after broker-target plumbing) and before `init_db` at L311. D-03 explicitly: replaces, does not merge.

### F4 — Optional-extra registry: extend `OptionalExtra` with optional `binary` field [VERIFIED]

`quirk/util/optional_extra.py:36-58` defines `OptionalExtra` as a frozen dataclass keyed on importable `modules`. Two viable shapes:

**Option A (recommended):** add optional `binary: Optional[str] = None` field. `is_extra_available` and `probe_missing_extras` check `shutil.which(binary)` when `binary` is set, falling back to `find_spec` for `modules`. Single registry, single probe loop, minimal diff. Drawback: an entry can mean "module missing" OR "binary missing" — message must disambiguate.

**Option B:** new sibling helper `probe_missing_binaries(cfg, error_endpoints)` with its own `BINARY_REGISTRY: tuple[BinaryDependency, ...]`. Cleaner separation, more code. Drawback: two probe call sites in `run_scan.py:386`.

**Recommendation: Option A.** The registry is small (4 entries), and `nmap` is the only foreseeable binary in v4.6 (Phase 47 only). One probe call (`run_scan.py:386`) keeps the orchestrator simple. The `cbom-validation` entry uses pure `modules=("jsonschema", "referencing")` and no binary — both shapes coexist.

**New entries:**
```python
OptionalExtra(
    extra="cbom",  # corresponds to cyclonedx-python-lib[json-validation] surface
    modules=("jsonschema", "referencing"),
    scanner_label="cbom_validator",
    install_hint="CBOM JSON schema validation skipped — run `pip install quirk[cbom]` to enable",
    enabled_attrs=(),  # always probe
),
OptionalExtra(
    extra="nmap",
    modules=(),
    binary="nmap",
    scanner_label="nmap_discovery",
    install_hint="Nmap discovery unavailable — install nmap (https://nmap.org/) and ensure it is in PATH",
    enabled_attrs=("enable_nmap",),  # NEW DiscoveryCfg or similar flag — see F8
),
```

### F5 — `cyclonedx-python-lib[json-validation]` extra contents [VERIFIED]

Verified against installed `cyclonedx-python-lib==11.7.0` distribution metadata:
```
jsonschema[format-nongpl] (>=4.25,<5.0) ; extra == "validation" or extra == "json-validation"
referencing (>=0.28.4)               ; extra == "validation" or extra == "json-validation"
lxml (>=4,<7)                        ; extra == "validation" or extra == "xml-validation"
```
Always-installed (regardless of extras): `license-expression`, `packageurl-python`, `py-serializable`, `sortedcontainers`, `typing_extensions` (py<3.13).

**Implication:** the `cbom-validation` registry entry's `modules` tuple is exactly `("jsonschema", "referencing")`. `py-serializable` is always present so it does NOT gate availability. `lxml` is XML-only — Phase 47 D-13 explicitly drops the XML extra; if XML output is to remain (writer.py L31-33 still calls `XmlV1Dot6`), note that XML serialization works WITHOUT lxml because the lib uses stdlib ElementTree by default — only XML *validation* needed lxml. Confirmed by current writer not failing without lxml installed.

### F6 — Post-write JSON validation API: `JsonStrictValidator.validate_str` [VERIFIED]

Verified by introspecting installed lib:
```python
from cyclonedx.validation.json import JsonStrictValidator
from cyclonedx.schema import SchemaVersion

validator = JsonStrictValidator(SchemaVersion.V1_6)
err = validator.validate_str(file_contents_as_string)  # returns None on success
# Signature: validate_str(data: str, *, all_errors: bool = False)
#   -> None | JsonValidationError | Iterable[JsonValidationError]
```

- Import path: `cyclonedx.validation.json.JsonStrictValidator`, `cyclonedx.schema.SchemaVersion`.
- Returns `None` on success, `JsonValidationError` instance on failure (string `data`, NOT a path — read file first).
- `MissingOptionalDependencyException` is raised if `jsonschema`/`referencing` are absent — catch this for D-16 path.
- Schema version: `SchemaVersion.V1_6` matches the writer's `JsonV1Dot6` at `quirk/cbom/writer.py:28`. **Always pin the writer and validator together** — drift = guaranteed false-positive failures.

### F7 — CBOM writer hook point: `quirk/cbom/writer.py:29-30` [VERIFIED]

Insert after the JSON `output_to_file` call, before the function return at L35:
```python
# quirk/cbom/writer.py — current L27-35
json_out = JsonV1Dot6(bom)
json_out.output_to_file(filename=json_path, allow_overwrite=True, indent=2)
# <-- insert validation here
xml_out = XmlV1Dot6(bom)
xml_out.output_to_file(filename=xml_path, allow_overwrite=True, indent=2)
return json_path, xml_path
```

The writer signature must change to either (a) accept an `error_endpoints: list[CryptoEndpoint] | None = None` parameter for soft-fail finding emission, OR (b) return validation status alongside the paths and let the caller decide. Option (a) keeps `run_scan.py` ergonomically clean and matches the Phase 45 pattern of mutating an `error_endpoints` list passed by the orchestrator. **D-14: file is NOT deleted on failure** — the `validate_str` call comes AFTER `output_to_file`, and there is no `os.remove` on the failure branch.

Caller signature change at any `write_cbom_files(...)` call site (one per file — `grep -rn write_cbom_files quirk/`).

### F8 — Probe-budget guard placement: just before `run_scan.py:337` [VERIFIED]

```python
# run_scan.py:336-345 — current
else:
    open_ports = run_nmap_discovery(
        targets=nmap_targets,
        ports=ports_for_nmap,
        ...
    )
```

`nmap_targets` (L321) and `ports_for_nmap` (L326) are both already resolved BEFORE this call — D-11 satisfied (uses post-config port list). The CIDR strings in `nmap_targets` need expansion to a host count for the budget math: use `ipaddress.ip_network(t, strict=False).num_addresses` for CIDR tokens, count 1 per FQDN/IP. Insert helper just before the `with _phase_timer(...)` block at L332.

```python
projected_probes = _count_hosts(nmap_targets) * len(ports_for_nmap)
if projected_probes > 10_000:
    msg = f"Projected nmap probes: {projected_probes:,} (targets × ports > 10,000)"
    if sys.stdout.isatty():
        if not _prompt_bool(f"{msg}. Continue?", default=False):
            logger.info("Aborted by user.")
            return
    else:
        print(f"⚠️ {msg} — proceeding (non-TTY).", file=sys.stderr)
```

### F9 — `_default_nmap_args` current state: `--max-parallelism 100` ABSENT [VERIFIED]

`quirk/discovery/nmap_provider.py:12-29` shows current args:
```python
return ["-sT", "-n", "-Pn", "--open", "-p", ports_csv, "--max-retries", "1", "--host-timeout", "10s"]
```
No `--max-parallelism`. **One-line addition:**
```python
return ["-sT", "-n", "-Pn", "--open", "-p", ports_csv,
        "--max-retries", "1", "--host-timeout", "10s",
        "--max-parallelism", "100"]
```
Per D-07: hard-coded, not configurable in this phase.

### F10 — TTY detection: `sys.stdout.isatty()` for budget guard, `sys.stdin.isatty()` for wizard [VERIFIED via D-09/D-10]

D-10 explicitly names `sys.stdout.isatty()` for the probe-budget confirm prompt. D-09 ("wizard prompt only fires when stdin is a TTY") implies `sys.stdin.isatty()` for the wizard nmap prompt — correct because wizard reads from stdin. Both are correct as written; do not unify.

Note: `interactive_config()` already implicitly assumes a TTY (uses `input()`). Extending it with the nmap prompt does not change that assumption — the gating is for `run_scan.py`'s decision to CALL `interactive_config()` vs. honor `cfg.discovery.enable_nmap`. Since `run_scan.py:284` already routes to `interactive_config()` only when `--config` is absent, and config-only invocations are necessarily non-interactive, the existing routing satisfies D-09 — no new TTY check inside `interactive.py` needed.

## Recommended Implementation Skeleton

| File | Action | Rationale |
|------|--------|-----------|
| `quirk/util/targets.py` | **CREATE** | Single-source parser shared by wizard + CLI; pure string transformation, easy to unit-test |
| `quirk/util/optional_extra.py` | EXTEND | Add optional `binary` field to `OptionalExtra`; add `cbom` and `nmap` registry entries; `probe_missing_extras` checks `shutil.which(binary)` when set |
| `quirk/discovery/nmap_provider.py` | EDIT (1 line) | Append `"--max-parallelism", "100"` to `_default_nmap_args` return list (L21-29) |
| `quirk/interactive.py` | EDIT | Replace L129–132 four-prompt block with single `Targets (CSV, @file, CIDR)` prompt → `parse_target_tokens`; add nmap y/N prompt + write to new `cfg.discovery.enable_nmap` flag |
| `quirk/config.py` | EDIT | Add `DiscoveryCfg` (or extend existing) with `enable_nmap: bool = False` so config-only mode honors D-09 |
| `run_scan.py` | EDIT | (a) add `--targets-file` arg next to `--config` at L221; (b) post-cfg override block before `init_db` at L311; (c) probe-budget guard at L332 before `run_nmap_discovery`; (d) honor `cfg.discovery.enable_nmap` in non-interactive mode (D-09); (e) update `write_cbom_files` call to pass `error_endpoints` |
| `quirk/cbom/writer.py` | EDIT | Add `error_endpoints` param; load JSON file post-write; call `JsonStrictValidator(SchemaVersion.V1_6).validate_str(...)`; on `JsonValidationError` append `coverage_gap` WARN advisory; on `MissingOptionalDependencyException` skip silently (registry entry handles INFO) |
| `pyproject.toml` | EDIT (1 line) | `cyclonedx-python-lib[validation]>=11.7.0,<12` → `cyclonedx-python-lib[json-validation]>=11.7.0,<12`; add `cbom` and (no-op) `nmap` entries to `[project.optional-dependencies]` if exposing as installable extras |
| `tests/test_targets_parser.py` | CREATE | Unit tests for CSV/`@file`/CIDR routing, malformed input errors, comment stripping |
| `tests/test_optional_extra.py` | EXTEND | Cover `binary`-field probe path (mock `shutil.which`) |
| `tests/test_cbom_writer_validation.py` | CREATE | Cover happy path, schema-violation soft-fail, missing-deps skip |
| `tests/test_run_scan_budget_guard.py` | CREATE | Cover TTY confirm + non-TTY auto-proceed paths (mock `sys.stdout.isatty`) |

## Plan Slicing Recommendation

Three plan files, each merge-able independently after its tests pass:

### 47-01: Target parser + `--targets-file` CLI flag
**Scope:** `quirk/util/targets.py` (new), `quirk/interactive.py` edit (single prompt), `run_scan.py` `--targets-file` flag, tests.
**Requirements:** MULTI-01, MULTI-02, MULTI-03, MULTI-04, MULTI-05.
**Why first:** zero downstream dependencies, pure-Python, fully unit-testable. Unblocks 47-02 (which needs `cfg.targets` populated correctly).

### 47-02: Nmap wiring + `--max-parallelism` + budget guard + binary advisory
**Scope:** `quirk/discovery/nmap_provider.py` (max-parallelism), `quirk/util/optional_extra.py` (binary-probe extension + `nmap` entry), `quirk/config.py` (`DiscoveryCfg.enable_nmap`), `quirk/interactive.py` (nmap y/N prompt), `run_scan.py` (budget guard + non-interactive routing).
**Requirements:** DISCOVER-01, DISCOVER-02, DISCOVER-03, DISCOVER-04.
**Why second:** depends on 47-01 (`cfg.targets.cidrs`/`fqdns` populated by parser); independent of 47-03 (CBOM validation is orthogonal).

### 47-03: CycloneDX `[json-validation]` swap + post-write JSON-schema validation
**Scope:** `pyproject.toml` (extras swap), `quirk/util/optional_extra.py` (`cbom` entry), `quirk/cbom/writer.py` (validator call + soft-fail finding plumbing), `run_scan.py` (writer call-site signature update), tests.
**Requirements:** none from the v4.6 list directly — this is the bundled CBOM-validation work CONTEXT folds into Phase 47. Verification via writer-level test + full scan smoke.
**Why third (or parallel to 47-02):** completely orthogonal to discovery work. Could parallelize with 47-02 if implementation bandwidth allows; sequencing it last keeps the dependency DAG linear.

## Risks / Unknowns

1. **`DiscoveryCfg.enable_nmap` does not exist today** — D-09 says "non-interactive mode uses `config.discovery.enable_nmap` (default false)", but there is no `DiscoveryCfg` in `quirk/config.py`. The planner must decide whether to (a) add a new `DiscoveryCfg` sub-config, (b) reuse the existing `--discovery {builtin,nmap}` CLI flag (`run_scan.py:228`) as the source of truth and reflect it into config at parse-time, or (c) add a flag to an existing sub-config. Recommend (b) — the flag already exists and config-from-yaml callers can already set it via CLI override. This avoids a config-schema migration.

2. **Writer signature change ripple** — `write_cbom_files` is called from at least one site in `run_scan.py` and possibly the dashboard. Plan 47-03 must `grep -rn write_cbom_files` and update every caller. If any caller can't pass `error_endpoints` (e.g., dashboard re-render), make the param `Optional[list] = None` and skip emission when None.

3. **Targets-file → existing `_build_nmap_target_list`** — once `--targets-file` populates `cfg.targets.fqdns`/`cidrs`, the existing nmap-target builder at `run_scan.py:55-60` works unchanged. Planner should add a regression test asserting that a 5-line targets file with one CIDR produces the same `nmap_targets` list as an equivalent YAML config.

4. **CIDR `num_addresses` includes network/broadcast** — `target_expander.py:16` uses `.hosts()` (excludes net/bcast) but the budget-guard projection should likewise use `.hosts()` not `.num_addresses` to avoid off-by-2-per-CIDR over-projection. For a /24 this is 254 vs 256 — small, but visible.

5. **`MissingOptionalDependencyException` import path** — `cyclonedx.validation.json` exports this name; importing it for the try/except in writer.py is fine, but the planner should pin the import location in case the lib reorganizes within the `>=11.7.0,<12` window. The 11.x line is API-stable per semver.

6. **Phase 45 advisory shape mutation** — adding the `binary` field to `OptionalExtra` is technically a breaking change to a frozen dataclass's positional constructor. All existing 4 entries use keyword args (`quirk/util/optional_extra.py:62-104`) so adding a new keyword-only optional field at the end is safe, but planner should make the field `Optional[str] = None` with a default to preserve backward compatibility.

## Out-of-Scope Confirmations (from CONTEXT)

- Exclude-list `!host` syntax → MULTI-06, future phase.
- IPv6 CIDR expansion → deferred (acceptance criteria are IPv4-only).
- nmap discovery for non-TLS scanners (motion/broker/email) → Phase 47 wires nmap into the TLS-host workflow only.
- Per-target nmap overrides via wizard → config-only (power users); D-06 mandates a single global y/N to avoid 50+ prompts.
- Configurable probe-budget threshold → locked at 10 000 by D-12.
- Configurable `--max-parallelism` → locked at 100 by D-07.
- Migrating per-scanner `*_AVAILABLE` flag pattern → Phase 45 D-11 prohibits.
- Deleting CBOM file on schema-validation failure → D-14 prohibits.
- Hard-failing the scan on schema-validation failure → D-15 prohibits (soft-fail WARN finding only).

## Project Constraints (from CLAUDE.md)

- PEP 8 across all Python diffs.
- Minimal-diff discipline — no unrelated refactors in this phase.
- Run `python -m compileall` and relevant tests after each change.
- Mandatory Phase Completion Steps: Obsidian phase note (write to vault filesystem, NOT via `obsidian content=`), update `docs/UAT-SERIES.md`, sync UAT-SERIES.md to vault, commit UAT-SERIES.md.
- Chaos lab maintenance: Phase 47 does not touch chaos lab profiles. If scope grows to add a discovery-test profile, `lab.sh` ALL_PROFILES + README.md + `expected_results_*.md` must update in the same change.

## Validation Architecture

| Property | Value |
|----------|-------|
| Framework | pytest (existing — confirmed by `tests/__pycache__/test_intelligence_*.cpython-314.pyc` artifacts in git status) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (verify location during planning) |
| Quick run command | `pytest tests/test_targets_parser.py tests/test_optional_extra.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MULTI-01 | CSV split | unit | `pytest tests/test_targets_parser.py::test_csv_split -x` | ❌ Wave 0 |
| MULTI-02 | `@file` load with comments | unit | `pytest tests/test_targets_parser.py::test_at_file_with_comments -x` | ❌ Wave 0 |
| MULTI-03 | `--targets-file` replaces config | integration | `pytest tests/test_run_scan_targets_file.py -x` | ❌ Wave 0 |
| MULTI-04 | CIDR expansion | unit | `pytest tests/test_targets_parser.py::test_cidr_expand -x` | ❌ Wave 0 |
| MULTI-05 | Malformed → clear error | unit | `pytest tests/test_targets_parser.py::test_malformed_raises -x` | ❌ Wave 0 |
| DISCOVER-01 | Wizard nmap prompt | unit | `pytest tests/test_interactive.py::test_nmap_prompt -x` | ❌ Wave 0 (extend if exists) |
| DISCOVER-02 | Missing nmap → INFO finding | unit | `pytest tests/test_optional_extra.py::test_nmap_binary_missing -x` | ❌ Wave 0 (extend) |
| DISCOVER-03 | `--max-parallelism 100` in default args | unit | `pytest tests/test_nmap_provider.py::test_default_args_includes_parallelism -x` | ❌ Wave 0 |
| DISCOVER-04 | Budget guard at 10 000 | unit | `pytest tests/test_run_scan_budget_guard.py -x` | ❌ Wave 0 |
| (CBOM-VALIDATE happy) | Valid CBOM passes | unit | `pytest tests/test_cbom_writer_validation.py::test_valid_passes -x` | ❌ Wave 0 |
| (CBOM-VALIDATE soft-fail) | Schema violation → WARN | unit | `pytest tests/test_cbom_writer_validation.py::test_invalid_soft_fails -x` | ❌ Wave 0 |
| (CBOM-VALIDATE deps-missing) | Missing jsonschema → INFO | unit | `pytest tests/test_cbom_writer_validation.py::test_missing_deps_skips -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_targets_parser.py tests/test_optional_extra.py tests/test_cbom_writer_validation.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green + manual smoke (CSV, `@file`, CIDR each through wizard once)

### Wave 0 Gaps
- [ ] `tests/test_targets_parser.py` — covers MULTI-01..05
- [ ] `tests/test_run_scan_targets_file.py` — covers MULTI-03 integration
- [ ] `tests/test_run_scan_budget_guard.py` — covers DISCOVER-04
- [ ] `tests/test_nmap_provider.py` — covers DISCOVER-03 (and may already exist; planner verifies)
- [ ] `tests/test_cbom_writer_validation.py` — covers CBOM validation triplet
- [ ] Extend `tests/test_optional_extra.py` for binary-probe path (DISCOVER-02)
- [ ] Extend `tests/test_interactive.py` (or create if absent) for nmap y/N prompt (DISCOVER-01)

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Hard-error on malformed CIDR (`ipaddress.ip_network` raises `ValueError`) and missing file (`FileNotFoundError`) — D-05; no silent skips |
| V6 Cryptography | no | — |
| V12 Files & Resources | yes | `--targets-file` reads from arbitrary user-supplied path; honor user intent, no path-traversal sanitization needed (CLI-trusted boundary). Do NOT follow nested `@file` references (D-02) — prevents inadvertent multi-file walks |
| V14 Configuration | yes | `cyclonedx-python-lib[json-validation]` pin window `>=11.7.0,<12` matches existing project convention |

### Known Threat Patterns for Phase 47

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Subprocess injection via target string | Tampering | nmap targets are validated by `ipaddress`/`@file` parser; any token reaching `subprocess.run(args)` (`nmap_provider.py:55`) is passed via list-form (already safe — no shell=True) |
| Probe-budget DoS via huge CIDR | DoS | TTY-aware budget guard (D-10/D-11/D-12) requires confirmation at >10 000 probes |
| CBOM JSON tampering downstream | Tampering | Post-write schema validation (D-14) catches malformed JSON before user consumes the artifact |
| Missing-binary silent failure | Repudiation | Coverage_gap INFO finding ensures the report shows nmap was unavailable (D-08, INSTALL-02 pattern) |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `pytest` is the test framework — inferred from `.cpython-314.pyc` artifacts under `tests/__pycache__/` | Validation Architecture | Test commands wrong; planner must verify by reading `pyproject.toml` |
| A2 | `write_cbom_files` is called only from `run_scan.py` (and possibly dashboard) | F7, Risks #2 | Missed call sites → broken kwarg signature; planner must `grep -rn write_cbom_files` |
| A3 | `tests/test_interactive.py` exists or can be created cleanly | Wave 0 Gaps | Minor — file creation is straightforward |
| A4 | XML output (`XmlV1Dot6` at writer.py L31-33) is intentionally retained even after dropping `[validation]` extra (which provided lxml for XML *validation*, not generation) | F5 | If XML output should also drop, scope expands; but D-13 only names JSON, so retaining XML write is safe |

All other claims are `[VERIFIED]` against either source files or the installed `cyclonedx-python-lib==11.7.0` distribution metadata.

## Open Questions

1. **`DiscoveryCfg.enable_nmap` schema location** — see Risks #1. Recommend reusing `--discovery {builtin,nmap}` CLI flag rather than adding a new config sub-table. Planner decides during 47-02.
2. **Should the `cbom` extra be exposed in `[project.optional-dependencies]` so users can `pip install quirk[cbom]`?** — D-16's coverage_gap INFO finding text uses `pip install quirk[cbom]`. If `[cbom]` doesn't exist as an extra, the hint is wrong. Recommend ADD a `cbom = ["cyclonedx-python-lib[json-validation]>=11.7.0,<12"]` entry, then ALSO include it in `[all]`. Planner confirms in 47-03.
3. **Per-CIDR vs aggregate budget projection wording** — F8 shows `f"Projected nmap probes: {projected_probes:,}"`. If the user has multiple large CIDRs, would itemized breakdown help? Out of scope; mention in plan as a UX-polish candidate for v4.6.x.

## Sources

### Primary (HIGH confidence)
- `quirk/discovery/nmap_provider.py` (read in full) — current default args, subprocess call shape
- `quirk/discovery/nmap_parser.py` (read in full) — `NmapOpenPort` shape
- `quirk/cbom/writer.py` (read in full) — current write path, hook point
- `quirk/util/optional_extra.py` (read in full) — Phase 45 registry pattern
- `quirk/interactive.py` (read in full) — wizard prompt idioms, target prompt block at L129–132
- `quirk/scanner/target_expander.py` (read in full) — existing CIDR expansion site
- `run_scan.py:1-345` (read in full) — argparse, `_build_nmap_target_list`, nmap call site
- `quirk/config.py:178-340` (TargetsCfg + load) — config schema
- `pyproject.toml:16` — current cyclonedx pin
- `cyclonedx-python-lib==11.7.0` distribution metadata via `importlib.metadata` — `[json-validation]` extra contents
- `cyclonedx.validation.json.JsonStrictValidator` introspected via Python — API signature

### Secondary (MEDIUM confidence)
- `.planning/phases/47-nmap-discovery-multi-target-wizard/47-CONTEXT.md` — D-01..D-16 (canonical for this phase)
- `.planning/REQUIREMENTS.md` § DISCOVER/MULTI — acceptance language

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library/version is verified against installed distribution
- Architecture: HIGH — every hook point is cited to file:line
- Pitfalls: HIGH — Risks section anchored in actual code (writer signature, `num_addresses` vs `hosts()`)
- Test infra: MEDIUM — pytest assumed but not confirmed via `pyproject.toml` read

**Research date:** 2026-05-03
**Valid until:** 2026-06-02 (30 days; cyclonedx-python-lib 11.x is stable per semver)
