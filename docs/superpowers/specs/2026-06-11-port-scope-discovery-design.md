# Port-Scope Control + Exhaustive Nmap Discovery — Design

**Date:** 2026-06-11
**Status:** Approved (design); pending implementation plan
**Author:** brainstorming session
**Routing:** GSD phase (feeds `/gsd-plan-phase` as spec input)

---

## Problem

Dashboard-initiated scans miss services because port coverage is hardcoded and
too narrow, and the failure is silent:

1. **GUI hardcodes 6 TLS ports.** `quirk/dashboard/api/routes/jobs.py::_write_job_config`
   writes a fixed `ports_tls: [443, 8443, 9443, 10443, 2222, 8000]`. The GUI has
   no way to express custom ports — `ScanSubmitRequest` only carries
   targets/profile/calibration/nmap.
2. **Nmap mode collapses to the same tiny set.** `run_scan.py` (~L1048) builds the
   nmap `-p` list via `select_nmap_port_list(cfg)`, which returns
   `cfg.scan.ports_tls` — i.e. the same 6 ports plus a fixed `[22, 80, 8080, 8000]`.
   "Nmap discovery" is therefore not exhaustive; it probes a subset.
3. **Empty scans masquerade as success.** When discovery finds nothing, the job
   completes with zero `CryptoEndpoint` rows. The dashboard's main views load
   `GET /api/scan/latest` *without* a scan_id, which anchors on
   `MAX(scanned_at)` — so the UI shows a stale prior scan, making it appear the
   scanner ignores new input. (Diagnosed 2026-06-11: a `127.0.0.1/24` lab scan
   probed only the hardcoded ports, found 0 open, and the UI kept showing a
   2026-05-10 session.)

The chaos lab publishes on high mapped ports (13443–13447, 15443, 15449, 16443,
24443, 24566, 21000–21002, 25671, 26379…), none of which overlap the hardcoded
set — so GUI lab scans always find nothing.

## Goals

- GUI can control which ports are scanned, including custom ranges.
- Nmap discovery can be genuinely exhaustive (top-1000 or all-65535) and feed
  *all* discovered open ports into fingerprinting.
- Sensible default that does not miss standard services in client environments.
- Lab is verifiable from the GUI immediately.

## Non-Goals

- Changing the stale-anchor UX in this work (tracked separately as a follow-up:
  the dashboard could banner "showing last successful scan: <date>" when a fresh
  scan returns zero endpoints). Noted here so it is not lost.
- UDP scanning. TCP only, consistent with current `nmap_to_targets(tcp_only=True)`.

## Key architecture finding

In **nmap mode**, `nmap_to_targets(open_ports, tcp_only=True)` already feeds every
open port nmap discovers into the fingerprinting stage — the scanner is **not**
limited to a subset. The only real constraint is the `-p` list nmap is *told* to
probe. So "make nmap exhaustive" is almost entirely about widening that `-p`
spec; the downstream scanner already takes whatever nmap finds.

In **builtin mode** there is no discovery — it blindly fingerprints every port in
`ports_tls` on every host. A wide list there is pathological, so exhaustive
scanning must route through nmap.

These are the two orthogonal axes the old design conflated:
- **Profile** (quick/standard/deep) = scanner *depth* per service.
- **Port scope** (new) = service *discovery breadth* (which ports are looked at).

## Design

### 1. Port-scope model

A new per-scan "port scope" flows from form → request → job config → discovery:

| Scope | Ports probed | Discovery mode | Speed |
|-------|-------------|---------------|-------|
| **Common TLS** | curated `CONSULTING_TLS_PORTS` (17 ports) | builtin or nmap | Fast, no nmap required |
| **Top 1000** (default) | nmap `--top-ports 1000` | forces nmap | Seconds–minutes/host |
| **All ports** | nmap `-p-` (all 65535) | forces nmap | Slow, exhaustive |
| **Custom** | user spec, e.g. `443,8000-9000,15449` | builtin if ≤ 25 discrete ports, else nmap | Depends |

Default scope is **Top 1000**.

### 2. Backend changes

- **`ScanSubmitRequest`** (`quirk/dashboard/api/schemas.py`): add
  `port_scope: Literal["common","top1000","all","custom"] = "top1000"` and
  `custom_ports: Optional[str] = None`. Validate `custom_ports` only when
  `port_scope == "custom"` (required + non-empty there, ignored otherwise).
- **New module `quirk/util/port_spec.py`**: `parse_port_spec(s: str) -> list[int]`
  supporting comma lists and `low-high` ranges, bounds 1–65535, dedup + sort, and
  an expansion cap (reject specs expanding beyond a max count — guards against
  `1-65535` typed into the custom box). Pure, unit-tested in isolation.
- **`jobs.py::_write_job_config`**: translate scope →
  - `common` → `cfg.scan.ports_tls = CONSULTING_TLS_PORTS`
  - `custom` → `cfg.scan.ports_tls = parse_port_spec(custom_ports)`
  - `top1000` / `all` → write a new `scan.nmap_port_scope` hint into the YAML
  - Auto-enable nmap when scope is `top1000`/`all`, or `custom` with > 25 ports.
- **`run_scan.py`** (nmap block ~L1048): replace the `select_nmap_port_list()`
  collapse with scope-aware arg construction:
  - `top1000` → append `--top-ports 1000` to nmap extra args
  - `all` → use `-p-`
  - explicit list → existing `-p <csv>` path
  - **Graceful failure:** if a wide scope (`top1000`/`all`) is requested but the
    nmap binary is absent, emit a clear advisory `CryptoEndpoint` and fail the job
    with an actionable message — do **not** silently fall back to a 6-port builtin
    scan (the current silent-empty trap).

### 3. GUI changes (`src/dashboard/src/pages/scan-new.tsx`)

- Add a **"Port scope"** `RadioGroup` (mirrors existing Profile/Calibration
  pattern) with the four options and short helper text per option.
- Conditionally render a **Custom ports** text input when "Custom" is selected,
  with inline validation feedback (reuse the existing error-display pattern).
- The existing **"Enable nmap discovery"** checkbox becomes auto-managed: when the
  selected scope forces nmap, show it checked + disabled with helper text
  ("Required for Top 1000 / All ports coverage").
- Extend `ScanSubmitRequest` TS type in `src/dashboard/src/types/api.ts`.
- Rebuild bundle (`npm run build`) + `npm run lint` before commit (dashboard CI
  gate; provider/hook split rule still applies).

### 4. Config change

Add to `./config.yaml` (the server-policy source `create_job` reads at
`jobs.py:232`):

```yaml
security:
  allow_internal_targets: true
```

Unblocks loopback/lab scans from the GUI. **Operator note:** set this back to
`false` on a machine that also scans untrusted client environments — internal
targeting should be off by default there.

## Data flow

```
scan-new.tsx (port_scope + custom_ports)
  → POST /api/jobs  (ScanSubmitRequest, validated)
    → create_job → _write_job_config
        → cfg.scan.ports_tls / cfg.scan.nmap_port_scope + enable_nmap
      → run_scan subprocess
        → nmap discovery (--top-ports / -p- / -p csv)
          → nmap_to_targets() — ALL open ports
            → fingerprint → classify → CryptoEndpoint rows
```

## Error handling

- Invalid `custom_ports` → 422 with a clear message (form shows inline error).
- Wide scope requested, nmap missing → job fails with advisory finding +
  actionable message (install nmap / pick Common TLS), never a silent empty scan.
- Over-cap custom spec → 422 rejected at validation.

## Testing

- `tests/test_port_spec.py` — unit tests for `parse_port_spec` (lists, ranges,
  bounds, dedup, over-cap rejection, malformed input).
- Backend: `_write_job_config` scope translation (common/custom/top1000/all →
  expected YAML + enable_nmap), schema validation of `ScanSubmitRequest`.
- nmap arg construction per scope (mock `run_nmap_discovery`).
- Frontend: scan-new renders selector, custom field toggles, forces-nmap states;
  vitest in `src/dashboard/src/pages/__tests__/`.
- Manual UAT: GUI scan of `127.0.0.1` Top 1000 against running chaos lab returns
  non-zero endpoints; Custom `15449,16443` finds those specific lab services.

## Mandatory phase-completion follow-ups (GSD)

- Obsidian phase note.
- `docs/UAT-SERIES.md` new test cases + sync to vault.
- `docs/configuration.md` / scan docs: document port-scope behavior.
- No chaos-lab profile change expected → `lab.sh`/expected-results untouched
  (verify during execution).
