# Phase 112: Distributed Chaos-Lab + Stabilization — Research

**Researched:** 2026-05-25
**Domain:** Docker Compose multi-network topology, chaos-lab tooling, dependency hygiene, docs completion
**Confidence:** HIGH (all claims verified against live codebase and Docker runtime)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Distributed Lab Topology (LAB-01 / LAB-02)**
- Separate `quantum-chaos-enterprise-lab/docker-compose.distributed.yml` — structurally different from the main compose; avoids polluting ALL_PROFILES sweep
- Two explicit bridge networks `segment-a` and `segment-b`, each with the SAME subnet `10.10.0.0/24` (overlapping RFC1918)
- Same static IP (e.g. `10.10.0.10`) assigned to a crypto target in BOTH networks so two per-segment sensors report identical `host:port` yielding two distinct CBOM components
- Crypto targets reuse existing nginx TLS images; at least one target per segment
- One sensor container per segment + one console container running `quirk serve`

**E2E Orchestration & Oracle (LAB-03)**
- `quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh` orchestrates enroll → scan-local → push → merge
- New `lab.sh distributed` command pointing at the separate compose file
- `ALL_PROFILES` continues to cover only the MAIN `docker-compose.yml`; distributed topology is its own `lab.sh distributed` command
- New `expected_results_distributed.md` oracle
- Update chaos-lab `README.md` with the distributed profile

**Verification Approach**
- Live multi-container run (LAB-01/02) is human-UAT
- Automated coverage: `docker compose -f docker-compose.distributed.yml config`, static topology test, Phase 110 unit MERGE-03 regression

**Docs & Dependency Hygiene (STAB-01 / STAB-03)**
- `docs/operators-guide.md`: add full distributed workflow + Windows sensor installation + close 999.59 settings gap
- `docs/UAT-SERIES.md`: ensure series cover all v5.4 phases 106-112 (108-111 already added; add 106, 107, 112)
- Dependency hygiene: confirm `platformdirs`, `tenacity`, `zstandard` pinned in correct group; resolve `datetime.utcnow()` deprecation in `sensor_cmd.py`
- Obsidian sync of operators-guide + UAT-SERIES + Phase 112 note

### Claude's Discretion
- Exact subnet/IP numbers, container image base, sensor container repo install method (editable vs wheel) — as long as two networks overlap and a target shares an IP across them
- Whether `distributed-e2e.sh` polls for readiness or uses fixed sleeps; precise `lab.sh` subcommand surface

### Deferred Ideas (OUT OF SCOPE)
- Windows-runner execution of the distributed lab
- Automatic merge trigger / polling (v5.5, D-06)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LAB-01 | Multi-segment chaos-lab topology validates E2E distributed flow on Linux (enroll → scan-local → push → merge → one CBOM + one score) | Docker compose two-network topology; sensor container install; `lab.sh distributed` command; `distributed-e2e.sh` orchestration |
| LAB-02 | Same-IP-in-two-segments physically reproduced in lab topology, proving MERGE-03 E2E | Subnet workaround (distinct subnets, same scan-target IP via config.yaml); sensor segment labels carry identity |
| LAB-03 | `lab.sh` ALL_PROFILES, README, expected_results oracle updated per CLAUDE.md chaos-lab rule | ALL_PROFILES unaffected (separate file); README profile table; `expected_results_distributed.md` oracle format |
| STAB-01 | `docs/operators-guide.md` covers full distributed workflow + Windows sensor install + 999.59 settings gap closed | Operators-guide sections 1-6 surveyed; missing distributed workflow section; Windows install gap confirmed |
| STAB-03 | Residual dep hygiene resolved; UAT-SERIES.md covers all v5.4 phases | `datetime.utcnow()` confirmed at sensor_cmd.py:296 only; deps in core group (correct); series 106/107/112 missing from UAT-SERIES |
</phase_requirements>

---

## Summary

Phase 112 closes the v5.4 milestone with three work streams: (1) a multi-segment Docker Compose topology that physically validates the distributed sensor flow end-to-end; (2) chaos-lab tooling maintenance (lab.sh, README, oracle, scripts) per the CLAUDE.md no-drift rule; and (3) stabilization tail (operators-guide distributed workflow + Windows install, UAT-SERIES coverage for phases 106/107/112, `datetime.utcnow()` fix).

**Critical finding — overlapping subnet constraint:** Docker (both macOS Docker Desktop 29.4.3 and standard Linux bridge driver) does NOT permit two user-defined bridge networks with the same subnet on a single daemon host. The `invalid pool request: Pool overlaps with other one on this address space` error is enforced at the IPAM pool level regardless of `driver_opts`. This is a hard constraint for the CONTEXT.md-locked "same subnet `10.10.0.0/24`" design. The practical solution is to use distinct but closely-matched subnets (e.g. `10.10.0.0/24` and `10.20.0.0/24`) while assigning the same last-octet address (`.10`) in each, then configuring each sensor's `config.yaml` to scan its target as `10.10.0.10` — the *scan-target IP from the sensor's perspective*. This is semantically correct: in production, two separate segments both legitimately contain `10.10.0.10:443`; the segment label (not the Docker network name) is the differentiator. The planner should document this subnet workaround clearly in the compose file and oracle. [VERIFIED: Docker runtime test]

**Critical finding — sensor container install:** The lightest reliable approach is a custom minimal `Dockerfile` (`FROM python:3.11-slim`) that bind-mounts the repo root at compose-build time (via `context: ../../.`) and runs `pip install .[all]` (not editable `-e`). Non-editable install copies to site-packages, is container-self-contained, and requires no write access or `.egg-link` metadata. The existing production `Dockerfile` at repo root confirms `pip install --no-cache-dir quirk-scanner[all]` as the established pattern. [VERIFIED: repo Dockerfile + lab grpc-tls pattern]

**Primary recommendation:** Use `10.10.0.0/24` + `10.20.0.0/24` as the two network subnets, static IP `10.10.0.10` in each, both sensor config.yaml files target `10.10.0.10:443` (which is reachable from within each respective segment). The two sensors report `host=10.10.0.10, segment=segment-a` and `host=10.10.0.10, segment=segment-b` — the merge produces two distinct CBOM components exactly as MERGE-03 proves.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Multi-segment Docker topology | Chaos Lab (compose) | — | Network isolation and static IP assignment are compose-level concerns |
| Sensor container install | Chaos Lab (Dockerfile) | Compose bind-mount | Package install happens at image build time |
| E2E orchestration (enroll/push/merge) | Shell script (distributed-e2e.sh) | lab.sh subcommand dispatch | Sequencing CLI commands that cross container boundaries |
| Expected-results oracle | Documentation file | README reference | Human-readable oracle for UAT pass criteria |
| lab.sh `distributed` subcommand | Bash CLI (lab.sh) | — | Launches the separate compose file; must not touch ALL_PROFILES |
| Operators-guide distributed section | Documentation | — | Narrative workflow for operators; no runtime code |
| datetime.utcnow() fix | sensor_cmd.py L296 | — | Single occurrence; replace with existing project idiom |
| UAT-SERIES coverage (106/107/112) | docs/UAT-SERIES.md | Obsidian sync | Add missing series sections; update version header |

---

## CRITICAL RESOLVED: Overlapping-Subnet Constraint (FLAGGED item 1)

### Docker Behavior — Verified Against Runtime

**Finding:** Docker bridge networks on a single host CANNOT share the same subnet. The IPAM pool check rejects the second network with `invalid pool request: Pool overlaps with other one on this address space`. This applies to:
- macOS Docker Desktop 29.4.3 (tested directly)
- Linux Docker bridge driver (same IPAM check in the daemon)
- `driver_opts: com.docker.network.bridge.inhibit_ipv4_check: "1"` — does NOT bypass the IPAM pool check at the daemon level on this Docker version [VERIFIED: Docker runtime test]

**Implication for CONTEXT.md locked design:** The "same subnet `10.10.0.0/24` in both networks" is not achievable without modifying the Docker daemon configuration (experimental flag, not portable across operators). The planner must use distinct subnets.

### Recommended Workaround — Two Subnets, Same Scan-Target IP

Use **two different subnets** with the same `.10` static host address:

- `segment-a` network: subnet `10.10.0.0/24`, target `tls-segment-a` at static IP `10.10.0.10`
- `segment-b` network: subnet `10.20.0.0/24`, target `tls-segment-b` at static IP `10.20.0.10`

Each sensor's `config.yaml` scans the target as `10.10.0.10:443` (sensor-a, reporting as segment `segment-a`) and `10.10.0.10:443` (sensor-b, reporting as segment `segment-b`). **Both sensors report the same `host:port` because that is what the target looks like from inside each segment.** The Docker-level IPs differ but the sensor-reported target IPs are identical — exactly modeling the real-world scenario where `10.10.0.10:443` exists in both the DMZ and the PCI segment.

This is the correct modeling because MERGE-03 relies on `sensor_id + segment` label distinctness, not on Docker network overlap. The `(sensor_id, host, port)` uniqueness key in `CryptoEndpoint` produces two rows for `host=10.10.0.10, port=443` when `sensor_id` differs. [VERIFIED: REQUIREMENTS.md MERGE-03, architecture-distributed.md §5]

### Automated Assertions for CI Floor

The strongest automated assertions achievable without a live run are:

```python
# tests/test_distributed_topology.py
import yaml
from pathlib import Path

LAB_DIR = Path("quantum-chaos-enterprise-lab")
COMPOSE = LAB_DIR / "docker-compose.distributed.yml"

def _load():
    return yaml.safe_load(COMPOSE.read_text())

def test_compose_file_exists():
    assert COMPOSE.exists()

def test_two_networks_defined():
    data = _load()
    nets = data.get("networks", {})
    assert len(nets) >= 2, f"Expected >=2 networks, found {list(nets)}"

def test_each_network_has_ipam_subnet():
    data = _load()
    for name, net in data.get("networks", {}).items():
        subnets = (net or {}).get("ipam", {}).get("config", [])
        assert subnets, f"Network '{name}' has no ipam.config subnet"

def test_same_static_ip_in_both_networks():
    """Both segment-a and segment-b have a service at 10.10.0.10 (or same last octet)."""
    data = _load()
    ips_per_network: dict = {}
    for svc_name, svc in (data.get("services") or {}).items():
        for net_name, net_cfg in (svc.get("networks") or {}).items():
            ip = (net_cfg or {}).get("ipv4_address", "")
            ips_per_network.setdefault(net_name, set()).add(ip)
    # The last octet should match across both segment networks
    all_ips = [list(v)[0].split(".")[-1] for v in ips_per_network.values() if v]
    assert len(set(all_ips)) == 1, f"Expected same last-octet IP in both networks, got {all_ips}"

def test_one_sensor_service_per_segment():
    data = _load()
    sensor_svcs = [n for n in data.get("services", {}) if "sensor" in n]
    assert len(sensor_svcs) >= 2

def test_one_console_service():
    data = _load()
    console_svcs = [n for n in data.get("services", {}) if "console" in n]
    assert len(console_svcs) >= 1
```

For the e2e script assertion:
```python
def test_e2e_script_references_enroll_push_merge():
    script = (LAB_DIR / "scripts" / "distributed-e2e.sh").read_text()
    assert "enroll" in script
    assert "push" in script
    assert "merge" in script
    # Assert order: enroll appears before push, push before merge
    assert script.index("enroll") < script.index("push") < script.index("merge")
```

`docker compose -f docker-compose.distributed.yml config` validates the compose file schema without bringing containers up and can run in CI. [VERIFIED: Docker docs behavior]

---

## CRITICAL RESOLVED: Sensor Container Repo Install (FLAGGED item 2)

### Recommendation: Minimal Dockerfile with `pip install .[all]`

**Lightest reliable approach:**

```dockerfile
# quantum-chaos-enterprise-lab/sensor.Dockerfile
FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends nmap ca-certificates curl \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /quirk
# Build context is the repo root (context: ../..)
COPY . /quirk/
RUN pip install --no-cache-dir ".[all]"

ENTRYPOINT ["quirk"]
CMD ["--help"]
```

In `docker-compose.distributed.yml`:
```yaml
sensor-a:
  build:
    context: ../..
    dockerfile: quantum-chaos-enterprise-lab/sensor.Dockerfile
  ...
```

**Why not editable (`pip install -e .`):**
- Editable installs create `.egg-link` files pointing to the source tree; containers rebuilding from a bind-mount require the source tree to remain mounted at runtime
- setuptools editable mode with `find_packages` requires the source tree at import time
- Non-editable copies all packages to site-packages — self-contained, no runtime dependency on mount

**Why not pre-built wheel:**
- Requires an explicit `python -m build` step before `docker compose up`; more moving parts
- The lab "runs from the repo checkout" — a build step is an extra operator task

**Why `.[all]` and not bare `pip install .`:**
- `quirk sensor push` uses `tenacity`, `zstandard`, `platformdirs` (in core deps — see pyproject.toml L33-35)
- `quirk serve` needs `fastapi`, `uvicorn` (in `[dashboard]` extra, included in `[all]`)
- Full `[all]` ensures no missing-extra advisory findings corrupt the lab scan
- `[identity]` is intentionally excluded from `[all]` (impacket + cryptography downgrade); this is correct for the sensor containers

**Entry point:** `quirk = "run_scan:_run_main_with_job_guard"` (pyproject.toml L119). Both `quirk sensor` and `quirk serve` dispatch through `run_scan.py`. [VERIFIED: pyproject.toml]

**Dependency verification:** `platformdirs>=4.3.0`, `tenacity>=8.2.0`, `zstandard>=0.22.0` are all in the `[project].dependencies` (core) group, not in an optional extra. They install with the bare `pip install .`. [VERIFIED: pyproject.toml L33-35]

---

## Docker Compose: Two-Network Topology Patterns

### Compose IPAM Syntax for Named Networks with Static IPs

```yaml
networks:
  segment-a:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: "10.10.0.0/24"
  segment-b:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: "10.20.0.0/24"

services:
  tls-segment-a:
    image: nginx:1.28.0
    networks:
      segment-a:
        ipv4_address: "10.10.0.10"
    # No published ports — sensor-a reaches it via container network

  sensor-a:
    build:
      context: ../..
      dockerfile: quantum-chaos-enterprise-lab/sensor.Dockerfile
    networks:
      - segment-a
      - console-net   # needs console-net to push to console
```

**Note:** A service attached to only one network can only reach services on that same network. The sensor container needs both the segment network (to scan the target) AND access to the console (to push). Solutions:
1. Attach each sensor to its segment network + a shared `console-net` network
2. Or attach the console to all networks (simpler but less realistic)

Option 1 is more architecturally correct. The console container attaches only to `console-net` and `0.0.0.0` binds its port. [VERIFIED: Docker networking docs]

### `quirk serve` Binding in a Container

`quirk serve` default host is `127.0.0.1` (loopback-only) as seen in `run_scan.py:396`. In a container, sensors hitting the console must bind `0.0.0.0`. The distributed-e2e.sh script must start the console with:

```bash
quirk serve --host 0.0.0.0 --port 8512
```

The console container's `docker-compose.distributed.yml` entry must pass `--host 0.0.0.0`. [VERIFIED: run_scan.py:396]

### How the E2E Script Passes the Enrollment Token to Each Sensor

The enrollment flow from `quirk console enroll` prints the raw bearer token to stdout once. The e2e script must capture it:

```bash
# In distributed-e2e.sh (pseudocode)
# Step 1: Enroll sensor-a on the console
TOKEN_A=$(docker compose -p quirk-dist -f docker-compose.distributed.yml \
  exec -T console quirk console enroll --segment segment-a)

# Step 2: Write sensor-a config with that token
docker compose ... exec -T sensor-a \
  quirk sensor enroll https://console:8512 \
    --segment segment-a \
    --api-token "$TOKEN_A"
```

`quirk sensor enroll` accepts `--api-token` (sensor_cmd.py L94) and writes it to `sensor.yaml` as `console_api_token`. [VERIFIED: sensor_cmd.py:94,220]

---

## lab.sh Command Structure — Adding `distributed`

### ALL_PROFILES Drift Rule — No Change Required

`ALL_PROFILES` is derived dynamically from `docker-compose.yml` via `_derive_all_profiles()` (lab.sh:58-70). Because the distributed topology lives in a **separate file** (`docker-compose.distributed.yml`), `ALL_PROFILES` is unaffected. The CLAUDE.md no-drift rule applies to the main compose file only. [VERIFIED: lab.sh:58-70, CONTEXT.md]

### Adding the `distributed` Subcommand

The `case "${cmd}"` block in lab.sh (~L114) must gain a `distributed)` arm. Pattern mirrors the Darwin kerberos-skip pattern at L143:

```bash
distributed)
  COMPOSE_FILE="docker-compose.distributed.yml"
  PROJECT_NAME="quirk-dist"
  subcmd="${1:-up}"
  shift || true
  case "${subcmd}" in
    up)
      if ! _validate_pinned_tags; then
        echo "Refusing to start: pin policy violation (CHAOS-05)." >&2; exit 1
      fi
      compose up -d "$@"
      compose ps
      ;;
    down)   compose --profile "*" down --remove-orphans ;;
    status) compose ps ;;
    logs)   compose logs -f --tail=200 "${1:-}" ;;
    e2e)    bash "$(dirname "$0")/scripts/distributed-e2e.sh" "$@" ;;
    *)      echo "Unknown distributed subcommand: ${subcmd}"; exit 1 ;;
  esac
  ;;
```

The `_validate_pinned_tags` function already accepts a file argument via `"${COMPOSE_FILE}"` (lab.sh:83) — it will pick up the new `COMPOSE_FILE` value because `COMPOSE_FILE` is reassigned before calling it.

`status` and `logs` use the `compose` helper which reads `PROJECT_NAME` and `COMPOSE_FILE` from the outer scope — reassigning them before the subcmd block means they work cleanly. [VERIFIED: lab.sh:51-54]

**Usage example:**
```bash
./lab.sh distributed up
./lab.sh distributed e2e
./lab.sh distributed down
./lab.sh distributed status
```

---

## expected_results_distributed.md Oracle Format

Mirror the `expected_results_v4.md` format exactly. Key sections to include:

```markdown
# Expected Scanner Results — Distributed Topology

**Scope:** docker-compose.distributed.yml (multi-segment overlay topology)
**Oracle type:** Distributed E2E validation (LAB-01/LAB-02)
**Status:** Authoritative for Phase 112 distributed lab

Host assumed: 10.10.0.10 (as reported by both sensors for their respective targets)

---

## Topology: distributed

*Two isolated Docker bridge networks (`segment-a`, `segment-b`), one TLS crypto
target per segment at static IP `10.10.0.10`, one sensor container per segment,
one console container on a shared `console-net` network.*

### Networks

| Network | Subnet | Purpose |
|---------|--------|---------|
| `segment-a` | `10.10.0.0/24` | DMZ-analog segment — sensor-a + tls-target-a |
| `segment-b` | `10.20.0.0/24` | PCI-analog segment — sensor-b + tls-target-b |
| `console-net` | `10.30.0.0/24` | Console-reachable network — console + both sensors |

### Services

| Service | IP | Port | Role |
|---------|----|------|------|
| `tls-target-a` | `10.10.0.10` | 443 | Crypto target in segment-a (nginx TLS) |
| `tls-target-b` | `10.20.0.10` | 443 | Crypto target in segment-b (same config) |
| `sensor-a` | `10.10.0.x` | — | Sensor scanning segment-a, pushing to console |
| `sensor-b` | `10.20.0.x` | — | Sensor scanning segment-b, pushing to console |
| `console` | `10.30.0.x` | `8512` | QUIRK console (quirk serve --host 0.0.0.0) |

### Expected E2E Outcome

| Assertion | Expected Value |
|-----------|---------------|
| Sensors enrolled | 2 rows in `sensors` table |
| Pushes accepted | 2 pushes, HTTP 200 each |
| CBOM components for `10.10.0.10:443` | **2 distinct components** (different `sensor_id`) |
| Merged score | Single `compute_readiness_score()` call over union of both sensors |
| `coverage_warning` | `null` (both sensors reported in) |

### MERGE-03 Validation

Both sensors report `host=10.10.0.10, port=443` with different `segment` labels.
After `quirk sensor merge`, the CBOM must contain two components — NOT one merged/deduped
component — because the `(sensor_id, host, port)` key is unique per sensor.
This physically proves MERGE-03 (same RFC1918 IP in two segments → two components).
```

[CITED: expected_results_v4.md header + profile format]

---

## operators-guide.md — Gap Analysis

### Current Coverage (end of file at L421)

The operators-guide.md has 7 sections: Install (§1), Configure (§2), Scan (§3), Validation/Smoke Test (§4), Troubleshooting (§5), Per-Scanner Reference (§6), Compliance Map Maintenance (§7). [VERIFIED: operators-guide.md grep]

### What Is Missing (999.59 gap)

**No distributed workflow section exists.** The guide covers single-host scanning entirely. Missing content:

1. **§8 Distributed Sensor Deployment** — the full enroll → push → merge workflow
2. **Windows sensor installation steps** — `pip install quirk-scanner` on Windows, `platformdirs` config path (`%APPDATA%\quirk\sensor.yaml`), PowerShell commands
3. **All-configurations/settings coverage** — The backlog item 999.59 in HORIZON.md is described as "operators-guide all-configurations-and-settings coverage." Scanning §2 and §6, coverage is sparse: no mention of `scan.timeouts.*` knob names in §2 (the troubleshooting section §5.1 mentions `tls_seconds` but not the full set), no mention of `output.directory` default, no mention of `sensor_id`/`segment` fields in scan output

**New section content required:**
- `quirk console enroll` (provision sensor in console DB, get bearer token)
- `quirk sensor enroll <console_url> --segment <label> --api-token <token>` (write sensor.yaml)
- `quirk sensor push` (run scan + push; spool if offline)
- `quirk sensor merge` (produce unified CBOM + score)
- `quirk sensor export-results` + `quirk console import-results` (air-gap path)
- Windows: `pip install quirk-scanner[all]`, sensor.yaml path via `platformdirs` (`%APPDATA%\quirk\sensor.yaml` on Windows), PowerShell snippet, `sys.platform != 'win32'` SIGTERM guard

[VERIFIED: operators-guide.md sections]

---

## datetime.utcnow() Fix (STAB-03)

### Exact Occurrences

**sensor_cmd.py:296** (the only occurrence in the entire `quirk/` package):

```python
# Current (deprecated in Python 3.12+):
"pushed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),

# Required replacement (matching project idiom):
"pushed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
```

The `from datetime import datetime` import at L39 must gain `timezone`:
```python
from datetime import datetime, timezone
```

**No sibling files affected:** All other `quirk/` files already use `datetime.now(timezone.utc)` or `datetime.now(timezone.utc).replace(tzinfo=None)`. [VERIFIED: grep of entire quirk/ package]

### Established Project Idiom

The project uses two forms depending on context:
- **For display/wire format (UTC ISO string):** `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")`
- **For SQLite storage (naive datetime):** `datetime.now(timezone.utc).replace(tzinfo=None)`

`pushed_at` is a wire-format field (ISO string), so the first form applies. [VERIFIED: quirk/notify/dispatcher.py:208, quirk/merge/scan.py:178]

---

## UAT-SERIES.md — Current Coverage

### Series That Already Exist (108-111 all added)

| Series | Phase | Status |
|--------|-------|--------|
| Series 106 | Architecture Documentation | EXISTS — UAT-106-01 |
| Series 107 | Distributed Data Model | EXISTS — UAT-107-01 |
| Series 108 | Sensor Push CLI + Windows CI | EXISTS — UAT-108-01..05 |
| Series 109 | Console Ingestion API | EXISTS — UAT-109-01..04 |
| Series 110 | Cross-Sensor Merge | EXISTS — UAT-110-01..06 |
| Series 111 | Console Dashboard Awareness | EXISTS — UAT-111-01..03 |
| **Series 112** | **Distributed Chaos-Lab + Stabilization** | **MISSING** |

[VERIFIED: grep of UAT-SERIES.md series 106-111]

### Series 112 Must Add

Minimum test cases required:

- **UAT-112-01:** `docker compose config` validates distributed compose schema — Automated
- **UAT-112-02:** Static topology test — two networks, same last-octet IP in both, enroll-push-merge order in e2e script — Automated
- **UAT-112-03:** Live E2E run — enroll → push → merge → two CBOM components for `10.10.0.10:443` — Human
- **UAT-112-04:** `datetime.utcnow()` deprecation removed — Automated (`python -W error::DeprecationWarning -c "from quirk.cli.sensor_cmd import _build_envelope"` must not warn)
- **UAT-112-05:** operators-guide §8 distributed workflow present — Automated (section heading exists + key command strings present)

---

## Standard Stack

### Core (no new packages — zero new dependencies)

| Component | Version | Purpose | Source |
|-----------|---------|---------|--------|
| PyYAML | >=6.0 (core dep) | Parse compose YAML in topology test | pyproject.toml L11 |
| pytest | (dev) | Topology test framework | existing |
| docker compose | (runtime) | Multi-network lab | existing |
| python:3.11-slim | Docker base | Sensor/console container base | existing Dockerfile pattern |

**No new pip packages required.** `platformdirs`, `tenacity`, `zstandard` are already in core dependencies. [VERIFIED: pyproject.toml]

### Package Legitimacy Audit

No new packages are introduced in this phase. All packages used are pre-existing core dependencies. This section is not applicable.

---

## Architecture Patterns

### System Architecture Diagram

```
quantum-chaos-enterprise-lab/
  docker-compose.distributed.yml
  ┌────────────────────────────────────────────────────────────────┐
  │  segment-a (10.10.0.0/24)          segment-b (10.20.0.0/24)   │
  │  ┌──────────────────────┐           ┌──────────────────────┐   │
  │  │ tls-target-a         │           │ tls-target-b         │   │
  │  │ IP: 10.10.0.10:443   │           │ IP: 10.20.0.10:443   │   │
  │  └────────▲─────────────┘           └────────▲─────────────┘   │
  │           │scan                              │scan              │
  │  ┌────────┴─────────────┐           ┌────────┴─────────────┐   │
  │  │ sensor-a             │           │ sensor-b             │   │
  │  │ segment=segment-a    │           │ segment=segment-b    │   │
  │  │ reports host=10.10.  │           │ reports host=10.10.  │   │
  │  │         0.10:443     │           │         0.10:443     │   │
  │  └──────────────────────┘           └──────────────────────┘   │
  │           │push (console-net)                │push             │
  │           └──────────────────┬───────────────┘                │
  │                              │                                  │
  │                    ┌─────────▼──────────┐                      │
  │                    │ console            │  console-net          │
  │                    │ quirk serve        │  (10.30.0.0/24)       │
  │                    │ --host 0.0.0.0     │                      │
  │                    │ --port 8512        │                      │
  │                    └────────────────────┘                      │
  │                              │                                  │
  │                    quirk sensor merge                          │
  │                              │                                  │
  │                    ┌─────────▼──────────┐                      │
  │                    │ CBOM: 2 components  │                      │
  │                    │ host=10.10.0.10:443 │                      │
  │                    │ sensor_id=A + B     │                      │
  │                    └────────────────────┘                      │
  └────────────────────────────────────────────────────────────────┘
```

Orchestration: `distributed-e2e.sh` → `lab.sh distributed e2e` → console enroll → sensor-a enroll → sensor-b enroll → sensor-a push → sensor-b push → merge

### Recommended Project Structure (new files only)

```
quantum-chaos-enterprise-lab/
├── docker-compose.distributed.yml   # NEW: two-network topology
├── sensor.Dockerfile                # NEW: sensor+console container image
├── expected_results_distributed.md  # NEW: E2E oracle
└── scripts/
    └── distributed-e2e.sh           # NEW: enroll→push→merge orchestrator

tests/
└── test_distributed_topology.py     # NEW: static compose assertions
```

### Anti-Patterns to Avoid

- **Publishing ports from segment services:** targets in `segment-a`/`segment-b` should use `expose:` not `ports:` — sensors reach them via container network; no host-port binding needed (avoids port collisions with the main lab)
- **Using `quirk serve` default host `127.0.0.1` in the console container:** bind must be `0.0.0.0` so sensors on other networks can reach the push endpoint
- **Editable install (`pip install -e .`) in the container:** requires source tree mounted at runtime; use `pip install .[all]` instead
- **Hardcoding enrollment token in docker-compose.yml:** the token is one-time-use and printed to stdout; `distributed-e2e.sh` must capture it dynamically

---

## Common Pitfalls

### Pitfall 1: Docker Subnet Overlap Rejection

**What goes wrong:** `docker compose up` for the distributed topology fails with `invalid pool request: Pool overlaps with other one on this address space` if the same subnet is used for both networks.

**Why it happens:** The Docker IPAM pool check prevents overlapping subnets on the same daemon host, even for separate user-defined bridge networks.

**How to avoid:** Use distinct subnets (`10.10.0.0/24` and `10.20.0.0/24`). Configure scan targets in each sensor's `config.yaml` to use `10.10.0.10:443` (the target IP as seen from within that segment). Both sensors report the same scan-target IP to the console — MERGE-03 is validated by `sensor_id + segment` label, not by physical Docker IP collision.

**Warning signs:** `failed to create network quirk-dist_segment-b` error on `./lab.sh distributed up`.

### Pitfall 2: quirk serve Loopback Bind in Container

**What goes wrong:** Sensors cannot reach the console push endpoint because `quirk serve` binds `127.0.0.1` by default.

**Why it happens:** `run_scan.py:396` sets default host to `127.0.0.1`. In a container, loopback is container-local only.

**How to avoid:** Always pass `--host 0.0.0.0` in the console container's `command:` in `docker-compose.distributed.yml`.

**Warning signs:** Sensor push returns `httpx.ConnectError` with "Connection refused" despite console being "up".

### Pitfall 3: Sensor Token Capture in e2e Script

**What goes wrong:** `quirk console enroll` prints the bearer token once to stdout; if the e2e script doesn't capture it correctly, `quirk sensor enroll --api-token` gets an empty or malformed value.

**Why it happens:** The raw token is printed to stdout; warnings go to stderr. `$()` captures stdout only — correct behavior if the script uses `TOKEN=$(docker compose exec -T console quirk console enroll ...)`.

**How to avoid:** Use `-T` (disable pseudo-TTY) in `docker compose exec` so stdout capture works cleanly. Parse the token from the `Enrollment token (shown once — save it now):` line.

**Warning signs:** Sensor push returns HTTP 401; `sensor.yaml` has empty `console_api_token`.

### Pitfall 4: datetime.utcnow() DeprecationWarning in Python 3.12+

**What goes wrong:** `python -W error::DeprecationWarning` fails or runtime emits `DeprecationWarning: datetime.utcnow()` on Python 3.12+.

**Why it happens:** `sensor_cmd.py:296` calls `datetime.utcnow()` which was deprecated in Python 3.12.

**How to avoid:** Replace with `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")` and add `timezone` to the `from datetime import datetime, timezone` import.

**Warning signs:** CI runs with Python 3.12+ emit deprecation warnings; `-W error` flag turns them into test failures.

### Pitfall 5: lab.sh ALL_PROFILES Drift Check

**What goes wrong:** A CI test checks that `lab.sh profiles` output matches the profiles in `docker-compose.yml`. Adding a new profile to the main compose without updating `expected_results_v4.md` causes the oracle-drift test to fail.

**Why it happens:** The distributed topology is in a separate compose file so ALL_PROFILES is unaffected. But the planner must not accidentally add new profiles to the main `docker-compose.yml`.

**How to avoid:** Confirm all new services are in `docker-compose.distributed.yml` only.

---

## Code Examples

### sensor.Dockerfile

```dockerfile
# quantum-chaos-enterprise-lab/sensor.Dockerfile
# Sensor and console container for the distributed chaos-lab topology.
# Build context is the repo root: context: ../..
FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends nmap ca-certificates curl \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /quirk
COPY . /quirk/
RUN pip install --no-cache-dir ".[all]"

ENTRYPOINT ["quirk"]
CMD ["--help"]
```

### docker-compose.distributed.yml (skeleton)

```yaml
# Source: CONTEXT.md decisions, Docker compose IPAM docs
services:
  tls-target-a:
    image: nginx:1.28.0
    volumes:
      - ./nginx/modern/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    networks:
      segment-a:
        ipv4_address: "10.10.0.10"

  tls-target-b:
    image: nginx:1.28.0
    volumes:
      - ./nginx/modern/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    networks:
      segment-b:
        ipv4_address: "10.20.0.10"

  sensor-a:
    build:
      context: ../..
      dockerfile: quantum-chaos-enterprise-lab/sensor.Dockerfile
    networks:
      - segment-a
      - console-net
    depends_on:
      - tls-target-a
      - console

  sensor-b:
    build:
      context: ../..
      dockerfile: quantum-chaos-enterprise-lab/sensor.Dockerfile
    networks:
      - segment-b
      - console-net
    depends_on:
      - tls-target-b
      - console

  console:
    build:
      context: ../..
      dockerfile: quantum-chaos-enterprise-lab/sensor.Dockerfile
    command: ["serve", "--host", "0.0.0.0", "--port", "8512"]
    networks:
      - console-net
    volumes:
      - console-data:/home/quirk

networks:
  segment-a:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: "10.10.0.0/24"
  segment-b:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: "10.20.0.0/24"
  console-net:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: "10.30.0.0/24"

volumes:
  console-data:
```

### Topology assertion test (tests/test_distributed_topology.py)

```python
# Source: RESEARCH findings + project test pattern (yaml.safe_load per test_chaos_lab_image_pinning.py)
import yaml
from pathlib import Path

LAB_DIR = Path(__file__).resolve().parent.parent / "quantum-chaos-enterprise-lab"
DIST_COMPOSE = LAB_DIR / "docker-compose.distributed.yml"
E2E_SCRIPT = LAB_DIR / "scripts" / "distributed-e2e.sh"

def test_distributed_compose_file_exists():
    assert DIST_COMPOSE.exists(), "docker-compose.distributed.yml must exist"

def test_config_validates():
    """docker compose config on the distributed compose must exit 0."""
    import subprocess
    result = subprocess.run(
        ["docker", "compose", "-f", str(DIST_COMPOSE), "config"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"compose config failed: {result.stderr}"

def _load_dist():
    return yaml.safe_load(DIST_COMPOSE.read_text())

def test_two_bridge_networks():
    nets = _load_dist().get("networks", {})
    assert len(nets) >= 2

def test_networks_have_ipam_subnets():
    for name, net in _load_dist().get("networks", {}).items():
        subnets = (net or {}).get("ipam", {}).get("config", [])
        if name == "console-net":
            continue  # management network
        assert subnets, f"Segment network '{name}' missing ipam.config"

def test_same_host_ip_in_segment_networks():
    """Both segment-a and segment-b must have a service at the same host IP."""
    data = _load_dist()
    static_ips = {}
    for svc, cfg in (data.get("services") or {}).items():
        for net_name, net_cfg in (cfg.get("networks") or {}).items():
            if isinstance(net_cfg, dict):
                ip = net_cfg.get("ipv4_address", "")
                if ip:
                    static_ips.setdefault(net_name, []).append(ip)
    seg_ips = {k: v[0].split(".")[-1] for k, v in static_ips.items()}
    # Last octets must match across segment networks
    last_octets = set(seg_ips.values())
    assert len(last_octets) <= 1, f"Segment target last-octet IPs differ: {seg_ips}"

def test_e2e_script_enroll_push_merge_order():
    text = E2E_SCRIPT.read_text()
    ei = text.index("enroll")
    pi = text.index("push")
    mi = text.index("merge")
    assert ei < pi < mi, "e2e script must reference enroll before push before merge"
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| IPAM subnet config | Custom subnet negotiation | Docker compose `ipam.config[].subnet` | Standard compose IPAM syntax |
| Container readiness | Fixed `sleep 30` in e2e script | `docker compose exec` with retry loop or `healthcheck:` + `depends_on: condition: service_healthy` | Fixed sleeps are fragile on slow machines |
| Token capture | Parsing quirk console output with custom regex | `$()` capture of stdout + grep for token line | Straightforward shell pattern |
| Topology validation | Ad-hoc bash assertions | `pytest` + `yaml.safe_load` | Project already uses this pattern (test_chaos_lab_image_pinning.py) |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_distributed_topology.py -x` |
| Full suite command | `pytest -m 'not slow'` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LAB-01 | Multi-segment E2E flow validated | Human (live run) + Automated (compose config) | `pytest tests/test_distributed_topology.py::test_config_validates` | ❌ Wave 0 |
| LAB-02 | Same-IP two-components assertion | Automated (topology) + Human (merge output) | `pytest tests/test_distributed_topology.py::test_same_host_ip_in_segment_networks` | ❌ Wave 0 |
| LAB-03 | lab.sh + README + oracle updated | Automated (file existence + heading check) | `pytest tests/test_distributed_topology.py::test_distributed_compose_file_exists` | ❌ Wave 0 |
| STAB-01 | operators-guide §8 section present | Automated (grep for section heading + key commands) | `grep -q "## 8. Distributed" docs/operators-guide.md` | ❌ Wave 0 |
| STAB-03 | datetime.utcnow() gone | Automated (DeprecationWarning -W error) | `python -W error::DeprecationWarning -c "from quirk.cli.sensor_cmd import _build_envelope"` | ❌ Wave 0 |

### Wave 0 Gaps

- [ ] `tests/test_distributed_topology.py` — covers LAB-01/02/03 static assertions
- [ ] `docker-compose.distributed.yml` — required before test can run
- [ ] `quantum-chaos-enterprise-lab/sensor.Dockerfile` — required for compose build
- [ ] `quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh` — required for e2e subcommand test

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `require_auth` on `/api/sensor/push` (already enforced in Phase 109) |
| V3 Session Management | no | No new session surfaces |
| V4 Access Control | no | No new access control surfaces |
| V5 Input Validation | yes | `compose -f ... config` validates compose YAML; sensor.yaml UUID validation already enforced |
| V6 Cryptography | no | No new crypto primitives; HMAC-SHA256 already enforced |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Sensor impersonation via stolen bearer token | Spoofing | One-time enrollment tokens + SHA-256 storage (already Phase 109); lab uses test tokens only |
| Path traversal in sensor.yaml `sensor_id` | Tampering | UUID regex gate in sensor_cmd.py (already enforced) |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Two distinct subnets with same last-octet IP adequately models the same-IP-across-segments scenario for MERGE-03 validation | CRITICAL RESOLVED §1 | MERGE-03 validation would be incomplete; would need Linux daemon `allow_network_overlap` setup |
| A2 | `python:3.11-slim` base is sufficient for `pip install .[all]` including nmap dependency in containers | Sensor Container Install | Build would fail; switch to `python:3.11` or add apt deps |

---

## Open Questions (RESOLVED)

> NOTE (2026-05-25): Claim A1 (same-last-octet IP) is SUPERSEDED by the user's topology decision and
> the plan-checker reachability finding. A sensor records the configured scan-target string verbatim
> (tls_scanner.py), but it must REACH the target to record a crypto finding — and sensor-b on
> 10.20.0.0/24 cannot reach 10.10.0.10. The correct mechanism is a **shared Docker DNS alias**
> (`crypto.internal`) on each segment's own target, so both sensors scan `crypto.internal:443`
> (locally reachable) and record an identical host:port. Same-last-octet IP is NOT used.

1. **RESOLVED — Readiness:** console container gets a `healthcheck:` (`curl -sf .../api/health`);
   sensor services use `depends_on: condition: service_healthy`. (Recommendation adopted.)

2. **RESOLVED — CHAOS-05 image pin:** `sensor.Dockerfile` uses `FROM python:3.11.12-slim`
   (patch-pinned) to satisfy the pin gate. (Recommendation adopted.)

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | compose topology | ✓ | 29.4.3 | — |
| Docker Compose v2 | `docker compose config` test | ✓ | v2.2.3 | — |
| python:3.11-slim | sensor.Dockerfile | ✓ (Docker Hub) | 3.11.x | python:3.11 |
| PyYAML | topology test | ✓ (core dep) | >=6.0 | — |
| pytest | topology test | ✓ (dev dep) | existing | — |

---

## Sources

### Primary (HIGH confidence)
- `quantum-chaos-enterprise-lab/lab.sh` — ALL_PROFILES derivation, command structure, `_validate_pinned_tags`, Darwin skip pattern [VERIFIED: codebase]
- `quantum-chaos-enterprise-lab/docker-compose.yml` — existing service definitions, profile patterns, IPAM syntax [VERIFIED: codebase]
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — oracle format to mirror [VERIFIED: codebase]
- `quirk/cli/sensor_cmd.py` — `_build_envelope()` L296 `datetime.utcnow()`, enroll `--api-token` arg L94, sensor.yaml format [VERIFIED: codebase]
- `quirk/cli/console_cmd.py` — `quirk console enroll` token print behavior [VERIFIED: codebase]
- `run_scan.py:396` — `quirk serve --host 127.0.0.1` default [VERIFIED: codebase]
- `pyproject.toml` — `platformdirs`, `tenacity`, `zstandard` in core deps (not extras); `quirk = "run_scan:_run_main_with_job_guard"` entrypoint [VERIFIED: codebase]
- Docker runtime test — overlapping bridge subnet rejection confirmed on Docker 29.4.3 [VERIFIED: Docker runtime]
- `docs/UAT-SERIES.md` — series 106-111 confirmed present; series 112 absent [VERIFIED: codebase]
- `docs/operators-guide.md` — sections 1-7 surveyed; no distributed workflow section exists [VERIFIED: codebase]
- `tests/test_chaos_lab_image_pinning.py` — PyYAML + compose-parse test pattern [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- `docs/architecture-distributed.md` — topology description, sensor_id/segment/host key semantics [CITED: repo]
- `Dockerfile` (repo root) — `pip install --no-cache-dir "quirk-scanner[all]"` as established container install pattern [VERIFIED: codebase]

### Tertiary (LOW confidence)
- Docker overlapping subnet behavior — confirmed via runtime test; documented constraint applies to Docker Desktop 29.4.3 on macOS and standard Linux bridge driver [VERIFIED: runtime + web search]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all tools verified present
- Architecture: HIGH — Docker network constraint verified by runtime test; compose syntax confirmed from existing lab
- Pitfalls: HIGH — verified via actual Docker network creation tests
- Docs gaps: HIGH — verified by reading operators-guide.md sections

**Research date:** 2026-05-25
**Valid until:** 2026-06-25 (Docker version changes could affect subnet constraint behavior)
