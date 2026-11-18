"""Unit tests of ``parse_target``, the one shared host/port parser of a connector target.

The trust gate reads every ``check`` connector value through it; a value that
does not read as exactly one host and port is refused while trusted_targets
is set.  Hosts are neutral (a.example, b.example, RFC 5737 and RFC 3849).
"""
from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from quirk.config import ConnectorsCfg
from quirk.util import target_trust as tt
from quirk.util.target_trust import (
    AMBIGUOUS_TARGET,
    RC_AMBIGUOUS_TARGET,
    SHAPE_HOST_PORT,
    SHAPE_HOST_PORT_NO_V6,
    SHAPE_LDAP,
    SHAPE_NAME,
    SHAPE_URL,
    AmbiguousTargetError,
    ParsedTarget,
    parse_target,
)

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize(
    "value, shape, kwargs, expected",
    [
        ("ldap://dc.example:389", SHAPE_LDAP, {}, ParsedTarget("dc.example", 389, "ldap")),
        ("ldaps://dc.example", SHAPE_LDAP, {}, ParsedTarget("dc.example", 636, "ldaps")),
        ("LDAP://dc.example", SHAPE_LDAP, {}, ParsedTarget("dc.example", 389, "ldap")),
        ("dc.example", SHAPE_LDAP, {}, ParsedTarget("dc.example", 389, None)),
        ("[2001:db8::1]:389", SHAPE_LDAP, {}, ParsedTarget("2001:db8::1", 389, None)),
        ("ldap://dc.example:389/x", SHAPE_LDAP, {}, ParsedTarget("dc.example", 389, "ldap")),
        ("db.example:5432", SHAPE_HOST_PORT, {"default_port": 5432}, ParsedTarget("db.example", 5432, None)),
        ("db.example", SHAPE_HOST_PORT, {"default_port": 5432}, ParsedTarget("db.example", 5432, None)),
        ("2001:db8::1", SHAPE_HOST_PORT, {}, ParsedTarget("2001:db8::1", None, None)),
        ("[2001:db8::1]", SHAPE_HOST_PORT, {}, ParsedTarget("2001:db8::1", None, None)),
        ("https://svc.example:8443/x", SHAPE_URL, {}, ParsedTarget("svc.example", 8443, "https")),
        ("https://SVC.example/x", SHAPE_URL, {}, ParsedTarget("svc.example", None, "https")),
        ("svc.example:8443", SHAPE_URL, {}, ParsedTarget("svc.example", 8443, None)),
        ("zone.example", SHAPE_NAME, {}, ParsedTarget("zone.example", None, None)),
        ("192.0.2.1", SHAPE_NAME, {}, ParsedTarget("192.0.2.1", None, None)),
        ("2001:db8::1", SHAPE_NAME, {}, ParsedTarget("2001:db8::1", None, None)),
        ("db.example:5432", SHAPE_HOST_PORT_NO_V6, {}, ParsedTarget("db.example", 5432, None)),
    ],
    ids=[f"p{i:02d}" for i in range(17)],
)
def test_parse_target_reads_well_formed_values(value, shape, kwargs, expected):
    assert parse_target(value, shape, **kwargs) == expected


COMMON_REFUSALS = [
    None, 5, "", "   ", " a.example", "a.example ", "a.example b.example", "a.example\tb.example",
    "a.example\nb.example", "a.example\x00", "a.example\ud800", "a.example;b.example",
    "a.example\\b.example", "a.example:0", "a.example:65536", "a.example:abc", "a.example:",
    "a.example:٣٨٩", "a.example:389:extra", "[2001:db8::1", "[a.example]",
    "[2001:db8::1]x", "a.example%2eb.example",
]


@pytest.mark.parametrize("shape", [SHAPE_URL, SHAPE_LDAP, SHAPE_HOST_PORT, SHAPE_HOST_PORT_NO_V6, SHAPE_NAME])
@pytest.mark.parametrize("value", COMMON_REFUSALS, ids=[f"r{i:02d}" for i in range(len(COMMON_REFUSALS))])
def test_parse_target_refuses_what_is_not_one_host_and_port(shape, value):
    with pytest.raises(AmbiguousTargetError):
        parse_target(value, shape)


@pytest.mark.parametrize(
    "value",
    ["a.example:389", "[2001:db8::1]:389", "x@a.example", "a.example/x",
     "a.example?x", "a.example#x", "a.example,b.example", "ldap://a.example", "https://a.example"],
    ids=[f"h{i:02d}" for i in range(9)],
)
def test_name_shape_refuses_every_separator(value):
    with pytest.raises(AmbiguousTargetError):
        parse_target(value, SHAPE_NAME)


@pytest.mark.parametrize(
    "value",
    ["ldap://user@a.example", "ldap://u:p@a.example", "ldap://b.example:389@a.example",
     "ldap://a.example?x", "ldap://a.example#x", "ldap://a.example,b.example", "ldap://:389",
     "ldap:///a.example", "ldap://[a.example]", "postgres://a.example", "https://a.example",
     "ldap://a.example%2fb.example", "x@a.example", "a.example/x", "a.example,b.example"],
    ids=[f"l{i:02d}" for i in range(15)],
)
def test_ldap_shape_refusals(value):
    with pytest.raises(AmbiguousTargetError):
        parse_target(value, SHAPE_LDAP)


@pytest.mark.parametrize(
    "value",
    ["https://u@a.example/", "https://u:p@a.example/", "https://b.example:443@a.example/",
     "https://a.example,b.example/", "https://:443/", "https:///x", "ht tp://a.example",
     "1http://a.example", "https://a.example%2fb.example", "https://[a.example]/",
     "x@a.example", "a.example/x"],
    ids=[f"u{i:02d}" for i in range(12)],
)
def test_url_shape_refusals(value):
    with pytest.raises(AmbiguousTargetError):
        parse_target(value, SHAPE_URL)


@pytest.mark.parametrize(
    "value",
    ["postgres://a.example", "mysql://u:p@a.example:3306", "u@a.example", "u:p@a.example:5432",
     "a.example/x", "a.example?x", "a.example#x", "a.example,b.example", "a.example:5432,b.example:5432",
     "ldap://a.example"],
    ids=[f"d{i:02d}" for i in range(10)],
)
@pytest.mark.parametrize("shape", [SHAPE_HOST_PORT, SHAPE_HOST_PORT_NO_V6])
def test_host_port_shape_refusals(shape, value):
    with pytest.raises(AmbiguousTargetError):
        parse_target(value, shape)


@pytest.mark.parametrize("value", ["2001:db8::1", "[2001:db8::1]", "[2001:db8::1]:5432"], ids=["v0", "v1", "v2"])
def test_no_v6_shape_refuses_ip_literals_with_colons(value):
    with pytest.raises(AmbiguousTargetError):
        parse_target(value, SHAPE_HOST_PORT_NO_V6)
    assert parse_target(value, SHAPE_HOST_PORT).host == "2001:db8::1"


def test_parser_does_not_use_stdlib_url_accessors():
    import inspect

    src = "".join(
        inspect.getsource(f) for f in (tt.parse_target, tt._split_authority, tt._parse_port)
    )
    assert not any(k in src for k in ("urlsplit", "urlparse", ".hostname", ".port"))


def test_connector_host_values_marks_a_refused_value():
    assert tt.connector_host_values({"adcs_targets": ["ldap://u@a.example"]}) == [
        ("adcs_targets", AMBIGUOUS_TARGET)
    ]
    assert tt.connector_host_values({"adcs_targets": ["ldap://a.example"]}) == [("adcs_targets", "a.example")]
    assert tt.connector_host_values({"adcs_targets": [{"host": "ldap://a.example:389"}]}) == [
        ("adcs_targets", "a.example")
    ]
    assert tt.connector_host_values({"adcs_targets": [5]}) == [("adcs_targets", None)]
    assert tt.connector_host_values({"adcs_targets": ["  "]}) == []


def test_ambiguous_marker_is_refused_only_while_an_allowlist_is_set():
    refused = tt.is_target_trusted(AMBIGUOUS_TARGET, ["a.example"])
    assert (refused.ok, refused.reason, refused.redacted_preview) == (False, RC_AMBIGUOUS_TARGET, "")
    assert tt.is_target_trusted(AMBIGUOUS_TARGET, []).ok


def test_refusal_message_names_the_field_and_never_echoes_the_value():
    value = "ldap://user-secret@a.example"
    (_field, marker), = tt.connector_host_values({"adcs_targets": [value]})
    msg = tt.refusal_message(tt.is_target_trusted(marker, ["a.example"]), "adcs_targets")
    assert "(connectors.adcs_targets)" in msg
    assert "user-secret" not in msg and "a.example" not in msg


def test_enforce_trusted_targets_refuses_an_ambiguous_connector_value():
    cfg = SimpleNamespace(
        security=SimpleNamespace(trusted_targets=["a.example"], allow_internal_targets=False),
        targets=SimpleNamespace(fqdns=["a.example"], cidrs=[], include_ips=[], exclude_ips=[]),
        connectors=SimpleNamespace(adcs_targets=["ldap://u@a.example"]),
    )
    with pytest.raises(ValueError, match=r"\(connectors\.adcs_targets\)"):
        tt.enforce_trusted_targets(cfg)
    cfg.security.trusted_targets = []
    tt.enforce_trusted_targets(cfg)


def test_broker_target_hosts_excludes_the_marker():
    cfg = SimpleNamespace(connectors=SimpleNamespace(broker_targets=["mq.example:9093", "mq.example,b.example"]))
    assert tt._broker_target_hosts(cfg) == ["mq.example"]


def test_shape_map_covers_every_check_field():
    check = {
        f.name for f in dataclasses.fields(ConnectorsCfg)
        if tt.CONNECTOR_HOST_FIELD_DISPOSITION.get(f.name) == "check"
    }
    assert set(tt.CONNECTOR_FIELD_TARGET_SHAPE) == check


def test_tracked_configs_have_no_ambiguous_targets():
    names = subprocess.run(
        ["git", "ls-files", "*.yaml", "*.yml"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    parsed = 0
    for name in names:
        try:
            doc = yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"{name} could not be parsed: {type(exc).__name__}")
        parsed += 1
        conn = doc.get("connectors") if isinstance(doc, dict) else None
        if isinstance(conn, dict):
            for field, host in tt.connector_host_values(conn):
                assert host is not AMBIGUOUS_TARGET, f"{name}: connectors.{field}"
    assert parsed >= 2
