# Changelog

All notable changes to QU.I.R.K. (Quantum Infrastructure Readiness Kit) are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

<!-- towncrier release notes start -->

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
