# Phase 34: Motion Intelligence — Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the email + broker TLS evidence (already produced by Phases 32 and 33) into the quantum-readiness scoring engine so that `data_in_motion` appears as a 6th named subscore in `compute_readiness_score()`'s output. Scope is **scoring-engine wiring only**:

- `quirk/intelligence/evidence.py` — `EvidenceCounters` dataclass gains six `motion_` fields (MOTION-01).
- `quirk/intelligence/scoring.py` — `SCORE_WEIGHTS` gains five `motion_` ratio entries (MOTION-02); `PROFILE_MULTIPLIERS` gains a `"motion_"` prefix key (MOTION-03); `compute_readiness_score()` returns `data_in_motion` as the 6th subscore (MOTION-04).
- Unit-test coverage proving that nonzero `motion_` counters lower the subscore.

**Out of scope (other phases):**
- CBOM algorithm/cert components for email + broker endpoints → **Phase 35**.
- Dashboard `/motion` tab, executive-summary 6th-line rendering, `MotionFinding` API schema → **Phase 36**.
- Any new scanner code, chaos-lab work, or evidence collection — already complete in Phases 32 and 33.

</domain>

<decisions>
## Implementation Decisions

### Scoring math (MOTION-01 / MOTION-02 reconciliation)
- **D-01:** `motion_email_starttls_missing_count` is **folded into `motion_email_plaintext_ratio`**, not given its own weight. Rationale: MOTION-01 declares 6 evidence counters but MOTION-02 declares only 5 ratios — the asymmetry is intentional dedup, not a spec gap. SMTP-without-STARTTLS and IMAP/POP3-without-TLS are both "mail traffic without TLS protection" and share the 12.0 weight.
- **D-02:** `motion_email_plaintext_ratio` numerator = `(motion_email_plaintext_count + motion_email_starttls_missing_count)`. Denominator stays the standard `total_endpoints` denom used by every other ratio in `scoring.py`.
- **D-03:** All 5 `motion_` ratio weights are LOCKED per MOTION-02: `motion_email_plaintext_ratio=12.0`, `motion_email_weak_cipher_ratio=6.0`, `motion_broker_plaintext_ratio=14.0`, `motion_broker_weak_tls_ratio=8.0`, `motion_broker_weak_cipher_ratio=6.0`. Do not adjust.

### Subscore key naming (MOTION-04)
- **D-04:** Append `data_in_motion` to the existing five subscore keys. Final shape: `{hygiene, modern_tls, identity_trust, agility_signals, data_at_rest, data_in_motion}`. **Do NOT rename** the existing five to match the ROADMAP's prose ("alongside tls, ssh, api, identity, data_at_rest") — that prose is aspirational.
- **D-05:** Renaming the five existing keys to roadmap-text names (tls/ssh/api/identity/...) is **deferred** — it would break the React dashboard, the `/api/scan/latest` contract, and saved scan reports. Captured as a v4.5+ idea.

### Driver integration
- **D-06:** Compute `motion_impacts` and `motion_drivers` exactly as the existing `dar_impacts` / `dar_drivers` pattern (lines 179–188 of `scoring.py`). Append `motion_drivers` to `all_drivers` before the abs-points sort, so motion findings can surface in `top_drivers` (the executive-summary list).
- **D-07:** Driver labels follow the existing human-readable convention: e.g., `"Plaintext broker listeners"`, `"Weak TLS on brokers"`, `"Email plaintext / missing STARTTLS"`, `"Weak cipher on email TLS"`, `"Weak cipher on broker TLS"`. Mirror the wording style in lines 158–164.

### Profile multipliers (MOTION-03)
- **D-08:** `PROFILE_MULTIPLIERS` gains the `"motion_"` prefix key with strict=1.4 / balanced=1.0 / lenient=0.7. Insert in the dict alongside existing prefixes — order does not matter mathematically, but place after `"dar_"` for readability.

### Verification approach (SC-1)
- **D-09:** SC-1 is verified by **unit tests against `compute_readiness_score()` with synthesized evidence dicts** — one with `motion_broker_plaintext_count >= 2`, one with all motion counters at 0. Assert `result["subscores"]["data_in_motion"]` is strictly lower in the first case, and that the overall `score` is also lower.
- **D-10:** Add a parallel unit test asserting that `top_drivers` surfaces a motion driver when motion counters dominate other categories.
- **D-11:** Integration validation against `labs/broker/` and `labs/email/` chaos labs is **deferred to Phase 36** (dashboard work), where it naturally combines with end-to-end UI smoke. No Docker dependency added in Phase 34.

### Legacy-scan compatibility
- **D-12:** Scans written before Phase 34 lack `motion_` evidence keys. `compute_readiness_score()` already uses `_as_int(evidence.get("...", 0))` for every counter — that pattern handles missing keys as 0 cleanly. No migration needed; legacy scans simply produce `data_in_motion = 100` (no findings = full credit), consistent with how other subscores treat zero-evidence input.

### Claude's Discretion
- Internal helper organization in `evidence.py` — whether the six new fields are appended to `EvidenceCounters` in declaration order or grouped under a `# motion_` comment block.
- Whether the `motion_impacts` / `motion_score` block lives directly inline in `compute_readiness_score()` (mirroring `dar_impacts`) or in a small `_compute_motion_subscore()` helper. Planner picks based on line-budget readability.
- Naming of the unit-test file — likely `tests/intelligence/test_motion_subscore.py` to mirror existing `test_*_subscore.py` files if they exist; planner verifies the convention.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap (locked)
- `.planning/REQUIREMENTS.md` §"Evidence Counters and Scoring" — MOTION-01, MOTION-02, MOTION-03, MOTION-04 are LOCKED. Do not redefine fields, weights, or multiplier values.
- `.planning/ROADMAP.md` Phase 34 entry — Motion Intelligence goal + 4 success criteria.

### Pattern templates (read before writing scoring code)
- `quirk/intelligence/scoring.py` (entire file, ~210 lines) — the wiring template. Specifically:
  - Lines 5–31 — `SCORE_WEIGHTS` shape; insert `motion_` entries in the same dict.
  - Lines 33–37 — `PROFILE_MULTIPLIERS` shape; add `"motion_"` to all three profiles.
  - Lines 179–188 — `dar_impacts` / `dar_drivers` block. **This is the exact template** for `motion_impacts` / `motion_drivers`.
  - Line 190 — `total_score = int(...)` sum; add `motion_score` to the sum.
  - Lines 193–196 — `all_drivers` accumulation; append `motion_drivers`.
  - Lines 199–210 — return shape; add `"data_in_motion": motion_score` as the 6th `subscores` key.
- `quirk/intelligence/evidence.py` — `EvidenceCounters` dataclass. Append the six `motion_` fields.

### Carry-forward decisions (from Phase 32 + Phase 33)
- Phase 32 finding IDs (`weak-cipher`, `starttls-downgrade-risk`) and Phase 33 finding IDs (`kafka-plaintext-listener`, `amqp-plaintext-listener`, `redis-plaintext-no-auth`) are the upstream signals that increment the new motion_ counters. The counter-increment logic itself lives in `quirk/engine/findings.py` (or wherever evidence aggregation happens) — the planner will read that module to identify the right counter-bump call sites.
- `_as_int(evidence.get(key, 0))` pattern for missing keys → automatic legacy-scan compatibility (D-12).

### Downstream consumers (informational; not modified in Phase 34)
- `quirk/dashboard/static/...` — the React dashboard reads `subscores` keys but tolerates extras. Phase 36 is responsible for rendering `data_in_motion`. Phase 34 must not break Phase 36's expected key.
- `quirk/cbom/classifier.py` — Phase 35 consumes `ep.protocol` strings, not subscore keys. No coupling.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_apply_weighted_impacts()` helper (`scoring.py` ~line 75) — converts `[(label, points), ...]` to a clamped score + driver list. Use verbatim for motion_impacts.
- `_ratio(num, denom)` helper (`scoring.py` ~line 53) — produces 0..1 ratios with safe division. Use for all motion ratios.
- `_as_int(...)` (`scoring.py` ~line 39) — safe integer extraction from evidence dict; tolerates missing keys.

### Established Patterns
- **Weighted-impact subscore:** every existing subscore (`hygiene_*`, `modern_tls_*`, `identity_trust_*`, `agility_*`, `dar_*`) follows the pattern `impacts = [(label, -ratio*weight), ...]; score, drivers = _apply_weighted_impacts(impacts)`. Motion mirrors this exactly.
- **Profile multiplier dict expansion:** `PROFILE_MULTIPLIERS[prof].items()` iterates prefix→factor pairs and `scoring.py:97` rewrites `w[key]` for any `SCORE_WEIGHTS` key starting with that prefix. Adding `"motion_": 1.4` automatically scales all five `motion_*_ratio` weights — no per-key wiring needed.
- **Subscore in return shape:** the `subscores` dict is hand-built (lines 202–208). Add one more line: `"data_in_motion": motion_score`.

### Integration Points
- `quirk/intelligence/evidence.py` `EvidenceCounters` — only structural change required outside `scoring.py`. Append 6 fields with default `int = 0`.
- `quirk/engine/findings.py` (or whichever module increments evidence counters from finding IDs) — must increment the new `motion_` counters when the relevant Phase 32 / Phase 33 finding IDs fire. Planner identifies the exact call site during research.
- Tests: new `tests/intelligence/test_motion_subscore.py` (or similarly named) with at least: (a) zero-motion case, (b) plaintext-broker case, (c) STARTTLS-missing folds into plaintext-ratio, (d) profile-multiplier `strict` increases penalty.

### Non-coupling
- No new dependencies. No new modules. No new CLI flags. No DB migration. No chaos-lab work. No frontend changes.

</code_context>

<specifics>
## Specific Ideas

- **Mirror `dar_impacts` block exactly** (`scoring.py:179–188`) for `motion_impacts`. Same shape, same calls, same `_apply_weighted_impacts` consumer.
- **STARTTLS fold formula:** `motion_email_plaintext_numerator = motion_email_plaintext_count + motion_email_starttls_missing_count`, then `_ratio(numerator, denom) * w["motion_email_plaintext_ratio"]`.
- **Driver label wording:**
  - "Plaintext broker listeners" — `motion_broker_plaintext_count`
  - "Weak TLS on brokers" — `motion_broker_weak_tls_count`
  - "Weak cipher on broker TLS" — `motion_broker_weak_cipher_count`
  - "Email plaintext or missing STARTTLS" — combined `motion_email_plaintext_count + motion_email_starttls_missing_count`
  - "Weak cipher on email TLS" — `motion_email_weak_cipher_count`
- **Test seed dicts:** keep them minimal — only the keys under test need to be set; everything else defaults to 0 via `_as_int`.

</specifics>

<deferred>
## Deferred Ideas

- **Rename existing subscore keys to ROADMAP prose names** (tls/ssh/api/identity/...) — captured as v4.5+ idea (D-05). Would require coordinated dashboard, API, and report-storage migration.
- **Integration test against `labs/email/` + `labs/broker/` chaos labs** for SC-1 — deferred to Phase 36 (dashboard) where end-to-end Docker validation already lives.
- **`motion_email_starttls_missing_ratio` as its own scoring weight** — rejected (D-01); fold-into-plaintext is the chosen model. Revisit only if telemetry shows the fold under-weights STARTTLS-missing in real engagements.
- **`MotionFinding` API schema** for `/api/scan/latest` — Phase 36 scope.
- **Motion CBOM components** (algorithm + cert + protocol entries for email/broker endpoints) — Phase 35 scope.
- **DAR dashboard tab (DASH-05 carry-forward)** — separate UI work, not Phase 34.

</deferred>

---

*Phase: 34-motion-intelligence*
*Context gathered: 2026-04-28*
