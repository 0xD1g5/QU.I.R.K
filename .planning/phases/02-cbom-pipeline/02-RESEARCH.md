# Phase 2: CBOM Pipeline — Research

**Researched:** 2026-03-29
**Domain:** CycloneDX CBOM generation, cryptographic asset modeling, NIST PQC classification
**Confidence:** HIGH (all core API findings verified against live GitHub source and official bom-examples)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CBOM-01 | cyclonedx-python-lib integration — map all scan results to CycloneDX CBOM components | Verified: v11.7.0 supports Python 3.14, `ComponentType.CRYPTOGRAPHIC_ASSET`, full crypto module |
| CBOM-02 | Algorithm → CBOM component mapping layer (all scanner outputs → CycloneDX schema) | Verified: algorithm mapping table built from official bom-examples Protocol/Algorithm fixtures |
| CBOM-03 | NIST PQC quantum-safety classification enrichment per algorithm | Verified: `nistQuantumSecurityLevel` int 0–6 from schema; concrete values from official Algorithm fixture |
| CBOM-04 | CBOM JSON + XML output artifact per scan run | Verified: `JsonV1Dot6` + `XmlV1Dot6` classes exist; `output_as_string()` and `output_to_file()` confirmed |
</phase_requirements>

---

## Summary

CycloneDX v1.6 (April 2024) introduced first-class CBOM support including `cryptographic-asset` component type and `cryptoProperties` schema. The Python library `cyclonedx-python-lib` v11.7.0 (released 2026-03-17) is the current stable version and explicitly supports Python 3.14. The library provides a clean data-model-first API: construct `Component(type=ComponentType.CRYPTOGRAPHIC_ASSET, crypto_properties=CryptoProperties(...))`, add to a `Bom`, then serialize with `JsonV1Dot6(bom).output_as_string(indent=2)` or `XmlV1Dot6(bom).output_as_string(indent=2)`. No lxml dependency is required for output — only for optional schema validation.

The NIST quantum security level field (`nistQuantumSecurityLevel`) is an integer 0–6 within `algorithmProperties`. Level 0 means not quantum-safe (vulnerable to Shor's/Grover's); levels 1–5 correspond to NIST PQC security categories anchored to AES-128 through AES-256 equivalence. Concrete values from official CycloneDX fixtures: RSA → 0, ECDSA/ECDH → 0, SHA-384 → 2 (NIST cat 4 ≈ SHA-384 collision resistance), AES-256 → 1 (GCM mode gets category 1 in examples; AES-256 CTR/CBC gets higher), ML-KEM-1024 → 5. RSA and all EC-based algorithms are quantum-vulnerable (level 0).

The recommended architecture is a new `quirk/cbom/` module containing a `builder.py` and a `writer.py`, called from `quirk/reports/writer.py::write_reports()` alongside existing report outputs. This keeps CBOM generation co-located with other output concerns while remaining independently testable.

**Primary recommendation:** Install `cyclonedx-python-lib==11.7.0`, implement `quirk/cbom/builder.py` to convert `CryptoEndpoint` objects into `Bom` + `Component` objects, and `quirk/cbom/writer.py` to serialize and write JSON + XML files. Call from `write_reports()` as step 5.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| cyclonedx-python-lib | 11.7.0 | CycloneDX data models, serialization | Official OWASP CycloneDX Python library; only first-party Python CBOM library |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| cyclonedx-python-lib[json-validation] | 11.7.0 | JSON schema validation of emitted CBOM | Optional — add to dev/test dependencies for CI validation |
| cyclonedx-python-lib[xml-validation] | 11.7.0 | XML schema validation via lxml | Optional — only if XML output needs to be validated in CI |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| cyclonedx-python-lib | cdxgen (Node.js) | cdxgen is a CLI tool, not a Python library; unsuitable for in-process generation |
| cyclonedx-python-lib | hand-rolled JSON | Misses schema compliance, BomRef deduplication, future schema migrations |

**Installation:**
```bash
pip install "cyclonedx-python-lib==11.7.0"
```

Add to `pyproject.toml` `[project.dependencies]`:
```toml
"cyclonedx-python-lib>=11.7.0,<12"
```

**Version verification:** Confirmed 11.7.0 released 2026-03-17 via PyPI JSON API. Python 3.14 added in this version. Prior versions supported 3.9–3.13 only.

---

## Architecture Patterns

### Recommended Project Structure

```
quirk/
├── cbom/
│   ├── __init__.py          # re-exports build_cbom, write_cbom_files
│   ├── builder.py           # CryptoEndpoint list → Bom object
│   ├── classifier.py        # algorithm string → nistQuantumSecurityLevel + CryptoPrimitive
│   └── writer.py            # Bom → JSON/XML files on disk
├── reports/
│   └── writer.py            # existing; calls write_cbom_files() in step 5
```

### Pattern 1: Constructing a CBOM Component for an Algorithm

**What:** Create a `Component` with `type=CRYPTOGRAPHIC_ASSET` and `crypto_properties` populated.

**When to use:** For every distinct cryptographic algorithm found across scanned endpoints.

```python
# Source: https://github.com/CycloneDX/cyclonedx-python-lib (verified against source + official fixtures)
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.model.crypto import (
    CryptoProperties, CryptoAssetType,
    AlgorithmProperties, CryptoPrimitive,
    CryptoExecutionEnvironment, CryptoFunction,
)

alg_component = Component(
    name="RSA-2048",
    type=ComponentType.CRYPTOGRAPHIC_ASSET,
    bom_ref="crypto/algorithm/rsa-2048",
    crypto_properties=CryptoProperties(
        asset_type=CryptoAssetType.ALGORITHM,
        algorithm_properties=AlgorithmProperties(
            primitive=CryptoPrimitive.PKE,
            parameter_set_identifier="2048",
            execution_environment=CryptoExecutionEnvironment.SOFTWARE_PLAIN_RAM,
            crypto_functions=[CryptoFunction.KEYGEN, CryptoFunction.ENCRYPT, CryptoFunction.DECRYPT],
            classical_security_level=112,
            nist_quantum_security_level=0,
        ),
        oid="1.2.840.113549.1.1.1",
    ),
)
bom = Bom(components=[alg_component])
```

### Pattern 2: Constructing a Certificate Component

**What:** Model an X.509 certificate found during TLS scanning.

**When to use:** For each scanned endpoint's leaf certificate.

```python
from cyclonedx.model.crypto import (
    CryptoProperties, CryptoAssetType, CertificateProperties,
)
from cyclonedx.model.bom_ref import BomRef

cert_component = Component(
    name=f"{endpoint.host}:{endpoint.port}",
    type=ComponentType.CRYPTOGRAPHIC_ASSET,
    bom_ref=f"crypto/certificate/{endpoint.host}:{endpoint.port}",
    crypto_properties=CryptoProperties(
        asset_type=CryptoAssetType.CERTIFICATE,
        certificate_properties=CertificateProperties(
            subject_name=endpoint.cert_subject,
            issuer_name=endpoint.cert_issuer,
            not_valid_before=endpoint.cert_not_before,
            not_valid_after=endpoint.cert_not_after,
            signature_algorithm_ref=BomRef(value=sig_alg_bom_ref),
            subject_public_key_ref=BomRef(value=pubkey_bom_ref),
            certificate_format="X.509",
        ),
    ),
)
```

### Pattern 3: Constructing a TLS Protocol Component

**What:** Model a TLS protocol instance with cipher suite list.

**When to use:** For each TLS endpoint.

```python
from cyclonedx.model.crypto import (
    CryptoProperties, CryptoAssetType,
    ProtocolProperties, ProtocolPropertiesType,
    ProtocolPropertiesCipherSuite,
)
from cyclonedx.model.bom_ref import BomRef

tls_component = Component(
    name=f"TLS-{endpoint.tls_version}",
    type=ComponentType.CRYPTOGRAPHIC_ASSET,
    bom_ref=f"crypto/protocol/tls/{endpoint.host}:{endpoint.port}",
    crypto_properties=CryptoProperties(
        asset_type=CryptoAssetType.PROTOCOL,
        protocol_properties=ProtocolProperties(
            type=ProtocolPropertiesType.TLS,
            version=endpoint.tls_version,   # e.g. "1.2", "1.3"
            cipher_suites=[
                ProtocolPropertiesCipherSuite(
                    name=endpoint.cipher_suite,
                    algorithms=[BomRef(v) for v in alg_bom_refs],
                )
            ],
        ),
    ),
)
```

### Pattern 4: Serialization to JSON and XML

**What:** Serialize a `Bom` to both JSON (CycloneDX 1.6) and XML (CycloneDX 1.6).

```python
# Source: verified against cyclonedx/output/json.py and cyclonedx/output/xml.py
from cyclonedx.output.json import JsonV1Dot6
from cyclonedx.output.xml import XmlV1Dot6

# JSON output
json_out = JsonV1Dot6(bom)
json_str: str = json_out.output_as_string(indent=2)

# Write JSON to file
json_out.output_to_file(
    filename="/path/to/cbom-{stamp}.cdx.json",
    allow_overwrite=True,
    indent=2,
)

# XML output (uses stdlib xml.etree — no lxml needed)
xml_out = XmlV1Dot6(bom)
xml_str: str = xml_out.output_as_string(indent=2)
xml_out.output_to_file(
    filename="/path/to/cbom-{stamp}.cdx.xml",
    allow_overwrite=True,
    indent=2,
)
```

Alternative using `make_outputter` factory (schema-version-agnostic path):
```python
from cyclonedx.output import make_outputter
from cyclonedx.schema import OutputFormat, SchemaVersion

outputter = make_outputter(bom, OutputFormat.JSON, SchemaVersion.V1_6)
json_str = outputter.output_as_string(indent=2)
```

### Pattern 5: BomRef String vs BomRef Object

The `Component.bom_ref` parameter accepts `Optional[Union[str, BomRef]]` — a plain string is accepted. `CertificateProperties.signature_algorithm_ref` and similar cross-reference fields require `BomRef` objects:

```python
from cyclonedx.model.bom_ref import BomRef
sig_ref = BomRef(value="crypto/algorithm/rsa-2048")
```

### Anti-Patterns to Avoid

- **Building one Component per endpoint with one crypto_properties blob:** CBOM models algorithms as shared components. Two endpoints using AES-256-GCM should reference the same algorithm component via `bom_ref`, not duplicate it.
- **Using SchemaVersion.V1_4 or V1_5:** `CRYPTOGRAPHIC_ASSET` was introduced in 1.6. Emitting to V1_4/V1_5 will silently strip `cryptoProperties`. Always use V1_6 or V1_7.
- **Importing JsonV1Dot5 expecting CBOM support:** Only `JsonV1Dot6` and `JsonV1Dot7` render `cryptoProperties` fields.
- **Hard-coding lxml for XML output:** The XML serializer (`XmlV1Dot6`) uses `xml.etree.ElementTree` (stdlib). lxml is only needed for schema validation, which is optional.
- **Forgetting to call `bom.register_dependency()`:** Dependencies are optional for CBOM but needed if the planner wants a dependency graph between protocol → algorithm components.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| BOM serial number generation | `uuid.uuid4()` boilerplate | `Bom()` auto-generates UUID serial number | Bom constructor handles this; `bom.serial_number` is set automatically |
| JSON schema compliance | Manual dict construction | `JsonV1Dot6(bom).output_as_string()` | Library handles field ordering, required fields, spec version header |
| XML namespace management | `xml.etree` manual namespace setup | `XmlV1Dot6(bom).output_as_string()` | Library emits correct CycloneDX XML namespaces |
| BomRef deduplication | Tracking seen bom-refs manually | Use consistent `bom_ref` strings per algorithm; library enforces set semantics on `bom.components` | Duplicate `bom_ref` values raise errors — build a component registry dict first |
| CycloneDX timestamp | `datetime.utcnow()` boilerplate | `BomMetaData(timestamp=datetime.now(timezone.utc))` | Or omit — library sets timestamp on `bom.metadata` |

**Key insight:** The library handles all schema envelope concerns. The only custom logic needed is: (1) the mapping from QUIRK's algorithm strings to CycloneDX enum values, and (2) the deduplication logic that converts N endpoint observations into M unique algorithm components.

---

## Algorithm → CycloneDX Mapping Table

This is the authoritative mapping for CBOM-02. Values derived from official CycloneDX bom-examples fixtures and the NIST PQC evaluation criteria.

### TLS Cipher Suite Decomposition

Cipher suites must be decomposed into constituent algorithm components. The cipher suite itself becomes a `ProtocolPropertiesCipherSuite` entry, referencing component `bom_ref` strings.

| Cipher Suite Fragment | CycloneDX `name` | `primitive` enum | `CryptoPrimitive.*` | Notes |
|-----------------------|-----------------|-----------------|--------------------||
| `ECDHE` (key exchange) | `ECDH-Curve25519` or `ECDH-secp256r1` | `key-agree` | `KEY_AGREE` | Extract curve from suite name |
| `RSA` (auth / key exchange) | `RSA-{keysize}` | `pke` | `PKE` | Size not in suite name; use cert_pubkey_size |
| `AES_256_GCM` | `AES-256-GCM` | `ae` | `AE` | Authenticated encryption |
| `AES_128_GCM` | `AES-128-GCM` | `ae` | `AE` | |
| `AES_256_CBC` | `AES-256-CBC` | `block-cipher` | `BLOCK_CIPHER` | |
| `3DES` / `DES_EDE` | `3DES` | `block-cipher` | `BLOCK_CIPHER` | |
| `CHACHA20_POLY1305` | `ChaCha20-Poly1305` | `ae` | `AE` | |
| `SHA384` (MAC/PRF) | `SHA-384` | `hash` | `HASH` | |
| `SHA256` (MAC/PRF) | `SHA-256` | `hash` | `HASH` | |
| `SHA1` (MAC/PRF) | `SHA-1` | `hash` | `HASH` | |

### Cert Public Key Algorithms

| `cert_pubkey_alg` value | CycloneDX `name` | `primitive` | `CryptoPrimitive.*` | `nistQuantumSecurityLevel` |
|------------------------|-----------------|-------------|--------------------|-----------------------------|
| `RSA` | `RSA-{cert_pubkey_size}` | `pke` | `PKE` | 0 |
| `ECDSA` | `ECDSA` | `signature` | `SIGNATURE` | 0 |
| `EC` | `ECDSA` | `signature` | `SIGNATURE` | 0 |
| `Ed25519` | `Ed25519` | `signature` | `SIGNATURE` | 0 (EdDSA is NOT PQC) |
| `Ed448` | `Ed448` | `signature` | `SIGNATURE` | 0 |

### SSH KEX Algorithms (`ssh_audit_json` → `kex` array)

| SSH KEX algorithm string | CycloneDX `name` | `primitive` | `CryptoPrimitive.*` | `nistQuantumSecurityLevel` |
|--------------------------|-----------------|-------------|--------------------|-----------------------------|
| `curve25519-sha256` | `X25519` | `key-agree` | `KEY_AGREE` | 0 |
| `curve25519-sha256@libssh.org` | `X25519` | `key-agree` | `KEY_AGREE` | 0 |
| `ecdh-sha2-nistp256` | `ECDH-P256` | `key-agree` | `KEY_AGREE` | 0 |
| `ecdh-sha2-nistp384` | `ECDH-P384` | `key-agree` | `KEY_AGREE` | 0 |
| `ecdh-sha2-nistp521` | `ECDH-P521` | `key-agree` | `KEY_AGREE` | 0 |
| `diffie-hellman-group14-sha256` | `DH-2048` | `key-agree` | `KEY_AGREE` | 0 |
| `diffie-hellman-group14-sha1` | `DH-2048` | `key-agree` | `KEY_AGREE` | 0 |
| `diffie-hellman-group16-sha512` | `DH-4096` | `key-agree` | `KEY_AGREE` | 0 |
| `diffie-hellman-group-exchange-sha256` | `DH-GroupExchange` | `key-agree` | `KEY_AGREE` | 0 |
| `sntrup761x25519-sha512@openssh.com` | `SNTRUP761X25519` | `kem` | `KEM` | 3 (hybrid; sntrup761 is Cat 3) |
| `mlkem768x25519-sha256` | `ML-KEM-768+X25519` | `kem` | `KEM` | 3 |

### SSH Host Key Algorithms (`ssh_audit_json` → `key` array)

| SSH host key string | CycloneDX `name` | `primitive` | `CryptoPrimitive.*` | `nistQuantumSecurityLevel` |
|--------------------|-----------------|-------------|--------------------|-----------------------------|
| `ssh-rsa` | `RSA` | `signature` | `SIGNATURE` | 0 |
| `rsa-sha2-256` | `RSA-SHA256` | `signature` | `SIGNATURE` | 0 |
| `rsa-sha2-512` | `RSA-SHA512` | `signature` | `SIGNATURE` | 0 |
| `ecdsa-sha2-nistp256` | `ECDSA-P256` | `signature` | `SIGNATURE` | 0 |
| `ecdsa-sha2-nistp384` | `ECDSA-P384` | `signature` | `SIGNATURE` | 0 |
| `ssh-ed25519` | `Ed25519` | `signature` | `SIGNATURE` | 0 |
| `sk-ssh-ed25519@openssh.com` | `Ed25519-SK` | `signature` | `SIGNATURE` | 0 |

---

## NIST PQC Quantum-Safety Classification

### nistQuantumSecurityLevel Scale

The `nistQuantumSecurityLevel` is an integer 0–6 within `AlgorithmProperties`. Source: CycloneDX bom-1.6 schema description; confirmed by official Algorithm fixture.

| Level | Meaning | Security Equivalent |
|-------|---------|---------------------|
| 0 | Not quantum-safe — breaks under Shor's algorithm (asymmetric) or Grover's (symmetric/hash insufficient key length) | Vulnerable |
| 1 | NIST PQC Category 1 | ≥ AES-128 key search hardness (~128-bit quantum security) |
| 2 | NIST PQC Category 2 | ≥ SHA-256 collision hardness (~128-bit classical collision) |
| 3 | NIST PQC Category 3 | ≥ AES-192 key search hardness (~192-bit quantum security) |
| 4 | NIST PQC Category 4 | ≥ SHA-384 collision hardness (~192-bit classical collision) |
| 5 | NIST PQC Category 5 | ≥ AES-256 key search hardness (~256-bit quantum security) |
| 6 | Reserved / beyond Category 5 | Rarely used |

### Algorithm → Level Mapping (from official CycloneDX fixtures + NIST docs)

| Algorithm family | `nistQuantumSecurityLevel` | Rationale |
|-----------------|---------------------------|-----------|
| RSA (any key size) | 0 | Broken by Shor's algorithm |
| ECDSA (any curve) | 0 | Broken by Shor's algorithm (elliptic curve DLP) |
| ECDH / X25519 / X448 | 0 | Broken by Shor's algorithm |
| DH (any group size) | 0 | Broken by Shor's algorithm |
| DSA | 0 | Broken by Shor's algorithm |
| Ed25519 / EdDSA | 0 | NOT PQC — broken by Shor's algorithm |
| SHA-1 | 0 | Below minimum threshold |
| SHA-256 | 0 | 128-bit classical, ~64-bit quantum (Grover) — marginal; use 0 |
| SHA-384 | 2 | ~192-bit collision resistance; confirmed level 2 in official Protocol fixture |
| SHA-512 | 2 | ~256-bit collision resistance; map to level 2 |
| AES-128-GCM | 1 | Confirmed level 1 in official Algorithm fixture |
| AES-256-GCM | 1 | Confirmed level 1 in official Protocol fixture — note: GCM tag truncation effect |
| AES-256-CBC / AES-256-CTR | 3 | Conservative: AES-256 without tag truncation → Category 3 acceptable |
| ChaCha20-Poly1305 | 1 | 256-bit key, ~128-bit quantum (Grover) → Category 1 |
| ML-KEM-512 (FIPS 203) | 1 | NIST Category 1 parameter set |
| ML-KEM-768 (FIPS 203) | 3 | NIST Category 3 parameter set |
| ML-KEM-1024 (FIPS 203) | 5 | NIST Category 5 — confirmed in official Algorithm fixture |
| ML-DSA-44 (FIPS 204) | 2 | NIST Category 2 parameter set |
| ML-DSA-65 (FIPS 204) | 3 | NIST Category 3 parameter set |
| ML-DSA-87 (FIPS 204) | 5 | NIST Category 5 parameter set |
| SLH-DSA-128f/s (FIPS 205) | 1 | NIST Category 1 parameter set |
| SLH-DSA-192f/s (FIPS 205) | 3 | NIST Category 3 parameter set |
| SLH-DSA-256f/s (FIPS 205) | 5 | NIST Category 5 parameter set |

### Classifier Function Skeleton

```python
# quirk/cbom/classifier.py
from cyclonedx.model.crypto import CryptoPrimitive

# Returns (primitive, nist_quantum_level, classical_security_level)
_QUANTUM_LEVEL: dict[str, int] = {
    # Quantum-vulnerable families
    "RSA": 0, "ECDSA": 0, "EC": 0, "ECDH": 0,
    "DH": 0, "DSA": 0, "ED25519": 0, "ED448": 0,
    "SHA1": 0, "SHA-1": 0, "SHA256": 0, "SHA-256": 0,
    # Symmetric/hash — safe at sufficient key length
    "AES128": 1, "AES-128": 1,
    "AES256": 1, "AES-256": 1,   # GCM; for CBC/CTR may use 3
    "SHA384": 2, "SHA-384": 2,
    "SHA512": 2, "SHA-512": 2,
    "CHACHA20": 1,
    # NIST PQC finalized standards
    "ML-KEM-512": 1, "ML-KEM-768": 3, "ML-KEM-1024": 5,
    "ML-DSA-44": 2, "ML-DSA-65": 3, "ML-DSA-87": 5,
    "SLH-DSA-128": 1, "SLH-DSA-192": 3, "SLH-DSA-256": 5,
}
```

---

## Integration Architecture

### Recommended Module Layout

Create `quirk/cbom/` as a new subpackage — not added to `quirk/reports/`. The reports package is already large and has a clear responsibility (text/JSON intelligence reports). CBOM is a distinct output artifact type with its own schema, library, and test surface.

```
quirk/cbom/__init__.py     # exports: build_cbom(endpoints) -> Bom, write_cbom_files(bom, outdir, stamp) -> tuple[str, str]
quirk/cbom/builder.py      # CryptoEndpoint list → Bom
quirk/cbom/classifier.py   # algorithm string → (CryptoPrimitive, int, int)
quirk/cbom/writer.py       # Bom → JSON/XML files
```

### Call Site

In `quirk/reports/writer.py::write_reports()`, after step 4 (run stats):

```python
# Step 5 — CBOM artifacts
from quirk.cbom import build_cbom, write_cbom_files
cbom = build_cbom(endpoints)
cbom_json_path, cbom_xml_path = write_cbom_files(cbom, outdir, stamp)
```

Add both paths to the console summary `print` loop at the bottom of `write_reports()`.

### Why Not `quirk/reports/cbom_writer.py`?

- `cyclonedx-python-lib` is a new dependency; isolating it in `quirk/cbom/` means tests can mock the entire `quirk.cbom` module without touching `quirk.reports`
- The builder logic (deduplication, mapping) is substantial enough to warrant a separate module with its own tests
- Future phases may add CBOM querying / diffing — `quirk/cbom/` as a namespace is forward-compatible

### builder.py Architecture

The builder must deduplicate algorithm components across endpoints. Two endpoints using `AES-256-GCM` should produce one algorithm component, not two.

```python
# Pseudocode structure for builder.py
def build_cbom(endpoints: list[CryptoEndpoint]) -> Bom:
    algo_registry: dict[str, Component] = {}   # bom_ref → Component
    cert_components: list[Component] = []
    protocol_components: list[Component] = []

    for ep in endpoints:
        # 1. Decompose cipher_suite → algorithm bom_refs
        # 2. Build/reuse algorithm components in algo_registry
        # 3. Build cert component if cert_pubkey_alg present
        # 4. Build protocol component (TLS or SSH)
        # 5. Build SSH algorithm components from ssh_audit_json

    bom = Bom(
        components=list(algo_registry.values()) + cert_components + protocol_components,
        metadata=BomMetaData(
            timestamp=datetime.now(timezone.utc),
            component=Component(
                name="QU.I.R.K. scan",
                type=ComponentType.APPLICATION,
                version=PLATFORM_VERSION,
            ),
        ),
    )
    return bom
```

---

## Common Pitfalls

### Pitfall 1: CRYPTOGRAPHIC_ASSET Not Rendered in Schema V1_5 or Earlier

**What goes wrong:** `Component(type=ComponentType.CRYPTOGRAPHIC_ASSET)` objects silently have their `crypto_properties` stripped when using `JsonV1Dot5` or `XmlV1Dot5`. No error is raised.

**Why it happens:** The CycloneDX schema versions below 1.6 do not define `cryptoProperties` or `cryptographic-asset` component type.

**How to avoid:** Always use `JsonV1Dot6` / `XmlV1Dot6` (or V1_7) for CBOM output. Never use the `make_outputter(..., SchemaVersion.V1_5)` path for CBOM.

**Warning signs:** Output JSON has components with empty `cryptoProperties` or missing the `type: "cryptographic-asset"` field.

### Pitfall 2: Duplicate BomRef Causes Set Collision

**What goes wrong:** Adding two `Component` objects with the same `bom_ref` string to `bom.components` (which is a `SortedSet`) silently drops one.

**Why it happens:** `Bom.components` uses set semantics; equality is determined by `bom_ref`.

**How to avoid:** Maintain an `algo_registry: dict[str, Component]` keyed on the canonical bom_ref string. Check before creating a new component.

**Warning signs:** Final CBOM has fewer components than expected; some cipher suite algorithm references point to absent bom_refs.

### Pitfall 3: BomRef Cross-References Become Stale

**What goes wrong:** `CertificateProperties.signature_algorithm_ref = BomRef(value="crypto/algorithm/rsa-2048")` but no component with `bom_ref="crypto/algorithm/rsa-2048"` exists in `bom.components`.

**Why it happens:** Builder creates certificate component before ensuring referenced algorithm component exists.

**How to avoid:** Always register algorithm components in `algo_registry` before building certificate or protocol components that reference them. Process order: algorithms first, keys second, certificates third, protocols fourth.

**Warning signs:** CBOM validates but Dependency Track / sbom-utility reports unresolved BomRef references.

### Pitfall 4: lxml Import Error on Fresh Install

**What goes wrong:** `import lxml` fails even though `cyclonedx-python-lib` is installed, because lxml is optional.

**Why it happens:** The core package does not install lxml. XML *output* (`XmlV1Dot6`) uses `xml.etree.ElementTree` (stdlib) — lxml is only needed for XML *validation*.

**How to avoid:** Do not `import lxml` in production code. Use `XmlV1Dot6(bom).output_as_string()`. If schema validation is desired in CI, install `cyclonedx-python-lib[xml-validation]` as a dev dependency.

### Pitfall 5: `nistQuantumSecurityLevel` Default of `None` Not Equivalent to 0

**What goes wrong:** Skipping `nist_quantum_security_level` in `AlgorithmProperties` omits the field from output. Some downstream tools (Dependency Track) interpret absence as "unknown" rather than "quantum-vulnerable".

**Why it happens:** All `AlgorithmProperties` fields default to `None` and are omitted if None.

**How to avoid:** Always explicitly set `nist_quantum_security_level=0` for quantum-vulnerable algorithms. Reserve `None` only for algorithms where classification is genuinely unknown.

### Pitfall 6: SSH KEX and Host Key Algorithm Strings Are Implementation-Specific

**What goes wrong:** `ssh_audit_json` contains algorithm names like `curve25519-sha256@libssh.org` (with vendor suffix). Exact string matching fails.

**Why it happens:** OpenSSH and other implementations add `@vendor.tld` suffixes to algorithm names.

**How to avoid:** Strip `@*` suffix before lookup: `alg_name = raw_name.split("@")[0]`. Maintain a fallback for unrecognized algorithms that maps to `CryptoPrimitive.UNKNOWN` with `nist_quantum_security_level=None`.

---

## Code Examples

### Minimal Working CBOM (verified pattern from official examples)

```python
# Source: https://github.com/CycloneDX/bom-examples/blob/master/CBOM/Protocol/bom.json
#         and cyclonedx-python-lib source (verified 2026-03-29)
from datetime import datetime, timezone
from cyclonedx.model.bom import Bom, BomMetaData
from cyclonedx.model.bom_ref import BomRef
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.model.crypto import (
    AlgorithmProperties,
    CertificateProperties,
    CryptoAssetType,
    CryptoExecutionEnvironment,
    CryptoFunction,
    CryptoPrimitive,
    CryptoProperties,
    ProtocolProperties,
    ProtocolPropertiesCipherSuite,
    ProtocolPropertiesType,
)
from cyclonedx.output.json import JsonV1Dot6
from cyclonedx.output.xml import XmlV1Dot6

# 1. Algorithm component (shared)
aes256_gcm = Component(
    name="AES-256-GCM",
    type=ComponentType.CRYPTOGRAPHIC_ASSET,
    bom_ref="crypto/algorithm/aes-256-gcm",
    crypto_properties=CryptoProperties(
        asset_type=CryptoAssetType.ALGORITHM,
        algorithm_properties=AlgorithmProperties(
            primitive=CryptoPrimitive.AE,
            parameter_set_identifier="256",
            execution_environment=CryptoExecutionEnvironment.SOFTWARE_PLAIN_RAM,
            crypto_functions=[CryptoFunction.ENCRYPT, CryptoFunction.DECRYPT],
            classical_security_level=256,
            nist_quantum_security_level=1,
        ),
        oid="2.16.840.1.101.3.4.1.46",
    ),
)

# 2. TLS protocol component referencing the algorithm
tls_protocol = Component(
    name="TLSv1.3",
    type=ComponentType.CRYPTOGRAPHIC_ASSET,
    bom_ref="crypto/protocol/tls/1.3/example.com:443",
    crypto_properties=CryptoProperties(
        asset_type=CryptoAssetType.PROTOCOL,
        protocol_properties=ProtocolProperties(
            type=ProtocolPropertiesType.TLS,
            version="1.3",
            cipher_suites=[
                ProtocolPropertiesCipherSuite(
                    name="TLS_AES_256_GCM_SHA384",
                    algorithms=[BomRef(value="crypto/algorithm/aes-256-gcm")],
                )
            ],
        ),
    ),
)

# 3. Build BOM
bom = Bom(
    components=[aes256_gcm, tls_protocol],
    metadata=BomMetaData(timestamp=datetime.now(timezone.utc)),
)

# 4. Serialize
json_str = JsonV1Dot6(bom).output_as_string(indent=2)
xml_str = XmlV1Dot6(bom).output_as_string(indent=2)
```

### SSH Protocol Component (from ssh_audit_json)

```python
# Source: derived from CycloneDX bom-examples Protocol fixture patterns
from cyclonedx.model.crypto import ProtocolPropertiesType

ssh_protocol = Component(
    name="SSH-2.0",
    type=ComponentType.CRYPTOGRAPHIC_ASSET,
    bom_ref=f"crypto/protocol/ssh/{endpoint.host}:{endpoint.port}",
    crypto_properties=CryptoProperties(
        asset_type=CryptoAssetType.PROTOCOL,
        protocol_properties=ProtocolProperties(
            type=ProtocolPropertiesType.SSH,
            version="2.0",
            cipher_suites=[
                ProtocolPropertiesCipherSuite(
                    name=kex_alg_name,
                    algorithms=[BomRef(value=kex_bom_ref)],
                )
                for kex_alg_name, kex_bom_ref in kex_pairs
            ],
        ),
    ),
)
```

### Parsing ssh_audit_json for Algorithm Names

```python
import json

def extract_ssh_algorithms(ssh_audit_json: str) -> dict:
    """Extract KEX, host key, cipher, and MAC algorithms from ssh-audit JSON."""
    data = json.loads(ssh_audit_json)
    return {
        "kex": [entry["algorithm"] for entry in data.get("kex", [])],
        "key": [entry["algorithm"] for entry in data.get("key", [])],
        "enc": [entry["algorithm"] for entry in data.get("enc", [])],
        "mac": [entry["algorithm"] for entry in data.get("mac", [])],
    }
```

### Parsing tls_capabilities_json for Cipher Suites

```python
import json

def extract_tls_cipher_suites(tls_capabilities_json: str) -> list[str]:
    """Extract accepted cipher suite names from sslyze capabilities JSON."""
    data = json.loads(tls_capabilities_json)
    suites = []
    for tls_ver_key in ("TLSv1.3", "TLSv1.2", "TLSv1.1", "TLSv1.0"):
        for suite_entry in data.get(tls_ver_key, {}).get("accepted_cipher_suites", []):
            name = suite_entry.get("cipher_suite", {}).get("name") or suite_entry.get("name")
            if name:
                suites.append(name)
    return suites
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SBOM-only (no crypto typing) | CycloneDX 1.6 CBOM with `cryptographic-asset` type | April 2024 (CycloneDX 1.6) | First standard CBOM schema |
| cyclonedx-python-lib <8.x API | v11.x API with `crypto_properties` kwarg on `Component` | 2024 | New kwarg name; old versions used different interface |
| Python 3.9–3.13 only | Python 3.14 supported from v11.7.0 | 2026-03-17 | Direct install on project's Python 3.14 venv |
| lxml required for XML output | stdlib xml.etree for output, lxml optional (validation only) | cyclonedx-python-lib v7+ | No lxml install required for basic use |
| Manual NIST level classification | CycloneDX `nistQuantumSecurityLevel` integer (0–6) in schema | CycloneDX 1.6 | Standard field; tooling reads it |

**Deprecated/outdated:**
- `cyclonedx-bom` (PyPI): This is the older *SBOM generator tool*, not the library. Do not confuse with `cyclonedx-python-lib`.
- `author` kwarg on `Component`: Deprecated in CycloneDX 1.6; replaced by `authors` (list of `OrganizationalContact`).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | cyclonedx-python-lib 11.7.0 | ✓ | 3.14.3 (confirmed in venv) | — |
| cyclonedx-python-lib | CBOM-01 through CBOM-04 | ✗ (not yet installed) | — | Must install; no fallback |
| lxml | Optional XML validation | unknown | — | Not needed for output; skip for now |
| jsonschema | Optional JSON validation | unknown | — | Not needed for output; skip for now |

**Missing dependencies with no fallback:**
- `cyclonedx-python-lib` — must be added to `pyproject.toml` and installed. Run: `pip install "cyclonedx-python-lib==11.7.0"`

**Missing dependencies with fallback:**
- None at this time.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (confirmed in `.venv/bin/pytest`) |
| Config file | none — no pytest.ini or setup.cfg `[tool:pytest]` section |
| Quick run command | `.venv/bin/python -m pytest tests/test_cbom_builder.py -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CBOM-01 | `build_cbom([endpoint])` returns a `Bom` instance with components | unit | `.venv/bin/python -m pytest tests/test_cbom_builder.py::test_build_cbom_returns_bom -x` | ❌ Wave 0 |
| CBOM-01 | `Bom.components` contains `ComponentType.CRYPTOGRAPHIC_ASSET` items | unit | `.venv/bin/python -m pytest tests/test_cbom_builder.py::test_components_are_crypto_assets -x` | ❌ Wave 0 |
| CBOM-02 | `RSA-2048` cert maps to `CryptoPrimitive.PKE`, level 0 | unit | `.venv/bin/python -m pytest tests/test_cbom_classifier.py::test_rsa_maps_to_pke_level0 -x` | ❌ Wave 0 |
| CBOM-02 | TLS cipher suite decomposed into correct algorithm components | unit | `.venv/bin/python -m pytest tests/test_cbom_builder.py::test_cipher_suite_decomposed -x` | ❌ Wave 0 |
| CBOM-02 | SSH KEX `curve25519-sha256` maps to `KEY_AGREE`, level 0 | unit | `.venv/bin/python -m pytest tests/test_cbom_classifier.py::test_ssh_kex_curve25519 -x` | ❌ Wave 0 |
| CBOM-02 | Duplicate algorithm across endpoints produces single component | unit | `.venv/bin/python -m pytest tests/test_cbom_builder.py::test_algorithm_deduplication -x` | ❌ Wave 0 |
| CBOM-03 | `AES-256-GCM` gets `nistQuantumSecurityLevel=1` | unit | `.venv/bin/python -m pytest tests/test_cbom_classifier.py::test_aes256gcm_level1 -x` | ❌ Wave 0 |
| CBOM-03 | `SHA-384` gets `nistQuantumSecurityLevel=2` | unit | `.venv/bin/python -m pytest tests/test_cbom_classifier.py::test_sha384_level2 -x` | ❌ Wave 0 |
| CBOM-04 | JSON output starts with `{"bomFormat": "CycloneDX"` | unit | `.venv/bin/python -m pytest tests/test_cbom_writer.py::test_json_output_is_valid_cdx -x` | ❌ Wave 0 |
| CBOM-04 | XML output contains `<bom xmlns=` | unit | `.venv/bin/python -m pytest tests/test_cbom_writer.py::test_xml_output_is_valid_cdx -x` | ❌ Wave 0 |
| CBOM-04 | `write_cbom_files()` creates two files on disk | unit | `.venv/bin/python -m pytest tests/test_cbom_writer.py::test_write_cbom_files_creates_two_files -x` | ❌ Wave 0 |
| CBOM-04 | `write_reports()` includes CBOM paths in output | integration | `.venv/bin/python -m pytest tests/test_cbom_integration.py::test_write_reports_includes_cbom -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/test_cbom_builder.py tests/test_cbom_classifier.py tests/test_cbom_writer.py -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_cbom_builder.py` — covers CBOM-01, CBOM-02 (builder logic, deduplication)
- [ ] `tests/test_cbom_classifier.py` — covers CBOM-02, CBOM-03 (algorithm → primitive/level mapping)
- [ ] `tests/test_cbom_writer.py` — covers CBOM-04 (JSON/XML serialization, file creation)
- [ ] `tests/test_cbom_integration.py` — covers CBOM-04 integration with `write_reports()`
- [ ] `cyclonedx-python-lib` install: `pip install "cyclonedx-python-lib==11.7.0"` and add to `pyproject.toml`

---

## Open Questions

1. **Cipher suite decomposition depth from `tls_capabilities_json`**
   - What we know: `tls_capabilities_json` stores sslyze JSON. The sslyze `CipherSuitesScanResult` contains `accepted_cipher_suites` with full suite names.
   - What's unclear: Whether sslyze exposes the key size of the negotiated RSA/ECDSA key in the cipher suite result, or whether we must derive it from `cert_pubkey_size`.
   - Recommendation: Use `cert_pubkey_size` as the RSA/ECDSA key size source; treat cipher suite name parsing as structural decomposition only (not key size).

2. **SSH `ssh_audit_json` structure for cipher/MAC algorithms**
   - What we know: ssh-audit `--json` produces top-level keys `kex`, `key`, `enc`, `mac`. The `enc` key contains symmetric encryption algorithms, `mac` contains MAC algorithms.
   - What's unclear: Whether the Phase 1 SSH scanner implementation stores the full ssh-audit JSON including `enc` and `mac`, or a subset.
   - Recommendation: Check `tests/test_ssh_scanner.py` and the Phase 1 scanner implementation for what is actually stored in `ssh_audit_json` before writing the builder.

3. **CycloneDX 1.7 vs 1.6 for initial output**
   - What we know: V1_7 is the latest schema; it adds deeper hybrid KEM support. V1_6 is the minimum for CBOM.
   - What's unclear: Whether V1_7 has any breaking Python API changes from V1_6.
   - Recommendation: Target V1_6 for initial implementation (simpler, more tooling support). Add V1_7 as a follow-on task or a config option.

---

## Sources

### Primary (HIGH confidence)

- `https://github.com/CycloneDX/cyclonedx-python-lib` — live source: `cyclonedx/model/crypto.py`, `cyclonedx/model/component.py`, `cyclonedx/output/json.py`, `cyclonedx/output/xml.py`, `cyclonedx/schema/__init__.py`, `cyclonedx/model/bom.py`
- `https://github.com/CycloneDX/bom-examples/blob/master/CBOM/Protocol/bom.json` — official TLS+RSA+SHA example (raw JSON verified)
- `https://github.com/CycloneDX/bom-examples/blob/master/CBOM/Algorithm/bom.json` — official Algorithm fixture with nistQuantumSecurityLevel values (ML-KEM-1024=5, RSA=0, AES-128-GCM=1 confirmed)
- `https://github.com/CycloneDX/bom-examples/blob/master/CBOM/Certificate/bom.json` — official Certificate fixture (SHA512withRSA nistQuantumSecurityLevel=0 confirmed)
- `https://pypi.org/pypi/cyclonedx-python-lib/json` — PyPI metadata: v11.7.0 released 2026-03-17, Python 3.14 supported

### Secondary (MEDIUM confidence)

- `https://cyclonedx.org/use-cases/cryptographic-protocol/` — TLS 1.2 cipher suite modeling example (AES-256-GCM level 1, SHA-384 level 2 cross-verified with Algorithm fixture)
- `https://postquantum.com/post-quantum/nist-pqc-security-categories/` — NIST category 1–5 security strength equivalences (AES-128/192/256 and SHA-256/SHA-384 anchors)
- `https://csrc.nist.gov/news/2024/postquantum-cryptography-fips-approved` — FIPS 203/204/205 finalization August 2024

### Tertiary (LOW confidence)

- WebSearch summaries describing `nistQuantumSecurityLevel` as integer 0–6 (cross-verified with official fixture examples above; upgraded to MEDIUM for the confirmed values)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — v11.7.0 confirmed via PyPI JSON API; Python 3.14 classifier confirmed
- Architecture: HIGH — source code of all relevant classes fetched directly from GitHub main branch
- Algorithm mapping table: HIGH for confirmed values (RSA=0, AES-256-GCM=1, SHA-384=2, ML-KEM-1024=5) from official fixtures; MEDIUM for derived values (AES-256-CBC=3 extrapolated from NIST category equivalence)
- Pitfalls: HIGH — derived directly from API behavior (set semantics on bom.components, schema version gating on CRYPTOGRAPHIC_ASSET)

**Research date:** 2026-03-29
**Valid until:** 2026-06-29 (cyclonedx-python-lib minor versions released frequently; verify version before installing)
