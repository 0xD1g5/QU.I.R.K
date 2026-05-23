"""QU.I.R.K. canonical error registry (Phase 68, UX-01).

Single source of truth for operator-facing error codes. All CLI and dashboard
error surfaces import format_error() from this module.

Wire format: `[QRK-<DOMAIN>-NNN] <cause> Fix: <fix>`
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorEntry:
    code: str    # e.g. "INSTALL-001" — NO "QRK-" prefix in stored code
    cause: str   # one-line, no embedded newlines
    fix: str     # one-line, no embedded newlines


ERROR_REGISTRY: dict[str, ErrorEntry] = {
    # --- INSTALL domain (first-run install-day, UX-02) ---
    "INSTALL-001": ErrorEntry(
        code="INSTALL-001",
        cause="Optional scanner package not installed.",
        fix="Run `pip install quirk[<extra>]` to enable this scanner.",
    ),
    "INSTALL-002": ErrorEntry(
        code="INSTALL-002",
        cause="Dashboard extras not installed.",
        fix="Run `pip install quirk[dashboard]` then retry `quirk serve`.",
    ),
    "INSTALL-003": ErrorEntry(
        code="INSTALL-003",
        cause="Cannot open the scan database.",
        fix="Run `quirk doctor` to diagnose. Ensure the configured db path is readable.",
    ),
    "INSTALL-004": ErrorEntry(
        code="INSTALL-004",
        cause="Dashboard port is already in use.",
        fix="Run `lsof -i :<port>` to find the conflicting process, or use `quirk serve --port <other>`.",
    ),
    "INSTALL-005": ErrorEntry(
        code="INSTALL-005",
        cause="Python interpreter version is below the minimum supported.",
        fix="Install Python 3.11 or newer; re-run `quirk doctor`.",
    ),
    "INSTALL-006": ErrorEntry(
        code="INSTALL-006",
        cause="`nmap` binary not found in PATH.",
        fix="Install nmap (`brew install nmap` / `apt install nmap`) and ensure it is on PATH.",
    ),
    "INSTALL-007": ErrorEntry(
        code="INSTALL-007",
        cause="`syft` binary not found in PATH.",
        fix="Install Anchore syft from https://github.com/anchore/syft#installation.",
    ),
    "INSTALL-008": ErrorEntry(
        code="INSTALL-008",
        cause="`semgrep` binary not found in PATH.",
        fix="Run `pip install semgrep` or follow https://semgrep.dev/docs/getting-started.",
    ),
    "INSTALL-009": ErrorEntry(
        code="INSTALL-009",
        cause="Compliance mapping entries are stale.",
        fix="Re-verify the compliance catalog and bump `last_verified` (see CLAUDE.md Staleness Review Cadence).",
    ),
    "INSTALL-010": ErrorEntry(
        code="INSTALL-010",
        cause="Configuration file is malformed.",
        fix="Run `quirk doctor` to see the parser error; validate YAML syntax.",
    ),

    # --- DASHBOARD domain (FastAPI 4xx/5xx) ---
    "DASHBOARD-001": ErrorEntry(
        code="DASHBOARD-001",
        cause="Authentication required.",
        fix="Send the dashboard auth token in the X-Quirk-Auth header.",
    ),
    "DASHBOARD-002": ErrorEntry(
        code="DASHBOARD-002",
        cause="Missing CSRF header on mutating request.",
        fix="Add header `X-Quirk-Request: 1` to POST/PUT/PATCH/DELETE requests.",
    ),
    "DASHBOARD-003": ErrorEntry(
        code="DASHBOARD-003",
        cause="Rate limit exceeded.",
        fix="Honor the Retry-After response header before retrying.",
    ),
    "DASHBOARD-004": ErrorEntry(
        code="DASHBOARD-004",
        cause="Invalid scan_id format.",
        fix="Provide a UUID-shaped scan_id from `/api/scans` or `quirk` CLI output.",
    ),
    "DASHBOARD-005": ErrorEntry(
        code="DASHBOARD-005",
        cause="No scan found with the requested scan_id.",
        fix="List scans via GET /api/scans and use a scan_id from the response.",
    ),
    "DASHBOARD-006": ErrorEntry(
        code="DASHBOARD-006",
        cause="No scan results available yet.",
        fix="Run your first scan: `quirk --config config.yaml`.",
    ),
    "DASHBOARD-007": ErrorEntry(
        code="DASHBOARD-007",
        cause="Cannot compare a scan to itself.",
        fix="Choose two distinct scan_ids for the compare request.",
    ),
    "DASHBOARD-008": ErrorEntry(
        code="DASHBOARD-008",
        cause="Job not found.",
        fix="List jobs via GET /api/jobs and use a job_id from the response.",
    ),
    "DASHBOARD-009": ErrorEntry(
        code="DASHBOARD-009",
        cause="QRAMM session not found.",
        fix="List sessions via GET /api/qramm/sessions and use a session_id from the response.",
    ),
    "DASHBOARD-010": ErrorEntry(
        code="DASHBOARD-010",
        cause="QRAMM profile_multiplier is out of range.",
        fix="profile_multiplier must be in [0.8, 1.5].",
    ),
    "DASHBOARD-011": ErrorEntry(
        code="DASHBOARD-011",
        cause="Cannot score a QRAMM session with no answered questions.",
        fix="Answer at least one question before requesting a score.",
    ),
    "DASHBOARD-012": ErrorEntry(
        code="DASHBOARD-012",
        cause="Playwright not installed for PDF export.",
        fix="Run `pip install playwright && playwright install chromium`.",
    ),
    "DASHBOARD-013": ErrorEntry(
        code="DASHBOARD-013",
        cause="PDF export failed due to an unexpected error.",
        fix="Check server logs for the full traceback and file an issue if reproducible.",
    ),

    # --- SCHED domain (scheduled scans) ---
    "SCHED-001": ErrorEntry(
        code="SCHED-001",
        cause="Invalid schedule name.",
        fix="Schedule names must match [A-Za-z0-9_-]+ and be 1-64 chars.",
    ),
    "SCHED-002": ErrorEntry(
        code="SCHED-002",
        cause="Invalid cron expression.",
        fix="Use a 5-field cron expression (e.g. `0 2 * * *`). See `man 5 crontab`.",
    ),
    "SCHED-003": ErrorEntry(
        code="SCHED-003",
        cause="Schedule with that name already exists.",
        fix="Choose a unique name or remove the existing schedule with `quirk schedule remove <name>`.",
    ),
    "SCHED-004": ErrorEntry(
        code="SCHED-004",
        cause="Schedule not found.",
        fix="Run `quirk schedule list` to see existing schedule names.",
    ),
    "SCHED-AUTH-001": ErrorEntry(
        code="SCHED-AUTH-001",
        cause="Authenticated scan configs cannot be scheduled — credentials are ephemeral and cannot be persisted.",
        fix="Run an authenticated scan interactively with `quirk --auth-bearer` (or `--auth-api-key` / `--auth-basic`).",
    ),

    # --- CBOM domain ---
    "CBOM-001": ErrorEntry(
        code="CBOM-001",
        cause="CBOM coverage gap detected for an in-scope endpoint.",
        fix="Re-run the scan with the required scanner extra installed, or mark the host out-of-scope.",
    ),

    # --- CMVP domain (Phase 81) ---
    "CMVP-REFRESH-NETWORK": ErrorEntry(
        code="CMVP-REFRESH-NETWORK",
        cause="Could not fetch CMVP search page (network error).",
        fix="Verify connectivity to csrc.nist.gov; retry `quirk compliance cmvp refresh`. Offline scans still use the bundled cache.",
    ),
    "CMVP-REFRESH-PARSE": ErrorEntry(
        code="CMVP-REFRESH-PARSE",
        cause="CMVP search page HTML did not match expected selectors.",
        fix="NIST page structure may have changed. File an issue and pin to the bundled cache until parser updated.",
    ),
    "CMVP-REFRESH-NO-CHANGES": ErrorEntry(
        code="CMVP-REFRESH-NO-CHANGES",
        cause="CMVP cache already current; no modules changed.",
        fix="No action needed. Bump `last_verified` only if re-verifying without content change.",
    ),
    "CMVP-STALE": ErrorEntry(
        code="CMVP-STALE",
        cause="CMVP cache is older than 90 days.",
        fix="Run `quirk compliance cmvp refresh` and commit with message `chore: re-verify CMVP catalog (YYYY-MM-DD)`.",
    ),

    # --- Reserved per-domain exception fallback codes (NNN-099) ---
    # Used by render-time CATEGORY_TO_CODE dispatch when scan_error_category == "exception"
    # and the host/scanner_label is one of these domains.
    "TLS-099": ErrorEntry(
        code="TLS-099",
        cause="Unexpected error in TLS scanner.",
        fix="Re-run with `--verbose` and inspect logs; file an issue if reproducible.",
    ),
    "SSH-099": ErrorEntry(
        code="SSH-099",
        cause="Unexpected error in SSH scanner.",
        fix="Re-run with `--verbose` and inspect logs; file an issue if reproducible.",
    ),
    "JWT-099": ErrorEntry(
        code="JWT-099",
        cause="Unexpected error in JWT/API scanner.",
        fix="Re-run with `--verbose` and inspect logs; file an issue if reproducible.",
    ),
    "CLOUD-099": ErrorEntry(
        code="CLOUD-099",
        cause="Unexpected error in cloud connector.",
        fix="Re-run with `--verbose` and inspect logs; verify cloud credentials.",
    ),
    "DB-099": ErrorEntry(
        code="DB-099",
        cause="Unexpected error in database scanner.",
        fix="Re-run with `--verbose` and inspect logs; verify DB credentials and network reach.",
    ),

    # --- Reserved per-domain config-error codes (NNN-001 in non-INSTALL domains) ---
    "JWT-001": ErrorEntry(
        code="JWT-001",
        cause="JWT scanner configuration is invalid.",
        fix="Check `jwt_scanner` block in your config.yaml; see docs/configuration.md.",
    ),
    "SSH-001": ErrorEntry(
        code="SSH-001",
        cause="SSH/SAML scanner configuration is invalid.",
        fix="Check `ssh_scanner` block in your config.yaml; see docs/configuration.md.",
    ),

    # --- Reserved per-domain timeout codes (dormant; not actively written today) ---
    "TLS-002": ErrorEntry(
        code="TLS-002",
        cause="TLS scanner timed out for a target.",
        fix="Increase the per-host timeout in config.yaml or exclude unreachable hosts.",
    ),
    "SSH-002": ErrorEntry(
        code="SSH-002",
        cause="SSH scanner timed out for a target.",
        fix="Increase the per-host timeout in config.yaml or exclude unreachable hosts.",
    ),
}


CATEGORY_TO_CODE: dict[str, str] = {
    "missing_extra": "INSTALL-001",
    "coverage_gap": "CBOM-001",
    # "exception", "config", "invalid_input", "timeout" are dispatched at render time
    # using the scanner host/label — see callers in CLI/dashboard render code.
}


def format_error(code: str) -> str:
    """Return the canonical operator-facing error string.

    Format: `[QRK-<code>] <cause> Fix: <fix>`
    Unknown codes return `[QRK-<code>] Unknown error code.`
    """
    entry = ERROR_REGISTRY.get(code)
    if entry is None:
        return f"[QRK-{code}] Unknown error code."
    return f"[QRK-{entry.code}] {entry.cause} Fix: {entry.fix}"


def error_for(code: str) -> ErrorEntry | None:
    """Return the ErrorEntry registered under ``code`` or ``None`` if absent.

    Read-only registry lookup used by callers that need the structured
    record (e.g. CMVP refresh exit handlers) rather than the rendered string.
    """
    return ERROR_REGISTRY.get(code)


__all__ = ["ErrorEntry", "ERROR_REGISTRY", "CATEGORY_TO_CODE", "format_error", "error_for"]
