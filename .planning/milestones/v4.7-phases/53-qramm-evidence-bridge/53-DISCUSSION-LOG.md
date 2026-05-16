# Phase 53: QRAMM Evidence Bridge - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 53-qramm-evidence-bridge
**Areas discussed:** SESSION_BRACKET definition, Maturity derivation logic, Confirmation & scoring mechanic

---

## SESSION_BRACKET Definition

### Q1: How should the bridge identify which CryptoEndpoint rows to read?

| Option | Description | Selected |
|--------|-------------|----------|
| Most recent scan run | Group by date(scanned_at), take all rows from MAX date | ✓ |
| Time window before session creation | All rows where scanned_at >= session.created_at - N hours | |
| All rows ever | No time filtering — aggregate all historical scan data | |

**User's choice:** Most recent scan run
**Notes:** Deterministic cohort regardless of session creation timing.

---

### Q2: What should the bridge do when there are zero CryptoEndpoint rows?

| Option | Description | Selected |
|--------|-------------|----------|
| Skip silently — no suggestions written | Session creates successfully with blank rows, logged at INFO | ✓ |
| Return a warning in the 201 response | bridge_status field in response body | |
| Reject session creation (400) | Force a scan before creating an assessment | |

**User's choice:** Skip silently
**Notes:** Allows consultants to start manual assessments without any prior scan.

---

### Q3: Which CryptoEndpoint fields should the bridge read?

| Option | Description | Selected |
|--------|-------------|----------|
| TLS + cert fields only | Structured string fields only — no JSON parsing | |
| All structured + JSON fields | Also parse ssh_audit_json, jwt_scan_json, etc. | ✓ |
| Use existing boolean flags only | tls_weak_ciphers_present etc — no classify_algorithm() calls | |

**User's choice:** All structured + JSON fields
**Notes:** Richer signal across more protocol types.

---

## Maturity Derivation Logic

### Q4: Same score per practice area vs per-question individual scores?

| Option | Description | Selected |
|--------|-------------|----------|
| Same score per practice area | One score for 1.1, one for 1.2, one for 1.3 | ✓ |
| Per-question individual scores | 30 distinct rules needed | |

**User's choice:** Same score per practice area
**Notes:** Scanner data answers "how well is this area covered", not individual sub-question granularity.

---

### Q5: Practice 1.2 (Vulnerability) maturity mapping?

| Option | Description | Selected |
|--------|-------------|----------|
| Quartile bands on vuln proportion | 0-25% vuln→4, 26-50%→3, 51-75%→2, 76-100%→1 | ✓ |
| Binary: any vuln = 1 or 2 | Any quantum-vulnerable endpoint caps score at 2 | |
| You decide | Leave thresholds to planner | |

**User's choice:** Quartile bands on vuln proportion
**Notes:** Directly satisfies success criterion 3 (RC4 → lower than AES-256).

---

### Q6: Practice 1.1 (Discovery & Inventory) signal?

| Option | Description | Selected |
|--------|-------------|----------|
| Endpoint count + protocol diversity | Count + distinct protocol types present | ✓ |
| Endpoint count only | Pure count with fixed thresholds | |

**User's choice:** Endpoint count + protocol diversity
**Notes:** Distinguishes a TLS-only scan from a full-spectrum scan.

---

### Q7: Practice 1.3 (Dependency Mapping) signal?

| Option | Description | Selected |
|--------|-------------|----------|
| Algorithm diversity as dependency proxy | Distinct algorithm count across all endpoints | ✓ |
| Cross-protocol coverage as proxy | Number of protocol categories with data | |

**User's choice:** Algorithm diversity as dependency proxy
**Notes:** Distinct algorithm count = proxy for cryptographic dependency breadth.

---

## Confirmation & Scoring Mechanic

### Q8: How does a consultant confirm an auto-suggested answer?

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse save_answers — write answer_value | No new endpoint; confirmed_at auto-set | ✓ |
| New confirm endpoint | POST .../answers/confirm — explicit semantic | |
| Auto-confirm on score | Calling POST .../score promotes all unconfirmed rows | |

**User's choice:** Reuse save_answers
**Notes:** Keeps API surface minimal; Phase 54 UI uses the existing endpoint.

---

### Q9: Should router auto-set confirmed_at on save?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — auto-set confirmed_at on save | Any write to answer_value on a suggested row sets confirmed_at | ✓ |
| Only if confirmed=true param sent | Explicit flag in save payload | |

**User's choice:** Yes — auto-set confirmed_at on save
**Notes:** Confirmation is implicit in the act of saving an answer value.

---

### Q10: Should score_session be modified in Phase 53?

| Option | Description | Selected |
|--------|-------------|----------|
| No change needed — existing filter works | answer_value IS NOT NULL already correct | ✓ |
| Add confirmed_at IS NOT NULL check too | Explicit double-filter | |

**User's choice:** No change needed
**Notes:** Existing Phase 51 filter already covers the confirmation semantics correctly.

---

## Claude's Discretion

- `evidence_source` string format per row (planner decides a format Phase 54 can display)
- Bridge as standalone function vs class (function preferred, planner decides)
- Exact INFO log message format for skip-silently path
- Whether `evidence_source` is per-row (different per practice area) or uniform across all CVI rows

## Deferred Ideas

- Evidence bridge for SGRM, DPE, ITR dimensions (QRAMM-F01 — v4.8)
- Badge display in assessment UI (QRAMM-14 — Phase 54)
