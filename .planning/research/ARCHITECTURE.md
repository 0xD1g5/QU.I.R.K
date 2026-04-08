# Architecture Research

**Domain:** Identity Protocol Cryptography Scanner Integration (v4.2)
**Researched:** 2026-04-08
**Confidence:** HIGH — based on direct codebase inspection + RFC/documentation verification

---

## Context: What Already Exists

QU.I.R.K. v4.1 has a well-established scanner integration pattern. Every scanner type follows
the same data flow:

```
Scanner module            → CryptoEndpoint rows (SQLite)
                          → build_cbom() (classifier.py)
                          → compute_readiness_score() (scoring.py)
                          → /api/scan/latest (dashboard API)
                          → React SPA (specific tab/section)
```

The v4.2 identity scanners must follow this pattern exactly. Diverging from it creates
maintenance debt and breaks the CBOM pipeline.

---

## Standard Architecture

### System Overview (v4.2 addition in context of whole system)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLI / Interactive Wizard                      │
│   quirk scan --config config.yaml                                   │
│   ConnectorsCfg: enable_kerberos, enable_saml, enable_dnssec        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                        Scanner Layer (quirk/scanner/)                │
│                                                                      │
│  Existing:                         New (v4.2):                      │
│  ┌──────────────┐                  ┌────────────────┐               │
│  │ tls_scanner  │                  │kerberos_scanner│               │
│  ├──────────────┤                  ├────────────────┤               │
│  │ ssh_scanner  │                  │ saml_scanner   │               │
│  ├──────────────┤                  ├────────────────┤               │
│  │ jwt_scanner  │                  │ dnssec_scanner │               │
│  ├──────────────┤                  └────────────────┘               │
│  │container_scan│                                                    │
│  ├──────────────┤                                                    │
│  │source_scanner│                                                    │
│  ├──────────────┤                                                    │
│  │aws_connector │                                                    │
│  └──────────────┘                                                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ CryptoEndpoint rows
┌──────────────────────────────▼──────────────────────────────────────┐
│                        SQLite (quirk.db)                             │
│                        crypto_endpoints table                        │
│                                                                      │
│  Existing columns:            New columns (v4.2):                   │
│  tls_capabilities_json        kerberos_scan_json                    │
│  ssh_audit_json               saml_scan_json                        │
│  jwt_scan_json                dnssec_scan_json                      │
│  container_scan_json                                                 │
│  source_scan_json                                                    │
│  cloud_scan_json                                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                        CBOM Pipeline (quirk/cbom/)                   │
│                                                                      │
│  classifier.py:  classify_algorithm()  ← new entries for identity   │
│  builder.py:     build_cbom()          ← new protocol branches      │
│  writer.py:      (unchanged)                                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                  Intelligence Layer (quirk/intelligence/)            │
│                                                                      │
│  evidence.py:   evidence collection  ← identity_weak_etype_count    │
│  scoring.py:    compute_readiness_score() ← new identity_ weights   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                        Dashboard (FastAPI + React)                   │
│                                                                      │
│  GET /api/scan/latest  ← new identity_findings in response JSON     │
│  React: new <IdentityTab> alongside TLS / SSH / JWT tabs            │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Modification Type |
|-----------|---------------|-------------------|
| `quirk/scanner/kerberos_scanner.py` | AS-REQ probe to KDC port 88, parse ETYPE-INFO2 from error reply | NEW |
| `quirk/scanner/saml_scanner.py` | Fetch SAML metadata XML + OIDC discovery JSON, extract signing algorithm and cert | NEW |
| `quirk/scanner/dnssec_scanner.py` | Query DNSKEY + DS records via dnspython, classify algorithms by RFC 8624 | NEW |
| `quirk/models.py` | Add `kerberos_scan_json`, `saml_scan_json`, `dnssec_scan_json` columns | MODIFY |
| `quirk/config.py` | Add `enable_kerberos`, `enable_saml`, `enable_dnssec` flags + target lists to `ConnectorsCfg` | MODIFY |
| `quirk/cbom/classifier.py` | Add Kerberos etype strings, DNSSEC algorithm names to `_ALGORITHM_TABLE` | MODIFY |
| `quirk/cbom/builder.py` | Add `KERBEROS`, `SAML`, `DNSSEC` protocol branches in `build_cbom()` Pass 1 + Pass 3 | MODIFY |
| `quirk/intelligence/evidence.py` | Add `identity_weak_etype_count`, `saml_weak_signing_count`, `dnssec_weak_algo_count` to evidence dict | MODIFY |
| `quirk/intelligence/scoring.py` | Add new weights for identity protocol sub-score | MODIFY |
| `quirk/dashboard/api/routes/scan.py` | Add identity finding derivation logic + identity tab data serialization | MODIFY |
| `quirk/dashboard/api/schemas.py` | Add `IdentityFinding` Pydantic model if divergent from `FindingItem` | MODIFY (likely minor) |
| `quantum-chaos-enterprise-lab/docker-compose.yml` | Add `kerberos`, `saml`, `dnssec` profiles | MODIFY |

---

## Recommended Project Structure

```
quirk/
├── scanner/
│   ├── kerberos_scanner.py     # NEW — AS-REQ etype probe
│   ├── saml_scanner.py         # NEW — SAML/OIDC metadata fetch
│   ├── dnssec_scanner.py       # NEW — DNSKEY/DS record audit
│   └── ... (existing)
├── cbom/
│   ├── classifier.py           # MODIFY — add Kerberos/DNSSEC entries
│   └── builder.py              # MODIFY — KERBEROS/SAML/DNSSEC branches
├── models.py                   # MODIFY — 3 new JSON columns
├── config.py                   # MODIFY — 3 flags + 3 target lists
└── dashboard/
    └── api/
        ├── routes/scan.py      # MODIFY — identity findings + serialization
        └── schemas.py          # MODIFY — identity-specific fields if needed

quantum-chaos-enterprise-lab/
├── docker-compose.yml          # MODIFY — add kerberos/saml/dnssec profiles
├── kerberos/
│   └── (Samba DC init scripts)
├── saml/
│   └── (SimpleSAMLphp override config or seed script)
└── dnssec/
    └── (BIND9 zone file with weak + strong algorithm keys)
```

---

## Architectural Patterns

### Pattern 1: JSON Blob Column per Scanner Type

**What:** Each scanner writes its full output to a dedicated `*_scan_json` column on `CryptoEndpoint`. The scanner controls the schema. Downstream consumers (CBOM builder, dashboard) parse it on read.

**When to use:** Every new scanner type in QU.I.R.K. Established by `ssh_audit_json`, `jwt_scan_json`, `cloud_scan_json`.

**Trade-offs:** Simple additive schema (no foreign keys, no joins, no migration tooling needed). Slight read-time parsing overhead is acceptable at consulting engagement scale (<10K rows). Schema evolution is unversioned — callers must handle missing keys gracefully.

**For v4.2, each new column holds:**

```python
# kerberos_scan_json — example structure
{
    "realm": "CORP.EXAMPLE.COM",
    "kdc": "192.168.1.10",
    "port": 88,
    "supported_etypes": [17, 18, 23],   # etype numbers from ETYPE-INFO2
    "has_rc4": true,                     # etype 23 present
    "has_des": false,                    # etype 1/3 present
    "has_aes128": true,                  # etype 17 present
    "has_aes256": true,                  # etype 18 present
    "error": null                        # KRB5 error code if probe failed
}

# saml_scan_json — example structure
{
    "entity_id": "https://idp.example.com/saml",
    "metadata_url": "https://idp.example.com/saml/metadata",
    "idp_signing_cert_subject": "CN=idp.example.com",
    "idp_signing_cert_algo": "RSA",
    "idp_signing_cert_bits": 2048,
    "idp_signing_alg_declared": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
    "oidc_issuer": "https://idp.example.com",
    "oidc_jwks_uri": "https://idp.example.com/.well-known/jwks.json",
    "oidc_id_token_signing_alg_values": ["RS256", "ES256"],
    "scan_type": "saml"   # "saml" | "oidc" | "both"
}

# dnssec_scan_json — example structure
{
    "domain": "example.com",
    "signed": true,
    "dnskey_records": [
        {"key_tag": 12345, "algorithm": 8, "algorithm_name": "RSASHA256", "flags": 257},
        {"key_tag": 23456, "algorithm": 13, "algorithm_name": "ECDSAP256SHA256", "flags": 256}
    ],
    "ds_records": [
        {"key_tag": 12345, "algorithm": 8, "digest_type": 2}
    ],
    "weak_algorithms": [5, 7],   # algorithm numbers considered weak per RFC 8624
    "recommended": true
}
```

### Pattern 2: Protocol String Convention

**What:** The `protocol` column on `CryptoEndpoint` is the discriminator used in all downstream code branches (`build_cbom`, `_derive_findings`, `_derive_cbom`).

**When to use:** Every new scanner type must set `ep.protocol` to a unique uppercase string.

**Established values:** `TLS`, `SSH`, `HTTP`, `JWT`, `CONTAINER`, `SOURCE`, `AWS`, `AZURE`

**New values for v4.2:**
- `KERBEROS` — one row per KDC endpoint probed
- `SAML` — one row per IdP metadata URL or OIDC issuer
- `DNSSEC` — one row per domain audited

**Why one row per target (not one row per algorithm):** The SSH scanner is the authoritative model — it writes one row per SSH endpoint with all algorithms packed into `ssh_audit_json`. The JWT scanner is the exception (one row per key), but that worked because JWT keys are independent signing entities. For identity protocols, the endpoint/domain is the natural unit. The JSON blob captures all algorithm detail.

### Pattern 3: Agentless Probe Posture

**What:** All three identity scanners must operate without credentials and without installing anything on the target.

**Kerberos:** Send an unauthenticated AS-REQ (with `KDC_ERR_PREAUTH_REQUIRED` expected as the normal reply). The KDC returns `PA-ETYPE-INFO2` in the error, which lists supported etypes — no credentials needed. This is the same technique used by AS-REP roasting tools, used here in read-only passive mode.

**SAML:** HTTP GET to publicly-accessible metadata endpoints (`/saml2/idp/metadata`, `/FederationMetadata/2007-06/FederationMetadata.xml`, Keycloak's `/realms/{realm}/protocol/saml/descriptor`). No auth. Parse XML with `lxml`. Also probe OIDC well-known (`/.well-known/openid-configuration`) — already partially covered by `jwt_scanner.py` but should be extended here for the IdP signing algorithm declared in `id_token_signing_alg_values_supported`.

**DNSSEC:** DNS queries over UDP/TCP with the `DO` (DNSSEC OK) bit set. `dnspython` handles this natively. No credentials. No agents.

---

## Data Flow: Scan → SQLite → CBOM → Dashboard

### Kerberos Flow

```
KDC :88 (TCP/UDP)
    ↓ AS-REQ (no preauth, etype list [1..23])
    ↓ KRB-ERROR (KDC_ERR_PREAUTH_REQUIRED)
    ↓ PA-DATA contains PA-ETYPE-INFO2
kerberos_scanner.py parses etype numbers
    → CryptoEndpoint(
        host=kdc_host, port=88,
        protocol="KERBEROS",
        service_detail=realm,
        kerberos_scan_json=json.dumps(result)
      )
    → stored in SQLite

build_cbom() Pass 1, branch ep.protocol == "KERBEROS":
    → parse kerberos_scan_json
    → map etype numbers to algorithm names:
        17 → "AES128-CTS-HMAC-SHA1-96"
        18 → "AES256-CTS-HMAC-SHA1-96"
        23 → "RC4-HMAC"
        1  → "DES-CBC-CRC"
        3  → "DES-CBC-MD5"
    → call _register_algorithm() for each

build_cbom() Pass 3, branch "KERBEROS":
    → emit ProtocolProperties(type=ProtocolPropertiesType.OTHER, ...)
    (no native Kerberos type in CycloneDX 1.6 — use OTHER with name="Kerberos")

_derive_findings():
    → ep.kerberos_scan_json parsed
    → if has_rc4: HIGH finding "RC4-HMAC Kerberos etype enabled (etype 23)"
    → if has_des: CRITICAL finding "DES Kerberos etype enabled (etype 1 or 3)"
    → if not has_aes256 and not has_aes128: MEDIUM "No AES Kerberos etypes configured"

_derive_cbom():
    → new branch for ep.protocol == "KERBEROS"
    → read etype algorithm names from kerberos_scan_json, call _qs_for_alg()
```

### SAML/OAuth Flow

```
IdP metadata URL (HTTP GET, no auth)
    ↓ XML metadata or JSON discovery document
saml_scanner.py parses:
    → lxml for SAML XML (ds:X509Certificate → extract cert, read sig alg URI)
    → httpx for OIDC JSON (id_token_signing_alg_values_supported, jwks_uri)
    → CryptoEndpoint(
        host=parsed_hostname, port=443,
        protocol="SAML",
        cert_pubkey_alg=extracted_alg,   # e.g. "RSA"
        cert_pubkey_size=cert_bits,
        cert_subject=cert_subject,
        saml_scan_json=json.dumps(result)
      )

build_cbom() Pass 1, branch ep.protocol == "SAML":
    → parse saml_scan_json
    → register idp_signing_cert_algo (cert key type)
    → register each value from oidc_id_token_signing_alg_values (JWT alg strings)
    → existing JWT alg mappings in _ALGORITHM_TABLE handle RS256/ES256/etc.

build_cbom() Pass 2 (certificates):
    → SAML endpoints have cert_pubkey_alg set → cert component emitted normally
    → no new code needed here

_derive_findings():
    → if idp_signing_cert_algo == "RSA" and bits < 2048: CRITICAL
    → if "none" in oidc_id_token_signing_alg_values: CRITICAL
    → if "HS256" in oidc_id_token_signing_alg_values (shared secret): MEDIUM
    → quantum_risk from classify_algorithm() on cert algo
```

### DNSSEC Flow

```
DNS resolver (UDP 53 / TCP 53, DO bit set)
    ↓ DNSKEY query for target domain
    ↓ DS query for target domain
dnssec_scanner.py via dnspython:
    → dns.resolver.resolve(domain, "DNSKEY")
    → dns.resolver.resolve(domain, "DS")
    → CryptoEndpoint(
        host=domain, port=53,
        protocol="DNSSEC",
        service_detail=f"DNSKEY algorithms: {algo_list}",
        dnssec_scan_json=json.dumps(result)
      )

build_cbom() Pass 1, branch ep.protocol == "DNSSEC":
    → parse dnssec_scan_json
    → map DNSSEC algorithm numbers to canonical names:
        1  → "RSAMD5"
        5  → "RSASHA1"
        7  → "RSASHA1-NSEC3-SHA1"
        8  → "RSASHA256"
        10 → "RSASHA512"
        13 → "ECDSAP256SHA256"
        14 → "ECDSAP384SHA384"
        15 → "ED25519"
        16 → "ED448"
    → call _register_algorithm() for each DNSKEY record's algorithm

_derive_findings():
    → if not signed: HIGH "DNSSEC not enabled for domain"
    → if algo 1 (RSAMD5): CRITICAL "RSAMD5 DNSKEY algorithm (RFC 8624 MUST NOT)"
    → if algo 3 (DSA): CRITICAL "DSA DNSKEY algorithm (RFC 8624 MUST NOT)"
    → if algo 5 or 7 (RSASHA1): HIGH "RSASHA1 DNSKEY algorithm (RFC 8624 NOT RECOMMENDED)"
    → quantum_risk set for all RSA/ECDSA-based algorithms
```

---

## New and Modified Components — Explicit List

### New Files

| File | What It Does |
|------|-------------|
| `quirk/scanner/kerberos_scanner.py` | AS-REQ probe, parses ETYPE-INFO2, returns `CryptoEndpoint` rows with `protocol="KERBEROS"` |
| `quirk/scanner/saml_scanner.py` | Fetches SAML XML metadata + OIDC well-known, extracts signing cert and algorithm declarations, returns `CryptoEndpoint` rows with `protocol="SAML"` |
| `quirk/scanner/dnssec_scanner.py` | Queries DNSKEY + DS records via dnspython, classifies per RFC 8624, returns `CryptoEndpoint` rows with `protocol="DNSSEC"` |
| `quantum-chaos-enterprise-lab/kerberos/` | Samba DC init scripts for chaos lab `kerberos` profile |
| `quantum-chaos-enterprise-lab/saml/` | SimpleSAMLphp config overrides for chaos lab `saml` profile |
| `quantum-chaos-enterprise-lab/dnssec/` | BIND9 zone files with RC4-signed and SHA1-signed zones for chaos lab `dnssec` profile |

### Modified Files

| File | What Changes |
|------|-------------|
| `quirk/models.py` | Add `kerberos_scan_json`, `saml_scan_json`, `dnssec_scan_json` columns (Text, nullable) |
| `quirk/config.py` | Add `enable_kerberos: bool = False`, `enable_saml: bool = False`, `enable_dnssec: bool = False`, `kerberos_targets: list`, `saml_targets: list`, `dnssec_targets: list` to `ConnectorsCfg` |
| `quirk/cbom/classifier.py` | Add Kerberos etype algorithm names + DNSSEC algorithm names to `_ALGORITHM_TABLE` |
| `quirk/cbom/builder.py` | Add `KERBEROS`, `SAML`, `DNSSEC` branches in Pass 1 (algorithms) and Pass 3 (protocol components) |
| `quirk/intelligence/evidence.py` | Add identity protocol counters to evidence dict |
| `quirk/intelligence/scoring.py` | Add `identity_weak_etype_ratio` and `identity_dnssec_coverage` weights (optional; these may surface only as findings, not score inputs, in v4.2) |
| `quirk/dashboard/api/routes/scan.py` | Add identity finding derivation logic; add identity_findings section to response |
| `quirk/dashboard/api/schemas.py` | Add `IdentityTabData` schema if the Identity tab needs a dedicated response shape; minimal change otherwise |
| `quantum-chaos-enterprise-lab/docker-compose.yml` | Add `kerberos`, `saml`, `dnssec` profile service entries |

---

## Build Order (Phase Dependencies)

The dependencies between components constrain the build order. Build phases must respect this:

```
Phase A: Schema (models.py) + Config (config.py)
    ↓
Phase B: Scanner modules (kerberos, saml, dnssec)
    ↓
Phase C: CBOM pipeline updates (classifier.py, builder.py)
    ↓
Phase D: Intelligence layer updates (evidence.py, scoring.py)
    ↓
Phase E: Dashboard (routes/scan.py, schemas.py, React Identity tab)
    ↓
Phase F: Chaos lab profiles (kerberos, saml, dnssec Docker services)
```

**Rationale:**
- Scanners import from `models.py` — schema must exist first.
- `build_cbom()` consumes scanner output via `CryptoEndpoint` protocol field — scanner protocol strings must be decided before builder branches.
- `compute_readiness_score()` consumes evidence dict — evidence.py changes must precede scoring.py weight additions.
- Dashboard reads from SQLite and calls CBOM pipeline — all upstream must work before surfacing in UI.
- Chaos lab can be built in parallel with dashboard (Phase E/F) since it is test infrastructure, not a dependency for any production path.

**Recommended v4.2 phase structure:**

| Phase | Components | Notes |
|-------|-----------|-------|
| v4.2-P1 | `models.py` + `config.py` + migration guard | Foundation; unblocks all other phases |
| v4.2-P2 | `kerberos_scanner.py` + `classifier.py` (Kerberos entries) + `builder.py` (KERBEROS branch) | Self-contained scanner unit |
| v4.2-P3 | `saml_scanner.py` + `builder.py` (SAML branch) | JWT alg strings already classified; minimal classifier changes |
| v4.2-P4 | `dnssec_scanner.py` + `classifier.py` (DNSSEC algo entries) + `builder.py` (DNSSEC branch) | Self-contained DNS audit unit |
| v4.2-P5 | `evidence.py` + `scoring.py` + `routes/scan.py` + `schemas.py` + React Identity tab | All scanners must exist; integrate and surface |
| v4.2-P6 | Chaos lab: `kerberos` profile (Samba DC) + `saml` profile (SimpleSAMLphp) + `dnssec` profile (BIND9) | Can overlap with P5; validates all three scanners end-to-end |

---

## Technology Decisions — New Dependencies

### Kerberos Scanner: impacket

**Use `impacket` (fortra/impacket, Apache license).** It provides `impacket.krb5.asn1` with AS-REQ/AS-REP/ETYPE-INFO2 ASN.1 structures and `impacket.krb5.kerberosv5.sendReceive()` for raw KDC communication. This is the de facto standard for Kerberos protocol work in Python, widely deployed in security tooling, pip-installable (`pip install impacket`).

**Alternative rejected: raw socket + pure ASN.1 construction.** Building AS-REQ from scratch with pyasn1 is 200+ lines of fragile byte manipulation for no gain. Impacket already has it all.

**Alternative considered: `krb5` (pkinit-tools fork).** Lighter than impacket but much smaller ecosystem and less maintained. Impacket is the right choice.

**Caveats:** Impacket is a large dependency with many sub-packages. Import only `impacket.krb5.*` to keep the footprint bounded. If impacket proves problematic for offline deployments, the fallback is a minimal raw socket implementation — flag this in PITFALLS.md.

### SAML Scanner: lxml + httpx (already present)

**Use `lxml` for SAML XML metadata parsing.** It is the only library that handles XML namespaces correctly for SAML metadata (`md:EntityDescriptor`, `ds:X509Certificate`, `md:IDPSSODescriptor`). The `xml.etree.ElementTree` stdlib module does not reliably preserve namespace-qualified attribute names in SAML metadata.

**Use `httpx` (already a project dependency from `jwt_scanner.py`) for metadata URL fetching.**

**No need for pysaml2.** The scanner only needs to read/parse IdP metadata, not implement SP/IdP logic. Full SAML stack libraries (pysaml2, python-saml) are overkill and bring heavy dependencies.

**For OIDC:** httpx GET to `/.well-known/openid-configuration`, parse JSON — already the pattern in `jwt_scanner.py`. The SAML scanner should call `jwks_uri` from OIDC discovery to cross-check signing algorithms. Reuse `_fetch_jwks()` logic from `jwt_scanner.py` or import it directly.

### DNSSEC Scanner: dnspython

**Use `dnspython` (>=2.4.0).** It is the only production-quality DNS library for Python, pip-installable, and has direct DNSSEC support including:
- `dns.resolver.resolve(name, "DNSKEY", want_dnssec=True)` — fetches DNSKEY RRset with RRSIG
- `dns.resolver.resolve(name, "DS")` — fetches DS records
- `dns.dnssec.algorithm_from_text()` / `dns.dnssec.algorithm_to_text()` — maps numbers to names
- RFC 8624 policy classification is not built-in to dnspython — implement a local lookup table mapping algorithm numbers to RFC 8624 status (MUST NOT, NOT RECOMMENDED, RECOMMENDED, etc.)

**Alternative rejected: dig subprocess.** Brittle, requires dig binary, output parsing is error-prone. dnspython is the correct Python-native approach.

### Chaos Lab Docker Images

**Kerberos profile — use `itherz/samba-ad-dc`.**
This Docker image provides Samba 4 with full AD, DNS, and Kerberos KDC. It is the most actively maintained option. The Samba DC must be configured to allow RC4-HMAC (etype 23) in its `smb.conf` (`kerberos encryption types = all`). Seed the lab with a test user account so AS-REQ probes get `KDC_ERR_PREAUTH_REQUIRED` responses containing ETYPE-INFO2 data.

**Why not Keycloak for Kerberos?** Keycloak does not implement native Kerberos KDC. It can act as a Kerberos SPNEGO broker but does not expose port 88. Samba is the correct image for AS-REQ etype enumeration against an actual KDC.

**SAML profile — use `kenchan0130/simplesamlphp`.**
This image is based on the official PHP8 Apache image with SimpleSAMLphp pre-installed. It exposes an IdP metadata endpoint at `/simplesaml/saml2/idp/metadata.php`. Default configuration uses RSA-SHA256 signing. For chaos lab coverage, configure it with a 1024-bit RSA signing key (weak) to generate a detectable finding. The image accepts `SIMPLESAMLPHP_SP_*` environment variables for configuration.

**Why not Keycloak here?** The existing chaos lab already has Keycloak in the `identity` profile. Adding a second Keycloak instance wastes memory and creates port conflicts. SimpleSAMLphp is lighter and its metadata endpoint is simpler to target. The `saml` profile scanner also needs to probe Keycloak's OIDC discovery endpoint — that is already available in the `identity` profile, so the `saml` profile scan can be directed at `keycloak-tls:15449`.

**DNSSEC profile — use `internetsystemsconsortium/bind9` (official ISC BIND9 image).**
BIND9 supports inline DNSSEC signing and can be configured with both deprecated algorithms (RSASHA1, algorithm 5) and recommended algorithms (ECDSAP256SHA256, algorithm 13) to produce chaos lab zones that trigger findings. A zone file seeded with RSA-SHA1 DNSKEY records creates a reproducible `RSASHA1` finding. A second zone signed with ECDSAP256SHA256 provides the clean baseline.

**Alternative for DNSSEC:** `mvance/unbound` is a resolver, not an authoritative server. The scanner targets authoritative servers via direct `DNSKEY` queries. BIND9 is the correct choice.

---

## Schema Migration Strategy

**Use SQLAlchemy `create_all` with additive columns only.** The project uses `Base.metadata.create_all(engine)` (see `db.py:init_db()`), which on SQLite adds new tables but does not add new columns to existing tables.

**Required: migration guard in `db.py` or a new `migrate.py`.** For each new `*_scan_json` column, run `ALTER TABLE crypto_endpoints ADD COLUMN kerberos_scan_json TEXT;` guarded by a check for column existence. This is the correct pattern for SQLite additive migrations without Alembic.

Pattern (already validated as the correct v4.x approach per `PROJECT.md` constraints):

```python
def _ensure_column(conn, table: str, column: str, col_type: str):
    result = conn.execute(text(f"PRAGMA table_info({table})"))
    cols = {row[1] for row in result}
    if column not in cols:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
```

Call this for `kerberos_scan_json TEXT`, `saml_scan_json TEXT`, `dnssec_scan_json TEXT` in `init_db()` after `create_all()`.

---

## CBOM Classifier Additions

New entries required in `_ALGORITHM_TABLE` in `classifier.py`:

```
# Kerberos encryption types (RFC 3961 etype numbers → canonical names)
"aes256-cts-hmac-sha1-96"    → (CryptoPrimitive.AE, 0, 256)   # etype 18 — AES quantum-vulnerable
"aes128-cts-hmac-sha1-96"    → (CryptoPrimitive.AE, 0, 128)   # etype 17
"rc4-hmac"                   → (CryptoPrimitive.AE, 0, 128)   # etype 23 — RC4 deprecated RFC 8429
"des-cbc-crc"                → (CryptoPrimitive.BLOCK_CIPHER, 0, 56)  # etype 1 — DES
"des-cbc-md5"                → (CryptoPrimitive.BLOCK_CIPHER, 0, 56)  # etype 3 — DES

# DNSSEC algorithms (IANA numbers → canonical names, classified per quantum risk)
"rsamd5"                     → (CryptoPrimitive.SIGNATURE, 0, 112)   # alg 1
"rsasha1"                    → (CryptoPrimitive.SIGNATURE, 0, 112)   # alg 5
"rsasha1-nsec3-sha1"         → (CryptoPrimitive.SIGNATURE, 0, 112)   # alg 7
"rsasha256"                  → (CryptoPrimitive.SIGNATURE, 0, 112)   # alg 8
"rsasha512"                  → (CryptoPrimitive.SIGNATURE, 0, 112)   # alg 10
"ecdsap256sha256"            → (CryptoPrimitive.SIGNATURE, 0, 128)   # alg 13
"ecdsap384sha384"            → (CryptoPrimitive.SIGNATURE, 0, 192)   # alg 14
"ed25519" already present                                            # alg 15
"ed448"   already present                                            # alg 16
```

Note: All current DNSSEC signing algorithms (RSA variants, ECDSA, EdDSA) are `nist_level=0` (quantum-vulnerable). No DNSSEC algorithms are PQC-safe. This is an accurate representation — NIST has not standardized PQC-safe DNSSEC algorithms as of 2026. The classifier correctly flags all DNSSEC signing as quantum-vulnerable, which is the finding QU.I.R.K. should surface.

---

## Dashboard: Identity Tab Design

### API Response Extension

Extend `ScanLatestResponse` in `schemas.py` with an optional `identity_findings` list. Maintain backward compatibility — frontend can render the Identity tab only when the list is non-empty.

```python
class IdentityFinding(BaseModel):
    id: Optional[int] = None
    host: str
    port: int
    protocol: str          # "KERBEROS" | "SAML" | "DNSSEC"
    severity: str          # CRITICAL / HIGH / MEDIUM / LOW / INFO
    title: str
    description: Optional[str] = None
    remediation: Optional[str] = None
    quantum_risk: Optional[str] = None
    # Protocol-specific detail
    realm: Optional[str] = None       # Kerberos realm
    entity_id: Optional[str] = None   # SAML entity ID
    domain: Optional[str] = None      # DNSSEC domain
```

### React Identity Tab Structure

The Identity tab should display three sub-sections (collapsible or tabbed):
- **Kerberos** — table with KDC endpoint, realm, supported etypes, RC4/DES flags
- **SAML/OAuth** — table with IdP entity ID or OIDC issuer, signing cert algorithm and key size, declared token signing algorithms
- **DNSSEC** — table with domain, DNSKEY algorithms present (color-coded by RFC 8624 status), signed/unsigned status

The tab should be hidden (not rendered) when no identity endpoints have been scanned. This mirrors how the CBOM viewer and cert inventory tabs behave with empty data.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Separate Identity Table

**What people do:** Create a new `identity_endpoints` SQLite table for identity scanner results, independent of `crypto_endpoints`.

**Why it's wrong:** Breaks the single-table CBOM pipeline. `build_cbom()` iterates `list[CryptoEndpoint]`. Adding a second table requires either a join query or duplicating all CBOM, scoring, and finding derivation logic. The v4.1 codebase has zero precedent for multi-table scanner output.

**Do this instead:** Add three nullable JSON columns to `crypto_endpoints`. The `protocol` discriminator field already handles heterogeneous scanner types in a single table.

### Anti-Pattern 2: New Classify Functions per Protocol

**What people do:** Add `classify_kerberos_etype()`, `classify_dnssec_algorithm()` as separate functions that return different types.

**Why it's wrong:** The CBOM builder, dashboard CBOM viewer, and intelligence layer all call `classify_algorithm(name)` and expect a `(CryptoPrimitive, int | None, int | None)` 3-tuple. Adding parallel classification paths means the dashboard CBOM viewer never sees Kerberos/DNSSEC algorithms, the quantum safety labels are inconsistent, and the finding derivation logic duplicates quantum risk assessment.

**Do this instead:** Add the new algorithm strings to `_ALGORITHM_TABLE` in `classifier.py`. One function, one lookup table, consistent output.

### Anti-Pattern 3: Kerberos Scanner Requiring Valid Credentials

**What people do:** Implement Kerberos etype detection by attempting a full AS exchange with a test username/password.

**Why it's wrong:** Requires credentials in config (violates consulting model — clients won't give credentials), fails if account is locked, creates auth log noise, and is unnecessary. The AS-REQ probe without preauth data returns `KDC_ERR_PREAUTH_REQUIRED`, which contains the ETYPE-INFO2 pre-auth data listing all supported etypes. No credentials needed.

**Do this instead:** Send AS-REQ with empty `padata` field and parse the `e-data` field from the `KRB-ERROR` response. impacket's `getKerberosTGT()` flow can be adapted; the `GetNPUsers.py` example in impacket shows the minimal AS-REQ construction needed.

### Anti-Pattern 4: Chaos Lab DNSSEC Using External Domains

**What people do:** Point the DNSSEC scanner test at real external domains (e.g., `google.com`) to get real DNSSEC data.

**Why it's wrong:** External dependencies make the chaos lab non-deterministic and non-reproducible. The domain might change algorithms, might be unreachable in air-gapped engagements, and doesn't allow testing deprecated algorithm scenarios.

**Do this instead:** Use BIND9 with a locally-authoritative zone (`chaos.local` or `quirk-lab.internal`) signed with deliberately weak algorithms. The scanner must be configurable to use a custom DNS resolver IP (the lab's BIND9 container) rather than the system resolver.

---

## Integration Points Summary

| Scanner | External Dep | Port | Auth Required | Finds |
|---------|-------------|------|---------------|-------|
| Kerberos | KDC (Samba/AD) | TCP/UDP 88 | None | RC4 (etype 23), DES (etype 1/3), AES128/256 presence |
| SAML | HTTP/HTTPS | 80/443 | None | Signing cert algorithm/size, XML sig alg URI, OIDC token alg values |
| DNSSEC | DNS resolver | UDP/TCP 53 | None | DNSKEY algorithm numbers, DS digest types, signed/unsigned status |

| New Classifier Entries | Category | Count |
|------------------------|----------|-------|
| Kerberos etype names | Symmetric cipher / AE | 5 |
| DNSSEC algorithm names | Signature | 7 (2 already present: ed25519, ed448) |
| Total new entries | — | ~10 |

| New chaos lab profiles | Docker image | Key scenario |
|------------------------|-------------|-------------|
| `kerberos` | `itherz/samba-ad-dc` | RC4-HMAC etype enabled alongside AES |
| `saml` | `kenchan0130/simplesamlphp` | RSA-1024 signing key (weak cert) |
| `dnssec` | `internetsystemsconsortium/bind9` | RSASHA1 zone + ECDSAP256SHA256 zone |

---

## Sources

- RFC 8429 (Deprecate 3DES and RC4 in Kerberos): https://datatracker.ietf.org/doc/html/rfc8429
- RFC 8624 (DNSSEC Algorithm Requirements): https://datatracker.ietf.org/doc/html/rfc8624
- RFC 4120 (Kerberos V5): https://datatracker.ietf.org/doc/html/rfc4120
- RFC 4757 (RC4-HMAC Kerberos, Historic): https://datatracker.ietf.org/doc/html/rfc4757
- IANA DNSSEC Algorithm Numbers: https://www.iana.org/assignments/dns-sec-alg-numbers/dns-sec-alg-numbers.xml
- dnspython DNSSEC documentation: https://dnspython.readthedocs.io/en/latest/dnssec.html
- impacket Kerberos module: https://github.com/fortra/impacket/blob/master/impacket/krb5/kerberosv5.py
- impacket PyPI: https://pypi.org/project/impacket/
- kenchan0130/simplesamlphp Docker Hub: https://hub.docker.com/r/kenchan0130/simplesamlphp/
- itherz/samba-ad-dc Docker Hub: https://hub.docker.com/r/itherz/samba-ad-dc
- RFC 8414 (OAuth 2.0 Authorization Server Metadata): https://datatracker.ietf.org/doc/html/rfc8414
- CycloneDX 1.6 CryptoPrimitive enum (verified via existing classifier.py usage)
- QU.I.R.K. v4.1 codebase (direct inspection):
  - quirk/models.py — CryptoEndpoint schema
  - quirk/cbom/classifier.py — _ALGORITHM_TABLE, classify_algorithm()
  - quirk/cbom/builder.py — build_cbom() protocol branches
  - quirk/scanner/jwt_scanner.py — agentless scanner pattern
  - quirk/config.py — ConnectorsCfg dataclass pattern
  - quirk/db.py — init_db() / create_all() migration approach
  - quantum-chaos-enterprise-lab/docker-compose.yml — profile pattern

---

*Architecture research for: QU.I.R.K. v4.2 Identity Crypto — Kerberos/SAML/DNSSEC integration*
*Researched: 2026-04-08*
