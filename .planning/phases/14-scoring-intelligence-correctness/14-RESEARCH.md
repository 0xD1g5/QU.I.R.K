# Phase 14: Scoring & Intelligence Correctness - Research

**Researched:** 2026-04-06
**Domain:** Python scoring engine, test-driven correctness, FastAPI dashboard
**Confidence:** HIGH

## Summary

Phase 14 fixes four discrete correctness bugs in the scoring and intelligence pipeline using the
same 2-plan TDD structure as Phase 12. All four bugs are in existing code; no new modules are
introduced. Research involved reading every canonical file from the CONTEXT.md, running the live
test suite (215/215 passing baseline), and executing live code probes to confirm current runtime
behavior for each SCORE requirement.

The most important finding is that **SCORE-01 and SCORE-03 are already functionally correct** in
their core logic — the TDD RED tests must be written to prove the existing behavior meets the
directional D-03 criterion (not just inequality) and the exact pattern-matching success against
every risk_engine title. SCORE-02 and SCORE-04 are genuine bugs requiring code changes. One
critical discrepancy from CONTEXT.md D-07 was found: the intelligence JSON stores the scan-time
profile at `calibration.profile`, NOT `assessment.profile` as stated in the CONTEXT.md.

**Primary recommendation:** Plan 1 writes failing RED assertions for all four requirements;
Plan 2 removes the delta parameter (SCORE-02) and wires profile into the dashboard call
(SCORE-04). The RED tests for SCORE-01 and SCORE-03 may become GREEN immediately, which is
expected — they become permanent regression guards.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Test Plan Structure**
- D-01: 2-plan TDD approach matching Phase 12 pattern.
  - Plan 1: RED scaffold — write failing tests that prove each of the 4 SCORE bugs exists
    (SCORE-01 through SCORE-04). Tests must fail before any fixes land.
  - Plan 2: GREEN fixes — implement changes that make all RED tests pass.

**SCORE-01: Calibration Profile Application**
- D-02: The `PROFILE_MULTIPLIERS` structure and `profile` parameter exist in
  `intelligence/scoring.py`. Phase 9 also wired `writer.py` to pass `profile=cfg.intelligence.profile`.
  Plan 1 must prove whether the end-to-end path actually produces measurably different scores
  for `strict` vs `lenient` on identical scan data. If the structure is already correct,
  the RED test becomes the permanent regression guard.
- D-03: Success criterion: `strict` profile produces a higher combined `agility_*` +
  `identity_*` weight contribution than `lenient` on the same evidence dict, measurable in the
  returned `score["total"]`.

**SCORE-02: validate.py Artifact List**
- D-04: Remove the `require_delta_if_baseline` logic entirely from `validate.py`. Delta
  reports are not implemented — this parameter causes permanent validation failures when a
  baseline intelligence JSON exists. `validate_run()` should validate only what
  `write_reports()` actually produces.
- D-05: After removal, the `expected_files` list (findings, executive-summary,
  technical-findings, scorecard, roadmap, run-stats, cbom.json, cbom.xml) should be verified
  against the actual `write_reports()` output paths. Remove any artifact from the list that
  `write_reports()` doesn't reliably produce.

**SCORE-03: migration_advisor Pattern Matching**
- D-06: `migration_advisor.py` uses substring matching (`"legacy tls" in title.lower()`).
  `risk_engine.py` emits `"Legacy TLS versions allowed (TLS 1.0/1.1)"` — this does match after
  `.lower()`. The RED test must confirm whether migration recommendations actually surface in
  practice by running `recommend_migration_paths()` with a representative findings list from
  `risk_engine.py`. If there is a mismatch on another pattern (e.g., "plaintext http", "ssh",
  "quantum"), the test will surface it; fix the pattern string to match exactly.

**SCORE-04: Dashboard Profile Propagation**
- D-07: The dashboard's `quirk/dashboard/api/routes/scan.py` (line 329-330) calls
  `compute_readiness_score(evidence)` without a `profile` kwarg. Fix: read the `profile` value
  from the stored `intelligence-*.json` file (field: `assessment.profile`, written by
  `writer.py` line 153), then pass it as `compute_readiness_score(evidence, profile=stored_profile)`.
- D-08: Do NOT re-read `config.yaml` at dashboard request time — the config could change
  after a scan was stored, causing dashboard score to drift from the CLI report score.
  The scan-time profile is the authoritative source.

### Claude's Discretion
- Exact structure of the RED test file(s) — one test file per bug or a single
  `test_scoring_correctness.py` covering all four
- Whether to use fixtures from existing test infrastructure or inline minimal evidence dicts
- Exact line removal scope in validate.py delta logic (function signature vs body)

### Deferred Ideas (OUT OF SCOPE)
- Score transparency in reports — Add a scoring methodology section to executive summaries
  explaining how profile weights affect the score, what score ranges map to readiness levels
  (e.g., 80-100 = high, 60-79 = medium, <60 = low), and which subscores contributed most.
  Deferred to backlog at medium priority. User will review Phase 14 output first.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCORE-01 | Calibration profile (`lenient/balanced/strict`) is applied to weight multipliers in `compute_readiness_score()` | PROFILE_MULTIPLIERS and profile kwarg exist and work; RED test must verify directional correctness (strict < lenient on penalized evidence) |
| SCORE-02 | `validate.py` checks for artifacts that `write_reports()` actually produces (no permanent validation failure on every scan) | `require_delta_if_baseline` param exists in function signature but is UNUSED in body; main() passes it via `--no-require-delta` CLI arg; both must be removed |
| SCORE-03 | `migration_advisor.py` finding pattern strings match `risk_engine.py` finding titles so legacy TLS migration recommendations surface correctly | Live probe confirms all patterns match; RED test verifies full recommendation list against every risk_engine title |
| SCORE-04 | Dashboard passes the scan-time profile kwarg to `compute_readiness_score()` so dashboard and CLI report scores match | Dashboard call at line 329-330 is missing profile kwarg; intelligence JSON stores profile at `calibration.profile` (NOT `assessment.profile`); dashboard needs output dir access mechanism |
</phase_requirements>

---

## Standard Stack

### Core (already in project)
| Module | Location | Purpose |
|--------|----------|---------|
| `compute_readiness_score` | `quirk/intelligence/scoring.py` | Primary scoring function — profile + weights params already exist |
| `PROFILE_MULTIPLIERS` | `quirk/intelligence/scoring.py` | `strict: 1.4x, balanced: 1.0x, lenient: 0.7x` on `agility_` and `identity_` prefixed weights |
| `validate_run` | `quirk/validate.py` | Artifact validation called from `run_scan.py` after `write_reports()` |
| `recommend_migration_paths` | `quirk/assessment/migration_advisor.py` | Pattern-matches finding titles, emits migration paths for executive report |
| `get_latest_scan` route | `quirk/dashboard/api/routes/scan.py:291` | Dashboard endpoint — computes score from evidence without profile |
| `_latest_intelligence` | `quirk/validate.py:43` | Already implemented — finds most recent intelligence JSON by mtime |

### Test Infrastructure
| File | Purpose | Status |
|------|---------|--------|
| `tests/test_intelligence_scoring.py` | Scoring unit tests including ProfileWeightTests | 8 tests, all GREEN |
| `tests/test_scoring_consolidation.py` | Import-level correctness guards for writer.py/executive.py | 20 tests, all GREEN |
| `tests/test_validate.py` | validate_run and _latest_intelligence tests | 4 tests, all GREEN |
| `tests/test_dashboard_api.py` | Dashboard API integration tests | 7 tests, all GREEN |

**Baseline:** 215/215 tests passing before Phase 14 begins.

### No External Dependencies
This phase is purely internal Python code fixes. No new packages required.

---

## Architecture Patterns

### Pattern 1: Phase 12 TDD — RED Scaffold then GREEN Fix

Plan 1 writes tests that assert what SHOULD be true after the fix. Tests fail before fixes land.
Plan 2 implements fixes and removes any `@pytest.mark.xfail` markers (or replaces assertion polarity).

The Phase 12 RED test pattern used either:
- `@unittest.expectedFailure` for tests known to fail before implementation
- Direct assertions that fail against current code (simpler, preferred for small fixes)

For Phase 14, the preferred RED pattern is **direct assertions that fail before the fix**.
Example: `assert 'require_delta_if_baseline' not in inspect.signature(validate_run).parameters`
This fails now (param exists) and passes after removal.

### Pattern 2: Intelligence JSON Field Access

The intelligence JSON written by `writer.py` has this top-level structure:
```python
{
    "intelligence_version": "...",
    "assessment": {
        "name": ...,
        "owner": ...,
        "data_classification": ...,
        "timezone": ...,
    },
    "evidence_summary": {...},
    "score": {"total": ..., "subscores": {...}, "drivers": [...]},
    "confidence": {...},
    "roadmap": {...},
    "calibration": {           # <-- profile lives HERE
        "profile": "strict",   # <-- the field to read for SCORE-04
        "overrides_applied": False,
    }
}
```

**CRITICAL DISCREPANCY:** CONTEXT.md D-07 states the profile field is `assessment.profile`.
This is incorrect. The actual field written by `writer.py` line 152-155 is `calibration.profile`.
The Plan 2 implementation for SCORE-04 MUST read `intel_data["calibration"]["profile"]`, NOT
`intel_data["assessment"]["profile"]`.

### Pattern 3: Dashboard Route — Reading Intelligence JSON

The dashboard currently has no mechanism to locate the output directory. The `get_latest_scan`
route at `quirk/dashboard/api/routes/scan.py:291` works entirely from SQLite (via `get_db()`).

To read the intelligence JSON, the SCORE-04 fix must:
1. Determine the output directory — use `QUIRK_OUTPUT_DIR` env var with `./quirk-output` as default
   (matching `config_template.yaml: output.directory: "./quirk-output"`)
2. Call `_latest_intelligence(output_dir)` from `quirk.validate` (already implemented, sorts by mtime)
3. Load the JSON and extract `calibration.profile`
4. Pass as `compute_readiness_score(evidence, profile=stored_profile)`
5. Wrap entire block in `try/except Exception` — if intelligence JSON is absent or unreadable,
   fall back to `profile=None` (balanced default), matching existing graceful degradation pattern

This is consistent with `QUIRK_DB_PATH` pattern already in `quirk/dashboard/api/deps.py:11`.

### Pattern 4: validate_run Signature Cleanup (SCORE-02)

Current state:
```python
def validate_run(output_dir: Path, require_delta_if_baseline: bool = True) -> ValidationResult:
    # body never references require_delta_if_baseline
```

`main()` also passes `not args.no_require_delta` as the second positional argument to `validate_run`.

Fix scope:
1. Remove `require_delta_if_baseline: bool = True` from function signature
2. Remove `--no-require-delta` argparse argument from `main()`
3. Change `validate_run(Path(args.output_dir), not args.no_require_delta)` to `validate_run(Path(args.output_dir))`

Check call sites: `run_scan.py` calls `validate_run()` — verify it does not pass the now-deleted param.

### Anti-Patterns to Avoid

- **Reading config.yaml in dashboard route (SCORE-04):** D-08 explicitly forbids this. Config can
  change after scan; only the stored intelligence JSON is authoritative.
- **Using `assessment.profile` field path (SCORE-04):** The field is `calibration.profile`. Using
  `assessment.profile` will return `KeyError` or `None` because `assessment` only contains `name`,
  `owner`, `data_classification`, `timezone`.
- **Adding delta logic back (SCORE-02):** The `_validate_calibration()` and `_validate_delta()`
  functions were removed in Phase 8. The `require_delta_if_baseline` param is an orphaned remnant.
  Do not re-implement any delta logic.
- **Modifying PROFILE_MULTIPLIERS (SCORE-01):** The multiplier table is correct. If the RED test
  passes without a code fix, it becomes a regression guard — do not change multiplier values.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Find latest intelligence JSON | Custom glob/sort | `_latest_intelligence()` in `quirk/validate.py:43` | Already sorts by mtime, handles edge cases |
| Output dir default | Hardcoded string | `os.environ.get("QUIRK_OUTPUT_DIR", "./quirk-output")` | Matches `config_template.yaml` default, consistent with `QUIRK_DB_PATH` pattern |
| Profile fallback on missing JSON | Complex logic | `profile=None` (scoring.py falls back to "balanced" automatically) | `compute_readiness_score` already handles `None` — line 83: `prof = str(profile or "balanced").lower()` |

---

## Common Pitfalls

### Pitfall 1: SCORE-01 RED Test Passes Immediately (Expected)

**What goes wrong:** The RED test for SCORE-01 is written, then it passes without any code change.
**Why it happens:** The profile multiplier logic was correctly wired in Phase 9. The RED test may
immediately be GREEN.
**How to avoid:** Per D-02, this is acceptable — the test becomes a permanent regression guard.
Do not force it to fail by introducing a bug. Document in the plan that the RED state may be
skipped for SCORE-01 if verification confirms the behavior already matches D-03.
**Warning signs:** If both strict and lenient produce identical scores on evidence with identity/
agility issues, the multiplier application is broken. Verified by live probe: strict=59, lenient=76
on evidence with expired certs and RSA-only keys.

### Pitfall 2: Wrong Field Path for Intelligence JSON Profile (SCORE-04)

**What goes wrong:** Code reads `intel_data["assessment"]["profile"]` and gets `None` or KeyError.
**Why it happens:** CONTEXT.md D-07 contains an error — it says `assessment.profile` but the
actual field is `calibration.profile`.
**How to avoid:** Always read `intel_data.get("calibration", {}).get("profile")` for SCORE-04.
**Warning signs:** Dashboard score never matches CLI score even after fix; `stored_profile` is
always `None`.

### Pitfall 3: validate_run Call Site in run_scan.py

**What goes wrong:** After removing `require_delta_if_baseline` from `validate_run` signature,
`run_scan.py` still passes a positional second argument and gets a TypeError.
**Why it happens:** `run_scan.py` may call `validate_run(output_dir, something)`.
**How to avoid:** Grep for all `validate_run(` calls before submitting Plan 2.
**Verified:** `run_scan.py` calls `validate_run(output_dir, ...)` at line 225 area — check exact
call before removing param.

### Pitfall 4: SCORE-03 SSH Pattern Ordering

**What goes wrong:** A finding with both "ssh" and "quantum" in its title (e.g., "SSH quantum
planning advisory") could match the "quantum" branch before the "ssh" branch.
**Why it happens:** migration_advisor.py checks "quantum" before "ssh" in its if/elif chain.
**Impact:** Both "quantum" and "ssh" would correctly assign path "Modernization → PQC Preparation".
Since SSH findings have severity INFO and are filtered at line 21, this is moot in practice.
**How to avoid:** The RED test should pass findings of each type and verify the recommendation
path, not just the count.

### Pitfall 5: Dashboard Test Isolation for SCORE-04

**What goes wrong:** SCORE-04 tests that read the intelligence JSON from disk break in CI if
no output dir exists.
**Why it happens:** The test doesn't mock the file read.
**How to avoid:** Use `tmp_path` fixture to create a mock intelligence JSON. Or mock
`_latest_intelligence` to return a known path. Keep the test focused on the kwarg propagation,
not file I/O.

---

## Code Examples

### Current Broken Call (SCORE-04)
```python
# quirk/dashboard/api/routes/scan.py line 329-330 — MISSING profile kwarg
from quirk.intelligence.scoring import compute_readiness_score
score_raw = compute_readiness_score(evidence)
```

### Reference Correct Call (writer.py lines 115-119)
```python
# Source: quirk/reports/writer.py
score_raw = compute_readiness_score(
    evidence,
    profile=cfg.intelligence.profile,
    weights=cfg.intelligence.calibration_overrides or None,
)
```

### SCORE-04 Fix Pattern
```python
# In get_latest_scan(), after building evidence:
stored_profile = None
try:
    from pathlib import Path
    from quirk.validate import _latest_intelligence
    output_dir = Path(os.environ.get("QUIRK_OUTPUT_DIR", "./quirk-output"))
    intel_path = _latest_intelligence(output_dir)
    if intel_path:
        import json
        intel_data = json.loads(intel_path.read_text(encoding="utf-8"))
        stored_profile = intel_data.get("calibration", {}).get("profile")
except Exception:
    pass  # fall back to balanced default

score_raw = compute_readiness_score(evidence, profile=stored_profile)
```

### SCORE-02 Fix Pattern — validate_run Signature
```python
# Before (broken — param exists but is unused):
def validate_run(output_dir: Path, require_delta_if_baseline: bool = True) -> ValidationResult:

# After (fixed):
def validate_run(output_dir: Path) -> ValidationResult:
```

### SCORE-01 RED Test Pattern (directional correctness)
```python
def test_strict_scores_lower_than_lenient_on_penalized_evidence(self):
    """D-03: strict produces higher agility+identity weight contribution (lower score on issues)."""
    evidence = {
        "totals": {"endpoints": 10, "findings": 5},
        "cert_key_type_counts": {"RSA": 8, "ECDSA": 0},
        "certificate_observations": {"expired_count": 3, "expiring_count": 2, "self_signed_count": 2},
        "finding_severity_counts": {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 1, "LOW": 1, "INFO": 0},
        # ... (minimal evidence with clear identity/agility issues)
    }
    strict_total = compute_readiness_score(evidence, profile="strict")["score"]
    lenient_total = compute_readiness_score(evidence, profile="lenient")["score"]
    self.assertLess(
        strict_total, lenient_total,
        f"strict ({strict_total}) should score LOWER than lenient ({lenient_total}) "
        "when evidence has identity/agility issues — higher weights = bigger penalty"
    )
```

### SCORE-02 RED Test Pattern
```python
def test_validate_run_no_delta_param(self):
    """D-04: require_delta_if_baseline must be removed from validate_run signature."""
    import inspect
    from quirk.validate import validate_run
    params = inspect.signature(validate_run).parameters
    self.assertNotIn(
        "require_delta_if_baseline",
        params,
        "validate_run must not have require_delta_if_baseline param — delta reports not implemented"
    )
```

### SCORE-03 RED Test Pattern
```python
def test_legacy_tls_finding_produces_migration_rec(self):
    """D-06: risk_engine title 'Legacy TLS versions allowed (TLS 1.0/1.1)' must produce a rec."""
    findings = [
        {"title": "Legacy TLS versions allowed (TLS 1.0/1.1)", "severity": "LOW",
         "host": "10.0.0.1", "port": 443, "recommendation": "Disable TLS 1.0/1.1"}
    ]
    recs = recommend_migration_paths(findings)
    self.assertEqual(len(recs), 1)
    self.assertEqual(recs[0]["path"], "Hygiene → Modernization")
```

---

## Live Probe Results

These were verified by running the actual code against the current codebase.

### SCORE-01 Runtime Verification
Evidence with expired certs (3), self-signed (2), RSA-only (8 RSA, 0 ECDSA), HIGH/CRITICAL findings:
- `strict` total: **59** (identity_trust=15, agility_signals=1)
- `lenient` total: **76** (identity_trust=20, agility_signals=13)
- `balanced` total: **69**
- Directional correctness: strict < balanced < lenient — **CONFIRMED WORKING**

### SCORE-02 Runtime Verification
- `validate_run` signature: `(output_dir: Path, require_delta_if_baseline: bool = True)`
- `require_delta_if_baseline` is present in signature but **never referenced in function body**
- `main()` passes `not args.no_require_delta` positionally — both must be removed
- `validate_run` call in `run_scan.py` at `output_dir=cfg.output.directory` parameter — verify before removing

### SCORE-03 Runtime Verification
All `risk_engine.py` finding titles and their migration_advisor pattern matches:
| risk_engine title | severity | matched pattern | result |
|---|---|---|---|
| `"Plaintext HTTP service detected"` | HIGH | `"plaintext http"` | Rec generated: Hygiene |
| `"Legacy TLS versions allowed (TLS 1.0/1.1)"` | LOW | `"legacy tls"` | Rec generated: Hygiene → Modernization |
| `"SSH quantum planning advisory"` | INFO | filtered (sev=INFO) | No rec (correct) |
| `"Unknown open service"` | MEDIUM | default fallback | Rec generated: Modernization |
| `"TLS handshake blocked assessment"` | MEDIUM | default fallback | Rec generated: Modernization |
| `"mTLS required"` | INFO | filtered (sev=INFO) | No rec (correct) |
| `"Informational protocol observation"` | INFO | filtered (sev=INFO) | No rec (correct) |
- Pattern matching is **CONFIRMED WORKING** for all titles. RED test becomes regression guard.

### SCORE-04 Runtime Verification
- `compute_readiness_score(evidence)` at line 330: **no profile kwarg** — confirmed bug
- Intelligence JSON `assessment` block has: `name, owner, data_classification, timezone` — NO `profile`
- Intelligence JSON `calibration` block has: `profile, overrides_applied` — profile IS here
- **CONTEXT.md D-07 field path `assessment.profile` is WRONG** — correct path is `calibration.profile`

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` |
| Quick run command | `python3 -m pytest tests/test_scoring_correctness.py -v` |
| Full suite command | `python3 -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCORE-01 | strict profile scores lower than lenient on penalized evidence | unit | `python3 -m pytest tests/test_scoring_correctness.py::ScoringCorrectnessTests::test_strict_scores_lower_than_lenient_on_penalized_evidence -x` | Wave 0 |
| SCORE-02 | validate_run has no require_delta_if_baseline param | unit | `python3 -m pytest tests/test_scoring_correctness.py::ValidateCorrectnessTests::test_validate_run_no_delta_param -x` | Wave 0 |
| SCORE-03 | legacy TLS finding produces migration recommendation | unit | `python3 -m pytest tests/test_scoring_correctness.py::MigrationAdvisorTests::test_legacy_tls_finding_produces_migration_rec -x` | Wave 0 |
| SCORE-04 | dashboard score equals CLI score when profile is non-default | integration | `python3 -m pytest tests/test_scoring_correctness.py::DashboardProfileTests -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_scoring_correctness.py tests/test_intelligence_scoring.py tests/test_validate.py -v`
- **Per wave merge:** `python3 -m pytest tests/ -v`
- **Phase gate:** Full suite 215+ passing before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_scoring_correctness.py` — new file covering SCORE-01 through SCORE-04

*(All existing test infrastructure is already configured — only the new test file is needed)*

---

## State of the Art

| Old Approach | Current Approach | Phase Changed | Impact |
|--------------|------------------|---------------|--------|
| Multiple assessment modules (`readiness_score.py`, `confidence.py`, etc.) | Single path through `intelligence/scoring.py` | Phase 9 | Removed in Phase 9; executive.py and writer.py both use intelligence module |
| `_validate_calibration()` / `_validate_delta()` in validate.py | Removed | Phase 8 | Confirmed removed; only `require_delta_if_baseline` parameter remnant remains |
| `migration_advisor.py` pattern `"deprecated tls"` | `"legacy tls"` | Phase 8 (D-15) | Already updated; now matches risk_engine title correctly |

**Key context:** Phase 8 removed `_validate_calibration()` and `_validate_delta()` but left the
`require_delta_if_baseline` parameter in the function signature as dead code. Phase 14 SCORE-02
completes this cleanup.

---

## Open Questions

1. **SCORE-04: validate_run call in run_scan.py**
   - What we know: `run_scan.py` calls `validate_run(output_dir, ...)` — the exact call signature
     needs verification before removing the parameter from SCORE-02.
   - What's unclear: Does it pass `require_delta_if_baseline` positionally or by keyword?
   - Recommendation: Plan 2 must grep `validate_run(` across the codebase and update all call sites
     before removing the parameter.
   - Verified search: `grep -n "validate_run" run_scan.py` — confirm exactly one call site.

2. **SCORE-04: QUIRK_OUTPUT_DIR vs hardcoded default**
   - What we know: No `QUIRK_OUTPUT_DIR` env var exists yet; `QUIRK_DB_PATH` pattern already
     established in `deps.py`.
   - What's unclear: Whether to introduce a new env var or just use `./quirk-output` default.
   - Recommendation: Add `QUIRK_OUTPUT_DIR` env var with `./quirk-output` default for consistency
     with `QUIRK_DB_PATH`. Single line in scan.py. Document in Plan 2 task.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 14 is purely internal Python code/config changes with no external tool
dependencies. All required modules (`quirk.intelligence.scoring`, `quirk.validate`,
`quirk.assessment.migration_advisor`, `quirk.dashboard.api.routes.scan`) are in the repo.
Python 3.14.3, pytest 9.0.2 confirmed available.

---

## Project Constraints (from CLAUDE.md)

- Follow PEP 8 for all Python changes.
- Keep diffs minimal — avoid unnecessary refactors.
- After changes, run `python -m compileall` and relevant tests.
- If detection logic changes, update `labs/*/expected_results.md` accordingly.
  (Phase 14 does not change detection logic — this constraint does not apply.)

---

## Sources

### Primary (HIGH confidence)
- Live code inspection: `quirk/intelligence/scoring.py` — PROFILE_MULTIPLIERS, compute_readiness_score
- Live code inspection: `quirk/validate.py` — validate_run signature and body, _latest_intelligence
- Live code inspection: `quirk/assessment/migration_advisor.py` — pattern matching logic
- Live code inspection: `quirk/engine/risk_engine.py:37-38` — exact finding title strings
- Live code inspection: `quirk/dashboard/api/routes/scan.py:329-330` — missing profile kwarg
- Live code inspection: `quirk/reports/writer.py:152-155` — calibration.profile storage (not assessment.profile)
- Live runtime probes — actual scores computed with strict/balanced/lenient profiles
- pytest run — 215/215 baseline tests confirmed passing

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` — accumulated decisions from prior phases
- `.planning/phases/14-scoring-intelligence-correctness/14-CONTEXT.md` — user decisions (with noted discrepancy on field path)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all modules read and probed live
- Architecture: HIGH — runtime behavior confirmed, field paths verified against actual code
- Pitfalls: HIGH — discrepancy between CONTEXT.md D-07 and actual code verified directly

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable codebase, no external dependencies)
