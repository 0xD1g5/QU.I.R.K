# Phase 112: Distributed Chaos-Lab + Stabilization — Pattern Map

**Mapped:** 2026-05-25
**Files analyzed:** 11 (9 new, 2 modified)
**Analogs found:** 10 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quantum-chaos-enterprise-lab/docker-compose.distributed.yml` | config | event-driven | `quantum-chaos-enterprise-lab/docker-compose.yml` | role-match |
| `quantum-chaos-enterprise-lab/sensor.Dockerfile` | config | file-I/O | `Dockerfile` (repo root) | exact |
| `quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh` | utility | request-response | `quantum-chaos-enterprise-lab/scripts/gen-certs.sh` | role-match |
| `quantum-chaos-enterprise-lab/lab.sh` | utility | request-response | `quantum-chaos-enterprise-lab/lab.sh` (self — add case arm) | exact |
| `quantum-chaos-enterprise-lab/expected_results_distributed.md` | config | — | `quantum-chaos-enterprise-lab/expected_results_v4.md` | exact |
| `quantum-chaos-enterprise-lab/README.md` | config | — | `quantum-chaos-enterprise-lab/expected_results_v4.md` | partial |
| `docs/operators-guide.md` | config | — | `docs/operators-guide.md` (self — append §8) | exact |
| `docs/UAT-SERIES.md` | config | — | `docs/UAT-SERIES.md` (self — Series 106/107 pattern) | exact |
| `quirk/cli/sensor_cmd.py` | utility | transform | `quirk/notify/dispatcher.py` | exact (datetime idiom) |
| `tests/test_distributed_topology.py` | test | file-I/O | `tests/test_chaos_lab_image_pinning.py` | exact |
| `pyproject.toml` | config | — | `pyproject.toml` (self — verify only, likely no change) | N/A |

---

## Pattern Assignments

---

### `quantum-chaos-enterprise-lab/docker-compose.distributed.yml` (config, event-driven)

**Analog:** `quantum-chaos-enterprise-lab/docker-compose.yml`

**Service definition pattern** (docker-compose.yml lines 5-11 and 18-25 — nginx TLS service with pinned image, volume mounts, no port publishing for internal-only services):
```yaml
tls-modern:
  image: nginx:1.28.0
  volumes:
    - ./nginx/modern/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./certs:/etc/nginx/certs:ro
  ports:
    - "443:443"
```

For distributed topology, segment-internal targets use `expose:` not `ports:` to avoid host-port collisions with the main lab. Static IP assignment within each bridge network uses the IPAM syntax from RESEARCH.md:

```yaml
tls-target-a:
  image: nginx:1.28.0
  volumes:
    - ./nginx/modern/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./certs:/etc/nginx/certs:ro
  expose:
    - "443"
  networks:
    segment-a:
      ipv4_address: "10.10.0.10"
```

**Network IPAM pattern** (new — no analog in docker-compose.yml which uses default networking):
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
  console-net:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: "10.30.0.0/24"
```

**CHAOS-05 pin policy:** Every `image:` key in the file must be a pinned tag (not `:latest`, not bare).  Build-only services (sensor-a, sensor-b, console) use `build:` with no `image:` — exempt from `_validate_pinned_tags`, but `FROM` in sensor.Dockerfile must be pinned (e.g. `FROM python:3.11.12-slim`). The `_validate_pinned_tags` function in `lab.sh` (lines 77-109) checks `${COMPOSE_FILE}` — it will pick up `docker-compose.distributed.yml` because `COMPOSE_FILE` is reassigned in the `distributed)` case arm before `_validate_pinned_tags` is called.

**FLAGGED TRAP — hostname alias:** CONTEXT.md D-01 contains a dependency note: QUIRK must record the configured `host` string on `CryptoEndpoint.host`, not the resolved IP. The RESEARCH.md resolution (distinct subnets `10.10.0.0/24` + `10.20.0.0/24` with the same last-octet `.10` per segment, both sensors configured to scan `10.10.0.10:443`) depends on each sensor's `config.yaml` scan-target list pointing at `10.10.0.10` — not a hostname alias that Docker could resolve differently. Confirm this assumption in the topology test (`test_same_host_ip_in_segment_networks`) before writing the oracle.

---

### `quantum-chaos-enterprise-lab/sensor.Dockerfile` (config, file-I/O)

**Analog:** `Dockerfile` (repo root, lines 1-61)

**Base image + apt layer pattern** (Dockerfile lines 18, 37-43):
```dockerfile
FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        nmap \
        curl \
        ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
```

For the sensor.Dockerfile the base must be pinned more specifically to satisfy the spirit of CHAOS-05 (`FROM python:3.11.12-slim`, not `python:3.11-slim`).

**Install pattern** (Dockerfile line 53 — pip install from PyPI wheel):
```dockerfile
RUN pip install --no-cache-dir "quirk-scanner[all]==${QUIRK_VERSION}"
```

For the sensor/console container the install is from the local repo checkout (build context is `../..`), so the pattern becomes:
```dockerfile
WORKDIR /quirk
COPY . /quirk/
RUN pip install --no-cache-dir ".[all]"
```

**Entrypoint pattern** (Dockerfile lines 59-60):
```dockerfile
CMD ["quirk", "--help"]
```

For the sensor container, `ENTRYPOINT ["quirk"]` + `CMD ["--help"]` allows compose to override `command:` per-service (sensors run `sensor push`; console runs `serve --host 0.0.0.0 --port 8512`).

**Why `.[all]` and not bare `.`:** `quirk serve` requires `[dashboard]` (fastapi, uvicorn) which is included in `[all]`. `[identity]` (impacket) is intentionally excluded from `[all]` — correct for sensor containers.

---

### `quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh` (utility, request-response)

**Analog:** `quantum-chaos-enterprise-lab/scripts/gen-certs.sh` (lines 1-3 for shebang + error flags)

**Shell script header pattern** (gen-certs.sh lines 1-4):
```bash
#!/usr/bin/env bash
set -euo pipefail

mkdir -p certs
```

**Token capture pattern** (from RESEARCH.md — stdout-only capture with -T flag):
```bash
TOKEN_A=$(docker compose -p quirk-dist -f \
  "$(dirname "$0")/../docker-compose.distributed.yml" \
  exec -T console quirk console enroll --segment segment-a)
```

`-T` disables pseudo-TTY allocation so `$()` captures stdout cleanly. The enroll command prints the bearer token as the last line of stdout (RESEARCH.md L284-298 verified).

**Order constraint:** The e2e script MUST reference `enroll` before `push` before `merge` — this is asserted by `test_e2e_script_enroll_push_merge_order` in `tests/test_distributed_topology.py`.

---

### `quantum-chaos-enterprise-lab/lab.sh` (utility, request-response — MODIFIED)

**Analog:** `quantum-chaos-enterprise-lab/lab.sh` itself (lines 111-215)

**Case block insertion point** (lab.sh lines 111-114 and 208-216 — insert before the catch-all `*)`):
```bash
cmd="${1:-}"
shift || true

case "${cmd}" in
  up)
    ...
  ;;
  ...
  clean)
    ...
  ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    echo "❌ Unknown command: ${cmd}"
    usage
    exit 1
    ;;
esac
```

**New `distributed)` arm pattern** — mirrors the `up)` arm but reassigns `COMPOSE_FILE` and `PROJECT_NAME` before dispatching subcmds. The `compose` helper (lab.sh lines 51-54) reads both from the outer scope:
```bash
compose() {
  docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" ${PROFILE_ARGS} "$@"
}
```

So the distributed arm sets these vars, then calls the helper:
```bash
distributed)
  COMPOSE_FILE="$(dirname "$0")/docker-compose.distributed.yml"
  PROJECT_NAME="quirk-dist"
  subcmd="${1:-up}"
  shift || true
  case "${subcmd}" in
    up)
      if ! _validate_pinned_tags; then
        echo "❌ Refusing to start: pin policy violation (CHAOS-05)." >&2; exit 1
      fi
      compose up -d "$@"
      compose ps
      ;;
    down)   compose down --remove-orphans ;;
    status) compose ps ;;
    logs)   compose logs -f --tail=200 "${1:-}" ;;
    e2e)    bash "$(dirname "$0")/scripts/distributed-e2e.sh" "$@" ;;
    *)      echo "❌ Unknown distributed subcommand: ${subcmd}"; exit 1 ;;
  esac
  ;;
```

**ALL_PROFILES is unaffected:** `_derive_all_profiles` (lab.sh lines 58-70) reads `${COMPOSE_FILE}` which defaults to `docker-compose.yml`. The `distributed)` arm only sets `COMPOSE_FILE` inside its own `case` block scope — it never affects the main `up` / `all` paths. No change to the `ALL_PROFILES` sweep is needed. This satisfies the CLAUDE.md chaos-lab no-drift rule.

---

### `quantum-chaos-enterprise-lab/expected_results_distributed.md` (config — NEW)

**Analog:** `quantum-chaos-enterprise-lab/expected_results_v4.md` (lines 1-15 — header + scope block)

**Oracle header pattern** (expected_results_v4.md lines 1-10):
```markdown
# Expected Scanner Results — v4 Oracle

**Scope:** Every Docker Compose profile shipped through QU.I.R.K. v4.4 ...
**Status:** Authoritative. Supersedes `expected_results_v3.md`.
**Schema:** Per-profile H2 sections (`## Profile: <name>`). ...

Host assumed: `127.0.0.1`

---
```

**Profile section pattern** (expected_results_v4.md lines 13-35 — `## Profile: core` block with prose intro + code block + table):
```markdown
## Profile: core

*The "core" baseline — ...*

```bash
./lab.sh up
```

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|---:|---|---|---|---|
| 443 | tls-modern | TLS | MODERN_TLS | ... |
```

For the distributed oracle, the section heading becomes `## Topology: distributed` (there is no `--profile` flag — the topology is a separate compose file invoked via `lab.sh distributed up`). The table schema shifts from per-port to per-network + per-service + per-assertion.

---

### `quantum-chaos-enterprise-lab/README.md` (config — MODIFIED)

**Analog:** `expected_results_v4.md` header structure for the new distributed section block.

Pattern: add a "Distributed Topology" section after the existing profile table. Reference the `expected_results_distributed.md` oracle with an anchor link (matching the `## Topology: distributed` H2 as the cross-reference target, per expected_results_v4.md line 7: "Use the matching `## Profile: <name>` anchor as the cross-reference target from README.md (D-11)").

---

### `docs/operators-guide.md` (config — MODIFIED, append §8)

**Analog:** `docs/operators-guide.md` itself — `## 7. Compliance Map Maintenance` section (lines 337-421) is the closest structural pattern for a new numbered top-level section.

**Section structure pattern** (operators-guide.md lines 337-355 — numbered H2 + prose intro + numbered runbook steps):
```markdown
## 7. Compliance Map Maintenance

QU.I.R.K. ships a `COMPLIANCE_MAP` in `quirk/compliance/__init__.py` that joins
finding titles to PCI-DSS, HIPAA (45 CFR §164.312), and FIPS 140-3 controls.
...

### 7.1 Quarterly review checklist

1. Run `quirk compliance status` and confirm ...
2. Visit each publisher URL ...
```

New §8 follows this exact pattern: `## 8. Distributed Sensor Deployment` → prose intro → `### 8.1 Enroll a sensor` → `### 8.2 Push findings` → `### 8.3 Merge findings into a unified CBOM` → `### 8.4 Windows sensor installation` → `### 8.5 Air-gap path (export/import)`. Each subsection uses numbered steps + bash code blocks.

**Key commands to cover (from RESEARCH.md §operators-guide gap analysis):**
- `quirk console enroll` — provision sensor, get bearer token
- `quirk sensor enroll <console_url> --segment <label> --api-token <token>` — write sensor.yaml
- `quirk sensor push` — run scan + push; spool if offline
- `quirk sensor merge` — produce unified CBOM + score
- `quirk sensor export-results` + `quirk console import-results` — air-gap path
- Windows: `pip install quirk-scanner[all]`, sensor.yaml path via platformdirs (`%APPDATA%\quirk\sensor.yaml`), PowerShell snippet

---

### `docs/UAT-SERIES.md` (config — MODIFIED, add Series 112)

**Analog:** `docs/UAT-SERIES.md` — Series 106 and Series 107 sections (lines 12367-12477) are the structural template for new single-UAT-item series.

**Series header pattern** (UAT-SERIES.md lines 12367-12378):
```markdown
## Series 106: Architecture Documentation (Phase 106 — v5.4)

**Requirement coverage:** ARCH-01, ARCH-02, ARCH-03, ARCH-04
**Phase:** 106 (architecture-documentation)

> No-code gating anchor for the **v5.4 Distributed On-Prem Scanner** milestone. ...

---
```

**UAT item pattern** (UAT-SERIES.md lines 12380-12421):
```markdown
### UAT-106-01: Architecture contract integrity + seam accuracy (ARCH-01..04) — Automated

**ID:** UAT-106-01
**Requirement:** ARCH-01, ARCH-02, ARCH-03, ARCH-04
**Type:** Automated

**Prerequisites:** ...

**Steps:**
1. ...

**Expected:** ...

**Pass Criteria:**
- ...

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:**   **Tester:**
**Notes:**

---
```

Series 112 requires UAT items for: compose-config validation (Automated), topology static test (Automated), live E2E run (Human), datetime.utcnow() fix (Automated), operators-guide §8 presence (Automated) — per RESEARCH.md §UAT-SERIES.md. Five items: UAT-112-01 through UAT-112-05.

---

### `quirk/cli/sensor_cmd.py` (utility, transform — MODIFIED, single-line fix)

**Analog:** `quirk/notify/dispatcher.py` lines 23, 208 (exact datetime idiom match)

**Current broken pattern** (sensor_cmd.py line 39 and line 296):
```python
# line 39 — import (needs timezone added):
from datetime import datetime

# line 296 — deprecated call:
"pushed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
```

**Target pattern — project idiom** (dispatcher.py lines 23, 208):
```python
# line 23 — import with timezone:
from datetime import datetime, timezone

# line 208 — wire-format UTC ISO string (naive storage uses .replace(tzinfo=None), not applicable here):
attempted_at=datetime.now(timezone.utc).replace(tzinfo=None),
```

For `pushed_at` (a wire-format ISO string, not SQLite storage), the correct replacement is:
```python
# line 39 — import fix:
from datetime import datetime, timezone

# line 296 — replacement:
"pushed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
```

This matches the `quirk/merge/scan.py:178` idiom confirmed in RESEARCH.md §datetime.utcnow fix.

---

### `tests/test_distributed_topology.py` (test, file-I/O — NEW)

**Analog:** `tests/test_chaos_lab_image_pinning.py` (lines 1-43 — full file, PyYAML parse pattern)

**Test module header + path-resolution pattern** (test_chaos_lab_image_pinning.py lines 1-17):
```python
"""CHAOS-05: Compose-file image-pin policy gate.
...
"""
from pathlib import Path

import yaml

COMPOSE_FILE = (
    Path(__file__).resolve().parent.parent
    / "quantum-chaos-enterprise-lab"
    / "docker-compose.yml"
)
```

For the topology test, use the same `Path(__file__).resolve().parent.parent / "quantum-chaos-enterprise-lab"` root and define `DIST_COMPOSE` and `E2E_SCRIPT` constants.

**YAML parse + service iteration pattern** (test_chaos_lab_image_pinning.py lines 27-43):
```python
def test_every_image_is_pinned():
    data = yaml.safe_load(COMPOSE_FILE.read_text())
    violations = []
    for name, svc in (data.get("services") or {}).items():
        if not isinstance(svc, dict):
            continue
        img = svc.get("image")
        if img is None:
            # build-only service; pinning enforced via Dockerfile FROM directive
            continue
        ...
    assert not violations, ...
```

The topology test follows this exact shape: `yaml.safe_load(DIST_COMPOSE.read_text())`, iterate `data.get("services") or {}`, iterate `data.get("networks") or {}`.

**Subprocess compose-config test pattern** (from RESEARCH.md):
```python
import subprocess

def test_config_validates():
    result = subprocess.run(
        ["docker", "compose", "-f", str(DIST_COMPOSE), "config"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"compose config failed: {result.stderr}"
```

**Script text-order assertion pattern:**
```python
def test_e2e_script_enroll_push_merge_order():
    text = E2E_SCRIPT.read_text()
    ei = text.index("enroll")
    pi = text.index("push")
    mi = text.index("merge")
    assert ei < pi < mi, "e2e script must reference enroll before push before merge"
```

---

## Shared Patterns

### CHAOS-05 Image-Pin Policy
**Source:** `quantum-chaos-enterprise-lab/lab.sh` lines 77-109 (`_validate_pinned_tags`)
**Source:** `tests/test_chaos_lab_image_pinning.py`
**Apply to:** `docker-compose.distributed.yml` (all `image:` keys must be pinned), `sensor.Dockerfile` (`FROM` must be `python:3.11.12-slim` not bare `3.11-slim`)

The `_validate_pinned_tags` function checks `${COMPOSE_FILE}` — the `distributed)` arm sets `COMPOSE_FILE` before calling it, so the same gate runs for the distributed compose.

### Project datetime Idiom
**Source:** `quirk/notify/dispatcher.py` line 23 (import) + line 208 (usage)
**Apply to:** `quirk/cli/sensor_cmd.py` lines 39 and 296

Two forms exist in the project:
- Wire-format UTC ISO string: `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")`
- SQLite naive datetime storage: `datetime.now(timezone.utc).replace(tzinfo=None)`

`pushed_at` is a wire-format field — use the first form.

### PyYAML + pathlib Compose-Parse Test Pattern
**Source:** `tests/test_chaos_lab_image_pinning.py` lines 1-43
**Apply to:** `tests/test_distributed_topology.py`

Every compose-file test in this project uses `yaml.safe_load(COMPOSE_FILE.read_text())` with a `Path(__file__).resolve().parent.parent / "quantum-chaos-enterprise-lab"` root. No `open()` calls; no relative paths.

### lab.sh `compose` Helper
**Source:** `quantum-chaos-enterprise-lab/lab.sh` lines 51-54
**Apply to:** `lab.sh distributed)` arm

The `compose` helper reads `PROJECT_NAME`, `COMPOSE_FILE`, and `PROFILE_ARGS` from outer scope. The `distributed)` arm must reassign `COMPOSE_FILE` and `PROJECT_NAME` before any `compose` call. `PROFILE_ARGS` can remain empty for the distributed topology (no `--profile` flags).

### UAT Series Section Template
**Source:** `docs/UAT-SERIES.md` lines 12367-12424 (Series 106 pattern)
**Apply to:** Series 112 addition in `docs/UAT-SERIES.md`

Each series has: `## Series NNN: <Name> (Phase NNN — v5.4)` H2 → requirement coverage + phase metadata block → `> ` prose summary callout → `---` divider → individual `### UAT-NNN-NN:` items with ID/Requirement/Type/Prerequisites/Steps/Expected/Pass Criteria/Result/Date/Tester/Notes.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `quantum-chaos-enterprise-lab/README.md` (distributed section) | config | — | The README has no prior distributed-topology section; the expected_results_v4.md oracle format is the closest structural model but is a different document type |

---

## Metadata

**Analog search scope:** `quantum-chaos-enterprise-lab/`, `quirk/cli/`, `quirk/notify/`, `tests/`, `docs/`, `Dockerfile`, `pyproject.toml`
**Files read:** 13
**Pattern extraction date:** 2026-05-25

### Hostname-Alias Trap (FLAGGED)

CONTEXT.md D-01 notes a dependency: if QUIRK records the resolved IP (not the configured host string) on `CryptoEndpoint.host`, the MERGE-03 validation breaks because both sensors would still record different IPs (`10.10.0.10` vs `10.20.0.10`). The RESEARCH.md workaround configures both sensor `config.yaml` files to scan `10.10.0.10:443` regardless of their actual Docker network IP. The planner must confirm this assumption holds before writing the oracle pass criteria in `expected_results_distributed.md`.
