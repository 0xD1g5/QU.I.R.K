# Phase 145: Liveness Pre-Pass - Pattern Map

**Mapped:** 2026-08-10
**Files analyzed:** 5 (2 new/extended production modules, 1 modified orchestration file, 1 modified
model comment, 2 test files [1 new, 1 extended])
**Analogs found:** 5 / 5 (all in-repo, no external patterns needed — RESEARCH.md confirms this phase
is entirely additive to existing files with direct precedents)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `quirk/discovery/nmap_provider.py` (+ `run_nmap_liveness_check()`, `_liveness_nmap_args()`) | service (subprocess wrapper) | request-response (subprocess exec + parse) | `run_nmap_discovery()` in same file (lines 56-159) | exact — same file, sibling function |
| `quirk/discovery/nmap_parser.py` (+ `parse_nmap_host_status()`, `NmapHostStatus` dataclass) | transform (XML parser) | transform | `parse_nmap_xml()` in same file (lines 22-77) | exact — same file, sibling function, deliberately NOT extending existing function (Pitfall 3) |
| `run_scan.py` (batch loop insert, ~line 1298-1330; privilege check before loop) | controller/orchestration | event-driven (per-batch loop) + CRUD (CryptoEndpoint persistence) | Phase 144 batch loop itself (lines 1298-1325) + `_emit_missing_extra_advisory` (lines 167-182) | exact — same file, adjacent code, direct decision-mapped precedents (D-01→advisory, D-04→batch-failure row) |
| `quirk/models.py` (`scan_error_category` docstring comment) | model | n/a (schema/comment only) | `scan_error_category` column comment itself (line 35) | exact — additive comment edit, not a new column |
| `tests/test_nmap_parser.py` (**new file**) | test | transform | `tests/test_nmap_provider.py` (existing, for structure/style) — no parser-specific test file exists today | role-match (borrow style from provider tests; content targets parser) |
| `tests/test_nmap_provider.py` (extended) | test | event-driven / request-response | itself — `test_batch_failure_does_not_stop_subsequent_batches` etc. (lines 52-100) | exact — same file, same style, new test functions |

## Pattern Assignments

### `quirk/discovery/nmap_provider.py` — new `run_nmap_liveness_check()` + `_liveness_nmap_args()`

**Analog:** `run_nmap_discovery()` / `_default_nmap_args()`, same file (`quirk/discovery/nmap_provider.py:35-159`)

**Imports pattern** (lines 1-10, already present — no new imports needed beyond what's already
imported; `os.geteuid` guard lives in `run_scan.py`, not here):
```python
from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from quirk.logging_util import Logger
from quirk.discovery.nmap_parser import parse_nmap_xml, NmapOpenPort
# NEW: also import parse_nmap_host_status, NmapHostStatus from nmap_parser
```

**Existing allowlist regex to reuse verbatim** (line 14) — per Security Domain V5 in RESEARCH.md,
any port-spec string built for `-PS<ports>` MUST go through this same allowlist before being
appended to `args`:
```python
_SAFE_NMAP_ARG_RE = re.compile(r"^[A-Za-z0-9._:/=,-]+$")
```

**Core args-builder pattern to mirror** (`_default_nmap_args`, lines 35-53) — build a new sibling
`_liveness_nmap_args(port_spec: str) -> List[str]` following the exact same shape (flat list,
docstring explaining each flag's intent, `--max-retries`/`--host-timeout`/`--max-parallelism`
carried over unchanged from the sweep's own defaults for consistency):
```python
def _default_nmap_args(ports_csv: str) -> List[str]:
    """
    Defaults chosen to be:
    - Non-admin friendly: -sT (TCP connect scan)
    - No DNS: -n
    - Treat hosts as up: -Pn (works better in segmented environments)
    - Only show open ports: --open
    - Conservative retry/timeouts to keep scans fast
    """
    return [
        "-sT",
        "-n",
        "-Pn",
        "--open",
        "-p", ports_csv,
        "--max-retries", "1",
        "--host-timeout", "10s",
        "--max-parallelism", "100",  # D-07: hard-coded; not configurable in Phase 47.
    ]
```

**Core function pattern to mirror** (`run_nmap_discovery`, lines 56-159) — the new
`run_nmap_liveness_check()` must reuse this exact skeleton: empty-targets short-circuit, timestamped
XML output path, `_SAFE_NMAP_ARG_RE` validation of any port-spec tokens BEFORE `subprocess.run`,
identical `FileNotFoundError`/`TimeoutExpired`/non-zero-exit → `RuntimeError` normalization, logger
calls at the same points, and a final `parse_...()` call instead of `parse_nmap_xml`:
```python
def run_nmap_discovery(
    targets: List[str],
    ports: List[int],
    output_dir: str,
    logger: Optional[Logger] = None,
    nmap_path: str = "nmap",
    extra_args: Optional[List[str]] = None,
    timeout_seconds: int = 1800,
    port_spec_override: Optional[str] = None,  # Phase 121: "--top-ports 1000" or "-p-"
) -> List[NmapOpenPort]:
    if not targets:
        return []

    os.makedirs(output_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    xml_path = os.path.join(output_dir, f"nmap-discovery-{stamp}.xml")
    ...
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout_seconds)
    except FileNotFoundError as e:
        raise RuntimeError(
            "Nmap not found. Install Nmap and ensure 'nmap' is in PATH, or pass --nmap-path."
        ) from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"Nmap discovery timed out after {timeout_seconds}s. Consider reducing scope or increasing --nmap-timeout."
        ) from e

    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"Nmap discovery failed (exit {proc.returncode}). Output:\n{msg}")
    ...
```

**Port-spec resolution for `-PS`** (RESEARCH.md Pitfall 1 — MUST be handled explicitly, not
inherited automatically):
- `port_spec_override is None` → pass batch's resolved `ports_csv` (same list as sweep) as
  `-PS<csv>` (D-03 satisfied directly).
- `port_spec_override == "-p-"` → use `-PS-` (verified equivalent, full 1-65535 range).
- `port_spec_override == "--top-ports 1000"` → no `-PS` equivalent exists; default to `-PS-`
  (superset, never under-covers) per RESEARCH.md's explicit recommendation.

**Error handling pattern:** identical `RuntimeError` normalization to `run_nmap_discovery` (see
above) — this is what lets `run_scan.py`'s existing `except RuntimeError` batch-loop wrapper handle
liveness-check failures the same way it already handles sweep failures, without new exception types.

---

### `quirk/discovery/nmap_parser.py` — new `parse_nmap_host_status()` + `NmapHostStatus`

**Analog:** `parse_nmap_xml()`, same file (`quirk/discovery/nmap_parser.py:14-77`)

**Imports/header pattern to preserve exactly** (lines 1-11) — the WR-06 XXE-safe parser chokepoint
comment block must be honored by the new function too:
```python
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional
from lxml import etree as ET
from quirk.util.xml_safe import make_safe_parser
# WR-06 mitigation: XML parsed via quirk/util/xml_safe.py hardened lxml parser
# (resolve_entities=False, no_network=True, load_dtd=False, dtd_validation=False,
# huge_tree=False).  Phase 87 DEP-02 migration to the xml_safe chokepoint.
# Invariant test: tests/test_xml_safe.py::test_nmap_parser_blocks_xxe_lxml (D-07).
# DO NOT replace make_safe_parser() with a shared parser constant — see D-04.
```

**Dataclass pattern to mirror** (`NmapOpenPort`, lines 14-19):
```python
@dataclass
class NmapOpenPort:
    host: str
    port: int
    protocol: str
    service: Optional[str] = None

# NEW, sibling:
@dataclass
class NmapHostStatus:
    host: str
    up: bool
    reason: str  # e.g. "syn-ack", "conn-refused", "no-response"
```

**Critical divergence from the analog (Pitfall 3 — do NOT copy this part):** `parse_nmap_xml()`
(lines 32-35) treats a non-`"up"` status as `continue` (skip). The new function must NOT do this —
every host nmap reports on (up or down) must produce a row, or D-04's "record, don't drop" guarantee
breaks one layer downstream in the parser instead of the orchestrator:
```python
# EXISTING (parse_nmap_xml) — DO NOT COPY THIS FILTER BEHAVIOR:
for host_el in root.findall("host"):
    status_el = host_el.find("status")
    if status_el is not None and status_el.get("state") not in (None, "up"):
        continue   # <-- skip-if-not-up: correct for the sweep, WRONG for liveness parsing
    ...
```

**Address-extraction pattern to reuse verbatim** (lines 37-48, IPv4-preferred fallback):
```python
addr = None
for addr_el in host_el.findall("address"):
    if addr_el.get("addrtype") == "ipv4":
        addr = addr_el.get("addr")
        break
if addr is None:
    addr_el = host_el.find("address")
    addr = addr_el.get("addr") if addr_el is not None else None
if not addr:
    continue
```

**New function shape** (verified against live nmap 7.991 XML output — see RESEARCH.md Pattern 2):
```python
def parse_nmap_host_status(xml_path: str) -> List[NmapHostStatus]:
    tree = ET.parse(xml_path, parser=make_safe_parser())
    root = tree.getroot()
    results: List[NmapHostStatus] = []
    for host_el in root.findall("host"):
        status_el = host_el.find("status")
        if status_el is None:
            continue
        state = status_el.get("state")
        reason = status_el.get("reason") or ""
        addr = None
        for addr_el in host_el.findall("address"):
            if addr_el.get("addrtype") == "ipv4":
                addr = addr_el.get("addr")
                break
        if addr is None:
            addr_el = host_el.find("address")
            addr = addr_el.get("addr") if addr_el is not None else None
        if not addr:
            continue
        results.append(NmapHostStatus(host=addr, up=(state == "up"), reason=reason))
    return results
```

---

### `run_scan.py` — batch-loop pre-pass insertion + once-per-scan privilege check + advisory

**Analog 1 (privilege-fallback disclosure, D-01):** `_emit_missing_extra_advisory()`
(`run_scan.py:167-182`)
```python
def _emit_missing_extra_advisory(scanner_name: str, extra_group: str, error_endpoints) -> None:
    """Phase 41 / D-12 — Phase 68 UX-02: emit QRK-INSTALL-001 stderr advisory + record CryptoEndpoint row.

    Invoked when an optional-extra-gated scanner is enabled but its underlying
    package is not installed. Emits format_error("INSTALL-001") to stderr and
    appends a CryptoEndpoint with scan_error_category='missing_extra' so
    trends.py can exclude it from regression counts (D-15).
    """
    print(format_error("INSTALL-001"), file=sys.stderr)
    error_endpoints.append(CryptoEndpoint(
        host=scanner_name,
        port=0,
        protocol="ADVISORY",
        scan_error=f"optional extra [{extra_group}] not installed",
        scan_error_category="missing_extra",
    ))
```
D-01's new `_emit_liveness_fallback_advisory(...)`-style helper (or inline block) should follow this
exact shape: a logger message (not necessarily `print(...file=sys.stderr)` — RESEARCH.md's Open
Question 1 recommends calling this once, before the batch loop, gated on the precomputed
`is_privileged` flag) + one `CryptoEndpoint(..., protocol="ADVISORY", scan_error_category=...)` row
appended to `error_endpoints`.

**Analog 2 (batch-failure CryptoEndpoint row shape, D-04/D-05):**
`run_scan.py:1316-1325` (Phase 144 batch-failure precedent):
```python
except RuntimeError as exc:
    logger.error(f"discovery batch {batch_num} failed: {exc!r}")
    error_endpoints.append(CryptoEndpoint(
        host=f"discovery-batch-{batch_num}",
        port=0,
        protocol="ERROR",
        scan_error=str(exc) or exc.__class__.__name__,
        scan_error_category="exception",
    ))
    continue
```
D-04/D-05's per-host liveness-skip row must mirror this shape but at per-host (not per-batch)
granularity, with `host=<actual host>` (not a synthetic `discovery-batch-N` label — real per-host
identity is exactly what D-04 asks for) and the new `scan_error_category="liveness_skip"`:
```python
error_endpoints.append(CryptoEndpoint(
    host=status.host,
    port=0,
    protocol="ADVISORY",  # or a new category-specific value — planner to confirm
    scan_error="liveness pre-pass: no response",
    scan_error_category="liveness_skip",
))
```

**Insertion point (the batch loop itself):** `run_scan.py:1298-1325`
```python
_discovery_batch_loop_ran = True
all_open_ports: List = []
batch_num = 0
host_iter = _expand_and_dedup_hosts(nmap_targets, cfg.targets.exclude_ips or [])
for batch in _chunked(host_iter, _MAX_HOSTS_PER_CIDR):
    batch_num += 1
    try:
        batch_open_ports = run_nmap_discovery(
            targets=batch,
            ports=ports_for_nmap if port_spec_override is None else [],
            output_dir=cfg.output.directory,
            logger=logger,
            nmap_path=args.nmap_path,
            extra_args=extra_args.split() if extra_args else None,
            timeout_seconds=args.nmap_timeout,
            port_spec_override=port_spec_override,  # Phase 121
        )
        all_open_ports.extend(batch_open_ports)
    except RuntimeError as exc:
        logger.error(f"discovery batch {batch_num} failed: {exc!r}")
        error_endpoints.append(CryptoEndpoint(
            host=f"discovery-batch-{batch_num}",
            port=0,
            protocol="ERROR",
            scan_error=str(exc) or exc.__class__.__name__,
            scan_error_category="exception",
        ))
        continue
```
The pre-pass inserts a new step immediately inside this `for batch in ...:` loop, before the
existing `try: batch_open_ports = run_nmap_discovery(...)` call — filtering `batch` down to
responsive hosts first, appending `liveness_skip` rows for non-responsive ones, and skipping the
`run_nmap_discovery()` call entirely if `responsive_hosts` is empty (RESEARCH.md Pitfall 4). The
once-per-scan `is_privileged` check and its advisory emission happen once, before this loop starts
(not inside the `for` body) — see RESEARCH.md Open Question 1 / Pattern 3.

**Privilege-check pattern (D-02, genuinely new — no existing analog in this codebase for
`os.geteuid`)**, verified live against nmap 7.991:
```python
import os

def _is_privileged() -> Optional[bool]:
    """POSIX only. Returns None on platforms without geteuid (Windows) — caller must
    treat None as 'unknown, assume unprivileged for safety' per D-01's spirit (never
    silently claim privileged when we can't verify)."""
    geteuid = getattr(os, "geteuid", None)
    if geteuid is None:
        return None
    return geteuid() == 0
```

---

### `quirk/models.py` — `scan_error_category` comment update (D-05)

**Analog:** the existing inline comment on the same column, `quirk/models.py:35`
```python
scan_error_category = Column(String(32), nullable=True)  # Phase 41 D-11 + Phase 57 D-06: missing_extra|timeout|exception|config|invalid_input
```
D-05 extends this comment (additive, no schema/migration change since it's an untyped `String(32)`
column already) to append `|liveness_skip` to the pipe-delimited enum-in-comment list, following the
exact style of prior phases appending their own new category values to this same line.

---

### `tests/test_nmap_provider.py` (extend) + `tests/test_nmap_parser.py` (new)

**Analog:** `tests/test_nmap_provider.py` full file (existing style: fake-callable, not
`unittest.mock.patch(subprocess.run)`; each test asserts on `CryptoEndpoint` fields directly)

**File header/import pattern** (lines 1-23):
```python
"""Phase 47 / Plan 02: tests for nmap_provider._default_nmap_args.
...
Phase 144 / Plan 02 (DISC-02, D-03/D-04): tests for the sequential per-batch
discovery loop's failure-isolation behavior. ...
"""
from __future__ import annotations

from typing import List

import pytest

from quirk.models import CryptoEndpoint
from quirk.scanner.target_expander import _chunked, _expand_and_dedup_hosts, _MAX_HOSTS_PER_CIDR
```
New Phase 145 tests should add a matching docstring block at the top explaining what they cover
(DISC-03, D-01/D-04/D-05) and reuse `_chunked`/`_expand_and_dedup_hosts` imports the same way.

**Batch-loop-mirroring helper pattern to replicate** (lines 26-49) — `_run_batched_discovery` mirrors
`run_scan.py`'s inline loop exactly so tests don't need a full `main()` run. Phase 145 needs an
equivalent `_run_liveness_prepass(...)` helper mirroring the NEW loop shape (privilege check once,
per-batch liveness filter, `liveness_skip` row append), same "mirrors run_scan.py's X exactly"
docstring convention:
```python
def _run_batched_discovery(host_tokens: List[str], discover_fn, chunk_size: int = _MAX_HOSTS_PER_CIDR):
    """Mirrors run_scan.py's discovery-block batch loop exactly (Phase 144 / D-03/D-04): ..."""
    error_endpoints: List[CryptoEndpoint] = []
    all_open_ports: List = []
    batch_num = 0
    host_iter = _expand_and_dedup_hosts(host_tokens)
    for batch in _chunked(host_iter, chunk_size):
        batch_num += 1
        try:
            batch_open_ports = discover_fn(batch)
            all_open_ports.extend(batch_open_ports)
        except RuntimeError as exc:
            error_endpoints.append(CryptoEndpoint(
                host=f"discovery-batch-{batch_num}",
                port=0,
                protocol="ERROR",
                scan_error=str(exc) or exc.__class__.__name__,
                scan_error_category="exception",
            ))
            continue
    return all_open_ports, error_endpoints, batch_num
```

**Test-per-behavior pattern to replicate** (lines 52-100) — one focused test per behavior, plain
`assert`, descriptive docstring citing the requirement ID:
```python
def test_batch_failure_does_not_stop_subsequent_batches():
    """A batch that raises RuntimeError does not abort the loop — batch 2
    failing must not prevent batch 3 from running (DISC-02)."""
    calls = []

    def fake_discover(batch):
        calls.append(batch)
        if len(calls) == 2:
            raise RuntimeError("nmap discovery timed out — batch 2 sentinel")
        return [f"open:{batch[0]}"]

    results, errors, batch_count = _run_batched_discovery(
        ["10.0.0.1", "10.0.0.2", "10.0.0.3"], fake_discover, chunk_size=1,
    )

    assert batch_count == 3, "all 3 batches must be attempted, not just up to the failure"
    assert len(calls) == 3, "batch 3's discover call must still happen after batch 2 fails"
    assert len(errors) == 1
    assert errors[0].scan_error_category == "exception"
    assert errors[0].protocol == "ERROR"
```
RESEARCH.md ships a directly-adapted example for the new liveness-skip test
(`test_liveness_skip_appends_liveness_skip_category`, RESEARCH.md "Code Examples" section) — reuse
that verbatim as the seed test, plus one for `_is_privileged()`'s `os.geteuid` monkeypatch (stdlib
`unittest.mock.patch("os.geteuid", ...)`, standard low-risk pattern, no existing repo analog needed).

`tests/test_nmap_parser.py` does not exist yet (RESEARCH.md Wave 0 Gap) — model its structure on
`tests/test_nmap_provider.py`'s header/docstring convention, targeting `parse_nmap_host_status()`
with inline XML strings (mirroring the up/down `<host><status state="...">` shape verified in
RESEARCH.md Pattern 2) rather than requiring a live nmap binary.

---

## Shared Patterns

### CryptoEndpoint advisory/error-row shape
**Source:** `run_scan.py:167-182` (`_emit_missing_extra_advisory`) and `run_scan.py:1316-1325`
(batch-failure precedent)
**Apply to:** Both D-01 (privilege-fallback advisory, once per scan) and D-04/D-05 (per-host
liveness-skip rows, per non-responsive host)
```python
error_endpoints.append(CryptoEndpoint(
    host=<identity string>,       # scanner_name / "discovery-batch-N" / real host per D-04
    port=0,
    protocol="ADVISORY" | "ERROR",
    scan_error=<human-readable string>,
    scan_error_category=<new "liveness_skip" or existing "missing_extra"/"exception">,
))
```
Both new call sites in this phase are additive uses of this exact same constructor call shape —
no new helper class or row schema is needed.

### `_SAFE_NMAP_ARG_RE` allowlist validation
**Source:** `quirk/discovery/nmap_provider.py:14` + its two existing call sites (lines 88-90,
119-120)
**Apply to:** Any port-spec string built for the new `-PS<ports>` argument (RESEARCH.md Security
Domain V5) — must go through `_SAFE_NMAP_ARG_RE.fullmatch()` before being appended to `args`, exactly
like `port_spec_override` and `extra_args` tokens already are.
```python
for token in override_tokens:
    if not _SAFE_NMAP_ARG_RE.fullmatch(token):
        raise ValueError(f"Unsafe port_spec_override token: {token!r}")
```

### RuntimeError normalization for subprocess failures
**Source:** `run_nmap_discovery()`, `quirk/discovery/nmap_provider.py:138-149`
**Apply to:** `run_nmap_liveness_check()` — identical `FileNotFoundError` → RuntimeError,
`TimeoutExpired` → RuntimeError, non-zero exit → RuntimeError mapping, so the existing
`except RuntimeError` batch-loop wrapper in `run_scan.py` continues to work unmodified for
liveness-check failures too (no new exception type needed).

### WR-06 XXE-safe parser chokepoint
**Source:** `quirk/discovery/nmap_parser.py:1-11` header comment + `make_safe_parser()` usage
**Apply to:** `parse_nmap_host_status()` — MUST call `ET.parse(xml_path, parser=make_safe_parser())`
exactly like `parse_nmap_xml()` does; this is an enforced invariant
(`tests/test_xml_safe.py::test_nmap_parser_blocks_xxe_lxml`), not optional.

## No Analog Found

None — RESEARCH.md confirms every piece of this phase (subprocess plumbing, XML parsing scaffold,
advisory-row disclosure, batch-failure row shape, allowlist validation, XXE-safe parser chokepoint)
has a direct in-repo precedent in the same files it touches. The one genuinely new element —
`os.geteuid()`-based privilege detection (D-02) — has no prior pattern to copy (RESEARCH.md is
explicit: "No existing precedent for privilege detection... anywhere in the codebase today"), but
RESEARCH.md's verified, ready-to-use implementation (`_is_privileged()`, Pattern 3 above) serves as
the source of truth for that one piece instead of a codebase analog.

## Metadata

**Analog search scope:** `quirk/discovery/`, `run_scan.py`, `quirk/models.py`, `tests/` (files
directly named in CONTEXT.md's `canonical_refs` and RESEARCH.md's "Recommended Project Structure")
**Files scanned:** `quirk/discovery/nmap_provider.py`, `quirk/discovery/nmap_parser.py`,
`run_scan.py` (lines 140-200, 1260-1350), `quirk/models.py` (CryptoEndpoint class),
`tests/test_nmap_provider.py` (full file)
**Pattern extraction date:** 2026-08-10
