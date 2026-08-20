import type { ComponentType } from "react"
import { ShieldCheck } from "lucide-react"
import type { VendorPqcTrendEventItem } from "@/types/api"

// Phase 161 HWLC-19 — one vendor PQC trend event's row anatomy, mirroring
// LifecycleEventRow's flex-row layout (type icon, eyebrow label, identity,
// old->new transition, detected date). This is vendor-scoped, not
// device-scoped: no host/port identity block, and deliberately no
// direction-indicator block (up/down trend icon+color) and no partial
// re-probe badge block — the event item has neither a direction field
// nor a partial-scan flag.
//
// D-07 layer 1 (HWLC-11 precedent) — this component must never import the
// score-regression alert chip or the filled-pill badge primitive, and must
// never use any of the app's severity-coded hsl() literals — enforced
// mechanically by vendor-trend-advisory-guard.test.ts.

const EVENT_TYPE_META: Record<string, { icon: ComponentType<{ className?: string }>; label: string }> = {
  pqc_status_change: { icon: ShieldCheck, label: "PQC status change" },
}

export function VendorTrendRow({ event }: { event: VendorPqcTrendEventItem }) {
  const typeMeta = EVENT_TYPE_META[event.event_type] ?? {
    icon: ShieldCheck,
    label: event.event_type,
  }
  const TypeIcon = typeMeta.icon

  return (
    <div className="flex flex-wrap items-center gap-3 py-2 text-sm">
      <div className="flex items-center gap-1.5 text-muted-foreground shrink-0">
        <TypeIcon className="h-3.5 w-3.5" aria-hidden="true" />
        <span className="label-eyebrow">{typeMeta.label}</span>
      </div>

      <div className="min-w-0">
        <div className="font-data">{event.vendor}</div>
      </div>

      <div className="min-w-0 flex-1">
        {event.old_value ?? "—"} → {event.new_value ?? "—"}
      </div>

      <div className="text-xs text-muted-foreground font-data shrink-0">
        {new Date(event.detected_at).toLocaleDateString("en-US", { dateStyle: "medium" })}
      </div>
    </div>
  )
}
