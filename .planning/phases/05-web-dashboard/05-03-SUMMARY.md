---
plan: 05-03
phase: 05-web-dashboard
status: complete
completed: 2026-03-31
commits:
  - 04bc8cb
  - 594e643
---

# Plan 05-03: React/Vite Frontend Scaffold

## What Was Built

Scaffolded the React frontend at `src/dashboard/` with Vite + TypeScript, shadcn/ui, Tailwind dark-mode, ThemeProvider, sidebar navigation, and all API type definitions.

## Key Files Created

- `src/dashboard/package.json` — Vite + React + shadcn/ui dependencies
- `src/dashboard/vite.config.ts` — build output to `quirk/dashboard/static/`
- `src/dashboard/tailwind.config.ts` — `darkMode: "class"`, zinc base color
- `src/dashboard/tsconfig.app.json` — paths: `@/*` → `./src/*`
- `src/dashboard/src/main.tsx` — React entry with StrictMode
- `src/dashboard/src/App.tsx` — BrowserRouter with placeholder routes for all 5 views + /print
- `src/dashboard/src/components/theme-provider.tsx` — defaultTheme=dark, storageKey=quirk-ui-theme
- `src/dashboard/src/components/mode-toggle.tsx` — light/dark/system toggle
- `src/dashboard/src/components/sidebar.tsx` — collapsible nav sidebar
- `src/dashboard/src/types/api.ts` — TypeScript types mirroring Pydantic schemas
- `src/dashboard/src/components/ui/` — 13 shadcn/ui components

## Verification

- `npm --prefix src/dashboard run build` exits 0 ✓
- `quirk/dashboard/static/index.html` exists after build ✓
- ThemeProvider wraps App with `defaultTheme="dark"`, `storageKey="quirk-ui-theme"` ✓
- `tailwind.config.ts` contains `darkMode: "class"` ✓

## Decisions

- Fixed: shadcn init placed components in literal `src/dashboard/@/components/ui/` — moved to correct `src/dashboard/src/components/ui/` and added tsconfig `paths` for `@` alias
- Build artifacts committed to `quirk/dashboard/static/` so `quirk serve` works without a local Node.js build step
- Default Vite boilerplate assets (react.svg, hero.png) retained for now, replaced in later plans
