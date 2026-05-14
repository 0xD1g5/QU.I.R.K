import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useScanList } from "@/hooks/useScanList"
import type { ScanSession } from "@/types/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { PageSpinner } from "@/components/PageSpinner"
import { EmptyStateCard } from "@/components/EmptyStateCard"
import { Card, CardContent } from "@/components/ui/card"

const SEVERITY_STYLES: Record<string, string> = {
  HIGH: "bg-[hsl(24_95%_53%)] text-white",
  MEDIUM: "bg-[hsl(38_92%_50%)] text-black",
  LOW: "bg-[hsl(213_94%_68%)] text-black",
}

export function ScanHistoryPage() {
  const navigate = useNavigate()
  const { sessions, loading, error } = useScanList()
  const [selected, setSelected] = useState<string[]>([])

  function handleCheck(scanId: string, checked: boolean) {
    setSelected(prev => {
      if (!checked) return prev.filter(id => id !== scanId)
      const next = [...prev, scanId]
      return next.length > 2 ? next.slice(next.length - 2) : next  // FIFO drop oldest (D-05)
    })
  }

  function handleClone(s: ScanSession) {
    const params = new URLSearchParams()
    if (s.target) params.set("target", s.target)
    if (s.profile) params.set("profile", s.profile)
    if (s.calibration) params.set("calibration", s.calibration)
    if (s.profile === null) params.set("reconstructed", "1")  // amber notice trigger
    navigate(`/scan/new?${params.toString()}`)
  }

  function handleCompare() {
    const [s1, s2] = selected
    const sess1 = sessions.find(s => s.scan_id === s1)!
    const sess2 = sessions.find(s => s.scan_id === s2)!
    const newer = sess1.scanned_at >= sess2.scanned_at ? s1 : s2
    const older = newer === s1 ? s2 : s1
    navigate(`/compare?a=${encodeURIComponent(newer)}&b=${encodeURIComponent(older)}`)
  }

  if (loading) return <PageSpinner ariaLabel="Loading scan history" />

  if (error) {
    return (
      <Card>
        <CardContent className="py-6 text-sm text-destructive">
          Could not load scan history. Check that the QUIRK server is running and reload the page.
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Scan History</h1>
        <p className="text-sm text-muted-foreground">All scans — select any two to compare</p>
      </div>

      {sessions.length === 0 ? (
        <EmptyStateCard message="No scans yet — run your first scan from the CLI or the New Scan form to see history here." />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10"></TableHead>
              <TableHead>Date</TableHead>
              <TableHead>Target</TableHead>
              <TableHead>Profile</TableHead>
              <TableHead>Score</TableHead>
              <TableHead>High</TableHead>
              <TableHead>Med</TableHead>
              <TableHead>Low</TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sessions.map(s => (
              <TableRow key={s.scan_id}>
                <TableCell>
                  <Checkbox
                    checked={selected.includes(s.scan_id)}
                    onCheckedChange={(checked: boolean | "indeterminate") =>
                      handleCheck(s.scan_id, checked === true)
                    }
                    aria-label={`Select scan from ${new Date(s.scanned_at).toLocaleString()}`}
                  />
                </TableCell>
                <TableCell className="text-sm">
                  {new Date(s.scanned_at).toLocaleString()}
                </TableCell>
                <TableCell className="text-sm">
                  {s.target ?? <span className="text-muted-foreground">—</span>}
                </TableCell>
                <TableCell className="text-sm">
                  {s.profile ?? <span className="text-muted-foreground">—</span>}
                </TableCell>
                <TableCell className="font-data text-sm">{s.score}</TableCell>
                <TableCell>
                  <Badge className={`${SEVERITY_STYLES.HIGH} font-semibold text-xs font-data`}>
                    {s.finding_counts.high}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge className={`${SEVERITY_STYLES.MEDIUM} font-semibold text-xs font-data`}>
                    {s.finding_counts.medium}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge className={`${SEVERITY_STYLES.LOW} font-semibold text-xs font-data`}>
                    {s.finding_counts.low}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Button variant="outline" size="sm" onClick={() => handleClone(s)}>Clone</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {selected.length === 2 && (
        <div className="fixed bottom-0 left-12 lg:left-60 right-0 z-20 bg-card border-t border-border px-6 py-3 flex items-center justify-between">
          <span className="text-sm text-muted-foreground">2 scans selected</span>
          <Button onClick={handleCompare}>Compare scans</Button>
        </div>
      )}
    </div>
  )
}
