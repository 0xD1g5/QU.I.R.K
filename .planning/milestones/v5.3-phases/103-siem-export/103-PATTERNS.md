# Phase 103: SIEM Export - Pattern Map

**Mapped:** 2026-05-24
**Files analyzed:** 11 (7 implementation + 4 test files collapsed to 6 test targets)
**Analogs found:** 11 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/siem/config.py` | config-loader | request-response | `quirk/notify/config.py` | exact |
| `quirk/siem/formatter.py` | utility/transform | transform | `quirk/notify/payload.py` (`to_integration_payload`) | role-match |
| `quirk/siem/transport.py` | service/channel | request-response | `quirk/notify/channels/webhook.py` (`send_webhook`) | role-match |
| `quirk/siem/dispatcher.py` | service/orchestrator | request-response | `quirk/notify/dispatcher.py` | exact |
| `quirk/siem/__init__.py` | config | — | `quirk/notify/__init__.py` (empty) | exact |
| `quirk/cli/export_cmd.py` | CLI entrypoint | request-response | `quirk/cli/analyze_token_cmd.py` | exact |
| `run_scan.py` (modify) | CLI entrypoint | request-response | `run_scan.py` lines 485-494 (analyze-token/token blocks) | exact |
| `quirk/cli/scheduler_cmd.py` (modify) | scheduler/hook | event-driven | `quirk/cli/scheduler_cmd.py` lines 171-184 (notify hook) | exact |
| `tests/test_siem_config.py` | test | — | `tests/test_notify_config.py` | exact |
| `tests/test_siem_formatter.py` + `test_siem_payload_whitelist.py` | test | — | `tests/test_notify_payload_whitelist.py` | exact |
| `tests/test_siem_transport.py` + `test_siem_dispatcher.py` + `test_export_cmd_wiring.py` | test | — | `tests/test_notify_dispatcher.py` | role-match |

---

## Pattern Assignments

### `quirk/siem/config.py` (config-loader, request-response)

**Analog:** `quirk/notify/config.py` (entire file, 185 lines)

**Imports pattern** (lines 16-22):
```python
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import yaml
```

**Dataclass pattern** (lines 30-82 — pick the simplest one, `WebhookNotifyCfg`):
```python
@dataclass
class WebhookNotifyCfg:
    url_env: str
    hmac_key_env: Optional[str] = None
    timeout_seconds: int = 10
```

Model `SiemCfg` the same way — flat dataclass, all fields have defaults except the required `host`:
```python
@dataclass
class SiemCfg:
    host: str
    port: int = 514
    protocol: str = "udp"          # "udp" or "tcp"
    export_after_scan: bool = False
    timeout_seconds: int = 5
```

**Config-load public API pattern** (lines 159-184 — copy verbatim, replace "notifications" with "siem"):
```python
def load_notifications_config(path: str | None = None) -> "NotifyCfg | None":
    effective_path = path or os.environ.get("QUIRK_CONFIG_PATH")
    if not effective_path or not os.path.isfile(effective_path):
        return None
    try:
        with open(effective_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        notify_raw = (raw or {}).get("notifications")
        if not notify_raw:
            return None
        return _parse_notify_cfg(notify_raw)
    except Exception:
        # Binary / malformed / non-YAML files (Pitfall 1) return None silently.
        return None
```

**Critical constraint to copy verbatim (lines 6-15 docstring):**
The module docstring MUST include the "CRITICAL CONSTRAINT (Pitfall 1)" warning that `QUIRK_CONFIG_PATH` is a YAML path, not the scheduler's SQLite DB path. Copy the warning block and update it for SIEM.

**Key difference from analog:** `load_siem_config()` takes NO path argument from the scheduler — it always resolves via `QUIRK_CONFIG_PATH`. The function signature is `load_siem_config(path: str | None = None)`, but the scheduler hook MUST call it as `load_siem_config()` with no args.

---

### `quirk/siem/formatter.py` (utility/transform)

**Analog:** `quirk/notify/payload.py` — specifically the `to_integration_payload()` whitelist pattern (lines 126-171)

**Imports pattern:**
```python
from __future__ import annotations
```
No external imports — pure string transformation.

**Whitelist function pattern** (modeled on `to_integration_payload`, lines 126-171):
```python
def to_integration_payload(report: TrendReport) -> dict:
    return {
        "current_score": report.current_score,
        ...
        # EXCLUDED: topology fields
    }
```

Apply the same EXPLICIT field extraction discipline for `to_cef_finding()` — construct the result dict only from named `.get()` calls, never `{k: v for k, v in finding.items() if k not in FORBIDDEN}`. This is the ISEC-03 enforcement rule (payload.py line 148 comment).

**Two-function escaping pattern** (from RESEARCH.md Pattern 1 — no codebase analog exists; copy from research):
```python
def _cef_escape_header(value: str) -> str:
    """CEF header field escaping: backslash and pipe only."""
    return value.replace("\\", "\\\\").replace("|", "\\|")

def _cef_escape_extension(value: str) -> str:
    """CEF extension value escaping: backslash, equals, and newlines."""
    return (
        value
        .replace("\\", "\\\\")
        .replace("=", "\\=")
        .replace("\r\n", "\\n")
        .replace("\r", "\\n")
        .replace("\n", "\\n")
    )
```

**Gotcha:** Backslash MUST be escaped FIRST in both functions. The order of the remaining replacements is irrelevant, but the `"\\"`→`"\\\\"` step must precede all others.

**Severity mapping and build_cef_event** (no codebase analog — use RESEARCH.md Pattern 1 directly):
```python
_CEF_SEVERITY = {"CRITICAL": 10, "HIGH": 8, "MEDIUM": 5, "LOW": 3}

def build_cef_event(finding: dict, version: str) -> str:
    ...
    signature = finding.get("category") or finding.get("id") or _slugify(finding.get("title", "UNKNOWN"))
    ...
```

`category` is NOT present in actual findings JSON (confirmed from `output/findings-20260522-011356.json`). The fallback to a slugified `title` is mandatory, not optional.

---

### `quirk/siem/transport.py` (service/channel, request-response)

**Analog:** `quirk/notify/channels/webhook.py` — `send_webhook()` function pattern (lines 44-94)

**Imports pattern** (replace urllib with socket):
```python
from __future__ import annotations

import logging
import socket

logger = logging.getLogger(__name__)
```

**Send function pattern** — mirror `send_webhook` (lines 44-94) but for syslog:
- `send_webhook` takes `(cfg, payload)` and raises on failure — caller wraps in try/except
- `send_syslog_raw` takes `(cef_msg, host, port, protocol, timeout)` and raises `OSError` on failure — caller wraps in try/except (same contract)
- Do NOT call `validate_external_url` — syslog hosts are internal by design (CONTEXT.md D-02). Instead validate that `host` is non-empty and `1 <= port <= 65535` only.

**Core send pattern** (from RESEARCH.md Pattern 2 — use raw socket, not SysLogHandler):
```python
def send_syslog_raw(cef_msg: str, host: str, port: int, protocol: str = "udp",
                    timeout: int = 5) -> None:
    pri = (1 * 8) + 4   # LOG_USER=1, LOG_WARNING=4 → <12>
    payload = f"<{pri}>{cef_msg}".encode("utf-8")
    socktype = socket.SOCK_STREAM if protocol == "tcp" else socket.SOCK_DGRAM
    with socket.socket(socket.AF_INET, socktype) as sock:
        sock.settimeout(timeout)
        if socktype == socket.SOCK_STREAM:
            sock.connect((host, port))
            sock.sendall(payload)
        else:
            sock.sendto(payload, (host, port))
```

**Key difference from analog:** `send_webhook` validates SSRF via `validate_external_url`. `send_syslog_raw` must NOT do this — syslog collectors are internal. Validate host/port format only.

---

### `quirk/siem/dispatcher.py` (service/orchestrator, request-response)

**Analog:** `quirk/notify/dispatcher.py` (entire file, 270 lines)

**Imports pattern** (lines 20-35):
```python
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from quirk.models import IntegrationDelivery
from quirk.util.safe_exc import safe_str

logger = logging.getLogger(__name__)
```

**Per-channel try/except + audit row pattern** (lines 203-220 — Slack block is cleanest example):
```python
row_slack = IntegrationDelivery(
    scan_id=scan_id,
    destination="slack",
    status="ok",
    attempted_at=datetime.now(timezone.utc).replace(tzinfo=None),
    error_summary=None,
)
try:
    _channel_send_slack(notify_cfg.slack, summary)
except Exception as exc:
    row_slack.status = "failed"
    row_slack.error_summary = safe_str(exc)
    logger.warning("Delivery failed (slack): %s", safe_str(exc))
audit_rows.append(row_slack)
```

**Single-commit audit row pattern** (lines 262-269 — WR-01):
```python
for row in audit_rows:
    db.add(row)
try:
    db.commit()
except Exception as exc:
    logger.warning("Audit row commit failed: %s", safe_str(exc))
```

**Key differences from analog:**
- No trend computation, no trigger evaluation, no fan-out to multiple channels.
- Per-finding loop replaces per-channel loop: for each finding, call `to_cef_finding()` → `build_cef_event()` → `send_syslog_raw()`, catch exceptions per-finding.
- One `IntegrationDelivery` row per batch (all findings for one scan), not per finding — `destination="siem"`, `finding_hash=None`.
- `export_after_scan_hook(run, schedule, db)` — public entry point from scheduler; loads SiemCfg, checks `cfg.export_after_scan`, locates findings JSON from `run.scan_output_path`, calls `export_findings()`.

---

### `quirk/siem/__init__.py`

Empty file. Copy `quirk/notify/__init__.py` pattern (empty or minimal re-exports). No content needed.

---

### `quirk/cli/export_cmd.py` (CLI entrypoint, request-response)

**Analog:** `quirk/cli/analyze_token_cmd.py` (entire file, 263 lines)

**Imports pattern** (lines 22-31):
```python
from __future__ import annotations

import argparse
import sys

from quirk.util.safe_exc import safe_str
```

**Entry point function pattern** (lines 176-183):
```python
def run_analyze_token(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="quirk analyze-token",
        description="...",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="...",
    )
```

Mirror as `run_export(argv: list[str]) -> None` with `prog="quirk export"`. Same signature, same pattern.

**Argparse structure** (copy the flag-then-dispatch pattern from lines 200-261):
```python
parser.add_argument("--siem", action="store_true", help="Export findings to SIEM via syslog/CEF")
parser.add_argument("--input", default=None, metavar="PATH",
                    help="Path to findings-*.json (default: latest in output-dir)")
parser.add_argument("--output-dir", default="output",
                    help="Output directory to search for latest findings-*.json")
args = parser.parse_args(argv)
if not args.siem:
    parser.print_help()
    sys.exit(1)
```

**Findings file discovery** (no codebase analog — use RESEARCH.md Don't-Hand-Roll table):
```python
from pathlib import Path
import os

def _find_latest_findings(output_dir: str) -> str | None:
    candidates = list(Path(output_dir).glob("findings-*.json"))
    if not candidates:
        return None
    return str(max(candidates, key=lambda p: p.stat().st_mtime))
```

**Error handling pattern** (lines 228-238 from analyze_token_cmd.py):
```python
try:
    info = _decode_token(raw_token)
except jwt.exceptions.DecodeError:
    print("INFO: ...")
    sys.exit(0)
except Exception as exc:
    print(f"ERROR: ...: {safe_str(exc)}")
    sys.exit(2)
```

Mirror: wrap the entire export flow in try/except; use `safe_str(exc)` on all exception outputs.

---

### `run_scan.py` (modify — add export interception block)

**Analog:** `run_scan.py` lines 485-494 (the `analyze-token` + `token` two-liner blocks)

**Exact pattern to copy** (lines 484-494):
```python
# --- analyze-token subcommand: intercept before scan argparse (Phase 94 TOKEN-01) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "analyze-token":
    from quirk.cli.analyze_token_cmd import run_analyze_token
    run_analyze_token(_sys.argv[2:])
    return

# --- token subcommand: intercept before scan argparse (Phase 102 AUTH-01) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "token":
    from quirk.cli.token_cmd import run_token
    run_token(_sys.argv[2:])
    return
```

**New block to add** after the `token` block (after line 494):
```python
# --- export subcommand: intercept before scan argparse (Phase 103 SIEM-01/02) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "export":
    from quirk.cli.export_cmd import run_export
    run_export(_sys.argv[2:])
    return
```

Three lines. No other changes to `run_scan.py` logic.

---

### `quirk/cli/scheduler_cmd.py` (modify — add after-scan SIEM hook)

**Analog:** `quirk/cli/scheduler_cmd.py` lines 171-184 (the Phase 101 notification dispatch hook)

**Exact pattern to copy** (lines 171-184):
```python
# Phase 101 NOTIFY-01: dispatch notifications for this completed run.
# Deferred import avoids circular-import between scheduler_cmd and dispatcher.
# Full try/except: notification failure must NEVER propagate or corrupt the
# scan record — the run row is already committed above (NOTIFY-07, T-101-10).
try:
    from quirk.notify.dispatcher import dispatch_notifications
    dispatch_notifications(run=run, schedule=schedule, db=db)
except Exception as exc:  # noqa: BLE001
    import logging as _logging
    from quirk.util.safe_exc import safe_str as _safe_str
    _logging.getLogger(__name__).warning(
        "Notification dispatch error (scan record unaffected): %s",
        _safe_str(exc),
    )
```

**New block to add** immediately after the notification block (after line 184, before `return run`):
```python
# Phase 103 SIEM-01: after-scan SIEM export (when export_after_scan: true in [siem] config).
# Same deferred-import + try/except isolation: SIEM failure must NEVER propagate.
try:
    from quirk.siem.dispatcher import export_after_scan_hook
    export_after_scan_hook(run=run, schedule=schedule, db=db)
except Exception as exc:  # noqa: BLE001
    import logging as _logging
    from quirk.util.safe_exc import safe_str as _safe_str
    _logging.getLogger(__name__).warning(
        "SIEM export error (scan record unaffected): %s",
        _safe_str(exc),
    )
```

**Critical constraint:** The `export_after_scan_hook` function in `dispatcher.py` MUST call `load_siem_config()` with NO arguments — not `load_siem_config(config_path)` where `config_path` is the scheduler's SQLite DB path.

---

## Test Pattern Assignments

### `tests/test_siem_config.py`

**Analog:** `tests/test_notify_config.py` (entire file, 253 lines)

Copy the entire test structure verbatim, replacing:
- `load_notifications_config` → `load_siem_config`
- `NotifyCfg` / `SlackNotifyCfg` / etc. → `SiemCfg`
- `[notifications]` YAML block → `[siem]` YAML block
- `trigger_score_floor` → `port`, `protocol`, `export_after_scan`, `timeout_seconds`

**Key tests to preserve exactly:**
- `test_no_env_no_path_returns_none` (lines 90-95) — unset env → None
- `test_binary_file_returns_none` (lines 218-225) — SQLite .db → None (Pitfall 2 guard)
- `test_binary_env_path_returns_none` (lines 227-233) — SQLite via env → None

**DB-path trap test** (new, no analog):
```python
def test_db_path_returns_none(self, tmp_path, monkeypatch):
    """Pitfall 2: scheduler --config SQLite DB passed to load_siem_config → None."""
    db_file = tmp_path / "quirk.db"
    db_file.write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)
    monkeypatch.delenv("QUIRK_CONFIG_PATH", raising=False)
    from quirk.siem.config import load_siem_config
    result = load_siem_config(path=str(db_file))
    assert result is None
```

---

### `tests/test_siem_formatter.py` + `tests/test_siem_payload_whitelist.py`

**Analog:** `tests/test_notify_payload_whitelist.py` (entire file, 329 lines) for structure

The payload whitelist test pattern (lines 72-87):
```python
EXPECTED_KEYS = frozenset({...})
FORBIDDEN_KEYS = frozenset({"host", "port", ...})

class TestToIntegrationPayloadWhitelist:
    def test_exact_key_set_present(self): ...
    def test_topology_keys_absent_even_with_samples(self): ...
```

Apply same pattern for `to_cef_finding()` — define `ALLOWED_FIELDS` and `FORBIDDEN_FIELDS`, assert only allowed fields present, assert `compliance`, `cert_pem`, `cert_sans` absent.

**CEF escaping tests** (no analog — unique to this phase):
- `test_header_escaping` — backslash becomes `\\`, pipe becomes `\|`, equals is NOT escaped
- `test_extension_escaping` — backslash becomes `\\`, equals becomes `\=`, newline becomes literal `\n`
- `test_escaping_backslash_first` — input `\|` becomes `\\|` not `\\\|`
- `test_severity_mapping` — CRITICAL→10, HIGH→8, MEDIUM→5, LOW→3
- `test_cef_header_field_count` — `build_cef_event(finding, version).split("|")` has exactly 8 parts
- `test_category_fallback_when_absent` — finding with no `category` key → signature derived from title slug

---

### `tests/test_siem_transport.py`

**Analog:** `tests/test_notify_dispatcher.py` (overall test DB setup) + RESEARCH.md socketserver pattern

**socketserver UDP capture pattern** (from RESEARCH.md Code Examples):
```python
import socketserver, threading

class _UDPCapture(socketserver.UDPServer):
    allow_reuse_address = True
    captured = []
    class _Handler(socketserver.BaseRequestHandler):
        def handle(self):
            self.server.captured.append(self.request[0])
    def __init__(self, host, port):
        super().__init__((host, port), self._Handler)

def test_send_cef_udp_delivers_to_receiver():
    server = _UDPCapture("127.0.0.1", 0)
    port = server.server_address[1]
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()
    send_syslog_raw("CEF:0|...", "127.0.0.1", port, "udp")
    t.join(timeout=2)
    assert server.captured
    assert b"CEF:0" in server.captured[0]
```

For TCP, use `socketserver.TCPServer` with same pattern. Port 0 lets the OS assign a free port.

---

### `tests/test_siem_dispatcher.py`

**Analog:** `tests/test_notify_dispatcher.py` lines 30-64 (DB setup helpers)

**DB setup pattern** (lines 30-34):
```python
def _make_db(tmp_path):
    db_path = str(tmp_path / "quirk_test.db")
    init_db(db_path)
    return db_path
```

**Scheduler isolation test** — model on the dispatcher's `try/except` block test (NOTIFY-07). Monkeypatch `send_syslog_raw` to raise `OSError`; assert `IntegrationDelivery` row with `status="failed"` is written; assert scan record (`ScheduledRun`) is unaffected.

**After-scan hook no-op test** — set `export_after_scan=False` in SiemCfg; assert `send_syslog_raw` is never called.

---

### `tests/test_export_cmd_wiring.py`

**Analog:** `tests/test_notify_dispatcher.py` overall pattern; argparse shape from `analyze_token_cmd.py`

**CLI wiring test** — mock `run_scan.py` argv with `["export", "--siem"]`; assert `run_export` is called (monkeypatch import). Also test:
- `quirk export` with no flags → `sys.exit(1)`
- `quirk export --siem --input /path/to/findings.json` → correct path passed
- `_find_latest_findings(output_dir)` with two findings files → returns the newer one

---

## Shared Patterns

### QUIRK_CONFIG_PATH Load Discipline
**Source:** `quirk/notify/config.py` lines 159-184 + docstring lines 6-15
**Apply to:** `quirk/siem/config.py::load_siem_config()` and `quirk/siem/dispatcher.py::export_after_scan_hook()`

The canonical pattern: `effective_path = path or os.environ.get("QUIRK_CONFIG_PATH")`. The scheduler hook calls `load_siem_config()` with NO arguments — never passes the scheduler's `config_path` (SQLite DB) into this function.

### safe_str on all exceptions
**Source:** `quirk/notify/dispatcher.py` lines 215, 240, 268
**Apply to:** `quirk/siem/dispatcher.py`, `quirk/cli/export_cmd.py`

```python
row.error_summary = safe_str(exc)
logger.warning("...: %s", safe_str(exc))
```

Never use `str(exc)` or `repr(exc)` directly. Always wrap with `safe_str` from `quirk.util.safe_exc`.

### Single-commit audit row pattern (WR-01)
**Source:** `quirk/notify/dispatcher.py` lines 201, 262-269
**Apply to:** `quirk/siem/dispatcher.py`

Collect all `IntegrationDelivery` rows into a list during the delivery loop. Call `db.add(row)` and `db.commit()` ONCE at the end, inside its own try/except. Never commit inside the per-finding loop.

### Deferred import + try/except for after-scan hooks
**Source:** `quirk/cli/scheduler_cmd.py` lines 171-184
**Apply to:** New SIEM after-scan block in `scheduler_cmd.py` (lines 185-194 after modification)

```python
try:
    from quirk.siem.dispatcher import export_after_scan_hook
    export_after_scan_hook(run=run, schedule=schedule, db=db)
except Exception as exc:  # noqa: BLE001
    import logging as _logging
    from quirk.util.safe_exc import safe_str as _safe_str
    _logging.getLogger(__name__).warning("...: %s", _safe_str(exc))
```

The deferred import (`from quirk.siem.dispatcher import ...` inside the try block) avoids circular imports and ensures that an import error in the SIEM module never crashes the scheduler.

### `from __future__ import annotations`
**Source:** All existing `quirk/` Python modules
**Apply to:** All new Python files

Every new module starts with `from __future__ import annotations` on line 1.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `quirk/siem/formatter.py` (CEF escaping + `build_cef_event`) | utility | transform | No CEF/syslog formatter exists in the codebase; ArcSight spec is the source (see RESEARCH.md Pattern 1) |
| `tests/test_siem_transport.py` (socketserver capture) | test | — | No in-test socket capture pattern exists; stdlib `socketserver` is the only reference (RESEARCH.md Code Examples) |

---

## Critical Gotchas for Planner

1. **`category` field is absent from actual findings JSON.** The `build_cef_event()` and `to_cef_finding()` implementations MUST implement the fallback: `finding.get("category") or finding.get("id") or _slugify(finding.get("title", "UNKNOWN"))`. This is confirmed from `output/findings-20260522-011356.json` which contains only: `severity`, `host`, `port`, `title`, `description`, `recommendation`, `compliance`.

2. **CEF two distinct escape functions, not one.** Header escapes `\` and `|`. Extension escapes `\`, `=`, `\n`, `\r\n`, `\r`. Using the same function for both will break SIEM parsing. Tests must cover both functions independently.

3. **Backslash escape order is mandatory.** In both escape functions, `value.replace("\\", "\\\\")` MUST execute before all other replacements. If placed last, already-escaped characters will be double-escaped.

4. **Do NOT block internal/loopback SIEM hosts.** Unlike `send_webhook` (which calls `validate_external_url`), `send_syslog_raw` MUST NOT call `validate_external_url`. Syslog collectors are internal by design (CONTEXT.md D-02). Validate only: `host` is non-empty, `1 <= port <= 65535`.

5. **SIEM dispatcher is NOT a drift-trigger system.** The Phase 101 `dispatch_notifications` evaluates `should_notify()` and fans out to multiple channels. The SIEM `export_findings()` is simpler: load findings JSON, call whitelist + formatter + transport per finding, write one audit row. No trend computation.

6. **`to_cef_finding()` must use explicit field extraction** (named `.get()` calls only), NOT an exclusion-list comprehension. This is the ISEC-03 enforcement from `to_integration_payload()` (payload.py lines 127-148 comments).

7. **`IntegrationDelivery.destination = "siem"` and `finding_hash = None`.** The `finding_hash` column exists for future per-finding dedup (phases 104/105); set to None for phase 103. Per-batch row, not per-finding.

---

## Metadata

**Analog search scope:** `quirk/notify/`, `quirk/cli/`, `tests/test_notify_*`, `run_scan.py`, `quirk/models.py`, `quirk/util/safe_exc.py`
**Files read:** 12
**Pattern extraction date:** 2026-05-24
