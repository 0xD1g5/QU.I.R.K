"""Strict reader for the server-side operator token.

Resolves ``security.api_token`` from ``QUIRK_API_TOKEN`` or the server config
file as a tri-state: a token, auth not configured, or a config file that
exists but cannot be read. Only ``security.api_token`` is consulted, so a
file holding just a ``security:`` section is valid. Error reasons are built
from an allow-list (path, exception class, line/column) and never carry
file content or the token.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import yaml


@dataclass(frozen=True)
class TokenState:
    token: str
    error: Optional[str]


def server_config_path() -> str:
    return os.environ.get("QUIRK_CONFIG_PATH", "./config.yaml")


def _reason(path: str, exc: BaseException) -> str:
    reason = f"{path}: {type(exc).__name__}"
    mark = getattr(exc, "problem_mark", None)
    if mark is not None:
        reason += f" at line {mark.line + 1}, column {mark.column + 1}"
    if isinstance(exc, OSError) and exc.strerror:
        reason += f" ({exc.strerror})"
    return reason


def read_server_config(path: str) -> tuple[Optional[dict], Optional[str]]:
    """Return ``(data, error)``.

    ``(None, None)`` for a missing file, ``({}, None)`` for an empty or
    comment-only file, ``(None, reason)`` when the file cannot be read or is
    not a mapping.
    """
    if not os.path.isfile(path):
        return None, None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return None, _reason(path, exc)
    if data is None:
        return {}, None
    if not isinstance(data, dict):
        return None, f"{path}: top level is not a mapping"
    return data, None


def resolve_operator_token() -> TokenState:
    env = os.environ.get("QUIRK_API_TOKEN")
    if env:
        return TokenState(env, None)
    path = server_config_path()
    data, error = read_server_config(path)
    if error:
        return TokenState("", error)
    if not data:
        return TokenState("", None)
    security = data.get("security")
    if security is None:
        return TokenState("", None)
    if not isinstance(security, dict):
        return TokenState("", f"{path}: 'security' is not a mapping")
    return TokenState(str(security.get("api_token", "") or ""), None)
