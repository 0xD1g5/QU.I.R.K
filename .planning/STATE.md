---
gsd_state_version: 1.0
milestone: v3.9
milestone_name: Gap Closure
status: executing
stopped_at: Completed 15-01-PLAN.md (Wave 0 TDD scaffold for code hygiene)
last_updated: "2026-04-08T02:24:58.082Z"
last_activity: 2026-04-08
progress:
  total_phases: 17
  completed_phases: 13
  total_plans: 48
  completed_plans: 51
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-06)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours
**Current focus:** Phase 15 — code-hygiene

## Current Position

Phase: 15 (code-hygiene) — EXECUTING
Plan: 2 of 2
Status: Ready to execute
Last activity: 2026-04-08

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
| Phase 05-web-dashboard P01 | 93 | 2 tasks | 4 files |
| Phase 05-web-dashboard P06 | 3 | 2 tasks | 6 files |
| Phase 05-web-dashboard P04 | 6 | 3 tasks | 9 files |
| Phase 05-web-dashboard P05 | 3 | 2 tasks | 4 files |
| Phase 06-documentation P01 | 12 | 2 tasks | 3 files |
| Phase 06-documentation P02 | 2 | 1 tasks | 1 files |
| Phase 06-documentation P03 | 12 | 2 tasks | 4 files |
| Phase 06-documentation P04 | 6 | 1 tasks | 1 files |
| Phase 06-documentation P05 | 2 | 1 tasks | 1 files |
| Phase 06-documentation P06 | 8 | 2 tasks | 2 files |
| Phase 07 P01 | 109 | 2 tasks | 7 files |
| Phase 07 P02 | 12 | 2 tasks | 5 files |
| Phase 07 P05 | 8 | 2 tasks | 6 files |
| Phase 07-polish-and-packaging P04 | 20 | 3 tasks | 6 files |
| Phase 07 P03 | 128 | 2 tasks | 3 files |
| Phase 08-legacy-debt-cleanup P02 | 5 | 2 tasks | 3 files |
| Phase 08 P01 | 115 | 2 tasks | 8 files |
| Phase 08 P03 | 3 | 2 tasks | 8 files |
| Phase 08-legacy-debt-cleanup P04 | 85 | 2 tasks | 2 files |
| Phase 09-scoring-consolidation P01 | 2 | 2 tasks | 3 files |
| Phase 09-scoring-consolidation P02 | 12 | 2 tasks | 4 files |
| Phase 09-scoring-consolidation PP03 | 8 | 2 tasks | 5 files |
| Phase 10-v39-gap-closure P01 | 89 | 2 tasks | 2 files |
| Phase 10-v39-gap-closure P02 | 4 | 3 tasks | 3 files |
| Phase 11-dashboard-wiring-fixes P01 | 2 | 2 tasks | 3 files |
| Phase 11 P02 | 3 | 1 tasks | 1 files |
| Phase 12-cli-correctness P01 | 2 | 1 tasks | 1 files |
| Phase 12 P02 | 2 | 2 tasks | 6 files |
| Phase 13-interactive-mode-overhaul P01 | 8 | 1 tasks | 1 files |
| Phase 13-interactive-mode-overhaul PP02 | 3 | 2 tasks | 3 files |
| Phase 14-scoring-intelligence-correctness P01 | 2 | 1 tasks | 1 files |
| Phase 14-scoring-intelligence-correctness P02 | 5 | 3 tasks | 2 files |
| Phase 15-code-hygiene P01 | 2 | 1 tasks | 1 files |

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
- [Phase 05-web-dashboard]: httpx excluded from dashboard optional group — already in main deps; avoids version conflict
- [Phase 05-web-dashboard]: deferred import in conftest.py dashboard_client fixture — try/except ImportError so stubs skip cleanly before quirk.dashboard exists
- [Phase 05-web-dashboard]: FastAPI/uvicorn/playwright in optional dashboard group — keeps CLI-only installs free of dashboard deps
- [Phase 05-web-dashboard]: sync_playwright imported at module level so mock.patch can intercept it in graceful-degradation tests
- [Phase 05-web-dashboard]: json.dumps() used for PDF error serialization — Playwright error messages contain control chars that break f-string JSON
- [Phase 05-web-dashboard]: conftest.py uses sqlite:///file::memory:?cache=shared&uri=true so in-memory DB is accessible from FastAPI sync route worker threads — plain :memory: creates separate per-connection DB
- [Phase 05-web-dashboard]: Findings derived at API layer from CryptoEndpoint columns — no separate findings table needed for v1
- [Phase 05-web-dashboard]: cytoscape-extensions.d.ts declares ambient module types for cose-bilkent and dagre — no @types packages available, ambient declaration is the TypeScript solution
- [Phase 05-web-dashboard]: CBOM graph uses breadthfirst for <15 nodes, cose-bilkent for >=15 — balances layout quality vs compute cost for typical vs large CBOM inventories
- [Phase 06-documentation]: README fully replaced — zero qcscan/QuRisk/Quantum Crypto Scanner references remain
- [Phase 06-documentation]: docs/ directory at repo root with plain Markdown per D-03 — no build step, GitHub-compatible relative links
- [Phase 06-documentation]: All config.yaml keys documented with type, default, and description — verified against config.yaml and ConnectorsCfg dataclass
- [Phase 06-documentation]: Scan profiles (quick/standard/deep) and score profiles (lenient/balanced/strict) documented with use-case guidance in docs/configuration.md
- [Phase 06-documentation]: IAM policy JSON derived from exact boto3 calls in aws_connector.py — 7 actions across 4 services (ACM, KMS, CloudFront, ELBv2), no wildcards, no write access
- [Phase 06-documentation]: Azure RBAC uses Reader + Key Vault Reader built-in roles at subscription scope — no custom role definition needed
- [Phase 06-documentation]: Docker guide documents full CRYPTO_LIB_ALLOWLIST; Git guide documents p/cryptography anti-pattern table (WEAK_ALGORITHM, HARDCODED_KEY, WEAK_RANDOM, DEPRECATED_PROTOCOL)
- [Phase 06-documentation]: Two-layer structure (reference table + Client Conversation sidebox) per D-08 — serves consultant preparing offline AND glancing at guide during live client meeting
- [Phase 06-documentation]: Report interpretation guide score band thresholds sourced verbatim from scoring.py _rating(): EXCELLENT>=85, GOOD>=70, MODERATE>=55, FAIR>=35, POOR<35
- [Phase 06-documentation]: Three-section CBOM guide structure per D-10: compliance-officer / technical pipeline / audit evidence — matches three distinct reader audiences
- [Phase 06-documentation]: alg:none documented as quantum-vulnerable (nist_level=0) with explicit callout that actual risk is authentication bypass — prevents consultant mischaracterization
- [Phase 06-documentation]: Vault port is 20009 (not 20008 as in CONTEXT.md D-14) — docker-compose.yml is the ground truth per RESEARCH.md Pitfall 4
- [Phase 06-documentation]: docs/chaos-lab.md is authoritative chaos lab operator guide; CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md retained as historical artifact per D-15
- [Phase 07]: jinja2>=3.1.0 and rich>=13.0.0 added as core dependencies — required for CLI + report outputs in Phase 7
- [Phase 07]: Wave 0 TDD scaffold: 10 RED stubs define full Phase 7 implementation contract; 7 behaviors already GREEN
- [Phase 07]: init subcommand intercept placed before serve intercept — mirrors serve pattern exactly
- [Phase 07]: tqdm=None retained after import removal to preserve residual references during transition (D-04)
- [Phase 07]: importlib.resources.files('quirk').joinpath('config_template.yaml') used for template lookup in run_init() — works after pip install with os.path fallback for dev
- [Phase 07]: quirk init defaults to 127.0.0.1 target and warns (not errors) on overwrite — idempotent for automation
- [Phase 07]: docs/getting-started.md primary install changed to git+https GitHub URL; PyPI coming-soon note removed
- [Phase 07-polish-and-packaging]: Use path-based SVG primitives for favicon (no text/font elements) to ensure cross-browser compatibility
- [Phase 07-polish-and-packaging]: FileSystemLoader with os.path.dirname(__file__) used for Jinja2 template loading — no pip reinstall needed during development
- [Phase 07-polish-and-packaging]: render_pdf_report() returns bool; pdf_path=None in write_reports() when Playwright unavailable — graceful degradation for HTML-only installs
- [Phase 08-legacy-debt-cleanup]: Backward compat for enable_windows_adcs: dict comprehension exclude in config_from_dict rather than pop() — avoids mutating caller dict
- [Phase 08]: config_template.yaml uses flat connectors block matching ConnectorsCfg field names exactly; documentation URL changed from [owner] placeholder to relative path ./docs/configuration.md
- [Phase 08-legacy-debt-cleanup]: D-15: migration_advisor 'deprecated tls' -> 'legacy tls' to match actual risk_engine finding title; removed dead 'public key' pattern
- [Phase 08-legacy-debt-cleanup]: D-17: cfg.scan mutations in TLS and SSH phases wrapped in try/finally for safe config restore on exception
- [Phase 08-legacy-debt-cleanup]: D-13/D-20/D-21: Removed 4 dead writer.py functions, replaced utcnow() with timezone.utc, eliminated tqdm dead branch
- [Phase 08-legacy-debt-cleanup]: validate.py expected_files now mirrors actual writer.py output: findings, executive-summary, technical-findings, scorecard, roadmap, run-stats, cbom .cdx.json, cbom .cdx.xml
- [Phase 08-legacy-debt-cleanup]: _validate_calibration() and _validate_delta() removed — dead code for artifacts that writer.py never produces
- [Phase 08-legacy-debt-cleanup]: _latest_intelligence() and _previous_intelligence() sort by st_mtime not filename to handle same-second-timestamp edge cases
- [Phase 09-scoring-consolidation]: D-05/D-06: PROFILE_MULTIPLIERS applies agility_/identity_ prefix multipliers before weights= override; profile= falls back to balanced on unknown names
- [Phase 09-scoring-consolidation]: Wave 0 expectedFailure stubs in ExecutiveConsolidationTests define executive.py migration contract for Plan 02
- [Phase 09-scoring-consolidation]: executive.py imports ONLY from intelligence/ plus migration_advisor; profile+weights wired at both call sites; calibration block added to intelligence JSON
- [Phase 09-scoring-consolidation]: D-02 complete: four assessment compute modules deleted; operator_context.py and migration_advisor.py preserved (used by run_scan.py and executive.py respectively)
- [Phase 09-scoring-consolidation]: Profile multiplier table added to docs/configuration.md: strict=1.4x, balanced=1.0x, lenient=0.7x on agility and identity weights
- [Phase 10-v39-gap-closure]: _QS_DISPLAY promoted to module level in scan.py so all three consumer functions share one display label map
- [Phase 10-v39-gap-closure]: Two-step classify_algorithm(alg) -> quantum_safety_label(nist_level) enforced at all call sites — no direct string-to-label shortcut
- [Phase 10-v39-gap-closure]: dashboard/static/**/* glob in pyproject.toml is relative to quirk/ package root — setuptools >= 68 resolves it recursively to include React bundle
- [Phase 10-v39-gap-closure]: Intelligence block in config_template.yaml is fully commented — pure discoverability for quirk init users with zero runtime impact
- [Phase 11-dashboard-wiring-fixes]: sys.modules patch used instead of patch('uvicorn.run') — uvicorn is lazily imported inside serve() and not installed in test env; sys.modules injection intercepts the import cleanly
- [Phase 11-dashboard-wiring-fixes]: SSH CBOM tests left RED intentionally — they define the Plan 02 implementation contract for ssh_audit_json parsing
- [Phase 11-dashboard-wiring-fixes]: _SSH_TYPE dict defined inline in _derive_cbom() for-ep loop — self-contained, no shared state; _qs_for_alg() handles @openssh.com vendor suffixes via except Exception guard; json.loads wrapped in (JSONDecodeError, TypeError, ValueError) matching builder.py exactly
- [Phase 12-cli-correctness]: test_config_default_version uses pathlib source inspection (not import) to assert the fallback string in config_from_dict — catches exact value before any module reload
- [Phase 12-cli-correctness]: Phase 12 TDD contract: 3 RED tests (version, config fallback, owner placeholder) define Plan 02 implementation targets; 3 GREEN tests guard existing correctness (template alignment, no quirk scan refs, load_config)
- [Phase 12-cli-correctness]: Version strings updated individually in each file (no shared import) — circular import avoidance intentional per RESEARCH.md D-01
- [Phase 12-cli-correctness]: getting-started.md uses <your-repo-url> generic placeholder per D-06 — no specific GitHub handle hardcoded
- [Phase 12-cli-correctness]: test_packaging.py stale 4.0.0 assertion updated to 4.1.0 as Rule 1 auto-fix — version bump is the intended change
- [Phase 13-interactive-mode-overhaul]: MINIMAL_INPUTS constant encodes new D-15 prompt order; tests copy with list() to avoid shared mutable state
- [Phase 13-interactive-mode-overhaul]: All 10 INTER tests use @unittest.expectedFailure — suite stays green (xfail) while tests are individually RED against current interactive.py
- [Phase Phase 13-interactive-mode-overhaul]: datetime.datetime.now().astimezone().tzname() auto-detects timezone; fallback UTC on exception (D-01)
- [Phase Phase 13-interactive-mode-overhaul]: scan_profile default initialized from args.profile before if/else to avoid dangling reference (D-08)
- [Phase Phase 13-interactive-mode-overhaul]: @unittest.expectedFailure removed from all 10 interactive mode tests after Plan 02 makes them GREEN
- [Phase 14-scoring-intelligence-correctness]: SCORE-01/SCORE-03 tests pass immediately as regression guards; SCORE-02/SCORE-04 tests confirm bugs exist with inspect.signature and inspect.getsource assertions
- [Phase 14-scoring-intelligence-correctness]: validate_run now accepts only output_dir: Path — dead require_delta_if_baseline parameter removed from signature and main() argparse
- [Phase 14-scoring-intelligence-correctness]: Dashboard reads calibration.profile (not assessment.profile) from latest intelligence JSON at request time; profile=None fallback to balanced on I/O error
- [Phase 15-code-hygiene]: HYGN-02 SSH test uses inspect.getsource structural assertion to detect mutations precede try block — matches Phase 14 pattern
- [Phase 15-code-hygiene]: HYGN-04 test covers all 14 completed phases (not 11 in REQUIREMENTS.md) — phases 12-14 added after requirement was written

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 13 and Phase 14 both depend on Phase 12 (CLI Correctness) — correctness baseline must be solid before expanding interactive mode or wiring scoring
- Phase 15 (Code Hygiene) is independent of 13 and 14 but logically follows Phase 12 to avoid removing files that correctness fixes might touch

## Session Continuity

Last session: 2026-04-08T02:24:58.078Z
Stopped at: Completed 15-01-PLAN.md (Wave 0 TDD scaffold for code hygiene)
Resume file: None
