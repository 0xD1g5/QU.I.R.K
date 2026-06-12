# Changelog

All notable changes to QU.I.R.K. (Quantum Infrastructure Readiness Kit) are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

<!-- towncrier release notes start -->

## [5.6.0] - 2026-06-12

### Added

- **Public launch** (Phase 119–120) — QU.I.R.K. is now an open-source public repository on GitHub with branch protection on `main` and `windows-sensor-smoke` enforced as a required CI status check. A full git-history secret scan (gitleaks, 0 findings across 2652+ commits) preceded the visibility flip; Actions SHA-pinning (all 30 uses:) and SECURITY_CHECKLIST canonicalization completed the posture sweep (Phase 120).
- **Windows production build — frozen sensor binary** (Phase 117) — production PyInstaller `--onedir` build of the QUIRK sensor on `windows-latest` CI; `quirk.exe --version` and `quirk.exe --help` confirmed on a runner with no Python installed; data-file and hidden-import set locked from the WINPKG-01 spike.
- **Windows packaging + Scheduled Task installer** (Phase 118) — zip + PowerShell `install.ps1` / `uninstall.ps1` pair; registers a Windows Scheduled Task for periodic sensor cadence; frozen sensor passes Phase 113 per-sensor Bearer-token wire contract in E2E CI; Windows zip published as a GitHub Release asset alongside PyPI/GHCR/Homebrew. (Unsigned — Authenticode deferred.)
- **Port-scope discovery control** (Phase 121) — dashboard scan-new form offers four port-scope options (Common TLS / Top 1000 / All ports / Custom); nmap discovery decoupled from the hardcoded 6-port TLS list; wide-scope jobs hard-fail without nmap rather than silently using 6 ports; custom port specs cap at 2048 expanded ports with strict nmap-style parse/validation; `GET /api/jobs/{id}/result-summary` returns an explicit zero-endpoints completion signal so stale data is never displayed.

### Fixed

- **Phase 122 tech-debt sweep** (11 audit items from 2026-05-27 codebase audit):
  - CR-01: Phantom +20 TLS-enum confidence bonus guarded on `tls_count > 0` — zero-TLS scans no longer receive unearned coverage credit (commit c60d1bd).
  - CE-01: AKS scanner now emits an advisory finding (K8S-03 invariant) instead of silently returning `[]` when valid credentials yield an empty cluster list (commit c20245e).
  - CE-02: `safe_str` base64 redaction regex tightened with a negative lookbehind + first-char guard; ARNs and resource IDs no longer over-redacted (commit ef6aeab).
  - CE-03: Vault PKI SHA-1 reason field always populated when detected, even on dual-weakness (RSA+SHA-1) certificates (commit ef6aeab).
  - CE-05: Engine safe-mode concurrency default aligned to 200 baseline — was erroneously 100 (a 2× divergence) (commit ef6aeab).
  - QC-01: Explicit `int()` cast on QRAMM `suggested_answer` — eliminates silent SQLite float→integer coercion (commit b14cdd9).
  - QC-04: `compute_overall_score` itself now clamped at 4.0 — prior BL-01 fix was router-only (commit b14cdd9).
  - QC-05: Compliance staleness gate moved to production code path (`check_compliance_staleness()` in `quirk/compliance/__init__.py`); malformed `last_verified` dates raise `RuntimeError` instead of silently continuing (commit 8539f99).
  - WR-01: `md_cell` now strips DEL (0x7f) and C1 control range (0x80–0x9f); previously kept by `c >= "\\x20"` guard (commit eba210a).
  - WR-06: `html_renderer` no-`exec_content` fallback reads canonical `score["score"]` key, not the non-existent `"total"` key (commit eba210a).
  - Stub-label: AWS and Azure connector prompts in `quirk/interactive.py` confirmed production-grade (stub labeling already absent from prior phase work).

### Misc

- Windows distribution is unsigned — Authenticode code-signing deferred to a future spike (needs certificate + CI secret handling).
- Phase 120 git-history rewrite: 12 sensitive path categories stripped from history; 989 → 901 tracked files, 6260 → 2952 commits after empty-commit pruning.

## [5.5.0] - 2026-05-27

### Added

- **Per-sensor authentication & revocation** (Phase 113) — distributed-mode sensors now enroll with opaque Bearer tokens individually issued and individually revocable via `quirk revoke-sensor`; new `revoked_at` migration on the sensors table; console rejects requests from revoked tokens.
- **Failure-isolated auto-merge** (Phase 114) — when one sensor fails mid-scan, the console merges the remaining successful results into a CBOM and final score rather than discarding the batch; operators guide §8.9 documents the partial-merge contract.
- **Weak-TLS chaos-lab target** (Phase 115) — added intentionally-weak TLS profile to widen scanner regression surface; live-UAT stabilization sweep cleared 4 follow-up items.

### Fixed

- Phase 114 inverted revoked-filter caught in code review pre-ship.
- Phase 115 cron crash on absent schedule resolved.
- Phase 116 over-broad hard-gate narrowed.

### Misc

- Windows packaging spike (Phase 116) — onedir frozen sensor build confirmed GO via live windows-latest CI run.

## [5.4.0] - 2026-05-26

### Added

- **Distributed on-prem scanner** (Phases 106–112) — sensor / console architecture: scan-per-segment on isolated sensors, push findings to a central console, merge into one CBOM + final score (Option A merge: keep newest-per-fingerprint, never rewrite `scanned_at`).
- **`enroll` + `--sensor-id` CLI surface** for sensor-to-console pairing.
- **`crypto.internal` hostname-alias** pattern for same-subnet docker compose validation (compose forbids same-subnet networks; alias works around).
- **Sensor SSRF mitigation** corrected to allow internal console targets while still blocking external SSRF paths.

### Fixed

- Discarded CBOM artifact on partial-success scans (caught by code review, not unit verification).
- `_run_local_scan --output` path resolution (caught by live E2E).

## [5.3.0] - 2026-05-25

### Added

- **Notification fan-out** (Phase 101) — webhook + email + Slack dispatch on schedule completion or finding severity threshold.
- **SIEM CEF dispatch** (Phase 102) — Common Event Format export for Splunk / QRadar / ArcSight ingestion.
- **Jira / ServiceNow ticketing** (Phase 103) — automatic ticket creation on high-severity findings with secret-scrubbing applied to ticket bodies.
- **Dashboard token auth** (Phase 105) — bearer-token gate on dashboard API to prevent unauthenticated query of stored scans.

### Fixed

- Fingerprint formula corrected to `SHA256(host:port::title)` for finding deduplication.
- Shared SSRF-safe / secret-scrubbing layer (Phase 101 anchor) unifies outbound HTTP across notification / SIEM / ticketing surfaces.

## [5.2.0] - 2026-05-24

### Added

- **Consulting-grade reporting** (Phases 97–100) — one shared content model drives CLI markdown, HTML, PDF, and new DOCX renderers; eliminates render-divergence across surfaces.
- **DOCX renderer** (`quirk/reports/docx_renderer.py`) — client-deliverable Word format with consultant-editable narrative blocks.
- **Code-signing endpoint evaluation** — LDAP+TLS-EKU based codesign certificate posture wired into agility scoring.

### Fixed

- CLI score sourcing aligned with executive narrative content (logged backlog item v5.2-TD-1 closed in v5.3).

## [5.1.0] - 2026-05-22

### Added

- **Authenticated scanning** (Phases 93–96) — ephemeral credentials for JWT API + cloud connector scans; no long-lived secret storage in scheduled scan rows.
- **Query-param API-key CLI flag** + JWT-scanner URL credential consumption (Phase 93 D-1, full delivery in 93 not 94).
- **Code-signing posture** (Phase 95) — LDAP+TLS-EKU only; fuzzing non-TTY hard-abort guard; schemathesis excluded from `[all]` extra.
- **Agility subscore** absorbs codesign signals; no separate 7th subscore.

### Fixed

- SCORE_WEIGHTS walks 283 → 293 → 299 → 303 across the v5.1 milestone.


## [5.0.0] - 2026-05-22

### Added

- Added four weak-TLS chaos-lab profiles (postgres-tls port 39432, redis-tls ports 39380/39379, kafka-tls ports 39093/39092, grpc-tls port 39443) with intentional RSA-2048 / RSA-KX ciphers, plus a Go gRPC multi-stage Docker build with empirically-confirmed sslyze ALPN-h2 compatibility (LAB-03 SMTP STARTTLS closed as already covered by the email profile). (v5.0-89)
- Added OQS-nginx PQC-hybrid chaos-lab profile (port 39444) serving TLS 1.3 with X25519MLKEM768 hybrid KEM and ML-DSA-65 certificate (digest-pinned openquantumsafe/nginx image, sha256:6ca18ac6); live openssl s_client probe detects X25519MLKEM768 group negotiation; agility scoring gains an agility_pqc_hybrid_bonus weight of +8.0 that anchors the scoring ceiling for post-quantum readiness. (v5.0-90)

### Fixed

- Added six-subscore N/25 decomposition block to CLI markdown, executive markdown, and HTML/PDF report surfaces so reviewers can see per-category scores alongside the overall readiness number; CBOM builder now emits affirmative coverage-note properties for five formerly-zero-algorithm profiles (database, registry, source, ssh-weak, storage-s3) closing Phase 42 OBS-1; forward-locking orthogonality and render-parity tests lock the single scoring engine as invariant. (v5.0-88)

### Misc

- v5.0-87, v5.0-91


## [4.10.1] - 2026-05-22

### Fixed

- Overall readiness no longer caps at 100 on real scans. The previous aggregator summed six 0–25 subscores and clamped at 100, masking real posture issues. Overall readiness is now `int(round(sum_of_subscores / 1.5))`; dashboard subscore radials now render against `maxValue=25` so a perfect category shows green and a depleted category shows red.

  **Before / After (canonical example):**

  | Subscores | Sum | Overall (before) | Rating (before) | Overall (after) | Rating (after) |
  |-----------|-----|-----------------|-----------------|-----------------|----------------|
  | 25+25+23+3+25+19 | 120 | **100** | EXCELLENT | **80** | GOOD |

  Old stored scores will display lower after upgrade. The underlying per-category penalty math is unchanged — only the aggregation and dashboard scale are corrected. To refresh a stored score, re-render or re-scan. (v4.10.1)


## 4.4.0 - 2026-04-29

**Milestone:** v4.4 Data in Motion — full release notes: [docs/release-notes/4.4.0.md](docs/release-notes/4.4.0.md)

### Added

- **Email protocol scanning** (Phase 32, EMAIL-01..12): SMTP/SMTPS, submission, IMAP/IMAPS,
  POP3/POP3S TLS posture with STARTTLS-stripping detection on port 25, weak-cipher
  detection on email TLS endpoints, and a new `email` Docker chaos lab profile (Postfix +
  Dovecot with intentionally weak TLS).
- **Message broker TLS scanning** (Phase 33, KAFKA-01..04, RABBIT-01..05, REDIS-01..03,
  BROKER-LAB-01/02): Kafka (9092/9093/9094), RabbitMQ AMQPS (5671) + management API (15672),
  Redis TLS (6380), Azure Service Bus AMQPS (5671), AWS SQS HTTPS (443). Plaintext-listener
  HIGH findings for all three local broker types. New `broker` Docker chaos lab profile
  (Kafka + RabbitMQ + Redis with weak TLS configs).
- **Data-in-motion intelligence** (Phase 34, MOTION-01..04): six new `motion_*` evidence
  counters in the intelligence summary, three new `motion_*_ratio` scoring weights with
  profile multipliers (strict / balanced / lenient), and a `data_in_motion` 6th subscore
  alongside `tls`, `ssh`, `api`, `identity`, and `data_at_rest`. Legacy scans without
  motion keys preserve full credit (D-12 backward compatibility).
- **Motion CBOM integration** (Phase 35, CBOM-01..04): email and broker TLS endpoints
  generate Pass-1 algorithm components with quantum-safety classification; plaintext-only
  endpoints (`KAFKA-PLAIN`, `AMQP-PLAIN`, `REDIS-PLAIN`, `SMTP-STARTTLS`) are excluded from
  Pass-2/Pass-3 to prevent hollow certificate entries. AMQPS/Azure-ServiceBus passes
  through the default-TLS branch unchanged.
- **Dashboard Motion tab** (Phase 36, DASH-01..05): new `/motion` React route with email
  and broker surface sections, a "Data in Motion" line on the executive summary card, and
  a `motion_findings` field on `/api/scan/latest`.
- **`[motion]` meta-extra** (Phase 37, INFRA-02): `pip install quirk[motion]` is now the
  single happy path; pulls in `quirk[email]`, `quirk[broker]`, and `quirk[kafka]` flat
  sub-extras. Each remains independently installable.
- **INFRA-03 Nyquist coverage** (Phase 37): new `tests/test_infra03_nyquist_coverage.py`
  module with 18 explicit tests — 6 scanner entry points × happy / refused / plaintext-only.
- **Version-regression lock** (Phase 37, INFRA-01): new `tests/test_version.py` asserting
  `quirk.__version__`, CBOM `PLATFORM_VERSION`, report `PLATFORM_VERSION`,
  `INTELLIGENCE_VERSION`, and `IntelligenceCfg.intelligence_version` all read 4.4.0.

### Changed

- **Version bumped to 4.4.0** across `quirk/__init__.py`, `pyproject.toml`,
  `quirk/cbom/builder.py` (CBOM tool metadata), `quirk/reports/writer.py` (report header),
  and `quirk/config.py` `intelligence_version` default.
- **`pyproject.toml [project.optional-dependencies]`** restructured: `motion` is now a
  meta-extra over `email` (no non-core deps), `broker` (`redis>=5.0`), and `kafka`
  (`kafka-python>=2.0`).

### Fixed

- Stale `PLATFORM_VERSION = "4.2.0"` and `INTELLIGENCE_VERSION = "4.2.0"` in
  `quirk/reports/writer.py` (carried over since v4.2) now reflect the current 4.4.0 platform
  version.
- Stale version-regression assertions in `tests/test_packaging.py`,
  `tests/test_v41_gap_closure.py`, and `tests/test_cli_correctness.py::test_version_consistency`
  bumped from 4.1.0/4.2.0 to 4.4.0 (Plan 37-04 sweep).
- Five legacy `quirk scan` CLI references in `docs/UAT-SERIES.md` (lines 1526, 3866, 4772,
  4833, 4835) replaced with the modern `quirk --config` invocation.

### Documentation

- This CHANGELOG, sourced from each phase's SUMMARY.md.
- `docs/release-notes/4.4.0.md` standalone narrative.
- `docs/UAT-SERIES.md` updated with v4.4 test cases (per Phase 37 close-out).
- Per-phase `VALIDATION.md` files for phases 32, 33, 34, 35, and 37 all read
  `nyquist_compliant: true` and `wave_0_complete: true`. Phase 36's flip is deferred
  pending an unrelated SAML scan-window regression (ISSUE-3 from Phase 24).

---

*Earlier milestones: see `.planning/milestones/v4.3-ROADMAP.md`, `v4.2-ROADMAP.md`,
`v4.1-ROADMAP.md`, `v3.9-ROADMAP.md` for the full historical record. v4.4 is the first
milestone with a top-level CHANGELOG.md.*
