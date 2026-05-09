---
phase: audit-2026-05-08-react-frontend
reviewed: 2026-05-08T00:00:00Z
depth: deep
files_reviewed: 46
files_reviewed_list:
  - src/dashboard/src/App.tsx
  - src/dashboard/src/main.tsx
  - src/dashboard/src/types/api.ts
  - src/dashboard/src/types/cytoscape-extensions.d.ts
  - src/dashboard/src/context/QRAMMContext.tsx
  - src/dashboard/src/context/QRAMMProvider.tsx
  - src/dashboard/src/context/ScanContext.tsx
  - src/dashboard/src/context/ScanProvider.tsx
  - src/dashboard/src/hooks/useQRAMMPrintData.ts
  - src/dashboard/src/hooks/useQRAMMSession.ts
  - src/dashboard/src/hooks/useScanData.ts
  - src/dashboard/src/hooks/useScanList.ts
  - src/dashboard/src/hooks/useSelectedScan.ts
  - src/dashboard/src/hooks/useTrendsData.ts
  - src/dashboard/src/lib/qramm-benchmarks.ts
  - src/dashboard/src/lib/qramm-constants.ts
  - src/dashboard/src/lib/utils.ts
  - src/dashboard/src/components/EmptyStateCard.tsx
  - src/dashboard/src/components/PageSpinner.tsx
  - src/dashboard/src/components/ScanSelector.tsx
  - src/dashboard/src/components/sidebar.tsx
  - src/dashboard/src/components/mode-toggle.tsx
  - src/dashboard/src/components/theme-context.ts
  - src/dashboard/src/components/theme-provider.tsx
  - src/dashboard/src/components/use-theme.ts
  - src/dashboard/src/components/gauges/ScoreGauge.tsx
  - src/dashboard/src/components/qramm/ComplianceMapTab.tsx
  - src/dashboard/src/components/qramm/PracticeAreaSection.tsx
  - src/dashboard/src/components/qramm/QuestionCard.tsx
  - src/dashboard/src/components/qramm/ScorecardTab.tsx
  - src/dashboard/src/pages/cbom.tsx
  - src/dashboard/src/pages/cbom.skeleton.tsx
  - src/dashboard/src/pages/certificates.tsx
  - src/dashboard/src/pages/certificates.skeleton.tsx
  - src/dashboard/src/pages/data-at-rest.tsx
  - src/dashboard/src/pages/executive.tsx
  - src/dashboard/src/pages/findings.tsx
  - src/dashboard/src/pages/findings.skeleton.tsx
  - src/dashboard/src/pages/identity.tsx
  - src/dashboard/src/pages/identity.skeleton.tsx
  - src/dashboard/src/pages/motion.tsx
  - src/dashboard/src/pages/print.tsx
  - src/dashboard/src/pages/qramm-assessment.tsx
  - src/dashboard/src/pages/qramm-profile.tsx
  - src/dashboard/src/pages/roadmap.tsx
  - src/dashboard/src/pages/trends.tsx
findings:
  blocker: 6
  warning: 14
  info: 7
  total: 27
status: issues_found
---

# Subsystem 6: React Frontend — Code Review Report

**Reviewed:** 2026-05-08
**Depth:** deep (cross-file analysis: contexts, providers, hooks, pages)
**Files Reviewed:** 46
**Status:** issues_found

## Summary

The React dashboard is generally well-structured with proper cancellation guards in most hooks, the project-mandated Recharts opacity-gating pattern is consistently applied (good — no conditional mount/unmount of Radar/Bar/Line found), and there is no unsafe HTML injection. TypeScript escape hatches are minimal and confined to library boundaries (TanStack Table, Cytoscape extensions).

However, deep cross-file analysis surfaces multiple correctness defects that bite primetime:

- The QRAMM debounced persister has a **field-coalescing bug** that silently drops user input under rapid edits across different fields of the same question (BR-01).
- The Confirm-Auto-Fill flow updates client state with `confirmed_at` but the provider's draft persister never sends `confirmed_at` to the server, so confirmation status is **lost on refresh** (BR-02).
- `useScanData` does not clear stale `data` when scan switches mid-fetch, and its error-path setters lack the cancellation guard, so prior scan's state can leak into the new scan's render (BR-03, BR-04).
- The `/print` `data-ready` sentinel has no cleanup — once true, stays true on every subsequent render even if the underlying data goes back to loading. PDF renderer can race a stale sentinel on re-render (BR-05).
- The system theme is not reactive — `prefers-color-scheme` is read once and never subscribed (BR-06).

Plus 14 warnings (cancellation-guard inconsistencies, missing error surfaces, fragile regexes, leaked timers, type-cast without validation, etc.) and 7 info items.

The chart-rendering pattern (Radar in ScorecardTab, Bar in executive) all follow the opacity-gate rule from project memory. No conditional Radar/Bar mount/unmount detected.

---

## BLOCKER Issues

### BR-01: Debounced draft persister drops fields on rapid multi-field edits within 300ms

**File:** `src/dashboard/src/context/QRAMMProvider.tsx:17-41`
**Issue:** `persistDraft` keeps a single timer per question number. Each call to `setAnswer({ answer_value })` followed within 300ms by `setAnswer({ evidence_note })` clears the prior timer and replaces it with a new one whose body **only contains fields from the latest call** (because the body is built via `..."answer_value" in state && ...` from the partial). The previously queued field (e.g., `answer_value`) is silently dropped.

Reproduce: pick a maturity radio for Q5, then within 300ms start typing in the evidence note for Q5. Server receives only `evidence_note`; `answer_value` never persists. On reload, the radio reverts to null.

**Fix:** Coalesce pending fields per-question in a separate map; flush all pending fields when the timer fires.

```ts
const pendingRef = useRef<Map<number, Partial<AnswerState>>>(new Map())

const persistDraft = useCallback((qn: number, state: Partial<AnswerState>) => {
  const sid = sessionIdRef.current
  if (sid == null) return
  // Merge into pending payload rather than overwriting
  const merged = { ...(pendingRef.current.get(qn) ?? {}), ...state }
  pendingRef.current.set(qn, merged)

  const existing = debounceRef.current.get(qn)
  if (existing) clearTimeout(existing)
  const timer = setTimeout(async () => {
    debounceRef.current.delete(qn)
    const payload = pendingRef.current.get(qn) ?? {}
    pendingRef.current.delete(qn)
    try {
      await fetch("/api/qramm/assessment/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sid,
          question_number: qn,
          ...("answer_value" in payload && { answer_value: payload.answer_value ?? null }),
          ...("evidence_note" in payload && { evidence_note: payload.evidence_note ?? null }),
        }),
      })
    } catch { /* silent */ }
  }, 300)
  debounceRef.current.set(qn, timer)
}, [])
```

---

### BR-02: Confirm-auto-fill flow never persists `confirmed_at` to the server

**File:** `src/dashboard/src/pages/qramm-assessment.tsx:151-156`, `src/dashboard/src/context/QRAMMProvider.tsx:25-39`
**Issue:** `handleConfirm` calls `ctx.setAnswer(qn, { answer_value, confirmed_at: new Date().toISOString() })`. The provider's `persistDraft` only forwards `answer_value` and `evidence_note` to `/api/qramm/assessment/draft`; `confirmed_at` is never included in the request body. Client state shows the question as confirmed (Auto-filled badge disappears), but on session reload, `confirmed_at` comes back null from the server and the badge reappears as if the user never confirmed.

This contradicts the comment at line 150 ("optimistically so the badge disappears immediately without waiting for a server round-trip") — there is no actual round-trip persisting confirmation.

**Fix:** Either (a) extend the draft endpoint to accept `confirmed_at`, or (b) call a dedicated `/api/qramm/assessment/confirm` endpoint from the page-level `handleConfirm` handler. Whichever path is correct, the provider must transmit confirmation. Verify by completing a Confirm flow, hard-refreshing the page, and checking the badge state.

---

### BR-03: `useScanData` error setters lack cancellation guard — stale fetch can clobber new scan's state

**File:** `src/dashboard/src/hooks/useScanData.ts:28-42`
**Issue:** The success path correctly checks `if (!cancelled)` before calling `setData`. The 404 branch (line 30) and the generic !ok branch (line 32) call `setError` without first checking the `cancelled` flag.

```ts
if (!resp.ok) {
  if (resp.status === 404) {
    setError("No scan data available...")   // no cancellation guard
  } else {
    setError(`API error: ${resp.status}...`) // no cancellation guard
  }
  return
}
```

When the user switches scans mid-fetch (selectedScanId changes from A to B), the prior effect cleanup sets `cancelled = true`. If scan A's response was a 404, its error handler still fires and overwrites the new effect's `setError(null)`, displaying scan A's error on scan B's page until B resolves.

**Fix:** Wrap every `setError`/`setData` in `if (!cancelled) { ... }`. Apply the same fix to `useQRAMMSession.ts` lines 30, 38, 43-44 (multiple state mutations between awaits without guards).

---

### BR-04: `useScanData` does not clear `data` when scan switches — stale data renders alongside new error

**File:** `src/dashboard/src/hooks/useScanData.ts:17-55`
**Issue:** When `selectedScanId` changes, the effect re-runs but `data` is not reset. If the new fetch returns 404 or errors, every page reads `data` and renders the previous scan's findings/CBOM/certs while simultaneously displaying an error banner. For example, `executive.tsx` line 71 only blocks if `!data || !data.score` — it will happily render scan A's gauges and severity chart while scan B is loading or errored.

**Fix:** Reset state when the dependency changes:

```ts
useEffect(() => {
  let cancelled = false
  setData(null)        // clear stale data on scan switch
  setError(null)
  setLoading(true)
  ...
}, [selectedScanId])
```

---

### BR-05: `/print` `data-ready` sentinel never reset — PDF renderer can observe stale sentinel on re-fetch

**File:** `src/dashboard/src/pages/print.tsx:337-341`
**Issue:** Confirmed against project memory. The effect sets `document.body.setAttribute('data-ready', 'true')` when both data hooks resolve, but never clears it. Two failure modes:

1. If the route is visited a second time (e.g., HMR refresh, navigation away/back, or a printed-then-reprinted PDF on the same page instance) and data goes back to `loading=true`, the body still has `data-ready=true`. Playwright/Chromium's wait-for-attribute polling sees true and snapshots an incomplete page.
2. If `qrammError` is set but `qrammLoading` becomes false, the attribute still flips true with potentially stale or null QRAMM data — that may be intentional (so PDF doesn't block on QRAMM failures) but combined with no cleanup it means a "ready" attribute can persist even when the next render has actual loading state.

The in-source comment ("removing the attribute on every dependency change creates a transient window...") is a real concern, but the correct fix is to clear in the cleanup (which runs *after* the new effect body sets the attribute on success), not to skip cleanup entirely.

**Fix:** Set the attribute conditionally and clear it on the false branch and on cleanup:

```ts
useEffect(() => {
  if (data && !loading && !qrammLoading) {
    document.body.setAttribute('data-ready', 'true')
  } else {
    document.body.removeAttribute('data-ready')
  }
  return () => {
    document.body.removeAttribute('data-ready')
  }
}, [data, loading, qrammLoading])
```

The cleanup ensures unmount also clears the sentinel so the next mount starts from a known state.

---

### BR-06: System theme is not reactive — `prefers-color-scheme` read once, never subscribed

**File:** `src/dashboard/src/components/theme-provider.tsx:21-32`
**Issue:** When `theme === "system"`, the effect calls `window.matchMedia("(prefers-color-scheme: dark)").matches` once at the time the effect runs. It does not subscribe via `addEventListener("change", ...)`. If the user has the app open and their OS flips dark/light (sunset/sunrise on macOS auto-mode, manual toggle), the dashboard does not update until the user picks a mode manually. Causes user-visible drift in mixed-light/dark exec settings.

**Fix:** Add a media-query change listener with cleanup:

```ts
useEffect(() => {
  const root = window.document.documentElement
  const mq = window.matchMedia("(prefers-color-scheme: dark)")

  const apply = () => {
    root.classList.remove("light", "dark")
    if (theme === "system") {
      root.classList.add(mq.matches ? "dark" : "light")
    } else {
      root.classList.add(theme)
    }
  }
  apply()

  if (theme === "system") {
    mq.addEventListener("change", apply)
    return () => mq.removeEventListener("change", apply)
  }
}, [theme])
```

---

## WARNING Issues

### WR-01: `useQRAMMSession` `setError`/`setSession`/`ctx.setSessionId` calls run without cancellation guard

**File:** `src/dashboard/src/hooks/useQRAMMSession.ts:30-44`
**Issue:** Lines 30-32 call `setError` then return without checking `cancelled`. Line 34 finally checks `if (cancelled) return`. Lines 37-39 (`setSession(null)`, `ctx.setSessionId(null)`) and lines 43-44 (`setSession(latest)`, `ctx.setSessionId(latest.session_id)`) execute without guard between the early-return at line 34 and the next cancelled check. If a re-render fires `tick++` mid-fetch, the stale fetch can still mutate global QRAMM context (`ctx.setSessionId`), pulling the in-flight new fetch off-track.

**Fix:** Add `if (cancelled) return` immediately after each await; or wrap each setter pair.

---

### WR-02: `useScanList` silently swallows non-OK responses

**File:** `src/dashboard/src/hooks/useScanList.ts:13-29`
**Issue:** If `/api/scans` returns 500, the hook never sets sessions and never surfaces an error. The Sidebar's `ScanSelector` checks `loading || sessions.length <= 1` and hides itself, so the user sees no scan-history dropdown and no indication anything is wrong. Hard to debug.

**Fix:** Add an `error` state and surface it; or at least `console.error` non-OK responses.

---

### WR-03: Pending QRAMM debounce timers leak on provider unmount

**File:** `src/dashboard/src/context/QRAMMProvider.tsx:13`
**Issue:** `debounceRef.current` holds setTimeout handles. There is no cleanup useEffect to clear these on unmount. Pending fetches will fire after the provider has unmounted, potentially with a stale sessionId. If the user navigates to /qramm, types fast, then navigates away within 300ms, the persist POST fires post-unmount (mostly harmless but noisy in network tab and may write to a session the user thought they abandoned).

**Fix:**

```ts
useEffect(() => {
  return () => {
    for (const t of debounceRef.current.values()) clearTimeout(t)
    debounceRef.current.clear()
  }
}, [])
```

---

### WR-04: `theme-provider` casts localStorage value to `Theme` without validation

**File:** `src/dashboard/src/components/theme-provider.tsx:17-19`
**Issue:** `localStorage.getItem(storageKey) as Theme` will accept arbitrary strings (e.g., from a tampered localStorage or a stale value from a previous schema). Downstream `theme === "system"` check passes by, and `root.classList.add(theme)` adds an unknown class. Effect: visible CSS breakage.

**Fix:**

```ts
const stored = localStorage.getItem(storageKey)
const initial: Theme =
  stored === "dark" || stored === "light" || stored === "system" ? stored : defaultTheme
const [theme, setTheme] = useState<Theme>(initial)
```

---

### WR-05: `executive.tsx` PDF download `setTimeout` for revoke leaks across unmount; revoke timing is fragile

**File:** `src/dashboard/src/pages/executive.tsx:48`
**Issue:** `setTimeout(() => URL.revokeObjectURL(url), 100)` is unreferenced; if the user navigates away before 100ms, the timer still fires (harmless) but the 100ms heuristic is fragile — slow client (low-end Chromebook) may not have begun the download. Browsers' download dispatch from `a.click()` is synchronous in modern Chromium, so this works in practice, but a more robust pattern is to revoke on the next macrotask without arbitrary delay.

**Fix:** Use a microtask deferral and clean up on unmount:

```ts
queueMicrotask(() => URL.revokeObjectURL(url))
```

---

### WR-06: `executive.tsx` reads `body.detail` without coercion check

**File:** `src/dashboard/src/pages/executive.tsx:51-52`
**Issue:** `const body = await resp.json().catch(() => ({}))` then `body.detail ?? "..."`. If `body.detail` is an object (FastAPI sometimes returns `{detail: [{loc: [...], msg: ...}]}` for validation errors), `setPdfMessage` receives an object, and React will throw a child-render error.

**Fix:**

```ts
const body = await resp.json().catch(() => ({})) as { detail?: unknown }
const detail = typeof body.detail === "string" ? body.detail : null
setPdfMessage(detail ?? "PDF export failed. Ensure Playwright is installed: playwright install chromium")
```

---

### WR-07: `print.tsx` `data-ready` is set even when QRAMM has errored — silently produces incomplete PDFs

**File:** `src/dashboard/src/pages/print.tsx:329-341`
**Issue:** The effect sets `data-ready=true` when `data && !loading && !qrammLoading`. It does NOT check `qrammError`. The QRAMM section then renders a "no QRAMM assessment" fallback (line 175-181). This is by design — but PDFs that *should* contain QRAMM data (because a scored session exists) but momentarily failed to fetch will silently print without it, indistinguishable from "no assessment exists." Without a marker on the printed page, recipients cannot tell.

**Fix:** Either retry-on-error in `useQRAMMPrintData`, or include a footer note when `qrammError` is set. Acceptable to leave as-is if the policy is "QRAMM section is best-effort and never blocks PDF" — but that policy should be documented in the HUMAN-UAT for the Print page.

---

### WR-08: `qramm-profile.tsx` `submitError` swallows the actual error message

**File:** `src/dashboard/src/pages/qramm-profile.tsx:187-188`
**Issue:** `} catch (err) {` — `err` is bound but unused. The user always sees the canned "Could not start assessment" regardless of whether session creation or profile creation failed, what the HTTP code was, or whether it was a network failure. Hard to diagnose. Also fails strict-null TS-eslint `no-unused-vars`.

**Fix:**

```ts
} catch (err) {
  const msg = err instanceof Error ? err.message : "unknown error"
  setSubmitError(`Could not start assessment — ${msg}`)
}
```

---

### WR-09: `certificates.tsx` Subject CN regex breaks on RFC2253-escaped commas inside CN

**File:** `src/dashboard/src/pages/certificates.tsx:60-65`
**Issue:** `cert.cert_subject.match(/CN=([^,]+)/)` fails on certs whose CN contains commas (escaped in RFC2253 as `\,` or in real X.509 strings as legitimate parts like `CN=Acme, Inc.,O=Acme Corp`). Returns truncated CN ("Acme") missing ", Inc." Same issue with issuer regex (line 64).

**Fix:** Parse RFC2253 properly, or use a more tolerant regex like `/CN=((?:\\,|[^,])+)/`. For an MVP, slicing on `=` and walking is sufficient.

---

### WR-10: `cbom.tsx` Cytoscape registration uses cast without proper typing for community extensions

**File:** `src/dashboard/src/pages/cbom.tsx:20`, `src/dashboard/src/pages/roadmap.tsx:13`
**Issue:** `cytoscape.use(coseBilkent as cytoscape.Ext)` and `cytoscape.use(dagre as cytoscape.Ext)`. The `cytoscape-extensions.d.ts` file declares the modules without types — the cast pretends they conform to `cytoscape.Ext`. Functionally this works, but if the underlying API surface changes upstream, TypeScript won't catch it. Acceptable as-is, but flag for future tightening.

**Fix:** Either add proper module declarations with the extension's actual signature, or accept the cast and leave a comment.

---

### WR-11: ScorecardTab Maturity Distribution width math allows count > 4 if catalog grows

**File:** `src/dashboard/src/components/qramm/ScorecardTab.tsx:50-60, 194`
**Issue:** `(count / 4) * 100` assumes 4 dimensions. Today DIMENSIONS has 4 entries — fine. If a 5th dimension is ever added, the bar can render >100% width. Hard-coded 4 should be derived from `DIMENSIONS.length`.

**Fix:**

```ts
style={{ width: `${(count / DIMENSIONS.length) * 100}%` }}
```

---

### WR-12: ScorecardTab maturity progress bar applies badge classes (text/border) to empty div — produces unintended visuals

**File:** `src/dashboard/src/components/qramm/ScorecardTab.tsx:193`
**Issue:** `MATURITY_BADGE_CLASS[level]` is e.g. `"bg-quantum-safe/20 text-quantum-safe border border-quantum-safe/30"`. Applied to `<div className="h-2 rounded-full ${...}" />` — text-* classes do nothing useful on an empty div, and `border` adds a 1px border that interacts with `h-2` (2px) producing a near-invisible bar with mismatched vertical metrics. Cosmetic but visible.

**Fix:** Define a separate `MATURITY_BAR_CLASS` map with only background classes (no text-/border-).

---

### WR-13: `ComplianceMapTab` re-fetches on every `ctx.scoreResult` change — including identical results

**File:** `src/dashboard/src/components/qramm/ComplianceMapTab.tsx:113-136`
**Issue:** Effect depends on `[ctx.sessionId, ctx.scoreResult]`. Each Calculate Score click sets a new `scoreResult` reference (always — even if scores didn't change), which re-fires the compliance-map fetch. Wasteful but not buggy. Note: `scoreResult` reference identity changes even when underlying scores match.

**Fix:** Compare deep on overall+maturity, or accept the network cost.

---

### WR-14: `qramm-assessment.tsx` `handleNewAssessment` does not abort in-flight debounced QRAMM persists

**File:** `src/dashboard/src/pages/qramm-assessment.tsx:162-181`, `src/dashboard/src/context/QRAMMProvider.tsx:13`
**Issue:** When the user clicks "Confirm New Assessment", the page deletes the session server-side, then resets context. But if there are pending debounced draft writes for the OLD sessionId in `debounceRef`, they fire 300ms later. By that time, `sessionIdRef.current` may already be null (reset above) — the closure check `if (sid == null) return` at line 19 only runs at *queue time*; the timer's body uses `sid` (captured at queue time, equal to OLD session_id), and posts to a session that has been deleted. Server returns 404 silently.

Worse: if a NEW session is created in the same tab quickly (via Org Profile form), `sessionIdRef.current` holds the NEW id but pending timers still close over OLD `sid`. Stale POSTs to deleted session, then user thinks "answer didn't save" because they were viewing the new session.

**Fix:** Expose a `flushPending()` or `cancelPending()` method on QRAMMContext that the New-Assessment handler calls before DELETE:

```ts
// in QRAMMProvider
const cancelPending = useCallback(() => {
  for (const t of debounceRef.current.values()) clearTimeout(t)
  debounceRef.current.clear()
}, [])
// expose via context
```

Then `handleNewAssessment` calls `ctx.cancelPending()` before the DELETE fetch.

---

## INFO

### IN-01: `qramm-assessment.tsx` comment says "5-tab" but renders 6 tabs

**File:** `src/dashboard/src/pages/qramm-assessment.tsx:246`
**Issue:** Per project memory note. CVI/SGRM/DPE/ITR + Scorecard + Compliance Map = 6 tabs.

**Fix:** Update comment to "6-tab assessment layout".

---

### IN-02: `cbom.tsx` and `roadmap.tsx` try/catch swallows extension registration error silently

**File:** `src/dashboard/src/pages/cbom.tsx:19-23`, `src/dashboard/src/pages/roadmap.tsx:12-16`
**Issue:** `try { cytoscape.use(...) } catch { /* already registered */ }` swallows ALL errors, not just "already registered." If the extension is broken, you'd never know.

**Fix:** Check the error message and only swallow re-registration:

```ts
try { cytoscape.use(coseBilkent as cytoscape.Ext) } catch (e) {
  if (!String(e).includes("already")) console.warn("cytoscape extension load failed:", e)
}
```

---

### IN-03: `findings.tsx` and `identity.tsx` recreate columns array on every render

**File:** `src/dashboard/src/pages/findings.tsx:53-82`, `src/dashboard/src/pages/identity.tsx:71-86`
**Issue:** `columns` array literal is rebuilt every render. `useReactTable` is told to use a fresh reference each time, which triggers internal recalculation. Out-of-v1-scope perf, but flagging.

**Fix:** Wrap `columns` in `useMemo(() => [...], [])`.

---

### IN-04: `useQRAMMSession` `seededRef` not reset on New Assessment flow

**File:** `src/dashboard/src/hooks/useQRAMMSession.ts:18`
**Issue:** Correct in steady-state. Only edge case: if a future feature lets the user explicitly reload a previously-archived session, the seededRef may hold a stale ID. Low risk today.

**Fix:** No action required. Document the invariant in a comment.

---

### IN-05: `cbom.tsx` `compByAlg` lookups use `[0]` for representative — multi-instance algorithms drop key_size variance

**File:** `src/dashboard/src/pages/cbom.tsx:284-294, 390`
**Issue:** When multiple components share the same algorithm name with different key sizes (e.g., RSA-2048 and RSA-4096 both labeled "RSA"), the detail panel shows only the first entry's key_size, hiding diversity. Acceptable for MVP, but inconsistent with the table view that shows each row independently.

**Fix:** Show key-size range or all variants in the detail panel.

---

### IN-06: `print.tsx` createElement style injection works but is non-standard React pattern

**File:** `src/dashboard/src/pages/print.tsx:1, 368`
**Issue:** Using `createElement("style", null, PRINT_CSS)` to inject CSS works but is unusual. The CSS string is a pure constant, so security is fine (no injection vector). React 19's normal `<style>{PRINT_CSS}</style>` JSX would be clearer. The comment says "to avoid hook restrictions on inline HTML" — but JSX `<style>` has no such restriction.

**Fix:** Replace with normal JSX `<style>{PRINT_CSS}</style>`.

---

### IN-07: `useScanData` does not propagate the actual fetch URL into errors

**File:** `src/dashboard/src/hooks/useScanData.ts:32`
**Issue:** Error message includes status but not the URL. When debugging across multiple scan_ids in a session, knowing which URL failed helps. Minor.

**Fix:** Include `selectedScanId ?? "latest"` in the error string.

---

_Reviewed: 2026-05-08_
_Reviewer: Claude (gsd-code-reviewer, Opus 4.7)_
_Depth: deep_
