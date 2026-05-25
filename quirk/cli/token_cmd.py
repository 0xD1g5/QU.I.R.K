"""quirk token — Phase 102 AUTH-01: dashboard API token management CLI."""
from __future__ import annotations

import argparse
import os
import secrets
import sys
import tempfile

import yaml


def _write_token_to_config(config_path: str, token: str) -> None:
    """Write token to security.api_token using a full-file YAML round-trip.

    Never writes a partial dict — always loads the full file first so
    other config keys (assessment, targets, scan, etc.) are preserved.

    The write is atomic on POSIX (temp file + os.replace) so a mid-write
    crash or disk-full condition cannot corrupt config.yaml.

    Limitation: yaml.safe_load + yaml.dump is a lossy round-trip — YAML
    comments, blank lines used for readability, and original key ordering
    are not preserved.  A warning is printed so operators are aware before
    running this command on an annotated config.
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except FileNotFoundError:
        raw = {}
    if not isinstance(raw.get("security"), dict):
        raw["security"] = {}
    raw["security"]["api_token"] = token
    print(
        "Warning: config.yaml comments and key ordering will be normalized by this operation.",
        file=sys.stderr,
    )
    dir_ = os.path.dirname(os.path.abspath(config_path))
    fd, tmp = tempfile.mkstemp(dir=dir_, prefix=".quirk_config_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        os.replace(tmp, config_path)  # atomic on POSIX; best-effort on Windows
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def run_token(argv: list[str]) -> None:
    """Main entrypoint for `quirk token` subcommands.

    argv = sys.argv[2:] — does NOT include 'quirk' or 'token'.
    """
    parser = argparse.ArgumentParser(
        prog="quirk token",
        description="Dashboard API token management (Phase 102 AUTH-01)",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    # --- generate ---
    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate and persist a new dashboard API token",
    )
    gen_parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml (default: config.yaml)",
    )

    # --- rotate ---
    rot_parser = subparsers.add_parser(
        "rotate",
        help="Rotate the dashboard API token (old token invalid immediately)",
    )
    rot_parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml (default: config.yaml)",
    )

    # --- show ---
    show_parser = subparsers.add_parser(
        "show",
        help="Show the persisted YAML token (not the env-var value)",
    )
    show_parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml (default: config.yaml)",
    )

    args = parser.parse_args(argv)

    if args.action in ("generate", "rotate"):
        token = secrets.token_urlsafe(32)
        config_path = args.config
        _write_token_to_config(config_path, token)
        print(f"Token written to {config_path} (security.api_token):")
        print(token)
        env_token = os.environ.get("QUIRK_API_TOKEN", "")
        if env_token:
            print(
                "Note: QUIRK_API_TOKEN env var is set and takes precedence over the YAML value."
            )
        sys.exit(0)

    if args.action == "show":
        config_path = args.config
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            token = (raw.get("security") or {}).get("api_token", "")
        except FileNotFoundError:
            print(f"Config file not found: {config_path}", file=sys.stderr)
            sys.exit(1)
        env_token = os.environ.get("QUIRK_API_TOKEN", "")
        if env_token:
            print(
                "Note: QUIRK_API_TOKEN env var is set and takes precedence over the YAML value."
            )
        print(token if token else "(no token configured)")
        sys.exit(0)
