# Phase 74: QRAMM + Compliance WARNINGs - Research

**Researched:** 2026-05-15
**Domain:** QRAMM scoring + evidence bridge + compliance map + migration advisor hardening (13 open WARNING rows)
**Confidence:** HIGH (every file:line in CONTEXT.md verified against HEAD `cf2417a`)

## Summary

Phase 74 closes 13 open WARNING rows (`qramm-compliance/WR-01..WR-13`) clustered around QRAMM scoring correctness (QWARN-01), evidence-bridge robustness (QWARN-02), and compliance-map / migration-advisor / staleness-helper hygiene (QWARN-03). CONTEXT.md locks 12 implementation decisions (D-01..D-12) plus D-14 do-not-touch. This research verifies each cite, identifies the actual fix sites at HEAD, surveys reusable precedent (Phase 73 `weak_crypto.py`, Phase 49 `STALENESS_THRESHOLD_DAYS` pattern, existing `tests/test_qramm_staleness.py` duplicated date math), and **surfaces nine discrepancies between CONTEXT wording and current code** that the planner must adjudicate without re-opening locked decisions (see `<research_concerns>`).

**Primary recommendation:** Three plans, one per QWARN-NN requirement — mirroring Phase 73's structure exactly. The largest single item is D-08's migration-advisor refactor; it is best treated as a from-scratch substitution because the current `migration_advisor.py` matches finding *titles* (not algorithm strings), so D-08's "word-boundary on algorithm names" requires both (a) introducing a NEW per-finding algorithm-aware code path AND (b) defining `CANONICAL_ALG_SYNONYMS`. The remaining 12 fixes are surgical (<20-line edits).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

All 12 decisions D-01 through D-12 (plus D-14 do-not-touch) are locked in `.planning/phases/74-qramm-compliance-warnings/74-CONTEXT.md`:

- **D-01** — `quirk/qramm/scoring.py::compute_practice_score` validates each answer ∈ {0,1,2,3,4} BEFORE summation; out-of-range raises `ValueError(f"Practice score answer {answer!r} for {practice_id} out of range [0, 4]")`. Fail-loud; do NOT silently clamp.
- **D-02** — Practice 1.1 Discovery score multiplied by `discovery_factor = min(1.0, max(0.25, math.log10(max(endpoint_count, 1)) / 3.0))`. `endpoint_count` sourced from existing local variable (researcher confirmed — see C-1).
- **D-02a (discretion)** — Curve shape: log10 default; researcher picks if clearer pattern fits.
- **D-03** — `vuln_pct = None` (sentinel) when `total_algos == 0`; maturity label becomes `"Indeterminate"`; NEW sibling band (not numeric tier); excluded from cohort stats; rendered with em-dash subscore in HTML/PDF/`ComplianceMapTab`.
- **D-04** — Adjust band so `>= 4.0` reachable at multiplier=1.0 ceiling: either lower threshold to `>= 3.95` OR raise underlying score ceiling. Researcher picks minimal change (see C-2). Parametrized test asserts both 3.99 and 4.0 land in top band.
- **D-05** — `quirk/qramm/evidence_bridge.py` date equality: parse both sides via `datetime.date.fromisoformat(s)` and compare `date_a == date_b`. If `datetime` (has time component), call `.date()` first. Researcher confirms call sites supply dates not datetimes (see C-3).
- **D-06** — Idempotent UPDATE: BEFORE the UPDATE, query existing target rows; skip if desired state already matches. Wrap UPDATE in `try/except SQLAlchemyError as e: logger.warning("evidence_bridge UPDATE failed: %s", e); db.rollback(); return` (also closes WR-07).
- **D-07** — `attach_context` `except AttributeError:` → `except AttributeError as e: logger.warning("attach_context skipped — source object missing attribute: %s", e)`.
- **D-08** — `quirk/assessment/migration_advisor.py` substring matching replaced with word-boundary regex + module-level `CANONICAL_ALG_SYNONYMS` synonym map + `_matches(canonical, text)` helper. (See C-4 — current advisor matches on finding *title*, not algorithm strings; D-08 introduces an algorithm-aware code path.)
- **D-09** — Extend `_walk_json_for_alg_strings`: after the keyed check, ALSO scan ALL string values for canonical algorithm tokens via `migration_advisor::_matches` (or lightweight inline variant). Researcher picks reuse vs inline.
- **D-10** — Add `coverage_status: Literal['covered', 'partial', 'pending', 'n/a']` to compliance_map entries. Semantics: covered=full-weight; partial=half-weight; pending/n_a=excluded from rollup. Migration: every existing entry gets `'covered'`; entries with `weight=0.0` flip to `'pending'`. CI gate test asserts every entry has valid status. Renders in HTML/PDF compliance table as new column. (See C-5 — "weight=0.0 entries" do not exist in `QRAMM_COMPLIANCE_WEIGHTS`; weight=0.0 lives on `SCANNER_COVERAGE` dimension ceilings instead.)
- **D-10a (discretion)** — Whether rollup excludes 'partial' or counts at half-weight. Default half-weight.
- **D-11** — Add public function `is_qramm_model_stale(today=None)` in `quirk/qramm/model_meta.py` using existing `STALENESS_THRESHOLD_DAYS` + `last_verified`. Used by Phase 75 `quirk doctor` + CI workflow. Test injects synthetic `today` to exercise both branches. (See C-6 — module has no `LAST_VERIFIED` constant; `last_verified` is nested in `QRAMM_MODEL["last_verified"]`.)
- **D-12** — Locate stale `# TODO Phase 50:` comment in production module header; delete. Verify via `git blame`. If cites work that did NOT land, capture in deferred-items.md before deletion. (Located at `quirk/compliance/__init__.py:3` — see Pitfall 8.)
- **D-14 (do-not-touch)** —
  - QRAMM 120-question taxonomy (`questions.py`) — no question text/structure changes
  - 5-band maturity scale itself — only the >=4.0 reachability + new 'Indeterminate' label
  - `quirk/engine/migration_planner.py` — `wont-fix` stub
  - `tests/test_compliance_freshness.py` — Phase 49/50/56 invariant (D-10 adds NEW test, does NOT modify existing)
  - QRAMM evidence bridge BLOCKERs (closed by Phase 70) — only WR rows in this phase

### Claude's Discretion

- D-02a (curve shape), D-10a (partial-weight rollup)

### Deferred Ideas (OUT OF SCOPE)

- Per-framework `coverage_status` granularity (one status per control vs per row) — capture if operators request
- `'Indeterminate'` as numeric maturity tier — v5.0 scoring refactor
- Synonym map externalization to YAML — revisit if map grows beyond ~20 algorithms
- `quirk doctor is-qramm-stale` CLI subcommand — Phase 75 wires `is_qramm_model_stale()` into doctor output
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QWARN-01 | Practice scoring correctness (closes WR-02, WR-04, WR-05, WR-06) | D-01 fail-loud pattern matches Phase 70 `_SAFE_COL_TYPE_RE`; D-02 endpoint factor — `endpoint_count` source = local `total_endpoints` in `evidence_bridge.py:59` (NOT `evidence_summary.endpoint_count` per CONTEXT wording — see C-1); D-03 sentinel + 'Indeterminate' label requires new sibling band in `scoring.py::_maturity_label`; D-04 reachability fix is one-line either at line 56 (`min(4.0, …)` clamp) or line 76 (`>= 4.0` band threshold) |
| QWARN-02 | Evidence bridge correctness (closes WR-01, WR-03, WR-07, WR-08) | D-05 — current code compares `max_date_str` (string from `func.date(func.max(...))`) against `func.date(CryptoEndpoint.scanned_at)` SQL column — both server-side; D-06 idempotency needs pre-query check at `evidence_bridge.py:114-126`; D-07 site = `quirk/assessment/operator_context.py:74-98` — current code uses BARE `except Exception` (NOT `except AttributeError` as CONTEXT D-07 says — see C-7) |
| QWARN-03 | Migration advisor + compliance map + meta (closes WR-09, WR-10, WR-11, WR-12, WR-13) | D-08 — current advisor at `quirk/assessment/migration_advisor.py:14-76` matches FINDING TITLES not algorithm strings (see C-4); D-09 site verified at `quirk/qramm/evidence_bridge.py:165-204` (208 lines total — CONTEXT line ref correct); D-10 site = `compliance_map.py` BUT applies to `SCANNER_COVERAGE` dims (3 zero-weight entries) not `QRAMM_COMPLIANCE_WEIGHTS` (zero entries have weight=0.0) — see C-5; D-11 helper consumes `QRAMM_MODEL["last_verified"]` (nested) not bare `LAST_VERIFIED` — see C-6; D-12 located at `quirk/compliance/__init__.py:3` (`# TODO Phase 50`) — single match |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Practice-score input validation | `quirk/qramm/scoring.py` | — | Pure stdlib function; D-09 isolation invariant requires no imports |
| Discovery endpoint-count factor | `quirk/qramm/evidence_bridge.py` | — | Evidence bridge owns CVI suggested-answer derivation; factor applies where `score_1_1` is computed |
| vuln_pct zero-algo sentinel + Indeterminate label | `quirk/qramm/evidence_bridge.py` + `quirk/qramm/scoring.py` | Reports / dashboard | Sentinel emitted by bridge; label decided by `_maturity_label()`; renderers consume label string verbatim |
| Maturity ceiling reachability | `quirk/qramm/scoring.py` | — | One-line threshold or clamp change |
| TZ-safe date comparison | `quirk/qramm/evidence_bridge.py` | — | Module-local fix; both sides are SQLAlchemy server-side `date()` results |
| Idempotent UPDATE + commit-failure handling | `quirk/qramm/evidence_bridge.py` | — | Module-local; routes through `logger.warning` + `db.rollback` |
| attach_context AttributeError visibility | `quirk/assessment/operator_context.py` | — | Single-function fix; current code has BARE `except Exception` (not `AttributeError`) |
| Migration advisor word-boundary + synonyms | `quirk/assessment/migration_advisor.py` | (consumer of D-09) | Pure helper module; mirrors `quirk/util/weak_crypto.py` (Phase 73) frozenset shape |
| `_walk_json_for_alg_strings` value-scan | `quirk/qramm/evidence_bridge.py` | `quirk/assessment/migration_advisor.py` (helper consumer) | Bridge consumes the matcher; matcher lives in advisor |
| coverage_status field + rollup | `quirk/qramm/compliance_map.py` | `quirk/dashboard/api/routes/qramm.py:598-663` (rollup consumer) | Data definition lives in compliance_map; consumer in qramm route reads `SCANNER_COVERAGE` and `QRAMM_COMPLIANCE_WEIGHTS` |
| `is_qramm_model_stale` helper | `quirk/qramm/model_meta.py` | `tests/test_qramm_staleness.py` (extant consumer) + `.github/workflows/python-staleness.yml` (CI) + Phase 75 `quirk doctor` | Centralizes date math currently duplicated in `_check_staleness` (test) and inline elsewhere |
| TODO Phase 50 removal | `quirk/compliance/__init__.py` | `docs/operators-guide.md` (referenced target — exists at §7 line 321; TODO is stale) | Single-line deletion |

## Standard Stack

### Core (no new deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| stdlib `re` | Python 3.11+ | D-08 word-boundary regex | [VERIFIED] Already imported across project (`weak_crypto.py`, `safe_exc.py`) |
| stdlib `math` | Python 3.11+ | D-02 `math.log10` discovery factor | [VERIFIED via `python3 -c "import math; print(math.log10(100)/3.0)"` → 0.667] |
| stdlib `datetime` | Python 3.11+ | D-05 TZ-safe date compare; D-11 staleness math | [VERIFIED] Already used in `compliance/__init__.py:19`, `tests/test_qramm_staleness.py:3` |
| stdlib `logging` | Python 3.11+ | D-06, D-07 warning logs | [VERIFIED] `logger = logging.getLogger(__name__)` already at `evidence_bridge.py:21` |
| `sqlalchemy.exc.SQLAlchemyError` | already in deps | D-06 UPDATE failure handling | [VERIFIED] SQLAlchemy is a top-level dep (used in `evidence_bridge.py:15-16`) |
| `typing.Literal` | Python 3.11+ | D-10 `coverage_status` annotation | [VERIFIED] Python 3.11+ supports `Literal` natively; project pins `>=3.11` (CLAUDE.md) |

### Supporting (pattern precedent — already present)

| Module | Pattern | Use Case |
|--------|---------|----------|
| `quirk/util/weak_crypto.py` (Phase 73) | `_WEAK_CIPHER_TOKENS: Final[frozenset[str]]` + helper function | D-08 `CANONICAL_ALG_SYNONYMS` mirrors this shape (but using `dict[str, frozenset[str]]`) |
| `quirk/util/safe_exc.py` | Module-shape template — docstring + private constant + public helper | D-08 helper module structure |
| `quirk/compliance/__init__.py:19, 263-265` | `datetime.date.fromisoformat` comparison | D-05, D-11 date-parsing precedent |
| `quirk/compliance/__init__.py:23` | `STALENESS_THRESHOLD_DAYS: int = 365` | D-11 mirror in `qramm/model_meta.py` (already there at line 15) |
| Phase 70 `_SAFE_COL_TYPE_RE` + ValueError | Fail-loud validation | D-01 `ValueError` raise pattern |
| Phase 73 `tests/test_score_weights_invariant.py` | Single-assertion CI invariant | D-10 `tests/test_compliance_coverage_status.py` |

### Alternatives Considered

None. CONTEXT.md locks every decision. **No new pip dependencies** — D-14 do-not-touch and phase boundary both explicit. `re`, `math`, `datetime`, `logging`, `sqlalchemy.exc`, `typing.Literal` all stdlib or already-installed.

**Installation:** No new packages.

**Version verification:** [VERIFIED via `python3 -c "import sys; print(sys.version)"`] Python 3.11+ required per CLAUDE.md and `pyproject.toml`. `typing.Literal` available since 3.8; `datetime.date.fromisoformat` since 3.7. All stdlib pieces are stable across the version pin.

## Architecture Patterns

### System Architecture Diagram

```
QWARN-01 (Practice scoring correctness):
   ┌──────────────────────────────────────────────┐
   │ quirk/qramm/scoring.py                       │
   │  compute_practice_score(answers)             │ ← D-01 ValueError on out-of-range
   │  compute_overall_score(dims, multiplier)     │
   │    weighted = min(4.0, dim * multiplier)     │ ← D-04 ceiling fix here OR at line 76
   │  _maturity_label(score) -> str               │ ← D-03 add 'Indeterminate' sibling
   │    if score >= 4.0: "Optimizing"             │ ← D-04 threshold candidate
   └──────────────────────────────────────────────┘
                       ▲
                       │ practice_scores fed by
                       │
   ┌──────────────────────────────────────────────┐
   │ quirk/qramm/evidence_bridge.py               │
   │  populate_cvi_suggestions(session_id, db)    │
   │   total_endpoints = len(endpoints)           │ ← D-02 endpoint_count source
   │   score_1_1 = (current rule)                 │ ← D-02 multiply by discovery_factor
   │   vuln_pct = (vuln/total) * 100.0            │ ← D-03 None when total_algos == 0
   └──────────────────────────────────────────────┘

QWARN-02 (Evidence bridge robustness):
   ┌──────────────────────────────────────────────┐
   │ quirk/qramm/evidence_bridge.py               │
   │  Lines 43-52  ← D-05 date compare           │
   │    max_date_str = db.query(func.date(MAX))   │
   │    .filter(func.date(...) == max_date_str)   │
   │  Lines 114-127  ← D-06 idempotent UPDATE     │
   │    db.query(QRAMMAnswer).filter(...).update(.│
   │     synchronize_session="fetch")             │
   │    db.commit()  ← D-06 SQLAlchemyError wrap │
   └──────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────┐
   │ quirk/assessment/operator_context.py         │
   │  attach_context(cfg, ctx)  ← lines 74-98     │
   │    try: setattr(cfg, "assessment_context",.) │
   │    except Exception: pass     ← D-07 NARROW │
   │    try: setattr(assessment, "context", .)    │
   │    except Exception: pass     ← D-07 NARROW │
   └──────────────────────────────────────────────┘

QWARN-03 (Migration advisor + compliance + meta):
   ┌──────────────────────────────────────────────┐
   │ quirk/assessment/migration_advisor.py        │
   │  recommend_migration_paths(findings)         │
   │    title.lower()                             │
   │    if "legacy tls" in title: …               │ ← D-08 substring (title-level)
   │    if "ssh" in title: …                      │ ← false-positive risk
   │   NEW: CANONICAL_ALG_SYNONYMS                │ ← D-08 new module-level dict
   │   NEW: _matches(canonical, text) helper      │ ← D-08 word-boundary regex
   └──────────────────────────────────────────────┘
                       ▲
                       │ consumed by D-09
   ┌──────────────────────────────────────────────┐
   │ quirk/qramm/evidence_bridge.py:165-204       │
   │  _walk_json_for_alg_strings(obj)             │
   │    if key in _ALG_KEYS: out.append(value)    │ ← D-09 ALSO scan non-_ALG_KEYS strings
   └──────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────┐
   │ quirk/qramm/compliance_map.py                │
   │  SCANNER_COVERAGE: Dict[str, float]          │ ← D-10 target (3 zero-weight dims)
   │    CVI: 1.0, SGRM: 0.0, DPE: 0.0, ITR: 0.0   │
   │  QRAMM_COMPLIANCE_WEIGHTS: Dict[str, Dict]   │ ← NO 0.0 weights — see C-5
   │  NEW: COVERAGE_STATUS or similar             │
   └──────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────┐
   │ quirk/qramm/model_meta.py                    │
   │  STALENESS_THRESHOLD_DAYS = 90               │
   │  QRAMM_MODEL["last_verified"] = "2026-05-05" │
   │  NEW: is_qramm_model_stale(today=None)       │ ← D-11
   └──────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────┐
   │ quirk/compliance/__init__.py:3               │
   │  '… # TODO Phase 50'                         │ ← D-12 delete
   └──────────────────────────────────────────────┘
```

### Recommended Plan Structure

```
.planning/phases/74-qramm-compliance-warnings/
├── 74-CONTEXT.md          # locked
├── 74-RESEARCH.md         # this file
├── 74-01-PLAN.md          # QWARN-01: practice scoring (WR-02, WR-04, WR-05, WR-06)
├── 74-02-PLAN.md          # QWARN-02: evidence bridge + attach_context (WR-01, WR-03, WR-07, WR-08)
└── 74-03-PLAN.md          # QWARN-03: advisor + map + meta + TODO (WR-09..WR-13)
```

Mirrors Phase 73's plan-per-requirement layout (3 plans).

### Pattern 1: D-08 helper module shape (mirrors `quirk/util/weak_crypto.py`)

**Reference:** Phase 73 weak_crypto helper shape.

```python
# quirk/assessment/migration_advisor.py — D-08 addition
from __future__ import annotations
import re
from typing import Final

CANONICAL_ALG_SYNONYMS: Final[dict[str, frozenset[str]]] = {
    "DES":  frozenset({"DES", "DES-EDE", "DES-CBC"}),
    "3DES": frozenset({"3DES", "TripleDES", "DES-EDE3"}),
    "RC4":  frozenset({"RC4", "ARCFOUR"}),
    "MD5":  frozenset({"MD5"}),
    "SHA1": frozenset({"SHA1", "SHA-1"}),
    # ...
}

def _matches(canonical: str, text: str) -> bool:
    variants = CANONICAL_ALG_SYNONYMS.get(canonical, frozenset({canonical}))
    pattern = r"\b(" + "|".join(re.escape(v) for v in variants) + r")\b"
    return bool(re.search(pattern, text, re.IGNORECASE))
```

### Pattern 2: D-11 staleness helper (mirrors `quirk/compliance/__init__.py:255-283`)

```python
# quirk/qramm/model_meta.py — D-11 addition
import datetime

def is_qramm_model_stale(today: datetime.date | None = None) -> bool:
    """Return True if the QRAMM catalog last_verified is older than STALENESS_THRESHOLD_DAYS."""
    reference = today or datetime.date.today()
    last_verified = datetime.date.fromisoformat(QRAMM_MODEL["last_verified"])
    age = (reference - last_verified).days
    return age > STALENESS_THRESHOLD_DAYS
```

Note: uses `QRAMM_MODEL["last_verified"]` (nested) not a top-level `LAST_VERIFIED` constant. CONTEXT D-11's example code says `LAST_VERIFIED` but no such constant exists; planner uses the nested key. See C-6.

### Pattern 3: D-01 fail-loud validation (Phase 70 precedent)

```python
def compute_practice_score(answers: List[int], practice_id: str = "") -> float:
    for answer in answers:
        if answer not in (0, 1, 2, 3, 4):
            raise ValueError(
                f"Practice score answer {answer!r} for {practice_id} out of range [0, 4]"
            )
    if not answers:
        return 0.0
    return round(sum(answers) / len(answers), 4)
```

CONTEXT D-01 references `practice_id` in the error message — current signature `compute_practice_score(answers: List[int])` has no `practice_id` parameter. Planner needs to add it (and update callers — none located in the codebase under non-test paths; the function is exported but not currently called by `evidence_bridge.py` which builds its own `score_1_1/1_2/1_3` directly).

### Pattern 4: D-06 idempotent UPDATE

```python
# quirk/qramm/evidence_bridge.py — D-06 retrofit (psuedo-code per CONTEXT)
from sqlalchemy.exc import SQLAlchemyError

for practice_area, suggested_value in practice_scores.items():
    existing = (
        db.query(QRAMMAnswer)
        .filter(
            QRAMMAnswer.session_id == session_id,
            QRAMMAnswer.dimension == "CVI",
            QRAMMAnswer.practice_area == practice_area,
        )
        .all()
    )
    if all(
        r.suggested_answer == suggested_value
        and r.evidence_source == evidence_source
        for r in existing
    ):
        continue   # idempotent skip
    db.query(QRAMMAnswer).filter(...).update({...}, synchronize_session="fetch")
try:
    db.commit()
except SQLAlchemyError as e:
    logger.warning("evidence_bridge UPDATE failed: %s", e)
    db.rollback()
    return
```

### Anti-Patterns to Avoid

- **Silent answer clamp** in `compute_practice_score` (D-01 forbids — fail-loud)
- **String date equality** across TZ boundaries (D-05)
- **Bare `except Exception: pass`** in `attach_context` (D-07 — current code uses bare; CONTEXT says `AttributeError` — see C-7; either way, fix is to log not swallow)
- **Substring-only matching** of algorithm tokens (D-08 — `'DES' in 'DESede'` false-positive)
- **Direct subscript** `QRAMM_MODEL["last_verified"]` outside helper — duplicated math (D-11 centralizes)
- **Weight=0.0 ambiguity** between "intentionally excluded" and "not yet covered" (D-10)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Algorithm-name word-boundary match | Inline `if "DES" in text:` per site | `migration_advisor::_matches` (NEW) + `CANONICAL_ALG_SYNONYMS` | One source of truth; eliminates `'DES' in 'DESede'` class of bugs |
| QRAMM model staleness math | Per-test inline `(today - parse(last_verified)).days` | `is_qramm_model_stale(today=None)` (NEW per D-11) | `tests/test_qramm_staleness.py::_check_staleness` already duplicates this — collapse |
| Coverage-status invariant | Manual code-review checklist | `tests/test_compliance_coverage_status.py` (NEW per D-10) | CI gate; new contributors learn through test failure |
| Date-string equality | `iso_a == iso_b` | `datetime.date.fromisoformat(a) == datetime.date.fromisoformat(b)` | TZ-safe; raises on malformed input |

## Runtime State Inventory

Phase 74 is a code-hardening + schema-extension phase. The compliance_map `coverage_status` field is a NEW field on a pure-data module — no DB migration; no on-disk format change.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 74 touches no DB schema. `QRAMMAnswer.suggested_answer` writes are unchanged in shape (only idempotency check added). | None |
| Live service config | None — no n8n / Datadog / scheduled-task references. | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | None — no pip package renamed; no new module. `__pycache__` regenerates. | None |

**Schema change risk:** D-10 adds `coverage_status` to `compliance_map.py`. Consumer `quirk/dashboard/api/routes/qramm.py:598-663` reads `QRAMM_COMPLIANCE_WEIGHTS[practice_area][framework]` and `SCANNER_COVERAGE[dimension]`. If `coverage_status` is added as a new top-level dict (e.g., `COVERAGE_STATUS: dict[str, str]`), the consumer must be updated to read it. If added as a wrapper around each weight value (changing `Dict[str, float]` to `Dict[str, dict]`), every existing reader breaks. **Recommendation:** new top-level dict — see C-5.

## Common Pitfalls

### Pitfall 1: D-02 `endpoint_count` source — CONTEXT says `evidence_summary.endpoint_count`, but there is no such field in `evidence_bridge.py`

**CONTEXT D-02 says:** "`endpoint_count` is sourced from `evidence_summary.endpoint_count` (researcher confirms exact key name)."
**Current code:** `evidence_bridge.py:59` has local `total_endpoints = len(endpoints)`. There is no `evidence_summary` object in scope — `build_evidence_summary` lives in `quirk/intelligence/evidence.py:52` and is NOT imported by `evidence_bridge.py` (and would VIOLATE D-09 isolation if it were — `evidence.py` imports scanner modules). [VERIFIED via grep]
**REVIEW.md WR-04 cites:** `evidence_bridge.py:78-87` — the practice 1.1 block.
**Planner action:** Use the local `total_endpoints` already in scope. Multiply `score_1_1` by `discovery_factor = min(1.0, max(0.25, math.log10(max(total_endpoints, 1)) / 3.0))`. CONTEXT's "researcher confirms" clause invited this confirmation. See C-1.

### Pitfall 2: D-04 ceiling fix — two implementation paths

**Current code:**
- `scoring.py:56`: `weighted = {d: round(min(4.0, dim_score * mult), 4) for d in dims}` — every weighted dim is capped AT 4.0
- `scoring.py:57`: `overall = round(sum(weighted.values()) / len(dims), 4)` — average of weighted dims
- `scoring.py:76`: `if score >= 4.0: return "Optimizing"`

[VERIFIED via `python3 -c "from quirk.qramm.scoring import compute_overall_score; print(compute_overall_score({'CVI':4.0,'SGRM':4.0,'DPE':4.0,'ITR':4.0}, 1.0))"`] → `overall: 4.0`, `maturity: 'Optimizing'`.

The ceiling **IS reachable** at exact `multiplier=1.0` with all-4.0 inputs. WR-06's "floating-point noise" concern manifests only when multiplier × score has rounding. Example: `multiplier=0.99999 * 4.0 = 3.99996 → round to 4 places → 4.0` (still reachable). But `multiplier=1.0 * 3.9999 = 3.9999 → round → 3.9999 → not >=4.0`.

**Planner adjudication:** Two minimal-change paths:
- (a) Lower threshold: `if score >= 3.95: return "Optimizing"` — easiest, locks 0.05-band tolerance
- (b) Round before band check: `if round(score, 1) >= 4.0: return "Optimizing"` — preserves 4.0 band semantics
CONTEXT D-04 explicitly says "researcher picks the minimal change". See C-2. Recommend (a) for symmetry with parametrized test asserting 3.99 and 4.0 both land in top band.

### Pitfall 3: D-05 date-comparison sites — `evidence_bridge.py` uses SQLAlchemy `func.date()` on BOTH sides

**Current code at `evidence_bridge.py:43, 50`:**
```python
max_date_str = db.query(func.date(func.max(CryptoEndpoint.scanned_at))).scalar()
# ...
.filter(func.date(CryptoEndpoint.scanned_at) == max_date_str)
```

Both sides are SQLAlchemy-server-side date strings (SQLite `date()` function output) — they share the SQLite engine's TZ semantics. The TZ-drift concern in WR-01 manifests if `scanned_at` is stored as a TZ-aware UTC `datetime` but `func.date()` evaluates in SQLite's local TZ. [VERIFIED `CryptoEndpoint.scanned_at` is `Column(DateTime)` — TZ behavior depends on writer; some scanners may write naive local time].

**Planner action per D-05:** This is a "compare both sides as `datetime.date` objects" requirement. Since SQLite's `func.date()` returns a string, the fix has two flavors:
- (a) Parse `max_date_str` via `datetime.date.fromisoformat(...)` BEFORE the filter, then compare server-side date column via a Python-level reconciliation (requires reading all rows — not viable for large scans)
- (b) Keep server-side filter unchanged (it's already symmetric) but add comment + test ensuring both sides go through `func.date()` consistently

D-05 wording fits (a) better for Python-side date comparisons, but the bridge's actual SQL filter is already symmetric. **Recommended adjudication:** the planner / `/gsd-discuss-phase` clarifies whether D-05 is targeting the SQL filter (already TZ-symmetric) or a downstream Python `==` comparison. See C-3.

### Pitfall 4: D-07 — current code does NOT use `except AttributeError`; it uses bare `except Exception`

**CONTEXT D-07 says:** "Replace `except AttributeError:` with `except AttributeError as e: logger.warning(…)`."
**Current code at `operator_context.py:80-95`:**
```python
try:
    setattr(cfg, "assessment_context", ctx_dict)
    return
except Exception:        # ← BARE, not AttributeError
    pass

try:
    assessment = getattr(cfg, "assessment", None)
    if assessment is not None:
        setattr(assessment, "context", ctx_dict)
        return
except Exception:        # ← BARE, not AttributeError
    pass
```

[VERIFIED] There is no `except AttributeError:` clause in the file. The bare `except Exception` swallows AttributeError AND every other exception type silently.

**Planner action:** D-07's intent — surface the silently-dropped context — applies. Narrow BOTH bare excepts to `except AttributeError as e:` and log. If the planner believes a broader catch is needed (e.g., dataclass-frozen `setattr` raises `dataclasses.FrozenInstanceError`), expand the tuple. See C-7.

### Pitfall 5: D-08 — current `migration_advisor.py` matches finding TITLES, not algorithm strings

**CONTEXT D-08 says:** "substring matching replaced with word-boundary regex" — implies the advisor matches algorithm strings like `"DES"` and gets false positives on `"DESede"`.
**Current code at `migration_advisor.py:14-76`:** Matches FINDING TITLES — `if "legacy tls" in title`, `if "ssh" in title`, etc. The matched strings are entire English phrases, NOT algorithm tokens. The "`'DES' in 'DESede'`" pattern is the canonical false-positive that D-08 quotes — but it does not exist in this file at HEAD.

**REVIEW.md WR-09 says:** "no severity weighting; substring matching produces false positives". The false-positive concern is real (e.g., a finding titled "SSH host SSHFP record" would falsely match the SSH branch).

**Planner adjudication:** Two paths:
- (a) **Apply D-08 verbatim** as a forward-looking addition: introduce `CANONICAL_ALG_SYNONYMS` + `_matches` even though no current call site matches algorithms. The map becomes available for D-09's `_walk_json_for_alg_strings` consumption. WR-09's title-matching false positives are addressed via word-boundary regex on the existing title checks.
- (b) **Reinterpret D-08** as title-level word-boundary fix: `if re.search(r"\blegacy tls\b", title)` etc., without introducing `CANONICAL_ALG_SYNONYMS`.

Both close WR-09. (a) is broader and lets D-09 reuse the helper — RECOMMENDED. See C-4.

### Pitfall 6: D-09 — `_walk_json_for_alg_strings` has 5 specific code paths

**Current code at `evidence_bridge.py:165-204`:**
- Lines 188-196: dict iteration — only appends value if `key in _ALG_KEYS`; recurses if value is dict/list
- Lines 197-204: list iteration — recurses if item is dict/list; appends if item is non-empty string

[VERIFIED via reading] Bare-string list items (line 203) ARE appended even when not under an `_ALG_KEYS` key (e.g., `"encryption_types": ["rc4-hmac", ...]` works). The actual gap is: **dict values that are strings but key is NOT in `_ALG_KEYS`** are silently skipped (line 195: "Non-ALG-key string values are intentionally not appended here").

**Planner action per D-09:** Modify the dict iteration branch — after the keyed check, if value is a string but key is NOT in `_ALG_KEYS`, scan via `_matches(canonical, value)` against the `CANONICAL_ALG_SYNONYMS` keys; if any match, append the value. This preserves the existing bare-string list behavior and only adds the missing dict-string-non-keyed scan.

### Pitfall 7: D-10 — `compliance_map.py` has NO entries with `weight=0.0` in `QRAMM_COMPLIANCE_WEIGHTS`

[VERIFIED via `python3 -c "from quirk.qramm.compliance_map import QRAMM_COMPLIANCE_WEIGHTS; print(min(min(d.values()) for d in QRAMM_COMPLIANCE_WEIGHTS.values()))"`] — minimum weight is **0.4** (line 78 onwards). Every entry is non-zero.

The weight=0.0 entries live in `SCANNER_COVERAGE` (lines 35-40): `CVI=1.0, SGRM=0.0, DPE=0.0, ITR=0.0` — these are dimension-level ceilings, not per-framework weights.

**CONTEXT D-10 says:** "Migration: every existing entry gets `'covered'` by default; entries with `weight=0.0` flip to `'pending'`."

**Planner adjudication:** The "weight=0.0 → pending" migration applies to `SCANNER_COVERAGE`, not `QRAMM_COMPLIANCE_WEIGHTS`. The semantic mapping is:
- CVI (1.0) → `'covered'`
- SGRM, DPE, ITR (0.0) → `'pending'` (the evidence bridge will lift these as new scanners land — comment at lines 32-34 confirms)

Implementation shapes:
- (a) **New parallel dict** `SCANNER_COVERAGE_STATUS: dict[str, Literal['covered','partial','pending','n/a']]` — minimal diff
- (b) **Replace `SCANNER_COVERAGE` with `dict[str, tuple[float, str]]`** — breaks 1 consumer (`qramm.py:623`)
Recommend (a). See C-5. The HTML/PDF table column and `ComplianceMapTab` rendering still need to read this new dict; consumer in `quirk/dashboard/api/routes/qramm.py:621-661` needs to include status in `ComplianceMapRow`.

### Pitfall 8: D-12 — TODO Phase 50 located, target doc EXISTS

[VERIFIED via grep] Single match in `quirk/qramm/`, `quirk/compliance/`, `quirk/assessment/`:

```
quirk/compliance/__init__.py:3:Maintenance cadence: see docs/operators-guide.md §"Compliance Map Maintenance".  # TODO Phase 50
```

Context (3 lines):
```python
1  """Phase 49 D-01: Compliance mapping for QUIRK findings (PCI-DSS 4.0.1, HIPAA 45 CFR, FIPS 140-3).
2
3  Maintenance cadence: see docs/operators-guide.md §"Compliance Map Maintenance".  # TODO Phase 50
4
5  Compliance refs are EAGERLY attached to every finding dict by
```

**Target doc verified:** `docs/operators-guide.md:321` contains `## 7. Compliance Map Maintenance`. The maintenance cadence documentation EXISTS. The TODO is stale — Phase 50 was supposed to add this section, and it has been added. **No deferred-items.md note needed** per D-12's escape clause.

**Planner action:** Delete `# TODO Phase 50` suffix; keep the rest of the line. One-character-cluster edit.

### Pitfall 9: D-11 — `LAST_VERIFIED` is not a module-level constant; date is in `QRAMM_MODEL["last_verified"]`

**CONTEXT D-11 sample code uses:** `datetime.date.fromisoformat(LAST_VERIFIED)`.
**Current code:** No `LAST_VERIFIED` constant. The date is at `QRAMM_MODEL["last_verified"]` (nested dict access). [VERIFIED]

**Planner action:** Helper uses `QRAMM_MODEL["last_verified"]` directly. Optionally extract `LAST_VERIFIED: str = QRAMM_MODEL["last_verified"]` at module level for the symmetry CONTEXT implies — minor stylistic choice. See C-6.

## Code Examples

Verified patterns from current code:

### QWARN-01 / D-01: `compute_practice_score` — current state

```python
# quirk/qramm/scoring.py:20-28
def compute_practice_score(answers: List[int]) -> float:
    """Average of question answers within a single practice area.

    CSNP toolkit uses 4-point scale (1-4). Empty list returns 0.0.
    Result rounded to 4 decimal places to avoid float representation noise.
    """
    if not answers:
        return 0.0
    return round(sum(answers) / len(answers), 4)
```

**Fix (D-01):** Add fail-loud validation before summation. Note that the docstring says "1-4" but CONTEXT says `{0, 1, 2, 3, 4}` — five-value range, including 0. Match CONTEXT.

### QWARN-01 / D-02: Practice 1.1 endpoint factor — current state

```python
# quirk/qramm/evidence_bridge.py:78-87
# D-06 — Practice 1.1 (Discovery & Inventory): endpoint count + protocol diversity
distinct_protocols = len(protocol_set)
if total_endpoints == 0:
    score_1_1 = 1
elif distinct_protocols <= 1:
    score_1_1 = 2
elif distinct_protocols <= 3:
    score_1_1 = 3
else:
    score_1_1 = 4
```

**Fix (D-02):** Multiply by `discovery_factor`:
```python
import math
discovery_factor = min(1.0, max(0.25, math.log10(max(total_endpoints, 1)) / 3.0))
score_1_1 = round(score_1_1 * discovery_factor, 4)
```

### QWARN-01 / D-03: vuln_pct sentinel — current state

```python
# quirk/qramm/evidence_bridge.py:89-98
# D-05 — Practice 1.2 (Vulnerability Assessment): % endpoints with nist_level == 0
vuln_pct = (vulnerable_endpoint_count / total_endpoints) * 100.0
if vuln_pct <= 25.0:
    score_1_2 = 4
elif vuln_pct <= 50.0:
    score_1_2 = 3
elif vuln_pct <= 75.0:
    score_1_2 = 2
else:
    score_1_2 = 1
```

**Fix (D-03):** Need a new state. `vuln_pct = None` when `total_algos == 0` (i.e., when `algorithm_set` is empty after classification loop). Propagate sentinel up to scoring; `_maturity_label` returns `"Indeterminate"` for `None` input.

### QWARN-01 / D-04: Maturity bands — current state

```python
# quirk/qramm/scoring.py:66-84
def _maturity_label(score: float) -> str:
    if score >= 4.0:
        return "Optimizing"
    if score >= 3.5:
        return "Advanced"
    # ...
```

**Fix (D-04):** Adjust either ceiling at line 56 (`min(4.0, ...)`) or band threshold at line 76. **Add `Indeterminate` arm** per D-03:
```python
def _maturity_label(score: float | None) -> str:
    if score is None:
        return "Indeterminate"
    if score >= 3.95:        # D-04 candidate
        return "Optimizing"
    # ...
```

### QWARN-02 / D-06: Idempotent UPDATE — current state

```python
# quirk/qramm/evidence_bridge.py:114-127
for practice_area, suggested_value in practice_scores.items():
    db.query(QRAMMAnswer).filter(
        QRAMMAnswer.session_id == session_id,
        QRAMMAnswer.dimension == "CVI",
        QRAMMAnswer.practice_area == practice_area,
    ).update(
        {
            QRAMMAnswer.suggested_answer: suggested_value,
            QRAMMAnswer.evidence_source: evidence_source,
        },
        synchronize_session="fetch",
    )

db.commit()
```

**Fix (D-06):** Pre-query + skip + try/except SQLAlchemyError around `db.commit()`. See Pattern 4 above.

### QWARN-02 / D-07: `attach_context` — current state

```python
# quirk/assessment/operator_context.py:74-98
def attach_context(cfg, ctx: OperatorContext) -> None:
    ctx_dict = ctx.to_dict()
    try:
        setattr(cfg, "assessment_context", ctx_dict)
        return
    except Exception:        # ← D-07 narrow + log
        pass
    try:
        assessment = getattr(cfg, "assessment", None)
        if assessment is not None:
            setattr(assessment, "context", ctx_dict)
            return
    except Exception:        # ← D-07 narrow + log
        pass
    return
```

**Fix (D-07):**
```python
import logging
logger = logging.getLogger(__name__)

# both excepts:
except AttributeError as e:
    logger.warning("attach_context skipped — source object missing attribute: %s", e)
```

### QWARN-03 / D-08: Migration advisor — current state

```python
# quirk/assessment/migration_advisor.py:14-76
for f in findings:
    title = (f.get("title") or "").lower()
    # ...
    if "legacy tls" in title:          # ← D-08 word-boundary regex needed
        recs.append({...})
        continue
    if "plaintext http" in title:      # ← same
        # ...
    if "ssh" in title:                 # ← false-positive risk ('ssh' in 'sshfp')
        # ...
```

**Fix (D-08):** Add `CANONICAL_ALG_SYNONYMS` + `_matches` (Pattern 1). Replace title-level substring checks with `_matches`-style word-boundary regex. The advisor stays title-driven, but the matching becomes word-boundary safe AND the synonyms map is available for D-09 reuse.

### QWARN-03 / D-09: `_walk_json_for_alg_strings` — current state

```python
# quirk/qramm/evidence_bridge.py:188-204
if isinstance(obj, dict):
    for key, value in obj.items():
        if key in _ALG_KEYS and isinstance(value, str) and value:
            out.append(value)
        elif isinstance(value, (dict, list)):
            out.extend(_walk_json_for_alg_strings(value))
        # ← D-09 GAP: string values where key NOT in _ALG_KEYS are dropped
elif isinstance(obj, list):
    for item in obj:
        if isinstance(item, (dict, list)):
            out.extend(_walk_json_for_alg_strings(item))
        elif isinstance(item, str) and item:
            out.append(item)
```

**Fix (D-09):** Add a third dict-branch arm:
```python
elif isinstance(value, str) and value:
    # D-09: scan for canonical algorithm tokens
    if any(_matches(canon, value) for canon in CANONICAL_ALG_SYNONYMS):
        out.append(value)
```

### QWARN-03 / D-10: `SCANNER_COVERAGE` + `QRAMM_COMPLIANCE_WEIGHTS` — current state

```python
# quirk/qramm/compliance_map.py:35-40
SCANNER_COVERAGE: Dict[str, float] = {
    "CVI": 1.0,
    "SGRM": 0.0,
    "DPE": 0.0,
    "ITR": 0.0,
}
```

**Fix (D-10):** New parallel dict (recommended — minimal diff to existing consumers):
```python
from typing import Literal

CoverageStatus = Literal['covered', 'partial', 'pending', 'n/a']

SCANNER_COVERAGE_STATUS: Dict[str, CoverageStatus] = {
    "CVI":  "covered",
    "SGRM": "pending",
    "DPE":  "pending",
    "ITR":  "pending",
}
```

Consumer at `quirk/dashboard/api/routes/qramm.py:621-661` reads `SCANNER_COVERAGE[dimension]` for the ceiling; add a parallel read of `SCANNER_COVERAGE_STATUS[dimension]` and surface as `ComplianceMapRow.coverage_status`.

**CI gate test (D-10):**
```python
# tests/test_compliance_coverage_status.py
def test_every_dimension_has_valid_coverage_status() -> None:
    from quirk.qramm.compliance_map import SCANNER_COVERAGE, SCANNER_COVERAGE_STATUS
    valid = {'covered', 'partial', 'pending', 'n/a'}
    assert set(SCANNER_COVERAGE_STATUS.keys()) == set(SCANNER_COVERAGE.keys())
    for k, v in SCANNER_COVERAGE_STATUS.items():
        assert v in valid, f"{k} has invalid coverage_status: {v!r}"
```

### QWARN-03 / D-11: `is_qramm_model_stale` helper — current state

```python
# quirk/qramm/model_meta.py
STALENESS_THRESHOLD_DAYS: int = 90
QRAMM_MODEL = {
    "qramm_version": "1.0",
    "last_verified": "2026-05-05",
    "source_url": "https://qramm.org",
    # ...
}
```

**Fix (D-11):** See Pattern 2. Extant duplicated math at `tests/test_qramm_staleness.py:34-39` (`_check_staleness`) can be collapsed to use the new helper (optional refactor).

### QWARN-03 / D-12: TODO Phase 50 — current state

```python
# quirk/compliance/__init__.py:3
Maintenance cadence: see docs/operators-guide.md §"Compliance Map Maintenance".  # TODO Phase 50
```

**Fix (D-12):** Delete trailing ` # TODO Phase 50`. The target doc exists (`docs/operators-guide.md:321 ## 7. Compliance Map Maintenance`). No deferred-items.md note required.

## Test File Pattern

Existing relevant test modules at HEAD:

| Test file | Covers | Phase 74 use |
|-----------|--------|--------------|
| `tests/test_qramm_staleness.py` | QRAMM-05/06/07 staleness math | Extend with `test_is_qramm_model_stale_fresh / _stale` (D-11) |
| `tests/test_compliance_freshness.py` | Phase 49/50/56 invariant | **DO NOT MODIFY** (D-14) — D-10 adds NEW test module |
| `tests/test_qramm_evidence_bridge.py` (search) | Existing bridge tests if present | Extend / new module for D-05, D-06, D-07 |
| `tests/test_qramm_scoring.py` (search) | Existing scoring tests if present | Extend / new module for D-01, D-04 |

**Confirm by `ls tests/`:**

[VERIFIED via existing repo files referenced]:
- `tests/test_qramm_staleness.py` exists (referenced by `python-staleness.yml`)
- `tests/test_compliance_freshness.py` exists (referenced by `python-staleness.yml`)

**New test modules required by CONTEXT `<test_strategy>`:**
- `tests/test_qramm_practice_scoring.py` — D-01 (ValueError on out-of-range), D-02 (endpoint factor curve), D-03 (Indeterminate sentinel), D-04 (3.99 / 4.0 both top band)
- `tests/test_evidence_bridge_correctness.py` — D-05 (TZ-safe date), D-06 (idempotent UPDATE + commit failure log), D-07 (AttributeError logged not swallowed)
- `tests/test_migration_advisor_precision.py` — D-08 (parametrized: `'DESede'`, `'AES-128'`, `'libdes3.so'`, `'TripleDES_v2'`)
- `tests/test_compliance_coverage_status.py` — D-10 invariant (every dim has valid status)
- `tests/test_qramm_model_stale.py` — D-11 (inject `today=date(2026,12,31)` stale; `today=date(2026,5,15)` fresh)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Silent answer summation | Fail-loud `ValueError` on out-of-range | Phase 74 (D-01) | Defense-in-depth; consistent with Phase 70 fail-loud pattern |
| Protocol-diversity-only Discovery score | Endpoint-count × diversity factor | Phase 74 (D-02) | Zero-endpoint scans cannot claim discovery maturity |
| `vuln_pct = 0` (no algos) → top band | `vuln_pct = None` → `'Indeterminate'` label | Phase 74 (D-03) | Excludes empty scans from cohort stats |
| String-equality date compare | `datetime.date.fromisoformat` parsing | Phase 74 (D-05) | TZ-safe; raises on malformed input |
| Per-call SQL UPDATE | Pre-query idempotency check | Phase 74 (D-06) | Skip no-op UPDATEs; commit failure logged not silenced |
| Substring title match | Word-boundary regex via `_matches` | Phase 74 (D-08) | Eliminates `'DES' in 'DESede'` family of false positives |
| Skip non-`_ALG_KEYS` string values | Scan via canonical-algorithm matcher | Phase 74 (D-09) | Schema-drift-resilient evidence extraction |
| Weight=0.0 ambiguous | Explicit `coverage_status` field | Phase 74 (D-10) | "Not yet covered" vs "intentionally excluded" distinguished |
| Duplicated staleness date math | `is_qramm_model_stale()` helper | Phase 74 (D-11) | Single source of truth; Phase 75 `quirk doctor` consumes |

**Deprecated/outdated:**
- `# TODO Phase 50` comment — target doc now exists.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | D-02 `endpoint_count` source = local `total_endpoints` (not `evidence_summary.endpoint_count`) | Pitfall 1, C-1 | None — CONTEXT explicitly invited researcher confirmation |
| A2 | D-04 path (a) `>= 3.95` is minimal-diff vs path (b) `round(score, 1)` | Pitfall 2, C-2 | None — both close WR-06; planner picks |
| A3 | D-05 SQL filter is already TZ-symmetric; D-05 actually targets Python-side date `==` (if any) | Pitfall 3, C-3 | If incorrect, may need broader audit of date-compare sites |
| A4 | D-08 path (a) — introduce `CANONICAL_ALG_SYNONYMS` for D-09 reuse — recommended over (b) | Pitfall 5, C-4 | None — (b) also closes WR-09 but loses D-09 reuse |
| A5 | D-10 `SCANNER_COVERAGE_STATUS` as parallel dict (not embedded in `SCANNER_COVERAGE`) | Pitfall 7, C-5 | Consumer at `qramm.py:621-661` change still needed either way |
| A6 | D-11 helper uses `QRAMM_MODEL["last_verified"]` directly (no `LAST_VERIFIED` module constant) | Pitfall 9, C-6 | None — minor stylistic |
| A7 | D-07 narrows BOTH bare `except Exception` clauses (CONTEXT says one `except AttributeError`) | Pitfall 4, C-7 | If reviewer prefers keep one, modify in code-review |
| A8 | D-08 advisor stays title-driven (current shape); WR-09 closed via word-boundary regex on titles + new synonyms map available for D-09 | C-8 | None — closes the audit-cited bug |
| A9 | D-12 TODO Phase 50 — no deferred-items.md note needed (target doc exists at `docs/operators-guide.md:321`) | Pitfall 8 | None — verified |

## Open Questions

1. **D-05 scope** — Does CONTEXT D-05 intend the SQL filter (already symmetric) or a downstream Python `==` site? See C-3. **Recommendation:** Surface to user via discuss-phase confirmation; default to: (a) keep SQL filter unchanged, (b) add inline comment + regression test asserting TZ-symmetry, (c) any Python-side date `==` in this module gets `datetime.date.fromisoformat` parsing.

2. **D-08 advisor scope** — Should `recommend_migration_paths` ALSO consume `_matches` against finding `cipher_suite` / `cert_pubkey_alg` fields (currently it only reads `title`)? CONTEXT does not require it. **Recommendation:** Defer (add helper + word-boundary on titles; cipher-aware logic stays Phase 75+).

3. **D-10 partial-weight rollup semantics (D-10a discretion)** — half-weight default. CI gate test asserts invariant only; rollup math is in `qramm.py:621-661`. Confirm whether qramm.py consumer should multiply ceiling by 0.5 for `'partial'` or exclude entirely. **Recommendation:** half-weight per D-10a default.

4. **D-11 LAST_VERIFIED extraction** — Should we extract `LAST_VERIFIED: str = QRAMM_MODEL["last_verified"]` at module level (matching CONTEXT's literal code sample), or keep nested access? Both work. **Recommendation:** Nested — minimal diff. Optionally add the module-level constant if `quirk doctor` ergonomics improve.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python stdlib `re`, `math`, `datetime`, `logging`, `typing.Literal` | D-01..D-11 | ✓ | 3.11+ | — |
| `sqlalchemy.exc.SQLAlchemyError` | D-06 commit failure handling | ✓ | already in deps | — |
| `pytest` | Test execution | ✓ | already in dev deps | — |
| `python -m compileall` | CLAUDE.md mandatory check | ✓ | Python 3.11+ | — |
| `git` | docs commit + D-12 `git blame` verification | ✓ | — | — |

No new external dependencies. All required modules are stdlib or already-installed.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | (project root) — pytest defaults |
| Quick run command | `pytest tests/test_qramm_practice_scoring.py tests/test_evidence_bridge_correctness.py tests/test_migration_advisor_precision.py tests/test_compliance_coverage_status.py tests/test_qramm_model_stale.py -x` |
| Full suite command | `pytest -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QWARN-01 / WR-02 | `compute_practice_score` raises ValueError on out-of-range answer | unit | `pytest tests/test_qramm_practice_scoring.py::test_out_of_range_raises -x` | ❌ Wave 0 |
| QWARN-01 / WR-04 | Practice 1.1 endpoint factor: 1 endpoint → 0.25, 1000 → 1.0 | unit | `pytest tests/test_qramm_practice_scoring.py::test_discovery_factor_curve -x` | ❌ Wave 0 |
| QWARN-01 / WR-05 | vuln_pct sentinel: zero algos → 'Indeterminate' label | unit | `pytest tests/test_qramm_practice_scoring.py::test_indeterminate_sentinel -x` | ❌ Wave 0 |
| QWARN-01 / WR-06 | Both 3.99 and 4.0 land in Optimizing band | unit (parametrized) | `pytest tests/test_qramm_practice_scoring.py::test_top_band_reachable -x` | ❌ Wave 0 |
| QWARN-02 / WR-01 | Date compare TZ-safe (parametrized over UTC midnight) | unit | `pytest tests/test_evidence_bridge_correctness.py::test_tz_safe_date -x` | ❌ Wave 0 |
| QWARN-02 / WR-03 | Idempotent UPDATE — repeat call does not re-write same value | unit | `pytest tests/test_evidence_bridge_correctness.py::test_idempotent_update -x` | ❌ Wave 0 |
| QWARN-02 / WR-07 | `db.commit()` failure logged + rollback | unit | `pytest tests/test_evidence_bridge_correctness.py::test_commit_failure_logged -x` | ❌ Wave 0 |
| QWARN-02 / WR-08 | `attach_context` AttributeError logged not swallowed | unit | `pytest tests/test_evidence_bridge_correctness.py::test_attach_context_logged -x` | ❌ Wave 0 |
| QWARN-03 / WR-09 | `_matches('DES', 'DESede')` is False; `_matches('DES', 'DES-CBC')` True | unit (parametrized) | `pytest tests/test_migration_advisor_precision.py::test_word_boundary_synonyms -x` | ❌ Wave 0 |
| QWARN-03 / WR-10 | `_walk_json_for_alg_strings({"foo": "RC4-MD5"})` extracts "RC4-MD5" | unit | `pytest tests/test_migration_advisor_precision.py::test_non_alg_key_scan -x` | ❌ Wave 0 |
| QWARN-03 / WR-11 | Every dim has valid coverage_status; `'pending'` excluded from rollup | unit | `pytest tests/test_compliance_coverage_status.py -x` | ❌ Wave 0 |
| QWARN-03 / WR-12 | `is_qramm_model_stale(today=date(2026,12,31))` True; `today=date(2026,5,15)` False | unit | `pytest tests/test_qramm_model_stale.py -x` | ❌ Wave 0 |
| QWARN-03 / WR-13 | grep `TODO Phase 50` → no match | invariant | grep gate in CI | manual / one-off |

### Sampling Rate

- **Per task commit:** Module-scoped pytest (one file)
- **Per wave merge:** All QWARN-NN test modules + `tests/test_qramm_staleness.py` (D-11 collapse regression)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_qramm_practice_scoring.py` — new module (D-01, D-02, D-03, D-04)
- [ ] `tests/test_evidence_bridge_correctness.py` — new module (D-05, D-06, D-07)
- [ ] `tests/test_migration_advisor_precision.py` — new module (D-08, D-09)
- [ ] `tests/test_compliance_coverage_status.py` — new module (D-10)
- [ ] `tests/test_qramm_model_stale.py` — new module (D-11)

*Framework already installed; no install command needed.*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes (D-01 fail-loud; D-10 coverage_status Literal type) | Inline `ValueError`; `typing.Literal` |
| V7 Error Handling & Logging | yes (D-06 commit-failure log; D-07 AttributeError log) | `logger.warning(...)` + `db.rollback()` |
| V8 Data Protection | yes (D-05 TZ-safe date — staleness math) | `datetime.date.fromisoformat` |

### Known Threat Patterns for qramm/compliance stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Out-of-range score amplification | Tampering (score integrity) | Fail-loud ValueError (D-01) |
| Stored-state silent corruption from non-idempotent UPDATE | Tampering | Pre-query idempotency check (D-06) |
| Silent context drop | Information Disclosure / Repudiation | Log AttributeError (D-07) |
| Algorithm-token false positive in advisor | Tampering (recommendation integrity) | Word-boundary regex (D-08) |
| Schema drift dropping evidence | Information Disclosure (missing data) | Value-scan extension (D-09) |
| Stale catalog → silent compliance drift | Repudiation (unknown freshness) | `is_qramm_model_stale` + CI gate (D-11) |
| Lexicographic date compare poisoning | Tampering (staleness signal) | `datetime.date.fromisoformat` (D-05, also addresses BL-03 carryover) |

## Project Constraints (from CLAUDE.md)

- **PEP 8** for all Python changes — applies to all edits in `quirk/qramm/`, `quirk/assessment/`, `quirk/compliance/`.
- **Minimal diffs** — D-14 do-not-touch list enforces this explicitly.
- After changes, run `python -m compileall` and relevant tests.
- **Staleness Review Cadence APPLIES** — D-11 helper is the centralization point. **No `last_verified` date is bumped in Phase 74** (this is a code phase, not a re-verification phase).
- **Chaos lab maintenance does NOT apply** — no Docker Compose profile changes.
- **Mandatory phase completion:** Create Obsidian Phase 74 note at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-74-QRAMM-Compliance-Warnings.md`; update `docs/UAT-SERIES.md` to document `'Indeterminate'` maturity label + `coverage_status` column; sync to vault; commit UAT-SERIES.md update.

## Sources

### Primary (HIGH confidence)

- `quirk/qramm/scoring.py:20-84` — D-01, D-03, D-04 sites verified (function body, MATURITY thresholds, no MATURITY_LABELS constant)
- `quirk/qramm/evidence_bridge.py:1-204` — D-05, D-06, D-07 (data flow), D-09 sites verified
- `quirk/assessment/operator_context.py:74-98` — D-07 site verified (BARE `except Exception`, not `AttributeError`)
- `quirk/assessment/migration_advisor.py:1-76` — D-08 site verified (title-driven, not algorithm-driven)
- `quirk/qramm/compliance_map.py:1-108` — D-10 site verified (`SCANNER_COVERAGE` is the weight=0.0 home; `QRAMM_COMPLIANCE_WEIGHTS` minimum weight is 0.4)
- `quirk/qramm/model_meta.py:1-23` — D-11 site verified (`STALENESS_THRESHOLD_DAYS=90`, `QRAMM_MODEL["last_verified"]="2026-05-05"`, no `LAST_VERIFIED` constant)
- `quirk/compliance/__init__.py:3` — D-12 site verified (single TODO Phase 50 match)
- `quirk/dashboard/api/routes/qramm.py:33-37, 200-247, 595-663` — bridge consumer + compliance_map rollup consumer verified
- `tests/test_qramm_staleness.py:1-40` — D-11 duplicated math at `_check_staleness` confirmed
- `.github/workflows/python-staleness.yml:1-37` — D-11 CI consumer verified
- `docs/operators-guide.md:321` — D-12 target doc verified (`## 7. Compliance Map Maintenance` exists)
- `.planning/REQUIREMENTS.md:46-50, 128-130` — QWARN-01..QWARN-03 IDs verified
- `.planning/audit-2026-05-08/AUDIT-TASKS.md:124-136` — all 13 open WR rows confirmed
- `.planning/audit-2026-05-08/qramm-compliance/REVIEW.md:62-78` — file:line cites confirmed

### Secondary (MEDIUM confidence)

- `quirk/util/weak_crypto.py` (Phase 73) — `_WEAK_CIPHER_TOKENS` frozenset shape — pattern reference for D-08
- `quirk/util/safe_exc.py:1-53` — module-shape template — D-08 structure reference
- `.planning/phases/73-cbom-intel-reports-warnings/73-RESEARCH.md` — research format precedent
- `quirk/compliance/__init__.py:23-27, 255-283` — `STALENESS_THRESHOLD_DAYS=365` + `status_report` pattern (D-11 reference)

### Tertiary (LOW confidence)

- D-04 implementation path (a vs b) — planner adjudicates
- D-05 scope (SQL filter vs Python-side `==`) — planner / discuss-phase confirms
- D-08 advisor scope (title-only vs cipher-aware) — planner picks
- D-10 implementation shape (parallel dict vs tuple-value) — planner picks

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib + already-installed; no version concerns
- Architecture: HIGH — every file:line in CONTEXT.md verified against HEAD; nine cite mismatches documented
- Pitfalls: HIGH — verified via direct file reads + Python execution (e.g., `min` weight in `QRAMM_COMPLIANCE_WEIGHTS` == 0.4; ceiling reachable at `multiplier=1.0`)
- Test gaps: HIGH — 5 new test modules identified; existing module extension points clear

**Research date:** 2026-05-15
**Valid until:** 2026-06-15 (stable phase; no fast-moving dependencies)

<research_concerns>
## Research Concerns (planner adjudication needed)

These are NOT new decisions. CONTEXT.md remains authoritative. Each concern surfaces a discrepancy between CONTEXT wording and current HEAD, with recommended handling.

### C-1 (D-02): `endpoint_count` source — CONTEXT says `evidence_summary.endpoint_count`, but no such field is in scope

**CONTEXT D-02 says:** "`endpoint_count` is sourced from `evidence_summary.endpoint_count` (researcher confirms exact key name)."
**Current code:** `evidence_bridge.py:59` has local `total_endpoints = len(endpoints)`. `evidence_summary` is built by `quirk/intelligence/evidence.py::build_evidence_summary` which is NOT imported by the bridge (would violate D-09 isolation invariant). [VERIFIED]
**Adjudication:** Use local `total_endpoints`. CONTEXT explicitly invited researcher confirmation. No decision change.

### C-2 (D-04): Ceiling fix — adjust band threshold vs adjust multiplier ceiling

**CONTEXT D-04 says:** "adjust the upper boundary check from `>= 4.0` to `>= 3.95` OR adjust the underlying score multiplier ceiling — researcher picks the minimal change."
**Current code:** The ceiling IS reachable at `multiplier=1.0` with all-4.0 inputs [VERIFIED via `python3 -c`]. The FP-noise concern manifests only with `multiplier < 1.0`. Path (a) `>= 3.95` is one-line at `scoring.py:76`; path (b) round-before-band is two-line at `scoring.py:76-77`.
**Adjudication:** Recommend (a) `>= 3.95`. Parametrized test asserts 3.99 and 4.0 both land in top band.

### C-3 (D-05): TZ-safe date compare — SQL filter is already symmetric

**CONTEXT D-05 says:** "Replace [date string equality] with `datetime.date` object comparison."
**Current code:** `evidence_bridge.py:43-50` uses SQLAlchemy `func.date()` on BOTH sides of the `==` — server-side string comparison; the SQLite engine evaluates both consistently. WR-01 cites "vulnerable to TZ drift" — manifests if `scanned_at` was written by different scanners using different TZ semantics.
**Adjudication:** Three sub-decisions for the planner:
- (a) Keep SQL filter unchanged; add inline comment + regression test asserting TZ-symmetry.
- (b) Add a Python-side reconciliation: parse `max_date_str` once with `datetime.date.fromisoformat`, then enumerate endpoints client-side. Heavier; loses query pushdown.
- (c) Hybrid — keep SQL filter, but parse `max_date_str` to a `datetime.date` for any DOWNSTREAM comparison (e.g., the `evidence_source` string at line 111 currently embeds `max_date_str` raw).
**Recommendation:** (a). Surface to user via discuss-phase if reviewer wants (b) or (c).

### C-4 (D-08): Migration advisor matches TITLES not algorithm strings

**CONTEXT D-08 says:** "substring matching replaced with word-boundary regex" — implies algorithm-token matching.
**Current code:** `migration_advisor.py:14-76` matches FINDING TITLES (`"legacy tls" in title`, `"ssh" in title`). No algorithm-string matching. The `'DES' in 'DESede'` canonical example is forward-looking.
**Adjudication:**
- (a) Apply D-08 verbatim — add `CANONICAL_ALG_SYNONYMS` + `_matches` even though no current call site matches algorithms. The helper becomes available for D-09 reuse. WR-09 closed via word-boundary regex on title checks.
- (b) Reinterpret as title-level fix only.
**Recommendation:** (a). Closes WR-09 AND enables D-09 reuse.

### C-5 (D-10): No entries with `weight=0.0` in `QRAMM_COMPLIANCE_WEIGHTS`

**CONTEXT D-10 says:** "entries with `weight=0.0` flip to `'pending'`."
**Current code:** `QRAMM_COMPLIANCE_WEIGHTS` minimum weight is 0.4 [VERIFIED via Python execution]. `SCANNER_COVERAGE` has the three zero-weight dimensions (SGRM, DPE, ITR). REVIEW.md WR-11 cites `compliance_map.py:35-40` — which is `SCANNER_COVERAGE`, not `QRAMM_COMPLIANCE_WEIGHTS`.
**Adjudication:** Apply `coverage_status` to `SCANNER_COVERAGE` dimensions. Recommended shape: NEW parallel dict `SCANNER_COVERAGE_STATUS: Dict[str, Literal['covered','partial','pending','n/a']]`. Migration: `CVI → 'covered'`; `SGRM, DPE, ITR → 'pending'`. Consumer at `qramm.py:621-661` adds parallel read.

### C-6 (D-11): `LAST_VERIFIED` is not a module-level constant

**CONTEXT D-11 sample code references:** `datetime.date.fromisoformat(LAST_VERIFIED)`.
**Current code:** `model_meta.py` has `STALENESS_THRESHOLD_DAYS` at module level but NO `LAST_VERIFIED` constant. The date is nested at `QRAMM_MODEL["last_verified"]`. [VERIFIED]
**Adjudication:** Helper uses nested access: `datetime.date.fromisoformat(QRAMM_MODEL["last_verified"])`. Optionally extract `LAST_VERIFIED: str = QRAMM_MODEL["last_verified"]` for symmetry — stylistic. No decision change.

### C-7 (D-07): `attach_context` uses BARE `except Exception`, not `except AttributeError`

**CONTEXT D-07 says:** "Replace `except AttributeError:` with `except AttributeError as e: logger.warning(...)`."
**Current code:** TWO `except Exception:` blocks at `operator_context.py:80-86` and `:88-95`. No `except AttributeError` exists. [VERIFIED]
**Adjudication:** Narrow BOTH bare excepts to `except AttributeError as e:` and log. The intent of WR-08 (surface silently dropped context) is satisfied. If the planner believes broader catches needed (e.g., `dataclasses.FrozenInstanceError`), expand the exception tuple. No decision change.

### C-8 (D-08 scope clarification): Does the advisor consume `cipher_suite` / `cert_pubkey_alg` fields?

**Current code:** Only reads `title`, `severity`, `host`, `port`, `recommendation`. Does NOT inspect cipher fields. **Recommendation:** keep advisor title-driven in this phase; cipher-aware migration logic is Phase 75+. The new `CANONICAL_ALG_SYNONYMS` + `_matches` helpers are still useful (D-09 consumes them).

### C-9 (D-12): Target doc EXISTS — no deferred-items.md note needed

**CONTEXT D-12 says:** "If it cites work that did NOT land in Phase 50, capture in a deferred-items.md note before deletion."
**Current state:** `docs/operators-guide.md:321` has `## 7. Compliance Map Maintenance` — the work DID land. [VERIFIED]
**Adjudication:** Delete TODO suffix; no deferred-items.md note required.
</research_concerns>
