# Phase 42: CBOM Correctness Audit - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 42-cbom-correctness-audit
**Areas discussed:** Schema validation source, Coverage scope (CBOM-02), Golden snapshot breadth

---

## Schema validation source (CBOM-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Use cyclonedx-python-lib validators | Import `JsonStrictValidator` + `XmlValidator` from `cyclonedx.validation.*` — schema bundled with the lib we already depend on. Offline, version-locked to producer, no extra deps. | ✓ |
| Vendor schema files in tests/ | Copy CycloneDX 1.6 .schema.json + .xsd into `tests/fixtures/schema/` and validate with jsonschema + lxml. Independent of lib upgrades but adds drift risk. | |
| Fetch from upstream at test time | GET from cyclonedx/specification on GitHub. Always current, but breaks offline CI and adds network flakiness. | |

**User's choice:** Use cyclonedx-python-lib validators (Recommended).
**Notes:** Avoids dual-source-of-truth between producer and validator. Offline + deterministic CI.

---

## Coverage scope (CBOM-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Lab-profile observed + Markdown report | In-scope = every algorithm name observed by running scanners against every chaos lab profile. Coverage report at `docs/cbom-classifier-coverage.md` (committed) AND asserted in pytest. | ✓ |
| Fixtures + lab observed, pytest-only | In-scope = union of (test fixture algorithms) and (lab-observed). Coverage asserted in pytest output only — no committed Markdown artifact. | |
| `expected_results_*.md` enumerated only | In-scope = exactly the algorithms listed in lab oracle files. Smallest scope, but misses anything scanners emit that wasn't pre-documented. | |

**User's choice:** Lab-profile observed + Markdown report (Recommended).
**Notes:** Catches drift caused by scanners emitting names that pre-date documented oracles; Markdown artifact gives consultants a human-readable coverage matrix.

---

## Golden snapshot breadth (CBOM-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Curated subset by CBOM shape | Keep broker + email; add 1 golden each for TLS-with-cert (`pki`), DAR (`vault`/`database`), and identity (`saml`). ~5–6 goldens covering distinct CBOM output shapes. Schema validation gates the rest. | ✓ |
| All 19 lab profiles | One golden per profile. Maximum drift detection, maximum maintenance burden. | |
| Keep 2, schema-only for rest | Don't expand goldens. Rely on schema + classifier coverage for the other 17 profiles. | |

**User's choice:** Curated subset by CBOM shape (Recommended).
**Notes:** Balances regression coverage against maintenance burden; the *output shape* is what matters, not the per-profile permutation.

---

## Claude's Discretion

- **Drift documentation form (D-09):** sibling `tests/fixtures/cbom/CHANGELOG.md` + commit message. Inline JSON comments not viable (JSON spec has no comments).
- **Skip-list test scaffolding (D-10–D-12):** extract motion-plaintext + DAR skip labels into named module-level constants in `quirk/cbom/builder.py`; parametrize unit tests over those constants. Existing integration tests retained, new tests are additive.
- **Specific lab profile picks within each "shape" (D-07):** planner may swap (e.g., `ldaps` instead of `saml` for identity) if a sibling profile in the same shape gives richer signal.

## Deferred Ideas

- Per-profile golden expansion to all 19 lab profiles — revisit only if schema + curated goldens miss a real regression.
- Online schema fetch / vendored schema files — rejected.
- Inline rationale comments inside golden JSON files — not viable.
- Schema validation as a runtime CLI flag on `quirk scan` — out of scope; future capability phase if ever desired.
