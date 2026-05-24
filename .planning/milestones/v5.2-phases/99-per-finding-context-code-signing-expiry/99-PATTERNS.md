# Phase 99: Per-Finding Context + Code-Signing Expiry - Pattern Map

**Mapped:** 2026-05-24
**Files analyzed:** 10 (6 modified source files + 4 new test files)
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/reports/content_model.py` | model/config | transform | self (Phase 98 ALGO_IMPACT_MAP pattern) | exact — extend existing map |
| `quirk/engine/findings_evaluator.py` | service | request-response | self (`evaluate_email_endpoints`, `evaluate_broker_endpoints`) | exact — add peer function |
| `quirk/scanner/codesign_scanner.py` | service | request-response | self (`_classify_codesign_severity` + TLS path) | exact — extend existing functions |
| `quirk/reports/technical.py` | utility | transform | self (pipe-table block, lines 110–125) | exact — add column |
| `quirk/reports/templates/report.html.j2` | template | transform | self (All Findings table lines 335–354; Top Findings table lines 276–291) | exact — add column/block |
| `run_scan.py` | wiring | request-response | `run_scan.py` lines 2117–2124 (email/broker evaluator pattern) | exact — replicate pattern |
| `tests/test_content_model_phase99.py` | test | CRUD | `tests/test_exec_content_model.py` | exact — same module, same fixture style |
| `tests/test_codesign_expiry_classification.py` | test | CRUD | `tests/test_codesign_scanner.py` | exact — same module, same mock/fixture style |
| `tests/test_codesign_findings_evaluator.py` | test | CRUD | `tests/test_risk_engine.py` (TestBuildFinding + evaluate_* tests) | exact — same evaluator pattern |
| `tests/test_quantum_risk_render_parity.py` | test | CRUD | `tests/test_score_render_parity.py` | role-match — render parity gate pattern |

---

## Pattern Assignments

### `quirk/reports/content_model.py` — ALGO_IMPACT_MAP extension + REMEDIATION_CATALOG

**Analog:** `quirk/reports/content_model.py` (self — Phase 98 patterns)

**Current ALGO_IMPACT_MAP structure** (lines 95–155) — extend 2-tuple to 3-tuple:
```python
# CURRENT (2-tuple):
ALGO_IMPACT_MAP: Dict[str, tuple[str, str]] = {
    "RSA": (
        "Harvest-now-decrypt-later exposure",
        "adversaries may already be archiving encrypted traffic for future decryption.",
    ),
    ...
}

# PHASE 99 TARGET (3-tuple — add quantum_risk_sentence as index [2]):
ALGO_IMPACT_MAP: Dict[str, tuple[str, str, str]] = {
    "RSA": (
        "Harvest-now-decrypt-later exposure",             # [0] risk_label — UNCHANGED
        "adversaries may already be archiving ...",        # [1] impact_sentence — UNCHANGED
        "<locked string from 99-UI-SPEC.md>",             # [2] quantum_risk_sentence — NEW
    ),
    ...
    # New keys to add (do NOT exist in current map):
    "CODESIGN_EXPIRY": (...),
    "CODESIGN_APPROACHING_EXPIRY": (...),
}
```

**_ALGO_KEYWORDS tuple** (lines 162–177) — add new keys:
```python
_ALGO_KEYWORDS: tuple[str, ...] = (
    "RSA", "ECC", "ECDSA", "DH", "DSA",
    "WEAK_HASH", "MD5", "SHA1", "SHA-1",
    "WEAK_KEY_EXCHANGE", "DHE_EXPORT", "RC4", "3DES", "DES",
    # Phase 99 additions:
    "CODESIGN_EXPIRY",
    "CODESIGN_APPROACHING_EXPIRY",
)
```

**_build_top_risks unpack** (line 360) — MUST update to 3-value unpack:
```python
# CURRENT (breaks on 3-tuple):
risk_label, impact_sentence = ALGO_IMPACT_MAP[crypto_class]

# PHASE 99 FIX:
risk_label, impact_sentence, _ = ALGO_IMPACT_MAP[crypto_class]
```

**New REMEDIATION_CATALOG dict** (add after ALGO_IMPACT_MAP, same key set):
```python
# Phase 99 D-04: centralized remediation catalog — same key set as ALGO_IMPACT_MAP.
# All copy locked in 99-UI-SPEC.md §Per-Finding Remediation Catalog — use verbatim.
REMEDIATION_CATALOG: Dict[str, str] = {
    "RSA": "<locked string from 99-UI-SPEC.md>",
    "ECC": "<locked string from 99-UI-SPEC.md>",
    # ... full key set mirroring ALGO_IMPACT_MAP
    "CODESIGN_EXPIRY": "<locked string from 99-UI-SPEC.md>",
    "CODESIGN_APPROACHING_EXPIRY": "<locked string from 99-UI-SPEC.md>",
}
```

**__all__ update** — add `REMEDIATION_CATALOG` and `_classify_finding` to the public list (lines 531–546).

---

### `quirk/engine/findings_evaluator.py` — _build_finding enrichment + evaluate_codesign_endpoints

**Analog 1:** `_build_finding` function (lines 65–102) — enrich with quantum_risk and conditional NIST boilerplate

**Current _build_finding** (lines 65–102):
```python
def _build_finding(
    *,
    severity: str,
    host: str,
    port: int,
    title: str,
    description: str,
    recommendation: str,
    quantum_vulnerable: bool = False,
) -> Dict[str, Any]:
    if not description or not description.strip():
        raise ValueError("_build_finding requires a non-empty description")
    if not recommendation or not recommendation.strip():
        raise ValueError("_build_finding requires a non-empty recommendation")
    rec = recommendation.strip()
    if quantum_vulnerable:
        rec = f"{rec} {NIST_IR_8547_DEPRECATION}"
    return {
        "severity": severity,
        "host": host,
        "port": port,
        "title": title,
        "description": description.strip(),
        "recommendation": rec,
        "compliance": COMPLIANCE_MAP.get(_normalize_for_compliance(title), []),
    }
```

**Phase 99 changes to _build_finding:**
- Add optional `check_id: str = ""` parameter (stored in returned dict; allows `_classify_finding` to match via check_id field for codesign expiry findings)
- After building the base dict: call `_classify_finding(finding)` to get `crypto_class`
- Set `finding["quantum_risk"]` from `ALGO_IMPACT_MAP[crypto_class][2]` if key found; else use `REMEDIATION_FALLBACK_QUANTUM_RISK` constant (from 99-UI-SPEC.md)
- Replace `recommendation` with `REMEDIATION_CATALOG[crypto_class]` if key found (D-04 catalog wins)
- Append `NIST_IR_8547_DEPRECATION` ONLY if `quantum_vulnerable=True` AND crypto_class NOT in `REMEDIATION_CATALOG` (D-05)
- `quantum_risk` must NOT be part of the `_dedupe_findings` key tuple (existing key is `(host, port, title, recommendation)` at line 303–312 — do not change it)

**Import addition** (top of module, line 10 area):
```python
from quirk.reports.content_model import (
    ALGO_IMPACT_MAP,
    REMEDIATION_CATALOG,
    _classify_finding,
)
# Fallback string — from 99-UI-SPEC.md §Field Name Contract
REMEDIATION_FALLBACK_QUANTUM_RISK = "<locked fallback string from 99-UI-SPEC.md>"
```

**Analog 2:** `evaluate_email_endpoints` (lines 754–841) — exact pattern to mirror for `evaluate_codesign_endpoints`

```python
# evaluate_email_endpoints signature/structure to copy (lines 754–761):
def evaluate_email_endpoints(endpoints) -> List[Dict[str, Any]]:
    """..."""
    findings: List[Dict[str, Any]] = []

    for e in endpoints:
        host = getattr(e, "host", "")
        port = int(getattr(e, "port", 0) or 0)
        # ... field reads via getattr
        # ... conditional _build_finding calls
    return findings
```

**evaluate_codesign_endpoints new function** — mirror above pattern:
- Docstring: "Phase 99 CTX-03: emit codesign-specific findings."
- For each endpoint: reads `host`, `port`, `severity`, `cert_subject`, `cert_not_after`, parses `reasons` from `smime_scan_json` via `json.loads`
- Datetime arithmetic pattern to copy from `evaluate_endpoints` TLS cert expiry block (lines 542–579):
  ```python
  now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
  na = cert_not_after if cert_not_after.tzinfo is None else cert_not_after.astimezone(timezone.utc).replace(tzinfo=None)
  if na < now_naive: ...
  elif na < now_naive + timedelta(days=30): ...
  ```
- Three branches: "expired" in reasons → HIGH `_build_finding` with `check_id="CODESIGN_EXPIRY"`; "approaching-expiry" in reasons → MEDIUM with `check_id="CODESIGN_APPROACHING_EXPIRY"`; else → weak-crypto HIGH with `quantum_vulnerable=True`
- All title/description/recommendation copy from 99-UI-SPEC.md §Code-Signing Expiry Findings (verbatim)

---

### `quirk/scanner/codesign_scanner.py` — _classify_codesign_severity + TLS pseudo_parsed

**Analog:** `_classify_codesign_severity` (lines 145–174) — extend with expiry branch

**Current function** (lines 145–174):
```python
def _classify_codesign_severity(parsed: dict) -> "tuple[str | None, list[str]]":
    reasons: list[str] = []
    if is_weak_cipher(parsed.get("sig_hash") or ""):
        reasons.append("weak-signing-alg")
    key_alg = (parsed.get("key_alg") or "").upper()
    key_bits = parsed.get("key_bits")
    if key_alg == "RSA" and isinstance(key_bits, int) and key_bits < 2048:
        reasons.append("weak-rsa-key")
    if key_alg == "ECDSA" and isinstance(key_bits, int) and key_bits < 256:
        reasons.append("weak-ec-key")
    if reasons:
        return "HIGH", reasons
    return None, reasons
```

**Phase 99 extension** — add expiry block AFTER existing weak-crypto checks, BEFORE the `if reasons:` return:
```python
    # [Phase 99 D-07/D-08] Expiry classification — independent of weak-crypto
    not_after_dt = parsed.get("not_after_dt")
    expired_flag = parsed.get("expired", False)
    if expired_flag:
        reasons.append("expired")
    elif not_after_dt is not None:
        # Mirror tzinfo normalization from findings_evaluator.py L544-546
        now = datetime.now(timezone.utc)
        if not_after_dt.tzinfo is None:
            not_after_dt = not_after_dt.replace(tzinfo=timezone.utc)
        days_remaining = (not_after_dt - now).days
        if 0 <= days_remaining <= 90:
            reasons.append("approaching-expiry")

    if reasons:
        if "expired" in reasons or any(r in reasons for r in ("weak-signing-alg", "weak-rsa-key", "weak-ec-key")):
            return "HIGH", reasons
        return "MEDIUM", reasons
    return None, reasons
```

**TLS path pseudo_parsed gap** in `scan_codesign_from_tls_endpoints` (lines 436–441) — add expiry fields:
```python
# CURRENT pseudo_parsed (lines 436–440):
pseudo_parsed = {
    "sig_hash": getattr(ep, "cert_sig_alg", None) or "",
    "key_alg": (getattr(ep, "cert_pubkey_alg", None) or "").upper(),
    "key_bits": getattr(ep, "cert_pubkey_size", None),
}

# PHASE 99 — add expiry fields:
pseudo_parsed["not_after_dt"] = getattr(ep, "cert_not_after", None)
_na = pseudo_parsed["not_after_dt"]
if _na is not None:
    _na_aware = _na if _na.tzinfo else _na.replace(tzinfo=timezone.utc)
    pseudo_parsed["expired"] = _na_aware < datetime.now(timezone.utc)
else:
    pseudo_parsed["expired"] = False
```

`cert_not_after` is confirmed populated on both paths: LDAP path at line 386 (`cert_not_after=parsed.get("not_after_dt")`), TLS path at line 473 (`cert_not_after=getattr(ep, "cert_not_after", None)`).

**LDAP path early-continue** (line 356–358):
```python
severity, reasons = _classify_codesign_severity(parsed)
if severity is None:
    continue  # SAFE cert — no finding emitted
```
This gates correctly on the extended function — expired certs now return non-None severity and will not hit `continue`. No change needed.

---

### `quirk/reports/technical.py` — Quantum Risk column

**Analog:** `build_tech_markdown` findings table block (lines 110–125)

**Current pipe-table** (lines 112–122):
```python
lines.append("| Severity | Host | Port | Title | Description | Recommendation |")
lines.append("|---|---|---:|---|---|---|")
for f in findings:
    sev = f.get("severity", "INFO")
    host = f.get("host", "")
    port = f.get("port", "")
    title = f.get("title", "")
    desc = f.get("description", "")
    rec = f.get("recommendation", "")
    lines.append(f"| {sev} | {md_cell(host)} | {port} | {md_cell(title)} | {md_cell(desc)} | {md_cell(rec)} |")
```

**Phase 99 — add Quantum Risk column between Description and Recommendation:**
```python
# Fallback from 99-UI-SPEC.md §Fallback Strings
FALLBACK_QR = "<locked fallback string from 99-UI-SPEC.md>"

lines.append("| Severity | Host | Port | Title | Description | Quantum Risk | Recommendation |")
lines.append("|---|---|---:|---|---|---|---|")
for f in findings:
    sev = f.get("severity", "INFO")
    host = f.get("host", "")
    port = f.get("port", "")
    title = f.get("title", "")
    desc = f.get("description", "")
    qr = (f.get("quantum_risk") or FALLBACK_QR)[:120]
    rec = f.get("recommendation", "")
    lines.append(
        f"| {sev} | {md_cell(host)} | {port} | {md_cell(title)} | {md_cell(desc)} | {md_cell(qr)} | {md_cell(rec)} |"
    )
```

---

### `quirk/reports/templates/report.html.j2` — Quantum Risk in findings tables

**Analog A:** All Findings table (lines 335–354) — 6-column structure to extend to 7 columns

**Current All Findings table** (lines 338–348):
```html
<thead><tr>
  <th>Severity</th><th>Title</th><th>Host</th><th>Port</th>
  <th>Description</th><th>Recommendation</th>
</tr></thead>
<tbody>
{% for f in findings if f.get('category') != 'coverage_gap' %}
<tr>
  <td><span class="sev-cell sev-{{ f.get('severity','INFO')|upper }}">...</span></td>
  <td>{{ f.get('title','') | sanitize }}</td>
  <td>{{ f.get('host','') | sanitize }}</td>
  <td>{{ f.get('port','') }}</td>
  <td>{{ f.get('description','')[:200] | sanitize }}{% if ... %}…{% endif %}</td>
  <td>{{ f.get('recommendation','')[:200] | sanitize }}{% if ... %}…{% endif %}</td>
</tr>
{% endfor %}
```

**Phase 99 — add `<th>Quantum Risk</th>` and `<td>` before Recommendation:**
```html
<th>Quantum Risk</th>
...
<td><span class="quantum-risk-label">{{ f.get('quantum_risk', FALLBACK_QR)[:200] | sanitize }}</span></td>
```

**Analog B:** Top Findings table (lines 276–291) — 4-column structure; quantum_risk added as sub-block INSIDE Description `<td>`, NOT as a new column:

**Current Top Findings Description cell** (line 286):
```html
<td>{{ f.get('description','')[:120] | sanitize }}{% if f.get('description','')|length > 120 %}…{% endif %}</td>
```

**Phase 99 — add .quantum-risk-block div inside the same `<td>`:**
```html
<td>
  {{ f.get('description','')[:120] | sanitize }}{% if f.get('description','')|length > 120 %}…{% endif %}
  {% if f.get('quantum_risk') %}
  <div class="quantum-risk-block"><span class="quantum-risk-label">{{ f.get('quantum_risk','')[:120] | sanitize }}</span></div>
  {% endif %}
</td>
```

**CSS additions** — add to the existing `<style>` block; exact CSS from 99-UI-SPEC.md §HTML/CSS Additions Contract:
```css
/* Phase 99 CTX-01: quantum risk presentation */
.quantum-risk-block { ... }   /* exact values from 99-UI-SPEC.md */
.quantum-risk-label { ... }   /* exact values from 99-UI-SPEC.md */
```

**Sanitize discipline** — ALL scanner-derived fields use `| sanitize` filter (established pattern throughout template; `quantum_risk` must follow the same rule; see lines 283–286 for the Top Findings `| sanitize` pattern and lines 343–347 for All Findings).

---

### `run_scan.py` — evaluate_codesign_endpoints wiring

**Analog:** broker findings wiring block (lines 2120–2124)

**Current broker wiring pattern:**
```python
# run_scan.py lines 2120–2124:
broker_findings = evaluate_broker_endpoints(all_broker_eps)
if broker_findings:
    findings = (findings or []) + broker_findings
```

**Phase 99 — add codesign block immediately after:**
```python
codesign_findings = evaluate_codesign_endpoints(codesign_endpoints)
if codesign_findings:
    findings = (findings or []) + codesign_findings
```

**Import line update** (line 37):
```python
# CURRENT:
from quirk.engine.findings_evaluator import evaluate_endpoints, evaluate_email_endpoints, evaluate_broker_endpoints

# PHASE 99:
from quirk.engine.findings_evaluator import evaluate_endpoints, evaluate_email_endpoints, evaluate_broker_endpoints, evaluate_codesign_endpoints
```

`codesign_endpoints` is already assembled at line 1617 and line 1870. No additional collection needed.

---

### `tests/test_content_model_phase99.py` (new)

**Analog:** `tests/test_exec_content_model.py`

**Imports pattern** (lines 1–20 of test_exec_content_model.py):
```python
from __future__ import annotations
import pytest
from quirk.reports.content_model import (
    ALGO_IMPACT_MAP,
    ExecContent,
    RiskItem,
    RoadmapItem,
    build_exec_content,
)
```

**New imports for Phase 99 test:**
```python
from quirk.reports.content_model import (
    ALGO_IMPACT_MAP,
    REMEDIATION_CATALOG,
    _classify_finding,
)
from quirk.engine.findings_evaluator import (
    _build_finding,
    NIST_IR_8547_DEPRECATION,
)
```

**Fixture pattern** (test_exec_content_model.py lines 59–76) — small inline dict fixtures:
```python
def _make_rsa_finding(severity: str = "CRITICAL") -> dict:
    return {
        "title": "RSA-2048 certificate — quantum-vulnerable",
        "description": "Endpoint uses RSA-2048...",
        "severity": severity,
        "category": "RSA",
    }
```

**Test structure pattern** — each test: one fixture, one call, one assert with inline rationale string identifying requirement ID. Copy from `test_top_risks_populated` (lines 84–119).

**Existing test to UPDATE** — `test_top_risks_populated` line 115:
```python
# CURRENT (breaks on 3-tuple):
_, expected_sentence = ALGO_IMPACT_MAP["RSA"]
# PHASE 99 FIX:
_, expected_sentence, _ = ALGO_IMPACT_MAP["RSA"]
```

---

### `tests/test_codesign_expiry_classification.py` (new)

**Analog:** `tests/test_codesign_scanner.py`

**Imports pattern** (lines 1–44 of test_codesign_scanner.py):
```python
from __future__ import annotations
import json
import pathlib
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from quirk.scanner import codesign_scanner
from quirk.scanner.codesign_scanner import (
    scan_codesign_from_ldap,
    scan_codesign_from_tls_endpoints,
    CODE_SIGNING,
    _classify_codesign_severity,
)
from quirk.models import CryptoEndpoint

FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures" / "codesign"
```

**Fixture/mock pattern** for expiry tests — use `SimpleNamespace` with `cert_not_after` set to a datetime:
```python
# Copy from test_codesign_scanner.py _target() pattern
def _expired_parsed() -> dict:
    from datetime import datetime, timezone, timedelta
    return {
        "sig_hash": "sha256",
        "key_alg": "RSA",
        "key_bits": 2048,
        "not_after_dt": datetime.now(timezone.utc) - timedelta(days=1),
        "expired": True,
    }

def _approaching_parsed() -> dict:
    from datetime import datetime, timezone, timedelta
    return {
        "sig_hash": "sha256",
        "key_alg": "RSA",
        "key_bits": 2048,
        "not_after_dt": datetime.now(timezone.utc) + timedelta(days=30),
        "expired": False,
    }
```

**TLS path test** — mirror `_run_with_entries` pattern but call `scan_codesign_from_tls_endpoints` with a `SimpleNamespace` carrying `cert_not_after`:
```python
def _tls_ep_with_codesign_eku(**kwargs):
    import json
    defaults = dict(
        host="10.0.0.1", port=443,
        tls_capabilities_json=json.dumps({"eku_oids": ["1.3.6.1.5.5.7.3.3"]}),
        cert_sig_alg="sha256", cert_pubkey_alg="RSA", cert_pubkey_size=2048,
        cert_subject="CN=test", cert_not_after=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)
```

---

### `tests/test_codesign_findings_evaluator.py` (new)

**Analog:** `tests/test_risk_engine.py` (TestBuildFinding class + evaluate_* tests)

**Imports pattern** (test_risk_engine.py lines 1–17):
```python
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from quirk.engine.findings_evaluator import (
    NIST_IR_8547_DEPRECATION,
    _build_finding,
    evaluate_endpoints,
)
```

**New imports for Phase 99 test:**
```python
from quirk.engine.findings_evaluator import evaluate_codesign_endpoints
```

**Endpoint stub pattern** (test_risk_engine.py `_tls_ep` function, lines 31–50):
```python
def _codesign_ep(**kwargs):
    import json
    defaults = dict(
        host="10.0.0.1", port=636,
        protocol="CODE_SIGNING",
        severity="HIGH",
        cert_subject="CN=test-codesign",
        cert_not_after=None,
        smime_scan_json=json.dumps({"reasons": ["expired"]}),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)
```

**Test structure pattern** — `_titles(findings)` helper (test_risk_engine.py line 53) and `_find(findings, title)` helper (line 57) are the standard assertion helpers to copy.

---

### `tests/test_quantum_risk_render_parity.py` (new)

**Analog:** `tests/test_score_render_parity.py` (render parity gate pattern)

**Imports pattern** (test_score_render_parity.py lines 1–16):
```python
from __future__ import annotations
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.evidence import build_evidence_summary
```

**New imports for Phase 99 test:**
```python
from quirk.reports.technical import build_tech_markdown
from quirk.reports.html_renderer import render_html_report
from unittest.mock import MagicMock
```

**Minimal fixtures** — small findings list with `quantum_risk` field set; empty `endpoints`. Mirror `FIXTURE_ENDPOINTS = []` / `FIXTURE_FINDINGS = []` pattern from test_score_render_parity.py lines 18–19.

**HTML renderer test** — use `render_html_report` with `findings` list containing a `quantum_risk` field; assert that the rendered HTML contains the text from `findings[0]["quantum_risk"]` in both "All Findings" and "Top Findings" sections. Pattern from `tests/test_html_renderer_coverage_gaps.py` and `tests/test_html_renderer_roadmap_section.py` (which call `render_html_report` with minimal stubs).

---

## Shared Patterns

### Static map pattern (ALGO_IMPACT_MAP / REMEDIATION_CATALOG)

**Source:** `quirk/reports/content_model.py` lines 95–155
**Apply to:** Both `ALGO_IMPACT_MAP` extension and new `REMEDIATION_CATALOG`

Pattern: module-level `Dict[str, tuple[...]]` or `Dict[str, str]` with doc comment identifying phase + decision number. Keys are uppercase crypto-class string tokens matching `_ALGO_KEYWORDS`. Values from 99-UI-SPEC.md §Copywriting Contract verbatim.

```python
# Phase 99 D-01/D-04: weakness-specific remediation catalog.
# Keys mirror ALGO_IMPACT_MAP — same key set, ordered identically.
# Copy from 99-UI-SPEC.md §Per-Finding Remediation Catalog (locked — use verbatim).
REMEDIATION_CATALOG: Dict[str, str] = {
    "RSA": "...",
    ...
}
```

### `_build_finding` call site pattern

**Source:** `quirk/engine/findings_evaluator.py` lines 120–135 (evaluate_container_package calls)
**Apply to:** All `_build_finding` calls in the new `evaluate_codesign_endpoints`

Pattern: always keyword-only arguments (`severity=`, `host=`, `port=`, `title=`, `description=`, `recommendation=`). When adding `check_id=`, it remains keyword-only. Never positional.

```python
findings.append(_build_finding(
    severity="HIGH",
    host=host,
    port=port,
    title="...",
    description="...",
    recommendation="...",
    check_id="CODESIGN_EXPIRY",  # Phase 99 new param
))
```

### `getattr` access pattern for CryptoEndpoint fields

**Source:** `quirk/engine/findings_evaluator.py` lines 763–768 (evaluate_email_endpoints loop)
**Apply to:** `evaluate_codesign_endpoints` loop variable reads

```python
host = getattr(e, "host", "")
port = int(getattr(e, "port", 0) or 0)
severity = getattr(e, "severity", None) or "HIGH"
cert_subject = getattr(e, "cert_subject", "") or ""
cert_not_after = getattr(e, "cert_not_after", None)
```

### Jinja2 sanitize filter pattern

**Source:** `quirk/reports/templates/report.html.j2` lines 283–286, 343–347
**Apply to:** All new `quantum_risk` field renders in the HTML template

Every scanner-derived cell uses `| sanitize`. Static prose (from ALGO_IMPACT_MAP — locked copy) does NOT require sanitize per existing Phase 98 comment at line 243. `quantum_risk` field carries scanner-context strings and must be sanitized.

### datetime expiry comparison pattern

**Source:** `quirk/engine/findings_evaluator.py` lines 542–579 (TLS cert expiry block)
**Apply to:** `evaluate_codesign_endpoints` and `_classify_codesign_severity` expiry logic

```python
# Naive UTC comparison (cert_not_after stored as naive UTC):
now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
na = cert_not_after if cert_not_after.tzinfo is None else cert_not_after.astimezone(timezone.utc).replace(tzinfo=None)
if na < now_naive:
    # expired
elif na < now_naive + timedelta(days=90):  # Phase 99 uses 90 days (not 30)
    # approaching
```

### Evaluator wiring pattern in run_scan.py

**Source:** `run_scan.py` lines 2113–2124 (email + broker findings blocks)
**Apply to:** New codesign findings wiring

```python
# Pattern to replicate:
email_findings = evaluate_email_endpoints(email_endpoints)
if email_findings:
    findings = (findings or []) + email_findings
broker_findings = evaluate_broker_endpoints(all_broker_eps)
if broker_findings:
    findings = (findings or []) + broker_findings
```

---

## No Analog Found

All files have close analogs in the codebase. No "no analog" entries.

---

## Key Anti-Pattern Warnings (from RESEARCH.md)

| Anti-Pattern | Guard |
|---|---|
| 2-tuple unpack of `ALGO_IMPACT_MAP` breaks on 3-tuple | Search for `= ALGO_IMPACT_MAP[` before committing; update `content_model.py:_build_top_risks` L360 AND `tests/test_exec_content_model.py` L115 |
| `quantum_risk` added to `_dedupe_findings` key tuple | Key is `(host, port, title, recommendation)` at L303–312 — do NOT add `quantum_risk` |
| TLS path `pseudo_parsed` missing expiry fields | Must add `not_after_dt` + `expired` to `pseudo_parsed` in `scan_codesign_from_tls_endpoints` (L436–440) in same plan as `_classify_codesign_severity` change |
| `evaluate_codesign_endpoints` not imported in run_scan.py | Update import at L37; add call after broker findings block at L2124 |
| NIST boilerplate still appended when catalog match exists | Condition append: `if quantum_vulnerable and crypto_class not in REMEDIATION_CATALOG` |
| Parallel quantum-risk map (new dict keyed differently from ALGO_IMPACT_MAP) | D-01: extend ALGO_IMPACT_MAP only; no separate map |

---

## Metadata

**Analog search scope:** `quirk/reports/`, `quirk/engine/`, `quirk/scanner/`, `quirk/reports/templates/`, `run_scan.py`, `tests/`
**Files read:** 12 source files, 6 test files
**Pattern extraction date:** 2026-05-24
