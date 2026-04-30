# Phase 42: CBOM Correctness Audit — Research

**Researched:** 2026-04-30
**Domain:** CycloneDX 1.6 schema validation, algorithm classifier coverage, golden-snapshot drift control, skip-list scaffolding (CBOM pipeline audit)
**Confidence:** HIGH

## Summary

Phase 42 hardens an already-shipping CBOM pipeline (`quirk/cbom/`). All four requirements (CBOM-01..04) target test-time hardening, not production behavior changes — the public `build_cbom()` / `write_cbom_files()` API does not change. The single non-trivial finding from this research: `cyclonedx-python-lib` ships its CycloneDX 1.6 validators behind **optional extras** (`json-validation`, `xml-validation`, or the umbrella `validation`) that are NOT currently declared in `pyproject.toml`. The Phase 42 plan must add `cyclonedx-python-lib[validation]` (or pin the two sub-extras) to `dependencies` (or to a dev-only group) before any pytest schema gate can succeed. Validator API, classifier shape, skip-list locations, profile inventory, and golden-snapshot regen path are all confirmed and ready for planning.

**Primary recommendation:** Use `JsonStrictValidator(SchemaVersion.V1_6)` and `XmlValidator(SchemaVersion.V1_6)` from `cyclonedx-python-lib[validation]` — both expose `validate_str(data, *, all_errors=False)` returning `None` on valid, a `*ValidationError` on invalid. Drive the gate from a single pytest test that synthesizes endpoint fixtures for every shipped chaos-lab profile, runs `build_cbom() → write_cbom_files()`, then re-reads the JSON and XML and asserts `validator.validate_str(text) is None`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Schema Validation Source (CBOM-01)
- **D-01:** Use `cyclonedx-python-lib`'s built-in validators — `cyclonedx.validation.json.JsonStrictValidator` and `cyclonedx.validation.xml.XmlValidator` (or the equivalent v1.6 entry points for the installed version, currently `cyclonedx-python-lib>=11.7.0,<12`). The schema files ship inside the lib (`cyclonedx/schema/...`), so validation is offline, deterministic, and version-locked to the same library that produces the output.
- **D-02:** Do NOT vendor schema files into the repo and do NOT fetch from upstream at test time — both options were rejected (drift risk and CI flakiness respectively).
- **D-03:** Validation is implemented as a pytest check that runs the producer (`build_cbom` → `write_cbom_files`) against representative endpoint fixtures for **every shipped chaos lab profile** and asserts both JSON and XML outputs validate cleanly. Zero schema violations is the bar.

#### Classifier Coverage Scope (CBOM-02)
- **D-04:** "In-scope" for the no-`unknown` rule is defined as **every algorithm name observed by running QU.I.R.K. scanners against every chaos lab profile** (the union of names that actually surface in real scan output). Broader than `expected_results_*.md` enumeration alone.
- **D-05:** Coverage report artifact at **`docs/cbom-classifier-coverage.md`** (committed). Enumerates each observed algorithm name, its NIST PQC classification, and the source profile(s) that surfaced it.
- **D-06:** A pytest assertion is the gate: any algorithm classified as `unknown` for an in-scope name fails the test.

#### Golden Snapshot Strategy (CBOM-03)
- **D-07:** Curated subset by **CBOM output shape**, not 1-per-profile. Existing goldens stay (broker, email — both motion-plaintext shape). Add one golden each for: TLS-with-cert (`pki`), Data-at-rest (`vault` or `database`), Identity (`saml`, fallback `ldaps`). Final ~5–6 goldens.
- **D-08:** Golden file location stays `tests/fixtures/cbom/expected_<shape>_cbom.json`. Regen mechanism stays Phase 35's `REGEN_CBOM_FIXTURES=1` env-flag.
- **D-09 (Claude's discretion):** Drift documentation lives in `tests/fixtures/cbom/CHANGELOG.md` (sibling to goldens) AND in commit messages. Inline JSON comments not viable.

#### Skip-List Test Scaffolding (CBOM-04 — Claude's discretion)
- **D-10:** Extract motion-plaintext skip labels into a named constant in `quirk/cbom/builder.py` (`MOTION_PLAINTEXT_PROTOCOLS = frozenset({...})`). Unit tests import it directly.
- **D-11:** Mirror approach for v4.3 DAR skip cases — extract a named constant, drive a parametrized pytest, assert each case is skipped at the documented Pass.
- **D-12:** Existing integration-style coverage retained — new unit tests are additive and target skip predicates in isolation.

### Claude's Discretion
- Drift-documentation form (D-09): chose sibling `CHANGELOG.md` over inline rationale.
- Skip-list scaffolding (D-10–D-12): chose extracted constants + direct unit tests over integration-only coverage.
- Specific lab profile picks within each "shape" (D-07): planner may swap if a different profile inside the same shape gives richer signal.

### Deferred Ideas (OUT OF SCOPE)
- Per-profile golden expansion to all 19 lab profiles — rejected for Phase 42 (maintenance burden).
- Online schema fetch / vendored schema files — rejected (dependency-bundled is the chosen source).
- Inline rationale comments inside golden JSON files — not viable.
- Schema-validation as a CLI flag on `quirk scan` — out of scope; test-time audit only.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **CBOM-01** | CBOM JSON and XML outputs validate against the official CycloneDX 1.6 schema for every shipped chaos lab profile; validation is automated as a pytest check. | Confirmed validator entry points, return semantics, optional-extras requirement, and SchemaVersion.V1_6 enum. See "Standard Stack" + "Code Examples" + "Common Pitfalls #1". |
| **CBOM-02** | Algorithm classifier coverage report; no `unknown` fallbacks for in-scope cases. | Confirmed `_ALGORITHM_TABLE` shape and `_FALLBACK` location at `classifier.py:181`. Coverage walk = union of algorithm names observed when `build_cbom()` runs against synthesized lab endpoints from all 19 profiles. |
| **CBOM-03** | Golden snapshot drift between v4.4 and v4.5 is reviewed; intentional, documented, accompanied by snapshot update commit with rationale. | Existing Phase 35 mechanism (`REGEN_CBOM_FIXTURES=1`) extends cleanly. Need 3 new endpoint synthesizers (TLS-with-cert / DAR / identity) modelled on `_build_email_lab_endpoints()` / `_build_broker_lab_endpoints()`. |
| **CBOM-04** | Pass-2 / Pass-3 skip-list logic unit-tested for all motion-plaintext labels and all v4.3 DAR skip cases. | Skip-list literals located at `builder.py:436-440` (Pass 2) and `builder.py:519-523` (Pass 3). Refactor target identified — see "Code Examples #4". |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CycloneDX schema validation | Test-time (pytest) | — | D-03 locks this as a test-only gate, not a runtime feature. |
| Endpoint fixture synthesis | Test fixtures (`tests/test_cbom_*_endpoints.py`) | — | No DB, no Docker — pure CryptoEndpoint construction. |
| Algorithm classification | `quirk/cbom/classifier.py` (lib code) | Coverage report generator (test/script) | `_ALGORITHM_TABLE` is library data; coverage MD artifact is a separate generator. |
| Skip-list constants | `quirk/cbom/builder.py` module-level | Tests import the constants directly | D-10/D-11 mandate module-level export so tests can parametrize over the source of truth. |
| Golden snapshot files | `tests/fixtures/cbom/` | Sibling `CHANGELOG.md` for drift rationale | D-08/D-09. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cyclonedx-python-lib` | `>=11.7.0,<12` (currently 11.7.0 installed) [VERIFIED: `pip show`, `pyproject.toml`] | CBOM model, JSON/XML serializer, **and** CycloneDX 1.6 schema validator | Already the producer in `writer.py`. Keeping the validator in the same library guarantees serializer/validator version lockstep — no schema drift. |
| `pytest` | as-installed | Test runner; parametrized test driver for skip-list coverage | Project convention (`pyproject.toml` `[tool.pytest.ini_options]`). |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `jsonschema[format-nongpl]` | `>=4.25,<5.0` (transitive via `cyclonedx-python-lib[json-validation]`) [VERIFIED: package metadata] | Backs `JsonStrictValidator` | Required for CBOM-01 JSON gate — installed automatically when the `validation` extra is selected. |
| `lxml` | `>=4,<7` (transitive via `cyclonedx-python-lib[xml-validation]`) [VERIFIED: package metadata] | Backs `XmlValidator` | Required for CBOM-01 XML gate. Already in project deps (`lxml>=6.0`) — but the cyclonedx XML validator path requires the `xml-validation` extra to be **declared** so the wheel actually wires it up. |
| `referencing` | `>=0.28.4` (transitive) | Used by jsonschema-based validation | Auto-installed with `json-validation` extra. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `cyclonedx-python-lib[validation]` extra | Bundle the schema files into the repo | Rejected by D-02 (drift risk). |
| `cyclonedx-python-lib` validators | Online fetch from `cyclonedx/specification` repo at test time | Rejected by D-02 (CI flakiness). |
| `JsonStrictValidator` | `JsonValidator` (lenient variant — accepts extra fields) | Use the strict variant — phase goal is to catch any spec drift, not tolerate it. |

**Installation directive (the only dependency change Phase 42 needs):**

```toml
# pyproject.toml [project] dependencies — current pin
"cyclonedx-python-lib>=11.7.0,<12",

# Phase 42 must change this to (or add a dev/test extra group containing):
"cyclonedx-python-lib[validation]>=11.7.0,<12",
```

**Version verification:**
- `pip show cyclonedx-python-lib` -> 11.7.0 (verified locally 2026-04-30) [VERIFIED]
- `[Provides-Extra]`: `json-validation`, `xml-validation`, `validation` (umbrella) [VERIFIED: `importlib.metadata`]
- `SchemaVersion.V1_6` is a member of `cyclonedx.schema.SchemaVersion` (alongside V1_0..V1_7) [VERIFIED]

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────┐
   chaos-lab profile ──► │ endpoint-synthesizer fns    │  (one per profile-shape)
   (port map oracle)     │ (CryptoEndpoint factories)  │
                         └──────────────┬──────────────┘
                                        │ list[CryptoEndpoint]
                                        ▼
                          ┌────────────────────────────┐
                          │ build_cbom()               │
                          │  Pass 1: algorithms        │ ◄─── classify_algorithm()
                          │  Pass 2: certs (skip-list) │      └ _ALGORITHM_TABLE
                          │  Pass 3: protos (skip-list)│
                          └──────────────┬─────────────┘
                                         │ Bom
                                         ▼
                          ┌────────────────────────────┐
                          │ write_cbom_files()         │
                          │  → cbom-{stamp}.cdx.json   │
                          │  → cbom-{stamp}.cdx.xml    │
                          └──────────────┬─────────────┘
                                         │ files
                          ┌──────────────┴─────────────┐
                          ▼                            ▼
              ┌──────────────────────┐   ┌──────────────────────┐
              │ JsonStrictValidator  │   │ XmlValidator         │  (CBOM-01 gate)
              │ (V1_6).validate_str  │   │ (V1_6).validate_str  │
              └──────────────────────┘   └──────────────────────┘
                          │                            │
                          └────────► assert is None ◄──┘

         Parallel paths (no file I/O):
            • CBOM-02 coverage: walk algo_registry + _ALGORITHM_TABLE → docs/cbom-classifier-coverage.md
            • CBOM-03 goldens : _normalize_bom_for_snapshot(bom) → tests/fixtures/cbom/*.json
            • CBOM-04 skip   : import MOTION_PLAINTEXT_PROTOCOLS / DAR_SKIP_PROTOCOLS,
                                parametrize, assert no cert/proto component for each
```

### Recommended Project Structure

```
quirk/cbom/
├── __init__.py          # public re-exports — unchanged
├── builder.py           # ADD: MOTION_PLAINTEXT_PROTOCOLS, DAR_SKIP_PROTOCOLS module-level frozensets
├── classifier.py        # _ALGORITHM_TABLE — append rows to close any unknown gap
└── writer.py            # unchanged

tests/
├── test_cbom_classifier.py            # extend with coverage-gate test
├── test_cbom_classifier_coverage.py   # NEW: builds docs/cbom-classifier-coverage.md, asserts no unknowns
├── test_cbom_schema_validation.py     # NEW (CBOM-01): per-profile JSON+XML validate
├── test_cbom_skip_lists.py            # NEW (CBOM-04): parametrized over the two frozensets
├── test_cbom_motion_endpoints.py      # existing — extend (don't replace)
├── test_cbom_motion_golden.py         # existing — extend with new shape goldens
└── fixtures/cbom/
    ├── expected_email_cbom.json       # existing
    ├── expected_broker_cbom.json      # existing
    ├── expected_pki_cbom.json         # NEW (D-07)
    ├── expected_vault_cbom.json       # NEW (D-07; or expected_database_cbom.json)
    ├── expected_saml_cbom.json        # NEW (D-07; or expected_ldaps_cbom.json)
    ├── CHANGELOG.md                   # NEW (D-09): drift rationale log
    └── README.md                      # update to point at CHANGELOG

docs/
└── cbom-classifier-coverage.md        # NEW (D-05): generated artifact, committed
```

### Pattern 1: Strict CycloneDX validator usage
**What:** Both validators expose the same surface: `validate_str(data: str, *, all_errors: bool = False) -> None | <Error> | Iterable[<Error>]`. **`None` means valid.** A non-None return (or raised exception when input is malformed JSON/XML before schema check) means invalid. [VERIFIED: `inspect.signature` on installed 11.7.0]

**When to use:** A pytest test parametrized over chaos-lab profiles.

```python
# Source: cyclonedx-python-lib 11.7.0 — inspect.signature on JsonStrictValidator.validate_str
from cyclonedx.validation.json import JsonStrictValidator
from cyclonedx.validation.xml import XmlValidator
from cyclonedx.schema import SchemaVersion

json_v = JsonStrictValidator(SchemaVersion.V1_6)
xml_v  = XmlValidator(SchemaVersion.V1_6)

result = json_v.validate_str(json_text)   # None ⇒ valid
assert result is None, f"JSON schema violation: {result}"
result = xml_v.validate_str(xml_text)
assert result is None, f"XML schema violation: {result}"
```

### Pattern 2: Phase 35 endpoint synthesizer (the template for new shapes)
**What:** Hand-built `list[CryptoEndpoint]` mirroring the chaos-lab port map verbatim — no DB, no Docker. The function `_build_broker_lab_endpoints()` in `tests/test_cbom_motion_golden.py` is the canonical template.

**When to use:** Need a CBOM fixture for a new lab profile shape (D-07's `pki`, `vault`/`database`, `saml`/`ldaps`).

### Pattern 3: Phase 35 snapshot normalization
**What:** `_normalize_bom_for_snapshot()` (in `test_cbom_motion_golden.py:126`) strips volatile fields (timestamp, UUIDs, serials) and sorts components by `bom_ref` so the JSON snapshot is deterministic. Reuse verbatim — do NOT reinvent.

### Anti-Patterns to Avoid
- **Vendoring `cyclonedx-spec/schema/*.json` into the repo.** Rejected by D-02; creates a second source of truth that drifts from the installed lib.
- **Spinning up Docker/`lab.sh up` inside pytest.** No CBOM test in this codebase does this — they all synthesize endpoints. Don't be the first.
- **Hand-rolling a JSON schema validator.** D-01 mandates the bundled validator; jsonschema is already a transitive optional.
- **Using `JsonValidator` (lenient).** Use `JsonStrictValidator` — Phase 42's bar is "zero spec violations," not "tolerable spec violations."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CycloneDX 1.6 schema validation | Custom JSON-schema fetcher + jsonschema wiring | `cyclonedx.validation.json.JsonStrictValidator(SchemaVersion.V1_6)` | Same library that produces the output owns the schema — versions stay locked. |
| XML schema validation | Custom XSD loader via `lxml.etree.XMLSchema` | `cyclonedx.validation.xml.XmlValidator(SchemaVersion.V1_6)` | Same reason. The XSDs ship inside the wheel under `cyclonedx/schema/`. |
| Snapshot diff/normalization | New diff library | Reuse `_normalize_bom_for_snapshot()` from `test_cbom_motion_golden.py:126` | Already strips timestamps/UUIDs/serials and sorts deterministically. |
| Endpoint factories | Construct `CryptoEndpoint(...)` inline in 5 places | `_tls_endpoint(**overrides)` from `test_cbom_builder.py` | Test code reuse rule — already established pattern. |
| Coverage walk | Run scanners against live containers | Run `build_cbom()` against the synthesized endpoints (per-profile fixtures) and dump `algo_registry.keys()` | No Docker / no network in tests; same shape as golden tests. |

**Key insight:** The CBOM pipeline is already test-friendly — every Phase 42 task can be solved by extending existing patterns (`_tls_endpoint`, `_normalize_bom_for_snapshot`, `REGEN_CBOM_FIXTURES=1`, `_ALGORITHM_TABLE` row append). No new architectural concepts.

## Common Pitfalls

### Pitfall 1: Optional-extras module-not-found at validate time
**What goes wrong:** `from cyclonedx.validation.json import JsonStrictValidator` succeeds, but `validate_str(...)` raises `cyclonedx.exception.MissingOptionalDependencyException: This functionality requires optional dependencies. Please install cyclonedx-python-lib with the extra "json-validation"`.

**Why it happens:** The validator class loads lazily; the `jsonschema` import is deferred to `validate_str`. Installing `cyclonedx-python-lib` without an extra silently produces a non-functional validator. This was verified locally on 2026-04-30. [VERIFIED: live `python3 -c` reproduction]

**How to avoid:** Phase 42 plan MUST update `pyproject.toml` to require the extra. Either:
- `"cyclonedx-python-lib[validation]>=11.7.0,<12"` (umbrella — pulls both JSON + XML), or
- declare a dev/test optional-dependencies group with `cyclonedx-python-lib[validation]`.

**Warning signs:** Test fails at runtime with `MissingOptionalDependencyException`, not at import. CI may pass on a dev box that has `jsonschema` from another package and fail on a fresh container.

### Pitfall 2: Validator returns vs raises
**What goes wrong:** Treating `validate_str` like `assert` (expecting a raise on invalid).

**Why it happens:** API actually **returns** `None` on success and **returns** a `JsonValidationError` / `XmlValidationError` on failure (when `all_errors=False`). It does not raise. [VERIFIED: `inspect.signature`]

**How to avoid:** Use `assert validator.validate_str(text) is None, ...` — never wrap in `try/except` to detect invalid output.

### Pitfall 3: Drift between `lab.sh` ALL_PROFILES and `docker-compose.yml` profiles
**What goes wrong:** Phase 42 adds endpoint synthesizers for profiles that the chaos lab no longer ships, or skips profiles the lab does ship.

**Why it happens:** `lab.sh` derives profiles dynamically (`_derive_all_profiles` in `lab.sh:56-65`) — there is no hardcoded list. But the test code will hardcode profile names. CLAUDE.md "Chaos Lab Maintenance" rule binds: any profile-list reference must stay in sync with `docker-compose.yml`.

**How to avoid:** Source-of-truth for the test parametrization is `docker-compose.yml`. Either parse it in the test or hardcode against the verified inventory below (19 profiles as of 2026-04-30) and add a sentinel test that re-derives from compose and fails if drift occurs.

**Verified profile inventory (19 profiles)** [VERIFIED: `grep "profiles:" docker-compose.yml`]:
`broker`, `cloud`, `database`, `dnssec`, `email`, `identity`, `jwt`, `kerberos`, `ldaps`, `phaseA`, `pki`, `registry`, `saml`, `source`, `ssh-weak`, `storage`, `storage-s3`, `vault`. (Note: `identity` and `phaseA` are listed both alone and as a multi-profile member.)

### Pitfall 4: `_FALLBACK` is also a legitimate output for some inputs
**What goes wrong:** A coverage gate that asserts "every algorithm name maps to non-fallback" breaks on legitimate cases like `classify_algorithm("none")` (JWT alg:none — verified to return `(UNKNOWN, 0, 0)` on purpose).

**Why it happens:** `_ALGORITHM_TABLE["none"] = (CryptoPrimitive.UNKNOWN, 0, 0)` — it's an intentional sentinel for the JWT `alg:none` critical-vuln finding. There is also `kerberos-unreachable`, `GCS-SUMMARY`, `NSEC`, `DS-MISMATCH`, `SHA1-DS`, `NONE` (DNSSEC) — these are filtered out **upstream in `builder.py`** (lines 385, 396, 407) and never reach the classifier.

**How to avoid:** The CBOM-02 coverage gate must operate on the algorithm names that actually appear in the CBOM (i.e., walk `algo_registry` after `build_cbom()` runs), not on every name the classifier could be asked about. This automatically excludes the synthetic finding labels because they're filtered before registration.

### Pitfall 5: Snapshot churn from cipher-suite name preservation
**What goes wrong:** A new endpoint synthesizer uses a cipher suite name not yet seen, the cipher decomposes into a new algorithm, snapshot diff is huge.

**Why it happens:** `_decompose_cipher_suite` (builder.py:158) is order-sensitive; new suites can shift component ordering. Snapshot is sorted by `bom_ref` so additions are localized — but new algorithms still produce new bom_refs.

**How to avoid:** When writing a new endpoint synthesizer for D-07, prefer cipher suites whose decomposed parts are already in `_ALGORITHM_TABLE`. If a new algorithm appears, document in `tests/fixtures/cbom/CHANGELOG.md` why the snapshot grew.

## Code Examples

Verified patterns from official sources and the existing codebase:

### Example 1: Schema validation gate (CBOM-01)
```python
# tests/test_cbom_schema_validation.py — NEW
# Source pattern: validator API verified via inspect.signature on cyclonedx-python-lib 11.7.0
from pathlib import Path
import pytest
from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonStrictValidator
from cyclonedx.validation.xml import XmlValidator

from quirk.cbom.builder import build_cbom
from quirk.cbom.writer import write_cbom_files

# Profile -> endpoint-synthesizer registry (extend as new shapes are added)
PROFILE_ENDPOINTS = {
    "email":   _build_email_lab_endpoints,
    "broker":  _build_broker_lab_endpoints,
    "pki":     _build_pki_lab_endpoints,        # NEW (D-07)
    "vault":   _build_vault_lab_endpoints,       # NEW (D-07)
    "saml":    _build_saml_lab_endpoints,        # NEW (D-07)
    # ... 19 entries total — one per docker-compose.yml profile
}

@pytest.mark.parametrize("profile", sorted(PROFILE_ENDPOINTS))
def test_cbom_validates_against_cyclonedx_1_6(profile, tmp_path):
    bom = build_cbom(PROFILE_ENDPOINTS[profile]())
    json_path, xml_path = write_cbom_files(bom, str(tmp_path), "test")

    json_v = JsonStrictValidator(SchemaVersion.V1_6)
    xml_v  = XmlValidator(SchemaVersion.V1_6)

    j_err = json_v.validate_str(Path(json_path).read_text())
    assert j_err is None, f"[{profile}] JSON schema violation: {j_err}"

    x_err = xml_v.validate_str(Path(xml_path).read_text())
    assert x_err is None, f"[{profile}] XML schema violation: {x_err}"
```

### Example 2: Classifier coverage gate (CBOM-02)
```python
# tests/test_cbom_classifier_coverage.py — NEW
from cyclonedx.model.crypto import CryptoPrimitive
from quirk.cbom.builder import build_cbom
from quirk.cbom.classifier import classify_algorithm

def test_no_unknown_classifications_across_lab_profiles():
    """Every algorithm name that surfaces from any chaos-lab profile must
    classify to a non-UNKNOWN primitive (per D-04/D-06).
    """
    seen: dict[str, set[str]] = {}  # algo_name -> {profiles_that_surfaced_it}
    for profile, builder_fn in PROFILE_ENDPOINTS.items():
        bom = build_cbom(builder_fn())
        for c in bom.components:
            cp = c.crypto_properties
            if cp and cp.asset_type and cp.asset_type.value == "algorithm":
                seen.setdefault(c.name, set()).add(profile)

    unknowns = []
    for name, profiles in seen.items():
        primitive, nist_level, _ = classify_algorithm(name)
        # NIST-level None marks not-yet-classified; UNKNOWN with level 0 is
        # the legitimate "alg:none" sentinel — distinguish via name.
        if primitive == CryptoPrimitive.UNKNOWN and name.lower() != "none":
            unknowns.append((name, sorted(profiles)))

    assert not unknowns, (
        f"In-scope algorithms classified as UNKNOWN — add rows to "
        f"_ALGORITHM_TABLE: {unknowns}"
    )
```

### Example 3: Coverage report generator (CBOM-02 / D-05)
```python
# tests/test_cbom_classifier_coverage.py — companion to the gate above
def test_regenerate_coverage_report(tmp_path):
    """When REGEN_CBOM_COVERAGE=1, write docs/cbom-classifier-coverage.md."""
    if os.environ.get("REGEN_CBOM_COVERAGE") != "1":
        pytest.skip("set REGEN_CBOM_COVERAGE=1 to regenerate")

    rows = []  # (name, primitive, nist_level, classical_level, [profiles])
    # ... walk PROFILE_ENDPOINTS, dedupe, sort
    Path("docs/cbom-classifier-coverage.md").write_text(_render_md(rows))
```

### Example 4: Skip-list extraction + parametrized test (CBOM-04 / D-10/D-11)
```python
# quirk/cbom/builder.py — NEW module-level constants (replace inline literals)
MOTION_PLAINTEXT_PROTOCOLS = frozenset({
    "KAFKA-PLAIN", "AMQP-PLAIN", "REDIS-PLAIN",
})
DAR_SKIP_PROTOCOLS = frozenset({
    "POSTGRESQL", "MYSQL", "RDS",
    "S3", "AZURE_BLOB",
    "KUBERNETES", "VAULT",
    "GCP", "CLOUD_SQL",  # already in skip list at builder.py:436
})
# Existing tuple literals at builder.py:436-440 and :519-523 become:
#   if ep.protocol in (
#       "SSH","CONTAINER","SOURCE","KERBEROS","SAML","DNSSEC",
#       *DAR_SKIP_PROTOCOLS, *MOTION_PLAINTEXT_PROTOCOLS,
#   ): continue
```

```python
# tests/test_cbom_skip_lists.py — NEW
import pytest
from quirk.cbom.builder import (
    build_cbom, MOTION_PLAINTEXT_PROTOCOLS, DAR_SKIP_PROTOCOLS,
)
from quirk.models import CryptoEndpoint

@pytest.mark.parametrize("protocol", sorted(MOTION_PLAINTEXT_PROTOCOLS | DAR_SKIP_PROTOCOLS))
def test_skip_protocol_emits_no_cert_or_proto_component(protocol):
    """Pass 2 + Pass 3 must both skip the listed protocols (CBOM-04)."""
    ep = CryptoEndpoint(host="h", port=1, protocol=protocol,
                        cert_pubkey_alg="RSA", cert_pubkey_size=2048,
                        cipher_suite="TLS_RSA_WITH_AES_128_CBC_SHA",
                        tls_version="TLSv1.2",
                        cert_sig_alg=None, cert_subject=None, cert_issuer=None,
                        cert_not_before=None, cert_not_after=None,
                        tls_capabilities_json=None, ssh_audit_json=None)
    bom = build_cbom([ep])
    refs = {str(c.bom_ref.value) for c in bom.components}
    assert not any(r.startswith(f"crypto/certificate/h:1") for r in refs)
    assert not any(r.startswith(f"crypto/protocol/tls/h:1") for r in refs)
```

## Runtime State Inventory

> Phase 42 is purely a code/test/docs hardening phase. No rename, no migration, no service registration. The Runtime State Inventory does not apply.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified by reading phase scope (no schema/data shape change). | None |
| Live service config | None — no service or container is touched. | None |
| OS-registered state | None — no daemon, scheduled task, or registered service. | None |
| Secrets/env vars | `REGEN_CBOM_FIXTURES`, `REGEN_CBOM_COVERAGE` (NEW) — local-only test env vars; no secrets. | None |
| Build artifacts | `cyclonedx-python-lib[validation]` requires a `pip install -e .` re-run after `pyproject.toml` is updated. | Plan must include "reinstall in editable mode" verification step. |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `cyclonedx-python-lib` | All four reqs | ✓ | 11.7.0 [VERIFIED] | — |
| `cyclonedx-python-lib[validation]` extra (jsonschema, lxml, referencing) | CBOM-01 | ✗ — extra NOT yet declared | — | None — must be declared in `pyproject.toml`, no other source |
| `pytest` | All test work | ✓ | as-installed | — |
| Python `>=3.10` | Project baseline | ✓ | 3.14.x detected | — |

**Missing dependencies with no fallback:**
- The `cyclonedx-python-lib[validation]` extra. The Phase 42 plan must include a task that updates `pyproject.toml` and reinstalls before any CBOM-01 test can pass.

**Missing dependencies with fallback:** None.

## Validation Architecture

> nyquist_validation is enabled (no explicit `false` in `.planning/config.json`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (config in `pyproject.toml` `[tool.pytest.ini_options]`) [VERIFIED] |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/test_cbom_*.py -x` |
| Full suite command | `pytest` (excludes `slow` by default per `addopts = "-m 'not slow'"`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CBOM-01 | Per-profile JSON+XML validates against CycloneDX 1.6 strict schema | unit (no-network, no-Docker) | `pytest tests/test_cbom_schema_validation.py -x` | ❌ Wave 0 — new file |
| CBOM-02a | No `UNKNOWN` classification for any algorithm surfaced by any profile (gate) | unit | `pytest tests/test_cbom_classifier_coverage.py::test_no_unknown_classifications_across_lab_profiles -x` | ❌ Wave 0 — new file |
| CBOM-02b | `docs/cbom-classifier-coverage.md` is regenerable and up-to-date | unit (regen flag) | `REGEN_CBOM_COVERAGE=1 pytest tests/test_cbom_classifier_coverage.py::test_regenerate_coverage_report -s` | ❌ Wave 0 — new file |
| CBOM-03a | Existing motion goldens still match | unit | `pytest tests/test_cbom_motion_golden.py::test_email_cbom_matches_snapshot tests/test_cbom_motion_golden.py::test_broker_cbom_matches_snapshot -x` | ✅ |
| CBOM-03b | New shape goldens (pki / vault-or-database / saml-or-ldaps) match | unit | `pytest tests/test_cbom_motion_golden.py::test_pki_cbom_matches_snapshot tests/test_cbom_motion_golden.py::test_vault_cbom_matches_snapshot tests/test_cbom_motion_golden.py::test_saml_cbom_matches_snapshot -x` | ❌ Wave 0 — new endpoint fns + fixtures |
| CBOM-03c | `tests/fixtures/cbom/CHANGELOG.md` exists and references the commit | manual (file-presence) | `test -f tests/fixtures/cbom/CHANGELOG.md && grep -q 'Phase 42' tests/fixtures/cbom/CHANGELOG.md` | ❌ Wave 0 — new file |
| CBOM-04a | Each label in `MOTION_PLAINTEXT_PROTOCOLS` is skipped at Pass 2 + Pass 3 | unit (parametrized) | `pytest tests/test_cbom_skip_lists.py -x` | ❌ Wave 0 — new file |
| CBOM-04b | Each label in `DAR_SKIP_PROTOCOLS` is skipped at Pass 2 + Pass 3 | unit (parametrized) | same as above | ❌ Wave 0 — new file |

### Sampling Rate
- **Per task commit:** `pytest tests/test_cbom_*.py -x`
- **Per wave merge:** `pytest` (full suite, excludes `slow`)
- **Phase gate:** `pytest` green AND `REGEN_CBOM_COVERAGE=1 pytest tests/test_cbom_classifier_coverage.py::test_regenerate_coverage_report -s` produces no diff in `docs/cbom-classifier-coverage.md` before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `pyproject.toml` — change `cyclonedx-python-lib>=11.7.0,<12` → `cyclonedx-python-lib[validation]>=11.7.0,<12` and reinstall (`pip install -e .`) — blocks CBOM-01.
- [ ] `tests/test_cbom_schema_validation.py` — new file, covers CBOM-01.
- [ ] `tests/test_cbom_classifier_coverage.py` — new file, covers CBOM-02.
- [ ] `tests/test_cbom_skip_lists.py` — new file, covers CBOM-04.
- [ ] Endpoint synthesizers `_build_pki_lab_endpoints`, `_build_vault_lab_endpoints` (or `_build_database_lab_endpoints`), `_build_saml_lab_endpoints` (or `_build_ldaps_lab_endpoints`) — new in `tests/test_cbom_motion_endpoints.py` (extend, don't replace), then referenced from `test_cbom_motion_golden.py`.
- [ ] `tests/fixtures/cbom/expected_pki_cbom.json`, `expected_vault_cbom.json` (or `_database_`), `expected_saml_cbom.json` (or `_ldaps_`) — generated via `REGEN_CBOM_FIXTURES=1`.
- [ ] `tests/fixtures/cbom/CHANGELOG.md` — new file (D-09).
- [ ] `docs/cbom-classifier-coverage.md` — new generated artifact (D-05).
- [ ] `quirk/cbom/builder.py` — extract `MOTION_PLAINTEXT_PROTOCOLS` and `DAR_SKIP_PROTOCOLS` module-level constants, replace literal tuples at lines 436-440 and 519-523.

## Project Constraints (from CLAUDE.md)

| Directive | Source | Impact on Phase 42 |
|-----------|--------|---------------------|
| PEP 8; minimal diffs; run `python -m compileall` and tests after changes | CLAUDE.md "Code Standards" | All new test files + builder edit must pass compileall and pytest. |
| Chaos Lab Maintenance — any profile/port/service change must update `lab.sh` ALL_PROFILES + chaos lab `README.md` + `expected_results_*.md` | CLAUDE.md "Chaos Lab Maintenance" | Phase 42 does NOT change the chaos lab. Verify no compose changes leak in. |
| Mandatory Phase Completion Steps: Obsidian phase note + UAT-SERIES.md update + sync to vault + commit | CLAUDE.md "Mandatory Phase Completion Steps" | Phase 42 plan must include a wave/task for: (1) write `Phase-42-CBOM-Correctness-Audit.md` to vault filesystem, (2) update `docs/UAT-SERIES.md` if a new test series row is needed, (3) sync UAT-SERIES.md to vault, (4) commit. |
| Vault frontmatter standards (project, type, status, source, updated) | CLAUDE.md "Frontmatter Standards" | Obsidian note must use the standard frontmatter block. |

## Security Domain

> `security_enforcement` not explicitly false in config — section included for completeness.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (test-only phase, no auth surface) |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (indirect) | The CBOM-01 schema gate **is** input/output validation: it asserts QU.I.R.K.'s output conforms to a published spec. |
| V6 Cryptography | yes (indirect) | CBOM-02 ensures every cryptographic algorithm name is correctly classified — directly material to QU.I.R.K.'s consulting deliverable. |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| CBOM consumer rejects malformed output | Repudiation (we ship invalid CBOMs) | Strict schema validation in CI (CBOM-01). |
| Misclassified algorithm in deliverable (e.g., RSA labeled quantum-safe) | Tampering / Information Disclosure | Coverage gate (CBOM-02) + curated golden snapshots (CBOM-03). |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Online schema fetch / vendor JSON Schemas in repo | `cyclonedx-python-lib[validation]` bundled validators | cyclonedx-python-lib 4.x+ — well-established by 11.7 | Single source of truth, no CI drift. |
| `JsonValidator` (lenient) | `JsonStrictValidator` | Available in current major (11.x) [VERIFIED] | Catches additionalProperties + unknown enum values. |
| Per-profile golden expansion (1:1 with lab profiles) | Curated by output **shape** | Phase 42 (D-07) | Lower maintenance burden; spec validator covers the long tail. |

**Deprecated/outdated:**
- Hand-rolled `XMLSchema(lxml)` calls for CycloneDX XML — replaced by `XmlValidator` from the same lib.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Adding `[validation]` to the existing pin (`cyclonedx-python-lib[validation]>=11.7.0,<12`) does not introduce a transitive conflict with already-declared `lxml>=6.0` | Standard Stack | LOW — extra requires `lxml>=4,<7` which overlaps; should be conflict-free. Verify with `pip install -e .` dry-run. |
| A2 | The 19 profiles in `docker-compose.yml` (verified via grep on 2026-04-30) is the complete shipped set; no out-of-tree compose overlays add profiles | Pitfall #3 | LOW — if a profile is added later, the test parametrization will simply not cover it (graceful). |
| A3 | `pki` profile has the richest TLS cert chain, `vault`/`database` has the most informative DAR fields, `saml` has the richest identity coverage — final picks left to planner per D-07 | Project Structure | LOW — D-07 explicitly grants planner discretion within shape. |

## Open Questions

1. **Profile-set parsing strategy in tests.**
   - What we know: `docker-compose.yml` is the source of truth; `lab.sh` derives profiles dynamically; tests will reference 19 names.
   - What's unclear: hardcode the 19 names in a test constant (simple, can drift) vs. parse `docker-compose.yml` at test time (zero drift, more code).
   - Recommendation: hardcode the 19-name list as a frozenset in the test module, then add ONE sentinel test that parses `docker-compose.yml` and asserts equality. Drift = one failing test that points at the diff. Planner decides.

2. **Database vs Vault for the DAR shape golden.**
   - What we know: D-07 says "vault or database — planner picks the one with the most informative DAR fields."
   - What's unclear: which profile actually surfaces the most DAR-distinct algorithms in `build_cbom()` output.
   - Recommendation: planner should generate a one-shot diagnostic snapshot of both during planning and pick the one with more components in the bom. If they tie, prefer `vault` (fewer external deps in the test fixture).

3. **SAML vs LDAPS for the identity shape golden.**
   - What we know: D-07 says "saml — alternative ldaps if SAML coverage is too thin."
   - What's unclear: SAML scanner emits `cert_pubkey_alg` for the IdP signing cert — but no separate identity-specific bom_ref shape. May be effectively a TLS-with-cert fixture.
   - Recommendation: pick `saml`. If the snapshot turns out structurally identical to `pki`, swap to `ldaps`.

## Sources

### Primary (HIGH confidence)
- `cyclonedx-python-lib` 11.7.0 — local install, methods verified via `inspect.signature` and `importlib.metadata` [VERIFIED]
- `quirk/cbom/builder.py` lines 1–595 — read in full
- `quirk/cbom/classifier.py` lines 1–229 — read in full
- `quirk/cbom/writer.py` lines 1–35 — read in full
- `tests/test_cbom_motion_golden.py` lines 1–384 — read in full
- `tests/test_cbom_motion_endpoints.py` lines 1–306 — read in full
- `tests/test_cbom_classifier.py` lines 1–259 — read in full
- `pyproject.toml` lines 1–82 — read in full
- `quantum-chaos-enterprise-lab/docker-compose.yml` — profile set extracted via grep
- `quantum-chaos-enterprise-lab/lab.sh` lines 14–104 — `_derive_all_profiles` function inspected
- `.planning/phases/42-cbom-correctness-audit/42-CONTEXT.md` — locked decisions D-01..D-12

### Secondary (MEDIUM confidence)
- CycloneDX 1.6 specification — accessed via the bundled `cyclonedx/schema/` files inside the installed wheel (not separately fetched)

### Tertiary (LOW confidence)
- None — every claim in this research was verified against an installed artifact or a file in the repo.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — validators, SchemaVersion enum, return semantics, and optional-extras gap all verified live.
- Architecture: HIGH — code read end-to-end; existing test patterns (`_normalize_bom_for_snapshot`, `REGEN_CBOM_FIXTURES=1`, `_tls_endpoint`) trivially extensible.
- Pitfalls: HIGH — Pitfall #1 (optional extras) reproduced live; #2 (return-not-raise) verified via `inspect.signature`.

**Research date:** 2026-04-30
**Valid until:** 2026-05-30 (30 days — stable lib, stable spec)
