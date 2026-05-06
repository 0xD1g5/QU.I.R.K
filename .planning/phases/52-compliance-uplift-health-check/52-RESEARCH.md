# Phase 52: Compliance Uplift & Health Check - Research

**Researched:** 2026-05-05
**Domain:** Python compliance framework extensions, CycloneDX CBOM property annotation, Rich CLI health dashboard, bash PROFILE_ARGS fix, lxml migration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**FIPS 140-3 Annotation (COMPLY-10)**
- D-01: `certified` tier never emitted in v4.7. All algorithm components receive `approved` or `non-approved` only.
- D-02: `approved`/`non-approved` derived from `nist_level`. Mapping: `nist_level >= 1` → `approved`; `nist_level == 0` → `non-approved`; `nist_level == None` → `non-approved`.
- D-03: Annotation attached inside `_make_algorithm_component()`.
- D-04: Helper `_fips_status(nist_level: int | None) -> str` in `builder.py`.

**SOC2 + ISO 27001:2022 (COMPLY-11/12)**
- D-05: `_soc2(control: str)` returns `{"framework": "SOC2 CC", "control": control, "version": "2017-rev", "last_verified": <phase_52_verified_date>, "source_url": <AICPA_CC_URL>}`.
- D-06: CC6.7 for transport/cipher/protocol findings; CC6.6 for auth and key/cert findings; both for findings spanning both domains.
- D-07: `_iso(control: str)` returns `{"framework": "ISO 27001:2022", "control": control, "version": "ISO 27001:2022", ...}`. Unit test rejects `A.x.x` IDs.
- D-08: 8.24 for algorithm/key-size findings; 8.26 for TLS/protocol transport; 8.28 for source-code scanner findings.
- D-09: Full parity — every COMPLIANCE_MAP key with `_pci()` or `_hipaa()` also gets `_soc2()` and `_iso()`.

**`quirk doctor` CLI (DOCS-05)**
- D-10: `if len(sys.argv) > 1 and sys.argv[1] == "doctor"` intercept in `run_scan.py:main()`, delegating to `quirk/cli/doctor_cmd.py`.
- D-11: QRAMM freshness check shows `[!]` informational only (graceful skip if Phase 51 not present). Does NOT exit 1.
- D-12: Rich text only, no `--format json`. Exit code is the machine-readable signal.
- D-13: Compliance framework freshness via `quirk.compliance.status_report()` or `STALENESS_THRESHOLD_DAYS`.
- D-14: 8 health check categories with precise exit semantics (see CONTEXT.md D-14 for full list).

**Tech Debt Fixes**
- D-15: DEBT-02: Snapshot `PROFILE_ARGS` before `source .env` in `lab.sh`.
- D-16: DEBT-03: `ports_scanned` + `hosts_scanned` added to `run_stats` dict in `run_scan.py` — currently these fields already exist inside `run_stats["counts"]`; the requirement is to ensure they also appear as top-level `run_stats` fields (per UAT-3-02 note about "run-stats ports_scanned").
- D-17: DEBT-04: Replace `defusedxml.lxml` with raw `lxml.etree.fromstring(xml_bytes, parser=lxml.etree.XMLParser(resolve_entities=False, no_network=True))`. Preserve graceful degradation guard when `lxml` not installed.

### Claude's Discretion
None specified — all decisions locked.

### Deferred Ideas (OUT OF SCOPE)
- `certified` CMVP tier — future phase
- `quirk doctor --format json` — future if CI health gate requested
- SOC2 CC8.x/CC9.x controls — out of scope for crypto findings
- New finding categories (email/broker/identity/DAR) — SOC2/ISO mappings on existing keys only
- Dashboard UI compliance view — Phase 55
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COMPLY-10 | CBOM Pass-1 algo components carry `quirk:fips140-3-status` property (`approved`/`non-approved`) via `Component.properties` | CycloneDX `Property` model verified in project venv; `_make_algorithm_component()` signature fully understood |
| COMPLY-11 | SOC2 CC6.x controls mapped via `_soc2()` helper following existing `_pci()/_hipaa()/_fips()` pattern | Existing compliance module structure fully read; builder pattern 1:1 documented |
| COMPLY-12 | ISO 27001:2022 controls (8.x numbering) mapped via `_iso()` helper; unit test rejects `A.x.x` IDs | ISO 8.x clause mapping verified against D-08 decisions; existing schema test patterns reviewed |
| DOCS-05 | `quirk doctor` CLI: 8 categories, `[✓]/[!]/[✗]`, exits 1 on non-informational failure | Subcommand intercept pattern fully documented; `shutil.which`, `socket`, `sqlite3` probe patterns confirmed; Rich 14.3.3 Table rendering verified |
| DEBT-02 | `lab.sh` PROFILE_ARGS CLI precedence fixed — snapshot before `source .env` | `lab.sh` lines 1–15 read; fix strategy confirmed (snapshot variable before source) |
| DEBT-03 | `run-stats-*.json` includes `ports_scanned` and `hosts_scanned` | Fields already exist in `run_stats["counts"]` at line 534–535; UAT note confirms correct location; planner needs to clarify exact placement requirement |
| DEBT-04 | `saml_scanner.py` migrated from `defusedxml.lxml` to `lxml.etree` with security flags | `lxml.etree.XMLParser(resolve_entities=False, no_network=True)` verified working in project venv; `defusedxml.lxml` emits `DeprecationWarning` confirmed |
</phase_requirements>

---

## Summary

Phase 52 is a four-track parallel phase requiring no new pip dependencies. All work touches existing, well-understood modules with established patterns — making this a precision surgical phase rather than a design phase. The CONTEXT.md decisions are exhaustive and leave essentially no discretionary choices for the planner.

**Track 1 (COMPLY-10):** The CycloneDX `Property` model is available and verified in the project virtualenv. `Component.__init__` already accepts a `properties: Iterable[Property] | None` kwarg. `_make_algorithm_component()` already has `nist_level` in scope via `classify_algorithm()`. The `_fips_status()` helper logic is a 3-line function. The FIPS annotation status derived from `nist_level` was manually verified: AES-256-GCM (nist_level=1) → `approved`; RSA/3DES (nist_level=0) → `non-approved`; RC4/MD5 (nist_level=None) → `non-approved`; ml-kem-768 (nist_level=3) → `approved`. This mapping exactly matches D-02.

**Track 2 (COMPLY-11/12):** The `_pci()/_hipaa()/_fips()` builder pattern is a single 6-key dict per call. `_soc2()` and `_iso()` are direct clones with different framework/version/source_url values. All 23 COMPLIANCE_MAP keys have been reviewed — every key with `_pci()` or `_hipaa()` must gain `_soc2()` and `_iso()` entries. The `_PHASE_49_VERIFIED` date constant pattern means Phase 52 adds `_PHASE_52_VERIFIED = "2026-05-05"`.

**Track 3 (DOCS-05):** The `quirk doctor` subcommand follows an exact 4-step intercept pattern already used by `init`, `serve`, and `compliance`. Rich 14.3.3 is installed and `Table` rendering works. The 8-category health check implementation uses `shutil.which` for binary detection (already used in `container_scanner.py` and `optional_extra.py`), `sqlite3.connect()` for DB probe, and `socket.create_connection()` for network probe.

**Track 4 (DEBT-02/03/04):** `lab.sh` PROFILE_ARGS fix is a 2-line shell change. DEBT-03 requires clarification — `ports_scanned` and `hosts_scanned` already exist in `run_stats["counts"]`; the UAT-3-02 note references these fields by name without nesting, suggesting the requirement is to also expose them at the `run_stats` top level (or the UAT test already passes as-is). DEBT-04: `defusedxml.lxml` emits a `DeprecationWarning` in the project venv; `lxml.etree.XMLParser(resolve_entities=False, no_network=True)` is verified to work.

**Primary recommendation:** Execute four independent plans in parallel. No cross-plan dependencies within Phase 52.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| FIPS 140-3 annotation (COMPLY-10) | Backend / Python lib | — | CBOM builder is a pure Python library layer; annotation logic lives co-located with algorithm component factory |
| SOC2/ISO compliance mapping (COMPLY-11/12) | Backend / Python lib | — | `quirk/compliance/__init__.py` is the canonical compliance tier; no UI or API involvement |
| `quirk doctor` CLI (DOCS-05) | CLI layer | Backend probes | CLI presentation via Rich; backend checks for DB/config/network probes |
| `lab.sh` PROFILE_ARGS fix (DEBT-02) | Chaos lab tooling | — | Pure bash script fix; no Python involved |
| `run-stats` fields (DEBT-03) | Backend / run_scan | — | `run_stats` dict assembled in `run_scan.py:main()`; `write_reports()` consumes it |
| `saml_scanner.py` migration (DEBT-04) | Backend / scanner | — | Module-internal XML parsing; lxml is already a project dependency |

---

## Standard Stack

### Core (all already installed — no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| cyclonedx-python-lib | >=11.7.0,<12 [VERIFIED: pyproject.toml] | CycloneDX CBOM model; `Property`, `Component` | Only CycloneDX Python library; already the QUIRK CBOM engine |
| rich | 14.3.3 [VERIFIED: pip show in project venv] | Rich terminal output; `Console`, `Table` | Already in `pyproject.toml`; used throughout QUIRK writers |
| lxml | 6.0.1 [VERIFIED: project venv] | XML parsing for SAML migration | Already in `pyproject.toml`; replaces `defusedxml.lxml` |
| defusedxml | 0.7.1 [VERIFIED: project venv] | Still in deps for fallback stdlib path | Remains for `defusedxml.ElementTree` fallback when `lxml` absent |

### No New Dependencies
Phase 52 explicitly requires zero new pip dependencies [VERIFIED: CONTEXT.md, STATE.md v4.7-D-01 scope].

---

## Architecture Patterns

### System Architecture Diagram

```
run_scan.py:main()
    │
    ├── [if sys.argv[1] == "doctor"] ──────────────────────────────────┐
    │                                                                    │
    │                                                               quirk/cli/doctor_cmd.py
    │                                                                    │
    │                                                         ┌──────── 8 health checks ─────────┐
    │                                               shutil.which(nmap/syft/semgrep)        quirk.compliance.status_report()
    │                                               sqlite3.connect(quirk.db)              socket.create_connection(host,port)
    │                                               yaml.safe_load(config.yaml)            port 8512 socket probe
    │                                               python sys.version_info check          qramm module import probe (informational)
    │                                                                    │
    │                                                         Rich Table output → stdout
    │                                                         exit(0) or exit(1)
    │
    ├── [main scan path]
    │       │
    │       ├── expand_targets(cfg) ──► targets: list[(host, port)]
    │       │
    │       ├── run_stats["counts"]["ports_scanned"] = sorted({p for _,p in targets})  [already exists line 535]
    │       ├── run_stats["counts"]["hosts_scanned"] = sorted({h for h,_ in targets})  [already exists line 534]
    │       │   [DEBT-03: verify field also appears at run_stats top level if needed]
    │       │
    │       └── write_reports(cfg, endpoints, findings, run_stats=run_stats)
    │               │
    │               └── build_cbom(endpoints)
    │                       │
    │                       └── Pass 1: _make_algorithm_component(name, bom_ref_key, key_size)
    │                                       │
    │                                       ├── classify_algorithm(name) → (primitive, nist_level, classical)
    │                                       ├── _fips_status(nist_level) → "approved" | "non-approved"  [NEW]
    │                                       └── Component(..., properties=[Property("quirk:fips140-3-status", status)])  [NEW]
    │
quirk/compliance/__init__.py
    ├── _PHASE_52_VERIFIED = "2026-05-05"  [NEW]
    ├── _SOC2_CC_URL = "https://..."       [NEW]
    ├── _ISO_27001_URL = "https://..."     [NEW]
    ├── _soc2(control) → dict              [NEW]
    ├── _iso(control) → dict               [NEW]
    └── COMPLIANCE_MAP: every existing key gains _soc2() + _iso() entries  [NEW]

quantum-chaos-enterprise-lab/lab.sh
    ├── [BEFORE source .env]  _PROFILE_ARGS_OVERRIDE="${PROFILE_ARGS:-}"  [NEW: DEBT-02]
    ├── source .env
    └── [AFTER source .env]   PROFILE_ARGS="${_PROFILE_ARGS_OVERRIDE:-${PROFILE_ARGS:-}}"  [NEW]

quirk/scanner/saml_scanner.py
    └── [import block refactored: DEBT-04]
        try:
            import lxml.etree as ET
            def _safe_ET_fromstring(xml_bytes):
                return ET.fromstring(xml_bytes, parser=ET.XMLParser(resolve_entities=False, no_network=True))
            LXML_AVAILABLE = True
        except ImportError:
            [defusedxml.ElementTree stdlib fallback — unchanged]
```

### Recommended Project Structure

No new directories needed. New file:

```
quirk/
├── cli/
│   ├── banner.py          # existing
│   ├── init_cmd.py        # existing
│   └── doctor_cmd.py      # NEW — quirk doctor implementation
```

### Pattern 1: Compliance Builder Helper (SOC2/ISO follows `_pci()` pattern exactly)

```python
# Source: quirk/compliance/__init__.py (existing _pci() pattern)
_PHASE_52_VERIFIED: str = "2026-05-05"
_SOC2_CC_URL = "https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater/trust-services-criteria"
_ISO_27001_URL = "https://www.iso.org/standard/82875.html"

def _soc2(control: str) -> Dict[str, Any]:
    return {
        "framework": "SOC2 CC",
        "control": control,
        "version": "2017-rev",
        "last_verified": _PHASE_52_VERIFIED,
        "source_url": _SOC2_CC_URL,
    }

def _iso(control: str) -> Dict[str, Any]:
    return {
        "framework": "ISO 27001:2022",
        "control": control,
        "version": "ISO 27001:2022",
        "last_verified": _PHASE_52_VERIFIED,
        "source_url": _ISO_27001_URL,
    }
```

### Pattern 2: FIPS 140-3 Status Annotation in CBOM Builder

```python
# Source: CONTEXT.md D-03/D-04; verified against cyclonedx-python-lib in project venv
from cyclonedx.model import Property  # add to existing import

def _fips_status(nist_level: int | None) -> str:
    """Return FIPS 140-3 approval status from NIST quantum security level."""
    return "approved" if (nist_level is not None and nist_level >= 1) else "non-approved"

def _make_algorithm_component(
    name: str,
    bom_ref_key: str,
    key_size: int | None = None,
) -> Component:
    primitive, nist_level, classical_level = classify_algorithm(name)
    algo_props = AlgorithmProperties(...)
    return Component(
        name=name,
        type=ComponentType.CRYPTOGRAPHIC_ASSET,
        bom_ref=f"crypto/algorithm/{bom_ref_key}",
        crypto_properties=CryptoProperties(...),
        properties=[Property(name="quirk:fips140-3-status", value=_fips_status(nist_level))],
    )
```

### Pattern 3: Doctor Subcommand Intercept (follows `compliance` pattern exactly)

```python
# Source: run_scan.py lines 223–244 (compliance intercept)
if len(_sys.argv) > 1 and _sys.argv[1] == "doctor":
    from quirk.cli.doctor_cmd import run_doctor
    run_doctor()
    return
```

### Pattern 4: `quirk doctor` Rich Table Output

```python
# Source: init_cmd.py and writer.py Rich usage patterns; verified Table rendering in project venv
from rich.console import Console
from rich.table import Table
import sys

def run_doctor() -> None:
    console = Console()
    table = Table(title="QU.I.R.K. Health Check", show_header=True, header_style="bold")
    table.add_column("Check", style="bold")
    table.add_column("Status")
    
    failed = False
    
    # Non-informational check example
    ok = sys.version_info >= (3, 11)
    if not ok:
        failed = True
    table.add_row("Python environment", "[green][✓][/green]" if ok else "[red][✗][/red]")
    
    # Informational check example (never sets failed)
    table.add_row("Network connectivity", "[yellow][!][/yellow] informational")
    
    console.print(table)
    sys.exit(1 if failed else 0)
```

### Pattern 5: Binary Detection (shutil.which)

```python
# Source: quirk/scanner/container_scanner.py line 54, quirk/util/optional_extra.py line 162
import shutil
nmap_ok = shutil.which("nmap") is not None
syft_ok = shutil.which("syft") is not None
semgrep_ok = shutil.which("semgrep") is not None
```

### Pattern 6: DB Connectivity Probe

```python
# Source: quirk/db.py init_db pattern; config default db_path = "./quirk.db"
import sqlite3
try:
    conn = sqlite3.connect(db_path, timeout=2)
    conn.execute("SELECT 1")
    conn.close()
    db_ok = True
except Exception:
    db_ok = False
```

### Pattern 7: SAML Scanner lxml Migration (DEBT-04)

```python
# Source: CONTEXT.md D-17; verified lxml.etree XMLParser in project venv
# BEFORE (deprecated):
import defusedxml.lxml as _defused_lxml_ET
def _safe_ET_fromstring(xml_bytes):
    return _defused_lxml_ET.fromstring(xml_bytes)

# AFTER:
import lxml.etree as ET
def _safe_ET_fromstring(xml_bytes):
    return ET.fromstring(xml_bytes, parser=ET.XMLParser(resolve_entities=False, no_network=True))
```

### Pattern 8: lab.sh PROFILE_ARGS Snapshot (DEBT-02)

```bash
# Source: CONTEXT.md D-15; lab.sh lines 1–15
# BEFORE (lines 4–14 in lab.sh):
if [[ -f ".env" ]]; then
  set -a
  source ".env"
  set +a
fi
PROFILE_ARGS="${PROFILE_ARGS:-}"

# AFTER:
_PROFILE_ARGS_OVERRIDE="${PROFILE_ARGS:-}"   # snapshot BEFORE source .env
if [[ -f ".env" ]]; then
  set -a
  source ".env"
  set +a
fi
PROFILE_ARGS="${_PROFILE_ARGS_OVERRIDE:-${PROFILE_ARGS:-}}"  # CLI wins over .env
```

### Anti-Patterns to Avoid

- **Do not use `defusedxml.lxml` in new code:** It emits a `DeprecationWarning` ("defusedxml.lxml is no longer supported") as confirmed in project venv. Use `lxml.etree.XMLParser(resolve_entities=False, no_network=True)` directly.
- **Do not set `exit(1)` for informational checks in `quirk doctor`:** Categories 4, 7, and 8 (QRAMM freshness, network connectivity, dashboard process) are informational-only `[!]`. Setting `failed = True` for these would break D-14.
- **Do not add 2013-style `A.x.x` ISO control IDs:** The unit test for COMPLY-12 explicitly rejects them. All ISO controls must use 8.x clause numbering.
- **Do not duplicate `_PHASE_49_VERIFIED` date for new SOC2/ISO entries:** New entries use `_PHASE_52_VERIFIED = "2026-05-05"`, not the Phase 49 date constant.
- **Do not import `risk_engine` from `doctor_cmd.py`:** Circular import risk. Doctor uses `quirk.compliance.status_report()` and `STALENESS_THRESHOLD_DAYS` directly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Terminal rich formatting | Custom ANSI escape codes | `rich.console.Console` + `rich.table.Table` | Already installed; handles color, width, fallback to plain text |
| XML parsing with security flags | Custom entity resolver | `lxml.etree.XMLParser(resolve_entities=False, no_network=True)` | Tested, verified in venv; covers XXE and SSRF vectors |
| Binary availability check | `subprocess.run(binary, ...)` | `shutil.which(binary)` | Already the project-wide pattern (container_scanner.py, optional_extra.py); no subprocess overhead |
| FIPS level mapping | In-line conditionals per call site | `_fips_status(nist_level)` helper | Single touch point; composable; the Context.md D-04 decision mandates it |

---

## DEBT-03 Clarification Finding

**IMPORTANT for planner:** `ports_scanned` and `hosts_scanned` already exist in `run_stats["counts"]` at `run_scan.py:534–535` [VERIFIED: source code read]. The `run-stats-20260401-180937.json` output file does NOT contain these fields — it predates the code addition.

The UAT-3-02 pass notes say: "run-stats ports_scanned: [443,465,...]" suggesting the field was validated at the `run_stats["counts"]["ports_scanned"]` path. The REQUIREMENTS.md DEBT-03 text says: "includes `ports_scanned` (sorted list...) and `hosts_scanned`...closing UAT-3-02 verification gap."

**Likely explanation:** The code at line 534–535 was added but the UAT verification was done against an older artifact that predates the code. The requirement is already implemented in the source but was not verified against the output.

**Planner action required:** The plan for DEBT-03 must include a verification step that runs a scan and confirms `run_stats["counts"]["ports_scanned"]` and `run_stats["counts"]["hosts_scanned"]` appear in the output JSON. If the requirement actually calls for top-level fields (not nested under `counts`), the plan must add them at `run_stats["ports_scanned"]` and `run_stats["hosts_scanned"]` directly in `run_scan.py` before the `write_reports()` call.

---

## Common Pitfalls

### Pitfall 1: ISO Control Version String Exactness
**What goes wrong:** Using `"2022"` alone, `"ISO 27001"` without year, or `"ISO 27001:2013"` as the version string.
**Why it happens:** Muscle memory from older ISO versions; 2013 used `A.x.x` numbering.
**How to avoid:** Unit test explicitly rejects `A.x.x` control IDs (per COMPLY-12). Version field must be exactly `"ISO 27001:2022"`.
**Warning signs:** Test output mentioning `A.` prefix in control IDs.

### Pitfall 2: Doctor Informational vs. Non-Informational Exit Logic
**What goes wrong:** Setting `failed = True` for informational-only checks (QRAMM freshness, network connectivity, dashboard status), causing exit 1 when a checked port isn't in use.
**Why it happens:** The 8-category list looks uniform but D-14 has asymmetric exit semantics.
**How to avoid:** Encode informational status in the `[!]` symbol display only; never set `failed = True` for categories 4, 7, 8.
**Warning signs:** `quirk doctor` exits 1 when run on a system with no nmap and no dashboard running (a normal dev environment).

### Pitfall 3: SAML Fallback Chain Ordering
**What goes wrong:** After DEBT-04 migration, the fallback to `defusedxml.ElementTree` (stdlib path) is lost if the `except ImportError` branch is removed.
**Why it happens:** The current `saml_scanner.py` has a 3-tier import chain: `lxml.etree + defusedxml.lxml` → `defusedxml.ElementTree` → `raise RuntimeError`. After migration, the chain becomes: `lxml.etree` → `defusedxml.ElementTree` → `raise RuntimeError`. The second fallback must be preserved.
**How to avoid:** Keep the `except ImportError` outer block; only replace the `lxml` usage inside the `try` block.
**Warning signs:** 25 SAML tests fail after migration.

### Pitfall 4: COMPLIANCE_MAP Coverage Gap
**What goes wrong:** Adding `_soc2()/_iso()` to some keys but missing others — especially the 4 container-image keys that only have `_pci()` entries (not `_hipaa()`).
**Why it happens:** D-09 says "every key with PCI or HIPAA" — the word "or" requires checking each key individually, not just multi-framework keys.
**How to avoid:** Iterate every key in `COMPLIANCE_MAP` systematically. Keys with only `_fips()` entries (no PCI/HIPAA) also need SOC2/ISO based on D-09's spirit.
**Warning signs:** Unit test asserting `>= 3 CC6.x control IDs` fails because only some keys were extended.

### Pitfall 5: `lab.sh` Variable Shadowing Order
**What goes wrong:** Snapshotting `PROFILE_ARGS` AFTER `source .env` (no change in behavior) or using the wrong restore expression.
**Why it happens:** The bug is that `.env` overwrites the inbound CLI-set value. The fix must capture the value BEFORE `source .env` runs.
**How to avoid:** `_PROFILE_ARGS_OVERRIDE="${PROFILE_ARGS:-}"` must appear on a line before the `if [[ -f ".env" ]]` block.
**Warning signs:** `PROFILE_ARGS="--profile tls" ./lab.sh up` still uses the value from `.env` instead of `--profile tls`.

### Pitfall 6: `Property` Import Source
**What goes wrong:** Importing `Property` from `cyclonedx.model.component` instead of `cyclonedx.model`.
**Why it happens:** `Component` is imported from `cyclonedx.model.component`; instinct says same module.
**How to avoid:** `from cyclonedx.model import Property` — it lives in the top-level `cyclonedx.model` package. Verified in venv.
**Warning signs:** `ImportError: cannot import name 'Property' from 'cyclonedx.model.component'`.

---

## Code Examples

### FIPS status mapping — verified algorithm outputs
```
# [VERIFIED: .venv/bin/python3 classify_algorithm probe 2026-05-05]
AES-256-GCM  nist_level=1  → approved
ml-kem-768   nist_level=3  → approved
RSA          nist_level=0  → non-approved
3DES         nist_level=0  → non-approved
SHA-256      nist_level=0  → non-approved  (classical hash, not PQC-safe)
RC4          nist_level=None → non-approved
MD5          nist_level=None → non-approved
```

### CycloneDX Property constructor — verified in project venv
```python
# [VERIFIED: .venv/bin/python3 cyclonedx API check 2026-05-05]
from cyclonedx.model import Property
p = Property(name="quirk:fips140-3-status", value="approved")
# Component accepts: properties: collections.abc.Iterable[cyclonedx.model.Property] | None = None
```

### defusedxml.lxml deprecation warning — confirmed in project venv
```
# [VERIFIED: .venv/bin/python3 import test 2026-05-05]
DeprecationWarning: defusedxml.lxml is no longer supported and will be removed in a future release.
```

### Rich Table rendering — verified in project venv
```python
# [VERIFIED: .venv/bin/python3 rich 14.3.3 Table render test 2026-05-05]
# Two-column table renders cleanly; unicode symbols [✓] [!] [✗] supported
```

---

## COMPLIANCE_MAP Key Coverage Audit

All 23 COMPLIANCE_MAP keys and their existing framework coverage (for D-09 parity check):

| COMPLIANCE_MAP Key | PCI | HIPAA | FIPS | Needs SOC2 | Needs ISO |
|---|---|---|---|---|---|
| Plaintext HTTP service detected | CC6.7 | CC6.7 | — | ✓ | 8.26 |
| Legacy TLS versions allowed (TLS 1.0/1.1) | CC6.6+CC6.7 | CC6.7 | yes | ✓ | 8.26 |
| Legacy TLS cipher suites accepted | CC6.7 | CC6.7 | yes | ✓ | 8.26 |
| TLS certificate expired | CC6.6 | — | — | ✓ | 8.24 |
| TLS certificate expiring within 30 days | CC6.6 | — | — | ✓ | 8.24 |
| TLS certificate is self-signed | CC6.6 | — | — | ✓ | 8.24 |
| TLS certificate issued by untrusted CA | CC6.6 | — | — | ✓ | 8.24 |
| TLS certificate uses undersized RSA key | CC6.6 | CC6.6 | yes | ✓ | 8.24 |
| TLS certificate uses undersized ECDSA key | CC6.6 | CC6.6 | yes | ✓ | 8.24 |
| TLS certificate uses quantum-vulnerable RSA key | CC6.6 | — | yes | ✓ | 8.24 |
| TLS certificate uses quantum-vulnerable ECDSA key | CC6.6 | — | yes | ✓ | 8.24 |
| STARTTLS downgrade risk on SMTP | CC6.7 | CC6.7 | — | ✓ | 8.26 |
| Weak cipher suite on email TLS endpoint | CC6.7 | CC6.7 | — | ✓ | 8.26 |
| Non-PFS cipher suite on email TLS endpoint | CC6.7 | — | — | ✓ | 8.26 |
| Plaintext Kafka listener detected | CC6.7 | CC6.7 | — | ✓ | 8.26 |
| Plaintext AMQP listener detected | CC6.7 | CC6.7 | — | ✓ | 8.26 |
| Plaintext Redis listener (no auth) | CC6.6+CC6.7 | CC6.7 | — | ✓ | 8.26 |
| Weak cipher suite on broker TLS endpoint | CC6.7 | CC6.7 | — | ✓ | 8.26 |
| End-of-life in container image | CC6.7 | — | yes | ✓ | 8.26 |
| Container image uses quantum-vulnerable crypto library | CC6.6 | — | yes | ✓ | 8.24 |
| Severely outdated Python cryptography package in container image | CC6.7 | — | — | ✓ | 8.26 |
| Outdated Python cryptography package in container image | CC6.7 | — | — | ✓ | 8.26 |
| Outdated pyOpenSSL package in container image | CC6.7 | — | — | ✓ | 8.26 |
| Outdated libgcrypt in container image | CC6.7 | — | — | ✓ | 8.26 |

**Note on container/outdated-package keys:** D-06 maps CC6.7 to cipher/protocol/transport findings and CC6.6 to key/cert/auth findings. Outdated crypto library packages are a deployment concern (cipher capability issue), so CC6.7 applies. "Container image uses quantum-vulnerable crypto library" is a key-size/algorithm concern, so CC6.6 applies.

**ISO 8.28 scope:** Source-code scanner findings are not represented in `COMPLIANCE_MAP` currently (source findings go through `UNMAPPED_TITLES` or do not have a dedicated title key). ISO 8.28 (Secure coding) will only be used if a `SOURCE` finding title is explicitly in `COMPLIANCE_MAP`. If no such keys exist, 8.28 will not appear in Phase 52 output — this is acceptable per scope.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `defusedxml.lxml.fromstring()` | `lxml.etree.fromstring(parser=XMLParser(resolve_entities=False, no_network=True))` | defusedxml 0.8.x deprecation cycle | Same security guarantees; eliminates DeprecationWarning |
| ISO 27001:2013 `A.x.x` numbering | ISO 27001:2022 `8.x` clause numbering | ISO published 2022 revision | 2022 restructured Annex A into Clause 6 and Annex A; cryptographic controls are now in 8.24/8.26/8.28 |
| SOC2 Type I/II (2016 criteria) | SOC2 2017 Trust Services Criteria (TSC) revision | AICPA 2017 TSC revision | CC6.x is the current common criteria numbering; use `"2017-rev"` version string |

**Deprecated/outdated:**
- `defusedxml.lxml`: deprecated, to be removed in a future defusedxml release. Direct `lxml.etree.XMLParser` with security flags is the replacement.
- ISO 27001:2013 `A.14.1.3` / `A.10.1.1` style controls: replaced by ISO 27001:2022 `8.26` / `8.24`. Unit test will reject 2013-style IDs.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | DEBT-03 fields (`ports_scanned`/`hosts_scanned`) are already present in the source code at `run_stats["counts"]` but the UAT artifact predates this code addition | DEBT-03 Clarification Finding | If the requirement means top-level `run_stats["ports_scanned"]` (not nested), the plan needs an additional dict assignment before `write_reports()` |
| A2 | ISO 8.28 (Secure coding) will not appear in Phase 52 COMPLIANCE_MAP output because no SOURCE finding titles are currently mapped | COMPLIANCE_MAP Coverage Audit | If a SOURCE finding title exists in COMPLIANCE_MAP, 8.28 should be applied per D-08 |
| A3 | AICPA TSC source URL will be the public trust services criteria page | Standard Stack | If AICPA changes their URL structure, the `source_url` will be a dead link on verification |

---

## Open Questions

1. **DEBT-03 exact placement**
   - What we know: `run_stats["counts"]["ports_scanned"]` and `run_stats["counts"]["hosts_scanned"]` already exist in the source code (run_scan.py:534–535). A matching run-stats JSON from April 2026 does NOT have these fields (predates the code).
   - What's unclear: Does REQUIREMENTS.md DEBT-03 require them at `run_stats["ports_scanned"]` (top-level) or is `run_stats["counts"]["ports_scanned"]` (nested) the correct location? The UAT-3-02 note references "run-stats ports_scanned" without nesting indication.
   - Recommendation: Plan should verify that a fresh scan produces these fields in the output JSON. If already present under `counts`, DEBT-03 may be a verification-only task, not a code task.

2. **`quirk doctor` config.yaml path**
   - What we know: Doctor needs to validate that `config.yaml` parses cleanly (D-14 category 6). The default path is `"./config.yaml"` (from `quirk init`).
   - What's unclear: Should doctor look for `config.yaml` in the current working directory only, or accept a `--config` flag? D-12 says no format flag needed, but config location may vary.
   - Recommendation: Default to `./config.yaml` with graceful `[!]` informational if no config file found (not a hard failure); leave `--config` flag for future.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (project venv) | All tracks | ✓ | 3.14.4 | — |
| cyclonedx-python-lib | COMPLY-10 (CBOM Property) | ✓ | >=11.7.0 [pyproject.toml] | — |
| rich | DOCS-05 (doctor CLI) | ✓ | 14.3.3 | — |
| lxml | DEBT-04 (saml_scanner migration) | ✓ | 6.0.1 (in project venv) | defusedxml.ElementTree fallback in scanner |
| defusedxml | DEBT-04 (fallback chain) | ✓ | 0.7.1 | — |
| shutil (stdlib) | DOCS-05 (binary detection) | ✓ | stdlib | — |
| socket (stdlib) | DOCS-05 (network probe) | ✓ | stdlib | — |
| sqlite3 (stdlib) | DOCS-05 (DB probe) | ✓ | stdlib | — |
| nmap | DOCS-05 (binary check, informational) | not checked at plan time | — | shutil.which returns None → [✗] |
| syft | DOCS-05 (binary check, informational) | not checked at plan time | — | shutil.which returns None → [✗] |
| semgrep | DOCS-05 (binary check, informational) | not checked at plan time | — | shutil.which returns None → [✗] |

**Missing dependencies with no fallback:** None — all required libraries are installed.

**Missing dependencies with fallback:** nmap/syft/semgrep may not be installed on the dev machine; this is expected and `quirk doctor` displays `[✗]` but exits 1 only if non-informational check fails (scanner binaries IS a non-informational check per D-14 category 2).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (pyproject.toml `[tool.pytest.ini_options]`) |
| Config file | pyproject.toml |
| Quick run command | `.venv/bin/python3 -m pytest tests/test_compliance_schema.py tests/test_cbom_builder.py tests/test_saml_scanner.py -q` |
| Full suite command | `.venv/bin/python3 -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMPLY-10 | Every algo component has `quirk:fips140-3-status` property | unit | `.venv/bin/python3 -m pytest tests/test_cbom_builder.py -k fips -x` | ❌ Wave 0 |
| COMPLY-10 | `_fips_status()` mapping: nist_level>=1→approved, 0→non-approved, None→non-approved | unit | `.venv/bin/python3 -m pytest tests/test_cbom_builder.py -k fips_status -x` | ❌ Wave 0 |
| COMPLY-11 | SOC2 CC6.x entries present in COMPLIANCE_MAP (≥ 3 CC6.x control IDs) | unit | `.venv/bin/python3 -m pytest tests/test_compliance_schema.py -x` | ✅ (will catch schema errors; needs SOC2-specific assert) |
| COMPLY-12 | ISO 27001:2022 entries present; no `A.x.x` control IDs | unit | `.venv/bin/python3 -m pytest tests/test_compliance_schema.py -x` | ✅ (needs ISO-specific assert added) |
| COMPLY-12 | `iso()` version field equals `"ISO 27001:2022"` exactly | unit | `.venv/bin/python3 -m pytest tests/test_compliance_schema.py -x` | ✅ (needs version assert added) |
| DOCS-05 | `quirk doctor` exits 0 when all checks pass | unit | `.venv/bin/python3 -m pytest tests/test_doctor_cmd.py -x` | ❌ Wave 0 |
| DOCS-05 | `quirk doctor` exits 1 when a non-informational check fails | unit | `.venv/bin/python3 -m pytest tests/test_doctor_cmd.py -k exit_1 -x` | ❌ Wave 0 |
| DOCS-05 | Informational checks (QRAMM/network/dashboard) never set exit 1 | unit | `.venv/bin/python3 -m pytest tests/test_doctor_cmd.py -k informational -x` | ❌ Wave 0 |
| DEBT-02 | lab.sh PROFILE_ARGS snapshot — manual verification | manual | `PROFILE_ARGS="--profile tls" ./quantum-chaos-enterprise-lab/lab.sh up --dry-run 2>&1 \| grep "profile tls"` | N/A |
| DEBT-03 | run-stats JSON contains `ports_scanned`+`hosts_scanned` fields | integration | `.venv/bin/python3 -m pytest tests/test_writer.py -k ports_scanned -x` | ❌ Wave 0 (or verify-only) |
| DEBT-04 | 25 SAML tests pass GREEN after migration | unit | `.venv/bin/python3 -m pytest tests/test_saml_scanner.py -q` | ✅ (all 27 test functions) |
| DEBT-04 | No `defusedxml.lxml` DeprecationWarning emitted | unit | `.venv/bin/python3 -W error::DeprecationWarning -m pytest tests/test_saml_scanner.py -q` | ✅ (after migration) |

### Sampling Rate
- **Per task commit:** `.venv/bin/python3 -m pytest tests/test_compliance_schema.py tests/test_cbom_builder.py tests/test_saml_scanner.py -q`
- **Per wave merge:** `.venv/bin/python3 -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_cbom_builder.py` — add `test_fips_status_helper()` and `test_algorithm_component_has_fips_property()` test functions
- [ ] `tests/test_compliance_schema.py` — add `test_soc2_entries_present()`, `test_iso_entries_present()`, `test_iso_rejects_legacy_control_ids()`, `test_iso_version_string()` test functions
- [ ] `tests/test_doctor_cmd.py` — new file; covers `run_doctor()` with mock checks for all 8 categories and exit code semantics

*(No new test files needed for DEBT-02 or DEBT-04 — SAML tests cover DEBT-04; DEBT-02 is bash-only.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (DEBT-04) | `lxml.etree.XMLParser(resolve_entities=False, no_network=True)` — prevents XXE injection |
| V6 Cryptography | yes (COMPLY-10) | CycloneDX Property annotation — annotation layer only, no new crypto logic |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XXE injection via SAML metadata XML | Tampering | `lxml.etree.XMLParser(resolve_entities=False, no_network=True)` — DEBT-04 fix directly addresses this |
| SSRF via XML external entities in SAML | Elevation of Privilege | `no_network=True` parser flag — prevents outbound network calls during XML parse |
| Compliance mapping staleness (stale frameworks used for audit) | Information Disclosure | `STALENESS_THRESHOLD_DAYS` + freshness test; doctor check category 3 (non-informational) |

---

## Sources

### Primary (HIGH confidence)
- `quirk/compliance/__init__.py` — existing `_pci()/_hipaa()/_fips()` builder pattern, `status_report()`, `STALENESS_THRESHOLD_DAYS`, `TITLE_PREFIX_ALIASES`, full COMPLIANCE_MAP key set [VERIFIED: file read]
- `quirk/cbom/builder.py` — `_make_algorithm_component()` signature, `classify_algorithm()` call site, `Component` constructor parameters [VERIFIED: file read]
- `quirk/cbom/classifier.py` — `classify_algorithm()` return signature and nist_level semantics [VERIFIED: file read]
- `run_scan.py:176–244` — subcommand intercept pattern for `init`, `serve`, `compliance` [VERIFIED: file read]
- `run_scan.py:529–536` — `run_stats["counts"]` assembly including existing ports_scanned/hosts_scanned fields [VERIFIED: file read]
- `quantum-chaos-enterprise-lab/lab.sh:1–15` — PROFILE_ARGS variable lifecycle [VERIFIED: file read]
- `quirk/scanner/saml_scanner.py:1–30` — current `defusedxml.lxml` import pattern [VERIFIED: file read]
- `quirk/cli/init_cmd.py` — file-per-subcommand pattern, Rich Console usage [VERIFIED: file read]
- cyclonedx-python-lib `Component.__init__` signature — `properties: Iterable[Property] | None` kwarg confirmed [VERIFIED: Python introspection in project venv]
- cyclonedx `Property` model — `from cyclonedx.model import Property` confirmed [VERIFIED: project venv import]
- lxml `XMLParser(resolve_entities=False, no_network=True)` — working in project venv [VERIFIED: .venv/bin/python3 test]
- defusedxml.lxml DeprecationWarning — confirmed emitted in project venv [VERIFIED: .venv/bin/python3 import test]
- rich 14.3.3 `Table` rendering — verified two-column output [VERIFIED: .venv/bin/python3 render test]
- `tests/test_compliance_schema.py` — existing schema test patterns (required keys, ISO date, https URL) [VERIFIED: file read]
- `tests/test_saml_scanner.py` — 27 test functions confirmed GREEN [VERIFIED: pytest run 60 passed]

### Secondary (MEDIUM confidence)
- ISO 27001:2022 Annex A restructure — 8.x clause numbering for cryptographic controls; 8.24 (Cryptography), 8.26 (Application security), 8.28 (Secure coding) [ASSUMED based on training knowledge — CONTEXT.md D-08 locked these assignments]
- AICPA SOC2 TSC 2017 revision — CC6.6 (Logical access controls) and CC6.7 (Transmission encryption) as the cryptography-relevant CC6.x controls [ASSUMED based on training knowledge — CONTEXT.md D-06 locked these assignments]

### Tertiary (LOW confidence)
- None — all critical claims verified in project codebase or venv.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in project venv with version probes
- Architecture: HIGH — all file locations and function signatures read directly
- Pitfalls: HIGH — most derived from direct code inspection; DEBT-03 ambiguity is flagged as open question
- Compliance control assignments: MEDIUM — SOC2/ISO control ID assignments are locked in CONTEXT.md D-06/D-08; training knowledge supports them but source URLs not fetched

**Research date:** 2026-05-05
**Valid until:** 2026-06-05 (stable Python/cyclonedx ecosystem)
