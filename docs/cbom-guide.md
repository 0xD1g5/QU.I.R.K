# Cryptographic Bill of Materials (CBOM) Guide

This guide covers three topics:

1. **What a CBOM is** — plain-English explanation for compliance officers and executives
2. **How QU.I.R.K. produces the CBOM** — technical pipeline for consultants and engineers
3. **Citing the CBOM as compliance evidence** — audit language for NIST SP 800-208, CNSA 2.0, and ISO 27001

---

## Section 1: What Is a CBOM?

*(Audience: compliance officers, executives, risk managers)*

A **Cryptographic Bill of Materials (CBOM)** is a machine-readable inventory of every cryptographic
algorithm, key, and protocol in use across a system or network. It is the cryptographic equivalent
of a Software Bill of Materials (SBOM) — a list of ingredients, not just a report that says
"encryption is present."

Without a CBOM, an organization does not know which of its systems use RSA-2048 (broken by a
sufficiently powerful quantum computer using Shor's algorithm), which use AES-256 (quantum-safe
with a 128-bit effective security margin after Grover's algorithm), and which use deprecated
algorithms like 3DES or RC4. The CBOM makes that inventory explicit, machine-readable, and auditable.

### Why the CBOM Matters for Compliance

Three regulatory drivers make the CBOM a required starting artifact:

**NIST Post-Quantum Cryptography (PQC) Program**

NIST's post-quantum cryptography program culminated in FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), and
FIPS 205 (SLH-DSA) — the first standardized post-quantum algorithms. Before any organization can
begin migration to these algorithms, it must know what it is migrating away from. NIST IR 8547 and
the broader NIST CBOM guidance explicitly use the CycloneDX CBOM schema as the inventory format.

**NIST SP 800-208**

NIST SP 800-208 (Recommendation for Stateful Hash-Based Signature Schemes) requires organizations
to inventory their cryptographic assets before beginning migration planning. A CBOM produced by
QU.I.R.K. satisfies this inventory requirement.

**CNSA 2.0 (Commercial National Security Algorithm Suite 2.0)**

NSA's CNSA 2.0 (August 2022) sets migration deadlines for National Security Systems (NSS):
cryptographic inventory by 2025, algorithm migration beginning by 2026. A CBOM is the starting
artifact for CNSA 2.0 compliance work. The `quantum-vulnerable` / `quantum-safe` labels in the
QU.I.R.K. CBOM map directly to CNSA 2.0 algorithm classification categories.

### What a CBOM Contains

Each component entry in the CBOM represents one discovered cryptographic algorithm and includes:

| Field | Description | Example |
|-------|-------------|---------|
| Algorithm name | Canonical algorithm identifier | `RSA-2048`, `TLS_AES_256_GCM_SHA384`, `ssh-ed25519` |
| Location | System, service, or endpoint where it was discovered | `192.168.1.10:443` (TLS), `10.0.0.5:22` (SSH) |
| Quantum-safety classification | One of three labels (see below) | `quantum-vulnerable` |
| NIST PQC security level | 0–5 scale from NIST's evaluation criteria | `0` (quantum-vulnerable), `3` (NIST level 3) |
| Classical security strength | Equivalent classical security in bits | `112` bits |

**The three quantum-safety labels:**

| Label | Meaning | Examples |
|-------|---------|---------|
| `quantum-safe` | Algorithm withstands known quantum attacks | AES-256-GCM, ML-KEM-768, SHA-384 |
| `quantum-vulnerable` | Algorithm broken by Shor's or Grover's algorithm | RSA (any size), ECDSA, DH, SHA-256 |
| `unknown` | Algorithm not recognized or no algorithm present | Unrecognized cipher, `alg:none` JWT header |

### CBOM Output Formats

QU.I.R.K. produces two artifacts per scan run:

- **`cbom-{timestamp}.cdx.json`** — CycloneDX 1.6 JSON format
- **`cbom-{timestamp}.cdx.xml`** — CycloneDX 1.6 XML format

Both files are written to the `output/` directory and validate against the CycloneDX 1.4+ schema.
The timestamp in the filename ties each inventory to a specific point in time for audit traceability.

---

## Section 2: How QU.I.R.K. Produces the CBOM

*(Audience: technical consultants, security engineers, architects)*

### The Five-Step Pipeline

```
Scan targets → CryptoEndpoints → Algorithm extraction → Classification → CycloneDX serialization
```

#### Step 1: Discovery

QU.I.R.K. scans configured targets across seven scan surfaces and produces `CryptoEndpoint`
database records. Each record contains the raw cryptographic material discovered at that endpoint:

| Scan surface | Raw data captured |
|-------------|-------------------|
| TLS | Cipher suites, certificate algorithm, certificate chain, EC curves, TLS version |
| SSH | KEX algorithms, host key algorithms, encryption algorithms, MAC algorithms (via ssh-audit) |
| JWT/API | JWT algorithm (`alg` header), JWKS public key algorithm and key size |
| Container | Cryptographic library names and versions (via Syft) |
| Source code | Cryptographic anti-patterns found by semgrep (rule IDs reference specific algorithms) |
| AWS cloud | KMS key specs, ACM certificate algorithms, CloudFront TLS policies, ELBv2 listener algorithms |
| Azure cloud | Key Vault key types, App Gateway TLS settings |

#### Step 2: Algorithm Extraction

The CBOM builder (`quirk/cbom/builder.py`, `build_cbom()`) reads each `CryptoEndpoint` and
extracts individual algorithm names. One endpoint typically contributes multiple algorithms:

- A TLS endpoint yields: certificate public-key algorithm + accepted cipher suites decomposed
  into constituent algorithms (key exchange, authentication, encryption, MAC) + EC curves
- An SSH endpoint yields: KEX algorithms + host-key algorithms + encryption algorithms +
  MAC algorithms (parsed from the `ssh_audit_json` field)
- A JWT endpoint yields: the `alg` header value (e.g., `RS256`, `HS256`) + JWKS public key
  algorithm and key size

**TLS cipher suite decomposition example:**

```
TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
→ Key exchange: X25519
→ Authentication: RSA
→ Encryption: AES-256-GCM
→ MAC: SHA-384
```

Algorithms are deduplicated across all endpoints. If 50 TLS endpoints all accept
`TLS_AES_256_GCM_SHA384`, the CBOM contains one `AES-256-GCM` component, not 50.

#### Step 3: Classification

`classify_algorithm()` in `quirk/cbom/classifier.py` maps each algorithm name to a
`(CryptoPrimitive, nist_level, classical_bits)` tuple:

- **`CryptoPrimitive`**: The type of cryptographic operation — `KEY_AGREE`, `PKE` (public-key
  encryption), `SIGNATURE`, `BLOCK_CIPHER`, `AE` (authenticated encryption), `HASH`, `MAC`,
  `KEM`, or `UNKNOWN`
- **`nist_level`**: NIST PQC security level on the 0–5 scale:
  - `0` = quantum-vulnerable (broken by Shor's or Grover-weakened below acceptable threshold)
  - `1`–`5` = quantum-safe at increasing security strength (maps to NIST PQC evaluation categories)
  - `None` = algorithm not recognized
- **`classical_bits`**: Equivalent classical security strength in bits (e.g., 112 for RSA-2048,
  128 for AES-128, 256 for AES-256)

The classifier performs normalization before lookup:
1. Strip vendor suffixes (`@openssh.com`, `@libssh.org`, etc.)
2. Lowercase
3. Direct lookup in the algorithm table
4. Fuzzy normalization: hyphen insertion between letter/digit boundaries
   (e.g., `aes256gcm` → `aes-256-gcm`)

#### Step 4: Quantum Safety Labeling

`quantum_safety_label(nist_level)` assigns the human-readable label:

```python
if nist_level is None:
    return "unknown"       # Algorithm not recognized or no algorithm present
if nist_level == 0:
    return "quantum-vulnerable"  # Broken by Shor's or Grover-weakened
return "quantum-safe"      # nist_level >= 1: meets NIST PQC security level 1+
```

These are the exact three strings returned by the function. They appear verbatim in the CycloneDX
output and in QU.I.R.K.'s JSON reports.

#### Step 5: CycloneDX Serialization

The deduplicated algorithm components are assembled into a `cyclonedx.model.bom.Bom` object with
three component types:

- **Algorithm components** (`CRYPTOGRAPHIC_ASSET / ALGORITHM`): One per unique algorithm, carrying
  `AlgorithmProperties` (primitive, nist_quantum_security_level, classical_security_level,
  execution_environment)
- **Certificate components** (`CRYPTOGRAPHIC_ASSET / CERTIFICATE`): One per TLS/cloud endpoint
  with a certificate, carrying `CertificateProperties` (subject, issuer, validity dates,
  signature algorithm ref, public key ref)
- **Protocol components** (`CRYPTOGRAPHIC_ASSET / PROTOCOL`): One per TLS/SSH endpoint, carrying
  `ProtocolProperties` (type, version, cipher suites with algorithm references)

The Bom is serialized to JSON and XML using `cyclonedx-python-lib` (`JsonV1Dot6` / `XmlV1Dot6`
serializers), producing CycloneDX 1.6 output.

### Algorithm Classification Reference Table

The table below documents representative algorithms from the QU.I.R.K. algorithm table.
Use these for consultant accuracy when explaining findings to clients.

| Algorithm | CryptoPrimitive | NIST Level | Quantum Label | Reason |
|-----------|----------------|-----------|---------------|--------|
| RSA (any size) | `PKE` | 0 | `quantum-vulnerable` | Shor's algorithm solves integer factorization in polynomial time |
| ECDSA / EC | `SIGNATURE` | 0 | `quantum-vulnerable` | Shor's algorithm solves elliptic curve discrete logarithm |
| X25519 / Curve25519 | `KEY_AGREE` | 0 | `quantum-vulnerable` | Shor's algorithm breaks elliptic curve key agreement |
| DH / DHE (all groups) | `KEY_AGREE` | 0 | `quantum-vulnerable` | Shor's algorithm solves discrete logarithm |
| Ed25519 | `SIGNATURE` | 0 | `quantum-vulnerable` | Shor's algorithm breaks elliptic curve signature |
| AES-256-GCM | `AE` | 1 | `quantum-safe` | Grover halving leaves 128-bit effective security — above NIST threshold |
| AES-128-GCM | `AE` | 1 | `quantum-safe` | 64-bit effective post-Grover — marginal but classified safe |
| ChaCha20-Poly1305 | `AE` | 1 | `quantum-safe` | 256-bit symmetric key, Grover leaves 128-bit effective |
| SHA-256 | `HASH` | 0 | `quantum-vulnerable` | Grover halving to 128-bit effective — below NIST threshold |
| SHA-384 | `HASH` | 2 | `quantum-safe` | Grover halving leaves 192-bit effective |
| SHA-512 | `HASH` | 2 | `quantum-safe` | Grover halving leaves 256-bit effective |
| SHA-1 | `HASH` | 0 | `quantum-vulnerable` | Grover halving to 80-bit effective + classical collision attacks |
| HMAC-SHA256 | `HASH` | 0 | `quantum-vulnerable` | 128-bit effective after Grover |
| HMAC-SHA512 | `HASH` | 2 | `quantum-safe` | 256-bit effective after Grover |
| ML-KEM-512 (FIPS 203) | `KEM` | 1 | `quantum-safe` | NIST PQC finalist — designed for quantum resistance |
| ML-KEM-768 (FIPS 203) | `KEM` | 3 | `quantum-safe` | NIST PQC — level 3 security |
| ML-KEM-1024 (FIPS 203) | `KEM` | 5 | `quantum-safe` | NIST PQC — highest security level |
| ML-DSA-65 (FIPS 204) | `SIGNATURE` | 3 | `quantum-safe` | NIST PQC — level 3 digital signature |
| ML-DSA-87 (FIPS 204) | `SIGNATURE` | 5 | `quantum-safe` | NIST PQC — level 5 digital signature |
| SLH-DSA-256 (FIPS 205) | `SIGNATURE` | 5 | `quantum-safe` | NIST PQC stateless hash-based signature |
| RS256 (JWT) | `SIGNATURE` | 0 | `quantum-vulnerable` | RSA-PKCS1 + SHA-256 — RSA component is vulnerable |
| HS256 (JWT) | `MAC` | 0 | `quantum-vulnerable` | HMAC-SHA256 — Grover halving to 128-bit effective |
| alg:none (JWT) | `UNKNOWN` | 0 | `quantum-vulnerable` | No signature — critical vulnerability (not a quantum issue) |
| 3DES | `BLOCK_CIPHER` | 0 | `quantum-vulnerable` | 112-bit effective classical security + SWEET32 attack |

> **Note on `alg:none`:** The `quantum-vulnerable` label for `alg:none` JWTs reflects that
> `nist_level == 0`, but the actual risk is a critical authentication bypass, not a quantum
> computing threat. The finding severity in QU.I.R.K.'s risk engine is CRITICAL for this reason.

---

## Section 3: Citing the CBOM as Compliance Evidence

*(Audience: auditors, compliance teams, consultants preparing evidence packages)*

### NIST SP 800-208 Alignment

NIST SP 800-208 (Recommendation for Stateful Hash-Based Signature Schemes) and the broader NIST
PQC migration guidance require a cryptographic inventory as a precondition for post-quantum
migration planning. The QU.I.R.K. CBOM satisfies this inventory requirement.

**Suggested audit language:**

> *"A cryptographic inventory was produced using QU.I.R.K. v[version] on [date]. The inventory
> covers [N] endpoints across [network ranges / business units]. Cryptographic algorithms were
> classified against the NIST Post-Quantum Cryptography evaluation criteria (NIST IR 8413) using
> the 0–5 NIST PQC security level scale. The complete inventory is attached as CBOM artifact
> `cbom-[timestamp].cdx.json` in CycloneDX 1.6 format, conforming to NIST IR 8547 guidance.
> Quantum-vulnerable components have been identified and are addressed in the accompanying
> migration roadmap."*

**Key facts for the auditor package:**
- QU.I.R.K. uses `nist_quantum_security_level` as defined in CycloneDX 1.4+ schema
- Classification maps to NIST IR 8413 (Status Report on the Third Round of the NIST PQC
  Evaluation Process) security level categories
- The CBOM file includes BOM serial number, timestamp, and tool metadata (name: QU.I.R.K.,
  version: [version]) for chain-of-custody documentation

### CNSA 2.0 Alignment

NSA's CNSA 2.0 (Commercial National Security Algorithm Suite 2.0, August 2022) requires
National Security System operators to:
- Complete a cryptographic inventory by 2025
- Begin migration to CNSA 2.0 algorithms by 2026 (software and firmware)
- Complete migration to CNSA 2.0 algorithms by 2030–2033 (depending on system type)

The QU.I.R.K. CBOM is suitable as the CNSA 2.0 inventory artifact. The `quantum-vulnerable`
label identifies systems using pre-quantum algorithms that CNSA 2.0 requires replacing.

**Suggested audit language:**

> *"Per CNSA 2.0 requirements, a full cryptographic inventory was conducted on [date] using
> QU.I.R.K. v[version]. The inventory identified [N] quantum-vulnerable components across [N]
> systems. Specific components mapped to CNSA 2.0 algorithm classes are documented in the
> attached CBOM (`cbom-[timestamp].cdx.json`). A phased migration plan targeting CNSA 2.0
> compliance by [year] is attached separately."*

**CNSA 2.0 algorithm mapping:**

| CNSA 2.0 Required Algorithm | QU.I.R.K. CBOM Label | Migration Priority |
|-----------------------------|---------------------|--------------------|
| ML-KEM (FIPS 203) — key establishment | `quantum-safe` | — already compliant |
| ML-DSA (FIPS 204) — signatures | `quantum-safe` | — already compliant |
| SLH-DSA (FIPS 205) — signatures | `quantum-safe` | — already compliant |
| RSA (any size) | `quantum-vulnerable` | Replace with ML-KEM/ML-DSA |
| ECDSA / ECDH (P-256, P-384, etc.) | `quantum-vulnerable` | Replace with ML-KEM/ML-DSA |
| DH / DHE | `quantum-vulnerable` | Replace with ML-KEM |
| AES-256 | `quantum-safe` | — already compliant |
| SHA-384 / SHA-512 | `quantum-safe` | — already compliant |

### ISO 27001 / ISO 27002:2022 Alignment

ISO 27002:2022 Control 8.24 (Use of cryptography) requires organizations to define rules on the
use of cryptographic controls and maintain an inventory of cryptographic assets. The QU.I.R.K.
CBOM satisfies the inventory component of Control 8.24.

**Suggested audit language:**

> *"Consistent with ISO 27002:2022 Control 8.24, a cryptographic asset inventory has been
> maintained. The current inventory, produced on [date] using QU.I.R.K. v[version], covers [N]
> systems and is available as CBOM artifact `cbom-[timestamp].cdx.json`. The inventory was
> produced using the CycloneDX 1.6 CBOM schema and classifies cryptographic assets against NIST
> PQC security levels."*

### CycloneDX Schema Validation

The CBOM files produced by QU.I.R.K. can be spot-checked against the CycloneDX schema to confirm
their structure before submission as audit evidence:

```bash
# Quick structure verification
python3 - <<'EOF'
import json, pathlib

cbom_path = pathlib.Path("output/cbom-latest.cdx.json")   # or use exact filename
if not cbom_path.exists():
    # List available CBOM files
    import glob
    files = sorted(glob.glob("output/cbom-*.cdx.json"))
    if files:
        cbom_path = pathlib.Path(files[-1])
    else:
        print("No CBOM files found in output/")
        raise SystemExit(1)

with open(cbom_path) as f:
    data = json.load(f)

print(f"BOM format   : {data.get('bomFormat')}")
print(f"Spec version : {data.get('specVersion')}")
print(f"Serial number: {data.get('serialNumber')}")
print(f"Components   : {len(data.get('components', []))}")

labels = [c.get('cryptoProperties', {}).get('algorithmProperties', {}).get('nistQuantumSecurityLevel')
          for c in data.get('components', [])
          if c.get('cryptoProperties', {}).get('assetType') == 'algorithm']
print(f"Algorithm components: {sum(1 for l in labels if l is not None)}")
EOF
```

**Expected output for a valid CBOM:**
```
BOM format   : CycloneDX
Spec version : 1.6
Serial number: urn:uuid:...
Components   : <N>
Algorithm components: <M>
```

### Artifact Retention Guidance

For compliance evidence packages, retain the following alongside each CBOM:

| Artifact | Purpose | Retention |
|----------|---------|-----------|
| `cbom-{timestamp}.cdx.json` | Machine-readable inventory (JSON) | With the scan session |
| `cbom-{timestamp}.cdx.xml` | Machine-readable inventory (XML) | With the scan session |
| `assessment-{timestamp}.md` | Human-readable report | With the scan session |
| QU.I.R.K. version (`quirk --version`) | Tool provenance | In the cover sheet |
| Scan configuration (`config.yaml`) | Scope documentation | With the scan session |

The timestamp in the CBOM filename ties the inventory to a specific point in time. For compliance
purposes, this timestamp represents the "as-of" date for the cryptographic inventory.

Some auditor toolchains have a preference for JSON or XML format. QU.I.R.K. produces both; include
both in evidence packages to maximize compatibility. If the receiving system supports CycloneDX
CBOM import, the JSON artifact is typically the preferred format.

---

## Quick Reference

### CBOM Checklist for Auditors

- [ ] `bomFormat` is `CycloneDX`
- [ ] `specVersion` is `1.6` (or `1.4` / `1.5` — all validate against CycloneDX CBOM schema)
- [ ] `serialNumber` is present (unique identifier for this CBOM)
- [ ] `metadata.timestamp` matches the scan date in the evidence package
- [ ] `metadata.component.name` is `QU.I.R.K.` and `version` is recorded
- [ ] `components` array is non-empty
- [ ] Algorithm components include `nistQuantumSecurityLevel` property
- [ ] Both JSON and XML artifacts are present

### Classification Logic Summary

```
Algorithm → classify_algorithm() → (CryptoPrimitive, nist_level, classical_bits)
                                        ↓
                               quantum_safety_label(nist_level)
                                        ↓
                    "quantum-vulnerable" | "quantum-safe" | "unknown"
```

The `nist_level` and `quantum_safety_label` values appear in the CycloneDX `algorithmProperties`
block of each algorithm component in the CBOM.

---

*Guide version: Phase 6 (2026-03-31) — covers QU.I.R.K. v3.9*

*Canonical references: `quirk/cbom/classifier.py` (`quantum_safety_label()`, `_ALGORITHM_TABLE`),
`quirk/cbom/builder.py` (`build_cbom()`)*
