# Phase 115: Live-UAT Stabilization + Lab Testability — Research

**Researched:** 2026-05-27
**Domain:** Python CLI bug-fix + Docker lab config (no new dependencies)
**Confidence:** HIGH — all findings verified by direct source inspection

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Re-enrolling an already-provisioned sensor/console is an idempotent success — prints "already enrolled" notice and exits 0 **without minting a new token**.
- **D-02:** Detection is a **pre-check by `sensor_id`** before insert; existing `IntegrityError` rollback retained as backstop. Mirror in both `console_cmd._cmd_enroll` and `sensor_cmd` enroll.
- **D-03:** `--rotate` / `--force` re-mint path is **deferred** (out of scope).
- **D-04:** Eliminate phantom `scanned_at=None` / port-0 rows **at the source** — stop the emission before push, not filter downstream.
- **D-05:** Add regression test asserting merged console output contains no endpoint with `scanned_at` null or port 0.
- **D-06:** `scheduler_cmd` **drops** `--target` / `--output` from the `python -m run_scan` subprocess. Do **not** widen `run_scan.py`'s arg surface.
- **D-07:** STAB-03 regression test goes in the **same file** as the SENSOR-05 fixes (`tests/test_scheduler_posix_fixes.py`).
- **D-08:** Ship `cmvp_cache.json` by declaring `quirk/compliance/*.json` under `[tool.setuptools.package-data]`; prefer `importlib.resources` for the load path.
- **D-09:** Weak-TLS target on **segment-b** only (reachable only by sensor-b).
- **D-10:** Reuse the existing `nginx/legacy/nginx.conf` image/pattern from the main `docker-compose.yml`.
- **D-11:** Same change updates `lab.sh`, `expected_results_distributed.md`, and `README.md`.

### Claude's Discretion

- Exact "already enrolled" message strings and whether they go to stdout vs stderr.
- The precise source-level location of the phantom-row emission and the cleanest fix.
- The exact weak-TLS service name, container name, and port; the resulting oracle finding rows.

### Deferred Ideas (OUT OF SCOPE)

- `--rotate` / `--force` explicit token re-mint.
- Widening `run_scan.py` to accept `--target` / `--output`.
- Weak-SSH distributed target / segment-a placement.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STAB-01 | `quirk console enroll` idempotent; no duplicate rows, no error on re-run | Pre-check in `_cmd_enroll` before two-row insert; mirror in `sensor_cmd` |
| STAB-02 | `cmvp_cache.json` ships in wheel (package-data); no warning on merge | Add `quirk/compliance/*.json` to `[tool.setuptools.package-data]` |
| STAB-03 | Scheduler drops `--target`/`--output`; regression test in `test_scheduler_posix_fixes.py` | Remove two args from cmd list at ~L161; test asserts cmd contains neither |
| STAB-04 | Phantom `email_scanner`/`broker_scanner` rows eliminated at source | Filter advisory rows from `_read_scan_endpoints` before push envelope |
| LAB-01 | Weak-TLS target on segment-b; lab.sh + oracle + README updated same change | Add `tls-weak-b` service to `docker-compose.distributed.yml` segment-b network |

</phase_requirements>

---

## Summary

Phase 115 is a pure stabilization + lab wiring phase with no new external dependencies
and no schema changes. All five defects are narrow, well-bounded code-only edits verified
by direct source inspection.

**STAB-01** requires a `sensor_id` pre-check in `console_cmd._cmd_enroll` before the
two-row `Sensor` + `SensorToken` insert, and an identical pre-check in
`sensor_cmd._cmd_enroll` (which writes `sensor.yaml` — the idempotency here means
silently overwriting with the same values). The existing `IntegrityError` backstop is
retained.

**STAB-02** is a one-line `pyproject.toml` edit. `cmvp.py` uses a source-tree-relative
`Path(__file__).parent / "cmvp_cache.json"` path, which works during development but
silently breaks in a wheel install because `.json` files are not picked up by
`setuptools.packages.find` (which collects `.py` only). The fix is declaring
`"quirk/compliance"` glob under `[tool.setuptools.package-data]` and migrating the load
path to `importlib.resources`.

**STAB-03** is a two-line removal in `scheduler_cmd.py` at ~L161, removing `--target`
and `--output` from the subprocess `cmd` list. `run_scan.py`'s top-level argparser
(~L589) does not declare either argument; the scheduler passing them causes
`unrecognized arguments` and a non-zero exit.

**STAB-04** is the key investigation result: the phantom rows originate in
`_emit_missing_extra_advisory()` in `run_scan.py` (L148–163), which writes
`CryptoEndpoint(host="email_scanner", port=0, scanned_at=None, ...)` rows to the local
scan DB when `[motion]` extra is absent. `_read_scan_endpoints` in `sensor_cmd.py`
(L431–440) reads **all** rows from that DB without filtering, so advisory rows ride the
push envelope into the console DB. The fix is filtering out rows with
`scan_error_category == "missing_extra"` (or `protocol == "ADVISORY"`) in
`_read_scan_endpoints` before they enter the envelope.

**LAB-01** adds a `tls-weak-b` service to `docker-compose.distributed.yml` on the
`segment-b` network, modelled exactly on the `tls-legacy` service in
`docker-compose.yml` (nginx:1.28.0 + `nginx/legacy/nginx.conf`). No new image or
certificate is needed. The same change updates `lab.sh` (if it enumerates distributed
services), `expected_results_distributed.md` (new weak-TLS finding row), and
`README.md`.

**Primary recommendation:** Fix all five items as four separate focused plans (STAB-01
idempotency, STAB-02 CMVP packaging, STAB-03 scheduler, STAB-04 phantom rows) plus one
lab plan (LAB-01). Each plan is independently verifiable.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Enroll idempotency (STAB-01) | CLI layer (`console_cmd`, `sensor_cmd`) | DB (SQLite sensors table) | Duplicate guard lives in CLI before insert; DB IntegrityError is backstop only |
| CMVP packaging (STAB-02) | Build / packaging (`pyproject.toml`) | Runtime (`cmvp.py` load path) | Root cause is missing `package-data` declaration; load path is secondary fix |
| Scheduler arg fix (STAB-03) | CLI layer (`scheduler_cmd.py`) | — | Subprocess arg list is entirely in `scheduler_cmd._dispatch_schedule` |
| Phantom-row elimination (STAB-04) | Sensor push path (`sensor_cmd._read_scan_endpoints`) | Scanner emission (`run_scan._emit_missing_extra_advisory`) | Filter at the push boundary; advisory rows are legitimate for local-only runs |
| Weak-TLS lab target (LAB-01) | Docker lab (`docker-compose.distributed.yml`) | Lab docs (`lab.sh`, oracle, README) | Service config + no-drift documentation updates |

---

## Standard Stack

This phase installs **no new packages**. All changes are code edits and a
`pyproject.toml` declaration update. The standard stack is the existing project stack.

### No Package Legitimacy Audit Required

No new packages are added; the Package Legitimacy Gate does not apply.

---

## Architecture Patterns

### STAB-01: Enroll Idempotency Pattern

**Current flow (`console_cmd._cmd_enroll`, L136–237):**

```
sensor_id → mint raw_token + token_hash → open Session →
  db.add(Sensor(...))  # flush triggers UNIQUE on sensor_id
  db.add(SensorToken(...))
  db.commit()
  # On IntegrityError: rollback + print "ERROR: sensor_id already enrolled" + sys.exit(1)
→ print raw_token to stdout
```

**Required flow (D-01, D-02):**

```
sensor_id → open Session →
  existing = db.query(Sensor).filter(Sensor.sensor_id == sensor_id).first()
  if existing:
    print "INFO: sensor already enrolled — no new token minted" (stderr)
    sys.exit(0)   # idempotent success, exit 0, NO token printed
  → mint raw_token + token_hash → [existing two-row insert]
  # IntegrityError backstop retained for race window
```

**Key point:** The idempotent-success path must NOT print a raw token (D-01). If a
token is printed it implies the sensor.yaml should be updated — but no new token was
minted. The "already enrolled" message goes to stderr; exit 0.

**`sensor_cmd._cmd_enroll` idempotency (L206–279):**

`sensor_cmd._cmd_enroll` writes `sensor.yaml` locally — there is no DB insert here. The
idempotency question is: if `sensor.yaml` already exists, silently overwrite (same
credentials) or print "already configured"? Since `--api-token` may have changed and the
operator re-ran enroll to update, the safe behaviour per D-01 pattern is to detect
existing `sensor.yaml` and print a warning, then overwrite — or simply always overwrite
and print the existing message. The CONTEXT.md (D-02) says mirror the pre-check, so the
safest interpretation is: if `sensor.yaml` already exists with the same `sensor_id`,
print "already enrolled" and exit 0 without generating a new random hmac_key. This keeps
the sensor's push credentials stable across re-runs.

### STAB-02: CMVP Packaging Fix

**Current state (VERIFIED by source read):**

- `cmvp.py` L50: `_CACHE_PATH = Path(__file__).parent / "cmvp_cache.json"`
- This is a source-tree-relative path. In an editable install (`pip install -e .`) it
  resolves correctly. In a wheel install it resolves to the installed `.py` file's
  parent — which is the package directory inside site-packages, which contains
  `cmvp_cache.json` **only if** it was declared as package data.
- `pyproject.toml` L128: `quirk = ["reports/templates/*.j2", "config_template.yaml",
  "dashboard/static/**/*"]` — `compliance/*.json` is **absent**.

**Fix:**

1. `pyproject.toml` — add `"compliance/*.json"` (or `"compliance/cmvp_cache.json"`)
   to the `quirk` package-data list.
2. `cmvp.py` — migrate `_load_cache` to use `importlib.resources` so the load path
   is wheel-safe regardless of install mode (D-08).

**`importlib.resources` pattern (Python 3.9+, the project requires 3.11+):**

```python
# Replace:
_CACHE_PATH = Path(__file__).parent / "cmvp_cache.json"
data = json.loads(_CACHE_PATH.read_text())

# With:
from importlib.resources import files as _ir_files
_data_text = _ir_files("quirk.compliance").joinpath("cmvp_cache.json").read_text()
data = json.loads(_data_text)
```

The `_atomic_write_json` refresh path still writes to `_CACHE_PATH` (the source-tree
path). For refresh to work correctly in a wheel install the write path should also use
the resolved package path. However: the `refresh_cache` command is a developer/operator
tool run from a dev environment, not a wheel install concern. Keep `_CACHE_PATH` as the
write target; only the **read** path (in `_load_cache`) needs the `importlib.resources`
migration. [ASSUMED — this is a reasonable separation but should be validated against
the refresh workflow]

### STAB-03: Scheduler Arg Fix

**Current `scheduler_cmd.py` subprocess cmd at ~L153–167 (VERIFIED):**

```python
cmd = [sys.executable, "-m", "run_scan"]
if scan_config_path is not None:
    cmd += ["--config", scan_config_path]
cmd += [
    "--target",          # ← does NOT exist in run_scan.py argparser
    schedule.target,
    "--profile",
    schedule.profile or "balanced",
    "--output",          # ← does NOT exist in run_scan.py argparser
    str(output_dir),
]
```

**`run_scan.py` top-level argparser (VERIFIED):** Declares `--config`, `--targets-file`,
`--verbose`, `--progress`, `--profile`, `--discovery`, `--nmap-*`, `--safe-mode`,
`--rate-limit`, `--cache*`, `--resume*`, etc. **No `--target` and no `--output`.**

**Fix (D-06):**

```python
cmd = [sys.executable, "-m", "run_scan"]
if scan_config_path is not None:
    cmd += ["--config", scan_config_path]
cmd += [
    "--profile",
    schedule.profile or "balanced",
]
# NOTE: target + output_dir are driven by --config (cfg.target + cfg.output.directory).
# Do NOT add --target or --output — run_scan.py does not accept them.
```

The `output_dir` (computed from `cfg.output.directory`) already anchors the scan output
(SENSOR-05 Fix-1). The target comes from `config.yaml` that `--config` points to.
Dropping `--target` means the scheduler loses the ability to override the target for a
specific run **at the subprocess level**; this is intentional per D-06 (do not widen
run_scan's arg surface). If a schedule needs a different target than the config's
default, it must use a dedicated config file per schedule.

**Regression test placement (D-07):** `tests/test_scheduler_posix_fixes.py` is the
established home for static scheduler regression guards (source-analysis style tests
that grep the `.py` file). The new test should be added to that module — no class
needed, all existing tests are module-level functions. The test should assert:

1. `"--target"` is NOT in the scheduler cmd list when a config is provided.
2. `"--output"` is NOT in the scheduler cmd list when a config is provided.
3. A scheduler dispatch with a real config exits 0 (subprocess smoke test using
   monkeypatched `Popen`).

### STAB-04: Phantom Row Root Cause and Fix

**VERIFIED root-cause trace:**

1. `run_scan.py:L1969–1973`: When `cfg.connectors.enable_email is True` and the
   `[motion]` extra is absent (sslyze not installed), `_emit_missing_extra_advisory`
   is called.
2. `run_scan.py:L148–163`: `_emit_missing_extra_advisory` appends to `error_endpoints`:
   ```python
   CryptoEndpoint(
       host="email_scanner",   # not a real host
       port=0,
       protocol="ADVISORY",
       scan_error="optional extra [motion] not installed",
       scan_error_category="missing_extra",
       # scanned_at: NOT SET → None
   )
   ```
3. Same for `broker_scanner` at ~L2012.
4. These rows are persisted to the local scan DB (via `_flush_stage_endpoints` and the
   bulk persist at run end).
5. `sensor_cmd._read_scan_endpoints` (L431–440) queries ALL rows:
   ```python
   return session.query(CryptoEndpoint).all()
   ```
   No filter for `scan_error_category` or `protocol == "ADVISORY"`.
6. The advisory rows enter `_build_envelope` → `findings` list → compressed payload →
   pushed to console.
7. Console `_ingest_envelope` (L538–561) persists them verbatim: `host="email_scanner"`,
   `port=0`, `scanned_at=None`.

**Fix location (D-04 — at the source):**

`sensor_cmd._read_scan_endpoints` should filter advisory rows before they enter the
push envelope:

```python
def _read_scan_endpoints(db_path: str) -> list:
    """Return scan CryptoEndpoint rows, excluding advisory/error-only rows.

    Filters out rows with scan_error_category='missing_extra' (advisory sentinels
    emitted when an optional scanner extra is absent — not real scan findings).
    These rows carry host=<scanner_name>, port=0, scanned_at=None and must not
    be pushed to the console or appear in merged output.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from quirk.models import CryptoEndpoint

    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        return (
            session.query(CryptoEndpoint)
            .filter(CryptoEndpoint.scan_error_category != "missing_extra")
            .all()
        )
```

**Why at `_read_scan_endpoints` and not at `_emit_missing_extra_advisory`:** Advisory
rows serve a legitimate purpose in local-only runs — `trends.py` uses
`scan_error_category` to exclude them from regression counts (run_scan.py D-15 comment).
Removing them from the push path is correct; removing them from the local DB would break
local trends tracking.

**Alternative filter:** `CryptoEndpoint.protocol != "ADVISORY"` also works since all
advisory rows use `protocol="ADVISORY"`. Either predicate is sufficient; filtering on
`scan_error_category` is more precise and directly maps to the advisory-row semantic.

**Regression test for D-05:**

The test should mock two sensors pushing advisory-containing scan DBs to a console and
assert that after `merge_scan`, no `CryptoEndpoint` in the merged union has
`scanned_at=None` or `port=0`. This can be a unit-level test using an in-memory SQLite
DB.

### LAB-01: Weak-TLS Distributed Target

**Current `docker-compose.distributed.yml` structure (VERIFIED):**

Segment-b network (`10.20.0.0/24`) has one service: `tls-target-b`
(ip `10.20.0.10`, alias `crypto.internal`, nginx:1.28.0, modern config).
sensor-b joins segment-b and console-net.

**Existing weak-TLS pattern in `docker-compose.yml` (VERIFIED):**

```yaml
tls-legacy:
  image: nginx:1.28.0
  volumes:
    - ./nginx/legacy/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./certs:/etc/nginx/certs:ro
  ports:
    - "8443:443"
```

`nginx/legacy/nginx.conf` configures `ssl_protocols TLSv1 TLSv1.1 TLSv1.2` and
`ssl_ciphers HIGH:MEDIUM:!aNULL:!MD5`.

**New service to add to `docker-compose.distributed.yml` (D-09, D-10):**

```yaml
  # -----------------------------------------------------------------------
  # WEAK-TLS TARGET — Segment B only
  # Models the main lab's tls-legacy service (TLS 1.0/1.1 + weak-ish ciphers).
  # Reachable only by sensor-b (segment-b network isolation).
  # LAB-01: exercises Phase 111 per-segment score/filter end-to-end.
  # -----------------------------------------------------------------------
  tls-weak-b:
    image: nginx:1.28.0
    volumes:
      - ./nginx/legacy/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    expose:
      - "443"
    networks:
      segment-b:
        ipv4_address: "10.20.0.20"
        # No crypto.internal alias — weak target is a distinct host from the modern target
```

**Port:** Internal `expose: 443` (no host-port binding needed — sensor-b scans it
internally). Static IP `10.20.0.20` on segment-b (avoids DHCP assignment variance).

**Scan config update:** `sensor-config.yaml` is currently mounted into both sensors
with target `crypto.internal:443`. For sensor-b to also scan the weak target, the
config needs to add `10.20.0.20:443` (or a DNS alias) to its target list. Alternatively
a separate `sensor-config-b.yaml` can be provided and mounted into sensor-b only — this
keeps sensor-a's config unchanged and preserves segment-a isolation semantics.

**`lab.sh` impact:** The `distributed` arm of `lab.sh` does not enumerate individual
services — it delegates to `docker compose -f docker-compose.distributed.yml`. Adding
a new service requires no `lab.sh` change to the `ALL_PROFILES` list (distributed does
not use profiles). However, `lab.sh distributed status` and `lab.sh distributed logs`
use generic `compose ps` / `compose logs` and will automatically include `tls-weak-b`.
The `distributed-e2e.sh` script needs an update if the e2e workflow should push
weak-TLS findings from sensor-b.

**`expected_results_distributed.md` update (D-11):** Add `tls-weak-b` to the Services
table, and add expected TLS findings rows (TLS 1.0/1.1 detected, legacy cipher, no PFS
on weak cipher). Document the Phase 111 per-segment filter validation (sensor-b segment
sees weak-TLS findings; sensor-a does not).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Package resource loading | `Path(__file__).parent / "file"` in wheel | `importlib.resources.files()` | Wheel-safe; `__file__` path is unreliable in zipimport / editable installs |
| DB idempotency check | Try-except-only guard | Pre-check + IntegrityError backstop | Race window is small; pre-check gives a clean "already enrolled" path |

---

## Runtime State Inventory

This phase is not a rename/refactor. However, the e2e lab runs with a persistent Docker
volume `console-data` that stores the SQLite DB. After STAB-01 is fixed, re-running
`./lab.sh distributed e2e` without `docker compose down -v` is safe because enroll is
idempotent. No data migration is required.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `console-data` Docker volume with `quirk.db`; may contain phantom email/broker rows from prior runs | `docker compose down -v` once before running the fixed e2e (clears stale advisory rows) |
| Live service config | None beyond Docker Compose | No action |
| OS-registered state | None | None |
| Secrets/env vars | `QUIRK_API_TOKEN=lab-shared-token` in docker-compose.distributed.yml; per-sensor token printed by enroll | Code rename only — token values unchanged |
| Build artifacts | sensor.Dockerfile image built from repo root | Rebuild via `./lab.sh distributed up` after code changes |

---

## Common Pitfalls

### Pitfall 1: STAB-01 — Printing a token on idempotent enroll
**What goes wrong:** If the pre-check exits 0 but the raw token was already minted
earlier in the function, the token gets printed even though no new DB row was written.
**Why it happens:** Token minting currently precedes the insert attempt; moving the
pre-check after minting means a stale token value is emitted.
**How to avoid:** Move the pre-check to **before** token minting. If already enrolled,
print message + exit 0 before `secrets.token_urlsafe(32)` is called.

### Pitfall 2: STAB-02 — `importlib.resources` write path in `refresh_cache`
**What goes wrong:** `_atomic_write_json(_CACHE_PATH, new_cache)` still uses the
`Path(__file__).parent` path. In a wheel install this is the site-packages directory —
which may be read-only.
**Why it happens:** The refresh path is a dev/operator tool; it runs from a dev checkout
where the path is writable. The symptom only appears if someone runs `quirk cmvp refresh`
from a wheel install.
**How to avoid:** Keep `_CACHE_PATH` as the write target for now (it works in the common
dev-checkout use case). Document that `quirk cmvp refresh` must be run from a source
checkout. If wheel-install refresh support is needed, it becomes a separate work item.
[ASSUMED — acceptable given refresh is a developer tool]

### Pitfall 3: STAB-04 — Filtering on `protocol != "ADVISORY"` misses future advisory types
**What goes wrong:** A future advisory type uses a different protocol label; it slips
through the filter.
**Why it happens:** Protocol string is used informally for many scanner-specific values.
**How to avoid:** Filter on `scan_error_category != "missing_extra"` (the dedicated
category field) rather than on protocol. This is more semantically precise.

### Pitfall 4: STAB-03 — Scheduler still fails when no `scan_config_path` is set
**What goes wrong:** If `scan_config_path is None` (schedule has no associated config),
the fix removes `--target` and `--output` but `run_scan.py` also has no default target.
**Why it happens:** The scheduler `schedule.target` field was the only target source
when no config was provided.
**How to avoid:** The scheduler should require `scan_config_path` to be non-None (a
schedule must have a `--config`). Add a guard: if `scan_config_path is None`, log an
error and mark the run as `failed` rather than attempting to launch run_scan with no
target.

### Pitfall 5: LAB-01 — No DNS alias for `tls-weak-b` means sensor-config.yaml must reference IP
**What goes wrong:** sensor-b's scan config references `crypto.internal:443` only; the
weak target at `10.20.0.20` is not scanned.
**Why it happens:** `sensor-config.yaml` is a single file mounted into both sensors.
**How to avoid:** Either add `10.20.0.20` to the shared config's target list (both
sensors try it; sensor-a cannot reach it and gets a timeout/refused, which is benign),
or mount a separate `sensor-config-b.yaml` into sensor-b with both targets. The
separate-config approach is cleaner for segment isolation semantics.

### Pitfall 6: STAB-01 `sensor_cmd` idempotency — `sensor.yaml` already exists
**What goes wrong:** Re-running `quirk sensor enroll` overwrites `sensor.yaml` with a
new `hmac_key`, breaking existing pushes that rely on the old key.
**Why it happens:** `_cmd_enroll` in `sensor_cmd` unconditionally writes sensor.yaml.
**How to avoid:** Pre-check: if `sensor.yaml` exists and `sensor_id` matches the
`--sensor-id` arg, print "already enrolled — sensor.yaml unchanged" and exit 0 without
regenerating `hmac_key`. If `--sensor-id` differs, treat as a new enrollment.

---

## Code Examples

### STAB-01: Pre-check in `console_cmd._cmd_enroll`

```python
# Source: quirk/cli/console_cmd.py _cmd_enroll (verified by source read)
# ADD BEFORE the token-minting block (before secrets.token_urlsafe):

with Session() as db:
    existing = db.query(Sensor).filter(Sensor.sensor_id == sensor_id).first()
    if existing is not None:
        print(
            f"INFO: sensor already enrolled — sensor_id={sensor_id}",
            file=sys.stderr,
        )
        print(f"sensor_id: {sensor_id}", file=sys.stderr)
        # D-01: no new token minted; exit 0
        return  # WR-04 pattern: return normally rather than sys.exit(0)
```

### STAB-02: `pyproject.toml` package-data addition

```toml
# Source: pyproject.toml L127-128 (verified by source read)
[tool.setuptools.package-data]
quirk = [
    "reports/templates/*.j2",
    "config_template.yaml",
    "dashboard/static/**/*",
    "compliance/*.json",    # STAB-02: cmvp_cache.json + any future compliance JSON
]
```

### STAB-02: `importlib.resources` load path in `cmvp.py`

```python
# Replace _load_cache's read path (verified current: _CACHE_PATH.read_text())
from importlib.resources import files as _ir_files

def _load_cache(force_reload: bool = False) -> dict:
    global _CACHE
    if _CACHE is not None and not force_reload:
        return _CACHE
    _text = _ir_files("quirk.compliance").joinpath("cmvp_cache.json").read_text(encoding="utf-8")
    data = json.loads(_text)
    # ... existing assertion validation unchanged ...
    _CACHE = data
    return _CACHE
```

### STAB-03: Scheduler cmd fix

```python
# Source: quirk/cli/scheduler_cmd.py ~L153 (verified by source read)
cmd = [sys.executable, "-m", "run_scan"]
if scan_config_path is not None:
    cmd += ["--config", scan_config_path]
cmd += [
    # "--target", schedule.target,   # REMOVED — run_scan does not accept --target
    "--profile",
    schedule.profile or "balanced",
    # "--output", str(output_dir),   # REMOVED — run_scan does not accept --output
]
# Target + output dir are driven by --config (cfg.target + cfg.output.directory per SENSOR-05)
```

### STAB-03: Regression test addition (in `test_scheduler_posix_fixes.py`)

```python
# Add to tests/test_scheduler_posix_fixes.py (same module as SENSOR-05 guards)
def test_scheduler_cmd_drops_target_and_output():
    """STAB-03 regression: scheduler subprocess cmd must not contain --target or --output."""
    src = _strip_comments(SCHEDULER_SRC.read_text())
    # Confirm neither flag appears as a string literal in the cmd construction
    # (source-analysis gate — mirrors SENSOR-05 Fix 1 style)
    assert '"--target"' not in src or "# REMOVED" in src, (
        "scheduler_cmd.py still passes --target to run_scan — regression of STAB-03"
    )
    assert '"--output"' not in src or "# REMOVED" in src, (
        "scheduler_cmd.py still passes --output to run_scan — regression of STAB-03"
    )
```

Note: the source-analysis approach (grep-style) mirrors the SENSOR-05 Fix-1 test style
already in this file. A complementary integration test using `FakePopen` (from
`test_scheduler_cmd.py`) that checks `cmd` at dispatch time is also appropriate.

### STAB-04: Filter in `_read_scan_endpoints`

```python
# Source: quirk/cli/sensor_cmd.py L431 (verified by source read)
def _read_scan_endpoints(db_path: str) -> list:
    """Open scan SQLite DB and return non-advisory CryptoEndpoint rows.

    Excludes rows with scan_error_category='missing_extra' (advisory sentinels
    written by _emit_missing_extra_advisory when an optional scanner is absent).
    These are local-only diagnostic rows, not real findings to push.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from quirk.models import CryptoEndpoint

    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        return (
            session.query(CryptoEndpoint)
            .filter(
                (CryptoEndpoint.scan_error_category != "missing_extra")
                | CryptoEndpoint.scan_error_category.is_(None)
            )
            .all()
        )
```

**Note on NULL filter:** SQLite `!= "missing_extra"` does NOT match NULL rows (SQL
three-valued logic). The explicit `IS NULL` or clause is required to include rows with
no `scan_error_category` set (the normal finding rows). [VERIFIED — standard SQLAlchemy
behaviour]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Path(__file__).parent` for data files | `importlib.resources.files()` | Python 3.9+ / PEP 451 | Wheel-safe for installed packages |
| Shared console token for all sensors | Per-sensor opaque Bearer tokens | Phase 113 (v5.5) | Each sensor has distinct push credential |
| Manual merge only | Auto-merge on full-check-in | Phase 114 (v5.5) | Distributed e2e no longer needs manual merge step |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `refresh_cache` write path (`_CACHE_PATH`) is acceptable to keep as source-tree path (wheel-install refresh not a supported scenario) | STAB-02 pitfalls | If users run `quirk cmvp refresh` from a wheel install, the write fails; low risk given it's a developer tool |
| A2 | Filtering `scan_error_category != "missing_extra"` is the right predicate for STAB-04 (vs `protocol != "ADVISORY"`) | STAB-04 code | If future advisory row types use a different category, this filter may be too narrow; low risk |
| A3 | A separate `sensor-config-b.yaml` (mounted only to sensor-b) is the cleaner approach for adding the weak-TLS target to sensor-b's scan scope | LAB-01 | If shared config is preferred, both sensors attempt to scan `10.20.0.20` — sensor-a will time out, which is benign but adds noise |

---

## Open Questions (RESOLVED)

> All three resolved by the accepted recommendations and reflected in the plans:
> O-Q1 (STAB-03 fail-fast) → Plan 115-02 Task 2; O-Q2 (export-results filter) →
> Plan 115-01 Task 3; O-Q3 (separate sensor-config-b.yaml) → Plan 115-03 Task 1.

1. **STAB-03 — Schedules without a config file** — RESOLVED: fail-fast (Plan 02 T2)
   - What we know: removing `--target` from the cmd means run_scan has no target when `scan_config_path is None`
   - What's unclear: should the scheduler fail-fast on schedules with no config, or silently mark the run failed?
   - Recommendation: fail-fast (log error + mark run `failed`) if `scan_config_path is None`; do not attempt to launch run_scan with no target

2. **STAB-04 — Export-results path also uses `_read_scan_endpoints`**
   - What we know: `_cmd_export_results` also calls `_read_scan_endpoints` at L727
   - What's unclear: should advisory rows also be excluded from air-gap `.qpush` exports?
   - Recommendation: yes — apply the same filter in `_cmd_export_results`; advisory rows have no meaning on the console side

3. **LAB-01 — Distributed e2e script update scope**
   - What we know: `distributed-e2e.sh` currently scans only `crypto.internal:443` via the sensor-config.yaml
   - What's unclear: should the e2e script explicitly validate that weak-TLS findings appear in the push, or is it enough for the target to be reachable?
   - Recommendation: update `sensor-config-b.yaml` to include the weak target; update the e2e step 2 to mount `sensor-config-b.yaml` to sensor-b and verify the merged output includes both modern and weak-TLS findings from sensor-b

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All code changes | Assumed (project requirement) | 3.11+ | — |
| Docker Compose | LAB-01 validation | Not verified in research session | — | Manual review of compose YAML |
| `importlib.resources` | STAB-02 load path | Python stdlib (3.9+) | Built-in | `Path(__file__).parent` (dev-only fallback) |
| SQLAlchemy | STAB-04 filter | Already installed | Already in requirements | — |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_scheduler_posix_fixes.py tests/test_console_cmd.py tests/test_sensor_cmd.py -x` |
| Full suite command | `pytest -m 'not slow' -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STAB-01 | Console enroll idempotent, exits 0, no duplicate row | unit | `pytest tests/test_console_cmd.py -k enroll -x` | Wave 0 — add test |
| STAB-01 | Sensor enroll idempotent, sensor.yaml unchanged | unit | `pytest tests/test_sensor_cmd.py -k enroll -x` | Wave 0 — add test |
| STAB-02 | `cmvp_cache.json` loads via `importlib.resources` | unit | `pytest tests/ -k cmvp -x` | Existing + extend |
| STAB-03 | Scheduler cmd list contains no `--target`/`--output` | static/unit | `pytest tests/test_scheduler_posix_fixes.py -x` | Extend existing file |
| STAB-04 | `_read_scan_endpoints` excludes advisory rows | unit | `pytest tests/ -k read_scan_endpoints -x` | Wave 0 — add test |
| STAB-04 | Merged output has zero `scanned_at=None` or `port=0` endpoints (D-05) | unit | `pytest tests/ -k phantom_row -x` | Wave 0 — add test |
| LAB-01 | `docker-compose.distributed.yml` valid YAML, `tls-weak-b` present | static | `python -c "import yaml; yaml.safe_load(open('...'))"` | Wave 0 — add test |

### Sampling Rate

- **Per task commit:** `pytest tests/test_scheduler_posix_fixes.py tests/test_console_cmd.py tests/test_sensor_cmd.py -x -q`
- **Per wave merge:** `pytest -m 'not slow' -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_console_cmd.py` — add `test_enroll_idempotent` (STAB-01)
- [ ] `tests/test_sensor_cmd.py` — add `test_enroll_idempotent_sensor_yaml` (STAB-01)
- [ ] `tests/test_scheduler_posix_fixes.py` — add `test_scheduler_cmd_drops_target_and_output` (STAB-03)
- [ ] `tests/` — add `test_read_scan_endpoints_excludes_advisory` (STAB-04)
- [ ] `tests/` — add `test_merge_no_phantom_rows` (STAB-04, D-05)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (partial) | `sensor_id` pre-check; no new user-controlled inputs |
| V6 Cryptography | no | cmvp.py change is packaging only, not crypto logic |

### Known Threat Patterns for this Phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Duplicate enroll flooding | DoS | Pre-check + IntegrityError backstop prevents repeated inserts |
| Advisory row injection via push | Tampering | STAB-04 fix eliminates at source; ingest path validates FK + dedup, not content |

No new security surface is introduced. The STAB-01 fix reduces attack surface by
preventing repeated enrollment tokens from being printed to stdout.

---

## Sources

### Primary (HIGH confidence — verified by direct source read)

- `quirk/cli/console_cmd.py` L136–237 — `_cmd_enroll` current implementation (STAB-01)
- `quirk/cli/sensor_cmd.py` L206–279, L431–440 — sensor enroll + `_read_scan_endpoints` (STAB-01, STAB-04)
- `quirk/cli/scheduler_cmd.py` L130–167 — subprocess cmd builder (STAB-03)
- `run_scan.py` L148–163, L589–643 — `_emit_missing_extra_advisory` + argparser (STAB-03, STAB-04)
- `quirk/compliance/cmvp.py` L50 — `_CACHE_PATH` definition (STAB-02)
- `pyproject.toml` L127–128 — `[tool.setuptools.package-data]` current contents (STAB-02)
- `quantum-chaos-enterprise-lab/docker-compose.distributed.yml` — segment topology (LAB-01)
- `quantum-chaos-enterprise-lab/docker-compose.yml` L14–24 — tls-legacy service pattern (LAB-01)
- `quantum-chaos-enterprise-lab/nginx/legacy/nginx.conf` — weak-TLS nginx config (LAB-01)
- `quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh` — e2e workflow (LAB-01)
- `quantum-chaos-enterprise-lab/expected_results_distributed.md` — current oracle (LAB-01)
- `tests/test_scheduler_posix_fixes.py` — SENSOR-05 regression test home (STAB-03 placement)

### Secondary (MEDIUM confidence)

- Python docs: `importlib.resources.files()` — Python 3.9+ API, project requires 3.11+ so no backport needed

---

## Metadata

**Confidence breakdown:**

- STAB-01 (enroll idempotency): HIGH — code path verified line by line
- STAB-02 (CMVP packaging): HIGH — `pyproject.toml` and `cmvp.py` load path verified
- STAB-03 (scheduler args): HIGH — both the offending args and the argparser surface verified
- STAB-04 (phantom rows): HIGH — complete call chain traced: `_emit_missing_extra_advisory` → local DB → `_read_scan_endpoints` → push envelope → console ingest
- LAB-01 (weak-TLS lab): HIGH — existing service pattern reused verbatim; no new image

**Research date:** 2026-05-27
**Valid until:** 2026-06-27 (stable codebase; 30-day window)
