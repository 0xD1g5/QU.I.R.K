import { ShieldCheck } from "lucide-react"
import type { VendorPqcTrendEventItem } from "@/types/api"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyStateCard } from "@/components/EmptyStateCard"
import { VendorTrendRow } from "@/components/VendorTrendRow"

// Phase 161 HWLC-19 — "Vendor PQC Status Trends" section, giving the Phase
// 160 GET /api/hardware/vendor-trends endpoint its first dashboard
// consumer. Mirrors LifecycleEventList's Card structure (teal-chrome,
// neutral-surface Card, advisory caption always rendered as visible DOM
// text). Deliberately has no prior-scan-precondition prop/branch — vendor
// trends have no per-device prior-scan precondition — and no Collapsible
// "Show older" affordance; a truncated flag instead renders a plain-text
// note (per the API's existing limit/truncated contract, no pagination).
//
// D-07 layer 1 (HWLC-11 precedent): this component must never import the
// score-regression alert chip or the filled-pill badge primitive, and must
// never use any of the app's severity-coded hsl() literals — enforced
// mechanically by vendor-trend-advisory-guard.test.ts.

const TEAL = "hsl(180 37% 47%)"

const ADVISORY_CAPTION =
  "Advisory — vendor PQC status trends do not affect the readiness score."

export interface VendorTrendListProps {
  events: VendorPqcTrendEventItem[]
  truncated?: boolean
  loading?: boolean
  error?: string | null
}

export function VendorTrendList({
  events,
  truncated = false,
  loading = false,
  error = null,
}: VendorTrendListProps) {
  return (
    <Card className="border-l-4 border-l-[hsl(180_37%_47%)]">
      <CardContent className="p-6 space-y-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4" style={{ color: TEAL }} aria-hidden="true" />
          <span className="label-eyebrow" style={{ color: TEAL }}>
            Vendor PQC Status Trends
          </span>
        </div>
        <h2 className="text-base font-semibold">Vendor PQC Status Trends</h2>
        <p className="text-xs text-muted-foreground">{ADVISORY_CAPTION}</p>

        <div role="separator" className="border-t border-border" />

        {loading ? (
          <div role="status" aria-label="Loading vendor PQC trends" className="space-y-2">
            <span className="sr-only">Loading...</span>
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : error ? (
          <p className="text-sm text-muted-foreground">{error}</p>
        ) : events.length === 0 ? (
          <EmptyStateCard message="No vendor PQC status trends recorded — No fleet-wide vendor PQC status transitions have been confirmed yet. Advisory only — this has no effect on the readiness score." />
        ) : (
          <div className="divide-y divide-border">
            {events.map((event, i) => (
              <VendorTrendRow key={`${event.vendor}-${event.event_type}-${i}`} event={event} />
            ))}
          </div>
        )}

        {!loading && !error && truncated && (
          <p className="text-xs text-muted-foreground">
            Older vendor PQC status trend events exist beyond the displayed limit.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
