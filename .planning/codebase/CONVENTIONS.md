# Coding Conventions

**Analysis Date:** 2026-04-02

## Naming Patterns

**Files:**
- Module names: `snake_case.py` throughout (`tls_scanner.py`, `risk_engine.py`, `logging_util.py`)
- Test files: `test_<module_or_feature>.py` in `tests/` directory
- Template files: `*.j2` suffix under `quirk/reports/templates/`
- Config template: `quirk/config_template.yaml`

**Functions:**
- Public functions: `snake_case` (`compute_readiness_score`, `build_evidence_summary`, `scan_tls_targets`)
- Private helpers: leading underscore `_snake_case` (`_pubkey_info`, `_extract_sans`, `_dedupe_findings`)
- Predicate helpers: `_is_<condition>` pattern (`_is_pfs`, _is_weak`, `_is_legacy_suite`, `_is_legacy_cipher`)
- Extraction helpers: `_extract_<thing>` pattern (`_extract_cert_key_type`, `_extract_cert_dates`, `_extract_ssh_algorithms`)

**Variables:**
- `snake_case` throughout; boolean flags prefixed with verb (`pfs_supported`, `weak_present`, `chain_verified`)
- Module-level constants: `UPPER_SNAKE_CASE` (`SCORE_WEIGHTS`, `SSLYZE_AVAILABLE`, `PLATFORM_VERSION`, `SCHEMA_VERSION`)

**Classes:**
- `PascalCase` for all classes (`CryptoEndpoint`, `AppConfig`, `ScoreBreakdown`, `ReadinessScore`, `IntelligenceReport`)
- Dataclasses use `PascalCase` with `Cfg` suffix for config (`ScanCfg`, `AssessmentCfg`, `ConnectorsCfg`)
- Pydantic models (API layer only) follow the same `PascalCase` convention (`FindingItem`, `ScoreData`, `ScanLatestResponse`)

**Inconsistency — Legacy vs New Naming:**
- `quirk/assessment/` modules still use verb-noun naming for their score functions:
  `compute_readiness_score(cfg, endpoints, findings)` — takes 3 positional args, returns `ReadinessScore` dataclass
- `quirk/intelligence/scoring.py` uses the same function name `compute_readiness_score` but takes a single `evidence` dict, returns a plain `Dict[str, Any]`
- `quirk/assessment/confidence.py` defines `compute_confidence(cfg, endpoints)` — legacy 2-arg form
- `quirk/intelligence/confidence.py` defines `compute_confidence(evidence)` — new 1-arg evidence form
- The canonical versions are in `quirk/intelligence/`. The `quirk/assessment/` equivalents are legacy code still used by `quirk/reports/executive.py`

## Data Modeling Patterns

Three coexisting approaches across the codebase — choose based on location:

**1. SQLAlchemy ORM — data layer only**
- `quirk/models.py`: `CryptoEndpoint` is the single ORM model for all scan results
- Backed by SQLite; columns versioned in-line with `# v3.6`, `# v4.0` comments
- Do not add runtime logic here; use `getattr(ep, field, default)` when consuming endpoints in engine/intelligence code to handle both real ORM objects and duck-typed fakes from tests

**2. `@dataclass` — config and internal result structs**
- `quirk/config.py`: all config structs are plain `@dataclass` (`ScanCfg`, `AppConfig`, etc.)
- `quirk/assessment/readiness_score.py`: `ScoreBreakdown`, `ReadinessScore` are `@dataclass` with `to_dict()` methods
- `quirk/assessment/transition_planner.py`: `RoadmapItem`, `TransitionRoadmap` are `@dataclass`
- `quirk/intelligence/schema.py`: `@dataclass(frozen=True, slots=True)` for immutable schema objects (`ScoreInputs`, `ScoreResult`, `IntelligenceReport`)
- `quirk/validate.py`: `ValidationResult` is a plain `@dataclass`
- Rule: prefer `@dataclass` for internal logic structs; use `frozen=True, slots=True` for objects that cross module boundaries as stable contracts

**3. `pydantic.BaseModel` — API boundary only**
- `quirk/dashboard/api/schemas.py` exclusively; never use Pydantic in scanner, engine, or intelligence modules
- Pydantic models define the FastAPI response contract; TypeScript types in `src/dashboard/src/types/api.ts` must mirror them exactly

**4. Plain `Dict[str, Any]` — intelligence pipeline**
- `quirk/intelligence/evidence.py` `build_evidence_summary()` returns a plain dict (the "evidence envelope")
- `quirk/intelligence/scoring.py` `compute_readiness_score(evidence)` consumes and returns plain dicts
- `quirk/intelligence/confidence.py` `compute_confidence(evidence)` same pattern
- `quirk/intelligence/roadmap.py` `build_phased_roadmap(evidence, scoring)` same
- This is intentional: the intelligence pipeline is purely functional, dict-in/dict-out, no class instantiation

## Import Organization

**Order (per PEP 8, consistently applied in new code):**
1. `from __future__ import annotations`
2. Standard library (`json`, `os`, `datetime`, `typing`, etc.)
3. Third-party (`sqlalchemy`, `fastapi`, `rich`, `cyclonedx`, `cryptography`)
4. Internal `quirk.*` imports

**Path Aliases:** None. All imports use full dotted paths (`from quirk.models import CryptoEndpoint`).

**`from __future__ import annotations`:** Present in newer modules (`intelligence/`, `cbom/`, `dashboard/`); absent in older scanner and assessment modules. Add it to new files.

## Error Handling

**Strategy: Return sentinel values, not exceptions.**

In scanner code, exceptions are caught broadly and stored in the `scan_error` field of `CryptoEndpoint`:
```python
# quirk/scanner/tls_scanner.py — standard pattern
except Exception as e:
    cat = _categorize_tls_error(e)
    ep.tls_blocker_reason = cat
    ep.scan_error = f"{cat}: {e}"
```

Error categories are UPPER_SNAKE_CASE strings: `CONNECTION_REFUSED`, `TIMEOUT`, `NOT_TLS_ON_PORT`, `MTLS_REQUIRED`, `TLS_HANDSHAKE_FAILED`, `CERT_VERIFY_FAILED`, `RESET_BY_PEER`, `TLS_ERROR`.

Consumers parse the category prefix from `scan_error` via `str.split(":", 1)[0]`.

**For optional dependencies (sslyze, Playwright, semgrep, ssh-audit):**
- Wrap `import` in `try/except ImportError`; set a module-level `AVAILABLE` flag (`SSLYZE_AVAILABLE`)
- Return `None` or empty list to trigger fallback; never raise to caller

**Legacy inconsistency in `quirk/assessment/confidence.py`:**
- The legacy `compute_confidence(cfg, endpoints)` uses a try/except heuristic score pattern inline
- The new `quirk/intelligence/confidence.py` uses pure evidence dict math — no exceptions
- In `quirk/reports/executive.py`, `compute_confidence` is called with `(cfg, endpoints)` (legacy signature); `writer.py` correctly calls the new form `compute_confidence(evidence)`

**FastAPI routes:**
- Raise `HTTPException` directly from route handlers
- Non-Playwright errors in `quirk/dashboard/api/routes/pdf.py` that are not chromium-related fall through to HTTP 500 (a known bug — the test `test_pdf_export_endpoint` fails because the test environment triggers a 500 rather than 503)

## Logging

**Framework:** Custom `Logger` class in `quirk/logging_util.py`. No stdlib `logging` module is used.

**Usage:**
```python
from quirk.logging_util import Logger
logger = Logger(verbose=True, use_tqdm=False)
logger.info("Always-visible message")
logger.v("Verbose-only debug message")     # gated by logger.verbose
logger.stamp("Timestamped progress event") # prepends [HH:MM:SSZ]
```

**Threading:** `Logger._write()` uses a module-level `threading.Lock` (`_PRINT_LOCK`) for thread-safe output during concurrent scans.

**Pattern:** Pass `logger` as an optional argument (`Optional[Logger] = None`) to scanner functions; guard all calls with `if logger:`.

## Comments and Docstrings

**Module docstrings:** Present in newer files (`cbom/builder.py`, `dashboard/api/schemas.py`, `validate.py`). Missing in most scanner and assessment modules.

**Inline version comments:** Legacy fields in `quirk/models.py` are annotated with version comments (`# v3.6 TLS capability fields`, `# v4.0 SSH audit fields`). Do not add new version comments; add docstrings to new fields instead.

**Stale/misleading comments:**
- `quirk/cbom/builder.py` line 76: `PLATFORM_VERSION = "3.9"` with comment "duplicated here to avoid circular imports" — the actual platform version in `writer.py` is `"4.0"`. These are out of sync.
- `quirk/assessment/migration_advisor.py` docstring says "v3.5 layer" — the module is still active in the pipeline through `executive.py`, but the version reference is stale
- `quirk/engine/risk_engine.py` has a comment `# v3.7.1 classifier patch companion` on `_postprocess_findings` — version references in comments should be removed and replaced with intent descriptions

**Function parameter annotations:** All new code in `quirk/intelligence/` uses full type annotations. Legacy assessment and scanner code uses `Any` for cfg/endpoints parameters rather than the actual types, reflecting duck-typed origins.

## Module Design

**Exports and `__init__.py`:**
- `quirk/cbom/__init__.py` re-exports `build_cbom` and `write_cbom_files` for convenience
- Most `__init__.py` files are empty stubs
- Do not add star-imports; import from the specific submodule

**Config consumption pattern:**
- Scanner functions take the whole `cfg` object and access `cfg.scan.*` attributes
- Use `getattr(cfg.scan, field, default)` rather than direct attribute access when the field might be from legacy config
- The `quirk/engine/profiles.py` `apply_profile()` uses `getattr/setattr` throughout to safely mutate config fields that may be `None`

---

*Convention analysis: 2026-04-02*
