# Requirements: QU.I.R.K.

**Defined:** 2026-04-08
**Core Value:** Produce a complete, defensible cryptographic inventory with a CBOM deliverable and quantum-readiness score that a consultant can hand to a client in under two hours.

## v4.2 Requirements

Requirements for the v4.2 Identity Crypto milestone. Each maps to roadmap phases.

### Infrastructure

- [x] **INFRA-01**: SQLite schema gains `kerberos_scan_json`, `saml_scan_json`, `dnssec_scan_json` nullable columns with idempotent `ALTER TABLE ADD COLUMN` guard in `db.py` startup
- [x] **INFRA-02**: `ConnectorsCfg` gains `enable_kerberos`, `enable_saml`, `enable_dnssec` flags and corresponding target list fields wired to `config.yaml`
- [x] **INFRA-03**: `pyproject.toml` gains `[identity]` optional extras group declaring `impacket>=0.13.0,<0.14`, `dnspython[dnssec]>=2.8.0`, `lxml>=6.0`, `defusedxml>=0.7.1`, `signxml>=4.4.0`

### DNSSEC

- [x] **DNSSEC-01**: Scanner queries `DNSKEY` and `DS` records via dnspython with `DO` bit set against authoritative nameservers directly (not system resolver)
- [x] **DNSSEC-02**: Algorithm classification per RFC 8624 / RFC 9905 — RSASHA1 (alg 5) and RSASHA1-NSEC3-SHA1 (alg 7) flagged as CRITICAL
- [x] **DNSSEC-03**: Unsigned zone (missing DNSSEC) detected and flagged as HIGH severity
- [x] **DNSSEC-04**: Results stored in `dnssec_scan_json` with `protocol="DNSSEC"` CryptoEndpoints; `DNSSEC_ALG_MAP` added to classifier; `build_cbom()` gains DNSSEC `elif` branches
- [x] **DNSSEC-05**: NSEC vs NSEC3 record type detected; NSEC flagged as zone-enumerable exposure
- [x] **DNSSEC-06**: DS broken chain detection — mismatched key tags between DS and DNSKEY records flagged as HIGH
- [x] **DNSSEC-07**: Chaos lab gains BIND9 `dnssec` Docker Compose profile with RSASHA1-signed zone and ECDSAP256SHA256 zone for scanner validation

### SAML

- [ ] **SAML-01**: Scanner fetches and parses SAML IdP metadata XML for signing and encryption certificate key type, size, and expiry using lxml with explicit `SAML_NS` namespace constant
- [ ] **SAML-02**: Scanner parses `<KeyDescriptor use="encryption">` certs separately from signing certs, extracting key size findings for each
- [ ] **SAML-03**: Scanner parses OIDC discovery endpoint for `id_token_signing_alg_values_supported` and `request_object_signing_alg_values_supported`
- [ ] **SAML-04**: RSA < 2048-bit signing keys flagged as CRITICAL; SHA-1 algorithm URIs flagged as HIGH
- [ ] **SAML-05**: Results stored in `saml_scan_json` with `protocol="SAML"` CryptoEndpoints; classifier updated with SAML algorithm URI strings; `build_cbom()` gains SAML `elif` branches
- [ ] **SAML-06**: Chaos lab gains SimpleSAMLphp `saml` Docker Compose profile with RSA-1024 weak signing cert for scanner validation

### Kerberos

- [ ] **KERB-01**: Scanner sends unauthenticated AS-REQ to port 88 (TCP with UDP fallback) and parses PA-ETYPE-INFO2 from `KDC_ERR_PREAUTH_REQUIRED` response — no credentials required
- [ ] **KERB-02**: RC4-HMAC (etype 23) flagged as HIGH; DES etypes (1, 2, 3) flagged as CRITICAL; AES-256 (etype 18/20) classified as quantum-safe
- [ ] **KERB-03**: Scanner attempts anonymous LDAP bind on port 389 to read `msDS-SupportedEncryptionTypes` attribute; gracefully degrades if unreachable or auth required
- [ ] **KERB-04**: Results stored in `kerberos_scan_json` with `protocol="KERBEROS"` CryptoEndpoints; classifier gains Kerberos etype entries; `build_cbom()` gains KERBEROS `elif` branches
- [ ] **KERB-05**: Chaos lab gains Samba DC `kerberos` Docker Compose profile with RC4-enabled realm and `start_period: 90s` healthcheck

### Identity Surface

- [ ] **IDENT-01**: `evidence.py` gains `identity_weak_etype_count`, `saml_weak_signing_count`, `dnssec_weak_algo_count` counters; `scoring.py` incorporates identity evidence into readiness score
- [ ] **IDENT-02**: FastAPI gains `IdentityFinding` Pydantic model and `identity_findings` array in `GET /api/scan/latest` response
- [ ] **IDENT-03**: React dashboard gains Identity tab with per-protocol summary cards (Kerberos/SAML/DNSSEC) and severity-color-coded findings list
- [ ] **IDENT-04**: Existing findings table includes identity protocol findings with protocol column filter

## Future Requirements

Deferred to v4.3+. Tracked but not in current roadmap.

### Data at Rest (v4.3)

- **DAR-01**: Database encryption detection — PostgreSQL, MySQL, RDS encryption settings
- **DAR-02**: Object storage audit — S3/Blob/GCS encryption-at-rest configuration
- **DAR-03**: Kubernetes secrets inspection — etcd EncryptionConfiguration, secret types
- **DAR-04**: HashiCorp Vault connector — transit keys, PKI mounts, auth method audit

### Data in Motion (v4.4)

- **DIM-01**: Email protocol scanning — SMTP/STARTTLS, IMAP, POP3 via sslyze handoff
- **DIM-02**: Message broker TLS — Kafka, RabbitMQ, Redis, AMQP connection audit

### Identity — Deferred

- **KERB-ADV-01**: Per-account etype probing via `msDS-SupportedEncryptionTypes` LDAP authenticated query (breaks agentless constraint; SaaS model)
- **SAML-ADV-01**: SAML assertion signature validation (requires SP context; SaaS model)
- **DNSSEC-ADV-01**: Post-quantum DNSSEC algorithm support — ML-DSA IANA numbers not yet registered as of 2026
- **DNSSEC-ADV-02**: DNSKEY rollover monitoring (continuous; SaaS feature)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Email / S/MIME scanning | Lower priority vs identity surfaces; deferred to v4.4 |
| Windows AD CS live connector | Complex Kerberos/NTLM auth; stub remains, deferred |
| Network traffic capture (Zeek/Wireshark) | Requires passive tap; out of scope for agentless model |
| OpenVAS / Nessus integration | Full vuln scanner; different scope, heavy dependency |
| Kerberoasting / SPN enumeration | Pentest territory; not a crypto audit |
| Full SAML authentication flow | Requires SP context; agentless model covers metadata read only |
| Mobile app | Web-first; SaaS phase determines mobile need |
| Real-time continuous monitoring | SaaS milestone, not v1 |
| pysaml2 / python3-saml | Require xmlsec1 system binary; violates pip-only constraint |
| impacket in core deps | pyOpenSSL conflict risk; must stay in [identity] optional extras |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 17 | Complete |
| INFRA-02 | Phase 17 | Complete |
| INFRA-03 | Phase 17 | Complete |
| DNSSEC-01 | Phase 18 | Complete |
| DNSSEC-02 | Phase 18 | Complete |
| DNSSEC-03 | Phase 18 | Complete |
| DNSSEC-04 | Phase 18 | Complete |
| DNSSEC-05 | Phase 18 | Complete |
| DNSSEC-06 | Phase 18 | Complete |
| DNSSEC-07 | Phase 18 | Complete |
| SAML-01 | Phase 19 | Pending |
| SAML-02 | Phase 19 | Pending |
| SAML-03 | Phase 19 | Pending |
| SAML-04 | Phase 19 | Pending |
| SAML-05 | Phase 19 | Pending |
| SAML-06 | Phase 19 | Pending |
| KERB-01 | Phase 20 | Pending |
| KERB-02 | Phase 20 | Pending |
| KERB-03 | Phase 20 | Pending |
| KERB-04 | Phase 20 | Pending |
| KERB-05 | Phase 20 | Pending |
| IDENT-01 | Phase 21 | Pending |
| IDENT-02 | Phase 21 | Pending |
| IDENT-03 | Phase 21 | Pending |
| IDENT-04 | Phase 21 | Pending |

**Coverage:**
- v4.2 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-08*
*Last updated: 2026-04-08 after initial definition*
