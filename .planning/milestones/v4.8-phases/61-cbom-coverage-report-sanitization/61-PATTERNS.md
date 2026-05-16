# Phase 61: CBOM Coverage + Report Sanitization - Pattern Map

**Mapped:** 2026-05-10
**Files analyzed:** 6 (2 modified, 1 new utility, 3 new tests)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/cbom/builder.py` | service | transform | self (existing Pass-1 branches) | exact |
| `quirk/reports/technical.py` | service | transform | self (existing `build_tech_markdown`) | exact |
| `quirk/reports/_md_escape.py` | utility | transform | `quirk/reports/__init__.py` (private module pattern) | partial |
| `tests/test_cbom_coverage.py` | test | CRUD | `tests/test_cbom_skip_lists.py` | exact |
| `tests/test_cbom_vault_consistency.py` | test | CRUD | `tests/test_cbom_motion_golden.py` | exact |
| `tests/test_report_sanitization.py` | test | CRUD | `tests/test_reports_writer.py` | role-match |

---

## Pattern Assignments

### `quirk/cbom/builder.py` (service, transform — Pass-1 dispatch additions)

**Analog:** self, lines 375–463 (Pass-1 for-loop)

**Imports pattern** (lines 12–37 of builder.py — no new imports needed):
```python
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Optional

from cyclonedx.model import Property
from cyclonedx.model.bom import Bom, BomMetaData
# ... (no new imports required for Phase 61 changes)

from quirk.cbom.classifier import classify_algorithm
from quirk.models import CryptoEndpoint
```

**Protocol constants pattern** (lines 45–54 of builder.py):
```python
MOTION_PLAINTEXT_PROTOCOLS: frozenset[str] = frozenset({
    "KAFKA-PLAIN", "AMQP-PLAIN", "REDIS-PLAIN",
})

DAR_SKIP_PROTOCOLS: frozenset[str] = frozenset({
    "POSTGRESQL", "MYSQL", "RDS",
    "S3", "AZURE_BLOB",
    "KUBERNETES", "VAULT",
    "GCP", "CLOUD_SQL",
})
```
NOTE: Remove "MYSQL", "POSTGRESQL", "RDS", "S3", "AZURE_BLOB" from the `pass` elif (line 443),
and remove "VAULT" from `DAR_SKIP_PROTOCOLS` once its dedicated Pass-1 branch is added.

**Core pattern — the SAML/KERBEROS/DNSSEC 3-line branch to copy for VAULT** (lines 432–441):
```python
elif ep.protocol == "SAML":
    # SAML: cert_pubkey_alg holds algorithm name (RSA, ECDSA) or SHA1 for URI findings
    if ep.cert_pubkey_alg:
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)

elif ep.protocol == "KERBEROS":
    # Kerberos: cert_pubkey_alg holds the etype name (e.g. "rc4-hmac", "aes256-cts-hmac-sha1-96")
    # Exclude "kerberos-unreachable" synthetic finding -- not a real algorithm (per D-18)
    if ep.cert_pubkey_alg and ep.cert_pubkey_alg != "kerberos-unreachable":
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
```

**Core pattern — the `pass` elif block that will be split** (line 443–446):
```python
elif ep.protocol in ("POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "KUBERNETES"):
    # DB, object storage, and Kubernetes config findings — no key material to catalog.
    # Security signal is in service_detail; CBOM algorithm catalog not applicable.
    pass
```

**`_register_algorithm` helper signature** (lines 338–347):
```python
def _register_algorithm(
    name: str,
    registry: dict[str, Component],
    key_size: int | None = None,
) -> str:
    """Ensure an algorithm component exists in registry; return its bom_ref key."""
    bom_ref_key = _normalize_bom_ref_key(name)
    if bom_ref_key not in registry:
        registry[bom_ref_key] = _make_algorithm_component(name, bom_ref_key, key_size)
    return bom_ref_key
```

**SSH branch fallback pattern to add at end of SSH block** (lines 378–386):
```python
if ep.protocol == "SSH":
    # SSH: parse ssh_audit_json
    ssh_data = _extract_ssh_algorithms(ep.ssh_audit_json)
    for section in ("kex", "key", "enc", "mac"):
        for entry in ssh_data.get(section, []):
            alg = entry.get("algorithm")
            if alg:
                keysize = entry.get("keysize")
                _register_algorithm(alg, algo_registry, key_size=keysize)
    # D-07 addition: also register host key alg if present (ssh-weak fallback)
    if ep.cert_pubkey_alg:
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
```

**SOURCE branch pattern to replace with fallback** (lines 398–402):
```python
elif ep.protocol == "SOURCE":
    # Source: cipher_suite=semgrep rule_id, extract algorithm hint
    algo_hint = _extract_algo_from_rule_id(ep.cipher_suite)
    if algo_hint:
        _register_algorithm(algo_hint, algo_registry)
    # D-06: fallback to raw rule_id if hint not recognized
```

---

### `quirk/reports/technical.py` (service, transform — add md_cell wrapping)

**Analog:** self, lines 1–100

**Import to add** (after existing imports at lines 1–3):
```python
from datetime import datetime, timezone
from typing import Dict, List

from quirk.reports._md_escape import md_cell  # ADD THIS
```

**Primary injection point — Findings table row** (line 97):
```python
# BEFORE (unsafe):
lines.append(f"| {sev} | {host} | {port} | {title} | {desc} | {rec} |")

# AFTER (safe — sev/port are computed values, only data fields wrapped):
lines.append(f"| {sev} | {md_cell(host)} | {port} | {md_cell(title)} | {md_cell(desc)} | {md_cell(rec)} |")
```

**Service Inventory table row** (line 41–43):
```python
# BEFORE (unsafe):
lines.append(
    f"| {e.host} | {e.port} | {getattr(e, 'protocol', '') or ''} | {_service_detail(e)} |"
)

# AFTER:
lines.append(
    f"| {md_cell(e.host)} | {e.port} | {getattr(e, 'protocol', '') or ''} | {md_cell(_service_detail(e))} |"
)
```

**TLS Capabilities table row** (line 61–62):
```python
# BEFORE (unsafe):
lines.append(
    f"| {e.host} | {e.port} | {getattr(e, 'tls_version', '') or ''} | {sv} | {weak} | {legacy} | {pfs} | {sample} | {notes} |"
)

# AFTER:
lines.append(
    f"| {md_cell(e.host)} | {e.port} | {md_cell(getattr(e, 'tls_version', '') or '')} | {md_cell(sv)} | {weak} | {legacy} | {pfs} | {md_cell(sample)} | {md_cell(notes)} |"
)
```

**TLS Blockers table row** (line 80–82):
```python
# BEFORE (unsafe):
lines.append(
    f"| {e.host} | {e.port} | {blocker} | {getattr(e, 'scan_error', '') or ''} |"
)

# AFTER:
lines.append(
    f"| {md_cell(e.host)} | {e.port} | {md_cell(blocker)} | {md_cell(getattr(e, 'scan_error', '') or '')} |"
)
```

**Safe vs unsafe field boundary (from D-10):**
- Safe (no wrapping): `sev`, `e.port` (int), `weak`/`legacy`/`pfs` ("YES"/"NO"), `now` (datetime string)
- Unsafe (must wrap): `e.host`, `e.tls_version`, `sv`, `sample`, `notes`, `blocker`, `e.scan_error`, `_service_detail(e)`, `host`, `title`, `desc`, `rec`

---

### `quirk/reports/_md_escape.py` (utility, transform — NEW FILE)

**Analog:** No direct existing analog. Private module convention observed from `quirk/reports/__init__.py` (empty `__init__` marks package boundary); underscore prefix `_md_escape` signals private-to-package.

**Module structure pattern** (modeled on project private utility convention):
```python
"""Markdown table cell escaping utility for GFM report output."""
from __future__ import annotations


def md_cell(value) -> str:
    """Escape a value for safe interpolation into a GFM table cell."""
    ...
```

No imports from cyclonedx or quirk are needed. No `__all__` required for a single-function private module. No class wrapper — bare function, matching the style of `_extract_algo_from_rule_id` and `_normalize_cloud_key_spec` in builder.py.

---

### `tests/test_cbom_coverage.py` (test, CRUD — NEW FILE)

**Analog:** `tests/test_cbom_skip_lists.py` (parametrized pytest over protocol list, synthetic CryptoEndpoint construction, `build_cbom` call, component assertion)

**Imports pattern** (test_cbom_skip_lists.py lines 1–12):
```python
from __future__ import annotations

import pytest

from quirk.cbom.builder import (
    DAR_SKIP_PROTOCOLS,
    MOTION_PLAINTEXT_PROTOCOLS,
    build_cbom,
)
from quirk.models import CryptoEndpoint
```

For `test_cbom_coverage.py`, add:
```python
from cyclonedx.model.component import ComponentType
from cyclonedx.model.crypto import CryptoAssetType
```

**Synthetic endpoint helper pattern** (test_cbom_skip_lists.py lines 26–38):
```python
def _full_tls_endpoint(protocol: str, host: str = "h", port: int = 1) -> CryptoEndpoint:
    """Construct an endpoint with FULL TLS+cert metadata so the skip
    cannot be attributed to missing fields."""
    return CryptoEndpoint(
        host=host, port=port, protocol=protocol,
        tls_version="TLSv1.2",
        cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
        cert_pubkey_alg="RSA", cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_subject="CN=example.com", cert_issuer="CN=Example CA",
        cert_not_before=None, cert_not_after=None,
        tls_capabilities_json=None, ssh_audit_json=None,
    )
```

One named helper per protocol family (or a factory dict), OR a single parametrize with a `pytest.param(..., id="vault")` tuple carrying the pre-built endpoint. The `id=` keyword is required per D-13 so CI names failures by protocol.

**Parametrize pattern** (test_cbom_skip_lists.py lines 56–59):
```python
@pytest.mark.parametrize(
    "protocol",
    sorted(MOTION_PLAINTEXT_PROTOCOLS | DAR_SKIP_PROTOCOLS),
)
def test_skip_protocol_emits_no_cert_or_proto_component(protocol):
    ...
```

For coverage test, parametrize over a list of `pytest.param(endpoint, id="<family>")` tuples, one per family from D-13.

**Algorithm component extractor helper** (test_cbom_builder.py lines 105–115):
```python
def _algorithm_components(bom: Bom) -> list[Component]:
    """Return components that are CRYPTOGRAPHIC_ASSET with ALGORITHM asset type."""
    result = []
    for c in bom.components:
        if (
            c.type == ComponentType.CRYPTOGRAPHIC_ASSET
            and c.crypto_properties is not None
            and c.crypto_properties.asset_type == CryptoAssetType.ALGORITHM
        ):
            result.append(c)
    return result
```

**Assertion pattern** (test_cbom_builder.py lines 500–505):
```python
def test_dnssec_endpoint_algorithm_registered():
    ep = _dnssec_endpoint(cert_pubkey_alg="ECDSAP256SHA256", cert_pubkey_size=256)
    bom = build_cbom([ep])
    algo_refs = [c.bom_ref for c in bom.components if "crypto/algorithm/" in str(c.bom_ref)]
    assert any("ecdsap256sha256" in str(ref) for ref in algo_refs), \
        f"ECDSAP256SHA256 algorithm not found in {algo_refs}"
```

For the coverage test, the assertion is simpler: `assert len(_algorithm_components(bom)) >= 1`.

---

### `tests/test_cbom_vault_consistency.py` (test, CRUD — NEW FILE)

**Analog:** `tests/test_cbom_motion_golden.py` (golden snapshot pattern — build endpoints, normalize bom, serialize to JSON, assert identity on re-run)

**Imports pattern** (test_cbom_motion_golden.py lines 1–34):
```python
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from quirk.cbom.builder import build_cbom
from quirk.models import CryptoEndpoint
```

**Fixtures directory convention** (test_cbom_motion_golden.py line 34):
```python
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "cbom"
```

For vault consistency test, use:
```python
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "cbom" / "cbom_vault_golden.json"
```

**Snapshot normalization — the D-02 approach** (different from motion_golden.py's `_normalize_bom_for_snapshot`):

Per D-02, vault golden snapshot compares **sorted `(component.name, str(component.type))` tuples**, not the full normalized dict. This sidesteps UUID/serialNumber instability without stripping structural shape. Compare with motion_golden's approach (lines 131–177) which strips volatile fields but keeps protocol_type, cipher_suite_names, etc.

```python
def _vault_snapshot_key(bom) -> list:
    """Return sorted (name, type_str) tuples from bom components."""
    return sorted(
        (c.name, str(c.type))
        for c in bom.components
    )
```

**Write/read fixture pattern** (test_cbom_motion_golden.py lines 180–187, 222–224):
```python
def _write_snapshot(name: str, builder_fn) -> Path:
    bom = build_cbom(builder_fn())
    snap = _normalize_bom_for_snapshot(bom)
    path = FIXTURES_DIR / f"expected_{name}_cbom.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap, indent=2, sort_keys=True) + "\n")
    return path

def _load_snapshot(name: str) -> dict:
    path = FIXTURES_DIR / f"expected_{name}_cbom.json"
    return json.loads(path.read_text())
```

**REGEN env-var gate pattern** (test_cbom_motion_golden.py lines 194–215):
```python
@pytest.mark.slow
@pytest.mark.skipif(
    os.environ.get("REGEN_CBOM_FIXTURES") != "1",
    reason="set REGEN_CBOM_FIXTURES=1 to regenerate golden fixtures",
)
def test_generate_fixtures():
    ...
```

**Assertion pattern** (test_cbom_motion_golden.py lines 263–272):
```python
def test_vault_cbom_matches_snapshot():
    bom = build_cbom(_build_vault_lab_endpoints())
    actual = _normalize_bom_for_snapshot(bom)
    expected = _load_snapshot("vault")
    assert actual == expected, (
        "vault CBOM diverged from golden snapshot. If this change is "
        "intentional, run "
        "`REGEN_CBOM_FIXTURES=1 pytest ...`"
    )
```

**Note:** The existing `tests/fixtures/cbom/expected_vault_cbom.json` (4 lines, only RSA-2048) is from Phase 35 motion-lab vault endpoints. The new `cbom_vault_golden.json` is a separate fixture for the 3 deterministic Phase 61 VAULT endpoints. Do not overwrite the existing file.

---

### `tests/test_report_sanitization.py` (test, CRUD — NEW FILE)

**Analog:** `tests/test_reports_writer.py` (direct call to report function, SimpleNamespace cfg, assertion on output string)

**Imports pattern** (test_reports_writer.py lines 1–19):
```python
from __future__ import annotations

import json
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest
```

For sanitization test, imports are simpler — no mocking needed since `build_tech_markdown` is a pure function:
```python
from __future__ import annotations

import pytest

from quirk.reports.technical import build_tech_markdown
from quirk.models import CryptoEndpoint
```

**SimpleNamespace cfg pattern** (test_reports_writer.py lines 27–38):
```python
def _make_cfg(tmp_path):
    return SimpleNamespace(
        output=SimpleNamespace(directory=str(tmp_path)),
        assessment=SimpleNamespace(
            name="Phase 48 Test Assessment",
            report_owner="Test Owner",
            data_classification="Internal",
            timezone="UTC",
        ),
        ...
    )
```

For sanitization test, only `cfg.assessment.name` is used by `build_tech_markdown`:
```python
def _make_cfg():
    return SimpleNamespace(
        assessment=SimpleNamespace(name="Test Assessment"),
    )
```

**Adversarial finding pattern** (from D-12 spec):
```python
def _adversarial_finding():
    return {
        "severity": "HIGH",
        "host": "bad.host.com|injected-col",
        "port": 443,
        "title": "Finding\nWith Newline",
        "description": "Desc with | multiple | pipes",
        "recommendation": "Fix\r\nwith CRLF",
    }
```

**Assertion pattern for column-count check** (no external markdown parser needed):
```python
def test_no_unescaped_pipe_in_data_cells(adversarial_output):
    for line in adversarial_output.splitlines():
        if not line.startswith("|"):
            continue
        # Count unescaped pipes (not preceded by backslash)
        ...
```

---

## Shared Patterns

### `from __future__ import annotations`
**Source:** Every Python file in the codebase
**Apply to:** All new Python files (`_md_escape.py`, all three test files)
```python
from __future__ import annotations
```

### CryptoEndpoint construction (all fields explicit)
**Source:** `tests/test_cbom_builder.py` lines 25–38
**Apply to:** `test_cbom_coverage.py`, `test_cbom_vault_consistency.py`
```python
CryptoEndpoint(
    host="example.com", port=443, protocol="VAULT",
    tls_version=None, cipher_suite=None,
    cert_pubkey_alg="rsa-2048", cert_pubkey_size=2048,
    cert_sig_alg=None, cert_subject=None, cert_issuer=None,
    cert_not_before=None, cert_not_after=None,
    tls_capabilities_json=None, ssh_audit_json=None,
)
```
All 14 fields must be passed explicitly — CryptoEndpoint has no defaults.

### `pytest.param(..., id="<name>")` for named parametrize cases
**Source:** Project convention referenced in D-13; structure seen in `test_cbom_skip_lists.py` lines 56–59
**Apply to:** `test_cbom_coverage.py` parametrize decorator
```python
@pytest.mark.parametrize("ep", [
    pytest.param(<endpoint>, id="vault"),
    pytest.param(<endpoint>, id="database-mysql"),
    # ...
])
def test_protocol_family_emits_algo_component(ep):
    bom = build_cbom([ep])
    assert len(_algorithm_components(bom)) >= 1
```

### Docstring convention — module-level + function-level
**Source:** `tests/test_cbom_motion_golden.py` lines 1–15; `tests/test_cbom_skip_lists.py` lines 1–13
**Apply to:** All three new test files
```python
"""<one-sentence summary of what this test file guards>.

<Extended description: what phase/decision drives this, what RED/GREEN
transition is expected, what CI signal it produces.>

No production code is modified — this is fixture + test only.
"""
```

### `algo_registry` deduplication is harmless for double-registration
**Source:** `quirk/cbom/builder.py` lines 338–347 (`_register_algorithm` implementation)
**Apply to:** `quirk/cbom/builder.py` SSH fallback addition (D-07)

The SSH branch can safely call `_register_algorithm(ep.cert_pubkey_alg, ...)` even if the same
algorithm was already registered via `ssh_audit_json` parsing — the `if bom_ref_key not in registry`
guard in `_register_algorithm` makes double-registration a no-op.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `quirk/reports/_md_escape.py` | utility | transform | No existing string-escape utility module in the codebase; pattern is inferred from builder.py standalone helper functions |

---

## Metadata

**Analog search scope:** `quirk/cbom/`, `quirk/reports/`, `tests/`
**Files scanned:** 10 (builder.py, technical.py, test_cbom_builder.py, test_cbom_skip_lists.py, test_cbom_motion_golden.py, test_cbom_motion_endpoints.py, test_reports_writer.py, conftest.py, reports/__init__.py, fixtures/cbom/expected_vault_cbom.json)
**Pattern extraction date:** 2026-05-10
