# Phase 13: Interactive Mode Overhaul - Research

**Researched:** 2026-04-06
**Domain:** Python CLI interactive prompt refactoring (stdlib input(), dataclass config)
**Confidence:** HIGH

## Summary

Phase 13 is a pure Python refactoring of `quirk/interactive.py` and its call site in
`run_scan.py`. All design decisions were locked in the CONTEXT.md discussion session — no
library choices or architecture decisions remain open. The work is self-contained: every change
touches exactly three files (`quirk/interactive.py`, `quirk/assessment/operator_context.py`, and
`run_scan.py`), with no new dependencies and no config schema changes.

The existing implementation has 168 lines and uses only stdlib `input()` via thin helper
functions (`_prompt`, `_prompt_bool`, `_prompt_int`, `_prompt_list`, `_prompt_ports`). This
pattern is correct and must be preserved. The current prompt ordering is wrong (metadata first,
targets buried), several prompts ask for things that should be auto-detected or hardcoded, and
the return signature `-> AppConfig` must change to `-> tuple[AppConfig, str]` to carry the
selected scan profile.

The key integration constraint is `run_scan.py` lines 179–198. After the tuple return type
change, `cfg = interactive_config()` becomes `cfg, scan_profile = interactive_config()`, and the
`apply_profile(cfg, args.profile, ...)` call becomes `apply_profile(cfg, scan_profile, ...)`.
The `prompt_for_context()` call at line 197 is replaced by deriving `OperatorContext` from the
data classification chosen inside `interactive_config()`.

Timezone auto-detect was verified: `datetime.datetime.now().astimezone().tzname()` returns the
correct local timezone name on this macOS host (returns `"EDT"` on macOS, appropriate IANA name
on Linux). A fallback to `"UTC"` on any exception is left to Claude's discretion.

**Primary recommendation:** Implement as a single plan (or two tightly sequenced plans: TDD scaffold + implementation), modifying only the three identified files. No external dependencies needed.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Remove the `timezone` prompt. Auto-detect using `datetime.datetime.now().astimezone().tzname()`. Store result in `AssessmentCfg.timezone` silently.
- **D-02:** Remove the `include_sni` prompt. Hardcode `include_sni=True`.
- **D-03:** Remove the `ports_tls` prompt. Hardcode the extended consulting-grade list: `[443, 8443, 9443, 10443, 4433, 5001, 636, 3269, 993, 995, 465, 6443, 2376, 5432, 3306, 1433, 8200]`.
- **D-04:** Do NOT add an `enable_windows_adcs` prompt. `config_from_dict()` already strips it. No generated config will contain this field.
- **D-05:** Replace `timeout_seconds` and `concurrency` prompts with a single scan profile question: "quick / standard / deep".
- **D-06:** Profile descriptions: `quick` — fast sweep, lower accuracy; `standard` — balanced, recommended for most engagements; `deep` — thorough, use for high-value targets or regulated environments.
- **D-07:** `interactive_config()` returns `tuple[AppConfig, str]` where the second element is the profile string ("quick" | "standard" | "deep"). Default: "standard".
- **D-08:** `run_scan.py` updated to unpack tuple: `cfg, scan_profile = interactive_config()` and pass `scan_profile` to `apply_profile(cfg, scan_profile, ...)`. When running with config file, `args.profile` still applies as before.
- **D-09:** The profile string does NOT appear in saved YAML config. `ScanCfg` gains no new field.
- **D-10:** Single "Data classification" prompt with 4 tiers populates BOTH `AssessmentCfg.data_classification` AND `OperatorContext.data_types`.
- **D-11:** Classification mapping — `Public` → data_classification="public", data_types=["PUBLIC"]; `Internal` → data_classification="internal", data_types=["GENERAL"]; `Confidential` → data_classification="confidential", data_types=["FINANCIAL", "TRADE"]; `Regulated` → data_classification="regulated", data_types=["PCI", "PHI"].
- **D-12:** `prompt_for_context()` call in `run_scan.py` replaced by deriving context from the classification chosen in `interactive_config()`. Other `OperatorContext` fields (`data_longevity_years`, `exposure`, `crown_jewels`) remain as separate prompts in a consolidated "Assessment Context" section.
- **D-13:** AWS and Azure presented as fully implemented connectors (no "(stub)" label).
- **D-14:** Inline credential reminder printed immediately after user enables a connector: AWS reminder and Azure reminder (exact text specified in CONTEXT.md).
- **D-15:** New prompt order: Targets → Scan options → Additional scanners → Cloud connectors → Output → Metadata.

### Claude's Discretion

- Exact auto-detect fallback if timezone detection fails (e.g., default to UTC)
- Whether `prompt_for_context()` is removed from `run_scan.py` or refactored into an internal helper called by `interactive_config()`
- `data_longevity_years`, `exposure`, `crown_jewels` prompt wording and section placement

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INTER-01 | Interactive mode detects local timezone automatically without prompting | D-01: `datetime.datetime.now().astimezone().tzname()` verified working |
| INTER-02 | Interactive mode does not prompt for SNI (hardcoded True for FQDN targets) | D-02: Remove `include_sni` prompt, set `include_sni=True` in ScanCfg |
| INTER-03 | Interactive mode does not prompt for Windows ADCS (non-functional feature removed) | D-04: No prompt needed; `config_from_dict()` already strips the field at line 132 of config.py |
| INTER-04 | Interactive mode correctly labels AWS and Azure as implemented connectors with credential warnings | D-13/D-14: Remove "(stub)" labels, add inline warning messages |
| INTER-05 | User can enable JWT, container, and source scanners from interactive mode | D-16: Prompts already exist at lines 116–129 of interactive.py; verify preserved in new order |
| INTER-06 | Interactive mode offers scan profile selection (quick/standard/deep) instead of raw timeout/concurrency | D-05 through D-09: Replace two prompts with profile menu |
| INTER-07 | Interactive mode uses consulting-grade TLS port default list without prompting | D-03: Hardcode extended list (17 ports), retire `_prompt_ports()` call |
| INTER-08 | Interactive mode presents prompts in targets-first order | D-15: New order: Targets → Scan options → Scanners → Connectors → Output → Metadata |
| INTER-09 | `enable_windows_adcs` dead field removed from interactive mode and generated configs | D-04: No prompt to add; config.py line 132 already strips it from loaded configs |
| INTER-10 | Interactive mode presents a single coherent data classification prompt | D-10/D-11/D-12: Unified 4-option prompt replaces separate `data_classification` and `data_types` prompts |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `datetime` | built-in | Timezone auto-detection | No dependency needed; `datetime.now().astimezone().tzname()` returns local TZ name |
| Python stdlib `input()` | built-in | All prompts | Existing pattern; no questionary/inquirer dependency per established project convention |

### No New Dependencies
This phase introduces zero new packages. All implementation uses existing stdlib and the project's
own helper functions.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `input()` | questionary, PyInquirer | questionary adds a dependency and changes the UX paradigm; existing pattern must be preserved |
| stdlib `datetime.tzname()` | `pytz`, `zoneinfo` | stdlib is sufficient; pytz/zoneinfo return IANA names, but `tzname()` returns the display name (e.g. "EDT") which is already used in assessment reports |

---

## Architecture Patterns

### File Map for Phase 13
```
quirk/
├── interactive.py          ← PRIMARY: full rewrite of interactive_config() body
│                              - Remove: timezone prompt, include_sni prompt, ports_tls prompt
│                              - Add: timezone auto-detect, profile selection menu,
│                                     data classification unified prompt,
│                                     connector credential warnings
│                              - Reorder: targets first, then options, scanners, connectors, output, metadata
│                              - Return type change: AppConfig → tuple[AppConfig, str]
│
├── assessment/
│   └── operator_context.py ← SECONDARY: prompt_for_context() is deprecated for interactive mode;
│                              OperatorContext construction moves into interactive_config() or a
│                              private helper; attach_context() / get_context() unchanged
│
run_scan.py                 ← CALL SITE: unpack tuple, route profile, remove prompt_for_context() call
```

### Pattern 1: Profile Selection Menu
**What:** Numbered list with descriptions, defaulting to "standard" (option 2)
**When to use:** Any time three or more mutually exclusive options need consulting-friendly labels
**Example (from CONTEXT.md specifics):**
```python
# Source: 13-CONTEXT.md §Specific Ideas
def _prompt_profile(default: str = "standard") -> str:
    profiles = {
        "1": ("quick",    "fast sweep, lower accuracy"),
        "2": ("standard", "balanced, recommended for most engagements (default)"),
        "3": ("deep",     "thorough, use for high-value targets or regulated environments"),
    }
    default_num = "2"
    print(f"\nScan profile [{default}]:")
    for num, (name, desc) in profiles.items():
        print(f"  {num}) {name:<10} — {desc}")
    raw = _prompt("Choice", default_num).strip()
    return profiles.get(raw, profiles[default_num])[0]
```

### Pattern 2: Data Classification Menu
**What:** Numbered list mapping a single selection to two config fields simultaneously
**When to use:** When one user concept maps to multiple implementation fields (INTER-10)
**Example (from CONTEXT.md specifics):**
```python
# Source: 13-CONTEXT.md §Specific Ideas
_DATA_CLASS_MAP = {
    "1": ("public",       ["PUBLIC"],              "no sensitive data"),
    "2": ("internal",     ["GENERAL"],             "general internal data"),
    "3": ("confidential", ["FINANCIAL", "TRADE"],  "financial, trade secrets, or business-sensitive data"),
    "4": ("regulated",    ["PCI", "PHI"],          "PCI, PHI, or other regulated data types"),
}
def _prompt_data_classification(default_num: str = "3") -> tuple[str, list[str]]:
    print("\nData classification:")
    for num, (label, _, desc) in _DATA_CLASS_MAP.items():
        print(f"  {num}) {label:<14} — {desc}")
    raw = _prompt("Choice", default_num).strip()
    label, data_types, _ = _DATA_CLASS_MAP.get(raw, _DATA_CLASS_MAP[default_num])
    return label, data_types
```

### Pattern 3: Credential Warning Print
**What:** Inline `print()` call immediately after the user enables a connector
**When to use:** Any boolean enable prompt that implies an external credential requirement
**Example:**
```python
# Source: 13-CONTEXT.md D-14
enable_aws = _prompt_bool("Enable AWS connector", False)
if enable_aws:
    print("  ⚠  Requires AWS credentials — set AWS_ACCESS_KEY_ID + "
          "AWS_SECRET_ACCESS_KEY, or configure an IAM role profile "
          "(aws_profile in config).")
```

### Pattern 4: OperatorContext derivation without prompting data_types
**What:** Build OperatorContext inside `interactive_config()` using the classification string,
then return it alongside AppConfig (or via `attach_context`), removing the separate
`prompt_for_context()` call in run_scan.py.

The remaining OperatorContext fields (`data_longevity_years`, `exposure`, `crown_jewels`) still
need prompts. Two implementation options (Claude's discretion):

- **Option A:** Integrate those three prompts into `interactive_config()` under a
  "Assessment Context" section header and return `(AppConfig, str, OperatorContext)` — but this
  changes the return signature more than D-07 specifies.
- **Option B (preferred):** Build OperatorContext inside `interactive_config()`, attach it to
  `cfg` immediately via `attach_context(cfg, ctx)` before returning, and remove the
  `prompt_for_context()` call from `run_scan.py`. Return type stays `tuple[AppConfig, str]`.

Option B keeps `run_scan.py` simpler and is more consistent with D-07 (return type is exactly
two elements).

### Pattern 5: run_scan.py call site change
```python
# BEFORE (current run_scan.py lines 179–198)
cfg = interactive_config()
apply_profile(cfg, args.profile, safe_mode=args.safe_mode)
...
if not used_config_file:
    ctx = prompt_for_context()
    attach_context(cfg, ctx)

# AFTER
cfg, scan_profile = interactive_config()   # D-07 / D-08
apply_profile(cfg, scan_profile, safe_mode=args.safe_mode)
# prompt_for_context() call removed — context already attached inside interactive_config()
```

### Anti-Patterns to Avoid
- **Adding `scan_profile` to ScanCfg:** D-09 explicitly prohibits this. Profile is runtime-only.
- **Calling `_prompt_ports()` for the TLS port list:** D-03 hardcodes it. The `_prompt_ports()` helper may become dead code after this phase (do not delete it yet — that is Phase 15 hygiene scope).
- **Labeling AWS/Azure as stubs:** D-13 forbids "(stub)" labels. The AWS and Azure connectors are fully implemented.
- **Keeping separate `data_types` prompt:** D-10/D-11 unify it into the classification menu.
- **Passing `args.profile` to `apply_profile` in interactive mode:** After D-08, interactive mode uses `scan_profile` from the tuple return.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Timezone detection | Custom TZ lookup table | `datetime.datetime.now().astimezone().tzname()` | stdlib, zero dependencies, tested on this host |
| Profile lookup | Custom profile class or dict wrapper | Plain `dict` + string return | `apply_profile()` already accepts the plain string |
| Numbered menu selection | Full menu framework | Pattern shown above (dict + `_prompt()`) | Consistent with existing `_prompt` helper style |

**Key insight:** The existing helper infrastructure (`_prompt`, `_prompt_bool`, `_prompt_int`,
`_prompt_list`) is sufficient for everything Phase 13 requires. Introduce only `_prompt_profile()`
and `_prompt_data_classification()` as new private helpers using the same pattern.

---

## Common Pitfalls

### Pitfall 1: ScanCfg constructor will fail with old positional args
**What goes wrong:** `ScanCfg` has four positional required fields — `timeout_seconds`, `concurrency`,
`ports_tls`, `include_sni`. If interactive_config() no longer prompts for timeout/concurrency/sni,
it must still supply values to construct `ScanCfg`. The profile sets them at runtime via
`apply_profile()`, but `ScanCfg` needs values at construction time.
**Why it happens:** `ScanCfg` is a plain dataclass with no `Optional` on its first four fields.
**How to avoid:** Supply safe baseline values for the positional fields:
  `timeout_seconds=5, concurrency=200, ports_tls=HARDCODED_LIST, include_sni=True`.
  `apply_profile()` will override `timeout_seconds` and `concurrency` to the profile-appropriate
  values immediately after `interactive_config()` returns.
**Warning signs:** `TypeError: ScanCfg.__init__() missing required positional arguments`

### Pitfall 2: Return type annotation change breaks callers
**What goes wrong:** Any code that does `cfg = interactive_config()` without expecting a tuple
will silently work at the assignment line but fail when `cfg.assessment` is accessed (it will
be the tuple, not AppConfig).
**Why it happens:** Python does not enforce return type annotations at runtime.
**How to avoid:** Update `run_scan.py` line 180 simultaneously with the return type change. The
only caller of `interactive_config()` in the codebase is `run_scan.py` line 180.
**Warning signs:** `AttributeError: 'tuple' object has no attribute 'assessment'`

### Pitfall 3: `prompt_for_context()` import left in run_scan.py
**What goes wrong:** Even if the call is removed, the import at line 26 of `run_scan.py` remains.
This is benign at runtime but inconsistent if the function is later removed.
**Why it happens:** Refactors often remove calls but forget imports.
**How to avoid:** If `prompt_for_context()` moves entirely inside `interactive_config()`, remove
the import from `run_scan.py`. If `attach_context()` is still called from `run_scan.py`, keep
that import only.
**Warning signs:** Unused import linter warnings; confusion for future maintainers.

### Pitfall 4: `_prompt_ports()` removed prematurely
**What goes wrong:** Removing `_prompt_ports()` from `interactive.py` in this phase violates the
Phase 15 (Code Hygiene) scope boundary.
**Why it happens:** It's tempting to clean up dead code immediately.
**How to avoid:** Leave `_prompt_ports()` in place. Only remove it in Phase 15.

### Pitfall 5: Data classification prompt default index mismatch
**What goes wrong:** CONTEXT.md D-11 implies "confidential" is the sensible default (consistent
with the current `_prompt("Data classification ...", "confidential")` default). If the numbered
menu defaults to option "3" (confidential), the mapping must be verified — option 3 must map to
"confidential".
**Why it happens:** Off-by-one errors in dict-key-to-label alignment.
**How to avoid:** Verify that `_DATA_CLASS_MAP["3"]` returns `("confidential", [...], "...")`.

### Pitfall 6: `OperatorContext` construction inside `interactive_config()` needs `data_longevity_years`, `exposure`, `crown_jewels`
**What goes wrong:** `OperatorContext` is a dataclass with four required fields. If only
`data_types` is derived from classification and the other three are not prompted, construction
will fail.
**Why it happens:** D-12 says those three fields "remain as separate prompts" — but they must
appear somewhere. If they move into `interactive_config()`, the current `prompt_for_context()`
call in `run_scan.py` is fully replaced and can be removed. If they stay in a separate helper,
that helper must still be called.
**How to avoid:** Ensure all four `OperatorContext` fields are populated before calling
`attach_context(cfg, ctx)`.

---

## Code Examples

### Current interactive_config() signature (line 79 of interactive.py)
```python
# Source: quirk/interactive.py — current state
def interactive_config() -> AppConfig:
    ...
    return cfg
```

### Target signature after D-07
```python
# Source: 13-CONTEXT.md D-07
def interactive_config() -> tuple[AppConfig, str]:
    ...
    return cfg, scan_profile   # scan_profile: "quick" | "standard" | "deep"
```

### Hardcoded TLS port list (D-03)
```python
# Source: 13-CONTEXT.md D-03
CONSULTING_TLS_PORTS = [
    443, 8443, 9443, 10443, 4433, 5001,   # original list
    636, 3269,                              # LDAPS
    993, 995, 465,                          # IMAPS, POP3S, SMTPS
    6443, 2376,                             # K8s API, Docker TLS
    5432, 3306, 1433,                       # PostgreSQL, MySQL, MSSQL
    8200,                                   # Vault
]
```

### Timezone auto-detect (D-01)
```python
# Source: 13-CONTEXT.md D-01 / verified on this host
import datetime
try:
    timezone = datetime.datetime.now().astimezone().tzname()
except Exception:
    timezone = "UTC"   # fallback (Claude's discretion)
```

### run_scan.py call site change (D-08)
```python
# Source: 13-CONTEXT.md D-08 / run_scan.py lines 179–198
# BEFORE
cfg = interactive_config()
apply_profile(cfg, args.profile, safe_mode=args.safe_mode)
...
if not used_config_file:
    ctx = prompt_for_context()
    attach_context(cfg, ctx)

# AFTER
cfg, scan_profile = interactive_config()
apply_profile(cfg, scan_profile, safe_mode=args.safe_mode)
# attach_context() already called inside interactive_config(); no separate call needed
```

### Connector credential warning (D-14)
```python
# Source: 13-CONTEXT.md D-14
enable_aws = _prompt_bool("Enable AWS connector", False)
if enable_aws:
    print(
        "  ⚠  Requires AWS credentials — set AWS_ACCESS_KEY_ID + "
        "AWS_SECRET_ACCESS_KEY, or configure an IAM role profile "
        "(aws_profile in config)."
    )

enable_azure = _prompt_bool("Enable Azure connector", False)
if enable_azure:
    print(
        "  ⚠  Requires Azure credentials — run az login, or set "
        "AZURE_CLIENT_ID + AZURE_CLIENT_SECRET + AZURE_TENANT_ID."
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `_prompt("Timezone", DEFAULT_TIMEZONE)` | `datetime.now().astimezone().tzname()` | Phase 13 | Consultant never sees a timezone prompt |
| `_prompt_bool("Use SNI for FQDN targets", True)` | Hardcoded `include_sni=True` | Phase 13 | No SNI prompt; correct for all FQDN targets |
| `_prompt_ports("TLS ports ...", [443, 8443, ...])` | Hardcoded `CONSULTING_TLS_PORTS` (17 ports) | Phase 13 | Extended enterprise coverage without confusion |
| `_prompt_int("Socket/TLS timeout seconds", 4, ...)` | Profile selection menu | Phase 13 | Consultant speaks profiles, not thread counts |
| `_prompt("Data classification ...", "confidential")` | Numbered 4-option menu → sets both fields | Phase 13 | Eliminates the separate `data_types` prompt in `prompt_for_context()` |
| `interactive_config() -> AppConfig` | `interactive_config() -> tuple[AppConfig, str]` | Phase 13 | Profile is surfaced to `apply_profile()` call site |

**Deprecated/outdated after Phase 13:**
- `_prompt_ports()` helper: still present but no longer called from `interactive_config()`. Delete in Phase 15.
- `prompt_for_context()` standalone call in `run_scan.py`: replaced by integrated context derivation inside `interactive_config()`.

---

## Open Questions

1. **Where do `data_longevity_years`, `exposure`, `crown_jewels` prompts live?**
   - What we know: D-12 says "remain as separate prompts in a consolidated Assessment Context section"; they must appear in the interactive flow.
   - What's unclear: Do they appear inside `interactive_config()` directly (recommended, Option B above) or stay in a refactored version of `prompt_for_context()`?
   - Recommendation: Move all three into `interactive_config()` under a `\n🧠 Assessment Context` section header. Build and `attach_context()` from inside `interactive_config()`. Remove the standalone `prompt_for_context()` call from `run_scan.py` entirely. `prompt_for_context()` itself can remain as dead code until Phase 15.

2. **`AssessmentCfg.timezone` field accepts the short tzname (e.g. "EDT") vs. IANA name (e.g. "America/New_York")?**
   - What we know: `AssessmentCfg.timezone: str` is unvalidated; the existing default was `"America/New_York"` (IANA format). `datetime.tzname()` returns the abbreviation ("EDT", "UTC", "PST").
   - What's unclear: Does any downstream consumer of `cfg.assessment.timezone` expect IANA format?
   - Recommendation: Search for `cfg.assessment.timezone` usage in report generation before implementing. If downstream uses it for display only, the short name is fine. If it feeds into `pytz.timezone()` or `zoneinfo.ZoneInfo()`, IANA format is required.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 13 is a pure Python source refactoring with no external dependencies beyond existing stdlib. All required modules (`datetime`, `input`) are built-in.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (currently collecting 205 tests) |
| Config file | none — pytest discovers tests/ automatically |
| Quick run command | `python3 -m pytest tests/test_interactive_mode.py -x -q` |
| Full suite command | `python3 -m pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTER-01 | `interactive_config()` auto-detects timezone; no input() call for timezone | unit | `pytest tests/test_interactive_mode.py::test_timezone_auto_detected -x` | ❌ Wave 0 |
| INTER-02 | `interactive_config()` does not prompt for SNI; returned config has `include_sni=True` | unit | `pytest tests/test_interactive_mode.py::test_no_sni_prompt -x` | ❌ Wave 0 |
| INTER-03 | `interactive_config()` does not prompt for windows_adcs; returned config has no such attribute | unit | `pytest tests/test_interactive_mode.py::test_no_adcs_prompt -x` | ❌ Wave 0 |
| INTER-04 | Connector section does not contain "(stub)" text in any print() call | unit | `pytest tests/test_interactive_mode.py::test_no_stub_labels -x` | ❌ Wave 0 |
| INTER-05 | Enabling JWT/container/source returns config with correct enable flags and targets | unit | `pytest tests/test_interactive_mode.py::test_scanner_enables -x` | ❌ Wave 0 |
| INTER-06 | Profile selection returns correct scan_profile string; tuple second element is "quick"/"standard"/"deep" | unit | `pytest tests/test_interactive_mode.py::test_profile_selection -x` | ❌ Wave 0 |
| INTER-07 | Returned config `ports_tls` contains all 17 consulting-grade ports including 636, 993, 6443, 8200 | unit | `pytest tests/test_interactive_mode.py::test_consulting_ports -x` | ❌ Wave 0 |
| INTER-08 | Prompt sequence order (verified via mock call-order inspection or source structure check) | unit | `pytest tests/test_interactive_mode.py::test_prompt_order -x` | ❌ Wave 0 |
| INTER-09 | Generated config dict (via `dataclasses.asdict`) has no `enable_windows_adcs` key | unit | `pytest tests/test_interactive_mode.py::test_no_adcs_in_config -x` | ❌ Wave 0 |
| INTER-10 | Single classification prompt produces both `data_classification` and correctly mapped `data_types` | unit | `pytest tests/test_interactive_mode.py::test_data_classification_unified -x` | ❌ Wave 0 |

### Test Implementation Strategy (Nyquist Pattern from Phase 12)
All INTER tests require mocking `input()` to supply scripted responses. The established project
pattern uses `unittest.mock.patch('builtins.input', side_effect=[...])`. Each test sets up a
side_effect list matching the exact prompt sequence and asserts the returned config fields.

Example scaffold:
```python
from unittest.mock import patch

def test_profile_selection():
    # Simulate: targets, profile=3 (deep), no scanners, no connectors, defaults for output/metadata
    inputs = [
        "",        # CIDRs (empty)
        "api.example.com",  # FQDNs
        "",        # include_ips
        "",        # exclude_ips
        "3",       # profile: deep
        # ... remaining prompts
    ]
    with patch('builtins.input', side_effect=inputs):
        cfg, profile = interactive_config()
    assert profile == "deep"
```

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_interactive_mode.py -x -q`
- **Per wave merge:** `python3 -m pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_interactive_mode.py` — covers INTER-01 through INTER-10 (all 10 requirements)
- [ ] No framework install needed (pytest already present, 205 tests collected)

---

## Project Constraints (from CLAUDE.md)

- Follow PEP 8 for all Python changes.
- Keep diffs minimal — avoid unnecessary refactors.
- After changes, run `python -m compileall` and relevant tests.
- No new library dependencies — this phase uses only Python stdlib and existing project imports.
- Interactive mode uses stdlib `input()` — no questionary/inquirer (established project pattern).

---

## Sources

### Primary (HIGH confidence)
- `quirk/interactive.py` — read directly; 168 lines, full current implementation
- `quirk/assessment/operator_context.py` — read directly; `OperatorContext` dataclass and `prompt_for_context()`
- `run_scan.py` lines 1–30, 170–200 — read directly; exact call site for tuple unpack change
- `quirk/engine/profiles.py` — read directly; `apply_profile()` accepts plain string "quick"/"standard"/"deep"
- `quirk/config.py` lines 1–137 — read directly; `AssessmentCfg`, `ScanCfg` field layout, `config_from_dict()` line 132
- `.planning/phases/13-interactive-mode-overhaul/13-CONTEXT.md` — read directly; all decisions locked
- `.planning/REQUIREMENTS.md` — read directly; INTER-01 through INTER-10 definitions

### Secondary (MEDIUM confidence)
- `tests/test_cli_correctness.py` — read directly; establishes Nyquist TDD RED scaffold pattern used by Phase 12; validates the `unittest.mock.patch('builtins.input', side_effect=[...])` approach is the project standard
- `.planning/STATE.md` — read directly; confirmed Phase 12 complete, Phase 13 not started

### Tertiary (LOW confidence)
- None — all claims sourced directly from project files.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all stdlib
- Architecture: HIGH — direct source inspection of all three affected files
- Pitfalls: HIGH — derived from dataclass definitions and call site analysis, not speculation
- Test patterns: HIGH — established by Phase 12 test_cli_correctness.py in same repo

**Research date:** 2026-04-06
**Valid until:** Stable — Phase 13 is pure refactoring with no moving external targets. Valid until implementation begins.
