---
gsd_state_version: 1.0
milestone: v4.6
milestone_name: Enterprise Readiness
current_phase: 49
current_phase_name: compliance-mapping
status: executing
stopped_at: Phase 49 context gathered
last_updated: "2026-05-05T21:43:33.023Z"
last_activity: 2026-05-05
progress:
  total_phases: 43
  completed_phases: 4
  total_plans: 19
  completed_plans: 16
  percent: 84
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-03)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours
**Current focus:** Phase 49 — compliance-mapping

## Current Position

Phase: 49 (compliance-mapping) — EXECUTING
Current Phase: 49
Current Phase Name: compliance-mapping
Plan: 4 of 5
Status: Ready to execute
Last activity: 2026-05-05
Last Activity Description: Phase 49 Plan 03 complete — Compliance Summary HTML section (COMPLY-05 GREEN)
Next action: Phase 48 (Rich Finding Context).

## Phase Overview

| Phase | Slug | Complexity | Depends On |
|-------|------|------------|------------|
| 45 | install-day-ux | S | Phase 44 |
| 46 | tls-finding-gaps | M | Phase 45 |
| 47 | nmap-multi-target | M | Phase 45 (parallel to 46) |
| 48 | rich-finding-context | M | Phase 46 |
| 49 | compliance-mapping | M | Phase 48 |
| 50 | enterprise-documentation | M | Phase 49 |

**Critical path:** 45 → 46 → 48 → 49 → 50 (Phase 47 parallel to Phase 46)

## Performance Metrics

**Velocity:**

- Total plans completed: 19 (v4.4)
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 43 | 6 | - | - |
| 44 | 6 | - | - |
| Phase 45-install-day-ux P01 | 8 | 3 tasks | 3 files |
| Phase 45-install-day-ux P02 | 12 | 3 tasks | 4 files |
| Phase 45-install-day-ux P03 | 5 | 5 tasks | 9 files |
| Phase 45-install-day-ux P04 | 6 | 3 tasks | 3 files |
| Phase 46-tls-finding-gaps P01 | ~12 min | 2 tasks | 5 files |
| 47 | 3 | - | - |
| Phase 48-rich-finding-context P01 | ~25 min | 2 tasks | 3 files |
| Phase 48-rich-finding-context P02 | ~10 min | 2 tasks | 4 files |
| Phase 48-rich-finding-context P03 | ~12 min | 2 tasks | 9 files |
| Phase 49-compliance-mapping P01 | 6min | 2 tasks | 7 files |
| Phase 49 P02 | 6m | 2 tasks | 4 files |
| Phase 49 P03 | ~5 min | 1 tasks | 1 files |

## Accumulated Context

| Phase 32 P03 | 12 min | 2 tasks | 1 files |
| Phase 32 P04 | 22 | 2 tasks | 5 files |
| Phase 32 P06 | 30 min | 2 tasks | 1 files |
| Phase 32 P07 | 10min | 2 tasks | 4 files |
| Phase 32 P08 | ~3.5 minutes | 2 tasks | 3 files |
| Phase 35 P04 | 180 | 3 tasks | 4 files |
| Phase 40-chaos-lab-parity P05 | 2 | 1 tasks | 1 files |
| Phase 40-chaos-lab-parity P06 | ~5 min | 4 tasks | 4 files |
| Phase 41 P01 | 12 min | 3 tasks | 7 files |
| Phase 41 P02 | 10 min | 2 tasks | 3 files |
| Phase 41 P03 | 9 min | 2 tasks | 7 files |
| Phase 41 P04 | 10 min | 2 tasks | 3 files |
| Phase 41 P05 | 10 min | 2 tasks | 12 files |
| Phase 41 P06 | 10 min | 2 tasks | 3 files |
| Phase 41 P07 | ~5 min | 2 tasks | 4 files |
| Phase 42 P01 | 105 | 2 tasks | 2 files |

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

Phase 40 decisions:

- [40-01]: lab.sh ALL_PROFILES replaced with _derive_all_profiles() that reads docker-compose.yml at runtime — structurally eliminates drift between lab.sh and compose (D-14)
- [40-01]: grep character class extended to [a-zA-Z0-9_-] to handle phaseA profile name (uppercase A); plan snippet had [a-z0-9_-] which missed phaseA
- [40-01]: yq preferred with grep fallback; yq not a hard requirement (not in chaos-lab toolchain today)
- [40-02]: Compose profile names are authoritative; fixed 3 profile-name drifts (bind9→dnssec, simpla-samlphp→saml, samba-dc→kerberos) and SAML port (8880→8080)
- [40-02]: pki section added as new content (v3 oracle had no pki section); sourced port 17443 / MTLS_STEPCA from docs/chaos-lab.md line 367
- [40-06]: lab.sh down arm (lines 97-101) omits PROFILE_ARGS — profile-tagged services survive teardown; deferred to Phase 41 backlog (fix: compose --profile "*" down --remove-orphans)
- [40-06]: LAB-04 human-verified by operator across all 5 v4.3+v4.4 profiles (vault, database, storage-s3, email, broker) — status + logs clean against real compose service names

Previous milestone (v4.3) key decisions carried forward:

- ISSUE-2 and ISSUE-3 patterns must be treated as structural requirements on every scanner phase — pyproject.toml diff is a required PLAN.md deliverable; session_start parameter is mandatory for all new scanners
- All new scanners must include [motion] extras group entry in pyproject.toml at plan time

Roadmap decisions (2026-04-27):

- Phase 32 and Phase 33 develop in parallel — no shared code dependencies between email_scanner.py and broker_scanner.py
- Phase 34 (Motion Intelligence) and Phase 35 (CBOM Integration) develop in parallel once 32+33 are done
- Chaos lab port allocation: email profile uses 30xxx range, broker profile uses 26xxx/29xxx/25xxx ranges (no conflicts with existing profiles)
- KAFKA-04 (AdminClient enrichment) is optional/graceful-degradation only — not required for Phase 33 success criteria; TLS probe via sslyze is the required path
- OpenSSL 3.x TLS 1.0/1.1 caveat applies to both email and broker chaos labs — target RSA key-exchange and weak cipher as primary detectable findings at TLS 1.2
- [Phase ?]: Phase 32 Plan 03: email_scanner.py uses module-level sslyze stub names so tests can patch SslyzeScanner even when sslyze is absent
- [Phase ?]: Phase 32 Plan 03: _peer_metadata() duck-types the wrapped socket so MagicMock SSLSockets work without spec=ssl.SSLSocket
- [Phase ?]: Phase 32 Plan 04: email findings merged inside the existing risk_engine phase-timer (single span) to preserve report metric integrity
- [Phase 32]: Plan 32-08: mirrored kerberos_scan_json attachment pattern to populate CryptoEndpoint.email_scan_json (closes Phase 32 SC-1) and added an AST-based real-Logger smoke test that catches stdlib-positional-args drift in run_scan.py's email branch
- [Phase ?]: Phase 35 close: CBOM-01..04 marked Complete; REQUIREMENTS wording aligned to code; UAT-35-01..03 added
- [Phase ?]: SAML port is 8080 (compose source of truth); 8880 was v3 oracle drift
- [Phase ?]: [41-01]: scan_error_category added as new column on CryptoEndpoint (not separate table) — preserves trends.py counting + reuses _ensure_*_columns migration pattern
- [Phase ?]: [41-01]: skip-registry meta-test uses +/-2 line tolerance to absorb minor edits without forcing registry churn; meta-test marked @pytest.mark.skip_registry_gate (not in ALLOWED_SKIPS — it is the gate)
- [Phase ?]: [41-01]: xfail-with-reason stubs (vs pytest.skip) keep pending tests visible in collection while non-blocking; each stub names the plan that lands the wiring
- [Phase ?]: [41-02]: Property setters added for legacy timeout aliases (silent route to TimeoutsCfg); apply_profile() in quirk/engine/profiles.py still writes through legacy names — Plan 03 cleans them up
- [Phase ?]: [41-02]: @dataclass(init=False) + custom __init__ chosen for ScanCfg to make legacy *_timeout_seconds kwarg routing self-documenting in the signature
- [Phase ?]: [41-03]: Scanners read TimeoutsCfg directly — D-08 BACK-45 dissolved
- [Phase ?]: [41-03]: hasattr guard in TLS/SSH scanners + cfg=None kwarg in db/vault connectors for SimpleNamespace mock compat
- [Phase ?]: [41-03]: HYGN-02 hygiene tests inverted (mutation-must-be-absent) instead of deleted to preserve regression guard role
- [Phase ?]: [41-04]: _wrapped_phase used for TLS/SSH/broker; email phase keeps with-block AST shape with inline try/except (preserves test_email_run_scan_wiring AST guard)
- [Phase ?]: [41-04]: trends.py D-15 exclusion uses getattr(ep, scan_error_category, None) so legacy DB rows without the column do not break counting
- [Phase ?]: [41-04]: Optional-extra advisory probes scoped to broker + email (the [motion]-gated scanners)
- [Phase ?]: Phase 41 Plan 05: Deleted dead test_migration_preserves_existing_rows (always-skip path); idempotency covered by sibling test.
- [Phase ?]: Phase 41 Plan 05: Hard-imported gcp_connector and email_scanner modules; Wave 0 RED-state guards no longer needed.
- [Phase ?]: Phase 41 Plan 06: D-10 + ROBUST-04 audit + lab.sh profile sweep
- [Phase ?]: lab.sh down + reset arms now use --profile "*" --remove-orphans for full profile-sweep (D-18 + extension)
- [41-07]: Phase 41 closed 2026-04-29 — UAT-41-01..04 added to UAT-SERIES.md, vault phase note + UAT mirror synced, ROADMAP marked [x]; CI-01..03 + ROBUST-01..04 all complete
- [41-Summary]: TimeoutsCfg + RetryCfg sub-tables on ScanCfg with deprecation-alias properties on four legacy fields (D-06/07); BACK-45 cfg.scan mutation pattern dissolved by passing explicit kwargs; cfg.scan.profile bug at run_scan.py:743 fixed; _wrapped_phase helper around every scanner phase implements D-14; trends.py respects scan_error_category to exclude missing_extra from regression counts (D-15); lab.sh down + reset arms both sweep profile-tagged services (D-18 + extension)
- [Phase 42]: Adopted [validation] umbrella extra over hand-pinned deps (D-01)
- [Phase 42]: Extracted MOTION_PLAINTEXT_PROTOCOLS and DAR_SKIP_PROTOCOLS as module-level frozensets (D-10/D-11)
- [Phase ?]: Phase 45-01: [all] meta-extra excludes [identity] (impacket transitively downgrades cryptography, breaks TLS scanner)
- [46-01]: chain_verified added as Boolean column on CryptoEndpoint (TLS-FIND-06); BOOLEAN type stores as INTEGER 0/1/NULL in SQLite — tri-state-compatible with Python None/True/False
- [46-01]: Fallback _scan_one_fallback gets a CERT_REQUIRED verify pre-pass BEFORE the existing CERT_NONE metadata pass; both run independently (verify result + metadata extraction decoupled)
- [46-01]: Network errors on the verify pre-pass set chain_verified=None, NOT False (Pitfall 1 — avoid false untrusted-CA findings on transient network failures)
- [46-01]: scan_one D-01 gate uses field-level merge (cert_not_after, cert_subject, cert_issuer, cert_pubkey_size+alg, chain_verified) — sslyze ep is mutated in place; fallback ep is consulted only for missing fields
- [46-03]: tls-cert-defects profile uses ports 13444-13447 (NOT 13443-13446 — 13443 already taken by phaseA tls-missing-intermediate)
- [46-03]: untrusted-CA leaf cert generated as RSA-2048 (strong) — isolates the untrusted-CA finding from the RSA-1024 finding when scanned at port 13446
- [46-03]: tls-cert-rsa1024 service includes OPENSSL_CONF=/etc/nginx/openssl-legacy.cnf + legacy.cnf volume mount (Pitfall 3 — nginx 3.x rejects RSA-1024 without legacy provider)
- [46-03]: lab.sh ALL_PROFILES NOT touched — Phase 40 D-14 _derive_all_profiles() runtime parser auto-discovered tls-cert-defects (verified: ./lab.sh profiles output)
- [46-02]: _chain_verified() uses _SENTINEL = object() to distinguish a column value of None (indeterminate) from a missing attribute (legacy pre-Phase-46 ORM row); only after both attribute-presence and not-None checks does the helper return bool — preserves tri-state semantics from Plan 46-01
- [46-02]: D-04 implementation uses if/elif within a single block — when issuer == subject, the untrusted-CA branch is structurally unreachable, eliminating any mutual-exclusivity bug surface
- [46-02]: Severity bumps — expired HIGH→CRITICAL (TLS-FIND-01); self-signed MEDIUM→HIGH (TLS-FIND-02); untrusted-CA gets dedicated MEDIUM branch (TLS-FIND-03)
- [46-02]: Parallel-staging race — Plan 46-02 file changes (risk_engine.py + 2 test files) were captured by Plan 46-03's commit 386e1bd because both plans shared a working copy; rather than rewriting history (would clobber 46-03's correctly authored chaos-lab work), the mis-attribution is documented in 46-02-SUMMARY.md
- [46-04]: Plan 46-01 verify pre-pass set check_hostname=True unconditionally; when server_hostname=None (SNI off / IP target) wrap_socket raised ValueError, swallowed by broad except as chain_verified=None — making the untrusted-CA branch structurally dead end-to-end. Fix in commit de70301: when verify_hostname is None, set check_hostname=False (chain validation is independent of hostname check; hostname mismatch is out of scope per CONTEXT.md)
- [46-04]: Live-fire chaos lab brought up via 'docker compose -p chaoslab --profile tls-cert-defects up -d' (NOT lab.sh) per BACK-87 — operator instructions explicitly recommended this workaround; phase 46 verification path bypasses BACK-87 entirely
- [48-01]: `_build_finding(...)` chokepoint helper validates non-empty description+recommendation at construction (D-02); `NIST_IR_8547_DEPRECATION` module constant appended to every quantum-vulnerable finding's recommendation (D-06); deterministic suffix preserves `_dedupe_findings` tuple equality (T-48-03 mitigation)
- [48-02]: `# DO NOT UNIFY` guardrail comment locks the intentional `recommendation` (risk-engine dict) vs `remediation` (dashboard DTO) field-name asymmetry; `routes/scan.py::_derive_findings` constructs `FindingItem` from `CryptoEndpoint` state, not from risk-engine dicts — no rename needed
- [48-03]: CI grep gate placement is a pytest test (`tests/test_pqc_terminology_gate.py`) — only existing in-repo lint-by-disk-read precedent (`tests/test_packaging.py`); auto-collected without Makefile/scripts runner; the GitHub workflow is path-scoped to `src/dashboard/**` and would not trigger on Python source changes anyway
- [48-03]: Two-test gate (file-resolution + substring) — `test_gated_files_resolve` makes accidental file rename of `risk_engine.py` or `routes/scan.py` a loud failure rather than a silent gate bypass
- [48-03]: D-04 doc rewrites in `docs/report-interpretation.md` (lines 121, 150) + `docs/quirk-overview.md` (line 75) replace Kyber/Dilithium/when-standards phrasing with FIPS 203/204/205 + NIST IR 8547 deprecation phrase
- [Phase ?]: AST extraction over runtime engine sweep — CI must not depend on Docker chaos lab
- [Phase ?]: Lazy TITLE_PREFIX_ALIASES import keeps Phase 49 fixture collectable before quirk.compliance exists

### Pending Todos

None at roadmap creation.

### Blockers/Concerns

None at roadmap creation.

## Deferred Items

Items acknowledged and deferred at v4.5 milestone close on 2026-05-03:

| Category | Item | Status |
|----------|------|--------|
| uat_gap | Phase 43: 43-HUMAN-UAT.md (2 pending) — loading-state first paint + keyboard focus ring visibility | deferred — require live browser session; cannot automate without E2E test infra |
| uat_gap | Phase 44: 44-HUMAN-UAT.md (1 pending) — Phase 29 K8s cloud-only justification review | deferred — human confirmation needed; justification document exists at 44-06-PLAN.md §phase_29_cloud_only_justification |
| seed | SEED-001-backlog-rollout-phase-plan [dormant] — Create prioritized phase rollout plan from backlog items | dormant — carry to v4.6 planning |

Items deferred at v4.4 close on 2026-04-29 (closed in v4.5 Phase 38 on 2026-04-29):

| ID | Category | Item | Status |
|----|----------|------|--------|
| DEF-v4.4-01 | phase_gating | Phase 36 `wave_0_complete: false` flip | closed in Phase 38 (PLAN 38-02) — wave_0_complete: true after GAP-01/02 closure |
| DEF-v4.4-02 | regression | SAML/OIDC missing from `/api/scan/latest` `identity_findings` (real bug, ISSUE-3 from Phase 24) | closed in Phase 38 (PLAN 38-01) — SESSION_BRACKET 5-min backward bracket on /api/scan/latest implicit-latest branch; regression test green |

Items carried over from v4.3 (acknowledged, non-blocking for v4.4):

| Category | Item | Status |
|----------|------|--------|
| uat_gap | Phase 04: 04-HUMAN-UAT.md (5 pending scenarios) | partial — Docker chaos lab tests, pre-v3.9 carry-over |
| uat_gap | Phase 05: 05-HUMAN-UAT.md (5 pending scenarios) | partial — Dashboard UI tests, pre-v3.9 carry-over |
| uat_gap | Phase 07: 07-HUMAN-UAT.md (4 pending scenarios) | partial — Packaging tests, pre-v3.9 carry-over |
| uat_gap | Phase 13: 13-UAT.md (6 pending scenarios) | deferred — Interactive mode, pre-v4.1 carry-over |
| uat_gap | Phase 25: 25-HUMAN-UAT.md (2 pending scenarios) | automated (chaos lab) — closed in Phase 44 (PLAN 44-02); tests/test_kerberos_scanner.py::test_samba_dc_integration + tests/test_saml_scanner.py::test_chaos_lab_integration cover UAT-25 against kerberos + saml chaos lab profiles |
| uat_gap | Phase 27: 27-HUMAN-UAT.md (1 pending scenario) | automated (chaos lab) — closed in Phase 44 (PLAN 44-01); tests/test_uat_db_integration.py covers PostgreSQL/MySQL ssl-off against database chaos lab |
| uat_gap | Phase 27: 27-UAT.md (7 pending scenarios) | automated (chaos lab) — closed in Phase 44 (PLAN 44-01); tests/test_uat_db_integration.py covers all 7 behavioral scenarios against database chaos lab profile (PostgreSQL :25432, MySQL :23306) |
| uat_gap | Phase 28: 28-HUMAN-UAT.md (3 pending scenarios) | partial — live S3/GCS bucket scan requires cloud credentials |
| uat_gap | Phase 29: 29-UAT.md (10 pending scenarios) | cloud-only — closed in Phase 44 (D-01/D-02/D-03): EKS/GKE/AKS encryption detection requires cloud-managed control plane APIs not available in a local cluster (UAT-29-01 needs AWS EKS DescribeCluster encryptionConfig.keyArn; UAT-29-02 needs GCP databaseEncryption.state; UAT-29-03 needs Azure AKS securityProfile.azureKeyVaultKms + AAD RBAC). Scanner logic is covered by mock-based unit tests in test_k8s_connector.py. Per-scenario justification: see .planning/phases/44-uat-debt-automation/44-06-PLAN.md §phase_29_cloud_only_justification |
| uat_gap | Phase 30: 30-HUMAN-UAT.md (1 pending scenario) | automated (chaos lab) — closed in Phase 44 (PLAN 44-03); tests/test_vault_connector.py::test_vault_live_uat_30_01_five_findings covers UAT-30-01 (5 findings) against vault chaos lab profile (vault-30 :28200) |
| uat_gap | Phase 31: 31-HUMAN-UAT.md (4 pending scenarios) | partial — trend analysis requires prior scan history |
| verification_gap | Phase 25: 25-VERIFICATION.md | automated (chaos lab) — closed in Phase 44 (PLAN 44-02); same chaos lab integration test coverage as Phase 25 HUMAN-UAT closure |
| verification_gap | Phase 28: 28-VERIFICATION.md | human_needed — live object storage scan (requires cloud credentials) |
| verification_gap | Phase 31: 31-VERIFICATION.md | automated (pytest) — closed in Phase 44 (PLAN 44-04); tests/test_dashboard_trends.py::test_uat_31_trends_two_sessions_flat_wire_format seeds two distinct sessions in UUID-named SQLite and asserts /api/trends flat wire format |

## Session Continuity

Last session: 2026-05-05T21:43:33.020Z
Stopped at: Phase 49 context gathered
Next action: Phase 49 (Compliance Mapping) — keys off the FIPS 203/204/205 literal substrings written by Phase 48
