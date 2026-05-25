"""Tests for quirk/siem/formatter.py — ISEC-03 per-finding whitelist.

Covers:
- to_cef_finding() returns the exact whitelisted key set
- host and port ARE included (SIEM needs them for dhost/dpt fields)
- cert_pem, cert_sans, cert_subject, private_key are EXCLUDED
- compliance list is EXCLUDED
- build_cef_event() string does not contain any forbidden material
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Whitelist / blocklist constants (ISEC-03 enforcement)
# ---------------------------------------------------------------------------

ALLOWED_FIELDS = frozenset({
    "severity",
    "host",
    "port",
    "title",
    "category",
    "description",
    "recommendation",
})

FORBIDDEN_FIELDS = frozenset({
    "cert_pem",
    "cert_sans",
    "cert_subject",
    "cert_issuer",
    "private_key",
    "key_material",
    "compliance",
})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _clean_finding(**overrides) -> dict:
    """Return a clean finding dict matching the actual findings-*.json shape."""
    base = {
        "severity": "HIGH",
        "host": "10.0.0.1",
        "port": 443,
        "title": "TLS certificate expired",
        "description": "The certificate has expired.",
        "recommendation": "Renew immediately.",
        "compliance": [
            {"framework": "NIST SP 800-131A", "control": "TA-01"},
            {"framework": "PCI-DSS", "control": "4.1"},
        ],
    }
    base.update(overrides)
    return base


def _salted_finding(**overrides) -> dict:
    """A finding salted with forbidden fields to test exclusion."""
    base = _clean_finding(**overrides)
    base["cert_pem"] = "-----BEGIN CERTIFICATE-----\nMIIC...SECRET\n-----END CERTIFICATE-----"
    base["cert_sans"] = ["*.example.com", "example.com"]
    base["cert_subject"] = "CN=example.com,O=Acme"
    base["cert_issuer"] = "CN=Let's Encrypt"
    base["private_key"] = "-----BEGIN RSA PRIVATE KEY-----\nSECRET\n-----END RSA PRIVATE KEY-----"
    base["key_material"] = b"raw_key_bytes_here"
    return base


# ---------------------------------------------------------------------------
# Tests — to_cef_finding whitelist
# ---------------------------------------------------------------------------

class TestToCefFindingWhitelist:
    """ISEC-03: explicit whitelist extraction — only allowed fields in output."""

    def test_returns_dict(self):
        from quirk.siem.formatter import to_cef_finding

        result = to_cef_finding(_clean_finding())
        assert isinstance(result, dict)

    def test_allowed_fields_present(self):
        """to_cef_finding output must contain severity, host, port, title, category, description."""
        from quirk.siem.formatter import to_cef_finding

        result = to_cef_finding(_clean_finding())
        for field in ("severity", "host", "port", "title", "category"):
            assert field in result, f"Expected allowed field '{field}' to be present in output"

    def test_no_forbidden_fields(self):
        """No forbidden field must appear in to_cef_finding output."""
        from quirk.siem.formatter import to_cef_finding

        result = to_cef_finding(_salted_finding())
        for forbidden in FORBIDDEN_FIELDS:
            assert forbidden not in result, (
                f"Forbidden field '{forbidden}' must not appear in to_cef_finding output (ISEC-03)"
            )

    def test_no_extra_unknown_fields(self):
        """to_cef_finding must not pass through unknown keys."""
        from quirk.siem.formatter import to_cef_finding

        finding = _salted_finding()
        finding["unknown_future_field"] = "should_not_appear"
        result = to_cef_finding(finding)
        assert "unknown_future_field" not in result, (
            "Unknown fields must not pass through to_cef_finding (ISEC-03 explicit extraction)"
        )

    # ---
    # Host and port MUST be included
    # ---

    def test_host_port_present(self):
        """host and port survive the whitelist — SIEM needs them for dhost/dpt."""
        from quirk.siem.formatter import to_cef_finding

        result = to_cef_finding(_clean_finding(host="192.168.1.50", port=8443))
        assert "host" in result, "host must be present in to_cef_finding output"
        assert "port" in result, "port must be present in to_cef_finding output"
        assert result["host"] == "192.168.1.50"
        assert result["port"] == 8443

    def test_host_survives_salted_finding(self):
        """host survives even when finding is salted with forbidden fields."""
        from quirk.siem.formatter import to_cef_finding

        result = to_cef_finding(_salted_finding(host="10.10.10.1"))
        assert result["host"] == "10.10.10.1"

    # ---
    # Cert PEM / SANs exclusion
    # ---

    def test_cert_pem_excluded(self):
        """cert_pem must not appear in to_cef_finding output."""
        from quirk.siem.formatter import to_cef_finding

        result = to_cef_finding(_salted_finding())
        assert "cert_pem" not in result

    def test_cert_sans_excluded(self):
        """cert_sans must not appear in to_cef_finding output."""
        from quirk.siem.formatter import to_cef_finding

        result = to_cef_finding(_salted_finding())
        assert "cert_sans" not in result

    def test_private_key_excluded(self):
        """private_key must not appear in to_cef_finding output."""
        from quirk.siem.formatter import to_cef_finding

        result = to_cef_finding(_salted_finding())
        assert "private_key" not in result

    # ---
    # Compliance exclusion
    # ---

    def test_compliance_excluded_from_to_cef_finding(self):
        """compliance list must not appear in to_cef_finding output."""
        from quirk.siem.formatter import to_cef_finding

        result = to_cef_finding(_clean_finding())
        assert "compliance" not in result, (
            "compliance list must be excluded from to_cef_finding output (ISEC-03)"
        )


# ---------------------------------------------------------------------------
# Tests — build_cef_event string does not contain forbidden material
# ---------------------------------------------------------------------------

class TestBuildCefEventExclusion:
    """build_cef_event CEF line must not contain cert/compliance/key material."""

    def test_cert_pem_not_in_cef_line(self):
        """cert_pem value must not appear anywhere in the CEF event string."""
        from quirk.siem.formatter import build_cef_event

        finding = _salted_finding()
        line = build_cef_event(finding, "1.0.0")
        assert "SECRET" not in line, (
            f"cert_pem material leaked into CEF line: {line}"
        )
        assert "BEGIN CERTIFICATE" not in line, (
            f"cert_pem PEM header leaked into CEF line: {line}"
        )

    def test_private_key_not_in_cef_line(self):
        """private_key value must not appear anywhere in the CEF event string."""
        from quirk.siem.formatter import build_cef_event

        finding = _salted_finding()
        line = build_cef_event(finding, "1.0.0")
        assert "BEGIN RSA PRIVATE KEY" not in line, (
            f"private_key PEM header leaked into CEF line: {line}"
        )

    def test_compliance_substring_not_in_cef_line(self):
        """compliance list contents must not appear in the CEF event string."""
        from quirk.siem.formatter import build_cef_event

        finding = _clean_finding()
        line = build_cef_event(finding, "1.0.0")
        # The raw compliance key should not be in the line
        assert "compliance" not in line, (
            f"'compliance' key/value appeared in CEF line: {line}"
        )
        # And the compliance framework values should not appear
        assert "NIST SP 800-131A" not in line, (
            f"Compliance framework value leaked into CEF line: {line}"
        )

    def test_cert_sans_not_in_cef_line(self):
        """cert_sans domain values must not appear in the CEF event string."""
        from quirk.siem.formatter import build_cef_event

        finding = _salted_finding()
        line = build_cef_event(finding, "1.0.0")
        assert "*.example.com" not in line, (
            f"cert_sans value leaked into CEF line: {line}"
        )

    def test_host_present_in_cef_line(self):
        """host value appears in the CEF extension (dhost field)."""
        from quirk.siem.formatter import build_cef_event

        finding = _clean_finding(host="172.16.0.5")
        line = build_cef_event(finding, "1.0.0")
        assert "172.16.0.5" in line, (
            f"host must appear in CEF line (dhost field), not found in: {line}"
        )

    def test_port_present_in_cef_line(self):
        """port value appears in the CEF extension (dpt field)."""
        from quirk.siem.formatter import build_cef_event

        finding = _clean_finding(port=9443)
        line = build_cef_event(finding, "1.0.0")
        assert "9443" in line, (
            f"port must appear in CEF line (dpt field), not found in: {line}"
        )
