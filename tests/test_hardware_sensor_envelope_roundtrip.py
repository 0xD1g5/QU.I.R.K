"""Phase 158 Plan 02 (HWLC-15) — sensor to hard console-side receiver schema round-trip.

Proves a populated ``HardwareDevice`` row survives ``_hardware_device_to_dict()`` ->
``_build_envelope()`` -> JSON serialize -> JSON parse -> ``PushEnvelope(**envelope)``
unchanged, under the console's ``model_config = ConfigDict(extra="ignore")`` contract.

This is the guard that prevents ``_build_envelope()`` (sensor/quirk/cli/sensor_cmd.py)
and ``PushEnvelope`` (console/quirk/dashboard/api/routes/sensor.py) from drifting apart
silently — a column added to one side and not the other would previously be dropped
with no test failure anywhere in the suite.

No network, no filesystem, no DB fixtures — pure in-memory ORM objects and dict/Pydantic
assertions, matching the existing test_sensor_windows_smoke.py style.
"""
from __future__ import annotations

import datetime as _dt
import json

from quirk.cli.sensor_cmd import _build_envelope, _hardware_device_to_dict
from quirk.dashboard.api.routes.sensor import PushEnvelope
from quirk.models import HardwareDevice

SAMPLE_SENSOR_CFG = {
    "sensor_version": "5.14.0-dev",
    "sensor_id": "test-sensor-uuid-1234",
    "segment": "dmz",
}


def _make_hardware_device() -> HardwareDevice:
    """Build a fully-populated in-memory HardwareDevice with distinctive sentinel
    values across every family (SSH/HTTP baseline, SNMP, Modbus, BACnet,
    bridge-evidence, Phase-154 identity). No DB, no network.
    """
    return HardwareDevice(
        host="switch-42.lab.example.com",
        port=22,
        vendor="Cisco",
        model="Catalyst-9300",
        pqc_status="unsupported",
        eol_date=_dt.date(2027, 6, 30),
        confidence="high",
        fingerprint_method="ssh_banner",
        raw_banner="SSH-2.0-Cisco-1.25",
        scanned_at=_dt.datetime(2026, 8, 16, 12, 0, 0),
        remediation_tier="Tier 1",
        snmp_sysdescr="Cisco IOS Software, Catalyst L3 Switch",
        snmp_sysname="switch-42",
        snmp_sysobjectid="1.3.6.1.4.1.9.1.2494",
        snmp_vendor="Cisco",
        snmp_version="v3",
        snmp_auth_protocol="SHA256",
        snmp_priv_protocol="AES256",
        bridge_evidence_json="target_ip=10.0.0.5;mac=aa:bb:cc:dd:ee:ff",
        bridge_confirmed_at=_dt.datetime(2026, 8, 15, 9, 30, 0),
        modbus_vendor="Schneider Electric",
        modbus_model="M221",
        modbus_firmware="1.2.3",
        modbus_probe_state="identified",
        bacnet_vendor="Johnson Controls",
        bacnet_model="FX16",
        bacnet_firmware="9.0",
        bacnet_probe_state="identified",
        ssh_host_key_fingerprint="SHA256:abcdef1234567890abcdef1234567890abcdef1234",
        match_confidence="high",
        probe_status="success",
    )


def _build_populated_envelope() -> dict:
    dev = _make_hardware_device()
    return _build_envelope(SAMPLE_SENSOR_CFG, [], hardware_devices=[dev])


# ---------------------------------------------------------------------------
# 1. Full round-trip: device dict survives _build_envelope -> JSON -> PushEnvelope
# ---------------------------------------------------------------------------


def test_hardware_device_round_trips_through_push_envelope():
    envelope = _build_populated_envelope()
    parsed = json.loads(json.dumps(envelope))
    env = PushEnvelope(**parsed)

    assert len(env.hardware_devices) == 1
    device = env.hardware_devices[0]

    # D-158-D: one representative field per family, spot-checked (not all ~30 columns)
    assert device["vendor"] == "Cisco"
    assert device["raw_banner"] == "SSH-2.0-Cisco-1.25"
    assert device["snmp_sysdescr"] == "Cisco IOS Software, Catalyst L3 Switch"
    assert device["modbus_firmware"] == "1.2.3"
    assert device["bacnet_vendor"] == "Johnson Controls"
    assert device["bridge_evidence_json"] == "target_ip=10.0.0.5;mac=aa:bb:cc:dd:ee:ff"
    assert device["ssh_host_key_fingerprint"] == (
        "SHA256:abcdef1234567890abcdef1234567890abcdef1234"
    )


# ---------------------------------------------------------------------------
# 2. Omitted key parses as None, never []
# ---------------------------------------------------------------------------


def test_omitted_hardware_devices_parses_as_none():
    envelope = _build_populated_envelope()
    del envelope["hardware_devices"]
    env = PushEnvelope(**envelope)
    assert env.hardware_devices is None


# ---------------------------------------------------------------------------
# 3. Confirmed-empty ([]) stays distinct from omitted (None)
# ---------------------------------------------------------------------------


def test_empty_hardware_devices_is_distinct_from_omitted():
    envelope = _build_envelope(SAMPLE_SENSOR_CFG, [], hardware_devices=[])
    env = PushEnvelope(**envelope)
    # ROADMAP success criterion 2: field-absent is structurally distinguishable
    # from confirmed-zero.
    assert env.hardware_devices == []
    assert env.hardware_devices is not None


# ---------------------------------------------------------------------------
# 4. Device dict excludes identity/PK columns
# ---------------------------------------------------------------------------


def test_device_dict_excludes_identity_and_pk_columns():
    dev = _make_hardware_device()
    d = _hardware_device_to_dict(dev)
    for excluded_key in ("id", "scan_id", "sensor_id", "segment"):
        assert excluded_key not in d


# ---------------------------------------------------------------------------
# 5. Column coverage — future-proofing gate
# ---------------------------------------------------------------------------


def test_device_dict_covers_all_hardware_device_columns():
    dev = _make_hardware_device()
    d = _hardware_device_to_dict(dev)
    model_columns = {c.name for c in HardwareDevice.__table__.columns}
    expected = model_columns - {"id", "scan_id"}
    assert set(d.keys()) == expected


# ---------------------------------------------------------------------------
# 6. JSON-serializable, backslash-free (mirrors Windows-smoke convention)
# ---------------------------------------------------------------------------


def test_envelope_is_json_serializable_and_backslash_free():
    envelope = _build_populated_envelope()
    serialized = json.dumps(envelope)
    assert chr(92) not in serialized


# ---------------------------------------------------------------------------
# 7. Zero devices produces an empty list, not a missing key
# ---------------------------------------------------------------------------


def test_zero_devices_produces_empty_list_not_missing_key():
    envelope = _build_envelope(SAMPLE_SENSOR_CFG, [], [])
    assert "hardware_devices" in envelope
    assert envelope["hardware_devices"] == []
