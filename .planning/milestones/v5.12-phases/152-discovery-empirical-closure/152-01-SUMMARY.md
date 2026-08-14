---
phase: 152-discovery-empirical-closure
plan: 01
subsystem: chaos-lab
tags: [chaos-lab, docker, iptables, networking, discovery]
dependency-graph:
  requires: []
  provides:
    - segmented-network chaos lab profile (segnet-gateway, segnet-live-tls, segnet-live-ssh, segnet-prober)
    - genuine RST/ICMP-unreachable dead-subnet lab environment for DISC-10
  affects:
    - quantum-chaos-enterprise-lab/docker-compose.yml
    - docs/chaos-lab.md
    - quantum-chaos-enterprise-lab/README.md
tech-stack:
  added:
    - alpine:3.20 + iptables (segnet-gateway base image)
  patterns:
    - Custom Docker bridge networks joined by an iptables-REJECT gateway container
    - In-container verification via `docker compose exec` (macOS Docker Desktop host-routing limitation)
key-files:
  created:
    - quantum-chaos-enterprise-lab/segmented-network/gateway/Dockerfile
    - quantum-chaos-enterprise-lab/segmented-network/gateway/entrypoint.sh
    - quantum-chaos-enterprise-lab/expected_results_segmented_network.md
  modified:
    - quantum-chaos-enterprise-lab/docker-compose.yml
    - docs/chaos-lab.md
    - quantum-chaos-enterprise-lab/README.md
decisions:
  - "Prober joins segnet-live only (not segnet-dead directly) and reaches the dead subnet via an explicit `ip route add ... via segnet-gateway` — direct dual-network membership bypasses the gateway's FORWARD chain entirely (confirmed via live smoke test)"
  - "IP forwarding is enabled via compose-level `sysctls: [net.ipv4.ip_forward=1]`, not the in-container `sysctl -w` call, which fails read-only on Docker Desktop/Engine bridge networking"
metrics:
  duration: "~50 minutes"
  completed: 2026-08-14
---

# Phase 152 Plan 01: segmented-network Chaos Lab Profile Summary

Built a new `segmented-network` chaos lab profile — two custom Docker bridge networks
(`segnet-live` with real reused TLS/SSH services, `segnet-dead` with no containers) joined
by an iptables-REJECT gateway container — verified live via Docker Desktop to produce
genuine TCP RST / ICMP-host-unreachable responses on the dead subnet, replacing the
unassigned-loopback-alias silence every other lab profile relies on.

## What Was Built

### Task 1: Gateway image + topology + 2-host smoke test

- `quantum-chaos-enterprise-lab/segmented-network/gateway/Dockerfile` — `FROM alpine:3.20`
  (CHAOS-05 pin reuse) + `apk add iptables`.
- `quantum-chaos-enterprise-lab/segmented-network/gateway/entrypoint.sh` — installs two
  `FORWARD`-chain REJECT rules scoped to the dead subnet CIDR (`tcp-reset` for TCP,
  `icmp-host-unreachable` for everything else), then idles.
- `docker-compose.yml`: added `segnet-gateway`, `segnet-live-tls`, `segnet-live-ssh`,
  `segnet-prober` services (`profiles: ["segmented-network"]`) plus new top-level
  `segnet-live` (10.70.0.0/24) and `segnet-dead` (10.71.0.0/24) bridge networks.
- Confirmed auto-discovery: `./lab.sh profiles` lists `segmented-network`.
- Confirmed clean parse: `docker compose --profile segmented-network config` exits 0.

**Live smoke test transcript (2026-08-14, real Docker Desktop run):**

Dead-subnet unassigned address (10.71.0.50), after the prober-routing fix (see Deviations):
```
$ docker compose exec segnet-prober nmap -sT -Pn -p 443 10.71.0.50
Nmap scan report for 10.71.0.50
Host is up (0.00010s latency).
PORT    STATE  SERVICE
443/tcp closed https
Nmap done: 1 IP address (1 host up) scanned in 0.08 seconds
```

Live-subnet TLS service (10.70.0.10):
```
$ docker compose exec segnet-prober nmap -sT -Pn -p 443 10.70.0.10
Nmap scan report for ...segnet-live-tls-1 (10.70.0.10)
Host is up (0.000064s latency).
PORT    STATE SERVICE
443/tcp open  https
```

### Task 2: Scale to representative dead range + second live service

- `segnet-live-ssh` (clones `hwcompat-ssh`'s image — `lscr.io/linuxserver/openssh-server:10.2_p1-r0-ls225`,
  container port 2222) added to the profile (done as part of the same Task 1 compose edit
  for efficiency; verification/documentation completed in Task 2).
- Added a comment on the `segnet-dead` network block documenting the representative range
  (`10.71.0.2/26`, 62 usable addresses) and quoting CONTEXT.md's "scaled reproduction of the
  original ~1024-host batch, not a 1:1 replica" framing verbatim.

**Full-range sweep transcript (2026-08-14):**
```
$ docker compose exec segnet-prober nmap -sT -Pn -p 443 10.71.0.0/26
...
Nmap done: 64 IP addresses (64 hosts up) scanned in 1.23 seconds
```
All 64 addresses in the swept `/26` returned `443/tcp closed https` — **100% RST-based,
0 filtered/silent.**

**Live-service probes:**
```
$ docker compose exec segnet-prober nmap -sT -Pn -p 443 10.70.0.10   # segnet-live-tls
443/tcp open  https

$ docker compose exec segnet-prober nmap -sT -Pn -p 2222 10.70.0.11  # segnet-live-ssh
2222/tcp open  EtherNetIP-1   # (nmap's generic port-number service guess; real service is OpenSSH)
```

**Container-count constraint confirmed:** `docker compose config --services | grep segnet`
returns exactly 4 services (`segnet-gateway`, `segnet-live-tls`, `segnet-live-ssh`,
`segnet-prober`) — no per-dead-host container was added to cover the 62-address range.

### Task 3: Documentation triad

- `docs/chaos-lab.md`: new `### 3.24 segmented-network Profile` section mirroring §3.23's
  skeleton, with a risk-note callout on the macOS host-routing limitation and the
  `docker compose exec segnet-prober` scan-command pattern.
- `quantum-chaos-enterprise-lab/README.md`: new Profile Summary table row, explicitly
  noting "none published" diverges from every other row's convention.
- `quantum-chaos-enterprise-lab/expected_results_segmented_network.md`: new oracle
  mirroring `expected_results_otics.md`'s structure, with the live-fire transcripts from
  this execution baked in as the authoritative expected results.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Prober joined to both `segnet-live` and `segnet-dead` bypassed the gateway's FORWARD chain**
- **Found during:** Task 1's mandated 2-host smoke test (exactly the check Pitfall 1 in
  152-RESEARCH.md called out as necessary before scaling).
- **Issue:** Both 152-RESEARCH.md's Pattern 4 diagram and this plan's Task 1 action text
  specified `segnet-prober` joined to BOTH `segnet-live` and `segnet-dead`. Live-fire
  testing showed this produces `443/tcp filtered` (silent timeout) on the dead subnet —
  the opposite of the required behavior — because a container that is itself a member of
  `segnet-dead` reaches unassigned addresses on that bridge via direct L2 delivery, never
  entering `segnet-gateway`'s `FORWARD` chain at all.
- **Fix:** `segnet-prober` now joins `segnet-live` only, with an explicit
  `ip route add 10.71.0.0/24 via 10.70.0.2` (the gateway's live-side IP) installed at
  container start (via a compose-level `command:` override, running as root +
  `cap_add: [NET_ADMIN]` to permit route installation and the `apt-get install
  iproute2` step, since `sensor.Dockerfile`'s base `python:3.11.12-slim` image ships
  without `iproute2`). This produces genuine routed traffic through the gateway's
  `FORWARD` chain, matching real-world "host on live segment reaches unreachable subnet
  through its router" behavior.
- **Files modified:** `quantum-chaos-enterprise-lab/docker-compose.yml`
- **Commit:** c4b97aa

**2. [Rule 1 - Bug] In-container `sysctl -w net.ipv4.ip_forward=1` fails read-only on Docker Desktop bridge networking**
- **Found during:** Task 1 first container start attempt.
- **Issue:** `sysctl -w net.ipv4.ip_forward=1` from inside `segnet-gateway` (even with
  `cap_add: [NET_ADMIN]`) failed with `Read-only file system` — `/proc/sys/net` is
  mounted read-only from inside a non-host-network bridge container on this Docker
  Desktop version.
- **Fix:** Added compose-level `sysctls: [net.ipv4.ip_forward=1]` to `segnet-gateway`,
  which Docker applies at container-creation time (permitted for non-host-network bridge
  containers). Kept the in-container `sysctl -w` attempt as a non-fatal defense-in-depth
  no-op (`|| echo ...`), with a hard failure only if `/proc/sys/net/ipv4/ip_forward` does
  not actually read back `1` after both attempts.
- **Files modified:** `quantum-chaos-enterprise-lab/docker-compose.yml`,
  `quantum-chaos-enterprise-lab/segmented-network/gateway/entrypoint.sh`
- **Commit:** c4b97aa

**3. [Rule 3 - Blocking] Docker IPAM race-assigned the prober the gateway's intended static IP**
- **Found during:** First `up` of the full 3-container smoke-test set — `segnet-gateway`
  failed to start with `Address already in use`.
- **Issue:** `segnet-prober` initially had no static IP on `segnet-live`; Docker's IPAM
  allocated it `10.70.0.2` (the first available address) before `segnet-gateway` started,
  colliding with the gateway's intended static `10.70.0.2`.
- **Fix:** Gave `segnet-prober` an explicit static IP (`10.70.0.20`, distinct from the
  gateway's `.2`).
- **Files modified:** `quantum-chaos-enterprise-lab/docker-compose.yml`
- **Commit:** c4b97aa

### Verify-command discrepancy (documented, not a defect)

Task 2's literal automated verify command, `grep -c "^  segnet-" quantum-chaos-enterprise-lab/docker-compose.yml`,
returns **6**, not the expected **4**. This is because the plan's own Task 1 interfaces
section specified the two new bridge networks be named `segnet-live` and `segnet-dead` —
both also match `^  segnet-` (2-space top-level indent) since they live under the
`networks:` block, which uses the same indentation convention as `services:`. The
authoritative check — `docker compose config --services | grep segnet` — confirms exactly
4 services (`segnet-gateway`, `segnet-live-tls`, `segnet-live-ssh`, `segnet-prober`), with
zero per-dead-host containers. No action needed; documented here and in
`expected_results_segmented_network.md`.

## Housekeeping Note

An early exploratory `docker compose down` (run without a `--profile` flag, before the
static-IP fix in Deviation 3) stopped and removed this repo's **default-profile**
containers (e.g. `tls-modern`) that happened to be running at session start. These are
ephemeral, stateless lab containers defined entirely by `docker-compose.yml` with no
persistent volumes — `./lab.sh up` (default profile) or `docker compose up -d
<service>` recreates them identically on demand. No code, data, or git state was affected.
All subsequent lifecycle operations in this plan used profile-scoped `up -d
<service...>`/`stop <service...>` rather than a bare `down`.

## Self-Check: PASSED

Verified files exist:
```
FOUND: quantum-chaos-enterprise-lab/segmented-network/gateway/Dockerfile
FOUND: quantum-chaos-enterprise-lab/segmented-network/gateway/entrypoint.sh
FOUND: quantum-chaos-enterprise-lab/expected_results_segmented_network.md
```

Verified commits exist:
```
FOUND: c4b97aa
FOUND: bc52ba0
FOUND: f97f9a6
```
