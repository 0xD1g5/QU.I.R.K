"""Phase 179 / Plan 02 — REMED-03: remediation_aliases config parsing tests.

`remediation_aliases:` is the human-in-the-loop mechanism that carries the re-scan
matching burden REMED-03 deliberately refuses to automate (D-10). It is a plain
Dict[str, str], defensively coerced from raw YAML, with zero runtime write paths.

This file is separate from tests/test_config.py to avoid line-drift in
tests/skip_registry.py, which allows the carried DEFER-172-01 failure by
(file, LINENO).
"""

from quirk.config import config_from_dict

# Minimal raw config dict that satisfies config_from_dict()'s required fields
# (mirrors the _MINIMAL_RAW pattern in tests/test_broker_config_and_profile.py).
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


def test_remediation_aliases_defaults_to_empty_dict():
    """No remediation_aliases key in config yields {} — not None."""
    raw = dict(_MINIMAL_RAW)
    cfg = config_from_dict(raw)
    assert cfg.remediation_aliases == {}


def test_remediation_aliases_hydrates_str_mapping():
    """A well-formed mapping loads exactly as-is with str keys/values."""
    raw = dict(_MINIMAL_RAW)
    raw["remediation_aliases"] = {"web01.corp.example": "10.0.0.15"}
    cfg = config_from_dict(raw)
    assert cfg.remediation_aliases == {"web01.corp.example": "10.0.0.15"}


def test_remediation_aliases_coerces_non_string_scalars():
    """Non-string scalar values are coerced via str(...)."""
    raw = dict(_MINIMAL_RAW)
    raw["remediation_aliases"] = {"host-01": 12345}
    cfg = config_from_dict(raw)
    assert cfg.remediation_aliases == {"host-01": "12345"}


def test_remediation_aliases_drops_dict_and_list_values():
    """A value that is a dict or list is dropped, not stringified into garbage."""
    raw = dict(_MINIMAL_RAW)
    raw["remediation_aliases"] = {
        "a": "b",
        "bad-dict": {"nested": 1},
        "bad-list": [1, 2, 3],
    }
    cfg = config_from_dict(raw)
    assert cfg.remediation_aliases == {"a": "b"}


def test_remediation_aliases_drops_none_values():
    """A None value is dropped."""
    raw = dict(_MINIMAL_RAW)
    raw["remediation_aliases"] = {"a": "b", "bad-none": None}
    cfg = config_from_dict(raw)
    assert cfg.remediation_aliases == {"a": "b"}


def test_remediation_aliases_drops_empty_or_whitespace_keys():
    """An entry whose key is empty or whitespace-only after strip is dropped."""
    raw = dict(_MINIMAL_RAW)
    raw["remediation_aliases"] = {"a": "b", "": "x", "   ": "y"}
    cfg = config_from_dict(raw)
    assert cfg.remediation_aliases == {"a": "b"}


def test_remediation_aliases_drops_empty_or_whitespace_values():
    """An entry whose coerced value is empty or whitespace-only after strip is dropped."""
    raw = dict(_MINIMAL_RAW)
    raw["remediation_aliases"] = {"a": "b", "empty-val": "", "whitespace-val": "   "}
    cfg = config_from_dict(raw)
    assert cfg.remediation_aliases == {"a": "b"}


def test_remediation_aliases_non_mapping_shape_yields_empty_dict():
    """A remediation_aliases value that is not a mapping at all yields {} without raising."""
    for bad_shape in ([1, 2, 3], "not-a-mapping", None):
        raw = dict(_MINIMAL_RAW)
        raw["remediation_aliases"] = bad_shape
        cfg = config_from_dict(raw)
        assert cfg.remediation_aliases == {}


def test_remediation_aliases_kitchen_sink():
    """Combined malformed-input case from the plan's acceptance criteria."""
    raw = dict(_MINIMAL_RAW)
    raw["remediation_aliases"] = {"a": "b", "": "x", "c": {"nested": 1}}
    cfg = config_from_dict(raw)
    assert cfg.remediation_aliases == {"a": "b"}


def test_remediation_aliases_does_not_alter_other_fields():
    """Loading remediation_aliases does not affect other AppConfig fields."""
    raw_without = dict(_MINIMAL_RAW)
    raw_with = dict(_MINIMAL_RAW)
    raw_with["remediation_aliases"] = {"web01.corp.example": "10.0.0.15"}

    cfg_without = config_from_dict(raw_without)
    cfg_with = config_from_dict(raw_with)

    assert cfg_without.assessment == cfg_with.assessment
    assert cfg_without.scan == cfg_with.scan
    assert cfg_without.targets == cfg_with.targets
    assert cfg_without.connectors == cfg_with.connectors
    assert cfg_without.output == cfg_with.output
    assert cfg_without.security == cfg_with.security
    assert cfg_without.broker_credentials == cfg_with.broker_credentials
