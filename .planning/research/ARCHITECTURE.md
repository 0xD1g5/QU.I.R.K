# Architecture Research — v4.7 QRAMM Integration

**Domain:** Governance/compliance platform extension — QRAMM maturity model + SOC2/ISO27001 compliance mapping onto existing QUIRK scanner
**Researched:** 2026-05-05
**Confidence:** HIGH (based on direct codebase inspection; no speculative claims)

---

## Current Architecture Baseline (v4.6)

```
┌─────────────────────────────────────────────────────────────────────┐
│  CLI Layer  (run_scan.py — single entry point `quirk`)               │
│  Subcommands: init | serve | compliance | [scan args]               │
│  Pattern: manual sys.argv[1] interception before argparse            │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────────┐
         │                 │                     │
┌────────▼────────┐ ┌──────▼───────┐ ┌──────────▼──────────────────┐
│  Scanner Layer  │ │  Engine Layer│ │  Dashboard Layer             │
│ quirk/scanner/  │ │quirk/engine/ │ │  FastAPI (quirk/dashboard/)  │
│  tls_scanner    │ │ risk_engine  │ │  /api/scan/latest  (scan.py) │
│  ssh_scanner    │ │ scoring      │ │  /api/trends       (trends)  │
│  jwt_scanner    │ │ migration_   │ │  /api/pdf          (pdf.py)  │
│  ...12 scanners │ │  planner     │ │  /api/health                 │
└────────┬────────┘ │ profiles     │ │                              │
         │          └──────┬───────┘ │  React SPA (src/dashboard/)  │
         │                 │         │  10 pages (executive, findings│
┌────────▼─────────────────▼───────┐ │  identity, motion, dat, certs│
│  Persistence Layer                │ │  cbom, roadmap, trends, print│
│  quirk/db.py + quirk/models.py    │ └──────────────────────────────┘
│  SQLite — single table:           │
│  crypto_endpoints (93 columns)    │
│  ALTER TABLE migration per phase  │
└───────────────────────────────────┘
         │
┌────────▼──────────────────────────┐
│  Support Modules                  │
│  quirk/cbom/    — 3-pass pipeline │
│  quirk/compliance/ — COMPLIANCE_  │
│    MAP dict + status_report()     │
│  quirk/intelligence/ — scoring    │
│  quirk/reports/ — HTML/PDF        │
└───────────────────────────────────┘
```

### Key Architectural Facts Confirmed by Inspection

1. **Single ORM table.** `crypto_endpoints` in `quirk/models.py` holds all scan data. Every new scanner phase appended columns via `ALTER TABLE` migrations in `quirk/db.py`. There is no findings table — findings are derived at query time in `routes/scan.py _derive_findings()`.

2. **Migration pattern is `_ensure_*_columns()` chains.** `init_db()` calls 7 stacked `_ensure_` functions in order. QRAMM's 3 new tables will be standalone SQLAlchemy `Base` subclasses with a corresponding `_ensure_qramm_tables()` at the end of `init_db()`.

3. **FastAPI routes are one file per logical domain.** `routes/health.py`, `routes/scan.py`, `routes/trends.py`, `routes/pdf.py` — each registered in `app.py` with `include_router`. QRAMM gets `routes/qramm.py`.

4. **CLI subcommands are manual `sys.argv[1]` branches in `run_scan.py`.** `init`, `serve`, `compliance` each have their own `if len(_sys.argv) > 1 and _sys.argv[1] == "..."` block. `quirk qramm` and `quirk doctor` follow the exact same pattern.

5. **React SPA uses BrowserRouter with file-per-page structure.** Each page is `src/dashboard/src/pages/<name>.tsx`, added to `App.tsx`'s `<Routes>`. QRAMM wizard gets `pages/qramm.tsx` (and sub-components under `components/qramm/`).

6. **`COMPLIANCE_MAP` is a module-level dict in `quirk/compliance/__init__.py`.** It is keyed by finding title string. SOC2 and ISO27001 entries are added to the same dict using new `_soc2()` / `_iso()` helper functions matching the existing `_pci()`, `_hipaa()`, `_fips()` pattern.

7. **CBOM pipeline is 3-pass in `quirk/cbom/builder.py`.** Pass 1: algorithm components. Pass 2: certificate components. Pass 3: protocol components. FIPS annotations are added as properties on existing Pass-1 algorithm components — not a separate pass.

---

## QRAMM Integration: Decisions and Rationale

### Decision 1: Where the 3 QRAMM Tables Live

**Recommended approach:** Add three new SQLAlchemy ORM classes to `quirk/models.py` alongside `CryptoEndpoint`. They are independent top-level tables, not columns on `crypto_endpoints`.

```python
# quirk/models.py additions

class QRAMMSession(Base):
    __tablename__ = "qramm_sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    org_profile_id = Column(Integer, ForeignKey("qramm_profiles.id"), nullable=True)
    status = Column(String(16), nullable=False, default="in_progress")  # in_progress | complete
    # Cached per-dimension scores (updated on each save)
    score_cvi = Column(Float, nullable=True)
    score_sgrm = Column(Float, nullable=True)
    score_dpe = Column(Float, nullable=True)
    score_itr = Column(Float, nullable=True)
    # Staleness metadata
    qramm_version = Column(String(16), nullable=False, default="1.0")
    last_verified = Column(String(10), nullable=True)   # ISO date YYYY-MM-DD
    source_url = Column(Text, nullable=True)


class QRAMMAnswer(Base):
    __tablename__ = "qramm_answers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("qramm_sessions.id"), nullable=False)
    question_number = Column(Integer, nullable=False)   # 1-120
    dimension = Column(String(8), nullable=False)       # CVI | SGRM | DPE | ITR
    practice = Column(String(16), nullable=False)       # e.g. CVI-1
    stream = Column(String(16), nullable=False)         # foundation | advanced
    answer = Column(Integer, nullable=True)             # 1-4 (null = unanswered)
    evidence_note = Column(Text, nullable=True)
    auto_populated = Column(Boolean, default=False)     # True = evidence bridge filled this


class QRAMMProfile(Base):
    __tablename__ = "qramm_profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    industry = Column(String(64), nullable=True)
    size = Column(String(32), nullable=True)            # SMB | Enterprise | Large Enterprise
    geo_scope = Column(String(32), nullable=True)       # Local | National | Global
    data_sensitivity = Column(String(32), nullable=True) # Low | Medium | High | Critical
    regulatory_requirements = Column(Text, nullable=True) # JSON list of framework strings
    multiplier = Column(Float, nullable=False, default=1.0)  # 0.8-1.5
```

**Why independent tables, not columns on `crypto_endpoints`:** QRAMM sessions are a completely different entity from scan endpoints. A session has a lifecycle (in_progress/complete), relates to one org profile, and contains up to 120 answers. Forcing this into `crypto_endpoints` would be structurally wrong — there is no `(host, port)` pairing. Independent tables with FK relationships are correct relational design.

**Why in `models.py` (not a new file):** Existing pattern — `CryptoEndpoint` is the only ORM class and lives in `models.py`. Keeping all ORM classes in one file means `Base.metadata.create_all(engine)` in `init_db()` picks them up automatically without extra imports.

**Migration:** Add `_ensure_qramm_tables(engine)` at the end of `init_db()`. Use `inspector.get_table_names()` to check table existence before `Base.metadata.create_all(engine, tables=[QRAMMSession.__table__, ...])`. This is idempotent and follows the spirit of the existing `_ensure_*` pattern while being cleaner for whole-table creation than `ALTER TABLE`.

---

### Decision 2: Evidence Bridge — Read from SQLite at Session-Start

**Recommended approach:** At session creation time, read the latest scan's `CryptoEndpoint` rows from SQLite and compute `auto_populated` answers immediately. Store them in `qramm_answers` with `auto_populated=True`. Do not pass findings at session creation via API.

**Data flow:**

```
POST /api/qramm/sessions
  |
  ├── CREATE QRAMMSession (status=in_progress)
  ├── (optional) link QRAMMProfile if org_profile_id provided
  ├── fetch MAX(scanned_at) scan window from crypto_endpoints
  |     (reuse SESSION_BRACKET = timedelta(minutes=5) pattern from routes/scan.py)
  ├── call quirk.qramm.evidence_bridge.derive_answers(endpoints) -> List[AnswerHint]
  └── bulk-INSERT qramm_answers with auto_populated=True for derived hints
      -> returns { session_id, auto_populated_count }
```

**Why read at session-start, not passed at creation:** If the client passes findings, the caller must load them — adding a roundtrip and tying the API shape to the full endpoint model. The backend is co-located with the database (local CLI model). Reading from SQLite directly is cheaper than client-round-tripping bulk endpoint data. Session creation is the only moment when evidence is "fresh" relative to the latest scan — loading later risks stale derivation against a superseded scan. This matches how `routes/scan.py` already reads at request time.

**Where evidence bridge lives:** New module `quirk/qramm/evidence_bridge.py`. It imports `CryptoEndpoint` from `quirk/models` only. It is called by the QRAMM route, not by the scanner. Input: `List[CryptoEndpoint]`. Output: `List[dict]` with keys `{question_number, dimension, practice, stream, answer, evidence_note}`.

**Mapping scope confirmed by ROADMAP.md (BACK-71):** CVI-1.1 (automated discovery), CVI-1.2 (severity-classified findings + NIST PQC labels), DPE-1.1 (TLS 1.3 / AES-256 in use), ITR-1.1 (TLS coverage rate, weak-cipher rate). All 4 CVI foundation questions partially auto-populatable. SGRM and most advanced questions remain manual.

---

### Decision 3: `quirk qramm status` CLI Placement

**Recommended approach:** New `qramm` subcommand block in `run_scan.py`, parallel to the existing `compliance` block. Do NOT extend `quirk compliance status`.

**Implementation pattern** (matching Phase 49's `compliance` block exactly):

```python
# run_scan.py — after the compliance block
if len(_sys.argv) > 1 and _sys.argv[1] == "qramm":
    qramm_parser = argparse.ArgumentParser(
        prog="quirk qramm",
        description="Manage QRAMM assessment sessions and staleness",
    )
    qramm_sub = qramm_parser.add_subparsers(dest="action", required=True)
    status_sub = qramm_sub.add_parser("status", help="Print QRAMM framework version and staleness metadata")
    status_sub.add_argument("--format", choices=["text", "json"], default="text")
    status_sub.add_argument("--db", default="./quirk.db", help="Path to quirk.db")
    qramm_args = qramm_parser.parse_args(_sys.argv[2:])
    if qramm_args.action == "status":
        from quirk.qramm import status_report as qramm_status
        qramm_status(db_path=qramm_args.db, format=qramm_args.format)
    return
```

**Why separate from `quirk compliance status`:** `quirk compliance status` is currently DB-free — it reads from the static `COMPLIANCE_MAP` dict with no I/O. Adding QRAMM staleness (which requires a DB read for `qramm_sessions.last_verified`) forces a `--db` flag and DB connection onto a previously zero-dependency command. Mixing them breaks single-responsibility. Separate subcommands preserve the compliance command's zero-dependency design.

**`quirk doctor`** — same `sys.argv` interception pattern: a new `if _sys.argv[1] == "doctor"` block that runs health checks (DB accessible, extras installed, COMPLIANCE_MAP staleness, QRAMM staleness if sessions exist) and prints a status table. `doctor` calls into both `quirk.compliance.status_report()` and `quirk.qramm.status_report()` — it is the aggregate view.

---

### Decision 4: CBOM FIPS Annotations — Property on Existing Pass-1 Components

**Recommended approach:** Add a FIPS-status property to existing algorithm `Component` objects during Pass 1. Do not create a separate annotation pass.

**Implementation:**

```python
# In quirk/cbom/builder.py — Pass 1 loop, after component creation
# CycloneDX 1.6 Component.properties is a set of Property objects

fips_status = _fips_status_for_algorithm(algo_name, nist_level)
if fips_status:
    comp.properties.add(Property(name="fips-140-3:status", value=fips_status))
    comp.properties.add(Property(name="fips-140-3:reference", value="FIPS 140-3 / SP 800-131A R2"))
```

**FIPS status values (3-tier):**
- `"approved"` — AES-256-GCM, ECDH-P384, ML-KEM, ML-DSA, SLH-DSA, SHA-256, SHA-3
- `"approved-with-deprecation-2030"` — RSA-2048+, ECDSA-P256+, ECDH-P256 (NIST IR 8547 schedule)
- `"not-approved"` — RSA<2048, EC<256, MD5, SHA-1, RC4, DES, 3DES, TLS 1.0/1.1 cipher suites

Helper function `_fips_status_for_algorithm(algo_name: str, nist_level: int | None) -> str | None` belongs in `quirk/cbom/classifier.py`, alongside the existing `quantum_safety_label()` function. This groups all algorithm classification logic in one place.

**Why not a separate pass:** Pass 1 already has `algo_name` and `nist_level` in scope. A 4th pass would re-iterate all components to attach a property computable from data already in hand during Pass 1. The existing 3-pass structure exists because Pass 2 (certs) and Pass 3 (protocols) operate on different input data. FIPS status derives from the same data Pass 1 already processes.

---

### Decision 5: SOC2/ISO27001 COMPLIANCE_MAP Extension

**Recommended approach:** Add `_soc2()` and `_iso()` helper functions in `quirk/compliance/__init__.py`, matching the shape of existing `_pci()`, `_hipaa()`, `_fips()`. Extend existing `COMPLIANCE_MAP` entries with new framework dicts. Add a new `_PHASE_XX_VERIFIED` constant for the verification date.

```python
_SOC2_TR_URL = "https://www.aicpa-cima.com/resources/landing/2017-trust-services-criteria"
_ISO_27001_URL = "https://www.iso.org/standard/82875.html"  # ISO/IEC 27001:2022

def _soc2(control: str) -> Dict[str, Any]:
    return {
        "framework": "SOC 2 (Trust Services Criteria)",
        "control": control,
        "version": "2017-rev",
        "last_verified": _PHASE_XX_VERIFIED,
        "source_url": _SOC2_TR_URL,
    }

def _iso(control: str) -> Dict[str, Any]:
    return {
        "framework": "ISO/IEC 27001:2022",
        "control": control,
        "version": "2022",
        "last_verified": _PHASE_XX_VERIFIED,
        "source_url": _ISO_27001_URL,
    }
```

**Representative mappings for existing finding categories:**

| Finding Category | SOC2 Control | ISO 27001:2022 Annex A |
|-----------------|-------------|------------------------|
| Legacy TLS versions allowed (TLS 1.0/1.1) | CC6.7 | A.8.24 (Use of cryptography) |
| Plaintext HTTP service detected | CC6.7 | A.8.20 (Networks security) |
| TLS certificate expired | CC9.9 (Availability) | A.8.24 |
| TLS certificate uses undersized RSA key | CC6.7 | A.8.24 |
| Plaintext Kafka listener detected | CC6.7 | A.8.20 |

**CI staleness gate:** The existing `status_report()` iterates all `COMPLIANCE_MAP` entries and surfaces the oldest `last_verified` per framework. New SOC2/ISO entries participate in this check automatically. No gate code changes needed.

**STALENESS_THRESHOLD_DAYS:** The existing constant is 365 days (annual review). QRAMM staleness is 90 days (quarterly). Keep them separate: `quirk/compliance/__init__.py` retains `STALENESS_THRESHOLD_DAYS = 365`, `quirk/qramm/staleness.py` defines `STALENESS_THRESHOLD_DAYS = 90`.

---

## New Module Structure

```
quirk/
├── qramm/
│   ├── __init__.py          # status_report(db_path, format) function + __all__
│   ├── questions.py         # QRAMM_QUESTIONS: List[dict] -- 120 question definitions
│   │                        # (question_number, dimension, practice, stream, text, scale_labels)
│   ├── evidence_bridge.py   # derive_answers(endpoints: List[CryptoEndpoint]) -> List[AnswerHint]
│   ├── scoring.py           # score_session(session_id, db_path) -> DimensionScores
│   │                        # applies profile multiplier, produces per-dimension weighted scores
│   └── staleness.py         # QRAMM_VERSION, QRAMM_SOURCE_URL, STALENESS_THRESHOLD_DAYS=90
│                            # check_staleness(last_verified: str) -> bool
├── compliance/
│   └── __init__.py          # EXTEND: add _soc2(), _iso(), new COMPLIANCE_MAP entries
├── models.py                # EXTEND: append QRAMMSession, QRAMMAnswer, QRAMMProfile classes
├── db.py                    # EXTEND: add _ensure_qramm_tables() call in init_db()
└── dashboard/api/routes/
    └── qramm.py             # NEW: FastAPI CRUD endpoints for QRAMM lifecycle
```

React additions:

```
src/dashboard/src/
├── pages/
│   └── qramm.tsx            # Main QRAMM page (org profile wizard + dimension tabs)
├── components/qramm/
│   ├── OrgProfileForm.tsx   # Industry/size/geo/sensitivity form -> POST profile
│   ├── DimensionTabs.tsx    # CVI / SGRM / DPE / ITR tab layout
│   ├── QuestionCard.tsx     # Single question: text + radio 1-4 + evidence note
│   ├── ProgressTracker.tsx  # "X of 120 answered" progress bar
│   ├── RadarChart.tsx       # Recharts RadarChart -- 4-axis dimension scores
│   └── ScorecardTable.tsx   # Dimension summary: Raw / Weighted / Benchmark / Level
└── types/
    └── qramm.ts             # TypeScript interfaces mirroring Pydantic schemas
```

---

## Data Flow

### QRAMM Assessment Creation Flow

```
User opens QRAMM page (React)
    |
    ├── Step 1: Org Profile form
    |     POST /api/qramm/profiles  ->  { id, multiplier }
    |
    ├── Step 2: Create session
    |     POST /api/qramm/sessions  { org_profile_id }
    |           |
    |           ├── INSERT qramm_sessions (status=in_progress)
    |           ├── fetch latest CryptoEndpoint rows from crypto_endpoints
    |           ├── call evidence_bridge.derive_answers(endpoints)
    |           └── bulk INSERT qramm_answers (auto_populated=True for derived)
    |                -> returns { session_id, auto_populated_count }
    |
    ├── Step 3: Dimension tabs -- question-by-question
    |     GET /api/qramm/sessions/{id}/answers  -> all 120 answers (with auto_populated flag)
    |     PATCH /api/qramm/sessions/{id}/answers/{q_num}  { answer, evidence_note }
    |           -> UPDATE qramm_answers, auto_populated=False (user overrode)
    |
    └── Step 4: Score and view scorecard
          POST /api/qramm/sessions/{id}/score
                -> calls scoring.score_session() with profile multiplier
                -> UPDATE qramm_sessions (score_cvi, score_sgrm, score_dpe, score_itr, status=complete)
                -> returns DimensionScores response
```

### Evidence Bridge Internal Flow

```
derive_answers(endpoints: List[CryptoEndpoint]) -> List[AnswerHint]:
    
    # CVI-1.1: Automated discovery check
    # Any endpoints present = automated scan ran
    if len(endpoints) > 0:
        yield AnswerHint(question=CVI_1_1, answer=3,
            note=f"QUIRK discovered {len(endpoints)} endpoints via automated scanner")
    
    # CVI-1.2: Vulnerability assessment
    # Presence of severity-classified endpoints with quantum-safety labels
    quantum_vulnerable = [ep for ep in endpoints
                          if ep.cert_pubkey_alg and "RSA" in ep.cert_pubkey_alg]
    if quantum_vulnerable:
        yield AnswerHint(question=CVI_1_2, answer=3,
            note=f"NIST PQC-classified findings: {len(quantum_vulnerable)} RSA endpoints")
    
    # DPE-1.1: Encryption implementation evidence
    tls13_eps = [ep for ep in endpoints if ep.tls_version == "TLSv1.3"]
    tls_eps = [ep for ep in endpoints if ep.tls_version]
    if tls_eps and len(tls13_eps) / len(tls_eps) > 0.5:
        yield AnswerHint(question=DPE_1_1, answer=3,
            note=f"TLS 1.3 on {len(tls13_eps)}/{len(tls_eps)} TLS endpoints")
    
    # ITR-1.1: TLS coverage rate as evidence note (answer requires human judgment)
    total = len(endpoints)
    tls_covered = len([ep for ep in endpoints if ep.tls_version])
    if total > 0:
        coverage_pct = tls_covered / total * 100
        yield AnswerHint(question=ITR_1_1, answer=None,  # no auto-answer
            note=f"{coverage_pct:.0f}% TLS coverage across {total} scanned endpoints")
```

**Critical design choice on risk_engine import:** `evidence_bridge.py` must NOT import `risk_engine.py`. Risk engine imports `quirk.compliance`, and if compliance were to import `quirk.qramm.evidence_bridge`, the cycle would be: `risk_engine -> compliance -> qramm -> evidence_bridge -> risk_engine`. The bridge reads raw `CryptoEndpoint` fields directly. This is the correct pattern — the bridge is a lightweight field-level inspector, not a finding derivation engine.

---

## FastAPI Route Design

```python
# quirk/dashboard/api/routes/qramm.py

router = APIRouter(prefix="/qramm", tags=["qramm"])

# Profiles
POST   /api/qramm/profiles                     # create org profile, compute multiplier
GET    /api/qramm/profiles/{id}                # fetch profile

# Sessions
POST   /api/qramm/sessions                     # create session + run evidence bridge
GET    /api/qramm/sessions                     # list sessions (id, created_at, status, scores)
GET    /api/qramm/sessions/{id}                # session detail + cached scores
DELETE /api/qramm/sessions/{id}                # delete session + cascade answers

# Answers
GET    /api/qramm/sessions/{id}/answers        # all 120 answers for session
PATCH  /api/qramm/sessions/{id}/answers/{q}   # update single answer

# Scoring
POST   /api/qramm/sessions/{id}/score          # compute/recompute dimension scores

# Status (for `quirk qramm status` CLI and dashboard health panel)
GET    /api/qramm/status                       # QRAMM version, staleness, session count
```

Register in `app.py`:
```python
from quirk.dashboard.api.routes import health, pdf, scan, trends, qramm
application.include_router(qramm.router, prefix="/api")
```

---

## Phase Build Order and Parallelism

```
Phase A: Data Model + Backend API (BACK-68)          <- MUST BE FIRST (no deps)
    Creates: QRAMMSession, QRAMMAnswer, QRAMMProfile ORM classes in models.py
    Creates: _ensure_qramm_tables() in db.py
    Creates: /api/qramm/* CRUD routes in routes/qramm.py
    Creates: quirk/qramm/__init__.py, questions.py, scoring.py, staleness.py
    Creates: Pydantic schemas in schemas.py
    No frontend required. No other phases block on it at start.

Phase B: SOC2/ISO27001 Compliance Map (COMPLY-11)    <- parallel with A
    Extends: quirk/compliance/__init__.py (_soc2, _iso, new COMPLIANCE_MAP entries)
    No new tables, no frontend. Zero deps on Phase A.

Phase C: CBOM FIPS Annotations (COMPLY-10)           <- parallel with A, B
    Extends: quirk/cbom/classifier.py (_fips_status_for_algorithm function)
    Extends: quirk/cbom/builder.py Pass-1 loop (Property attachment)
    No new tables, no frontend. Zero deps on Phase A or B.

Phase D: `quirk doctor` CLI (DOCS-05)               <- parallel with A, B, C
    Extends: run_scan.py with `doctor` subcommand block
    Light dep on Phase A: doctor checks QRAMM table existence
    but can degrade gracefully (try inspector.get_table_names()) if tables absent.
    Effectively zero hard dep — can land same time as A or after.

--- Phase A must complete before these can start ---

Phase E: QRAMM Evidence Bridge (BACK-71)            <- depends on A
    Creates: quirk/qramm/evidence_bridge.py
    Wires: POST /api/qramm/sessions to call bridge at creation
    No new tables, no frontend.

--- Phases A and E must complete before these ---

Phase F: QRAMM Assessment UI + Scorecard            <- depends on A, E
         (BACK-69 + BACK-70, combine into one phase)
    Creates: src/dashboard/src/pages/qramm.tsx
    Creates: OrgProfileForm, DimensionTabs, QuestionCard, ProgressTracker
    Creates: RadarChart, ScorecardTable
    Adds: sidebar nav item, /qramm route in App.tsx

--- Phases B and F must complete before this ---

Phase G: QRAMM Compliance Mapping View (BACK-72)   <- depends on B, F
    Extends: qramm.tsx or new compliance-mapping sub-page
    Maps: QRAMM practice scores -> 8 framework coverage table

--- Phase F (minimum) must complete before this ---

Phase H: QRAMM Report Export + Staleness CI Gate   <- depends on F, G
         (BACK-73 + staleness enforcement)
    Extends: quirk/reports/ -- combined governance + technical PDF
    Extends: CI workflow with 90-day QRAMM staleness gate
    Extends: run_scan.py with `quirk qramm status` subcommand block
```

**Recommended milestone phase numbering:**

| Phase | Contents | Depends On |
|-------|----------|------------|
| 51 | BACK-68: Data Model + Backend API | none (first) |
| 52 | COMPLY-10 + COMPLY-11 + DOCS-05 | none (can parallel 51) |
| 53 | BACK-71: Evidence Bridge | 51 |
| 54 | BACK-69 + BACK-70: Assessment UI + Scorecard | 51, 53 |
| 55 | BACK-72: Compliance Mapping View | 52, 54 |
| 56 | BACK-73: Report Export + Staleness CI Gate + `quirk qramm status` | 54, 55 |

Phases 51 and 52 can execute in parallel if there are two engineers. In a single-engineer flow, 52 before 53 is fine since 52 has zero DB/API deps.

---

## Component Boundaries

| Component | Responsibility | Communicates With | Modified or New |
|-----------|---------------|------------------|-----------------|
| `quirk/qramm/__init__.py` | `status_report()` CLI function for session staleness | `qramm_sessions` table via SQLAlchemy | NEW |
| `quirk/qramm/questions.py` | Static 120-question catalog (`QRAMM_QUESTIONS`) | No runtime deps | NEW |
| `quirk/qramm/evidence_bridge.py` | Derive answers from `CryptoEndpoint` rows | `quirk/models.py` only | NEW |
| `quirk/qramm/scoring.py` | Compute weighted dimension scores with profile multiplier | `qramm_sessions`, `qramm_answers`, `qramm_profiles` | NEW |
| `quirk/qramm/staleness.py` | Constants and `check_staleness()` | No runtime deps | NEW |
| `quirk/models.py` | ORM class definitions | SQLAlchemy `Base` | MODIFIED — append 3 new classes |
| `quirk/db.py` | DB init and migration | `quirk/models.py` | MODIFIED — append `_ensure_qramm_tables()` |
| `quirk/compliance/__init__.py` | `COMPLIANCE_MAP` + `status_report()` | Static only | MODIFIED — add `_soc2()`, `_iso()`, new entries |
| `quirk/cbom/builder.py` | CBOM construction (3 passes) | `quirk/cbom/classifier.py` | MODIFIED — add FIPS Property in Pass-1 loop |
| `quirk/cbom/classifier.py` | Algorithm lookup table + classification helpers | cyclonedx-python-lib | MODIFIED — add `_fips_status_for_algorithm()` |
| `quirk/dashboard/api/routes/qramm.py` | FastAPI CRUD for QRAMM lifecycle | `qramm.*` modules, `quirk/db.py` | NEW |
| `quirk/dashboard/api/app.py` | FastAPI app factory | All route modules | MODIFIED — register `qramm.router` |
| `quirk/dashboard/api/schemas.py` | Pydantic response models | None (pure schema) | MODIFIED — add QRAMM response models |
| `run_scan.py` | CLI entry point and subcommand dispatch | All `quirk.*` modules | MODIFIED — add `qramm` and `doctor` subcommand blocks |
| `src/dashboard/src/pages/qramm.tsx` | QRAMM assessment wizard page | `/api/qramm/*` endpoints | NEW |
| `src/dashboard/src/components/qramm/` | Org profile form, dimension tabs, question cards, scorecard, radar | `qramm.tsx` | NEW |
| `src/dashboard/src/App.tsx` | React Router + sidebar registration | All pages | MODIFIED — add `/qramm` route and sidebar item |

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Storing Pre-computed Findings in a `qramm_findings` Table

**What people do:** Create a separate findings table for QRAMM that duplicates the derivation logic already in `routes/scan.py _derive_findings()`, creating two sources of truth.

**Why it's wrong:** `_derive_findings()` is the authoritative derivation path. A duplicate findings table drifts the moment any finding logic changes. Two sources of truth create audit confusion for a compliance deliverable.

**Do this instead:** Evidence bridge reads `CryptoEndpoint` raw fields directly (same data source as `_derive_findings()`). QRAMM answers reference scanner evidence by description string in `evidence_note`, not by FK to a findings row.

### Anti-Pattern 2: Importing `risk_engine.evaluate_endpoints()` from `evidence_bridge.py`

**What people do:** Call the existing risk engine from the evidence bridge to reuse finding logic.

**Why it's wrong:** Creates a potential circular import: `risk_engine -> compliance -> qramm -> evidence_bridge -> risk_engine`. Also pulls the heavy risk engine into a module that only needs a few field-level checks.

**Do this instead:** `evidence_bridge.py` reads `CryptoEndpoint` field values directly (`ep.tls_version`, `ep.protocol`, `ep.cert_pubkey_alg`). Duplicate a small subset of logic rather than creating the import dependency.

### Anti-Pattern 3: A 4th CBOM Annotation Pass

**What people do:** Add a separate post-processing pass to attach FIPS annotations to all algorithm components.

**Why it's wrong:** Pass 1 already has `algo_name` and `nist_level` in scope. A 4th pass iterates the component set twice for a property computable without re-iteration.

**Do this instead:** Add FIPS `Property` objects in Pass 1, where `algo_name` and `nist_level` are already bound. One loop, one responsibility.

### Anti-Pattern 4: Extending `quirk compliance status` to Include QRAMM Staleness

**What people do:** Add QRAMM session staleness output to the existing `quirk compliance status` command.

**Why it's wrong:** `quirk compliance status` is currently DB-free. Adding QRAMM staleness forces a `--db` flag and SQLAlchemy session onto a previously zero-dependency command.

**Do this instead:** `quirk qramm status --db ./quirk.db` is a separate subcommand. `quirk doctor` is the aggregate that calls both.

### Anti-Pattern 5: Storing QRAMM Questions in the Database

**What people do:** Insert 120 rows of question text into a `qramm_question_definitions` table.

**Why it's wrong:** Questions are framework-versioned content, not user data. DB storage forces schema migrations on QRAMM framework version bumps. Adds JOIN complexity to every answer query.

**Do this instead:** `quirk/qramm/questions.py` with a module-level `QRAMM_QUESTIONS: List[dict]` constant. The DB stores only `question_number` as an integer. Question text is resolved at runtime from the module constant. Identical to the `COMPLIANCE_MAP` pattern.

---

## Integration Points

### Existing Systems Requiring No Change

- `quirk/engine/risk_engine.py` — QRAMM adds no new finding categories; `_build_finding()` chokepoint and `_normalize_for_compliance()` operate only on findings, no QRAMM coupling needed.
- `quirk/intelligence/scoring.py` — QRAMM score is separate from the 6-subscore quantum-readiness score; no coupling.
- `quirk/reports/` — Report export (Phase H / BACK-73) adds a new report template or extends the existing HTML/PDF renderer; the existing `writer.py` is not modified until Phase H.
- `cyclonedx-python-lib` — `Component.properties` (`Set[Property]`) is already in the CycloneDX 1.6 SDK in the current pinned version (`>=11.7.0,<12`). No version bump needed for FIPS annotation.

### Existing Systems Requiring Modification

- `quirk/models.py`: append 3 ORM classes (additive, non-breaking).
- `quirk/db.py`: append `_ensure_qramm_tables()` to `init_db()` (additive).
- `quirk/dashboard/api/app.py`: import and register `qramm.router` (additive).
- `quirk/dashboard/api/schemas.py`: append QRAMM Pydantic models (additive).
- `run_scan.py`: append `qramm` and `doctor` subcommand blocks (additive).
- `src/dashboard/src/App.tsx`: add `/qramm` route and sidebar entry (additive).

All modifications are strictly additive. No existing interfaces change. No existing tests require modification as a precondition for Phase A.

---

## Sources

- `quirk/models.py` — confirmed CryptoEndpoint ORM structure and ALTER TABLE migration pattern
- `quirk/db.py` — confirmed `_ensure_*_columns()` chain pattern in `init_db()`
- `quirk/compliance/__init__.py` — confirmed COMPLIANCE_MAP structure, `_pci()/_hipaa()/_fips()` helper pattern, `status_report()` design, `STALENESS_THRESHOLD_DAYS = 365`
- `quirk/dashboard/api/app.py` — confirmed route registration pattern
- `quirk/dashboard/api/routes/scan.py` — confirmed `_derive_findings()` at-query-time derivation, `SESSION_BRACKET = timedelta(minutes=5)` design for scan window
- `quirk/dashboard/api/schemas.py` — confirmed Pydantic schema shape for new QRAMM schemas to follow
- `quirk/cbom/builder.py` — confirmed 3-pass structure, module-level constants pattern
- `quirk/cbom/classifier.py` — confirmed `quantum_safety_label()` location as the right home for `_fips_status_for_algorithm()`
- `run_scan.py` (lines 223-244) — confirmed CLI subcommand dispatch pattern for `qramm` and `doctor` additions
- `src/dashboard/src/App.tsx` — confirmed React Router pattern and existing page list
- `pyproject.toml` — confirmed `cyclonedx-python-lib[json-validation]>=11.7.0,<12` is pinned; `Component.properties` available
- `.planning/ROADMAP.md` BACK-68 through BACK-73 — confirmed QRAMM scope definitions and dimension structure
- `.planning/PROJECT.md` — confirmed v4.7 milestone targets, architectural decisions log, and constraint that all modifications must be additive (no breaking schema migrations)

---
*Architecture research for: QU.I.R.K. v4.7 Governance & Compliance Platform*
*Researched: 2026-05-05*
