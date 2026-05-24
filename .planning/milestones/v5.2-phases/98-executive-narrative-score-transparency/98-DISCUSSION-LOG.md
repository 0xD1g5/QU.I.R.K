# Phase 98: Executive Narrative + Score Transparency - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-23
**Phase:** 98-executive-narrative-score-transparency
**Areas discussed:** Narrative generation method, Cross-surface content parity, Remediation roadmap structure, Score↔severity consistency

---

## Narrative generation method

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic templating (no LLM) | Rule-based composition: rating-band lead + score-driver/finding-derived clauses; offline, reproducible | ✓ |
| Optional LLM enrichment | Deterministic baseline + opt-in LLM polish; adds network/nondeterminism | |
| Author-time templates only | Hand-written blocks keyed only on rating band; minimal interpolation | |

**User's choice:** Deterministic templating (no LLM)
**Notes:** Consistent with QUIRK's offline/air-gap-safe design; LLM departure rejected.

### Narrative — top-risks business framing (follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| Algorithm-class → impact band mapping | Static map: crypto class + severity → short business-impact sentence; keeps Phase 98 at summary tier | ✓ |
| Reuse existing finding fields only | Frame from existing description/severity; may read technical | |
| Build full impact engine now | Rich per-finding "so what" — NOTE: Phase 99 scope (999.72) | |

**User's choice:** Algorithm-class → impact band mapping
**Notes:** Holds the 98/99 boundary — deep per-finding context stays in Phase 99.

---

## Cross-surface content parity

| Option | Description | Selected |
|--------|-------------|----------|
| Shared content model, format-specific render | Narrative/roadmap/decomposition built once as a structured object both renderers consume; PDF HTML-derived | ✓ |
| Markdown canonical → convert to HTML | executive.py markdown converted to HTML; couples HTML to markdown formatting | |
| Keep separate + golden parity test | Independent renderers + cross-surface parity assertion test | |

**User's choice:** Shared content model, format-specific render
**Notes:** Eliminates drift at the source rather than only testing for it.

---

## Remediation roadmap structure

| Option | Description | Selected |
|--------|-------------|----------|
| Impact×effort priority, keep time-horizon grouping | Order by impact×effort within existing now/next/later buckets | ✓ |
| Severity × quantum-agility ranking | Rank by severity weighted by agility signal; ignores effort | |
| Keep current time-horizon grouping only | Reuse buckets as-is + add rationale; no within-bucket priority | |

**User's choice:** Impact×effort priority, keep time-horizon grouping

### Roadmap — effort/impact source (follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| Static per-finding-type map | Maintained lookup: finding type/crypto class → (effort, impact) bands | ✓ |
| Derive from severity + score weights | Compute impact from severity/subscore weight + effort heuristic; coarse | |

**User's choice:** Static per-finding-type map
**Notes:** Aligns with the algorithm-class map from the narrative area — may be co-located.

---

## Score↔severity consistency

| Option | Description | Selected |
|--------|-------------|----------|
| Single source + reconciliation guard | One computed summary for headline language + detail counts, plus a congruence guard that fails the build/test on contradiction | ✓ |
| Single source only | Shared source, no explicit assertion | |
| Reconciliation test only | CI test scans generated report for contradiction; no runtime prevention | |

**User's choice:** Single source + reconciliation guard
**Notes:** Must prevent a contradictory report from being generated at runtime, not just flag it in CI.

## Claude's Discretion

- Exact narrative wording/templates, content-model dataclass structure, band thresholds in the algorithm-class and effort/impact maps, and test shapes.
- Whether to add a cross-surface parity test as corroboration to the shared model (D-03a).

## Deferred Ideas

- LLM narrative enrichment — rejected (offline determinism).
- PDF visual layout / typography / branding — Phase 100 (999.2).
- Rich per-finding "so what" + remediation guidance — Phase 99 (999.72).
- Code-signing cert expiry finding — Phase 99 (WR-05).
- DOCX editable export — Phase 100.
