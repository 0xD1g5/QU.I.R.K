# Phase 145: Liveness Pre-Pass - Research

**Researched:** 2026-08-10
**Domain:** nmap host-discovery (TCP SYN ping), subprocess/XML integration, privilege detection
**Confidence:** HIGH

## Summary

This phase is small and well-scoped by CONTEXT.md's six locked decisions (D-01..D-06). The
remaining work for research was to confirm exact nmap CLI/XML behavior against a live nmap
7.991 binary and to reconcile D-03 (reuse the batch's full-sweep port list for the pre-pass) with
the fact that `-PS<port-list>` cannot accept `--top-ports N` syntax the way `-p` can.

Live testing against a local nmap binary (non-root shell) confirms the core premise behind D-02:
**nmap's `-sn -PS<ports>` output is byte-for-byte indistinguishable between a privileged SYN probe
and an unprivileged connect-fallback probe** — same XML shape, same `reason="syn-ack"` value, same
exit code 0. There is no reliable post-hoc signal to detect the fallback from nmap's own output.
D-02's "check `os.geteuid()` once, before the loop" approach is therefore not just simpler but the
*only* reliable approach — this is now VERIFIED, not just assumed.

`quirk/discovery/nmap_parser.py::parse_nmap_xml()` currently only returns open **ports** — it reads
`<host><status>` purely as a filter (skip host entirely if not "up") and throws away host-level
up/down state. A new function is needed to expose per-host liveness, because the existing return
type (`List[NmapOpenPort]`, one row per open port) cannot represent "this host was queried and
found down" — a down host has zero ports and would otherwise vanish silently, which is exactly
what D-04 says must not happen.

The port-list mismatch (`-PS` vs `--top-ports`) needs a documented resolution: when
`port_spec_override` is `"-p-"`, the direct nmap-verified equivalent is `-PS-` (tested, works,
covers all 65535 ports). When `port_spec_override` is `"--top-ports 1000"`, there is no `-PS`
equivalent for "top N ports" — `-PS`'s argument grammar is the same as `-p` minus type specifiers,
and `--top-ports` is not a valid `-p`-style token. The safe, D-03-consistent resolution is to
default the pre-pass to `-PS-` (full 1-65535 range) whenever `port_spec_override` is set, since
that is always a superset of both the `-p-` and `--top-ports 1000` sweep scopes — it never
under-covers, matching D-03's "correctness over speed for wide scans" framing at the cost of the
pre-pass being closer in cost to the sweep itself for wide-scope runs. This is a design detail
planners must make explicit, not something automatically handled by simply forwarding
`port_spec_override`.

No chaos-lab profile or `lab.sh` change is needed for D-06's verification: the privilege gap is a
property of the **host process running QUIRK** (root vs. non-root shell), not of any target
service the lab exposes. Any existing lab profile (e.g. `common`) is sufficient as the scan target;
the human-UAT variable is "run `run_scan.py` from a non-root shell" vs. root/sudo, not a new
Docker service. CLAUDE.md's chaos-lab-maintenance clause therefore does not trigger for this phase.

**Primary recommendation:** Add a sibling function `run_nmap_liveness_check()` in
`nmap_provider.py` (mirrors `run_nmap_discovery()`'s subprocess/XML plumbing but issues
`-sn -PS<ports>` and returns host-level up/down, not open ports), a new `parse_nmap_host_status()`
function in `nmap_parser.py` (extracts `<host><status state="..."/>` + address, does not touch the
existing port-parsing function), a one-time `_privileged = os.geteuid() == 0 if hasattr(os,
"geteuid") else None` check before the Phase 144 batch loop, and per-batch pre-pass filtering that
appends `CryptoEndpoint(host=<host>, port=0, scan_error_category="liveness_skip")` rows for
non-responsive hosts before calling `run_nmap_discovery()` on the survivors.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| TCP SYN/ACK liveness probe execution | Backend (discovery module, `quirk/discovery/nmap_provider.py`) | — | Subprocess/nmap invocation is backend-only; no CLI/dashboard surface in this phase |
| Host up/down XML parsing | Backend (`quirk/discovery/nmap_parser.py`) | — | Pure parsing function, same tier as existing `parse_nmap_xml()` |
| Privilege detection (`os.geteuid()`) | Backend (`run_scan.py`, scan orchestration) | — | Process-level fact, determined once per scan run before batch loop |
| Liveness-skip / fallback disclosure | Backend (`CryptoEndpoint` rows + logger) | Database (SQLite `crypto_endpoints` table) | Follows existing `_emit_missing_extra_advisory` precedent — DB row is the artifact of record; report/dashboard surfacing is explicitly deferred to Phase 146 |

## Standard Stack

### Core
No new dependencies. This phase extends existing code:

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|---------------|
| `nmap` binary | 7.80+ (project already requires this for discovery) | `-sn -PS<ports>` liveness probe | Already the sole discovery engine (`quirk/discovery/nmap_provider.py`); no python-nmap or other wrapper library is used anywhere in this codebase — confirmed via `grep` (subprocess.run only) |
| `lxml` (`quirk.util.xml_safe.make_safe_parser`) | already pinned in repo | XML parsing of `-oX` output | Existing hardened XXE-safe parser chokepoint (WR-06); the new host-status parser MUST reuse this, not stdlib `xml.etree` |
| `os.geteuid()` (stdlib) | n/a | POSIX privilege check | Per D-02; POSIX-only, no Windows equivalent — see Pitfall below |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `os.geteuid() == 0` | `python-nmap`'s built-in privilege detection, or shelling `id -u` | Both add complexity/deps for no benefit; `os.geteuid()` is stdlib, zero-cost, and exactly what D-02 specifies |
| New sibling function `run_nmap_liveness_check()` | Extend `run_nmap_discovery()` with a `mode` param | Rejected — D-06/canonical_refs explicitly recommend a sibling function since the two nmap invocations have different flags (`-sT` vs `-sn -PS`), different return shapes (open ports vs. host status), and different failure semantics (skip-and-record vs. batch-abort) |

**Installation:** None — no new packages. `pip install` is not required for this phase.

**Version verification:** `nmap --version` on the dev machine reports `Nmap version 7.991`
[VERIFIED: local binary]. The `-PS` flag syntax and silent-fallback behavior described below were
tested live against this binary, not sourced from training data alone.

## Package Legitimacy Audit

Not applicable — this phase introduces zero new external packages (Python or otherwise). No
`slopcheck`/registry verification is required.

## Architecture Patterns

### System Architecture Diagram

```
Phase 144 batch loop (run_scan.py, per-batch iteration)
                                                          
  [batch: List[str] hosts] 
        │
        ▼
  ┌─────────────────────────────┐   privileged? (once, before loop)
  │ NEW: liveness pre-pass step │◄──────────────────────────────────┐
  │ run_nmap_liveness_check()   │                                   │
  │  -sn -PS<batch's port list> │                        os.geteuid()==0 (POSIX)
  └──────────────┬──────────────┘                        checked ONCE, reused
                 │ XML → parse_nmap_host_status()         for every batch's
                 ▼                                        fallback-advisory
   ┌───────────────────────────┐                          decision
   │ split batch into:         │
   │  - responsive hosts        │
   │  - non-responsive hosts    │
   └─────────┬──────────┬──────┘
             │          │
             │          ▼
             │   append CryptoEndpoint(host, port=0,
             │     scan_error_category="liveness_skip")
             │   per non-responsive host (D-04/D-05)
             │
             │   if not privileged: ALSO append/log
             │     fallback-advisory row (D-01), once
             │     per scan (not per batch/host)
             ▼
  run_nmap_discovery() — existing -sT full sweep,
  UNCHANGED, called only on responsive hosts
             │
             ▼
  existing Phase 144 error-handling / ScanCheckpoint path
  (RuntimeError → error_endpoints, continue to next batch)
```

### Recommended Project Structure
No new files/directories. Changes land in existing files:
```
quirk/discovery/
├── nmap_provider.py     # + run_nmap_liveness_check(), + _liveness_nmap_args() (or inline)
├── nmap_parser.py        # + parse_nmap_host_status() (new function, sibling to parse_nmap_xml)
run_scan.py                # discovery batch loop (~1290-1330): insert pre-pass step + privilege check
quirk/models.py             # scan_error_category docstring: add "liveness_skip" to comment enum
tests/
├── test_nmap_provider.py  # extend with liveness pre-pass unit tests (mocked subprocess)
```

### Pattern 1: Sibling function for the liveness probe, not a mode flag
**What:** `run_nmap_liveness_check(targets, ports_csv_or_dash, ...)` — separate function from
`run_nmap_discovery()`, built the same way (subprocess.run + `-oX` temp file + parse), but hardcodes
`-sn -PS<ports>` instead of `-sT ... --open`.
**When to use:** Always for this phase — do not add a `mode="liveness"` branch inside
`run_nmap_discovery()`. The two calls have incompatible return types (host status list vs. open-port
list) and incompatible failure semantics (a liveness-check failure should probably not abort the
batch's sweep the same way a sweep failure does — planner should decide, but keeping the functions
separate keeps that decision isolated).
**Example:**
```python
# Source: adapted from quirk/discovery/nmap_provider.py:_default_nmap_args (existing pattern)
def _liveness_nmap_args(port_spec: str) -> List[str]:
    """
    port_spec: either an explicit CSV ("22,443,...") or "-" for full 1-65535 range
    (used when the batch's sweep itself uses port_spec_override, see Pitfall below).
    """
    return [
        "-sn",
        f"-PS{port_spec}",
        "-n",
        "--max-retries", "1",
        "--host-timeout", "10s",
        "--max-parallelism", "100",
    ]
```

### Pattern 2: New parser function, not an extension of `parse_nmap_xml()`
**What:** `parse_nmap_host_status(xml_path) -> List[NmapHostStatus]` where
`NmapHostStatus` is a new small dataclass `(host: str, up: bool, reason: str)`.
**When to use:** Any time the pre-pass needs host-level up/down, since
`parse_nmap_xml()`'s return type (`NmapOpenPort`, one row per open port) structurally cannot
represent a down host (zero ports = invisible, which is the exact bug D-04 exists to prevent).
**Example — verified XML shape from a live `-sn -PS443` run:**
```xml
<!-- Source: live nmap 7.991 test run, this session -->
<host><status state="up" reason="syn-ack" reason_ttl="0"/>
<address addr="127.0.0.1" addrtype="ipv4"/>
...
</host>
<runstats><hosts up="1" down="0" total="1"/></runstats>
```
A down host still gets a `<host>` element with `<status state="down" .../>` (nmap does not omit
`<host>` elements for down targets in `-sn` mode when the target was explicitly listed) — confirm
this during implementation with a target expected to be down, but the `<status>` element's presence
on every listed host (not just "up" ones) is the documented XML contract per nmap's DTD, consistent
with `parse_nmap_xml()`'s existing code already reading `status_el.get("state")` as a value that can
be `"up"` or something else.
```python
@dataclass
class NmapHostStatus:
    host: str
    up: bool
    reason: str  # e.g. "syn-ack", "conn-refused", "no-response"

def parse_nmap_host_status(xml_path: str) -> List[NmapHostStatus]:
    tree = ET.parse(xml_path, parser=make_safe_parser())  # reuse WR-06 hardened parser
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

### Pattern 3: Privilege check — once per scan, POSIX only
**What:** Determine `is_privileged` once, before the batch loop starts (D-02), reuse for every
batch's fallback-advisory decision.
**Example — VERIFIED behavior, tested this session:**
```python
# Source: tested live — nmap -sS (as scan TYPE) hard-errors without root:
#   "You requested a scan type which requires root privileges. QUITTING!" (exit != 0)
# But -sn -PS<ports> (ping-scan-style probe, not -sS scan type) does NOT error —
# it silently substitutes a connect() probe and returns exit 0 with IDENTICAL XML
# shape/fields (including reason="syn-ack") whether privileged or not. Confirmed by
# running the exact same command with and without --unprivileged and diffing output —
# zero difference except the echoed args line.
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
**Corroborating signal check (requested by orchestrator prompt):** None exists. Tested `reason=`
attribute, exit code, and stdout/stderr with `-v` verbosity — all identical between privileged and
`--unprivileged`-forced runs. `--privileged` / `--unprivileged` are nmap flags that let you *force*
a specific behavior for testing without needing an actual privilege change — this is useful for
writing a deterministic integration test (see Common Pitfalls / Code Examples below) but they are
not an output *signal*; nmap does not tell you afterward which path it took. D-02's approach is
confirmed as not just sufficient but the only reliable option.

### Anti-Patterns to Avoid
- **Inferring fallback from nmap stdout/stderr text-matching:** No such message exists for `-PS`
  ping-probe fallback (only `-sS` as an explicit scan *type* errors out; `-PS` as a *discovery
  probe* degrades silently). Do not write a regex against nmap output looking for a "falling
  back" string — it does not exist for this code path.
- **Re-deriving privilege per batch:** Rejected by D-02 explicitly; also wasteful — `os.geteuid()`
  doesn't change mid-process.
- **Forwarding `port_spec_override` string verbatim into `-PS`:** `-PS--top-ports 1000` is not
  valid nmap syntax (`-PS` takes a port-list/range argument, same grammar as `-p` minus `T:` type
  specifiers — `--top-ports` is not part of that grammar). Must resolve to an explicit port spec
  before building the `-PS` argument (see Common Pitfalls).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TCP liveness detection | A custom raw-socket or `connect()`-based liveness prober in Python | nmap's own `-sn -PS<ports>` | nmap already handles the privileged/unprivileged branching, timeouts, and parallelism; the project's entire discovery layer is nmap-subprocess-based already — adding a second, parallel liveness mechanism (e.g. Python `socket.connect_ex`) would duplicate logic, introduce a second privilege-handling code path, and diverge from the one nmap binary the rest of discovery already depends on |
| XXE-safe XML parsing | A fresh `lxml.etree.parse()` call with default parser | `quirk.util.xml_safe.make_safe_parser()` | WR-06 mitigation chokepoint; `nmap_parser.py`'s docstring explicitly warns "DO NOT replace `make_safe_parser()` with a shared parser constant" — any new parsing function in this file must call it the same way `parse_nmap_xml()` does |

**Key insight:** This phase's entire job is filling two small, well-understood gaps in code that
already exists and already works (subprocess/XML plumbing in `nmap_provider.py`/`nmap_parser.py`,
advisory-row pattern in `run_scan.py`). There is no greenfield infrastructure decision here — every
piece has a direct precedent in the same file.

## Common Pitfalls

### Pitfall 1: `-PS` cannot accept `--top-ports N` or `-p-` verbatim in all cases
**What goes wrong:** Naively doing `f"-PS{port_spec_override}"` when `port_spec_override ==
"--top-ports 1000"` produces `-PS--top-ports 1000`, which is invalid nmap syntax and will error.
**Why it happens:** `-PS`'s port-list grammar matches `-p`'s grammar (numbers, ranges, commas) but
NOT `-p`'s special flags like `--top-ports` or bare `-p-` is actually valid for `-PS` (`-PS-` was
tested and works, giving the 1-65535 range) — only `--top-ports` has no `-PS` equivalent.
**How to avoid:**
- `port_spec_override is None` (normal/"Common TLS" scope): pass the batch's resolved
  `ports_csv` (same list used for the sweep) directly as `-PS<csv>`. D-03 satisfied exactly.
- `port_spec_override == "-p-"`: use `-PS-` (VERIFIED: tested locally, equivalent full-range
  probe, exit 0, correct XML).
- `port_spec_override == "--top-ports 1000"`: no exact `-PS` equivalent exists. Recommend
  defaulting to `-PS-` (full range) here too — it is a strict superset of "top 1000 ports" so it
  can never wrongly mark a host non-responsive, matching D-03's reliability-first framing. Document
  this as a deliberate simplification (probe cost ≈ full-range for both wide-scope options) rather
  than silently under-covering.
**Warning signs:** A liveness pre-pass that returns 0 live hosts for a target known to be up on a
`--top-ports 1000`/`-p-` scoped scan — check the actual `-PS` argument string built for that batch.

### Pitfall 2: `os.geteuid()` doesn't exist on Windows
**What goes wrong:** `AttributeError: module 'os' has no attribute 'geteuid'` on Windows.
**Why it happens:** `geteuid()` is POSIX-only; the project's Windows sensor support
(`project_windows_frozen_build_gotchas` memory) means this code path WILL run on Windows.
**How to avoid:** Guard with `getattr(os, "geteuid", None)`; on Windows (no `geteuid`), the
privilege model is different (Administrator vs. non-elevated, checked via
`ctypes.windll.shell32.IsUserAnAdmin()` if precision is needed) — but nmap's raw-socket
requirement on Windows also differs (Npcap driver, not euid). Given D-02's scope and this phase's
stated boundary (no Windows-specific research requested in CONTEXT.md), the safe default is:
treat "cannot determine privilege" (Windows or any platform without `geteuid`) as **not
privileged** — this means the fallback-advisory always fires on Windows, which is honest (Windows
Administrator-without-Npcap-raw-socket-perms is a real degraded case too) rather than silently
assuming best-case.
**Warning signs:** Windows CI (`windows-sensor-smoke`, referenced in `project_windows_frozen_build_gotchas`
memory) failing on this new code path — confirms the guard is needed.

### Pitfall 3: A "down" host's `<host>` XML element still needs a `<status>` check, not just absence
**What goes wrong:** Assuming down hosts are simply missing from the XML (like
`parse_nmap_xml()`'s current filter-and-skip behavior does for anything not `state="up"`) and
therefore iterating only over "up" hosts silently drops the non-responsive ones from the pre-pass's
own accounting — recreating exactly the D-04 bug this phase exists to fix, just one layer
downstream (parser instead of orchestration).
**Why it happens:** `parse_nmap_xml()`'s existing code (`nmap_parser.py:32-35`) treats `status_el`
absence-or-non-"up" as a `continue` (skip entirely) because for the *sweep* use case, only live
hosts with open ports matter. The new `parse_nmap_host_status()` function must NOT reuse that
skip-if-not-up logic — it must return a row for every host nmap reports on, `up` boolean either way.
**How to avoid:** Write `parse_nmap_host_status()` as a genuinely separate function (Pattern 2
above), not a copy-paste of `parse_nmap_xml()` with the `continue` accidentally left in.
**Warning signs:** A test with a mix of up/down mocked-XML hosts where the down host doesn't appear
in the pre-pass's non-responsive count.

### Pitfall 4: Batches with zero survivors after the pre-pass
**What goes wrong:** If every host in a batch is liveness-skipped, `run_nmap_discovery()` gets
called with an empty `targets` list (or should be skipped entirely).
**Why it happens:** `run_nmap_discovery()` already handles `if not targets: return []` at its top
(confirmed, `nmap_provider.py` line ~74) — so calling it with an empty list is safe today, but it's
wasteful (spawns nmap for nothing) if the pre-pass filtering doesn't short-circuit first.
**How to avoid:** After building the responsive-hosts sublist, skip the `run_nmap_discovery()` call
entirely (`if not responsive_hosts: continue`) rather than relying on the callee's empty-list guard.
**Warning signs:** Extra nmap subprocess spawns visible in `-v` logger output for batches that
should have been entirely skipped.

## Code Examples

### Deterministic fallback-path test without real root (for automated coverage up to D-06's human gate)
```python
# Source: derived from live testing this session — nmap's own --unprivileged flag
# forces the exact connect()-fallback code path deterministically, without needing
# an actual non-root shell. Useful for an integration test that exercises the REAL
# nmap binary (not just a mocked subprocess) to prove the XML output is parseable
# and the liveness-skip logic behaves correctly under the fallback path — this is
# still not a substitute for D-06's human-run real-non-root verification (D-06 is
# explicit that the final confirmation must be a real non-root run), but it closes
# the gap between "fully mocked unit test" and "real non-root shell" with something
# that actually invokes the nmap binary.
subprocess.run([
    "nmap", "-sn", "-PS443", "--unprivileged", "-oX", xml_path, "127.0.0.1",
])
```

### Mocked-subprocess unit test pattern (matches `test_nmap_provider.py` existing style)
```python
# Source: pattern mirrors tests/test_nmap_provider.py's existing
# test_batch_failure_does_not_stop_subsequent_batches (fake callable, not mocked
# subprocess directly — this codebase's nmap tests favor a fake discover_fn over
# monkeypatching subprocess.run).
def test_liveness_skip_appends_liveness_skip_category():
    error_endpoints: List[CryptoEndpoint] = []

    def fake_liveness(batch):
        # host .2 is "down", others "up"
        return [
            NmapHostStatus(host=h, up=(h != "10.0.0.2"), reason="syn-ack")
            for h in batch
        ]

    responsive = []
    for status in fake_liveness(["10.0.0.1", "10.0.0.2", "10.0.0.3"]):
        if status.up:
            responsive.append(status.host)
        else:
            error_endpoints.append(CryptoEndpoint(
                host=status.host, port=0, protocol="ADVISORY",
                scan_error="liveness pre-pass: no response",
                scan_error_category="liveness_skip",
            ))

    assert responsive == ["10.0.0.1", "10.0.0.3"]
    assert len(error_endpoints) == 1
    assert error_endpoints[0].scan_error_category == "liveness_skip"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Full `-sT` sweep on every host in every batch (Phase 144) | `-sn -PS<ports>` liveness pre-pass filters batch before the `-sT` sweep | This phase (145) | Non-responsive hosts (dead IPs in a /22-sized batch, common in sparse enterprise subnets) skip the expensive per-port TCP-connect sweep entirely, cutting scan time in segmented networks without relying on unreliable ICMP |

**Deprecated/outdated:** N/A — no prior liveness-check code exists to deprecate; this is greenfield
within an established file.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Down hosts still produce a `<host>` element with `<status state="down">` in `-sn` XML output for explicitly-listed targets (not silently omitted) | Pattern 2 / Pitfall 3 | If nmap actually omits `<host>` elements for down targets in some versions, `parse_nmap_host_status()` would need to reconcile the *requested* target list against the *returned* host list to detect omissions — verify with a real down host during implementation (e.g. an unused RFC5737 TEST-NET address), not just localhost |
| A2 | Defaulting the pre-pass to `-PS-` (full 1-65535 range) for both `-p-` and `--top-ports 1000` override scopes is an acceptable D-03-consistent simplification | Pitfall 1 | If a `--top-ports 1000` scan is chosen specifically for pre-pass speed and a full-range `-PS-` probe erodes that speed benefit meaningfully, the planner/user may want a resolved top-1000 port list instead — flag for discuss-phase/planner confirmation |
| A3 | Treating "cannot determine privilege" (e.g. Windows, no `geteuid`) as "not privileged" (always emit fallback advisory) is the safer default than assuming privileged | Pitfall 2 | If this is wrong for the Windows sensor path specifically (Windows privilege model uses Npcap/Administrator, not euid, and could genuinely have raw-socket capability), the advisory could fire as a false-positive on every Windows scan; low severity (it's a disclosure, not a failure) but worth confirming scope with the user since CONTEXT.md D-02 only discusses POSIX `os.geteuid()` |

**All other claims in this research were verified via live nmap 7.991 testing on the dev machine
this session** (CLI flag behavior, XML shape, fallback-indistinguishability, `--unprivileged` test
flag) or cited directly from `man nmap`.

## Open Questions

1. **Should the liveness-skip advisory (D-01's CryptoEndpoint fallback row) fire once per scan or
   once per batch?**
   - What we know: D-02 says privilege is determined once, before the loop. D-01 says disclose it
     "the same way `_emit_missing_extra_advisory` already discloses" — that helper is called once
     per scan for a given missing extra, not per-batch.
   - What's unclear: Whether the planner should emit ONE fallback-advisory CryptoEndpoint row for
     the whole scan (simplest, matches D-02's "once per scan" framing) or one per batch (more
     granular but redundant given root/non-root doesn't change mid-scan).
   - Recommendation: Emit once per scan (mirrors `_emit_missing_extra_advisory`'s existing
     call-once-per-condition pattern exactly) — planner should write this as a single task, gated
     by the pre-computed `is_privileged` flag, executed right after that flag is computed and before
     the batch loop starts.

2. **Does `port_spec_override == "--top-ports 1000"` deserve a real resolved top-1000 port list
   for `-PS`, or is `-PS-` (full range) an acceptable simplification for v1?**
   - What we know: No `-PS`-native `--top-ports` equivalent exists (Pitfall 1). `-PS-` is a strict
     superset and never under-covers.
   - What's unclear: Whether the extra probe cost of `-PS-` vs. a "true" top-1000 probe is
     significant enough in practice to justify building a resolved port list (nmap ships a
     `nmap-services` frequency file that could be parsed, but that's meaningfully more
     implementation work for a corner case).
   - Recommendation: Ship `-PS-` for both wide-scope overrides in this phase (matches D-03's
     reliability-first framing, keeps the phase small); flag as a possible Phase 146+ optimization
     if wide-scope scan times regress noticeably.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| `nmap` binary | Both the existing `-sT` sweep and the new `-sn -PS` pre-pass | ✓ (dev machine) | 7.991 | Existing D-08 fallback (builtin discovery via `expand_targets()`) already covers nmap-absent; this phase adds no new fallback requirement since it only runs when `nmap_binary_available` is already True |
| Non-root shell for D-06 verification | Human-UAT final confirmation | Confirmed available (dev shell tested this session is non-root; `nmap -sS ...` errored as expected without `sudo`) | n/a | None needed — the dev machine itself satisfies D-06's non-root requirement |
| `os.geteuid()` | D-02 privilege check (POSIX) | ✓ macOS/Linux; ✗ Windows | stdlib | See Pitfall 2 — `getattr(os, "geteuid", None)` guard, treat missing as "not privileged" |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None new — existing D-08 nmap-absent fallback is unaffected
by this phase.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing repo standard) |
| Config file | `pyproject.toml` — `addopts = "-m 'not slow'"` (default run excludes `@slow`) |
| Quick run command | `pytest tests/test_nmap_provider.py -x` |
| Full suite command | `pytest` (repo default; excludes `@slow` unless `-m slow` explicitly added) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| DISC-03 (pre-pass runs before sweep) | Pre-pass filters batch hosts before `run_nmap_discovery()` call | unit (fake callable, mirrors existing style) | `pytest tests/test_nmap_provider.py::test_liveness_pass_filters_batch -x` | ❌ Wave 0 |
| DISC-03 (non-responsive hosts recorded, not dropped) | Liveness-skipped hosts produce `CryptoEndpoint(scan_error_category="liveness_skip")` rows | unit | `pytest tests/test_nmap_provider.py::test_liveness_skip_appends_liveness_skip_category -x` | ❌ Wave 0 |
| DISC-03 (privilege fallback detected+logged) | `os.geteuid()`-based check produces the D-01 advisory row when non-root | unit (monkeypatch `os.geteuid`) | `pytest tests/test_nmap_provider.py::test_fallback_advisory_emitted_when_non_root -x` | ❌ Wave 0 |
| DISC-03 (XML host-status parsing) | `parse_nmap_host_status()` correctly extracts up/down state incl. down hosts | unit (fixture XML, up+down hosts) | `pytest tests/test_nmap_parser.py::test_parse_host_status_up_and_down -x` | ❌ Wave 0 (new test file — no `test_nmap_parser.py` currently exists; parser has no dedicated test file today) |
| DISC-03 (non-root real-run verification) | Real non-root nmap invocation behaves as expected end-to-end | manual-only (D-06) | N/A — human-UAT chaos-lab walkthrough | manual gate, not automatable per D-06's explicit decision |

### Sampling Rate
- **Per task commit:** `pytest tests/test_nmap_provider.py tests/test_nmap_parser.py -x`
- **Per wave merge:** `pytest` (full suite, `not slow` default)
- **Phase gate:** Full suite green before `/gsd:verify-work`, plus D-06's human-UAT non-root pass
  signed off separately (cannot be gated by automated suite per D-06)

### Wave 0 Gaps
- [ ] `tests/test_nmap_parser.py` — does not exist today; needs creation to cover
      `parse_nmap_host_status()` (no prior parser-specific test file — existing coverage of
      `parse_nmap_xml()` lives inline in other test files or is implicitly covered via
      `test_nmap_provider.py`/integration tests; verify during planning which file currently
      exercises `parse_nmap_xml()` directly, if any, and decide whether to add to it or create new)
- [ ] Fixture XML files or inline XML strings for up/down host test cases (mirror the "fake
      callable" style already used in `test_nmap_provider.py` rather than requiring a live nmap
      binary in CI)
- [ ] `os.geteuid` monkeypatch pattern for the privilege-check unit test (stdlib `unittest.mock.patch`
      of `os.geteuid`, standard and low-risk)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|---------------------|
| V5 Input Validation | yes | Port-list string built for `-PS<ports>` must go through the SAME `_SAFE_NMAP_ARG_RE` allowlist validation `nmap_provider.py` already applies to `extra_args`/`port_spec_override` tokens (existing WR-04/WR-05 pattern) — do not build a second, weaker validation path for the liveness pre-pass's port argument |
| V6 Cryptography | no | Not applicable — no cryptographic operation in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| Argument injection via unvalidated port-list string into subprocess argv | Tampering | Reuse `_SAFE_NMAP_ARG_RE.fullmatch()` (already exists, `nmap_provider.py`) on any port-spec string built for `-PS<ports>` before appending to `args` — since `args` is a `subprocess.run(args, ...)` list (not shell=True), injection risk is already low, but the existing project pattern of allowlisting nmap-arg tokens should extend to this new code path for consistency and defense-in-depth (WR-05 precedent) |
| XXE via untrusted XML | Tampering / Info Disclosure | `parse_nmap_host_status()` MUST use `quirk.util.xml_safe.make_safe_parser()`, same as `parse_nmap_xml()` (WR-06) — the XML source is nmap's own local subprocess output (not attacker-controlled network input), but the project's existing invariant test (`tests/test_xml_safe.py::test_nmap_parser_blocks_xxe_lxml`) treats this as a hard chokepoint regardless of source trust level; the new parser function must not bypass it |

## Sources

### Primary (HIGH confidence)
- Live `nmap --version` / `nmap -sn -PS443 ...` / `nmap -sS -PS443 ...` / `nmap --unprivileged ...`
  test runs on the dev machine, this session (nmap 7.991, macOS/arm) — CLI behavior, XML shape,
  fallback-indistinguishability all directly observed, not assumed
- `man nmap` (local man page, nmap 7.991) — `-PS`, `-sn`, `--top-ports`, `--privileged`/
  `--unprivileged` flag semantics
- `quirk/discovery/nmap_provider.py` (repo source, read this session) — existing `-sT` args,
  `_SAFE_NMAP_ARG_RE`, `port_spec_override` handling, subprocess/XML plumbing
- `quirk/discovery/nmap_parser.py` (repo source, read this session) — existing
  `parse_nmap_xml()` host-status filtering behavior (the gap this phase must fill)
- `run_scan.py` lines 140-200, 1260-1340 (repo source, read this session) — `_emit_missing_extra_advisory`,
  Phase 144 batch loop, `error_endpoints.append(CryptoEndpoint(...))` precedent
- `quirk/models.py` (repo source, read this session) — `CryptoEndpoint` schema,
  `scan_error_category` column
- `tests/test_nmap_provider.py` (repo source, read this session) — existing test style/pattern for
  the batch loop (fake-callable, not mocked-subprocess)
- `.planning/phases/145-liveness-pre-pass/145-CONTEXT.md` — locked decisions D-01..D-06 (this
  research does not re-litigate any of them)

### Secondary (MEDIUM confidence)
None required — all claims were directly verifiable against live nmap output or repo source in
this session.

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all existing project patterns
- Architecture: HIGH — every pattern has a direct precedent in the same files, verified by reading
  the actual current source this session
- Pitfalls: HIGH — the two riskiest technical claims (silent SYN→connect fallback
  indistinguishability, and `-PS` vs `--top-ports` syntax mismatch) were both directly tested
  against a live nmap binary, not inferred from documentation alone

**Research date:** 2026-08-10
**Valid until:** 2026-09-09 (30 days — stable domain, nmap CLI behavior does not change quickly,
but re-verify if the project's nmap minimum version requirement changes)
