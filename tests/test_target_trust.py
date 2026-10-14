"""Tests for quirk/util/target_trust.py — Phase 143 / TAIL-02.

Covers the allowlist matcher (``is_target_trusted``) and the single CLI-side
enforcement chokepoint (``enforce_trusted_targets``), per D-03 (empty =
allow-all) and D-06 (exact host/IP + CIDR containment only, no wildcards).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from quirk.util.target_trust import RC_NOT_IN_ALLOWLIST, enforce_trusted_targets, is_target_trusted


def test_empty_allowlist_allows_all():
    """D-03: an empty/absent trusted_targets list allows everything."""
    result = is_target_trusted("1.2.3.4", [])
    assert result.ok is True


def test_exact_and_cidr_matching():
    """D-06: exact string membership and CIDR containment both match."""
    exact = is_target_trusted("host.example.com", ["host.example.com"])
    assert exact.ok is True

    cidr_match = is_target_trusted("10.0.0.5", ["10.0.0.0/24"])
    assert cidr_match.ok is True

    cidr_miss = is_target_trusted("192.168.9.9", ["10.0.0.0/24"])
    assert cidr_miss.ok is False
    assert cidr_miss.reason == RC_NOT_IN_ALLOWLIST


def test_cli_entry_point_enforces():
    """enforce_trusted_targets() raises for out-of-allowlist CLI targets, is a
    no-op when trusted_targets is empty (D-03)."""
    cfg = SimpleNamespace(
        security=SimpleNamespace(trusted_targets=["10.0.0.0/24"]),
        targets=SimpleNamespace(fqdns=[], cidrs=["192.168.9.0/24"]),
    )
    with pytest.raises(ValueError):
        enforce_trusted_targets(cfg)

    cfg_open = SimpleNamespace(
        security=SimpleNamespace(trusted_targets=[]),
        targets=SimpleNamespace(fqdns=["anything.example.com"], cidrs=[]),
    )
    enforce_trusted_targets(cfg_open)  # must not raise


def test_enforce_trusted_targets_rejects_out_of_allowlist_broker_host():
    """T-190-01 (Phase 190): a connectors.broker_targets host outside the
    allowlist is rejected by the same chokepoint as targets.fqdns/cidrs."""
    cfg = SimpleNamespace(
        security=SimpleNamespace(trusted_targets=["10.0.0.0/24"]),
        targets=SimpleNamespace(fqdns=[], cidrs=[]),
        connectors=SimpleNamespace(broker_targets=["evil.example.com:29092"]),
    )
    with pytest.raises(ValueError):
        enforce_trusted_targets(cfg)


def test_enforce_trusted_targets_allows_in_allowlist_broker_host():
    cfg = SimpleNamespace(
        security=SimpleNamespace(trusted_targets=["kafka.internal"]),
        targets=SimpleNamespace(fqdns=[], cidrs=[]),
        connectors=SimpleNamespace(broker_targets=["kafka.internal:29092"]),
    )
    enforce_trusted_targets(cfg)  # must not raise


def test_enforce_trusted_targets_empty_allowlist_allows_broker_host():
    """D-03: empty allowlist is allow-all, including for broker_targets hosts."""
    cfg = SimpleNamespace(
        security=SimpleNamespace(trusted_targets=[]),
        targets=SimpleNamespace(fqdns=[], cidrs=[]),
        connectors=SimpleNamespace(broker_targets=["anything.example.com:29092"]),
    )
    enforce_trusted_targets(cfg)  # must not raise


def test_enforce_trusted_targets_unchanged_with_no_broker_targets():
    """Backward compatibility: cfg with no connectors attribute at all behaves
    exactly as before (no AttributeError, no behavior change)."""
    cfg = SimpleNamespace(
        security=SimpleNamespace(trusted_targets=["10.0.0.0/24"]),
        targets=SimpleNamespace(fqdns=[], cidrs=["10.0.0.0/24"]),
    )
    enforce_trusted_targets(cfg)  # must not raise; no connectors attr present


# ---------------------------------------------------------------------------
# Phase 225.1 / SECH-03 (D-07, D-26): include_ips + dispositioned connector hosts
# ---------------------------------------------------------------------------
import dataclasses
import re

from quirk.util import target_trust as _tt

_HOST_SHAPED = re.compile(
    r"(_targets|_addr|_url|_urls|_namespaces|_regions|_clusters|_resolver|_endpoint_url)$"
)


def _table():
    return getattr(_tt, "CONNECTOR_HOST_FIELD_DISPOSITION", {})


_CHECK_FIELDS = sorted(k for k, v in _table().items() if v == "check")


def _cfg(trusted, connectors=None, include_ips=None):
    targets = SimpleNamespace(fqdns=[], cidrs=[])
    if include_ips is not None:
        targets.include_ips = include_ips
    return SimpleNamespace(
        security=SimpleNamespace(trusted_targets=trusted),
        targets=targets,
        connectors=SimpleNamespace(**(connectors or {})),
    )


def test_include_ips_is_checked():
    with pytest.raises(ValueError):
        enforce_trusted_targets(_cfg(["127.0.0.1"], include_ips=["127.0.0.2"]))
    enforce_trusted_targets(_cfg(["127.0.0.1"], include_ips=["127.0.0.1"]))


def test_check_fields_not_empty():
    assert len(_CHECK_FIELDS) >= 10


@pytest.mark.parametrize("field_name", _CHECK_FIELDS)
def test_untrusted_connector_field_refused_and_named(field_name):
    value = "untrusted.invalid"
    cfg = _cfg(["trusted.invalid"], {field_name: [value] if field_name.endswith("s") else value})
    with pytest.raises(ValueError, match=field_name):
        enforce_trusted_targets(cfg)


@pytest.mark.parametrize("field_name", _CHECK_FIELDS)
def test_trusted_connector_field_passes(field_name):
    cfg = _cfg(["trusted.invalid"], {field_name: ["trusted.invalid"] if field_name.endswith("s") else "trusted.invalid"})
    enforce_trusted_targets(cfg)


def test_disabled_connector_still_checked():
    cfg = _cfg(["t.example"], {"enable_jwt": False, "jwt_targets": ["https://evil.example/x"]})
    with pytest.raises(ValueError, match="jwt_targets"):
        enforce_trusted_targets(cfg)


@pytest.mark.parametrize(
    "raw,host",
    [
        ("https://idp.example/metadata", "idp.example"),
        ("ldaps://ca.example:636", "ca.example"),
        ("[2001:db8::5]:5671", "2001:db8::5"),
        ("db.example:5432", "db.example"),
        ({"host": "x"}, "x"),
        ("bare.example", "bare.example"),
    ],
)
def test_extract_host_shapes(raw, host):
    assert _tt._extract_host(raw) == host


def test_unparseable_checked_whole_and_fails_closed():
    cfg = _cfg(["t.example"], {"saml_targets": ["not a host!!"]})
    with pytest.raises(ValueError):
        enforce_trusted_targets(cfg)


def test_empty_allowlist_allows_connector_hosts():
    enforce_trusted_targets(_cfg([], {"jwt_targets": ["evil.example"]}))


@pytest.mark.parametrize(
    "ref,host",
    [
        ("registry.internal:5000/app:1", "registry.internal"),
        ("localhost/app", "localhost"),
        ("ghcr.io/org/app", "ghcr.io"),
        ("nginx:1.25", None),
        ("library/nginx", None),
    ],
)
def test_registry_host(ref, host):
    assert _tt._registry_host(ref) == host


def test_container_registry_host_checked():
    with pytest.raises(ValueError, match="container_targets"):
        enforce_trusted_targets(_cfg(["t.example"], {"container_targets": ["evil.example/app:1"]}))
    enforce_trusted_targets(_cfg(["t.example"], {"container_targets": ["nginx:1.25"]}))


def test_dnssec_dispositions():
    t = _table()
    assert t["dnssec_targets"] == "check"
    assert t["dnssec_resolver"].startswith("exempt: ")


def test_every_host_shaped_connector_field_is_dispositioned():
    from quirk.config import ConnectorsCfg

    matched = [f.name for f in dataclasses.fields(ConnectorsCfg) if _HOST_SHAPED.search(f.name)]
    print("host-shaped ConnectorsCfg fields matched:", len(matched))
    assert len(matched) >= 15, matched
    table = _table()
    offenders = [n for n in matched if n not in table]
    bad = [
        n for n, v in table.items()
        if not (v in ("check", "check-registry") or (v.startswith("exempt: ") and v[8:].strip()))
    ]
    assert not offenders, f"undispositioned host-shaped fields: {offenders}"
    assert not bad, f"malformed dispositions: {bad}"
