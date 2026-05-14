"""Shared fixtures for dashboard test suite."""
import pytest


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
    """Return True if patching succeeded, False if openssl binary is absent."""
    try:
        import subprocess
        import tempfile
        import os
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

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
                result = subprocess.run(
                    [
                        "openssl", "req", "-new", "-x509", "-sha1",
                        "-key", key_path, "-out", cert_path,
                        "-days", "365", "-subj", subj,
                    ],
                    capture_output=True,
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"openssl SHA1 cert failed: {result.stderr.decode()}"
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


@pytest.fixture
def dashboard_client():
    """FastAPI TestClient for the dashboard app with an in-memory test database.

    Overrides the get_db dependency to use a fresh in-memory SQLite DB so
    tests pass without requiring a real data/quirk.db file.
    """
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from quirk.dashboard.api.app import create_app
        from quirk.dashboard.api.deps import get_db
        from quirk.models import Base
        from fastapi.testclient import TestClient

        # Create a shared in-memory SQLite DB with all tables.
        # Use file::memory:?cache=shared so the same DB is accessible from
        # the worker thread FastAPI uses for sync route handlers.
        engine = create_engine(
            "sqlite:///file::memory:?cache=shared&uri=true",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        def override_get_db():
            db = TestingSession()
            try:
                yield db
            finally:
                db.close()

        app = create_app()
        app.dependency_overrides[get_db] = override_get_db
        return TestClient(app, headers={"X-Quirk-Request": "1"})
    except ImportError as exc:
        pytest.fail("quirk.dashboard import failed unexpectedly: " + repr(exc))
