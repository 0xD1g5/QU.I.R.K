"""Phase 193 / PARITY-02 / PARITY-03: validator coverage for
`ScanSubmitRequest.connectors` and `.credentials`.

Both expected-value sets are derived at test-run time from the same
expressions the schema validators themselves consult
(`dataclasses.fields(ConnectorsCfg)` and `CREDENTIAL_REGISTRY`), never a
hand-written list, per CLAUDE.md's repeated "a written list of known sites
is not a safeguard" lesson.

pytest -q tests/test_schemas_connector_credential_fields.py
"""
from __future__ import annotations

import dataclasses

import pydantic
import pytest

from quirk.config import ConnectorsCfg
from quirk.config_redaction import CREDENTIAL_REGISTRY
from quirk.dashboard.api.schemas import ScanSubmitRequest


def _known_connector_toggle_keys() -> set[str]:
    """Every enable_* ConnectorsCfg field, derived at run time -- never a
    hand-written list."""
    return {
        f.name
        for f in dataclasses.fields(ConnectorsCfg)
        if f.name.startswith("enable_")
    }


def _known_connector_non_toggle_keys() -> set[str]:
    """Every non-enable_* ConnectorsCfg field, derived at run time."""
    return {
        f.name
        for f in dataclasses.fields(ConnectorsCfg)
        if not f.name.startswith("enable_")
    }


def _known_credential_names() -> set[str]:
    """Every CREDENTIAL_REGISTRY entry name whose section is "connectors",
    derived at run time -- never a hand-written list."""
    return {entry.name for entry in CREDENTIAL_REGISTRY if entry.section == "connectors"}


# ---------------------------------------------------------------------------
# 1. Every known enable_* toggle is accepted
# ---------------------------------------------------------------------------


def test_every_known_connector_toggle_key_is_accepted():
    toggles = _known_connector_toggle_keys()
    assert toggles, "expected at least one enable_* ConnectorsCfg field"
    for key in toggles:
        req = ScanSubmitRequest(targets="example.com", connectors={key: True})
        assert req.connectors == {key: True}


# ---------------------------------------------------------------------------
# 2. Unknown connector key rejected, message names the offending key
# ---------------------------------------------------------------------------


def test_unknown_connector_key_rejected_with_key_named():
    with pytest.raises(pydantic.ValidationError) as exc_info:
        ScanSubmitRequest(targets="example.com", connectors={"enable_totally_bogus": True})
    assert "enable_totally_bogus" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 3. Known-but-non-toggle connector field names rejected
# ---------------------------------------------------------------------------


# Phase 197 / D-09: `broker_targets` was rejected pre-Phase-197 (the overlay
# only accepted enable_* toggles) -- it is now one of the 37 widened detail
# fields (CONTEXT D-03) and is therefore intentionally REMOVED from this
# rejection parametrization; it is asserted-accepted instead by
# `test_connector_detail_overlay_lockstep.py`'s PAYLOAD_CASES. `adcs_password`
# remains rejected: it is a true secret (D-04) that rides the Phase-193
# env-var credential path, never this overlay, and is deliberately excluded
# from `_CONNECTOR_DETAIL_KEY_TYPES`.
@pytest.mark.parametrize("key", ["adcs_password"])
def test_known_non_toggle_connector_field_rejected(key: str):
    # Sanity: the key must be a real (non-enable_*) ConnectorsCfg field --
    # if it is renamed/removed, this test should fail loudly rather than
    # silently pass on a key that was never a valid field to begin with.
    assert key in _known_connector_non_toggle_keys()
    with pytest.raises(pydantic.ValidationError):
        ScanSubmitRequest(targets="example.com", connectors={key: True})


def test_broker_targets_now_accepted_as_widened_detail_field():
    """Phase 197 / PARITY-05 / D-03 regression lock: `broker_targets` moved
    from "rejected" to "accepted list[str] detail field" -- this test
    replaces the old rejection assertion removed from the parametrization
    above so the behavior change is proven, not just silently dropped."""
    req = ScanSubmitRequest(
        targets="example.com", connectors={"broker_targets": ["kafka.example.com"]}
    )
    assert req.connectors == {"broker_targets": ["kafka.example.com"]}


# ---------------------------------------------------------------------------
# 4. credentials accepts every registry-derived "connectors"-section name
# ---------------------------------------------------------------------------


def test_every_known_credential_registry_name_is_accepted():
    names = _known_credential_names()
    assert names, "expected at least one connectors-section CREDENTIAL_REGISTRY entry"
    for name in names:
        req = ScanSubmitRequest(targets="example.com", credentials={name: "value"})
        assert req.credentials == {name: "value"}


# ---------------------------------------------------------------------------
# 5. broker:<host> / snmpv3:<host>:auth|priv shapes accepted; arbitrary
#    unknown key rejected
# ---------------------------------------------------------------------------


def test_broker_and_snmpv3_shaped_keys_accepted():
    req = ScanSubmitRequest(
        targets="example.com",
        credentials={
            "broker:kafka.example.com": "s3cr3t",
            "snmpv3:switch1.example.com:auth": "authpass",
            "snmpv3:switch1.example.com:priv": "privpass",
        },
    )
    assert req.credentials is not None
    assert req.credentials["broker:kafka.example.com"] == "s3cr3t"
    assert req.credentials["snmpv3:switch1.example.com:auth"] == "authpass"
    assert req.credentials["snmpv3:switch1.example.com:priv"] == "privpass"


def test_username_shaped_keys_accepted():
    """Phase 193 review CR-03: username keys (identifiers, not secrets) ride
    the same credentials map -- `broker:<host>:user` matches the existing
    `broker:` prefix rule; `snmpv3:<host>:username` needed a validator
    extension."""
    req = ScanSubmitRequest(
        targets="example.com",
        credentials={
            "broker:default:user": "alice",
            "snmpv3:default:username": "bob",
        },
    )
    assert req.credentials is not None
    assert req.credentials["broker:default:user"] == "alice"
    assert req.credentials["snmpv3:default:username"] == "bob"


def test_arbitrary_unknown_credential_key_rejected():
    with pytest.raises(pydantic.ValidationError) as exc_info:
        ScanSubmitRequest(targets="example.com", credentials={"totally_unknown_field": "x"})
    assert "totally_unknown_field" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 6. api_token explicitly rejected as a scan credential
# ---------------------------------------------------------------------------


def test_api_token_rejected_as_scan_credential():
    with pytest.raises(pydantic.ValidationError) as exc_info:
        ScanSubmitRequest(targets="example.com", credentials={"api_token": "x"})
    assert "api_token" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 7. Leak-shape guard: a credential VALUE must never appear in a
#    ValidationError raised because of an unrelated invalid connectors key.
# ---------------------------------------------------------------------------


def test_credential_value_never_leaks_into_unrelated_validation_error():
    sentinel = "SENTINEL-DO-NOT-LOG"
    with pytest.raises(pydantic.ValidationError) as exc_info:
        ScanSubmitRequest(
            targets="example.com",
            connectors={"enable_totally_bogus": True},
            credentials={"adcs_password": sentinel},
        )
    assert sentinel not in str(exc_info.value)


# ---------------------------------------------------------------------------
# 8. None default for both fields leaves them None and does not raise
# ---------------------------------------------------------------------------


def test_connectors_and_credentials_default_to_none():
    req = ScanSubmitRequest(targets="example.com")
    assert req.connectors is None
    assert req.credentials is None
