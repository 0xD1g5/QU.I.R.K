import { useScanData } from "@/hooks/useScanData"
import { fetchApi } from "@/lib/api"
import { ScoreGauge } from "@/components/gauges/ScoreGauge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { PageSpinner } from "@/components/PageSpinner"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts"
import { Button } from "@/components/ui/button"
import { Download, Loader2 } from "lucide-react"
import { useState } from "react"
import { RegressionAlertChip } from "@/components/RegressionAlertChip"
import type { PartialFailureEntry } from "@/types/api"

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "hsl(0 72% 51%)",
  HIGH: "hsl(24 95% 53%)",
  MEDIUM: "hsl(38 92% 50%)",
  LOW: "hsl(213 94% 68%)",
  INFO: "hsl(240 5% 46%)",
}

const CONFIDENCE_BADGE_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  HIGH: "default",
  MEDIUM: "secondary",
  LOW: "outline",
  VERY_LOW: "destructive",
  NO_DATA: "outline",
}

/**
 * D-02 (WR-06): Defensive coercion of an unknown response body to a
 * user-facing string. Guards against raw-string bodies, null/undefined,
 * and non-string `detail` fields — never throws on `body.detail` access.
 */
export function coerceErrorDetail(body: unknown): string {
  if (body && typeof body === "object" && typeof (body as {detail?: unknown}).detail === 'string') {
    return (body as { detail: string }).detail
  }
  return String(body ?? "Unknown error")
}

function ScannerStatusCard({ failures }: { failures: PartialFailureEntry[] }) {
  function badgeElement(entry: PartialFailureEntry) {
    const cat = entry.error_category
    // Derive status from error_category per UI-SPEC:
    // missing_extra -> Skipped (gray), exception -> Failed (red), partial -> Partial (amber)
    if (cat === "missing_extra") {
      return (
        <Badge variant="secondary" aria-label="status: Skipped">
          Skipped
        </Badge>
      )
    }
    if (cat === "exception") {
      return (
        <Badge variant="destructive" aria-label="status: Failed">
          Failed
        </Badge>
      )
    }
    // partial or unknown -> amber custom badge
    return (
      <Badge
        className="bg-[#d4893a]/10 text-[#d4893a] border border-[#d4893a]/28"
        aria-label="status: Partial"
      >
        Partial
      </Badge>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle style={{ fontSize: 20, fontWeight: 600 }}>
          Scanner Status
        </CardTitle>
      </CardHeader>
      <CardContent>
        {failures.map((entry, idx) => (
          <div
            key={idx}
            className="flex items-center gap-3 py-2 border-b border-border last:border-0"
          >
            <span className="text-muted-foreground text-sm w-24 shrink-0">
              {entry.stage}
            </span>
            <span className="text-sm w-32 shrink-0">{entry.scanner}</span>
            {badgeElement(entry)}
            <span className="text-muted-foreground text-sm w-28 shrink-0">
              {entry.error_category}
            </span>
            <span
              className="text-sm truncate max-w-[60ch]"
              title={entry.error_message}
            >
              {entry.error_message}
            </span>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export function ExecutivePage() {
  const { data, loading, error } = useScanData()
  const [pdfExporting, setPdfExporting] = useState(false)
  const [pdfMessage, setPdfMessage] = useState<string | null>(null)

  async function handleExportPdf() {
    setPdfExporting(true)
    setPdfMessage("Generating PDF...")
    try {
      const resp = await fetchApi("/api/export/pdf", { method: "POST" })
      if (resp.ok) {
        const blob = await resp.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        const date = new Date().toISOString().split("T")[0]
        a.href = url
        a.download = `quirk-report-${date}.pdf`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        // Revoke after a tick so the browser has time to start the fetch
        setTimeout(() => URL.revokeObjectURL(url), 100)
        setPdfMessage(`PDF saved to ~/Downloads/quirk-report-${date}.pdf`)
      } else {
        const body = await resp.json().catch(() => null)
        const detail = coerceErrorDetail(body)
        // Preserve the operator-friendly Playwright hint when the API returned
        // no actionable detail (null, {}, etc. — coercion yields a non-string-detail fallback).
        const looksUseful =
          body && typeof body === "object" && typeof (body as {detail?: unknown}).detail === 'string'
        setPdfMessage(looksUseful ? detail : "PDF export failed. Ensure Playwright is installed: playwright install chromium")
      }
    } catch {
      setPdfMessage("PDF export failed. Ensure Playwright is installed: `playwright install chromium`")
    } finally {
      setPdfExporting(false)
    }
  }

  if (loading) return <PageSpinner ariaLabel="Loading executive summary" />

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">{error}</p>
      </div>
    )
  }

  if (!data || !data.score) {
    return (
      <div className="space-y-4 py-8">
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Executive Summary</h1>
        <p className="text-muted-foreground text-sm">
          No scan data available. Run a scan first: <code>quirk scan &lt;target&gt;</code>
        </p>
      </div>
    )
  }

  const { score, confidence, findings = [], meta } = data

  // Severity counts for bar chart
  const severityCounts = findings.reduce<Record<string, number>>((acc, f) => {
    acc[f.severity] = (acc[f.severity] ?? 0) + 1
    return acc
  }, {})
  const chartData = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"].map((s) => ({
    severity: s,
    count: severityCounts[s] ?? 0,
  }))

  const scanDate = meta.scanned_at
    ? new Date(meta.scanned_at).toLocaleDateString("en-US", { dateStyle: "medium" })
    : "Unknown"

  return (
    <div className="space-y-8">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <h1 style={{ fontSize: 20, fontWeight: 600 }} className="text-foreground">
          QU.I.R.K. — Scan Results
        </h1>
        <div className="flex items-center gap-3">
          {pdfMessage && (
            <span className="text-sm text-muted-foreground">{pdfMessage}</span>
          )}
          {/* Export PDF button — POST /api/export/pdf implemented in 05-06 (Wave 2, parallel).
               The endpoint exists by the time this plan executes. Button is fully wired. */}
          <Button
            onClick={handleExportPdf}
            disabled={pdfExporting}
            className="bg-accent text-white hover:bg-accent/90"
            title="Export PDF — requires playwright install chromium"
          >
            {pdfExporting ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Generating PDF...</>
            ) : (
              <><Download className="mr-2 h-4 w-4" /> Export PDF</>
            )}
          </Button>
        </div>
      </div>

      {/* Phase 64 TREND-02: Regression alert (above score gauge) */}
      <RegressionAlertChip />

      {/* Score gauges row */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap justify-around gap-8">
            <div className="flex flex-col items-center gap-1">
              <ScoreGauge
                score={score.score}
                label="Overall Readiness"
                size={160}
                isOverall
              />
              <Badge
                variant={CONFIDENCE_BADGE_VARIANT[confidence.confidence_rating] ?? "outline"}
                className="mt-1 text-xs font-semibold"
              >
                {confidence.confidence_rating === "HIGH" ? "High Confidence"
                  : confidence.confidence_rating === "MEDIUM" ? "Medium Confidence"
                  : confidence.confidence_rating === "LOW" ? "Low Confidence"
                  : confidence.confidence_rating === "VERY_LOW" ? "Very Low Confidence"
                  : "No Data"}
              </Badge>
            </div>
            <ScoreGauge score={score.subscores.hygiene} label="Hygiene" size={120} />
            <ScoreGauge score={score.subscores.modern_tls} label="Modern TLS" size={120} />
            <ScoreGauge score={score.subscores.identity_trust} label="Identity" size={120} />
            <ScoreGauge score={score.subscores.agility_signals} label="Agility" size={120} />
            <ScoreGauge score={score.subscores.data_at_rest} label="Data at Rest" size={120} />
            <ScoreGauge score={score.subscores.data_in_motion} label="Data in Motion" size={120} />
          </div>
        </CardContent>
      </Card>

      {/* Severity breakdown */}
      <Card>
        <CardHeader>
          <CardTitle style={{ fontSize: 20, fontWeight: 600 }}>Severity Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 32 }}>
              <XAxis type="number" tick={{ fontSize: 12 }} />
              <YAxis type="category" dataKey="severity" tick={{ fontSize: 12 }} width={72} />
              <Tooltip
                contentStyle={{ background: "hsl(240 6% 10%)", border: "1px solid hsl(240 6% 17%)" }}
                labelStyle={{ color: "hsl(0 0% 95%)" }}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {chartData.map((entry) => (
                  <Cell key={entry.severity} fill={SEVERITY_COLORS[entry.severity] ?? "#888"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Phase 67 RESUME-02: Scanner Status card — only shown when there are partial failures */}
      {data.partial_failures && data.partial_failures.length > 0 && (
        <ScannerStatusCard failures={data.partial_failures} />
      )}

      {/* Scan metadata */}
      <p className="text-muted-foreground" style={{ fontSize: 14 }}>
        Scan date: {scanDate} &nbsp;·&nbsp; {meta.total_endpoints} endpoint(s) scanned &nbsp;·&nbsp; {meta.total_findings} finding(s)
      </p>
    </div>
  )
}
