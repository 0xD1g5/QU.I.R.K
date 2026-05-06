# Requirements: QU.I.R.K. v4.7 Governance & Compliance Platform

**Defined:** 2026-05-05
**Core Value:** Complete, defensible cryptographic inventory with a CBOM deliverable and quantum-readiness score — handed to a client in under two hours.

## v4.7 Requirements

Requirements for the Governance & Compliance Platform milestone. Each maps to roadmap phases.

### Compliance Extensions

- [ ] **COMPLY-10**: CBOM Pass-1 algorithm components carry a 3-tier FIPS 140-3 status annotation (`certified` / `approved` / `non-approved`) via `Component.properties` — only endpoints with verifiable CMVP-validated evidence receive `certified`; all others receive `approved` or `non-approved` based on algorithm classification
- [ ] **COMPLY-11**: SOC2 CC6.x controls (cryptography-relevant Common Criteria subset) are mapped to QUIRK finding categories in `COMPLIANCE_MAP` via a `_soc2()` helper following the existing `_pci()` / `_hipaa()` / `_fips()` builder pattern
- [ ] **COMPLY-12**: ISO 27001:2022 Annex A controls (8.x clause numbering, not 2013 A.x.x) are mapped to QUIRK finding categories via an `_iso()` helper; the framework entry declares `version: "ISO 27001:2022"` and is unit-tested to reject 2013-style `A.x.x` control IDs

### QRAMM Core Infrastructure

- [ ] **QRAMM-01**: SQLite gains three new normalized tables — `qramm_sessions` (lifecycle, `model_version`, `profile_multiplier`, `status`), `qramm_answers` (`assessment_id` FK, `question_number`, `dimension`, `practice_area`, `answer_value`, `suggested_answer`, `confirmed_at`, `evidence_source`), `qramm_profiles` (org profile inputs → computed multiplier 0.8–1.5×) — created via `_ensure_qramm_tables()` in `db.py:init_db()`, no changes to `CryptoEndpoint`
- [ ] **QRAMM-02**: FastAPI router at `/api/qramm/` provides CRUD endpoints for the assessment lifecycle: create session, read session, save/update answers, score session, delete session
- [ ] **QRAMM-03**: `quirk/qramm/questions.py` contains the full 120-question catalog as a versioned `QRAMM_QUESTIONS` constant (4 dimensions × 3 practices × 10 questions); each entry carries `question_number`, `dimension`, `practice_area`, `text`, and `maturity_labels`
- [ ] **QRAMM-04**: `quirk/qramm/scoring.py` computes dimension scores using the weakest-link minimum rule (dimension score = `min()` of its 3 practice scores, NOT average); profile multiplier applied to weighted dimension scores; overall score = average of 4 weighted dimensions; scoring logic is unit-tested to match the CSNP QRAMM toolkit reference values

### QRAMM Staleness Enforcement

- [ ] **QRAMM-05**: `QRAMM_MODEL` module constant in `quirk/qramm/model_meta.py` carries `qramm_version` (string), `last_verified` (ISO date), and `source_url` (`https://qramm.org`) — mirroring the compliance staleness pattern from v4.6
- [ ] **QRAMM-06**: CI pytest gate fails when `QRAMM_MODEL.last_verified` is more than 90 days old; supports injectable `QUIRK_CI_STALENESS_OVERRIDE_DATE` env var for CI boundary testing
- [ ] **QRAMM-07**: `quirk qramm status` CLI subcommand displays `qramm_version`, `last_verified`, days remaining until stale, and current staleness verdict; exits non-zero when stale

### QRAMM Assessment Experience

- [ ] **QRAMM-08**: React QRAMM Assessment page presents 120 questions across 4 dimension tabs (CVI, SGRM, DPE, ITR); each question displays a 1–4 radio scale with maturity-level labels (Basic / Developing / Established / Optimizing) and an optional evidence note field; a progress tracker shows questions answered per dimension
- [ ] **QRAMM-09**: Org Profile wizard collects industry sector, organization size, geographic scope, data sensitivity, and regulatory obligations; computes a profile multiplier (0.8–1.5×) before the assessment begins and stores it in `qramm_profiles`
- [ ] **QRAMM-10**: All 120 assessment answers live in top-level React context above all route changes; every answer change triggers a debounced `POST /api/qramm/assessment/draft` so browser refresh restores in-progress answers without data loss
- [ ] **QRAMM-11**: QRAMM Scorecard displays: (a) radar chart (4-axis Recharts `RadarChart`, rendered as static SVG for PDF compatibility), (b) dimension summary table (raw score, weighted score, industry benchmark, maturity level, completion %), (c) maturity distribution (count of practices at each maturity level); real-time score recalculation is disabled mid-session — scores update only on explicit "Calculate Score" action

### QRAMM Evidence Bridge

- [ ] **QRAMM-12**: At QRAMM assessment session creation (`POST /api/qramm/sessions`), the evidence bridge auto-populates CVI dimension questions (~30 questions) by reading the latest scan's `CryptoEndpoint` rows via the SESSION_BRACKET scan-window pattern; `quirk/qramm/evidence_bridge.py` does NOT import `risk_engine` (circular import prevention)
- [ ] **QRAMM-13**: Auto-populated answers are stored in `qramm_answers.suggested_answer` with `requires_confirmation: true`; `answer_value` remains `null` until a human confirms; only rows with a non-null `confirmed_at` timestamp contribute to the final maturity score
- [ ] **QRAMM-14**: Auto-filled answers display an "Auto-filled from scan" badge in the assessment UI and remain fully editable; the badge is removed when the human modifies or confirms the answer

### QRAMM Governance Artifacts

- [ ] **QRAMM-15**: Dashboard includes a QRAMM Compliance Mapping view showing an 8-framework coverage table (NIST PQC Standards, NSM-10, CNSA 2.0, ISO 27001:2022, ETSI Quantum-Safe, PCI-DSS v4.0, Common Criteria, BSI TR-02102) with per-practice relevance scores derived from the active assessment session; view never displays a "fully compliant" badge and never shows a coverage percentage above the scanner's actual coverage ceiling
- [ ] **QRAMM-16**: Combined PDF export (`/print` route) includes a QRAMM section (executive QRAMM summary, dimension scorecard table, static SVG radar chart, compliance framework mapping summary) starting on a new page via `@media print { page-break-before: always }` — existing Technical Findings section layout is not regressed

### Health & Diagnostics

- [ ] **DOCS-05**: `quirk doctor` CLI subcommand performs a health check across 8 categories — Python environment, scanner binaries (nmap/syft/semgrep), compliance framework freshness, QRAMM framework freshness, database connectivity, configuration validity, network connectivity (informational), dashboard process status (informational) — and displays results with `[✓]` / `[!]` / `[✗]` symbols using `rich`; exits with code 1 if any non-informational check fails

### Tech Debt

- [ ] **DEBT-01**: All `datetime.utcnow()` calls replaced with `datetime.now(timezone.utc)` across `quirk/logging_util.py`, `quirk/discovery/nmap_provider.py`, and any other affected modules (BACK-56); resolves Python 3.12+ `DeprecationWarning`
- [ ] **DEBT-02**: `lab.sh` PROFILE_ARGS CLI precedence fixed — inbound env value is snapshotted before `source .env` so `PROFILE_ARGS="--profile <name>" ./lab.sh up` correctly overrides `.env` defaults (BACK-87)
- [ ] **DEBT-03**: `run-stats-*.json` output includes `ports_scanned` (sorted list of all ports that entered the scan pipeline) and `hosts_scanned` (sorted list of all scanned hosts), closing UAT-3-02 verification gap (BACK-85)
- [ ] **DEBT-04**: `quirk/scanner/saml_scanner.py` migrated from deprecated `defusedxml.lxml` to raw `lxml.etree` with `resolve_entities=False` and `no_network=True` parser options; all 25 existing SAML tests pass GREEN (BACK-67)

---

## Future Requirements

Deferred to v4.8 or later — not in scope for v4.7.

### QRAMM Coverage Expansion

- **QRAMM-F01**: Evidence bridge extended to SGRM, DPE, and ITR dimensions (requires validation of CVI bridge quality first)
- **QRAMM-F02**: QRAMM standalone PDF export (governance-only delivery, without full QUIRK technical findings)
- **QRAMM-F03**: Multi-session QRAMM history — compare assessment scores across time to track maturity improvement

### Compliance Depth

- **COMPLY-F01**: CMMC 2.0 SC.3.177/SC.3.187 control mapping
- **COMPLY-F02**: NIST CSF 2.0 Protect function mapping
- **COMPLY-F03**: FedRAMP compliance mapping (deferred — hundreds of controls, misleading without full coverage)

### Platform

- **PLATFORM-F01**: Dashboard-initiated scan configuration and launch (BACK-86) — deferred to SaaS milestone

---

## Out of Scope

Explicitly excluded from v4.7. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| QRAMM evidence bridge for SGRM/DPE/ITR | Requires human judgment; auto-population would inflate governance scores; scoped to CVI only for v4.7 |
| AI inference for QRAMM answers | Only ~25% of questions have technical evidence equivalents; governance theater risk |
| QRAMM Excel import | Unversioned file format, no stable API contract |
| Real-time score updates during answer entry | Weakest-link rule makes intermediate scores misleading |
| FedRAMP compliance mapping | Hundreds of controls; scanner cannot satisfy process controls |
| "100% compliant" badges for any framework | Scanner covers cryptographic controls only; process controls require human attestation |
| Authenticated scan mode (BACK-64) | Platform-level concern; requires credential security review gate |
| Dashboard-initiated scanning (BACK-86) | Targeted for SaaS milestone |

---

## Traceability

Populated by the roadmapper. Updated at each phase transition.

| Requirement | Phase | Status |
|-------------|-------|--------|
| COMPLY-10 | — | Pending |
| COMPLY-11 | — | Pending |
| COMPLY-12 | — | Pending |
| QRAMM-01 | — | Pending |
| QRAMM-02 | — | Pending |
| QRAMM-03 | — | Pending |
| QRAMM-04 | — | Pending |
| QRAMM-05 | — | Pending |
| QRAMM-06 | — | Pending |
| QRAMM-07 | — | Pending |
| QRAMM-08 | — | Pending |
| QRAMM-09 | — | Pending |
| QRAMM-10 | — | Pending |
| QRAMM-11 | — | Pending |
| QRAMM-12 | — | Pending |
| QRAMM-13 | — | Pending |
| QRAMM-14 | — | Pending |
| QRAMM-15 | — | Pending |
| QRAMM-16 | — | Pending |
| DOCS-05 | — | Pending |
| DEBT-01 | — | Pending |
| DEBT-02 | — | Pending |
| DEBT-03 | — | Pending |
| DEBT-04 | — | Pending |
