---
phase: 52-compliance-uplift-health-check
verified: 2026-05-06T00:00:00Z
status: passed
score: 6/7 must-haves verified
overrides_applied: 1
overrides:
  - must_have: "COMPLY-10: CBOM Pass-1 algorithm components carry a 3-tier FIPS 140-3 status annotation (certified / approved / non-approved)"
    reason: "Phase 52 CONTEXT.md D-01 explicitly scopes 'certified' tier to a future CMVP attestation phase. Implementation ships 2-tier (approved / non-approved). The plan must_haves, acceptance criteria, and automated tests are all written around the 2-tier contract. The REQUIREMENTS.md text predates the D-01 scope decision. This deviation is intentional and documented."
    accepted_by: "user"
    accepted_at: "2026-05-06"
gaps: []
human_verification:
  - test: "quirk doctor end-to-end render"
    expected: "Running `python run_scan.py doctor` (or `quirk doctor`) from the project root prints a Rich-formatted table with 10 rows (Python env, 3 binary checks, compliance freshness, QRAMM module, database, configuration, network connectivity, dashboard process). Exit code is 0 if all non-informational checks pass, 1 if any fail (e.g., semgrep not in PATH)."
    why_human: "Terminal Rich rendering cannot be verified by grep. Exit code depends on local system state (binaries installed, quirk.db present). Automated tests use mocks."
  - test: "PROFILE_ARGS CLI override in lab.sh"
    expected: "`cd quantum-chaos-enterprise-lab && PROFILE_ARGS=\"--profile tls\" ./lab.sh status` reports tls-profile services regardless of any PROFILE_ARGS value in .env."
    why_human: "Requires a running or accessible Docker Compose environment. The bash syntax check passes but runtime behavior with a real .env can only be confirmed by a human with the lab running."
---

# Phase 52: Compliance Uplift & Health Check Verification Report

**Phase Goal:** Compliance uplift (FIPS 140-3 CBOM annotation, SOC2 + ISO 27001:2022 mapping), health-check CLI (`quirk doctor`), and three v4.6 tech-debt closures — all verified by automated tests and documented for operators.
**Verified:** 2026-05-06
**Status:** passed (human verification approved 2026-05-06)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every CBOM algorithm component carries a `quirk:fips140-3-status` property with value `approved` or `non-approved` | VERIFIED | `quirk/cbom/builder.py:274` — `def _fips_status`; `line 311` — `properties=[Property(name="quirk:fips140-3-status", value=_fips_status(nist_level))]`; both `test_fips_status_helper` and `test_algorithm_component_has_fips_property` pass |
| 2 | SOC2 CC6.x controls (>= 3) are mapped in COMPLIANCE_MAP via `_soc2()` helper | VERIFIED | `quirk/compliance/__init__.py:74-83` — `def _soc2`; 26 SOC2 CC6.x entries confirmed programmatically; `test_soc2_entries_present` passes |
| 3 | ISO 27001:2022 controls (>= 3, 8.x numbering, no A.x.x) are mapped via `_iso()` helper | VERIFIED | `quirk/compliance/__init__.py:85-93` — `def _iso`; 24 ISO 27001:2022 entries, zero A.x.x IDs; `test_iso_entries_present`, `test_iso_rejects_legacy_control_ids`, `test_iso_version_string_exact` all pass |
| 4 | `quirk doctor` runs end-to-end: 8-category Rich health table, exit 0 on all-pass, exit 1 on non-informational failure, informational checks never trigger exit 1 | VERIFIED (automated) / UNCERTAIN (UX) | `quirk/cli/doctor_cmd.py` — 172 lines, `run_doctor()` implements all 8 categories; `run_scan.py:247-250` — doctor intercept wired; all 3 doctor tests pass; end-to-end Rich render requires human verification |
| 5 | PROFILE_ARGS CLI override wins over .env in lab.sh (DEBT-02) | VERIFIED (syntax) / UNCERTAIN (runtime) | `lab.sh:4` — `_PROFILE_ARGS_OVERRIDE="${PROFILE_ARGS:-}"` before `.env` source; `lab.sh:16` — `PROFILE_ARGS="${_PROFILE_ARGS_OVERRIDE:-${PROFILE_ARGS:-}}"` applies CLI wins pattern; `bash -n` syntax passes; runtime behavior with live .env requires human verification |
| 6 | `run-stats-*.json` contains `ports_scanned` and `hosts_scanned` (DEBT-03) | VERIFIED | `run_scan.py:540-541` — both fields present under `run_stats["counts"]`; `test_run_stats_ports_and_hosts_scanned` passes (accepts top-level OR nested under `counts`) |
| 7 | `saml_scanner.py` uses raw `lxml.etree` with `resolve_entities=False, no_network=True`; all SAML tests pass (DEBT-04) | VERIFIED | `quirk/scanner/saml_scanner.py:1-24` — `defusedxml.lxml` removed, `ET.XMLParser(resolve_entities=False, no_network=True)` in place; 26 tests pass + 1 integration deselected; no DeprecationWarning |

**Score:** 6/7 truths verified (7th has automated component verified; UX portion needs human)

### COMPLY-10 Scope Note

REQUIREMENTS.md defines COMPLY-10 as a 3-tier annotation (`certified` / `approved` / `non-approved`). The implementation delivers 2 tiers only. This is an intentional scope decision documented in Phase 52 CONTEXT.md D-01: the `certified` tier requires CMVP attestation support not available in v4.7. All plan must_haves, acceptance criteria, and tests are written around the 2-tier contract. An override entry is included in the frontmatter pending human acceptance.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/cbom/builder.py` | `_fips_status` helper + Property annotation | VERIFIED | Line 274: `def _fips_status`; line 311: properties kwarg; `from cyclonedx.model import Property` at line 19 |
| `quirk/compliance/__init__.py` | `_soc2`, `_iso`, constants, COMPLIANCE_MAP entries | VERIFIED | Lines 74-93: both helpers; lines 38-41: Phase 52 constants; 26 SOC2 + 24 ISO entries |
| `quirk/cli/doctor_cmd.py` | `run_doctor()` with 8-category health check | VERIFIED | 172 lines; all categories implemented; Rich table; exits 0 or 1 |
| `run_scan.py` | doctor subcommand intercept | VERIFIED | Lines 246-250: intercept before main argparse; `run_doctor()` called; `return` statement present |
| `quantum-chaos-enterprise-lab/lab.sh` | PROFILE_ARGS snapshot before .env | VERIFIED | Lines 4 and 16: snapshot + fallback chain |
| `quirk/scanner/saml_scanner.py` | lxml.etree with security flags; no defusedxml.lxml | VERIFIED | Lines 5-13: raw lxml parser; no defusedxml.lxml anywhere in file |
| `tests/test_cbom_builder.py` | FIPS test stubs present and passing | VERIFIED | Lines 528-560: two test functions; both GREEN |
| `tests/test_compliance_schema.py` | SOC2/ISO test stubs present and passing | VERIFIED | Lines 72-127: four test functions; all 8 schema tests GREEN |
| `tests/test_doctor_cmd.py` | 3 doctor test functions | VERIFIED | Lines 8-49: three functions; all GREEN |
| `tests/test_writer.py` | run_stats ports/hosts test | VERIFIED | Present and GREEN |
| `docs/operators-guide.md` | `### quirk doctor` section | VERIFIED | Line 258: section present with 8-category table, symbols, and Rich example |
| `docs/configuration.md` | SOC2 + ISO + FIPS 140-3 status property documentation | VERIFIED | Lines 484-496: Compliance Frameworks section with all required content |
| `docs/UAT-SERIES.md` | 6 Phase 52 UAT test cases | VERIFIED | UAT-COMPLY-52-01/02, UAT-DOCS-52-03, UAT-DEBT-52-04/05/06 all present |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-52-Compliance-Uplift-Health-Check.md` | Obsidian phase note, status: complete | VERIFIED | File exists; frontmatter: `status: complete`, `type: phase`, `project: QU.I.R.K.`; all 7 req IDs present |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` | Vault UAT sync with frontmatter | VERIFIED | File exists; `source: docs/UAT-SERIES.md` frontmatter present; `quirk doctor` content included |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_cbom_builder.py` | `quirk/cbom/builder.py` | `from quirk.cbom.builder import _fips_status` | WIRED | Import confirmed; test passes |
| `tests/test_doctor_cmd.py` | `quirk/cli/doctor_cmd.py` | `from quirk.cli.doctor_cmd import run_doctor` | WIRED | Import confirmed; all 3 tests pass |
| `quirk/cbom/builder.py` | `cyclonedx.model.Property` | `from cyclonedx.model import Property` at line 19 | WIRED | Import present; `properties=[Property(...)]` at line 311 |
| `quirk/cbom/builder.py` | `quirk/cbom/classifier.py` | `_fips_status(nist_level)` where `nist_level` from `classify_algorithm()` | WIRED | `nist_level` unpacked from classifier at line 290; passed to `_fips_status` at line 311 |
| `quirk/cli/doctor_cmd.py` | `quirk/compliance` | `from quirk.compliance import COMPLIANCE_MAP, STALENESS_THRESHOLD_DAYS` | WIRED | Import in `_check_compliance_freshness()` at line 43; used in freshness gate |
| `run_scan.py` | `quirk/cli/doctor_cmd.py` | `from quirk.cli.doctor_cmd import run_doctor` | WIRED | Lines 247-250: lazy import + call inside doctor intercept |
| `quirk/compliance/__init__.py` | COMPLIANCE_MAP entries | Each list extended with `_soc2(...)` and `_iso(...)` calls | WIRED | 26 SOC2 + 24 ISO calls; zero A.x.x IDs; parity verified programmatically |
| `quirk/scanner/saml_scanner.py` | `lxml.etree` | `ET.XMLParser(resolve_entities=False, no_network=True)` | WIRED | Lines 9-11: parser constructed with both security flags |
| `docs/operators-guide.md` | `quirk/cli/doctor_cmd.py` | documented `quirk doctor` usage | WIRED | Section present at line 258; 8 categories, exit codes, symbols documented |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `quirk/cbom/builder.py` `_make_algorithm_component()` | `nist_level` → `_fips_status()` → `Property.value` | `classify_algorithm(name)` in `quirk/cbom/classifier.py` — hardcoded `_ALGORITHM_TABLE` | Yes — real classifier lookup, not hardcoded stub | FLOWING |
| `quirk/compliance/__init__.py` COMPLIANCE_MAP | `_soc2("CC6.x")`, `_iso("8.x")` | Helper functions using module-level constants | Yes — functions return real dicts with all 5 required keys | FLOWING |
| `quirk/cli/doctor_cmd.py` `run_doctor()` | `failed` flag, table rows | `shutil.which`, `sqlite3.connect`, `socket.create_connection`, `COMPLIANCE_MAP`, `sys.version_info` | Yes — real system probes; not mocked in production path | FLOWING |
| `run_scan.py` run_stats | `ports_scanned`, `hosts_scanned` | Scan target set `{h for h, _ in targets}` / `{p for _, p in targets}` at lines 540-541 | Yes — derived from actual scan targets, not empty literals | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `_fips_status` maps nist_level correctly | `python3 -c "from quirk.cbom.builder import _fips_status; print(_fips_status(1), _fips_status(3), _fips_status(0), _fips_status(None))"` | `approved approved non-approved non-approved` | PASS |
| COMPLIANCE_MAP has >= 3 SOC2 CC6.x entries | Programmatic count | 26 SOC2 CC6.x entries, 24 ISO 27001:2022 entries, 0 A.x.x legacy IDs | PASS |
| `saml_scanner.py` has no defusedxml.lxml reference | `grep -c "defusedxml.lxml" quirk/scanner/saml_scanner.py` | 0 | PASS |
| SAML tests pass without DeprecationWarning | `pytest tests/test_saml_scanner.py -q` | 26 passed, 1 deselected | PASS |
| Doctor cmd imports cleanly | `python3 -c "from quirk.cli.doctor_cmd import run_doctor; print('OK')"` | OK | PASS |
| lab.sh bash syntax valid | `bash -n quantum-chaos-enterprise-lab/lab.sh` | exits 0 | PASS |
| All Phase 52 tests pass | `pytest tests/test_cbom_builder.py tests/test_compliance_schema.py tests/test_doctor_cmd.py tests/test_writer.py tests/test_saml_scanner.py -q` | 70 passed, 1 deselected | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| COMPLY-10 | 52-02 | CBOM algorithm components carry FIPS 140-3 status annotation | VERIFIED (2-tier; see scope note) | `_fips_status` helper + `properties=[Property(...)]` in `_make_algorithm_component`; 2 tests pass |
| COMPLY-11 | 52-03 | SOC2 CC6.x controls mapped via `_soc2()` helper | VERIFIED | `def _soc2` present; 26 CC6.x entries; `test_soc2_entries_present` passes |
| COMPLY-12 | 52-03 | ISO 27001:2022 controls mapped via `_iso()` helper; 8.x clause only; rejects A.x.x | VERIFIED | `def _iso` present; 24 ISO entries; all 3 ISO tests pass; zero A.x.x IDs |
| DOCS-05 | 52-04 | `quirk doctor` CLI with 8 categories, Rich output, exits 0/1 | VERIFIED (automated) / needs human (UX) | `doctor_cmd.py` 172 lines; `run_scan.py` intercept; all 3 doctor tests pass; UX needs human |
| DEBT-02 | 52-05 | lab.sh PROFILE_ARGS CLI precedence fixed | VERIFIED (syntax) / needs human (runtime) | `_PROFILE_ARGS_OVERRIDE` snapshot pattern; bash -n passes |
| DEBT-03 | 52-05 | run-stats-*.json includes ports_scanned + hosts_scanned | VERIFIED | `run_scan.py:540-541`; writer test passes |
| DEBT-04 | 52-05 | saml_scanner.py migrated from defusedxml.lxml to raw lxml.etree | VERIFIED | Zero defusedxml.lxml references; security flags present; 26 SAML tests pass |

No orphaned requirements: all 7 requirements declared across plans (COMPLY-10, COMPLY-11, COMPLY-12, DOCS-05, DEBT-02, DEBT-03, DEBT-04) are accounted for and implemented.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `quirk/cli/doctor_cmd.py` | 62-69 | `_check_qramm_present()` checks module presence but REQUIREMENTS.md DOCS-05 says "QRAMM framework freshness" | Info | DOCS-05 in REQUIREMENTS.md names category 4 "QRAMM framework freshness"; the implementation checks only module presence (not a staleness gate). CONTEXT.md D-11 explicitly authorizes this as "graceful skip" since Phase 51 QRAMM module may not be installed. This is a documented scope reduction, not a code smell. |
| `tests/test_saml_scanner.py` | 367 | `@pytest.mark.integration` not registered in pytest config | Info | Causes PytestUnknownMarkWarning; pre-existing issue not introduced by Phase 52 |
| Multiple pre-existing tests | — | `test_azure_blob`, `test_gcs_reuse`, `test_k8s_connector`, `test_pdf_export`, `test_tls_scanner_chain_verified` — 10 pre-existing failures | Info | None of these failures are in Phase 52 code paths. Last changes to these files predate Phase 52 commits. Not a Phase 52 regression. |

### Human Verification Required

#### 1. quirk doctor Rich Table Render

**Test:** From the project root, run `python run_scan.py doctor` (or `quirk doctor` if installed).
**Expected:** A Rich-formatted table titled "QU.I.R.K. Health Check" appears with 10 rows (Python environment, Binary: nmap, Binary: syft, Binary: semgrep, Compliance freshness, QRAMM module, Database (quirk.db), Configuration, Network connectivity, Dashboard process). Exit code is 0 if all non-informational checks pass, or 1 if any fail (e.g., semgrep not in PATH is a common failure on dev machines). Each row shows `[✓]`, `[!]`, or `[✗]` with a descriptive status string.
**Why human:** Rich terminal rendering cannot be verified by grep. Exit code depends on local system state (which binaries are installed, whether `./quirk.db` exists, whether `./config.yaml` is present). Automated tests use mocks for all system probes.

#### 2. lab.sh PROFILE_ARGS CLI Override Runtime Behavior

**Test:** In the `quantum-chaos-enterprise-lab/` directory (with or without a `.env` file present), run: `PROFILE_ARGS="--profile tls" ./lab.sh status`.
**Expected:** The command uses the tls profile as the active profile, overriding any `PROFILE_ARGS` value in `.env`. If no `.env` exists, the tls profile is used regardless.
**Why human:** The bash syntax check passes (`bash -n` exits 0). The snapshot-before-source pattern is code-verified. But confirming that a real `.env` with a different `PROFILE_ARGS` value is correctly overridden requires a live shell environment with actual `.env` file state.

### Gaps Summary

No blocker gaps found. All 7 required must-have truths have evidence in the codebase. The two human verification items are UX-level confirmations (Rich rendering, bash runtime behavior) that automated checks cannot substitute for. Two items require human sign-off before this verification fully closes:

1. The COMPLY-10 scope deviation (2-tier vs. 3-tier FIPS annotation) needs an `accepted_by` + `accepted_at` value in the frontmatter override entry above.
2. Human verification items 1 and 2 need manual sign-off.

Once those are complete, status upgrades to `passed`.

---

_Verified: 2026-05-06_
_Verifier: Claude (gsd-verifier)_
