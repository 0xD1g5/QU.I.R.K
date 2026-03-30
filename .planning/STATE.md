---
gsd_state_version: 1.0
milestone: v3.9
milestone_name: milestone
status: executing
stopped_at: Completed 04-05-PLAN.md (ssh-weak + ldaps profiles + Phase 4 expected results)
last_updated: "2026-03-30T18:57:54.595Z"
last_activity: 2026-03-30
progress:
  total_phases: 7
  completed_phases: 3
  total_plans: 12
  completed_plans: 16
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-28)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours
**Current focus:** Phase 04 — chaos-lab-expansion

## Current Position

Phase: 04 (chaos-lab-expansion) — EXECUTING
Plan: 5 of 5
Status: Ready to execute
Last activity: 2026-03-30

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01-foundation-fixes P01 | 3 | 2 tasks | 3 files |
| Phase 01-foundation-fixes P02 | 3 | 2 tasks | 4 files |
| Phase 01-foundation-fixes P03 | 262 | 2 tasks | 3 files |
| Phase 01-foundation-fixes P04 | 3 | 2 tasks | 52 files |
| Phase 02-cbom-pipeline P01 | 2 | 2 tasks | 4 files |
| Phase 02-cbom-pipeline P03 | 3 | 3 tasks | 5 files |
| Phase 03-scanner-coverage P01 | 5 | 2 tasks | 7 files |
| Phase 03-scanner-coverage P02 | 2 | 2 tasks | 3 files |
| Phase 03-scanner-coverage P03 | 2 | 2 tasks | 2 files |
| Phase 03-scanner-coverage P04 | 10 | 2 tasks | 5 files |
| Phase 04-chaos-lab-expansion P02 | 15 | 2 tasks | 5 files |
| Phase 04-chaos-lab-expansion P03 | 5 | 2 tasks | 2 files |
| Phase 04 P04 | 3 | 2 tasks | 4 files |
| Phase 04-chaos-lab-expansion P05 | 3 | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Init: sslyze over testssl.sh (Python-native, programmatic API)
- Init: ssh-audit over raw paramiko (JSON output, full algorithm enum maps to CBOM)
- Init: cyclonedx-python-lib for CBOM (only Python SDK with full CycloneDX 1.4+ CBOM schema)
- Init: SaaS deferred — prove value with CLI+dashboard first
- [Phase 01-foundation-fixes]: Removed assessment-TIMESTAMP.json output from writer.py — assessment layer deprecated, single scoring path through intelligence/scoring.py
- [Phase 01-foundation-fixes]: cert_pubkey_alg is canonical CryptoEndpoint field — checked first in _extract_cert_key_type before legacy fallbacks
- [Phase 01-foundation-fixes]: D-04/D-05/D-06/D-07: ssh-audit subprocess with JSON output in ssh_audit_json column; tls_version field no longer misused; ThreadPoolExecutor for concurrency
- [Phase 01-foundation-fixes]: sslyze primary TLS scanner with ssl+cryptography fallback; SSLYZE_AVAILABLE flag enables graceful degradation
- [Phase 01-foundation-fixes]: tls_capabilities_json stores sslyze deep data: accepted_by_version dict, chain_depth, chain_verified, elliptic_curves
- [Phase 01-foundation-fixes]: Package renamed qcscan -> quirk per D-13; pyproject.toml created with entry point quirk=run_scan:main per D-14/D-15; all QU.I.R.K. user-facing strings updated per D-16/D-17
- [Phase 02-cbom-pipeline]: classify_algorithm returns 3-tuple (CryptoPrimitive, nist_level, classical_level) — single call carries both quantum and classical security bit-strength
- [Phase 02-cbom-pipeline]: SHA-256 nist_level=0 (quantum-vulnerable via Grover halving); SHA-384 nist_level=2 — different levels reflect post-quantum effective security
- [Phase 02-cbom-pipeline]: SSH vendor suffix stripping (@openssh.com, @libssh.org) and fuzzy hyphen-insertion fallback normalize algorithm names before lookup
- [Phase 02-cbom-pipeline]: JsonV1Dot6/XmlV1Dot6 for CycloneDX 1.6 serialization — write_cbom_files() produces cbom-{stamp}.cdx.json and cbom-{stamp}.cdx.xml
- [Phase 02-cbom-pipeline]: CBOM step placed after run_stats (step 4) in write_reports() so timing stats exclude CBOM generation
- [Phase 03-scanner-coverage]: ConnectorsCfg Phase 3 fields use Python defaults for backwards-compatible config.yaml handling
- [Phase 03-scanner-coverage]: Wave 0 test scaffolds define scanner module contracts before implementation (TDD RED state expected)
- [Phase 03-scanner-coverage]: pyproject.toml build-backend changed to setuptools.build_meta for Python 3.14 compatibility
- [Phase 03-scanner-coverage]: JWKS_PATHS probes three paths in order; OIDC discovery follows jwks_uri; RSA bits = modulus byte-length * 8; EC bits from crv lookup
- [Phase 03-scanner-coverage]: scan_aws_targets calls _scan_acm last so assert_called_with('list_certificates') passes — test checks most recent get_paginator call
- [Phase 03-scanner-coverage]: azure-mgmt-network imported inside _scan_app_gateways to keep it optional without affecting AZURE_AVAILABLE flag
- [Phase 03-scanner-coverage]: JWT algorithm entries map to (SIGNATURE/MAC, 0, bits) per RFC 7518; alg:none maps to (UNKNOWN, 0, 0) as critical vulnerability marker
- [Phase 03-scanner-coverage]: CBOM builder Pass 3 uses explicit elif for JWT/CONTAINER/SOURCE/AWS/AZURE to prevent TLS fallthrough (pitfall 6)
- [Phase 04-chaos-lab-expansion]: apt 'openssl' is the CRYPTO_LIB_ALLOWLIST exact match in image-old-libssl; 'libssl1.0.0' also installed but not in frozenset
- [Phase 04-chaos-lab-expansion]: registry-seed uses docker:24-dind + socket mount; seed.sh uses registry:5000 (compose network hostname) not localhost:20005
- [Phase 04-chaos-lab-expansion]: Gitea admin user created via entrypoint bash -c with INSTALL_LOCK=true; gitea-seed waits on service_healthy with start_period: 30s; seed.sh uses printf + base64 tr -d newlines for alpine sh file encoding
- [Phase 04]: RSA_1024 KMS key spec not supported by LocalStack free tier — second RSA_2048 with rsa-1024-fallback description used; KMS_KEY_SPEC_MAP has no RSA_1024 entry so scanner behavior unchanged
- [Phase 04]: Storage profile uses dedicated LocalStack instance (port 20007, SERVICES=kms) independent of cloud profile LocalStack (port 24566, SERVICES=s3,sts,iam)
- [Phase 04-chaos-lab-expansion]: ubuntu:18.04 for ssh-weak (OpenSSH 7.6p1 supports legacy algorithms removed in later versions); port 20022 avoids conflict with ssh-alt on 2222
- [Phase 04-chaos-lab-expansion]: Port 636 for ldaps (standard LDAPS port required by sslyze); osixia/openldap cert mount path /container/service/slapd/assets/certs/ per image convention; LDAP_TLS_VERIFY_CLIENT=never for lab use

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 5 (Web Dashboard) depends on Phase 2 (CBOM Pipeline) not Phase 4 — parallel path possible after Phase 2 ships
- SCAN-01/SCAN-02 placed in Phase 1 (not Phase 3) because they are foundation scanner replacements, not net-new surface coverage

## Session Continuity

Last session: 2026-03-30T18:57:54.592Z
Stopped at: Completed 04-05-PLAN.md (ssh-weak + ldaps profiles + Phase 4 expected results)
Resume file: None
