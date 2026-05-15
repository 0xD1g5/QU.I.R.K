# Phase 76: React Frontend WARNINGs - Research

**Researched:** 2026-05-15
**Domain:** React dashboard (`src/dashboard/`) WARNING-severity defect closure — 11 open `react-frontend/WR-*` rows
**HEAD verified at:** `cf2417a` (post-Phase 71 wrap)
**Confidence:** HIGH (every D-NN site verified against HEAD; one minor mismatch noted in research_concerns)

## Summary

Phase 76 closes 11 open WARNING rows clustered into 3 REACT-NN requirements:
**REACT-01** (API error surfacing — WR-02, WR-06, WR-07, WR-08), **REACT-02** (localStorage / PDF / re-fetch correctness — WR-04, WR-05, WR-13), **REACT-03** (Cert regex / Cytoscape typing / Scorecard math — WR-09, WR-10, WR-11, WR-12).

Every CONTEXT site verified at HEAD: useScanList already returns `{sessions, loading, error}` (WR-02 partially complete — see C-1), executive PDF + body.detail at expected lines, print.tsx already has Phase 62 BR-05 cleanup, qramm-profile submitError generic, theme-provider cast, ComplianceMapTab broad dep, Subject CN regex appears at THREE sites (not two — see C-2), Cytoscape uses ad-hoc `cytoscape.Ext` cast (not `as any` per CONTEXT — see C-3), ScorecardTab hardcoded `/4` + correct `MATURITY_BADGE_CLASS` already in `lib/qramm-constants.ts` but applies `bg-*/20 text-* border` not pure `bg-*` fill.

**Primary recommendation:** Three plans (one per REACT-NN). All edits are <30-line surgical changes. Vitest is confirmed framework; existing `__tests__` infra is sparse — Wave 0 must add 6 new test modules.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

D-01..D-10 (D-11 absent in CONTEXT) + D-12 do-not-touch:

- **D-01** — `useScanList` adds `error: string | null` to return shape; non-OK sets error AND clears scans; callers render banner + retry.
- **D-02** — Executive `body.detail` coercion: `(body && typeof body === 'object' && typeof body.detail === 'string') ? body.detail : String(body ?? 'Unknown error')`.
- **D-03** — `print.tsx` sets `data-ready` only when QRAMM `loaded` OR `n/a`; if `errored`, leave unset + visible alert.
- **D-04** — `qramm-profile.tsx::submitError` extracts API message via D-02 coercion.
- **D-05** — `theme-provider.tsx` `VALID_THEMES` allowlist + type narrowing; fallback `'system'`; no console.warn.
- **D-06** — Executive PDF `setTimeout` revoke: store timer in ref, `useEffect` cleanup calls `clearTimeout` + `URL.revokeObjectURL`.
- **D-07** — ComplianceMapTab dep narrowed from `ctx.scoreResult` to `ctx.scoreResult?.session_id` (stable identity).
- **D-08** — Subject CN regex `/CN=((?:[^,\\]|\\.)*)(,|$)/`; post-process with `.replace(/\\(.)/g, '$1')`.
- **D-09** — Module augment `cytoscape.use(extension: unknown): void` in `src/dashboard/src/types/cytoscape-augment.d.ts`; remove cast at registration site.
- **D-10** — `MATURITY_MAX = 4` constant; width = `(score / MATURITY_MAX) * 100`%; `score === null` (Phase 74 Indeterminate) renders em-dash; switch maturity bar fill from `text-*` / `border-*` to `bg-*` Tailwind.
- **D-12** (do-not-touch) — Component structure, route hierarchy, Tailwind tokens, shadcn primitives, Recharts components, Phase 62 hooks, Phase 58 API hardening, Phase 65/66 dashboard, QRAMM taxonomy.

### Claude's Discretion

- D-07 stable-identity field choice (`session_id` vs alternatives) — researcher recommends `ctx.sessionId` (already used in line 121; `scoreResult` does not expose a `session_id` field directly — see C-4).
- D-10 maturity color map — CONTEXT specifies `bg-red/orange/yellow/green/gray-500` ladder; researcher recommends keeping the existing `quantum-vulnerable / quantum-at-risk / severity-low / quantum-safe` semantic-token palette already in `qramm-constants.ts` lines 37-42 and only swapping the modifier from `bg-*/20 text-* border` → `bg-*` (drop the `/20` opacity and the `text-*` / `border-*` accompaniment).

### Deferred Ideas (OUT OF SCOPE)

- Centralized error-banner component (D-01 sharing primitive).
- Recharts static-children documentation hoist to `src/dashboard/README.md`.
- Cytoscape extension API typing beyond `.use()`.
- Theme transition animation polish.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REACT-01 | API error surfacing (closes WR-02, WR-06, WR-07, WR-08) | All four sites verified. WR-02: `useScanList.ts` already exposes `error` and handles 401/403/429/non-OK at lines 21-39 — see C-1 (WR-02 is **partially closed already**). WR-06: `executive.tsx:118` reads `body.detail` after `.catch(() => ({}))` — `body.detail` would still be `undefined` on a raw-string error response. WR-07: `print.tsx:346-350` sets `data-ready` when `data && !loading && !qrammLoading` — does not check `qrammError`. WR-08: `qramm-profile.tsx:187` hardcodes `"Could not start assessment — check your connection and try again"` regardless of API message. |
| REACT-02 | localStorage / PDF / re-fetch correctness (closes WR-04, WR-05, WR-13) | WR-04: `theme-provider.tsx:18` `(localStorage.getItem(storageKey) as Theme) \|\| defaultTheme` — raw cast confirmed. WR-05: `executive.tsx:115` `setTimeout(() => URL.revokeObjectURL(url), 100)` — no cleanup. WR-13: `ComplianceMapTab.tsx:136` dep array `[ctx.sessionId, ctx.scoreResult]` — entire scoreResult object. |
| REACT-03 | Cert regex / Cytoscape typing / Scorecard math (closes WR-09, WR-10, WR-11, WR-12) | WR-09: Regex appears at THREE sites — `pages/certificates.tsx:61` (Subject), `pages/certificates.tsx:64` (Issuer — same bug class), `pages/print.tsx:88` (Subject in print). **No `lib/cert-parse.ts` exists** — see C-2; D-08 should either extract to a new helper or fix all 3 inline. WR-10: `cbom.tsx:20` uses `cytoscape.use(coseBilkent as cytoscape.Ext)` (not `as any` — see C-3); same pattern at `roadmap.tsx:13` `cytoscape.use(dagre as cytoscape.Ext)`. WR-11: `ScorecardTab.tsx:194` `width: ${(count / 4) * 100}%`. WR-12: `ScorecardTab.tsx:193` applies `MATURITY_BADGE_CLASS[level]` which contains `bg-*/20 text-* border-*` not solid `bg-*` (see `qramm-constants.ts:37-42`). |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Scan list error surfacing | `hooks/useScanList.ts` | `pages/scan-history.tsx` (or wherever consumed) | Hook owns error state; page renders banner |
| Executive body.detail coercion | `pages/executive.tsx` | — | Inline in `handleExportPdf` |
| Print data-ready guard | `pages/print.tsx` | `hooks/useQRAMMPrintData.ts` (already exports `error`) | Page consumes hook's `qrammError`, gates sentinel |
| QRAMM submitError message | `pages/qramm-profile.tsx` | — | Inline in `handleSubmit` catch |
| Theme localStorage allowlist | `components/theme-provider.tsx` | — | Module-local `VALID_THEMES` + helper |
| Executive PDF cleanup | `pages/executive.tsx` | — | `useEffect` cleanup with `useRef` timer |
| ComplianceMap targeted refetch | `components/qramm/ComplianceMapTab.tsx` | — | Dep array narrowing only |
| Cert CN RFC-2253 regex | `pages/certificates.tsx` + `pages/print.tsx` (+ optionally new `lib/cert-parse.ts`) | — | Shared helper recommended (D-12 discretion: extract to lib OR inline at 3 sites) |
| Cytoscape module augmentation | `types/cytoscape-augment.d.ts` (new) | `pages/cbom.tsx`, `pages/roadmap.tsx` (remove casts) | Type declaration is global; consumers benefit |
| Scorecard maturity math + fill | `components/qramm/ScorecardTab.tsx` | `lib/qramm-constants.ts` (new MATURITY_MAX, optional new MATURITY_BAR_CLASS) | Math constant + class lookup co-located with existing maturity tokens |

## Standard Stack

### Core (no new deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.2.4 | All hook/effect patterns | [VERIFIED `package.json:42`] |
| TypeScript | 5.9.3 | D-05 `as const` allowlist, D-09 module augmentation | [VERIFIED `package.json:71`] |
| cytoscape | 3.33.1 | D-09 augmentation target | [VERIFIED `package.json:36`] |
| @types/cytoscape | 3.21.9 | The package whose `cytoscape` module gets augmented | [VERIFIED `package.json:54`] |
| Vitest | 2.1.9 | All new tests | [VERIFIED `package.json:74`] |
| @testing-library/react | 16.3.2 | Component + hook tests | [VERIFIED `package.json:52`] |
| jsdom | 25.0.1 | Test environment (`vitest.config.ts:13`) | [VERIFIED] |

### Supporting (pattern precedent — already present)

| Module | Pattern | Use Case |
|--------|---------|----------|
| `hooks/useScanList.ts` lines 17, 51 | `let cancelled = false` + `return () => { cancelled = true }` | Phase 62 HOOK pattern — D-06 setTimeout-ref cleanup mirrors |
| `hooks/useScanData.ts`, `useTrendsData.ts`, `useTimelineData.ts`, etc. (10 hooks) | Same cancellation-guard pattern | [VERIFIED via grep] — pattern is universal |
| `hooks/useQRAMMSession.ts` returns `{session, loading, error, reload}` | Consistent error-surface shape | D-01 should match this shape (already does — see C-1) |
| `lib/qramm-constants.ts` | Static export map (MATURITY_LABEL, MATURITY_BADGE_CLASS, DIMENSIONS) | D-10's MATURITY_MAX belongs here |
| `types/cytoscape-extensions.d.ts` | Already exists: `declare module "cytoscape-cose-bilkent"` + `"cytoscape-dagre"` | D-09's augmentation should be a sibling file `cytoscape-augment.d.ts` to keep concerns separated, OR could be merged into the existing file |

**Installation:** No new packages required.

## Architecture Patterns

### Recommended file layout (no structural changes per D-12)

```
src/dashboard/src/
├── components/qramm/ScorecardTab.tsx      # D-10 edits
├── components/qramm/ComplianceMapTab.tsx  # D-07 dep narrowing
├── components/theme-provider.tsx          # D-05 allowlist
├── hooks/useScanList.ts                   # D-01 (mostly complete)
├── lib/qramm-constants.ts                 # add MATURITY_MAX
├── pages/executive.tsx                    # D-02, D-06
├── pages/print.tsx                        # D-03
├── pages/qramm-profile.tsx                # D-04
├── pages/certificates.tsx                 # D-08 (Subject + Issuer)
├── pages/cbom.tsx                         # D-09 (remove cast)
├── pages/roadmap.tsx                      # D-09 (remove cast — dagre)
└── types/cytoscape-augment.d.ts           # D-09 (new)
```

### Pattern 1: Module augmentation for cytoscape.use()

**Source:** TypeScript handbook — `declare module` for re-opening third-party types.

```typescript
// src/dashboard/src/types/cytoscape-augment.d.ts
import 'cytoscape'

declare module 'cytoscape' {
    function use(extension: unknown): void
}
```

After this is in place, remove `as cytoscape.Ext` at `cbom.tsx:20` and `roadmap.tsx:13`. TypeScript's declaration merging applies the looser signature.

### Pattern 2: setTimeout cleanup in useEffect (D-06)

```typescript
// pages/executive.tsx — inside ExecutivePage component
const revokeTimerRef = useRef<number | null>(null)
const blobUrlRef = useRef<string | null>(null)

useEffect(() => {
  return () => {
    if (revokeTimerRef.current !== null) clearTimeout(revokeTimerRef.current)
    if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current)
  }
}, [])

// In handleExportPdf, after URL.createObjectURL(blob):
blobUrlRef.current = url
revokeTimerRef.current = window.setTimeout(() => {
  URL.revokeObjectURL(url)
  blobUrlRef.current = null
  revokeTimerRef.current = null
}, 100)
```

### Pattern 3: VALID_THEMES allowlist (D-05)

```typescript
const VALID_THEMES = ['light', 'dark', 'system'] as const
type Theme = typeof VALID_THEMES[number]

function getStoredTheme(storageKey: string, defaultTheme: Theme): Theme {
  const raw = localStorage.getItem(storageKey)
  return (VALID_THEMES as readonly string[]).includes(raw ?? '')
    ? (raw as Theme)
    : defaultTheme
}
```

### Pattern 4: RFC-2253 CN regex (D-08)

```typescript
const CN_RE = /CN=((?:[^,\\]|\\.)*)(,|$)/

export function extractCN(dn: string | null | undefined): string {
  if (!dn) return '—'
  const m = dn.match(CN_RE)
  if (!m) return dn
  return m[1].replace(/\\(.)/g, '$1')
}
```

Test cases (from CONTEXT test_strategy):
- `CN=O\,reilly` → `O,reilly`
- `CN=Smith\\, John` → `Smith\, John`  (or `Smith, John` depending on input encoding — clarify with planner)
- `CN=plain,O=Corp` → `plain`
- `CN=plain` → `plain`

### Anti-Patterns to Avoid

- **Conditional Recharts mount/unmount** — preserved untouched per D-12 and project memory; Radar uses `fillOpacity={ctx.scoreResult ? 1 : 0}` pattern at `ScorecardTab.tsx:148`.
- **`as any` for library types** — replaced by module augmentation (D-09).
- **String error fallback inside `.json().catch(() => ({}))`** — `.detail` is `undefined` not raised; D-02 coercion handles both.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL object cleanup across unmount | Custom AbortController scaffolding | `useRef` + `useEffect` cleanup (Pattern 2) | Standard React idiom |
| RFC-2253 DN parsing | Full RFC-2253 tokenizer | Targeted regex (D-08) | Only CN extraction needed; full parser is overkill |
| Cytoscape extension typing | Local cast at each call site | Module augmentation (D-09) | Idiomatic across cytoscape ecosystem |
| Theme validation | Schema library (zod) | `as const` array + `.includes` (D-05) | Three values; no dep justified |
| Error banner UI | New shared component | Inline `<p className="text-destructive">` | Deferred in CONTEXT |

## Common Pitfalls

### Pitfall 1: `useScanList` may already be partially done

`useScanList.ts` at HEAD already exposes `error: string | null` and handles 401/403/429/non-OK at lines 21-39. The D-01 wording in CONTEXT ("currently catches non-OK responses and returns an empty list silently") is **stale** — the audit was 2026-05-08, Phase 62 + other phases shipped error-surfacing since. Researcher recommends planner confirms scope: either (a) close WR-02 as **already-fixed-by-Phase-62-followup** (audit ledger flip only, no code change), OR (b) add the missing piece: confirm the consumer (likely `scan-history.tsx`) renders the error banner + retry. See C-1.

### Pitfall 2: Subject CN regex has 3 sites, not 2

CONTEXT D-08 references `certificates.tsx` OR `lib/cert-parse.ts`. Truth: `lib/cert-parse.ts` does not exist; regex appears at `certificates.tsx:61` (Subject), `certificates.tsx:64` (Issuer — same bug), `print.tsx:88` (Subject in print). Recommend extracting to a new `lib/cert-parse.ts` helper and using it at all 3 sites — this avoids drift and matches D-12's "no new components" by being a `lib/` utility, not a component.

### Pitfall 3: Print page already has Phase 62 cleanup

`print.tsx:332-335` already has `useEffect(() => { document.body.removeAttribute('data-ready'); return () => { document.body.removeAttribute('data-ready') } }, [])` (Phase 62 BR-05 fix). The D-03 change is purely in the second `useEffect` at lines 346-350: add `qrammError` to the guard condition. **Do not touch the BR-05 cleanup effect.**

### Pitfall 4: Cytoscape cast is `as cytoscape.Ext` not `as any`

CONTEXT D-09 says "Remove the `(cytoscape as any).use(coseBilkent)` cast". Actual code at `cbom.tsx:20` is `cytoscape.use(coseBilkent as cytoscape.Ext)` — the cast is on the extension, not on cytoscape. After adding the augmentation, the cast can be dropped to `cytoscape.use(coseBilkent)`. Same applies to `roadmap.tsx:13` (`dagre as cytoscape.Ext`). Both lines need touching, not just `cbom.tsx`.

### Pitfall 5: MATURITY_BADGE_CLASS already exists with semantic-token palette

`qramm-constants.ts:37-42` exports `MATURITY_BADGE_CLASS` mapping `4 → bg-quantum-safe/20 text-quantum-safe border border-quantum-safe/30`, etc. This is appropriate for the Badge use at `ScorecardTab.tsx:249` (small pill badges) but WRONG for the maturity bar fill at line 193 (which needs solid color). Recommend adding a separate `MATURITY_BAR_CLASS` constant with `bg-quantum-safe` / `bg-severity-low` / `bg-quantum-at-risk` / `bg-quantum-vulnerable` (drop `/20` opacity and `text-*` / `border-*`). Existing `MATURITY_BADGE_CLASS` stays untouched (it's correct for the Badge usage).

### Pitfall 6: Indeterminate (Phase 74) does not yet propagate to maturityInt

`scoring.py:73-85` returns `"Indeterminate"` string when overall score is `None`. Frontend `ScorecardTab.tsx:231-234` computes `maturityInt = d != null ? Math.max(1, Math.min(4, Math.round(d.score))) : null` — already null-safe per dimension. The Maturity Distribution math at line 56 (`maturityDist`) buckets numeric scores into 1-4; `null` dimension score is `continue`d. **The bar widths use `count / 4` (number of dimensions in this bucket, max 4 since there are 4 dimensions)** — **the `4` is dimension count, not maturity max**. This is a semantic mismatch with D-10's narrative. See C-5.

## Runtime State Inventory

> Not applicable — Phase 76 is pure code edits to React components/hooks/types. No DB, no live service config, no OS-registered state, no secrets/env, no build artifacts beyond the standard `dist/` rebuild via `npm run build`.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified by grep (no DB schema changes) | None |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | `src/dashboard/dist/` regenerates on `npm run build` | Run build before commit (memory note) |

## Code Examples

### D-01 — useScanList consumer banner pattern (likely site `scan-history.tsx`)

```typescript
const { sessions, loading, error } = useScanList()
if (loading) return <PageSpinner ariaLabel="Loading scans" />
if (error) {
  return (
    <div className="text-center py-12 space-y-4">
      <p className="text-destructive">{error}</p>
      <Button onClick={() => window.location.reload()}>Retry</Button>
    </div>
  )
}
```

### D-03 — print sentinel guard

```typescript
// pages/print.tsx — replace lines 346-350
useEffect(() => {
  if (data && !loading && !qrammLoading && !qrammError) {
    document.body.setAttribute('data-ready', 'true')
  }
}, [data, loading, qrammLoading, qrammError])
```

### D-07 — ComplianceMapTab dep narrowing

```typescript
// components/qramm/ComplianceMapTab.tsx:136
}, [ctx.sessionId])  // was [ctx.sessionId, ctx.scoreResult]
```

Note: This may need to add a manual re-fetch trigger when the user clicks Calculate Score. Verify consumers don't rely on auto-refetch-on-score. (Discretion item.)

### D-10 — Maturity Distribution math + class

```typescript
// lib/qramm-constants.ts — append
export const MATURITY_MAX = 4
export const MATURITY_BAR_CLASS: Record<number, string> = {
  4: "bg-quantum-safe",
  3: "bg-severity-low",
  2: "bg-quantum-at-risk",
  1: "bg-quantum-vulnerable",
}

// components/qramm/ScorecardTab.tsx:190-197 — replace bar div
<div className="h-2 w-full rounded-full bg-muted">
  {ctx.scoreResult && (
    <div
      className={`h-2 rounded-full ${MATURITY_BAR_CLASS[level]}`}
      style={{ width: `${(count / MATURITY_MAX) * 100}%` }}
    />
  )}
</div>
```

For Indeterminate (overall string from scoreResult.maturity === "Indeterminate" or all dimensions null): render em-dash row.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `as any` cast for cytoscape extensions | Module augmentation via `declare module 'cytoscape'` | TS 4.x+ pattern | D-09 adopts |
| Single-string error swallow | Structured error state in hooks | Phase 62 | D-01 aligns with established hooks |
| `setTimeout` without cleanup | useEffect cleanup with ref | React 18 strict-mode pressure | D-06 |

## Open Questions

1. **Q1: D-01 scope — is WR-02 already closed by an unaudited follow-up?**
   - What we know: `useScanList.ts` HEAD has full `error` surface incl. 401/403/429/non-OK handling.
   - What's unclear: Is the **consumer** rendering the banner? CONTEXT D-01 talks about "show a user-visible error banner with a retry button" — need to grep `useScanList` callsites.
   - Recommendation: Planner adds a Wave 0 task to grep `useScanList` consumers and verify banner rendering before deciding code-edit vs. audit-ledger-flip-only.

2. **Q2: D-08 — extract to `lib/cert-parse.ts` or inline?**
   - 3 sites identified. Inlining triplicates the regex; extracting is the better architectural choice but introduces a new file.
   - Recommendation: Extract to `lib/cert-parse.ts` (allowed under D-12 — `lib/` is a utility folder, not a component/page).

3. **Q3: D-07 — re-fetch when Calculate Score completes?**
   - Narrowing dep to `ctx.sessionId` means compliance map stops auto-refetching when score result changes.
   - Recommendation: If a tab visibility / "score recalculated" UX matters, add a manual reload button in ComplianceMapTab. Otherwise the score result already lives in context and the compliance rows are independent (they reflect the question-bank-driven framework mapping, not the current score). Researcher believes the auto-refetch is spurious and can be safely removed.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node + npm | All build/test | ✓ (assumed, matches Phase 62 precedent) | per `package.json` engines | — |
| Vitest | All new tests | ✓ | 2.1.9 | — |
| @testing-library/react | Component tests | ✓ | 16.3.2 | — |
| jsdom | Test env | ✓ | 25.0.1 | — |
| TypeScript | Build + augmentation | ✓ | 5.9.3 | — |

No missing dependencies. `npm run build` exists in `package.json:8` (`tsc -b && vite build`).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 2.1.9 + @testing-library/react 16.3.2 |
| Config file | `src/dashboard/vitest.config.ts` |
| Quick run command | `cd src/dashboard && npm test -- <path-pattern>` |
| Full suite command | `cd src/dashboard && npm test` |
| Build verification | `cd src/dashboard && npm run build` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| REACT-01 / WR-02 | useScanList exposes error on non-OK | unit (hook) | `npm test -- useScanList` | ❌ Wave 0 |
| REACT-01 / WR-06 | executive PDF body.detail coercion handles raw-string body | unit (helper or page) | `npm test -- executive` | ❌ Wave 0 |
| REACT-01 / WR-07 | print does not set data-ready on qrammError | unit (page) | `npm test -- print-pdf` | ❌ Wave 0 |
| REACT-01 / WR-08 | qramm-profile submitError shows API message | unit (page) | `npm test -- qramm-profile` | ❌ Wave 0 |
| REACT-02 / WR-04 | theme-provider rejects invalid localStorage | unit (component) | `npm test -- theme-provider` | ❌ Wave 0 |
| REACT-02 / WR-05 | executive PDF cleanup clears timer on unmount | unit (page) | `npm test -- executive-pdf-cleanup` | ❌ Wave 0 |
| REACT-02 / WR-13 | ComplianceMapTab does not refetch on scoreResult change alone | unit (component) | `npm test -- compliance-map-tab` | ❌ Wave 0 |
| REACT-03 / WR-09 | CN regex handles RFC-2253 escaped commas | unit (lib) | `npm test -- cert-parse` | ❌ Wave 0 |
| REACT-03 / WR-10 | cytoscape augmentation compiles + no `as Ext` needed | TS compile via build | `npm run build` | ❌ Wave 0 (.d.ts file) |
| REACT-03 / WR-11, WR-12 | Maturity bar width math + bg-* class application | unit (component) | `npm test -- scorecard-maturity` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `npm test -- <specific-test-pattern>` (file or describe-block scoped)
- **Per wave merge:** `npm test` (full Vitest suite) + `npm run build` (TS compile + Vite build)
- **Phase gate:** Full suite green + `npm run build` exits 0 before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `src/dashboard/src/hooks/__tests__/useScanList.test.ts` — REACT-01 / WR-02
- [ ] `src/dashboard/src/pages/__tests__/executive.test.tsx` — REACT-01 / WR-06 + REACT-02 / WR-05
- [ ] `src/dashboard/src/pages/__tests__/print-pdf-cleanup.test.tsx` — REACT-01 / WR-07
- [ ] `src/dashboard/src/pages/__tests__/qramm-profile.test.tsx` — REACT-01 / WR-08
- [ ] `src/dashboard/src/components/__tests__/theme-provider.test.tsx` — REACT-02 / WR-04
- [ ] `src/dashboard/src/components/qramm/__tests__/compliance-map-tab.test.tsx` — REACT-02 / WR-13
- [ ] `src/dashboard/src/components/qramm/__tests__/scorecard-maturity.test.tsx` — REACT-03 / WR-11, WR-12
- [ ] `src/dashboard/src/lib/__tests__/cert-parse.test.ts` — REACT-03 / WR-09 (requires new `src/dashboard/src/lib/cert-parse.ts`)
- [ ] `src/dashboard/src/types/cytoscape-augment.d.ts` — REACT-03 / WR-10 (new declaration file; not a test, but Wave 0 dependency)

Test directory `src/dashboard/src/hooks/__tests__/` already exists with `useScanData.test.tsx` — Vitest infra is live.

## Security Domain

Phase 76 makes no new security-sensitive surface. Quick ASVS sweep:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (no auth changes; 401/403 already surfaced by useScanList) |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (D-05 theme allowlist, D-08 regex, D-17 absent here — N/A) | `as const` allowlist + targeted regex |
| V6 Cryptography | no | — (Subject CN extraction is parsing, not crypto) |

### Known Threat Patterns for React + browser stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Untrusted localStorage value cast to type | Tampering | D-05 allowlist (already in research) |
| Memory leak via uncleaned timer | Denial of Service (minor) | D-06 cleanup |
| Stale sentinel observed by external PDF renderer | Information Disclosure (partial captures) | D-03 guard |

## Project Constraints (from CLAUDE.md)

- **PEP 8** — Python only; not applicable to this phase (frontend-only).
- **Minimal diffs** — all D-NN are < 30-line surgical edits; D-12 reinforces.
- **`python -m compileall` + tests** — Python rule, not applicable.
- **Detection logic changes → update `labs/*/expected_results.md`** — N/A (frontend bug fixes don't change detection).
- **Staleness review cadence** — N/A.
- **Chaos lab maintenance (`lab.sh`)** — N/A.
- **Mandatory phase completion** — Obsidian phase note + UAT-SERIES.md update + Obsidian sync + commit. All standard, no Phase-76-specific deltas.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Vitest 2.1.9 supports `import.meta.env` + `vi.useFakeTimers()` for D-06 setTimeout cleanup tests | Validation Architecture | LOW — well-established Vitest API since 0.x |
| A2 | The Indeterminate sentinel from Phase 74 backend reaches the frontend as `scoreResult.maturity === "Indeterminate"` (string) AND dimensions[d].score can be null per-dimension | Pitfall 6 | MEDIUM — frontend type `QRAMMScoreResponse` should be checked; if `dimensions[d].score` is typed `number` not `number \| null`, D-10's `score === null` branch is unreachable from real data. Planner verifies. |
| A3 | `useScanList` callsite (likely `scan-history.tsx`) does not currently render an error banner | Open Q1 | LOW — easy to verify in Wave 0 |
| A4 | Extracting to `lib/cert-parse.ts` does not violate D-12 ("no new components") because `lib/` is a utility folder, not a component | Open Q2 | LOW — `lib/` already houses `api.ts`, `qramm-constants.ts`, `qramm-benchmarks.ts`, `utils.ts`; pattern is established |

## Sources

### Primary (HIGH confidence)

- `src/dashboard/src/hooks/useScanList.ts` (1-55) — read in full
- `src/dashboard/src/pages/executive.tsx` (1-263) — read in full, WR-05/WR-06 sites at 99-126
- `src/dashboard/src/pages/print.tsx` (1-463) — read in full, BR-05 cleanup at 332-335, WR-07 site at 346-350
- `src/dashboard/src/pages/qramm-profile.tsx` (1-314) — read in full, WR-08 site at 186-188
- `src/dashboard/src/components/theme-provider.tsx` (1-61) — read in full, WR-04 site at 17-19
- `src/dashboard/src/components/qramm/ComplianceMapTab.tsx` (100-160) — WR-13 site at 121-136
- `src/dashboard/src/components/qramm/ScorecardTab.tsx` (1-269) — WR-11/WR-12 sites at 50-60, 180-200
- `src/dashboard/src/pages/cbom.tsx` (1-30) — WR-10 site at 20
- `src/dashboard/src/pages/roadmap.tsx` (grep) — sibling site at 13
- `src/dashboard/src/pages/certificates.tsx` (55-65) — WR-09 sites at 61, 64
- `src/dashboard/src/lib/qramm-constants.ts` (1-74) — read in full
- `src/dashboard/src/types/cytoscape-extensions.d.ts` — confirmed contents
- `src/dashboard/vitest.config.ts`, `src/dashboard/package.json` — framework + scripts
- `quirk/qramm/scoring.py:73-85` — Phase 74 Indeterminate sentinel verified
- `.planning/audit-2026-05-08/AUDIT-TASKS.md:221-234` — 11 open WR rows verified

### Secondary (MEDIUM confidence)

- TypeScript handbook module augmentation pattern (training knowledge)
- React useEffect cleanup for setTimeout (training knowledge, widely standard)

### Tertiary (LOW confidence)

- None — every claim verified at HEAD.

<research_concerns>
## Mismatches between CONTEXT.md and HEAD

- **C-1 (D-01 / WR-02):** CONTEXT says useScanList "currently catches non-OK responses and returns an empty list silently." HEAD already exposes `error: string | null` with 401/403/429/non-OK branches (lines 21-39). The hook itself appears complete. The remaining gap is likely the **consumer banner**, which CONTEXT also mentions ("Callers ... show a user-visible error banner with a retry button"). Planner should verify by grep'ing `useScanList()` callsites — if banner is missing in the page, that's the actual edit; if banner already exists, WR-02 should be closed as audit-ledger-flip-only.

- **C-2 (D-08 / WR-09):** CONTEXT says regex is at "`certificates.tsx` or `lib/cert-parse.ts`." Truth: regex is at 3 sites — `certificates.tsx:61` (Subject), `certificates.tsx:64` (Issuer — same bug pattern, Subject-only fix would leave Issuer broken), `print.tsx:88` (Subject in print). `lib/cert-parse.ts` does not exist. Researcher recommends extracting to `lib/cert-parse.ts` and using at all 3 sites; otherwise planner must fix all 3 inline.

- **C-3 (D-09 / WR-10):** CONTEXT says "Remove the `(cytoscape as any).use(coseBilkent)` cast." Truth: HEAD uses `cytoscape.use(coseBilkent as cytoscape.Ext)` (cast on extension, not on cytoscape). Same pattern at `roadmap.tsx:13` for dagre. Both need touching. The fix is identical (drop the `as cytoscape.Ext` once module augmentation is in place) — minor wording correction only.

- **C-4 (D-07 / WR-13):** CONTEXT says "Narrow dependency to `ctx.scoreResult?.session_id` (or whichever stable identity field exists — researcher confirms)." Truth: `scoreResult` type does not appear to expose `session_id` directly. The stable identity already exists as `ctx.sessionId` (used at line 121 to build the fetch URL). Recommend narrowing to `[ctx.sessionId]` — this is also what CONTEXT's intent matches, since the fetch URL only depends on `sessionId`. The scoreResult dependency was always spurious; compliance rows are framework-question mapping, independent of scored values.

- **C-5 (D-10 / WR-11 — semantic, not wording):** CONTEXT D-10 says "Replace hardcoded `/4` with a module-level `const MATURITY_MAX = 4` ... Width formula: `width = (score / MATURITY_MAX) * 100%`". Truth: the `/4` in `ScorecardTab.tsx:194` is `(count / 4) * 100` where `count` is **the number of dimensions falling into this maturity bucket** (max 4 since there are 4 dimensions: CVI, SGRM, DPE, ITR). The `4` is **dimension count, not maturity max** — they happen to be the same number but the semantic naming `MATURITY_MAX` is misleading. Recommend constant name `DIMENSION_COUNT` (or import `DIMENSIONS.length`). This is a labeling concern, not a logic fix — the math itself is correct.

- **C-6 (D-11 absent in CONTEXT):** CONTEXT decision numbering jumps from D-10 to D-12 — no D-11. No action; just a numbering note.

- **C-7 (D-12 / Phase 65/66 reference):** CONTEXT lists `.planning/phases/65-66-dashboard-*` in canonical_refs as preserved. No conflicts identified, but planner should spot-check that scan-history page edits (likely D-01 banner site) don't touch Phase 65 scan history code.
</research_concerns>

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — package.json + vitest.config.ts verified
- Architecture: HIGH — all 10 D-NN sites located and read at HEAD
- Pitfalls: HIGH — 6 concrete pitfalls extracted from real HEAD differences

**Research date:** 2026-05-15
**Valid until:** 2026-06-14 (30 days — stable frontend, no fast-moving deps)
