# Phase 116: Windows Packaging Spike - Research

**Researched:** 2026-05-27
**Domain:** PyInstaller frozen-EXE packaging, Windows CI mechanics, Windows host models for periodic sensors
**Confidence:** HIGH (PyInstaller mechanics, CI patterns, __file__ risk inventory); MEDIUM (effort sizing, uvicorn/fastapi runtime stability)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** CI validation runs a real `pyinstaller --onefile` build of the `quirk` console entrypoint on `windows-latest` and captures hidden-import/collection failures as evidence. `--collect-all quirk` is an acceptable fallback if onefile build exceeds reasonable CI time.
- **D-02:** Add a new dedicated, non-blocking `windows-packaging-spike` job to `.github/workflows/python-ci.yml` (`continue-on-error: true`). Mirror `windows-sensor-smoke` setup (checkout, setup-python 3.11, `pip install -e .`).
- **D-03:** PyInstaller is installed CI-only inline (`pip install pyinstaller==<pinned>`) — NOT added to `[project]` dependencies or a `[packaging]` extra.
- **D-04:** Assessment recommends Windows Scheduled Task as primary v5.6 host model; documents Windows Service as always-on alternative with trade-offs.
- **D-05:** Recommend "go" if spike build yields a runnable EXE (or fails only on documented, fixable hidden-imports) AND estimated full-build effort fits one focused v5.6 phase; otherwise "defer/no-go" with rationale.
- **D-06 (LOCKED scope guard):** No frozen EXE, installer, or NSIS script is committed or published. Deliverable is assessment doc + CI evidence only.

### Claude's Discretion

- Exact pinned PyInstaller version and whether to add a minimal `.spec` file in the assessment as an appendix (illustrative only).
- Precise structure/headings of `docs/windows-packaging-spike.md` beyond the five required topics.
- How the CI job surfaces the build result into the doc (artifact upload, log excerpt, or committed summary).
- Effort-estimate format (t-shirt size + rough day/phase breakdown).

### Deferred Ideas (OUT OF SCOPE)

- Full production PyInstaller build + Windows Scheduled Task/Service host + installer — v5.6 fast-follow gated on spike go/no-go.
- Adding PyInstaller as a shipped `[packaging]` extra — only if v5.6 proceeds.
- Public-repo cutover + required `windows-sensor-smoke` status check — separate v5.6 launch decision.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WINPKG-01 | Spike phase produces a written feasibility and sizing assessment for packaging the sensor as a PyInstaller frozen EXE hosted as a Windows Scheduled Task (or Service), validated against `windows-latest` CI runner, ending in a go/no-go recommendation and effort estimate for v5.6. No production packaging artifact ships. | PyInstaller mechanics (§Freeze Target), CI job pattern (§CI Mechanics), host-model analysis (§Host Model), effort sizing (§Effort Sizing) all documented below. |
</phase_requirements>

---

## Summary

Phase 116 is a pure spike: produce an assessment document and CI evidence, no frozen binary shipped. The primary work is (1) adding one non-blocking CI job that runs a real `pyinstaller --onefile` build of the `quirk` entrypoint on `windows-latest`, (2) capturing the build outcome as evidence, and (3) writing `docs/windows-packaging-spike.md` with analysis, trade-offs, and a go/no-go recommendation.

PyInstaller 6.20.0 (current stable as of 2026-05-27) has verified hooks for most of QUIRK's heavy dependencies (`cryptography`, `uvicorn`, `boto3`, `lxml`, `rich`, `platformdirs`, `jinja2`, `dns`). The biggest known risks are: (a) **SQLAlchemy and FastAPI have no built-in hooks** in `pyinstaller-hooks-contrib 2026.5` — they require `--collect-all sqlalchemy` and `--collect-all fastapi`; (b) five `__file__`-based data-file loads in QUIRK's source that break in a frozen EXE without the `sys._MEIPASS`/`importlib.resources` pattern (three are already safe, two need attention); and (c) `--onefile` on Windows unpacks to `%TEMP%` at each run, which is inappropriate for a production sensor — the assessment should surface this and recommend `--onedir` for v5.6.

**Primary recommendation:** The CI job should attempt `--onefile` (per D-01) with `--collect-all quirk --collect-all sqlalchemy --collect-all fastapi` plus explicit `--add-data` for the three data-file groups. Capture the build log (artifact upload, ~2 MB). The assessment structure should mirror the five required topics from WINPKG-01 success criterion 1, end with a single go/no-go line, and include an illustrative `.spec` file appendix.

---

## Architectural Responsibility Map

This phase makes no architectural changes — it is investigation-only.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Freeze build | CI runner (windows-latest) | — | PyInstaller build must run on target OS; cross-compilation is not supported |
| Evidence capture | CI (artifact upload) | doc committed to repo | Log + EXE size captured at build time; embedded in assessment doc |
| Assessment document | Source (docs/) | — | Written by executor after CI evidence is captured |
| Host-model recommendation | Assessment doc | — | Scheduled Task vs Service is a doc/analysis decision, not a code change |

---

## Standard Stack

### Core (CI-only inline install — NOT added to project deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyinstaller | 6.20.0 | Freeze Python application to standalone EXE | Current stable; slopcheck [OK]; has hooks for most QUIRK deps |
| pyinstaller-hooks-contrib | 2026.5 | Community hooks for cryptography, uvicorn, boto3, etc. | Auto-installed by pyinstaller; current as of 2026-05-27 |

[VERIFIED: PyPI registry — `pip index versions pyinstaller` returned 6.20.0 as latest; slopcheck [OK]]
[VERIFIED: PyPI registry — `pip index versions pyinstaller-hooks-contrib` returned 2026.5 as latest]

### Supporting (already in project)

All production dependencies are already declared in `pyproject.toml`. No new project deps added this phase.

### Installation (CI inline — per D-03)

```yaml
- name: Install PyInstaller (spike only)
  run: pip install pyinstaller==6.20.0
```

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| pyinstaller | PyPI | 15+ yrs | Very high | github.com/pyinstaller/pyinstaller | [OK] | Approved |
| pyinstaller-hooks-contrib | PyPI | 5+ yrs | Very high | github.com/pyinstaller/pyinstaller-hooks-contrib | auto-dep, not separately slopchecked | Approved (official sub-project of PyInstaller) |

[VERIFIED: slopcheck install pyinstaller — returned [OK] in this session]

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Freeze Target and Hidden-Import Surface

### The Entrypoint

`pyproject.toml` declares:
```
quirk = "run_scan:_run_main_with_job_guard"
```

PyInstaller cannot accept `module:function` strings. The freeze target must be the script file: `run_scan.py` (located at repo root). PyInstaller will analyse `run_scan.py` as the entry script and the `_run_main_with_job_guard` function is called via `if __name__ == "__main__": _run_main_with_job_guard()` at the bottom of `run_scan.py` — this pattern is already present (line 2254-2255). [VERIFIED: read run_scan.py]

The CI command is therefore:
```bash
pyinstaller --onefile --name quirk \
  --collect-all quirk \
  --collect-all sqlalchemy \
  --collect-all fastapi \
  --add-data "quirk/compliance/cmvp_cache.json:quirk/compliance" \
  --add-data "quirk/compliance/cmvp_curated.csv:quirk/compliance" \
  --add-data "quirk/reports/templates:quirk/reports/templates" \
  run_scan.py
```

(Additional flags covered in the patterns section below.)

### Hook Coverage Matrix

The following table maps each QUIRK dependency to its PyInstaller hook status as of `pyinstaller-hooks-contrib 2026.5`. "Has hook" means the package has a dedicated `hook-<name>.py` in the installed hooks corpus. [VERIFIED: filesystem scan of installed pyinstaller-hooks-contrib hooks]

| Dependency | Has Hook | Hook Coverage | Hidden-Import Risk |
|------------|----------|---------------|--------------------|
| `cryptography` | Yes (`hook-cryptography.py`) | hazmat backends, cffi binaries, OpenSSL 3 modules | LOW — hook handles all known backends |
| `uvicorn` | Yes (`hook-uvicorn.py`) | `collect_submodules('uvicorn')` — all submodules | LOW — hook collects all; `uvicorn[standard]` needs separate `--hidden-import uvicorn.logging uvicorn.loops uvicorn.loops.auto uvicorn.protocols uvicorn.protocols.http` if not fully collected |
| `boto3` | Yes (`hook-boto3.py`) | dynamodb, ec2, s3 submodules + data files | MEDIUM — botocore service JSON data files are large; hook collects boto3 but botocore's service data may miss |
| `lxml` | Yes (`hook-lxml.py`, `hook-lxml.etree.py`, etc.) | multiple sub-hooks | LOW |
| `jinja2` | Yes (`hook-jinja2.py`) | template extensions | LOW |
| `platformdirs` | Yes (`hook-platformdirs.py`) | Windows/macOS/Unix submodules platform-selected | LOW — hook specifically handles Windows submodule |
| `rich` | Yes (`hook-rich.py`) | markup and renderable submodules | LOW |
| `dnspython` | Yes (`hook-dns.rdata.py`) | rdata record types | LOW — hook collects dynamically loaded rdata types |
| `sqlalchemy` | **No hook** | None in hooks corpus | **HIGH — all dialects and backends are dynamically loaded; SQLite dialect must be explicitly collected** |
| `fastapi` | **No hook** | None in hooks corpus | **HIGH — Starlette routing and response submodules dynamically loaded** |
| `httpx` | No hook | None | MEDIUM — async transports and http2 loaded conditionally |
| `PyJWT` | No hook | None | LOW — pure Python, no dynamic loading |
| `python-jose` | No hook | None | MEDIUM — crypto backends conditionally imported |
| `zstandard` | No hook | None | LOW — C extension, auto-collected via binary analysis |
| `tenacity` | No hook | None | LOW — pure Python |
| `croniter` | No hook | None | LOW — pure Python |
| `pyyaml` | No hook (ruamel.yaml has one, not pyyaml) | None | LOW — C extension auto-collected |
| `cyclonedx-python-lib` | No hook | None | MEDIUM — JSON schema data files need explicit collection |
| `python-docx` | No hook | None | MEDIUM — template docx files in package data |
| `signxml` | No hook | None | MEDIUM — XSD schema files may need collection |
| `nh3` | No hook | None | LOW — Rust extension, binary auto-collected |
| `beautifulsoup4` | No hook | None | LOW — pure Python, parsers conditionally loaded |

**[ASSUMED]** — hook coverage is based on filesystem scan of installed pyinstaller-hooks-contrib 2026.5 on this macOS dev machine. The exact same corpus will be installed on windows-latest by `pip install pyinstaller==6.20.0`; hook content may differ slightly due to platform-specific filtering inside hooks.

### Data Files That Must Be Bundled

QUIRK's `pyproject.toml` `[tool.setuptools.package-data]` declares:
```
quirk = [
    "reports/templates/*.j2",
    "config_template.yaml",
    "dashboard/static/**/*",
    "compliance/*.json",
]
```
[VERIFIED: read pyproject.toml]

Files actually present:

| Data File / Dir | Path in Package | Accessed By | Frozen-EXE Risk |
|-----------------|-----------------|-------------|-----------------|
| `cmvp_cache.json` | `quirk/compliance/` | `cmvp.py` via `importlib.resources` (STAB-02) | LOW — importlib.resources path is frozen-safe; `--collect-data quirk.compliance` bundles it |
| `cmvp_curated.csv` | `quirk/compliance/` | `cmvp.py` via `_CURATED_CSV_PATH = Path(__file__).parent / "cmvp_curated.csv"` | **HIGH — `Path(__file__).parent` is broken in frozen EXE; `__file__` points into `_MEIxxxxxx` temp dir for `--onefile`** |
| `report.html.j2` | `quirk/compliance/` (also found at `quirk/reports/templates/`) | html_renderer.py | MEDIUM — `_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")` is broken in `--onefile`; safe in `--onedir` |
| `config_template.yaml` | `quirk/` | `init_cmd.py` via `importlib.resources` (primary) with `__file__` fallback | LOW — primary path is frozen-safe; fallback path is not but is only triggered on exception |
| `dashboard/static/**/*` | `quirk/dashboard/` | `app.py` via `_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")` | MEDIUM — broken in `--onefile`; sensor-only freeze can skip dashboard static if `quirk serve` is excluded |
| CycloneDX JSON schemas | Inside cyclonedx-python-lib package | cbom validator | MEDIUM — may need `--collect-data cyclonedx` |

---

## __file__ Risk Inventory

[VERIFIED: grep of `quirk/**/*.py` for `Path(__file__)` and `os.path.dirname(__file__)`]

Every use of `__file__` to locate data files breaks in PyInstaller `--onefile` mode because the frozen script's `__file__` points into the `_MEIxxxxxx` temp directory, which is unpacked fresh on every run. In `--onedir` mode `__file__` remains stable (pointing into the dist directory), making `--onedir` the safer v5.6 target.

| File | Line | Pattern | Risk in --onefile | Risk in --onedir | Fix Required |
|------|------|---------|-------------------|------------------|--------------|
| `quirk/__init__.py` | 23 | `Path(__file__).resolve().parent.parent / "pyproject.toml"` | **HIGH** — `pyproject.toml` not bundled; this path only triggers in the `PackageNotFoundError` branch (no `pip install -e` in frozen env, so `importlib.metadata.version` will work from embedded metadata) | LOW — same fallback issue, but frozen EXE has embedded metadata | LOW RISK: frozen EXE uses `importlib.metadata`; the `PackageNotFoundError` branch should not fire if metadata is collected |
| `quirk/cli/init_cmd.py` | 53 | `os.path.join(os.path.dirname(__file__), "..", "config_template.yaml")` | MEDIUM — only triggers if `importlib.resources` fails (line 49 primary path); `importlib.resources` is frozen-safe in PyInstaller 6.x | LOW | LOW RISK: primary path (importlib.resources) is frozen-safe; fallback fires only on exception |
| `quirk/compliance/cmvp.py` | 51 | `_CACHE_PATH = Path(__file__).parent / "cmvp_cache.json"` (module-level constant) | **HIGH** — `_CACHE_PATH` is set at import time; `_load_cache` uses this as the equality check for "is it monkeypatched?". In normal (non-test) frozen operation, `_load_cache` uses `importlib.resources` because `_CACHE_PATH == _default_path` (both derive from same `__file__`). So read path is SAFE. But `refresh_cache` (write path) uses `_CACHE_PATH` — acceptable because refresh is dev-tool-only. | LOW | LOW RISK: read path via importlib.resources is frozen-safe (STAB-02 already fixed this) |
| `quirk/compliance/cmvp.py` | 52 | `_CURATED_CSV_PATH = Path(__file__).parent / "cmvp_curated.csv"` | **HIGH** — used directly without importlib.resources fallback (line 52 sets constant, used in `refresh_cache`). Same assessment as above: `refresh_cache` is dev-only, not invoked in normal sensor operation. | LOW | LOW RISK for sensor use; refresh_cache is not a sensor code path |
| `quirk/dashboard/api/app.py` | 27 | `_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")` | **HIGH** — dashboard static files not at that path in frozen EXE | LOW (stable in --onedir) | MEDIUM: sensor freeze can skip `quirk serve` subcommand; document as known limitation |
| `quirk/reports/html_renderer.py` | 144 | `_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")` | **HIGH** — templates dir not at relative path in --onefile | LOW (stable in --onedir) | **REQUIRES FIX for v5.6 production build**: use `importlib.resources` or `sys._MEIPASS`-aware path |

**Summary for spike assessment:**
- Sensor-critical paths (`_load_cache` read, `config_template.yaml`) are ALREADY frozen-safe via `importlib.resources` (STAB-02 fix).
- Dashboard and HTML report paths (`_STATIC_DIR`, `_TEMPLATES_DIR`) break in `--onefile` but work in `--onedir` — acceptable for v5.6 `--onedir` build.
- `refresh_cache` and version fallback are dev-only / non-sensor code paths — low impact.
- **Net assessment:** the sensor-relevant code paths have zero `__file__` blockers. The spike build may succeed even without fixes; failures (if any) will be in report generation or dashboard startup, not in the core scan→push workflow.

---

## Sensor Wire-Contract Compatibility

The per-sensor auth contract (Phase 113) is implemented in `sensor_cmd.py` and `sensor_auth.py`. Key analysis:

| Component | Frozen-EXE Compatible? | Notes |
|-----------|----------------------|-------|
| `platformdirs.user_config_dir` / `user_data_dir` | YES | `platformdirs` has a dedicated hook that selects `platformdirs.windows` on Windows; config/data dirs are derived from Windows APPDATA/LOCALAPPDATA — fully OS-correct in frozen EXE |
| `httpx.Client(verify=True)` | YES | httpx bundled; TLS verification uses `certifi` bundle (auto-collected by PyInstaller via binary deps) |
| `zstandard` (Cython extension) | YES | Binary extension; PyInstaller collects `.pyd` files automatically |
| `hmac`, `hashlib`, `secrets` | YES | stdlib; always available |
| `sensor.yaml` config loading (YAML) | YES | PyYAML has no dynamic loading issues |
| `uuid`, `subprocess`, `tempfile` | YES | stdlib |
| `quirk.__version__` via `importlib.metadata` | YES — IF metadata collected | Requires `--copy-metadata quirk-scanner` in PyInstaller command |
| HMAC envelope signing | YES | Pure Python + stdlib |
| Spool files (`%LOCALAPPDATA%/quirk-scanner/...`) | YES | Uses `platformdirs` → Windows APPDATA path |

**Wire-contract verdict:** The sensor enroll/push path has no frozen-EXE incompatibilities assuming `platformdirs` hook is active and `certifi` is collected. The lock-and-key of per-sensor Bearer tokens (SHA-256 hash comparison) is pure stdlib.

---

## Architecture Patterns

### PyInstaller Freeze Mechanics for this Project

#### --onefile vs --onedir

| Aspect | --onefile | --onedir |
|--------|-----------|----------|
| Delivery | Single `.exe` | Folder of files |
| Runtime startup | Unpacks to `%TEMP%\_MEIxxxxxx` on every run; adds 1-5s cold start | No unpack; starts immediately |
| `__file__` paths | Point into ephemeral temp dir; unstable across runs | Point into stable dist dir |
| Antivirus friction | HIGH — `.exe` writing to `%TEMP%` is AV-flagged behaviour | LOWER — no temp extraction |
| Sensor suitability | Poor (AV risk + slow start) | Good (stable paths, fast start) |
| Spike usage | Use for CI evidence per D-01; acceptable fallback is `--collect-all` | Recommend for v5.6 production |

**For the spike:** run `--onefile` per D-01. For the v5.6 recommendation in the assessment, recommend `--onedir` as the production packaging strategy.

#### Entrypoint Wrapper Requirement

PyInstaller takes a `.py` script, not a `module:function` string. `run_scan.py` is the correct freeze target — it is a top-level module at repo root, and already contains:

```python
if __name__ == "__main__":
    _run_main_with_job_guard()
```

[VERIFIED: run_scan.py line 2254-2255]

PyInstaller will call `python run_scan.py` under the hood, which triggers `__main__` and calls `_run_main_with_job_guard`. No wrapper script is needed.

#### Spec File Pattern (illustrative — for assessment appendix only)

```python
# quirk-sensor.spec (illustrative — NOT shipped in v5.5)
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

block_cipher = None

# Collect package data
quirk_datas = collect_data_files('quirk', include_py_files=False)
cyclonedx_datas = collect_data_files('cyclonedx')

a = Analysis(
    ['run_scan.py'],
    pathex=['.'],
    binaries=[],
    datas=(
        quirk_datas
        + cyclonedx_datas
        + copy_metadata('quirk-scanner')   # for importlib.metadata.__version__
    ),
    hiddenimports=[
        # SQLAlchemy — no hook; must collect dialects explicitly
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.dialects.sqlite.pysqlite',
        # FastAPI / Starlette — no hook
        'starlette.middleware.base',
        'starlette.routing',
        # uvicorn extras (covered by hook but belt-and-suspenders)
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
        # botocore service endpoint data
        'botocore',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Reduce size — sensor doesn't need these
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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,   # sensor is a CLI tool
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

[ASSUMED] — spec file content is illustrative based on PyInstaller 6.x documentation and hook analysis; actual hidden-import failures will be revealed by the CI build log.

### Recommended Project Structure (Post-Spike Artefacts)

```
docs/
└── windows-packaging-spike.md   # Assessment (new, this phase)
.github/workflows/
└── python-ci.yml                # New windows-packaging-spike job added
```

No source code changes. No `.spec` file committed in v5.5.

### CI Job Pattern

Mirror `windows-sensor-smoke` exactly:

```yaml
windows-packaging-spike:
  name: Windows Packaging Spike
  runs-on: windows-latest
  continue-on-error: true        # D-02: non-blocking
  steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Setup Python 3.11
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install project (editable) and PyInstaller
      run: |
        pip install -e .
        pip install pyinstaller==6.20.0

    - name: Run PyInstaller onefile build
      id: pyinstaller_build
      run: |
        pyinstaller --onefile --name quirk \
          --collect-all quirk \
          --collect-all sqlalchemy \
          --collect-all fastapi \
          --copy-metadata quirk-scanner \
          --hidden-import sqlalchemy.dialects.sqlite \
          --hidden-import sqlalchemy.dialects.sqlite.pysqlite \
          --hidden-import uvicorn.logging \
          --hidden-import uvicorn.loops \
          --hidden-import uvicorn.loops.auto \
          --hidden-import uvicorn.protocols \
          --hidden-import uvicorn.protocols.http.auto \
          --add-data "quirk/compliance/cmvp_cache.json;quirk/compliance" \
          --add-data "quirk/compliance/cmvp_curated.csv;quirk/compliance" \
          --add-data "quirk/reports/templates;quirk/reports/templates" \
          run_scan.py 2>&1 | tee pyinstaller-build.log
      continue-on-error: true

    - name: Capture EXE size (if build succeeded)
      run: |
        if (Test-Path dist/quirk.exe) {
          $size = (Get-Item dist/quirk.exe).Length / 1MB
          Write-Output "EXE size: $([math]::Round($size, 1)) MB"
          Write-Output "BUILD_SUCCESS=true" >> $env:GITHUB_OUTPUT
        } else {
          Write-Output "BUILD_SUCCESS=false" >> $env:GITHUB_OUTPUT
        }
      shell: pwsh

    - name: Upload build evidence
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: pyinstaller-spike-evidence
        path: |
          pyinstaller-build.log
          build/quirk/warn-quirk.txt
          dist/quirk.exe
        retention-days: 30
```

**Key Windows-specific note:** `--add-data` path separator on Windows is `;` not `:`. [CITED: pyinstaller.org/en/stable/usage.html]

**Evidence capture approach (Claude's Discretion):** Upload build log + warn file as CI artifact (lowest friction — no committed file). The executor writes the `docs/windows-packaging-spike.md` assessment by reading the artifact after the CI run completes, embedding a summary of failures or success.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Console-script freeze wrapper | Custom launcher script | `run_scan.py` directly as entrypoint (`if __name__ == "__main__"` already present) | PyInstaller analysis starts from a `.py` file; the `__main__` guard is sufficient |
| Data file collection | Manual `--add-data` for every file | `--collect-all quirk` or `collect_data_files('quirk')` in spec | Collects all declared package-data globs automatically |
| Hidden import enumeration | Manual `--hidden-import` for every submodule | `--collect-all sqlalchemy` / `--collect-all fastapi` | Recursively collects submodules + data; safer than piecemeal listing |
| Metadata for `importlib.metadata` | Embed version string directly | `--copy-metadata quirk-scanner` | Ensures `importlib.metadata.version("quirk-scanner")` works in frozen EXE |
| Windows Service wrapper | pywin32 `ServiceFramework` subclass | Windows Scheduled Task (`schtasks`) for periodic sensor | Sensor is periodic (scan→push), not always-on; Task Scheduler avoids pywin32 dependency and SCM registration complexity |

---

## Common Pitfalls

### Pitfall 1: --add-data Separator Is OS-Specific
**What goes wrong:** Using `:` (POSIX) as the `--add-data` separator on Windows causes PyInstaller to silently mismatch the source and dest, producing a build that starts but immediately throws FileNotFoundError for data files.
**Why it happens:** PyInstaller uses `:` on POSIX and `;` on Windows. GitHub Actions `windows-latest` is Windows — `;` is required.
**How to avoid:** Use `;` in the CI YAML step. Alternatively use a spec file where `datas` is a Python list of tuples, which is always platform-neutral.
**Warning signs:** Build succeeds, EXE launches, but `cmvp_cache.json` or template not found at runtime.
[CITED: pyinstaller.org/en/stable/usage.html]

### Pitfall 2: SQLAlchemy "Can't load plugin" at Runtime
**What goes wrong:** The frozen EXE starts but crashes with `sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:sqlite` when the first DB call is made.
**Why it happens:** SQLAlchemy uses entry points and dynamic dialect loading; PyInstaller's static analysis does not follow this. There is no hook for SQLAlchemy in hooks-contrib 2026.5. [VERIFIED: hooks-contrib filesystem scan]
**How to avoid:** Always include `--collect-all sqlalchemy` AND `--hidden-import sqlalchemy.dialects.sqlite` AND `--hidden-import sqlalchemy.dialects.sqlite.pysqlite`.
**Warning signs:** Build succeeds (no ImportError at build time), runtime crash only on first ORM call.
[CITED: github.com/sqlalchemy/sqlalchemy/discussions/10372]

### Pitfall 3: --onefile AV Friction on Windows
**What goes wrong:** `windows-latest` CI runner or a client's endpoint protection flags the EXE writing to `%TEMP%` during unpack as suspicious, blocking execution.
**Why it happens:** PyInstaller `--onefile` unpacks itself to `%TEMP%\_MEIxxxxxx` at startup — a well-known AV false-positive trigger pattern.
**How to avoid:** For the spike, the CI runner is a clean VM and AV friction is lower. For v5.6 production, use `--onedir` instead.
**Warning signs:** EXE exits with non-zero immediately after launch on a managed Windows endpoint; no Python traceback emitted.
[ASSUMED]

### Pitfall 4: Slow Startup on --onefile
**What goes wrong:** The sensor EXE takes 5-30 seconds to start because it unpacks its entire bundle to `%TEMP%` before executing.
**Why it happens:** `--onefile` packs all `.pyc` and binary files into a compressed archive; Windows AV scans each extracted file. The `--onedir` bundle avoids this entirely.
**How to avoid:** Acceptable for CI evidence capture; document as known limitation in the assessment.
**Warning signs:** Scheduled Task completes "too slowly"; sensor timeout firing before scan starts.
[ASSUMED]

### Pitfall 5: importlib.resources Fails for Non-Package Directories
**What goes wrong:** `importlib.resources.files("quirk.compliance").joinpath("cmvp_cache.json")` raises `FileNotFoundError` in the frozen EXE.
**Why it happens:** PyInstaller implements a frozen importer that supports `importlib.resources` for packages collected as `pyz` archives, but only if the package's `__init__.py` is present in the archive. If `--collect-all quirk` does not explicitly include the compliance subdirectory as a package, the resources API fails.
**How to avoid:** Use `--collect-all quirk` (collects all sub-packages including `quirk.compliance`) OR add explicit `--add-data "quirk/compliance;quirk/compliance"` on Windows.
**Warning signs:** CMVP cache unavailable warning on first scan (same symptom as pre-STAB-02 bug).
[CITED: pyinstaller.org/en/stable/hooks.html — importlib.resources frozen importer note]

### Pitfall 6: botocore Service Data Files Missing
**What goes wrong:** AWS connector (`quirk[cloud]`) fails at runtime with `DataNotFoundError` because botocore's service JSON files are not bundled.
**Why it happens:** `hook-boto3.py` collects boto3 data files but botocore's service endpoint data is a separate large corpus (~50 MB). It may not be fully collected.
**How to avoid:** The spike should use `pip install -e .` (base deps only) rather than `pip install -e ".[all]"` — this excludes cloud/botocore from the freeze entirely, keeping the spike EXE manageable. For the assessment, document that a full `[all]` freeze would require `--collect-all botocore`.
**Warning signs:** Import succeeds but boto3 API calls fail with `botocore.exceptions.DataNotFoundError`.
[ASSUMED — based on known botocore data-file footprint; HIGH risk if cloud extras included in freeze]

### Pitfall 7: multiprocessing on Windows
**What goes wrong:** If any code path uses `multiprocessing.spawn` (the Windows default), the frozen EXE re-spawns itself and tries to import the main module again, causing recursive import failures.
**Why it happens:** Windows uses `spawn` start method; the frozen EXE is re-executed with a special argument to launch the worker. PyInstaller requires `if __name__ == "__main__":` guard (already present in run_scan.py) and `multiprocessing.freeze_support()` call.
**How to avoid:** Add `multiprocessing.freeze_support()` as the first call in `if __name__ == "__main__":` block. Review whether uvicorn or any worker spawns subprocesses.
**Warning signs:** Recursive import of run_scan module; secondary `quirk` process appearing in Task Manager.
[CITED: pyinstaller.org/en/stable/when-things-go-wrong.html]

---

## Windows Host Model — Scheduled Task vs Service

[D-04: assessment recommends Scheduled Task as primary; document Service as alternative]

| Dimension | Windows Scheduled Task | Windows Service |
|-----------|----------------------|-----------------|
| Purpose fit | Periodic scan→push (e.g. hourly) — starts, runs, exits | Always-on daemon — runs continuously in background |
| Dependencies | `schtasks.exe` (built-in to all Windows versions) | `sc.exe` + SCM registration; pywin32 or NSSM wrapper for Python/EXE |
| Privileges | Can run as any user or SYSTEM; no SCM interaction | Must register with SCM; requires Administrator for registration |
| Network access on startup | Starts after network is available via task trigger settings | Can start before network; custom delay required |
| Monitoring | Task History in Task Scheduler console | Windows Event Log + Service Control Manager |
| Extra deps | None | pywin32 (heavy; conflicts risk) or NSSM (lightweight, separate binary) |
| Setup command | `schtasks /Create /SC HOURLY /TN QUIRK-Sensor /TR "C:\path\quirk.exe sensor push"` | `sc create QUIRK-Sensor binpath= "C:\path\quirk.exe sensor push"` or `nssm install QUIRK-Sensor "C:\path\quirk.exe"` |
| Recovery | Task retry on failure via trigger settings | Automatic restart via SCM recovery actions |
| QUIRK sensor fit | **RECOMMENDED** — sensor is a short-lived process (scan → compress → push → exit); Task Scheduler perfectly models this | Overkill — would require keep-alive loop inside sensor, adding complexity |

**Assessment recommendation (D-04):** Scheduled Task is architecturally correct for a sensor that scans-and-pushes. The always-on Service model requires the sensor to manage its own sleep/poll loop, adding unnecessary complexity and making the frozen EXE harder to reason about. Document the Service pattern as available for operators who require it (with NSSM as the recommended wrapper, avoiding pywin32 dependency).

[CITED: docs.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks — task triggers and scheduling]
[ASSUMED] — NSSM description based on training knowledge; verify at nssm.cc if included in assessment.

---

## Effort Sizing Inputs for v5.6

The following table provides inputs the executor should use when writing the effort estimate section of the assessment.

| Work Item | Estimated Effort | Notes |
|-----------|-----------------|-------|
| Finalize `.spec` file (hidden imports resolved from spike CI log) | 0.5 day | Iterative; each build failure narrows the list |
| Fix `_TEMPLATES_DIR` `__file__` path for `--onedir` mode | 0.5 day | Convert to `importlib.resources` or `sys._MEIPASS` check |
| Fix `_STATIC_DIR` in `app.py` for `--onedir` mode (dashboard support in EXE) | 1 day | More complex; dashboard serves files from filesystem |
| GitHub Actions pipeline for `--onedir` build + artifact publish | 0.5 day | Extend spike job; add release upload step |
| Windows Scheduled Task install script (PowerShell or schtasks) | 0.5 day | Simple wrapper; unit test on Windows runner |
| End-to-end sensor test on Windows (enroll + push against local console) | 1 day | Requires Windows CI with network access to test console |
| Documentation update (operator guide, README) | 0.5 day | Update install docs for Windows path |
| **Total** | **~4-5 days / 1 focused phase** | Fits one v5.6 phase; "go" if spike confirms no deep blockers |

**[ASSUMED]** — effort estimates are based on analogous packaging projects and the __file__ surface identified above. Actual effort depends on hidden-import failures surfaced by the spike CI log.

**Go/no-go threshold (D-05):** "Go" if spike CI job produces a runnable EXE (or fails only on documented, fixable hidden imports) AND the above sizing fits one phase. "Defer/no-go" if the EXE fails to build for non-trivial reasons (e.g. a C extension incompatible with Windows, or hidden import surface is unexpectedly large requiring multiple iteration cycles beyond one phase budget).

---

## Code Examples

### CI Job YAML (complete)

```yaml
# Source: mirrored from windows-sensor-smoke pattern in .github/workflows/python-ci.yml
windows-packaging-spike:
  name: Windows Packaging Spike
  runs-on: windows-latest
  continue-on-error: true
  steps:
    - uses: actions/checkout@v4

    - uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install project and PyInstaller
      run: |
        pip install -e .
        pip install pyinstaller==6.20.0

    - name: Build onefile EXE
      run: |
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
      continue-on-error: true

    - name: Report build outcome
      shell: pwsh
      run: |
        if (Test-Path dist/quirk.exe) {
          $mb = [math]::Round((Get-Item dist/quirk.exe).Length / 1MB, 1)
          Write-Output "RESULT: BUILD_SUCCESS — EXE size: $mb MB"
        } else {
          Write-Output "RESULT: BUILD_FAILED — see pyinstaller-build.log artifact"
        }

    - uses: actions/upload-artifact@v4
      if: always()
      with:
        name: pyinstaller-spike-evidence
        path: |
          pyinstaller-build.log
          build/quirk/warn-quirk.txt
          dist/quirk.exe
        retention-days: 30
```

### Reading Hidden-Import Failures from Log

Build-time warnings appear as `WARNING: Hidden import not found!` or `ModuleNotFoundError` in `pyinstaller-build.log`. Runtime-only failures appear in `warn-quirk.txt` generated in `build/quirk/`. Both files are captured as artifacts.

```bash
# From the build log, look for lines starting with:
# WARNING: ...
# ModuleNotFoundError: No module named '...'
grep -E "WARNING:|ModuleNotFoundError|ImportError" pyinstaller-build.log
```

### spec file --add-data equivalent (platform-neutral)

```python
# In Analysis() datas argument — avoids ; vs : OS difference
from PyInstaller.utils.hooks import collect_data_files

datas = (
    collect_data_files('quirk')      # all package-data globs from pyproject.toml
    + collect_data_files('cyclonedx')
    + copy_metadata('quirk-scanner') # importlib.metadata version support
)
```
[CITED: pyinstaller.org/en/stable/spec-files.html]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `sys._MEIPASS` path construction for data files | `__file__`-relative paths (now work in --onedir; `importlib.resources` for wheel safety) | PyInstaller 6.0 (2023) | No special `sys.frozen` check needed in --onedir mode |
| PyInstaller 5.x hooks (external `hook-cryptography.py`) | hooks-contrib 2026.x auto-installed | Continuous since 2020 | Most major deps now have hooks; gaps are SQLAlchemy, FastAPI |
| `--onefile` as default recommendation | `--onedir` preferred for server tools | Community consensus ~2022 | AV friction + startup latency make --onefile inappropriate for services/sensors |
| `pywin32` for Windows services | NSSM wrapper (no Python service framework) | Established pattern | Simpler; avoids pyOpenSSL/cryptography chain that pywin32 can trigger |

**Deprecated/outdated:**
- `py2exe`: Windows-only predecessor to PyInstaller; not maintained for Python 3.10+. [ASSUMED]
- `cx_Freeze`: Still maintained but smaller ecosystem; fewer hooks for complex deps like cryptography. [ASSUMED]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | pyinstaller-hooks-contrib 2026.5 on windows-latest will have the same hook set as observed on macOS dev machine | Hook Coverage Matrix | If Windows runner has different hooks, hidden-import list may be incomplete; spike CI log will reveal the gap |
| A2 | `--collect-all fastapi` collects all necessary starlette/anyio submodules | Spec File Pattern | FastAPI startup may fail; fixable by adding explicit `--hidden-import` entries |
| A3 | botocore service data files are NOT included in base `pip install -e .` freeze because cloud extra is not installed | Pitfall 6 | If botocore is pulled in transitively, the EXE will be unexpectedly large; check `pip show botocore` in CI |
| A4 | Effort sizing (4-5 days for v5.6 full build) | Effort Sizing | Could be +2 days if hidden-import iteration takes multiple CI cycles |
| A5 | NSSM description as a lightweight service wrapper | Host Model table | NSSM URL: nssm.cc; verify current version before including in assessment |
| A6 | `multiprocessing.freeze_support()` is not currently called in run_scan.py | Pitfall 7 | If uvicorn uses multiprocessing, Windows worker spawn may fail; verify by checking uvicorn startup mode used in sensor context (sensor uses subprocess, not uvicorn directly) |

---

## Open Questions (RESOLVED)

> Resolved by plan design: Q1 (botocore size) → captured as CI build evidence + assessment EXE-size note (Plan 116-02); Q2 (uvicorn/multiprocessing) → `multiprocessing.freeze_support()` added in Plan 116-01 Task 1; Q3 (EXE size acceptability) → captured as assessment evidence and folded into the go/no-go (Plan 116-02). A spike legitimately resolves discovery questions via CI evidence rather than pre-analysis.

1. **Does `pip install -e .` on windows-latest pull in botocore?** — RESOLVED: CI evidence captures size; doc notes `--exclude`/`--collect-all` trade-off
   - What we know: botocore is a dependency of boto3 which is in `[project]` core deps (not optional)
   - What's unclear: botocore's service data JSON corpus is ~50-100 MB; if included in the freeze the EXE will be very large
   - Recommendation: In the CI job, check `pip show botocore` size and add `--exclude botocore` if sensor-only mode is desired; OR use `--collect-all botocore` but document EXE size implication

2. **Will uvicorn workers cause multiprocessing spawn issues?**
   - What we know: sensor uses `subprocess.run(["quirk", ...])` not uvicorn directly for scans; `quirk serve` (dashboard) would use uvicorn
   - What's unclear: whether the spike build triggers uvicorn import at top level (it does, via run_scan.py imports)
   - Recommendation: Add `multiprocessing.freeze_support()` as first call in `if __name__ == "__main__"` in run_scan.py; this is a safe 1-line change

3. **EXE size — acceptable for a sensor distribution?**
   - What we know: cryptography + boto3 + SQLAlchemy + other core deps will likely produce a 50-150 MB EXE
   - What's unclear: client AV and distribution channel constraints
   - Recommendation: Capture EXE size as part of assessment evidence; document compression options (`upx=True` in spec file)

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | CI job | ✓ (windows-latest via setup-python@v5) | 3.11.x | — |
| PyInstaller 6.20.0 | CI build step | ✓ (inline install) | 6.20.0 | — |
| windows-latest runner | CI job | ✓ (existing `windows-sensor-smoke` job proves it works) | GitHub hosted | — |
| `run_scan.py` at repo root | Freeze target | ✓ | — | — |
| `quirk/compliance/cmvp_cache.json` | Bundled data file | ✓ (STAB-02 shipped it as package-data) | — | — |

**Missing dependencies with no fallback:** None.

---

## Validation Architecture

> nyquist_validation is enabled (not set to false in .planning/config.json).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_sensor_windows_smoke.py -v` |
| Full suite command | `pytest tests/ -m "not slow and not live_infra"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WINPKG-01 | PyInstaller build executes on windows-latest | CI integration | `windows-packaging-spike` CI job (not pytest) | ❌ Wave 0 — new CI job |
| WINPKG-01 | Assessment document exists with required sections | manual | human review of `docs/windows-packaging-spike.md` | ❌ Wave 0 — new doc |
| WINPKG-01 | Go/no-go recommendation present | manual | human review | ❌ Wave 0 — new doc |

This phase has no new pytest unit tests — it is a spike producing a doc and a CI job. The "tests" are the CI job pass/fail evidence and human review of the assessment document.

### Wave 0 Gaps

- [ ] `.github/workflows/python-ci.yml` — add `windows-packaging-spike` job (new CI job, not a test file)
- [ ] `docs/windows-packaging-spike.md` — assessment document (new file)

---

## Security Domain

> security_enforcement is not set to false; section included.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Assessment doc only; no new auth code |
| V3 Session Management | No | No new session code |
| V4 Access Control | No | No new access control |
| V5 Input Validation | No | Spike produces a doc; no new input handling |
| V6 Cryptography | No | No new crypto primitives |

**Threat patterns specific to this spike:**

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Frozen EXE contains secrets embedded at build time | Information Disclosure | Do not pass API tokens or credentials to PyInstaller command; sensor reads credentials from `sensor.yaml` at runtime |
| Malicious package substituted for `pyinstaller` | Tampering | slopcheck [OK] verified; pin exact version `==6.20.0` in CI step |
| CI artifact (quirk.exe) treated as production binary | Elevation of Privilege | D-06 hard scope guard: artifact upload is for assessment evidence only; `retention-days: 30` limits window; add note to assessment doc warning against production use |

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on This Phase |
|-----------|---------------------|
| `python -m compileall` after changes | Only changes are CI YAML and a new doc file — no Python source changes expected |
| Keep diffs minimal — no unnecessary refactors | The `multiprocessing.freeze_support()` addition (if made) is the only source change; keep it to run_scan.py `if __name__ == "__main__"` block |
| Chaos Lab Maintenance rule | No chaos lab changes this phase — no lab.sh update needed |
| Mandatory Phase Completion Steps (Obsidian note, UAT-SERIES.md, Obsidian sync, commit) | Apply at phase end per CLAUDE.md |
| `run_scan.py` is the freeze target | `pyproject.toml` confirms `quirk = "run_scan:_run_main_with_job_guard"` and `py-modules = ["run_scan"]` |

---

## Sources

### Primary (HIGH confidence)

- PyInstaller 6.20.0 documentation — pyinstaller.org/en/stable/usage.html — CLI flags, --add-data separator, entrypoint handling
- PyInstaller 6.20.0 documentation — pyinstaller.org/en/stable/runtime-information.html — `__file__` and `sys._MEIPASS` in frozen apps
- PyInstaller 6.20.0 documentation — pyinstaller.org/en/stable/spec-files.html — spec file datas, Analysis, collect_data_files
- PyInstaller 6.20.0 documentation — pyinstaller.org/en/stable/when-things-go-wrong.html — hidden imports, --debug=imports
- PyInstaller 6.20.0 documentation — pyinstaller.org/en/stable/hooks.html — collect_submodules, collect_data_files, importlib.resources
- pyinstaller-hooks-contrib 2026.5 hooks filesystem scan (this session) — hook-cryptography.py, hook-uvicorn.py, hook-boto3.py, hook-platformdirs.py, hook-jinja2.py, hook-lxml.py confirmed present; sqlalchemy/fastapi hooks ABSENT confirmed
- Project source scan (this session) — __file__ usages in quirk/__init__.py, quirk/cli/init_cmd.py, quirk/compliance/cmvp.py, quirk/dashboard/api/app.py, quirk/reports/html_renderer.py
- pyproject.toml (this session) — entrypoint, package-data globs, dependency surface
- run_scan.py (this session) — `if __name__ == "__main__": _run_main_with_job_guard()` confirmed at line 2254-2255
- slopcheck run (this session) — pyinstaller [OK]
- PyPI registry (this session) — pyinstaller==6.20.0 confirmed current

### Secondary (MEDIUM confidence)

- github.com/sqlalchemy/sqlalchemy/discussions/10372 — SQLAlchemy dialect hidden-import patterns in PyInstaller
- github.com/pyinstaller/pyinstaller-hooks-contrib/issues/736 — cryptography hook issue in 2024.5 (resolved in later releases)
- github.com/Kludex/uvicorn/discussions/1820 — FastAPI/uvicorn PyInstaller known issues

### Tertiary (LOW confidence)

- Community knowledge on Windows AV friction with --onefile (training data, not recently verified)
- NSSM (Non-Sucking Service Manager) as service wrapper — nssm.cc; verify current version
- Effort sizing estimates — training-data analogy, not verified against recent PyInstaller packaging projects

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — PyInstaller 6.20.0 verified on PyPI; slopcheck [OK]; hooks confirmed by filesystem scan
- __file__ risk inventory: HIGH — derived from direct grep of project source
- Architecture (CI pattern): HIGH — mirrored from existing windows-sensor-smoke job
- Pitfalls: MEDIUM-HIGH — hooks corpus verified; runtime behaviour on windows-latest is [ASSUMED] for some cases
- Effort sizing: MEDIUM — analogical; actual effort revealed by spike CI result

**Research date:** 2026-05-27
**Valid until:** 2026-06-27 (PyInstaller hooks corpus updated monthly; re-verify if >30 days)
