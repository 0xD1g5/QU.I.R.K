# Phase 3: Scanner Coverage - Research

**Researched:** 2026-03-29
**Domain:** Multi-surface cryptographic scanner integration (JWT/API, Container/SBOM, Source code, AWS cloud, Azure cloud)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Add one nullable JSON blob column per new scanner surface, following the `tls_capabilities_json` / `ssh_audit_json` pattern from Phase 1. New columns: `jwt_scan_json TEXT`, `container_scan_json TEXT`, `source_scan_json TEXT`, `cloud_scan_json TEXT`. All additive — no breaking schema migrations.

**D-02:** Use the existing `protocol` field (`String(32)`) as the scanner-type discriminator for the CBOM builder. New protocol values: `"JWT"`, `"CONTAINER"`, `"SOURCE"`, `"AWS"`, `"AZURE"`. The CBOM builder already branches on `ep.protocol == "SSH"` — extend this branching to handle all five new types.

**D-03:** Each new scanner follows the established pattern: guarded block in `run_scan.py`, function returns `List[CryptoEndpoint]`, merged into `endpoints` before `evaluate_endpoints()` and `write_reports()`.

**D-04:** New scanner enable flags added to `ConnectorsCfg` (or a new `ScannersCfg` section): `enable_jwt`, `enable_container`, `enable_source`. Cloud connectors reuse the existing `enable_aws` / `enable_azure` booleans already in `quirk/config.py`.

**D-05:** JWT endpoints are configured explicitly in config (not discovered by CIDR sweep). Users specify a list of API base URLs. The scanner fetches `/.well-known/jwks.json` (and configurable JWKS path), parses each key entry (alg, kty, n/e for RSA key size), and optionally probes known JWT-issuing paths.

**D-06:** Python-native: `httpx` (or `requests`) for HTTP, `PyJWT` / `python-jose` for token parsing. No subprocess — these are pip-installable. Graceful degradation if no JWT targets configured.

**D-07:** Each JWKS key becomes one `CryptoEndpoint` row: `protocol="JWT"`, `host=<api_base_url>`, `port=443`, `cert_pubkey_alg=<alg>`, `cert_pubkey_size=<key_bits>`, `jwt_scan_json=<full key entry JSON>`.

**D-08:** Syft subprocess only (not Trivy). Command: `syft <image> -o json`, parse `artifacts` array, filter by crypto library name allowlist.

**D-09:** Each matching artifact becomes one `CryptoEndpoint` row: `protocol="CONTAINER"`, `host=<image_ref>`, `port=0`, `cipher_suite=<library_name>`, `tls_version=<library_version>`, `container_scan_json=<full artifact JSON>`.

**D-10:** Graceful degradation: if `syft` binary is not on PATH, log a warning and skip — do not hard-fail. Match the ssh-audit not-installed behavior.

**D-11:** Use `semgrep` with crypto-detection rules — NOT CBOMkit Hyperion. Run via subprocess. Semgrep is pip-installable and runs offline.

**D-12:** Run semgrep with `--config auto` (or a bundled ruleset): `semgrep --json --config p/cryptography <repo_path>`. Parse JSON output `results` array.

**D-13:** Each semgrep finding becomes one `CryptoEndpoint` row: `protocol="SOURCE"`, `host=<repo_path>`, `port=0`, `cipher_suite=<rule_id>`, `service_detail=<file:line>`, `source_scan_json=<full finding JSON>`.

**D-14:** Graceful degradation: if `semgrep` is not installed, log warning and skip.

**D-15:** AWS connector uses boto3 ambient credential resolution (env vars → `~/.aws/credentials` → instance profile). No credentials stored in `config.yaml`. Add `aws_region` (required when `enable_aws: true`) and optional `aws_profile` to `ConnectorsCfg`.

**D-16:** Azure connector uses `DefaultAzureCredential` from `azure-identity`. No credentials stored in config. Add `azure_subscription_id` (required when `enable_azure: true`) to `ConnectorsCfg`.

**D-17:** AWS surfaces: ACM certificates (`acm.list_certificates`), KMS key specs (`kms.list_keys` + `describe_key`), CloudFront TLS policies (`cloudfront.list_distributions`), ELB/ALB listeners (`elbv2.describe_listeners`). Each resource: `protocol="AWS"`, `host=<resource_arn>`, `cloud_scan_json=<resource metadata JSON>`.

**D-18:** Azure surfaces: Key Vault certificates + keys (`azure-keyvault-certificates`, `azure-keyvault-keys`), App Gateway TLS policies (`azure-mgmt-network`). Each resource: `protocol="AZURE"`, `host=<resource_id>`, `cloud_scan_json=<resource metadata JSON>`.

**D-19:** Extend `quirk/cbom/builder.py` to handle the new protocol values. JWT → `AlgorithmProperties` component. Container → `CryptographicLibrary` component. Source → `AlgorithmProperties` component. Cloud → `CryptographicLibrary` or `AlgorithmProperties` depending on resource type.

### Claude's Discretion

- Exact semgrep ruleset selection (`p/cryptography` vs bundled custom rules)
- Crypto library allowlist for container scanner (exact package names)
- JWT path probing beyond `/.well-known/jwks.json` (e.g., `/oauth/jwks`, `/auth/keys`)
- boto3 pagination handling strategy for large AWS accounts
- Whether to add `aws_region` as a list (multi-region scan) or single string

### Deferred Ideas (OUT OF SCOPE)

- Trivy vulnerability scanning on containers
- Multi-region AWS scanning (single region in Phase 3)
- Azure Front Door / CDN TLS scanning
- SonarQube / CBOMkit Hyperion integration
- Email / S/MIME scanning
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCAN-03 | API/JWT scanner — REST endpoint discovery, JWKS fetch, JWT algorithm and key-size classification | httpx + PyJWT pattern; JWKS JSON structure documented; classifier needs RS256/HS256/ES256 entries |
| SCAN-04 | Container/binary crypto scanner — Syft subprocess wrapper for crypto library inventory | syft 1.42.3 (homebrew); JSON output format verified; `artifacts` array structure documented |
| SCAN-05 | Source code scanner — semgrep with p/cryptography ruleset for code-level crypto detection | semgrep 1.136.0 available via pip; `--json` output format documented; graceful degradation pattern |
| SCAN-06 | AWS cloud connector — ACM, KMS, CloudFront, ELB/ALB via boto3 | boto3 1.42.x; ambient credential pattern; paginator API for large accounts |
| SCAN-07 | Azure cloud connector — Key Vault, App Gateway via azure-sdk-for-python | azure-identity 1.25.3; azure-keyvault-* 4.x; azure-mgmt-network 30.x |
</phase_requirements>

---

## Summary

Phase 3 extends QU.I.R.K. from two scan surfaces (TLS, SSH) to seven by adding JWT/API, Container/SBOM, Source code, AWS cloud, and Azure cloud scanners. All five new scanners follow an identical integration pattern already proven in Phase 1: a scanner module returns `List[CryptoEndpoint]`, a guarded phase block in `run_scan.py` appends to the shared `endpoints` list, and the CBOM builder branches on `ep.protocol` to generate the correct CycloneDX component type.

The implementation divides into four technical layers: (1) new SQLAlchemy columns on `CryptoEndpoint`, (2) new scanner modules under `quirk/scanner/`, (3) config dataclass extensions in `quirk/config.py`, and (4) CBOM builder extensions in `quirk/cbom/builder.py` and `quirk/cbom/classifier.py`. All external tools (syft, semgrep) degrade gracefully to a log-and-skip if absent, matching the established `ssh-audit` pattern. All cloud credentials use ambient resolution — nothing is stored in config files.

The `pyproject.toml` currently declares only `cyclonedx-python-lib` as a dependency. All Phase 3 library dependencies (`httpx`, `PyJWT`, `python-jose`, `boto3`, `azure-identity`, `azure-keyvault-certificates`, `azure-keyvault-keys`, `azure-mgmt-network`) must be added as optional extras or unconditional dependencies. Syft and semgrep are external binaries installed separately (not via pip), so they are not added to `pyproject.toml`.

**Primary recommendation:** Implement all five scanners as thin wrappers that follow the ssh_scanner.py template exactly — each in its own module file, each returning `List[CryptoEndpoint]`, with `shutil.which()` guards for subprocess-based scanners.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 | HTTP client for JWKS fetching | Async-capable, modern replacement for requests; sync API works for scanner context |
| PyJWT | 2.12.1 | JWT decode / algorithm extraction | Official PyJWT library; parses header alg field without signature verification |
| python-jose | 3.5.0 | RSA key size extraction from JWKS n/e parameters | Handles JWK-to-key conversion; compute RSA modulus bit-length from `n` |
| boto3 | 1.42.78 | AWS API (ACM, KMS, CloudFront, ELBv2) | Official AWS SDK; ambient credential chain built-in |
| azure-identity | 1.25.3 | DefaultAzureCredential for Azure auth | Official Azure SDK; supports env vars, managed identity, CLI credentials |
| azure-keyvault-certificates | 4.10.0 | Key Vault certificate listing | Official Azure SDK component |
| azure-keyvault-keys | 4.11.0 | Key Vault key type listing | Official Azure SDK component |
| azure-mgmt-network | 30.2.0 | App Gateway TLS policy enumeration | Official Azure management SDK |

### Supporting (External Binaries — NOT pip)
| Tool | Version | Purpose | Install |
|------|---------|---------|---------|
| syft | 1.42.3 | Container SBOM generation (`artifacts` JSON) | `brew install syft` or GitHub releases |
| semgrep | 1.136.0 | Source code crypto detection (`p/cryptography` ruleset) | `pip install semgrep` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | requests | requests is already installed; httpx preferred for future async path; decision already locked to httpx or requests (D-06) |
| PyJWT | python-jose only | python-jose handles both JWT decode and JWK conversion; PyJWT is lighter for header-only inspection |
| syft | Trivy | Trivy adds vuln scanning outside scope; syft is SBOM-focused (locked D-08) |
| semgrep `p/cryptography` | Custom regex | Custom regex has insufficient coverage; semgrep rules are community-maintained and updated (locked D-11) |

**Installation (pyproject.toml additions):**
```toml
dependencies = [
    "cyclonedx-python-lib>=11.7.0,<12",
    "httpx>=0.28.0",
    "PyJWT>=2.12.0",
    "python-jose>=3.5.0",
    "boto3>=1.42.0",
    "azure-identity>=1.25.0",
    "azure-keyvault-certificates>=4.10.0",
    "azure-keyvault-keys>=4.11.0",
    "azure-mgmt-network>=30.2.0",
]
```

---

## Architecture Patterns

### Recommended Project Structure
```
quirk/
├── scanner/
│   ├── tls_scanner.py        # existing
│   ├── ssh_scanner.py        # existing
│   ├── jwt_scanner.py        # Phase 3 NEW
│   ├── container_scanner.py  # Phase 3 NEW
│   ├── source_scanner.py     # Phase 3 NEW
│   ├── aws_connector.py      # Phase 3 NEW
│   └── azure_connector.py    # Phase 3 NEW
├── cbom/
│   ├── builder.py            # extend protocol branching
│   └── classifier.py         # add JWT alg entries
├── models.py                 # add 4 new nullable TEXT columns
└── config.py                 # extend ConnectorsCfg
```

### Pattern 1: Scanner Module Template (clone from ssh_scanner.py)

**What:** Each scanner module exposes a single public function `scan_<surface>_targets(cfg, targets, logger) -> List[CryptoEndpoint]`. Subprocess scanners use `shutil.which()` guard before running. Pure-Python scanners use `try/except ImportError` guard.

**When to use:** All five new scanners follow this exact template.

**Example (subprocess variant — syft):**
```python
# Source: ssh_scanner.py pattern (established Phase 1)
import shutil, subprocess, json
from quirk.models import CryptoEndpoint

def _run_syft(image_ref: str, timeout: int) -> list | None:
    exe = shutil.which("syft")
    if not exe:
        return None
    try:
        proc = subprocess.run(
            [exe, image_ref, "-o", "json"],
            capture_output=True, text=True, timeout=timeout
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout).get("artifacts", [])
        return None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None
```

**Example (Python-native variant — JWT):**
```python
# Source: tls_scanner.py SSLYZE_AVAILABLE pattern
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

def scan_jwt_one(base_url: str, ...) -> List[CryptoEndpoint]:
    if not HTTPX_AVAILABLE:
        logger.v("httpx not installed — JWT scanning unavailable")
        return []
    ...
```

### Pattern 2: Guarded Phase Block in run_scan.py

**What:** Each new scanner gets a `with _phase_timer(run_stats, "<scanner>_scanning"):` block guarded by the enable flag from config. Results are appended to the shared `endpoints` list at line 356.

**Example:**
```python
# After the existing ssh phase block (run_scan.py ~line 356)
jwt_endpoints = []
with _phase_timer(run_stats, "jwt_scanning"):
    if cfg.connectors.enable_jwt and jwt_targets:
        jwt_endpoints = scan_jwt_targets(cfg, jwt_targets, logger=logger)

container_endpoints = []
with _phase_timer(run_stats, "container_scanning"):
    if cfg.connectors.enable_container and container_targets:
        container_endpoints = scan_container_targets(cfg, container_targets, logger=logger)

# ...same for source, aws, azure

endpoints = (inventory_endpoints + tls_endpoints + ssh_endpoints
             + jwt_endpoints + container_endpoints + source_endpoints
             + aws_endpoints + azure_endpoints)
```

### Pattern 3: CBOM Builder Protocol Branching Extension

**What:** The existing builder.py uses `is_ssh = ep.protocol == "SSH"` and `if is_ssh / else` (TLS). Extend Pass 1 and Pass 3 with explicit protocol guards for each new surface type.

**Example (Pass 1 extension):**
```python
# Source: builder.py Pass 1, extend after is_ssh block
elif ep.protocol == "JWT":
    # cert_pubkey_alg holds the JWT algorithm (RS256, HS256, etc.)
    if ep.cert_pubkey_alg:
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)

elif ep.protocol == "CONTAINER":
    # cipher_suite holds library name, tls_version holds version
    # Register as a LIBRARY component — handled in Pass 2 extension

elif ep.protocol == "SOURCE":
    # cipher_suite holds semgrep rule_id (e.g. python.cryptography.insecure-hash-md5)
    # Extract algorithm name from rule_id for registry
    algo_hint = _extract_algo_from_rule_id(ep.cipher_suite)
    if algo_hint:
        _register_algorithm(algo_hint, algo_registry)

elif ep.protocol in ("AWS", "AZURE"):
    # Parse cloud_scan_json for algorithm/key spec fields
    cloud_data = json.loads(ep.cloud_scan_json or "{}")
    # KMS: KeySpec field (RSA_2048, ECC_NIST_P256, SYMMETRIC_DEFAULT)
    # ACM: KeyAlgorithm field (RSA_2048, EC_prime256v1)
    key_spec = cloud_data.get("KeySpec") or cloud_data.get("KeyAlgorithm")
    if key_spec:
        _register_algorithm(_normalize_cloud_key_spec(key_spec), algo_registry)
```

### Pattern 4: Classifier Extension for JWT Algorithms

**What:** Add JWT standard algorithm identifiers to `_ALGORITHM_TABLE` in `classifier.py`. These are RFC 7518 algorithm names returned by JWKS `alg` fields.

**JWT algorithms to add:**
```python
# Source: RFC 7518 / JOSE standard
"rs256": (CryptoPrimitive.SIGNATURE, 0, 112),   # RSA + SHA-256 — quantum-vulnerable
"rs384": (CryptoPrimitive.SIGNATURE, 0, 112),   # RSA + SHA-384
"rs512": (CryptoPrimitive.SIGNATURE, 0, 112),   # RSA + SHA-512
"es256": (CryptoPrimitive.SIGNATURE, 0, 128),   # ECDSA P-256 — quantum-vulnerable
"es384": (CryptoPrimitive.SIGNATURE, 0, 192),   # ECDSA P-384
"es512": (CryptoPrimitive.SIGNATURE, 0, 256),   # ECDSA P-521
"hs256": (CryptoPrimitive.MAC, 0, 128),         # HMAC-SHA256 — symmetric
"hs384": (CryptoPrimitive.MAC, 0, 192),
"hs512": (CryptoPrimitive.MAC, 0, 256),
"ps256": (CryptoPrimitive.SIGNATURE, 0, 112),   # RSA-PSS
"ps384": (CryptoPrimitive.SIGNATURE, 0, 112),
"ps512": (CryptoPrimitive.SIGNATURE, 0, 112),
"none":  (CryptoPrimitive.UNKNOWN, 0, 0),       # alg:none — critical vulnerability
```

### Anti-Patterns to Avoid

- **Storing cloud credentials in config.yaml:** boto3 and azure-identity both use ambient credential chains. Never add credential fields to the config dataclass — this is an explicit locked decision (D-15, D-16).
- **Hard-failing when syft/semgrep is absent:** The tool should be usable without these optional external binaries. Log and skip, matching the ssh-audit pattern.
- **Scanning CIDR ranges for JWT targets:** JWT scanner is config-driven (explicit URL list), not network-sweep-driven (D-05).
- **Treating all CBOM builder protocol branches as TLS:** The existing `else:` clause in builder.py handles TLS. New protocols need explicit guards before hitting that clause to prevent misclassification.
- **Not paginating AWS API calls:** ACM, KMS, CloudFront, and ELBv2 all return paginated results. Fetching only the first page silently misses resources.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RSA key size from JWKS `n` parameter | Custom base64url decode + bit count | `python-jose` JWK-to-key conversion or `cryptography.hazmat.primitives` | Off-by-one on padding bits, base64url vs base64 confusion |
| JWT header inspection | Custom base64 decode + JSON parse | `PyJWT.decode(..., options={"verify_signature": False})` | Handles compact vs JSON serialization edge cases |
| Container SBOM parsing | Custom Docker image layer inspection | `syft` subprocess output | syft handles distroless, Windows images, OCI artifacts, multi-arch; custom layer inspection misses package managers |
| Semgrep rule authoring | Custom AST/regex crypto detection | `semgrep --config p/cryptography` | p/cryptography rules cover 20+ languages with pattern-based algo detection; regex misses aliased imports |
| AWS API pagination | Manual NextToken loop | `boto3` paginator: `client.get_paginator("list_certificates")` | Boto3 paginators handle all pagination protocols; manual loops break on empty NextToken edge cases |
| Azure resource enumeration | Custom REST calls to ARM API | `azure-mgmt-network` SDK | SDK handles auth token refresh, retries, ARM API versioning |

**Key insight:** The value in this phase is breadth of surface coverage. Every hour spent on custom protocol parsing is an hour not spent adding the next scanner surface.

---

## JWKS Key Size Extraction

The RSA key size is not returned directly by JWKS endpoints — it must be computed from the modulus `n` parameter:

```python
# Source: RFC 7517 / python-jose pattern
import base64

def _rsa_key_bits_from_n(n_b64url: str) -> int | None:
    """Compute RSA key size in bits from JWKS 'n' (base64url modulus)."""
    try:
        # base64url: replace - with +, _ with /, add padding
        padded = n_b64url.replace("-", "+").replace("_", "/")
        padded += "=" * (4 - len(padded) % 4)
        modulus_bytes = base64.b64decode(padded)
        return len(modulus_bytes) * 8
    except Exception:
        return None
```

For EC keys, key size is derived from the `crv` parameter: `P-256` → 256, `P-384` → 384, `P-521` → 521.

---

## Syft Output Format

Syft 1.42.3 `syft <image> -o json` returns:

```json
{
  "artifacts": [
    {
      "id": "abc123",
      "name": "openssl",
      "version": "3.0.2-0ubuntu1.12",
      "type": "deb",
      "foundBy": "dpkg-db-cataloger",
      "locations": [{"path": "/var/lib/dpkg/info/openssl.list"}],
      "language": "",
      "cpes": ["cpe:2.3:a:openssl:openssl:3.0.2:..."],
      "purl": "pkg:deb/ubuntu/openssl@3.0.2-0ubuntu1.12"
    }
  ],
  "source": {"type": "image", "target": {"userInput": "ubuntu:22.04"}},
  "schema": {"version": "16.0.12"}
}
```

**Crypto library allowlist (recommended):**
```python
CRYPTO_LIB_ALLOWLIST = {
    "openssl", "libssl", "libssl3", "libssl1.1", "libssl1.0.2",
    "libcrypto", "libcrypto3",
    "botan", "botan2", "libbotan",
    "libgcrypt", "libgcrypt20",
    "nss", "libnss3", "libnss",
    "mbedtls", "libmbedtls",
    "wolfssl", "libwolfssl",
    "gnutls", "libgnutls",
    "python-cryptography", "cryptography",   # PyPI name
    "pyopenssl", "pyOpenSSL",
    "pycryptodome", "pycryptodomex",
    "bcrypt",
    "nacl", "pynacl",
}
```

Match by lowercased `artifact["name"]` membership in this set.

---

## Semgrep Output Format

`semgrep --json --config p/cryptography <repo_path>` returns:

```json
{
  "results": [
    {
      "check_id": "python.cryptography.security.insecure-hash-algorithms.insecure-hash-algorithms-md5",
      "path": "app/auth.py",
      "start": {"line": 42, "col": 4},
      "end": {"line": 42, "col": 30},
      "extra": {
        "message": "Use of weak MD5 hash algorithm",
        "severity": "WARNING",
        "metadata": {"confidence": "HIGH"}
      }
    }
  ],
  "errors": [],
  "stats": {"total_time": 1.23, "files_skipped": 0}
}
```

Map `service_detail` as `f"{result['path']}:{result['start']['line']}"`.

**Note on `--config p/cryptography`:** This ruleset requires a network connection to download on first run. For offline use, pre-download with `semgrep --config p/cryptography --dry-run` or bundle rules locally. The CONTEXT.md notes Claude's discretion on ruleset selection — recommend starting with `p/cryptography` (online) and document the offline caveat.

---

## Cloud Connector Data Shapes

### AWS ACM Certificate
```python
# boto3 acm.describe_certificate()["Certificate"]
{
    "CertificateArn": "arn:aws:acm:us-east-1:123:certificate/abc",
    "DomainName": "example.com",
    "KeyAlgorithm": "RSA_2048",        # <- map to cert_pubkey_alg
    "SignatureAlgorithm": "SHA256WITHRSA",
    "NotBefore": datetime(...),
    "NotAfter": datetime(...),
    "Status": "ISSUED",
}
```

### AWS KMS Key
```python
# boto3 kms.describe_key()["KeyMetadata"]
{
    "KeyId": "1234abcd-...",
    "Arn": "arn:aws:kms:us-east-1:123:key/1234abcd",
    "KeySpec": "RSA_2048",             # <- map to key spec
    "KeyUsage": "SIGN_VERIFY",
    "KeyState": "Enabled",
    "CustomerMasterKeySpec": "RSA_2048",
}
```

**KMS KeySpec → algorithm mapping:**
```python
KMS_KEY_SPEC_MAP = {
    "RSA_2048": ("RSA", 2048),
    "RSA_3072": ("RSA", 3072),
    "RSA_4096": ("RSA", 4096),
    "ECC_NIST_P256": ("ECDSA", 256),
    "ECC_NIST_P384": ("ECDSA", 384),
    "ECC_NIST_P521": ("ECDSA", 521),
    "ECC_SECG_P256K1": ("ECDSA", 256),
    "SYMMETRIC_DEFAULT": ("AES", 256),   # AES-256-GCM
    "HMAC_224": ("HMAC", 224),
    "HMAC_256": ("HMAC", 256),
    "HMAC_384": ("HMAC", 384),
    "HMAC_512": ("HMAC", 512),
    "SM2": ("SM2", 256),                 # China region only
}
```

### AWS CloudFront Distribution
```python
# boto3 cloudfront.list_distributions()["DistributionList"]["Items"][n]
{
    "Id": "EDFDVBD6EXAMPLE",
    "ARN": "arn:aws:cloudfront::123:distribution/EDFD...",
    "ViewerCertificate": {
        "MinimumProtocolVersion": "TLSv1.2_2021",
        "SSLSupportMethod": "sni-only",
    }
}
```

### AWS ELBv2 Listener
```python
# boto3 elbv2.describe_listeners()["Listeners"][n]
{
    "ListenerArn": "arn:aws:elasticloadbalancing:...",
    "LoadBalancerArn": "arn:aws:elasticloadbalancing:...",
    "Port": 443,
    "Protocol": "HTTPS",
    "SslPolicy": "ELBSecurityPolicy-TLS13-1-2-2021-06",
}
```

### Azure Key Vault Key
```python
# azure-keyvault-keys: client.list_properties_of_keys()
KeyProperties(
    name="my-rsa-key",
    vault_url="https://myvault.vault.azure.net",
    key_type=KeyType.rsa,   # rsa, ec, oct (AES), rsa-hsm, ec-hsm
    key_size=2048,
)
```

### Azure App Gateway TLS Policy
```python
# azure-mgmt-network: client.application_gateways.get(rg, name)
ApplicationGateway(
    ssl_policy=ApplicationGatewaySslPolicy(
        policy_type="Predefined",
        policy_name="AppGwSslPolicy20220101",   # or "Custom"
        min_protocol_version="TLSv1_2",
        cipher_suites=["TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384", ...]
    )
)
```

---

## Common Pitfalls

### Pitfall 1: JWKS Endpoint Returns Multiple Keys
**What goes wrong:** A JWKS endpoint may return 2-5 keys (current + previous rotation keys). If the scanner only creates one CryptoEndpoint per URL instead of one per key, key IDs and rotation state are lost.
**Why it happens:** Treating the JWKS response as a single credential rather than a key set.
**How to avoid:** Iterate `jwks["keys"]` and create one CryptoEndpoint per key entry (D-07 is explicit on this).
**Warning signs:** Single endpoint returning `kid` field in JWT header but only one DB row per API URL.

### Pitfall 2: Semgrep `p/cryptography` Requires Internet on First Run
**What goes wrong:** In an air-gapped or offline consultant environment, `semgrep --config p/cryptography` fails with a network error downloading the ruleset.
**Why it happens:** Semgrep downloads rulesets from `semgrep.dev` on demand.
**How to avoid:** Either (a) pre-cache the ruleset before air-gapped use, or (b) bundle a local copy of the rules in the project. Document this in the connector setup guide (DOC-04 scope). For Phase 3 implementation, log a clear error if the semgrep run fails and treat it as graceful degradation.
**Warning signs:** `semgrep` exits with error code 7 ("Could not connect to Semgrep registry").

### Pitfall 3: boto3 Pagination Silently Truncates Large Accounts
**What goes wrong:** AWS list APIs return max 100 items per page. An account with 200 ACM certificates silently returns only the first 100 without pagination.
**Why it happens:** Calling `list_certificates()` directly without using `get_paginator("list_certificates")`.
**How to avoid:** Always use `boto3.client.get_paginator()` for all AWS list operations. The paginator protocol differs per service (NextToken, Marker, NextPage) — the paginator abstraction handles all variants.
**Warning signs:** Scan results capped at exactly 100 resources for any AWS surface.

### Pitfall 4: Azure Key Vault Requires List + Get Permissions
**What goes wrong:** `list_properties_of_keys()` succeeds but returns minimal metadata. Getting the full key type requires an additional `get_key()` call, which requires the `keys/get` permission (not just `keys/list`).
**Why it happens:** List and Get are separate RBAC permissions in Key Vault access policies.
**How to avoid:** Document minimum required permissions in DOC-04. In code, catch `ResourceNotFoundError` / `HttpResponseError` on `get_key()` and fall back to properties-only data.
**Warning signs:** `key_type=None` in properties despite successful listing.

### Pitfall 5: syft Produces Different Artifact IDs Across Runs
**What goes wrong:** Re-scanning the same image produces different `id` fields on artifacts, breaking any deduplication logic that relies on syft's internal IDs.
**Why it happens:** syft generates artifact IDs from location hashes that can vary across schema versions.
**How to avoid:** Use `(name, version, type)` tuple as the deduplication key for container findings, not syft's `id` field. The `purl` field is stable and suitable for deduplication.
**Warning signs:** Duplicate CONTAINER rows in the DB after re-scanning the same image.

### Pitfall 6: CBOM Builder `else:` Clause Handles TLS by Default
**What goes wrong:** A new protocol value (e.g., "CONTAINER") falls through to the existing `else:` clause in builder.py, which treats it as a TLS endpoint and attempts cipher suite decomposition on a library name string like `"openssl"`.
**Why it happens:** The current builder has binary `is_ssh / else (TLS)` branching.
**How to avoid:** Add explicit `elif ep.protocol == "CONTAINER":` etc. guards before any fallback. Add a final `else: logger.warning(f"Unknown protocol: {ep.protocol}")` to surface unhandled types.
**Warning signs:** CBOM components with garbled algorithm names derived from library names.

---

## Code Examples

### JWT Scanner — JWKS Fetch and Key Extraction
```python
# Source: RFC 7517 JWKS format + httpx pattern
import httpx, json, base64
from quirk.models import CryptoEndpoint
from datetime import datetime, timezone

JWKS_PATHS = [
    "/.well-known/jwks.json",
    "/oauth/jwks",
    "/.well-known/openid-configuration",  # discover jwks_uri from OIDC metadata
]

def _rsa_key_bits_from_n(n_b64url: str) -> int | None:
    try:
        padded = n_b64url.replace("-", "+").replace("_", "/")
        padded += "=" * (4 - len(padded) % 4)
        return len(base64.b64decode(padded)) * 8
    except Exception:
        return None

def _ec_key_bits_from_crv(crv: str) -> int | None:
    return {"P-256": 256, "P-384": 384, "P-521": 521, "secp256k1": 256}.get(crv)

def scan_jwks_url(base_url: str, jwks_path: str, timeout: int) -> list[dict]:
    """Fetch JWKS and return list of key entries, or empty list on failure."""
    url = base_url.rstrip("/") + jwks_path
    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True,
                         verify=False)  # consultant tool — may scan self-signed
        if resp.status_code == 200:
            data = resp.json()
            return data.get("keys", [])
    except Exception:
        pass
    return []

def scan_jwt_endpoint(base_url: str, cfg, logger=None) -> list[CryptoEndpoint]:
    results = []
    for path in JWKS_PATHS:
        keys = scan_jwks_url(base_url, path, cfg.scan.timeout_seconds)
        if keys:
            for key_entry in keys:
                kty = key_entry.get("kty", "")
                alg = key_entry.get("alg", kty)   # fall back to kty if no alg
                key_bits = None
                if kty == "RSA":
                    key_bits = _rsa_key_bits_from_n(key_entry.get("n", ""))
                elif kty == "EC":
                    key_bits = _ec_key_bits_from_crv(key_entry.get("crv", ""))
                ep = CryptoEndpoint(
                    host=base_url,
                    port=443,
                    protocol="JWT",
                    scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    cert_pubkey_alg=alg,
                    cert_pubkey_size=key_bits,
                    jwt_scan_json=json.dumps(key_entry),
                    service_detail=path,
                )
                results.append(ep)
            break   # found JWKS — stop probing other paths
    return results
```

### Container Scanner — Syft Subprocess + Allowlist Filter
```python
# Source: ssh_scanner._run_ssh_audit pattern + syft JSON schema
import shutil, subprocess, json
from quirk.models import CryptoEndpoint
from datetime import datetime, timezone

CRYPTO_LIB_ALLOWLIST = frozenset({
    "openssl", "libssl", "libssl3", "libssl1.1", "libcrypto", "libcrypto3",
    "botan", "libgcrypt", "libgcrypt20", "nss", "libnss3",
    "mbedtls", "libmbedtls", "wolfssl", "gnutls", "libgnutls",
    "cryptography", "pyopenssl", "pycryptodome", "pycryptodomex",
    "bcrypt", "nacl", "pynacl",
})

def scan_container_image(image_ref: str, timeout: int, logger=None) -> list[CryptoEndpoint]:
    exe = shutil.which("syft")
    if not exe:
        if logger:
            logger.v("syft not found — install with: brew install syft. Container scanning skipped.")
        return []
    try:
        proc = subprocess.run(
            [exe, image_ref, "-o", "json"],
            capture_output=True, text=True, timeout=timeout
        )
        data = json.loads(proc.stdout)
    except Exception as e:
        if logger:
            logger.v(f"syft failed for {image_ref}: {e}")
        return []

    results = []
    for artifact in data.get("artifacts", []):
        name = artifact.get("name", "").lower()
        if name not in CRYPTO_LIB_ALLOWLIST:
            continue
        version = artifact.get("version", "")
        ep = CryptoEndpoint(
            host=image_ref,
            port=0,
            protocol="CONTAINER",
            scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
            cipher_suite=artifact.get("name"),
            tls_version=version,
            container_scan_json=json.dumps(artifact),
        )
        results.append(ep)
    return results
```

### AWS Connector — ACM with Paginator
```python
# Source: boto3 paginator pattern
import boto3, json
from quirk.models import CryptoEndpoint
from datetime import datetime, timezone

def scan_acm_certificates(region: str, profile: str | None, logger=None) -> list[CryptoEndpoint]:
    session = boto3.Session(region_name=region, profile_name=profile)
    client = session.client("acm")
    results = []
    try:
        paginator = client.get_paginator("list_certificates")
        for page in paginator.paginate():
            for summary in page["CertificateSummaryList"]:
                arn = summary["CertificateArn"]
                try:
                    detail = client.describe_certificate(CertificateArn=arn)["Certificate"]
                except Exception:
                    detail = summary
                ep = CryptoEndpoint(
                    host=arn,
                    port=0,
                    protocol="AWS",
                    scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    cert_pubkey_alg=detail.get("KeyAlgorithm"),
                    cloud_scan_json=json.dumps(detail, default=str),
                    service_detail="ACM",
                )
                results.append(ep)
    except Exception as e:
        if logger:
            logger.v(f"ACM scan failed: {e}")
    return results
```

### Config Extension
```python
# Source: quirk/config.py ConnectorsCfg pattern
@dataclass
class ConnectorsCfg:
    enable_aws: bool
    enable_azure: bool
    enable_windows_adcs: bool
    # Phase 3 additions
    enable_jwt: bool = False
    enable_container: bool = False
    enable_source: bool = False
    aws_region: str = "us-east-1"
    aws_profile: Optional[str] = None
    azure_subscription_id: Optional[str] = None
    jwt_targets: list = field(default_factory=list)       # list of API base URLs
    container_targets: list = field(default_factory=list)  # list of image refs
    source_targets: list = field(default_factory=list)     # list of repo paths
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CBOMkit Hyperion (Java SonarQube plugin) for code scanning | semgrep `p/cryptography` | 2023+ | Works offline, pip-installable, no SonarQube server dependency |
| Trivy for container crypto inventory | syft SBOM output | Phase 3 decision (D-08) | SBOM-focused, no vuln scanner overhead |
| KMS `CustomerMasterKeySpec` (deprecated) | KMS `KeySpec` | AWS deprecated CMK in 2023 | Code should read `KeySpec`; fall back to `CustomerMasterKeySpec` for old key metadata |
| azure-keyvault 1.x | azure-keyvault-certificates 4.x + azure-keyvault-keys 4.x | 2021 SDK split | Separate packages per service; unified authentication via azure-identity |

**Deprecated/outdated:**
- `CustomerMasterKeySpec` on KMS DescribeKey response: AWS deprecated this field; use `KeySpec`. Both fields exist in API response — read `KeySpec` first with `CustomerMasterKeySpec` as fallback for old key metadata.
- `azure-keyvault` (monolithic): Replaced by `azure-keyvault-certificates`, `azure-keyvault-keys`, `azure-keyvault-secrets` in separate packages.

---

## Open Questions

1. **Semgrep `p/cryptography` offline availability**
   - What we know: semgrep downloads ruleset from `semgrep.dev` on first use; subsequent runs use cache
   - What's unclear: Is the cache persistent enough for typical consultant field use (days/weeks)?
   - Recommendation: Document the caveat in DOC-04; implement graceful degradation treating download failure the same as `semgrep` not installed

2. **aws_region as string vs list**
   - What we know: D-15 specifies single region in Phase 3; multi-region is deferred backlog
   - What's unclear: Whether the config field name should anticipate future list expansion
   - Recommendation: Use `aws_region: str` (single string) for Phase 3. A future migration to `aws_regions: List[str]` is a minor config breaking change, acceptable when the backlog item is picked up.

3. **Azure subscription vs Key Vault URL configuration**
   - What we know: `azure_subscription_id` is required (D-16); Key Vault URLs are needed to instantiate `CertificateClient` / `KeyClient`
   - What's unclear: How does the scanner enumerate Key Vault URLs given only a subscription ID? Requires `azure-mgmt-keyvault` to list vaults in the subscription.
   - Recommendation: Add `azure_keyvault_urls: List[str]` as an explicit config field (user provides vault URLs directly) for Phase 3 simplicity. Full subscription-level enumeration via `azure-mgmt-keyvault` can be added in a later iteration.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All scanners | Assumed (project requirement) | — | — |
| httpx | SCAN-03 JWT scanner | Not installed | — | requests (already installed 2.32.5) |
| PyJWT | SCAN-03 JWT scanner | Not installed | — | Parse JWT header manually (base64url decode) |
| python-jose | SCAN-03 key size extraction | Not installed | — | Manual base64url modulus decode (documented above) |
| boto3 | SCAN-06 AWS connector | Not installed | — | AWS scanning blocked without it |
| azure-identity | SCAN-07 Azure connector | Not installed | — | Azure scanning blocked without it |
| azure-keyvault-certificates | SCAN-07 | Not installed | — | Azure KV cert scan blocked |
| azure-keyvault-keys | SCAN-07 | Not installed | — | Azure KV key scan blocked |
| azure-mgmt-network | SCAN-07 App Gateway | Not installed | — | App Gateway TLS policy scan blocked |
| syft (binary) | SCAN-04 container scanner | Available (homebrew) | 1.42.3 | Graceful skip (log warning) |
| semgrep (binary) | SCAN-05 source scanner | Not installed | — | Graceful skip (log warning) |
| Docker daemon | SCAN-04 (for image pull) | Not checked | — | syft can scan local tarballs too |

**Missing dependencies with no fallback (block their surface):**
- `boto3` — SCAN-06 AWS connector non-functional without it
- `azure-identity`, `azure-keyvault-*`, `azure-mgmt-network` — SCAN-07 Azure connector non-functional without them
- All must be added to `pyproject.toml` dependencies

**Missing dependencies with fallback:**
- `httpx` — can use `requests` (already installed) for JWKS fetches; flag this as implementation choice for Claude's discretion
- `semgrep` — graceful skip with install instructions; log `pip install semgrep`
- `syft` — graceful skip with install instructions; log `brew install syft`

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | none — see Wave 0 (no pytest.ini exists) |
| Quick run command | `pytest tests/test_jwt_scanner.py tests/test_container_scanner.py tests/test_source_scanner.py tests/test_cloud_connectors.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCAN-03 | JWKS fetch returns key entries; RSA key size computed from modulus | unit | `pytest tests/test_jwt_scanner.py -x` | Wave 0 |
| SCAN-03 | JWT CryptoEndpoint has protocol="JWT", cert_pubkey_alg set, jwt_scan_json set | unit | `pytest tests/test_jwt_scanner.py -x` | Wave 0 |
| SCAN-03 | JWKS endpoint with 3 keys produces 3 CryptoEndpoint rows | unit | `pytest tests/test_jwt_scanner.py::test_multi_key_jwks -x` | Wave 0 |
| SCAN-04 | syft absent → empty list returned, no exception | unit | `pytest tests/test_container_scanner.py::test_syft_not_found -x` | Wave 0 |
| SCAN-04 | syft JSON parsed; crypto libs filtered by allowlist | unit | `pytest tests/test_container_scanner.py::test_allowlist_filter -x` | Wave 0 |
| SCAN-04 | Container CryptoEndpoint has protocol="CONTAINER", cipher_suite=lib_name | unit | `pytest tests/test_container_scanner.py -x` | Wave 0 |
| SCAN-05 | semgrep absent → empty list returned, no exception | unit | `pytest tests/test_source_scanner.py::test_semgrep_not_found -x` | Wave 0 |
| SCAN-05 | semgrep JSON parsed; each finding → CryptoEndpoint with service_detail="file:line" | unit | `pytest tests/test_source_scanner.py -x` | Wave 0 |
| SCAN-06 | AWS connector uses paginator (not direct list_certificates) | unit (mock boto3) | `pytest tests/test_cloud_connectors.py::test_aws_acm_pagination -x` | Wave 0 |
| SCAN-06 | KMS KeySpec → cert_pubkey_alg mapped correctly | unit | `pytest tests/test_cloud_connectors.py::test_kms_key_spec_mapping -x` | Wave 0 |
| SCAN-07 | Azure Key Vault key type → CryptoEndpoint with protocol="AZURE" | unit (mock azure SDK) | `pytest tests/test_cloud_connectors.py::test_azure_keyvault -x` | Wave 0 |
| ALL | New protocol values branch correctly in CBOM builder (no TLS fallthrough) | unit | `pytest tests/test_cbom_builder.py -x -k "jwt or container or source or aws or azure"` | Wave 0 (extend existing) |
| ALL | New algorithms (RS256, ES256, HS256) present in classifier table | unit | `pytest tests/test_cbom_classifier.py -x -k "jwt"` | Wave 0 (extend existing) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_jwt_scanner.py tests/test_container_scanner.py tests/test_source_scanner.py tests/test_cloud_connectors.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_jwt_scanner.py` — covers SCAN-03 with mocked httpx responses
- [ ] `tests/test_container_scanner.py` — covers SCAN-04 with mocked syft subprocess output
- [ ] `tests/test_source_scanner.py` — covers SCAN-05 with mocked semgrep subprocess output
- [ ] `tests/test_cloud_connectors.py` — covers SCAN-06/07 with mocked boto3/azure SDK calls
- [ ] Framework install: `pip install pytest` — not currently installed

---

## Sources

### Primary (HIGH confidence)
- Verified from installed packages and `pip index versions`: all package versions current as of 2026-03-29
- `syft --version` (homebrew): 1.42.3 confirmed installed on dev machine
- `quirk/scanner/ssh_scanner.py` — canonical subprocess+graceful degradation pattern for Phase 3 to clone
- `quirk/cbom/builder.py` — confirmed `is_ssh / else (TLS)` branching at lines 274, 307 requiring extension
- `quirk/cbom/classifier.py` — confirmed JWT algorithm names absent from `_ALGORITHM_TABLE`; RS256/ES256/HS256 need addition
- `quirk/models.py` — confirmed no Phase 3 columns exist yet; `ssh_audit_json` is the last column

### Secondary (MEDIUM confidence)
- RFC 7517 (JWKS), RFC 7518 (JWT algorithms): IETF standard, stable reference for JWKS key structure and algorithm identifiers
- Syft JSON output schema: inferred from syft 1.42.3 documentation and schema version 16.x structure
- boto3 paginator API: documented in official AWS boto3 docs; pagination patterns are stable

### Tertiary (LOW confidence)
- Semgrep `p/cryptography` ruleset coverage: ruleset contents change as rules are added/removed; Phase 3 plan should not hard-code specific rule IDs as acceptance criteria
- Azure App Gateway `ApplicationGatewaySslPolicy` field names: based on azure-mgmt-network 30.x SDK; field names verified against SDK but not tested against live Azure

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against PyPI index on 2026-03-29
- Architecture: HIGH — patterns directly cloned from existing Phase 1 code; integration points identified with line numbers
- Pitfalls: HIGH — pagination trap and CBOM branching trap are verified from reading existing code; semgrep offline trap is documented behavior
- Cloud connector data shapes: MEDIUM — KMS/ACM shapes based on boto3 docs; verified field names match current SDK
- Semgrep ruleset contents: LOW — rule IDs change between versions; treat as guidance only

**Research date:** 2026-03-29
**Valid until:** 2026-04-29 (30 days; boto3/azure-mgmt-network patch versions release weekly but API shapes are stable)
