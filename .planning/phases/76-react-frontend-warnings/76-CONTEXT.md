# Phase 76: React Frontend WARNINGs - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Close all 11 open WARNING-severity audit findings in the React frontend (`react-frontend/WR-02, WR-04..WR-13`). WR-01, WR-03, WR-14 already closed by Phase 62 (HOOK-01..04). Frontend bug fixes only — no new components, no new pages, no new design contracts. Dashboard must still build cleanly via `npm run build` in `src/dashboard/`.

**In scope (mapped to REACT-NN requirements):**

- **REACT-01** — API error surfacing: `useScanList` exposes non-OK responses, executive `body.detail` coerces safely, print sentinel respects QRAMM error state, QRAMM `submitError` shows actual API message (closes WR-02, WR-06, WR-07, WR-08)
- **REACT-02** — localStorage / PDF / re-fetch correctness: Theme value validated, executive PDF `setTimeout` revoke runs on unmount, ComplianceMapTab re-fetches only on targeted dependency (closes WR-04, WR-05, WR-13)
- **REACT-03** — Cert regex / CBOM typing / Scorecard math: Subject CN regex handles RFC-2253 escaped commas, Cytoscape registration uses module augmentation, Maturity Distribution width math + correct class mapping (closes WR-09, WR-10, WR-11, WR-12)

**Out of scope:**

- INFO/code-quality findings (Phase 77)
- All BLOCKER rows (closed in Phase 58, 62, 64)
- WR-01, WR-03, WR-14 (already closed by Phase 62)
- Any change to React component structure / route hierarchy — D-12 do-not-touch
- New Tailwind tokens or shadcn primitives — D-12 do-not-touch
- Recharts component swaps — D-12 do-not-touch (Recharts static-children requirement from prior memory still applies)

</domain>

<decisions>
## Implementation Decisions

### useScanList API error surfacing (REACT-01 / WR-02)

- **D-01 (locked):** `src/dashboard/src/hooks/useScanList.ts` currently catches non-OK responses and returns an empty list silently. Add `error: string | null` to the hook's return shape; on `!response.ok`, set `error = response.statusText || 'Failed to load scans'` AND set scans to `[]`. Callers (the scans list page) check `error` before rendering the empty state — show a user-visible error banner with a retry button. Researcher confirms whether callers already destructure `error` from related hooks (consistency).

### executive body.detail coercion (REACT-01 / WR-06)

- **D-02 (locked):** Executive page reads `body.detail` from API error responses without checking if `body` is an object or a string. Fix: `const detail = (body && typeof body === 'object' && typeof body.detail === 'string') ? body.detail : String(body ?? 'Unknown error')`. Avoids `Cannot read properties of undefined` on raw-string error responses.

### print data-ready sentinel guards QRAMM error (REACT-01 / WR-07)

- **D-03 (locked):** `src/dashboard/src/pages/print.tsx` (or wherever the print page lives) sets the `data-ready` DOM sentinel that the PDF renderer waits for. Currently set even when QRAMM has errored. Fix: only set sentinel when QRAMM state is `loaded` OR `n/a` (no QRAMM session). If `errored`, leave sentinel unset and add a visible "QRAMM data unavailable — Q section omitted" alert. PDF renderer should NOT capture an incomplete page.

### QRAMM submitError exposes API message (REACT-01 / WR-08)

- **D-04 (locked):** `src/dashboard/src/pages/qramm-profile.tsx` `submitError` state currently shows a generic "Submit failed" string. Fix: extract the API error message via the same coercion pattern as D-02, set as `submitError: string`. User sees the real reason (e.g., "Organization Name required" instead of "Submit failed").

### Theme localStorage allowlist (REACT-02 / WR-04)

- **D-05 (locked):** `src/dashboard/src/components/theme-provider.tsx`:
  ```typescript
  const VALID_THEMES = ['light', 'dark', 'system'] as const;
  type Theme = typeof VALID_THEMES[number];
  function getStoredTheme(): Theme {
      const raw = localStorage.getItem('theme');
      return (VALID_THEMES as readonly string[]).includes(raw ?? '') ? (raw as Theme) : 'system';
  }
  ```
  Silently falls back to `'system'` on invalid value. No console warn (theme is QoL, not security).

### executive PDF setTimeout revoke on unmount (REACT-02 / WR-05)

- **D-06 (locked):** Executive PDF download uses `setTimeout(() => URL.revokeObjectURL(blobUrl), 0)` which can leak if the user navigates away mid-download. Fix: store the timer ID in a ref; `useEffect` cleanup function calls `clearTimeout(timerRef.current); URL.revokeObjectURL(blobUrl)`. Standard React effect-cleanup pattern.

### ComplianceMapTab targeted re-fetch (REACT-02 / WR-13)

- **D-07 (locked):** `ComplianceMapTab` currently `useEffect`'s dependency array includes the entire `ctx.scoreResult` object, triggering a re-fetch on ANY scoreResult change. Narrow dependency to `ctx.scoreResult?.session_id` (or whichever stable identity field exists — researcher confirms). Eliminates spurious refetch loop. Existing Phase 55 fix (Calculate Score button + Recharts static-children) preserved.

### Cert Subject CN regex RFC-2253 (REACT-03 / WR-09)

- **D-08 (locked):** Certificate Subject CN regex currently matches `CN=([^,]+)` which breaks on RFC-2253 escaped commas (`CN=O\\,reilly`). Fix: regex `/CN=((?:[^,\\]|\\.)*)(,|$)/` captures CN values including escaped commas; post-process the captured group with `.replace(/\\(.)/g, '$1')` to unescape. Researcher confirms the exact module path (likely `src/dashboard/src/pages/certificates.tsx` or `src/dashboard/src/lib/cert-parse.ts`).

### Cytoscape module augmentation (REACT-03 / WR-10)

- **D-09 (locked):** Create `src/dashboard/src/types/cytoscape-augment.d.ts`:
  ```typescript
  import 'cytoscape';
  declare module 'cytoscape' {
      function use(extension: unknown): void;
  }
  ```
  Remove the `(cytoscape as any).use(coseBilkent)` cast in `cbom.tsx` (or wherever the registration happens). Module augmentation is the idiomatic cytoscape-ecosystem pattern.

### ScorecardTab Maturity Distribution + badge classes (REACT-03 / WR-11, WR-12)

- **D-10 (locked):**
  - WR-11: Replace hardcoded `/4` with a module-level `const MATURITY_MAX = 4` (or import from a shared `lib/qramm-constants.ts` if such file exists). Width formula: `width = `${(score / MATURITY_MAX) * 100}%``. Add an explicit guard: if `score === null` (the new "Indeterminate" sentinel from Phase 74), render an em-dash instead of a bar.
  - WR-12: Maturity bar fill currently uses `text-*` / `border-*` classes (which color the text/border, leaving the bar empty). Switch to `bg-*` Tailwind classes. Map:
    - Beginner → `bg-red-500`
    - Foundational → `bg-orange-500`
    - Intermediate → `bg-yellow-500`
    - Advanced → `bg-green-500`
    - Indeterminate → `bg-gray-300` (matches em-dash treatment)

### Phase-76 do-not-touch list

- **D-12 (locked):**
  - Component structure, route hierarchy, page-level layouts — bug fixes only, no restructuring
  - New Tailwind tokens, new shadcn primitives — none added
  - Recharts components — Phase 55/64 Recharts static-children requirement still applies (`fillOpacity` toggle, not conditional mount/unmount)
  - Phase 62 hooks (HOOK-01..04) — already closed; no re-touching
  - Phase 58 dashboard API hardening (CSRF, CORS, rate-limit) — out of scope
  - Phase 65/66 dashboard scan-history/clone-compare — preserved exactly
  - QRAMM 120-question taxonomy — Phase 74 boundary

</decisions>

<canonical_refs>
## Canonical References

- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — 11 open `react-frontend/WR-*` rows
- `.planning/audit-2026-05-08/react-frontend/REVIEW.md` — file:line citations
- `.planning/REQUIREMENTS.md` — REACT-01..REACT-03
- `.planning/ROADMAP.md` Phase 76 — 3 SCs (gating)
- `.planning/phases/62-react-hook-cancellation/` (if exists) — Phase 62 HOOK-01..04 precedent for hook cancellation guards
- `.planning/phases/65-66-dashboard-*` — preserved exactly (D-12)
- `src/dashboard/src/hooks/useScanList.ts` — WR-02 site
- `src/dashboard/src/components/theme-provider.tsx` — WR-04 site
- `src/dashboard/src/pages/qramm-profile.tsx` — WR-08 site
- `src/dashboard/src/pages/cbom.tsx` (or similar) — WR-10 Cytoscape site
- `src/dashboard/src/pages/scorecard.tsx` or `src/dashboard/src/components/ScorecardTab.tsx` — WR-11, WR-12 site

</canonical_refs>

<code_context>
## Reusable Assets / Patterns

- **Phase 62 cancellation-guard pattern** — `useEffect` cleanup with `cancelled` ref boolean; D-06 setTimeout cleanup mirrors this shape
- **`useEffect` dependency-narrowing** — Phase 62 HOOK-02 already established the pattern of depending on a stable ID (e.g., `session.id`) rather than the whole object; D-07 follows
- **`as const` allowlist + type narrowing** — common React/TS idiom; D-05 uses it
- **Module augmentation `declare module`** — idiomatic for cytoscape/three.js/d3 ecosystems; D-09 uses it
- **Tailwind `bg-*` vs `text-*` distinction** — common mistake when porting from a static design tool; D-10 corrects
- **Recharts static-children requirement** (from project memory) — fillOpacity/strokeOpacity toggle pattern, NOT conditional mount/unmount; preserved untouched

## Build Reminder

Per memory: `.tsx` edits require `npm run build` in `src/dashboard/` before they're visible — FastAPI serves pre-built statics. Every executor commit must include the rebuilt `dist/` (or whatever the build output path is) OR the build step runs as part of CI.

</code_context>

<test_strategy>
## Test Approach

- **Frontend test framework: Vitest** (per Phase 62 precedent)
- **One test module per REACT-NN requirement** (3 modules):
  - `src/dashboard/src/hooks/__tests__/useScanList.test.ts` — REACT-01 (error surfacing)
  - `src/dashboard/src/components/__tests__/theme-provider.test.tsx` + `src/dashboard/src/pages/__tests__/print-pdf-cleanup.test.tsx` + `src/dashboard/src/pages/__tests__/compliance-map-tab.test.tsx` — REACT-02
  - `src/dashboard/src/pages/__tests__/scorecard-maturity.test.tsx` + `src/dashboard/src/lib/__tests__/cert-parse.test.ts` + `src/dashboard/src/types/__tests__/cytoscape-augment.test.ts` — REACT-03
- **RED-then-GREEN** per fix. D-08 parametrized table includes RFC-2253 escape cases: `CN=O\,reilly`, `CN=Smith\\, John`, `CN=plain,O=Corp`, `CN=plain`.
- **D-05 parametrized**: `'light'`, `'dark'`, `'system'`, `'banana'`, `''`, `null`.
- **D-10 parametrized**: all 4 maturity bands + 'Indeterminate' with `score=null`.
- **Build verification**: `npm run build` in `src/dashboard/` must exit 0 before any plan calls itself done.
- **No new HUMAN-UAT** — internal fixes; existing UAT-46/55/65/66 cover visual regressions. The new "Indeterminate" maturity label rendering (D-10) is a visual change but mirrors the Phase 74 backend label introduction; document in UAT-SERIES Phase 76 wrap.
- **Audit ledger flip** — 11 rows.

</test_strategy>

<deferred>
## Deferred Ideas

- **Centralized error-banner component** (reusing across pages) — D-01's error display could share a primitive; defer if multiple pages need it.
- **Recharts static-children documentation** — already a known constraint; consider hoisting to `src/dashboard/README.md` for newcomer-friendly visibility.
- **Cytoscape extension API typing** — D-09 augments only `.use()`; if other cytoscape extension methods need typing in future, expand the .d.ts.
- **Theme transition animation polish** — out of scope; tracked in dashboard polish backlog.

</deferred>
