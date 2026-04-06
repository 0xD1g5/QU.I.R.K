# Phase 13: Interactive Mode Overhaul - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix `quirk`'s interactive prompt sequence so a security consultant running `quirk` without
a config file reaches a correctly configured scan. Remove broken/misleading prompts, auto-detect
what can be auto-detected, surface live scanner options, and organize the flow professionally.

Scope: `quirk/interactive.py`, `quirk/assessment/operator_context.py`, and the call site in
`run_scan.py` that chains them. INTER-01 through INTER-10.

Not in scope: scoring correctness (Phase 14), code hygiene/stubs (Phase 15), TLS enum mode
surfacing (backlog), SSH port prompts (backlog).
</domain>

<decisions>
## Implementation Decisions

### Removed / Auto-detected Prompts (INTER-01, INTER-02, INTER-03, INTER-07, INTER-09)
- **D-01:** Remove the `timezone` prompt. Auto-detect using Python stdlib:
  `datetime.datetime.now().astimezone().tzname()` — no external dependency needed.
  Store result in `AssessmentCfg.timezone` silently.
- **D-02:** Remove the `include_sni` prompt. Hardcode `include_sni=True` in the returned config.
  SNI is correct for FQDN targets and the prompt confused users.
- **D-03:** Remove the `ports_tls` prompt. Hardcode a consulting-grade default list:
  `[443, 8443, 9443, 10443, 4433, 5001, 636, 3269, 993, 995, 465, 6443, 2376, 5432, 3306, 1433, 8200]`
  (existing list + LDAPS 636/3269, IMAPS 993, POP3S 995, SMTPS 465, K8s 6443,
  Docker TLS 2376, DB ports 5432/3306/1433, Vault 8200).
- **D-04:** Do NOT add an `enable_windows_adcs` prompt. `config_from_dict()` already strips it
  (line 132 of config.py). No generated config will contain this field.

### Scan Profile Selection (INTER-06)
- **D-05:** Replace the raw `timeout_seconds` and `concurrency` prompts with a single profile
  selection question: "Scan profile: quick / standard / deep".
- **D-06:** Descriptions (speed-focused, one line each):
  - `quick` — fast sweep, lower accuracy
  - `standard` — balanced, recommended for most engagements
  - `deep` — thorough, use for high-value targets or regulated environments
- **D-07:** `interactive_config()` returns a tuple `(AppConfig, str)` where the second element
  is the selected profile string ("quick" | "standard" | "deep"). Default: "standard".
- **D-08:** `run_scan.py` is updated to unpack the tuple:
  `cfg, scan_profile = interactive_config()`
  and pass `scan_profile` to `apply_profile(cfg, scan_profile, ...)` instead of `args.profile`.
  When running with a config file (`args.config`), `args.profile` still applies as before.
- **D-09:** The profile string does NOT appear in the saved YAML config. `ScanCfg` gains no new
  field. Profile is only used at runtime to configure timeouts/concurrency via `apply_profile()`.

### Data Classification Consolidation (INTER-10)
- **D-10:** Present a single "Data classification" prompt with 4 consulting-grade tier labels.
  The selection populates BOTH `AssessmentCfg.data_classification` AND `OperatorContext.data_types`.
- **D-11:** Mapping:
  - `Public` → data_classification="public", data_types=["PUBLIC"]
  - `Internal` → data_classification="internal", data_types=["GENERAL"]
  - `Confidential` → data_classification="confidential", data_types=["FINANCIAL", "TRADE"]
  - `Regulated` → data_classification="regulated", data_types=["PCI", "PHI"]
- **D-12:** The `data_types` list from `prompt_for_context()` is derived from this selection
  rather than asked separately. The `prompt_for_context()` call in `run_scan.py` is either
  removed or replaced with a derived-context builder using the classification chosen in
  `interactive_config()`. The other `OperatorContext` fields (`data_longevity_years`,
  `exposure`, `crown_jewels`) remain as separate prompts in a consolidated "Assessment Context"
  section.

### Connector Credential Warnings (INTER-04)
- **D-13:** AWS and Azure are presented as fully implemented connectors (no "(stub)" label).
- **D-14:** Inline credential reminder printed immediately after the user enables a connector:
  - AWS: `⚠  Requires AWS credentials — set AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY, or configure an IAM role profile (aws_profile in config).`
  - Azure: `⚠  Requires Azure credentials — run az login, or set AZURE_CLIENT_ID + AZURE_CLIENT_SECRET + AZURE_TENANT_ID.`

### Prompt Order (INTER-08)
- **D-15:** New prompt order: targets → scan options → output → metadata.
  Specific sections in order:
  1. **Targets** — CIDRs, FQDNs, include_ips, exclude_ips
  2. **Scan options** — profile selection (quick/standard/deep)
  3. **Additional scanners** — JWT, container, source (each with targets if enabled)
  4. **Cloud connectors** — AWS, Azure (with inline credential warnings)
  5. **Output** — output directory, db_path
  6. **Metadata** — assessment name, data classification (unified), report_owner
  (Timezone auto-detected, SNI hardcoded, ADCS removed.)

### Additional Scanners Already Present (INTER-05)
- **D-16:** JWT, container, and source scanner prompts already exist in `interactive_config()`
  (lines 116–129). Verify they are preserved and correctly placed in the new section order.
  No new scanner prompts needed.

### Claude's Discretion
- Exact auto-detect fallback if timezone detection fails (e.g., default to UTC)
- Whether `prompt_for_context()` is removed from `run_scan.py` or refactored into an
  internal helper called by `interactive_config()`
- `data_longevity_years`, `exposure`, `crown_jewels` prompt wording and section placement
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Interactive Mode Source
- `quirk/interactive.py` — current `interactive_config()` implementation (168 lines, full file)
- `quirk/assessment/operator_context.py` — `prompt_for_context()` and `OperatorContext` dataclass

### Call Site
- `run_scan.py` lines 180–197 — where `interactive_config()` and `prompt_for_context()` are
  called and chained; the return-type change in D-07 must be reflected here

### Profile Logic
- `quirk/engine/profiles.py` — `apply_profile(cfg, profile, safe_mode)` with quick/standard/deep
  definitions (lines 75–116); interactive mode profile string feeds directly into this function

### Config Schema
- `quirk/config.py` — `AssessmentCfg`, `ScanCfg`, `ConnectorsCfg`, `config_from_dict()`
  (line 132: `enable_windows_adcs` strip); no new fields required by Phase 13

### Requirements
- `.planning/REQUIREMENTS.md` §Interactive Mode — INTER-01 through INTER-10 with BACK ticket refs
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/interactive.py:_prompt()`, `_prompt_bool()`, `_prompt_int()`, `_prompt_list()`, `_prompt_ports()` — existing helper functions; most will be retained but `_prompt_ports()` may become unused after D-03
- `quirk/engine/profiles.py:apply_profile()` — already handles quick/standard/deep; interactive mode only needs to capture the string

### Established Patterns
- All prompts use stdlib `input()` — no questionary/inquirer dependency; keep this pattern
- Default values shown in brackets: `_prompt("Assessment name", "Quantum Crypto Readiness - Interactive")`
- Boolean prompts use `_prompt_bool()` which defaults to Y/N display

### Integration Points
- `run_scan.py:180–197` — must be updated to unpack `(AppConfig, str)` tuple from `interactive_config()` and pass profile to `apply_profile()`
- `run_scan.py:197` — `prompt_for_context()` call will be replaced by deriving context from the data classification chosen in `interactive_config()`
- `quirk/config.py:config_from_dict()` line 132 — `enable_windows_adcs` strip stays; no changes needed
</code_context>

<specifics>
## Specific Ideas

- Timezone auto-detect: `import datetime; tz = datetime.datetime.now().astimezone().tzname()` — no extra package
- Profile prompt display pattern:
  ```
  Scan profile [standard]:
    1) quick    — fast sweep, lower accuracy
    2) standard — balanced, recommended for most engagements (default)
    3) deep     — thorough, use for high-value targets or regulated environments
  Choice [2]:
  ```
- Data classification prompt display pattern:
  ```
  Data classification [confidential]:
    1) public        — no sensitive data
    2) internal      — general internal data
    3) confidential  — financial, trade secrets, or business-sensitive data
    4) regulated     — PCI, PHI, or other regulated data types
  Choice [3]:
  ```
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>

---

*Phase: 13-interactive-mode-overhaul*
*Context gathered: 2026-04-06*
