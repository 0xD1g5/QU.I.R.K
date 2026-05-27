# Phase 115: Live-UAT Stabilization + Lab Testability — Pattern Map

**Mapped:** 2026-05-27
**Files analyzed:** 12 (8 modified, 2 extended tests, 2 new test functions)
**Analogs found:** 12 / 12

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/cli/console_cmd.py` (`_cmd_enroll`) | CLI handler | request-response | Self (L136–237) — extend with pre-check | exact |
| `quirk/cli/sensor_cmd.py` (`_cmd_enroll`) | CLI handler | request-response | `console_cmd._cmd_enroll` — mirror pattern | role-match |
| `quirk/cli/sensor_cmd.py` (`_read_scan_endpoints`) | data accessor | CRUD | Self (L431–440) — add SQLAlchemy filter | exact |
| `quirk/cli/scheduler_cmd.py` | CLI handler | request-response | Self (L130–179) — remove two args | exact |
| `quirk/compliance/cmvp.py` (`_load_cache`) | utility | file-I/O | `quirk/qramm/model_meta.py` (similar JSON load) | role-match |
| `pyproject.toml` (package-data) | config | — | Self (L127–128) — add one glob | exact |
| `tests/test_scheduler_posix_fixes.py` | test | — | Self (L1–71) — add new function | exact |
| `tests/test_console_cmd.py` | test | — | Self (L48–80) — add idempotency test | exact |
| `tests/test_sensor_cmd.py` | test | — | Self (L19–59) — add idempotency test | exact |
| `tests/` (new phantom-row test) | test | — | `tests/test_console_cmd.py` enroll helper pattern | role-match |
| `quantum-chaos-enterprise-lab/docker-compose.distributed.yml` | config | — | `docker-compose.yml` L13–24 (`tls-legacy` service) | exact |
| `quantum-chaos-enterprise-lab/sensor-config-b.yaml` | config | — | `sensor-config.yaml` (same schema) | exact |

---

## Pattern Assignments

### `quirk/cli/console_cmd.py` — `_cmd_enroll` (STAB-01)

**Analog:** Same file, L136–239. Add a pre-check block before token minting.

**Current token-minting block** (L175–178) — the pre-check must appear BEFORE these lines:

```python
# quirk/cli/console_cmd.py L175-178 — CURRENT (pre-check must precede these)
raw_token = secrets.token_urlsafe(32)
token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
now = datetime.now(timezone.utc).replace(tzinfo=None)
```

**Current Session/insert block** (L189–214) — shows the IntegrityError backstop to retain:

```python
# quirk/cli/console_cmd.py L189-214 — retain as backstop
with Session() as db:
    try:
        db.add(Sensor(sensor_id=sensor_id, ...))
        db.flush()
        db.add(SensorToken(sensor_id=sensor_id, token_hash=token_hash, ...))
        db.commit()
    except IntegrityError:
        db.rollback()
        print("ERROR: sensor_id already enrolled", file=sys.stderr)
        sys.exit(1)
```

**Pre-check to INSERT** (new, before L175):

```python
# Open a read-only session to check for an existing sensor_id BEFORE minting.
# D-01: if already enrolled, exit 0 without printing a token.
# WR-04: return rather than sys.exit(0) so atexit handlers and unit tests work.
db_path = _default_db_path()
engine = init_db(db_path)
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
with Session() as db:
    existing = db.query(Sensor).filter(Sensor.sensor_id == sensor_id).first()
    if existing is not None:
        print(f"INFO: sensor already enrolled — sensor_id={sensor_id}", file=sys.stderr)
        print(f"sensor_id: {sensor_id}", file=sys.stderr)
        return  # D-01: no new token minted; WR-04: return, not sys.exit(0)
```

**Idempotent message style** — mirrors the existing fixed-string pattern (T-109-03):

```python
# EXISTING fixed-string pattern at L213 — the "already enrolled" notice must
# match this T-109 convention (no exception text, no dynamic values in the label):
print("ERROR: sensor_id already enrolled", file=sys.stderr)
```

---

### `quirk/cli/sensor_cmd.py` — `_cmd_enroll` (STAB-01 mirror)

**Analog:** `console_cmd._cmd_enroll` for the idempotency concept; `sensor_cmd._cmd_enroll` itself (L206–279) for the write-side pattern.

**Current write-always block** (L271–278) — the pre-check must precede `_write_sensor_config`:

```python
# quirk/cli/sensor_cmd.py L260-279 — CURRENT (always writes)
sensor_cfg = {
    "console_url": console_url,
    "sensor_id": sensor_id,
    "segment": args.segment,
    "engagement": args.engagement,
    "sensor_version": quirk.__version__,
    "hmac_key": hmac_key,
    "console_api_token": api_token,
    "allow_internal_console": allow_internal,
}
_write_sensor_config(config_path, sensor_cfg)
print(f"Enrollment token (shown once — save it now):\n{raw_token}", flush=True)
print("WARNING: this token will not be shown again.", file=sys.stderr)
print(f"Sensor config written to: {config_path}", file=sys.stderr)
sys.exit(0)
```

**Pre-check to INSERT** (new, before token minting at ~L248):

```python
# D-02 / Pitfall 6: pre-check before generating hmac_key.
# If sensor.yaml already exists and sensor_id matches, exit 0 without
# regenerating credentials — prevents breaking existing pushes.
config_path: str = args.config or _default_sensor_yaml_path()
if os.path.exists(config_path):
    try:
        existing_cfg = yaml.safe_load(Path(config_path).read_text()) or {}
        if existing_cfg.get("sensor_id") == getattr(args, "sensor_id", None):
            print(
                f"INFO: sensor already enrolled — sensor.yaml unchanged ({config_path})",
                file=sys.stderr,
            )
            sys.exit(0)
    except Exception:
        pass  # Malformed sensor.yaml — fall through to fresh enroll
```

---

### `quirk/cli/sensor_cmd.py` — `_read_scan_endpoints` (STAB-04)

**Analog:** Same file, L431–440. Add a SQLAlchemy filter predicate.

**Current implementation** (L431–440):

```python
# quirk/cli/sensor_cmd.py L431-440 — CURRENT (returns ALL rows including advisory)
def _read_scan_endpoints(db_path: str) -> list:
    """Open the scan SQLite DB produced by the local scan and return CryptoEndpoint rows."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from quirk.models import CryptoEndpoint

    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        return session.query(CryptoEndpoint).all()
```

**Required filter** (RESEARCH L579–599, STAB-04 fix):

```python
# STAB-04: filter advisory sentinel rows before they enter the push envelope.
# Advisory rows have scan_error_category="missing_extra", host=<scanner_name>,
# port=0, scanned_at=None — not real findings.
# NULL guard: SQLite != does NOT match NULL rows (SQL 3VL); explicit IS NULL
# or-clause required to include normal finding rows with no category set.
return (
    session.query(CryptoEndpoint)
    .filter(
        (CryptoEndpoint.scan_error_category != "missing_extra")
        | CryptoEndpoint.scan_error_category.is_(None)
    )
    .all()
)
```

---

### `quirk/cli/scheduler_cmd.py` (STAB-03)

**Analog:** Same file, L130–179. Remove two args from the cmd list.

**Current (broken) cmd construction** (L153–167):

```python
# quirk/cli/scheduler_cmd.py L153-167 — CURRENT (passes unsupported args)
cmd = [
    sys.executable,
    "-m",
    "run_scan",
]
if scan_config_path is not None:
    cmd += ["--config", scan_config_path]
cmd += [
    "--target",          # run_scan.py does NOT accept --target
    schedule.target,
    "--profile",
    schedule.profile or "balanced",
    "--output",          # run_scan.py does NOT accept --output
    str(output_dir),
]
```

**Required fix** (D-06 — drop --target and --output):

```python
# STAB-03: remove --target and --output; target + output come from --config.
# Guard: if scan_config_path is None, no target is available — fail fast.
cmd = [sys.executable, "-m", "run_scan"]
if scan_config_path is not None:
    cmd += ["--config", scan_config_path]
else:
    run.status = "failed"
    db.commit()
    logger.error("Schedule %s has no config file; cannot determine target — skipping", schedule.name)
    return
cmd += [
    "--profile",
    schedule.profile or "balanced",
]
# NOTE: target + output_dir are driven by --config (cfg.target + cfg.output.directory).
# Do NOT add --target or --output — run_scan.py does not accept them (STAB-03).
```

**Verified argparser surface** (run_scan.py ~L589 — does not include `--target`/`--output`):

```
--config, --targets-file, --verbose, --progress, --profile, --discovery,
--nmap-*, --safe-mode, --rate-limit, --cache*, --resume*
```

---

### `quirk/compliance/cmvp.py` — `_load_cache` (STAB-02)

**Analog:** Same file, L50 and L75–100. Migrate the read path from `Path(__file__).parent` to `importlib.resources`.

**Current load path** (L50 + L80):

```python
# quirk/compliance/cmvp.py L50 — CURRENT (source-tree-relative, breaks in wheel)
_CACHE_PATH = Path(__file__).parent / "cmvp_cache.json"

# quirk/compliance/cmvp.py L75-80 — current _load_cache uses _CACHE_PATH
def _load_cache(force_reload: bool = False) -> dict:
    global _CACHE
    if _CACHE is not None and not force_reload:
        return _CACHE
    data = json.loads(_CACHE_PATH.read_text())
```

**Required importlib.resources migration** (D-08, RESEARCH L189–197):

```python
# Replace the _CACHE_PATH.read_text() call in _load_cache with:
from importlib.resources import files as _ir_files

def _load_cache(force_reload: bool = False) -> dict:
    global _CACHE
    if _CACHE is not None and not force_reload:
        return _CACHE
    _text = _ir_files("quirk.compliance").joinpath("cmvp_cache.json").read_text(encoding="utf-8")
    data = json.loads(_text)
    # ... existing schema assertion validation unchanged ...
    _CACHE = data
    return _CACHE
```

**Keep `_CACHE_PATH` for the write path** (RESEARCH Pitfall 2): `_atomic_write_json(_CACHE_PATH, ...)` in `refresh_cache` stays unchanged — refresh is a developer-only tool run from a source checkout.

---

### `pyproject.toml` — package-data (STAB-02)

**Analog:** Same file, L127–128.

**Current state** (L127–128):

```toml
[tool.setuptools.package-data]
quirk = ["reports/templates/*.j2", "config_template.yaml", "dashboard/static/**/*"]
```

**Required addition** (D-08):

```toml
[tool.setuptools.package-data]
quirk = [
    "reports/templates/*.j2",
    "config_template.yaml",
    "dashboard/static/**/*",
    "compliance/*.json",    # STAB-02: cmvp_cache.json + any future compliance JSON
]
```

---

### `tests/test_scheduler_posix_fixes.py` — STAB-03 regression test

**Analog:** Same file, L34–70. Mirrors the existing static source-analysis style exactly.

**Existing test structure** to copy:

```python
# tests/test_scheduler_posix_fixes.py L1-13 — module header + constants (reuse as-is)
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEDULER_SRC = REPO_ROOT / "quirk" / "cli" / "scheduler_cmd.py"

def _strip_comments(src: str) -> str:
    # ... tokenize-based comment stripper (L16-31) ...

def test_output_dir_anchored():
    src = _strip_comments(SCHEDULER_SRC.read_text())
    assert 'Path("output/scheduled")' not in src, "..."
    assert "cfg.output.directory" in src, "..."
```

**New test function to add** (D-07, same module-level function style — no class):

```python
def test_scheduler_cmd_drops_target_and_output():
    """STAB-03 regression: scheduler subprocess cmd must not pass --target or --output.

    run_scan.py does not accept either argument; passing them causes
    'unrecognized arguments' and a non-zero exit (verified by source read).
    """
    src = _strip_comments(SCHEDULER_SRC.read_text())
    assert '"--target"' not in src, (
        "scheduler_cmd.py still passes --target to run_scan — regression of STAB-03"
    )
    assert '"--output"' not in src, (
        "scheduler_cmd.py still passes --output to run_scan — regression of STAB-03"
    )
```

---

### `tests/test_console_cmd.py` — STAB-01 idempotency test

**Analog:** Same file, `_enroll_default` helper (L48–80) and test structure (L88–104).

**Existing helper to reuse** (L48–80) — directly provisions a `Sensor` row:

```python
# tests/test_console_cmd.py L48-80 — _enroll_default: provisions a Sensor row
def _enroll_default(sensor_id: str, segment: str = "air-gap") -> None:
    from quirk.dashboard.api.deps import _default_db_path
    from quirk.db import init_db
    from quirk.models import Sensor
    engine = init_db(_default_db_path())
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        if db.query(Sensor).filter(Sensor.sensor_id == sensor_id).first() is None:
            db.add(Sensor(sensor_id=sensor_id, segment=segment, ...))
            db.commit()
    finally:
        db.close()
```

**New test to add**:

```python
def test_enroll_idempotent_console(capsys):
    """STAB-01: re-enrolling an already-provisioned sensor_id exits 0
    without printing a bearer token and without creating duplicate rows.
    """
    sensor_id = str(uuid.uuid4())
    _enroll_default(sensor_id, segment="test-seg")

    from quirk.cli.console_cmd import _cmd_enroll

    class Args:
        sensor_id = sensor_id  # same ID as already enrolled
        segment = "test-seg"
        engagement = None
        config = "config.yaml"

    # Must NOT raise SystemExit; must return normally (WR-04)
    _cmd_enroll(Args())

    captured = capsys.readouterr()
    # D-01: no raw token printed to stdout on idempotent path
    assert "Bearer" not in captured.out
    # INFO message goes to stderr
    assert "already enrolled" in captured.err
    assert sensor_id in captured.err
```

---

### `tests/test_sensor_cmd.py` — STAB-01 sensor idempotency test

**Analog:** Same file, `test_enroll_writes_sensor_yaml` (L19–59).

**Existing test structure** to mirror:

```python
# tests/test_sensor_cmd.py L19-59 — writes sensor.yaml, checks keys
def test_enroll_writes_sensor_yaml(tmp_path, monkeypatch):
    sensor_yaml = tmp_path / "sensor.yaml"
    mock_result = MagicMock(); mock_result.ok = True
    import quirk.cli.sensor_cmd as sensor_cmd_mod
    monkeypatch.setattr(sensor_cmd_mod, "validate_external_url", lambda *a, **kw: mock_result)
    from quirk.cli.sensor_cmd import _cmd_enroll
    class Args:
        console_url = "https://console.example"
        segment = "dmz"; engagement = None
        config = str(sensor_yaml); api_token = "test-api-token-abc"
    with pytest.raises(SystemExit) as exc_info:
        _cmd_enroll(Args())
    assert exc_info.value.code == 0
    # ... key assertions ...
```

**New test to add**:

```python
def test_enroll_idempotent_sensor_yaml(tmp_path, monkeypatch, capsys):
    """STAB-01 / Pitfall 6: re-running enroll with the same sensor_id must not
    regenerate hmac_key, must exit 0, and must print 'already enrolled' to stderr.
    """
    sensor_yaml = tmp_path / "sensor.yaml"
    mock_result = MagicMock(); mock_result.ok = True
    import quirk.cli.sensor_cmd as sensor_cmd_mod
    monkeypatch.setattr(sensor_cmd_mod, "validate_external_url", lambda *a, **kw: mock_result)
    from quirk.cli.sensor_cmd import _cmd_enroll

    sid = str(uuid.uuid4())

    class Args:
        console_url = "https://console.example"
        segment = "dmz"; engagement = None
        config = str(sensor_yaml); api_token = "tok1"; sensor_id = sid
        allow_internal_console = False

    # First enroll
    with pytest.raises(SystemExit) as exc_info:
        _cmd_enroll(Args())
    assert exc_info.value.code == 0
    first_cfg = yaml.safe_load(sensor_yaml.read_text())
    first_hmac = first_cfg["hmac_key"]

    # Second enroll — same sensor_id
    with pytest.raises(SystemExit) as exc_info:
        _cmd_enroll(Args())
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "already enrolled" in captured.err

    # hmac_key must be unchanged (Pitfall 6)
    second_cfg = yaml.safe_load(sensor_yaml.read_text())
    assert second_cfg["hmac_key"] == first_hmac
```

---

### `tests/` — phantom-row tests (STAB-04, D-05)

**Analog:** `tests/test_console_cmd.py` DB-setup helper pattern (L48–80); `test_sensor_cmd.py` monkeypatch style.

**Two new test functions** (can live in `tests/test_sensor_cmd.py` or a new `tests/test_stab04_phantom_rows.py`):

```python
def test_read_scan_endpoints_excludes_advisory(tmp_path):
    """STAB-04: _read_scan_endpoints must not return rows with
    scan_error_category='missing_extra' (advisory sentinels).
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from quirk.db import init_db
    from quirk.models import CryptoEndpoint
    from quirk.cli.sensor_cmd import _read_scan_endpoints

    db_path = str(tmp_path / "scan.db")
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        db.add(CryptoEndpoint(
            host="email_scanner", port=0, protocol="ADVISORY",
            scan_error_category="missing_extra", scanned_at=None,
        ))
        db.add(CryptoEndpoint(
            host="10.0.0.1", port=443, protocol="tls",
            scan_error_category=None, scanned_at=datetime.now(),
        ))
        db.commit()

    rows = _read_scan_endpoints(db_path)
    assert all(r.scan_error_category != "missing_extra" for r in rows)
    assert any(r.host == "10.0.0.1" for r in rows)


def test_no_phantom_rows_in_merged_output(tmp_path):
    """STAB-04 D-05 regression: after push+merge, merged DB must contain
    zero CryptoEndpoint rows with scanned_at=None or port=0.
    """
    # Uses in-memory SQLite + _ingest_envelope to verify merged state.
    # See RESEARCH §STAB-04 for full call-chain trace.
    # ... build envelope without advisory rows; ingest; assert ...
```

---

### `quantum-chaos-enterprise-lab/docker-compose.distributed.yml` (LAB-01)

**Analog:** Same file (L54–65) — `tls-target-b` service structure for network placement; `docker-compose.yml` (L18–24) — `tls-legacy` service for image/volume/config.

**Existing `tls-target-b` service** (L54–65) — shows the segment-b network pattern to copy:

```yaml
# docker-compose.distributed.yml L54-65 — tls-target-b (modern TLS, segment-b)
tls-target-b:
  image: nginx:1.28.0
  volumes:
    - ./nginx/modern/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./certs:/etc/nginx/certs:ro
  expose:
    - "443"
  networks:
    segment-b:
      ipv4_address: "10.20.0.10"
      aliases:
        - crypto.internal
```

**Existing `tls-legacy` service** (docker-compose.yml L18–24) — the weak-TLS image/volume pattern to reuse:

```yaml
# docker-compose.yml L18-24 — tls-legacy (TLS 1.0/1.1 + weak-ish ciphers)
tls-legacy:
  image: nginx:1.28.0
  volumes:
    - ./nginx/legacy/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./certs:/etc/nginx/certs:ro
  ports:
    - "8443:443"
```

**New `tls-weak-b` service** (combine the two patterns — D-09, D-10):

```yaml
# WEAK-TLS TARGET — Segment B only (LAB-01)
# Reuses tls-legacy image/config from docker-compose.yml (D-10).
# No host-port binding — sensor-b scans it internally on segment-b.
# No crypto.internal alias — distinct from the modern tls-target-b.
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
```

**`nginx/legacy/nginx.conf`** (already present at `quantum-chaos-enterprise-lab/nginx/legacy/nginx.conf`) — no new file needed. Configures `ssl_protocols TLSv1 TLSv1.1 TLSv1.2` and `ssl_ciphers HIGH:MEDIUM:!aNULL:!MD5`.

---

### `quantum-chaos-enterprise-lab/sensor-config-b.yaml` (LAB-01, D-09 / A3)

**Analog:** `sensor-config.yaml` (same schema, already in the lab dir).

**Existing `sensor-config.yaml`** (full file) — copy and extend for sensor-b:

```yaml
# sensor-config.yaml — current shared config (both sensors use this)
targets:
  fqdns:
    - crypto.internal   # resolves per-segment via DNS alias
  cidrs: []
  include_ips: []
  exclude_ips: []
```

**New `sensor-config-b.yaml`** — adds the weak-TLS target IP (D-09 / Pitfall 5):

```yaml
# sensor-config-b.yaml — sensor-b only; extends shared config with weak-TLS target
# Mounted into sensor-b only (keeps sensor-a config unchanged, preserving
# segment-a isolation — sensor-a cannot reach 10.20.0.20).
targets:
  fqdns:
    - crypto.internal   # segment-b DNS alias → 10.20.0.10 (modern TLS target)
  cidrs: []
  include_ips:
    - "10.20.0.20"      # LAB-01: weak-TLS target (tls-weak-b, port 443)
  exclude_ips: []
```

**`docker-compose.distributed.yml` sensor-b volume mount update** — change from shared `sensor-config.yaml` to `sensor-config-b.yaml`:

```yaml
# Before (L120):
      - ./sensor-config.yaml:/quirk/sensor-config.yaml:ro
# After:
      - ./sensor-config-b.yaml:/quirk/sensor-config.yaml:ro
```

---

### `quantum-chaos-enterprise-lab/lab.sh` (LAB-01 no-drift check)

**Analog:** Same file, `distributed` arm (L216–267). The `distributed` subcommand uses `docker-compose.distributed.yml` without profile flags — no `ALL_PROFILES` change is needed. `distributed status` and `distributed logs` use generic `compose ps` / `compose logs -f`, so `tls-weak-b` is automatically included.

**No change required** to `lab.sh` for the new service — confirmed by RESEARCH §LAB-01:

```bash
# lab.sh L222-224 — distributed arm delegates generically; no service enumeration
COMPOSE_FILE="$(dirname "$0")/docker-compose.distributed.yml"
PROJECT_NAME="quirk-dist"
PROFILE_ARGS=""  # no --profile flags for distributed topology
```

**`distributed-e2e.sh` update required** — sensor-b must scan the weak target:

```bash
# scripts/distributed-e2e.sh L115-121 — CURRENT sensor-b push
${DC} exec -T sensor-b \
  quirk sensor enroll "${CONSOLE_URL}" --segment segment-b \
  --sensor-id sensor-b \
  --api-token "${CONSOLE_SHARED_TOKEN}" \
  --allow-internal-console
${DC} exec -T sensor-b \
  quirk sensor push --scan-config /quirk/sensor-config.yaml

# AFTER (sensor-b now mounts sensor-config-b.yaml):
${DC} exec -T sensor-b \
  quirk sensor push --scan-config /quirk/sensor-config.yaml
# (no change to push command — the mounted config file now includes the weak target)
```

---

### `quantum-chaos-enterprise-lab/expected_results_distributed.md` (LAB-01, D-11)

**Analog:** Same file — existing Services table (L49–56) and Expected E2E Outcome table (L88–99).

**Services table addition** (after `tls-target-b` row):

```markdown
| `tls-weak-b` | `nginx:1.28.0` | `segment-b` | `10.20.0.20` on segment-b | — (expose 443 only) | — | Weak-TLS target for sensor-b (TLS 1.0/1.1 + legacy ciphers); LAB-01 |
```

**New oracle section** (add after MERGE-03 Validation section):

```markdown
### LAB-01: Per-Segment Weak-TLS Filter Validation

sensor-b scans both `crypto.internal:443` (modern TLS) and `10.20.0.20:443`
(weak TLS, TLS 1.0/1.1 + legacy ciphers). sensor-a does NOT join segment-b
and cannot reach `10.20.0.20` — segment isolation is preserved.

| Expected Finding (sensor-b only) | Value |
|----------------------------------|-------|
| `host` | `10.20.0.20` (or configured FQDN) |
| `port` | 443 |
| `tls_version` | TLS 1.0 or TLS 1.1 (reported as legacy protocol) |
| `cipher_suite` | HIGH:MEDIUM legacy cipher (e.g., AES128-SHA) |
| `quantum_risk` | elevated (legacy protocol penalty) |

sensor-a merged output: zero rows with `host=10.20.0.20`
sensor-b merged output: one or more rows with `host=10.20.0.20`, `scanned_at` non-null
```

---

## Shared Patterns

### T-109 Fixed-String Error Convention
**Source:** `quirk/cli/console_cmd.py` L213
**Apply to:** All new CLI error/info messages in `console_cmd._cmd_enroll` and `sensor_cmd._cmd_enroll`

```python
# EXISTING pattern — never stringify exceptions, use fixed strings only
print("ERROR: sensor_id already enrolled", file=sys.stderr)
# New pattern follows same style:
print(f"INFO: sensor already enrolled — sensor_id={sensor_id}", file=sys.stderr)
```

### WR-04 Return-Not-Exit Convention
**Source:** `quirk/cli/console_cmd.py` L237–238 (comment) and `tests/test_console_cmd.py` L103–104
**Apply to:** All new idempotent-success code paths in `console_cmd._cmd_enroll`

```python
# WR-04: return normally rather than sys.exit(0) so atexit handlers
# and unit tests work without SystemExit monkeypatching.
return  # not sys.exit(0)
```

### SQLAlchemy Session Context Manager
**Source:** `quirk/cli/console_cmd.py` L189; `quirk/cli/sensor_cmd.py` L438
**Apply to:** STAB-01 pre-check session, STAB-04 filter query

```python
with Session(engine) as session:
    # ... query ...
```

### Static Source-Analysis Test Style
**Source:** `tests/test_scheduler_posix_fixes.py` L34–70
**Apply to:** STAB-03 regression test in the same file

```python
def test_<name>():
    src = _strip_comments(SCHEDULER_SRC.read_text())
    assert '"--bad-flag"' not in src, "regression guard message"
```

### CHAOS-05 Image Pin Policy
**Source:** `quantum-chaos-enterprise-lab/docker-compose.distributed.yml` L36–38 (all services)
**Apply to:** `tls-weak-b` new service — must use `nginx:1.28.0`, not `:latest` or bare `nginx`

```yaml
image: nginx:1.28.0   # pinned minor/patch — CHAOS-05 requirement
```

---

## No Analog Found

All files have close analogs in the codebase. No file requires pattern invention from scratch.

---

## Metadata

**Analog search scope:** `quirk/cli/`, `quirk/compliance/`, `tests/`, `quantum-chaos-enterprise-lab/`, `pyproject.toml`
**Files directly read:** 14
**Pattern extraction date:** 2026-05-27
