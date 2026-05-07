# Command — Obsidian Pro UI kit

A click-thru recreation of the security tooling console implied by the v1.1 component reference (`ds-components.html`). "Command" is the working name — the v1.1 nav demos used it for the dashboard product.

## What's here

- `index.html` — full prototype shell. Loads tokens, renders the app chrome, mounts React, wires the screen router.
- `components.jsx` — shared atoms: `Button`, `Badge`, `Stat`, `Field`, `Input`, `Select`, `Search`, `Checkbox`, `Header`, `NavRail`, `Icon` (Lucide wrapper).
- `DashboardScreen.jsx` — Layer 1 metrics + Layer 2 recent table.
- `DetectionsScreen.jsx` — full triage table with severity filtering and row drill-in.
- `DetailDrawer.jsx` — Layer 3 actionable detail, slides in from the right when a row is clicked.

## Click-thru behavior

- The icon-rail toggles between Dashboard / Detections / Assets (assets is a stub).
- On Detections, clicking a row opens the detail drawer.
- The drawer's *Investigate*, *Assign*, *Dismiss* buttons close the drawer.
- A theme toggle in the header switches between dark and light.

## Cosmetic-only

This is a UI kit — not production. Filtering, sorting, and search inputs are visually wired but don't fully filter the data. State is local React, no persistence.

## Caveats

- Real product wordmark is a `C` placeholder tile.
- Asset inventory and Settings are stubbed. Add screens as needed.
