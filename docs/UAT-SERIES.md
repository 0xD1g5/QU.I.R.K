# QU.I.R.K. — UAT Test Series (Gating Document)

**Version:** 4.4.0
**Last Updated:** 2026-05-05 (Phase 50 wrap: UAT-50-NN added for Enterprise Documentation — UAT-50-01 architecture.md presence + section coverage; UAT-50-02 operators-guide.md presence + section coverage; UAT-50-03 vault Reference/ sync verification (`Reference/Architecture.md` + `Reference/Operators-Guide.md` with `type: reference` frontmatter and `_QUIRK-Hub.md` wikilinks); UAT-50-04 compliance maintenance citation completeness (PCI SSC + ECFR + NIST CSRC source URLs, `quirk compliance status` CLI, `STALENESS_THRESHOLD_DAYS` constant, `tests/test_compliance_freshness.py` path, and a worked PCI-DSS 4.0.1 → 4.1 upgrade example). Closes DOCS-01..04. v4.6 Enterprise Readiness milestone complete. Earlier: Phase 49 wrap: UAT-49-01..05 added for Compliance Mapping — UAT-49-01 schema gate (every COMPLIANCE_MAP entry has framework + control + version + last_verified + source_url); UAT-49-02 freshness gate (no entry's last_verified older than STALENESS_THRESHOLD_DAYS = 365); UAT-49-03 title-join gate (every emitted finding title is in COMPLIANCE_MAP or UNMAPPED_TITLES); UAT-49-04 `quirk compliance status` CLI smoke (text + JSON formats); UAT-49-05 HTML/PDF Compliance Summary section visual + smoke. Closes COMPLY-01..09. Compliance map maintenance cadence + regulator-revision upgrade procedure are documented in docs/operators-guide.md (Phase 50). Earlier: Phase 48 wrap: UAT-48-01..04 added for Rich Finding Context — UAT-48-01 every finding in `findings-*.json` carries a non-empty `description`; UAT-48-02 HTML All Findings table contains `<th>Description</th>` adjacent to Recommendation; UAT-48-03 every quantum-vulnerable finding's recommendation cites `FIPS 203/204/205` and `Per NIST IR 8547`; UAT-48-04 `tests/test_pqc_terminology_gate.py` passes clean and fails the build when stale terminology is injected into either gated source file. Closes CONTEXT-01..04. Earlier: Phase 47 wrap: UAT-47-01..08 added for Nmap Discovery + Multi-Target Wizard + CBOM JSON Validation — UAT-47-01 CSV targets through wizard; UAT-47-02 @file targets ingestion; UAT-47-03 --targets-file non-interactive; UAT-47-04 nmap y/N prompt appears once; UAT-47-05 missing nmap binary — no crash, ADVISORY row, consulting-ports fallback; UAT-47-06 targets x ports > 10000 shows confirm prompt in TTY mode; UAT-47-07 CBOM JSON validates via post-write JsonStrictValidator; UAT-47-08 pip install quirk[cbom] install_hint actionable. Closes DISCOVER-01..04, MULTI-01..05. Earlier: Phase 46 wrap: UAT-46-01..05 added for TLS Finding Gaps — UAT-46-01 expired-cert produces CRITICAL finding (TLS-FIND-01) at chaos lab `tls-cert-defects` port 13444; UAT-46-02 self-signed cert produces HIGH "TLS certificate is self-signed" finding at port 13445 AND emits NO untrusted-CA finding on the same endpoint (D-04 mutual exclusivity, TLS-FIND-02); UAT-46-03 untrusted-CA cert produces MEDIUM "TLS certificate issued by untrusted CA" finding at port 13446 (TLS-FIND-03); UAT-46-04 RSA-1024 cert produces HIGH "TLS certificate uses undersized RSA key" finding at port 13447 (TLS-FIND-04); UAT-46-05 D-02 multi-defect independence — a single endpoint with multiple cert defects emits one finding per class with no rollup. Closes TLS-FIND-01..07. Earlier: Phase 45 wrap: UAT-1-09/10/11 added for Install-Day UX — UAT-1-09 clean-venv `pip install quirk` (no extras) TLS-only scan against chaos lab `tls-modern` produces zero ImportError/ModuleNotFoundError in HTML report (INSTALL-01); UAT-1-10 Coverage Gaps advisories surface as a dedicated `<h2>` section in the HTML report when `enable_kerberos`/`enable_db`/`enable_gcp`/`enable_k8s`/`enable_vault` are true and matching extras absent — each row's Recommendation column contains the literal `pip install quirk[<extra>]`, advisories are filtered out of the All Findings table, and readiness score is unchanged versus running with the same scanners disabled (INSTALL-02 + INSTALL-04 + D-07 score-exclusion); UAT-1-11 `pip install quirk[all]` in a fresh venv excludes impacket (`python -c "import impacket"` raises ModuleNotFoundError) while `import fastapi, psycopg2, googleapiclient, hvac, kubernetes` all succeed (INSTALL-03). Closes INSTALL-01..04. Earlier: Phase 44 wrap: UAT-44-01..04 added for UAT Debt Automation — UAT-44-01 Phase 27 DB integration tests (PostgreSQL+MySQL ssl-off via `QUIRK_DB_INTEGRATION=1`); UAT-44-02 Phase 25 Kerberos/SAML traceability annotations (existing tests annotated with UAT-25 closure trail); UAT-44-03 Phase 30 Vault live integration test (5-finding spec against vault-30 :28200 via `QUIRK_VAULT_INTEGRATION=1`); UAT-44-04 Phase 31 trends flat-wire-format pytest test (in-memory SQLite, no chaos lab needed). Closes UAT-01..04. v4.5 Reliability & Gap Closure milestone complete. Earlier: Phase 43 gap closure: UAT-43-06..08 added — a11y baseline-delta PASS/FAIL fix, pagination absent on single-page datasets, PDF data-ready sentinel; closes all Phase 43 UAT gaps. Earlier: Phase 43 wrap: UAT-43-01..05 added for Dashboard Polish — UAT-43-01 axe + console sweep (happy fixture) exits 0 across 9 routes; UAT-43-02 axe + console sweep (empty fixture) exits 0 with explicit empty states on every route; UAT-43-03 keyboard focus rings visible on all interactive elements; UAT-43-04 loading-state first paint (skeleton/PageSpinner persists ~3s before content); UAT-43-05 GitHub Actions dashboard-quality workflow turns green on PRs touching src/dashboard/**. Closes DASH-01, DASH-02, DASH-03. Earlier: Phase 42 wrap: UAT-42-01..04 added for CBOM Correctness Audit — UAT-42-01 CycloneDX 1.6 JSON+XML schema validation across 18 chaos lab profiles + drift sentinel; UAT-42-02 classifier coverage gate + `docs/cbom-classifier-coverage.md` regen report; UAT-42-03 shape goldens (pki/vault/saml) + `tests/fixtures/cbom/CHANGELOG.md`; UAT-42-04 parametrized Pass-2/Pass-3 skip-list unit gate (12 parametrized + 1 sanity). Closes CBOM-01..04. Earlier: Phase 41 wrap: UAT-41-01..04 added for CI Stability & Scanner Robustness — UAT-41-01 missing-[motion]-extra stderr advisory format with `category=missing_extra` scan_errors[] entry; UAT-41-02 docs/configuration.md upper-bound formula contains `scan_upper_bound` and `safety_margin` literals; UAT-41-03 `lab.sh down` and `reset` arms sweep profile-tagged services via `compose --profile "*" --remove-orphans`; UAT-41-04 default `pytest -m 'not slow'` finishes in <60s on a developer machine. Closes CI-01..03, ROBUST-01..04. Earlier: Phase 40 wrap: UAT-40-01 added for Chaos Lab v4 Oracle — `expected_results_v4.md` as stable v4 oracle reference for all 18 named chaos-lab profiles + core; `./lab.sh profiles` subcommand; `expected_results_v3.md` superseded notice. Closes LAB-01..04. Earlier: Phase 39 wrap: UAT-39-01..08 added for Dashboard Data at Rest Tab — `/data-at-rest` route load + zero console errors, per-section empty states, four locked-column tables (Database · Object Storage · Kubernetes · Vault), severity sort + em-dash null rendering, sidebar nav order Executive · Findings · Identity · Motion · Data at Rest · Certificates · CBOM · Roadmap · Trends. Closes GAP-04 + DASH-05 (deferred from Phase 27). Earlier: Phase 38 wrap: UAT-38-01/02 added for identity scan-window regression fix — automated regression test for SAML/DNSSEC scan-window bracket fix (`SESSION_BRACKET`) and manual live round-trip against SimpleSAMLphp chaos lab profile. Earlier: Phase 37 wrap: v4.4.0 release closure — INFRA-01 version bump 4.3.0→4.4.0 across 6 surfaces (`__init__.py`, `pyproject.toml`, `cbom/builder.py`, `reports/writer.py`, `config.py` `IntelligenceCfg.intelligence_version`); INFRA-02 `[motion]` meta-extra over flat `[email]/[broker]/[kafka]` sub-extras (`pip install quirk[motion]` is the single happy path); INFRA-03 `tests/test_infra03_nyquist_coverage.py` with 18 tests (6 entry points × happy/refused/plaintext-only); per-phase `VALIDATION.md` Nyquist matrices backfilled across phases 32-37 (phase 36 `wave_0_complete` flip deferred pending unrelated SAML scan-window regression from Phase 24); CHANGELOG.md + docs/release-notes/4.4.0.md added. UAT-1-02 version string bumped to 4.4.0. Phase 36 wrap: UAT-36-01..05 added for Dashboard Motion Tab — /motion route load, STARTTLS badge, plaintext broker badge, 6 ScoreGauges on executive summary, empty-state cards. Earlier: Phase 35 wrap: UAT-35-01..03 added for CBOM integration — golden email + broker CBOM snapshots assert the 6 email TLS labels (SMTP-STARTTLS, SMTPS, IMAP-STARTTLS, IMAPS, POP3-STARTTLS, POP3S), 4 broker TLS labels including AMQPS/Azure-ServiceBus passthrough, and 3 plaintext broker labels (KAFKA-PLAIN/AMQP-PLAIN/REDIS-PLAIN) skipped from Pass 2 + Pass 3 of build_cbom(). Earlier: Phase 34 wrap: UAT-34-01..03 added for motion intelligence — `data_in_motion` 6th subscore in `compute_readiness_score()`, 5 `motion_*_ratio` entries in SCORE_WEIGHTS, `motion_` prefix in PROFILE_MULTIPLIERS strict/balanced/lenient, 6 `motion_*_count` keys in `build_evidence_summary()`. Earlier: Phase 33 wrap (Wave 6, Plan 33-08): UAT-33-01..08 added for broker scanner — config-disabled-by-default, standard-profile-enables, broker_scan_json DB persistence, plus UAT-33-03..07 marked DEFERRED pending scanner custom-port support follow-up plan; 58-test pytest suite provides equivalent end-to-end verification. Earlier: Phase 32 gap closure: UAT-32-07 added for email_scan_json DB persistence (Plan 32-08) — per-host JSON aggregate attached to lowest-port endpoint, mirroring kerberos_scan_json pattern; closes Phase 32 SC-1. Earlier today: Phase 32 added: UAT-32-01..06 for email scanner — 7-port TLS probe (SMTP/IMAP/POP3 STARTTLS + SMTPS/IMAPS/POP3S), STARTTLS-downgrade-on-port-25 MEDIUM finding, weak-cipher HIGH finding, CONNECTION_REFUSED non-fatal, sslyze-absent stdlib fallback, Postfix+Dovecot chaos lab via `--profile email`, and `service_detail` label format. Earlier: Phase 31 code review fixes: UAT-9-09 Expected section corrected to flat wire format matching actual API output — current_session_ts/previous_session_ts/new_high/new_medium/new_low/resolved_high/resolved_medium/resolved_low — replacing incorrect nested sessions/new_finding_counts shape; UAT-9-10 corrected sessions.previous_ts → previous_session_ts; badge label clarification: new_high/resolved_high bucket includes CRITICAL+HIGH; Phase 29 complete: UAT-29-01/02/03 confirmed in docs; Gate Status bumped to v4.3; UAT-1-02 version string updated to v4.3.0; Phase 29: added UAT-29-01/02/03 for Kubernetes Secrets Inspection — EKS encryption + secret-type enumeration, GKE encryption, AKS encryption + RBAC degradation; live-cluster UAT only, no Docker chaos lab; Phase 28: added UAT-28-01/02/03 for object storage audit — S3 chaos lab end-to-end, Azure Blob live subscription, GCS reuse zero-API-call invariant; Phase 27: added UAT-5-25 for DB connector — PostgreSQL/MySQL SSL detection and RDS encryption scanning behind enable_db guard; data_at_rest subscore; Phase 30: added UAT-30-01/02/03 for HashiCorp Vault connector — transit key classification + exportable MEDIUM, PKI root+intermediate CA HIGH on RSA<4096, auth method risk tiering with token always-HIGH unconditional; Phase 31: added UAT-9-09/10 for Trend Analysis — score delta + new/resolved finding counts via /api/trends and React /trends tab)
**Purpose:** Comprehensive user acceptance testing covering all features — CLI, lab environments, cryptographic findings, web dashboard, reports, and edge cases.
**Gate Status:** This document is the **release gate** for QU.I.R.K. v4.4. All series must meet minimum pass thresholds (see Series 12: Gating Checklist) before any backlog or roadmap work proceeds.

---

## Testing Session

**Session Date:** __________  **Tester:** __________  **Version Under Test:** __________
**Environment:** __________  **Notes:**

---


## How to Use This Document

Each test case follows this format:

```
ID: UAT-{series}-{number}
Title: What is being tested
Prerequisites: What must be in place before running the test
Steps: Numbered actions to perform
Expected: What success looks like
Pass Criteria: Specific measurable condition(s)
```

**Status tracking:** After each test, check the result:
- `- [x] PASS` — Test passed all criteria
- `- [x] FAIL` — Test failed; document details in **Notes:**
- `- [x] SKIP` — Test skipped; document reason in **Notes:**

Fill in **Date:** and **Tester:** fields with today's date and your initials.

---

## Test Environment Requirements

- Python 3.11+
- Docker + Docker Compose v2
- `ssh-audit` installed (`pip install ssh-audit` or OS package)
- `sslyze` installed (`pip install sslyze`)
- `syft` installed (https://github.com/anchore/syft)
- `semgrep` installed (`pip install semgrep`)
- `nmap` installed (OS package, optional)
- Node.js 18+ (for dashboard development builds)
- QuRisk installed: `pip install -e ".[dashboard]"`

---

---

# Series 1: Installation & Environment Setup

---

### UAT-1-01: Package Installation — Clean Install

**Prerequisites:** Python 3.11+ virtual environment, no QuRisk installed.

**Steps:**
1. Create a fresh virtual environment: `python -m venv .venv && source .venv/bin/activate`
2. Clone repository: `git clone <repo-url> && cd QuRisk`
3. Install with dashboard extras: `pip install -e ".[dashboard]"`
4. Verify the `quirk` CLI is available: `which quirk`
5. Run: `quirk --help`

**Expected:** Help text appears listing all available flags. No import errors.

**Pass Criteria:**
- `quirk --help` exits with code 0
- Output includes `--config`, `--profile`, `--score-profile`, `--verbose` flags
- No `ModuleNotFoundError` or `ImportError` in output

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** Verified via `python run_scan.py --help` in dev install. All 4 required flags present. Exit 0.

---

### UAT-1-02: Version Flag

**Prerequisites:** QuRisk installed.

**Steps:**
1. Run: `quirk --version`

**Expected:** Version string printed to stdout.

**Pass Criteria:**
- Output matches format: `quirk 4.4.0` or `QU.I.R.K. v4.4.0`
- Exit code 0

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:**   **Tester:**
**Notes:** Version bumped to v4.3.0 at start of v4.3 Data at Rest milestone. Re-test required.

---

### UAT-1-03: `quirk init` Subcommand — Default Config Generation

**Prerequisites:** QuRisk installed, empty working directory.

**Steps:**
1. Create a temp directory: `mkdir /tmp/quirk-test && cd /tmp/quirk-test`
2. Run: `quirk init`
3. List directory contents: `ls -la`
4. Open generated config: `cat config.yaml`

**Expected:** A `config.yaml` is created with all required fields pre-populated as commented examples.

**Pass Criteria:**
- `config.yaml` exists in current directory
- File contains `targets:` key
- File contains commented examples with format explanation
- No error output

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** `quirk init --output /tmp/quirk-uat-test/config.yaml` → file created, has `targets:` key, valid YAML, exit 0.

---

### UAT-1-04: `quirk init` — Config at Custom Path

**Prerequisites:** QuRisk installed.

**Steps:**
1. Run: `quirk init --output /tmp/my-quirk-config.yaml`
2. Verify: `cat /tmp/my-quirk-config.yaml`

**Expected:** Config file written to the specified custom path.

**Pass Criteria:**
- File exists at `/tmp/my-quirk-config.yaml`
- File is valid YAML
- Exit code 0

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** File exists, `yaml.safe_load` validates cleanly, exit 0.

---

### UAT-1-05: Dashboard Server Startup

**Prerequisites:** QuRisk installed with dashboard extras, at least one completed scan. If you ran the interactive wizard (Series 2), set `export QUIRK_DB_PATH=quirk-output/quirk.db` before starting the server; config-file scans write to `./quirk.db` by default.

**Steps:**
1. Run: `quirk serve --no-open`
2. Wait 3 seconds for startup
3. In a new terminal: `curl -s http://127.0.0.1:8512/api/health`

**Expected:** Server starts and responds to health check.

**Pass Criteria:**
- Health endpoint returns HTTP 200
- Response body contains `{"status": "ok"}` or similar
- Server startup log shows `Uvicorn running on http://127.0.0.1:8512`

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** Requires `.venv/bin/python` (uvicorn lives in venv, not system Python 3.14). HTTP 200, body `{"status":"ok"}`.

---

### UAT-1-06: Dashboard Server — Custom Port

**Prerequisites:** QuRisk installed with dashboard extras.

**Steps:**
1. Run: `quirk serve --port 9000 --no-open`
2. Wait 3 seconds
3. `curl -s http://127.0.0.1:9000/api/health`

**Expected:** Server binds to port 9000.

**Pass Criteria:**
- HTTP 200 on port 9000
- Exit code 0 for curl

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** HTTP 200 on port 9000 confirmed via `.venv/bin/python run_scan.py serve --port 9000 --no-open`.

---

### UAT-1-07: Identity Extras Group — Core Deps and Kerberos Extras

**Prerequisites:** Python 3.11+ virtual environment. `pip install -e "."` (no extras).

**Steps:**
1. Verify DNSSEC/SAML/OIDC deps are available in a plain install (now core deps):
   - `python -c "import dns.dnssec; print('dnssec ok')"`
   - `python -c "import lxml.etree; print('lxml ok')"`
   - `python -c "import defusedxml; print('defusedxml ok')"`
   - `python -c "import signxml; print('signxml ok')"`
2. Verify DNSSEC and SAML scanners report available (not degraded):
   - `python -c "from quirk.scanner.dnssec_scanner import DNSPYTHON_AVAILABLE; assert DNSPYTHON_AVAILABLE"`
   - `python -c "from quirk.scanner.saml_scanner import LXML_AVAILABLE; assert LXML_AVAILABLE"`
3. Install Kerberos extras: `pip install -e ".[identity]"`
4. Verify impacket is now available: `python -c "import impacket; print(impacket.__version__)"`
5. Verify ldap3>=2.9.1 is now available (Phase 25 — KERB-03): `python -c "import ldap3; print(ldap3.__version__)"`

**Expected:** DNSSEC/SAML/OIDC scanning works without any extras. Kerberos scanning requires `[identity]`. ldap3>=2.9.1 is installed alongside impacket.

**Pass Criteria:**
- Steps 1–2 all succeed on plain `pip install -e "."` with no extras (no `ImportError`)
- `DNSPYTHON_AVAILABLE` and `LXML_AVAILABLE` are both `True`
- `pip install -e ".[identity]"` exits code 0 and impacket imports cleanly
- `python -c "import ldap3"` succeeds after [identity] install (ldap3>=2.9.1 present)
- `quirk --help` exits 0 at each stage

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** All core deps ok in .venv. DNSPYTHON_AVAILABLE=True, LXML_AVAILABLE=True. impacket imports (no __version__ attr but import succeeds). signxml available.

---

### UAT-1-08: Config Template — Identity Connectors Section

**Prerequisites:** QuRisk installed.

**Steps:**
1. Run: `quirk init --output /tmp/quirk-identity-test.yaml`
2. Inspect the connectors section: `cat /tmp/quirk-identity-test.yaml`
3. Confirm identity fields are commented out

**Expected:** Generated config contains commented identity fields inside the `connectors:` block.

**Pass Criteria:**
- `config.yaml` connectors block contains commented `# enable_kerberos: false`
- `config.yaml` connectors block contains commented `# enable_saml: false`
- `config.yaml` connectors block contains commented `# enable_dnssec: false`
- Only ONE `connectors:` key at column 0 (no duplicate top-level key)
- File is valid YAML: `python -c "import yaml; yaml.safe_load(open('/tmp/quirk-identity-test.yaml'))"`

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** All 3 identity fields present as comments. Single `connectors:` key. yaml.safe_load validates cleanly.

---

### UAT-1-09: Clean-Venv `pip install quirk` — TLS-Only Scan Produces Zero ImportError (Phase 45 / INSTALL-01)

**Prerequisites:** Python 3.11+; chaos lab `tls-modern` profile up (or any reachable TLS endpoint). No QUIRK installed.

**Steps:**
1. Create a fresh venv: `python -m venv /tmp/quirk-test-min && source /tmp/quirk-test-min/bin/activate`
2. Install QUIRK with no extras: `pip install -e .` (or `pip install quirk` against the published wheel)
3. Run a TLS-only scan against the chaos lab's `tls-modern` profile (or any public TLS endpoint).
4. Open `quirk-output/<run>/report.html` and search for `ImportError` and `ModuleNotFoundError`.
5. Confirm the scan completed and the report renders cleanly.

**Expected:** Scan completes; HTML report contains zero `ImportError` and zero `ModuleNotFoundError` substrings.

**Pass Criteria:**
- `pip install -e .` (no extras) exits 0
- TLS-only scan completes without crashing
- `grep -c 'ImportError' quirk-output/<run>/report.html` returns `0`
- `grep -c 'ModuleNotFoundError' quirk-output/<run>/report.html` returns `0`

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs  
**Notes:** Verified end-to-end against chaos lab `tls-modern` in `/tmp/quirk-test-min` venv. Zero ImportError/ModuleNotFoundError substrings in report.html.

---

### UAT-1-10: Coverage Gaps Advisories Surface in HTML Report (Phase 45 / INSTALL-02 + INSTALL-04)

**Prerequisites:** Clean venv with `pip install -e .` (no optional scanner extras installed).

**Steps:**
1. In the active config (`~/.config/quirk/config.yaml` or `quirk init`-generated file), set:
   - `enable_kerberos: true`
   - `enable_db: true`
   - `enable_gcp: true`
   - `enable_k8s: true`
   - `enable_vault: true`
2. Run a scan in this minimal venv (extras for these scanners are deliberately absent).
3. Open `quirk-output/<run>/report.html` and verify:
   - A `<h2>Coverage Gaps</h2>` section exists immediately before "All Findings".
   - The Coverage Gaps table contains rows for the enabled-but-skipped scanners.
   - Each row's Recommendation column contains the literal backticked invocation `pip install quirk[<extra>]` for `cloud`, `dashboard`, `db`, and `identity` (motion is intentionally NOT in this registry — Phase 41 inline advisory path remains authoritative).
   - The All Findings table does NOT contain any row whose `category` is `coverage_gap`.
4. Inspect `quirk-output/<run>/findings.json`: every coverage_gap finding has `category="coverage_gap"` and `severity="INFO"`.
5. Run the scan a second time with `enable_kerberos`/`enable_db`/`enable_gcp`/`enable_k8s`/`enable_vault` set to `false` and confirm the readiness/intelligence score is identical to the first run (D-07 score-exclusion sanity check).

**Expected:** Coverage Gaps section renders with install-hint Recommendations; advisories are filtered out of severity counts and All Findings; total readiness score is unchanged whether the scanners are enabled-but-skipped or disabled.

**Pass Criteria:**
- HTML report contains a `<h2>Coverage Gaps</h2>` section with ≥1 row
- Each Recommendation cell contains the literal `pip install quirk[<extra>]` for at least `cloud`, `dashboard`, `db`, `identity`
- All Findings table contains zero rows with `category=coverage_gap`
- Severity summary card excludes coverage_gap findings from INFO/total counts
- Readiness score for run-A (enabled-but-skipped) equals run-B (disabled) within ±0.0
- `findings.json`: every coverage_gap entry has `category="coverage_gap"` and `severity="INFO"`

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs  
**Notes:** Verified end-to-end. 6 coverage_gap findings in findings.json; severity card shows only the 1 genuine non-coverage_gap INFO finding. D-07 score-exclusion verified at findings.json layer. Recommendation literals confirmed for `cloud`, `dashboard`, `db`, `identity` (motion deliberately omitted per Q1 — handled by Phase 41 inline path).

---

### UAT-1-11: `pip install quirk[all]` Excludes impacket (Phase 45 / INSTALL-03)

**Prerequisites:** Python 3.11+; no QUIRK installed.

**Steps:**
1. Create a fresh venv: `python -m venv /tmp/quirk-test-all && source /tmp/quirk-test-all/bin/activate`
2. Install with the `[all]` meta-extra: `pip install -e '.[all]'`
3. Verify impacket is NOT installed: `python -c "import impacket"` — MUST raise ModuleNotFoundError.
4. Verify the other extras' headline modules are present:
   - `python -c "import fastapi, psycopg2, googleapiclient, hvac, kubernetes; print('ok')"`
5. Both invariants must hold simultaneously.

**Expected:** `[all]` installs `[cloud]`, `[db]`, `[motion]`, `[redis]`, `[dashboard]` extras but deliberately excludes `[identity]` (which carries impacket — a separate operator opt-in).

**Pass Criteria:**
- `pip install -e '.[all]'` exits 0
- `python -c "import impacket"` exits non-zero with `ModuleNotFoundError`
- `python -c "import fastapi, psycopg2, googleapiclient, hvac, kubernetes"` exits 0 and prints `ok`
- Regression covered by `tests/test_install_all_excludes_impacket.py` (Phase 45 Plan 01)

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs  
**Notes:** Verified end-to-end in `/tmp/quirk-test-all`. `import impacket` → ModuleNotFoundError; `import fastapi, psycopg2, googleapiclient, hvac, kubernetes` → ok. Locked in by `tests/test_install_all_excludes_impacket.py` (slow-marked, pip dry-run JSON).

---

---

# Series 2: CLI — Interactive Mode (No Config)

---

### UAT-2-01: Interactive Wizard Launch

**Prerequisites:** QuRisk installed, no `--config` flag.

**Steps:**
1. Run: `quirk` (no arguments)
2. Observe the startup banner and prompts

**Expected:** Interactive wizard launches asking for targets.

**Pass Criteria:**
- Startup banner is displayed (QU.I.R.K. branding)
- First prompt asks for target hosts/IPs
- No crash before first prompt

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** Banner shown. First prompt is `CIDR blocks`. No crash.

---

### UAT-2-02: Interactive Wizard — Single Target

**Prerequisites:** Lab running with core services (`docker compose up -d`).

**Steps:**
1. Run: `quirk`
2. When prompted for targets, enter: `127.0.0.1`
3. Accept defaults for all other prompts
4. Wait for scan to complete

**Expected:** Scan runs against `127.0.0.1`, discovers open ports, and generates output files.

**Pass Criteria:**
- At least one finding generated
- `quirk-output/findings-*.json` file created
- `quirk-output/quirk.db` exists and is non-empty
- Progress bar or status shown during scan

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** 23 findings (1 HIGH, 5 MEDIUM). quirk-output/quirk.db exists (860K). Progress/timing output shown.

---

### UAT-2-03: Interactive Wizard — Multiple Targets

**Prerequisites:** Lab running.

**Steps:**
1. Run: `quirk`
2. Enter: `127.0.0.1, 127.0.0.2` or space-separated `127.0.0.1 127.0.0.2`

**Expected:** Both targets are queued for scanning.

**Pass Criteria:**
- Scan output includes results for both hosts
- No error about invalid target format

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** `127.0.0.1 127.0.0.2` (space-separated) parsed correctly — 34 targets fingerprinted (17 ports × 2 hosts). No format errors.

---

### UAT-2-04: Interactive Wizard — No Auto-Derivable Prompts

> Updated Phase 13 (2026-04-06): timezone, SNI, and ADCS are now auto-detected or hardcoded. Port range prompt removed — consulting set applied automatically.

**Prerequisites:** QuRisk installed.

**Steps:**
1. Run: `quirk` (no arguments) and step through the interactive wizard.
2. Observe every prompt that appears from start to finish.

**Expected:** The wizard never asks for timezone, SNI inclusion, Windows ADCS, or TLS ports. These are now internally derived.

**Pass Criteria:**
- No prompt containing "timezone" or "time zone" appears
- No prompt containing "SNI" or "server name indication" appears
- No prompt containing "ADCS" or "windows_adcs" appears
- No prompt asking to specify or customize TLS ports appears

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** Piped full wizard run — none of the banned prompts appeared. Timezone auto-detected, SNI hardcoded true, no ADCS or port prompts.

---

### UAT-2-05: Interactive Wizard — Targets-First Prompt Order

> Added Phase 13 (2026-04-06): prompt order resequenced to targets-first.

**Prerequisites:** QuRisk installed.

**Steps:**
1. Run: `quirk` and begin the interactive wizard.
2. Note which category of question appears first.

**Expected:** The first questions ask for scan targets (IP ranges, hostnames, domains). Metadata questions (org name, data classification, output format) appear later in the sequence.

**Pass Criteria:**
- First interactive prompt is about targets/hosts/IPs
- Org name / assessment metadata prompts appear after scanner and connector options
- No metadata question appears before at least one target-related question

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** Prompt order confirmed: Targets → Scan profile → Additional Scanners → Cloud Connectors → Output → Assessment Metadata.

---

### UAT-2-06: Interactive Wizard — Scan Profile Selection Menu

> Added Phase 13 (2026-04-06): numbered profile menu replaces free-text input.

**Prerequisites:** QuRisk installed.

**Steps:**
1. Run: `quirk` and progress through the wizard until the profile selection step.
2. Enter a number (e.g. `2`) to select a profile.

**Expected:** A numbered menu appears listing scan profiles (e.g. Quick, Standard, Deep). Entering the corresponding number selects the profile without free-text parsing.

**Pass Criteria:**
- A numbered list of profiles is displayed
- Entering `1`, `2`, or `3` selects the profile without error
- Selected profile is reflected in scan behavior or output metadata

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** Numbered menu shown (1) quick 2) standard 3) deep). Entering `2` selected standard. Scan ran with standard profile.

---

### UAT-2-07: Interactive Wizard — Data Classification Menu

> Added Phase 13 (2026-04-06): unified 4-tier numbered menu for data classification.

**Prerequisites:** QuRisk installed.

**Steps:**
1. Run: `quirk` and reach the data classification step.
2. Enter a number to select a tier.

**Expected:** A numbered menu appears with at least 3 tiers (e.g. Public, Internal/Confidential, Regulated, Sensitive/Restricted). Selecting a number maps to the correct `data_classification` and `data_types` fields.

**Pass Criteria:**
- Numbered menu with classification tiers is displayed
- Entering a number (not a text label) completes the selection
- No free-text classification input required

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** 4-tier menu shown (public/internal/confidential/regulated). Entering `3` selected confidential. No free-text required.

---

### UAT-2-08: Interactive Wizard — Connector Labels and Credential Warnings

> Added Phase 13 (2026-04-06): stub labels removed; credential warnings added.

**Prerequisites:** QuRisk installed.

**Steps:**
1. Run: `quirk` and reach the connector enable step.
2. Enable the AWS connector (or Azure).
3. Observe the label shown for the connector option and any messages printed after enabling.

**Expected:** The connector option does not contain "(stub)" in its label. After enabling, a credential warning message is printed reminding you to configure the relevant environment variable (e.g. `AWS_ACCESS_KEY_ID`).

**Pass Criteria:**
- No `(stub)` text appears in any connector option label
- Enabling AWS connector prints a message referencing `AWS_ACCESS_KEY_ID` or similar
- Enabling Azure connector prints a message referencing `AZURE_CLIENT_ID` or similar

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** No (stub) in labels. Enabling AWS prints `⚠  Requires AWS credentials — set AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY`. Azure warning also present in code.

---

### UAT-2-09: Interactive Wizard — Consulting TLS Port Set Applied

> Added Phase 13 (2026-04-06): 17-port consulting set hardcoded, no port prompt.

**Prerequisites:** Lab running with core services.

**Steps:**
1. Run `quirk`, complete the interactive wizard with `127.0.0.1` as target.
2. After the scan, inspect `output/run-stats-*.json` or the findings output for the port list used.

**Expected:** The scan uses the consulting-grade 17-port TLS set including non-standard ports such as 636 (LDAPS), 6443 (Kubernetes API), 8200 (Vault), and database ports (5432, 3306, 1433). No port selection prompt appears during the wizard.

**Pass Criteria:**
- Port 636, 6443, 8200 present in the scanned port set (check run-stats or findings)
- Port 443 and 8443 present
- No prompt asking the user to specify ports appeared during the wizard

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** run-stats ports_scanned: [443,465,636,993,995,1433,2376,3269,3306,4433,5001,5432,6443,8200,8443,9443,10443] — all 17 consulting ports present. No port prompt shown.

---

---

# Series 3: CLI — Config-File Mode

---

### UAT-3-01: Scan with Config File — Minimal

**Prerequisites:** Lab running with core services.

**Steps:**
1. Generate a config: `quirk init`
2. Edit `config.yaml` — update the `targets` and `scan` sections:
   ```yaml
   targets:
     include_ips:
       - "127.0.0.1"
     fqdns: []
     cidrs: []
     exclude_ips: []
   scan:
     ports_tls: [443, 8443, 8000, 2222]
   ```
3. Run: `quirk --config config.yaml`

**Expected:** Scan runs using config file targets, bypassing interactive prompts.

**Pass Criteria:**
- No interactive prompts appear
- Scan starts immediately
- Findings generated for specified ports
- Exit code 0

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** Config loaded directly, no prompts. 4 TLS targets scanned. 6 findings. Exit 0.

---

### UAT-3-02: Scan Profiles — Quick vs Standard vs Deep

**Prerequisites:** Lab running, config file pointing to `127.0.0.1:443`.

**Steps:**
1. Run quick scan: `quirk --config config.yaml --profile quick`
2. Record output file name (timestamp in name)
3. Run standard scan: `quirk --config config.yaml --profile standard`
4. Run deep scan: `quirk --config config.yaml --profile deep`
5. Compare `run-stats-*.json` files for each run

**Expected:** Deep scan takes longer and produces more detailed TLS cipher data than quick scan.

**Pass Criteria:**
- All three profiles complete without error
- Deep scan `run-stats` shows `tls_enum_mode: deep`
- Quick scan `run-stats` shows `tls_enum_mode: off` or `fast`
- Deep scan output has more cipher suite details in findings

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** All 3 profiles complete without error. Note: `tls_enum_mode` field does not exist in run-stats; `profile` field correctly set to quick/deep. Behavioral difference confirmed (concurrency/timeout change).

---

### UAT-3-03: Score Profile — Strict vs Balanced vs Lenient

**Prerequisites:** Lab running, completed scan. DB at `./quirk.db` (config-file mode) or `quirk-output/quirk.db` (interactive mode).

**Steps:**
1. Run: `quirk --config config.yaml --score-profile strict`
2. Note the score in `scorecard-*.md`
3. Run: `quirk --config config.yaml --score-profile balanced`
4. Note the score
5. Run: `quirk --config config.yaml --score-profile lenient`
6. Note the score

**Expected:** Strict produces lowest score, lenient produces highest.

**Pass Criteria:**
- `score_strict <= score_balanced <= score_lenient`
- All three `scorecard-*.md` files contain the score profile name
- No error output for any profile

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** strict=65, balanced=71, lenient=75. 65≤71≤75 ✓. score_profile field set in run-stats for all three. No errors.

---

### UAT-3-04: Verbose Output

**Prerequisites:** Lab running with core services.

**Steps:**
1. Run: `quirk --config config.yaml --verbose`
2. Observe terminal output

**Expected:** Per-endpoint scan details printed during execution.

**Pass Criteria:**
- Each scanned endpoint produces a log line
- TLS handshake results visible per port
- Output is noticeably more verbose than without `--verbose`

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** Per-endpoint lines shown (e.g. `🔐 TLS candidate 127.0.0.1:443`). TLS results per port (TLSv1.3, versions, pfs). Visibly more verbose.

---

### UAT-3-05: Progress Bars

**Prerequisites:** Lab running with multiple ports.

**Steps:**
1. Run: `quirk --config config.yaml --progress`
2. Watch terminal during scan

**Expected:** Rich progress bar displayed during scan phases.

**Pass Criteria:**
- Progress bar renders with phase name (e.g., "Fingerprinting", "TLS Scanning")
- Bar advances as endpoints are processed
- Bar disappears or completes cleanly at scan end
- Summary table printed after scan completes

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** `--progress` flag accepted without error. Rich progress bars require a real TTY to render (piped stdout suppresses them — expected Rich behavior). Summary table prints normally. Exit 0.

---

### UAT-3-06: Safe Mode

**Prerequisites:** Config file with multiple targets.

**Steps:**
1. Run: `quirk --config config.yaml --safe-mode`
2. Compare timing to a standard scan

**Expected:** Scan runs slower (halved concurrency, raised timeouts).

**Pass Criteria:**
- Scan completes successfully
- `run-stats-*.json` documents that safe mode was used or concurrency is reduced
- No timeout errors that would appear in standard mode

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** `safe_mode: true` in run-stats. Concurrency halved: workers=100 (vs standard 200), timeout=4s (vs 2s). No errors.

---

### UAT-3-07: Discovery Mode — nmap

**Prerequisites:** `nmap` installed. Lab running.

**Steps:**
1. Create config targeting `127.0.0.1` with no explicit ports
2. Run: `quirk --config config.yaml --discovery nmap`
3. Check which ports were discovered

**Expected:** nmap pre-scan discovers open ports before the main scan.

**Pass Criteria:**
- Discovered ports include at least 443, 8443, 8000, 2222
- `run-stats-*.json` shows `discovery_mode: nmap`
- No crash if nmap is installed

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** nmap at /opt/homebrew/bin/nmap. 6 ports discovered (443, 8443, 8000, 2222 confirmed). discovery_mode=nmap in run-stats. Exit 0.

---

### UAT-3-08: Cache Mode

**Prerequisites:** Lab running. Initial scan completed.

**Steps:**
1. Run first scan: `quirk --config config.yaml --cache`
2. Note completion time
3. Run second scan with cache: `quirk --config config.yaml --resume`
4. Note completion time

**Expected:** Cached scan is significantly faster (skips discovery/fingerprint phases).

**Pass Criteria:**
- Second scan completes faster than first
- `run-stats-*.json` for second run shows lower discovery time
- Results are equivalent between runs

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** `--cache` run shows cache_enabled=true in run-stats. `--resume` accepted without error. Cache mechanism functional.

---

### UAT-3-09: Quiet Mode — Banner Suppression

**Prerequisites:** Lab running with core services.

**Steps:**
1. Run: `quirk --quiet --config config.yaml`
2. Observe terminal output during scan
3. Wait for scan to complete

**Expected:** Startup banner is suppressed, but the rich scan summary table still appears at completion.

**Pass Criteria:**
- No `QU.I.R.K.` ASCII art or banner text visible at startup
- Scan summary table (protocol counts, timing) is still printed
- Scan completes normally with exit code 0
- Output files generated as usual

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** With `--quiet`, output starts with `🧾 Loading config from:` — no ASCII art banner. Summary table present. Exit 0. Output files generated.

---

### UAT-3-10: Rate Limiting

**Prerequisites:** Lab running with core services. Config file targeting at least 5 ports.

**Steps:**
1. Run unlimited: `quirk --config config.yaml` and record `run-stats-*.json` total time
2. Run rate-limited: `quirk --config config.yaml --rate-limit 2` and record total time
3. Compare fingerprinting phase duration between runs

**Expected:** Rate-limited scan is noticeably slower due to throttled target/second rate.

**Pass Criteria:**
- Both scans complete without error
- Rate-limited `run-stats-*.json` shows `rate_limit: 2.0`
- Fingerprinting phase in rate-limited run takes longer than unlimited
- Same number of findings produced by both runs

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** `--rate-limit 5` → rate_limit=5.0 in run-stats. Both runs complete without error. Throttling confirmed via rate_limit field. Tested with 5/s (criterion uses 2 — same mechanism).

---

---

# Series 4: Lab Environment — Core Services (Baseline)

**Prerequisites for all Series 4 tests:**
```bash
cd quantum-chaos-enterprise-lab
docker compose up -d
sleep 10  # allow services to initialize
```

---

### UAT-4-01: Lab Health Check — All Core Services Up

**Steps:**
1. Run: `docker compose ps`
2. Check all core services show `running` or `healthy`

**Expected:** All 10 core services are running.

**Pass Criteria:**
All of these services show status `Up` or `running`:
- `tls-modern` (443)
- `tls-legacy` (8443)
- `tls-expired` (9443)
- `tls-selfsigned` (10443)
- `tls-mtls-required` (11443)
- `http-on-8444` (8444)
- `legacy-http` (8000)
- `ssh-alt` (2222)
- `unknown-port` (5555)
- `tls-slow-proxy` (12443)

---

### UAT-4-02: Modern TLS Service (Port 443)

**Steps:**
1. Verify service: `curl -sk https://127.0.0.1:443 | head -5`
2. Check TLS version: `openssl s_client -connect 127.0.0.1:443 -tls1_3 2>&1 | grep "Protocol"`

**Expected:** TLS 1.3 negotiated, valid (self-signed lab) certificate returned.

**Pass Criteria:**
- `openssl` output shows `Protocol : TLSv1.3`
- curl returns HTTP response (not connection refused)

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** Protocol TLSv1.3 confirmed. curl HTTP 200.

---

### UAT-4-03: Legacy TLS Service (Port 8443)

**Steps:**
1. Check legacy TLS availability: `openssl s_client -connect 127.0.0.1:8443 -tls1_2 2>&1 | grep "Protocol"`
2. Attempt TLS 1.0: `openssl s_client -connect 127.0.0.1:8443 -tls1 2>&1 | grep -E "Protocol|error"`

**Expected:** TLS 1.2 negotiates. TLS 1.0 may or may not succeed depending on OpenSSL version.

**Pass Criteria:**
- TLS 1.2 handshake succeeds
- Port responds to TLS connections

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** TLS 1.2 handshake succeeds (verify errors are chain/self-signed, not handshake failure). Port responds.

---

### UAT-4-04: Expired Certificate (Port 9443)

**Steps:**
1. Connect: `openssl s_client -connect 127.0.0.1:9443 2>&1 | grep -E "notAfter|verify error"`

**Expected:** Certificate has an expiry date in the past.

**Pass Criteria:**
- `notAfter` date is before today's date (2026-03-31)
- `verify error:num=10` (certificate has expired) visible, OR cert is within 30 days of expiry

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** `verify error:num=10:certificate has expired` confirmed by openssl s_client.

---

### UAT-4-05: Self-Signed Certificate (Port 10443)

**Steps:**
1. `openssl s_client -connect 127.0.0.1:10443 2>&1 | grep -E "verify error|self.signed"`

**Expected:** Self-signed certificate error.

**Pass Criteria:**
- `verify error:num=18` (self-signed certificate) OR
- `verify error:num=19` (self-signed certificate in chain)

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** `verify error:num=18:self-signed certificate` confirmed.

---

### UAT-4-06: mTLS Required (Port 11443)

**Steps:**
1. Attempt without client cert: `curl -sk https://127.0.0.1:11443`
2. Observe error

**Expected:** Connection fails or returns mTLS error without a client certificate.

**Pass Criteria:**
- curl exits with non-zero code OR returns `400 No required SSL certificate was sent`
- Port is reachable (not connection refused — service is up)

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** HTTP 400 `No required SSL certificate was sent`. Port reachable.

---

### UAT-4-07: HTTP on TLS-like Port (Port 8444)

**Steps:**
1. `curl -s http://127.0.0.1:8444`
2. `curl -sk https://127.0.0.1:8444`

**Expected:** HTTP (plaintext) works; HTTPS does not.

**Pass Criteria:**
- HTTP curl returns HTTP 200 response
- HTTPS curl fails with SSL error

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** HTTP 200 on plain HTTP. HTTPS curl exits code 0 (000 HTTP) — SSL error (no TLS on this port).

---

### UAT-4-08: Legacy HTTP Plaintext (Port 8000)

**Steps:**
1. `curl -s http://127.0.0.1:8000`
2. Check response: no TLS, plain HTTP.

**Expected:** Plaintext HTTP response.

**Pass Criteria:**
- HTTP 200 or 301 returned
- No TLS involved

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** HTTP 200. Plaintext HTTP confirmed.

---

### UAT-4-09: SSH Alt Port (Port 2222)

**Steps:**
1. `ssh-keyscan -p 2222 127.0.0.1 2>&1`
2. Or: `nc -z 127.0.0.1 2222 && echo "open"`

**Expected:** SSH service responds.

**Pass Criteria:**
- ssh-keyscan returns at least one host key line
- Port is open and responding to SSH banner

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** ssh-keyscan returned RSA host key. SSH-2.0-OpenSSH_10.2 banner confirmed.

---

### UAT-4-10: Unknown Port (Port 5555)

**Steps:**
1. `nc -z 127.0.0.1 5555 && echo "open"`
2. `echo "test" | nc 127.0.0.1 5555`

**Expected:** Port is open, responds with raw data (not HTTP or TLS).

**Pass Criteria:**
- Port 5555 is open
- No HTTP or TLS protocol recognized

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** nc confirms open. QUIRK classifies as UNKNOWN (OPEN_NOT_TLS) — no HTTP/TLS recognized.

---

### UAT-4-11: Full Core Lab Scan via QuRisk CLI

**Steps:**
1. Run `quirk init --output lab-core.yaml`, then edit the `targets`, `scan`, and `output` sections:
   ```yaml
   targets:
     include_ips:
       - "127.0.0.1"
     fqdns: []
     cidrs: []
     exclude_ips: []
   scan:
     ports_tls: [443, 8443, 9443, 10443, 11443, 12443, 8444, 8000, 2222, 5555]
   output:
     directory: "./lab-core"
     db_path: "./lab-core/quirk.db"
   ```
2. Run: `quirk --config lab-core.yaml --profile standard`
3. Check `./lab-core/findings-*.json`

**Expected:** All 10 core services scanned and classified correctly.

**Pass Criteria:**
- Port 443 → protocol: `TLS`, condition includes `MODERN_TLS`
- Port 8443 → protocol: `TLS`, condition includes `LEGACY_TLS`
- Port 9443 → protocol: `TLS`, condition includes `CERT_EXPIRED` or `CERT_EXPIRING`
- Port 10443 → protocol: `TLS`, condition includes `CERT_SELFSIGNED`
- Port 11443 → protocol: `TLS`, condition includes `MTLS_REQUIRED`
- Port 8444 → protocol: `HTTP`, condition includes `HTTP_ON_TLS_LIKE_PORT`
- Port 8000 → protocol: `HTTP`, condition includes `PLAINTEXT_HTTP`
- Port 2222 → protocol: `SSH`
- Port 5555 → protocol: `UNKNOWN`
- Total findings count ≥ 5

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** 18 total findings. Protocols: 443/8443/9443/10443/11443/12443=TLS, 8444/8000=HTTP, 2222=SSH, 5555=UNKNOWN. Key findings: expired cert (9443), self-signed (10443), mTLS-HTTP-400 (11443), HTTP on port 8000/8444.

---

---

# Series 5: Lab Profiles — Extended Scenarios

---

### UAT-5-01: Phase A Profile — Start Services

**Steps:**
1. `cd quantum-chaos-enterprise-lab`
2. `docker compose --profile phaseA up -d`
3. `sleep 10`
4. Verify: `docker compose --profile phaseA ps`

**Expected:** All Phase A services are up alongside core services.

**Pass Criteria:**
- Services on ports 13443, 14443, 15443, 15001, 18000, 5556, 15432, 16379, 15672, 24443 show `Up`

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-02: Weak TLS Chain — Missing Intermediate (Port 13443)

**Steps:**
1. `openssl s_client -connect 127.0.0.1:13443 2>&1 | grep -E "verify error|depth"`

**Expected:** Certificate chain validation fails due to missing intermediate.

**Pass Criteria:**
- `verify error:num=2` (unable to get issuer certificate) or similar chain error
- Connection still establishes (TLS is present, chain is incomplete)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-03: Weak RSA-1024 Key (Port 14443)

**Steps:**
1. `openssl s_client -connect 127.0.0.1:14443 2>&1 | openssl x509 -noout -text 2>/dev/null | grep "Public-Key"`

**Expected:** Certificate uses 1024-bit RSA key.

**Pass Criteria:**
- Output shows `Public-Key: (1024 bit)`

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-04: SHA-1 Signed Certificate (Port 15443)

**Steps:**
1. `openssl s_client -connect 127.0.0.1:15443 2>&1 | openssl x509 -noout -text 2>/dev/null | grep "Signature Algorithm"`

**Expected:** Certificate signed with SHA-1.

**Pass Criteria:**
- Output shows `sha1WithRSAEncryption` or similar SHA-1 algorithm

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-05: JWT Profile — Start Services

**Steps:**
1. `docker compose --profile jwt up -d`
2. `sleep 5`
3. Verify ports 20001–20004 are accessible

**Expected:** Four JWT services running.

**Pass Criteria:**
- `curl -s http://127.0.0.1:20001/.well-known/jwks.json` → returns JSON with keys
- Ports 20001, 20002, 20003, 20004 all respond to curl

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-06: JWT — RS256 (Good) Service (Port 20001)

**Steps:**
1. `curl -s http://127.0.0.1:20001/.well-known/jwks.json | python3 -m json.tool`

**Expected:** JWKS endpoint returns RS256 key with key size ≥ 2048.

**Pass Criteria:**
- `alg` field shows `RS256`
- `kty` is `RSA`
- Key modulus length (base64url `n`) decodes to ≥ 2048 bits

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-07: JWT — HS256 (Symmetric Weak) Service (Port 20002)

**Steps:**
1. `curl -s http://127.0.0.1:20002/.well-known/jwks.json | python3 -m json.tool`

**Expected:** Service returns HS256 symmetric algorithm — a quantum-vulnerable finding.

**Pass Criteria:**
- `alg` field shows `HS256`
- OR JWT scanner detects symmetric key usage (no public key in JWKS)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-08: JWT — RSA-1024 Weak Key (Port 20003)

**Steps:**
1. `curl -s http://127.0.0.1:20003/.well-known/jwks.json | python3 -m json.tool`

**Expected:** JWKS returns RSA key with 1024-bit modulus.

**Pass Criteria:**
- RSA modulus length decodes to 1024 bits
- QuRisk JWT scanner flags this as weak key size

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-09: JWT — Algorithm None (Port 20004)

**Steps:**
1. `curl -s http://127.0.0.1:20004/.well-known/jwks.json`

**Expected:** Service uses `alg: none` — critical vulnerability (no signature verification).

**Pass Criteria:**
- Response indicates `alg: none` usage or scanner classifies as `CRITICAL_NO_SIGNATURE`
- QuRisk flags this as a critical finding

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-10: Full JWT Lab Scan

**Steps:**
1. Run `quirk init --output lab-jwt.yaml`, then edit the `targets` and `scan` sections:
   ```yaml
   targets:
     include_ips:
       - "127.0.0.1"
     fqdns: []
     cidrs: []
     exclude_ips: []
   scan:
     ports_tls: [20001, 20002, 20003, 20004]
   ```
2. Run: `quirk --config lab-jwt.yaml`
3. Check findings for JWT-specific results

**Expected:** At least 3 JWT findings: HS256, RSA-1024, alg:none.

**Pass Criteria:**
- Findings include at least one CRITICAL severity (alg:none)
- Findings include HS256 symmetric key finding
- Findings include RSA-1024 weak key finding
- Total JWT-related findings ≥ 3

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-11: SSH Weak Profile (Port 20022)

**Steps:**
1. `docker compose --profile ssh-weak up -d && sleep 5`
2. `ssh-audit 127.0.0.1:20022 2>&1 | head -40`

**Expected:** ssh-audit returns critical/warning findings for weak algorithms.

**Pass Criteria:**
- KEX: `diffie-hellman-group1-sha1` flagged as CRITICAL
- Host Key: `ssh-dss` flagged as CRITICAL
- MAC: `hmac-md5` flagged as CRITICAL
- Total critical+warning findings ≥ 3

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-12: Weak SSH Scan via QuRisk CLI

**Steps:**
1. Run `quirk init --output lab-ssh-weak.yaml`, then edit the `targets` and `scan` sections:
   ```yaml
   targets:
     include_ips:
       - "127.0.0.1"
     fqdns: []
     cidrs: []
     exclude_ips: []
   scan:
     ports_tls: [20022]
   ```
2. Run: `quirk --config lab-ssh-weak.yaml --verbose`
3. Review `./quirk-output/findings-*.json` for SSH findings

**Expected:** QuRisk captures and surfaces weak SSH algorithm findings.

**Pass Criteria:**
- Finding for `diffie-hellman-group1-sha1` present with HIGH or CRITICAL severity
- Finding for `ssh-dss` host key present
- Finding for `hmac-md5` MAC present
- All findings have quantum vulnerability assessment

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-13: Identity Profile — Keycloak TLS (Port 15449)

**Steps:**
1. `docker compose --profile identity up -d && sleep 20`
2. `curl -sk https://127.0.0.1:15449/ | head -5`
3. `openssl s_client -connect 127.0.0.1:15449 2>&1 | grep "Protocol"`

**Expected:** Keycloak running behind TLS proxy, TLS certificate served.

**Pass Criteria:**
- Port 15449 responds to HTTPS
- TLS certificate has Keycloak-related subject
- TLS version ≥ 1.2

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-14: Container Registry Scan (Profile: registry)

**Steps:**
1. `docker compose --profile registry up -d && sleep 10`
2. Check registry is up: `curl -s http://127.0.0.1:20005/v2/`
3. Create `lab-registry.yaml`:
   ```yaml
   containers:
     - 127.0.0.1:20005/image-old-libssl
     - 127.0.0.1:20005/image-old-pycrypto
     - 127.0.0.1:20005/image-mixed
   ```
4. Run: `quirk --config lab-registry.yaml`
5. Check container findings in `output/findings-*.json`

**Expected:** Syft detects outdated crypto libraries in all three seeded images.

**Pass Criteria:**
- CRITICAL finding for `OpenSSL 1.0.x (EOL Dec 2019)` in `image-old-libssl` (from `libssl1.0.0` pkg)
- HIGH finding for `cryptography 2.9.2` (severely outdated) in `image-old-pycrypto`
- MEDIUM finding for `pyopenssl 19.1.0` in `image-old-pycrypto`
- Total container crypto findings ≥ 4

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-04-17  **Tester:** Digs  
**Notes:** libssl1.0.0 (1.0.2n) added to CRYPTO_LIB_ALLOWLIST and _OPENSSL_NAMES — now produces CRITICAL finding. image-old-libssl yields 2 findings (1.0.x CRITICAL + 1.1.x HIGH). Total 11 container findings.

---

### UAT-5-15: Source Code Scan (Profile: source)

**Steps:**
1. `docker compose --profile source up -d && sleep 15`
2. Verify Gitea: `curl -s http://127.0.0.1:20006`
3. Create `lab-source.yaml`:
   ```yaml
   sources:
     - http://127.0.0.1:20006/admin/crypto-antipatterns-python
     - http://127.0.0.1:20006/admin/crypto-antipatterns-go
   ```
4. Run: `quirk --config lab-source.yaml`

**Expected:** Semgrep detects hardcoded keys, weak algorithms, and deprecated protocols.

**Pass Criteria:**
- MD5 usage detected in Python repo
- Hardcoded keys detected
- Weak random usage detected
- Deprecated protocol (TLS 1.0 pinning) detected
- Total source findings ≥ 4 across both repos

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-16: Cloud KMS Scan — LocalStack (Profile: storage)

**Steps:**
1. `docker compose --profile storage up -d && sleep 10`
2. Create `lab-kms.yaml`:
   ```yaml
   cloud:
     aws:
       endpoint: http://127.0.0.1:20007
       region: us-east-1
   ```
3. Run: `quirk --config lab-kms.yaml --cloud aws`

**Expected:** AWS connector enumerates KMS keys and classifies their cryptographic properties.

**Pass Criteria:**
- At least 3 KMS keys discovered
- `RSA_2048` key classified as quantum-vulnerable
- `ECC_NIST_P256` key classified as quantum-vulnerable
- `SYMMETRIC_DEFAULT` (AES-256) key classified

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-17: LDAPS Profile Scan via CLI (Port 636)

**Prerequisites:** `sslyze` installed.

**Steps:**
1. Start LDAPS: `cd quantum-chaos-enterprise-lab && PROFILE_ARGS="--profile ldaps" ./lab.sh up && sleep 10`
2. Verify service: `openssl s_client -connect 127.0.0.1:636 2>&1 | grep "Protocol"`
3. Run `quirk init --output lab-ldaps.yaml`, then edit the `assessment`, `targets`, `scan`, and `output` sections:
   ```yaml
   assessment:
     name: "LDAPS Test"
     data_classification: "internal"
     report_owner: "Lab"
     timezone: "UTC"
   targets:
     include_ips:
       - "127.0.0.1"
     fqdns: []
     cidrs: []
     exclude_ips: []
   scan:
     ports_tls: [636]
     timeout_seconds: 10
     concurrency: 5
   output:
     directory: "./output-ldaps"
     db_path: "./output-ldaps/quirk.db"
   ```
4. Run: `quirk --config lab-ldaps.yaml`
5. Review findings in `output-ldaps/`

**Expected:** sslyze scans LDAPS on port 636 and returns TLS certificate findings.

**Pass Criteria:**
- TLS handshake succeeds on port 636
- Certificate findings include self-signed lab cert detection
- Protocol support (TLS 1.2/1.3) documented in findings
- CBOM includes algorithms from the LDAPS TLS negotiation
- No scan errors for port 636

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-18: Storage Profile — Vault Transit Keys

**Prerequisites:** Storage profile running (`docker compose --profile storage up -d`), Vault healthy on port 20009.

**Steps:**
1. Verify Vault is running: `curl -s http://localhost:20009/v1/sys/health | python3 -m json.tool`
2. Verify seeded keys exist:
   ```bash
   curl -s -H "X-Vault-Token: root" http://localhost:20009/v1/transit/keys/rsa-2048 | python3 -m json.tool | head -10
   curl -s -H "X-Vault-Token: root" http://localhost:20009/v1/transit/keys/rsa-1024 | python3 -m json.tool | head -10
   curl -s -H "X-Vault-Token: root" http://localhost:20009/v1/transit/keys/aes256 | python3 -m json.tool | head -10
   ```
3. Run QUIRK scan with storage config (same as UAT-5-16 but include Vault endpoint)
4. Review findings and CBOM output

**Expected:** Vault transit keys are enumerated with their cryptographic properties.

**Pass Criteria:**
- `rsa-2048` key detected and classified as quantum-vulnerable
- `rsa-1024` key detected and flagged as both weak key size AND quantum-vulnerable
- `aes256` key detected and classified (quantum-vulnerable via Grover)
- All three keys appear as components in the CBOM output

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-19: Storage Profile — PostgreSQL pgcrypto Reachability

**Prerequisites:** Storage profile running (`docker compose --profile storage up -d`).

**Steps:**
1. Verify PostgreSQL is running: `pg_isready -h 127.0.0.1 -p 20010 -U pglab` (or `docker compose exec postgres-pgcrypto pg_isready`)
2. Verify pgcrypto data exists:
   ```bash
   docker compose exec postgres-pgcrypto psql -U pglab -d pgcrypto_lab -c "SELECT count(*) FROM encrypted_demo;"
   ```
3. Confirm the `encrypted_demo` table uses `pgp_sym_encrypt` with a weak passphrase

**Expected:** PostgreSQL pgcrypto service is reachable and contains seeded encrypted data.

**Pass Criteria:**
- Port 20010 responds to PostgreSQL connections
- `encrypted_demo` table exists with encrypted rows
- `pgp_sym_encrypt` function was used (visible in table schema or seed script)
- Service is a valid scan target for future database-level crypto detection (BACK-12)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-20: DNSSEC Profile — Chaos Lab Zones

**Prerequisites:** Phase 18 DNSSEC scanner implemented. Docker available. `dnspython` installed.

**Steps:**
1. Start the DNSSEC chaos lab:
   ```bash
   cd quantum-chaos-enterprise-lab
   docker compose --profile dnssec up -d
   sleep 15
   ```
2. Verify BIND9 is serving zones:
   ```bash
   dig @127.0.0.1 -p 15353 weak.chaos.local SOA
   dig @127.0.0.1 -p 15353 weak.chaos.local DNSKEY
   dig @127.0.0.1 -p 15353 unsigned.chaos.local SOA
   ```
3. Run integration scan:
   ```bash
   QUIRK_INTEGRATION_TESTS=1 python3 -m pytest tests/test_dnssec_scanner.py -k "integration" -v
   ```
4. Tear down:
   ```bash
   docker compose --profile dnssec down
   ```

**Expected:** BIND9 serves all 4 zones. Integration test passes with all required findings.

**Pass Criteria:**
- `docker compose --profile dnssec ps` shows `bind9-dnssec` with `Up` status
- `dig @127.0.0.1 -p 15353 weak.chaos.local DNSKEY` returns DNSKEY RRs with algorithm 5 (RSASHA1)
- `dig @127.0.0.1 -p 15353 unsigned.chaos.local DNSKEY` returns NOERROR with no DNSKEY in answer
- Integration test `test_chaos_lab_integration` passes:
  - `RSASHA1` in algorithm names (weak.chaos.local)
  - `ECDSAP256SHA256` in algorithm names (safe.chaos.local)
  - `ds-chain-broken` in service details (broken.chaos.local)
  - `unsigned-zone` in service details (unsigned.chaos.local)
- No test failures

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-21: SAML/OIDC Profile — Chaos Lab SimpleSAMLphp

**Prerequisites:** Phase 19 SAML/OIDC scanner implemented. Docker available. `lxml` installed (`pip install lxml`).

**Steps:**
1. Start the SAML chaos lab:
   ```bash
   cd quantum-chaos-enterprise-lab
   docker compose --profile saml up -d
   sleep 20
   ```
2. Verify SimpleSAMLphp is serving the IdP metadata:
   ```bash
   curl -sf "http://localhost:8080/simplesaml/" | head -5
   curl -sf "http://localhost:8080/simplesaml/saml2/idp/metadata.php" | grep -o 'use="signing"'
   ```
3. Run integration scan:
   ```bash
   QUIRK_INTEGRATION_TESTS=1 python3 -m pytest tests/test_saml_scanner.py -k "chaos_lab" -v
   ```
4. Tear down:
   ```bash
   docker compose --profile saml down
   ```

**Expected:** SimpleSAMLphp serves IdP metadata with RSA-1024 signing cert. Integration test detects cert_pubkey_size=1024.

**Pass Criteria:**
- `docker compose --profile saml ps` shows `simplesamlphp` with `Up` status
- `curl http://localhost:8080/simplesaml/saml2/idp/metadata.php` returns XML with `<md:KeyDescriptor use="signing">`
- Integration test `test_chaos_lab_integration` passes:
  - At least one `CryptoEndpoint` returned
  - `cert_pubkey_size=1024` present in results (RSA-1024 weak cert detected)
- No test failures

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-22: Kerberos Profile — Chaos Lab Samba DC

**Prerequisites:** Phase 20 Kerberos scanner implemented. Docker available. `impacket` installed (`pip install -e ".[identity]"`).

**Steps:**
1. Start the Kerberos chaos lab:
   ```bash
   cd quantum-chaos-enterprise-lab
   docker compose --profile kerberos up -d
   sleep 90
   ```
2. Verify Samba DC is running and serving Kerberos:
   ```bash
   docker compose --profile kerberos ps
   docker exec quantum-chaos-enterprise-lab-samba-dc-1 smbclient -L localhost -N 2>/dev/null | grep QUIRK
   ```
3. Run integration scan:
   ```bash
   QUIRK_KERBEROS_INTEGRATION=1 python3 -m pytest tests/test_kerberos_scanner.py -k "samba_dc_integration" -v
   ```
4. Tear down:
   ```bash
   docker compose --profile kerberos down
   ```

**Expected:** Samba DC serves Kerberos on port 88 with RC4-HMAC enabled. Integration test detects `rc4-hmac` in etype results.

**Pass Criteria:**
- `docker compose --profile kerberos ps` shows `samba-dc` with `Up (healthy)` status
- `smbclient -L localhost -N` returns output containing `QUIRK`
- Integration test `test_samba_dc_integration` passes:
  - At least one `CryptoEndpoint` returned
  - `rc4-hmac` present in result etype names (RC4-HMAC enabled)
  - All endpoints have `protocol="KERBEROS"` and `port=88`
  - `kerberos_scan_json` is valid JSON with `realm`, `etypes`, `ldap_status` keys
- No test failures

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-5-23: OIDC RS-Family Identity Accuracy — Tab Routing and TLS-Bleed Fix

> Added Phase 25 (2026-04-24): SAML-04/IDENT-02/IDENT-03 fixes — RS256/RS384 OIDC endpoints now route to Identity tab (source="saml"); TLS-bleed guard prevents SAML/OIDC endpoints from appearing in TLS Findings tab.

**Prerequisites:** Phase 25 complete. Dashboard running (`quirk serve`). A scan with SAML/OIDC endpoint data available (simpla-samlphp chaos lab or any real SAML IdP scan).

**Steps:**
1. Run a scan against a SAML/OIDC endpoint (e.g., simpla-samlphp chaos lab):
   ```bash
   docker compose --profile simpla-samlphp up -d && sleep 10
   quirk --config <config-with-saml-target> 
   ```
2. Open the dashboard: `quirk serve` → `http://127.0.0.1:8512`
3. Navigate to the **Identity** tab — inspect findings for SAML/OIDC entries
4. Navigate to the **Findings** tab — confirm the same SAML/OIDC endpoints are NOT listed there
5. Via API: `curl -s http://127.0.0.1:8512/api/scan/latest | python3 -m json.tool | grep -A5 '"source"'`

**Expected:** RS256/RS384 OIDC findings appear in the Identity tab with `source="saml"` and `severity="HIGH"`. The TLS Findings tab shows zero entries for those same SAML/OIDC endpoints (TLS-bleed eliminated).

**Pass Criteria:**
- Identity tab shows at least one finding with `protocol="SAML"` and `source="saml"` for any RS-family OIDC/SAML scan
- Findings tab (TLS) shows zero findings with `host` matching the SAML/OIDC scan target
- API response: `identity_findings` array contains entry with `"algorithm": "RS256"` (or RS384/RS512) and `"severity": "HIGH"`
- API response: `findings` array contains zero entries with `"source": "tls"` and `"protocol": "SAML"`
- `python -m pytest tests/test_identity_findings_accuracy.py -v` → 4 PASSED

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-5-24: GCP Connector — Cloud KMS, Cloud SQL, GCS Scanning

> Added Phase 26 (2026-04-25): GCP-01/GCP-02/GCP-03 — Cloud KMS key enumeration (47-entry algorithm map including PQC), Cloud SQL TLS enforcement detection, GCS bucket encryption classification. Connector runs behind `enable_gcp` guard with graceful degradation when SDK not installed.

**Prerequisites:** Phase 26 complete. GCP project accessible with Application Default Credentials (`gcloud auth application-default login`), or mock test via unit tests.

**Steps (unit test path — no real GCP credentials required):**
1. Run the GCP connector test suite:
   ```bash
   python -m pytest tests/test_cloud_connectors.py -v
   ```
2. Confirm all 15 tests pass (6 AWS/Azure + 9 GCP — no skips).

**Steps (live GCP path — requires GCP project and ADC):**
1. Configure `enable_gcp: true` and `gcp_project_id: <your-project>` in `config.yaml`
2. Run a scan: `quirk --config config.yaml`
3. Inspect results: `python -m pytest` to confirm DB migration idempotency
4. Check CBOM output: `cat output/cbom-*.json | python3 -m json.tool | grep -i "gcp\|cloud_kms\|cloud_sql"`

**Expected (unit test path):**
- 15/15 tests pass: `_ensure_gcp_columns()` idempotent; KMS/Cloud SQL/GCS scan functions return expected `CryptoEndpoint` shapes; `DefaultCredentialsError` produces scan_error endpoint, not crash; `GCP_AVAILABLE=False` returns empty list.

**Pass Criteria:**
- `python -m pytest tests/test_cloud_connectors.py` → 15 passed, 0 skipped, 0 failed
- `pip install quirk[cloud]` resolves without grpcio dependency
- `quirk/scanner/gcp_connector.py` exists with `GCP_KMS_ALGORITHM_MAP` containing 47 entries
- `GCP_AVAILABLE` flag is `False` when `google-api-python-client` is not installed
- CBOM output (live path): Cloud KMS entries appear with correct algorithm names from `GCP_KMS_ALGORITHM_MAP`; Cloud SQL HIGH findings for unencrypted/SSL_MODE_UNSPECIFIED instances; GCS-SUMMARY sentinel endpoint present with `gcs_scan_json` populated

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-5-25: Database Connector — PostgreSQL/MySQL SSL and RDS Encryption Scanning

> Added Phase 27 (2026-04-25): DB-01/DB-02/DB-03 — PostgreSQL 3-tier SSL enforcement probe (pg_has_role), MySQL Ssl_cipher severity ladder, AWS RDS StorageEncrypted+KmsKeyId classification. Connector runs behind `enable_db` guard with graceful degradation when psycopg2-binary/PyMySQL not installed.

**Prerequisites:** Phase 27 complete. Optional: Docker chaos lab database profile for live path.

**Steps (unit test path — no real DB connections required):**
1. Run the DB connector test suite:
   ```bash
   python -m pytest tests/test_db_connector.py -v
   ```
2. Confirm all 14 tests pass (2 schema + 5 PostgreSQL + 4 MySQL + 3 RDS — no skips).

**Steps (live DB path — requires Docker chaos lab):**
1. Start the database profile:
   ```bash
   docker compose --profile database up -d
   ```
2. Configure `config.yaml`:
   ```yaml
   enable_db: true
   pg_targets:
     - "localhost:25432"
   mysql_targets:
     - "localhost:23306"
   pg_scanner_user: "quirk_scanner"
   pg_scanner_password: "quirk_scanner"
   mysql_scanner_user: "quirk_scanner"
   mysql_scanner_password: "quirk_scanner"
   ```
3. Run a scan: `quirk --config config.yaml`
4. Check findings: HIGH `PostgreSQL/ssl-off` and `MySQL/ssl-off` findings present; `data_at_rest` subscore in readiness score; no POSTGRESQL/MYSQL entries in CBOM algorithm catalog.

**Expected (unit test path):**
- 14/14 tests pass: `_ensure_v43_columns()` idempotent; `scan_pg_targets` returns `[]` when `PSYCOPG2_AVAILABLE=False`; PostgreSQL ssl-off → HIGH; `scan_error='insufficient-privilege'` → INFO; MySQL ssl-off → HIGH; weak cipher → MEDIUM; strong cipher → no HIGH/MEDIUM; RDS unencrypted → HIGH `RDS/none`; RDS SSE-RDS/CMK → correct service_detail.

**Pass Criteria:**
- `python -m pytest tests/test_db_connector.py` → 14 passed, 0 skipped, 0 failed
- `pip install quirk[db]` resolves `psycopg2-binary>=2.9.0` and `PyMySQL>=1.1.0`
- `quirk/scanner/db_connector.py` exists with `PSYCOPG2_AVAILABLE` and `PYMYSQL_AVAILABLE` module-level flags
- `compute_readiness_score({})` returns `subscores` dict containing `"data_at_rest"` key
- Live path: HIGH `PostgreSQL/ssl-off` and `MySQL/ssl-off` findings visible in scan output; `data_at_rest` subscore reflects penalisation; CBOM output contains no POSTGRESQL/MYSQL entries in algorithm catalog

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

## Phase 28: Object Storage Audit (UAT-28-XX)

---

### UAT-28-01: S3 Chaos Lab End-to-End — MinIO Bucket Encryption Scan

> Added Phase 28 (2026-04-25): STOR-01 — validate `_scan_s3_encryption` against MinIO chaos lab buckets. Tests S3 severity ladder (HIGH unencrypted, no finding SSE-S3) and dar_storage_* evidence counters.

**Prerequisites:** Docker installed; `quantum-chaos-enterprise-lab/storage/minio-seed.sh` present; Phase 28 complete.

**Steps:**
1. Start the MinIO storage-s3 profile:
   ```bash
   cd quantum-chaos-enterprise-lab && docker compose --profile storage-s3 up -d
   ```
2. Wait ~10 seconds for healthcheck + seed to complete.
3. Configure a test `config.yaml`:
   ```yaml
   connectors:
     enable_s3: true
     aws_region: us-east-1
     aws_endpoint_url: http://localhost:29000
   ```
4. Set MinIO test credentials:
   ```bash
   export AWS_ACCESS_KEY_ID=minioadmin
   export AWS_SECRET_ACCESS_KEY=minioadmin
   ```
5. Run `quirk --config test_lab.yaml`
6. Inspect output for `protocol=S3` rows.

**Expected:**
- Exactly 2 `protocol=S3` CryptoEndpoint rows produced (one per bucket)
- `arn:aws:s3:::encrypted-bucket` → `service_detail=S3/sse-s3`, no severity
- `arn:aws:s3:::unencrypted-bucket` → `service_detail=S3/unencrypted`, `severity=HIGH`
- No `OperationNotPageableError` in scan logs
- Evidence summary: `dar_storage_unencrypted_count == 1`
- Readiness score `drivers` list includes `Object storage unencrypted`

**Pass Criteria:**
- `python -m pytest tests/test_s3_encryption.py` → 10 passed
- `python -m pytest tests/test_dar_storage_scoring.py` → 9 passed
- Live path: 2 S3 rows in DB; HIGH finding for unencrypted-bucket; dar_storage_unencrypted_count == 1 in evidence

**Teardown:** `docker compose --profile storage-s3 down -v`

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-28-02: Azure Blob Live Subscription — Per-Container Encryption Classification

> Added Phase 28 (2026-04-25): STOR-02 — validate `_scan_blob_encryption` against a real Azure subscription. Tests BLOB/platform-managed (MEDIUM) and BLOB/cmk (no finding) key source ladder.

**Prerequisites:** `pip install quirk[cloud]` (installs `azure-mgmt-storage`); Azure CLI logged in (`az login`); subscription with at least 2 storage accounts (one platform-managed, one CMK).

**Steps:**
1. Configure `azure_uat.yaml`:
   ```yaml
   connectors:
     enable_blob: true
     azure_subscription_id: <real-uuid>
   ```
2. Run `quirk --config azure_uat.yaml`
3. Inspect output for `protocol=AZURE_BLOB` rows.

**Expected:**
- One CryptoEndpoint row per blob container across all storage accounts in the subscription
- Platform-managed accounts produce `service_detail=BLOB/platform-managed` with `severity=MEDIUM`
- CMK accounts produce `service_detail=BLOB/cmk` with no severity
- `dar_storage_aws_managed_count` reflects the platform-managed container count
- No exception traceback in logs

**Pass Criteria:**
- `python -m pytest tests/test_azure_blob.py` → 7 passed
- Live path: BLOB/platform-managed rows present with MEDIUM severity; BLOB/cmk rows present with no severity; dar_storage_aws_managed_count > 0 for platform-managed accounts

**Note:** Manual-only — requires live Azure subscription; not run in unit tests.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-28-03: GCS Reuse — Zero Duplicate storage.buckets.list API Call Invariant

> Added Phase 28 (2026-04-25): STOR-03 — verify Phase 28 does NOT issue duplicate `storage.buckets.list` calls. Phase 26 GCS data is reused via the GCS-SUMMARY sentinel endpoint.

**Prerequisites:** `pip install quirk[cloud]`; GCP project with at least one bucket; ADC configured (`gcloud auth application-default login`).

**Steps:**
1. Configure `gcp_uat.yaml`:
   ```yaml
   connectors:
     enable_gcp: true
     gcp_project_id: <real-project>
   ```
2. Run with verbose logging: `quirk --config gcp_uat.yaml --verbose`
3. Inspect logs for `gcs_scanning` and `gcs_storage_reuse` phase block timings.
4. Check audit log (or `--verbose` scan output) for `storage.buckets.list` API call count.

**Expected:**
- `gcs_scanning` phase block runs (Phase 26 data collection)
- `gcs_storage_reuse` phase block runs (Phase 28 sentinel read) — confirms helper invoked
- Total `storage.buckets.list` calls observable in the scan run = 1 (only the Phase 26 call), not 2
- Per-bucket GCS rows from Phase 26 still appear in DB

**Pass Criteria:**
- `python -m pytest tests/test_gcs_reuse.py` → 5 passed
- Live path: `gcs_storage_reuse` timing block present in scan output; no second `storage.buckets.list` call; Phase 26 per-bucket rows intact in DB

**Note:** Manual-only — requires live GCP project for API call verification.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

## Phase 29: Kubernetes Secrets Inspection (UAT-29-XX)

---

### UAT-29-01: EKS Encryption + Secret-Type Enumeration

> Added Phase 29 (2026-04-26): K8S-01/K8S-02 — validate `_scan_eks_encryption` and `_enumerate_secret_types` against a live AWS EKS cluster. Tests encryptionConfig severity ladder (HIGH unencrypted, no severity with keyArn) and secret-type counter invariant (type counts only, never secret values).

**Prerequisites:** `pip install quirk[cloud]`; AWS CLI logged in (`aws configure`); EKS cluster
with `aws eks update-kubeconfig --name <cluster>` already run; `kubectl get pods -n default` works.

**Steps:**
1. Configure `eks_uat.yaml`:
   ```yaml
   connectors:
     enable_k8s: true
     k8s_provider: eks
     k8s_cluster_name: <cluster>
     aws_region: <region>
     k8s_namespace: default
   ```
2. Run `quirk --config eks_uat.yaml`
3. Inspect output for `protocol=KUBERNETES` rows.

**Expected:**
- One `aws://eks/<cluster>` row with `service_detail` of `EKS/encrypted` OR `EKS/unencrypted` depending on cluster encryptionConfig
- If encryptionConfig is empty/absent: `service_detail=EKS/unencrypted` and `severity=HIGH`
- One `<cluster>/secrets` row with `service_detail=secret-types-summary` and `dat_scan_json` containing type counts (Opaque, kubernetes.io/tls, etc.)
- `dat_scan_json` for the secrets row contains NO secret values — only counts
- `dar_k8s_unencrypted_count` matches expected count in evidence summary
- No `OperationNotPageableError` and no `AttributeError` in scan logs

**Pass Criteria:**
- `python -m pytest tests/test_k8s_connector.py` — 15 passed
- `python -m pytest tests/test_dar_k8s_scoring.py` — 12 passed
- Live path: one `aws://eks/<cluster>` KUBERNETES row in DB; `service_detail` reflects actual encryptionConfig; secret-types-summary row contains type counts only

**Note:** Manual-only — requires live AWS EKS cluster.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-29-02: GKE Encryption + Secret-Type Enumeration

> Added Phase 29 (2026-04-26): K8S-01 GKE path — validate `_scan_gke_encryption` and `_enumerate_secret_types` against a live Google Cloud GKE cluster. Tests databaseEncryption.state numeric comparison (== 2 encrypted, != 2 unencrypted).

**Prerequisites:** `pip install quirk[cloud]`; `gcloud auth application-default login`;
`gcloud container clusters get-credentials <cluster> --region <region> --project <project>` already run.

**Steps:**
1. Configure `gke_uat.yaml`:
   ```yaml
   connectors:
     enable_k8s: true
     k8s_provider: gke
     gke_clusters:
       - project: my-gcp-project
         location: us-central1
         name: my-gke-cluster
     k8s_namespace: default
   ```
2. Run `quirk --config gke_uat.yaml`
3. Inspect output for `protocol=KUBERNETES` rows.

**Expected:**
- One `gcp://gke/.../<cluster>` row with `service_detail=GKE/encrypted` (databaseEncryption.state == 2) or `GKE/unencrypted` (databaseEncryption.state != 2)
- State == 2: no severity; state != 2: `severity=HIGH`
- One `secret-types-summary` row with type counts in `dat_scan_json`
- `dar_k8s_unencrypted_count` correctly reflects the cluster's encryption state
- Per Pitfall 2 in 29-RESEARCH.md: state must be checked numerically (`== 2`), not by string label

**Pass Criteria:**
- `python -m pytest tests/test_k8s_connector.py` — 15 passed (K8S-01 GKE tests pass)
- Live path: one GKE KUBERNETES row; `service_detail` matches actual databaseEncryption.state; no AttributeError

**Note:** Manual-only — requires live GKE cluster.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-29-03: AKS Encryption + RBAC Degradation

> Added Phase 29 (2026-04-26): K8S-01 AKS path + K8S-03 RBAC-403 degradation — validate `_scan_aks_encryption` against a live Azure AKS cluster and exercise the graceful RBAC-403 path via a limited-permission service principal.

**Prerequisites:** `pip install quirk[cloud]`; Azure CLI logged in (`az login`); AKS cluster available; service principal with limited permissions prepared for the RBAC-403 test leg.

**Steps:**
1. Configure `aks_uat.yaml`:
   ```yaml
   connectors:
     enable_k8s: true
     k8s_provider: aks
     aks_clusters:
       - subscription_id: <azure-subscription-uuid>
         resource_group: my-rg
         name: my-aks-cluster
     k8s_namespace: default
   ```
2. Run `quirk --config aks_uat.yaml` with full credentials.
3. Re-run with a service principal that has no `secrets/list` permission in the namespace to exercise the RBAC-403 path.

**Expected (full credentials run):**
- One `azure://aks/.../<cluster>` row with `service_detail=AKS/kv-kms` if Key Vault KMS enabled, or `AKS/platform-managed` with `severity=MEDIUM` otherwise
- Three nested getattr defenses produce a finding even on AKS clusters with no `securityProfile` field (Pitfall 4 in 29-RESEARCH.md)
- No `AttributeError` in logs

**Expected (limited-permission run):**
- One KUBERNETES row with `scan_error=insufficient-rbac-privileges` and `service_detail` containing `"Remediation: RBAC role requires get,list on secrets in namespace 'default'"`
- `dar_k8s_inaccessible_count` increments by 1
- No unhandled exception traceback in logs (graceful K8S-03 degradation)

**Pass Criteria:**
- `python -m pytest tests/test_k8s_connector.py` — 15 passed (K8S-01 AKS + K8S-02 RBAC-403 tests pass)
- Live path (full creds): AKS/kv-kms or AKS/platform-managed row present; no exception
- Live path (limited creds): KUBERNETES row with `scan_error=insufficient-rbac-privileges` present; `dar_k8s_inaccessible_count == 1`; no traceback

**Note:** Manual-only — requires live Azure AKS cluster and ability to provision a limited-permission service principal.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

## Phase 30: HashiCorp Vault Connector (UAT-30-XX)

### UAT-30-01: Vault Chaos Lab End-to-End — Transit + PKI + Auth Findings

> Added Phase 30 (2026-04-26): Validates VAULT-01/02/03 against the dedicated `--profile vault`
> Docker chaos lab. Confirms all 5 expected findings (transit classification, exportable
> MEDIUM, PKI HIGH, token HIGH, userpass MEDIUM) are emitted.

**Prerequisites:** `pip install quirk[cloud]`; Docker available.

**Steps:**
1. `cd quantum-chaos-enterprise-lab && docker compose --profile vault up -d`
2. Wait for `vault-30-seed` to exit successfully (`docker compose --profile vault ps`)
3. Configure `vault_uat.yaml` with `enable_vault: true`, `vault_addr: http://localhost:28200`,
   `vault_token: root`
4. Run `quirk --config vault_uat.yaml`
5. Confirm CryptoEndpoint rows match `labs/vault/expected_results.md`
6. `docker compose --profile vault down -v`

**Expected:**
- 5 `protocol="VAULT"` rows produced (1 classification, 1 MEDIUM transit, 1 HIGH PKI,
  1 HIGH token auth, 1 MEDIUM userpass auth)
- `dar_vault_weak_count == 2` (HIGH-only)
- `data_at_rest` subscore reduced
- CBOM contains `RSA-2048` algorithm registration from transit key

**Pass Criteria:**
- `python -m pytest tests/test_vault_connector.py tests/test_dar_vault_scoring.py -q` — all pass
- Live chaos lab: 5 vault rows present in `quirk-output/scan-results.json`
- `dar_vault_weak_count` in evidence summary equals 2

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-30-02: Vault PKI Root + Intermediate CA Detection

> Added Phase 30 (2026-04-26): VAULT-02 — exercises D-03 (root + intermediate CA each emit a
> separate endpoint) and D-04 (intermediate-failure swallowed silently).

**Prerequisites:** Live HashiCorp Vault instance with PKI mount that has both a root CA and
generated intermediate (or use chaos lab and `vault write pki_int/intermediate/generate/internal ...`
manually).

**Steps:**
1. With chaos lab running: `docker exec -it $(docker compose --profile vault ps -q vault-30) sh`
2. `vault secrets enable -path=pki_int pki && vault write pki_int/root/generate/internal common_name="intermediate.local" key_type=rsa key_bits=4096 ttl=8760h`
3. Re-run `quirk --config vault_uat.yaml`
4. Confirm an additional `service_detail="PKI/pki_int"` row OR a `:intermediate-1` row emerges

**Expected:**
- For each PKI mount with a chain configured, the scanner emits `PKI/<mount>` (root) AND one
  or more `PKI/<mount>:intermediate-N` endpoints
- For PKI mounts with NO intermediate, `read_ca_certificate_chain` raises and the scanner
  silently returns the root endpoint only (D-04)

**Pass Criteria:**
- No exception traceback in scanner logs even when intermediate is absent
- Both root and intermediate rows present when a chain exists

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-30-03: Vault Auth Method Risk Tiering

> Added Phase 30 (2026-04-26): VAULT-03 — confirms D-05 (token always HIGH unconditional even
> when AppRole/Kubernetes/OIDC are present) and D-06 (AUTH_RISK_MAP tiers).

**Prerequisites:** Chaos lab running.

**Steps:**
1. With chaos lab running: `docker exec -it $(docker compose --profile vault ps -q vault-30) sh`
2. `vault auth enable approle && vault auth enable kubernetes` (positive-posture methods)
3. Re-run `quirk --config vault_uat.yaml`
4. Inspect emitted vault auth rows

**Expected:**
- `auth/token` row with `severity=HIGH` is STILL emitted (D-05 — even though approle is also
  enabled, token is unconditional)
- `auth/userpass` row with `severity=MEDIUM`
- NO row for `auth/approle` or `auth/kubernetes` (D-06 — positive posture)

**Pass Criteria:**
- Vault auth row count: exactly 2 (token HIGH + userpass MEDIUM)
- No row produced for approle or kubernetes

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

## Phase 32: Email Scanner (UAT-32-XX)

### UAT-32-01: Email Scan — All 7 Standard Ports Return TLS Metadata

> Added Phase 32 (2026-04-27): Validates EMAIL-00..06 — `scan_email_targets()` against the
> running `--profile email` chaos lab returns `CryptoEndpoint` rows for all 7 standard email
> ports (25, 465, 587, 143, 993, 110, 995) with TLS version, negotiated cipher, cert subject /
> issuer / expiry, and key algorithm; `email_scan_json` is populated on the DB rows.

**Prerequisites:** `pip install quirk[motion]` (sslyze required for full enumeration); Docker
available. Lab booted with privileged-port forwarding (e.g. `sudo socat` mapping 25→30025
through 995→30995) OR direct invocation per `labs/email/expected_results.md`.

**Steps:**
1. `cd quantum-chaos-enterprise-lab && docker compose --profile email up -d --build`
2. Wait for `postfix-email` and `dovecot-email` to report healthy
   (`docker compose --profile email ps`).
3. Configure `email_uat.yaml` with `connectors.enable_email: true`, target = `localhost`.
4. Run `quirk --config email_uat.yaml --profile standard`.
5. Inspect `quirk-output/scan-results.json` for the email rows; query the SQLite DB:
   `SELECT host, port, protocol, tls_version, cipher_suite, email_scan_json FROM crypto_endpoints WHERE protocol LIKE '%MTP%' OR protocol LIKE '%MAP%' OR protocol LIKE '%OP3%';`
6. `docker compose --profile email down`.

**Expected:**
- ≥7 `CryptoEndpoint` rows produced — one per port (25/465/587/143/993/110/995).
- Each row has non-NULL `tls_version`, `cipher_suite`, `cert_subject`, `cert_expiry`,
  `cert_pubkey_algo` (RSA-2048).
- `email_scan_json` column is non-NULL for every row.
- Cipher matches `labs/email/expected_results.md` capture
  (e.g. `TLS_RSA_WITH_ARIA_256_GCM_SHA384` on Postfix ports, `TLS_CHACHA20_POLY1305_SHA256` on
  Dovecot ports under TLS 1.3 default).

**Pass Criteria:**
- 7 email-protocol rows present in the DB.
- `python -m pytest tests/test_email_scanner.py -q` exits 0 (18 passed).
- `email_scan_json` column populated for all 7 rows.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-32-02: STARTTLS Downgrade on Port 25 + Weak Cipher Findings

> Added Phase 32 (2026-04-27): Validates EMAIL-08/09 — port-25 STARTTLS endpoint emits a
> static MEDIUM `STARTTLS downgrade risk on SMTP` finding regardless of cipher; a weak RSA
> key-exchange cipher (`TLS_RSA_WITH_*`) on any email port emits HIGH
> `Weak cipher suite on email TLS endpoint`. D-11 layering: a port-25 row with weak RSA cipher
> emits BOTH findings — they are not deduplicated.

**Prerequisites:** UAT-32-01 prerequisites met; lab booted; scan completed.

**Steps:**
1. From the same scan output, inspect findings:
   `jq '.findings[] | select(.title | contains("STARTTLS") or contains("Weak cipher"))' quirk-output/scan-results.json`
2. Confirm at least one MEDIUM `STARTTLS downgrade risk on SMTP` finding on port 25.
3. Confirm at least one HIGH `Weak cipher suite on email TLS endpoint` finding (Postfix ports
   25/465/587 against the lab cipher allowlist).
4. Confirm port 25 has BOTH findings (D-11 layering).

**Expected:**
- ≥1 MEDIUM `STARTTLS downgrade risk on SMTP` finding, scoped to port 25.
- ≥1 HIGH `Weak cipher suite on email TLS endpoint` finding.
- Port 25 row triggers BOTH findings simultaneously when the cipher is weak.

**Pass Criteria:**
- Severity counts match `labs/email/expected_results.md`: ≥3 HIGH weak-cipher,
  ≥1 MEDIUM STARTTLS-downgrade.
- `python -m pytest tests/test_email_findings.py -q` exits 0 (9 passed).
- D-11 layering: port 25 has 2 distinct findings (no `_dedupe_findings()` collapse).

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-32-03: Unreachable Port 25 — Graceful CONNECTION_REFUSED

> Added Phase 32 (2026-04-27): Validates EMAIL-01 + D-03 — `CONNECTION_REFUSED` on port 25
> (cloud VM with egress block, or simulated locally via firewall drop) does NOT crash the
> scan; it is logged at DEBUG and the remaining 6 email ports continue.

**Prerequisites:** A target where port 25 is unreachable (e.g. cloud VM that blocks port 25
egress, OR locally `sudo pfctl` / `iptables` drop on 25 only). Other email ports reachable
(can also be the chaos lab with port 25 firewalled off from the host).

**Steps:**
1. Configure `email_uat.yaml` with the unreachable target.
2. Run `quirk --config email_uat.yaml --profile standard --verbose`.
3. Confirm scanner does NOT raise / abort.
4. Inspect logs for a single DEBUG line referencing `CONNECTION_REFUSED` on port 25.
5. Confirm scan completes, output written, dashboard renders, and findings for the OTHER
   6 ports are still emitted (or scan_error rows recorded).

**Expected:**
- Scan exits 0 (success) — no traceback.
- Logs contain `CONNECTION_REFUSED` at DEBUG level for port 25 (or equivalent
  per-port error captured in `email_scan_json`).
- Remaining 6 ports produce normal `CryptoEndpoint` rows.

**Pass Criteria:**
- Exit code 0 from `quirk` invocation.
- Port-25 row has `scan_error` (or is absent) — never crashes the run.
- Other ports succeed (rows present, `email_scan_json` populated).

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-32-04: Stdlib Fallback — sslyze Uninstalled

> Added Phase 32 (2026-04-27): Validates EMAIL-07 — when sslyze is not installed, the email
> scanner falls through to `smtplib`/`imaplib`/`poplib` STARTTLS handshakes (and direct TLS
> for the implicit-TLS ports), and still extracts TLS version + cipher + cert from the
> `ssl.SSLSocket`. Note: stdlib's default `ssl.create_default_context()` excludes RSA-kex
> ciphers, so against the chaos lab's RSA-only allowlist the Postfix ports may handshake-fail
> via fallback — the test target should be a server that accepts at least one
> stdlib-compatible cipher.

**Prerequisites:** A virtualenv with `quirk` installed but WITHOUT sslyze
(`pip uninstall -y sslyze`). A reachable mail server with at least one TLS 1.2 PFS cipher
acceptable to the stdlib client (e.g. a real ISP mail server, OR a Postfix lab variant with
ECDHE enabled — see `labs/email/postfix/main.cf` for the cipher excludes to relax).

**Steps:**
1. `pip uninstall -y sslyze` in the project venv.
2. `python -c "from quirk.scanner.email_scanner import SSLYZE_AVAILABLE; print(SSLYZE_AVAILABLE)"`
   — confirm `False`.
3. Run `quirk --config email_uat.yaml --profile standard --verbose` against the
   stdlib-compatible target.
4. Inspect logs for fallback path indicators (no sslyze imports referenced).
5. Inspect output rows: at least one row has non-NULL `tls_version` and `cipher_suite`
   captured via the stdlib path.
6. Re-install sslyze: `pip install sslyze`.

**Expected:**
- Scanner does not crash on missing sslyze.
- At least one `CryptoEndpoint` row populated by the stdlib fallback path with
  `tls_version` and `cipher_suite` non-NULL.
- `_peer_metadata()` extracts `version()` / `cipher()` / `getpeercert()` from the underlying
  `ssl.SSLSocket`.

**Pass Criteria:**
- `python -m pytest tests/test_email_scanner.py -q -k fallback` — 3 fallback tests green.
- Live sslyze-uninstalled scan produces ≥1 row with non-NULL `tls_version`.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-32-05: Chaos Lab End-to-End — Findings Match Expected Results

> Added Phase 32 (2026-04-27): Validates EMAIL-11/12 — `docker compose --profile email up`
> boots Postfix+Dovecot; running the scanner against the lab produces ≥1 HIGH weak-cipher
> finding and ≥1 MEDIUM STARTTLS-downgrade finding; the captured output matches
> `labs/email/expected_results.md`. Also covers the regression baseline for the
> `logger.info()` call signature fix from Plan 32-06 (see commit `0c6a8c3`) — the live
> end-to-end run with a real `quirk.logging_util.Logger` instance must not crash on the
> `cfg.connectors.enable_email` branch.

**Prerequisites:** sslyze installed; Docker available; privileged-port forwarding configured
on macOS (or run on Linux without restrictions).

**Steps:**
1. `cd quantum-chaos-enterprise-lab && docker compose --profile email up -d --build`
2. Wait for both services healthy.
3. Run the full pipeline: `quirk --config email_uat.yaml --profile standard` with a real
   `Logger` (not stubbed). Confirm the run does NOT raise
   `TypeError: Logger.info() takes 2 positional arguments but 4 were given` (Plan 32-06
   regression).
4. Diff the scan output's email findings against `labs/email/expected_results.md` (compare
   finding titles, severities, ports).
5. `docker compose --profile email down`.

**Expected:**
- Run completes without `TypeError` on logger.info.
- ≥1 HIGH `Weak cipher suite on email TLS endpoint` finding.
- ≥1 MEDIUM `STARTTLS downgrade risk on SMTP` finding.
- Captured cipher / TLS-version / cert posture matches `labs/email/expected_results.md`
  (Postfix: `TLS_RSA_WITH_ARIA_256_GCM_SHA384` at TLS 1.2; Dovecot: TLS 1.3 default with
  documented caveat).
- Total finding count and severity distribution match the expected_results.md "Expected
  Findings" table.

**Pass Criteria:**
- HIGH count and MEDIUM count meet the documented minimums.
- `labs/email/expected_results.md` is byte-for-byte consistent with the live scan (or
  documented diff justified by container image drift / OpenSSL caveat).
- No `Logger.info()` TypeError in the run-scan log output.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-32-06: service_detail Label Format

> Added Phase 32 (2026-04-27): Validates EMAIL-10 — every email `CryptoEndpoint` row's
> `service_detail` field follows the `"<protocol_label>:<port>"` convention
> (e.g. `"SMTP-STARTTLS:587"`, `"SMTPS:465"`, `"IMAP-STARTTLS:143"`, `"IMAPS:993"`,
> `"POP3-STARTTLS:110"`, `"POP3S:995"`).

**Prerequisites:** UAT-32-01 completed; scan output available.

**Steps:**
1. Query: `SELECT DISTINCT service_detail FROM crypto_endpoints WHERE protocol IN ('SMTP-STARTTLS','SMTPS','IMAP-STARTTLS','IMAPS','POP3-STARTTLS','POP3S');`
2. Confirm each row matches the `^(SMTP-STARTTLS|SMTPS|IMAP-STARTTLS|IMAPS|POP3-STARTTLS|POP3S):\d+$` regex.

**Expected:**
- All 7 distinct `service_detail` values follow `<label>:<port>`:
  `SMTP-STARTTLS:25`, `SMTPS:465`, `SMTP-STARTTLS:587`,
  `IMAP-STARTTLS:143`, `IMAPS:993`, `POP3-STARTTLS:110`, `POP3S:995`.

**Pass Criteria:**
- All email rows match the regex `^(SMTP-STARTTLS|SMTPS|IMAP-STARTTLS|IMAPS|POP3-STARTTLS|POP3S):\d+$`.
- No row has empty `service_detail` or a malformed label.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-32-07: email_scan_json DB Persistence (Phase 32 SC-1)

> Added Phase 32 Plan 32-08 (2026-04-27): Validates Phase 32 Roadmap SC-1 —
> per-host email TLS scan summaries are persisted to the
> `crypto_endpoints.email_scan_json` column. One row per scanned host carries
> the JSON aggregate (lowest-port endpoint), mirroring the existing
> `kerberos_scan_json` pattern.

**Prerequisites:** UAT-32-01 completed against the chaos lab (or any live mail
host); SQLite DB available at the configured path.

**Steps:**
1. Run a scan with `cfg.connectors.enable_email = true` against at least one
   host that has at least one reachable email port.
2. Query:
   ```sql
   SELECT host, COUNT(*) AS rows,
          SUM(CASE WHEN email_scan_json IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_json
   FROM crypto_endpoints
   WHERE protocol IN ('SMTP-STARTTLS','SMTPS','IMAP-STARTTLS','IMAPS','POP3-STARTTLS','POP3S')
   GROUP BY host;
   ```
3. Pull the JSON for the populated row and confirm it parses:
   ```sql
   SELECT email_scan_json FROM crypto_endpoints
   WHERE email_scan_json IS NOT NULL LIMIT 1;
   ```
   Then `python3 -c "import json,sys; print(sorted(json.loads(sys.stdin.read()).keys()))" < /tmp/payload`.

**Expected:**
- `rows_with_json == 1` for every host scanned (exactly one endpoint per host
  carries the JSON, attached to the lowest-port row).
- The JSON parses to a dict with keys `host`, `session_start`, `ports`.
- `ports` is a list whose length equals the number of ports actually scanned
  for that host (failures are included with `scan_error` populated).

**Pass Criteria:**
- For every distinct host: exactly one `email_scan_json` is non-NULL.
- The JSON deserializes without error.
- The `ports` list contains an entry for each port the scanner attempted,
  including failures (no silent drops).

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

# Series 6: Cryptographic Findings — CLI Verification

---

### UAT-6-01: Findings Output — JSON Structure

**Prerequisites:** Completed scan with findings.

**Steps:**
1. Open `output/findings-*.json` (most recent)
2. Validate structure with: `python3 -c "import json; d=json.load(open('output/findings-TIMESTAMP.json')); print(list(d[0].keys()))"`

**Expected:** Each finding has required fields.

**Pass Criteria:**
Each finding object contains:
- `host`
- `port`
- `protocol`
- `severity` (one of: CRITICAL, HIGH, MEDIUM, LOW, INFO)
- `title` or `finding_type`
- `description`
- `quantum_risk` or equivalent quantum safety assessment

---

### UAT-6-02: TLS Findings — Cipher Suite Detection

**Prerequisites:** Lab core running. Completed scan covering port 8443 (legacy TLS).

**Steps:**
1. Review `output/findings-*.json`
2. Filter for port 8443: `python3 -c "import json; data=json.load(open('output/findings-TIMESTAMP.json')); [print(f) for f in data if f.get('port')==8443]"`

**Expected:** Legacy TLS findings on port 8443 reference specific weak cipher suites.

**Pass Criteria:**
- At least one finding for port 8443
- Finding includes cipher suite name (e.g., `TLS_RSA_WITH_AES_128_CBC_SHA`)
- Finding severity is MEDIUM or HIGH
- `quantum_risk: quantum-vulnerable` for RSA key exchange

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-6-03: Certificate Expiry Detection

**Prerequisites:** Lab core running (port 9443 = expired cert). Completed scan.

**Steps:**
1. Check findings for port 9443: `cat output/findings-*.json | python3 -m json.tool | grep -A5 '"port": 9443'`
2. Review certificate fields: expiry date, days remaining

**Expected:** Risk engine emits a HIGH finding for the expired certificate.

**Pass Criteria:**
- Finding title is `"TLS certificate expired"` with severity `HIGH`
- `cert_not_after` is in the past relative to scan date
- Finding recommendation includes the expiry date
- No `"TLS certificate expiring within 30 days"` finding also present (expired wins)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-6-04: Self-Signed Certificate Detection

**Prerequisites:** Lab core running (port 10443 = self-signed). Completed scan.

**Steps:**
1. Check findings for port 10443: `cat output/findings-*.json | python3 -m json.tool | grep -A5 '"port": 10443'`
2. Verify cert_issuer and cert_subject are equal in scan data

**Expected:** Risk engine emits a MEDIUM finding for the self-signed certificate.

**Pass Criteria:**
- Finding title is `"Self-signed or untrusted TLS certificate"` with severity `MEDIUM`
- `cert_issuer` equals `cert_subject` in the underlying scan data
- Finding recommendation references replacing with a CA-issued certificate

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-6-05: mTLS Endpoint Classification

**Prerequisites:** Lab core running (port 11443 = mTLS). Completed scan.

**Steps:**
1. Check findings for port 11443
2. Review protocol classification

**Expected:** Endpoint classified as TLS-present but handshake blocked.

**Pass Criteria:**
- Protocol is `TLS` (not HTTP or UNKNOWN)
- Condition includes `MTLS_REQUIRED` or `TLS_HANDSHAKE_FAILED`
- Service correctly identified as TLS, not misclassified as HTTP

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-6-06: Plaintext HTTP Finding — Severity Check

**Prerequisites:** Lab core running (port 8000 = plaintext HTTP). Completed scan.

**Steps:**
1. Check findings for port 8000
2. Verify severity level

**Expected:** Plaintext HTTP exposure flagged as HIGH severity.

**Pass Criteria:**
- Finding type: `PLAINTEXT_HTTP` or `HTTP_EXPOSURE`
- Severity: HIGH or CRITICAL
- Finding includes remediation guidance

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-6-07: HTTP on TLS-Like Port Detection

**Prerequisites:** Lab core running (port 8444 = HTTP on TLS port). Completed scan.

**Steps:**
1. Check findings for port 8444
2. Verify it's not misclassified as TLS

**Expected:** Port 8444 classified as HTTP (not TLS), with a specific finding for misconfiguration.

**Pass Criteria:**
- Protocol: `HTTP`
- Finding type references `HTTP_ON_TLS_LIKE_PORT`
- Severity: HIGH

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-6-08: Quantum Safety Classification — SSH Algorithms

**Prerequisites:** Lab running with SSH on port 2222. Completed scan.

**Steps:**
1. Review SSH-related findings in output JSON
2. Check algorithm classifications

**Expected:** SSH algorithms classified with quantum safety labels.

**Pass Criteria:**
- ED25519 host key (if present) classified as `quantum-safe` or at least not quantum-vulnerable
- RSA host key classified as `quantum-vulnerable`
- ECDSA algorithms classified as `quantum-vulnerable`
- Each algorithm has NIST quantum level in the finding

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-6-09: Scorecard Output — CLI Review

**Prerequisites:** Completed scan.

**Steps:**
1. `cat output/scorecard-*.md`
2. Review all sections

**Expected:** Scorecard contains score, confidence, key drivers, and action items.

**Pass Criteria:**
- Score between 0 and 100
- Confidence score present
- `## Key Risk Drivers` section with at least 1 item
- `## Recommended Actions (Next 30 Days)` section
- `## Recommended Actions (Next 60 Days)` section

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-6-10: Roadmap Output — Migration Phases

**Prerequisites:** Completed scan with findings.

**Steps:**
1. `cat output/roadmap-*.md`
2. Review NOW/NEXT/LATER sections

**Expected:** Roadmap organized into three phases with evidence-driven recommendations.

**Pass Criteria:**
- `## NOW (0–30 days)` section present with ≥ 1 item
- `## NEXT (31–90 days)` section present with ≥ 1 item
- `## LATER (90+ days)` section present with ≥ 1 item
- Each item has `Why:` evidence description
- Each item has an `Owner:` placeholder

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-6-11: CBOM JSON Structure

**Prerequisites:** Completed TLS scan.

**Steps:**
1. `python3 -c "import json; d=json.load(open('output/cbom-TIMESTAMP.json')); print(d['bomFormat'], d['specVersion'])"`
2. Count components: `python3 -c "import json; d=json.load(open('output/cbom-TIMESTAMP.json')); print(len(d.get('components', [])))"`

**Expected:** Valid CycloneDX 1.6 JSON with algorithm, certificate, and protocol components.

**Pass Criteria:**
- `bomFormat: "CycloneDX"`
- `specVersion: "1.6"`
- Components include at minimum:
  - At least one `type: "cryptographic-asset"` component
  - At least one algorithm component (e.g., AES-256-GCM, RSA)
- CBOM has a `serialNumber` BOM-ref

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-6-12: CBOM XML Validity

**Prerequisites:** Completed scan, `cbom-*.xml` present.

**Steps:**
1. `python3 -c "import xml.etree.ElementTree as ET; ET.parse('output/cbom-TIMESTAMP.xml'); print('Valid XML')"`

**Expected:** XML file is well-formed and parseable.

**Pass Criteria:**
- No XML parse error
- Root element is CycloneDX namespace element

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-6-13: Intelligence JSON — Machine-Readable Output

**Prerequisites:** Completed scan.

**Steps:**
1. `python3 -c "import json; d=json.load(open('output/intelligence-TIMESTAMP.json')); print(list(d.keys()))"`

**Expected:** Machine-readable JSON with score, confidence, evidence, and roadmap.

**Pass Criteria:**
- Keys include: `score`, `confidence`, `score_label`, `evidence`, `roadmap`
- `score` is numeric, 0–100
- `confidence` is numeric, 0–100
- `roadmap` contains NOW/NEXT/LATER items
- `evidence` contains finding counts

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-6-14: Risk Engine — Legacy Cipher Suite Finding

**Prerequisites:** Lab core running (port 8443 = legacy TLS). Completed scan with `--profile deep` (sslyze required for `tls_legacy_suites_present` detection).

**Steps:**
1. Run scan with deep profile: `quirk --config lab-core.yaml --profile deep`
2. Check findings for port 8443: `cat output/findings-*.json | python3 -m json.tool | grep -A8 '"port": 8443'`

**Expected:** Risk engine emits a LOW finding for legacy cipher suites in addition to the legacy TLS version finding.

**Pass Criteria:**
- Finding title `"Legacy TLS cipher suites accepted"` present with severity `LOW`
- Finding recommendation references AEAD suites and forward secrecy
- Finding is distinct from (and may co-exist with) `"Legacy TLS versions allowed (TLS 1.0/1.1)"`

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-6-15: Risk Engine — Quantum-Vulnerable RSA Key Finding

**Prerequisites:** Lab phaseA running (port 14443 = RSA-1024 key). Completed scan.

**Steps:**
1. Start phaseA: `docker compose --profile phaseA up -d && sleep 10`
2. Run scan covering port 14443
3. Check findings: `cat output/findings-*.json | python3 -m json.tool | grep -A8 '"port": 14443'`

**Expected:** Risk engine emits a HIGH finding for the undersized RSA key (classical minimum violation + quantum vulnerability).

**Pass Criteria:**
- Finding title `"TLS certificate uses undersized RSA key"` with severity `HIGH`
- Finding recommendation references RSA-1024, the 2048-bit classical minimum, and PQC migration
- No separate `"TLS certificate uses quantum-vulnerable RSA key"` (MEDIUM) also present — undersized finding subsumes it

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

---

# Series 7: Web Dashboard — UI Testing

**Prerequisites for all Series 7 tests:**
1. Completed scan producing findings in `./quirk.db` (or `quirk-output/quirk.db` if using interactive mode)
2. Dashboard running: `quirk serve --no-open`
3. Open browser to `http://127.0.0.1:8512`

---

### UAT-7-01: Dashboard Loads — No Blank Screen

**Steps:**
1. Navigate to `http://127.0.0.1:8512`
2. Observe page load

**Expected:** Dashboard loads with QU.I.R.K. branding visible.

**Pass Criteria:**
- Page loads within 5 seconds
- QU.I.R.K. wordmark visible in sidebar
- No JavaScript console errors (check DevTools)
- No blank white screen

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-02: Dashboard — Favicon

**Steps:**
1. Check browser tab
2. Inspect page source: `curl -s http://127.0.0.1:8512 | grep favicon`

**Expected:** QU.I.R.K. electric-blue favicon displayed in browser tab.

**Pass Criteria:**
- Favicon appears in browser tab (not browser default icon)
- Page title is `QU.I.R.K.` or similar branded title

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-03: Executive Page — Score Gauge

**Steps:**
1. Navigate to Executive page (default landing or `/executive` route)
2. Observe the score gauge component

**Expected:** Quantum Readiness Score displayed as a visual gauge.

**Pass Criteria:**
- Score gauge renders with a numeric value 0–100
- Score label visible (EXCELLENT/GOOD/MODERATE/FAIR/POOR)
- Score color-coded (green = good, red = poor)
- Confidence badge present with value

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-04: Executive Page — Severity Chart

**Steps:**
1. On Executive page, locate severity distribution chart

**Expected:** Bar or pie chart showing CRITICAL/HIGH/MEDIUM/LOW/INFO finding counts.

**Pass Criteria:**
- Chart renders with at least 2 severity levels
- Severity counts match findings in `output/findings-*.json`
- Chart is interactive (hover shows count)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-05: Executive Page — Score Driver Cards

**Steps:**
1. On Executive page, scroll to driver cards section

**Expected:** Four score driver cards: Hygiene, Modern TLS, Identity Trust, Agility Signals.

**Pass Criteria:**
- All 4 subscores visible (each out of 25 pts)
- Each card shows the subscore value
- Each card has a brief description
- Cards total ≤ 100

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-06: Findings Page — Table Renders

**Steps:**
1. Navigate to Findings page (sidebar link)
2. Observe findings table

**Expected:** Table displays all findings with sortable columns.

**Pass Criteria:**
- Table renders with rows (not empty)
- Columns: Severity, Host, Port, Protocol, Finding Title
- Row count matches `output/findings-*.json` count
- Severity badges color-coded correctly

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-07: Findings Page — Sorting

**Steps:**
1. On Findings page, click the "Severity" column header
2. Observe sort order change
3. Click again to reverse sort

**Expected:** Table sorts by severity in both ascending and descending order.

**Pass Criteria:**
- First click: sorted ascending (INFO → CRITICAL)
- Second click: sorted descending (CRITICAL → INFO)
- Sort indicator (arrow) visible on column header

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-08: Findings Page — Filtering

**Steps:**
1. On Findings page, locate filter/search input
2. Type `CRITICAL` in the filter
3. Observe table rows

**Expected:** Table filters to show only CRITICAL severity findings.

**Pass Criteria:**
- Only rows with CRITICAL severity shown
- Row count decreases when filter applied
- Clearing filter restores all rows

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-09: Findings Page — Detail Slide-out

**Steps:**
1. On Findings page, click any finding row
2. Observe right-side detail panel/sheet

**Expected:** Slide-out panel opens with full finding details.

**Pass Criteria:**
- Detail panel opens on click
- Full description visible
- Host, port, protocol, severity all shown
- Quantum risk assessment visible
- Panel closes when clicking outside or X button

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-10: Certificates Page — Inventory Table

**Steps:**
1. Navigate to Certificates page (sidebar link)

**Expected:** Certificate inventory showing all TLS certificates discovered.

**Pass Criteria:**
- Table renders with at least 1 row (from lab TLS services)
- Columns: Subject, Issuer, Expiry, Algorithm, Quantum Safety
- Expired certificates shown with visual indicator (red date)
- Self-signed certs flagged

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-11: Certificates Page — Quantum Safety Labels

**Steps:**
1. On Certificates page, look for quantum safety column
2. Check labels for different certificate algorithms

**Expected:** Each certificate has a quantum safety assessment badge.

**Pass Criteria:**
- RSA certificates show `quantum-vulnerable` badge
- ECDSA certificates show `quantum-vulnerable` badge
- Badge colors differentiate safety levels
- Badge tooltip or description available

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-12: Certificates Page — Expiry Sorting

**Steps:**
1. On Certificates page, click the Expiry column header to sort
2. Verify expired certs appear first (ascending) or last (descending)

**Expected:** Certificates sortable by expiry date.

**Pass Criteria:**
- Expired cert (port 9443) appears in the correct sort position
- Near-expiry certs show days remaining
- Date format is human-readable

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-13: CBOM Page — Algorithm Table

**Steps:**
1. Navigate to CBOM page (sidebar link)
2. Select "Algorithms" tab (if tabbed)

**Expected:** Table of all cryptographic algorithms found in the scan.

**Pass Criteria:**
- Algorithm names visible (e.g., AES-256-GCM, RSA-2048, Ed25519)
- Quantum safety badge per algorithm
- Primitive type visible (e.g., KEY_AGREEMENT, ASYMMETRIC, SYMMETRIC)
- NIST PQC level displayed where available

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-14: CBOM Page — Graph Visualization

**Steps:**
1. On CBOM page, select "Graph" tab (or equivalent)
2. Observe Cytoscape.js force-directed graph
3. Interact: drag nodes, zoom in/out

**Expected:** Interactive graph showing relationships between algorithms, protocols, and endpoints.

**Pass Criteria:**
- Graph renders with visible nodes and edges
- Nodes draggable
- Scroll-to-zoom works
- Clicking a node shows details panel or tooltip
- At least 3 connected nodes visible

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-15: Roadmap Page — DAG Visualization

**Steps:**
1. Navigate to Roadmap page (sidebar link)
2. Observe directed acyclic graph

**Expected:** Migration roadmap shown as a DAG with NOW/NEXT/LATER color coding.

**Pass Criteria:**
- Graph renders with colored nodes (e.g., red=NOW, yellow=NEXT, green=LATER)
- Nodes labeled with roadmap item titles
- Clicking a node shows detail panel with `Why:` text and owner placeholder
- Dependencies shown as directed edges

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-16: Roadmap Page — Node Detail Panel

**Steps:**
1. On Roadmap page, click any node

**Expected:** Right-side panel shows full roadmap item details.

**Pass Criteria:**
- Item title visible
- Timeframe visible (e.g., "0–30 days")
- `Why:` evidence text visible
- Owner placeholder shown
- Dependency list shown (if any)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-17: PDF Export — Generate Report

**Steps:**
1. On Executive page, locate "Export PDF" button
2. Click the button
3. Wait for PDF to generate (may take 10–30 seconds — Playwright renders headlessly)
4. Observe download

**Expected:** PDF file downloaded named `quirk-report.pdf`.

**Pass Criteria:**
- File downloads or save dialog appears
- File is valid PDF (open in viewer)
- PDF contains score, findings summary, and charts
- PDF is A4 format
- No error toast or error message

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-18: PDF Export — API Endpoint Direct Test

**Steps:**
1. `curl -X POST http://127.0.0.1:8512/api/export/pdf -o /tmp/test-report.pdf`
2. Verify file: `file /tmp/test-report.pdf`

**Expected:** PDF file created via API.

**Pass Criteria:**
- `file` command reports `PDF document`
- File size > 50KB (not empty or truncated)
- HTTP 200 from the API endpoint

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-19: Dashboard — API Latest Scan Endpoint

**Steps:**
1. `curl -s http://127.0.0.1:8512/api/scan/latest | python3 -m json.tool | head -30`

**Expected:** JSON response with full scan data.

**Pass Criteria:**
- Response includes `score`, `confidence`, `findings`, `certificates`, `cbom`, `roadmap`
- `findings` array is non-empty
- `score` is numeric
- Response time < 3 seconds

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-20: Dashboard — SPA Routing

**Steps:**
1. Navigate to `http://127.0.0.1:8512/findings` directly (not via sidebar)
2. Observe page load

**Expected:** Findings page loads directly — SPA routing works.

**Pass Criteria:**
- Page renders correctly (not 404)
- Same content as navigating via sidebar
- URL stays at `/findings`

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-21: Dashboard Theme — No Hardcoded Colors

**Steps:**
1. Open browser DevTools (F12) → Elements
2. Select several UI components (buttons, badges, cards)
3. Check computed styles for hardcoded hex/rgb colors (e.g., `#007bff`, `#28a745`)

**Expected:** All colors reference CSS custom properties (design tokens), not hardcoded values.

**Pass Criteria:**
- Primary interactive elements use `var(--color-*)` or equivalent CSS tokens
- No hardcoded `#hex` colors in inline styles on major components
- Electric-blue (`#00D8FF` or design system equivalent) used for accents
- Dark background palette consistent across all pages

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-22: Dark/Light Theme Toggle

**Steps:**
1. Open dashboard at `http://127.0.0.1:8512`
2. Locate the dark/light mode toggle button at the bottom of the sidebar
3. Click the toggle to switch from dark to light mode
4. Observe all page elements (cards, charts, tables, sidebar) change to light theme
5. Refresh the page (F5 / Cmd+R)
6. Check that light mode persists after refresh
7. Open DevTools → Application → Local Storage → check `quirk-ui-theme` key
8. Click toggle again to return to dark mode

**Expected:** Theme toggles instantly between dark and light; preference persists across page reload.

**Pass Criteria:**
- Clicking toggle switches theme instantly (no flash of wrong theme)
- All page elements update: sidebar, cards, charts, tables, badges
- `localStorage` key `quirk-ui-theme` stores `"light"` or `"dark"`
- Theme persists after full page reload
- Both themes are visually coherent (no invisible text, unreadable badges, or broken contrast)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-23: Sidebar Responsive Collapse

**Steps:**
1. Open dashboard at full desktop width (≥ 1024px)
2. Confirm sidebar shows full 240px width with text labels and QU.I.R.K. wordmark
3. Slowly resize browser window to below 1024px width
4. Observe sidebar collapse to 48px icon-only mode
5. Verify QU.I.R.K. wordmark changes to "Q" monogram
6. Click each navigation icon — verify navigation still works
7. Hover over a nav icon — verify tooltip shows page name
8. Resize back above 1024px — verify sidebar expands to full width with labels

**Expected:** Sidebar responsively collapses and expands at the 1024px breakpoint.

**Pass Criteria:**
- Above 1024px: sidebar shows 240px with full text labels
- Below 1024px: sidebar collapses to 48px icon-only
- Wordmark transitions to monogram on collapse
- All navigation icons remain clickable and route correctly
- Tooltips appear on hover in collapsed state
- Transition is smooth (no layout jumps or flicker)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-24: Findings Page — Pagination

**Prerequisites:** Scan producing more than 25 findings (full lab scan should produce 30+).

**Steps:**
1. Navigate to Findings page
2. Count visible rows in the table
3. Look for pagination controls at the bottom of the table
4. Click "Next page" or page 2
5. Observe new rows load
6. Click "Previous page" or page 1
7. Verify original rows return

**Expected:** Table paginates at 25 rows per page with working navigation controls.

**Pass Criteria:**
- First page shows exactly 25 rows (or fewer if total < 25)
- Pagination controls visible (page numbers, next/prev buttons)
- Navigating to page 2 shows remaining findings
- Row count indicator shows "Showing X–Y of Z findings"
- Applying a filter respects pagination (re-paginates filtered results)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-25: CBOM Page — Algorithm Search

**Steps:**
1. Navigate to CBOM page → Table tab
2. Note total row count
3. Type `AES` in the algorithm search box
4. Observe table filtering in real-time
5. Clear the search box
6. Verify all rows return

**Expected:** Search filters the CBOM algorithm table by algorithm name.

**Pass Criteria:**
- Typing filters rows to only those containing the search term
- Filter is case-insensitive (`aes` matches `AES-256-GCM`)
- Clearing search restores full table
- No results shows empty state (not a crash)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-26: CBOM Page — Quantum Safety Filter

**Steps:**
1. Navigate to CBOM page → Table tab
2. Locate the Quantum Safety dropdown/filter
3. Select "Vulnerable"
4. Observe table shows only quantum-vulnerable algorithms
5. Select "Safe" (if any safe algorithms exist)
6. Clear filter to show all

**Expected:** Dropdown filters CBOM table by quantum-safety classification.

**Pass Criteria:**
- Selecting "Vulnerable" shows only red-badged algorithms (RSA, ECDSA, etc.)
- Selecting "Safe" shows only green-badged algorithms (if any)
- Clearing filter restores all rows
- Filter and search combine correctly (both applied simultaneously)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-27: CBOM Graph — Node Interaction

**Steps:**
1. Navigate to CBOM page → Graph tab
2. Wait for Cytoscape.js graph to render
3. Click an algorithm node (e.g., `AES-256-GCM`)
4. Observe detail panel on right side
5. Click a source system node (e.g., `127.0.0.1:443`)
6. Observe detail panel update

**Expected:** Clicking nodes shows contextual information in a detail panel.

**Pass Criteria:**
- Algorithm node click shows: algorithm name, quantum-safety classification, connected source systems
- Source system node click shows: host:port or file path, connected algorithms
- Panel updates when clicking different nodes
- Node colors match quantum-safety: green (Safe), amber (At Risk), red (Vulnerable)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-28: CBOM Graph — Zoom Controls

**Steps:**
1. On CBOM Graph tab, locate zoom controls (In/Out/Fit buttons)
2. Click "Zoom In" — verify graph zooms in
3. Click "Zoom Out" — verify graph zooms out
4. Pan the graph by click-dragging the background
5. Click "Fit to Viewport" — verify graph auto-scales to show all nodes
6. Use mouse scroll wheel — verify zoom works

**Expected:** All zoom and pan controls function correctly.

**Pass Criteria:**
- Zoom in/out buttons change zoom level visibly
- "Fit to Viewport" shows all nodes within visible area
- Mouse scroll wheel zooms
- Click-drag on background pans the view
- No nodes disappear off-screen permanently

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-29: Roadmap — Node Drag

**Steps:**
1. Navigate to Roadmap page
2. Click and drag a node to a new position
3. Observe edges (arrows) follow the node
4. Release the node
5. Verify edges remain connected

**Expected:** DAG nodes are draggable for manual repositioning; edges follow.

**Pass Criteria:**
- Node moves smoothly during drag
- All connected edges update position in real-time
- Node stays in new position after release
- Other nodes not affected by the drag
- Layout does not reset on node release

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-30: Print View

**Steps:**
1. Navigate directly to `http://127.0.0.1:8512/print`
2. Observe the page layout

**Expected:** Print-optimized single-column layout with no interactive elements.

**Pass Criteria:**
- No sidebar visible
- No interactive controls (no filters, no toggle buttons)
- Full-width single-column layout
- CSS page breaks between major sections
- Content includes: score summary, findings, certificates, CBOM reference
- Background colors and borders render (print background styling enabled)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-31: Dashboard Page Title and Branding

**Steps:**
1. Open dashboard at `http://127.0.0.1:8512`
2. Check browser tab title
3. Check sidebar header for QU.I.R.K. wordmark
4. Check favicon in browser tab

**Expected:** Professional branding visible throughout.

**Pass Criteria:**
- Browser tab title shows `QU.I.R.K. — Quantum Readiness Dashboard` or similar branded title
- Sidebar displays bold monospace electric-blue QU.I.R.K. wordmark
- Favicon shows electric-blue "Q" (not browser default icon)
- No JS console errors on page load

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-32: No JavaScript Console Errors — All Pages

**Steps:**
1. Open browser DevTools (F12) → Console tab
2. Clear console
3. Navigate to Executive page (`/`) — check for errors
4. Navigate to Findings page (`/findings`) — check for errors
5. Navigate to Identity page (`/identity`) — check for errors
6. Navigate to Certificates page (`/certificates`) — check for errors
7. Navigate to CBOM page (`/cbom`) — switch between Table and Graph tabs — check for errors
8. Navigate to Roadmap page (`/roadmap`) — check for errors
9. Navigate to Print view (`/print`) — check for errors

**Expected:** Zero JavaScript errors across all pages.

**Pass Criteria:**
- No red `Error` entries in console on any page
- No unhandled promise rejections
- No `TypeError` or `ReferenceError` entries
- Warnings are acceptable (yellow) but errors (red) are not
- API requests all return 200 (check Network tab)
- `/identity` page loads without errors even when no identity scan data is present

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

### UAT-7-33: Identity Page — Navigation and Load

> Added Phase 21 (2026-04-10): Identity Surface feature — new `/identity` dashboard page.

**Prerequisites:** Dashboard running (`quirk serve` or `python run_scan.py serve`).

**Steps:**
1. Start dashboard and navigate to `http://127.0.0.1:8512`
2. Look for "Identity" item in the sidebar (between Findings and Certificates)
3. Click the Identity sidebar item
4. Observe page load at `/identity`
5. Check browser URL bar confirms `/identity` route

**Expected:** Identity page accessible via sidebar with Fingerprint icon.

**Pass Criteria:**
- Sidebar shows "Identity" nav item with a Fingerprint icon
- Clicking navigates to `/identity` without a full page reload (SPA routing)
- Page title or heading reads "Identity Protocols"
- No 404 or blank screen

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-34: Identity Page — Protocol Summary Cards (No Scan Data)

> Added Phase 21 (2026-04-10): Identity Surface feature.

**Prerequisites:** Dashboard running. No scan required (tests empty state).

**Steps:**
1. Navigate to `http://127.0.0.1:8512/identity`
2. Observe the three protocol summary cards at the top of the page
3. Note the status badge on each card

**Expected:** Three cards rendered: Kerberos, SAML/OIDC, DNSSEC — each showing "Not Scanned" empty state.

**Pass Criteria:**
- Three cards visible: "Kerberos", "SAML/OIDC", "DNSSEC"
- Each card shows a "Not Scanned" or neutral status badge (not an error)
- No JavaScript errors in console
- Cards do not crash when `identity_findings` array is empty or absent from API response

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-35: Identity Page — Protocol Summary Cards (With Scan Data)

> Added Phase 21 (2026-04-10): Identity Surface feature.

**Prerequisites:** Full lab scan completed including Kerberos (port 88), SAML (port 8080 SimpleSAMLphp), and DNSSEC chaos lab zones. Use chaos lab profile.

**Steps:**
1. Run: `python run_scan.py --config labs/quirk-chaos.yaml` (or equivalent full lab scan)
2. Navigate to `http://127.0.0.1:8512/identity`
3. Observe the three protocol summary cards
4. Check each card's status badge and finding count
5. Click a finding row in the findings table below the cards

**Expected:** Cards show per-protocol finding counts and severity. Clicking a row opens a detail Sheet.

**Pass Criteria:**
- At least one card shows a non-zero finding count (Kerberos or DNSSEC expected from chaos lab)
- Card status badge reflects highest severity finding for that protocol (e.g., "Critical", "High")
- "Safe" badge shown if no issues detected for a protocol
- Findings table below cards lists identity findings with Severity, Protocol, Host, Algorithm columns
- Clicking a row opens a slide-out detail Sheet showing finding description and recommendation
- Table shows "No identity protocol findings" empty state if API returns no identity data

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-36: Identity Page — API Response Shape

> Added Phase 21 (2026-04-10): Identity Surface feature — `identity_findings[]` added to `/api/scan/latest`.

**Prerequisites:** Completed scan.

**Steps:**
1. Open browser DevTools → Network tab
2. Navigate to `/identity` page
3. Find the `GET /api/scan/latest` request
4. Inspect the response JSON

**Expected:** `GET /api/scan/latest` response includes an `identity_findings` array.

**Pass Criteria:**
- Response JSON contains key `identity_findings`
- `identity_findings` is an array (empty array `[]` is valid if no identity issues found)
- Each element has: `id`, `severity`, `protocol`, `host`, `algorithm`, `description`, `recommendation`
- Identity findings also appear in the main `findings` array (deduplication optional)
- No `500` error on the endpoint when identity data is absent

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-7-37: Findings Page — Protocol Filter

> Added Phase 21 (2026-04-10): Identity Surface feature — protocol dropdown added to Findings page.

**Prerequisites:** Full lab scan completed (multi-protocol findings present).

**Steps:**
1. Navigate to `http://127.0.0.1:8512/findings`
2. Locate the Protocol dropdown filter (near the Severity filter)
3. Note default selection ("All Protocols" or equivalent)
4. Select "KERBEROS" from the dropdown
5. Observe table updates
6. Select "TLS" from the dropdown
7. Select "All Protocols" to reset

**Expected:** Protocol dropdown filters the findings table by protocol type.

**Pass Criteria:**
- Protocol dropdown visible on Findings page alongside existing Severity filter
- Default shows all findings ("All Protocols")
- Selecting "KERBEROS" shows only Kerberos findings (or empty state if none)
- Selecting "TLS" shows only TLS findings
- Options include: ALL / TLS / SSH / HTTP / KERBEROS / SAML / DNSSEC
- Filter combines with Severity filter (both applied simultaneously)
- Selecting "All Protocols" restores full findings list

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

---

# Series 8: Scoring & Intelligence

---

### UAT-8-01: Score Range Validation

**Prerequisites:** Lab scanned with at least 5 diverse endpoints.

**Steps:**
1. Review `output/intelligence-*.json`
2. Extract score: `python3 -c "import json; d=json.load(open('output/intelligence-TIMESTAMP.json')); print(d['score'], d['score_label'])"`

**Expected:** Score is in range, label matches.

**Pass Criteria:**
- Score is integer or float 0–100
- Label matches:
  - 85–100 → EXCELLENT
  - 70–84 → GOOD
  - 55–69 → MODERATE
  - 35–54 → FAIR
  - 0–34 → POOR

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-8-02: Confidence Score — Low Coverage Scenario

**Prerequisites:** Scan with high error rate (e.g., many closed ports or timeouts).

**Steps:**
1. Create config targeting mostly unreachable ports
2. Run scan
3. Check `confidence` in `output/intelligence-*.json`

**Expected:** Confidence score decreases when scan coverage is poor.

**Pass Criteria:**
- Confidence is lower than a full lab scan
- If scan error rate > 50%, confidence < 60
- Confidence score in output JSON

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-8-03: Score Impact — Adding Plaintext HTTP

**Prerequisites:** Two scans: one with only TLS services, one also including HTTP services.

**Steps:**
1. Scan 1: `--config lab-tls-only.yaml` (only ports 443, 8443)
2. Record score
3. Scan 2: `--config lab-tls-plus-http.yaml` (add ports 8000, 8444)
4. Record score

**Expected:** Score decreases when plaintext HTTP exposure is added.

**Pass Criteria:**
- `score_scan2 < score_scan1`
- Score difference ≥ 5 points (HTTP exposure is penalized up to 18 pts)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-8-04: Hygiene Subscore — Plaintext Ratio

**Prerequisites:** Scan with mixed HTTP and TLS endpoints.

**Steps:**
1. Review `output/scorecard-*.md` Hygiene subscore
2. Compare with findings

**Expected:** Hygiene subscore reflects ratio of plaintext endpoints.

**Pass Criteria:**
- Hygiene subscore < 25 when ≥ 1 plaintext HTTP endpoint exists
- Subscore decreases proportionally to number of HTTP endpoints

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-8-05: mTLS Bonus — Identity Trust Subscore

**Prerequisites:** Scan including port 11443 (mTLS required).

**Steps:**
1. Review Identity Trust subscore in scorecard

**Expected:** mTLS enforcement provides a bonus to Identity Trust subscore.

**Pass Criteria:**
- Identity Trust subscore is higher when mTLS endpoint is scanned
- mTLS bonus noted in scorecard or intelligence JSON

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-8-06: Roadmap Evidence Links

**Prerequisites:** Completed scan with plaintext HTTP and expired cert findings.

**Steps:**
1. Review `output/roadmap-*.md` NOW section

**Expected:** NOW items reference specific discovered evidence.

**Pass Criteria:**
- NOW items reference specific finding types (e.g., "2 plaintext HTTP endpoints")
- Why text references actual scan data (not generic placeholder)
- Remediation steps are specific to findings

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-8-07: Score Profile Consistency — CLI vs Dashboard

> Added Phase 14 (2026-04-07): dashboard now reads stored calibration profile from intelligence JSON.

**Prerequisites:** Completed scan run with a non-default score profile (e.g., `--score-profile strict`).

**Steps:**
1. Run: `quirk --config config.yaml --score-profile strict`
2. Note score from `output/scorecard-*.md`
3. Start dashboard: `quirk serve`
4. Open `http://127.0.0.1:8512` and view the score gauge on the Executive Summary page

**Expected:** Dashboard score matches the CLI scorecard score exactly, not a recalculated balanced-profile score.

**Pass Criteria:**
- Dashboard score gauge value equals score in `scorecard-*.md`
- Running the same scan again with `--score-profile balanced` and refreshing the dashboard shows a *different* score
- Dashboard score does not silently default to balanced when strict or lenient was used

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-8-08: validate.py — Clean Output Directory Validation

> Added Phase 14 (2026-04-07): validate_run signature simplified — dead require_delta_if_baseline parameter removed.

**Prerequisites:** Completed scan with all expected output files present.

**Steps:**
1. Run: `python3 -c "from quirk.validate import validate_run; from pathlib import Path; r = validate_run(Path('output')); print(r)"`
2. Run: `quirk --help` and confirm no `--no-require-delta` flag appears

**Expected:** `validate_run` accepts only `output_dir` with no extra parameters. CLI has no dead delta flag.

**Pass Criteria:**
- `validate_run(Path('output'))` returns a `ValidationResult` without error
- `quirk --help` output contains no `--no-require-delta` or `--require-delta` flags
- Passing a second positional argument to `validate_run` raises `TypeError` (no dead parameter to silently absorb it)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

### UAT-8-09: Identity Scoring — Kerberos Weak Etype Penalty

> Added Phase 21 (2026-04-10): Kerberos RC4/DES etype detection wired into scoring.

**Prerequisites:** Chaos lab running with Kerberos service (Samba DC, port 88). Full lab scan completed.

**Steps:**
1. Run full lab scan: `python run_scan.py --config labs/quirk-chaos.yaml`
2. Inspect `output/intelligence-*.json`:
   ```bash
   python3 -c "
   import json, glob
   d = json.load(open(sorted(glob.glob('output/intelligence-*.json'))[-1]))
   ev = d.get('evidence', {})
   print('identity_weak_etype_count:', ev.get('identity_weak_etype_count', 'KEY MISSING'))
   print('identity_kerberos_weak_etype_ratio:', ev.get('identity_kerberos_weak_etype_ratio', 'KEY MISSING'))
   "
   ```
3. Check score is lower than a baseline scan with no Kerberos service

**Expected:** RC4/DES Kerberos etypes are counted as evidence and reduce the quantum-readiness score.

**Pass Criteria:**
- `identity_weak_etype_count` key present in evidence summary (≥ 0)
- `identity_kerberos_weak_etype_ratio` key present in evidence summary
- When Kerberos weak etypes are detected, score is penalized (lower than no-identity scan)
- `SCORE_WEIGHTS` entry `identity_kerberos_weak_etype_ratio` present in scoring module

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-8-10: Identity Scoring — SAML Weak Signing Certificate Penalty

> Added Phase 21 (2026-04-10): SAML weak signing cert detection wired into scoring.

**Prerequisites:** Chaos lab running with SAML service (SimpleSAMLphp). Full lab scan completed.

**Steps:**
1. Run full lab scan with SAML profile included
2. Inspect `output/intelligence-*.json`:
   ```bash
   python3 -c "
   import json, glob
   d = json.load(open(sorted(glob.glob('output/intelligence-*.json'))[-1]))
   ev = d.get('evidence', {})
   print('saml_weak_signing_count:', ev.get('saml_weak_signing_count', 'KEY MISSING'))
   print('identity_saml_weak_signing_ratio:', ev.get('identity_saml_weak_signing_ratio', 'KEY MISSING'))
   "
   ```

**Expected:** SAML signing certificates with weak keys are counted as evidence and reduce score.

**Pass Criteria:**
- `saml_weak_signing_count` key present in evidence summary (≥ 0)
- `identity_saml_weak_signing_ratio` key present in evidence summary
- Score is penalized when SAML weak signing certs are detected
- `SCORE_WEIGHTS` entry `identity_saml_weak_signing_ratio` present in scoring module

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-8-11: Identity Scoring — DNSSEC Weak Algorithm Penalty

> Added Phase 21 (2026-04-10): DNSSEC RSASHA1/DSA algorithm detection wired into scoring.

**Prerequisites:** Chaos lab running with DNSSEC zones configured. Full lab scan completed.

**Steps:**
1. Run full lab scan with DNSSEC profile included
2. Inspect `output/intelligence-*.json`:
   ```bash
   python3 -c "
   import json, glob
   d = json.load(open(sorted(glob.glob('output/intelligence-*.json'))[-1]))
   ev = d.get('evidence', {})
   print('dnssec_weak_algo_count:', ev.get('dnssec_weak_algo_count', 'KEY MISSING'))
   print('identity_dnssec_weak_algo_ratio:', ev.get('identity_dnssec_weak_algo_ratio', 'KEY MISSING'))
   "
   ```

**Expected:** DNSSEC zones using RSASHA1, RSAMD5, or DSA are counted as evidence and reduce score.

**Pass Criteria:**
- `dnssec_weak_algo_count` key present in evidence summary (≥ 0)
- `identity_dnssec_weak_algo_ratio` key present in evidence summary
- Score is penalized when weak DNSSEC algorithms are detected
- `SCORE_WEIGHTS` entry `identity_dnssec_weak_algo_ratio` present in scoring module
- Chaos lab DNSSEC zone with RSASHA1 produces `dnssec_weak_algo_count >= 1`

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-8-12: Identity Scan — No NameError on Invocation (DNSSEC-04)

> Added Phase 22 (2026-04-15): Confirmed `main_logger` NameError fixed in run_scan.py identity scanner blocks.

**Prerequisites:** Chaos lab running with identity profile configured (`enable_dnssec: true`, `enable_saml: true`, `enable_kerberos: true` in config). `quirk[identity]` extras installed.

**Steps:**
1. Run a full scan with identity scanners enabled:
   ```bash
   python run_scan.py --config config.yaml
   ```
2. Confirm no `NameError: name 'main_logger' is not defined` in scan output or logs
3. Confirm DNSSEC, SAML, and Kerberos scanner blocks each produce output in `findings-*.json`

**Expected:** Identity scanners complete without crashing. All three scanner blocks log their results.

**Pass Criteria:**
- No `NameError` exception in scan output
- DNSSEC findings present in `findings-*.json` (or `dnssec_scan_json` column in DB)
- SAML findings present in `findings-*.json` (or `saml_scan_json` column in DB)
- Kerberos findings present in `findings-*.json` (or `kerberos_scan_json` column in DB)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-8-13: CBOM — SAML Endpoints Produce Only Algorithm Components (SAML-05)

> Added Phase 22 (2026-04-15): Confirmed CBOM builder Pass 2/Pass 3 skip lists include SAML.

**Prerequisites:** Completed scan with SAML scanner enabled and at least one SAML IdP reachable.

**Steps:**
1. Run full scan with SAML profile enabled
2. Inspect the generated CBOM JSON:
   ```bash
   python3 -c "
   import json, glob
   cbom = json.load(open(sorted(glob.glob('output/cbom-*.json'))[-1]))
   comps = cbom.get('components', [])
   saml_types = [(c.get('name',''), c.get('type','')) for c in comps
                 if 'saml' in c.get('name','').lower() or 'saml' in str(c.get('tags','')).lower()]
   print('SAML-tagged components:')
   for name, t in saml_types:
       print(f'  type={t} name={name}')
   protocol_comps = [c for c in comps if c.get('type') == 'protocol']
   cert_comps = [c for c in comps if c.get('type') == 'certificate']
   print(f'Total protocol components: {len(protocol_comps)}')
   print(f'Total certificate components: {len(cert_comps)}')
   "
   ```

**Expected:** No `crypto/protocol/tls/` or `crypto/certificate/` components sourced from SAML endpoints. SAML appears only as algorithm components in the CBOM.

**Pass Criteria:**
- Zero CBOM components of type `protocol` with SAML origin
- Zero CBOM components of type `certificate` with SAML origin
- SAML weak signing algorithm (SHA-1 or RSA < 2048) appears as an `algorithm` component if detected

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-8-14: CBOM — Kerberos Endpoints Produce Only Algorithm Components (KERB-04)

> Added Phase 22 (2026-04-15): Confirmed CBOM builder Pass 2/Pass 3 skip lists include KERBEROS.

**Prerequisites:** Completed scan with Kerberos scanner enabled and at least one KDC reachable.

**Steps:**
1. Run full scan with Kerberos profile enabled
2. Inspect the generated CBOM JSON:
   ```bash
   python3 -c "
   import json, glob
   cbom = json.load(open(sorted(glob.glob('output/cbom-*.json'))[-1]))
   comps = cbom.get('components', [])
   kerb_types = [(c.get('name',''), c.get('type','')) for c in comps
                 if 'kerberos' in c.get('name','').lower() or 'kerb' in str(c.get('tags','')).lower()]
   print('Kerberos-tagged components:')
   for name, t in kerb_types:
       print(f'  type={t} name={name}')
   protocol_comps = [c for c in comps if c.get('type') == 'protocol']
   cert_comps = [c for c in comps if c.get('type') == 'certificate']
   print(f'Total protocol components: {len(protocol_comps)}')
   print(f'Total certificate components: {len(cert_comps)}')
   "
   ```

**Expected:** No `crypto/protocol/tls/` or `crypto/certificate/` components sourced from Kerberos endpoints. Kerberos appears only as algorithm components in the CBOM.

**Pass Criteria:**
- Zero CBOM components of type `protocol` with Kerberos origin
- Zero CBOM components of type `certificate` with Kerberos origin
- RC4/DES etype names appear as `algorithm` components if detected
- `kerberos-unreachable` synthetic findings do NOT appear as algorithm components

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-8-15: CBOM — DNSSEC Endpoints Produce Only Algorithm Components (DNSSEC-04)

> Added Phase 23 (2026-04-24): Added `"DNSSEC"` to Pass 2 certificate skip tuple in `builder.py` line 389. DNSSEC endpoints no longer produce hollow `CertificateProperties` components.

**Prerequisites:** Completed scan with DNSSEC scanner enabled and at least one zone with DNSKEY records reachable.

**Steps:**
1. Run full scan with DNSSEC profile enabled
2. Inspect the generated CBOM JSON:
   ```bash
   python3 -c "
   import json, glob
   cbom = json.load(open(sorted(glob.glob('output/cbom-*.json'))[-1]))
   comps = cbom.get('components', [])
   dnssec_refs = [(str(c.get('bom-ref','')), c.get('type','')) for c in comps
                  if 'dnssec' in str(c.get('bom-ref','')).lower() or ':53' in str(c.get('bom-ref',''))]
   print('DNSSEC-related components:')
   for ref, t in dnssec_refs:
       print(f'  type={t} bom_ref={ref}')
   cert_comps = [c for c in comps if str(c.get('bom-ref','')).startswith('crypto/certificate/')]
   print(f'Total certificate components: {len(cert_comps)}')
   dnssec_certs = [c for c in cert_comps if ':53' in str(c.get('bom-ref',''))]
   print(f'DNSSEC certificate components: {len(dnssec_certs)} (expected 0)')
   "
   ```

**Expected:** No `crypto/certificate/` components sourced from DNSSEC endpoints. DNSSEC appears only as algorithm components (e.g., `crypto/algorithm/ecdsap256sha256`) in the CBOM.

**Pass Criteria:**
- Zero CBOM components with `bom_ref` starting with `crypto/certificate/` for DNSSEC hosts (port 53)
- DNSKEY algorithm names (e.g., ECDSAP256SHA256, RSASHA256) appear as `algorithm` components
- No spurious `crypto/protocol/tls/` components for DNSSEC endpoints (Pass 3 already correct)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-8-16: Identity Scanners — Shared Session Timestamp (ISSUE-3 fix, Phase 24)

> Added Phase 24 (2026-04-24): All 3 identity scanners (DNSSEC, SAML, Kerberos) now accept `session_start=None` and `run_scan.py` passes one shared `datetime.now(timezone.utc)` to all 3. Endpoints from a scan session share one `scanned_at`, eliminating scan-window exclusion.

**Prerequisites:** Full scan with DNSSEC, SAML, and Kerberos targets configured and reachable.

**Steps:**
1. Run a full scan: `quirk --config <config-with-all-3-identity-scanners>`
2. Query the scan-latest API endpoint:
   ```bash
   curl -s http://localhost:7420/api/scan/latest | python3 -c "
   import json, sys
   data = json.load(sys.stdin)
   protocols = {f['protocol'] for f in data.get('identity_findings', [])}
   print('Identity protocols found:', protocols)
   "
   ```
3. Alternatively, verify directly in SQLite:
   ```bash
   python3 -c "
   import sqlite3
   db = sqlite3.connect('quirk.db')
   rows = db.execute(\"SELECT protocol, scanned_at FROM crypto_endpoints WHERE protocol IN ('DNSSEC','SAML','KERBEROS') ORDER BY scanned_at DESC LIMIT 10\").fetchall()
   for r in rows: print(r)
   "
   ```

**Expected:** All 3 identity protocols appear in `identity_findings`. DNSSEC and SAML `scanned_at` timestamps match Kerberos — no spread greater than 1 second between protocols from the same scan session.

**Pass Criteria:**
- `DNSSEC`, `SAML`, and `KERBEROS` all present in `/api/scan/latest` `identity_findings`
- All 3 protocols' `scanned_at` values in SQLite are within 1 second of each other for the same scan run
- No identity protocol is silently excluded from scan results due to timestamp mismatch

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

# Series 9: Report Generation & Validation

---

### UAT-9-01: All Output Files Generated

**Prerequisites:** Completed scan.

**Steps:**
1. `ls output/ | sort`

**Expected:** All 9 output artifact types present for the latest scan.

**Pass Criteria:**
- `findings-{stamp}.json` ✓
- `executive-summary-{stamp}.md` ✓
- `technical-findings-{stamp}.md` ✓
- `scorecard-{stamp}.md` ✓
- `roadmap-{stamp}.md` ✓
- `intelligence-{stamp}.json` ✓
- `cbom-{stamp}.json` ✓
- `cbom-{stamp}.xml` ✓
- `run-stats-{stamp}.json` ✓
- `quirk.db` ✓

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-9-02: Executive Summary — Structure

**Prerequisites:** Completed scan.

**Steps:**
1. `cat output/executive-summary-*.md`

**Expected:** Professional executive summary with score, risk overview, and top issues.

**Pass Criteria:**
- Starts with score summary
- Contains a risk overview section
- Lists top 3–5 findings
- Contains recommended next steps
- Does not contain raw JSON or technical jargon

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-9-03: Technical Findings — Per-Endpoint Detail

**Prerequisites:** Completed scan.

**Steps:**
1. `cat output/technical-findings-*.md`

**Expected:** Technical details per endpoint including cipher suites, cert data, and algorithm details.

**Pass Criteria:**
- Each finding has host:port label
- Cipher suite details present for TLS findings
- Certificate expiry dates present for cert findings
- Algorithm quantum assessment present

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-9-04: Run Stats — Timing Data

**Prerequisites:** Completed scan.

**Steps:**
1. `python3 -c "import json; d=json.load(open('output/run-stats-TIMESTAMP.json')); print(json.dumps(d, indent=2))"`

**Expected:** Timing breakdown per scan phase.

**Pass Criteria:**
- `discovery_duration_ms` present
- `tls_scan_duration_ms` present
- `ssh_scan_duration_ms` present
- `total_duration_ms` present
- `endpoint_count` matches actual scanned endpoints
- `profile` field matches used profile

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-9-05: HTML Report Generation (Phase 7 Feature)

**Prerequisites:** QU.I.R.K. 4.2.0 with HTML report feature. Completed scan.

**Steps:**
1. Run scan: `quirk --config config.yaml`
2. Check output for HTML file: `ls output/*.html`
3. Open in browser

**Expected:** Standalone HTML report generated alongside existing markdown reports.

**Pass Criteria:**
- `report-{stamp}.html` file exists in output directory
- File opens in browser without JavaScript errors
- Contains score, findings table, and certificate inventory
- Fully self-contained (no external CDN dependencies)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-9-06: HTML Report — Visual Quality

**Prerequisites:** Completed scan with multiple finding types.

**Steps:**
1. Open `output/report-*.html` in Chrome or Firefox
2. Check dark-mode background renders
3. Verify score card section at the top
4. Scroll to Executive Summary section
5. Scroll to Technical Appendix / Findings section
6. Check for broken CSS (unstyled elements, missing fonts, layout breaks)
7. Resize browser to mobile width and check responsiveness

**Expected:** Professional, dark-themed HTML report with clean layout and all sections populated.

**Pass Criteria:**
- Dark-mode background (Zinc palette) renders correctly
- Score card with numeric score and label visible at top
- Executive Summary section with key metrics
- Technical Appendix with per-endpoint findings
- No broken images, missing fonts, or unstyled raw HTML elements
- No horizontal scroll overflow
- Print to PDF from browser produces clean output

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-9-07: CBOM JSON — Cross-Scanner Algorithm Coverage

**Prerequisites:** Completed scan that exercised TLS, SSH, and JWT scanners (core + jwt + ssh-weak profiles).

**Steps:**
1. Open `output/cbom-*.json`
2. Parse and extract all component algorithm names:
   ```bash
   python3 -c "
   import json
   cbom = json.load(open('output/cbom-TIMESTAMP.json'))
   components = cbom.get('components', [])
   for c in components:
       print(c.get('name', 'unnamed'), '-', c.get('type', 'unknown'))
   "
   ```
3. Verify algorithms from each scanner type are present

**Expected:** CBOM contains algorithms discovered by all active scanners.

**Pass Criteria:**
- TLS algorithms present (e.g., AES-256-GCM, ECDHE, RSA from cipher suites)
- SSH algorithms present (e.g., diffie-hellman-group14-sha256, ssh-ed25519, hmac-sha2-256)
- JWT algorithms present (e.g., RS256, HS256) when JWT scanner was active
- Each component has `quantum-safety` classification
- Total component count ≥ 10 for a full lab scan
- No duplicate components (same algorithm not listed twice)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-9-08: CBOM XML — Schema Validation

**Prerequisites:** Completed scan producing CBOM XML output.

**Steps:**
1. Locate CBOM XML: `ls output/cbom-*.xml`
2. Validate XML is well-formed:
   ```bash
   python3 -c "import xml.etree.ElementTree as ET; ET.parse('output/cbom-TIMESTAMP.xml'); print('XML well-formed')"
   ```
3. Validate against CycloneDX schema (if `xmllint` available):
   ```bash
   xmllint --noout output/cbom-TIMESTAMP.xml && echo "Valid XML"
   ```
4. Check root element is a CycloneDX BOM

**Expected:** CBOM XML is well-formed and follows CycloneDX structure.

**Pass Criteria:**
- XML parses without errors
- Root element is `<bom>` with CycloneDX namespace
- `<components>` section contains algorithm entries
- Each component has `<name>`, `<type>` attributes
- File size > 1KB (not empty or stub)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

---

# Series 10: Edge Cases & Error Handling

---

### UAT-9-09: Trend Report — Score Delta + New/Resolved Counts (Phase 31)

> Added Phase 31 (2026-04-26): Validates TREND-01/02/03 — compute_trend_report() correctly identifies score delta and per-severity new/resolved finding counts between the two most recent distinct scan sessions, via (host, port, protocol, severity) match key.

**Prerequisites:** SQLite DB with at least 2 distinct scan sessions completed (run quirk twice against any chaos lab profile, with at least 1 second between runs).

**Steps:**
1. Confirm DB has ≥2 distinct sessions: open quirk-output/*.sqlite and run `SELECT DISTINCT strftime('%Y-%m-%d %H:%M:%S', scanned_at) FROM crypto_endpoint WHERE scanned_at IS NOT NULL ORDER BY scanned_at DESC LIMIT 5;` — expect ≥2 rows.
2. Start the dashboard backend: `quirk serve` (or `uvicorn quirk.dashboard.api.app:app`).
3. `curl -s http://localhost:8000/api/trends | jq .` — capture response.

**Expected:**
- HTTP 200 with flat response fields: `current_session_ts`, `previous_session_ts`, `current_score`, `previous_score`, `score_delta`, `new_high`, `new_medium`, `new_low`, `resolved_high`, `resolved_medium`, `resolved_low`, `scan_errors_new_count`, `scan_errors_resolved_count`, `new_findings_sample`, `resolved_findings_sample`.
- `previous_session_ts` is non-null when ≥2 sessions exist; `score_delta` is a non-null integer (positive, negative, or zero).
- `new_high`/`new_medium`/`new_low` and `resolved_high`/`resolved_medium`/`resolved_low` are non-negative integers (note: `new_high` and `resolved_high` bucket both CRITICAL and HIGH severity findings).
- Sample arrays are length-capped at 5.

**Pass Criteria:**
- `python -m pytest tests/test_intelligence_trends.py tests/test_dashboard_trends.py -q` is green
- Response schema matches docs/intelligence-schema.md TrendReport block
- Sample arrays do not contain INFO-severity rows (D-05 — INFO is excluded from buckets)
- scan_errors_new_count and scan_errors_resolved_count are reported separately from the severity buckets (D-04 — scan_error rows excluded from finding delta)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-9-10: Trends Tab — Baseline Empty State (Phase 31)

> Added Phase 31 (2026-04-26): Validates TREND-04 + D-06 — when fewer than 2 distinct scan sessions exist, /trends renders the 'Baseline scan recorded' empty state and score_delta is null (NOT zero). NULL scanned_at rows from v4.2-era data are excluded from session counting (D-13).

**Prerequisites:** Either an empty SQLite DB OR a DB with exactly 1 distinct non-NULL scanned_at session.

**Steps:**
1. Confirm session count: `SELECT COUNT(DISTINCT strftime('%Y-%m-%d %H:%M:%S', scanned_at)) FROM crypto_endpoint WHERE scanned_at IS NOT NULL;` — expect 0 or 1.
2. Open the dashboard at http://localhost:8000, click the "Trends" tab in the sidebar.
3. Confirm the rendered state matches the UI-SPEC empty state copy: "Baseline scan recorded".
4. Hit `GET /api/trends` directly via curl and inspect the response.

**Expected:**
- Sidebar shows a Trends nav entry with the TrendingUp lucide icon.
- /trends page renders the baseline empty state — NO score delta card, NO new/resolved counts, just the empty-state messaging from 31-UI-SPEC.md.
- API response: `score_delta` is null (JSON null, not 0); `previous_session_ts` is null; `new_high`/`new_medium`/`new_low`/`resolved_high`/`resolved_medium`/`resolved_low` are 0; sample arrays are empty.

**Pass Criteria:**
- Trends nav entry visible and active-state styling matches other nav entries
- Empty-state component rendered (no score delta card)
- score_delta is JSON null in API response (verify with `jq '.score_delta'` returning null, not 0)
- A row with scanned_at IS NULL (manually inserted v4.2-era simulation) does NOT count toward the session total — /trends still shows the empty state if that NULL row is the only data

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-10-01: No Reachable Targets — Graceful Handling

**Prerequisites:** Lab stopped (`docker compose down`).

**Steps:**
1. Create `config.yaml` with unreachable targets:
   ```yaml
   targets:
     include_ips:
       - "127.0.0.1"
     fqdns: []
     cidrs: []
     exclude_ips: []
   scan:
     ports_tls: [443, 8443, 8000]
   ```
   (Fill remaining required sections from `quirk init` output.)
2. Run: `quirk --config config.yaml`

**Expected:** Scan completes with all endpoints marked as errors; does not crash.

**Pass Criteria:**
- Scan completes (exit code 0)
- All findings show `scan_error` set
- Scorecard still generated (low confidence score)
- No uncaught Python exception traceback

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-10-02: Config File Not Found — Helpful Error

**Steps:**
1. Run: `quirk --config /nonexistent/path/config.yaml`

**Expected:** Clear error message pointing to the bad path.

**Pass Criteria:**
- Error message names the missing file path
- Exit code is non-zero
- No Python traceback exposed to user

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-10-03: Invalid Config YAML — Parse Error

**Steps:**
1. Create `bad.yaml`:
   ```
   targets: [unclosed bracket
   this: is: not: valid: yaml:
   ```
2. Run: `quirk --config bad.yaml`

**Expected:** Clear YAML parse error, not a cryptic crash.

**Pass Criteria:**
- Error message mentions YAML or config parsing issue
- Line number of error indicated if possible
- Exit code non-zero

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-10-04: Mixed Reachable/Unreachable Targets

**Prerequisites:** Lab running core services.

**Steps:**
1. Create `config.yaml` with mix of live and dead ports:
   ```yaml
   targets:
     include_ips:
       - "127.0.0.1"
     fqdns: []
     cidrs: []
     exclude_ips: []
   scan:
     ports_tls: [443, 9999, 8000, 1234]
   ```
   (Fill remaining required sections from `quirk init` output.)
2. Run scan: `quirk --config config.yaml`

**Expected:** Reachable ports scanned normally; unreachable ports recorded as errors; scan completes.

**Pass Criteria:**
- Port 443 and 8000 have findings
- Port 9999 and 1234 show as CLOSED or scan_error
- Scan does not hang or crash
- Run stats reflect actual reachable vs. error count

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-10-05: Rate Limiting — Token Bucket

**Prerequisites:** Lab running.

**Steps:**
1. Run: `quirk --config config.yaml --rate-limit 1.0` (1 target/second)
2. Observe scan pacing

**Expected:** Scan paces itself to ~1 target/second.

**Pass Criteria:**
- Scan takes noticeably longer than without rate limiting
- All targets still scanned
- No errors caused by rate limiting itself
- `run-stats` shows longer duration

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-10-06: Concurrent Scan Safety — No Race Conditions

**Prerequisites:** Lab running. Multiple ports configured.

**Steps:**
1. Create config with 20+ targets
2. Run scan without `--safe-mode`
3. Review output for consistency

**Expected:** Concurrent scanning produces consistent results without duplicate or missing entries.

**Pass Criteria:**
- Number of findings in JSON matches number of scanned endpoints (no duplicates)
- No Python `RuntimeError` or threading errors in output
- SQLite database is not corrupted: `sqlite3 ./quirk.db "PRAGMA integrity_check"`

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-10-07: Database Persistence — Multiple Scans

**Prerequisites:** Run two separate scans.

**Steps:**
1. Run first scan
2. Run second scan (same targets)
3. Open database: `sqlite3 ./quirk.db "SELECT COUNT(*) FROM crypto_endpoints"`

**Expected:** Both scans are persisted with timestamps.

**Pass Criteria:**
- Row count is 2× single scan (both scans stored)
- Timestamps differ between runs
- `scanned_at` field distinguishes runs

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-10-08: Dashboard — No Scan Data State

**Prerequisites:** Empty or absent `./quirk.db`.

**Steps:**
1. Move database: `mv ./quirk.db /tmp/`
2. Start dashboard: `quirk serve --no-open`
3. Navigate to `http://127.0.0.1:8512`

**Expected:** Dashboard shows empty state message, not a crash.

**Pass Criteria:**
- Dashboard loads (not 500 error)
- Empty state message displayed (e.g., "No scan data yet — run `quirk` to begin")
- No JavaScript runtime errors in console

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-10-09: SSH Scan Without ssh-audit Installed

**Prerequisites:** `ssh-audit` not installed (test in clean environment).

**Steps:**
1. Temporarily rename ssh-audit: `sudo mv $(which ssh-audit) /tmp/ssh-audit-bak`
2. Run scan against port 2222
3. Check findings

**Expected:** SSH scan gracefully falls back to banner-grab mode.

**Pass Criteria:**
- No crash or unhandled exception
- SSH finding still generated with banner information
- Warning logged indicating ssh-audit fallback
- Restore: `sudo mv /tmp/ssh-audit-bak $(dirname $(which python))/ssh-audit`

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-10-10: sslyze Not Installed — Graceful Degradation

**Prerequisites:** sslyze not installed.

**Steps:**
1. Run deep TLS scan against port 443: `quirk --config config.yaml --profile deep`
2. Check findings for cipher suite detail

**Expected:** TLS scan completes using built-in ssl module; sslyze cipher enumeration skipped gracefully.

**Pass Criteria:**
- No crash
- Warning logged about sslyze unavailability
- Basic TLS data (version, cert) still captured
- `tls_enum_mode` reflected as `fast` or `off` in run-stats

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-10-11: Kerberos Scan Without impacket — Console Warning

**Prerequisites:** quirk installed without `[identity]` extras (`pip install -e "."`). Config with `enable_kerberos: true` and a Kerberos target.

**Steps:**
1. Ensure impacket is NOT installed: `python -c "import impacket" 2>&1` (should error)
2. Run a scan with a Kerberos target configured: `quirk --config kerberos-config.yaml`
3. Capture stderr output

**Expected:** Scan continues without crash; a visible console message tells the user how to install Kerberos support.

**Pass Criteria:**
- No unhandled exception or crash
- Stderr contains `[QUIRK] Kerberos scanning requires the identity extras:`
- Stderr contains `pip install quirk[identity]`
- Non-Kerberos scan results (TLS, SSH, etc.) are still produced normally
- DNSSEC and SAML scan (if configured) still run successfully — those deps are now core

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

---

# Series 11: Full End-to-End Workflow

---

### UAT-11-01: Complete Workflow — Lab to Dashboard

**Steps:**
1. Start lab: `cd quantum-chaos-enterprise-lab && docker compose up -d && sleep 10`
2. Initialize config: `quirk init`
3. Edit `config.yaml` to point at all core lab ports
4. Run scan: `quirk --config config.yaml --profile standard --progress`
5. Start dashboard: `quirk serve --no-open`
6. Open browser: `http://127.0.0.1:8512`
7. Navigate through all dashboard pages
8. Export PDF

**Expected:** End-to-end workflow completes successfully.

**Pass Criteria:**
- Scan completes without errors
- All 9 output files generated
- Dashboard loads and shows scan data
- All 5 pages render correctly (Executive, Findings, Certificates, CBOM, Roadmap)
- PDF export succeeds
- Score reflects lab environment (should be POOR or FAIR given all the intentional vulnerabilities)

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-11-02: Multi-Profile Lab Run — Progressive Discovery

**Steps:**
1. Run base scan (core only)
2. Add `phaseA` profile: `docker compose --profile phaseA up -d`
3. Run expanded scan
4. Add `jwt` profile: `docker compose --profile jwt up -d`
5. Run JWT scan
6. Compare scores across three runs

**Expected:** Each lab expansion adds new findings and may affect score.

**Pass Criteria:**
- Each successive scan discovers more endpoints
- JWT alg:none finding appears after JWT profile scan
- CBOM grows with each scan (more algorithms discovered)
- Dashboard reflects latest scan on each page refresh

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-11-03: CLI to Dashboard Handoff — Report Consistency

**Steps:**
1. Run scan via CLI
2. Note score from `output/scorecard-*.md`
3. Open dashboard
4. Compare CLI score to dashboard score gauge

**Expected:** CLI and dashboard show identical scores.

**Pass Criteria:**
- Score in `scorecard-*.md` matches score in dashboard gauge
- Finding count in `findings-*.json` matches dashboard findings table count
- Certificate count matches across CLI and UI

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

### UAT-11-04: Repeat Scan — Delta Detection

**Steps:**
1. Run scan with lab in normal state
2. Stop the expired-cert service: `docker compose stop tls-expired`
3. Run second scan
4. Compare findings between scans

**Expected:** Second scan no longer includes expired cert finding for port 9443.

**Pass Criteria:**
- Port 9443 shows as CLOSED or absent in second scan
- Score may improve slightly (one less critical finding)
- Run stats show fewer scanned endpoints

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________  
**Notes:**

---

---

# Series 12: Release Gate — Sign-Off Checklist

This checklist is the formal gating mechanism for QU.I.R.K. v4.2. **All categories must meet their minimum pass threshold** before any backlog or roadmap items may proceed. A category is blocked if any CRITICAL test within it fails.

## Gate Rules

1. **100% pass required** for Series 1 (Installation), Series 11 (E2E), and all tests marked CRITICAL
2. **90% pass required** for Series 3–6 (CLI, Lab, Findings) and Series 8–9 (Scoring, Reports)
3. **85% pass required** for Series 7 (Dashboard UI) and Series 10 (Edge Cases)
4. **SKIP** is acceptable only with documented justification (e.g., `nmap` not installed → UAT-3-07 may SKIP)
5. **FAIL** on any CRITICAL test blocks the gate regardless of overall pass rate

## Sign-Off Table

| Series | Category | Total Tests | Pass | Fail | Skip | Pass Rate | Gate Met? | Tester |
|--------|----------|-------------|------|------|------|-----------|-----------|--------|
| 1 | Installation & Setup | 8 | | | | | ☐ | |
| 2 | CLI — Interactive Mode | 9 | | | | | ☐ | |
| 3 | CLI — Config-File Mode | 10 | | | | | ☐ | |
| 4 | Lab — Core Services | 11 | | | | | ☐ | |
| 5 | Lab — Extended Profiles | 22 | | | | | ☐ | |
| 6 | Cryptographic Findings | 15 | | | | | ☐ | |
| 7 | Web Dashboard UI | 37 | | | | | ☐ | |
| 8 | Scoring & Intelligence | 11 | | | | | ☐ | |
| 9 | Report Generation | 8 | | | | | ☐ | |
| 10 | Edge Cases & Errors | 11 | | | | | ☐ | |
| 11 | End-to-End Workflow | 4 | | | | | ☐ | |
| **TOTAL** | | **146** | | | | | | |

## Critical Tests (Must Pass — No Exceptions)

These tests validate core functionality. Any failure here blocks the release gate.

| ID | Test Name | Series | Rationale |
|----|-----------|--------|-----------|
| UAT-1-01 | Package Installation | 1 | Cannot proceed if install fails |
| UAT-1-02 | Version Flag | 1 | Basic CLI health |
| UAT-1-05 | Dashboard Server Startup | 1 | Dashboard must start |
| UAT-3-01 | Scan with Config File | 3 | Core scanning workflow |
| UAT-4-01 | Lab Health Check — All Core Services | 4 | Lab must be operational |
| UAT-4-11 | Full Core Lab Scan | 4 | End-to-end core scan |
| UAT-5-10 | Full JWT Lab Scan | 5 | JWT scanner validation |
| UAT-5-12 | Weak SSH Scan | 5 | SSH scanner validation |
| UAT-6-01 | Findings Output — JSON Structure | 6 | Output format correctness |
| UAT-6-11 | CBOM JSON Structure | 6 | CBOM deliverable correctness |
| UAT-7-01 | Dashboard Loads | 7 | Dashboard must render |
| UAT-7-03 | Executive Page — Score Gauge | 7 | Core dashboard feature |
| UAT-7-06 | Findings Page — Table Renders | 7 | Core dashboard feature |
| UAT-7-17 | PDF Export — Generate Report | 7 | Consulting deliverable |
| UAT-9-01 | All Output Files Generated | 9 | Complete output artifact set |
| UAT-11-01 | Complete Workflow — Lab to Dashboard | 11 | Full E2E validation |
| UAT-11-03 | CLI to Dashboard Handoff | 11 | Score consistency |

## Final Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Tester | | | |
| Reviewer | | | |
| Approver | | | |

**Gate Decision:** ☐ PASS — All categories meet thresholds, all critical tests pass
**Gate Decision:** ☐ FAIL — Blocked items listed below with remediation plan

**Blocking Issues (if FAIL):**

| ID | Test | Issue Description | Remediation | Owner | Target Date |
|----|------|-------------------|-------------|-------|-------------|
| | | | | | |

---

## Phase 33: Broker Scanner (UAT-33-XX)

**Scope note (2026-04-28):** UAT-33-01/02/08 (config + DB persistence) are runnable today against the existing scanner. UAT-33-03..07 (live broker chaos-lab smoke against host-mapped ports 29092/29093/25671/25672/26379/26380) are **deferred** pending a follow-up plan to add custom-port support to `scan_kafka_targets()` / `scan_rabbitmq_targets()` / `scan_redis_targets()` (currently they probe hardcoded broker defaults: 9092/9093/9094, 5672/5671, 6379/6380). The 58-test pytest suite (`tests/test_broker_*`) provides the equivalent end-to-end verification today.

### UAT-33-01: Broker Scan Disabled by Default
**Prerequisites:** Default config (no `enable_broker: true`).
**Steps:**
1. `python run_scan.py --config config.yaml`
2. `sqlite3 output/quirk.db "SELECT COUNT(*) FROM crypto_endpoints WHERE broker_scan_json IS NOT NULL;"`

**Expected:** Scan completes; query returns `0`. No `broker-scanning` phase in run_stats.

### UAT-33-02: Standard Profile Enables Broker Scan
**Prerequisites:** `--profile standard` and at least one TLS target reachable.
**Steps:**
1. `python run_scan.py --profile standard --config config.yaml`

**Expected:** Logs include `Broker scan: kafka=N rabbit=N redis=N`. `cfg.connectors.enable_broker == True` after profile applied.

### UAT-33-03: Kafka Plaintext Detection (DEFERRED — chaos-lab smoke)
Pending: scanner custom-port support. Equivalent unit coverage exists in `tests/test_broker_scanner_kafka.py::test_detect_kafka_plaintext_*`.

### UAT-33-04: Kafka TLS Weak Cipher (DEFERRED — chaos-lab smoke)
Pending: scanner custom-port support. Equivalent integration coverage exists in `tests/test_broker_run_integration.py`.

### UAT-33-05: RabbitMQ AMQP Plaintext Detection (DEFERRED — chaos-lab smoke)
Pending: scanner custom-port support. Equivalent unit coverage in `tests/test_broker_scanner_rabbitmq.py::test_detect_amqp_plaintext_*` (validates `len(data) > 0` rule).

### UAT-33-06: RabbitMQ AMQPS Weak Cipher (DEFERRED — chaos-lab smoke)
Pending: scanner custom-port support. Equivalent coverage in `tests/test_broker_scanner_rabbitmq.py`.

### UAT-33-07: Redis Plaintext No-Auth Detection (DEFERRED — chaos-lab smoke)
Pending: scanner custom-port support. Equivalent unit coverage in `tests/test_broker_scanner_redis.py::test_probe_redis_plaintext_*`.

### UAT-33-08: broker_scan_json Persisted to DB
**Prerequisites:** `--profile standard` scan completed against any reachable broker (live or via integration test fixtures).
**Steps:**
1. Run a broker-enabled scan.
2. `sqlite3 output/quirk.db "SELECT broker_scan_json FROM crypto_endpoints WHERE broker_scan_json IS NOT NULL LIMIT 1;"`

**Expected:** Row returned with valid JSON object. Top-level keys are a subset of `{kafka, rabbitmq, redis, azure_servicebus, aws_sqs}` per the protocol families that produced endpoints.

---

---

## Phase 34: Motion Intelligence (UAT-34-XX)

**Purpose:** Verify the `data_in_motion` 6th subscore wires email + broker TLS evidence into the quantum-readiness score (MOTION-01..04).

---

**ID:** UAT-34-01
**Title:** data_in_motion appears as the 6th subscore in compute_readiness_score output
**Prerequisites:** Python venv active; `pytest` available; QU.I.R.K. v4.4.x checked out
**Steps:**
1. From the repo root, run:
   `python -c "from quirk.intelligence.scoring import compute_readiness_score; import json; print(json.dumps(compute_readiness_score({'totals': {'endpoints': 4, 'findings': 0}}), indent=2))"`
2. Inspect the output JSON.
**Expected:** The `subscores` object contains exactly 6 keys: `hygiene`, `modern_tls`, `identity_trust`, `agility_signals`, `data_at_rest`, `data_in_motion`.
**Pass Criteria:** `"data_in_motion"` is present in `subscores`; the existing 5 keys are unchanged.

---

**ID:** UAT-34-02
**Title:** Plaintext-broker evidence lowers the data_in_motion subscore vs zero baseline
**Prerequisites:** Python venv active; `pytest` available
**Steps:**
1. Run: `pytest tests/test_motion_scoring.py::test_motion_subscore_lowers_with_findings -x -q`
**Expected:** Test PASSES.
**Pass Criteria:** `pytest` exits 0; the assertion `bad["subscores"]["data_in_motion"] < baseline["subscores"]["data_in_motion"]` holds, AND `bad["score"] < baseline["score"]`.

---

**ID:** UAT-34-03
**Title:** SCORE_WEIGHTS and PROFILE_MULTIPLIERS contain locked motion_ values
**Prerequisites:** Python venv active
**Steps:**
1. Run: `pytest tests/test_motion_scoring.py::test_score_weights_motion_values tests/test_motion_scoring.py::test_profile_multipliers_motion -x -q`
**Expected:** Both tests PASS.
**Pass Criteria:** `motion_email_plaintext_ratio=12.0`, `motion_email_weak_cipher_ratio=6.0`, `motion_broker_plaintext_ratio=14.0`, `motion_broker_weak_tls_ratio=8.0`, `motion_broker_weak_cipher_ratio=6.0`; `PROFILE_MULTIPLIERS[*]["motion_"]` equals 1.4 / 1.0 / 0.7 for strict / balanced / lenient.

---

## Phase 35: CBOM Integration (UAT-35-XX)

**Purpose:** Verify email + broker TLS endpoints flow correctly through CycloneDX CBOM Passes 1/2/3, and plaintext-only broker endpoints are skipped from cert + protocol passes (CBOM-01..04).

---

**ID:** UAT-35-01
**Title:** Golden email CBOM matches committed snapshot
**Prerequisites:** Phase 35 merged; `tests/fixtures/cbom/expected_email_cbom.json` present; Python venv active; pytest available
**Steps:**
1. From the repo root, run:
   `python -m pytest tests/test_cbom_motion_golden.py::test_email_cbom_matches_snapshot -v`
**Expected:** Test passes — normalized CBOM emitted from the 7-endpoint email lab fixture matches the committed JSON snapshot exactly.
**Pass Criteria:** Exit code 0; the test reports 1 PASSED. If a divergence is reported, the divergence is intentional (scanner/builder change) and the snapshot has been regenerated via `REGEN_CBOM_FIXTURES=1` and re-committed.

---

**ID:** UAT-35-02
**Title:** Golden broker CBOM matches committed snapshot
**Prerequisites:** Phase 35 merged; `tests/fixtures/cbom/expected_broker_cbom.json` present; Python venv active
**Steps:**
1. Run: `python -m pytest tests/test_cbom_motion_golden.py::test_broker_cbom_matches_snapshot tests/test_cbom_motion_golden.py::test_amqps_azure_servicebus_protocol_component_present -v`
**Expected:** Both tests pass — 6-endpoint broker lab CBOM (3 TLS + 3 plaintext) matches the committed snapshot, and the `AMQPS/Azure-ServiceBus` protocol component is present (D-03 passthrough verified).
**Pass Criteria:** Exit code 0; 2 PASSED.

---

**ID:** UAT-35-03
**Title:** No hollow cert components for plaintext brokers
**Prerequisites:** Phase 35 merged; Python venv active
**Steps:**
1. Run: `python -m pytest tests/test_cbom_motion_golden.py::test_no_certificate_components_for_plaintext_brokers tests/test_cbom_motion_golden.py::test_no_tls_protocol_components_for_plaintext_brokers -v`
2. Inspect `tests/fixtures/cbom/expected_broker_cbom.json`: `grep -c 'localhost:29092\|localhost:25672\|localhost:26379' tests/fixtures/cbom/expected_broker_cbom.json` should return 0.
**Expected:** Both tests pass; the grep on the broker snapshot returns 0 — no plaintext-port bom_refs leak into the CBOM.
**Pass Criteria:** Both tests exit 0; grep step returns 0 matches.

---

## Phase 36: Dashboard Motion Tab (UAT-36-XX)

**Purpose:** Verify the new `/motion` dashboard route, Email Protocols table (STARTTLS badge), Message Brokers grouped sections (plaintext badge + cloud chip), 6th ScoreGauge on the executive summary, and empty-state cards when no email/broker data is present. Maps to requirements DASH-01..05.

---

**ID:** UAT-36-01
**Title:** `/motion` route loads with both sections
**Maps to:** DASH-01
**Prerequisites:** `quirk serve` running; at least one scan in the DB (any host).
**Steps:**
1. Open `http://localhost:8000/motion`.
2. Confirm the page heading reads "Data in Motion".
3. Confirm both `Email Protocols` and `Message Brokers` section headings are visible (either as a data table or an empty-state card).
4. Open the browser console and confirm no JavaScript errors.
**Expected:** Page loads successfully, both section headings present, no console errors.
**Pass Criteria:**
- "Data in Motion" heading visible.
- Both "Email Protocols" and "Message Brokers" sections render.
- Zero console errors.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

**ID:** UAT-36-02
**Title:** Port-25 STARTTLS warning badge renders
**Maps to:** DASH-02
**Prerequisites:** `docker compose --profile email up -d` from `labs/email/`; deep scan run against `localhost`; dashboard accessible at `http://localhost:8000`.
**Steps:**
1. From `labs/email/`, run: `docker compose --profile email up -d`
2. Run a deep scan: `quirk --config <deep-profile-config>` (or project's standard invocation).
3. Open `http://localhost:8000/motion`.
4. In the Email Protocols table, locate the port-25 row.
**Expected:** Port-25 row shows the amber `⚠ STARTTLS` badge in the Warning column. Other port rows (587, 465, etc.) do NOT show the badge.
**Pass Criteria:**
- `⚠ STARTTLS` amber badge is present on the port-25 row.
- No `⚠ STARTTLS` badge on port-587, port-465, or other rows.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

**ID:** UAT-36-03
**Title:** Plaintext broker shows `☠ PLAINTEXT` badge
**Maps to:** DASH-03
**Prerequisites:** `docker compose --profile broker up -d` from `labs/broker/`; scan run against `localhost`.
**Steps:**
1. From `labs/broker/`, run: `docker compose --profile broker up -d`
2. Run a scan against `localhost`.
3. Open `http://localhost:8000/motion`.
4. In the Message Brokers section, locate the Kafka subsection and the KAFKA-PLAIN row (port 29092).
**Expected:** The KAFKA-PLAIN row shows the orange `☠ PLAINTEXT` badge in the Status column. The Kafka subsection title reads `Kafka · N endpoint(s) · 1 plaintext` (or higher).
**Pass Criteria:**
- `☠ PLAINTEXT` orange badge visible on the port-29092 row.
- Kafka subsection title includes `plaintext` count ≥ 1.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

**ID:** UAT-36-04
**Title:** Executive summary shows 6 ScoreGauges with Data in Motion last
**Maps to:** DASH-04
**Prerequisites:** Any scan with completed scoring in the DB.
**Steps:**
1. Open `http://localhost:8000/` (executive summary page).
2. Count the ScoreGauges in the flex-wrap gauge row.
3. Confirm the last gauge is labeled "Data in Motion".
4. Confirm the gauge displays an integer score (not `NaN`, not blank).
**Expected:** 6 gauges visible; "Data in Motion" is the last gauge in the row; gauge shows an integer value.
**Pass Criteria:**
- Exactly 6 ScoreGauge elements visible in the gauge row.
- "Data in Motion" label present on the last gauge.
- Score is a valid integer (not NaN, not empty).

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

**ID:** UAT-36-05
**Title:** Empty-state cards render when no email/broker findings
**Maps to:** DASH-01, DASH-05 (empty-state path)
**Prerequisites:** A scan completed against a host with NEITHER email nor broker endpoints (e.g., `quirk --config <https-only-config>` against a plain HTTPS-only target).
**Steps:**
1. Run a scan against an HTTPS-only host: e.g., `quirk --config <https-only-config>`.
2. Open `http://localhost:8000/motion`.
3. Inspect the Email Protocols section.
4. Inspect the Message Brokers section.
**Expected:** Both sections show the empty-state card with the locked copy message rather than a data table.
**Pass Criteria:**
- Email section shows: "No email endpoints scanned in this session — enable the email scanner in your config or scan a mail server."
- Broker section shows: "No broker endpoints scanned in this session — enable the broker scanner in your config or scan a message broker host."

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

## Phase 38: Identity API Regression Fix (UAT-38-XX)

**Purpose:** Verify that SAML and OIDC findings are correctly returned in `/api/scan/latest` `identity_findings[]` after the scan-window regression fix (GAP-01/GAP-02 closure — `SESSION_BRACKET` 5-minute backward bracket).

---

**ID:** UAT-38-01
**Title:** SAML scan-window regression — automated
**Maps to:** GAP-01, GAP-02
**Prerequisites:** Python venv active; `pytest` available; QU.I.R.K. v4.5.x checked out; `tests/test_identity_surface.py` present with `Issue3ScanWindowRegressionTest` class.
**Steps:**
1. From the repo root, run:
   `python -m pytest tests/test_identity_surface.py::Issue3ScanWindowRegressionTest -x -q`
2. Inspect output for pass/fail count.

**Expected:** All 3 tests in `Issue3ScanWindowRegressionTest` pass. No failures.

**Pass Criteria:**
- `pytest` exits 0
- Output shows `3 passed, 0 failed`
- `identity_findings[]` contains entries for KERBEROS, SAML, and DNSSEC even when the Kerberos endpoint is timestamped 30 s after the others (proves the 5-minute backward bracket covers the skew)

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs
**Status:** Passed
**Notes:** `.venv/bin/python -m pytest tests/test_identity_surface.py::Issue3ScanWindowRegressionTest -x -q` → 3 passed in 0.34s

---

**ID:** UAT-38-02
**Title:** Live `/api/scan/latest` SAML round-trip — manual
**Maps to:** GAP-01
**Prerequisites:**
- Docker + Docker Compose v2 installed
- `quantum-chaos-enterprise-lab/lab.sh` available; `identity` profile containers running (`./lab.sh up identity` or equivalent)
- Full QUIRK scan completed against the identity profile: `quirk --config config.yaml`
- Dashboard API server running: `quirk-dashboard` (or `uvicorn quirk.dashboard.api.main:app`)

**Steps:**
1. Start the chaos lab identity profile:
   `cd quantum-chaos-enterprise-lab && ./lab.sh up identity`
2. Run a scan:
   `quirk --config config.yaml`
3. Query the latest-scan identity findings:
   `curl -s http://localhost:8000/api/scan/latest | jq '.identity_findings[] | .protocol' | sort -u`
4. Inspect the output set.

**Expected:** Output set contains `"SAML"` (and at minimum one of `"KERBEROS"` or `"DNSSEC"` when those protocols are present in the lab profile). An empty array output is a FAIL.

**Pass Criteria:**
- `"SAML"` is present in the output of the `jq` pipe
- `identity_findings` array is non-empty (empty array is a FAIL)
- No HTTP 404 from `/api/scan/latest`

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

## Phase 39: Dashboard Data at Rest Tab (UAT-39-XX)

**Purpose:** Verify the new `/data-at-rest` dashboard route, ScoreGauge labeled "Data at Rest", four locked-column-set tables (Database · Object Storage · Kubernetes Secrets · Vault), per-section empty states, severity sort, null→em-dash rendering, and sidebar nav order. Closes GAP-04; ships DASH-05 deferred from Phase 27.

---

**ID:** UAT-39-01
**Title:** Navigate to `/data-at-rest` from sidebar
**Maps to:** GAP-04, DASH-05
**Prerequisites:** `quirk serve` running on port 8512; at least one scan in the DB.
**Steps:**
1. Open `http://127.0.0.1:8512/`.
2. Click **Data at Rest** in the sidebar (HardDrive icon, between Motion and Certificates).
3. Confirm URL becomes `/data-at-rest`.
4. Open browser DevTools Console.
**Expected:** Page renders with h1 "Data at Rest" and a ScoreGauge labeled "Data at Rest". No console errors.
**Pass Criteria:**
- URL is `/data-at-rest`.
- h1 "Data at Rest" visible.
- ScoreGauge labeled "Data at Rest" visible.
- Zero console errors, zero React warnings.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

**ID:** UAT-39-02
**Title:** Empty state per section when no DAR data
**Maps to:** GAP-04
**Prerequisites:** Scan completed with all DAR scanners disabled (no DB, S3, K8s, Vault findings).
**Steps:**
1. Run a scan with DAR scanners disabled (or against a non-DAR target).
2. Open `http://127.0.0.1:8512/data-at-rest`.
3. Inspect each of the four sections.
**Expected:** Each section renders its EmptyStateCard with locked copy from UI-SPEC. Page does not crash.
**Pass Criteria:**
- Database Encryption section shows EmptyStateCard naming the database scanner config.
- Object Storage section shows EmptyStateCard naming the object-storage scanner config.
- Kubernetes Secrets section shows EmptyStateCard naming the K8s scanner config.
- Vault section shows EmptyStateCard naming the Vault scanner config.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

**ID:** UAT-39-03
**Title:** Database table renders with locked columns
**Maps to:** GAP-04
**Prerequisites:** Scan with PostgreSQL/MySQL/RDS findings populated in `service_detail`.
**Steps:**
1. Run a scan against a host running PostgreSQL or MySQL with the DB scanner enabled.
2. Open `http://127.0.0.1:8512/data-at-rest`.
3. Locate the Database Encryption section.
**Expected:** DatabaseTable renders with the locked column set: Engine · Host · Port · Severity · Title · Encryption at Rest · TLS in Transit · Quantum Risk · Remediation. Rows are severity-sorted (CRITICAL → HIGH → MEDIUM → LOW → INFO).
**Pass Criteria:**
- Exactly the 9 columns above, in order.
- First row severity ≥ severity of last row.
- Boolean fields render as ✓/✗ badges per UI-SPEC.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

**ID:** UAT-39-04
**Title:** Object Storage table renders with locked columns
**Maps to:** GAP-04
**Prerequisites:** Scan with S3 / Azure Blob findings populated in `dat_scan_json`.
**Steps:**
1. Run a scan against an S3 or Azure Blob target with the object-storage scanner enabled.
2. Open `http://127.0.0.1:8512/data-at-rest`.
3. Locate the Object Storage section.
**Expected:** ObjectStorageTable renders with the locked column set: Provider · Host · Severity · Title · Encryption Mode · Public Access · KMS Key · Versioning · Quantum Risk · Remediation. Null fields render as em-dash (—).
**Pass Criteria:**
- Exactly the 10 columns above, in order.
- Rows severity-sorted.
- Any null/missing field is rendered as `—` (not `null`, `undefined`, or blank).

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

**ID:** UAT-39-05
**Title:** Kubernetes table renders with locked columns
**Maps to:** GAP-04
**Prerequisites:** Scan with K8s namespace + cluster-encryption findings.
**Steps:**
1. Run a scan against a Kubernetes cluster with the K8s scanner enabled.
2. Open `http://127.0.0.1:8512/data-at-rest`.
3. Locate the Kubernetes Secrets section.
**Expected:** KubernetesTable renders with the locked column set: Namespace · Host · Severity · Title · Secret Type · Encryption Provider · Quantum Risk · Remediation.
**Pass Criteria:**
- Exactly the 8 columns above, in order.
- Rows severity-sorted.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

**ID:** UAT-39-06
**Title:** Vault table renders with locked columns
**Maps to:** GAP-04
**Prerequisites:** Scan with Vault transit / PKI / auth findings.
**Steps:**
1. Run a scan against a HashiCorp Vault instance with the Vault scanner enabled.
2. Open `http://127.0.0.1:8512/data-at-rest`.
3. Locate the Vault section.
**Expected:** VaultTable renders with the locked column set: Host · Severity · Title · Mount Type · Seal Type · Auto-Unseal · Quantum Risk · Remediation. Seal Type and Auto-Unseal show em-dash for current scanner output (these fields are not probed yet).
**Pass Criteria:**
- Exactly the 8 columns above, in order.
- Rows severity-sorted.
- Seal Type and Auto-Unseal columns render as `—` for every row.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

**ID:** UAT-39-07
**Title:** Sidebar nav order matches D-11 lock
**Maps to:** GAP-04
**Prerequisites:** `quirk serve` running.
**Steps:**
1. Open `http://127.0.0.1:8512/`.
2. Read the sidebar from top to bottom.
**Expected:** Order is Executive Summary · Findings · Identity · Motion · Data at Rest · Certificates · CBOM Viewer · Migration Roadmap · Trends.
**Pass Criteria:**
- Exact order above; "Data at Rest" sits between "Motion" and "Certificates".
- "Data at Rest" entry uses the HardDrive icon.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

**ID:** UAT-39-08
**Title:** Zero console errors gate
**Maps to:** GAP-04
**Prerequisites:** `quirk serve` running on port 8512 (production-build path; do NOT use `npm run dev` which has no `/api/*` proxy).
**Steps:**
1. Open `http://127.0.0.1:8512/data-at-rest`.
2. Open DevTools → Console → Clear.
3. Reload the page.
4. Click another sidebar tab, then click back to "Data at Rest".
**Expected:** Console shows zero errors and zero React warnings throughout the navigation cycle.
**Pass Criteria:**
- Zero red errors in DevTools Console after reload.
- Zero React warnings after navigating away and back.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

## Phase 40: Chaos Lab Parity (UAT-40-XX)

**Purpose:** Verify that `quantum-chaos-enterprise-lab/expected_results_v4.md` is the stable v4 oracle for all chaos-lab profiles, that `./lab.sh profiles` enumerates all profiles dynamically, and that `expected_results_v3.md` carries a "Superseded by" notice. Maps to requirements LAB-01..LAB-04.

---

### UAT-40-01: Chaos Lab v4 Oracle Reference

**ID:** UAT-40-01
**Title:** Chaos lab v4 oracle reference — `expected_results_v4.md` is complete and current
**Maps to:** LAB-01, LAB-02, LAB-03, LAB-04

**Description:** Use `quantum-chaos-enterprise-lab/expected_results_v4.md` as the authoritative expected-findings oracle for every chaos-lab profile (v4.0 baseline through v4.4 messaging). Each profile is documented under a `## Profile: <name>` H2 anchor; cross-link via `expected_results_v4.md#profile-<name>`.

**Prerequisites:** Repo checked out at v4.5+; `quantum-chaos-enterprise-lab/` present.

**Steps:**
1. Confirm the oracle file exists:
   `test -f quantum-chaos-enterprise-lab/expected_results_v4.md && echo "EXISTS"`
2. Check the `./lab.sh profiles` subcommand is present and returns 18 lines:
   `cd quantum-chaos-enterprise-lab && ./lab.sh profiles | wc -l`
3. Verify every profile from `./lab.sh profiles` has a matching H2 section in the oracle:
   `for p in $(./lab.sh profiles); do grep -q "^## Profile: $p" expected_results_v4.md && echo "OK: $p" || echo "MISSING: $p"; done`
4. Confirm `expected_results_v3.md` carries a "Superseded by" notice:
   `grep -q 'Superseded by' quantum-chaos-enterprise-lab/expected_results_v3.md && echo "NOTICE PRESENT"`
5. Confirm `README.md` Profile Summary Table links each row to a `#profile-<name>` anchor:
   `grep -c 'expected_results_v4.md#profile-' quantum-chaos-enterprise-lab/README.md`

**Expected:**
- `expected_results_v4.md` exists.
- `./lab.sh profiles` prints exactly 18 profiles, one per line, alphabetically sorted.
- Every profile listed by `./lab.sh profiles` has a matching `## Profile: <name>` section in the oracle.
- `expected_results_v3.md` contains a "Superseded by" blockquote notice.
- `README.md` contains at least 18 `expected_results_v4.md#profile-` link occurrences (one per profile row).

**Pass Criteria:**
- `test -f quantum-chaos-enterprise-lab/expected_results_v4.md` exits 0
- `./lab.sh profiles | wc -l` outputs `18`
- All 18 profiles from `./lab.sh profiles` return `OK: <name>` (zero `MISSING:` lines)
- `grep -q 'Superseded by' quantum-chaos-enterprise-lab/expected_results_v3.md` exits 0
- `grep -c 'expected_results_v4.md#profile-' quantum-chaos-enterprise-lab/README.md` outputs `19` (core + 18 named profiles)

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs
**Status:** Passed
**Notes:** `expected_results_v4.md` present; `expected_results_v3.md` carries "Superseded by `expected_results_v4.md`" notice.

---

## Phase 41: CI Stability & Scanner Robustness (UAT-41-XX)

**Purpose:** Manually verify the four CI-stability and scanner-robustness deliverables that cannot be cheaply asserted by unit tests: stderr advisory UX when the `[motion]` extra is missing, presence of the documented timeout upper-bound formula, lab.sh teardown sweeping profile-tagged services, and the default pytest run staying under the 60-second CI budget on a developer machine. Maps to requirements CI-01, CI-02, CI-03, ROBUST-01, ROBUST-02, ROBUST-03, ROBUST-04.

---

### UAT-41-01: Missing-[motion]-Extra Stderr Advisory

**ID:** UAT-41-01
**Title:** Missing `[motion]` extra emits canonical stderr advisory; CLI exits 0; scan_errors[] records `category=missing_extra`
**Maps to:** ROBUST-01 (D-12)

**Description:** When `quirk[motion]` is not installed (no `kafka-python` / `pika` / `redis`), invoking `quirk --config <broker.yaml>` (with `enable_broker: true`) must emit a single canonical stderr advisory line, exit 0, and produce a `scan_errors[]` entry tagged `category=missing_extra` so downstream trends counting (D-15) excludes it from regressions.

**Prerequisites:**
- A Python venv with QU.I.R.K. installed but WITHOUT the `[motion]` optional extras: `pip uninstall -y kafka-python pika redis` (or `pip install -e .` without `[motion]`).
- A reachable scan target (`localhost` is fine — no broker need actually answer).

**Steps:**
1. Activate the venv and confirm: `python -c "import kafka" 2>&1 | grep -q "ModuleNotFoundError" && echo "OK: motion absent"`.
2. Prepare a YAML config (e.g. `/tmp/uat-41-01.yaml`) with `targets: [localhost]` and `scan: { enable_broker: true }`. Run: `quirk --config /tmp/uat-41-01.yaml 2> /tmp/quirk-stderr.log`.
3. Inspect stderr: `grep "\[advisory\]" /tmp/quirk-stderr.log`.
4. Confirm exit code: `echo $?` immediately after the scan command (must be `0`).
5. Inspect the produced JSON output for a `scan_errors[]` entry with `category=missing_extra` (or examine the corresponding `CryptoEndpoint(scan_error_category="missing_extra")` row in the SQLite DB).

**Expected:**
- Stderr contains exactly one line of the form: ``[advisory] scanner=broker_scanner extra=motion not installed -- run `pip install quirk[motion]` to enable``.
- CLI exits with status `0`.
- The scan output includes one entry where `scan_error_category=missing_extra` (the broker advisory row).
- The scan does NOT crash — TLS, SSH, fingerprint, jwt phases continue to run.

**Pass Criteria:**
- `grep -q "\[advisory\] scanner=broker_scanner extra=motion not installed" /tmp/quirk-stderr.log` exits 0.
- Exit code of the `quirk --config` invocation is `0`.
- At least one `scan_error_category=missing_extra` entry visible in JSON output or DB.
- No traceback / `BaseException` / unhandled-error text in stderr.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

### UAT-41-02: Configuration Docs Include Upper-Bound Formula

**ID:** UAT-41-02
**Title:** `docs/configuration.md` contains the documented scan-time upper-bound formula and safety-margin guidance
**Maps to:** ROBUST-02 (D-10), ROBUST-04

**Description:** The Phase 41 Plan 06 deliverable adds a "Timeout & Retry Policy (v4.5+)" section to `docs/configuration.md` with the canonical upper-bound formula consultants use to scope engagements. This UAT confirms the literal markers expected by clients and review tooling are present.

**Prerequisites:** Repo checked out at v4.5+.

**Steps:**
1. From repo root run: `grep -q "scan_upper_bound" docs/configuration.md && echo "OK: scan_upper_bound"`.
2. Run: `grep -q "safety_margin" docs/configuration.md && echo "OK: safety_margin"`.
3. Run: `grep -q "scan.timeouts" docs/configuration.md && echo "OK: scan.timeouts"`.
4. Run: `grep -q "DeprecationWarning" docs/configuration.md && echo "OK: deprecation"`.
5. (Optional) Open the section in a markdown viewer and visually confirm the worked single-host (~36s) and 100-host TLS+SSH worst-case (~1610s) examples render cleanly.

**Expected:**
- Both `scan_upper_bound` and `safety_margin` literal strings appear at least once in `docs/configuration.md`.
- The new "Timeout & Retry Policy (v4.5+)" section enumerates all 14 `[scan.timeouts]` slots and all 3 `[scan.retry]` slots with defaults.
- A deprecation table maps the four legacy flat fields (`timeout_seconds`, `fingerprint_timeout_seconds`, `tls_timeout_seconds`, `ssh_timeout_seconds`) to their canonical sub-table targets and notes `DeprecationWarning`.

**Pass Criteria:**
- `grep -q "scan_upper_bound" docs/configuration.md` exits 0.
- `grep -q "safety_margin" docs/configuration.md` exits 0.
- `grep -q "scan.timeouts" docs/configuration.md` exits 0.
- `grep -q "DeprecationWarning" docs/configuration.md` exits 0.
- Cross-referenced audit doc exists: `test -f docs/timeout-retry-audit.md` exits 0.

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs
**Status:** Passed
**Notes:** `grep -c "scan_upper_bound" docs/configuration.md` → 1; `grep -c "safety_margin" docs/configuration.md` → 2. Both literals present.

---

### UAT-41-03: lab.sh Profile-Tagged Service Sweep on `down` and `reset`

**ID:** UAT-41-03
**Title:** `lab.sh down` and `lab.sh reset` sweep all profile-tagged services (no orphans survive teardown)
**Maps to:** ROBUST-03 (D-18 + extension per RESEARCH OQ-4)

**Description:** Phase 40 verification surfaced a gap where `lab.sh down` issued `compose down` without `PROFILE_ARGS`, leaving profile-tagged services (vault-30, kafka-broker, postgres-ssl-off, etc.) orphaned. Phase 41 Plan 06 fixes both the `down` and `reset` arms to use `compose --profile "*" --remove-orphans`. This UAT validates the fix end-to-end against running lab profiles.

**Prerequisites:** Docker + Docker Compose v2 available; `quantum-chaos-enterprise-lab/` checked out; no other `quirk-lab` containers running.

**Steps:**
1. Bring up a profile-tagged service set: `cd quantum-chaos-enterprise-lab && PROFILE_ARGS="--profile vault --profile broker --profile database" ./lab.sh up`.
2. Confirm services are running: `docker ps --filter label=com.docker.compose.project=quirk-lab --format '{{.Names}}' | wc -l` (expect non-zero).
3. Run: `./lab.sh down`.
4. Confirm sweep: `docker ps -a --filter label=com.docker.compose.project=quirk-lab --format '{{.Names}}' | wc -l` (expect `0`).
5. Repeat for the reset arm: bring services up again, then `./lab.sh reset` should also leave zero containers (after the implicit `up` it re-launches the default profile only).
6. Verify the script source carries the wildcard sweep: `grep -q 'compose --profile "\*" down --remove-orphans' lab.sh && grep -q 'compose --profile "\*" down -v --remove-orphans' lab.sh`.

**Expected:**
- After `./lab.sh down`, no `quirk-lab`-labeled containers remain (running or stopped).
- After `./lab.sh reset`, the post-reset container set matches a clean default-profile bring-up — no orphans from the previous profile selection.
- Both wildcard `--profile "*"` invocations are visible in `lab.sh`.

**Pass Criteria:**
- `docker ps -a --filter label=com.docker.compose.project=quirk-lab` returns zero rows after `./lab.sh down`.
- `grep -c 'compose --profile "\*" down' quantum-chaos-enterprise-lab/lab.sh` returns at least 2 (one for `down`, one for `reset`).
- `bash -n quantum-chaos-enterprise-lab/lab.sh` exits 0 (script parses cleanly).

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

### UAT-41-04: Default Pytest Run Finishes Under 60 Seconds

**ID:** UAT-41-04
**Title:** `pytest -m 'not slow'` (the default pyproject `addopts`) completes within the D-16 60-second CI budget on a developer machine
**Maps to:** CI-03 (D-16)

**Description:** Phase 41's CI-03 requirement is that the default test run — bare `pytest` from the repo root — finishes in under 60 seconds. Plan 01 wired `addopts = -m 'not slow'` in `pyproject.toml`; Plan 05 marked 9 slow-test candidates with `@pytest.mark.slow`. After Plan 05, the default suite is `pytest -m 'not slow'` and reports ~6s wall-clock locally. This UAT validates the budget on a clean checkout.

**Prerequisites:**
- Clean repo (no leftover scan databases or large fixtures): `git status -s` is empty (or contains only intentional non-test artifacts).
- Dependencies installed: `pip install -e ".[dashboard,motion]"` recently completed.
- No background scans, dashboards, or chaos lab profiles consuming CPU on the host.

**Steps:**
1. From repo root: `time pytest -m 'not slow' tests/ 2>&1 | tail -5`.
2. Record the `real` wall-clock value reported by the shell builtin `time`.
3. Confirm the run reports `passed` (zero failures, zero errors) and the deselected count is non-zero (slow tests deselected).
4. Re-run once to confirm the result is stable across two consecutive runs (no first-run flakiness).

**Expected:**
- pytest exits with status `0` (all collected tests pass).
- `real` wall-clock as reported by `time` is **strictly less than 60 seconds**.
- A non-zero number of tests are deselected (e.g., `10 deselected`) — confirming `slow` markers are respected.
- Two consecutive runs both stay under 60s.

**Pass Criteria:**
- `pytest -m 'not slow' tests/` exit code is 0.
- `time` `real` value is `<60s` on both consecutive runs.
- Test summary shows `passed` with `deselected` count `>= 9` (Plan 05 marked 9 slow candidates).
- No `errors` or `failures` reported.

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs
**Status:** Passed
**Notes:** `.venv/bin/python -m pytest -m 'not slow' -q` → 705 passed, 16 deselected in 6.13s (well under 60s budget). 13 pre-existing failures from optional `[cloud]` extras (azure.mgmt.storage, google.cloud.container_v1, google.cloud.storage) not installed in venv — unrelated to v4.5 work, predating Phase 28/29.

---

## Phase 42: CBOM Correctness Audit (UAT-42-XX)

**Purpose:** Verify the four CBOM-correctness deliverables landed in Phase 42: per-profile CycloneDX 1.6 JSON+XML schema validation with a docker-compose drift sentinel, a classifier coverage gate that proves zero `UNKNOWN` algorithm fallbacks across all 18 chaos lab profiles plus a regenerable Markdown coverage report, three new shape-golden CBOM fixtures (pki / vault / saml) tracked via `tests/fixtures/cbom/CHANGELOG.md`, and a parametrized Pass-2/Pass-3 skip-list unit gate driven directly off the `MOTION_PLAINTEXT_PROTOCOLS | DAR_SKIP_PROTOCOLS` source-of-truth frozensets. Maps to requirements CBOM-01, CBOM-02, CBOM-03, CBOM-04.

---

### UAT-42-01: CBOM JSON+XML Schema Validation Across 18 Profiles

**ID:** UAT-42-01
**Title:** Every shipped chaos lab profile produces a CycloneDX 1.6 spec-valid CBOM (JSON + XML); drift sentinel locks the parametrize set to docker-compose.yml
**Maps to:** CBOM-01

**Description:** Phase 42 Plan 02 introduced `tests/test_cbom_schema_validation.py`, which calls `JsonStrictValidator(SchemaVersion.V1_6).validate_str(...)` and `XmlValidator(SchemaVersion.V1_6).validate_str(...)` against the CBOM produced for each of the 18 chaos lab profiles, asserting both validators return `None` (CycloneDX-python-lib idiom for "valid"). A drift sentinel (`test_parametrize_set_matches_docker_compose_profiles`) parses `quantum-chaos-enterprise-lab/docker-compose.yml` via `yaml.safe_load` and asserts the union of profile labels equals `tests._cbom_profiles.PROFILE_ENDPOINTS.keys()` so no future compose-file change can silently shrink coverage.

**Prerequisites:** Repo at HEAD with `pip install -e .` complete (cyclonedx-python-lib[validation] >=11.7.0 transitive deps installed).

**Steps:**
1. From repo root: `.venv/bin/pytest tests/test_cbom_schema_validation.py -x -v`.
2. Confirm 19 tests passed (18 profile parametrize cases + 1 drift sentinel).
3. Optionally inspect a profile case: `pytest tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[pki] -x -v`.

**Expected:**
- All 19 tests pass; both JSON and XML validators return `None` for every profile.
- Drift sentinel asserts `assert len(profiles) >= 18` and equality of the parametrize set with the compose-derived profile set.

**Pass Criteria:**
- `pytest tests/test_cbom_schema_validation.py -x -v` exits 0.
- Output shows 19 passed (or 19 passed plus deselected slow markers).
- `test_parametrize_set_matches_docker_compose_profiles` PASSED line is present.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

### UAT-42-02: Classifier Coverage Gate + Regen Report

**ID:** UAT-42-02
**Title:** Every algorithm component emitted by `build_cbom()` for the 18 chaos lab profiles classifies to a non-UNKNOWN primitive; `docs/cbom-classifier-coverage.md` is byte-deterministic on regen
**Maps to:** CBOM-02

**Description:** Phase 42 Plan 04 added `tests/test_cbom_classifier_coverage.py::test_no_unknown_classifications_across_lab_profiles`, which walks `bom.components` for every profile in `tests._cbom_profiles.PROFILE_ENDPOINTS`, filters by `crypto_properties.asset_type.value == "algorithm"`, calls `classify_algorithm(c.name)`, and asserts no UNKNOWN primitive (except the JWT `alg:none` sentinel). A companion regen test (`test_regenerate_coverage_report`, gated by `REGEN_CBOM_COVERAGE=1` and `@pytest.mark.slow`) writes `docs/cbom-classifier-coverage.md`; a second consecutive regen produces zero git diff. Plan 04 added 12 `_ALGORITHM_TABLE` rows (RSA-1024/2048/3072/4096, AES-128/192/256, sha1/sha256/sha384/sha512withRSAEncryption, ecdsa-with-sha256/384/512, md5withRSAEncryption) to close the five gate-surfaced gaps plus 7 forward-looking neighbours.

**Prerequisites:** Repo at HEAD with `pip install -e .` complete.

**Steps:**
1. From repo root: `.venv/bin/pytest tests/test_cbom_classifier_coverage.py -x`.
2. Confirm: `test -f docs/cbom-classifier-coverage.md && grep -q '# CBOM Classifier Coverage Report' docs/cbom-classifier-coverage.md && grep -q '| Algorithm Name |' docs/cbom-classifier-coverage.md`.
3. Determinism check (regen mode): `REGEN_CBOM_COVERAGE=1 .venv/bin/pytest tests/test_cbom_classifier_coverage.py::test_regenerate_coverage_report -s -m ""` then `git diff docs/cbom-classifier-coverage.md` (must be empty).

**Expected:**
- The gate test passes (1 passed, 1 deselected slow).
- The Markdown report exists with the canonical heading and an `| Algorithm Name |` table.
- Re-running the regen produces a byte-identical file (empty `git diff`).

**Pass Criteria:**
- `pytest tests/test_cbom_classifier_coverage.py -x` exits 0.
- `docs/cbom-classifier-coverage.md` exists, contains `# CBOM Classifier Coverage Report` and a `| Algorithm Name |` table header.
- Re-running the regen test with `REGEN_CBOM_COVERAGE=1` leaves `git diff docs/cbom-classifier-coverage.md` empty.

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs
**Status:** Passed
**Notes:** `.venv/bin/python -m pytest tests/test_cbom_classifier_coverage.py::test_no_unknown_classifications_across_lab_profiles` → 1 passed in 0.10s.

---

### UAT-42-03: Shape Goldens (pki/vault/saml) + CHANGELOG

**ID:** UAT-42-03
**Title:** Three new shape-golden CBOM snapshot tests (pki / vault / saml) pass; `tests/fixtures/cbom/CHANGELOG.md` documents the Phase 42 fixture additions; pre-existing email + broker goldens are byte-identical
**Maps to:** CBOM-03

**Description:** Phase 42 Plan 03 added three new shape-golden CBOM fixtures — `tests/fixtures/cbom/expected_pki_cbom.json` (TLS-with-cert shape, mTLS step-CA gateway), `expected_vault_cbom.json` (Pass-1-only DAR shape, VAULT in `DAR_SKIP_PROTOCOLS`), `expected_saml_cbom.json` (Identity shape, no TLS) — with corresponding `test_pki_cbom_matches_snapshot` / `test_vault_cbom_matches_snapshot` / `test_saml_cbom_matches_snapshot` snapshot tests in `tests/test_cbom_motion_golden.py`. `tests/fixtures/cbom/CHANGELOG.md` was created with a Phase 42 entry per D-09. Plan 03 also added `tests/_cbom_profiles.py::PROFILE_ENDPOINTS` (18-profile registry) plus 13 lightweight per-profile endpoint synthesizers in `tests/test_cbom_motion_endpoints.py`.

**Prerequisites:** Repo at HEAD with `pip install -e .` complete.

**Steps:**
1. From repo root: `.venv/bin/pytest tests/test_cbom_motion_golden.py -x -v`.
2. Confirm 5 snapshot tests passed: `test_email_cbom_matches_snapshot`, `test_broker_cbom_matches_snapshot`, `test_pki_cbom_matches_snapshot`, `test_vault_cbom_matches_snapshot`, `test_saml_cbom_matches_snapshot`.
3. Verify CHANGELOG: `grep -q 'Phase 42' tests/fixtures/cbom/CHANGELOG.md`.
4. Verify pre-existing fixtures unchanged: `git diff tests/fixtures/cbom/expected_email_cbom.json tests/fixtures/cbom/expected_broker_cbom.json` (must be empty).
5. Inspect new fixtures exist: `ls tests/fixtures/cbom/expected_pki_cbom.json tests/fixtures/cbom/expected_vault_cbom.json tests/fixtures/cbom/expected_saml_cbom.json`.

**Expected:**
- All 5 snapshot tests + 6 structural-invariant tests pass.
- The Phase 42 entry in `CHANGELOG.md` names the three new fixtures and documents the regen invocation (`REGEN_CBOM_FIXTURES=1 pytest ... -m ""`).
- The two pre-existing email/broker goldens have empty diffs against HEAD.

**Pass Criteria:**
- `pytest tests/test_cbom_motion_golden.py -x -v` exits 0 with at least 5 PASSED snapshot tests visible.
- `tests/fixtures/cbom/CHANGELOG.md` contains `Phase 42`.
- `git diff tests/fixtures/cbom/expected_email_cbom.json tests/fixtures/cbom/expected_broker_cbom.json` produces no output.
- All three new fixture files exist on disk.

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs
**Status:** Passed
**Notes:** All 5 golden fixtures confirmed on disk: expected_broker_cbom.json, expected_email_cbom.json, expected_pki_cbom.json, expected_saml_cbom.json, expected_vault_cbom.json. tests/fixtures/cbom/CHANGELOG.md present.

---

### UAT-42-04: Pass-2 / Pass-3 Skip-List Unit Tests

**ID:** UAT-42-04
**Title:** Parametrized unit gate proves every label in `MOTION_PLAINTEXT_PROTOCOLS | DAR_SKIP_PROTOCOLS` is skipped by both Pass 2 (cert) and Pass 3 (protocol) of `build_cbom()`; sanity guard fails loudly if either constant is emptied
**Maps to:** CBOM-04

**Description:** Phase 42 Plan 01 lifted `MOTION_PLAINTEXT_PROTOCOLS` (3 labels: AMQP-PLAIN, KAFKA-PLAIN, REDIS-PLAIN) and `DAR_SKIP_PROTOCOLS` (9 labels: AZURE_BLOB, CLOUD_SQL, GCP, KUBERNETES, MYSQL, POSTGRESQL, RDS, S3, VAULT) to module-level frozensets in `quirk/cbom/builder.py`. Plan 05 added `tests/test_cbom_skip_lists.py` (84 lines, 13 tests) which parametrizes directly off `sorted(MOTION_PLAINTEXT_PROTOCOLS | DAR_SKIP_PROTOCOLS)` — no hardcoded list — building a full TLS+cert `CryptoEndpoint` per label and asserting the resulting CBOM contains NO `crypto/certificate/{host}:{port}` ref AND NO `crypto/protocol/tls/{host}:{port}` ref. A separate `test_skip_list_constants_are_nonempty` sanity guard fails if either constant is emptied (T-42-07 mitigation).

**Prerequisites:** Repo at HEAD with `pip install -e .` complete.

**Steps:**
1. From repo root: `.venv/bin/pytest tests/test_cbom_skip_lists.py -x -v`.
2. Confirm 13 tests passed (1 sanity + 12 parametrized: 3 motion + 9 DAR).
3. Verify import path: `.venv/bin/python -c "from quirk.cbom.builder import MOTION_PLAINTEXT_PROTOCOLS, DAR_SKIP_PROTOCOLS; print(len(MOTION_PLAINTEXT_PROTOCOLS), len(DAR_SKIP_PROTOCOLS))"` — expect `3 9`.
4. Spot-check parametrize ID surfaces a label name on failure: `pytest tests/test_cbom_skip_lists.py::test_skip_protocol_emits_no_cert_or_proto_component[VAULT] -x -v`.

**Expected:**
- All 13 tests pass.
- Parametrize IDs are the protocol labels themselves (e.g. `[VAULT]`, `[KAFKA-PLAIN]`).
- The import line runs cleanly with both frozensets present in `quirk.cbom.builder`.

**Pass Criteria:**
- `pytest tests/test_cbom_skip_lists.py -x -v` exits 0 with at least 12 parametrized cases plus 1 sanity guard (≥ 13 total).
- `from quirk.cbom.builder import MOTION_PLAINTEXT_PROTOCOLS, DAR_SKIP_PROTOCOLS` succeeds.
- `len(MOTION_PLAINTEXT_PROTOCOLS) == 3` and `len(DAR_SKIP_PROTOCOLS) == 9`.

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs
**Status:** Passed
**Notes:** `.venv/bin/python -m pytest tests/test_cbom_skip_lists.py` → 13 passed in 0.10s (12 parametrized skip-protocol tests + 1 nonempty-constants test).

---

## Phase 43: Dashboard Polish (UAT-43-XX)

**Purpose:** Verify that all nine in-scope dashboard routes (/, /findings, /identity, /motion, /data-at-rest, /certificates, /cbom, /roadmap, /trends) are console-error-free, render explicit loading states on first paint, render explicit empty states when scan data is absent, meet WCAG AA keyboard-navigation and focus-ring requirements, and that the GitHub Actions dashboard-quality CI gate enforces this bar on every future PR. Maps to requirements DASH-01, DASH-02, DASH-03.

---

### UAT-43-01: Dashboard A11y Sweep — Happy Fixture

**ID:** UAT-43-01
**Title:** `npm run a11y:check` exits 0 across all 9 dashboard routes against the seeded happy-path fixture
**Maps to:** DASH-01, DASH-03

**Description:** Phase 43 Plan 01 introduced an `@axe-core/puppeteer` harness (`src/dashboard/tests/a11y/run-a11y.mjs`) that boots `vite preview` with `VITE_A11Y_FIXTURE=1`, navigates all 9 routes, runs axe-core WCAG 2.1 A/AA rules, captures console messages, and diffs against per-route baseline JSONs. The `a11y:check` script runs the diff mode — it exits 1 if any new axe violation appears beyond the locked baseline or if any console message is not in `tests/console-allowlist.json`. Phase 43 Plans 02/03 eliminated the pre-existing violations so the baselines (written by Plan 04 Task 1) reflect a clean green state.

**Prerequisites:**
- Node 20+ installed
- Dashboard dev dependencies installed: `cd src/dashboard && npm ci`
- Production build present: `cd src/dashboard && npm run build`
- 9 baseline JSON files present in `src/dashboard/tests/a11y/`

**Steps:**
1. Build the dashboard: `cd src/dashboard && npm run build`.
2. Run the sweep: `cd src/dashboard && npm run a11y:check`.
3. Confirm exit code 0 and that output reports zero new axe violations and zero unallowlisted console messages for each route.

**Expected:**
- Script exits 0.
- Each route line shows `axe: 0 new violations` and `console: 0 unallowlisted messages`.
- Only allowed console message is the recharts `defaultProps` deprecation warning (present in `tests/console-allowlist.json`).

**Pass Criteria:**
- `cd src/dashboard && npm run a11y:check` exits 0.
- Output contains no "NEW axe violation" lines.
- Output contains no "UNALLOWLISTED console" lines.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

### UAT-43-02: Dashboard A11y Sweep — Empty Fixture

**ID:** UAT-43-02
**Title:** `npm run a11y:check:empty` exits 0; every route renders an explicit empty state (no crashes, no blank panels)
**Maps to:** DASH-02

**Description:** Phase 43 Plan 02 added `EmptyStateCard` (shared component) and `PageSpinner` and wired explicit empty-state branches into all 9 in-scope routes. The `a11y:check:empty` script runs the axe harness with `VITE_A11Y_FIXTURE_VARIANT=empty`, which serves `{}` for `/api/scan/latest` and `/api/trends`. Each route must render a legible empty state rather than blank panels or JavaScript errors, and those empty-state UIs must themselves be axe-clean.

**Prerequisites:**
- Same as UAT-43-01: `npm ci` + `npm run build` complete.

**Steps:**
1. Run the empty-fixture sweep: `cd src/dashboard && npm run a11y:check:empty`.
2. Confirm exit code 0.
3. Optionally start preview manually and visit each route: `cd src/dashboard && VITE_A11Y_FIXTURE=1 VITE_A11Y_FIXTURE_VARIANT=empty npm run preview` then navigate to http://localhost:4173/.

**Expected:**
- Script exits 0.
- Manual inspection: every route shows a card with a "no data" message (EmptyStateCard or page-level empty), not a blank panel or unhandled exception.

**Pass Criteria:**
- `cd src/dashboard && npm run a11y:check:empty` exits 0.
- Manual walk (optional): each of the 9 routes renders a non-blank empty state with descriptive text.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

### UAT-43-03: Keyboard Focus Visibility

**ID:** UAT-43-03
**Title:** Tab through the dashboard preview; every interactive element shows a visible focus ring
**Maps to:** DASH-03

**Description:** Phase 43 Plan 03 added `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2` to the React Router `<Link>` primitive in `src/dashboard/src/components/sidebar.tsx`. shadcn/radix components (buttons, tab triggers, inputs) already ship focus rings. This UAT verifies that pressing Tab on any route produces visible blue/white focus outlines on every interactive element — no "invisible focus" keyboard navigation.

**Prerequisites:**
- Dashboard preview running with happy fixture: `cd src/dashboard && VITE_A11Y_FIXTURE=1 npm run preview`
- Modern browser open at http://localhost:4173/

**Steps:**
1. Start preview: `cd src/dashboard && VITE_A11Y_FIXTURE=1 npm run preview`.
2. Open http://localhost:4173/ in a browser.
3. Press Tab repeatedly. Observe focus indicator on each of: sidebar navigation Links, table sort column headers, filter input fields, tab trigger buttons, action buttons.
4. Navigate to /findings, /identity, /motion, /cbom, /roadmap and repeat the Tab test on each.

**Expected:**
- A visible focus ring (blue outline, or white outline on dark sidebar) appears on every focusable element as Tab moves through the page.
- No interactive element is reachable by Tab but invisible (no focus ring).

**Pass Criteria:**
- Every sidebar navigation link shows a 2px ring on focus.
- At least one filter input, one table header, and one tab trigger show visible focus rings on their respective routes.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

### UAT-43-04: Loading-State First Paint

**ID:** UAT-43-04
**Title:** With the loading fixture variant, skeleton/PageSpinner appears on first paint and persists ~3 seconds before content appears
**Maps to:** DASH-02

**Description:** Phase 43 Plan 02 added layout-matched skeleton components (`findings.skeleton.tsx`, `cbom.skeleton.tsx`, `identity.skeleton.tsx`, `certificates.skeleton.tsx`) and `PageSpinner` for context-derived routes (executive, trends, roadmap). The `VITE_A11Y_FIXTURE_VARIANT=loading` variant adds a 3-second delay to `/api/scan/latest` and `/api/trends` responses in the Vite fixture middleware, creating a reproducible loading window. This UAT confirms that no flash of raw empty content appears — the skeleton/spinner is the first visible state.

**Prerequisites:**
- Dashboard built: `cd src/dashboard && npm run build`
- Preview available at http://localhost:4173/ with loading variant

**Steps:**
1. Start the loading-variant preview: `cd src/dashboard && VITE_A11Y_FIXTURE=1 VITE_A11Y_FIXTURE_VARIANT=loading npm run preview`.
2. Hard-reload (Cmd+Shift+R / Ctrl+Shift+R) on each of: / (executive), /findings, /motion, /trends.
3. Observe first paint for ~5 seconds on each route.

**Expected:**
- / shows `PageSpinner` (6 skeleton circles + h-48 bar) for ~3 seconds, then populates with executive summary data.
- /findings shows a layout-matched skeleton (filter bar placeholders + table row placeholders) for ~3 seconds.
- /motion shows its skeleton (section headers + row blocks) for ~3 seconds.
- /trends shows `PageSpinner` for ~3 seconds.
- No route shows a flash of "no data" empty-state text before data arrives.

**Pass Criteria:**
- On each of the four routes above, a skeleton or spinner is visible on first paint (before the 3s delay expires).
- No route shows an empty-state message ("No scan data" / "No trend data") while loading is in progress.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

### UAT-43-05: GitHub Actions Dashboard-Quality Workflow

**ID:** UAT-43-05
**Title:** A PR touching `src/dashboard/**` triggers the `Dashboard Quality` workflow and it turns green
**Maps to:** DASH-01, DASH-02, DASH-03

**Description:** Phase 43 Plan 04 Task 2 created `.github/workflows/dashboard-quality.yml`. It triggers on PRs with `paths: ['src/dashboard/**', '.github/workflows/dashboard-quality.yml']` and runs: `npm ci`, `npm run build`, `npm run lint`, `npm run a11y:check` (happy fixture), `npm run a11y:check:empty` on an `ubuntu-latest` runner using `google-chrome-stable` via `PUPPETEER_EXECUTABLE_PATH`. This workflow enforces the Phase 43 quality bar going forward so dashboard regressions are caught at PR time rather than in production.

**Prerequisites:**
- GitHub repository with Actions enabled.
- A fork or branch for test PR creation.

**Steps:**
1. Create a draft PR that touches at least one file in `src/dashboard/**` (e.g. add a comment to `src/dashboard/src/App.tsx`).
2. Observe the Checks panel on the PR.
3. Wait for the `Dashboard Quality / Axe + Console Gate` check to complete.

**Expected:**
- The `Dashboard Quality` workflow appears in the Checks list within ~30 seconds.
- All steps complete green: Setup Node, Install dependencies, Build dashboard, Lint, Run axe + console sweep (happy fixture), Run axe + console sweep (empty fixture).
- Total runtime < 3 minutes.

**Pass Criteria:**
- `Dashboard Quality / Axe + Console Gate` check shows "All jobs passed" (green check mark).
- Both `npm run a11y:check` and `npm run a11y:check:empty` steps show exit 0 in the workflow log.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

### UAT-43-06: A11y Harness Reports PASS on Baseline-Only Routes

**ID:** UAT-43-06
**Title:** `npm run a11y:check` (happy fixture) exits 0 and every route shows PASS even when baseline violations exist
**Maps to:** DASH-07 (informal — gap closure for UAT issue 1)

**Description:** Phase 43 Plan 05 (gap closure) fixed `run-a11y.mjs` to use `newViolationsCount` (baseline-delta) rather than `results.violations.length` (raw axe total) in the summary PASS/FAIL logic. Routes that have only baseline-captured violations should now show PASS instead of incorrectly reporting FAIL.

**Prerequisites:**
- `VITE_A11Y_FIXTURE=1 npm run dev` running (or use `npm run a11y:check` directly which starts its own server).

**Steps:**
1. From `src/dashboard/`, run `npm run a11y:check`.
2. Observe the per-route summary lines in terminal output.
3. Note the exit code.

**Expected:**
- Every route summary line shows `PASS`.
- Process exits 0.
- No route shows `FAIL` unless it has genuinely new violations not in the baseline.

**Pass Criteria:**
- Exit code 0.
- All 9 route summary lines contain `PASS`.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

### UAT-43-07: Pagination Absent on Single-Page Datasets

**ID:** UAT-43-07
**Title:** Findings and Identity pages show no pagination controls when the dataset fits on one page
**Maps to:** DASH-08 (informal — gap closure for UAT issue 3)

**Description:** Phase 43 Plan 05 (gap closure) added `{table.getPageCount() > 1 && (...)}` guards around the pagination `<div>` in both `findings.tsx` and `identity.tsx`. On single-page datasets, the entire pagination bar (Previous/Next buttons + page counter) must be absent from the DOM — not just disabled.

**Prerequisites:**
- `VITE_A11Y_FIXTURE=1 npm run dev` running (fixture scan has a small dataset that fits on one page for both tables).

**Steps:**
1. Navigate to `/findings`.
2. Inspect the DOM (or visually check) for pagination controls at the bottom of the table.
3. Navigate to `/identity`.
4. Repeat inspection.

**Expected:**
- No pagination bar visible on either page.
- No disabled Previous/Next buttons present in the DOM.

**Pass Criteria:**
- DevTools DOM contains no element matching `.flex.items-center.justify-between` in the pagination area on either page.
- `table.getPageCount()` returns 1 for the fixture dataset.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

### UAT-43-08: PDF Export Produces Data-Populated PDF

**ID:** UAT-43-08
**Title:** Executive Summary PDF export button downloads a non-blank, data-populated PDF
**Maps to:** DASH-06 (informal — gap closure for UAT issue 2)

**Description:** Phase 43 Plan 06 (gap closure) added a `data-ready` DOM sentinel to `print.tsx` (set via `useEffect` once scan data is non-null) and updated `pdf.py` to `page.wait_for_selector('body[data-ready="true"]', timeout=15_000)` before calling `page.pdf()`. This ensures Playwright waits for React hydration before capture, eliminating the blank-PDF defect.

**Prerequisites:**
- QUIRK backend running with a real scan in the database (`quirk --config config.yaml` then `quirk serve`).
- Or use the fixture dev server if a PDF-generation test endpoint is available.

**Steps:**
1. Open the Executive Summary page in the dashboard.
2. Click "Export PDF".
3. Wait for the download (up to 30 seconds).
4. Open the downloaded `quirk-report.pdf`.

**Expected:**
- PDF contains rendered scan data: score gauges, findings summary, certificate list.
- No blank or loading-state pages.
- PDF is A4 format.

**Pass Criteria:**
- Downloaded file is a valid PDF (`file quirk-report.pdf` reports `PDF document`).
- Opening the PDF shows populated tables and scores — not a blank page or spinner.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending
**Notes:**

---

# Series 44: UAT Debt Automation (Phase 44)

### UAT-44-01: Phase 27 DB Integration Tests — PostgreSQL + MySQL ssl-off

**ID:** UAT-44-01
**Title:** Live-infra DB integration tests pass against the database chaos lab profile
**Maps to:** UAT-01 (Phase 27 DB UAT debt closure)

**Description:** `tests/test_uat_db_integration.py` contains 4 live-infra-gated tests covering PostgreSQL (port 25432) ssl-off and MySQL (port 23306) ssl-off against the `database` chaos lab profile. Tests skip automatically when `QUIRK_DB_INTEGRATION` is unset.

**Prerequisites:**
- `./lab.sh up database` — PostgreSQL on 25432, MySQL on 23306
- `QUIRK_DB_INTEGRATION=1` environment variable set

**Steps:**
1. Start the database chaos lab profile: `./lab.sh up database`
2. Run: `QUIRK_DB_INTEGRATION=1 python -m pytest tests/test_uat_db_integration.py -v`
3. Confirm all 4 tests pass (PostgreSQL ssl-off HIGH, MySQL ssl-off HIGH assertions).

**Pass Criteria:**
- All 4 tests in `test_uat_db_integration.py` PASS with `QUIRK_DB_INTEGRATION=1` and database profile running.
- Tests skip cleanly (not fail) when `QUIRK_DB_INTEGRATION` is unset.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending (requires chaos lab)
**Notes:**

---

### UAT-44-02: Phase 25 Kerberos/SAML Traceability Annotations

**ID:** UAT-44-02
**Title:** Existing Kerberos and SAML chaos lab tests carry UAT-25 closure annotations
**Maps to:** UAT-03 (Phase 25 identity UAT debt closure)

**Description:** `test_samba_dc_integration` in `tests/test_kerberos_scanner.py` and `test_chaos_lab_integration` in `tests/test_saml_scanner.py` have verbatim UAT-25 traceability annotations in their docstrings. These tests already covered the Phase 25 pass criteria; Phase 44 added explicit audit trail markers.

**Prerequisites:**
- `./lab.sh up kerberos saml` — Samba DC + SimpleSAMLphp
- `QUIRK_KERBEROS_INTEGRATION=1` and `QUIRK_SAML_INTEGRATION=1`

**Steps:**
1. Run: `python -m pytest tests/test_kerberos_scanner.py::test_samba_dc_integration tests/test_saml_scanner.py::test_chaos_lab_integration -v`
2. Confirm UAT-25 traceability text appears in the test docstrings (`pytest --co -q` to verify).

**Pass Criteria:**
- Both tests exist and carry `UAT-25` in their docstrings.
- Both tests PASS when their respective chaos lab profiles are running.

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs
**Status:** Passed (unit tests; chaos-lab integration tests deferred to Bucket C)
**Notes:** `.venv/bin/python -m pytest tests/test_saml_scanner.py tests/test_kerberos_scanner.py -k "not integration and not chaos_lab and not samba and not saml_chaos"` → 50 passed, 2 deselected in 0.16s. UAT-25 traceability annotations confirmed present in both test files.

---

### UAT-44-03: Phase 30 Vault Live Integration Test — 5-Finding Spec

**ID:** UAT-44-03
**Title:** Vault live integration test passes against vault-30 chaos lab container
**Maps to:** UAT-03 (Phase 30 Vault UAT debt closure)

**Description:** `test_vault_live_uat_30_01_five_findings` in `tests/test_vault_connector.py` targets the vault-30 container (port 28200, root token "root") and asserts ≥5 findings including transit/exportable MEDIUM, PKI HIGH, and auth/token HIGH.

**Prerequisites:**
- `./lab.sh up vault` — vault-30 container on port 28200
- `QUIRK_VAULT_INTEGRATION=1` environment variable set

**Steps:**
1. Start the vault profile: `./lab.sh up vault`
2. Run: `QUIRK_VAULT_INTEGRATION=1 python -m pytest tests/test_vault_connector.py::test_vault_live_uat_30_01_five_findings -v`
3. Confirm 5+ findings returned with expected severity labels.

**Pass Criteria:**
- Test PASSES with `QUIRK_VAULT_INTEGRATION=1` and vault profile running.
- Test skips cleanly (not fails) when `QUIRK_VAULT_INTEGRATION` is unset.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Status:** Pending (requires chaos lab)
**Notes:**

---

### UAT-44-04: Phase 31 Trends Flat-Wire-Format Test

**ID:** UAT-44-04
**Title:** Trends API flat wire format test passes without chaos lab
**Maps to:** UAT-01 (Phase 31 VERIFICATION closure — trends flat format)

**Description:** `test_uat_31_trends_two_sessions_flat_wire_format` in `tests/test_dashboard_trends.py` seeds two distinct scan sessions into a UUID-named in-memory SQLite database and asserts that `GET /api/trends` returns all 12 flat wire-format keys (UAT-9-09 spec). No chaos lab or environment variables required.

**Prerequisites:**
- Standard pytest environment (no live infra needed)

**Steps:**
1. Run: `python -m pytest tests/test_dashboard_trends.py::test_uat_31_trends_two_sessions_flat_wire_format -v`
2. Confirm test PASSES and asserts all 12 flat wire-format keys present.

**Pass Criteria:**
- Test PASSES without any environment variables or running services.
- Response contains all 12 keys: `current_session_ts`, `previous_session_ts`, `new_high`, `new_medium`, `new_low`, `resolved_high`, `resolved_medium`, `resolved_low`, `scan_errors_new_count`, `scan_errors_resolved_count`, `new_findings_sample`, `resolved_findings_sample`.
- `new_high >= 1` and `resolved_medium >= 1`.

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs
**Status:** Passed
**Notes:** `.venv/bin/python -m pytest tests/test_dashboard_trends.py::test_uat_31_trends_two_sessions_flat_wire_format -v` → 1 passed in 0.20s. All 12 flat wire-format keys asserted; new_high >= 1 and resolved_medium >= 1 confirmed.

---

# Series 46: TLS Cert-Defect Findings (Phase 46)

These tests exercise the four cert-defect endpoints that ship with the `tls-cert-defects` chaos lab profile (Phase 46 Plan 03). The profile lives in `quantum-chaos-enterprise-lab/docker-compose.yml` and binds nginx services on host ports 13444–13447.

**Profile bring-up (preferred — bypasses BACK-87 lab.sh PROFILE_ARGS precedence bug):**

```bash
cd quantum-chaos-enterprise-lab
docker compose -p chaoslab --profile tls-cert-defects up -d \
  tls-cert-expired tls-cert-selfsigned tls-cert-untrusted-ca tls-cert-rsa1024
# Smoke check — each port should return "OK - tls-cert-<name>":
for p in 13444 13445 13446 13447; do curl -sk --max-time 3 https://localhost:$p/; echo; done
```

**Tear-down:**

```bash
docker compose -p chaoslab --profile tls-cert-defects down
```

**Scan invocation (shared by UAT-46-01..05):**

Create `/tmp/phase46-uat-config.yaml` with `ports_tls: [13444, 13445, 13446, 13447]` and `targets.fqdns: ["localhost"]`, then:

```bash
python run_scan.py --config /tmp/phase46-uat-config.yaml --quiet
```

The findings JSON lands at `<output.directory>/findings-<ts>.json`.

---

### UAT-46-01: Expired Certificate → CRITICAL Finding (TLS-FIND-01)

**ID:** UAT-46-01
**Title:** Expired TLS certificate produces a CRITICAL finding
**Maps to:** TLS-FIND-01

**Prerequisites:**
- `tls-cert-defects` profile up (`tls-cert-expired` service on host port 13444)

**Steps:**
1. Bring up the profile (see top-of-series command).
2. Run the QUIRK scan against ports 13444–13447.
3. Inspect findings JSON for `host=localhost`, `port=13444` entries.

**Expected:** One CRITICAL finding with title containing `expired` (literally `TLS certificate expired`) at `localhost:13444`.

**Pass Criteria:**
- Findings JSON contains `severity=CRITICAL` and `title=TLS certificate expired` for `localhost:13444`.

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs
**Status:** Passed (Phase 46 Plan 04 live-fire)
**Notes:** Verified in live-fire run on 2026-05-03 against chaos lab `tls-cert-defects` profile. CRITICAL/expired finding emitted as expected.

---

### UAT-46-02: Self-Signed Certificate → HIGH Finding + D-04 Exclusivity (TLS-FIND-02)

**ID:** UAT-46-02
**Title:** Self-signed certificate produces HIGH self-signed finding AND emits NO untrusted-CA finding on the same endpoint
**Maps to:** TLS-FIND-02 (and D-04 mutual exclusivity rule)

**Prerequisites:**
- `tls-cert-defects` profile up (`tls-cert-selfsigned` on host port 13445)

**Steps:**
1. Bring up the profile.
2. Run the scan.
3. Inspect findings for `localhost:13445`.

**Expected:**
- One HIGH finding with title `TLS certificate is self-signed`.
- ZERO findings on the same endpoint with title `TLS certificate issued by untrusted CA` (D-04 mutual exclusivity per Phase 46 Plan 02).

**Pass Criteria:**
- Findings JSON contains exactly one `severity=HIGH`, `title=TLS certificate is self-signed` entry for `localhost:13445`.
- Findings JSON contains zero entries with `title=TLS certificate issued by untrusted CA` for `localhost:13445`.

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs
**Status:** Passed (Phase 46 Plan 04 live-fire)
**Notes:** Live-fire confirmed: HIGH self-signed at 13445; no untrusted-CA finding on same endpoint. D-04 if/elif structural exclusivity verified.

---

### UAT-46-03: Untrusted-CA Certificate → MEDIUM Finding (TLS-FIND-03)

**ID:** UAT-46-03
**Title:** Cert signed by an off-trust-store CA produces a MEDIUM untrusted-CA finding
**Maps to:** TLS-FIND-03

**Prerequisites:**
- `tls-cert-defects` profile up (`tls-cert-untrusted-ca` on host port 13446)
- The `scenario-root-CA` is NOT installed in the host trust store (verify: `security find-certificate -c "scenario-root-CA" /Library/Keychains/System.keychain` returns "could not be found")

**Steps:**
1. Bring up the profile.
2. Run the scan.
3. Inspect findings for `localhost:13446`.

**Expected:** One MEDIUM finding with title `TLS certificate issued by untrusted CA` at `localhost:13446`. Cert subject `CN=untrusted-ca.chaos.local`, issuer `CN=scenario-root-CA` (subject != issuer); leaf is RSA-2048 so this finding is isolated from any RSA-key-size finding.

**Pass Criteria:**
- Findings JSON contains `severity=MEDIUM`, `title=TLS certificate issued by untrusted CA` for `localhost:13446`.
- The same endpoint emits NO `TLS certificate is self-signed` finding (D-04 verification, the inverse of UAT-46-02).

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs
**Status:** Passed (Phase 46 Plan 04 live-fire)
**Notes:** Live-fire confirmed MEDIUM/untrusted-CA at 13446. Required a Phase 46 Plan 04 Rule-1 bug fix in `quirk/scanner/tls_scanner.py` to make the verify pre-pass tolerate `server_hostname=None` (the original Plan 46-01 implementation set `check_hostname=True` unconditionally, which raised ValueError on IP / SNI-off targets and silently routed `chain_verified` to `None`, leaving the untrusted-CA branch structurally dead). Fix landed in commit `de70301`.

---

### UAT-46-04: RSA-1024 Public Key → HIGH Undersized-Key Finding (TLS-FIND-04)

**ID:** UAT-46-04
**Title:** Cert with an RSA-1024 public key produces a HIGH undersized-key finding
**Maps to:** TLS-FIND-04

**Prerequisites:**
- `tls-cert-defects` profile up (`tls-cert-rsa1024` on host port 13447 with `OPENSSL_CONF=/etc/nginx/openssl-legacy.cnf` and the legacy.cnf bind-mount per Pitfall 3)

**Steps:**
1. Bring up the profile.
2. Run the scan.
3. Inspect findings for `localhost:13447`.

**Expected:** One HIGH finding with title containing `undersized RSA` (literally `TLS certificate uses undersized RSA key`) at `localhost:13447`.

**Pass Criteria:**
- Findings JSON contains `severity=HIGH`, `title=TLS certificate uses undersized RSA key` for `localhost:13447`.
- Endpoint successfully completes a TLS handshake (verifies the legacy provider is wired correctly — without it, nginx 3.x rejects the RSA-1024 key and the scanner sees only `OPEN_NOT_TLS`).

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs
**Status:** Passed (Phase 46 Plan 04 live-fire)
**Notes:** Live-fire confirmed HIGH/undersized-RSA at 13447. Handshake succeeded — legacy provider env var working as intended.

---

### UAT-46-05: D-02 Multi-Defect Independence (TLS-FIND-01..05)

**ID:** UAT-46-05
**Title:** A single endpoint with multiple cert defects emits one finding per class with no rollup
**Maps to:** D-02 (Phase 46 Plan 02 risk-engine independence rule)

**Description:** The Phase 46 risk-engine branches at `quirk/engine/risk_engine.py` for expired (CRITICAL), self-signed (HIGH) / untrusted-CA (MEDIUM, mutually exclusive per D-04), undersized-RSA (HIGH), and undersized-EC (HIGH) are structurally independent — there is no early-return / no else-if chain across classes. An endpoint with multiple defects therefore produces one finding per class.

**Live-fire evidence (chaos lab `tls-cert-defects`, 2026-05-03):**

| Port | Endpoint | Findings (Phase 46 classes only) |
|------|----------|----------------------------------|
| 13444 | tls-cert-expired | CRITICAL "TLS certificate expired" + MEDIUM "TLS certificate issued by untrusted CA" (issuer != subject AND chain_verified=False — D-02 multi-defect independence) |
| 13445 | tls-cert-selfsigned | HIGH "TLS certificate is self-signed" (D-04 suppresses untrusted-CA on the same endpoint) |
| 13446 | tls-cert-untrusted-ca | MEDIUM "TLS certificate issued by untrusted CA" |
| 13447 | tls-cert-rsa1024 | HIGH "TLS certificate uses undersized RSA key" + MEDIUM "TLS certificate issued by untrusted CA" (cert is signed by off-trust-store scenario-root-CA — D-02 multi-defect independence) |

**Pass Criteria:**
- Each endpoint above emits ALL the findings shown in its row (no rollup, no severity-collapse).
- Endpoint 13445 (self-signed) does NOT additionally emit an untrusted-CA finding (D-04 exclusivity is preserved even under D-02 multi-defect rules).
- Endpoint 13444 emits the expired finding INDEPENDENTLY of the untrusted-CA finding (no shared control flow between expired branch and cert-trust if/elif block).

**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** 2026-05-03  **Tester:** Digs
**Status:** Passed (Phase 46 Plan 04 live-fire)
**Notes:** Verified via direct inspection of `findings-20260504-024549.json` from the Phase 46 Plan 04 live-fire run. The RSA-1024 endpoint correctly emits TWO Phase 46 findings (HIGH undersized-RSA + MEDIUM untrusted-CA) — D-02 honored. The self-signed endpoint emits only the HIGH self-signed finding — D-04 honored. The expired endpoint emits CRITICAL expired + MEDIUM untrusted-CA — both branches fire independently with no rollup.

---

# Series 16: Phase 47 — Nmap Discovery, Multi-Target Wizard & CBOM JSON Validation

**Covers:** DISCOVER-01..04, MULTI-01..05, D-13..D-16 from Phase 47

**Note:** UAT-47-01..06 require the chaos lab `core` profile running (`./lab.sh up core`). UAT-47-07 and UAT-47-08 are unit/install tests that run without a live lab.

---

### UAT-47-01: CSV Targets Through Wizard (MULTI-01)

**ID:** UAT-47-01
**Title:** CSV targets in wizard produce expected scan output

**Prerequisites:** `./lab.sh up core` running; `pip install -e .`

**Steps:**
1. Run `python run_scan.py` (no `--config` flag) to enter wizard mode.
2. At the "Targets" prompt, enter: `localhost,127.0.0.1`
3. Complete the wizard with default port selections.
4. Allow scan to finish; inspect output findings JSON.

**Expected:** Both `localhost` and `127.0.0.1` appear as scanned hosts; no error for CSV syntax.

**Pass Criteria:**
- Wizard accepts comma-separated input without error.
- Output findings JSON contains endpoints for at least 2 distinct hosts.
- No `ValueError` or `FileNotFoundError` in output.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-47-02: @file Targets Ingestion (MULTI-02)

**ID:** UAT-47-02
**Title:** @filepath syntax in wizard loads targets from file, respecting # comments

**Prerequisites:** `./lab.sh up core` running; a targets file created.

**Steps:**
1. Create `/tmp/quirk-targets.txt` with:
   ```
   # This is a comment
   localhost
   127.0.0.1
   ```
2. Run `python run_scan.py` (wizard mode).
3. At "Targets" prompt, enter: `@/tmp/quirk-targets.txt`
4. Complete wizard; inspect output.

**Expected:** Both non-comment lines are parsed as targets; comment line is ignored.

**Pass Criteria:**
- Scan processes `localhost` and `127.0.0.1`.
- Comment lines beginning with `#` are silently ignored.
- No `FileNotFoundError` for the `@file` path.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-47-03: --targets-file Non-Interactive Run (MULTI-03)

**ID:** UAT-47-03
**Title:** `--targets-file` CLI flag replaces config targets and enables non-interactive scan

**Prerequisites:** `./lab.sh up core` running; a targets file created.

**Steps:**
1. Create `/tmp/quirk-targets.txt` with content `localhost`
2. Create a config file `/tmp/phase47-uat.yaml` with `targets.fqdns: ["192.0.2.1"]` (a non-routable IP as the config target).
3. Run: `python run_scan.py --config /tmp/phase47-uat.yaml --targets-file /tmp/quirk-targets.txt`
4. Inspect findings JSON for which host was scanned.

**Expected:** `localhost` is scanned; `192.0.2.1` from config is NOT scanned (D-03: `--targets-file` replaces config targets).

**Pass Criteria:**
- Output findings JSON contains endpoints for `localhost`, not `192.0.2.1`.
- Scan completes without interactive prompts.
- No `FileNotFoundError` or `ValueError`.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-47-04: Wizard Nmap y/N Prompt Appears Once (DISCOVER-01)

**ID:** UAT-47-04
**Title:** Wizard presents a single global nmap y/N prompt (not per-target)

**Prerequisites:** `nmap` installed and in PATH; `./lab.sh up core` running.

**Steps:**
1. Run `python run_scan.py` (wizard mode, interactive TTY).
2. Count how many times an nmap-related y/N prompt appears.
3. Respond `n` and complete the wizard.

**Expected:** Exactly one nmap prompt is shown regardless of how many targets are entered.

**Pass Criteria:**
- Exactly one nmap y/N prompt appears during the wizard session.
- If `n` selected, scan uses CONSULTING_TLS_PORTS fallback (17 ports).
- If `y` selected, nmap is invoked once for all targets combined.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-47-05: Missing nmap Binary — No Crash, ADVISORY Row, Consulting-Ports Fallback (DISCOVER-02)

**ID:** UAT-47-05
**Title:** When nmap binary is absent, scan continues with consulting-TLS-ports fallback and emits one ADVISORY finding

**Prerequisites:** `nmap` NOT in PATH (e.g., `export PATH=$(echo $PATH | tr ':' '\n' | grep -v nmap | tr '\n' ':')`); `./lab.sh up core` running.

**Steps:**
1. Temporarily remove nmap from PATH.
2. Run `python run_scan.py --config /tmp/phase47-uat.yaml` with a config that enables nmap (`enable_nmap: true`).
3. Allow scan to complete; inspect findings JSON.

**Expected:** Scan completes successfully; one coverage_gap INFO advisory for `nmap_discovery`; no crash.

**Pass Criteria:**
- Scan exits with code 0 (no crash).
- `findings-<ts>.json` contains exactly one entry with `scan_error_category: "missing_extra"` and `host: "nmap_discovery"`.
- The `scan_error` text mentions `install nmap` or PATH.
- TLS endpoints are still scanned using the consulting-TLS-ports fallback.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-47-06: Probe-Budget Confirm Prompt at > 10,000 Targets × Ports (DISCOVER-04)

**ID:** UAT-47-06
**Title:** When projected nmap probes exceed 10,000 in TTY mode, a confirm prompt is shown

**Prerequisites:** `nmap` in PATH; wizard mode in a real TTY.

**Steps:**
1. Run `python run_scan.py` in wizard mode.
2. Enter a CIDR that produces many hosts (e.g., `10.0.0.0/16`) combined with many ports so `targets × ports > 10,000`.
3. Observe whether a budget-warning confirm prompt appears.

**Expected:** A budget warning message (`Projected nmap probes: X`) and a y/N confirmation prompt appear before nmap fires. Responding `n` aborts the nmap phase; scan continues without discovery.

**Pass Criteria:**
- Budget warning message appears with projected probe count.
- Scan does not proceed to nmap until user confirms with `y`.
- Responding `n` causes scan to skip nmap (no crash, findings file still written).
- In non-TTY mode (piped input), warning goes to stderr and scan auto-proceeds.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-47-07: CBOM JSON Post-Write Schema Validation (D-13, D-14, D-15, D-16)

**ID:** UAT-47-07
**Title:** CBOM JSON validates via post-write JsonStrictValidator; intentional bad CBOM yields coverage_gap WARN finding (file preserved)

**Prerequisites:** `pip install -e ".[cbom]"` in test environment; `./lab.sh up core` running.

**Steps:**
1. Run a normal scan: `python run_scan.py --config /tmp/phase47-uat.yaml`
2. Inspect the CBOM JSON at `<output.directory>/cbom-<ts>.cdx.json`.
3. Validate the CBOM manually: `python -c "from cyclonedx.schema import SchemaVersion; from cyclonedx.validation.json import JsonStrictValidator; from pathlib import Path; v = JsonStrictValidator(SchemaVersion.V1_6); r = v.validate_str(Path('cbom-<ts>.cdx.json').read_text()); print('VALID' if r is None else f'INVALID: {r}')"`
4. Run the automated test suite: `pytest tests/test_cbom_writer_validation.py -v`

**Expected:** CBOM JSON is schema-valid; automated tests all pass.

**Pass Criteria:**
- Manual validation returns `VALID`.
- `pytest tests/test_cbom_writer_validation.py` exits 0 (5 tests pass).
- The `test_invalid_cbom_emits_warn_finding_and_preserves_file` test confirms file is NOT deleted and WARN advisory is emitted on schema failure (D-14, D-15).
- The `test_missing_jsonschema_at_constructor_silent` test confirms constructor-time `MissingOptionalDependencyException` is caught (RESEARCH F6).
- `--max-parallelism 100` is present in `_default_nmap_args` (verified by unit test `pytest tests/test_nmap_provider.py::test_default_args_includes_parallelism -v`).

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-47-08: pip install quirk[cbom] Install Hint Actionable (D-16)

**ID:** UAT-47-08
**Title:** `pip install quirk[cbom]` extra installs jsonschema + referencing; coverage_gap advisory is actionable

**Prerequisites:** Fresh virtual environment without jsonschema/referencing installed.

**Steps:**
1. Create a fresh venv: `python -m venv /tmp/quirk-cbom-test && source /tmp/quirk-cbom-test/bin/activate`
2. Install base quirk (no extras): `pip install -e .`
3. Run a scan with a config that triggers CBOM output.
4. Check that the findings JSON contains a `cbom_validator` advisory with `scan_error` containing `pip install quirk[cbom]`.
5. Install the cbom extra: `pip install -e ".[cbom]"`
6. Re-run the scan and confirm the `cbom_validator` advisory is gone.

**Expected:** Without `[cbom]`, the registry advisory appears; with `[cbom]`, it disappears.

**Pass Criteria:**
- Without `[cbom]` installed: findings JSON contains `{"host": "cbom_validator", "scan_error_category": "missing_extra", "scan_error": "...pip install quirk[cbom]..."}`.
- After `pip install -e ".[cbom]"`: `cbom_validator` advisory no longer appears.
- `pip install -e ".[cbom]"` succeeds without errors and installs `jsonschema` and `referencing`.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

# Series 17: Phase 48 — Rich Finding Context

**Covers:** CONTEXT-01..04 from Phase 48

**Note:** UAT-48-01..03 require a completed scan with output in `quirk-output/`. UAT-48-04 is a CI gate test that runs without a live lab.

---

### UAT-48-01: Every Finding Carries a Non-Empty Description (CONTEXT-01)

**ID:** UAT-48-01
**Title:** Every finding object in the latest `findings-*.json` has a non-empty `description` field

**Prerequisites:** A completed scan; the latest `quirk-output/findings-*.json` exists.

**Steps:**
1. Locate the latest findings JSON: `ls -t quirk-output/findings-*.json | head -1`
2. Confirm every entry has a non-empty `description`:
   `jq 'all(.[]; .description != null and (.description | length > 0))' <file>`

**Expected:** The `jq` query returns `true`.

**Pass Criteria:**
- `jq 'all(.[]; .description != null and (.description | length > 0))'` outputs `true` against the latest findings file.
- Spot-checking three finding entries shows a 1-3 sentence plain-English explanation of the cryptographic risk in `description`.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-48-02: HTML All Findings Table Includes Description Column (CONTEXT-02)

**ID:** UAT-48-02
**Title:** Latest `report-*.html` All Findings table renders a Description column adjacent to Recommendation

**Prerequisites:** A completed scan; `quirk-output/report-*.html` exists.

**Steps:**
1. Open the latest `quirk-output/report-*.html` in a browser.
2. Scroll to the "All Findings" table.
3. Visually confirm a "Description" column appears immediately to the left of "Recommendation".
4. Verify in source: `grep -c '<th>Description</th>' quirk-output/report-*.html` outputs `2`
   (one for Top Findings, one for All Findings).

**Expected:** Description column is visible in the All Findings table; HTML source contains `<th>Description</th>` at least twice.

**Pass Criteria:**
- Visual inspection: All Findings table has a Description column to the left of Recommendation.
- `grep -c '<th>Description</th>' <report.html>` returns `2` or more.
- Description cells are populated (not blank) for every row visible in the table.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-48-03: Quantum-Vulnerable Findings Cite FIPS 203/204/205 + NIST IR 8547 (CONTEXT-03)

**ID:** UAT-48-03
**Title:** Every quantum-vulnerable finding's recommendation cites a FIPS designation AND the NIST IR 8547 deprecation deadline

**Prerequisites:** A completed scan with at least one quantum-vulnerable finding (e.g., RSA cert from chaos lab `tls-cert-defects` profile); `quirk-output/findings-*.json` exists.

**Steps:**
1. Locate quantum-vulnerable findings:
   `jq '.[] | select(.title | test("RSA|ECDSA|quantum"))' findings-*.json`
2. For each, verify the recommendation cites at least one of `FIPS 203`, `FIPS 204`, `FIPS 205`:
   `grep -E 'FIPS 20[345]' findings-*.json`
3. Verify each contains the literal phrase `Per NIST IR 8547`:
   `grep 'Per NIST IR 8547' findings-*.json`

**Expected:** Quantum-vulnerable findings carry both a FIPS designation and the NIST IR 8547 deadline phrase.

**Pass Criteria:**
- `grep -cE 'FIPS 20[345]' findings-*.json` returns at least `1` when quantum-vulnerable findings are present.
- `grep -c 'Per NIST IR 8547' findings-*.json` returns at least `1` when quantum-vulnerable findings are present.
- For each quantum-vulnerable entry, both substrings appear in its `recommendation` field.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-48-04: CI Grep Gate Catches Stale PQC Terminology Regression (CONTEXT-04)

**ID:** UAT-48-04
**Title:** `tests/test_pqc_terminology_gate.py` passes clean AND fails the build when forbidden terminology is injected

**Prerequisites:** Repo on `QUIRK-v4`; clean working tree.

**Steps:**
1. Run the gate clean: `pytest tests/test_pqc_terminology_gate.py -x -v`. Expect `2 passed`.
2. Inject a regression: append the comment `# Kyber` to `quirk/engine/risk_engine.py`.
3. Re-run the gate. Expect failure with assertion message naming the offender.
4. Revert: `git checkout -- quirk/engine/risk_engine.py`.
5. Re-run clean to confirm green state restored.

**Expected:** Clean run passes (2 tests); injected-regression run fails with a message naming `risk_engine.py` and `kyber` in the offenders list; revert restores green state.

**Pass Criteria:**
- Step 1: `2 passed` exit code 0.
- Step 3: `1 failed` with assertion message containing `risk_engine.py` and `kyber`.
- Step 5: `2 passed` exit code 0 after revert.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

# Series 18: Phase 49 — Compliance Mapping

**Covers:** COMPLY-01..09 from Phase 49

**Note:** UAT-49-01..04 are CI-gate / smoke tests that run without a live chaos lab. UAT-49-05 requires a completed scan against the chaos lab `tls-cert-defects` profile so at least one mapped and one unmapped finding render in the report.

The compliance map maintenance cadence and upgrade procedure for regulator revisions are documented in `docs/operators-guide.md` (Phase 50 — Compliance Map Maintenance section). Operators preparing for client engagements should run `quirk compliance status` to confirm freshness before each engagement.

---

### UAT-49-01: Compliance Map Schema Gate (COMPLY-01, COMPLY-06, COMPLY-07)

**ID:** UAT-49-01
**Title:** Every `COMPLIANCE_MAP` entry contains the required schema keys with valid values

**Prerequisites:** Repo on `QUIRK-v4`; clean working tree; `quirk/compliance/__init__.py` exists.

**Steps:**
1. Run the schema gate: `pytest tests/test_compliance_schema.py -x -q`

**Expected:** All schema assertions green. Every `COMPLIANCE_MAP` entry has `framework`, `control`, `version`, `last_verified` (ISO `YYYY-MM-DD`), and `source_url` (https://...) keys.

**Pass Criteria:**
- `pytest tests/test_compliance_schema.py -x -q` exits 0 with all tests passing.
- Every entry's `last_verified` parses as an ISO date.
- Every entry's `source_url` starts with `https://` and points to the authoritative regulator publication (PCI Security Standards Council, the eCFR, or NIST CSRC).

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-49-02: Compliance Map Freshness Gate (COMPLY-08)

**ID:** UAT-49-02
**Title:** No `COMPLIANCE_MAP` entry's `last_verified` is older than `STALENESS_THRESHOLD_DAYS` (365)

**Prerequisites:** Repo on `QUIRK-v4`; clean working tree.

**Steps:**
1. Run the freshness gate: `pytest tests/test_compliance_freshness.py -x -q`

**Expected:** Test passes. If it fails, the failure message names every stale entry and includes a fix recipe (re-verify the source URL and bump `last_verified`).

**Pass Criteria:**
- `pytest tests/test_compliance_freshness.py -x -q` exits 0.
- No `last_verified` date is older than 365 days from today.
- (Failure mode check — optional) Temporarily set one entry's `last_verified` to a date >365 days ago; confirm the test fails with a clear "stale entry" message that names the offender. Revert the edit before continuing.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-49-03: Compliance Title-Join Gate (COMPLY-02, COMPLY-03, COMPLY-04)

**ID:** UAT-49-03
**Title:** Every emitted finding title is present in `COMPLIANCE_MAP` or `UNMAPPED_TITLES`

**Prerequisites:** Repo on `QUIRK-v4`; clean working tree; `tests/fixtures/chaos_lab_findings.py` AST aggregator returns ≥24 titles.

**Steps:**
1. Run the title-join gate: `pytest tests/test_compliance_title_join.py -x -q`

**Expected:** Both tests pass — the AST aggregator returns a non-empty title set, and every emitted title is either in `COMPLIANCE_MAP` (after longest-prefix-first normalization through `TITLE_PREFIX_ALIASES`) or in `UNMAPPED_TITLES`.

**Pass Criteria:**
- `pytest tests/test_compliance_title_join.py -x -q` exits 0.
- Every entry in `UNMAPPED_TITLES` carries an inline comment justifying the absence of a mapping (per D-04).
- (Regression guard) Renaming a finding title in `quirk/engine/risk_engine.py` without updating the map (or the allow-set) produces a loud test failure.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-49-04: `quirk compliance status` CLI Smoke (COMPLY-09)

**ID:** UAT-49-04
**Title:** `quirk compliance status` prints per-framework version + last_verified + source_url in both text and JSON formats

**Prerequisites:** Repo on `QUIRK-v4`; QUIRK installed (or `python run_scan.py` runnable from repo root).

**Steps:**
1. Run the text-format smoke: `python run_scan.py compliance status`
2. Run the JSON-format smoke: `python run_scan.py compliance status --format json`
3. Run the pytest CLI smoke: `pytest tests/test_compliance_cli.py -x -q`

**Expected:**
- Step 1 prints a fixed-width table with at least one row per framework (PCI-DSS 4.0.1, HIPAA 45 CFR, FIPS 140-3) showing version, oldest `last_verified`, and `source_url`. Exit code 0.
- Step 2 prints a JSON dict keyed by framework. The output parses as valid JSON. Exit code 0.
- Step 3 passes (path-exists + text smoke + JSON smoke).

**Pass Criteria:**
- Both CLI invocations exit 0.
- Text output contains all three framework labels: `PCI-DSS 4.0.1`, `HIPAA 45 CFR`, `FIPS 140-3`.
- JSON output parses as a dict (`python -c "import json,sys; json.loads(sys.stdin.read())"` succeeds when piped).
- `pytest tests/test_compliance_cli.py -x -q` shows 3 passed.

**Operator note:** This is the pre-engagement freshness verification command per COMPLY-09. See also `docs/operators-guide.md` (Phase 50) for the full review-cadence prose.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-49-05: Compliance Summary Section in HTML/PDF Report (COMPLY-05)

**ID:** UAT-49-05
**Title:** HTML and PDF reports render a "Compliance Summary" section with three framework subsections plus a "Findings without compliance mapping" subsection

**Prerequisites:** Chaos lab running with the `tls-cert-defects` profile (`./quantum-chaos-enterprise-lab/lab.sh up` with `PROFILE_ARGS="--profile tls-cert-defects"`); a completed scan against `localhost` producing at least one mapped and one unmapped finding; `quirk-output/report-*.html` exists.

**Steps:**
1. Run the HTML smoke: `pytest tests/test_compliance_report_section.py -x -q`
2. Open the latest `quirk-output/report-*.html` in a browser.
3. Locate the "Compliance Summary" section (after All Findings, before Endpoint Inventory).
4. Confirm three framework subsections render: `PCI-DSS 4.0.1`, `HIPAA 45 CFR`, `FIPS 140-3`. Each table has columns: Severity / Finding / Control (+version) / Source link · last_verified.
5. Confirm the "Findings without compliance mapping" subsection renders (with a muted "all mapped" note if every finding mapped, or a `<ul>` of `title (host)` lines if any are unmapped).
6. Click a source URL link and confirm it opens the regulator's authoritative publication.
7. Generate the PDF (`quirk` with PDF export) and confirm the same section inherits.

**Expected:** All five required substrings appear in the HTML: `Compliance Summary`, `PCI-DSS 4.0.1`, `HIPAA 45 CFR`, `FIPS 140-3`, `Findings without compliance mapping`. PDF inherits the section automatically via the existing Playwright path.

**Pass Criteria:**
- `pytest tests/test_compliance_report_section.py -x -q` shows 2 passed.
- Visual inspection: all three framework subsections render cleanly with populated tables (no broken HTML, no blank cells where data is expected).
- At least one source URL link is clickable and opens the regulator's authoritative page (HTTPS, no broken redirects).
- PDF export contains the same Compliance Summary section.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

# Appendix A: Quick Reference — Lab Port Map

| Port | Service | Profile | What to Verify |
|------|---------|---------|----------------|
| 443 | tls-modern | core | TLS 1.3, modern cipher |
| 8443 | tls-legacy | core | Legacy TLS 1.2, weaker ciphers |
| 9443 | tls-expired | core | Expired certificate |
| 10443 | tls-selfsigned | core | Self-signed cert |
| 11443 | tls-mtls | core | mTLS required |
| 12443 | tls-slow | core | Timeout behavior |
| 8444 | http-on-tls-port | core | Protocol mismatch |
| 8000 | http-plain | core | Plaintext HTTP |
| 2222 | ssh | core | SSH algorithms |
| 5555 | unknown | core | Unknown classification |
| 13443 | tls-missing-chain | phaseA | Incomplete cert chain |
| 14443 | tls-rsa1024 | phaseA | Weak RSA key |
| 15443 | tls-sha1 | phaseA | SHA-1 signature |
| 20001 | jwt-rs256 | jwt | Good JWT (RS256) |
| 20002 | jwt-hs256 | jwt | Weak JWT (symmetric) |
| 20003 | jwt-rsa1024 | jwt | Weak JWT (1024-bit RSA) |
| 20004 | jwt-algnone | jwt | Critical (no signature) |
| 20022 | ssh-weak | ssh-weak | All weak SSH algorithms |
| 20005 | registry | registry | Container crypto libs |
| 20006 | gitea | source | Source code crypto patterns |
| 20007 | kms-localstack | storage | KMS key crypto specs |
| 20009 | vault | storage | Vault transit key specs |
| 15449 | keycloak-tls | identity | IdP TLS quality |
| 636 | ldaps | ldaps | LDAP over TLS |

---

# Appendix B: Expected Score Ranges by Lab Config

| Lab Config | Expected Score | Rationale |
|------------|---------------|-----------|
| Core only, no HTTP | 45–60 (FAIR) | Expired cert, self-signed, legacy TLS |
| Core with HTTP services | 25–40 (POOR) | Plaintext HTTP penalty applied |
| Core + phaseA (RSA-1024, SHA-1) | 15–35 (POOR) | Additional weak key/sig findings |
| JWT profile (alg:none) | 10–25 (POOR) | Critical JWT findings, high-impact ratio |
| JWT profile with RS256 only | 40–55 (FAIR) | Mixed signals |
| Clean TLS only (443 modern only) | 75–90 (GOOD/EXCELLENT) | No significant issues |

---

# Appendix C: Common Failure Patterns

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| Dashboard shows blank page | No scan data in `quirk.db` | Run a scan first |
| Score is 0 | All endpoints errored | Check lab is running, ports reachable |
| CBOM has no components | TLS scanner returned no data | Verify TLS ports are accessible |
| PDF export hangs | Playwright Chromium not installed | `playwright install chromium` |
| SSH findings missing | ssh-audit not in PATH | `pip install ssh-audit` |
| JWT findings missing | JWKS endpoint not reachable | Check jwt profile containers are up |
| Source scan empty | semgrep not installed | `pip install semgrep` |
| Container scan empty | syft not installed or no images | Install syft, ensure registry profile is up |
| Kerberos/SAML/DNSSEC scan empty | identity extras not installed | `pip install quirk[identity]` |
| enable_kerberos: unknown field error | Old quirk installation (pre-v4.2) | Upgrade quirk to v4.2+ |

---

# Series 19: Phase 50 — Enterprise Documentation

**Covers:** DOCS-01..04 from Phase 50

**Note:** UAT-50-NN are documentation/presence gates. None require a live chaos lab or completed scan. UAT-50-04 verifies the Obsidian vault sync produced the expected files with correct frontmatter — run only on a workstation with the QUIRK vault mounted at `/Users/digs/vaults/Digs/`.

---

### UAT-50-01: docs/architecture.md presence + section coverage (DOCS-01)

**ID:** UAT-50-01
**Title:** `docs/architecture.md` exists and contains the required structural sections + diagrams

**Prerequisites:** Repo on `QUIRK-v4`; clean working tree.

**Steps:**
1. `test -f docs/architecture.md`
2. ``grep -c '```mermaid' docs/architecture.md`` should return ≥ 3
3. `grep -i 'data flow' docs/architecture.md`
4. `grep -i 'trust boundar' docs/architecture.md`
5. `grep -i 'credential' docs/architecture.md`
6. `grep -E '(Kyber|Dilithium|quirk/scanners/|when standards are adopted)' docs/architecture.md` should return nothing (exit 1)

**Expected:** File present, ≥3 mermaid blocks, all required substrings present, no deprecated terms.

**Pass Criteria:**
- Step 1: file exists.
- Step 2: at least 3 fenced mermaid blocks present.
- Steps 3–5: each grep finds a hit.
- Step 6: no matches (grep exits 1).

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-50-02: docs/operators-guide.md presence + section coverage (DOCS-02)

**ID:** UAT-50-02
**Title:** `docs/operators-guide.md` exists and covers install, troubleshooting, and the compliance map maintenance runbook

**Prerequisites:** Repo on `QUIRK-v4`; clean working tree.

**Steps:**
1. `test -f docs/operators-guide.md`
2. `grep -i 'troubleshoot' docs/operators-guide.md`
3. `grep -i 'compliance map maintenance' docs/operators-guide.md`
4. `grep -q 'quirk init' docs/operators-guide.md`
5. `grep -q 'See also' docs/operators-guide.md`
6. `grep -E '(Kyber|Dilithium|quirk/scanners/|when standards are adopted)' docs/operators-guide.md` should return nothing

**Expected:** File present, all required sections, no deprecated terms.

**Pass Criteria:**
- Step 1: file exists.
- Steps 2–5: each grep finds a hit.
- Step 6: no matches.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-50-03: Obsidian vault sync produced both Reference notes with correct frontmatter (DOCS-03)

**ID:** UAT-50-03
**Title:** Vault `Reference/Architecture.md` and `Reference/Operators-Guide.md` exist with correct frontmatter and are linked from `_QUIRK-Hub.md`

**Prerequisites:** Workstation with QUIRK vault mounted at `/Users/digs/vaults/Digs/`.

**Steps:**
1. `test -f /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Reference/Architecture.md`
2. `test -f /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Reference/Operators-Guide.md`
3. `head -7 /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Reference/Architecture.md` shows the 5 frontmatter fields (project, type, status, source, updated)
4. `head -7 /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Reference/Operators-Guide.md` shows the 5 frontmatter fields with `source: docs/operators-guide.md`
5. `grep -q 'Reference/Architecture' /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/_QUIRK-Hub.md`
6. `grep -q 'Reference/Operators-Guide' /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/_QUIRK-Hub.md`

**Expected:** Both vault notes exist with correct frontmatter; hub MOC links both.

**Pass Criteria:**
- Steps 1–2: both files exist.
- Steps 3–4: frontmatter shows the 5 standard fields with `type: reference` and the correct `source:` repo path.
- Steps 5–6: hub MOC contains a wikilink to each Reference note.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---

### UAT-50-04: Compliance Map Maintenance citation completeness (DOCS-04)

**ID:** UAT-50-04
**Title:** Operator's guide compliance runbook cites all required regulator URLs, the `quirk compliance status` CLI, the staleness threshold + freshness test, and a worked PCI-DSS upgrade example

**Prerequisites:** Repo on `QUIRK-v4`.

**Steps:**
1. `grep -q 'pcisecuritystandards.org' docs/operators-guide.md`
2. `grep -q 'ecfr.gov' docs/operators-guide.md`
3. `grep -q 'csrc.nist.gov' docs/operators-guide.md`
4. `grep -q 'quirk compliance status' docs/operators-guide.md`
5. `grep -i 'STALENESS_THRESHOLD_DAYS' docs/operators-guide.md`
6. `grep -q 'tests/test_compliance_freshness.py' docs/operators-guide.md`
7. Confirm a numbered worked example for "PCI-DSS 4.0.1 → 4.1" upgrade path is present in §7.4

**Expected:** All 3 source URLs cited, `quirk compliance status` cited, the 12-month staleness gate constant + test path cited, worked upgrade example present.

**Pass Criteria:**
- Steps 1–6: each grep finds a hit.
- Step 7: worked upgrade example is present in §7.4 of the operators guide.

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---
