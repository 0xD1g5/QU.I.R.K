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


# ---------------------------------------------------------------------------
# Phase 198 / PARITY-08 / PARITY-09 / D-11 — 19 new fields' bounds gate
# ---------------------------------------------------------------------------

_NEW_TIMEOUT_FIELDS = [
    "timeout_fingerprint_seconds",
    "timeout_jwt_seconds",
    "timeout_container_seconds",
    "timeout_source_seconds",
    "timeout_dnssec_seconds",
    "timeout_saml_seconds",
    "timeout_kerberos_seconds",
    "timeout_vault_seconds",
    "timeout_db_connect_seconds",
    "timeout_broker_seconds",
    "timeout_email_seconds",
]

_CONCURRENCY_FIELDS = [
    "scan_concurrency",
    "fingerprint_concurrency",
    "tls_concurrency",
    "ssh_concurrency",
    "motion_concurrency",
]


@pytest.mark.parametrize("field_name", _NEW_TIMEOUT_FIELDS)
def test_new_timeout_field_accepts_bounds(field_name):
    """1 and 600 are both valid (D-11: 1-600 for the 19 new fields)."""
    AdvancedScanFields(**{field_name: 1})
    AdvancedScanFields(**{field_name: 600})


@pytest.mark.parametrize("field_name", _NEW_TIMEOUT_FIELDS)
def test_new_timeout_field_rejects_zero(field_name):
    with pytest.raises(ValidationError):
        AdvancedScanFields(**{field_name: 0})


@pytest.mark.parametrize("field_name", _NEW_TIMEOUT_FIELDS)
def test_new_timeout_field_rejects_over_max(field_name):
    with pytest.raises(ValidationError):
        AdvancedScanFields(**{field_name: 601})


@pytest.mark.parametrize("field_name", _CONCURRENCY_FIELDS)
def test_concurrency_field_accepts_bounds(field_name):
    """1 and 500 are both valid (D-11: 1-500)."""
    AdvancedScanFields(**{field_name: 1})
    AdvancedScanFields(**{field_name: 500})


@pytest.mark.parametrize("field_name", _CONCURRENCY_FIELDS)
def test_concurrency_field_rejects_zero(field_name):
    with pytest.raises(ValidationError):
        AdvancedScanFields(**{field_name: 0})


@pytest.mark.parametrize("field_name", _CONCURRENCY_FIELDS)
def test_concurrency_field_rejects_over_max(field_name):
    with pytest.raises(ValidationError):
        AdvancedScanFields(**{field_name: 501})


def test_backoff_fields_accept_valid_floats():
    AdvancedScanFields(retry_backoff_base_seconds=0.5, retry_backoff_max_seconds=30.0)


@pytest.mark.parametrize(
    "field_name", ["retry_backoff_base_seconds", "retry_backoff_max_seconds"]
)
def test_backoff_field_rejects_zero(field_name):
    with pytest.raises(ValidationError):
        AdvancedScanFields(**{field_name: 0})


@pytest.mark.parametrize(
    "field_name", ["retry_backoff_base_seconds", "retry_backoff_max_seconds"]
)
def test_backoff_field_rejects_negative(field_name):
    with pytest.raises(ValidationError):
        AdvancedScanFields(**{field_name: -1.0})


def test_backoff_base_greater_than_max_rejected():
    with pytest.raises(ValidationError, match="retry_backoff_base_seconds"):
        AdvancedScanFields(
            retry_backoff_base_seconds=10.0, retry_backoff_max_seconds=5.0
        )


def test_existing_shipped_timeout_fields_still_bounded_at_300():
    """The 3 pre-Phase-198 timeout fields were NOT widened to 1-600 (D-11)."""
    with pytest.raises(ValidationError):
        AdvancedScanFields(timeout_default_seconds=301)
    with pytest.raises(ValidationError):
        AdvancedScanFields(timeout_tls_seconds=301)
    with pytest.raises(ValidationError):
        AdvancedScanFields(timeout_ssh_seconds=301)


def test_tls_designated_ports_unknown_key_still_extra_forbid():
    """extra="forbid" is unchanged — an unrelated unknown key still 422s
    even with the new fields present."""
    with pytest.raises(ValidationError):
        AdvancedScanFields(bogus_new_field=1)
