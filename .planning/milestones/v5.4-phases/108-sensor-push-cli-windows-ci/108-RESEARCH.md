# Phase 108: Sensor Push CLI + Windows CI — Research

**Researched:** 2026-05-25
**Domain:** Python CLI dispatch, HTTPS push client, zstd compression, HMAC signing, file-spool, Windows CI
**Confidence:** HIGH (all claims verified from codebase or PyPI registry)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **(106 D-02 / 107):** Enrollment tokens are one-time-use — `secrets.token_urlsafe(32)`, SHA-256 hash stored in `sensor_tokens`; raw token never persisted. Mirrors `token_cmd.py`.
- **(106 D-13):** Bound config carries `sensor_id` (UUID), `segment`, `engagement` (nullable), `sensor_version`; the console-side `sensors` table holds `enrolled_at`, `last_push_at`, `expected_cadence_minutes`.
- **(106 D-15):** Air-gap export writes the identical wire payload (same `payload_id`, `schema_version`, `pushed_at`, zstd compression, HMAC) to a file; import runs it through the same ingest + dedup path. Replay-window check is transport-conditional: ±15-min window applies to HTTPS push only; air-gap import skips the window but keeps `payload_id` dedup.
- **(106 D-05):** Windows = floor in v5.4 — OS-agnostic wire contract, `pip install` on Python 3.11+ with no POSIX deps, POSIX-ism audit (`scheduler_cmd.py:136` relative path → `cfg.output_root`-anchored; `:258-259` SIGTERM → `sys.platform != 'win32'`-guarded), `platformdirs` for dirs, `windows-latest` CI smoke job as a hard gate (no `continue-on-error`). PyInstaller EXE + Scheduled Task + `pywin32` are v5.5/out.
- **(STAB-02):** `_NoRedirectHandler` (currently duplicated in `notify/channels/webhook.py` and `ticketing/servicenow.py`) is extracted to `quirk/util/no_redirect.py`; the sensor push client imports from there. Treat as a sensor-phase prerequisite.
- **Sensor config format:** YAML, at `platformdirs.user_config_dir("quirk")/sensor.yaml`, atomic write (tempfile + `os.replace`), reusing `token_cmd._write_token_to_config` idiom.
- **Spool location:** `platformdirs.user_data_dir("quirk")/spool/`, file-per-payload, naming `{payload_id}.json.zst`, max file count (default 100) + max total-bytes cap, oldest-evicted with warning on full, FIFO retry on next push, delete on HTTP 200 or 409.
- **Air-gap file naming:** `{sensor_id}-{payload_id}.qpush`, one payload per file.
- **CLI structure:** `quirk sensor <enroll|push|export-results>` and `quirk console import-results` matching existing compliance/cmvp subparser pattern.
- **Token display:** `enroll` prints one-time token to stdout with "won't be shown again" warning; not written to file.
- **`verify=True`:** hardcoded, no CLI flag to disable; CI grep gate asserts no `verify=False` in push client.
- **Retry:** tenacity — 5 attempts, exponential backoff 2s→60s cap, retry on connection errors and 5xx only (never 4xx).

### Claude's Discretion

- Exact `platformdirs` app author/name args, spool default byte cap value, and `.qpush` internal envelope layout (as long as it is byte-identical to the HTTPS push body).
- Module organization of `sensor_cmd.py` / `console_cmd.py` and helper factoring.
- Precise CI grep-gate expression and whether the Windows smoke job runs a stub console or asserts on serialized payload bytes directly.

### Deferred Ideas (OUT OF SCOPE)

- PyInstaller frozen EXE, Windows Scheduled Task registration, and signed packaging — v5.5 ceiling per 106 D-05.
- Automatic merge trigger (poll-on-full-check-in) — v5.5 per 106 D-06; merge stays manual.
- Spooled-payload TTL/cleanup job — none in v5.4 per 106 D-10 (low single-tenant volume).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SENSOR-01 | `quirk sensor enroll <console-url> --segment <label>` writes bound config + returns one-time token | token_cmd.py `secrets.token_urlsafe`/SHA-256 pattern; YAML atomic write idiom; `platformdirs.user_config_dir` |
| SENSOR-02 | `quirk sensor push` runs local scan via `run_scan.py`, POSTs result over HTTPS with tenacity retry; `verify=True` enforced + CI grep gate | scheduler_cmd.py subprocess-invoke pattern; httpx already in deps; tenacity NEW dep; `verify=True` grep-gate mirrors test_phase57_invariants.py |
| SENSOR-03 | Console unreachable → spool to bounded file-per-payload dir, retry next push | `platformdirs.user_data_dir`; zstandard NEW dep for `.json.zst` naming; stdlib `pathlib` for dir management |
| SENSOR-04 | `quirk sensor export-results` → transferable `.qpush` file; `quirk console import-results` ingests on air-gapped console | Same wire payload path; byte-identical to HTTPS push body (D-15 invariant) |
| SENSOR-05 | OS-agnostic sensor runtime — POSIX-ism audit; `platformdirs` for dirs | Two concrete targets in `scheduler_cmd.py` (L136, L258-259); `platformdirs` NEW dep; no other POSIX-isms found in sensor-relevant code |
| SENSOR-06 | `windows-latest` CI smoke job as hard gate (no `continue-on-error`); validates no backslash paths in payload, clean shutdown | New GitHub Actions job added to existing workflow; pattern from `dashboard-quality.yml` + `python-staleness.yml` |
| STAB-02 | `_NoRedirectHandler` extracted from two duplicate sites to `quirk/util/no_redirect.py` | Both duplicates confirmed: `webhook.py:29-41` and `servicenow.py:34-47`; identical code |

</phase_requirements>

---

## Summary

Phase 108 is an **implementation phase** with no ambiguous technology choices — the CONTEXT.md + Phase 106/107 decisions lock every meaningful decision. The research task is to surface the exact code locations, dependency gaps, and pitfalls that the planner needs to write concrete, non-ambiguous task instructions.

The phase adds four new CLI modules (`quirk/cli/sensor_cmd.py`, `quirk/cli/console_cmd.py`, a push-client helper, and a spool-manager helper), three new `pyproject.toml` dependencies (`platformdirs`, `tenacity`, `zstandard`), two POSIX-ism fixes in `scheduler_cmd.py`, one extraction (`_NoRedirectHandler` → `quirk/util/no_redirect.py`), two `run_scan.py` dispatch blocks, and one new GitHub Actions job.

**Critical finding:** `docs/architecture-distributed.md` §3.3 states zstandard is "already in the codebase" — this is **incorrect**. `zstandard` does not appear anywhere in `pyproject.toml` or any `quirk/` Python file. It must be added as a new dependency alongside `platformdirs` and `tenacity`. [VERIFIED: grep of full codebase]

**Primary recommendation:** Plan in this order — (1) STAB-02 `_NoRedirectHandler` extraction (prerequisite, zero-risk refactor), (2) `pyproject.toml` dependency additions, (3) POSIX-ism fixes in `scheduler_cmd.py`, (4) `sensor_cmd.py` + `console_cmd.py` implementation, (5) `run_scan.py` dispatch wiring, (6) tests, (7) CI job.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sensor enrollment (config write, token mint) | CLI / Sensor process | Console DB (via future Phase 109) | Sensor-side: writes `sensor.yaml`; console-side enrollment endpoint is Phase 109 |
| Local scan invocation | CLI / Sensor process | — | Subprocess call to `run_scan.py`; no console involvement |
| HTTPS push with retry | CLI / Sensor process | — | httpx client + tenacity; console ingest endpoint is Phase 109 |
| Store-and-forward spool | CLI / Sensor process (filesystem) | — | Bounded file-per-payload dir; retry on next `quirk sensor push` |
| Air-gap export / import | CLI / Sensor + CLI / Console | — | Same wire payload written to file; `console import-results` reads and ingests |
| POSIX-ism fixes | CLI / Scheduler process | — | `scheduler_cmd.py` changes; no other tier affected |
| `_NoRedirectHandler` extraction | Util layer | Notify + Ticketing callers | Pure refactor; all three callers import from new location |
| Windows CI smoke gate | CI / GitHub Actions | — | Hard-gate job on `windows-latest`; does not touch runtime code |

---

## Standard Stack

### Core (already in `pyproject.toml`)

| Library | Current Version | Purpose | Notes |
|---------|-----------------|---------|-------|
| `httpx` | `>=0.28.0` | HTTP client for push | Already a core dep; `verify=True` is default — do not pass `verify=False` |
| `PyYAML` | `>=6.0` | sensor.yaml read/write | Already a core dep; full-file round-trip pattern from `token_cmd.py` |
| `cryptography` | `>=44.0` | `secrets.token_urlsafe`, `hmac` | stdlib `hmac` module used directly (no new dep) |
| `SQLAlchemy` | `>=2.0` | DB access for `sensors`/`sensor_tokens`/`sensor_pushes` | Already a core dep |

[VERIFIED: grep of pyproject.toml]

### New Dependencies (must be added to `pyproject.toml`)

| Library | Latest Version | Purpose | slopcheck |
|---------|---------------|---------|-----------|
| `platformdirs` | 4.4.0 | Cross-OS user config/data directories | [OK] |
| `tenacity` | 9.1.2 | Retry with exponential backoff for push | [OK] |
| `zstandard` | 0.25.0 | zstd level-3 compression for wire payload + spool | [OK] |

[VERIFIED: pip index versions for all three; slopcheck [OK] for all three]

**Installation (add to `[project] dependencies` in `pyproject.toml`):**
```
platformdirs>=4.3.0
tenacity>=8.2.0
zstandard>=0.22.0
```

Note: `tenacity` is already installed in the dev environment (9.1.2 confirmed) but is NOT declared in `pyproject.toml`. It must be added. `platformdirs` and `zstandard` are similarly not declared.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `zstandard` | stdlib `gzip` or `lzma` | zstd is faster and better ratio at level-3; architecture doc locks zstd — not a choice |
| `tenacity` | manual retry loop | tenacity is explicit in SENSOR-02 — not a choice |
| `platformdirs` | hardcoded `~/.config` | SENSOR-05 explicitly requires platformdirs — not a choice |

---

## Package Legitimacy Audit

| Package | Registry | Age | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|
| `platformdirs` | PyPI | ~5 yrs | [OK] | Approved |
| `tenacity` | PyPI | ~9 yrs | [OK] | Approved |
| `zstandard` | PyPI | ~8 yrs | [OK] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
quirk sensor enroll <url> --segment <label>
        |
        v
  [console enrollment endpoint — Phase 109]
        |
  returns: sensor_id (UUID) + one-time token
        |
        v
  write sensor.yaml (atomic tempfile + os.replace)
  platformdirs.user_config_dir("quirk") / sensor.yaml
  print token once to stdout ("won't be shown again")

quirk sensor push
        |
        v
  read sensor.yaml → console_url, sensor_id, segment
        |
        v
  subprocess: sys.executable -m run_scan --config ... --output <tmp_dir>
        |
        v
  read CryptoEndpoint rows from tmp scan DB
        |
        v
  build envelope: payload_id (uuid4), pushed_at (utcnow), schema_version,
                  sensor_version, sensor_id, segment, findings[]
        |
        v
  zstd compress (level=3)
  HMAC-SHA256 over compressed body → X-Sensor-Signature header
        |
        v
  httpx.Client(verify=True).post(console_url + "/api/sensor/push",
      headers={"X-Sensor-Signature": ..., "Authorization": "Bearer <token>"},
      content=<zstd bytes>)
  tenacity: 5 attempts, exp backoff 2s→60s, retry on ConnectError + 5xx only
        |
  200/409 ────→ delete spooled file (if any) → done
  conn error ──→ spool to platformdirs.user_data_dir("quirk")/spool/{payload_id}.json.zst
  4xx ─────────→ abort (no retry — permanent client error)

quirk sensor export-results
        → identical envelope, write to {sensor_id}-{payload_id}.qpush

quirk console import-results <file.qpush>
        → read file, send to same ingest path (Phase 109), skip ±15-min replay window
```

### Recommended Project Structure

```
quirk/
├── cli/
│   ├── sensor_cmd.py       # run_sensor() — enroll, push, export-results subcommands
│   ├── console_cmd.py      # run_console() — import-results subcommand
│   └── ...existing...
├── util/
│   ├── no_redirect.py      # _NoRedirectHandler extracted from webhook.py + servicenow.py
│   └── ...existing...
run_scan.py                 # two new dispatch blocks: "sensor" and "console"
```

### Pattern 1: CLI Dispatch (exact existing pattern in `run_scan.py:main()`)

**What:** Intercept `sys.argv[1]` before scan argparse, lazy-import `run_X` from `quirk/cli/X_cmd.py`, call with `_sys.argv[2:]`.
**When to use:** All new CLI subcommands.

```python
# Source: run_scan.py:491-494 (token dispatch — mirror this exactly)
if len(_sys.argv) > 1 and _sys.argv[1] == "sensor":
    from quirk.cli.sensor_cmd import run_sensor
    run_sensor(_sys.argv[2:])
    return

if len(_sys.argv) > 1 and _sys.argv[1] == "console":
    from quirk.cli.console_cmd import run_console
    run_console(_sys.argv[2:])
    return
```

These blocks belong in `main()`, ordered with the existing intercepts (after `token` at L491, before scan argparse). [VERIFIED: run_scan.py:363-515]

### Pattern 2: Nested Subparser (compliance/cmvp pattern)

**What:** `add_subparsers(dest="action", required=True)` on the parent parser, then `add_parser` for each subcommand.
**When to use:** `quirk sensor enroll|push|export-results` and `quirk console import-results`.

```python
# Source: run_scan.py:416-446 (compliance/cmvp — mirror for sensor)
parser = argparse.ArgumentParser(prog="quirk sensor", ...)
sub = parser.add_subparsers(dest="action", required=True)
enroll_p = sub.add_parser("enroll", ...)
enroll_p.add_argument("console_url", ...)
enroll_p.add_argument("--segment", required=True, ...)
push_p = sub.add_parser("push", ...)
export_p = sub.add_parser("export-results", ...)
args = parser.parse_args(argv)
```

[VERIFIED: run_scan.py:410-447]

### Pattern 3: Atomic YAML Write (token_cmd.py idiom — reuse for sensor.yaml)

```python
# Source: quirk/cli/token_cmd.py:13-50 (_write_token_to_config)
dir_ = os.path.dirname(os.path.abspath(config_path))
fd, tmp = tempfile.mkstemp(dir=dir_, prefix=".quirk_sensor_")
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
```

The sensor.yaml write must use exactly this idiom. The parent directory for `tempfile.mkstemp` must be `os.path.dirname(os.path.abspath(config_path))` — same dir as the target — so `os.replace` is always same-filesystem (cross-device replace raises `OSError`). [VERIFIED: token_cmd.py:39-50]

### Pattern 4: One-Time Token (secrets + SHA-256)

```python
# Source: quirk/cli/token_cmd.py:99-100
import secrets, hashlib
raw_token = secrets.token_urlsafe(32)
token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
# Store token_hash in sensor_tokens table (Phase 109 consumes it)
# Print raw_token once; do NOT write it to sensor.yaml
```

[VERIFIED: token_cmd.py:99-100; models.py:311 confirms `token_hash = Column(String(64))`]

### Pattern 5: zstd Compress + HMAC Sign

```python
# Source: architecture-distributed.md §3.3 + zstandard PyPI docs
import zstandard
import hmac as _hmac
import hashlib

compressor = zstandard.ZstdCompressor(level=3)
body_bytes = compressor.compress(json.dumps(envelope).encode("utf-8"))

# HMAC over compressed body; key derived from enrollment token
# (key material stored in sensor.yaml or env — Claude's discretion on exact key derivation)
sig = _hmac.new(key_bytes, body_bytes, hashlib.sha256).hexdigest()
# Header: X-Sensor-Signature: hmac-sha256=<sig>
```

The `zstandard.ZstdCompressor(level=3).compress()` API is the single-call form for in-memory compression. Use `zstandard.ZstdDecompressor().decompress()` for reading spooled files. [VERIFIED: PyPI; architecture-distributed.md §3.3]

### Pattern 6: tenacity Retry

```python
# Source: tenacity PyPI docs; CONTEXT.md retry policy
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception(lambda e: _is_retryable(e)),
    reraise=True,
)
def _do_push(client, url, headers, content):
    resp = client.post(url, headers=headers, content=content)
    if resp.status_code >= 500:
        resp.raise_for_status()  # triggers retry
    return resp

def _is_retryable(exc):
    import httpx
    return isinstance(exc, (httpx.ConnectError, httpx.TimeoutException))
```

Key invariant: 4xx responses (401, 409, 413) must NOT be retried — they are permanent errors. Only `ConnectError`, `TimeoutException`, and 5xx responses should retry. [VERIFIED: CONTEXT.md retry policy]

### Pattern 7: `_NoRedirectHandler` Extraction (STAB-02)

```python
# Source: quirk/notify/channels/webhook.py:29-41 (identical in servicenow.py:34-47)
# Target: quirk/util/no_redirect.py

import urllib.error
import urllib.request

class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Block all HTTP redirects to prevent post-validation SSRF bypass."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url, code, "Redirect blocked (SSRF guard)", headers, fp
        )
```

Both source files have **identical** implementations. The extraction is a pure copy-to-new-file + update-two-imports refactor. No logic changes. [VERIFIED: webhook.py:29-41; servicenow.py:34-47]

After extraction, both callers change `class _NoRedirectHandler(...)` definitions to `from quirk.util.no_redirect import _NoRedirectHandler`. The push client also imports from `quirk/util/no_redirect.py` (push uses httpx, not urllib, but the extraction is still the STAB-02 prerequisite as locked — the push client is the named consumer).

**Note on push client:** The push client uses `httpx` (not `urllib`). `httpx.Client` does not use `urllib.request.HTTPRedirectHandler`. The push client should set `follow_redirects=False` on the httpx client directly, and separately import `_NoRedirectHandler` only if urllib is used elsewhere (or treat the import as a policy-document import to satisfy STAB-02). The simplest implementation: push client uses `httpx.Client(verify=True, follow_redirects=False)` and imports `_NoRedirectHandler` from `quirk/util/no_redirect.py` for future urllib-based fallbacks.

### Pattern 8: Local Scan Invocation

```python
# Source: scheduler_cmd.py:140-161 (exact subprocess pattern)
# Push command must reuse this pattern, not call main() directly
import sys, subprocess

cmd = [
    sys.executable,
    "-m",
    "run_scan",
    "--config", config_path,
    "--target", target,
    "--output", str(output_dir),
]
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = proc.communicate()
```

`quirk sensor push` runs a local scan via subprocess (`sys.executable -m run_scan`), then reads the resulting SQLite DB to extract `CryptoEndpoint` rows, serializes them into the wire payload, and pushes. The scan must write to a known `--output` directory so the push command can locate the DB. [VERIFIED: scheduler_cmd.py:140-161]

### Pattern 9: Existing verify=False Grep Gate (mirror for push client)

```python
# Source: tests/scanner/test_phase57_invariants.py:46-54
# Mirror this for the push client module

import io, pathlib, tokenize

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
TARGET = REPO_ROOT / "quirk" / "cli" / "sensor_cmd.py"

def _strip_comments(src):
    chars = list(src)
    for tok_type, tok_string, tok_start, tok_end, _ in tokenize.generate_tokens(
        io.StringIO(src).readline
    ):
        if tok_type == tokenize.COMMENT:
            # blank out comment range
            ...
    return "".join(chars)

def test_sensor_push_no_verify_false():
    src = _strip_comments(TARGET.read_text())
    assert "verify=False" not in src, "sensor_cmd.py must never use verify=False"
```

The project already has a mature `_strip_comments` + `assert "verify=False" not in src` pattern in `tests/scanner/test_phase57_invariants.py`. The new test for `sensor_cmd.py` (and `console_cmd.py`) should copy that exact tokenize-based approach. [VERIFIED: tests/scanner/test_phase57_invariants.py:21-54]

### Anti-Patterns to Avoid

- **Direct `main()` call for local scan:** Do not call `run_scan.main()` in-process from `sensor push`. Use `subprocess` like `scheduler_cmd.py` does. This avoids argparse namespace pollution, stdout/stderr bleed, and `sys.exit()` calls inside `main()` that would terminate the push process.
- **`verify=False` anywhere in push path:** Not just the httpx call — also ensure `ssl_verify` or any equivalent kwarg is never `False`. The CI grep gate will catch it, but do not introduce it.
- **Storing the raw enrollment token:** `sensor.yaml` must NOT contain the raw token. It is printed once and consumed at enrollment. sensor.yaml only carries `console_url`, `sensor_id`, `segment`, `engagement`, `sensor_version`.
- **Non-atomic sensor.yaml write:** A plain `open(path, "w")` can leave a partial file on crash. Always use `tempfile.mkstemp` + `os.replace`.
- **Unbounded spool:** The spool dir MUST enforce both a max-file-count and a max-total-bytes cap. Never let it grow without bound.
- **Retrying 4xx:** A 401 or 413 is a permanent error. Retrying it wastes time and could trigger rate-limiting on the console.
- **Backslash paths in serialized payload:** All `host` and path strings in the JSON envelope must be forward-slash normalized before serialization. Windows `Path` objects serialize with backslashes — always use `pathlib.PurePosixPath` or `str(path).replace("\\", "/")` before putting any path into the wire payload.
- **`signal.SIGTERM` without platform guard:** `signal.SIGTERM` is not available on Windows in the same way as POSIX. The existing `scheduler_cmd.py:259` line must be guarded: `if sys.platform != "win32": signal.signal(signal.SIGTERM, _handle_signal)`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-OS config dirs | Custom `~/.quirk/` path logic | `platformdirs.user_config_dir("quirk")` | Handles Windows `%APPDATA%`, macOS `~/Library/Preferences`, Linux `~/.config` correctly |
| Cross-OS data dirs | Custom `~/.quirk/data/` | `platformdirs.user_data_dir("quirk")` | Same cross-OS logic for spool dir |
| Retry with backoff | Manual sleep loop | `tenacity.retry` with `wait_exponential` | Handles jitter, cap, exception type filtering, reraise |
| Compression | Custom gzip wrapper | `zstandard.ZstdCompressor(level=3)` | Architecture doc locks zstd; faster than gzip; single-call compress API |
| SSRF redirect block | Custom redirect detection | `_NoRedirectHandler` from `quirk/util/no_redirect.py` | Already exists; blocking all 3xx redirects is the correct SSRF mitigation |
| `verify=False` audit | Manual code review | Pytest grep gate (tokenize-based, from test_phase57_invariants.py pattern) | Survives future edits; automated |

---

## POSIX-ism Audit Results

Two concrete targets confirmed in `quirk/cli/scheduler_cmd.py` [VERIFIED: grep of file]:

### Target 1: Relative Path (L136)

**Current (L135-137):**
```python
output_dir = (
    Path("output/scheduled") / safe_name / now.strftime("%Y%m%d-%H%M%S")
)
```

**Problem:** `Path("output/scheduled")` is relative to CWD. On Windows, if the process is not started from the repo root, output goes to an unexpected location. Also, this is a hardcoded path, not honoring `cfg.output.directory`.

**Fix:** Anchor to `cfg.output.directory`:
```python
output_dir = (
    Path(cfg.output.directory) / "scheduled" / safe_name / now.strftime("%Y%m%d-%H%M%S")
)
```

Note: `cfg` is available in `_dispatch_schedule_run()` via the `db_path` parameter which comes from `_resolve_db_path(args.config)`. The config object is accessible via `load_config(args.config)` — check the function signature to confirm `cfg` is in scope. If not, pass it as a parameter.

### Target 2: Unconditional SIGTERM (L258-259)

**Current (L258-259):**
```python
signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)
```

**Problem:** `signal.SIGTERM` raises `AttributeError` on Windows (`signal.SIGTERM` exists but `signal.signal(signal.SIGTERM, ...)` may raise `OSError` or behave differently). Windows only guarantees SIGINT and SIGBREAK.

**Fix:**
```python
signal.signal(signal.SIGINT, _handle_signal)
if sys.platform != "win32":
    signal.signal(signal.SIGTERM, _handle_signal)
```

### Other POSIX-isms to Review

The following were checked and are either acceptable or not in sensor-relevant code paths [VERIFIED: grep]:

- `os.sep` usage in `quirk/util/targets.py:152` and `quirk/cli/init_cmd.py:36` — these use `os.sep` correctly for path component splitting, which is cross-platform. No change needed.
- `os.path.join` usage is universal — works on Windows. No change needed.
- `os.replace` in `token_cmd.py:44` — works on Windows (atomic on POSIX; best-effort on Windows per existing comment). Same idiom for sensor.yaml is acceptable.
- No hardcoded `/var`, `/tmp`, or `~/.config` paths found in sensor-relevant code.

---

## Wire Contract Serialization

The wire envelope fields (from `docs/architecture-distributed.md §3.1`) [VERIFIED: architecture-distributed.md]:

```python
envelope = {
    "payload_id": str(uuid.uuid4()),        # unique per push
    "pushed_at": datetime.utcnow().isoformat() + "Z",
    "schema_version": "1.0.0",
    "sensor_version": quirk.__version__,
    "sensor_id": sensor_cfg["sensor_id"],
    "segment": sensor_cfg["segment"],
    "findings": [_endpoint_to_dict(ep) for ep in endpoints],
}
```

Key serialization invariants for Windows CI:
- All `host` values from `CryptoEndpoint.host` are already hostname/IP strings — no path separators. No normalization needed.
- All datetime strings must use `isoformat() + "Z"` or `strftime("%Y-%m-%dT%H:%M:%SZ")` — no OS-specific time formatting.
- JSON `json.dumps(envelope)` produces forward-slash-free output since there are no filesystem paths in the envelope fields.
- The `findings` list serializes `CryptoEndpoint` ORM objects — define a `_endpoint_to_dict()` helper that reads column values explicitly (not `.__dict__` which includes SQLAlchemy internal keys).

**`received_at` is NOT sent by the sensor.** The console stamps it on ingest (Phase 109). Do not include it in the push payload. [VERIFIED: architecture-distributed.md §3.1]

---

## GitHub Actions Windows CI Job

### Existing Workflow Patterns [VERIFIED: .github/workflows/]

Current workflows:
- `python-staleness.yml` — runs on `ubuntu-latest`, installs with `pip install -e . && pip install pytest`, runs specific test files
- `dashboard-quality.yml` — runs on `ubuntu-latest`, Node.js + npm

No existing `windows-latest` job exists. The new job must be added to an appropriate workflow file — either a new `python-ci.yml` or added as a job to the existing `python-staleness.yml`.

### Hard-Gate Windows Smoke Job Structure

```yaml
jobs:
  windows-sensor-smoke:
    name: Windows Sensor Smoke
    runs-on: windows-latest
    # NOTE: NO continue-on-error — this is a hard gate (SENSOR-06)
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install project with sensor deps
        run: pip install -e ".[sensor]"
        # OR: pip install -e . platformdirs tenacity zstandard
        # if sensor extras group is not created

      - name: Run Windows sensor smoke tests
        run: pytest tests/test_sensor_windows_smoke.py -v

      - name: Assert no backslash paths in serialized payload
        # Inline grep or pytest test that builds an envelope and asserts
        # json.dumps(envelope) contains no backslash characters in field values
        run: python -c "from quirk.cli.sensor_cmd import _build_envelope; import json; e = _build_envelope(...); assert '\\\\' not in json.dumps(e)"
```

**Key SENSOR-06 requirements:**
1. `runs-on: windows-latest` — mandatory
2. No `continue-on-error: true` — mandatory (hard gate)
3. Must validate no backslash paths in serialized payload
4. Must validate clean process shutdown (SIGINT handling on Windows)

The CI grep gate for `verify=False` can be a pytest test (`test_sensor_no_verify_false.py`) that runs on both Linux and Windows, rather than a shell grep command (shell grep differs between platforms). [ASSUMED — specific CI file placement is Claude's discretion per CONTEXT.md]

---

## Common Pitfalls

### Pitfall 1: `zstandard` Not Declared in `pyproject.toml`
**What goes wrong:** `architecture-distributed.md` says zstandard is "already in the codebase" — it is NOT. Package is absent from `pyproject.toml` and all `quirk/` Python files.
**Why it happens:** The architecture doc was written before implementation; the claim was aspirational.
**How to avoid:** Add `zstandard>=0.22.0` to `[project] dependencies` in the same task that adds `platformdirs` and `tenacity`. CI on a clean venv would catch this anyway.
**Warning signs:** `ModuleNotFoundError: No module named 'zstandard'` on clean install.

### Pitfall 2: `sensor.yaml` Directory May Not Exist
**What goes wrong:** `platformdirs.user_config_dir("quirk")` returns a path that may not exist yet on a fresh system. `tempfile.mkstemp(dir=...)` will raise `FileNotFoundError` if the dir doesn't exist.
**Why it happens:** `platformdirs` returns the path; it does not create it.
**How to avoid:** `os.makedirs(config_dir, exist_ok=True)` before calling `tempfile.mkstemp`.
**Warning signs:** `FileNotFoundError: [Errno 2] No such file or directory: '...quirk...'` on first `enroll`.

### Pitfall 3: `tempfile.mkstemp` + `os.replace` Cross-Filesystem
**What goes wrong:** If `tmpdir` from `tempfile.mkstemp()` is on a different filesystem than the target (e.g., `/tmp` vs `~/.config`), `os.replace` raises `OSError: [Errno 18] Invalid cross-device link`.
**Why it happens:** `os.replace` is not cross-device on Linux (POSIX rename(2) is same-FS only).
**How to avoid:** Always pass `dir=os.path.dirname(os.path.abspath(target_path))` to `tempfile.mkstemp`. This is exactly what `token_cmd.py` does. Do not use the system's default temp dir.
**Warning signs:** `OSError: [Errno 18] Invalid cross-device link` on write.

### Pitfall 4: `signal.SIGTERM` on Windows
**What goes wrong:** `signal.signal(signal.SIGTERM, handler)` is already at `scheduler_cmd.py:259`. If this is not guarded, importing `scheduler_cmd` or running the scheduler on Windows may fail.
**Why it happens:** Windows supports `SIGTERM` in the `signal` module namespace but `signal.signal(SIGTERM, ...)` behavior differs from POSIX.
**How to avoid:** Apply the `if sys.platform != "win32":` guard at L259. This is a 3-line change.
**Warning signs:** `OSError` or unexpected behavior in the Windows CI job.

### Pitfall 5: Backslash Paths from Windows `Path.__str__()`
**What goes wrong:** `str(pathlib.Path("C:/Users/digs/.config/quirk"))` on Windows returns `C:\Users\digs\.config\quirk`. If any path is embedded in the JSON payload, it will contain backslashes.
**Why it happens:** `pathlib.Path.__str__()` uses the OS separator.
**How to avoid:** Never embed filesystem paths in the wire payload (the spec does not include any paths). If any path is needed in future, use `path.as_posix()`. The Windows CI smoke test should assert `"\\" not in json.dumps(envelope)`.
**Warning signs:** CI smoke test failure "backslash found in serialized payload".

### Pitfall 6: `_dispatch_schedule_run` — `cfg` Scope
**What goes wrong:** The POSIX-ism fix at L136 requires replacing `Path("output/scheduled")` with `Path(cfg.output.directory) / "scheduled"`. But `cfg` (a `QuirkConfig` object) may not be in scope in `_dispatch_schedule_run()`.
**Why it happens:** The function currently takes `(schedule, db, db_path)` — not `cfg`.
**How to avoid:** Check the function signature; if `cfg` is not available, either pass it as a parameter or load it from `db_path` inside the function. The fix must not break existing schedule dispatch behavior.
**Warning signs:** `NameError: name 'cfg' is not defined` after applying the fix.

### Pitfall 7: Spool Dir Race Condition
**What goes wrong:** Two concurrent `quirk sensor push` invocations could both try to spool at the same time, potentially racing on the max-count check.
**Why it happens:** File system operations are not atomic.
**How to avoid:** v5.4 is single-tenant, single-sensor-process — document that concurrent push is not supported. A file lock or atomic counter is not required for v5.4.
**Warning signs:** Spool dir exceeding max count by a small margin. Not a correctness issue for single-process use.

---

## Code Examples

### Enrollment Token Lifecycle

```python
# Source: quirk/cli/token_cmd.py:99-100 + quirk/models.py:291-313
import secrets, hashlib, uuid

sensor_id = str(uuid.uuid4())
raw_token = secrets.token_urlsafe(32)
token_hash = hashlib.sha256(raw_token.encode()).hexdigest()  # 64-char hex

# Store in sensor_tokens table (console-side, Phase 109):
# SensorToken(sensor_id=sensor_id, token_hash=token_hash, created_at=utcnow())

# Write to sensor.yaml (sensor-side):
sensor_cfg = {
    "console_url": console_url,
    "sensor_id": sensor_id,
    "segment": segment,
    "engagement": engagement,   # may be None
    "sensor_version": quirk.__version__,
}
# Use _write_sensor_config(config_path, sensor_cfg) — mirrors _write_token_to_config

# Print once (never store):
print(f"Enrollment token (shown once — save it now): {raw_token}")
```

### zstd Compress + HMAC Sign + httpx Push

```python
# Source: architecture-distributed.md §3.3; zstandard PyPI; webhook.py:81-86
import json, hmac as _hmac, hashlib, zstandard

def _build_compressed_payload(envelope: dict) -> bytes:
    raw = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    return zstandard.ZstdCompressor(level=3).compress(raw)

def _sign(body: bytes, key: bytes) -> str:
    return "hmac-sha256=" + _hmac.new(key, body, hashlib.sha256).hexdigest()

# httpx push (verify=True hardcoded):
import httpx
with httpx.Client(verify=True, follow_redirects=False) as client:
    resp = client.post(
        console_url.rstrip("/") + "/api/sensor/push",
        content=body,
        headers={
            "Content-Type": "application/octet-stream",
            "X-Sensor-Signature": _sign(body, key_bytes),
            "Authorization": f"Bearer {bearer_token}",
        },
    )
```

### platformdirs Usage

```python
# Source: platformdirs PyPI docs (verified 4.4.0)
from platformdirs import user_config_dir, user_data_dir
import os

config_dir = user_config_dir("quirk")   # ~/.config/quirk on Linux, %APPDATA%\quirk on Windows
data_dir = user_data_dir("quirk")       # ~/.local/share/quirk on Linux
spool_dir = os.path.join(data_dir, "spool")

os.makedirs(config_dir, exist_ok=True)
os.makedirs(spool_dir, exist_ok=True)

sensor_yaml_path = os.path.join(config_dir, "sensor.yaml")
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|-----------------|-------|
| Hardcoded `~/.config/quirk` | `platformdirs.user_config_dir("quirk")` | Handles Windows `%APPDATA%` correctly |
| `signal.SIGTERM` unconditional | `if sys.platform != "win32": signal.signal(signal.SIGTERM, ...)` | Windows-safe |
| Duplicate `_NoRedirectHandler` in 2 files | Single `quirk/util/no_redirect.py` | STAB-02 prerequisite |

**Deprecated/outdated:**
- `Path("output/scheduled")` relative path in `scheduler_cmd.py:136` — replace with `cfg.output.directory`-anchored absolute path.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All | Dev env: 3.11 confirmed | 3.11 | — |
| `platformdirs` | SENSOR-01, SENSOR-03, SENSOR-05 | Not in pyproject.toml | — | None — must add |
| `tenacity` | SENSOR-02 | Installed in dev env (9.1.2) but NOT in pyproject.toml | 9.1.2 | None — must declare |
| `zstandard` | SENSOR-02, SENSOR-03, SENSOR-04 | Not in pyproject.toml | — | None — must add |
| `httpx` | SENSOR-02 | In pyproject.toml (>=0.28.0) | Current | — |
| `windows-latest` GitHub runner | SENSOR-06 | Available on GitHub Actions | — | None — required |

**Missing dependencies with no fallback:**
- `platformdirs`, `tenacity` (declared), `zstandard` — all three must be added to `pyproject.toml [project] dependencies` before any sensor code can run.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (confirmed in pyproject.toml) |
| Config file | `pyproject.toml [tool.pytest.ini_options]` — `testpaths = ["tests"]`, `addopts = "-m 'not slow'"` |
| Quick run command | `pytest tests/test_sensor_cmd.py -x -q` |
| Full suite command | `pytest tests/ -x -q -m "not slow and not live_infra"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SENSOR-01 | `enroll` writes sensor.yaml atomically with correct fields | unit | `pytest tests/test_sensor_cmd.py::test_enroll_writes_sensor_yaml -x` | ❌ Wave 0 |
| SENSOR-01 | `enroll` prints token to stdout, never writes it | unit | `pytest tests/test_sensor_cmd.py::test_enroll_token_not_in_yaml -x` | ❌ Wave 0 |
| SENSOR-02 | `push` invokes local scan subprocess and posts result | unit (mock httpx) | `pytest tests/test_sensor_cmd.py::test_push_posts_compressed_payload -x` | ❌ Wave 0 |
| SENSOR-02 | `verify=False` never appears in sensor_cmd.py | static AST/grep | `pytest tests/test_sensor_no_verify_false.py -x` | ❌ Wave 0 |
| SENSOR-02 | tenacity retries on 5xx but not 4xx | unit | `pytest tests/test_sensor_cmd.py::test_push_retry_policy -x` | ❌ Wave 0 |
| SENSOR-03 | Offline push spools to platformdirs data dir | unit (mock httpx) | `pytest tests/test_sensor_cmd.py::test_push_spools_on_connect_error -x` | ❌ Wave 0 |
| SENSOR-03 | Spool dir respects max-file-count eviction | unit | `pytest tests/test_sensor_cmd.py::test_spool_eviction_policy -x` | ❌ Wave 0 |
| SENSOR-04 | `export-results` writes byte-identical envelope to `.qpush` | unit | `pytest tests/test_sensor_cmd.py::test_export_results_identical_envelope -x` | ❌ Wave 0 |
| SENSOR-04 | `console import-results` reads `.qpush` and calls same ingest path | unit (mock) | `pytest tests/test_console_cmd.py::test_import_results_calls_ingest -x` | ❌ Wave 0 |
| SENSOR-05 | `scheduler_cmd.py:136` uses `cfg.output.directory`-anchored path | unit | `pytest tests/test_scheduler_posix_fixes.py::test_output_dir_anchored -x` | ❌ Wave 0 |
| SENSOR-05 | `signal.SIGTERM` registration is platform-conditional | unit | `pytest tests/test_scheduler_posix_fixes.py::test_sigterm_guard -x` | ❌ Wave 0 |
| SENSOR-06 | Windows: serialized payload has no backslash paths | unit (runs on windows-latest) | `pytest tests/test_sensor_windows_smoke.py -x` | ❌ Wave 0 |
| SENSOR-06 | Windows: clean shutdown (KeyboardInterrupt / SIGINT) | unit | `pytest tests/test_sensor_windows_smoke.py::test_clean_shutdown -x` | ❌ Wave 0 |
| STAB-02 | `_NoRedirectHandler` importable from `quirk.util.no_redirect` | unit | `pytest tests/test_no_redirect_extraction.py -x` | ❌ Wave 0 |
| STAB-02 | `webhook.py` and `servicenow.py` no longer define `_NoRedirectHandler` | static | `pytest tests/test_no_redirect_extraction.py::test_no_duplicate_definitions -x` | ❌ Wave 0 |

Existing test: `tests/test_sensor_schema.py` — covers MODEL-01..04 (Phase 107, already passing). Phase 108 must not break it.

### Wave 0 Gaps

- [ ] `tests/test_sensor_cmd.py` — covers SENSOR-01, SENSOR-02, SENSOR-03, SENSOR-04
- [ ] `tests/test_console_cmd.py` — covers SENSOR-04 (import-results)
- [ ] `tests/test_sensor_no_verify_false.py` — covers SENSOR-02 verify gate
- [ ] `tests/test_sensor_windows_smoke.py` — covers SENSOR-06 (runs on windows-latest)
- [ ] `tests/test_scheduler_posix_fixes.py` — covers SENSOR-05 scheduler fixes
- [ ] `tests/test_no_redirect_extraction.py` — covers STAB-02

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | One-time token SHA-256 hash stored; raw token never persisted; `secrets.token_urlsafe(32)` |
| V3 Session Management | no | No session; token consumed at enrollment |
| V4 Access Control | yes | Push client sends Bearer token in Authorization header; console enforces `require_auth` (Phase 109) |
| V5 Input Validation | yes | `validate_external_url()` called on console URL before any push; `_NoRedirectHandler` blocks redirect bypass |
| V6 Cryptography | yes | HMAC-SHA256 via stdlib `hmac.new`; never hand-rolled; `hmac.compare_digest` for timing-safe comparison on console side |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSRF via console_url redirect | Spoofing | `_NoRedirectHandler` from `quirk/util/no_redirect.py`; `validate_external_url()` pre-connection check |
| `verify=False` TLS downgrade | Tampering | Hardcoded `verify=True`; CI grep gate (tokenize-based) |
| Replay attack (duplicate payload) | Repudiation | `payload_id` dedup → 409 in `sensor_pushes` table; ±15-min window for HTTPS push |
| Token leaked to sensor.yaml | Info Disclosure | Raw token never written to file; only `token_hash` stored in DB |
| Spool unbounded disk fill | DoS | Max-file-count + max-total-bytes cap with oldest-evicted policy |
| Path traversal in spool filenames | Tampering | Spool filenames are `{uuid4}.json.zst` — UUID format enforced, no user-controlled path components |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The push client uses `httpx.Client(follow_redirects=False)` instead of `_NoRedirectHandler` (since httpx is not urllib-based) | Don't Hand-Roll / Pattern 7 | Minor — if httpx follows redirects by default when `follow_redirects` is not set, a redirect-based SSRF could occur. Mitigation: always set `follow_redirects=False`. |
| A2 | The new Windows CI job should be added to a new `python-ci.yml` or to `python-staleness.yml` rather than creating a separate file | Environment Availability / CI | Minor — if the staleness workflow grows too large, a separate file is cleaner. Claude's discretion per CONTEXT.md. |
| A3 | `cfg.output.directory` is the correct attribute path for the scheduler's output directory anchor | POSIX-ism Audit / Pitfall 6 | Low — if the attribute name differs (e.g., `cfg.output.directory` vs `cfg.output_dir`), the fix will raise `AttributeError`. Must verify attribute name in `quirk/config.py:OutputCfg`. |

**Note on A3:** `quirk/config.py:292-294` shows `class OutputCfg` with `directory: str` and `db_path: str`. Usage in `run_scan.py` confirms `cfg.output.directory`. The attribute is `cfg.output.directory`. [VERIFIED: quirk/config.py:292-294; run_scan.py:1021]

---

## Open Questions

1. **HMAC key material storage in sensor.yaml**
   - What we know: The push client needs a per-sensor key to compute `X-Sensor-Signature: hmac-sha256=...`. Architecture doc §6 says "per-sensor key derived from the enrollment token."
   - What's unclear: The raw token is consumed at enrollment and not stored. The key must either be derived from a stored value or stored separately. Options: (a) store a derived key in `sensor.yaml`, (b) require the operator to re-enter the token on each push (bad UX), (c) derive from `sensor_id + shared-secret` (but what shared secret?).
   - Recommendation: Store a `hmac_key` (32-byte `secrets.token_bytes(32)` as hex) in `sensor.yaml` at enrollment time, derived separately from the one-time token. This is safe because `sensor.yaml` is operator-controlled (same sensitivity as `config.yaml`). The console must receive and store the corresponding key material at enrollment to verify signatures. This is a Phase 108 decision; Phase 109 consumes it.

2. **Bearer token for push Authorization header**
   - What we know: The console ingest endpoint requires `require_auth` (Bearer token from `config.yaml`'s `security.api_token`). The push client needs a bearer token.
   - What's unclear: Does the push client re-use the console's API token (from `sensor.yaml`?), or does enrollment generate a separate per-sensor bearer token?
   - Recommendation: Store the console API token in `sensor.yaml` at enrollment time (operator provides it). The sensor push client sends it as `Authorization: Bearer <console_api_token>`. This is the simplest approach and consistent with the existing `require_auth` mechanism.

---

## Sources

### Primary (HIGH confidence)
- `run_scan.py:363-515` — CLI dispatch pattern (verified by reading file)
- `quirk/cli/token_cmd.py` — atomic YAML write + `secrets.token_urlsafe` + SHA-256 token pattern
- `quirk/notify/channels/webhook.py:29-41` — `_NoRedirectHandler` definition
- `quirk/ticketing/servicenow.py:34-47` — identical `_NoRedirectHandler` duplication
- `quirk/util/url_allowlist.py` — `validate_external_url` API
- `quirk/cli/scheduler_cmd.py:135-138, 257-259` — POSIX-ism targets
- `quirk/models.py:269-335` — `Sensor`, `SensorToken`, `SensorPush` ORM models
- `tests/scanner/test_phase57_invariants.py` — verify=False grep gate pattern
- `tests/conftest.py` — `QUIRK_DB_PATH` isolation fixture pattern
- `pyproject.toml` — confirmed absence of `platformdirs`, `tenacity`, `zstandard`
- `docs/architecture-distributed.md` — wire contract (§3), enrollment (§6), Windows scope (§10)
- PyPI registry: `pip index versions zstandard` (0.25.0), `platformdirs` (4.4.0), `tenacity` (9.1.2)

### Secondary (MEDIUM confidence)
- `zstandard` PyPI documentation — `ZstdCompressor(level=3).compress()` and `ZstdDecompressor().decompress()` API
- `platformdirs` PyPI documentation — `user_config_dir("quirk")` and `user_data_dir("quirk")`
- `tenacity` PyPI documentation — `retry`, `stop_after_attempt`, `wait_exponential`, `retry_if_exception`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified on PyPI, presence/absence in pyproject.toml confirmed by grep
- Architecture patterns: HIGH — derived from actual codebase code reading
- POSIX-ism targets: HIGH — exact line numbers confirmed by grep
- Wire contract: HIGH — architecture-distributed.md is the locked canonical contract
- Pitfalls: HIGH — cross-device rename and signal.SIGTERM are well-known Python cross-platform issues; confirmed by code inspection

**Research date:** 2026-05-25
**Valid until:** 2026-06-25 (stable codebase; 30-day estimate)
