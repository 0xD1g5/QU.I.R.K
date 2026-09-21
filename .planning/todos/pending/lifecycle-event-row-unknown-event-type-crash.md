# LifecycleEventRow crashes the whole /hardware page on an unknown drift event_type

**Filed:** 2026-09-21 (Phase 206 plan 206-09, while building a drift fixture — test-only phase, not fixed)
**Severity:** P2 — whole-page render crash, but only reachable when the API emits an event_type/direction
the frontend union does not know about.

## What

`src/dashboard/src/components/LifecycleEventRow.tsx:63-66`:

```tsx
const typeMeta = EVENT_TYPE_META[event.event_type]
const TypeIcon = typeMeta.icon          // <- throws if event_type is not one of the four keys
const dirMeta = DIRECTION_META[event.direction]
const DirIcon = dirMeta.icon            // <- same, for direction
```

`EVENT_TYPE_META` has exactly four keys (`tier_crossing`, `upstream_mitigated_change`, `cve_delta`,
`eol_state_change`) and `DIRECTION_META` three (`improved`, `worsened`, `neutral`). Any other value
arriving from `GET /api/hardware/drift` makes the lookup `undefined` and the `.icon` dereference
throws `TypeError: Cannot read properties of undefined (reading 'icon')`. Because
`LifecycleEventList` is rendered inside `HardwarePage`'s tree with no error boundary, this takes
down the **entire** `/hardware` page, not just the offending row.

Reproduced in jsdom on 2026-09-21: rendering `HardwarePage` with a drift fixture whose
`event_type` was `"pqc_status_changed"` (an off-by-one-word value) produced exactly that stack, at
`LifecycleEventRow.tsx:64:29`.

## Why it matters

The `HardwareDriftEventItem` union is a *compile-time* claim about *wire* data. TypeScript does not
validate the response; a backend that adds a fifth drift event type (or a QU.I.R.K. DB written by a
newer scanner than the dashboard build serving it — a real mixed-version scenario, since
`quirk serve` reads whatever `quirk.db` is on disk) silently becomes a blank page with a console
stack.

## The fix shape (not applied)

The sibling component already does the right thing — `src/dashboard/src/components/VendorTrendRow.tsx:24`:

```tsx
const typeMeta = EVENT_TYPE_META[event.event_type] ?? { icon: ShieldCheck, label: event.event_type }
```

Mirror that in `LifecycleEventRow` for both `EVENT_TYPE_META` and `DIRECTION_META` (a neutral icon
plus the raw value as its own label). This also matches `hardware.tsx`'s own established
raw-fallback convention for unmapped wire values (`snmpLabel`, `probeStateLabel`).

## Not fixed here

Phase 206 is test-only by CONTEXT: "if a test reveals a product defect, file it rather than fixing
it here." No UAT case covers this behaviour today.
