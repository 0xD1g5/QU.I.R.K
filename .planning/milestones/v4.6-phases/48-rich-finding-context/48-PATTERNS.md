---
phase: 48-rich-finding-context
type: patterns
status: active
source: gsd-pattern-mapper
updated: 2026-05-04
---

# Phase 48 — Rich Finding Context — Pattern Map

**Mapped:** 2026-05-04
**Files analyzed:** 8 artifacts (4 code, 1 template, 1 test, 2 docs)
**Analogs found:** 8 / 8 (one CI-gate analog is partial — test_packaging.py disk-read pattern)

## File Classification

| New / Modified Artifact | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `_build_finding(...)` helper in `quirk/engine/risk_engine.py` | utility (producer-side factory) | transform | `_evaluate_container_package` at `quirk/engine/risk_engine.py:29-113` | exact (same module, same return shape, same import block) |
| `NIST_IR_8547_DEPRECATION` module-level constant in `quirk/engine/risk_engine.py` | config (literal constant) | n/a | `_OPENSSL_EOL`, `_OPENSSL_NAMES`, `_SEVERITY_RANK` at `quirk/engine/risk_engine.py:8-19` | exact (same file, same level) |
| `description: str` field on dashboard finding DTO | schema/model | request-response | `FindingItem` at `quirk/dashboard/api/schemas.py:44-55` | **already present** — verify only |
| HTML/PDF renderer update (display `description` above `recommendation`) | renderer (Jinja template) | transform | `quirk/reports/templates/report.html.j2:172-187` (Top Findings) and `:223-241` (All Findings) | exact (Top Findings already shows description; All Findings does not) |
| JSON export path serialization | service (file I/O) | file-I/O | `_json_dump` + `write_reports` at `quirk/reports/writer.py:32-34, 91-102` | exact (no projection — passes the dict straight through) |
| CI grep gate over two files | test (forbidden-string lint) | request-response | `tests/test_packaging.py:33-44` (read pyproject.toml from disk; assert substring) | role-match (closest existing pattern; no dedicated lint test exists yet) |
| Unit test for `_build_finding` (non-empty `description`/`recommendation`) | test (fixture-based) | transform | `tests/test_risk_engine.py:1-77` (helpers `_cfg`, `_tls_ep`, `_find`, class-grouped tests) | exact (same engine, same fixture style) |
| Doc rewrite: `docs/report-interpretation.md` + `docs/quirk-overview.md` | docs (markdown) | n/a | both files exist; stale terms confirmed | exact |

## Pattern Assignments

### 1. `_build_finding(...)` helper — `quirk/engine/risk_engine.py`

**Analog:** `_evaluate_container_package` at `quirk/engine/risk_engine.py:29-113`

**Imports already in scope** (`risk_engine.py:1-8`):
```python
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
```
No new imports required for the helper itself.

**Signature + return-shape pattern** (`risk_engine.py:29-47`):
```python
def _evaluate_container_package(
    host: str, port: int, pkg_name: str, pkg_version: str
) -> Optional[Dict[str, Any]]:
    name = pkg_name.lower()
    version = pkg_version or ""

    if name in _OPENSSL_NAMES:
        for prefix, sev, label in _OPENSSL_EOL:
            if version.startswith(prefix):
                return {
                    "severity": sev,
                    "host": host,
                    "port": port,
                    "title": f"End-of-life {label} in container image",
                    "recommendation": (
                        f"{label} has reached end-of-life and no longer receives security patches. "
                        "Update the base image to a supported distribution with a current OpenSSL version."
                    ),
                }
```

**Apply to `_build_finding`:** keep the same five-key dict shape (`severity`, `host`, `port`, `title`, `recommendation`) and add `description`. Return `Dict[str, Any]` (not `Optional` — helper always succeeds). Required positional args per CONTEXT D-02: `severity, host, port, title, description, recommendation`. Optional kw-only `quantum_vulnerable: bool = False` triggers `NIST_IR_8547_DEPRECATION` append on `recommendation` (D-06).

**Producer call sites to refactor** — all in `risk_engine.py` between lines 343 and 497, plus the email/broker evaluators at lines 502-628:
- TLS legacy versions (lines 327-341)
- TLS legacy cipher suites (343-354)
- TLS cert expired (363-372)
- TLS cert expiring (373-383)
- TLS self-signed (394-406)
- TLS untrusted CA (407-420)
- TLS quantum-vulnerable RSA undersized (425-437) — **quantum_vulnerable=True**
- TLS quantum-vulnerable RSA (438-449) — **quantum_vulnerable=True** (also stale-term hit at line 447)
- TLS quantum-vulnerable ECDSA undersized (450-461) — **quantum_vulnerable=True**
- TLS quantum-vulnerable ECDSA (462-472) — **quantum_vulnerable=True**
- SSH advisory (474-481) — **quantum_vulnerable=True**
- CONTAINER (483-488) — handled by `_evaluate_container_package`; refactor that helper to use `_build_finding` too
- UNKNOWN open service (490-497)
- EMAIL findings (lines 521-567) — STARTTLS, weak email TLS — last two are **quantum_vulnerable=True**
- BROKER findings (lines 591-628) — Kafka/AMQP/Redis plaintext + weak-cipher

---

### 2. `NIST_IR_8547_DEPRECATION` module-level constant

**Analog:** existing module-level constants at `quirk/engine/risk_engine.py:8-19`

**Placement/style pattern**:
```python
_SEVERITY_RANK = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

# (version_prefix, severity, eol_label)
_OPENSSL_EOL: List[Tuple[str, str, str]] = [
    ("0.", "CRITICAL", "OpenSSL 0.x"),
    ...
]

_OPENSSL_NAMES = frozenset({"openssl", "libssl", ...})
```

**Apply:** define `NIST_IR_8547_DEPRECATION` as a top-of-module constant in the same constants block (after `_OPENSSL_NAMES` line 19, before `_pkg_major` line 22). Convention here is leading-underscore for private constants — but this constant is **the canonical anchor** that the CI grep gate (D-08) and Phase 49 (Compliance Mapping) will key off literally; planner should use the public name `NIST_IR_8547_DEPRECATION` exactly as locked in CONTEXT D-06.

```python
NIST_IR_8547_DEPRECATION = (
    "Per NIST IR 8547, RSA and ECC are deprecated after 2030 and "
    "disallowed after 2035."
)
```

---

### 3. `description: str` field on dashboard DTO — `quirk/dashboard/api/schemas.py`

**Analog:** existing `FindingItem` at `quirk/dashboard/api/schemas.py:44-55`:
```python
class FindingItem(BaseModel):
    id: Optional[int] = None
    host: str
    port: int
    severity: str        # CRITICAL / HIGH / MEDIUM / LOW / INFO
    title: str
    protocol: Optional[str] = None
    description: Optional[str] = None
    remediation: Optional[str] = None
    quantum_risk: Optional[str] = None   # quantum-safety label
    source: Optional[str] = None        # scanner type
    category: Optional[str] = None      # Phase 45 — coverage_gap visibility (Q2)
```

**Critical finding for the planner:** `description` is **already present on the DTO** (line 51), and so are sibling DTOs `IdentityFinding` (line 89), `MotionFinding` (line 104), `DarFinding` (line 124). The dashboard side is structurally complete; Phase 48's job here is to:
1. Verify nothing in `_derive_findings` (`quirk/dashboard/api/routes/scan.py:47-186`) sets `description=None` for any branch — spot-check confirms current branches **already** populate `description` (e.g., `scan.py:72, 87, 102, 122, 135, 155, 175`).
2. Optionally tighten the type from `Optional[str] = None` to `str` (or keep optional but enforce at construction). CONTEXT D-01 says "non-empty"; planner should decide whether to enforce via Pydantic validator or rely on the producer-side `_build_finding` chokepoint.
3. **Note:** dashboard uses `remediation` (not `recommendation`). The risk engine emits dicts with `recommendation`. The dashboard route in `scan.py` constructs `FindingItem` directly from endpoint state (does not consume risk-engine dicts), so the field-name mismatch is intentional. Phase 48 must not rename either.

---

### 4. HTML/PDF renderer — `quirk/reports/templates/report.html.j2`

**Analog 1 (Top Findings — already shows description):** `quirk/reports/templates/report.html.j2:172-187`
```jinja
{% if findings %}
<h2>Top Findings</h2>
<table>
  <thead><tr><th>Severity</th><th>Title</th><th>Host</th><th>Description</th></tr></thead>
  <tbody>
  {% for f in (findings | rejectattr('category', 'equalto', 'coverage_gap') | list)[:10] %}
  <tr>
    <td><span class="sev-cell sev-{{ f.get('severity','INFO')|upper }}">{{ f.get('severity','INFO')|upper }}</span></td>
    <td>{{ f.get('title','') }}</td>
    <td>{{ f.get('host','') }}{% if f.get('port') %}:{{ f.get('port') }}{% endif %}</td>
    <td>{{ f.get('description','')[:120] }}{% if f.get('description','')|length > 120 %}…{% endif %}</td>
  </tr>
```

**Analog 2 (All Findings — currently shows ONLY recommendation; needs description column added per D-01):** `quirk/reports/templates/report.html.j2:223-241`
```jinja
<h2>All Findings</h2>
{% if findings %}
<table>
  <thead><tr><th>Severity</th><th>Title</th><th>Host</th><th>Port</th><th>Recommendation</th></tr></thead>
  <tbody>
  {% for f in findings if f.get('category') != 'coverage_gap' %}
  <tr>
    <td><span class="sev-cell sev-{{ f.get('severity','INFO')|upper }}">{{ f.get('severity','INFO')|upper }}</span></td>
    <td>{{ f.get('title','') }}</td>
    <td>{{ f.get('host','') }}</td>
    <td>{{ f.get('port','') }}</td>
    <td>{{ f.get('recommendation','')[:160] }}</td>
  </tr>
```

**Apply to "All Findings":** insert a `Description` column before `Recommendation` per D-01 ("display `description` above `recommendation`"). For a table layout this means a column to the left of Recommendation; for the per-finding render in the technical Markdown report (`quirk/reports/technical.py:88-96`), prepend `description` text above `recommendation` in the output.

**Analog 3 (technical Markdown finding render):** `quirk/reports/technical.py:85-99`
```python
# === Findings table ===
lines.append("## Findings")
lines.append("")
lines.append("| Severity | Host | Port | Title | Recommendation |")
lines.append("|---|---|---:|---|---|")
for f in findings:
    sev = f.get("severity", "INFO")
    host = f.get("host", "")
    port = f.get("port", "")
    title = f.get("title", "")
    rec = f.get("recommendation", "")
    lines.append(f"| {sev} | {host} | {port} | {title} | {rec} |")
```
**Apply:** add a `Description` column to the table header and to the row format string, sourced from `f.get("description", "")`.

---

### 5. JSON export path

**Analog:** `quirk/reports/writer.py:32-34` and `:91-102`
```python
def _json_dump(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, default=str)
...
def write_reports(cfg, endpoints, findings, run_stats=None, *, error_endpoints=None):
    outdir = cfg.output.directory
    os.makedirs(outdir, exist_ok=True)
    stamp = _utc_stamp()
    ...
    # 1) Findings JSON (raw)
    findings_path = os.path.join(outdir, f"findings-{stamp}.json")
    _json_dump(findings_path, findings)
```

**Verification only:** `_json_dump` serializes the raw `findings` list of dicts with no whitelist/projection. Once `_build_finding` writes `description` into the dict, it flows through to `findings-*.json` automatically. No code change required here — just a unit-test or smoke-check that the on-disk JSON includes `description` for every finding.

---

### 6. CI grep gate — pytest test (planner picks placement)

**Analog:** `tests/test_packaging.py:33-44` (read source file from repo root, assert string content)
```python
def test_pyproject_has_jinja2():
    """pyproject.toml must declare jinja2 as a core dependency."""
    root = os.path.join(os.path.dirname(__file__), "..")
    pyproject = open(os.path.join(root, "pyproject.toml")).read()
    assert "jinja2" in pyproject.lower(), "jinja2 not found in pyproject.toml dependencies"


def test_pyproject_has_rich():
    """pyproject.toml must declare rich as a core dependency."""
    root = os.path.join(os.path.dirname(__file__), "..")
    pyproject = open(os.path.join(root, "pyproject.toml")).read()
    assert "rich" in pyproject.lower(), "rich not found in pyproject.toml dependencies"
```

**Repo CI conventions discovered:**
- No top-level `scripts/` directory (only `quantum-chaos-enterprise-lab/scripts/`).
- No `Makefile` at repo root.
- Sole GitHub workflow is `.github/workflows/dashboard-quality.yml` and is **path-scoped to `src/dashboard/**`** — would not trigger on Python source changes anyway.
- pytest config at `pyproject.toml:88-95` defines `testpaths = ["tests"]` with `addopts = "-m 'not slow'"` — any new `tests/test_*.py` is auto-collected.

**Recommendation for planner:** placement should be a new pytest test file (e.g. `tests/test_pqc_terminology_gate.py`) — this matches the only existing in-repo "lint by reading source file" precedent and is automatically picked up by every test run. A `scripts/ci_pqc_terminology_gate.sh` would have nowhere to be invoked from (no CI runner triggers on `quirk/**`).

**Apply pattern (case-insensitive substring per D-08, no exemptions, two locked file paths per D-07):**
```python
import os

_GATED_FILES = [
    "quirk/engine/risk_engine.py",
    "quirk/dashboard/api/routes/scan.py",
]
_FORBIDDEN = ("kyber", "dilithium", "when standards are adopted")


def _read(rel: str) -> str:
    root = os.path.join(os.path.dirname(__file__), "..")
    return open(os.path.join(root, rel), encoding="utf-8").read().lower()


def test_no_stale_pqc_terminology_in_gated_files():
    """D-07/D-08: forbidden substrings must not appear in the two gated source files."""
    offenders = []
    for rel in _GATED_FILES:
        text = _read(rel)
        for needle in _FORBIDDEN:
            if needle in text:
                offenders.append((rel, needle))
    assert not offenders, (
        f"Stale PQC terminology found: {offenders}. "
        f"Use FIPS designations only (FIPS 203/204/205); see Phase 48 D-04."
    )
```

---

### 7. Unit test for `_build_finding` — `tests/test_risk_engine.py`

**Analog:** `tests/test_risk_engine.py:1-77` — fixture-based engine tests already in this file.

**Imports + fixture pattern** (`tests/test_risk_engine.py:1-46`):
```python
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from quirk.engine.risk_engine import evaluate_endpoints


def _cfg():
    """Minimal config stub with an empty TLS port list."""
    cfg = MagicMock()
    cfg.scan.ports_tls = []
    return cfg


def _tls_ep(**kwargs):
    """Build a minimal TLS CryptoEndpoint-like object with sensible defaults."""
    defaults = dict(
        host="10.0.0.1",
        port=443,
        protocol="TLS",
        ...
        cert_pubkey_alg=None,
        cert_pubkey_size=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)
```

**Class-grouped assertion pattern** (`tests/test_risk_engine.py:61-77`):
```python
class TestLegacyCipherSuites:
    def test_legacy_suites_present_produces_low_finding(self):
        ep = _tls_ep(tls_legacy_suites_present=True)
        findings = evaluate_endpoints(_cfg(), [ep])
        f = _find(findings, "Legacy TLS cipher suites accepted")
        assert f is not None, "Expected legacy cipher suite finding"
        assert f["severity"] == "LOW"
```

**Apply:** add a new `TestRichFindingContext` class (or `TestBuildFinding`) that drives `evaluate_endpoints` with a small fixture set covering at least one quantum-vulnerable endpoint (e.g. RSA cert) and one non-quantum endpoint (e.g. expired cert). Assertions per CONTEXT D-02:
- Every emitted finding has `f["description"]` and `f["description"].strip()` non-empty.
- Every finding flagged quantum-vulnerable contains the literal `NIST_IR_8547_DEPRECATION` string in `f["recommendation"]`.
- Every quantum-vulnerable finding's `recommendation` cites `FIPS 203`, `FIPS 204`, or `FIPS 205` (D-04 contract for Phase 49).

---

### 8. Doc rewrite — `docs/report-interpretation.md` + `docs/quirk-overview.md`

**Confirmed file existence:** both present.

**Stale-term hits (`grep -niE 'kyber|dilithium|when standards are adopted'`):**
- `docs/report-interpretation.md:121` —
  `| SSH quantum planning advisory | INFO | SSH host key or KEX algorithm is quantum-vulnerable (RSA/ECDH) | Plan CRYSTALS-Kyber/ML-KEM migration for post-quantum OpenSSH |`
- `docs/report-interpretation.md:150` —
  `| **LATER** | Long-horizon quantum migration; CRYSTALS-Kyber (ML-KEM), ML-DSA adoption when standards finalize in your ecosystem | 2026–2030 (NIST FIPS 203/204/205 window) |`
- `docs/quirk-overview.md:75` —
  `Every TLS certificate's key algorithm is evaluated against a 50-entry NIST PQC classification table that marks each algorithm as *quantum-safe*, *quantum-vulnerable*, or *hybrid-ready*. RSA and ECDSA keys are flagged as vulnerable. CRYSTALS-Kyber and ML-DSA implementations are recognized as quantum-safe.`

**Apply per D-04:** rewrite to FIPS designations only — `ML-KEM (FIPS 203)`, `ML-DSA (FIPS 204)`, `SLH-DSA (FIPS 205)`. Strip `CRYSTALS-Kyber`, `Kyber`, `Dilithium`, `CRYSTALS-Dilithium`, and `when standards are adopted`/`when standards finalize` phrasing. Per CLAUDE.md: after the rewrite, sync both files to Obsidian under `20_Dev-Work/QUIRK/Guides/` with frontmatter `type: guide` + `source: docs/<filename>.md`.

---

## Shared Patterns

### Finding-dict canonical shape
**Source:** `quirk/engine/risk_engine.py:343-497` (every TLS/SSH/CONTAINER/UNKNOWN branch is a 5-key dict).
**Apply to:** every producer call site after `_build_finding` is introduced. Extending the contract from 5 keys to 6 keys (`description` added) is the **only** schema change in Phase 48. Do not introduce typed model classes (CONTEXT-01 D-01 explicitly preserves the dict convention).
```python
findings.append({
    "severity": "MEDIUM",
    "host": host,
    "port": port,
    "title": "...",
    "recommendation": "...",
    # NEW for Phase 48:
    "description": "...",
})
```

### Postprocessing chokepoint
**Source:** `quirk/engine/risk_engine.py:163-205` (`_normalize_finding` + `_dedupe_findings`).
**Apply to:** verify the dedup key tuple `(host, port, title, recommendation)` at line 184-189 still produces correct dedup behavior after the `recommendation` field gains the `NIST_IR_8547_DEPRECATION` suffix on quantum-vulnerable findings. Two findings with the same title but different recommendation will no longer dedup — confirm this is the intended behavior (likely yes, since one would be quantum-vuln-flagged and one would not, distinct semantics).

### Mandatory phase completion (CLAUDE.md)
**Source:** `CLAUDE.md` lines 50-95.
**Apply to:** every Phase 48 plan must end with these tasks:
1. Update `docs/UAT-SERIES.md` — add test cases for non-empty `description` and FIPS-terminology presence.
2. Sync UAT-SERIES.md to Obsidian via direct vault filesystem write at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`.
3. Commit `docs/UAT-SERIES.md` via `gsd-tools.cjs commit`.
4. Create Obsidian phase note at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-48-Rich-Finding-Context.md` (do NOT use `obsidian CLI content=` — write directly to the vault filesystem).
5. Sync the two rewritten guides (`docs/report-interpretation.md`, `docs/quirk-overview.md`) to Obsidian under `20_Dev-Work/QUIRK/Guides/`.

## No Analog Found

None. Every artifact has a usable analog in the existing codebase.

## Metadata

**Analog search scope:**
- `quirk/engine/risk_engine.py` (629 lines, full file scanned)
- `quirk/dashboard/api/schemas.py` (227 lines, full file)
- `quirk/dashboard/api/routes/scan.py` (lines 1-80 + grep over remainder)
- `quirk/reports/` (technical.py, executive.py, html_renderer.py, writer.py, templates/report.html.j2)
- `tests/test_risk_engine.py` (lines 1-100)
- `tests/test_packaging.py` (lines 1-60)
- `pyproject.toml`, `.github/workflows/`
- `docs/report-interpretation.md`, `docs/quirk-overview.md` (grep-only)

**Files scanned:** ~12
**Pattern extraction date:** 2026-05-04
