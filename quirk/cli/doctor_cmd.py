"""quirk doctor — Phase 52 DOCS-05: pre-engagement health check for operators.

Exit semantics (per Phase 52 D-14):
    Non-informational checks -> set failed=True on failure -> sys.exit(1)
    Informational checks     -> display [!] only -> never set failed

Phase 75 D-01..D-03 (APCL-01 / WR-01, WR-02, WR-03):
  - ``_check_dashboard`` and ``_check_network`` return a typed status dict
    ``{"ok": bool, "detail": str, "remediation": str}`` populated by real
    probes (HTTP HEAD against the dashboard, DNS lookup for network).
  - ``_check_db`` honors ``QUIRK_DB_PATH`` env var first; falls back to
    ``_default_db_path()`` only when env is unset.
  - ``_default_db_path()`` (in ``quirk/dashboard/api/deps.py``) is the
    single canonical resolver; it raises ``ValueError`` when multiple
    legacy DBs are present.

Per Phase 75 D-18, ``quirk doctor`` exit-code semantics are unchanged.
"""
from __future__ import annotations

import datetime
import os
import shutil
import socket
import sqlite3
import sys
from typing import Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from rich.console import Console
from rich.table import Table

from quirk.errors import format_error
from quirk.util.safe_exc import safe_str

_PYTHON_MIN = (3, 11)

_BINARY_TO_CODE = {"nmap": "INSTALL-006", "syft": "INSTALL-007", "semgrep": "INSTALL-008"}
_CONFIG_DEFAULT_PATH = "./config.yaml"
_DASHBOARD_PORT = 8512
_DASHBOARD_URL = f"http://127.0.0.1:{_DASHBOARD_PORT}/"
_NETWORK_PROBE_HOST = "example.com"


def _check_python_version() -> Tuple[bool, str]:
    ok = sys.version_info >= _PYTHON_MIN
    if ok:
        return True, f"[green][✓][/green] Python {sys.version_info.major}.{sys.version_info.minor}"
    return False, f"[red][✗] {format_error('INSTALL-005')}[/red]"


def _check_binary(name: str) -> Tuple[bool, str]:
    path = shutil.which(name)
    if path:
        return True, f"[green][✓][/green] {path}"
    code = _BINARY_TO_CODE.get(name, "INSTALL-006")
    return False, f"[red][✗] {format_error(code)}[/red]"


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
        return False, f"[red][✗] {format_error('INSTALL-009')}[/red]"
    return True, "[green][✓][/green] all frameworks within freshness window"


def _check_qramm_present() -> Tuple[bool, str]:
    """Informational only — never sets failed (D-11)."""
    try:
        import importlib
        importlib.import_module("quirk.qramm")
        return True, "[green][✓][/green] QRAMM module available"
    except Exception:
        return True, "[yellow][!] QRAMM module not installed — run Phase 51 first[/yellow]"


def _check_db() -> dict:
    """Phase 75 D-02 (WR-02) — honor ``QUIRK_DB_PATH`` then ``_default_db_path()``.

    Returns the typed status dict ``{"ok", "detail", "remediation"}``.
    """
    env_path = os.environ.get("QUIRK_DB_PATH")
    if env_path:
        if not (os.path.exists(env_path) and os.access(env_path, os.R_OK)):
            return {
                "ok": False,
                "detail": f"QUIRK_DB_PATH={env_path!r} not readable",
                "remediation": "Unset QUIRK_DB_PATH or point it at a readable SQLite file.",
            }
        resolved = env_path
    else:
        # D-02 falls back to D-03 single canonical resolver.
        try:
            from quirk.dashboard.api.deps import _default_db_path
            resolved = _default_db_path()
        except ValueError as ve:
            return {
                "ok": False,
                "detail": safe_str(ve),
                "remediation": "Set QUIRK_DB_PATH to disambiguate between the legacy DB files listed above.",
            }
    try:
        conn = sqlite3.connect(resolved, timeout=2)
        try:
            conn.execute("SELECT 1")
        finally:
            conn.close()
        return {
            "ok": True,
            "detail": f"DB at {resolved} reachable",
            "remediation": "",
        }
    except Exception as exc:
        return {
            "ok": False,
            "detail": f"DB at {resolved} not reachable: {safe_str(exc)}",
            "remediation": "Verify QUIRK_DB_PATH or run `quirk init` to create the database.",
        }


def _check_config(config_path: str = _CONFIG_DEFAULT_PATH) -> Tuple[bool, str, str]:
    """Returns (failed_flag_value, informational_or_none, status_str).

    If file absent -> informational [!]; if file present but malformed -> fail.
    """
    if not os.path.exists(config_path):
        return False, "info", f"[yellow][!] {config_path} not found (run `quirk init` to create one)[/yellow]"
    try:
        import yaml
    except ImportError:
        return False, "info", "[yellow][!] PyYAML not installed — config validation skipped[/yellow]"
    try:
        with open(config_path, "r") as fh:
            yaml.safe_load(fh)
        return False, None, f"[green][✓][/green] {config_path} parses cleanly"
    except Exception:
        return True, None, f"[red][✗] {format_error('INSTALL-010')}[/red]"


def _check_network() -> dict:
    """Phase 75 D-01 (WR-01) — DNS-lookup probe with typed status dict.

    Informational only — caller does NOT set failed on a False return
    (D-14 cat 7 preserved).
    """
    try:
        socket.gethostbyname(_NETWORK_PROBE_HOST)
        return {
            "ok": True,
            "detail": f"DNS lookup succeeded for {_NETWORK_PROBE_HOST}",
            "remediation": "",
        }
    except socket.gaierror as exc:
        return {
            "ok": False,
            "detail": f"DNS lookup failed for {_NETWORK_PROBE_HOST}: {safe_str(exc)}",
            "remediation": "Verify /etc/resolv.conf or run `quirk config --dns ...`.",
        }


def _check_dashboard() -> dict:
    """Phase 75 D-01 (WR-01) — HTTP HEAD probe with typed status dict.

    Informational only — caller does NOT set failed on a False return
    (D-14 cat 8 preserved).
    """
    try:
        req = Request(_DASHBOARD_URL, method="HEAD")
        resp = urlopen(req, timeout=2)
        try:
            status = getattr(resp, "status", 200)
        finally:
            try:
                resp.close()
            except Exception:
                pass
        if 200 <= int(status) < 400:
            return {
                "ok": True,
                "detail": f"Dashboard reachable at {_DASHBOARD_URL} (HTTP {status})",
                "remediation": "",
            }
        return {
            "ok": False,
            "detail": f"Dashboard returned unexpected HTTP {status}",
            "remediation": "Start the dashboard with `quirk dashboard up` and retry.",
        }
    except (URLError, HTTPError, socket.timeout, OSError) as exc:
        return {
            "ok": False,
            "detail": f"Dashboard unreachable at {_DASHBOARD_URL}: {safe_str(exc)}",
            "remediation": "Start the dashboard with `quirk dashboard up` and retry.",
        }


def _render_status(result: dict) -> str:
    """Render a typed status dict (D-01) into a Rich-coloured cell."""
    if result["ok"]:
        return f"[green][✓][/green] {result['detail']}"
    rem = result.get("remediation", "")
    rem_suffix = f" — {rem}" if rem else ""
    return f"[red][✗][/red] {result['detail']}{rem_suffix}"


def _render_status_informational(result: dict) -> str:
    """Same as _render_status but yellow on failure (informational checks)."""
    if result["ok"]:
        return f"[green][✓][/green] {result['detail']}"
    rem = result.get("remediation", "")
    rem_suffix = f" — {rem}" if rem else ""
    return f"[yellow][!] {result['detail']}{rem_suffix} (informational)[/yellow]"


def run_doctor() -> None:
    """Phase 52 DOCS-05 entrypoint. Prints a Rich health table and exits 0 or 1.

    Phase 75 D-18: exit-code semantics unchanged from Phase 52.
    """
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

    # 5. Database connectivity (non-informational) — Phase 75 D-02 typed dict
    db_result = _check_db()
    failed = failed or (not db_result["ok"])
    table.add_row("Database (quirk.db)", _render_status(db_result))

    # 6. Configuration validity
    cfg_failed, _info, status = _check_config()
    failed = failed or cfg_failed
    table.add_row("Configuration", status)

    # 7. Network connectivity (informational only — D-14 cat 7) — Phase 75 D-01
    net_result = _check_network()
    table.add_row("Network connectivity", _render_status_informational(net_result))

    # 8. Dashboard process (informational only — D-14 cat 8) — Phase 75 D-01
    dash_result = _check_dashboard()
    table.add_row("Dashboard process", _render_status_informational(dash_result))

    console.print(table)
    sys.exit(1 if failed else 0)
