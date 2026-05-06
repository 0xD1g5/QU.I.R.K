"""quirk doctor — Phase 52 DOCS-05: pre-engagement health check for operators.

Exit semantics (per Phase 52 D-14):
    Non-informational checks -> set failed=True on failure -> sys.exit(1)
    Informational checks     -> display [!] only -> never set failed
"""
from __future__ import annotations

import datetime
import os
import shutil
import socket
import sqlite3
import sys
from typing import Tuple

from rich.console import Console
from rich.table import Table

_PYTHON_MIN = (3, 11)
_DB_DEFAULT_PATH = "./quirk.db"
_CONFIG_DEFAULT_PATH = "./config.yaml"
_DASHBOARD_PORT = 8512
_DNS_PROBE = ("8.8.8.8", 53)


def _check_python_version() -> Tuple[bool, str]:
    ok = sys.version_info >= _PYTHON_MIN
    if ok:
        return True, f"[green][✓][/green] Python {sys.version_info.major}.{sys.version_info.minor}"
    return False, f"[red][✗] Python {sys.version_info.major}.{sys.version_info.minor} < {_PYTHON_MIN[0]}.{_PYTHON_MIN[1]}[/red]"


def _check_binary(name: str) -> Tuple[bool, str]:
    path = shutil.which(name)
    if path:
        return True, f"[green][✓][/green] {path}"
    return False, f"[red][✗] {name} not found in PATH[/red]"


def _check_compliance_freshness() -> Tuple[bool, str]:
    try:
        from quirk.compliance import COMPLIANCE_MAP, STALENESS_THRESHOLD_DAYS
    except Exception as exc:  # pragma: no cover - import guard
        return False, f"[red][✗] cannot import quirk.compliance: {exc}[/red]"
    today = datetime.date.today()
    stale: list[str] = []
    for title, entries in COMPLIANCE_MAP.items():
        for entry in entries:
            try:
                lv = datetime.date.fromisoformat(entry["last_verified"])
            except (KeyError, ValueError):
                stale.append(f"{title}/{entry.get('framework', '?')}")
                continue
            if (today - lv).days > STALENESS_THRESHOLD_DAYS:
                stale.append(f"{title}/{entry.get('framework', '?')}")
    if stale:
        return False, f"[red][✗] {len(stale)} compliance entries stale (>{STALENESS_THRESHOLD_DAYS} days)[/red]"
    return True, "[green][✓][/green] all frameworks within freshness window"


def _check_qramm_present() -> Tuple[bool, str]:
    """Informational only — never sets failed (D-11)."""
    try:
        import importlib
        importlib.import_module("quirk.qramm")
        return True, "[green][✓][/green] QRAMM module available"
    except Exception:
        return True, "[yellow][!] QRAMM module not installed — run Phase 51 first[/yellow]"


def _check_db(db_path: str = _DB_DEFAULT_PATH) -> Tuple[bool, str]:
    try:
        conn = sqlite3.connect(db_path, timeout=2)
        try:
            conn.execute("SELECT 1")
        finally:
            conn.close()
        return True, f"[green][✓][/green] {db_path} reachable"
    except Exception as exc:
        return False, f"[red][✗] cannot open {db_path}: {exc}[/red]"


def _check_config(config_path: str = _CONFIG_DEFAULT_PATH) -> Tuple[bool, str, str]:
    """Returns (failed_flag_value, informational_or_none, status_str).

    If file absent -> informational [!]; if file present but malformed -> fail.
    """
    if not os.path.exists(config_path):
        return False, "info", f"[yellow][!] {config_path} not found (run `quirk init` to create one)[/yellow]"
    try:
        import yaml
        with open(config_path, "r") as fh:
            yaml.safe_load(fh)
        return False, None, f"[green][✓][/green] {config_path} parses cleanly"
    except Exception as exc:
        return True, None, f"[red][✗] {config_path} malformed: {exc}[/red]"


def _check_network() -> Tuple[bool, str]:
    """Informational only — never sets failed (D-14 cat 7)."""
    try:
        sock = socket.create_connection(_DNS_PROBE, timeout=2)
        sock.close()
        return True, f"[green][✓][/green] outbound TCP to {_DNS_PROBE[0]}:{_DNS_PROBE[1]} OK"
    except OSError:
        return True, "[yellow][!] no outbound network — informational only[/yellow]"


def _check_dashboard() -> Tuple[bool, str]:
    """Informational only — never sets failed (D-14 cat 8)."""
    try:
        sock = socket.create_connection(("127.0.0.1", _DASHBOARD_PORT), timeout=1)
        sock.close()
        return True, f"[green][✓][/green] dashboard listening on port {_DASHBOARD_PORT}"
    except OSError:
        return True, f"[yellow][!] dashboard not running on port {_DASHBOARD_PORT} — informational only[/yellow]"


def run_doctor() -> None:
    """Phase 52 DOCS-05 entrypoint. Prints a Rich health table and exits 0 or 1."""
    console = Console()
    table = Table(title="QU.I.R.K. Health Check", show_header=True, header_style="bold")
    table.add_column("Check", style="bold")
    table.add_column("Status")

    failed = False

    # 1. Python environment (non-informational)
    ok, status = _check_python_version()
    failed = failed or (not ok)
    table.add_row("Python environment", status)

    # 2. Scanner binaries (non-informational)
    for binary in ("nmap", "syft", "semgrep"):
        ok, status = _check_binary(binary)
        failed = failed or (not ok)
        table.add_row(f"Binary: {binary}", status)

    # 3. Compliance framework freshness (non-informational)
    ok, status = _check_compliance_freshness()
    failed = failed or (not ok)
    table.add_row("Compliance freshness", status)

    # 4. QRAMM module (informational only — D-11)
    _ok, status = _check_qramm_present()
    table.add_row("QRAMM module", status)

    # 5. Database connectivity (non-informational)
    ok, status = _check_db()
    failed = failed or (not ok)
    table.add_row("Database (quirk.db)", status)

    # 6. Configuration validity
    cfg_failed, _info, status = _check_config()
    failed = failed or cfg_failed
    table.add_row("Configuration", status)

    # 7. Network connectivity (informational only — D-14 cat 7)
    _ok, status = _check_network()
    table.add_row("Network connectivity", status)

    # 8. Dashboard process (informational only — D-14 cat 8)
    _ok, status = _check_dashboard()
    table.add_row("Dashboard process", status)

    console.print(table)
    sys.exit(1 if failed else 0)
