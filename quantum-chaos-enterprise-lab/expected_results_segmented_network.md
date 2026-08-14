# Expected Scanner Results — segmented-network Oracle

**Profile:** `segmented-network`
**Phase:** 152 — Discovery Empirical Closure (DISC-09/DISC-10)
**Requirement:** DISC-09 (chaos-lab profile produces genuine RST/ICMP-unreachable behavior
on a routed dead subnet) / DISC-10 (empirical settlement of the Phase 144 nmap
timing-engine artifact)
**Status:** Authoritative oracle for Phase 152 `segmented-network` chaos lab validation.

This profile replaces the unassigned-loopback-alias approach every other chaos-lab profile
uses with a *realistic routed-segment* environment: a "live" subnet with real reused
services and a "dead" subnet whose gateway REJECTs all traffic to unassigned addresses,
producing genuine TCP RST / ICMP host-unreachable responses instead of silent timeouts.

## macOS Host-Routing Caveat

**macOS Docker Desktop cannot route host traffic into custom bridge networks.** Every
command below MUST run via `docker compose exec segnet-prober ...` — never `python
run_scan.py --target ... ` from the host shell, and never a bare `nmap` invocation from the
macOS terminal. `segnet-prober` is an idle in-lab container (`sensor.Dockerfile`) that is
the only vantage point from which `segnet-live`/`segnet-dead` are reachable at all. This
constraint holds identically on Linux hosts (the in-container pattern works there too), so
there is no host-OS branch to reason about — always use `docker compose exec`.

## How to Run

```bash
PROFILE_ARGS="--profile segmented-network" ./lab.sh up
```

---

## Services

| Service | Host Port | Container Port | Network / IP | Purpose |
|---------|-----------|-----------------|----------------|---------|
| segnet-gateway | none | — | segnet-live 10.70.0.2, segnet-dead 10.71.0.2 | Routes segnet-live ↔ segnet-dead; iptables `FORWARD`-chain REJECT for the entire dead subnet |
| segnet-live-tls | none | 443 | segnet-live 10.70.0.10 | Real nginx TLS 1.3 service (clones `tls-modern`'s image/config) |
| segnet-live-ssh | none | 2222 | segnet-live 10.70.0.11 | Real OpenSSH service (clones `hwcompat-ssh`'s image/config) |
| segnet-prober | none | — | segnet-live 10.70.0.20 (segnet-dead unreachable except via routing through segnet-gateway) | In-lab idle container (`sensor.Dockerfile`) driving all verification |

No host ports are published for this profile — every service is reachable only from
`segnet-prober` (or `segnet-gateway`) inside the lab network.

---

## Scan Command

```bash
# Live-subnet services (real open ports)
docker compose exec segnet-prober nmap -sT -Pn -p 443 10.70.0.10
docker compose exec segnet-prober nmap -sT -Pn -p 2222 10.70.0.11

# Dead-range sweep (representative slice, not the full /24)
docker compose exec segnet-prober nmap -sT -Pn -p 443 10.71.0.0/26
```

Run these exclusively via `docker compose exec segnet-prober ...` per the macOS caveat above.

**Note on transcript dates:** the three "Live-fire verification" timestamps below read
`2026-08-14`, one day after the phase's commit dates (`2026-08-13`, e.g. `b84d927`).
This is a UTC-vs-local timezone artifact, not a stale/copy-pasted transcript: the
verification tooling (`compare_discovery.py`, in-container `nmap` runs) timestamps in
UTC, and the phase's local commits were authored in the evening US Eastern (`-04:00`),
which rolls over to the next UTC calendar day (confirmed live during the WR-01/WR-02
code-review fix pass — a `compare_discovery.py` re-run at `2026-08-13 22:xx -04:00`
local produced `run_timestamp_utc: "20260814-..."`).

---

## segnet-live-tls — 10.70.0.10:443/TCP (nginx, TLS 1.3)

**Expected result:** `open`

**Live-fire verification (Phase 152 execution, 2026-08-14):**
```
Nmap scan report for quantum-chaos-enterprise-lab-segnet-live-tls-1... (10.70.0.10)
Host is up (0.000064s latency).
PORT    STATE SERVICE
443/tcp open  https
```

---

## segnet-live-ssh — 10.70.0.11:2222/TCP (OpenSSH)

**Expected result:** `open`

**Live-fire verification (Phase 152 execution, 2026-08-14):**
```
Nmap scan report for quantum-chaos-enterprise-lab-segnet-live-ssh-1... (10.70.0.11)
Host is up (0.000072s latency).
PORT     STATE SERVICE
2222/tcp open  EtherNetIP-1
```
(nmap's default service-name guess for 2222/tcp is `EtherNetIP-1` — a generic port-number
heuristic, not a protocol misdetection; `-sV` would correctly identify the real OpenSSH
banner if a service-version probe were added.)

---

## Dead-Range Sweep — 10.71.0.0/26 (segnet-dead)

**Representative range:** `10.71.0.0/26` (a 62-usable-address slice of the segnet-dead
`/24`) — a **scaled reproduction of the original ~1024-host batch, not a 1:1 replica**,
per `152-CONTEXT.md`'s "Segmented-Network Lab Profile Design" decision.
`segnet-gateway`'s REJECT rule covers the entire `/24` CIDR, so no per-dead-host
container is required to exercise this at scale.

**IMPORTANT — gateway self-address caveat:** `10.71.0.2` is `segnet-gateway`'s own IP on
the `segnet-dead` network. A probe to `.2` is answered by the gateway container's own
`INPUT` chain (an ordinary kernel "no listener" TCP RST), **not** the `FORWARD`-chain
`REJECT` rule this lab exists to verify. `compare_discovery.py`'s automated sweep
excludes `.2` (WR-01, `152-REVIEW.md`), scanning 61 addresses that are genuinely
REJECT-rule-verified. The raw-nmap live-fire transcript below swept the full `/26` CIDR
(64 addresses, unfiltered) and is annotated accordingly: 63/64 results are REJECT-rule
RST, and 1/64 (`10.71.0.2`) is gateway-self INPUT-chain RST.

**Expected result:** every non-gateway address in the sweep reports `closed` (fast,
RST-based) — **zero** `filtered`/silent-timeout results.

**Live-fire verification (Phase 152 execution, 2026-08-14):** swept the full `10.71.0.0/26`
range (64 addresses, including the `.0` network / `.63` broadcast addresses and the
gateway's own `.2`):
```
Nmap done: 64 IP addresses (64 hosts up) scanned in 1.23 seconds
```
All 64 addresses returned `443/tcp closed https` — but only 63/64 of those `closed`
results are attributable to the `iptables REJECT` rule under test; the `10.71.0.2` result
is the gateway's own kernel "no listener" RST via its `INPUT` chain, not the `FORWARD`
chain `REJECT`. **63/64 (98.4%) REJECT-rule-verified, 0 filtered/silent.** A
representative single-host smoke test (`10.71.0.50`) confirmed sub-100ms response time
(`Host is up (0.00010s latency)` / scanned in `0.08 seconds`), consistent with a real
iptables REJECT rather than a connection timeout.

---

## Architecture Notes

`segnet-gateway` (`alpine:3.20` + `iptables`, `cap_add: [NET_ADMIN]`, never
`--privileged`) enables IP forwarding via compose's `sysctls: [net.ipv4.ip_forward=1]`
(the in-container `sysctl -w` fallback fails with "Read-only file system" on Docker
Desktop/Engine bridge networking — expected, not a bug) and installs two `FORWARD`-chain
rules scoped to the dead subnet CIDR:

```bash
iptables -A FORWARD -d 10.71.0.0/24 -p tcp -j REJECT --reject-with tcp-reset
iptables -A FORWARD -d 10.71.0.0/24 -j REJECT --reject-with icmp-host-unreachable
```

**`segnet-prober` deliberately joins only `segnet-live`**, not `segnet-dead`. A live
smoke test during Phase 152 execution confirmed that a container which is itself a
*member* of `segnet-dead` reaches unassigned dead-subnet addresses via direct L2 bridge
delivery — bypassing `segnet-gateway`'s `FORWARD` chain entirely and producing `filtered`
(silence), not the expected RST. `segnet-prober` instead reaches the dead subnet via an
explicit route installed at container start: `ip route add 10.71.0.0/24 via 10.70.0.2`
(the gateway's live-side IP) — genuine routed traffic through the gateway's `FORWARD`
chain, matching how a real host on a live network segment reaches an unreachable subnet
through its router.

## Container-Count Constraint

This profile adds exactly 4 new services regardless of the dead-range size being tested:
`segnet-gateway`, `segnet-live-tls`, `segnet-live-ssh`, `segnet-prober` (verified via
`docker compose config --services | grep segnet`). The REJECT rule covers the whole CIDR,
so scaling the dead-range sweep from 2 hosts (Task 1 smoke test) to 64 addresses (Task 2
full sweep) required zero additional containers — satisfying the "without an impractical
container count" constraint from `152-CONTEXT.md`.
