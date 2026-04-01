# Phase 7: Polish and Packaging - Research

**Researched:** 2026-03-31
**Domain:** Python CLI UX (rich), Jinja2 HTML report generation, Playwright PDF rendering, pip GitHub install, React/shadcn theme pass
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Visual Identity (BRAND-01)**
- D-01: Styled wordmark only — typography-based treatment, `QU.I.R.K.` in a monospace/tech font with electric-blue accent. No illustrative icon needed for v1.
- D-02: Color palette: dark backgrounds with electric-blue accent (navy/slate base, bright blue highlight). Complements the existing shadcn/ui dark theme.
- D-03: Branding appears on all surfaces: report headers (HTML/PDF), dashboard navbar + favicon, and CLI startup banner.

**CLI UX (BRAND-02)**
- D-04: Add `rich` library as a core dependency (not optional). Replace tqdm + plain `print()` calls with rich progress bars, spinners, colored severity levels, and phase timing output. Full rich treatment throughout scan execution.
- D-05: Add a final scan summary table rendered by rich after every scan completes — shows hosts scanned, findings by severity, readiness score, output files written. Replaces the current scattered `print("✅ Wrote reports: ...")` lines.
- D-06: Add `--version` flag to CLI: `quirk --version` returns the current version string sourced from `quirk/__init__.py __version__`.
- D-07: Add CLI startup banner (ASCII/styled) displaying `QU.I.R.K.` wordmark and version when running `quirk scan` or `quirk serve`. Dismissible / suppressible with `--quiet`.

**Report HTML/PDF Templates (BRAND-03)**
- D-08: New standalone HTML report template using Jinja2. `write_reports()` produces a self-contained single-file `report.html` (embedded CSS, no external dependencies) alongside the existing Markdown report.
- D-09: HTML report contains both executive and technical sections: executive summary (score gauges, severity breakdown, top findings, transition roadmap, CBOM summary) + full technical appendix (all endpoints, raw findings, cert inventory). Single file, scrollable.
- D-10: HTML report reuses existing data builders — `executive.py` and `technical.py` already assemble all required data. Phase 7 adds a Jinja2 renderer consuming the same data dicts. No refactor of data assembly logic.
- D-11: PDF = Playwright renders the standalone HTML report (same Playwright dependency already in `[dashboard]` optional group). PDF shares the same data as HTML — no separate PDF pipeline.
- D-12: QU.I.R.K. branding in report: wordmark header, electric-blue accent colors, professional layout with score band color coding (red/amber/green).

**Dashboard Branding (BRAND-01 + UI-02)**
- D-13: Full theme pass of the React dashboard — audit every shadcn/ui component color token, update to the defined palette (dark + electric blue). Update navbar with QU.I.R.K. wordmark, set favicon.

**Distribution + Packaging (BRAND-04)**
- D-14: GitHub-based install as the distribution target: `pip install 'git+https://github.com/[owner]/quirk.git[dashboard]'`. No PyPI publication in Phase 7.
- D-15: `quirk init` subcommand generates a `config.yaml` from a bundled template with sensible defaults and inline comments. Enables zero-to-scan without manual config editing.
- D-16: Version bumped to `4.0.0` in `pyproject.toml` and `quirk/__init__.py`. Manual bump + `git tag v4.0.0`. No bump2version tooling added.

### Claude's Discretion
- Jinja2 template layout details (section ordering, table styling, fonts)
- Rich theme/style specifics (exact colors, spinner style)
- ASCII banner art style and dimensions
- Playwright PDF page size and margins

### Deferred Ideas (OUT OF SCOPE)
- MkDocs/Material skin for docs/ — plain Markdown stays
- PyPI publication — deferred post-Phase 7
- CHANGELOG / semantic-release tooling — not added; manual version bump only
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BRAND-01 | QU.I.R.K. visual identity — name treatment, color palette, logo mark for reports and dashboard | D-01/D-02/D-03: palette already defined in index.css CSS vars; report header and dashboard navbar are the two remaining surfaces |
| BRAND-02 | CLI UX polish — rich progress indicators, consistent output formatting, version command | `rich` 13.9.4 already in .venv; `tqdm` 4.67.1 also present (to be replaced); argparse `action='version'` is the `--version` pattern |
| BRAND-03 | Professional report templates — HTML + PDF with QU.I.R.K. branding and consultant-grade layout | Jinja2 3.1.6 available in system Python but NOT in .venv — must be added as dependency; Playwright 1.58.0 + chromium already installed |
| BRAND-04 | Packaging + installer — pip install quirk or single-file distribution; zero-to-scan < 10 min on fresh machine | GitHub-based `pip install git+https://...` works with setuptools; `quirk init` subcommand mirrors existing `serve` intercept pattern |
</phase_requirements>

---

## Summary

Phase 7 is a pure polish phase: no new scanner logic, no new API endpoints. It threads four concerns — CLI UX overhaul, standalone HTML/PDF report generation, React dashboard theme pass, and GitHub-based distribution — across a codebase that already has the core infrastructure in place.

The biggest risk is the Jinja2 self-contained HTML report. `executive.py` and `technical.py` return Markdown strings, not data dicts. The planner must decide whether to (a) pass `endpoints` and `findings` directly to the Jinja2 renderer or (b) extract data from the Markdown string builders. Option (a) is cleaner — Jinja2 templates can iterate `endpoints` and `findings` lists directly, bypassing the Markdown intermediary. This aligns with D-10 ("reuses existing data builders") — the builders already have the data, the renderer simply consumes the same inputs with a different output format.

Jinja2 is not yet in the project's `.venv` or `pyproject.toml` — it must be added as a core dependency. Everything else (`rich` 13.9.4, `playwright` 1.58.0, chromium installed) is already available. The dashboard CSS variable system (`index.css`) already has the correct electric-blue palette (`--primary: 210 100% 56%`) — the theme pass is editing tokens that already exist, not designing from scratch.

**Primary recommendation:** Structure work as four independent tracks (CLI UX, HTML/PDF reports, dashboard theme, packaging) with a final integration track. Each track has well-defined entry points with no cross-track dependencies.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `rich` | 13.9.4 (in .venv) | CLI progress bars, tables, panels, styled output | Already installed; D-04 locks it as core dep |
| `jinja2` | 3.1.6 (system Python, NOT in .venv) | HTML report templating | Industry standard for Python HTML templating; must be added to pyproject.toml |
| `playwright` | 1.58.0 (in .venv) | Headless Chromium → PDF | Already in `[dashboard]` optional group; chromium binary confirmed installed |
| `argparse` | stdlib | CLI argument parsing (--version, init subcommand) | Existing pattern in run_scan.py; no migration needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tqdm` | 4.67.1 (in .venv) | Legacy progress bar | Currently used with `--progress` flag; replaced by `rich` in this phase |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Jinja2 | string f-templates | Jinja2 supports inheritance, filters, loops — required for complex multi-section HTML report |
| Playwright PDF | weasyprint / pdfkit | Playwright already in dependency graph; weasyprint has complex system deps (cairo, pango) |
| argparse --version | Click/Typer | argparse already used throughout; migration out of scope per CONTEXT.md |

**Installation (additions to pyproject.toml):**
```bash
# Add to [project] dependencies:
"jinja2>=3.1.0"
"rich>=13.0.0"
```

**Version verification:**
```bash
# In .venv:
pip show rich       # → 13.9.4
pip show playwright # → 1.58.0
# jinja2 is NOT yet in .venv — confirmed missing
pip show jinja2     # → WARNING: Package(s) not found: jinja2
```

---

## Architecture Patterns

### Recommended Project Structure

New files this phase introduces:

```
quirk/
├── reports/
│   ├── writer.py          # existing — HTML/PDF steps inserted here (after Markdown writes)
│   ├── executive.py       # existing — data source for HTML renderer
│   ├── technical.py       # existing — data source for HTML renderer
│   ├── html_renderer.py   # NEW — Jinja2 renderer, produces self-contained HTML
│   └── templates/
│       └── report.html.j2 # NEW — Jinja2 template (embedded CSS, no CDN)
├── cli/
│   └── banner.py          # NEW — ASCII wordmark + version banner
└── __init__.py            # existing — __version__ bump to "4.0.0"
```

Dashboard changes:
```
src/dashboard/src/
├── index.css              # existing — CSS var updates for theme pass
├── components/
│   └── layout/
│       └── Navbar.tsx     # existing — add QU.I.R.K. wordmark
└── public/
    └── favicon.svg        # NEW — QU.I.R.K. favicon (SVG)
```

### Pattern 1: Rich CLI Integration

**What:** Replace `tqdm` + `print()` calls in `run_scan.py` and `writer.py` with `rich` console, progress, and table primitives.

**When to use:** Every user-facing output call in `run_scan.py` and `writer.py`.

**Key insight on tqdm replacement:** `run_scan.py` uses `tqdm` only when `--progress` flag is passed. With `rich`, progress bars can always be displayed (rich handles terminal detection gracefully). The `tqdm` import block at lines 136-139 becomes a rich Progress context manager.

**Example — rich progress bar:**
```python
# Source: rich docs — Progress class
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn

with Progress(SpinnerColumn(), "[progress.description]{task.description}",
              TimeElapsedColumn()) as progress:
    task = progress.add_task("Fingerprinting...", total=len(targets))
    for result in results:
        progress.advance(task)
```

**Example — rich summary table (replaces writer.py print block):**
```python
from rich.console import Console
from rich.table import Table

console = Console()
table = Table(title="QU.I.R.K. Scan Summary", show_header=True)
table.add_column("Metric", style="bold cyan")
table.add_column("Value", justify="right")
table.add_row("Hosts scanned", str(hosts_count))
table.add_row("CRITICAL findings", f"[red]{crit_count}[/red]")
table.add_row("Readiness score", f"[bold]{score}/100[/bold]")
console.print(table)
```

**Example -- --version flag (argparse):**
```python
# Source: Python argparse docs — action='version'
# In run_scan.py parser setup (before args = parser.parse_args()):
from quirk import __version__
parser.add_argument("--version", action="version", version=f"QU.I.R.K. v{__version__}")
```

**The `--quiet` suppression pattern:** Pass a `quiet: bool` flag through to any function that calls `console.print()`. With rich, a `Console(quiet=True)` silences all output. Create a module-level console that can be swapped.

### Pattern 2: Jinja2 Self-Contained HTML Report

**What:** A Jinja2 template that produces a single `.html` file with all CSS inlined (no CDN, no external fonts, no JavaScript dependencies beyond inline `<style>` and minimal `<script>`).

**Critical constraint from CONTEXT.md D-08:** Self-contained, works offline. Air-gapped client engagements.

**Data flow — what to pass to the Jinja2 renderer:**

The existing `build_exec_markdown()` and `build_tech_markdown()` functions in `executive.py` and `technical.py` return Markdown strings — they do NOT return structured data dicts. The HTML renderer must receive `endpoints`, `findings`, `score`, `conf`, `roadmap_items`, and `cfg` directly — the same inputs that `write_reports()` already has when it calls the Markdown builders.

```python
# Source: writer.py write_reports() existing call site
# HTML renderer inserts AFTER existing Markdown writes (step 2) and BEFORE stats write (step 4)

from quirk.reports.html_renderer import render_html_report

html_path = os.path.join(outdir, f"report-{stamp}.html")
render_html_report(
    path=html_path,
    cfg=cfg,
    endpoints=endpoints,
    findings=findings,
    score=score,          # already computed in write_reports()
    conf=conf,            # already computed
    roadmap_items=roadmap_items,  # already computed
)
```

**Jinja2 template pattern — self-contained CSS:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>QU.I.R.K. — {{ cfg_name }} Quantum Readiness Report</title>
  <style>
    /* All CSS embedded here — no external references */
    :root {
      --bg: #0a0a0f;
      --accent: #3b9dff;  /* electric blue: hsl(210 100% 56%) */
      --critical: #e53935;
      --high: #f57c00;
      --medium: #f9a825;
      --low: #5c9cff;
    }
    /* ... full stylesheet ... */
  </style>
</head>
<body>
  <header class="report-header">
    <span class="wordmark">QU.I.R.K.</span>
    <span class="report-meta">{{ generated_at }} | {{ cfg_name }}</span>
  </header>
  <!-- executive section -->
  <!-- technical appendix -->
</body>
</html>
```

**Jinja2 renderer module pattern:**
```python
# quirk/reports/html_renderer.py
from jinja2 import Environment, PackageLoader, select_autoescape

def render_html_report(path, cfg, endpoints, findings, score, conf, roadmap_items):
    env = Environment(
        loader=PackageLoader("quirk", "reports/templates"),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html.j2")
    html = template.render(
        cfg_name=cfg.assessment.name,
        report_owner=cfg.assessment.report_owner,
        data_classification=cfg.assessment.data_classification,
        generated_at=...,
        score=score,
        conf=conf,
        roadmap_items=roadmap_items,
        findings=findings,
        endpoints=endpoints,
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
```

**PackageLoader requirement:** When using `PackageLoader("quirk", "reports/templates")`, the `quirk/reports/templates/` directory must be included in the package via `pyproject.toml`. With `[tool.setuptools.packages.find]` using `include = ["quirk*"]`, the templates directory needs explicit inclusion via `package_data` or `MANIFEST.in`. Use `FileSystemLoader` from an absolute path as a simpler alternative:

```python
# Simpler — avoids package_data complexity:
import os
from jinja2 import Environment, FileSystemLoader

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

def render_html_report(...):
    env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR), autoescape=...)
```

### Pattern 3: Playwright Standalone PDF

**What:** After writing `report.html`, use Playwright to open the local file and export to PDF.

**Existing PDF code in `quirk/dashboard/api/routes/pdf.py`** (Phase 5) renders the dashboard URL. Phase 7 standalone PDF renders a local file path instead.

```python
# Source: playwright Python docs + existing quirk/dashboard/api/routes/pdf.py pattern
from playwright.sync_api import sync_playwright

def render_pdf_from_html(html_path: str, pdf_path: str) -> None:
    """Render a local HTML file to PDF using Playwright headless chromium."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        # Use file:// URI for local files
        page.goto(f"file://{os.path.abspath(html_path)}", wait_until="networkidle")
        page.pdf(
            path=pdf_path,
            format="A4",
            print_background=True,
            margin={"top": "20mm", "bottom": "20mm",
                    "left": "15mm", "right": "15mm"},
        )
        browser.close()
```

**Graceful degradation:** Wrap in try/except. If Playwright or chromium is not installed (CLI-only install without `[dashboard]`), skip PDF generation and log a message. Do NOT raise.

```python
try:
    from quirk.reports.pdf_renderer import render_pdf_from_html
    pdf_path = os.path.join(outdir, f"report-{stamp}.pdf")
    render_pdf_from_html(html_path, pdf_path)
except ImportError:
    logger.info("PDF export skipped — install quirk[dashboard] for PDF support")
except Exception as e:
    logger.info(f"PDF export failed: {e}")
    pdf_path = None
```

### Pattern 4: `quirk init` Subcommand

**What:** New subcommand following the same intercept pattern as `quirk serve`.

**Current pattern (run_scan.py lines 80-107):**
```python
if len(_sys.argv) > 1 and _sys.argv[1] == "serve":
    serve_parser = argparse.ArgumentParser(prog="quirk serve", ...)
    ...
    return
```

**`quirk init` follows the same pattern:**
```python
if len(_sys.argv) > 1 and _sys.argv[1] == "init":
    import shutil, os
    dest = _sys.argv[2] if len(_sys.argv) > 2 else "config.yaml"
    template_path = os.path.join(os.path.dirname(__file__), "quirk", "config_template.yaml")
    if os.path.exists(dest):
        print(f"[!] {dest} already exists. Use --force to overwrite.")
        return
    shutil.copy(template_path, dest)
    print(f"[ok] Created {dest} — edit targets.cidrs/fqdns, then run: quirk --config {dest}")
    return
```

**Template file location:** `quirk/config_template.yaml` — bundled inside the package. Must be declared in `pyproject.toml` package_data to survive `pip install`.

**pyproject.toml addition for package data:**
```toml
[tool.setuptools.package-data]
quirk = ["config_template.yaml", "reports/templates/*.j2"]
```

### Pattern 5: GitHub-based pip install

**What:** Replace Phase 6 "coming in v4.0" callout in `docs/getting-started.md` with the GitHub install path.

**How pip handles git+https install with extras:**
```bash
pip install 'git+https://github.com/OWNER/REPO.git#egg=quirk[dashboard]'
# or with a tag:
pip install 'git+https://github.com/OWNER/REPO.git@v4.0.0#egg=quirk[dashboard]'
```

**Confirmed working:** setuptools-based packages install correctly from `git+https://` with extras. The `[project.scripts]` entry point (`quirk = "run_scan:main"`) is preserved. The `run_scan.py` file at repo root is included because `[tool.setuptools.packages.find]` uses `include = ["quirk*"]` — but `run_scan.py` is NOT under `quirk/`. This is an existing issue: `run_scan.py` is the entry point but lives at repo root, outside the `quirk` package. Setuptools `py_modules` declaration is needed:

```toml
# REQUIRED addition to pyproject.toml for run_scan.py to be installed:
[tool.setuptools]
py-modules = ["run_scan"]
```

Without this, `pip install git+https://...` will install the `quirk` package but the `quirk` CLI entry point will fail with `ModuleNotFoundError: No module named 'run_scan'`.

### Pattern 6: Dashboard Theme Pass

**What:** The `src/dashboard/src/index.css` already defines the correct palette as CSS variables. The theme pass is verifying every component uses tokens (not hardcoded colors) and updating the navbar.

**Current state — already done (Phase 5):**
```css
/* index.css — confirmed present */
--primary: 210 100% 56%;       /* electric blue */
--accent: 210 100% 56%;        /* same */
--quantum-safe: 142 71% 45%;   /* green */
--quantum-vulnerable: 0 72% 51%; /* red */
```

**What remains:**
1. Audit all `.tsx` files for hardcoded hex/hsl colors (should use CSS vars or `hsl(var(--name))`)
2. Add `QU.I.R.K.` wordmark text to the Navbar component
3. Add `public/favicon.svg` — a simple SVG using the electric-blue accent

**Tailwind config integration:** Tailwind is configured in the project. Custom CSS vars map to Tailwind via the `tailwind.config.js` `extend.colors` section. Existing pattern uses shadcn/ui convention (CSS vars + `hsl()` wrapper in Tailwind config).

### Anti-Patterns to Avoid

- **Separate PDF data pipeline:** D-11 is explicit — PDF renders the HTML file, not a separate data assembly. Never build a second data pipeline for PDF.
- **External CSS/JS in HTML report:** Report must work offline. No CDN links, no Google Fonts, no external scripts. All CSS embedded in `<style>` tags.
- **tqdm as a fallback:** `tqdm` should be fully replaced in run_scan.py for scan phases. The `--progress` flag argument can be repurposed to control rich verbosity level rather than tqdm toggling.
- **Hardcoded colors in Jinja2 template:** Use CSS variables in the template, not hardcoded hex values. This makes the report consistent with the dashboard palette.
- **`PackageLoader` without package_data:** If using `PackageLoader` for Jinja2 templates, `quirk/reports/templates/` must appear in `[tool.setuptools.package-data]` or templates will not be found after `pip install`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress bars | Custom print-based progress | `rich.progress.Progress` | Thread-safe, handles multiple concurrent tasks, auto-detects terminal width |
| HTML escaping in report | Manual `str.replace("<", "&lt;")` | Jinja2 `autoescape=True` | Jinja2 autoescaping handles all edge cases including attribute injection |
| PDF generation from HTML | wkhtmltopdf subprocess, weasyprint | `playwright` (already installed) | Already in deps, chromium already installed, produces print-accurate PDF |
| CLI version flag | Manual `if args.version:` check | `argparse action='version'` | Built-in; handles `--version` and `-V`; exits cleanly |
| Config file discovery | Custom path resolution | Bundled template + `shutil.copy` | Simple, no magic; user knows exactly where the file is |

**Key insight:** Every "don't hand-roll" item here has an existing solution already in the project's dependency graph. The implementation cost is integration, not dependency introduction.

---

## Runtime State Inventory

> This is a packaging/polish phase, not a rename/refactor phase. Runtime state is not relevant. Omitted.

---

## Common Pitfalls

### Pitfall 1: `run_scan.py` Not Found After pip install

**What goes wrong:** `quirk` CLI fails with `ModuleNotFoundError: No module named 'run_scan'` after installing from GitHub.

**Why it happens:** `run_scan.py` lives at the repository root, outside the `quirk/` package directory. `[tool.setuptools.packages.find]` with `include = ["quirk*"]` picks up the `quirk` package but NOT `run_scan.py`. The entry point `quirk = "run_scan:main"` requires the module to be importable.

**How to avoid:** Add to `pyproject.toml`:
```toml
[tool.setuptools]
py-modules = ["run_scan"]
```

**Warning signs:** `pip install -e .` works (editable install with PYTHONPATH including repo root) but `pip install git+https://...` fails.

### Pitfall 2: Jinja2 Templates Not Included in Distribution

**What goes wrong:** `quirk` reports `jinja2.exceptions.TemplateNotFound: report.html.j2` after pip install even though the file exists in the repo.

**Why it happens:** Python packages only include `.py` files by default. `*.j2` template files must be explicitly declared in package data.

**How to avoid:**
```toml
[tool.setuptools.package-data]
quirk = ["reports/templates/*.j2", "config_template.yaml"]
```

**Warning signs:** Works in editable install (`pip install -e .`), fails after `pip install git+https://...`.

### Pitfall 3: Playwright PDF Blocks on `--progress` / `--quiet` rich Console

**What goes wrong:** Rich's live console (Progress display) and Playwright's subprocess execution can conflict if rich is still rendering when Playwright launches chromium. This causes garbled terminal output or hangs.

**Why it happens:** Rich's `Live` / `Progress` context manager holds the terminal. Playwright spawns a subprocess.

**How to avoid:** Ensure the rich `Progress` context manager exits before `render_pdf_from_html()` is called. Place the Playwright PDF call in `write_reports()` after all rich output is complete (rich console output happens at end of `main()`, not during `write_reports()`).

**Warning signs:** Terminal output freezes after scan completes; PDF file created but terminal stuck.

### Pitfall 4: `executive.py` Returns Markdown Strings, Not Data Dicts

**What goes wrong:** Developer tries to parse the Markdown string from `build_exec_markdown()` to extract data for the HTML template. This is fragile and unnecessary.

**Why it happens:** The function signature `build_exec_markdown(cfg, endpoints, findings) -> str` looks like the only way to get executive data.

**How to avoid:** Pass `cfg`, `endpoints`, `findings`, `score`, `conf`, `roadmap_items` directly to `render_html_report()`. These are all already computed inside `write_reports()` before the Markdown functions are called.

**Warning signs:** Any code that uses `re.search()` or `.split("\n")` on Markdown output to extract data for the HTML template.

### Pitfall 5: `quirk init` Overwrites Existing Config

**What goes wrong:** Running `quirk init` in a directory with an existing `config.yaml` silently overwrites client-specific configuration.

**Why it happens:** Simple `shutil.copy()` with no guard.

**How to avoid:** Check for existing file before writing. Only overwrite with explicit `--force` flag.

### Pitfall 6: Rich Console Output in Tests

**What goes wrong:** Test output is polluted with rich's ANSI escape codes, or tests fail because rich tries to render to a non-TTY.

**Why it happens:** Rich auto-detects terminal capabilities. In pytest, stdout is captured and not a TTY.

**How to avoid:** Create the rich `Console` with `Console(stderr=False)` or accept a `console` parameter in functions that output. In tests, pass `Console(quiet=True)` or mock console output. Rich's default behavior (no color when not a TTY) handles most cases automatically.

### Pitfall 7: Version String Out of Sync

**What goes wrong:** `quirk --version` returns `3.9.0` after bump, or version in `writer.py` (`PLATFORM_VERSION = "3.9"`) is stale.

**Why it happens:** Version string exists in three places: `quirk/__init__.py`, `pyproject.toml`, and `quirk/reports/writer.py` (`PLATFORM_VERSION`).

**How to avoid:** `writer.py` should import from `quirk.__version__` rather than hardcoding. As part of the version bump, update all three locations.

---

## Code Examples

### Rich Banner / Startup Panel

```python
# Source: rich docs — Panel, Text
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

def print_banner(version: str, quiet: bool = False) -> None:
    if quiet:
        return
    console = Console()
    title = Text("QU.I.R.K.", style="bold cyan")
    subtitle = Text(f"Quantum Infrastructure Readiness Kit  v{version}", style="dim")
    console.print(Panel.fit(title + "\n" + subtitle, border_style="cyan"))
```

### Rich Severity Coloring

```python
# Severity → rich style mapping
SEVERITY_STYLE = {
    "CRITICAL": "bold red",
    "HIGH":     "red",
    "MEDIUM":   "yellow",
    "LOW":      "blue",
    "INFO":     "dim",
}

def severity_text(sev: str) -> str:
    style = SEVERITY_STYLE.get(sev.upper(), "white")
    return f"[{style}]{sev}[/{style}]"
```

### argparse --version Flag

```python
# Source: Python docs — argparse action='version'
# In run_scan.py, after creating parser:
from quirk import __version__
parser.add_argument(
    "--version",
    action="version",
    version=f"QU.I.R.K. v{__version__}",
)
```

### `quirk init` Subcommand Intercept

```python
# Pattern mirrors existing `serve` subcommand in run_scan.py lines 80-107
if len(_sys.argv) > 1 and _sys.argv[1] == "init":
    import shutil as _shutil
    dest = _sys.argv[2] if len(_sys.argv) > 2 else "config.yaml"
    force = "--force" in _sys.argv
    _template = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "quirk", "config_template.yaml"
    )
    if os.path.exists(dest) and not force:
        print(f"config.yaml already exists. Use: quirk init {dest} --force")
        return
    _shutil.copy(_template, dest)
    print(f"Created {dest} — edit targets section, then: quirk --config {dest}")
    return
```

### Playwright PDF (standalone file)

```python
# Source: Playwright Python docs — page.pdf()
def render_pdf_from_html(html_path: str, pdf_path: str) -> None:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(
            f"file://{os.path.abspath(html_path)}",
            wait_until="networkidle",
        )
        page.pdf(
            path=pdf_path,
            format="A4",
            print_background=True,
            margin={"top": "20mm", "bottom": "20mm",
                    "left": "15mm", "right": "15mm"},
        )
        browser.close()
```

### Jinja2 FileSystemLoader (preferred over PackageLoader)

```python
# Source: Jinja2 docs — FileSystemLoader
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

def _get_env() -> "Environment":
    return Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "j2"]),
    )
```

### pyproject.toml Complete Package Data Config

```toml
[tool.setuptools]
py-modules = ["run_scan"]

[tool.setuptools.packages.find]
include = ["quirk*"]

[tool.setuptools.package-data]
quirk = ["reports/templates/*.j2", "config_template.yaml"]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| tqdm for progress | rich Progress | This phase | rich handles multi-task, spinners, color; tqdm is single-bar only |
| Scattered `print()` summary | rich Table summary | This phase | Structured, aligned, professional output |
| `--progress` flag for tqdm | always-on rich output | This phase | Rich detects TTY and gracefully degrades in non-interactive contexts |
| Markdown-only reports | HTML + PDF alongside Markdown | This phase | Consultants can hand a client a professional-looking PDF |

**Deprecated/outdated:**
- `tqdm` import in `run_scan.py` (lines 136-139): replaced by rich Progress; `tqdm` dependency can be removed from `.venv` after replacement (not a declared dependency in `pyproject.toml` — it was always an implicit dependency)
- `PLATFORM_VERSION = "3.9"` string in `writer.py`: should import from `quirk.__version__` after bump

---

## Open Questions

1. **Does `executive.py` need a data-dict variant, or is passing raw inputs to Jinja2 sufficient?**
   - What we know: `build_exec_markdown()` accepts `(cfg, endpoints, findings)` and returns a Markdown string; `write_reports()` also calls `build_evidence_summary()`, `compute_readiness_score()`, etc. and has all computed data.
   - What's unclear: Whether the Jinja2 template should receive just `(cfg, endpoints, findings)` (re-computing internally) or the already-computed `score`, `conf`, `roadmap_items` (passed from `write_reports()`).
   - Recommendation: Pass the already-computed values from `write_reports()`. This avoids double-computation and keeps the renderer stateless.

2. **`--quiet` flag scope**
   - What we know: D-07 says banner is suppressible with `--quiet`. Current `run_scan.py` parser has `--verbose` but not `--quiet`.
   - What's unclear: Whether `--quiet` suppresses only the banner or all rich output.
   - Recommendation: `--quiet` suppresses banner + rich progress output, keeping only error-level messages. This is the standard Unix convention.

3. **GitHub repo URL for pip install docs update**
   - What we know: D-14 specifies `pip install 'git+https://github.com/[owner]/quirk.git[dashboard]'` — `[owner]` is a placeholder.
   - What's unclear: The actual repo URL.
   - Recommendation: Documentation update uses the placeholder; planner should add a task to fill in the real URL, or leave it as `[owner]` for the user to complete.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (3.14) | All Python tasks | ✓ | 3.14.3 (.venv) | — |
| pytest | Test suite | ✓ | 9.0.2 (.venv) | — |
| rich | CLI UX (BRAND-02) | ✓ | 13.9.4 (.venv) | — |
| jinja2 | HTML report (BRAND-03) | MISSING from .venv | 3.1.6 (system Python only) | Must add to pyproject.toml and install |
| playwright (Python) | PDF export (BRAND-03) | ✓ | 1.58.0 (.venv) | Skip PDF, log message |
| Chromium binary | PDF export | ✓ | v145 (ms-playwright/chromium-1208) | Already installed at ~/Library/Caches/ms-playwright |
| node.js | Vite dashboard build | ✓ | v25.8.2 | — |
| npm | Vite dashboard build | ✓ | 11.11.1 | — |
| tqdm | Current run_scan.py | ✓ | 4.67.1 (.venv) | Replaced by rich |

**Missing dependencies with no fallback:**
- `jinja2` is not in `.venv` or `pyproject.toml` — Wave 0 must `pip install jinja2>=3.1.0` and add it to `[project] dependencies`.

**Missing dependencies with fallback:**
- `playwright`/Chromium: if not installed, PDF export skips gracefully with informative message.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (configfile: pyproject.toml — confirmed by pytest run) |
| Quick run command | `.venv/bin/python -m pytest tests/test_brand*.py -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -q` |

**Baseline:** 148 tests, all passing. Full suite runs in ~2 seconds.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BRAND-01 | HTML report contains `QU.I.R.K.` wordmark in `<header>` | unit | `pytest tests/test_html_report.py::test_report_contains_wordmark -x` | ❌ Wave 0 |
| BRAND-01 | Dashboard index.css sets `--primary: 210 100% 56%` | unit | `pytest tests/test_dashboard_theme.py::test_primary_color_token -x` | ❌ Wave 0 |
| BRAND-02 | `quirk --version` returns version string from `__init__.py` | smoke | `pytest tests/test_cli_version.py::test_version_flag -x` | ❌ Wave 0 |
| BRAND-02 | `write_reports()` uses rich console (no raw print calls for summary) | unit | `pytest tests/test_rich_output.py::test_scan_summary_uses_rich -x` | ❌ Wave 0 |
| BRAND-03 | `render_html_report()` produces valid HTML with embedded CSS | unit | `pytest tests/test_html_report.py::test_html_is_self_contained -x` | ❌ Wave 0 |
| BRAND-03 | HTML report includes score, severity counts, and CBOM section | unit | `pytest tests/test_html_report.py::test_html_report_sections -x` | ❌ Wave 0 |
| BRAND-03 | PDF generation skips gracefully when playwright unavailable | unit | `pytest tests/test_html_report.py::test_pdf_graceful_degradation -x` | ❌ Wave 0 |
| BRAND-04 | `quirk init` creates config.yaml from template | unit | `pytest tests/test_cli_init.py::test_init_creates_config -x` | ❌ Wave 0 |
| BRAND-04 | `quirk init` does not overwrite existing config without --force | unit | `pytest tests/test_cli_init.py::test_init_no_overwrite -x` | ❌ Wave 0 |
| BRAND-04 | pyproject.toml declares run_scan as py-module | smoke | `pytest tests/test_packaging.py::test_run_scan_importable -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/ -q` (2 seconds — run full suite; it's fast)
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -q` — full suite
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_html_report.py` — covers BRAND-01 (wordmark), BRAND-03 (self-contained HTML, sections, PDF degradation)
- [ ] `tests/test_cli_version.py` — covers BRAND-02 (`--version` flag)
- [ ] `tests/test_rich_output.py` — covers BRAND-02 (rich summary table in write_reports)
- [ ] `tests/test_cli_init.py` — covers BRAND-04 (`quirk init` subcommand)
- [ ] `tests/test_packaging.py` — covers BRAND-04 (`run_scan` importable after install, package data present)
- [ ] `tests/test_dashboard_theme.py` — covers BRAND-01 (CSS token audit)
- [ ] Install Jinja2: `.venv/bin/pip install "jinja2>=3.1.0"` + add to `pyproject.toml [project] dependencies`

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `run_scan.py`, `quirk/reports/writer.py`, `quirk/reports/executive.py`, `quirk/reports/technical.py`, `quirk/__init__.py`, `pyproject.toml` — all read at research time
- Direct environment probe: `.venv/bin/pip list` — confirmed rich 13.9.4, playwright 1.58.0, jinja2 ABSENT
- Direct test run: `148 tests, all passing` — confirmed baseline
- `src/dashboard/src/index.css` — confirmed CSS variable palette already set

### Secondary (MEDIUM confidence)
- Python argparse stdlib docs — `action='version'` pattern is standard and stable
- Playwright Python docs pattern for `page.goto("file://...")` — consistent with existing `quirk/dashboard/api/routes/pdf.py` pattern
- Jinja2 `FileSystemLoader` preference over `PackageLoader` — standard pattern when template path is known at runtime

### Tertiary (LOW confidence)
- `py-modules = ["run_scan"]` requirement in pyproject.toml for root-level modules — verified by setuptools behavior with `pip install -e .` vs `pip install git+https://` distinction (requires validation in test environment)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions confirmed by direct .venv inspection
- Architecture: HIGH — integration points identified from direct code read of writer.py, run_scan.py
- Pitfalls: HIGH for Pitfall 1 (py-modules) and Pitfall 2 (package-data) — these are known setuptools packaging traps; MEDIUM for Pitfall 3 (rich/playwright conflict) — derived from understanding of both libraries' behavior
- Test gaps: HIGH — confirmed no test files for BRAND-* requirements exist

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stable libraries; packaging behavior is version-stable)
