"""Tests for Phase 57 / CR-04 / HARDEN-SCAN-02: SAML SSRF allowlist."""
from unittest.mock import MagicMock, patch
import pytest

from quirk.scanner.saml_scanner import (
    _fetch_metadata,
    scan_saml_targets,
    ADVISORY_SAML_INTERNAL_TARGET,
)


@pytest.mark.parametrize("forbidden_url,reason", [
    ("http://10.0.0.5/sso", "internal_ip"),
    ("http://192.168.1.1/sso", "internal_ip"),
    ("http://172.16.0.1/sso", "internal_ip"),
    ("http://127.0.0.1/sso", "loopback"),
    ("http://169.254.169.254/latest/meta-data/", "metadata_service_ip"),
    ("http://169.254.0.5/sso", "link_local"),
    ("file:///etc/passwd", "scheme_prefix"),
])
def test_fetch_metadata_blocks_forbidden_default(forbidden_url, reason):
    with patch("quirk.scanner.saml_scanner.httpx") as mock_httpx:
        result = _fetch_metadata(forbidden_url, timeout=5)
        assert result is None
        mock_httpx.get.assert_not_called()


def test_fetch_metadata_allow_internal_permits_rfc1918():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"<EntityDescriptor/>"
    with patch("quirk.scanner.saml_scanner.httpx") as mock_httpx:
        mock_httpx.get.return_value = mock_resp
        _fetch_metadata("http://10.0.0.5/sso", timeout=5, allow_internal=True)
        mock_httpx.get.assert_called_once()


def test_fetch_metadata_allow_internal_still_blocks_metadata_ip():
    with patch("quirk.scanner.saml_scanner.httpx") as mock_httpx:
        result = _fetch_metadata(
            "http://169.254.169.254/latest/meta-data/", timeout=5, allow_internal=True
        )
        assert result is None
        mock_httpx.get.assert_not_called()


def test_scan_saml_targets_emits_advisory_on_internal_optin():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"<EntityDescriptor xmlns='urn:oasis:names:tc:SAML:2.0:metadata'/>"
    with patch("quirk.scanner.saml_scanner.httpx") as mock_httpx:
        mock_httpx.get.return_value = mock_resp
        endpoints = scan_saml_targets(
            ["http://10.0.0.5/sso"], timeout=5, allow_internal_targets=True
        )
        advisories = [
            e for e in endpoints
            if getattr(e, "protocol", None) == "ADVISORY"
            and getattr(e, "service_detail", None) == ADVISORY_SAML_INTERNAL_TARGET
        ]
        assert len(advisories) == 1
        assert advisories[0].severity == "HIGH"


def test_scan_saml_targets_no_advisory_on_default():
    with patch("quirk.scanner.saml_scanner.httpx") as mock_httpx:
        endpoints = scan_saml_targets(["http://10.0.0.5/sso"], timeout=5)
        mock_httpx.get.assert_not_called()
        advisories = [
            e for e in endpoints
            if getattr(e, "protocol", None) == "ADVISORY"
            and getattr(e, "service_detail", None) == ADVISORY_SAML_INTERNAL_TARGET
        ]
        assert advisories == []
