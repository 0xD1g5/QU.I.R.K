# Phase 8: Legacy Debt Cleanup - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Every show-stopper bug, dead code artifact, and label/intent inconsistency surfaced by the
CONCERNS.md codebase audit is resolved — the tool works correctly for new users out of the box
and produces internally consistent output.

Scope: config template fix, wrong subcommand references, dead connectors/ directory, interactive
mode label and prompt fixes, migration_advisor.py pattern bugs, cfg.scan mutation safety, version
string consistency, legacy file/artifact removal, dead code pruning, validate.py repair.

Not in scope: scoring consolidation (Phase 9), Windows ADCS implementation (Phase 10/roadmap),
interactive mode UX redesign beyond adding the three missing scanner prompts.
</domain>

<decisions>
## Implementation Decisions

### validate.py
- **D-01:** Fix validate.py — update artifact checks to match real output files (`findings-*.json`,
  `intelligence-*.json`, `executive-summary-*.md`, `cbom-*.cdx.json`, etc.). Fix
  `_latest_intelligence()` to sort by mtime rather than filename when timestamps tie.
- **D-02:** Add one integration test that runs a minimal mock scan and calls `validate_run()` —
  confirms the validator passes on real output and catches Phase 9 regressions automatically.

### Interactive Mode
- **D-03:** Fix AWS/Azure connector labels in `interactive.py` — remove "(stub)" language.
  Change to "Enable AWS connector (fully implemented)" and "Enable Azure connector (fully
  implemented)".
- **D-04:** Remove Windows ADCS prompt and `enable_windows_adcs` field entirely from
  `interactive.py` and `ConnectorsCfg`. The field is stored but never consumed; the feature is
  deferred to v2. Note it for the roadmap (Phase 10 or post-v1 milestone).
- **D-05:** Add JWT, Container, and Source scanner prompts to interactive mode. All three are
  fully implemented but currently unreachable from the interactive path. Prompts should ask for
  enable flag + target list (multi-value input). Matches how AWS/Azure targets are handled.

### Config Template
- **D-06:** Fix `quirk/config_template.yaml` — correct all field name mismatches (§3.4):
  - `scan.timeout` → `scan.timeout_seconds`
  - `scan.max_workers` → `scan.concurrency`
  - `targets.ips` → `targets.include_ips`
  - `connectors.aws.enabled` (nested) → `connectors.enable_aws` (flat)
  - `connectors.azure.enabled` (nested) → `connectors.enable_azure` (flat)
  - `connectors.azure.key_vault_names` → `connectors.azure_keyvault_urls`
  - `connectors.jwt_endpoints` → `connectors.jwt_targets`
  - Remove `scan.ports_ssh` (no such field)
- **D-07:** Fix placeholder URL in config_template.yaml line 4 — substitute `[owner]` with
  the actual GitHub org/repo path (or a canonical docs URL).

### Subcommand Reference Fix
- **D-08:** Remove all references to `quirk scan --config ...` — replace with the correct
  invocation `quirk --config ...`. Affected: `quirk/config_template.yaml`, `quirk/cli/init_cmd.py`,
  `docs/getting-started.md`.

### Dead Code Removal
- **D-09:** Delete `quirk/connectors/` directory entirely (3 stub files + `__init__.py`). All
  three stubs are empty comments; real connectors live in `quirk/scanner/`.
- **D-10:** Delete `quirk/engine/rules.py` — reserved-only empty file, never imported.
- **D-11:** Delete `quirk/intelligence/driver_text.py` — `polish_drivers()` never called in
  production; key mismatches with evidence.py mean it returns empty results if wired.
- **D-12:** Delete `quirk/intelligence/calibration.py` — `get_calibration()` never called;
  uses wrong config field name (`cfg.intelligence.calibration_profile` vs actual
  `cfg.intelligence.profile`).
- **D-13:** Remove 4 dead private functions from `quirk/reports/writer.py`:
  `_count_findings()`, `_extract_cert_dates()`, `_is_self_signed()`, `_mtls_present()`.
  Leave `_extract_cert_key_type()` — it was actively fixed in Phase 1 and is the canonical
  cert key extraction path.
- **D-14:** Leave `quirk/intelligence/schema.py` and `quirk/reports/scorecard.py` for Phase 9
  — both are adjacent to the dual-scoring consolidation and may be repurposed.

### migration_advisor.py Pattern Fixes
- **D-15:** Fix `recommend_migration_paths()` in `quirk/assessment/migration_advisor.py`:
  - `"deprecated tls"` → match actual finding title `"Legacy TLS versions allowed"` (or the
    substring `"Legacy TLS"`)
  - `"public key"` — remove this stale pattern; no finding title contains "public key"
- **D-16:** Leave the rest of `assessment/` (readiness_score.py, confidence.py,
  transition_planner.py, interpretation_engine.py) untouched — Phase 9 scope.

### cfg.scan Mutation Safety
- **D-17:** Wrap the `cfg.scan.timeout_seconds` / `cfg.scan.concurrency` mutation + restore
  pattern in `run_scan.py` with `try/finally` so timeouts are always restored even if a scan
  phase raises an exception.

### Version String Consistency
- **D-18:** Align all version constants to v4.0.0 (set in Phase 7 D-16):
  - `quirk/cbom/builder.py` `PLATFORM_VERSION` → `"4.0"` (currently `"3.9"`)
  - `quirk/reports/writer.py` `INTELLIGENCE_VERSION` → `"4.0.0"` (currently `"4.0.0"` ✓ but
    `quirk/config.py` `intelligence_version` default → `"4.0.0"` from `"3.9.0"`)
  - `quirk/reports/executive.py` line 51 header → remove `v3.7` version tag
  - `quirk/reports/technical.py` lines 46–49 → remove `v3.6` version tag from TLS section header

### Legacy Artifact Cleanup
- **D-19:** Delete `data/qcscan-legacy.sqlite` — artifact from the pre-rename package name.
- **D-20:** Replace `datetime.utcnow()` in `quirk/logging_util.py` and
  `quirk/discovery/nmap_provider.py` with `datetime.now(timezone.utc)` — eliminates
  DeprecationWarning in Python 3.12+.
- **D-21:** Clean `run_scan.py` dead tqdm branch: remove `tqdm = None` assignment (line 161)
  and the dead `if tqdm:` branch (line 283–284). Keep tqdm in pyproject.toml — still used by
  `logging_util.py` for `--progress` flag.

### Claude's Discretion
- Exact wording of the interactive mode JWT/Container/Source prompts
- Whether to add AWS region/profile prompts to interactive mode (§5.2 concern — not in success
  criteria; can be included if straightforward)
- D-reference comment cleanup in source (§6.3) — remove internal ticket comments if touched
  while working on adjacent files; don't sweep the codebase for them separately
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Codebase audit (primary source)
- `.planning/codebase/CONCERNS.md` — Full audit with file:line citations for every issue.
  Phase 8 addresses §1.1, §1.2, §1.6, §1.7, §2.1, §2.2, §2.3, §2.4, §2.5, §2.6, §2.7,
  §3.1, §3.2, §3.4, §3.5, §5.1, §6.1, §6.2, §6.4, §10.2

### Key source files
- `quirk/interactive.py` — AWS/Azure labels, Windows ADCS prompt, missing Phase 3 prompts
- `quirk/config.py` — `ConnectorsCfg` (remove enable_windows_adcs), `config_from_dict()`
  (no field validation — related to D-06)
- `quirk/config_template.yaml` — broken field names (D-06, D-07)
- `quirk/cli/init_cmd.py` — wrong `quirk scan` reference (D-08)
- `quirk/assessment/migration_advisor.py` — stale string patterns (D-15)
- `quirk/reports/writer.py` — dead functions (D-13), version constants (D-18)
- `quirk/reports/executive.py` — version tag in section header (D-18)
- `quirk/reports/technical.py` — version tag in section header (D-18)
- `quirk/cbom/builder.py` — PLATFORM_VERSION mismatch (D-18)
- `quirk/validate.py` — wrong artifact checks (D-01)
- `run_scan.py` — cfg.scan mutation (D-17), tqdm dead branch (D-21)
- `quirk/logging_util.py` — datetime.utcnow() (D-20)
- `quirk/discovery/nmap_provider.py` — datetime.utcnow() (D-20)

### Phase 9 context (boundary)
- Phase 9 ROADMAP entry — scoring consolidation owns assessment/readiness_score.py,
  assessment/confidence.py, assessment/transition_planner.py. Phase 8 must not remove these.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/scanner/aws_connector.py`, `quirk/scanner/azure_connector.py` — fully implemented;
  interactive mode prompts need to match what these connectors actually accept
- `quirk/cli/init_cmd.py` — existing init subcommand pattern; `quirk scan` fix goes here
- `quirk/interactive.py` — existing prompt helpers (`_prompt_bool`, `_prompt_str`) available
  for adding JWT/Container/Source prompts

### Established Patterns
- Config mutation: `ScanCfg(**raw["scan"])` — no field validation; config_template.yaml must
  use exact dataclass field names or raise TypeError at startup (the exact bug being fixed)
- Subcommand dispatch: `run_scan.py` intercepts `init` and `serve` before argparse; `scan`
  subcommand does not exist — correct invocation is `quirk --config config.yaml`
- Version sourcing: `quirk/__init__.py __version__ = "4.0.0"` is the single source of truth;
  all constants in writer.py, cbom/builder.py should reference or match this

### Integration Points
- `quirk/validate.py` `validate_run()` — called nowhere in production, only in tests;
  fix must not break the test suite that currently calls it
- `quirk/connectors/` — confirmed zero imports from any production module; safe to delete
  without any import chain updates needed
- `assessment/migration_advisor.py` `recommend_migration_paths()` — called from where?
  (Downstream agents: verify call site before changing signatures)
</code_context>

<specifics>
## Specific Ideas

- Windows ADCS: remove prompt + note for roadmap Phase 10 (full ADCS implementation with
  Kerberos auth belongs in its own phase, deferred to v2)
- validate.py: minimal fix (correct artifacts + sort fix) + one integration test — not a
  full rewrite; Phase 9 may need to update it again after scoring consolidation
- Dead functions in writer.py: `_extract_cert_key_type()` was actively fixed in Phase 1 —
  do not remove it; remove the other 4 only
</specifics>

<deferred>
## Deferred Ideas

- Windows ADCS implementation — full Kerberos/NTLM + AD CS API connector; deferred to Phase 10
  or post-v1 milestone. Remove prompt in Phase 8, add Phase 10 stub to ROADMAP.md.
- Interactive mode: AWS region/profile prompts (§5.2) — not in success criteria; Claude may
  include if trivial while touching interactive.py, otherwise defer
- D-reference comment sweep (§6.3) — clean internal ticket comments only when touching
  adjacent files, not as a dedicated sweep
- schema.py and scorecard.py cleanup — Phase 9 (adjacent to scoring consolidation)
- assessment/interpretation_engine.py — Phase 9 (entangled with executive.py scoring path)
- quirk.validate full test suite — Phase 9 will change artifact set again; full test coverage
  deferred until scoring stabilizes
</deferred>

---

*Phase: 08-legacy-debt-cleanup*
*Context gathered: 2026-04-02*
