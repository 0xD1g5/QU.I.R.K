# Technology Stack

**Analysis Date:** 2026-04-02

## Languages

**Primary:**
- Python 3.10+ (required), 3.14 in active `.venv` - Core scanner, CLI, API, CBOM pipeline
- TypeScript 5.9 - React dashboard frontend (`src/dashboard/`)

**Secondary:**
- HTML/CSS (Jinja2-rendered) - Standalone offline reports (`quirk/reports/templates/`)

## Runtime

**Environment:**
- CPython 3.14.3 (active `.venv` at `/Volumes/.../QUIRK/.venv`, Python@3.14 via Homebrew)
- A second venv `.venv2` also exists at Python 3.14.3 — likely a legacy/test environment, not used in CI
- Node.js (version unspecified) — frontend build only (`src/dashboard/`)

**Package Manager:**
- Python: pip + setuptools (via `pyproject.toml`)
- Node: npm (lockfile: `src/dashboard/package-lock.json` — present)
- Lockfile: No `requirements.txt` at project root — pyproject.toml pinning only with `>=` ranges

## Frameworks

**Core (Python):**
- FastAPI `>=0.128.8` (optional `dashboard` extra) - Dashboard REST API (`quirk/dashboard/api/`)
- SQLAlchemy `>=2.0` - ORM for SQLite persistence (`quirk/db.py`, `quirk/models.py`)
- Jinja2 `>=3.1.0` - Offline HTML report templating (`quirk/reports/html_renderer.py`)

**Core (TypeScript):**
- React `^19.2.4` - Dashboard UI (`src/dashboard/src/`)
- React Router DOM `^7.4.0` - SPA client-side routing
- Vite `^8.0.1` - Frontend build tool (`src/dashboard/`)
- Tailwind CSS `^3.4.19` - Styling
- shadcn/ui (via `@radix-ui/*`) - UI component primitives

**Dashboard UI Libraries:**
- `@radix-ui/*` (dialog, label, progress, select, separator, slot, tabs, tooltip) - Component primitives
- `@tanstack/react-table ^8.21.3` - Findings table
- `recharts ^2.15.4` - Score/readiness charts
- `cytoscape ^3.33.1` + `cytoscape-cose-bilkent` + `cytoscape-dagre` - CBOM graph visualization
- `dagre ^0.8.5` - Graph layout
- `lucide-react ^0.474.0` - Icon set
- `next-themes ^0.4.6` - Light/dark mode

**Testing:**
- pytest (Python) - No version pinned in pyproject.toml, in venv
- No JavaScript test framework present

**Build/Dev:**
- uvicorn `>=0.39.0[standard]` (optional `dashboard` extra) - ASGI server for dashboard
- Playwright `>=1.58.0` (optional `dashboard` extra) - Headless Chromium for PDF export
- TypeScript compiler (`tsc`) - Type checking and build
- ESLint `^9.39.4` + `eslint-plugin-react-hooks` + `eslint-plugin-react-refresh` - Linting

## Key Dependencies

**Critical (always installed):**
- `cryptography >=44.0` (46.0.6 installed) - TLS cert parsing, public key inspection (`quirk/scanner/tls_scanner.py`)
- `SQLAlchemy >=2.0` (2.0.48 installed) - Only database layer; no migrations framework present
- `cyclonedx-python-lib >=11.7.0,<12` (11.7.0 installed) - CycloneDX 1.6 CBOM JSON/XML output (`quirk/cbom/`)
- `PyYAML >=6.0` - Config file parsing (`quirk/config.py`)
- `rich >=13.0.0` - CLI tables, progress display (`quirk/reports/writer.py`)
- `httpx >=0.28.0` - JWKS endpoint fetching in JWT scanner (`quirk/scanner/jwt_scanner.py`)
- `jinja2 >=3.1.0` - HTML report templates (`quirk/reports/html_renderer.py`)

**Declared but NOT imported anywhere in `quirk/` package code:**
- `PyJWT >=2.12.0` - Listed in `pyproject.toml` runtime deps; no `import jwt` or `import PyJWT` found anywhere in `quirk/`
- `python-jose >=3.5.0` - Listed in `pyproject.toml` runtime deps; no `from jose import` found anywhere in `quirk/`
- Both are installed in `.venv` (PyJWT 2.12.1, python-jose 3.5.0). Both packages provide JWT encode/decode but serve different APIs. Neither is called by any scanner or report module.

**Cloud connectors (always installed, used conditionally):**
- `boto3 >=1.42.0` (1.42.80 installed) - AWS connector: ACM, KMS, CloudFront, ELBv2 (`quirk/scanner/aws_connector.py`)
- `azure-identity >=1.25.0` (1.25.3 installed) - Azure DefaultAzureCredential (`quirk/scanner/azure_connector.py`)
- `azure-keyvault-keys >=4.11.0` (4.11.0 installed) - Azure Key Vault key enumeration
- `azure-keyvault-certificates >=4.10.0` (4.10.0 installed) - Azure cert enumeration (imported in connector but KeyClient is the active path)
- `azure-mgmt-network >=30.2.0` (30.2.0 installed) - Azure App Gateway TLS policy enumeration

**Partially used:**
- `tqdm >=4.67.0` (4.67.3 installed) - Declared as a runtime dependency; only used as an optional `--progress` flag through `logging_util.py`. A comment in `run_scan.py` line 162 explicitly notes "tqdm removed (D-04)" and sets `tqdm = None`. The import in `logging_util.py` is guarded. Effectively dead in the normal code path.
- `python-multipart >=0.0.20` (0.0.22 installed) - Listed in `dashboard` optional extra; FastAPI uses it for form parsing, but no form endpoints are defined in the current API routes (only JSON and PDF responses).

**Optional/degrading external tools (not Python packages — system binaries):**
- `sslyze` - Optional Python package for deep TLS scanning (`quirk/scanner/tls_scanner.py`); NOT installed in `.venv` (sslyze directory absent from site-packages). Falls back gracefully to stdlib `ssl` + `cryptography`.
- `ssh-audit` - Optional system binary for SSH algorithm enumeration (`quirk/scanner/ssh_scanner.py`); located via `shutil.which("ssh-audit")`. Falls back to banner grab.
- `syft` - Optional system binary for container image scanning (`quirk/scanner/container_scanner.py`); located via `shutil.which("syft")`.
- `semgrep` - Optional system binary for source code crypto scanning (`quirk/scanner/source_scanner.py`); located via `shutil.which("semgrep")`.
- `nmap` - Optional system binary for network discovery (`quirk/discovery/nmap_provider.py`); only invoked with `--discovery nmap`.

## Configuration

**Environment:**
- No `.env` file or environment variable loading in application code
- Runtime config exclusively via `config.yaml` (YAML, parsed by `quirk/config.py`)
- Interactive prompts as fallback when no `--config` flag is passed
- `QUIRK_SERVE_PORT` environment variable used by `quirk/dashboard/api/routes/pdf.py` for dashboard PDF export (defaults to 8512)
- AWS credentials: ambient `~/.aws/credentials` or instance role via `boto3.Session`
- Azure credentials: ambient `DefaultAzureCredential` (env vars, CLI login, managed identity)

**Build:**
- `pyproject.toml` - Python package configuration, dependency declarations, entry point
- `src/dashboard/vite.config.ts` - Vite build config (output to `quirk/dashboard/static/`)
- `src/dashboard/tsconfig.json` - TypeScript config
- `src/dashboard/tailwind.config.js` - Tailwind config
- `src/dashboard/postcss.config.js` - PostCSS config

## Platform Requirements

**Development:**
- Python 3.10+ (3.14 active in `.venv`)
- Node.js + npm (for frontend builds)
- Optional: nmap (PATH), ssh-audit (PATH), syft (PATH), semgrep (PATH)
- Optional: `playwright install chromium` for PDF export (~150MB one-time download)

**Production:**
- Self-hosted; no cloud deployment target defined
- Dashboard serves locally on `127.0.0.1:8512` by default (`quirk/dashboard/server.py`)
- SQLite file at `output/quirk.db` (configurable via `config.yaml`)

## Dependency Concerns

**Dual JWT libraries (PyJWT + python-jose):**
Both `PyJWT>=2.12.0` and `python-jose>=3.5.0` are declared in `pyproject.toml` runtime dependencies and installed. Neither is imported anywhere in the `quirk/` package. These are legacy carries from the abandoned project the codebase was built on top of. They represent ~2MB of unused install weight with overlapping functionality. The JWT scanner (`quirk/scanner/jwt_scanner.py`) works entirely via JWKS HTTP discovery using `httpx` — it never decodes or signs tokens.

**tqdm partially retired:**
`tqdm` is a runtime dependency but the migration note in `run_scan.py` (line 162: "rich Progress used throughout; tqdm removed (D-04)") confirms it was replaced by `rich`. The only remaining `tqdm` usage is an optional guard in `logging_util.py` activated by `--progress`. It should be moved to `[dev]` or removed from runtime deps.

**sslyze not installed:**
`sslyze` is not in `pyproject.toml` and not installed in `.venv`. The TLS scanner silently falls back to stdlib `ssl`. This is intentional per code design but undocumented in setup instructions.

**Two virtual environments:**
`.venv` and `.venv2` both exist. `.venv2` was created for a project previously named `QuRisk` (visible in `pyvenv.cfg` path). It should be removed to avoid confusion.

---

*Stack analysis: 2026-04-02*
