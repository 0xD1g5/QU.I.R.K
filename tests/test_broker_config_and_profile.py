"""Phase 33 / Plan 02: broker config flag + profile gating regression tests."""
from types import SimpleNamespace

from quirk.config import ConnectorsCfg, ScanCfg, config_from_dict
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
