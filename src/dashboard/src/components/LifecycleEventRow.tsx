import type { ComponentType } from "react"
import {
  Layers,
  ShieldCheck,
  Bug,
  CalendarClock,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react"
import type { HardwareDriftEventItem } from "@/types/api"

// Phase 156 HWLC-10/11 — one lifecycle event's row anatomy, per
// 156-UI-SPEC.md §Event row anatomy. Left-to-right: type icon, event-type
// label (plain text, never a Badge), device identity, old->new transition,
// direction indicator (icon + one-word label, text color only, no fill),
// detected date.
//
// D-07 layer 1 (HWLC-11): this component must never import the score-
// regression alert chip or the filled-pill badge primitive, and must never
// use any of the app's severity-coded hsl() literals — enforced mechanically
// by lifecycle-advisory-guard.test.ts.

const EVENT_TYPE_META: Record<
  HardwareDriftEventItem["event_type"],
  { icon: ComponentType<{ className?: string }>; label: string }
> = {
  tier_crossing: { icon: Layers, label: "Tier crossing" },
  upstream_mitigated_change: { icon: ShieldCheck, label: "Bridge mitigation change" },
  cve_delta: { icon: Bug, label: "CVE correlation change" },
  eol_state_change: { icon: CalendarClock, label: "EOL/EOS state change" },
}

const DIRECTION_META: Record<
  HardwareDriftEventItem["direction"],
  { icon: ComponentType<{ className?: string }>; label: string; colorClass: string }
> = {
  improved: {
    icon: TrendingUp,
    label: "Improved",
    colorClass: "text-[hsl(172_45%_42%)]",
  },
  worsened: {
    icon: TrendingDown,
    label: "Worsened",
    colorClass: "text-[hsl(300_45%_55%)]",
  },
  neutral: {
    icon: Minus,
    label: "Changed",
    colorClass: "text-muted-foreground",
  },
}

export function LifecycleEventRow({
  event,
  muted,
}: {
  event: HardwareDriftEventItem
  muted?: boolean
}) {
  const typeMeta = EVENT_TYPE_META[event.event_type]
  const TypeIcon = typeMeta.icon
  const dirMeta = DIRECTION_META[event.direction]
  const DirIcon = dirMeta.icon

  return (
    <div
      className={`flex flex-wrap items-center gap-3 py-2 text-sm ${muted ? "text-foreground/70" : ""}`}
    >
      <div className="flex items-center gap-1.5 text-muted-foreground shrink-0">
        <TypeIcon className="h-3.5 w-3.5" aria-hidden="true" />
        <span className="label-eyebrow">{typeMeta.label}</span>
      </div>

      <div className="min-w-0">
        <div className="font-data">{event.host}:{event.port}</div>
        {(event.vendor || event.model) && (
          <div className="text-xs text-muted-foreground">
            {[event.vendor, event.model].filter(Boolean).join(" ")}
          </div>
        )}
      </div>

      <div className="min-w-0 flex-1">
        {event.old_value ?? "—"} → {event.new_value ?? "—"}
      </div>

      <div className={`flex items-center gap-1 shrink-0 ${dirMeta.colorClass}`}>
        <DirIcon className="h-3.5 w-3.5" aria-hidden="true" />
        <span>{dirMeta.label}</span>
      </div>

      <div className="text-xs text-muted-foreground font-data shrink-0">
        {new Date(event.detected_at).toLocaleDateString("en-US", { dateStyle: "medium" })}
      </div>
    </div>
  )
}
