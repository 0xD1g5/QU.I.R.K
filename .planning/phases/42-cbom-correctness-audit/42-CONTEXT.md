# Phase 42: CBOM Correctness Audit - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Lock down the CBOM pipeline so that:
1. Every CBOM JSON+XML output is valid against the official CycloneDX 1.6 schema (automated via pytest, every shipped chaos lab profile).
2. Every algorithm name observed in scanner output (against any chaos lab profile) is mapped to a real NIST PQC classification — no `unknown` fallback for in-scope cases.
3. Golden snapshot drift between v4.4 and v4.5 is intentional, documented, and accompanied by rationale.
4. Pass-2 / Pass-3 skip-list logic (motion plaintext + v4.3 DAR) has direct unit-test coverage.

This phase **audits and hardens** the existing CBOM pipeline (`quirk/cbom/`). It does NOT add new CBOM features, new connectors, or new output formats — those belong in other phases.

</domain>

<decisions>
## Implementation Decisions

### Schema Validation Source (CBOM-01)
- **D-01:** Use `cyclonedx-python-lib`'s built-in validators — `cyclonedx.validation.json.JsonStrictValidator` and `cyclonedx.validation.xml.XmlValidator` (or the equivalent v1.6 entry points for the installed version, currently `cyclonedx-python-lib>=11.7.0,<12`). The schema files ship inside the lib (`cyclonedx/schema/...`), so validation is offline, deterministic, and version-locked to the same library that produces the output.
- **D-02:** Do NOT vendor schema files into the repo and do NOT fetch from upstream at test time — both options were rejected (drift risk and CI flakiness respectively).
- **D-03:** Validation is implemented as a pytest check that runs the producer (`build_cbom` → `write_cbom_files`) against representative endpoint fixtures for **every shipped chaos lab profile** and asserts both JSON and XML outputs validate cleanly. Zero schema violations is the bar.

### Classifier Coverage Scope (CBOM-02)
- **D-04:** "In-scope" for the no-`unknown` rule is defined as **every algorithm name observed by running QU.I.R.K. scanners against every chaos lab profile** (the union of names that actually surface in real scan output). This is broader than the `expected_results_*.md` enumeration alone — it includes anything scanners emit, even if undocumented.
- **D-05:** A coverage report artifact is produced at **`docs/cbom-classifier-coverage.md`** (committed). It enumerates each observed algorithm name, its NIST PQC classification, and the source profile(s) that surfaced it.
- **D-06:** A pytest assertion is the gate: if the test discovers any algorithm classified as `unknown` for an in-scope name, the test fails. Adding a new chaos lab profile or a new algorithm-emitting scanner therefore forces an explicit classifier mapping update before CI goes green.

### Golden Snapshot Strategy (CBOM-03)
- **D-07:** Curated subset by **CBOM output shape**, not 1-per-profile. Existing goldens stay (broker, email — both motion-plaintext shape). Add one golden each for:
  - **TLS-with-cert** — recommended profile: `pki` (rich cert chain, deep TLS).
  - **Data-at-rest** — recommended profile: `vault` or `database` (planner picks the one with the most informative DAR fields).
  - **Identity** — recommended profile: `saml` (covers SAML signing/encryption metadata; alternative: `ldaps` if SAML coverage is too thin).
  - Final ~5–6 goldens. Schema validation gates the remaining profiles.
- **D-08:** Golden file location stays `tests/fixtures/cbom/expected_<shape>_cbom.json`. Regen mechanism stays Phase 35's `REGEN_CBOM_FIXTURES=1 pytest tests/test_cbom_motion_golden.py …` — extend (don't replace) that pattern for the new shapes.
- **D-09 (Claude's discretion):** Drift documentation lives in two places: (a) a sibling `tests/fixtures/cbom/CHANGELOG.md` that captures one rationale entry per intentional snapshot change with date + commit hash + reason; (b) the commit message itself. Inline JSON comments are not viable (JSON has no comments), so a sibling changelog is the cleanest place.

### Skip-List Test Scaffolding (CBOM-04 — Claude's discretion)
- **D-10:** Extract the motion-plaintext skip labels into a named constant in `quirk/cbom/builder.py` (e.g., `MOTION_PLAINTEXT_PROTOCOLS = frozenset({...})`) so unit tests can import it directly and assert the skip path is exercised for every label, without requiring a full integration fixture per case.
- **D-11:** Mirror the same approach for v4.3 DAR skip cases — extract a named constant, drive a parametrized pytest over it, assert each case is skipped at the documented Pass (2 or 3) and that no protocol/cert component is emitted for it.
- **D-12:** Existing integration-style coverage (full endpoint → CBOM round-trip) is retained — the new unit tests are additive and target the skip predicates in isolation.

### Claude's Discretion
- Drift-documentation form (D-09): chose sibling `CHANGELOG.md` over inline rationale.
- Skip-list scaffolding (D-10–D-12): chose extracted constants + direct unit tests over integration-only coverage.
- Specific lab profile picks within each "shape" (D-07): planner may swap if a different profile inside the same shape gives richer signal — the *shape coverage* matters, not the exact profile name.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` §"Phase 42: CBOM Correctness Audit" — phase goal, depends-on (Phase 40), success criteria.
- `.planning/REQUIREMENTS.md` §"CBOM-01"/"CBOM-02"/"CBOM-03"/"CBOM-04" — the four requirement entries this phase closes.

### CBOM pipeline (the code under audit)
- `quirk/cbom/builder.py` — `build_cbom()`; Pass-1 algorithms, Pass-2 certs (skip logic at `:439`), Pass-3 protocols (skip logic at `:522`). 522 lines.
- `quirk/cbom/classifier.py` — `classify_algorithm()`, `quantum_safety_label()`. `_FALLBACK = (CryptoPrimitive.UNKNOWN, None, None)` at `:181` is the gate to close.
- `quirk/cbom/writer.py` — `write_cbom_files()` using `JsonV1Dot6` + `XmlV1Dot6`.
- `quirk/cbom/__init__.py` — public re-exports (`build_cbom`, `write_cbom_files`, `classify_algorithm`).

### Existing tests (extend; do not replace)
- `tests/test_cbom_builder.py` — endpoint factory helpers (`_tls_endpoint`, `_ssh_endpoint`).
- `tests/test_cbom_classifier.py` — current classifier coverage; the new coverage gate adds to this.
- `tests/test_cbom_motion_golden.py` — Phase 35 golden pattern + `REGEN_CBOM_FIXTURES=1` workflow (lines 192, 195, 224, 236).
- `tests/test_cbom_motion_endpoints.py` — lab-shaped endpoint fixtures for motion plaintext.
- `tests/fixtures/cbom/expected_broker_cbom.json`, `expected_email_cbom.json`, `README.md` — existing goldens.

### Chaos lab oracle
- `quantum-chaos-enterprise-lab/docker-compose.yml` — full profile list (19 profiles enumerated in CONTEXT discussion).
- `quantum-chaos-enterprise-lab/expected_results_v3.md` (and any `expected_results_*.md` for newer milestones) — algorithm enumeration ground-truth.
- `quantum-chaos-enterprise-lab/lab.sh` — `ALL_PROFILES` list (per CLAUDE.md chaos-lab maintenance rule, must remain in sync — Phase 42 must not drift this).

### Spec & dependency
- CycloneDX 1.6 spec — accessed via the `cyclonedx-python-lib` (`cyclonedx-python-lib>=11.7.0,<12` in `pyproject.toml`); schema files bundled inside the wheel under `cyclonedx/schema/`.

### Codebase intel
- `.planning/codebase/STRUCTURE.md` §"`quirk/cbom/`" — directory purpose & key files.
- `.planning/codebase/TESTING.md` §"Test Structure" / "Mocking" / "Fixtures and Factories" — pytest conventions to follow.

### Project rules
- `CLAUDE.md` §"Chaos Lab Maintenance" — any lab change must touch `lab.sh` + `README.md` + `expected_results_*.md` together.
- `CLAUDE.md` §"Mandatory Phase Completion Steps" — Obsidian phase note + UAT-SERIES.md update + commit are required at end of `/gsd:execute-phase`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_tls_endpoint(**overrides)` and `_ssh_endpoint(**overrides)` factories in `tests/test_cbom_builder.py` — use these to build endpoint fixtures for new schema-validation tests instead of constructing CryptoEndpoint by hand.
- `tests/test_cbom_motion_endpoints.py` — already has lab-shaped endpoint synthesizers per profile; extend this rather than duplicate.
- `cyclonedx.validation.*` — built-in validators ship with the dependency; no new lib required.
- `REGEN_CBOM_FIXTURES=1` env-flag pattern from Phase 35 — reuse for any new golden-shape fixtures.
- `CryptoPrimitive` and `_LOOKUP` table in `quirk/cbom/classifier.py` — every closed `unknown` gap is a row added to `_LOOKUP`.

### Established Patterns
- pytest with bare asserts is the dominant style for new code (per `.planning/codebase/TESTING.md`); legacy `unittest.TestCase` classes exist but new tests should use bare-assert pytest.
- Mocks: `unittest.mock.patch` for httpx/subprocess/optional deps. The CBOM tests do NOT mock cyclonedx — they use the real library and real endpoint fixtures.
- Fixtures live in `tests/fixtures/<topic>/`; goldens are JSON; rationale/README sits alongside them as Markdown.
- Tests are flat in `tests/`; no subdirectories. Stick to `tests/test_cbom_<area>.py`.
- "Coverage report" Markdown artifacts (e.g., for classifier) are committed to `docs/`, not generated into `output/` (which is gitignored).

### Integration Points
- Schema validation hooks into the **end** of CBOM build: `build_cbom(...) → write_cbom_files(...) → validate written JSON + XML against bundled schema`. No upstream pipeline changes needed.
- Classifier coverage report is generated by walking `_LOOKUP` × the union of observed algorithm names from synthesized lab endpoints — no scanner rewrite needed.
- Skip-list extraction is local to `quirk/cbom/builder.py`; the public API of `build_cbom()` does not change.

</code_context>

<specifics>
## Specific Ideas

- Curated golden subset: `pki` for TLS-with-cert, `vault` or `database` for DAR, `saml` for identity (planner may pick `ldaps` if SAML coverage is too thin) — chosen by *CBOM output shape*, not protocol name.
- Coverage report path: `docs/cbom-classifier-coverage.md` (committed).
- Drift rationale path: `tests/fixtures/cbom/CHANGELOG.md` (sibling to the goldens).
- Skip-list constants: extract to `quirk/cbom/builder.py` module-level (e.g., `MOTION_PLAINTEXT_PROTOCOLS`, `DAR_SKIP_PROTOCOLS`) so they're directly importable for parametrized unit tests.
- Validators: prefer the strictest entry-point exposed by the installed `cyclonedx-python-lib` version (e.g., `JsonStrictValidator`) over lenient variants.

</specifics>

<deferred>
## Deferred Ideas

- **Per-profile golden expansion to all 19 lab profiles** — rejected for Phase 42 due to maintenance burden; revisit only if schema validation + curated goldens prove insufficient to catch a real regression.
- **Online schema fetch / vendored schema files** — rejected; dependency-bundled schema is the chosen source.
- **Inline rationale comments inside golden JSON files** — not viable (JSON has no comments). Sibling `CHANGELOG.md` is the substitute.
- **Schema-validation as a CLI flag on `quirk scan`** — out of scope; this phase is a test-time audit, not a runtime feature. Belongs in a future capability phase if ever desired.

</deferred>

---

*Phase: 42-cbom-correctness-audit*
*Context gathered: 2026-04-30*
