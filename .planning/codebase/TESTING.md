# Testing Patterns

**Analysis Date:** 2026-04-02

## Test Framework

**Runner:**
- pytest (no version pinned in `pyproject.toml`; available in `.venv`)
- No `pytest.ini` or `[tool.pytest]` section in `pyproject.toml` — defaults apply
- Config: none beyond `tests/conftest.py`

**Assertion Library:**
- Mix of `unittest.TestCase` and bare `assert` statements
- New tests use pytest-style bare asserts; older tests use `unittest.TestCase`

**Run Commands:**
```bash
.venv/bin/python -m pytest tests/              # Run all tests
.venv/bin/python -m pytest tests/ -x -q       # Stop on first failure
.venv/bin/python -m pytest tests/ -k name     # Run by keyword match
```

## Test File Organization

**Location:** All tests live in `tests/` at the project root. No co-location with source.

**Naming:** `test_<feature_or_module>.py`

**Examples:**
```
tests/
├── conftest.py                    # Shared fixtures (dashboard_client only)
├── test_cbom_builder.py           # Unit tests for quirk/cbom/builder.py
├── test_cbom_classifier.py
├── test_cbom_integration.py
├── test_cbom_writer.py
├── test_cert_pubkey_fix.py        # Regression tests for field mapping
├── test_cli_init.py
├── test_cli_version.py
├── test_cloud_connectors.py
├── test_container_scanner.py
├── test_dashboard_api.py          # Integration tests against FastAPI TestClient
├── test_dashboard_theme.py
├── test_html_report.py
├── test_intelligence_confidence.py
├── test_intelligence_evidence.py
├── test_intelligence_roadmap.py
├── test_intelligence_schema.py
├── test_intelligence_scoring.py
├── test_jwt_scanner.py
├── test_packaging.py
├── test_pdf_export.py             # Has 1 failing test (HTTP 500 vs expected 503)
├── test_reports_scorecard.py
├── test_rich_output.py
├── test_scoring_consolidation.py  # AST-based guard tests for import boundaries
├── test_source_scanner.py
├── test_ssh_scanner.py
└── test_sslyze_integration.py
```

## Test Structure

**Pytest-style (new code):**
```python
# tests/test_jwt_scanner.py — typical scanner test
def test_multi_key_jwks():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_JWKS

    with patch("quirk.scanner.jwt_scanner.httpx") as mock_httpx:
        mock_httpx.get.return_value = mock_response
        endpoints = scan_jwt_endpoint("https://api.example.com", timeout=5)
        assert len(endpoints) == 3
        for ep in endpoints:
            assert ep.protocol == "JWT"
```

**unittest.TestCase style (legacy pattern, still in use):**
```python
# tests/test_intelligence_scoring.py
class ReadinessScoringTests(unittest.TestCase):
    def test_compute_readiness_score_shape(self) -> None:
        result = compute_readiness_score(_base_evidence())
        self.assertIn("score", result)
        self.assertIn("rating", result)
```

**Mixed style in same file:** Some test files use class-based organization (`class TestSslyzeAvailableSuccess:`) without inheriting from `unittest.TestCase`, using bare assert statements. This is valid pytest.

## Shared Fixtures

**`tests/conftest.py` defines one fixture:**
```python
@pytest.fixture
def dashboard_client():
    """FastAPI TestClient with an in-memory SQLite database.
    Overrides get_db dependency for isolation.
    """
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
```
Uses `sqlite:///file::memory:?cache=shared&uri=true` so sync route handlers and test threads share the same connection. Fixture skips automatically if `quirk.dashboard` is not importable.

## Mocking

**Framework:** `unittest.mock` — `patch`, `MagicMock`, `patch.dict`, `patch.object`

**Standard patterns:**

Patching an HTTP client at the module level:
```python
with patch("quirk.scanner.jwt_scanner.httpx") as mock_httpx:
    mock_httpx.get.return_value = mock_response
    result = scan_jwt_endpoint(url, timeout=5)
```

Patching subprocess for external tools (ssh-audit, semgrep):
```python
mock_proc = MagicMock()
mock_proc.stdout = json.dumps(SAMPLE_OUTPUT)
mock_proc.returncode = 0
with patch("shutil.which", return_value="/usr/bin/semgrep"), \
     patch("subprocess.run", return_value=mock_proc):
    endpoints = scan_source_repo("/path/to/repo", timeout=120)
```

Injecting fake optional dependency (sslyze) via `sys.modules`:
```python
# tests/test_sslyze_integration.py — build a complete fake module tree
sslyze_mod = ModuleType("sslyze")
sslyze_mod.Scanner = MagicMock()
with patch.dict(sys.modules, {"sslyze": sslyze_mod}):
    import quirk.scanner.tls_scanner as tls_mod
    importlib.reload(tls_mod)
    tls_mod.SSLYZE_AVAILABLE = True
    ep = tls_mod._scan_one_sslyze("example.com", 443, 10, True, None)
```

FastAPI dependency override (via conftest fixture, not inline):
```python
app.dependency_overrides[get_db] = override_get_db
```

**What to Mock:**
- External network calls (`httpx.get`, `socket.create_connection`, `ssl.SSLContext.wrap_socket`)
- External binary calls (`subprocess.run` for ssh-audit, semgrep)
- Optional third-party libraries (`sslyze`, `playwright`)
- Database via SQLAlchemy session override (not mocked at the ORM level)

**What NOT to Mock:**
- The `quirk.models.CryptoEndpoint` ORM class — tests construct real instances
- Internal scoring/evidence functions — unit-tested directly with fixture data
- The SQLAlchemy `Base` — tests use real schema creation against in-memory SQLite

## Fixtures and Factories

**Duck-typed test endpoints:** Many tests define a local `@dataclass` stub or `SimpleNamespace` as a lightweight `CryptoEndpoint` substitute:
```python
# tests/test_intelligence_evidence.py
@dataclass
class _Ep:
    host: str
    port: int
    protocol: str
    scanned_at: datetime | None = None
    scan_error: str | None = None
    tls_blocker_reason: str | None = None
    cert_pubkey_alg: str | None = None
    cert_not_after: datetime | None = None
    cert_subject: str | None = None
    cert_issuer: str | None = None
```

**Evidence dict fixtures** (intelligence tests):
```python
def _base_evidence() -> dict:
    return {
        "totals": {"endpoints": 10, "findings": 4},
        "protocol_counts": {"TLS": 6, "HTTP": 2, "SSH": 1, "UNKNOWN": 1},
        "scan_error": {"count": 1, "rate": 0.1},
        "tls_enum_coverage_ratio": 1.0,
        ...
    }
```

**Helper factories in test files (not in conftest):**
- `tests/test_sslyze_integration.py`: `_make_mock_cert()`, `_make_sslyze_mock_modules()`, `_make_mock_cipher_suite()`
- `tests/test_cbom_builder.py`: `_tls_endpoint(**overrides)`, `_ssh_endpoint(**overrides)`
- `tests/test_ssh_scanner.py`: `_make_cfg(concurrency, timeout)` — minimal `SimpleNamespace` config

## Coverage

**Requirements:** None enforced. No coverage threshold in `pyproject.toml`.

**Current test count:** 165 tests collected.
**Current pass rate:** 164/165 (one failing: `tests/test_pdf_export.py::test_pdf_export_endpoint` — see Concerns doc).

## Test Types

**Unit Tests:**
- Intelligence pipeline (`test_intelligence_*.py`) — pure function tests, no I/O
- Scanner unit tests (`test_jwt_scanner.py`, `test_ssh_scanner.py`, `test_source_scanner.py`) — mocked subprocess/httpx
- CBOM pipeline (`test_cbom_*.py`) — real CycloneDX library, fake endpoints
- Import guard tests (`test_scoring_consolidation.py`) — AST parsing to enforce import constraints

**Integration Tests:**
- `test_dashboard_api.py` — full FastAPI route tests against in-memory SQLite
- `test_sslyze_integration.py` — fake sslyze module injection via `sys.modules`

**E2E Tests:** Not present. The `test_pdf_export.py` tests use the TestClient but require an actual Playwright/Chromium installation to fully pass — they are effectively integration tests for an optional external dependency.

## Common Patterns

**Async Testing:** Not used. The dashboard API uses synchronous FastAPI route handlers (no `async def`); tests use `TestClient` which is synchronous.

**Error path testing:**
```python
def test_semgrep_not_found():
    """If semgrep binary is absent, must return empty list."""
    with patch("shutil.which", return_value=None):
        endpoints = scan_source_repo("/path/to/repo", timeout=120)
        assert endpoints == []
```

**Determinism tests** (intelligence layer):
```python
def test_output_is_deterministic(self) -> None:
    evidence = _base_evidence()
    a = compute_readiness_score(evidence)
    b = compute_readiness_score(evidence)
    self.assertEqual(a, b)
```

**Comparative scoring tests** (verify direction of impact):
```python
def test_risky_evidence_scores_lower(self) -> None:
    safe_score = compute_readiness_score(safe)["score"]
    risky_score = compute_readiness_score(risky)["score"]
    self.assertLess(risky_score, safe_score)
```

**AST-based constraint tests** (`tests/test_scoring_consolidation.py`):
```python
# Enforce that writer.py does NOT import legacy scoring modules
def test_no_assessment_readiness_import(self) -> None:
    for module, names in self.imports:
        self.assertNotEqual(module, "quirk.assessment.readiness_score", ...)
```

## Coverage Gaps

**`quirk/assessment/` modules — largely untested:**
- `quirk/assessment/readiness_score.py` — `compute_readiness_score(cfg, endpoints, findings)` has no dedicated test suite
- `quirk/assessment/confidence.py` — `compute_confidence(cfg, endpoints)` has no dedicated test suite
- `quirk/assessment/transition_planner.py` — `build_transition_roadmap()` has no dedicated test suite
- `quirk/assessment/migration_advisor.py` — `recommend_migration_paths()` has no dedicated test suite
- `quirk/assessment/interpretation_engine.py` — `build_interpretation()` has no dedicated test suite
- These modules are called by `quirk/reports/executive.py` which is also untested; `executive.py` imports from the legacy `quirk.assessment.*` path that `test_scoring_consolidation.py` forbids in `writer.py` — this inconsistency is unresolved

**`quirk/discovery/` — legacy tls_scanner untested:**
- `quirk/discovery/tls_scanner.py` has a `scan_one()` function with identical logic to `quirk/scanner/tls_scanner.py`'s fallback — no tests exist for the discovery-layer copy
- `quirk/discovery/coverage.py` `quantum_readiness_score()` is an old scoring stub — no tests, likely dead

**`quirk/engine/` — partial coverage:**
- `quirk/engine/rules.py` — not examined but no test file exists for it
- `quirk/engine/cache.py` — no test file
- `quirk/engine/rate_limiter.py` — no test file
- `quirk/engine/profiles.py` — no test file for `apply_profile()`

**`quirk/validate.py` — untested:**
- `validate_run()` and `_validate_intelligence()` contain logic that checks for `assessment-{stamp}.json`, `calibration-{stamp}.json`, and `delta-{stamp}.json` — artifacts that `writer.py` does not currently produce (the validate module's expected artifact list is out of sync with `write_reports()`)

**`quirk/reports/executive.py` — untested:**
- Calls legacy `quirk.assessment.*` scoring functions (the path that `test_scoring_consolidation.py` guards against in `writer.py`); the same restriction has not been applied to `executive.py`

**PDF export test is broken:**
- `tests/test_pdf_export.py::test_pdf_export_endpoint` fails with HTTP 500 when Playwright is installed but Chromium cannot connect to the test server (no server is running in the test environment). The test asserts `status_code in (200, 503)` but receives 500. The route's exception handler does not classify connection-refused errors as 503.

---

*Testing analysis: 2026-04-02*
