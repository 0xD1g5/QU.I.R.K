# Phase 152: Discovery Empirical Closure - Pattern Map

**Mapped:** 2026-08-13
**Files analyzed:** 9 (create/modify) + 2 doc-sync artifacts
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------------------------------------------------------------|------------|------------------|----------------------------------------------------------------------|----------------|
| `quantum-chaos-enterprise-lab/docker-compose.yml` (add `segmented-network` services block) | config (compose service definitions) | event-driven (network topology, no request/response code) | `quantum-chaos-enterprise-lab/docker-compose.yml` otics-modbus/otics-bacnet block (lines 1364-1400) + `docker-compose.distributed.yml` (custom bridge/static-IP networks) | role-match (profile registration exact; network topology partial — no in-repo REJECT precedent) |
| `quantum-chaos-enterprise-lab/segmented-network/gateway/Dockerfile` | config (container image build) | event-driven | `quantum-chaos-enterprise-lab/sensor.Dockerfile` | role-match (Dockerfile conventions: pinned base, apt-get pattern, comment style) — no REJECT/iptables precedent |
| `quantum-chaos-enterprise-lab/segmented-network/gateway/entrypoint.sh` | utility (network init script) | event-driven | none (net-new capability; no existing entrypoint.sh in this repo for a routing/iptables role) | no analog — see "No Analog Found" |
| `quantum-chaos-enterprise-lab/lab.sh` (verification-only touch, likely no diff) | utility (CLI shell script) | CRUD (profile lifecycle: up/down/status) | `quantum-chaos-enterprise-lab/lab.sh` itself — `_derive_all_profiles()` (lines 168-180) + `all` command (lines 237-280) | exact (same file, no new code needed — verify only) |
| `quantum-chaos-enterprise-lab/expected_results_segmented_network.md` | test (oracle/expected-results doc) | CRUD (documents expected scan output per host/port) | `quantum-chaos-enterprise-lab/expected_results_otics.md` | exact (template structure directly reusable) |
| `docs/chaos-lab.md` (new §3.24 section) | config/docs (profile documentation) | request-response (doc describing start/scan commands) | `docs/chaos-lab.md` §3.23 otics Profile (lines 768-834) | exact |
| `quantum-chaos-enterprise-lab/README.md` (Profile Summary table row) | config/docs (table row) | CRUD | `quantum-chaos-enterprise-lab/README.md` otics row (line 83) | exact |
| `quirk/interactive.py` (flip `default=False` → `default=True` at `enable_nmap` prompt) | utility (CLI prompt logic) | request-response (interactive stdin prompt) | `quirk/interactive.py` itself — `enable_nmap` call site (lines 175-179) + `_prompt_bool` (lines 99-106) | exact (same file, one-line diff) |
| `tests/test_interactive_validate_routes.py` (new/updated test asserting `default=True`) | test (static-source-check unit test) | request-response (asserts source string, not live I/O) | `tests/test_interactive_validate_routes.py` `test_interactive_py_no_setattr_enable_nmap` (lines 85-89) and `test_connectors_cfg_has_enable_nmap_field` (lines 79-82) | exact |
| `.planning/phases/152-discovery-empirical-closure/152-DISC09-FINDING.md` | test (finding/evidence doc, not code) | batch (aggregates 3 verification runs into a written determination) | no direct in-repo analog file, but the CONTEXT.md-cited precedent — `.planning/milestones/v5.11-MILESTONE-AUDIT.md`'s Phase 144 override writeup (tech_debt block, lines 69-72) — is the closest prose precedent for framing | role-match |
| `.planning/STATE.md` (Deferred Items ledger update) | config/docs (planning ledger) | CRUD (update existing row / add resolution note) | `.planning/STATE.md` existing "RESOLVED (...)" bullet pattern (lines 287-288) | exact |
| `.planning/milestones/v5.11-MILESTONE-AUDIT.md` (tech_debt block update) | config/docs (audit ledger) | CRUD | `.planning/milestones/v5.11-MILESTONE-AUDIT.md` tech_debt block (lines 69-81, 251-261) | exact |

## Pattern Assignments

### `quantum-chaos-enterprise-lab/docker-compose.yml` (config, event-driven — new `segmented-network` services)

**Analogs:** `docker-compose.yml` lines 1364-1400 (profile registration pattern) + `docker-compose.distributed.yml` (full file, custom bridge/static-IP pattern)

**Profile registration pattern** (`docker-compose.yml:1364-1400`):
```yaml
# =========================
# PHASE 141 / OTICS-04 — OTICS PROFILE (profile: otics)
# ...
# lab.sh ALL_PROFILES needs NO edit — _derive_all_profiles discovers this
# profile dynamically by parsing docker-compose.yml at runtime.
# =========================
  otics-modbus:
    build: ./otics-modbus/
    profiles: ["otics"]
    ports:
      - "502:502"
```
Apply the same shape: every new service in the segmented-network block gets `profiles:
["segmented-network"]`. No `lab.sh` `ALL_PROFILES` edit needed — confirmed by
`_derive_all_profiles()` at `lab.sh:168-180` (parses `profiles:` keys dynamically via `yq` or
a `grep -oE '"[a-zA-Z0-9_-]+"'` fallback).

**Custom bridge network + static IP pattern** (`docker-compose.distributed.yml:36-65, 191-211`):
```yaml
  tls-target-a:
    image: nginx:1.28.0
    ...
    networks:
      segment-a:
        ipv4_address: "10.10.0.10"
        aliases:
          - crypto.internal
...
networks:
  segment-a:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: "10.10.0.0/24"
```
Apply this for `segnet-live` (e.g. `10.70.0.0/24`) and `segnet-dead` (e.g. `10.71.0.0/24`) —
static IPs for the gateway container on both subnets, reused live-side services (`tls-modern`
or similar) getting static/dynamic IPs on `segnet-live` only. This compose file has **no
`networks:` section at all today** — the new block is fully additive, does not touch existing
service definitions.

**Idle-container / build-context pattern for the gateway and prober** (`docker-compose.distributed.yml:81-101`):
```yaml
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
The gateway container needs an analogous shape but with `cap_add: [NET_ADMIN]` (not `NET_RAW`)
and its own local `build: ./segmented-network/gateway/` context (not `sensor.Dockerfile`,
since its job is routing/REJECT, not scanning). The prober container should reuse
`sensor.Dockerfile` directly (context `..`, `dockerfile: quantum-chaos-enterprise-lab/
sensor.Dockerfile`) joined to both `segnet-live` and `segnet-dead`, idling via `tail -f
/dev/null` and driven by `docker compose exec`.

---

### `quantum-chaos-enterprise-lab/segmented-network/gateway/Dockerfile` (config, event-driven)

**Analog:** `quantum-chaos-enterprise-lab/sensor.Dockerfile` (full file)

**Structure/comment-header pattern to mirror:**
```dockerfile
# QU.I.R.K. — Sensor / Console container image for the distributed chaos lab
# ...
# Base image: python:3.11.12-slim (patch-pinned per CHAOS-05 policy).
FROM python:3.11.12-slim

# System dependencies:
#   * nmap            — required by TLS/SSH scanners
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        nmap \
        curl \
        ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
```
Adapt: swap `nmap`/`curl` for `iptables` (`apt-get install -y --no-install-recommends
iptables`), keep the pinned-base-image comment convention (CHAOS-05), keep the apt-get
clean/rm pattern. Unlike `sensor.Dockerfile`, this container does not run as the `quirk`
non-root user for its core function — routing/iptables rules on the container's own `FORWARD`
chain need `cap_add: [NET_ADMIN]` at the compose level (see Common Pitfall 1 in RESEARCH.md);
document that capability grant inline exactly as `docker-compose.distributed.yml:79`'s
`cap_add NET_RAW is required for nmap...` comment does for its own elevated capability.

---

### `quantum-chaos-enterprise-lab/segmented-network/gateway/entrypoint.sh` (utility, event-driven)

**No direct analog** — this repo has no existing entrypoint script that does IP forwarding /
iptables rule application. Illustrative shape from RESEARCH.md (netfilter-standard, not
QUIRK-specific, needs live smoke-test per Pitfall 1):
```bash
#!/bin/sh
set -e
sysctl -w net.ipv4.ip_forward=1
iptables -A FORWARD -d 10.71.0.0/24 -p tcp -j REJECT --reject-with tcp-reset
iptables -A FORWARD -d 10.71.0.0/24 -j REJECT --reject-with icmp-host-unreachable
tail -f /dev/null
```
Style precedent for shell scripts in this lab (set -e, minimal comments, idle-tail pattern) is
`lab.sh` itself (`set -euo pipefail` at file top) and the `command: ["tail", "-f",
"/dev/null"]` idle pattern already used by `sensor-a`/`sensor-b`/`console` (adapted here to a
plain shell `tail -f /dev/null` since this is a custom entrypoint, not a compose `command:`
override).

---

### `quantum-chaos-enterprise-lab/expected_results_segmented_network.md` (test, CRUD)

**Analog:** `quantum-chaos-enterprise-lab/expected_results_otics.md` (full file, 178 lines)

**Structure to mirror (section order):** title/profile/phase/requirement/status header →
"How to Run" → "Services" table → "Scan Command" (called out with the macOS host-routing
caveat per Pitfall 2 — NOT the usual `python run_scan.py --target 127.0.0.1` pattern, must use
`docker compose exec <prober> ...`) → per-target expected-result tables → "Image Notes" table
→ "Architecture Note".

```markdown
# Expected Scanner Results — otics Oracle

**Profile:** `otics`
**Phase:** 141 — OT/ICS Fingerprinting (Modbus + BACnet)
**Requirement:** OTICS-04 (chaos-lab profile validates both scanners end-to-end)
**Status:** Authoritative oracle for Phase 141 `otics` chaos lab validation.
...
## Scan Command

```bash
python run_scan.py --target 127.0.0.1 --enable-modbus --enable-bacnet
```
```
For `segmented-network`, the "Scan Command" section must instead read (per Pitfall 2, no
host-shell fallback exists):
```bash
docker compose exec segnet-prober python run_scan.py --target <segnet-live-cidr>,<segnet-dead-cidr> --enable-nmap ...
```
and the "Image Notes" table row for the gateway lists `NET_ADMIN` capability the way otics
lists `CHAOS-05 Compliant`.

---

### `docs/chaos-lab.md` (new §3.24, config/docs, request-response)

**Analog:** `docs/chaos-lab.md` §3.23 "otics Profile" (lines 768-834)

**Section skeleton to mirror:**
```markdown
### 3.23 otics Profile (v5.10 — Phase 141 OTICS-04)

The `otics` profile (D-09: ...) ships two **deliberately fragile** simulators ...

> **Prerequisites:** ...
> **Risk note:** ...

| Host Port | Service | Protocol | Purpose | Expected Finding |
|-----------|---------|----------|---------|-------------------|
| 502 | otics-modbus | Modbus/TCP | ... | ... |

**Start:**
```bash
PROFILE_ARGS="--profile otics" ./lab.sh up
```

**Scan command:**
```bash
python run_scan.py --target 127.0.0.1 --enable-modbus --enable-bacnet
```

**Simulator architecture.** ...
**Expected scanner findings:** ...
> **Lab note:** `lab.sh` requires no `ALL_PROFILES` edit for this profile — `_derive_all_profiles()` discovers `otics` dynamically ...

See: `quantum-chaos-enterprise-lab/expected_results_otics.md`
```
New §3.24 "segmented-network Profile" follows this exact skeleton, but the "Scan command" block
must be replaced with the `docker compose exec`-based invocation (Pitfall 2), and a new
callout block (mirroring the `> **Risk note:**` style) must explain the macOS host-routing
limitation and the "why in-container, not host shell" rationale, plus the "scaled reproduction,
not 1:1 replica" framing from CONTEXT.md.

---

### `quantum-chaos-enterprise-lab/README.md` (config/docs, CRUD)

**Analog:** README.md Profile Summary table, otics row (line 83)

```markdown
| Profile | Services / What it ships | Published Ports | Expected Findings | Notes |
|---------|---------------------------|-------------------|----------------------|-------|
| otics | otics-modbus, otics-bacnet | 502, 47808/udp | [Expected Findings](expected_results_otics.md) | v5.10 (Phase 141, OTICS-04); ... |
```
New row: `| segmented-network | segnet-gateway, segnet-prober, reused live-side services | none published (in-container access only) | [Expected Findings](expected_results_segmented_network.md) | v5.12 (Phase 152, DISC-09/DISC-10); scaled routed-segment RST/ICMP-unreachable topology — scan via `docker compose exec`, not host `127.0.0.1` (macOS Docker Desktop cannot route into custom bridges). |`
Note the "Published Ports" column value diverges from every other row (which all show
`host:container` mappings) — this is the one profile with none, and that itself is worth a
short inline note per the Notes-column convention already used for other profiles' caveats.

---

### `quirk/interactive.py` (utility, request-response — one-line default flip)

**Analog:** same file, exact call site (lines 175-179)

**Current code (to change):**
```python
# --- 1b. Nmap discovery toggle (D-06: one global y/N, NOT per-target) ---
enable_nmap = _prompt_bool(
    "Run nmap port discovery first? (recommended for >10 hosts)",
    default=False,
)  # D-06: single global toggle, NOT per-target
```
Change only `default=False` → `default=True`. No other line changes (CONTEXT.md: no prompt
copy change, preserve D-06 single global toggle).

**`_prompt_bool` implementation** (lines 99-106, unchanged, referenced for the new test):
```python
def _prompt_bool(text: str, default: bool) -> bool:
    d = "Y" if default else "N"
    raw = _prompt(f"{text} (y/n)", d).lower()
    if raw in ("y", "yes"):
        return True
    if raw in ("n", "no"):
        return False
    return default
```

---

### `tests/test_interactive_validate_routes.py` (test, request-response — new/updated assertion)

**Analog:** same file, existing static-source-check tests (lines 76-89)

```python
# D-13 (WR-12) — ConnectorsCfg.enable_nmap declared field
def test_connectors_cfg_has_enable_nmap_field():
    ...
    assert cfg.enable_nmap is False


def test_interactive_py_no_setattr_enable_nmap():
    """Static check: setattr-enable_nmap injection removed from interactive.py."""
    ...
    assert 'setattr(cfg.connectors, "enable_nmap"' not in src
    assert "setattr(cfg.connectors, 'enable_nmap'" not in src
```
Mirror this exact static-source-inspection style for DISC-11: read `quirk/interactive.py`
source text and assert the `enable_nmap = _prompt_bool(` call site is followed by
`default=True` (e.g. a regex or substring check on the source slice around that call), rather
than driving the full `interactive_config()` input sequence (that broader style already lives
in `tests/test_interactive_mode.py` and is unnecessary for a single default-value check per
RESEARCH.md's explicit recommendation).

---

## Shared Patterns

### Chaos-lab profile auto-discovery (no `lab.sh` hand-edit)
**Source:** `quantum-chaos-enterprise-lab/lab.sh:168-180` (`_derive_all_profiles()`)
**Apply to:** `docker-compose.yml`'s new segmented-network services block
```bash
_derive_all_profiles() {
  if command -v yq >/dev/null 2>&1; then
    yq eval '.. | select(has("profiles")) | .profiles[]' "${COMPOSE_FILE}" 2>/dev/null | sort -u
  else
    grep -E '^[[:space:]]*profiles:[[:space:]]*\[' "${COMPOSE_FILE}" \
      | grep -oE '"[a-zA-Z0-9_-]+"' | tr -d '"' | sort -u
  fi
}
```
Every new service just needs `profiles: ["segmented-network"]` — verify via `./lab.sh
profiles | grep segmented-network`, do not hand-edit an `ALL_PROFILES` array (none exists).

### In-container scan execution (macOS Docker Desktop cannot route host → custom bridge)
**Source:** `quantum-chaos-enterprise-lab/docker-compose.distributed.yml:81-101` (idle
`sensor-a`/`sensor-b` + `docker compose exec` e2e pattern), `sensor.Dockerfile` (full file)
**Apply to:** the new `segnet-prober` service and every DISC-10 verification command
documented in `expected_results_segmented_network.md` / `docs/chaos-lab.md` §3.24. Every
other lab profile's "Scan command" is written for host-shell execution against
`127.0.0.1:<published-port>`; this profile must not follow that convention — it structurally
cannot, since there is no port to publish for unassigned/dead-subnet IPs.

### CHAOS-05 image pinning
**Source:** `quantum-chaos-enterprise-lab/lab.sh:182-219` (`_validate_pinned_tags()`), enforced
on every `up`/`all` invocation
**Apply to:** any `image:` key added to the new services (none expected — both gateway and
prober are local builds, which the pin-policy gate exempts, matching otics-modbus/
otics-bacnet's `build:`-only precedent at `docker-compose.yml:1381-1399`). If a base image tag
is pinned in a Dockerfile `FROM` line (gateway Dockerfile), match the `python:3.11.12-slim` /
`python:3.12-slim` patch-pinned convention already used by `sensor.Dockerfile` and
`otics-modbus`/`otics-bacnet`.

### Three-artifact doc-sync requirement (CLAUDE.md Chaos Lab Maintenance)
**Source:** `docs/chaos-lab.md` §3.23, `quantum-chaos-enterprise-lab/README.md` line 83,
`quantum-chaos-enterprise-lab/expected_results_otics.md` (all three landed together in Phase
141 per the otics precedent)
**Apply to:** `docs/chaos-lab.md` (new §3.24), `README.md` (new Profile Summary row),
`expected_results_segmented_network.md` — all three required in the same change per CLAUDE.md,
plus the Obsidian sync of `docs/chaos-lab.md` → `20_Dev-Work/QUIRK/Guides/Chaos-Lab.md`
(project CLAUDE.md, LIVE-03 sync table).

### Deferred-item ledger closure pattern
**Source:** `.planning/STATE.md` lines 287-288 (existing "RESOLVED (Plan N, date): ..." bullet
style), `.planning/milestones/v5.11-MILESTONE-AUDIT.md` tech_debt block lines 69-81, 251-261
**Apply to:** `152-DISC09-FINDING.md`'s cross-references — write a parallel "RESOLVED" or
"STILL OPEN, re-scoped" bullet in STATE.md's Deferred Items area (note: the Phase 144 timing
artifact itself is NOT currently a row in STATE.md's Deferred Items table — it lives only in
the v5.11-MILESTONE-AUDIT.md tech_debt block; DISC-09 IS referenced there at line 80 as "the
same capability that would close the Phase 144 nmap timing item"). Update the
v5.11-MILESTONE-AUDIT.md tech_debt entries at lines 69-72 and 251-261 directly, converting them
from "OPEN (needs real hardware)" to either a closure note or a scoped-mitigation note per
CONTEXT.md's two-branch outcome.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `quantum-chaos-enterprise-lab/segmented-network/gateway/entrypoint.sh` | utility | event-driven | No existing entrypoint script in this repo performs IP forwarding / iptables rule application — this is the first genuinely new networking-primitive capability added to the lab (RESEARCH.md Architecture Pattern 3, Assumption A1). Use the illustrative shape in RESEARCH.md as a starting point and smoke-test early (Pitfall 1) rather than trusting an in-repo precedent, since none exists. |
| `.planning/phases/152-discovery-empirical-closure/152-DISC09-FINDING.md` | test/finding doc | batch | No prior phase in this repo has produced a dedicated `*-FINDING.md` artifact of this exact shape (multi-run empirical determination write-up); closest prose precedent is the tech_debt block prose in `v5.11-MILESTONE-AUDIT.md`, but that is a summary table entry, not a source template — author from CONTEXT.md's own definition of "reproduces" plus the 3-run discipline requirement. |

## Metadata

**Analog search scope:** `quantum-chaos-enterprise-lab/` (docker-compose.yml,
docker-compose.distributed.yml, lab.sh, sensor.Dockerfile, README.md,
expected_results_otics.md), `docs/chaos-lab.md`, `quirk/interactive.py`,
`tests/test_interactive_validate_routes.py`, `.planning/STATE.md`,
`.planning/milestones/v5.11-MILESTONE-AUDIT.md`
**Files scanned:** 11 read directly (full or targeted ranges), plus grep sweeps over
`docker-compose.yml`, `lab.sh`, `README.md`, `docs/chaos-lab.md`, `STATE.md`,
`v5.11-MILESTONE-AUDIT.md`
**Pattern extraction date:** 2026-08-13
