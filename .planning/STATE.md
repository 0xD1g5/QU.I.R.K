---
gsd_state_version: 1.0
milestone: v4.5
milestone_name: Reliability & Gap Closure
status: ready_to_plan
stopped_at: Phase 42 context gathered
last_updated: "2026-05-01T21:52:52.285Z"
last_activity: 2026-05-01
progress:
  total_phases: 7
  completed_phases: 7
  total_plans: 32
  completed_plans: 32
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-26)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours
**Current focus:** Phase 43 — dashboard-polish

## Current Position

Phase: 44
Plan: Not started
Status: Ready to plan
Last activity: 2026-05-01

## Phase Overview

| Phase | Slug | Complexity | Depends On |
|-------|------|------------|------------|
| 38 | identity-api-regression-fix | S | Phase 37 |
| 39 | data-at-rest-dashboard-tab | M | Phase 37 (parallel to 38) |
| 40 | chaos-lab-parity | M | Phase 37 |
| 41 | ci-stability-scanner-robustness | M | Phase 38, 40 |
| 42 | cbom-correctness-audit | M | Phase 40 |
| 43 | dashboard-polish | M | Phase 39, 42 |
| 44 | uat-debt-automation | M | Phase 40, 41, 42, 43 |

**Critical path:** 37 → 38/39/40 (parallel) → 41/42 → 43 → 44

## Performance Metrics

**Velocity:**

- Total plans completed: 4 (v4.4)
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 43 | 4 | - | - |

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

### Pending Todos

None at roadmap creation.

### Blockers/Concerns

None at roadmap creation.

## Deferred Items

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
| uat_gap | Phase 25: 25-HUMAN-UAT.md (2 pending scenarios) | partial — live identity scan requires Docker + samba-dc |
| uat_gap | Phase 27: 27-HUMAN-UAT.md (1 pending scenario) | partial — live DB encryption scan requires running DB |
| uat_gap | Phase 27: 27-UAT.md (7 pending scenarios) | deferred — DB encryption behavioral tests require live DB |
| uat_gap | Phase 28: 28-HUMAN-UAT.md (3 pending scenarios) | partial — live S3/GCS bucket scan requires cloud credentials |
| uat_gap | Phase 29: 29-UAT.md (10 pending scenarios) | testing — K8s secrets inspection requires live cluster |
| uat_gap | Phase 30: 30-HUMAN-UAT.md (1 pending scenario) | partial — live Vault connector requires running Vault instance |
| uat_gap | Phase 31: 31-HUMAN-UAT.md (4 pending scenarios) | partial — trend analysis requires prior scan history |
| verification_gap | Phase 25: 25-VERIFICATION.md | human_needed — live identity scan (requires Docker) |
| verification_gap | Phase 28: 28-VERIFICATION.md | human_needed — live object storage scan (requires cloud credentials) |
| verification_gap | Phase 31: 31-VERIFICATION.md | human_needed — trend analysis UI requires running dashboard with scan history |

## Session Continuity

Last session: 2026-05-01T21:52:52.281Z
Stopped at: Phase 42 context gathered
Next action: Begin Phase 42 (cbom-correctness-audit)
