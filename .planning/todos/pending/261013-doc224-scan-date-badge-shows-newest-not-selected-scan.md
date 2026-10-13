---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure GC3-OPS (fork A); ledger rows DCL-OPS-A-0134, DCL-OPS-A-0135, DCL-OPS-GC3A-0002 (docs/operators-guide.md §2.4 Scan-date badge)
priority: low
area: src/dashboard/src/components/ScanDateBadge.tsx, src/dashboard/src/hooks/useScanList.ts
status: pending
resolves_phase: null
---

# The sidebar "Last scan" badge ignores the selected scan, never refreshes, and says "No scan yet" on a fetch error

The badge (TAIL-01) was described as telling the operator "how current the data you're looking at is". It cannot:

1. It always shows `sessions[0]` (`ScanDateBadge.tsx:17`), the newest scan from `/api/scans` (newest first,
   `quirk/dashboard/api/routes/scan.py:1495`). It does not read `useSelectedScan`, so with an older scan picked in the
   selector it shows a date that does not belong to the data on screen.
2. `useScanList` fetches once on mount (`useScanList.ts:52`, empty dependency array). The sidebar mounts once, so a
   scan that finishes later does not move the badge until a page reload.
3. On a 401/403/429/network error `sessions` stays `[]`, and the badge reads "No scan yet" even when scans exist.

The operators-guide now says the badge shows the newest scan as of page load, not the selected one.

- [ ] Decide whether the badge should show the selected scan (likely) and wire it to `useSelectedScan`.
- [ ] Refresh the list when a job completes, or on navigation.
- [ ] Render an error state instead of "No scan yet" when the fetch fails.

## Feasibility & Effort

- **CONFIRMED** at `src/dashboard/src/components/ScanDateBadge.tsx:17` and `src/dashboard/src/hooks/useScanList.ts:52`.
- **LIKELY** effort **S**: hook change plus vitest updates; dashboard rebuild required (statics are committed).
  No spike needed.
