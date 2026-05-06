---
phase: 42-cbom-correctness-audit
plan: 01
subsystem: cbom
tags: [cbom, cyclonedx, dependencies, refactor]
requires: []
provides:
  - "MOTION_PLAINTEXT_PROTOCOLS frozenset (importable from quirk.cbom.builder)"
  - "DAR_SKIP_PROTOCOLS frozenset (importable from quirk.cbom.builder)"
  - "cyclonedx-python-lib[validation] extras pinned (JsonStrictValidator + XmlValidator import-clean)"
affects:
  - pyproject.toml
  - quirk/cbom/builder.py
tech-stack:
  added:
    - "cyclonedx-python-lib[validation] (jsonschema, lxml, referencing transitively)"
  patterns:
    - "Module-level frozenset constants exposed for test parametrization (mirrors classifier.py _ALGORITHM_TABLE pattern)"
key-files:
  modified:
    - pyproject.toml
    - quirk/cbom/builder.py
decisions:
  - "Adopted the [validation] umbrella extra over hand-pinned deps (D-01) — single source of truth tied to the library version"
  - "Preserved Pass 3 inline AWS / AZURE entries (NOT in DAR_SKIP_PROTOCOLS) — refactor faithfully reproduces original membership"
metrics:
  duration_seconds: 105
  completed: 2026-04-30
status: complete
---

# Phase 42 Plan 01: Wave 0 Prerequisite — Validation Extras + Skip-List Constants Summary

Pinned `cyclonedx-python-lib[validation]>=11.7.0,<12` so `JsonStrictValidator`/`XmlValidator`
import without `MissingOptionalDependencyException`, and extracted `MOTION_PLAINTEXT_PROTOCOLS`
+ `DAR_SKIP_PROTOCOLS` as module-level frozensets in `quirk/cbom/builder.py` so Wave 1 unit
tests can parametrize off the source of truth.

## What Was Built

### Task 1 — pyproject.toml: validation extras pin

One-line dependency change:

```diff
-    "cyclonedx-python-lib>=11.7.0,<12",
+    "cyclonedx-python-lib[validation]>=11.7.0,<12",
```

Reinstall: `.venv/bin/pip install -e .` succeeded. Transitively installed `jsonschema-4.26.0`,
`referencing-0.37.0`, plus the validator's other deps (`arrow`, `attrs`, `fqdn`,
`isoduration`, `jsonpointer`, `jsonschema-specifications`, `lark`, `rfc3339-validator`,
`rfc3986-validator`, `rfc3987-syntax`, `rpds-py`, `tzdata`, `uri-template`, `webcolors`).

Sanity-check imports:

```
from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonStrictValidator
from cyclonedx.validation.xml import XmlValidator
v = JsonStrictValidator(SchemaVersion.V1_6)
v.validate_str('{"bomFormat":"CycloneDX","specVersion":"1.6","version":1}')  # → None (valid)
```

All clean — no `MissingOptionalDependencyException`. Commit: `1077d7c`.

### Task 2 — quirk/cbom/builder.py: extract skip-list constants

Added module-level frozensets after imports (per D-10 / D-11):

```python
MOTION_PLAINTEXT_PROTOCOLS: frozenset[str] = frozenset({
    "KAFKA-PLAIN", "AMQP-PLAIN", "REDIS-PLAIN",
})

DAR_SKIP_PROTOCOLS: frozenset[str] = frozenset({
    "POSTGRESQL", "MYSQL", "RDS",
    "S3", "AZURE_BLOB",
    "KUBERNETES", "VAULT",
    "GCP", "CLOUD_SQL",
})
```

Refactored Pass 2 (cert components) and Pass 3 (protocol components) skip-tuple
literals to splat the new constants:

- Pass 2 (line ~436): `"SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC", *DAR_SKIP_PROTOCOLS, *MOTION_PLAINTEXT_PROTOCOLS`
- Pass 3 (line ~519): `"JWT", "CONTAINER", "SOURCE", "AWS", "AZURE", "DNSSEC", "SAML", "KERBEROS", *DAR_SKIP_PROTOCOLS, *MOTION_PLAINTEXT_PROTOCOLS`

`AWS` + `AZURE` remain inline in Pass 3 (NOT in either constant — the plan's refactor
faithfully preserves this).

## Behavior Preservation

Set-equality verified pre/post for both passes (programmatic check before running tests):

| Pass | Original size | New size | Symmetric diff |
|------|--------------:|---------:|----------------|
| Pass 2 | 18 | 18 | ∅ |
| Pass 3 | 20 | 20 | ∅ |

Regression tests (the safety net for this refactor):

```
.venv/bin/python -m pytest tests/test_cbom_builder.py tests/test_cbom_motion_endpoints.py tests/test_cbom_motion_golden.py -x
→ 57 passed, 1 deselected
```

Broader cbom slice (verification block):

```
.venv/bin/python -m pytest tests/test_cbom_*.py -x
→ 101 passed, 1 deselected
.venv/bin/python -m compileall quirk/cbom/  → exit 0
```

`test_email_cbom_matches_snapshot` and `test_broker_cbom_matches_snapshot` (the
behavior-preservation oracles called out in the plan) both pass — no snapshot drift.

Commit: `a7c6dbe`.

## Deviations from Plan

None — plan executed exactly as written. The only environmental wrinkle was that the
system `pip` is rooted at Python 3.9.6 (which fails the `>=3.10` requires-python guard),
so the install was run via `.venv/bin/pip` (Python 3.14.4) — the project's existing
virtualenv. This is the standard project install path, not a deviation from the plan.

## Self-Check: PASSED

- `pyproject.toml` contains `cyclonedx-python-lib[validation]>=11.7.0,<12` — FOUND
- `quirk/cbom/builder.py` defines `MOTION_PLAINTEXT_PROTOCOLS` and `DAR_SKIP_PROTOCOLS` — FOUND
- Commit `1077d7c` (Task 1) — FOUND
- Commit `a7c6dbe` (Task 2) — FOUND
- 57/57 regression tests + 101/101 cbom slice pass — VERIFIED
- `JsonStrictValidator(SchemaVersion.V1_6).validate_str(...)` returns `None` on valid input — VERIFIED
