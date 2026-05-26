# Phase 108: Sensor Push CLI + Windows CI - Pattern Map

**Mapped:** 2026-05-25
**Files analyzed:** 10 (new or modified)
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/cli/sensor_cmd.py` | CLI module | request-response + file-I/O | `quirk/cli/token_cmd.py` + `quirk/cli/scheduler_cmd.py` | exact (composite) |
| `quirk/cli/console_cmd.py` | CLI module | file-I/O | `quirk/cli/token_cmd.py` (subparser shape) | role-match |
| `quirk/util/no_redirect.py` | utility | request-response | `quirk/notify/channels/webhook.py` lines 29–41 | exact (extract) |
| `run_scan.py` (dispatch blocks) | entrypoint | request-response | `run_scan.py` lines 490–506 (token + export blocks) | exact |
| `quirk/cli/scheduler_cmd.py` (POSIX fixes) | CLI module | event-driven | same file, lines 135–137 and 258–259 | exact |
| `pyproject.toml` (new deps) | config | — | `pyproject.toml` lines 11–32 (dependencies list) | exact |
| `tests/test_sensor_cmd.py` | test | request-response + file-I/O | `tests/scanner/test_phase57_invariants.py` | role-match |
| `tests/test_sensor_no_verify_false.py` | test | static-analysis | `tests/scanner/test_phase57_invariants.py` lines 21–54 | exact |
| `tests/test_no_redirect_extraction.py` | test | static-analysis | `tests/scanner/test_phase57_invariants.py` | role-match |
| `.github/workflows/python-ci.yml` (new Windows job) | CI config | — | `.github/workflows/python-staleness.yml` | role-match |

---

## Pattern Assignments

### `quirk/cli/sensor_cmd.py` (CLI module, request-response + file-I/O)

**Analogs:** `quirk/cli/token_cmd.py` (atomic YAML write, token idiom) + `quirk/cli/scheduler_cmd.py` (subprocess scan invoke)

---

**Imports pattern** — copy from `quirk/cli/token_cmd.py` lines 1–10 and `quirk/cli/scheduler_cmd.py` lines 1–14:

```python
from __future__ import annotations

import argparse
import hashlib
import hmac as _hmac
import json
import os
import secrets
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import yaml
import zstandard
from platformdirs import user_config_dir, user_data_dir
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

import quirk
from quirk.util.no_redirect import _NoRedirectHandler          # STAB-02 prerequisite
from quirk.util.url_allowlist import validate_external_url
```

---

**Subparser pattern** — copy from `run_scan.py` lines 410–456 (`compliance` block) and `quirk/cli/token_cmd.py` lines 53–97:

```python
def run_sensor(argv: list[str]) -> None:
    """Main entrypoint for `quirk sensor` subcommands.

    argv = sys.argv[2:] — does NOT include 'quirk' or 'sensor'.
    """
    parser = argparse.ArgumentParser(
        prog="quirk sensor",
        description="Distributed sensor management (Phase 108)",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    enroll_p = sub.add_parser("enroll", help="Enroll sensor against a console")
    enroll_p.add_argument("console_url", help="Console base URL (https://...)")
    enroll_p.add_argument("--segment", required=True, help="Network segment label")
    enroll_p.add_argument("--engagement", default=None, help="Optional engagement tag")
    enroll_p.add_argument("--config", default=None, help="Override sensor.yaml path")

    push_p = sub.add_parser("push", help="Run local scan and push results to console")
    push_p.add_argument("--config", default=None, help="Override sensor.yaml path")
    push_p.add_argument("--scan-config", default="config.yaml", help="Scan config.yaml path")

    export_p = sub.add_parser("export-results", help="Export results to .qpush file for air-gap transfer")
    export_p.add_argument("--config", default=None, help="Override sensor.yaml path")
    export_p.add_argument("--scan-config", default="config.yaml", help="Scan config.yaml path")
    export_p.add_argument("--output", default=".", help="Directory to write .qpush file")

    args = parser.parse_args(argv)
    if args.action == "enroll":
        _cmd_enroll(args)
    elif args.action == "push":
        _cmd_push(args)
    elif args.action == "export-results":
        _cmd_export_results(args)
```

---

**Atomic YAML write pattern** — copy EXACTLY from `quirk/cli/token_cmd.py` lines 13–50:

```python
def _write_sensor_config(config_path: str, sensor_cfg: dict) -> None:
    """Write sensor.yaml using atomic tempfile + os.replace (crash-safe).

    dir= param MUST be same directory as target so os.replace is same-filesystem.
    Parent directory must already exist (call os.makedirs(..., exist_ok=True) first).
    """
    dir_ = os.path.dirname(os.path.abspath(config_path))
    fd, tmp = tempfile.mkstemp(dir=dir_, prefix=".quirk_sensor_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(sensor_cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        os.replace(tmp, config_path)  # atomic on POSIX; best-effort on Windows
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
```

The parent directory must be created before calling `tempfile.mkstemp`:

```python
config_dir = user_config_dir("quirk")
os.makedirs(config_dir, exist_ok=True)
sensor_yaml_path = os.path.join(config_dir, "sensor.yaml")
```

---

**One-time token idiom** — copy from `quirk/cli/token_cmd.py` lines 99–100 and `quirk/models.py` lines 291–312:

```python
# In _cmd_enroll():
sensor_id = str(uuid.uuid4())
raw_token = secrets.token_urlsafe(32)
token_hash = hashlib.sha256(raw_token.encode()).hexdigest()  # 64-char hex

sensor_cfg = {
    "console_url": console_url,
    "sensor_id": sensor_id,
    "segment": args.segment,
    "engagement": args.engagement,   # may be None
    "sensor_version": quirk.__version__,
}
_write_sensor_config(sensor_yaml_path, sensor_cfg)

# Print once — NEVER write raw_token to sensor.yaml
print(f"Enrollment token (shown once — save it now):\n{raw_token}", flush=True)
print("WARNING: this token will not be shown again.", file=sys.stderr)
```

---

**Subprocess scan invocation** — copy from `quirk/cli/scheduler_cmd.py` lines 141–161:

```python
def _run_local_scan(scan_config: str, output_dir: Path) -> int:
    """Invoke run_scan as subprocess. Returns proc.returncode."""
    cmd = [
        sys.executable,
        "-m",
        "run_scan",
        "--config",
        scan_config,
        "--output",
        str(output_dir),
    ]
    # list-form Popen — no shell=True, no metacharacter expansion (T-63-07 pattern)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _stdout, _stderr = proc.communicate()
    return proc.returncode
```

---

**zstd compress + HMAC sign pattern** (from RESEARCH.md Pattern 5 — no existing codebase analog for zstd):

```python
def _build_compressed_payload(envelope: dict) -> bytes:
    raw = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    return zstandard.ZstdCompressor(level=3).compress(raw)

def _sign(body: bytes, key: bytes) -> str:
    return "hmac-sha256=" + _hmac.new(key, body, hashlib.sha256).hexdigest()
```

---

**tenacity retry pattern** (from RESEARCH.md Pattern 6 — no existing codebase analog):

```python
import httpx

def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, (httpx.ConnectError, httpx.TimeoutException))

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
def _do_push(client: httpx.Client, url: str, headers: dict, content: bytes) -> httpx.Response:
    resp = client.post(url, headers=headers, content=content)
    if resp.status_code >= 500:
        resp.raise_for_status()  # triggers tenacity retry
    return resp

# Caller: verify=True and follow_redirects=False are HARDCODED — no parameters
with httpx.Client(verify=True, follow_redirects=False) as client:
    resp = _do_push(client, push_url, headers, body)
```

---

**Spool management pattern** (file-per-payload, bounded dir — no existing codebase analog; use platformdirs + pathlib):

```python
_SPOOL_MAX_FILES = 100
_SPOOL_MAX_BYTES = 500 * 1024 * 1024  # 500 MB default cap — Claude's discretion

def _spool_payload(payload_id: str, body: bytes) -> None:
    spool_dir = Path(user_data_dir("quirk")) / "spool"
    os.makedirs(spool_dir, exist_ok=True)
    _evict_if_full(spool_dir)
    dest = spool_dir / f"{payload_id}.json.zst"
    dest.write_bytes(body)

def _evict_if_full(spool_dir: Path) -> None:
    files = sorted(spool_dir.glob("*.json.zst"), key=lambda p: p.stat().st_mtime)
    total_bytes = sum(f.stat().st_size for f in files)
    while (len(files) >= _SPOOL_MAX_FILES or total_bytes > _SPOOL_MAX_BYTES) and files:
        evicted = files.pop(0)
        total_bytes -= evicted.stat().st_size
        evicted.unlink()
        print(f"WARNING: spool full — evicted oldest payload: {evicted.name}", file=sys.stderr)
```

---

**Wire envelope shape** (from RESEARCH.md §Wire Contract + `quirk/models.py` lines 315–335):

```python
def _build_envelope(sensor_cfg: dict, endpoints: list) -> dict:
    return {
        "payload_id": str(uuid.uuid4()),
        "pushed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": "1.0.0",
        "sensor_version": sensor_cfg["sensor_version"],
        "sensor_id": sensor_cfg["sensor_id"],
        "segment": sensor_cfg["segment"],
        "findings": [_endpoint_to_dict(ep) for ep in endpoints],
    }
    # NOTE: received_at is NOT included — the console stamps it on ingest (Phase 109)
    # NOTE: all values must be JSON-serializable primitives — no Path objects,
    #       no OS-specific datetime formatting, no backslash path separators.
```

---

### `quirk/cli/console_cmd.py` (CLI module, file-I/O)

**Analog:** `quirk/cli/token_cmd.py` (subparser shape, `run_X` signature)

**Subparser + dispatch pattern** — mirror `token_cmd.py` lines 53–97:

```python
def run_console(argv: list[str]) -> None:
    """Main entrypoint for `quirk console` subcommands.

    argv = sys.argv[2:] — does NOT include 'quirk' or 'console'.
    """
    parser = argparse.ArgumentParser(
        prog="quirk console",
        description="Console-side management for distributed sensors (Phase 108)",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    import_p = sub.add_parser(
        "import-results",
        help="Import a .qpush air-gap file into the console",
    )
    import_p.add_argument("file", help="Path to .qpush file")
    import_p.add_argument("--config", default="config.yaml", help="Console config.yaml path")

    args = parser.parse_args(argv)
    if args.action == "import-results":
        _cmd_import_results(args)
```

**Import-results handler note:** reads the `.qpush` file (same zstd-compressed wire payload as an HTTPS push), then routes to the same ingest path as Phase 109 will provide. In Phase 108, write a stub that deserializes and validates the envelope, printing a summary — the full ingest (DB write) is Phase 109.

---

### `quirk/util/no_redirect.py` (utility, request-response)

**Analog:** `quirk/notify/channels/webhook.py` lines 29–41 AND `quirk/ticketing/servicenow.py` lines 34–47 — both are IDENTICAL; this is a pure extraction.

**Extracted module content** — copy verbatim from `webhook.py` lines 29–41 (the docstring accurately describes the threat model):

```python
"""quirk.util.no_redirect — SSRF redirect guard (STAB-02 extraction).

Extracted from quirk/notify/channels/webhook.py and quirk/ticketing/servicenow.py
where the class was duplicated verbatim. All callers now import from here.
"""
from __future__ import annotations

import urllib.error
import urllib.request


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Block all HTTP redirects to prevent post-validation SSRF bypass.

    urllib.request.urlopen follows 3xx redirects by default via HTTPRedirectHandler.
    An attacker-controlled endpoint returning 302 → http://169.254.169.254/... would
    bypass the validate_external_url() pre-connection check.  This handler refuses
    any redirect by raising HTTPError, keeping the connection to the validated URL.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url, code, "Redirect blocked (SSRF guard)", headers, fp
        )
```

**Callers to update after extraction:**
- `quirk/notify/channels/webhook.py` line 29: remove the class definition; add `from quirk.util.no_redirect import _NoRedirectHandler`
- `quirk/ticketing/servicenow.py` line 34: same replacement

---

### `run_scan.py` dispatch blocks (entrypoint, request-response)

**Analog:** `run_scan.py` lines 490–506 (token and export dispatch blocks — exact same structure)

**Pattern to copy exactly** — lines 490–500 for `token`, lines 497–500 for `export`:

```python
# After line 500 (export block), before the scan argparse:

# --- sensor subcommand: intercept before scan argparse (Phase 108 SENSOR-01/02/03/04) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "sensor":
    from quirk.cli.sensor_cmd import run_sensor
    run_sensor(_sys.argv[2:])
    return

# --- console subcommand: intercept before scan argparse (Phase 108 SENSOR-04) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "console":
    from quirk.cli.console_cmd import run_console
    run_console(_sys.argv[2:])
    return
```

Placement rule: insert after the existing `ticket` block (line 506) and before the `errors` block (line 509), following the existing alphabetical-ish ordering pattern. Lazy import (`from quirk.cli.X import run_X` inside the `if` block) is the established project convention — do not hoist imports to module level.

---

### `quirk/cli/scheduler_cmd.py` POSIX-ism fixes (CLI module, event-driven)

**Analog:** same file — targeted line-level edits

**Fix 1 — relative path at line 135–137:**

Current (line 135–137):
```python
output_dir = (
    Path("output/scheduled") / safe_name / now.strftime("%Y%m%d-%H%M%S")
)
```

Replacement — anchor to `cfg.output.directory`. The function `_dispatch_schedule` takes `(schedule, db, config_path)`. Load config inside the function or pass it:
```python
from quirk.config import load_config
cfg = load_config(config_path)
output_dir = (
    Path(cfg.output.directory) / "scheduled" / safe_name / now.strftime("%Y%m%d-%H%M%S")
)
```

`cfg.output.directory` is confirmed at `quirk/config.py` `OutputCfg.directory` (String attribute, verified in RESEARCH.md assumptions log A3). `load_config` is already imported elsewhere in the module — confirm before adding a second import.

**Fix 2 — unconditional SIGTERM at line 258–259:**

Current (lines 258–259):
```python
signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)
```

Replacement:
```python
signal.signal(signal.SIGINT, _handle_signal)
if sys.platform != "win32":
    signal.signal(signal.SIGTERM, _handle_signal)
```

`sys` is already imported at line 9. No new import needed.

---

### `pyproject.toml` new dependencies (config)

**Analog:** `pyproject.toml` lines 11–32 — existing `[project] dependencies` list

**Pattern to copy:** append to the `dependencies` list following the same `"package>=floor.version"` format. All three packages are NEW — none present anywhere in the file:

```toml
[project]
dependencies = [
    # ... existing entries ...
    "platformdirs>=4.3.0",   # Phase 108 SENSOR-05: cross-OS config/data dirs
    "tenacity>=8.2.0",       # Phase 108 SENSOR-02: retry with exponential backoff
    "zstandard>=0.22.0",     # Phase 108 SENSOR-02/03/04: zstd payload compression
]
```

Do NOT add these to an extras group — they are required for the core sensor runtime, not optional.

---

### `tests/test_sensor_no_verify_false.py` (test, static-analysis)

**Analog:** `tests/scanner/test_phase57_invariants.py` lines 1–54 — copy the `_strip_comments` helper and `test_no_unconditional_verify_false` structure EXACTLY.

**Full pattern to copy** (from `test_phase57_invariants.py` lines 1–54):

```python
"""Phase 108 verify=False grep gate for sensor push client (SENSOR-02)."""
import io
import pathlib
import tokenize

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

SENSOR_FILES = [
    REPO_ROOT / "quirk" / "cli" / "sensor_cmd.py",
    REPO_ROOT / "quirk" / "cli" / "console_cmd.py",
]


def _strip_comments(src: str) -> str:
    """Strip Python comments using tokenize (handles # in string literals correctly).

    Copied from tests/scanner/test_phase57_invariants.py — authoritative version.
    """
    chars = list(src)
    for tok_type, tok_string, tok_start, tok_end, _ in tokenize.generate_tokens(
        io.StringIO(src).readline
    ):
        if tok_type == tokenize.COMMENT:
            lines = src.splitlines(keepends=True)
            start_offset = sum(len(lines[i]) for i in range(tok_start[0] - 1)) + tok_start[1]
            end_offset = sum(len(lines[i]) for i in range(tok_end[0] - 1)) + tok_end[1]
            for i in range(start_offset, end_offset):
                chars[i] = " "
    return "".join(chars)


import pytest

@pytest.mark.parametrize("sensor_file", SENSOR_FILES, ids=lambda p: p.name)
def test_sensor_no_verify_false(sensor_file):
    """SENSOR-02: sensor_cmd.py / console_cmd.py must never use verify=False."""
    src = _strip_comments(sensor_file.read_text())
    assert "verify=False" not in src, (
        f"{sensor_file.name} contains literal verify=False outside comments — "
        "regression of SENSOR-02 TLS enforcement"
    )
```

---

### `tests/test_no_redirect_extraction.py` (test, static-analysis)

**Analog:** `tests/scanner/test_phase57_invariants.py` — static grep pattern

**Pattern to copy:**

```python
"""STAB-02: _NoRedirectHandler must be defined only in quirk/util/no_redirect.py."""
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_no_redirect_importable():
    from quirk.util.no_redirect import _NoRedirectHandler
    import urllib.request
    assert issubclass(_NoRedirectHandler, urllib.request.HTTPRedirectHandler)


def test_no_duplicate_definitions():
    """webhook.py and servicenow.py must NOT define _NoRedirectHandler after extraction."""
    for rel in [
        "quirk/notify/channels/webhook.py",
        "quirk/ticketing/servicenow.py",
    ]:
        src = (REPO_ROOT / rel).read_text()
        assert "class _NoRedirectHandler" not in src, (
            f"{rel} still defines _NoRedirectHandler — STAB-02 extraction incomplete"
        )
```

---

### `.github/workflows/python-ci.yml` Windows smoke job (CI config)

**Analog:** `.github/workflows/python-staleness.yml` (full file — copy job structure)

**Pattern to copy** — mirror the staleness workflow job structure exactly, changing `runs-on` and the test command. The critical constraint is NO `continue-on-error` (SENSOR-06 hard gate):

```yaml
name: Python CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  windows-sensor-smoke:
    name: Windows Sensor Smoke
    runs-on: windows-latest
    # NO continue-on-error — this is a hard gate (SENSOR-06)
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install project and pytest
        run: |
          pip install -e .
          pip install pytest

      - name: Run Windows sensor smoke tests
        run: pytest tests/test_sensor_windows_smoke.py -v
```

The staleness workflow's `pip install -e . && pip install pytest` two-step is the established pattern. The Windows job should NOT add `continue-on-error: true` at any level (job or step).

**`tests/test_sensor_windows_smoke.py` must assert:**
1. `json.dumps(_build_envelope(...))` contains no `"\\"` backslash characters
2. `KeyboardInterrupt` is handled cleanly (process exits 0 or 130, not with a traceback)

---

## Shared Patterns

### SSRF URL Validation
**Source:** `quirk/util/url_allowlist.py` lines 95–161
**Apply to:** `sensor_cmd.py` — call `validate_external_url(console_url)` before any connection in `_cmd_enroll` and `_cmd_push`. Raise `SystemExit(1)` with a clear message if validation fails.
**Usage pattern** (from `quirk/notify/channels/webhook.py` lines 65–69):
```python
from quirk.util.url_allowlist import validate_external_url
result = validate_external_url(console_url)
if not result.ok:
    print(f"ERROR: console URL blocked — {result.reason}", file=sys.stderr)
    sys.exit(1)
```

### Atomic YAML Write (tempfile + os.replace)
**Source:** `quirk/cli/token_cmd.py` lines 39–50
**Apply to:** `sensor_cmd.py` `_write_sensor_config()` — identical idiom; `dir=` MUST be same directory as target (cross-device `os.replace` raises `OSError` otherwise).

### Lazy CLI Dispatch Import
**Source:** `run_scan.py` lines 491–494 (token block), lines 497–500 (export block)
**Apply to:** `run_scan.py` new `sensor` and `console` blocks — import inside the `if` block, never at module top level. Keeps startup time fast and avoids circular import issues.

### `run_X(argv)` Signature Convention
**Source:** `quirk/cli/token_cmd.py` line 53, `quirk/cli/scheduler_cmd.py` line 231
**Apply to:** `sensor_cmd.py:run_sensor(argv)` and `console_cmd.py:run_console(argv)` — `argv` is `sys.argv[2:]`, does not include `quirk` or the subcommand name.

### `sys.exit(0)` After Successful Action
**Source:** `quirk/cli/token_cmd.py` lines 110, 127
**Apply to:** `sensor_cmd.py` — call `sys.exit(0)` at the end of each successful `_cmd_*` handler, matching the token_cmd convention.

### Platform Guard for SIGTERM
**Source:** `quirk/cli/scheduler_cmd.py` lines 258–259 (the fix target itself)
**Apply to:** `scheduler_cmd.py` line 259 — wrap in `if sys.platform != "win32":`. `sys` is already imported at line 9 in that module.

---

## No Analog Found

All files have close analogs in the codebase. The following capabilities use patterns from RESEARCH.md since no existing codebase analog exists:

| Capability | Reason | Reference |
|---|---|---|
| zstd compress/decompress | `zstandard` is not used anywhere in current codebase | RESEARCH.md Pattern 5; zstandard PyPI docs |
| tenacity retry decorator | `tenacity` not used anywhere in current codebase | RESEARCH.md Pattern 6; tenacity PyPI docs |
| platformdirs dir resolution | `platformdirs` not used anywhere in current codebase | RESEARCH.md Code Examples §platformdirs; platformdirs PyPI docs |
| Bounded spool dir (file-per-payload) | No spool/queue pattern exists in codebase | RESEARCH.md Decisions §Store-and-Forward Spool |

---

## Metadata

**Analog search scope:** `quirk/cli/`, `quirk/util/`, `quirk/notify/channels/`, `quirk/ticketing/`, `tests/scanner/`, `run_scan.py`, `.github/workflows/`, `pyproject.toml`
**Files scanned:** 12 (read in full or targeted range)
**Pattern extraction date:** 2026-05-25
