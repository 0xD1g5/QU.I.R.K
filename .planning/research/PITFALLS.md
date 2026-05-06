# Pitfalls Research

**Domain:** Adding a governance maturity model (QRAMM) + SOC2/ISO27001 compliance mapping to an existing Python cryptographic scanner (QU.I.R.K. v4.7)
**Researched:** 2026-05-05
**Confidence:** HIGH (code-verified against existing codebase patterns); MEDIUM (QRAMM model specifics, SOC2/ISO27001 mapping accuracy)

---

## Critical Pitfalls

### Pitfall 1: Evidence Bridge Over-Claiming — Scanner Findings Do Not Prove Governance Maturity

**What goes wrong:**
The evidence bridge auto-populates QRAMM question answers from live scanner findings (e.g., "TLS 1.3 found on 12 endpoints" auto-answers the "Are strong TLS versions enforced?" question as Level 3). This feels like a power feature but becomes a liability when the auto-populated answer claims a maturity level the organization has not actually earned. Scanning what is deployed is not the same as governance of what is deployed. An org can have TLS 1.3 everywhere by accident (vendor default) and score Level 3 on "Cryptographic Visibility" despite having zero inventory management process, no policy, and no repeatable procedure. If the QRAMM report is used in an audit, the inflated score becomes a misrepresentation.

**Why it happens:**
Developers map scanner outputs (HIGH confidence, measurable) directly to QRAMM maturity levels (which require governance evidence: policies, process repeatability, documented ownership). The two evidence types are categorically different. Technical presence is necessary but not sufficient for any QRAMM level above Level 1.

**How to avoid:**
Treat the evidence bridge as a read-only hint layer, not an answer layer. Auto-populated answers must use a distinct `evidence_source: "scanner_auto"` flag and must render with a visual "unconfirmed" state in the UI — a different color or an explicit "Verify this claim" prompt before the answer is locked. Require a human confirmation click before any auto-populated answer contributes to the final score. Define and document the exact mapping: scanner finding X populates QRAMM question Y as a suggested answer at maturity level Z, not as a confirmed answer. In the scoring engine, apply a `confidence_discount` (e.g., 0.8x) to any dimension where more than 50% of answers are scanner-sourced without human confirmation.

**Warning signs:**
- QRAMM report generates a Level 3 or higher maturity score on the first run against an org with no prior governance work
- Evidence bridge sets `answer_value` directly rather than `suggested_answer` + `requires_confirmation: true`
- The compliance report cites scanner-derived answers without disclosure that they are automated

**Phase to address:**
QRAMM Evidence Bridge phase — design the data model with `evidence_source`, `confirmed_by`, `confirmed_at` fields before writing any bridge logic. The UI must not allow an unconfirmed auto-answer to be included in the final export.

---

### Pitfall 2: QRAMM Scoring Model Drift — Hardcoded Profile Multiplier and Level Thresholds

**What goes wrong:**
The QRAMM model uses a profile multiplier (0.8–1.5x) and five-level thresholds (1.0–1.5, 1.6–2.5, 2.6–3.5, 3.6–3.9, 4.0). These values are sourced from the QRAMM toolkit, which is an externally maintained framework. If QUIRK hardcodes the multiplier range and thresholds as Python literals, any revision to the QRAMM framework (e.g., added dimensions, reweighted practice areas, updated level boundaries) requires a QUIRK code change. More critically, QUIRK reports generated before and after a QRAMM version change will produce different scores for identical answers — causing client confusion if they compare reports year-over-year and cannot explain the delta.

**Why it happens:**
The first implementation of a scoring model always hardcodes constants. It is the path of least resistance. The QRAMM toolkit is an Excel tool — its version is not machine-readable by default, and there is no API to detect framework updates. So developers copy the constants once and never revisit them.

**How to avoid:**
Store all QRAMM model constants (level thresholds, multiplier range, dimension weights, question-to-practice-area mapping, 120-question text) in a versioned data structure: `QRAMM_MODEL_VERSION = "1.0"` and a `QRAMM_MODEL: dict` constant with a `version`, `source_url`, and `last_verified` key — exactly the same pattern used in `quirk/compliance/__init__.py` for the existing compliance map. Every assessment record in SQLite must store the `qramm_model_version` at the time of assessment. The `quirk qramm status` CLI and the staleness CI gate must check that `last_verified` is within 365 days. When QRAMM updates its framework, updating QUIRK requires changing one data module, not hunting string literals across the codebase.

**Warning signs:**
- Level thresholds and multiplier ranges are Python literals inside the scoring function, not a named constant with a version key
- SQLite `qramm_assessment` table has no `model_version` column
- Two assessments from different QUIRK versions produce different scores for identical answers with no recorded explanation

**Phase to address:**
QRAMM Data Model phase — the `QRAMM_MODEL` versioned constant must exist before any scoring function is written.

---

### Pitfall 3: 120-Question Wizard State Loss on Navigation — React Unmount Anti-Pattern

**What goes wrong:**
A naive implementation of the 120-question assessment wizard splits questions across steps and uses component-per-step routing (e.g., `/qramm/step/1`, `/qramm/step/2`). React router navigation between steps unmounts the current step component, destroying its local state. If the wizard uses `useState` per-step for answers, the user loses all work when they press the browser Back button, refresh the page, or if a tab is put to sleep by the browser. A 120-question wizard where a wrong navigation gesture silently discards 40 minutes of work is a consultant-rage-inducing UX failure.

**Why it happens:**
Multi-step forms are routinely implemented as page-per-step because it maps naturally to router semantics. This works acceptably for 3–5 step forms where each step takes seconds. It fails for 120-question assessments where a single dimension (30 questions) takes 5–10 minutes and any unmount drops answers that are not yet persisted.

**How to avoid:**
Keep all 120 answers in a single React context (or Zustand store) that lives at the top-level layout component, above all route changes. Answer state must never be owned by a step-level component. Persist the entire in-progress assessment to the backend (draft save via `POST /api/qramm/assessment/draft`) every time any answer changes, with debouncing (500ms). On wizard mount, load the draft from the backend if one exists. This makes browser refresh recovery automatic. Never use `useNavigate` to advance steps — use tab-index state within a single mounted component so nothing unmounts between steps. Treat the 120 questions as a single long form with a scrollable/paginated display, not as multiple pages.

**Warning signs:**
- `useEffect(() => { setAnswers([]) }, [])` appears at step-component level
- Each wizard step is a separate React route (`/qramm/step/:n`)
- No draft-save endpoint exists in the FastAPI backend
- Browser Back button during assessment produces an empty answers array

**Phase to address:**
QRAMM Assessment UI phase — state architecture must be decided before any step component is written. The draft-save endpoint must exist before the wizard is wired.

---

### Pitfall 4: SQLite Schema for Assessment State — JSON Blob Anti-Pattern

**What goes wrong:**
Storing the 120 QRAMM question answers as a single `answers_json` TEXT blob on an `assessment` row feels natural (it mirrors the existing `tls_capabilities_json`, `ssh_audit_json` patterns in `quirk/models.py`). However, those existing JSON blobs are raw scanner outputs that are never queried by field — they are opaque payloads for the UI. QRAMM answers are different: the scoring engine needs to aggregate by dimension, filter by practice area, compute per-question confidence weights, and detect which answers are scanner-confirmed vs. human-confirmed. Running `json_extract()` across 120 keys on every scoring call is fragile and slow. More critically, the JSON blob approach makes it impossible to write a unit test that asserts "dimension CVI has 30 answered questions" without deserializing the blob.

**Why it happens:**
The existing `*_scan_json` pattern in `models.py` works well for raw scan outputs and developers correctly recognize the additive migration constraint. They reach for the same pattern for assessment state because it avoids schema design work.

**How to avoid:**
Use a normalized `qramm_answer` table: `(id, assessment_id FK, question_id, dimension, practice_area, answer_value INT, evidence_source TEXT, suggested_by TEXT, confirmed_at DATETIME, model_version TEXT)`. This is a separate table from `qramm_assessment` (which holds the header: org profile, created_at, overall score, model version). The `assessment_id` FK makes all answers for one assessment queryable with a simple `WHERE assessment_id = ?`. Scoring queries become `SELECT AVG(answer_value) FROM qramm_answer WHERE assessment_id = ? AND dimension = 'CVI'` — no JSON deserialization. Keep a `summary_json` column on `qramm_assessment` only for the pre-computed score breakdown (not the raw answers), to avoid recomputing on every dashboard load. The additive migration constraint is satisfied: both new tables are created via `CREATE TABLE IF NOT EXISTS`, never altering existing tables.

**Warning signs:**
- `qramm_assessment` has an `answers_json` TEXT column instead of a `qramm_answer` child table
- Scoring function deserializes a JSON blob and iterates over it to compute dimension averages
- No SQLAlchemy `relationship()` from `QRAMMAssessment` to `QRAMMAnswer`

**Phase to address:**
QRAMM Data Model phase — normalize the schema before writing any API routes or scoring logic.

---

### Pitfall 5: PDF Export Regression — QRAMM Section Breaking Existing Print Layout

**What goes wrong:**
The current `POST /api/export/pdf` route navigates Playwright to `/print`, waits for `body[data-ready="true"]`, then renders A4 with fixed margins. Adding a QRAMM governance section to the print route (radar chart, 8-framework compliance table, dimension breakdowns) will change page count, affect page breaks in the existing Technical Findings section, and potentially push the Executive Summary off page 1. Playwright PDF output changes when content reflows. The Chromium version pinned in the development environment may differ from CI, producing different page counts. Radar charts rendered via a canvas or SVG element may not print at all if the element is not in the visible DOM or if it relies on JavaScript animations that have not settled when Playwright captures the page.

**Why it happens:**
PDF print layout is treated as a visual concern that "just works." Developers add new sections to the print route without print-specific CSS, without testing page breaks, and without verifying that chart elements are print-visible. The 30-second Playwright timeout and 15-second selector wait are generous for the existing lean report but may be insufficient if the QRAMM section triggers additional async data fetches.

**How to avoid:**
Add `@media print` CSS rules for every new QRAMM section before the section ships. Explicitly set `page-break-before: always` on the QRAMM section to guarantee it starts on a fresh page rather than inheriting broken pagination from the technical section. Set `break-inside: avoid` on each sub-table and chart container. Render the radar chart as a static SVG (no animation) — never as a `<canvas>` element, which does not print reliably. Add a snapshot test: render the print route headlessly and assert the PDF page count is within an expected range (e.g., 4–12 pages). Pin the Playwright/Chromium version in `pyproject.toml` to the same version used in CI. Do not add any new async data fetches inside the print route's React component — the component must receive all data synchronously from props/context at mount time, not fetch it after mount.

**Warning signs:**
- The `/print` React component calls `useEffect(() => { fetch(...) })` at component mount for QRAMM data
- QRAMM radar chart is implemented as `<canvas>` rather than inline SVG
- No `@media print` CSS for the QRAMM section
- PDF page count is not asserted in any test

**Phase to address:**
QRAMM Report Export phase — print CSS must be written alongside the QRAMM section components, not added later as a fix.

---

### Pitfall 6: Staleness Gate False Positives — Date-Based CI Failures Blocking Legitimate Deployments

**What goes wrong:**
The existing Phase 49 staleness infrastructure uses `STALENESS_THRESHOLD_DAYS = 365` and compares `last_verified` against the current date. The v4.7 QRAMM staleness gate extends this to QRAMM model constants (90-day threshold per the milestone spec) and SOC2/ISO27001 control mappings. The false-positive risk arises when: (1) CI runs in a timezone where the date rolls over at a different moment than the developer's local machine; (2) a patch release is cut exactly at the 90-day boundary and the CI run on that day fails; (3) the staleness check reads `datetime.utcnow()` (deprecated) instead of `datetime.now(timezone.utc)`, producing a 0-day-old reading in some Python versions; (4) a `last_verified` date is bumped during a cosmetic edit (comment change) without actual re-verification, creating false freshness and defeating the gate.

**Why it happens:**
Staleness checks feel straightforward but have three independent failure modes: clock source (utcnow vs. timezone-aware now), boundary edge cases (exactly N days), and social pressure to bump the date to silence CI rather than do the verification.

**How to avoid:**
Use `datetime.now(timezone.utc).date()` everywhere — never `datetime.utcnow()`. The BACK-56 tech debt item (datetime.utcnow deprecation) must be resolved in the same milestone before any new staleness gates are added. Use `<` (strictly less than) not `<=` for the boundary: a last_verified date that is exactly `threshold_days` old is not yet stale. Add a CI environment variable `QUIRK_CI_STALENESS_OVERRIDE_DATE` that allows the test suite to inject a fixed "today" date — this enables tests to verify staleness behavior at known boundaries without coupling the test to wall-clock time. Distinguish "not yet verified" (null last_verified) from "verified but stale" — they require different CI failure messages and different remediation actions. Document in CONTRIBUTING.md that bumping `last_verified` requires a link to the verification artifact (PR, external changelog, or issue) in the commit message.

**Warning signs:**
- Staleness check uses `datetime.utcnow()` — BACK-56 not yet resolved
- CI fails on the 90th day after a release and the fix is to bump `last_verified` without re-verification
- `QUIRK_CI_STALENESS_OVERRIDE_DATE` does not exist as an env var hook in the staleness module
- `last_verified` is updated in the same commit as a docstring fix with no re-verification evidence

**Phase to address:**
QRAMM Data Model / staleness enforcement phase — resolve BACK-56 first. Write the staleness module with the injectable-date pattern before adding any QRAMM thresholds.

---

### Pitfall 7: SOC2 and ISO27001 Mapping Accuracy — Framework Versioning and Partial Coverage Misrepresentation

**What goes wrong:**
SOC2 Trust Service Criteria (TSC) reference AICPA 2017 (updated 2022). ISO 27001:2022 reorganized from 114 controls across 14 domains (ISO 27001:2013) to 93 controls across 4 clauses. Mappings written against ISO 27001:2013 control IDs (e.g., "A.10.1.1") are invalid in ISO 27001:2022 (which uses "8.24"). If QUIRK maps TLS findings to ISO 27001 controls using 2013 numbering without declaring the version, a client undergoing a 2022 audit will find the control references do not match their framework. SOC2 is an even larger trap: the TSC are principles (CC6.1, CC6.7), not numbered controls, and their applicability depends on which Trust Service Categories the organization has selected. Mapping a TLS finding to CC6.7 (availability-adjacent) when the org has not selected Availability TSC produces a report that looks authoritative but is scoped incorrectly.

**How to avoid:**
Version-pin every mapping entry with `"version": "ISO 27001:2022"` or `"version": "SOC 2 TSC 2017 (2022 points of focus)"` — never just `"ISO 27001"`. Use the new ISO 27001:2022 clause numbers (8.x) not the 2013 Annex A numbers (A.x.x). For SOC2, map only to Common Criteria (CC) controls — not to Availability, Confidentiality, or Processing Integrity controls unless the org profile in the QRAMM assessment explicitly indicates those TSCs apply. Add an org-profile input during the QRAMM org wizard: "Which Trust Service Categories does your SOC2 audit cover?" and gate the SOC2 control display on the answer. Add a prominent disclaimer in the PDF export: "SOC2 control mapping reflects Common Criteria applicable to all audits; additional TSC controls may apply based on your audit scope." Never display a "100% coverage" badge for any framework — QUIRK scans the network/crypto surface, not the full control environment, and claiming full coverage is a material misrepresentation.

**Warning signs:**
- Any SOC2 control reference uses clause numbers rather than CC/A/C/I/P/PI prefix notation
- Any ISO 27001 control reference uses `A.x.x` notation (2013 numbering) without a version declaration
- QUIRK displays a coverage percentage above ~30% for any framework — a cryptographic scanner cannot cover human-process controls
- The QRAMM compliance mapping view shows all 8 frameworks with equal confidence regardless of org TSC selection

**Phase to address:**
COMPLY-11 SOC2/ISO27001 mapping phase — the control reference data structure must enforce version as a required field (not nullable). A unit test must assert that no entry uses 2013-era `A.x.x` control IDs without a version override.

---

### Pitfall 8: CBOM FIPS 140-3 Annotations — certificationLevel Inferred vs. Verified

**What goes wrong:**
CycloneDX 1.6 (QUIRK's current output format) supports `certificationLevel` on algorithm components. The tempting implementation annotates any algorithm that is FIPS-approved (ML-KEM, AES-256, SHA-2) with `certificationLevel: "FIPS 140-3"`. This is factually wrong: FIPS 140-3 certifies the *implementation* (a specific hardware or software module validated by a CMVP lab), not the algorithm. AES-256 implemented in OpenSSL 3.x is not FIPS 140-3 certified unless OpenSSL's FIPS provider module was specifically validated and the application was configured to use it. Annotating an endpoint's TLS AES-256 cipher as FIPS 140-3 certified when the server runs unvalidated OpenSSL will be challenged immediately in any FISMA or FedRAMP audit.

**How to avoid:**
Use `certificationLevel` only when scanner evidence explicitly indicates a validated module (e.g., a CloudHSM KMS key, a FIPS-mode AWS service, a Vault transit key configured with a FIPS-validated backend). For all other algorithm components, omit `certificationLevel` or set it to `"none"`. Annotate algorithm components with a `quantum_safety` property (already implemented in QUIRK's CBOM classifier) but not with a certification claim that cannot be verified by a network scanner. Add a disclaimer to the CBOM export: "certificationLevel annotations are present only where scanner evidence indicates a validated cryptographic module. Network-observable algorithm usage does not imply FIPS 140-3 module validation." The COMPLY-10 requirement is CBOM FIPS 140-3 *annotations* — interpret this as "annotate findings that are relevant to FIPS 140-3 compliance evaluation" not "claim FIPS certification on all matching algorithms."

**Warning signs:**
- Every AES or SHA component in the CBOM has `certificationLevel: "FIPS 140-3"` regardless of whether the endpoint is a cloud HSM or a local Apache server
- No test asserts that a non-validated endpoint produces `certificationLevel: "none"` or absent field
- CBOM export does not include a disclaimer about the distinction between algorithm approval and module validation

**Phase to address:**
COMPLY-10 CBOM FIPS annotation phase — define the exact evidence criteria that justifies each certification level claim before writing any annotation logic.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store all 120 QRAMM answers as a `answers_json` blob | Fast schema, mirrors existing scan JSON pattern | Cannot query per-dimension; scoring function is a deserialize-iterate loop; untestable at unit level | Never — normalize to `qramm_answer` table |
| Auto-confirm scanner evidence as QRAMM answers | Demo looks impressive; answers fill automatically | Audit misrepresentation risk; inflated maturity scores | Never — require human confirmation click |
| Hardcode QRAMM level thresholds and multipliers as literals | Fast to ship | Breaks year-over-year comparability when QRAMM framework updates | Never — use a versioned `QRAMM_MODEL` constant |
| Map all FIPS-approved algorithms to `certificationLevel: "FIPS 140-3"` | CBOM looks comprehensive | Any auditor will challenge unverified certification claims | Never — only annotate with evidence |
| ISO 27001 control IDs without version declaration | Looks complete | 2013 vs 2022 numbering mismatch in client audit | Never — version key is required |
| Add new PDF section without print-specific CSS | Quick to ship | Page break regressions break existing report layout | Never for a document delivered to paying clients |
| Bump `last_verified` to silence CI without re-verification | Passes CI | Defeats the staleness gate entirely; creates false assurance | Never — document verification artifact in commit |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| QRAMM evidence bridge | Setting `answer_value` directly from scanner output | Set `suggested_answer` + `evidence_source: "scanner_auto"` + `requires_confirmation: true`; human click locks the answer |
| Playwright PDF export + new sections | Adding async fetches inside `/print` component | All QRAMM data must be in React context at mount time; no fetch-on-render in print route |
| SOC2 TSC mapping | Mapping findings to all 5 TSC categories | Map only to Common Criteria (CC) by default; gate additional TSC on org profile input |
| ISO 27001 control IDs | Using 2013 Annex A numbering (A.10.1.1) | Use 2022 clause numbering (8.24); version-pin every entry |
| SQLite additive migration for QRAMM tables | `ALTER TABLE` existing tables to add columns | `CREATE TABLE IF NOT EXISTS qramm_assessment` and `qramm_answer` — never alter `crypto_endpoint` |
| Staleness gate datetime | `datetime.utcnow()` | `datetime.now(timezone.utc).date()` — BACK-56 must be resolved first |
| QRAMM wizard step navigation | Route-per-step causing unmount | Single mounted component with tab-index state; answers in top-level context |
| CBOM certificationLevel | Annotating all FIPS-approved algorithms | Annotate only endpoints with validated module evidence (HSM, FIPS-mode cloud service) |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Scoring 120 QRAMM answers by deserializing JSON blob on every API call | `/api/qramm/assessment/:id/score` takes > 500ms | Pre-compute score breakdown into `summary_json` column on save; only recompute on answer change | Any org with > 5 assessments loaded in the dashboard simultaneously |
| Radar chart rendered as `<canvas>` in print route | Chart is blank in PDF export | Use static inline SVG; no animations, no JavaScript canvas | Every PDF export when canvas is used |
| Loading all 120 questions from DB on every wizard page render | Wizard feels slow to navigate between dimensions | Load all 120 questions once at wizard mount; keep in memory for session | Any connection latency > 100ms |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Displaying QRAMM maturity score without org-profile context | A Level 2 org in financial services is worse than a Level 2 startup — raw score without profile is misleading | Always display score alongside profile multiplier and org sector in reports |
| Evidence bridge populating answers from scanner data without audit trail | Auditor cannot verify how a QRAMM answer was derived | Every answer row must store `evidence_source`, `evidence_ref` (scan session ID), `confirmed_by`, `confirmed_at` |
| SOC2 control mapping claiming "passed" for any control | Scanner cannot verify human-process controls (policies, training, vendor reviews) | Display only "relevant" or "technical evidence present" — never "compliant" or "passed" |
| Storing assessment answers with no `assessment_id` FK | Multiple incomplete assessments accumulate as orphaned rows | Enforce FK integrity at the ORM layer; auto-delete orphaned draft answers after 30 days |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| 120 questions displayed as a single scrolling list | Consultant loses track of position; no sense of progress | Group by dimension (4 groups of 30); show dimension progress bar; allow saving and resuming per-dimension |
| Auto-populated answers indistinguishable from human answers | Consultant exports a report thinking all answers are confirmed; client catches inflated score in audit | Use distinct visual state for `evidence_source: "scanner_auto"` answers (amber badge, "Verify" button) |
| Radar chart showing Level 5 spikes | Client incorrectly believes they are fully quantum-ready in that dimension | Cap visual display at the raw score; add explanatory text for any dimension above Level 3 |
| PDF export including all 120 question answers | 30-page appendix that no client reads | Export dimension summaries + findings by default; offer raw Q&A as an optional appendix with explicit checkbox |
| `quirk doctor` health-check output mixing QRAMM model freshness with scanner dep checks | Consultant cannot triage which issue to fix first | Group output: (1) Scanner dependencies, (2) Compliance map freshness, (3) QRAMM model freshness — separate sections with separate exit codes |

---

## "Looks Done But Isn't" Checklist

- [ ] **QRAMM evidence bridge:** Every auto-populated answer has `evidence_source: "scanner_auto"` and `requires_confirmation: true`. A human confirmation click is required before the answer contributes to the scored total. Verify by checking a fresh assessment with no human inputs — the score should be 0 or explicitly marked as "unconfirmed."
- [ ] **QRAMM model versioning:** Every scoring function reads thresholds and weights from `QRAMM_MODEL` constant, not literals. `QRAMM_MODEL` has a `version` and `last_verified` key. `qramm_assessment` table has a `model_version` column populated at assessment creation time.
- [ ] **Wizard state persistence:** Browser refresh during question 60 of 120 restores the in-progress answers from the backend draft. Verify: answer Q1–Q30, refresh, Q1–Q30 answers are present.
- [ ] **SQLite schema normalization:** `qramm_answer` is a separate table, not a JSON column on `qramm_assessment`. Verify by running `SELECT sql FROM sqlite_master WHERE name='qramm_answer'` — must return a CREATE TABLE statement with individual columns.
- [ ] **PDF print layout:** Adding QRAMM section does not push Executive Summary off page 1. Verify by generating a PDF from a fully populated assessment and checking that page 1 is still the exec summary.
- [ ] **Staleness gate injectable date:** `QUIRK_CI_STALENESS_OVERRIDE_DATE` env var is respected by the staleness check. Verify by setting it to a date 91 days after a `last_verified` date and asserting the gate fails.
- [ ] **SOC2 control version:** Every SOC2 mapping entry uses `CC` prefix notation (Common Criteria), not numeric controls. Every ISO 27001 entry uses 2022 clause numbering and has a `version: "ISO 27001:2022"` key. Verify with a unit test.
- [ ] **CBOM certificationLevel discipline:** Generating a CBOM from a standard TLS endpoint produces no `certificationLevel` annotation or explicitly `"none"`. Only a Cloud HSM or FIPS-mode service produces a non-null annotation. Verify with the chaos lab.
- [ ] **BACK-56 resolved before staleness gates:** `git grep "utcnow"` in `quirk/` returns 0 results before any QRAMM staleness module is merged.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Evidence bridge ships without confirmation gate | HIGH — assessments already exported with inflated scores | Add confirmation gate in patch; mark all existing auto-populated answers `requires_reconfirmation: true`; notify users to re-verify; do not silently recalculate old scores |
| QRAMM model constants hardcoded — framework updates | MEDIUM | Extract to `QRAMM_MODEL` constant in a patch; all new assessments use new version; old assessments retain their `model_version` reference |
| SOC2/ISO27001 wrong-version control IDs shipped to clients | HIGH — auditor challenge in a live engagement | Issue corrected report immediately; add version correction to patch release; cite version in CHANGELOG |
| PDF regression breaks exec summary pagination | LOW — visual only | Fix `@media print` CSS; re-export from the same scan data |
| Staleness gate blocking CI release without re-verification | LOW | Use `QUIRK_CI_STALENESS_OVERRIDE_DATE` to verify the test is correct; then actually perform re-verification; do not bypass the gate by bumping the date |
| `answers_json` blob schema shipped — needs normalization | HIGH — requires data migration | Write a one-time migration script to deserialize existing blobs into `qramm_answer` rows; test migration on a copy before running on production DB |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Evidence bridge over-claiming | QRAMM Evidence Bridge phase | Unit test: fresh assessment with all scanner evidence returns `overall_confirmed_score = 0` until human confirmation |
| QRAMM model version drift | QRAMM Data Model phase | `QRAMM_MODEL` constant exists with `version` key; scoring function has no numeric literals for thresholds |
| Wizard state loss on navigation | QRAMM Assessment UI phase | Integration test: answer 30 questions, force route change, confirm answers reload from draft |
| JSON blob schema for answers | QRAMM Data Model phase | `sqlite_master` query: `qramm_answer` is a real table, not a column on `qramm_assessment` |
| PDF layout regression | QRAMM Report Export phase | PDF snapshot test: page 1 is exec summary; QRAMM section starts on its own page |
| Staleness gate false positives | QRAMM staleness enforcement phase | CI runs with injected date at exactly 90 days — must NOT fail; at 91 days — must fail |
| SOC2 wrong-version control IDs | COMPLY-11 phase | Unit test: all SOC2 entries use `CC` prefix; all ISO 27001 entries use `8.x` clause numbers |
| CBOM certificationLevel over-annotation | COMPLY-10 phase | Chaos lab: standard TLS endpoint CBOM has no `certificationLevel` or has `"none"` |
| BACK-56 datetime.utcnow before staleness gates | Tech debt phase (same milestone) | `git grep "utcnow" quirk/` returns 0 before any staleness module merges |

---

## Sources

- QU.I.R.K. codebase — `quirk/compliance/__init__.py`, `quirk/dashboard/api/routes/pdf.py`, `quirk/models.py` (direct code inspection, HIGH confidence)
- `.planning/PROJECT.md` — v4.7 milestone feature list and Key Decisions (HIGH confidence)
- [QRAMM Toolkit Overview — qramm.org](https://qramm.org/toolkit-overview.html) — 4 dimensions, 120 questions, 12 practice areas, profile multiplier 0.8–1.5x, 5-level thresholds (MEDIUM confidence — external framework, verify on each review)
- [CycloneDX v1.7 release — certificationLevel and FIPS inference caveat](https://cyclonedx.org/news/cyclonedx-v1.7-released/) — "compliance is usually inferred" caution (HIGH confidence)
- [Censinet — ISO 27001 and SOC 2 integration pitfalls](https://censinet.com/perspectives/iso-27001-and-soc-2-integration-common-pitfalls-to-avoid) — control alignment, scoping errors, documentation gaps (MEDIUM confidence)
- [Ampcus — ISO 27001 mapping with SOC2/HIPAA/PCI-DSS/NIST](https://www.ampcuscyber.com/ampcuscyber.com/blogs/iso-27001-mapping-with-security-standards/) — 2022 control restructure context (MEDIUM confidence)
- [Playwright PDF generation — print CSS regression risks](https://pdf4.dev/blog/html-to-pdf-benchmark-2026) — Chromium version pinning, print-specific CSS necessity (MEDIUM confidence)
- [Anecdotes — 3 types of automated compliance evidence](https://www.anecdotes.ai/post/3-types-of-automated-compliance-evidence-which-do-you-need) — false positive/negative risks in automated evidence (MEDIUM confidence)
- [NIST CSRC — FIPS 140-3 final](https://csrc.nist.gov/pubs/fips/140-3/final) — certificationLevel means module validation, not algorithm approval (HIGH confidence)

---
*Pitfalls research for: QU.I.R.K. v4.7 Governance & Compliance Platform milestone*
*Researched: 2026-05-05*
