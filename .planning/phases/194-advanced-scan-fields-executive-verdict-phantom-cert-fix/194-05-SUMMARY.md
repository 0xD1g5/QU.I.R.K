---
phase: 194
plan: 05
subsystem: dashboard-frontend
tags: [scan-form, advanced-fields, effective-config-preview, parity]
dependency-graph:
  requires: ["194-02"]
  provides: ["AdvancedPanel.tsx", "AdvancedScanFields (types/api.ts)"]
  affects: ["scan-new.tsx", "EffectiveConfigPanel.tsx"]
tech-stack:
  added: []
  patterns:
    - "delta-only overlay map (ConnectorsPanel precedent), setField() deletes empty keys"
    - "collapsible form-section shell (Collapsible + Card, chevron-rotate trigger)"
key-files:
  created:
    - src/dashboard/src/components/AdvancedPanel.tsx
    - src/dashboard/src/components/__tests__/AdvancedPanel.test.tsx
  modified:
    - src/dashboard/src/types/api.ts
    - src/dashboard/src/pages/scan-new.tsx
    - src/dashboard/src/components/EffectiveConfigPanel.tsx
    - src/dashboard/src/components/__tests__/EffectiveConfigPanel.test.tsx
    - quirk/dashboard/static/ (rebuilt assets)
decisions:
  - "No per-field 'Preset: {label}' provenance badges on AdvancedPanel (Researcher's Discretion, UI-SPEC default) — presetState is accepted for interface symmetry and used only for input placeholders"
  - "advanced is NOT cleared after a successful submit (unlike credentials) — these aren't secrets and a repeat scan should retain them"
  - "TLS Ports input binds to the same customPorts state the Custom port scope already uses; advancedPayload derives ports_tls from customPorts only when Custom scope is active and non-empty, avoiding a second independent port input (RESEARCH Pitfall 5)"
metrics:
  duration: "~40 minutes"
  completed: "2026-09-09"
---

# Phase 194 Plan 05: Advanced Scan Fields UI Summary

Collapsed "Advanced" section on the scan-submit form exposing plan 194-02's backend overlay
fields (TLS ports, TLS enumeration mode, discovery/SNI, timeouts + retry, data classification),
feeding the live effective-config preview and surfacing the server's 422 as the authority.

## What Was Built

**Task 1 — `AdvancedPanel.tsx` + tests + `types/api.ts`.** New `AdvancedScanFields` TypeScript
interface mirrors plan 194-02's Pydantic model (all optional) and is threaded onto
`ScanSubmitRequest.advanced?`. `AdvancedPanel.tsx` is the structural analog of
`ConnectorsPanel.tsx` — same `Collapsible` + `Card` shell, same chevron-rotate trigger pattern,
renamed to "Advanced" — minus the availability-fetch `useEffect` (there is no server-side
"advanced field availability" probe; every field here is always settable). Renders, in a
`grid-cols-1 md:grid-cols-2` layout: TLS Ports (free-text `Input` with helper text and a
client-side amber hint for a malformed port shape, never blocking submit), TLS Enumeration Mode
(`Select` offering exactly Fast/Deep, D-19 — no "Off"), Discovery Options (a single `Switch` for
`include_sni`; `enable_nmap` already has its own top-level checkbox and is deliberately not
duplicated here), Timeouts & Retry (four numeric `Input` fields with `min`/`max` UX bounds), and
Data Classification (`Select` offering exactly Public/Internal/Confidential/Regulated, D-21 — no
"Restricted"). A local `setField()` implements the delta-only rule (D-02): every change writes
only the touched key into the map, and clearing a field back to empty **deletes** the key rather
than writing `""`/`NaN`. No SSH Ports field is rendered (D-18) — a code comment names backlog item
999.106 so a future reader does not "restore" it. Each field shows an accent "Set" badge when its
key is present in the delta map. 6 new tests cover collapsed-by-default, single-key delta on one
edit, key-removal on clear, the exact Fast/Deep option set, the exact 4-value classification
option set, and the absence of any "SSH Ports" text.

**Task 2 — mount on `scan-new.tsx` + submit wiring.** `<AdvancedPanel/>` mounts between
`<ConnectorsPanel/>` and `<EffectiveConfigPanel/>` per D-04's required order. A new
`advanced` state (`useState<AdvancedScanFields>({})`) feeds it. In `handleSubmit`, an
`advancedPayload` is derived as `{...advanced, ...(portScope === "custom" && customPorts.trim()
? { ports_tls: customPorts.trim() } : {})}` — this keeps ONE port-spec string in play per
RESEARCH's Pitfall 5 resolution: the AdvancedPanel's own `ports_tls` input is a real, independent
field for every other scope, but when Custom scope is active the submitted overlay is derived
from the same `customPorts` string the Custom-scope input already populates, so the two never
diverge. A one-line note ("Also applied via the Custom port scope above.") renders under
AdvancedPanel when `portScope === "custom"`. The request body gains `advanced: advancedPayload`
only when non-empty (D-02, mirroring Phase 193's `connectors` guard) — an untouched form submits
the byte-identical body it submitted before this phase. The existing 422 array-`detail` branch now
also checks `detail[0]?.loc?.includes("advanced")` and renders
`Invalid {field}: {reason}. Fix the value above and resubmit.` in the existing destructive
`rejectionBanner` (D-03) — no new banner component.

**Task 3 — `EffectiveConfigPanel.tsx` query extension.** `EffectiveConfigPanelProps` gains an
optional `advanced?: AdvancedScanFields` prop, mirroring the Phase 193 `connectors?` prop's own
shape and comment. `buildQuery` appends `advanced=<JSON>` after the existing `connectors` block,
guarded by `Object.keys(props.advanced ?? {}).length > 0` — additive-only, so an empty/undefined
delta produces the byte-identical query string this panel produced before this phase. Because the
panel already refetches on query-string change (existing `[open, query]` effect dependency), no
new effect or dependency-array entry was needed — editing any Advanced field automatically
re-fetches the preview. 3 new tests: empty-delta parity (asserts the exact pre-existing query
string, byte-for-byte), non-empty delta shape, and a refetch-key-moves regression proving a value
change produces a different query string on the second fetch call.

## Verification

- `AdvancedPanel.test.tsx`: 6/6 passing.
- `EffectiveConfigPanel.test.tsx`: 10/10 passing (up from 7, +3 new).
- `scan-new-port-scope.test.tsx` + `scan-new-effective-config-panel.test.tsx`: 10/10 passing
  (pre-existing, unaffected).
- Full frontend suite: `npm run build && npm run lint && npm run test` — 44 files, 313 tests, all
  green (up from 41/304 before this plan).
- All plan-specified `grep` acceptance criteria pass: `export function AdvancedPanel` (1 match),
  `SSH Ports` (0, case-insensitive), `999.106` (2 matches), `restricted` (0, case-insensitive),
  `regulated` (2 matches), `"off"` (0 literal matches), `<AdvancedPanel` mount line falls between
  `<ConnectorsPanel` and `<EffectiveConfigPanel`, `advanced: advancedPayload` present,
  `params.set("advanced"` exactly one guarded occurrence.
- Dashboard static assets rebuilt and committed separately.

## Deviations from Plan

**1. [Rule 1 - Bug] `SetBadge` sub-component defined inside render triggered `react-hooks/static-components` lint error.**
- **Found during:** Task 1, first `npm run lint` run.
- **Issue:** The plan's badge pattern (mirroring `ConnectorsPanel.tsx`'s inline JSX, not a
  separate component) was implemented as a nested `function SetBadge(...)` component defined
  inside `AdvancedPanel`'s render body — ESLint's `react-hooks/static-components` rule (not
  present when `ConnectorsPanel.tsx` was written, or its inline badge JSX simply never triggered
  it since it wasn't extracted into a named component) flagged this as "components created during
  render will reset their state each time they are created."
- **Fix:** Renamed to a lowercase `renderSetBadge(field)` plain function (not a component — never
  used as a JSX tag, invoked as `{renderSetBadge("field_name")}`), which the same rule does not
  flag since it isn't recognized as a component definition.
- **Files modified:** `src/dashboard/src/components/AdvancedPanel.tsx`.
- **Commit:** `8d3d4d9b` (folded into Task 1's commit, found before that commit landed).

**2. [Rule 1 - Bug] Data Classification `Select` placeholder collided with its own "Confidential" option text.**
- **Found during:** Task 1, first `AdvancedPanel.test.tsx` run.
- **Issue:** The plan's placeholder text (`presetState?.data_classification ?? "Confidential"`)
  produced two elements with the text "Confidential" once the select was opened (the closed
  trigger's placeholder span plus the open dropdown's `SelectItem`), making
  `screen.getByText("Confidential")` ambiguous and failing the D-21 option-set test.
- **Fix:** Changed the unset placeholder to the generic "Select classification" (matching the TLS
  Enumeration Mode select's own "Select mode" unset-state placeholder pattern already used
  elsewhere in this file); `presetState?.data_classification` still takes precedence when set.
- **Files modified:** `src/dashboard/src/components/AdvancedPanel.tsx`.
- **Commit:** `8d3d4d9b` (folded into Task 1's commit, found before that commit landed).

No other deviations. Plan otherwise executed as written.

## Known Stubs

None. All fields render real, wired controls backed by live state; no placeholder/mock data paths.

## Threat Flags

None — this plan's changes fall entirely within the threat model's existing T-194-16/17/18/19/SC
dispositions (client-side hints advisory-only, port-spec string passed through unparsed,
`GET /api/config/effective` already auth-gated, numeric `min`/`max` are UX-only, zero new npm
dependencies).

## Self-Check: PASSED

- `src/dashboard/src/components/AdvancedPanel.tsx` — FOUND
- `src/dashboard/src/components/__tests__/AdvancedPanel.test.tsx` — FOUND
- `src/dashboard/src/components/EffectiveConfigPanel.tsx` (modified) — FOUND
- `src/dashboard/src/components/__tests__/EffectiveConfigPanel.test.tsx` (modified) — FOUND
- `src/dashboard/src/pages/scan-new.tsx` (modified) — FOUND
- `src/dashboard/src/types/api.ts` (modified) — FOUND
- Commit `8d3d4d9b` — FOUND (`git log --oneline --all | grep 8d3d4d9b`)
- Commit `3adffe97` — FOUND
- Commit `09c8c37e` — FOUND
- Commit `29dee6aa` — FOUND
