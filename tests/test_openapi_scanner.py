"""Tests for OpenAPI spec scanner (SPEC-01/02/03, Phase 94).

TDD RED phase — these tests are written before the implementation exists.

Coverage:
  - test_local_file_parse: local OAS 3.0 YAML yields CryptoEndpoint rows
  - test_url_scope_rejected: URL outside cfg.targets raises SpecParsingError before network
  - test_oversize_rejected: >10MB file raises SpecParsingError before yaml.safe_load
  - test_external_ref_ssrf_guard: external $ref raises SpecParsingError with ZERO network calls
  - test_missing_extra_degrades: OPENAPI_AVAILABLE=False returns missing_extra endpoint, never raises
"""

from __future__ import annotations

import os
import tempfile
import textwrap
import json
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_OAS3_YAML = textwrap.dedent("""\
    openapi: "3.0.0"
    info:
      title: Test API
      version: "1.0.0"
    servers:
      - url: "https://api.example.com/v1"
      - url: "http://api.example.com/v1"
    paths:
      /users:
        get:
          summary: List users
          security:
            - bearerAuth: []
          responses:
            "200":
              description: OK
      /public:
        get:
          summary: Public endpoint — no security
          responses:
            "200":
              description: OK
    components:
      securitySchemes:
        bearerAuth:
          type: http
          scheme: bearer
          bearerFormat: JWT
        apiKeyAuth:
          type: apiKey
          in: header
          name: X-Api-Key
""")

_EXTERNAL_REF_OAS3_YAML = textwrap.dedent("""\
    openapi: "3.0.0"
    info:
      title: Dangerous Spec
      version: "1.0.0"
    servers:
      - url: "https://api.example.com"
    paths:
      /users:
        $ref: "http://169.254.169.254/metadata"
""")


# ---------------------------------------------------------------------------
# Test: local file parse (SPEC-01)
# ---------------------------------------------------------------------------

def test_local_file_parse(tmp_path):
    """A local OAS 3.0 YAML file yields CryptoEndpoint rows.

    Expects:
    - Security scheme rows (protocol="OPENAPI")
    - A plaintext http:// server row (service_detail contains "plaintext_server")
    - An unauthenticated endpoint row (service_detail contains "unauthenticated")
    """
    from quirk.scanner.openapi_scanner import scan_openapi_spec, SpecParsingError

    spec_file = tmp_path / "api.yaml"
    spec_file.write_text(_MINIMAL_OAS3_YAML)

    endpoints = scan_openapi_spec(str(spec_file), cfg_targets=["https://api.example.com"])

    assert len(endpoints) > 0, "Expected at least one CryptoEndpoint from the spec"

    protocols = {ep.protocol for ep in endpoints}
    assert "OPENAPI" in protocols, f"Expected protocol='OPENAPI' among endpoints; got {protocols}"

    service_details = {ep.service_detail for ep in endpoints}

    # Plaintext server check
    plaintext_eps = [ep for ep in endpoints if "plaintext_server" in (ep.service_detail or "")]
    assert len(plaintext_eps) >= 1, (
        f"Expected at least one plaintext_server endpoint; service_details={service_details}"
    )

    # Unauthenticated path check
    unauth_eps = [ep for ep in endpoints if "unauthenticated" in (ep.service_detail or "").lower()]
    assert len(unauth_eps) >= 1, (
        f"Expected at least one unauthenticated_endpoint; service_details={service_details}"
    )


def test_local_file_security_scheme_rows(tmp_path):
    """Security scheme rows carry the scheme name and JWT bearerFormat alg."""
    from quirk.scanner.openapi_scanner import scan_openapi_spec

    spec_file = tmp_path / "api.yaml"
    spec_file.write_text(_MINIMAL_OAS3_YAML)

    endpoints = scan_openapi_spec(str(spec_file), cfg_targets=[])
    security_eps = [ep for ep in endpoints if "security_scheme" in (ep.service_detail or "")]
    assert len(security_eps) >= 1, (
        f"Expected at least one security_scheme endpoint; details={[ep.service_detail for ep in endpoints]}"
    )


# ---------------------------------------------------------------------------
# Test: URL scope rejected (SPEC-02)
# ---------------------------------------------------------------------------

def test_url_scope_rejected():
    """A URL not in cfg.targets raises SpecParsingError BEFORE any network call."""
    from quirk.scanner.openapi_scanner import scan_openapi_spec, SpecParsingError

    url = "https://evil.example.com/openapi.yaml"
    cfg_targets = ["https://safe.example.com"]

    # Patch httpx.get to assert it is never called
    with patch("httpx.get") as mock_get:
        with pytest.raises(SpecParsingError, match="scope"):
            scan_openapi_spec(url, cfg_targets=cfg_targets)
        mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# Test: oversize rejected (SPEC-03 DoS guard)
# ---------------------------------------------------------------------------

def test_oversize_rejected(tmp_path):
    """A file over 10 MB raises SpecParsingError before yaml.safe_load."""
    from quirk.scanner.openapi_scanner import scan_openapi_spec, SpecParsingError, MAX_SPEC_BYTES

    # Create a file slightly over the limit
    big_file = tmp_path / "big_spec.yaml"
    big_file.write_bytes(b"x" * (MAX_SPEC_BYTES + 1))

    with patch("yaml.safe_load") as mock_yaml:
        with pytest.raises(SpecParsingError, match="10 MB"):
            scan_openapi_spec(str(big_file), cfg_targets=[])
        mock_yaml.assert_not_called()


# ---------------------------------------------------------------------------
# Test: external $ref SSRF guard (SPEC-03)
# ---------------------------------------------------------------------------

def test_external_ref_ssrf_guard(tmp_path):
    """A spec containing $ref 'http://169.254.169.254/meta' raises SpecParsingError.

    CRITICAL: httpx.get and openapi_spec_validator.validate MUST NOT be called.
    This is the primary SSRF guard test — proven by mock assertion.
    """
    from quirk.scanner.openapi_scanner import scan_openapi_spec, SpecParsingError

    spec_file = tmp_path / "ssrf_spec.yaml"
    spec_file.write_text(_EXTERNAL_REF_OAS3_YAML)

    with patch("httpx.get") as mock_get:
        # Patch the validator to assert it is never called
        with patch("quirk.scanner.openapi_scanner._oas_validate") as mock_validate:
            with pytest.raises(SpecParsingError, match="(?i)ssrf|external.*ref|ref.*external"):
                scan_openapi_spec(str(spec_file), cfg_targets=[])
            mock_validate.assert_not_called()
        mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# Test: missing extra degrades gracefully (no raise)
# ---------------------------------------------------------------------------

def test_missing_extra_degrades():
    """With OPENAPI_AVAILABLE=False, scan returns a single missing_extra endpoint."""
    import quirk.scanner.openapi_scanner as oas_mod

    with patch.object(oas_mod, "OPENAPI_AVAILABLE", False):
        endpoints = oas_mod.scan_openapi_spec("some_spec.yaml", cfg_targets=[])

    assert len(endpoints) == 1
    ep = endpoints[0]
    assert ep.scan_error_category == "missing_extra", (
        f"Expected scan_error_category='missing_extra', got {ep.scan_error_category!r}"
    )
    assert ep.protocol == "OPENAPI"


# ---------------------------------------------------------------------------
# Test: openapi_plaintext_server_count evidence counter (SCORE-01)
# ---------------------------------------------------------------------------

def test_openapi_plaintext_server_evidence_counter(tmp_path):
    """OpenAPI plaintext server endpoints increment openapi_plaintext_server_count in evidence."""
    from quirk.scanner.openapi_scanner import scan_openapi_spec
    from quirk.intelligence.evidence import build_evidence_summary

    spec_file = tmp_path / "api.yaml"
    spec_file.write_text(_MINIMAL_OAS3_YAML)

    endpoints = scan_openapi_spec(str(spec_file), cfg_targets=[])
    evidence = build_evidence_summary(endpoints)

    assert evidence["openapi_plaintext_server_count"] >= 1, (
        f"Expected openapi_plaintext_server_count >= 1; got {evidence['openapi_plaintext_server_count']}"
    )


# ---------------------------------------------------------------------------
# CR-01 regression: bare-FQDN targets must match a full URL by HOST (not prefix)
# ---------------------------------------------------------------------------

def test_url_scope_accepts_bare_fqdn_target():
    """A URL whose host is in bare-FQDN cfg.targets passes the scope gate (CR-01).

    Regression for the prefix-match bug: cfg.targets are bare FQDNs like
    'api.example.com', which never prefix-match 'https://api.example.com/...'.
    The scope gate must compare HOSTS. We mock httpx.get so the request is
    intercepted AFTER the scope gate has been passed.
    """
    from quirk.scanner.openapi_scanner import scan_openapi_spec, SpecParsingError

    url = "https://api.example.com/openapi.yaml"
    cfg_targets = ["api.example.com"]  # bare FQDN — the real cfg.targets.fqdns shape

    mock_resp = MagicMock()
    mock_resp.content = b"openapi: 3.0.0\ninfo:\n  title: t\n  version: '1'\npaths: {}\n"
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_resp) as mock_get:
        # Should NOT raise a scope error; httpx.get must be reached.
        try:
            scan_openapi_spec(url, cfg_targets=cfg_targets)
        except SpecParsingError as exc:
            assert "scope" not in str(exc).lower(), f"scope gate wrongly rejected in-scope host: {exc}"
        mock_get.assert_called_once()
