"""Tests for schedule_cmd._config_has_authenticated_mode (D-05 / WR-06).

Phase 97 / TD-01: the extension-heuristic bypass is removed; any existing file
is parsed, and the function fails closed (returns True) on unclassifiable configs.

Tests use tmp_path to write extensionless and malformed files without touching
the real filesystem.
"""
import pytest


def test_extensionless_auth_config_rejected(tmp_path):
    """D-05 / Test 1: a file with no .yml/.yaml extension whose YAML body sets
    connectors.enable_authenticated_mode: true must return True (scheduler rejects)."""
    from quirk.cli.schedule_cmd import _config_has_authenticated_mode

    config_file = tmp_path / "quirk_config"  # no extension
    config_file.write_text(
        "connectors:\n  enable_authenticated_mode: true\n",
        encoding="utf-8",
    )
    assert _config_has_authenticated_mode(str(config_file)) is True, (
        "Extensionless auth config must be rejected (return True)"
    )


def test_nonexistent_path_returns_false(tmp_path):
    """D-05 / Test 2: a config_path that does not exist on disk returns False —
    nothing to parse; non-existent path is not authenticated."""
    from quirk.cli.schedule_cmd import _config_has_authenticated_mode

    nonexistent = str(tmp_path / "does_not_exist.yml")
    assert _config_has_authenticated_mode(nonexistent) is False, (
        "Non-existent config path must return False"
    )

    # None path also returns False
    assert _config_has_authenticated_mode(None) is False, (
        "None config path must return False"
    )


def test_nonauthenticated_yaml_returns_false(tmp_path):
    """D-05 / Test 3: an existing parseable YAML dict WITHOUT the auth flag
    returns False (scheduler proceeds)."""
    from quirk.cli.schedule_cmd import _config_has_authenticated_mode

    config_file = tmp_path / "quirk.yml"
    config_file.write_text(
        "connectors:\n  enable_authenticated_mode: false\ntargets: []\n",
        encoding="utf-8",
    )
    assert _config_has_authenticated_mode(str(config_file)) is False, (
        "Non-authenticated config must return False"
    )


def test_unparseable_existing_file_fails_closed(tmp_path):
    """D-05 / Test 4: an existing file that does not parse to a dict returns True
    (fail closed) — NOT the current fail-open False."""
    from quirk.cli.schedule_cmd import _config_has_authenticated_mode

    # Binary/garbage content that yaml.safe_load cannot parse as a dict
    binary_file = tmp_path / "quirk_config"
    binary_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe binary garbage")
    assert _config_has_authenticated_mode(str(binary_file)) is True, (
        "Unparseable existing file must fail closed (return True)"
    )

    # YAML that parses to a non-dict (e.g., a plain string)
    string_yaml = tmp_path / "string_config.yml"
    string_yaml.write_text("just a plain string\n", encoding="utf-8")
    assert _config_has_authenticated_mode(str(string_yaml)) is True, (
        "Existing YAML that parses to non-dict must fail closed (return True)"
    )


def test_sqlite_db_config_not_rejected(tmp_path):
    """D-05 carve-out: `--config` is overloaded as the scheduler's SQLite DB path
    (_resolve_db_path). A real SQLite database file is categorically not an
    authenticated-mode YAML config and must NOT trip the fail-closed reject —
    otherwise `quirk schedule add --config <db>` exits 2 on a valid DB path."""
    from quirk.cli.schedule_cmd import _config_has_authenticated_mode
    from quirk.db import init_db

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)  # materializes a real SQLite file with the magic header
    assert _config_has_authenticated_mode(db_path) is False, (
        "A SQLite DB passed via --config must not be treated as an auth config"
    )


# --------------------------------------------------------------------------
# 225.1-10 / D-08: `quirk schedule add` checks the SERVER config trusted_targets
# --------------------------------------------------------------------------

def _run_add(tmp_path, monkeypatch, server_yaml, target):
    import argparse
    from rich.console import Console
    from quirk.cli.schedule_cmd import _cmd_add

    cfg = tmp_path / "server.yaml"
    cfg.write_text(server_yaml, encoding="utf-8")
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(cfg))
    args = argparse.Namespace(
        name="nightly", cron="0 2 * * 1", target=target, profile="balanced",
        config=str(tmp_path / "sched.db"), check_in=False,
    )
    _cmd_add(args, Console())


def test_add_untrusted_target_exits_2(tmp_path, monkeypatch):
    with pytest.raises(SystemExit) as ei:
        _run_add(tmp_path, monkeypatch, "security:\n  trusted_targets: [127.0.0.1]\n", "10.9.9.9")
    assert ei.value.code == 2


def test_add_trusted_target_ok(tmp_path, monkeypatch):
    _run_add(tmp_path, monkeypatch, "security:\n  trusted_targets: [127.0.0.1]\n", "127.0.0.1")


def test_add_empty_allowlist_ok(tmp_path, monkeypatch):
    _run_add(tmp_path, monkeypatch, "security:\n  trusted_targets: []\n", "10.9.9.9")


def test_add_unreadable_server_config_exits_2(tmp_path, monkeypatch):
    with pytest.raises(SystemExit) as ei:
        _run_add(tmp_path, monkeypatch, "security: [unclosed\n", "127.0.0.1")
    assert ei.value.code == 2
