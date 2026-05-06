# QUIRK Near-Term Milestone Roadmap Design

**Date:** 2026-04-06
**Status:** Approved
**Scope:** Five milestones following v3.9 Gap Closure

---

## Context

v3.9 shipped all 36 planned requirements on 2026-04-04. The codebase is at v4.0.0 — pip-installable, 199 tests green, dashboard functional. Two categories of work now compete for attention: a backlog of P0/P1 correctness gaps that undermine first-run trust, and a scanner surface expansion roadmap covering identity, data at rest, data in motion, and API depth.

**Primary driver:** Scanner depth — expand what QUIRK can discover on a real enterprise engagement.
**Sequencing decision:** Fix correctness gaps first (v4.1), then four scanner milestones in order of finding-density on typical enterprise targets.

---

## Overall Structure

| Version | Milestone | Phases | Core Deliverable |
|---------|-----------|--------|-----------------|
| v4.1 | Foundation Polish | 4 | Trustworthy CLI + accurate scoring |
| v4.2 | Identity Crypto | 5 | Kerberos, SAML/OAuth, DNSSEC |
| v4.3 | Data at Rest | 5 | DB, S3/Blob, K8s, Vault |
| v4.4 | Data in Motion | 4 | Email, message brokers |
| v4.5 | API Depth | 4 | OpenAPI, Bearer tokens, active probing |

Scanner milestones follow the sequence: Identity → Data at Rest → Data in Motion → API Depth. This is ordered by finding-density on typical enterprise targets: Kerberos RC4 and weak SSO signing certs appear on almost every AD/SSO environment; database and storage encryption gaps are universally asked about in compliance conversations; email/broker TLS is commonly misconfigured but less universal; API depth closes a specific gap in the existing JWT/API scanner.

---

## Milestone 1: Foundation Polish (v4.1)

**Goal:** Make v4.0.0 trustworthy enough that new scanner output is credible. No new user-visible features — exclusively closes P0/P1 correctness and trust gaps.

### Phase 1 — CLI Correctness

Closes the P0 show-stoppers that break first-run experience:

- **BACK-40:** `quirk init` generates config with wrong field names (`scan.timeout` instead of `scan.timeout_seconds`, `scan.max_workers` instead of `scan.concurrency`, `targets.ips` instead of `targets.include_ips`, wrong connector block structure) — crashes on startup for every new user
- **BACK-41:** `quirk scan` is documented in `config_template.yaml`, `init_cmd.py`, and `docs/getting-started.md` but the subcommand does not exist — argparse errors on first attempt
- **BACK-47:** `quirk init` template contains `https://github.com/[owner]/quirk/...` — the `[owner]` placeholder was never substituted; appears in every generated config file
- **BACK-48:** Version number disagreements — `INTELLIGENCE_VERSION = "4.0.0"` in `writer.py` vs `"3.9.0"` in config default; CBOM stamps `PLATFORM_VERSION = "3.9"` while CLI is `4.0.0`; report headers read `v3.6` and `v3.7` verbatim in client-facing output

### Phase 2 — Interactive Mode Overhaul

Cleans up the interactive mode prompt flow — all changes in one pass to avoid interleaved half-states:

- **BACK-27:** Auto-detect timezone from `datetime.now().astimezone().tzname()` instead of prompting with `America/New_York` default
- **BACK-28:** Remove SNI prompt — hardcode `True` for FQDN targets (SNI must always be True for FQDNs; surfacing as a question implies it is a meaningful choice)
- **BACK-29:** Remove the Windows ADCS stub prompt — it is labeled `(stub)` and does nothing; prompting for non-functional features erodes trust. (Note: AWS and Azure prompts are NOT removed — see BACK-38.)
- **BACK-38:** Fix AWS and Azure connector prompts — currently mislabeled `(stub)` despite being fully implemented connectors; relabel correctly, add credential requirement warnings, surface `aws_region` and `aws_profile` config fields that are currently never prompted for
- **BACK-32:** Surface JWT, container, and source scanners in interactive mode — these are fully implemented but unreachable interactively
- **BACK-30:** Replace raw `timeout_seconds` and `concurrency` prompts with a single scan profile selection (`quick/standard/deep`) — delegate to existing `apply_profile()`
- **BACK-33:** Expand TLS port defaults to consulting-grade list (add LDAPS 636/3269, IMAPS/POP3S/SMTPS 993/995/465, Kubernetes API 6443, Docker TLS 2376, common DB TLS ports 5432/3306/1433, Vault 8200); remove interactive port prompt
- **BACK-36:** Reorder interactive prompts targets-first (currently: metadata → tuning → targets; correct: targets → options → output → metadata)
- **BACK-39:** Remove `enable_windows_adcs` dead config field and its prompt — never checked in `run_scan.py`; remove until ADCS scanner ships
- **BACK-31:** Consolidate `data_classification` and `data_types` into a single coherent block — currently two overlapping prompts for the same question

### Phase 3 — Scoring & Intelligence Correctness

- **BACK-43:** Scoring calibration profile (`lenient/balanced/strict`) is cosmetic — `get_calibration()` never called, `calibration_overrides` loaded then discarded, score weights unchanged regardless of profile setting
- **BACK-44:** `validate.py` checks for `assessment-*.json` and `calibration-*.json` which `write_reports()` never produces — every scan permanently fails validation
- **BACK-46:** `migration_advisor.py` matches `"deprecated tls"` and `"public key"` strings that don't appear in `risk_engine.py` finding titles — migration recommendations for legacy TLS are silently skipped
- **BACK-60:** Dashboard `api/routes/scan.py:330` calls `compute_readiness_score(evidence)` without `profile=` kwarg — always uses `balanced` default regardless of scan-time profile; a `strict` profile user sees different scores in dashboard vs CLI report

### Phase 4 — Code Hygiene

- **BACK-37:** Remove `quirk/connectors/` legacy stub directory (`aws_stub.py`, `azure_stub.py`, `windows_adcs_stub.py`) — never imported; real implementations live in `quirk/scanner/`; presence implies wrong implementations are the connectors
- **BACK-45:** Guard `cfg.scan` in-place mutation with `try/finally` — `run_scan.py` mutates `timeout_seconds` and `concurrency` around TLS/SSH phases without cleanup; exceptions leave downstream phases with wrong values
- **BACK-61:** Delete orphaned `quirk/reports/scorecard.py` — `build_scorecard_markdown()` never called in production; `writer.py` uses its own inline `_scorecard_markdown()`; also missing `profile=` kwarg
- **BACK-62:** Update 9 stale + 2 missing Nyquist `VALIDATION.md` files — stale `nyquist_compliant: false` / `wave_0_complete: false` from planning time; all phase verifications passed GREEN; run `/gsd:validate-phase N` for each

---

## Milestone 2: Identity Crypto (v4.2)

**Goal:** Surface quantum vulnerabilities in Kerberos (AD), SAML/OAuth (SSO), and DNSSEC — the three identity-layer crypto surfaces that are currently invisible to QUIRK and present on almost every enterprise network.

### Phase 1 — Kerberos Encryption Type Enumeration

Send AS-REQ probes to Kerberos ports (88/TCP+UDP) on discovered targets. Enumerate supported encryption types from the `KRB5KDC_ERR_C_PRINCIPAL_UNKNOWN` error response (which lists supported etypes without credentials):

- etype 3: DES — `nist_level=0`, critical
- etype 23: RC4/arcfour-hmac — `nist_level=0`, high (default in millions of AD environments)
- etype 17: AES-128 — `nist_level=1`
- etype 18: AES-256 — `nist_level=2`

Maps to CBOM as algorithm components with `source_type=IDENTITY`. RC4 present alongside AES is a specific finding pattern (downgrade possible) distinct from RC4-only.

### Phase 2 — SAML / OAuth Metadata Scanning

Probe well-known metadata paths on discovered HTTPS endpoints:
- SAML: `/saml/metadata`, `/saml2/metadata`, `/FederationMetadata/2007-06/FederationMetadata.xml`
- OAuth/OIDC: `/.well-known/openid-configuration`, `/.well-known/oauth-authorization-server`

Parse signing certificates (extract key type and size) and algorithm declarations from XML/JSON responses. No authentication required — all public metadata. Findings: RSA-1024 signing cert, SHA-1 assertion signing, quantum-vulnerable JWT algorithms declared in OAuth server metadata.

### Phase 3 — DNSSEC Algorithm Audit

For each FQDN target, query DNSKEY and DS records via `dnspython`. Enumerate signing algorithm:
- Algorithm 5/7: RSASHA1 — quantum-vulnerable
- Algorithm 8: RSASHA256 — classical strong, quantum-vulnerable
- Algorithm 13: ECDSA P-256 — preferred
- Algorithm 15: Ed25519 — preferred

Flag unsigned zones as a separate finding. Maps to CBOM as infrastructure-level algorithm components.

### Phase 4 — Identity Chaos Lab

Two new docker-compose profiles following existing chaos lab patterns:

- **ad-sim:** Samba in DC mode configured to advertise both RC4 (etype 23) and AES-256 on port 88 — exercises the Kerberos scanner and produces a "RC4 downgrade possible" finding
- **saml-idp:** Keycloak or SimpleSAMLphp with an RSA-1024 signing cert and SHA-1 assertion signing — exercises the SAML metadata scanner

### Phase 5 — CBOM Integration & Docs

- Wire `IDENTITY` source type through CBOM builder (Pass 3 `elif` block, matching the existing TLS/SSH/JWT/CONTAINER/SOURCE/AWS/AZURE pattern)
- Update CBOM compliance guide with Kerberos and SSO findings interpretation
- Add connector docs for Kerberos, SAML/OAuth, and DNSSEC scanners
- Update chaos lab guide with two new profiles

---

## Milestone 3: Data at Rest (v4.3)

**Goal:** Answer "are your databases and storage encrypted?" — the first question in most compliance conversations. QUIRK currently knows about KMS keys but has no visibility into whether they protect anything.

### Phase 1 — Database Encryption Detection

Probe on-prem and cloud databases:
- **PostgreSQL:** SSH + `psql -c "SHOW ssl"` and `pg_hba.conf` inspection for `hostssl` entries
- **MySQL/MariaDB:** SSH + `mysql -e "SHOW VARIABLES LIKE 'have_ssl'"` and `SHOW STATUS LIKE 'Ssl_cipher'`
- **RDS:** Existing boto3 session + `describe_db_instances` for `StorageEncrypted` flag and `CACertificateIdentifier`

Findings: unencrypted database (critical), SSL disabled in transit, TLS below 1.2 on database connection. Maps to CBOM as data-store components with algorithm annotation (or absence).

### Phase 2 — S3 / Blob Storage Encryption Audit

Extends existing cloud connectors:
- **AWS:** `get_bucket_encryption` per bucket — classifies SSE-S3 (AES-256 AWS-managed), SSE-KMS (links to existing KMS findings by key ARN), or no encryption (critical finding)
- **Azure:** Blob Storage service properties — CMK vs platform-managed key
- **GCS:** Bucket metadata `defaultKmsKeyName` presence

Single API call per bucket. High finding yield for cloud-heavy clients; links S3 encryption findings back to the KMS key inventory already in CBOM.

### Phase 3 — Kubernetes Secrets At Rest

Inspect etcd encryption configuration:
- Via kubeconfig: read API server pod manifest or `encryption-config.yaml` via SSH on control plane node
- Parse `EncryptionConfiguration` resource for provider type per resource

Provider findings: `identity` (plaintext — critical), `aescbc` (encrypted, classical), `aesgcm` (encrypted, classical), `secretbox` (preferred), `kms` (links to existing KMS scanner). Critical finding for cloud-native clients.

### Phase 4 — HashiCorp Vault Live Connector

Connect via Vault API token (from config). Enumerate:
- Secret engines and their KV/transit/PKI types
- Transit key specs: key type, key bits, rotation policy, exportable flag
- PKI mount signing algorithms and cert chain
- Auth method crypto configuration (token TTL, TLS cert auth)

Produces the richest CBOM output of the milestone. Vault chaos lab target already exists from Phase 4 of v3.9.

### Phase 5 — Data at Rest Chaos Lab & Docs

New chaos lab profiles:
- **db-unencrypted:** PostgreSQL with `ssl = off` in `postgresql.conf`
- **minio-nosse:** MinIO S3-compatible store with default bucket, no SSE configured
- **k8s-plaintext:** k3s cluster with `identity` provider in encryption config (secrets plaintext in etcd)

Documentation: connector docs for DB, S3/Blob, K8s, and Vault scanners; "Data at Rest" section in report interpretation guide covering compliance conversation framing.

---

## Milestone 4: Data in Motion (v4.4)

**Goal:** Surface crypto misconfigurations in email and message broker protocols — widely misconfigured in enterprise, missed by every scanner that focuses on HTTPS.

### Phase 1 — Email Protocol Scanning (SMTP / STARTTLS / IMAP / POP3)

Connect to mail ports (25, 465, 587 for SMTP; 143/993 for IMAP; 110/995 for POP3). Issue protocol-specific handshakes before TLS negotiation:
- SMTP: `EHLO quirk-scanner` → parse STARTTLS advertisement → `STARTTLS` → hand off to sslyze
- IMAP: `A001 CAPABILITY` → `A002 STARTTLS` → hand off to sslyze
- POP3: `CAPA` → `STLS` → hand off to sslyze
- Implicit TLS ports (465, 993, 995): connect directly to sslyze

Findings: plaintext accepted on STARTTLS port, TLS below 1.2, weak cipher, expired/self-signed cert. sslyze handles everything after the protocol upgrade — this phase is protocol-specific connection wrappers feeding the existing TLS scanner pipeline.

### Phase 2 — Message Broker TLS (Kafka, RabbitMQ, Redis, AMQP)

Port-based heuristic detection followed by TLS negotiation attempt:
- **Kafka:** 9092 (plaintext — finding if data port is open), 9093 (TLS — sslyze)
- **RabbitMQ:** 5672 (plaintext AMQP — finding), 5671 (AMQP+TLS — sslyze), 15672 (management HTTP — existing TLS scanner)
- **Redis:** 6379 (check `CONFIG GET tls-port` via Redis protocol to detect TLS-capable instances on plaintext), 6380 (TLS — sslyze)
- **AMQP generic:** 5672/5671 same as RabbitMQ pattern

Plaintext-accepting brokers carrying event payloads are critical findings.

### Phase 3 — Data in Motion Chaos Lab

New profiles:
- **smtp-weak:** Postfix configured to advertise STARTTLS but negotiate TLS 1.0 with RC4 cipher suite
- **broker-plaintext:** RabbitMQ plaintext AMQP on 5672 with TLS-enabled 5671 using a misconfigured cert; Redis 6379 with TLS disabled

### Phase 4 — Docs

Email and broker connector docs; "Data in Motion" section in report interpretation guide; update getting-started guide with new scanner types.

---

## Milestone 5: API Depth (v4.5)

**Goal:** Close the three gaps in QUIRK's existing JWT/API scanner — spec-declared algorithms (OpenAPI), tokens actually in use (Bearer interception), and endpoint crypto under active probing.

### Phase 1 — OpenAPI / Swagger Spec Analysis

Fetch specs from well-known paths (`/openapi.json`, `/swagger.json`, `/api-docs`, `/v2/api-docs`) or accept local file paths in config. Parse:
- `securitySchemes` → extract declared algorithms (RS256, HS256, ES256, etc.)
- Endpoints with no `security` declaration → unauthenticated endpoint finding
- OAuth2 flows and scopes
- `servers` array → cross-reference with TLS scan results

Produces CBOM components from spec-declared algorithms even without live traffic access. Complements JWKS scanner: JWKS = what keys exist; spec = what algorithms are declared.

### Phase 2 — Bearer Token Interception & Analysis

Two input modes:
- **Passive capture:** Decode Bearer tokens observed in `Authorization` headers during active HTTP probing of in-scope endpoints
- **Sample file:** Accept `--sample-tokens <file>` with client-provided tokens

Decode without verification: extract `alg` header, key size hint, `exp` claim presence and duration, claim structure. Findings: quantum-vulnerable algorithm (RS256, ES256, HS256 with short keys), `alg:none` (critical — authentication bypass), no expiry, excessively long TTL. Maps to CBOM algorithm components with `source_type=JWT` (extends existing JWT scanner source type).

### Phase 3 — Active REST API Fuzzing for Crypto Posture

Scoped to crypto-posture signals only (not general-purpose fuzzing):
- Enumerate authentication schemes observed in responses (Basic, Bearer, API key in header vs query string)
- Flag endpoints transmitting credentials over non-TLS transports
- Detect deprecated TLS versions on REST API endpoints (sslyze already in pipeline)
- Probe for endpoints accepting `Authorization: Bearer invalid_token` with 200 response (missing auth enforcement)

### Phase 4 — API Depth Chaos Lab & Docs

New profiles:
- **api-weak:** Mock API server with `/openapi.json` declaring `HS256` securityScheme and several unauthenticated endpoints; issues JWT tokens with `alg:none` and RS256 with 512-bit key
- Update JWT/API connector doc with three new capabilities
- "API Crypto" section in report interpretation guide distinguishing spec-declared, token-observed, and live-probed findings

---

## Cross-Cutting Constraints

- Every new scanner produces `CryptoEndpoint` rows and CBOM components following existing source type patterns (`TLS`, `SSH`, `JWT`, `CONTAINER`, `SOURCE`, `AWS`, `AZURE`) — new types added as needed (`IDENTITY`, `DATA_AT_REST`, `EMAIL`, `BROKER`)
- Every milestone includes a chaos lab phase for scanner validation (same docker-compose pattern as v3.9 Phase 4)
- Every milestone includes a docs phase updating connector guides and report interpretation guide
- Each new scanner integrates with the existing `classify_algorithm()` → `quantum_safety_label()` pipeline — no new scoring paths
- sslyze is reused as the TLS inspection engine wherever a protocol upgrade lands on a TLS session (email, broker, API) — protocol-specific wrappers feed the existing pipeline

---

## Backlog Items Not In Scope

The following backlog items were reviewed and excluded from these five milestones:

- **BACK-01 through BACK-07** (dashboard UI enhancements — config panel, multi-scan navigation, heatmap, light/dark mode, PDF formatting, CBOM graph colors, migration roadmap visuals) — deferred to a dedicated dashboard/UX milestone
- **BACK-08** (narrative report onboarding guide) — deferred to documentation milestone
- **BACK-21** (trend analysis across scan sessions) — deferred; natural companion to BACK-02 (multi-scan navigation)
- **BACK-25** (scheduled/continuous scanning) — significant operational mode change; deferred to v5.x
- **BACK-26** (distributed multi-node architecture) — milestone-level platform work; deferred to v5.x
- **BACK-34, BACK-35** (SSH port prompt, tls_enum_mode surface) — P2/P3; deferred to v4.1 if capacity allows
