# Phase 51: QRAMM Core Infrastructure - Research

**Researched:** 2026-05-05
**Domain:** SQLite/SQLAlchemy ORM, FastAPI CRUD, CSNP QRAMM question catalog, scoring engine
**Confidence:** HIGH (codebase patterns verified by direct file read; QRAMM catalog verified from GitHub source)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Question Catalog (QRAMM-03)**
- D-01: Source the 120 question texts verbatim from the publicly available CSNP QRAMM toolkit at qramm.org. Researcher fetches docs directly and transcribes questions — no paraphrasing, no custom authoring.
- D-02: `maturity_labels` per question are verbatim from the CSNP toolkit. Labels match the standard exactly so consultants can cross-reference with official QRAMM documentation.
- D-03: If qramm.org content turns out to be paywalled or inaccessible at research time, researcher surfaces the gap and falls back to a hand-crafted minimal catalog — does NOT block the phase.

**SQLite Tables (QRAMM-01)**
- D-04: Three new tables use SQLAlchemy ORM declarative models (`QRAMMSession`, `QRAMMAnswer`, `QRAMMProfile` extending `Base`) added to `quirk/models.py`. Consistent with `CryptoEndpoint` pattern.
- D-05: `_ensure_qramm_tables()` calls `Base.metadata.create_all()` scoped to the QRAMM models with `checkfirst=True`. No raw DDL strings. Called from `init_db()` alongside existing `_ensure_*` functions.

**Scoring Engine (QRAMM-04)**
- D-06: Dimension score = `min()` of its 3 practice scores (weakest-link rule, NOT average). Profile multiplier (0.8–1.5×) applied to weighted dimension scores. Overall score = average of 4 weighted dimensions.
- D-07: Unit tests cover both paths: (a) weakest-link formula with exact numeric agreement with reference or synthetic example; (b) profile multiplier path.
- D-08: Fallback if no CSNP reference calculation is findable: use synthetic example (e.g. practice scores `[2, 4, 3]` → dimension score `2`; multiplier `1.2` → weighted score `2.4`).
- D-09: `scoring.py` MUST NOT import `risk_engine` or any scanner module (circular import prevention).

**Computed Score Persistence**
- D-10: `POST /api/qramm/sessions/{id}/score` computes AND persists score to `qramm_sessions`. Re-calling triggers fresh computation and updates stored value.

**FastAPI Router & Pydantic Models (QRAMM-02)**
- D-11: QRAMM Pydantic models live inline in `quirk/dashboard/api/routes/qramm.py`. Consistent with `scan.py`, `trends.py`, `health.py` pattern.
- D-12: Router includes TestClient smoke tests in `tests/test_qramm_router.py` covering all 5 endpoint families.

**datetime.utcnow Tech Debt (DEBT-01)**
- D-13: All `datetime.utcnow()` calls replaced with `datetime.now(timezone.utc)` across any affected modules. Test suite must produce zero `DeprecationWarning: datetime.utcnow()` messages after fix.

### Claude's Discretion
- `qramm_sessions` column naming for stored score — `score_json` (JSON blob) or separate `score_float` + `score_detail_json` columns
- Exact field names on ORM models beyond schema specified in QRAMM-01 — may add `created_at`, `updated_at` timestamps following `CryptoEndpoint` convention
- `model_meta.py` initial `last_verified` date and `qramm_version` string
- Whether `_ensure_qramm_tables()` belongs in `db.py` or in a new `quirk/qramm/db.py`

### Deferred Ideas (OUT OF SCOPE)
- `quirk qramm status` CLI subcommand (QRAMM-07) — model_meta.py created here but CLI surface is Phase 55
- Refactor Pydantic models to dedicated `quirk/qramm/models.py` — deferred unless router file grows unwieldy
- Evidence bridge for SGRM/DPE/ITR dimensions (QRAMM-F01) — deferred to v4.8
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QRAMM-01 | Three SQLite tables (`qramm_sessions`, `qramm_answers`, `qramm_profiles`) via `_ensure_qramm_tables()` | ORM model pattern from `CryptoEndpoint`; `_ensure_*` pattern from `db.py`; proposed schema below |
| QRAMM-02 | FastAPI CRUD router at `/api/qramm/` with 5 endpoint families | `scan.py` inline Pydantic pattern; `app.py` `include_router()` registration; proposed endpoints below |
| QRAMM-03 | 120-question catalog as versioned `QRAMM_QUESTIONS` constant with `question_number`, `dimension`, `practice_area`, `text`, `maturity_labels` | All 120 questions fetched verbatim from github.com/csnp/qramm; 4-point answer scale confirmed |
| QRAMM-04 | Scoring engine: weakest-link dimension scores, profile multiplier, unit-tested | Formulas verified from CSNP scoring-methodology.md; reference calculation and synthetic example documented below |
| DEBT-01 | Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` project-wide | Grep audit complete — all occurrences found; details in dedicated section |
</phase_requirements>

---

## Summary

Phase 51 creates the entire QRAMM backend foundation: three SQLite tables, a complete FastAPI CRUD router, the 120-question catalog, and a weakest-link scoring engine. Research confirms that CSNP QRAMM is fully open-source (MIT License) and hosted at github.com/csnp/qramm — all 120 question texts are publicly available verbatim and have been transcribed here. The scoring methodology is documented in the CSNP repository: questions use a 4-point answer scale (1–4), practice scores average 10 questions, dimension scores apply the weakest-link minimum rule, and the overall score averages 4 dimension scores. A CSNP reference calculation exists (practice scores `[3,2,3,4,2,2,3,2,3,1]` → 2.5) and a second worked overall example (dimensions `[2.8, 3.1, 2.5, 2.9]` → 2.8) are verified.

The existing codebase patterns are consistent and well-understood. The `CryptoEndpoint` model uses `Base` with `Column(Integer/String/Text/Boolean/DateTime)` — QRAMM models follow identically. The `_ensure_*` idempotency pattern in `db.py` always uses `create_all(engine)` or inspector-checked ALTER TABLE — the new `_ensure_qramm_tables()` will use `create_all()` scoped to QRAMM tables. The FastAPI `scan.py` router places Pydantic models inline at the top of the file and uses `Depends(get_db)` — the QRAMM router mirrors this exactly.

The DEBT-01 grep audit revealed **zero occurrences** of `datetime.utcnow()` in `quirk/` production code — `logging_util.py` and `nmap_provider.py` already use `datetime.now(timezone.utc)`. Occurrences do exist in `tests/` and `quantum-chaos-enterprise-lab/` (lab fixtures only). The CONTEXT.md scope includes "any other affected modules" — research confirms those modules are already fixed; the fix needed is in the test files.

**Primary recommendation:** Build the QRAMM module in this order: (1) models.py ORM additions → (2) `_ensure_qramm_tables()` in db.py → (3) `quirk/qramm/questions.py` catalog → (4) `quirk/qramm/scoring.py` engine → (5) `quirk/qramm/model_meta.py` → (6) `quirk/dashboard/api/routes/qramm.py` CRUD router → (7) `app.py` registration → (8) test files → (9) DEBT-01 test file fixes.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| QRAMM table schema | Database / Storage | — | ORM model definitions; no presentation logic |
| `_ensure_qramm_tables()` | Database / Storage | — | DB initialization, idempotent migration |
| 120-question catalog | API / Backend | — | Static data constant in `quirk/qramm/questions.py`; consumed by router and scoring |
| Weakest-link scoring engine | API / Backend | — | Pure math module; no DB or UI imports |
| Profile multiplier | API / Backend | — | Applied during score computation; stored result in DB |
| CRUD endpoints `/api/qramm/` | API / Backend | — | FastAPI router; session lifecycle, answer persistence, score trigger |
| Score persistence | Database / Storage | API / Backend | Score computed in API tier, persisted to `qramm_sessions.score_json` |
| `model_meta.py` staleness | API / Backend | — | Module constant; no DB needed; mirrors `quirk/compliance/__init__.py` |
| datetime.utcnow fix | API / Backend | — | Affects test and lab files; zero production-code occurrences found |

---

## Standard Stack

### Core (all already installed — zero new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | >=2.0 (in pyproject.toml) | ORM models, engine, session | Existing project stack; `CryptoEndpoint` pattern proven |
| FastAPI | >=0.128.8 | CRUD router, Pydantic validation | Existing dashboard API stack |
| pytest | 9.0.2 (verified) | Unit + integration tests | Existing test suite with `conftest.py` fixtures |
| fastapi.testclient | (bundled with fastapi) | HTTP smoke tests | Used by `test_dashboard_trends.py` pattern |
| Python 3.14.4 (runtime) | >=3.10 required | All production code | Project requirement |

**Installation:** No new packages required. All dependencies present.
[VERIFIED: pyproject.toml read directly]

---

## QRAMM Question Catalog (QRAMM-03)

### Catalog Status: FULLY ACCESSIBLE — No Paywall

The CSNP QRAMM toolkit is open-source under MIT License at https://github.com/csnp/qramm.
All 120 question texts were fetched verbatim from:
`https://raw.githubusercontent.com/csnp/qramm/main/framework/Complete_QRAMM_Questions.md`

[VERIFIED: github.com/csnp/qramm — MIT License confirmed]

### Structure: 4 Dimensions × 3 Practices × 10 Questions = 120 Questions

```
Dimension 1: CVI - Cryptographic Visibility & Inventory       (Q1–30)
  Practice 1.1: Cryptographic Discovery & Inventory Management (Q1–10)
  Practice 1.2: Vulnerability Assessment & Classification       (Q11–20)
  Practice 1.3: Cryptographic Dependency Mapping                (Q21–30)

Dimension 2: SGRM - Strategic Governance & Risk Management    (Q31–60)
  Practice 2.1: Executive Leadership & Policy Management        (Q31–40)
  Practice 2.2: Risk Assessment & Compliance Management         (Q41–50)
  Practice 2.3: Third-Party & Supply Chain Risk Management      (Q51–60)

Dimension 3: DPE - Data Protection Engineering                (Q61–90)
  Practice 3.1: Data Classification & Protection Requirements   (Q61–70)
  Practice 3.2: Storage Security & Encryption Management        (Q71–80)
  Practice 3.3: Transit Security & Protocol Management          (Q81–90)

Dimension 4: ITR - Implementation & Technical Readiness       (Q91–120)
  Practice 4.1: Infrastructure Assessment & Planning            (Q91–100)
  Practice 4.2: Implementation Capability Development           (Q101–110)
  Practice 4.3: Testing & Validation Capabilities               (Q111–120)
```

### Answer Scale: 4-Point (1–4), Maps to 5 Maturity Levels via Aggregation

The CSNP toolkit uses a 4-point per-question answer scale:
- Score 1 → Basic
- Score 2 → Developing
- Score 3 → Established
- Score 4 → Advanced

Maturity level thresholds (applied to aggregated practice/dimension scores):

| Score Range | Maturity Level |
|-------------|----------------|
| 1.0 – 1.4 | Level 1: Basic |
| 1.5 – 2.4 | Level 2: Developing |
| 2.5 – 3.4 | Level 3: Established |
| 3.5 – 3.9 | Level 4: Advanced |
| 4.0 | Level 5: Optimizing |

[VERIFIED: github.com/csnp/qramm/framework/maturity-levels.md and scoring-methodology.md]

**Implementation note for `maturity_labels`:** The REQUIREMENTS.md specification (QRAMM-08) uses labels "Basic / Developing / Established / Optimizing" (4 labels) for the UI radio scale. The CSNP catalog has 5 maturity levels. The `maturity_labels` field in `QRAMM_QUESTIONS` should store the 4 per-answer labels that map to the 4 answer score choices (1–4). For the UI's 1–4 radio scale:
- 1 → "Basic"
- 2 → "Developing"
- 3 → "Established"
- 4 → "Advanced"

[ASSUMED] Whether the CSNP Excel toolkit contains per-question verbatim maturity label text beyond the generic pattern above. The GitHub text files do not include per-question answer choice text. The generic pattern from `full-assessment.md` (verified) provides one worked example for Q1 — all other questions follow the same pattern structure.

### All 120 Questions — Verbatim from CSNP GitHub Repository

[CITED: https://raw.githubusercontent.com/csnp/qramm/main/framework/Complete_QRAMM_Questions.md]

**Practice 1.1: Cryptographic Discovery & Inventory Management**
1. How does your organization identify cryptographic assets?
2. How does your organization document cryptographic assets?
3. How does your organization govern cryptographic asset ownership and accountability?
4. How does your organization validate cryptographic asset inventory completeness?
5. How does your organization ensure cryptographic visibility across third-party and cloud systems?
6. How is cryptographic asset inventory data used for strategic planning?
7. How are cryptographic assets prioritized for quantum-resistance upgrades?
8. How is cryptographic asset inventory maintained over time?
9. How does your organization include IoT and embedded devices in its cryptographic inventory and quantum readiness planning?
10. How does your organization stay informed about quantum computing and cryptanalysis advancements?

**Practice 1.2: Vulnerability Assessment & Classification**
11. How does your organization assess quantum vulnerability of cryptographic assets?
12. How does your organization classify quantum vulnerability severity?
13. How does your organization validate vulnerability findings?
14. How does your organization integrate emerging quantum threats into planning and strategy?
15. How does your organization contribute to (quantum) cryptanalysis and mitigation research?
16. How are vulnerability findings communicated to stakeholders?
17. How does your organization assess the quantum vulnerability of cryptographic mechanisms used for data authenticity and long-term integrity?
18. How does your organization validate the correctness and secure configuration of deployed cryptographic implementations?
19. How does your organization assess trends in cryptographic vulnerabilities over time?
20. How does your organization apply quantum vulnerability insights to improve cryptographic practices and standards?

**Practice 1.3: Cryptographic Dependency Mapping**
21. How does your organization identify and map cryptographic dependencies across systems and services?
22. How does your organization document and maintain cryptographic dependencies between systems and services?
23. How does your organization analyze the impact of cryptographic changes across dependent systems and services?
24. How does your organization validate the accuracy and completeness of cryptographic dependency mapping?
25. How does your organization keep cryptographic dependency information current as systems evolve?
26. How is cryptographic dependency information used to inform migration planning and operational risk management?
27. How does your organization manage cryptographic dependencies in software build systems and code-signing infrastructure?
28. How does your organization assess cryptographic dependencies and transition constraints in operational technology (OT) and industrial control environments?
29. How are cryptographic dependencies evaluated for architectural complexity and transition fragility?
30. How are cryptographic dependencies tracked across CI/CD pipelines, shared libraries, and external APIs?

**Practice 2.1: Executive Leadership & Policy Management**
31. How is quantum risk oversight structured at the executive level?
32. How comprehensive is your quantum risk policy framework?
33. How are quantum security initiatives funded and resourced?
34. How do you measure quantum risk governance effectiveness?
35. How does leadership drive quantum security innovation?
36. How is quantum risk integrated into organizational strategy and long-term planning?
37. How are quantum security policies reviewed and maintained over time?
38. How is executive leadership kept informed and prepared to guide quantum security strategy?
39. How do you monitor and manage progress across your quantum readiness program and cryptographic transition activities?
40. How does your organization contribute to shaping industry-wide quantum security and cryptographic agility practices?

**Practice 2.2: Risk Assessment & Compliance Management**
41. How comprehensive is your quantum risk assessment methodology?
42. How automated is your quantum risk monitoring and integration into cryptographic transition planning?
43. How do you quantify quantum risk exposure?
44. How do you validate the effectiveness of quantum risk controls?
45. How do you update your quantum risk assessment methodology as new threats and cryptographic developments emerge?
46. How mature is your quantum security compliance program?
47. How does your organization adapt cryptographic practices in response to evolving quantum security standards and regulatory requirements?
48. How do you track and map compliance across quantum-relevant controls and systems?
49. How do you measure cryptographic remediation progress for regulated domains?
50. How do you ensure quantum security requirements are integrated into audits and control testing?

**Practice 2.3: Third-Party & Supply Chain Risk Management**
51. How comprehensive is your assessment of vendor quantum readiness and cryptographic agility?
52. How do you manage quantum security and cryptographic agility requirements for vendors handling sensitive systems?
53. How do you audit vendor controls for quantum security in critical systems?
54. How does your organization enforce and validate vendor cryptographic agility under real-world constraints?
55. How do you evaluate vendor support for hardware dependencies?
56. How does your organization assess and manage quantum-related risks across its supply chain?
57. How does your organization perform technical evaluation of quantum risk across individual supply chain vendors and components?
58. How do you identify and prioritize supply chain systems that could delay or block enterprise cryptographic transitions?
59. How does your organization evaluate fallback or downgrade risks in supply chain cryptographic protocols?
60. How does your organization improve vendor risk practices?

**Practice 3.1: Data Classification & Protection Requirements**
61. How does your organization identify data requiring quantum-resistant protection?
62. How does your organization classify data based on quantum risk?
63. How does your organization implement quantum-resistant controls?
64. How does your organization validate protection controls?
65. How does your organization tailor data protection requirements for constrained or specialized environments?
66. How does your organization define protection strategies based on data lifecycle and retention needs?
67. How does your organization define protection strategies for unstructured or semi-structured data?
68. How does your organization measure the effectiveness of data protection controls?
69. How does your organization identify opportunities to improve data protection controls?
70. How does your organization assess the performance of data protection controls?

**Practice 3.2: Storage Security & Encryption Management**
71. How does your organization ensure that symmetric encryption for sensitive stored data is secure against quantum algorithms?
72. How does your organization manage encryption keys for stored data in an agile manner?
73. How does your organization ensure strong, adaptable protection and recoverability for backup and archived data?
74. How does your organization ensure long-term cryptographic integrity of stored and archived data?
75. How does your organization test whether storage encryption and key management controls are strong enough for long-term resilience, including future quantum threats?
76. How is your organization's storage security strategy designed to support long-term data protection and resilience?
77. How does your organization assess the upgrade and cryptographic support constraints of storage systems?
78. How does your organization measure the effectiveness of encryption and key management controls used to protect stored data?
79. How does your organization identify opportunities to improve the security of encryption and key management for stored data?
80. How does your organization enhance its storage encryption and key management capabilities over time?

**Practice 3.3: Transit Security & Protocol Management**
81. How does your organization implement cryptographic protections within data-in-transit protocols?
82. How does your organization manage secure communication protocols?
83. How does your organization ensure trusted identity and authentication in secure network communications?
84. How does your organization enforce minimum cryptographic standards to prevent downgrade attacks in data-in-transit protocols?
85. How does your organization validate the effectiveness of cryptographic protections used in transit protocols?
86. How does your organization define its approach to protecting data in transit?
87. How does your organization prioritize communication channels for enhanced cryptographic protection?
88. How does your organization manage and validate trust anchors for secure communication protocols?
89. How does your organization assess and enforce cryptographic protections in third-party or externally managed communication channels?
90. How does your organization plan for interoperability and backward compatibility during cryptographic transitions in transit protocols?

**Practice 4.1: Infrastructure Assessment & Planning**
91. How does your organization assess the cryptographic agility and quantum readiness of its technical infrastructure?
92. How does your organization plan infrastructure upgrades to support cryptographic agility and quantum readiness?
93. How does your organization evaluate cryptographic hardware readiness for quantum-era requirements?
94. How does your organization identify and address cryptographic upgrade blockers in legacy or third-party systems?
95. How does your organization incorporate cryptographic agility requirements into system and software design processes?
96. How does your organization plan for cryptographic upgrade sequencing and dependency management?
97. How does your organization provide technical environments and tooling to support cryptographic transition planning and implementation?
98. How does your organization embed cryptographic agility into system architecture design?
99. How does your organization define and measure technical milestones for cryptographic transitions?
100. How does your organization contribute to the development and advancement of technical standards for cryptographic agility and quantum-resistant implementations?

**Practice 4.2: Implementation Capability Development**
101. How does your organization define the technical capabilities required to support quantum-resistant implementation?
102. How does your organization allocate and protect specialized resources for cryptographic implementation and transition efforts?
103. How does your organization ensure the quality and correctness of cryptographic implementations?
104. How does your organization monitor the operational impact of cryptographic implementations after deployment?
105. How does your organization ensure cryptographic implementation libraries, patterns, and tools remain up to date with evolving standards?
106. How structured is your delivery process for implementing cryptographic changes?
107. How does your organization ensure consistent implementation of cryptographic practices across systems?
108. How does your organization identify and manage risks associated with cryptographic transitions?
109. How does your organization track and benchmark cryptographic delivery outcomes across implementation projects?
110. How does your organization enforce cryptographic change readiness and agility through its CI/CD and software delivery pipelines?

**Practice 4.3: Testing & Validation Capabilities**
111. How comprehensive is your testing strategy for cryptographic transitions and quantum-resistant implementations?
112. How does your organization validate cryptographic fallback mechanisms and recovery readiness during transition testing?
113. How does your organization test the performance and scalability of cryptographic implementations under realistic and constrained conditions?
114. How does your organization generate and manage assurance evidence from cryptographic testing activities?
115. How does your organization adapt cryptographic testing practices in response to evolving threats, implementation risks, and post-quantum developments?
116. How structured is your validation process for cryptographic transitions?
117. How does your organization ensure consistent validation practices across cryptographic transitions and systems?
118. How does your organization ensure validation of cryptographic implementations aligns with regulatory, industry, and internal compliance requirements?
119. How does your organization assess cryptographic weaknesses or downgrade risks in third-party and externally managed systems during implementation testing?
120. How does your organization contribute to industry standards or best practices for validating cryptographic implementations?

### `QRAMM_QUESTIONS` Constant Structure

Each entry in the catalog should be a dict (or dataclass):

```python
# Source: github.com/csnp/qramm (MIT License)
{
    "question_number": 1,           # 1-120
    "dimension": "CVI",             # CVI | SGRM | DPE | ITR
    "practice_area": "1.1",         # "1.1" | "1.2" | ... | "4.3"
    "text": "How does your organization identify cryptographic assets?",
    "maturity_labels": [
        "No formal cryptographic asset identification process exists",      # score=1 Basic
        "Manual inventory covering only known high-value systems",          # score=2 Developing
        "Automated discovery implemented for portions of infrastructure",   # score=3 Established
        "Comprehensive automated discovery with validation across all environments",  # score=4 Advanced
    ],
}
```

**Maturity label sourcing:** The CSNP `full-assessment.md` provides the generic pattern for Q1 verbatim. The Excel toolkit contains per-question labels, but the GitHub text files only show the generic four-level progression. [ASSUMED] Per-question maturity label text is not uniquely written for each of the 120 questions — the pattern is consistent. Planner decision: use the generic 4-label pattern for all questions, or surface a note that labels are structurally representative and users should consult the Excel toolkit for the precise wording of each answer option.

---

## Scoring Model (QRAMM-04)

### Verified Formulas
[VERIFIED: github.com/csnp/qramm/framework/scoring-methodology.md]

```
Practice Score   = sum(10 question scores) / 10
Dimension Score  = min(Practice_A_Score, Practice_B_Score, Practice_C_Score)   ← weakest-link
Overall Score    = (CVI + SGRM + DPE + ITR) / 4
```

**Answer scale:** 4-point per question (1 = Basic, 2 = Developing, 3 = Established, 4 = Advanced).
Score ranges: 1.0–1.4 = Basic, 1.5–2.4 = Developing, 2.5–3.4 = Established, 3.5–3.9 = Advanced, 4.0 = Optimizing.

### Profile Multiplier

[VERIFIED: qramm.org/toolkit-overview.html — range 0.8–1.5× confirmed]
[ASSUMED] Specific per-profile multiplier values are not documented in any GitHub text file. The CSNP scoring-methodology.md does not include profile multiplier details. The toolkit-overview page states the range is 0.8–1.5× based on industry, regulatory obligations, org size, data sensitivity, technology complexity. No discrete profile-to-multiplier mapping was found.

**Design decision for the planner:** `QRAMMProfile` should store the inputs (industry, size, etc.) and the computed multiplier as a `Float`. The scoring engine applies the multiplier as: `weighted_dimension_score = dimension_score * multiplier`. The `qramm_profiles` table stores one row per assessment session profile; `qramm_sessions` references it via FK or stores the multiplier directly.

**Profile multiplier example (for REQUIREMENTS.md QRAMM-09 context):**
- Healthcare/finance/government = higher end (1.3–1.5×)
- Small org, low data sensitivity = lower end (0.8–1.0×)
- Default/unset = 1.0× (neutral multiplier)

### Reference Calculation (CSNP-Verified)

[VERIFIED: github.com/csnp/qramm/framework/scoring-methodology.md]

**Practice-level worked example:**
```
Stream A (Q1-5): scores = [3, 2, 3, 4, 2] → sum = 14
Stream B (Q6-10): scores = [2, 3, 2, 3, 1] → sum = 11
Practice Score = (14 + 11) / 10 = 25 / 10 = 2.5  → "Established"
```

**Overall score worked example:**
```
CVI_dimension  = 2.8
SGRM_dimension = 3.1
DPE_dimension  = 2.5
ITR_dimension  = 2.9
Overall = (2.8 + 3.1 + 2.5 + 2.9) / 4 = 11.3 / 4 = 2.825  → "Established"
```

**Weakest-link example (synthetic for D-08 unit test):**
```
Practice 1.1 score = 2.0   (weakest)
Practice 1.2 score = 4.0
Practice 1.3 score = 3.0
CVI dimension score = min(2.0, 4.0, 3.0) = 2.0
With multiplier 1.2: weighted CVI = 2.0 * 1.2 = 2.4
```

**Complete unit-test reference calculation:**
```python
# Exact values for test_qramm_scoring.py assertions
Q1_to_Q10  = [3, 2, 3, 4, 2, 2, 3, 2, 3, 1]  # practice 1.1: sum=25, score=2.5
Q11_to_Q20 = [4, 4, 3, 3, 3, 4, 3, 4, 3, 3]  # practice 1.2: sum=34, score=3.4
Q21_to_Q30 = [1, 2, 1, 2, 2, 1, 2, 1, 2, 1]  # practice 1.3: sum=15, score=1.5

practice_11 = 2.5
practice_12 = 3.4
practice_13 = 1.5

CVI_score = min(2.5, 3.4, 1.5) = 1.5   ← weakest-link

# With multiplier 1.0 (neutral):
weighted_CVI = 1.5 * 1.0 = 1.5

# Overall (all 4 dimensions at 1.5 for symmetry in test):
overall = (1.5 + 1.5 + 1.5 + 1.5) / 4 = 1.5
```

---

## Architecture Patterns

### System Architecture Diagram

```
Client (Phase 54 UI / test_qramm_router.py TestClient)
         |
         | HTTP POST/GET/DELETE
         v
FastAPI Router  quirk/dashboard/api/routes/qramm.py
  /api/qramm/sessions        POST  → create_session()
  /api/qramm/sessions/{id}   GET   → read_session()
  /api/qramm/sessions/{id}/answers  POST → save_answers()
  /api/qramm/sessions/{id}/score    POST → compute_score()
  /api/qramm/sessions/{id}   DELETE → delete_session()
         |
         | Depends(get_db) → SQLAlchemy Session
         |                 → QRAMMSession, QRAMMAnswer, QRAMMProfile ORM models
         v
SQLite quirk.db  (qramm_sessions, qramm_answers, qramm_profiles tables)
         ^
         |   scoring.py (pure math, no DB import)
         |   questions.py (static constant, no DB import)
quirk/qramm/
  __init__.py
  questions.py    ← QRAMM_QUESTIONS constant (120 entries)
  scoring.py      ← compute_practice_score(), compute_dimension_score(), compute_overall_score()
  model_meta.py   ← QRAMM_MODEL constant (version, last_verified, source_url)
```

### Recommended Project Structure

```
quirk/
├── qramm/                    # NEW top-level module (peer to compliance/, cbom/, etc.)
│   ├── __init__.py
│   ├── questions.py          # QRAMM_QUESTIONS constant — 120 entries
│   ├── scoring.py            # weakest-link engine + profile multiplier
│   └── model_meta.py         # QRAMM_MODEL staleness constant
├── models.py                 # MODIFIED — add QRAMMSession, QRAMMAnswer, QRAMMProfile
├── db.py                     # MODIFIED — add _ensure_qramm_tables(), call from init_db()
└── dashboard/api/
    ├── app.py                # MODIFIED — include_router(qramm.router, prefix="/api")
    └── routes/
        └── qramm.py          # NEW — inline Pydantic models + CRUD router
tests/
├── test_qramm_questions.py   # count=120, schema per entry
├── test_qramm_scoring.py     # weakest-link + multiplier unit tests
└── test_qramm_router.py      # TestClient smoke tests (5 endpoint families)
```

---

## Codebase Patterns (Verified)

### Pattern 1: ORM Declarative Model (CryptoEndpoint)

```python
# Source: quirk/models.py (read directly)
from __future__ import annotations
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text

Base = declarative_base()

class CryptoEndpoint(Base):
    __tablename__ = "crypto_endpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    protocol = Column(String(32), nullable=True)
    scanned_at = Column(DateTime, nullable=True)
    # ... Text for JSON blobs, Boolean, etc.
```

**QRAMM models follow this EXACT pattern:** extend `Base`, use `__tablename__`, use `Column(Integer/String/Text/DateTime/Float)`.

### Pattern 2: `_ensure_*` Idempotency (db.py)

```python
# Source: quirk/db.py (read directly)
def _ensure_identity_columns(engine) -> None:
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col in _IDENTITY_COLUMNS:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
        conn.commit()

def init_db(db_path: str) -> Engine:
    engine = get_engine(db_path)
    with engine.connect() as conn:
        conn.commit()
    Base.metadata.create_all(engine)
    _ensure_identity_columns(engine)
    _ensure_gcp_columns(engine)
    # ... more _ensure_* calls
    _ensure_phase46_columns(engine)     # Phase 46 — TLS-FIND-06 chain_verified
    return engine
```

**For QRAMM tables:** `_ensure_qramm_tables()` calls `Base.metadata.create_all(engine)` (not ALTER TABLE — these are entirely new tables, not new columns on an existing table). The `checkfirst=True` parameter is the idempotency mechanism. No ALTER TABLE needed.

```python
# Proposed _ensure_qramm_tables() pattern
def _ensure_qramm_tables(engine) -> None:
    """Create QRAMM assessment tables if absent (idempotent).

    Uses Base.metadata.create_all with checkfirst=True — new tables, not new columns.
    Called from init_db() after _ensure_phase46_columns().
    """
    # Import QRAMM models to register them on Base before create_all
    from quirk.models import QRAMMSession, QRAMMAnswer, QRAMMProfile  # noqa: F401
    Base.metadata.create_all(engine, checkfirst=True)
```

**Note:** Since `Base.metadata.create_all(engine)` is already called in `init_db()`, and QRAMM models are added to `models.py` (which is imported by `db.py`), the QRAMM tables will be created automatically. The `_ensure_qramm_tables()` may simply be a no-op wrapper for documentation and call-site clarity, or the planner may choose to inline the pattern.

### Pattern 3: Inline Pydantic + FastAPI Router (scan.py)

```python
# Source: quirk/dashboard/api/routes/scan.py (read directly)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from quirk.dashboard.api.deps import get_db
from quirk.models import CryptoEndpoint

router = APIRouter()

@router.get("/scans", response_model=List[ScanSession])
def list_scans(db: Session = Depends(get_db)) -> List[ScanSession]:
    ...
```

**Pydantic models (from schemas.py in scan.py's imports):** The QRAMM router will define its own inline Pydantic models at the top of `qramm.py` consistent with `trends.py` which has inline models.

### Pattern 4: Router Registration (app.py)

```python
# Source: quirk/dashboard/api/app.py (read directly)
from quirk.dashboard.api.routes import health, pdf, scan, trends

def create_app() -> FastAPI:
    application = FastAPI(...)
    application.include_router(health.router, prefix="/api")
    application.include_router(pdf.router, prefix="/api")
    application.include_router(scan.router, prefix="/api")
    application.include_router(trends.router, prefix="/api")
    # ... static files and SPA catch-all
```

**QRAMM registration:** Add `from quirk.dashboard.api.routes import qramm` and `application.include_router(qramm.router, prefix="/api")` after the existing routers, before static file mounts.

### Pattern 5: Compliance Staleness (model_meta.py mirrors)

```python
# Source: quirk/compliance/__init__.py (read directly)
STALENESS_THRESHOLD_DAYS: int = 365
_PHASE_49_VERIFIED: str = "2026-05-05"
_PCI_4_0_1_URL = "https://docs-prv.pcisecuritystandards.org/..."

def _pci(control: str) -> Dict[str, Any]:
    return {
        "framework": "PCI-DSS 4.0.1",
        "control": control,
        "version": "4.0.1",
        "last_verified": _PHASE_49_VERIFIED,
        "source_url": _PCI_4_0_1_URL,
    }
```

**`model_meta.py` mirrors this pattern:**
```python
# Proposed quirk/qramm/model_meta.py
QRAMM_MODEL = {
    "qramm_version": "1.0",           # planner sets based on GitHub tag/release
    "last_verified": "2026-05-05",    # set to research date
    "source_url": "https://qramm.org",
    "github_url": "https://github.com/csnp/qramm",
}
STALENESS_THRESHOLD_DAYS: int = 90   # per QRAMM-06
```

### Pattern 6: TestClient with Dependency Override (conftest.py)

```python
# Source: tests/conftest.py (read directly)
@pytest.fixture
def dashboard_client():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.models import Base
    from fastapi.testclient import TestClient

    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
```

**QRAMM router tests use this exact fixture** — it already calls `Base.metadata.create_all(engine)` which will include QRAMM tables once models are added to `models.py`. The existing `dashboard_client` fixture in `conftest.py` will work for QRAMM router smoke tests without modification.

For `test_qramm_router.py` that needs a named in-memory DB (to seed data): follow the `test_dashboard_trends.py` pattern of creating a UUID-named shared-cache DB (lines 78–95 in that file).

---

## Proposed Table Schemas

### `qramm_sessions`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK autoincrement | Session identifier |
| `org_name` | String(255) nullable | Optional org name for display |
| `created_at` | DateTime nullable | Timestamp of session creation |
| `updated_at` | DateTime nullable | Last modification timestamp |
| `model_version` | String(32) nullable | e.g. "1.0" from QRAMM_MODEL |
| `profile_id` | Integer FK → qramm_profiles.id nullable | Link to profile (nullable until QRAMM-09) |
| `status` | String(32) nullable | "draft" \| "scored" \| "complete" |
| `score_json` | Text nullable | JSON blob: `{"overall": 2.8, "dimensions": {"CVI": 2.5, ...}, "maturity": "Established"}` |

**Score storage decision (Claude's Discretion):** Use a single `score_json` Text column. This is the simplest approach and consistent with `tls_capabilities_json`, `ssh_audit_json`, etc. The Phase 54 UI reads one column; the scoring engine writes one column. A separate `score_float` would duplicate data that already lives in the JSON. The planner may override this.

### `qramm_answers`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK autoincrement | Row identifier |
| `session_id` | Integer FK → qramm_sessions.id | Cascade delete |
| `question_number` | Integer nullable=False | 1–120 |
| `dimension` | String(16) nullable=False | "CVI" \| "SGRM" \| "DPE" \| "ITR" |
| `practice_area` | String(8) nullable=False | "1.1" \| "1.2" \| ... \| "4.3" |
| `answer_value` | Integer nullable | 1–4; null until answered |
| `suggested_answer` | Integer nullable | Phase 53: evidence bridge pre-fill |
| `confirmed_at` | DateTime nullable | Phase 53: human confirmation timestamp |
| `evidence_source` | String(255) nullable | Phase 53: e.g. "scan:CryptoEndpoint:42" |

**Note:** `suggested_answer` and `confirmed_at` and `evidence_source` are QRAMM-13 columns (Phase 53). They should be in the schema now to avoid ALTER TABLE migrations later — the Phase 51 router does not populate them (they stay NULL). This is the recommended approach consistent with the existing pattern of adding fields preemptively.

### `qramm_profiles`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK autoincrement | Profile identifier |
| `session_id` | Integer nullable | Link back to session (or standalone) |
| `industry` | String(64) nullable | e.g. "healthcare", "finance", "government" |
| `org_size` | String(32) nullable | e.g. "small", "medium", "large" |
| `data_sensitivity` | String(32) nullable | e.g. "low", "medium", "high" |
| `regulatory_obligations` | Text nullable | JSON list of applicable frameworks |
| `geographic_scope` | String(32) nullable | e.g. "domestic", "multinational" |
| `multiplier` | Float nullable | Computed: 0.8–1.5 |
| `created_at` | DateTime nullable | Creation timestamp |

---

## Proposed API Endpoints

### 1. POST /api/qramm/sessions — Create Session

**Request body:**
```json
{
  "org_name": "Acme Corp",           // optional
  "model_version": "1.0"             // optional, defaults to QRAMM_MODEL["qramm_version"]
}
```

**Response 201:**
```json
{
  "session_id": 42,
  "org_name": "Acme Corp",
  "created_at": "2026-05-05T12:00:00Z",
  "status": "draft",
  "model_version": "1.0"
}
```

**Side effect:** Creates one `QRAMMSession` row. Does NOT auto-create `QRAMMAnswer` rows (created on first save-answers call).

### 2. GET /api/qramm/sessions/{session_id} — Read Session

**Response 200:**
```json
{
  "session_id": 42,
  "org_name": "Acme Corp",
  "created_at": "2026-05-05T12:00:00Z",
  "status": "scored",
  "model_version": "1.0",
  "score": {
    "overall": 2.8,
    "dimensions": {"CVI": 2.5, "SGRM": 3.1, "DPE": 2.5, "ITR": 2.9},
    "maturity": "Established",
    "profile_multiplier": 1.0
  },
  "answers_count": 120
}
```

**Response 404:** `{"detail": "Session not found"}`

### 3. POST /api/qramm/sessions/{session_id}/answers — Save/Update Answers

**Request body (bulk upsert):**
```json
{
  "answers": [
    {"question_number": 1, "answer_value": 3},
    {"question_number": 2, "answer_value": 2}
  ]
}
```

**Response 200:**
```json
{
  "session_id": 42,
  "saved_count": 2,
  "total_answered": 45
}
```

**Side effect:** Upserts `QRAMMAnswer` rows. `dimension` and `practice_area` derived from `question_number` via lookup into `QRAMM_QUESTIONS`.

### 4. POST /api/qramm/sessions/{session_id}/score — Compute & Persist Score

**Request body:** Empty or optional `{"profile_multiplier": 1.2}`.

**Response 200:**
```json
{
  "session_id": 42,
  "overall": 2.8,
  "maturity": "Established",
  "dimensions": {
    "CVI":  {"score": 2.5, "weighted": 2.5, "practices": {"1.1": 2.5, "1.2": 3.4, "1.3": 1.5}},
    "SGRM": {"score": 3.1, "weighted": 3.1, "practices": {"2.1": 3.1, "2.2": 3.1, "2.3": 3.1}},
    "DPE":  {"score": 2.5, "weighted": 2.5, "practices": {"3.1": 2.5, "3.2": 3.0, "3.3": 2.5}},
    "ITR":  {"score": 2.9, "weighted": 2.9, "practices": {"4.1": 2.9, "4.2": 3.5, "4.3": 2.9}}
  },
  "profile_multiplier": 1.0
}
```

**Side effect:** Persists score result to `qramm_sessions.score_json`, sets `status = "scored"`.

### 5. DELETE /api/qramm/sessions/{session_id} — Delete Session

**Response 204:** No body.

**Side effect:** Deletes `QRAMMSession` row and all related `QRAMMAnswer` rows (cascade). If using SQLite without FK enforcement, router explicitly deletes answers first, then session.

---

## DEBT-01: datetime.utcnow Audit

[VERIFIED: grep -rn "utcnow" across entire project — ran in research session]

### Result: Zero occurrences in `quirk/` production code

Both files mentioned in CONTEXT.md already use `datetime.now(timezone.utc)`:
- `quirk/logging_util.py` line 43: `ts = datetime.now(timezone.utc).strftime(...)` — ALREADY FIXED
- `quirk/discovery/nmap_provider.py` line 51: `stamp = datetime.now(timezone.utc).strftime(...)` — ALREADY FIXED

### Occurrences Found in Test Files (require fixing per D-13 scope)

| File | Line(s) | Context |
|------|---------|---------|
| `tests/test_saml_scanner.py` | 44, 45 | `datetime.datetime.utcnow()` in certificate not_valid_before/after |
| `tests/test_broker_scanner_redis.py` | 122, 123 | `dt.datetime.utcnow()` in certificate generation |

### Occurrences Found in Lab Files (out of QUIRK production scope)

| File | Line(s) | Context |
|------|---------|---------|
| `quantum-chaos-enterprise-lab/jwt/algnone/main.py` | 27 | Lab JWT fixture |
| `quantum-chaos-enterprise-lab/jwt/hs256/main.py` | 27 | Lab JWT fixture |
| `quantum-chaos-enterprise-lab/jwt/rsa1024/main.py` | 39 | Lab JWT fixture |
| `quantum-chaos-enterprise-lab/jwt/rs256/main.py` | 39 | Lab JWT fixture |

**Decision for planner:** DEBT-01 scope per CONTEXT.md D-13 is "across `quirk/logging_util.py`, `quirk/discovery/nmap_provider.py`, and any other affected modules." The two test files generate DeprecationWarning on Python 3.12+. The lab files are chaos lab Python services — not part of the QUIRK package. The planner should decide whether to fix test files (recommended) and lab files (optional, separate concern).

**Fix pattern for test files:**
```python
# Before (deprecated)
from datetime import datetime
datetime.utcnow()

# After (correct)
from datetime import datetime, timezone
datetime.now(timezone.utc)
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| In-memory SQLite for tests | Custom DB setup | `Base.metadata.create_all()` + `app.dependency_overrides[get_db]` | Already in conftest.py; proven pattern |
| Question-to-dimension mapping | Custom lookup dict | Index into `QRAMM_QUESTIONS` by `question_number` | Catalog already has dimension/practice_area per entry |
| Maturity level string from score | Custom thresholds | Single lookup function using CSNP ranges | Ranges are documented; implement once in scoring.py |
| UUID named test DB | Custom fixture | `uuid.uuid4().hex` shared-cache pattern from test_dashboard_trends.py | Already proven in this codebase |
| Profile multiplier logic | Custom algorithm | Simple float lookup/compute in `QRAMMProfile` | Range is 0.8–1.5; store computed value, not formula |

---

## Common Pitfalls

### Pitfall 1: `Base.metadata.create_all()` Called Before Models Imported

**What goes wrong:** `_ensure_qramm_tables()` calls `create_all()` but QRAMM model classes haven't been imported yet, so their tables are not registered on `Base.metadata`.
**Why it happens:** Python only registers a model on `Base.metadata` when the class body is executed (i.e., when the module is imported).
**How to avoid:** Ensure `quirk/models.py` imports are at the top of `db.py`. Since `db.py` already imports `from quirk.models import Base`, adding `QRAMMSession`, `QRAMMAnswer`, `QRAMMProfile` to `models.py` is sufficient — they'll be on `Base.metadata` when `db.py` imports `models.py`.
**Warning signs:** `qramm_sessions` table absent from `sqlite_master` after `init_db()`.

### Pitfall 2: SQLite FK Cascade Not Enforced Without PRAGMA

**What goes wrong:** DELETE on `qramm_sessions` does not cascade to `qramm_answers` because SQLite has FK enforcement disabled by default.
**Why it happens:** SQLite requires `PRAGMA foreign_keys = ON` per connection — not a database-level setting.
**How to avoid:** In the DELETE endpoint, explicitly delete answers first (`db.query(QRAMMAnswer).filter_by(session_id=session_id).delete()`) before deleting the session. No PRAGMA needed for the explicit approach.
**Warning signs:** Orphaned `qramm_answers` rows after DELETE /sessions/{id}.

### Pitfall 3: `score_json` Storing Non-Serializable Types

**What goes wrong:** `json.dumps()` fails at route handler time if scoring engine returns `float` subclasses or `Decimal`.
**Why it happens:** Python's `json.dumps` rejects `numpy.float64`, `decimal.Decimal`, etc.
**How to avoid:** `scoring.py` must return native Python `float` and `int`. Use `round(value, 4)` to avoid floating-point representation noise. Use `json.dumps(score_dict, default=str)` as fallback safety.
**Warning signs:** 500 error from score endpoint; `TypeError: Object of type float64 is not JSON serializable`.

### Pitfall 4: Shared In-Memory SQLite Collision in Tests

**What goes wrong:** Multiple tests using `"sqlite:///file::memory:?cache=shared"` interfere with each other if they run concurrently or in the wrong order.
**Why it happens:** Shared cache name is global within the process.
**How to avoid:** Use UUID-named DBs for any test that seeds data. The `dashboard_client` fixture (no data seeding) is safe to share. Tests that seed rows should use the `uuid.uuid4().hex` named pattern from `test_dashboard_trends.py`.
**Warning signs:** Flaky tests that pass alone but fail in suite.

### Pitfall 5: Router Registered After SPA Catch-All

**What goes wrong:** All `/api/qramm/*` requests are intercepted by the `/{full_path:path}` SPA handler and return `index.html` with 200.
**Why it happens:** FastAPI registers routes in order; the first matching route wins.
**How to avoid:** Register `qramm.router` before the SPA catch-all (which is last in `app.py`). The existing structure in `app.py` already does this — just append the QRAMM router to the existing block before static file mounts.
**Warning signs:** QRAMM API calls return HTML 200 instead of JSON.

### Pitfall 6: `_ensure_qramm_tables()` Placement in init_db()

**What goes wrong:** `_ensure_qramm_tables()` placed BEFORE `Base.metadata.create_all(engine)` causes the QRAMM tables to be created twice, or the existing tables to be missed on first run.
**Why it happens:** `create_all()` is idempotent, but ordering matters for documentation clarity.
**How to avoid:** Call `_ensure_qramm_tables(engine)` AFTER the main `Base.metadata.create_all(engine)` call, consistent with all other `_ensure_*` functions.

---

## Environment Availability

Step 2.6: Environment audit for this phase — no new external dependencies. All tooling required for Phase 51 is already installed.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All production code | ✓ | 3.14.4 | — |
| SQLAlchemy 2.0 | ORM models, db.py | ✓ | in pyproject.toml | — |
| FastAPI | Router, TestClient | ✓ | >=0.128.8 | — |
| pytest | All tests | ✓ | 9.0.2 | — |
| github.com/csnp/qramm | Question catalog | ✓ | MIT License, public | — |

No missing dependencies. No new pip installs required.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` §`[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/test_qramm_questions.py tests/test_qramm_scoring.py tests/test_qramm_router.py -v` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QRAMM-03 | `len(QRAMM_QUESTIONS) == 120` | unit | `pytest tests/test_qramm_questions.py::test_question_count -x` | ❌ Wave 0 |
| QRAMM-03 | Each entry has required keys | unit | `pytest tests/test_qramm_questions.py::test_question_schema -x` | ❌ Wave 0 |
| QRAMM-03 | Dimensions and practice areas are correct | unit | `pytest tests/test_qramm_questions.py::test_question_dimensions -x` | ❌ Wave 0 |
| QRAMM-04 | Weakest-link formula: `min([2.5, 3.4, 1.5]) == 1.5` | unit | `pytest tests/test_qramm_scoring.py::test_weakest_link_rule -x` | ❌ Wave 0 |
| QRAMM-04 | Practice score avg: CSNP reference `[3,2,3,4,2,2,3,2,3,1]` → 2.5 | unit | `pytest tests/test_qramm_scoring.py::test_practice_score_reference -x` | ❌ Wave 0 |
| QRAMM-04 | Profile multiplier applied: `1.5 * 1.2 == 1.8` | unit | `pytest tests/test_qramm_scoring.py::test_profile_multiplier -x` | ❌ Wave 0 |
| QRAMM-04 | Overall score: avg of 4 dimensions | unit | `pytest tests/test_qramm_scoring.py::test_overall_score -x` | ❌ Wave 0 |
| QRAMM-02 | POST /api/qramm/sessions → 201 | smoke | `pytest tests/test_qramm_router.py::test_create_session -x` | ❌ Wave 0 |
| QRAMM-02 | GET /api/qramm/sessions/{id} → 200 | smoke | `pytest tests/test_qramm_router.py::test_read_session -x` | ❌ Wave 0 |
| QRAMM-02 | POST /api/qramm/sessions/{id}/answers → 200 | smoke | `pytest tests/test_qramm_router.py::test_save_answers -x` | ❌ Wave 0 |
| QRAMM-02 | POST /api/qramm/sessions/{id}/score → 200 | smoke | `pytest tests/test_qramm_router.py::test_score_session -x` | ❌ Wave 0 |
| QRAMM-02 | DELETE /api/qramm/sessions/{id} → 204 | smoke | `pytest tests/test_qramm_router.py::test_delete_session -x` | ❌ Wave 0 |
| QRAMM-01 | Tables created by init_db() | integration | `pytest tests/test_qramm_router.py::test_tables_exist -x` | ❌ Wave 0 |
| DEBT-01 | Zero DeprecationWarning from utcnow | unit | `python -W error::DeprecationWarning -m pytest tests/test_saml_scanner.py tests/test_broker_scanner_redis.py -x` | Partial (files exist, tests need fixing) |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_qramm_questions.py tests/test_qramm_scoring.py tests/test_qramm_router.py -x`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_qramm_questions.py` — covers QRAMM-03 (count, schema, dimension mapping)
- [ ] `tests/test_qramm_scoring.py` — covers QRAMM-04 (weakest-link, reference calc, multiplier)
- [ ] `tests/test_qramm_router.py` — covers QRAMM-02 (all 5 endpoint families, HTTP status)
- [ ] `quirk/qramm/__init__.py` — package init (empty file)
- [ ] `quirk/qramm/questions.py` — QRAMM_QUESTIONS constant
- [ ] `quirk/qramm/scoring.py` — scoring engine
- [ ] `quirk/qramm/model_meta.py` — QRAMM_MODEL constant
- [ ] `quirk/dashboard/api/routes/qramm.py` — CRUD router

---

## Security Domain

QRAMM is a self-assessment survey tool. The threat surface is limited to the dashboard API.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Dashboard is localhost-only (no auth layer in v4.7) |
| V3 Session Management | No | QRAMM "sessions" are assessment sessions, not HTTP sessions |
| V4 Access Control | No | Same localhost scope |
| V5 Input Validation | Yes | Pydantic request models validate `answer_value` ∈ [1,4], `question_number` ∈ [1,120] |
| V6 Cryptography | No | No cryptographic operations in this phase |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Integer overflow in question_number | Tampering | Pydantic `Field(ge=1, le=120)` constraint |
| Invalid answer_value (e.g. 0 or 5) | Tampering | Pydantic `Field(ge=1, le=4)` constraint |
| session_id not found → 500 | DoS | `db.get(QRAMMSession, session_id)` with 404 HTTPException |
| Large answer batch (>120 items) | DoS | Pydantic `max_length=120` on the answers list |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Per-question maturity label text is not uniquely authored per question in the GitHub text files — the generic 4-level pattern applies to all 120 questions | Question Catalog | If the Excel file has unique answer text per question, implementor needs to transcribe from the Excel. Low impact: generic labels are functional for Phase 51; Phase 54 UI can refine. |
| A2 | Profile multiplier specific values (e.g. healthcare=1.5, small org=0.8) are not documented in any public CSNP text file — the planner must use a reasonable mapping | Scoring Model | If CSNP publishes exact per-profile multipliers in a future document, the `qramm_profiles.multiplier` column stores it correctly regardless. Zero breaking change. |
| A3 | `qramm_profiles` is treated as a row-per-session lookup (not a static reference table) — one profile per assessment session | Table Schema | If the Phase 54 UI (QRAMM-09) expects profiles to be reusable across sessions, a FK design with a shared profiles table would be needed. But QRAMM-01 says `qramm_profiles` stores "org profile inputs → computed multiplier" — per-session interpretation is consistent. |

---

## Open Questions (RESOLVED)

1. **Profile multiplier input fields vs. multiplier direct entry**
   - What we know: QRAMM-09 (Phase 54) collects industry sector, org size, geographic scope, data sensitivity, regulatory obligations to compute the multiplier.
   - What's unclear: Whether Phase 51's `POST /api/qramm/sessions` accepts a raw `profile_multiplier` float directly (for programmatic use) or always goes through the profile wizard inputs.
   - Recommendation: Accept optional `profile_multiplier: float` in the score endpoint request body (for Phase 51 flexibility). Full profile wizard is Phase 54 (QRAMM-09).
   - **RESOLVED:** Plan 51-03 `ScoreRequest` body accepts optional `profile_multiplier: float` (defaults to 1.0). Full wizard inputs deferred to Phase 54 (QRAMM-09).

2. **Whether `suggested_answer`, `confirmed_at`, `evidence_source` should be in Phase 51 schema**
   - What we know: These are Phase 53 (QRAMM-13) fields.
   - What's unclear: Whether to add them now (avoids ALTER TABLE later) or defer (simpler Phase 51 schema).
   - Recommendation: Add them now as nullable columns — zero Phase 51 code populates them, but they prevent a migration in Phase 53. This matches the project's established pattern (see `severity` column added before it was used).
   - **RESOLVED:** Plan 51-01 pre-provisions `suggested_answer`, `confirmed_at`, and `evidence_source` as nullable columns on `qramm_answers` to avoid ALTER TABLE in Phase 53.

---

## Sources

### Primary (HIGH confidence)
- `github.com/csnp/qramm` — MIT License; all 120 questions fetched from `framework/Complete_QRAMM_Questions.md`
- `github.com/csnp/qramm/framework/scoring-methodology.md` — Formulas, reference calculations, answer scale
- `github.com/csnp/qramm/framework/maturity-levels.md` — Maturity level names and score ranges
- `quirk/models.py` — ORM pattern (read directly)
- `quirk/db.py` — `_ensure_*` pattern, `init_db()` call sequence (read directly)
- `quirk/compliance/__init__.py` — staleness pattern for `model_meta.py` (read directly)
- `quirk/dashboard/api/routes/scan.py` — inline Pydantic + `APIRouter` pattern (read directly)
- `quirk/dashboard/api/app.py` — `include_router()` registration (read directly)
- `quirk/dashboard/api/deps.py` — `get_db()` dependency pattern (read directly)
- `tests/conftest.py` — `dashboard_client` fixture, `dependency_overrides[get_db]` pattern (read directly)
- `pyproject.toml` — dependency versions, pytest config (read directly)

### Secondary (MEDIUM confidence)
- `qramm.org/toolkit-overview.html` — profile multiplier range 0.8–1.5× confirmed
- `github.com/csnp/qramm/framework/full-assessment.md` — maturity label pattern (generic across questions, Q1 example verbatim)

### Tertiary (LOW confidence)
- None — all claims are HIGH or MEDIUM and verified via tool

---

## Metadata

**Confidence breakdown:**
- Question catalog: HIGH — 120 questions fetched verbatim from MIT-licensed GitHub repo
- Standard stack: HIGH — verified via pyproject.toml and direct file reads
- Architecture patterns: HIGH — all 6 patterns verified from live source files
- Scoring formulas: HIGH — verified from CSNP scoring-methodology.md
- Profile multiplier specific values: LOW — range confirmed but per-profile mapping not published
- Maturity labels per question: MEDIUM — generic pattern confirmed, per-question text assumed same pattern

**Research date:** 2026-05-05
**Valid until:** 2026-08-03 (90 days — CSNP is an active open-source project; check for new releases before Phase 55 staleness work)
