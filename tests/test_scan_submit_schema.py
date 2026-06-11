"""
Tests for Phase 121-01 — ScanSubmitRequest schema validation (PORT-03, PORT-04).

Covers:
- Default port_scope is 'top1000', custom_ports is None (PORT-03)
- 'custom' scope without custom_ports raises ValidationError (PORT-04)
- 'custom' scope with valid custom_ports is accepted (PORT-03)
- Valid non-custom scopes are accepted (PORT-03)
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from quirk.dashboard.api.schemas import ScanSubmitRequest


def test_default_port_scope_is_top1000() -> None:
    """Default port_scope is 'top1000' and custom_ports is None (PORT-03)."""
    req = ScanSubmitRequest(targets="example.com")
    assert req.port_scope == "top1000"
    assert req.custom_ports is None


def test_custom_scope_requires_custom_ports() -> None:
    """port_scope='custom' without custom_ports raises ValidationError (PORT-04)."""
    with pytest.raises(ValidationError) as exc_info:
        ScanSubmitRequest(targets="example.com", port_scope="custom", custom_ports=None)
    assert "custom_ports is required" in str(exc_info.value)


def test_custom_scope_with_empty_string_requires_custom_ports() -> None:
    """port_scope='custom' with empty string custom_ports raises ValidationError (PORT-04)."""
    with pytest.raises(ValidationError) as exc_info:
        ScanSubmitRequest(targets="example.com", port_scope="custom", custom_ports="   ")
    assert "custom_ports is required" in str(exc_info.value)


def test_custom_scope_with_ports_accepted() -> None:
    """port_scope='custom' with a non-empty custom_ports is accepted (PORT-03)."""
    req = ScanSubmitRequest(targets="example.com", port_scope="custom", custom_ports="443,8443")
    assert req.port_scope == "custom"
    assert req.custom_ports == "443,8443"


def test_common_scope_accepted() -> None:
    """port_scope='common' is accepted; custom_ports optional (PORT-03)."""
    req = ScanSubmitRequest(targets="example.com", port_scope="common")
    assert req.port_scope == "common"
    assert req.custom_ports is None


def test_all_scope_accepted() -> None:
    """port_scope='all' is accepted (PORT-03)."""
    req = ScanSubmitRequest(targets="example.com", port_scope="all")
    assert req.port_scope == "all"


def test_top1000_scope_explicit() -> None:
    """Explicitly setting port_scope='top1000' is accepted (PORT-03)."""
    req = ScanSubmitRequest(targets="example.com", port_scope="top1000")
    assert req.port_scope == "top1000"
