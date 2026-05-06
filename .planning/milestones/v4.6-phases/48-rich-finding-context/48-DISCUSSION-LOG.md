# Phase 48: Rich Finding Context - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-04
**Phase:** 48-rich-finding-context
**Areas discussed:** Finding schema shape, PQC purge scope, Deprecation deadline format, CI grep gate location & rigor

---

## Finding schema shape

### Q1 — How should the `description` field be added to findings?

| Option | Description | Selected |
|--------|-------------|----------|
| New `description` field, keep `recommendation` | Add `description` (1-3 sentence risk explanation) as a separate dict key alongside existing `title`/`recommendation`. Renderers show description above remediation. | ✓ |
| Rename `recommendation` → `remediation`, add `description` | Two new fields with semantically clean names matching the requirements text. Larger blast radius. | |
| Single combined field | Merge risk explanation and remediation into one prose block. Likely violates CONTEXT-01. | |

**User's choice:** New `description` field, keep `recommendation`
**Notes:** Matches success criterion #1 verbatim. Minimum-viable contract change.

### Q2 — How should we enforce that every finding has a non-empty `description`?

| Option | Description | Selected |
|--------|-------------|----------|
| Helper builder + unit test | `_build_finding(...)` helper requires `description` as positional arg; unit test asserts non-empty across fixtures. | ✓ |
| Pydantic/TypedDict model | Promote findings to typed model. Stronger long-term but adds class + serialization shim. | |
| Runtime validation pass | Validator at end of `evaluate_endpoints()` raises on empty/missing. Failures surface late. | |

**User's choice:** Helper builder + unit test
**Notes:** Construction-time enforcement is unmissable. Helper also injects D-06 deprecation constant.

---

## PQC purge scope

### Q3 — What scope should the PQC terminology purge cover?

| Option | Description | Selected |
|--------|-------------|----------|
| Source code + project docs | `quirk/**/*.py` + `docs/**/*.md` + Jinja/HTML templates under `quirk/`. Excludes `quirk-output/` and `.planning/`. | ✓ |
| Strict — only the two gated files | Modify only `risk_engine.py` and dashboard scan route. Leaves `docs/*.md` stale — drift risk. | |
| Everything except generated artifacts | Include tests + chaos lab `expected_results_*.md`. Maximum consistency, larger blast radius. | |

**User's choice:** Source code + project docs
**Notes:** Fixes the truth at source; artifacts self-heal on next scan.

### Q4 — What's the canonical replacement string for legacy PQC terminology?

| Option | Description | Selected |
|--------|-------------|----------|
| FIPS-only naming | `ML-KEM` / `ML-DSA` / `SLH-DSA` only, no aliases. | |
| FIPS with one-time clarifier | `ML-KEM (FIPS 203)` on first use per document. | |
| FIPS with FIPS standard number always | `ML-KEM (FIPS 203)` / `ML-DSA (FIPS 204)` / `SLH-DSA (FIPS 205)` everywhere. | ✓ |

**User's choice:** FIPS with FIPS standard number always
**Notes:** Maximum regulatory traceability. FIPS numbers become anchor for Phase 49 compliance map.

---

## Deprecation deadline format

### Q5 — How should NIST IR 8547 deprecation deadlines be represented?

| Option | Description | Selected |
|--------|-------------|----------|
| Prose embedded in `description`/`recommendation` | Sentence cites '2030 deprecated / 2035 disallowed' inline. No new schema field. | ✓ |
| Structured `deprecation` field | `deprecation: {deprecated_year, disallowed_year, source}`. Enables future filtering. | |
| Both — structured + prose mirror | Belt-and-suspenders. Drift risk if they desync. | |

**User's choice:** Prose embedded in `description`/`recommendation`
**Notes:** Smallest diff that satisfies success criterion #3. Structured field can be added later without breaking v4.6 contract.

### Q6 — Should the deprecation prose use a fixed canonical phrase across all findings?

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed canonical phrase via constant | `NIST_IR_8547_DEPRECATION` constant injected by `_build_finding`. | ✓ |
| Per-finding tailored phrasing | Natural in-context phrasing per finding. Drift risk, harder CI verification. | |

**User's choice:** Fixed canonical phrase via constant
**Notes:** One symbol to update when NIST revises; per-finding drift impossible.

---

## CI grep gate location & rigor

### Q7 — Which files should the CI grep gate scan?

| Option | Description | Selected |
|--------|-------------|----------|
| Two named files (resolved paths) | `quirk/engine/risk_engine.py` + `quirk/dashboard/api/routes/scan.py`. | ✓ |
| All of `quirk/` source tree | Wider safety net; exceeds success criterion #4. | |
| Two files + `docs/**/*.md` | Reinforces D-03 in CI; minor false-positive risk. | |

**User's choice:** Two named files (resolved paths)
**Notes:** Matches success criterion #4 verbatim with the real dashboard path resolved.

### Q8 — How rigorous should the grep gate be on the two files?

| Option | Description | Selected |
|--------|-------------|----------|
| Case-insensitive substring, no exemptions | `grep -i -E 'kyber|dilithium|when standards are adopted'`. Any match fails. | ✓ |
| Case-insensitive, exempt comments/docstrings | AST-aware tooling; allows educational comments. More maintenance. | |
| Word-boundary regex, case-insensitive | `\b(kyber|dilithium)\b`. Marginal value. | |

**User's choice:** Case-insensitive substring, no exemptions
**Notes:** Simplest, trivially auditable. Narrow gate scope (D-07) means no legitimate false positives.

---

## Claude's Discretion

- Exact prose wording of `description` strings per finding type — content
  decision deferred to planning/execution.
- Whether `NIST_IR_8547_DEPRECATION` is appended to `description` or
  `recommendation` (recommend `recommendation`; planner finalizes).
- File-system layout of the CI gate (`scripts/`, `Makefile`, or pytest
  test) — planner picks based on existing CI conventions.

## Deferred Ideas

- Structured `deprecation` field (revisit in v4.7 if filtering UX needed).
- Word-boundary regex CI gate (revisit if false positives appear).
- Comment/docstring exemption for educational PQC history.
- Purge of test fixtures + chaos lab `expected_results_*.md` files.
- `see_also` URL field per finding — already deferred to v4.7 (CONTEXT-05).
