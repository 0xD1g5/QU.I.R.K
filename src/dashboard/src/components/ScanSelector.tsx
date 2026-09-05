import { useScanList } from "@/hooks/useScanList"
import { useSelectedScan } from "@/hooks/useSelectedScan"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { formatScanDateTime } from "@/lib/datetime"

function formatScanLabel(scannedAt: string, totalEndpoints: number): string {
  return `${formatScanDateTime(scannedAt)} · ${totalEndpoints} ep`
}

export function ScanSelector() {
  const { sessions, loading } = useScanList()
  const { selectedScanId, setSelectedScanId } = useSelectedScan()

  if (loading || sessions.length <= 1) return null

  const value = selectedScanId ?? "__latest__"

  return (
    <div className="px-2 py-3 border-t border-border hidden lg:block">
      <p className="text-xs text-muted-foreground mb-1.5 px-1">Scan history</p>
      <Select
        value={value}
        onValueChange={(v) => setSelectedScanId(v === "__latest__" ? null : v)}
      >
        <SelectTrigger className="w-full text-xs h-8" aria-label="Select scan">
          <SelectValue placeholder="Latest scan" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__latest__">Latest scan</SelectItem>
          {sessions.map((s) => (
            <SelectItem key={s.scan_id} value={s.scan_id}>
              {formatScanLabel(s.scanned_at, s.total_endpoints)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
