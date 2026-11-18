"""Phase 239 TRUST-01 / SC#1 / D-07: one target shape for every list-typed connector field.

The field set is enumerated at run time from ``ConnectorsCfg`` with this
file's own walk, never by name, so a field added later is covered without
editing this test.  For every field a scalar value must load as a
one-element list, and the hosts the trust gate reads must equal the hosts of
the elements the scanner iterates.
"""
from __future__ import annotations

import dataclasses
import inspect
import re
import typing
from types import SimpleNamespace

import pytest
import yaml

from quirk.config import ConnectorsCfg, config_from_dict, load_config
from quirk.util import target_trust as _tt


def _is_list_type(t) -> bool:
    if isinstance(t, str):
        return re.match(r"(typing\.)?(List|list)\b", t) is not None
    return t is list or typing.get_origin(t) is list


LIST_FIELDS = [f.name for f in dataclasses.fields(ConnectorsCfg) if _is_list_type(f.type)]
BROKER_FIELDS = {"broker_targets", "broker_azure_namespaces", "broker_sqs_regions"}

_MAPPING = {"dc01.example": 1}
SHAPES = [
    ("scalar", "h.example:443", ["h.example:443"]),
    ("int", 123, [123]),
    ("mapping", _MAPPING, [_MAPPING]),
    ("bool", True, [True]),
    ("none", None, []),
    ("empty", "", []),
    ("tuple", ("a.example", "b.example"), ["a.example", "b.example"]),
    ("frozenset", frozenset({"a.example"}), ["a.example"]),
]


def _write_cfg(tmp_path, connectors):
    p = tmp_path / "cfg.yaml"
    doc = {
        "assessment": {
            "name": "target-shape-test",
            "data_classification": "internal",
            "report_owner": "tester",
            "timezone": "UTC",
        },
        "scan": {"concurrency": 50, "ports_tls": [443]},
        "output": {
            "directory": str(tmp_path / "out"),
            "db_path": str(tmp_path / "out" / "quirk.db"),
        },
        "connectors": connectors,
    }
    p.write_text(yaml.safe_dump(doc), encoding="utf-8")
    return str(p)


def _raw(connectors):
    return {
        "assessment": {
            "name": "t",
            "data_classification": "internal",
            "report_owner": "t",
            "timezone": "UTC",
        },
        "scan": {"timeout_seconds": 5, "concurrency": 200, "ports_tls": [443]},
        "targets": {"fqdns": [], "cidrs": [], "include_ips": [], "exclude_ips": []},
        "output": {"directory": "/tmp/quirk-test", "db_path": "/tmp/quirk-test.db"},
        "connectors": connectors,
    }


def test_list_field_enumeration_is_not_vacuous():
    assert len(LIST_FIELDS) >= 17, LIST_FIELDS
    assert {"jwt_targets", "azure_keyvault_urls", "kerberos_targets", "broker_targets"} <= set(LIST_FIELDS)
    assert "_user_set_fields" not in LIST_FIELDS
    assert "snmp_v3_credentials" not in LIST_FIELDS


@pytest.mark.parametrize("field", LIST_FIELDS)
def test_scalar_loads_as_one_element_and_gate_sees_scanner_set(tmp_path, field):
    cfg = load_config(_write_cfg(tmp_path, {field: "h.example:443"}))
    value = getattr(cfg.connectors, field)
    assert value == ["h.example:443"]
    disposition = _tt.CONNECTOR_HOST_FIELD_DISPOSITION.get(field)
    assert disposition is not None, f"{field} has no gate disposition"
    gate = [h for f, h in _tt.connector_host_values(cfg.connectors) if f == field]
    if disposition == "check":
        assert gate == [_tt._extract_host(e) for e in value]
    elif disposition == "check-registry":
        assert gate == [h for h in (_tt._registry_host(e) for e in value) if h]


@pytest.mark.parametrize("field", LIST_FIELDS)
@pytest.mark.parametrize("shape", SHAPES, ids=[s[0] for s in SHAPES])
def test_direct_construction_coerces_shapes(field, shape):
    _, given, expected = shape
    value = getattr(ConnectorsCfg(**{field: given}), field)
    assert value == expected
    if shape[0] == "mapping":
        assert value[0] is given


def test_list_value_is_kept_as_same_object():
    v = ["a.example"]
    assert ConnectorsCfg(jwt_targets=v).jwt_targets is v


@pytest.mark.parametrize("field", [f for f in LIST_FIELDS if f not in BROKER_FIELDS])
@pytest.mark.parametrize("shape", SHAPES, ids=[s[0] for s in SHAPES])
def test_config_from_dict_coerces_shapes(field, shape):
    _, given, expected = shape
    cfg = config_from_dict(_raw({field: given}))
    assert getattr(cfg.connectors, field) == expected


def test_kerberos_coercion_block_removed():
    import quirk.config as qc

    assert 'conn_raw["kerberos_targets"]' not in inspect.getsource(qc.config_from_dict)


def test_code_and_test_enumerations_agree():
    from quirk.config import _is_list_annotation

    code = [f.name for f in dataclasses.fields(ConnectorsCfg) if _is_list_annotation(f.type)]
    assert sorted(code) == sorted(LIST_FIELDS)


def test_enforce_reads_scalar_trusted_targets_whole():
    from quirk.util.target_trust import enforce_trusted_targets

    cfg = SimpleNamespace(
        security=SimpleNamespace(trusted_targets="10.0.0.0/8", allow_internal_targets=False),
        targets=SimpleNamespace(fqdns=["10.1.2.3"], cidrs=[], include_ips=[], exclude_ips=[]),
        connectors=SimpleNamespace(),
    )
    enforce_trusted_targets(cfg)
