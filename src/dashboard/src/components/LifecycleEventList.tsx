import { useState } from "react"
import { History, ChevronDown } from "lucide-react"
import type { HardwareDriftEventItem } from "@/types/api"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyStateCard } from "@/components/EmptyStateCard"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { LifecycleEventRow } from "@/components/LifecycleEventRow"

// Phase 156 HWLC-10/11 — "Recent Lifecycle Changes" section, per
// 156-UI-SPEC.md §Section anatomy. Structurally and visually distinct from
// the scored-finding chrome (TIER_STYLES/PQC_STYLES/CONF_STYLES on
// hardware.tsx, SEVERITY_STYLES on compare.tsx): a teal-chrome, neutral
// -surface Card, never nested inside the device-table Card (D-02), with the
// advisory caption always rendered as visible DOM text (D-13).
//
// `events` is a prop, not fetched internally — this is what lets /compare
// reuse this component with CompareResponse.hardware_drift as its source.
//
// D-07 layer 1 (HWLC-11): this component must never import the score-
// regression alert chip or the filled-pill badge primitive, and must never
// use any of the app's severity-coded hsl() literals — enforced mechanically
// by lifecycle-advisory-guard.test.ts.

const TEAL = "hsl(180 37% 47%)"

const ADVISORY_CAPTION =
  "Advisory — hardware lifecycle changes do not affect the readiness score."

export interface LifecycleEventListProps {
  events: HardwareDriftEventItem[]
  historicalEvents?: HardwareDriftEventItem[]
  historicalTruncated?: boolean
  hasPriorScan: boolean
  lastScanDate?: string | null
  loading?: boolean
  error?: string | null
}

export function LifecycleEventList({
  events,
  historicalEvents = [],
  hasPriorScan,
  lastScanDate,
  loading = false,
  error = null,
}: LifecycleEventListProps) {
  const [historyOpen, setHistoryOpen] = useState(false)

  const lastScanLabel = lastScanDate
    ? new Date(lastScanDate).toLocaleDateString("en-US", { dateStyle: "medium" })
    : "the previous scan"

  return (
    <Card className="border-l-4 border-l-[hsl(180_37%_47%)]">
      <CardContent className="p-6 space-y-3">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4" style={{ color: TEAL }} aria-hidden="true" />
          <span className="label-eyebrow" style={{ color: TEAL }}>
            Recent Lifecycle Changes
          </span>
        </div>
        <h2 className="text-base font-semibold">Recent Lifecycle Changes</h2>
        <p className="text-xs text-muted-foreground">{ADVISORY_CAPTION}</p>

        <div role="separator" className="border-t border-border" />

        {loading ? (
          <div role="status" aria-label="Loading lifecycle changes" className="space-y-2">
            <span className="sr-only">Loading...</span>
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : error ? (
          <p className="text-sm text-muted-foreground">{error}</p>
        ) : !hasPriorScan ? (
          <EmptyStateCard message="No prior scan to compare against — This is the first scan recorded for these targets. Lifecycle tracking (tier changes, EOL proximity, CVE deltas) begins on the next scan of the same devices." />
        ) : events.length === 0 ? (
          <EmptyStateCard
            message={`No lifecycle changes detected — Hardware tier, bridge mitigation status, EOL proximity, and CVE correlation held steady since the last scan on ${lastScanLabel}. Advisory only — this has no effect on the readiness score.`}
          />
        ) : (
          <div className="divide-y divide-border">
            {events.map((event, i) => (
              <LifecycleEventRow key={`${event.host}-${event.port}-${event.event_type}-${i}`} event={event} />
            ))}
          </div>
        )}

        {!loading && !error && historicalEvents.length > 0 && (
          <>
            <div className="border-t border-border" />
            <Collapsible open={historyOpen} onOpenChange={setHistoryOpen}>
              <CollapsibleTrigger asChild>
                <button
                  type="button"
                  className="flex items-center gap-1 text-xs text-muted-foreground cursor-pointer"
                >
                  <ChevronDown
                    className={`h-3 w-3 transition-transform ${historyOpen ? "rotate-180" : ""}`}
                    aria-hidden="true"
                  />
                  {historyOpen
                    ? "Hide older lifecycle changes"
                    : `Show older lifecycle changes (${historicalEvents.length})`}
                </button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="divide-y divide-border mt-2">
                  {historicalEvents.map((event, i) => (
                    <LifecycleEventRow
                      key={`${event.host}-${event.port}-${event.event_type}-hist-${i}`}
                      event={event}
                      muted
                    />
                  ))}
                </div>
              </CollapsibleContent>
            </Collapsible>
          </>
        )}
      </CardContent>
    </Card>
  )
}
