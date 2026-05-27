# Expected Scanner Results — Distributed Multi-Segment Oracle

**Scope:** The distributed two-segment chaos-lab topology introduced in v5.4 Phase 112.
Invoked via `./lab.sh distributed up` and `./lab.sh distributed e2e`.
This is a separate compose file (`docker-compose.distributed.yml`); it is NOT covered by
`expected_results_v4.md` and does NOT add entries to `ALL_PROFILES` in `lab.sh`.

**Status:** Authoritative for distributed/MERGE-03 E2E validation (LAB-02, LAB-03).

**Schema:** One `## Topology: distributed` section covering all services.
Use `## Topology: distributed` as the cross-reference anchor from `README.md`.

---

## Topology: distributed

*Two isolated bridge networks (`segment-a`, `segment-b`) plus a console-only management
network (`console-net`). Reproduces the same-host:port-in-two-segments scenario (MERGE-03)
via a shared Docker DNS alias `crypto.internal` — each segment's TLS target carries the
alias on its OWN segment network, so per-network Docker DNS resolves `crypto.internal`
to each segment's own reachable target. Both sensors scan `crypto.internal:443` and
therefore record the same host:port string, differing only by `sensor_id` / `segment`.*

---

### Networks

Three distinct bridge networks are required. Docker enforces that no two user-defined
bridge networks may share a subnet on a single daemon (`invalid pool request: Pool
overlaps with other one on this address space`). The subnets below were chosen to be
distinct while keeping the last-octet assignment (`.10`) consistent across both segments
for operational clarity.

| Network | Subnet | Purpose |
|---------|--------|---------|
| `segment-a` | `10.10.0.0/24` | Segment A isolation — `tls-target-a` and `sensor-a` |
| `segment-b` | `10.20.0.0/24` | Segment B isolation — `tls-target-b` and `sensor-b` |
| `console-net` | `10.30.0.0/24` | Console-only management — `console`, `sensor-a`, `sensor-b` (push path) |

Each sensor joins **two** networks: its own segment (for DNS resolution and TLS scanning)
and `console-net` (for HTTP push to the console). No sensor joins the other sensor's
segment — this intentional isolation prevents cross-segment DNS resolution and mirrors
real-world network segmentation.

---

### Services

| Service | Image | Networks | Static IP | Published Port | Alias | Role |
|---------|-------|----------|-----------|----------------|-------|------|
| `tls-target-a` | `nginx:1.28.0` | `segment-a` | `10.10.0.10` on segment-a | — (expose 443 only) | `crypto.internal` (segment-a) | TLS target for sensor-a |
| `tls-target-b` | `nginx:1.28.0` | `segment-b` | `10.20.0.10` on segment-b | — (expose 443 only) | `crypto.internal` (segment-b) | TLS target for sensor-b |
| `sensor-a` | sensor.Dockerfile | `segment-a`, `console-net` | — | — | — | Scans `crypto.internal:443` on segment-a, pushes to console |
| `sensor-b` | sensor.Dockerfile | `segment-b`, `console-net` | — | — | — | Scans `crypto.internal:443` on segment-b, pushes to console |
| `console` | sensor.Dockerfile | `console-net` | — | `8512:8512` | — | Runs `quirk serve --host 0.0.0.0 --port 8512`; aggregates pushed findings |

**Image pin note:** `nginx:1.28.0` is a minor/patch pin per the chaos-lab Image Pin Policy.
`sensor.Dockerfile` pins `FROM python:3.11.12-slim` (CHAOS-05).

**Alias mechanism:** The `crypto.internal` alias is assigned at the *network* level in
`docker-compose.distributed.yml` — `tls-target-a` carries the alias on `segment-a` only;
`tls-target-b` carries it on `segment-b` only. Docker's per-network embedded DNS means
`sensor-a` (only on segment-a) resolves `crypto.internal` → `10.10.0.10`, and `sensor-b`
(only on segment-b) resolves `crypto.internal` → `10.20.0.10`. Neither sensor can resolve
the alias on the other segment.

---

### Expected E2E Outcome (MERGE-03)

The LAB-02 linchpin is confirmed in-code before building this topology:

- `quirk/scanner/tls_scanner.py:188-189` — sslyze path:
  `ep = CryptoEndpoint(host=host, ...)` records the **configured scan-target string verbatim**
- `quirk/scanner/tls_scanner.py:351-352` — fallback path, same pattern

Both sensors receive the same scan-target: `crypto.internal:443`. After the configured-host
string is passed to the scanner, `CryptoEndpoint.host` stores `"crypto.internal"` — not the
resolved Docker bridge IP — for both sensors. This is the invariant that makes MERGE-03
reproducible across real segmented networks: operators configure the same logical hostname
in both segments; the scanner records what it was told to scan.

**Authentication:** The lab runs with auth **ENABLED** using the v5.5 **per-sensor token
model**. Each sensor gets its own push credential from `quirk console enroll`. The
console's `QUIRK_API_TOKEN` governs operator/dashboard auth only; sensor pushes use the
per-sensor enrollment tokens placed in `console_api_token` in each sensor's `sensor.yaml`.

| Step | Expected Outcome |
|------|-----------------|
| `quirk console enroll --segment segment-a` | Prints per-sensor Bearer token (shown once); sensor row written to DB with `revoked_at=NULL` |
| `quirk console enroll --segment segment-b` | Prints distinct per-sensor Bearer token; second sensor row written to DB |
| Edit `sensor.yaml` on sensor-a host: set `console_api_token: <enrollment-token-a>` | `sensor.yaml` contains `sensor_id` (UUID), `segment: segment-a`, `console_api_token: <per-sensor-token-a>` |
| Edit `sensor.yaml` on sensor-b host: set `console_api_token: <enrollment-token-b>` | `sensor.yaml` contains distinct `sensor_id` (UUID), `segment: segment-b`, `console_api_token: <per-sensor-token-b>` |
| `quirk sensor push` on sensor-a | HTTP 200 from console (per-sensor token validated via SHA-256 hash match); scan results for `crypto.internal:443` persisted |
| `quirk sensor push` on sensor-b | HTTP 200 from console (per-sensor token validated); scan results for `crypto.internal:443` persisted |
| `quirk sensor merge` on console | Produces one merged CBOM + one readiness score across union of sensor endpoints |
| Merged CBOM component count for `crypto.internal:443` | **2 distinct `CryptoEndpoint` rows**, each with `host="crypto.internal"`, `port=443`, differing only by `sensor_id` |
| `coverage_warning` | `null` — both sensors have pushed within the merge window |

---

### MERGE-03 Validation

**Scenario:** The same logical host:port (`crypto.internal:443`) exists in two separate
network segments. A sensor in each segment scans it independently and pushes results to
a shared console. After merge, the CBOM must contain **two** distinct components — one
per sensor — not a de-duplicated single entry.

**Why the alias is the correct mechanism:**

A literal shared IP across two Docker bridge networks is architecturally impossible on a
single daemon host — Docker's IPAM pool check enforces non-overlapping subnets
(`invalid pool request: Pool overlaps with other one on this address space`). Therefore the
two TLS targets have different Docker-assigned IPs (`10.10.0.10` on segment-a,
`10.20.0.10` on segment-b), but both targets carry the DNS alias `crypto.internal` on
their respective segment networks.

From each sensor's perspective:
- `sensor-a` resolves `crypto.internal` → `10.10.0.10` (segment-a DNS, TLS scan succeeds)
- `sensor-b` resolves `crypto.internal` → `10.20.0.10` (segment-b DNS, TLS scan succeeds)

Both sensors run `quirk sensor push --target crypto.internal:443 --allow-self-signed`.
The scanner records `CryptoEndpoint(host="crypto.internal", port=443, sensor_id=<uuid>)`
(see `tls_scanner.py:188-189` and `:351-352`). The `host` field captures the *configured
scan-target string*, not the resolved IP, so both sensors record `host="crypto.internal"`.

**Key field: `sensor_id`**

The `CryptoEndpoint.sensor_id` column (`nullable=True`, added v5.4 D-08) holds the UUID
from each sensor's `sensor.yaml`. After merge, the console DB contains:

```
CryptoEndpoint(host="crypto.internal", port=443, sensor_id="<sensor-a-uuid>", segment="segment-a", ...)
CryptoEndpoint(host="crypto.internal", port=443, sensor_id="<sensor-b-uuid>", segment="segment-b", ...)
```

The `(sensor_id, host, port)` key uniqueness is preserved — these are two distinct rows,
not duplicates. The merge pipeline re-runs `compute_readiness_score()` and `build_cbom()`
over the union, producing **one score + one CBOM** that covers both segments.

**Single-host constraint note:** Because two identical IPs are impossible on one Docker
daemon, this lab uses the DNS alias mechanism as the canonical substitute. In production,
two physical segments may legitimately both contain `10.10.0.10:443` (or any other shared
RFC 1918 address); the segment label carried in `sensor_id` / `segment` is the correct
differentiator — not the IP alone. The alias approach in this lab faithfully models that
production pattern.

**Human-UAT gate:** The live enroll→push→merge run against the running containers is
human-UAT (deferred by design; see `distributed-e2e.sh` for the orchestration script).
Automated CI floor: `tests/test_distributed_topology.py` (10 static assertions).

---

### `lab.sh distributed` Commands

```bash
# Build images and start all distributed services
./lab.sh distributed up

# Run the enroll→push→merge orchestration end-to-end
./lab.sh distributed e2e

# Stop and remove distributed containers (leaves volumes)
./lab.sh distributed down

# Show running distributed container status
./lab.sh distributed status

# Tail logs for a specific distributed service
./lab.sh distributed logs <service>
# e.g.: ./lab.sh distributed logs console
#       ./lab.sh distributed logs sensor-a
```

The `all` command in `lab.sh` sweeps only `docker-compose.yml` (main compose). The
`distributed` arm uses `docker-compose.distributed.yml` and a separate project name
(`quirk-distributed`) to avoid name collisions with main-compose services.

---

### Verification Summary

| Check | Pass Criteria |
|-------|---------------|
| `docker compose -f docker-compose.distributed.yml config -q` | Exit 0 |
| `bash -n lab.sh` | Exit 0 (no syntax errors) |
| `bash -n scripts/distributed-e2e.sh` | Exit 0 |
| `pytest tests/test_distributed_topology.py` | 10 passed |
| Live e2e (human-UAT) | 2 enrollments succeed, 2 pushes HTTP 200, merge exits 0, CBOM has 2 `crypto.internal:443` components |
