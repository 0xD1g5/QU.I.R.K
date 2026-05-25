# Phase 103: SIEM Export — Research

**Researched:** 2026-05-24
**Domain:** CEF/syslog export, stdlib socket transport, CLI subcommand wiring, Phase 101 audit table reuse
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **CEF format:** ArcSight CEF:0 — `CEF:0|QUIRK|scanner|<version>|<signature>|<name>|<severity>|<extension>`
- **Severity mapping:** CRITICAL→10, HIGH→8, MEDIUM→5, LOW→3
- **signature** = finding category/id; **name** = human-readable title
- **Extension keys:** `dhost`=host, `dpt`=port, `cs1`=category, `cs2`=evidence summary, `msg`=detail
- **Transport:** stdlib `socket`, UDP and TCP, config-selectable; zero new pip deps
- **Splunk HEC:** DEFERRED — syslog/CEF only this phase
- **Config:** `[siem]` YAML block (host, port, protocol udp/tcp) via `QUIRK_CONFIG_PATH`
- **Endpoint validation:** validate host/port format; do NOT block internal/loopback targets (syslog collectors are commonly internal); reject only malformed targets
- **CLI:** `quirk export --siem`; reads latest `findings-*.json` in output dir, or `--input <path>`
- **Granularity:** one CEF event per finding
- **After-scan:** `export_after_scan: true` flag in `[siem]` block triggers push after scheduled scan
- **Failure handling:** unreachable endpoint → clear error + WARNING + `integration_deliveries` row; NEVER aborts scan
- **Payload whitelist:** host, port, protocol, severity, category, evidence-summary ALLOWED; cert PEM, SANs, private-key material EXCLUDED
- **Evidence field:** truncated/sanitized summary, never raw PEM blocks
- **CEF escaping:** header escapes `\` and `|`; extension escapes `\`, `=`, and newlines

### Claude's Discretion

No Claude's-discretion areas recorded in CONTEXT.md.

### Deferred Ideas (OUT OF SCOPE)

- Splunk HEC native endpoint
- Elastic native endpoint
- TLS-wrapped syslog (RFC 5425) — plain UDP/TCP only
- Per-finding dedup/idempotency (ticketing concern in 104/105; SIEM is fire-and-forget)

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SIEM-01 | User can export findings to a SIEM in syslog/CEF format (vendor-neutral), landing in any syslog-ingesting platform | stdlib `socket` + `logging.handlers.SysLogHandler` pattern; CEF format verified from official ArcSight spec; no new deps confirmed |
| SIEM-02 | SIEM export is a findings-push with correct CEF field mapping (severity, host, signature/category, evidence), invokable from CLI and optionally after a scan | findings JSON shape confirmed from actual output files; CEF key mapping verified; after-scan hook pattern mirrors Phase 101 notification dispatch |

</phase_requirements>

---

## Summary

Phase 103 ships a standalone SIEM export capability that reads `findings-*.json` output from a completed scan and pushes one CEF-formatted syslog message per finding to a configured receiver. The implementation reuses three Phase 101 primitives — the `IntegrationDelivery` audit table, `safe_str` scrubbing, and the QUIRK_CONFIG_PATH config-load discipline — while adding a new `quirk/siem/` module tree: a config loader (`SiemCfg`), a CEF formatter, a socket transport, and an export dispatcher.

The SIEM delivery path is intentionally simpler than the notification dispatcher: no trend computation, no trigger evaluation, no channel fan-out. It reads raw findings dicts, applies the per-finding CEF whitelist (distinct from the drift-level `to_integration_payload` whitelist), formats each as a CEF event, and sends them sequentially. Failures are isolated per-finding and recorded as `integration_deliveries` rows with `destination="siem"`.

The after-scan hook mirrors the `dispatch_notifications` call in `scheduler_cmd.py::_dispatch_schedule` — a deferred import wrapped in `try/except`, called after the final `db.commit()`, loading config via `QUIRK_CONFIG_PATH` (never the scheduler DB-path argument). The CLI surface follows the established interception-block pattern in `run_scan.py`.

**Primary recommendation:** Model `quirk/siem/` on `quirk/notify/` — config loader, dispatcher, transport as separate files. The run_scan.py interception block for `export` is a two-line addition; the after-scan hook in scheduler_cmd.py is a three-line addition (deferred import, try/except, call).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CEF formatting | Backend / library | — | Pure string transformation; no I/O |
| Syslog transport (UDP/TCP) | Backend / library | — | stdlib socket; called by dispatcher |
| Per-finding payload whitelist | Backend / library | — | ISEC-03 enforcement; same layer as to_integration_payload |
| CLI `quirk export --siem` | CLI entrypoint | Backend / library | Follows run_scan.py interception pattern |
| After-scan hook | Scheduler (CLI) | Backend / library | Mirror of Phase 101 notify hook in scheduler_cmd.py |
| SiemCfg config loader | Backend / library | — | Mirror of quirk/notify/config.py::load_notifications_config |
| IntegrationDelivery audit rows | Database | Backend | Shared Phase 101 table; destination="siem" |

---

## Standard Stack

### Core (all stdlib — zero new pip deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `socket` | stdlib | Raw UDP/TCP send for syslog | Confirmed: `logging.handlers.SysLogHandler` uses `socket` internally; direct socket use gives full control over framing |
| `logging.handlers.SysLogHandler` | stdlib | Optional higher-level wrapper with priority encoding | Can be used as the send mechanism OR as reference for `encodePriority`; `SysLogHandler(address=(host, port), socktype=socket.SOCK_DGRAM|SOCK_STREAM)` |
| `json` | stdlib | Load findings-*.json | Already used throughout |
| `glob` / `pathlib` | stdlib | Locate latest findings file | Pattern: `max(Path(outdir).glob("findings-*.json"), key=os.path.getmtime)` |
| `yaml` | project dep (pyyaml) | Parse [siem] config block | Already imported in quirk/notify/config.py |
| `dataclasses` | stdlib | SiemCfg dataclass | Matches NotifyCfg pattern exactly |

**Installation:** No new packages required. All transport and formatting via stdlib.

---

## Package Legitimacy Audit

No new packages are introduced in this phase. All implementation uses stdlib (`socket`, `logging.handlers`, `json`, `pathlib`, `glob`, `dataclasses`) and the project's existing `pyyaml` dependency. Audit is not applicable.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
findings-{stamp}.json
        |
        v
[export_cmd.py / after-scan hook]
        |
        v
[quirk/siem/config.py]  <-- QUIRK_CONFIG_PATH env var --> [config.yaml [siem] block]
        |
        v
[SiemCfg dataclass]
        |
        v
[quirk/siem/dispatcher.py]
   for each finding:
        |
        +--> [quirk/siem/formatter.py]  -->  CEF string (with escaping)
        |
        +--> [quirk/siem/transport.py]  -->  socket.sendto (UDP) / socket.sendall (TCP)
        |
        +--> [IntegrationDelivery row]  --> quirk.db (destination="siem")
```

### Recommended Project Structure

```
quirk/siem/
├── __init__.py          # empty or re-exports
├── config.py            # SiemCfg dataclass + load_siem_config()
├── formatter.py         # build_cef_event(finding, version) -> str
├── transport.py         # send_syslog(msg, cfg) -> None
└── dispatcher.py        # export_findings(findings, cfg, db, scan_id) -> int

quirk/cli/
└── export_cmd.py        # run_export(argv) -> None  (CLI entrypoint)

tests/
├── test_siem_formatter.py         # CEF format + escaping correctness
├── test_siem_transport.py         # socket send (socketserver capture in-test)
├── test_siem_config.py            # SiemCfg loader, QUIRK_CONFIG_PATH trap
├── test_siem_dispatcher.py        # per-finding dispatch, audit rows, failure isolation
├── test_siem_payload_whitelist.py # cert PEM/SAN exclusion
└── test_export_cmd_wiring.py      # run_scan.py interception + CLI arg parsing
```

### Pattern 1: CEF:0 Header and Extension Format

**What:** ArcSight CEF:0 line with syslog `<PRI>` prefix, fixed 7-pipe header, and space-separated key=value extension.

**RFC 3164 syslog framing:** the `<PRI>` byte sequence `<facility*8 + severity>` prepended to the CEF string. `logging.handlers.SysLogHandler.encodePriority(facility, priority)` encodes this. For SIEM delivery, `facility=LOG_USER` (1) is conventional; the CEF severity field (0-10) is separate from the syslog priority byte.

**Exact CEF:0 structure:**
```
<PRI>CEF:0|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension
```
- Pipe `|` separates exactly 8 fields (including the `CEF:0` version prefix)
- Header fields 1-6 (vendor, product, version, signature, name, severity) are positional
- Severity is an integer 0-10 in field 7
- Extension is field 8 — zero or more `key=value` pairs separated by spaces

**Reference CEF line (no syslog prefix, for clarity):**
```
CEF:0|QUIRK|scanner|1.0.0|tls_cert_expiry|TLS certificate expired|10|dhost=10.0.0.1 dpt=443 cs1=tls_cert_expiry cs1Label=Category cs2=Certificate expired 2026-02-20 cs2Label=EvidenceSummary msg=Certificate notAfter date exceeded. Renew immediately.
```

**With syslog `<PRI>` (facility=LOG_USER=1, mapPriority for WARNING=4 → encoded as 1*8+4=12):**
```
<13>CEF:0|QUIRK|scanner|1.0.0|tls_cert_expiry|TLS certificate expired|10|dhost=...
```

**Source:** [VERIFIED: Micro Focus ArcSight CEF Implementation Standard] — confirmed pipe-delimited header, escaping rules, extension key=value format.

**Example formatter:**
```python
# Source: ArcSight CEF Implementation Standard (cef-implementation-standard.pdf)
# + verified against quirk/notify/config.py NotifyCfg pattern

def _cef_escape_header(value: str) -> str:
    """Escape pipe and backslash in CEF header fields."""
    return value.replace("\\", "\\\\").replace("|", "\\|")

def _cef_escape_extension(value: str) -> str:
    """Escape backslash, equals, and newlines in CEF extension values."""
    return (
        value
        .replace("\\", "\\\\")
        .replace("=", "\\=")
        .replace("\r\n", "\\n")
        .replace("\r", "\\n")
        .replace("\n", "\\n")
    )

# CEF severity mapping (CONTEXT.md D-01)
_CEF_SEVERITY = {"CRITICAL": 10, "HIGH": 8, "MEDIUM": 5, "LOW": 3}

def build_cef_event(finding: dict, version: str) -> str:
    sev_str = str(finding.get("severity", "LOW")).upper()
    cef_sev = _CEF_SEVERITY.get(sev_str, 3)
    signature = _cef_escape_header(str(finding.get("category", "") or finding.get("id", "UNKNOWN")))
    name = _cef_escape_header(str(finding.get("title", "Finding")))
    dhost = _cef_escape_extension(str(finding.get("host", "")))
    dpt = str(finding.get("port", ""))
    cs1 = _cef_escape_extension(str(finding.get("category", "")))
    # evidence summary: truncated description, never PEM
    raw_desc = str(finding.get("description", "") or finding.get("detail", ""))
    cs2 = _cef_escape_extension(raw_desc[:256])  # truncate to avoid large datagrams
    msg_raw = str(finding.get("recommendation", "") or raw_desc)
    msg = _cef_escape_extension(msg_raw[:256])
    header = f"CEF:0|QUIRK|scanner|{_cef_escape_header(version)}|{signature}|{name}|{cef_sev}"
    ext = f"dhost={dhost} dpt={dpt} cs1={cs1} cs1Label=Category cs2={cs2} cs2Label=EvidenceSummary msg={msg}"
    return f"{header}|{ext}"
```

**Order of escape replacements matters:** always escape the backslash FIRST in both header and extension, then the character-specific escapes. Reversing the order double-escapes already-escaped backslashes.

### Pattern 2: stdlib Transport — SysLogHandler vs Raw Socket

**What:** Use `logging.handlers.SysLogHandler` as the transport mechanism; it handles `<PRI>` encoding, UDP vs TCP selection via `socktype`, and connection management.

**Verified from Python 3.11 stdlib source (read above):**
- `SysLogHandler(address=(host, port), socktype=None)` → defaults to `SOCK_DGRAM` (UDP)
- `SysLogHandler(address=(host, port), socktype=socket.SOCK_STREAM)` → TCP
- TCP path calls `sock.connect(sa)` then `sock.sendall(msg)` — framing is raw bytes, no octet-count (RFC 5424 TLS framing not used here)
- UDP path calls `sock.sendto(msg, self.address)` — single datagram per event
- `timeout` kwarg (Python 3.11+) sets `sock.settimeout(timeout)` on TCP sockets
- `emit()` prepends `<PRI>` as `<%d>` bytes, appends NUL (`\000`) when `append_nul=True` (default True)

**Recommended transport pattern:**
```python
# Source: Python 3.11 stdlib logging.handlers (verified from source above)
import logging.handlers
import socket

def send_syslog(cef_msg: str, cfg: SiemCfg, timeout: int = 5) -> None:
    """Send a single CEF event via syslog UDP or TCP.

    cfg.protocol: "udp" -> SOCK_DGRAM, "tcp" -> SOCK_STREAM.
    Raises OSError on connection/send failure — caller wraps in try/except.
    """
    socktype = socket.SOCK_STREAM if cfg.protocol == "tcp" else socket.SOCK_DGRAM
    handler = logging.handlers.SysLogHandler(
        address=(cfg.host, cfg.port),
        facility=logging.handlers.SysLogHandler.LOG_USER,
        socktype=socktype,
    )
    if cfg.protocol == "tcp" and hasattr(handler, 'timeout'):
        handler.timeout = timeout
    # Build a LogRecord so emit() applies PRI encoding
    record = logging.LogRecord(
        name="quirk.siem", level=logging.WARNING,
        pathname="", lineno=0, msg=cef_msg, args=(), exc_info=None,
    )
    handler.emit(record)
    handler.close()
```

**Alternative — raw socket (simpler, avoids LogRecord wrapping):**
```python
import socket

def send_syslog_raw(cef_msg: str, host: str, port: int, protocol: str = "udp",
                    timeout: int = 5) -> None:
    """Send pre-formatted CEF string with RFC 3164 <PRI> prefix via socket."""
    # LOG_USER (1) facility, LOG_WARNING (4) syslog severity
    pri = (1 * 8) + 4  # = 12
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

**Recommendation:** Use the raw socket approach (`send_syslog_raw`) for the initial implementation — it is simpler, testable without LogRecord, and easier to mock in tests than the handler lifecycle. It matches the "zero new deps, stdlib only" norm.

**TCP framing note:** This phase uses raw TCP (no octet-count prefix, no TLS). The receiver must be configured for traditional LF-terminated or raw-bytes syslog input — the `\000` NUL appended by SysLogHandler may confuse some receivers; the raw socket approach avoids it. Document this in the SIEM config comment.

### Pattern 3: SiemCfg — Mirror of NotifyCfg

**What:** A dataclass loaded from the `[siem]` YAML block via `QUIRK_CONFIG_PATH`.

**Modeled on:** `quirk/notify/config.py::load_notifications_config` (lines 159-184 confirmed above).

**Critical discipline (Pitfall 1):** The scheduler's `--config` is a SQLite DB path. `load_siem_config()` MUST resolve the YAML config via `QUIRK_CONFIG_PATH` env var (or explicit path), never from the scheduler DB path argument. The function silently returns `None` on missing/non-YAML files so a misconfigured SIEM never aborts a scan.

```python
# Source: quirk/notify/config.py pattern (confirmed via code read)
@dataclass
class SiemCfg:
    host: str
    port: int = 514
    protocol: str = "udp"          # "udp" or "tcp"
    export_after_scan: bool = False
    timeout_seconds: int = 5

def load_siem_config(path: str | None = None) -> "SiemCfg | None":
    effective_path = path or os.environ.get("QUIRK_CONFIG_PATH")
    if not effective_path or not os.path.isfile(effective_path):
        return None
    try:
        with open(effective_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        siem_raw = (raw or {}).get("siem")
        if not siem_raw:
            return None
        return SiemCfg(
            host=str(siem_raw.get("host", "")),
            port=int(siem_raw.get("port", 514)),
            protocol=str(siem_raw.get("protocol", "udp")).lower(),
            export_after_scan=bool(siem_raw.get("export_after_scan", False)),
            timeout_seconds=int(siem_raw.get("timeout_seconds", 5)),
        )
    except Exception:
        return None  # binary/malformed/non-YAML: silently return None
```

**YAML config snippet (document in docs):**
```yaml
siem:
  host: siem.corp.example.com
  port: 514
  protocol: udp          # udp (default) or tcp
  export_after_scan: true
  timeout_seconds: 5
```

### Pattern 4: Per-Finding CEF Whitelist (New, Distinct from to_integration_payload)

**What:** The Phase 101 `to_integration_payload()` operates on `TrendReport` (drift-level aggregates). SIEM needs a per-finding whitelist. This is a NEW function — not a reuse of `to_integration_payload`.

**Confirmed fields from actual `findings-{stamp}.json`** (read from `output/findings-20260522-011356.json`):
```json
{
  "compliance": [...],        // EXCLUDED — internal control mapping
  "description": "...",       // OK as cs2/msg (truncated)
  "host": "127.0.0.1",        // ALLOWED (dhost)
  "port": 9443,               // ALLOWED (dpt)
  "recommendation": "...",    // OK as msg (truncated)
  "severity": "CRITICAL",     // ALLOWED → CEF severity integer
  "title": "TLS certificate expired"  // ALLOWED → CEF name
}
```

**Fields NOT present in findings JSON** (confirmed): `cert_pem`, `cert_sans`, `cert_subject`, `cert_issuer` — these live on `CryptoEndpoint` model (DB row), NOT in the findings dict. The findings JSON is already safe — the per-finding whitelist is defensive against future additions.

**Finding dict schema (confirmed from actual output file):**
- `severity` — string: "CRITICAL", "HIGH", "MEDIUM", "LOW"
- `host` — string (IP or hostname)
- `port` — integer
- `title` — string (human-readable finding name)
- `description` — string (finding description, safe to truncate)
- `recommendation` — string (remediation advice)
- `compliance` — list of dicts (framework/control refs — EXCLUDED from SIEM)
- `category` — string **NOT confirmed present in all findings** — signature field may need to fall back to a slug derived from `title`

**Note on `category` field:** The actual findings JSON examined shows no top-level `category` key — only `title`, `description`, `host`, `port`, `severity`, `recommendation`, `compliance`. The signature/category for CEF should be derived from `title` (slugified) or a dedicated `id` field if present. The planner should account for this: the formatter needs a fallback when `category` is absent.

**Whitelist function:**
```python
# ISEC-03 per-finding whitelist — distinct from to_integration_payload()
_FORBIDDEN_FIELDS = frozenset({
    "compliance", "cert_pem", "cert_subject", "cert_issuer",
    "cert_sans", "private_key", "key_material",
})

def to_cef_finding(finding: dict) -> dict:
    """Extract only whitelisted fields from a finding dict for CEF emission."""
    return {
        "severity": finding.get("severity", "LOW"),
        "host": finding.get("host", ""),
        "port": finding.get("port", ""),
        "title": finding.get("title", "Finding"),
        "category": finding.get("category") or _slugify(finding.get("title", "")),
        "description": str(finding.get("description", ""))[:256],
        "recommendation": str(finding.get("recommendation", ""))[:256],
    }
```

### Pattern 5: integration_deliveries Reuse

**Confirmed schema** (from `quirk/models.py` lines 245-261, Phase 101):
```
id, scan_id, finding_hash, destination, status, attempted_at, error_summary
```

**SIEM-specific column values:**
- `destination = "siem"`
- `scan_id` = derived from findings file path (the `{stamp}` portion) or passed in from the after-scan hook's `current_ts.isoformat()`
- `finding_hash` = `None` for the initial implementation (dedup is a ticketing concern per CONTEXT.md); set to None
- `status` = `"ok"` or `"failed"`
- `error_summary` = `safe_str(exc)` on failure, `None` on success

**From dispatcher.py (confirmed):** All audit rows are collected first, then committed in a single `db.commit()` to keep audit writes isolated from delivery failures.

**For SIEM export (per-finding rows vs per-channel rows):** Write one `IntegrationDelivery` row per finding attempt, or one summary row per batch. Decision: write one row per batch (all findings for one scan) to keep the table lightweight. The planner may decide per-finding — either is acceptable.

### Pattern 6: CLI Wiring — run_scan.py Interception Block

**Confirmed pattern** (lines 364-500 of run_scan.py): each subcommand is an `if len(_sys.argv) > 1 and _sys.argv[1] == "<cmd>":` block with a deferred import and `return`.

**New block to add (after `token` block, before `errors` or at end of chain):**
```python
# --- export subcommand: intercept before scan argparse (Phase 103 SIEM-01/02) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "export":
    from quirk.cli.export_cmd import run_export
    run_export(_sys.argv[2:])
    return
```

**export_cmd.py argparse shape** (modeled on analyze_token_cmd.py pattern):
```python
def run_export(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="quirk export")
    parser.add_argument("--siem", action="store_true", help="Export findings to SIEM via syslog/CEF")
    parser.add_argument("--input", default=None, metavar="PATH", help="Path to findings-*.json (default: latest in output/)")
    parser.add_argument("--output-dir", default="output", help="Output directory to search for latest findings-*.json")
    args = parser.parse_args(argv)
    if not args.siem:
        parser.print_help()
        sys.exit(1)
    # locate findings file
    # load siem config
    # export
```

### Pattern 7: After-Scan Hook — scheduler_cmd.py

**Confirmed hook location** (scheduler_cmd.py lines 170-184): immediately after the final `db.commit()` in `_dispatch_schedule`, before `return run`.

**New hook (add after the notification dispatch block):**
```python
# Phase 103 SIEM-01: after-scan SIEM export (when export_after_scan: true)
try:
    from quirk.siem.dispatcher import export_after_scan_hook
    export_after_scan_hook(run=run, schedule=schedule, db=db)
except Exception as exc:
    import logging as _logging
    from quirk.util.safe_exc import safe_str as _safe_str
    _logging.getLogger(__name__).warning(
        "SIEM export error (scan record unaffected): %s", _safe_str(exc)
    )
```

The `export_after_scan_hook` function loads `SiemCfg` via `load_siem_config()`, checks `cfg.export_after_scan`, locates the findings file from `run.scan_output_path`, and calls the dispatcher.

### Anti-Patterns to Avoid

- **Escaping extension values with header escaping rules:** header escapes `\` and `|`; extension escapes `\`, `=`, and `\n`. Using the same function for both breaks the CEF parser at the receiver.
- **Escaping backslash LAST:** always replace `\\` with `\\\\` FIRST in both header and extension escape functions; otherwise a previously escaped `\|` becomes `\\\\|` instead of `\\|`.
- **Reading the scheduler --config as a YAML path:** the `--config` arg in scheduler_cmd is a SQLite DB path. `load_siem_config()` MUST use `QUIRK_CONFIG_PATH` env var.
- **Blocking internal/loopback SIEM hosts:** unlike webhook SSRF prevention, syslog collectors are commonly on internal networks. Do NOT call `validate_external_url` for syslog host:port — validate only that host is non-empty and port is in range 1-65535.
- **Blocking the scan on SIEM failure:** all syslog transport exceptions must be caught and logged; the scan result is already committed.
- **Including `compliance` list in CEF payload:** the compliance array carries framework control references; it adds bulk and is not a standard CEF field.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Syslog `<PRI>` encoding | Custom bit-shift math | `logging.handlers.SysLogHandler.encodePriority(facility, priority)` or the raw `(facility * 8) + priority` formula (verified: LOG_USER=1, LOG_WARNING=4 → `<12>`) | Standard formula; SysLogHandler source confirmed |
| Config YAML parsing | Custom parser | `yaml.safe_load` (already used in notify/config.py) | Already a project dep |
| CEF char escaping | Regex-based substitution | String `.replace()` chain (always backslash first) | Replace chain is deterministic; regex can have ordering bugs |
| Audit table | New schema | `IntegrationDelivery` table from Phase 101 (confirmed schema above) | Table already exists after init_db; shared across phases 103/104/105 |
| Findings file discovery | Walk output tree | `max(Path(outdir).glob("findings-*.json"), key=lambda p: p.stat().st_mtime)` | Deterministic, no subprocess, stdlib only |

---

## Common Pitfalls

### Pitfall 1: CEF Escaping Order
**What goes wrong:** Extension value `host\=value` is intended to escape `=` but the backslash itself needs escaping first. Result: `host\\=value` instead of `host\=value`.
**Why it happens:** Applying escapes left-to-right without escaping the escape character first.
**How to avoid:** Always run `value.replace("\\", "\\\\")` as the FIRST step in both `_cef_escape_header` and `_cef_escape_extension`. Then apply character-specific escapes.
**Warning signs:** A test that sends a value containing a literal backslash and checks the receiver-parsed result shows a doubled backslash.

### Pitfall 2: QUIRK_CONFIG_PATH vs Scheduler DB Path
**What goes wrong:** `export_after_scan_hook` or `load_siem_config()` receives the scheduler's `config_path` argument (a `.db` file) and tries to `yaml.safe_load` it — silently returns None or raises.
**Why it happens:** Copying the function signature pattern from `_dispatch_schedule` without reading the critical comment.
**How to avoid:** `load_siem_config(path=None)` — no path argument from the scheduler. The function resolves via `QUIRK_CONFIG_PATH` env var only. This is already the `load_notifications_config` pattern.
**Warning signs:** `load_siem_config` returns None even when a YAML config exists; adding a print reveals a binary SQLite file was passed.

### Pitfall 3: UDP Datagram Size
**What goes wrong:** A CEF event with a very long description field exceeds the practical UDP datagram size and is silently dropped by the OS or fragmented.
**Why it happens:** `description` fields in findings can be 500+ characters; `recommendation` can be similar.
**How to avoid:** Truncate `description` and `recommendation` to 256 characters each before CEF encoding. The combined CEF line will stay under 1500 bytes (verified: sample CEF line is ~265 bytes with typical field lengths). Document truncation in code comments.
**Warning signs:** SIEM receiver shows fewer events than findings count; no transport error reported.

### Pitfall 4: `category` Field Absence
**What goes wrong:** `build_cef_event(finding, version)` calls `finding["category"]` but the actual findings JSON (confirmed from output files) has no top-level `category` key — only `title`, `description`, `host`, `port`, `severity`, `recommendation`, `compliance`.
**Why it happens:** The CONTEXT.md says signature=finding category/id, but the actual dict schema uses `title` as the primary identifier.
**How to avoid:** Implement fallback: `finding.get("category") or finding.get("id") or _slugify(finding.get("title", "UNKNOWN"))`.
**Warning signs:** All CEF events have an empty `signature` field; SIEM correlation rules break.

### Pitfall 5: TCP Framing / NUL Byte
**What goes wrong:** `SysLogHandler.emit()` appends a `\000` NUL byte (`append_nul=True` by default). Some syslog receivers reject NUL-terminated messages; others require it.
**Why it happens:** SysLogHandler's default behavior.
**How to avoid:** Use the raw socket approach (Pattern 2 above), which gives full control over the byte stream. Or set `handler.append_nul = False` explicitly when using SysLogHandler.
**Warning signs:** SIEM ingests 0 events despite successful socket send; Wireshark shows NUL at end of packet.

### Pitfall 6: cert PEM in Findings
**What goes wrong:** A future scanner update adds cert PEM material to the findings dict. The existing whitelist-based `to_cef_finding()` passes through unknown keys.
**Why it happens:** Whitelist function is implemented as field extraction (only named fields) but a future update might pass the raw finding dict through.
**How to avoid:** `to_cef_finding()` must be an EXPLICIT field extraction (construct the result dict from named `.get()` calls only), not a `{k: v for k, v in finding.items() if k not in FORBIDDEN_FIELDS}` exclusion approach. Confirmed: the current findings JSON doesn't include PEM, but the whitelist must be additive/explicit.

---

## Code Examples

### Complete CEF Escaping

```python
# Source: ArcSight CEF Implementation Standard (verified via WebSearch)
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

### Finding Field Discovery (actual findings.json shape)

```python
# Confirmed from output/findings-20260522-011356.json (actual scan output)
# Keys present in every finding:
#   severity, host, port, title, description, recommendation, compliance
# Keys NOT present (not in findings.json, only in CryptoEndpoint DB row):
#   cert_pem, cert_subject, cert_issuer, cert_sans, tls_version, cipher_suite
# Keys sometimes absent:
#   category (absent in examined files — fall back to slugified title)
#   id (not observed in output)

def to_cef_finding(finding: dict) -> dict:
    """Per-finding ISEC-03 whitelist. Explicit extraction only."""
    raw_desc = str(finding.get("description") or "")
    raw_rec = str(finding.get("recommendation") or "")
    return {
        "severity": str(finding.get("severity") or "LOW").upper(),
        "host": str(finding.get("host") or ""),
        "port": finding.get("port") or "",
        "title": str(finding.get("title") or "Finding"),
        "category": str(finding.get("category") or finding.get("id") or ""),
        "description_truncated": raw_desc[:256],
        "recommendation_truncated": raw_rec[:256],
    }
```

### Dispatcher Pattern (modeled on notify/dispatcher.py)

```python
# Source: quirk/notify/dispatcher.py pattern (lines 200-269 confirmed)
from datetime import datetime, timezone
from quirk.models import IntegrationDelivery
from quirk.util.safe_exc import safe_str
import logging

logger = logging.getLogger(__name__)

def export_findings(findings: list, cfg: SiemCfg, db, scan_id: str) -> int:
    """Export all findings to SIEM. Returns count of successful sends.

    One IntegrationDelivery row per batch (ok/failed). Never raises.
    """
    sent = 0
    errors = []
    version = _get_version()

    for finding in findings:
        safe_finding = to_cef_finding(finding)
        cef_line = build_cef_event(safe_finding, version)
        try:
            send_syslog_raw(cef_line, cfg.host, cfg.port, cfg.protocol, cfg.timeout_seconds)
            sent += 1
        except Exception as exc:
            errors.append(safe_str(exc))
            logger.warning("SIEM send failed for finding: %s", safe_str(exc))

    # One audit row per batch (like dispatcher.py WR-01 pattern)
    status = "ok" if not errors else "failed"
    row = IntegrationDelivery(
        scan_id=scan_id,
        finding_hash=None,
        destination="siem",
        status=status,
        attempted_at=datetime.now(timezone.utc).replace(tzinfo=None),
        error_summary=safe_str(Exception("; ".join(errors))) if errors else None,
    )
    db.add(row)
    try:
        db.commit()
    except Exception as exc:
        logger.warning("SIEM audit row commit failed: %s", safe_str(exc))
    return sent
```

### Test: socketserver-Based Capture

```python
# Source: Python stdlib socketserver (standard test pattern for UDP receivers)
import socketserver
import threading

class _UDPCapture(socketserver.UDPServer):
    """UDP server that captures incoming datagrams for assertion."""
    allow_reuse_address = True
    captured = []

    class _Handler(socketserver.BaseRequestHandler):
        def handle(self):
            self.server.captured.append(self.request[0])

    def __init__(self, host, port):
        super().__init__((host, port), self._Handler)

def test_send_cef_udp_delivers_to_receiver(tmp_path):
    server = _UDPCapture("127.0.0.1", 0)
    port = server.server_address[1]
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()
    cfg = SiemCfg(host="127.0.0.1", port=port, protocol="udp")
    send_syslog_raw("CEF:0|QUIRK|scanner|1.0.0|test|Test|5|dhost=localhost", "127.0.0.1", port, "udp")
    t.join(timeout=2)
    assert server.captured, "No UDP datagram received"
    assert b"CEF:0" in server.captured[0]
```

---

## Runtime State Inventory

**Trigger:** Not applicable — this is a greenfield feature addition, not a rename/refactor/migration phase.

None — verified: no existing SIEM-related stored data, OS registrations, or runtime state to migrate.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CEF over Splunk HEC (HTTP) | CEF over syslog UDP/TCP (vendor-neutral) | CONTEXT.md v5.3-D-04 | Works with any syslog-ingesting SIEM, not just Splunk |
| New pip dep (e.g., `pysyslog`) | stdlib `socket` | Phase 103 design | Zero new deps; simpler audit trail |

**Not applicable here:**
- `logging.handlers.SysLogHandler` has been in the stdlib since Python 2.3 — no version concerns for Python 3.11+.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All stdlib patterns | ✓ | Confirmed (project requirement) | — |
| `socket` module | Transport | ✓ | stdlib | — |
| `logging.handlers` | SysLogHandler reference | ✓ | stdlib | — |
| `pyyaml` | SiemCfg YAML parsing | ✓ | Project dep (already in requirements) | — |
| Live syslog receiver | Integration test | ✗ | N/A | `socketserver.UDPServer` in-test capture (no external dep) |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** A live SIEM receiver is not available for automated tests; the `socketserver` in-test capture pattern covers UDP delivery. TCP delivery can be tested with `socketserver.TCPServer`.

---

## Validation Architecture

Nyquist validation is enabled (`workflow.nyquist_validation: true` confirmed in `.planning/config.json`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pytest.ini` or `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/test_siem_formatter.py tests/test_siem_config.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SIEM-01 | Syslog UDP send delivers CEF event | unit | `pytest tests/test_siem_transport.py -x -q` | ❌ Wave 0 |
| SIEM-01 | Syslog TCP send delivers CEF event | unit | `pytest tests/test_siem_transport.py::test_send_cef_tcp -x -q` | ❌ Wave 0 |
| SIEM-01 | Unreachable endpoint → WARNING + audit row, no scan abort | unit | `pytest tests/test_siem_dispatcher.py::test_unreachable_endpoint -x -q` | ❌ Wave 0 |
| SIEM-01 | `[siem]` config loads from QUIRK_CONFIG_PATH | unit | `pytest tests/test_siem_config.py -x -q` | ❌ Wave 0 |
| SIEM-01 | QUIRK_CONFIG_PATH DB-path trap: binary file → None | unit | `pytest tests/test_siem_config.py::test_db_path_returns_none -x -q` | ❌ Wave 0 |
| SIEM-02 | CEF header field count is exactly 8 (pipe-delimited) | unit | `pytest tests/test_siem_formatter.py::test_cef_header_field_count -x -q` | ❌ Wave 0 |
| SIEM-02 | Header escaping: pipe and backslash in field values | unit | `pytest tests/test_siem_formatter.py::test_header_escaping -x -q` | ❌ Wave 0 |
| SIEM-02 | Extension escaping: equals, backslash, newline | unit | `pytest tests/test_siem_formatter.py::test_extension_escaping -x -q` | ❌ Wave 0 |
| SIEM-02 | Severity mapping: CRITICAL→10, HIGH→8, MEDIUM→5, LOW→3 | unit | `pytest tests/test_siem_formatter.py::test_severity_mapping -x -q` | ❌ Wave 0 |
| SIEM-02 | cert PEM / SANs absent from CEF payload | unit | `pytest tests/test_siem_payload_whitelist.py -x -q` | ❌ Wave 0 |
| SIEM-02 | host and port ARE present in CEF payload | unit | `pytest tests/test_siem_payload_whitelist.py::test_host_port_present -x -q` | ❌ Wave 0 |
| SIEM-02 | compliance list absent from CEF payload | unit | `pytest tests/test_siem_payload_whitelist.py::test_compliance_excluded -x -q` | ❌ Wave 0 |
| SIEM-02 | `quirk export --siem` locates latest findings file | unit | `pytest tests/test_export_cmd_wiring.py -x -q` | ❌ Wave 0 |
| SIEM-02 | After-scan hook dispatches when export_after_scan=true | unit | `pytest tests/test_siem_dispatcher.py::test_after_scan_hook_fires -x -q` | ❌ Wave 0 |
| SIEM-02 | After-scan hook no-ops when export_after_scan=false | unit | `pytest tests/test_siem_dispatcher.py::test_after_scan_hook_noop -x -q` | ❌ Wave 0 |
| SIEM-01/02 | integration_deliveries row written (destination=siem) | unit | `pytest tests/test_siem_dispatcher.py::test_audit_row_written -x -q` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_siem_formatter.py tests/test_siem_config.py -x -q`
- **Per wave merge:** `python -m pytest tests/test_siem_*.py tests/test_export_cmd_wiring.py -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

All test files are new:
- [ ] `tests/test_siem_formatter.py` — CEF format, escaping, severity mapping (SIEM-02)
- [ ] `tests/test_siem_transport.py` — UDP/TCP send via socketserver capture (SIEM-01)
- [ ] `tests/test_siem_config.py` — SiemCfg loader, QUIRK_CONFIG_PATH, DB-path trap (SIEM-01)
- [ ] `tests/test_siem_dispatcher.py` — per-finding dispatch, audit row, failure isolation, after-scan hook (SIEM-01/02)
- [ ] `tests/test_siem_payload_whitelist.py` — cert exclusion, host/port inclusion (SIEM-02)
- [ ] `tests/test_export_cmd_wiring.py` — run_scan.py interception, argparse (SIEM-02)
- [ ] `quirk/siem/__init__.py`, `config.py`, `formatter.py`, `transport.py`, `dispatcher.py` — implementation modules
- [ ] `quirk/cli/export_cmd.py` — CLI entrypoint

---

## Security Domain

`security_enforcement` is not explicitly set to false — treating as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth on syslog transport (by design — internal collector) |
| V3 Session Management | No | Stateless send |
| V4 Access Control | No | No user-facing auth in this phase |
| V5 Input Validation | Yes | `to_cef_finding()` explicit whitelist; host/port format validation; CEF escaping |
| V6 Cryptography | No | No crypto in CEF formatter; syslog transport is plaintext (TLS deferred) |

### Known Threat Patterns for CEF/syslog stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| CEF injection via finding content | Tampering | `_cef_escape_header` + `_cef_escape_extension` (pipe, backslash, equals, newline) |
| PEM/cert material in SIEM payload | Information Disclosure | `to_cef_finding()` explicit whitelist (not exclusion list) |
| Credential leak in error messages | Information Disclosure | `safe_str(exc)` on all exception handling |
| SSRF via SIEM host config | SSRF | Not applicable (syslog host:port, not an HTTP URL); validate host non-empty and port 1-65535 only |
| Log injection via finding content with newlines | Tampering | `_cef_escape_extension` replaces `\n`, `\r\n`, `\r` with `\n` literal |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `category` field is absent from all findings JSON output (only `title` observed) | Pattern 4 / Pitfall 4 | If `category` IS present in some findings, the fallback slug derivation is redundant but harmless |
| A2 | The syslog receiver does not require octet-count TCP framing (RFC 5425) — raw bytes sufficient | Standard Stack / Pattern 2 | If receiver requires octet-count framing, TCP delivery will silently fail; TLS-syslog (RFC 5425) defers this |
| A3 | LOG_USER facility (1) and LOG_WARNING syslog priority are appropriate defaults for SIEM events | Pattern 2 | Some SIEM ingestors filter by facility; may need config option in a future phase |

---

## Open Questions

1. **`category` field in findings dict**
   - What we know: Examined `output/findings-20260522-011356.json` has no top-level `category` key
   - What's unclear: Whether any scanner emits a `category` key (some finding generators may add it)
   - Recommendation: Implement the fallback: `finding.get("category") or finding.get("id") or slugify(title)`. A future pass can normalize if needed.

2. **Per-finding vs per-batch audit row**
   - What we know: Phase 101 writes one row per channel attempt (slack/email/webhook); SIEM sends N findings
   - What's unclear: Whether one row per batch or one per finding is more operationally useful
   - Recommendation: Start with one row per batch (simpler, same pattern as drift notification); `finding_hash` column exists for future per-finding dedup (ticketing phases 104/105)

---

## Sources

### Primary (HIGH confidence)
- ArcSight CEF Implementation Standard (Micro Focus) — CEF:0 header structure, escaping rules, extension key=value format. [VERIFIED via WebSearch + Delinea docs cross-reference]
- Python 3.11 stdlib `logging.handlers.SysLogHandler` source — `createSocket`, `emit` methods; socktype behavior; `<PRI>` encoding; timeout kwarg. [VERIFIED: stdlib source read in-session]
- `quirk/notify/config.py` (lines 1-184) — NotifyCfg/load_notifications_config pattern for SiemCfg. [VERIFIED: codebase read]
- `quirk/notify/dispatcher.py` (lines 1-270) — Fan-out pattern, IntegrationDelivery row construction, WR-01 single-commit pattern. [VERIFIED: codebase read]
- `quirk/cli/scheduler_cmd.py` (lines 110-186) — `_dispatch_schedule` after-hook location; QUIRK_CONFIG_PATH discipline; NOTIFY-07 error isolation. [VERIFIED: codebase read]
- `quirk/models.py` (lines 245-261) — IntegrationDelivery schema (7 columns + constraints). [VERIFIED: codebase read]
- `output/findings-20260522-011356.json` — Actual findings dict shape (keys: severity, host, port, title, description, recommendation, compliance). [VERIFIED: codebase read]

### Secondary (MEDIUM confidence)
- Delinea ArcSight CEF Format documentation — cross-reference for escaping rules [CITED: docs.delinea.com/online-help/cloud-suite/siem-integrations/arcsight-cef]
- `quirk/cli/analyze_token_cmd.py` — CLI subcommand pattern reference (argparse, deferred import, run_X entry point). [VERIFIED: codebase read]

### Tertiary (LOW confidence)
- RFC 3164 `<PRI>` encoding (`facility*8 + syslog_severity`) — `[ASSUMED]` from training; confirmed indirectly by `SysLogHandler.encodePriority` source which uses the same formula.

---

## Metadata

**Confidence breakdown:**
- CEF format spec: HIGH — cross-referenced ArcSight official docs + Delinea implementation guide
- Findings JSON shape: HIGH — read from actual scan output file
- stdlib transport: HIGH — read from Python 3.11 SysLogHandler source directly
- Phase 101 patterns (SiemCfg, integration_deliveries, safe_str): HIGH — read from actual codebase files
- CLI wiring (run_scan.py interception): HIGH — confirmed from actual code
- `category` field presence: LOW — only one findings file examined; may vary by scanner

**Research date:** 2026-05-24
**Valid until:** 2026-06-24 (stdlib and CEF spec are stable; findings schema changes are tracked in-codebase)

---

## RESEARCH COMPLETE

**Phase:** 103 - SIEM Export
**Confidence:** HIGH

### Key Findings

- The actual `findings-*.json` dict shape is: `severity`, `host`, `port`, `title`, `description`, `recommendation`, `compliance` — NO `category` key observed. The CEF signature field needs a fallback (slugify title). This is the primary implementation surprise.
- `logging.handlers.SysLogHandler` stdlib source confirmed: UDP default, TCP via `socktype=socket.SOCK_STREAM`, `timeout` kwarg sets `sock.settimeout()`, `emit()` prepends `<PRI>` and appends NUL. The raw socket approach avoids the NUL-byte and LogRecord wrapping complexities.
- CEF escaping has two distinct functions: header (`\` and `|`) vs extension (`\`, `=`, newlines). Backslash MUST be escaped first in both.
- The Phase 101 `to_integration_payload()` is a DRIFT-level whitelist (wrong shape for SIEM). A new `to_cef_finding()` whitelist is required — explicit field extraction, not exclusion-list.
- `IntegrationDelivery` table is confirmed fully sufficient: `destination="siem"`, `finding_hash=None`, shared by phases 103/104/105.
- After-scan hook placement confirmed: immediately after `dispatch_notifications` call in `_dispatch_schedule` (scheduler_cmd.py line ~183), same deferred-import + try/except pattern.

### File Created
`.planning/phases/103-siem-export/103-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| CEF format spec | HIGH | Official ArcSight docs cross-referenced |
| Findings JSON shape | HIGH | Read from actual scan output file |
| stdlib transport | HIGH | Python 3.11 SysLogHandler source read in-session |
| Phase 101 integration patterns | HIGH | All relevant source files read |
| `category` field presence | LOW | Single findings file examined; may vary |

### Open Questions
- Whether any scanner emits a `category` key (recommendation: implement fallback regardless)
- Per-finding vs per-batch IntegrationDelivery rows (recommendation: per-batch to start)

### Ready for Planning
Research complete. Planner can now create PLAN.md files for Phase 103.
