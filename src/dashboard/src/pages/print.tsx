import { createElement, useEffect } from "react"
import { useScanData } from "@/hooks/useScanData"
import type { FindingItem, CertItem, CbomComponent, RoadmapNode } from "@/types/api"

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
          const subjectCN = c.cert_subject ? (c.cert_subject.match(/CN=([^,]+)/)?.[1] ?? c.cert_subject) : "—"
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

export function PrintPage() {
  const { data, loading, error } = useScanData()

  useEffect(() => {
    if (data) {
      document.body.setAttribute('data-ready', 'true')
    }
    return () => {
      document.body.removeAttribute('data-ready')
    }
  }, [data])

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
    // Inject static print CSS via createElement to avoid hook restrictions on inline HTML.
    // The CSS string is a pure constant — no user data is interpolated into it.
    <>
      {createElement("style", null, PRINT_CSS)}
      <div style={{ padding: "0 24px", maxWidth: 900, margin: "0 auto" }}>

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

      </div>
    </>
  )
}
