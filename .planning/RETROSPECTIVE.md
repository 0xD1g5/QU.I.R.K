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

## Milestone: v4.6 — Enterprise Readiness

**Shipped:** 2026-05-05
**Phases:** 6 (45–50) | **Plans:** 24 | **Commits:** 105 | **Timeline:** 3 days

### What Was Built

- Phase 45: `[all]` meta-extra + `quirk.util.optional_extra` probe registry + coverage-gap advisory findings — zero ImportError crashes on `pip install quirk`
- Phase 46: 5 new TLS certificate-defect finding types (expired/self-signed/untrusted-CA/weak-RSA/weak-EC); `chain_verified` DB column with sslyze + fallback plumbing; `tls-cert-defects` chaos lab profile (4 nginx services on 13444–13447)
- Phase 47: `quirk.util.targets` module — comma/`@file`/CIDR multi-target parsing; `--targets-file` CLI flag; nmap pre-scan discovery with `--max-parallelism 100` and 10,000-probe budget TTY guard; CBOM json-validation optional-extra advisory
- Phase 48: `_build_finding` chokepoint enforcing non-empty description/remediation; `NIST_IR_8547_DEPRECATION` constant; FIPS 203/204/205 terminology throughout; CI grep gate (`test_pqc_terminology_gate.py`)
- Phase 49: `quirk/compliance/` module with 24-entry `COMPLIANCE_MAP` (PCI-DSS 4.0.1/HIPAA/FIPS 140-3); `_normalize_for_compliance` longest-prefix-first matcher; staleness CI gate; `quirk compliance status` CLI; Compliance Summary Jinja2 block in reports
- Phase 50: `docs/architecture.md` (3 Mermaid diagrams, connector credential matrix) + `docs/operators-guide.md` (compliance runbook, quarterly cadence); both synced to Obsidian vault `Reference/`

### What Worked

- **Chokepoint-enforced contracts** — `_build_finding` as the single finding emitter made the "non-empty description" invariant trivially testable without touching 20+ call sites individually; the CI grep gate acts as a second enforcement layer
- **3-day execution velocity** — tight milestone scope (7 backlog items, 36 requirements, zero new pip deps in core path) enabled fast execution without context overhead
- **TDD RED-before-GREEN discipline** — Phase 49 Plan 01 spent a full plan writing 5 RED-state tests before any implementation; by Plan 05 all 5 tests were GREEN with zero rework
- **Milestone audit at v4.5 close pre-positioned v4.6** — because requirements, scope, and integration gaps were clarified before execution started, phases 45–50 had no ambiguity at execution time
- **`_normalize_for_compliance` longest-prefix-first** — category normalization using a sorted-by-length descending map cleanly handled f-string title variants without runtime regex

### What Was Inefficient

- Phase 47 ROADMAP.md plan references accidentally listed Phase 45 plan names (copy-paste from template) — discovered at milestone audit; minor cleanup
- Phase 46 VERIFICATION.md was never authored; the milestone closed with a `passed_with_followup` status rather than a clean pass — artifact discipline should match code discipline
- BACK-87 (lab.sh PROFILE_ARGS override bug) was discovered during Phase 46 live-fire verification, introduced workaround friction for that phase and all future chaos lab work until fixed

### Patterns Established

- **Advisory finding pattern** — `ADVISORY`-category CryptoEndpoints + coverage-gap findings are the standard way to surface "configuration missing" without a scan crash; any new optional scanner should follow Phase 45 patterns
- **`_build_finding` chokepoint pattern** — all new finding types should go through `_build_finding()`; no direct dict construction in risk_engine branches
- **Compliance module `UNMAPPED_TITLES` allow-list** — intentionally unmapped finding categories (non-cryptographic advisories) are documented in `UNMAPPED_TITLES` with inline justification; new finding categories need an explicit entry or an UNMAPPED_TITLES annotation
- **Staleness infrastructure for regulatory mappings** — any compliance or regulatory mapping needs `last_verified` + `source_url` + staleness CI gate; this pattern from Phase 49 is the template for future compliance work

### Key Lessons

1. **Scope discipline pays off** — tight scope (zero infra, zero new dependencies in core path, 7 backlog items → 36 requirements) enabled 3-day execution; feature creep and scope drift are the primary execution velocity killers
2. **Chokepoints beat convention** — a single enforced entry point (`_build_finding`) with an assertion is more durable than a convention ("remember to set description") documented in a comment
3. **Regulatory mappings rot without maintenance infrastructure** — shipping a compliance mapping without a staleness CI gate and operator visibility is tech debt from day one; Phase 49 built the infrastructure correctly
4. **Artifact completeness is a first-class deliverable** — Phase 46's missing VERIFICATION.md meant the audit had to work around it; VERIFICATION.md should be authored atomically with the last plan, not deferred

### Cost Observations

- Sessions: 105 commits, 3 days (2026-05-03 → 2026-05-05)
- Model: Claude Sonnet 4.6
- Notable: Phase 49 (5 plans) was the heaviest; compliance module design benefited from the RED-state scaffold phase buying time to think about normalization edge cases before implementation

---

## Milestone: v4.8 — Pre-Primetime Hardening + Operating Model

**Shipped:** 2026-05-14
**Phases:** 13 (57–68, including 64.1) | **Plans:** 53 | **Tasks:** 122

### What Was Built

- Wave A (Phases 57–62): All 15 audit blockers closed — JWT TLS verification, SAML SSRF allowlist, argument-injection guards, bearer auth + CSRF, CORS lockdown, rate-limit middleware, `safe_str` credential scrubbing, score arithmetic clamps, CBOM Pass-1 coverage expansion, React hook cancellation pattern
- Wave B (Phases 63–68): Scheduled scanning, multi-scan trend timeline with regression chips, dashboard-initiated scan with live stage polling, scan history/clone/compare, resumable partial-failure scans, stable operator error-code registry
- Phase 64.1 (audit residual): 5 code fixes for remaining BLOCKERs + 14 structured dispositions (13 deferred-v4.9, 1 wont-fix); AUDIT-TASKS.md zero bare-open BLOCKERs at v4.8 close

### What Worked

- Wave A / Wave B split made the primetime cutover rationale self-documenting; every executor knew exactly what was gating
- Parallel Wave A execution (6 phases on disjoint code paths) compressed the hardening sprint to 2 days
- Pre-phase audit (2026-05-08) with an explicit `AUDIT-TASKS.md` ledger meant zero ambiguity about what "done" looked like at every step
- UAT walkthroughs for browser-visual behaviors completed in the same session as milestone close (no carry-over)

### What Was Inefficient

- REQUIREMENTS.md checkbox tracking fell behind — 15 requirements implemented but never ticked; caught at milestone close pre-flight
- Phase 62 SUMMARY.md files for Plans 01–03 missing (worktree cherry-pick gap); documentation artifact, not code gap, but adds friction at close
- `status: pass` in HUMAN-UAT.md is not recognized by the SDK — only `status: complete` passes the audit gate; discovered at close instead of at execution time

### Patterns Established

- Audit-ledger-as-milestone-input: AUDIT-TASKS.md maps directly to phase requirements with traceability IDs; this pattern should be reused for v4.9 which consumes the same ledger
- Error registry (`quirk/errors.py`): INSTALL-xxx / DASHBOARD-xxx / SCAN-xxx stable codes with cause+remediation is now the mandatory format for all operator-facing errors
- `_wrapped_phase()` + `ScanCheckpoint`: all 12 scanners now use uniform error capture + resumability; new scanners added in v4.9 must adopt the same pattern from day 1

### Key Lessons

- Wave gating requires a CI-enforced check, not just documentation — two phases tried to start Wave B before Wave A was fully closed; caught by executor state checks, not by automation
- `human_needed` VERIFICATION.md status must be resolved before milestone close — carrying it forward creates pre-flight noise; build a "UAT day" into the milestone timeline
- Browser-visual contracts (chart rendering, chip placement, FIFO state) are genuinely untestable by pytest and should be explicitly UAT-budgeted rather than treated as optional

### Cost Observations

- Model mix: Sonnet 4.x primary; Opus for planning agents
- Sessions: ~9 across 6 days (2026-05-09 → 2026-05-14)
- Notable: Wave A subagent parallelism was the most cost-efficient execution pattern in any milestone to date — 6 phases in 2 days with clear code-path isolation

---

## Milestone: v4.10.1 — Scoring Correctness Hotfix

**Shipped:** 2026-05-22
**Phases:** 1 (86) | **Plans:** 3 | **Tasks:** 6

> Note: v4.9 (Audit Depth) and v4.10 (Launch Readiness) retrospective sections were not authored at their closes — a documentation gap in the retrospective ledger. Their records live in `MILESTONES.md` and the `milestones/v4.9-*` / `milestones/v4.10-*` archives.

### What Was Built

- Single-phase vertical MVP slice fixing the marquee overall-readiness score that always rendered `100 / EXCELLENT`. Backend aggregator `_clamp(sum, 0, 100)` → `int(round(sum / 1.5))`; `ScoreGauge.tsx` `maxValue` prop + normalized fraction-based `_gaugeColor()`; six executive subscore radials + Data at Rest tab gauge wired to `maxValue={25}`; version 4.10.0 → 4.10.1 with operator-language changelog.

### What Worked

- Diagnosing the bug as a *triple-layer scale collision* before planning meant the fix scope was correctly bounded — backend + frontend coupled, render-side deferred. The "fixing one half displays a different wrong number" framing justified the single-phase atomic shape and held up through UAT.
- Pre-locking the deferred work (EVIDENCE-TALLY-01, RENDER-CLI-01/PDF-01) as v5.0 Future Requirements at milestone-open time meant the hotfix stayed surgical without losing the follow-up trail.
- TDD boundary tests (100 only at all-25, 0 only at all-zero) gave the aggregation change a precise correctness contract.

### What Was Inefficient

- **Recurrence of the v4.8 lesson:** HUMAN-UAT.md closed with `Result: PASS` but the `audit-open` parser still flagged Phase 86 as `[unknown]` at close — the same status-string recognition gap noted in the v4.8 retrospective (line 325) that was never fixed in the SDK. Cost a manual false-positive verification at close.
- `gsd-sdk query milestone.complete` produced a poor archive: it dumped a raw 1541-line copy of the live ROADMAP into `v4.10.1-ROADMAP.md` and emitted garbled accomplishments (`"One-liner:"`, `"Phase:"`) because the SUMMARY one-liner format didn't match its extractor. Both required full manual rewrite to match the curated archive convention established since v4.10.
- STATE.md prose body carried stale mid-phase content ("86-02 and 86-03 pending") long after the frontmatter said `completed` — resume relied on HANDOFF.json + git to disambiguate.

### Patterns Established

- **Aggregation-fix vs penalty-model-change distinction:** when a score is wrong, first determine whether the *inputs* (penalties) or the *aggregation* is broken. v4.10.1 was purely aggregation — leaving `SCORE_WEIGHTS` untouched kept the diff surgical and the regression surface tiny.
- **Physics-coupled MVP slicing:** when a bug spans layers such that a partial fix produces a *different* wrong output, treat the layers as one indivisible phase rather than separate ones.

### Key Lessons

- The HUMAN-UAT `status:` parser gap is now a *repeat* offender across two milestones — it should be filed as an SDK fix (accept `PASS` / `Result: PASS`) rather than re-litigated by hand at every close.
- Don't trust `milestone.complete`'s ROADMAP archive or accomplishment extraction blindly — always inspect and curate against the established archive format.

### Cost Observations

- Model mix: Opus for the resume + close orchestration; prior phase execution Sonnet-primary
- Sessions: ~2 (phase execution 2026-05-22 AM; milestone close 2026-05-22 PM)
- Notable: smallest milestone to date (1 phase) — overhead was dominated by close ceremony, not implementation

---

## Milestone: v5.0 — Stabilization + Tech Debt Sweep

**Shipped:** 2026-05-22
**Phases:** 6 (87–92) | **Plans:** 16

### What Was Built
Dependency hygiene (Node 20→24, defusedxml→hardened lxml); scoring correctness + six-subscore /25 transparency across CLI/HTML/PDF + 5 zero-algo CBOM profiles fixed; 5 new weak-TLS chaos-lab profiles + identity evidence verified; a digest-pinned OQS-nginx X25519MLKEM768 PQC-hybrid profile with a raw-openssl probe feeding a genuine quantum-safe CBOM component + agility bonus (the post-quantum scoring ceiling); vulture-confirmed dead-code cleanup + a permanent conftest DB-isolation fix; v5.0.0 release.

### What Worked
- **Research-shaped-by-phase:** skipping research on Phase 90 (a live spike had already answered every unknown) and running it on Phase 91 (which explicitly deferred file-resolution to a vulture pass) — research earned its place where uncertainty was real, and the 91 researcher *shrank the phase* by finding most BACK items already deleted.
- **Goal-backward verification caught a real seam break:** Phase 90's verifier found that the classifier alias + agility scoring were green while the probe→CBOM-builder integration was silently severed (no genuine quantum-safe component emitted). Three layers of passing tests had masked it. A one-line `_KEX_MAP` gap-closure fixed it.
- **The cleanup phase paid down the milestone's own bookkeeping debt:** Phase 91's CLEAN-03 retroactively closed Phase 89's `gaps_found` (unflipped LAB REQUIREMENTS rows).

### What Was Inefficient
- **Recurring REQUIREMENTS.md row-flip omission:** executors repeatedly left traceability rows `pending` after completing work (89 LAB rows, 90 PQC rows, 92 REL-01) — each needed a manual or gap-closure fix. A standing executor checklist item or a closeout sweep would remove the recurring toil.
- **Premature tag creation:** the 92-01 executor created the `v5.0.0` tag mid-phase (wrong commit); caught and deleted, recreated correctly at the final close-out HEAD via the human-verify checkpoint. Tag creation belongs only at the gated final step.
- **milestone.complete raw-dump + garbled accomplishments** required full hand-curation of MILESTONES.md (known issue).

### Patterns Established
- A demoable capability anchor inside a stabilization milestone (OQS-nginx PQC ceiling) gives an otherwise-internal cycle a customer-facing headline.
- Sequential-on-main execution (not worktree-parallel) is the right choice for Docker-coupled, human-verify-checkpoint-heavy phases.

### Key Lessons
- Verify the *integration seam*, not just the unit: passing classifier/scoring/evidence tests did not prove the probe→CBOM path was wired.
- Reconcile audit-open's literal status-string grep against the milestone audit's content-level judgment — VERIFICATION status strings (88 human_needed, 89 gaps_found) lagged reality.

### Cost Observations
- Model mix: planning/verification on opus + sonnet; executors + checkers on sonnet.
- Notable: a true stabilization cycle — bounded ≤6 phases per HORIZON; the value was in paid-down debt + one demoable anchor, not new surface.

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
| v4.6 Enterprise Readiness | 6 | 24 | Install-day UX, 5 TLS finding types, nmap/multi-target, rich finding context, compliance mapping to PCI-DSS/HIPAA/FIPS 140-3, enterprise docs |
| v4.7 Governance & Compliance Platform | 7 | 27 | QRAMM data model + evidence bridge, assessment UI, compliance mapping view, PDF governance section, staleness CI gate, `quirk doctor` health check |
| v4.8 Pre-Primetime Hardening + Operating Model | 13 | 53 | Audit-driven Wave A (15 blockers) + Wave B operating model (scheduled scans, trends, dashboard scan launch, history/compare, resumable scans, error registry); first milestone with subagent-parallel Wave execution |
| v4.9 Audit Depth | 9 (+69.1) | 38 | Closed the 2026-05-08 audit ledger entirely (166 closed / 2 deferred / 4 wont-fix); zero-bare-open invariant locked via CI gate (retrospective section not authored at close) |
| v4.10 Launch Readiness | 8 | 31 | S/MIME + AD CS coverage, CMVP feed, HTML/PDF injection hardening, full release engineering (Trusted Publishers + Sigstore + towncrier + multi-arch GHCR + Homebrew); 52/52 reqs (retrospective section not authored at close) |
| v4.10.1 Scoring Correctness Hotfix | 1 | 3 | Smallest milestone — single physics-coupled MVP slice fixing the overall-readiness clamp bug (backend `sum/1.5` + ScoreGauge `maxValue`); render-side + evidence-tally deferred to v5.0 Phase 01 |

### Cumulative Quality

| Milestone | Tests | Notes |
|-----------|-------|-------|
| v3.9 | 199 | 199 tests green at ship; 9 stale Nyquist VALIDATION.md files (BACK-62) |
| v4.1 | 233 | 233 tests green at ship; all 14 VALIDATION.md files updated to nyquist_compliant: true; zero known tech debt |
| v4.2 | 352 | 352 tests green at ship; 7/7 Nyquist VALIDATION.md files compliant; 2 MEDIUM gaps deferred (Phase 25 in v4.3) |
| v4.3 | 504 | 504 tests collected at ship; tech_debt audit status (16 deferred items, all live-env or minor structural); __init__.py version skew fixed at archive time |
| v4.4 | 662 | 662 tests at ship; all Nyquist VALIDATION.md compliant except Phase 36 (DEF-v4.4-01, closed in v4.5) |
| v4.5 | 718 | 718 tests at ship; all Nyquist VALIDATION.md compliant; 7 carry-over UAT gaps remain (cloud-only or browser-only) |
| v4.6 | ~800 | Compliance mapping + enterprise docs added; test count estimated |
| v4.7 | ~850 | QRAMM 35-test suite added; staleness CI gates added |
| v4.8 | ~900+ | 31 pre-existing failures unrelated to v4.8 work remain; Wave A regression suites added (auth/CSRF/rate-limit: 16 tests, score arithmetic: 45 tests, credential scrubbing: 32 tests) |

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
