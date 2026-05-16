# Phase 52: Compliance Uplift & Health Check - Pattern Map

**Mapped:** 2026-05-05
**Files analyzed:** 7 new/modified files
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/compliance/__init__.py` | service/library | transform | `quirk/compliance/__init__.py` (self — extend in place) | exact |
| `quirk/cbom/builder.py` | service/library | transform | `quirk/cbom/builder.py` (self — extend `_make_algorithm_component`) | exact |
| `quirk/cli/doctor_cmd.py` | CLI command | request-response | `quirk/cli/init_cmd.py` | role-match |
| `run_scan.py` (subcommand intercept + run_stats) | entrypoint | request-response | `run_scan.py` lines 176–244 (existing intercepts) | exact |
| `quirk/scanner/saml_scanner.py` | scanner | request-response | `quirk/scanner/saml_scanner.py` (self — import block only) | exact |
| `quantum-chaos-enterprise-lab/lab.sh` | config/tooling | batch | `quantum-chaos-enterprise-lab/lab.sh` lines 1–15 (self) | exact |
| `tests/test_compliance_schema.py` | test | transform | `tests/test_compliance_schema.py` (self — extend) | exact |
| `tests/test_cbom_builder.py` | test | transform | `tests/test_cbom_builder.py` (self — extend) | exact |
| `tests/test_doctor_cmd.py` | test | request-response | `tests/test_compliance_schema.py` (structural model) | role-match |

---

## Pattern Assignments

### `quirk/compliance/__init__.py` — _soc2() / _iso() helpers + COMPLIANCE_MAP extensions (COMPLY-11/12)

**Analog:** `quirk/compliance/__init__.py` — existing `_pci()/_hipaa()/_fips()` builder functions.

**Existing builder helper pattern** (lines 39–66):
```python
_PHASE_49_VERIFIED: str = "2026-05-05"
_PCI_4_0_1_URL = "https://docs-prv.pcisecuritystandards.org/PCI%20DSS/Standard/PCI-DSS-v4_0_1.pdf"
_HIPAA_164_312_URL = (
    "https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/"
    "subpart-C/section-164.312"
)
_FIPS_140_3_URL = "https://csrc.nist.gov/pubs/fips/140-3/final"

def _pci(control: str) -> Dict[str, Any]:
    return {
        "framework": "PCI-DSS 4.0.1",
        "control": control,
        "version": "4.0.1",
        "last_verified": _PHASE_49_VERIFIED,
        "source_url": _PCI_4_0_1_URL,
    }

def _hipaa(control: str) -> Dict[str, Any]:
    return {
        "framework": "HIPAA 45 CFR",
        "control": control,
        "version": "2024-rev",
        "last_verified": _PHASE_49_VERIFIED,
        "source_url": _HIPAA_164_312_URL,
    }

def _fips(control: str) -> Dict[str, Any]:
    return {
        "framework": "FIPS 140-3",
        "control": control,
        "version": "FIPS 140-3",
        "last_verified": _PHASE_49_VERIFIED,
        "source_url": _FIPS_140_3_URL,
    }
```

**New `_soc2()` and `_iso()` — copy this exact shape** (add after `_fips()`, before `TITLE_PREFIX_ALIASES`):
```python
# Phase 52: _PHASE_49_VERIFIED date is intentionally reused for Phase 49 entries.
# Phase 52 entries use _PHASE_52_VERIFIED.
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

**COMPLIANCE_MAP extension pattern** (lines 101–183) — every list value gains `_soc2()` and `_iso()` entries appended. Example for one key:
```python
"Plaintext HTTP service detected": [
    _pci("4.2.1"), _hipaa("§164.312(e)(1)"),   # existing — DO NOT REMOVE
    _soc2("CC6.7"), _iso("8.26"),               # NEW — Phase 52 D-06/D-08
],
```

**`status_report()` function** (lines 207–234) — no changes needed. Doctor calls this directly.

**`__all__` extension** (line 237–243) — no changes needed; `status_report` already exported.

---

### `quirk/cbom/builder.py` — `_fips_status()` helper + `_make_algorithm_component()` property annotation (COMPLY-10)

**Analog:** `quirk/cbom/builder.py` — `_make_algorithm_component()` at lines 273–296.

**Existing imports block** (lines 1–34) — add `Property` import:
```python
from cyclonedx.model import Property   # ADD — Property lives in cyclonedx.model, NOT cyclonedx.model.component
# (cyclonedx.model.component already imported on line 21 for Component, ComponentType)
```

**Existing `_make_algorithm_component()` signature and body** (lines 273–296):
```python
def _make_algorithm_component(
    name: str,
    bom_ref_key: str,
    key_size: int | None = None,
) -> Component:
    """Build a CRYPTOGRAPHIC_ASSET/ALGORITHM Component."""
    primitive, nist_level, classical_level = classify_algorithm(name)

    algo_props = AlgorithmProperties(
        primitive=primitive,
        nist_quantum_security_level=nist_level,
        classical_security_level=classical_level,
        execution_environment=CryptoExecutionEnvironment.SOFTWARE_PLAIN_RAM,
        parameter_set_identifier=str(key_size) if key_size is not None else None,
    )
    return Component(
        name=name,
        type=ComponentType.CRYPTOGRAPHIC_ASSET,
        bom_ref=f"crypto/algorithm/{bom_ref_key}",
        crypto_properties=CryptoProperties(
            asset_type=CryptoAssetType.ALGORITHM,
            algorithm_properties=algo_props,
        ),
    )
```

**New `_fips_status()` helper — add immediately before `_make_algorithm_component()`:**
```python
def _fips_status(nist_level: int | None) -> str:
    """Return FIPS 140-3 approval status from NIST quantum security level.

    nist_level >= 1  → "approved"  (quantum-safe or NIST-approved classical)
    nist_level == 0  → "non-approved"  (quantum-vulnerable)
    nist_level is None → "non-approved" (unknown algorithm)
    """
    return "approved" if (nist_level is not None and nist_level >= 1) else "non-approved"
```

**Modified `Component(...)` call — add `properties` kwarg:**
```python
    return Component(
        name=name,
        type=ComponentType.CRYPTOGRAPHIC_ASSET,
        bom_ref=f"crypto/algorithm/{bom_ref_key}",
        crypto_properties=CryptoProperties(
            asset_type=CryptoAssetType.ALGORITHM,
            algorithm_properties=algo_props,
        ),
        properties=[Property(name="quirk:fips140-3-status", value=_fips_status(nist_level))],
    )
```

---

### `quirk/cli/doctor_cmd.py` — NEW FILE (DOCS-05)

**Analog:** `quirk/cli/init_cmd.py` — file-per-subcommand pattern, Rich Console import style.

**init_cmd.py import and Rich pattern** (lines 1–19):
```python
"""quirk init — generate a starter config.yaml from the bundled template."""
import os
import shutil
from importlib.resources import files  # Python 3.10+

def run_init(output_path: str) -> None:
    try:
        from rich.console import Console
        console = Console()
        _info = lambda msg: console.print(f"[bold #3b9dff]QU.I.R.K.[/] {msg}")
        _warn = lambda msg: console.print(f"[bold yellow]WARNING:[/] {msg}")
    except ImportError:
        _info = lambda msg: print(f"QU.I.R.K. {msg}")
        _warn = lambda msg: print(f"WARNING: {msg}")
```

**`doctor_cmd.py` must follow this module shape:**
```python
"""quirk doctor — system health check for QU.I.R.K. operator environments."""
import shutil
import socket
import sqlite3
import sys
import yaml

from rich.console import Console
from rich.table import Table


def run_doctor() -> None:
    console = Console()
    table = Table(title="QU.I.R.K. Health Check", show_header=True, header_style="bold")
    table.add_column("Check", style="bold")
    table.add_column("Status")

    failed = False

    # NON-INFORMATIONAL: Python version (category 1)
    ok = sys.version_info >= (3, 11)
    if not ok:
        failed = True
    table.add_row("Python environment", "[green][✓][/green]" if ok else "[red][✗] Python < 3.11[/red]")

    # NON-INFORMATIONAL: scanner binaries (category 2)
    for binary in ("nmap", "syft", "semgrep"):
        bin_ok = shutil.which(binary) is not None
        if not bin_ok:
            failed = True
        table.add_row(f"Binary: {binary}", "[green][✓][/green]" if bin_ok else f"[red][✗] {binary} not found[/red]")

    # NON-INFORMATIONAL: compliance framework freshness (category 3)
    # (see Shared Patterns section for staleness check pattern)

    # INFORMATIONAL ONLY — never sets failed (categories 4, 7, 8)
    table.add_row("QRAMM freshness", "[yellow][!] QRAMM module not installed — run Phase 51 first[/yellow]")

    console.print(table)
    sys.exit(1 if failed else 0)
```

**Binary detection analog** — `quirk/scanner/container_scanner.py` line ~54 and `quirk/util/optional_extra.py` line ~162:
```python
import shutil
nmap_ok = shutil.which("nmap") is not None
```

**DB probe pattern** (from `quirk/db.py` init pattern):
```python
import sqlite3
try:
    conn = sqlite3.connect(db_path, timeout=2)
    conn.execute("SELECT 1")
    conn.close()
    db_ok = True
except Exception:
    db_ok = False
```

**Network probe pattern** (stdlib socket):
```python
import socket
try:
    socket.create_connection(("8.8.8.8", 53), timeout=2).close()
    net_ok = True
except OSError:
    net_ok = False
```

**Dashboard port probe** (informational, never sets failed):
```python
try:
    socket.create_connection(("127.0.0.1", 8512), timeout=1).close()
    dash_running = True
except OSError:
    dash_running = False
# table.add_row("Dashboard process", "[yellow][!] not running[/yellow]") — informational only
```

---

### `run_scan.py` — doctor subcommand intercept + DEBT-03 run_stats fields

**Analog:** `run_scan.py` lines 194–244 — `serve` and `compliance` subcommand intercept blocks.

**Existing subcommand intercept pattern** (lines 194–244):
```python
# --- serve subcommand: intercept before scan argparse to avoid conflicts ---
if len(_sys.argv) > 1 and _sys.argv[1] == "serve":
    serve_parser = argparse.ArgumentParser(
        prog="quirk serve",
        description="Start the QU.I.R.K. web dashboard",
    )
    # ... add_argument calls ...
    serve_args = serve_parser.parse_args(_sys.argv[2:])
    from quirk.dashboard.server import serve as _serve
    _serve(port=serve_args.port, host=serve_args.host, no_open=serve_args.no_open)
    return

# --- compliance subcommand: intercept before scan argparse (Phase 49 D-05) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "compliance":
    # ... argparse setup ...
    if comp_args.action == "status":
        from quirk.compliance import status_report
        status_report(format=comp_args.format)
    return
```

**New doctor intercept — insert after compliance block (before line 246):**
```python
# --- doctor subcommand: intercept before scan argparse (Phase 52 DOCS-05) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "doctor":
    from quirk.cli.doctor_cmd import run_doctor
    run_doctor()
    return
```

**Existing run_stats counts** (lines 529–536) — DEBT-03 target:
```python
run_stats["counts"] = {
    "targets_total": len(targets),
    "tls_candidates": len(tls_targets),
    "ssh_candidates": len(ssh_targets),
    "inventory_other": len(inventory_endpoints),
    "hosts_scanned": sorted({h for h, _ in targets}),   # already exists
    "ports_scanned": sorted({p for _, p in targets}),    # already exists
}
```

**DEBT-03 verification task:** Run a fresh scan and confirm `run_stats["counts"]["ports_scanned"]` appears in `run-stats-*.json`. If REQUIREMENTS.md demands top-level fields (not nested under `counts`), also add:
```python
run_stats["ports_scanned"] = run_stats["counts"]["ports_scanned"]
run_stats["hosts_scanned"] = run_stats["counts"]["hosts_scanned"]
```
Place this immediately after the `run_stats["counts"] = {...}` block (after line 536).

---

### `quirk/scanner/saml_scanner.py` — DEBT-04 lxml migration (import block only)

**Analog:** `quirk/scanner/saml_scanner.py` lines 1–20 — current import block (the migration target).

**Current import block** (lines 4–20):
```python
try:
    import lxml.etree as ET
    import defusedxml.lxml as _defused_lxml_ET
    def _safe_ET_fromstring(xml_bytes):  # noqa: E306
        return _defused_lxml_ET.fromstring(xml_bytes)
    LXML_AVAILABLE = True
except ImportError:
    ET = None  # type: ignore[assignment]
    try:
        import defusedxml.ElementTree as _defused_stdlib_ET
        def _safe_ET_fromstring(xml_bytes):  # noqa: E306
            return _defused_stdlib_ET.fromstring(xml_bytes)
        LXML_AVAILABLE = True
    except ImportError:
        def _safe_ET_fromstring(xml_bytes):  # noqa: E306
            raise RuntimeError("defusedxml is not installed — SAML parsing unavailable")
        LXML_AVAILABLE = False
```

**Replacement import block — preserve 3-tier fallback chain structure:**
```python
try:
    import lxml.etree as ET
    def _safe_ET_fromstring(xml_bytes):  # noqa: E306
        return ET.fromstring(xml_bytes, parser=ET.XMLParser(resolve_entities=False, no_network=True))
    LXML_AVAILABLE = True
except ImportError:
    ET = None  # type: ignore[assignment]
    try:
        import defusedxml.ElementTree as _defused_stdlib_ET
        def _safe_ET_fromstring(xml_bytes):  # noqa: E306
            return _defused_stdlib_ET.fromstring(xml_bytes)
        LXML_AVAILABLE = True
    except ImportError:
        def _safe_ET_fromstring(xml_bytes):  # noqa: E306
            raise RuntimeError("defusedxml is not installed — SAML parsing unavailable")
        LXML_AVAILABLE = False
```

The only change is within the first `try` block: remove `import defusedxml.lxml as _defused_lxml_ET` and replace `_defused_lxml_ET.fromstring(xml_bytes)` with `ET.fromstring(xml_bytes, parser=ET.XMLParser(resolve_entities=False, no_network=True))`. The outer `except ImportError` chain is preserved exactly.

---

### `quantum-chaos-enterprise-lab/lab.sh` — DEBT-02 PROFILE_ARGS snapshot

**Analog:** `quantum-chaos-enterprise-lab/lab.sh` lines 1–14 — current PROFILE_ARGS lifecycle.

**Current sequence** (lines 1–14):
```bash
#!/usr/bin/env bash
set -euo pipefail

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

# ---- Config ----
PROJECT_NAME="${PROJECT_NAME:-chaoslab}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
PROFILE_ARGS="${PROFILE_ARGS:-}"   # e.g. "--profile identity" or "--profile core --profile identity"
```

**Fixed sequence — snapshot before `source .env`:**
```bash
#!/usr/bin/env bash
set -euo pipefail

_PROFILE_ARGS_OVERRIDE="${PROFILE_ARGS:-}"   # snapshot CLI value BEFORE .env can overwrite it

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

# ---- Config ----
PROJECT_NAME="${PROJECT_NAME:-chaoslab}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
PROFILE_ARGS="${_PROFILE_ARGS_OVERRIDE:-${PROFILE_ARGS:-}}"   # CLI wins over .env
```

The two new lines are: one before the `if [[ -f ".env" ]]` block (snapshot), and the `PROFILE_ARGS=` assignment on line 14 changes from `"${PROFILE_ARGS:-}"` to `"${_PROFILE_ARGS_OVERRIDE:-${PROFILE_ARGS:-}}"`.

---

### `tests/test_compliance_schema.py` — extend with SOC2/ISO assertions (COMPLY-11/12)

**Analog:** `tests/test_compliance_schema.py` — existing test pattern at lines 22–65.

**Existing test structure to copy:**
```python
def test_every_entry_has_required_keys():
    from quirk.compliance import COMPLIANCE_MAP
    offenders: list[tuple[str, set[str]]] = []
    for title, entries in COMPLIANCE_MAP.items():
        for entry in entries:
            missing = _REQUIRED - set(entry.keys())
            if missing:
                offenders.append((title, missing))
    assert not offenders, (
        f"Compliance entries missing required keys: {offenders}. "
        f"Each entry must include {sorted(_REQUIRED)}."
    )
```

**New test functions to add:**
```python
def test_soc2_entries_present():
    """COMPLY-11: COMPLIANCE_MAP must have >= 3 SOC2 CC6.x control IDs."""
    from quirk.compliance import COMPLIANCE_MAP
    cc6_controls = [
        entry["control"]
        for entries in COMPLIANCE_MAP.values()
        for entry in entries
        if entry.get("framework") == "SOC2 CC" and entry.get("control", "").startswith("CC6.")
    ]
    assert len(cc6_controls) >= 3, (
        f"Expected >= 3 SOC2 CC6.x control IDs, got {len(cc6_controls)}: {cc6_controls}"
    )


def test_iso_entries_present():
    """COMPLY-12: COMPLIANCE_MAP must have ISO 27001:2022 entries using 8.x clause numbering."""
    from quirk.compliance import COMPLIANCE_MAP
    iso_controls = [
        entry["control"]
        for entries in COMPLIANCE_MAP.values()
        for entry in entries
        if entry.get("framework") == "ISO 27001:2022"
    ]
    assert len(iso_controls) >= 3, (
        f"Expected >= 3 ISO 27001:2022 entries, got {len(iso_controls)}"
    )


def test_iso_rejects_legacy_control_ids():
    """COMPLY-12: No ISO 27001:2013-style A.x.x control IDs allowed."""
    from quirk.compliance import COMPLIANCE_MAP
    offenders = [
        (title, entry["control"])
        for title, entries in COMPLIANCE_MAP.items()
        for entry in entries
        if entry.get("framework") == "ISO 27001:2022" and entry.get("control", "").startswith("A.")
    ]
    assert not offenders, (
        f"Legacy ISO 27001:2013 A.x.x control IDs found: {offenders}. "
        f"Use 8.x clause numbering (ISO 27001:2022)."
    )


def test_iso_version_string_exact():
    """COMPLY-12: ISO version field must be exactly 'ISO 27001:2022'."""
    from quirk.compliance import COMPLIANCE_MAP
    offenders = [
        (title, entry["version"])
        for title, entries in COMPLIANCE_MAP.items()
        for entry in entries
        if entry.get("framework") == "ISO 27001:2022" and entry.get("version") != "ISO 27001:2022"
    ]
    assert not offenders, (
        f"ISO version field not exactly 'ISO 27001:2022': {offenders}"
    )
```

---

### `tests/test_cbom_builder.py` — extend with FIPS annotation assertions (COMPLY-10)

**Analog:** `tests/test_cbom_builder.py` lines 1–38 — import structure and `_tls_endpoint()` fixture.

**Existing import block** (lines 1–18):
```python
from __future__ import annotations
import json
import pytest
from quirk.models import CryptoEndpoint
from quirk.cbom.builder import build_cbom
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.model.crypto import CryptoAssetType, ProtocolPropertiesType
```

**New test functions to add:**
```python
def test_fips_status_helper():
    """COMPLY-10: _fips_status() maps nist_level correctly."""
    from quirk.cbom.builder import _fips_status
    assert _fips_status(1) == "approved"
    assert _fips_status(3) == "approved"
    assert _fips_status(0) == "non-approved"
    assert _fips_status(None) == "non-approved"


def test_algorithm_component_has_fips_property():
    """COMPLY-10: Every algo component built by build_cbom has quirk:fips140-3-status property."""
    ep = _tls_endpoint()  # uses existing fixture from test file
    bom = build_cbom([ep])
    algo_components = [
        c for c in bom.components
        if hasattr(c, "crypto_properties")
        and c.crypto_properties is not None
        and c.crypto_properties.asset_type is not None
        and c.crypto_properties.asset_type.value == "algorithm"
    ]
    assert algo_components, "Expected at least one algorithm component in CBOM"
    for comp in algo_components:
        prop_names = {p.name for p in (comp.properties or [])}
        assert "quirk:fips140-3-status" in prop_names, (
            f"Algorithm component '{comp.name}' missing quirk:fips140-3-status property"
        )
        fips_val = next(p.value for p in comp.properties if p.name == "quirk:fips140-3-status")
        assert fips_val in ("approved", "non-approved"), (
            f"quirk:fips140-3-status must be 'approved' or 'non-approved', got '{fips_val}'"
        )
```

---

### `tests/test_doctor_cmd.py` — NEW FILE (DOCS-05 test coverage)

**Analog:** `tests/test_compliance_schema.py` — module import + assertion style; `tests/test_cbom_builder.py` — pytest fixture pattern.

**New test file structure:**
```python
"""Phase 52 DOCS-05: Tests for quirk.cli.doctor_cmd.run_doctor() health check."""
from __future__ import annotations
import sys
import pytest
from unittest import mock


def test_doctor_exits_0_all_pass(monkeypatch):
    """run_doctor() exits 0 when all non-informational checks pass."""
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/" + x)
    monkeypatch.setattr("sys.version_info", (3, 11, 0))
    # patch sqlite3 and compliance checks to return healthy
    with mock.patch("sqlite3.connect") as mock_conn:
        mock_conn.return_value.__enter__ = lambda s: s
        mock_conn.return_value.execute = lambda q: None
        mock_conn.return_value.close = lambda: None
        with pytest.raises(SystemExit) as exc:
            from quirk.cli.doctor_cmd import run_doctor
            run_doctor()
    assert exc.value.code == 0


def test_doctor_exits_1_missing_binary(monkeypatch):
    """run_doctor() exits 1 when a required binary is missing."""
    monkeypatch.setattr("shutil.which", lambda x: None)  # all binaries absent
    with pytest.raises(SystemExit) as exc:
        from quirk.cli.doctor_cmd import run_doctor
        run_doctor()
    assert exc.value.code == 1


def test_informational_checks_never_exit_1(monkeypatch):
    """Categories 4 (QRAMM), 7 (network), 8 (dashboard) are informational — never cause exit 1."""
    # All non-informational checks pass; network + dashboard + QRAMM fail
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/" + x)
    # network probe fails
    with mock.patch("socket.create_connection", side_effect=OSError("no network")):
        with pytest.raises(SystemExit) as exc:
            from quirk.cli.doctor_cmd import run_doctor
            run_doctor()
    # Should still be 0 because only informational checks failed
    assert exc.value.code == 0
```

---

## Shared Patterns

### compliance builder helper shape (5 keys)
**Source:** `quirk/compliance/__init__.py` lines 39–66
**Apply to:** `_soc2()` and `_iso()` in `quirk/compliance/__init__.py`

Every compliance builder returns exactly these 5 keys: `framework`, `control`, `version`, `last_verified`, `source_url`. No additions, no omissions.

---

### `status_report()` reuse for doctor freshness check
**Source:** `quirk/compliance/__init__.py` lines 207–234
**Apply to:** `quirk/cli/doctor_cmd.py` category 3 (compliance framework freshness)

```python
from quirk.compliance import STALENESS_THRESHOLD_DAYS, COMPLIANCE_MAP
import datetime

def _compliance_is_fresh() -> bool:
    today = datetime.date.today()
    for entries in COMPLIANCE_MAP.values():
        for e in entries:
            try:
                lv = datetime.date.fromisoformat(e["last_verified"])
                if (today - lv).days > STALENESS_THRESHOLD_DAYS:
                    return False
            except (KeyError, ValueError):
                return False
    return True
```

Do NOT import `risk_engine` from `doctor_cmd.py` — circular import risk (RESEARCH.md anti-pattern).

---

### Rich Console + Table rendering
**Source:** `quirk/cli/init_cmd.py` lines 12–19 (Console import); `quirk/reports/writer.py` (Table usage)
**Apply to:** `quirk/cli/doctor_cmd.py`

```python
from rich.console import Console
from rich.table import Table

console = Console()
table = Table(title="QU.I.R.K. Health Check", show_header=True, header_style="bold")
table.add_column("Check", style="bold")
table.add_column("Status")
# table.add_row(label, "[green][✓][/green]" | "[red][✗] reason[/red]" | "[yellow][!] reason[/yellow]")
console.print(table)
```

---

### Subcommand intercept pattern
**Source:** `run_scan.py` lines 176–244
**Apply to:** `run_scan.py` doctor intercept block

All intercepts follow the same pattern:
1. `if len(_sys.argv) > 1 and _sys.argv[1] == "<cmd>":` — before main `argparse.ArgumentParser` at line 246
2. Optional local `argparse.ArgumentParser` for subcommand args (doctor needs none)
3. `from quirk.cli.<cmd>_cmd import run_<cmd>`
4. `run_<cmd>(...)`
5. `return`

---

### Phase-verified date constant pattern
**Source:** `quirk/compliance/__init__.py` line 26 — `_PHASE_49_VERIFIED: str = "2026-05-05"`
**Apply to:** `quirk/compliance/__init__.py` Phase 52 additions

Add `_PHASE_52_VERIFIED: str = "2026-05-05"` as a module-level constant. Use it in `_soc2()` and `_iso()` `last_verified` fields. Do NOT reuse `_PHASE_49_VERIFIED` for new Phase 52 entries.

---

### Test assertion style
**Source:** `tests/test_compliance_schema.py` lines 22–65
**Apply to:** All new test functions

Pattern: collect offenders into a list, `assert not offenders, f"<descriptive message>: {offenders}"`. This surfaces all failures at once rather than stopping at the first.

---

## No Analog Found

No files in Phase 52 lack a codebase analog. All new files have direct structural models.

| File | Role | Data Flow | Closest Analog |
|---|---|---|---|
| `quirk/cli/doctor_cmd.py` (new) | CLI command | request-response | `quirk/cli/init_cmd.py` — same file-per-subcommand shape; Rich Console usage |
| `tests/test_doctor_cmd.py` (new) | test | request-response | `tests/test_compliance_schema.py` — assertion style; `unittest.mock` patterns for probe isolation |

---

## Metadata

**Analog search scope:** `quirk/compliance/`, `quirk/cbom/`, `quirk/cli/`, `quirk/scanner/`, `run_scan.py`, `quantum-chaos-enterprise-lab/lab.sh`, `tests/`
**Files scanned:** 10 source files read directly
**Pattern extraction date:** 2026-05-05
