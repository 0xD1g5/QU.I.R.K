# Milestones

## v5.5 Distributed Hardening + Stabilization (Shipped: 2026-05-27)

**Phases completed:** 4 phases (113–116), 11 plans, 26 tasks. Audit: 13/13 requirements satisfied, 0 blockers, integration 12/12 + 3/3 E2E flows clean.

**Key accomplishments:**

- **Per-sensor authentication (Phase 113):** opaque per-sensor Bearer tokens (SHA-256 hash, `hmac.compare_digest`) replacing the v5.4 shared token; `revoke-sensor` CLI + `revoked_at` additive migration; two-router split keeps operator routes on `require_auth`. Security audit: threats_open 0 (10 mitigate + 3 accept).
- **Automatic merge trigger (Phase 114):** console auto-merges once every non-revoked enrolled sensor has checked in, via a FastAPI BackgroundTask scheduled after the push commit (structural failure isolation); config toggle + two trigger conditions (`all-sensors-in`, `cadence-window`); manual `quirk sensor merge` regression-free. Code review caught + fixed an inverted revoked-sensor filter (CR-01).
- **Live-UAT stabilization (Phase 115):** idempotent enroll (lab re-runnable without `down -v`), `cmvp_cache.json` shipped via importlib.resources, scheduler no longer passes unsupported `--target`/`--output` to run_scan (target preserved via a generated config), phantom `email/broker_scanner` rows eliminated at the read/export boundary.
- **Distributed lab testability (LAB-01):** weak-TLS `tls-weak-b` target on segment-b so the Phase 111 per-segment filter is exercisable end-to-end; lab.sh/oracle/README updated together (no-drift).
- **Windows packaging spike (Phase 116):** evidence-backed PyInstaller feasibility assessment + non-blocking `windows-packaging-spike` CI job (onefile build of run_scan.py) → **GO (conditional on live CI build)**, Scheduled Task host model, ~4–5 day v5.6 estimate. No artifact ships.

**Known deferred items at close:** 2 human-UAT (UAT-114-03 doc review, UAT-116-02 live windows-latest CI build) + cosmetic empty SUMMARY frontmatter — see STATE.md Deferred Items.

---

## v5.4 Distributed On-Prem Scanner Architecture (Shipped: 2026-05-26)

**Phases completed:** 7 phases (106–112), 20 plans
**Delivered:** QU.I.R.K. now scans a segmented enterprise network segment-by-segment — lightweight sensors scan locally and push results *outbound* to a single-tenant console that merges them into one authoritative CBOM + one quantum-readiness score, with no inbound access to any segment required. Milestone audit PASSED (0 blockers, 7/7 phases verified, 33/33 requirements delivered, cross-phase E2E chain wired). Single-tenant, additive-schema-only, OS-agnostic wire contract, reusing v5.3 security primitives throughout.

**Key accomplishments:**

- **Phase 106 (ANCHOR, no-code) — Architecture lock.** A single `docs/architecture-distributed.md` locks every expensive-to-change decision before code shipped: the sensor→console wire payload (`payload_id`/`pushed_at`/`received_at`/`schema_version`/`sensor_version`), `(sensor_id, host, port)` data-model keying with NULL=implicit-local, **Option A** unified scoring (union re-scored through the existing engine, never averaged), one-time-use enrollment tokens, the Windows floor-vs-ceiling split, and an explicit forbidden-additions list (no Celery/Redis/MQTT/Postgres/per-sensor-JWT/mTLS/tenant_id).
- **Phase 107 — Additive data model.** `CryptoEndpoint` gained nullable indexed `sensor_id` + `segment`; new `sensors` / `sensor_tokens` (SHA-256 hashes) / `sensor_pushes` (payload_id dedup) tables — all via the existing `_ADDITIVE_MIGRATIONS` path. A pre-v5.4 SQLite fixture migrates with no data loss and scores identically.
- **Phase 108 — Sensor CLI + Windows CI.** `quirk sensor enroll/push/export-results` (atomic `sensor.yaml`, `tenacity` retry, hardcoded `verify=True` + grep gate, bounded store-and-forward spool, byte-identical air-gap `.qpush`); `_NoRedirectHandler` extracted to `quirk/util/no_redirect.py` (STAB-02); POSIX-ism audit + `platformdirs`; a hard-gated `windows-latest` CI smoke job (no `continue-on-error`).
- **Phase 109 — Console ingestion.** `POST /api/sensor/push` on the existing FastAPI app with router-level `require_auth` (401 anti-bypass gating test), the full failure ladder (413/422+`console_utc`/409 dedup), an `IntegrationDelivery` audit row per attempt with `safe_str` scrubbing + AST gate, `extra='ignore'` version-skew tolerance, and `quirk console enroll` provisioning. One shared `_ingest_envelope` path for HTTPS push + air-gap import.
- **Phase 110 — Cross-sensor merge.** `quirk sensor merge` → one canonical CBOM + one score via Option-A union scoring; `coverage_warning` for overdue sensors (`2×cadence`); CBOM component identity threaded with `sensor_id` at four `bom_ref` sites so the same `host:port` in two segments yields two components; `merge_runs` persistence with per-endpoint `scanned_at` preserved (no rewrite).
- **Phase 111 — Console dashboard awareness.** Sensor registry page (green/stale/unknown badges), a shared per-segment filter, per-segment score gauges alongside the org-wide gauge, and a `coverage_warning` banner — backed by `GET /api/sensor/registry` + `GET /api/merge/latest` (per-segment recompute on read) + a NULL-safe `?segment=` filter.
- **Phase 112 — Distributed chaos-lab + stabilization.** A multi-segment `docker-compose.distributed.yml` (two isolated networks, `crypto.internal` hostname-alias reproducing the same-`host:port`-across-segments scenario after the Docker same-subnet constraint was discovered), `lab.sh distributed` arm + oracle + README (CLAUDE.md no-drift), operators-guide §8 (distributed workflow + Windows install + settings gap closed), and dependency/`datetime.utcnow()` hygiene.
- **Hardening via layered review gates.** Code review caught bugs that passed unit tests + verification across every phase: a zstd decompression bomb + path traversal + missing air-gap HMAC framing (108); audit-on-rolled-back-session + `UnknownSensorError`→404 (109); a *discarded CBOM artifact* and a cross-sensor dedup collision (110); an empty-`?segment=` 404 trap + a non-functional CBOM segment filter (111); and three lab showstoppers including an **SSRF allowlist that blocked the internal on-prem console** — a real product bug fixed via opt-in `--allow-internal-console` (112). The milestone-audit integration check then surfaced and fixed the `sensor_version` registry-display gap and reconciled the shared-token auth model (TD-1).

**Deferred (human-UAT, live infrastructure):** live enroll/spool round-trip (108), live merge + two-component CBOM inspection (110), dashboard visual fidelity vs UI-SPEC (111), the live multi-container `enroll→push→merge` E2E + MERGE-03 physical reproduction (112), GitHub branch-protection for the windows-smoke gate.

**Carry-forward to v5.5:** per-sensor token authentication + revocation (TD-1), automatic merge-trigger / poll-on-full-check-in (106 D-06), full Windows packaging ceiling — PyInstaller EXE + Scheduled Task (106 D-05).

Local tag `v5.4.0`.

## v5.3 Adoption & Integration Surface (Shipped: 2026-05-25)

**Phases completed:** 5 phases (101–105), 20 plans, 50 tasks
**Delivered:** QU.I.R.K. became load-bearing in others' workflows — scheduled-scan drift events now fan out to Slack/email/webhook, findings push to any SIEM as CEF, and per-finding tickets auto-open in both Jira and ServiceNow with idempotent dedup — all on one shared, SSRF-safe, secret-scrubbing delivery layer. Audit PASSED (21/21 requirements, 18/18 integration, 3/3 E2E flows).

**Key accomplishments:**

- **Phase 101 (ANCHOR) — Notification fan-out + the 7 integration-security primitives.** Scheduled-scan drift now delivers to Slack/email/webhook via a shared `DriftSummary` content model + per-channel fan-out, with the conservative trigger (new HIGH/CRITICAL OR score regression beyond −5, never on first scan). Shipped the primitives every later phase inherits: the `integration_deliveries` audit table, `safe_str` secret-scrubbing patterns, delivery-time SSRF (`validate_external_url`), the outbound-field whitelist, and the optional-extra lazy-import discipline. Delivery failures never touch the committed scan record.
- **Phase 102 — Dashboard auth UX + score-tax.** `quirk token` CLI (generate/rotate/show, atomic YAML round-trip); `require_auth` extended to accept `X-API-Key` (timing-safe) alongside bearer, with a CI route-coverage gate guarding every data route; a React login form with localStorage token + mid-session 401→logout. TRANS-04 repointed the CLI executive score to the shared `exec_content` — which surfaced and fixed a real cross-surface bug (CLI had shown 91/EXCELLENT vs the canonical 42/FAIR).
- **Phase 103 — SIEM export.** `quirk export --siem` pushes one CEF event per finding over stdlib syslog (UDP/TCP), vendor-neutral (Splunk/Elastic/QRadar), zero new pip deps; an explicit `to_cef_finding` whitelist keeps cert PEM / PKI topology out of the payload.
- **Phase 104 — Jira ticketing + the shared `TicketingChannel` abstraction.** Per-finding Jira issues carry QRAMM evidence; `SHA256(host:port::title)` fingerprint stored as a label, JQL-searched before create so re-scans add a rediscovery comment instead of duplicates. `jira` lives behind a lazy `[tickets]` extra (joined `[all]` + CI guard).
- **Phase 105 — ServiceNow ticketing as a pure second backend.** `quirk ticket create --backend servicenow` creates incidents via the stdlib `urllib` Table API (correlation_id dedup → work_notes rediscovery), proving TICKET-04: a second backend dropped in with **zero changes to `base.py` or `jira.py`** (git-verified).
- **Hardening via layered review gates.** Code review caught and fixed bugs that passed unit tests: an SSRF redirect-bypass (webhook urllib following 302→cloud-metadata), CEF header newline log-forgery + missing TCP framing, and JQL/URL-path injection via config-controlled `project_key`/`table`.

**Known deferred items at close:** 19 live-delivery human-UAT scenarios across 5 phases (Slack/email/webhook/syslog/Jira/ServiceNow against real servers — network sends are unit-tested with mocked transports), tracked in per-phase `*-HUMAN-UAT.md`. 1 LOW tech-debt item (extract the duplicated `_NoRedirectHandler` to a shared util). See STATE.md Deferred Items.

---

## v5.2 Consulting-Grade Reporting (Shipped: 2026-05-24)

**Phases completed:** 4 phases (97–100), 12 plans, 24 tasks
**Stats:** 109 commits, ~5,000 source LOC across 34 files (Python/Jinja2/TOML), 2026-05-23 → 2026-05-24

**Delivered:** QU.I.R.K.'s report is now a consulting-grade deliverable. From a single scan and ONE shared content model, a consultant gets a CISO-readable executive narrative with transparent scoring, a finding list that reads like an advisory document, a branded client-ready PDF, and an editable DOCX — the same story across every surface.

**Key accomplishments:**

- **v5.1 tech-debt cleanup (97):** corrected the `from_cli` env-var docstring and added the accepted str-copy proliferation comments (docstring/comment only, zero behavior change); REST-fuzzer combined failure-cascade counter so connection exceptions also count toward `_CONSECUTIVE_5XX_LIMIT` (timeout-only servers can't escape back-off); jwt_scanner query-param guard + fail-closed scheduler auth-reject; real-path credential-leakage sentinel test routed through the actual TLS scanner exception handler.
- **Executive narrative + score transparency (98):** shared `ExecContent` dataclass + `ALGO_IMPACT_MAP`/`EFFORT_IMPACT_MAP` static maps; a readiness narrative, top business risks, and effort/impact remediation roadmap wired across CLI + HTML; full subscore decomposition with the ÷1.5 rollup explanation; a `_check_congruence` guard that blocks a GOOD/EXCELLENT band from coexisting with CRITICAL findings (exits before any report is written); belt-and-suspenders cross-surface parity test (EXEC-04).
- **Per-finding context + code-signing expiry (99):** `ALGO_IMPACT_MAP` extended to a 3-tuple + new `REMEDIATION_CATALOG`, making `_build_finding` inject a plain-language quantum-risk "so what" and weakness-specific remediation on every finding (catalog-wins over generic NIST boilerplate); `_classify_codesign_severity` gained an independent expiry branch (expired→HIGH, ≤90d→MEDIUM); `evaluate_codesign_endpoints` turns CODE_SIGNING endpoints into first-class report findings for the first time, wired into run_scan.py; Quantum Risk surfaced across CLI/HTML/PDF with `| sanitize` discipline.
- **Professional & editable report delivery (100):** branded PDF cover page with a configurable base64-embedded logo (graceful omit) + print CSS (`@media print`, fixed table-layout, no mid-row splits, repeating headers); new `render_docx_report` auto-emitting an editable Word document (cover/exec/findings/roadmap/score, Heading 1/2, native tables, logo placeholder) on every run, derived from the same `exec_content` pipeline, gated behind a `[docx]` optional extra with graceful skip.

**Audit:** PASSED — 13/13 requirements satisfied (EXEC/TRANS/CTX/FMT), 4/4 phases verified, cross-phase integration intact (one shared content model → CLI + HTML + PDF + DOCX), E2E consultant flow complete, 0 blockers.

**Quality gates of note:** code review caught + fixed real robustness gaps the happy-path verifier missed — Phase 100's unbounded logo read + narrow except (could abort a scan) and unguarded `doc.save` (could abort CBOM generation), both now honoring their graceful-degradation contracts. Human UAT caught a PDF/DOCX findings-table header-wrap defect (FMT-02), fixed via HTML `white-space:nowrap`/widened columns and DOCX landscape orientation + pinned column widths.

**Known deferred items at close:** 1 acknowledged audit false-positive (Phase 98 HUMAN-UAT shows as "open" in audit-open because the parser keys on walkthrough checkboxes, not the `**Result:**` line — it is `status: passed`, 0 pending scenarios). 1 non-blocking tech-debt item carried to backlog: CLI executive markdown re-derives the score locally instead of sourcing `exec_content` (de-facto identical / deterministic; thread from `exec_content` + add a score-number parity test in a future milestone).

---

## v5.1 Authenticated Scanning + API Surface Depth (Shipped: 2026-05-23)

**Phases completed:** 4 phases (93–96), 16 plans

**Delivered:** An optional, ephemeral credential model that unlocks deeper crypto findings across the API surface — without QU.I.R.K. ever becoming a secret store. Credentials are in-memory-only and never persisted; the milestone's sharpest edge (active fuzzing) ships off-by-default behind a defensive gate.

**Key accomplishments:**

- **Credential infrastructure (93):** ephemeral `CredentialContext` (bytearray-backed, BaseException-safe zeroization) supporting Bearer/OAuth2 + API-key (header/query) + HTTP Basic via CLI flag/env/prompt; a committed 11-surface security-review gate; `safe_str` scrubbing extended to credential shapes with an AST CI gate; `QRK-SCHED-AUTH-001` hard-rejects authenticated scheduled scans. Code review caught + fixed 4 leakage/SSRF BLOCKERs (query-param log redaction, scan-error log scrub, JWKS-probe SSRF, DB error-message scrub).
- **OpenAPI & bearer-token analysis (94):** `analyze-token` JWT classifier (alg:none / missing-alg → CRITICAL); OpenAPI spec scanner hardened against `$ref` SSRF (pre-validate raw-ref reject — subclassing the resolver is insufficient), 10 MB pre-parse DoS gate, and scope-gated URL fetch; CBOM bearer classification `declared_algorithm (unverified)` wired end-to-end through the authenticated scan path (TOKEN-02 gap closed).
- **Code-signing certificate inventory (95):** LDAP `userCertificate` (CodeSigning EKU) + in-process TLS-EKU discovery; RSA<2048 / EC<256 / SHA-1 → HIGH `CODE-SIGN/weak-algorithm`; SHA-256-fingerprint + surrogate-key cross-source CBOM dedup (TLS-derived component wins). Code review caught + fixed a production-dead dedup (scanner wasn't populating the surrogate-key ORM columns).
- **Active REST fuzzing (96):** schemathesis-driven crypto-posture probes (TLS downgrade, cipher, HSTS, HTTP-only cred) + RS256→HS256 alg-confusion (stdlib-hmac forge); literal `CONFIRM` gate, hard non-TTY abort, six guardrails, and an unbypassable budget ceiling (default 50 / hard max 500) now bounding ALL traffic (two budget-bypass BLOCKERs — uncounted alg-confusion + per-iteration socket probes — found and fixed). New `fuzz-target` chaos profile.
- **Packaging + scoring:** `[api]` extras group (openapi-spec-validator + schemathesis) excluded from `[all]` with a CI guard; `SCORE_WEIGHTS` walked 283.0/37 → 293.0 → 299.0 → **303.0 / 41** via the existing `agility_signals` subscore (no 7th pillar).

**Audit:** PASSED — 21/21 requirements satisfied, 21/21 cross-phase integration seams wired, 5/5 E2E flows complete, 0 blockers (1 cosmetic OPENAPI-CBOM finding resolved inline).

**Known deferred items at close:** 6 human-UAT (environment/TTY-gated, non-blocking) — getpass TTY prompt + live PDF export (93); live ldaps code-signing scan (95); TTY CONFIRM gate + non-TTY abort + live alg-confusion vs fuzz-target container (96). Minor design-judgment tech-debt tracked for v5.2 (see v5.1-MILESTONE-AUDIT.md).

---

## v5.0 Stabilization + Tech Debt Sweep (Shipped: 2026-05-22)

**Phases completed:** 6 phases (87–92), 16 plans

**Delivered:** A deliberate stabilization cycle after four heavy capability milestones — dependency hygiene, scoring correctness/transparency, chaos-lab coverage, a demoable post-quantum scoring ceiling, dead-code cleanup, and the v5.0.0 release. No new capability surface.

**Key accomplishments:**

- **Dependency hygiene (87):** Node 20→24 CI bump ahead of GitHub's 2026-06-16 default-switch deadline; `defusedxml` replaced by a hardened lxml `make_safe_parser()` factory (XXE/billion-laughs safe) across `nmap_parser.py` + `saml_scanner.py`.
- **Scoring correctness + transparency (88):** single canonical scoring engine confirmed; six subscores surfaced against their /25 budget with the ÷1.5 rollup across CLI/HTML/PDF; orthogonal-subscore contract locked; five previously zero-algo CBOM profiles now emit real components or affirmative `quirk:coverage-note` markers (closes Phase 42 OBS-1).
- **Chaos-lab expansion (89):** five new weak-TLS lab profiles (postgres-tls, redis-tls, kafka-tls, grpc-tls; smtp covered by the existing email profile); identity evidence (DNSSEC=2, SAML=2) verified end-to-end into the identity subscore, surfacing + fixing a latent Logger-API crash.
- **Post-quantum scoring ceiling (90):** digest-pinned OQS-nginx `X25519MLKEM768` hybrid lab profile + a raw-`openssl s_client` PQC probe (outside the sslyze path) feeding a genuine quantum-safe CBOM component and an `agility` bonus — the milestone's one demoable capability anchor.
- **Code cleanup + bookkeeping (91):** Tier-A then vulture-confirmed Tier-B dead-code removal; a permanent `conftest.py` DB-isolation fix eliminating the recurring 7-module "Multiple QU.I.R.K. DBs" collection error; JWT `verify=False` inspection-mode advisory documented in code + operator docs.
- **v5.0.0 release (92):** version bumped to 5.0.0 (single-source pyproject), towncrier CHANGELOG + `docs/release-notes/5.0.0.md` built, UAT-SERIES + Obsidian synced, local `v5.0.0` tag created.

**Audit:** PASSED — 21/21 requirements satisfied, 4/4 cross-phase integration seams verified, 0 blockers.

**Known deferred items at close:** 4 human-UAT (non-blocking, environment-gated) — 88's three rendered-report visual checks (CLI/HTML/PDF Score Decomposition tables) + 89's kerberos `identity_weak_etype_count` (needs impacket + live KDC; macOS port-88 caveat). See STATE.md Deferred Items.

---

## v4.10.1 Scoring Correctness Hotfix (Shipped: 2026-05-22)

**Phases completed:** 1 phase, 3 plans, 6 tasks

**Delivered:** Fixed the marquee overall-readiness score that always displayed `100 / EXCELLENT` regardless of posture — a triple-layer bug spanning backend aggregation and frontend gauge math, fixed atomically as a single-phase vertical MVP slice.

**Key accomplishments:**

- Backend aggregator at `quirk/intelligence/scoring.py` rewritten: `_clamp(sum, 0, 100)` → `int(round(sum / 1.5))`. Canonical `25+25+23+3+25+19 = 120` now displays as **80 GOOD**, not **100 EXCELLENT**. Penalty model (`SCORE_WEIGHTS`, `_apply_weighted_impacts`) unchanged; boundary tests assert 100 only at all-25 ceiling, 0 only at all-zero.
- `ScoreGauge.tsx` gained a `maxValue?: number` prop (default 100) and a `_gaugeColor()` rewrite onto a normalized 0–1 fraction (red < 50 %, amber 50–79 %, green ≥ 80 %); six executive subscore radials + the Data at Rest tab gauge wired to `maxValue={25}`, with vitest coverage.
- Version bumped 4.10.0 → 4.10.1 (SoT in `pyproject.toml`); towncrier changelog fragment in operator language documenting the accepted 100 → ~80 visual jump; HUMAN-UAT operator walkthrough closed **PASS** (4/4 criteria, post-hard-refresh), verifier PASSED 5/5.

**Deferred to v5.0 Phase 01 (Stabilization):** EVIDENCE-TALLY-01 (evidence-summarizer tally gap), RENDER-CLI-01 + RENDER-PDF-01 (same-bug-class audit of CLI/HTML/PDF renderers).

---

## v4.8 Pre-Primetime Hardening + Operating Model (Shipped: 2026-05-14)

**Phases completed:** 13 phases, 53 plans, 122 tasks

**Key accomplishments:**

- One-liner:
- One-liner:
- SAML metadata fetcher routes all outbound URLs through validate_external_url before httpx.get, blocking RFC1918/loopback/link-local/file:///metadata IPs by default and emitting a HIGH advisory CryptoEndpoint per internal target when operator opts in via allow_internal_targets
- One-liner:
- broker_scanner.py changes:
- Bearer-token auth (hmac.compare_digest) and CSRF header check middleware for the FastAPI dashboard API, with configurable CORS allowlist and api_token fields in SecurityCfg
- Sliding-window rate limiter (60 POST/PUT/DELETE/PATCH/min/IP, Retry-After) and configurable CORSMiddleware registered in FastAPI app factory via get_cors_origins() — zero new pip dependencies
- One-liner:
- Full 16-test auth/CSRF/rate-limit/CORS/GET-auth/introspection/pdf-port-clamp suite; require_auth + require_csrf wired at router level on pdf, qramm, scan, and trends routers via TDD RED/GREEN cycle
- One-liner:
- fetchApi() TypeScript wrapper in src/dashboard/src/lib/api.ts enforcing X-Quirk-Request CSRF header and Bearer token on all 14 API call sites across 9 dashboard files, with 401/403/429 error handling at each site
- One-liner:
- Substitution table:
- 1. [Rule 1 - Bug] Refined _is_fstring_with_safe_str to handle benign Name + safe_str pattern
- One-liner:
- One-liner:
- 1. [Rule 1 - Bug] Regenerated expected_vault_cbom.json golden fixture
- One-liner:
- One-liner:
- One-liner:
- SQLite-backed scheduled_scans/scheduled_runs tables with argparse CRUD subcommands (add/list/enable/disable/remove) using croniter for cron validation and path-traversal-safe name allowlist
- 60-second sleep-loop dispatcher with SIGINT/SIGTERM signal handling, croniter next-run computation, subprocess.Popen crash-isolated dispatch, and startup recovery for orphaned runs
- FastAPI GET/POST/PATCH/DELETE /api/schedules router (first writable dashboard route, D-04) + React /schedules page with Switch toggles, delete Dialog, and optimistic UI — 11 pytest tests, production build verified
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- 1. [Rule 3 - Blocking] Added Phase 63 model/helper prereqs missing from worktree
- 1. [Rule 2 - Missing] Register Plan 01 test stubs in skip_registry.py
- 1. [Rule 3 - Blocking] Worktree branch was 14 commits behind main
- `src/dashboard/src/types/api.ts`
- One-liner:
- 1. [Rule 3 - Blocker] Worktree missing Phase 63/64/65 infrastructure
- One-liner:
- Import addition
- Argparse additions
- quirk/dashboard/api/schemas.py:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:

---

## v4.6 Enterprise Readiness (Shipped: 2026-05-05)

**Phases completed:** 6 phases (45–50), 24 plans
**Files changed:** 125 files, +20,560 / -405 lines
**Timeline:** 2026-05-03 → 2026-05-05 (3 days), 105 commits
**Audit:** passed_with_followup — 36/36 requirements, 6/6 integration flows

**Key accomplishments:**

- `[all]` meta-extra + `quirk.util.optional_extra` probe registry eliminate ImportError crashes on `pip install quirk`; coverage-gap advisory findings surface missing extras gracefully
- 5 new TLS finding types (expired CRITICAL, self-signed HIGH, untrusted-CA MEDIUM, RSA<2048 HIGH, EC<256 HIGH) + `tls-cert-defects` chaos lab profile for end-to-end verification
- Comma/`@file`/CIDR multi-target ingestion and optional nmap pre-scan port discovery with 10,000-probe TTY budget guard wired into both interactive mode and CLI
- `_build_finding` chokepoint enforces non-empty `description`/`remediation` on every finding; FIPS 203/204/205 algorithm names replace stale Kyber/Dilithium terminology project-wide; CI grep gate enforces compliance
- `quirk/compliance/` maps 24 finding categories to PCI-DSS 4.0.1/HIPAA/FIPS 140-3; staleness CI gate; `quirk compliance status` CLI; Compliance Summary in HTML/PDF reports
- `docs/architecture.md` (3 Mermaid diagrams, connector matrix) and `docs/operators-guide.md` (compliance runbook) authored and synced to Obsidian vault Reference/

**Deferred to v4.7:** COMPLY-10 (CBOM FIPS annotations), COMPLY-11 (SOC2/ISO27001 mapping), DOCS-05 (quirk doctor health check)

---

## v4.5 Reliability & Gap Closure (Shipped: 2026-05-03)

**Phases completed:** 7 phases, 40 plans, 69 tasks

**Key accomplishments:**

- One-liner:
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- Typed DarFinding Pydantic model + _derive_dar_findings() projection with 7-protocol dispatch, wired into ScanLatestResponse — all 8 Wave 0 tests GREEN
- lab.sh ALL_PROFILES replaced with _derive_all_profiles() bash parser reading docker-compose.yml at runtime, adding profiles subcommand, covering all 18 profiles including v4.3+v4.4 additions
- One-liner:
- Six category-tuned oracle sections (database, storage-s3, vault, storage legacy, email, broker) appended to expected_results_v4.md using verbatim scanner output strings, completing the 19-profile v4 oracle through v4.4
- One-liner:
- One-liner:
- Pytest config with slow-marker exclusion, AST-walk skip-registry gate, scan_error_category column with idempotent migration, and 9 xfail stubs that downstream plans turn green.
- Canonical [scan.timeouts] / [scan.retry] sub-tables landed on ScanCfg with warn-on-read deprecation aliases for the four legacy flat fields; config_from_dict loads sub-tables and falls back to legacy flat keys when no sub-table is present.
- BACK-45 cfg.scan mutation pattern eliminated; TLS/SSH/db/vault/jwt/container/source/email/broker scanners now read timeouts from the canonical cfg.scan.timeouts sub-table; run_scan.py:743 broker AttributeError fixed; ROBUST-02 TLS-timeout test green.
- `_wrapped_phase` helper added to run_scan.py with BaseException protection (re-raises KeyboardInterrupt/SystemExit, captures everything else as `scan_error_category='exception'`); broker_scanner and email_scanner emit canonical D-12 advisory + `scan_error_category='missing_extra'` row when the [motion] extra is absent; trends.py cur_err/prev_err exclude `missing_extra` so absent extras never register as regressions; 4 ROBUST-01/03 xfail stubs flipped to real assertions plus one new D-15 trends test — all green.
- Deletes 13 stale code-reason skips, converts defensive skips to pytest.fail, marks 9 slow tests, and turns the Plan 01 skip-registry meta-gate green — default `pytest` now runs in ~6s with zero stale skip markers.
- Consultant-facing timeout/retry documentation landed (configuration.md sub-table reference + D-10 upper-bound formula + ROBUST-04 audit doc), and the Phase 40 carry-over `lab.sh` profile-sweep gap is closed on both `down` and `reset` arms.
- Phase 41 closed across all four artifacts: UAT-SERIES.md gained UAT-41-01..04 entries (stderr advisory, upper-bound formula, lab.sh profile sweep, 60s budget); vault UAT-Series.md mirror synced; vault Phase-41 phase note created with status: complete sourcing all 6 prior plan SUMMARYs; ROADMAP.md Phase 41 checkbox flipped to [x]; STATE.md updated with Phase 41 close-out decisions and progress 4/7 phases (22/22 plans, 100%).
- 1. [Rule 3 — Blocker] Added `tests/__init__.py` to make `tests` a real package
- 3 shape-golden synthesizers
- 1. [Rule 3 — Blocking] Added `pythonpath = ["."]` to `[tool.pytest.ini_options]`
- Vault UAT mirror
- 1. [Rule 1 - Bug] Corrected trends API path in fixture middleware
- Sidebar Link primitives now receive visible keyboard focus rings via Tailwind focus-visible utilities; axe color-contrast audit confirmed zero new violations against the seeded fixture baseline.
- 1. [Rule 1 - Bug] Fixed Cytoscape HSL syntax error in roadmap.tsx
- DOM sentinel pattern closes UAT Gap 2: print.tsx sets `body[data-ready]` after data loads; pdf.py waits for that attribute before calling `page.pdf()`
- 1. [Rule 1 - Bug] Fixed pre-existing skip_registry drift
- One-liner:
- 1. [Rule 1 - Bug] Used correct scan_vault_targets signature
- One-liner:
- One-liner:
- 7 of 14 deferred UAT/VERIFICATION items closed in STATE.md via chaos lab automation and pytest tests, satisfying UAT-02 (Phase 29 cloud-only rationale) and UAT-04 (>=50% net reduction)

---

## v4.4 Data in Motion (Shipped: 2026-04-29)

**Phases completed:** 6 phases (32–37), 33 plans
**Files changed:** 162 files, +26,973 / -233 lines
**Timeline:** 2026-04-27 → 2026-04-29
**Tests:** 662 passed, 7 skipped, 1 deferred (pre-existing SAML scan-window regression — Phase 24 ISSUE-3, out of scope)
**Tag:** `v4.4.0` (commit `b72797a`)

**Key accomplishments:**

1. Email protocol scanning (Phase 32) — SMTP/SMTPS, IMAP/IMAPS, POP3/POP3S TLS posture across all 7 standard ports with STARTTLS-stripping detection on port 25; new `email` Docker chaos lab (Postfix + Dovecot, weak TLS).
2. Message broker TLS scanning (Phase 33) — Kafka (9092/9093/9094), RabbitMQ AMQPS (5671) + management API, Redis TLS (6380), Azure Service Bus, AWS SQS; plaintext-listener HIGH findings for all three local broker types; new `broker` Docker chaos lab (Kafka + RabbitMQ + Redis, weak TLS).
3. Data-in-motion intelligence (Phase 34) — six new `motion_*` evidence counters, three `motion_*_ratio` scoring weights with `strict`/`balanced`/`lenient` profile multipliers, and a 6th named `data_in_motion` subscore alongside `tls`/`ssh`/`api`/`identity`/`data_at_rest`; legacy v4.3 scans preserve full credit (D-12 backward compatibility).
4. Motion CBOM integration (Phase 35) — email and broker TLS endpoints generate Pass-1 algorithm components with quantum-safety classification; plaintext-only labels (`KAFKA-PLAIN`, `AMQP-PLAIN`, `REDIS-PLAIN`, `SMTP-STARTTLS`) excluded from Pass-2/Pass-3; golden snapshot fixtures lock the output shape.
5. Dashboard Motion tab (Phase 36) — new `/motion` React route with email per-port table + STARTTLS warnings, broker per-family grouped sections + plaintext flags, "Data in Motion" 6th `ScoreGauge`; `/api/scan/latest` carries `motion_findings`.
6. v4.4.0 release artifacts (Phase 37) — version bump locked across 6 surfaces by `tests/test_version.py`; `[motion]` meta-extra over `[email]+[broker]+[kafka]`; INFRA-03 18-test Nyquist coverage module; first top-level `CHANGELOG.md` + `docs/release-notes/4.4.0.md`.

**Requirements:** 50/50 mapped, 50/50 complete (100%) ✓

**Known deferred items at close:** 2 (see STATE.md `## Deferred Items`)

- **DEF-v4.4-01** — Phase 36 `wave_0_complete: false` flip — gated on the SAML scan-window regression below; documented in `37-VALIDATION.md` "Deferred Gaps" #1.
- **DEF-v4.4-02** — SAML/OIDC missing from `/api/scan/latest` `identity_findings` (real functional regression, ISSUE-3 from Phase 24, predates v4.4) — out of scope for v4.4.0; tracked for v4.5 follow-up.

**Carry-over from prior milestones:** 14 audit-open items (UAT gaps on phases 04–31, verification gaps on 25/28/31) — all pre-v4.4, non-blocking, retained in STATE.md `## Deferred Items`.

**Archived:** `.planning/milestones/v4.4-ROADMAP.md`, `.planning/milestones/v4.4-REQUIREMENTS.md`

---

## v4.3 Data at Rest (Shipped: 2026-04-26)

**Phases completed:** 7 phases (25–31), 24 plans, 504 tests collected

**Key accomplishments:**

1. Identity Findings Accuracy (Phase 25) — OIDC RS-family routing fix in `_derive_identity_findings()`, TLS-bleed guard in `_derive_findings()`, `ldap3>=2.9.1` in `[identity]` extras, chaos lab expected results oracle for all three v4.2 identity scanner profiles (DNSSEC/SAML/Kerberos) — closes NEW-ISSUE-1, ISSUE-2, NEW-ISSUE-3 from v4.2 audit
2. GCP Connector (Phase 26) — 47-entry `GCP_KMS_ALGORITHM_MAP` including PQC, Cloud SQL TLS enforcement, GCS CMEK detection; `gcs_scan_json` ORM column; `[cloud]` extras group; CBOM Pass 1/2/3 integration; `DefaultCredentialsError` explicit catch
3. Database Encryption Detection (Phase 27) — PostgreSQL 3-tier SSL probe (`pg_has_role`), MySQL `Ssl_cipher` scanner, RDS `StorageEncrypted`+`KmsKeyId`; `dat_scan_json` ORM column; `dar_` 5th subscore prefix; `[db]` extras; Docker database chaos lab (25432/23306)
4. Object Storage Audit (Phase 28) — S3 severity ladder via `ThreadPoolExecutor(max_workers=10)`, Azure Blob `keySource` ladder, GCS sentinel reuse (zero duplicate API calls); `dar_storage_*` evidence counters (SCORE_WEIGHTS 12.0/4.0); MinIO chaos lab (storage-s3 profile)
5. Kubernetes Secrets Inspection (Phase 29) — EKS/GKE/AKS managed encryption APIs, secret type enumeration, RBAC-403 graceful degradation, `encryption-config-inaccessible` invariant; `dar_k8s_*` evidence counters; gap closure CR-01/02/03
6. HashiCorp Vault Connector (Phase 30) — Transit keys with PQC positive findings (`ml-dsa`/`slh-dsa`), PKI CA cert detection, auth method risk tiering; `dar_vault_weak_count` HIGH-only counter; CBOM Pass 2+3 VAULT skip; dedicated chaos lab at port 28200 with seed.sh
7. Trend Analysis (Phase 31) — `compute_trend_report()` with score delta and net-new/resolved findings by severity; `GET /api/trends` FastAPI route; React `TrendsPage` with `useTrendsData` hook and `/trends` route; `scanned_at`-based session grouping — no new SQLite table

**Archived:** `.planning/milestones/v4.3-ROADMAP.md`, `.planning/milestones/v4.3-REQUIREMENTS.md`

**Known deferred items at close:** 16 (see STATE.md Deferred Items)

- B-1: OIDC ep.severity always None (cosmetic — downstream correct via scan.py re-derivation)
- W-2: dat_scan_json always NULL for DB rows (scoring correct via service_detail; JSON contract broken)
- W-1: Vault CBOM Pass 1 fragile — future VAULT skip list addition could break transit key registration
- 9 UAT deferred items (live Docker/cloud/browser environment required)
- Pre-existing carry-over UAT/verification gaps from prior milestones (acknowledged, non-blocking)

---

## v4.2 Identity Crypto (Shipped: 2026-04-24)

**Phases completed:** 8 phases (17–24), 14 plans, 352 tests passing

**Key accomplishments:**

1. Three new identity protocol scanners — DNSSEC (RFC 8624/9905 algorithm classification), SAML/OIDC (defusedxml XXE-safe metadata parsing), and Kerberos (impacket AS-REQ unauthenticated probe) — expanding QU.I.R.K.'s cryptographic surface to identity protocols
2. Three Docker Compose chaos lab profiles — BIND9 with 4 DNSSEC zones, SimpleSAMLphp with RSA-1024 signing cert, Samba DC with RC4-enabled realm — providing testbeds for all three identity scanners
3. Full identity CBOM pipeline — all three protocols produce CycloneDX components via dedicated elif branches; Pass 2/3 skip lists prevent hollow X.509 artifacts for non-certificate identity records
4. Identity surface in dashboard — React Identity tab with per-protocol summary cards (Kerberos/SAML/DNSSEC), FastAPI IdentityFinding model and identity_findings array in /api/scan/latest, Findings table protocol column filter
5. Intelligence layer extended — identity_weak_etype_count, saml_weak_signing_count, dnssec_weak_algo_count counters in evidence.py wired into compute_readiness_score()
6. Scan-session timestamp isolation (Phase 24) — ISSUE-3 HIGH gap eliminated: shared session_start from run_scan.py passed into all 3 identity scanners; scan-window query no longer silently excludes early-stamped endpoints

**Archived:** `.planning/milestones/v4.2-ROADMAP.md`, `.planning/milestones/v4.2-REQUIREMENTS.md`

**Known deferred items at close:** 12 (see STATE.md Deferred Items)

- ISSUE-2 (MEDIUM): ldap3 absent from pyproject.toml → Phase 25 in v4.3
- NEW-ISSUE-1 (MEDIUM): OIDC RS256 findings mislabeled as TLS-sourced → Phase 25 in v4.3
- NEW-ISSUE-3 (LOW): expected_results_v3.md missing identity chaos lab entries → Phase 25 in v4.3
- Pre-existing carry-over UAT/verification gaps from v3.9/v4.1 (acknowledged, non-blocking)

---

## v4.1 Foundation Polish (Shipped: 2026-04-08)

**Phases completed:** 9 phases, 17 plans, 29 tasks

**Key accomplishments:**

- 1. [Rule 1 - Bug] Cleaned stale version tag in code comment
- Removed enable_windows_adcs from ConnectorsCfg and interactive.py; added JWT/container/source scanner prompts with correct AWS/Azure labels
- One-liner:
- One-liner:
- PROFILE_MULTIPLIERS constant (strict=1.4x, balanced=1.0x, lenient=0.7x) added to compute_readiness_score() with prefix-based agility/identity weight scaling, plus 7 Wave 0 expectedFailure stubs for executive.py migration
- executive.py fully migrated from assessment/ imports to intelligence call sequence with ported _build_interpretation(), NOW/NEXT/LATER roadmap, and profile+calibration wired at both call sites
- One-liner:
- TDD RED scaffold establishing the Phase 12 contract: 3 failing tests prove version inconsistency (4.0.0 vs 4.1.0), stale config fallback, and [owner] placeholder; 3 passing tests guard already-clean areas (config template, no quirk scan refs, load_config integrity)
- Version bump to 4.1.0 across all 5 canonical locations and dev-install workflow replacing [owner] placeholder in Getting Started guide — all 6 Phase 12 contract tests GREEN, 205 total tests passing
- 10 RED expectedFailure tests in tests/test_interactive_mode.py defining the complete Plan 02 implementation contract for interactive_config() overhaul
- Rewrote interactive_config() implementing all 10 INTER requirements with auto-detected timezone, hardcoded consulting-grade TLS ports and SNI, targets-first prompt order, profile selection menu, unified 4-tier data classification menu, and AWS/Azure credential warnings; updated run_scan.py to unpack tuple return and remove deprecated prompt_for_context() call.
- 7-test RED scaffold covering SCORE-01 through SCORE-04: profile multipliers verified, validate.py dead param caught, migration advisor regression-guarded, dashboard profile gap exposed
- SCORE-02 and SCORE-04 made GREEN: dead validate_run parameter removed and dashboard now reads calibration.profile from intelligence JSON to produce profile-aware readiness scores
- 7-test Wave 0 scaffold asserting quirk/connectors/ absent (GREEN), cfg.scan SSH mutation guard structure (RED), scorecard.py absent (RED), and all 14 phase VALIDATION.md files nyquist_compliant (RED)
- Deleted orphaned scorecard.py and co-deleted its test, moved SSH cfg.scan mutations inside try block for correct finally-guard semantics, and updated all 14 completed phase VALIDATION.md files to nyquist_compliant: true (11 updated, 2 created) — turning all 7 test_hygiene.py tests GREEN
- 4-test RED TDD scaffold proves CLI-04 (pyproject.toml manifest version = 4.0.0) and SCORE-04 (interactive.py output dir defaults to "output" not "quirk-output") gaps exist before Plan 02 fixes
- pyproject.toml bumped to 4.1.0 and interactive.py output defaults corrected to "quirk-output", turning all 4 RED TDD tests GREEN and closing CLI-04 and SCORE-04 milestone gaps

---

## v3.9 Gap Closure (Shipped: 2026-04-04)

**Phases completed:** 13 phases, 40 plans, 75 tasks

**Key accomplishments:**

- Consolidated writer.py onto single intelligence-layer scoring path and fixed cert_pubkey_alg field extraction bug — both were silent data quality blockers
- Threaded SSH scanner with ssh-audit subprocess integration storing full KEX/hostkey/MAC JSON in new ssh_audit_json column, replacing sequential banner-only scan
- One-liner:
- Full qcscan -> quirk rename with pyproject.toml: zero remaining qcscan/QuRisk references in .py files, all 56 tests pass, `python3 -c "import quirk; print(quirk.__version__)"` prints 3.9.0
- classify_algorithm() lookup table mapping 50+ algorithm strings from TLS/SSH/cert scanners to CycloneDX CryptoPrimitive enum values and NIST PQC quantum security levels via cyclonedx-python-lib 11.7.0
- CycloneDX Bom builder with TLS cipher suite decomposition, SSH kex/key/enc/mac parsing, certificate components, and bom_ref deduplication via in-memory registry
- CycloneDX 1.6 JSON+XML file output with write_cbom_files() wired into write_reports() as step 5, producing cbom-{stamp}.cdx.{json,xml} alongside every scan run
- CryptoEndpoint extended with four JSON blob columns (jwt/container/source/cloud), ConnectorsCfg extended with Phase 3 flags and cloud config, all eight Phase 3 dependencies installed, and Wave 0 test scaffolds defining contracts for SCAN-03 through SCAN-07
- Three new CryptoEndpoint-producing scanners (JWT/JWKS via httpx, container images via syft, source code via semgrep) expanding QU.I.R.K. from 2 to 5 scan surfaces with graceful degradation when tools are absent
- AWS boto3 connector (ACM/KMS/CloudFront/ELBv2) and Azure SDK connector (KeyVault/AppGateway) with paginator-based enumeration and graceful SDK degradation
- quirk/cbom/classifier.py
- 4 FastAPI JWT microservices (RS256/2048-bit, HS256-weak/128-bit, RSA-1024, alg:none) deployed as docker-compose jwt profile on ports 20001-20004 with JWKS + /token endpoints matching SCAN-03 scanner field expectations
- Docker Registry v2 profile on port 20005 with 3 seeded test images containing openssl, cryptography==2.9.2, and pyOpenSSL==19.1.0 that Syft's CRYPTO_LIB_ALLOWLIST will detect
- Gitea instance seeded with 3 repos (Python/Go/Java) covering all 4 D-08 crypto anti-pattern categories for semgrep p/cryptography validation
- LocalStack KMS + HashiCorp Vault transit engine + postgres-pgcrypto storage profile with 5 Docker Compose services seeded with real crypto key material for scanner validation
- ubuntu:18.04 OpenSSH ssh-weak service (port 20022) with group1-sha1/ssh-dss/hmac-md5 weak config, osixia/openldap ldaps service (port 636) with TLS via modern.crt, and expected_results_v3.md updated with all 6 Phase 4 scanner oracle sections
- One-liner:
- GET /api/scan/latest endpoint wired to SQLite intelligence functions, with Executive (5 arc gauges + severity chart), Findings (TanStack Table + Sheet), and Certificate Inventory (expiry color-coded + quantum-safety badges) pages
- Cytoscape.js CBOM bipartite graph and migration DAG pages with shadcn/ui table, full route wiring in App.tsx
- POST /api/export/pdf Playwright headless PDF generation from /print React page with white-bg print layout and graceful 503 degradation when chromium absent
- README fully replaced and docs/getting-started.md + docs/installation.md written: zero-to-first-scan consultant path in under 10 minutes covering macOS, Linux, and Windows WSL
- Complete config.yaml and CLI flag reference in docs/configuration.md — all 6 top-level blocks, scan profiles, score profiles, and copy-pasteable minimal and full config templates
- Four copy-paste-ready connector guides covering AWS IAM policy (7 actions), Azure RBAC roles, Syft-based container scanning, and semgrep p/cryptography source scanning — all permissions derived from the actual connector source code.
- Consultant-facing report interpretation guide with exact scoring thresholds, all four subscore driver tables, severity tier definitions, and Client Conversation sideboxes for live client meetings
- Three-section CBOM guide for compliance officers, consultants, and auditors — covering what a CBOM is, QU.I.R.K.'s five-step CycloneDX pipeline, and copy-pasteable audit language for NIST SP 800-208, CNSA 2.0, and ISO 27002:2022
- Authoritative chaos lab operator guide covering all 10 profiles (core through ldaps) with per-profile port matrices, copy-pasteable start commands, and connector config snippets
- One-liner:
- Rich Panel startup banner, --version/--quiet flags, and rich scan summary table replacing tqdm/print output in QU.I.R.K. CLI
- quirk/reports/html_renderer.py
- SVG redesigned:
- Version bumped to 4.0.0 across __init__.py, pyproject.toml, and writer.py; quirk init implemented using importlib.resources with bundled config_template.yaml; getting-started.md updated to git+https install path
- 1. [Rule 1 - Bug] Cleaned stale version tag in code comment
- Removed enable_windows_adcs from ConnectorsCfg and interactive.py; added JWT/container/source scanner prompts with correct AWS/Azure labels
- One-liner:
- One-liner:
- PROFILE_MULTIPLIERS constant (strict=1.4x, balanced=1.0x, lenient=0.7x) added to compute_readiness_score() with prefix-based agility/identity weight scaling, plus 7 Wave 0 expectedFailure stubs for executive.py migration
- executive.py fully migrated from assessment/ imports to intelligence call sequence with ported _build_interpretation(), NOW/NEXT/LATER roadmap, and profile+calibration wired at both call sites
- One-liner:
- Added `dashboard/static/
- Two-line fix closes GAP-INT-01 and GAP-INT-02: deps.py default db_path aligned to './quirk.db' (config_template.yaml) and server.py now sets QUIRK_SERVE_PORT before uvicorn starts so PDF export inherits the correct port
- SSH algorithm parsing added to _derive_cbom() in scan.py: kex/key/enc/mac sections from ssh_audit_json now produce classified CbomComponent entries in the dashboard CBOM viewer, closing GAP-INT-03

---
