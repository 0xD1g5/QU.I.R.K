# Phase 52: Compliance Uplift & Health Check - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Four parallel tracks, all fully independent of Phase 51 (zero shared code paths):

1. **CBOM FIPS 140-3 annotations (COMPLY-10)** — Every Pass-1 algorithm component in the CBOM gains a `quirk:fips140-3-status` property (`approved` / `non-approved`) derived from the existing `nist_level` classifier output. The `certified` tier is reserved for a future phase with CMVP attestation support.

2. **SOC2 CC6.x + ISO 27001:2022 extensions (COMPLY-11/12)** — Two new framework helpers `_soc2()` and `_iso()` join the existing `_pci()/_hipaa()/_fips()` pattern in `quirk/compliance/__init__.py`. Full parity coverage: every finding category that currently has PCI or HIPAA entries gets SOC2 and ISO mappings.

3. **`quirk doctor` CLI (DOCS-05)** — New `quirk doctor` subcommand following the existing subcommand-intercept pattern in `run_scan.py:main()`. Rich-formatted health dashboard across 8 categories; exits 1 on any non-informational failure.

4. **Three tech debt closures (DEBT-02/03/04)** — lab.sh PROFILE_ARGS precedence fix, run-stats.json `ports_scanned`+`hosts_scanned` fields, saml_scanner.py migration from deprecated `defusedxml.lxml` to raw `lxml.etree`.

**In scope:**
- `quirk/cbom/builder.py` — `_make_algorithm_component()` gains `quirk:fips140-3-status` property via CycloneDX `Component.properties`
- `quirk/compliance/__init__.py` — `_soc2()` helper (CC6.6/CC6.7 controls) + `_iso()` helper (8.24/8.26/8.28 controls); all existing COMPLIANCE_MAP keys extended
- `run_scan.py:main()` — `if sys.argv[1] == "doctor"` intercept block; implementation in `quirk/cli/doctor_cmd.py`
- `quantum-chaos-enterprise-lab/lab.sh` — snapshot PROFILE_ARGS before `source .env`
- `quirk/reports/writer.py` — add `ports_scanned` + `hosts_scanned` to run-stats JSON
- `quirk/scanner/saml_scanner.py` — replace `defusedxml.lxml` with raw `lxml.etree` (resolve_entities=False, no_network=True)

**Out of scope:**
- CBOM `certified` tier — reserved for future CMVP attestation phase
- `quirk doctor --format json` — not needed; exit code is the machine-readable signal
- New finding categories for email/broker/identity/DAR — SOC2/ISO mappings on existing finding titles only
- Dashboard UI for compliance view — deferred BACK-72, covered by Phase 55

</domain>

<decisions>
## Implementation Decisions

### FIPS 140-3 Annotation (COMPLY-10)

- **D-01 — `certified` tier never emitted in v4.7.** All algorithm components receive either `approved` or `non-approved`. The `certified` tier is reserved for a future phase when QUIRK can ingest explicit CMVP module attestation (e.g., operator config flag or attestation file). This is honest about the current data model — QUIRK knows algorithm names, not CMVP module IDs.

- **D-02 — `approved`/`non-approved` derived from `nist_level`.** Mapping: `nist_level >= 1` → `approved`; `nist_level == 0` → `non-approved`; `nist_level == None` (unknown algorithms) → `non-approved`. This reuses the existing classifier taxonomy — quantum-safe and classical-approved algorithms already land at `nist_level >= 1`; quantum-vulnerable (RSA, 3DES, RC4, MD5) are `nist_level == 0`.

- **D-03 — Annotation attached inside `_make_algorithm_component()`.** Add `properties=[Property(name="quirk:fips140-3-status", value=_fips_status(nist_level))]` directly in the factory function. Single touch point; every component built via this helper gets the annotation automatically. No post-build traversal pass needed.

- **D-04 — Helper `_fips_status(nist_level: int | None) -> str` in `builder.py`.** Small private helper that encodes the D-02 mapping. Returns `"approved"` or `"non-approved"`.

### SOC2 CC6.x and ISO 27001:2022 (COMPLY-11/12)

- **D-05 — `_soc2(control: str)` builder follows existing `_pci()/_hipaa()/_fips()` pattern.** Returns `{"framework": "SOC2 CC", "control": control, "version": "2017-rev", "last_verified": <phase_52_verified_date>, "source_url": <AICPA_CC_URL>}`. Unit test asserts ≥ 3 CC6.x control IDs present.

- **D-06 — SOC2 control assignment:** CC6.7 for transport/cipher/protocol findings (TLS, email, broker TLS in transit); CC6.6 for authentication and key/cert findings (SSH, JWT, API key, cert validity). Both CC6.6 + CC6.7 assigned to findings that span both domains (e.g., TLS legacy protocol).

- **D-07 — `_iso(control: str)` builder follows same pattern.** Returns `{"framework": "ISO 27001:2022", "control": control, "version": "ISO 27001:2022", "last_verified": <phase_52_verified_date>, "source_url": <ISO_27001_URL>}`. Uses 8.x clause numbering — unit test explicitly rejects any `A.x.x` (2013-style) control ID.

- **D-08 — ISO control assignment:** 8.24 (Use of Cryptography) for algorithm/key-size findings; 8.26 (Application security) for TLS/protocol transport findings; 8.28 (Secure coding) for source-code scanner findings. Multi-control mappings allowed per finding key (same as PCI/HIPAA).

- **D-09 — Full coverage parity with existing PCI/HIPAA.** Every finding category key in `COMPLIANCE_MAP` that has a `_pci()` or `_hipaa()` entry also gets `_soc2()` and `_iso()` entries. No existing key is left with only PCI/HIPAA coverage.

### `quirk doctor` CLI (DOCS-05)

- **D-10 — Subcommand intercept pattern in `run_scan.py:main()`.** `if len(sys.argv) > 1 and sys.argv[1] == "doctor"` before main argparse, delegating to `quirk/cli/doctor_cmd.py`. Consistent with `init`, `serve`, and `compliance` intercepts already in `main()`.

- **D-11 — QRAMM freshness check: graceful skip if module absent.** Doctor checks for QRAMM module availability (e.g., `quirk.qramm` importable and `qramm_sessions` table exists). If absent: shows `[!]` informational — "QRAMM module not installed — run Phase 51 first". Does NOT trigger exit code 1. Phase 52 is self-contained; this check becomes meaningful after Phase 51 ships.

- **D-12 — Rich text only, no `--format json`.** Doctor is an operator UX tool. Exit code (0 = all non-informational checks pass, 1 = any non-informational check fails) is the machine-readable signal. No format flag needed.

- **D-13 — Compliance framework freshness reuses `status_report()`.** Doctor calls into existing `quirk.compliance.status_report()` logic (or checks `STALENESS_THRESHOLD_DAYS` directly) rather than duplicating the staleness check. Shows `[✓]` if all frameworks within threshold, `[✗]` if any stale (non-informational → exits 1).

- **D-14 — 8 health check categories and exit semantics:**
  1. Python environment (version check) — non-informational; `[✗]` + exit 1 if unsupported
  2. Scanner binaries (nmap, syft, semgrep) — non-informational; `[✗]` + exit 1 if missing
  3. Compliance framework freshness (via STALENESS_THRESHOLD_DAYS) — non-informational; `[✗]` + exit 1 if stale
  4. QRAMM framework freshness — informational `[!]` only (graceful skip if Phase 51 not present)
  5. Database connectivity (`quirk.db` reachable and healthy) — non-informational; `[✗]` + exit 1 if unreachable
  6. Configuration validity (config.yaml parses cleanly) — non-informational; `[✗]` + exit 1 if invalid
  7. Network connectivity (DNS + TCP reachability probe) — informational `[!]` only, never exits 1
  8. Dashboard process status (port 8512 in use) — informational `[!]` only, never exits 1

### Tech Debt Fixes

- **D-15 — DEBT-02: Snapshot PROFILE_ARGS before `source .env`.** In `lab.sh`, capture the environment value before sourcing `.env` overrides it: `_PROFILE_ARGS_OVERRIDE="${PROFILE_ARGS:-}"` before `source .env`, then `PROFILE_ARGS="${_PROFILE_ARGS_OVERRIDE:-${PROFILE_ARGS:-}}"` after. This ensures `PROFILE_ARGS="--profile <name>" ./lab.sh up` wins over `.env` defaults.

- **D-16 — DEBT-03: `ports_scanned` + `hosts_scanned` in run-stats JSON.** Derived from the actual scan pipeline target list (after expand_targets + filter). Sorted lists of unique ports (integers) and hosts (strings). Added to `run_stats` dict in `run_scan.py` before `write_reports()` call.

- **D-17 — DEBT-04: Replace `defusedxml.lxml` with raw `lxml.etree`.** In `quirk/scanner/saml_scanner.py`, call `lxml.etree.fromstring(xml_bytes, parser=lxml.etree.XMLParser(resolve_entities=False, no_network=True))` directly. Preserves graceful degradation guard for when `lxml` is not installed. All 25 existing SAML tests must pass GREEN.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Compliance Module
- `quirk/compliance/__init__.py` — COMPLIANCE_MAP structure, existing `_pci()/_hipaa()/_fips()` builder pattern, `STALENESS_THRESHOLD_DAYS`, `TITLE_PREFIX_ALIASES` (MUST follow same pattern for `_soc2()/_iso()`)
- `.planning/milestones/v4.6-phases/49-compliance-mapping/49-CONTEXT.md` — D-01 establishes key-by-title data model; D-05 documents `compliance` field eager attachment; UNMAPPED_TITLES pattern
- `.planning/REQUIREMENTS.md` §COMPLY-10, COMPLY-11, COMPLY-12 — acceptance criteria for FIPS annotation, SOC2, ISO controls

### CBOM Builder
- `quirk/cbom/builder.py` — `_make_algorithm_component()` at line ~277; `_normalize_bom_ref_key()`; `build_cbom()` Pass-1 flow
- `quirk/cbom/classifier.py` — `classify_algorithm()` return signature `(primitive, nist_level, classical_level)`; `_ALGORITHM_TABLE`; `quantum_safety_label()` mapping logic (nist_level == 0 = quantum-vulnerable)
- `.planning/REQUIREMENTS.md` §COMPLY-10 — CBOM annotation acceptance criteria including unit test requirement

### CLI Structure
- `run_scan.py` lines 176–255 — existing subcommand intercept pattern (`init`, `serve`, `compliance`) that `quirk doctor` must follow
- `.planning/REQUIREMENTS.md` §DOCS-05 — `quirk doctor` 8 categories, `[✓]/[!]/[✗]` symbols, exit code semantics

### Tech Debt
- `quantum-chaos-enterprise-lab/lab.sh` lines 1–15 — PROFILE_ARGS + `.env` loading sequence (DEBT-02 fix target)
- `quirk/reports/writer.py` lines 187–195 — `run_stats` dict assembly before `_json_dump()` (DEBT-03 target)
- `quirk/scanner/saml_scanner.py` lines 1–20 — current `defusedxml.lxml` import pattern (DEBT-04 migration target)
- `tests/test_saml_scanner.py` — 25 existing SAML tests that must remain GREEN after DEBT-04 migration
- `.planning/REQUIREMENTS.md` §DEBT-02, DEBT-03, DEBT-04 — acceptance criteria for each debt item

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_pci()/_hipaa()/_fips()` builder helpers in `quirk/compliance/__init__.py` — `_soc2()/_iso()` copy this exact shape; one 6-key dict per call
- `quirk.compliance.status_report()` — reusable by doctor for compliance freshness check (D-13)
- `rich>=13.0.0` already in `pyproject.toml` — `quirk doctor` can use `rich.console.Console` and `rich.table.Table` directly; no new dependency
- `quirk/cli/` directory — existing CLI modules (`banner.py`, `init_cmd.py`) establish the file-per-subcommand pattern; `doctor_cmd.py` goes here

### Established Patterns
- **Subcommand intercept pattern** (`run_scan.py` lines 176–255): `if len(sys.argv) > 1 and sys.argv[1] == "<cmd>"` before main argparse, then delegate to `quirk/cli/<cmd>_cmd.py`. Doctor follows this exactly.
- **`_PHASE_49_VERIFIED` date constant** in `compliance/__init__.py`: Phase 52 adds a `_PHASE_52_VERIFIED` equivalent for SOC2/ISO `last_verified` fields.
- **CycloneDX `Component.properties`**: The `cyclonedx-python-lib` `Component` accepts a `properties` iterable of `Property(name, value)` objects — attach at construction time inside `_make_algorithm_component()`.

### Integration Points
- `_make_algorithm_component()` → add `properties=[...]` kwarg — `nist_level` is already in scope at that call site
- `run_scan.py:main()` → add `elif sys.argv[1] == "doctor"` intercept block (or new `if` before existing chain)
- `quirk/compliance/__init__.py:COMPLIANCE_MAP` → extend existing keys with `_soc2()/_iso()` entries in the same list; no structural changes to the dict

</code_context>

<specifics>
## Specific Ideas

- The `_fips_status()` helper in `builder.py` should be a small private function (3 lines) — not a method or class. Keeps it co-located with `_make_algorithm_component()`.
- SOC2 `version` field should be `"2017-rev"` (TSC 2017 revision) with source URL pointing to the AICPA Trust Services Criteria publication.
- ISO `version` field must be `"ISO 27001:2022"` (not `"2022"` alone, not `"ISO 27001:2013"`) — unit test rejects 2013-style `A.x.x` control IDs explicitly per COMPLY-12.
- `quirk doctor` output should use a Rich `Table` (not `Panel`) for the check results — two columns: "Check" and "Status". Matches consultant-grade terminal output.

</specifics>

<deferred>
## Deferred Ideas

- **`certified` CMVP tier** — reserved for a future phase when QUIRK can ingest CMVP module attestation (config flag, attestation file, or CMVP API lookup). Phase 52 emits only `approved`/`non-approved`.
- **`quirk doctor --format json`** — informational, not needed for current use cases. Revisit if CI health gate is requested.
- **SOC2 CC8.x / CC9.x controls** — availability/monitoring controls. Out of scope for crypto findings; could apply to scanner connectivity checks in a future phase.

</deferred>

---

*Phase: 52-compliance-uplift-health-check*
*Context gathered: 2026-05-05*
