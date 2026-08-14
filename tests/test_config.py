"""Phase 100 — FMT-01 / D-01: AssessmentCfg.logo_path backward-compat tests."""

import pytest


def test_assessment_cfg_logo_path():
    """AssessmentCfg accepts logo_path as an optional kwarg without raising."""
    from quirk.config import AssessmentCfg
    cfg = AssessmentCfg(
        name="Test Org",
        data_classification="CONFIDENTIAL",
        report_owner="Security Team",
        timezone="UTC",
        logo_path="/tmp/x.png",
    )
    assert cfg.logo_path == "/tmp/x.png"


def test_backward_compat_config():
    """AssessmentCfg constructed without logo_path must not raise; .logo_path is None."""
    from quirk.config import AssessmentCfg
    cfg = AssessmentCfg(
        name="Test Org",
        data_classification="CONFIDENTIAL",
        report_owner="Security Team",
        timezone="UTC",
    )
    assert cfg.logo_path is None


# ---------------------------------------------------------------------------
# Phase 139 — SNMPV3-01 / D-02: SnmpV3Credential config-load + protocol
# validation RED tests. quirk.config.SnmpV3Credential does not exist yet;
# these fail until Plan 139-01 adds the dataclass/loader/validation.
# ---------------------------------------------------------------------------

# Minimal raw config dict that satisfies config_from_dict()'s required fields
# (mirrors the _MINIMAL_RAW pattern in tests/test_broker_config_and_profile.py).
_SNMP_V3_MINIMAL_RAW = {
    "assessment": {
        "name": "test",
        "data_classification": "internal",
        "report_owner": "tester",
        "timezone": "UTC",
    },
    "scan": {
        "timeout_seconds": 5,
        "concurrency": 200,
        "ports_tls": [443],
    },
    "targets": {
        "fqdns": [],
        "cidrs": [],
        "include_ips": [],
        "exclude_ips": [],
    },
    "output": {
        "directory": "/tmp/quirk-test",
        "db_path": "/tmp/quirk-test.db",
    },
}


# ---------------------------------------------------------------------------
# Phase 154 — HWLC-03 / D-11: ScanCfg.hardware_history_retention_days
# ---------------------------------------------------------------------------


def test_scan_cfg_hardware_history_retention_days_default():
    """ScanCfg defaults hardware_history_retention_days to 180 (D-11)."""
    from quirk.config import ScanCfg

    cfg = ScanCfg(concurrency=200, ports_tls=[443])
    assert cfg.hardware_history_retention_days == 180


def test_scan_cfg_hardware_history_retention_days_yaml_override():
    """A `scan:` YAML block setting hardware_history_retention_days flows
    through config_from_dict()'s **scan_raw passthrough with no loader edit."""
    from quirk.config import config_from_dict

    raw = dict(_SNMP_V3_MINIMAL_RAW)
    raw["scan"] = dict(raw["scan"])
    raw["scan"]["hardware_history_retention_days"] = 30

    cfg = config_from_dict(raw)

    assert cfg.scan.hardware_history_retention_days == 30


def test_snmp_v3_credentials_load_by_host():
    """SNMPV3-01: connectors.snmp_v3_credentials loads into a
    Dict[str, SnmpV3Credential] keyed by bare host, with env-var NAMES
    (never resolved secret VALUES) in the key fields — mirrors the
    BrokerCredential per-host pattern.
    """
    from quirk.config import SnmpV3Credential, config_from_dict  # noqa — will fail until Plan 139-01

    raw = dict(_SNMP_V3_MINIMAL_RAW)
    raw["connectors"] = {
        "snmp_v3_credentials": {
            "10.0.0.1": {
                "username": "u",
                "auth_key_env": "SNMP_AUTH",
                "priv_key_env": "SNMP_PRIV",
                "auth_protocol": "SHA",
                "priv_protocol": "AES",
            },
        },
    }

    cfg = config_from_dict(raw)

    creds = cfg.connectors.snmp_v3_credentials
    assert "10.0.0.1" in creds, (
        f"snmp_v3_credentials must be keyed by bare host '10.0.0.1'. Got keys: {sorted(creds)}"
    )
    cred = creds["10.0.0.1"]
    assert isinstance(cred, SnmpV3Credential), (
        f"snmp_v3_credentials entries must be SnmpV3Credential instances, got: {type(cred)}"
    )
    assert cred.username == "u"
    assert cred.auth_key_env == "SNMP_AUTH", (
        "auth_key_env must store the env-var NAME 'SNMP_AUTH', never a resolved secret value"
    )
    assert cred.priv_key_env == "SNMP_PRIV", (
        "priv_key_env must store the env-var NAME 'SNMP_PRIV', never a resolved secret value"
    )


def test_snmp_v3_credentials_reject_weak_protocols():
    """D-02: SnmpV3Credential/config loader must reject non-SHA auth or
    non-AES priv protocol values at load time with a clear config error —
    never silently substitute/downgrade to MD5/DES.
    """
    from quirk.config import config_from_dict  # noqa — will fail until Plan 139-01

    raw_md5 = dict(_SNMP_V3_MINIMAL_RAW)
    raw_md5["connectors"] = {
        "snmp_v3_credentials": {
            "10.0.0.2": {
                "username": "u",
                "auth_key_env": "SNMP_AUTH",
                "priv_key_env": "SNMP_PRIV",
                "auth_protocol": "MD5",
                "priv_protocol": "AES",
            },
        },
    }
    with pytest.raises(ValueError):
        config_from_dict(raw_md5)

    raw_des = dict(_SNMP_V3_MINIMAL_RAW)
    raw_des["connectors"] = {
        "snmp_v3_credentials": {
            "10.0.0.3": {
                "username": "u",
                "auth_key_env": "SNMP_AUTH",
                "priv_key_env": "SNMP_PRIV",
                "auth_protocol": "SHA",
                "priv_protocol": "DES",
            },
        },
    }
    with pytest.raises(ValueError):
        config_from_dict(raw_des)
