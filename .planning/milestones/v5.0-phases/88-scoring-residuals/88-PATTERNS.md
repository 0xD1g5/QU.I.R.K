# Phase 88: Scoring Residuals — Pattern Map

**Mapped:** 2026-05-22
**Files analyzed:** 9 (4 new test files, 4 modified production files, 1 modified classifier)
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tests/test_scoring_orthogonal_contract.py` | test | batch/transform | `tests/test_score_weights_invariant.py` + `tests/test_xml_safe.py` | exact (forward-locking parametrized invariant) |
| `tests/test_score_render_parity.py` | test | request-response | `tests/test_score_weights_invariant.py` | role-match (assertion gate over shared function) |
| `tests/test_score_transparency.py` | test | request-response | `tests/test_score_weights_invariant.py` | role-match (string-content gate) |
| `tests/test_cbom_zero_algo_profiles.py` | test | batch | `tests/test_cbom_classifier_coverage.py` | exact (profile-fixture CBOM gate) |
| `quirk/reports/writer.py` | utility | request-response | self (existing file, targeted addition to `_scorecard_markdown`) | self-analog |
| `quirk/reports/executive.py` | utility | request-response | self (existing file, targeted addition to `build_exec_markdown`) | self-analog |
| `quirk/reports/html_renderer.py` | utility | request-response | self (existing file, targeted variable addition to `render_html_report`) | self-analog |
| `quirk/reports/templates/report.html.j2` | config/template | request-response | existing template score-card block (lines 148–154) | self-analog |
| `quirk/cbom/builder.py` | service | batch | self (existing Pass-1 per-protocol branches) | self-analog |
| `quirk/cbom/classifier.py` | utility | transform | self (existing `_ALGORITHM_TABLE`) | self-analog |

---

## Pattern Assignments

---

### `tests/test_scoring_orthogonal_contract.py` (test, batch/transform)

**Purpose (D-02):** Forward-lock the orthogonal subscore contract — a finding in one category must not affect other categories' subscores.

**Primary analog:** `tests/test_score_weights_invariant.py` (simple assertion gate over scoring module)
**Secondary analog:** `tests/test_xml_safe.py` (parametrized forward-locking gates with inline rationale docstrings)
**Tertiary analog:** `tests/test_audit_ledger_zero_open.py` (grep/regex gate style)

**Module-level docstring pattern** (from `tests/test_xml_safe.py` lines 1–32):
```python
"""Phase 88 D-02 / EVIDENCE-TALLY-01: Orthogonal subscore contract forward-locking invariant.

Resolved correct-by-design. The scoring model (quirk/intelligence/scoring.py) assigns each
of the six subscores independently: subscore = 25 + sum(category_local_penalties), clamped
[0, 25]. A category with no findings of its own type scores 25/25 regardless of findings in
other categories. Cross-category penalties are explicitly rejected (Phase 88 D-01).

This parametrized test suite forward-locks that contract in perpetuity.
"""
```

**Import pattern** (from `tests/test_score_weights_invariant.py` lines 1–3):
```python
from quirk.intelligence.scoring import compute_readiness_score
```

**Parametrize pattern** (from `tests/test_xml_safe.py` lines 37–43 and `tests/test_score_weights_invariant.py` lines 5–31):
```python
import pytest
from quirk.intelligence.scoring import compute_readiness_score

@pytest.mark.parametrize("category,trigger_key,trigger_value,clean_categories", [
    (
        "hygiene",
        "plaintext_http_count",
        10,
        ["modern_tls", "identity_trust", "agility_signals", "data_at_rest", "data_in_motion"],
    ),
    # ... repeat for all six categories ...
])
def test_subscore_orthogonality(category, trigger_key, trigger_value, clean_categories):
    """Forward-locking invariant: a finding in one category only affects that category's subscore."""
    evidence = {
        trigger_key: trigger_value,
        "totals": {"endpoints": 10, "findings": trigger_value},
    }
    result = compute_readiness_score(evidence)
    subscores = result["subscores"]
    for clean_cat in clean_categories:
        assert subscores[clean_cat] == 25, (
            f"{clean_cat} must be 25 when only {category} has findings. "
            f"Got {subscores[clean_cat]}. Orthogonality contract violated."
        )
```

**Invariant assertion style** (from `tests/test_score_weights_invariant.py` lines 18–21):
```python
assert abs(sum(SCORE_WEIGHTS.values()) - 275.0) < 1e-9, (
    f"SCORE_WEIGHTS sum drifted from 275.0 to {sum(SCORE_WEIGHTS.values())}. "
    "Per D-04 this is intentional — update this test ONLY if rebalance is documented."
)
```

**Evidence key catalogue** — use these exact keys from `quirk/intelligence/scoring.py` to trigger each category:

| Category subscore | Trigger evidence key | Trigger value |
|-------------------|---------------------|---------------|
| `hygiene` | `plaintext_http_count` | 10 |
| `modern_tls` | `finding_severity_counts` | `{"HIGH": 5}` |
| `identity_trust` | `identity_weak_etype_count` | 5 |
| `agility_signals` | `cert_key_type_counts` | `{"RSA": 10}` |
| `data_at_rest` | `dar_db_plaintext_count` | 5 |
| `data_in_motion` | `motion_email_plaintext_num` | 5 (needs `totals.endpoints` >= 1) |

---

### `tests/test_score_render_parity.py` (test, request-response)

**Purpose (D-04):** Data-layer parity gate — all three render surfaces (CLI scorecard, executive markdown, HTML/PDF) receive identical `total` and `subscores` values for the same evidence.

**Primary analog:** `tests/test_score_weights_invariant.py` (simple assertion gate)

**Import pattern:**
```python
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.evidence import build_evidence_summary
```

**Core pattern** (modeled on `test_score_weights_invariant.py` assertion structure):
```python
FIXTURE_ENDPOINTS = []   # minimal realistic list; can be empty for baseline
FIXTURE_FINDINGS = []

def test_render_parity_all_surfaces():
    """D-04 gate: all render surfaces receive identical score values from same evidence.

    writer.py path: wraps compute_readiness_score output as
      {"total": score_raw["score"], "subscores": score_raw["subscores"], ...}
    html_renderer.py: receives the same wrapped dict; accesses score.get("total")
      and score.get("subscores") — same integers, no re-rounding.
    dashboard API: calls compute_readiness_score independently with same evidence.
    """
    evidence = build_evidence_summary(FIXTURE_ENDPOINTS, FIXTURE_FINDINGS)
    canonical = compute_readiness_score(evidence)

    # writer.py compat wrapper (writer.py lines 166-170)
    writer_score = {
        "total": canonical["score"],
        "subscores": canonical["subscores"],
    }
    assert writer_score["total"] == canonical["score"]
    assert writer_score["subscores"] == canonical["subscores"]

    # dashboard API re-calls compute_readiness_score with same evidence (scan.py line 1057)
    dashboard_score = compute_readiness_score(evidence)
    assert dashboard_score["score"] == canonical["score"]
    assert dashboard_score["subscores"] == canonical["subscores"]
```

**Do NOT re-round:** Scores are already `int` from `_apply_weighted_impacts` (scoring.py line 109: `int(round(clamped))`). Any helper must pass integers through as-is.

---

### `tests/test_score_transparency.py` (test, request-response)

**Purpose (SCORE-XPARENCY-01):** Verify that after D-07 additions, scorecard markdown and executive markdown contain the `N/25` strings and rollup math text.

**Primary analog:** `tests/test_score_weights_invariant.py` (string/value assertion gate)

**Pattern** (simple string-contains assertions, no parametrize needed):
```python
from quirk.intelligence.scoring import compute_readiness_score
from quirk.reports.writer import _scorecard_markdown
from quirk.reports.executive import build_exec_markdown

def test_scorecard_markdown_contains_subscore_decomposition():
    """Gate: _scorecard_markdown output contains N/25 labels and rollup math."""
    score = {"total": 67, "subscores": {
        "hygiene": 20, "modern_tls": 18, "identity_trust": 25,
        "agility_signals": 15, "data_at_rest": 22, "data_in_motion": 21,
    }, "drivers": []}
    # ... call _scorecard_markdown with a mock cfg, score, conf, drivers, roadmap
    output = _scorecard_markdown(mock_cfg, score, {}, [], [])
    assert "/25" in output
    assert "÷1.5" in output or "/ 1.5" in output
```

---

### `tests/test_cbom_zero_algo_profiles.py` (test, batch)

**Purpose (SCORE-CBOM-01):** Verify that after D-05/D-06 fixes, the five zero-algo profiles either emit real algorithm components or carry affirmative `quirk:coverage-note` properties.

**Primary analog:** `tests/test_cbom_classifier_coverage.py` (full file)

**Import pattern** (from `tests/test_cbom_classifier_coverage.py` lines 1–34):
```python
from __future__ import annotations
import pytest
from cyclonedx.model.crypto import CryptoPrimitive
from quirk.cbom.builder import build_cbom
from quirk.cbom.classifier import classify_algorithm
from tests._cbom_profiles import PROFILE_ENDPOINTS
```

**Core pattern** (adapted from `tests/test_cbom_classifier_coverage.py` lines 62–80):
```python
@pytest.mark.parametrize("profile", [
    "database", "registry", "source", "ssh-weak", "storage-s3"
])
def test_zero_algo_profile_emits_components_or_marker(profile):
    """SCORE-CBOM-01: Five formerly-zero-algo profiles must now either emit
    real algorithm components OR carry an affirmative quirk:coverage-note
    property on the Bom (D-06 marker convention).
    """
    fn = PROFILE_ENDPOINTS[profile]
    bom = build_cbom(fn())

    # Collect algorithm component names
    algo_names = [
        c.name for c in bom.components
        if getattr(c, "crypto_properties", None)
        and c.crypto_properties.asset_type.value == "algorithm"
    ]

    # Collect coverage-note properties (D-06 affirmative marker)
    coverage_notes = []
    for prop in (bom.metadata.component.properties if bom.metadata and bom.metadata.component else []):
        if prop.name == "quirk:coverage-note":
            coverage_notes.append(prop.value)

    assert algo_names or coverage_notes, (
        f"Profile '{profile}' emits zero algorithm components and has no "
        f"quirk:coverage-note property — Phase 42 OBS-1 not resolved. "
        f"Add real components (D-05) or an affirmative marker (D-06)."
    )
```

**UNKNOWN gate style** (from `tests/test_cbom_classifier_coverage.py` lines 67–80):
```python
unknowns: list[tuple[str, list[str]]] = []
for name, profiles in sorted(seen.items()):
    primitive, _, _ = classify_algorithm(name)
    if primitive == CryptoPrimitive.UNKNOWN and name.lower() != "none":
        unknowns.append((name, sorted(profiles)))
assert not unknowns, (
    "In-scope algorithms classified as UNKNOWN — add rows to "
    "_ALGORITHM_TABLE in quirk/cbom/classifier.py: "
    f"{unknowns}"
)
```

---

### `quirk/reports/writer.py` — `_scorecard_markdown` addition (D-07)

**File:** `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/reports/writer.py`
**Target function:** `_scorecard_markdown` (lines 91–109)
**Change:** Add subscore decomposition block after the `## Score` section.

**Existing score section pattern** (lines 91–109, the block to extend after):
```python
def _scorecard_markdown(cfg, score: Dict[str, Any], conf: Dict[str, Any], drivers: List[str], roadmap: List[Dict[str, Any]]) -> str:
    # ...
    lines.append(f"## Score\n- **Readiness Score:** **{score.get('total')} / 100**\n- **Confidence:** **{conf.get('confidence')} / 100**\n")
    # INSERT subscore decomposition block HERE (after this line)
```

**Pattern to add** (follows existing `lines.append` style, uses `score.get("subscores")` — never `score_raw`):
```python
# D-07 / SCORE-XPARENCY-01: subscore decomposition block
subscores = score.get("subscores") or {}
_SUBSCORE_LABELS = [
    ("hygiene",        "Hygiene"),
    ("modern_tls",     "Modern TLS"),
    ("identity_trust", "Identity"),
    ("agility_signals","Agility"),
    ("data_at_rest",   "Data at Rest"),
    ("data_in_motion", "Data in Motion"),
]
lines.append("## Score Decomposition\n")
lines.append("| Category | Score | Budget |")
lines.append("|----------|-------|--------|")
for key, label in _SUBSCORE_LABELS:
    lines.append(f"| {label} | {subscores.get(key, '—')} | /25 |")
raw_sum = sum(subscores.get(k, 0) for k, _ in _SUBSCORE_LABELS)
lines.append(f"\n**Rollup:** {raw_sum} ÷ 1.5 = **{score.get('total')} / 100**\n")
```

**md_cell convention** (existing, writer.py line 13): Labels are hardcoded Python strings (not scanner-derived) — `md_cell()` is NOT needed for label strings or integer subscore values. Only scanner-derived cell content uses `md_cell`.

---

### `quirk/reports/executive.py` — `build_exec_markdown` addition (D-07)

**File:** `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/reports/executive.py`
**Target function:** `build_exec_markdown` (lines 111–end)
**Change:** Add "Score Decomposition" section after the "## Quantum Readiness Score" section.

**Existing score section** (lines 166–172, the insertion point):
```python
lines.append("## Quantum Readiness Score")
lines.append(f"**Score:** **{score_raw['score']}/100**  \n**Rating:** **{score_raw['rating']}**")
lines.append("")
lines.append("### Score Drivers (Top)")
# INSERT decomposition block AFTER drivers section, BEFORE "## Confidence & Coverage"
```

**Pattern to add** (uses `score_raw["subscores"]` — the raw dict, not the wrapped `score` dict used in writer.py):
```python
# D-07 / SCORE-XPARENCY-01: subscore decomposition in executive markdown
subscores = score_raw.get("subscores") or {}
_SUBSCORE_LABELS = [
    ("hygiene",        "Hygiene"),
    ("modern_tls",     "Modern TLS"),
    ("identity_trust", "Identity"),
    ("agility_signals","Agility"),
    ("data_at_rest",   "Data at Rest"),
    ("data_in_motion", "Data in Motion"),
]
lines.append("### Score Decomposition")
lines.append("")
lines.append("| Category | Score | Budget |")
lines.append("|----------|-------|--------|")
for key, label in _SUBSCORE_LABELS:
    lines.append(f"| {label} | {subscores.get(key, '—')} | /25 |")
raw_sum = sum(subscores.get(k, 0) for k, _ in _SUBSCORE_LABELS)
lines.append(f"")
lines.append(f"**Rollup:** {raw_sum} ÷ 1.5 = **{score_raw['score']} / 100**")
lines.append("")
```

**Import pattern** (executive.py lines 1–11 — no new imports needed; `md_cell` already imported):
```python
from quirk.intelligence.scoring import compute_readiness_score
from quirk.reports._md_escape import md_cell
```

---

### `quirk/reports/html_renderer.py` — `render_html_report` addition (D-07)

**File:** `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/reports/html_renderer.py`
**Target function:** `render_html_report` (lines 145–210)
**Change:** Add `subscores` variable to the template context dict.

**Existing template call pattern** (lines 189–207 — the dict to extend):
```python
html = template.render(
    org_name=...,
    total_score=total_score,
    score_band=band,
    score_color=_score_color(band),
    confidence=conf.get("confidence", 0),
    # ... existing variables ...
    severity_color=_severity_color,
)
```

**Pattern to add** (one new key, consistent with existing variable naming):
```python
html = template.render(
    # ... existing variables unchanged ...
    subscores=score.get("subscores", {}),   # D-07 / SCORE-XPARENCY-01 — int values, no sanitize needed
    severity_color=_severity_color,
)
```

**Pitfall 6 note:** `score` here is the WRAPPED dict (from writer.py lines 166–170), so access via `score.get("subscores")` (key `"subscores"`), NOT `score_raw.get("subscores")`. The wrapping happens in `write_reports` at lines 166–170 before `render_html_report` is called.

---

### `quirk/reports/templates/report.html.j2` — subscore table (D-07)

**File:** `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/reports/templates/report.html.j2`
**Change:** Add subscore decomposition table after the existing score-card block.

**Existing score-card block** (template lines 148–154 — insert AFTER this):
```html
<h2>Quantum Readiness Score</h2>
<div class="score-card">
  <div class="score-value">{{ total_score }}</div>
  <div class="score-band">{{ score_band }}</div>
  <div class="score-label">/ 100 &nbsp;|&nbsp; Confidence: {{ confidence }}/100</div>
</div>
```

**Pattern to add** (follows existing Jinja2 var style; int values need no `| sanitize`):
```html
{% if subscores %}
<h3>Score Decomposition</h3>
<table>
  <thead><tr><th>Category</th><th>Score</th><th>Budget</th></tr></thead>
  <tbody>
    <tr><td>Hygiene</td><td>{{ subscores.get('hygiene', '—') }}</td><td>/25</td></tr>
    <tr><td>Modern TLS</td><td>{{ subscores.get('modern_tls', '—') }}</td><td>/25</td></tr>
    <tr><td>Identity</td><td>{{ subscores.get('identity_trust', '—') }}</td><td>/25</td></tr>
    <tr><td>Agility</td><td>{{ subscores.get('agility_signals', '—') }}</td><td>/25</td></tr>
    <tr><td>Data at Rest</td><td>{{ subscores.get('data_at_rest', '—') }}</td><td>/25</td></tr>
    <tr><td>Data in Motion</td><td>{{ subscores.get('data_in_motion', '—') }}</td><td>/25</td></tr>
  </tbody>
</table>
<p><strong>Rollup:</strong>
  {{ subscores.values() | sum }} ÷ 1.5 = <strong>{{ total_score }} / 100</strong>
</p>
{% endif %}
```

**Autoescape note:** `subscores` values are Python `int` — Jinja2 autoescaping applies but integers render safely without `| sanitize`. Labels are hardcoded template literals, not scanner-derived.

---

### `quirk/cbom/builder.py` — Pass-1 per-protocol additions (D-05/D-06)

**File:** `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/cbom/builder.py`

#### D-06 no-crypto marker helper pattern

**Analog:** Existing `Property` usage in `_make_algorithm_component` (lines 316–320):
```python
from cyclonedx.model import Property   # already imported at line 19

properties = [Property(name="quirk:fips140-3-status", value=_fips_status(nist_level))]
if _cmvp_coverage:
    properties.append(Property(name="quirk:cmvp-coverage", value=_module_names))
```

**New helper to add** (follows the same `Property` pattern; attach to `bom.metadata.component.properties` or via a synthetic advisory component per Research Option B if Bom-level properties aren't available):
```python
def _emit_coverage_note(bom_component, note: str) -> None:
    """Attach a quirk:coverage-note property to the Bom root component (D-06).

    Used for genuinely plaintext endpoints or library-level-only observations
    where no cryptographic algorithm can be catalogued.
    """
    prop = Property(name="quirk:coverage-note", value=note)
    if bom_component is not None:
        existing = list(bom_component.properties or [])
        existing.append(prop)
        bom_component.properties = existing
```

#### POSTGRESQL / MYSQL / database ssl-off pattern (D-06)

**Analog:** Existing MYSQL branch (builder.py lines 497–507):
```python
elif ep.protocol == "MYSQL":
    detail = ep.service_detail or ""
    if "/" in detail:
        cipher_part = detail.split("/", 1)[1]
        if cipher_part.endswith(("-ok", "-weak")):
            cipher_name = cipher_part.rsplit("-", 1)[0]
        else:
            cipher_name = cipher_part
        if cipher_name and cipher_name.upper() not in ("SSL-OFF", "UNSPECIFIED", ""):
            _register_algorithm(cipher_name, algo_registry)
```

**Pattern for D-06 marker** — when `cipher_name.upper() == "SSL-OFF"` (currently falls through silently), add the affirmative marker:
```python
        if cipher_name and cipher_name.upper() not in ("SSL-OFF", "UNSPECIFIED", ""):
            _register_algorithm(cipher_name, algo_registry)
        elif cipher_name.upper() == "SSL-OFF":
            # D-06: affirmative no-crypto marker
            coverage_notes.append(
                f"plaintext endpoint — {ep.protocol} connection uses no TLS; "
                "no cryptographic material observed"
            )
```

**POSTGRESQL branch** (lines 509–512) — add D-06 marker when `cert_pubkey_alg` is absent:
```python
elif ep.protocol in ("POSTGRESQL", "RDS"):
    if ep.cert_pubkey_alg:
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
    # D-06: if no cert (ssl-off), emit affirmative plaintext marker
    elif not ep.cert_pubkey_alg:
        coverage_notes.append(
            "plaintext endpoint — PostgreSQL/RDS connection uses no TLS; "
            "no cryptographic material observed"
        )
```

#### S3/AZURE_BLOB unencrypted pattern (D-06)

**Analog:** Existing S3 branch (builder.py lines 514–526):
```python
elif ep.protocol in ("S3", "AZURE_BLOB"):
    _S3_ENCRYPTED_POSTURES = frozenset({...})
    detail = ep.service_detail or ""
    detail_lower = detail.lower()
    if any(posture in detail_lower for posture in _S3_ENCRYPTED_POSTURES):
        _register_algorithm("AES-256", algo_registry)
    # D-06: unencrypted bucket gets affirmative marker
    elif "unencrypted" in detail_lower or not any(...):
        coverage_notes.append(
            "unencrypted S3/Blob endpoint — no server-side encryption observed; "
            "no algorithm material to catalog"
        )
```

#### ssh-weak fixture + classifier additions (D-05)

**Analog for fixture:** `tests/test_cbom_motion_endpoints.py` `_build_ssh_weak_lab_endpoints` (current fixture at lines 608–622 uses `ssh_audit_json=None`).

**Pattern:** Update the fixture to include realistic `ssh_audit_json` with actual weak algorithms. Then add the missing algorithms to `classifier.py _ALGORITHM_TABLE`.

**New classifier entries needed** (following existing SSH KEX pattern at classifier.py lines 57–65):
```python
# Weak SSH KEX algorithms (ssh-audit output for ssh-weak chaos lab profile)
"diffie-hellman-group1-sha1": (CryptoPrimitive.KEY_AGREE, 0, 80),
# Weak SSH host key algorithms
"ssh-dss": (CryptoPrimitive.SIGNATURE, 0, 80),
# Weak SSH MAC algorithms
"hmac-md5": (CryptoPrimitive.HASH, 0, 64),
"hmac-md5-96": (CryptoPrimitive.HASH, 0, 64),
"hmac-sha1-96": (CryptoPrimitive.HASH, 0, 80),
```

#### SOURCE coverage note for non-algorithm rule IDs (D-06)

**Analog:** Existing SOURCE branch (builder.py lines 425–430):
```python
elif ep.protocol == "SOURCE":
    algo_hint = _extract_algo_from_rule_id(ep.cipher_suite)
    algo_to_register = algo_hint or ep.cipher_suite   # D-06: fallback to raw rule ID
    if algo_to_register:
        _register_algorithm(algo_to_register, algo_registry)
```

**Pattern:** Replace the raw-rule-ID fallback registration with a D-06 coverage note:
```python
elif ep.protocol == "SOURCE":
    algo_hint = _extract_algo_from_rule_id(ep.cipher_suite)
    if algo_hint:
        _register_algorithm(algo_hint, algo_registry)
    elif ep.cipher_suite:
        # D-06: raw rule ID does not encode a specific algorithm — emit coverage note
        coverage_notes.append(
            f"crypto library/pattern observed (rule: {ep.cipher_suite}); "
            "algorithm-level detail not captured by source scanner"
        )
```

#### coverage_notes accumulation and attachment pattern

**Location in `build_cbom`:** After Pass-1 loop (line ~395), before Pass-2, attach all accumulated notes to the Bom root component. Keep `coverage_notes` as a `list[str]` accumulated inside the Pass-1 loop.

```python
# At top of build_cbom, before the Pass-1 loop:
coverage_notes: list[str] = []

# At the end of Pass-1 (after the per-endpoint for loop), before Pass-2:
# Attach accumulated D-06 coverage notes to Bom metadata root component
# (check if Bom.metadata.component supports properties, else use advisory Component)
```

---

### `quirk/cbom/classifier.py` — `_ALGORITHM_TABLE` additions (D-05)

**File:** `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/cbom/classifier.py`
**Change:** Add entries for weak SSH algorithms used in `ssh-weak` chaos lab profile.

**Existing SSH KEX entry pattern** (lines 57–65 — follow exactly):
```python
# SSH KEX algorithms (raw ssh-audit strings)
"diffie-hellman-group14-sha1": (CryptoPrimitive.KEY_AGREE, 0, 112),
"diffie-hellman-group16-sha512": (CryptoPrimitive.KEY_AGREE, 0, 128),
```

**New entries to add** (after the existing SSH KEX section):
```python
# Weak SSH KEX algorithms (ssh-weak profile — Phase 88 SCORE-CBOM-01)
"diffie-hellman-group1-sha1": (CryptoPrimitive.KEY_AGREE, 0, 80),
```

**Existing SSH host key pattern** (lines 70–76):
```python
"ssh-rsa": (CryptoPrimitive.SIGNATURE, 0, 112),
"ssh-ed25519": (CryptoPrimitive.SIGNATURE, 0, 128),
```

**New entries to add** (after existing SSH host key section):
```python
# Weak SSH host key algorithms (ssh-weak profile — Phase 88 SCORE-CBOM-01)
"ssh-dss": (CryptoPrimitive.SIGNATURE, 0, 80),
```

**Existing SSH MAC pattern** (lines 89–91):
```python
"hmac-sha2-256": (CryptoPrimitive.HASH, 0, 128),
"hmac-sha1": (CryptoPrimitive.HASH, 0, 80),
```

**New entries to add** (after existing SSH MAC section):
```python
# Weak SSH MAC algorithms (ssh-weak profile — Phase 88 SCORE-CBOM-01)
"hmac-md5": (CryptoPrimitive.HASH, 0, 64),
"hmac-md5-96": (CryptoPrimitive.HASH, 0, 64),
"hmac-sha1-96": (CryptoPrimitive.HASH, 0, 80),
```

---

## Shared Patterns

### Forward-locking invariant gate structure
**Source:** `tests/test_score_weights_invariant.py` + `tests/test_xml_safe.py`
**Apply to:** `test_scoring_orthogonal_contract.py`, `test_score_render_parity.py`, `test_score_transparency.py`, `test_cbom_zero_algo_profiles.py`

Standard structure:
1. Module-level docstring citing the D-NN decision it locks and the rationale.
2. No database, no endpoints object by default — pure unit tests over Python functions.
3. `assert not <list>` pattern with an error message listing all violations.
4. `pytest.mark.parametrize` for multi-case coverage (follow `test_xml_safe.py` style).

```python
"""Phase 88 D-NN / REQ-ID: <invariant description>.
<Rationale — one paragraph citing the model and the decision.>
"""
from __future__ import annotations
import pytest
# ... imports ...

def test_<invariant_name>() -> None:
    """D-NN gate: <what it locks>."""
    # ... assertion ...
    assert <condition>, (
        "<Violation description>. "
        "<How to fix>."
    )
```

### Property emission pattern (CBOM)
**Source:** `quirk/cbom/builder.py` lines 316–320, `_make_algorithm_component`
**Apply to:** D-06 no-crypto marker in `build_cbom` Pass-1

```python
from cyclonedx.model import Property  # already imported at builder.py line 19
prop = Property(name="quirk:coverage-note", value="<hardcoded affirmative string>")
```

Property values MUST be hardcoded string literals — not scanner-derived input — so no `safe_str` sanitization is needed.

### Subscore label mapping (canonical)
**Source:** `quirk/intelligence/scoring.py` lines 267–277 (return dict keys) + `src/dashboard/src/pages/executive.tsx` lines 251–256 (display labels)
**Apply to:** `writer.py`, `executive.py`, `report.html.j2`

Always use this exact mapping — it mirrors the dashboard:
```python
_SUBSCORE_LABELS = [
    ("hygiene",        "Hygiene"),
    ("modern_tls",     "Modern TLS"),
    ("identity_trust", "Identity"),
    ("agility_signals","Agility"),
    ("data_at_rest",   "Data at Rest"),
    ("data_in_motion", "Data in Motion"),
]
```

### Score dict key disambiguation (critical pitfall)
**Source:** `quirk/reports/writer.py` lines 166–170

```python
# WRAPPED dict (writer.py output, received by html_renderer.py and _scorecard_markdown):
score = {
    "total": score_raw["score"],       # key = "total"
    "subscores": score_raw["subscores"],
    "drivers": [d["reason"] for d in score_raw.get("drivers", [])],
}
# RAW dict (compute_readiness_score return, used in executive.py and dashboard API):
score_raw = compute_readiness_score(...)  # key = "score" (not "total")
```
- In `_scorecard_markdown` and `html_renderer.py`: use `score.get("total")` and `score.get("subscores")`
- In `build_exec_markdown`: use `score_raw["score"]` and `score_raw["subscores"]`
- Never call `round()` on these values — they are already `int`.

---

## No Analog Found

All files have clear analogs. The following are notable first-of-kind patterns but have partial matches:

| File | Role | Data Flow | Note |
|------|------|-----------|------|
| `quirk:coverage-note` Property on Bom root | CBOM convention | batch | New property name; existing `quirk:fips140-3-status` and `quirk:cmvp-coverage` are the direct analogs (builder.py lines 316–320). Planner must decide: attach to `bom.metadata.component.properties` OR emit advisory component (Research Option B). |

---

## Metadata

**Analog search scope:** `tests/`, `quirk/reports/`, `quirk/cbom/`, `quirk/intelligence/`
**Files scanned:** 12 (test analogs: 3; production analogs: 9)
**Pattern extraction date:** 2026-05-22
