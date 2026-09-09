"""Phase 193 / PARITY-03 / D-09 -- env-var-fallback precedence coverage for
the four `run_scan.py` credential consumption sites (`adcs_password`,
`pg_scanner_password`, `mysql_scanner_password`, `snmp_community`).

Two things are asserted, deliberately kept separate:

1. Precedence semantics -- built from the actual `ConnectorsCfg` dataclass
   via `quirk.config.load_config` on a temp YAML (never a hand-rolled stand-in
   object), replicating the exact `config-value-or-env` expression each site
   uses. Never runs a full scan.

2. An AST-based pin (`ast.parse`/`ast.walk`, never a regex over file text --
   `run_scan.py` contains prose/docstrings mentioning these env-var names,
   see RESEARCH Pitfall 5) proving each of the four production sites still
   contains a genuine `os.environ.get("QUIRK_...")` call with the expected
   literal name, so this test cannot stay green while the production site
   drifts or is reverted.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

from quirk.config import load_config

_REPO_ROOT = Path(__file__).resolve().parent.parent
_RUN_SCAN_PATH = _REPO_ROOT / "run_scan.py"


def _write_config(tmp_path: Path, **connectors_overrides) -> Path:
    lines = [
        "assessment:",
        "  name: test",
        "  data_classification: internal",
        "  report_owner: me",
        "  timezone: UTC",
        "scan:",
        "  concurrency: 10",
        "  ports_tls: [443]",
        "output:",
        "  directory: ./out",
        "  db_path: ./out/quirk.db",
        "connectors:",
    ]
    for key, value in connectors_overrides.items():
        if value is None:
            lines.append(f"  {key}: null")
        elif isinstance(value, bool):
            lines.append(f"  {key}: {'true' if value else 'false'}")
        else:
            lines.append(f'  {key}: "{value}"')
    config_path = tmp_path / "config.yaml"
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config_path


# ---------------------------------------------------------------------------
# Precedence coverage -- one field at a time, three cases each: config wins,
# env used when config unset, documented default when neither is present.
# ---------------------------------------------------------------------------

_FIELDS = [
    ("adcs_password", "QUIRK_ADCS_PASSWORD", None),
    ("pg_scanner_password", "QUIRK_PG_SCANNER_PASSWORD", None),
    ("mysql_scanner_password", "QUIRK_MYSQL_SCANNER_PASSWORD", None),
    ("snmp_community", "QUIRK_SNMP_COMMUNITY", "public"),
]


def _resolve(cfg, field: str, env_var: str, default):
    """Mirrors the exact resolution expression each run_scan.py site uses.

    - Password fields (falsy config defaults): getattr with the documented
      default, plain or-fallback to env.
    - `snmp_community` (TRUTHY default "public" -- Phase 193 review CR-01):
      env beats the *default* but never an operator-explicit config value,
      keyed off `_user_set_fields` exactly as the production sites in
      run_scan.py and quirk/scanner/hardware_scanner.py do.
    """
    import os

    if field == "snmp_community":
        value = getattr(cfg.connectors, field, default)
        if not value or field not in getattr(
            cfg.connectors, "_user_set_fields", frozenset()
        ):
            value = os.environ.get(env_var, "") or value or default
        return value
    return getattr(cfg.connectors, field, default) or os.environ.get(env_var, default)


@pytest.mark.parametrize("field,env_var,default", _FIELDS)
def test_config_value_wins_over_env_var(tmp_path, monkeypatch, field, env_var, default):
    monkeypatch.setenv(env_var, "from-env")
    config_path = _write_config(tmp_path, **{field: "from-config"})
    cfg = load_config(str(config_path))
    assert _resolve(cfg, field, env_var, default) == "from-config"


@pytest.mark.parametrize("field,env_var,default", _FIELDS)
def test_env_var_used_when_config_unset(tmp_path, monkeypatch, field, env_var, default):
    monkeypatch.setenv(env_var, "from-env")
    config_path = _write_config(tmp_path, **{field: None})
    cfg = load_config(str(config_path))
    assert _resolve(cfg, field, env_var, default) == "from-env"


@pytest.mark.parametrize("field,env_var,default", _FIELDS)
def test_env_var_used_when_config_key_omitted(tmp_path, monkeypatch, field, env_var, default):
    """Phase 193 review CR-01: the dashboard's job config.yaml never writes a
    credential key at all (env-only by design), so the field resolves to its
    dataclass DEFAULT -- for `snmp_community` that default is the truthy
    "public", which a plain `or`-fallback never falls through. This is the
    fixture shape a real dashboard job produces (key OMITTED, not null)."""
    monkeypatch.setenv(env_var, "from-env")
    config_path = _write_config(tmp_path)  # no connectors overrides at all
    cfg = load_config(str(config_path))
    assert _resolve(cfg, field, env_var, default) == "from-env"


@pytest.mark.parametrize("field,env_var,default", _FIELDS)
def test_documented_default_when_neither_present(tmp_path, monkeypatch, field, env_var, default):
    monkeypatch.delenv(env_var, raising=False)
    config_path = _write_config(tmp_path, **{field: None})
    cfg = load_config(str(config_path))
    assert _resolve(cfg, field, env_var, default) == default


# Negative-control precedence pins, explicit per acceptance criteria: env
# value used when config is None; config value ("from-config") wins over a
# populated env var ("from-env").
def test_negative_control_adcs_password_env_wins_when_config_none(tmp_path, monkeypatch):
    monkeypatch.setenv("QUIRK_ADCS_PASSWORD", "from-env")
    config_path = _write_config(tmp_path, adcs_password=None)
    cfg = load_config(str(config_path))
    assert _resolve(cfg, "adcs_password", "QUIRK_ADCS_PASSWORD", None) == "from-env"


def test_negative_control_adcs_password_config_wins_over_env(tmp_path, monkeypatch):
    monkeypatch.setenv("QUIRK_ADCS_PASSWORD", "from-env")
    config_path = _write_config(tmp_path, adcs_password="from-config")
    cfg = load_config(str(config_path))
    assert _resolve(cfg, "adcs_password", "QUIRK_ADCS_PASSWORD", None) == "from-config"


# ---------------------------------------------------------------------------
# AST pin -- proves the production sites in run_scan.py genuinely contain the
# expected os.environ.get("QUIRK_...") calls, so this test cannot pass while
# the production code has drifted or been reverted.
# ---------------------------------------------------------------------------

_EXPECTED_ENV_NAMES = {
    "QUIRK_ADCS_PASSWORD",
    "QUIRK_PG_SCANNER_PASSWORD",
    "QUIRK_MYSQL_SCANNER_PASSWORD",
    "QUIRK_SNMP_COMMUNITY",
}


def _find_environ_get_string_args(tree: ast.AST) -> set[str]:
    """Walk *tree* and collect the literal first-argument string of every
    `os.environ.get(...)` call -- an AST walk, never a regex over source
    text (run_scan.py's prose/docstrings mention these names too)."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "get"):
            continue
        value = func.value
        if not (
            isinstance(value, ast.Attribute)
            and value.attr == "environ"
            and isinstance(value.value, ast.Name)
            and value.value.id == "os"
        ):
            continue
        if not node.args:
            continue
        first_arg = node.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            found.add(first_arg.value)
    return found


def test_all_four_env_fallback_names_present_in_run_scan_py():
    tree = ast.parse(_RUN_SCAN_PATH.read_text(encoding="utf-8"), filename=str(_RUN_SCAN_PATH))
    found = _find_environ_get_string_args(tree)
    missing = _EXPECTED_ENV_NAMES - found
    assert not missing, (
        f"run_scan.py is missing os.environ.get(...) call(s) for: {missing}. "
        "Production sites may have drifted or been reverted."
    )


def test_ast_pin_would_fail_on_a_synthetic_snippet_missing_the_call():
    """Falsifiability: the same detector applied to a snippet that lacks the
    call correctly reports it missing -- proves the detector is sensitive,
    not vacuously true."""
    snippet = textwrap.dedent(
        """
        password = cfg.connectors.pg_scanner_password
        """
    )
    tree = ast.parse(snippet)
    found = _find_environ_get_string_args(tree)
    assert "QUIRK_PG_SCANNER_PASSWORD" not in found
