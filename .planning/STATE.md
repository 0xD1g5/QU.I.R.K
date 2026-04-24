---
gsd_state_version: 1.0
milestone: v4.2
milestone_name: Identity Crypto
status: milestone_complete
stopped_at: Phase 24 planned — 2 plans (01 RED, 02 GREEN), verification passed, ready to execute
last_updated: "2026-04-24T19:28:16.026Z"
last_activity: 2026-04-24 -- Phase --phase execution started
progress:
  total_phases: 5
  completed_phases: 6
  total_plans: 10
  completed_plans: 10
  percent: 120
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-24)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours
**Current focus:** v4.3 Data at Rest — next milestone (start with /gsd-new-milestone)

## Current Position

Phase: —
Plan: Not started
Status: v4.2 milestone shipped; planning v4.3
Last activity: 2026-04-24

Progress: [██████████] v4.2 SHIPPED — v4.3 planning next

## Performance Metrics

**Velocity:**

- Total plans completed: 4 (v4.2)
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 23 | 1 | - | - |
| 24 | 2 | - | - |

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

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 20 (Kerberos): impacket bare AS-REQ exact call sequence should be verified against 0.13.0 source before implementation -- STACK.md covers behavior but not exact field sequence
- Phase 19 (SAML): confirm whether SimpleSAMLphp emits alg:SigningMethod elements -- fallback to cert key inspection must be primary path
- Phase 20 (Kerberos): smblds/smblds etype configuration via samba-tool for RC4-only realm is MEDIUM confidence -- fallback image itherz/samba-ad-dc documented in research

## Deferred Items

Items acknowledged and deferred at milestone close on 2026-04-24:

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
| milestone_gap | ISSUE-2: ldap3 absent from pyproject.toml (KERB-03 LDAP always inert) | MEDIUM — Phase 25 target |
| milestone_gap | NEW-ISSUE-1: OIDC RS256 findings mislabeled as TLS-sourced | MEDIUM — Phase 25 target |
| milestone_gap | NEW-ISSUE-3: expected_results_v3.md missing identity chaos lab entries | LOW — Phase 25 target |

Known deferred items at close: 12 (see above)

## Session Continuity

Last session: 2026-04-24
Stopped at: v4.2 Identity Crypto milestone complete — archived, tagged v4.2
Resume file: /gsd-new-milestone for v4.3 planning
