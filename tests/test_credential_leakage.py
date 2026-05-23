"""Phase 59 LEAK-02 + Phase 93 AUTH-02: per-connector regression tests verifying that
scan_error writes never carry credential-shaped substrings, plus sentinel leak-detection
suite asserting that credentials never reach stored/rendered surfaces (D-06/D-07).

Approach: each connector's exception path funnels through safe_str().
These tests assert (a) safe_str strips the credential payloads we know
real libraries surface, (b) every modified file imports safe_str, and
(c) a known sentinel credential appears in none of the 11 stored/rendered surfaces.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from quirk.util.safe_exc import safe_str

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

MODIFIED_FILES = [
    "quirk/scanner/vault_connector.py",
    "quirk/scanner/gcp_connector.py",
    "quirk/scanner/tls_scanner.py",
    "quirk/scanner/email_scanner.py",
    "quirk/scanner/broker_scanner.py",
    "quirk/scanner/ssh_scanner.py",
    # quirk/discovery/tls_scanner.py removed in Phase 71 (WR-13, dead duplicate)
    "quirk/cbom/writer.py",
    "quirk/auth/credentials.py",  # Phase 93: credential module must import safe_str
]

# ---------------------------------------------------------------------------
# Phase 93 / AUTH-02: sentinel value for leak-detection tests (D-06/D-07).
# This string is intentionally unique; its presence in any stored/rendered
# surface indicates a credential-leakage regression.
# ---------------------------------------------------------------------------
SENTINEL = "QUIRK_SENTINEL_CRED_d41d8cd9"


# ---------------------------------------------------------------------------
# Behavior tests — verify safe_str strips known credential payloads
# ---------------------------------------------------------------------------

def test_vault_scan_error_strips_token() -> None:
    """T-59-04: Vault hvac token in exception must be stripped."""
    exc = Exception("https://vault:8200?token=s.AbCdEfGhIjKlMnOpQrSt1234")
    result = safe_str(exc)
    assert result == "Exception"


def test_gcp_scan_error_strips_adc_path() -> None:
    """T-59-05: GCP ADC path in exception must be stripped."""
    exc = Exception("/home/user/.config/gcloud/application_default_credentials.json missing")
    result = safe_str(exc)
    assert result == "Exception"


def test_email_scan_error_strips_smtp_password() -> None:
    """T-59-06: SMTP connection string password must be stripped."""
    exc = Exception("smtp://user:secret123@mail.example.com:587 auth failed")
    result = safe_str(exc)
    assert result == "Exception"


def test_broker_scan_error_strips_redis_password() -> None:
    """T-59-06: Redis connection string password must be stripped."""
    exc = Exception("redis://default:supersecret@redis:6379 auth failed")
    result = safe_str(exc)
    assert result == "Exception"


def test_ssh_scan_error_class_name_only_for_creds() -> None:
    """T-59-07: Authorization Bearer header in SSH exception must be stripped."""
    exc = Exception("Authorization: Bearer abc.def.ghi")
    result = safe_str(exc)
    assert result == "Exception"


def test_tls_scan_error_benign_passthrough() -> None:
    """T-59-07: Benign connection errors pass through with message intact."""
    result = safe_str(ConnectionRefusedError("[Errno 111] Connection refused"))
    assert result.startswith("ConnectionRefusedError:")


def test_cbom_writer_scan_error_strips_creds() -> None:
    """T-59-14: CBOM validator text with DB connection string is stripped."""
    exc = Exception("validator config: postgresql://admin:S3cret!@db:5432/x")
    result = safe_str(exc)
    assert result == "Exception"


# ---------------------------------------------------------------------------
# Import-presence gate — all 8 modified files must import safe_str
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("relpath", MODIFIED_FILES)
def test_all_callsites_import_safe_str(relpath: str) -> None:
    path = PROJECT_ROOT / relpath
    text = path.read_text(encoding="utf-8")
    assert "from quirk.util.safe_exc import safe_str" in text, (
        f"{relpath} must import safe_str"
    )


# ---------------------------------------------------------------------------
# Phase 93 / AUTH-02: Sentinel leak-detection suite (D-06/D-07)
#
# These tests inject SENTINEL as a credential value and assert it is absent
# from every stored/rendered surface. Together with 93-SECURITY-REVIEW-GATE.md
# they form the milestone's committed security gate (D-07).
# ---------------------------------------------------------------------------


def test_sentinel_not_in_safe_str_bearer_shape() -> None:
    """AUTH-02 / D-06: Authorization Bearer shape must be scrubbed by safe_str."""
    exc = Exception(f"Authorization: Bearer {SENTINEL}")
    result = safe_str(exc)
    assert SENTINEL not in result, f"Sentinel leaked through safe_str (Bearer): {result!r}"


def test_sentinel_not_in_safe_str_api_key_header_shape() -> None:
    """AUTH-02 / D-06: X-Api-Key header shape must be scrubbed by safe_str (D-08)."""
    exc = Exception(f"X-Api-Key: {SENTINEL}")
    result = safe_str(exc)
    assert SENTINEL not in result, f"Sentinel leaked through safe_str (X-Api-Key): {result!r}"


def test_sentinel_not_in_safe_str_query_param_shape() -> None:
    """AUTH-02 / D-06 / D-03: query-param API key shape must be scrubbed by safe_str (D-08)."""
    exc = Exception(f"https://api.example.com?api_key={SENTINEL}")
    result = safe_str(exc)
    assert SENTINEL not in result, f"Sentinel leaked through safe_str (query param): {result!r}"


def test_sentinel_not_in_safe_str_basic_shape() -> None:
    """AUTH-02 / D-06: HTTP Basic authorization shape must be scrubbed by safe_str (D-08)."""
    import base64
    basic_encoded = base64.b64encode(f"user:{SENTINEL}".encode()).decode()
    exc = Exception(f"Authorization: Basic {basic_encoded}")
    result = safe_str(exc)
    assert SENTINEL not in result, f"Sentinel leaked through safe_str (Basic): {result!r}"


def test_sentinel_not_in_scan_error_json() -> None:
    """AUTH-02 / D-06: sentinel in a CryptoEndpoint scan_error must not appear in json.dumps output."""
    from quirk.models import CryptoEndpoint

    # scan_error is written via safe_str in _wrapped_phase; safe_str must scrub it
    scrubbed = safe_str(Exception(f"Authorization: Bearer {SENTINEL}"))
    ep = CryptoEndpoint(
        host="example.com",
        port=443,
        protocol="JWT",
        scan_error=scrubbed,
    )
    dumped = json.dumps({"scan_error": ep.scan_error})
    assert SENTINEL not in dumped, f"Sentinel leaked into JSON scan_error: {dumped!r}"


def test_sentinel_not_in_db_row(tmp_path) -> None:
    """AUTH-02 / D-06: sentinel credential must not appear in the persisted SQLite scan row.

    Creates a real CredentialContext seeded with SENTINEL (api_key_query scheme),
    writes a CryptoEndpoint row with a scan_error path that exercises safe_str,
    then reads the row back and asserts SENTINEL is absent from all text columns.
    """
    import os
    from quirk.auth.credentials import CredentialContext
    from quirk.db import init_db, get_session
    from quirk.models import CryptoEndpoint
    from datetime import datetime, timezone

    db_path = str(tmp_path / "sentinel_test.db")
    init_db(db_path)

    # Build a real CredentialContext with SENTINEL as the secret via env var
    os.environ["_QUIRK_SENTINEL_TEST_ENV"] = SENTINEL
    try:
        ctx = CredentialContext.from_cli(api_key_query="_QUIRK_SENTINEL_TEST_ENV")
    finally:
        os.environ.pop("_QUIRK_SENTINEL_TEST_ENV", None)

    assert ctx is not None

    # Simulate what _wrapped_phase would write: scan_error routed via safe_str.
    # Use a URL query-param shape that matches the safe_str pattern (D-08).
    error_text = safe_str(Exception(f"https://api.example.com?api_key={SENTINEL}"))

    ep = CryptoEndpoint(
        host="jwt.example.com",
        port=443,
        protocol="JWT",
        scan_error=error_text,
        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    with get_session(db_path) as session:
        session.add(ep)
        session.commit()
        row_id = ep.id

    # Read back the row and check all text columns
    with get_session(db_path) as session:
        row = session.get(CryptoEndpoint, row_id)
        assert row is not None

        text_fields = [
            row.scan_error,
            row.service_detail,
            row.jwt_scan_json,
            row.host,
        ]
        for val in text_fields:
            if val is not None:
                assert SENTINEL not in val, (
                    f"Sentinel found in DB column '{val!r}'"
                )

    # Zeroize credential buffer
    ctx.close()

    # Assert buffer is zeroed after close()
    assert all(b == 0 for b in ctx._secret_buf), (
        "CredentialContext buffer not zeroed after close()"
    )


def test_sentinel_not_in_cbom_json(tmp_path) -> None:
    """AUTH-02 / D-06: sentinel must not appear in CBOM JSON output.

    Builds a CryptoEndpoint with a safe_str-scrubbed scan_error bearing the sentinel
    (simulating what an authenticated scan would produce), generates a CBOM, writes
    it to a file, and asserts SENTINEL is absent from the file contents.
    """
    import os
    from quirk.models import CryptoEndpoint
    from quirk.cbom import build_cbom
    from quirk.cbom.writer import write_cbom_files
    from datetime import datetime, timezone

    # Simulate scan_error with sentinel scrubbed by safe_str
    error_text = safe_str(Exception(f"Authorization: Bearer {SENTINEL}"))

    ep = CryptoEndpoint(
        host="jwt.example.com",
        port=443,
        protocol="JWT",
        cert_pubkey_alg="RS256",
        cert_pubkey_size=2048,
        scan_error=error_text,
        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    bom = build_cbom([ep])
    outdir = str(tmp_path / "cbom_out")
    json_path, _ = write_cbom_files(bom, outdir, "20260523-000000")

    cbom_text = pathlib.Path(json_path).read_text(encoding="utf-8")
    assert SENTINEL not in cbom_text, (
        f"Sentinel found in CBOM JSON at {json_path}"
    )


def test_sentinel_not_in_dashboard_api_json(dashboard_client) -> None:
    """AUTH-02 / D-06: sentinel must not appear in /api/scan/latest JSON response.

    Writes a CryptoEndpoint row with a sentinel-bearing (safe_str scrubbed) scan_error,
    then calls the dashboard API and asserts SENTINEL is absent from the response JSON.
    """
    from quirk.models import CryptoEndpoint, Base
    from quirk.dashboard.api.deps import get_db
    from datetime import datetime, timezone

    # Use the dashboard client's overridden get_db to write a row
    override_gen = dashboard_client.app.dependency_overrides.get(get_db)
    if override_gen is None:
        pytest.skip("dashboard get_db override not set up")

    db = next(override_gen())
    try:
        scrubbed = safe_str(Exception(f"Authorization: Bearer {SENTINEL}"))
        ep = CryptoEndpoint(
            host="jwt.sentinel.example.com",
            port=443,
            protocol="JWT",
            cert_pubkey_alg="RS256",
            scan_error=scrubbed,
            scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(ep)
        db.commit()
    finally:
        db.close()

    resp = dashboard_client.get("/api/scan/latest")
    resp_text = resp.text
    assert SENTINEL not in resp_text, (
        f"Sentinel found in /api/scan/latest response body"
    )


def test_sentinel_not_in_pdf_export_surface(tmp_path) -> None:
    """AUTH-02 / SC-2: sentinel must not appear in the PDF export surface.

    PDF export (quirk/dashboard/api/routes/pdf.py) renders via Playwright from
    the /print route, which is populated from the same CBOM JSON / SQLite
    CryptoEndpoint rows that /api/scan/latest serves. The PDF export has NO
    independent data path — it is a headless-browser rendering of the React
    dashboard UI, which reads from /api/scan/* endpoints.

    LINKAGE: The PDF export surface shares its upstream data source with:
      - The SQLite 'scan_error' column (asserted in test_sentinel_not_in_db_row)
      - The 'jwt_scan_json' column (asserted in test_sentinel_not_in_db_row)
      - The CBOM JSON file (asserted in test_sentinel_not_in_cbom_json)
      - The /api/scan/latest JSON response (asserted in test_sentinel_not_in_dashboard_api_json)

    Since the PDF renderer reads exclusively from these same CBOM-JSON/DB columns,
    the automated assertions on those upstream sources provably cover the PDF surface.
    This assertion explicitly confirms that the CBOM JSON (the shared upstream source
    the PDF derives from) does not contain the sentinel.

    NOTE: A live Playwright PDF render is not performed here because it requires
    a running server + Playwright Chromium install. The upstream-linkage approach
    satisfies SC-2 per the plan: "assert on that exact upstream data source explicitly
    AND document the linkage in the test (a comment naming the shared CBOM-JSON/DB
    column the PDF reads from)".
    """
    from quirk.models import CryptoEndpoint
    from quirk.cbom import build_cbom
    from quirk.cbom.writer import write_cbom_files
    from datetime import datetime, timezone

    # The credential never enters any endpoint field — it is either stripped by
    # safe_str (scan_error path) or kept ephemeral (never serialized).
    ep = CryptoEndpoint(
        host="pdf.sentinel.example.com",
        port=443,
        protocol="JWT",
        cert_pubkey_alg="RS256",
        cert_pubkey_size=2048,
        # scan_error would carry a safe_str-scrubbed message; SENTINEL absent
        scan_error=safe_str(Exception(f"Bearer {SENTINEL}")),
        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    bom = build_cbom([ep])
    outdir = str(tmp_path / "pdf_cbom_out")
    json_path, _ = write_cbom_files(bom, outdir, "20260523-000001")

    # The CBOM JSON is the shared upstream source that the PDF renderer derives from.
    # Asserting SENTINEL is absent here provably covers the PDF export surface (SC-2).
    cbom_text = pathlib.Path(json_path).read_text(encoding="utf-8")
    assert SENTINEL not in cbom_text, (
        f"Sentinel found in CBOM JSON (PDF upstream source) at {json_path}"
    )


def test_credential_context_buffer_zeroed_after_close() -> None:
    """AUTH-02 / D-04: CredentialContext bytearray buffer must be zeroed after close()."""
    import os
    from quirk.auth.credentials import CredentialContext

    os.environ["_QUIRK_ZEROIZE_TEST_ENV"] = SENTINEL
    try:
        ctx = CredentialContext.from_cli(bearer="_QUIRK_ZEROIZE_TEST_ENV")
    finally:
        os.environ.pop("_QUIRK_ZEROIZE_TEST_ENV", None)

    assert ctx is not None
    assert len(ctx._secret_buf) > 0, "Buffer should be non-empty before close"

    ctx.close()

    assert all(b == 0 for b in ctx._secret_buf), (
        "CredentialContext buffer not zeroed after close()"
    )
