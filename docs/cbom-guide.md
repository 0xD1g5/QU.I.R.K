# Cryptographic Bill of Materials (CBOM) Guide

This guide covers three topics:

1. **What a CBOM is** — plain-English explanation for compliance officers and executives
2. **How QU.I.R.K. produces the CBOM** — technical pipeline for consultants and engineers
3. **Citing the CBOM as compliance evidence** — what the CBOM does and does not establish, with audit language for the frameworks QU.I.R.K. maps

---

## Section 1: What Is a CBOM?

*(Audience: compliance officers, executives, risk managers)*

A **Cryptographic Bill of Materials (CBOM)** is a machine-readable inventory of every cryptographic
algorithm, key, and protocol in use across a system or network. It is the cryptographic equivalent
of a Software Bill of Materials (SBOM) — a list of ingredients, not just a report that says
"encryption is present."

Without a CBOM, an organization does not know which of its systems use RSA-2048 (which Shor's
algorithm would break on a sufficiently powerful quantum computer), which use AES-256 (classified
quantum-safe by QU.I.R.K.), and which use legacy algorithms like 3DES. The CBOM makes that
inventory explicit, machine-readable, and auditable.

### Why the CBOM Matters for Compliance

**NIST Post-Quantum Cryptography (PQC) Program**

NIST published the first three post-quantum standards — FIPS 203 (ML-KEM), FIPS 204 (ML-DSA) and
FIPS 205 (SLH-DSA) — on August 13, 2024. Before an organization can migrate to these algorithms,
it must know what it is migrating away from. NIST's draft transition report, IR 8547
(*Transition to Post-Quantum Cryptography Standards*), describes how quantum-vulnerable algorithms
are expected to be deprecated and disallowed; a CBOM is the inventory that tells you which of
those algorithms you actually use.

**OMB Memorandum M-23-02**

For U.S. federal agencies, OMB Memorandum M-23-02 establishes requirements to inventory active
cryptographic systems, with a focus on High Value Assets and high impact systems. A QU.I.R.K. CBOM
is a machine-readable inventory of the cryptography it observed on the targets you scanned. It does
not by itself satisfy an agency's M-23-02 submission, which has its own scope and format.

**CNSA 2.0**

QU.I.R.K. does not encode CNSA 2.0 requirements or dates in its CBOM classifier or labels, and this
guide does not state them: NSA's CNSA 2.0 publication cannot be fetched by automated tooling (HTTP
403), so the dates have not been verified against the primary source. Take CNSA 2.0 algorithms and
deadlines from NSA's own publication.

### What a CBOM Contains

Each algorithm component in the CBOM represents one distinct algorithm and carries:

| Field | Description | Example |
|-------|-------------|---------|
| Algorithm name | Algorithm identifier as normalized by the builder | `RSA-2048`, `AES-256-GCM`, `ssh-ed25519` |
| Primitive | CycloneDX crypto primitive | `pke`, `signature`, `ae` |
| NIST security level | `nistQuantumSecurityLevel` — the NIST security strength category; `0` means none of the categories is met (CycloneDX allows 0–6) | `0` for RSA-2048, `3` for ML-KEM-768 |
| Classical security strength | `classicalSecurityLevel`, in bits | `112` for RSA-2048 |
| FIPS 140-3 status | `quirk:fips140-3-status` property: `approved` or `non-approved` | `non-approved` for RSA |

Where an endpoint was scanned, the location (host and port) appears in the certificate and protocol
component names, for example `protocol:tls:192.168.1.10:443`; algorithm components are shared across
endpoints.

**The three quantum-safety labels:**

The CBOM file itself does not contain these label strings. They are derived from the NIST security
level by `quantum_safety_label()` and appear in the dashboard, the API, and `quirk analyze-token`
(the dashboard and the API display them as `Safe`, `Vulnerable` and `Unknown`).

| Label | NIST level | Examples |
|-------|-----------|----------|
| `quantum-safe` | 1 or higher | `AES-256-GCM`, `ML-KEM-768`, `SHA-384` |
| `quantum-vulnerable` | 0 | `RSA`, `RSA-1024` to `RSA-4096`, `ECDSA`, `X25519`, `SHA-256` |
| `unknown` | none (algorithm not recognized, or a table entry that carries no level) | an unrecognized cipher name, an RSA key size the table does not list (for example `RSA-8192`) |

### CBOM Output Formats

QU.I.R.K. writes two CBOM files per scan run:

- **`cbom-{timestamp}.cdx.json`** — CycloneDX 1.6 JSON
- **`cbom-{timestamp}.cdx.xml`** — CycloneDX 1.6 XML

Both are written to the configured output directory (`output.directory`, `./quirk-output` in the
shipped config template). After writing the JSON file, QU.I.R.K. validates it against the CycloneDX
1.6 JSON schema; a failure is recorded as a warning finding and the file is kept. The timestamp
(UTC, `YYYYMMDD-HHMMSS`) ties each inventory to a specific point in time.

---

## Section 2: How QU.I.R.K. Produces the CBOM

*(Audience: technical consultants, security engineers, architects)*

### The Five-Step Pipeline

```
Scan targets → CryptoEndpoints → Algorithm extraction → Classification → CycloneDX serialization
```

#### Step 1: Discovery

QU.I.R.K. scans the configured targets and stores one `CryptoEndpoint` database record per
discovered endpoint or finding. Each record carries the raw cryptographic material for its
protocol. The CBOM builder has a dedicated branch for these record types:

- **TLS** (the default branch) — cipher suite, certificate public-key and signature algorithms
- **SSH** — KEX, host-key, encryption and MAC algorithms parsed from ssh-audit JSON
- **JWT** and **bearer token** — the declared JWT algorithm
- **Container** — cryptographic library names found by Syft (recorded as a coverage note)
- **Source code** — an algorithm hint taken from the semgrep rule ID (known defect in 5.28.0: ruleset unavailable, so no source records are produced)
- **Cloud** (AWS, Azure, GCP) — KMS and Key Vault key specs and certificate algorithms
- **Identity** (Kerberos, SAML, DNSSEC, S/MIME, AD CS) and **code signing** — the algorithm named by the finding
- **Data at rest** (Vault, MySQL, PostgreSQL/RDS, S3 / Azure Blob) — an algorithm only when the record names one; plaintext and unencrypted endpoints produce a coverage note instead. Azure Blob rows currently never register an algorithm: every Blob container, including one encrypted with a customer-managed or platform-managed key, gets the `unencrypted S3/Blob endpoint` coverage note (a known defect)

#### Step 2: Algorithm Extraction

The CBOM builder (`quirk/cbom/builder.py`, `build_cbom()`) reads each `CryptoEndpoint` and
extracts individual algorithm names. One endpoint typically contributes multiple algorithms:

- A TLS endpoint yields: the certificate public-key and signature algorithms + the recorded
  cipher suite decomposed into constituent algorithms (key exchange, authentication, encryption, MAC)
- An SSH endpoint yields: KEX algorithms + host-key algorithms + encryption algorithms +
  MAC algorithms (parsed from the `ssh_audit_json` field)
- A JWT endpoint yields: the JWT algorithm recorded for the key (e.g., `RS256`, `ES256`) and its key size

**TLS cipher suite decomposition example:**

```
TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
→ Key exchange: X25519
→ Authentication: RSA
→ Encryption: AES-256-GCM
→ MAC: SHA-384
```

The decomposition is name-based: every `ECDHE` or `ECDH` key exchange is recorded as `X25519`,
whatever curve was actually negotiated.

Algorithms are deduplicated across all endpoints. If 50 TLS endpoints all record
`TLS_AES_256_GCM_SHA384`, the CBOM contains one `AES-256-GCM` component, not 50.

#### Step 3: Classification

`classify_algorithm()` in `quirk/cbom/classifier.py` looks the name up in a table of 120 entries
(`_ALGORITHM_TABLE`) and returns a `(CryptoPrimitive, nist_level, classical_bits)` tuple:

- **`CryptoPrimitive`**: The type of cryptographic operation — for example `KEY_AGREE`, `PKE`
  (public-key encryption), `SIGNATURE`, `BLOCK_CIPHER`, `AE` (authenticated encryption), `HASH`,
  `MAC`, `KEM`, or `UNKNOWN`
- **`nist_level`**: the NIST security strength category:
  - `0` = none of the categories is met; QU.I.R.K. labels this quantum-vulnerable
  - `1`–`5` = quantum-safe, at increasing security strength
  - `None` = algorithm not recognized, or one of the 11 table entries that carry no level (for
    example the DNSSEC names `rsasha256` and `rsasha512`, and `sha1`)
- **`classical_bits`**: Equivalent classical security strength in bits (e.g., 112 for RSA-2048,
  128 for AES-128-GCM, 256 for AES-256-GCM)

The classifier performs normalization before lookup:
1. Strip vendor suffixes (`@openssh.com`, `@libssh.org`, etc.)
2. Lowercase
3. Direct lookup in the algorithm table
4. Fuzzy normalization: hyphen insertion between letter/digit boundaries
   (e.g., `aes256gcm` → `aes-256-gcm`)

A name that is still not found returns `(UNKNOWN, None, None)`.

#### Step 4: Quantum Safety Labeling

`quantum_safety_label(nist_level)` assigns the human-readable label:

```python
if nist_level is None:
    return "unknown"             # algorithm not recognized
if nist_level == 0:
    return "quantum-vulnerable"  # none of the NIST categories is met
return "quantum-safe"            # nist_level >= 1
```

These are the only three strings the function returns. The labels are not written into the
CycloneDX file — the file carries `nistQuantumSecurityLevel` — but `quirk analyze-token` prints
them, and the dashboard and the API show them as `Safe`, `Vulnerable` and `Unknown`.

#### Step 5: CycloneDX Serialization

The deduplicated components are assembled into a `cyclonedx.model.bom.Bom` object. The cryptographic
asset components are:

- **Algorithm components** (`CRYPTOGRAPHIC_ASSET / ALGORITHM`): One per unique algorithm, carrying
  `AlgorithmProperties` (primitive, nist_quantum_security_level, classical_security_level,
  execution_environment)
- **Certificate components** (`CRYPTOGRAPHIC_ASSET / CERTIFICATE`): One per TLS-style endpoint with a
  certificate public-key algorithm, carrying `CertificateProperties` (subject, issuer, validity
  dates, signature algorithm ref, public key ref)
- **Protocol components** (`CRYPTOGRAPHIC_ASSET / PROTOCOL`): One per TLS or SSH endpoint, carrying
  `ProtocolProperties` (type, version, cipher suites with algorithm references). TLS is the
  builder's default branch, so an endpoint whose protocol has no dedicated skip also gets a
  `protocol:tls` component. One known case is the `ADVISORY` row the PQC probe writes when the
  scanning host's OpenSSL cannot test for ML-KEM: it yields a second, empty `protocol:tls`
  component for the same host and port.

When hardware devices were inventoried the CBOM also contains device and firmware components, and
when remediation items exist it carries VEX entries.

The Bom is serialized to JSON and XML using `cyclonedx-python-lib` (`JsonV1Dot6` / `XmlV1Dot6`
serializers), producing CycloneDX 1.6 output.

### Algorithm Classification Reference Table

The table below shows how representative entries of the algorithm table are classified. Names are
the table keys (matching is case-insensitive); a bare family name such as `DH` or `HMAC-SHA256`
is **not** a key and classifies as `unknown`. Use the exact names below when explaining findings.

| Algorithm | CryptoPrimitive | NIST Level | Quantum Label | Reason |
|-----------|----------------|-----------|---------------|--------|
| `RSA`, `RSA-2048`, `RSA-4096` | `PKE` | 0 | `quantum-vulnerable` | Shor's algorithm factors integers in polynomial time |
| `ECDSA`, `EC` | `SIGNATURE` | 0 | `quantum-vulnerable` | Elliptic-curve based; classified level 0 by the table |
| `X25519`, `curve25519-sha256` | `KEY_AGREE` | 0 | `quantum-vulnerable` | Elliptic-curve based; classified level 0 by the table |
| `dh-2048`, `diffie-hellman-group14-sha256` | `KEY_AGREE` | 0 | `quantum-vulnerable` | Shor's algorithm solves discrete logarithms in polynomial time |
| `Ed25519` | `SIGNATURE` | 0 | `quantum-vulnerable` | Elliptic-curve based; classified level 0 by the table |
| `AES-256-GCM` | `AE` | 1 | `quantum-safe` | 256-bit classical strength; level 1 in the table |
| `AES-128-GCM` | `AE` | 1 | `quantum-safe` | 128-bit classical strength; level 1 in the table |
| `ChaCha20-Poly1305` | `AE` | 1 | `quantum-safe` | 256-bit classical strength; level 1 in the table |
| `SHA-256` | `HASH` | 0 | `quantum-vulnerable` | 128-bit classical strength; level 0 in the table |
| `SHA-384` | `HASH` | 2 | `quantum-safe` | 192-bit classical strength |
| `SHA-512` | `HASH` | 2 | `quantum-safe` | 256-bit classical strength |
| `SHA-1` | `HASH` | 0 | `quantum-vulnerable` | 80-bit classical strength; level 0 in the table |
| `hmac-sha2-256` | `HASH` | 0 | `quantum-vulnerable` | 128-bit classical strength; level 0 in the table |
| `hmac-sha2-512` | `HASH` | 2 | `quantum-safe` | 256-bit classical strength |
| `ML-KEM-512` (FIPS 203) | `KEM` | 1 | `quantum-safe` | Module-lattice KEM standardized in FIPS 203 |
| `ML-KEM-768` (FIPS 203) | `KEM` | 3 | `quantum-safe` | Level 3 |
| `ML-KEM-1024` (FIPS 203) | `KEM` | 5 | `quantum-safe` | Level 5 |
| `ML-DSA-65` (FIPS 204) | `SIGNATURE` | 3 | `quantum-safe` | Level 3 digital signature |
| `ML-DSA-87` (FIPS 204) | `SIGNATURE` | 5 | `quantum-safe` | Level 5 digital signature |
| `SLH-DSA-256` (FIPS 205) | `SIGNATURE` | 5 | `quantum-safe` | Stateless hash-based signature |
| `RS256` (JWT) | `SIGNATURE` | 0 | `quantum-vulnerable` | RSA-based signature; classified level 0 |
| `HS256` (JWT) | `MAC` | 0 | `quantum-vulnerable` | Classified level 0 by the table |
| `none` (JWT `alg` header) | `UNKNOWN` | 0 | `quantum-vulnerable` | No signature — a critical authentication weakness, not a quantum issue |
| `3DES` | `BLOCK_CIPHER` | 0 | `quantum-vulnerable` | 112-bit classical strength; level 0 in the table |

The symmetric and hash levels are the table's own assignments, not a statement about any
standard. Grover's algorithm searches an unsorted space of N items in O(sqrt(N)) steps.

> **DNSSEC algorithm names:** The DNSSEC scanner records the DNSKEY algorithm name (for example
> `ECDSAP256SHA256`), and those names are separate table keys. `ecdsap256sha256` and
> `ecdsap384sha384` (DNSSEC algorithms 13 and 14) are classified at NIST level 1 and 3, so a zone
> signed with them is labelled `quantum-safe`, although plain `ECDSA` is level 0.
> `rsasha256` and `rsasha512` carry no level and are labelled `unknown`. This inconsistency in the
> table is an open defect; do not cite the label of a DNSSEC algorithm component as a
> quantum-safety determination.

> **Note on `alg:none`:** The `quantum-vulnerable` label for a JWT whose `alg` is `none` reflects
> that `nist_level == 0`, but the actual risk is a critical authentication bypass, not a quantum
> computing threat. A scan run with a bearer credential (`--auth-bearer`) whose JWT declares `alg:none`, or no `alg`, reports the CRITICAL finding "Bearer token is unsigned (alg:none)", and `quirk analyze-token` reports it as a CRITICAL finding offline. The CBOM still classifies the declared `none` at level 0, and a missing `alg` registers no algorithm component.

---

## Section 3: Citing the CBOM as Compliance Evidence

*(Audience: auditors, compliance teams, consultants preparing evidence packages)*

A QU.I.R.K. CBOM is evidence of what cryptography the scanner observed on the targets in scope at
one point in time. It is not a certification, and it does not on its own demonstrate that any
framework's requirements are met.

### NIST Post-Quantum Cryptography Alignment

QU.I.R.K. classifies each algorithm with the NIST security strength category carried in the
CycloneDX `nistQuantumSecurityLevel` field (`0` means none of the categories is met). It labels
the table entries `ML-KEM-512`, `ML-KEM-768`, `ML-KEM-1024` (FIPS 203), `ML-DSA-44`, `ML-DSA-65`,
`ML-DSA-87` (FIPS 204) and `SLH-DSA-128`, `SLH-DSA-192`, `SLH-DSA-256` (FIPS 205) as quantum-safe.
FIPS 205's full parameter-set names, such as `SLH-DSA-SHA2-128s`, are not table keys and classify
as `unknown`.

**Suggested audit language:**

> *"A cryptographic inventory was produced using QU.I.R.K. v[version] on [date]. The inventory
> covers [N] endpoints across [network ranges / business units]. Cryptographic algorithms were
> classified by NIST security strength category using the CycloneDX `nistQuantumSecurityLevel`
> field. The complete inventory is attached as CBOM artifact `cbom-[timestamp].cdx.json` in
> CycloneDX 1.6 format. Quantum-vulnerable components have been identified and are addressed in the
> accompanying migration roadmap."*

**Key facts for the auditor package:**
- `nistQuantumSecurityLevel` is defined in the CycloneDX 1.6 schema (minimum 0, maximum 6)
- The CBOM file includes a BOM serial number, a timestamp, and the producing tool in
  `metadata.component` (name: QU.I.R.K., version: [version]) for chain-of-custody documentation

### CNSA 2.0

See "Why the CBOM Matters for Compliance" above. QU.I.R.K. does not map its CBOM labels to CNSA 2.0
algorithm classes, so do not cite this CBOM as a CNSA 2.0 compliance determination. It can serve
as the starting inventory for that work.

### Framework Mappings Carried by Findings

QU.I.R.K. attaches machine-readable control references to findings for five frameworks, listed by
`quirk compliance status`: FIPS 140-3, HIPAA 45 CFR, ISO 27001:2022, PCI-DSS 4.0.1 and SOC 2 CC.
The references appear on findings and in reports; the CBOM file does not carry them. Its only
compliance-related data are the `quirk:fips140-3-status` and `quirk:cmvp-coverage` properties
described below. Each mapping is a QU.I.R.K. judgement about
which control a finding bears on, not an assessment result.

**PCI DSS 4.0.1.** Findings carry references to Requirements 4.2.1, 4.2.1.1, 6.3.3 and 8.3.2 (for example
plaintext or weak transport encryption, expired, self-signed or untrusted certificates,
outdated cryptographic packages in container images, and an unauthenticated plaintext Redis
listener).

**HIPAA 45 CFR § 164.312.** Findings carry references to § 164.312(a)(2)(iv), (e)(1) and
(e)(2)(ii). The regulation text for these specifications reads: "(iv) Encryption and decryption
(Addressable). Implement a mechanism to encrypt and decrypt electronic protected health
information." and "(ii) Encryption (Addressable). Implement a mechanism to encrypt electronic
protected health information whenever deemed appropriate."

**FIPS 140-3** (*Security Requirements for Cryptographic Modules*). Every algorithm component in
the CycloneDX CBOM carries a `quirk:fips140-3-status` property set to `approved` (NIST level of 1
or higher) or `non-approved` (NIST level 0 or unknown). The property is derived from QU.I.R.K.'s
NIST level, not from a CMVP validation. When QU.I.R.K.'s bundled CMVP cache lists validated
modules for the algorithm family, the component also carries an informational
`quirk:cmvp-coverage` property naming those modules; it does not change `quirk:fips140-3-status`.

**SOC 2.** Findings carry references to Common Criteria CC6.6 and CC6.7.

**ISO 27001:2022.** Findings carry references to Annex A controls 8.24 and 8.26.

**Suggested audit language:**

> *"A cryptographic inventory was produced on [date] using QU.I.R.K. v[version]. Findings carrying
> a `PCI-DSS 4.0.1` compliance reference are included in the attached report, and the complete
> inventory is attached as CBOM artifact `cbom-[timestamp].cdx.json`. The inventory was produced
> using the CycloneDX 1.6 CBOM schema."*

### CycloneDX Schema Validation

QU.I.R.K. validates the JSON CBOM against the CycloneDX 1.6 schema right after writing it. You can
also spot-check a file's structure before submitting it as audit evidence. Run this from the
directory that contains your output directory (`quirk-output` by default):

```bash
python3 - <<'EOF'
import glob, json, pathlib

files = sorted(glob.glob("quirk-output/cbom-*.cdx.json"))
if not files:
    print("No CBOM files found in quirk-output/")
    raise SystemExit(1)

data = json.loads(pathlib.Path(files[-1]).read_text())
components = data.get("components", [])
algorithms = [
    c for c in components
    if c.get("cryptoProperties", {}).get("assetType") == "algorithm"
]

print(f"BOM format   : {data.get('bomFormat')}")
print(f"Spec version : {data.get('specVersion')}")
print(f"Serial number: {data.get('serialNumber')}")
print(f"Components   : {len(components)}")
print(f"Algorithm components: {len(algorithms)}")
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
| `report-{timestamp}.html` and `executive-summary-{timestamp}.md` | Human-readable reports | With the scan session |
| QU.I.R.K. version (`quirk --version`) | Tool provenance | In the cover sheet |
| Scan configuration (`config.yaml`) | Scope documentation | With the scan session |

The timestamp in the CBOM filename ties the inventory to a specific point in time. For compliance
purposes, this timestamp represents the "as-of" date for the cryptographic inventory.

Some auditor toolchains prefer JSON or XML. QU.I.R.K. produces both; include both in evidence
packages to maximize compatibility.

---

## Quick Reference

### CBOM Checklist for Auditors

- [ ] `bomFormat` is `CycloneDX`
- [ ] `specVersion` is `1.6`
- [ ] `serialNumber` is present (unique identifier for this CBOM)
- [ ] `metadata.timestamp` matches the scan date in the evidence package
- [ ] `metadata.component.name` is `QU.I.R.K.` and `version` is recorded
- [ ] `components` array is non-empty
- [ ] Algorithm components include `nistQuantumSecurityLevel` property
- [ ] Algorithm components include `quirk:fips140-3-status` property (`approved` or `non-approved`)
- [ ] Both JSON and XML artifacts are present

### Classification Logic Summary

```
Algorithm → classify_algorithm() → (CryptoPrimitive, nist_level, classical_bits)
                                        ↓
                               quantum_safety_label(nist_level)
                                        ↓
                    "quantum-vulnerable" | "quantum-safe" | "unknown"
```

The `nist_level` and `classical_bits` values appear in the CycloneDX `algorithmProperties` block of
each algorithm component in the CBOM. The `quantum_safety_label` result is derived from the level
for the dashboard, API and CLI output; it is not written into the CBOM file.

---

## Additional CBOM Behaviors

The five-step pipeline above covers the common case. The builder also handles these:

- **PQC-hybrid components** — `X25519MLKEM768` is recognised by the classifier (it is a KEM entry at NIST level 3) and is emitted as a quantum-safe KEM component, not as a classical fallback. The agility subscore's `+8.0` PQC-hybrid bonus is keyed to the PQC probe's `pqc-hybrid-detected` endpoint marker, not to the CBOM component. The probe also sets that marker on the advisory row it writes when the scanning host's OpenSSL cannot test for ML-KEM, so the bonus is applied in that case too although nothing was detected (an open defect).
- **Bearer-token branch** — when the operator-supplied bearer token is a JWT, the scan adds a `BEARER_TOKEN` endpoint with the token's declared `alg`, and the builder's dedicated branch registers that algorithm and adds a `bearer-token-declared-algorithm` coverage note recording that it is declared, not verified. An opaque (non-JWT) bearer token declares no algorithm, so it adds nothing to the CBOM.
- **Code-signing branch** — code-signing certificates are emitted as their own branch, deduplicated by fingerprint; when a TLS certificate with the same subject, algorithm and expiry exists, the TLS component is kept and annotated with a `quirk:code-signing-eku` property.
- **REST fuzz endpoints** — fuzz-only API probes are skipped when certificate and protocol components are built, so they do not appear as phantom TLS components.
- **Distributed-mode merge keys** — when multiple sensors push findings to a central console, the builder prefixes certificate and protocol component references with the sensor ID, and includes `sensor_id` in the TLS and code-signing surrogate keys, so per-sensor findings are preserved through a merge.
- **Zero-algorithm profiles** — endpoints that surface no algorithm (for example the chaos-lab `database`, `registry`, `source`, `ssh-weak` and `storage-s3` profiles) are covered by a test that requires the CBOM to contain either real algorithm components or an affirmative coverage note, rather than leaving a silent gap.

---

*Canonical references: `quirk/cbom/classifier.py` (`quantum_safety_label()`, `_ALGORITHM_TABLE`),
`quirk/cbom/builder.py` (`build_cbom()`), `quirk/compliance/` (framework mappings)*
