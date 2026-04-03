# Phase 9: Scoring Consolidation - Research

**Researched:** 2026-04-03
**Domain:** Python refactoring — dual-path elimination, scoring engine extension, executive report migration
**Confidence:** HIGH (all findings sourced from direct codebase inspection)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Refactor `quirk/reports/executive.py` to call `build_evidence_summary(endpoints, findings)`
first, then call `intelligence/scoring.py::compute_readiness_score()`,
`intelligence/confidence.py::compute_confidence()`, and `intelligence/roadmap.py::build_phased_roadmap()`.
This is the same call sequence already used by `writer.py`. The executive summary markdown and
intelligence JSON will share the same source data and produce the same score.

**D-02:** Delete `quirk/assessment/readiness_score.py`, `quirk/assessment/confidence.py`,
`quirk/assessment/transition_planner.py`, and `quirk/assessment/interpretation_engine.py`.
Keep `quirk/assessment/operator_context.py` (used by `run_scan.py` for operator context prompts)
and `quirk/assessment/migration_advisor.py` (rules-based migration recommendations, no intelligence
equivalent exists).

**D-03:** Use NOW/NEXT/LATER format throughout. The executive summary markdown renders
`build_phased_roadmap()` output (same as intelligence JSON and HTML). Wave 1/2/3 format is retired.

**D-04:** Port the rich narrative logic from `assessment/interpretation_engine.py` into a new
function that takes `evidence: Dict` and `score: Dict` instead of `ReadinessScore` dataclass.
Preserve these elements: top-3 score driver analysis, TLS/SSH visibility framing (successful
handshake counts), TIMEOUT and NOT_TLS_ON_PORT event context, CRITICAL+HIGH severity summary.
This function lives in `intelligence/` or directly in `executive.py` — Claude's discretion on
placement.

**D-05:** Add per-profile weight multipliers to `intelligence/scoring.py`. Semantics:
- `strict` — `agility_*` and `identity_*` weights × 1.4
- `balanced` — base weights as currently defined in `SCORE_WEIGHTS` (1.0×)
- `lenient` — `agility_*` and `identity_*` weights × 0.7
- `hygiene_*` and `modern_tls_*` weights unchanged across all profiles

**D-06:** `compute_readiness_score()` accepts a new `profile: str | None = None` keyword
argument alongside the existing `weights: Mapping[str, float] | None = None`. Profile
multipliers are applied first; then `weights` (calibration_overrides) are merged on top —
user-specific overrides always win over profile defaults.

**D-07:** Wire `cfg.intelligence.profile` and `cfg.intelligence.calibration_overrides` into
both `compute_readiness_score()` call sites: `writer.py` (line 115) and the refactored
`executive.py`. Pass `profile=cfg.intelligence.profile` and
`weights=cfg.intelligence.calibration_overrides` (the latter may be None — the function
already handles None gracefully).

### Claude's Discretion

- Exact placement of the ported `build_interpretation()` logic (new file in intelligence/ or
  inline in executive.py)
- Precise weight multiplier values beyond the 1.4/1.0/0.7 anchors — tuning within that range
  is acceptable to achieve measurably different scores on the same scan data
- Whether to add a `--score-profile` flag passthrough test to the validate.py integration test
  added in Phase 8 D-02

### Deferred Ideas (OUT OF SCOPE)

- `assessment/operator_context.py` runtime prompts — assess whether fields feed scoring or are
  decorative; if decorative, consider removing in a future phase
- `scorecard.py` fate — currently orphaned (§1.8); Phase 9 may leave it as-is or consolidate
  into executive.py; out of scope unless it blocks the migration
- `intelligence/schema.py` typed Score inputs — available for repurposing but not required
  by Phase 9 success criteria; defer unless a natural use emerges during implementation
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SC-01 | Readiness score in executive summary markdown matches score in intelligence JSON and HTML report | D-01 wires executive.py to intelligence/scoring.py — same evidence dict, same function, same output |
| SC-02 | Roadmap in executive summary markdown is the same data as the roadmap artifact files | D-03 replaces Wave 1/2/3 with NOW/NEXT/LATER via `build_phased_roadmap()` in executive.py |
| SC-03 | `assessment/readiness_score.py`, `assessment/confidence.py`, `assessment/transition_planner.py` either removed or deprecated aliases | D-02 deletes all four compute modules; operator_context.py and migration_advisor.py survive |
| SC-04 | `profile: strict` produces measurably different score weights than `profile: lenient` on same scan data | D-05/D-06 add PROFILE_MULTIPLIERS to scoring.py; `agility_*` and `identity_*` keys change by ×1.4 vs ×0.7 |
| SC-05 | `calibration_overrides` set in config are applied to scoring engine weights at runtime | D-07 wires `cfg.intelligence.calibration_overrides` as `weights=` arg at both call sites |
</phase_requirements>

---

## Summary

Phase 9 is a surgical refactoring of `quirk/reports/executive.py` paired with a feature addition
to `quirk/intelligence/scoring.py`. There are no new scanners, no schema changes to scan output,
and no UI work. The phase resolves CONCERNS.md §4.1–4.3 (dual scoring paths), §1.7 (calibration
wiring), and §12.1 (calibration_overrides never applied).

The current state: `executive.py` imports from `assessment/` (four modules), while `writer.py`
imports from `intelligence/`. Both run on every scan, computing different scores, different
confidence values, and different roadmaps. The executive summary markdown and the intelligence JSON
show different numbers because they use different algorithms with different inputs. This phase
eliminates the `assessment/` compute modules and reroutes `executive.py` through the intelligence
call sequence, making all artifacts share one code path.

The second half of the phase wires profile-based weight multipliers that already exist in config
(`cfg.intelligence.profile`) but are currently cosmetic — stored, never applied to scoring. After
this phase, `strict` vs `lenient` will produce measurably different scores on identical scan data.

**Primary recommendation:** Implement as three sequential tasks — (1) extend scoring.py with profile
param, (2) refactor executive.py to use intelligence call sequence + ported narrative, (3) delete
the four assessment compute modules and update tests. Keep tasks small and independently testable.

---

## Architecture Patterns

### Current State (Dual Path)

```
run_scan.py
└── write_reports(cfg, endpoints, findings)
    ├── build_exec_markdown(cfg, endpoints, findings)    ← calls assessment/
    │   ├── assessment/readiness_score.compute_readiness_score(cfg, endpoints, findings)
    │   ├── assessment/transition_planner.build_transition_roadmap(cfg, endpoints, findings)
    │   ├── assessment/interpretation_engine.build_interpretation(cfg, endpoints, findings, score)
    │   └── assessment/confidence.compute_confidence(cfg, endpoints)
    │
    └── intelligence call sequence                       ← calls intelligence/
        ├── evidence = build_evidence_summary(endpoints, findings)
        ├── score_raw = compute_readiness_score(evidence)
        ├── conf_raw = compute_confidence(evidence)
        └── roadmap_raw = build_phased_roadmap(evidence, score_raw)
```

### Target State (Single Path)

```
run_scan.py
└── write_reports(cfg, endpoints, findings)
    ├── build_exec_markdown(cfg, endpoints, findings)    ← calls intelligence/ (same as below)
    │   ├── evidence = build_evidence_summary(endpoints, findings)
    │   ├── score_raw = compute_readiness_score(evidence, profile=..., weights=...)
    │   ├── conf_raw = compute_confidence(evidence)
    │   ├── roadmap_raw = build_phased_roadmap(evidence, score_raw)
    │   └── build_interpretation(evidence, score_raw)   ← ported narrative (intelligence/ or inline)
    │
    └── intelligence call sequence (unchanged)
        ├── evidence = build_evidence_summary(endpoints, findings)
        ├── score_raw = compute_readiness_score(evidence, profile=..., weights=...)
        ├── conf_raw = compute_confidence(evidence)
        └── roadmap_raw = build_phased_roadmap(evidence, score_raw)
```

### Recommended Project Structure (no changes needed)

The intelligence layer directory structure is already correct:

```
quirk/
├── intelligence/
│   ├── evidence.py         ← build_evidence_summary()
│   ├── scoring.py          ← compute_readiness_score() — add profile param here
│   ├── confidence.py       ← compute_confidence()
│   ├── roadmap.py          ← build_phased_roadmap()
│   ├── interpretation.py   ← NEW: build_interpretation(evidence, score) [option A]
│   └── ...
├── reports/
│   ├── executive.py        ← REFACTOR: wire to intelligence/, narrative inline or imported
│   └── writer.py           ← update two call sites: add profile= and weights= args
├── assessment/
│   ├── operator_context.py ← KEEP
│   ├── migration_advisor.py ← KEEP
│   ├── readiness_score.py  ← DELETE
│   ├── confidence.py       ← DELETE
│   ├── transition_planner.py ← DELETE
│   └── interpretation_engine.py ← DELETE (port logic first)
```

### Pattern 1: Profile Multiplier Table in scoring.py

The profile multipliers should be a module-level constant applied as a pre-pass before the
existing `weights` override logic. Profile keys map exactly to the weight key prefixes:

```python
# Source: quirk/intelligence/scoring.py — current SCORE_WEIGHTS keys
PROFILE_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "strict":   {"agility_": 1.4, "identity_": 1.4},
    "balanced": {"agility_": 1.0, "identity_": 1.0},
    "lenient":  {"agility_": 0.7, "identity_": 0.7},
}

def compute_readiness_score(
    evidence: Mapping[str, Any],
    *,
    profile: str | None = None,
    weights: Mapping[str, float] | None = None,
) -> Dict[str, Any]:
    w = dict(SCORE_WEIGHTS)
    # 1. Apply profile multipliers first
    prof = str(profile or "balanced").lower()
    if prof not in PROFILE_MULTIPLIERS:
        prof = "balanced"
    for prefix, factor in PROFILE_MULTIPLIERS[prof].items():
        for key in list(w):
            if key.startswith(prefix):
                w[key] = w[key] * factor
    # 2. User-specific overrides always win (existing logic)
    if weights:
        for k, v in weights.items():
            w[k] = _as_float(v)
    # ... rest of function unchanged ...
```

**SCORE_WEIGHTS keys that have `agility_` prefix:**
- `agility_high_impact_ratio` (14.0)
- `agility_unknown_ratio` (6.0)
- `agility_rsa_only_penalty` (8.0)
- `agility_has_ecdsa_bonus` (4.0)

**SCORE_WEIGHTS keys that have `identity_` prefix:**
- `identity_expired_ratio` (14.0)
- `identity_expiring_ratio` (7.0)
- `identity_self_signed_ratio` (9.0)
- `identity_mtls_ratio_bonus` (6.0)

Total affected weight sum: agility (32.0) + identity (36.0) = 68.0 points.
With `strict` (×1.4) vs `lenient` (×0.7): difference of ×0.7 on 68 base points = ~47.6 point
range on the weight table. In practice, actual score delta on non-trivial scan data will be
measurably different (easily 5–15+ points on realistic data). Satisfies SC-04.

### Pattern 2: Interpretation Port (assessment → intelligence)

The current `assessment/interpretation_engine.py::build_interpretation(cfg, endpoints, findings, score: ReadinessScore)`
takes a `ReadinessScore` dataclass. The port must replace the dataclass-specific access with
dict access. All the data is available in the evidence/score dicts.

Current dataclass access patterns and their dict equivalents:

| Old (ReadinessScore dataclass) | New (evidence + score dicts) |
|-------------------------------|------------------------------|
| `score.score` | `score_raw["score"]` |
| `score.rating` | `score_raw["rating"]` |
| `score.breakdown.drivers[:3]` | `score_raw["drivers"][:3]` where each driver is `{"reason": str, "points": int}` |
| `coverage.get("tls_success", 0)` | evidence has no direct `tls_success` key — must compute from `protocol_counts["TLS"]` or pass via a helper |
| `coverage.get("ssh_success", 0)` | same issue — derive from evidence or pass a coverage dict |
| `coverage.get("error_categories", {})` | no `error_categories` in evidence dict |

**Key gap:** The current `interpretation_engine.py` reads `score.breakdown.coverage` which contains:
- `tls_success` (TLS endpoints with no error)
- `ssh_success` (SSH endpoints with no error)
- `error_categories` (Counter of TIMEOUT, NOT_TLS_ON_PORT, etc.)

The evidence dict (`build_evidence_summary` output) does NOT have these fields directly.
Evidence has `protocol_counts: {"TLS": N, "SSH": N}` (total, not success-only) and
`scan_error: {"count": N, "rate": f}`. The `tls_success` and `error_categories` counts exist
in `assessment/readiness_score.py` but not in `intelligence/evidence.py`.

**Resolution options:**
1. Compute `tls_success`, `ssh_success`, `error_categories` locally inside `build_interpretation()`
   by accepting `endpoints` as an additional argument (not ideal — breaks the evidence-dict-only pattern)
2. Enrich `build_evidence_summary()` to add `tls_success_count`, `ssh_success_count`,
   and `error_category_counts` to the evidence dict (enables all downstream consumers to use it)
3. Accept `protocol_counts["TLS"]` as a proxy for `tls_success` (conservative — may overcount
   if TLS endpoints have scan errors, but evidence already has `scan_error.count`)

**Recommendation:** Option 3 is acceptable for Phase 9 — the executive markdown already shows
`{protocol_counts["TLS"]} TLS endpoints`. If precision is needed, option 2 is the correct
long-term design but adds scope. The interpretation narrative does not need exact success-only
counts; approximate framing ("X TLS endpoints in scope") preserves the consulting value.

Alternatively, the executive.py refactor receives `endpoints` as an argument (its signature
already includes it), so computing counts locally is feasible.

### Pattern 3: executive.py Refactored Call Sequence

Following `writer.py` lines 113–117 exactly:

```python
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.confidence import compute_confidence
from quirk.intelligence.roadmap import build_phased_roadmap
from quirk.assessment.migration_advisor import recommend_migration_paths
# plus build_interpretation (from intelligence/ or inline)

def build_exec_markdown(cfg, endpoints, findings) -> str:
    evidence = build_evidence_summary(endpoints, findings)
    score_raw = compute_readiness_score(
        evidence,
        profile=cfg.intelligence.profile,
        weights=cfg.intelligence.calibration_overrides or None,
    )
    conf_raw = compute_confidence(evidence)
    roadmap_raw = build_phased_roadmap(evidence, score_raw)
    recs = recommend_migration_paths(findings)
    interp = build_interpretation(evidence, score_raw)
    # ... render markdown using intelligence dicts ...
```

### Data Shape Reference for executive.py Migration

The executive.py markdown currently accesses `score.score`, `score.rating`,
`score.breakdown.drivers`, `score.breakdown.coverage.tls_success`, etc. from a
`ReadinessScore` dataclass. After migration, use these dict paths:

| Current (ReadinessScore) | Replacement (intelligence dicts) |
|--------------------------|----------------------------------|
| `score.score` | `score_raw["score"]` |
| `score.rating` | `score_raw["rating"]` |
| `score.breakdown.drivers[:8]` → `(name, pts)` | `score_raw["drivers"][:8]` → `{"reason": str, "points": int}` |
| `score.breakdown.coverage.get("tls_success", 0)` | derive locally from `endpoints` |
| `score.breakdown.coverage.get("ssh_success", 0)` | derive locally from `endpoints` |
| `score.breakdown.coverage.get("http_plain", 0)` | `evidence.get("plaintext_http_count", 0)` |
| `score.breakdown.coverage.get("unknown_open", 0)` | `evidence["protocol_counts"].get("UNKNOWN", 0)` |
| `conf.get("confidence_rating")` | `conf_raw["confidence_rating"]` |
| `conf.get("confidence_score")` | `conf_raw["confidence_score"]` |
| `conf.get("coverage_pct")` | not directly in conf_raw — compute as `(tls+ssh)/total*100` |
| `conf.get("tls_enum_coverage_pct")` | `evidence["tls_enum_coverage_pct"]` |
| `conf.get("blockers_top")` | not in intelligence confidence — compute locally |
| `roadmap.wave_1` / `wave_2` / `wave_3` | `roadmap_raw["items"]` filtered by `phase` field |

**Note on conf keys:** The `assessment/confidence.py::compute_confidence()` returns keys
`coverage_pct`, `tls_enum_coverage_pct`, `blockers_top` which executive.py currently reads.
The `intelligence/confidence.py::compute_confidence()` returns `confidence_score`,
`confidence_rating`, `factor_breakdown`. The executive.py render will need to adapt — derive
`coverage_pct` from evidence, and either drop `blockers_top` or derive it locally from endpoints.
The confidence section of the executive markdown should be updated to the intelligence model.

### Pattern 4: Intelligence JSON — calibration Block

The `validate.py::_validate_intelligence()` currently checks for `intel.get("calibration")`
and issues a warning if missing. The test data in `test_validate.py` includes a `calibration`
block with `profile` and `resolved` keys. Writer.py does NOT currently write this block (verified
— no `calibration` key in the `intelligence` dict assembled in writer.py). This means every real
scan currently produces a warning from `validate.py`.

After Phase 9 adds profile wiring to writer.py (D-07), writer.py should also add a `calibration`
block to the intelligence JSON output to satisfy the validator and make the profile visible in the
output artifact:

```python
intelligence = {
    ...
    "calibration": {
        "profile": cfg.intelligence.profile,
        "resolved": dict(w),  # the actual weights used
    },
    ...
}
```

This is a natural addition in the D-07 task and removes the validator warning.

### Anti-Patterns to Avoid

- **Keeping `(name, pts)` tuple driver format in new code:** `assessment/readiness_score.py`
  returns `drivers` as `List[Tuple[str, int]]`. `intelligence/scoring.py` returns `drivers` as
  `List[Dict{"reason": str, "points": int}]`. Ensure the executive.py migration uses the dict
  format throughout — do not re-introduce tuple unpacking.

- **Passing `cfg` into `compute_readiness_score()`:** The assessment layer took `cfg` as a
  positional arg; the intelligence layer takes only `evidence`. The profile and weights come from
  `cfg` at the call site, not inside the function. Keep the function signature clean.

- **Leaving the Wave 1/2/3 roadmap render in executive.py:** The current render iterates
  `roadmap.wave_1`, `roadmap.wave_2`, `roadmap.wave_3`. This must be completely replaced with
  iteration over `roadmap_raw["items"]` grouped by `phase` (NOW/NEXT/LATER). The Wave format
  is retired per D-03.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Evidence normalization | Custom field extraction in executive.py | `build_evidence_summary(endpoints, findings)` | Already handles all edge cases, datetime parsing, finding-target dedup |
| Score computation | New scoring formula | `compute_readiness_score(evidence, profile=, weights=)` | Verified correct, deterministic, tested |
| Confidence calculation | New heuristic | `compute_confidence(evidence)` | Evidence-dict interface already complete |
| Roadmap phasing | New roadmap logic | `build_phased_roadmap(evidence, score_raw)` | Handles min/max items, deterministic baseline |
| Profile multipliers | New config system | Extend SCORE_WEIGHTS with PROFILE_MULTIPLIERS constant | Two-layer approach (profile then override) is already designed |

---

## Common Pitfalls

### Pitfall 1: Driver Format Mismatch

**What goes wrong:** `executive.py` currently iterates `score.breakdown.drivers` as
`(label, pts)` tuples from the assessment layer. The intelligence layer returns
`[{"reason": "...", "points": N}]` dicts. Accidentally using tuple unpacking on the new format
will raise `TypeError` or silently render empty labels.

**Why it happens:** The two scoring systems have incompatible driver representations.

**How to avoid:** Use `d["reason"]` and `d["points"]` throughout the refactored executive.py.
Add a unit test that asserts the driver list items are dicts with those keys.

**Warning signs:** Rendering shows empty or "None" score driver labels in generated markdown.

---

### Pitfall 2: Confidence Field Key Mismatch

**What goes wrong:** `executive.py` reads `conf.get("coverage_pct")`, `conf.get("blockers_top")`,
and `conf.get("tls_enum_coverage_pct")`. These keys exist in `assessment/confidence.py` output
but NOT in `intelligence/confidence.py` output. After migration, these reads silently return None.

**Why it happens:** The two confidence engines return different key shapes.

**How to avoid:** Map each field explicitly during the refactor:
- `coverage_pct` → compute `(protocol_counts["TLS"] + protocol_counts["SSH"]) / totals["endpoints"] * 100`
- `tls_enum_coverage_pct` → `evidence["tls_enum_coverage_pct"]`
- `blockers_top` → derive locally if needed, or simplify the section

**Warning signs:** Confidence & Coverage section shows `None/100`, `None%`, or missing blockers.

---

### Pitfall 3: roadmap Dict vs Object Attribute Access

**What goes wrong:** `executive.py` currently accesses `roadmap.wave_1`, `roadmap.wave_2`,
`roadmap.wave_3` as dataclass attributes on `TransitionRoadmap`. After migration,
`build_phased_roadmap()` returns a dict with `roadmap_raw["items"]` (a flat list with a `phase`
field). Attribute access on a dict raises `AttributeError`.

**Why it happens:** `build_transition_roadmap()` returns a `TransitionRoadmap` dataclass;
`build_phased_roadmap()` returns a plain dict.

**How to avoid:** Filter `roadmap_raw["items"]` by `item["phase"]` for NOW/NEXT/LATER sections.
The item fields are `phase`, `title`, `why`, `owner_placeholder`, `dependencies`, `timeframe`.
Map the render accordingly — note the old format had `rationale`, `deliverable`, `owner_hint`,
`effort` which do not exist in intelligence roadmap items.

**Warning signs:** `AttributeError: 'dict' object has no attribute 'wave_1'` at report time.

---

### Pitfall 4: validate.py calibration Warning After Phase 9

**What goes wrong:** `validate.py` warns when `intel.get("calibration")` is missing or not a dict.
Writer.py currently does not write a `calibration` block. If D-07 adds profile wiring to
`compute_readiness_score()` calls but does not add a `calibration` block to the intelligence JSON,
every scan will continue to produce a validation warning.

**Why it happens:** `validate.py` was written with a `calibration` key in mind but writer.py
was never updated to write it.

**How to avoid:** As part of the D-07 wiring task, add a `calibration` block to the
`intelligence` dict in writer.py with `profile` and `resolved` (the actual weight dict used).

**Warning signs:** `validate.py` reports `intelligence.calibration missing/invalid` on all scans.

---

### Pitfall 5: Test Scope for Deletion of Assessment Modules

**What goes wrong:** Deleting the four assessment compute modules (D-02) will break
`test_scoring_consolidation.py` if it imports from assessment, or break `executive.py` tests
if they still import the old modules. The existing consolidation test already checks `writer.py`
imports only — it does not test `executive.py` imports.

**Why it happens:** `test_scoring_consolidation.py` was written before executive.py was migrated.

**How to avoid:** After migrating executive.py, extend `test_scoring_consolidation.py` (or add
a new test) to assert `executive.py` does NOT import from the four deleted modules and DOES import
from the intelligence layer. This test will then guard against regressions on both files.

**Warning signs:** `ImportError: cannot import name 'compute_readiness_score' from 'quirk.assessment.readiness_score'` when running executive.py tests.

---

### Pitfall 6: calibration_overrides Is an Empty Dict, Not None

**What goes wrong:** `config_from_dict()` initializes `overrides = {}` (empty dict) when
`calibration_overrides` is absent from YAML. Passing an empty dict `{}` as `weights={}` to
`compute_readiness_score()` triggers the `if weights:` branch but the loop does nothing —
this is harmless but slightly wasteful.

**Why it happens:** `config_from_dict()` normalizes `None` to `{}` for `calibration_overrides`.

**How to avoid:** Pass `weights=cfg.intelligence.calibration_overrides or None` at the call site
(already specified in D-07). An empty dict will coerce to `None`, skipping the override loop.

---

## Code Examples

### SCORE_WEIGHTS keys by prefix (verified from intelligence/scoring.py)

```python
# Source: quirk/intelligence/scoring.py lines 5–20
SCORE_WEIGHTS = {
    # hygiene_ prefix (unchanged across profiles)
    "hygiene_plaintext_http_ratio": 18.0,
    "hygiene_http_on_tls_ratio": 16.0,
    "hygiene_scan_error_rate": 6.0,
    # modern_tls_ prefix (unchanged across profiles)
    "modern_tls_legacy_versions_ratio": 14.0,
    "modern_tls_unknown_ratio": 6.0,
    "modern_tls_scan_error_rate": 5.0,
    # identity_ prefix (× multiplier by profile)
    "identity_expired_ratio": 14.0,
    "identity_expiring_ratio": 7.0,
    "identity_self_signed_ratio": 9.0,
    "identity_mtls_ratio_bonus": 6.0,
    # agility_ prefix (× multiplier by profile)
    "agility_high_impact_ratio": 14.0,
    "agility_unknown_ratio": 6.0,
    "agility_rsa_only_penalty": 8.0,
    "agility_has_ecdsa_bonus": 4.0,
}
```

### writer.py call site to update (D-07)

```python
# Source: quirk/reports/writer.py lines 114–117 (current)
evidence = build_evidence_summary(endpoints, findings)
score_raw = compute_readiness_score(evidence)           # ← add profile= and weights=
conf_raw = compute_confidence(evidence)
roadmap_raw = build_phased_roadmap(evidence, score_raw)

# After D-07:
evidence = build_evidence_summary(endpoints, findings)
score_raw = compute_readiness_score(
    evidence,
    profile=cfg.intelligence.profile,
    weights=cfg.intelligence.calibration_overrides or None,
)
conf_raw = compute_confidence(evidence)
roadmap_raw = build_phased_roadmap(evidence, score_raw)
```

Note: `write_reports()` already receives `cfg` as its first argument (line 91 signature:
`def write_reports(cfg, endpoints, findings, run_stats=None)`), so `cfg` is available.

### executive.py NOW/NEXT/LATER roadmap render (replaces wave_1/wave_2/wave_3)

```python
# After D-01 + D-03 migration
roadmap_items = roadmap_raw.get("items", [])

for phase_label in ("NOW", "NEXT", "LATER"):
    phase_items = [r for r in roadmap_items if r.get("phase") == phase_label]
    lines.append(f"### {phase_label}")
    for item in phase_items:
        lines.append(f"- **{item['title']}** — {item['why']}")
        lines.append(f"  - Owner: {item['owner_placeholder']} | Timeframe: {item['timeframe']}")
```

Roadmap item fields (from intelligence/roadmap.py final_items):
`phase`, `title`, `why`, `owner_placeholder`, `dependencies`, `timeframe`

### Narrative interpretation port (D-04)

The logic from `assessment/interpretation_engine.py` to port:

```python
# Current (takes ReadinessScore dataclass):
def build_interpretation(cfg, endpoints, findings, score: ReadinessScore) -> Dict:
    coverage = score.breakdown.coverage
    tls_ok = coverage.get("tls_success", 0)
    ssh_ok = coverage.get("ssh_success", 0)
    err_cats = coverage.get("error_categories", {})
    drivers_txt = "; ".join([f"{name} (-{pts})" for name, pts in score.breakdown.drivers[:3]])
    # ...

# Ported (takes evidence: Dict, score: Dict):
def build_interpretation(evidence: Dict, score: Dict, endpoints=None) -> Dict:
    tls_ok = len([e for e in (endpoints or [])
                  if getattr(e, "protocol", "") == "TLS" and not getattr(e, "scan_error", None)])
    ssh_ok = len([e for e in (endpoints or [])
                  if getattr(e, "protocol", "") == "SSH" and not getattr(e, "scan_error", None)])
    # Derive error categories from endpoints if needed
    drivers = score.get("drivers", [])[:3]
    drivers_txt = "; ".join([f"{d['reason']} (-{d['points']})" for d in drivers])
    # ...
```

The `build_exec_markdown(cfg, endpoints, findings)` signature already receives `endpoints`, so
passing it to `build_interpretation` is clean without changing the outer signature.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Wave 1/2/3 roadmap (assessment layer) | NOW/NEXT/LATER (intelligence layer) | Phase 9 | Unified roadmap format across all artifacts |
| assessment/ compute modules | intelligence/ evidence-dict pipeline | Phase 9 | Single score, single confidence, single roadmap |
| Profile cosmetic (stored, not applied) | Profile applied to weight multipliers | Phase 9 | `strict` vs `lenient` produces measurably different scores |
| calibration_overrides ignored | Overrides applied as weights= arg | Phase 9 | User config actually affects output |

**Deprecated after this phase:**
- `assessment/readiness_score.py`: Deleted. Import path `quirk.assessment.readiness_score` no longer valid.
- `assessment/confidence.py`: Deleted. Import path `quirk.assessment.confidence` no longer valid.
- `assessment/transition_planner.py`: Deleted.
- `assessment/interpretation_engine.py`: Deleted (logic ported to intelligence layer).

---

## Open Questions

1. **Confidence "blockers_top" display in executive markdown**
   - What we know: `executive.py` currently renders top visibility blockers from `assessment/confidence.py` which returns them explicitly. `intelligence/confidence.py` does not.
   - What's unclear: Whether the blockers display is worth preserving in the migrated executive.py. The data is available by iterating `endpoints` directly.
   - Recommendation: Derive blockers locally in executive.py from `endpoints` (5-line Counter), or simplify the section to omit them. Either is valid — this is Claude's discretion territory.

2. **coverage_pct field**
   - What we know: `executive.py` renders "Coverage: {coverage_pct}% (TLS+SSH successful / total in-scope endpoints)". The `intelligence/confidence.py` output does not expose this percentage directly.
   - What's unclear: Whether to compute it from `evidence` (straightforward: `(protocol_counts["TLS"] + protocol_counts["SSH"]) / totals["endpoints"] * 100`) or derive from `conf_raw["factor_breakdown"]["coverage_ratio"]["value"]`.
   - Recommendation: Use `conf_raw["factor_breakdown"]["coverage_ratio"]["value"] * 100` — this is exactly the coverage ratio the confidence engine computed, avoiding recomputation.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 9 is purely code refactoring and file deletion with no new external dependencies.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml (confirmed — `[tool.pytest.ini_options]` section) |
| Quick run command | `python3 -m pytest tests/test_scoring_consolidation.py tests/test_intelligence_scoring.py tests/test_validate.py -x` |
| Full suite command | `python3 -m pytest tests/ -x` |

### Current Test State (all passing before Phase 9 work)

14 tests pass across the three directly relevant test files:
- `tests/test_scoring_consolidation.py` (7 tests) — verifies writer.py import sources
- `tests/test_intelligence_scoring.py` (3 tests) — verifies scoring shape and determinism
- `tests/test_validate.py` (4 tests) — verifies artifact validation

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SC-01 | Score in exec markdown = score in intelligence JSON | unit | `python3 -m pytest tests/test_scoring_consolidation.py -x` | Wave 0 gap |
| SC-02 | Roadmap in exec markdown = roadmap artifact data | unit | `python3 -m pytest tests/test_scoring_consolidation.py -x` | Wave 0 gap |
| SC-03 | Four assessment compute modules deleted | unit (import check) | `python3 -m pytest tests/test_scoring_consolidation.py -x` | Partial — extend existing |
| SC-04 | strict != lenient score on same data | unit | `python3 -m pytest tests/test_intelligence_scoring.py -x` | Wave 0 gap |
| SC-05 | calibration_overrides applied at runtime | unit | `python3 -m pytest tests/test_intelligence_scoring.py -x` | Wave 0 gap |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/test_scoring_consolidation.py tests/test_intelligence_scoring.py tests/test_validate.py -x`
- **Per wave merge:** `python3 -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_scoring_consolidation.py` — extend to check executive.py imports (SC-01, SC-02, SC-03)
- [ ] `tests/test_intelligence_scoring.py` — add `test_profile_strict_scores_differently_from_lenient` (SC-04)
- [ ] `tests/test_intelligence_scoring.py` — add `test_calibration_overrides_applied` (SC-05)
- [ ] `tests/test_scoring_consolidation.py` — add `test_executive_uses_intelligence_roadmap_format` checking NOW/NEXT/LATER (SC-02)

---

## Project Constraints (from CLAUDE.md)

| Directive | Applies To |
|-----------|-----------|
| Follow PEP 8 for all Python changes | All new/modified .py files |
| Keep diffs minimal — avoid unnecessary refactors | Do not refactor files outside Phase 9 scope |
| After changes, run `python -m compileall` and relevant tests | Post each task |
| If detection logic changes, update `labs/*/expected_results.md` | N/A — no scanner changes in Phase 9 |
| Docs + Obsidian sync tasks required in every phase plan | Plan must include doc update and Obsidian vault sync tasks |

**Security:** No new dependencies introduced. No scanner changes. No credential handling changes.

---

## Sources

### Primary (HIGH confidence)

- Direct inspection of `quirk/reports/executive.py` — confirmed all imports and call signatures
- Direct inspection of `quirk/reports/writer.py` — confirmed intelligence call sequence at lines 113–117
- Direct inspection of `quirk/intelligence/scoring.py` — confirmed `SCORE_WEIGHTS` dict, key prefixes, existing `weights` parameter
- Direct inspection of `quirk/intelligence/confidence.py` — confirmed output key shape (confidence_score, confidence_rating, factor_breakdown)
- Direct inspection of `quirk/intelligence/roadmap.py` — confirmed item schema (phase, title, why, owner_placeholder, dependencies, timeframe)
- Direct inspection of `quirk/intelligence/evidence.py` — confirmed output keys available to executive.py
- Direct inspection of `quirk/assessment/interpretation_engine.py` — confirmed ReadinessScore dataclass access patterns to port
- Direct inspection of `quirk/assessment/readiness_score.py` — confirmed dataclass structure
- Direct inspection of `quirk/assessment/confidence.py` — confirmed output keys (coverage_pct, blockers_top) that executive.py reads
- Direct inspection of `quirk/config.py` — confirmed IntelligenceCfg fields: profile, calibration_overrides
- Direct inspection of `quirk/validate.py` — confirmed calibration block expectation and current validate logic
- Direct inspection of all three test files — confirmed 14 tests GREEN, gaps identified
- Direct inspection of `.planning/codebase/CONCERNS.md` — confirmed §4.1–4.3, §1.7, §12.1 root causes

### Secondary (MEDIUM confidence)

- None required — all research sourced from direct codebase inspection

---

## Metadata

**Confidence breakdown:**
- Code paths and call sequences: HIGH — read all source files directly
- Profile multiplier semantics: HIGH — SCORE_WEIGHTS keys confirmed by inspection
- Test coverage gaps: HIGH — ran test suite, confirmed 14 tests pass
- Narrative port complexity: MEDIUM — tls_success/error_categories gap identified, two viable resolutions documented

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (stable internal codebase, no external library changes)
