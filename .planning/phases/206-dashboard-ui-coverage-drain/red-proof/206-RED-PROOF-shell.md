| UAT-7-20 | `src/dashboard/src/__tests__/shell-spa-routing.test.tsx::"renders the findings page from the app route table when navigating directly to slash findings"` | `App.tsx`'s real route table entry `<Route path="/findings" element={<FindingsPage />} />` re-pointed at `element={<ExecutivePage />}`, so `/findings` resolves to the wrong page component. | `TestingLibraryElementError: Unable to find an accessible element with the role "heading" and name "Findings"` | 705e9c39 | 472878a8 |
| UAT-7-22 | `src/dashboard/src/components/__tests__/theme-toggle-persistence.test.tsx::"switches the theme and persists the selection to localStorage when the theme toggle is used"` | `theme-provider.tsx`'s `setTheme` had its `localStorage.setItem(storageKey, t)` line removed, so the theme still switches on the document but is never persisted. | `AssertionError: expected null to be 'light' // Object.is equality` | 705e9c39 | 472878a8 |
| UAT-7-31 | `src/dashboard/src/components/__tests__/dashboard-branding.test.tsx::"renders the QUIRK wordmark in the sidebar and the configured document title"` | The full wordmark text node inside `sidebar.tsx`'s logo `<span className="text-accent font-black ... font-mono">` blanked to whitespace, leaving the `Q` monogram in place. | `TestingLibraryElementError: Unable to find an element with the text: QU.I.R.K.. This could be because the text is broken up by multiple elements. In this case, you can provide a function for your text matcher to make your matcher more flexible.` | 705e9c39 | 472878a8 |

## Citations

UAT-7-20 -> `src/dashboard/src/__tests__/shell-spa-routing.test.tsx::"renders the findings page from the app route table when navigating directly to slash findings"`
- Full coverage of the case's three Pass Criteria bullets, asserted against the application's REAL
  `<Routes>` table via the `AppShell` named export (D-A4). No route tree is duplicated into the test
  (206-RESEARCH.md § Pitfall 2). The test asserts both that the Findings page's own heading and row
  content render AND that the Executive page's distinguishing heading (`QU.I.R.K. — Scan Results`)
  is absent — the second half is what proves the route was *selected* rather than that something
  merely mounted. "URL stays at `/findings`" is covered in the jsdom-honest sense: `MemoryRouter`'s
  entry is what the route table resolves against, and no full document reload exists in jsdom to
  lose it.

UAT-7-22 -> `src/dashboard/src/components/__tests__/theme-toggle-persistence.test.tsx::"switches the theme and persists the selection to localStorage when the theme toggle is used"`
- Partial coverage. Three of the case's five Pass Criteria bullets are covered: the toggle switches
  the applied theme (`documentElement` gains `light`, loses `dark`), `localStorage["quirk-ui-theme"]`
  holds the new value under the app's real storage key (`App.tsx:130`), and the reload path is
  asserted through the app's own rehydration function `getStoredTheme()`. Two bullets are uncovered
  and are appearance claims jsdom cannot honestly assert:
  - "All page elements update: sidebar, cards, charts, tables, badges" — the theme is applied as a
    single class on `<html>`; whether every descendant *repaints* correctly requires a cascade and
    layout engine, which jsdom does not have.
  - "Both themes are visually coherent (no invisible text, unreadable badges, or broken contrast)" —
    a computed-style/contrast claim, browser-tier.
  These two route to the Phase 207 browser verdict alongside the existing browser-only group.
  This is genuinely new coverage: the pre-existing `components/__tests__/theme-provider.test.tsx`
  asserts only the `getStoredTheme()` / `VALID_THEMES` utility surface — it renders no provider,
  clicks no toggle, and never asserts an applied theme class.

UAT-7-31 -> `src/dashboard/src/components/__tests__/dashboard-branding.test.tsx::"renders the QUIRK wordmark in the sidebar and the configured document title"`
- Partial coverage, split across two testing tiers, stated here rather than left implied:
  - **Render tier (the wordmark).** Asserted by rendering the real `Sidebar` — the element carrying
    the text `QU.I.R.K.` plus its `font-black` / `font-mono` / `text-accent` classes ("bold
    monospace electric-blue"). The colour is asserted as the `accent` design token rather than as a
    hex literal, because a hardcoded hex on a component is exactly what UAT-7-21 forbids.
  - **Static-document tier (tab title + favicon).** `document.title` is never set at runtime
    (`grep -rn "document.title" src/dashboard/src/` returns nothing) and the favicon is three static
    `<link rel="icon">` tags; both live in `src/dashboard/index.html`, which Vite copies verbatim
    into the build. No React render assertion can reach them, so the test asserts them against
    `index.html` itself. **This is not the banned source-text-regex substitution.** The ban's own
    stated rationale is that grepping source "does not cover a *render* case" — it turns on whether
    the case's claim is a render behaviour. A `<title>` element in a static HTML document is not
    one; the static document IS the artifact the Pass Criterion describes. Same reasoning shape as
    D-A1's UAT-7-21 carve-out, applied per-claim, not as a general loosening — the wordmark half of
    this very case IS a render behaviour and is asserted by rendering.
  - **Uncovered bullet:** "No JS console errors on page load" is UAT-7-32's own subject and is
    structurally browser-only (Phase 207). It is not asserted here.

## UAT-7-23 reclassification evidence

`UAT-7-23` (Sidebar Responsive Collapse) converted **no** test and therefore has **no** row above.
This section is the evidence that it is jsdom-intractable, recorded so a verifier can re-derive the
claim instead of trusting prose (T-206-10-02). Commands run from the repository root on 2026-09-21,
against the unmodified `sidebar.tsx` (post-revert, byte-identical to its pre-plan state).

**Command 1 — is there any JavaScript media-query listener to assert against?**

```
$ grep -n "matchMedia\|useMediaQuery" src/dashboard/src/components/sidebar.tsx
$ echo $?
1
```

Literal output: **none** (no matching lines; grep exit status `1` = no match).

**Command 2 — what actually implements the collapse?**

```
$ grep -n "lg:w-\|w-12" src/dashboard/src/components/sidebar.tsx
78:        "w-12 lg:w-60",
$ echo $?
0
```

Literal output: the single line above — a Tailwind responsive width pair on the `<aside>`
(`w-12` at all widths, overridden to `w-60` at the `lg` breakpoint, i.e. ≥1024px). The same pattern
governs every other half of the case: the wordmark/monogram swap is `hidden lg:block` vs `lg:hidden`
(sidebar.tsx lines 86 and 90), and the collapsed-state tooltips are `className="lg:hidden"` on
`TooltipContent`. Each is a CSS class toggle evaluated by a real stylesheet at a real viewport
width.

**Conclusion.** The collapse is a **pure CSS breakpoint**. There is no JS state, no `matchMedia`
listener, and no `useMediaQuery` hook whose behaviour a render assertion could observe. jsdom has no
layout engine and does not evaluate media queries, so the rendered DOM is **byte-identical above and
below 1024px** — every element the case asks about (240px vs 48px width, wordmark vs monogram,
tooltip visibility) is present in the DOM in both states, distinguished only by which CSS rule a
browser would apply. No honest jsdom assertion can distinguish collapsed from expanded; any test
that appeared to would be asserting the class strings, i.e. the banned source-text substitution
wearing a render test's clothes.

**Disposition consequence — stated explicitly, not enacted silently.** `UAT-7-23` **leaves the
jsdom-tractable set** and joins the browser-only group (`UAT-7-01`, `UAT-7-17`, `UAT-7-32`) routed to
**Phase 207**. This is a reclassification, and it moves SC#3's denominator from 28 to 27 jsdom-
tractable series-7 cases. It is recorded here — with reproducible commands and their literal output —
precisely so the denominator change is visible and re-derivable rather than quietly assumed. Plan
206-12 writes the disposition and the SUMMARY's reclassification record from this block; plan 206-13
owns the `docs/UAT-SERIES.md` edit. Plan 206-10 wrote **no** `docs/` file.

**Finding, not a failure, had it gone the other way:** if command 1 had returned a JS media-query
listener, `UAT-7-23` would have been convertible after all and this block would say so. It did not.
