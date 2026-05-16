# Phase 74: QRAMM + Compliance WARNINGs - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Close all 13 WARNING-severity audit findings in the QRAMM/compliance subsystem (`qramm-compliance/WR-01..WR-13`). Internal-contract changes + one customer-facing schema extension (compliance_map `coverage_status` field). No new pip dependencies.

**In scope (mapped to QWARN-NN requirements):**

- **QWARN-01** — Practice scoring correctness: out-of-range answer validation, Practice 1.1 endpoint-count integration, vuln_pct zero-algo sentinel + 'Indeterminate' maturity label, >=4.0 maturity ceiling reachable (closes WR-02, WR-04, WR-05, WR-06)
- **QWARN-02** — Evidence bridge correctness: `datetime.date` TZ-safe comparison, `synchronize_session` idempotent, `db.commit` failure handling, `attach_context` AttributeError logged not swallowed (closes WR-01, WR-03, WR-07, WR-08)
- **QWARN-03** — Migration advisor + compliance map + meta: word-boundary regex + canonical synonym map, `_walk_json_for_alg_strings` covers all `_ALG_KEYS`, compliance_map `coverage_status` field, `is_qramm_model_stale()` helper, stale Phase 50 TODO removed (closes WR-09, WR-10, WR-11, WR-12, WR-13)

**Out of scope:**

- API/CLI WARNINGs (Phase 75); React frontend WARNINGs (Phase 76)
- All BLOCKER-severity rows (closed in Phase 60 / 64.1 / 70)
- `quirk/engine/migration_planner.py` (16-line stub) — `wont-fix` per audit ledger; the real migration advisor is `quirk/assessment/migration_advisor.py` (WR-09 fix site)
- Any change to QRAMM question taxonomy (120-question structure stays) — D-14 do-not-touch
- Any change to the 5-band maturity scale itself — only the >=4.0 reachability and the new 'Indeterminate' label

</domain>

<decisions>
## Implementation Decisions

### compute_practice_score input validation (QWARN-01 / WR-02)

- **D-01 (locked):** `quirk/qramm/scoring.py::compute_practice_score` validates each answer ∈ {0, 1, 2, 3, 4} BEFORE summation. Out-of-range raises `ValueError(f"Practice score answer {answer!r} for {practice_id} out of range [0, 4]")`. Validate at the function entry; do NOT silently clamp.

### Practice 1.1 Discovery endpoint-count integration (QWARN-01 / WR-04)

- **D-02 (locked):** Practice 1.1 Discovery score multiplied by an endpoint-count factor: `discovery_factor = min(1.0, max(0.25, math.log10(max(endpoint_count, 1)) / 3.0))`. Rationale: 1 endpoint = 0.25 (penalized), 10 endpoints = 0.33, 100 = 0.67, 1000+ = 1.0 (full credit). A scan that found nothing cannot claim discovery maturity. `endpoint_count` is sourced from `evidence_summary.endpoint_count` (researcher confirms exact key name).
- **D-02a (Claude's discretion):** Curve shape — log10 vs linear vs piecewise. Default log10 (above); researcher picks if a clearer existing pattern fits.

### vuln_pct zero-algo sentinel (QWARN-01 / WR-05)

- **D-03 (locked):** When `total_algos == 0`, `vuln_pct = None` (sentinel). The maturity label becomes `"Indeterminate"` (NEW band added to MATURITY_LABELS as a sibling, not a numeric tier — sorts outside the 0..4 range). Output downstream (HTML, PDF, dashboard `ComplianceMapTab`) renders 'Indeterminate' with an em-dash subscore. Excluded from cohort statistics. Mirrors the 'n/a' pattern already used elsewhere in QRAMM.

### Maturity >=4.0 reachable (QWARN-01 / WR-06)

- **D-04 (locked):** Researcher confirms current curve. If the existing formula caps just below 4.0 due to floating-point or multiplier-stacking, adjust the band threshold so `>= 4.0` is reachable AT the strict profile multiplier ceiling (multiplier=1.0). Method: adjust the upper boundary check from `>= 4.0` to `>= 3.95` OR adjust the underlying score multiplier ceiling — researcher picks the minimal change. Add parametrized test asserting both 3.99 and 4.0 land in the top band.

### Evidence bridge TZ-safe date comparison (QWARN-02 / WR-01)

- **D-05 (locked):** `quirk/qramm/evidence_bridge.py` date equality currently compares ISO date strings, which drift across timezones if one side uses local TZ and the other uses UTC. Replace with `datetime.date` object comparison: parse both sides via `datetime.date.fromisoformat(s)` and compare `date_a == date_b`. If either side is a `datetime` (has time component), call `.date()` first. Both sides MUST be in the same TZ — bridge function accepts dates only (researcher confirms the existing call sites supply dates not datetimes).

### Evidence bridge idempotency (QWARN-02 / WR-03)

- **D-06 (locked):** The bridge runs an UPDATE with `synchronize_session=fetch` on every call. Make idempotent: BEFORE the UPDATE, query existing target rows; skip the UPDATE if the desired state already matches. Wrap the UPDATE in `try/except SQLAlchemyError as e: logger.warning("evidence_bridge UPDATE failed: %s", e); db.rollback(); return` (closes WR-07 in same task).

### Evidence bridge attach_context AttributeError (QWARN-02 / WR-08)

- **D-07 (locked):** `attach_context` swallows `AttributeError` silently when the source object lacks the expected attribute. Replace `except AttributeError:` with `except AttributeError as e: logger.warning("attach_context skipped — source object missing attribute: %s", e)`. User-context is then visibly skipped, not silently dropped.

### Migration advisor word-boundary regex + canonical synonyms (QWARN-03 / WR-09)

- **D-08 (locked):** `quirk/assessment/migration_advisor.py` substring matching replaced with word-boundary regex + module-level synonym map:
  ```python
  CANONICAL_ALG_SYNONYMS: dict[str, frozenset[str]] = {
      "DES": frozenset({"DES", "DES-EDE", "DES-CBC"}),
      "3DES": frozenset({"3DES", "TripleDES", "DES-EDE3"}),
      "RC4": frozenset({"RC4", "ARCFOUR"}),
      "MD5": frozenset({"MD5"}),
      "SHA1": frozenset({"SHA1", "SHA-1"}),
      # ...
  }
  def _matches(canonical: str, text: str) -> bool:
      variants = CANONICAL_ALG_SYNONYMS.get(canonical, frozenset({canonical}))
      pattern = r"\b(" + "|".join(re.escape(v) for v in variants) + r")\b"
      return bool(re.search(pattern, text, re.IGNORECASE))
  ```
  Word-boundaries (`\b`) eliminate the `'DES' in 'DESede'` false positive.

### _walk_json_for_alg_strings coverage (QWARN-03 / WR-10)

- **D-09 (locked):** `quirk/qramm/evidence_bridge.py:165::_walk_json_for_alg_strings` currently checks only `key in _ALG_KEYS` before recursing. Audit row notes it misses strings outside `_ALG_KEYS`. Extend: after the keyed check, ALSO scan ALL string values for canonical algorithm tokens via the new `migration_advisor::_matches` helper (or a lightweight inline variant). Researcher confirms whether to reuse the helper or inline a streamlined matcher.

### compliance_map coverage_status field (QWARN-03 / WR-11)

- **D-10 (locked):** Extend each `compliance_map.py` entry shape to include `coverage_status: Literal['covered', 'partial', 'pending', 'n/a']`. Semantics:
  - `'covered'` — fully mapped, contributes to rollup with its weight
  - `'partial'` — partial mapping, contributes at weight × 0.5
  - `'pending'` — not yet covered, EXCLUDED from rollup
  - `'n/a'` — intentionally out-of-scope, EXCLUDED from rollup
  Migration: every existing entry gets `'covered'` by default; entries with `weight=0.0` flip to `'pending'`. Add CI gate test `tests/test_compliance_coverage_status.py` asserting every entry has a valid status. Renders in HTML/PDF report compliance table as new column.
- **D-10a (Claude's discretion):** Whether the rollup excludes 'partial' contributions or counts them at half-weight. Default half-weight per the spec above.

### model_meta is_qramm_model_stale helper (QWARN-03 / WR-12)

- **D-11 (locked):** `quirk/qramm/model_meta.py` already has `STALENESS_THRESHOLD_DAYS = 90` and `last_verified`. Add public function:
  ```python
  def is_qramm_model_stale(today: datetime.date | None = None) -> bool:
      reference = today or datetime.date.today()
      age = (reference - datetime.date.fromisoformat(LAST_VERIFIED)).days
      return age > STALENESS_THRESHOLD_DAYS
  ```
  Used by `quirk doctor` (Phase 75 will wire it in) and by CI workflow (`.github/workflows/python-staleness.yml`). Test injects a synthetic `today` to exercise both branches.

### Stale Phase 50 TODO removal (QWARN-03 / WR-13)

- **D-12 (locked):** Researcher locates the stale `# TODO Phase 50:` comment in the production module header; delete it. Verify via `git blame` that the TODO is dead. If it cites work that did NOT land in Phase 50, capture in a deferred-items.md note before deletion.

### Phase-74 do-not-touch list

- **D-14 (locked):**
  - QRAMM 120-question taxonomy (questions.py) — no question text/structure changes
  - 5-band maturity scale itself — only the >=4.0 reachability and the new 'Indeterminate' label
  - `quirk/engine/migration_planner.py` — `wont-fix` per audit ledger
  - `tests/test_compliance_freshness.py` — Phase 49/50/56 invariant; D-10 adds NEW test, does not modify existing
  - QRAMM evidence bridge BLOCKERs (already closed by Phase 70) — only the WR rows in this phase

</decisions>

<canonical_refs>
## Canonical References

- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — 13 rows `qramm-compliance/WR-01..WR-13`
- `.planning/audit-2026-05-08/qramm-compliance/REVIEW.md` — file:line citations
- `.planning/REQUIREMENTS.md` — QWARN-01..QWARN-03 (note: requirement IDs may differ; researcher confirms naming)
- `.planning/ROADMAP.md` Phase 74 — 3 success criteria (gating)
- `.planning/phases/73-cbom-intel-reports-warnings/73-CONTEXT.md` — Phase 73 precedent for clamp + fail-loud (D-01), invariant test (D-04 model — applies to D-11), new helper module (D-08 mirrors weak_crypto.py shape)
- `.planning/phases/72-cloud-scanner-warnings/72-CONTEXT.md` — Phase 72 do-not-touch discipline (D-14 mirrors Phase 72 D-25)
- `quirk/qramm/scoring.py::compute_practice_score` — WR-02 site
- `quirk/qramm/scoring.py` Practice 1.1 + vuln_pct + maturity bands — WR-04, WR-05, WR-06 sites
- `quirk/qramm/evidence_bridge.py:150-200` — WR-01, WR-03, WR-07, WR-08, WR-10 sites
- `quirk/assessment/migration_advisor.py` — WR-09 site (NOT engine/migration_planner.py — that's the wont-fix stub)
- `quirk/qramm/compliance_map.py` — WR-11 site
- `quirk/qramm/model_meta.py` — WR-12 site
- `.github/workflows/python-staleness.yml` — D-11 helper consumer
- `quirk/util/weak_crypto.py` (Phase 73 NEW) — pattern reference for D-08's CANONICAL_ALG_SYNONYMS shape

</canonical_refs>

<code_context>
## Reusable Assets / Patterns

- **`quirk/util/weak_crypto.py::_WEAK_CIPHER_TOKENS` (Phase 73)** — frozenset + helper function shape. D-08 mirrors this for `CANONICAL_ALG_SYNONYMS`.
- **Phase 70 `_SAFE_COL_TYPE_RE` + ValueError pattern** — D-01 fail-loud validation follows this.
- **Phase 73 SCORE_WEIGHTS invariant test pattern** — D-11 staleness helper gets a similar CI gate.
- **`datetime.date.fromisoformat` pattern** (existing in `quirk/compliance/__init__.py` via the staleness check) — D-05 reuses.
- **`logger = logging.getLogger(__name__)` + `logger.warning(...)`** (project-wide idiom) — D-07 follows.
- **`Literal['covered', 'partial', 'pending', 'n/a']` typing pattern** — new for QRAMM; aligns with stdlib typing.Literal usage if Python version >=3.8.

</code_context>

<test_strategy>
## Test Approach

- **One test module per QWARN-NN requirement** (3 modules), mirroring Phase 73 granularity:
  - `tests/test_qramm_practice_scoring.py` — QWARN-01 (out-of-range ValueError, Practice 1.1 endpoint factor, vuln_pct Indeterminate sentinel, maturity >=4.0 reachable)
  - `tests/test_evidence_bridge_correctness.py` — QWARN-02 (TZ-safe date, idempotency, commit failure logged, AttributeError logged not swallowed)
  - `tests/test_migration_advisor_precision.py` + `tests/test_compliance_coverage_status.py` + `tests/test_qramm_model_stale.py` — QWARN-03 (word-boundary matching, coverage_status invariant, staleness helper)
- **RED-then-GREEN** per fix. D-08 parametrized table includes the canonical false-positive cases: `'DESede'`, `'AES-128'`, `'libdes3.so'`, `'TripleDES_v2'`.
- **D-11 staleness helper** test injects `today=date(2026,12,31)` to exercise stale branch and `today=date(2026,5,15)` for fresh branch.
- **D-10 schema test** asserts every entry in COMPLIANCE_MAP has a valid `coverage_status`; CI gate against accidental omission.
- **No new UAT-NN-NN cases** — internal contracts + one customer-facing field (compliance_map column). The new 'Indeterminate' maturity label and 'coverage_status' column are documented in the Phase 74 UAT-SERIES wrap note.
- **Audit ledger flip** — 13 rows to `Phase 74 | [x] closed`.

</test_strategy>

<deferred>
## Deferred Ideas

- **Migration of compliance_map `coverage_status` to per-framework granularity** (one status per control vs per row) — capture if operators request.
- **'Indeterminate' as a numeric maturity tier** instead of a sibling label — out of scope; revisit in v5.0 scoring refactor.
- **Synonym map externalization to YAML** — D-08 keeps it in `migration_advisor.py`; revisit if the map grows beyond ~20 algorithms.
- **`quirk doctor is-qramm-stale` CLI subcommand** — Phase 75 will wire `is_qramm_model_stale()` into `quirk doctor` output.

</deferred>
