# Codebase Concerns

**Analysis Date:** 2026-04-02

---

## 1. Dead Code — Files, Functions, and Modules That Are Never Reached

### 1.1 `quirk/connectors/` Directory — Entire Directory Is Dead Code

**Resolved:** `quirk/connectors/` directory deleted in Phase 91. [CLEAN-03 / BACK-49 resolved]

---

### 1.2 `quirk/engine/rules.py` — Reserved File with Zero Implementation

**Resolved:** `quirk/engine/rules.py` deleted. No imports reference it. [CLEAN-03 / BACK-49 resolved]

---

### 1.3 `quirk/engine/migration_planner.py` — Superseded but Still Called

**Resolved:** `quirk/engine/migration_planner.py` deleted. `categorize_waves()` inlined into `quirk/reports/writer.py` (Phase 83 CLEAN-01). [CLEAN-03 / BACK-51 resolved]

---

### 1.4 `quirk/reports/writer.py` — One Remaining Dead Function

**File:** `quirk/reports/writer.py`

**Resolved:** All five originally-listed dead functions removed. `_extract_cert_key_type()` deleted from `quirk/reports/writer.py` and `tests/test_cert_pubkey_fix.py` deleted in Plan 91-02 (BACK-50 / CLEAN-02). Unused `RichText` import also removed from writer.py:9. [CLEAN-02 resolved]

---

### 1.5 `quirk/intelligence/schema.py` — Dataclasses Never Instantiated in Production

**File:** `quirk/intelligence/schema.py`

**Status:** Superseded-by-D-15 (Plan 91-02, option-a decision). Deletion of the five schema dataclasses (ScoreInputs, ScoreResult, ConfidenceResult, RoadmapItem, IntelligenceReport) was listed in BACK-52/CLEAN-02 but is blocked by the Phase 77 D-15 CI gate (`tests/test_intelligence_public_api.py`), which explicitly asserts IntelligenceReport MUST remain exported from `quirk.intelligence` and MUST NOT be deleted. BACK-52's schema-deletion portion is intentionally not executed; the schema files and their tests are PRESERVED. The D-15 guardrail remains active.

---

### 1.6 `quirk/intelligence/driver_text.py` — Deleted

**Resolved:** `quirk/intelligence/driver_text.py` deleted in a prior phase. [CLEAN-03 / BACK-52 resolved]

---

### 1.7 `quirk/intelligence/calibration.py` — Deleted

**Resolved:** `quirk/intelligence/calibration.py` deleted in a prior phase. [CLEAN-03 / BACK-52 resolved]

---

### 1.8 `quirk/reports/scorecard.py` — Deleted

**Resolved:** `quirk/reports/scorecard.py` deleted in a prior phase (BACK-61 / Phase 83). [CLEAN-03 resolved]

---

## 2. Label/Intent Drift — Named One Way, Behaves Another

### 2.1 Interactive Mode Labels AWS/Azure as "stub" — But They Are Fully Implemented

**File:** `quirk/interactive.py`, lines 109–113

**Issue:**
```python
# Connectors (stubs for now)
print("\n🔌 Connectors (stubs in v2)")
enable_aws = _prompt_bool("Enable AWS connector (stub)", False)
enable_azure = _prompt_bool("Enable Azure connector (stub)", False)
enable_windows_adcs = _prompt_bool("Enable Windows AD CS connector (stub)", False)
```

AWS (`quirk/scanner/aws_connector.py`) and Azure (`quirk/scanner/azure_connector.py`) are fully implemented and reach live AWS/Azure APIs when enabled. Calling them "stubs" in the interactive prompt is incorrect and would confuse operators enabling them for real assessments. Windows AD CS is genuinely a stub (empty file), so only that label is accurate.

**Impact:** A user enabling AWS or Azure in interactive mode reads "stub" and may believe no real scan will occur.

---

### 2.2 `quirk/assessment/migration_advisor.py` — `"deprecated tls"` Pattern Matches Nothing

**File:** `quirk/assessment/migration_advisor.py`, line 24

**Issue:** `recommend_migration_paths()` contains:
```python
if "deprecated tls" in title:
```
The actual finding title produced by `quirk/engine/risk_engine.py` is `"Legacy TLS versions allowed (TLS 1.0/1.1)"`. The string `"deprecated tls"` never appears in any finding. This branch is never entered.

**Impact:** Migration recommendations for legacy TLS findings are never generated; they fall through to the default case.

---

### 2.3 `quirk/assessment/migration_advisor.py` — `"public key"` Pattern Matches Nothing

**File:** `quirk/assessment/migration_advisor.py`, line 46

**Issue:** `if "quantum" in title or "public key" in title` — the finding titled `"SSH quantum planning advisory"` would match `"quantum"`, but there is no finding with `"public key"` in its title produced by the risk engine. This appears to be a stale reference to an earlier finding taxonomy.

---

### 2.4 `quirk/reports/writer.py` — `INTELLIGENCE_VERSION = "4.0.0"` vs `IntelligenceCfg` Default of `"3.9.0"`

**Files:**
- `quirk/reports/writer.py`, line 25: `INTELLIGENCE_VERSION = "4.0.0"`
- `quirk/config.py`, line 73: `intelligence_version: str = "3.9.0"`
- `quirk/config.py`, line 123: `intelligence_version=str(intel_raw.get("intelligence_version", "3.9.0") ...)`

**Issue:** The hardcoded `INTELLIGENCE_VERSION` stamped into every output `intelligence-*.json` is `"4.0.0"`. The config dataclass default (used in config.yaml and interactive mode) writes `"3.9.0"` into `cfg.intelligence.intelligence_version`. These are independently sourced and will disagree. The value in the output JSON comes from the writer constant, not from config.

**Impact:** Version tracking in output artifacts is unreliable.

---

### 2.5 `quirk/cbom/builder.py` — `PLATFORM_VERSION = "3.9"` vs `quirk.__version__ = "4.0.0"`

**Files:**
- `quirk/cbom/builder.py`, line 76: `PLATFORM_VERSION = "3.9"`
- `quirk/__init__.py`, line 2: `__version__ = "4.0.0"`
- `quirk/reports/writer.py`, line 23: `PLATFORM_VERSION = "4.0"`

**Issue:** The CBOM root component version is stamped as `"3.9"` while the CLI version and report summary show `"4.0"`. Any CBOM-consuming toolchain will see an inconsistent tool version.

---

### 2.6 `quirk/reports/executive.py` — Section Header Still Reads `v3.7`

**File:** `quirk/reports/executive.py`, line 51

**Issue:** `lines.append("## Confidence & Coverage (v3.7)")` — the confidence engine is in `quirk/assessment/confidence.py` which itself is labelled `v3.7`. The tool is currently at v4.0. This version tag appears directly in generated executive summary markdown reports.

---

### 2.7 `quirk/reports/technical.py` — Section Header Still Reads `v3.6`

**File:** `quirk/reports/technical.py`, lines 46–49

**Issue:** `lines.append("## TLS Capabilities (v3.6)")` — version artifact from when the TLS capability enumerator was first added. Appears verbatim in generated technical findings reports.

---

## 3. Schema/Runtime Divergence — Config Fields That Are Defined But Never Applied

### 3.1 `ConnectorsCfg.enable_windows_adcs` — Stored, Prompted, Never Consumed

**Files:**
- `quirk/config.py`, line 47: `enable_windows_adcs: bool`
- `quirk/interactive.py`, line 113: prompted from user
- `run_scan.py`: no reference to `enable_windows_adcs` anywhere

**Issue:** `cfg.connectors.enable_windows_adcs` is stored and prompted for in interactive mode, but `run_scan.py` never checks it and takes no action on it. There is no scan phase for Windows AD CS. The user is asked a question whose answer is permanently ignored.

---

### 3.2 Interactive Mode Never Asks About Phase 3 Scanner Flags

**File:** `quirk/interactive.py` (entire module)

**Issue:** `ConnectorsCfg` has six fields that are only accessible via a config file, never via interactive mode:
- `enable_jwt` (default: `False`)
- `enable_container` (default: `False`)
- `enable_source` (default: `False`)
- `jwt_targets` (default: `[]`)
- `container_targets` (default: `[]`)
- `source_targets` (default: `[]`)

A user running interactive mode cannot enable JWT, container, or source scanning. These scanners are fully implemented and functional — they are simply unreachable from the interactive path.

---

### 3.3 Interactive Mode Never Asks About `tls_enum_mode`, Phase-Tuned Timeouts, or Intelligence Profile

**File:** `quirk/interactive.py` (entire module)

**Issue:** Multiple `ScanCfg` fields are set to dataclass defaults and never prompted:
- `tls_enum_mode` (default: `"fast"`) — controls TLS capability depth
- `fingerprint_timeout_seconds`, `fingerprint_concurrency`
- `tls_timeout_seconds`, `tls_concurrency`
- `ssh_timeout_seconds`, `ssh_concurrency`

And `IntelligenceCfg` is constructed with all defaults (`IntelligenceCfg()`) — the `profile` (lenient/balanced/strict) is never asked.

**Impact:** Interactive mode produces a reduced config. The only path to controlling these is a config file, but the `quirk init` command generates `quirk/config_template.yaml` (the bundled template), not the working `config.yaml`, and the bundled template has different field names (see §3.4).

---

### 3.4 `quirk/config_template.yaml` — Multiple Field Names Incompatible with Config Dataclasses

**File:** `quirk/config_template.yaml`

**Issue:** The template generated by `quirk init` uses field names that do not exist in the config dataclasses and will cause `KeyError` or be silently ignored:

| Template field | Actual dataclass field |
|---|---|
| `scan.ports_ssh` | Does not exist — SSH ports are discovered via fingerprinting, not configured |
| `scan.timeout` | Should be `scan.timeout_seconds` |
| `scan.max_workers` | Should be `scan.concurrency` |
| `targets.ips` | Should be `targets.include_ips` |
| `connectors.aws.enabled` (nested) | Should be `connectors.enable_aws` (flat) |
| `connectors.azure.enabled` (nested) | Should be `connectors.enable_azure` (flat) |
| `connectors.azure.key_vault_names` | Should be `connectors.azure_keyvault_urls` |
| `connectors.jwt_endpoints` | Should be `connectors.jwt_targets` |

**Impact:** A user who runs `quirk init`, edits the generated template, and attempts to run with `quirk --config config.yaml` will get a runtime `TypeError` from `ScanCfg(**raw["scan"])` because `timeout` and `max_workers` are not valid constructor arguments. The template is broken for its intended purpose. The working `config.yaml` in the repository root uses the correct field names and serves as the actual operational example.

---

### 3.5 `quirk/validate.py` — Expects Artifacts That `write_reports()` Never Produces

**File:** `quirk/validate.py`, lines 143–151

**Issue:** `validate_run()` checks for these files by stamp:
- `assessment-{stamp}.json`
- `calibration-{stamp}.json`
- `delta-{stamp}.json` (if baseline exists)

`quirk/reports/writer.py` produces none of these. It produces: `findings-*.json`, `executive-summary-*.md`, `technical-findings-*.md`, `scorecard-*.md`, `roadmap-*.md`, `intelligence-*.json`, `run-stats-*.json`, `report-*.html`, `report-*.pdf`, `cbom-*.cdx.json`, `cbom-*.cdx.xml`.

`validate_run()` will always report errors for `assessment-*.json` and `calibration-*.json` missing, and will error on delta if a previous intelligence file exists. The validator structurally cannot pass on any real scan output.

**Impact:** `python -m quirk.validate --output-dir output` is permanently broken as a QA gate. Every real scan run will fail validation.

---

## 4. Duplicate/Parallel Implementations

### 4.1 Two Parallel Scoring Systems — Resolved

**Resolved:** `quirk/assessment/readiness_score.py`, `quirk/assessment/confidence.py`,
`quirk/assessment/transition_planner.py` were all deleted in prior phases. The codebase
now has a single scoring engine: `quirk/intelligence/scoring.py`. Both
`quirk/reports/executive.py` and `quirk/reports/writer.py` import
`compute_readiness_score` from `quirk.intelligence.scoring`. [CLEAN-03 / BACK-52 resolved]

---

### 4.2 Two Confidence Engines — Resolved

**Resolved:** `quirk/assessment/confidence.py` deleted. Single engine: `quirk/intelligence/confidence.py`. [CLEAN-03 resolved]

---

### 4.3 Two Roadmap Builders — Resolved

**Resolved:** `quirk/assessment/transition_planner.py` deleted. Single builder: `quirk/intelligence/roadmap.py`. [CLEAN-03 resolved]

---

### 4.4 Two Interpretation Engines — Resolved

**Resolved:** `quirk/reports/scorecard.py` deleted (see §1.8). `quirk/assessment/interpretation_engine.py` is the only remaining interpretation helper. [CLEAN-03 resolved]

---

## 5. Interactive Mode vs Config File Inconsistencies

### 5.1 Scan Subcommand Does Not Exist

**Files:**
- `quirk/config_template.yaml`, line 7: `quirk scan --config config.yaml`
- `quirk/cli/init_cmd.py`, line 45: `_info(f"  [dim]quirk scan --config {output_path}[/dim]")`
- `docs/getting-started.md`, line 52: `quirk scan --config config.yaml`

**Issue:** `run_scan.py:main()` handles only `init` and `serve` as named subcommands. There is no `scan` subcommand. The correct invocation is `quirk --config config.yaml`. The template, the init command's help text, and the getting-started doc all tell users to run `quirk scan --config config.yaml`, which will fail with argparse error.

---

### 5.2 Interactive Mode Has No `aws_region`, `aws_profile`, `azure_subscription_id`, or `azure_keyvault_urls` Prompts

**File:** `quirk/interactive.py`

**Issue:** When a user enables AWS in interactive mode, `ConnectorsCfg` is constructed with `aws_region="us-east-1"` (hardcoded default) and `aws_profile=None`. There is no prompt to set region or profile. Similarly, Azure is enabled without prompting for `azure_subscription_id` or `azure_keyvault_urls`. Both connectors will fail silently or scan wrong regions without the user being aware.

---

## 6. Legacy Naming Artifacts

### 6.1 `data/qcscan-legacy.sqlite` — Deleted

**Resolved:** `data/qcscan-legacy.sqlite` removed (commit 708402b). [CLEAN-03 / BACK-53 resolved]

---

### 6.2 `tqdm = None` Dead Assignment in `run_scan.py` — Removed

**Resolved:** The `tqdm = None; if tqdm:` dead branch was removed from `run_scan.py` pre-v4.10. `quirk/logging_util.py` uses a live lazy import of `tqdm` for the `--progress` flag — this is not dead code. `tqdm>=4.67` is a legitimate production dependency. [CLEAN-03 / BACK-54 resolved]

---

### 6.3 Internal D-Reference Comments Scattered Throughout Source

**Files:** Multiple (see list in §6.3 detail)

**Issue:** Source code contains internal ticket references (`D-04`, `D-05`, `D-06`, `D-07`, `D-08`, `D-11`, `D-15`, `D-16`, `D-17`, `D-18`) and historical version comments (`v3.5`, `v3.6`, `v3.7`, `v3.7.1`, `v3.7.3`, `v3.9`) that appear in generated output and in code comments. These are development artifact comments that have no meaning to an external reader or consumer of the CBOM/reports. Examples:
- `quirk/config.py:48` — `# Phase 3 scanner enable flags (per D-04)`
- `quirk/models.py:40` — `# v3.6 TLS capability fields`
- `quirk/scanner/ssh_scanner.py:43` — `cipher_suite="SSH",  # D-06: SSH marker field`
- `quirk/reports/technical.py:49` — `lines.append("## TLS Capabilities (v3.6)")` — version tag appears in generated reports

---

### 6.4 `datetime.utcnow()` Deprecation Warnings — Resolved

**Resolved:** All `datetime.utcnow()` calls in `quirk/` production code were fixed in earlier phases. The 9 remaining occurrences in `tests/test_dashboard_scan_history.py` were fixed in Phase 91 Plan 01 (CLEAN-01 / BACK-56). [CLEAN-01 resolved]

---

## 7. Connector/Scanner Truth Table

| Scanner | Implementation | Callable via Interactive Mode | Callable via Config File | Notes |
|---|---|---|---|---|
| **TLS** | Fully implemented | Yes (targets only) | Yes | sslyze primary, ssl stdlib fallback |
| **SSH** | Fully implemented | Yes (targets only) | Yes | ssh-audit primary, banner fallback |
| **JWT/JWKS** | Fully implemented | **No** | Yes | Requires `enable_jwt: true` + `jwt_targets` in config |
| **Container (syft)** | Fully implemented | **No** | Yes | Requires `enable_container: true` + `container_targets` in config |
| **Source (semgrep)** | Fully implemented | **No** | Yes | Requires `enable_source: true` + `source_targets` in config |
| **AWS** | Fully implemented | Yes (but labelled "stub") | Yes | Label drift: called "stub" in prompt but fully functional |
| **Azure** | Fully implemented | Yes (but labelled "stub") | Yes | Label drift: called "stub" in prompt but fully functional |
| **Windows AD CS** | True stub (empty file) | Yes (prompted, ignored) | Yes (field exists, never consumed) | Config field accepted, engine ignores it entirely |

**Summary of unreachable-from-interactive scanners:** JWT, Container, Source. All three are fully implemented but have no interactive mode prompts and no `quirk init` template fields that would expose them correctly.

---

## 8. Security Considerations

### 8.1 JWT Scanner TLS Verification — Documented (CLEAN-04)

**Resolved:** Phase 57 (HARDEN-SCAN-01) refactored `jwt_scanner.py` to use `verify=verify_tls`
(not a hardcoded `verify=False`). `allow_insecure_jwks` defaults to `false`; when enabled, a
HIGH advisory `ADVISORY_JWKS_VERIFY_DISABLED` finding is emitted and `validate_external_url()`
still runs on JWKS URIs. Phase 91 Plan 01 (CLEAN-04) added inline `# WHY:` comments at the
`httpx.get` call sites and documented `allow_insecure_jwks` in `docs/operators-guide.md` and
`docs/configuration.md`. [CLEAN-04 / BACK-58 resolved]

---

### 8.2 Credentials Never Stored — But No Validation of Ambient Auth Scope

**Files:** `quirk/scanner/aws_connector.py`, `quirk/scanner/azure_connector.py`

**Issue:** Both connectors use ambient credential resolution (boto3 session, DefaultAzureCredential). No validation of minimum required permissions is performed before enumerating ACM, KMS, CloudFront, ELBv2, or Key Vault resources. If the ambient credentials have broad write permissions (e.g. an overpowered dev profile), QUIRK will silently operate with excessive privilege. No principle-of-least-privilege guidance is documented in the connector stubs or prompts.

---

### 8.3 `quirk init` Template Contains Placeholder Documentation URL

**File:** `quirk/config_template.yaml`, line 4

**Issue:**
```yaml
# Documentation: https://github.com/[owner]/quirk/blob/main/docs/configuration.md
```
The `[owner]` placeholder was never substituted. This URL is non-functional and will appear in any config file generated by `quirk init`.

---

## 9. Performance Concerns

### 9.1 `config_template.yaml` Default Port List Includes Port 22 as a TLS Port

**File:** `docs/sample-config.yaml`, line 10: `ports_tls: [22, 443, 8443]`

**Issue:** Port 22 (SSH) is listed in `ports_tls` in the sample config. `expand_targets()` creates `(host, 22)` pairs that go through the TLS fingerprinting path. The fingerprinter will try a TLS handshake on port 22 (which will fail), then an HTTP probe (which will also fail), before classifying the connection as UNKNOWN or falling through. The SSH fingerprinter is never tried because port 22 is only routed to SSH scanning if the fingerprinter detects the SSH banner — which does happen — but the wasted TLS/HTTP probe attempts add latency for every host at scale.

---

### 9.2 TLS Capability Enumeration Runs Multiple Handshakes Per Host Per Scan

**File:** `quirk/scanner/tls_capabilities.py`

**Issue:** For each TLS target in `fast` mode, `enumerate_tls_capabilities()` attempts up to 10 TLS handshakes (4 version probes + 6 modern cipher probes). In `deep` mode this is 14+ handshakes. For large scans (hundreds of TLS endpoints) at high concurrency, this multiplies network traffic significantly. There is no shared-connection optimization. Each handshake creates a new `socket.create_connection()`.

---

## 10. Fragile Areas

### 10.1 `quirk/config.py` — `config_from_dict()` Uses `**raw["scan"]` Without Field Validation

**File:** `quirk/config.py`, line 130

**Issue:**
```python
scan=ScanCfg(**raw["scan"]),
```
If the YAML contains an unexpected key in the `scan` section (e.g. from the broken template: `timeout`, `max_workers`, `ports_ssh`), this raises `TypeError: __init__() got an unexpected keyword argument 'timeout'` at startup. There is no try/except around any of the dataclass constructors. A single malformed YAML key will crash the tool before the first scan target is processed.

**Impact:** HIGH for users using the `quirk init` generated template without manual fixup.

---

### 10.2 `run_scan.py` Mutates `cfg.scan` In-Place During Scan Phases

**File:** `run_scan.py`, lines 367–410

**Issue:**
```python
cfg.scan.timeout_seconds = tls_timeout
cfg.scan.concurrency = tls_conc
# ... scan ...
cfg.scan.timeout_seconds = base_timeout
cfg.scan.concurrency = base_conc
```
The shared config object is mutated and restored around each scan phase. If an exception occurs during TLS scanning, the restore lines at lines 385–386 are not reached, leaving `cfg.scan` with TLS-phase values for the remainder of the run (SSH scan, JWT scan, etc.). There is no `try/finally` guard.

---

### 10.3 `quirk/validate.py` — `_latest_intelligence()` Sorts Filenames Lexicographically

**File:** `quirk/validate.py`, lines 43–48

**Issue:** Files are sorted by name in reverse lexicographic order. The filename pattern `intelligence-YYYYMMDD-HHMMSS.json` sorts correctly because the timestamp format is zero-padded. However, if two scans run within the same second (common in testing), the sort order is undefined for equal timestamps.

---

## 11. Test Coverage Gaps

### 11.1 `run_scan.py` Has No Tests

**Issue:** The main entry point `run_scan.py` — which wires together discovery, fingerprinting, TLS, SSH, JWT, container, source, AWS, Azure, reporting, and CBOM — has no direct tests. All integration is covered by individual module tests. The cfg mutation pattern (§10.2), interactive mode behavior, and the subcommand dispatch (init/serve vs scan) are untested.

---

### 11.2 `quirk/validate.py` Has No Tests

**Issue:** The validation module is untested. Its divergence from the actual output artifact set (§3.5) would be caught immediately by a test that runs a scan and then validates the output.

---

### 11.3 Interactive Mode Has No Tests

**File:** `quirk/interactive.py`

**Issue:** `interactive_config()` is not tested. The missing Phase 3 scanner prompts (§3.2), the stub labels (§2.1), and the missing AWS region/profile prompts (§5.2) have no test coverage.

---

## 12. Missing Critical Features (Configuration-Visible but Inoperative)

### 12.1 `intelligence.calibration_overrides` Field Is Loaded but Never Applied to Scoring

**File:** `quirk/config.py`, line 80: `calibration_overrides: Optional[Dict[str, Any]] = None`

**Issue:** A user can set per-weight overrides in config.yaml under `intelligence.calibration_overrides`. `config_from_dict()` loads these into `cfg.intelligence.calibration_overrides`. However, `quirk/intelligence/scoring.py:compute_readiness_score()` accepts a `weights` parameter that allows override — but neither `run_scan.py` nor `quirk/reports/writer.py` passes `cfg.intelligence.calibration_overrides` as the `weights` argument. The overrides are stored and then discarded.

---

*Concerns audit: 2026-04-02*
