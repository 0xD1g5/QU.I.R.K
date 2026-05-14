# Requirements: QU.I.R.K. v4.8 Pre-Primetime Hardening + Operating Model

**Defined:** 2026-05-09
**Core Value:** Complete, defensible cryptographic inventory with a CBOM deliverable and quantum-readiness score — handed to a client in under two hours.

**Milestone goal:** Close all 15 audit-identified blockers (Wave A) and ship the operating-model features that turn QU.I.R.K. into a deploy-and-forget platform (Wave B). Wave A is gating; Wave B cannot start until all Wave A phases are complete.

**Source documents:**
- Audit: `.planning/audit-2026-05-08/AUDIT-SUMMARY.md` (44 blockers, 96 warnings, 29 info across 116 files / 6 subsystems)
- Outlook: `.planning/HORIZON.md` — v4.8 framed as primetime cutover

---

## v4.8 Requirements

### Wave A — Pre-Primetime Hardening (gates Wave B)

#### Scanner Security Hardening
*Closes audit blockers 1–6 (`scanners-protocol/CR-01..CR-06`). Phase 57.*

- [ ] **HARDEN-SCAN-01**: JWKS fetch in `quirk/scanner/jwt_scanner.py` enables TLS verification by default; the operator-facing flag to disable verification (if any) is renamed, gated behind an explicit config knob, and emits a HIGH advisory finding when used (closes CR-01)
- [ ] **HARDEN-SCAN-02**: SAML scanner HTTP fetcher routes through a shared URL-allowlist helper that rejects RFC1918 ranges, link-local, loopback, `file://`, and metadata-service IPs (169.254.169.254, fd00:ec2::254) unless an explicit `--allow-internal-targets` flag is set (closes CR-04)
- [ ] **HARDEN-SCAN-03**: `quirk/scanner/source_scanner.py` validates `repo_path` against a path-allowlist (existing local directory, no shell metacharacters) before invoking `subprocess.run` for semgrep (closes CR-02)
- [ ] **HARDEN-SCAN-04**: `quirk/scanner/container_scanner.py` validates `image_ref` against a regex allowlist (registry/image:tag form), rejecting `dir:/`, `file://`, and any value containing shell metacharacters before invoking syft (closes CR-03)
- [x] **HARDEN-SCAN-05**: `quirk/scanner/broker_scanner.py` no longer ships a hardcoded `guest:guest` Basic-auth credential to every host; default behavior probes anonymously, and any credential probe requires an explicit per-target opt-in via config (closes CR-05)
- [x] **HARDEN-SCAN-06**: Broker management API and Redis probes default to TLS-required and reject `ssl_cert_reqs="none"`; cleartext probes require an explicit `--allow-cleartext-broker-probe` flag and emit a HIGH advisory finding (closes CR-06)

#### Dashboard API Hardening
*Closes audit blockers 7–10 (`api-cli-core/CR-01..CR-03, CR-09`). Phase 58.*

- [ ] **HARDEN-API-01**: Every mutating dashboard route requires a single-user bearer token loaded from config or environment; missing/invalid token returns 401 before route logic runs; CSRF token required on browser-form requests (closes CR-03 — auth)
- [ ] **HARDEN-API-02**: CORS middleware is locked down to a configurable allowlist (default `127.0.0.1` and `localhost` only); preflight rejection for unknown origins returns 403 with no body (closes CR-03 — CORS)
- [ ] **HARDEN-API-03**: Rate-limit middleware applies per-route token-bucket limits to mutating routes (default 60 req/min/IP) with 429 on exhaustion; informational routes exempted (closes CR-03 — rate-limit)
- [ ] **HARDEN-API-04**: `quirk init` validates `output_path` against a path-traversal allowlist (resolved path must descend from CWD or an explicit `--target` directory); rejects `..`, absolute paths outside allowlist, and symlinks pointing outside the allowlist (closes CR-01)
- [ ] **HARDEN-API-05**: `routes/pdf.py` validates `QUIRK_SERVE_PORT` against an integer-port allowlist (1024–65535) and binds outbound fetches to localhost only (closes CR-02)
- [ ] **HARDEN-API-06**: `@file` target loading enforces a path allowlist (no traversal outside `--target` dir, no absolute paths to `/etc`, `/proc`, `/sys`, `/dev`), a maximum file size (default 1 MB), and a maximum target-line count (default 10,000) (closes CR-09)

#### Credential Leakage Sweep
*Closes audit blocker 11 + Pattern A (cross-subsystem). Phase 59.*

- [x] **LEAK-01**: A shared `quirk/util/safe_exc.py::safe_str(exc)` helper returns `f"{type(exc).__name__}"` by default and scrubs known-sensitive substrings (token-like strings, connection-string passwords, GCP ADC paths) from the exception message before returning
- [x] **LEAK-02**: Every connector that persists `scan_error` (vault, GCP, AWS, DB, broker, email, identity) routes exception text through `safe_str(exc)`; raw exception stringification (`f"...: {exc}"`) is removed from connector error paths
- [x] **LEAK-03**: A pytest gate enumerates all `scan_error` writes via AST scan and fails the build if any new caller bypasses `safe_str(exc)` (mirrors the `_build_finding` chokepoint pattern from v4.6 Phase 48)

#### Score Arithmetic Correctness
*Closes audit blockers 12, 15 + Pattern E. Phase 60.*

- [x] **SCORE-01**: Total readiness score is clamped to `[0, 100]` at the top-level emission point in `quirk/intelligence/scoring.py`; reports never display a value above 100 (closes CR-06)
- [x] **SCORE-02**: QRAMM profile multiplier is clamped server-side to `[0.8, 1.5]` regardless of client-supplied value; client values outside the range are rejected with 400 and the canonical range is documented in the API schema (closes BL-01)
- [x] **SCORE-03**: Confidence bonus is awarded only when at least one TLS endpoint is scanned; zero-data scans receive zero confidence bonus instead of the current 20-point default
- [x] **SCORE-04**: QRAMM maturity threshold bands are closed and contiguous — every score in `[0, 100]` maps to exactly one maturity level; threshold gap audit covered by parametrized test sweeping at 0.5-point increments

#### CBOM Coverage + Report Sanitization
*Closes audit blockers 13, 14. Phase 61.*

- [x] **CBOM-COVER-01**: CBOM Pass-1 emits at least one algorithm component for each of the 12+ protocol families currently dropping zero algos (database, registry, source, ssh-weak, storage-s3, broker subfamilies, email subfamilies, vault, identity-secondary); per-protocol coverage assertion in test suite (closes CR-01)
- [x] **CBOM-COVER-02**: VAULT classification is consistent across Pass-1 / Pass-2 / Pass-3 — Pass-1 routes to a vault-specific branch (not the TLS branch), Pass-2 and Pass-3 emit the same evidence claims about the vault endpoint
- [x] **REPORT-SAN-01**: All adversary-controllable strings (host, cipher_suite, cert_subject, cert_issuer, finding text, banner, evidence note) interpolated into markdown report tables are escaped so that pipe (`|`) and newline characters cannot break table rendering or inject content (closes CR-07)
- [x] **REPORT-SAN-02**: A pytest fixture renders both the technical and executive markdown reports against a corpus of adversarial inputs (pipes, newlines, backticks, HTML entities, control characters) and asserts the output is a valid GFM table

#### React Hook Cancellation Pattern
*Closes Pattern C (cross-frontend). Phase 62.*

- [x] **HOOK-01**: A standardized cancellation pattern (`useCancellableFetch` or equivalent) is used by every data-fetch hook in `src/dashboard/src/hooks/` (`useScanData`, `useQRAMMSession`, `useTrendData`, etc.); each hook gates state-setters with an `if (!cancelled)` check after every async boundary
- [x] **HOOK-02**: QRAMM debounce coalescing is fixed so that rapid answer changes during a single debounce window POST a single coalesced batch instead of stale per-keystroke partials
- [x] **HOOK-03**: Auto-fill confirm round-trip preserves the badge-removal contract (badge disappears when `confirmed_at` is set) without requiring a full session refetch
- [x] **HOOK-04**: A custom ESLint rule (or codemod check in CI) flags `useEffect` blocks that call `setState` from an async branch without an `if (!cancelled)` guard

### Wave B — Operating Model (gates on Wave A complete)

#### Scheduled / Continuous Scanning
*BACK-25. Phase 63.*

- [x] **SCHED-01**: Operator can register a scan schedule via `quirk schedule add --name <X> --cron <expr> --target <Y>` that persists to a new `scheduled_scans` SQLite table with cron expression, target spec, profile, and enabled flag
- [x] **SCHED-02**: A `quirk scheduler run` long-running mode dispatches scheduled scans at their cron times, writes scan results to the standard scan output path, and surfaces dispatch status to the dashboard
- [x] **SCHED-03**: Dashboard `/schedules` route lists scheduled scans, their next-run time, last-run status, and provides enable/disable toggles

#### Trend Analysis Foundation
*BACK-21. Phase 64.*

- [ ] **TREND-01**: The dashboard `/trends` route renders a multi-scan timeline of overall readiness score, per-pillar subscores, and finding counts across the last N scans (default 30)
- [ ] **TREND-02**: Trend regressions (score drop ≥ 5 points OR new HIGH/CRITICAL finding category) are surfaced as alert chips on the dashboard home with deep-links to the regressing scan

#### Dashboard-Initiated Scan
*BACK-86 slice 1. Phase 65.*

- [ ] **UI-SCAN-01**: A `/scan/new` dashboard route lets operators configure a scan (target spec, profile, options) via form, validate inputs against the same Pydantic schema the CLI uses, and submit
- [ ] **UI-SCAN-02**: Scan submission spawns the scan via the dashboard backend with a job ID; a live status page polls progress and streams scanner stage transitions to the UI
- [ ] **UI-SCAN-03**: On scan completion, the UI navigates to the scan results view and the new scan is selectable from the scan switcher

#### Dashboard Scan History + Clone/Compare
*BACK-86 slice 2. Phase 66.*

- [x] **UI-HIST-01**: A `/scans` route lists all scans with date, target, profile, overall score, and a "Clone configuration" button that pre-fills the `/scan/new` form
- [x] **UI-HIST-02**: A "Compare" mode on `/scans` lets the operator pick any two scans and renders a diff view (score deltas, added/removed findings, changed endpoint posture)

#### Resumable / Partial-Failure Scans
*Phase 67.*

- [x] **RESUME-01**: A scan that crashes mid-run leaves a recoverable checkpoint in `scan_checkpoints` SQLite table; `quirk scan --resume <scan-id>` continues from the last completed scanner stage
- [x] **RESUME-02**: Per-scanner failures (e.g., one cloud connector errors but TLS succeeds) no longer abort the whole scan — the scan completes with a `partial_failures` array in the output and a per-scanner status panel in the dashboard

#### Operator Error-Message Pass
*Phase 68.*

- [x] **UX-01**: Every operator-facing error path (CLI exit, dashboard 4xx/5xx, scan_error_category rows) includes a one-line cause, a one-line remediation hint, and a stable error code; an `quirk errors` reference page documents all codes
- [x] **UX-02**: First-run install-day errors (missing extras, missing nmap binary, port-conflict on `quirk serve`) render with the same one-line-cause + one-line-fix format

---

## Validated Requirements

### v4.7 — Governance & Compliance Platform (Shipped 2026-05-08)

#### Compliance Extensions

- [x] **COMPLY-10**: CBOM Pass-1 algorithm components carry a 3-tier FIPS 140-3 status annotation (`certified` / `approved` / `non-approved`) via `Component.properties` — only endpoints with verifiable CMVP-validated evidence receive `certified`; all others receive `approved` or `non-approved` based on algorithm classification
- [x] **COMPLY-11**: SOC2 CC6.x controls (cryptography-relevant Common Criteria subset) are mapped to QUIRK finding categories in `COMPLIANCE_MAP` via a `_soc2()` helper following the existing `_pci()` / `_hipaa()` / `_fips()` builder pattern
- [x] **COMPLY-12**: ISO 27001:2022 Annex A controls (8.x clause numbering, not 2013 A.x.x) are mapped to QUIRK finding categories via an `_iso()` helper; the framework entry declares `version: "ISO 27001:2022"` and is unit-tested to reject 2013-style `A.x.x` control IDs

#### QRAMM Core Infrastructure

- [x] **QRAMM-01**: SQLite gains three new normalized tables — `qramm_sessions`, `qramm_answers`, `qramm_profiles` — created via `_ensure_qramm_tables()` in `db.py:init_db()`
- [x] **QRAMM-02**: FastAPI router at `/api/qramm/` provides CRUD endpoints for the assessment lifecycle
- [x] **QRAMM-03**: `quirk/qramm/questions.py` contains the full 120-question catalog as a versioned `QRAMM_QUESTIONS` constant
- [x] **QRAMM-04**: `quirk/qramm/scoring.py` computes dimension scores using the weakest-link minimum rule

#### QRAMM Staleness Enforcement

- [x] **QRAMM-05**: `QRAMM_MODEL` module constant in `quirk/qramm/model_meta.py` carries `qramm_version`, `last_verified`, and `source_url`
- [x] **QRAMM-06**: CI pytest gate fails when `QRAMM_MODEL.last_verified` is more than 90 days old
- [x] **QRAMM-07**: `quirk qramm status` CLI subcommand displays staleness metadata and verdict

#### QRAMM Assessment Experience

- [x] **QRAMM-08**: React QRAMM Assessment page presents 120 questions across 4 dimension tabs
- [x] **QRAMM-09**: Org Profile wizard collects organization inputs and computes profile multiplier
- [x] **QRAMM-10**: All 120 assessment answers live in top-level React context with debounced draft persistence
- [x] **QRAMM-11**: QRAMM Scorecard displays radar chart, dimension summary table, and maturity distribution

#### QRAMM Evidence Bridge

- [x] **QRAMM-12**: At session creation the evidence bridge auto-populates CVI dimension questions via SESSION_BRACKET pattern
- [x] **QRAMM-13**: Auto-populated answers are stored in `suggested_answer` with `requires_confirmation: true`
- [x] **QRAMM-14**: Auto-filled answers display an "Auto-filled from scan" badge; badge removed when human modifies/confirms

#### QRAMM Governance Artifacts

- [x] **QRAMM-15**: Dashboard QRAMM Compliance Mapping view shows 8-framework coverage table
- [x] **QRAMM-16**: Combined PDF export includes a QRAMM section starting on a new page

#### Health & Diagnostics

- [x] **DOCS-05**: `quirk doctor` CLI subcommand performs a health check across 8 categories

#### Tech Debt

- [x] **DEBT-01**: All `datetime.utcnow()` calls replaced with `datetime.now(timezone.utc)` (BACK-56)
- [x] **DEBT-02**: `lab.sh` PROFILE_ARGS CLI precedence fixed (BACK-87)
- [x] **DEBT-03**: `run-stats-*.json` includes `ports_scanned` and `hosts_scanned` (BACK-85)
- [x] **DEBT-04**: SAML scanner migrated from `defusedxml.lxml` to raw `lxml.etree` (BACK-67)

### Earlier milestones (v4.0 – v4.6)

See `.planning/MILESTONES.md` for full validated requirement history per milestone.

---

## Future Requirements

Items that may surface in v4.9+ or later:

- **CBOM Coverage Expansion** — protocol families beyond the 12+ closed in v4.8
- **Trend Analysis Depth** — anomaly detection, baseline drift alerting, multi-tenant trend isolation
- **Distributed Scanning Nodes** — multi-node scan dispatch, central aggregation (BACK-26)
- **Multi-User Auth** — beyond v4.8's single-user bearer token: roles, audit log, SSO

---

## Out of Scope

Items explicitly deferred and not in v4.8:

| Item | Reason |
|---|---|
| Markdown injection in reports → HTML/PDF surface | Wave A REPORT-SAN-01 handles markdown; HTML/PDF rendering injection is a separate audit shape |
| Advisor false-positives (audit WR-09 scanners-cloud) | Non-blocking polish; defer to dedicated tuning pass |
| Dead code cleanup (`tls_scanner.py`, `intelligence/schema.py`, `migration_planner.py` stub) | Fits v5.x chaos lab + tech debt sweep, not v4.8 hardening |
| `risk_engine.py` rename (misnamed — it's a findings evaluator) | Pure rename; defer to v5.x tech debt sweep |
| Multi-user / RBAC dashboard | v4.8 ships single-user bearer token; multi-user is a separate milestone |
| Performance profiling pass | Audit excluded runtime measurement; warrants dedicated phase |
| Test correctness audit (excluded from 2026-05-08 audit) | Separate audit shape |
| Chaos lab audit (excluded from 2026-05-08 audit) | Separate audit shape |

---

## Traceability

Populated by the roadmapper. Updated at each phase transition.

**Coverage:** 41/41 active v4.8 requirements mapped (100%) — Wave A: 27 reqs across Phases 57–62 | Wave B: 14 reqs across Phases 63–68

| Requirement | Phase | Status |
|-------------|-------|--------|
| HARDEN-SCAN-01 | Phase 57 | Pending |
| HARDEN-SCAN-02 | Phase 57 | Pending |
| HARDEN-SCAN-03 | Phase 57 | Pending |
| HARDEN-SCAN-04 | Phase 57 | Pending |
| HARDEN-SCAN-05 | Phase 57 | Complete |
| HARDEN-SCAN-06 | Phase 57 | Complete |
| HARDEN-API-01 | Phase 58 | Pending |
| HARDEN-API-02 | Phase 58 | Pending |
| HARDEN-API-03 | Phase 58 | Pending |
| HARDEN-API-04 | Phase 58 | Pending |
| HARDEN-API-05 | Phase 58 | Pending |
| HARDEN-API-06 | Phase 58 | Pending |
| LEAK-01 | Phase 59 | Complete |
| LEAK-02 | Phase 59 | Complete |
| LEAK-03 | Phase 59 | Complete |
| SCORE-01 | Phase 60 | Complete |
| SCORE-02 | Phase 60 | Complete |
| SCORE-03 | Phase 60 | Complete |
| SCORE-04 | Phase 60 | Complete |
| CBOM-COVER-01 | Phase 61 | Complete |
| CBOM-COVER-02 | Phase 61 | Complete |
| REPORT-SAN-01 | Phase 61 | Complete |
| REPORT-SAN-02 | Phase 61 | Complete |
| HOOK-01 | Phase 62 | Complete |
| HOOK-02 | Phase 62 | Complete |
| HOOK-03 | Phase 62 | Complete |
| HOOK-04 | Phase 62 | Complete |
| SCHED-01 | Phase 63 | Complete |
| SCHED-02 | Phase 63 | Complete |
| SCHED-03 | Phase 63 | Complete |
| TREND-01 | Phase 64 | Pending |
| TREND-02 | Phase 64 | Pending |
| UI-SCAN-01 | Phase 65 | Pending |
| UI-SCAN-02 | Phase 65 | Pending |
| UI-SCAN-03 | Phase 65 | Pending |
| UI-HIST-01 | Phase 66 | Complete |
| UI-HIST-02 | Phase 66 | Complete |
| RESUME-01 | Phase 67 | Complete |
| RESUME-02 | Phase 67 | Complete |
| UX-01 | Phase 68 | Complete |
| UX-02 | Phase 68 | Complete |
