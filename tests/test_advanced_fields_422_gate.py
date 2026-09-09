"""Phase 194 / Plan 02 / Task 1 — AdvancedScanFields 422 gate (PARITY-04 / D-03).

Every invalid-input class the `AdvancedScanFields` request model + its
`build_advanced_overlays` mapper must reject before a job or preview is ever
resolved. See `quirk/dashboard/api/schemas.py::AdvancedScanFields` and
`quirk/dashboard/api/routes/jobs.py::build_advanced_overlays`.

pytest -q tests/test_advanced_fields_422_gate.py
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from quirk.dashboard.api.routes.jobs import build_advanced_overlays
from quirk.dashboard.api.schemas import AdvancedScanFields


def test_tls_enum_mode_off_rejected():
    """D-19: "off" is deliberately absent from the Literal — tls_scanner.py
    silently coerces it to "fast", so offering it would be a no-op."""
    with pytest.raises(ValidationError):
        AdvancedScanFields(tls_enum_mode="off")


def test_data_classification_restricted_rejected():
    """D-21: the vocabulary is _DATA_CLASS_MAP's 4 values — no "restricted"."""
    with pytest.raises(ValidationError):
        AdvancedScanFields(data_classification="restricted")


def test_timeout_tls_seconds_zero_rejected():
    with pytest.raises(ValidationError):
        AdvancedScanFields(timeout_tls_seconds=0)


def test_timeout_tls_seconds_over_max_rejected():
    with pytest.raises(ValidationError):
        AdvancedScanFields(timeout_tls_seconds=301)


def test_retry_count_out_of_bounds_rejected():
    with pytest.raises(ValidationError):
        AdvancedScanFields(retry_count=999999)


def test_unknown_key_ports_ssh_rejected():
    """D-18: no ports_ssh field exists (no CLI/scanner counterpart, filed as
    backlog 999.106) — extra="forbid" rejects it as an unrecognized key."""
    with pytest.raises(ValidationError):
        AdvancedScanFields(ports_ssh=[22])


def test_malformed_ports_tls_raises_value_error_from_parse_port_spec():
    advanced = AdvancedScanFields(ports_tls="443,abc")
    with pytest.raises(ValueError):
        build_advanced_overlays(advanced)


def test_empty_advanced_fields_produce_empty_overlays():
    scan_overlay, assessment_overlay = build_advanced_overlays(AdvancedScanFields())
    assert scan_overlay == {}
    assert assessment_overlay == {}


def test_none_advanced_produces_empty_overlays():
    scan_overlay, assessment_overlay = build_advanced_overlays(None)
    assert scan_overlay == {}
    assert assessment_overlay == {}
