# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v3.9 — Gap Closure

**Shipped:** 2026-04-04
**Phases:** 11 | **Plans:** 40+ | **Commits:** 263

### What Was Built

- **Full cryptographic scanner surface:** sslyze TLS deep scan, ssh-audit KEX/hostkey/MAC enumeration, API/JWT scanner with JWKS fetch, Syft container scanner, semgrep source code scanner, AWS + Azure cloud connectors — all wired to a single SQLite persistence layer
- **CycloneDX CBOM pipeline:** classifier (50+ NIST PQC entries), builder, writer producing JSON+XML per scan run; dashboard CBOM viewer renders bipartite component graph with quantum-safety labels
- **FastAPI + React dashboard:** executive summary with 4-subscore gauges, findings table, certificate inventory, CBOM viewer, PDF export via Playwright — all served from `quirk serve` with correct db_path and port propagation
- **6-profile chaos lab expansion:** jwt, registry, source, storage, ssh-weak, ldaps — full Docker Compose lab for validating every new scanner surface against realistic targets
- **7-guide documentation suite:** getting started, installation, configuration, connector setup, report interpretation, CBOM compliance guide, chaos lab operator guide
- **v4.0.0 packaging and polish:** pip-installable wheel with bundled React static assets, `quirk init` wizard, HTML/PDF report templates, QU.I.R.K. visual identity, `quirk banner` rich CLI UX
- **E2E dashboard wiring fixes (Phase 11):** closed GAP-INT-01 (db_path default mismatch), GAP-INT-02 (PDF port env var not propagated), GAP-INT-03 (SSH algorithms missing from CBOM viewer)

### What Worked

- **Phase-gated verification:** Every phase produced a VERIFICATION.md with observable truths and behavioral spot-checks before marking complete. This caught the packaging gap (PACKAGE-01) and quantum safety label type confusion (MISMATCH-01) before they shipped.
- **Gap closure phases (10 + 11):** Explicitly scheduling gap-closure phases at the end of the milestone — rather than trying to fix defects inline — kept primary phases clean and gave defects first-class planning treatment.
- **Integration audit before milestone close:** The `audit-milestone` workflow running the `gsd-integration-checker` agent as a final gate found INT-01 and INT-02 after all phase verifications passed. Without this, the dashboard scoring profile gap and orphaned `scorecard.py` would have shipped silently.
- **3-source requirements cross-reference:** Mapping REQ-IDs across VERIFICATION.md + REQUIREMENTS.md traceability + SUMMARY.md frontmatter identified 7 requirements with incomplete SUMMARY coverage — surfaced as Nyquist debt rather than silent gaps.
- **Tech debt backlog (BACK-xx):** Tracking found-but-deferred issues (BACK-60, BACK-61, BACK-62) as first-class backlog entries with phase directory stubs means they won't be forgotten between milestones.

### What Was Inefficient

- **Nyquist VALIDATION.md hygiene:** 9 of 11 phases have stale VALIDATION.md files (`nyquist_compliant: false`); 2 phases (02, 08) are missing VALIDATION.md entirely. These were never updated post-execution. Updating them should be a required exit step for every plan execution, not a backlog item.
- **Phase 1 not structured as sub-plans:** Phase 1 (Foundation Fixes) appears to have no discoverable `01-xx-PLAN.md` files (the plan glob returned only phases 02–11). Large phases benefit from the same sub-plan breakdown structure used in later phases.
- **SUMMARY.md frontmatter inconsistency:** 7 SUMMARY.md files were missing `requirements-completed` frontmatter fields (SCAN-01, LAB-04, DOC-05, DOC-07, BRAND-01, BRAND-02, BRAND-03). The gsd-tools `summary-extract` command returned empty output for all files because of this. Frontmatter field completeness should be validated at plan-complete time.
- **Documentation + Obsidian sync deferred:** Guide syncs to the Obsidian vault were skipped in most phase executions. This creates drift between the planning system and the knowledge base. Per memory: all phase plans must include explicit docs update and Obsidian sync tasks.

### Patterns Established

- **GAP closure phase naming:** `NN-v{version}-gap-closure` and `NN-{feature}-wiring-fixes` as dedicated end-of-milestone phases for closing audit findings
- **3-source requirements cross-reference table** in milestone audit as standard coverage gate
- **BACK-xx backlog entries with phase directory stubs** for tech debt that can't be closed in the current milestone
- **`<details>` collapse in ROADMAP.md** for archived milestone phase lists — keeps the roadmap scannable as phases accumulate
- **Milestone archival to `.planning/milestones/`** as authoritative historical record, with ROADMAP.md/REQUIREMENTS.md kept clean for next milestone

### Key Lessons

1. **Verification without integration testing is incomplete.** All 11 phases passed individual VERIFICATION.md checks, but the integration audit still found 2 wiring gaps (INT-01, INT-02). Unit-level verification and cross-phase integration are separate quality gates — both are necessary.
2. **Packaging is easy to forget and hard to notice.** PACKAGE-01 (React static assets missing from pip wheel) would have been invisible until someone ran `pip install` in a fresh virtualenv. Packaging verification must be part of phase exit criteria whenever pyproject.toml or build artifacts change.
3. **Documentation debt compounds.** 9 stale VALIDATION.md files + 7 incomplete SUMMARY.md files + deferred Obsidian syncs = a documentation state that drifts far from the code. Treating docs as a first-class task in every plan execution (not a post-milestone cleanup) prevents this accumulation.
4. **Type confusion bugs survive code review.** MISMATCH-01 (passing a string directly to `quantum_safety_label()` instead of the NIST level it expects) was a semantic type mismatch that Python's dynamic typing couldn't catch. The regression tests in `test_gap_closure.py` are the right fix — ensure classifiers have unit tests that assert output types, not just no-exception execution.

### Cost Observations

- Model mix: Sonnet 4.6 primary throughout milestone
- Sessions: Multiple multi-hour sessions; 263 commits across the milestone
- Notable: Gap closure phases (10, 11) required approximately the same planning and execution effort as primary phases despite targeting only 3 defects — defects in integration wiring are not cheaper to fix than features

---

## Milestone: v4.1 — Foundation Polish

**Shipped:** 2026-04-08
**Phases:** 5 (12–16) | **Plans:** 10 | **Files changed:** 80 (+10,261 / -638)

### What Was Built

- **CLI correctness sweep:** Fixed generated config field names, replaced `[owner]` placeholder with dev-install workflow, bumped all 5 version string locations to 4.1.0 including pyproject.toml (caught by gap-closure phase)
- **Interactive mode rewrite:** Fully replaced interactive_config() — auto-detected timezone, hardcoded 17-port consulting TLS defaults, profile selection menu (quick/standard/deep), JWT/container/source scanner prompts, targets-first prompt order, unified data classification menu
- **Scoring end-to-end correctness:** Calibration profile (strict/balanced/lenient) now correctly applied in compute_readiness_score(); dashboard reads calibration.profile from intelligence JSON; validate.py no longer flags non-existent artifacts; migration_advisor pattern strings now match risk_engine finding titles
- **Dead code elimination:** Legacy connector stubs (aws_stub.py, azure_stub.py, windows_adcs_stub.py) deleted; orphaned scorecard.py + test removed; SSH cfg.scan mutations moved inside try block; 14 VALIDATION.md files updated to nyquist_compliant: true
- **Flow C closure (Phase 16):** Two one-line fixes that audit found — pyproject.toml version and interactive.py output dir default — closed the E2E gap from interactive wizard to dashboard profile display

### What Worked

- **Audit-then-gap-closure pattern established in v3.9 paid off immediately.** The v4.1 audit found CLI-04 and SCORE-04 as two precise, actionable gaps (not ambiguous issues). Phase 16 closed both in a single plan with 4 targeted edits. The pattern of audit → gap-closure phase → milestone close is now validated across two milestones.
- **TDD RED-first discipline caught real bugs.** Every plan pair (N-01 scaffold, N-02 implementation) proved the bug existed before fixing it. Phase 16 specifically used importlib.metadata.version() inspection to distinguish the installed egg-info version from the runtime __version__ — a gap that code inspection alone would have missed.
- **Phase 15 (VALIDATION.md hygiene)** closing 14 stale files in a single plan means the next milestone starts with an accurate Nyquist baseline — the v3.9 retrospective specifically called this out as debt. Fixed and won't compound.

### What Was Inefficient

- **Two SUMMARY.md files missing `one_liner` frontmatter:** The `summary-extract` CLI returned empty for all 10 SUMMARY.md files — the field isn't being written by the execute-phase workflow. This means MILESTONES.md auto-generation falls back to verbose description strings rather than crisp one-liners. The frontmatter contract needs enforcement at plan-complete time.
- **Interactive mode tech debt (DEFAULT_TIMEZONE, _prompt_ports) deferred twice:** Deferred in Phase 13 to Phase 15; Phase 15 didn't address. Zero runtime impact but the dead code accumulates. These should have been deleted in Phase 15 alongside the scorecard cleanup — they're adjacent hygiene items.
- **Phase 16 could have been avoided:** CLI-04 (pyproject.toml version) and SCORE-04 (output dir default) were both identified by the milestone audit, meaning they slipped through all 4 phases of verification. Had test_packaging.py included `importlib.metadata.version()` verification from Phase 12, CLI-04 would have been caught immediately.

### Patterns Established

- **Two-edit gap-closure pattern:** A gap-closure phase targeting only 2 files with 2 targeted edits is valid and fast — avoid over-engineering the fix just because it has a phase to itself
- **importlib.metadata.version() vs __version__:** When testing package version consistency, inspect the installed package manifest (importlib.metadata) not just the module attribute — they can diverge with editable installs if pyproject.toml isn't updated
- **output dir alignment as integration contract:** Dashboard QUIRK_OUTPUT_DIR default and interactive_config() output dir default are a cross-component contract — both must agree for E2E profile passthrough to work; this should be a formal integration test

### Key Lessons

1. **GAP-closure phases scale down cleanly.** v4.1's gap-closure was 2 files / 4 lines vs v3.9's 3-defect Phase 11. The same planning structure (audit → gap-closure → milestone close) works at both scales — don't skip it for "small" gaps.
2. **Version consistency needs manifest-level verification.** Runtime __version__ and installed package version (importlib.metadata) are independent until pip install -e . is run. Test both, not just the module attribute.
3. **Deferred dead code has a shelf life.** DEFAULT_TIMEZONE and _prompt_ports() were deferred twice before this retrospective. They should have been deleted in Phase 15 — dead code that survives two milestones becomes permanent fixture.
4. **SUMMARY.md `one_liner` field needs enforced.** Auto-extraction from SUMMARY.md frontmatter is only useful if the field is actually populated. This is a workflow enforcement gap, not a content gap.

### Cost Observations

- Model mix: Sonnet 4.6 primary throughout milestone
- Sessions: Intensive 2-day execution (2026-04-06 → 2026-04-08)
- Notable: Correctness-only milestone with no new features — lowest code churn of any milestone; highest precision (22/22 requirements satisfied, 2/2 audit gaps closed)

---

## Milestone: v4.2 — Identity Crypto

**Shipped:** 2026-04-24
**Phases:** 8 (17–24; Phase 25 deferred) | **Plans:** 14 | **Tests at ship:** 352

### What Was Built

- **Three identity protocol scanners:** DNSSEC (RFC 8624/9905 3-tier classification via dnspython authoritative query), SAML/OIDC (defusedxml XXE-safe lxml parsing, RSA-1024/SHA-1 detection, OIDC discovery), Kerberos (impacket AS-REQ unauthenticated probe, 7-etype severity map) — the first major scanner expansion since Phase 3
- **Three Docker chaos lab profiles:** BIND9 with 4 pre-signed DNSSEC zones, SimpleSAMLphp with RSA-1024 signing cert, Samba DC with RC4-enabled realm — complete testbeds for all three identity scanners
- **Full identity CBOM pipeline:** all three protocols produce CycloneDX components; Pass 2/3 skip lists prevent hollow X.509 artifacts; DNSSEC required a separate gap-closure phase (23) to add it to Pass 2 cert skip list
- **Identity surface in dashboard:** React Identity tab with per-protocol summary cards, FastAPI IdentityFinding Pydantic model, identity_findings[] in /api/scan/latest, Findings table protocol filter — identity findings fully wired end-to-end
- **Three-phase gap closure sweep:** Phase 22 (NameError + CBOM skip lists), Phase 23 (DNSSEC Pass 2 certificate skip), Phase 24 (scan-window timing ISSUE-3 HIGH) — milestone audit found 4 gaps; all severity HIGH and above closed before ship

### What Worked

- **Audit-at-v3 pattern proved its value.** The v3 milestone audit after Phase 23 completion found ISSUE-3 (HIGH scan-window timing defect) that would have been invisible in production — Kerberos timeouts silently excluding DNSSEC/SAML endpoints from the API response. Without the audit, the Identity tab would have appeared empty under realistic network conditions.
- **TDD RED-first caught domain-specific edge cases.** The SAML_NS constant requirement (lxml XPath returns empty without explicit namespace dict) and the kerberos _derive_realm IPv4 detection gap were both caught by RED tests before implementation, not after. The discipline of writing failing assertions first surfaces silent bugs that code review misses.
- **Impacket isolation decision paid off.** Keeping impacket in [identity] extras only (not core deps) prevented a pyOpenSSL transitive conflict from blocking all users. The KERB-03 graceful-degradation path means the scanner always works; ldap3 absence is a capability gap, not a crash.
- **Gap-closure phases scale to single-file fixes.** Phase 23 was a one-line addition to a skip tuple (`"DNSSEC"` to builder.py Pass 2). Phase 24 was a two-line change (session_start wired from run_scan.py). These tiny fixes still got their own planned phases with TDD scaffolds — that rigor confirmed the fix was correct and protected against regressions.

### What Was Inefficient

- **DNSSEC-04 required three gap-closure phases to fully close.** The CBOM skip list was initially missed in Phase 22 (which handled SAML/Kerberos but not DNSSEC), caught in Phase 23, then the scan-window timing defect was found in Phase 24. A more complete Phase 22 spec would have covered all three protocols equally — the gap existed because DNSSEC was structurally different (no X.509 cert components at all) and wasn't treated the same way in the builder audit.
- **Phase 25 deferred at ship.** ISSUE-2 (ldap3) and NEW-ISSUE-1 (OIDC RS256 identity routing) were identified by the v3 audit but not closed before milestone. Both are small fixes (one dependency line + one if-branch in scan.py). They should have been Phase 25 candidates from the audit's first pass, not discovered at v3.
- **expected_results_v3.md missing identity chaos lab entries.** CLAUDE.md explicitly requires updating expected_results.md when detection logic changes. This was flagged as NEW-ISSUE-3 in the audit but not fixed during the milestone. One of the clearest CLAUDE.md rule violations in this milestone's execution.

### Patterns Established

- **Per-protocol CBOM elif branches + skip lists:** Each new protocol scanner requires both an addition to builder.py (elif branch for algorithm registration) AND an entry in the Pass 2 cert skip tuple AND the Pass 3 protocol-component skip tuple. Checklist item for all future identity-class scanners.
- **Shared session_start as scan session contract:** All scanners that run sequentially from run_scan.py must accept a `session_start` parameter and use it rather than calling `datetime.now()` internally. This is now an established interface contract — future scanners should follow it from Phase 1, not as a gap closure.
- **Direct authoritative NS query for DNSSEC:** System resolver always strips the DO bit. Any DNSSEC scanner must use `dns.resolver.resolve()` against the authoritative NS directly, not the system stub resolver. Documented once here so the next DNSSEC-adjacent feature doesn't rediscover it.

### Key Lessons

1. **The scan-window query is a systemic integration test.** GET /api/scan/latest's 1-second window around MAX(scanned_at) is fragile by design — any sequential scanner that can timeout will skew the anchor. The shared session_start pattern (Phase 24) fixes this, but the API query itself should be reviewed for future scanner additions.
2. **CBOM skip list coverage must be audited symmetrically.** Phase 22 added SAML + KERBEROS to skip lists but missed DNSSEC (different shape — no X.509 components, needs a different skip path). Future builder.py changes should audit all 3 identity protocols plus TLS/SSH in the same pass.
3. **expected_results.md updates are not optional.** CLAUDE.md makes this an explicit requirement when detection logic changes. All three identity chaos lab profiles (bind9-dnssec, simplesamlphp, samba-dc) are missing entries. This compounds: the longer it's deferred, the harder it is to write accurate expected results from memory.
4. **Graceful degradation must be installable too.** KERB-03's ldap3 path gracefully degrades — but graceful degradation is only useful if the happy path is achievable. A dependency that can never be installed (ldap3 absent from pyproject.toml) is not a graceful degradation; it's a permanently broken feature. The fix is trivial (one line); the lesson is to verify every import-guarded dependency exists in some installable group.

### Cost Observations

- Model mix: Sonnet 4.6 primary throughout milestone
- Sessions: Extended execution across 2026-04-08 → 2026-04-24 (16 days including research and gap-closure cycles)
- Notable: Three gap-closure phases after primary feature work — audit-driven rigor caught ISSUE-3 HIGH that would have caused silent data loss in the Identity tab under realistic conditions; cost justified by correctness guarantee

---

## Milestone: v4.3 — Data at Rest

**Shipped:** 2026-04-26
**Phases:** 7 (25–31) | **Plans:** 24 | **Tests at ship:** 504 collected

### What Was Built

- **Identity Findings Accuracy carry-over (Phase 25):** OIDC RS-family routing fixed in `_derive_identity_findings()`, TLS-bleed guard in `_derive_findings()`, `ldap3>=2.9.1` added to `[identity]` extras, and full chaos lab expected results oracle written for all three v4.2 identity scanner profiles — the first milestone where a prior-milestone audit finding arrived pre-packaged as Phase 1 of the new milestone
- **GCP Connector (Phase 26):** 47-entry KMS algorithm map including PQC key types, Cloud SQL TLS enforcement detection, GCS CMEK detection — GCS enumeration data stored and forwarded to Phase 28, eliminating duplicate API calls
- **Database Encryption Detection (Phase 27):** PostgreSQL 3-tier SSL probe using `pg_has_role()` privilege check, MySQL `Ssl_cipher` session scanner, RDS `StorageEncrypted`+`KmsKeyId` via existing boto3 session; `dat_scan_json` ORM column established as shared dependency; `dar_` 5th subscore prefix introduced; Docker chaos lab for database targets
- **Object Storage Audit (Phase 28):** S3 per-bucket severity ladder via `ThreadPoolExecutor(max_workers=10)`, Azure Blob `keySource` classification, GCS CMEK sentinel reuse confirming zero duplicate storage API calls; MinIO chaos lab; dar_storage evidence counters with SCORE_WEIGHTS 12.0/4.0
- **Kubernetes Secrets Inspection (Phase 29):** EKS/GKE/AKS managed cluster encryption APIs, secret type enumeration without reading values, RBAC-403 degradation, `encryption-config-inaccessible` invariant; gap closure plan 29-04 closed three VERIFICATION gaps after primary implementation
- **HashiCorp Vault Connector (Phase 30):** Transit keys with PQC positive findings (`ml-dsa`/`slh-dsa` → quantum-safe), PKI CA cert algorithm detection, auth method risk tiering; dedicated chaos lab at port 28200; conftest.py SHA-1 shim required for cryptography 46.x compatibility
- **Trend Analysis (Phase 31):** `compute_trend_report()` using `scanned_at`-based session grouping (no new SQLite table), score delta, net-new/resolved findings by severity, `GET /api/trends` FastAPI route, React `TrendsPage` with `useTrendsData` hook — first cross-session intelligence feature

### What Worked

- **CRITICAL PATH designation for Phase 27 paid off.** Marking Phase 27 as the explicit critical path dependency (`_ensure_v43_columns()` and `dat_scan_json` shared by Phases 28, 29, 30) allowed Phases 28/29/30 to be planned and executed in logical parallel with full confidence that the schema was stable. No rework required from schema drift.
- **GCS sentinel reuse design (STOR-03).** The decision to have Phase 26 store GCS bucket data in `gcs_scan_json` and Phase 28 read from it — rather than each making independent `storage.buckets.list` API calls — required upfront API boundary agreement. That contract worked as designed: zero duplicate GCS calls in a single scan run.
- **dar_ prefix as 5th parallel subscore.** Introducing `dar_` as a parallel prefix to `identity_` (rather than extending an existing subscore) kept the scoring infrastructure separable. This architectural choice, made at roadmap-creation time, meant all 6 dar_ scanner contributions (db, storage, k8s, vault) could be added independently without touching each other.
- **Phase 25 carry-over pattern.** Treating the v4.2 audit's NEW-ISSUE-1 and ISSUE-2 as the literal Phase 25 of v4.3 — rather than shoehorning them into v4.2's close — produced a cleaner milestone with explicit traceability. The carry-over was pre-planned at roadmap creation, not discovered mid-execution.
- **Gap closure plan 29-04.** After primary K8s implementation, VERIFICATION.md surfaced CR-01/02/03 (RBAC counter, AKS per-cluster inaccessible, service_detail alignment). Plan 29-04 closed all three in one targeted plan — the audit-then-gap-closure pattern validating at 3-gap scale again.

### What Was Inefficient

- **W-2: `dat_scan_json` always NULL.** The evidence counters were wired via `service_detail` parsing, which works for scoring, but the `dat_scan_json` column itself is never populated by any DB scanner. This was a structural gap — the column was introduced in Phase 27-01 as part of the ORM schema but no Phase 27 plan wrote to it. It should have been a Phase 27 exit criterion: "`dat_scan_json` is non-null after a DB scan."
- **W-1: Vault CBOM Pass 1 fragile.** The decision to leave Vault endpoints registering algorithms through the default `else` clause (D-14) is architecturally fragile — a future `VAULT` addition to the Pass 1 skip list would silently break transit key registration. This was a known trade-off (documented in SUMMARY.md) but should have been resolved with an explicit `elif ep.protocol == 'VAULT'` guard in the same plan that introduced the skip entries.
- **`__init__.py` version skew.** `quirk/__init__.py` still read `4.2.0` at milestone close despite `pyproject.toml` being `4.3.0`. This was caught during milestone archive and fixed, but it repeated the v4.1 lesson (importlib.metadata vs module attribute). The version bump should be a required milestone execution step, not a milestone-close finding.
- **TREND-04 visual render deferred from Plan 03.** The React `/trends` page code was committed in Plan 31-03 but the human verification checkpoint was accepted without running the dashboard in a browser. Visual rendering confirmation should be a blocking checkpoint, not an acknowledged deferral — a blank /trends page in production is a user-visible regression even if the API is wired.

### Patterns Established

- **CRITICAL PATH annotation in roadmap:** When a phase establishes shared schema or infrastructure that multiple downstream phases depend on, mark it explicitly in the roadmap as `(CRITICAL PATH)`. This makes dependency sequencing unambiguous for any executor.
- **GCS sentinel reuse contract:** Scanner A stores API enumeration results in a JSON column; Scanner B reads from that column rather than re-fetching. This pattern eliminates duplicate cloud API calls for any two scanners that share a common enumeration step. Document the producer-consumer contract in both SUMMARY.md files.
- **dar_ prefix as independent subscore slot:** New scanner surface areas that score independently of each other should introduce their own prefix in `evidence.py`/`scoring.py`, not share an existing prefix. Keeps surface scoring separable for future per-surface dashboard breakdowns.
- **conftest.py shim for upstream library breaks:** When a transitive dependency changes behavior across versions (cryptography 46.x SHA-1 deprecation), add the shim to `conftest.py` rather than patching individual test files. One location, visible to all tests.

### Key Lessons

1. **Column-level exit criteria.** A new ORM column that is always NULL is not "implemented" — it's a stub. Exit criteria for any plan that introduces a new DB column must include: "column is non-null after a successful scan run." Otherwise the column exists in the schema but fails the JSON contract it was designed to serve.
2. **CBOM skip list symmetry is still not automatic.** This lesson appeared in v4.2 (DNSSEC missed in Pass 2). In v4.3, the Vault `elif` guard was skipped intentionally (D-14) — but the fragility was acknowledged rather than resolved. A future audit that catches a transit key registration regression will trace back to this decision. The correct fix is an explicit `elif ep.protocol == 'VAULT'` in Pass 1.
3. **Version bump is a milestone phase task, not a milestone-close finding.** `__init__.py` and `pyproject.toml` version consistency should be a required exit step for the milestone's final phase (or a dedicated gap-closure plan), not discovered at archive time. Add to the phase exit checklist.
4. **Visual rendering is a blocking checkpoint.** Frontend code that is committed but never rendered in a browser is in an unknown state. The `/trends` page deferred from Plan 03 is the canonical example. Human checkpoint at Plan 31-03 should have been `blocked` (not `accepted`) until browser confirmation was obtained.

### Cost Observations

- Model mix: Sonnet 4.6 primary throughout milestone
- Sessions: 2-day execution (2026-04-24 → 2026-04-26); ~208 commits
- Notable: Heaviest infrastructure milestone to date — 6 new scanner surfaces, 16 chaos lab profiles total at ship. Fastest per-phase execution of any milestone (24 plans in 2 days). Critical path discipline and pre-planned carry-over phase kept rework near zero.

---

## Milestone: v4.5 — Reliability & Gap Closure

**Shipped:** 2026-05-03
**Phases:** 7 (38–44) | **Plans:** 40

### What Was Built

- Phase 38: 5-min SESSION_BRACKET fix for `/api/scan/latest` implicit-latest branch + wave_0_complete flip — closed both v4.4 carry-over defects
- Phase 39: Data at Rest React tab — DarFinding Pydantic model + 4 category tables (DB/ObjectStorage/K8s/Vault) — shipped deferred DASH-05
- Phase 40: `_derive_all_profiles()` runtime parser for lab.sh + `expected_results_v4.md` 13-profile oracle + chaos-lab.md 8 profile sections
- Phase 41: TimeoutsCfg/RetryCfg sub-tables, `_wrapped_phase` BaseException helper, scan_error_category column, zero code-reason skips, < 60s default suite
- Phase 42: CycloneDX 1.6 schema gate across 18 profiles; classifier coverage gate; MOTION_PLAINTEXT_PROTOCOLS / DAR_SKIP_PROTOCOLS constants; parametrized skip-list tests
- Phase 43: Zero browser console errors; EmptyStateCard/PageSpinner; axe-core GHA workflow; WCAG AA focus rings; DOM-sentinel PDF gate
- Phase 44: DB/Vault/identity UAT chaos lab integration tests; Phase 31 seeded-DB /api/trends test; 7 of 14 STATE.md carry-over gaps closed

### What Worked

- **Structural drift elimination over discipline** — `_derive_all_profiles()` reading docker-compose.yml at runtime is a permanent fix to a recurring 3x drift problem; better than asking humans to keep a list in sync
- **Parametrized test coverage of skip lists** — extracting MOTION_PLAINTEXT_PROTOCOLS and DAR_SKIP_PROTOCOLS as constants and testing them parametrically caught previously invisible edge cases
- **DOM sentinel for PDF** — waiting for `body[data-ready]` attribute instead of a fixed sleep is the correct asynchronous handshake pattern; discovered organically
- **UAT automation via chaos lab** — closing 7 carry-over items by wiring existing chaos lab profiles to pytest integration tests (rather than one-off scripts) was high-leverage

### What Was Inefficient

- REQUIREMENTS.md checkboxes for GAP-03, GAP-04, CBOM-03 were not updated when the work landed in their respective phases — discovered at milestone close; cost minor cleanup time
- Progress table in ROADMAP.md drifted (phases 38/40/41/42 showed wrong plan counts) — could be fixed automatically when plans complete
- v4.4 RETROSPECTIVE.md entry was never written — skipped gap carried to v4.5 close

### Patterns Established

- `_wrapped_phase` pattern: every scanner phase in run_scan.py should use the BaseException helper — mandatory for all future scanner additions
- Chaos lab UAT automation: when a manual UAT item exists and a chaos lab profile covers it, write an integration pytest test against the profile rather than leaving it as human-UAT
- CycloneDX validation gate: schema validation is now part of CI; new CBOM additions must not introduce schema violations
- DOM-sentinel pattern for async UI/PDF testing: set `body[data-ready]` in React after data loads; wait for it in Playwright

### Key Lessons

1. **Drift is structural, not discipline** — any list that humans must keep in sync with a system file will drift; generate it from the system file at runtime instead
2. **UAT debt accumulates into a milestone-scale task** — 14 carry-over items from v4.2/v4.3 required a full phase (44) to address; keep UAT debt under 5 open items per milestone
3. **Parametrize what you test, not what you eyeball** — skip lists and protocol labels are logic that can be wrong silently without parametrized coverage
4. **Schema validation in CI, not just "it looks right"** — CBOM output was spec-valid but this was only verified locally until Phase 42; gate it from the start of any schema-producing feature

### Cost Observations

- Sessions: ~212 commits across 5 days
- Model: Claude Sonnet 4.x (mixed)
- Notable: Phase 41 (7 plans) was the heaviest single phase; systematic robustness work benefits from tight plan decomposition

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v3.9 Gap Closure | 11 | 40+ | First milestone to use audit-milestone + integration checker gate before close; established BACK-xx backlog and milestones/ archival patterns |
| v4.1 Foundation Polish | 5 | 10 | Correctness-only milestone — no new features; 22/22 requirements satisfied; audit-gap-closure pattern validated at small scale |
| v4.2 Identity Crypto | 8 | 14 | First major scanner expansion since v3.9; 3-phase gap closure sweep; shared session_start contract established; audit caught HIGH-severity ISSUE-3 before ship |
| v4.3 Data at Rest | 7 | 24 | Heaviest infrastructure milestone — 6 scanner surfaces; CRITICAL PATH annotation pattern established; dar_ 5th subscore prefix; GCS sentinel reuse; carry-over phase pre-planned at roadmap creation |
| v4.4 Data in Motion | 6 | 33 | First motion-coverage milestone — email + broker TLS, 6th subscore, motion CBOM; meta-extra pattern `[motion]`; 18-test Nyquist coverage module; CHANGELOG.md introduced; retrospective entry skipped at close |
| v4.5 Reliability & Gap Closure | 7 | 40 | First reliability-only milestone — no new scanner surface; structural drift fixes (runtime profile parser, _wrapped_phase, schema gate); 7/14 UAT debt automated; test count: 662→718 |

### Cumulative Quality

| Milestone | Tests | Notes |
|-----------|-------|-------|
| v3.9 | 199 | 199 tests green at ship; 9 stale Nyquist VALIDATION.md files (BACK-62) |
| v4.1 | 233 | 233 tests green at ship; all 14 VALIDATION.md files updated to nyquist_compliant: true; zero known tech debt |
| v4.2 | 352 | 352 tests green at ship; 7/7 Nyquist VALIDATION.md files compliant; 2 MEDIUM gaps deferred (Phase 25 in v4.3) |
| v4.3 | 504 | 504 tests collected at ship; tech_debt audit status (16 deferred items, all live-env or minor structural); __init__.py version skew fixed at archive time |
| v4.4 | 662 | 662 tests at ship; all Nyquist VALIDATION.md compliant except Phase 36 (DEF-v4.4-01, closed in v4.5) |
| v4.5 | 718 | 718 tests at ship; all Nyquist VALIDATION.md compliant; 7 carry-over UAT gaps remain (cloud-only or browser-only) |

### Top Lessons (Verified Across Milestones)

1. Schedule gap-closure phases explicitly at the end of milestones — defects found late deserve first-class planning treatment, not inline patches
2. Integration audit (`gsd:audit-milestone`) must run before `gsd:complete-milestone` — phase-level verification alone is insufficient to confirm cross-phase wiring is correct
3. Test package manifest version (importlib.metadata) separately from runtime __version__ — editable installs can make them diverge invisibly
4. Dead code deferred across two milestones becomes permanent — enforce dead code deletion in the phase that discovers it, not later
5. Every import-guarded optional dependency must exist in an installable extras group — graceful degradation is only meaningful if the non-degraded path is reachable
6. Shared session_start is an integration contract, not a fix — future scanners added to run_scan.py must accept and use it from Phase 1
7. Column-level exit criteria: a new ORM column that is always NULL is not implemented — exit criteria must include non-null verification after a real scan run
8. Version bump (__init__.py) is a required milestone task, not a milestone-close finding — add to every final phase's exit checklist
9. Drift is structural, not discipline — any list humans must keep in sync with a system file will drift; generate it from the file at runtime instead
10. UAT debt under 5 open items per milestone — beyond that, it requires a dedicated closing phase to address systematically
11. Parametrize skip-list coverage from the first day — skip logic that isn't tested is invisible tech debt
