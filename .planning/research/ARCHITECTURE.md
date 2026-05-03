# Architecture Patterns: v4.6 Enterprise Readiness Integration

**Project:** QU.I.R.K. v4.6
**Researched:** 2026-05-03
**Confidence:** HIGH — all findings based on direct source inspection

---

## Integration Summary by Feature

### BACK-76: Install-Day UX — Graceful ImportError Degradation

**Problem:** sslyze, impacket, kafka-python, redis, hvac are optional extras that currently crash
the scanner on import at runtime if the corresponding extra is not installed.

**Existing pattern to follow:** `_emit_missing_extra_advisory()` in `run_scan.py` (lines 122–142)
is the canonical v4.5 Phase 41 pattern. It prints a stderr advisory, appends a
`CryptoEndpoint(scan_error_category='missing_extra')` row, and returns, allowing the rest of
the scan to continue.

**Where degradation needs to be added:**

| Scanner | Module | AVAILABLE flag exists? | Advisory wired in run_scan.py? |
|---------|--------|----------------------|-------------------------------|
| `email_scanner` | `quirk/scanner/email_scanner.py` | `SSLYZE_AVAILABLE` | YES (lines 779-787) |
| `broker_scanner` | `quirk/scanner/broker_scanner.py` | `SSLYZE_AVAILABLE` | YES (lines 824-830) |
| `kerberos_scanner` | `quirk/scanner/kerberos_scanner.py` | `IMPACKET_AVAILABLE` | NO — missing advisory |
| `vault_connector` | `quirk/scanner/vault_connector.py` | `HVAC_AVAILABLE` | Partial — guards on HVAC_AVAILABLE but no advisory emission |
| `db_connector` | `quirk/scanner/db_connector.py` | Unknown — check psycopg2/pymysql guards | NO — missing advisory |

**What BACK-76 requires:**
1. Wire `_emit_missing_extra_advisory("kerberos_scanner", "identity", error_endpoints)` in the
   kerberos scanning block of `run_scan.py` when `IMPACKET_AVAILABLE is False`.
2. Wire advisory for `vault_connector` when `HVAC_AVAILABLE is False`.
3. Wire advisory for `db_connector` when psycopg2/pymysql are absent.
4. `pyproject.toml`: move sslyze into core deps or a default-installed extra so email/broker
   scanning works on first install. The milestone context says "ship identity/motion extras by
   default" — this means changing the install happy path.
5. The `_wrapped_phase` helper is already present and should wrap the kerberos/vault/db phases
   consistently (they currently use bare `with _phase_timer()` blocks without `_wrapped_phase`).

**Files to modify:** `run_scan.py`, `pyproject.toml`. No new modules needed.

---

### BACK-74: TLS Finding Gaps — Expired Certs, Self-Signed Certs, RSA-1024/512

**Good news: the finding generation code already exists.** Inspecting `quirk/engine/risk_engine.py`
(lines 325–421) shows that `evaluate_endpoints()` already generates:
- `"TLS certificate expired"` (HIGH) and `"TLS certificate expiring within 30 days"` (MEDIUM)
  via `cert_not_after` datetime comparison (lines 326–352)
- `"Self-signed or untrusted TLS certificate"` (MEDIUM) via `cert_issuer == cert_subject` or
  `chain_verified is False` (lines 355–368)
- `"TLS certificate uses undersized RSA key"` (HIGH) for `cert_pubkey_size < 2048` (lines 371–397)

Similarly, `quirk/dashboard/api/routes/scan.py` `_derive_findings()` (lines 47–186) already
generates these as `FindingItem` objects.

**The actual gap is data availability, not finding logic.** The sslyze scanner path
(`_scan_one_sslyze` in `quirk/scanner/tls_scanner.py`) correctly populates:
- `ep.cert_not_before` / `ep.cert_not_after` (lines 197–205) from `leaf.not_valid_before_utc`
- `ep.cert_subject` / `ep.cert_issuer` (lines 183–184)
- `ep.cert_pubkey_size` via `_pubkey_info(pubkey)` (lines 192–195)
- `tls_capabilities_json` with `"chain_verified"` (line 308)

The fallback scanner (`_scan_one_fallback`) also populates all these fields (lines 368–389).

**Investigation needed in BACK-74 phase:** Verify whether expired/self-signed certs in the chaos
lab actually reach the finding generation step. The most likely culprits:
1. sslyze may return `scan_status != COMPLETED` for expired/self-signed certs (TLS validation
   errors) → `_scan_one_sslyze` returns `None` → falls back to `_scan_one_fallback` → fallback
   uses `ssl.CERT_NONE` so it connects regardless.
2. The fallback's `chain_verified` value is never set (only sslyze sets it in `tls_capabilities_json`).
3. The risk_engine `_chain_verified()` helper (line 136) reads `chain_verified` from
   `tls_capabilities_json` — if the fallback ran, that field is absent and `_chain_verified()`
   returns `None`, so the self-signed check falls through.

**Fix location:** `_scan_one_sslyze` — after `CERTIFICATE_INFO` completes, capture
`deployment.verified_certificate_chain is not None`, store in `tls_capabilities_json`. Also add
a direct self-signed heuristic (`leaf.issuer == leaf.subject`) directly onto `ep` at scan time
so the fallback scanner path also emits it without depending on sslyze.

**Files to modify:** `quirk/scanner/tls_scanner.py` only. The risk_engine and dashboard route
finding generators are already correct — no changes needed there.

---

### BACK-79: Rich Finding Context — Per-Finding Risk Explanation + PQC Remediation

**Where enrichment belongs: at finding generation time, not at API response time.**

Rationale: findings are derived at API response time from endpoint data (no separate findings
table). Adding enrichment at API response time would duplicate logic between `risk_engine.py`
(CLI/report path) and `routes/scan.py` (dashboard path). The correct approach is to enrich the
`recommendation` and `description` fields when findings are generated, so both paths benefit.

**Current finding schema** (`FindingItem` in `quirk/dashboard/api/schemas.py`, lines 44–56):
```python
class FindingItem(BaseModel):
    id: Optional[int] = None
    host: str
    port: int
    severity: str
    title: str
    protocol: Optional[str] = None
    description: Optional[str] = None      # already exists
    remediation: Optional[str] = None      # already exists
    quantum_risk: Optional[str] = None     # already exists
    source: Optional[str] = None
```

All three enrichment fields (`description`, `remediation`, `quantum_risk`) already exist on
`FindingItem`. The risk_engine `evaluate_endpoints()` (lines 246–447) populates `recommendation`
but not `description`. The dashboard API `_derive_findings()` populates `description` inline.

**What BACK-79 requires:**
1. Expand `description` text in `_derive_findings()` (in `routes/scan.py`) to include risk
   rationale — why this matters quantum-security-wise, not just what the finding is.
2. Expand `remediation` text in `_derive_findings()` to include specific PQC migration path
   (algorithm name, NIST standard reference: FIPS 203 ML-KEM, FIPS 204 ML-DSA, FIPS 205 SLH-DSA).
3. Expand `risk_engine.evaluate_endpoints()` `recommendation` text similarly for the CLI/report path.
4. Optionally add `pqc_migration_path: Optional[str] = None` to `FindingItem` — but enriching
   the existing `remediation` string is simpler and avoids TypeScript schema churn in
   `src/dashboard/src/types/api.ts`.
5. Apply same enrichment to `IdentityFinding`, `MotionFinding`, `DarFinding` derivation functions.

**No new modules needed.** Enrichment is a text expansion within existing generation functions.

**Files to modify:**
- `quirk/engine/risk_engine.py` — expand `recommendation` strings
- `quirk/dashboard/api/routes/scan.py` — expand `description` and `remediation` strings in
  `_derive_findings()`, `_derive_identity_findings()`, `_derive_motion_findings()`, `_derive_dar_findings()`
- `quirk/dashboard/api/schemas.py` — add `pqc_migration_path: Optional[str] = None` if desired

---

### BACK-20: Compliance Mapping — FIPS/NIST SP 800-208/PCI-DSS 4.0/HIPAA

**Where it belongs: a new module `quirk/compliance/` consumed at report generation time.**

Compliance mapping maps findings to framework control IDs. It has no dependency on scan data
beyond the finding itself (severity + title + algorithm). This is pure reference data + lookup logic,
not scanner logic. Creating `quirk/compliance/` separates concerns cleanly:

```
quirk/compliance/
    __init__.py
    mapper.py           # finding -> [ControlReference] lookup
    frameworks.py       # FIPS_140_3 / NIST_SP_800_208 / PCI_DSS_4 / HIPAA constants
```

**Data model for a control reference:**
```python
@dataclass
class ControlReference:
    framework: str       # "FIPS 140-3" | "NIST SP 800-208" | "PCI DSS 4.0" | "HIPAA"
    control_id: str      # e.g. "PCI DSS 4.0 s6.2.4"
    requirement: str     # human-readable control text
    applicability: str   # "DIRECT" | "RELATED" | "INFORMATIONAL"
```

**Integration points:**

1. **CLI report path:** `quirk/reports/technical.py` and `quirk/reports/executive.py` call the
   mapper on the findings list at report write time. No schema changes.

2. **API path:** Add `compliance_references` list field to `FindingItem` in schemas.py, or expose
   compliance as a separate API endpoint `GET /api/compliance` (preferred — avoids bloating the
   already-large `ScanLatestResponse`). A separate endpoint also means the React frontend can
   lazy-load compliance data only when the compliance tab is open.

3. **Optional-by-default:** The compliance module has zero external dependencies — it is pure
   Python lookup tables. No extra group needed. It ships in core and is simply not called unless
   the user requests a compliance report.

**No breaking schema changes required** if delivered as a new API endpoint. The compliance module
does not touch the SQLite schema (no new ORM columns). Finding-to-control mapping is stateless.

**Files to create:** `quirk/compliance/__init__.py`, `quirk/compliance/mapper.py`,
`quirk/compliance/frameworks.py`

**Files to modify:** `quirk/reports/technical.py`, `quirk/reports/executive.py` (add compliance
section to HTML/PDF reports); optionally new `quirk/dashboard/api/routes/compliance.py` and
additions to `quirk/dashboard/api/schemas.py` (new `ComplianceRef` model).

---

### BACK-75: Nmap Port Discovery — Pre-Scan Nmap Probe

**Nmap integration already exists end-to-end.** The `quirk/discovery/nmap_provider.py` module
implements `run_nmap_discovery()` which runs nmap, parses XML, and returns `NmapOpenPort` objects.
The `run_scan.py` `--discovery nmap` CLI flag (line 228) routes through this code path already
(lines 321–356).

**What BACK-75 requires is UX work, not new architecture:**

1. `interactive.py` (`interactive_config()`) currently does not surface nmap discovery as an
   option — the user must pass `--discovery nmap` on the CLI. Add a `_prompt_bool("Use Nmap for
   port discovery (requires nmap in PATH)", False)` prompt after the scan profile question.

2. When nmap is chosen in interactive mode, check if `nmap` is in PATH before the scan starts
   and emit a clear error if not. The current `run_nmap_discovery()` raises `RuntimeError` on
   `FileNotFoundError` — this needs to be caught gracefully and presented as a user-facing
   message, not a traceback.

3. The `--nmap-extra-args`, `--nmap-path`, and `--nmap-timeout` CLI flags already exist. No new
   CLI flags needed.

**Graceful degradation:** nmap is a subprocess call, not a Python package — no `ImportError`
pattern applies. The degradation is: if nmap binary is absent, fall back to builtin
fingerprinting with an advisory message. The `nmap_provider.py` `FileNotFoundError` catch
(line 75–79) already raises `RuntimeError`. The fix is to catch that `RuntimeError` in
`run_scan.py` and fall back to builtin discovery rather than aborting the scan.

**Files to modify:** `quirk/interactive.py` (add discovery prompt), `run_scan.py` (catch nmap
RuntimeError and fall back). No new modules.

---

### BACK-77: Multi-Target Wizard — Multi-Host Input in Interactive Mode

**Current state in `quirk/interactive.py`:**

The `_prompt_list()` helper (lines 71–77) already accepts comma-or-space-separated input and
returns `List[str]`. The "Targets" section (lines 127–133) calls `_prompt_list` for CIDRs,
FQDNs, and IPs — so multi-host input is architecturally supported.

**The gap is not parsing, it is UX and file-input:**

1. Consultants with 50+ hosts need to supply a file path (`@hosts.txt`) rather than pasting
   comma-separated IPs into a prompt. `_prompt_list()` does not support file-path input.

2. The interactive prompt for FQDNs/IPs does not validate input length or give feedback on how
   many hosts were recognized.

3. `TargetsCfg` in `config.py` already has `fqdns: List[str]`, `cidrs: List[str]`,
   `include_ips: List[str]` — the data model is correct.

**What BACK-77 requires:**

1. Extend `_prompt_list()` or add `_prompt_list_or_file()`: if input starts with `@`, read lines
   from that file and return them as the list.

2. Add a `--targets-file` CLI argument to `run_scan.py` that loads a newline-delimited host file
   into `cfg.targets.include_ips` / `cfg.targets.fqdns` before the scan begins.

3. The interactive wizard should explicitly prompt: "Enter hosts/IPs directly, or enter @filepath
   to load from a file."

4. Add basic validation: after parsing, print the count of recognized targets so the user can
   confirm the input was correctly parsed.

**Files to modify:** `quirk/interactive.py` (`_prompt_list_or_file()` helper, update target
prompts), `run_scan.py` (add `--targets-file` argparse argument, load before `interactive_config()`
or merge after). No schema changes — `TargetsCfg` fields are already lists.

---

### BACK-65 + BACK-66: Architecture Reference Doc + Operator's Guide

**Where docs live:** `docs/` directory, Markdown format. Existing files:
- `docs/getting-started.md`
- `docs/installation.md`
- `docs/configuration.md`
- `docs/report-interpretation.md`
- `docs/chaos-lab.md`
- `docs/connectors/` — per-connector guides

**Format:** Plain Markdown only. Existing guides are plain Markdown with no special tooling.
The Obsidian vault sync (CLAUDE.md "Sync Workflows" section) handles publishing.

**BACK-65: Architecture Reference Doc** → `docs/architecture.md`
Contents: system diagram (ASCII or Mermaid), scanner pipeline, CBOM pipeline, intelligence layer,
FastAPI/React data flow, SQLite schema overview, extras groups, chaos lab structure.

**BACK-66: Operator's Guide** → `docs/operators-guide.md`
Contents: production deployment checklist, config.yaml complete reference, all scanner enable
flags, nmap integration, multi-target patterns, troubleshooting scan errors, reading the report,
compliance mapping usage.

**Files to create:** `docs/architecture.md`, `docs/operators-guide.md`. No code changes.
Both files must be synced to Obsidian vault at `20_Dev-Work/QUIRK/Guides/` per CLAUDE.md patterns.

---

## System-Level Data Flow

```
CLI / interactive.py
        |
        v
run_scan.py
  |  discovery (builtin fingerprinting OR nmap — BACK-75)
  |  multi-target file load (BACK-77)
  |  +-----------------------------------------------------------------+
  |  | scanner phases, each in _wrapped_phase or _phase_timer           |
  |  |   tls_scanner.py  ->  CryptoEndpoint[]  (BACK-74 fixes here)   |
  |  |   ssh_scanner.py  ->  CryptoEndpoint[]                          |
  |  |   kerberos/saml/dnssec  ->  CryptoEndpoint[]  (BACK-76 guard)  |
  |  |   email_scanner  ->  CryptoEndpoint[]                           |
  |  |   broker_scanner  ->  CryptoEndpoint[]                          |
  |  |   db/k8s/vault/aws/azure/gcp  ->  CryptoEndpoint[]  (BACK-76)  |
  |  +-----------------------------------------------------------------+
  |  risk_engine.evaluate_endpoints()  ->  findings (BACK-79 enriched)
  |  SQLite persist
  |  write_reports()  <-- quirk/compliance/mapper.py called here (BACK-20)
  +-> quirk-output/ (intelligence*.json, report-*.html, cbom-*.json/.xml)

FastAPI (quirk/dashboard/api/)
  GET /api/scan/latest
    _derive_findings()          (BACK-79 enriched description/remediation)
    _derive_identity_findings()
    _derive_motion_findings()
    _derive_dar_findings()
    _derive_cbom()
    compute_readiness_score()
    compute_confidence()
  GET /api/compliance  (new, BACK-20)
    quirk/compliance/mapper.map_finding()

React SPA (src/dashboard/)
```

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `run_scan.py` | Orchestrates all scanner phases; assembles endpoint list; calls risk_engine, db persist, write_reports | All scanner modules, risk_engine, reports, db |
| `quirk/interactive.py` | Interactive wizard — prompts, builds AppConfig | run_scan.py (returns cfg + scan_profile) |
| `quirk/scanner/tls_scanner.py` | TLS scanning via sslyze (primary) + ssl fallback; populates CryptoEndpoint | run_scan.py |
| `quirk/engine/risk_engine.py` | CLI-path finding generation; finding dedup/normalization | run_scan.py, reports |
| `quirk/dashboard/api/routes/scan.py` | API-path finding derivation (parallel to risk_engine); score/confidence computation | FastAPI, intelligence/, cbom/classifier |
| `quirk/compliance/` (NEW) | Finding-to-control-ID mapping; zero external deps | risk_engine, routes/scan.py, reports |
| `quirk/discovery/nmap_provider.py` | Subprocess nmap execution and XML output | run_scan.py |
| `quirk/cbom/` | classifier -> builder -> writer pipeline; CycloneDX 1.6 JSON+XML | run_scan.py via write_reports; classifier imported by routes/scan.py |
| `quirk/intelligence/` | 6-pillar scoring, evidence counters, confidence, roadmap | routes/scan.py, write_reports |
| `docs/` | Markdown documentation suite | Obsidian vault sync |

---

## New vs. Modified Files Summary

| Backlog Item | Action | Files |
|---|---|---|
| BACK-76 | Modify | `run_scan.py`, `pyproject.toml` |
| BACK-74 | Modify | `quirk/scanner/tls_scanner.py` |
| BACK-79 | Modify | `quirk/engine/risk_engine.py`, `quirk/dashboard/api/routes/scan.py`, optionally `quirk/dashboard/api/schemas.py` |
| BACK-20 | Create + Modify | `quirk/compliance/__init__.py`, `quirk/compliance/mapper.py`, `quirk/compliance/frameworks.py`; modify `quirk/reports/technical.py`, `quirk/reports/executive.py`; optionally new `quirk/dashboard/api/routes/compliance.py` and additions to `quirk/dashboard/api/schemas.py` |
| BACK-75 | Modify | `quirk/interactive.py`, `run_scan.py` |
| BACK-77 | Modify | `quirk/interactive.py`, `run_scan.py` |
| BACK-65 | Create | `docs/architecture.md` |
| BACK-66 | Create | `docs/operators-guide.md` |

---

## Recommended Build Order

Dependencies between the 7 features:

```
BACK-76 (graceful degradation)
    No dependencies. Build first — fixes crashes that block testing of everything else.

BACK-74 (TLS finding gaps)
    Depends on BACK-76 being stable (need reliable sslyze path before debugging cert data).

BACK-75 (nmap discovery UX) + BACK-77 (multi-target wizard)
    No dependencies on BACK-74 or each other. Can be one phase or two parallel phases.

BACK-79 (rich finding context)
    Depends on BACK-74 (want all TLS findings present before enriching text).
    Must precede BACK-20 (compliance text uses enriched remediation descriptions).

BACK-20 (compliance mapping)
    Depends on BACK-79 (enriched findings make mapping more coherent).
    No code dependency on BACK-75 or BACK-77.

BACK-65 + BACK-66 (docs)
    Written last — documents the completed feature set.
```

**Recommended phase sequence:**
1. BACK-76 — install-day fixes (unblocks all testing)
2. BACK-74 — TLS finding gaps (core correctness)
3. BACK-75 + BACK-77 — nmap + multi-target (independent; one combined phase)
4. BACK-79 — finding enrichment (requires correct findings from BACK-74)
5. BACK-20 — compliance mapping (new module; requires enriched findings)
6. BACK-65 + BACK-66 — documentation (last, documents completed milestone)

---

## Patterns to Follow

### Pattern 1: Optional Extra Guard (BACK-76)
Follow the existing `_emit_missing_extra_advisory()` + `_wrapped_phase()` pattern from Phase 41.

The correct shape for a scanner phase with optional extras in `run_scan.py`:
```python
# 1. Probe at module level, outside _wrapped_phase:
if cfg.connectors.enable_kerberos and cfg.connectors.kerberos_targets:
    from quirk.scanner import kerberos_scanner as _kerb_mod
    if not getattr(_kerb_mod, "IMPACKET_AVAILABLE", True):
        _emit_missing_extra_advisory("kerberos_scanner", "identity", error_endpoints)
        cfg_kerberos_skip = True
    else:
        cfg_kerberos_skip = False
else:
    cfg_kerberos_skip = True

# 2. Run inside _wrapped_phase:
def _run_kerberos_phase():
    if cfg_kerberos_skip:
        return []
    ...
kerberos_endpoints = _wrapped_phase(
    run_stats, "kerberos_scanning", "kerberos_scanner",
    _run_kerberos_phase, error_endpoints, logger,
) or []
```

### Pattern 2: File-or-List Input (BACK-77)
```python
def _prompt_list_or_file(text: str, default=None) -> List[str]:
    raw = _prompt(f"{text} (comma-separated, or @filepath)", "")
    if raw.startswith("@"):
        path = raw[1:].strip()
        try:
            with open(path) as f:
                return [l.strip() for l in f if l.strip() and not l.startswith("#")]
        except OSError as e:
            print(f"  Could not read file {path}: {e}")
            return []
    return [x.strip() for x in re.split(r"[,\s]+", raw) if x.strip()]
```

### Pattern 3: sslyze Version Guard (BACK-74)
The existing `hasattr(leaf, "not_valid_before_utc")` guard in `_scan_one_sslyze` (line 198)
is the established pattern for accessing sslyze API surface that may differ across versions.
All BACK-74 changes to `_scan_one_sslyze` must use `hasattr` guards for any new API access.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Third Finding Derivation Path
`risk_engine.evaluate_endpoints()` (CLI path) and `_derive_findings()` (API path) are already
parallel implementations. Do not add a third finding derivation path for compliance. Call
`mapper.map_finding(finding_dict)` from both existing paths.

### Anti-Pattern 2: New Required Dependencies for Optional Features
Compliance mapping (BACK-20) must remain zero-dependency — no new pip packages. The framework
control tables are static data. If compliance data ever needs external fetch, that is a future
SaaS feature.

### Anti-Pattern 3: Breaking the `tls_capabilities_json` Contract
The `chain_verified` field inside `tls_capabilities_json` is read by `_chain_verified()` in
`risk_engine.py`. When modifying `_scan_one_sslyze` for BACK-74, add new keys alongside
existing ones — do not rename or remove `chain_verified` or `source` keys. Existing tests
snapshot this structure.

### Anti-Pattern 4: Mutating AppConfig After Construction
The `_wrapped_phase` advisory pattern sets a `cfg_*_skip` boolean variable rather than mutating
`cfg.connectors.enable_*`. Do not change the enable flags on the config object — this would
affect report/stats output and violate the Phase 41 design.

### Anti-Pattern 5: sslyze Returning None for Invalid Certs
`_scan_one_sslyze` returns `None` when `scan_status != COMPLETED`. For expired/self-signed
certs, sslyze may complete the scan but with `CERTIFICATE_INFO` in a non-COMPLETED attempt
state. Check `cert_attempt.status` specifically (not just server scan status) and extract
whatever cert data is available even on partial sslyze results, before triggering fallback.

---

## Confidence Assessment

| Area | Confidence | Source |
|------|------------|--------|
| BACK-76 missing advisories | HIGH | Direct inspection of run_scan.py kerberos/vault/db phases |
| BACK-74 finding code exists | HIGH | Direct inspection of risk_engine.py lines 325-421 and routes/scan.py lines 47-186 |
| BACK-74 data availability gap | HIGH | sslyze fallback path confirmed via tls_scanner.py; chain_verified only set by sslyze path |
| BACK-79 schema fields exist | HIGH | Direct inspection of schemas.py FindingItem |
| BACK-20 no new deps needed | HIGH | Compliance mapping is static lookup; verified no external calls required |
| BACK-75 nmap fully implemented | HIGH | Direct inspection of nmap_provider.py and run_scan.py lines 321-356 |
| BACK-77 _prompt_list exists | HIGH | Direct inspection of interactive.py lines 71-77 |
| BACK-65/66 docs format | HIGH | Direct inspection of docs/ directory structure |
