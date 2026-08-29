"""Tests for Phase 173-01 — SCOPE-01 CLI-path scope suppression (D-01/D-01a).

`tests/test_profiles.py` covers the ConnectorsCfg._user_set_fields mechanism
in isolation via stub dataclasses; it never asserts the CLI-path OUTCOME (a
user narrowing `scan.ports_tls` in YAML). These tests build configs as raw
dicts through `quirk.config.config_from_dict` — the live load path — because
a direct `ScanCfg(...)` construction bypasses the `_user_set_fields` stamp
and would silently exercise nothing.

No child-process spawning — these are in-process unit tests exercising
config_from_dict and apply_profile directly.
"""
from __future__ import annotations

from quirk.config import config_from_dict
from quirk.engine.profiles import apply_profile


def _raw_config(scan_overrides: dict) -> dict:
    scan = {"concurrency": 50}
    scan.update(scan_overrides)
    return {
        "assessment": {
            "name": "x", "data_classification": "c",
            "report_owner": "o", "timezone": "UTC",
        },
        "scan": scan,
        "targets": {},
        "output": {"directory": ".", "db_path": "x.db"},
    }


def test_narrowed_ports_suppresses_standard_profile_auto_enable():
    """A human-authored narrowed `ports_tls`, no `connectors:` block.

    Falsifiability: fails if the `port_scope_origin` guard is removed from
    profiles.py's standard-email/standard-broker blocks (i.e. reverting to
    plain `if "enable_email" not in user_set: ... = True`).
    """
    cfg = config_from_dict(_raw_config({"ports_tls": [8443]}))
    apply_profile(cfg, "standard")
    assert cfg.connectors.enable_email is False
    assert cfg.connectors.enable_broker is False


def test_explicit_connector_value_wins_over_scope_suppression():
    """Explicit `connectors.enable_email: true` alongside narrowed ports still wins.

    Falsifiability: fails if the explicit-`_user_set_fields` check in
    profiles.py is reordered after (or removed from) the scope-suppression
    guard, breaking D-01's locked precedence (explicit connector value >
    scope suppression > profile auto-enable).
    """
    raw = _raw_config({"ports_tls": [8443]})
    raw["connectors"] = {"enable_email": True}
    cfg = config_from_dict(raw)
    apply_profile(cfg, "standard")
    assert cfg.connectors.enable_email is True


def test_narrowed_ports_suppresses_deep_profile_auto_enable():
    """Same narrowed-ports YAML under the `deep` profile branch.

    Falsifiability: fails if the `port_scope_origin` guard is present only
    in the standard branch and omitted from the deep branch's email/broker
    blocks (a partial fix covering one profile but not the other).
    """
    cfg = config_from_dict(_raw_config({"ports_tls": [8443]}))
    apply_profile(cfg, "deep")
    assert cfg.connectors.enable_email is False
    assert cfg.connectors.enable_broker is False


def test_no_ports_tls_key_preserves_auto_enable():
    """A user who never touched port scope still gets full default coverage.

    Deviation from the plan's literal scenario, recorded here rather than
    silently worked around: `ScanCfg.ports_tls` is a required positional
    constructor argument with no default (`quirk/config.py`), so
    `config_from_dict` cannot construct a valid config whose scan block
    omits `ports_tls` entirely — every real YAML must supply it. The
    behavioural intent ("a user who never narrowed anything keeps auto-
    enable") is instead reproduced by loading through the live
    `config_from_dict` path and then clearing `ports_tls` from the resulting
    `_user_set_fields`, simulating the frozenset state that would exist if
    the field were optional. This still exercises the real `apply_profile`
    guard logic, not a stub.

    Falsifiability: fails if the suppression guard is broadened to trigger on
    any scan-block key being user-set (rather than specifically `ports_tls`
    being present in `_user_set_fields`), which would silently narrow
    coverage for users who never touched port scope at all — the exact
    regression D-01 explicitly warns against reversing.
    """
    cfg = config_from_dict(_raw_config({"ports_tls": [443]}))
    cfg.scan._user_set_fields = cfg.scan._user_set_fields - {"ports_tls"}
    apply_profile(cfg, "standard")
    assert cfg.connectors.enable_email is True
