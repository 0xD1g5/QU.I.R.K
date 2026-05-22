import { useEffect } from "react"
import { useScanData } from "@/hooks/useScanData"
import { useQRAMMPrintData } from "@/hooks/useQRAMMPrintData"
import type { FindingItem, CertItem, CbomComponent, RoadmapNode } from "@/types/api"
import type { QRAMMScoreResponse, QRAMMComplianceMapRow } from "@/types/api"
import { extractCN } from "@/lib/cert-parse"

const FRAMEWORK_DISPLAY: Record<string, string> = {
  NIST_PQC: "NIST PQC Standards",
  NSM10: "NSM-10",
  CNSA2: "CNSA 2.0",
  ISO27001: "ISO 27001:2022",
  ETSI_QS: "ETSI Quantum-Safe",
  PCI_DSS: "PCI-DSS v4.0",
  CC: "Common Criteria",
  BSI_TR: "BSI TR-02102",
}
const FRAMEWORK_ORDER = ["NIST_PQC", "NSM10", "CNSA2", "ISO27001", "ETSI_QS", "PCI_DSS", "CC", "BSI_TR"]
const QRAMM_DIMS = ["CVI", "SGRM", "DPE", "ITR"] as const

// Static CSS string — pure constant, no user content interpolated
const PRINT_CSS = [
  "body,html{background:#fff!important;color:#0a0a0a!important;font-family:Inter,-apple-system,sans-serif;font-size:14px}",
  ".print-section{break-before:page;padding-top:24px}",
  ".print-section:first-child{break-before:avoid}",
  "h1{font-size:28px;font-weight:600;margin-bottom:8px}",
  "h2{font-size:20px;font-weight:600;margin-bottom:12px;margin-top:24px}",
  "h3{font-size:16px;font-weight:600;margin-bottom:8px}",
  "table{width:100%;border-collapse:collapse;font-size:12px}",
  "th{text-align:left;padding:6px 8px;border-bottom:2px solid #e4e4e7;font-weight:600;background:#f4f4f5}",
  "td{padding:5px 8px;border-bottom:1px solid #e4e4e7;vertical-align:top}",
  ".badge{display:inline-block;padding:1px 6px;border-radius:4px;font-size:11px;font-weight:600}",
  ".sev-CRITICAL{background:#dc2626;color:#fff}",
  ".sev-HIGH{background:#f97316;color:#fff}",
  ".sev-MEDIUM{background:#f59e0b;color:#000}",
  ".sev-LOW{background:#60a5fa;color:#000}",
  ".sev-INFO{background:#71717a;color:#fff}",
  ".qs-Safe{background:#22c55e;color:#fff}",
  ".qs-At-Risk{background:#f59e0b;color:#000}",
  ".qs-Vulnerable{background:#dc2626;color:#fff}",
  ".qs-Unknown{background:#71717a;color:#fff}",
  ".meta{color:#52525b;font-size:12px;margin-top:4px}",
  ".score-row{display:flex;gap:32px;flex-wrap:wrap;margin:16px 0}",
  ".score-item{text-align:center;min-width:80px}",
  ".score-number{font-size:28px;font-weight:600}",
  ".score-label{font-size:12px;font-weight:600;color:#52525b}",
  ".tier-scanner{background:#4ba8a8;color:#fff}",
  ".tier-manual{background:#e4e4e7;color:#52525b}",
  ".qramm-radar{margin:16px 0}",
  ".qramm-footnote{font-size:12px;color:#52525b;margin-top:8px;border-top:1px solid #e4e4e7;padding-top:8px}",
  ".qramm-detail-section{margin-top:16px}",
].join("")

function PrintFindings({ findings }: { findings: FindingItem[] }) {
  if (!findings.length) return <p className="meta">No findings recorded.</p>
  return (
    <table>
      <thead>
        <tr>
          <th>Severity</th><th>Host</th><th>Port</th><th>Title</th><th>Quantum Risk</th>
        </tr>
      </thead>
      <tbody>
        {findings.map((f, i) => (
          <tr key={i}>
            <td><span className={`badge sev-${f.severity}`}>{f.severity}</span></td>
            <td>{f.host}</td>
            <td>{f.port}</td>
            <td>{f.title}</td>
            <td>{f.quantum_risk ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function PrintCerts({ certs }: { certs: CertItem[] }) {
  if (!certs.length) return <p className="meta">No TLS endpoints found.</p>
  return (
    <table>
      <thead>
        <tr>
          <th>Host</th><th>Port</th><th>Subject CN</th><th>Expiry</th><th>Algorithm</th><th>Quantum Safety</th>
        </tr>
      </thead>
      <tbody>
        {certs.map((c, i) => {
          const subjectCN = extractCN(c.cert_subject)
          const expiry = c.cert_not_after
            ? new Date(c.cert_not_after).toLocaleDateString("en-US", { dateStyle: "medium" })
            : "—"
          const qsClass = c.quantum_safety ? `qs-${c.quantum_safety.replace(" ", "-")}` : ""
          return (
            <tr key={i}>
              <td>{c.host}</td>
              <td>{c.port}</td>
              <td style={{ fontFamily: "monospace", fontSize: 11 }}>{subjectCN}</td>
              <td>{expiry}</td>
              <td style={{ fontFamily: "monospace", fontSize: 11 }}>
                {c.cert_pubkey_alg ?? "—"}{c.cert_pubkey_size ? ` ${c.cert_pubkey_size}b` : ""}
              </td>
              <td>{c.quantum_safety ? <span className={`badge ${qsClass}`}>{c.quantum_safety}</span> : "—"}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function PrintCbom({ components }: { components: CbomComponent[] }) {
  if (!components.length) return <p className="meta">No CBOM data available.</p>
  return (
    <table>
      <thead>
        <tr>
          <th>Algorithm</th><th>Type</th><th>Key Size</th><th>Quantum Safety</th><th>Source Systems</th>
        </tr>
      </thead>
      <tbody>
        {components.map((c, i) => {
          const qsClass = c.quantum_safety ? `qs-${c.quantum_safety.replace(" ", "-")}` : ""
          return (
            <tr key={i}>
              <td style={{ fontFamily: "monospace", fontSize: 11 }}>{c.algorithm}</td>
              <td>{c.type ?? "—"}</td>
              <td>{c.key_size ? `${c.key_size} bits` : "—"}</td>
              <td>{c.quantum_safety ? <span className={`badge ${qsClass}`}>{c.quantum_safety}</span> : "—"}</td>
              <td style={{ fontSize: 11 }}>
                {c.source_systems.slice(0, 5).join(", ")}
                {c.source_systems.length > 5 ? ` +${c.source_systems.length - 5} more` : ""}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function PrintRoadmap({ nodes }: { nodes: RoadmapNode[] }) {
  if (!nodes.length) return <p className="meta">No migration roadmap generated.</p>
  const grouped: Record<string, RoadmapNode[]> = {}
  for (const n of nodes) {
    const tf = n.timeframe ?? "Unknown"
    if (!grouped[tf]) grouped[tf] = []
    grouped[tf].push(n)
  }
  return (
    <div>
      {Object.entries(grouped).map(([tf, items]) => (
        <div key={tf} style={{ marginBottom: 16 }}>
          <h3>{tf}</h3>
          <ul style={{ paddingLeft: 20, margin: 0 }}>
            {items.map((n) => (
              <li key={n.id} style={{ marginBottom: 6 }}>
                <strong>{n.title}</strong>
                {n.why && <span className="meta"> — {n.why}</span>}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}

function PrintQRAMM({
  scoreResult,
  complianceRows,
}: {
  scoreResult: QRAMMScoreResponse | null
  complianceRows: QRAMMComplianceMapRow[] | null
}) {
  if (!scoreResult || !complianceRows) {
    return (
      <p className="meta">
        No QRAMM assessment completed — run an assessment from the dashboard to populate this section.
      </p>
    )
  }

  // Radar polygon points (compass: CVI=top, SGRM=right, DPE=bottom, ITR=left)
  const cx = 100, cy = 100, r = 80
  const cviScore  = scoreResult.dimensions["CVI"]?.score  ?? 0
  const sgrmScore = scoreResult.dimensions["SGRM"]?.score ?? 0
  const dpeScore  = scoreResult.dimensions["DPE"]?.score  ?? 0
  const itrScore  = scoreResult.dimensions["ITR"]?.score  ?? 0
  const cviPt  = [cx,                 cy - (cviScore  / 4) * r] as const
  const sgrmPt = [cx + (sgrmScore / 4) * r, cy] as const
  const dpePt  = [cx,                 cy + (dpeScore  / 4) * r] as const
  const itrPt  = [cx - (itrScore  / 4) * r, cy] as const
  const polygon = [cviPt, sgrmPt, dpePt, itrPt].map(([x, y]) => `${x},${y}`).join(" ")

  // Tier classification per framework: any row with scanner_informed=true → "Scanner-informed"
  const frameworkTier: Record<string, "scanner" | "manual"> = {}
  for (const fw of FRAMEWORK_ORDER) {
    const rows = complianceRows.filter((row) => row.framework === fw)
    frameworkTier[fw] = rows.some((row) => row.scanner_informed) ? "scanner" : "manual"
  }

  // Group compliance rows by framework
  const grouped: Record<string, QRAMMComplianceMapRow[]> = {}
  for (const row of complianceRows) {
    if (!grouped[row.framework]) grouped[row.framework] = []
    grouped[row.framework].push(row)
  }

  return (
    <div>
      {/* Layout order per UI-SPEC §Layout Structure: radar SVG FIRST, then executive intro paragraph. */}
      <div style={{ width: 200, height: 200, margin: "16px 0" }}>
        <svg viewBox="0 0 200 200" width={200} height={200} className="qramm-radar">
          {/* Axis lines */}
          <line x1={100} y1={100} x2={100} y2={20}  stroke="#e4e4e7" strokeWidth={1} />
          <line x1={100} y1={100} x2={180} y2={100} stroke="#e4e4e7" strokeWidth={1} />
          <line x1={100} y1={100} x2={100} y2={180} stroke="#e4e4e7" strokeWidth={1} />
          <line x1={100} y1={100} x2={20}  y2={100} stroke="#e4e4e7" strokeWidth={1} />
          {/* Score polygon */}
          <polygon
            points={polygon}
            fill="#4ba8a8"
            fillOpacity={0.18}
            stroke="#4ba8a8"
            strokeWidth={2}
          />
          {/* Axis labels */}
          <text x={100} y={14}  textAnchor="middle" fontSize={12} fill="#52525b">CVI</text>
          <text x={194} y={104} textAnchor="end"    fontSize={12} fill="#52525b">SGRM</text>
          <text x={100} y={196} textAnchor="middle" fontSize={12} fill="#52525b">DPE</text>
          <text x={6}   y={104} textAnchor="start"  fontSize={12} fill="#52525b">ITR</text>
          {/* Score values adjacent to each polygon vertex */}
          <text x={cviPt[0] + 4}  y={cviPt[1] - 4}  fontSize={12} fontWeight={600} fill="#0a0a0a">{cviScore.toFixed(1)}</text>
          <text x={sgrmPt[0] - 4} y={sgrmPt[1] - 4} fontSize={12} fontWeight={600} fill="#0a0a0a" textAnchor="end">{sgrmScore.toFixed(1)}</text>
          <text x={dpePt[0] + 4}  y={dpePt[1] + 12} fontSize={12} fontWeight={600} fill="#0a0a0a">{dpeScore.toFixed(1)}</text>
          <text x={itrPt[0] + 4}  y={itrPt[1] - 4}  fontSize={12} fontWeight={600} fill="#0a0a0a">{itrScore.toFixed(1)}</text>
        </svg>
      </div>

      <p>
        This section summarizes the organization's QRAMM (Quantum Readiness &amp; Maturity Model) governance posture based on the most recent completed assessment.
      </p>

      <h3>Dimension Scorecard</h3>
      <table>
        <thead>
          <tr><th>Dimension</th><th>Raw Score</th><th>Weighted Score</th></tr>
        </thead>
        <tbody>
          {QRAMM_DIMS.map((d) => {
            const dim = scoreResult.dimensions[d]
            const raw = dim?.score ?? 0
            const weighted = dim?.weighted ?? 0
            return (
              <tr key={d}>
                <td>{d}</td>
                <td>{raw.toFixed(1)}</td>
                <td>{weighted.toFixed(2)}</td>
              </tr>
            )
          })}
          <tr>
            <td colSpan={3} style={{ fontWeight: 600, textAlign: "right" }}>
              Overall maturity: {scoreResult.maturity}
            </td>
          </tr>
        </tbody>
      </table>

      <h3>Compliance Framework Coverage</h3>
      <table>
        <thead>
          <tr><th>Framework</th><th>Coverage Tier</th></tr>
        </thead>
        <tbody>
          {FRAMEWORK_ORDER.map((fw) => {
            const tier = frameworkTier[fw]
            const label = tier === "scanner" ? "Scanner-informed" : "Manual only"
            const cls   = tier === "scanner" ? "badge tier-scanner" : "badge tier-manual"
            return (
              <tr key={fw}>
                <td>{FRAMEWORK_DISPLAY[fw]}</td>
                <td><span className={cls}>{label}</span></td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="qramm-footnote">
        Coverage reflects QUIRK scanner findings for CVI only — SGRM, DPE, ITR require manual assessment.
      </p>

      {FRAMEWORK_ORDER.map((fw) => {
        const rows = grouped[fw] ?? []
        return (
          <div key={fw} className="qramm-detail-section">
            <h3>{FRAMEWORK_DISPLAY[fw]}</h3>
            <table>
              <thead>
                <tr>
                  <th>Practice Area</th>
                  <th>Dimension</th>
                  <th>Relevance Score</th>
                  <th>Scanner-Informed</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.practice_number}>
                    <td style={{ fontFamily: "monospace", fontSize: 11 }}>{row.practice_area}</td>
                    <td>{row.dimension}</td>
                    <td>{row.relevance_score === null ? "—" : row.relevance_score.toFixed(2)}</td>
                    <td>{row.scanner_informed ? "Yes" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      })}
    </div>
  )
}

export function PrintPage() {
  const { data, loading, error } = useScanData()
  const { scoreResult, complianceRows, loading: qrammLoading, error: qrammError } = useQRAMMPrintData()

  // BR-05 (D-06): clear stale data-ready on mount (in case a previous PrintPage left it set)
  // and on unmount, so the attribute does not survive client-side navigation.
  // Empty dep array — runs once on mount, cleanup on unmount only.
  useEffect(() => {
    document.body.removeAttribute('data-ready')
    return () => { document.body.removeAttribute('data-ready') }
  }, [])

  // QRAMM hook errors should not block the rest of the PDF — log and render the no-session fallback in that section.
  if (qrammError) {
    console.error("QRAMM print data error:", qrammError)
  }

  // Set data-ready only when both hooks have resolved. No cleanup return: removing the
  // attribute on every dependency change creates a transient window that PDF renderers
  // polling the attribute could observe before the re-set fires.
  useEffect(() => {
    // D-03 (WR-07): also gate on !qrammError so the PDF renderer never
    // captures a page that is missing the Q section due to a QRAMM hook error.
    if (data && !loading && !qrammLoading && !qrammError) {
      document.body.setAttribute('data-ready', 'true')
    }
  }, [data, loading, qrammLoading, qrammError])

  if (loading) {
    return (
      <div style={{ padding: 40, fontFamily: "sans-serif" }}>
        Loading scan data...
      </div>
    )
  }
  if (error) {
    return (
      <div style={{ padding: 40, fontFamily: "sans-serif", color: "red" }}>
        {error}
      </div>
    )
  }
  if (!data) return null

  const { meta, score, confidence, findings, certificates, cbom_components, roadmap } = data
  const scanDate = meta.scanned_at
    ? new Date(meta.scanned_at).toLocaleDateString("en-US", { dateStyle: "long" })
    : "Unknown"

  return (
    // D-28 (IN-06): inject static print CSS via JSX <style>. The CSS string
    // is a pure module-level constant — no user content is interpolated.
    <>
      <style>{PRINT_CSS}</style>
      <div style={{ padding: "0 24px", maxWidth: 900, margin: "0 auto" }}>

        {/* D-03 (WR-07): visible alert when QRAMM data could not be loaded. */}
        {qrammError && (
          <div role="alert" className="text-destructive text-sm" style={{ padding: "8px 0" }}>
            QRAMM data unavailable — Q section omitted
          </div>
        )}

        {/* Section 1: Cover */}
        <div className="print-section">
          <h1>QU.I.R.K. — Scan Results</h1>
          <p className="meta">Scan date: {scanDate}</p>
          <p className="meta">
            {meta.total_endpoints} endpoint(s) scanned &nbsp;·&nbsp; {meta.total_findings} finding(s)
          </p>
        </div>

        {/* Section 2: Executive Summary */}
        <div className="print-section">
          <h2>Executive Summary</h2>
          <div className="score-row">
            <div className="score-item">
              <div className="score-number">{score.score}</div>
              <div className="score-label">Overall Readiness ({score.rating})</div>
            </div>
            <div className="score-item">
              <div className="score-number">{score.subscores.hygiene}</div>
              <div className="score-label">Hygiene</div>
            </div>
            <div className="score-item">
              <div className="score-number">{score.subscores.modern_tls}</div>
              <div className="score-label">Modern TLS</div>
            </div>
            <div className="score-item">
              <div className="score-number">{score.subscores.identity_trust}</div>
              <div className="score-label">Identity</div>
            </div>
            <div className="score-item">
              <div className="score-number">{score.subscores.agility_signals}</div>
              <div className="score-label">Agility</div>
            </div>
            <div className="score-item">
              <div className="score-number">{score.subscores.data_at_rest}</div>
              <div className="score-label">Data at Rest</div>
            </div>
            <div className="score-item">
              <div className="score-number">{score.subscores.data_in_motion}</div>
              <div className="score-label">Data in Motion</div>
            </div>
          </div>
          <p className="meta">
            Confidence: {confidence.confidence_rating} ({confidence.confidence_score}%)
          </p>
        </div>

        {/* Section 3: Findings */}
        <div className="print-section">
          <h2>Findings</h2>
          <PrintFindings findings={findings} />
        </div>

        {/* Section 4: Certificate Inventory */}
        <div className="print-section">
          <h2>Certificate Inventory</h2>
          <PrintCerts certs={certificates} />
        </div>

        {/* Section 5: CBOM */}
        <div className="print-section">
          <h2>Cryptographic Bill of Materials</h2>
          <PrintCbom components={cbom_components} />
        </div>

        {/* Section 6: Migration Roadmap (text list — no Cytoscape graph in print per UI-SPEC) */}
        <div className="print-section">
          <h2>Migration Roadmap</h2>
          <PrintRoadmap nodes={roadmap.nodes} />
        </div>

        {/* Section 7: QRAMM Governance Assessment */}
        <div className="print-section">
          <h2>QRAMM Governance Assessment</h2>
          <PrintQRAMM
            scoreResult={qrammError ? null : scoreResult}
            complianceRows={qrammError ? null : complianceRows}
          />
        </div>

      </div>
    </>
  )
}
