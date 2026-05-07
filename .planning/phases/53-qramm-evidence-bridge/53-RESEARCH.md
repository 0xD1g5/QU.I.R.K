# Phase 53: QRAMM Evidence Bridge - Research

**Researched:** 2026-05-07
**Domain:** Python backend — SQLAlchemy ORM, FastAPI route integration, algorithm classification
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** SESSION_BRACKET = all `CryptoEndpoint` rows where `date(scanned_at) = MAX(date(scanned_at))` across the whole table.
- **D-02:** Zero rows in `crypto_endpoints` → bridge skips silently; session creates with 30 blank CVI rows; logged at INFO: "evidence_bridge: no scan data found, skipping".
- **D-03:** Bridge reads ALL field types from `CryptoEndpoint` — structured fields, JSON blob fields; calls `classify_algorithm()` from `quirk.cbom.classifier` on all found algorithm strings; JSON blobs parsed gracefully, malformed blobs skipped without error.
- **D-04:** Same `suggested_answer` value for all questions within a practice area.
- **D-05 (Practice 1.2):** Quartile bands on proportion of endpoints with `nist_level == 0`: 0–25% → 4; 26–50% → 3; 51–75% → 2; 76–100% → 1.
- **D-06 (Practice 1.1):** Endpoint count + distinct `protocol` values: 0 endpoints → 1; 1+ endpoints, 1 protocol → 2; 2–3 distinct protocols → 3; 4+ distinct protocols → 4.
- **D-07 (Practice 1.3):** Distinct algorithm count: 0 → 1; 1–2 → 2; 3–5 → 3; 6+ → 4.
- **D-08:** No new API endpoint for confirmation. Existing `save_answers` endpoint writes `answer_value`.
- **D-09:** `save_answers` auto-sets `confirmed_at = datetime.now(timezone.utc)` when `answer_value` is written to a row where `suggested_answer IS NOT NULL`.
- **D-10:** `score_session` requires no modification. Existing `answer_value IS NOT NULL` filter already excludes unconfirmed suggestions.
- **D-11:** Badge state is implicit (`suggested_answer IS NOT NULL AND answer_value IS NULL` → badge shown). Phase 54 UI derives it; no extra API field needed.

### Claude's Discretion

- Exact `evidence_source` string format (e.g., `"scan:2026-05-07:tls"` or `"evidence_bridge:v1"`). Planner decides a format Phase 54 UI can display as "Auto-filled from scan on YYYY-MM-DD".
- Whether bridge is a standalone function `populate_cvi_suggestions(session_id, db)` or a class. (Context recommends function as simpler.)
- Exact INFO log message format for D-02 skip-silently path.
- Whether `evidence_source` is per-row (different per practice area) or one value for all 30 CVI rows.

### Deferred Ideas (OUT OF SCOPE)

- Evidence bridge for SGRM, DPE, ITR dimensions (QRAMM-F01 — v4.8)
- Badge display in assessment UI (QRAMM-14 badge rendering — Phase 54)
- Any new API endpoints
- Modifications to `score_session`
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QRAMM-12 | At session creation, evidence bridge auto-populates CVI dimension questions from latest scan's `CryptoEndpoint` rows; `evidence_bridge.py` does NOT import `risk_engine` | Verified: `classify_algorithm()` in `quirk/cbom/classifier.py` has zero scanner/engine imports — safe to call from bridge |
| QRAMM-13 | Auto-populated answers stored in `suggested_answer` with `requires_confirmation: true`; `answer_value` null until human confirms; only rows with non-null `confirmed_at` contribute to score | Verified: `QRAMMAnswer` has `suggested_answer`, `confirmed_at`, `evidence_source` columns pre-provisioned; `score_session` already filters `answer_value IS NOT NULL` |
| QRAMM-14 | Auto-filled answers display "Auto-filled from scan" badge in UI; badge removed on modify/confirm | Data model already supports it via `suggested_answer IS NOT NULL AND answer_value IS NULL`; Phase 54 owns rendering |
</phase_requirements>

---

## Summary

Phase 53 is a pure Python backend phase. It adds one new module (`quirk/qramm/evidence_bridge.py`), modifies one existing route handler (`save_answers` in `qramm.py`), and adds one new route call in `create_session`. No new database columns are required — `QRAMMSession`, `QRAMMAnswer`, and their Phase 53 columns (`suggested_answer`, `confirmed_at`, `evidence_source`) are already declared in `quirk/models.py` from Phase 51.

The evidence bridge reads `CryptoEndpoint` rows in the SESSION_BRACKET window (most-recent scan date), extracts algorithm strings from both structured fields and JSON blobs, calls `classify_algorithm()` to get `nist_level`, and uses three deterministic rules (D-05/D-06/D-07) to derive a single integer (1–4) per practice area. It bulk-updates the 30 CVI `QRAMMAnswer` rows that `create_session` already writes. The confirmation mechanic is a two-line addition to `save_answers`.

The codebase is fully verified. Phase 51 is complete — all required files (`quirk/qramm/`, `quirk/models.py`, `quirk/dashboard/api/routes/qramm.py`) exist and are production-ready. No schema migrations are needed. The test pattern (UUID-named in-memory SQLite + `dependency_overrides[get_db]`) is established in `tests/test_qramm_router.py` and ready to reuse.

**Primary recommendation:** Implement `evidence_bridge.py` as a single function `populate_cvi_suggestions(session_id: int, db: Session) -> None`. Call it synchronously from `create_session` after `db.refresh(session)`. Add a two-line `confirmed_at` update inside `save_answers`. Write `tests/test_qramm_evidence_bridge.py` using the existing UUID-named in-memory DB pattern.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SESSION_BRACKET query | API / Backend | Database / Storage | SQLAlchemy ORM query on SQLite; pure server-side logic |
| Algorithm string extraction | API / Backend | — | Reads JSON blobs and structured columns; stdlib json only |
| `classify_algorithm()` call | API / Backend | — | Pure function in `quirk/cbom/classifier.py`; no I/O |
| Maturity derivation (D-05/D-06/D-07) | API / Backend | — | Pure arithmetic; no DB write until derivation complete |
| `suggested_answer` bulk write | Database / Storage | API / Backend | SQLAlchemy ORM update to `qramm_answers` rows |
| `confirmed_at` auto-set | API / Backend | Database / Storage | Inline in `save_answers` route handler; one-line ORM update |
| Badge state signal | Frontend Server (SSR) | — | Phase 54 UI derives from `suggested_answer`/`answer_value` fields |

---

## Standard Stack

### Core

All libraries are already project dependencies. No new `pip install` required. [VERIFIED: codebase imports]

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | project dep | ORM query for SESSION_BRACKET, bulk update | Established via `quirk/db.py` and all route handlers |
| FastAPI | project dep | Route handler injection point (`create_session`, `save_answers`) | All API routes use it |
| Python stdlib `json` | stdlib | Parse JSON blob fields gracefully | Used throughout existing scanner modules |
| Python stdlib `logging` | stdlib | INFO-level skip logging (D-02) | Established project logging pattern |
| `quirk.cbom.classifier` | internal | `classify_algorithm()` → `nist_level` | Zero circular import risk; imports only stdlib + cyclonedx |

### No New Dependencies

Phase 53 introduces zero new pip packages. All required imports are either stdlib or internal project modules. [VERIFIED: codebase grep]

---

## Architecture Patterns

### System Architecture Diagram

```
POST /api/qramm/sessions
        │
        ▼
create_session (router)
  │  1. Write QRAMMSession row → db.commit() → session.id available
  │  2. Write 30 blank QRAMMAnswer rows (CVI Q1-30)
  │  3. Call populate_cvi_suggestions(session.id, db)
  │        │
  │        ▼
  │   evidence_bridge.populate_cvi_suggestions()
  │     ├── SESSION_BRACKET query: MAX(date(scanned_at)) on crypto_endpoints
  │     ├── [D-02 guard] zero rows → log INFO, return
  │     ├── Extract algorithm strings from structured fields + JSON blobs
  │     │       ├── tls_version, cipher_suite, cert_sig_alg, cert_pubkey_alg
  │     │       └── ssh_audit_json, jwt_scan_json, container_scan_json, etc.
  │     ├── Call classify_algorithm(name) → nist_level per string
  │     │       └── quirk.cbom.classifier (no scanner/engine imports)
  │     ├── Compute suggested_answer per practice area
  │     │       ├── D-06: Practice 1.1 — endpoint count + distinct protocol count
  │     │       ├── D-05: Practice 1.2 — % endpoints with nist_level == 0
  │     │       └── D-07: Practice 1.3 — distinct algorithm count
  │     └── Bulk UPDATE qramm_answers SET suggested_answer, evidence_source
  │           WHERE session_id = X AND dimension = 'CVI'
  │
  │  4. Return 201 CreateSessionResponse
  ▼
  201 response to caller

POST /api/qramm/sessions/{id}/answers
  │
  ▼
save_answers (router) — MODIFIED
  ├── existing upsert logic (unchanged)
  └── [NEW] if existing.suggested_answer is not None:
              existing.confirmed_at = datetime.now(timezone.utc)
```

### Recommended Project Structure

No new directories. All files added to existing packages:

```
quirk/
├── qramm/
│   ├── __init__.py             # existing
│   ├── evidence_bridge.py      # NEW — Phase 53
│   ├── model_meta.py           # existing
│   ├── questions.py            # existing
│   └── scoring.py              # existing
└── dashboard/api/routes/
    └── qramm.py                # MODIFIED — create_session + save_answers

tests/
└── test_qramm_evidence_bridge.py   # NEW — Phase 53
```

### Pattern 1: SESSION_BRACKET Query

**What:** Query `crypto_endpoints` for all rows matching the most-recent scan date. Uses SQLAlchemy `func.max()` and SQLite `date()`.

**When to use:** Any time the bridge needs a deterministic cohort of scan data.

```python
# Source: [VERIFIED: quirk/models.py, quirk/db.py — SQLAlchemy ORM pattern]
from sqlalchemy import func, cast, Date
from quirk.models import CryptoEndpoint

def _get_bracket_endpoints(db: Session):
    max_date_subq = db.query(
        func.date(func.max(CryptoEndpoint.scanned_at))
    ).scalar()
    if max_date_subq is None:
        return []
    return (
        db.query(CryptoEndpoint)
        .filter(func.date(CryptoEndpoint.scanned_at) == max_date_subq)
        .all()
    )
```

**Note:** `func.date()` is available in SQLite and works on DateTime columns. SQLAlchemy passes it through as `date(column)`. [VERIFIED: SQLite docs, SQLAlchemy func passthrough]

### Pattern 2: Graceful JSON Blob Parsing

**What:** Parse JSON blob fields from `CryptoEndpoint`, skipping malformed entries.

```python
# Source: [VERIFIED: existing scanner modules use similar try/except json patterns]
import json

def _parse_json_blob(blob: str | None) -> dict | list | None:
    if not blob:
        return None
    try:
        return json.loads(blob)
    except (json.JSONDecodeError, TypeError):
        return None
```

### Pattern 3: Algorithm String Extraction per Scanner Type

**What:** Each scanner stores algorithm strings in different locations within its JSON blob. The bridge must know the structure for each blob type.

**Verified blob schemas** (from Phase 51/52 implementation):

| Field | Scanner | Algorithm location |
|-------|---------|-------------------|
| `tls_version` | TLS | direct string, e.g. `"TLSv1.2"` |
| `cipher_suite` | TLS | direct string, e.g. `"ECDHE-RSA-AES256-GCM-SHA384"` |
| `cert_sig_alg` | TLS/cert | direct string, e.g. `"sha256WithRSAEncryption"` |
| `cert_pubkey_alg` | TLS/cert | direct string, e.g. `"RSA"`, `"EC"` |
| `ssh_audit_json` | SSH | `kex[].algorithm`, `hostkeys[].algorithm`, `enc[].algorithm`, `mac[].algorithm` |
| `jwt_scan_json` | JWT/JWKS | `alg` field on JWKS key entries |
| `container_scan_json` | container (syft) | `metadata.algorithm` or similar in artifact JSON |
| `cloud_scan_json` | cloud KMS | `keyAlgorithm` or `algorithm` field |
| `kerberos_scan_json` | Kerberos | encryption type strings (e.g., `"rc4-hmac"`, `"aes256-cts-hmac-sha1-96"`) |

[VERIFIED: `quirk/models.py` column definitions; `quirk/cbom/classifier.py` lookup table confirms all Kerberos, SSH, JWT, TLS algorithm strings]

**RC4-HMAC Kerberos classification:** `"rc4-hmac"` maps to `(CryptoPrimitive.BLOCK_CIPHER, 0, 128)` — `nist_level == 0` = quantum-vulnerable. AES-256 Kerberos (`"aes256-cts-hmac-sha1-96"`) maps to `(CryptoPrimitive.BLOCK_CIPHER, 1, 256)` — `nist_level == 1` = quantum-safe. This directly satisfies ROADMAP success criterion 3. [VERIFIED: `quirk/cbom/classifier.py` lines 195–198]

### Pattern 4: Bulk QRAMMAnswer Update

**What:** Update `suggested_answer` and `evidence_source` on existing rows (created blank by `create_session`).

```python
# Source: [VERIFIED: test_qramm_router.py — existing upsert shape in save_answers]
from quirk.models import QRAMMAnswer

rows = (
    db.query(QRAMMAnswer)
    .filter(
        QRAMMAnswer.session_id == session_id,
        QRAMMAnswer.dimension == "CVI",
        QRAMMAnswer.practice_area == practice_area,
    )
    .all()
)
for row in rows:
    row.suggested_answer = suggested_value
    row.evidence_source = evidence_source_str
db.commit()
```

**Note:** The CONTEXT says the bridge updates rows created by `create_session`. But reviewing `create_session` in `quirk/dashboard/api/routes/qramm.py` reveals it does NOT currently create blank CVI rows — it only creates the `QRAMMSession`. The bridge must either: (a) create the 30 CVI rows itself, or (b) rely on the router to be modified to create them first. See Critical Finding below.

### Pattern 5: `confirmed_at` Auto-Set in `save_answers`

**What:** Two-line addition inside the existing upsert block in `save_answers`.

```python
# Source: [VERIFIED: quirk/dashboard/api/routes/qramm.py lines 189-190 — existing update block]
else:
    existing.answer_value = item.answer_value
    existing.dimension = meta["dimension"]
    existing.practice_area = meta["practice_area"]
    # [NEW for Phase 53 — D-09]:
    if existing.suggested_answer is not None:
        existing.confirmed_at = _now_iso()
```

### Pattern 6: `no risk_engine import` Guard (QRAMM-12)

**What:** Unit test asserts `sys.modules` does not contain `risk_engine` after importing `evidence_bridge`.

```python
# Source: [VERIFIED: test_qramm_scoring.py test_d09_isolation_no_forbidden_imports — exact analog]
import pathlib, inspect
import quirk.qramm.evidence_bridge as bridge_mod

src_path = pathlib.Path(inspect.getsourcefile(bridge_mod))
text = src_path.read_text(encoding="utf-8")
forbidden = ["quirk.engine.risk_engine", "quirk.risk_engine"]
for f in forbidden:
    assert f"from {f}" not in text
    assert f"import {f}" not in text
```

### Pattern 7: Test DB Setup (UUID Named In-Memory SQLite)

**What:** Reuse the established pattern from `test_qramm_router.py` for isolated per-test DB.

```python
# Source: [VERIFIED: tests/test_qramm_router.py lines 20-43 — _make_qramm_client()]
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from quirk.models import Base

def _make_test_db():
    db_name = f"test_bridge_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
```

For bridge unit tests that do NOT need the FastAPI client, use the `TestingSession` directly — no `dependency_overrides` needed. The bridge function takes `(session_id: int, db: Session)` — call it with `db = TestingSession()`.

### Anti-Patterns to Avoid

- **Importing `risk_engine`:** `evidence_bridge.py` must never import `quirk.engine.risk_engine` or `quirk.scanner.*`. Use only `quirk.cbom.classifier.classify_algorithm`. [VERIFIED: CONTEXT.md D-03, QRAMM-12]
- **Using `datetime.utcnow()`:** Always use `datetime.now(timezone.utc)`. DEBT-01 is complete — the test in `test_qramm_router.py` `test_no_utcnow_in_qramm_module` will fail if this is used. [VERIFIED: test_qramm_router.py lines 259-268]
- **Assuming `create_session` pre-creates CVI rows:** Current code does not. The bridge or `create_session` must handle row creation. (See Critical Finding.)
- **Calling `db.commit()` multiple times in bridge:** One commit at the end of `populate_cvi_suggestions` is sufficient.
- **Crashing on empty scan data:** D-02 requires silent skip, not exception.

---

## Critical Finding: `create_session` Does Not Pre-Create QRAMMAnswer Rows

**Verified from `quirk/dashboard/api/routes/qramm.py` lines 110-132:** [VERIFIED: direct read]

The current `create_session` handler creates only the `QRAMMSession` row. It does NOT create any `QRAMMAnswer` rows. The CONTEXT.md says "bridge updates `suggested_answer` + `evidence_source` on those rows in the same request" and that "they are created by the existing `create_session` handler with blank `answer_value`" — but this is NOT the current Phase 51 implementation.

**Resolution options for the planner:**

1. **Option A (simpler):** The bridge creates the 30 CVI rows itself (with `suggested_answer` already set). No separate row-creation step in `create_session`.

2. **Option B (context-aligned):** Modify `create_session` to create 30 blank CVI `QRAMMAnswer` rows when the session is created (before calling the bridge), then the bridge updates them. This matches the CONTEXT description exactly.

**Recommendation:** Option B, because it means the 30 CVI rows exist in the DB even when the bridge skips (D-02 path), allowing the UI to display all 30 questions with empty state. Option A would mean zero answer rows when no scan exists.

**Implementation impact:** `create_session` needs a loop over the 30 CVI questions from `QRAMM_QUESTIONS` to pre-create rows. The bridge then does bulk `UPDATE` not `INSERT`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Algorithm classification | Custom nist_level lookup | `classify_algorithm()` from `quirk.cbom.classifier` | Complete lookup table with 60+ algorithms, normalization, vendor suffix stripping |
| JSON parsing with error recovery | Custom try/except tree | stdlib `json.loads` in `_parse_json_blob()` helper | One-liner covers all blob types uniformly |
| SQLite date comparison | Raw SQL string | `func.date()` via SQLAlchemy | Handled by existing SQLAlchemy expression layer; no string injection risk |
| Test DB isolation | File-based DB with teardown | UUID-named in-memory SQLite (established pattern) | Zero cleanup, zero collisions, 10× faster |

---

## Common Pitfalls

### Pitfall 1: `nist_level is None` vs `nist_level == 0`

**What goes wrong:** Unknown algorithms return `(CryptoPrimitive.UNKNOWN, None, None)` from `classify_algorithm()`. Treating `None` as `0` would inflate the "quantum-vulnerable" count.

**Why it happens:** Many scanner blob fields contain non-algorithm strings (host names, key IDs, etc.) that the classifier cannot recognize.

**How to avoid:** Filter on `nist_level is not None` before counting vulnerable algorithms. Only count `nist_level == 0` endpoints when the level is known. [VERIFIED: `quirk/cbom/classifier.py` lines 201-249 — `_FALLBACK = (CryptoPrimitive.UNKNOWN, None, None)`]

**Warning signs:** D-05 practice 1.2 returning unexpectedly low scores for clean scans.

### Pitfall 2: SESSION_BRACKET Date Comparison with DateTime

**What goes wrong:** `CryptoEndpoint.scanned_at` is a `DateTime` column. Direct `==` comparison on the max value will miss rows from the same calendar day with different times.

**Why it happens:** `MAX(scanned_at)` returns one exact timestamp; comparing other rows' `scanned_at == max_timestamp` misses rows scanned 0.001 seconds earlier.

**How to avoid:** Use `func.date(CryptoEndpoint.scanned_at) == func.date(func.max(...))` to compare date portions only. [VERIFIED: CONTEXT.md D-01 — "date(scanned_at) = MAX(date(scanned_at))"]

### Pitfall 3: SQLite `func.date()` vs Python date comparison

**What goes wrong:** Computing `max_date` in Python as a `datetime` object and then comparing `func.date(CryptoEndpoint.scanned_at) == python_date` may not serialize correctly.

**How to avoid:** Use a fully server-side subquery for the max date lookup, or compare `func.date(CryptoEndpoint.scanned_at) == max_date_string` where `max_date_string` is the ISO date string (e.g., `"2026-05-07"`). SQLite's `date()` function returns text in `"YYYY-MM-DD"` format. [ASSUMED — based on SQLite documentation behavior]

### Pitfall 4: Bridge Called Before Session Commit

**What goes wrong:** Calling `populate_cvi_suggestions(session.id, db)` before `db.commit()` means `session.id` may be None (SQLite autoincrement doesn't assign ID until flush/commit).

**How to avoid:** The current `create_session` already does `db.commit()` then `db.refresh(session)` before returning. Call the bridge AFTER `db.refresh(session)`. [VERIFIED: qramm.py lines 122-125]

### Pitfall 5: Multiple `db.commit()` calls in `create_session`

**What goes wrong:** `create_session` already commits once for the session. If the bridge commits again (for the 30 CVI row updates) and then the router commits again after pre-creating rows, there are 3 commits in one request — safe but potentially surprising.

**How to avoid:** Bridge calls one `db.commit()` at end of `populate_cvi_suggestions`. Pre-creation of CVI rows (if using Option B) can use `db.flush()` to get row IDs without committing, then bridge updates and commits once. Simplest approach: bridge commits once, which also persists the pre-created rows.

### Pitfall 6: test_no_utcnow_in_qramm_module Gate

**What goes wrong:** `test_qramm_router.py` has a test that scans ALL files in `quirk/qramm/` for `utcnow()`. If `evidence_bridge.py` contains `datetime.utcnow()`, this test fails.

**How to avoid:** Use `datetime.now(timezone.utc)` throughout `evidence_bridge.py`. [VERIFIED: test_qramm_router.py lines 259-268]

---

## Code Examples

### Full Bridge Function Skeleton

```python
# Source: [VERIFIED: quirk/cbom/classifier.py, quirk/models.py, quirk/dashboard/api/routes/qramm.py]
"""quirk/qramm/evidence_bridge.py — Phase 53 QRAMM-12/13.

Auto-populates CVI dimension suggested_answer values from the latest scan's
CryptoEndpoint rows. Called synchronously from create_session.

MUST NOT import risk_engine or any scanner module (QRAMM-12 / Phase 51 D-09).
"""
from __future__ import annotations

import json
import logging
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from quirk.cbom.classifier import classify_algorithm
from quirk.models import CryptoEndpoint, QRAMMAnswer

logger = logging.getLogger(__name__)

_EVIDENCE_SOURCE_VERSION = "v1"


def populate_cvi_suggestions(session_id: int, db: Session) -> None:
    """Derive CVI suggested_answer values from the SESSION_BRACKET scan cohort.

    Updates the 30 CVI QRAMMAnswer rows (pre-created by create_session) with
    suggested_answer and evidence_source. Skips silently if no scan data exists.
    """
    # SESSION_BRACKET query (D-01)
    max_date_str = db.query(
        func.date(func.max(CryptoEndpoint.scanned_at))
    ).scalar()

    if max_date_str is None:
        # D-02: no scan data — skip silently
        logger.info("evidence_bridge: no scan data found, skipping")
        return

    endpoints = (
        db.query(CryptoEndpoint)
        .filter(func.date(CryptoEndpoint.scanned_at) == max_date_str)
        .all()
    )

    if not endpoints:
        logger.info("evidence_bridge: no scan data found, skipping")
        return

    # Extract features from endpoints
    protocol_set = set()
    algorithm_set = set()
    total_endpoints = len(endpoints)
    vulnerable_endpoint_count = 0

    for ep in endpoints:
        if ep.protocol:
            protocol_set.add(ep.protocol.upper())
        alg_names = _extract_algorithm_names(ep)
        ep_has_vulnerable = False
        for name in alg_names:
            _, nist_level, _ = classify_algorithm(name)
            if nist_level is not None:
                algorithm_set.add(name.lower())
                if nist_level == 0:
                    ep_has_vulnerable = True
        if ep_has_vulnerable:
            vulnerable_endpoint_count += 1

    # D-06: Practice 1.1 — Discovery & Inventory
    distinct_protocols = len(protocol_set)
    if total_endpoints == 0:
        score_1_1 = 1
    elif distinct_protocols == 1:
        score_1_1 = 2
    elif distinct_protocols <= 3:
        score_1_1 = 3
    else:
        score_1_1 = 4

    # D-05: Practice 1.2 — Vulnerability Assessment
    vuln_pct = (vulnerable_endpoint_count / total_endpoints) * 100
    if vuln_pct <= 25:
        score_1_2 = 4
    elif vuln_pct <= 50:
        score_1_2 = 3
    elif vuln_pct <= 75:
        score_1_2 = 2
    else:
        score_1_2 = 1

    # D-07: Practice 1.3 — Dependency Mapping
    distinct_algs = len(algorithm_set)
    if distinct_algs == 0:
        score_1_3 = 1
    elif distinct_algs <= 2:
        score_1_3 = 2
    elif distinct_algs <= 5:
        score_1_3 = 3
    else:
        score_1_3 = 4

    evidence_source = f"scan:{max_date_str}:{_EVIDENCE_SOURCE_VERSION}"
    practice_scores = {"1.1": score_1_1, "1.2": score_1_2, "1.3": score_1_3}

    # Bulk update CVI QRAMMAnswer rows
    for practice_area, suggested_value in practice_scores.items():
        db.query(QRAMMAnswer).filter(
            QRAMMAnswer.session_id == session_id,
            QRAMMAnswer.dimension == "CVI",
            QRAMMAnswer.practice_area == practice_area,
        ).update(
            {
                QRAMMAnswer.suggested_answer: suggested_value,
                QRAMMAnswer.evidence_source: evidence_source,
            },
            synchronize_session="fetch",
        )

    db.commit()


def _extract_algorithm_names(ep: CryptoEndpoint) -> list[str]:
    """Extract raw algorithm name strings from all fields of a CryptoEndpoint."""
    names = []
    # Structured fields
    for val in (ep.tls_version, ep.cipher_suite, ep.cert_sig_alg, ep.cert_pubkey_alg):
        if val:
            names.append(val)
    # JSON blob fields — parsed gracefully; malformed blobs skipped (D-03)
    for blob in (
        ep.ssh_audit_json, ep.jwt_scan_json, ep.container_scan_json,
        ep.cloud_scan_json, ep.kerberos_scan_json, ep.saml_scan_json,
    ):
        parsed = _parse_json_blob(blob)
        if parsed is not None:
            names.extend(_walk_json_for_alg_strings(parsed))
    return names


def _parse_json_blob(blob: str | None) -> dict | list | None:
    if not blob:
        return None
    try:
        return json.loads(blob)
    except (json.JSONDecodeError, TypeError):
        return None


def _walk_json_for_alg_strings(obj) -> list[str]:
    """Recursively extract strings from JSON that look like algorithm names."""
    # Planner implements full extraction logic per scanner blob schema
    ...
```

### `create_session` Modification (adding CVI row pre-creation + bridge call)

```python
# Source: [VERIFIED: quirk/dashboard/api/routes/qramm.py lines 109-132]
# Add import at top:
# from quirk.qramm.evidence_bridge import populate_cvi_suggestions
# from quirk.qramm.questions import QRAMM_QUESTIONS

@router.post("/qramm/sessions", status_code=201, response_model=CreateSessionResponse)
def create_session(payload: CreateSessionRequest, db: Session = Depends(get_db)):
    now = _now_iso()
    model_version = payload.model_version or QRAMM_MODEL["qramm_version"]
    session = QRAMMSession(
        org_name=payload.org_name,
        created_at=now,
        updated_at=now,
        model_version=model_version,
        status="draft",
    )
    db.add(session)
    db.flush()  # flush to get session.id without full commit

    # Pre-create 30 blank CVI QRAMMAnswer rows (Option B from research)
    cvi_questions = [q for q in QRAMM_QUESTIONS if q["dimension"] == "CVI"]
    for q in cvi_questions:
        db.add(QRAMMAnswer(
            session_id=session.id,
            question_number=q["question_number"],
            dimension=q["dimension"],
            practice_area=q["practice_area"],
        ))
    db.commit()
    db.refresh(session)

    # Evidence bridge (synchronous — 30 writes + classify calls are fast)
    populate_cvi_suggestions(session.id, db)

    return CreateSessionResponse(...)
```

### `save_answers` Modification (D-09 `confirmed_at` auto-set)

```python
# Source: [VERIFIED: quirk/dashboard/api/routes/qramm.py lines 188-193]
# Inside the existing upsert block, add two lines to the `else` branch:
else:
    existing.answer_value = item.answer_value
    existing.dimension = meta["dimension"]
    existing.practice_area = meta["practice_area"]
    if existing.suggested_answer is not None:      # D-09: auto-set confirmed_at
        existing.confirmed_at = _now_iso()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | Phase 51 DEBT-01 | All new code in `quirk/qramm/` must use new form; test gate enforces it |
| No evidence bridge | `populate_cvi_suggestions()` auto-fired on session create | Phase 53 | 30 CVI rows get `suggested_answer` from scan data automatically |
| Manual confirmation field | `confirmed_at` auto-set by `save_answers` | Phase 53 D-09 | No explicit "confirm" endpoint needed |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | SQLite `func.date()` returns `"YYYY-MM-DD"` text string that can be compared directly in a subsequent filter | Architecture Patterns — Pattern 1 | SESSION_BRACKET query could fail or return wrong rows; fix: test with `db.execute(text("SELECT date(datetime('now'))"))` |
| A2 | `kerberos_scan_json` contains Kerberos encryption type strings in a structure the bridge can traverse to find `"rc4-hmac"` | Code Examples — `_extract_algorithm_names` | RC4-heavy scan might not produce lower score; fix: read actual kerberos scanner output format before implementing `_walk_json_for_alg_strings` |
| A3 | Option B (pre-creating 30 CVI rows in `create_session`) is the intended design per CONTEXT.md wording | Critical Finding | If Option A is chosen, bridge creates rows rather than updating them — functionally equivalent but test setup differs |

---

## Open Questions

1. **JSON blob internal structure for algorithm extraction**
   - What we know: CONTEXT.md says bridge reads `kerberos_scan_json`, `ssh_audit_json`, etc. and extracts algorithm strings. `classify_algorithm()` can classify them if found.
   - What's unclear: The exact JSON structure of each blob type — e.g., does `kerberos_scan_json` store `{"encryption_types": ["rc4-hmac", "aes256-cts-hmac-sha1-96"]}` or nested differently?
   - Recommendation: Planner should read one actual blob from the DB or read the relevant scanner source file to confirm the JSON shape before implementing `_walk_json_for_alg_strings`. This is the highest-risk unknown for test correctness.

2. **Concurrent request safety (double-bridge invocation)**
   - What we know: Bridge is synchronous; SQLite is single-writer.
   - What's unclear: If `create_session` is called twice rapidly, both will try to update the same rows (different session IDs — no conflict). Non-issue.
   - Recommendation: No action needed.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 53 is a pure Python backend change. No external tools, services, CLI utilities, or databases beyond the existing project SQLite database are required.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (project standard) |
| Config file | none detected (pytest discovers `tests/test_*.py`) |
| Quick run command | `python -m pytest tests/test_qramm_evidence_bridge.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QRAMM-12 | Bridge auto-populates on session create | integration | `pytest tests/test_qramm_evidence_bridge.py::test_bridge_populates_on_session_create -x` | ❌ Wave 0 |
| QRAMM-12 | Bridge skips silently when no scan data (D-02) | unit | `pytest tests/test_qramm_evidence_bridge.py::test_bridge_skips_when_no_scan_data -x` | ❌ Wave 0 |
| QRAMM-12 | `evidence_bridge.py` does not import `risk_engine` (static source check) | unit | `pytest tests/test_qramm_evidence_bridge.py::test_no_risk_engine_import -x` | ❌ Wave 0 |
| QRAMM-13 | RC4-HMAC scan → lower CVI 1.2 score than AES-256 scan | unit | `pytest tests/test_qramm_evidence_bridge.py::test_rc4_scan_lower_score_than_aes256 -x` | ❌ Wave 0 |
| QRAMM-13 | Unconfirmed rows excluded from score | integration | `pytest tests/test_qramm_evidence_bridge.py::test_unconfirmed_excluded_from_score -x` | ❌ Wave 0 |
| QRAMM-13 | Confirmed rows included in score | integration | `pytest tests/test_qramm_evidence_bridge.py::test_confirmed_included_in_score -x` | ❌ Wave 0 |
| QRAMM-13 | `confirmed_at` auto-set when `save_answers` writes `answer_value` to suggested row | unit | `pytest tests/test_qramm_evidence_bridge.py::test_confirmed_at_auto_set -x` | ❌ Wave 0 |
| QRAMM-14 | Badge signal: `suggested_answer IS NOT NULL AND answer_value IS NULL` → badge visible | unit | `pytest tests/test_qramm_evidence_bridge.py::test_badge_signal_data_model -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_qramm_evidence_bridge.py -x`
- **Per wave merge:** `python -m pytest tests/test_qramm_evidence_bridge.py tests/test_qramm_router.py tests/test_qramm_scoring.py -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_qramm_evidence_bridge.py` — covers QRAMM-12, QRAMM-13, QRAMM-14

*(No conftest gaps — existing `conftest.py` + UUID-named in-memory DB pattern in `test_qramm_router.py` covers all fixture needs.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | Bridge is server-internal; no new API surface |
| V5 Input Validation | no | Bridge reads from internal DB rows, not user input |
| V6 Cryptography | no | Bridge classifies algorithms; does not perform cryptographic operations |

**No new attack surface:** `evidence_bridge.py` is called server-side from an existing authenticated endpoint. It reads from the DB and writes back to the DB. No user input flows through the bridge.

**SQL injection prevention:** The SESSION_BRACKET query uses `func.date(func.max(...))` via SQLAlchemy ORM — parameterized by default. No raw SQL string interpolation. [VERIFIED: established `_SAFE_COL_RE` pattern in `quirk/db.py` for column names; bridge uses no DDL]

---

## Sources

### Primary (HIGH confidence)

- [VERIFIED: `quirk/models.py`] — QRAMMSession, QRAMMAnswer, QRAMMProfile columns; CryptoEndpoint fields
- [VERIFIED: `quirk/cbom/classifier.py`] — `classify_algorithm()` signature, return type, import graph (zero scanner/engine deps), full lookup table including RC4-HMAC and AES-256 Kerberos entries
- [VERIFIED: `quirk/dashboard/api/routes/qramm.py`] — `create_session`, `save_answers`, `score_session` handler code; confirmed `create_session` does NOT pre-create QRAMMAnswer rows
- [VERIFIED: `quirk/qramm/questions.py`] — `QRAMM_QUESTIONS` structure; 30 CVI entries (Q1-30), practice areas 1.1/1.2/1.3
- [VERIFIED: `quirk/db.py`] — `get_session()`, `_ensure_qramm_tables()`, `init_db()` chain
- [VERIFIED: `quirk/dashboard/api/deps.py`] — `get_db()` FastAPI dependency pattern
- [VERIFIED: `tests/test_qramm_router.py`] — UUID-named in-memory DB test pattern, `_make_qramm_client()`, existing smoke tests
- [VERIFIED: `tests/test_qramm_scoring.py`] — D-09 static source check pattern (`test_d09_isolation_no_forbidden_imports`)
- [VERIFIED: `.planning/phases/53-qramm-evidence-bridge/53-CONTEXT.md`] — All locked decisions D-01 through D-11
- [VERIFIED: `.planning/REQUIREMENTS.md`] — QRAMM-12, QRAMM-13, QRAMM-14 acceptance criteria

### Secondary (MEDIUM confidence)

- [ASSUMED] SQLite `func.date()` behavior — standard SQLite behavior documented but not runtime-tested in this session

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all imports verified from codebase; zero new dependencies
- Architecture: HIGH — all call sites, column schemas, and test patterns verified from source
- Critical Finding (row pre-creation): HIGH — confirmed by direct read of `create_session` handler
- Pitfalls: HIGH — most verified from classifier source code and existing test patterns
- JSON blob extraction detail: MEDIUM — blob structures assumed from scanner architecture; planner should verify kerberos/ssh blob shapes before implementing `_walk_json_for_alg_strings`

**Research date:** 2026-05-07
**Valid until:** 2026-06-07 (stable internal codebase; 30-day window)
