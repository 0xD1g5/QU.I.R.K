"""quirk schedule — Phase 63 SCHED-01: CLI CRUD for scheduled scans."""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone

from rich.console import Console
from rich.table import Table
from sqlalchemy.exc import IntegrityError
from croniter import croniter

from quirk.db import get_session, init_db
from quirk.models import ScheduledScan

# T-63-02: validate name to prevent path traversal (no path separators, bounded length)
_NAME_RE = re.compile(r"^[A-Za-z0-9_\-\.]{1,255}$")


def _resolve_db_path(config_arg: str | None) -> str:
    """Resolve DB path in priority order: --config arg > QUIRK_DB_PATH env > ./quirk.db.

    For Phase 63 CLI use, --config accepts a raw .db path or :memory: directly.
    YAML config file parsing is deferred (not needed for SCHED-01 scope).
    """
    if config_arg is not None:
        return config_arg
    env_path = os.environ.get("QUIRK_DB_PATH")
    if env_path:
        return env_path
    return "./quirk.db"


def _cmd_add(args: argparse.Namespace, console: Console) -> None:
    """Handle `quirk schedule add` — validate and insert a new ScheduledScan row."""
    # T-63-02: validate name against allowlist regex before any DB write
    if not _NAME_RE.match(args.name):
        console.print(
            f"[red]Invalid schedule name: '{args.name}'. "
            "Only letters, digits, underscore, hyphen, and dot are allowed (max 255 chars).[/]"
        )
        sys.exit(2)

    # T-63-01: validate cron expression using croniter before any DB write
    if not croniter.is_valid(args.cron):
        console.print(f"[red]Invalid cron expression: {args.cron!r}[/]")
        sys.exit(2)

    db_path = _resolve_db_path(args.config)
    # Ensure tables exist (idempotent)
    init_db(db_path)

    row = ScheduledScan(
        name=args.name,
        cron_expr=args.cron,
        target=args.target,
        profile=args.profile,
        enabled=True,
        created_at=datetime.now(timezone.utc),
    )

    try:
        with get_session(db_path) as db:
            db.add(row)
            # commit() is called by the context manager on clean exit
    except IntegrityError:
        # T-63-03: fixed message — never stringify the exception (LEAK-02 pattern)
        console.print(f"[red]Schedule '{args.name}' already exists[/]")
        sys.exit(2)

    console.print(f"[green]Schedule '{args.name}' added.[/]")


def _cmd_list(args: argparse.Namespace, console: Console) -> None:
    """Handle `quirk schedule list` — print all ScheduledScan rows as a Rich table."""
    db_path = _resolve_db_path(args.config)
    init_db(db_path)

    with get_session(db_path) as db:
        rows = db.query(ScheduledScan).order_by(ScheduledScan.id).all()

    table = Table(title="Scheduled Scans", show_header=True, header_style="bold")
    table.add_column("Name", style="bold")
    table.add_column("Target")
    table.add_column("Profile")
    table.add_column("Cron")
    table.add_column("Enabled")
    table.add_column("Last Run")
    table.add_column("Created")

    for r in rows:
        last_run = r.last_run_at.isoformat() if r.last_run_at else "—"
        created = r.created_at.isoformat() if r.created_at else "—"
        enabled_str = "[green]yes[/]" if r.enabled else "[red]no[/]"
        table.add_row(
            r.name,
            r.target,
            r.profile or "balanced",
            r.cron_expr,
            enabled_str,
            last_run,
            created,
        )

    console.print(table)


def _cmd_enable_disable(args: argparse.Namespace, console: Console, *, enable: bool) -> None:
    """Handle `quirk schedule enable/disable <name>`."""
    db_path = _resolve_db_path(args.config)
    init_db(db_path)

    with get_session(db_path) as db:
        row = db.query(ScheduledScan).filter_by(name=args.name).first()
        if row is None:
            console.print(f"[red]Schedule '{args.name}' not found.[/]")
            sys.exit(2)
        row.enabled = enable
        # commit() called automatically by context manager

    action = "enabled" if enable else "disabled"
    console.print(f"[green]Schedule '{args.name}' {action}.[/]")


def _cmd_remove(args: argparse.Namespace, console: Console) -> None:
    """Handle `quirk schedule remove <name>`."""
    db_path = _resolve_db_path(args.config)
    init_db(db_path)

    with get_session(db_path) as db:
        row = db.query(ScheduledScan).filter_by(name=args.name).first()
        if row is None:
            console.print(f"[red]Schedule '{args.name}' not found.[/]")
            sys.exit(2)
        db.delete(row)
        # commit() called automatically by context manager

    console.print(f"[green]Schedule '{args.name}' removed.[/]")


def run_schedule(argv: list[str]) -> None:
    """Main entrypoint for `quirk schedule` subcommands.

    argv = sys.argv[2:] — does NOT include 'quirk' or 'schedule'.
    """
    console = Console()

    parser = argparse.ArgumentParser(
        prog="quirk schedule",
        description="Manage scheduled scans (Phase 63 SCHED-01)",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    # --- add ---
    add_parser = subparsers.add_parser("add", help="Add a new scheduled scan")
    add_parser.add_argument("--name", required=True, help="Unique schedule name")
    add_parser.add_argument("--cron", required=True, help="Cron expression (5-field)")
    add_parser.add_argument("--target", required=True, help="Scan target (host/IP/range)")
    add_parser.add_argument("--profile", default=None, help="Scan profile (default: balanced)")
    add_parser.add_argument("--config", default=None, help="Path to quirk.db or :memory:")

    # --- list ---
    list_parser = subparsers.add_parser("list", help="List all scheduled scans")
    list_parser.add_argument("--config", default=None, help="Path to quirk.db or :memory:")

    # --- enable ---
    enable_parser = subparsers.add_parser("enable", help="Enable a scheduled scan")
    enable_parser.add_argument("name", help="Schedule name")
    enable_parser.add_argument("--config", default=None, help="Path to quirk.db or :memory:")

    # --- disable ---
    disable_parser = subparsers.add_parser("disable", help="Disable a scheduled scan")
    disable_parser.add_argument("name", help="Schedule name")
    disable_parser.add_argument("--config", default=None, help="Path to quirk.db or :memory:")

    # --- remove ---
    remove_parser = subparsers.add_parser("remove", help="Remove a scheduled scan")
    remove_parser.add_argument("name", help="Schedule name")
    remove_parser.add_argument("--config", default=None, help="Path to quirk.db or :memory:")

    args = parser.parse_args(argv)

    if args.action == "add":
        _cmd_add(args, console)
    elif args.action == "list":
        _cmd_list(args, console)
    elif args.action == "enable":
        _cmd_enable_disable(args, console, enable=True)
    elif args.action == "disable":
        _cmd_enable_disable(args, console, enable=False)
    elif args.action == "remove":
        _cmd_remove(args, console)
