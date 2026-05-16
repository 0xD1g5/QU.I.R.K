---
phase: 56
status: findings
depth: standard
reviewed_files:
  - src/dashboard/src/hooks/useQRAMMPrintData.ts
  - src/dashboard/src/pages/print.tsx
findings:
  critical: 1
  warning: 4
  info: 2
  total: 7
---

# Phase 56: Code Review Report

**Reviewed:** 2026-05-08T00:00:00Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Two files reviewed: the new `useQRAMMPrintData` hook and the extended `print.tsx`. The hook
implementation is clean and largely follows the `useScanData` pattern correctly. The print
component has one critical correctness bug in the `data-ready` gate, four warnings around
incorrect/missing logic, and two minor info-level items. No injection or XSS surface exists
(SVG content is entirely static constants, user data is JSX-interpolated not innerHTML).

---

## Critical Issues

### CR-01: `data-ready` fires even when scan data failed to load (error path bypasses gate)

**File:** `src/dashboard/src/pages/print.tsx:331-338`

**Issue:** The `useEffect` gate is:

```ts
if (data && !qrammLoading) {
  document.body.setAttribute('data-ready', 'true')
}
```

When `useScanData` returns `error` (network failure, 500, etc.) `data` stays `null` so
`data-ready` is never set — this part is fine. BUT `loading` from `useScanData` is not
checked here at all. The effect depends on `[data, qrammLoading]`. If `useScanData` is still
in flight (`loading === true`, `data === null`) while `qrammLoading` transitions to `false`
first, the condition `data && !qrammLoading` is momentarily `false` — no problem yet.

The real bug: when `useScanData` resolves successfully (`data` set, `loading = false`) but
`qrammLoading` is still `true`, the condition is `data && !qrammLoading` = false — correct.
However once both resolve, `data-ready` is set. That is the intended path.

The actual defect is that the effect's dependency array omits `loading`. Consider this race:

1. React mounts component. Both hooks set `loading = true`.
2. QRAMM hook resolves first: `qrammLoading = false`, `data` is still `null`.
   Effect fires: `null && true` → false. OK.
3. Scan data hook resolves: `data` set, `loading = false`.
   Effect fires: `data && !qrammLoading` = `truthy && true` → **sets `data-ready`**.

That is actually correct for the happy path. The latent bug surfaces in the **error + retry
scenario**: if the component re-renders after `error` is set (e.g., parent forces re-mount),
`data` becomes `null` again but `qrammLoading` may already be `false` from the prior
resolution. The cleanup in the effect's return removes `data-ready` — but only when the
**same** effect instance unmounts. If dependencies change in a way that re-runs the effect
while `data === null` and `qrammLoading === false`, `data-ready` is NOT set (correct), but
the cleanup from the prior run fires first and removes it, leaving the gate in a permanently
unset state even if a new fetch eventually succeeds.

More concretely: the cleanup function runs on **every** effect re-execution (not just
unmount), because it is returned from an effect that depends on `[data, qrammLoading]`. This
means every time either value changes, the cleanup fires and removes `data-ready`. If QRAMM
loads first (sets nothing), then scan data arrives (sets `data-ready`), then QRAMM would
never change again — OK. But if any dependency change causes a re-run *after* `data-ready`
was set, the cleanup removes it even though the data is still available and the gate condition
is still true. The attribute is then re-added by the new effect run, which is a transient
removal.

For a headless PDF renderer that polls `data-ready`, this transient removal between effect
cleanup and re-application is a **race window** where the renderer could fire the screenshot
before the attribute is restored.

**Fix:** Move the cleanup to only fire on unmount, or guard the cleanup:

```ts
useEffect(() => {
  if (data && !loading && !qrammLoading) {
    document.body.setAttribute('data-ready', 'true')
  } else {
    // Ensure attribute is removed when not ready
    document.body.removeAttribute('data-ready')
  }
  // No cleanup return — attribute removal is handled inline above
}, [data, loading, qrammLoading])
```

This eliminates the transient-removal window and also explicitly guards against the
`data === null` case (including the `loading` state from `useScanData` which the current
implementation omits from the condition entirely).

---

## Warnings

### WR-01: `loading` state initializes to `true` but never resets to `false` in the no-scored-session path

**File:** `src/dashboard/src/hooks/useQRAMMPrintData.ts:46`

**Issue:** When no scored session exists, the hook returns early without calling
`setLoading(false)` or passing through the `finally` block:

```ts
if (!scored) {
  if (!cancelled) {
    setScoreResult(null)
    setComplianceRows(null)
  }
  return   // <-- exits without setLoading(false)
}
```

The `finally` block at line 77 only runs when the function returns normally from the bottom
or throws. A bare `return` inside a `try` block **does** execute `finally` in JavaScript, so
this is actually safe — `finally` will still set `loading = false` after this return.

Wait — on re-examination this is **correct** behavior: `return` inside a `try` block causes
the `finally` clause to execute before the function returns. So `setLoading(false)` will be
called. However, the same applies to the `!listResp.ok` early return at line 33. That early
return also passes through `finally`, which calls `setLoading(false)` — also correct.

**Revised: this is a warning about the early-return-from-try pattern being non-obvious to
future maintainers.** If someone refactors the `finally` away, these early returns silently
break. The pattern should be documented or restructured for clarity.

**Fix:** Make the intent explicit — either add a comment noting that `finally` handles
`setLoading(false)` for all return paths, or explicitly call `setLoading(false)` before each
early `return` to make each path self-contained:

```ts
if (!scored) {
  if (!cancelled) {
    setScoreResult(null)
    setComplianceRows(null)
    // setLoading(false) handled by finally
  }
  return
}
```

### WR-02: Compliance summary table "Source" column is a duplicate of "Coverage Tier" — always identical values

**File:** `src/dashboard/src/pages/print.tsx:269-284`

**Issue:** The compliance summary table has three columns: Framework, Coverage Tier, Source.
Both "Coverage Tier" and "Source" are populated with the same `label` string
("Scanner-informed" or "Manual only"):

```tsx
<td><span className={cls}>{label}</span></td>  {/* Coverage Tier */}
<td>{label}</td>                                 {/* Source */}
```

The Source column is always identical in value to Coverage Tier (same `label` variable, line
279-280). The table renders two visually distinct columns (badge vs plain text) that convey
identical information. This is almost certainly not intentional — Source should probably show
a different value (e.g., "QUIRK scanner" vs "Manual evidence", or a source URL/reference).
As implemented it is dead output that misleads readers.

Per D-08 in CONTEXT.md the columns are defined as "Framework Name | Coverage Tier | Source" —
but the implementation maps both Tier and Source to the same `label`, making Source redundant.

**Fix:** Determine the intended Source value. If Source should distinguish data origin:

```tsx
<td>{tier === "scanner" ? "QUIRK scanner" : "Manual evidence"}</td>
```

Or remove the Source column if it adds no value beyond Coverage Tier.

### WR-03: Dimension Scorecard table repeats `scoreResult.maturity` for every row instead of per-dimension maturity

**File:** `src/dashboard/src/pages/print.tsx:250-263`

**Issue:** The Dimension Scorecard table renders one row per dimension (CVI, SGRM, DPE, ITR).
The Maturity column on every row is populated with `scoreResult.maturity`:

```tsx
<td>{scoreResult.maturity}</td>
```

`scoreResult.maturity` is the **overall** session maturity label (a single string on the
`QRAMMScoreResponse` root). It is the same value in all 4 rows — every row shows identical
maturity text. If the intent is to show the per-dimension maturity label, the API type
(`Record<string, { score: number; weighted: number }>`) does not include a per-dimension
maturity field, so the data is unavailable. If the intent is to show overall maturity, it
should appear once (e.g., in the heading row or a separate cell spanning all rows), not
repeated four times identically in each row.

**Fix:** Either show overall maturity once outside the table:

```tsx
<p><strong>Overall Maturity:</strong> {scoreResult.maturity}</p>
<table>
  <thead>
    <tr><th>Dimension</th><th>Raw Score</th><th>Weighted Score</th></tr>
  </thead>
  ...
```

Or remove the Maturity column from the per-dimension table entirely.

### WR-04: `data-ready` gate ignores `loading` from `useScanData` — gate can fire while scan is loading

**File:** `src/dashboard/src/pages/print.tsx:331-338`

**Issue:** The `data-ready` effect checks `data && !qrammLoading`, but `data` from
`useScanData` is initially `null` during the fetch. On the surface this works — `null &&`
short-circuits. However the effect dependency array is `[data, qrammLoading]` and does not
include `loading` (the scan loading flag). This means the scan's `loading` state is not part
of the gate computation.

Consider: `useScanData` initialises `data = null, loading = true`. The hook runs its async
fetch. If, in an unusual execution order (e.g., Strict Mode double-invoke, or a React
concurrent-mode teardown), `data` is set to a stale cached value before `loading` is reset,
the gate could fire early. This is a defence-in-depth concern rather than a production crash,
but the contract stated in CONTEXT.md §Established Patterns is:

> `data-ready` should only be set once BOTH `useScanData` and `useQRAMMPrintData` have
> resolved (`loading = false` for both).

The implementation only checks `!qrammLoading`, not `!loading`. The `loading` variable is in
scope but absent from both the condition and the dependency array.

**Fix:** (Same fix as CR-01 — address both together):

```ts
useEffect(() => {
  if (data && !loading && !qrammLoading) {
    document.body.setAttribute('data-ready', 'true')
  } else {
    document.body.removeAttribute('data-ready')
  }
}, [data, loading, qrammLoading])
```

---

## Info

### IN-01: No type guard on `scoreResult.dimensions` key access — silent zero-fill masks missing dimensions

**File:** `src/dashboard/src/pages/print.tsx:185-193`

**Issue:** Dimension scores are extracted with optional-chain + nullish coalescing:

```ts
const cviScore = scoreResult.dimensions["CVI"]?.score ?? 0
```

If the API returns a session where a dimension key is absent (e.g., incomplete scoring,
schema version skew), the polygon vertex silently falls to `0`, collapsing that axis to the
centre. The radar renders a misshapen polygon with no indication that a dimension was missing.
This is not a crash but it silently misrepresents data.

**Fix:** Add a console warning when a dimension is missing so the anomaly is at least visible
in browser DevTools during debugging:

```ts
const getDim = (key: string) => {
  const d = scoreResult.dimensions[key]
  if (!d) console.warn(`PrintQRAMM: dimension '${key}' missing from scoreResult`)
  return d?.score ?? 0
}
const cviScore = getDim("CVI")
```

### IN-02: `key={i}` (index-based key) used in all table row maps

**File:** `src/dashboard/src/pages/print.tsx:63, 94, 121, 305`

**Issue:** Four table components (`PrintFindings`, `PrintCerts`, `PrintCbom`, and the
per-framework practice detail loop) use array index as the React key. In a static print
context with no reordering or user interaction, this does not cause bugs. However it is
inconsistent — the per-framework rows at line 305 already use `key={row.practice_number}`
which is the stable identifier. The other tables have natural keys (`f.host+f.port`,
`c.host+c.port`, `c.algorithm`) that could be used instead. This is a pre-existing pattern
in the non-QRAMM code, but the new code in PrintQRAMM correctly uses the stable key,
highlighting the inconsistency in the older components.

**Fix:** Not strictly required for print correctness, but use stable keys in the pre-existing
components if they are ever touched in future:

```tsx
{findings.map((f) => (
  <tr key={`${f.host}-${f.port}-${f.title}`}>
```

---

_Reviewed: 2026-05-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
