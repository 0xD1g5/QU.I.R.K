# Windows Packaging Spike — Feasibility & Sizing Assessment

**Phase:** 116 — Windows Packaging Spike (v5.5 milestone)
**Date:** 2026-05-27
**Requirement:** WINPKG-01
**Scope:** Assessment document + CI evidence only. No frozen EXE, installer, or NSIS script is committed or published (D-06 hard scope guard).

---

## Summary

This document records the Phase 116 feasibility assessment for packaging the QUIRK sensor as a
PyInstaller frozen EXE on Windows, validated by a non-blocking `windows-packaging-spike` CI job
on `windows-latest`. It covers the five WINPKG-01 criterion-1 topics: PyInstaller spec viability,
hidden-import surface, Scheduled Task vs. Windows Service trade-offs, CI validation results, and
the v5.6 effort estimate. It ends with a single go/no-go/defer recommendation.

---

## PyInstaller Spec Viability

### Freeze Target

The correct freeze target is `run_scan.py` (the `.py` script at repo root) — **not** the
`module:function` string `run_scan:_run_main_with_job_guard` declared in `pyproject.toml`.
PyInstaller analyses a script file as its entry point. `run_scan.py` already contains the
required `__main__` guard:

```python
if __name__ == "__main__":
    multiprocessing.freeze_support()   # Phase 116-01: added for Windows spawn safety
    _run_main_with_job_guard()
```

`multiprocessing.freeze_support()` was added in Phase 116 Plan 01 (commit 723f8ca) as the first
call inside `if __name__ == "__main__"`. This prevents recursive self-invocation when Windows
uses the `spawn` start method for subprocesses under a frozen EXE.

### --onefile vs. --onedir Trade-off

| Aspect | --onefile | --onedir |
|--------|-----------|----------|
| Delivery form | Single `.exe` | Folder of files |
| Runtime startup | Unpacks to `%TEMP%\_MEIxxxxxx` on every run; 1–5 s cold start | No unpack; starts immediately |
| `__file__` paths | Point into ephemeral temp dir — unstable across runs | Point into stable `dist/` dir — stable |
| Antivirus friction | HIGH — writing to `%TEMP%` is a well-known AV false-positive trigger | LOWER — no temp extraction |
| Sensor suitability | Poor for production (AV risk + slow start + unstable paths) | Good — stable paths, fast start |
| Spike CI usage | Used for D-01 evidence build (acceptable for one-off validation) | **Recommended for v5.6 production** |

**Recommendation for v5.6:** Use `--onedir`. The sensor does not require a single-file
distribution and the `--onefile` drawbacks (AV friction, slow startup, unstable `__file__`
paths) are unacceptable for a production sensor. The dashboard (`quirk serve`) and HTML report
`_STATIC_DIR`/`_TEMPLATES_DIR` `__file__` paths work correctly in `--onedir` mode without
modification; they break only in `--onefile`. Two paths require code changes before a
production `--onedir` build (see §Hidden-Import Surface below), but neither affects the
core sensor scan→push workflow.

### PyInstaller Version

PyInstaller **6.20.0** is pinned in the CI spike job (current stable as of 2026-05-27, PyPI
verified, slopcheck [OK]). `pyinstaller-hooks-contrib 2026.5` is auto-installed as a dependency
and provides community hooks for most QUIRK dependencies.

---

## Hidden-Import Surface

### Hook Coverage Matrix

QUIRK's dependency surface against `pyinstaller-hooks-contrib 2026.5`:

| Dependency | Has Hook | Hidden-Import Risk | Action Required |
|------------|----------|--------------------|-----------------|
| `cryptography` | Yes (`hook-cryptography.py`) | LOW — hook handles all hazmat backends and OpenSSL 3 modules | None |
| `uvicorn` | Yes (`hook-uvicorn.py`) | LOW — `collect_submodules('uvicorn')` covers submodules | Belt-and-suspenders: `--hidden-import uvicorn.logging uvicorn.loops.auto uvicorn.protocols.http.auto` |
| `boto3` / `botocore` | Yes (boto3) | MEDIUM — botocore service JSON corpus (~50–100 MB) may be missed | Use base `pip install -e .` (not `[all]`); document EXE size |
| `lxml` | Yes (multiple sub-hooks) | LOW | None |
| `jinja2` | Yes | LOW | None |
| `platformdirs` | Yes (Windows submodule platform-selected) | LOW | None |
| `rich` | Yes | LOW | None |
| `dnspython` | Yes (`hook-dns.rdata.py`) | LOW | None |
| `sqlalchemy` | **No hook** | **HIGH** — all dialects dynamically loaded; no hook in hooks-contrib 2026.5 | `--collect-all sqlalchemy --hidden-import sqlalchemy.dialects.sqlite --hidden-import sqlalchemy.dialects.sqlite.pysqlite` — **mandatory** |
| `fastapi` | **No hook** | **HIGH** — Starlette routing/response submodules dynamically loaded | `--collect-all fastapi` — **mandatory** |
| `httpx` | No hook | MEDIUM — async transports conditional | `--hidden-import httpx._transports.default` |
| `PyJWT` / `python-jose` | No hook | LOW / MEDIUM — pure Python / crypto backends | `--hidden-import jose.backends` |
| `zstandard` | No hook | LOW — C extension auto-collected via binary analysis | None |
| `cyclonedx-python-lib` | No hook | MEDIUM — JSON schema data files | `--collect-data cyclonedx` |
| `python-docx` | No hook | MEDIUM — template docx files in package data | Sensor-only freeze can exclude `[docx]` |

**Key finding:** SQLAlchemy and FastAPI are the only HIGH-risk dependencies without hooks.
Both are mitigated by `--collect-all sqlalchemy` and `--collect-all fastapi` in the CI
invocation. The spike build's `warn-quirk.txt` artifact will confirm whether any gaps remain.

### `__file__` Risk Inventory

All `__file__`-based data-file paths in `quirk/` were audited. Summary:

| File | Pattern | Risk in --onefile | Risk in --onedir | Sensor Impact |
|------|---------|-------------------|------------------|---------------|
| `quirk/__init__.py` | `Path(__file__).parent.parent / "pyproject.toml"` (fallback only) | LOW — fires only in `PackageNotFoundError` branch; metadata collected via `--copy-metadata` | LOW | None — metadata path used |
| `quirk/cli/init_cmd.py` | `os.path.dirname(__file__) + config_template.yaml` (fallback) | LOW — primary `importlib.resources` path is frozen-safe | LOW | None — primary path used |
| `quirk/compliance/cmvp.py` | `Path(__file__).parent / "cmvp_cache.json"` (module-level constant) | HIGH (write path `refresh_cache`) | LOW | **None for sensor**: `_load_cache` read path uses `importlib.resources` (STAB-02 fix, Phase 115) |
| `quirk/compliance/cmvp.py` | `Path(__file__).parent / "cmvp_curated.csv"` | HIGH (`refresh_cache` write path) | LOW | **None for sensor**: `refresh_cache` is a dev-only CLI, not a sensor code path |
| `quirk/dashboard/api/app.py` | `_STATIC_DIR = os.path.dirname(__file__) + "../static"` | HIGH | LOW (stable) | LOW for sensor-only freeze — `quirk serve` can be documented as unsupported in frozen EXE v1 |
| `quirk/reports/html_renderer.py` | `_TEMPLATES_DIR = os.path.dirname(__file__) + "templates"` | HIGH | LOW (stable) | LOW for sensor-only freeze — HTML reports not generated by sensor push workflow |

**Net assessment for sensor freeze:**

- The sensor scan→push workflow (enroll, scan, push) has **zero `__file__` blockers** in
  `--onedir` mode. The `importlib.resources` migration (STAB-02, Phase 115) already made the
  sensor-critical CMVP cache read path frozen-safe.
- `_TEMPLATES_DIR` and `_STATIC_DIR` break in `--onefile` but are stable in `--onedir`.
  For a v5.6 sensor-only build these paths are acceptable as-is; for a full-feature build
  (including `quirk serve` and HTML report generation) they require conversion to
  `importlib.resources` or a `sys._MEIPASS`-aware path. This is a known, bounded fix
  (~1 day effort, see §v5.6 Effort Estimate).

### Sensor Wire-Contract Compatibility

Per-sensor authentication (Phase 113 Bearer token contract) is fully frozen-EXE compatible:

| Component | Frozen-EXE Compatible | Notes |
|-----------|----------------------|-------|
| `platformdirs` config/data dirs | YES | `hook-platformdirs.py` selects `platformdirs.windows` on Windows; APPDATA/LOCALAPPDATA paths correct |
| `httpx.Client(verify=True)` TLS | YES | `certifi` bundle auto-collected by PyInstaller binary analysis |
| `zstandard` (Cython extension) | YES | `.pyd` binary extension auto-collected |
| `hmac`, `hashlib`, `secrets` | YES | stdlib — always available |
| `sensor.yaml` YAML config loading | YES | PyYAML has no dynamic loading issues |
| `quirk.__version__` via `importlib.metadata` | YES — with `--copy-metadata quirk-scanner` | Requires this flag in CI command; included |
| HMAC envelope signing (SHA-256) | YES | Pure stdlib |
| Spool files via `platformdirs` | YES | Windows APPDATA path derived correctly |

**Wire-contract verdict:** The sensor enroll→scan→push path is fully compatible with a frozen
EXE build. Per-sensor Bearer tokens (SHA-256 hash comparison) are pure stdlib.

---

## Windows Host Model: Scheduled Task vs. Service

The QUIRK sensor is a **periodic scan→push process** (start, run, exit). This makes Windows
Task Scheduler the architecturally correct host model.

### Trade-off Table

| Dimension | Windows Scheduled Task | Windows Service |
|-----------|------------------------|-----------------|
| Purpose fit | Periodic scan→push (starts, runs, exits) | Always-on daemon — runs continuously |
| Dependencies | `schtasks.exe` — built into all Windows versions since XP | `sc.exe` + SCM registration; requires NSSM or pywin32 wrapper for EXE |
| Privilege model | Runs as any user or SYSTEM; no SCM interaction | Requires Administrator for registration |
| Network on startup | Configurable via trigger (e.g. "Start after network available") | Can start before network; manual delay required |
| Monitoring | Task History in Task Scheduler MMC | Windows Event Log + Service Control Manager |
| Extra dependencies | **None** | NSSM (lightweight, separate binary) or pywin32 (heavy, conflicts risk) |
| Setup command | `schtasks /Create /SC HOURLY /TN QUIRK-Sensor /TR "C:\path\quirk.exe sensor push"` | `nssm install QUIRK-Sensor "C:\path\quirk.exe"` + configure args |
| Recovery on failure | Retry via Task Scheduler trigger settings | Automatic restart via SCM recovery actions |
| QUIRK sensor fit | **RECOMMENDED (D-04)** — matches the scan→push lifecycle exactly | Overkill — requires sensor to manage its own sleep/poll loop |

### Recommendation: Windows Scheduled Task (Primary)

**D-04 decision:** The Scheduled Task model is the correct fit for a periodic sensor. The
sensor already exits cleanly after each push; Task Scheduler models this naturally (hourly
or per-schedule triggers, Task History for audit, no keep-alive loop required in the EXE).

Example setup:

```powershell
schtasks /Create /SC HOURLY /TN "QUIRK-Sensor" `
  /TR "C:\Program Files\quirk-scanner\quirk.exe sensor push" `
  /RU SYSTEM /F
```

### Windows Service (Alternative — Always-On)

For operators who require continuous, immediately-restarted sensor operation (e.g. regulated
environments where task scheduler history is insufficient), a **Windows Service** via
[NSSM (Non-Sucking Service Manager)](https://nssm.cc) is the recommended wrapper. NSSM wraps
any EXE as a Windows service without requiring pywin32 or a custom
`ServiceFramework` subclass.

```powershell
# Install NSSM from https://nssm.cc/download, then:
nssm install QUIRK-Sensor "C:\Program Files\quirk-scanner\quirk.exe"
nssm set QUIRK-Sensor AppParameters "sensor push"
nssm set QUIRK-Sensor AppDirectory "C:\Program Files\quirk-scanner"
sc start QUIRK-Sensor
```

Trade-offs vs. Scheduled Task: requires NSSM binary distribution alongside the EXE, SCM
registration needs Administrator, and the sensor would need a keep-alive loop or NSSM restart
configuration to run periodically. pywin32 is explicitly excluded as a dependency (v5.4
forbidden-additions list).

---

## CI Validation Results

### Job Configuration

A non-blocking `windows-packaging-spike` CI job was added to `.github/workflows/python-ci.yml`
in Phase 116 Plan 01 (commit 300ec19). Key properties:

- **Runner:** `windows-latest` (GitHub-hosted, matches `windows-sensor-smoke` job)
- **Non-blocking:** `continue-on-error: true` at both job level and build step level (D-02)
- **PyInstaller install:** `pip install pyinstaller==6.20.0` inline in CI step; **not** in
  `pyproject.toml` (D-03 — zero new install-time dependencies for end users)

### PyInstaller Invocation

The CI job runs the following build (PowerShell `pwsh` shell, backtick line continuations):

```powershell
pyinstaller --onefile --name quirk `
  --collect-all quirk `
  --collect-all sqlalchemy `
  --collect-all fastapi `
  --copy-metadata quirk-scanner `
  --hidden-import sqlalchemy.dialects.sqlite `
  --hidden-import sqlalchemy.dialects.sqlite.pysqlite `
  --hidden-import uvicorn.logging `
  --hidden-import uvicorn.loops.auto `
  --hidden-import uvicorn.protocols.http.auto `
  --add-data "quirk/compliance/cmvp_cache.json;quirk/compliance" `
  --add-data "quirk/compliance/cmvp_curated.csv;quirk/compliance" `
  --add-data "quirk/reports/templates;quirk/reports/templates" `
  run_scan.py 2>&1 | Tee-Object -FilePath pyinstaller-build.log
```

Note: the `--add-data` separator is `;` (Windows) not `:` (POSIX). Using `:` on Windows causes
silent path mismatch and `FileNotFoundError` at runtime despite a clean build.

### Expected Evidence Artifact

The job uploads the `pyinstaller-spike-evidence` artifact (`retention-days: 30`) containing:

| File | Content |
|------|---------|
| `pyinstaller-build.log` | Full PyInstaller stdout/stderr; `WARNING:` and `ModuleNotFoundError` lines identify hidden-import gaps |
| `build/quirk/warn-quirk.txt` | PyInstaller runtime analysis warnings — secondary hidden-import signal |
| `dist/quirk.exe` | The frozen EXE (if build succeeded) — for size and smoke verification only |

The report step emits either:
- `RESULT: BUILD_SUCCESS — EXE size: N.N MB`
- `RESULT: BUILD_FAILED — see pyinstaller-build.log artifact`

### Live CI Build Status

**At the time of authoring this document, the `windows-packaging-spike` CI job has not yet
executed on a pushed branch.** The job runs on `push` to GitHub Actions (windows-latest runner).

**RESULT (to be confirmed from pyinstaller-spike-evidence artifact after first push):**
`[ BUILD_SUCCESS / BUILD_FAILED — update this line from the artifact after push ]`

The go/no-go recommendation below is based on the research evidence (D-05 threshold): the
freeze path is viable with the documented flags and the sensor wire contract is frozen-EXE
compatible. The live CI build will confirm or adjust this assessment.

### Evidence-Only Warning (D-06)

> **The CI EXE (`dist/quirk.exe`) is evidence-only and is NOT a production binary.**
> It is a transient CI artifact with `retention-days: 30`. It must not be distributed,
> deployed, or used as a production sensor binary. A production frozen-EXE build requires
> the v5.6 full-build phase (see §v5.6 Effort Estimate).

---

## v5.6 Effort Estimate

Assuming the CI spike confirms no deep architectural blockers (runnable EXE or only documented,
fixable hidden-import failures):

| Work Item | Estimate | Notes |
|-----------|----------|-------|
| Finalize `.spec` file (resolve any remaining hidden-import gaps from spike CI log) | 0.5 day | Each build failure narrows the list; CI log is the primary input |
| Fix `_TEMPLATES_DIR` (`__file__`) for `--onedir` report generation | 0.5 day | Convert `html_renderer.py` to `importlib.resources` or `sys._MEIPASS`-aware path |
| Fix `_STATIC_DIR` in `app.py` for `--onedir` dashboard support (optional for sensor-only) | 1 day | More complex; FastAPI serves static files from filesystem |
| GitHub Actions `--onedir` build + artifact publish pipeline | 0.5 day | Extend spike job; add release upload step and SHA-256 checksum |
| Windows Scheduled Task install script (PowerShell) | 0.5 day | `schtasks /Create` wrapper; unit-testable on Windows runner |
| End-to-end sensor test on Windows (enroll + push against local console) | 1 day | Requires Windows CI with network access to test console; extends `windows-sensor-smoke` |
| Documentation update (operator guide, README Windows section) | 0.5 day | Install path, Task Scheduler setup, NSSM alternative |
| **Total** | **~4–5 days / 1 focused phase** | T-shirt size: **M** |

**Confidence:** MEDIUM. The 4–5 day estimate is based on the `__file__` surface identified
above and analogous packaging projects. Actual effort depends on hidden-import failures revealed
by the spike CI log; add +1–2 days if iteration requires more than two CI cycles.

**Go/no-go threshold (D-05):** "Go" if the spike CI job produces a runnable EXE (or fails only
on the documented, fixable hidden-imports above) AND the sizing fits one v5.6 phase. "No-go"
or "Defer" if the EXE fails for non-trivial reasons — e.g. a C extension incompatible with
Windows, or hidden-import surface is unexpectedly large beyond one phase budget.

---

## Recommendation

**GO (conditional on live CI build)**

The freeze path is **viable based on the research evidence**: the sensor wire contract is fully
frozen-EXE compatible (STAB-02 importlib.resources migration, per-sensor Bearer token using
pure stdlib), the two HIGH-risk hidden-import gaps (SQLAlchemy, FastAPI) have documented,
proven mitigations (`--collect-all` flags), and the `__file__` surface has zero sensor-critical
blockers in `--onedir` mode. The 4–5 day effort estimate fits one focused v5.6 phase.

**The recommendation becomes unconditional GO when the `pyinstaller-spike-evidence` artifact
from the first `windows-packaging-spike` CI run shows `RESULT: BUILD_SUCCESS` (or `BUILD_FAILED`
with only the documented fixable hidden-import gaps). It becomes DEFER if the build fails for
reasons outside the documented surface (e.g. C extension incompatibility or unexpectedly large
hidden-import iteration).**

For v5.6: proceed with a `--onedir` production build targeting the sensor subcommands
(enroll/scan/push/export-results), hosted as a Windows Scheduled Task. Document `quirk serve`
(dashboard) and HTML report generation as not supported in the v5.6 frozen EXE pending the
`_STATIC_DIR`/`_TEMPLATES_DIR` fixes.

---

## Appendix: Illustrative .spec (not committed)

The following spec file listing is **illustrative only** — it is documentation, not a
committed build script (D-06 scope guard). A production v5.6 `.spec` would be refined from
the spike CI log's hidden-import findings.

```python
# quirk-sensor.spec
# ILLUSTRATIVE ONLY — not shipped in v5.5 or committed to the repository (D-06).
# Refine from pyinstaller-spike-evidence/pyinstaller-build.log after CI run.
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

block_cipher = None

quirk_datas = collect_data_files('quirk', include_py_files=False)
cyclonedx_datas = collect_data_files('cyclonedx')

a = Analysis(
    ['run_scan.py'],
    pathex=['.'],
    binaries=[],
    datas=(
        quirk_datas
        + cyclonedx_datas
        + copy_metadata('quirk-scanner')   # importlib.metadata.__version__ support
    ),
    hiddenimports=[
        # SQLAlchemy — no hook in hooks-contrib 2026.5; dialects dynamically loaded
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.dialects.sqlite.pysqlite',
        # FastAPI / Starlette — no hook; routing submodules dynamically loaded
        'starlette.middleware.base',
        'starlette.routing',
        # uvicorn extras (belt-and-suspenders beyond hook-uvicorn.py)
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        # python-jose crypto backends
        'jose.backends',
        # httpx async transport
        'httpx._transports.default',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Reduce size — sensor does not need these; re-add for full-feature build
        'playwright',
        'impacket',
        'psycopg2',
        'pymysql',
        'schemathesis',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# For v5.6 production: use COLLECT (--onedir) instead of EXE with a=scripts+binaries+datas
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='quirk',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,           # UPX compression reduces EXE size ~30%
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,       # sensor is a CLI tool
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```
