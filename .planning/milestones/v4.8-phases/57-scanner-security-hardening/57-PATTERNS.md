# Phase 57: Scanner Security Hardening - Pattern Map

**Mapped:** 2026-05-09
**Files analyzed:** 12 new/modified files
**Analogs found:** 11 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/util/url_allowlist.py` | utility | request-response | `quirk/util/targets.py` | role-match |
| `quirk/util/subprocess_input.py` | utility | request-response | `quirk/util/targets.py` | role-match |
| `quirk/scanner/jwt_scanner.py` | scanner | request-response | self (modify) | exact |
| `quirk/scanner/saml_scanner.py` | scanner | request-response | self (modify) | exact |
| `quirk/scanner/source_scanner.py` | scanner | batch | self (modify) | exact |
| `quirk/scanner/container_scanner.py` | scanner | batch | self (modify) | exact |
| `quirk/scanner/broker_scanner.py` | scanner | request-response | self (modify) | exact |
| `quirk/models.py` | model | CRUD | self (modify) | exact |
| `quirk/config_template.yaml` | config | — | self (modify) | exact |
| `quirk/config.py` | config | — | self (modify) | exact |
| `run_scan.py` (CLI flags) | CLI entrypoint | request-response | self (modify) | exact |
| `tests/util/` + `tests/scanner/` | test | — | `tests/test_targets_parser.py`, `tests/test_source_scanner.py` | exact |

---

## Pattern Assignments

### `quirk/util/url_allowlist.py` (utility, request-response)

**Analog:** `quirk/util/targets.py`

**Module docstring pattern** (`quirk/util/targets.py` lines 1–28):
```python
"""Multi-target parser for QUIRK — Phase 47 / MULTI-01..05.

Decision enforcement:
  D-01: ...

Public surface:
  function_one(arg) -> ReturnType
  function_two(arg) -> ReturnType
"""
from __future__ import annotations
```

**NamedTuple / dataclass result pattern** — The module uses no shared result type today, but the new `ValidationResult` shape `(ok: bool, reason: str, redacted_preview: str)` should be a `NamedTuple` or frozen `@dataclass`. Mirror the `OptionalExtra` frozen dataclass style from `quirk/util/optional_extra.py` lines 45–73:
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason: str          # enum-like reason code e.g. "internal_ip"
    redacted_preview: str
```

**Reason-code enum pattern** — Use a module-level string enum or `str` constants (matches how `quirk/util/optional_extra.py` uses module-level constants, not an `Enum` subclass):
```python
# Reason codes (D-03) — fixed set of string constants
RC_INTERNAL_IP = "internal_ip"
RC_LOOPBACK = "loopback"
RC_METADATA_SERVICE_IP = "metadata_service_ip"
RC_SCHEME_PREFIX = "scheme_prefix"
RC_LINK_LOCAL = "link_local"
```

**Validation function signature** (mirror `apply_targets_file_override` pattern, `targets.py` lines 205–224):
```python
def validate_external_url(url: str, *, allow_internal: bool = False) -> ValidationResult:
    """Validate url is safe to fetch externally (CR-04/CR-06).

    Rejects RFC1918, link-local, loopback, file://, and cloud-metadata IPs
    unless allow_internal=True.

    Args:
        url: The URL string to validate.
        allow_internal: If True, RFC1918/loopback/link-local addresses are accepted.

    Returns:
        ValidationResult(ok=True, reason="", redacted_preview="") on success.
        ValidationResult(ok=False, reason=<reason_code>, redacted_preview=<snippet>) on rejection.
    """
```

---

### `quirk/util/subprocess_input.py` (utility, request-response)

**Analog:** `quirk/util/targets.py`

**Module docstring pattern** — Same `"""Phase 57 / CR-02..CR-03. Decision enforcement: ..."""` style.

**Validation function pair** — Two sibling functions in the same module (D-02):
```python
def validate_repo_path(p: str) -> ValidationResult:
    """Validate p is safe to pass to semgrep (CR-02).
    No shell metacharacters, no '..', must be an existing local directory.
    """

def validate_image_ref(r: str) -> ValidationResult:
    """Validate r is safe to pass to syft (CR-03).
    registry/image:tag regex form, no dir:/, no file://, no shell metacharacters.
    """
```

**Redacted preview pattern** (D-08 — strip control chars, truncate to 32 chars):
```python
import re

def _redact_preview(raw: str, max_len: int = 32) -> str:
    """Strip control characters; truncate to max_len for forensic preview."""
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", raw)
    return cleaned[:max_len]
```

---

### `quirk/scanner/jwt_scanner.py` (scanner, request-response) — MODIFY

**Sites to fix:** lines 56 and 67 — `verify=False` on both `httpx.get` calls.

**Before (lines 56, 67):**
```python
resp = httpx.get(url, timeout=timeout, follow_redirects=True, verify=False)
# ...
resp2 = httpx.get(jwks_uri, timeout=timeout, follow_redirects=True, verify=False)
```

**After pattern** — Add `allow_insecure_jwks` parameter threading from `scan_jwt_endpoint` down to `_fetch_jwks`, with advisory emission on opt-in:
```python
def _fetch_jwks(base_url: str, timeout: int, verify_tls: bool = True) -> ...:
    # ...
    resp = httpx.get(url, timeout=timeout, follow_redirects=True, verify=verify_tls)
```

**Advisory emission pattern** (D-09 — mirror `aws_connector.py` HIGH advisory shape, lines 285–296):
```python
# When allow_insecure_jwks=True, emit one advisory CryptoEndpoint per affected URL:
advisory = CryptoEndpoint(
    host=base_url,
    port=443,
    protocol="ADVISORY",
    service_detail="JWKS/verify-disabled",
    severity="HIGH",
    scan_error_category="config",
    scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
)
```

**Existing imports** (`jwt_scanner.py` lines 1–17):
```python
import base64
import json
from datetime import datetime, timezone
from typing import List, Optional

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from quirk.models import CryptoEndpoint
```

---

### `quirk/scanner/saml_scanner.py` (scanner, request-response) — MODIFY

**Site:** `_fetch_metadata` function (lines 57–75).

**Current pattern** (already uses `verify=True` — only needs URL allowlist guard added before fetch):
```python
def _fetch_metadata(url: str, timeout: int) -> "bytes | None":
    try:
        import httpx
        response = httpx.get(url, timeout=timeout, follow_redirects=True, verify=True)
```

**New pattern** — inject `allow_internal: bool = False` parameter and call `validate_external_url` before the `httpx.get`:
```python
from quirk.util.url_allowlist import validate_external_url

def _fetch_metadata(url: str, timeout: int, allow_internal: bool = False) -> "bytes | None":
    result = validate_external_url(url, allow_internal=allow_internal)
    if not result.ok:
        logging.getLogger(__name__).warning(
            "SAML: blocked fetch to %s (%s)", result.redacted_preview, result.reason
        )
        return None
    # ... existing httpx.get call unchanged ...
```

**Advisory emission for opt-in** (D-09, `service_detail="SAML/internal-target-fetched"`):
```python
advisory = CryptoEndpoint(
    host=host,
    port=port,
    protocol="ADVISORY",
    service_detail="SAML/internal-target-fetched",
    severity="HIGH",
    scan_error_category="config",
    scanned_at=now,
)
```

---

### `quirk/scanner/source_scanner.py` (scanner, batch) — MODIFY

**Site:** `scan_source_repo` before `subprocess.run` call (lines 38–43).

**Current subprocess pattern** (`source_scanner.py` lines 38–43):
```python
proc = subprocess.run(
    [exe, "--json", "--config", "p/cryptography", repo_path],
    capture_output=True,
    text=True,
    timeout=timeout,
)
```

**New pattern** — call `validate_repo_path` before subprocess, write rejection row on failure:
```python
from quirk.util.subprocess_input import validate_repo_path

result = validate_repo_path(repo_path)
if not result.ok:
    if logger:
        logger.v(f"SOURCE rejected {result.redacted_preview!r}: {result.reason}")
    return [CryptoEndpoint(
        host=result.redacted_preview,
        port=0,
        protocol="SOURCE",
        scan_error=result.reason,
        scan_error_category="invalid_input",
        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )]
# ... existing subprocess.run call unchanged ...
```

---

### `quirk/scanner/container_scanner.py` (scanner, batch) — MODIFY

**Site:** `scan_container_image` before `subprocess.run` call (lines 61–68).

**Current subprocess pattern** (`container_scanner.py` lines 61–68):
```python
proc = subprocess.run(
    [exe, image_ref, "-o", "json"],
    capture_output=True,
    text=True,
    timeout=timeout,
)
```

**New pattern** — call `validate_image_ref` before subprocess, write rejection row on failure (same shape as source_scanner rejection row above):
```python
from quirk.util.subprocess_input import validate_image_ref

result = validate_image_ref(image_ref)
if not result.ok:
    if logger:
        logger.v(f"CONTAINER rejected {result.redacted_preview!r}: {result.reason}")
    return [CryptoEndpoint(
        host=result.redacted_preview,
        port=0,
        protocol="CONTAINER",
        scan_error=result.reason,
        scan_error_category="invalid_input",
        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )]
```

---

### `quirk/scanner/broker_scanner.py` (scanner, request-response) — MODIFY

**CR-05 site:** `_enrich_rabbitmq_mgmt`, line 313 — `b"guest:guest"` hardcoded credentials.

**Current pattern** (`broker_scanner.py` lines 305–337):
```python
def _enrich_rabbitmq_mgmt(host: str, port: int = 15672, logger=None) -> dict:
    url = f"http://{host}:{port}/api/overview"
    credentials = base64.b64encode(b"guest:guest").decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {credentials}"})
```

**New pattern** — accept optional `credentials` dict and `allow_cleartext` flag; look up env var:
```python
def _enrich_rabbitmq_mgmt(
    host: str,
    port: int = 15672,
    logger=None,
    credentials: "dict | None" = None,
    allow_cleartext: bool = False,
) -> dict:
    """CR-05/CR-06: no default credentials; cleartext blocked unless allow_cleartext=True."""
    if not allow_cleartext:
        # no HTTP probing without explicit opt-in
        return {}
    url = f"http://{host}:{port}/api/overview"
    if credentials:
        user = credentials.get("user", "")
        pass_env = credentials.get("pass_env", "")
        password = os.environ.get(pass_env, "") if pass_env else ""
        if not password:
            # pass_env unset → skip credential probe, fall back to anonymous (D-05)
            req = urllib.request.Request(url)
        else:
            creds_bytes = base64.b64encode(f"{user}:{password}".encode()).decode()
            req = urllib.request.Request(url, headers={"Authorization": f"Basic {creds_bytes}"})
    else:
        req = urllib.request.Request(url)
```

**Advisory emission for credential probe** (D-09, `service_detail="BROKER/credential-probe"`):
```python
advisory = CryptoEndpoint(
    host=host,
    port=port,
    protocol="ADVISORY",
    service_detail="BROKER/credential-probe",
    severity="HIGH",
    scan_error_category="config",
    scanned_at=now,
)
```

**CR-06 site:** `_enrich_redis_config`, line 640 — `ssl_cert_reqs="none"`.

**Current pattern** (`broker_scanner.py` line 639–641):
```python
r = redis_lib.Redis(
    host=host, port=port, ssl=True, ssl_cert_reqs="none",
    socket_timeout=5, socket_connect_timeout=5,
)
```

**New pattern** — default to `ssl_cert_reqs="required"`; only `"none"` when `allow_cleartext=True` with advisory:
```python
ssl_cert_reqs = "none" if allow_cleartext else "required"
r = redis_lib.Redis(
    host=host, port=port, ssl=True, ssl_cert_reqs=ssl_cert_reqs,
    socket_timeout=5, socket_connect_timeout=5,
)
```

**Advisory for cleartext/no-verify broker** (`service_detail="BROKER/cleartext-mgmt-api"`):
```python
advisory = CryptoEndpoint(
    host=host,
    port=port,
    protocol="ADVISORY",
    service_detail="BROKER/cleartext-mgmt-api",
    severity="HIGH",
    scan_error_category="config",
    scanned_at=now,
)
```

---

### `quirk/models.py` (model) — MODIFY

**Site:** line 36 — extend `scan_error_category` docstring comment.

**Current pattern** (`models.py` line 36):
```python
scan_error_category = Column(String(32), nullable=True)  # Phase 41 D-11: missing_extra|timeout|exception|config
```

**New pattern** (D-06 — add `invalid_input` to the comment):
```python
scan_error_category = Column(String(32), nullable=True)  # Phase 41 D-11: missing_extra|timeout|exception|config|invalid_input
```

No migration needed — this is a doc-string-only change to an existing nullable column.

---

### `quirk/config_template.yaml` (config) — MODIFY

**Analog:** existing `connectors:` block structure (`config_template.yaml` lines 47–110).

**Pattern for new blocks** — add at the end of the file, using the same comment style as existing blocks:
```yaml
# -- Security hardening (Phase 57 / HARDEN-SCAN-01..06) --------------------
# These knobs disable safety checks that protect against SSRF and credential
# exposure. Each opt-in emits a HIGH advisory finding naming the affected target.
# CLI flags override per-run: --allow-internal-targets, --allow-cleartext-broker-probe,
# --allow-insecure-jwks.
security:
  allow_internal_targets: false        # CR-04: permit RFC1918/loopback SAML/broker URLs
  allow_cleartext_broker_probe: false  # CR-06: permit HTTP/no-TLS broker mgmt API probes
  allow_insecure_jwks: false           # CR-01: permit verify=False JWKS fetches

# -- Broker credentials (Phase 57 / CR-05) ---------------------------------
# Per-host opt-in credentials for broker management API probes.
# Keyed by host:port. Passwords MUST be in environment variables (never inline).
# broker_credentials:
#   "rabbit.lab:15672":
#     user: "admin"
#     pass_env: "RABBIT_LAB_PASS"   # os.environ["RABBIT_LAB_PASS"] at scan time
```

---

### `quirk/config.py` (config) — MODIFY

**Analog:** `IntelligenceCfg` dataclass + `config_from_dict` block (lines 256–383).

**New SecurityCfg dataclass** — mirror `IntelligenceCfg` shape (lines 256–267):
```python
@dataclass
class SecurityCfg:
    """Phase 57 / D-04: operator safety-override knobs.

    All default False — operators must explicitly opt in.
    """
    allow_internal_targets: bool = False
    allow_cleartext_broker_probe: bool = False
    allow_insecure_jwks: bool = False
```

**BrokerCredential dataclass** — for D-05 per-host credentials:
```python
@dataclass(frozen=True)
class BrokerCredential:
    user: str
    pass_env: str
```

**AppConfig extension** — add `security` and `broker_credentials` fields:
```python
@dataclass
class AppConfig:
    assessment: AssessmentCfg
    scan: ScanCfg
    targets: TargetsCfg
    connectors: ConnectorsCfg
    output: OutputCfg
    intelligence: IntelligenceCfg
    security: SecurityCfg = field(default_factory=SecurityCfg)   # Phase 57 D-04
    broker_credentials: Dict[str, BrokerCredential] = field(default_factory=dict)  # Phase 57 D-05
```

**config_from_dict loading pattern** — mirror the `intel_raw` block (lines 299–330):
```python
security_raw = raw.get("security") or {}
security_cfg = SecurityCfg(
    allow_internal_targets=bool(security_raw.get("allow_internal_targets", False)),
    allow_cleartext_broker_probe=bool(security_raw.get("allow_cleartext_broker_probe", False)),
    allow_insecure_jwks=bool(security_raw.get("allow_insecure_jwks", False)),
)

broker_creds_raw = raw.get("broker_credentials") or {}
broker_credentials: Dict[str, BrokerCredential] = {}
for host_port, cred in broker_creds_raw.items():
    broker_credentials[str(host_port)] = BrokerCredential(
        user=str(cred.get("user", "")),
        pass_env=str(cred.get("pass_env", "")),
    )
```

---

### `run_scan.py` CLI flags — MODIFY

**Analog:** existing `--targets-file` and broker namespace flags (`run_scan.py` lines 264–304).

**`--targets-file` flag pattern** (lines 264–270) — exact model for the three new `store_true` flags:
```python
parser.add_argument(
    "--targets-file",
    help=(
        "Path to file of targets (one per line, '#' comments). "
        "Replaces config targets entirely (does NOT merge). Phase 47 / D-03."
    ),
)
```

**Three new flags** — add after existing broker flags (after line 304):
```python
# Phase 57 / D-04: security hardening opt-outs
parser.add_argument(
    "--allow-internal-targets",
    action="store_true", default=False,
    help="Permit SAML/broker fetches to RFC1918, loopback, and link-local IPs. "
         "Emits HIGH advisory per affected target. Phase 57 / CR-04.",
)
parser.add_argument(
    "--allow-cleartext-broker-probe",
    action="store_true", default=False,
    help="Permit broker management API probes over HTTP (no TLS). "
         "Emits HIGH advisory per affected target. Phase 57 / CR-06.",
)
parser.add_argument(
    "--allow-insecure-jwks",
    action="store_true", default=False,
    help="Disable TLS certificate verification for JWKS fetches. "
         "Emits HIGH advisory per affected target. Phase 57 / CR-01.",
)
```

**CLI-overrides-YAML wire-up pattern** — mirror Phase 47 / D-03 (lines 346–348):
```python
# Phase 57 / D-04: CLI flags override YAML security block per-run
if getattr(args, "allow_internal_targets", False):
    cfg.security.allow_internal_targets = True
if getattr(args, "allow_cleartext_broker_probe", False):
    cfg.security.allow_cleartext_broker_probe = True
if getattr(args, "allow_insecure_jwks", False):
    cfg.security.allow_insecure_jwks = True
```

---

### `tests/util/test_url_allowlist.py` and `tests/util/test_subprocess_input.py` (tests)

**Analog:** `tests/test_targets_parser.py` (lines 1–37) for util test structure.

**Test file header pattern** (`test_targets_parser.py` lines 1–17):
```python
"""Tests for quirk/util/targets.py — multi-target parser (Phase 47 / MULTI-01..05).

Covers:
  - CSV split (MULTI-01)
  ...
"""
import os
import pytest

from quirk.util.targets import parse_target_tokens, load_targets_file
```

**Parametrize-heavy test style** — use `@pytest.mark.parametrize` for exhaustive input coverage (all forbidden categories, all allowed categories). Each forbidden category is a separate test or parametrize case.

**Test isolation pattern** — no network, no subprocess. All tests are pure unit tests on the helper's logic.

---

### `tests/scanner/test_jwt_hardening.py`, `tests/scanner/test_saml_hardening.py`, etc. (integration tests)

**Analog:** `tests/test_source_scanner.py` and `tests/test_container_scanner.py` for the subprocess-mock / httpx-mock pattern.

**Subprocess mock pattern** (`test_source_scanner.py` lines 44–46, 55–57):
```python
with patch("shutil.which", return_value=None):
    endpoints = scan_source_repo("/path/to/repo", timeout=120)
    assert endpoints == []

with patch("shutil.which", return_value="/usr/bin/semgrep"), \
     patch("subprocess.run", return_value=mock_proc):
    endpoints = scan_source_repo("/path/to/repo", timeout=120)
```

**httpx mock pattern** (`test_jwt_scanner.py` lines 50–53):
```python
with patch("quirk.scanner.jwt_scanner.httpx") as mock_httpx:
    mock_httpx.get.return_value = mock_response
    endpoints = scan_jwt_endpoint("https://api.example.com", timeout=5)
```

**Rejection row assertion pattern** — for CR-02/CR-03 tests, assert that:
1. `subprocess.run` is **never called** (use `MagicMock` and assert `call_count == 0`)
2. The returned list contains exactly one `CryptoEndpoint` with `scan_error_category="invalid_input"`
3. `host` equals the 32-char redacted preview (not the raw malicious input)

```python
with patch("subprocess.run") as mock_run, \
     patch("shutil.which", return_value="/usr/bin/semgrep"):
    endpoints = scan_source_repo("../../etc/passwd", timeout=120)
    assert mock_run.call_count == 0
    assert len(endpoints) == 1
    assert endpoints[0].scan_error_category == "invalid_input"
    assert endpoints[0].scan_error == "path_traversal"
```

---

## Shared Patterns

### Advisory Emission (HIGH severity opt-out findings)

**Source:** `quirk/scanner/aws_connector.py` lines 246–296 (S3 classification + endpoint build)

**Apply to:** `jwt_scanner.py` (CR-01), `saml_scanner.py` (CR-04), `broker_scanner.py` (CR-05/CR-06)

The four `service_detail` constants should be defined at module level so QRAMM/remediation copy can reference them by name (per CONTEXT.md specifics section):

```python
# Module-level advisory constants — greppable by QRAMM/remediation copy
ADVISORY_JWKS_VERIFY_DISABLED   = "JWKS/verify-disabled"
ADVISORY_SAML_INTERNAL_TARGET   = "SAML/internal-target-fetched"
ADVISORY_BROKER_CLEARTEXT       = "BROKER/cleartext-mgmt-api"
ADVISORY_BROKER_CREDENTIAL      = "BROKER/credential-probe"
```

Advisory `CryptoEndpoint` shape (D-09 — one per affected target, not once per scan):
```python
CryptoEndpoint(
    host=<affected_url_or_host>,
    port=<relevant_port>,
    protocol="ADVISORY",
    service_detail=<ADVISORY_CONSTANT>,
    severity="HIGH",
    scan_error_category="config",
    scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
)
```

### Rejection Row (invalid_input)

**Source:** `quirk/util/optional_extra.py` lines 222–230 (missing_extra advisory row shape)

**Apply to:** `source_scanner.py` (CR-02), `container_scanner.py` (CR-03), and optionally `saml_scanner.py` / `jwt_scanner.py` when input URL is syntactically invalid

```python
CryptoEndpoint(
    host=result.redacted_preview,   # 32-char sanitized preview, NOT raw input (D-08)
    port=0,
    protocol=<"SOURCE"|"CONTAINER"|"SAML"|"JWT">,
    scan_error=result.reason,       # reason code string e.g. "path_traversal"
    scan_error_category="invalid_input",
    scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
)
```

### Config Block Loading

**Source:** `quirk/config.py` `config_from_dict` function, lines 297–383

**Apply to:** `SecurityCfg` and `broker_credentials` loading in `config_from_dict`

Pattern: `raw.get("security") or {}` → construct dataclass with explicit field mapping (never `**kwargs` unpack from raw YAML — see how `ConnectorsCfg` uses `_KNOWN_CONNECTOR_KEYS` filter at line 340).

### CLI Flag Override Wiring

**Source:** `run_scan.py` lines 336–348 (broker namespace + targets-file override pattern)

**Apply to:** the three new `--allow-*` flags

Pattern: `if getattr(args, "<dest>", False): cfg.security.<field> = True` — all three are `store_true` flags that can only flip `False → True`, never `True → False`.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| (none) | — | — | All files have close analogs in the codebase |

---

## Metadata

**Analog search scope:** `quirk/util/`, `quirk/scanner/`, `quirk/config.py`, `quirk/config_template.yaml`, `quirk/models.py`, `run_scan.py`, `tests/`
**Files scanned:** 16 source files, 6 test files
**Pattern extraction date:** 2026-05-09
