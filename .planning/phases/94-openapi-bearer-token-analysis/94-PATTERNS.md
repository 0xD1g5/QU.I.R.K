# Phase 94: OpenAPI & Bearer Token Analysis — Pattern Map

**Mapped:** 2026-05-23
**Files analyzed:** 9 new/modified files
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/cli/analyze_token_cmd.py` | cli-command | request-response | `quirk/cli/errors_cmd.py` | role-match |
| `quirk/scanner/openapi_scanner.py` | scanner | file-I/O + request-response | `quirk/scanner/jwt_scanner.py` | exact |
| `quirk/cbom/builder.py` (edit) | CBOM builder | transform | `quirk/cbom/builder.py` (JWT branch) | exact |
| `quirk/intelligence/scoring.py` (edit) | scorer | transform | `quirk/intelligence/scoring.py` (agility block) | exact |
| `quirk/intelligence/evidence.py` (edit) | evidence | transform | `quirk/intelligence/evidence.py` (_PROTOCOL_KEYS) | exact |
| `run_scan.py` (edit) | entry-point | request-response | `run_scan.py` (errors intercept) | exact |
| `pyproject.toml` (edit) | config | — | `pyproject.toml` (identity extras) | exact |
| `tests/test_analyze_token.py` | test | — | `tests/test_install_all_excludes_impacket.py` (structure) | partial |
| `tests/test_openapi_scanner.py` | test | — | `tests/test_install_all_excludes_impacket.py` (structure) | partial |
| `tests/test_install_all_excludes_schemathesis.py` | test | — | `tests/test_install_all_excludes_impacket.py` | exact |

---

## Pattern Assignments

### `quirk/cli/analyze_token_cmd.py` (cli-command, request-response)

**Analog:** `quirk/cli/errors_cmd.py` (self-contained argparse module) +
`quirk/cli/init_cmd.py` (run_X entry point shape)

**Imports pattern** (`errors_cmd.py` lines 1–12):
```python
from __future__ import annotations

import argparse
import sys
from typing import Iterable

from rich.console import Console
from rich.table import Table

from quirk.errors import ERROR_REGISTRY, ErrorEntry, format_error
```

**For `analyze_token_cmd.py`, adapt imports to:**
```python
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

import jwt

from quirk.cbom.classifier import classify_algorithm
from quirk.util.safe_exc import safe_str
```

**Entry-point function shape** (`init_cmd.py` lines 7–9):
```python
def run_init(output_path: str) -> None:
    """..."""
    try:
        from rich.console import Console
        ...
    except ImportError:
        ...  # graceful degradation if rich absent
```
Adapt as `def run_analyze_token(argv: list[str]) -> None` — builds its own
`argparse.ArgumentParser(prog="quirk analyze-token")`, parses `argv`, then calls
internal helpers. Exits via `sys.exit(1)` on CRITICAL finding.

**`alg:none` CRITICAL finding pattern** (from RESEARCH Pattern 2):
```python
# TOKEN-03: case-insensitive check on decoded header dict key — NOT raw string search
alg = header.get("alg", "")
if alg.lower() == "none":
    # ... build finding, set severity="CRITICAL", call sys.exit(1) after report
```

**safe_str scrub pattern** (`jwt_scanner.py` line 339):
```python
logger.v(f"JWT scan error for {base_url}: {safe_str(exc)}")
# Wrap any exception message in safe_str() before printing/logging — TOKEN never logged raw
```

**Graceful opaque-token handling** (RESEARCH Open Question 3):
```python
try:
    header = jwt.get_unverified_header(raw_token)
except jwt.exceptions.DecodeError:
    # Report "opaque token" with INFO severity, exit 0 (non-CRITICAL)
    print("token does not appear to be a JWT (opaque token) — cannot classify")
    return
```

---

### `quirk/scanner/openapi_scanner.py` (scanner, file-I/O + request-response)

**Analog:** `quirk/scanner/jwt_scanner.py` (full file)

**Imports pattern** (`jwt_scanner.py` lines 1–27):
```python
"""JWT/JWKS scanner module (SCAN-03).
...
"""
import base64
import json
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from quirk.models import CryptoEndpoint
from quirk.util.safe_exc import safe_str
from quirk.util.url_allowlist import validate_external_url
```

Adapt for openapi_scanner.py — replace httpx guard with openapi_spec_validator guard:
```python
try:
    from openapi_spec_validator import validate as _oas_validate
    OPENAPI_AVAILABLE = True
except ImportError:
    OPENAPI_AVAILABLE = False
```

**SSRF/availability guard pattern** (`jwt_scanner.py` lines 222–223 and 301–302):
```python
if not HTTPX_AVAILABLE:
    return []
```
Mirror as:
```python
if not OPENAPI_AVAILABLE:
    return [CryptoEndpoint(
        host="<spec-path>", port=0, protocol="OpenAPI",
        scan_error_category="missing_extra",
        service_detail="openapi-spec-validator not installed; install quirk[api]",
        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )]
```

**URL validation before fetch** (`jwt_scanner.py` lines 150–153):
```python
_vr_base = validate_external_url(url)
if not _vr_base.ok:
    continue
```
For openapi_scanner.py URL path (SPEC-02 scope gate):
```python
vr = validate_external_url(url)
if not vr.ok:
    raise SpecParsingError(
        f"OpenAPI spec URL rejected ({vr.reason}): {vr.redacted_preview!r}"
    )
```

**CryptoEndpoint construction pattern** (`jwt_scanner.py` lines 269–281):
```python
ep = CryptoEndpoint(
    host=base_url,
    port=443,
    protocol="JWT",
    cert_pubkey_alg=alg,
    cert_pubkey_size=key_bits,
    jwt_scan_json=json.dumps(key_entry),
    service_detail=jwks_path,
    scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
)
```
For OpenAPI findings, use `protocol="OpenAPI"` and populate `service_detail` with the finding
category (e.g., `"plaintext_server"`, `"unauthenticated_endpoint"`, `"security_scheme:<name>"`).

**Exception swallowing pattern** (`jwt_scanner.py` lines 334–340):
```python
except Exception as exc:
    if logger:
        logger.v(f"JWT scan error for {base_url}: {safe_str(exc)}")
```
Mirror in openapi_scanner.py for any parse/fetch failure.

---

### `quirk/cbom/builder.py` — JWT branch edit (CBOM builder, transform)

**Analog:** `quirk/cbom/builder.py` lines 436–439 (JWT Pass-1 branch) — exact match

**JWT Pass-1 branch** (lines 436–439):
```python
elif ep.protocol == "JWT":
    # JWT: cert_pubkey_alg holds algorithm (RS256, ES256, etc.)
    if ep.cert_pubkey_alg:
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
```

Add immediately after this block:
```python
elif ep.protocol == "BEARER_TOKEN":
    # TOKEN-02: operator-supplied bearer credential, classified passively.
    # service_detail carries "declared_algorithm (unverified)" label per CONTEXT D.
    if ep.cert_pubkey_alg:
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)

elif ep.protocol == "OpenAPI":
    # SPEC-01: OpenAPI security scheme algorithm (e.g. RS256 from bearerFormat)
    if ep.cert_pubkey_alg:
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
```

**Pass-3 skip list** (`builder.py` line 694 — existing JWT entry):
```python
"JWT", "CONTAINER", "SOURCE", "AWS", "AZURE",
*DAR_SKIP_PROTOCOLS,
*MOTION_PLAINTEXT_PROTOCOLS,
```
Add `"BEARER_TOKEN"` and `"OpenAPI"` to this skip tuple (no ProtocolProperties component needed).

**`_emit_coverage_note` pattern** (`builder.py` lines 377–393, referenced at line 444–450):
```python
def _emit_coverage_note(bom_component: Component | None, note: str) -> None:
    ...
# Usage — emit at end of pass:
coverage_notes.append("bearer-token-declared-algorithm")
```

---

### `quirk/intelligence/scoring.py` — SCORE_WEIGHTS edit (scorer, transform)

**Analog:** `quirk/intelligence/scoring.py` lines 54–58 (agility block) — exact match

**Existing agility weights block** (lines 54–58):
```python
"agility_high_impact_ratio": 14.0,
"agility_unknown_ratio": 6.0,
"agility_rsa_only_penalty": 8.0,
"agility_has_ecdsa_bonus": 4.0,
"agility_pqc_hybrid_bonus": 8.0,   # Phase 90 PQC-03 — X25519MLKEM768 ceiling anchor
```

Append two new entries in the same block:
```python
"agility_weak_jwt_alg_ratio": 6.0,          # Phase 94 SCORE-01 — alg:none / weak in bearer token
"agility_openapi_plaintext_ratio": 4.0,     # Phase 94 SCORE-01 — OpenAPI spec declares http:// servers
```

**Scoring function** — add agility_impacts entries in `compute_intelligence_report()` (lines 212–223):
```python
agility_impacts: List[Tuple[str, float]] = [
    ("High-impact findings", -_ratio(...) * w["agility_high_impact_ratio"]),
    ...
    ("PQC-hybrid key exchange (X25519MLKEM768)", w["agility_pqc_hybrid_bonus"]),
    # Phase 94 — new:
    ("Weak/unsigned JWT algorithm in bearer token", -_ratio(...) * w["agility_weak_jwt_alg_ratio"]),
    ("OpenAPI plaintext server URLs", -_ratio(...) * w["agility_openapi_plaintext_ratio"]),
]
```

---

### `quirk/intelligence/evidence.py` — _PROTOCOL_KEYS edit (evidence, transform)

**Analog:** `quirk/intelligence/evidence.py` lines 11–15 — exact match

**Existing `_PROTOCOL_KEYS` tuple** (lines 11–15):
```python
_PROTOCOL_KEYS = ("TLS", "HTTP", "SSH", "UNKNOWN", "KERBEROS", "SAML", "DNSSEC",
                  "POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "KUBERNETES", "VAULT",
                  "CONTAINER", "SOURCE", "AWS", "AZURE", "GCP", "CLOUD_SQL")
```

Add `"BEARER_TOKEN"` and `"OpenAPI"` to this tuple (maintains protocol_counts inventory).

**Counter pattern for new agility evidence keys** — mirror `dar_db_plaintext_count` pattern
(lines 99 and 243–255):
```python
dar_db_plaintext_count = 0    # PG ssl=off + MySQL SSL disabled
# ...
if ep.protocol == "POSTGRESQL" and ...:
    dar_db_plaintext_count += 1
# ...
"dar_db_plaintext_ratio": round(dar_db_plaintext_count / total_endpoints, 4) if total_endpoints else 0.0,
```
Mirror for new counters:
```python
bearer_token_weak_alg_count = 0   # Phase 94 SCORE-01
openapi_plaintext_server_count = 0  # Phase 94 SCORE-01
# ... in loop:
if ep.protocol == "BEARER_TOKEN" and ep.cert_pubkey_alg and ep.cert_pubkey_alg.lower() != "none":
    bearer_token_weak_alg_count += 1  # all currently quantum-vulnerable
# ... returned dict:
"bearer_token_weak_alg_count": bearer_token_weak_alg_count,
"agility_weak_jwt_alg_ratio": round(bearer_token_weak_alg_count / max(total_endpoints, 1), 4),
"openapi_plaintext_server_count": openapi_plaintext_server_count,
"agility_openapi_plaintext_ratio": round(openapi_plaintext_server_count / max(total_endpoints, 1), 4),
```

---

### `run_scan.py` — `analyze-token` subcommand intercept (entry-point, request-response)

**Analog:** `run_scan.py` lines 483–487 (errors intercept) — exact match

**Simplest intercept form** (lines 483–487):
```python
# --- errors subcommand: intercept before scan argparse (Phase 68 UX-01) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "errors":
    from quirk.cli.errors_cmd import run_errors
    run_errors(_sys.argv[2:])
    return
```

Add before the `errors` block (or after — order doesn't matter, intercepts are checked top-to-bottom):
```python
# --- analyze-token subcommand: intercept before scan argparse (Phase 94 TOKEN-01) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "analyze-token":
    from quirk.cli.analyze_token_cmd import run_analyze_token
    run_analyze_token(_sys.argv[2:])
    return
```

No `return` on the errors intercept is needed — each intercept already returns. The `import sys as _sys`
is already present at the top of `main()` (line 364).

---

### `pyproject.toml` — `[api]` extras group (config)

**Analog:** `pyproject.toml` lines 43–54 (identity + adcs extras) — exact match

**Pattern to follow** (lines 43–54):
```toml
identity = [
    "impacket>=0.13.0,<0.14",
    "ldap3>=2.9.1",
]
# Phase 80 ADCS-07: dedicated extras group for the AD CS scanner. Lists ONLY
# ldap3 (NOT impacket) so that quirk[adcs] can safely be included in [all]
# ...
adcs = [
    "ldap3>=2.9.1",
]
```

Add new `[api]` group after `adcs`:
```toml
api = [
    "openapi-spec-validator>=0.9.0",
]
```

**`[all]` meta-extra** (lines 78–90): do NOT add `"quirk-scanner[api]"` to the `[all]` list.
The guarding comment pattern:
```toml
# NOTE: quirk[identity] is INTENTIONALLY EXCLUDED from [all] -- impacket
# transitively pulls pyOpenSSL which downgrades cryptography and breaks the
# TLS scanner. See Phase 45 / D-01. tests/test_install_all_excludes_impacket.py
# guards this; do NOT add quirk[identity] to the list above.
```
Mirror as a comment after the `all` block:
```toml
# NOTE: quirk[api] is INTENTIONALLY EXCLUDED from [all] -- Phase 96 will add
# schemathesis to [api]. tests/test_install_all_excludes_schemathesis.py guards
# this; do NOT add quirk[api] to [all] until Phase 96 schemathesis scoping is complete.
```

---

### `tests/test_install_all_excludes_schemathesis.py` (test, CI guard)

**Analog:** `tests/test_install_all_excludes_impacket.py` (full file) — exact copy pattern

**Full structure to mirror** (lines 1–119):
- Module docstring explaining Phase 94 PKG-01 rationale (replace impacket references with schemathesis)
- `REPO_ROOT = Path(__file__).resolve().parent.parent`
- `@pytest.mark.slow` decorator
- `pip install --dry-run --ignore-installed --quiet --report <report_path> -e <repo>[all]` subprocess
- `assert result.returncode == 0` with diagnostic message
- `assert "does not provide the extra 'all'" not in combined_output` (vacuous-pass guard)
- `report = json.loads(report_path.read_text())`
- `installed = {item["metadata"]["name"].lower() for item in report.get("install", []) ...}`
- **Sanity check:** assert `openapi-spec-validator` IS in installed (proves `[api]` is reachable — but `[api]` is NOT in `[all]`, so this check must confirm `openapi-spec-validator` is NOT present to guard against accidental `[api]` inclusion)
- Primary assertion: `assert "schemathesis" not in installed`

**Key assertion text to adapt** (`test_install_all_excludes_impacket.py` lines 113–119):
```python
assert "impacket" not in installed, (
    "REGRESSION: impacket is present in the resolved set for quirk[all]. "
    "Phase 45 / D-01: impacket transitively pulls pyOpenSSL which "
    "downgrades the cryptography library and breaks the TLS scanner. "
    "Remove quirk[identity] from the [all] meta-extra in pyproject.toml. "
    f"Resolved packages: {sorted(installed)}"
)
```
Adapt:
```python
assert "schemathesis" not in installed, (
    "REGRESSION: schemathesis is present in the resolved set for quirk[all]. "
    "Phase 94 PKG-01: schemathesis is reserved for [api] extras (added Phase 96). "
    "Remove quirk[api] from the [all] meta-extra in pyproject.toml. "
    f"Resolved packages: {sorted(installed)}"
)
```

**Sanity check** — replace the `expected_from_all` set check with a check that `openapi-spec-validator`
is NOT in the resolved set (since `[api]` must not be in `[all]`):
```python
# Confirm [api] is not silently pulled into [all]
assert "openapi-spec-validator" not in installed, (
    "quirk[all] unexpectedly resolved openapi-spec-validator. "
    "Phase 94 PKG-01: [api] must not be included in [all]. "
    f"Resolved packages: {sorted(installed)}"
)
```
Keep the original `expected_from_all` check as well to confirm `[all]` didn't regress.

---

### `tests/test_score_weights_invariant.py` — edit (test, invariant)

**Analog:** itself — file already exists at `tests/test_score_weights_invariant.py`

**Current assertions** (lines 22 and 36):
```python
assert abs(sum(SCORE_WEIGHTS.values()) - 283.0) < 1e-9, (...)
assert len(SCORE_WEIGHTS) == 37
```

Update both to:
```python
assert abs(sum(SCORE_WEIGHTS.values()) - 293.0) < 1e-9, (...)
assert len(SCORE_WEIGHTS) == 39
```

Update the docstring history in `test_score_weights_sum_invariant`:
```
Phase 94 SCORE-01: bumped from 283.0 -> 293.0 (+10.0):
  - agility_weak_jwt_alg_ratio: +1 entry at +6.0
  - agility_openapi_plaintext_ratio: +1 entry at +4.0
Net delta = +2 entries / +10.0 sum (37 -> 39, 283.0 -> 293.0).
```

---

## Shared Patterns

### Optional-import graceful degradation
**Source:** `quirk/scanner/jwt_scanner.py` lines 18–22
**Apply to:** `quirk/scanner/openapi_scanner.py`
```python
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
```
In openapi_scanner.py, the degraded path emits a `CryptoEndpoint` with
`scan_error_category="missing_extra"` and returns a list (never raises). Mirror the early-return
guard at the top of the public scan function.

### `safe_str` exception scrubbing
**Source:** `quirk/scanner/jwt_scanner.py` line 339; imported from `quirk/util/safe_exc`
**Apply to:** `quirk/cli/analyze_token_cmd.py`, `quirk/scanner/openapi_scanner.py`
```python
from quirk.util.safe_exc import safe_str
# ...
except Exception as exc:
    print(f"analysis error: {safe_str(exc)}")
```
Wrapping any exception that might carry token bytes or spec content in `safe_str()` before
printing or logging satisfies AUTH-02 / LEAK-03.

### `validate_external_url` SSRF guard
**Source:** `quirk/util/url_allowlist.py` lines 95–161
**Apply to:** `quirk/scanner/openapi_scanner.py` (URL fetch path and `$ref` pre-scan)
```python
from quirk.util.url_allowlist import validate_external_url
vr = validate_external_url(url)
if not vr.ok:
    raise SpecParsingError(f"... ({vr.reason}): {vr.redacted_preview!r}")
```
The `_redact_preview` helper is also available for building `SpecParsingError` messages that
contain partial URL previews (import via `from quirk.util.url_allowlist import _redact_preview`
per RESEARCH code example line 569).

### `CryptoEndpoint` construction with scanned_at
**Source:** `quirk/scanner/jwt_scanner.py` lines 269–281 and 244–252
**Apply to:** `quirk/scanner/openapi_scanner.py`, `quirk/cli/analyze_token_cmd.py` (TOKEN-03)
```python
ep = CryptoEndpoint(
    host=...,
    port=0,
    protocol="OpenAPI",          # or "BEARER_TOKEN"
    cert_pubkey_alg=alg,
    service_detail="...",
    severity="HIGH",             # or "CRITICAL" for alg:none
    scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
)
```
Always use `.replace(tzinfo=None)` to produce a tz-naive UTC datetime (matches DB column type).

### Subcommand intercept shape
**Source:** `run_scan.py` lines 483–487
**Apply to:** `run_scan.py` (new `analyze-token` block)
```python
if len(_sys.argv) > 1 and _sys.argv[1] == "errors":
    from quirk.cli.errors_cmd import run_errors
    run_errors(_sys.argv[2:])
    return
```
Three lines: guard, lazy import, delegate with `_sys.argv[2:]`, then `return`. No inline argparse —
all argparse lives in the cmd module.

---

## No Analog Found

All files have close analogs in the codebase. No files require falling back to RESEARCH.md
patterns as primary references.

---

## Metadata

**Analog search scope:** `quirk/scanner/`, `quirk/cli/`, `quirk/cbom/`, `quirk/intelligence/`,
`tests/`, `run_scan.py`, `pyproject.toml`
**Files scanned:** 12 source files read + grep output from 6 additional files
**Pattern extraction date:** 2026-05-23
