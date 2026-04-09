# Phase 19: SAML/OIDC Scanner - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 19-SAML/OIDC Scanner
**Areas discussed:** OIDC target config, SAML finding schema, SHA-1 URI detection scope, SimpleSAMLphp chaos lab

---

## OIDC Target Configuration

| Option | Description | Selected |
|--------|-------------|----------|
| Same saml_targets list | Scanner auto-detects XML vs JSON; no new config field | ✓ |
| Separate oidc_targets list | Add `enable_oidc` + `oidc_targets` to ConnectorsCfg | |
| OIDC inferred from SAML | Auto-probe /.well-known on same host as SAML target | |

**User's choice:** Same `saml_targets` list — no new config field needed.
**Notes:** Phase 17 schema is final. Scanner detects type by response Content-Type/structure.

---

## SAML Finding Schema

### CryptoEndpoint service_detail

| Option | Description | Selected |
|--------|-------------|----------|
| entity_id\|use=signing | One row per cert per use-type; no serial | |
| entity_id\|use=signing\|serial | Include cert serial for federation disambiguation | ✓ |
| entity_id only | Collapse certs per IdP | |

**User's choice:** `entity_id|use=signing|serial={serial_hex}` — correct for federated IdPs.
**Notes:** User specifically called out that many enterprise organizations use certificate
rotation/federation with multiple active signing certs. The serial prevents collisions.
Complexity is low: `cryptography.x509.load_der_x509_certificate()` already in core deps.

### OIDC Alg Finding Schema

| Option | Description | Selected |
|--------|-------------|----------|
| One row per alg string | service_detail=oidc-discovery\|id_token_signing_alg | ✓ |
| Single row per OIDC endpoint | Collapsed comma-separated | |
| No CryptoEndpoint for OIDC | Store in JSON only, not CBOM | |

**User's choice:** One row per alg string — preserves per-alg granularity in CBOM.

---

## SHA-1 Algorithm URI Detection Scope

| Option | Description | Selected |
|--------|-------------|----------|
| alg:SigningMethod only | Declared preferred signing algorithms | |
| SignatureMethod + alg:SigningMethod | Both the metadata signature and the declared algs | ✓ |
| All three sources | Above plus cert.signature_hash_algorithm | |

**User's choice:** Two sources: `<ds:SignatureMethod>` + `<alg:SigningMethod>`.

### SHA-1 URI CryptoEndpoint Schema

| Option | Description | Selected |
|--------|-------------|----------|
| One row per URI found | service_detail includes URI and source | ✓ |
| Aggregate into one row per IdP | service_detail includes count | |

**User's choice:** One row per URI occurrence — granular and queryable per finding.

---

## SimpleSAMLphp Chaos Lab

### Cert Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-baked cert committed to repo | Deterministic, same cert every run | ✓ |
| Runtime generation at startup | New cert each run — fragile test assertions | |

**User's choice:** Pre-baked RSA-1024 cert committed to repo.
**Notes:** Matches DNSSEC pre-signed zone approach. Under `quantum-chaos-enterprise-lab/simplesamlphp/cert/`.

### Docker Image

| Option | Description | Selected |
|--------|-------------|----------|
| kenchan0130/simplesamlphp | Official image, PHP 8+, maintained | ✓ |
| kristophjunge/test-saml-idp | Purpose-built test IdP, less maintained | |
| Build from php:apache base | Full control, significant Dockerfile complexity | |

**User's choice:** `kenchan0130/simplesamlphp`.

---

## Claude's Discretion

- Internal helper function naming (`_fetch_metadata`, `_parse_signing_certs`, etc.)
- Exact XPath expressions for each XML field
- Whether `SAML_NS` namespace dict lives in `saml_scanner.py` or a shared `xml_utils.py`
- SimpleSAMLphp authsource configuration details
- Exact env vars and volume mount paths in docker-compose.yml

## Deferred Ideas

None raised during discussion.
