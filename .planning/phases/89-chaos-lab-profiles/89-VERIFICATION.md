---
phase: 89-chaos-lab-profiles
verified: 2026-05-22T18:00:00Z
status: gaps_found
score: 5/7 must-haves verified
overrides_applied: 1
overrides:
  - must_have: "docker compose --profile smtp-starttls up starts a STARTTLS-capable SMTP container (ROADMAP SC#3)"
    reason: "D-01 (CONTEXT.md, locked pre-planning decision): LAB-03 smtp-starttls is closed as already-covered by the existing email profile. Port 30587 (Postfix submission) satisfies the requirement. Coverage note added to expected_results_v4.md, UAT-89-03-02 added, REQUIREMENTS.md row marked [x]. No standalone smtp-starttls profile is added — this is an explicit architectural decision, not an omission."
    accepted_by: "orchestrator (D-01 locked in 89-CONTEXT.md)"
    accepted_at: "2026-05-22T00:00:00Z"
gaps:
  - truth: "REQUIREMENTS.md requirement rows LAB-01, LAB-02, LAB-04, LAB-06 marked complete (checkbox and traceability table)"
    status: failed
    reason: "REQUIREMENTS.md shows [ ] (unchecked) for LAB-01, LAB-02, LAB-04 in the requirement list and 'pending' for all four in the traceability table, even though all implementations are complete in the codebase. REQUIREMENTS.md was not updated by the executor for these four requirements."
    artifacts:
      - path: ".planning/REQUIREMENTS.md"
        issue: "Lines 28-29, 31, 33: LAB-01/02/04/06 show '- [ ] **LAB-xx**:' (unchecked). Lines 83-84, 86, 88 in traceability table show 'pending' for LAB-01, LAB-02, LAB-04, LAB-06."
    missing:
      - "Flip LAB-01, LAB-02, LAB-04 requirement rows from '- [ ]' to '- [x]' with closure rationale"
      - "Flip LAB-06 requirement row from '- [ ]' to '- [x]' with LAB-06 closure rationale (DNSSEC+SAML verified; kerberos-etype deferred with documented caveat)"
      - "Update traceability table rows LAB-01, LAB-02, LAB-04, LAB-06 from 'pending' to '✅ done — <rationale>'"
  - truth: "kerberos identity_weak_etype_count deferred item is documented as a known limitation (not a silent gap)"
    status: partial
    reason: "The deferral is documented in 89-02-SUMMARY.md and the phase context, but not in REQUIREMENTS.md (LAB-06 row). When REQUIREMENTS.md is updated, the LAB-06 closure note should call out that identity_weak_etype_count is a known limitation requiring the 'identity' extra (impacket) + a live KDC, and that DNSSEC+SAML counters were verified non-zero."
    artifacts:
      - path: ".planning/REQUIREMENTS.md"
        issue: "LAB-06 row is blank 'pending' — no closure note documenting the kerberos deferred item"
    missing:
      - "LAB-06 closure note in REQUIREMENTS.md: reference dnssec_weak_algo_count=2, saml_weak_signing_count=2 verified; kerberos etype deferred (needs impacket + KDC, macOS port-88 caveat)"
human_verification:
  - test: "Kerberos identity_weak_etype_count path (deferred from orchestrator human-verify)"
    expected: "identity_weak_etype_count > 0 after installing 'identity' extra (pip install -e '.[identity]') and bringing up the kerberos profile with LAB_INCLUDE_KERBEROS=1 (system KDC stopped on macOS)"
    why_human: "Requires impacket installation + live KDC container; macOS port-88 collision prevents automated run in dev environment"
  - test: "Live scanner scan against each new chaos-lab profile"
    expected: "postgres-tls: sslyze POSTGRES probe emits HIGH weak-cipher + MEDIUM RSA-2048. redis-tls: broker_scanner.py emits HIGH weak-cipher + HIGH plaintext. kafka-tls: broker_scanner.py emits HIGH plaintext + HIGH weak-cipher + MEDIUM RSA-2048. grpc-tls: sslyze emits RSA-2048 MEDIUM (no HIGH weak-cipher — ECDHE-RSA PFS per D-03 empirical result). email port 30587: emits SMTP-STARTTLS HIGH finding (LAB-03 proof)."
    why_human: "Docker required; cannot run Docker in this verification environment. D-03 sslyze gate was already run empirically by the executor and logged in 89-03-SUMMARY.md — human should re-confirm if needed."
---

# Phase 89: Chaos Lab Profiles — Verification Report

**Phase Goal:** Five new chaos-lab profiles covering the remaining TLS-capable services (postgres-tls, redis-tls, smtp-starttls, kafka-tls, grpc-tls) are up and scanner-verified, and the identity-lab evidence gap (BACK-78) is confirmed closed — every new profile satisfies the CLAUDE.md lab-sync obligation in the same change

**Verified:** 2026-05-22T18:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | postgres-tls profile: weak-TLS PostgreSQL container, four-file lab-sync complete (LAB-01) | VERIFIED | `labs/postgres-tls/postgresql.conf` contains `ssl_ciphers='AES128-SHA:AES256-SHA'`, TLS 1.2 only; service block in `docker-compose.yml` (L1155); `## Profile: postgres-tls` section in `expected_results_v4.md` (L594); README row present; `./lab.sh profiles` lists `postgres-tls` |
| 2 | redis-tls profile: standalone weak-TLS Redis container, four-file lab-sync complete (LAB-02) | VERIFIED | `labs/redis-tls/redis.conf` has `tls-ciphers "DES-CBC3-SHA:AES128-SHA:AES256-SHA"`, `tls-protocols "TLSv1.2"`; standalone service in `docker-compose.yml` (L1183); `## Profile: redis-tls` section in expected_results (L621); README row; profiles output confirms listing |
| 3 | smtp-starttls: existing email profile port 30587 satisfies LAB-03, no standalone service (D-01) | PASSED (override) | `expected_results_v4.md` L446-451: explicit LAB-03 coverage note under `## Profile: email`; REQUIREMENTS.md LAB-03 `[x]` with D-01 rationale; UAT-89-03-02 added; no smtp-starttls service in docker-compose.yml. Override: D-01 pre-planning decision in CONTEXT.md |
| 4 | kafka-tls profile: weak-TLS Kafka 3.9.0 container, four-file lab-sync complete (LAB-04) | VERIFIED | `labs/kafka-tls/server.properties` has `ssl.cipher.suites=TLS_RSA_WITH_AES_128_CBC_SHA,...`, `ssl.enabled.protocols=TLSv1.2`, PEM keystore; service in `docker-compose.yml` (L1205); `## Profile: kafka-tls` in expected_results (L650); README row; profiles output confirms |
| 5 | grpc-tls profile: Go gRPC ALPN-h2 server on 39443, D-03 sslyze gate PASSED empirically, four-file lab-sync (LAB-05) | VERIFIED | `labs/grpc-tls/main.go` uses `credentials.NewServerTLSFromFile` (auto-ALPN h2); `Dockerfile` FROM `golang:1.23-alpine`; service in `docker-compose.yml` (L1229); `## Profile: grpc-tls` in expected_results (L682); README row; SUMMARY records sslyze `ServerScanStatusEnum.COMPLETED`, cert CN=grpc-tls.chaos.local RSA-2048 |
| 6 | Identity evidence (DNSSEC + SAML) flows non-zero into identity subscore against live lab; Logger crash fixed (LAB-06) | VERIFIED | `config.yaml` L30-49: enable_kerberos/saml/dnssec true + targets + dnssec_resolver 127.0.0.1:15353; `dnssec_scanner.py` `_parse_resolver()` at L62, resolver threaded through `_resolve_ns`/`_query_rrset`/`_detect_nsec_type`/`_scan_domain`/`scan_dnssec_targets`; `run_scan.py` L1437 passes `cfg.connectors.dnssec_resolver`; `quirk/logging_util.py` has `.warning/.error/.debug` and printf-style `*args`; live scan results: dnssec_weak_algo_count=2, saml_weak_signing_count=2; `scoring.py` L159-161/197-198 reads and weights all three counters |
| 7 | REQUIREMENTS.md updated — LAB-01, LAB-02, LAB-04, LAB-06 rows marked complete | FAILED | REQUIREMENTS.md lines 28-29, 31, 33 still show `- [ ] **LAB-0x**:` (unchecked); traceability table L83-84, 86, 88 show 'pending' for all four. LAB-03 (`[x]`) and LAB-05 (`[x]`) are correctly updated but four requirements were left in 'pending' state. |

**Score:** 5/7 truths verified (including 1 override applied)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `labs/postgres-tls/postgresql.conf` | Weak ssl_ciphers + TLS 1.2 | VERIFIED | Contains `ssl_ciphers = 'AES128-SHA:AES256-SHA'`, TLS 1.2 min/max |
| `labs/redis-tls/redis.conf` | Weak tls-ciphers 3DES/RSA | VERIFIED | Contains `tls-ciphers "DES-CBC3-SHA:AES128-SHA:AES256-SHA"` |
| `labs/kafka-tls/server.properties` | Weak ssl.cipher.suites RSA-KX | VERIFIED | Contains `ssl.cipher.suites=TLS_RSA_WITH_AES_128_CBC_SHA,TLS_RSA_WITH_AES_256_CBC_SHA` |
| `labs/grpc-tls/main.go` | grpc.NewServer with TLS creds | VERIFIED | Uses `credentials.NewServerTLSFromFile` — auto ALPN h2 |
| `labs/grpc-tls/Dockerfile` | Multi-stage FROM golang:1.23-alpine | VERIFIED | FROM golang:1.23-alpine AS builder → FROM alpine:3.20 runtime |
| `quantum-chaos-enterprise-lab/expected_results_v4.md` | Sections for all 4 new profiles + LAB-03 note | VERIFIED | `## Profile: postgres-tls` (L594), `## Profile: redis-tls` (L621), `## Profile: kafka-tls` (L650), `## Profile: grpc-tls` (L682), LAB-03 note under `## Profile: email` (L446) |
| `config.yaml` | enable_kerberos/saml/dnssec + dnssec_resolver | VERIFIED | Lines 30-49: all three connectors true + targets + dnssec_resolver: 127.0.0.1:15353 |
| `quirk/logging_util.py` | stdlib-compatible Logger (warning/error/debug + printf args) | VERIFIED | `.warning`, `.warn`, `.error`, `.critical`, `.exception`, `.debug` all present; `_fmt(*args)` for printf-style |
| `tests/test_phase89_lab_expected_results.py` | Doc-completeness pytest (14 assertions) | VERIFIED | 14 tests, all PASS — confirmed by test run |
| `tests/test_phase89_lab_config_identity.py` | Identity config + resolver API tests (13 assertions) | VERIFIED | 13 tests, all PASS |
| `tests/test_phase89_logger_stdlib_compat.py` | Logger stdlib-compat regression tests (5 assertions) | VERIFIED | 5 tests, all PASS |
| `.planning/REQUIREMENTS.md` | LAB-01/02/04/06 rows `[x]` + traceability 'done' | FAILED | Lines 28-29, 31, 33: unchecked `[ ]`; traceability L83-84, 86, 88: 'pending' |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `docker-compose.yml` | `labs/postgres-tls/postgresql.conf` | volume bind-mount | WIRED | L1164: `../labs/postgres-tls/postgresql.conf:/etc/postgresql/postgresql.conf:ro` |
| `docker-compose.yml` | `labs/grpc-tls/Dockerfile` | build context | WIRED | L1231: `context: ../labs/grpc-tls` |
| `config.yaml` → `run_scan.py` | `quirk/scanner/dnssec_scanner.py` | `scan_dnssec_targets(resolver=...)` | WIRED | `run_scan.py` L1437: `resolver=getattr(cfg.connectors, "dnssec_resolver", None)` |
| `quirk/intelligence/evidence.py` | `quirk/intelligence/scoring.py` | counters → identity subscore | WIRED | `evidence.py` L387-399 emits counters; `scoring.py` L159-161, L197-198 reads and weights them |
| `tests/test_chaos_lab_image_pinning.py` | `docker-compose.yml` | CHAOS-05 version-tag pin gate | WIRED | Test parses compose file and asserts all `image:` entries are tag-pinned; 33 tests pass |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `quirk/intelligence/evidence.py` | `dnssec_weak_algo_count`, `saml_weak_signing_count` | `scan_dnssec_targets()` + `scan_saml_targets()` via `run_scan.py` | Yes — live scan returned 2/2 respectively | FLOWING |
| `quirk/intelligence/scoring.py` | identity subscore | evidence counters via `compute_readiness_score()` | Yes — weights 8.0/8.0 applied to ratios | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `./lab.sh profiles` lists all 4 new profiles | `bash lab.sh profiles` (in quantum-chaos-enterprise-lab/) | postgres-tls, redis-tls, kafka-tls, grpc-tls all listed among 20 profiles | PASS |
| docker-compose config validates | `docker compose config -q` (in quantum-chaos-enterprise-lab/) | Exit 0, no output | PASS |
| CHAOS-05 image-pin gate passes | `pytest tests/test_chaos_lab_image_pinning.py -q` | 15 passed | PASS |
| Doc-completeness gate passes (Task 0) | `pytest tests/test_phase89_lab_expected_results.py -q` | 14 passed | PASS |
| Identity config + resolver tests pass | `pytest tests/test_phase89_lab_config_identity.py -q` | 13 passed | PASS |
| Logger stdlib-compat tests pass | `pytest tests/test_phase89_logger_stdlib_compat.py -q` | 5 passed | PASS |
| `python -m compileall` clean for all modified Python | `compileall quirk/ tests/test_phase89_*.py -q` | No output (clean) | PASS |
| Live profile start + scanner probe (Docker required) | Docker not available in verification env | Cannot run | SKIP — human UAT required |

---

### Probe Execution

Step 7c: No `scripts/*/tests/probe-*.sh` probes exist for Phase 89. Docker-based live probes are deferred to human UAT items below.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|------------|------------|-------------|--------|----------|
| LAB-01 | 89-01 | postgres-tls chaos-lab profile | SATISFIED (codebase) / UNCLOSED (REQUIREMENTS.md) | Profile implemented, four-file lab-sync complete, tests pass. REQUIREMENTS.md checkbox not updated. |
| LAB-02 | 89-01 | redis-tls chaos-lab profile | SATISFIED (codebase) / UNCLOSED (REQUIREMENTS.md) | Profile implemented, four-file lab-sync complete, tests pass. REQUIREMENTS.md checkbox not updated. |
| LAB-03 | 89-03 | smtp-starttls — closed as already-covered (D-01) | SATISFIED + CLOSED | REQUIREMENTS.md `[x]` L30; expected_results_v4.md LAB-03 note; UAT-89-03-02 |
| LAB-04 | 89-01 | kafka-tls chaos-lab profile | SATISFIED (codebase) / UNCLOSED (REQUIREMENTS.md) | Profile implemented, four-file lab-sync complete, tests pass. REQUIREMENTS.md checkbox not updated. |
| LAB-05 | 89-03 | grpc-tls chaos-lab profile (ALPN h2) | SATISFIED + CLOSED | REQUIREMENTS.md `[x]` L32; D-03 empirical gate PASSED; four-file lab-sync |
| LAB-06 | 89-02 | Identity evidence end-to-end | SATISFIED (codebase) / UNCLOSED (REQUIREMENTS.md) | config.yaml identity connectors wired; dnssec+saml counters non-zero in live scan; Logger fixed; kerberos etype deferred with documented caveat. REQUIREMENTS.md checkbox not updated. |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

No debt markers (TBD/FIXME/XXX), placeholder implementations, or stub patterns found in any phase-modified files. The `certs/` directories contain `.gitkeep` placeholders — these are intentional by design (certs generated at lab spin-up, gitignored) and are not stubs.

---

### CLAUDE.md Chaos Lab Maintenance Rule — Compliance Check

The CLAUDE.md rule requires: any chaos lab profile add/change must update `lab.sh ALL_PROFILES + README.md + expected_results_*.md` in the same change.

Per the verified evidence:

| Profile | docker-compose.yml | lab.sh auto-derive | README row | expected_results section | Compliant |
|---------|-------------------|-------------------|------------|--------------------------|-----------|
| postgres-tls | WIRED | WIRED (auto from compose) | PRESENT | PRESENT (L594) | YES |
| redis-tls | WIRED | WIRED (auto from compose) | PRESENT | PRESENT (L621) | YES |
| kafka-tls | WIRED | WIRED (auto from compose) | PRESENT | PRESENT (L650) | YES |
| grpc-tls | WIRED | WIRED (auto from compose) | PRESENT | PRESENT (L682) | YES |

The `lab.sh` uses `_derive_all_profiles()` (dynamic yq/grep-based derivation — no hardcoded ALL_PROFILES list), so adding a service to `docker-compose.yml` with a `profiles:` key is sufficient. CLAUDE.md maintenance rule is fully honored for all four new profiles.

---

### Human Verification Required

#### 1. Kerberos identity_weak_etype_count (deferred from orchestrator)

**Test:** Install the `identity` extra (`pip install -e '.[identity]'`), stop the system KDC on macOS, then bring up `LAB_INCLUDE_KERBEROS=1 PROFILE_ARGS="--profile kerberos" ./lab.sh up`. Run `QUIRK_DB_PATH=./quirk.db quirk scan --config config.yaml`. Inspect `output/intelligence-*.json` for `identity_weak_etype_count`.

**Expected:** `identity_weak_etype_count > 0` and the identity subscore reflects it.

**Why human:** Requires impacket installation + live Kerberos KDC container; macOS port-88 collision makes this impossible in a non-Linux environment without stopping the system KDC. The wiring is confirmed correct (counter code at `evidence.py` L165; scoring at `scoring.py` L159/196); the gap is environmental only.

#### 2. Live scanner scans against all new chaos-lab profiles

**Test:** For each profile — bring it up via `PROFILE_ARGS="--profile <name>" ./lab.sh up`, then run `QUIRK_DB_PATH=./quirk.db quirk scan --config config.yaml --allow-internal-targets`. Confirm the findings match `expected_results_v4.md`.

**Expected:**
- postgres-tls (39432): HIGH weak-cipher + MEDIUM RSA-2048
- redis-tls (39380/39379): HIGH weak-cipher + HIGH plaintext-port
- kafka-tls (39092/39093): HIGH plaintext + HIGH weak-cipher + MEDIUM RSA-2048
- grpc-tls (39443): RSA-2048 MEDIUM only (no HIGH — ECDHE-RSA PFS via Go TLS defaults, per D-03)
- email (30587): SMTP-STARTTLS HIGH (LAB-03 proof)

**Why human:** Docker required; cannot start containers in the verification environment. The D-03 sslyze result was recorded empirically by the executor in 89-03-SUMMARY.md.

---

### Gaps Summary

**One real gap:** REQUIREMENTS.md was not updated by the executor for requirements LAB-01, LAB-02, LAB-04, and LAB-06. The implementations are complete and tested in the codebase — this is purely a tracking/documentation gap in `.planning/REQUIREMENTS.md`. The fix is straightforward: flip four checkboxes and update four traceability table rows to `✅ done`.

**One partial gap:** The LAB-06 closure note in REQUIREMENTS.md should document the kerberos etype deferral explicitly so the audit trail is clear when v5.0 milestone is closed.

**No implementation gaps.** All four new lab profiles (postgres-tls, redis-tls, kafka-tls, grpc-tls) are substantively implemented with real weak-TLS configs, complete Makefiles, and full lab-sync. The identity wiring (config.yaml + dnssec_scanner.py resolver override + Logger fix + evidence→scoring chain) is live. All 33 automated tests pass.

The root cause: the 89-01-PLAN.md did not list `.planning/REQUIREMENTS.md` in `files_modified`, and the 89-02-PLAN.md similarly omitted it. Only 89-03-PLAN.md modified REQUIREMENTS.md (for LAB-03 and LAB-05), leaving the other four requirements untracked.

---

_Verified: 2026-05-22T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
