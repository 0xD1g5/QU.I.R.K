import { useScanList } from "@/hooks/useScanList"
import { Calendar } from "lucide-react"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

function formatBadgeLabel(scannedAt: string): string {
  const date = new Date(scannedAt)
  const formatted = date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
  const time = date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
  return `Last scan: ${formatted} ${time}`
}

export function ScanDateBadge() {
  const { sessions, loading } = useScanList()

  // Transient flash prevention only — this is the ONLY state in which the badge is absent.
  // TAIL-01: unlike ScanSelector, the badge must never hide once loading resolves.
  if (loading) return null

  const label = sessions.length > 0 ? formatBadgeLabel(sessions[0].scanned_at) : "No scan yet"

  return (
    <div className="px-2 py-3 border-t border-border" role="status">
      {/* Expanded (lg+): full text row */}
      <p className="hidden lg:block text-xs text-muted-foreground px-1">{label}</p>
      {/* Collapsed (<lg): icon-only + tooltip, mirrors every other sidebar row's degrade pattern */}
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="lg:hidden flex justify-center">
            <Calendar className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          </div>
        </TooltipTrigger>
        <TooltipContent side="right" className="lg:hidden">{label}</TooltipContent>
      </Tooltip>
    </div>
  )
}
