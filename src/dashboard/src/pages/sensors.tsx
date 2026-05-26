import { useMemo } from "react"
import { useSensorRegistry } from "@/hooks/useSensorRegistry"
import type { SensorRegistryItem } from "@/types/api"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyStateCard } from "@/components/EmptyStateCard"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"

// Relative time helper — no date library dependency
function relativeTime(isoString: string | null | undefined): string {
  if (!isoString) return "Never"
  const then = new Date(isoString).getTime()
  if (isNaN(then)) return "Never"
  const diffMs = Date.now() - then
  // Clamp negative deltas (sensor clock slightly ahead of console) to "Just now"
  // so a future timestamp never renders as "−N seconds ago" (WR-01).
  if (diffMs < 0) return "Just now"
  const diffSec = Math.floor(diffMs / 1000)
  if (diffSec < 60) return `${diffSec} second${diffSec !== 1 ? "s" : ""} ago`
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin} minute${diffMin !== 1 ? "s" : ""} ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr} hour${diffHr !== 1 ? "s" : ""} ago`
  const diffDay = Math.floor(diffHr / 24)
  return `${diffDay} day${diffDay !== 1 ? "s" : ""} ago`
}

// Status badge helper per UI-SPEC §1
function SensorStatusBadge({ status }: { status: SensorRegistryItem["status"] }) {
  if (status === "current") {
    return (
      <Badge
        className="bg-[hsl(var(--quantum-safe))] text-white text-xs"
        aria-label="status: Current"
      >
        Current
      </Badge>
    )
  }
  if (status === "stale") {
    return (
      <Badge
        className="bg-[#d4893a]/10 text-[#d4893a] border border-[#d4893a]/28 text-xs"
        aria-label="status: Stale"
      >
        Stale
      </Badge>
    )
  }
  // unknown
  return (
    <Badge
      variant="secondary"
      className="text-xs"
      aria-label="status: Unknown"
    >
      Unknown
    </Badge>
  )
}

function SensorsTable({ sensors }: { sensors: SensorRegistryItem[] }) {
  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead scope="col" className="text-xs font-semibold">Sensor ID</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Segment</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Version</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Last Seen</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sensors.map((s) => (
              <TableRow key={s.sensor_id} className="hover:bg-accent/5">
                <TableCell>
                  <span className="font-mono text-xs">{s.sensor_id}</span>
                </TableCell>
                <TableCell className="text-sm">{s.segment}</TableCell>
                <TableCell className="text-sm">
                  {s.sensor_version ?? "—"}
                </TableCell>
                <TableCell className="text-sm">
                  {relativeTime(s.last_push_at)}
                </TableCell>
                <TableCell>
                  <SensorStatusBadge status={s.status} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

export function SensorsPage() {
  const { sensors, loading, error } = useSensorRegistry()

  // Stable reference to the sensors list
  const sensorList = useMemo(() => sensors, [sensors])

  if (loading) {
    return (
      <div role="status" aria-label="Loading sensors" className="space-y-6">
        <span className="sr-only">Loading...</span>
        <Skeleton className="h-7 w-28" />
        {Array.from({ length: 5 }).map((_, r) => (
          <Skeleton key={r} className="h-10 w-full" />
        ))}
      </div>
    )
  }

  if (error) return <p className="text-muted-foreground text-sm">{error}</p>

  return (
    <div className="space-y-6">
      <h1 style={{ fontSize: 20, fontWeight: 600 }}>Sensors</h1>

      {sensorList.length === 0 ? (
        <EmptyStateCard message="No sensors enrolled. Run: quirk sensor enroll --console <url> to register a sensor." />
      ) : (
        <SensorsTable sensors={sensorList} />
      )}
    </div>
  )
}
