"""Shared fixtures for dashboard test suite."""
import os
import tempfile

import pytest

# ---------------------------------------------------------------------------
# CLEAN-03 D-03a: Collection-time QUIRK_DB_PATH isolation
#
# quirk/dashboard/api/app.py has a module-level `app = create_app()` call that
# triggers _default_db_path() in quirk/dashboard/api/deps.py during pytest
# collection (before any fixture can run). When multiple stale *.db files exist
# in the working tree, _default_db_path() raises ValueError("Multiple QU.I.R.K.
# DBs found"), causing 7 test modules to fail collection.
#
# Setting QUIRK_DB_PATH at conftest.py import time (before test modules are
# collected) side-steps the resolver entirely. The autouse fixture below then
# isolates each test to its own tmp_path DB so no test can pollute another.
# ---------------------------------------------------------------------------
if not os.environ.get("QUIRK_DB_PATH"):
    _CONFTEST_TMP_DIR = tempfile.mkdtemp(prefix="quirk_conftest_")
    os.environ["QUIRK_DB_PATH"] = os.path.join(_CONFTEST_TMP_DIR, "quirk_collection.db")


@pytest.fixture(autouse=True)
def _isolate_quirk_db(tmp_path, monkeypatch):
    """CLEAN-03 D-03a: Point QUIRK_DB_PATH at an isolated tmp_path DB.

    Prevents _default_db_path() in quirk/dashboard/api/deps.py from raising
    'Multiple QU.I.R.K. DBs found' when stale scan DBs exist in the working tree.
    Applies to ALL tests automatically; does not affect tests that mock get_db
    via FastAPI dependency injection (e.g. dashboard_client()), which bypass
    _default_db_path() entirely.
    """
    monkeypatch.setenv("QUIRK_DB_PATH", str(tmp_path / "quirk_test.db"))


# ---------------------------------------------------------------------------
# SHA1 signing compatibility shim (Rule 1 auto-fix)
#
# cryptography >=45.x (and 46.x) with OpenSSL 3.x blocks SHA1 for certificate
# signing at the Rust binding level. The vault connector tests use
# _make_test_pem_rsa(key_size, "SHA1") to generate test PKI certificates.
# This shim patches CertificateBuilder.sign to delegate to the `openssl` binary
# for SHA1-signed certificates so the test contract can be executed without
# modifying the locked test file.
# ---------------------------------------------------------------------------

def _patch_sha1_signing():
    """Return True if patching succeeded, False if openssl binary is absent.

    Phase 166 GATE-03 (166-05): this shim's `subprocess.run(["openssl", ...])`
    call was the cause of a fatal SIGSEGV in test_vault_connector.py's
    full-suite run -- discovered by 166-05's mandatory full unfiltered proof
    run even though this file was outside the plan's declared nine-file
    scope. Two conditions were required together (see
    .planning/phases/164-first-run-correctness/164-FINDING-fork-crash.md and
    tests/cli_helpers.py::run_fork_safe's docstring): close_fds=False + no
    cwd, AND (discovered here) argv[0] must contain a path separator --
    a bare "openssl" resolved via PATH defeats CPython's posix_spawn
    eligibility check (`os.path.dirname(executable)` must be truthy) exactly
    like the bare "git" case test_verify_phase_gates.py hit. Routed through
    tests.cli_helpers.run_fork_safe, which enforces both.
    """
    try:
        import shutil
        import tempfile
        import os
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        from tests.cli_helpers import run_fork_safe

        _openssl = shutil.which("openssl")
        if _openssl is None:
            return False

        _original_sign = x509.CertificateBuilder.sign

        def _patched_sign(self, private_key, algorithm, backend=None, **kwargs):
            # Only intercept SHA1 (UnsupportedAlgorithm on OpenSSL 3.x).
            if not isinstance(algorithm, hashes.SHA1):
                return _original_sign(self, private_key, algorithm, backend=backend, **kwargs)

            # Write private key and use openssl req to produce a SHA1-signed cert.
            with tempfile.TemporaryDirectory() as tmpdir:
                key_path = os.path.join(tmpdir, "key.pem")
                cert_path = os.path.join(tmpdir, "cert.pem")

                key_pem = private_key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.TraditionalOpenSSL,
                    serialization.NoEncryption(),
                )
                with open(key_path, "wb") as fh:
                    fh.write(key_pem)

                subj = "/CN=quirk-test-sha1-ca"
                result = run_fork_safe(
                    [
                        _openssl, "req", "-new", "-x509", "-sha1",
                        "-key", key_path, "-out", cert_path,
                        "-days", "365", "-subj", subj,
                    ],
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"openssl SHA1 cert failed: {result.stderr}"
                    )

                with open(cert_path, "rb") as fh:
                    cert_pem = fh.read()

            return x509.load_pem_x509_certificate(cert_pem)

        x509.CertificateBuilder.sign = _patched_sign
        return True
    except Exception:
        return False


# Apply patch at import time (before any test module is collected).
_patch_sha1_signing()


def make_isolated_memory_engine():
    """RVW-017: build an in-memory SQLite engine that is private to one test.

    The repo-wide idiom used to be ``sqlite:///file::memory:?cache=shared&uri=true``.
    That URI names SQLite's *anonymous* shared-cache database, of which there is
    exactly one per process — so 16 test files were not each getting "a shared
    in-memory DB", they were all getting **the same one**. Rows written by one
    file were visible to every other, which is why
    ``test_schedules_api.py::test_get_schedules_empty`` failed in CI whenever
    ``test_otics_cadence_floor.py`` ran first, and why three tests sit skipped in
    ``skip_registry.py`` under "shared in-memory SQLite cache pollution".

    ``file:<uuid>?mode=memory&cache=shared`` keeps the property those tests
    actually needed — shared-cache, so FastAPI's sync-route worker thread sees
    the same data — while giving each caller its own database.

    ``StaticPool`` is required, not cosmetic: a *named* in-memory database is
    destroyed when its last connection closes, so without a pool that holds one
    open, the schema can evaporate between requests.

    Callers own the engine and should ``engine.dispose()`` when done.
    """
    import uuid

    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    from quirk.models import Base

    engine = create_engine(
        f"sqlite:///file:quirk_test_{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def dashboard_client():
    """FastAPI TestClient for the dashboard app with a per-test in-memory database.

    RVW-017: each test gets its OWN database. This fixture previously used
    ``file::memory:?cache=shared`` — SQLite's *anonymous* shared-cache database,
    of which there is exactly one per process. Every connection naming that URI
    joins the same database, which is what let FastAPI's worker thread see the
    tables, and equally what let 31 test files write into each other's state.
    ``test_get_schedules_empty`` failed in full-suite runs because
    ``test_otics_cadence_floor.py`` had already written schedule rows into the
    one shared database. The old docstring's claim of "a fresh in-memory SQLite
    DB" was simply untrue.

    Three properties make isolation real here:

    * **A unique database name per test.** ``file:<uuid>?mode=memory&cache=shared``
      keeps shared-cache semantics — so the worker thread FastAPI uses for sync
      route handlers still sees the same data — while giving each test its own
      database rather than joining the process-wide one.
    * **StaticPool.** A *named* in-memory database is destroyed the moment its
      last connection closes. StaticPool holds one connection for the engine's
      lifetime, so the schema cannot evaporate between requests.
    * **Teardown.** The fixture now yields rather than returns, closing the
      client and disposing the engine. Without this, ~31 in-memory databases
      would accumulate for the length of the run.

    A test that needs to seed rows directly must use ``client.quirk_engine``
    rather than rebuilding a URI — with per-test names there is no longer a
    well-known URI to reconstruct, which is the point.
    """
    try:
        from sqlalchemy.orm import sessionmaker
        from quirk.dashboard.api.app import create_app
        from quirk.dashboard.api.deps import get_db
        from fastapi.testclient import TestClient

        engine = make_isolated_memory_engine()
        TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        def override_get_db():
            db = TestingSession()
            try:
                yield db
            finally:
                db.close()

        app = create_app()
        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app, headers={"X-Quirk-Request": "1"})
        # Seam for tests that need to write rows directly into this test's DB.
        client.quirk_engine = engine
        try:
            yield client
        finally:
            client.close()
            app.dependency_overrides.clear()
            engine.dispose()
    except ImportError as exc:
        pytest.fail("quirk.dashboard import failed unexpectedly: " + repr(exc))
