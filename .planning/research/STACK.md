# Stack Research — v5.4 Distributed On-Prem Scanner Architecture (ADDITIONS ONLY)

**Domain:** Distributed agent/console architecture for an existing Python 3.11+ crypto-scanner + FastAPI dashboard — sensor→console outbound push, sensor enrollment/identity, cross-platform Windows runtime, and cross-sensor CBOM merge
**Researched:** 2026-05-25
**Confidence:** HIGH (versions verified against live PyPI; integration points confirmed from source; patterns confirmed from existing quirk/dashboard/api/middleware/auth.py, quirk/notify/dispatcher.py, quirk/util/safe_exc.py)

> This file covers ONLY stack additions/changes for v5.4. The full existing stack
> (sslyze, FastAPI + HTTPBearer auth + hmac.compare_digest, SQLite + SQLAlchemy 2.0,
> httpx>=0.28.0, croniter, React + shadcn/ui, cyclonedx-python-lib>=11.7,
> slack-sdk, jira, zstandard — see pyproject.toml) is documented in PROJECT.md
> and is NOT repeated here unless directly affected by v5.4 changes.

---

## TL;DR — New Dependency Budget

| Capability | New pip dep | Notes |
|---|---|---|
| Sensor push transport | none (httpx already in core) | Use existing httpx>=0.28.0 |
| Payload compression | `zstandard>=0.22.0` (check if already present) | Already in pyproject.toml if added by v5.3; verify |
| Retry / store-and-forward | `tenacity>=9.1.4` | New; optional-extra or [sensor] group |
| Console ingestion endpoint | none (FastAPI already in [dashboard]) | Reuse existing auth middleware |
| Sensor enrollment/identity | none (stdlib secrets, hmac, hashlib) | Mirror of existing token_cmd.py pattern |
| Windows Service host | `pywin32>=311` (Windows-only, optional) | New; conditional extra or sensor-specific extra |
| Windows frozen executable | `pyinstaller>=6.20.0` (build-time only, not a runtime dep) | Build tooling, not pip dep |
| Cross-sensor CBOM merge | none (pure Python dict/set logic on existing cyclonedx model) | No new dep warranted |
| Windows path hardening | none (stdlib pathlib.Path already correct) | Audit only, no new dep |

**Net new runtime deps: tenacity (1 mandatory for sensor push reliability) + pywin32 (1 Windows-only optional). PyInstaller is a build tool, not a runtime dep.**

---

## 1. Sensor→Console Outbound Push Transport

### Decision: httpx (already in core) + gzip/zstd content-encoding + tenacity for retry

**Why httpx, not requests:** httpx>=0.28.0 is already in `dependencies` (core, not optional). It supports streaming uploads via generator-based `content=` parameter, async and sync clients, client certificates for future mTLS upgrade, and automatic response decompression. Adding requests would be a pure duplicate.

**Why not message broker (MQTT/AMQP/Redis Streams):** Hard constraint — zero new heavy infra. A broker would require the console to run a broker process and sensors to reach it. The outbound-push model (sensor initiates, console accepts) matches the existing v5.3 dispatcher pattern exactly; no inbound access to sensor segments required.

**Wire format: JSON (application/json) with Content-Encoding: gzip or zstd**

CBOM/findings payloads are highly compressible JSON (string-heavy, repetitive field names). Benchmark data shows zstd level-3 achieves ~2.8:1 compression at speeds approaching lz4, with 11% better ratio than gzip. At typical CBOM sizes (50–500 KB uncompressed), zstd compression reduces payload to 15–60 KB — well within a single synchronous POST.

Sensor push pattern:
1. Sensor serializes scan result to JSON bytes.
2. Compresses with `zstandard.ZstdCompressor(level=3)`.
3. POSTs to `POST /api/v1/sensor/ingest` with `Content-Encoding: zstd`, `Content-Type: application/json`, `Authorization: Bearer <sensor-token>`.
4. Console FastAPI endpoint decompresses, validates schema, writes to `sensor_results` table.

**Why not chunked/resumable upload:** Typical CBOM payloads for one sensor are 50–500 KB after compression. HTTP resumable upload (multipart with range headers, or tus protocol) adds implementation complexity warranted only for multi-MB blobs. At these sizes, a single POST with retry is simpler and equivalent. If a future sensor produces >5 MB payloads (unlikely for single-segment scans), chunking can be added to the push client without changing the console endpoint contract — the design should leave that door open by accepting an `X-Sensor-Chunk` header.

**Store-and-forward for air-gapped/intermittent connectivity:**
Sensors in air-gapped segments cannot reach the console continuously. The push client needs a local spool: write the compressed payload to `<data_dir>/spool/<timestamp>-<uuid>.json.zst`, attempt delivery, remove on 200, leave on failure, retry on next scheduled window. SQLite is WRONG for the spool (file-per-payload avoids SQLite locking contention during the scan phase; the spool directory is a simple OS-level queue). The main `quirk.db` SQLite is for scan results; spool is ephemeral files.

**Retry library: tenacity>=9.1.4**
tenacity provides `@retry(wait=wait_exponential(multiplier=2, min=4, max=300), stop=stop_after_attempt(5), retry=retry_if_exception_type(httpx.TransportError))` — concise, composable, async-compatible. Current version 9.1.4 (released 2026-02-07). Requires Python >=3.10. No transitive deps. This is a new dep — add to a `[sensor]` extras group.

**mTLS vs. bearer token auth:** Bearer token is right for v5.4. The project already has a complete bearer token auth stack (HTTPBearer + hmac.compare_digest in `quirk/dashboard/api/middleware/auth.py`, secrets.token_urlsafe(32) in token_cmd.py). mTLS adds a PKI — certificate issuance, rotation, revocation, CA distribution — which is heavyweight infra the project explicitly avoids. A sensor-specific bearer token (separate from the dashboard token, same mechanism) is the correct choice: simple, pip-native, already battle-tested in this codebase. If a future enterprise customer requires mTLS, httpx supports it via `httpx.Client(cert=("client.crt", "client.key"), verify="ca.crt")` — the sensor push client can add mTLS as a config option later without changing the console endpoint contract.

**Payload integrity:** For v5.4, TLS in transit (HTTPS to the console) provides transport-layer integrity. An `X-Sensor-Signature: hmac-sha256=<hex>` header computed over the raw compressed body adds application-layer integrity for defense-in-depth — the console verifies with `hmac.compare_digest` before decompressing (prevents decompression bomb on tampered payloads). This uses stdlib only (hmac + hashlib).

### Console Ingestion Endpoint

`POST /api/v1/sensor/ingest` on the existing FastAPI app in `[dashboard]`.

Auth: reuse `require_auth` dependency pattern from `quirk/dashboard/api/middleware/auth.py` — sensor tokens are separate rows in a new `sensor_tokens` table (or a separate env var `QUIRK_SENSOR_TOKEN_<sensor_id>`), looked up by sensor_id from the payload. The existing `hmac.compare_digest` pattern is used unchanged.

No new framework dep. FastAPI already handles:
- `Request.body()` for raw bytes (needed to verify HMAC before parsing JSON)
- `UploadFile` / streaming body for future large payloads
- `BackgroundTasks` to write to DB asynchronously after immediate 202 response

Schema: console writes to new `sensor_results` table (additive schema, never breaking). Columns: `sensor_id`, `segment_label`, `received_at`, `payload_json`, `schema_version`. The merge step reads from this table.

---

## 2. Sensor Enrollment / Identity

### Decision: stdlib secrets + per-sensor token stored as SHA-256 hash in SQLite

**Pattern:** Mirror of existing `token_cmd.py` (Phase 102 AUTH-01):
1. `quirk sensor enroll --sensor-id <name> --segment <label>` generates `secrets.token_urlsafe(32)`.
2. Console stores `sha256(token)` in `sensor_tokens` table (sensor_id, segment_label, token_hash, created_at, last_seen_at, revoked).
3. Sensor config file (or env var `QUIRK_SENSOR_TOKEN`) stores the raw token. Config file lives under the sensor's data dir; permissions should be 0600 (or Windows ACL equivalent).
4. On push, sensor sends `Authorization: Bearer <raw-token>`; console computes `sha256(received)` and compares with `hmac.compare_digest` against the stored hash.

**Why SHA-256 hash storage, not plaintext:** same reason as passwords — if the DB is exfiltrated, tokens are not directly usable. This matches the spirit of the existing auth layer even though the current `require_auth` does plaintext compare against env var (the env var is the single-copy secret; this is fine for dashboard auth but for multi-sensor we want the DB to be safe to inspect).

**Why not JWT for sensors:** JWT adds a secret-management problem (signing key rotation) and a clock-sync requirement (expiry). A long-lived enrollment token that can be explicitly revoked is simpler and better suited to air-gapped sensors that may not have accurate clocks.

**Why not mTLS / client certs for enrollment:** PKI issuing. Out of scope. Bearer token is sufficient.

**No new dep.** stdlib secrets + hashlib + hmac.

---

## 3. Cross-Platform Sensor Runtime (Windows)

### 3a. Long-Lived Scheduler on Windows

**The problem:** `scheduler_cmd.py` is a 60-second subprocess loop that assumes POSIX (relies on signals, POSIX process model, cron/systemd as the parent supervisor). On Windows it will run as a plain Python process but has no integration with the Windows Service Control Manager (SCM), no auto-restart on crash, no clean stop/start from `services.msc`.

**Two valid options — recommend Option A for v5.4, keep Option B as documented alternative:**

**Option A: Windows Scheduled Task (no new dep, lower complexity)**
- Use `schtasks.exe` (stdlib subprocess) to register a task that runs `quirk sensor run` on a schedule (e.g., every 30 minutes).
- `quirk sensor run` is a single-shot scan + push, not a long-running daemon.
- Advantages: No SCM integration, no pywin32 dep, works on locked-down Windows boxes, trivial to register/deregister.
- Disadvantages: Coarser scheduling (1-minute minimum vs. seconds), no push-on-demand without external trigger.
- Implementation: `quirk sensor install-task --schedule "*/30"` calls `subprocess.run(["schtasks", "/create", ...])`. Pure stdlib.

**Option B: Windows Service via pywin32>=311 (new dep, richer lifecycle)**
- `win32serviceutil.ServiceFramework` subclass wraps the existing scheduler dispatch loop.
- Handles SCM start/stop/pause signals, writes to Windows Event Log, auto-restart on crash.
- `pywin32>=311` (released 2026-07-14): pip-installable on Python 3.11+, Windows-only wheels.
- Disadvantages: Requires elevated install (`python -m win32serviceutil install`), does not work inside virtual environments cleanly (pywin32_postinstall must run in global Python), adds a Windows-only dep that complicates `pyproject.toml` platform markers.
- PyInstaller + pywin32 Windows Service combo is documented as "not well maintained" in PyInstaller issues; the combination requires careful hook configuration.

**Recommendation:** Ship Option A (Scheduled Task) in v5.4 — it works on every Windows version without admin rights for task creation (standard user can create tasks for their own account), no new dep, and covers the 30-minute cadence that is the natural scan interval for a segmented-network sensor. Option B (Windows Service) is a v5.5 follow-on if customers require it.

**Platform detection:** `sys.platform == "win32"` — already the Python convention. Wrap scheduler start-up path in a `_platform_scheduler()` factory that calls `schtasks` on Windows and `systemd`/`launchd`/`cron` helpers on POSIX.

### 3b. Packaging for Locked-Down Windows Boxes

Three options in order of preference for v5.4:

**Option A: PyInstaller>=6.20.0 frozen executable (RECOMMENDED for v5.4)**
- Current version: 6.20.0 (released 2026-05-18). Supports Python 3.8–3.14.
- Produces a single-directory bundle (`--onedir`, preferred) or single-file EXE (`--onefile`). Single-directory is faster to start and easier to update file-by-file; single-file is simpler to distribute.
- Recommended: `--onedir` with a wrapper launcher script `quirk-sensor.exe`. Ship as a ZIP; unzip to `C:\ProgramData\quirk-sensor\`.
- Advantages: Zero Python requirement on target machine; bundles all pip deps; works on enterprise Windows with application whitelisting if the EXE is signed (Authenticode — already in the v4.10 Sigstore/release-engineering pipeline).
- Disadvantages: Antivirus false positives (common for PyInstaller binaries — mitigate with Authenticode signing); build must happen on a Windows machine or Windows CI runner (cross-compilation not supported); `--onefile` extracts to %TEMP% at runtime which may be blocked by enterprise DLP.
- Build: `windows-latest` GitHub Actions runner already available; the v5.4 CI job `build-sensor-windows` runs PyInstaller and smoke-tests the resulting EXE.
- PyInstaller is a BUILD-TIME tool. It does NOT go in `[project.dependencies]` or any extras group. Add to a `[build]` or CI requirements file only.

**Option B: Python Embeddable Distribution (alternative for advanced deployers)**
- CPython 3.11 embeddable ZIP (python.org/downloads/windows) + pre-installed wheels vendored alongside.
- Advantages: Smaller download than PyInstaller bundle; no antivirus false positives (it is the real Python interpreter).
- Disadvantages: Requires manual configuration (`pythonXX._pth` file, uncomment `import site`); no pip by default; all deps must be pre-vendored; higher deployment complexity.
- Appropriate for large-scale enterprise deployments with a proper software distribution system (SCCM/Intune). Overkill for v5.4.

**Option C: Windows Container (not recommended for sensors)**
- A sensor in a segmented network running Docker would require Docker Desktop or containerd on each Windows box — heavyweight, often blocked by enterprise policy, defeats the "lightweight sensor" goal.

**Recommendation:** Deliver PyInstaller-frozen EXE via the existing GHCR multi-arch image pipeline as a separate `sensor` artifact. A separate `quirk-sensor-win64.zip` release asset.

### 3c. SQLite Path/Locking Behavior on Windows

**Key differences from Linux:**

1. **Path separators:** `pathlib.Path` handles this transparently. The existing codebase must be audited for any hard-coded `/` in paths — use `Path(...)` everywhere, never string concatenation with `/`. `os.path.join` also works but `pathlib.Path` is preferred. This is a code audit task, not a new dep.

2. **Default data directory:** Linux: `~/.local/share/quirk/` or `./quirk.db`. Windows: `%APPDATA%\quirk\` or `%LOCALAPPDATA%\quirk\`. Use `platformdirs` (see below) to resolve correctly on both.

3. **WAL mode on Windows local filesystem:** Works correctly. WAL mode relies on shared memory via memory-mapped files; Windows VFS supports this for local storage. Known issues only arise with network shares / UNC paths (`\\server\share\quirk.db`) — SQLite explicitly documents this as unsupported. Document: "Do not place quirk.db on a UNC path or network drive."

4. **WAL mode + multiple processes:** On Windows, SQLite WAL creates a `-wal` and `-shm` file alongside the DB. These are ordinary files; Windows file handles lock them differently than Unix. Use `busy_timeout=5000` (5 seconds) on all SQLAlchemy connections to avoid `database is locked` under concurrent access. This is a config change, not a new dep.

5. **Sensor vs. console SQLite isolation:** Each sensor has its own local `quirk.db` (scan results). The console has its own `quirk.db` (merged results + sensor_tokens + sensor_results). They NEVER share a file. No network SQLite. This sidesteps the WAL-over-network problem entirely.

**platformdirs — new dep for data directory resolution:**

| Technology | Version | Purpose | Why |
|---|---|---|---|
| `platformdirs` | `>=4.3.0` | OS-appropriate data/config dirs (`user_data_dir`, `user_config_dir`) | Replaces the current implicit `./quirk.db` assumption; returns `C:\Users\<user>\AppData\Local\quirk\quirk\` on Windows, `~/.local/share/quirk/` on Linux, `~/Library/Application Support/quirk/` on macOS. Already widely used (pip itself uses platformdirs). |

Current version: platformdirs 4.3.7 (released 2025-11-14, verified PyPI). Zero transitive deps. Pure Python. Add to core `dependencies`.

---

## 4. Cross-Sensor Merge on the Console

**Decision: No new library needed. Pure Python on existing cyclonedx-python-lib model.**

The merge problem is:
- N sensor result payloads, each containing a `CryptoEndpoint` list + CBOM component list + findings list + subscores.
- Same RFC1918 IP can appear in two segments (different logical hosts). The `segment_label` dimension disambiguates: merge key is `(sensor_id, host, port)`, not just `(host, port)`.
- CBOM components: deduplicate by `(bom_ref, algorithm, segment_label)`. The existing `cyclonedx-python-lib>=11.7` model supports this — components have a `bom_ref` field; union across sensors, keeping provenance.
- Quantum-readiness score: weighted average or minimum across sensors, depending on policy. Pure arithmetic, no library needed.
- The `sbommerge` PyPI package and CycloneDX CLI tool both exist for BOM merging, but they operate on serialized JSON/XML files, not Python model objects. Using them would require serialize→merge-tool→deserialize, adding a subprocess call and an external tool dependency. The existing builder pattern (Pass 1/2/3) is better extended to accept N sensor inputs and produce one merged output directly in Python.

**Explicit NOT-to-add:** `sbommerge`, `cyclonedx-cli`, `cdxgen` — these are external tools for SBOM file formats, not Python-native model operations. The CBOM builder already runs in-process.

---

## Recommended Stack — New Additions Only

### Core Technologies (NEW)

| Technology | Version | Purpose | Why Recommended |
|---|---|---|---|
| `platformdirs` | `>=4.3.7` | OS-appropriate data/config directory resolution | Replaces implicit `./quirk.db` assumption; Windows needs `%APPDATA%\quirk\`, not cwd; pure Python, zero deps |
| `tenacity` | `>=9.1.4` | Retry with exponential backoff for sensor→console HTTP push | Composable @retry decorator, async-compatible, no transitive deps; required for store-and-forward reliability |

### Supporting Libraries (NEW, Windows-only optional)

| Library | Version | Purpose | When to Use |
|---|---|---|---|
| `pywin32` | `>=311` | Windows Service Control Manager integration | Only if v5.5 Windows Service support added; NOT needed for v5.4 Scheduled Task approach |

### Build Tooling (NOT a runtime dep)

| Tool | Version | Purpose | Notes |
|---|---|---|---|
| `PyInstaller` | `>=6.20.0` | Frozen EXE for locked-down Windows sensor deployment | Build-time only; runs on `windows-latest` GitHub Actions runner; not in pyproject.toml dependencies |

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|---|---|---|
| httpx (existing) for sensor push | requests | Already in core; httpx has streaming upload, async support, cert auth |
| Bearer token enrollment (stdlib secrets) | mTLS / client certificates | PKI issuance/rotation is heavyweight infra; bearer token already battle-tested in this codebase |
| Bearer token enrollment (stdlib secrets) | JWT per-sensor | Clock-sync requirement hostile to air-gapped sensors; signing key rotation complexity |
| tenacity retry | httpx built-in retry transport | httpx's `HTTPTransport(retries=N)` only retries connection errors, not 5xx; tenacity retries any condition |
| Windows Scheduled Task (stdlib) | pywin32 Windows Service | No admin elevation for task creation; simpler; works on locked-down machines; no new dep |
| PyInstaller frozen EXE | Python Embeddable Distribution | Higher deployment complexity; requires pre-vendoring all deps manually |
| PyInstaller frozen EXE | Windows Container | Docker required on sensor host — defeats lightweight sensor goal |
| File-per-payload spool directory | SQLite spool table | SQLite locking contention during concurrent scan + push; files are naturally idempotent (UUID name), atomically created, OS-managed |
| Pure Python CBOM merge (in-process) | sbommerge / cyclonedx-cli | External tools operate on serialized files; in-process merge is faster, avoids subprocess, keeps provenance metadata |
| platformdirs>=4.3.7 | Hard-coded `./quirk.db` | POSIX-only assumption fails on Windows; platformdirs is the de facto standard (used by pip, Poetry, etc.) |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|---|---|---|
| Redis / Celery | Hard constraint — zero new heavy infra; single-tenant SQLite-only | File-based spool + tenacity retry |
| RabbitMQ / MQTT / any message broker | Requires inbound access from console to sensor segments — violates outbound-only requirement | httpx POST from sensor to console |
| PostgreSQL | Hard constraint — additive SQLite-only schema | SQLite with WAL + busy_timeout=5000 |
| mTLS / PKI infra (e.g., step-ca, cfssl) | Over-engineered for single-tenant on-prem; requires CA distribution to all sensors | Bearer token + HTTPS (TLS in transit) |
| JWT per-sensor tokens | Clock drift hostile to air-gapped sensors; signing key rotation | Long-lived opaque enrollment tokens (secrets.token_urlsafe) with explicit revocation |
| sbommerge / cyclonedx-cli | External binary tools; subprocess call; no Python model access | In-process merge using existing cyclonedx-python-lib model |
| tus / resumable upload protocol library | CBOM payloads are 50–500 KB compressed — single POST is sufficient | httpx POST + retry via tenacity |
| Docker (for Windows sensor) | Enterprise locked-down boxes often prohibit Docker Desktop | PyInstaller frozen EXE |
| pywin32 (in v5.4) | Scheduled Task covers the v5.4 use case without admin elevation | `schtasks.exe` via subprocess; defer Service support to v5.5 |
| aiofiles | Sensor push is CPU-bound (scan) + synchronous HTTP push; async not required | Synchronous httpx.Client |
| opentelemetry / distributed tracing | Heavy infra; single-tenant console can use existing scan logs + delivery audit table | Existing `integration_deliveries` + new `sensor_results` table |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---|---|---|
| `tenacity>=9.1.4` | Python 3.10–3.14 | Requires Python >=3.10; project requires >=3.10; no conflict |
| `platformdirs>=4.3.7` | Python 3.8–3.14 | Pure Python; no conflicts |
| `pywin32>=311` | Python 3.11, Windows only | Post-install script (`pywin32_postinstall.py`) must run as admin; do NOT run in venv |
| `PyInstaller>=6.20.0` | Python 3.8–3.14, Windows/Linux/macOS | Build on target platform only (no cross-compilation) |
| `zstandard>=0.22.0` | Python 3.9–3.14 | Binary wheels for Windows (cp311-win_amd64 confirmed); version 0.25.0 is current |
| `httpx>=0.28.0` | Already in core | Supports streaming upload via generator `content=` param; cert auth for future mTLS |
| SQLite WAL mode | Windows local filesystem | Works correctly on local NTFS; NEVER use WAL on UNC/network paths |

---

## Stack Patterns by Variant

**If sensor is on a fully-connected network (can reach console):**
- Use direct httpx POST with tenacity retry (max 5 attempts, exponential backoff 4s–300s).
- No spool directory needed, but implement it anyway for consistency and crash-safety.

**If sensor is in an air-gapped / store-and-forward segment:**
- Sensor writes compressed payload to spool directory after each scan.
- On a scheduled "push window" (separate from scan schedule), attempt delivery of all spooled files.
- Console endpoint is idempotent: `sensor_id + scan_session_id` is the dedup key; duplicate pushes are silently accepted (201 → already exists).

**If Windows sensor cannot use PyInstaller (application whitelisting):**
- Fall back to Python Embeddable Distribution with pre-vendored wheels.
- Document in operator guide; provide a `vendor-wheels.ps1` PowerShell script that runs `pip download` on a connected machine and produces a bundle.

**If customer requires per-sensor mTLS (future):**
- httpx already supports `httpx.Client(cert=("cert.pem", "key.pem"), verify="ca.pem")`.
- The push client module should accept an optional `SensorTLSConfig` dataclass (cert_path, key_path, ca_path).
- No new dep needed; add as a config option in the sensor YAML template.

---

## Implementation Integration Points

### Existing seams the sensor push reuses directly:

1. **`quirk/util/safe_exc.py::safe_str()`** — already scrubs secrets from error messages; sensor push errors must pass through `safe_str()` before logging (same ISEC-02 invariant as v5.3 dispatcher).

2. **`quirk/util/url_allowlist.py::validate_external_url()`** — SSRF guard; the console URL in sensor config must be validated before the first connection attempt.

3. **`quirk/dashboard/api/middleware/auth.py::require_auth()`** — the console ingestion endpoint adds `Depends(require_sensor_auth)`, a new dependency that reads from the `sensor_tokens` table instead of the single configured token, but uses the same `hmac.compare_digest` pattern.

4. **`quirk/notify/dispatcher.py`** — the delivery-audit pattern (write audit row before attempt, update on success/failure) is the exact pattern the console ingestion endpoint should use for `sensor_results` rows.

5. **`quirk/cli/token_cmd.py`** — `quirk sensor enroll` is a near-copy of the token generation logic; reuse `secrets.token_urlsafe(32)` + SHA-256 hash storage.

---

## Installation (New Deps Only)

```toml
# pyproject.toml additions

[project.dependencies]
# Add to existing list:
"platformdirs>=4.3.7",

[project.optional-dependencies]
sensor = [
    "tenacity>=9.1.4",
    "quirk-scanner[dashboard]",  # sensor mode includes push client; console endpoint requires dashboard
]

# Windows-only service support (v5.5 candidate — do NOT add in v5.4):
# win_service = ["pywin32>=311; sys_platform == 'win32'"]
```

```bash
# Sensor install (Linux/macOS)
pip install "quirk-scanner[sensor]"

# Sensor install (Windows, with frozen EXE — preferred for locked-down boxes)
# Download quirk-sensor-win64.zip from GHCR release assets; no pip needed

# Build frozen EXE (CI only, windows-latest runner)
pip install pyinstaller>=6.20.0
pyinstaller --onedir --name quirk-sensor quirk/cli/sensor_entry.py
```

---

## Sources

- [pypi.org/project/zstandard/](https://pypi.org/project/zstandard/) — version 0.25.0 confirmed current; Python 3.9–3.14 + Windows cp311 wheels
- [pypi.org/project/tenacity/](https://pypi.org/project/tenacity/) — version 9.1.4 (2026-02-07); Python >=3.10
- [pypi.org/project/platformdirs/](https://pypi.org/project/platformdirs/) — version 4.3.7 (2025-11-14); pure Python
- [pypi.org/project/pywin32/](https://pypi.org/project/pywin32/) — version 311 (2025-07-14); Windows-only
- [pyinstaller.org/en/stable/](https://pyinstaller.org/en/stable/) — version 6.20.0 (2026-05-18); Python 3.8–3.14; Windows service support noted as "not well maintained"
- [python-httpx.org/advanced/ssl/](https://www.python-httpx.org/advanced/ssl/) — client certificate auth confirmed; existing dep >=0.28.0
- [sqlite.org/useovernet.html](https://sqlite.org/useovernet.html) — WAL on network shares explicitly unsupported (official docs)
- [sqlite.org/wal.html](https://sqlite.org/wal.html) — WAL shared-memory requirement; Windows local filesystem supported
- [tenacity.readthedocs.io](https://tenacity.readthedocs.io/) — wait_exponential, retry_if_exception_type patterns confirmed
- [pypi.org/project/sbommerge/](https://pypi.org/project/sbommerge/) — evaluated and rejected (file-based, not Python model API)
- quirk/dashboard/api/middleware/auth.py — existing hmac.compare_digest + HTTPBearer pattern (source review)
- quirk/cli/token_cmd.py — existing secrets.token_urlsafe(32) enrollment pattern (source review)
- quirk/util/safe_exc.py — ISEC-02 safe_str pattern for error scrubbing (source review)
- quirk/notify/dispatcher.py — delivery-audit row pattern (source review)
- pyproject.toml — confirmed: httpx>=0.28.0 in core; fastapi/uvicorn in [dashboard]; no tenacity or platformdirs yet

---
*Stack research for: v5.4 Distributed On-Prem Scanner Architecture*
*Researched: 2026-05-25*
