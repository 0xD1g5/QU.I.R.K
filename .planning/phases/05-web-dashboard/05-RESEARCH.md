# Phase 5: Web Dashboard - Research

**Researched:** 2026-03-30
**Domain:** FastAPI + React + shadcn/ui + Cytoscape.js + Playwright PDF
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**API Architecture (UI-01)**
- D-01: FastAPI layer added under `quirk/dashboard/api/`. Launched via `quirk serve` CLI subcommand. FastAPI reads SQLite directly via SQLAlchemy — same `get_session()` / `get_engine()` from `quirk/db.py`. No new persistence layer.
- D-02: Primary endpoint: `GET /api/scan/latest` — returns the most recent scan session's endpoints, findings, scores, and CBOM summary. Response includes a `scan_id` field derived from `MAX(scanned_at)`.
- D-03: Multi-scan navigation deferred to BACK-02. v1 always shows the most recent scan.

**Frontend Bundling (UI-01, UI-02)**
- D-04: React source lives under `src/dashboard/` (project root). Pre-built static assets committed to `quirk/dashboard/static/` (index.html + assets/). FastAPI mounts this directory as StaticFiles. End users need no Node.js.
- D-05: Build toolchain: Vite + React + TypeScript. shadcn/ui for component library. `npm run build` outputs to `quirk/dashboard/static/` — run by developer, output committed.
- D-06: `quirk serve` starts uvicorn on `localhost:8512` (default, configurable via `--port`). Auto-opens browser on launch unless `--no-open` flag passed.

**Executive Dashboard (UI-02)**
- D-07: Four radial/arc score gauges — one per intelligence subscore: Hygiene, Modern TLS, Identity, Agility. Values from `compute_readiness_score()`. Overall readiness score displayed prominently above gauges.
- D-08: Severity breakdown bar chart using shadcn/ui Chart (Recharts-based) or lightweight Recharts directly.
- D-09: Confidence badge from `compute_confidence()` in `quirk/intelligence/confidence.py`.

**Findings Table + Certificate Inventory (UI-03)**
- D-10: Findings table with shadcn/ui DataTable + TanStack Table. Filterable, searchable, sortable, expandable rows.
- D-11: Certificate inventory sourced from `CryptoEndpoint` rows where `protocol = 'TLS'`.

**CBOM Viewer (UI-03)**
- D-12: Two tabs: Table and Graph (Cytoscape.js). Both in scope for Phase 5.
- D-13: Table tab — filterable/sortable columns. Algorithm names in `font-mono`.
- D-14: Graph tab — Cytoscape.js. Algorithm nodes → source system nodes. cose-bilkent force-directed. Node color encodes quantum-safety.
- D-15: Algorithm vulnerability thresholds via `config.yaml` `algorithm_overrides` in v1.

**Visualizations (UI-02)**
- D-16: Migration dependency graph — directed Cytoscape.js graph from `build_phased_roadmap()`. Dedicated "Migration Roadmap" tab or panel.
- D-17: Severity heatmap NOT in scope for Phase 5.

**PDF Export (UI-04)**
- D-18: PDF export via Playwright headless — `playwright install chromium` required (one-time, ~150MB). "Export PDF" triggers FastAPI endpoint that spawns Playwright browser, renders `/print` URL, saves as PDF.
- D-19: Print-optimized URL: `GET /print` — same data but with print CSS (no nav, no interactive controls, page breaks between sections).

**UI Design Contract**
- Design system: shadcn (New York style, Zinc base color, CSS variables ON)
- Color: Dark-first, Zinc 950/900 dominant, Sky 500 accent
- Layout: Left sidebar 240px, collapses to icon-only at < 1024px
- Typography: Inter, 14px body / 12px label / 20px heading / 28px display
- Component inventory: card, badge, button, table, tabs, input, select, separator, skeleton, tooltip, sheet, progress, chart (all from shadcn official registry)
- Third-party: cytoscape, cytoscape-cose-bilkent, @tanstack/react-table

### Claude's Discretion
- Exact Cytoscape.js layout algorithm selection (cose vs cola vs dagre) — choose based on graph density at runtime
- shadcn/ui component choices for specific UI elements (cards, badges, tabs)
- FastAPI response pagination strategy for large findings lists
- Recharts vs Victory vs shadcn Chart for score gauges and severity bars
- Whether `quirk serve` is a new argparse subcommand or a separate entry point in pyproject.toml
- Port number for uvicorn (8512 suggested — avoids common dev ports)

### Deferred Ideas (OUT OF SCOPE)
- BACK-01: Dashboard UI config panel for algorithm vulnerability thresholds
- BACK-02: Multi-scan navigation (scan selector dropdown)
- BACK-03: Severity heatmap (grid of systems × severity)

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | FastAPI API layer — scan job management, results API, serving scanner output | D-01 through D-06: FastAPI + uvicorn + StaticFiles pattern fully documented; SQLAlchemy session dependency injection pattern confirmed |
| UI-02 | React + shadcn/ui executive dashboard — score gauges, trend charts, severity heatmaps | D-07 through D-09, D-16: shadcn/ui Chart (Recharts) for bar charts; custom SVG arc for gauges; Cytoscape.js dagre for migration graph |
| UI-03 | Findings table, certificate inventory, CBOM viewer in dashboard | D-10 through D-15: TanStack Table v8 confirmed; Cytoscape.js cose-bilkent confirmed; react-cytoscapejs wrapper available |
| UI-04 | HTML report export + PDF generation via Playwright headless | D-18 through D-19: Playwright 1.58.0 confirmed; `page.pdf()` is Chromium-only but chromium is the target; print CSS media query pattern confirmed |

</phase_requirements>

---

## Summary

Phase 5 adds a local web dashboard to QU.I.R.K. — a FastAPI backend serving pre-built React static assets, accessed via `quirk serve`. The frontend renders executive score gauges, a findings table, a certificate inventory, a CBOM viewer (table + Cytoscape.js graph), and a migration roadmap graph. A Playwright headless PDF export produces the consulting deliverable. The user has also requested light/dark mode toggle support (BACK-04 in ROADMAP.md), which is in scope for this phase.

The architecture is a deliberate two-world design: developers build the frontend with Node.js and commit the built assets (`quirk/dashboard/static/`), while end users see a pure Python experience — `pip install quirk` then `quirk serve`. All data flows from the existing SQLite database through SQLAlchemy, reusing the established `get_session()` / `get_engine()` pattern. The intelligence and CBOM functions already exist and just need API wrappers. There is no net-new persistence work.

The key complexity areas are: (1) SPA routing — FastAPI must serve `index.html` for any non-API path so client-side React Router navigation works correctly; (2) Cytoscape.js layout selection at runtime based on node count; (3) Playwright graceful-degradation on PDF export when chromium is not installed; (4) the light/dark theme token set must be designed so Phase 7 branding layers on top without rework.

**Primary recommendation:** Build backend first (FastAPI skeleton + `/api/scan/latest`), then frontend in three passes: (1) scaffolding + routing + theme system, (2) data-display views (Executive, Findings, Certificates, CBOM table), (3) graph views (CBOM graph, Roadmap graph) and PDF export. This ordering validates the data contract early and isolates Playwright complexity to the final pass.

---

## Standard Stack

### Core — Backend

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.128.8 | HTTP API framework | Async-native, Pydantic validation, auto-OpenAPI docs, StaticFiles built-in |
| uvicorn | 0.39.0 | ASGI server | FastAPI's standard server; supports `--reload` for dev |
| python-multipart | 0.0.20 | Form/file upload support | Required by FastAPI for form data |
| SQLAlchemy | 2.0.37 | ORM / SQLite access | Already in project via `quirk/db.py` — no new dependency |
| playwright | 1.58.0 | Headless Chromium PDF export | `page.pdf()` is Chromium-only; full CSS/JS rendering |

### Core — Frontend

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | 19.2.4 | UI framework | Confirmed current |
| react-dom | 19.2.4 | DOM rendering | Paired with react |
| typescript | ~5.7 | Type safety | Vite TypeScript template default |
| vite | 8.0.3 | Build toolchain | Fastest HMR for dev; outputs to `quirk/dashboard/static/` |
| @vitejs/plugin-react | ~4.5 | Vite React plugin | Official Vite React integration |
| tailwindcss | ~4.1 | Utility CSS | shadcn/ui dependency |
| shadcn/ui | (init-based) | Component library | Locked in D-05; New York style, Zinc base |
| lucide-react | 1.7.0 | Icons | shadcn/ui standard icon library |
| @tanstack/react-table | 8.21.3 | Table sort/filter/pagination | Locked in D-10; shadcn DataTable pattern uses this |
| cytoscape | 3.33.1 | Graph visualization | Locked in D-14 for CBOM + roadmap graphs |
| cytoscape-cose-bilkent | 4.1.0 | Force-directed layout | Locked in D-14 for CBOM graph |
| react-router-dom | ~7.4 | SPA routing | Multi-page navigation (/, /findings, /certificates, /cbom, /roadmap, /print) |
| recharts | ~2.15 | Severity bar chart + score gauges | Used by shadcn Chart; also available directly for custom gauge |

### Supporting — Theme

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| next-themes | 0.4.6 | Dark/light/system theme management | BACK-04 light/dark toggle requirement. Works with Vite React (not Next.js-specific despite name) |

### Supporting — Frontend Dev Tooling

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| cytoscape-dagre | 2.5.0 | DAG hierarchical layout | Migration roadmap graph (DAG directed layout). Use dagre when node count > 15 or graph is a DAG |
| dagre | ~0.8.5 | dagre peer dependency | Required by cytoscape-dagre |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| cytoscape-cose-bilkent | react-flow | react-flow is heavier (React-specific), doesn't support cytoscape plugin ecosystem; cose-bilkent locked by D-14 |
| recharts (via shadcn Chart) | Victory | Recharts is default in shadcn Chart; less code, already available |
| next-themes | Custom context ThemeProvider | shadcn/ui official Vite dark mode docs recommend a custom ThemeProvider context (same pattern as next-themes, no extra dep). Either is valid. |
| playwright | WeasyPrint | WeasyPrint cannot render canvas/SVG from shadcn/ui; locked by D-18 |

**Installation — backend:**
```bash
pip install "fastapi>=0.128.8" "uvicorn[standard]>=0.39.0" "python-multipart>=0.0.20" "playwright>=1.58.0"
playwright install chromium
```

**Installation — frontend (from `src/dashboard/`):**
```bash
npm create vite@latest . -- --template react-ts
npm install
npm install @tanstack/react-table cytoscape cytoscape-cose-bilkent cytoscape-dagre dagre lucide-react recharts react-router-dom next-themes
cd src/dashboard && npx shadcn init
# Select: Style = New York, Base color = Zinc, CSS variables = Yes
npx shadcn add card badge button table tabs input select separator skeleton tooltip sheet progress chart
```

**Version verification (confirmed 2026-03-30 via npm registry):**
- vite: 8.0.3
- react: 19.2.4
- @tanstack/react-table: 8.21.3
- cytoscape: 3.33.1
- cytoscape-cose-bilkent: 4.1.0
- lucide-react: 1.7.0
- next-themes: 0.4.6

---

## Architecture Patterns

### Recommended Project Structure

```
src/dashboard/                    # React source (developer builds this)
├── src/
│   ├── components/
│   │   ├── ui/                   # shadcn generated components
│   │   ├── theme-provider.tsx    # Dark/light mode ThemeProvider
│   │   ├── mode-toggle.tsx       # Sun/Moon/System toggle button
│   │   ├── sidebar.tsx           # Fixed left sidebar nav (240px)
│   │   ├── gauges/
│   │   │   └── ScoreGauge.tsx    # SVG arc gauge component
│   │   ├── graphs/
│   │   │   ├── CbomGraph.tsx     # Cytoscape CBOM visualization
│   │   │   └── RoadmapGraph.tsx  # Cytoscape DAG visualization
│   │   └── pdf-export-button.tsx
│   ├── pages/
│   │   ├── executive.tsx         # / route
│   │   ├── findings.tsx          # /findings route
│   │   ├── certificates.tsx      # /certificates route
│   │   ├── cbom.tsx              # /cbom route
│   │   ├── roadmap.tsx           # /roadmap route
│   │   └── print.tsx             # /print route (Playwright target)
│   ├── hooks/
│   │   └── useScanData.ts        # React Query or SWR data fetching hook
│   ├── lib/
│   │   └── utils.ts              # shadcn utils (cn helper)
│   ├── types/
│   │   └── api.ts                # TypeScript types matching FastAPI response schema
│   ├── App.tsx                   # Router, ThemeProvider, Sidebar layout
│   └── main.tsx                  # Vite entry point
├── vite.config.ts                # outDir: ../../quirk/dashboard/static
├── tailwind.config.ts            # darkMode: "class"
├── package.json
└── tsconfig.json

quirk/dashboard/                  # Python package for dashboard
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── app.py                    # FastAPI app instance, StaticFiles mount, SPA fallback
│   ├── deps.py                   # DB session dependency injection
│   ├── routes/
│   │   ├── scan.py               # GET /api/scan/latest
│   │   ├── pdf.py                # POST /api/export/pdf
│   │   └── health.py             # GET /api/health
│   └── schemas.py                # Pydantic response models
├── server.py                     # quirk serve entrypoint — uvicorn.run(), browser open
└── static/                       # Pre-built React assets (committed)
    ├── index.html
    └── assets/
```

### Pattern 1: FastAPI SPA Fallback Mount

**What:** StaticFiles mounts the built React assets, with a catch-all that serves `index.html` for any path not matched by an API route.

**When to use:** Any SPA served from the same FastAPI app. Without this, `/findings` returns 404 when the user navigates directly or refreshes.

**Example:**
```python
# quirk/dashboard/api/app.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI()

# API routes registered first
app.include_router(scan_router, prefix="/api")
app.include_router(pdf_router, prefix="/api")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

# SPA fallback — must come AFTER API routes
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    index = os.path.join(STATIC_DIR, "index.html")
    return FileResponse(index)

# Mount assets directory (CSS/JS/fonts) separately
app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")
```

### Pattern 2: FastAPI SQLAlchemy Dependency Injection

**What:** FastAPI `Depends()` pattern wraps `get_session()` from `quirk/db.py` for clean per-request DB sessions.

**When to use:** Every endpoint that queries SQLite.

**Example:**
```python
# quirk/dashboard/api/deps.py
from typing import Generator
from sqlalchemy.orm import Session
from quirk.db import get_engine
from sqlalchemy.orm import sessionmaker

def get_db(db_path: str) -> Generator[Session, None, None]:
    engine = get_engine(db_path)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False,
                                expire_on_commit=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# In route:
@router.get("/scan/latest")
def get_latest_scan(db: Session = Depends(get_db)):
    ...
```

### Pattern 3: shadcn/ui Vite Dark Mode ThemeProvider

**What:** Custom React context ThemeProvider (shadcn/ui official Vite pattern). Applies `dark` or `light` class to `document.documentElement`. Persists to localStorage. System preference detection via `window.matchMedia`.

**When to use:** Wrap entire `<App />` in `main.tsx`. Toggle component reads `useTheme()` hook.

**Example (from shadcn/ui official Vite dark mode docs):**
```typescript
// src/components/theme-provider.tsx
import { createContext, useContext, useEffect, useState } from "react"

type Theme = "dark" | "light" | "system"

type ThemeProviderProps = {
  children: React.ReactNode
  defaultTheme?: Theme
  storageKey?: string
}

const ThemeProviderContext = createContext<{theme: Theme; setTheme: (t: Theme) => void}>({
  theme: "system",
  setTheme: () => null,
})

export function ThemeProvider({
  children,
  defaultTheme = "dark",       // dark-first per UI-SPEC
  storageKey = "quirk-ui-theme",
}: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem(storageKey) as Theme) || defaultTheme
  )

  useEffect(() => {
    const root = window.document.documentElement
    root.classList.remove("light", "dark")
    if (theme === "system") {
      const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
      root.classList.add(systemTheme)
    } else {
      root.classList.add(theme)
    }
  }, [theme])

  return (
    <ThemeProviderContext.Provider value={{ theme, setTheme: (t) => {
      localStorage.setItem(storageKey, t)
      setTheme(t)
    }}}>
      {children}
    </ThemeProviderContext.Provider>
  )
}

export const useTheme = () => useContext(ThemeProviderContext)
```

**Tailwind config:** `darkMode: "class"` in `tailwind.config.ts`.

**Light mode token set** (parallel to dark-first UI-SPEC tokens):
```css
/* globals.css — light mode overrides on :root.light */
.light {
  --background: 0 0% 100%;       /* white */
  --card: 0 0% 98%;              /* near-white cards */
  --foreground: 240 10% 8%;      /* near-black text */
  --border: 240 5% 88%;          /* light gray borders */
  --muted: 240 4% 46%;           /* muted text */
  --accent: 210 100% 56%;        /* Sky 500 — same as dark mode */
}
```

### Pattern 4: Cytoscape.js React Integration

**What:** Mount Cytoscape into a React `ref` via `useEffect`. Register layout extensions (cose-bilkent, dagre) once at module level. Destroy cy instance on unmount.

**When to use:** Both CBOM graph and Roadmap graph.

**Example:**
```typescript
// src/components/graphs/CbomGraph.tsx
import cytoscape from "cytoscape"
import coseBilkent from "cytoscape-cose-bilkent"
import dagre from "cytoscape-dagre"

cytoscape.use(coseBilkent)
cytoscape.use(dagre)

export function CbomGraph({ elements }: { elements: cytoscape.ElementDefinition[] }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
    const layoutName = elements.length < 15 ? "breadthfirst" : "cose-bilkent"
    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      layout: { name: layoutName, roots: "#algo" },
      style: [...],
    })
    return () => cyRef.current?.destroy()
  }, [elements])

  return <div ref={containerRef} style={{ width: "100%", height: "100%", minHeight: 400 }}
              role="img" aria-label="CBOM algorithm-to-system dependency graph" />
}
```

### Pattern 5: Playwright PDF Export Endpoint

**What:** FastAPI endpoint spawns async Playwright browser, navigates to `/print` URL on localhost, calls `page.pdf()`, saves to temp file, returns file as response. Graceful-degradation if Playwright not installed.

**When to use:** `POST /api/export/pdf` endpoint.

**Example:**
```python
# quirk/dashboard/api/routes/pdf.py
import asyncio, os, tempfile
from fastapi import HTTPException
from fastapi.responses import FileResponse
from datetime import datetime

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

async def export_pdf(port: int = 8512):
    if not PLAYWRIGHT_AVAILABLE:
        raise HTTPException(503, detail=(
            "Playwright not installed. Run: playwright install chromium"
        ))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = os.path.join(tempfile.gettempdir(), f"quirk-report-{stamp}.pdf")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"http://localhost:{port}/print", wait_until="networkidle")
        await page.pdf(path=out_path, format="A4", print_background=True)
        await browser.close()
    return FileResponse(out_path, media_type="application/pdf",
                        filename=f"quirk-report-{stamp}.pdf")
```

### Pattern 6: quirk serve argparse Subcommand

**What:** Add `subparsers` to the existing `argparse.ArgumentParser` in `run_scan.py` — `quirk scan` for current behavior, `quirk serve` for dashboard.

**When to use:** Extending `run_scan:main` via subparsers (cleanest approach — single entry point in pyproject.toml).

**Example:**
```python
# run_scan.py main()
subparsers = parser.add_subparsers(dest="command")

scan_parser = subparsers.add_parser("scan", help="Run a cryptographic scan")
# ... add all existing scan args to scan_parser ...

serve_parser = subparsers.add_parser("serve", help="Start the web dashboard")
serve_parser.add_argument("--port", type=int, default=8512)
serve_parser.add_argument("--no-open", action="store_true")
serve_parser.add_argument("--config", help="Path to config.yaml")

args = parser.parse_args()
if args.command == "serve" or args.command is None and not args.config:
    from quirk.dashboard.server import run_server
    run_server(port=args.port, no_open=args.no_open)
```

**Alternative:** Add a second entry point to `pyproject.toml`:
```toml
[project.scripts]
quirk = "run_scan:main"
quirk-serve = "quirk.dashboard.server:run_server_cli"
```

The subparser approach is preferred: single command `quirk serve`, consistent with the success criteria ("Running `quirk serve`").

### Anti-Patterns to Avoid

- **No SPA fallback route:** React Router navigation (e.g., refreshing `/findings`) returns 404. Always register a `/{full_path:path}` catch-all that serves `index.html` for non-API, non-asset paths.
- **Cytoscape in SSR context:** Cytoscape.js accesses `window` — ensure it only runs in a browser `useEffect`, never during SSR. (Not applicable here since we're in Vite SPA mode, but guard against server-side rendering assumptions.)
- **Cytoscape layout registered twice:** Calling `cytoscape.use(coseBilkent)` at component mount (inside `useEffect`) will error if the component remounts. Register layouts at module scope, outside the component.
- **Playwright in sync FastAPI route:** `playwright.sync_api` blocks the event loop. Use `playwright.async_api` with `async def` endpoint. Playwright and uvicorn are both async-native.
- **Building React assets inside pip package:** Do not include `src/dashboard/node_modules/` or `src/dashboard/src/` in the sdist/wheel. Only `quirk/dashboard/static/` ships. Add `src/dashboard/` to `.gitignore` exclusions from the Python build manifest.
- **Relative paths in Vite build:** Set `base: "./"` in `vite.config.ts` so asset paths in `index.html` are relative, not absolute. This is required for FastAPI's StaticFiles to serve them correctly regardless of mount path.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Table sort/filter/pagination | Custom sort logic | @tanstack/react-table v8 | Handles virtualization, multi-sort, column visibility; locked by D-10 |
| Dark/light theme management | localStorage + class toggle manually | ThemeProvider context (shadcn/ui Vite pattern) | Handles system preference, flash-of-wrong-theme, localStorage sync |
| Force-directed graph layout | Hand-coded physics | cytoscape-cose-bilkent | Spring-embedder physics; peer-reviewed implementation from Bilkent University |
| DAG hierarchical layout | Custom tree positioning | cytoscape-dagre | Dagre is the standard for directed acyclic graphs; avoids edge crossing complexity |
| Headless PDF from HTML | Custom wkhtmltopdf wrapper or WeasyPrint | Playwright `page.pdf()` | Only Playwright renders canvas/SVG correctly; WeasyPrint fails on shadcn Chart output |
| Score arc gauge | Third-party gauge library | Custom SVG arc via `<circle>` stroke-dashoffset | Gauge libraries add 50KB+ for a feature that is 20 lines of SVG math; shadcn does not have a native gauge — build it with SVG |
| ASGI server | Custom HTTP server | uvicorn | Standard ASGI server for FastAPI; do not use Flask or HTTP.server |
| SPA routing | Server-side routing | React Router DOM v7 + FastAPI catch-all | SPAs must own their routing client-side |

**Key insight:** The intelligence and CBOM layers are already built. The hardest API work is query assembly from `CryptoEndpoint` rows — do not rebuild the scoring or CBOM pipeline in the API layer; call the existing Python functions directly.

---

## Common Pitfalls

### Pitfall 1: SPA Route 404 on Refresh
**What goes wrong:** User navigates to `/findings`, refreshes — FastAPI returns 404 because no route matches `/findings`.
**Why it happens:** FastAPI routes are exact-match unless you add a catch-all.
**How to avoid:** Register `@app.get("/{full_path:path}")` AFTER all API routes, returning `index.html`.
**Warning signs:** Works on `/` but not on any sub-route after a hard refresh.

### Pitfall 2: Vite Absolute Asset Paths
**What goes wrong:** `index.html` references `/assets/index-abc123.js` (absolute path). When FastAPI mounts assets at a different prefix, the browser can't find them.
**Why it happens:** Vite defaults to `base: "/"` (absolute paths).
**How to avoid:** Set `base: "./"` in `vite.config.ts` so paths are relative.
**Warning signs:** `index.html` loads but CSS/JS 404s in the browser console.

### Pitfall 3: Cytoscape Layout Registered Inside Component
**What goes wrong:** `cytoscape.use(coseBilkent)` called inside `useEffect` or component body — throws "Layout already registered" on remount.
**Why it happens:** `cytoscape.use()` is global, not per-instance.
**How to avoid:** Register extensions at module scope (top of the file, outside any function/component).
**Warning signs:** Graph renders once, then throws on tab switch.

### Pitfall 4: Playwright Blocking Event Loop
**What goes wrong:** Using `playwright.sync_api` inside a FastAPI async endpoint blocks uvicorn's event loop, hanging all requests during PDF generation.
**Why it happens:** sync_api wraps async in a blocking thread.
**How to avoid:** Use `playwright.async_api` with `async with async_playwright()` in an `async def` endpoint.
**Warning signs:** Server becomes unresponsive during PDF export.

### Pitfall 5: Playwright chromium Not Installed
**What goes wrong:** `playwright install chromium` is a separate step after `pip install playwright`. Without it, `p.chromium.launch()` throws `BrowserNotFoundError`.
**Why it happens:** pip install only installs the Python bindings; the browser binary requires a second step.
**How to avoid:** Wrap the launch in try/except and return a 503 with the install instruction. Show a banner on the dashboard if chromium isn't detected.
**Warning signs:** PDF export button triggers a 500 error with no helpful message.

### Pitfall 6: Dark Mode Flash-of-Wrong-Theme (FOUC)
**What goes wrong:** On page load, screen flashes white (wrong theme) before the ThemeProvider reads localStorage and applies the dark class.
**Why it happens:** React hydrates before the `useEffect` that sets the class runs.
**How to avoid:** Add an inline `<script>` in `index.html` that reads localStorage and sets the class on `<html>` before React loads. The shadcn/ui Vite pattern includes this.
**Warning signs:** Visible white flash on every page load in dark mode.

### Pitfall 7: Print Route Renders Interactive Controls
**What goes wrong:** PDF generated from `/print` includes sidebar, buttons, and interactive filter controls, wasting page space and appearing unprofessional.
**Why it happens:** `/print` route reuses the same layout without hiding navigation.
**How to avoid:** `/print` is a completely separate route that renders a print-only layout — no sidebar, no nav, no Sheet/Modal components. CSS `@media print` rules also needed as a fallback.
**Warning signs:** PDF includes a sidebar or "Export PDF" button in the output.

### Pitfall 8: SQLite check_same_thread with FastAPI
**What goes wrong:** SQLite raises "SQLite objects created in a thread can only be used in that same thread" in an async FastAPI context.
**Why it happens:** Default SQLite behavior; each request may run on a different thread.
**How to avoid:** `connect_args={"check_same_thread": False}` is already set in `quirk/db.py:get_engine()`. Do not bypass this or create a new engine without this flag.
**Warning signs:** Intermittent 500 errors on concurrent requests to `/api/scan/latest`.

---

## Code Examples

### GET /api/scan/latest — Query Assembly

```python
# quirk/dashboard/api/routes/scan.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from quirk.models import CryptoEndpoint
from quirk.intelligence.scoring import compute_readiness_score
from quirk.intelligence.confidence import compute_confidence
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.roadmap import build_phased_roadmap
from quirk.cbom.builder import build_cbom
from quirk.cbom.classifier import quantum_safety_label

def get_latest_scan(db: Session):
    # Derive scan_id from max scanned_at timestamp (D-02/D-03)
    max_ts = db.query(func.max(CryptoEndpoint.scanned_at)).scalar()
    if max_ts is None:
        return {"scan_id": None, "endpoints": [], "findings": [], "scores": None}

    endpoints = db.query(CryptoEndpoint).filter(
        CryptoEndpoint.scanned_at == max_ts
    ).all()

    # Build intelligence outputs (reuse existing functions)
    evidence = build_evidence_summary(endpoints)
    scores = compute_readiness_score(evidence)
    confidence = compute_confidence(evidence)
    roadmap = build_phased_roadmap(scores, evidence)

    return {
        "scan_id": max_ts.isoformat(),
        "scanned_at": max_ts.isoformat(),
        "endpoint_count": len(endpoints),
        "scores": scores,
        "confidence": confidence,
        "roadmap": roadmap,
        # ... findings, cbom_summary ...
    }
```

### Vite Config — Output to quirk/dashboard/static/

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  base: "./",          // CRITICAL: relative paths for StaticFiles mount
  build: {
    outDir: path.resolve(__dirname, "../../quirk/dashboard/static"),
    emptyOutDir: true,
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") }
  }
})
```

### SVG Arc Score Gauge (Custom — 20 lines)

```typescript
// src/components/gauges/ScoreGauge.tsx
interface ScoreGaugeProps { score: number; label: string; size?: number }

export function ScoreGauge({ score, label, size = 120 }: ScoreGaugeProps) {
  const r = size * 0.4
  const cx = size / 2, cy = size / 2
  const circumference = Math.PI * r   // half-circle arc
  const filled = (score / 100) * circumference
  const color = score >= 80 ? "hsl(142 71% 45%)" : score >= 50 ? "hsl(38 92% 50%)" : "hsl(0 72% 51%)"
  return (
    <svg width={size} height={size * 0.6} aria-label={`${label}: ${score}`}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="hsl(240 6% 17%)" strokeWidth={8}
              strokeDasharray={`${circumference} ${circumference}`}
              strokeDashoffset={0} transform={`rotate(180 ${cx} ${cy})`} />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={8}
              strokeDasharray={`${filled} ${circumference}`}
              strokeLinecap="round" transform={`rotate(180 ${cx} ${cy})`} />
      <text x={cx} y={cy - 4} textAnchor="middle" fontSize={size * 0.22} fontWeight={600}
            fill="currentColor">{score}</text>
    </svg>
  )
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| WeasyPrint for Python PDF | Playwright headless Chromium | ~2022 | Playwright renders canvas/SVG correctly; WeasyPrint doesn't support JS-rendered charts |
| Flask + Jinja templates | FastAPI + pre-built React SPA | ~2021 | Type-safe API contract, async-native, OpenAPI docs free |
| wkhtmltopdf | Playwright page.pdf() | ~2023 | wkhtmltopdf is unmaintained; Playwright supports CSS Grid/Flexbox/SVG |
| shadcn/ui v1 (Next.js-only) | shadcn/ui v2 (framework-agnostic with Vite support) | 2024 | Official Vite init path; works outside Next.js |
| TanStack Table v7 | TanStack Table v8 | 2023 | Headless, framework-agnostic API; hooks-based |

**Deprecated/outdated:**
- `wkhtmltopdf`: Unmaintained since 2023; no CSS Grid/Flexbox support. Do not use.
- `react-table < 8`: Old API, package name changed to `@tanstack/react-table`. Do not import `react-table`.
- `cytoscape-cose` (built-in): Less sophisticated than cose-bilkent. Use the external `cytoscape-cose-bilkent` package.

---

## Open Questions

1. **Arc gauge implementation: custom SVG vs Recharts RadialBar**
   - What we know: shadcn/ui has no native gauge component. Recharts has `RadialBarChart`. Custom SVG is ~20 lines and zero dependency.
   - What's unclear: Whether RadialBarChart meets the exact visual spec (arc gauge, not full circle) with the right fill colors.
   - Recommendation: Use custom SVG arc (recommended above). Lower bundle cost, full control over the half-circle arc shape specified in UI-SPEC.

2. **`quirk serve` as subparser vs new entry point**
   - What we know: Both approaches work. CONTEXT.md lists this as Claude's discretion.
   - What's unclear: Whether breaking backwards compatibility of `quirk` (which currently maps to `run_scan:main` with no subcommands) is a concern.
   - Recommendation: Subparser approach — `quirk scan` and `quirk serve`. Breaking change is version-appropriate (this is v4.0). Alternatively, keep `quirk` as-is and add `quirk-serve` entry point for zero breaking change.

3. **Light mode color token completeness**
   - What we know: UI-SPEC is dark-first; light mode is BACK-04 (now in scope per user note). The dark token set is fully specified in UI-SPEC. Light mode needs a parallel token set.
   - What's unclear: Whether light mode should mirror the quantum-safety semantic colors exactly or use slightly different hues for contrast on white.
   - Recommendation: Keep semantic colors identical (Green 500 / Amber 500 / Red 600 for quantum safety). Change only background/card/text/border tokens. Verify 4.5:1 contrast ratios for all text on light backgrounds before shipping.

4. **Findings list assembly — engine vs direct DB query**
   - What we know: Findings are generated by `quirk/engine/risk_engine.py:evaluate_endpoints()` — they are derived, not stored. There is no `findings` table in SQLite.
   - What's unclear: Whether findings should be regenerated on each API call (CPU cost) or stored during scan and read back.
   - Recommendation: Regenerate on demand in the API call — `evaluate_endpoints()` is fast (CPU-only, no I/O). This avoids a schema migration and matches the "no new persistence layer" decision in D-01. Cache in FastAPI memory if latency becomes an issue.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | FastAPI backend | Yes | 3.14.3 | — |
| Node.js | Frontend build | Yes | 25.8.2 | — |
| npm | Frontend build | Yes | 11.11.1 | — |
| SQLAlchemy | DB access | Yes (in project) | 2.0.37 | — |
| fastapi | API server | No (not installed) | — | Install in Wave 0 |
| uvicorn | ASGI server | No (not installed) | — | Install in Wave 0 |
| playwright (pip) | PDF export | No (not installed) | — | Graceful-degrade: 503 with install instructions |
| playwright chromium | PDF export | No (not installed) | — | Graceful-degrade: banner + 503 |
| pytest | Tests | No (not installed) | — | Install in Wave 0 |
| Vite / React / shadcn | Frontend | No (src/dashboard/ not created) | — | Create in Wave 0 |

**Missing dependencies with no fallback:**
- `fastapi`, `uvicorn`, `pytest` — must be installed before any implementation. Add to `pyproject.toml` optional dependency group `[project.optional-dependencies] serve = [...]` and test requirements.

**Missing dependencies with fallback:**
- `playwright` + chromium — PDF export degrades gracefully with a 503 response and a user-visible error banner. The rest of the dashboard functions without Playwright installed.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (not yet installed — Wave 0 task) |
| Config file | None — add `[tool.pytest.ini_options]` to `pyproject.toml` in Wave 0 |
| Quick run command | `python -m pytest tests/test_dashboard_api.py -x -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | `GET /api/scan/latest` returns 200 with scores + endpoints | unit (FastAPI TestClient) | `python -m pytest tests/test_dashboard_api.py::test_latest_scan_endpoint -x` | Wave 0 |
| UI-01 | `GET /api/health` returns 200 | unit | `python -m pytest tests/test_dashboard_api.py::test_health_endpoint -x` | Wave 0 |
| UI-01 | `GET /` serves index.html (StaticFiles) | unit | `python -m pytest tests/test_dashboard_api.py::test_spa_serves_index -x` | Wave 0 |
| UI-01 | `GET /findings` (SPA route) serves index.html | unit | `python -m pytest tests/test_dashboard_api.py::test_spa_fallback -x` | Wave 0 |
| UI-02 | Score data structure has total + 4 sub-scores | unit | `python -m pytest tests/test_dashboard_api.py::test_score_structure -x` | Wave 0 |
| UI-03 | Findings list includes severity + host + title | unit | `python -m pytest tests/test_dashboard_api.py::test_findings_structure -x` | Wave 0 |
| UI-03 | CBOM data includes algorithm + quantum_safety | unit | `python -m pytest tests/test_dashboard_api.py::test_cbom_structure -x` | Wave 0 |
| UI-04 | PDF export returns 503 when Playwright not installed | unit | `python -m pytest tests/test_dashboard_api.py::test_pdf_export_no_playwright -x` | Wave 0 |
| UI-04 | `/print` route serves index.html (for Playwright) | unit | `python -m pytest tests/test_dashboard_api.py::test_print_route -x` | Wave 0 |

Frontend testing (React components) is manual in Phase 5 — browser-based verification of the UI against the UI-SPEC. Playwright-based e2e tests for the frontend are out of scope until Phase 7.

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_dashboard_api.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_dashboard_api.py` — FastAPI TestClient tests for all UI-01 through UI-04 API behaviors
- [ ] `tests/conftest.py` — extend existing (if any) or create shared fixture: in-memory SQLite DB with seeded CryptoEndpoint rows
- [ ] `pyproject.toml` — add `[project.optional-dependencies] serve = ["fastapi>=0.128.8", "uvicorn[standard]>=0.39.0", "playwright>=1.58.0"]` and `[tool.pytest.ini_options]`
- [ ] Install: `pip install "fastapi>=0.128.8" "uvicorn[standard]>=0.39.0" pytest httpx` (httpx required for FastAPI TestClient async mode)

---

## Sources

### Primary (HIGH confidence)
- npm registry — vite@8.0.3, react@19.2.4, @tanstack/react-table@8.21.3, cytoscape@3.33.1, cytoscape-cose-bilkent@4.1.0, lucide-react@1.7.0, next-themes@0.4.6 (verified 2026-03-30)
- pip registry — fastapi@0.128.8, uvicorn@0.39.0, playwright@1.58.0 (verified 2026-03-30)
- [shadcn/ui Vite dark mode docs](https://ui.shadcn.com/docs/dark-mode/vite) — ThemeProvider pattern, tailwind config
- [FastAPI StaticFiles docs](https://fastapi.tiangolo.com/tutorial/static-files/) — mount pattern
- [Playwright Python page.pdf() API](https://playwright.dev/python/docs/api/class-page) — PDF generation, Chromium-only constraint
- [cytoscape-cose-bilkent GitHub](https://github.com/cytoscape/cytoscape.js-cose-bilkent) — layout registration pattern
- Project source: `quirk/db.py`, `quirk/models.py`, `quirk/config.py`, `quirk/intelligence/scoring.py`, `quirk/intelligence/confidence.py`, `quirk/intelligence/roadmap.py`, `quirk/reports/writer.py` — all read directly

### Secondary (MEDIUM confidence)
- [FastAPI + React SPA pattern (Medium)](https://medium.com/@asafshakarzy/embedding-a-react-frontend-inside-a-fastapi-python-package-in-a-monorepo-c00f99e90471) — StaticFiles + catch-all SPA pattern
- [Playwright PDF generation guide (Checkly)](https://www.checklyhq.com/docs/learn/playwright/generating-pdfs/) — print CSS + page.pdf() options
- [DEV Community Vite dark mode with shadcn](https://dev.to/ashsajal/implementing-lightdark-mode-in-your-vite-app-with-shadcnui-1ae4) — Vite implementation without Next.js

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against npm/pip registries 2026-03-30
- Architecture: HIGH — patterns verified against official FastAPI, shadcn/ui, and Playwright docs
- Pitfalls: HIGH — SPA fallback, Vite base path, Cytoscape layout registration, Playwright async are well-documented failure modes with confirmed mitigations
- Light/dark mode: HIGH — shadcn/ui official Vite docs provide the exact pattern

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (30-day window; all libraries are stable with no major releases expected)
