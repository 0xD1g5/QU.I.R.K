# Phase 30: HashiCorp Vault Connector - Research

**Researched:** 2026-04-26
**Domain:** HashiCorp Vault Python client (hvac), transit keys, PKI mounts, auth methods, chaos lab
**Confidence:** HIGH

---

## Summary

Phase 30 adds `quirk/scanner/vault_connector.py` — the fourth DAR scanner in the v4.3 milestone. It connects to a HashiCorp Vault instance using the `hvac` Python client (>=2.4.0) and audits three surfaces: (1) transit engine key type classification using `VAULT_TRANSIT_KEY_MAP` (including PQC-positive `ml-dsa` and `slh-dsa` key types); (2) PKI mount CA certificate algorithm extraction with RSA-size and SHA-1 findings; (3) active auth method list with risk-tiered findings for token and LDAP methods. All findings write to the `dat_scan_json` column (added in Phase 27) and produce `protocol="VAULT"` CryptoEndpoint rows.

The chaos lab target (HashiCorp Vault in dev mode) already exists in the `storage` Docker Compose profile at port 20009, seeded by `quantum-chaos-enterprise-lab/storage/vault-seed.sh`. Phase 30 must **extend** the vault-seed.sh to create PKI and auth method scenarios, rather than creating a new profile. The existing transit key seed creates `rsa-2048`, `rsa-1024`, `aes256-gcm96`, and `ecdsa-p256` keys — these cover the negative-finding test paths. The seed needs to be extended with PKI CA cert and auth method enablement.

The structural requirements from STATE.md are critical: `session_start` parameter is mandatory (ISSUE-3), a `pyproject.toml` diff adding `hvac>=2.4.0` to `[cloud]` extras is a required PLAN.md deliverable (ISSUE-2), and the `VAULT_AVAILABLE` import guard must follow the exact `GCP_AVAILABLE`/`BOTO3_AVAILABLE` pattern for test patching to work.

**Primary recommendation:** Model `vault_connector.py` after `gcp_connector.py` — same import guard pattern, same per-resource try/except, same `session_start` usage, same `dat_scan_json` field for output. The key novelty is (1) the VAULT_TRANSIT_KEY_MAP with PQC positive entries, (2) PKI CA cert parsing via `cryptography` library (already in core deps), and (3) auth method risk tiering.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Transit key enumeration | API / Backend (scanner) | — | hvac client calls Vault REST API; no browser or DB involvement |
| PKI CA cert extraction | API / Backend (scanner) | — | PEM returned from Vault API; parsed with `cryptography` lib in scanner |
| Auth method listing | API / Backend (scanner) | — | `client.sys.list_auth_methods()` is a sys API call; risk logic stays in scanner |
| VAULT_TRANSIT_KEY_MAP | API / Backend (scanner) | — | Same tier as GCP_KMS_ALGORITHM_MAP — module-level constant in scanner |
| Score impact | Intelligence layer | — | `dar_vault_weak_count` counter follows dar_ subscore pattern from Phase 27/28 |
| CBOM integration | CBOM builder | — | "VAULT" added to Pass 1/2/3 skip lists, same as "POSTGRESQL"/"S3" |
| dat_scan_json persistence | Database | — | Column already exists from Phase 27; scanner just writes to it |
| Chaos lab Vault instance | CDN / Static (infra) | — | Already running at port 20009 in `storage` profile |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hvac | 2.4.0 | HashiCorp Vault Python client | Official Python SDK maintained by HashiCorp community; only production-grade option |
| cryptography | >=44.0 (already core dep) | Parse PKI CA cert PEM to extract algorithm/key size | Already in pyproject.toml core; x509.load_pem_x509_certificate is the standard path |

[VERIFIED: pip index versions hvac] hvac 2.4.0 is the current latest version as of 2026-04-26.
[VERIFIED: pyproject.toml] `cryptography>=44.0` is already in core `dependencies` — no new dep needed.

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hashicorp/vault:1.15 | 1.15 | Chaos lab Docker image | Already used in storage profile; extend existing seed |

[VERIFIED: docker-compose.yml line 687] `image: hashicorp/vault:1.15` already pinned in storage profile.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hvac | requests + raw Vault REST | hvac is higher-level and handles auth/retry; raw requests is more work with no benefit |
| cryptography x509 | pyOpenSSL | cryptography is already a core dep; pyOpenSSL is not and introduces transitive conflicts |

**Installation:**
```bash
pip install "hvac>=2.4.0"
```

**Version verification:**
```
hvac (2.4.0) confirmed current via pip index versions
```

---

## Architecture Patterns

### System Architecture Diagram

```
VAULT_ADDR / config.vault_addr
VAULT_TOKEN / VAULT_TOKEN env
        |
        v
 scan_vault_targets(vault_addr, token, session_start, logger)
        |
        +--[HVAC_AVAILABLE check]---> return [] (no hvac installed)
        |
        +--[token missing]---> return [scan_error CryptoEndpoint]
        |
        v
  hvac.Client(url=vault_addr, token=token, timeout=10)
        |
        +--[client.is_authenticated() False]---> return [scan_error: vault-auth-failed]
        |
        +--- _scan_transit_keys(client, logger, session_start)
        |         |
        |         +--> client.secrets.transit.list_keys()
        |         |    -> iterate key names
        |         +--> client.secrets.transit.read_key(name)
        |              -> extract key["data"]["type"] -> VAULT_TRANSIT_KEY_MAP lookup
        |              -> CryptoEndpoint(protocol="VAULT", dat_scan_json=...)
        |
        +--- _scan_pki_mounts(client, logger, session_start)
        |         |
        |         +--> client.sys.list_mounted_secrets_engines()["data"]
        |         |    -> filter type == "pki"
        |         +--> client.secrets.pki.read_ca_certificate(mount_point=path)
        |              -> PEM string -> cryptography.x509.load_pem_x509_certificate()
        |              -> extract sig_alg name + RSA key size
        |              -> HIGH finding if RSA<4096 or SHA-1
        |
        +--- _scan_auth_methods(client, logger, session_start)
                  |
                  +--> client.sys.list_auth_methods()["data"]
                  |    -> iterate mount paths
                  +--> AUTH_RISK_MAP lookup on method type
                       -> HIGH/MEDIUM/INFO per method
                       -> CryptoEndpoint(protocol="VAULT", dat_scan_json=...)
        |
        v
  List[CryptoEndpoint] -> run_scan.py vault_scanning block
        |
        v
  dat_scan_json persisted to SQLite
  Protocol="VAULT" added to CBOM Pass 1/2/3 skip lists
  dar_vault_weak_count -> evidence.py -> scoring.py dar_impacts
```

### Recommended Project Structure
```
quirk/
├── scanner/
│   ├── vault_connector.py   # NEW: scan_vault_targets + helpers + VAULT_TRANSIT_KEY_MAP
quantum-chaos-enterprise-lab/
├── storage/
│   └── vault-seed.sh        # MODIFY: add PKI + userpass/ldap auth method setup
labs/
├── storage/
│   └── expected_results.md  # MODIFY: add Vault section
```

### Pattern 1: VAULT_TRANSIT_KEY_MAP (analogous to GCP_KMS_ALGORITHM_MAP)

**What:** Module-level dict mapping Vault transit key type strings to (alg_name, key_size) tuples. The `alg_name` strings must match entries already in `quirk/cbom/classifier.py` where possible.

**When to use:** In `_scan_transit_keys()` to classify each key's type after `read_key()` returns.

```python
# Source: Verified against Vault transit key type documentation + classifier.py entries
# Vault transit key type -> (alg_name for cert_pubkey_alg, key_size for cert_pubkey_size)
VAULT_TRANSIT_KEY_MAP = {
    # Symmetric encryption
    "aes128-gcm96":       ("AES", 128),
    "aes256-gcm96":       ("AES", 256),
    "chacha20-poly1305":  ("chacha20-poly1305", 256),
    # Asymmetric signing
    "ed25519":            ("ed25519", 256),
    "ecdsa-p256":         ("ECDSA", 256),
    "ecdsa-p384":         ("ECDSA", 384),
    "ecdsa-p521":         ("ECDSA", 521),
    "rsa-2048":           ("RSA", 2048),
    "rsa-3072":           ("RSA", 3072),
    "rsa-4096":           ("RSA", 4096),
    # HMAC
    "hmac":               ("HMAC", 256),
    # PQC (NIST FIPS 204/205 — positive quantum-safe findings)
    # NOTE: Vault OSS does not support ml-dsa/slh-dsa as of 1.15.
    # These are Vault Enterprise / future Vault versions.
    # Include in the map so the scanner handles them correctly when present.
    "ml-dsa-44":          ("ml-dsa-44", None),
    "ml-dsa-65":          ("ml-dsa-65", None),
    "ml-dsa-87":          ("ml-dsa-87", None),
    "slh-dsa-shake-128s": ("slh-dsa-128", None),
    "slh-dsa-shake-192s": ("slh-dsa-192", None),
    "slh-dsa-shake-256s": ("slh-dsa-256", None),
}
```

**PQC positive finding mechanism:** The `alg_name` values `"ml-dsa-87"`, `"slh-dsa-128"`, etc. are already in `quirk/cbom/classifier.py` with `nist_level >= 1`. The CBOM builder's Pass 1 registers these algorithms, and `quantum_safety_label(nist_level)` returns `"quantum-safe"`. No new classifier entries needed — the names already match. [VERIFIED: classifier.py lines 141-146]

**Classifier gap:** Vault key types `"rsa-2048"`, `"rsa-3072"`, `"rsa-4096"`, `"ecdsa-p256"`, `"ecdsa-p384"`, `"ecdsa-p521"`, `"aes256-gcm96"`, `"aes128-gcm96"` are NOT in the classifier under those exact names. The scanner should map them to short-form names (`"RSA"`, `"ECDSA"`, `"AES"`) which are in the classifier. [VERIFIED: classifier.py grep for rsa/ecdsa/aes entries] The `GCP_KMS_ALGORITHM_MAP` follows this same pattern — it normalizes `"RSA_SIGN_PKCS1_2048_SHA256"` to `("RSA", 2048)`.

### Pattern 2: hvac Client Initialization

**What:** Build the hvac client from config addr + token (with env var fallback). The client does NOT automatically pick up `VAULT_TOKEN` from the environment — it must be explicitly set. [VERIFIED: hvac Context7 docs]

**When to use:** Top of `scan_vault_targets()` before any API calls.

```python
# Source: Context7 /hvac/hvac — Initialize hvac Client
import os
import hvac

def scan_vault_targets(vault_addr: str, token: str | None = None,
                       logger=None, session_start=None) -> List[CryptoEndpoint]:
    if not HVAC_AVAILABLE:
        return []
    # Token resolution order: explicit arg -> VAULT_TOKEN env var
    resolved_token = token or os.environ.get("VAULT_TOKEN", "")
    if not resolved_token:
        return [CryptoEndpoint(
            host=vault_addr or "vault://unknown",
            port=8200,
            protocol="VAULT",
            scan_error="vault-no-token: set VAULT_TOKEN or vault_token in config",
        )]
    resolved_addr = vault_addr or os.environ.get("VAULT_ADDR", "http://127.0.0.1:8200")
    client = hvac.Client(url=resolved_addr, token=resolved_token, timeout=10)
    if not client.is_authenticated():
        return [CryptoEndpoint(
            host=resolved_addr,
            port=8200,
            protocol="VAULT",
            scan_error="vault-auth-failed: token rejected or Vault sealed",
        )]
    ...
```

**Note:** `VAULT_ADDR` env var is NOT automatically picked up by hvac either — it must be passed as `url=`. [ASSUMED based on Context7 docs showing explicit `url=` parameter; hvac may support env fallback in some versions but the explicit pattern is safest.]

### Pattern 3: Transit Key Listing and Classification

**What:** List all key names, then read each key to get its `type` field.

**When to use:** In `_scan_transit_keys()`.

```python
# Source: Context7 /hvac/hvac — List Keys + Read Key
def _scan_transit_keys(client, mount_point: str, logger, session_start) -> List[CryptoEndpoint]:
    results = []
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    try:
        # list_keys returns {"data": {"keys": {"key-name": {}, ...}}}
        list_response = client.secrets.transit.list_keys(mount_point=mount_point)
        key_names = list_response.get("data", {}).get("keys", {})
        for key_name in key_names:
            try:
                read_response = client.secrets.transit.read_key(
                    name=key_name, mount_point=mount_point
                )
                key_data = read_response.get("data", {})
                key_type = key_data.get("type", "")
                alg_name, key_size = VAULT_TRANSIT_KEY_MAP.get(
                    key_type, (key_type or "UNKNOWN", None)
                )
                ep = CryptoEndpoint(
                    host=f"{client.url}/transit/keys/{key_name}",
                    port=8200,
                    protocol="VAULT",
                    cert_pubkey_alg=alg_name,
                    cert_pubkey_size=key_size,
                    service_detail=f"transit/{key_name}",
                    dat_scan_json=json.dumps({
                        "key_name": key_name,
                        "key_type": key_type,
                        "exportable": key_data.get("exportable", False),
                        "latest_version": key_data.get("latest_version"),
                    }, default=str),
                    scanned_at=now,
                )
                results.append(ep)
            except Exception as exc:
                if logger:
                    logger.v(f"Vault transit key read error for {key_name}: {exc}")
    except Exception as exc:
        if logger:
            logger.v(f"Vault transit list_keys error: {exc}")
    return results
```

**API detail:** `client.secrets.transit.list_keys(mount_point="transit")` returns the key names as dict keys (not a list). `client.secrets.transit.read_key(name=..., mount_point=...)` returns a dict with `data.type` (the key type string) and `data.latest_version`, `data.exportable`, etc. [VERIFIED: Context7 /hvac/hvac transit docs]

### Pattern 4: PKI Mount Discovery and CA Cert Parsing

**What:** List all mounted secrets engines, filter to `type == "pki"`, then call `read_ca_certificate()` for each PKI mount. Parse the returned PEM with `cryptography.x509`.

**When to use:** In `_scan_pki_mounts()`.

```python
# Source: Context7 /hvac/hvac — list_mounted_secrets_engines + PKI read_ca_certificate
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa as crypto_rsa

def _scan_pki_mounts(client, logger, session_start) -> List[CryptoEndpoint]:
    results = []
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    try:
        mounts = client.sys.list_mounted_secrets_engines().get("data", {})
        for path, mount_info in mounts.items():
            if mount_info.get("type") != "pki":
                continue
            mount_point = path.rstrip("/")
            try:
                pem_str = client.secrets.pki.read_ca_certificate(mount_point=mount_point)
                # read_ca_certificate returns the PEM string directly (not a dict)
                cert = x509.load_pem_x509_certificate(pem_str.encode())
                sig_alg = cert.signature_algorithm_oid.dotted_string
                sig_alg_name = cert.signature_hash_algorithm.name if cert.signature_hash_algorithm else "unknown"
                pub_key = cert.public_key()
                key_size = getattr(pub_key, "key_size", None)
                # Severity logic
                severity = None
                finding_reason = ""
                if isinstance(pub_key, crypto_rsa.RSAPublicKey) and (key_size or 0) < 4096:
                    severity = "HIGH"
                    finding_reason = f"RSA-{key_size} signing key below 4096-bit threshold"
                elif "sha1" in sig_alg_name.lower():
                    severity = "HIGH"
                    finding_reason = "SHA-1 signing algorithm"
                ep = CryptoEndpoint(
                    host=f"{client.url}/pki/{mount_point}",
                    port=8200,
                    protocol="VAULT",
                    cert_pubkey_alg=sig_alg_name,
                    cert_pubkey_size=key_size,
                    service_detail=f"PKI/{mount_point}",
                    severity=severity,
                    dat_scan_json=json.dumps({
                        "mount_point": mount_point,
                        "sig_alg": sig_alg_name,
                        "key_size": key_size,
                        "finding": finding_reason or "ok",
                    }, default=str),
                    scanned_at=now,
                )
                results.append(ep)
            except Exception as exc:
                if logger:
                    logger.v(f"Vault PKI scan error for mount {mount_point}: {exc}")
    except Exception as exc:
        if logger:
            logger.v(f"Vault list_mounted_secrets_engines error: {exc}")
    return results
```

**API detail:** `client.secrets.pki.read_ca_certificate(mount_point=...)` returns a PEM string directly, not a dict. The `mount_point` arg for non-default PKI mounts must strip the trailing slash from the path key. [VERIFIED: Context7 /hvac/hvac PKI docs]

**PKI parsing gap:** `rsa-1024` keys in the existing vault-seed.sh are on transit keys, not PKI CA certs. The chaos lab seed must be extended to mount a PKI engine with a known weak CA cert for RED path testing.

### Pattern 5: Auth Method Risk Classification

**What:** List all auth methods via `client.sys.list_auth_methods()`, map each method's `type` field to a risk tier, produce one CryptoEndpoint per method.

**When to use:** In `_scan_auth_methods()`.

```python
# Source: Context7 /hvac/hvac — list_auth_methods

# Risk map — higher risk methods get HIGH finding; medium-risk get MEDIUM
AUTH_RISK_MAP = {
    "token":    ("HIGH",   "Root token auth method enabled — eliminate root token usage; use AppRole or entity-bound tokens"),
    "ldap":     ("HIGH",   "LDAP auth enabled — ensure bind credentials are service-account bound, not root bind DN"),
    "userpass": ("MEDIUM", "Userpass auth enabled — prefer short-lived token auth methods (AppRole, k8s)"),
    "radius":   ("MEDIUM", "RADIUS auth enabled — legacy auth method; prefer OIDC or AppRole"),
    "github":   ("MEDIUM", "GitHub auth enabled — tokens are long-lived; prefer OIDC"),
    "approle":  (None,     "AppRole auth — low risk; no finding"),
    "kubernetes": (None,   "Kubernetes auth — low risk; no finding"),
    "jwt":      (None,     "JWT/OIDC auth — low risk; no finding"),
    "oidc":     (None,     "OIDC auth — low risk; no finding"),
    "aws":      (None,     "AWS IAM auth — low risk; no finding"),
    "gcp":      (None,     "GCP auth — low risk; no finding"),
    "cert":     (None,     "TLS cert auth — low risk; no finding"),
}

def _scan_auth_methods(client, logger, session_start) -> List[CryptoEndpoint]:
    results = []
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    try:
        auth_methods = client.sys.list_auth_methods().get("data", {})
        for path, method_info in auth_methods.items():
            method_type = method_info.get("type", "")
            risk_tuple = AUTH_RISK_MAP.get(method_type)
            if risk_tuple is None:
                risk_tuple = (None, f"Unknown auth method type: {method_type}")
            severity, remediation = risk_tuple
            if severity is None:
                continue  # positive posture — no finding needed
            ep = CryptoEndpoint(
                host=f"{client.url}/auth/{path}",
                port=8200,
                protocol="VAULT",
                cert_pubkey_alg=method_type,
                service_detail=f"auth/{path}",
                severity=severity,
                dat_scan_json=json.dumps({
                    "auth_path": path,
                    "auth_type": method_type,
                    "remediation": remediation,
                }, default=str),
                scanned_at=now,
            )
            results.append(ep)
    except Exception as exc:
        if logger:
            logger.v(f"Vault list_auth_methods error: {exc}")
    return results
```

**VAULT_TOKEN env-var risk:** The `token` auth method is always present in dev-mode Vault. The finding text should mention VAULT_TOKEN specifically when the `token` path is detected. [ASSUMED: risk classification tiers are based on general Vault security best practices; no authoritative NIST/CIS mapping verified in this session.]

### Pattern 6: run_scan.py Integration (vault_scanning block)

**Analog:** `run_scan.py` db_scanning block (lines 506-524) — exact structural template.

```python
# Source: run_scan.py db_scanning block pattern
vault_endpoints = []
with _phase_timer(run_stats, "vault_scanning"):
    if cfg.connectors.enable_vault:
        from quirk.scanner.vault_connector import scan_vault_targets, HVAC_AVAILABLE
        if not HVAC_AVAILABLE:
            logger.v("hvac not installed — Vault scanning skipped")
        elif not (cfg.connectors.vault_addr or os.environ.get("VAULT_ADDR")):
            logger.v("vault_addr not configured — Vault scanning skipped")
        else:
            vault_endpoints = scan_vault_targets(
                vault_addr=cfg.connectors.vault_addr or "",
                token=cfg.connectors.vault_token,
                logger=logger,
                session_start=session_start,
            )
            logger.info(f"Vault scan: {len(vault_endpoints)} endpoints")
```

**Endpoint aggregation line** — append `+ vault_endpoints` to the existing list (currently ends with `+ kerberos_endpoints`).

### Pattern 7: config.py ConnectorsCfg Fields

```python
# Analog: DB connector config (lines 73-80) — exact pattern
# Vault connector config (v4.3, Phase 30)
enable_vault: bool = False
vault_addr: Optional[str] = None        # e.g. "http://localhost:8200"
vault_token: Optional[str] = None       # if None, falls back to VAULT_TOKEN env var
vault_transit_mount: str = "transit"    # non-default transit mount path
```

**config_template.yaml addition:**
```yaml
  # -- HashiCorp Vault connector (optional, requires: pip install quirk[cloud]) --
  # enable_vault: false
  # vault_addr: "http://localhost:8200"
  # vault_token: null          # defaults to VAULT_TOKEN env var
  # vault_transit_mount: "transit"
```

### Pattern 8: pyproject.toml diff (ISSUE-2 mandatory deliverable)

The Phase 30 plan MUST include this exact diff as a required deliverable:

```toml
# Before:
cloud = [
    "google-api-python-client>=2.0.0",
    "google-auth>=2.36.0",
    "azure-mgmt-storage>=21.0.0",  # Phase 28: Azure Blob encryption audit (STOR-02)
]

# After (Phase 30):
cloud = [
    "google-api-python-client>=2.0.0",
    "google-auth>=2.36.0",
    "azure-mgmt-storage>=21.0.0",  # Phase 28: Azure Blob encryption audit (STOR-02)
    "hvac>=2.4.0",                  # Phase 30: HashiCorp Vault connector (VAULT-01/02/03)
]
```

[VERIFIED: pyproject.toml cloud extras current state] [VERIFIED: pip index versions — hvac 2.4.0 is current]

### Anti-Patterns to Avoid

- **Catching all exceptions at top level and silently returning []:** Each sub-scanner (`_scan_transit_keys`, `_scan_pki_mounts`, `_scan_auth_methods`) must return its own results independently. A PKI scan failure must not suppress transit key results. The outer `scan_vault_targets` aggregates from all three.
- **Not calling `client.is_authenticated()` before API calls:** An invalid token raises `hvac.exceptions.Forbidden` on every call; checking upfront produces one clean `scan_error` endpoint instead of three cryptic exception traces.
- **Using `mount_point` without stripping trailing slash:** `client.sys.list_mounted_secrets_engines()` returns paths with trailing slashes (`"transit/"`, `"pki/"`). Pass these with trailing slash stripped to sub-calls.
- **Treating `read_ca_certificate()` response as a dict:** The PKI `read_ca_certificate()` method returns the PEM string directly, not a response dict. [VERIFIED: Context7 /hvac/hvac PKI docs]
- **Adding VAULT to `_PROTOCOL_KEYS` without adding dar_vault counters:** The `_PROTOCOL_KEYS` tuple in evidence.py must be extended, and a `dar_vault_weak_count` counter must be added to the for-ep loop.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vault API authentication | Raw requests + token header | `hvac.Client(url=..., token=...)` | hvac handles auth, session, retries, and error types |
| PKI CA cert algorithm extraction | ASN.1 parsing from scratch | `cryptography.x509.load_pem_x509_certificate()` | cryptography is already a core dep; x509 object has `.signature_hash_algorithm` and `.public_key()` |
| Vault transit key enumeration | Raw `GET /v1/transit/keys` | `client.secrets.transit.list_keys()` + `read_key()` | hvac wraps pagination, auth headers, and JSON parsing |
| Auth method listing | Raw `GET /v1/sys/auth` | `client.sys.list_auth_methods()` | hvac handles the sys backend consistently |

**Key insight:** The `cryptography` library (already core) eliminates any need to parse PEM manually for the PKI CA cert use case. The only new dependency is `hvac` itself.

---

## Runtime State Inventory

Phase 30 is a new connector (not a rename/refactor). The existing `vault-seed.sh` creates transit keys that will be scanned. The relevant runtime state is:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Vault dev-mode state is ephemeral (in-memory); transit keys created by vault-seed.sh persist only for the container lifetime | No migration needed — seed script is the source of truth |
| Live service config | Vault in dev mode at port 20009 (storage profile) — already seeded with transit keys (rsa-2048, rsa-1024, aes256-gcm96, ecdsa-p256) | Extend vault-seed.sh to add PKI mount + auth methods |
| OS-registered state | None — Vault is Docker-only in chaos lab | None |
| Secrets/env vars | VAULT_TOKEN=root used in vault-seed.sh and docker-compose.yml; Phase 30 scanner reads from VAULT_TOKEN env var | Code only — no key rename |
| Build artifacts | None | None |

**Existing vault-seed.sh gap:** The current seed creates transit keys but does NOT create a PKI mount or enable any non-default auth methods. The Phase 30 chaos lab test needs at minimum: (1) PKI mount with a known RSA-2048 CA cert (HIGH finding path), (2) userpass auth method enabled (MEDIUM finding path). The `token` auth method is always present in dev mode (HIGH finding guaranteed without seed changes).

---

## Common Pitfalls

### Pitfall 1: `list_keys` Returns Dict Keys, Not a List
**What goes wrong:** `client.secrets.transit.list_keys()["data"]["keys"]` is a dict (key name → empty dict), not a list. Iterating the dict iterates key names — which is correct — but accessing `.values()` instead of direct iteration breaks the loop.
**Why it happens:** The Vault API returns a HATEOAS-style map, and hvac preserves this structure.
**How to avoid:** Use `for key_name in key_names:` where `key_names = response["data"]["keys"]`. Do not call `.keys()` explicitly.
**Warning signs:** Loop body never executes despite Vault having keys.

### Pitfall 2: `read_ca_certificate` Returns PEM String, Not Dict
**What goes wrong:** `client.secrets.pki.read_ca_certificate(mount_point=...)["certificate"]` raises `TypeError: string indices must be integers` because the method returns the PEM string directly.
**Why it happens:** Unlike most hvac methods, PKI read_ca_certificate bypasses JSON deserialization.
**How to avoid:** Use the raw return value: `pem_str = client.secrets.pki.read_ca_certificate(mount_point=...)`. Then `cert = x509.load_pem_x509_certificate(pem_str.encode())`.
**Warning signs:** `TypeError: string indices must be integers` in PKI scan function.

### Pitfall 3: Mount Paths Have Trailing Slashes
**What goes wrong:** `client.secrets.transit.list_keys(mount_point="transit/")` raises `InvalidPath` because the mount_point parameter must NOT have a trailing slash.
**Why it happens:** `list_mounted_secrets_engines()` returns `"transit/"` as the dict key; passing this directly to sub-calls breaks the API path construction.
**How to avoid:** Always strip trailing slash: `mount_point = path.rstrip("/")`.
**Warning signs:** `hvac.exceptions.InvalidPath` on every transit/PKI call.

### Pitfall 4: `is_authenticated()` Makes a Network Call
**What goes wrong:** `client.is_authenticated()` makes an actual HTTP request to Vault. If Vault is unreachable, it raises a `requests.exceptions.ConnectionError`, not an hvac exception.
**Why it happens:** hvac delegates connectivity to `requests`; the session creation is local but the auth check is remote.
**How to avoid:** Wrap the `is_authenticated()` call in a broad `except Exception` that maps to a `scan_error` finding.
**Warning signs:** Unhandled `ConnectionError` in tests that patch `is_authenticated`.

### Pitfall 5: Vault Dev Mode Has `token` Auth Always Enabled
**What goes wrong:** Tests that expect "no auth method findings" fail because dev mode always has `token/` in the auth method list.
**Why it happens:** Vault dev mode bootstraps with a root token and keeps `token` auth always active.
**How to avoid:** Tests for the "no-findings" path must either mock `list_auth_methods()` to return only `approle/`, or test the positive case (`token` produces HIGH) and not rely on dev mode producing zero auth-method findings.
**Warning signs:** Test expects 0 auth endpoints but gets 1 (the always-present `token/` mount).

### Pitfall 6: CBOM builder VAULT skip list gap
**What goes wrong:** `"VAULT"` protocol endpoints fall through to the TLS `else` branch in CBOM Pass 1, causing spurious "certificate not found" warnings or hollow component entries.
**Why it happens:** builder.py has explicit skip tuples for every protocol. Any new protocol must be added explicitly.
**How to avoid:** Add `"VAULT"` to Pass 1 `elif`, Pass 2 skip list, and Pass 3 skip list in `quirk/cbom/builder.py`.
**Warning signs:** CBOM output contains `VAULT` protocol CryptoComponent entries with empty algorithm fields.

### Pitfall 7: Score cap — existing 5-subscore ceiling already accounts for DAR
**What goes wrong:** Adding a `dar_vault_weak_count` to evidence.py triggers a new weight in scoring.py, but the `dar_score` subscore already exists (from Phase 27) and is capped at 25. Adding more `dar_` impacts to the existing `dar_impacts` list is safe — the cap is per-subscore, not per-impact-item.
**Why it happens:** `_apply_weighted_impacts` clamps each subscore independently; adding more negative impacts just reaches the floor faster.
**How to avoid:** Add `dar_vault_weak_count` as a new impact tuple in the existing `dar_impacts` list. Do NOT create a new sixth subscore — that would change `NUM_SUBSCORES` from 5 and break `test_intelligence_scoring.py`.
**Warning signs:** `test_compute_readiness_score_shape` fails if `NUM_SUBSCORES` is changed.

---

## Code Examples

### Import Guard Pattern (mandatory for test patching)

```python
# Source: gcp_connector.py lines 23-32 — exact pattern to replicate
try:
    import hvac
    from hvac import exceptions as hvac_exceptions
    HVAC_AVAILABLE = True
except ImportError:
    hvac = None           # type: ignore[assignment]
    hvac_exceptions = None  # type: ignore[assignment]
    HVAC_AVAILABLE = False
```

The module-level `None` assignment is mandatory. Tests patch `quirk.scanner.vault_connector.HVAC_AVAILABLE` to `False` to test the unavailable path without installing hvac.

### Exception Hierarchy to Catch

```python
# Source: Context7 /hvac/hvac — Handle Vault Errors
# Catch order matters: specific before general
from hvac import exceptions as hvac_exceptions

try:
    ...
except hvac_exceptions.InvalidPath:
    # 404 — transit engine not enabled or key doesn't exist
    ...
except hvac_exceptions.Forbidden:
    # 403 — token lacks policy to read this resource
    ...
except hvac_exceptions.Unauthorized:
    # 401 — invalid token
    ...
except hvac_exceptions.VaultDown:
    # 503 — Vault sealed or unreachable
    ...
except hvac_exceptions.VaultError:
    # Base class — catch-all for other Vault API errors
    ...
except Exception:
    # Connection errors (requests.exceptions.ConnectionError etc.)
    ...
```

In practice, per-resource inner try/except blocks can use `except Exception as exc:` with `logger.v()` — matching the `aws_connector.py` and `gcp_connector.py` convention. The outer function body should also use `except Exception` to produce a `scan_error` CryptoEndpoint on connection failure.

### scan_error Finding Pattern

```python
# Source: db_connector.py lines 154-161 — scan_error CryptoEndpoint pattern
results.append(CryptoEndpoint(
    host=vault_addr,
    port=8200,
    protocol="VAULT",
    scan_error=f"vault-connection-error: {type(exc).__name__}: {exc}",
    scanned_at=now,
))
```

### Evidence Counter Pattern for dar_vault

```python
# Source: evidence.py lines 79-84 (dar_db_* counters) — extend this pattern
# After dar_storage_aws_managed_count initialization:
dar_vault_weak_count = 0   # transit keys with RSA<4096 or deprecated alg + PKI HIGH + HIGH auth methods

# In the elif chain (after elif proto == "AZURE_BLOB":):
elif proto == "VAULT":
    sev = str(getattr(ep, "severity", "") or "")
    if sev == "HIGH":
        dar_vault_weak_count += 1

# In return dict (after dar_storage_aws_managed_ratio):
"dar_vault_weak_count": dar_vault_weak_count,
"dar_vault_weak_ratio": round(dar_vault_weak_count / total_endpoints, 4) if total_endpoints else 0.0,
```

### scoring.py Impact Addition (in existing dar_impacts list)

```python
# Source: scoring.py lines 172-177 (existing dar_impacts) — append new tuple only
# DO NOT add a new subscore block — add to existing dar_impacts list
dar_impacts: List[Tuple[str, float]] = [
    ("Database plaintext connections", -_ratio(dar_db_plaintext, denom) * w["dar_db_plaintext_ratio"]),
    ("Database weak SSL configuration", -_ratio(dar_db_weak_ssl, denom) * w["dar_db_weak_ssl_ratio"]),
    ("Object storage unencrypted", -_ratio(dar_storage_unencrypted, denom) * w["dar_storage_unencrypted_ratio"]),
    ("Object storage platform-managed keys", -_ratio(dar_storage_aws_managed, denom) * w["dar_storage_aws_managed_ratio"]),
    # Phase 30 addition:
    ("Vault weak crypto posture", -_ratio(dar_vault_weak, denom) * w["dar_vault_weak_ratio"]),
]
```

New SCORE_WEIGHTS entry: `"dar_vault_weak_ratio": 8.0` (lighter than db-plaintext at 12.0; Vault misconfiguration is a policy gap, not a plaintext exposure).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| hvac 0.x API (`client.secrets.transit.list()`) | hvac 2.x API (`client.secrets.transit.list_keys()`) | hvac 1.0 (2022) | Method names changed; old tutorials reference 0.x API |
| `client.sys.list_auth_backends()` | `client.sys.list_auth_methods()` | hvac 1.0 | Renamed for clarity |
| `client.read("transit/keys/foo")` | `client.secrets.transit.read_key(name="foo")` | hvac 1.0 | Structured namespace API replaces raw path API |

[VERIFIED: Context7 /hvac/hvac — all examples use 2.x API] [VERIFIED: hvac 2.4.0 is current]

**Deprecated/outdated:**
- `client.list("transit/keys")` (raw path): Replaced by `client.secrets.transit.list_keys()`; raw path still works but is undocumented in hvac 2.x
- `client.sys.list_auth_backends()`: Renamed to `client.sys.list_auth_methods()` in hvac 1.0

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `hvac.Client` does NOT automatically read `VAULT_TOKEN` from env — token must be set explicitly | Architecture Patterns P2 | Low risk: if hvac does auto-read env, the explicit `os.environ.get("VAULT_TOKEN")` fallback still works |
| A2 | `VAULT_ADDR` env var is NOT auto-read by hvac — `url=` must be passed explicitly | Architecture Patterns P2 | Low risk: same fallback applies; explicit is always safer |
| A3 | Auth method risk tiers (AUTH_RISK_MAP) reflect Vault security best practices | Architecture Patterns P5 | Medium: if project has different risk appetite, risk levels may need adjustment |
| A4 | `ml-dsa` and `slh-dsa` key types are not supported in Vault OSS 1.15 | Standard Stack / VAULT_TRANSIT_KEY_MAP | Low: the map handles them correctly if/when they appear; chaos lab uses standard key types for RED/GREEN tests |
| A5 | `dar_vault_weak_ratio` weight of 8.0 is appropriate relative to `dar_db_plaintext_ratio` (12.0) | Code Examples | Medium: weight is a discretion-area choice; planner can adjust |

---

## Open Questions (RESOLVED)

1. **Vault transit mount path — always "transit"?**
   - What we know: The existing chaos lab enables transit at `"transit"`. The config adds `vault_transit_mount: str = "transit"` as a configurable field.
   - What's unclear: In production, customers may mount transit at a custom path (e.g., `"encryption/"`). The scanner should either enumerate all mounts of type `"transit"` (like PKI discovery), or require explicit config.
   - Recommendation: Enumerate via `list_mounted_secrets_engines()` filtering `type == "transit"`, same as PKI. This is more robust than config-driven path. Add as a planning decision to confirm.

2. **PKI CA cert chaos lab scenario**
   - What we know: vault-seed.sh does not currently enable a PKI mount.
   - What's unclear: Does the `hashicorp/vault:1.15` dev-mode image support `vault secrets enable pki` and `vault write pki/root/generate/internal common_name=... key_type=rsa key_bits=2048` without additional setup?
   - Recommendation: Yes, dev mode supports all secrets engines. The seed extension should enable PKI and generate an RSA-2048 root CA (intentionally weak, below 4096-bit threshold). This produces a HIGH finding on scan.

3. **Auth method chaos lab — do we need to seed LDAP?**
   - What we know: `vault auth enable userpass` is simple and requires no external LDAP server. The `token` method is always present.
   - What's unclear: LDAP auth requires an actual LDAP server to be useful, and VAULT-03 says "LDAP root bind" is a risk signal, not that LDAP itself requires a live LDAP backend.
   - Recommendation: Enable `userpass` (MEDIUM finding) and rely on the always-present `token` method (HIGH finding). Skip LDAP in the chaos lab to avoid the dependency on a live LDAP server.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| hvac | vault_connector.py | ✗ (not in dev env) | — | Module-level HVAC_AVAILABLE guard; scanner returns [] |
| hashicorp/vault:1.15 Docker image | Chaos lab | ✓ | 1.15 | — |
| cryptography | PKI CA cert parsing | ✓ | >=44.0 (core dep) | — |
| docker (for chaos lab) | Phase 30 chaos lab testing | ✓ | — | Manual Vault setup |

[VERIFIED: pyproject.toml — cryptography>=44.0 in core dependencies]
[VERIFIED: docker-compose.yml — hashicorp/vault:1.15 already in storage profile]
[VERIFIED: pip3 show hvac — hvac IS installed in dev env (2.4.0)]

**Note:** `pip3 show hvac` returned `hvac (2.4.0)` — hvac IS available in the dev environment. The `HVAC_AVAILABLE` guard is still required for CI/pip install without `[cloud]` extras.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (inferred from conftest.py + existing test files) |
| Config file | None detected — tests run from project root |
| Quick run command | `python -m pytest tests/test_vault_connector.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VAULT-01 | Transit key type enumeration + quantum-safe classification for ml-dsa/slh-dsa | unit (mock) | `pytest tests/test_vault_connector.py::test_transit_key_aes256_no_finding -x` | ❌ Wave 0 |
| VAULT-01 | rsa-2048 transit key produces no severity (informational) | unit (mock) | `pytest tests/test_vault_connector.py::test_transit_key_rsa2048 -x` | ❌ Wave 0 |
| VAULT-01 | ml-dsa-87 transit key produces quantum-safe alg_name in cert_pubkey_alg | unit (mock) | `pytest tests/test_vault_connector.py::test_transit_key_ml_dsa_positive -x` | ❌ Wave 0 |
| VAULT-02 | PKI CA cert RSA-2048 produces HIGH finding | unit (mock) | `pytest tests/test_vault_connector.py::test_pki_rsa2048_high_finding -x` | ❌ Wave 0 |
| VAULT-02 | PKI CA cert RSA-4096 produces no severity | unit (mock) | `pytest tests/test_vault_connector.py::test_pki_rsa4096_no_finding -x` | ❌ Wave 0 |
| VAULT-02 | PKI CA cert SHA-1 produces HIGH finding | unit (mock) | `pytest tests/test_vault_connector.py::test_pki_sha1_high_finding -x` | ❌ Wave 0 |
| VAULT-03 | Token auth method produces HIGH finding | unit (mock) | `pytest tests/test_vault_connector.py::test_auth_token_high -x` | ❌ Wave 0 |
| VAULT-03 | LDAP auth method produces HIGH finding | unit (mock) | `pytest tests/test_vault_connector.py::test_auth_ldap_high -x` | ❌ Wave 0 |
| VAULT-03 | AppRole auth method produces no finding | unit (mock) | `pytest tests/test_vault_connector.py::test_auth_approle_no_finding -x` | ❌ Wave 0 |
| VAULT-01/02/03 | Connection error produces scan_error endpoint | unit (mock) | `pytest tests/test_vault_connector.py::test_connection_error_scan_error -x` | ❌ Wave 0 |
| VAULT-01/02/03 | Invalid token produces scan_error endpoint | unit (mock) | `pytest tests/test_vault_connector.py::test_invalid_token_scan_error -x` | ❌ Wave 0 |
| VAULT-01/02/03 | HVAC_AVAILABLE=False returns empty list | unit (mock) | `pytest tests/test_vault_connector.py::test_hvac_unavailable_returns_empty -x` | ❌ Wave 0 |
| VAULT-01/02/03 | Live Vault chaos lab scan produces expected findings | integration (Docker) | `docker compose --profile storage up -d && pytest tests/test_chaos_vault.py -x` | ❌ Wave 0 |
| VAULT-01/02/03 | dat_scan_json populated on all VAULT endpoints | unit (mock) | `pytest tests/test_vault_connector.py::test_dat_scan_json_populated -x` | ❌ Wave 0 |

### RED/GREEN/REFACTOR Test Strategy

**What can be unit-tested with hvac mocks (most of it):**

All three scanner functions (`_scan_transit_keys`, `_scan_pki_mounts`, `_scan_auth_methods`) can be fully unit-tested by patching the hvac client:

```python
# Pattern: mock hvac.Client() before scan_vault_targets() call
with patch("quirk.scanner.vault_connector.hvac") as mock_hvac:
    mock_client = MagicMock()
    mock_hvac.Client.return_value = mock_client
    mock_client.is_authenticated.return_value = True
    mock_client.secrets.transit.list_keys.return_value = {
        "data": {"keys": {"my-rsa-key": {}}}
    }
    mock_client.secrets.transit.read_key.return_value = {
        "data": {"type": "rsa-2048", "exportable": False, "latest_version": 1}
    }
    result = scan_vault_targets("http://localhost:8200", token="root")
    assert len(result) == 1
    assert result[0].cert_pubkey_alg == "RSA"
```

The PKI CA cert parsing needs a real PEM string in tests. Use `cryptography` to generate a test cert in the test fixture — this avoids network calls while testing real PEM parsing:

```python
# Pattern: generate a real (but ephemeral) RSA-2048 cert for PKI tests
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from cryptography.hazmat.primitives import hashes
import datetime

def _make_test_pem_rsa2048():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(...)])
    cert = (x509.CertificateBuilder()
        .subject_name(subject).issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256()))
    return cert.public_bytes(serialization.Encoding.PEM).decode()
```

**What requires a live dev Vault Docker container (chaos lab):**

- End-to-end scan against the `storage` profile Vault instance (port 20009)
- Verifying that the extended vault-seed.sh successfully enables PKI and auth methods
- Confirming the CBOM output contains no spurious VAULT components (Pass 1/2/3 skip lists)
- Confirming `dat_scan_json` is populated and readable from the SQLite DB after a full scan

Chaos lab test file: `tests/test_chaos_vault.py` — follows the pattern of `tests/test_chaos_storage.py`.

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_vault_connector.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_vault_connector.py` — unit tests for all three scanner functions (VAULT-01, VAULT-02, VAULT-03)
- [ ] `tests/test_chaos_vault.py` — integration test against live storage-profile Vault (optional, chaos lab only)
- [ ] No framework install needed — pytest already in use across existing test suite

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Token sourced from env var (VAULT_TOKEN) or config; not hardcoded |
| V3 Session Management | no | Scanner is stateless; no session to manage |
| V4 Access Control | no | Scanner is read-only; Vault policies control what token can read |
| V5 Input Validation | yes | vault_addr validated as non-empty before API call; token presence checked |
| V6 Cryptography | yes — this IS the crypto audit | Never hand-roll Vault API; use hvac |

### Known Threat Patterns for Vault connector

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Token exfiltration via logs | Information Disclosure | Never log token value; log only first 8 chars at DEBUG level if at all |
| SSRF via vault_addr config | Tampering | Validate vault_addr is a well-formed URL; restrict to http/https schemes |
| Vault sealed / unreachable produces crash | Denial of Service | Wrap all calls in except Exception; produce scan_error endpoint instead |
| Scanning with root token (unnecessary privilege) | Elevation of Privilege | Document minimum required Vault policy in config_template.yaml comments |

**Minimum Vault policy for scanner (to document in config template):**
```hcl
path "transit/keys/*" { capabilities = ["list", "read"] }
path "sys/mounts" { capabilities = ["read"] }
path "+/ca" { capabilities = ["read"] }  # PKI CA cert
path "sys/auth" { capabilities = ["read"] }
```

---

## Sources

### Primary (HIGH confidence)
- `/hvac/hvac` (Context7) — transit list_keys, read_key, PKI read_ca_certificate, list_mounted_secrets_engines, list_auth_methods, client initialization, exception hierarchy
- `pyproject.toml` (codebase) — confirmed current [cloud] extras contents and cryptography core dep
- `quirk/scanner/gcp_connector.py` (codebase) — GCP_KMS_ALGORITHM_MAP pattern, import guard, per-resource try/except, scan_error pattern
- `quirk/scanner/db_connector.py` (codebase) — session_start parameter pattern, scan_error CryptoEndpoint, PSYCOPG2_AVAILABLE guard
- `quirk/cbom/classifier.py` (codebase) — confirmed ml-dsa-44/65/87, slh-dsa-128/192/256 entries; confirmed Vault key type names not in classifier (using normalised form)
- `quantum-chaos-enterprise-lab/docker-compose.yml` (codebase) — Vault container at port 20009, storage profile
- `quantum-chaos-enterprise-lab/storage/vault-seed.sh` (codebase) — existing seed: transit keys rsa-2048, rsa-1024, aes256-gcm96, ecdsa-p256
- `quirk/intelligence/evidence.py` (codebase) — current _PROTOCOL_KEYS tuple, dar_ counter pattern
- `quirk/intelligence/scoring.py` (codebase) — confirmed 5-subscore structure, dar_impacts list pattern, SCORE_WEIGHTS dict
- `quirk/cbom/builder.py` (codebase) — confirmed current Pass 1/2/3 skip list state for "S3", "AZURE_BLOB"
- `tests/test_intelligence_scoring.py` (codebase) — MAX_SUBSCORE=25, NUM_SUBSCORES=5 constraint
- `pip index versions hvac` (verified) — hvac 2.4.0 is current latest

### Secondary (MEDIUM confidence)
- hvac README / Context7 docs — VAULT_TOKEN env var handling (confirmed: hvac requires explicit token assignment, env var is user responsibility)

### Tertiary (LOW confidence)
- Auth method risk tier assignments (AUTH_RISK_MAP) are based on Vault security best-practices knowledge; no authoritative NIST/CIS scoring verified in this session [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — hvac 2.4.0 verified via pip, all API calls verified via Context7
- Architecture: HIGH — patterns directly derived from Phase 27/28 codebase analogs
- Pitfalls: HIGH — most derived from codebase inspection and verified API docs; P3 (auth risk tiers) is MEDIUM

**Research date:** 2026-04-26
**Valid until:** 2026-05-26 (hvac is stable; Vault API changes slowly)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VAULT-01 | Transit engine key type enumeration with quantum-safety classification (ml-dsa/slh-dsa as positive PQC findings) | VAULT_TRANSIT_KEY_MAP covers all standard and PQC key types; alg_name values match classifier.py entries; `client.secrets.transit.list_keys()` + `read_key()` API verified |
| VAULT-02 | PKI mount CA cert algorithm detection — RSA<4096 or SHA-1 = HIGH finding | `client.sys.list_mounted_secrets_engines()` + `client.secrets.pki.read_ca_certificate()` + `cryptography.x509` parsing; cryptography is already a core dep |
| VAULT-03 | Active auth method list with HIGH for token/LDAP, MEDIUM for userpass/radius; token sourced from VAULT_TOKEN env var or config | `client.sys.list_auth_methods()` API verified; AUTH_RISK_MAP defined; token resolution via explicit arg → VAULT_TOKEN env fallback |
</phase_requirements>
