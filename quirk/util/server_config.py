"""Strict reader for the server-side operator token.

Resolves ``security.api_token`` from ``QUIRK_API_TOKEN`` or the server config
file as a tri-state: a token, auth not configured, or a config file that
exists but cannot be read. Only ``security.api_token`` is consulted, so a
file holding just a ``security:`` section is valid. Error reasons are built
from an allow-list (path, exception class, line/column) and never carry
file content or the token.

Only a path that does not exist is "no config" (fresh install). A path that
exists but cannot be reached (permission denied, a directory, a dangling
symlink) is the error state. Once this process has read a populated file at a
path, a later missing or empty read of that same path is also the error state,
so a running server never drops to "auth not configured" because its config
file was moved aside, truncated mid-edit, or briefly unavailable. Restart the
process after deliberately removing a config file.
"""
from __future__ import annotations

import os
import stat
import threading
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


# Absolute paths this process has read as a populated mapping.
_populated_paths: set = set()
_populated_lock = threading.Lock()


def _key(path: str) -> str:
    return os.path.abspath(path)


def _seen_populated(path: str) -> bool:
    with _populated_lock:
        return _key(path) in _populated_paths


def _read_once(path: str) -> tuple[Optional[dict], Optional[str]]:
    try:
        st = os.stat(path)
    except FileNotFoundError:
        if os.path.lexists(path):
            return None, f"{path}: dangling symbolic link"
        return None, None
    except OSError as exc:
        return None, _reason(path, exc)
    if not stat.S_ISREG(st.st_mode):
        return None, f"{path}: not a regular file"
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception as exc:  # noqa: BLE001 - YAMLError, OSError, and constructor errors
        # The loader's constructors raise plain ValueError/TypeError (for
        # example an impossible date literal) as well as YAMLError; every
        # failure to build the document is the unreadable state.
        return None, _reason(path, exc)
    if data is None:
        return {}, None
    if not isinstance(data, dict):
        return None, f"{path}: top level is not a mapping"
    return data, None


def read_server_config(path: str) -> tuple[Optional[dict], Optional[str]]:
    """Return ``(data, error)``.

    ``(None, None)`` for a missing file, ``({}, None)`` for an empty or
    comment-only file, ``(None, reason)`` when the path cannot be reached, is
    not a regular file, cannot be read or is not a mapping. A missing or empty
    read of a path this process already read as populated is ``(None, reason)``.
    """
    data, error = _read_once(path)
    if error:
        return None, error
    if data:
        with _populated_lock:
            _populated_paths.add(_key(path))
        return data, None
    if _seen_populated(path):
        state = "missing" if data is None else "empty"
        return None, (
            f"{path}: {state} after this process read it with settings; "
            "restore the file or restart"
        )
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


@dataclass(frozen=True)
class ServerSecurity:
    allow_internal_targets: bool
    trusted_targets: list
    error: Optional[str]


def load_server_security() -> ServerSecurity:
    """Tolerant reader for the server's ``security`` block (D-07, D-03).

    Supplies ``allow_internal_targets`` and ``trusted_targets`` to dashboard
    jobs and the Effective Config preview. A missing or empty file is the
    documented default (False, allow-all); a file that exists but cannot be
    read is an ``error`` the caller must refuse on, never an empty list.
    Coercion matches ``quirk/config.py``.
    """
    path = server_config_path()
    data, error = read_server_config(path)
    if error:
        return ServerSecurity(False, [], error)
    if not data:
        return ServerSecurity(False, [], None)
    security = data.get("security")
    if security is None:
        return ServerSecurity(False, [], None)
    if not isinstance(security, dict):
        return ServerSecurity(False, [], f"{path}: 'security' is not a mapping")
    return ServerSecurity(
        bool(security.get("allow_internal_targets", False)),
        list(security.get("trusted_targets") or []),
        None,
    )
