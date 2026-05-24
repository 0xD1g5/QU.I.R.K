# Phase 98: Executive Narrative + Score Transparency — Pattern Map

**Mapped:** 2026-05-24
**Files analyzed:** 8 (4 new, 4 modified)
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/reports/content_model.py` | model/utility | transform | `quirk/intelligence/schema.py` | exact (dataclass module with static maps) |
| `quirk/reports/executive.py` | utility/renderer | transform | self (existing — refactor target) | self-refactor |
| `quirk/reports/html_renderer.py` | renderer | request-response | self (existing — kwarg extension) | self-refactor |
| `quirk/reports/writer.py` | orchestrator | batch | self (existing — seam insertion) | self-refactor |
| `quirk/reports/templates/report.html.j2` | template | transform | self (existing — block additions) | self-refactor |
| `tests/test_exec_content_model.py` | test | — | `tests/test_score_transparency.py` | exact (unit test, mock score, assert string/structure) |
| `tests/test_congruence_guard.py` | test | — | `tests/test_executive_score_guard.py` | exact (error-path unit test pattern) |
| `tests/test_exec_narrative_ordering.py` | test | — | `tests/test_html_report.py` | exact (render→string→assert pattern) |
| `tests/test_cross_surface_parity.py` | test | — | `tests/test_score_render_parity.py` | exact (two-surface output identity gate) |

---

## Pattern Assignments

---

### `quirk/reports/content_model.py` (model, transform)

**Analog:** `quirk/intelligence/schema.py`

**Imports pattern** (`quirk/intelligence/schema.py` lines 1-6):
```python
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Tuple
```

**Core dataclass pattern** (`quirk/intelligence/schema.py` lines 10-28, 62-79):
```python
# Frozen + slots = immutable, memory-efficient; use for ExecContent sub-items too.
@dataclass(frozen=True, slots=True)
class ScoreInputs:
    total_endpoints: int
    tls_success: int
    # ... fields ...

    def to_dict(self) -> Dict[str, int]:
        return { ... }

# IntelligenceReport — composite dataclass (the ExecContent analog):
@dataclass(frozen=True, slots=True)
class IntelligenceReport:
    """Typed return shape ..."""
    generated_utc: str
    score_inputs: ScoreInputs
    score_result: ScoreResult
    confidence_result: ConfidenceResult
    roadmap: Tuple[RoadmapItem, ...] = ()
    schema_version: str = SCHEMA_VERSION
```

**Static map + custom exception pattern** (`quirk/errors.py` lines 11-17, 20-21, 259-268):
```python
# Use @dataclass(frozen=True) for registry entries (not frozen=True,slots=True — this
# is a simple frozen value object without the slots optimization overhead).
@dataclass(frozen=True)
class ErrorEntry:
    code: str
    cause: str
    fix: str

ERROR_REGISTRY: dict[str, ErrorEntry] = {
    "INSTALL-001": ErrorEntry(code="INSTALL-001", cause="...", fix="..."),
    ...
}

# Custom exception subclasses ValueError — same pattern for ReportCongruenceError:
class ReportCongruenceError(ValueError):
    """Raised when exec headline band contradicts severity counts (D-06/TRANS-03)."""
    pass
```

**Decision-tag comment convention** (`quirk/reports/executive.py` lines 10-14, 176):
```python
from quirk.reports._md_escape import md_cell  # Phase 78 / HARDEN-01: wrap scanner-controlled cells
# D-07 / WR-09 (Phase 73): fallback bullet when score dict is malformed.
_INTERPRETATION_UNAVAILABLE = "Score data unavailable for this run."
# D-07 / SCORE-XPARENCY-01: subscore decomposition in executive markdown
```
Apply same `# D-NN / REQ-ID: description` comment tagging to all new content_model.py definitions.

**Lazy-import pattern for optional extras** (`quirk/reports/html_renderer.py` lines 86-103):
```python
# For any new optional dep: lazy import inside function, never at module scope.
try:
    from quirk.compliance.cmvp import coverage_for_algorithm
except ImportError:
    def coverage_for_algorithm(_name: str):
        return []
```
No new optional deps are added in Phase 98; Playwright/pypdf already follow this pattern. Do not break it.

**Key structural decisions for `content_model.py`:**
- Use `@dataclass` (not `frozen=True, slots=True`) for `ExecContent`, `RiskItem`, `RoadmapItem` — these are mutable build-time objects, not hash-keyed registry entries. `config.py` uses plain `@dataclass` for the same reason.
- Module-level dicts `ALGO_IMPACT_MAP` and `EFFORT_IMPACT_MAP` follow the `ERROR_REGISTRY` pattern (plain `dict` literal, not a dataclass).
- `_check_congruence()` and `build_exec_content()` are module-level functions, not class methods.
- Export via `__all__` at bottom of module (see `quirk/errors.py` line 281).

---

### `quirk/reports/executive.py` (renderer, transform — refactor)

**Analog:** self (full file read above)

**Current imports block** (`executive.py` lines 1-12):
```python
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List

from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.confidence import compute_confidence
from quirk.intelligence.roadmap import build_phased_roadmap
from quirk.assessment.migration_advisor import recommend_migration_paths
from quirk.reports._md_escape import md_cell  # Phase 78 / HARDEN-01: wrap scanner-controlled cells
from quirk.reports.html_renderer import build_algorithm_inventory
```
After Phase 98: add `from quirk.reports.content_model import ExecContent` to this block.

**Function signature change** (`executive.py` line 111):
```python
# Current:
def build_exec_markdown(cfg, endpoints, findings) -> str:

# After Phase 98 (new kwarg, backward-compat default):
def build_exec_markdown(cfg, endpoints, findings, *, exec_content: "ExecContent | None" = None) -> str:
```

**md_cell wrapping pattern for narrative cells** (`executive.py` lines 172, 234, 248, 264):
```python
# Any finding-derived string in a GFM table cell or bullet must be wrapped:
lines.append(f"- {md_cell(d['reason'])} (**-{d['points']}**)")
lines.append(f"  - {md_cell(category)}: {count}")
lines.append(f"- {md_cell(b)}")
lines.append(f"- **{md_cell(item['title'])}** — {md_cell(item['why'])}")
# Static template strings (narrative lead, rollup formula) do NOT need md_cell.
```

**Section ordering** — the `lines.append` calls currently follow this sequence (lines 158-308):
1. `## Executive Summary` (metadata)
2. `## Quantum Readiness Score` + Score Decomposition (lines 166-194)
3. `## Confidence & Coverage` (lines 197-213)
4. `## Discovery and Coverage` (lines 215-220)
5. `## Algorithm Inventory` (lines 222-238)
6. `## Findings Overview (Executive-Relevant)` (lines 240-245)
7. `## Interpretation` bullets (lines 246-249) — **MUST MOVE before section 2**
8. `## Transition Roadmap` (lines 250-268)
9. `## Recommended Migration Paths` (lines 270-286)
10. `## Recommended Next Actions` (lines 288-307)

After Phase 98: narrative prose block (from `exec_content.narrative_lead + narrative_drivers`) inserted at position 2; `## Interpretation` section removed or replaced.

---

### `quirk/reports/html_renderer.py` (renderer, request-response — kwarg extension)

**Analog:** self (full file read above)

**Current function signature** (`html_renderer.py` lines 145-153):
```python
def render_html_report(
    path: str,
    cfg: Any,
    endpoints: List[Any],
    findings: List[Dict[str, Any]],
    score: Dict[str, Any],
    conf: Dict[str, Any],
    roadmap_items: List[Dict[str, Any]],
) -> None:
```
After Phase 98: add `exec_content: "ExecContent | None" = None` keyword argument.

**Template context build pattern** (`html_renderer.py` lines 189-208):
```python
html = template.render(
    org_name=...,
    total_score=total_score,
    score_band=band,
    score_color=_score_color(band),
    sev_counts=sev_counts,
    drivers=score.get("drivers", []),
    findings=findings or [],
    subscores=score.get("subscores", {}),  # D-07 / SCORE-XPARENCY-01
    ...
)
```
After Phase 98: replace `subscores=score.get("subscores", {})` with `subscores=exec_content.subscores if exec_content else score.get("subscores", {})`. Add `narrative_lead`, `top_risks`, `roadmap_now`/`roadmap_next`/`roadmap_later` from `exec_content`.

**sanitize filter registration** (`html_renderer.py` lines 158-162):
```python
env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "j2"]),
)
env.filters["sanitize"] = sanitize_scanner_text
```
All scanner-derived text in new template sections must pipe through `| sanitize`. Static strings (narrative lead, rollup formula, effort/impact band labels) are template-static and do not need it.

---

### `quirk/reports/writer.py` (orchestrator, batch — seam insertion)

**Analog:** self (full file read above)

**Integration seam location** (`writer.py` lines 156-221 — current write_reports):
```python
# Step 2: exec + tech markdown (lines 146-154) — exec_md produced HERE before score_raw
exec_md = build_exec_markdown(cfg, endpoints, findings)

# Step 3: intelligence outputs (lines 157-177) — score_raw computed HERE
evidence = build_evidence_summary(endpoints, findings)
score_raw = compute_readiness_score(...)
conf_raw = compute_confidence(evidence)
roadmap_raw = build_phased_roadmap(evidence, score_raw)

# Compat wrappers (lines 167-177)
score = {"total": score_raw["score"], "subscores": score_raw["subscores"], ...}
```
After Phase 98: `build_exec_content()` must be called AFTER `score_raw` and `roadmap_raw` are computed (step 3), but BEFORE the compat wrapper. Then `exec_md` must be rebuilt (or `build_exec_markdown` called after step 3 with `exec_content`).

**D-06 guard placement:** `_check_congruence()` is embedded inside `build_exec_content()` and raises `ReportCongruenceError` before any file I/O. The `ReportCongruenceError` propagates to `write_reports()` caller. No try/except in `write_reports()` — let it propagate.

**md_cell import already present** (`writer.py` line 12):
```python
from quirk.reports._md_escape import md_cell  # Phase 78 / HARDEN-01: scanner-cell escape
```

**score dict shape warning** (`writer.py` lines 167-170):
```python
# writer.py wraps score_raw as {"total": score_raw["score"], ...}
# build_exec_content() must receive score_raw (canonical keys: "score", "rating", "subscores")
# NOT the compat wrapper (which uses "total"). Call build_exec_content() BEFORE the compat wrapper.
score = {
    "total": score_raw["score"],
    ...
}
```

---

### `quirk/reports/templates/report.html.j2` (template, transform — block additions)

**Analog:** self (lines 140-223 read above)

**Existing `| sanitize` filter pattern** (lines 142-145, 188, 203-204):
```jinja
{{ org_name | sanitize }}
{{ f.get('title','') | sanitize }}
{{ f.get('description','')[:120] | sanitize }}
```
All new narrative/risk/roadmap content derived from scanner data (finding titles in risk sentences, driver text) must pipe through `| sanitize`. Static narrative prose does not.

**Existing score decomposition block** (lines 155-171 — DO NOT REBUILD):
```jinja
{% if subscores %}
<h3>Score Decomposition</h3>
<table>
  <thead><tr><th>Category</th><th>Score</th><th>Budget</th></tr></thead>
  <tbody>
    <tr><td>Hygiene</td><td>{{ subscores.get('hygiene', '—') }}</td><td>/25</td></tr>
    ...
  </tbody>
</table>
<p><strong>Rollup:</strong>
  {{ subscores.values() | sum }} &divide; 1.5 = <strong>{{ total_score }} / 100</strong>
</p>
{% endif %}
```
After Phase 98: `subscores` context var sourced from `exec_content.subscores`. Block itself unchanged.

**Existing roadmap-item rendering** (lines 210-223):
```jinja
{% for phase_label, items in [('NOW', roadmap_now), ('NEXT', roadmap_next), ('LATER', roadmap_later)] %}
{% if items %}
<div class="roadmap-phase">
  <h3>{{ phase_label }}</h3>
  {% for item in items %}
  <div class="roadmap-item">
    <strong>{{ item.get('title','') | sanitize }}</strong><br>
    <span>{{ item.get('why','') | sanitize }}</span>
  </div>
  {% endfor %}
</div>
{% endif %}
{% endfor %}
```
After Phase 98: add `<span class="priority-label">` inside `roadmap-item` div. Items now carry `effort` and `impact` attributes from `ExecContent.roadmap_items`.

**New section insertion point:** narrative prose block (`<div class="narrative-block">`) goes before `<h2>Quantum Readiness Score</h2>` (line 148). Top-risks list (`.risks-list`) goes after the Score Decomposition block and before `<h2>Findings Breakdown</h2>` (line 173).

---

## Test Pattern Assignments

---

### `tests/test_exec_content_model.py` (unit test — EXEC-02, EXEC-03, TRANS-01)

**Analog:** `tests/test_score_transparency.py`

**Fixture factory pattern** (`test_score_transparency.py` lines 17-42):
```python
def _make_mock_score():
    """Construct a writer.py-style wrapped score dict (key='total', not 'score')."""
    return {
        "total": 67,
        "subscores": {
            "hygiene": 20,
            "modern_tls": 18,
            "identity_trust": 25,
            "agility_signals": 15,
            "data_at_rest": 22,
            "data_in_motion": 21,
        },
        "drivers": ["Plaintext HTTP exposure (-12)", "RSA-only certificate posture (-8)"],
    }

def _make_mock_cfg():
    cfg = MagicMock()
    cfg.assessment.report_owner = "Test Owner"
    cfg.assessment.data_classification = "CONFIDENTIAL"
    cfg.assessment.name = "Test Assessment"
    cfg.intelligence.profile = "balanced"
    cfg.intelligence.calibration_overrides = None
    return cfg
```
For `test_exec_content_model.py`: use the CANONICAL score_raw key shape (`"score"` not `"total"`) since `build_exec_content()` receives `score_raw` before the compat wrapper. Provide minimal `findings` list for top-risks population tests.

**Assert style** (`test_score_transparency.py` lines 54-64):
```python
assert "/25" in output, (
    "_scorecard_markdown output missing '/25' budget strings. "
    "SCORE-XPARENCY-01 requires subscore decomposition block."
)
assert "÷ 1.5" in output or "/ 1.5" in output, (...)
```
Use descriptive assertion messages that name the requirement ID.

---

### `tests/test_congruence_guard.py` (unit test — TRANS-03)

**Analog:** `tests/test_executive_score_guard.py`

**Error-path unit test pattern** (`test_executive_score_guard.py` lines 1-49):
```python
from quirk.reports.executive import _INTERPRETATION_UNAVAILABLE, _build_interpretation

def test_build_interpretation_with_none_score():
    """None score returns fallback shape (no KeyError)."""
    result = _build_interpretation(
        evidence={}, score=None, endpoints=[], findings=[]
    )
    assert result == {"bullets": [_INTERPRETATION_UNAVAILABLE]}

def test_build_interpretation_with_non_dict():
    """Non-dict (e.g., string) returns fallback shape (no AttributeError)."""
    result = _build_interpretation(...)
    assert result == {"bullets": [_INTERPRETATION_UNAVAILABLE]}
```
For `test_congruence_guard.py`: import `_check_congruence` and `ReportCongruenceError` from `quirk.reports.content_model`. Cover both raise and no-raise cases explicitly per requirement:
- `_check_congruence("GOOD", {"CRITICAL": 3})` → `pytest.raises(ReportCongruenceError)`
- `_check_congruence("FAIR", {"CRITICAL": 5})` → no raise
- Check the exception message string matches the UI-SPEC copy.
- Integration test: mock `write_reports()` path to assert no files written when guard fires.

---

### `tests/test_exec_narrative_ordering.py` (unit test — EXEC-01, EXEC-02, EXEC-03, TRANS-02)

**Analog:** `tests/test_html_report.py`

**Render → file → read → assert pattern** (`test_html_report.py` lines 20-37):
```python
from quirk.reports.html_renderer import render_html_report
import os
cfg = _make_minimal_cfg()
os.makedirs(cfg.output.directory, exist_ok=True)
out = os.path.join(cfg.output.directory, "report-test.html")
render_html_report(
    path=out, cfg=cfg, endpoints=[], findings=[],
    score={"total": 75, "subscores": {}, "drivers": []},
    conf={"confidence": 80, "confidence_factors": {}},
    roadmap_items=[],
)
content = open(out).read()
assert "QU.I.R.K." in content
```

**SimpleNamespace cfg factory** (`test_html_report.py` lines 6-17):
```python
from types import SimpleNamespace
return SimpleNamespace(
    assessment=SimpleNamespace(
        name="Test Org",
        report_owner="Test Owner",
        data_classification="CONFIDENTIAL",
        timezone="UTC",
    ),
    output=SimpleNamespace(directory="/tmp/quirk_test_html"),
)
```

For ordering tests: use `content.index("narrative-block")` or `content.index("## Readiness Assessment")` < `content.index("<table")` pattern. For CLI ordering, call `build_exec_markdown()` with `exec_content` kwarg and assert narrative position.

---

### `tests/test_cross_surface_parity.py` (unit test — EXEC-04)

**Analog:** `tests/test_score_render_parity.py`

**Two-surface identity gate pattern** (`test_score_render_parity.py` lines 22-72):
```python
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.evidence import build_evidence_summary

FIXTURE_ENDPOINTS = []
FIXTURE_FINDINGS = []

def test_render_parity_all_surfaces():
    """D-04 gate: all render surfaces receive identical score values from same evidence."""
    evidence = build_evidence_summary(FIXTURE_ENDPOINTS, FIXTURE_FINDINGS)
    canonical = compute_readiness_score(evidence)

    writer_score = {"total": canonical["score"], "subscores": canonical["subscores"]}
    assert writer_score["total"] == canonical["score"], (
        f"writer.py 'total' key ({writer_score['total']}) diverges from canonical "
        f"'score' key ({canonical['score']}). RENDER-CLI-01 parity violated."
    )
```
For `test_cross_surface_parity.py`: call `build_exec_content(score_raw=score_raw, findings=[], roadmap_items=[])` once. Pass the same `exec_content` instance to both `build_exec_markdown()` (CLI path) and `render_html_report()` (HTML path). Assert `exec_content.narrative_lead` appears in CLI output AND HTML output. Assert `exec_content.top_risks` count equals count of risk items in HTML `.risks-list`.

---

## Shared Patterns

### Decision-tag comment convention
**Source:** `quirk/reports/executive.py` lines 10-14, 176; `quirk/reports/writer.py` line 12; `quirk/reports/html_renderer.py` lines 14-17
**Apply to:** All new and modified files in Phase 98
```python
# D-NN / REQ-ID (Phase PP): one-line rationale for this code.
from quirk.reports._md_escape import md_cell  # Phase 78 / HARDEN-01: wrap scanner-controlled cells
```

### GFM table cell escaping (HARDEN-01)
**Source:** `quirk/reports/_md_escape.py` (full file, 34 lines)
**Apply to:** All new markdown table cells and bullets in `executive.py` that include finding-derived text (risk sentence labels that embed finding titles, driver reason clauses)
```python
from quirk.reports._md_escape import md_cell
# Wrap: finding title, finding description, driver reason, owner placeholder, timeframe
# Do NOT wrap: static narrative lead sentences, rollup formula text
```

### HTML template escaping
**Source:** `quirk/reports/templates/report.html.j2` lines 142, 188, 203-204
**Apply to:** All new Jinja template variables that carry scanner-derived strings
```jinja
{{ value | sanitize }}          {# scanner-derived content #}
{{ static_string }}             {# template-static prose — no sanitize needed #}
```

### Lazy-import pattern for optional extras
**Source:** `quirk/reports/html_renderer.py` lines 86-103, 228-229, 244-248
**Apply to:** Any new imports of Playwright or pypdf in Phase 98 (no new ones expected; enforce via code review)
```python
# Inside function body only — never at module scope:
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    return False
```

### score_raw vs. compat wrapper key shapes
**Source:** `quirk/reports/writer.py` lines 158-170
**Apply to:** `content_model.py:build_exec_content()` and any test that constructs a score fixture
```python
# canonical (from compute_readiness_score):  score_raw["score"], score_raw["rating"], score_raw["subscores"]
# compat wrapper (writer.py internal):        score["total"],                          score["subscores"]
# build_exec_content() receives score_raw — use "score" key, not "total"
```

### `from __future__ import annotations`
**Source:** `quirk/reports/_md_escape.py` line 8; `quirk/intelligence/schema.py` line 1; `quirk/errors.py` line 9
**Apply to:** `quirk/reports/content_model.py` and all new test files
```python
from __future__ import annotations
```

---

## No Analog Found

All files have close analogs. No entries.

---

## Metadata

**Analog search scope:** `quirk/reports/`, `quirk/intelligence/`, `quirk/errors.py`, `quirk/config.py`, `tests/`
**Files scanned:** 14 (executive.py, html_renderer.py, writer.py, report.html.j2, _md_escape.py, schema.py, errors.py, config.py, test_score_transparency.py, test_html_report.py, test_executive_score_guard.py, test_score_render_parity.py, CONTEXT.md, RESEARCH.md)
**Pattern extraction date:** 2026-05-24
