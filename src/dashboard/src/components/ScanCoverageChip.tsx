import { useEffect, useState } from "react"
import { ChevronDown } from "lucide-react"
import { fetchApi } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import {
  Collapsible, CollapsibleContent, CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"

/**
 * Phase 192 Plan 09 (OBS-02 / D-12): "N ran / M skipped" coverage chips with
 * expandable per-phase detail, backed by GET /api/scans/{id}/coverage or
 * GET /api/jobs/{id}/coverage — both read through the same
 * quirk.reports.coverage.load_scan_coverage() the report pipeline uses.
 *
 * D-15: an unrecorded scan (pre-v5.21, no ScanPhaseRecord rows) renders the
 * honest "Coverage data not recorded" notice — never a "0 ran / 0 skipped"
 * chip pair, which would misreport rather than merely look empty. A failed
 * fetch renders nothing that claims coverage, for the same reason.
 */

interface ScanCoveragePhase {
  phase_name: string
  label: string
  status: string
  reason: string | null
  detail: string | null
  duration_sec: number | null
}

interface ScanCoverageResponse {
  recorded: boolean
  ran: number
  skipped: number
  phases: ScanCoveragePhase[]
}

// UI-SPEC §Color: skip-reason -> --ds-* token; ran rows always --ds-ok.
const STATUS_COLOR_CLASS: Record<string, string> = {
  ran: "text-[var(--ds-ok)]",
  "disabled-by-config": "text-[var(--ds-medium)]",
  "missing-extra": "text-[var(--ds-medium)]",
  "no-eligible-targets": "text-[var(--ds-medium)]",
  "missing-credentials": "text-[var(--ds-high)]",
  failed: "text-[var(--ds-critical)]",
}

function statusColorClass(phase: ScanCoveragePhase): string {
  if (phase.status === "ran") return STATUS_COLOR_CLASS.ran
  return STATUS_COLOR_CLASS[phase.reason ?? ""] ?? STATUS_COLOR_CLASS["disabled-by-config"]
}

function formatDuration(durationSec: number | null): string {
  if (durationSec == null) return "—"
  return `${durationSec}s`
}

interface ScanCoverageChipProps {
  scanRunId?: string
  jobId?: string
  className?: string
}

export function ScanCoverageChip({ scanRunId, jobId, className }: ScanCoverageChipProps) {
  const [data, setData] = useState<ScanCoverageResponse | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false

    if (!scanRunId && !jobId) return

    const path = jobId
      ? `/api/jobs/${jobId}/coverage`
      : `/api/scans/${scanRunId}/coverage`

    async function load() {
      try {
        const resp = await fetchApi(path)
        if (!resp.ok) {
          if (!cancelled) setFailed(true)
          return
        }
        const json: ScanCoverageResponse = await resp.json()
        if (!cancelled) {
          setData(json)
          setFailed(false)
        }
      } catch {
        if (!cancelled) setFailed(true)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [scanRunId, jobId])

  // Failed fetch — render nothing that claims coverage (never fall back to
  // a fabricated "0 ran / 0 skipped" chip pair).
  if (failed || data == null) return null

  if (!data.recorded) {
    return (
      <div className={`rounded-md border px-4 py-2 ${className ?? ""}`}>
        <p className="text-sm font-semibold">Coverage data not recorded</p>
        <p className="text-sm text-muted-foreground mt-1">
          This scan predates per-phase coverage tracking (pre-v5.21). Re-scan to get full coverage
          detail.
        </p>
      </div>
    )
  }

  return (
    <div className={className}>
      <Collapsible>
        <div className="flex items-center gap-2 text-sm">
          <Badge variant="default" className="bg-[var(--ds-ok)] text-white border-transparent">
            {data.ran} ran
          </Badge>
          <Badge variant="outline">{data.skipped} skipped</Badge>
          <CollapsibleTrigger className="flex items-center gap-1 text-muted-foreground hover:text-[var(--ds-accent)] ml-2">
            Show detail
            <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
          </CollapsibleTrigger>
        </div>
        <CollapsibleContent>
          <Table className="mt-2">
            <TableHeader>
              <TableRow>
                <TableHead>Phase</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Detail</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.phases.map(phase => (
                <TableRow key={phase.phase_name}>
                  <TableCell className="text-sm">{phase.label}</TableCell>
                  <TableCell className={`text-sm ${statusColorClass(phase)}`}>
                    {phase.status === "ran" ? "ran" : `skipped: ${phase.reason}`}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {phase.status === "ran"
                      ? `${phase.label} — ran in ${formatDuration(phase.duration_sec)}`
                      : `${phase.label} — skipped: ${phase.reason} (${phase.detail ?? ""})`}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}
