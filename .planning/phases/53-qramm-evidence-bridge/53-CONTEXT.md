---
phase: 53-qramm-evidence-bridge
type: context
status: active
source: /gsd-discuss-phase 53
updated: 2026-05-07
milestone: v4.7 Governance & Compliance Platform
requirements: [QRAMM-12, QRAMM-13, QRAMM-14]
---

# Phase 53: QRAMM Evidence Bridge - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 53 delivers `quirk/qramm/evidence_bridge.py` — a module that fires
automatically when `POST /api/qramm/sessions` creates a new QRAMM assessment
session. It reads the latest scan's `CryptoEndpoint` rows, translates
cryptographic findings into maturity-level suggestions (1–4) for the 30
CVI-dimension questions, and writes `suggested_answer` values to
`qramm_answers` rows. Unconfirmed suggestions do not contribute to the
maturity score until a consultant explicitly confirms them by writing
`answer_value` via the existing `save_answers` endpoint.

**In scope:**
- `quirk/qramm/evidence_bridge.py` — new module: SESSION_BRACKET query,
  maturity derivation rules for CVI practices 1.1 / 1.2 / 1.3, bulk
  `suggested_answer` write to `qramm_answers`
- `quirk/dashboard/api/routes/qramm.py` — call `evidence_bridge.py` from
  `create_session` (synchronous); update `save_answers` to auto-set
  `confirmed_at = now()` when writing `answer_value` to a row that has
  `suggested_answer IS NOT NULL`
- `tests/test_qramm_evidence_bridge.py` — unit tests covering: bridge output
  with RC4-heavy vs AES-256-only scan data; D-02 skip-silently path; no
  `risk_engine` import guard (QRAMM-12 sys.modules check); confirmed_at
  auto-set on save

**Out of scope:**
- Evidence bridge for SGRM, DPE, ITR dimensions (QRAMM-F01 — v4.8)
- Badge display in assessment UI (QRAMM-14 — Phase 54)
- Any new API endpoints (confirmation reuses existing save_answers)
- Modifications to `score_session` (existing `answer_value IS NOT NULL` filter
  already correctly excludes unconfirmed suggestions)

</domain>

<decisions>
## Implementation Decisions

### SESSION_BRACKET Scan Window

- **D-01:** SESSION_BRACKET = all `CryptoEndpoint` rows where
  `date(scanned_at) = MAX(date(scanned_at))` across the whole table.
  Deterministic cohort: uses the most recent scan run regardless of how
  many hours later the session is created.

- **D-02:** If the `crypto_endpoints` table has zero rows (no scan has
  ever run), the bridge skips silently — session creates successfully with
  30 blank CVI `qramm_answers` rows, no `suggested_answer` values, no
  error. Logged at INFO level: "evidence_bridge: no scan data found, skipping".

- **D-03:** The bridge reads ALL field types from `CryptoEndpoint`:
  - Structured fields: `tls_version`, `cipher_suite`, `cert_sig_alg`,
    `cert_pubkey_alg`, `tls_weak_ciphers_present`, `tls_legacy_suites_present`,
    `tls_pfs_supported`, `protocol`
  - JSON blob fields: `ssh_audit_json`, `jwt_scan_json`, `container_scan_json`,
    `cloud_scan_json` (parsed gracefully; malformed blobs skipped without error)
  - Calls `classify_algorithm()` from `quirk.cbom.classifier` on all found
    algorithm name strings to get `nist_level`. This import is safe (no
    circular import risk — `classifier.py` has no scanner or engine deps).

### Maturity Derivation Logic

- **D-04:** Same `suggested_answer` value for all questions within a
  practice area. Three distinct derivation rules, one per practice area:

- **D-05 — Practice 1.2 (Vulnerability Assessment, Q11–20):**
  Quartile bands on the proportion of endpoints with quantum-vulnerable
  algorithms (`nist_level == 0`):
  - 0–25% vulnerable → suggested_answer = 4
  - 26–50% → 3
  - 51–75% → 2
  - 76–100% → 1
  - This directly satisfies ROADMAP success criterion 3: RC4-HMAC-heavy
    scans land at 1–2; AES-256-only scans land at 4.

- **D-06 — Practice 1.1 (Discovery & Inventory, Q1–10):**
  Endpoint count + protocol diversity (distinct `protocol` values present
  in the scan cohort: TLS, SSH, JWT, container, cloud, etc.):
  - Zero endpoints → 1
  - 1+ endpoints but only 1 protocol type → 2
  - 2–3 distinct protocol types → 3
  - 4+ distinct protocol types → 4
  - Planner sets exact thresholds; the band logic above is the intent.

- **D-07 — Practice 1.3 (Dependency Mapping, Q21–30):**
  Distinct algorithm count across all endpoints in the cohort as a proxy
  for dependency breadth:
  - 0 distinct algorithms → 1
  - 1–2 distinct algorithms → 2
  - 3–5 distinct algorithms → 3
  - 6+ distinct algorithms → 4

### Confirmation & Scoring Mechanic

- **D-08:** No new API endpoint for confirmation. Consultant confirms a
  suggested answer by sending `POST .../answers` with `answer_value` set
  for that question via the existing `save_answers` endpoint — same call
  used for manual answers.

- **D-09:** The `save_answers` router handler auto-sets `confirmed_at =
  datetime.now(timezone.utc)` when writing `answer_value` to a row where
  `suggested_answer IS NOT NULL`. This is the sole write to `confirmed_at`
  in v4.7 — no explicit "confirm" flag needed in the request payload.

- **D-10:** `score_session` requires no modification. The existing filter
  `answer_value IS NOT NULL` already correctly excludes unconfirmed
  suggestions (which keep `answer_value = NULL`) and includes confirmed ones
  (which have `answer_value` set). Phase 53 does not touch `score_session`.

- **D-11:** Badge removal signal (QRAMM-14) is implicit in the data model:
  `suggested_answer IS NOT NULL AND answer_value IS NULL` → badge shown;
  `answer_value IS NOT NULL` → badge gone. Phase 54 UI derives badge state
  from these two fields — no extra API field needed.

### Claude's Discretion

- Exact `evidence_source` string format on each `QRAMMAnswer` row (e.g.,
  `"scan:2026-05-07:tls"` or `"evidence_bridge:v1"`). Planner decides a
  consistent format that Phase 54 UI can display.
- Whether the bridge is implemented as a standalone function
  `populate_cvi_suggestions(session_id, db)` called from the router, or as
  a class. Function is simpler; planner decides.
- Exact INFO log message format for D-02 skip-silently path.
- How the bridge handles the `evidence_source` column: per-row (different
  source per practice area) or one value for all CVI rows. Planner decides.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/ROADMAP.md` §"Phase 53: QRAMM Evidence Bridge" — goal, depends
  on Phase 51, success criteria 1–3 (authoritative spec, especially SC-3 for
  the RC4 vs AES-256 maturity ordering)
- `.planning/REQUIREMENTS.md` §QRAMM-12, QRAMM-13, QRAMM-14 — acceptance
  criteria for bridge auto-population, suggested_answer storage semantics,
  and badge behavior

### Phase 51 Foundation (MUST READ)
- `.planning/phases/51-qramm-core-infrastructure/51-CONTEXT.md` — D-09:
  no risk_engine imports from any qramm module (established here, must be
  honoured in evidence_bridge.py); D-10: score persistence; D-11: inline
  Pydantic models in router
- `quirk/models.py` §QRAMMSession, QRAMMAnswer — pre-provisioned Phase 53
  columns: `suggested_answer`, `confirmed_at`, `evidence_source` (no ALTER
  TABLE needed)
- `quirk/dashboard/api/routes/qramm.py` — `create_session` (call site for
  bridge), `save_answers` (update to auto-set `confirmed_at`), `score_session`
  (no changes needed)

### Codebase Patterns
- `quirk/cbom/classifier.py` — `classify_algorithm(name) → (primitive,
  nist_level, classical_level)` — safe import from evidence_bridge.py;
  `quantum_safety_label()` for human-readable label strings
- `quirk/db.py` — SQLAlchemy session pattern, `get_db()` dependency
- `quirk/qramm/questions.py` — `QRAMM_QUESTIONS` list; iterate to find CVI
  question_numbers for the initial `qramm_answers` row creation

### Mandate
- `CLAUDE.md` §"Mandatory Phase Completion Steps" — Obsidian phase note,
  UAT-SERIES.md update + sync, commit pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`quirk/cbom/classifier.py:classify_algorithm()`** — call on each algorithm
  string to get `nist_level`; `nist_level == 0` = quantum-vulnerable. Zero
  circular-import risk: classifier.py imports only stdlib and cyclonedx.
- **`quirk/qramm/questions.py:QRAMM_QUESTIONS`** — iterate with
  `[q for q in QRAMM_QUESTIONS if q['dimension'] == 'CVI']` to get the 30
  CVI rows; extract `question_number` and `practice_area` for bulk insert.
- **`quirk/dashboard/api/routes/qramm.py:save_answers` upsert block** —
  the existing `MERGE`-style upsert already handles the `QRAMMAnswer` row;
  Phase 53 adds a single `if row.suggested_answer is not None: row.confirmed_at
  = now()` check inside the same write path.

### Established Patterns
- **No `risk_engine` imports** — isolation rule established in Phase 51 D-09;
  `evidence_bridge.py` must not import `quirk.engine.risk_engine` or any
  scanner module. Use `classify_algorithm()` from cbom.classifier only.
- **`datetime.now(timezone.utc)`** — Phase 51 DEBT-01 replaced all
  `datetime.utcnow()` calls; bridge and router updates must use
  `datetime.now(timezone.utc)` throughout.
- **Synchronous bridge call** — the bridge is called synchronously within
  `create_session` before the 201 response. 30 SQL writes + lightweight
  classify_algorithm calls are fast enough to not warrant a background task.

### Integration Points
- `quirk/dashboard/api/routes/qramm.py:create_session` — add
  `evidence_bridge.populate_cvi_suggestions(session.id, db)` call after
  the session row is committed (so session.id is available)
- `qramm_answers` table — bridge writes 30 rows (one per CVI question);
  they are created by the existing `create_session` handler with blank
  `answer_value`; bridge updates `suggested_answer` + `evidence_source` on
  those rows in the same request

</code_context>

<specifics>
## Specific Ideas

- The RC4-HMAC / AES-256 maturity ordering from ROADMAP.md success criterion
  3 is the bridge's primary correctness test: a scan with RC4-HMAC Kerberos
  must produce a lower CVI 1.2 suggested_answer than a scan with only AES-256.
  The quartile-band rule (D-05) satisfies this directly — RC4-HMAC has
  `nist_level == 0`, pushing the vuln proportion toward 1.
- `evidence_source` string should identify the scan date + bridge version
  so Phase 54 UI can show "Auto-filled from scan on 2026-05-07" rather than
  a generic badge.

</specifics>

<deferred>
## Deferred Ideas

- **Evidence bridge for SGRM, DPE, ITR dimensions** (QRAMM-F01) — deferred
  to v4.8 per Phase 51 deferred list. CVI bridge quality must be validated
  in Phase 53 first.
- **Badge display in assessment UI** (QRAMM-14) — deferred to Phase 54 which
  owns all QRAMM UI work. The API data model is fully specified here (D-11).
- **`--format json` on any doctor/bridge output** — not needed; exit code
  and data model are the machine-readable signals.

</deferred>

---

*Phase: 53-qramm-evidence-bridge*
*Context gathered: 2026-05-07*
