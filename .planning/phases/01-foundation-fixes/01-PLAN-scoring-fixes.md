---
phase: 01-foundation-fixes
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - qcscan/reports/writer.py
  - tests/test_cert_pubkey_fix.py
  - tests/test_scoring_consolidation.py
autonomous: true
requirements: [CORE-01, CORE-02]

must_haves:
  truths:
    - "A scan run produces one score, sourced from intelligence/scoring.py, with no silent override from assessment/readiness_score.py"
    - "Certificate public key algorithm appears correctly in all output for every cert encountered"
    - "_extract_cert_key_type() returns the value from cert_pubkey_alg (the actual CryptoEndpoint field)"
  artifacts:
    - path: "qcscan/reports/writer.py"
      provides: "Consolidated scoring through intelligence layer, fixed cert_pubkey_alg extraction"
      contains: "from qcscan.intelligence.evidence import build_evidence_summary"
    - path: "tests/test_cert_pubkey_fix.py"
      provides: "Unit tests for _extract_cert_key_type fix"
    - path: "tests/test_scoring_consolidation.py"
      provides: "Tests confirming single scoring path through intelligence/scoring.py"
  key_links:
    - from: "qcscan/reports/writer.py"
      to: "qcscan/intelligence/scoring.py"
      via: "compute_readiness_score(evidence) call"
      pattern: "from qcscan\\.intelligence\\.scoring import compute_readiness_score"
    - from: "qcscan/reports/writer.py"
      to: "qcscan/intelligence/evidence.py"
      via: "build_evidence_summary(endpoints, findings) call"
      pattern: "from qcscan\\.intelligence\\.evidence import build_evidence_summary"
---

<objective>
Consolidate the dual scoring system into a single authoritative path and fix the cert_pubkey_alg field extraction bug.

Purpose: writer.py currently has its own inline scoring (_score_from_evidence) AND calls
assessment/readiness_score.py — producing two competing scores. The cert_pubkey_alg field
is never found because _extract_cert_key_type() probes wrong attribute names. Both are
data quality blockers.

Output: writer.py uses intelligence/scoring.py as sole scoring path, assessment block removed,
cert key type extraction fixed, dead code deleted, tests green.
</objective>

<execution_context>
@/Users/digs/.claude/get-shit-done/workflows/execute-plan.md
@/Users/digs/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-foundation-fixes/01-CONTEXT.md
@.planning/phases/01-foundation-fixes/01-RESEARCH.md

<interfaces>
<!-- Key types and contracts the executor needs. -->

From qcscan/intelligence/evidence.py:
```python
def build_evidence_summary(
    endpoints: Iterable[Any],
    findings: Iterable[Mapping[str, Any]],
    *,
    reference_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    # Returns Schema B evidence dict with keys:
    # totals, protocol_counts, plaintext_http_count, http_on_tls_port_count,
    # mtls_present_count, cert_key_type_counts, certificate_observations,
    # scan_error, finding_severity_counts, tls_enum_coverage_ratio
```

From qcscan/intelligence/scoring.py:
```python
def compute_readiness_score(
    evidence: Mapping[str, Any],
    *,
    weights: Mapping[str, float] | None = None,
) -> Dict[str, Any]:
    # Returns: {"score": int, "rating": str, "subscores": {...}, "drivers": [...]}
```

From qcscan/intelligence/confidence.py:
```python
def compute_confidence(
    evidence: Mapping[str, Any],
    *,
    weights: Mapping[str, float] | None = None,
) -> Dict[str, Any]:
    # Returns: {"confidence_score": int, "confidence_rating": str, ...}
```

From qcscan/intelligence/roadmap.py:
```python
def build_phased_roadmap(
    evidence: Mapping[str, Any],
    score: Mapping[str, Any],
    confidence: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    # Returns list of roadmap items with timeframe/title/why/owner/dependencies
```

From qcscan/reports/scorecard.py (reference implementation - correct pattern):
```python
from qcscan.intelligence.confidence import compute_confidence
from qcscan.intelligence.evidence import build_evidence_summary
from qcscan.intelligence.roadmap import build_phased_roadmap
from qcscan.intelligence.scoring import compute_readiness_score

# Usage:
evidence = build_evidence_summary(endpoints, findings)
score = compute_readiness_score(evidence)
confidence = compute_confidence(evidence)
roadmap = build_phased_roadmap(evidence, score, confidence)
```

From qcscan/models.py:
```python
class CryptoEndpoint(Base):
    cert_pubkey_alg = Column(String(64), nullable=True)  # THE canonical field name
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Write tests for cert_pubkey_alg fix and scoring consolidation</name>
  <files>tests/test_cert_pubkey_fix.py, tests/test_scoring_consolidation.py</files>
  <read_first>
    - qcscan/reports/writer.py (lines 234-245 for _extract_cert_key_type, lines 398-431 for _score_from_evidence, lines 540-648 for write_reports)
    - qcscan/models.py (CryptoEndpoint field names)
    - qcscan/intelligence/scoring.py (compute_readiness_score signature and return shape)
    - qcscan/intelligence/evidence.py (build_evidence_summary signature)
    - qcscan/reports/scorecard.py (reference implementation of correct pattern)
    - tests/test_intelligence_scoring.py (existing test patterns)
  </read_first>
  <behavior>
    - test_cert_pubkey_alg_found: Create a mock object with cert_pubkey_alg="RSA", call _extract_cert_key_type(), assert returns "RSA"
    - test_cert_pubkey_alg_preferred_over_fallbacks: Create mock with both cert_pubkey_alg="ECDSA" and cert_key_type="RSA", assert returns "ECDSA" (canonical field wins)
    - test_cert_pubkey_alg_none_falls_through: Create mock with cert_pubkey_alg=None and cert_key_type="RSA", assert returns "RSA"
    - test_scoring_uses_intelligence_module: After consolidation, writer.py must import compute_readiness_score from qcscan.intelligence.scoring (not from qcscan.assessment.readiness_score)
    - test_no_assessment_readiness_import: After consolidation, writer.py must NOT import from qcscan.assessment.readiness_score
  </behavior>
  <action>
    Create tests/test_cert_pubkey_fix.py:
    - Import _extract_cert_key_type from qcscan.reports.writer
    - Use types.SimpleNamespace to create mock endpoint objects with various attribute combinations
    - Test that cert_pubkey_alg is checked first (per D-12)

    Create tests/test_scoring_consolidation.py:
    - Test that writer.py imports compute_readiness_score from qcscan.intelligence.scoring
    - Test that writer.py does NOT import from qcscan.assessment.readiness_score
    - Use inspect or ast module to verify import sources in writer.py
    - These tests will FAIL initially (RED phase) since writer.py hasn't been fixed yet
  </action>
  <verify>
    <automated>cd /Volumes/Digs-1TB/Development/quantum-apps/QuRisk && python -m pytest tests/test_cert_pubkey_fix.py tests/test_scoring_consolidation.py -x -v 2>&1 | tail -20</automated>
  </verify>
  <done>Test files exist, cert_pubkey_alg tests fail (because the fix isn't in yet), scoring consolidation import tests fail (because writer.py still imports from assessment)</done>
</task>

<task type="auto">
  <name>Task 2: Fix _extract_cert_key_type and consolidate scoring in writer.py</name>
  <files>qcscan/reports/writer.py</files>
  <read_first>
    - qcscan/reports/writer.py (full file — must understand all current imports, functions, and the write_reports flow)
    - qcscan/reports/scorecard.py (reference implementation — shows correct import pattern for intelligence layer)
    - qcscan/intelligence/evidence.py (build_evidence_summary signature)
    - qcscan/intelligence/scoring.py (compute_readiness_score signature and return value shape)
    - qcscan/intelligence/confidence.py (compute_confidence signature — the INTELLIGENCE version, not assessment version)
    - qcscan/intelligence/roadmap.py (build_phased_roadmap signature)
    - qcscan/intelligence/driver_text.py (polish_drivers — still used, check its signature)
  </read_first>
  <action>
    Per D-08, D-09, D-10, D-11, D-12:

    **Fix _extract_cert_key_type() (D-12, CORE-02):**
    Replace the function at line ~235. The new version checks `cert_pubkey_alg` FIRST:
    ```python
    def _extract_cert_key_type(ep: Any) -> Optional[str]:
        # cert_pubkey_alg is the canonical field on CryptoEndpoint
        v = getattr(ep, "cert_pubkey_alg", None)
        if v:
            return str(v).upper()
        # Fallback probe for any legacy/duck-typed endpoints
        for attr in ("cert_key_type", "cert_pubkey_type", "cert_public_key_type", "cert_key_algo", "cert_pubkey_algo"):
            v = getattr(ep, attr, None)
            if v:
                return str(v).upper()
        cert = getattr(ep, "cert", None)
        if isinstance(cert, dict):
            for k in ("key_type", "public_key_type", "pubkey_type", "algo"):
                if cert.get(k):
                    return str(cert.get(k)).upper()
        return None
    ```

    **Remove legacy assessment imports (D-09, D-11):**
    Delete these imports from the top of writer.py:
    - `from qcscan.assessment.readiness_score import compute_readiness_score`
    - `from qcscan.assessment.transition_planner import build_transition_roadmap`
    - `from qcscan.assessment.migration_advisor import recommend_migration_paths`
    - `from qcscan.assessment.operator_context import get_context`
    - `from qcscan.assessment.confidence import compute_confidence`

    **Add intelligence imports:**
    ```python
    from qcscan.intelligence.evidence import build_evidence_summary
    from qcscan.intelligence.scoring import compute_readiness_score as compute_score
    from qcscan.intelligence.confidence import compute_confidence as compute_conf
    from qcscan.intelligence.roadmap import build_phased_roadmap
    ```
    Note: use aliases `compute_score` and `compute_conf` to avoid shadowing with the deleted assessment imports. Or use the full module path in calls.

    **Remove the legacy assessment block in write_reports() (D-09):**
    Delete lines ~584-602 (the block that produces assessment-TIMESTAMP.json):
    ```python
    # DELETE THIS ENTIRE BLOCK:
    confidence_legacy = compute_confidence(cfg, endpoints)
    readiness_legacy = compute_readiness_score(cfg, endpoints, findings).to_dict()
    transition_legacy = build_transition_roadmap(cfg, endpoints, findings).to_dict()
    assessment = { ... }
    assessment_path = ...
    _json_dump(assessment_path, assessment)
    ```
    Also remove `assessment_path` from the final console print list.

    **Replace inline scoring with intelligence calls (D-10):**
    In write_reports(), replace:
    ```python
    evidence = _normalize_evidence(endpoints, findings)
    score = _score_from_evidence(evidence)
    ```
    With (matching scorecard.py pattern):
    ```python
    evidence = build_evidence_summary(endpoints, findings)
    score_result = compute_readiness_score(evidence)
    ```

    Adapt downstream references:
    - `score.get("total")` stays the same (intelligence scoring returns {"score": N, ...} — map "score" key to "total" for backward compat in intelligence JSON output, or update the key references)
    - Actually: intelligence/scoring.py returns `{"score": int, "rating": str, "subscores": {...}, "drivers": [...]}`. The existing writer code uses `score.get("total")` and `score.get("subscores")`. So create a compat wrapper:
      ```python
      score_raw = compute_readiness_score(evidence)
      score = {"total": score_raw["score"], "subscores": score_raw["subscores"], "drivers": [d["reason"] for d in score_raw.get("drivers", [])]}
      ```

    Replace confidence:
    ```python
    conf_result = compute_confidence(evidence)  # intelligence version
    conf = {"confidence": conf_result.get("confidence_score", 0), "confidence_factors": conf_result.get("confidence_factors", {})}
    ```

    Replace roadmap:
    ```python
    roadmap = build_phased_roadmap(evidence, score_raw, conf_result)
    ```

    **Delete dead functions from writer.py:**
    - `_normalize_evidence()` (lines ~292-376)
    - `_score_from_evidence()` (lines ~398-430)
    - `_confidence_from_evidence()` (lines ~433-449)
    - `_drivers_from_evidence()` (lines ~379-395)
    - `_roadmap_from_evidence()` (lines ~452-501)

    **Keep these functions** (still used by delta logic or evidence pipeline):
    - `_extract_cert_key_type()` (fixed above)
    - `_extract_cert_dates()`, `_is_self_signed()`, `_mtls_present()` — check if build_evidence_summary uses them. If not (it has its own), they may be dead too. Verify before deleting.
    - `_scorecard_markdown()`, `_roadmap_markdown()`, `_delta_*` helpers — still used
    - `_count_findings()` — check if still used

    **Important:** The `polish_drivers()` call needs updated input. Currently it receives `(evidence, raw_drivers)` where raw_drivers is a list of strings. After consolidation, `score_raw["drivers"]` is a list of dicts `{"reason": str, "points": int}`. Extract just the reason strings: `raw_drivers = [d["reason"] for d in score_raw.get("drivers", [])]`
  </action>
  <verify>
    <automated>cd /Volumes/Digs-1TB/Development/quantum-apps/QuRisk && python -m pytest tests/test_cert_pubkey_fix.py tests/test_scoring_consolidation.py tests/test_intelligence_scoring.py tests/test_intelligence_confidence.py tests/test_intelligence_evidence.py -x -v 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - grep -n "from qcscan.assessment.readiness_score" qcscan/reports/writer.py returns NO matches
    - grep -n "from qcscan.assessment.transition_planner" qcscan/reports/writer.py returns NO matches
    - grep -n "from qcscan.assessment.confidence" qcscan/reports/writer.py returns NO matches
    - grep -n "from qcscan.intelligence.evidence import build_evidence_summary" qcscan/reports/writer.py returns a match
    - grep -n "from qcscan.intelligence.scoring import compute_readiness_score" qcscan/reports/writer.py returns a match
    - grep -n "cert_pubkey_alg" qcscan/reports/writer.py shows cert_pubkey_alg as the FIRST attribute checked in _extract_cert_key_type
    - grep -n "_score_from_evidence" qcscan/reports/writer.py returns NO matches (function deleted)
    - grep -n "_normalize_evidence" qcscan/reports/writer.py returns NO matches (function deleted)
    - All pytest tests pass
  </acceptance_criteria>
  <done>writer.py uses intelligence/scoring.py as sole scoring path, assessment imports removed, _extract_cert_key_type checks cert_pubkey_alg first, dead code deleted, all tests green</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/ -x -q` passes (all existing + new tests)
- `grep -rn "from qcscan.assessment.readiness_score" qcscan/reports/writer.py` returns nothing
- `grep -rn "from qcscan.intelligence.scoring import" qcscan/reports/writer.py` returns a match
- `grep -n "cert_pubkey_alg" qcscan/reports/writer.py` shows it as first probe in _extract_cert_key_type
- `python -c "from qcscan.reports.writer import _extract_cert_key_type; from types import SimpleNamespace; ep = SimpleNamespace(cert_pubkey_alg='RSA'); print(_extract_cert_key_type(ep))"` prints "RSA"
</verification>

<success_criteria>
- Single scoring path through intelligence/scoring.py (CORE-01)
- cert_pubkey_alg correctly extracted as first probe (CORE-02)
- No assessment/readiness_score imports remain in writer.py
- All existing tests remain green
- New tests for cert fix and scoring consolidation pass
</success_criteria>

<output>
After completion, create `.planning/phases/01-foundation-fixes/01-01-SUMMARY.md`
</output>
