"""quirk report — save, list, and select named report branding/template
profiles (Phase 200 / RPT-04)."""
from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.table import Table

from quirk.report_profiles import list_profiles, profiles_dir, save_profile


def run_report(argv: list[str]) -> None:
    """quirk report entrypoint. argv is sys.argv[2:] (after the subcommand name)."""
    parser = argparse.ArgumentParser(
        prog="quirk report",
        description="Manage named report branding/template profiles.",
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest="action", required=True)

    profile_parser = sub.add_parser(
        "profile",
        help="Save or list report branding/template profiles",
        allow_abbrev=False,
    )
    profile_sub = profile_parser.add_subparsers(dest="profile_action", required=True)

    save_parser = profile_sub.add_parser(
        "save",
        help="Save the current config's report branding/template settings as a named profile",
        allow_abbrev=False,
    )
    save_parser.add_argument("name", help="Profile name (letters, digits, hyphens, underscores)")
    save_parser.add_argument(
        "--config",
        required=True,
        help="Path to the engagement config.yaml whose report.* settings should be saved",
    )

    profile_sub.add_parser(
        "list",
        help="List saved report profile names",
        allow_abbrev=False,
    )

    args = parser.parse_args(argv)
    console = Console()

    if args.action == "profile" and args.profile_action == "save":
        _run_save(args, console)
        return
    if args.action == "profile" and args.profile_action == "list":
        _run_list(console)
        return


def _run_save(args: argparse.Namespace, console: Console) -> None:
    from quirk.config import load_config
    from quirk.report_profiles import validate_profile_name

    try:
        validate_profile_name(args.name)
        cfg = load_config(args.config)
        existed = args.name in list_profiles()
        path = save_profile(args.name, cfg)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)

    if existed:
        console.print(f"[yellow]Profile {args.name!r} already existed — overwritten.[/yellow]")
    console.print(f"[green]Saved report profile {args.name!r} to {path}[/green]")
    sys.exit(0)


def _run_list(console: Console) -> None:
    names = list_profiles()
    if not names:
        console.print(
            f"No report profiles saved. Profiles directory: {profiles_dir()}"
        )
        sys.exit(0)

    table = Table(title="QU.I.R.K. Report Profiles", show_header=True, header_style="bold")
    table.add_column("Name", style="bold")
    for name in names:
        table.add_row(name)
    console.print(table)
    sys.exit(0)
