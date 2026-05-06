---
phase: 39
plan: "04"
subsystem: dashboard-ui
tags: [react, table, severity-sort, boolean-badge, xss-safe, dar]
one_liner: "Four locked-column DAR tables (Database/ObjectStorage/Kubernetes/Vault) with severity sort, boolean badges, and null-dash rendering replace placeholder cards"
requirements: [GAP-04]

dependency_graph:
  requires: [39-03]
  provides: [dar-tables-rendered]
  affects: [src/dashboard/src/pages/data-at-rest.tsx]

tech_stack:
  added: []
  patterns:
    - "BoolBadge helper component for boolean fields with locked badge copy/color per UI-SPEC"
    - "sortBySev defensive-copy sort using SEV_ORDER constant"
    - "nullDash/truncate helpers for safe field rendering"
    - "SeverityBadge reusing SEVERITY_STYLES constant (matches motion.tsx pattern)"

key_files:
  created: []
  modified:
    - src/dashboard/src/pages/data-at-rest.tsx

decisions:
  - "Used BoolBadge shared helper rather than inline ternaries to keep boolean badge rendering DRY and spec-compliant"
  - "Engine column for DatabaseTable maps from f.protocol (matches D-06 source field; f.category is always 'database' for this table)"
  - "Provider column for ObjectStorageTable maps from f.protocol (consistent with D-06 spec)"
  - "ObjectStorageTable: encryption_mode='none' rendered in destructive red badge; all other non-null values plain text"

metrics:
  duration_minutes: 8
  tasks_completed: 1
  tasks_total: 1
  files_modified: 1
  completed_date: "2026-04-29"
---

# Phase 39 Plan 04: DAR Table Components Summary

## What Was Built

Four category-tuned table components were added to `data-at-rest.tsx` and wired into `DataAtRestPage`. Each table replaces the placeholder `EmptyStateCard` that previously showed `"Pending table render — N finding(s)"`.

### DatabaseTable

Columns: Engine | Host | Port | Severity | Title | Encryption at Rest | TLS in Transit | Quantum Risk | Remediation

- Engine maps from `f.protocol` (POSTGRESQL / MYSQL / RDS)
- `encryption_at_rest`: ENCRYPTED (green) / UNENCRYPTED (red) / — (null)
- `tls_in_transit`: TLS ON (green) / TLS OFF (red) / — (null)

### ObjectStorageTable

Columns: Provider | Host | Severity | Title | Encryption Mode | Public Access | KMS Key | Versioning | Quantum Risk | Remediation

- `encryption_mode = "none"` renders in destructive red badge; other values plain text; null → —
- KMS Key in monospace font, truncated at 20 chars
- `public_access`: PUBLIC (red) / PRIVATE (muted)
- `versioning`: ON (blue) / OFF (muted)

### KubernetesTable

Columns: Namespace | Host | Severity | Title | Secret Type | Encryption Provider | Quantum Risk | Remediation

All text + nullDash; no boolean badges in this table.

### VaultTable

Columns: Host | Severity | Title | Mount Type | Seal Type | Auto-Unseal | Quantum Risk | Remediation

- `auto_unseal`: YES (green) / NO (muted)

### Shared Helpers

- `BoolBadge`: renders boolean fields with locked badge copy/color per UI-SPEC, or em dash for null/undefined
- `SeverityBadge`: uses SEVERITY_STYLES (copied verbatim from motion.tsx)
- `SEV_ORDER` / `sortBySev`: sorts CRITICAL → HIGH → MEDIUM → LOW → INFO, tiebreak by host then port
- `nullDash`: renders em dash for null/undefined/empty strings
- `truncate(s, n=60)`: truncates with ellipsis for remediation columns

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. All four table components render real field data from `DarFinding`. No hardcoded placeholder values.

## Threat Surface Scan

No new network endpoints or auth paths introduced. All scanner string fields rendered through React text nodes (`{f.field}`, `{nullDash(...)}`, `{truncate(...)}`). The `__html` prop is absent from the file (enforced by acceptance criterion and verified by grep). T-39-05 mitigated.

## Commits

| Hash | Message |
|------|---------|
| 135103f | feat(39-04): add four DAR table components with severity sort and boolean badges |

## Self-Check

- [x] `src/dashboard/src/pages/data-at-rest.tsx` exists and contains all four table functions
- [x] Commit `135103f` exists
- [x] `npm run build` exited 0 (✓ built in 647ms)
- [x] All 21 acceptance criteria grepped PASS
- [x] No unexpected file deletions in commit

## Self-Check: PASSED
