# Phase 60: Score Arithmetic Correctness - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 60 closes audit blockers 12, 15 + Pattern E by making every score path
bounded and defensible. The phase delivers four targeted arithmetic fixes plus
the tests that prove them:

- **SCORE-01 (CR-06, WR-05):** Top-level readiness score clamped to `[0, 100]`
  inside `compute_readiness_score()` — currently the sum of six 25-point
  subscores can reach 150 with no clamp.
- **SCORE-02 (BL-01):** `POST /api/qramm/sessions/{id}/score` rejects a
  client-supplied multiplier outside `[0.8, 1.5]` with HTTP **400** (not the
  current Pydantic-generated 422); canonical range documented in OpenAPI schema.
- **SCORE-03 (CR-04):** Confidence bonus for TLS enumeration coverage is exactly
  0 when zero TLS endpoints were scanned — the current fallback of `1.0`
  incorrectly awards 20 confidence points to zero-data scans.
- **SCORE-04 (BL-02):** A parametrized test sweeping `[0.0, 4.0]` at 0.5-step
  increments verifies the QRAMM maturity bands are closed and contiguous (no
  gaps, no overlaps, no silent fall-throughs).

**In scope:** fixes to `quirk/intelligence/scoring.py`,
`quirk/intelligence/confidence.py`, and `quirk/dashboard/api/routes/qramm.py`;
new tests in `tests/`; AUDIT-TASKS.md row closures (flip BL-01, BL-02,
CR-04, CR-06 + Pattern E items to `[x] closed`).

**Out of scope:** weight renormalization (SCORE_WEIGHTS sum ≠ 100 is a WARNING
deferred to v5.x tech-debt), HTML/PDF score rendering, CBOM fixes (Phase 61),
React hook cancellation (Phase 62).

</domain>

<decisions>
## Implementation Decisions

### Clamp Strategy (SCORE-01)

- **D-01:** Add a single `_clamp(total_score, 0, 100)` call as the last step
  inside `compute_readiness_score()` before the `return` statement — at line
  219 of `quirk/intelligence/scoring.py` where `total_score` is currently set.
  Individual subscore caps (`score_cap=25.0`) are left unchanged. This is the
  authoritative bound; no weight renormalization needed.
  ```python
  total_score = int(_clamp(
      hygiene_score + modern_tls_score + identity_trust_score +
      agility_score + dar_score + motion_score,
      0, 100
  ))
  ```
- **D-02:** The `"score"` key returned by `compute_readiness_score()` is
  therefore already clamped. Callers (`writer.py`, `scan.py`, `qramm.py`) do
  NOT add a second clamp — the canonical clamp lives only in
  `compute_readiness_score()`.

### Property Test (SCORE-01 test)

- **D-03:** Use a **seeded `random.Random(42)` loop** (1,000 iterations) in a
  new pytest test. No Hypothesis dependency needed. Each iteration:
  1. Synthesize a random evidence dict (endpoints 0–200, counts 0–endpoints,
     rates 0.0–1.0 using the RNG).
  2. Call `compute_readiness_score(evidence)` with a random profile.
  3. Assert `0 <= result["score"] <= 100`.
  The seed is fixed for determinism; the 1,000-sample breadth satisfies
  SCORE-01's coverage requirement. Test file: `tests/test_score_clamp_property.py`.

### Multiplier 400 Path (SCORE-02)

- **D-04:** **Remove** the `ge=0.8, le=1.5` Pydantic field constraints from
  `ScoreRequest.profile_multiplier` in `quirk/dashboard/api/routes/qramm.py`.
  Replace them with an explicit guard at the top of `score_session()`:
  ```python
  if multiplier is not None and not (0.8 <= multiplier <= 1.5):
      raise HTTPException(
          status_code=400,
          detail={
              "error_code": "QRAMM_MULTIPLIER_OUT_OF_RANGE",
              "message": "profile_multiplier must be in [0.8, 1.5]",
              "valid_range": [0.8, 1.5],
          },
      )
  ```
  This guarantees HTTP 400 (not 422). The range is still documented on the
  field via `Field(description="Profile risk multiplier. Must be in [0.8, 1.5].")`.
- **D-05:** Values inside `[0.8, 1.5]` are accepted and passed through to
  `compute_overall_score()` unchanged — no server-side re-clamping of valid
  values.
- **D-06:** The OpenAPI schema description on `ScoreRequest.profile_multiplier`
  is updated to include the valid range and the 400 error code so API consumers
  have self-documenting guidance.

### Confidence Zero-Data Guard (SCORE-03)

- **D-07:** In `quirk/intelligence/confidence.py` line 82–83, change the
  zero-TLS fallback from `1.0` to `0.0`:
  ```python
  # Before:
  tls_enum_coverage_ratio = 1.0 if tls_count == 0 else 0.0
  # After:
  tls_enum_coverage_ratio = 0.0  # no TLS → no coverage bonus
  ```
  This means a scan with no TLS endpoints no longer receives the 20-point
  `tls_enum_coverage_ratio` contribution. The fix applies only to the
  "no evidence provided AND no TLS scanned" branch — scans that DO enumerate
  TLS are unaffected.
- **D-08:** A dedicated unit test asserts: evidence with `tls_count=0` and no
  `tls_enum_coverage_ratio` key produces `confidence_score` with
  `tls_enum_coverage_ratio` factor contributing exactly `0.0` points.

### Maturity Band Test (SCORE-04)

- **D-09:** Add a parametrized pytest test in `tests/test_qramm_scoring.py`
  that sweeps `score` from 0.0 to 4.0 in 0.5-step increments (81 steps) and
  asserts:
  1. Each call to `_maturity_label(score)` returns a non-None string.
  2. Every score maps to exactly one of the five canonical labels
     (`Basic`, `Developing`, `Established`, `Advanced`, `Optimizing`).
  The maturity band logic is already contiguous — this test is a regression
  guard, not a bug fix. Import `_maturity_label` directly from
  `quirk.qramm.scoring`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Score Arithmetic
- `quirk/intelligence/scoring.py` — `compute_readiness_score()` at line 219 where
  `total_score` is assembled without a top-level clamp; `_clamp()` and
  `_apply_weighted_impacts()` helpers already exist and must be reused.
- `quirk/intelligence/confidence.py` — `compute_confidence()` lines 82–83:
  the zero-TLS fallback that incorrectly assigns `tls_enum_coverage_ratio = 1.0`.

### QRAMM Scoring + Multiplier
- `quirk/qramm/scoring.py` — `compute_overall_score()` and `_maturity_label()`;
  `_maturity_label` must be importable directly for the sweep test.
- `quirk/dashboard/api/routes/qramm.py` — `ScoreRequest` (lines 91–93),
  `score_session()` (line 330–); `_compute_multiplier()` (line 168) already
  clamps correctly — the server-side fix targets only the client-supplied
  multiplier path.

### Audit Ledger
- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — flip `qramm-compliance/BL-01`,
  `qramm-compliance/BL-02`, `cbom-intel-reports/CR-04`, `cbom-intel-reports/CR-06`
  and Pattern E items to `[x] closed` as part of this phase.

### Requirements
- `.planning/REQUIREMENTS.md` — SCORE-01 through SCORE-04 (lines under
  "Score Arithmetic Correctness" section).
- `.planning/ROADMAP.md` §Phase 60 — Success Criteria 1–4 are the acceptance
  gates.

### Existing Tests to Extend
- `tests/test_intelligence_scoring.py` — existing scoring tests; regression
  guard ensures subscore values are unaffected by the top-level clamp.
- `tests/test_intelligence_confidence.py` — existing confidence tests; extend
  with the zero-TLS guard assertion.
- `tests/test_qramm_scoring.py` — existing maturity threshold tests; extend
  with the parametrized sweep.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_clamp(v, lo, hi)` in `quirk/intelligence/scoring.py:65` — already exists,
  already handles float inputs; use it for the top-level `[0, 100]` clamp.
- `random` stdlib — no new dep needed for the seeded property test.

### Established Patterns
- `compute_readiness_score()` returns a dict with `"score"`, `"subscores"`, and
  `"drivers"` — the `"score"` key is what callers persist and display. Clamping
  at this key means all callers get bounded output without changes.
- The `ScoreRequest` Pydantic model pattern (lines 91–93) is standard FastAPI;
  the multiplier field must change from `Field(..., ge=0.8, le=1.5)` to
  `Field(None, description="...")` with the bounds check moved into the handler.
- The confidence module returns `"NO_DATA"` rating when `endpoints == 0` — the
  zero-TLS fix is a narrower case (endpoints > 0 but tls_count == 0).

### Integration Points
- `quirk/reports/writer.py:127` reads `score_raw["score"]` → stored as
  `score["total"]`. After the clamp fix, this value is always `[0, 100]`.
- `quirk/dashboard/api/routes/scan.py:866` calls `compute_readiness_score()`
  and stores the result — no changes needed there.
- Dashboard JSON response includes `profile_multiplier: float` (line 389 of
  `qramm.py`) — must still echo the accepted value, not a clamped one.

</code_context>

<specifics>
## Specific Ideas

- The property test file is `tests/test_score_clamp_property.py` — a new file,
  not bolted onto an existing test module, since it tests cross-cutting
  behavior (1,000 random inputs across evidence shapes).
- The 400 error payload uses `error_code: "QRAMM_MULTIPLIER_OUT_OF_RANGE"` as
  the machine-readable key (consistent with the error-code pattern introduced
  in Phase 57 for scanner rejections).

</specifics>

<deferred>
## Deferred Ideas

- **SCORE_WEIGHTS normalization (WR-06):** The weights sum to 261, not 100.
  This is a known WARNING; normalizing would change all weight values and break
  existing test fixtures. Deferred to v5.x tech-debt sweep per STATE.md D-07
  (dead code / tech debt sweep is out of scope for v4.8).
- **cbom-intel-reports/WR-05 (score_cap=25.0 magic constant):** Extracting it
  to a named constant is a cleanup, not a bug fix. Deferred.

</deferred>

---

*Phase: 60-score-arithmetic-correctness*
*Context gathered: 2026-05-09*
