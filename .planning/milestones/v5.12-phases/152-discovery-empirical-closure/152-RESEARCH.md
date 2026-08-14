# Phase 152: Discovery Empirical Closure - Research

**Researched:** 2026-08-13
**Domain:** Docker Compose multi-subnet networking (iptables REJECT/ICMP), nmap adaptive
timing internals, CLI interactive-prompt defaults, chaos-lab documentation conventions
**Confidence:** MEDIUM-HIGH (codebase-verified for all existing patterns; MEDIUM on the
brand-new iptables/routing topology since there is no existing analog in this repo)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

## Implementation Decisions

### Segmented-Network Lab Profile Design
- Two-subnet routed topology: a "live" subnet with real services and a "dead" subnet behind a
  gateway container that REJECTs TCP (RST) and answers ICMP-unreachable for dead hosts, built via
  a custom Docker bridge + iptables rules — genuinely reproduces routed-segment RST/ICMP-unreachable
  behavior, unlike unassigned loopback aliases.
- Host count: a scaled-but-representative segment (~50-100 hosts) — enough to trigger nmap's
  adaptive RTT/timing engine without an impractical container count. Document explicitly as a
  scaled reproduction of the original ~1024-host batch, not a 1:1 replica.
- Profile name: `segmented-network` — matches `lab.sh`'s existing single-word profile naming
  convention (`tls-modern`, `otics`, etc.).
- Live-side services: reuse existing lab services (e.g. `tls-modern`, an ssh profile container) on
  the live subnet so discovery has real ports to find, rather than inventing new dummy services.

### Timing-Artifact Resolution Methodology
- "Reproduces" is defined strictly as the same failure mode as the original: real open ports on
  live hosts missed/suppressed by adaptive RTT/timing throttling during chunked discovery,
  confirmed by diffing chunked-discovery output against a direct nmap run of the same segment.
  Any other kind of missed port does not count as reproduction.
- The finding is written to a dedicated `152-DISC09-FINDING.md` in the phase directory, plus a
  cross-reference update in `.planning/STATE.md`'s deferred-items ledger and
  `.planning/milestones/v5.11-MILESTONE-AUDIT.md`'s tech-debt block — closing the loop explicitly
  rather than leaving it only in a phase-local file.
- Run the verification scenario at least 3 times before declaring closed or confirmed, to rule out
  timing-variance flakiness.
- Test environment is the Docker Compose chaos lab (today's oracle standard for this project) —
  Docker bridge networking + iptables REJECT genuinely produces RST/ICMP-unreachable behavior.
  Real hardware/VM testing is explicitly out of scope for this phase (the audit flagged it as
  ideal-but-not-required; Docker bridge networking is judged sufficient to settle the question).

### Mitigation Scope (conditional on reproduction)
- If the artifact reproduces: implement the timing-template/RTT-bound tuning already flagged as
  the known alternative in `nmap_provider.py`, scoped conservatively to the silent-batch detection
  heuristic — NOT a blanket global timing-engine change — to avoid the false-negative tradeoff on
  slow real networks that the v5.11 audit explicitly called out as a risk.
- If the artifact does NOT reproduce: close the deferred item outright with a written closure
  note; remove the override-acceptance framing from STATE.md/audit references since it is no
  longer an open risk, rather than leaving stale "accepted override" language in place.

### Interactive Default Flip Scope
- Flip `_prompt_bool("Run nmap port discovery first? (recommended for >10 hosts)",
  default=False)` in `quirk/interactive.py` (~line 176) to `default=True`. Preserve the existing
  single global toggle behavior (D-06, already locked: one global y/N prompt, NOT per-target) —
  this phase does not reopen that architecture decision.
- No prompt copy change — "(recommended for >10 hosts)" already exists and now matches the new
  default; no redundant wording to clean up.
- No UI-SPEC / `ui-phase` needed — this is a CLI prompt-default change, not a dashboard/GUI
  component. The phase's "UI hint" refers to the CLI interactive flow, not a web UI surface.
- Add or update an `interactive.py` unit test asserting the new `default=True` value directly, so
  a future edit can't silently flip it back without a test failure.

### Claude's Discretion
- Exact Docker Compose service/network naming inside the `segmented-network` profile (container
  names, subnet CIDRs, iptables rule specifics) — follow existing lab conventions, check
  `docker-compose.yml` for naming patterns before choosing.
- Exact diffing mechanism for comparing chunked-discovery output against a direct nmap run (script
  vs. manual comparison) — whichever produces the clearest evidence for `152-DISC09-FINDING.md`.
- Whether the RTT-bound tuning mitigation (if needed) lives in `nmap_provider.py` directly or as a
  new small helper — follow existing code organization in that file.

### Deferred Ideas (OUT OF SCOPE)

## Deferred Ideas

None — discussion stayed within phase scope. Real hardware/VM testing was explicitly considered
and deliberately deferred as out of scope for this phase (Docker bridge networking judged
sufficient), not deferred as a future phase idea.
</user_constraints>

## Summary

Phase 152 closes a single named open item from the v5.11 audit (`.planning/milestones/
v5.11-MILESTONE-AUDIT.md`, Phase 144 override) by building a new chaos-lab profile that can
actually reproduce real-world RST/ICMP-unreachable behavior, re-running the chunked-discovery
path against it, and writing a definitive finding. It also flips one boolean default in
`quirk/interactive.py`. There is no new pip/npm dependency — this phase is Docker Compose +
iptables + one Python default flip + docs/oracle updates.

The hard part is the lab topology, not the code. Today's `quantum-chaos-enterprise-lab/
docker-compose.yml` (the file `_derive_all_profiles()` parses for `lab.sh`'s auto-discovered
profile list) has **no `networks:` section at all** — every service sits on the single
implicit default bridge, and every profile is reached by the scanning host via a published
`host:container` port mapping to `127.0.0.1`. That pattern cannot produce "unreachable host"
behavior at all (there's nothing to be unreachable — you either published a port or you
didn't). The one existing multi-subnet analog in this repo, `docker-compose.distributed.yml`
(3 custom bridge networks, static IPs, Phase 106-112 MERGE-03), demonstrates the Compose
syntax for custom bridges/subnets/static IPs but does **not** use iptables and is not part of
the `ALL_PROFILES` auto-discovery system — it is a wholly separate `./lab.sh distributed`
subcommand with its own compose file. Neither existing pattern is a full analog for "REJECT
on a live subnet's gateway edge for a dead subnet's unassigned IPs."

The second load-bearing finding: **Docker Desktop for macOS cannot route host traffic
directly into a custom user-defined bridge network.** The developer machine for this project
is macOS (`uname -s == Darwin`, confirmed in `lab.sh`'s existing kerberos-skip logic). Every
existing lab profile sidesteps this by publishing ports to `127.0.0.1`. A profile whose entire
point is "traffic to unpublished/unassigned IPs on a routed segment" cannot be scanned from
the host at all on macOS — the scan must run from *inside* a container that is itself attached
to the lab's networks, exactly the pattern `docker-compose.distributed.yml` already uses
(`sensor.Dockerfile` + `docker compose exec ... python run_scan.py`, `cap_add: [NET_RAW]`).
Plan for a small idle "prober" container joined to the live+dead subnets, not a host-side
`python run_scan.py` invocation, and document that as the DISC-10 verification procedure.

**Primary recommendation:** Build `segmented-network` as two custom bridge networks in the
existing `docker-compose.yml` (so `_derive_all_profiles()` auto-discovers it — no `lab.sh`
edit needed), route the dead subnet through a small `iptables`-driven gateway container
(`cap_add: NET_ADMIN`), and drive DISC-10's actual nmap comparison from a `sensor.Dockerfile`
idle container joined to both networks rather than from the macOS host.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Segmented-network Docker topology (live/dead subnets + gateway) | Chaos Lab (Docker Compose) | — | Pure test-fixture infra; no application code |
| RST/ICMP-unreachable emulation | Gateway container (iptables) | Chaos Lab | Kernel-level packet handling, not QUIRK code |
| Chunked discovery / partial-result tolerance | `run_scan.py` (CLI/backend) | `quirk/discovery/nmap_provider.py` | Already-shipped Phase 144/145/146 code under test, not modified unless DISC-10 reproduces |
| Timing-artifact mitigation (conditional) | `quirk/discovery/nmap_provider.py` | — | Same module that already owns `discovery_timing_template_for_batch()` |
| Interactive default flip | CLI (`quirk/interactive.py`) | — | Single-file, single-line prompt default |
| Finding documentation | Docs/planning artifacts | — | `152-DISC09-FINDING.md`, STATE.md, v5.11-MILESTONE-AUDIT.md |

## Standard Stack

No new external packages. This phase uses only what's already installed/available:

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|---------------|
| Docker Compose | already in use (`quantum-chaos-enterprise-lab/`) | New `segmented-network` profile | Existing lab tooling — `[VERIFIED: codebase]` |
| `iptables` (inside a container) | Debian/Alpine-packaged, no pinned version needed | REJECT rules on the gateway container | Standard Linux netfilter tool; every mainstream minimal Linux base image can `apt-get install iptables` or `apk add iptables` — `[ASSUMED]` (not previously used in this repo, so no in-repo precedent to cite; verify base-image package availability at build time) |
| nmap | already a scan dependency (`quirk/discovery/nmap_provider.py`) | The subject under test | `[VERIFIED: codebase]` |
| `sensor.Dockerfile` (existing) | n/a — local build | Container base for the in-network prober | Reuse rather than invent a new Dockerfile — `[VERIFIED: codebase]`, `quantum-chaos-enterprise-lab/sensor.Dockerfile` |

No `pip install`, `npm install`, or new Python dependency is introduced by this phase. **Package
Legitimacy Audit is not applicable** — skip that section (no external packages installed).

## Package Legitimacy Audit

Not applicable. This phase installs no new pip/npm/cargo packages. The only new runtime
component (`iptables` inside a gateway container) is a Linux base-image package installed via
`apt-get`/`apk` inside a Dockerfile — not a QUIRK application dependency, and not something
`slopcheck`/`npm view`/`pip index` apply to. Verify only that the chosen base image (Debian
slim, Alpine, or reuse of an image already pinned elsewhere in `docker-compose.yml` per
CHAOS-05) actually ships or can install `iptables` before finalizing the plan's Dockerfile.

## Architecture Patterns

### System Architecture Diagram (segmented-network profile, target design)

```
                     ┌─────────────────────────────────────────┐
                     │   docker network: segnet-live            │
                     │   (e.g. 10.70.0.0/24)                     │
                     │                                            │
  prober container ──┼──> tls-modern (reused live service)        │
  (joins BOTH        │    ssh-* (reused live service)             │
   networks, runs     │                                            │
   nmap discovery     │    gateway container ─┐                    │
   from inside)        │   (static IP on live  │                   │
      │                │    subnet, forwards)  │                   │
      │                └────────────────────────┼───────────────────┘
      │                                          │
      │                     ip_forward=1         │  iptables REJECT
      │                     + iptables rules      │  (--reject-with
      │                                          │   tcp-reset / icmp-
      │                ┌─────────────────────────▼   host-unreachable)
      │                │   docker network: segnet-dead              │
      │                │   (e.g. 10.71.0.0/24 — routed via gateway) │
      │                │   NO live containers; every host in the    │
      │                │   /24 except the gateway's own IP is       │
      │                │   "dead" — gateway REJECTs on their behalf │
      └────────────────┴──────────────────────────────────────────┘

Data flow for DISC-10 verification:
  prober container --chunked discovery (run_scan.py)--> segnet-live hosts (find real open
  ports) + segnet-dead hosts (expect RST/ICMP-unreachable per host, NOT silence)
      --diff against--> prober container --direct nmap -sT/-sn (no chunking)--> same targets
      --> written comparison in 152-DISC09-FINDING.md
```

### Recommended Project Structure (additions only)

```
quantum-chaos-enterprise-lab/
├── docker-compose.yml            # add: segnet-live/segnet-dead networks + new services
├── segmented-network/            # new dir, mirrors otics-modbus/otics-bacnet build-dir convention
│   └── gateway/
│       ├── Dockerfile            # small base + iptables + ip_forward entrypoint
│       └── entrypoint.sh         # sets ip_forward, applies REJECT rules for the dead range
├── expected_results_segmented_network.md   # new oracle, mirrors expected_results_otics.md
└── lab.sh                        # NO edit needed for ALL_PROFILES (auto-derived) — verify
                                    # only, per the otics/hwcompat precedent comment already
                                    # in docs/chaos-lab.md §3.23
```

```
.planning/phases/152-discovery-empirical-closure/
└── 152-DISC09-FINDING.md   # new, per CONTEXT.md decision — dedicated finding doc
```

### Pattern 1: Auto-discovered profile registration (no `lab.sh` edit)
**What:** Any service in `docker-compose.yml` with `profiles: ["segmented-network"]` is
automatically picked up by `lab.sh`'s `_derive_all_profiles()` (parses the compose file via
`yq` or a `grep -oE '"[a-zA-Z0-9_-]+"'` fallback) — confirmed identical mechanism used for
`otics` (Phase 141) and `hwcompat` (Phase 127/133).
**When to use:** Always, for any new single-word profile name.
**Example (from the existing otics precedent, `docker-compose.yml:1381-1393`):**
```yaml
# Source: quantum-chaos-enterprise-lab/docker-compose.yml (otics-modbus/otics-bacnet)
otics-modbus:
  build: ./otics-modbus/
  profiles: ["otics"]
  ports:
    - "502:502"
```
The equivalent for this phase is `profiles: ["segmented-network"]` on every new
gateway/live/dead-adjacent service. **Do not add a manual `ALL_PROFILES` entry to `lab.sh`** —
the CONTEXT.md phrasing "listed in lab.sh's ALL_PROFILES" is satisfied automatically by this
dynamic-discovery mechanism; the actual planner task is to *verify* `./lab.sh profiles`
prints `segmented-network` after the compose edit, not to hand-edit an `ALL_PROFILES` array
(there is no static array to edit — see `lab.sh:245-271`).

### Pattern 2: Custom bridge network + static IP (existing analog, adapt for routing)
**What:** `docker-compose.distributed.yml` already demonstrates custom bridge networks with
pinned subnets and static container IPs.
**When to use:** As the syntactic base for `segnet-live`/`segnet-dead`; this phase's addition
on top is IP forwarding + iptables REJECT on the gateway, which the distributed file does NOT
have (it relies on network *isolation*, not REJECT emulation — MERGE-03's need was "can't
reach", not "reaches and gets rejected").
**Example:**
```yaml
# Source: quantum-chaos-enterprise-lab/docker-compose.distributed.yml:191-211
networks:
  segment-a:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: "10.10.0.0/24"
```

### Pattern 3: Gateway/router container with `cap_add: NET_ADMIN` + iptables REJECT
**What:** A container attached to both `segnet-live` and `segnet-dead`, with
`sysctl net.ipv4.ip_forward=1` and iptables rules that answer for the entire dead subnet
(minus its own gateway IP) with `--reject-with tcp-reset` (for TCP) and
`--reject-with icmp-host-unreachable` (for other traffic/ICMP).
**When to use:** This is genuinely new territory for this repo — no existing Dockerfile or
compose service does this. Base the Dockerfile on a small pinned image (Alpine or Debian
slim, matching CHAOS-05's pin-everything rule) with `iptables` installed, `cap_add: [NET_ADMIN]`
set in compose, and a small `entrypoint.sh` that applies the forwarding + REJECT rules then
idles (`tail -f /dev/null` or similar, matching the idle-container pattern already used by
`sensor-a`/`sensor-b` in `docker-compose.distributed.yml`).
**Illustrative shape (not verified against a live source — `[ASSUMED]`, standard netfilter
usage, not QUIRK-specific):**
```bash
#!/bin/sh
set -e
sysctl -w net.ipv4.ip_forward=1
# Reject anything destined for the dead subnet except the gateway's own dead-side IP.
iptables -A FORWARD -d 10.71.0.0/24 -p tcp -j REJECT --reject-with tcp-reset
iptables -A FORWARD -d 10.71.0.0/24 -j REJECT --reject-with icmp-host-unreachable
tail -f /dev/null
```
This needs live verification inside the lab — the exact rule ordering/chain (`FORWARD` vs.
`INPUT`, whether Docker's own iptables management on the host interferes with rules applied
*inside* a container's own network namespace) should be smoke-tested early in execution, not
assumed correct from research alone.

### Pattern 4: In-container scan execution (macOS host cannot reach custom bridges)
**What:** Reuse `quantum-chaos-enterprise-lab/sensor.Dockerfile` (already builds a `quirk`-
installed image with `cap_add: NET_RAW` support) for a "prober" service joined to both
`segnet-live` and `segnet-dead`. Drive DISC-10's actual nmap runs via `docker compose exec
prober python run_scan.py ...` (or the equivalent `quirk` CLI invocation), not from the
macOS host shell.
**When to use:** Always for this phase's DISC-10 verification step. Every other lab profile
in this repo scans via `127.0.0.1:<published-port>` from the host — that pattern is
structurally incompatible with "unreachable/unassigned IP on a routed segment," which by
definition has no port to publish.
**Example (existing idle-container + exec pattern):**
```yaml
# Source: quantum-chaos-enterprise-lab/docker-compose.distributed.yml:81-101
sensor-a:
  build:
    context: ..
    dockerfile: quantum-chaos-enterprise-lab/sensor.Dockerfile
  entrypoint: []
  command: ["tail", "-f", "/dev/null"]
  networks:
    - segment-a
    - console-net
  cap_add:
    - NET_RAW
```

### Anti-Patterns to Avoid
- **Assuming `127.0.0.1`-style host scanning works for this profile:** it structurally cannot
  — there is no host route into a custom bridge subnet on macOS Docker Desktop, and even on
  Linux CI runners, scanning "dead" unassigned IPs from the host still routes through the
  gateway correctly only if the host itself has a route to the dead subnet via the gateway's
  live-side IP, which requires either running the scan from inside a container on that network
  or manually adding a host route (`ip route add ... via ...`) — the in-container approach is
  simpler, portable across macOS/Linux, and matches the existing `sensor.Dockerfile` pattern.
- **Editing `lab.sh`'s `ALL_PROFILES`:** there is no static array — `_derive_all_profiles()`
  parses the compose file dynamically (see Pattern 1). A manual edit attempt would either be a
  no-op or (worse) introduce drift from the auto-derivation the rest of the lab depends on.
- **Rewriting `nmap_provider.py`'s adaptive timing engine wholesale:** explicitly out of scope
  per CONTEXT.md. If DISC-10 reproduces, the mitigation must be scoped to the
  silent-batch-detection heuristic only (see Common Pitfalls below for exactly what that
  heuristic is).
- **1:1 replicating the original ~1024-host batch:** CONTEXT.md explicitly calls for a scaled
  (~50-100 host) reproduction, documented as scaled, not a literal 1024-container lab (that
  would also collide with realistic CI resource limits).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TCP RST / ICMP-unreachable emulation | A custom Python/Scapy packet responder | Kernel `iptables REJECT` on a gateway container | REJECT is the exact real-world mechanism (routers/OS TCP stacks do this natively); a hand-rolled responder risks subtly wrong packet semantics that wouldn't actually validate the timing engine against *real* RST/ICMP-unreachable behavior — defeats the entire point of DISC-10 |
| Diffing chunked vs. direct nmap XML output | A bespoke XML-diff parser | Existing `quirk.discovery.nmap_parser.parse_nmap_xml`/`parse_nmap_host_status` (already imported by `nmap_provider.py`) plus a simple Python set-difference on discovered `(host, port)` tuples | The parsing/normalization logic already exists in this codebase; reuse it for the comparison script instead of re-parsing raw nmap XML by hand |

**Key insight:** Everything genuinely new in this phase (gateway REJECT rules, in-container
scan execution) is infrastructure a real network already provides for free — the goal is to
stop *simulating* absence (silent loopback aliases) and start using the real Linux networking
stack's actual behavior, which is also the cheapest and most trustworthy way to get it right.

## Common Pitfalls

### Pitfall 1: iptables rules applied inside a container may not affect Docker's own NAT/forwarding path as expected
**What goes wrong:** Docker manages its own iptables rules on the *host* for bridge networking
(DOCKER-USER chain, NAT masquerade, etc.). Rules applied *inside* a container's own network
namespace (via `cap_add: NET_ADMIN`) operate on that container's own netfilter tables, which is
a different scope from the host's Docker-managed iptables. This is a well-known source of
confusion when building router/gateway containers.
**Why it happens:** Two independent netfilter processing points exist — the Docker host's
tables (governs whether packets reach the container's namespace at all) and the gateway
container's own tables (governs packets it forwards between its own two attached interfaces).
**How to avoid:** For a gateway container attached to two Docker networks, `FORWARD` chain
rules *inside that container* control traffic being routed between the container's own two
NICs (one per attached network) — this is the correct and sufficient scope for this use case,
since the "dead" subnet traffic must pass through the gateway container to reach any other
network. Verify this holds with a live smoke test early (send a probe from the prober
container to a dead-subnet IP and confirm RST/ICMP-unreachable arrives) before building the
full ~50-100-host topology.
**Warning signs:** Probes to the dead subnet time out (silence) instead of returning
RST/ICMP-unreachable — indicates the REJECT rule isn't in the packet's actual path, likely
because IP forwarding wasn't enabled, or the destination route doesn't actually traverse the
gateway container.

### Pitfall 2: macOS Docker Desktop cannot reach custom bridge networks from the host
**What goes wrong:** A plan or task written as `python run_scan.py --target 10.71.0.0/24`
(run directly from a macOS terminal) will simply fail to route anywhere — not even to a
"REJECT" response — because the packets never leave the Docker Desktop VM's internal network.
**Why it happens:** Docker Desktop for macOS runs containers inside a lightweight Linux VM;
only published `host:container` ports are exposed to the macOS host network stack. Custom
bridge network IPs are only reachable from other containers, or from processes running inside
the VM.
**How to avoid:** Run the DISC-9/DISC-10 verification nmap commands via `docker compose exec
<prober-service> ...` (see Architecture Pattern 4), not directly from the host shell. Document
this explicitly in `expected_results_segmented_network.md` and `docs/chaos-lab.md`'s new
section, since every other profile's "Scan command" is written for host execution and a reader
copy-pasting the usual `python run_scan.py --target 127.0.0.1 ...` pattern here will silently
get nothing.
**Warning signs:** All hosts (both live and dead) come back as unreachable/timeout when run
from the host shell — this is a host-routing failure, not evidence about the timing engine,
and must not be mistaken for a DISC-10 finding.

### Pitfall 3: A silent-batch false positive/negative in the "reproduces" determination
**What goes wrong:** Declaring the artifact "reproduced" or "closed" off a single noisy run.
**Why it happens:** nmap's adaptive RTT/timing engine is explicitly probabilistic/timing-
sensitive by design — a single run's result may not be representative.
**How to avoid:** CONTEXT.md already locks this down: run the verification scenario **at least
3 times** before declaring closed or confirmed. Build this into the plan as an explicit,
repeatable script/task, not a one-off manual command, so the 3 runs are actually comparable
(same target set, same batch size, same nmap args each time).
**Warning signs:** Only one run's XML output exists in the evidence trail for
`152-DISC09-FINDING.md`.

### Pitfall 4: Conflating "reproduces" with any missed port
**What goes wrong:** Treating an unrelated discovery gap (e.g., a port genuinely closed, or a
host genuinely down for a mundane reason) as evidence the timing artifact reproduced.
**Why it happens:** CONTEXT.md's strict definition — "real open ports on live hosts
missed/suppressed by adaptive RTT/timing throttling during chunked discovery, confirmed by
diffing chunked-discovery output against a direct nmap run of the same segment" — is easy to
loosely apply if the diff isn't automated/precise.
**How to avoid:** Build the comparison as target-set-aware: only count a discrepancy where (a)
the host is on the *live* subnet (dead-subnet non-findings are expected/correct), and (b) a
direct, non-chunked nmap run against that same host finds the port open while the chunked run
does not.
**Warning signs:** The finding lumps dead-subnet "no open ports" results in with the
comparison as if they were suppressions.

### Pitfall 5: If mitigation is needed, scope creep into the global timing template
**What goes wrong:** `discovery_timing_template_for_batch()` (`nmap_provider.py:103-125`)
currently selects `-T4` vs `-T3` purely by batch size (`_DISCOVERY_T4_MAX_BATCH_SIZE = 256`).
A naive "fix" would change this function's behavior for *all* batches, not just
mostly-silent ones — exactly the blanket change CONTEXT.md rules out.
**Why it happens:** This is the only existing lever in the file that controls nmap timing
aggressiveness; it's tempting to just tighten it globally.
**How to avoid:** If DISC-10 reproduces, the CONTEXT.md-locked scope is a **silent-batch
detection heuristic** — i.e., a new, narrower signal (e.g., detecting that a batch's liveness
pre-pass — Phase 145's `run_nmap_liveness_check` — reported an overwhelming majority of hosts
down) that *conditionally* selects a more conservative timing template or reduces
`--max-parallelism`/adds `--min-rtt-timeout`-style tuning **only for that batch**, leaving the
existing `_DISCOVERY_T4_MAX_BATCH_SIZE`-based default path untouched for normal (non-silent)
batches. `run_nmap_liveness_check`'s existing up/down counting (`nmap_provider.py:276-279`,
`up_count`/`down_count`) is the natural signal source — it's already computed and logged.
**Warning signs:** A plan task that edits `_default_nmap_args()` or
`discovery_timing_template_for_batch()`'s general-case branch rather than adding a new
conditional path keyed off liveness-pre-pass silence ratio.

## Code Examples

### Existing chunked discovery loop (verification target — read, do not modify unless DISC-10 reproduces)
```python
# Source: run_scan.py:1464-1537 (Phase 144/145/146, current shipped code)
for batch in _chunked(host_iter, _MAX_HOSTS_PER_CIDR):
    batch_num += 1
    _batch_timeout = discovery_timeout_for_batch(len(batch))
    _batch_timing_template = discovery_timing_template_for_batch(len(batch))
    # ... liveness pre-pass (Phase 145) narrows `batch` to `sweep_targets` ...
    _batch_extra_args = list(extra_args.split()) if extra_args else []
    _batch_extra_args.append(_batch_timing_template)
    batch_open_ports = run_nmap_discovery(
        targets=sweep_targets, ports=ports, output_dir=output_dir,
        extra_args=_batch_extra_args, timeout_seconds=_batch_timeout,
    )
```

### Existing liveness pre-pass up/down counting (candidate signal source for a scoped mitigation)
```python
# Source: quirk/discovery/nmap_provider.py:276-279
if logger:
    up_count = sum(1 for h in host_statuses if h.up)
    down_count = len(host_statuses) - up_count
    logger.stamp(f"Nmap liveness pre-pass: {up_count} up, {down_count} down.")
```

### Interactive prompt to flip (exact current code)
```python
# Source: quirk/interactive.py:175-179 (current, to be changed default=False -> default=True)
# --- 1b. Nmap discovery toggle (D-06: one global y/N, NOT per-target) ---
enable_nmap = _prompt_bool(
    "Run nmap port discovery first? (recommended for >10 hosts)",
    default=False,
)  # D-06: single global toggle, NOT per-target
```

### `_prompt_bool` implementation (for writing the new default-value unit test)
```python
# Source: quirk/interactive.py:99-106
def _prompt_bool(text: str, default: bool) -> bool:
    d = "Y" if default else "N"
    raw = _prompt(f"{text} (y/n)", d).lower()
    if raw in ("y", "yes"):
        return True
    if raw in ("n", "no"):
        return False
    return default
```
A minimal, robust test asserts the literal `default=True` at the `enable_nmap` call site (the
existing `test_interactive_validate_routes.py` file already uses this exact static-source-
inspection style for a related D-13 assertion — `'setattr(cfg.connectors, "enable_nmap"'` not
in `src`) — mirror that pattern rather than driving the full `interactive_config()` input
sequence, since the latter is already covered extensively by `test_interactive_mode.py` and
adding a full new input-sequence test there is unnecessary for a single default-value check.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Chaos lab profiles model "unreachable" via unassigned loopback aliases (127.0.0.x with no listener) | `segmented-network` profile models it via genuine routed-subnet RST/ICMP-unreachable (iptables REJECT on a gateway) | This phase (152) | First lab profile whose entire purpose is *negative* host behavior fidelity, not positive service fingerprinting |
| Interactive setup defaults nmap discovery to off (`default=False`) | Defaults to on (`default=True`) | This phase (152) | Users accepting all interactive-setup defaults now exercise the Phase 144/145 chunked-discovery + liveness path automatically |

**Deprecated/outdated:** None — no existing behavior is removed by this phase unless DISC-10
reproduces and a scoped mitigation lands in `nmap_provider.py`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A minimal Linux base image (Alpine/Debian slim) can install `iptables` via its package manager inside a Docker build, and `cap_add: NET_ADMIN` is sufficient (no `--privileged`) to apply `FORWARD`-chain REJECT rules inside that container's own namespace | Architecture Pattern 3 | If wrong, the gateway container needs `--privileged` (a much larger blast-radius change for a project with CHAOS-05 pinning discipline) or a different mechanism (e.g., a userspace proxy that fabricates RST/ICMP itself) — would require re-scoping the whole profile design |
| A2 | Docker Desktop for macOS's VM-based networking model (no direct host route into custom bridge networks) still holds as of the current Docker Desktop version in use on this machine | Common Pitfall 2 | If Docker Desktop's networking model has changed (e.g., via a beta host-networking feature), the in-container prober workaround may be unnecessary complexity — but it remains strictly safer/more-portable (works identically on Linux CI) even if unnecessary on this specific machine, so low risk either way |
| A3 | ~50-100 containers on a single Docker Compose profile is a practical, CI-safe scale (won't blow resource limits on `ubuntu-latest` GitHub Actions runners or the developer's local Docker Desktop) | Segmented-Network Lab Profile Design (CONTEXT.md, carried into this research) | If wrong, either the host count needs reducing further or the profile needs to be excluded from `./lab.sh all`/CI-driven paths and documented as local-only/manual verification |

## Open Questions

1. **Does the "Linux Full Suite" CI job (`ubuntu-latest`, `.github/workflows/python-ci.yml`)
   need to exercise this profile, or is DISC-9/DISC-10 verification purely local/manual?**
   - What we know: No existing workflow spins up `docker compose up` for any chaos-lab profile
     today — `linux-full-suite` runs `pytest -q -m ""` against unit/integration tests only, not
     live Docker Compose lab profiles.
   - What's unclear: Whether the planner should add a genuinely new CI job that starts the
     `segmented-network` profile and asserts something automatically, vs. treating DISC-10's
     empirical determination as a one-time, human-executed, and hand-written finding (matching
     the "at least 3 times" wording in CONTEXT.md, which reads as manual verification rounds).
   - Recommendation: Treat DISC-10 as a manual/local verification producing a written finding
     (matches CONTEXT.md's phrasing and the existing precedent of `152-DISC09-FINDING.md` as a
     hand-authored artifact); do not gate CI on it. Revisit only if the planner decides an
     automated regression guard is separately valuable.

2. **Exact base image and REJECT-rule syntax for the gateway container.**
   - What we know: `iptables -A FORWARD -d <dead-subnet-cidr> -p tcp -j REJECT --reject-with
     tcp-reset` and an analogous `icmp-host-unreachable` rule are standard netfilter syntax.
   - What's unclear: Whether Docker Desktop's own bridge-network implementation on macOS
     requires any additional `iptables -t nat` masquerade consideration for a container-internal
     gateway pattern like this (untested in this repo).
   - Recommendation: Smoke-test the minimal 2-service (gateway + one dead-subnet-adjacent probe)
     topology first, before building out the full ~50-100-host scale, exactly as Pitfall 1
     recommends.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| Docker Compose | Building/running the new profile | ✓ (existing lab infra) | — (already in use project-wide) | — |
| `iptables` package inside gateway container | REJECT rule emulation | Not yet verified — new Dockerfile | — | If unavailable in the chosen base image, switch base image (Debian slim ships `iptables` via apt; Alpine via `apk add iptables`) |
| macOS Docker Desktop host routing into custom bridges | N/A — explicitly NOT relied upon (see Pitfall 2) | ✗ by design | — | In-container prober (`sensor.Dockerfile` pattern) — no host-side fallback needed since the workaround is already the primary plan |

**Missing dependencies with no fallback:** None — `iptables` has a documented install fallback
across base images, and the macOS-routing limitation has a fully worked-out fallback (Pattern 4).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (`[tool.pytest.ini_options]`, `pyproject.toml:151-157`) |
| Config file | `pyproject.toml` (`addopts = "-m 'not slow'"` — default run skips `@slow`) |
| Quick run command | `pytest tests/test_interactive_mode.py tests/test_interactive_validate_routes.py -x -q` |
| Full suite command | `pytest -q -m ""` (matches `linux-full-suite` CI job) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| DISC-09 | `segmented-network` profile exists, `lab.sh profiles` lists it, produces real RST/ICMP-unreachable | manual/infra (Docker Compose live-fire) — not pytest-automatable | `./lab.sh profiles \| grep segmented-network` then live smoke test via prober container | ❌ Wave 0 (new lab dir + compose edit) |
| DISC-10 | Written finding on whether the Phase 144 artifact reproduces | manual, documentation-producing task | N/A (produces `152-DISC09-FINDING.md`, not a pass/fail test) | ❌ Wave 0 (new finding doc) |
| DISC-11 | `enable_nmap` prompt defaults to `True` | unit | `pytest tests/test_interactive_validate_routes.py -x -q` (add new assertion here, mirroring the existing static-source-check style at lines 85-89) | ❌ Wave 0 (new test function; file itself exists) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_interactive_validate_routes.py tests/test_interactive_mode.py -x -q`
- **Per wave merge:** `pytest -q -m ""` (full suite — DISC-09/DISC-10 lab work has no pytest
  surface, so the full suite here is really validating DISC-11's one-line change plus no
  regressions elsewhere)
- **Phase gate:** Full suite green before `/gsd:verify-work`; DISC-09/DISC-10 gated by the
  written finding document + at least 3 live verification runs (CONTEXT.md), not by pytest.

### Wave 0 Gaps
- [ ] New unit test in `tests/test_interactive_validate_routes.py` asserting
      `default=True` at the `enable_nmap` prompt call site (static-source-check style,
      matching the file's existing pattern at lines 79-89).
- [ ] `quantum-chaos-enterprise-lab/expected_results_segmented_network.md` — new oracle file
      (no existing file to gate on; this is a Wave 0 deliverable, not a pre-existing gap).
- [ ] `.planning/phases/152-discovery-empirical-closure/152-DISC09-FINDING.md` — new,
      dedicated finding document per CONTEXT.md's locked decision.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|-----------------|---------|--------------------|
| V2 Authentication | No | No auth surface touched by this phase |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | No | No new user-controllable input path (the gateway/iptables rules are static, lab-only config, not driven by scan input) |
| V6 Cryptography | No | N/A |

### Known Threat Patterns for this phase's stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| `cap_add: NET_ADMIN` on the gateway container broadens container capability beyond the lab's existing norms (every other lab service runs with default/no added capabilities except `sensor.Dockerfile`'s `NET_RAW`) | Elevation of Privilege | Scope `NET_ADMIN` to only the new gateway container, not the whole compose file; this is a local dev/test-only chaos lab (never deployed, gitignored certs elsewhere in the same lab already establish this posture) — document the capability addition inline in the compose file comment block, mirroring the existing `cap_add NET_RAW is required for nmap...` comment style at `docker-compose.distributed.yml:79` |
| A misconfigured REJECT rule accidentally blocks legitimate live-subnet traffic (self-inflicted DoS within the lab) | Denial of Service (lab-scope only, not production) | Smoke-test the minimal topology first (Open Question 2 / Pitfall 1) before scaling to ~50-100 hosts |

This phase does not touch any QUIRK application-facing security surface (no new endpoint, no
new auth, no new user input path) — the above is scoped to the chaos-lab test fixture only.

## Project Constraints (from CLAUDE.md)

- **Chaos Lab Maintenance (hard rule):** Any new Docker Compose profile requires `lab.sh`'s
  `ALL_PROFILES` set to include it, `docs/chaos-lab.md` new section, `README.md` row, and an
  `expected_results_*.md` oracle — **all in the same change**. Per Pattern 1 above,
  `ALL_PROFILES` is satisfied automatically by `_derive_all_profiles()` for any service tagged
  `profiles: ["segmented-network"]` — no hand-edit needed, but the planner must still include a
  verification step (`./lab.sh profiles` output check) to prove compliance, and the other three
  artifacts (`docs/chaos-lab.md`, `README.md`, `expected_results_segmented_network.md`) DO need
  hand-authored content in this phase.
- **PEP 8 / minimal diffs:** Applies to the `nmap_provider.py` mitigation, if DISC-10
  reproduces and a scoped fix is needed.
- **`python -m compileall` + relevant tests after changes:** Standard post-change verification
  for the `quirk/interactive.py` edit and any conditional `nmap_provider.py` mitigation.
- **`labs/*/expected_results.md` update if detection logic changes:** Not applicable unless
  DISC-10 reproduces and a mitigation changes nmap discovery/timing behavior — in that case,
  any existing oracle whose expected findings depend on discovery timing (unlikely, since
  timing affects *whether* ports are found, not fixed content values) should be spot-checked.
- **Obsidian sync + UAT-SERIES.md update (Mandatory Phase Completion Steps):** Applies
  post-execution, not to research/planning — flagging here so the planner's final wave includes
  these steps (phase note creation, UAT-SERIES.md update+sync, per the standing CLAUDE.md
  checklist).
- **STATE.md Deferred Items ledger cross-reference (CONTEXT.md-locked, reinforces CLAUDE.md's
  spirit of not leaving stale docs):** DISC-10's finding must update both `.planning/STATE.md`'s
  Deferred Items table and `.planning/milestones/v5.11-MILESTONE-AUDIT.md`'s Phase 144
  tech-debt block, not just the phase-local finding doc.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|--------------|----------------------|
| DISC-09 | A segmented-network chaos lab profile exists so chunked discovery and partial-result tolerance can be exercised against realistic unreachable hosts rather than unassigned loopback aliases (deferred from v5.11) | Architecture Patterns 1-4 (auto-discovered profile, custom bridges, gateway/iptables REJECT, in-container prober); Common Pitfalls 1-2 (netfilter scope, macOS host-routing limitation); Environment Availability table |
| DISC-10 | The Phase 144 nmap timing-engine artifact is settled empirically against DISC-09's profile — either it does not reproduce (finding closed), or it does and a scoped mitigation is chosen with its false-negative tradeoffs documented | Code Examples (chunked discovery loop, liveness up/down counting); Common Pitfalls 3-5 (repeat-run discipline, strict reproduction definition, scoped-not-global mitigation); Don't Hand-Roll (reuse existing nmap XML parsing for the diff); Open Questions 1-2 |
| DISC-11 | Interactive setup opts users into nmap discovery by default — the current `default=False` on "Run nmap port discovery first?" silently routes users past the entire v5.11 chunked-discovery and liveness path | Code Examples (exact current prompt code + `_prompt_bool` implementation + existing static-source-check test pattern to mirror) |
</phase_requirements>

## Sources

### Primary (HIGH confidence — direct codebase reads, this session)
- `quirk/discovery/nmap_provider.py` (full file read) — adaptive timing engine, liveness
  pre-pass, `discovery_timing_template_for_batch()`, `discovery_timeout_for_batch()`
- `quirk/interactive.py:150-200` — exact `enable_nmap` prompt call site and `_prompt_bool`
- `run_scan.py:1391-1598` (chunked discovery batch loop, grep + read via prior context)
- `quantum-chaos-enterprise-lab/docker-compose.yml` (full grep of all `profiles:`/service
  blocks, plus full read of `hwcompat-snmp`/`otics-modbus`/`otics-bacnet` sections)
- `quantum-chaos-enterprise-lab/docker-compose.distributed.yml` (full file read) — only
  existing multi-subnet/custom-bridge analog in this repo
- `quantum-chaos-enterprise-lab/lab.sh` (grep of `_derive_all_profiles`, `all` command, usage
  block, `distributed` subcommand)
- `docs/chaos-lab.md:768-834` (§3.23 otics profile) — documentation template followed
- `quantum-chaos-enterprise-lab/expected_results_otics.md` (full read) — oracle-file template
- `quantum-chaos-enterprise-lab/README.md:82-83` — profile-table row template
- `.planning/milestones/v5.11-MILESTONE-AUDIT.md` (grepped nmap/timing/144/override sections) —
  the original incident writeup and its exact framing of the open question
- `.planning/REQUIREMENTS.md` (DISC-09/10/11 exact text)
- `.planning/STATE.md` (Deferred Items ledger, v5.11/v5.12 phase maps)
- `tests/test_interactive_validate_routes.py` — existing static-source-check test pattern
- `tests/test_interactive_mode.py` — existing full-input-sequence test pattern (used to decide
  NOT to extend it for this single-value change)
- `.github/workflows/python-ci.yml` — confirmed no CI job runs live chaos-lab Docker Compose
  profiles; `linux-full-suite` runs on `ubuntu-latest`, `pytest -q -m ""`
- `pyproject.toml:151-157` — pytest config (`addopts = "-m 'not slow'"`)

### Secondary (MEDIUM confidence)
- None — no WebSearch/WebFetch was needed; this phase's domain (this repo's own conventions,
  standard Linux netfilter REJECT semantics, Docker Desktop macOS networking limitations) is
  fully covered by direct codebase inspection plus well-established, uncontroversial
  networking-fundamentals knowledge.

### Tertiary (LOW confidence)
- The exact iptables rule syntax/chain scoping (Architecture Pattern 3, Assumption A1) is
  standard netfilter usage from training knowledge, not verified against a live container in
  this session — flagged in the Assumptions Log and Open Question 2 for early smoke-testing
  during execution.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; every existing tool/pattern cited is
  codebase-verified in this session.
- Architecture: MEDIUM-HIGH — the auto-discovery/documentation patterns (Patterns 1, 4) are
  HIGH confidence (direct codebase precedent); the gateway/iptables REJECT design (Patterns 2,
  3) is MEDIUM — sound standard networking practice but genuinely new to this repo, no existing
  in-repo REJECT/NET_ADMIN precedent to point to, so it needs an early smoke test during
  execution rather than blind trust in this research.
- Pitfalls: HIGH — the macOS Docker Desktop host-routing limitation and the netfilter
  scope-confusion pitfall are both well-documented, uncontroversial facts about how Docker
  networking and Linux netfilter work, cross-checked against this repo's own existing
  `sensor.Dockerfile`/`docker-compose.distributed.yml` workaround pattern for a structurally
  similar problem (MERGE-03's cross-segment scanning).

**Research date:** 2026-08-13
**Valid until:** 30 days (stable domain — no external library/API surface to go stale; the
only decay risk is if Docker Desktop's networking model changes, which research flags as
Assumption A2)
