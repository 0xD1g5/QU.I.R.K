# Feature Research

**Domain:** Governance / Compliance Platform — QRAMM maturity assessment + SOC2/ISO27001 framework expansion for QUIRK v4.7
**Researched:** 2026-05-05
**Confidence:** HIGH (QRAMM structure from github.com/csnp/qramm), HIGH (compliance framework controls from NIST/ISO primary sources), MEDIUM (UX patterns, doctor command conventions)

---

## Existing Baseline (Do Not Rebuild)

What is already shipped and stable in v4.6.0:

- `quirk/compliance/__init__.py` — `COMPLIANCE_MAP` with 24 finding categories mapped to PCI-DSS 4.0.1, HIPAA 45 CFR, FIPS 140-3; per-entry `framework`, `version`, `control`, `last_verified`, `source_url` fields; `_pci()` / `_hipaa()` / `_fips()` builder helpers
- `quirk compliance status` CLI — per-framework version + last_verified + source_url; 365-day staleness signal; pytest CI gate
- `_build_finding` chokepoint in `risk_engine.py` — all findings pass through single emitter; `compliance` field already attached before renderers see it
- CycloneDX CBOM pipeline — Pass 1 (classifier + builder), Pass 2/3 skip-lists; JSON + XML; CycloneDX 1.6 schema validation in CI; NIST PQC quantum-safety lookup table (50+ entries)
- 6-pillar readiness scoring: tls / ssh / api / identity / data_at_rest / data_in_motion
- HTML + PDF reports (Playwright); FastAPI `/api/scan/latest`; React dashboard with 6 scanner tabs + Compliance + Trends
- Phase 45 `optional_extra` probe registry — graceful ImportError degradation, `quirk[all]` meta-extra

New v4.7 work builds on this infrastructure and does not rearchitect any of it.

---

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Depends On |
|---------|--------------|------------|------------|
| SOC2 Type II control mapping (CC6.x) | Enterprise security teams face SOC2 audits routinely; CC6.1/CC6.6/CC6.7 cover logical access security + transmission encryption — every category in COMPLIANCE_MAP is relevant | LOW | Existing `COMPLIANCE_MAP` structure; add `_soc2()` helper parallel to `_pci()` / `_hipaa()` / `_fips()`; no schema changes |
| ISO 27001:2022 Annex A.10 mapping | Global ISMS standard; A.10.1 policy on cryptographic controls; A.10.2 key management lifecycle; EU/APAC customers require it | LOW | Same COMPLIANCE_MAP extension pattern; add `_iso27001()` helper |
| CBOM FIPS 140-3 algorithm-level annotations | CycloneDX 1.6 `cryptoProperties` supports `certificationLevel` field; auditors expect FIPS-mode marking on each algorithm component; COMPLY-10 | MEDIUM | CBOM Pass 1 builder; NIST PQC lookup table; no new pip deps |
| QRAMM data model (SQLite) | Without persistence, an assessment cannot be saved, resumed, or exported; nothing else in the QRAMM feature set can be built without this | MEDIUM | New `qramm_sessions` + `qramm_responses` tables; additive columns only; no breaking migration |
| QRAMM 120-question assessment UI | QRAMM is 4 dimensions × 3 practices × 10 questions at 5 maturity levels; primary value is structured question delivery with save/resume and section navigation | HIGH | QRAMM data model; existing React router pattern; shadcn/ui form components |
| QRAMM scorecard — radar/spider chart | QRAMM specification identifies spider charts as canonical output; executives and auditors expect this visual; no scorecard = assessment has no deliverable | MEDIUM | QRAMM data model; Recharts (already in dashboard bundle from Trends tab) |
| QRAMM compliance framework coverage table | QRAMM maps to 8 frameworks: NIST PQC, NSM 10, CNSA 2.0, ISO 27001, FedRAMP, NIST CSF, CMMC, PCI DSS 4.0; consultants present this to clients as part of governance assessment | MEDIUM | QRAMM scorecard; static mapping table (does not require live data) |
| QRAMM staleness enforcement — 90-day CI gate | Matches existing compliance staleness pattern (COMPLY-08 / Phase 49 D-04); QRAMM framework is community-maintained and will receive updates; per feedback memory this is mandatory | LOW | New `qramm_version` / `last_verified` / `source_url` metadata; CI pytest gate; `quirk qramm status` CLI; same pattern as `quirk compliance status` |
| `quirk doctor` health-check CLI | Security tool users expect a self-diagnostic command — `flutter doctor`, `brew doctor`, `wp-cli doctor` are canonical references; surfaces missing extras, stale compliance data, DB connectivity, scanner binary availability before the first scan fails | MEDIUM | Phase 45 `optional_extra` probe registry; Phase 49 compliance staleness logic; QRAMM staleness (new); no new pip deps |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Depends On |
|---------|-------------------|------------|------------|
| QRAMM evidence bridge — auto-populate from scan findings | No other PQC scanner pre-fills a QRAMM assessment from live scanner findings; eliminates manual data entry for questions where technical evidence directly answers the question (CVI dimension especially, ~30 questions) | HIGH | QRAMM data model; scanner evidence counters from `run_scan.py`; `_build_finding` chokepoint; static mapping table from finding category → QRAMM practice + question index |
| Org profile multiplier (0.8–1.5×) UI wizard | QRAMM's profile multiplier contextualizes raw scores for industry sector, org size, data sensitivity, regulatory obligations, technology complexity; high-risk sectors (healthcare, finance, government) can exceed 4.0 on weighted score — differentiates engagement from generic 5-point scale | MEDIUM | QRAMM data model (org profile stored with session); wizard before dimension assessment; score computation module |
| QRAMM + technical findings combined PDF | Single consulting deliverable: governance maturity score + technical scan findings + compliance control mapping in one Playwright-rendered PDF; no open-source competitor does this in a pip-installable tool | HIGH | Existing PDF export pipeline (Playwright); QRAMM scorecard rendered component; existing compliance mapping section |
| CMMC 2.0 Level 2 control mapping | Defense contractor market needs SC.3.177 (FIPS-validated cryptographic modules) and SC.3.187 (key management lifecycle); QUIRK already detects the evidence these controls require — adding the mapping is additive | MEDIUM | COMPLIANCE_MAP extension; SC.3.177 overlaps FIPS 140-3 already present; SC.3.185 = transmission confidentiality = TLS findings |
| NIST CSF 2.0 control mapping | CSF 2.0 Protect function (PR.DS = data security) maps cleanly to TLS/encryption/cipher findings; CSF 2.0 Govern function maps to SGRM practices in QRAMM; broadens QUIRK appeal to non-regulated enterprises | MEDIUM | COMPLIANCE_MAP extension |
| Quick QRAMM assessment (12 questions, 5–10 min) | QRAMM supports a 12-question variant (one representative question per practice); lowers barrier for initial client engagement; teaser scorecard drives demand for full 120-question assessment | LOW | Full QRAMM data model and scoring already built; filter to one question per practice; no new infrastructure |
| FIPS 140-3 algorithm-level CBOM annotations | CycloneDX `certificationLevel` per algorithm component; machines can parse which algorithms are FIPS-validated vs. non-validated; enables downstream automated compliance pipelines beyond QUIRK's own reports | MEDIUM | CBOM Pass 1 builder; NIST PQC lookup table already has quantum-safety classification; add `fips_approved: bool` field |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Better Approach |
|---------|---------------|-----------------|-----------------|
| Real-time continuous QRAMM scoring | "Show live score as I answer" | QRAMM dimension scoring uses weakest-link-of-three-practices; updating on every answer creates misleading intermediate states and heavy re-computation; Level 3 practice becomes Level 2 dimension if one sibling practice drops — confusing mid-flow | Compute and display scores only after dimension completion or full assessment submit |
| Editable compliance control text in UI | "Customize the control mapping to our specific interpretation" | Customized mappings drift from official framework text; breaks audit defensibility; staleness CI gate cannot validate custom entries; auditors reject non-standard control references | Allow custom frameworks via a separate config file with explicit "not-official" flag; default UI shows only validated controls with source URLs |
| Importing raw QRAMM Excel toolkit files | "Consultants already have Excel files" | Excel format is unversioned; CSNP may revise the spreadsheet structure without notice; creates a parser maintenance surface the team cannot control | Implement QRAMM framework natively from the open-source spec (github.com/csnp/qramm); the framework is stable JSON/Markdown, not the Excel artifact |
| QRAMM SaaS mode — multi-tenant assessments | "Sell assessments as a service" | SaaS is an explicit future milestone requiring auth, org management, job queues, multi-tenancy — none exist in v4.7; premature architecture increases v4.7 complexity with zero v4.7 revenue benefit | Add "data is local; export CSV/JSON for sharing" note in UI; document SaaS migration path for future milestone |
| Automated QRAMM question answering (AI inference for all 120 questions) | "Let the scanner answer everything" | Only ~25-30% of QRAMM questions have direct technical evidence equivalents; governance/policy/supply-chain/executive-leadership questions require human judgment; full automation creates false confidence that harms clients in actual audits | Evidence bridge pre-populates only questions with direct scanner evidence; remaining questions require human review; confidence indicator marks auto-populated vs. human-answered responses |
| Per-finding remediation priority score based on QRAMM impact | "Show which finding to fix first to maximize QRAMM score improvement" | Requires solving an optimization problem across 120 questions × 24 finding categories × weakest-link dimension scoring; correctness is hard to guarantee and the math is opaque to auditors | Show which QRAMM practices have supporting scan evidence; leave priority ordering to the existing severity-ranked findings table |
| FedRAMP compliance mapping in COMPLIANCE_MAP | "Government clients need FedRAMP" | FedRAMP has hundreds of controls; crypto-relevant controls are already covered by NIST 800-53 which maps to FIPS 140-3 (already in map); adding FedRAMP as a named framework without full control coverage misleads auditors | Note NIST SP 800-53 control IDs in relevant finding entries; document that FedRAMP inherits these |

---

## QRAMM Framework Reference (Authoritative — verified against github.com/csnp/qramm)

**Structure:** 4 dimensions × 3 practices × 10 questions = 120 questions

| Dimension | Practice 1 | Practice 2 | Practice 3 | QUIRK Scanner Evidence Available |
|-----------|------------|------------|------------|----------------------------------|
| Cryptographic Visibility & Inventory (CVI) | Discovery & Inventory Management | Vulnerability Assessment & Classification | Cryptographic Dependency Mapping | HIGH — TLS/SSH/API/CBOM scans produce direct evidence for all 3 practices; evidence bridge can auto-populate ~25-30 of 30 CVI questions |
| Strategic Governance & Risk Management (SGRM) | Executive Leadership & Policy Management | Risk Assessment & Compliance Management | Third-Party & Supply Chain Risk Management | LOW — policy and governance questions require human answers; compliance mapping provides supporting context only |
| Data Protection Engineering (DPE) | Data Classification & Protection Requirements | Storage Security & Encryption Management | Transit Security & Protocol Management | MEDIUM — DAR scanner covers storage (Phase 27-30); Motion scanner covers transit (Phase 32-36); classification is a human decision |
| Implementation & Technical Readiness (ITR) | Infrastructure Assessment & Planning | Implementation Capability Development | Testing & Validation Capabilities | MEDIUM — nmap discovery output (Phase 47) shows infrastructure breadth; chaos lab existence is evidence of testing capability; migration planning is manual |

**Scoring Architecture (implement exactly — the weakest-link rule is non-obvious and critical):**
- Foundation stream = 60% weight + Advanced stream = 40% weight per practice
- Practice score = average of 10 questions within that practice
- Dimension score = minimum of the 3 practice scores (weakest-link principle — if one practice is Level 2, the dimension is Level 2 even if the other two are Level 4)
- Overall QRAMM score = average of 4 dimension scores
- Org profile multiplier (0.8–1.5×) applied to overall score; determined by: industry sector, org size, data sensitivity, regulatory obligations, technology complexity

**Maturity Levels:**
1. Basic (1.0–1.5): ad-hoc processes, no formal quantum program
2. Developing (1.6–2.5): emerging structure, basic awareness underway
3. Established (2.6–3.5): systematic and consistent practices, complete inventory
4. Advanced (3.6–3.9): measured processes, quantitative tracking, active migration
5. Optimizing (4.0): continuous improvement, full crypto-agility, automated systems

**Evidence Bridge Scope for v4.7:** Focus on CVI dimension only (~30 questions, high confidence auto-populate). SGRM, DPE, ITR extensions are v4.8+ scope after measuring evidence quality on CVI.

---

## Compliance Framework Coverage Analysis

### What v4.6 covers (existing — do not break or duplicate)

| Framework | Finding categories mapped | Notes |
|-----------|--------------------------|-------|
| PCI-DSS 4.0.1 | 24 finding categories (all current COMPLIANCE_MAP entries) | CC6.x requirements, cipher restrictions, cert validity |
| HIPAA 45 CFR | 24 finding categories | Addressable encryption safeguards |
| FIPS 140-3 | 24 finding categories | Algorithm approved/not-approved classification |

### What v4.7 adds (new framework entries in COMPLIANCE_MAP)

| Framework | Priority | Complexity | Key Controls to Map |
|-----------|----------|------------|---------------------|
| SOC2 Type II (AICPA TSC) | HIGH — most-requested by enterprise customers | LOW | CC6.1 logical access including encryption; CC6.6 transmission protection = TLS/cipher findings; CC6.7 data removal/transfer protection |
| ISO 27001:2022 Annex A | HIGH — global ISMS standard; EU/APAC required | LOW | A.10.1 cryptographic policy; A.10.2 key management; A.8.24 (2022 update) use of cryptography |
| CMMC 2.0 Level 2 (SC domain) | MEDIUM — DoD contractor market | MEDIUM | SC.3.177 FIPS-validated crypto (overlaps FIPS 140-3 already present); SC.3.187 key management; SC.3.185 transmission confidentiality |
| NIST CSF 2.0 (Protect function) | MEDIUM — non-regulated enterprise | MEDIUM | PR.DS-1 data at rest protection; PR.DS-2 data in transit protection; PR.AC-3 identity/access management (SSH, Kerberos) |

**Do not add in v4.7:** NSM 10, CNSA 2.0 (QRAMM's own table entries, but narrow US government audience not relevant to COMPLIANCE_MAP's finding-level mapping).

### SOC2 CC6 Mapping Details

| SOC2 Control | Scope | QUIRK Finding Categories |
|---|---|---|
| CC6.1 | Logical access controls implemented using encryption | SSH weak cipher, Kerberos RC4/DES, SAML weak signing |
| CC6.6 | Transmission of data encrypted with current cipher suites | Legacy TLS, weak cipher, plaintext HTTP, STARTTLS downgrade, Kafka/Redis/AMQP plaintext |
| CC6.7 | Data removal and transfer protection | TLS expired, self-signed, untrusted CA, undersized keys |

### ISO 27001:2022 A.10 Mapping Details

| ISO Control | Scope | QUIRK Finding Categories |
|---|---|---|
| A.10.1 (A.8.24 in 2022 rev) | Policy on use of cryptographic controls | Any finding — policy absence is inferred from technical failures |
| A.10.2 | Cryptographic key management lifecycle | RSA undersized/quantum-vulnerable, expired cert, self-signed |

---

## `quirk doctor` Health-Check Command Design

**Canonical pattern:** `flutter doctor`, `brew doctor`, `wp-cli doctor` — categorized checks with status symbols (pass / warn / error), human-readable messages, non-zero exit code on any error. Output is scannable, not verbose.

**Check categories (priority order):**

| Category | Specific Checks | Source |
|----------|-----------------|--------|
| Python environment | Python ≥ 3.11; `quirk[tls]`, `[ssh]`, `[motion]`, `[cloud]`, `[db]` extras installed vs. missing; `[identity]` available with advisory | Phase 45 `optional_extra` probe registry |
| Scanner binaries | `nmap` on PATH — required for Phase 47 multi-target discovery; `syft` — container scanning; `semgrep` — source scanning | `shutil.which()` + version check subprocess |
| Compliance data freshness | Inline call to `quirk compliance status` logic; flag any framework with `last_verified` > 365 days | Phase 49 staleness module |
| QRAMM data freshness | Flag if QRAMM version string `last_verified` > 90 days | New `qramm_version` metadata table |
| Database | SQLite file exists and readable; `scans` table has rows (or "no scans yet" informational); schema columns match expected set | SQLite `PRAGMA table_info()` |
| Configuration | `quirk.toml` / `.quirk.yaml` found and passes `validate.py`; no `[owner]` placeholder tokens remaining | Existing `validate.py` |
| Connectivity (optional) | TCP to `1.1.1.1:443` — informational; skip with `--offline` flag; never blocks exit code | Timeout-gated socket connect |
| Dashboard | HTTP GET to configured `localhost:PORT` — informational "not running" if unreachable | Requests or stdlib urllib |

**Output contract:**
```
quirk doctor
  [✓] Python 3.11.9 — OK
  [✓] quirk[all] extras installed
  [✗] nmap not found — nmap discovery disabled (install: brew install nmap / apt install nmap)
  [✓] Compliance data fresh — PCI-DSS: 2026-05-05, HIPAA: 2026-05-05, FIPS: 2026-05-05
  [!] QRAMM version metadata not found — run `quirk qramm status`
  [✓] Database: quirk.db found, 12 scans indexed
  [✓] Configuration: quirk.toml valid, no placeholder tokens
  [!] Dashboard not running — start with `quirk serve`

2 warnings, 1 error. Run with --verbose for details.
```

Exit code: 0 if all checks pass or warn; 1 if any check is error. Warn `[!]` does not block exit code.

---

## Feature Dependencies

```
SOC2 / ISO 27001 / CMMC / NIST CSF mapping
    └──extends──> COMPLIANCE_MAP (v4.6, existing)
                      └──pattern: add _soc2() / _iso27001() / _cmmc() / _csf() helpers
                      └──no schema changes required

CBOM FIPS 140-3 annotations (COMPLY-10)
    └──extends──> CBOM Pass 1 builder (v3.9, existing)
                      └──adds fips_approved flag to algorithm components
                      └──NIST PQC lookup table already has algorithm classification

QRAMM data model (SQLite)
    └──required by──> QRAMM assessment UI
    └──required by──> QRAMM scorecard
    └──required by──> QRAMM evidence bridge
    └──required by──> QRAMM staleness gate
    └──required by──> QRAMM combined PDF export
    └──CRITICAL PATH: all other QRAMM features are blocked until this lands

QRAMM assessment UI (120 questions, org profile wizard)
    └──requires──> QRAMM data model
    └──required by──> QRAMM evidence bridge (answers pre-populated into existing session)
    └──required by──> QRAMM scorecard (score computed from completed session)

QRAMM evidence bridge (CVI dimension, ~30 questions)
    └──requires──> QRAMM data model
    └──requires──> QRAMM assessment UI (session must exist to receive pre-populated answers)
    └──requires──> scanner evidence counters (run_scan.py evidence dict, existing)
    └──requires──> static mapping table: finding category → QRAMM practice + question index

QRAMM scorecard + radar chart
    └──requires──> QRAMM data model (completed session)
    └──uses──> Recharts (existing in dashboard bundle via Trends tab)

QRAMM compliance mapping view (8 frameworks)
    └──requires──> QRAMM scorecard
    └──uses──> COMPLIANCE_MAP for QUIRK's mapped frameworks
    └──uses──> static QRAMM-to-framework table for NSM 10 / CNSA 2.0 / FedRAMP (static, no live data)

QRAMM combined PDF export
    └──requires──> QRAMM scorecard (rendered component)
    └──requires──> existing PDF export pipeline (Playwright, Phase 11)
    └──appends QRAMM section to existing HTML/PDF report structure

quirk doctor
    └──requires──> optional_extra probe registry (Phase 45, existing)
    └──uses──> compliance staleness logic (Phase 49, existing)
    └──uses──> QRAMM staleness metadata (new, but thin)
    └──independent of QRAMM UI and QRAMM evidence bridge

QRAMM staleness gate (90-day CI + quirk qramm status CLI)
    └──same pattern as──> compliance staleness gate (Phase 49 D-04)
    └──independent of QRAMM assessment UI
    └──can land in same phase as QRAMM data model
```

### Critical Dependency Notes

- **QRAMM data model is the critical-path gate.** Phase it first among QRAMM features. Everything else is unblocked once the tables exist and the CRUD endpoints are live.
- **SOC2/ISO27001/CMMC/NIST CSF mapping is completely independent of QRAMM.** It uses the same `COMPLIANCE_MAP` infrastructure as v4.6. It can be its own phase and does not block or depend on any QRAMM work.
- **CBOM FIPS 140-3 annotations are independent.** Touch only the CBOM builder and lookup table. No UI, no schema changes, no API changes.
- **`quirk doctor` is independent of QRAMM UI.** It needs only the QRAMM staleness metadata (which lands with the data model) plus existing Phase 45 probe registry. Can be phased any time after the data model.
- **QRAMM evidence bridge is the highest-complexity item and should be its own phase.** It requires the assessment UI to be proven correct before pre-population is layered on top; avoid combining with UI build phase.
- **QRAMM PDF export requires a complete scorecard.** Playwright pipeline is already proven; the new work is adding a QRAMM score section to the existing report template.
- **Weakest-link dimension scoring must be implemented exactly as specified.** Getting this wrong produces scores that disagree with what a client computes from the CSNP Excel toolkit — immediate credibility loss. Unit-test the weakest-link rule explicitly.

---

## MVP Definition

### Launch With (v4.7 milestone)

All of the following are P1 for this milestone based on PROJECT.md target feature list:

- [ ] SOC2 CC6.x + ISO 27001 A.10 added to `COMPLIANCE_MAP` (COMPLY-11) — highest enterprise demand, lowest cost, uses existing infrastructure
- [ ] CBOM FIPS 140-3 algorithm annotations (COMPLY-10) — completes open backlog item; CBOM builder touch only
- [ ] `quirk doctor` health-check CLI (DOCS-05) — high consultant UX value; low risk; independent
- [ ] QRAMM data model (SQLite tables + FastAPI CRUD) — critical path gate; must be first QRAMM phase
- [ ] QRAMM 120-question assessment UI with org profile wizard — table stakes for QRAMM integration
- [ ] QRAMM scorecard + radar chart — the assessment has no deliverable without this
- [ ] QRAMM evidence bridge (CVI dimension auto-populate, ~30 questions) — key differentiator; scoped to CVI only in v4.7
- [ ] QRAMM compliance mapping view (8 frameworks, static table) — closes consulting deliverable
- [ ] QRAMM combined PDF export — single-file consulting deliverable; Playwright already proven
- [ ] QRAMM staleness enforcement — 90-day CI gate + `quirk qramm status` CLI

### Add After Validation (v4.8)

- [ ] CMMC 2.0 Level 2 control mapping — specialized market (DoD contractors); add when first client engagement requires it
- [ ] NIST CSF 2.0 control mapping — broader audience than CMMC but lower priority than SOC2/ISO27001; add after v4.7 compliance tab is validated
- [ ] QRAMM evidence bridge full coverage (SGRM, DPE, ITR dimensions) — v4.7 scopes to CVI; extend after measuring evidence quality against real client sessions
- [ ] Quick QRAMM assessment (12-question variant) — low-friction entry point; add after full 120-question flow is stable

### Future Consideration (v5+ / SaaS milestone)

- [ ] Custom compliance frameworks via config file — needed for consulting firms with proprietary frameworks
- [ ] QRAMM multi-tenant / SaaS mode — explicit future milestone; do not design for it in v4.7
- [ ] Continuous QRAMM re-scoring triggered by new scan data — requires SaaS job queue architecture

---

## Feature Prioritization Matrix

| Feature | Consultant Value | Implementation Cost | Priority |
|---------|-----------------|---------------------|----------|
| SOC2 CC6.x + ISO 27001 A.10 compliance mapping | HIGH | LOW | P1 |
| CBOM FIPS 140-3 algorithm annotations | HIGH | MEDIUM | P1 |
| `quirk doctor` health-check CLI | HIGH | MEDIUM | P1 |
| QRAMM data model (SQLite + FastAPI CRUD) | HIGH | MEDIUM | P1 — gate |
| QRAMM 120-question assessment UI + org profile wizard | HIGH | HIGH | P1 |
| QRAMM scorecard + radar chart | HIGH | MEDIUM | P1 |
| QRAMM evidence bridge (CVI scope) | HIGH | HIGH | P1 |
| QRAMM compliance mapping view (8 frameworks) | MEDIUM | MEDIUM | P1 |
| QRAMM combined PDF export | HIGH | MEDIUM | P1 |
| QRAMM staleness gate + `quirk qramm status` CLI | HIGH | LOW | P1 |
| CMMC 2.0 SC domain mapping | MEDIUM | MEDIUM | P2 |
| NIST CSF 2.0 Protect function mapping | MEDIUM | MEDIUM | P2 |
| Quick QRAMM (12-question) | MEDIUM | LOW | P2 |
| QRAMM evidence bridge full coverage (all 4 dimensions) | MEDIUM | HIGH | P2 |

---

## Competitor Feature Analysis

No direct open-source competitor implements QRAMM + live scanner evidence bridge in a single pip-installable tool.

| Feature | CSNP QRAMM Excel Toolkit | Enterprise GRC (RapidFire, RegScale) | QUIRK v4.7 Plan |
|---------|--------------------------|--------------------------------------|-----------------|
| QRAMM assessment | Manual Excel, 120 questions | Not applicable | Native web UI, save/resume, section navigation |
| Evidence from scans | Manual only; no scanner integration | Tenable/Qualys via API connector | Auto-populate from QUIRK scan evidence counters |
| PDF export | Excel-generated report | Platform-generated | Combined QRAMM + technical findings PDF (Playwright) |
| Offline capable | Yes (Excel) | No (SaaS) | Yes (local SQLite + Playwright) |
| License cost | Free (open source) | Enterprise SaaS pricing | Consulting deliverable, open-source core |
| Compliance frameworks | 8 frameworks (static table in toolkit) | Multiple via GRC platform license | 5 in COMPLIANCE_MAP (v4.7) + QRAMM's 8 (static display) |
| Staleness enforcement | None | Platform-managed (opaque) | 90-day QRAMM gate + 365-day compliance gate, CI-enforced with source URLs |
| CBOM output | None | None | CycloneDX 1.6 JSON+XML with FIPS 140-3 algorithm annotations |

---

## Sources

- [QRAMM GitHub — framework overview, 4 dimensions, 12 practices, 5 levels, weakest-link scoring, dual-stream weighting](https://github.com/csnp/qramm/blob/main/framework/qramm-overview.md)
- [QRAMM Toolkit Overview — org profile multiplier (0.8–1.5×), 8 compliance frameworks, dual-stream (Foundation 60% / Advanced 40%) scoring](https://qramm.org/toolkit-overview.html)
- [QRAMM Quantum Readiness Assessment — 7-step process, spider chart canonical output](https://qramm.org/learn/quantum-readiness-assessment.html)
- [SOC2 CC6 encryption controls — CC6.1 logical access, CC6.6 transmission protection, CC6.7 data removal](https://securityboulevard.com/2022/06/soc-2-controls-encryption-of-data-at-rest/)
- [SOC2 CC6.6 — TLS and AES transmission encryption as control evidence](https://www.isms.online/soc-2/controls/logical-and-physical-access-controls-cc6-6-explained/)
- [ISO 27001 Annex A.10 Cryptography — A.10.1 policy, A.10.2 key management lifecycle](https://www.dataguard.com/blog/iso-27001-annex-a.10-cryptography)
- [ISO 27001:2022 A.8.24 — updated cryptography control (2022 revision)](https://www.sorinmustaca.com/understanding-iso-27001-2022-annex-a-10-cryptography/)
- [CMMC Level 2 SC domain — SC.3.177 FIPS-validated crypto, SC.3.187 key management lifecycle](https://ndisac.org/dibscc/cyberassist/cybersecurity-maturity-model-certification/level-2/sc-l2-3-13-10/)
- [CMMC Level 2 encryption — SC.3.177 CMVP validation requirement, evidence package](https://theodosian.com/blog/cmmc-level-2-encryption-requirements-a-plain-language-guide-for-defense-contractors)
- [ISO 27001 and SOC2/NIST CSF/CMMC cross-framework mapping overview](https://www.ampcuscyber.com/blogs/iso-27001-mapping-with-security-standards/)
- [GRC auto-populate pattern — API-based evidence from Tenable/Qualys into controls mapping](https://cybersierra.co/blog/enterprise-cybersecurity-scanning-tools/)
- [GRC continuous monitoring and evidence collection mechanics](https://fedresources.com/how-continuous-monitoring-and-validation-actually-work-in-governance-risk-and-compliance-grc-tools/)
- [Wizard UX patterns — save/resume, section navigation, draft state, NN/g recommendations](https://www.nngroup.com/articles/wizards/)
- [Flutter doctor — canonical CLI health-check output format (per-category, status symbol, human message)](https://www.codecademy.com/article/check-your-flutter-installation-with-flutter-doctor)
- [WP-CLI doctor — status/warning/error three-state pattern, customizable checks via YAML](https://github.com/wp-cli/doctor-command)

---

*Feature research for: QU.I.R.K. v4.7 Governance & Compliance Platform milestone*
*Researched: 2026-05-05*
