# Requirements: QU.I.R.K. v4.3 Data at Rest

**Defined:** 2026-04-24
**Core Value:** Produce a complete, defensible cryptographic inventory with a CBOM deliverable and quantum-readiness score that a consultant can hand to a client in under two hours.

## v4.3 Requirements

Requirements for this milestone. Each maps to roadmap phases 25–31.

### Phase 25 Carry-Over (from v4.2)

Requirements already defined in v4.2 — surfaced here for phase planning completeness.
These close NEW-ISSUE-1 (OIDC RS256 mislabeled as TLS-sourced) and ISSUE-2 (ldap3 absent from pyproject.toml).

- [ ] **SAML-04**: OIDC RS256 endpoints produce `IdentityFinding(source="saml")` objects, not TLS-sourced findings
- [ ] **IDENT-02**: Identity findings from OIDC RS256 appear in the Identity tab, not the Findings tab
- [ ] **IDENT-03**: OIDC RS-family algorithms (RS256, RS384, RS512) are classified via `OIDC_ALG_SEVERITY` lookup
- [ ] **KERB-03**: `ldap3>=2.9.1` is included in the `[identity]` extras group and resolves without conflicts
- [ ] **INFRA-03**: `pip install quirk[identity]` installs ldap3; Kerberos LDAP enumeration is no longer always-inert

### GCP Connector

- [ ] **GCP-01**: Scanner can enumerate Cloud KMS key specs with quantum-safety classification (RSA-2048/4096, ECDSA P-256/P-384, AES-256, HMAC-SHA256, external/HSM variants) for a configured GCP project
- [ ] **GCP-02**: Scanner can detect Cloud SQL instance TLS enforcement mode and produce findings for disabled or plaintext-allowed TLS configurations
- [ ] **GCP-03**: Scanner can detect GCS bucket default encryption type (CMEK with customer-managed key vs Google-managed key) across all buckets in a project

### Database Encryption

- [ ] **DB-01**: Scanner can detect PostgreSQL SSL enforcement posture using `pg_stat_ssl` and report plaintext-allowed as a HIGH finding; gracefully degrades without `pg_read_all_stats` role (emits `scan_error` finding rather than crashing)
- [ ] **DB-02**: Scanner can detect MySQL/MariaDB SSL session status and report disabled or weak SSL as a finding with the negotiated cipher if available
- [ ] **DB-03**: RDS scanner extension — detects `StorageEncrypted` flag and `StorageEncryptionType` (none / sse-rds / sse-kms) via existing boto3 session, distinguishing AWS-managed from customer-managed keys

### Object Storage

- [ ] **STOR-01**: Scanner can determine S3 bucket encryption policy per bucket (SSE-S3, SSE-KMS with CMK vs AWS-managed key, unencrypted) across all buckets in a configured AWS account
- [ ] **STOR-02**: Scanner can determine Azure Blob container encryption configuration (platform-managed key vs customer-managed CMK) for a configured Azure subscription
- [ ] **STOR-03**: GCS bucket encryption audit reuses the Phase 26 GCP connector's bucket enumeration — no duplicate GCS bucket list API calls issued in a single scan run

### Kubernetes Secrets

- [x] **K8S-01**: Scanner can detect etcd encryption status on managed clusters (EKS `encryptionConfig`, GKE `databaseEncryption.state`, AKS Key Vault integration) via managed cluster APIs without requiring direct etcd access
- [x] **K8S-02**: Scanner can enumerate Kubernetes Secret type counts (Opaque, `kubernetes.io/tls`, `kubernetes.io/dockerconfigjson`, etc.) for a configured cluster without reading any secret values
- [x] **K8S-03**: Scanner emits an explicit `encryption-config-inaccessible` finding with remediation guidance when etcd encryption state cannot be determined via available managed-cluster APIs

### HashiCorp Vault

- [x] **VAULT-01**: Scanner can enumerate Vault transit engine key types with quantum-safety classification — including PQC key types (`ml-dsa`, `slh-dsa`) emitted as positive quantum-safe findings
- [x] **VAULT-02**: Scanner can detect Vault PKI mount CA certificate algorithm and flag RSA < 4096-bit signing keys or SHA-1 signing algorithms as HIGH findings
- [x] **VAULT-03**: Scanner can list active Vault auth methods and flag higher-risk methods (token, LDAP root bind) as findings with remediation guidance

### Trend Analysis

- [x] **TREND-01**: Intelligence layer computes a readiness score delta between the current scan session and the most recent previous scan session, using the existing `scanned_at` grouping from `list_scans()`
- [x] **TREND-02**: Trend report identifies net-new findings — endpoints or algorithm findings present in the current scan but absent in the previous scan — with counts by severity
- [x] **TREND-03**: Trend report identifies resolved findings — endpoints or algorithm findings present in the previous scan but absent in the current — with counts by severity
- [x] **TREND-04**: Dashboard surfaces trend data: readiness score delta and new/resolved finding counts for the two most recent scan sessions

## Future Requirements

Deferred to v4.4 and beyond. Not in current roadmap.

### v4.4 Data in Motion

- **MOTION-01**: Email protocol scanning — SMTP/STARTTLS, IMAP, POP3 via sslyze handoff
- **MOTION-02**: Message broker TLS — Kafka (9092/9093), RabbitMQ (5672/5671), Redis (6379/6380) TLS negotiation

### Dashboard Polish (v4.5 candidate)

- **DASH-01**: Multi-scan navigation — scan selector dropdown for historical session browsing
- **DASH-02**: Severity heatmap — grid of systems × severity for dense overview
- **DASH-03**: Light/dark mode toggle — parallel token set for light mode
- **DASH-04**: PDF report formatting improvements — cover page, pagination, CBOM visual section

## Out of Scope

Explicitly excluded from v4.3. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| GCP Cloud SQL via Discovery API | Uncertain API path (Discovery API vs dedicated client library unverified); defer to planning-time verification in future milestone |
| Self-hosted K8s direct etcd access | Requires agent installation on etcd nodes — violates agentless constraint |
| Vault root token audit | Requires audit log read access; not available agentlessly in most deployments |
| PostgreSQL without pg_read_all_stats | pg_stat_ssl only shows scanner's own connection without this role — misleading result; emit scan_error instead |
| SAML/Kerberos/DNSSEC chaos lab additions | Identity chaos lab profiles already built in v4.2; v4.3 chaos work limited to database/Vault/K8s targets |
| Email / S/MIME scanning | v4.4 Data in Motion milestone |
| Message broker TLS | v4.4 Data in Motion milestone |
| Compliance framework mapping (BACK-20) | Deferred from backlog review — high value but independent milestone |
| Dashboard polish (BACK-02/03/04/05) | Deferred — does not serve data-at-rest goal |
| QRAMM assessment platform (BACK-60–66) | Large independent feature — separate future milestone |
| Windows AD CS live connector | Complex Kerberos/NTLM auth; stub remains, deferred to v2 |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SAML-04, IDENT-02, IDENT-03, KERB-03, INFRA-03 | Phase 25 | Pending |
| GCP-01, GCP-02, GCP-03 | Phase 26 | Pending |
| DB-01, DB-02, DB-03 | Phase 27 | Pending |
| STOR-01, STOR-02, STOR-03 | Phase 28 | Pending |
| K8S-01, K8S-02, K8S-03 | Phase 29 | Pending |
| VAULT-01, VAULT-02, VAULT-03 | Phase 30 | Pending |
| TREND-01, TREND-02, TREND-03, TREND-04 | Phase 31 | Pending |

**Coverage:**
- v4.3 requirements: 24 total (5 carry-over + 19 new)
- Mapped to phases: 24
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-24*
*Last updated: 2026-04-24 after initial definition*
