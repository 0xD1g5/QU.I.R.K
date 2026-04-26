---
gsd_state_version: 1.0
milestone: v4.3
milestone_name: Data at Rest
status: ready_to_plan
stopped_at: Phase 31 context gathered
last_updated: "2026-04-26T17:34:39.878Z"
last_activity: 2026-04-26 -- Phase 30 execution started
progress:
  total_phases: 32
  completed_phases: 29
  total_plans: 84
  completed_plans: 85
  percent: 91
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-24)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours
**Current focus:** Phase 30 — hashicorp-vault-connector

## Current Position

Phase: 31
Plan: Not started
Status: Ready to plan
Last activity: 2026-04-26

Progress: [░░░░░░░░░░] 0/7 phases complete (v4.3)

## Performance Metrics

**Velocity:**

- Total plans completed: 24 (v4.2 last milestone phases)
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 23 | 1 | - | - |
| 24 | 2 | - | - |
| 25 | 3 | - | - |
| 26 | 3 | - | - |
| 27 | 4 | - | - |
| 28 | 3 | - | - |
| 29 | 4 | - | - |
| 30 | 3 | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 17-identity-infrastructure P01 | 5 | 1 tasks | 1 files |
| Phase 17-identity-infrastructure P02 | 2min | 2 tasks | 5 files |
| Phase 18-dnssec-scanner P01 | 160 | 2 tasks | 2 files |
| Phase 18-dnssec-scanner P02 | 6 | 3 tasks | 9 files |
| Phase 19 P01 | 4 | 2 tasks | 2 files |
| Phase 19-saml-oidc-scanner P02 | 3 | 2 tasks | 7 files |
| Phase 20-kerberos-scanner P01 | 3 | 2 tasks | 2 files |
| Phase 20-kerberos-scanner P02 | 5 | 3 tasks | 9 files |
| Phase 21-identity-surface P01 | 3 | 2 tasks | 3 files |
| Phase 21-identity-surface P02 | 2 | 4 tasks | 7 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v4.2 research]: impacket over pyasn1 for Kerberos AS-REQ -- impacket.krb5.asn1 handles KDC_ERR_PREAUTH_REQUIRED without raising; pyasn1 approach is 200+ lines of fragile ASN.1
- [v4.2 research]: impacket stays in [identity] extras group -- pyOpenSSL transitive conflict risk; must not enter core deps
- [v4.2 research]: DNSSEC first, SAML second, Kerberos third -- validates classifier extension pattern cheaply before raw socket work
- [v4.2 research]: Direct authoritative NS query required for DNSSEC -- system resolver strips DO bit and DNSKEY records
- [v4.2 research]: SAML_NS namespace constant required for all lxml XPath -- silent empty results without it (Pitfall 3)
- [Phase 17-identity-infrastructure]: Table name in RED scaffold is crypto_endpoints (not scan_results) -- CryptoEndpoint is the actual ORM model
- [Phase 17-identity-infrastructure]: Table name in _ensure_identity_columns is crypto_endpoints (not scan_results) -- CryptoEndpoint is the actual ORM model
- [Phase 17-identity-infrastructure]: impacket placed in [identity] extras group only -- not in core dependencies to avoid pyOpenSSL transitive conflict risk
- [Phase 17-identity-infrastructure]: All 6 identity ConnectorsCfg fields have safe defaults so v4.1 config.yaml loads without error via config_from_dict()
- [Phase 18-dnssec-scanner]: DNSSEC_ALG_MAP placed in dnssec_scanner.py for scanner self-containment per RFC 8624/9905 3-tier (CRITICAL/HIGH/SAFE)
- [Phase 18-dnssec-scanner]: udp_with_fallback isinstance check handles real dnspython tuple vs test mock direct-return without breaking either
- [Phase 18-dnssec-scanner]: CryptoPrimitive.PKE for RSA DNSSEC algorithms, SIGNATURE for DSA/ECDSA — CryptoPrimitive.RSA does not exist in cyclonedx
- [Phase 18-dnssec-scanner]: Synthetic DNSSEC finding types (NONE/NSEC/DS-MISMATCH/SHA1-DS) excluded from CBOM algorithm registration
- [Phase 19]: _is_sha1_uri and _classify_key_severity implemented in stub file — pure logic needed for static test GREEN state per RED scaffold plan
- [Phase 19]: SAML_NS declared as module-level dict constant (md/ds/alg/mdui) — required for lxml XPath calls to produce non-empty results
- [Phase 19-saml-oidc-scanner]: lxml ElementPath does not support not(@use) predicate — filter KeyDescriptor elements in Python instead of XPath
- [Phase 19-saml-oidc-scanner]: classifier.py rs256/es256/eddsa entries reused from JWT section — only sha1 short-form added for SAML SHA-1 URI findings
- [Phase 20-kerberos-scanner]: Functional RED tests patch IMPACKET_AVAILABLE=True -- impacket not installed in dev env, stub must be reachable
- [Phase 20-kerberos-scanner]: _derive_realm IPv4 detection added: 4-part all-numeric splits return full address, not last 2 octets
- [Phase 20-kerberos-scanner]: Test isolation: patch.object on _probe_kdc/_probe_ldap_anon internal functions rather than raw impacket mocks -- works with or without impacket installed
- [Phase 20-kerberos-scanner]: kerberos_scan_json includes ldap_status at top level AND nested under ldap key for compatibility
- [Phase 20-kerberos-scanner]: No-preauth case (empty etype list from AS-REP) produces kerberos-no-preauth placeholder endpoint rather than empty list
- [Phase 21-identity-surface]: IdentityFinding.algorithm is non-Optional str — every identity finding must name the weak algorithm
- [Phase 21-identity-surface]: ScanLatestResponse.identity_findings defaults to [] for backward compatibility with existing API responses
- [Phase 21-identity-surface]: Derivation tests use skipUnless(_HAS_DERIVE) pattern to SKIP gracefully until Plan 02 implements _derive_identity_findings
- [Phase 21-identity-surface]: Human verification approved (UAT deferred) — UAT-7-33 through UAT-7-37 and UAT-8-09 through UAT-8-11 added to docs/UAT-SERIES.md for testing after next phase
- [v4.3 roadmap]: GCP connector (Phase 26) must precede object storage audit (Phase 28) — GCS bucket enumeration done in Phase 26 is consumed by Phase 28 to prevent double API calls
- [v4.3 roadmap]: Phase 27 (Database Encryption) is CRITICAL PATH — dat_scan_json column and _ensure_v43_columns() are shared dependencies for Phases 28, 29, 30; must complete before any of them begin
- [v4.3 roadmap]: dar_ subscore prefix introduced as 5th prefix in scoring.py (parallel to identity_), not as extension of identity_trust — keeps surface scoring separable for future per-surface dashboard breakdowns
- [v4.3 roadmap]: Trend analysis (Phase 31) uses scanned_at-based session grouping from existing list_scans() — no new SQLite table needed
- [v4.3 roadmap]: GCP libs (google-cloud-kms, google-cloud-storage), hvac, kubernetes in [cloud] extras; psycopg2-binary and PyMySQL in [db] extras; ldap3 one-liner addition to [identity] extras
- [v4.3 roadmap]: DefaultCredentialsError fires at API call time (not import time) — GCP_AVAILABLE flag alone does not protect against it; must catch explicitly in gcp_connector.py
- [v4.3 roadmap]: S3 list_buckets is NOT paginated — get_paginator('list_buckets') raises OperationNotPageableError; use ThreadPoolExecutor(max_workers=10) for per-bucket encryption calls
- [v4.3 roadmap]: etcd EncryptionConfiguration is NOT a queryable K8s API resource — use managed cluster APIs (EKS/GKE/AKS) or kube-apiserver pod spec; K8S-03 encryption-config-inaccessible finding is required
- [v4.3 roadmap]: VAULT_TRANSIT_KEY_MAP similar to KMS_KEY_SPEC_MAP; ml-dsa/slh-dsa key types are positive PQC findings; Vault token via VAULT_TOKEN env var or config
- [v4.3 roadmap]: NULL collision with v4.2-era scan sessions in trend analysis is expected behavior — document, do not fix; first post-v4.3 trend will show all DAR findings as "new"
- [v4.3 roadmap]: ISSUE-2 and ISSUE-3 patterns must be treated as structural requirements on every scanner phase — pyproject.toml diff is a required PLAN.md deliverable; session_start parameter is mandatory for all new scanners

### Pending Todos

- Plan Phase 25 first; run /gsd-plan-phase 25

### Blockers/Concerns

None at roadmap creation time. Structural risks documented in research/SUMMARY.md Critical Pitfalls.

## Deferred Items

Items acknowledged and deferred at v4.2 milestone close on 2026-04-24 (carried to v4.3):

| Category | Item | Status |
|----------|------|--------|
| uat_gap | Phase 04: 04-HUMAN-UAT.md (5 pending scenarios) | partial — Docker chaos lab tests, pre-v3.9 carry-over |
| uat_gap | Phase 05: 05-HUMAN-UAT.md (5 pending scenarios) | partial — Dashboard UI tests, pre-v3.9 carry-over |
| uat_gap | Phase 07: 07-HUMAN-UAT.md (4 pending scenarios) | partial — Packaging tests, pre-v3.9 carry-over |
| uat_gap | Phase 13: 13-UAT.md (6 pending scenarios) | testing — Interactive mode, pre-v4.1 carry-over |
| verification_gap | Phase 04: 04-VERIFICATION.md | human_needed — pre-v3.9 carry-over |
| verification_gap | Phase 07: 07-VERIFICATION.md | human_needed — pre-v3.9 carry-over |
| verification_gap | Phase 22: 22-VERIFICATION.md | human_needed — E2E live identity scan (requires Docker) |
| verification_gap | Phase 24: 24-VERIFICATION.md | human_needed — intentionally accepted (0 pending scenarios) |
| seed | SEED-001-backlog-rollout-phase-plan | dormant |
| milestone_gap | NEW-ISSUE-3: expected_results_v3.md missing identity chaos lab entries | LOW — Phase 25 target |

## Session Continuity

Last session: 2026-04-26T16:48:04.831Z
Stopped at: Phase 30 context gathered
Resume file: .planning/phases/31-trend-analysis/31-CONTEXT.md

**Planned Phase:** 29 (Kubernetes Secrets Inspection) — 3 plans — 2026-04-26T12:22:11.840Z
