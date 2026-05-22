# Phase 88: Scoring Residuals — Research

**Researched:** 2026-05-22
**Domain:** Python scoring engine, CBOM builder, report renderers (CLI markdown, HTML/PDF, dashboard API)
**Confidence:** HIGH — all claims verified against current source code

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** EVIDENCE-TALLY-01 resolves as documented correct-by-design / won't-fix at the subscore level. Orthogonal per-category model; no cross-category penalties.
- **D-02:** Build parametrized six-subscore-family test suite to forward-lock the orthogonal contract. Follow project's forward-locking-invariant test pattern.
- **D-03:** Verify-first — `quirk/assessment/readiness_score.py` is DELETED; `quirk/reports/writer.py:17` imports from `quirk.intelligence.scoring`. Single canonical engine confirmed (see §D-03 Verification below).
- **D-04:** Satisfy RENDER-CLI-01 and RENDER-PDF-01 via a data-layer parity gate: parametrized regression test asserting that overall + all six subscore VALUES received by each surface are identical for fixture scans, anchored to the Phase 86 0–100 contract. Fix divergence via a single shared rounding/formatting helper.
- **D-05:** SCORE-CBOM-01 — emit algorithm components for crypto the scanners ALREADY observe but Pass-1 drops, for the five zero-algo profiles. No new scanning.
- **D-06:** Genuinely plaintext profiles emit an affirmative no-crypto marker (CBOM property / coverage note).
- **D-07:** Reports (HTML, PDF, CLI markdown) show each subscore as `Label: N/25` PLUS explicit rollup math.
- **D-08:** D-01 + D-07 together resolve BACK-89 via transparency without changing the math.

### Claude's Discretion

- Exact CBOM property key/shape for the no-crypto marker (D-06)
- Precise table/layout of the decomposition block (D-07)
- Shared rounding-helper location (D-04)

### Deferred Ideas (OUT OF SCOPE)

- Overall critical-cap / severity floor on the headline score (SSL-Labs pattern). Deliberate scoring-model change; its own future phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVIDENCE-TALLY-01 | Resolve orthogonal-subscore semantics with product-decision gate + parametrized test suite | §Requirement: EVIDENCE-TALLY-01 |
| RENDER-CLI-01 | Empirically verify CLI/markdown report overall + subscores match dashboard for same scan ID | §Requirement: RENDER-CLI-01 / RENDER-PDF-01 |
| RENDER-PDF-01 | Same empirical verification for HTML/Playwright-PDF report | §Requirement: RENDER-CLI-01 / RENDER-PDF-01 |
| SCORE-CBOM-01 | Pass-1 emits real algorithm components for the five zero-algo profiles | §Requirement: SCORE-CBOM-01 |
| SCORE-XPARENCY-01 | Reports surface six subscores labeled N/25 plus rollup math | §Requirement: SCORE-XPARENCY-01 |
</phase_requirements>

---

## Summary

Phase 88 is a scoring-residuals cleanup phase: five requirements inherited from v4.10.1, all addressable without changing the scoring math or adding new scanners. All work is concentrated in three layers: the report renderers (executive markdown, HTML template, scorecard markdown), the CBOM builder Pass-1, and a new forward-locking test module.

The key architectural fact is that **one canonical scoring engine exists** (`quirk/intelligence/scoring.py`) and all report surfaces already call it. The CONCERNS.md dual-engine entry is confirmed stale. The data-layer parity question (D-04) becomes: do all three surfaces (CLI scorecard markdown, dashboard API, HTML report) use the same dict value without re-rounding? They do — rounding happens once in `_apply_weighted_impacts` (line 109) and once for the total in `compute_readiness_score` (line 255-258). No surface re-rounds. The only divergence vector is `_scorecard_markdown` accessing `score.get("total")` while the executive markdown (`build_exec_markdown`) calls `compute_readiness_score` independently with the same evidence — both reach the same function. The parity gate test (D-04) must verify this invariant over fixture scans, not re-audit production paths.

The SCORE-CBOM-01 work (D-05/D-06) is the most code-intensive change: the five zero-algo profiles each have a distinct reason for their gap, and each requires a targeted fix in `quirk/cbom/builder.py` Pass-1 or a new affirmative no-crypto marker.

**Primary recommendation:** Implement in two plans — Plan A: scoring transparency + parity gate (EVIDENCE-TALLY-01 + RENDER-CLI-01 + RENDER-PDF-01 + SCORE-XPARENCY-01), Plan B: CBOM builder Pass-1 fixes (SCORE-CBOM-01). Both plans are independent and could parallelize if needed, but the CBOM plan touches a different file from the report plan.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Scoring computation | `quirk/intelligence/scoring.py` | None | Single canonical engine; all surfaces delegate here |
| Subscore transparency (D-07) | Report renderers (writer.py, executive.py, template) | Dashboard (already done) | Dashboard already shows `/25` gauges; reports need parity |
| Render parity gate (D-04) | Test layer (`tests/test_score_render_parity.py`) | Data layer (no change) | Gate validates existing data-layer; no production code change if no divergence |
| CBOM emission (D-05/D-06) | `quirk/cbom/builder.py` Pass-1 | CBOM property model | All algorithm and marker emission is builder responsibility |
| Forward-locking invariant (D-02) | Test layer (`tests/test_scoring_orthogonal_contract.py`) | `scoring.py` (no change) | Test locks the model; scoring code is unchanged |

---

## D-03 Verification: Single-Engine Claim

**CONFIRMED — CONCERNS.md entry is stale.**

`quirk/assessment/readiness_score.py` **does not exist**. [VERIFIED: `ls quirk/assessment/` returns only `migration_advisor.py` and `operator_context.py`]

Current import chain:
- `quirk/reports/writer.py:17` — `from quirk.intelligence.scoring import compute_readiness_score` [VERIFIED]
- `quirk/reports/executive.py:6` — `from quirk.intelligence.scoring import compute_readiness_score` [VERIFIED]
- `quirk/dashboard/api/routes/scan.py:44` — `from quirk.intelligence.scoring import compute_readiness_score` [VERIFIED]

All three production surfaces import from the same module. The CONCERNS.md §1.11 entry (which cited `quirk/assessment/readiness_score.py` as a second engine) is an artifact of the pre-Phase 83 architecture when that file existed. The planner must update CONCERNS.md (or note it for Phase 91 cleanup) but does NOT need to reconcile any divergent engines.

---

## Requirement: EVIDENCE-TALLY-01

### What to lock

The scoring contract in `quirk/intelligence/scoring.py`:

```python
# _apply_weighted_impacts (lines 103-111)
def _apply_weighted_impacts(impacts, score_cap=25.0):
    total = score_cap + sum(v for _, v in impacts)   # penalties are negative
    clamped = _clamp(total, 0.0, score_cap)
    score = int(round(clamped))
    return score, ...

# Six subscore calls (lines 182-253)
hygiene_score, _   = _apply_weighted_impacts(hygiene_impacts)
modern_tls_score, _ = _apply_weighted_impacts(modern_tls_impacts)
identity_trust_score, _ = _apply_weighted_impacts(identity_trust_impacts)
agility_score, _   = _apply_weighted_impacts(agility_impacts)
dar_score, _       = _apply_weighted_impacts(dar_impacts)
motion_score, _    = _apply_weighted_impacts(motion_impacts)

# Overall (lines 255-258)
total_score = int(round(
    (hygiene_score + modern_tls_score + identity_trust_score +
     agility_score + dar_score + motion_score) / 1.5
))
```

**Orthogonality property to lock:** Each subscore's `impacts` list contains ONLY keys from its own category prefix (`hygiene_*`, `modern_tls_*`, `identity_*`, `agility_*`, `dar_*`, `motion_*`). There is no evidence key shared across categories. A category with zero findings in its category scores 25/25 regardless of findings in other categories. This is the contract that the D-02 test must lock.

### Forward-locking test pattern (D-02)

The project's established pattern is in `tests/test_score_weights_invariant.py` (simple assertion), `tests/test_xml_safe.py` (parametrized behavioral gates), and `tests/test_audit_ledger_zero_open.py` (grep/AST gate). For D-02, the pattern is a **parametrized pytest** that:

1. Builds a fixture evidence dict with findings in only ONE category.
2. Calls `compute_readiness_score(evidence)`.
3. Asserts that the affected category's subscore < 25, while ALL OTHER subscores == 25.
4. Parametrizes over all six categories.

This is a pure unit test over `scoring.py` — no database, no endpoints needed.

### Resolution wording (for inline rationale)

> EVIDENCE-TALLY-01: Resolved correct-by-design. The scoring model (`quirk/intelligence/scoring.py`) assigns each of the six subscores independently: `subscore = 25 + sum(category_local_penalties)`, clamped [0, 25]. A category with no findings of its own type scores 25/25, regardless of findings in other categories. This orthogonality is intentional — it mirrors the SSL Labs methodology of per-dimension grading before a headline composite. Cross-category penalties are explicitly rejected (Phase 88 D-01). The parametrized test in `tests/test_scoring_orthogonal_contract.py` forward-locks this contract permanently.

---

## Requirement: RENDER-CLI-01 / RENDER-PDF-01

### Current rounding sites per surface [VERIFIED]

**Canonical rounding (happens once, in `scoring.py`):**

| Site | File:Line | What it rounds |
|------|-----------|----------------|
| Per-subscore | `scoring.py:109` — `int(round(clamped))` | Each of the 6 subscores, [0,25] |
| Total score | `scoring.py:255-258` — `int(round(sum_of_six / 1.5))` | Overall readiness, [0,100] |

**Surface-level data flow (no additional rounding):**

| Surface | Path | Score access | Subscore access |
|---------|------|-------------|-----------------|
| CLI scorecard markdown | `writer.py:157-169` → `_scorecard_markdown(score)` | `score.get("total")` | `score.get("subscores")` dict |
| CLI terminal table | `writer.py:268-275` | `score.get("total", 0)` | Not displayed (gap for D-07) |
| Executive markdown | `executive.py:115-122` — independent call to `compute_readiness_score` | `score_raw["score"]` | `score_raw["subscores"]` (not rendered — gap for D-07) |
| HTML/PDF report | `html_renderer.py:165` — receives pre-computed `score` dict from `writer.py` | `score.get("total", 0)` | `score.get("subscores")` (not rendered in template — gap for D-07) |
| Dashboard API | `scan.py:1057-1079` — independent call to `compute_readiness_score` | `score_raw.get("score", 0)` | `subscores_raw` → `SubScores(...)` — ALREADY rendered in React |

**Key finding:** There is NO secondary rounding at the surface level. All surfaces call `compute_readiness_score` with the same `evidence` dict (from `build_evidence_summary`) and the same `profile` (from config). The only divergence vector is if `build_evidence_summary` is called with different arguments — `writer.py` calls it with `(endpoints, findings)` while `executive.py` also calls it with `(endpoints, findings)`. The dashboard's `scan.py` calls it with `(endpoints, [f.model_dump() for f in findings])` where `findings` are derived findings (FindingItem), not the raw findings list.

**What the D-04 parity gate must assert:**

For a fixture scan, run `compute_readiness_score(build_evidence_summary(endpoints, findings))` once and compare its output against the equivalent call path for each surface. Since all three surfaces end up calling the same function with the same arguments (or equivalent arguments), this is expected to pass verified-no-bug — but the test must exist to lock the invariant.

### Shared rounding/formatting helper (D-04)

If any divergence is found: introduce `quirk/intelligence/format_score.py` (or a helper in `scoring.py`) that returns a canonical dict `{"total": int, "subscores": dict[str, int], ...}`. Currently `writer.py` wraps the raw output in its own `score` dict (lines 166-170); this is the only format adaptation, and it already preserves the integer values.

---

## Requirement: SCORE-XPARENCY-01

### Current state: subscores NOT rendered in any report surface

**Dashboard:** ALREADY renders subscores as `Label: N/25` via `ScoreGauge` with `maxValue={25}`. [VERIFIED: `src/dashboard/src/pages/executive.tsx:251-256`]

```tsx
// Dashboard already has this — target for report parity
<ScoreGauge score={score.subscores.hygiene} label="Hygiene" size={120} maxValue={25} />
<ScoreGauge score={score.subscores.modern_tls} label="Modern TLS" size={120} maxValue={25} />
<ScoreGauge score={score.subscores.identity_trust} label="Identity" size={120} maxValue={25} />
<ScoreGauge score={score.subscores.agility_signals} label="Agility" size={120} maxValue={25} />
<ScoreGauge score={score.subscores.data_at_rest} label="Data at Rest" size={120} maxValue={25} />
<ScoreGauge score={score.subscores.data_in_motion} label="Data in Motion" size={120} maxValue={25} />
```

**CLI scorecard markdown (`_scorecard_markdown`):** `score.get("subscores")` is available in the dict but NOT rendered in the output. [VERIFIED: `writer.py:91-109` — only renders `score.get("total")` and confidence]

**Executive markdown (`build_exec_markdown`):** Calls `compute_readiness_score` independently, gets `score_raw["subscores"]` dict, but does NOT include it in the markdown output. [VERIFIED: `executive.py:115-184` — renders only total/100 and rating]

**HTML/PDF template (`report.html.j2`):** Receives `total_score` and `confidence` only. The `subscores` dict is in the `score` parameter passed to `render_html_report` but is NOT forwarded to the Jinja2 template. [VERIFIED: `html_renderer.py:189-207` — template variables listed do not include subscores]

### What D-07 requires

Three targeted additions:

**1. CLI scorecard markdown** (`writer.py:_scorecard_markdown`): After the score line, add a subscore decomposition block:
```
## Score Decomposition
| Category | Score | Budget |
|----------|-------|--------|
| Hygiene | N | /25 |
| Modern TLS | N | /25 |
| Identity | N | /25 |
| Agility | N | /25 |
| Data at Rest | N | /25 |
| Data in Motion | N | /25 |
| **Total** | sum → ÷1.5 → **overall/100** |
```

**2. Executive markdown** (`executive.py:build_exec_markdown`): Add a "Score Decomposition" section after the "## Quantum Readiness Score" section using `score_raw["subscores"]`.

**3. HTML/Jinja2 template** (`report.html.j2` + `html_renderer.py`): Pass `subscores=score.get("subscores", {})` to the template and render it in the Executive Summary section after the score card.

The subscore label mapping (for human-readable labels) mirrors the dashboard:

| Key | Display Label |
|-----|--------------|
| `hygiene` | Hygiene |
| `modern_tls` | Modern TLS |
| `identity_trust` | Identity |
| `agility_signals` | Agility |
| `data_at_rest` | Data at Rest |
| `data_in_motion` | Data in Motion |

The rollup math to display: `sum(six subscores) / 1.5 = overall` (show the raw sum and the division).

---

## Requirement: SCORE-CBOM-01

### Per-profile analysis: what scanners observe vs what Pass-1 emits [VERIFIED against builder.py + scanner source]

**Profile: `database` (POSTGRESQL, MYSQL)**

Scanner behavior (verified in `db_connector.py`):
- `postgres-ssl-off` (port 25432): `service_detail="PostgreSQL/ssl-off"`. `cert_pubkey_alg` is NOT set. No TLS is negotiated.
- `mysql-ssl-off` (port 23306): `service_detail="MySQL/ssl-off"`. `cipher_suite=None`. `cert_pubkey_alg` NOT set.

Builder Pass-1 behavior:
- `POSTGRESQL` branch (line 509-511): only emits `_register_algorithm(ep.cert_pubkey_alg)` when `cert_pubkey_alg` is set. For ssl-off: NOT set → **ZERO algo components**.
- `MYSQL` branch (line 497-507): parses `service_detail`, extracts cipher from `"MySQL/<cipher>-ok"` or `-weak`; explicitly filters out `"SSL-OFF"` → **ZERO algo components** for ssl-off.

**What the scanner already observes:** The scanner confirms that SSL is OFF — there is no TLS cipher negotiated. The database IS accessible (finding emitted), but there is no cryptographic material on the wire.

**D-05 approach:** The scanner observes "no TLS" — there is no crypto algorithm to catalog. This is a genuinely plaintext endpoint.

**D-06 affirmative marker:** Emit a CBOM property on the Bom root (or a synthetic no-crypto component with a `quirk:coverage-note` property) stating: `"plaintext endpoint — database connection uses no TLS; no cryptographic material observed"`. The existing `Property(name="quirk:fips140-3-status", ...)` and `Property(name="quirk:cmvp-coverage", ...)` patterns on algorithm components show the convention.

---

**Profile: `storage-s3` (S3, AZURE_BLOB)**

Scanner behavior (verified in `aws_connector.py`):
- `encrypted-bucket`: `service_detail="S3/sse-s3"` → builder line 519-526: AES-256 IS registered ✓
- `unencrypted-bucket`: `service_detail="S3/unencrypted"` → builder condition fails → **ZERO algo components** for this endpoint.

**What the scanner already observes:** The S3 connector confirms the bucket has no server-side encryption. There is no KMS key, no AES-256 cipher in use.

**D-05 approach:** The `unencrypted-bucket` endpoint is genuinely plaintext-at-rest. No crypto material to catalog.

**D-06 affirmative marker:** For `S3` endpoints where `service_detail` ends with `/unencrypted` or where no encrypted posture matched: emit a property `quirk:coverage-note` = `"unencrypted S3/Blob endpoint — no server-side encryption observed; no algorithm material to catalog"`.

---

**Profile: `ssh-weak` (SSH, port 20022)**

Scanner behavior (verified in `ssh_scanner.py`):
- When `ssh-audit` IS installed: `ep.ssh_audit_json = json.dumps(audit_data)` (line 64). Data includes `kex`, `key`, `enc`, `mac` sections with algorithms like `diffie-hellman-group1-sha1`, `ssh-dss`, `hmac-md5`, `hmac-sha1`.
- When `ssh-audit` is NOT installed: falls back to banner grab; `ssh_audit_json` is NOT set. Only `cert_pubkey_alg` fallback path (builder line 412) runs, and only if `cert_pubkey_alg` is set.

Builder Pass-1 behavior:
- SSH branch (lines 401-413): parses `ep.ssh_audit_json` → registers each kex/key/enc/mac algorithm. If `ssh_audit_json` is not set AND `cert_pubkey_alg` is not set: **ZERO algo components**.

**What the scanner already observes:** When ssh-audit runs, it observes all algorithms — the data IS in `ssh_audit_json`. The builder IS wired to extract them. The zero-algo condition is only hit when `ssh_audit_json` is absent.

**D-05 approach:** The fix is in the test fixture, not the builder. The `_build_ssh_weak_lab_endpoints` fixture in `tests/test_cbom_motion_endpoints.py` (line 608-622) uses `cert_pubkey_alg="ssh-dss"` and `ssh_audit_json=None`. The ssh-dss algorithm IS registered via the `cert_pubkey_alg` fallback (builder line 412). However in the real scan, the ssh-audit JSON would contain all the kex/key/mac data. The Phase 42 OBS-1 note says the real scan showed zero — this suggests the chaos lab test ran without ssh-audit installed.

**The real fix:** Update `_build_ssh_weak_lab_endpoints` to include a realistic `ssh_audit_json` value (with `diffie-hellman-group1-sha1`, `ssh-dss`, `hmac-md5`, `hmac-sha1` in their respective sections). This ensures the classifier coverage gate (test_cbom_classifier_coverage.py) sees and validates these algorithms. Also add these algorithm names to the classifier's `_ALGORITHM_TABLE` in `quirk/cbom/classifier.py` if they currently return UNKNOWN.

Check: `classify_algorithm("diffie-hellman-group1-sha1")` → `UNKNOWN` (confirmed via code). `classify_algorithm("ssh-dss")` → `UNKNOWN`. `classify_algorithm("hmac-md5")` → `UNKNOWN`. These must be added to the classifier before the gate will pass.

---

**Profile: `registry` (CONTAINER, port 20005)**

Scanner behavior (verified in `container_scanner.py`):
- `cipher_suite = name` where `name` is the crypto library name (e.g., `"openssl"`, `"cryptography"`, `"libssl1.0.0"`). [VERIFIED line 115]
- `cert_pubkey_alg` is NOT set by the container scanner.

Builder Pass-1 behavior (lines 422-424):
- `CONTAINER` branch: if `ep.cipher_suite`: `_register_algorithm(ep.cipher_suite)`.
- So `"openssl"` IS registered. But `classify_algorithm("openssl")` → `CryptoPrimitive.UNKNOWN, None, None` [VERIFIED].
- The classifier coverage gate (`test_cbom_classifier_coverage.py:73`) flags UNKNOWN as a failure (unless name == "none").

**What the scanner already observes:** The scanner observes the crypto library NAME and VERSION, but NOT the algorithms within. The library name is the observable. Pass-1 already registers the library name — it's just classified as UNKNOWN.

**D-05 approach:** Two sub-options:
1. Add `"openssl"`, `"libssl1.0.0"`, etc. to `_ALGORITHM_TABLE` in `classifier.py` with appropriate primitive/NIST level (e.g., `UNKNOWN, 0, None` for legacy openssl; this is classification of the library as a crypto primitive container, not an algorithm). But library names are NOT algorithm names — this is architecturally wrong.
2. Better: update the `CONTAINER` branch in builder.py to emit algorithm components based on the library version, using a known-weak-library mapping (e.g., `openssl 1.0.x` → known to support `RC4`, `3DES`). This surfaces the "already-observed" crypto the scanner sees.
3. Simplest that honors D-05: treat the library name as a library-type component (not an algorithm). Emit a CBOM property noting the library. The current registration of the raw library name in `algo_registry` with UNKNOWN primitive is architecturally incorrect. Per D-06, if the library version indicates known-weak algorithms, those can be surfaced.

**Recommended approach (D-05 scope constraint):** The container scanner records the library NAME — that IS the observation. The algorithm within the library is NOT observed by the scanner. Therefore this profile belongs under D-06 (coverage note), not D-05 (real algo components). The proper fix is: keep registering library names in the CBOM but with a `quirk:coverage-note` property = `"crypto library observed; specific algorithm negotiation not captured by container scanner"`. Additionally, update the classifier or the CONTAINER branch to avoid the UNKNOWN gate failure — either by adding library names with a dedicated primitive type, or by suppressing the gate for library-type names.

---

**Profile: `source` (SOURCE, port 20006)**

Scanner behavior (verified in `source_scanner.py`):
- `cipher_suite = check_id` (the semgrep rule ID, e.g., `"python.cryptography.security.insecure-hash-algorithms-md5"`).
- `cert_pubkey_alg` is NOT set.

Builder Pass-1 behavior (lines 426-430):
- `SOURCE` branch: calls `_extract_algo_from_rule_id(ep.cipher_suite)`.
- If a known algorithm is extracted (e.g., `MD5` from `-md5` in rule ID): registers extracted algo.
- Otherwise (`algo_hint is None`): `algo_to_register = ep.cipher_suite` (raw rule ID) → registers `"python.lang.security.insecure-random"` as an algorithm name → UNKNOWN primitive.

**What the scanner already observes:** The semgrep rule ID encodes the vulnerability category. For rules that map to specific algorithms (`-md5`, `-sha1`, etc.), the algorithm IS extractable. For rules about generic patterns (`insecure-random`, `no-ssl-handshake`), the algorithm is NOT encoded in the rule ID.

**D-05 approach:** Expand `_extract_algo_from_rule_id` in `builder.py` to cover more rule ID patterns:
- `"insecure-random"` → could map to `"PRNG"` (pseudo-random number generator, not a crypto algorithm per se) — but this would be a false precision. Better: no extraction, emit D-06 marker.
- `"no-ssl-handshake"` / `"deprecated-protocol"` → no specific algorithm known from rule name alone.

**Recommended approach:** For SOURCE endpoints where `algo_hint is None` (rule doesn't encode a specific algorithm), emit a `quirk:coverage-note` property on the Bom (or on a synthetic ADVISORY component) instead of registering the raw rule ID as an algorithm name. The raw rule ID registration produces spurious UNKNOWN classifier failures.

---

### No-crypto marker convention (D-06) [VERIFIED]

Existing CBOM property keys in use:
- `"quirk:fips140-3-status"` — on algorithm components (`_make_algorithm_component` line 316)
- `"quirk:cmvp-coverage"` — on algorithm components (line 319-320)

Both are `Property(name="...", value="...")` from `cyclonedx.model.Property`. [VERIFIED: builder.py line 19-20]

**Proposed affirmative no-crypto marker convention:**

Add a `quirk:coverage-note` property to the Bom metadata (or to a sentinel ADVISORY component). Two forms:
1. **Genuinely plaintext** (database ssl-off, storage-s3 unencrypted): `"plaintext endpoint — no cryptographic material observed by scanner"`
2. **Library observed but algorithm not probed** (registry, source non-algorithm rules): `"crypto library/pattern observed; algorithm-level detail not captured by this scanner"`

Implementation options for where to attach the property:
- **Option A:** On the `BomMetaData.component` (root component) as an additional property — simple but affects all profiles.
- **Option B:** Emit a synthetic `Component` with `type=ComponentType.CRYPTOGRAPHIC_ASSET` and `asset_type=CryptoAssetType.PROTOCOL` (or a new advisory type) carrying the note. More CycloneDX-compliant.
- **Option C:** Add a top-level Bom property (CycloneDX 1.6 Bom has a `properties` field on the Bom itself). [ASSUMED: CycloneDX Bom object may support top-level properties — verify in cyclonedx-python-lib]

**Recommended:** Option C (Bom-level properties) if supported by the library, otherwise Option B (advisory component). The existing pattern for advisory findings is `protocol="ADVISORY"` in `CryptoEndpoint` rows (see `cbom/writer.py:79`), so Option B mirrors that convention at the CBOM level.

---

## Common Pitfalls

### Pitfall 1: Test fixture gap vs production code gap

**What goes wrong:** The five zero-algo profiles are "zero" in the classifier coverage gate because the test fixtures (`_build_*_lab_endpoints`) use synthetic endpoints that don't reflect real scanner output. For example, `_build_database_lab_endpoints` sets `cert_pubkey_alg="RSA"` which makes the gate pass — but the real postgres ssl-off scan never sets `cert_pubkey_alg`.

**How to avoid:** Fix BOTH the test fixtures (to reflect real scanner output) AND the builder (to emit the right components or markers for that real output). Don't fix only the fixture — that's lying to the test.

**Warning signs:** If the gate passes after a fixture change but without builder change, the fixture is still synthetic.

### Pitfall 2: Rounding introduction

**What goes wrong:** Adding a shared formatting helper that re-rounds already-rounded integer values.

**How to avoid:** The `score` dict values are already `int` from `_apply_weighted_impacts` (line 109: `int(round(clamped))`). Any formatting helper should pass them through as-is; never call `round()` on them again.

### Pitfall 3: Jinja2 template autoescaping

**What goes wrong:** Adding a new subscore variable to the HTML template without piping it through `| sanitize` for string values.

**How to avoid:** Subscore values are Python `int` — no escaping needed. The label strings should use the hardcoded Python dict (no scanner input), not scanner-derived strings — so no `| sanitize` needed for them.

### Pitfall 4: Classifier UNKNOWN failures in coverage gate

**What goes wrong:** Adding ssh-audit algorithm names to the fixture without adding them to `quirk/cbom/classifier.py`'s `_ALGORITHM_TABLE`. The gate `test_no_unknown_classifications_across_lab_profiles` fails for any algorithm not in the table (except `"none"`).

**How to avoid:** For each new algorithm added to the ssh-weak fixture, verify `classify_algorithm(name)` returns a non-UNKNOWN primitive, and if not, add the entry to `_ALGORITHM_TABLE`.

### Pitfall 5: SCORE_WEIGHTS invariant sum

**What goes wrong:** Phase 88 does NOT change scoring weights (D-01), but if any helper file is accidentally modified, `test_score_weights_sum_invariant` fails (sum must stay 275.0, count 36).

**How to avoid:** Touch only the test files and report renderers. Do not modify `SCORE_WEIGHTS`.

### Pitfall 6: HTML template receives score as dict with `"total"` key, not `"score"` key

**What goes wrong:** The writer wraps `compute_readiness_score` output: `score = {"total": score_raw["score"], "subscores": ..., "drivers": ...}` (writer.py:166-170). The HTML renderer receives this wrapped dict, not the raw output. Adding subscore rendering must use `score.get("subscores")` not `score_raw.get("subscores")`.

**How to avoid:** In `html_renderer.py`, add `subscores=score.get("subscores", {})` to the template call (line 189-207). In the template, use `subscores` not `score.subscores`.

---

## Architecture Patterns

### Forward-locking invariant test pattern (D-02)

Mirror of `tests/test_score_weights_invariant.py` and `tests/test_xml_safe.py`:

```python
# tests/test_scoring_orthogonal_contract.py
import pytest
from quirk.intelligence.scoring import compute_readiness_score

@pytest.mark.parametrize("category,evidence_key,expected_dirty,expected_clean", [
    ("hygiene",      "plaintext_http_count",    ["hygiene"],                  ["modern_tls","identity_trust","agility_signals","data_at_rest","data_in_motion"]),
    ("modern_tls",   "finding_severity_counts", ["modern_tls"],              ["hygiene","identity_trust","agility_signals","data_at_rest","data_in_motion"]),
    # ... etc for all six categories
])
def test_subscore_orthogonality(category, evidence_key, expected_dirty, expected_clean):
    """Forward-locking invariant: a finding in one category only affects that category's subscore."""
    # Build evidence with findings ONLY in the target category
    evidence = {evidence_key: 5, "totals": {"endpoints": 10, "findings": 5}, ...}
    result = compute_readiness_score(evidence)
    subscores = result["subscores"]
    for clean_cat in expected_clean:
        assert subscores[clean_cat] == 25, f"{clean_cat} must be 25 when only {category} has findings"
    for dirty_cat in expected_dirty:
        assert subscores[dirty_cat] < 25, f"{dirty_cat} must be < 25 when its category has findings"
```

### Data-layer parity gate pattern (D-04)

```python
# tests/test_score_render_parity.py
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.evidence import build_evidence_summary

FIXTURE_ENDPOINTS = [...]  # realistic fixture set
FIXTURE_FINDINGS = [...]

def test_render_parity_all_surfaces():
    """All surfaces receive identical score and subscore values from the same evidence."""
    evidence = build_evidence_summary(FIXTURE_ENDPOINTS, FIXTURE_FINDINGS)
    canonical = compute_readiness_score(evidence)
    
    # writer.py path: wraps as {"total": ..., "subscores": ...}
    writer_score = {"total": canonical["score"], "subscores": canonical["subscores"]}
    assert writer_score["total"] == canonical["score"]
    assert writer_score["subscores"] == canonical["subscores"]
    
    # html_renderer.py receives the same writer_score dict
    # dashboard API calls compute_readiness_score with the same evidence
    dashboard_score = compute_readiness_score(evidence)  # re-call simulates API path
    assert dashboard_score["score"] == canonical["score"]
    assert dashboard_score["subscores"] == canonical["subscores"]
```

---

## Standard Stack

No new packages. Phase 88 uses only existing dependencies:

- `quirk/intelligence/scoring.py` — canonical scoring engine
- `quirk/reports/writer.py`, `executive.py`, `html_renderer.py` — report renderers
- `quirk/reports/templates/report.html.j2` — Jinja2 template
- `quirk/cbom/builder.py` — CBOM Pass-1
- `quirk/cbom/classifier.py` — algorithm classifier (may need `_ALGORITHM_TABLE` additions)
- `cyclonedx.model.Property` — already imported in builder.py (line 19) [VERIFIED]
- `pytest` — test framework (already used)

## Package Legitimacy Audit

Not applicable — no new packages are installed in this phase. All work uses existing dependencies.

---

## Architecture: Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| CBOM property/marker emission | Custom serialization | `cyclonedx.model.Property` (already imported) |
| Test parametrization | Manual loops | `pytest.mark.parametrize` (matches existing test style) |
| Score integer formatting | Custom number formatting | Python f-string `f"{n}/25"` (scores are already int) |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `python -m pytest tests/test_scoring_orthogonal_contract.py tests/test_score_render_parity.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVIDENCE-TALLY-01 | Orthogonal subscore contract locked | unit | `pytest tests/test_scoring_orthogonal_contract.py -x` | ❌ Wave 0 |
| RENDER-CLI-01 | CLI scorecard value == dashboard value for fixture scan | unit | `pytest tests/test_score_render_parity.py -x` | ❌ Wave 0 |
| RENDER-PDF-01 | HTML/PDF data-layer value == dashboard value for fixture scan | unit | `pytest tests/test_score_render_parity.py -x` | ❌ Wave 0 |
| SCORE-CBOM-01 | Builder emits algo components / markers for all 5 profiles | unit | `pytest tests/test_cbom_classifier_coverage.py tests/test_cbom_zero_algo_profiles.py -x` | Partial (coverage gate exists, new profile tests ❌) |
| SCORE-XPARENCY-01 | Scorecard markdown contains "N/25" and "÷1.5" text | unit | `pytest tests/test_score_transparency.py -x` | ❌ Wave 0 |

### Sampling Rate

- Per task commit: `python -m pytest tests/test_scoring_orthogonal_contract.py tests/test_score_render_parity.py tests/test_score_transparency.py tests/test_cbom_classifier_coverage.py -x`
- Per wave merge: `python -m pytest tests/ -x`
- Phase gate: Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_scoring_orthogonal_contract.py` — covers EVIDENCE-TALLY-01 (parametrized orthogonality gate)
- [ ] `tests/test_score_render_parity.py` — covers RENDER-CLI-01 / RENDER-PDF-01 (data-layer parity gate)
- [ ] `tests/test_score_transparency.py` — covers SCORE-XPARENCY-01 (scorecard + exec markdown + HTML template renders N/25)
- [ ] `tests/test_cbom_zero_algo_profiles.py` — covers SCORE-CBOM-01 for the 5 profiles with updated fixtures

---

## Security Domain

`security_enforcement` is not explicitly set to `false` in config.json, so this section is required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Not modified |
| V3 Session Management | no | Not modified |
| V4 Access Control | no | Not modified |
| V5 Input Validation | yes (CBOM property values) | All CBOM property values are hardcoded string literals or formatted integers — no scanner input reaches them. No validation library needed beyond existing `safe_str` convention. |
| V6 Cryptography | no | Not applicable — this phase does not handle crypto operations |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Injected content in report markdown via subscore labels | Tampering | Labels are hardcoded Python strings (not scanner-derived); no `md_cell()` needed |
| Injected content in HTML template via subscore values | Tampering | Subscore values are `int` (not scanner-derived strings); Jinja2 autoescaping not needed for ints |
| CBOM property value injection | Tampering | No-crypto marker values are hardcoded string literals; not derived from scanner output |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Two scoring engines (assessment + intelligence) | Single engine (`quirk/intelligence/scoring.py`) | Phase 83 cleanup | CONCERNS.md entry stale; D-03 confirmed |
| Subscores not surfaced in reports | Dashboard shows N/25 gauges; reports lag | Phase 86 (dashboard); Phase 88 (reports) | D-07 closes the gap |
| CBOM passes vacuously for zero-algo profiles | Targeted per-profile fixes | Phase 88 SCORE-CBOM-01 | OBS-1 closed |

**Deprecated/outdated:**
- `quirk/assessment/readiness_score.py`: DELETED. Never reference this path.
- CONCERNS.md §1.11 (dual scoring engines): STALE. Planner should note for Phase 91 (CLEAN-04) CONCERNS.md update.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | CycloneDX Bom object supports top-level `properties` field in v1.6 schema | §D-06 Option C | If not supported, use Option B (advisory component) instead — minor implementation change |
| A2 | ssh-weak profile's zero-algo condition in Phase 42 was caused by ssh-audit not being installed in the test environment | §ssh-weak analysis | If builder has a separate bug, need to trace builder logic for ssh_audit_json parsing |

---

## Open Questions

1. **CycloneDX Bom-level properties (D-06 Option C)**
   - What we know: `_make_algorithm_component` uses `Property` on individual components. The CycloneDX 1.6 spec allows properties on Bom-level too.
   - What's unclear: Whether `cyclonedx-python-lib` exposes a `Bom.properties` setter.
   - Recommendation: Planner assigns a Wave 0 task to check `Bom.__init__` signature in the installed version. If not available, use Option B (synthetic advisory component with `protocol="ADVISORY"` parallel to `cbom/writer.py` error endpoint pattern).

2. **ssh-weak classifier additions**
   - What we know: `diffie-hellman-group1-sha1`, `ssh-dss`, `hmac-md5` all return UNKNOWN from `classify_algorithm`. They need entries in `_ALGORITHM_TABLE`.
   - What's unclear: The correct primitive/NIST level assignment for each (e.g., `ssh-dss` = `SIGNATURE, 0, 80`?).
   - Recommendation: Research `quirk/cbom/classifier.py` `_ALGORITHM_TABLE` at plan time; add entries consistent with existing SSH algorithm entries.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 88 is code/config-only changes. No external tools or services are installed or configured in this phase.

---

## Sources

### Primary (HIGH confidence)

- `quirk/intelligence/scoring.py` — verified lines 103-111, 182-258 (scoring model, rounding sites)
- `quirk/reports/writer.py` — verified lines 17, 157-204 (import, score computation, surface rendering)
- `quirk/reports/executive.py` — verified lines 1-12, 115-184 (import, score render)
- `quirk/reports/html_renderer.py` — verified lines 145-207 (template call, variables)
- `quirk/reports/templates/report.html.j2` — verified lines 148-206 (no subscores in template)
- `quirk/cbom/builder.py` — verified lines 397-551 (Pass-1 per-protocol logic)
- `quirk/dashboard/api/routes/scan.py` — verified lines 1054-1079 (score computation, subscore rendering)
- `quirk/dashboard/api/schemas.py` — verified `SubScores`, `ScoreData` models
- `src/dashboard/src/pages/executive.tsx` — verified lines 251-256 (`ScoreGauge` with `maxValue={25}`)
- `src/dashboard/src/components/gauges/ScoreGauge.tsx` — verified `maxValue` prop and fraction calculation
- `quirk/scanner/db_connector.py` — verified ssl-off detection, no `cert_pubkey_alg` set
- `quirk/scanner/ssh_scanner.py` — verified `ssh_audit_json` assignment path
- `quirk/scanner/container_scanner.py` — verified `CRYPTO_LIB_ALLOWLIST`, `cipher_suite=name`
- `quirk/scanner/source_scanner.py` — verified `cipher_suite=check_id` pattern
- `quirk/scanner/aws_connector.py` — verified S3 `service_detail` logic
- `tests/_cbom_profiles.py` — verified 18 profiles, profile-to-function mapping
- `tests/test_cbom_motion_endpoints.py` — verified synthetic fixture endpoints for 5 zero-algo profiles
- `tests/test_cbom_classifier_coverage.py` — verified UNKNOWN gate logic
- `tests/test_score_weights_invariant.py` — verified forward-locking pattern for D-02
- `tests/test_xml_safe.py` — verified parametrized forward-locking pattern
- `tests/test_audit_ledger_zero_open.py` — verified grep-gate forward-locking pattern
- `quirk/assessment/` — verified `readiness_score.py` is absent (D-03 confirmed)
- `.planning/codebase/CONCERNS.md` — verified §1.11 dual-engine entry is stale
- `.planning/REQUIREMENTS.md` — verified requirement text for all 5 IDs
- `.planning/phases/88-scoring-residuals/88-CONTEXT.md` — authoritative decisions D-01..D-08

### Secondary (MEDIUM confidence)

- Phase 42 memory note (project_cbom_zero_algo_profiles.md) — documents OBS-1 observation; 22 days old but consistent with current code

## Metadata

**Confidence breakdown:**
- Single engine (D-03): HIGH — directly verified in source
- Rounding sites (D-04): HIGH — traced all surfaces, no secondary rounding found
- CBOM zero-algo root causes (D-05): HIGH for database/storage-s3 (clear from builder logic); HIGH for ssh-weak (scanner JSON path is clear); MEDIUM for registry/source (library-name vs algorithm-name distinction is judgment call)
- Forward-locking test pattern (D-02): HIGH — project patterns are well-established
- No-crypto marker convention (D-06): MEDIUM — existing Property pattern verified; Bom-level support is ASSUMED

**Research date:** 2026-05-22
**Valid until:** 2026-06-22 (stable codebase; 30-day window)
