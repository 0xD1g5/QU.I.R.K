"""Phase 33 / Plan 02: broker config flag + profile gating regression tests."""
from types import SimpleNamespace

import pytest

from quirk.config import ConnectorsCfg, ScanCfg, _parse_host_port, config_from_dict
from quirk.engine.profiles import apply_profile

# Minimal raw config dict that satisfies config_from_dict() required fields.
_MINIMAL_RAW = {
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


def _base_cfg():
    """Minimal duck-type cfg for profile-gating tests. Mirrors Phase 32 _mk_cfg() pattern."""
    return SimpleNamespace(
        scan=ScanCfg(timeout_seconds=5, concurrency=200, ports_tls=[443]),
        connectors=ConnectorsCfg(),
    )


def test_connectors_cfg_defaults():
    """D-10: enable_broker defaults False; cloud target lists default empty."""
    c = ConnectorsCfg()
    assert c.enable_broker is False
    assert c.broker_azure_namespaces == []
    assert c.broker_sqs_regions == []


def test_config_from_dict_hydrates_broker_lists():
    """D-01: broker_azure_namespaces and broker_sqs_regions populate from raw config dict."""
    raw = dict(_MINIMAL_RAW)
    raw["connectors"] = {
        "enable_broker": True,
        "broker_azure_namespaces": ["ns-prod", "ns-staging"],
        "broker_sqs_regions": ["us-east-1", "eu-west-1"],
    }
    cfg = config_from_dict(raw)
    assert cfg.connectors.enable_broker is True
    assert cfg.connectors.broker_azure_namespaces == ["ns-prod", "ns-staging"]
    assert cfg.connectors.broker_sqs_regions == ["us-east-1", "eu-west-1"]


def test_apply_profile_standard_enables_broker():
    """D-10: standard profile sets enable_broker=True (matches email gating)."""
    cfg = _base_cfg()
    assert cfg.connectors.enable_broker is False
    apply_profile(cfg, "standard", safe_mode=False)
    assert cfg.connectors.enable_broker is True


def test_apply_profile_deep_enables_broker():
    """D-10: deep profile sets enable_broker=True."""
    cfg = _base_cfg()
    apply_profile(cfg, "deep", safe_mode=False)
    assert cfg.connectors.enable_broker is True


def test_apply_profile_quick_leaves_broker_disabled():
    """D-10: quick profile does NOT set enable_broker — broker scanning excluded from quick."""
    cfg = _base_cfg()
    apply_profile(cfg, "quick", safe_mode=False)
    assert cfg.connectors.enable_broker is False


# --- Phase 190 / TRIAGE-06: _parse_host_port ---------------------------------

def test_parse_host_port_bare_hostname():
    assert _parse_host_port("kafka.internal", field_name="connectors.broker_targets") == (
        "kafka.internal",
        None,
    )


def test_parse_host_port_host_and_port():
    assert _parse_host_port("localhost:29092", field_name="connectors.broker_targets") == (
        "localhost",
        29092,
    )


def test_parse_host_port_bracketed_ipv6_with_port():
    assert _parse_host_port("[::1]:29092", field_name="connectors.broker_targets") == (
        "::1",
        29092,
    )


def test_parse_host_port_bare_ipv6_no_port():
    assert _parse_host_port("::1", field_name="connectors.broker_targets") == ("::1", None)


@pytest.mark.parametrize(
    "entry",
    ["host:0", ":70000", "host:abc", "host:80.5", "host:true"],
)
def test_parse_host_port_malformed_port_raises_config_002(entry):
    with pytest.raises(ValueError) as exc_info:
        _parse_host_port(entry, field_name="connectors.broker_targets")
    assert "QRK-CONFIG-002" in str(exc_info.value)
    assert "connectors.broker_targets" in str(exc_info.value)


def test_parse_host_port_ambiguous_unbracketed_ipv6_with_port_raises():
    with pytest.raises(ValueError) as exc_info:
        _parse_host_port("::1:29092", field_name="connectors.broker_targets")
    assert "QRK-CONFIG-002" in str(exc_info.value)


@pytest.mark.parametrize("entry", ["", "   ", ":29092"])
def test_parse_host_port_empty_host_raises(entry):
    with pytest.raises(ValueError) as exc_info:
        _parse_host_port(entry, field_name="connectors.broker_targets")
    assert "QRK-CONFIG-002" in str(exc_info.value)


# --- Phase 190 / TRIAGE-06: connectors.broker_targets config surface --------

def test_connectors_cfg_broker_targets_defaults_empty():
    assert ConnectorsCfg().broker_targets == []


def test_broker_targets_in_known_connector_keys():
    """A new dataclass field is auto-recognized — no manual registration needed."""
    from quirk.config import _KNOWN_CONNECTOR_KEYS

    assert "broker_targets" in _KNOWN_CONNECTOR_KEYS


def test_config_from_dict_no_broker_targets_key_is_backward_compatible():
    raw = dict(_MINIMAL_RAW)
    raw["connectors"] = {"enable_broker": True}
    cfg = config_from_dict(raw)
    assert cfg.connectors.broker_targets == []
    assert cfg.connectors.enable_broker is True


def test_config_from_dict_broker_targets_scalar_coerces_to_list():
    raw = dict(_MINIMAL_RAW)
    raw["connectors"] = {"broker_targets": "localhost:29092"}
    cfg = config_from_dict(raw)
    assert cfg.connectors.broker_targets == ["localhost:29092"]


def test_config_from_dict_broker_targets_list_loads_cleanly():
    raw = dict(_MINIMAL_RAW)
    raw["connectors"] = {"broker_targets": ["localhost:29092", "kafka.internal"]}
    cfg = config_from_dict(raw)
    assert cfg.connectors.broker_targets == ["localhost:29092", "kafka.internal"]


def test_config_from_dict_broker_targets_malformed_port_raises_at_load_time():
    raw = dict(_MINIMAL_RAW)
    raw["connectors"] = {"broker_targets": ["localhost:notaport"]}
    with pytest.raises(ValueError) as exc_info:
        config_from_dict(raw)
    assert "QRK-CONFIG-002" in str(exc_info.value)
    assert "connectors.broker_targets" in str(exc_info.value)
