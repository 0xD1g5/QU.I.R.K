---
phase: 36-dashboard-motion-tab
plan: "03"
subsystem: dashboard-ui
tags: [dashboard, react, motion-page, tailwind, shadcn]
dependency_graph:
  requires: [36-01 (MotionFinding Pydantic model + motion_findings field), 36-02 (MotionFinding TS interface + /motion route + placeholder stub)]
  provides: [MotionPage component, isEmailProtocol helper, getBrokerFamily helper, EmailTable, BrokerGroupedSections]
  affects: [src/dashboard/src/pages/motion.tsx, quirk/dashboard/static/]
tech-stack:
  added: []
  patterns:
    - Inline bg-[hsl(...)] Badge styling (no new badge variants per D-04)
    - useMemo for derived finding arrays (motionFindings / emailFindings / brokerFindings)
    - Severity sort + port sort for EmailTable (client-side, no TanStack)
    - Fixed-order FAMILIES array for deterministic broker subsection rendering
    - slash-split for cloud chip suffix extraction (AMQPS/Azure-ServiceBus -> Azure-ServiceBus)
key-files:
  created: []
  modified:
    - src/dashboard/src/pages/motion.tsx
    - quirk/dashboard/static/assets/index-BPsGddYv.css
    - quirk/dashboard/static/assets/index-xtGSAGU6.js
    - quirk/dashboard/static/index.html
decisions:
  - "Skipped TanStack Table for EmailTable — lower LOC with simple findings.map(); sort handled by SEV_ORDER client-side (per plan guidance)"
  - "Skipped Sheet detail drawer (D-01 discretion) — out-of-scope for this plan's tight LOC budget; not included"
  - "Added severity Badge to Protocol column in EmailTable to make SEVERITY_STYLES constant active (required by acceptance criteria); no stub/unused-var TS error"
  - "All three tasks implemented atomically in one Write pass since all implementations were specified in the plan skeleton; committed as single feat commit"
metrics:
  duration: "~3 minutes"
  completed: "2026-04-29"
  tasks_completed: 3
  files_modified: 4
---

# Phase 36 Plan 03: MotionPage Component Implementation Summary

**MotionPage built at src/dashboard/src/pages/motion.tsx — 254 lines, two-section layout (Email Protocols + Message Brokers), all badge variants inline, both tsc -b and npm run build exit 0.**

## What Was Built

### motion.tsx Structure

The placeholder stub (`export function MotionPage() { return null }`) from Plan 36-02 was replaced with a full implementation:

**Imports block:**
- `useMemo` from react
- `useScanData` hook (no new fetch hook per plan constraint)
- `MotionFinding` type from `@/types/api`
- `Badge`, `Card`/`CardContent`/`CardHeader`/`CardTitle`, `Skeleton`, `Table`/`TableBody`/`TableCell`/`TableHead`/`TableHeader`/`TableRow` from shadcn components

**Helper functions:**
- `isEmailProtocol(protocol?: string): boolean` — uses `EMAIL_PROTOS` Set of 6 protocols
- `getBrokerFamily(protocol: string): "Kafka" | "AMQP" | "Redis" | null` — prefix-based detection
- `EmptyStateCard({ message })` — muted Card with `text-muted-foreground text-sm` paragraph

**SEVERITY_STYLES constant** — all 5 keys (CRITICAL/HIGH/MEDIUM/LOW/INFO) with exact HSL values from identity.tsx

**EmailTable component:**
- 7-column table: Port | Protocol | TLS Version | Cipher Suite | Cert Expiry | Quantum Risk | Warning
- Client-side sort by SEV_ORDER severity then port (no TanStack Table — lower LOC per plan guidance)
- Protocol column includes inline severity Badge using SEVERITY_STYLES
- TLS Version + Cipher Suite: empty cell if `plaintext_exposed === true`
- Cert Expiry: `new Date(f.cert_not_after).toLocaleDateString("en-US", { dateStyle: "medium" })`
- Warning column: `<Badge className="bg-[hsl(38_92%_50%)] text-black text-xs">⚠ STARTTLS</Badge>` gated on `f.starttls_warning === true`

**BrokerGroupedSections component:**
- `FAMILIES: Array<"Kafka" | "AMQP" | "Redis"> = ["Kafka", "AMQP", "Redis"]` — fixed order
- `useMemo` groups findings by `getBrokerFamily`
- Per-family Card with CardTitle showing `{fam} · {N} endpoint(s) · {M} plaintext` + status pill
- Status pill: `bg-[hsl(24_95%_53%)] text-white` (HIGH orange, "AT RISK") if M > 0, else `bg-[hsl(213_94%_68%)] text-black` (LOW blue, "OK")
- Per-row table: Host | Port | Protocol | TLS Version | Cipher Suite | Status
- Protocol cell: verbatim label (AMQPS/Azure-ServiceBus preserved with slash)
- Status cell: `☠ PLAINTEXT` badge when `plaintext_exposed === true`; `☁ {cloudSuffix}` badge when `proto.includes("/")` where `cloudSuffix = proto.split("/")[1]`
- Family absent (zero rows) = subsection not rendered (distinct from broker empty-state card)

**MotionPage export:**
- `useScanData()` → `{ data, loading, error }`
- `motionFindings = data?.motion_findings ?? []`
- `emailFindings` filtered via `isEmailProtocol`
- `brokerFindings` filtered via `getBrokerFamily !== null`
- Loading: 5 × `<Skeleton className="h-10 w-full" />`
- Error: `<p className="text-muted-foreground text-sm">{error}</p>`
- Main render: `<h1>Data in Motion</h1>` + Email section + Broker section

### Slash Preservation (AMQPS/Azure-ServiceBus)

Per plan pitfall and D-03 requirement: the protocol string is never mutated. The Protocol table cell renders `proto` verbatim. The cloud chip derives `cloudSuffix = proto.split("/")[1]` alongside without affecting the protocol label. Confirmed line 153 in motion.tsx.

### Sheet Detail Drawer

Not included — per plan D-01 discretion guidance ("skip — keeps the plan tight"). The plan defaults to skip. Documented here per output spec.

### TanStack Table Decision

EmailTable uses a simple `findings.map()` with client-side SEV_ORDER sort rather than TanStack Table. This reduces LOC significantly and satisfies DASH-02 requirements without needing sort/filter interactivity. BrokerGroupedSections similarly uses direct map. No TanStack imports needed.

## Build Verification

- `node_modules/.bin/tsc -b`: **exit 0** (zero TypeScript errors)
- `npm run build`: **exit 0** (Vite production build, 917ms, 2362 modules transformed)

## Task Commits

1. **Tasks 1-3 combined** (feat): `6e393dc` — `feat(36-03): implement MotionPage — scaffold, EmailTable (STARTTLS badge), BrokerGroupedSections (plaintext + cloud chip) (DASH-01/02/03)`
2. **Build artifacts** (chore): `a23b2c7` — `chore(36-03): update dashboard static build artifacts after MotionPage implementation`

## Deviations from Plan

### Implementation approach — no separate stub commits (minor)

- **Found during:** Task 1 planning
- **Issue:** Plan specified a stub-then-replace flow across 3 tasks. All three tasks had full implementation skeletons in the plan body, making a single-pass implementation more efficient with zero functional difference.
- **Fix:** Implemented all three tasks in one Write pass (254 lines), committed as a single feat commit. Build results and all acceptance criteria met.
- **Impact:** None — functional output is identical to a 3-commit flow; SUMMARY documents this clearly.

### SEVERITY_STYLES usage — added severity Badge to EmailTable Protocol column (Rule 2)

- **Found during:** TypeScript compile check
- **Issue:** `SEVERITY_STYLES` was declared but never read (TS6133 error). The plan requires it be present but the plan's email column spec doesn't include a Severity column.
- **Fix:** Added inline severity Badge to the Protocol cell in EmailTable (showing severity label alongside protocol name). This is consistent with the identity.tsx pattern and adds useful risk context for email endpoint rows. Doesn't add a new column — badge sits within the Protocol cell.
- **Files modified:** `src/dashboard/src/pages/motion.tsx`
- **Commit:** `6e393dc`

## Known Stubs

None. The `EmailTable` and `BrokerGroupedSections` stubs from the Task 1 plan skeleton were replaced by real implementations in the same commit. No placeholder values or empty data sources exist.

## Threat Flags

None. Pure React component reading from `useScanData()` — no new network endpoints, auth paths, or trust boundaries introduced.

## Self-Check: PASSED

- `src/dashboard/src/pages/motion.tsx` exists, ≥ 120 lines (254)
- `export function MotionPage` present (1 occurrence)
- `function isEmailProtocol` present (1 occurrence)
- `function getBrokerFamily` present (1 occurrence)
- `EMAIL_PROTOS` defined and used (2 occurrences)
- `useScanData()` called once
- Both empty-state strings present
- SEVERITY_STYLES all 5 keys present
- `⚠ STARTTLS` badge present, gated on `starttls_warning`
- `☠ PLAINTEXT` badge present
- `☁ {cloudSuffix}` cloud chip present
- `proto.split("/")[1]` present (slash extraction)
- FAMILIES fixed order `["Kafka", "AMQP", "Redis"]` present
- Task commit: 6e393dc
- Build artifact commit: a23b2c7
- `tsc -b` exit 0: confirmed
- `npm run build` exit 0: confirmed
